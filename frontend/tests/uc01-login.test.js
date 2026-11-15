import assert from "node:assert/strict";
import { test } from "node:test";
import { loginErrorMessage } from "../src/features/auth/loginErrors.js";
import { homeFor } from "../src/features/auth/permissions.js";
import { toApiError } from "../src/lib/api/contract.js";

for (const [role, home] of [
  ["quan_tri_vien", "/admin"],
  ["quan_ly", "/kho"],
  ["nhan_vien", "/nv"],
]) {
  // UC-01 AC-1: Đăng nhập thành công theo vai trò
  test(`${role} enters ${home} after login`, () => {
    assert.equal(homeFor(role), home);
  });
}

// UC-01 AC-2: Sai mật khẩu
test("401 reports invalid username or password", () => {
  assert.equal(
    loginErrorMessage({ status: 401 }),
    "Tên đăng nhập hoặc mật khẩu không đúng",
  );
});

// UC-01 AC-3: Tài khoản bị khóa không đăng nhập được
test("403 with the inactive account code reports a locked account", () => {
  const error = toApiError({
    response: {
      status: 403,
      data: { error: { code: "tai_khoan_bi_vo_hieu_hoa", message: "backend message" } },
    },
  });
  assert.equal(loginErrorMessage(error), "Tài khoản đang bị khóa");
});

// UC-01 A1: Thiếu tên đăng nhập hoặc mật khẩu
test("422 asks for both required credentials", () => {
  assert.equal(
    loginErrorMessage({ status: 422 }),
    "Vui lòng nhập đủ tên đăng nhập và mật khẩu",
  );
});

for (const status of [500, 503]) {
  // UC-01 A4: Không ghi được lịch sử đăng nhập
  test(`${status} reports login failure`, () => {
    assert.equal(
      loginErrorMessage({ status }),
      "Đăng nhập thất bại. Vui lòng thử lại.",
    );
  });
}

for (const code of ["khong_co_quyen", "unknown", undefined]) {
  // UC-01 A3: Tài khoản bị khóa; phân biệt lỗi quyền đăng nhập
  test(`403 with ${code} reports missing login permission`, () => {
    assert.equal(
      loginErrorMessage({ status: 403, code }),
      "Tài khoản không có quyền đăng nhập",
    );
  });
}

for (const [status, message] of [
  [0, "Không kết nối được máy chủ. Vui lòng thử lại."],
  [429, "Bạn thử quá nhiều lần. Vui lòng thử lại sau."],
]) {
  // UC-01 A4: Đăng nhập thất bại; giữ thông báo kết nối và giới hạn yêu cầu
  test(`${status} retains its existing login feedback`, () => {
    assert.equal(loginErrorMessage({ status }), message);
  });
}
