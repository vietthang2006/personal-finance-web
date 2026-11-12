import { useState } from "react";
import { Button, FormError } from "@/shared/components";
import { formatMoney } from "@/shared/lib/formatMoney";
import { accountErrorMessage } from "../errorMessages";
import { useArchiveAccount, useDeleteAccount } from "../hooks";

export default function DeleteAccountModal({ account, onClose }) {
  const deleteMutation = useDeleteAccount();
  const archiveMutation = useArchiveAccount();
  const [error, setError] = useState("");
  const [hasHistoryConflict, setHasHistoryConflict] = useState(false);

  if (!account) return null;

  function handleConfirmDelete() {
    setError("");
    setHasHistoryConflict(false);

    deleteMutation.mutate(account.id, {
      onSuccess: () => onClose(),
      onError: (err) => {
        setError(accountErrorMessage(err));
        if (
          err.status === 409 ||
          err.code === "ACCOUNT_HAS_HISTORY" ||
          err.code === "ACCOUNT_HAS_TRANSACTIONS"
        ) {
          setHasHistoryConflict(true);
        }
      },
    });
  }

  function handleArchiveInstead() {
    setError("");
    archiveMutation.mutate(account.id, {
      onSuccess: () => onClose(),
      onError: (err) => setError(accountErrorMessage(err)),
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-account-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 id="delete-account-title" className="text-lg font-semibold text-gray-900">
          Xóa ví / tài khoản
        </h2>

        <p className="mt-2 text-sm text-gray-600">
          Bạn có chắc muốn xóa vĩnh viễn ví <strong>{account.name}</strong> (số dư{" "}
          <strong>{formatMoney(account.current_balance, account.currency_code)}</strong>)?
          Hành động này không thể hoàn tác.
        </p>

        <div className="mt-4">
          <FormError message={error} />
        </div>

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={deleteMutation.isPending || archiveMutation.isPending}
          >
            Hủy
          </Button>

          {hasHistoryConflict && !account.is_archived && (
            <Button
              variant="primary"
              loading={archiveMutation.isPending}
              onClick={handleArchiveInstead}
            >
              Chuyển sang Lưu trữ
            </Button>
          )}

          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={handleConfirmDelete}
          >
            Xóa vĩnh viễn
          </Button>
        </div>
      </div>
    </div>
  );
}
