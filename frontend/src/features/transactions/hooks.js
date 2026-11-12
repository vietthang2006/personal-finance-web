import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

export const txKeys = {
  all: ["transactions"],
  list: (filters) => ["transactions", "list", filters],
  tags: (txId) => ["transactions", "tags", txId],
  attachments: (txId) => ["transactions", "attachments", txId],
  categories: (filters) => ["categories", filters],
  subcategories: (catId, includeInactive) => ["subcategories", catId, includeInactive],
  tagsAll: ["tags"],
  transfers: (filters) => ["transfers", "list", filters],
};

// ==================== Transactions ====================

export function useTransactions(filters = {}) {
  return useQuery({
    queryKey: txKeys.list(filters),
    queryFn: () => api.listTransactions(filters),
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTransaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.all });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => api.updateTransaction(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.all });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTransaction,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.all });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

// ==================== Transaction Tags ====================

export function useTransactionTags(transactionId, enabled = true) {
  return useQuery({
    queryKey: txKeys.tags(transactionId),
    queryFn: () => api.listTransactionTags(transactionId),
    enabled: Boolean(transactionId) && enabled,
  });
}

export function useAssignTransactionTags() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, tagIds }) =>
      api.assignTransactionTags(transactionId, tagIds),
    onSuccess: (_data, { transactionId }) => {
      qc.invalidateQueries({ queryKey: txKeys.tags(transactionId) });
    },
  });
}

export function useRemoveTransactionTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, tagId }) =>
      api.removeTransactionTag(transactionId, tagId),
    onSuccess: (_data, { transactionId }) => {
      qc.invalidateQueries({ queryKey: txKeys.tags(transactionId) });
    },
  });
}

// ==================== Attachments ====================

export function useAttachments(transactionId, enabled = true) {
  return useQuery({
    queryKey: txKeys.attachments(transactionId),
    queryFn: () => api.listAttachments(transactionId),
    enabled: Boolean(transactionId) && enabled,
  });
}

export function useUploadAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, file }) => api.uploadAttachment(transactionId, file),
    onSuccess: (_data, { transactionId }) => {
      qc.invalidateQueries({ queryKey: txKeys.attachments(transactionId) });
    },
  });
}

export function useDeleteAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, attachmentId }) =>
      api.deleteAttachment(transactionId, attachmentId),
    onSuccess: (_data, { transactionId }) => {
      qc.invalidateQueries({ queryKey: txKeys.attachments(transactionId) });
    },
  });
}

// ==================== Categories & Subcategories ====================

export function useCategories(filters = {}) {
  return useQuery({
    queryKey: txKeys.categories(filters),
    queryFn: () => api.listCategories(filters),
  });
}

export function useSubcategories(categoryId, includeInactive = false) {
  return useQuery({
    queryKey: txKeys.subcategories(categoryId, includeInactive),
    queryFn: () => api.listSubcategories(categoryId, { includeInactive }),
    enabled: Boolean(categoryId),
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createCategory,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] });
    },
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ categoryId, data }) => api.updateCategory(categoryId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] });
    },
  });
}

export function useCreateSubcategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ categoryId, data }) => api.createSubcategory(categoryId, data),
    onSuccess: (_data, { categoryId }) => {
      qc.invalidateQueries({ queryKey: ["subcategories", categoryId] });
    },
  });
}

export function useUpdateSubcategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ categoryId, subcategoryId, data }) =>
      api.updateSubcategory(categoryId, subcategoryId, data),
    onSuccess: (_data, { categoryId }) => {
      qc.invalidateQueries({ queryKey: ["subcategories", categoryId] });
    },
  });
}

// ==================== Tags ====================

export function useTags() {
  return useQuery({
    queryKey: txKeys.tagsAll,
    queryFn: api.listTags,
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTag,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.tagsAll });
    },
  });
}

export function useUpdateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, data }) => api.updateTag(tagId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.tagsAll });
    },
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteTag,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: txKeys.tagsAll });
    },
  });
}

// ==================== Transfers ====================

export function useTransfers(filters = {}) {
  return useQuery({
    queryKey: txKeys.transfers(filters),
    queryFn: () => api.listTransfers(filters),
  });
}

export function useCreateTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTransfer,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transfers"] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}
