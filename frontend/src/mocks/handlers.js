import { http, HttpResponse } from "msw";

const API = "/api/v1";

const fail = (status, code, message) =>
  HttpResponse.json({ error: { code, message } }, { status });

// "Database" giả trong bộ nhớ (mất khi tải lại trang, trừ 3 tài khoản có sẵn)
const db = new Map([
  ["demo@test.com", { id: 1, email: "demo@test.com", full_name: "Người dùng Demo", roles: ["user"], password: "Demo@1234" }],
  ["admin@test.com", { id: 2, email: "admin@test.com", full_name: "Quản trị viên", roles: ["admin"], password: "Admin@1234" }],
  ["locked@test.com", { id: 3, email: "locked@test.com", full_name: "Bị khóa", roles: ["user"], password: "Demo@1234", locked: true }],
]);

const publicUser = (u) => ({ id: u.id, email: u.email, full_name: u.full_name, roles: u.roles });

export const handlers = [
  http.post(`${API}/auth/register`, async ({ request }) => {
    const { email, password, full_name } = await request.json();
    const key = String(email).toLowerCase();
    if (password.length < 8)
      return fail(422, "WEAK_PASSWORD", "Mật khẩu tối thiểu 8 ký tự");
    if (db.has(key)) return fail(409, "EMAIL_TAKEN", "Email đã được sử dụng");
    const user = { id: db.size + 1, email: key, full_name, roles: ["user"], password };
    db.set(key, user);
    return HttpResponse.json(publicUser(user), { status: 201 });
  }),

  http.post(`${API}/auth/login`, async ({ request }) => {
    const { email, password } = await request.json();
    const key = String(email).toLowerCase();
    if (key === "limit@test.com") return fail(429, "RATE_LIMITED", "Quá nhiều lần thử");
    const user = db.get(key);
    if (!user || user.password !== password)
      return fail(401, "INVALID_CREDENTIALS", "Sai email hoặc mật khẩu");
    if (user.locked) return fail(403, "ACCOUNT_LOCKED", "Tài khoản bị khóa");
    return HttpResponse.json({
      access_token: `fake-access:${user.email}`,
      refresh_token: `fake-refresh:${user.email}`,
      user: publicUser(user),
    });
  }),

  http.post(`${API}/auth/refresh`, async ({ request }) => {
    const { refresh_token } = await request.json();
    const email = String(refresh_token).replace("fake-refresh:", "");
    if (!db.has(email)) return fail(401, "TOKEN_REUSED", "Phiên không hợp lệ");
    return HttpResponse.json({
      access_token: `fake-access:${email}`,
      refresh_token: `fake-refresh:${email}`,
    });
  }),

  http.get(`${API}/users/me`, ({ request }) => {
    const auth = request.headers.get("Authorization") ?? "";
    if (auth === "Bearer expired") return fail(401, "TOKEN_EXPIRED", "Token hết hạn");
    const email = auth.replace("Bearer fake-access:", "");
    const user = db.get(email);
    if (!auth.startsWith("Bearer fake-access:") || !user)
      return fail(401, "TOKEN_INVALID", "Token không hợp lệ");
    return HttpResponse.json(publicUser(user));
  }),

  http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
];