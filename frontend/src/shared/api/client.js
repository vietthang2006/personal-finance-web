import { tokenStorage } from "@/shared/lib/tokenStorage";

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

// Khớp TokenPair của backend (app/schemas/user.py)
export const ACCESS_FIELD = "access_token";
export const REFRESH_FIELD = "refresh_token";
const REFRESH_PATH = "/auth/refresh";

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;     // mã HTTP (0 nếu không kết nối được)
    this.code = code;         // "NETWORK_ERROR", "VALIDATION_ERROR" hoặc mã backend (nếu có)
    this.details = details;   // với 422: { tenTruong: "thông báo" }
  }
}

// Hàm cấp thấp: gửi request, KHÔNG xử lý refresh
async function rawFetch(path, { skipAuth, ...options } = {}, accessToken) {
  const headers = { ...options.headers };
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken && !skipAuth) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  try {
    return await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Không kết nối được máy chủ");
  }
}

// Nhiều request cùng gặp 401 thì chỉ refresh MỘT lần
let refreshing = null;

async function refreshTokens() {
  const tokens = tokenStorage.get();
  const used = tokens?.[REFRESH_FIELD];
  if (!used) return null;

  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await rawFetch(REFRESH_PATH, {
          method: "POST",
          skipAuth: true,
          body: JSON.stringify({ [REFRESH_FIELD]: used }),
        });
        if (res.ok) {
          const merged = { ...tokens, ...(await res.json()) };
          tokenStorage.set(merged);
          return merged;
        }
      } catch {
        // rơi xuống nhánh bên dưới
      }
      // Backend đổi refresh token sau mỗi lần dùng. Nếu một tab khác vừa
      // làm mới trước, refresh token đã đổi -> dùng bản mới thay vì đăng xuất
      const current = tokenStorage.get();
      return current && current[REFRESH_FIELD] !== used ? current : null;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

// AuthProvider đăng ký hàm này để xử lý khi phiên hết hạn hẳn
let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

// Chấp nhận cả hai dạng lỗi:
//  - FastAPI mặc định: { detail: "..." } hoặc { detail: [{ loc, msg }] }
//  - Theo kế hoạch:    { error: { code, message, details } }
function parseError(status, data) {
  if (data?.error) {
    return new ApiError(
      status,
      data.error.code ?? null,
      data.error.message ?? "Có lỗi xảy ra",
      data.error.details ?? null
    );
  }

  const detail = data?.detail;

  if (typeof detail === "string") {
    return new ApiError(status, null, detail, null);
  }

  if (Array.isArray(detail)) {
    const fields = {};
    for (const d of detail) {
      const name = d.loc?.[d.loc.length - 1];
      if (typeof name === "string" && !(name in fields)) fields[name] = d.msg;
    }
    return new ApiError(status, "VALIDATION_ERROR", "Dữ liệu không hợp lệ", fields);
  }

  return new ApiError(status, null, "Có lỗi xảy ra", null);
}

export async function request(path, options = {}) {
  const tokens = tokenStorage.get();
  let res = await rawFetch(path, options, tokens?.[ACCESS_FIELD]);

  // Backend không có mã TOKEN_EXPIRED: mọi 401 của request có token
  // đều thử làm mới đúng 1 lần
  if (res.status === 401 && !options.skipAuth && tokens?.[REFRESH_FIELD]) {
    const fresh = await refreshTokens();
    if (fresh) {
      res = await rawFetch(path, options, fresh[ACCESS_FIELD]);
      if (res.status === 401) onUnauthorized();
    } else {
      onUnauthorized();
    }
  }

  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) throw parseError(res.status, data);
  return data;
}

// Biến { page: 1, q: "" } thành "?page=1" (bỏ giá trị rỗng)
function withQuery(path, params) {
  if (!params) return path;
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, v);
  });
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

const json = (body) => (body === undefined ? undefined : JSON.stringify(body));

export const api = {
  get: (path, { params, ...opts } = {}) =>
    request(withQuery(path, params), opts),
  post: (path, body, opts = {}) =>
    request(path, { ...opts, method: "POST", body: json(body) }),
  patch: (path, body, opts = {}) =>
    request(path, { ...opts, method: "PATCH", body: json(body) }),
  put: (path, body, opts = {}) =>
    request(path, { ...opts, method: "PUT", body: json(body) }),
  del: (path, opts = {}) => request(path, { ...opts, method: "DELETE" }),
};