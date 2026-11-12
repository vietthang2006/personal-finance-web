import { useState } from "react";
import { Button, EmptyState, ErrorState, FormError, Spinner } from "@/shared/components";
import { formatDate, formatDateTime } from "@/shared/lib/formatDate";
import { formatMoney } from "@/shared/lib/formatMoney";
import { accountErrorMessage } from "../errorMessages";
import { useAccountHistory, useSnapshotAccount } from "../hooks";

export default function AccountHistoryModal({ account, onClose }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [snapshotMsg, setSnapshotMsg] = useState("");
  const [snapshotErr, setSnapshotErr] = useState("");

  const {
    data: history = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useAccountHistory(
    account?.id,
    { startDate: startDate || undefined, endDate: endDate || undefined },
    Boolean(account)
  );

  const snapshotMutation = useSnapshotAccount();

  if (!account) return null;

  function handleTakeSnapshot() {
    setSnapshotMsg("");
    setSnapshotErr("");
    snapshotMutation.mutate(account.id, {
      onSuccess: (res) => {
        setSnapshotMsg(`Đã lưu snapshot số dư ngày ${formatDate(res.snapshot_date)}.`);
      },
      onError: (err) => setSnapshotErr(accountErrorMessage(err)),
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="history-modal-title"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="history-modal-title" className="text-lg font-semibold text-gray-900">
              Lịch sử số dư — {account.name}
            </h2>
            <p className="text-xs text-gray-500">
              Số dư hiện tại:{" "}
              <strong>{formatMoney(account.current_balance, account.currency_code)}</strong>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        <div className="mb-4 flex flex-wrap items-end justify-between gap-3 rounded-lg bg-gray-50 p-3">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="hist-start" className="block text-xs font-medium text-gray-600">
                Từ ngày
              </label>
              <input
                id="hist-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="hist-end" className="block text-xs font-medium text-gray-600">
                Đến ngày
              </label>
              <input
                id="hist-end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
              />
            </div>
            {(startDate || endDate) && (
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-xs"
                onClick={() => {
                  setStartDate("");
                  setEndDate("");
                }}
              >
                Xóa lọc
              </Button>
            )}
          </div>

          <Button
            variant="primary"
            className="px-3 py-1.5 text-xs"
            loading={snapshotMutation.isPending}
            onClick={handleTakeSnapshot}
          >
            Chụp snapshot hôm nay
          </Button>
        </div>

        <FormError message={snapshotErr} />
        {snapshotMsg && (
          <p className="mb-3 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-700">
            {snapshotMsg}
          </p>
        )}

        {isLoading && <Spinner label="Đang tải lịch sử số dư..." />}

        {isError && (
          <ErrorState message={accountErrorMessage(error)} onRetry={() => refetch()} />
        )}

        {!isLoading && !isError && history.length === 0 && (
          <EmptyState text="Chưa có bản ghi lịch sử số dư nào trong khoảng thời gian này." />
        )}

        {!isLoading && !isError && history.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-2.5">Ngày ghi nhận</th>
                  <th className="px-4 py-2.5 text-right">Số dư</th>
                  <th className="px-4 py-2.5 text-right">Cập nhật lúc</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((item) => (
                  <tr key={item.snapshot_date} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">
                      {formatDate(item.snapshot_date)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold text-gray-900">
                      {formatMoney(item.balance, account.currency_code)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-xs text-gray-500">
                      {formatDateTime(item.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Đóng
          </Button>
        </div>
      </div>
    </div>
  );
}
