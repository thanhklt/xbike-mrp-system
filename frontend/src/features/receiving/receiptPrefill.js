import { newLine } from "../../components/ResourceFields.jsx";

// UC-20 Lập, sửa, xóa phiếu nhập nháp — A1 mở từ yêu cầu chờ bổ sung (BR-009) (specs/use_cases/goods_receipt/UC-20.md)
export function prefillReceipt(request, items) {
  if (!request || request.da_du || !request.linh_kien_thieu?.length) return null;

  return {
    ghi_chu: `Bổ sung linh kiện cho ${request.ma_yeu_cau_san_xuat}`,
    lines: request.linh_kien_thieu.map(({ mat_hang_id, so_luong_thieu }) => {
      const item = items.find(({ id }) => id === mat_hang_id);
      return newLine({
        mat_hang_id: String(mat_hang_id),
        so_luong: String(so_luong_thieu),
        don_gia_thuc: String(item?.don_gia ?? 0),
      });
    }),
  };
}
