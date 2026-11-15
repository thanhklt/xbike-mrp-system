import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canChangeAccountState, lockRequestBody, stateConfirmOptions } from "../src/features/auth/accountState.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

const users = readFileSync(new URL("../src/features/auth/UsersPage.jsx", import.meta.url), "utf8");
const feedback = readFileSync(new URL("../src/components/FeedbackProvider.jsx", import.meta.url), "utf8");
const record = {
  id: 3, ma_nhan_vien: "NV-000003", ten_dang_nhap: "uc06-user",
  ma_vai_tro: "nhan_vien", trang_thai: "bi_khoa",
};

function unlockAction({ etag = '"reviewed"', writeError } = {}) {
  const start = users.indexOf("function promptAccountStateChange(");
  const end = users.indexOf("// UC-03", start);
  const writes = [];
  const invalidations = [];
  const notices = [];
  const errors = [];
  let confirmation;
  const prompt = new Function(
    "API", "ApiError", "writeResource", "canChangeAccountState", "lockRequestBody", "stateConfirmOptions",
    `${users.slice(start, end)}; return promptAccountStateChange;`,
  )(
    { employees: "/nhan_vien" }, Error,
    async (request) => {
      writes.push(request);
      if (writeError) throw writeError;
    },
    canChangeAccountState, lockRequestBody, stateConfirmOptions,
  );
  prompt({
    record, etag, currentUserId: 1,
    confirm: (options) => { confirmation = options; },
    notify: (message) => notices.push(message),
    queryClient: { invalidateQueries: async (options) => { invalidations.push(options); } },
    onError: (error) => errors.push(error),
  });
  return { confirmation, writes, invalidations, notices, errors };
}

// UC-06 AC-1: mở khóa cho phép lý do trống, giữ tiêu đề, POST /mo_khoa và không danger
test("unlock confirmation accepts an optional reason and keeps its action options", () => {
  assert.deepEqual(stateConfirmOptions(record), {
    title: "Mở khóa tài khoản", reasonOptional: true, danger: false,
    method: "post", pathSuffix: "/mo_khoa",
  });
  const { confirmation } = unlockAction();
  assert.equal(confirmation.title, "Mở khóa tài khoản");
  assert.equal(confirmation.reason, true);
  assert.equal(confirmation.reasonOptional, true);
  assert.equal(confirmation.danger, false);
});

// UC-06 A1: lý do thiếu/null/rỗng/khoảng trắng gửi null qua cùng hàm chuẩn hóa
test("confirming an unlock with no reason sends null and the reviewed ETag", async () => {
  for (const reason of [undefined, null, "", "   "]) {
    assert.deepEqual(lockRequestBody(reason), { ly_do: null });
    const action = unlockAction();
    await action.confirmation.onConfirm(reason);
    assert.deepEqual(action.writes, [{
      path: "/nhan_vien/3/mo_khoa", method: "post", body: { ly_do: null }, etag: '"reviewed"',
    }]);
    assert.deepEqual(action.invalidations, [{ queryKey: ["resources"] }]);
    assert.deepEqual(action.notices, ["Đã mở khóa tài khoản."]);
  }
});

// UC-06 AC-3: lý do mở khóa được trim trước khi gửi để ghi lịch sử
test("unlock trims a supplied reason before sending", async () => {
  const action = unlockAction();
  await action.confirmation.onConfirm("  Khôi phục truy cập  ");
  assert.deepEqual(action.writes[0].body, { ly_do: "Khôi phục truy cập" });
});

// UC-06 A4: mở rồi hủy/đóng hộp xác nhận không gửi request và không báo thành công
test("closing unlock confirmation before saving does not write", () => {
  const action = unlockAction();
  assert.ok(action.confirmation);
  assert.deepEqual(action.writes, []);
  assert.deepEqual(action.invalidations, []);
  assert.deepEqual(action.notices, []);
  assert.match(feedback, /<Button variant="secondary" onClick=\{onClose\} disabled=\{busy\}>\s*Hủy/);
});

// UC-06 A5: QLK/NV không mở được đường dẫn quản trị tài khoản kể cả gõ trực tiếp
test("nonadministrators cannot access account management routes", () => {
  for (const role of ["quan_ly", "nhan_vien"]) {
    for (const path of ["/admin/tai-khoan", "/admin/tai-khoan/3"]) {
      assert.equal(canAccessPath(role, path), false);
    }
  }
});

// UC-06 A2: thiếu ETag không được mở hộp xác nhận hoặc gửi thao tác
test("unlock requires the reviewed ETag before confirmation", () => {
  const action = unlockAction({ etag: null });
  assert.equal(action.confirmation, undefined);
  assert.deepEqual(action.writes, []);
  assert.equal(action.errors.length, 1);
});

// UC-06 A6: lỗi lưu được truyền cho hộp xác nhận, không thông báo thành công hoặc reload
test("failed unlock propagates its error and does not report success", async () => {
  const error = new Error("save unavailable");
  const action = unlockAction({ writeError: error });
  await assert.rejects(action.confirmation.onConfirm(""), error);
  assert.equal(action.writes.length, 1);
  assert.deepEqual(action.invalidations, []);
  assert.deepEqual(action.notices, []);
});
