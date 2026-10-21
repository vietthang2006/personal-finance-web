# Thư mục minh chứng (`docs/evidence/`)

Nơi lưu minh chứng cho các ca trong `docs/test-plan.md` và các yêu cầu của `rule.md`. Mỗi tệp do người ghi ở cột "Người làm" tạo khi hoàn thành ca tương ứng.

## 1. Danh mục tệp

| Tệp | Nội dung | Ca / Issue | Người làm | Trạng thái |
|---|---|---|---|---|
| `constraints.md` | Bảng "quy tắc – nơi bảo vệ – ca hợp lệ – ca vi phạm" | `TC-DB-*`, M2-04 | Hán Minh Thành | Chưa có |
| `row-counts.md` | Số dòng mọi bảng và thời gian nạp của bộ lớn | `TC-PERF-DATA-*`, M2-12 | Hán Minh Thành | Chưa có |
| `perf-P1.md` | EXPLAIN trước/sau của truy vấn "đã chi" ngân sách | `TC-PERF-P1-*`, M2-15 | Hán Minh Thành | Chưa có |
| `perf-P2.md` | EXPLAIN trước/sau của danh sách giao dịch Q01 | `TC-PERF-P2-*`, M2-15 | Hán Minh Thành | Chưa có |
| `migration-0002.md` | Kế hoạch, lệnh, kiểm tra trước/sau, thử `downgrade` | `TC-MIG-*`, M2-16 | Hán Minh Thành | Chưa có |
| `restore.md` | Lệnh, thời gian, bảng đối chiếu khôi phục | `TC-RST-*`, M2-17, M4-11 | Hán Minh Thành + Tiến Thành | Chưa có |
| `concurrency-C1.md` | Kịch bản, lệnh, kết quả, ảnh/video C1 (tự động và hai phiên `psql`) | `TC-C1`, `TC-C1-MAN`, M4-09 | Bùi Tiến Thành | Chưa có |
| `concurrency-C2.md` | Như trên cho C2 | `TC-C2`, M4-09 | Bùi Tiến Thành | Chưa có |
| `concurrency-C5.md` | Như trên cho C5 | `TC-C5`, M4-09 | Bùi Tiến Thành | Chưa có |
| `concurrency-C6.md` | Như trên cho C6 | `TC-C6`, M4-09 | Bùi Tiến Thành | Chưa có |
| `concurrency-C7.md` | Như trên cho C7 | `TC-C7`, M4-09 | Bùi Tiến Thành | Chưa có |
| `network-check.md` | Kết quả `nc -zv` giữa các VM, ảnh chụp thăm dò cổng | `TC-INF-01…05`, M4-03 | Bùi Tiến Thành | Chưa có |
| `security-checklist.md` | Checklist bảo mật vận hành, có chữ ký của M1 | `TC-INF-05`, `TC-INF-09…11`, M4-12 | Bùi Tiến Thành | Chưa có |

## 2. Mẫu một tệp minh chứng

```markdown
# <Tên minh chứng> — <mã ca TC-…>

- Ngày chạy: YYYY-MM-DD
- Người chạy: <họ tên>
- Môi trường: <máy / VM, phiên bản PostgreSQL, commit hash>
- Issue / PR liên quan: #<số>

## Thao tác
Các lệnh đã chạy, theo thứ tự (chép nguyên văn).

## Kết quả mong đợi
Chép từ `docs/test-plan.md`.

## Kết quả thực tế
Đầu ra, số liệu, ảnh chụp (đặt trong `docs/evidence/img/`).

## Kết luận
Đạt / Không đạt; nếu không đạt thì ghi Issue `bug`.
```

## 3. Quy ước

1. Chỉ lưu kết quả thật. Không chép kết quả mong đợi vào mục kết quả thực tế.
2. Ảnh chụp đặt trong `docs/evidence/img/`; không chụp màn hình chứa mật khẩu, khóa hoặc `.env`.
3. Tệp dữ liệu lớn (dump, video) không commit; ghi đường dẫn lưu và mã băm SHA-256 vào tệp minh chứng.
4. Mỗi tệp minh chứng được cập nhật đồng thời với trạng thái ca trong `docs/test-plan.md`.
