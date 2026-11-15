import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  PASSWORD_MIN_LENGTH,
  buildCreateAccountBody,
  creatableRoles,
} from "../src/features/auth/accountForm.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

const roles = ["quan_tri_vien", "quan_ly", "nhan_vien"].map((code, index) => ({
  id: index + 1, ma_vai_tro: code, ten_vai_tro: code,
}));
const profileFields = ["ho_ten", "email", "so_dien_thoai", "ngay_sinh", "ngay_vao_lam", "he_so_luong"];
const values = {
  ten_dang_nhap: "  uc04-new  ", mat_khau: " 12345", vai_tro_id: "1",
  ma_nhan_vien: "NV-999999", ly_do: "  Bổ sung tài khoản  ",
  ho_ten: "  Người mới  ", email: "", so_dien_thoai: "", ngay_sinh: "",
  ngay_vao_lam: "2026-11-15", he_so_luong: "1.25",
};
const source = readFileSync(new URL("../src/features/auth/UsersPage.jsx", import.meta.url), "utf8");
const form = source.slice(source.indexOf("function EmployeeForm("));

// UC-04 AC-1: select tạo cho phép vai trò QTV
test("administrator is a creatable role", () => {
  assert.deepEqual(creatableRoles(roles).find((role) => role.ma_vai_tro === "quan_tri_vien"), roles[0]);
});

// UC-04 AC-2: select giữ đủ QTV, QLK và NV từ API
test("creation lists all three roles supplied by the API", () => {
  assert.deepEqual(creatableRoles(roles), roles);
  assert.deepEqual(creatableRoles([]), []);
  assert.match(form, /creatableRoles\(roles\)/);
  assert.match(form, /editableRoles\.map/);
});

// UC-04 AC-4: ô mật khẩu dùng giới hạn 6, giữ required, maxLength và autoComplete
test("initial password input uses the six character minimum", () => {
  assert.equal(PASSWORD_MIN_LENGTH, 6);
  const password = form.match(/<Field\s+label="Mật khẩu ban đầu"[\s\S]*?\/>/)?.[0];
  assert.ok(password);
  assert.match(password, /minLength=\{PASSWORD_MIN_LENGTH\}/);
  assert.match(password, /maxLength=\{1024\}/);
  assert.match(password, /\brequired\b/);
  assert.match(password, /autoComplete="new-password"/);
});

// UC-04 R6: bỏ ô mã và không gửi key mã dù values có sẵn mã do client nhập
test("creation payload excludes a client supplied employee code", () => {
  const body = buildCreateAccountBody(values, profileFields);
  assert.equal(Object.hasOwn(body, "ma_nhan_vien"), false);
  assert.doesNotMatch(form, /ma_nhan_vien|Mã nhân viên/);
  assert.match(form, /buildCreateAccountBody\(values, PROFILE_FIELDS\)/);
});

// UC-04 AC-5: trim lý do, rỗng hoặc không nhập chuyển null
test("reason is trimmed and blank or absent reasons become null", () => {
  assert.equal(buildCreateAccountBody(values, profileFields).ly_do, "Bổ sung tài khoản");
  for (const ly_do of ["", "   ", null, undefined]) {
    assert.equal(buildCreateAccountBody({ ...values, ly_do }, profileFields).ly_do, null);
  }
});

// UC-04 AC-5: textarea lý do tùy chọn nằm sau hồ sơ và trước hàng nút
test("optional reason textarea follows the profile grid", () => {
  const reason = form.match(/<Field\s+as="textarea"[^>]*label="Lý do"[^>]*\/>/)?.[0];
  assert.ok(reason);
  assert.match(reason, /rows=\{3\}/);
  assert.match(reason, /maxLength=\{1000\}/);
  assert.doesNotMatch(reason, /\brequired\b/);
  assert.ok(form.indexOf('label="Hệ số lương"') < form.indexOf(reason));
  assert.ok(form.indexOf(reason) < form.indexOf('className="actions actions-end"'));
});

// UC-04 A1: body chuẩn hóa trường bắt buộc theo R7 và giữ hồ sơ tùy chọn
test("payload trims username, converts role ID and preserves password and profile types", () => {
  assert.deepEqual(buildCreateAccountBody(values, profileFields), {
    ten_dang_nhap: "uc04-new", mat_khau: " 12345", vai_tro_id: 1,
    ly_do: "Bổ sung tài khoản", ho_ten: "Người mới", email: null,
    so_dien_thoai: null, ngay_sinh: null, ngay_vao_lam: "2026-11-15", he_so_luong: "1.25",
  });
  assert.deepEqual(buildCreateAccountBody({ ...values, he_so_luong: "" }, profileFields).he_so_luong, null);
});

// UC-04 A5: Hủy là điều hướng về danh sách, không gọi submit/save
test("cancel navigates back to the list without submitting the form", () => {
  assert.match(form, /<Link to=\{base\}>Hủy<\/Link>/);
  assert.match(form, /<form onSubmit=\{submit\}/);
});

// UC-04 A6: đường dẫn tạo chỉ dành cho QTV, QLK/NV không mở trực tiếp được
test("only administrators can open the new account route", () => {
  assert.equal(canAccessPath("quan_tri_vien", "/admin/tai-khoan/moi"), true);
  for (const role of ["quan_ly", "nhan_vien"]) {
    assert.equal(canAccessPath(role, "/admin/tai-khoan/moi"), false);
  }
});
