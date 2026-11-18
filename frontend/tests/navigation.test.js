import assert from "node:assert/strict";
import { test } from "node:test";
import { canAccessPath, homeFor } from "../src/features/auth/permissions.js";
import { navigationFor } from "../src/layouts/navigation.js";

const areas = { quan_tri_vien: "/admin", quan_ly: "/kho", nhan_vien: "/nv" };

for (const [role, home] of Object.entries(areas)) {
  test(`${role}: sidebar only contains links in its permitted area`, () => {
    const groups = navigationFor(role);
    assert.ok(groups.length > 0);
    assert.equal(groups[0].items[0][0], home);
    for (const group of groups) {
      assert.ok(group.items.length > 0);
      for (const [path] of group.items) {
        assert.ok(path === home || path.startsWith(`${home}/`));
        assert.equal(canAccessPath(role, path), true);
      }
    }
  });

  test(`${role}: direct URLs share sidebar permissions including nested records`, () => {
    assert.equal(canAccessPath(role, "/ho-so"), true);
    assert.equal(canAccessPath(role, `${home}/record/42`), true);
    assert.equal(canAccessPath(role, `${home}-other`), false);
    for (const otherHome of Object.values(areas).filter((area) => area !== home)) {
      assert.equal(canAccessPath(role, otherHome), false);
      assert.equal(canAccessPath(role, `${otherHome}/record/42`), false);
    }
  });
}

test("missing, unknown and inherited property names never grant a role or menu", () => {
  for (const role of [null, undefined, "", "unknown", "toString", "constructor", "__proto__"]) {
    assert.deepEqual(navigationFor(role), []);
    assert.equal(homeFor(role), "/403");
    for (const path of [...Object.values(areas), "/ho-so", "/403"])
      assert.equal(canAccessPath(role, path), false);
  }
});

// UC-29 D5: Việc được giao dẫn tới yêu cầu; giữ quyền xem phiếu xuất liên quan
test("employee sidebar focuses on assigned work without revoking read-only document access", () => {
  const paths = navigationFor("nhan_vien").flatMap((group) => group.items.map(([path]) => path));
  assert.deepEqual(paths, ["/nv", "/nv/yeu-cau", "/nv/phieu-xuat", "/nv/chung-tu-hoan-thanh", "/nv/ton-kho"]);
  assert.equal(canAccessPath("nhan_vien", "/nv/yeu-cau"), true);
  assert.equal(canAccessPath("nhan_vien", "/nv/phieu-xuat"), true);
  assert.equal(canAccessPath("nhan_vien", "/nv/chung-tu-hoan-thanh"), true);
  for (const path of ["/nv/xuat-nvl", "/nv/xuat-tp", "/nv/phieu"]) {
    assert.equal(paths.includes(path), false);
    assert.equal(canAccessPath("nhan_vien", path), true);
  }
});

test("admin sidebar displays all 6 approved navigation items in order with read-only catalog access", () => {
  const items = navigationFor("quan_tri_vien").flatMap((group) => group.items);
  assert.deepEqual(items, [
    ["/admin", "Tổng quan"],
    ["/admin/tai-khoan", "Quản lý tài khoản"],
    ["/admin/vai-tro", "Quản lý vai trò"],
    ["/admin/mat-hang", "Tra cứu mặt hàng"],
    ["/admin/nha-cung-cap", "Tra cứu nhà cung cấp"],
    ["/admin/lich-su", "Lịch sử thao tác"],
  ]);
  assert.equal(canAccessPath("quan_tri_vien", "/admin/lich-su"), true);
  assert.equal(canAccessPath("quan_tri_vien", "/admin/mat-hang/1"), true);
  assert.equal(canAccessPath("quan_tri_vien", "/admin/nha-cung-cap/1"), true);
  assert.equal(canAccessPath("quan_tri_vien", "/kho/mat-hang"), false);
  assert.equal(canAccessPath("quan_tri_vien", "/kho/nha-cung-cap"), false);
});
