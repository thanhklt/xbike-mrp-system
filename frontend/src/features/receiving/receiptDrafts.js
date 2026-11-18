import { linePayload } from "../../components/ResourceFields.jsx";
import { ApiError } from "../../lib/api/contract.js";

// UC-20 R1–R2: Each receipt belongs to one supplier and cannot repeat an item.
export function receiptDraftsBySupplier(lines, fields) {
  const groups = new Map();
  for (const line of lines) {
    const supplierId = Number(line.ncc_id);
    if (!Number.isSafeInteger(supplierId) || supplierId <= 0) {
      throw new ApiError("Chọn nhà cung cấp cho từng linh kiện.", { status: 422 });
    }
    if (!groups.has(supplierId)) groups.set(supplierId, []);
    const group = groups.get(supplierId);
    if (group.some((entry) => Number(entry.mat_hang_id) === Number(line.mat_hang_id))) {
      throw new ApiError("Mỗi linh kiện chỉ được chọn một lần cho cùng nhà cung cấp.", {
        status: 422,
      });
    }
    group.push(line);
  }
  return Array.from(groups, ([ncc_id, group]) => ({
    ncc_id,
    ...fields,
    chi_tiet: linePayload(group, true),
  }));
}
