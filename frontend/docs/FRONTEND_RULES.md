# Quy tắc xây dựng Frontend: Personal Finance Web

> Tài liệu này là **quy ước chung của cả nhóm** khi viết code trong thư mục `frontend/`.
> Mục tiêu: thêm tính năng mới mà **không phải sửa lại cấu trúc tổng thể**, và bất kỳ thành viên nào mở một feature cũng biết tìm file ở đâu.

---

## 1. Công nghệ

| Hạng mục | Lựa chọn | Ghi chú |
|---|---|---|
| Framework | React + Vite | |
| Điều hướng | `react-router-dom` | |
| Dữ liệu từ server | `@tanstack/react-query` | thay cho `useEffect + fetch` thủ công |
| Gọi API | `fetch` bọc trong `shared/api/client.js` | không dùng `fetch` trực tiếp ở nơi khác |
| Biểu đồ | Recharts (hoặc thư viện nhóm chọn) | bọc trong `shared/components/charts/` |
| Style | **Tailwind CSS v4** (plugin `@tailwindcss/vite`) | Đã chốt; **không** dùng CSS Modules hay CSS thuần cho component |

Frontend **không bao giờ** kết nối trực tiếp PostgreSQL. Mọi dữ liệu đi qua Backend (FastAPI) bằng HTTP, đúng yêu cầu mục V.1 của `rule.md`.

---

## 2. Cấu trúc thư mục

```
frontend/
├── index.html
├── vite.config.js
├── .env.example
└── src/
    ├── main.jsx
    ├── app/                         # lắp ráp toàn ứng dụng
    │   ├── App.jsx
    │   ├── providers.jsx            # QueryClientProvider, Auth...
    │   ├── router.jsx               # gom route của các feature
    │   ├── navigation.js            # danh sách menu sidebar
    │   └── layouts/
    │       ├── AppLayout.jsx
    │       └── AuthLayout.jsx
    │
    ├── features/                    # MỖI TÍNH NĂNG MỘT THƯ MỤC
    │   ├── auth/
    │   ├── profile/
    │   ├── accounts/
    │   ├── transactions/
    │   ├── categories/
    │   ├── transfers/
    │   ├── imports/
    │   ├── budgets/
    │   ├── goals/
    │   ├── loans/
    │   ├── cards/
    │   ├── recurring/
    │   ├── dashboard/
    │   ├── reports/
    │   ├── notifications/
    │   ├── tickets/
    │   ├── chat/
    │   └── admin/
    │       ├── users/
    │       ├── stats/
    │       ├── audit-logs/
    │       ├── tickets/
    │       └── category-keywords/
    │
    └── shared/                      # dùng chung, KHÔNG chứa nghiệp vụ
        ├── api/client.js
        ├── components/              # Button, Modal, Table, Spinner, EmptyState, ErrorState
        │   └── charts/              # LineChart, DonutChart...
        ├── hooks/                   # useUrlFilters, useDebounce
        ├── lib/                     # formatMoney, formatDate, tokenStorage
        └── styles/
```

Ba thư mục cấp một của `src/` là `app/`, `features/`, `shared/`. **Không thêm thư mục cấp một khác** nếu chưa thống nhất với cả nhóm.

---

## 3. Quy tắc phụ thuộc (quan trọng nhất)

```
app  ──►  features  ──►  shared
```

1. `shared/` **không** được import từ `features/` hoặc `app/`.
2. `features/` **không** được import từ `app/`.
3. Feature A **không** import vào ruột feature B (ví dụ `@/features/B/components/...`). Nếu cần, chỉ import qua `@/features/B` (file `index.js`).
4. Không để hai feature import lẫn nhau (phụ thuộc vòng). Nếu xảy ra, phần chung phải chuyển xuống `shared/`, hoặc hai feature nên gộp làm một.
5. Import dùng alias `@/` (ví dụ `@/shared/api/client`), **không** dùng đường dẫn tương đối nhiều cấp như `../../../`. Trong cùng một feature thì dùng đường dẫn tương đối ngắn (`./`, `../`).

---

## 4. Khuôn chuẩn của một feature

Mọi feature **phải theo cùng một khuôn**:

```
features/<tên>/
├── api.js            # gọi endpoint của backend, chỉ làm việc này
├── hooks.js          # React Query: useXxx, useCreateXxx, khai báo query keys
├── components/       # component riêng của feature
├── pages/            # mỗi trang một file, tên kết thúc bằng Page
├── routes.jsx        # khai báo đường dẫn của feature
└── index.js          # "cổng" công khai: chỉ export thứ bên ngoài được dùng
```

