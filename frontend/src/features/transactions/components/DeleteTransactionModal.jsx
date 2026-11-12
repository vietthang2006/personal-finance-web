import { useState } from "react";
import { Button, FormError } from "@/shared/components";
import { transactionErrorMessage } from "../errorMessages";
import { useDeleteTransaction } from "../hooks";

export default function DeleteTransactionModal({ transaction, onClose }) {
  const deleteMutation = useDeleteTransaction();
  const [error, setError] = useState("");

  if (!transaction) return null;

  function handleConfirm() {
    setError("");
    deleteMutation.mutate(transaction.id, {
      onSuccess: () => onClose(),
      onError: (err) => setError(transactionErrorMessage(err)),
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-tx-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 id="delete-tx-title" className="text-lg font-semibold text-gray-900">
          Xóa giao dịch
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Bạn có chắc muốn xóa giao dịch này? Số dư ví sẽ được hoàn tác tự động và các hóa
          đơn đính kèm (nếu có) sẽ bị gỡ bỏ.
        </p>

        <div className="mt-4">
          <FormError message={error} />
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={deleteMutation.isPending}
          >
            Hủy
          </Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={handleConfirm}
          >
            Xóa giao dịch
          </Button>
        </div>
      </div>
    </div>
  );
}
