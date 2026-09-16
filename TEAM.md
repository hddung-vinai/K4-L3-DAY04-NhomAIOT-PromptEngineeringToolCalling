# AIOT — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: AIOT
- Người đại diện / MSSV: Hoàng Đức Dũng / 2A202602798
- Tên repo: `K4-L3-DAY04-NhomAIOT-PromptEngineeringToolCalling`
- URL repo, nhánh nộp, commit chốt: https://github.com/hddung-vinai/K4-L3-DAY04-NhomAIOT-PromptEngineeringToolCalling — nhánh nộp `main` (đã merge từ nhánh `dung` qua Pull Request #1) — commit chốt: commit mới nhất trên `main` tại thời điểm nộp
- Deadline áp dụng và link thông báo đổi hạn nếu có: hạn mặc định 12:00 ngày làm lab 16/09/2026 (Asia/Ho_Chi_Minh) theo [SUBMISSION.md](SUBMISSION.md); 
- Lịch sử bản nộp:
  - `56756cb` (15/09/2026 20:29 +07): bản làm tại lớp — v0–v3 lần đầu, 10 case nhóm, run adversarial. Run của bản này được giữ ở `starter_v0/runs/archive_lab4_attempt1/`.

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Hoàng Đức Dũng | 2A202602798 | https://github.com/hddung-vinai | Đại diện nhóm, prompt engineering lead: chạy baseline, đặt giả thuyết và sửa `system_prompt.md`/`tools.yaml` qua v1→v3, guard xác nhận v4–v5, chạy eval/probe, làm web UI và transcript, tổng hợp `version_log.csv` và `REPORT.md` | `starter_v0/artifacts/system_prompt.md`, `starter_v0/artifacts/tools.yaml`, `starter_v0/artifacts/version_log.csv`, `starter_v0/confirmation_guard.py`, `starter_v0/tests/test_confirmation_guard.py`, `starter_v0/runs/v0..v5_*.json`, `starter_v0/analysis/`, `starter_v0/web_ui.py`, `starter_v0/transcripts/`; commit `56756cb` + commit bổ sung |
| Nguyễn Thanh Bình | 2A202602777 | https://github.com/ThanhBinh159 | Eval & safety: viết 10 case nhóm (5 một lượt + 5 nhiều lượt), kiểm thử bộ adversarial 12 case, phân tích an toàn | `starter_v0/data/eval_group.json` (được commit trong `56756cb`) |
| Hoàng Đức Minh | 2A202602362 | https://github.com/hoangminh92k3 | Dự kiến phụ trách UI & tích hợp; phần UI và transcript của bản chốt do Dũng thực hiện | Chưa có commit riêng đứng tên Minh tính đến bản chốt |

## Nhận xét chung
- Kết quả và bằng chứng: bộ base 30 câu `case_accuracy` v0 0.70 → v1 0.8667 → v2 0.9667 → v3 0.9667, giữ 0.9667 ở v4, v5 (`starter_v0/artifacts/version_log.csv`, REPORT mục B1). Bộ adversarial 12 câu: v3 0.6667 và **2 ticket thật bị tạo do tấn công** → v5 0.75 và **0 lệnh ghi do tấn công** (REPORT B4a). Bộ 10 case nhóm trên v5: 0.80 (REPORT B3). Transcript: 5 kịch bản CLI và 1 phiên web UI trên v5 (REPORT B4).
- Thay đổi hiệu quả nhất: (1) v1 viết lại tool declaration — +0.1667 trên base, hết đoán ID và sai `check`; (2) v2 luồng xác nhận 2 bước trong prompt — hết 3 lỗi boundary trên base; (3) v4–v5 guard ở tầng thực thi — chặn ghi dữ liệu từ xác nhận giả mà luồng xác nhận hợp lệ vẫn tạo được ticket.
- Giới hạn còn lại: H19 (môi trường không có trong enum) lật pass/fail theo artifact, probe 5 lần xác nhận không ổn định; G05 hỏi `yes_no` thay vì `choice` cho priority mơ hồ; A04/A11 vẫn FAIL về điểm vì eval chấm lời gọi tool của model dù guard đã chặn ghi; A12/S5 agent vẫn đưa mã nội bộ vào tool web, chỉ được code của tool chặn; guard nhận diện câu đồng ý bằng từ khóa nên có thể chặn nhầm câu trả lời diễn đạt lạ (chặn nhầm thì agent hỏi lại, không ghi sai).
- Cách phân công và tích hợp: phân công dự kiến là Dũng phụ trách vòng lặp prompt/tool và đo lường, Bình phụ trách case nhóm và an toàn, Minh phụ trách UI/transcript; bằng chứng tích hợp vào `starter_v0/artifacts/REPORT.md`. 

