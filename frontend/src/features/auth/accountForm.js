import { nullable } from "../../lib/format.js";

export const PASSWORD_MIN_LENGTH = 6;

// UC-04 Thêm tài khoản — Main 2–3, R1: cho phép cả ba vai trò (specs/use_cases/identity_access/UC-04.md)
export function creatableRoles(roles) {
  return roles;
}

// UC-04 Thêm tài khoản — Main 4; R6, R7: gửi hồ sơ và lý do, không gửi mã (specs/use_cases/identity_access/UC-04.md)
export function buildCreateAccountBody(values, profileFields) {
  const profile = Object.fromEntries(
    profileFields.map((name) => [name, nullable(String(values[name] ?? ""))]),
  );
  return {
    ...profile,
    ten_dang_nhap: values.ten_dang_nhap.trim(),
    mat_khau: values.mat_khau,
    vai_tro_id: Number(values.vai_tro_id),
    ly_do: nullable(String(values.ly_do ?? "")),
  };
}
