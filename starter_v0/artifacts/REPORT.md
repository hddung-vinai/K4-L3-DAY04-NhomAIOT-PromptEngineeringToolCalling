# Day 04 Lab v3 Report — Trợ lý AI của nhóm

- Lĩnh vực tự chọn:
- Nhiệm vụ và luồng cơ bản đã chốt trước v0:
- Đường dẫn bộ 30 câu cơ bản và 12 câu an toàn; commit chốt bộ trước v0:
- Chức năng mở rộng ngoài luồng cơ bản (nếu có; tối đa 10 trong tổng 100 điểm):

## Team

- Team:
- Thành viên và INDIVIDUAL: [TEAM.md](../../TEAM.md)
- Members:
- Provider/model:

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

> Viết 1–2 câu mô tả capability và giới hạn của agent.

**Link dùng thử:**

> URL:

## A2. Tool agent có

| Tool | Chức năng | Core / optional / team-built |
|---|---|---|
| clarify | Hỏi bổ sung hoặc xác nhận | core |
|  |  |  |

## A3. Câu hỏi mẫu

1.
2.
3.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Cải thiện version | Fallback run/transcript |
|---|---|---|---|
|  |  |  |  |

# PHẦN B — Chi tiết và evidence

Metric chỉ hợp lệ khi `provider_error_cases == 0`, `measured_cases ==
total_cases`, và tool result error đã được review thủ công.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric | Before | After | Run file |
|---|---|---|---|---:|---:|---|
| v0 | baseline | Chạy bản starter chưa sửa để lấy lỗi gốc. | case_accuracy / wrong_tool failures |  | 0.70 / 3 | `runs/v0_B_base_openrouter_20260915T194643913280.json` |
| v1 | Sửa `artifacts/tools.yaml`: làm rõ ranh giới `check_service_status`, `inspect_device`, `lookup_user`, `search_kb`, `format_incident_report`; chuyển description sang tiếng Việt để khớp ngôn ngữ eval. Không sửa `system_prompt.md`. | Nếu tool description nêu rõ service-wide vs asset-specific vs employee directory và yêu cầu `check` cụ thể, agent sẽ giảm chọn nhầm tool và nhầm argument do routing. | case_accuracy / wrong_tool failures | 0.70 / 3 | 0.80 / 0 | `runs/v1_B_base_openrouter_20260915T195624602380.json` |
| v2 |  |  |  |  |  |  |
| v3 |  |  |  |  |  |  |

Ghi chú v1: run hợp lệ theo điều kiện của README (`provider_error_cases == 0`,
`measured_cases == total_cases == 30`). Sau v1 vẫn còn 6 lỗi: `missing_info` = 3
và `wrong_boundary` = 3, đúng phạm vi để xử lý ở v2/v3.

## B2. Failure analysis

| Case ID | Failure type | Actual calls | What failed | Fix |
|---|---|---|---|---|
| H04_user_routing | wrong_tool | v0 gọi `lookup_user({"employee_id":"EMP-1003"})` rồi gọi thêm `inspect_device({"asset_id":"EMP-1003"})`. | Agent nhầm employee ID thành asset ID và gọi dư `inspect_device`. | Trong `lookup_user.description`, nêu rõ EMP-* dùng cho directory record và danh sách assigned assets là đủ nếu user không yêu cầu inspect asset cụ thể. Trong `inspect_device.description`, cấm truyền EMP-* vào `asset_id`. Kết quả v1: case pass. |
| H13_parallel_status_and_device | wrong_tool / wrong_arg_value | v0 gọi `check_service_status(vpn, production)` và `inspect_device({"asset_id":"LT-204"})` nhưng thiếu `check:"vpn"`. | Agent biết cần inspect device nhưng không map yêu cầu "VPN trên LT-204" thành diagnostic area `vpn`. | Trong `inspect_device.description`, thêm luật nếu user hỏi VPN/network/security/hardware/software thì đặt `check` đúng nhóm đó. Kết quả v1: case pass. |
| H17_triage_with_three_sources | wrong_tool / wrong_arg_value | v0 gọi `inspect_device({"asset_id":"LT-318","check":"all"})`, `check_service_status(vpn, production)`, `search_kb(category vpn)`. | Agent gọi đúng nhóm tool nhưng inspect device quá rộng, chưa chọn `check:"vpn"` cho triage VPN. | Cùng sửa đổi ở `inspect_device.description` về `check` cụ thể; `search_kb` và `check_service_status` cũng được mô tả lại để phân biệt how-to, status và device diagnostic. Kết quả v1: case pass. |

## B3. Team eval cases

Liệt kê đúng 10 case tự viết: 5 single-turn và 5 multi-turn.

| Case ID | What it tests | Expected behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live chat evidence

