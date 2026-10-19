import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, FormError, Input } from "@/shared/components";
import { EMAIL_RE, USERNAME_RE, passwordError } from "@/shared/lib/validators";
import { useAuth } from "../authContext";
import { registerErrorMessage } from "../errorMessages";

function validate(f) {
  const errors = {};
  if (f.full_name.trim().length > 150) errors.full_name = "Họ tên tối đa 150 ký tự";
  if (!USERNAME_RE.test(f.username.trim()))
    errors.username = "3–50 ký tự: chữ, số, dấu gạch dưới, chấm hoặc gạch ngang";
  if (!EMAIL_RE.test(f.email.trim())) errors.email = "Email không hợp lệ";
  const pe = passwordError(f.password);
  if (pe) errors.password = pe;
  if (f.confirm !== f.password) errors.confirm = "Mật khẩu xác nhận không khớp";
  return errors;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    full_name: "",
    username: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError("");

    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await register({
        email: form.email.trim(),
        username: form.username.trim(),
        password: form.password,
        full_name: form.full_name.trim() || undefined,
      });
      // Thành công: đã đăng nhập, GuestRoute tự chuyển sang trang chính
    } catch (err) {
      // 422 của Pydantic: gắn lỗi vào đúng ô (khóa là tên trường backend)
      const fieldErrors = err.details
        ? Object.fromEntries(Object.entries(err.details).filter(([k]) => k in form))
        : {};
      if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors);
      else setFormError(registerErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 className="mb-4 text-lg font-semibold">Đăng ký</h2>
      <FormError message={formError} />

      <Input label="Họ tên (không bắt buộc)" name="full_name" autoComplete="name"
        value={form.full_name} onChange={onChange} error={errors.full_name} />
      <Input label="Tên đăng nhập" name="username" autoComplete="username"
        value={form.username} onChange={onChange} error={errors.username} />
      <Input label="Email" name="email" type="email" autoComplete="email"
        value={form.email} onChange={onChange} error={errors.email} />
      <Input label="Mật khẩu" name="password" type="password" autoComplete="new-password"
        value={form.password} onChange={onChange} error={errors.password} />
      <Input label="Nhập lại mật khẩu" name="confirm" type="password" autoComplete="new-password"
        value={form.confirm} onChange={onChange} error={errors.confirm} />

      <Button type="submit" block loading={submitting}>
        Tạo tài khoản
      </Button>

      <p className="mt-4 text-center text-sm text-gray-600">
        Đã có tài khoản?{" "}
        <Link to="/login" className="text-blue-600 hover:underline">
          Đăng nhập
        </Link>
      </p>
    </form>
  );
}