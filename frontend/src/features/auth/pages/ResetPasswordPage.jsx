import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button, ErrorState, FormError, Input } from "@/shared/components";
import { passwordError } from "@/shared/lib/validators";
import * as authApi from "../api";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const navigate = useNavigate();

  const [form, setForm] = useState({ password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [expired, setExpired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!token || expired) {
    return (
      <div>
        <ErrorState message="Liên kết không hợp lệ hoặc đã hết hạn." />
        <p className="mt-4 text-center text-sm">
          <Link to="/forgot-password" className="text-blue-600 hover:underline">
            Yêu cầu liên kết mới
          </Link>
        </p>
      </div>
    );
  }

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError("");

    const found = {};
    const pe = passwordError(form.password);
    if (pe) found.password = pe;
    if (form.confirm !== form.password) found.confirm = "Mật khẩu xác nhận không khớp";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await authApi.resetPassword(token, form.password);
      navigate("/login", { replace: true, state: { resetDone: true } });
    } catch (err) {
      if (err.status === 401) setExpired(true);   // token sai / hết hạn / đã dùng
      else setFormError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 className="mb-4 text-lg font-semibold">Đặt lại mật khẩu</h2>
      <FormError message={formError} />
      <Input label="Mật khẩu mới" name="password" type="password" autoComplete="new-password"
        value={form.password} onChange={onChange} error={errors.password} />
      <Input label="Nhập lại mật khẩu mới" name="confirm" type="password" autoComplete="new-password"
        value={form.confirm} onChange={onChange} error={errors.confirm} />
      <Button type="submit" block loading={submitting}>Đặt lại mật khẩu</Button>
    </form>
  );
}