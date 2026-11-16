import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  ACCOUNT_SEARCH_LABEL,
  ACCOUNT_SORT_OPTIONS,
  DEFAULT_ACCOUNT_SORT,
  accountMetaLine,
} from "../src/features/auth/accountList.js";
import { canAccessPath } from "../src/features/auth/permissions.js";

for (const role of ["quan_ly", "nhan_vien"]) {
  // UC-03 AC-2: Người không có quyền bị chặn khi gõ thẳng đường dẫn quản trị tài khoản
  test(`${role} cannot open the account administration page`, () => {
    assert.equal(canAccessPath(role, "/admin/tai-khoan"), false);
  });
}

// UC-03 AC-2: Người không có quyền bị chặn — đối chứng QTV truy cập đúng route thực tế
test("administrator can open the account route declared by the router", () => {
  const routes = readFileSync(new URL("../src/routes/index.jsx", import.meta.url), "utf8");
  assert.ok(routes.includes('path="/admin/tai-khoan/:id?"'));
  assert.equal(canAccessPath("quan_tri_vien", "/admin/tai-khoan"), true);
});

// UC-03 AC-3: Tìm kiếm, lọc đúng tiêu chí — R3 chỉ có bốn lựa chọn sort hợp lệ của API
test("account sorting has four API-supported choices and defaults to employee code", () => {
  assert.deepEqual(ACCOUNT_SORT_OPTIONS, [
    { value: "ma_nhan_vien", label: "Mã NV tăng dần" },
    { value: "-ma_nhan_vien", label: "Mã NV giảm dần" },
    { value: "ho_ten", label: "Họ tên tăng dần" },
    { value: "-ho_ten", label: "Họ tên giảm dần" },
  ]);
  const schemas = readFileSync(
    new URL("../../backend/app/modules/nhan_vien/schemas.py", import.meta.url), "utf8",
  );
  const employeeSort = schemas.match(/EmployeeSort = Literal\[([\s\S]*?)\]/)?.[1];
  assert.ok(employeeSort, "EmployeeSort must be declared in backend schemas");
  const allowed = [...employeeSort.matchAll(/"([^"]+)"/g)].map((match) => match[1]);
  for (const { value } of ACCOUNT_SORT_OPTIONS) assert.ok(allowed.includes(value));
  assert.equal(DEFAULT_ACCOUNT_SORT, "ma_nhan_vien");
  assert.ok(ACCOUNT_SORT_OPTIONS.some(({ value }) => value === DEFAULT_ACCOUNT_SORT));
});

// UC-03 AC-1: Quản trị viên thấy toàn bộ tài khoản — Main 2 có mã NV và tên đăng nhập
test("account meta line displays employee code and username", () => {
  assert.equal(
    accountMetaLine({ ma_nhan_vien: "NV-000017", ten_dang_nhap: "uc01-user" }),
    "NV-000017 · uc01-user",
  );
});

// UC-03 AC-3: Tìm kiếm, lọc đúng tiêu chí — R3 nhãn tìm kiếm nói rõ mã NV hoặc họ tên
test("account search label describes the two searchable fields", () => {
  assert.equal(ACCOUNT_SEARCH_LABEL, "Tìm theo mã NV hoặc họ tên");
});
