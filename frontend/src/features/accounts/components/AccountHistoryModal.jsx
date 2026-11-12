import { useMemo, useState } from "react";
import {
  useCategories,
  useTransactions,
  useTransfers,
} from "@/features/transactions/hooks";
import { TRANSACTION_KIND_MAP } from "@/features/transactions/constants";
import { Button, EmptyState, ErrorState, FormError, Spinner } from "@/shared/components";
import { formatDate, formatDateTime } from "@/shared/lib/formatDate";
import { formatMoney } from "@/shared/lib/formatMoney";
import { accountErrorMessage } from "../errorMessages";
import { useAccountHistory, useAccounts, useSnapshotAccount } from "../hooks";

export default function AccountHistoryModal({ account, onClose }) {
  const [activeTab, setActiveTab] = useState("transactions"); // "transactions" | "balance"
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [snapshotMsg, setSnapshotMsg] = useState("");
  const [snapshotErr, setSnapshotErr] = useState("");

  const {
    data: history = [],
    isLoading: loadingBalance,
    isError: isBalanceError,
    error: balanceError,
    refetch: refetchBalance,
  } = useAccountHistory(
    account?.id,
    { startDate: startDate || undefined, endDate: endDate || undefined },
    Boolean(account) && activeTab === "balance"
  );

  const txFilters = useMemo(
    () => ({
      account_id: account?.id,
      from_date: startDate || undefined,
      to_date: endDate || undefined,
    }),
    [account?.id, startDate, endDate]
  );

  const outTransferFilters = useMemo(
    () => ({
      from_account_id: account?.id,
      from_date: startDate || undefined,
      to_date: endDate || undefined,
    }),
    [account?.id, startDate, endDate]
  );

  const inTransferFilters = useMemo(
    () => ({
      to_account_id: account?.id,
      from_date: startDate || undefined,
      to_date: endDate || undefined,
    }),
    [account?.id, startDate, endDate]
  );

  const {
    data: transactions = [],
    isLoading: loadingTx,
    isError: isTxError,
    error: txError,
    refetch: refetchTx,
  } = useTransactions(txFilters);

  const {
    data: outTransfers = [],
    isLoading: loadingOut,
    isError: isOutError,
    error: outError,
    refetch: refetchOut,
  } = useTransfers(outTransferFilters);

  const {
    data: inTransfers = [],
    isLoading: loadingIn,
    isError: isInError,
    error: inError,
    refetch: refetchIn,
  } = useTransfers(inTransferFilters);

  const { data: accountsData } = useAccounts({ includeArchived: true });
  const accountMap = useMemo(
    () => Object.fromEntries((accountsData?.accounts ?? []).map((a) => [a.id, a])),
    [accountsData?.accounts]
  );

  const { data: categories = [] } = useCategories({ includeInactive: true });
  const categoryMap = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.id, c])),
    [categories]
  );

  const combinedItems = useMemo(() => {
    const txItems = transactions.map((tx) => {
      const cat = tx.category_id ? categoryMap[tx.category_id] : null;
      const kindInfo = TRANSACTION_KIND_MAP[tx.kind] ?? {
        label: tx.kind,
        badgeClass: "bg-gray-100 text-gray-700 border-gray-200",
      };
      return {
        key: `tx-${tx.id}`,
        date: tx.transaction_date,
        createdAt: tx.created_at,
        badgeLabel: kindInfo.label,
        badgeClass: kindInfo.badgeClass,
        subLabel: cat ? `${cat.icon ? `${cat.icon} ` : ""}${cat.name}` : "",
        description: tx.merchant || tx.description || "—",
        isNegative: tx.kind === "expense",
        amount: tx.amount,
      };
    });

    const outItems = outTransfers.map((tr) => {
      const toAcc = accountMap[tr.to_account_id];
      return {
        key: `tr-out-${tr.id}`,
        date: tr.transaction_date,
        createdAt: tr.created_at,
        badgeLabel: "Chuyển đi",
        badgeClass: "bg-amber-50 text-amber-700 border-amber-200",
        subLabel: `Đến: ${toAcc?.name ?? tr.to_account_id}`,
        description: tr.description || "Chuyển tiền giữa hai ví",
        isNegative: true,
        amount: tr.amount,
      };
    });

    const inItems = inTransfers.map((tr) => {
      const fromAcc = accountMap[tr.from_account_id];
      return {
        key: `tr-in-${tr.id}`,
        date: tr.transaction_date,
        createdAt: tr.created_at,
        badgeLabel: "Nhận chuyển",
        badgeClass: "bg-blue-50 text-blue-700 border-blue-200",
        subLabel: `Từ: ${fromAcc?.name ?? tr.from_account_id}`,
        description: tr.description || "Nhận tiền từ ví khác",
        isNegative: false,
        amount: tr.to_amount,
      };
    });

    return [...txItems, ...outItems, ...inItems].sort((a, b) => {
      if (a.date !== b.date) return a.date < b.date ? 1 : -1;
      return String(b.createdAt).localeCompare(String(a.createdAt));
    });
  }, [transactions, outTransfers, inTransfers, categoryMap, accountMap]);

  const loadingCombined = loadingTx || loadingOut || loadingIn;
  const isCombinedError = isTxError || isOutError || isInError;
  const combinedError = txError || outError || inError;

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
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="history-modal-title" className="text-lg font-semibold text-gray-900">
              Lịch sử — {account.name}
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

        {/* Tabs */}
        <div className="mb-4 flex gap-1 border-b border-gray-200">
          <button
            type="button"
            onClick={() => setActiveTab("transactions")}
            className={[
              "border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              activeTab === "transactions"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-800",
            ].join(" ")}
          >
            Lịch sử giao dịch ({combinedItems.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("balance")}
            className={[
              "border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              activeTab === "balance"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-800",
            ].join(" ")}
          >
            Lịch sử số dư
          </button>
        </div>

        {/* Bộ lọc ngày dùng chung */}
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

          {activeTab === "balance" && (
            <Button
              variant="primary"
              className="px-3 py-1.5 text-xs"
              loading={snapshotMutation.isPending}
              onClick={handleTakeSnapshot}
            >
              Chụp snapshot hôm nay
            </Button>
          )}
        </div>

        {/* Tab 1: Lịch sử giao dịch + chuyển khoản của ví */}
        {activeTab === "transactions" && (
          <>
            {loadingCombined && <Spinner label="Đang tải lịch sử giao dịch..." />}

            {isCombinedError && (
              <ErrorState
                message={accountErrorMessage(combinedError)}
                onRetry={() => {
                  refetchTx();
                  refetchOut();
                  refetchIn();
                }}
              />
            )}

            {!loadingCombined && !isCombinedError && combinedItems.length === 0 && (
              <EmptyState text="Ví này chưa có giao dịch hoặc chuyển khoản nào trong khoảng thời gian đã chọn." />
            )}

            {!loadingCombined && !isCombinedError && combinedItems.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-3 py-2.5">Ngày</th>
                      <th className="px-3 py-2.5">Loại / Chi tiết</th>
                      <th className="px-3 py-2.5">Mô tả</th>
                      <th className="px-3 py-2.5 text-right">Số tiền</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {combinedItems.map((item) => (
                      <tr key={item.key} className="hover:bg-gray-50">
                        <td className="whitespace-nowrap px-3 py-2.5 text-gray-700">
                          {formatDate(item.date)}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${item.badgeClass}`}
                            >
                              {item.badgeLabel}
                            </span>
                            {item.subLabel && (
                              <span className="text-xs font-medium text-gray-800">
                                {item.subLabel}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-gray-700">
                          {item.description}
                        </td>
                        <td
                          className={[
                            "whitespace-nowrap px-3 py-2.5 text-right font-semibold",
                            item.isNegative ? "text-rose-600" : "text-emerald-700",
                          ].join(" ")}
                        >
                          {item.isNegative ? "-" : "+"}
                          {formatMoney(item.amount, account.currency_code)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* Tab 2: Lịch sử số dư (Snapshot) */}
        {activeTab === "balance" && (
          <>
            <FormError message={snapshotErr} />
            {snapshotMsg && (
              <p className="mb-3 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-700">
                {snapshotMsg}
              </p>
            )}

            {loadingBalance && <Spinner label="Đang tải lịch sử số dư..." />}

            {isBalanceError && (
              <ErrorState
                message={accountErrorMessage(balanceError)}
                onRetry={() => refetchBalance()}
              />
            )}

            {!loadingBalance && !isBalanceError && history.length === 0 && (
              <EmptyState text="Chưa có bản ghi lịch sử số dư nào trong khoảng thời gian này." />
            )}

            {!loadingBalance && !isBalanceError && history.length > 0 && (
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
          </>
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
