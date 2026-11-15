import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { endsOwnSession, roleChangeBody, roleOptions } from "../src/features/auth/accountRole.js";
import {
  endsOwnSessionAfterPasswordReset,
  passwordResetBody,
  passwordTooShort,
} from "../src/features/auth/accountPassword.js";
import { PASSWORD_MIN_LENGTH } from "../src/features/auth/accountForm.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

const users = readFileSync(new URL("../src/features/auth/UsersPage.jsx", import.meta.url), "utf8");
const roles = [
  { id: 1, ma_vai_tro: "quan_tri_vien", ten_vai_tro: "Quản trị viên" },
  { id: 2, ma_vai_tro: "quan_ly", ten_vai_tro: "Quản lý kho" },
  { id: 3, ma_vai_tro: "nhan_vien", ten_vai_tro: "Nhân viên" },
];

function editAction({ own = false, writeError, reason = "  Phân công mới  " } = {}) {
  const record = { id: own ? 1 : 4, vai_tro_id: own ? 1 : 2, ma_vai_tro: own ? "quan_tri_vien" : "quan_ly" };
  const writes = [], logouts = [], errors = [], successes = [], cacheUpdates = [];
  let confirmation;
  const start = users.indexOf("  function handleInlineSubmit(");
  const end = users.indexOf("\n  const roleChoices", start);
  const environment = {
    editBaselineRef: { current: { data: record, etag: '"reviewed"' } }, snapshot: null,
    busy: false, isProfileChanged: () => false, values: {}, newPassword: "new-password",
    roleId: "3", roleReason: reason, ApiError: Error, setSaveError: (error) => errors.push(error),
    editInitializedRef: { current: true }, onCancelEdit: () => {},
    confirm: (options) => { confirmation = options; }, setBusy: () => {},
    PROFILE_FIELDS: [], nullable: (value) => value || null,
    queryClient: {
      setQueryData: (...args) => cacheUpdates.push(args), invalidateQueries: async () => {},
    },
    user: { id: 1, ma_vai_tro: "quan_tri_vien" }, id: record.id,
    API: { employees: "/nhan_vien" },
    writeResource: async (request) => {
      writes.push(request);
      if (writeError) throw writeError;
      return { data: { ...record, vai_tro_id: 3, ma_vai_tro: "nhan_vien" }, etag: '"new"' };
    },
    roleChangeBody, endsOwnSession, roles: { data: roles },
    PASSWORD_MIN_LENGTH, passwordTooShort, passwordResetBody, endsOwnSessionAfterPasswordReset,
    logout: (message) => logouts.push(message), login: async () => {},
    setNewPassword: () => {}, setPasswordVisible: () => {},
    showSuccess: (options) => successes.push(options),
  };
  const handler = new Function("env", `
    const { ${Object.keys(environment).join(", ")} } = env;
    ${users.slice(start, end)}
    return handleInlineSubmit;
  `)(environment);
  handler({ preventDefault() {} });
  return { confirmation, writes, logouts, errors, successes, cacheUpdates };
}

// UC-07 AC-1: đủ ba vai trò và chỉ hai vai trò còn lại chọn được
test("role options include all three roles for each current role", () => {
  for (const current of roles) {
    const options = roleOptions(roles, current.id);
    assert.deepEqual(options.map((option) => option.id), [1, 2, 3]);
    assert.equal(options.filter((option) => !option.disabled).length, 2);
  }
});

// UC-07 AC-3: NV được chọn QTV; select không bị khóa khi tài khoản hiện tại là QTV
test("employee can select administrator and administrators can edit their role", () => {
  const options = roleOptions(roles, 3);
  assert.equal(options[0].disabled, false);
  assert.equal(options[0].label, "Quản trị viên");
  const select = users.slice(users.indexOf('id="inline-vai-tro"'), users.indexOf('id="inline-vai-tro"') + 900);
  assert.match(select, /disabled=\{busy \|\| roles.isLoading\}/);
  assert.match(select, /disabled=\{role.disabled\}/);
  assert.doesNotMatch(users, /lockedAdmin/);
});

// UC-07 A2: vai trò hiện tại disabled và nhãn có (hiện tại), so ID chuỗi/số
test("current role option is disabled and marked current", () => {
  assert.deepEqual(roleOptions(roles, "2"), [
    { id: 1, label: "Quản trị viên", disabled: false },
    { id: 2, label: "Quản lý kho (hiện tại)", disabled: true },
    { id: 3, label: "Nhân viên", disabled: false },
  ]);
});

