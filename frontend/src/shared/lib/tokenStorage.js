const KEY = "pf_tokens";

export const tokenStorage = {
  // Trả về object token đã lưu, hoặc null nếu chưa có / dữ liệu hỏng
  get() {
    try {
      return JSON.parse(localStorage.getItem(KEY));
    } catch {
      return null;
    }
  },

  // Lưu nguyên object backend trả về, không phụ thuộc tên trường token
  set(tokens) {
    try {
      localStorage.setItem(KEY, JSON.stringify(tokens));
    } catch {
      // Bỏ qua nếu trình duyệt chặn localStorage (chế độ riêng tư...)
    }
  },

  clear() {
    try {
      localStorage.removeItem(KEY);
    } catch {
      // bỏ qua
    }
  },
};