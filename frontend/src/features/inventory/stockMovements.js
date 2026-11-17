// UC-42 Tra cứu lịch sử biến động kho — Main 3; R1 (specs/use_cases/reporting/UC-42.md)
export const MOVEMENT_TYPES = [
  { value: "nhap_linh_kien", label: "Nhập kho" },
  { value: "xuat_linh_kien", label: "Xuất linh kiện" },
  { value: "nhap_san_pham_san_xuat", label: "Nhập thành phẩm sản xuất" },
  { value: "xuat_thanh_pham", label: "Xuất thành phẩm" },
];

// UC-42 Tra cứu lịch sử biến động kho — Main 2; R2 (specs/use_cases/reporting/UC-42.md)
export const SOURCE_LABELS = {
  phieu_nhap: "Phiếu nhập",
  phieu_xuat: "Phiếu xuất",
  chung_tu_hoan_thanh_sx: "Chứng từ hoàn thành SX",
};

// UC-42 Tra cứu lịch sử biến động kho — Main 3–4; R1, R3 (specs/use_cases/reporting/UC-42.md)
export function movementParams(params) {
  const query = {};
  for (const key of ["page", "page_size", "mat_hang_id", "nhan_vien_id"]) {
    if (params[key] !== "" && params[key] !== null && params[key] !== undefined)
      query[key] = Number(params[key]);
  }
  for (const key of ["loai_giao_dich", "tu_ngay", "den_ngay"]) {
    if (params[key] !== "" && params[key] !== null && params[key] !== undefined)
      query[key] = params[key];
  }
  return query;
}

// UC-42 Tra cứu lịch sử biến động kho — Main 2 (specs/use_cases/reporting/UC-42.md)
export function signedQuantity(n) {
  return n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : "0";
}
