import { useState } from "react";
import { Button, EmptyState, FormError, Spinner } from "@/shared/components";
import { formatDateTime } from "@/shared/lib/formatDate";
import { downloadAttachment } from "../api";
import {
  ALLOWED_ATTACHMENT_TYPES,
  MAX_ATTACHMENT_SIZE_BYTES,
  MAX_ATTACHMENTS_PER_TX,
} from "../constants";
import { transactionErrorMessage } from "../errorMessages";
import {
  useAssignTransactionTags,
  useAttachments,
  useDeleteAttachment,
  useRemoveTransactionTag,
  useTags,
  useTransactionTags,
  useUploadAttachment,
} from "../hooks";

export default function TransactionDetailModal({ transaction, onClose }) {
  const [error, setError] = useState("");
  const [selectedTagId, setSelectedTagId] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);

  const txId = transaction?.id;

  const { data: allTags = [] } = useTags();
  const {
    data: txTags = [],
    isLoading: loadingTags,
  } = useTransactionTags(txId, Boolean(txId));
  const {
    data: attachments = [],
    isLoading: loadingAttachments,
  } = useAttachments(txId, Boolean(txId));

  const assignTagsMutation = useAssignTransactionTags();
  const removeTagMutation = useRemoveTransactionTag();
  const uploadMutation = useUploadAttachment();
  const deleteAttachmentMutation = useDeleteAttachment();

  if (!transaction) return null;

  const availableTags = allTags.filter(
    (t) => !txTags.some((assigned) => assigned.id === t.id)
  );

  function handleAddTag() {
    if (!selectedTagId) return;
    setError("");
    assignTagsMutation.mutate(
      { transactionId: txId, tagIds: [Number(selectedTagId)] },
      {
        onSuccess: () => setSelectedTagId(""),
        onError: (err) => setError(transactionErrorMessage(err)),
      }
    );
  }

  function handleRemoveTag(tagId) {
    setError("");
    removeTagMutation.mutate(
      { transactionId: txId, tagId },
      { onError: (err) => setError(transactionErrorMessage(err)) }
    );
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");

    if (attachments.length >= MAX_ATTACHMENTS_PER_TX) {
      setError(`Mỗi giao dịch chỉ đính kèm tối đa ${MAX_ATTACHMENTS_PER_TX} tệp.`);
      return;
    }
    if (!ALLOWED_ATTACHMENT_TYPES.includes(file.type)) {
      setError("Chỉ hỗ trợ tệp JPG, PNG hoặc PDF.");
      return;
    }
    if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
      setError("Dung lượng tệp tối đa là 10MB.");
      return;
    }

    uploadMutation.mutate(
      { transactionId: txId, file },
      { onError: (err) => setError(transactionErrorMessage(err)) }
    );
  }

  async function handleDownload(att) {
    setError("");
    setDownloadingId(att.id);
    try {
      await downloadAttachment(txId, att.id, att.file_name);
    } catch (err) {
      setError(err.message || "Không thể tải tệp đính kèm.");
    } finally {
      setDownloadingId(null);
    }
  }

  function handleDeleteAttachment(attachmentId) {
    setError("");
    deleteAttachmentMutation.mutate(
      { transactionId: txId, attachmentId },
      { onError: (err) => setError(transactionErrorMessage(err)) }
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tx-detail-title"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 id="tx-detail-title" className="text-lg font-semibold text-gray-900">
              Nhãn & Hóa đơn đính kèm
            </h2>
            <p className="text-xs text-gray-500">
              {transaction.merchant || transaction.description || "Giao dịch"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-100"
            aria-label="Đóng"
          >
            ✕
          </button>
        </div>

        <FormError message={error} />

        {/* Phần Nhãn (Tags) */}
        <div className="mb-6 rounded-xl border border-gray-200 p-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-800">
            Nhãn đã gắn ({txTags.length}/10)
          </h3>

          {loadingTags ? (
            <Spinner label="Đang tải nhãn..." />
          ) : (
            <div className="mb-3 flex flex-wrap gap-2">
              {txTags.length === 0 ? (
                <p className="text-xs text-gray-400">Chưa gắn nhãn nào.</p>
              ) : (
                txTags.map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-700"
                  >
                    <span
                      className="size-2.5 rounded-full"
                      style={{ backgroundColor: tag.color }}
                    />
                    {tag.name}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag.id)}
                      className="ml-1 text-gray-400 hover:text-red-600"
                      aria-label={`Gỡ nhãn ${tag.name}`}
                    >
                      ×
                    </button>
                  </span>
                ))
              )}
            </div>
          )}

          {availableTags.length > 0 && txTags.length < 10 && (
            <div className="flex items-center gap-2">
              <select
                value={selectedTagId}
                onChange={(e) => setSelectedTagId(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
              >
                <option value="">-- Chọn nhãn để gắn --</option>
                {availableTags.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-xs"
                disabled={!selectedTagId}
                loading={assignTagsMutation.isPending}
                onClick={handleAddTag}
              >
                Gắn nhãn
              </Button>
            </div>
          )}
        </div>

        {/* Phần Đính kèm hóa đơn (Attachments) */}
        <div className="rounded-xl border border-gray-200 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-gray-800">
                Hóa đơn / Chứng từ ({attachments.length}/{MAX_ATTACHMENTS_PER_TX})
              </h3>
              <p className="text-xs text-gray-400">
                Hỗ trợ JPG, PNG, PDF — tối đa 10MB/tệp
              </p>
            </div>

            <label className="cursor-pointer rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700">
              {uploadMutation.isPending ? "Đang tải lên..." : "+ Tải hóa đơn lên"}
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                onChange={handleFileChange}
                disabled={
                  uploadMutation.isPending ||
                  attachments.length >= MAX_ATTACHMENTS_PER_TX
                }
                className="hidden"
              />
            </label>
          </div>

          {loadingAttachments && <Spinner label="Đang tải danh sách hóa đơn..." />}

          {!loadingAttachments && attachments.length === 0 && (
            <EmptyState text="Chưa có hóa đơn đính kèm nào." />
          )}

          {!loadingAttachments && attachments.length > 0 && (
            <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200">
              {attachments.map((att) => (
                <li
                  key={att.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-gray-900">
                      {att.file_name}
                    </p>
                    <p className="text-xs text-gray-400">
                      {(att.size_bytes / 1024).toFixed(1)} KB •{" "}
                      {formatDateTime(att.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      className="px-2.5 py-1 text-xs"
                      loading={downloadingId === att.id}
                      onClick={() => handleDownload(att)}
                    >
                      Tải xuống
                    </Button>
                    <Button
                      variant="danger"
                      className="px-2.5 py-1 text-xs"
                      loading={deleteAttachmentMutation.isPending}
                      onClick={() => handleDeleteAttachment(att.id)}
                    >
                      Xóa
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mt-5 flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Đóng
          </Button>
        </div>
      </div>
    </div>
  );
}
