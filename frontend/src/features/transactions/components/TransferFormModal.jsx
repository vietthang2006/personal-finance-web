import { useMemo, useState } from "react";
import { Button, FormError, Input } from "@/shared/components";
import { formatMoney } from "@/shared/lib/formatMoney";
import { todayISODate, TRANSFER_PURPOSES } from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import { useCreateTransfer } from "../hooks";

export default function TransferFormModal({ accounts = [], onClose }) {
  const activeAccounts = useMemo(
    () => accounts.filter((a) => !a.is_archived),
    [accounts]
  );

  const [form, setForm] = useState(() => ({
    from_account_id: activeAccounts[0]?.id ?? "",
    to_account_id: activeAccounts[1]?.id ?? "",
    amount: "",
    exchange_rate: "",
    transaction_date: todayISODate(),
    purpose: "normal",
    description: "",
  }));

  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const createMutation = useCreateTransfer();

  const fromAcc = activeAccounts.find((a) => a.id === form.from_account_id);
  const toAcc = activeAccounts.find((a) => a.id === form.to_account_id);
  const isCrossCurrency =
    fromAcc && toAcc && fromAcc.currency_code !== toAcc.currency_code;

  function onChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    setServerError("");
  }

  function validate() {
    const errs = {};
    if (!form.from_account_id) errs.from_account_id = "Vui lòng chọn ví nguồn";
    if (!form.to_account_id) errs.to_account_id = "Vui lòng chọn ví đích";
    if (
      form.from_account_id &&
      form.to_account_id &&
      form.from_account_id === form.to_account_id
    ) {
      errs.to_account_id = "Ví nguồn và ví đích phải khác nhau";
    }

    const amt = Number(form.amount);
    if (!form.amount || Number.isNaN(amt) || amt <= 0) {
      errs.amount = "Số tiền chuyển phải lớn hơn 0";
    }

    if (isCrossCurrency && form.exchange_rate) {
      const rate = Number(form.exchange_rate);
      if (Number.isNaN(rate) || rate <= 0) {
        errs.exchange_rate = "Tỷ giá phải lớn hơn 0";
      }
    }

    if (!form.transaction_date) {
      errs.transaction_date = "Vui lòng chọn ngày chuyển khoản";
    } else if (form.transaction_date > todayISODate()) {
      errs.transaction_date = "Ngày chuyển khoản không được ở tương lai";
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e) {
    e.preventDefault();
    setServerError("");
    if (!validate()) return;

    const payload = {
      from_account_id: form.from_account_id,
      to_account_id: form.to_account_id,
      amount: String(form.amount).trim(),
      transaction_date: form.transaction_date,
      purpose: form.purpose,
      description: form.description.trim() || null,
    };
    if (isCrossCurrency && form.exchange_rate.trim()) {
      payload.exchange_rate = String(form.exchange_rate).trim();
    }

    createMutation.mutate(payload, {
      onSuccess: () => onClose(),
      onError: (err) => {
        if (err.details && typeof err.details === "object") {
          setFieldErrors((prev) => ({ ...prev, ...err.details }));
        }
        setServerError(transactionErrorMessage(err));
      },
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="transfer-form-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="transfer-form-title" className="text-lg font-semibold text-gray-900">
            Chuyển tiền giữa hai ví
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        <FormError message={serverError} />

        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="tr-from" className="text-sm font-medium">
                Từ ví *
              </label>
              <select
                id="tr-from"
                name="from_account_id"
                value={form.from_account_id}
                onChange={onChange}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">-- Chọn ví nguồn --</option>
                {activeAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({formatMoney(acc.current_balance, acc.currency_code)})
                  </option>
                ))}
              </select>
              {fieldErrors.from_account_id && (
                <small role="alert" className="text-sm text-red-600">
                  {fieldErrors.from_account_id}
                </small>
              )}
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="tr-to" className="text-sm font-medium">
                Đến ví *
              </label>
              <select
                id="tr-to"
                name="to_account_id"
                value={form.to_account_id}
                onChange={onChange}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">-- Chọn ví đích --</option>
                {activeAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({formatMoney(acc.current_balance, acc.currency_code)})
                  </option>
                ))}
              </select>
              {fieldErrors.to_account_id && (
                <small role="alert" className="text-sm text-red-600">
                  {fieldErrors.to_account_id}
                </small>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label={`Số tiền gửi${fromAcc ? ` (${fromAcc.currency_code})` : ""} *`}
              name="amount"
              type="number"
              min="0.01"
              step="any"
              value={form.amount}
              onChange={onChange}
              error={fieldErrors.amount}
            />
            <Input
              label="Ngày chuyển *"
              name="transaction_date"
              type="date"
              max={todayISODate()}
              value={form.transaction_date}
              onChange={onChange}
              error={fieldErrors.transaction_date}
            />
          </div>

          {isCrossCurrency && (
            <div className="mb-2 rounded-lg border border-blue-200 bg-blue-50/50 p-3">
              <p className="mb-2 text-xs text-blue-800">
                Chuyển khoản khác tiền tệ ({fromAcc.currency_code} → {toAcc.currency_code}
                ). Để trống tỷ giá để hệ thống tự tra cứu từ VCB.
              </p>
              <Input
                label="Tỷ giá quy đổi (tùy chọn)"
                name="exchange_rate"
                type="number"
                min="0.000001"
                step="any"
                placeholder="Ví dụ: 25400"
                value={form.exchange_rate}
                onChange={onChange}
                error={fieldErrors.exchange_rate}
              />
            </div>
          )}

          <div className="mb-4 flex flex-col gap-1">
            <label htmlFor="tr-purpose" className="text-sm font-medium">
              Mục đích
            </label>
            <select
              id="tr-purpose"
              name="purpose"
              value={form.purpose}
              onChange={onChange}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
            >
              {TRANSFER_PURPOSES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Ghi chú (tùy chọn)"
            name="description"
            placeholder="Ví dụ: Nạp tiền vào thẻ, chuyển tiết kiệm..."
            value={form.description}
            onChange={onChange}
          />

          <p className="mb-4 rounded-lg bg-gray-50 p-2.5 text-xs text-gray-500">
            Lưu ý: Giao dịch chuyển khoản mang tính bất biến (không thể sửa hoặc xóa sau
            khi tạo).
          </p>

          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Xác nhận chuyển
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
