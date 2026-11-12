import { useMemo, useState } from "react";
import { Button, FormError, Input } from "@/shared/components";
import { formatMoney } from "@/shared/lib/formatMoney";
import { todayISODate, TRANSACTION_KINDS } from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import {
  useCategories,
  useCreateTransaction,
  useSubcategories,
  useTags,
  useUpdateTransaction,
} from "../hooks";

function buildInitialForm(tx, accounts) {
  if (tx) {
    return {
      account_id: tx.account_id ?? "",
      kind: tx.kind ?? "expense",
      category_id: tx.category_id ? String(tx.category_id) : "",
      subcategory_id: tx.subcategory_id ? String(tx.subcategory_id) : "",
      amount: String(tx.amount ?? ""),
      transaction_date: tx.transaction_date ?? todayISODate(),
      merchant: tx.merchant ?? "",
      description: tx.description ?? "",
      tag_ids: [],
    };
  }
  const firstActive = accounts.find((a) => !a.is_archived);
  return {
    account_id: firstActive?.id ?? "",
    kind: "expense",
    category_id: "",
    subcategory_id: "",
    amount: "",
    transaction_date: todayISODate(),
    merchant: "",
    description: "",
    tag_ids: [],
  };
}

export default function TransactionFormModal({
  transaction = null,
  accounts = [],
  onClose,
}) {
  const isEdit = Boolean(transaction);
  const isLockedSource =
    isEdit && (transaction.source === "goal" || transaction.source === "loan");

  const [form, setForm] = useState(() => buildInitialForm(transaction, accounts));
  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState("");

  const { data: categories = [] } = useCategories({ kind: form.kind });
  const { data: subcategories = [] } = useSubcategories(
    form.category_id ? Number(form.category_id) : null
  );
  const { data: tags = [] } = useTags();

  const createMutation = useCreateTransaction();
  const updateMutation = useUpdateTransaction();
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  const activeAccounts = useMemo(
    () => accounts.filter((a) => !a.is_archived || a.id === form.account_id),
    [accounts, form.account_id]
  );

  function onChange(e) {
    const { name, value } = e.target;
    setFieldErrors((prev) => ({ ...prev, [name]: "" }));
    setServerError("");

    if (name === "kind") {
      setForm((prev) => ({
        ...prev,
        kind: value,
        category_id: "",
        subcategory_id: "",
      }));
      return;
    }
    if (name === "category_id") {
      setForm((prev) => ({
        ...prev,
        category_id: value,
        subcategory_id: "",
      }));
      return;
    }
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function toggleTag(tagId) {
    setForm((prev) => {
      const exists = prev.tag_ids.includes(tagId);
      if (exists) {
        return { ...prev, tag_ids: prev.tag_ids.filter((id) => id !== tagId) };
      }
      if (prev.tag_ids.length >= 10) return prev;
      return { ...prev, tag_ids: [...prev.tag_ids, tagId] };
    });
  }

  function validate() {
    const errs = {};
    if (!form.account_id) errs.account_id = "Vui lòng chọn ví";
    const amt = Number(form.amount);
    if (!form.amount || Number.isNaN(amt) || amt <= 0) {
      errs.amount = "Số tiền phải lớn hơn 0";
    }
    if (!form.transaction_date) {
      errs.transaction_date = "Vui lòng chọn ngày giao dịch";
    } else if (form.transaction_date > todayISODate()) {
      errs.transaction_date = "Ngày giao dịch không được ở tương lai";
    }
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e) {
    e.preventDefault();
    setServerError("");
    if (!validate()) return;

    const handleError = (err) => {
      if (err.details && typeof err.details === "object") {
        setFieldErrors((prev) => ({ ...prev, ...err.details }));
      }
      setServerError(transactionErrorMessage(err));
    };

    if (!isEdit) {
      const payload = {
        account_id: form.account_id,
        kind: form.kind,
        category_id: form.category_id ? Number(form.category_id) : null,
        subcategory_id: form.subcategory_id ? Number(form.subcategory_id) : null,
        amount: String(form.amount).trim(),
        transaction_date: form.transaction_date,
        merchant: form.merchant.trim() || null,
        description: form.description.trim() || null,
        tag_ids: form.tag_ids,
      };
      createMutation.mutate(payload, {
        onSuccess: () => onClose(),
        onError: handleError,
      });
      return;
    }

    const updatePayload = {};
    if (!isLockedSource) {
      if (form.account_id !== transaction.account_id) {
        updatePayload.account_id = form.account_id;
      }
      if (form.kind !== transaction.kind) {
        updatePayload.kind = form.kind;
      }
      if (Number(form.amount) !== Number(transaction.amount)) {
        updatePayload.amount = String(form.amount).trim();
      }
    }

    const nextCat = form.category_id ? Number(form.category_id) : null;
    if (nextCat !== (transaction.category_id ?? null)) {
      updatePayload.category_id = nextCat;
    }
    const nextSub = form.subcategory_id ? Number(form.subcategory_id) : null;
    if (nextSub !== (transaction.subcategory_id ?? null)) {
      updatePayload.subcategory_id = nextSub;
    }
    if (form.transaction_date !== transaction.transaction_date) {
      updatePayload.transaction_date = form.transaction_date;
    }
    const nextMerchant = form.merchant.trim() || null;
    if (nextMerchant !== (transaction.merchant ?? null)) {
      updatePayload.merchant = nextMerchant;
    }
    const nextDesc = form.description.trim() || null;
    if (nextDesc !== (transaction.description ?? null)) {
      updatePayload.description = nextDesc;
    }

    if (Object.keys(updatePayload).length === 0) {
      onClose();
      return;
    }

    updateMutation.mutate(
      { id: transaction.id, data: updatePayload },
      { onSuccess: () => onClose(), onError: handleError }
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tx-form-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="tx-form-title" className="text-lg font-semibold text-gray-900">
            {isEdit ? "Chỉnh sửa giao dịch" : "Thêm giao dịch mới"}
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

        {isLockedSource && (
          <p className="mb-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
            Giao dịch thuộc nguồn <strong>{transaction.source}</strong> nên chỉ được phép
            chỉnh sửa danh mục, ngày, nhà cung cấp hoặc mô tả.
          </p>
        )}

        <FormError message={serverError} />

        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="tx-kind" className="text-sm font-medium">
                Loại giao dịch *
              </label>
              <select
                id="tx-kind"
                name="kind"
                value={form.kind}
                onChange={onChange}
                disabled={isLockedSource}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100"
              >
                {TRANSACTION_KINDS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="tx-account" className="text-sm font-medium">
                Ví / Tài khoản *
              </label>
              <select
                id="tx-account"
                name="account_id"
                value={form.account_id}
                onChange={onChange}
                disabled={isLockedSource}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100"
              >
                <option value="">-- Chọn ví --</option>
                {activeAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({formatMoney(acc.current_balance, acc.currency_code)})
                  </option>
                ))}
              </select>
              {fieldErrors.account_id && (
                <small role="alert" className="text-sm text-red-600">
                  {fieldErrors.account_id}
                </small>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Số tiền *"
              name="amount"
              type="number"
              min="0.01"
              step="any"
              value={form.amount}
              onChange={onChange}
              disabled={isLockedSource}
              error={fieldErrors.amount}
            />
            <Input
              label="Ngày giao dịch *"
              name="transaction_date"
              type="date"
              max={todayISODate()}
              value={form.transaction_date}
              onChange={onChange}
              error={fieldErrors.transaction_date}
            />
          </div>

          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="tx-category" className="text-sm font-medium">
                Danh mục
              </label>
              <select
                id="tx-category"
                name="category_id"
                value={form.category_id}
                onChange={onChange}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">-- Không chọn --</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.icon ? `${cat.icon} ` : ""}
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="tx-subcategory" className="text-sm font-medium">
                Danh mục con
              </label>
              <select
                id="tx-subcategory"
                name="subcategory_id"
                value={form.subcategory_id}
                onChange={onChange}
                disabled={!form.category_id}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100"
              >
                <option value="">-- Không chọn --</option>
                {subcategories.map((sub) => (
                  <option key={sub.id} value={sub.id}>
                    {sub.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Input
            label="Đối tác / Cửa hàng (tùy chọn)"
            name="merchant"
            placeholder="Ví dụ: Grab, Highlands, Siêu thị..."
            value={form.merchant}
            onChange={onChange}
          />

          <div className="mb-4 flex flex-col gap-1">
            <label htmlFor="tx-desc" className="text-sm font-medium">
              Ghi chú (tùy chọn)
            </label>
            <textarea
              id="tx-desc"
              name="description"
              rows={2}
              value={form.description}
              onChange={onChange}
              placeholder="Nội dung chi tiết giao dịch..."
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
            />
          </div>

          {!isEdit && tags.length > 0 && (
            <div className="mb-4">
              <p className="mb-1.5 text-sm font-medium">
                Nhãn ({form.tag_ids.length}/10)
              </p>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag) => {
                  const active = form.tag_ids.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => toggleTag(tag.id)}
                      className={[
                        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                        active
                          ? "border-blue-600 bg-blue-50 text-blue-700"
                          : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
                      ].join(" ")}
                    >
                      <span
                        className="size-2.5 rounded-full"
                        style={{ backgroundColor: tag.color }}
                      />
                      {tag.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
              Hủy
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEdit ? "Lưu thay đổi" : "Tạo giao dịch"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
