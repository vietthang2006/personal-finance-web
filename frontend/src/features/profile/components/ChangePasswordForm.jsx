import { useState } from "react";
import { Button, FormError, Input } from "@/shared/components";
import { passwordError } from "@/shared/lib/validators";
import { useChangePassword } from "../hooks";

const EMPTY = { old_password: "", new_password: "", confirm: "" };

export default function ChangePasswordForm() {
  const change = useChangePassword();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [done, setDone] = useState(false);

  const onChange = (e) => {
    setDone(false);
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  function handleSubmit(e) {
    e.preventDefault();
    setDone(false);
    setFormError("");

    const found = {};
    if (!form.old_password) found.old_password = "Vui lòng nhập mật khẩu hiện tại";
    const pe = passwordError(form.new_password);
    if (pe) found.new_password = pe;
    if (form.confirm !== form.new_password) found.confirm = "Mật khẩu xác nhận không khớp";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    change.mutate(
      { old_password: form.old_password, new_password: form.new_password },
      {
        onSuccess: () => {
          setDone(true);
          setForm(EMPTY);
        },
        onError: (err) => {
          // Backend: 400 chỉ xảy ra khi sai mật khẩu hiện tại (InvalidPasswordError)
          if (err.status === 400) setErrors({ old_password: "Mật khẩu hiện tại không đúng" });
          else if (err.details?.new_password) setErrors({ new_password: err.details.new_password });
          else setFormError(err.message);
        },
      }
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <h2 className="mb-4 text-lg font-semibold">Đổi mật khẩu</h2>
      <FormError message={formError} />
      {done && (
        <p className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">Đã đổi mật khẩu.</p>
      )}

      <Input label="Mật khẩu hiện tại" name="old_password" type="password" autoComplete="current-password"
        value={form.old_password} onChange={onChange} error={errors.old_password} />
      <Input label="Mật khẩu mới" name="new_password" type="password" autoComplete="new-password"
        value={form.new_password} onChange={onChange} error={errors.new_password} />
      <Input label="Nhập lại mật khẩu mới" name="confirm" type="password" autoComplete="new-password"
        value={form.confirm} onChange={onChange} error={errors.confirm} />

      <Button type="submit" loading={change.isPending}>Đổi mật khẩu</Button>
    </form>
  );
}