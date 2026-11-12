import { formatMoney } from "@/shared/lib/formatMoney";

export default function AccountSummaryCards({ summary }) {
  const {
    default_currency = "VND",
    total_assets_base = 0,
    total_liabilities_base = 0,
    net_worth_base = 0,
    accounts = [],
    warnings = [],
  } = summary ?? {};

  const missingRateAccounts = accounts.filter(
    (acc) => acc.balance_base === null || acc.balance_base === undefined
  );

  const cards = [
    {
      label: "Tổng tài sản",
      value: formatMoney(total_assets_base, default_currency),
      sub: "Tổng số dư dương các ví",
      valueClass: "text-emerald-700",
    },
    {
      label: "Tổng dư nợ thẻ",
      value: formatMoney(total_liabilities_base, default_currency),
      sub: "Dư nợ thẻ tín dụng hiện tại",
      valueClass: "text-rose-600",
    },
    {
      label: "Tài sản ròng",
      value: formatMoney(net_worth_base, default_currency),
      sub: `Quy đổi theo ${default_currency}`,
      valueClass: Number(net_worth_base) < 0 ? "text-rose-600" : "text-blue-700",
    },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-gray-500">{card.label}</p>
            <p className={`mt-2 text-2xl font-bold ${card.valueClass}`}>
              {card.value}
            </p>
            <p className="mt-1 text-xs text-gray-400">{card.sub}</p>
          </div>
        ))}
      </div>

      {(warnings.length > 0 || missingRateAccounts.length > 0) && (
        <div
          role="status"
          className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
        >
          <p className="font-medium">Lưu ý quy đổi tỷ giá:</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs">
            {warnings.map((w, idx) => (
              <li key={idx}>{typeof w === "string" ? w : w.message ?? w.code}</li>
            ))}
            {warnings.length === 0 &&
              missingRateAccounts.map((acc) => (
                <li key={acc.id}>
                  Ví <strong>{acc.name}</strong> ({acc.currency_code}) chưa có tỷ giá
                  quy đổi sang {default_currency}, tạm chưa tính vào tổng tài sản.
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
