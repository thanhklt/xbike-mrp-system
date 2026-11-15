export const ACCOUNT_SORT_OPTIONS = [
  { value: "ma_nhan_vien", label: "Mã NV tăng dần" },
  { value: "-ma_nhan_vien", label: "Mã NV giảm dần" },
  { value: "ho_ten", label: "Họ tên tăng dần" },
  { value: "-ho_ten", label: "Họ tên giảm dần" },
];
export const DEFAULT_ACCOUNT_SORT = "ma_nhan_vien";
export const ACCOUNT_SEARCH_LABEL = "Tìm theo mã NV hoặc họ tên";

// UC-03 Xem danh sách tài khoản — Main 2: mã nhân viên và tên đăng nhập (specs/use_cases/identity_access/UC-03.md)
export function accountMetaLine(row) {
  return `${row.ma_nhan_vien} · ${row.ten_dang_nhap}`;
}
