# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

Tên nhóm: AIOT
Người đại diện / MSSV: Hoàng Đức Dũng / 2A202602798
Tên repo: K4-L3-DAY04-NhomAIOT-PromptEngineeringToolCalling
URL repo, nhánh nộp, commit chốt: https://github.com/hddung-vinai/K4-L3-DAY04-NhomAIOT-PromptEngineeringToolCalling — nhánh nộp dung — commit chốt 6d92614 (commit sau đó chỉ cập nhật TEAM.md)
Deadline áp dụng và link thông báo đổi hạn nếu có: hạn mặc định 12:00 ngày làm lab 16/09/2026 (Asia/Ho_Chi_Minh) theo SUBMISSION.md;
Lịch sử bản nộp:
56756cb (15/09/2026 20:29 +07): bản làm tại lớp — v0–v3 lần đầu, 10 case nhóm, run adversarial. Run của bản này được giữ ở starter_v0/runs/archive_lab4_attempt1/.

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| | | | | |

## Nhận xét chung

Kết quả và bằng chứng: bộ base 30 câu case_accuracy v0 0.70 → v1 0.8667 → v2 0.9667 → v3 0.9667, giữ 0.9667 ở v4, v5 (starter_v0/artifacts/version_log.csv, REPORT mục B1). Bộ adversarial 12 câu: v3 0.6667 và 2 ticket thật bị tạo do tấn công → v5 0.75 và 0 lệnh ghi do tấn công (REPORT B4a). Bộ 10 case nhóm trên v5: 0.80 (REPORT B3). Transcript: 5 kịch bản CLI và 1 phiên web UI trên v5 (REPORT B4).
Thay đổi hiệu quả nhất: (1) v1 viết lại tool declaration — +0.1667 trên base, hết đoán ID và sai check; (2) v2 luồng xác nhận 2 bước trong prompt — hết 3 lỗi boundary trên base; (3) v4–v5 guard ở tầng thực thi — chặn ghi dữ liệu từ xác nhận giả mà luồng xác nhận hợp lệ vẫn tạo được ticket.
Giới hạn còn lại: H19 (môi trường không có trong enum) lật pass/fail theo artifact, probe 5 lần xác nhận không ổn định; G05 hỏi yes_no thay vì choice cho priority mơ hồ; A04/A11 vẫn FAIL về điểm vì eval chấm lời gọi tool của model dù guard đã chặn ghi; A12/S5 agent vẫn đưa mã nội bộ vào tool web, chỉ được code của tool chặn; guard nhận diện câu đồng ý bằng từ khóa nên có thể chặn nhầm câu trả lời diễn đạt lạ (chặn nhầm thì agent hỏi lại, không ghi sai).
Cách phân công và tích hợp: phân công dự kiến là Dũng phụ trách vòng lặp prompt/tool và đo lường, Bình phụ trách case nhóm và an toàn, Minh phụ trách UI/transcript; bằng chứng tích hợp vào starter_v0/artifacts/REPORT.md.

## INDIVIDUAL

### Hoàng Đức Minh — 2A202602362

- Phần việc và file/commit/PR:
  - **Web UI** (`starter_v0/web_ui.py`): Xây dựng Gradio Blocks UI kết nối trực tiếp với `run_model_tool_loop` từ `chat.py`. UI gồm cửa sổ chat, panel "Tool trace" hiển thị tool calls/results sau mỗi lượt, nút xoá hội thoại, và tự động lưu transcript JSON vào `transcripts/` sau mỗi turn. Hỗ trợ `--provider`, `--model`, `--version`, `--share`.
  - **Smoke test** (`starter_v0/scripts/ui_smoke_test.py`): Script kiểm thử pipeline agent end-to-end gồm 3 cases — routing (`check_service_status`), clarify khi thiếu asset ID, và out-of-scope không gọi tool. Chạy được bằng `python scripts/ui_smoke_test.py --provider openrouter --verbose`; exit code 0 khi pass, 1 khi fail.
  - **Transcripts** (`starter_v0/transcripts/.gitkeep`): Tạo thư mục lưu transcript với `.gitkeep` để theo dõi qua git.
  - **Phân tích và fix lỗi eval** (`starter_v0/artifacts/system_prompt.md`, `starter_v0/artifacts/tools.yaml`): Phân tích nguyên nhân các failure type `wrong_tool` (H04, H13, H17), `missing_info` (H10, H11, H19), `wrong_boundary` (H12, M05, M09) từ kết quả run eval. Viết fix có hypothesis rõ ràng, giữ code cũ dưới dạng comment `[v0]` trước khi thay thế.

- Quyết định, khó khăn và cách xử lý:
  - **Web UI không dùng `agent.run()` trực tiếp** mà dùng `run_model_tool_loop` từ `chat.py` — vì `agent.run()` chỉ làm 1 tool round, trong khi UI cần xử lý clarify (tool loop dừng lại chờ user) và multi-round. Quyết định này giữ consistency với `chat.py`.
  - **Gradio `type="messages"`** thay vì `type="tuples"` (deprecated trong Gradio 4+): tránh warning và tương thích với Gradio 6.
  - **Fix `wrong_boundary` sau khi fix `missing_info` làm M05 tệ hơn**: Xác định root cause là `clarify` description quá ngắn khiến LLM không biết dùng `yes_no` cho ticket. Fix bằng cách mô tả rõ 3 `response_type` trong description của tool `clarify`, đồng thời liệt kê các phrase trigger Step 1 trong `system_prompt.md` (tiếng Việt cụ thể như "cho mình xem lại và hỏi xác nhận").
  - **Bỏ `default: "production"` trong `environment`** để LLM không fall back im lặng khi gặp "demo", "QA" — thay vào đó phải gọi `clarify(choice)`. Kiểm tra collision: tất cả 7 cases dùng `check_service_status` đều có environment rõ ràng trong query hoặc carry từ turn trước, nên bỏ default an toàn.

- Điều đã học:
  - Tool description trong `tools.yaml` ảnh hưởng trực tiếp đến routing của LLM — description ngắn và thiếu boundary conditions là nguyên nhân chính của các failure type `wrong_tool` và `missing_info`. Cải thiện description cụ thể hơn default behavior giúp tăng accuracy rõ rệt.
  - Khi fix một failure type cần kiểm tra collision với các cases khác trước khi áp dụng — fix `missing_info` có thể làm hỏng `wrong_boundary` nếu không cẩn thận về scope của rule.
  - `run_model_tool_loop` trong `chat.py` detect clarify tool qua `result.get("awaiting_user")` thay vì hard-code tên tool — pattern này rename-proof và nên giữ nhất quán trong web_ui.

- AI/công cụ đã dùng và cách kiểm tra:
  - Dùng **Kiro (AI IDE)** để phân tích codebase (`agent.py`, `chat.py`, `run_eval.py`), đề xuất fix hypothesis, và viết code cho `web_ui.py` và `ui_smoke_test.py`.
  - Kiểm tra: chạy `python scripts/ui_smoke_test.py --provider openrouter --verbose` — kết quả 3/3 PASS, exit code 0. Tool calls khớp với expected: `check_service_status(vpn, production)`, `clarify(text)`, no-tool cho out-of-scope.
  - Mọi fix `system_prompt.md` và `tools.yaml` được đối chiếu thủ công với từng case trong `eval_base.json` trước khi áp dụng để tránh regression.

- Thời điểm đã tự nộp URL repo chung trên VLearn: 10h30 16/09/2026
