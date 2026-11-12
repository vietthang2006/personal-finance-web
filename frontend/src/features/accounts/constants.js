export const ACCOUNT_KINDS = [
  { value: "cash", label: "Tiền mặt", badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  { value: "bank", label: "Ngân hàng", badgeClass: "bg-blue-50 text-blue-700 border-blue-200" },
  { value: "e_wallet", label: "Ví điện tử", badgeClass: "bg-purple-50 text-purple-700 border-purple-200" },
  { value: "savings", label: "Tiết kiệm", badgeClass: "bg-amber-50 text-amber-700 border-amber-200" },
  { value: "credit_card", label: "Thẻ tín dụng", badgeClass: "bg-rose-50 text-rose-700 border-rose-200" },
];

export const ACCOUNT_KIND_MAP = Object.fromEntries(
  ACCOUNT_KINDS.map((item) => [item.value, item])
);

export const SUPPORTED_CURRENCIES = [
  { code: "VND", label: "VND - Việt Nam Đồng (₫)" },
  { code: "USD", label: "USD - Đô la Mỹ ($)" },
  { code: "EUR", label: "EUR - Euro (€)" },
  { code: "GBP", label: "GBP - Bảng Anh (£)" },
  { code: "JPY", label: "JPY - Yên Nhật (¥)" },
  { code: "KRW", label: "KRW - Won Hàn Quốc (₩)" },
];
