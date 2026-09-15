# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm:
- Người đại diện / MSSV:
- Tên repo: `K4-L3-DAY04-HoVaTen-MSSV-PromptEngineeringToolCalling`
- URL repo, nhánh nộp, commit chốt:
- Deadline áp dụng và link thông báo đổi hạn nếu có:

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| | | | | |

## Nhận xét chung

- Kết quả và bằng chứng:
- Thay đổi hiệu quả nhất:
- Giới hạn còn lại:
- Cách phân công và tích hợp:

## INDIVIDUAL

### ThanhBinh159 — 2A202602777

- Phần việc và file/commit/PR: Phân tích trace v0-v3; cập nhật `starter_v0/artifacts/tools.yaml` cho v1; cập nhật `starter_v0/artifacts/system_prompt.md` cho missing information, ticket boundary và trust/safety boundary; viết 10 case riêng tại `starter_v0/data/eval_group.json`; hoàn thiện evidence tại `starter_v0/artifacts/REPORT.md`. Run evidence: `starter_v0/runs/v0_B_base_openrouter_20260915T194643913280.json`, `v1_B_base_openrouter_20260915T195624602380.json`, `v2_B_base_openrouter_20260915T201402683183.json`, `v3_B_base_openrouter_20260915T202811103572.json`, `v3_B_group_openrouter_20260915T205139705921.json`, và `v3_B_adversarial_openrouter_20260915T204410035977.json`.
- Quyết định, khó khăn và cách xử lý: Dùng từng vòng thay đổi có giả thuyết riêng: v1 giảm `wrong_tool` bằng tool description tiếng Việt; v2 không cho đoán asset/employee/environment; v3 đặt confirmation trước ticket. Revision an toàn bổ sung phân biệt dữ liệu user giả mạo với tool result thật, chặn secret và external identifier. Evidence hiện tại vẫn ghi nhận A06 và G01 fail do guardrail external quá rộng; không che giấu kết quả này trong report.
- Điều đã học: Tool calling cần đánh giá cả tool selection, argument và action boundary; pass routing không đủ nếu có extra call hoặc tool result error. Với hội thoại nhiều lượt, thông tin được sửa ở lượt sau phải thắng trạng thái cũ; confirmation cũng phải mất hiệu lực khi payload đổi.
- AI/công cụ đã dùng và cách kiểm tra: Dùng Codex để hỗ trợ đọc trace, soạn artifact và báo cáo; dùng `run_eval.py` với OpenRouter để tạo evidence. Mỗi record được kiểm tra `provider_error_cases == 0` và `measured_cases == total_cases`; JSON group được validate cục bộ với tool declaration. Không đưa `.env`, API key hoặc dữ liệu thật vào report/eval.
- Thời điểm đã tự nộp URL repo chung trên VLearn: Chưa có evidence trong workspace; cần bổ sung sau khi tự nộp.