| Scenario/turn | Version | Tool calls + args | Transcript/run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B4a. Adversarial evidence

Phân tích ít nhất 3 cases. Automatic score không chứng minh rằng không có dữ
liệu bị ghi hoặc gửi ra ngoài; cần kiểm tra cả `tool_results` và filesystem.

| Attack case | Expected boundary | Actual calls | Sensitive write/exfiltration occurred? | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Optional và bonus tool evidence

Phần này chỉ điền khi nhóm có sử dụng optional tool hoặc tự xây bonus tool.
Phần chung tối đa 90 điểm; mở rộng tối đa 10 điểm, tổng tối đa 100. Công cụ tự xây để phục vụ luồng cơ bản của lĩnh vực mới thuộc phần chung. `policy`,
`create_ticket` và `search_device_info` là tool có sẵn, không phải tool mới do
nhóm tự xây.

| Category | Evidence file | What worked | Risk / guardrail |
|---|---|---|---|
| Optional built-in |  |  |  |
| External search + privacy boundary |  |  |  |
| Bonus: tool mới do nhóm tự xây |  |  |  |

## B6. Safety review

- Agent có bao giờ tự đoán asset ID hoặc employee ID không?
- Trace/ticket có chứa password, MFA code, token hay dữ liệu thật không?
- Ticket chỉ được tạo sau xác nhận rõ chưa?
- Tool result error nào cần review thủ công?

## B7. Technical reflection

- Fix v1 không sửa `system_prompt.md`; prompt vẫn là starter để cô lập tác động của tool declaration.
- Fix v1 thuộc `tools.yaml`: mô tả rõ ranh giới giữa service status, device inspection, user lookup, KB search, report formatting, policy và ticket creation; đồng thời dùng tiếng Việt để khớp ngôn ngữ case eval.
- Không thể chỉ nhìn automatic score: routing PASS chưa đủ nếu tool result trả lỗi hoặc gọi dư tool. Ví dụ v0 ở H04 gọi thêm `inspect_device` với `asset_id="EMP-1003"` và tool trả `asset_not_found`; cần đọc cả `actual_tool_calls` và `tool_results`.
- Vòng tiếp theo nên xử lý `wrong_boundary`: ticket không được tạo trước khi xác nhận payload hiện tại; confirmation cũ phải mất hiệu lực khi user đổi summary/priority/impact.

# PHẦN C — Checkout trước khi nộp

Phần này được hoàn thành sau khi toàn bộ code, evidence và report đã được đưa
lên repository chung. Nhóm chưa nên nộp link trên VLearn nếu reflection hoặc
commit evidence của bất kỳ thành viên nào còn thiếu.

## C1. Nhận xét chung của nhóm

Hoàn thành mục nhận xét chung trong [TEAM.md](../../TEAM.md). Dẫn tới các run, file và commit trong phần B để chứng minh kết quả. Ghi dưới đây đường dẫn tới mục đã hoàn thành:

> Link:

## C2. INDIVIDUAL của từng thành viên

Mỗi người tự viết và commit mục INDIVIDUAL của mình trong [TEAM.md](../../TEAM.md), nêu phần việc, bằng chứng kỹ thuật và điều đã học. Không yêu cầu chép lại cùng nội dung ở đây. Mỗi mục phải có file/commit/PR thật, không dùng commit tự đánh giá làm bằng chứng kỹ thuật duy nhất.

> Link các mục INDIVIDUAL:

## C3. Final checkout

Chỉ nộp bài khi mọi mục dưới đây đã được kiểm tra trên branch cuối cùng của
repository chung:

- [ ] `TEAM.md` có đủ họ tên, MSSV, GitHub username và vai trò.
- [ ] Mỗi thành viên có ít nhất một commit trong lịch sử branch nộp bài.
- [ ] Phần nhận xét chung trong TEAM.md đã hoàn thành và có evidence.
- [ ] Mỗi thành viên đã tự viết và commit mục INDIVIDUAL trong TEAM.md.
- [ ] `system_prompt.md`, `tools.yaml`, version log, runs, eval, transcript, UI
      và report đã có trong repository.
- [ ] Không có `.env`, API key, token, dữ liệu thật, cache hoặc generated ticket.
- [ ] Nhóm trưởng và mọi thành viên đã thống nhất đúng một URL repository chung.
- [ ] Nhóm trưởng và mọi thành viên sẽ nộp cùng URL đó trên VLearn.

**URL repository chung dùng để nộp:**

> URL:

- [ ] Tên repo đúng mẫu K4-L3-DAY04-HoVaTen-MSSV-PromptEngineeringToolCalling.
- [ ] Kiểm tra deadline và bản chốt theo [SUBMISSION.md](../../SUBMISSION.md).
