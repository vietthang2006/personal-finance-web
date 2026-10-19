const NETWORK = "Không kết nối được máy chủ. Vui lòng thử lại";

export function loginErrorMessage(err) {
  if (err.code === "NETWORK_ERROR") return NETWORK;
  if (err.status === 429)
    return "Bạn thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại";
  if (err.status === 401) {
    // [XÁC NHẬN] Backend trả riêng "Account is locked" cho tài khoản bị khóa.
    // Dựa vào chuỗi nên dễ gãy; nên đề nghị backend thêm mã lỗi (xem cuối bài)
    if (/locked/i.test(err.message))
      return "Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên";
    return "Email hoặc mật khẩu không đúng";
  }
  if (err.status === 422) return "Email hoặc mật khẩu không hợp lệ";
  return err.message;
}

export function registerErrorMessage(err) {
  if (err.code === "NETWORK_ERROR") return NETWORK;
  // Backend dùng một câu chung cho trùng email và trùng username
  if (err.status === 409) return "Email hoặc tên đăng nhập đã được sử dụng";
  return err.message;
}