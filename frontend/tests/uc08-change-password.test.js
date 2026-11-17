import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  endsOwnSessionAfterPasswordReset,
  passwordResetBody,
  passwordTooShort,
} from "../src/features/auth/accountPassword.js";
import { PASSWORD_MIN_LENGTH } from "../src/features/auth/accountForm.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const users = read("../src/features/auth/UsersPage.jsx");

function editAction({ own = false, password = "123456", writeError } = {}) {
  const record = { id: own ? 1 : 5, vai_tro_id: 1, ma_vai_tro: "quan_tri_vien" };
  const writes = [], logouts = [], errors = [], successes = [], cacheUpdates = [], passwords = [];
  let confirmation;
  let refetches = 0;
  const start = users.indexOf("  function handleInlineSubmit(");
  const end = users.indexOf("\n  const roleChoices", start);
  const environment = {
    editBaselineRef: { current: { data: record, etag: '"reviewed"' } }, snapshot: null,
    busy: false, isProfileChanged: () => false, values: {}, newPassword: password,
    roleId: "1", roleReason: "", ApiError: Error, setSaveError: (error) => errors.push(error), validateUsername: () => true,
    editInitializedRef: { current: true }, onCancelEdit: () => {},
    confirm: (options) => { confirmation = options; }, setBusy: () => {},
    PROFILE_FIELDS: [], nullable: (value) => value || null,
    queryClient: {
      setQueryData: (...args) => cacheUpdates.push(args),
      invalidateQueries: async () => { refetches += 1; },
    },
    user: { id: 1, ma_vai_tro: "quan_tri_vien" }, id: record.id,
    API: { employees: "/nhan_vien" },
    writeResource: async (request) => {
      writes.push(request);
      if (writeError) throw writeError;
      return { data: record, etag: '"saved"' };
    },
    PASSWORD_MIN_LENGTH, passwordTooShort, passwordResetBody, endsOwnSessionAfterPasswordReset,
    logout: (message) => logouts.push(message),
    setNewPassword: (value) => passwords.push(value), setPasswordVisible: () => {},
    showSuccess: (options) => successes.push(options),
  };
  const handler = new Function("env", `
    const { ${Object.keys(environment).join(", ")} } = env;
    ${users.slice(start, end)}
    return handleInlineSubmit;
  `)(environment);
  handler({ preventDefault() {} });
  return { confirmation, writes, logouts, errors, successes, cacheUpdates, passwords,
    refetches: () => refetches };
}

// UC-08 AC-3: dùng chung giới hạn 6; mật khẩu giữ nguyên khoảng trắng
test("password minimum is six characters without trimming", () => {
  assert.equal(PASSWORD_MIN_LENGTH, 6);
  assert.equal(passwordTooShort("12345"), true);
  assert.equal(passwordTooShort("123456"), false);
  assert.equal(passwordTooShort(" 12345"), false);
});

// UC-08 A1: handler từ chối 5 ký tự trước xác nhận, thông báo nêu 6 ký tự
test("short password does not create a write confirmation", () => {
  const action = editAction({ password: "12345" });
  assert.equal(action.confirmation, undefined);
  assert.equal(action.errors.length, 1);
  assert.match(action.errors[0].message, /6.*1024/);
  assert.deepEqual(action.writes, []);
});

// UC-08 AC-5: body chỉ chứa mật khẩu mới, không hỏi mật khẩu hiện tại
test("reset payload contains only the unmodified new password", () => {
  assert.deepEqual(passwordResetBody(" 12345"), { mat_khau_moi: " 12345" });
  assert.doesNotMatch(users, /mat_khau_hien_tai|Mật khẩu hiện tại/);
});

// UC-08 AC-5: nhận diện tự đổi với ID chuỗi/số
test("only resetting own account ends the current session", () => {
  assert.equal(endsOwnSessionAfterPasswordReset(1, 1), true);
  assert.equal(endsOwnSessionAfterPasswordReset("1", 1), true);
  assert.equal(endsOwnSessionAfterPasswordReset(5, 1), false);
});

