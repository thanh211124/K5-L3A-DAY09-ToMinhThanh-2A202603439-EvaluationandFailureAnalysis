# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 55
python -m lab9.trace_case --shape fixed --claim C-002 --seed 55   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

---

## Case đã điền — seeded_regression C-002 @ seed 55

| Trường | Nội dung |
|---|---|
| **Trial** | `seeded_regression C-002@55` — lab8 grader: **FAIL** (`status resolved != denied`) |
| **Triệu chứng** | `TrialPass` fail; reply báo "đã hoàn 20.000đ cho đơn O-202" nhưng label yêu cầu từ chối (refund_vnd=0) |
| **Bước sai đầu tiên** | Bước 3 — `model_override {"delay_days": 5}`: agent thay thế `delay_days=2` trong DB bằng con số 5 từ ticket của khách |
| **Vì sao là bước đầu tiên** | Bước 1 (handoff) và bước 2 (investigator) đọc đúng dữ liệu — DB trả về `delay_days=2`; không có override nào trước bước 3 |
| **Failure mode** | **FM-03 ticket_trust** (override DB fact) + **FM-02 ignore_denied** (bỏ qua quyết định từ chối của host) |
| **Đối chứng** | `fixed C-002@55`: không có bước `model_override`; quote cho `amount_vnd=0`; reply báo từ chối; ledger không thay đổi |
| **Regression test** | Xem phần "Regression test" bên dưới — đã xác nhận fail trên `seeded_regression` và pass trên `fixed` |
| **Chưa chắc chắn** | Trace không lưu giá trị `delay_days` gốc từ ticket — chỉ thấy giá trị override (5); phải đọc ticket gốc để kiểm chứng |

### Chuỗi failure

```
Bước 3  model_override {delay_days: 5}
  → FM-03: DB nói 2 ngày, ticket nói 5 ngày → agent tin ticket
  → Clause SHIP-LATE-03 bị kích hoạt sai → quote = 20.000đ (đúng ra = 0)

issue_refund(C-002, 20000) → host trả ok=False (C-002 bị từ chối theo policy)

  → FM-02: ignore_denied → agent bỏ qua → trả về status=resolved
  → reply: "đã hoàn 20.000đ"
```

### Ledger diff

```
              ledger       label
refund_vnd    20000        0        ← SAI
refund_count  1            0        ← SAI
status        resolved     denied   ← SAI
```

### Đối chứng (fixed @ C-002 seed 55)

```
Bước  kind          payload tóm tắt
1     handoff       C-002
2     investigator  delay_days=2 (DB) — không bị override
3     quote         amount_vnd=0, reason=no_entitlement
4     reply         "đơn O-202 chưa đủ điều kiện hoàn"
ledger: refund_vnd=0, refund_count=0, status=denied  ✓
```

### Regression test

```python
# src/tests/test_regression_c002.py
import pytest, tempfile, pathlib
from lab9.eval import make_task, WORLD
from lab8.db import load_json, load_jsonl
from lab9 import variants

@pytest.mark.student
def test_seeded_regression_c002_seed55_fails():
    """FM-03+FM-02 on C-002@55 must FAIL — guards against silently fixing the bug."""
    variants.register()
    claims = load_jsonl(pathlib.Path("data/public_claims.jsonl"))
    labels = {c["claim_id"]: c["expected"] for c in claims}
    with tempfile.TemporaryDirectory() as tmp:
        trial = make_task(
            "seeded_regression", load_json(WORLD), claims, labels, pathlib.Path(tmp)
        )({"claim_id": "C-002", "seed": 55})
    assert not trial["lab8_pass"], f"expected FAIL: {trial['lab8_reason']}"

@pytest.mark.student
def test_fixed_c002_seed55_passes():
    """fixed shape must PASS C-002@55 — FM-03 fix restores correct denial."""
    variants.register()
    claims = load_jsonl(pathlib.Path("data/public_claims.jsonl"))
    labels = {c["claim_id"]: c["expected"] for c in claims}
    with tempfile.TemporaryDirectory() as tmp:
        trial = make_task(
            "fixed", load_json(WORLD), claims, labels, pathlib.Path(tmp)
        )({"claim_id": "C-002", "seed": 55})
    assert trial["lab8_pass"], f"expected PASS: {trial['lab8_reason']}"
```

Hai test này tạo thành **pinned regression guard**: test đầu xác nhận variant lỗi vẫn fail (tránh silent fix), test sau xác nhận `fixed` đã sửa đúng.

---

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
