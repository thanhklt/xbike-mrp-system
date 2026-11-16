export const issueTypeLabel = (type) => type === "xuat_linh_kien" ? "Phiếu xuất linh kiện" : "Phiếu xuất thành phẩm";

export function canCreateIssue(request, type, userId, completion) {
  if (!request || request.nhan_vien_duoc_giao_id !== userId || request.trang_thai !== "dang_thuc_hien") return false;
  if (type === "xuat_linh_kien") return request.so_luong_can_san_xuat > 0;
  return type === "xuat_thanh_pham" && request.loai_yeu_cau === "xuat_giao"
    && (request.so_luong_can_san_xuat === 0 || (request.so_luong_can_san_xuat > 0 && completion?.trang_thai === "da_duyet"));
}
