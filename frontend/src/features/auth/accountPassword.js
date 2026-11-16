import { PASSWORD_MIN_LENGTH } from "./accountForm.js";

// UC-08 Đổi mật khẩu tài khoản — Main 4; A1: kiểm tra tối thiểu 6 ký tự (specs/use_cases/identity_access/UC-08.md)
export function passwordTooShort(value) {
  return value.length < PASSWORD_MIN_LENGTH;
}

// UC-08 Đổi mật khẩu tài khoản — Main 2–3; R5: chỉ gửi mật khẩu mới (specs/use_cases/identity_access/UC-08.md)
export function passwordResetBody(value) {
  return { mat_khau_moi: value };
}

// UC-08 Đổi mật khẩu tài khoản — Main 5; A2: tự đổi phải kết thúc phiên hiện tại (specs/use_cases/identity_access/UC-08.md)
export function endsOwnSessionAfterPasswordReset(targetId, currentUserId) {
  return Number(targetId) === Number(currentUserId);
}
