import { nullable, UNIT_OPTIONS, unitLabel } from "../../lib/format.js";

export function itemUnitOptions(currentUnit) {
  return !currentUnit || UNIT_OPTIONS.some((option) => option.value === currentUnit)
    ? UNIT_OPTIONS
    : [
        ...UNIT_OPTIONS.filter((option) => option.label !== unitLabel(currentUnit)),
        { value: currentUnit, label: unitLabel(currentUnit) },
      ];
}

// UC-10/11/16 — adapt the form to MatHangCreate/MatHangPatch v4; codes are DB-generated.
export function itemPayload(values, { record, lines = [] } = {}) {
  const body = {
    sku: values.sku.trim(),
    ten_mat_hang: values.ten_mat_hang.trim(),
    don_vi_tinh: values.don_vi_tinh.trim(),
    mau_sac: nullable(values.mau_sac),
    mo_ta: nullable(values.mo_ta),
    don_gia: Number(values.don_gia),
  };
  if (!record) {
    body.loai_mat_hang = values.loai_mat_hang;
    if (values.loai_mat_hang === "thanh_pham") {
      body.bom = {
        chi_tiet: lines.map(({ mat_hang_id, so_luong }) => ({
          mat_hang_id: Number(mat_hang_id),
          so_luong: Number(so_luong),
        })),
      };
    }
  }
  if (record)
    return Object.fromEntries(
      Object.entries(body).filter(([key, value]) => value !== (record[key] ?? null)),
    );
  return body;
}
