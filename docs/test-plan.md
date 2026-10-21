# Kế hoạch kiểm thử (Test Plan)

Người phụ trách: **Bùi Tiến Thành (M4)** · Người xác nhận: **Thắng (M1)** · Issue: **M4-01** · Pha: P1, cập nhật liên tục đến P6.

Tài liệu này liệt kê các ca kiểm thử của hệ thống Personal Finance Web theo 11 nhóm của `08` §9. Cột **Mong đợi** lấy từ tài liệu thiết kế (`03`, `04`, `07`, `08`), **không** suy ra từ mã đang chạy: nếu mã và tài liệu lệch nhau thì mở Issue (mã sai là `bug`, tài liệu sai là errata trong `00` §3), không sửa kỳ vọng cho khớp mã.

## 1. Cách dùng

**Cột của mỗi bảng ca**

| Cột | Ý nghĩa |
|---|---|
| Mã ca | `TC-<nhóm>-…`; không đổi sau khi đã gán |
| Thao tác | Các bước thực hiện hoặc request gửi đi |
| Kết quả mong đợi | Hành vi và dữ liệu đúng theo tài liệu |
| Nguồn | Quy tắc (`BR-xxx`), mục tài liệu hoặc Issue làm căn cứ cho kỳ vọng |
| Issue phụ thuộc | Mã Issue (theo `08`) của phần mã mà ca này cần; thay bằng `#số` GitHub khi có |
| Trạng thái | Xem bảng trạng thái bên dưới |
| Kết quả thực tế | Chỉ điền sau khi **đã chạy**; ghi số liệu cụ thể, liên kết minh chứng |
| Người / ngày | Ai chạy và ngày chạy (`YYYY-MM-DD`) |

**Trạng thái**

| Trạng thái | Ý nghĩa |
|---|---|
| `Chưa viết test` | Mới có mô tả ca |
| `Chờ phụ thuộc` | Đã mô tả đủ, đang chờ Issue ở cột "Issue phụ thuộc" |
| `Sẵn sàng chạy` | Mã đã có, chưa chạy |
| `Đạt` | Đã chạy, kết quả thực tế khớp mong đợi; có ngày chạy |
| `Không đạt` | Đã chạy, lệch; có Issue `bug` hoặc errata đi kèm |

**Quy tắc cập nhật**

1. Không ghi `Đạt` khi chưa chạy và chưa có kết quả thực tế.
2. Khi Issue phụ thuộc được merge vào `develop`: đổi trạng thái sang `Sẵn sàng chạy`, chạy ca, điền kết quả.
3. Ca `Không đạt`: mở Issue `bug` gắn người viết nghiệp vụ, ghi mã Issue vào cột "Kết quả thực tế"; chỉ đóng khi chạy lại `Đạt`.
4. Thêm ca mới thì thêm vào cuối nhóm, không đánh lại số.
5. Mỗi ca có test tự động thì ghi đường dẫn tệp test vào cột "Kết quả thực tế" khi chạy lần đầu.

## 2. Tổng hợp

Cập nhật cột Đạt, Không đạt mỗi khi chạy ca.

| Nhóm | Nội dung | Rule | Tổng ca | Chờ phụ thuộc | Sẵn sàng | Đạt | Không đạt |
|---|---|---|---:|---:|---:|---:|---:|
| `TC-OK` | Thành công (đường chính của từng luồng Tầng 1) | IV.1 | 36 | 36 | 0 | 0 | 0 |
| `TC-BND` | Dữ liệu sai và giá trị biên | IV.1 | 26 | 26 | 0 | 0 | 0 |
| `TC-PERM` | Phân quyền, cách ly dữ liệu và bảo mật API | IV.1 | 19 | 19 | 0 | 0 | 0 |
| `TC-DB` | Ràng buộc cơ sở dữ liệu (cặp ca hợp lệ / vi phạm) | III.1 | 34 | 34 | 0 | 0 | 0 |
| `TC-RB` | Rollback của transaction ghi nhiều bảng | III.4 | 6 | 6 | 0 | 0 | 0 |
| `TC-C` | Đồng thời (hai kết nối thật chạy chồng lấn) | III.4 | 11 | 11 | 0 | 0 | 0 |
| `TC-PERF` | Dữ liệu lớn và hiệu năng (chỉ mục) | III.2, III.5 | 8 | 8 | 0 | 0 | 0 |
| `TC-MIG` | Migration có phiên bản | III.6 | 5 | 5 | 0 | 0 | 0 |
| `TC-RST` | Sao lưu và khôi phục | III.6 | 2 | 2 | 0 | 0 | 0 |
| `TC-INF` | Hạ tầng 3 VM, bảo mật vận hành, đóng gói | V, IV.3 | 15 | 15 | 0 | 0 | 0 |
| `TC-FE` | Frontend | IV.1 | 12 | 12 | 0 | 0 | 0 |
| **Tổng** | | | **174** | **174** | **0** | **0** | **0** |

## 3. Phụ thuộc cần theo dõi

Ca nào chờ Issue nào được ghi ở cột "Issue phụ thuộc". Các mốc chính:

| Cần có | Do ai | Mở khóa các ca |
|---|---|---|
| Alembic `0001` (M2-03) | Hán Minh Thành | Hạ tầng test M4-02, nhóm `DB`, `RB`, `C`, `MIG` |
| Hợp đồng API đóng băng (M1-05) | Thắng | `TC-PERM-*`, `TC-FE-*`; mã HTTP chính xác của nhóm `OK` |
| W4, W5, W7 (M1-09, M1-10, M1-11) | Thắng | `TC-OK-W4/W5/W6/W7`, `TC-RB-TX/EDIT/XFER`, `TC-C1`, `TC-C6` |
| W8, W9, W11 (M2-07, M2-08, M2-09) | Hán Minh Thành | `TC-OK-W8/W9/W11`, `TC-RB-IMP/GOAL`, `TC-C2`, `TC-C5`, `TC-C7` |
| API admin (M1-14), Q08/Q13/QA (M4-06) | Thắng, Tiến Thành | `TC-PERM-03/13/14/16`, `TC-OK-W18-*`, `TC-FE-M-04/05` |
| Bộ dữ liệu lớn (M2-12) | Hán Minh Thành | Nhóm `PERF` |
| 3 VM (M4-03, M4-10) | Tiến Thành | Nhóm `INF`, `RST` |

## 4. Các ca kiểm thử

### 4.1. `TC-OK` — Thành công (đường chính của từng luồng Tầng 1)