Vai trò từng lớp, mỗi lớp **chỉ nói chuyện với lớp ngay bên cạnh**:

| Lớp | Được làm | Không được làm |
|---|---|---|
| `pages/`, `components/` | Hiển thị, nhận thao tác người dùng, gọi hook | Gọi `fetch`/`api.*` trực tiếp |
| `hooks.js` | Quản lý cache, loading, error, làm mới dữ liệu | Viết JSX |
| `api.js` | Gọi `api.get/post/patch/del` | Giữ state, dùng hook React |
| `shared/api/client.js` | Gắn token, xử lý lỗi, refresh token | Chứa logic nghiệp vụ |

Khi feature lớn lên: `api.js` hoặc `hooks.js` vượt khoảng 150–200 dòng thì tách thành thư mục `api/` hoặc `hooks/` chứa nhiều file; `index.js` giữ nguyên để bên ngoài không bị ảnh hưởng.

---

## 5. Code mới đặt ở đâu?

```
Là một PHẦN của nghiệp vụ đã có?          → thêm vào feature đó
Nghiệp vụ mới, có endpoint + trang riêng?  → tạo feature mới theo khuôn ở mục 4
Không thuộc nghiệp vụ nào, nhiều nơi dùng? → shared/
```

Ví dụ:

| Tính năng | Nơi đặt |
|---|---|
| Gợi ý danh mục khi nhập giao dịch | `features/transactions` |
| Đề xuất giao dịch định kỳ | `features/recurring` |
| Dự báo ARIMA | `features/reports` |
| Trợ lý AI (chat) | `features/chat` (feature riêng) |
| Ô nhập tiền, bộ chọn ngày, biểu đồ | `shared/components` |
| Hàm định dạng tiền, ngày | `shared/lib` |

Component được **từ 2 feature trở lên** dùng thì chuyển vào `shared/components`.

---

## 6. Tầng API

- Mọi request đi qua `shared/api/client.js`. Cấm gọi `fetch` ở nơi khác.
- `client.js` chịu trách nhiệm: địa chỉ gốc (`/api/v1`), header JSON, gắn `Authorization: Bearer <access_token>`, thử refresh khi gặp 401, chuẩn hóa lỗi thành `ApiError`. Định dạng lỗi của backend là `{ "error": { "code", "message", "details" } }`; `client.js` đọc `error.code` và `error.message` rồi ném `ApiError` để giao diện hiển thị đúng từng tình huống.
- Địa chỉ gốc lấy từ `import.meta.env.VITE_API_URL`, mặc định `/api/v1`. Khi dev, Vite proxy chuyển `/api` sang backend; khi triển khai, reverse proxy (Nginx) trên VM1 chuyển `/api` sang VM2.
- Mỗi hàm trong `api.js` ứng với **một endpoint** trong danh mục API của kế hoạch (Phụ lục A):

```js
// features/accounts/api.js
import { api } from "@/shared/api/client";

export const getAccounts  = ()         => api.get("/accounts");
export const createAccount = (data)    => api.post("/accounts", data);
export const updateAccount = (id, data) => api.patch(`/accounts/${id}`, data);
export const deleteAccount = (id)      => api.del(`/accounts/${id}`);
```

- Tên trường `access_token`, `refresh_token` phải **khớp response thật** của workflow W2. Nếu backend đổi, chỉ sửa `client.js` và `tokenStorage.js`.

---

## 7. Dữ liệu từ server (React Query)

- **Đọc** dữ liệu bằng `useQuery`, **thay đổi** dữ liệu bằng `useMutation`.
- Mỗi feature khai báo **query keys** trong `hooks.js` và export qua `index.js`:

```js
export const accountKeys = {
  all: ["accounts"],
  detail: (id) => ["accounts", id],
};
```

- Sau mutation thành công, gọi `invalidateQueries` để làm mới dữ liệu liên quan.
- Một thao tác có thể ảnh hưởng nhiều feature. Ví dụ thêm giao dịch làm đổi số dư ví, ngân sách và dashboard:

```js
onSuccess: () => {
  qc.invalidateQueries({ queryKey: transactionKeys.all });
  qc.invalidateQueries({ queryKey: accountKeys.all });   // import qua @/features/accounts
  qc.invalidateQueries({ queryKey: ["budgets"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
}
```

- **Không** copy dữ liệu server vào `useState`/Redux rồi tự đồng bộ. React Query là nơi giữ dữ liệu từ server. `useState` chỉ dùng cho trạng thái giao diện cục bộ (ô đang gõ, modal đang mở).

