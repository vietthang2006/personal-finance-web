export default function EmptyState({ text = "Chưa có dữ liệu", action }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-gray-300 bg-white p-6">
      <p className="text-gray-500">{text}</p>
      {action}
    </div>
  );
}