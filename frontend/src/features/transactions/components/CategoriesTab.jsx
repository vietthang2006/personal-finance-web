import { useState } from "react";
import { Button, EmptyState, ErrorState, FormError, Input, Spinner } from "@/shared/components";
import { TRANSACTION_KIND_MAP, TRANSACTION_KINDS } from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import {
  useCategories,
  useCreateCategory,
  useCreateSubcategory,
  useSubcategories,
  useUpdateCategory,
} from "../hooks";

function CategoryRow({ category, onEdit }) {
  const [expanded, setExpanded] = useState(false);
  const [subName, setSubName] = useState("");
  const [subError, setSubError] = useState("");

  const { data: subcategories = [], isLoading } = useSubcategories(
    expanded ? category.id : null,
    true
  );
  const createSubMutation = useCreateSubcategory();
  const updateCatMutation = useUpdateCategory();

  const isSystem = category.user_id === null;
  const kindInfo = TRANSACTION_KIND_MAP[category.kind] ?? {
    label: category.kind,
    badgeClass: "bg-gray-100 text-gray-700 border-gray-200",
  };

  function handleAddSub(e) {
    e.preventDefault();
    const name = subName.trim();
    if (!name) return;
    setSubError("");
    createSubMutation.mutate(
      { categoryId: category.id, data: { name } },
      {
        onSuccess: () => setSubName(""),
        onError: (err) => setSubError(transactionErrorMessage(err)),
      }
    );
  }

  function handleToggleActive() {
    updateCatMutation.mutate({
      categoryId: category.id,
      data: { is_active: !category.is_active },
    });
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {category.icon && <span className="text-lg">{category.icon}</span>}
          <span className="font-semibold text-gray-900">{category.name}</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-xs font-medium ${kindInfo.badgeClass}`}
          >
            {kindInfo.label}
          </span>
          {isSystem ? (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              Hệ thống
            </span>
          ) : (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
              Cá nhân
            </span>
          )}
          {!category.is_active && (
            <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-600">
              Đã ẩn
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            className="px-3 py-1 text-xs"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? "Thu gọn" : "Danh mục con"}
          </Button>
          {!isSystem && (
            <>
              <Button
                variant="secondary"
                className="px-3 py-1 text-xs"
                onClick={() => onEdit(category)}
              >
                Sửa
              </Button>
              <Button
                variant="secondary"
                className="px-3 py-1 text-xs"
                loading={updateCatMutation.isPending}
                onClick={handleToggleActive}
              >
                {category.is_active ? "Ẩn" : "Hiện"}
              </Button>
            </>
          )}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          {isLoading ? (
            <Spinner label="Đang tải danh mục con..." />
          ) : (
            <div className="space-y-3">
              {subcategories.length === 0 ? (
                <p className="text-xs text-gray-400">Chưa có danh mục con nào.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {subcategories.map((sub) => (
                    <span
                      key={sub.id}
                      className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-700"
                    >
                      {sub.name}
                      {!sub.is_active && " (ẩn)"}
                    </span>
                  ))}
                </div>
              )}

              <FormError message={subError} />

              {isSystem ? (
                <p className="text-xs text-gray-500">
                  Danh mục hệ thống chỉ xem, không thể thêm danh mục con. Bạn có thể tạo
                  danh mục cá nhân ở trên để thêm danh mục con riêng.
                </p>
              ) : (
                <form onSubmit={handleAddSub} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={subName}
                    onChange={(e) => setSubName(e.target.value)}
                    placeholder="Tên danh mục con mới..."
                    className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
                  />
                  <Button
                    type="submit"
                    variant="secondary"
                    className="px-3 py-1.5 text-xs"
                    loading={createSubMutation.isPending}
                    disabled={!subName.trim()}
                  >
                    + Thêm mục con
                  </Button>
                </form>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CategoriesTab() {
  const [kindFilter, setKindFilter] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  const [editing, setEditing] = useState(null);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("expense");
  const [icon, setIcon] = useState("");
  const [formError, setFormError] = useState("");

  const {
    data: categories = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useCategories({
    kind: kindFilter || undefined,
    includeInactive,
  });

  const createMutation = useCreateCategory();
  const updateMutation = useUpdateCategory();

  function startEdit(cat) {
    setEditing(cat);
    setName(cat.name);
    setKind(cat.kind);
    setIcon(cat.icon ?? "");
    setFormError("");
  }

  function resetForm() {
    setEditing(null);
    setName("");
    setKind("expense");
    setIcon("");
    setFormError("");
  }

  function handleSubmit(e) {
    e.preventDefault();
    setFormError("");
    const trimmed = name.trim();
    if (!trimmed) {
      setFormError("Vui lòng nhập tên danh mục");
      return;
    }

    if (editing) {
      updateMutation.mutate(
        {
          categoryId: editing.id,
          data: { name: trimmed, icon: icon.trim() || null },
        },
        {
          onSuccess: () => resetForm(),
          onError: (err) => setFormError(transactionErrorMessage(err)),
        }
      );
    } else {
      createMutation.mutate(
        { name: trimmed, kind, icon: icon.trim() || null },
        {
          onSuccess: () => resetForm(),
          onError: (err) => setFormError(transactionErrorMessage(err)),
        }
      );
    }
  }

  return (
    <div className="space-y-5">
      {/* Form tạo / sửa danh mục */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
      >
        <h3 className="mb-3 text-sm font-semibold text-gray-800">
          {editing ? `Sửa danh mục: ${editing.name}` : "Tạo danh mục cá nhân mới"}
        </h3>
        <FormError message={formError} />
        <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-4">
          <div className="sm:col-span-2">
            <Input
              label="Tên danh mục *"
              placeholder="Ví dụ: Cafe, Thú cưng, Thưởng..."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="mb-4 flex flex-col gap-1">
            <label htmlFor="cat-kind" className="text-sm font-medium">
              Loại
            </label>
            <select
              id="cat-kind"
              value={kind}
              disabled={Boolean(editing)}
              onChange={(e) => setKind(e.target.value)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100"
            >
              {TRANSACTION_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Input
              label="Biểu tượng (emoji)"
              placeholder="☕"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          {editing && (
            <Button variant="secondary" onClick={resetForm}>
              Hủy sửa
            </Button>
          )}
          <Button
            type="submit"
            loading={createMutation.isPending || updateMutation.isPending}
          >
            {editing ? "Lưu thay đổi" : "+ Thêm danh mục"}
          </Button>
        </div>
      </form>

      {/* Bộ lọc */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[
            { value: "", label: "Tất cả" },
            { value: "expense", label: "Chi tiêu" },
            { value: "income", label: "Thu nhập" },
          ].map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setKindFilter(item.value)}
              className={[
                "rounded-lg px-3 py-1.5 text-xs font-medium",
                kindFilter === item.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200",
              ].join(" ")}
            >
              {item.label}
            </button>
          ))}
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="size-4 rounded border-gray-300 text-blue-600"
          />
          <span>Hiện danh mục đã ẩn</span>
        </label>
      </div>

      {isLoading && <Spinner label="Đang tải danh mục..." />}
      {isError && (
        <ErrorState message={transactionErrorMessage(error)} onRetry={() => refetch()} />
      )}
      {!isLoading && !isError && categories.length === 0 && (
        <EmptyState text="Không có danh mục nào." />
      )}
      {!isLoading && !isError && categories.length > 0 && (
        <div className="space-y-3">
          {categories.map((cat) => (
            <CategoryRow key={cat.id} category={cat} onEdit={startEdit} />
          ))}
        </div>
      )}
    </div>
  );
}
