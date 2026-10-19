import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Button, FormError, Input } from "@/shared/components";
import { useAuth } from "../authContext";
import { loginErrorMessage } from "../errorMessages";

export default function LoginPage() {
  const { login } = useAuth();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ email: form.email.trim(), password: form.password });
      // Thành công: GuestRoute tự chuyển sang trang cần vào
    } catch (err) {
      setError(loginErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 className="mb-4 text-lg font-semibold">Đăng nhập</h2>

      {location.state?.resetDone && (
        <p className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
          Đã đặt lại mật khẩu. Hãy đăng nhập bằng mật khẩu mới.
        </p>
      )}
      <FormError message={error} />

      <Input label="Email" name="email" type="email" autoComplete="email"
        value={form.email} onChange={onChange} required />
      <Input label="Mật khẩu" name="password" type="password" maxLength={72}
        autoComplete="current-password" value={form.password} onChange={onChange} required />

      <div className="-mt-2 mb-4 text-right text-sm">
        <Link to="/forgot-password" className="text-blue-600 hover:underline">
          Quên mật khẩu?
        </Link>
      </div>

      <Button type="submit" block loading={submitting}>
        Đăng nhập
      </Button>

      <p className="mt-4 text-center text-sm text-gray-600">
        Chưa có tài khoản?{" "}
        <Link to="/register" className="text-blue-600 hover:underline">
          Đăng ký
        </Link>
      </p>
    </form>
  );
}