import { useState } from "react";
import { Button, EmptyState, ErrorState, FormError, Input, Spinner } from "@/shared/components";
import { transactionErrorMessage } from "../errorMessages";
import { useCreateTag, useDeleteTag, useTags, useUpdateTag } from "../hooks";

export default function TagsTab() {
  const [editing, setEditing] = useState(null);
  const [name, setName] = useState("");
  const [color, setColor] = useState("#2563eb");
  const [formError, setFormError] = useState("");
  const [actionError, setActionError] = useState("");

  const { data: tags = [], isLoading, isError, error, refetch } = useTags();
  const createMutation = useCreateTag();
  const updateMutation = useUpdateTag();
  const deleteMutation = useDeleteTag();

  function startEdit(tag) {
    setEditing(tag);
    setName(tag.name);
    setColor(tag.color || "#2563eb");
    setFormError("");
  }

  function resetForm() {
    setEditing(null);
    setName("");
    setColor("#2563eb");
    setFormError("");
  }

  function handleSubmit(e) {
    e.preventDefault();
    setFormError("");
    const trimmed = name.trim();
    if (!trimmed) {
      setFormError("Vui lòng nhập tên nhãn");
      return;
    }
    if (!/^#[0-9A-Fa-f]{6}$/.test(color)) {
      setFormError("Mã màu phải theo định dạng #RRGGBB");
      return;
    }

    if (editing) {
      updateMutation.mutate(
        { tagId: editing.id, data: { name: trimmed, color } },
        {
          onSuccess: () => resetForm(),
          onError: (err) => setFormError(transactionErrorMessage(err)),
        }
      );
    } else {
      createMutation.mutate(
        { name: trimmed, color },
        {
          onSuccess: () => resetForm(),
          onError: (err) => setFormError(transactionErrorMessage(err)),
        }
      );
    }
  }

  function handleDelete(tagId) {
    setActionError("");
    deleteMutation.mutate(tagId, {
      onError: (err) => setActionError(transactionErrorMessage(err)),
    });
  }

  return (
    <div className="space-y-5">
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
      >
        <h3 className="mb-3 text-sm font-semibold text-gray-800">
          {editing ? `Sửa nhãn: ${editing.name}` : "Tạo nhãn cá nhân mới"}
        </h3>
        <FormError message={formError} />

        <div className="flex flex-wrap items-end gap-4">
          <div className="min-w-[200px] flex-1">
            <Input
              label="Tên nhãn *"
              placeholder="Ví dụ: Công tác, Gia đình, Khẩn cấp..."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="mb-4 flex flex-col gap-1">
            <label htmlFor="tag-color" className="text-sm font-medium">
              Màu sắc
            </label>
            <div className="flex items-center gap-2">
              <input
                id="tag-color"
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="h-10 w-12 cursor-pointer rounded border border-gray-300 bg-white p-1"
              />
              <span className="font-mono text-xs text-gray-600">{color}</span>
            </div>
          </div>

          <div className="mb-4 flex gap-2">
            {editing && (
              <Button variant="secondary" onClick={resetForm}>
                Hủy
              </Button>
            )}
            <Button
              type="submit"
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {editing ? "Lưu nhãn" : "+ Thêm nhãn"}
            </Button>
          </div>
        </div>
      </form>

      <FormError message={actionError} />

      {isLoading && <Spinner label="Đang tải danh sách nhãn..." />}
      {isError && (
        <ErrorState message={transactionErrorMessage(error)} onRetry={() => refetch()} />
      )}
      {!isLoading && !isError && tags.length === 0 && (
        <EmptyState text="Bạn chưa tạo nhãn nào." />
      )}
      {!isLoading && !isError && tags.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tags.map((tag) => (
            <div
              key={tag.id}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-center gap-2.5">
                <span
                  className="size-4 rounded-full border border-black/10"
                  style={{ backgroundColor: tag.color }}
                />
                <div>
                  <p className="font-medium text-gray-900">{tag.name}</p>
                  <p className="font-mono text-xs text-gray-400">{tag.color}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="secondary"
                  className="px-2.5 py-1 text-xs"
                  onClick={() => startEdit(tag)}
                >
                  Sửa
                </Button>
                <Button
                  variant="danger"
                  className="px-2.5 py-1 text-xs"
                  loading={deleteMutation.isPending}
                  onClick={() => handleDelete(tag.id)}
                >
                  Xóa
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