Rule: **IV.1**. Mỗi luồng Tầng 1 có ít nhất một ca đường chính. Mã HTTP chính xác của từng endpoint chốt theo OpenAPI sau khi M1-05 đóng băng hợp đồng; cột "Mong đợi" ở đây chỉ nêu hành vi và dữ liệu.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-OK-W1-01` | Đăng ký với email và mật khẩu hợp lệ | Tạo user; role `user` được gán (BR-A07); mật khẩu lưu bcrypt, không xuất hiện trong response; có dòng `audit_logs` cùng transaction (BR-D01) | 03 BR-A03, A07, D01; 04 W1 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-OK-W2-01` | Đăng nhập đúng email và mật khẩu | Trả access token (sống 15 phút) và refresh token (7 ngày); cập nhật `last_login` | 03 BR-A06; 04 W2.1 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-OK-W2-02` | Làm mới token bằng refresh token còn hạn | Trả cặp token mới; refresh token cũ bị thu hồi (xoay vòng) | 03 BR-A05; 04 W2.2 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-OK-W2-03` | Đăng xuất rồi dùng lại refresh token vừa đăng xuất | Đăng xuất thành công; refresh token bị thu hồi, không dùng được nữa | 04 W2.3 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-OK-W3-01` | Tạo ví thường có số dư đầu | Ví tạo xong; `current_balance = opening_balance`; có bản chụp số dư ban đầu | 03 BR-C07; 08 M1-07 | M1-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W3-02` | Tạo ví thẻ tín dụng đủ hạn mức, ngày chốt, ngày đến hạn | Tạo thành công; cho phép số dư âm trong giới hạn hạn mức | 03 BR-C03 | M1-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W3-03` | Gọi `GET /accounts` trên bộ dữ liệu nhỏ | Danh sách ví kèm tổng tài sản, tổng nợ, giá trị ròng khớp kết quả tính tay | 04 W3.2 | M1-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W3-04` | Xóa ví chưa có lịch sử; lưu trữ ví đã có giao dịch | Ví chưa có lịch sử xóa được; ví đã có lịch sử chỉ lưu trữ được | 03 BR-C04 | M1-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W4-01` | Ghi một khoản chi hợp lệ | Tạo giao dịch; số dư ví giảm đúng số tiền; `v_account_balance_check.diff = 0`; audit cùng transaction | 03 BR-T08, D01; 04 W4 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-OK-W4-02` | Ghi một khoản thu hợp lệ | Số dư ví tăng đúng số tiền; `diff = 0` | 04 W4 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-OK-W4-03` | Ghi khoản chi làm `used_percent` vượt ngưỡng cảnh báo của ngân sách, rồi chi thêm một khoản nữa | Phát đúng một cảnh báo kèm một thông báo; khoản chi sau không phát lại cùng mức | 03 BR-B07 | M1-09, M2-08 | Chờ phụ thuộc | — | — |
| `TC-OK-W4-04` | Ghi giao dịch có danh mục con, 2 nhãn hợp lệ và hóa đơn jpg | Thành công; tệp lưu ở MinIO, DB chỉ giữ khóa đối tượng | 03 BR-T11; 07 D-07 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-OK-W5-01` | Sửa số tiền, ví và loại của một giao dịch | Ảnh hưởng số dư cũ được hoàn tác, ảnh hưởng mới được áp; `diff = 0` | 03 BR-T09; 04 W5 | M1-10 | Chờ phụ thuộc | — | — |
| `TC-OK-W5-02` | Sửa giao dịch làm `used_percent` xuống dưới ngưỡng đã cảnh báo | Sự kiện cảnh báo tương ứng được nạp lại để lần sau phát lại | 03 BR-B08 | M1-10, M2-08 | Chờ phụ thuộc | — | — |
| `TC-OK-W6-01` | Xóa một giao dịch chi | Số dư ví được hoàn lại; `diff = 0` | 03 BR-T09; 04 W6 | M1-10 | Chờ phụ thuộc | — | — |
| `TC-OK-W7-01` | Chuyển khoản giữa hai ví cùng tiền tệ | Ví nguồn trừ, ví đích cộng đúng số tiền; giao dịch không tính vào thu/chi báo cáo hay ngân sách | 03 BR-X04; 04 W7 | M1-11 | Chờ phụ thuộc | — | — |
| `TC-OK-W7-02` | Chuyển khoản giữa hai ví khác tiền tệ có tỷ giá | `to_amount = round(amount × tỷ_giá, 2)`; tỷ giá được lưu | 03 BR-X02 | M1-11, M1-12 | Chờ phụ thuộc | — | — |
| `TC-OK-W8-01` | Import pha 1 với tệp CSV hợp lệ | Tạo lô `previewed` và các `import_rows`; **không** có dòng nào mới trong `transactions` | 03 BR-I05; 04 W8.1 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W8-02` | Import pha 2: xác nhận lô vừa xem trước | Số giao dịch mới = số dòng được nhập; số dư cập nhật một lần; ngân sách được đánh giá lại; có đúng 1 thông báo `import_done` | 03 BR-I07, I09, I10; 04 W8.2 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W8-03` | Import tệp `.xlsx` hợp lệ | Đọc và chuẩn hóa giống tệp CSV | 03 BR-I01 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W8-04` | Import tệp có dòng trùng: mặc định rồi chọn "vẫn nhập" | Dòng trùng được đánh dấu `duplicate` và bị bỏ qua; khi chọn "vẫn nhập" thì được ghi | 03 BR-I04 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-OK-W9-01` | Tạo ngân sách cùng các hạn mức danh mục trong một request | Tạo thành công (trigger hoãn kiểm tra tổng hạn mức lúc COMMIT) | 03 BR-B02; 04 W9.1 | M2-08 | Chờ phụ thuộc | — | — |
| `TC-OK-W9-02` | Xem tiến độ ngân sách trên bộ dữ liệu nhỏ | "Đã chi" khớp công thức F3 (chỉ chi, danh mục con tính vào cha, không tính chuyển khoản) | 03 BR-B06; Q05 | M2-08, M2-14 | Chờ phụ thuộc | — | — |
| `TC-OK-W11-01` | Góp tiền vào mục tiêu `active` từ ví cùng tiền tệ gốc | Tạo giao dịch chi danh mục `SAVING` với `source='goal'`, trừ ví, ghi `goal_contributions`, cộng `current_amount` | 03 BR-G05; 04 W11 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-OK-W11-02` | Góp số tiền làm `current_amount` bằng `target_amount` | Mục tiêu chuyển `achieved`, có `achieved_at`, có thông báo `goal_achieved` | 03 BR-G06 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-OK-W14-01` | Admin nhập tỷ giá thủ công; chạy job tỷ giá hai lần; giả lập API tỷ giá lỗi | Tỷ giá upsert theo ngày, không trùng; API lỗi thì giữ tỷ giá gần nhất và ghi `RATE_FETCH_FAILED` | 03 BR-F01; 04 W14 | M1-12 | Chờ phụ thuộc | — | — |
| `TC-OK-W15-01` | Gọi `summary`, `by-category`, `cashflow` trên bộ demo | Số liệu khớp truy vấn SQL tính tay (Q02, Q03, Q04) | 04 W15; 08 §7 | M1-13, M3-12, M2-14 | Chờ phụ thuộc | — | — |
| `TC-OK-W16-01` | Liệt kê thông báo, đếm chưa đọc, đánh dấu đã đọc một và tất cả | Số chưa đọc giảm đúng; chỉ thông báo của chính user bị ảnh hưởng | 03 BR-N02; 04 W16 | M2-10 | Chờ phụ thuộc | — | — |
| `TC-OK-W18-01` | Admin liệt kê user có tìm kiếm, lọc trạng thái và phân trang | Danh sách và tổng số khớp DB | 04 W18 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-OK-W18-02` | Admin khóa một user đang có phiên | `status='locked'` và mọi phiên bị thu hồi trong cùng transaction; có audit | 03 BR-D03 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-OK-W18-03` | Admin xem thống kê hệ thống (Q13) và `audit_logs` có lọc | Số liệu tổng hợp khớp truy vấn tính tay; log lọc và phân trang đúng | 08 §7 Q13, QA | M4-06, M1-14 | Chờ phụ thuộc | — | — |
| `TC-OK-W19-01` | Chạy job chụp số dư (00:05) hai lần liên tiếp | Mỗi ví đúng một bản chụp mỗi ngày; kết quả không đổi ở lần hai | 03 BR-C08; 08 M2-11 | M2-11 | Chờ phụ thuộc | — | — |
| `TC-OK-W19-02` | Chạy job đóng ngân sách (00:20) hai lần | Ngân sách có `end_date` đã qua chuyển `closed`; lần hai không đổi | 03 BR-B09 | M2-11 | Chờ phụ thuộc | — | — |
| `TC-OK-W19-03` | Chạy job dọn import (01:00) hai lần | Lô hết hạn được đánh dấu và dọn đúng; lần hai không đổi | 04 W8.3 | M2-11 | Chờ phụ thuộc | — | — |
| `TC-OK-W19-04` | Chạy job đối soát (01:30) khi dữ liệu đúng | `diff = 0` cho mọi ví; không có cảnh báo | 03 BR-D05 | M2-11 | Chờ phụ thuộc | — | — |
| `TC-OK-W19-05` | Cố tình sửa tay `current_balance` của một ví trong DB test rồi chạy job đối soát | Phát hiện lệch; ghi `audit_logs` `JOB_*` và gửi thông báo cho admin | 03 BR-D05; 08 M2-11 | M2-11 | Chờ phụ thuộc | — | — |

