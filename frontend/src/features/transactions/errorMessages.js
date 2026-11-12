const CODE_MESSAGES = {
  NETWORK_ERROR: "Không kết nối được máy chủ. Vui lòng thử lại.",
  ACCOUNT_NOT_FOUND: "Không tìm thấy ví đã chọn.",
  ACCOUNT_ARCHIVED: "Ví đã bị lưu trữ, không thể thực hiện giao dịch.",
  CATEGORY_NOT_FOUND: "Không tìm thấy danh mục.",
  CATEGORY_KIND_MISMATCH: "Danh mục không khớp với loại giao dịch (Thu/Chi).",
  SUBCATEGORY_MISMATCH: "Danh mục con không thuộc danh mục đã chọn.",
  TAG_NOT_FOUND: "Có nhãn không tồn tại hoặc không thuộc quyền sở hữu của bạn.",
  FUTURE_DATE: "Ngày giao dịch không được lớn hơn ngày hiện tại.",
  INSUFFICIENT_FUNDS: "Số dư ví không đủ để thực hiện giao dịch này.",
  CREDIT_LIMIT_EXCEEDED: "Giao dịch vượt quá hạn mức thẻ tín dụng.",
  TX_LOCKED_BY_SOURCE:
    "Giao dịch được tạo từ Mục tiêu hoặc Khoản vay nên không thể sửa số tiền, ví hoặc loại giao dịch.",
  SAME_ACCOUNT: "Ví nguồn và ví đích phải khác nhau.",
  RATE_UNAVAILABLE: "Chưa có tỷ giá quy đổi cho cặp tiền tệ này. Vui lòng nhập tỷ giá thủ công.",
};

const MESSAGE_PATTERNS = [
  [
    /insufficient funds|exceeds.*credit limit|available balance/i,
    "Số dư ví nguồn không đủ hoặc vượt quá hạn mức thẻ tín dụng.",
  ],
  [
    /exchange rate|rate unavailable|no rate/i,
    "Chưa có tỷ giá quy đổi cho cặp tiền tệ này. Vui lòng nhập tỷ giá thủ công.",
  ],
  [/must be distinct|same account/i, "Ví nguồn và ví đích phải khác nhau."],
  [/archived/i, "Ví đã bị lưu trữ, không thể thực hiện giao dịch."],
  [/in the future/i, "Ngày giao dịch không được lớn hơn ngày hiện tại."],
  [/already exists|duplicate/i, "Dữ liệu này đã tồn tại."],
  [/account not found/i, "Không tìm thấy ví đã chọn."],
  [/category not found/i, "Không tìm thấy danh mục."],
  [/transaction not found/i, "Không tìm thấy giao dịch."],
  [
    /system categories are read-only/i,
    "Danh mục hệ thống chỉ được xem, không thể thêm hoặc sửa danh mục con.",
  ],
];

function translateRawMessage(msg) {
  if (!msg || typeof msg !== "string") return null;
  for (const [pattern, vi] of MESSAGE_PATTERNS) {
    if (pattern.test(msg)) return vi;
  }
  return null;
}

export function transactionErrorMessage(err) {
  if (!err) return "Có lỗi xảy ra";
  if (err.code && CODE_MESSAGES[err.code]) {
    return CODE_MESSAGES[err.code];
  }
  const translated = translateRawMessage(err.message);
  if (translated) return translated;

  if (err.status === 413) {
    return "Dung lượng tệp đính kèm vượt quá giới hạn cho phép (tối đa 10MB).";
  }
  if (err.status === 415) {
    return "Định dạng tệp không được hỗ trợ. Chỉ chấp nhận JPG, PNG hoặc PDF.";
  }
  if (err.status === 422) {
    if (err.details && typeof err.details === "object") {
      const firstMsg = Object.values(err.details)[0];
      if (typeof firstMsg === "string") {
        return translateRawMessage(firstMsg) || firstMsg;
      }
    }
    return "Dữ liệu nhập không hợp lệ. Vui lòng kiểm tra lại.";
  }
  return err.message || "Có lỗi xảy ra. Vui lòng thử lại.";
}
