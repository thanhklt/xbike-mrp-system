export const issueTypeLabel = (type) => type === "xuat_linh_kien" ? "Phiếu xuất linh kiện" : "Phiếu xuất thành phẩm";

export function isReadyForFinishedIssue(request, completion) {
  return request?.loai_yeu_cau === "xuat_giao" && request.trang_thai === "dang_thuc_hien"
    && (request.so_luong_can_san_xuat === 0
      || (request.so_luong_can_san_xuat > 0 && completion?.trang_thai === "da_duyet"));
}

export function canCreateIssue(request, type, userId, completion) {
  if (!request || request.nhan_vien_duoc_giao_id !== userId) return false;
  if (type === "xuat_linh_kien") return ["dang_thuc_hien", "cho_bo_sung_linh_kien"].includes(request.trang_thai)
    && request.so_luong_can_san_xuat > 0;
  return type === "xuat_thanh_pham" && isReadyForFinishedIssue(request, completion);
}