### 4.2. `TC-BND` — Dữ liệu sai và giá trị biên

Rule: **IV.1**. Mỗi ca biên gồm cặp: giá trị sát ngưỡng còn hợp lệ và giá trị ngay sau ngưỡng bị từ chối.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-BND-AMT-01` | Ghi giao dịch với số tiền 0 | 422 `INVALID_AMOUNT`; không có giao dịch, số dư giữ nguyên | 03 BR-T01 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-AMT-02` | Ghi giao dịch với số tiền âm | 422 `INVALID_AMOUNT` | 03 BR-T01 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-DATE-01` | Ghi giao dịch với ngày của ngày mai | 422 `FUTURE_DATE` | 03 BR-T02 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-DATE-02` | Ghi giao dịch với ngày hôm nay (hợp lệ) và ngày 1999-12-31 | Hôm nay được nhận; ngày trước 2000-01-01 bị từ chối | 03 BR-T02 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-PWD-01` | Đăng ký với mật khẩu 7 ký tự, rồi 8 ký tự gồm chữ và số | Bản 7 ký tự: 422 `WEAK_PASSWORD`; bản 8 ký tự: thành công | 03 BR-A03 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-BND-PWD-02` | Đăng ký với mật khẩu đúng 72 byte UTF-8, rồi 73 byte | 72 byte: thành công; 73 byte: 422 `WEAK_PASSWORD` (không được 500) | 00 E-07; 03 BR-A03 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-BND-PWD-03` | Đăng ký với mật khẩu chỉ có chữ (không có số) | 422 `WEAK_PASSWORD` | 03 BR-A03 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-BND-RATE-01` | Đăng nhập sai 5 lần liên tiếp trong 15 phút từ một IP, rồi lần thứ 6 | Lần thứ 6 bị chặn: 429 `RATE_LIMITED` | 03 BR-A09; 07 D-09 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-BND-TAG-01` | Gắn 10 nhãn rồi 11 nhãn vào một giao dịch | 10 nhãn: thành công; 11 nhãn: 422 `TOO_MANY_TAGS`; rollback hoàn toàn | 03 BR-T07 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-IMP-01` | Import tệp đúng 5.000 dòng, rồi 5.001 dòng | 5.000 dòng: xem trước thành công; 5.001 dòng: 422 `TOO_MANY_ROWS` | 03 BR-I01 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-BND-IMP-02` | Import tệp đúng 5 MB, rồi 5 MB + 1 byte | 5 MB: nhận; vượt 5 MB: 413 | 03 BR-I01 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-BND-IMP-03` | Import tệp có dòng ngày tương lai, số tiền 0, không xác định được thu/chi | Các dòng đó được đánh dấu `invalid` kèm lý do; dòng hợp lệ vẫn xem trước được | 03 BR-I03 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-BND-IMP-04` | Import tệp có đuôi khác `.csv`/`.xlsx` | Bị từ chối, không tạo lô | 03 BR-I01 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-BND-ATT-01` | Tải hóa đơn đúng 10 MB, rồi 10 MB + 1 byte | 10 MB: nhận; vượt: 413 | 03 BR-T11 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-ATT-02` | Tải hóa đơn định dạng `.exe` hoặc `.gif` | 415; không có tệp trên MinIO, không có dòng `transaction_attachments` | 03 BR-T11 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-ATT-03` | Đính kèm tệp thứ 5 rồi thứ 6 vào cùng một giao dịch | Tệp thứ 5 nhận; tệp thứ 6 bị từ chối (mã lỗi chốt theo OpenAPI) | 03 BR-T11 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-BUD-01` | Tạo ngân sách với `warn_percent` = 0, 1, 100, 101 | 0 và 101: 422; 1 và 100: thành công | 03 BR-B01 | M2-08 | Chờ phụ thuộc | — | — |
| `TC-BND-BUD-02` | Tạo ngân sách với `total_limit` = 0 hoặc `limit_amount` = 0 | 422 | 03 BR-B01 | M2-08 | Chờ phụ thuộc | — | — |
| `TC-BND-GOAL-01` | Tạo mục tiêu với `deadline` là hôm nay, rồi ngày mai | Hôm nay: 422; ngày mai: thành công | 03 BR-G01 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-BND-GOAL-02` | Góp đúng số còn thiếu, rồi góp thêm 1 đồng | Đúng số còn thiếu: thành công; thêm 1 đồng: 422 `GOAL_OVER_TARGET` | 03 BR-G04 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-BND-CUR-01` | Góp mục tiêu từ ví có tiền tệ khác tiền tệ gốc của user | 422 `CURRENCY_MISMATCH` | 03 BR-G03 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-BND-XFER-01` | Chuyển khoản cùng một ví; chuyển khoản khác tiền tệ khi thiếu tỷ giá | Cùng ví: 422; thiếu tỷ giá: 422 `RATE_UNAVAILABLE` | 03 BR-X01, X02 | M1-11 | Chờ phụ thuộc | — | — |
| `TC-BND-ACC-01` | Ghi giao dịch vào ví đã lưu trữ | 422 `ACCOUNT_ARCHIVED` | 03 BR-C05 | M1-07, M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-ACC-02` | Tạo ví thẻ tín dụng thiếu hạn mức | 422; không có ví nào được tạo | 03 BR-C03; 08 M1-07 | M1-07 | Chờ phụ thuộc | — | — |
| `TC-BND-ACC-03` | Chi trên ví thẻ cho đến khi dư nợ vượt hạn mức | 422 `CREDIT_LIMIT_EXCEEDED`; rollback | 03 BR-C03 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-BND-EMAIL-01` | Đăng ký email `A@Mail.COM` khi `a@mail.com` đã tồn tại | 409 `EMAIL_TAKEN` (email lưu chữ thường) | 03 BR-A01 | M1-06 | Chờ phụ thuộc | — | — |

