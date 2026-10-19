const variants = {
  primary: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "bg-white text-gray-900 border-gray-300 hover:bg-gray-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
};

export default function Button({
  variant = "primary",   // "primary" | "secondary" | "danger"
  loading = false,
  block = false,         // true: rộng hết chiều ngang
  type = "button",
  disabled,
  className = "",
  children,
  ...props
}) {
  const cls = [
    "inline-flex items-center justify-center rounded-lg border border-transparent",
    "px-4 py-2 font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-60",
    variants[variant],
    block && "w-full",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={cls}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? "Đang xử lý..." : children}
    </button>
  );
}