---

## 8. Routing, phân quyền, menu

- Mỗi feature export mảng route trong `routes.jsx`; `app/router.jsx` là nơi **duy nhất** gom các mảng đó.
- Cấu trúc router:
  - Nhóm công khai (`/login`, `/register`): `AuthLayout`.
  - Nhóm cần đăng nhập: bọc bằng `ProtectedRoute`, dùng `AppLayout`.
  - Nhóm admin: bọc thêm `RoleRoute role="admin"`.
- Menu sidebar khai báo trong `app/navigation.js`.
- **Phân quyền ở frontend chỉ để ẩn/hiện giao diện cho tiện.** Bảo mật thật nằm ở Backend. Không bao giờ coi việc ẩn nút là đã chặn quyền.

---

## 9. Ba trạng thái bắt buộc: đang tải, rỗng, lỗi

Mọi màn hình hoặc khối có dữ liệu từ server **phải xử lý đủ 3 trạng thái** (yêu cầu `rule.md` mục IV.1):

```jsx
if (isLoading) return <Spinner />;
if (isError)   return <ErrorState message={error.message} />;
if (data.length === 0) return <EmptyState text="Chưa có dữ liệu" />;
```

- Dùng 3 component chung trong `shared/components`, không tự viết lại ở từng trang.
- Dashboard gồm nhiều khối độc lập (KPI, biểu đồ, top merchant, ngân sách...). **Mỗi khối tự gọi hook riêng** để có trạng thái riêng; một khối lỗi không làm hỏng cả trang.
- Nút gửi dữ liệu phải `disabled` khi `isPending` để tránh bấm 2 lần.

---

## 10. Form và kiểm tra dữ liệu

- Kiểm tra ở frontend (bắt buộc, định dạng, số dương...) chỉ để **báo lỗi sớm cho người dùng**. Backend vẫn kiểm tra lại toàn bộ.
- Lỗi do backend trả về (409, 422...) phải hiển thị cho người dùng, không nuốt lỗi.
- Số tiền backend trả về là **chuỗi decimal** (`"85000.00"`). `formatMoney` trong `shared/lib` chỉ để **hiển thị**; **không** cộng trừ tiền bằng số thực của JavaScript. Giá trị nghiệp vụ (số dư, hạn mức...) lấy từ backend, frontend không tự tính lại.

---

## 11. Bộ lọc nằm trên URL

Các màn hình có bộ lọc (dashboard, danh sách giao dịch, báo cáo) lưu trạng thái lọc trong **query string**:

```
/dashboard?w=30d&cat=1,3&acc=2
```

- Lý do: chia sẻ được đường dẫn, tải lại trang vẫn giữ bộ lọc, nút Quay lại hoạt động đúng.
- Dùng chung hook `shared/hooks/useUrlFilters.js` (bọc `useSearchParams`), **không** tự viết lại ở từng trang.
- Giá trị lọc đưa vào `queryKey` của React Query để tự tải lại khi đổi bộ lọc.

---

## 12. Giao diện và style

- Thiết kế giao diện trong **Figma** trước, chia thành các khối rồi mới code thành component (yêu cầu `rule.md`).
- `index.html` gần như không sửa (chỉ `<title>`, favicon, font). Toàn bộ giao diện nằm trong `src/`.
- Một component một file; component quá ~150 dòng thì cân nhắc tách.
- Component trong `shared/components` **không biết gì về nghiệp vụ** (không gọi API, không import feature). Dữ liệu và hành động truyền vào qua props.
- Style dùng **Tailwind CSS**: viết class trực tiếp trong JSX.
- Class dài, lặp lại phải được đóng gói vào component trong `shared/components` (Button, Input, Card...). **Không** copy một chuỗi class dài sang nhiều nơi.
- Màu sắc, cỡ chữ, khoảng cách dùng thang có sẵn của Tailwind hoặc token khai báo trong `@theme` ở `shared/styles/index.css`. **Không** viết cứng mã màu (`#2563eb`) hay giá trị tùy ý (`w-[137px]`) trừ khi thật sự cần.
- Không tạo file `.css` riêng cho component. File CSS duy nhất của ứng dụng là `shared/styles/index.css`.
- Nên cài tiện ích VS Code **Tailwind CSS IntelliSense** để có gợi ý class.
- Biểu đồ dùng qua `shared/components/charts/`; đổi thư viện biểu đồ chỉ sửa ở đó.