### 4.3. `TC-PERM` — Phân quyền, cách ly dữ liệu và bảo mật API

Rule: **IV.1**. Ma trận tham số hóa (không đăng nhập / user / admin) × mọi endpoint Tầng 1 sinh từ `/openapi.json` và nằm trong `backend/tests/api/`. Bảng dưới liệt kê các kịch bản mà ma trận phải phủ.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-PERM-01` | Gọi mọi endpoint yêu cầu đăng nhập mà không có token | 401 cho tất cả | 07 §5; 03 §7 | M1-05, M1-06 | Chờ phụ thuộc | — | — |
| `TC-PERM-02` | Dùng access token đã hết hạn | 401 `TOKEN_EXPIRED` | 03 BR-A06 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-PERM-03` | User thường gọi mọi endpoint `/admin/*` | 403 `FORBIDDEN` | 03 BR-A08, §7 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-04` | Admin gọi các endpoint tài chính cá nhân (ví, giao dịch, import, ngân sách, mục tiêu, báo cáo) | 403; admin không thao tác dữ liệu tài chính thay user | 03 BR-D04, §7 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-05` | User A xem, sửa, xóa giao dịch của user B | 404 cho cả ba thao tác; dữ liệu B không đổi | 03 BR-T03; 07 §5 | M1-09, M1-10 | Chờ phụ thuộc | — | — |
| `TC-PERM-06` | User A ghi giao dịch với `account_id` của user B | 404 `ACCOUNT_NOT_FOUND` (không tiết lộ ví tồn tại) | 03 BR-T03 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-PERM-07` | User A dùng `category_id` riêng của user B | 404 `CATEGORY_NOT_FOUND` | 03 BR-T05 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-PERM-08` | User A gắn nhãn của user B vào giao dịch của mình | 422 `TAG_NOT_FOUND`; rollback | 03 BR-T07 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-PERM-09` | User A đọc, đánh dấu đã đọc thông báo của user B | 404 | 03 BR-N02 | M2-10 | Chờ phụ thuộc | — | — |
| `TC-PERM-10` | User A xem ticket của user B (Tầng 2) | 404; admin xem được mọi ticket | 03 BR-S01 | M4-16 | Chờ phụ thuộc | — | — |
| `TC-PERM-11` | Gửi `user_id` của người khác trong body hoặc query | Bị bỏ qua; dữ liệu luôn theo `uid` từ JWT | 03 §7; 05 §1 | M1-05 | Chờ phụ thuộc | — | — |
| `TC-PERM-12` | Admin khóa user đang đăng nhập; user đó dùng lại access token cũ và đăng nhập mới | Bị từ chối ngay (`get_current_user` đọc lại DB); đăng nhập mới: 403 `ACCOUNT_LOCKED` | 03 BR-A04; 07 §5 | M1-06, M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-13` | Admin tự khóa chính mình | Bị từ chối (BR-A08); mã lỗi chốt theo OpenAPI | 03 BR-A08 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-14` | Hạ quyền admin cuối cùng | 409 `LAST_ADMIN`; vai trò không đổi | 03 BR-A08 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-15` | Dùng lại refresh token đã bị thu hồi | 401 `TOKEN_REUSED`; mọi phiên của user bị thu hồi | 03 BR-A05 | M1-06 | Chờ phụ thuộc | — | — |
| `TC-PERM-16` | Gọi PUT/DELETE trên `/admin/audit-logs` | Không tồn tại hoặc không cho phép (404/405); log chỉ thêm | 03 BR-D02 | M1-14 | Chờ phụ thuộc | — | — |
| `TC-PERM-17` | Gửi chuỗi kiểu SQL injection vào tham số tìm kiếm và lọc (ví dụ `' OR 1=1 --`) | Truy vấn tham số hóa: không lỗi 500, không lộ dữ liệu ngoài phạm vi | 07 §6; 05 §2; rule IV.1 | M1-13, M4-06 | Chờ phụ thuộc | — | — |
| `TC-PERM-18` | Truyền tên cột sắp xếp không thuộc danh sách trắng | Bị từ chối (4xx), không chạy SQL | 05 §2 quy ước 2 | M1-13 | Chờ phụ thuộc | — | — |
| `TC-PERM-19` | Gây lỗi không lường trước (ràng buộc không có trong `ERROR_MAP`) | 500 `INTERNAL_ERROR`; response không chứa SQL, stack trace; log phía server đầy đủ | 03 §6; 08 M4-12 | M1-04 | Chờ phụ thuộc | — | — |

### 4.4. `TC-DB` — Ràng buộc cơ sở dữ liệu (cặp ca hợp lệ / vi phạm)