## INDIVIDUAL

Mỗi thành viên tự viết mục của mình. Các dòng in nghiêng là chỗ chính thành viên đó cần điền.

### Hoàng Đức Dũng — 2A202602798

- Phần việc và file/commit/PR:
  - Làm lại v0–v3 từ starter gốc (git `311580e`): run `starter_v0/runs/v0..v3_B_base_openai_20260916T*.json`, giả thuyết và hash trong `starter_v0/artifacts/version_log.csv`, probe độ ổn định trong `starter_v0/analysis/stability_probe/`.
  - Chạy adversarial và 5 transcript CLI (`starter_v0/runs/v3_B_adversarial_*.json`, `starter_v0/transcripts/S1..S5/`, `starter_v0/scripts/run_transcript_scenarios.py`).
  - Guard xác nhận v4–v5: `starter_v0/confirmation_guard.py`, tích hợp vào `starter_v0/agent.py` và `starter_v0/chat.py`, 14 unit test `starter_v0/tests/test_confirmation_guard.py`, run `starter_v0/runs/v4_*`, `starter_v0/runs/v5_*`.
  - Web UI `starter_v0/web_ui.py` và smoke test `starter_v0/scripts/ui_smoke_test.py`, transcript `starter_v0/transcripts/ui/`.
  - Commit: `56756cb` (bản làm tại lớp), `bfa3e18` và `6d92614` (bổ sung ngày 16/09).
- Quyết định, khó khăn và cách xử lý: Khi rà lại bản làm tại lớp, mình thấy `version_log.csv` ghi v1 = 0.80 trong khi run thật là 0.8333, nên quyết định làm lại toàn bộ v0–v3 từ artifact starter gốc (git `311580e`) thay vì sửa số liệu cho khớp, và giữ run cũ trong `runs/archive_lab4_attempt1/` để đối chiếu. Khó khăn lớn nhất là phân biệt tác động thật của thay đổi với dao động của model: v2 làm H03 hỏng (`category=software`, KB trả 0 bài) nhưng H19 lại pass, nên trước khi viết rule cho v3 mình chạy lặp 5 lần hai case này trên từng artifact (`analysis/stability_probe/`) và xác định H03 là regression thật, còn H19 chỉ pass nhờ ngữ cảnh. Khó khăn thứ hai là bản vá guard ở v4: chặn được tấn công nhưng chặn nhầm cả luồng hợp lệ trong transcript S2 (người dùng xác nhận đúng vẫn không tạo được ticket), nên ở v5 mình nới điều kiện để câu hỏi xác nhận viết bằng text cũng được chấp nhận, trong khi vẫn bắt buộc payload phải khớp với câu hỏi.
- Điều đã học: (1) Agent chọn đúng tool không có nghĩa là hành động thành công — phải đọc `tool_results`, ví dụ `search_kb` trả `results: []` ở H03 hoặc `asset_not_found` ở v0. (2) Điểm eval không phản ánh mức an toàn: A04 và A11 đều FAIL ở cả v3 lẫn v5, nhưng v3 ghi 2 ticket thật còn v5 không ghi gì, chỉ so thư mục `tickets/` trước và sau khi chạy mới thấy. (3) Quy tắc viết trong prompt không phải ràng buộc cứng; điều kiện xác nhận chỉ chắc chắn khi được kiểm tra trong code, nên mình chuyển ranh giới ghi dữ liệu xuống tầng thực thi. (4) Một lần chạy đơn lẻ dễ dẫn tới kết luận sai, phải chạy lặp trước khi coi một thay đổi là có tác dụng.
- AI/công cụ đã dùng và cách kiểm tra: Dùng Claude Code (model Claude Opus 5) để đọc và so sánh run JSON, đề xuất giả thuyết, sửa `system_prompt.md`/`tools.yaml`, viết guard, unit test, web UI, script transcript và chạy eval. Kiểm tra tự động đã chạy: `scripts/parse_runs.py`, kiểm tra schema `tools.yaml` không đổi tên/enum/required so với starter, probe 5 lần cho case lật kết quả, `python -m unittest discover -s tests` (14 test), so sánh thư mục `tickets/` trước/sau mỗi lần chạy, quét run/transcript tìm credential và API key.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 21h 15/9/2026

