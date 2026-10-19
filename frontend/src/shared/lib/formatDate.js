// Ngày thuần "2026-10-02": tự tách để không bị lệch ngày do múi giờ
function parseDateOnly(value) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

function toDate(value) {
  if (!value) return null;
  const d = typeof value === "string" ? parseDateOnly(value) ?? new Date(value) : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

// "2026-10-02"  ->  "02/10/2026"
export function formatDate(value) {
  const d = toDate(value);
  return d ? d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";
}

// "2026-10-02T08:30:00Z"  ->  "15:30 02/10/2026" (giờ máy người dùng)
export function formatDateTime(value) {
  const d = toDate(value);
  if (!d) return "—";
  const time = d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${time} ${formatDate(d)}`;
}

// Đưa ngày về dạng "2026-10-02" để gửi lên backend
export function toISODate(date) {
  const d = toDate(date);
  if (!d) return null;
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}