Rule: **III.1**. Test do M2 viết (`backend/tests/db/`, Issue M2-04, tối thiểu 25 cặp). M4 theo dõi độ phủ tại đây và kiểm tra bảng "quy tắc – nơi bảo vệ – ca hợp lệ – ca vi phạm" trong `docs/evidence/constraints.md`. Mỗi dòng: ca hợp lệ phải ghi được, ca vi phạm phải bị chính ràng buộc nêu tên từ chối.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-DB-01` | Số dư ví thường về âm | SQLSTATE 23514 `ck_accounts_non_negative` | 03 BR-C02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-02` | Dư nợ thẻ tín dụng vượt hạn mức | 23514 `ck_accounts_card_debt_limit` | 03 BR-C03 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-03` | Ví `credit_card` thiếu hạn mức, ngày chốt hoặc ngày đến hạn | 23514 `ck_accounts_card_fields` | 03 BR-C03 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-04` | Giao dịch trỏ ví của user khác | 23503 `fk_tx_account_owner` | 03 BR-T03 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-05` | Danh mục thu gắn vào khoản chi | 23503 `fk_tx_category_kind` | 03 BR-T04 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-06` | Danh mục con thuộc danh mục cha khác | 23503 `fk_tx_subcategory` | 03 BR-T06 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-07` | Giao dịch dùng danh mục riêng của user khác | Trigger `trg_tx_category_owner` từ chối (`ck_category_owner`) | 03 BR-T05 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-08` | Gắn nhãn của user khác vào giao dịch | Trigger `trg_tt_owner` từ chối (`ck_tag_owner`) | 03 BR-T07 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-09` | Hai ngân sách `active` chồng kỳ của cùng user | 23P01 `ex_budgets_no_overlap` | 03 BR-B03 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-10` | Tổng hạn mức danh mục vượt `total_limit` (kiểm tra lúc COMMIT) | Trigger hoãn từ chối khi COMMIT (`ck_budget_total_limit`) | 03 BR-B02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-11` | Giảm `total_limit` xuống dưới tổng đã phân bổ | Trigger `trg_budget_total` từ chối | 03 BR-B10 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-12` | Cùng một danh mục hai lần trong một ngân sách | 23505 `uq_budget_categories` | 03 BR-B05 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-13` | Ngân sách gắn danh mục thu | 23503 `fk_bc_category_kind` | 03 BR-B04 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-14` | Cảnh báo ngân sách cùng (hạn mức, mức độ) phát hai lần trong một kỳ | 23505 `uq_alert_once`; `ON CONFLICT DO NOTHING` bỏ qua êm | 03 BR-B07 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-15` | `current_amount` vượt `target_amount` của mục tiêu | 23514 `ck_goals_not_over` | 03 BR-G04, G09 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-16` | Mục tiêu `achieved` nhưng không có `achieved_at` | 23514 `ck_goals_achieved` | 03 BR-G06 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-17` | `goal_contributions` không khớp giao dịch (ví, số tiền, `source`) | Trigger `trg_gc_match` từ chối (`ck_link_tx_match`) | 03 BR-G05 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-18` | Sửa số tiền, ví hoặc loại của giao dịch `source='goal'`/`loan` | Trigger `trg_tx_lock_linked` từ chối (`ck_tx_locked_by_source`) | 03 BR-T10 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-19` | Xóa trực tiếp giao dịch đã gắn `goal_contributions` hoặc `loan_payments` | 23503 từ khóa ngoại `RESTRICT` | 03 BR-T10, G07; 00 E-03 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-20` | Khoản vay có dư nợ 0 nhưng `status` khác `paid_off` | Từ chối bởi `ck_loans_paid_off` | 03 BR-L04 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-21` | Hai lần trả cùng một `installment_no` của một khoản vay | 23505 `uq_loan_installment` | 03 BR-L02, L05 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-22` | Sao kê `status='paid'` nhưng không có chuyển khoản thanh toán | Từ chối bởi `ck_stmt_paid` | 03 BR-K05 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-23` | Hai sao kê cho cùng một chu kỳ của một thẻ | 23505 `uq_stmt_period` | 03 BR-K02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-24` | Phiên đăng nhập có `expires_at` không hợp lệ (ràng buộc phiên theo `02-schema.sql`) | Bị từ chối đúng ràng buộc; phiên hợp lệ ghi được | 03 BR-A06; 08 M2-04 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-25` | Đính kèm sai loại tệp hoặc quá cỡ | Từ chối bởi `ck_transaction_attachments_*` | 03 BR-T11 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-26` | Import cùng tệp (SHA-256) đã xác nhận vào cùng ví | 23505 `uq_import_confirmed_file` | 03 BR-I02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-27` | Hai giao dịch cùng `dedup_hash` trong một ví | 23505 `uq_tx_account_dedup` | 03 BR-I04 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-28` | Email viết hoa; email trùng; username trùng | `ck_users_email`; 23505 `uq_users_email`; 23505 `uq_users_username` | 03 BR-A01, A02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-29` | Số tiền giao dịch bằng 0; ngày ngoài khoảng cho phép | `ck_transactions_amount`; `ck_transactions_transaction_date` | 03 BR-T01, T02 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-30` | Chuyển khoản cùng một ví nguồn và đích; ví của user khác | `ck_transfers_diff`; `fk_transfers_from`/`fk_transfers_to` | 03 BR-X01 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-31` | Hai ví cùng tên trong một user | 23505 `uq_accounts_user_name` | 03 BR-C01 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-32` | Hai giao dịch định kỳ sinh cùng (quy tắc, ngày); hai bản chụp số dư cùng ngày; hai thông báo cùng `dedup_key` | 23505 `uq_tx_recurring_day`; `uq_balance_history_day`; `uq_notif_dedup` | 03 BR-R03, C08, N01 | M2-04 | Chờ phụ thuộc | — | — |
| `TC-DB-ERR-01` | Quét mọi tên ràng buộc trong `ERROR_MAP` và đối chiếu `pg_constraint` | Mọi tên tồn tại thật, hoặc là tên do trigger đặt (`ck_category_owner`, `ck_tag_owner`, `ck_budget_total_limit`, `ck_link_tx_match`, `ck_tx_locked_by_source`) | 00 E-03; 05 §3 | M1-04, M1-15 | Chờ phụ thuộc | — | — |
| `TC-DB-STR-01` | Chạy `psql -v ON_ERROR_STOP=1 -f db/02-schema.sql` trên PostgreSQL 17 trống | Chạy sạch; 30 bảng, 4 view, số trigger đúng `01` §7 | 00 E-05; 08 M2-01 | M2-01 | Chờ phụ thuộc | — | — |

### 4.5. `TC-RB` — Rollback của transaction ghi nhiều bảng

