import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canChangeAccountState, lockRequestBody, stateConfirmOptions } from "../src/features/auth/accountState.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

const users = readFileSync(new URL("../src/features/auth/UsersPage.jsx", import.meta.url), "utf8");
const feedback = readFileSync(new URL("../src/components/FeedbackProvider.jsx", import.meta.url), "utf8");
const record = {
  id: 1, ma_nhan_vien: "NV-000001", ten_dang_nhap: "uc05-admin",
  ma_vai_tro: "quan_tri_vien", trang_thai: "hoat_dong",
};

function stateAction(overrides = {}) {
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
    async (request) => { writes.push(request); },
    canChangeAccountState, lockRequestBody, stateConfirmOptions,
  );
  prompt({
    record, etag: '"reviewed"', currentUserId: 9,
    confirm: (options) => { confirmation = options; },
    notify: (message) => notices.push(message),
    queryClient: { invalidateQueries: async (options) => { invalidations.push(options); } },
    onError: (error) => errors.push(error),
    ...overrides,
  });
  return { confirmation, writes, invalidations, notices, errors };
}

// UC-05 AC-1: lý do thiếu/rỗng/khoảng trắng thành null
test("lock request accepts absent and blank reasons", () => {
  for (const reason of [undefined, null, "", "   "]) {
    assert.deepEqual(lockRequestBody(reason), { ly_do: null });
  }
});

// UC-05 AC-1: lý do nhập được trim trước gửi
test("lock request trims a supplied reason", () => {
  assert.deepEqual(lockRequestBody("  Tạm ngừng truy cập  "), { ly_do: "Tạm ngừng truy cập" });
});

// UC-05 AC-1: hộp khóa giữ tiêu đề/cảnh báo, cho phép bỏ trống lý do
test("lock confirmation keeps its warning and makes the reason optional", () => {
  assert.deepEqual(stateConfirmOptions(record), {
    title: "Khóa tài khoản", reasonOptional: true, danger: true, method: "delete", pathSuffix: "",
  });
  const { confirmation } = stateAction();
  assert.equal(confirmation.title, "Khóa tài khoản");
  assert.equal(confirmation.reason, true);
  assert.equal(confirmation.reasonOptional, true);
  assert.equal(confirmation.danger, true);
  assert.equal(confirmation.description, "NV-000001 · uc05-admin");
  assert.equal(confirmation.impact,
    "Bảo toàn hồ sơ, công việc và chứng từ đã lập. Khóa tài khoản chặn mọi request tiếp theo.");
});

// UC-05 AC-1: xác nhận khóa trống gửi DELETE với null và ETag đã xem
test("confirming a blank lock sends DELETE with null reason and the reviewed ETag", async () => {
  const action = stateAction();
  await action.confirmation.onConfirm("");
  assert.deepEqual(action.writes, [{
    path: "/nhan_vien/1", method: "delete", body: { ly_do: null }, etag: '"reviewed"',
  }]);
  assert.deepEqual(action.invalidations, [{ queryKey: ["resources"] }]);
  assert.deepEqual(action.notices, ["Đã khóa tài khoản."]);
});

// UC-05 AC-3: nút cho phép chọn QTV; backend quyết định QTV cuối
test("administrators can be selected for a state change", () => {
  assert.equal(canChangeAccountState(record), true);
  assert.equal(canChangeAccountState({ ...record, trang_thai: "bi_khoa" }), true);
  assert.ok(stateAction().confirmation);
});

// UC-05 A3: tự khóa vẫn có hộp xác nhận và kiểm tra lại phiên ngay sau ghi thành công
test("self lock is allowed and refreshes the current session immediately", async () => {
  const action = stateAction({ currentUserId: record.id });
  assert.ok(action.confirmation);
  await action.confirmation.onConfirm("Tự khóa");
  assert.deepEqual(action.writes[0].body, { ly_do: "Tự khóa" });
  assert.deepEqual(action.invalidations, [
    { queryKey: ["session"] }, { queryKey: ["resources"] },
  ]);
});

// UC-05 AC-3: danh sách và chi tiết dùng chung kiểm tra trạng thái, không ẩn QTV/chính mình
test("both list and detail buttons use the shared state eligibility", () => {
  assert.match(users, /const canChangeState = canChangeAccountState\(row\)/);
  assert.match(users, /const canChangeState = canChangeAccountState\(activeBaselineRecord\)/);
  const rowAction = users.slice(users.indexOf("async function handleRowStateAction("), users.indexOf('className="admin-screen"'));
  assert.match(rowAction, /readResource\(/);
  assert.match(rowAction, /record: freshRecord/);
  assert.match(rowAction, /etag: snapshot\?\.etag/);
  assert.doesNotMatch(rowAction, /ma_vai_tro|freshRecord\.id === user\.id/);
});

// UC-05 AC-3: chỉ bản ghi có trạng thái hợp lệ mới được thao tác
test("missing or invalid account state cannot be changed", () => {
  for (const item of [null, undefined, {}, { trang_thai: "nhap" }]) {
    assert.equal(canChangeAccountState(item), false);
    assert.equal(stateAction({ record: item }).confirmation, undefined);
  }
});

// UC-05 AC-1: reasonOptional bỏ required và không disable xác nhận khi trống; mặc định false
test("shared confirmation keeps required reasons by default and supports optional ones", () => {
  assert.match(feedback, /const reasonOptional = options\.reasonOptional \?\? false/);
  assert.match(feedback, /required=\{!reasonOptional\}/);
  assert.match(feedback, /disabled=\{busy \|\| Boolean\(options\.reason && !reasonOptional && !reason\.trim\(\)\)\}/);
});

// UC-05 A8: đối chứng mở khóa giữ lý do bắt buộc tới UC-06
test("unlock still requires a reason and uses the existing POST endpoint", async () => {
  const locked = { ...record, trang_thai: "bi_khoa" };
  assert.deepEqual(stateConfirmOptions(locked), {
    title: "Mở khóa tài khoản", reasonOptional: false, danger: false, method: "post", pathSuffix: "/mo_khoa",
  });
  const action = stateAction({ record: locked });
  assert.equal(action.confirmation.reasonOptional, false);
  await action.confirmation.onConfirm("Khôi phục truy cập");
  assert.deepEqual(action.writes, [{
    path: "/nhan_vien/1/mo_khoa", method: "post", body: { ly_do: "Khôi phục truy cập" }, etag: '"reviewed"',
  }]);
});

// UC-05 A6: mở rồi đóng/hủy hộp xác nhận không gửi lệnh ghi
test("opening confirmation without saving does not send a write", () => {
  const action = stateAction();
  assert.ok(action.confirmation);
  assert.deepEqual(action.writes, []);
  assert.deepEqual(action.invalidations, []);
  assert.deepEqual(action.notices, []);
  assert.match(feedback, /<Button variant="secondary" onClick=\{onClose\} disabled=\{busy\}>\s*Hủy/);
});

// UC-05 A4: chưa có ETag không được xác nhận hay gửi thao tác
test("missing ETag reports an error before confirmation", () => {
  const action = stateAction({ etag: null });
  assert.equal(action.confirmation, undefined);
  assert.deepEqual(action.writes, []);
  assert.equal(action.errors.length, 1);
});

// UC-05 A8: QLK/NV không truy cập được đường dẫn quản trị danh sách/chi tiết
test("nonadministrators cannot open account management routes directly", () => {
  for (const role of ["quan_ly", "nhan_vien"]) {
    for (const path of ["/admin/tai-khoan", "/admin/tai-khoan/1"]) {
      assert.equal(canAccessPath(role, path), false);
    }
  }
});
