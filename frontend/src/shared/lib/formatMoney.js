const formatters = {};

function getFormatter(currency) {
  if (!formatters[currency]) {
    formatters[currency] = new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency,
    });
  }
  return formatters[currency];
}

/**
 * Chỉ dùng để HIỂN THỊ. Backend trả số tiền dạng chuỗi decimal ("85000.00").
 * Không dùng kết quả hoặc Number() để cộng trừ tiền.
 */
export function formatMoney(value, currency = "VND") {
  if (value === null || value === undefined || value === "") return "—";

  const n = Number(value);
  if (Number.isNaN(n)) return "—";

  try {
    return getFormatter(currency).format(n);
  } catch {
    // Mã tiền tệ lạ: hiển thị số kèm mã
    return `${n.toLocaleString("vi-VN")} ${currency}`;
  }
}