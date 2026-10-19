import { useState } from "react";
import { Button, FormError, Input } from "@/shared/components";
import { useAuth } from "@/features/auth";
import { useUpdateProfile } from "../hooks";

// Danh sách tiền tệ hợp lệ khớp với database backend
const SUPPORTED_CURRENCIES = [
  { code: "VND", symbol: "₫", label: "VND - Vietnamese Dong (₫)" },
  { code: "USD", symbol: "$", label: "USD - US Dollar ($)" },
  { code: "EUR", symbol: "€", label: "EUR - Euro (€)" },
  { code: "GBP", symbol: "£", label: "GBP - British Pound (£)" },
];

export default function ProfileForm() {
  const { user } = useAuth();
  const update = useUpdateProfile();
  const [form, setForm] = useState({
    full_name: user.full_name ?? "",
    default_currency: user.default_currency ?? "VND",
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [currencyError, setCurrencyError] = useState("");

  const onChange = (e) => {
    setSaved(false);
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  function handleSubmit(e) {
    e.preventDefault();
    setSaved(false);
    setError("");
    setCurrencyError("");

    // Không cần regex kiểm tra độ dài nữa vì người dùng chỉ chọn từ danh sách cố định

    update.mutate(
      {
        full_name: form.full_name.trim() || undefined,
        default_currency: form.default_currency,
      },
      {
        onSuccess: () => setSaved(true),
        onError: (err) => {
          if (err.details?.default_currency) {
            setCurrencyError(err.details.default_currency);
          } else if (err.status === 422) {
            setCurrencyError("Mã tiền tệ này chưa được hỗ trợ");
          } else {
            setError(err.message);
          }
        },
      }
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 className="mb-4 text-lg font-semibold">Thông tin cá nhân</h2>
      
      <FormError message={error} />
      
      {saved && (
        <p className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
          Đã lưu thay đổi.
        </p>
      )}

      <Input label="Email" value={user.email} disabled readOnly />
      <Input label="Tên đăng nhập" value={user.username} disabled readOnly />
      <Input label="Họ tên" name="full_name" value={form.full_name} onChange={onChange} />

      <div className="mb-4">
        <label htmlFor="default_currency" className="mb-1 block text-sm font-medium text-gray-700">
          Tiền tệ mặc định
        </label>
        <select
          id="default_currency"
          name="default_currency"
          value={form.default_currency}
          onChange={onChange}
          className="w-full rounded-lg border border-gray-300 p-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {SUPPORTED_CURRENCIES.map((currency) => (
            <option key={currency.code} value={currency.code}>
              {currency.label}
            </option>
          ))}
        </select>
        {currencyError && (
          <p className="mt-1 text-xs text-red-500">{currencyError}</p>
        )}
      </div>

      <Button type="submit" loading={update.isPending}>
        Lưu thay đổi
      </Button>
    </form>
  );
}