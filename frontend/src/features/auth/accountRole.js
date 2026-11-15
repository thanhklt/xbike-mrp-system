import { ROLE_LABELS } from "../../lib/format.js";

// UC-07 Đổi vai trò — Main 2; R1, R7: đủ ba vai trò, chỉ khóa option hiện tại (specs/use_cases/identity_access/UC-07.md)
export function roleOptions(roles, currentRoleId) {
  return roles.map((role) => {
    const disabled = Number(role.id) === Number(currentRoleId);
    const name = ROLE_LABELS[role.ma_vai_tro] || role.ten_vai_tro;
    return { id: role.id, label: `${name}${disabled ? " (hiện tại)" : ""}`, disabled };
  });
}

// UC-07 Đổi vai trò — Main 3; R2: chuẩn hóa vai trò và lý do tùy chọn (specs/use_cases/identity_access/UC-07.md)
export function roleChangeBody(roleId, reason) {
  return { vai_tro_id: Number(roleId), ly_do: reason?.trim() || null };
}

// UC-07 Đổi vai trò — Main 5; A5: tự đổi vai trò kết thúc phiên của chính mình (specs/use_cases/identity_access/UC-07.md)
export function endsOwnSession(targetId, currentUserId) {
  return Number(targetId) === Number(currentUserId);
}
