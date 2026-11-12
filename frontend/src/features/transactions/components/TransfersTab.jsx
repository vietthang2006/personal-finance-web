import { useMemo, useState } from "react";
import { Button, EmptyState, ErrorState, Spinner } from "@/shared/components";
import { formatDate } from "@/shared/lib/formatDate";
import { formatMoney } from "@/shared/lib/formatMoney";
import { TRANSFER_PURPOSE_MAP } from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import { useTransfers } from "../hooks";
import TransferFormModal from "./TransferFormModal";

export default function TransfersTab({ accounts = [] }) {
  const [filters, setFilters] = useState({
    from_account_id: "",
    to_account_id: "",
    from_date: "",
    to_date: "",
  });
  const [showCreate, setShowCreate] = useState(false);

  const queryParams = useMemo(
    () => ({
      from_account_id: filters.from_account_id || undefined,
      to_account_id: filters.to_account_id || undefined,
      from_date: filters.from_date || undefined,
      to_date: filters.to_date || undefined,
    }),
    [filters]
  );

  const { data: transfers = [], isLoading, isError, error, refetch } = useTransfers(
    queryParams
  );

  const accountMap = useMemo(
    () => Object.fromEntries(accounts.map((a) => [a.id, a])),
    [accounts]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="f-tr-from" className="block text-xs font-medium text-gray-600">
              Từ ví
            </label>
            <select
              id="f-tr-from"
              value={filters.from_account_id}
              onChange={(e) =>
                setFilters((p) => ({ ...p, from_account_id: e.target.value }))
              }
              className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
            >
              <option value="">Tất cả</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="f-tr-to" className="block text-xs font-medium text-gray-600">
              Đến ví
            </label>
            <select
              id="f-tr-to"
              value={filters.to_account_id}
              onChange={(e) =>
                setFilters((p) => ({ ...p, to_account_id: e.target.value }))
              }
              className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
            >
              <option value="">Tất cả</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="f-tr-start" className="block text-xs font-medium text-gray-600">
              Từ ngày
            </label>
            <input
              id="f-tr-start"
              type="date"
              value={filters.from_date}
              onChange={(e) => setFilters((p) => ({ ...p, from_date: e.target.value }))}
              className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
            />
          </div>

          <div>
            <label htmlFor="f-tr-end" className="block text-xs font-medium text-gray-600">
              Đến ngày
            </label>
            <input
              id="f-tr-end"
              type="date"
              value={filters.to_date}
              onChange={(e) => setFilters((p) => ({ ...p, to_date: e.target.value }))}
              className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
            />
          </div>
        </div>

        <Button onClick={() => setShowCreate(true)}>+ Chuyển tiền giữa ví</Button>
      </div>

      {isLoading && <Spinner label="Đang tải lịch sử chuyển khoản..." />}

      {isError && (
        <ErrorState message={transactionErrorMessage(error)} onRetry={() => refetch()} />
      )}

      {!isLoading && !isError && transfers.length === 0 && (
        <EmptyState
          text="Chưa có giao dịch chuyển khoản nào."
          action={
            <Button onClick={() => setShowCreate(true)}>Tạo chuyển khoản đầu tiên</Button>
          }
        />
      )}

      {!isLoading && !isError && transfers.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Ngày</th>
                <th className="px-4 py-3">Từ ví → Đến ví</th>
                <th className="px-4 py-3 text-right">Số tiền gửi</th>
                <th className="px-4 py-3 text-right">Số tiền nhận</th>
                <th className="px-4 py-3 text-right">Tỷ giá</th>
                <th className="px-4 py-3">Mục đích & Ghi chú</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transfers.map((tr) => {
                const fromAcc = accountMap[tr.from_account_id];
                const toAcc = accountMap[tr.to_account_id];
                return (
                  <tr key={tr.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-gray-700">
                      {formatDate(tr.transaction_date)}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {fromAcc?.name ?? tr.from_account_id} →{" "}
                      {toAcc?.name ?? tr.to_account_id}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-semibold text-rose-600">
                      -{formatMoney(tr.amount, fromAcc?.currency_code ?? "VND")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-semibold text-emerald-700">
                      +{formatMoney(tr.to_amount, toAcc?.currency_code ?? "VND")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-xs text-gray-500">
                      {Number(tr.exchange_rate)}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      <span className="inline-block rounded bg-gray-100 px-2 py-0.5 font-medium text-gray-700">
                        {TRANSFER_PURPOSE_MAP[tr.purpose] ?? tr.purpose}
                      </span>
                      {tr.description && (
                        <p className="mt-1 text-gray-500">{tr.description}</p>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <TransferFormModal accounts={accounts} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
