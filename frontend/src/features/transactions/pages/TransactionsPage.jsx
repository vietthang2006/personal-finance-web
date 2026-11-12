import { useMemo, useState } from "react";
import { useAccounts } from "@/features/accounts/hooks";
import { Button, EmptyState, ErrorState, Spinner } from "@/shared/components";
import { formatDate } from "@/shared/lib/formatDate";
import { formatMoney } from "@/shared/lib/formatMoney";
import CategoriesTab from "../components/CategoriesTab";
import DeleteTransactionModal from "../components/DeleteTransactionModal";
import TagsTab from "../components/TagsTab";
import TransactionDetailModal from "../components/TransactionDetailModal";
import TransactionFormModal from "../components/TransactionFormModal";
import TransfersTab from "../components/TransfersTab";
import { TRANSACTION_KIND_MAP } from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import { useCategories, useTransactions } from "../hooks";

const TABS = [
  { id: "transactions", label: "Giao dịch Thu / Chi" },
  { id: "transfers", label: "Chuyển khoản" },
  { id: "categories", label: "Danh mục" },
  { id: "tags", label: "Nhãn (Tags)" },
];

export default function TransactionsPage() {
  const [activeTab, setActiveTab] = useState("transactions");
  const [filters, setFilters] = useState({
    account_id: "",
    kind: "",
    category_id: "",
    from_date: "",
    to_date: "",
  });

  const [formState, setFormState] = useState(null); // null | { transaction: tx | null }
  const [detailTx, setDetailTx] = useState(null);
  const [deletingTx, setDeletingTx] = useState(null);

  const { data: accountsData } = useAccounts({ includeArchived: true });
  const accounts = useMemo(
    () => accountsData?.accounts ?? [],
    [accountsData?.accounts]
  );

  const { data: categories = [] } = useCategories({ includeInactive: true });

  const queryParams = useMemo(
    () => ({
      account_id: filters.account_id || undefined,
      kind: filters.kind || undefined,
      category_id: filters.category_id ? Number(filters.category_id) : undefined,
      from_date: filters.from_date || undefined,
      to_date: filters.to_date || undefined,
    }),
    [filters]
  );

  const {
    data: transactions = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useTransactions(queryParams);

  const accountMap = useMemo(
    () => Object.fromEntries(accounts.map((a) => [a.id, a])),
    [accounts]
  );
  const categoryMap = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.id, c])),
    [categories]
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Giao dịch, Danh mục & Chuyển khoản
          </h1>
          <p className="text-sm text-gray-500">
            Ghi nhận thu chi, đính kèm hóa đơn, chuyển tiền giữa các ví và quản lý danh
            mục.
          </p>
        </div>

        {activeTab === "transactions" && (
          <Button onClick={() => setFormState({ transaction: null })}>
            + Thêm giao dịch
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={[
              "border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-800",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Giao dịch Thu / Chi */}
      {activeTab === "transactions" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div>
              <label htmlFor="f-tx-acc" className="block text-xs font-medium text-gray-600">
                Ví
              </label>
              <select
                id="f-tx-acc"
                value={filters.account_id}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, account_id: e.target.value }))
                }
                className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
              >
                <option value="">Tất cả ví</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="f-tx-kind" className="block text-xs font-medium text-gray-600">
                Loại
              </label>
              <select
                id="f-tx-kind"
                value={filters.kind}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, kind: e.target.value, category_id: "" }))
                }
                className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
              >
                <option value="">Tất cả</option>
                <option value="expense">Chi tiêu</option>
                <option value="income">Thu nhập</option>
              </select>
            </div>

            <div>
              <label htmlFor="f-tx-cat" className="block text-xs font-medium text-gray-600">
                Danh mục
              </label>
              <select
                id="f-tx-cat"
                value={filters.category_id}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, category_id: e.target.value }))
                }
                className="mt-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
              >
                <option value="">Tất cả</option>
                {categories
                  .filter((c) => !filters.kind || c.kind === filters.kind)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label htmlFor="f-tx-start" className="block text-xs font-medium text-gray-600">
                Từ ngày
              </label>
              <input
                id="f-tx-start"
                type="date"
                value={filters.from_date}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, from_date: e.target.value }))
                }
                className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
              />
            </div>

            <div>
              <label htmlFor="f-tx-end" className="block text-xs font-medium text-gray-600">
                Đến ngày
              </label>
              <input
                id="f-tx-end"
                type="date"
                value={filters.to_date}
                onChange={(e) => setFilters((p) => ({ ...p, to_date: e.target.value }))}
                className="mt-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-sm"
              />
            </div>

            {(filters.account_id ||
              filters.kind ||
              filters.category_id ||
              filters.from_date ||
              filters.to_date) && (
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-xs"
                onClick={() =>
                  setFilters({
                    account_id: "",
                    kind: "",
                    category_id: "",
                    from_date: "",
                    to_date: "",
                  })
                }
              >
                Xóa lọc
              </Button>
            )}
          </div>

          {isLoading && <Spinner label="Đang tải danh sách giao dịch..." />}

          {isError && (
            <ErrorState
              message={transactionErrorMessage(error)}
              onRetry={() => refetch()}
            />
          )}

          {!isLoading && !isError && transactions.length === 0 && (
            <EmptyState
              text="Chưa có giao dịch nào phù hợp."
              action={
                <Button onClick={() => setFormState({ transaction: null })}>
                  Tạo giao dịch đầu tiên
                </Button>
              }
            />
          )}

          {!isLoading && !isError && transactions.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-3 py-3">Ngày</th>
                    <th className="px-3 py-3">Loại & Danh mục</th>
                    <th className="px-3 py-3">Ví</th>
                    <th className="px-3 py-3">Mô tả / Đối tác</th>
                    <th className="px-3 py-3 text-right">Số tiền</th>
                    <th className="px-3 py-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {transactions.map((tx) => {
                    const acc = accountMap[tx.account_id];
                    const cat = tx.category_id ? categoryMap[tx.category_id] : null;
                    const kindInfo = TRANSACTION_KIND_MAP[tx.kind] ?? {
                      label: tx.kind,
                      badgeClass: "bg-gray-100 text-gray-700 border-gray-200",
                    };
                    const isExpense = tx.kind === "expense";

                    return (
                      <tr key={tx.id} className="hover:bg-gray-50">
                        <td className="whitespace-nowrap px-3 py-2.5 text-gray-700">
                          {formatDate(tx.transaction_date)}
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${kindInfo.badgeClass}`}
                            >
                              {kindInfo.label}
                            </span>
                            {cat && (
                              <span className="text-xs font-medium text-gray-800">
                                {cat.icon ? `${cat.icon} ` : ""}
                                {cat.name}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-gray-700">
                          {acc?.name ?? tx.account_id}
                        </td>
                        <td className="px-3 py-2.5">
                          <p className="font-medium text-gray-900">
                            {tx.merchant || tx.description || "—"}
                          </p>
                          {tx.merchant && tx.description && (
                            <p className="text-xs text-gray-500">{tx.description}</p>
                          )}
                          {tx.source !== "manual" && (
                            <span className="mt-0.5 inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500">
                              Nguồn: {tx.source}
                            </span>
                          )}
                        </td>
                        <td
                          className={[
                            "whitespace-nowrap px-3 py-2.5 text-right font-bold",
                            isExpense ? "text-rose-600" : "text-emerald-700",
                          ].join(" ")}
                        >
                          {isExpense ? "-" : "+"}
                          {formatMoney(tx.amount, acc?.currency_code ?? "VND")}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <div className="flex flex-wrap justify-end gap-1.5">
                            <Button
                              variant="secondary"
                              className="px-2.5 py-1 text-xs"
                              onClick={() => setDetailTx(tx)}
                            >
                              Hóa đơn / Nhãn
                            </Button>
                            <Button
                              variant="secondary"
                              className="px-2.5 py-1 text-xs"
                              onClick={() => setFormState({ transaction: tx })}
                            >
                              Sửa
                            </Button>
                            <Button
                              variant="danger"
                              className="px-2.5 py-1 text-xs"
                              onClick={() => setDeletingTx(tx)}
                            >
                              Xóa
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "transfers" && <TransfersTab accounts={accounts} />}
      {activeTab === "categories" && <CategoriesTab />}
      {activeTab === "tags" && <TagsTab />}

      {formState && (
        <TransactionFormModal
          transaction={formState.transaction}
          accounts={accounts}
          onClose={() => setFormState(null)}
        />
      )}

      {detailTx && (
        <TransactionDetailModal
          transaction={detailTx}
          onClose={() => setDetailTx(null)}
        />
      )}

      {deletingTx && (
        <DeleteTransactionModal
          transaction={deletingTx}
          onClose={() => setDeletingTx(null)}
        />
      )}
    </div>
  );
}