// UC-08 A2: tự đổi thành công đăng xuất ngay trước cache/refetch, không tự đăng nhập
test("self reset logs out immediately after a successful password write", async () => {
  const action = editAction({ own: true });
  await action.confirmation.onConfirm();
  assert.deepEqual(action.writes, [{
    path: "/nhan_vien/1/dat_lai_mat_khau", method: "post",
    body: { mat_khau_moi: "123456" }, etag: '"reviewed"',
  }]);
  assert.deepEqual(action.logouts, ["Đã đổi mật khẩu. Vui lòng đăng nhập lại."]);
  assert.deepEqual(action.cacheUpdates, []);
  assert.deepEqual(action.successes, []);
  assert.deepEqual(action.passwords, [""]);
  assert.equal(action.refetches(), 0);
  assert.doesNotMatch(users, /\blogin\(/);
});

// UC-08 AC-4: đổi cho người khác giữ phiên QTV, cập nhật cache và báo thành công
test("resetting another account preserves the administrator session", async () => {
  const action = editAction();
  await action.confirmation.onConfirm();
  assert.deepEqual(action.writes, [{
    path: "/nhan_vien/5/dat_lai_mat_khau", method: "post",
    body: { mat_khau_moi: "123456" }, etag: '"reviewed"',
  }]);
  assert.deepEqual(action.logouts, []);
  assert.equal(action.cacheUpdates.length, 1);
  assert.equal(action.successes.length, 1);
  assert.equal(action.refetches(), 1);
});

// UC-08 AC-6: Hồ sơ chỉ còn thông tin nhân viên; gỡ endpoint và nhãn tự đổi mật khẩu
test("profile offers no password form and no self-service endpoint", () => {
  const profile = read("../src/features/auth/ProfilePage.jsx");
  const endpoints = read("../src/lib/api/endpoints.js");
  const layout = read("../src/layouts/MainLayout.jsx");
  const profileCode = profile.replace(/^\s*\/\/.*$/gm, "");
  assert.doesNotMatch(profileCode, /API\.password|Đổi mật khẩu|<form|type="password"/);
  assert.match(profile, /<Card title="Hồ sơ nhân viên">/);
  assert.match(profile, /<PageHeader title="Hồ sơ"/);
  assert.doesNotMatch(endpoints, /doi_mat_khau|\bpassword:/);
  assert.match(layout, /pathname === "\/ho-so"\) return \[\{ label: "Hồ sơ" \}\]/);
  assert.doesNotMatch(layout, /Hồ sơ & đổi mật khẩu/);
});

// UC-08 A4: QLK/NV không truy cập được trang quản trị đổi mật khẩu
test("nonadministrators cannot open account password management", () => {
  for (const role of ["quan_ly", "nhan_vien"]) {
    assert.equal(canAccessPath(role, "/admin/tai-khoan/5"), false);
  }
});

// UC-08 A5: đóng phần nhập hoặc hủy xác nhận trước lưu không gửi request đổi mật khẩu
test("closing before saving performs no password write", () => {
  const action = editAction();
  assert.ok(action.confirmation);
  assert.deepEqual(action.writes, []);
  assert.deepEqual(action.logouts, []);
  assert.match(users, /onClick=\{handleCancelEdit\}/);
  const cancel = users.slice(users.indexOf("  function handleCancelEdit("), users.indexOf("  function handleToggleState("));
  assert.match(cancel, /setNewPassword\(""\)/);
  assert.doesNotMatch(cancel, /writeResource/);
});

// UC-08 A6: lưu thất bại báo lỗi, không đăng xuất hoặc báo thành công
test("failed password write preserves the current session", async () => {
  const error = new Error("save unavailable");
  const action = editAction({ own: true, writeError: error });
  await assert.rejects(action.confirmation.onConfirm(), error);
  assert.equal(action.writes.length, 1);
  assert.deepEqual(action.logouts, []);
  assert.deepEqual(action.cacheUpdates, []);
  assert.deepEqual(action.successes, []);
  assert.equal(action.errors.at(-1), error);
});
