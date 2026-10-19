import Button from "./Button";

export default function ErrorState({ message = "Có lỗi xảy ra", onRetry }) {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-lg border border-red-600 bg-red-50 p-6"
      role="alert"
    >
      <p className="text-red-600">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Thử lại
        </Button>
      )}
    </div>
  );
}