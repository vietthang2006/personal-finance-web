export const TRANSACTION_KINDS = [
  { value: "expense", label: "Chi tiêu", badgeClass: "bg-rose-50 text-rose-700 border-rose-200" },
  { value: "income", label: "Thu nhập", badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200" },
];

export const TRANSACTION_KIND_MAP = Object.fromEntries(
  TRANSACTION_KINDS.map((item) => [item.value, item])
);

export const TRANSFER_PURPOSES = [
  { value: "normal", label: "Chuyển khoản thường" },
  { value: "card_payment", label: "Thanh toán thẻ tín dụng" },
];

export const TRANSFER_PURPOSE_MAP = {
  normal: "Chuyển khoản thường",
  card_payment: "Thanh toán thẻ tín dụng",
  internal: "Chuyển nội bộ",
  credit_card_payment: "Thanh toán thẻ tín dụng",
};

export const ALLOWED_ATTACHMENT_TYPES = [
  "image/jpeg",
  "image/png",
  "application/pdf",
];

export const MAX_ATTACHMENTS_PER_TX = 5;
export const MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

export function todayISODate() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
