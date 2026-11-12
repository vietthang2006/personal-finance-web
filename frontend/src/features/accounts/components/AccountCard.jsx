import { Button } from "@/shared/components";
import { formatMoney } from "@/shared/lib/formatMoney";
import { ACCOUNT_KIND_MAP } from "../constants";

export default function AccountCard({
  account,
  defaultCurrency = "VND",
  onEdit,
  onDelete,
  onArchiveToggle,
  onViewHistory,
  archivingId,
}) {
  const kindInfo = ACCOUNT_KIND_MAP[account.kind] ?? {
    label: account.kind,
    badgeClass: "bg-gray-100 text-gray-700 border-gray-200",
  };

  const isCreditCard = account.kind === "credit_card";
  const currentNum = Number(account.current_balance);
  const isNegative = currentNum < 0;
  const showBase =
    account.currency_code !== defaultCurrency &&
    account.balance_base !== null &&
    account.balance_base !== undefined;

  const isArchivingThis = archivingId === account.id;

  return (
    <div
      className={[
        "flex flex-col justify-between rounded-xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md",
        account.is_archived ? "border-gray-200 opacity-75" : "border-gray-200",
      ].join(" ")}
    >
      <div>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${kindInfo.badgeClass}`}
              >
                {kindInfo.label}
              </span>
              {account.is_archived && (
                <span className="inline-block rounded-full border border-gray-300 bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                  Đã lưu trữ
                </span>
              )}
            </div>
            <h3 className="mt-2 truncate text-lg font-semibold text-gray-900">
              {account.name}
            </h3>
            {account.bank_name && (
              <p className="truncate text-xs text-gray-500">{account.bank_name}</p>
            )}
          </div>

          <span className="rounded-md bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-700">
            {account.currency_code}
          </span>
        </div>

        <div className="mt-4">
          <p className="text-xs text-gray-500">
            {isCreditCard ? "Số dư / Dư nợ hiện tại" : "Số dư hiện tại"}
          </p>
          <p
            className={[
              "mt-0.5 text-2xl font-bold",
              isNegative ? "text-rose-600" : "text-gray-900",
            ].join(" ")}
          >
            {formatMoney(account.current_balance, account.currency_code)}
          </p>
          {showBase && (
            <p className="mt-0.5 text-xs text-gray-500">
              ≈ {formatMoney(account.balance_base, defaultCurrency)}
            </p>
          )}
          {account.currency_code !== defaultCurrency &&
            (account.balance_base === null || account.balance_base === undefined) && (
              <p className="mt-0.5 text-xs text-amber-600">
                Chưa có tỷ giá quy đổi sang {defaultCurrency}
              </p>
            )}
        </div>

        {isCreditCard && (
          <div className="mt-3 rounded-lg bg-rose-50/60 p-3 text-xs text-gray-700">
            <div className="flex justify-between">
              <span className="text-gray-500">Hạn mức tín dụng:</span>
              <span className="font-semibold">
                {formatMoney(account.credit_limit, account.currency_code)}
              </span>
            </div>
            <div className="mt-1 flex justify-between">
              <span className="text-gray-500">Sao kê / Đến hạn:</span>
              <span className="font-medium">
                Ngày {account.billing_day} / Ngày {account.due_day}
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          onClick={() => onViewHistory(account)}
        >
          Lịch sử
        </Button>
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          onClick={() => onEdit(account)}
        >
          Sửa
        </Button>
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          loading={isArchivingThis}
          onClick={() => onArchiveToggle(account)}
        >
          {account.is_archived ? "Khôi phục" : "Lưu trữ"}
        </Button>
        <Button
          variant="danger"
          className="ml-auto px-3 py-1.5 text-xs"
          onClick={() => onDelete(account)}
        >
          Xóa
        </Button>
      </div>
    </div>
  );
}