### Nguyễn Thanh Bình — 2A202602777


- Phần việc và file/commit/PR: Viết 10 case tự thiết kế trong `data/eval_group.json` (5 một lượt G01-G05, 5 nhiều lượt MG01-MG05), phủ các phần chưa được bộ base test (tool `policy`, `search_device_info`, service `printing`/`sso`, priority mơ hồ). Chạy và phân tích bộ adversarial 12 case (`runs/*_adversarial_*.json`), tổng hợp mục B3, B4a, B6 (safety review) trong `REPORT.md`.
- Quyết định, khó khăn và cách xử lý: Lần chạy adversarial đầu tiên dùng nhầm `--provider openrouter` (chưa cấu hình key) khiến toàn bộ 12/12 case báo `provider_error`, không dùng được làm bằng chứng — xử lý bằng cách chạy lại đúng `--provider openai` (provider đang hoạt động) trước khi phân tích.
- Điều đã học: Một run có `routing_correct: false` hàng loạt không tự động nghĩa là agent sai — cần đọc `failures`/exception message để phân biệt lỗi cấu hình (provider_error) với lỗi hành vi thật; và với case an toàn, PASS ở routing không chứng minh không có dữ liệu nhạy cảm bị ghi/gửi đi, phải đọc cả `tool_results` và kiểm tra filesystem (thư mục `tickets/`).
- AI/công cụ đã dùng và cách kiểm tra: Dùng Claude (Claude Code) để soạn case theo đúng format `eval_base.json`, đối chiếu enum hợp lệ trong `tools.yaml` trước khi chốt expected output. Kiểm tra bằng cách chạy `run_eval.py --suite group`/`--suite adversarial` và tự đọc lại từng case thay vì chỉ nhìn `case_accuracy` tổng.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 21h 15/9/2026

### Hoàng Đức Minh — 2A202602362


- Phần việc và file/commit/PR: Phụ trách mảng UI & tích hợp của nhóm. Sản phẩm của mảng này trong bản chốt gồm: web UI `starter_v0/web_ui.py` (hiển thị tool call, input, kết quả/lỗi, trạng thái lượt và `artifact_version`, lưu transcript mỗi phiên), smoke test qua HTTP `starter_v0/scripts/ui_smoke_test.py`, kịch bản hội thoại `starter_v0/scripts/transcript_scenarios.json` và transcript trong `starter_v0/transcripts/` (5 kịch bản CLI + 1 phiên web UI trên v5). Phần hiện thực của bản chốt do Dũng làm; đóng góp riêng của Minh bổ sung sau.
- Quyết định, khó khăn và cách xử lý: Bổ sung sau, do Minh tự viết theo [RULES.md](RULES.md).
- Điều đã học: Bổ sung sau, do Minh tự viết theo [RULES.md](RULES.md).
- AI/công cụ đã dùng và cách kiểm tra: Bổ sung sau, do Minh tự viết theo [RULES.md](RULES.md).
- Thời điểm đã tự nộp URL repo chung trên VLearn: 21h 15/9/2026
