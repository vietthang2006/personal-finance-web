# TÀI LIỆU YÊU CẦU KỸ THUẬT API ENDPOINTS (API_ENDPOINT.MD)

Tài liệu này tổng hợp chi tiết các đặc tả kỹ thuật, giao thức kết nối, định dạng dữ liệu, ràng buộc và luồng nghiệp vụ của hệ thống **Personal Finance API**. 

Tài liệu được phân loại theo cấu trúc mô-đun hóa để phục vụ việc mở rộng và tích hợp các module nghiệp vụ trong tương lai.

---

## MỤC LỤC TỔNG QUAN HỆ THỐNG

- [A. THÔNG TIN MÔI TRƯỜNG & TÀI LIỆU TRỰC QUAN (SWAGGER UI)](#a-thông-tin-môi-trường--tài-liệu-trực-quan-swagger-ui)
- [B. CẤU TRÚC DANH MỤC CÁC MODULE HỆ THỐNG](#b-cấu-trúc-danh-mục-các-module-hệ-thống)
- [1. MODULE AUTHENTICATION & USER IDENTITY (DANH MỤC SỐ 1)](#1-module-authentication--user-identity-danh-mục-số-1)
  - [1.1. Đăng ký tài khoản (User Registration)](#11-đăng-ký-tài-khoản-user-registration)
  - [1.2. Đăng nhập hệ thống (User Login)](#12-đăng-nhập-hệ-thống-user-login)
  - [1.3. Làm mới Access Token (Token Refresh & Rotation)](#13-làm-mới-access-token-token-refresh--rotation)
  - [1.4. Đăng xuất (User Logout & Session Revocation)](#14-đăng-xuất-user-logout--session-revocation)
  - [1.5. Quên mật khẩu & Đặt lại mật khẩu (Forgot & Reset Password)](#15-quên-mật-khẩu--đặt-lại-mật-khẩu-forgot--reset-password)
  - [1.6. Đổi mật khẩu chủ động (Change Password)](#16-đổi-mật-khẩu-chủ-động-change-password)
  - [1.7. Tổng hợp các tính năng bảo mật (Security Features & Best Practices)](#17-tổng-hợp-các-tính-năng-bảo-mật-security-features--best-practices)

---

## A. THÔNG TIN MÔI TRƯỜNG & TÀI LIỆU TRỰC QUAN (SWAGGER UI)

Hệ thống được phát triển trên nền tảng **FastAPI**, tự động cung cấp bộ tài liệu tương tác chuẩn OpenAPI:

| Thành phần | Đường dẫn (URL / Path) | Ghi chú |
| :--- | :--- | :--- |
| **Server Host mặc định** | `http://localhost:8000` | Cổng phát triển tiêu chuẩn |
| **API Version Prefix** | `/api/v1` | Tiền tố cho toàn bộ API phiên bản 1 |
| **Base API URL** | `http://localhost:8000/api/v1` | URL gốc cho các endpoint nghiệp vụ |
| **Swagger UI Documentation** | `http://localhost:8000/docs` | Giao diện kiểm thử trực quan tương tác (Interactive API Docs) |
| **ReDoc Documentation** | `http://localhost:8000/redoc` | Tài liệu tĩnh theo cấu trúc phân cấp chuẩn kỹ thuật |
| **OpenAPI Schema (JSON)** | `http://localhost:8000/openapi.json` | Đặc tả schema chuẩn OpenAPI 3.1.0 |
| **Health Check Endpoint** | `http://localhost:8000/health` | Kiểm tra tình trạng hoạt động của service |

### Quy ước chung về truyền tải dữ liệu
- **Content-Type**: Toàn bộ request/response body sử dụng định dạng JSON `application/json; charset=utf-8`.
- **Cơ chế xác thực (Authentication)**: Các endpoint yêu cầu quyền đăng nhập sử dụng chuẩn HTTP Bearer Token qua header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Quy chuẩn mã hóa thời gian**: Chuỗi thời gian chuẩn ISO 8601 kèm múi giờ UTC (ví dụ: `2026-10-18T10:30:00Z`).

---

## B. CẤU TRÚC DANH MỤC CÁC MODULE HỆ THỐNG

Hệ thống được tổ chức thành các mô-đun độc lập, định hướng tích hợp dài hạn:
- **1. Module Authentication & User Identity**: Xác thực, phân quyền, cấp phát và thu hồi phiên JWT.
---

# 1. MODULE AUTHENTICATION & USER IDENTITY (DANH MỤC SỐ 1)

Module Authentication đảm nhiệm việc quản lý định danh người dùng, kiểm soát truy cập và bảo vệ phiên làm việc qua cơ chế **Dual Token (Access Token + Refresh Token Rotation)**.

---

### 1.1. ĐĂNG KÝ TÀI KHOẢN (USER REGISTRATION)

Đăng ký tài khoản người dùng mới vào hệ thống, thiết lập vai trò cơ bản (`user`) và tự động khởi tạo phiên đăng nhập đầu tiên.

- **API Endpoint**: `POST /api/v1/auth/register`
- **Full URL**: `http://localhost:8000/api/v1/auth/register`
- **Authentication**: `None (Public)`
- **HTTP Method**: `POST`
- **Request Headers**:
  - `Content-Type: application/json`

#### Request Body & Constraints
| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc kỹ thuật (Validation) | Mô tả chi tiết |
| :--- | :--- | :---: | :--- | :--- |
| `email` | `string (email)` | Có | Chuẩn Email RFC, tự động chuẩn hóa chữ thường (`lowercase`) và cắt khoảng trắng | Email dùng để đăng nhập và định danh duy nhất |
| `username` | `string` | Có | Độ dài từ 3 đến 50 ký tự, regex: `^[A-Za-z0-9_.-]+$` | Tên người dùng định danh duy nhất trong hệ thống |
| `password` | `string` | Có | Độ dài ký tự: 8 - 72 ký tự, độ dài byte UTF-8 $\le$ 72 bytes | Mật khẩu thô (giới hạn 72 bytes do thuật toán Bcrypt) |
| `full_name` | `string` | Không | Tối đa 150 ký tự, tự động cắt khoảng trắng thừa | Họ và tên đầy đủ hiển thị của người dùng |
| `default_currency`| `string` | Không | Mặc định: `"VND"`. Độ dài đúng 3 ký tự (ISO 4217), phải tồn tại trong bảng `currencies` | Mã tiền tệ mặc định cho ví và báo cáo tài chính |

#### Request Body Example
```json
{
  "email": "user@example.com",
  "username": "financial_user",
  "password": "StrongPassword123@",
  "full_name": "Nguyễn Văn A",
  "default_currency": "VND"
}
```

#### Business Flow (Luồng xử lý nghiệp vụ)
1. **Validation**: Kiểm tra cấu trúc dữ liệu theo schema `UserCreate`.
2. **Kiểm tra tiền tệ**: `CurrencyRepository` xác thực mã `default_currency` có tồn tại trong hệ thống hay không. Nếu không, trả về lỗi `422`.
3. **Kiểm tra vai trò mặc định**: `UserRepository` tìm role có mã `user`. Nếu thiếu, báo lỗi hệ thống `500`.
4. **Mã hóa mật khẩu**: Băm mật khẩu bằng thuật toán **Bcrypt** với salt ngẫu nhiên.
5. **Khởi tạo dữ liệu người dùng**: Lưu người dùng mới vào database với trạng thái mặc định `status = "active"`.
6. **Gán vai trò**: Gán quan hệ vai trò người dùng vào bảng `user_roles`.
7. **Khởi tạo phiên làm việc (Session)**:
   - Tạo mã phiên `session_id` ngẫu nhiên chuẩn UUID v4.
   - Thu thập thông tin client: IP Address (nếu hợp lệ) và User-Agent header (tối đa 255 ký tự).
   - Thiết lập thời gian hết hạn của phiên: `now() + 30 ngày`.
   - Sinh chuỗi `refresh_token` (JWT chứa `sub`, `sid`, `jti`).
   - Băm chuỗi refresh token bằng **SHA-256** và lưu vào bảng `user_sessions`.
   - Sinh chuỗi `access_token` (JWT chứa `sub`, danh sách `roles`, thời hạn 15 phút).
8. **Transaction Commit**: Thực thi commit vào database và trả về cặp token cho client.

#### Response Specifications
- **Success Response (`201 Created`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `409 Conflict`: Email hoặc username đã được đăng ký trước đó.
    ```json
    {
      "detail": "Email or username is already registered"
    }
    ```
  - `422 Unprocessable Entity`: Dữ liệu không thỏa mãn validation (mật khẩu quá ngắn, quá 72 bytes, định dạng email sai, hoặc đơn vị tiền tệ không hỗ trợ).
    ```json
    {
      "detail": "Unsupported default currency"
    }
    ```

---

### 1.2. ĐĂNG NHẬP HỆ THỐNG (USER LOGIN)

Xác thực thông tin tài khoản và cấp phát cặp token mới để client truy cập các tài nguyên bảo vệ.

- **API Endpoint**: `POST /api/v1/auth/login`
- **Full URL**: `http://localhost:8000/api/v1/auth/login`
- **Authentication**: `None (Public)`
- **HTTP Method**: `POST`
- **Request Headers**:
  - `Content-Type: application/json`

#### Request Body & Constraints
| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc kỹ thuật | Mô tả chi tiết |
| :--- | :--- | :---: | :--- | :--- |
| `email` | `string (email)` | Có | Chuẩn Email RFC, tự động chuẩn hóa chữ thường | Địa chỉ email đăng ký |
| `password` | `string` | Có | Tối thiểu 1 ký tự, tối đa 72 ký tự | Mật khẩu tài khoản |

#### Request Body Example
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123@"
}
```

#### Business Flow (Luồng xử lý nghiệp vụ)
1. **Tìm kiếm người dùng**: Truy vấn `UserRepository` theo email (chuẩn hóa chữ thường) đồng thời tải sẵn danh sách quyền (`selectinload(User.roles)`).
2. **Xác thực mật khẩu**: So khớp mật khẩu thô và hash lưu trong database thông qua hàm `bcrypt.checkpw`.
3. **Kiểm tra trạng thái tài khoản**: Kiểm tra trường `status`:
   - Nếu `user is None` hoặc sai mật khẩu: Trả về lỗi `401 Unauthorized` với thông điệp chung `"Invalid email or password"` để chống tấn công dò tài khoản.
   - Nếu `status != "active"` (tài khoản bị khóa): Trả về lỗi `401 Unauthorized` kèm thông báo `"Account is locked"`.
4. **Cập nhật thời gian đăng nhập**: Cập nhật `last_login_at = now()` vào bảng `users`.
5. **Cấp phát phiên (Session Creation)**:
   - Sinh UUID phiên mới, ghi nhận IP Address và User-Agent.
   - Băm SHA-256 chuỗi refresh token và lưu vào `user_sessions`.
   - Sinh access token mang claim quyền hạn của người dùng.
6. **Transaction Commit**: Lưu phiên và trả về `TokenPair`.

#### Response Specifications
- **Success Response (`200 OK`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Sai email hoặc mật khẩu, hoặc tài khoản đang bị khóa.
    ```json
    {
      "detail": "Invalid email or password"
    }
    ```
  - `422 Unprocessable Entity`: Định dạng body hoặc email không hợp lệ.

---

### 1.3. LÀM MỚI ACCESS TOKEN (TOKEN REFRESH & ROTATION)

Cấp phát lại Access Token mới khi token cũ đã hết hạn, đồng thời áp dụng cơ chế **Refresh Token Rotation** (thu hồi refresh token cũ và cấp refresh token mới) nhằm chống tấn công Replay Attack.

- **API Endpoint**: `POST /api/v1/auth/refresh`
- **Full URL**: `http://localhost:8000/api/v1/auth/refresh`
- **Authentication**: `None` (Sử dụng Refresh Token truyền trong Body)
- **HTTP Method**: `POST`
- **Request Headers**:
  - `Content-Type: application/json`

#### Request Body & Constraints
| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc kỹ thuật | Mô tả chi tiết |
| :--- | :--- | :---: | :--- | :--- |
| `refresh_token` | `string` | Có | Độ dài từ 1 đến 4096 ký tự | Chuỗi Refresh Token JWT còn hiệu lực |

#### Request Body Example
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Business Flow (Luồng xử lý nghiệp vụ)
1. **Giải mã Token**:
   - Giải mã JWT bằng Secret Key và Algorithm của hệ thống.
   - Xác minh claim `type == "refresh"`.
   - Trích xuất định danh người dùng `sub` (User ID) và định danh phiên `sid` (Session ID).
2. **Khóa bản ghi phiên (Row-level Lock)**:
   - Truy vấn phiên qua `UserSessionRepository` bằng câu lệnh `SELECT ... FOR UPDATE`.
   - Cơ chế khóa hàng ngăn chặn trường hợp hai request refresh token được gửi song song đồng thời từ cùng một client (Race Condition).
3. **Kiểm tra tính hợp lệ của phiên**:
   - Phiên có tồn tại trong database hay không.
   - Phiên có đúng là của `user_id` trong token hay không.
   - Phiên đã bị thu hồi trước đó chưa (`revoked_at IS NULL`).
   - Phiên đã hết hạn chưa (`expires_at > now()`).
   - So sánh hash SHA-256 của refresh token với giá trị lưu trong database bằng phương thức an toàn `hmac.compare_digest` (chống Timing Attack).
   - Nếu vi phạm bất kỳ điều kiện nào $\rightarrow$ Trả về `401 Unauthorized` ngay lập tức.
4. **Kiểm tra trạng thái tài khoản**: Kiểm tra người dùng có còn tồn tại và ở trạng thái `active` hay không.
5. **Thực hiện Token Rotation**:
   - Tạo chuỗi `refresh_token` mới kế thừa thời hạn hết hạn (`expires_at`) của phiên hiện tại.
   - Cập nhật trường `refresh_token_hash` của session thành hash mới.
   - Tạo chuỗi `access_token` mới (15 phút) chứa danh sách roles cập nhật nhất của user.
6. **Commit & Return**: Lưu thay đổi và trả về `TokenPair` mới.

#### Response Specifications
- **Success Response (`200 OK`)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: Token không hợp lệ, phiên đã hết hạn, hoặc bị thu hồi.
    ```json
    {
      "detail": "Invalid or expired refresh token"
    }
    ```

---

### 1.4. ĐĂNG XUẤT (USER LOGOUT & SESSION REVOCATION)

Vô hiệu hóa phiên đăng nhập hiện tại trên thiết bị bằng cách đánh dấu thời điểm thu hồi của phiên trong cơ sở dữ liệu.

- **API Endpoint**: `POST /api/v1/auth/logout`
- **Full URL**: `http://localhost:8000/api/v1/auth/logout`
- **Authentication**: `None` (Truyền Refresh Token trong Request Body)
- **HTTP Method**: `POST`
- **Request Headers**:
  - `Content-Type: application/json`

#### Request Body & Constraints
| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc kỹ thuật | Mô tả chi tiết |
| :--- | :--- | :---: | :--- | :--- |
| `refresh_token` | `string` | Có | Độ dài từ 1 đến 4096 ký tự | Refresh Token của phiên cần đăng xuất |

#### Request Body Example
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Business Flow (Luồng xử lý nghiệp vụ)
1. **Giải mã Token**: Giải mã chuỗi JWT, xác thực `type == "refresh"`, trích xuất `sid` và `sub`.
2. **Khóa bản ghi phiên**: Truy vấn session theo `sid` có `with_for_update()`.
3. **Đối soát tính toàn vẹn**: So sánh hash token và kiểm tra quyền sở hữu của user.
4. **Vô hiệu hóa phiên**:
   - Đặt `revoked_at = now()`.
   - Kể từ thời điểm này, refresh token đó không thể sử dụng để làm mới access token được nữa.
5. **Commit**: Lưu vào database và trả về mã trạng thái thành công.

#### Response Specifications
- **Success Response (`204 No Content`)**: Không có response body.
- **Error Responses**:
  - `401 Unauthorized`: Token không hợp lệ hoặc không tìm thấy phiên tương ứng.
    ```json
    {
      "detail": "Invalid refresh token"
    }
    ```

---

### 1.5. QUÊN MẬT KHẨU & ĐẶT LẠI MẬT KHẨU (FORGOT & RESET PASSWORD)

Quy trình hỗ trợ người dùng tự lấy lại quyền truy cập tài khoản khi quên mật khẩu qua email xác nhận gồm hai giai đoạn:

```
[Client] ---> (1) Gửi yêu cầu qua Email ---> [API: forgot-password]
                                                    |
                                            Tạo Reset Token (30m)
                                            & Gửi Email liên kết
                                                    |
[Client] <--- (2) Gửi Token + Pass mới <--- [Người dùng bấm link]
       |
  [API: reset-password] ---> Băm mật khẩu mới & Hủy toàn bộ Sessions cũ
```

#### Bước 1: Yêu cầu cấp lại mật khẩu (Forgot Password Request)
- **API Endpoint**: `POST /api/v1/auth/forgot-password`
- **Full URL**: `http://localhost:8000/api/v1/auth/forgot-password`
- **Authentication**: `None (Public)`
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Business Flow**:
  1. Kiểm tra định dạng email hợp lệ.
  2. Truy vấn người dùng trong database theo email.
  3. **Chống dò quét thông tin người dùng (Anti-Email Enumeration)**: Dù email có tồn tại hay không trong hệ thống, API **luôn trả về cùng một thông điệp phản hồi thành công** (`200 OK`).
  4. Nếu người dùng tồn tại và đang `active`:
     - Tạo một JWT Token loại `type = "password_reset"` với thời hạn là 30 phút (`settings.password_reset_token_expire_minutes`).
     - Gửi email chứa đường dẫn đặt lại mật khẩu dạng: `https://frontend-domain.com/reset-password?token=<reset_token>`.
- **Success Response (`200 OK`)**:
  ```json
  {
    "message": "If the email is registered, a password reset link has been sent."
  }
  ```

---

#### Bước 2: Xác nhận đặt lại mật khẩu mới (Reset Password Confirmation)
- **API Endpoint**: `POST /api/v1/auth/reset-password`
- **Full URL**: `http://localhost:8000/api/v1/auth/reset-password`
- **Authentication**: `None` (Xác thực qua mã Reset Token trong Body)
- **Request Body**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password": "NewStrongPassword456@"
  }
  ```
- **Constraints**:
  - `token`: Chuỗi JWT hợp lệ, chưa hết hạn (trong vòng 30 phút).
  - `new_password`: Từ 8 đến 72 ký tự (tối đa 72 UTF-8 bytes).
- **Business Flow**:
  1. Giải mã `token` và kiểm tra `payload["type"] == "password_reset"`. Nếu hết hạn hoặc sai kiểu, trả về `400 Bad Request`.
  2. Trích xuất `user_id = UUID(payload["sub"])`.
  3. Lấy thông tin người dùng và xác nhận trạng thái `active`.
  4. Mã hóa `new_password` bằng Bcrypt và cập nhật `password_hash`.
  5. **Bảo mật phiên**: Gọi `session_repo.revoke_all_by_user_id(user_id)` để **thu hồi toàn bộ các phiên đăng nhập hiện có** trên mọi thiết bị, buộc kẻ xâm nhập hoặc các phiên cũ phải đăng nhập lại bằng mật khẩu mới.
  6. Commit transaction và trả về thông báo thành công.
- **Success Response (`200 OK`)**:
  ```json
  {
    "message": "Password has been reset successfully. Please login with your new password."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.
    ```json
    {
      "detail": "Invalid or expired password reset token"
    }
    ```
  - `422 Unprocessable Entity`: Mật khẩu mới không thỏa mãn điều kiện độ dài/định dạng.

---

### 1.6. ĐỔI MẬT KHẨU CHỦ ĐỘNG (CHANGE PASSWORD)

Cho phép người dùng đã đăng nhập tự đổi mật khẩu tài khoản trong trang cài đặt cá nhân.

- **API Endpoint**: `PUT /api/v1/users/me/password`
- **Full URL**: `http://localhost:8000/api/v1/users/me/password`
- **Authentication**: `Bearer Token (JWT Access Token Required)`
- **HTTP Method**: `PUT`
- **Request Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`

#### Request Body & Constraints
| Trường | Kiểu dữ liệu | Bắt buộc | Ràng buộc kỹ thuật | Mô tả chi tiết |
| :--- | :--- | :---: | :--- | :--- |
| `old_password` | `string` | Có | 1 đến 72 ký tự | Mật khẩu hiện tại của người dùng |
| `new_password` | `string` | Có | 8 đến 72 ký tự, tối đa 72 bytes UTF-8 | Mật khẩu mới cần thiết lập |

#### Request Body Example
```json
{
  "old_password": "StrongPassword123@",
  "new_password": "NewStrongPassword456@"
}
```

#### Business Flow (Luồng xử lý nghiệp vụ)
1. **Dependency Injection**: Tầng API trích xuất thông tin người dùng từ `CurrentUser` dependency (`get_current_user`).
2. **Xác thực mật khẩu cũ**: Kiểm tra `old_password` với `user.password_hash` bằng `verify_password`. Nếu sai, ném ngoại lệ `InvalidPasswordError`.
3. **Mã hóa và cập nhật**:
   - Băm `new_password` bằng thuật toán Bcrypt.
   - Gán `user.password_hash = hash_password(new_password)`.
   - `user_repo.update(user)`.
4. **Quản lý phiên**: Có thể tùy chọn giữ phiên hiện tại hoặc thu hồi các phiên làm việc khác để tăng cường tính an toàn.
5. **Commit**: Thực thi lưu vào database và trả về mã thành công `204 No Content`.

#### Response Specifications
- **Success Response (`204 No Content`)**: Không có response body.
- **Error Responses**:
  - `400 Bad Request`: Mật khẩu cũ không chính xác.
    ```json
    {
      "detail": "Current password is not correct"
    }
    ```
  - `401 Unauthorized`: Access Token bị thiếu, sai hoặc đã hết hạn.
    ```json
    {
      "detail": "Not authenticated"
    }
    ```
  - `422 Unprocessable Entity`: Mật khẩu mới không thỏa mãn độ dài (dưới 8 ký tự hoặc vượt quá 72 UTF-8 bytes).

---

### 1.7. TỔNG HỢP CÁC TÍNH NĂNG BẢO MẬT (SECURITY FEATURES & BEST PRACTICES)

1. **Giới hạn 72 Bytes của thuật toán Bcrypt**:
   - Thuật toán băm Bcrypt chỉ xử lý tối đa 72 bytes đầu tiên của mật khẩu thô.
   - Hệ thống áp dụng validator kiểm tra rõ ràng `len(password.encode('utf-8')) <= 72` ngay tại tầng Schema Pydantic để ngăn chặn lỗi Silent Truncation (cắt xén âm thầm ký tự thừa gây hiểu lầm cho người dùng) và phòng chống tấn công từ chối dịch vụ (DoS) bằng payload mật khẩu siêu dài.
2. **Refresh Token Rotation (RTR)**:
   - Mỗi chu kỳ gọi `/auth/refresh` thành công sẽ hủy hoàn toàn refresh token cũ và sinh một refresh token mới. Nếu một refresh token đã dùng bị gửi lại, hệ thống có thể phát hiện và phong tỏa phiên làm việc ngay lập tức.
3. **Chống Race Condition bằng Khóa hàng (Row-level Locking)**:
   - Thao tác refresh token và revoke sử dụng `with_for_update()` của PostgreSQL, đảm bảo các request đồng thời từ cùng một thiết bị không thể lạm dụng sinh nhiều phiên hợp lệ cùng lúc.
4. **Chống tấn công đo thời gian (Timing-Attack Protection)**:
   - Việc so sánh hash chuỗi token trong database được thực hiện bằng `hmac.compare_digest`, ngăn chặn kẻ tấn công đo thời gian phản hồi của CPU để suy đoán nội dung token.
5. **Bảo mật lưu trữ Token (One-way Hashing)**:
   - Refresh token của người dùng **không bao giờ được lưu dưới dạng chuỗi thô** trong cơ sở dữ liệu. Chỉ có chuỗi băm **SHA-256** được lưu trữ trong bảng `user_sessions`. Khi database bị rò rỉ, kẻ tấn công không thể sử dụng trực tiếp các hash này để truy cập API.
6. **Theo dõi và Giám sát phiên (Session Forensics)**:
   - Mỗi phiên lưu trữ đầy đủ `ip_address`, `user_agent`, `created_at`, `expires_at`, và `revoked_at` để phục vụ đối soát, thống kê đăng nhập bất thường và cho phép người dùng kiểm tra lịch sử thiết bị.
7. **Thời hạn tồn tại ngắn của Access Token (Short-lived Tokens)**:
   - Access token chỉ có hiệu lực trong **15 phút**. Kể cả khi access token bị lộ qua đường truyền mạng, thiệt hại được giới hạn trong khoảng thời gian rất ngắn.
8. **Chống dò quét tài khoản (Anti-User Enumeration)**:
   - Endpoint quên mật khẩu luôn phản hồi thành công một thông điệp thống nhất để ngăn chặn kẻ tấn công lợi dụng phản hồi nhằm lập danh sách email có trong hệ thống.