// UC-07 AC-2: lý do thiếu/null/rỗng/khoảng trắng thành null, vai_tro_id là số
test("role request accepts an optional reason", () => {
  for (const reason of [undefined, null, "", "   "]) {
    assert.deepEqual(roleChangeBody("1", reason), { vai_tro_id: 1, ly_do: null });
  }
});

// UC-07 AC-2: lý do có nội dung được trim
test("role request trims a supplied reason", () => {
  assert.deepEqual(roleChangeBody("3", "  Phân công mới  "), {
    vai_tro_id: 3, ly_do: "Phân công mới",
  });
});

// UC-07 D5: ô lý do ngay dưới Vai trò chỉ hiện khi đổi, textarea đúng khuôn và không bắt buộc
test("optional reason appears below role only for a changed selection", () => {
  const area = users.slice(users.indexOf('<InlineEditRow icon={Layers} label="Vai trò"'), users.indexOf('htmlFor="inline-ngay-vao-lam"'));
  assert.match(area, /Number\(roleId\) !== Number\(activeBaselineRecord.vai_tro_id\)/);
  assert.match(area, /label="Lý do đổi vai trò"/);
  assert.match(area, /<textarea[\s\S]*className="admin-inline-input"[\s\S]*rows=\{2\}[\s\S]*maxLength=\{1000\}/);
  assert.doesNotMatch(area, /required/);
  assert.match(users, /function handleCancelEdit\(\) \{\s*setRoleReason\(""\)/);
});

// UC-07 A5: nhận diện tự đổi vai trò với ID chuỗi/số
test("only changing own account ends own session", () => {
  assert.equal(endsOwnSession(1, 1), true);
  assert.equal(endsOwnSession("1", 1), true);
  assert.equal(endsOwnSession(4, 1), false);
});

// UC-07 A5: tự đổi thành công đăng xuất ngay, dừng trước mật khẩu và cache/refetch
test("self role change logs out before the password step", async () => {
  const action = editAction({ own: true });
  await action.confirmation.onConfirm();
  assert.deepEqual(action.writes, [{
    path: "/nhan_vien/1/vai_tro", method: "put",
    body: { vai_tro_id: 3, ly_do: "Phân công mới" }, etag: '"reviewed"',
  }]);
  assert.deepEqual(action.logouts, ["Đã đổi vai trò. Vui lòng đăng nhập lại."]);
  assert.deepEqual(action.successes, []);
  assert.deepEqual(action.cacheUpdates, []);
});

// UC-07 AC-1: đổi người khác gửi lý do và tiếp tục bước mật khẩu bằng ETag mới
test("changing another account sends role body then continues saving", async () => {
  const action = editAction({ reason: "   " });
  await action.confirmation.onConfirm();
  assert.deepEqual(action.writes, [
    { path: "/nhan_vien/4/vai_tro", method: "put", body: { vai_tro_id: 3, ly_do: null }, etag: '"reviewed"' },
    { path: "/nhan_vien/4/dat_lai_mat_khau", method: "post", body: { mat_khau_moi: "new-password" }, etag: '"new"' },
  ]);
  assert.deepEqual(action.logouts, []);
  assert.equal(action.successes.length, 1);
});

// UC-07 A7: đóng phần nhập hoặc hủy xác nhận trước khi lưu không ghi vai trò
test("closing before confirmation does not send a role write", () => {
  const action = editAction();
  assert.ok(action.confirmation);
  assert.deepEqual(action.writes, []);
  assert.deepEqual(action.logouts, []);
  assert.match(users, /onClick=\{handleCancelEdit\}/);
  const cancel = users.slice(users.indexOf("  function handleCancelEdit("), users.indexOf("  function handleToggleState("));
  assert.doesNotMatch(cancel, /writeResource/);
  assert.match(cancel, /setRoleId\(String\(base.vai_tro_id/);
});

// UC-07 A8: QLK/NV không truy cập được đường dẫn quản trị tài khoản
test("nonadministrators cannot access role editing", () => {
  for (const role of ["quan_ly", "nhan_vien"]) {
    assert.equal(canAccessPath(role, "/admin/tai-khoan/4"), false);
  }
});

// UC-07 A9: lưu vai trò lỗi không đăng xuất, không ghi mật khẩu và không báo thành công
test("role save failure stops later steps and preserves own session", async () => {
  const error = new Error("save unavailable");
  const action = editAction({ own: true, writeError: error });
  await assert.rejects(action.confirmation.onConfirm(), error);
  assert.equal(action.writes.length, 1);
  assert.deepEqual(action.logouts, []);
  assert.deepEqual(action.successes, []);
  assert.equal(action.errors.at(-1), error);
});
