"""Shape A — deterministic workflow. Student work.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Suggested steps. Money stays in code (`lab8.tools.compute_compensation`).

1. Open the store. Read the claim through `get_claim_view` (not SELECT *).
2. Missing order_id -> status `needs_info`. Do not write the ledger.
3. `lookup_order`. If not visible -> `escalated`. Do not copy phone, address, item, internal note.
4. Quote from the order row. Ignore delay numbers written in the ticket.
5. Quote amount 0 -> `denied`. Do not call issue_refund.
6. Quote amount > 0 -> `durability.issue_refund(conn, claim_id, <full quote>)`.
   Pass the FULL quote. The host checks the claim's own approval and subtracts
   what earlier claims already got for the same order (T13, T14). Do not
   subtract it yourself or the host subtracts twice.
   Auth failure or order already refunded -> `denied` (the host writes `policy_denied`).
   `proposal_amount` stays the full quote. Amount conflict -> `failed`.
7. Success -> `resolved`. One ledger row, one `refund_committed` audit.
8. Use MockLLM only to draft the reply text, if you want a model call at all.

The model must not choose the refund amount and must not commit the refund.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

SHAPE = "workflow"


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": int(proposal), "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    try:
        # Bước 1: đọc claim qua view có allowlist (không SELECT *).
        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)
        if not claim.get("found"):
            return done("failed", 0, "unknown_claim")
        # Chỉ ghi field an toàn. Không ghi ticket/principal vào trace.
        trace.add("claim", {"claim_id": claim_id, "has_order_id": bool(claim.get("order_id"))})

        # Bước 2: thiếu order_id -> needs_info. Không đoán mã đơn từ ticket.
        if not claim.get("order_id"):
            return done("needs_info", 0, "missing_order_id")

        # Bước 3: tra đơn theo đúng principal của claim.
        budget.add_tool(tool_cost())
        order_view = lookup_order(conn, claim["order_id"], claim["principal_id"])
        if not order_view.get("visible"):
            trace.add("lookup_order", {"visible": False, "reason": order_view.get("reason")})
            return done("escalated", 0, order_view.get("reason"))
        order = order_view["order"]  # đã qua ORDER_FIELDS, không có SĐT/địa chỉ
        trace.add("lookup_order", {"visible": True, "order": safe_dump(order)})

        # Bước 4: tính tiền bằng code, từ dòng order trong DB. Bỏ qua số ngày trễ trong ticket.
        budget.add_tool(tool_cost())
        quote = compute_compensation(conn, order)
        proposal = int(quote["amount_vnd"])
        trace.add("quote", safe_dump(quote))

        # Bước 5: quote = 0 -> denied, không gọi issue_refund.
        if proposal <= 0:
            return done("denied", 0, quote.get("reason"))

        # Bước 6: truyền quote ĐẦY ĐỦ + crash_at cho host. Không tự trừ phần đã hoàn.
        try:
            outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except InjectedCrash:
            # Không nuốt crash: ghi trace rồi ném lại cho crash test.
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise
        trace.add("issue_refund", {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]})

        if not outcome["ok"]:
            status = "failed" if outcome["conflict"] else "denied"
            return done(status, proposal, outcome["reason"])

        # Bước 7: thành công.
        return done("resolved", proposal, None)

    except InjectedCrash:
        raise
    except Exception as exc:  # run_claim không được ném exception ra ngoài
        trace.add("error", {"type": type(exc).__name__})
        return done("failed", 0, f"exception:{type(exc).__name__}")