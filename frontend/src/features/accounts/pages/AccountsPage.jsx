import { useMemo, useState } from "react";
import { Button, EmptyState, ErrorState, FormError, Spinner } from "@/shared/components";
import AccountCard from "../components/AccountCard";
import AccountFormModal from "../components/AccountFormModal";
import AccountHistoryModal from "../components/AccountHistoryModal";
import AccountSummaryCards from "../components/AccountSummaryCards";
import DeleteAccountModal from "../components/DeleteAccountModal";
import { ACCOUNT_KINDS } from "../constants";
import { accountErrorMessage } from "../errorMessages";
import {
  useAccounts,
  useArchiveAccount,
  useUnarchiveAccount,
} from "../hooks";

export default function AccountsPage() {
  const [showArchivedOnly, setShowArchivedOnly] = useState(false);
  const [kindFilter, setKindFilter] = useState("all");
  const [formModalState, setFormModalState] = useState(null); // null | { account: Account | null }
  const [deletingAccount, setDeletingAccount] = useState(null);
  const [historyAccount, setHistoryAccount] = useState(null);
  const [actionError, setActionError] = useState("");
  const [archivingId, setArchivingId] = useState(null);

  const { data, isLoading, isError, error, refetch } = useAccounts({
    includeArchived: showArchivedOnly,
  });

  const archiveMutation = useArchiveAccount();
  const unarchiveMutation = useUnarchiveAccount();

  const accountsByArchive = useMemo(() => {
    const raw = data?.accounts ?? [];
    return showArchivedOnly
      ? raw.filter((acc) => acc.is_archived)
      : raw.filter((acc) => !acc.is_archived);
  }, [data?.accounts, showArchivedOnly]);

  const defaultCurrency = data?.default_currency ?? "VND";

  const filteredAccounts = useMemo(() => {
    if (kindFilter === "all") return accountsByArchive;
    return accountsByArchive.filter((acc) => acc.kind === kindFilter);
  }, [accountsByArchive, kindFilter]);

  function handleArchiveToggle(account) {
    setActionError("");
    setArchivingId(account.id);
    const mutation = account.is_archived ? unarchiveMutation : archiveMutation;
    mutation.mutate(account.id, {
      onError: (err) => setActionError(accountErrorMessage(err)),
      onSettled: () => setArchivingId(null),
    });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quản lý Ví & Tài khoản</h1>
          <p className="text-sm text-gray-500">
            Theo dõi số dư, thẻ tín dụng và tổng tài sản ròng theo đa tiền tệ.
          </p>
        </div>

        <Button onClick={() => setFormModalState({ account: null })}>
          + Thêm ví / thẻ
        </Button>
      </div>

      {isLoading && <Spinner label="Đang tải danh sách ví..." />}

      {isError && (
        <ErrorState message={accountErrorMessage(error)} onRetry={() => refetch()} />
      )}

      {!isLoading && !isError && (
        <>
          <AccountSummaryCards summary={data} />

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => setKindFilter("all")}
                className={[
                  "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                  kindFilter === "all"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200",
                ].join(" ")}
              >
                Tất cả ({accountsByArchive.length})
              </button>
              {ACCOUNT_KINDS.map((k) => {
                const count = accountsByArchive.filter((a) => a.kind === k.value).length;
                return (
                  <button
                    key={k.value}
                    type="button"
                    onClick={() => setKindFilter(k.value)}
                    className={[
                      "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                      kindFilter === k.value
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200",
                    ].join(" ")}
                  >
                    {k.label} ({count})
                  </button>
                );
              })}
            </div>

            <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showArchivedOnly}
                onChange={(e) => setShowArchivedOnly(e.target.checked)}
                className="size-4 rounded border-gray-300 text-blue-600"
              />
              <span>Chỉ hiện ví đã lưu trữ</span>
            </label>
          </div>

          <FormError message={actionError} />

          {filteredAccounts.length === 0 ? (
            <EmptyState
              text={
                showArchivedOnly
                  ? "Chưa có ví nào được lưu trữ."
                  : accountsByArchive.length === 0
                    ? "Bạn chưa có ví hoặc tài khoản nào."
                    : "Không có ví nào phù hợp với bộ lọc hiện tại."
              }
              action={
                !showArchivedOnly &&
                accountsByArchive.length === 0 && (
                  <Button onClick={() => setFormModalState({ account: null })}>
                    Tạo ví đầu tiên
                  </Button>
                )
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredAccounts.map((account) => (
                <AccountCard
                  key={account.id}
                  account={account}
                  defaultCurrency={defaultCurrency}
                  archivingId={archivingId}
                  onEdit={(acc) => setFormModalState({ account: acc })}
                  onDelete={(acc) => setDeletingAccount(acc)}
                  onArchiveToggle={handleArchiveToggle}
                  onViewHistory={(acc) => setHistoryAccount(acc)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {formModalState && (
        <AccountFormModal
          account={formModalState.account}
          defaultCurrency={defaultCurrency}
          onClose={() => setFormModalState(null)}
        />
      )}

      {deletingAccount && (
        <DeleteAccountModal
          account={deletingAccount}
          onClose={() => setDeletingAccount(null)}
        />
      )}

      {historyAccount && (
        <AccountHistoryModal
          account={historyAccount}
          onClose={() => setHistoryAccount(null)}
        />
      )}
    </div>
  );
}
