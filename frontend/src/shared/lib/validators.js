export const EMAIL_RE = /^\S+@\S+\.\S+$/;
export const USERNAME_RE = /^[A-Za-z0-9_.-]{3,50}$/;

// Trả về chuỗi lỗi, hoặc "" nếu hợp lệ
export function passwordError(value) {
  if (value.length < 8) return "Mật khẩu tối thiểu 8 ký tự";
  if (new TextEncoder().encode(value).length > 72)
    return "Mật khẩu quá dài (tối đa 72 byte)";
  return "";
}