Rule: **III.4**. Mỗi ca kiểm tra cả ba điều sau khi lỗi: không còn bản ghi mồ côi, số dư giữ nguyên, `v_account_balance_check.diff = 0`.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-RB-TX-1` | W4: ghi giao dịch hợp lệ nhưng kèm một nhãn không hợp lệ (nhãn của user khác) | Lỗi 422; không có dòng `transactions` mồ côi; số dư ví giữ nguyên; không có audit hay cảnh báo ngân sách | 03 BR-T07, T08; 08 M1-09 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-RB-TX-2` | W4: chi vượt số dư ví | 422 `INSUFFICIENT_FUNDS`; không có giao dịch, tag, audit; số dư giữ nguyên | 03 BR-C02, T08 | M1-09 | Chờ phụ thuộc | — | — |
| `TC-RB-IMP-1` | W8 pha 2: lô có số dư cuối âm | 422 `IMPORT_FAILED`; **0** giao dịch của lô tồn tại; số dư giữ nguyên; lô `status='failed'` (ghi bằng transaction riêng) | 03 BR-I07, I09; 08 M2-07 | M2-07 | Chờ phụ thuộc | — | — |
| `TC-RB-GOAL-1` | W11: ép trigger `trg_gc_match` từ chối bản ghi `goal_contributions` | Không còn giao dịch chi; ví giữ nguyên; `current_amount` giữ nguyên | 03 BR-G05; 08 M2-09 | M2-09 | Chờ phụ thuộc | — | — |
| `TC-RB-EDIT-1` | W5: sửa giao dịch sang ví khác nhưng ví mới thiếu tiền | 422; số dư cả hai ví về đúng giá trị trước khi sửa; giao dịch giữ nguyên | 03 BR-T09 | M1-10 | Chờ phụ thuộc | — | — |
| `TC-RB-XFER-1` | W7: chuyển khoản vượt số dư ví nguồn | 422 `INSUFFICIENT_FUNDS`; không có dòng `transfers`; hai ví giữ nguyên | 03 BR-X03 | M1-11 | Chờ phụ thuộc | — | — |

### 4.6. `TC-C` — Đồng thời (hai kết nối thật chạy chồng lấn)

Rule: **III.4**. Bản tự động: hai thread, mỗi thread một kết nối, dùng `threading.Barrier(2)` để cả hai gọi cùng lúc; chạy ổn định 20 lần liên tiếp. Sau mỗi ca kiểm tra `v_account_balance_check.diff = 0`. C3, C4, C8 thuộc Tầng 2.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-C1` | Hai khoản chi 70.000 cùng lúc trên ví có 100.000 | Một giao dịch thành công, một nhận 422 `INSUFFICIENT_FUNDS` và rollback; số dư cuối 30.000; chỉ 1 dòng trong `transactions` | 03 §5 C1 | M1-09, M4-02 | Chờ phụ thuộc | — | — |
| `TC-C1-MAN` | Chạy tay C1 bằng hai phiên `psql` theo kịch bản `03` §5; quay video/ghi log | Phiên 2 bị chặn đến khi phiên 1 COMMIT, rồi nhận 23514 `ck_accounts_non_negative`; số dư 30.000 | 03 §5 | M2-01 | Chờ phụ thuộc | — | — |
| `TC-C2` | Gửi hai request xác nhận import cùng một lô gần như đồng thời | Một request 201, một 409 `BATCH_NOT_PENDING`; số giao dịch = số dòng hợp lệ | 03 §5 C2; BR-I08 | M2-07, M4-02 | Chờ phụ thuộc | — | — |
| `TC-C3` | Thanh toán cùng một sao kê thẻ từ hai tab (Tầng 2) | Một thành công, một 409 `STATEMENT_ALREADY_PAID`; đúng một dòng `transfers purpose='card_payment'` | 03 §5 C3; BR-K04 | M2-18 | Chờ phụ thuộc | — | — |
| `TC-C4` | Chạy hai instance job định kỳ cùng lúc (Tầng 2) | Mỗi (quy tắc, ngày) đúng một giao dịch; số dư chỉ đổi một lần | 03 §5 C4; BR-R03 | M2-18 | Chờ phụ thuộc | — | — |
| `TC-C5` | Hai lần góp 80.000 vào mục tiêu còn thiếu 100.000 | Lần đầu thành công; lần sau thấy còn 20.000 nên 422 `GOAL_OVER_TARGET`; `current_amount = 80.000` | 03 §5 C5 | M2-09, M4-02 | Chờ phụ thuộc | — | — |
| `TC-C6` | Chuyển A→B và B→A cùng lúc | Cả hai thành công tuần tự; không có lỗi `40P01`; tổng tiền hai ví không đổi | 03 §5 C6; BR-X05 | M1-11, M4-02 | Chờ phụ thuộc | — | — |
| `TC-C7` | Hai request tạo ngân sách chồng kỳ | Một thành công, một 409 `BUDGET_OVERLAP` | 03 §5 C7; BR-B03 | M2-08, M4-02 | Chờ phụ thuộc | — | — |
| `TC-C8` | Hai request trả cùng một kỳ vay (Tầng 2) | Một thành công, một 409 `INSTALLMENT_ALREADY_PAID`; dư nợ giảm đúng một lần | 03 §5 C8; BR-L05 | M1-16 | Chờ phụ thuộc | — | — |
| `TC-C-STAB` | Chạy lặp C1, C2, C5, C6, C7 tự động 20 lần liên tiếp | Cả 20 lần cùng kết quả; không có ca chập chờn (flaky) | 08 M4-09 | M4-09 | Chờ phụ thuộc | — | — |
| `TC-C-RETRY` | Gây xung đột 40001/40P01 có chủ đích | Bộ `retry_on_conflict` thử lại tối đa 3 lần; hết lượt trả 503 `TRY_AGAIN` | 05 §2 quy ước 4; 03 §6 | M1-04 | Chờ phụ thuộc | — | — |

### 4.7. `TC-PERF` — Dữ liệu lớn và hiệu năng (chỉ mục)

Rule: **III.2, III.5**. Ghi trung thực kể cả khi chỉ mục không cải thiện. Mỗi trạng thái chạy ≥ 5 lần lấy trung vị; ghi quy mô dữ liệu, môi trường, tham số.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-PERF-DATA-01` | Nạp bộ dữ liệu lớn (`gen_data.py --profile large`) và xuất thống kê số dòng | ≥ 3 bảng ≥ 10.000 dòng; `transactions` ≥ 100.000 dòng; có `docs/evidence/row-counts.md` | rule III.2; 08 M2-12 | M2-12 | Chờ phụ thuộc | — | — |
| `TC-PERF-DATA-02` | Chạy `v_account_balance_check` trên bộ lớn | `diff = 0` cho mọi ví | 08 M2-12 | M2-12 | Chờ phụ thuộc | — | — |
| `TC-PERF-P1-A` | P1 trước: đo truy vấn tính "đã chi" ngân sách (W4-Q8) khi bỏ `ix_tx_expense_cat` | Có `EXPLAIN (ANALYZE, BUFFERS)`, trung vị ≥ 5 lần | 08 M2-15 | M2-15 | Chờ phụ thuộc | — | — |
| `TC-PERF-P1-B` | P1 sau: cùng truy vấn, có `ix_tx_expense_cat` | Kế hoạch và thời gian được ghi; nhận xét trung thực | 08 M2-15 | M2-15 | Chờ phụ thuộc | — | — |
| `TC-PERF-P2-A` | P2 trước: danh sách giao dịch Q01 khi bỏ `ix_tx_user_date` | Có `EXPLAIN (ANALYZE, BUFFERS)`, trung vị ≥ 5 lần | 08 M2-15 | M2-15 | Chờ phụ thuộc | — | — |
| `TC-PERF-P2-B` | P2 sau: Q01 có `ix_tx_user_date` | Kế hoạch và thời gian được ghi; nhận xét trung thực | 08 M2-15 | M2-15 | Chờ phụ thuộc | — | — |
| `TC-PERF-REPRO` | M1 chạy lại P1 và P2 trên môi trường riêng | Cùng xu hướng với kết quả của M2 | 08 M2-15 (người kiểm tra M1) | M2-15 | Chờ phụ thuộc | — | — |
| `TC-PERF-Q-ALL` | Chạy mọi truy vấn Q01–Q13, QA trên bộ lớn | Mọi truy vấn chạy được, không timeout | 08 M2-13 | M2-13 | Chờ phụ thuộc | — | — |

