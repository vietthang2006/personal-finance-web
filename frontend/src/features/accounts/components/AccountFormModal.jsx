import { useState } from "react";
import { Button, FormError, Input } from "@/shared/components";
import { ACCOUNT_KINDS, SUPPORTED_CURRENCIES } from "../constants";
import { accountErrorMessage } from "../errorMessages";
import { useCreateAccount, useUpdateAccount } from "../hooks";

function buildInitialForm(account, defaultCurrency) {
  if (account) {
    return {
      name: account.name ?? "",
      kind: account.kind ?? "cash",
      currency_code: account.currency_code ?? defaultCurrency,
      bank_name: account.bank_name ?? "",
      opening_balance: String(account.opening_balance ?? "0"),
      credit_limit: account.credit_limit != null ? String(account.credit_limit) : "",
      billing_day: account.billing_day != null ? String(account.billing_day) : "",
      due_day: account.due_day != null ? String(account.due_day) : "",
    };
  }
  return {
    name: "",
    kind: "cash",
    currency_code: defaultCurrency || "VND",
    bank_name: "",
    opening_balance: "0",
    credit_limit: "",
    billing_day: "15",
    due_day: "5",
  };
}

export default function AccountFormModal({
  account = null,
  defaultCurrency = "VND",
  onClose,
}) {
  const isEdit = Boolean(account);
  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount();

  const [form, setForm] = useState(() => buildInitialForm(account, defaultCurrency));
  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState("");

  const isCreditCard = form.kind === "credit_card";
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  function onChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    setServerError("");
  }

  function validate() {
    const errs = {};
    const trimmedName = form.name.trim();
    if (!trimmedName) {
      errs.name = "Vui lòng nhập tên ví";
    } else if (trimmedName.length > 100) {
      errs.name = "Tên ví tối đa 100 ký tự";
    }

    const opening = Number(form.opening_balance);
    if (form.opening_balance === "" || Number.isNaN(opening) || opening < 0) {
      errs.opening_balance = "Số dư ban đầu phải lớn hơn hoặc bằng 0";
    }

    if (isCreditCard) {
      const limit = Number(form.credit_limit);
      if (!form.credit_limit || Number.isNaN(limit) || limit <= 0) {
        errs.credit_limit = "Hạn mức tín dụng phải lớn hơn 0";
      }

      const billing = Number(form.billing_day);
      if (
        !form.billing_day ||
        !Number.isInteger(billing) ||
        billing < 1 ||
        billing > 28
      ) {
        errs.billing_day = "Ngày sao kê phải từ 1 đến 28";
      }

      const due = Number(form.due_day);
      if (!form.due_day || !Number.isInteger(due) || due < 1 || due > 28) {
        errs.due_day = "Ngày đến hạn phải từ 1 đến 28";
      }
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e) {
    e.preventDefault();
    setServerError("");
    if (!validate()) return;

    const basePayload = {
      name: form.name.trim(),
      kind: form.kind,
      currency_code: form.currency_code,
      bank_name: form.bank_name.trim() || null,
      opening_balance: String(form.opening_balance).trim(),
    };

    const payload = isCreditCard
      ? {
          ...basePayload,
          allow_negative: true,
          credit_limit: String(form.credit_limit).trim(),
          billing_day: Number(form.billing_day),
          due_day: Number(form.due_day),
        }
      : {
          ...basePayload,
          allow_negative: false,
        };

    const handleError = (err) => {
      if (err.details && typeof err.details === "object") {
        setFieldErrors((prev) => ({ ...prev, ...err.details }));
      }
      setServerError(accountErrorMessage(err));
    };

    if (isEdit) {
      // Chỉ gửi những trường thực sự thay đổi khi PATCH
      const updatePayload = {};
      if (payload.name !== account.name) updatePayload.name = payload.name;
      if (payload.kind !== account.kind) updatePayload.kind = payload.kind;
      if (payload.currency_code !== account.currency_code) {
        updatePayload.currency_code = payload.currency_code;
      }
      if ((payload.bank_name ?? null) !== (account.bank_name ?? null)) {
        updatePayload.bank_name = payload.bank_name;
      }
      if (Number(payload.opening_balance) !== Number(account.opening_balance)) {
        updatePayload.opening_balance = payload.opening_balance;
      }
      if (isCreditCard) {
        if (Number(payload.credit_limit) !== Number(account.credit_limit)) {
          updatePayload.credit_limit = payload.credit_limit;
        }
        if (payload.billing_day !== account.billing_day) {
          updatePayload.billing_day = payload.billing_day;
        }
        if (payload.due_day !== account.due_day) {
          updatePayload.due_day = payload.due_day;
        }
      }

      if (Object.keys(updatePayload).length === 0) {
        onClose();
        return;
      }

      updateMutation.mutate(
        { accountId: account.id, data: updatePayload },
        { onSuccess: () => onClose(), onError: handleError }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => onClose(),
        onError: handleError,
      });
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="account-form-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="account-form-title" className="text-lg font-semibold text-gray-900">
            {isEdit ? "Chỉnh sửa ví / tài khoản" : "Thêm ví / tài khoản mới"}
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
          <Input
            label="Tên ví / tài khoản *"
            name="name"
            placeholder="Ví dụ: Tiền mặt, Vietcombank, Thẻ Visa..."
            value={form.name}
            onChange={onChange}
            error={fieldErrors.name}
          />

          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="kind" className="text-sm font-medium">
                Loại ví *
              </label>
              <select
                id="kind"
                name="kind"
                value={form.kind}
                onChange={onChange}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:-outline-offset-1 focus:outline-blue-600"
              >
                {ACCOUNT_KINDS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
              {fieldErrors.kind && (
                <small role="alert" className="text-sm text-red-600">
                  {fieldErrors.kind}
                </small>
              )}
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="currency_code" className="text-sm font-medium">
                Loại tiền tệ *
              </label>
              <select
                id="currency_code"
                name="currency_code"
                value={form.currency_code}
                onChange={onChange}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-2 focus:-outline-offset-1 focus:outline-blue-600"
              >
                {SUPPORTED_CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
              {fieldErrors.currency_code && (
                <small role="alert" className="text-sm text-red-600">
                  {fieldErrors.currency_code}
                </small>
              )}
            </div>
          </div>

          <Input
            label="Tên ngân hàng / tổ chức (tùy chọn)"
            name="bank_name"
            placeholder="Ví dụ: Vietcombank, MoMo, Techcombank..."
            value={form.bank_name}
            onChange={onChange}
            error={fieldErrors.bank_name}
          />

          <Input
            label="Số dư ban đầu *"
            name="opening_balance"
            type="number"
            min="0"
            step="any"
            value={form.opening_balance}
            onChange={onChange}
            error={fieldErrors.opening_balance}
          />

          {isEdit && (
            <p className="mb-4 rounded-lg bg-gray-50 p-2.5 text-xs text-gray-500">
              Lưu ý: Nếu ví đã phát sinh giao dịch hoặc chuyển khoản, hệ thống sẽ không
              cho phép thay đổi <strong>Loại ví</strong>, <strong>Tiền tệ</strong> và{" "}
              <strong>Số dư ban đầu</strong>.
            </p>
          )}

          {isCreditCard && (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50/50 p-4">
              <p className="mb-3 text-sm font-semibold text-rose-800">
                Thông tin thẻ tín dụng
              </p>

              <Input
                label="Hạn mức tín dụng *"
                name="credit_limit"
                type="number"
                min="1"
                step="any"
                placeholder="Ví dụ: 20000000"
                value={form.credit_limit}
                onChange={onChange}
                error={fieldErrors.credit_limit}
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Ngày sao kê (1 - 28) *"
                  name="billing_day"
                  type="number"
                  min="1"
                  max="28"
                  value={form.billing_day}
                  onChange={onChange}
                  error={fieldErrors.billing_day}
                />
                <Input
                  label="Ngày đến hạn (1 - 28) *"
                  name="due_day"
                  type="number"
                  min="1"
                  max="28"
                  value={form.due_day}
                  onChange={onChange}
                  error={fieldErrors.due_day}
                />
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
              Hủy
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEdit ? "Lưu thay đổi" : "Tạo ví"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
