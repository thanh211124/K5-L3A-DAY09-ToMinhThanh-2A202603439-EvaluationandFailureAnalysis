# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | **Đạt** (0.757 ≥ 0.6, 0.857 ≥ 0.8, 0.800 ≥ 0.7) | **dùng** cho report |
| helpful | 100 | 0.375 | 1.000 | 0.300 | **Không** (κ < 0.6, R < 0.7) | **loại** |

Ma trận nhầm lẫn (FAIL là positive):
- tone: `tp=24, fp=4, fn=6, tn=66` → fail rate quan sát 0.28, sau hiệu chỉnh Rogan–Gladen ≈ 0.30.
- helpful: `tp=9, fp=0, fn=21, tn=70` → recall chỉ 0.30: 21/30 lỗi người đánh FAIL thì judge vẫn nói PASS.

## ≥5 case audit thủ công

Lấy từ 10 trường hợp bất đồng của tone (`judge_tone_public.csv`), kèm 3 trường hợp của helpful.

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha…" | PASS | FAIL | **Người đúng** | Xưng "em" + "nha" quá suồng sã với khách; judge coi là thân thiện |
| 2 | H-029 "…không cần nhắn thêm" | PASS | FAIL | **Người đúng** | Giọng ra lệnh; judge chỉ thấy "Dạ, vui lòng" |
| 3 | H-070 "…cho đơn O-909 ạ 😂😂" | PASS | FAIL | **Người đúng** | Emoji buồn cười trong ngữ cảnh khiếu nại là sai tone |
| 4 | H-042 "Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | **Người đúng** | Judge phạt vì "thiếu xin lỗi" dù reply đủ ý, đúng thông tin |
| 5 | H-051 "Dạ, LogiX đã refund 90.000đ…" | FAIL | PASS | **Người đúng** | "refund" là từ CS LogiX cho phép; judge phạt sai khi thấy tiếng Anh |
| 6 | H-081 "Dạ, đơn O-107 chưa đủ điều kiện hoàn…" | FAIL | PASS | **Judge đúng** | Nhãn người đọc nhầm ticket — nên **sửa nhãn** trước khi dùng lại |
| 7 | H-088 "Dạ, dạ, LogiX đã hoàn 40.000đ…" | FAIL | PASS | **Người đúng** | Lặp "Dạ" do lỗi gõ; cả hai đều chấp nhận được, lỗi nhẹ |
| 8 | H-094 "Da, LogiX da hoan 40.000đ…" | PASS | FAIL | **Người đúng** | Dịch máy mất dấu tiếng Việt — tone hỏng, judge không bắt được |
| 9 | HL-015 "Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ." (helpful) | PASS | FAIL | **Người đúng** | Số trong reply (55.000) khác ledger (40.000) — lỗi FM-08, nhưng judge chỉ chấm "có lịch sự không" → PASS |
| 10 | HL-047 "Ok bạn, đơn O-515 xử lý rồi nhé." (helpful) | PASS | FAIL | **Người đúng** | Reply quá ngắn, thiếu thông tin khách cần; judge không bắt được |

## Kết luận

- **tone_ok: DÙNG.** κ = 0.757, P = 0.857, R = 0.800 đều ≥ FLOORS. Judge hơi **nghiêm khắc** ở giọng
  thân-mít (H-042, H-051: người chấp nhận, judge phạt vì "thiếu xin lỗi" / "dùng tiếng Anh") và
  **bỏ sót** các lỗi tone sâu (xưng hô H-008, giọng lệnh H-029, emoji H-070, mất dấu H-094).
  Sau hiệu chỉnh Rogan–Gladen (sens = recall = 0.8, spec = tn/(tn+fp) = 66/70 ≈ 0.943),
  fail rate thực ≈ 0.30. Có 1 nhãn người sai (H-081) cần rà lại trước khi dùng làm calibration set.
- **helpful: LOẠI.** κ = 0.375 < 0.6 và R = 0.300 < 0.7 (21/30 lỗi "không hữu ích" bị bỏ qua).
  Ma trận `tp=9, fp=0, fn=21, tn=70` — không có FP, chỉ toàn FN, đúng dấu hiệu judge quá rộng.
  Nguyên nhân: judge chỉ chấm "reply có lịch sự không" chứ không kiểm **số trong reply khớp ledger
  hay không** (HL-015: reply 55.000, ledger ghi 40.000) hay "reply có đủ thông tin khách cần" (HL-047).
  → Chấm "helpful" bằng **code** (grader ReplyMatchesLedger cho FM-08, grader missing-info) thay vì LLM judge.
- **Sửa rubric (gợi ý):** (1) thêm tiêu chí "số trong reply phải khớp ledger" vào rubric helpful;
  (2) tone rubric cần liệt kê **ví dụ lỗi** (xưng hô, giọng lệnh, emoji, dấu) thay vì chỉ "lịch sự";
  (3) loại nhãn sai H-081 khỏi calibration set; (4) re-calibrate sau khi thêm 20–30 nhãn người mới.
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có
  held-out thật. κ = 0.757 đạt FLOOR nhưng chưa đủ để tin judge trong vùng khó (FN tập trung ở lỗi
  tone sâu); dùng judge **chỉ khi nào pass floor**, còn tiền/approval luôn chấm bằng code.
