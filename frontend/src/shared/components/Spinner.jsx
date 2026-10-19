export default function Spinner({ label = "Đang tải..." }) {
  return (
    <div
      className="flex items-center justify-center gap-2 p-6 text-gray-500"
      role="status"
      aria-live="polite"
    >
      <span
        className="size-5 animate-spin rounded-full border-[3px] border-gray-300 border-t-blue-600"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}