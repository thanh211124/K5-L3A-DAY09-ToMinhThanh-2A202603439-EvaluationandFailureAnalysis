# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** `E-swarm-20261117-8d0f` · eval set sha `8d0f4dc0100d`
- **Phiên bản:** commit `66560ef` · eval set v1 (sha `8d0f4dc0100d`) · metric_spec v1.0 · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: `labels_v1.json`
- **Metric & ngưỡng:**

| Metric | Loại | Ngưỡng | Chặn? | Baseline (swarm) |
|---|---|---|---|---|
| approval_bypass | an toàn | max=0 | có | 0 |
| secret_leak | an toàn | max=0 | có | 0 |
| reply_amount_correct | an toàn (FM-08) | max=0 | có | 0 |
| refund_amount_correct | năng lực | ≥0.95, no_significant_drop | có | 0.9857 |
| pass_rate | năng lực | ≥0.85, no_significant_drop | có | 0.9857 |
| db_fact_kept | năng lực | ≥0.95 | không | 0.9857 |
| pass_5 | theo dõi | ≥0.80 | không | 0.9286 |
| cost_per_success | hệ thống | max_increase=10% | không | 49.567 |

- **Kết quả baseline vs PR:**

| Shape | pass_rate | Δ vs baseline | CI 95% | Gate |
|---|---|---|---|---|
| swarm (baseline) | 0.9857 | — | — | — |
| fixed | 1.0000 | +0.014 | [+0.000, +0.043] | exit 0 |
| seeded_regression | 0.7143 | −0.271 | [−0.500, −0.057] | exit 1 |

- **Judge:** `tone_ok` κ=0.757 → **SỬ DỤNG** (P=0.857, R=0.800); `helpful` κ=0.375 → **LOẠI** (P=1.0, R=0.300 < 0.70 — recall quá thấp, grader bỏ sót 70% false)
- **Trace case:** `docs/trace_case.md` — `seeded_regression C-002@55`; bước sai đầu tiên: bước 3 `model_override {delay_days:5}` (FM-03); regression test `test_seeded_regression_c002_seed55_fails` + `test_fixed_c002_seed55_passes`
- **Gate owner:** To Minh Thanh (MSSV 2A202603439) — xử lý khi gate exit 1
- **Phạm vi pilot:** MockLLM, eval set v1 (14 item × 5 seed); yêu cầu hoàn tiền đơn lẻ theo policy LogiX-VN
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item (CI rộng, chỉ bắt hồi quy lớn), judge replay trên CSV công khai; chưa đo trên người dùng thật
- **Khi nào tăng eval-set version:** thêm item từ trace case mới, hoặc bắt được failure mode mới chưa có trong v1
