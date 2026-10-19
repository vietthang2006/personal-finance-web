import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, FormError, Input } from "@/shared/components";
import * as authApi from "../api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await authApi.forgotPassword(email.trim());
      setMessage(res?.message ?? "Nếu email hợp lệ, hướng dẫn đã được gửi.");
    } catch (err) {
      setError(err.code === "NETWORK_ERROR" ? "Không kết nối được máy chủ" : err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (message) {
    return (
      <div>
        <p className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>
        <Link to="/login" className="text-sm text-blue-600 hover:underline">
          Quay lại đăng nhập
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 className="mb-2 text-lg font-semibold">Quên mật khẩu</h2>
      <p className="mb-4 text-sm text-gray-600">
        Nhập email của bạn, chúng tôi sẽ gửi hướng dẫn đặt lại mật khẩu.
      </p>
      <FormError message={error} />
      <Input label="Email" type="email" autoComplete="email" value={email}
        onChange={(e) => setEmail(e.target.value)} required />
      <Button type="submit" block loading={submitting}>Gửi hướng dẫn</Button>
      <p className="mt-4 text-center text-sm">
        <Link to="/login" className="text-blue-600 hover:underline">Quay lại đăng nhập</Link>
      </p>
    </form>
  );
}