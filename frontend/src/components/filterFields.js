// Cấu hình bộ lọc dùng chung, tách khỏi ResourceFields.jsx (chứa JSX) để module thuần JS
// và `node --test` import trực tiếp được.
export const dateFilters = [
  { name: "tu_ngay", label: "Từ ngày", type: "date" },
  { name: "den_ngay", label: "Đến ngày", type: "date" },
];

// Trả về thông báo lỗi khi "Từ ngày" sau "Đến ngày"; null khi hợp lệ hoặc thiếu một đầu.
export function dateRangeError({ tu_ngay, den_ngay } = {}) {
  if (tu_ngay && den_ngay && tu_ngay > den_ngay) {
    return "Từ ngày không được sau Đến ngày.";
  }
  return null;
}