---

## 13. Quy ước đặt tên

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Thư mục feature | `kebab-case` / số nhiều | `transactions`, `audit-logs` |
| Component, trang | `PascalCase.jsx` | `AccountCard.jsx`, `AccountsPage.jsx` |
| Hook | `useXxx` | `useAccounts`, `useCreateAccount` |
| Hàm API | động từ + danh từ | `getAccounts`, `createAccount` |
| Query keys | `xxxKeys` | `accountKeys` |
| File route | `routes.jsx`, export `xxxRoutes` | `accountRoutes` |
| Biến môi trường | tiền tố `VITE_` | `VITE_API_URL` |

Mỗi file chỉ export **một thứ chính** (component hoặc hook). Dùng `export default` cho component trang và component; dùng named export cho hook, hàm API, route.

---

## 14. Bảo mật và cấu hình

- **Không** để mật khẩu, khóa bí mật, token cố định trong code hoặc `.env` của frontend. Mọi biến `VITE_*` đều công khai với người dùng.
- Không commit `.env`. Chỉ commit `.env.example`.
- Token chỉ thao tác qua `shared/lib/tokenStorage.js`. Hiện lưu ở `localStorage` theo thiết kế W2; nếu sau này chuyển sang cookie `httpOnly` thì chỉ sửa `tokenStorage.js` và `client.js`.
- Không dùng `dangerouslySetInnerHTML` với nội dung do người dùng nhập (chống XSS). Nội dung chatbot và ticket phải được hiển thị dưới dạng văn bản thuần hoặc đã làm sạch.
- Khi nhận lỗi 401 không thể phục hồi: xóa token và chuyển về `/login` (do `client.js` xử lý).

---

## 15. Quy trình Git

- Một repository chung; luồng: **Issue → nhánh → commit → Pull Request → review → merge**.
- Mỗi nhánh nên làm **một feature hoặc một phần của feature**, ví dụ `feat/loans-schedule`.
- Mỗi người làm trong thư mục feature của mình để hạn chế xung đột. Sửa `shared/` hoặc `app/` cần báo trong PR vì ảnh hưởng cả nhóm.
- PR phải được ít nhất một người khác review có nội dung nhận xét trước khi merge.

---

## 16. Checklist thêm một feature mới

- [ ] Tạo `features/<tên>/` đủ: `api.js`, `hooks.js`, `components/`, `pages/`, `routes.jsx`, `index.js`.
- [ ] `api.js` chỉ gọi qua `api.*` của `shared/api/client.js`.
- [ ] Khai báo `xxxKeys` trong `hooks.js` và export qua `index.js`.
- [ ] Thêm `...xxxRoutes` vào `app/router.jsx` (đúng nhóm: công khai / đăng nhập / admin).
- [ ] Thêm một dòng vào `app/navigation.js` (nếu cần hiện trên menu).
- [ ] Mutation có `invalidateQueries` cho mọi dữ liệu bị ảnh hưởng, kể cả của feature khác.
- [ ] Không sửa `shared/` hay feature khác, trừ khi thật sự cần và đã báo trong PR.

## 17. Checklist trước khi tạo Pull Request

- [ ] Mọi màn hình có dữ liệu server đều xử lý **đang tải, rỗng, lỗi**.
- [ ] Không có `fetch` ngoài `shared/api/client.js`.
- [ ] Không có import vi phạm chiều phụ thuộc (`shared` → `features`, feature → ruột feature khác).
- [ ] Không có `console.log`, code chết hoặc đoạn comment thừa.
- [ ] Không commit `.env`, token, dữ liệu cá nhân.
- [ ] Đã thử luồng chính trên trình duyệt với backend thật (không chỉ dữ liệu giả).
- [ ] Nút gửi dữ liệu bị khóa khi đang xử lý; lỗi từ backend được hiển thị.
- [ ] `npm run build` chạy không lỗi.

---

## 18. Những điều KHÔNG làm

1. Không gọi `fetch` trực tiếp trong component hoặc hook.
2. Không copy dữ liệu server vào `useState` rồi tự đồng bộ.
3. Không để `shared/` import từ `features/`.
4. Không import vào ruột feature khác (chỉ qua `index.js`).
5. Không viết logic nghiệp vụ tính tiền ở frontend thay cho backend.
6. Không để secret trong code hoặc biến `VITE_*`.
7. Không tạo thư mục cấp một mới trong `src/` khi chưa thống nhất.
8. Không coi việc ẩn nút/menu theo quyền là đủ bảo mật.