### 4.8. `TC-MIG` — Migration có phiên bản

Rule: **III.6**. Kiểm thử trên DB đã có dữ liệu lớn, sao lưu trước khi chạy.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-MIG-0001` | So sánh DB dựng bằng `alembic upgrade head` với DB dựng từ `02-schema.sql` | Cùng danh sách bảng, cột, ràng buộc, chỉ mục | 00 D-06; 08 M2-03 | M2-03 | Chờ phụ thuộc | — | — |
| `TC-MIG-0001-D` | `alembic downgrade base` từ revision 0001 | Chạy được, không lỗi | 08 M2-03 | M2-03 | Chờ phụ thuộc | — | — |
| `TC-MIG-1` | Chạy migration 0002 (ví dụ thêm `transactions.merchant_norm` kèm backfill theo lô) trên DB có dữ liệu | Số dòng trước = sau; không có `NULL` ngoài dự kiến; truy vấn cũ vẫn đúng | 08 M2-16 | M2-16 | Chờ phụ thuộc | — | — |
| `TC-MIG-1-D` | `alembic downgrade` từ 0002 về 0001 trên cùng DB | Về đúng schema 0001; dữ liệu cũ không mất | 08 M2-16 | M2-16 | Chờ phụ thuộc | — | — |
| `TC-MIG-1-DOC` | Đối chiếu ERD và từ điển sau migration | Tài liệu đã cập nhật trong cùng PR | 00 D-06 | M2-16 | Chờ phụ thuộc | — | — |

### 4.9. `TC-RST` — Sao lưu và khôi phục

Rule: **III.6**. M2 thực hiện, M4 dựng môi trường và đối chiếu.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-RST-0` | Chạy `backup.sh` (pg_dump định dạng custom + sao lưu bucket MinIO) | Có tệp sao lưu; cron trên VM3 chạy đúng lịch | 08 M2-17, M4-11 | M2-17, M4-11 | Chờ phụ thuộc | — | — |
| `TC-RST-1` | Chạy `restore.sh` sang DB/VM khác | Số dòng từng bảng khớp 100%; `v_account_balance_check.diff = 0`; Q02 cho cùng kết quả trước và sau; số đối tượng MinIO khớp | rule III.6; 08 M2-17 | M2-17, M4-11 | Chờ phụ thuộc | — | — |

### 4.10. `TC-INF` — Hạ tầng 3 VM, bảo mật vận hành, đóng gói

