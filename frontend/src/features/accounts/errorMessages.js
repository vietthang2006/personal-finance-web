const CODE_MESSAGES = {
  NETWORK_ERROR: "Không kết nối được máy chủ. Vui lòng thử lại.",
  ACCOUNT_NOT_FOUND: "Không tìm thấy tài khoản hoặc ví này.",
  ACCOUNT_NAME_TAKEN: "Tên ví này đã tồn tại. Vui lòng chọn tên khác.",
  ACCOUNT_IMMUTABLE_FIELD:
    "Ví đã có lịch sử giao dịch nên không thể sửa loại ví, tiền tệ hoặc số dư ban đầu.",
  ACCOUNT_HAS_HISTORY:
    "Ví đã có lịch sử giao dịch nên không thể xóa vĩnh viễn. Bạn có thể chuyển sang Lưu trữ.",
  ACCOUNT_HAS_TRANSACTIONS:
    "Ví đã có lịch sử giao dịch nên không thể xóa vĩnh viễn. Bạn có thể chuyển sang Lưu trữ.",
  ACCOUNT_ARCHIVED: "Ví đã được lưu trữ.",
  UNSUPPORTED_CURRENCY: "Mã tiền tệ này hiện chưa được hệ thống hỗ trợ.",
  MISSING_RATE: "Chưa có tỷ giá quy đổi cho loại tiền tệ này.",
};

export function accountErrorMessage(err) {
  if (!err) return "Có lỗi xảy ra";
  if (err.code && CODE_MESSAGES[err.code]) {
    return CODE_MESSAGES[err.code];
  }
  if (err.status === 409) {
    return err.message || "Xung đột dữ liệu tài khoản.";
  }
  if (err.status === 422) {
    if (err.details && typeof err.details === "object") {
      const firstMsg = Object.values(err.details)[0];
      if (typeof firstMsg === "string") return firstMsg;
    }
    return err.message || "Dữ liệu nhập không hợp lệ.";
  }
  return err.message || "Có lỗi xảy ra. Vui lòng thử lại.";
}
