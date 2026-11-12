import { api, request } from "@/shared/api/client";
import { tokenStorage } from "@/shared/lib/tokenStorage";

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

// ==================== Transactions ====================

export function listTransactions(params = {}) {
  return api.get("/transactions", { params });
}

export const getTransaction = (id) => api.get(`/transactions/${id}`);

export const createTransaction = (data) => api.post("/transactions", data);

export const updateTransaction = (id, data) => api.patch(`/transactions/${id}`, data);

export const deleteTransaction = (id) => api.del(`/transactions/${id}`);

// ==================== Transaction Tags ====================

export const listTransactionTags = (transactionId) =>
  api.get(`/transactions/${transactionId}/tags`);

export const assignTransactionTags = (transactionId, tagIds) =>
  api.post(`/transactions/${transactionId}/tags`, { tag_ids: tagIds });

export const removeTransactionTag = (transactionId, tagId) =>
  api.del(`/transactions/${transactionId}/tags/${tagId}`);

// ==================== Transaction Attachments ====================

export const listAttachments = (transactionId) =>
  api.get(`/transactions/${transactionId}/attachments`);

export function uploadAttachment(transactionId, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(`/transactions/${transactionId}/attachments`, {
    method: "POST",
    body: formData,
  });
}

export const deleteAttachment = (transactionId, attachmentId) =>
  api.del(`/transactions/${transactionId}/attachments/${attachmentId}`);

export async function downloadAttachment(transactionId, attachmentId, fileName) {
  const tokens = tokenStorage.get();
  const headers = {};
  if (tokens?.access_token) {
    headers.Authorization = `Bearer ${tokens.access_token}`;
  }
  const res = await fetch(
    `${BASE}/transactions/${transactionId}/attachments/${attachmentId}/download`,
    { headers }
  );
  if (!res.ok) {
    throw new Error("Không thể tải tệp đính kèm");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || "attachment";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ==================== Categories & Subcategories ====================

export function listCategories({ kind, includeInactive = false } = {}) {
  return api.get("/categories", {
    params: {
      kind: kind || undefined,
      include_inactive: includeInactive ? true : undefined,
    },
  });
}

export const createCategory = (data) => api.post("/categories", data);

export const updateCategory = (categoryId, data) =>
  api.patch(`/categories/${categoryId}`, data);

export function listSubcategories(categoryId, { includeInactive = false } = {}) {
  return api.get(`/categories/${categoryId}/subcategories`, {
    params: { include_inactive: includeInactive ? true : undefined },
  });
}

export const createSubcategory = (categoryId, data) =>
  api.post(`/categories/${categoryId}/subcategories`, data);

export const updateSubcategory = (categoryId, subcategoryId, data) =>
  api.patch(`/categories/${categoryId}/subcategories/${subcategoryId}`, data);

// ==================== Tags ====================

export const listTags = () => api.get("/tags");

export const createTag = (data) => api.post("/tags", data);

export const updateTag = (tagId, data) => api.patch(`/tags/${tagId}`, data);

export const deleteTag = (tagId) => api.del(`/tags/${tagId}`);

// ==================== Transfers ====================

export function listTransfers(params = {}) {
  return api.get("/transfers", { params });
}

export const createTransfer = (data) => api.post("/transfers", data);
