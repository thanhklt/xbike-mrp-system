// UC-05 Khóa tài khoản — R3, R7, A3: mọi tài khoản đều có thao tác khóa/mở khóa; BE chặn QTV cuối (specs/use_cases/identity_access/UC-05.md)
export function canChangeAccountState(record) {
  return ["hoat_dong", "bi_khoa"].includes(record?.trang_thai);
}

// UC-05 Khóa tài khoản — R1, A1: lý do tùy chọn, trống gửi null (specs/use_cases/identity_access/UC-05.md)
// UC-06 Mở khóa tài khoản — R1, A1: chuẩn hóa lý do mở khóa, trống gửi null (specs/use_cases/identity_access/UC-06.md)
export function lockRequestBody(reason) {
  return { ly_do: reason?.trim() || null };
}

// UC-05 Khóa tài khoản — Main 2–3: tùy chọn hộp xác nhận khóa (specs/use_cases/identity_access/UC-05.md)
// UC-06 Mở khóa tài khoản — Main 2–3; A1: hộp mở khóa cho phép bỏ trống lý do (specs/use_cases/identity_access/UC-06.md)
export function stateConfirmOptions(record) {
  const unlock = record.trang_thai === "bi_khoa";
  return {
    title: unlock ? "Mở khóa tài khoản" : "Khóa tài khoản",
    reasonOptional: true,
    danger: !unlock,
    method: unlock ? "post" : "delete",
    pathSuffix: unlock ? "/mo_khoa" : "",
  };
}
