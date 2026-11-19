import assert from "node:assert/strict";
import test from "node:test";
import { canCreateIssue, issueTypeLabel } from "../src/features/material-issuing/issueForm.js";

const request = { nhan_vien_duoc_giao_id: 3, trang_thai: "dang_thuc_hien", loai_yeu_cau: "xuat_giao", so_luong_can_san_xuat: 8 };
test("only an assigned employee can create component issues for positive production demand", () => {
  assert.equal(canCreateIssue(request, "xuat_linh_kien", 3), true);
  assert.equal(canCreateIssue(request, "xuat_linh_kien", 4), false);
  assert.equal(canCreateIssue({ ...request, trang_thai: "cho_bo_sung_linh_kien" }, "xuat_linh_kien", 3), true);
  for (const trang_thai of ["nhap", "da_gui", "hoan_thanh", "da_huy"])
    assert.equal(canCreateIssue({ ...request, trang_thai }, "xuat_linh_kien", 3), false);
  assert.equal(canCreateIssue({ ...request, so_luong_can_san_xuat: 0 }, "xuat_linh_kien", 3), false);
  assert.equal(canCreateIssue(null, "xuat_linh_kien", 3), false);
});
test("product issues require an export request and zero production or approved completion", () => {
  assert.equal(canCreateIssue({ ...request, trang_thai: "cho_bo_sung_linh_kien" }, "xuat_thanh_pham", 3, { trang_thai: "da_duyet" }), false);
  assert.equal(canCreateIssue(request, "xuat_thanh_pham", 3), false);
  for (const trang_thai of ["nhap", "cho_duyet", "tu_choi"])
    assert.equal(canCreateIssue(request, "xuat_thanh_pham", 3, { trang_thai }), false);
  assert.equal(canCreateIssue(request, "xuat_thanh_pham", 3, { trang_thai: "da_duyet" }), true);
  assert.equal(canCreateIssue({ ...request, so_luong_can_san_xuat: 0 }, "xuat_thanh_pham", 3), true);
  assert.equal(canCreateIssue({ ...request, so_luong_can_san_xuat: null }, "xuat_thanh_pham", 3), false);
  assert.equal(canCreateIssue({ ...request, loai_yeu_cau: "nhap_kho" }, "xuat_thanh_pham", 3, { trang_thai: "da_duyet" }), false);
  assert.equal(canCreateIssue(request, "xuat_vat_tu", 3), false);
  assert.equal(issueTypeLabel("xuat_linh_kien"), "Phiếu xuất linh kiện");
});