Rule: **V, IV.3**. Mỗi ca có ảnh chụp hoặc log lưu trong `docs/deploy.md` hoặc `docs/evidence/`.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-INF-01` | Từ VM1: `nc -zv VM3 5432` | Thất bại (Frontend không nối DB) | 07 §8.2 | M4-03 | Chờ phụ thuộc | — | — |
| `TC-INF-02` | Từ VM2: `nc -zv VM3 5432` và `nc -zv VM3 9000` | Cả hai thành công | 07 §8.2 | M4-03 | Chờ phụ thuộc | — | — |
| `TC-INF-03` | Từ Internet: thăm dò VM2 và VM3 | Mọi cổng bị chặn | 07 §8.2 | M4-03 | Chờ phụ thuộc | — | — |
| `TC-INF-04` | Từ VM1 tới VM2: cổng 8000 và một cổng khác | 8000 qua được; cổng khác bị chặn | 07 §8.2 | M4-03 | Chờ phụ thuộc | — | — |
| `TC-INF-05` | Từ ngoài VM3: thăm dò cổng console MinIO 9001 | Không truy cập được (không publish ra ngoài VM3) | 07 §8.2; 08 M4-12 | M4-03, M4-12 | Chờ phụ thuộc | — | — |
| `TC-INF-06` | Khởi động lại VM3 sau khi ghi dữ liệu DB và tải hóa đơn | Dữ liệu DB và tệp trên MinIO còn nguyên | 08 M4-10; 07 §8.5 | M4-10 | Chờ phụ thuộc | — | — |
| `TC-INF-07` | Chạy migration trên VM2: `docker compose run --rm api alembic upgrade head` | Schema dựng đúng trên VM3; extension `btree_gist` có sẵn | 07 §8.3; 00 E-05 | M4-10 | Chờ phụ thuộc | — | — |
| `TC-INF-08` | Container `worker` chạy trên VM2 và một job chạy đúng lịch | Job ghi `audit_logs` `JOB_*`; chạy hai instance vẫn an toàn | 00 D-08; 08 M2-11 | M4-10 | Chờ phụ thuộc | — | — |
| `TC-INF-09` | Quét bí mật: `git grep -nEi "password|secret|apikey"` trên mã và lịch sử | Không có bí mật thật trong repo hay lịch sử; `.env` không được commit | 07 §6; 08 M4-12 | M4-12 | Chờ phụ thuộc | — | — |
| `TC-INF-10` | Kiểm tra CORS với origin lạ và origin hợp lệ | Chỉ origin của VM1 hoặc tên miền được phép | 08 M4-12 | M4-12 | Chờ phụ thuộc | — | — |
| `TC-INF-11` | Kiểm tra header và nội dung lỗi của response 4xx/5xx | Không lộ stack trace hay chi tiết SQL | 08 M4-12; 03 §6 | M4-12 | Chờ phụ thuộc | — | — |
| `TC-INF-12` | Build Docker image backend, frontend; kiểm tra `.env.example` mỗi thành phần | Build thành công; có `.env.example` cho từng thành phần; container chạy bằng user không phải root | rule IV.3; 07 §8.3, §8.4 | M4-10 | Chờ phụ thuộc | — | — |
| `TC-INF-13` | Thành viên khác (không phải M4) dựng lại hệ thống theo `docs/deploy.md` | Dựng được; biên bản ghi trên Issue | 08 M1-17, M4-10 | M4-10 | Chờ phụ thuộc | — | — |
| `TC-INF-14` | (Điểm cộng) Truy cập bằng tên miền; chuyển HTTP → HTTPS | Chứng chỉ hợp lệ; chuyển hướng đúng; không lỗi mixed content | 08 M4-14 | M4-14 | Chờ phụ thuộc | — | — |
| `TC-INF-15` | (Điểm cộng) Gắn tag `v*` và kích hoạt `deploy.yml` | Ít nhất một lần deploy tự động thành công và có ghi lại | 07 §9; 08 M4-15 | M4-15 | Chờ phụ thuộc | — | — |

### 4.11. `TC-FE` — Frontend

Rule: **IV.1**. Phần tự động chạy bằng `npm test` (Vitest + Testing Library). Phần thủ công ghi theo ca, chạy trên bản 3 VM.

| Mã ca | Thao tác | Kết quả mong đợi | Nguồn | Issue phụ thuộc | Trạng thái | Kết quả thực tế | Người / ngày |
|---|---|---|---|---|---|---|---|
| `TC-FE-A-01` | Test `DataState` với dữ liệu: đang tải, rỗng, lỗi, có dữ liệu | Mỗi trạng thái hiển thị đúng thành phần | 07 §6; 08 M3-13 | M3-02, M3-13 | Chờ phụ thuộc | — | — |
| `TC-FE-A-02` | Test `errorMessages.js` với mọi `error.code` trong `03` §3 và §6 | Mỗi mã có thông báo tiếng Việt; mã lạ có thông báo mặc định | 07 §6 | M3-02 | Chờ phụ thuộc | — | — |
| `TC-FE-A-03` | Test định dạng tiền với chuỗi thập phân (`"85000.00"`) và các giá trị lớn, nhỏ | Hiển thị đúng; không cộng trừ tiền bằng `Number` | 07 §5 (Tiền) | M3-13 | Chờ phụ thuộc | — | — |
| `TC-FE-A-04` | Test reducer quyết định import (bỏ qua, vẫn nhập, chọn danh mục) | Trạng thái cập nhật đúng với từng hành động | 08 M3-13 | M3-07, M3-13 | Chờ phụ thuộc | — | — |
| `TC-FE-A-05` | Test route guard theo role | User thường không vào được `/admin`; chưa đăng nhập bị chuyển về trang đăng nhập | 08 M3-02, M4-04 | M3-02, M4-04 | Chờ phụ thuộc | — | — |
| `TC-FE-A-06` | Test interceptor Axios khi gặp 401 | Tự làm mới token một lần; thất bại thì đăng xuất, không lặp vô hạn | 08 M3-02 | M3-02 | Chờ phụ thuộc | — | — |
| `TC-FE-M-01` | Thủ công: màn hình tạo giao dịch khi vượt số dư | Hiển thị thông báo `INSUFFICIENT_FUNDS` tiếng Việt; số dư trên màn hình khớp DB | 08 M3-05 | M3-05 | Chờ phụ thuộc | — | — |
| `TC-FE-M-02` | Thủ công: import 3 bước, nhấn "Xác nhận" hai lần liên tiếp | Chỉ một lần thành công; lần kia hiển thị `BATCH_NOT_PENDING` | 08 M3-07; 03 C2 | M3-07 | Chờ phụ thuộc | — | — |
| `TC-FE-M-03` | Thủ công: mỗi màn hình dữ liệu khi API chậm, trả rỗng, trả lỗi | Có đủ ba trạng thái đang tải, rỗng, lỗi | rule IV.1; 08 M3-01 | M3-03…M3-11 | Chờ phụ thuộc | — | — |
| `TC-FE-M-04` | Thủ công: giao diện quản trị với tài khoản user thường và admin | User thường không vào được `/admin`, API trả 403; admin dùng được mọi trang | 08 M4-04 | M4-04 | Chờ phụ thuộc | — | — |
| `TC-FE-M-05` | Thủ công: trang thống kê và đối soát số dư của admin | Số liệu khớp truy vấn SQL trực tiếp trên bộ demo; đủ ba trạng thái | 08 M4-05 | M4-05, M4-06 | Chờ phụ thuộc | — | — |
| `TC-FE-M-06` | Thủ công: hai báo cáo R1 (theo danh mục) và R2 (dòng tiền) | Số trên biểu đồ khớp Q03, Q04 trên bộ demo | 08 M3-11 | M3-11 | Chờ phụ thuộc | — | — |

## 5. Truy vết yêu cầu `rule.md` → nhóm ca

| Yêu cầu (mục rule) | Nhóm ca | Minh chứng |
|---|---|---|
| III.1 Ràng buộc có ca hợp lệ và không hợp lệ | `TC-DB` | `docs/evidence/constraints.md` |
| III.2 Quy mô dữ liệu | `TC-PERF-DATA` | `docs/evidence/row-counts.md` |
| III.4 Transaction, rollback và đồng thời | `TC-RB`, `TC-C` | `docs/evidence/concurrency-C*.md` |
| III.5 Chỉ mục và EXPLAIN | `TC-PERF-P1`, `TC-PERF-P2` | `docs/evidence/perf-P1.md`, `perf-P2.md` |
| III.6 Migration, sao lưu, khôi phục | `TC-MIG`, `TC-RST` | `docs/evidence/migration-0002.md`, `restore.md` |
| IV.1 Kiểm tra đầu vào, phân quyền, tham số hóa, không lộ bí mật | `TC-OK`, `TC-BND`, `TC-PERM`, `TC-FE` | Kết quả `pytest` và `npm test` |
| IV.3 Đóng gói Docker, `.env.example` | `TC-INF-12` | `docs/deploy.md` |
| V Hạ tầng 3 VM | `TC-INF` | Ảnh chụp và log trong `docs/deploy.md` |

## 6. Nhật ký lỗi phát hiện khi kiểm thử

Mỗi lỗi là một Issue gắn nhãn `bug`; bảng này là mục lục.

| Issue | Ca phát hiện | Mô tả ngắn | Người viết nghiệp vụ | Mức độ | Trạng thái |
|---|---|---|---|---|---|
| — | — | Chưa có lỗi nào được ghi nhận | — | — | — |

Điều kiện qua pha P4 (`08` §2): không còn `bug` mức cao.

## 7. Lịch sử thay đổi

| Ngày | Người | Thay đổi |
|---|---|---|
| TODO | Bùi Tiến Thành | Tạo khung kế hoạch kiểm thử (M4-01) |
