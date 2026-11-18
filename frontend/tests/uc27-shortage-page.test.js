import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CHECK_COLUMNS } from "../src/features/production/requestForm.js";
import {
  SHORTAGE_COLUMNS,
  shortageRequestEntries,
  shortageRows,
} from "../src/features/production/shortageView.js";
import { canAccessPath } from "../src/features/auth/permissions.js";
import { navigationFor } from "../src/layouts/navigation.js";
import { API } from "../src/lib/api/endpoints.js";
import { dateTime } from "../src/lib/format.js";

const source = readFileSync(
  new URL("../src/features/production/ShortagePage.jsx", import.meta.url), "utf8",
);
const routes = readFileSync(new URL("../src/routes/index.jsx", import.meta.url), "utf8");
const record = {
  id: 1, ma_yeu_cau_san_xuat: "YCSX-202611-000001", mat_hang_id: 5,
  loai_yeu_cau: "xuat_giao", so_luong_can_san_xuat: 1200,
  han_hoan_thanh: "2026-12-01", nhan_vien_duoc_giao_id: 20,
  kiem_tra_lan_dau_at: "2026-11-16T08:00:00Z",
};

// UC-27 AC-1: Bảng thiếu của từng yêu cầu dùng sáu cột UC-26
test("request shortage table reuses UC26 columns and preserves separate shortages", () => {
  assert.equal(SHORTAGE_COLUMNS, CHECK_COLUMNS);
  assert.equal(SHORTAGE_COLUMNS.length, 6);
  const missing = {
    mat_hang_id: 2, ma_mat_hang: "MH-000002", ten_mat_hang: "Khung", don_vi_tinh: "cái",
    so_luong_can: 10, so_luong_con_dung: 5, so_luong_thieu: 5,
  };
  const rows = shortageRows([missing]);
  assert.deepEqual(SHORTAGE_COLUMNS.map(({ key }) => rows[0][key]), [
    "MH-000002", "Khung", "cái", 10, 5, 5,
  ]);
  assert.match(source, /<DataTable\s+rows=\{shortageRows\(record\.linh_kien_thieu\)\}\s+columns=\{SHORTAGE_COLUMNS\}\s*\/>/);
});

// UC-27 AC-1: Hiển thị thông tin nhận diện từng yêu cầu chờ bổ sung
test("waiting request information formats all six approved fields", () => {
  const items = [{ id: 5, ten_mat_hang: "Mountain Pro" }];
  const employees = [{ id: 20, ho_ten: "Nguyễn An" }];
  assert.deepEqual(shortageRequestEntries(record, items, employees), [
    ["Thành phẩm", "Mountain Pro"],
    ["Loại yêu cầu", "Sản xuất để xuất giao"],
    ["Số cần sản xuất", "1.200"],
    ["Hạn hoàn thành", "01/12/2026"],
    ["Nhân viên được giao", "Nguyễn An"],
    ["Kiểm tra lần đầu lúc", dateTime(record.kiem_tra_lan_dau_at)],
  ]);
  const stock = Object.fromEntries(shortageRequestEntries({ ...record, loai_yeu_cau: "nhap_kho" }, [], []));
  assert.equal(stock["Loại yêu cầu"], "Sản xuất nhập kho");
  assert.equal(stock["Thành phẩm"], "Mặt hàng #5");
  assert.equal(stock["Nhân viên được giao"], "Nhân viên #20");
  assert.match(source, /<h3>\s*<Link to=\{`\/kho\/yeu-cau\/\$\{record\.id\}`\}>\{record\.ma_yeu_cau_san_xuat\}<\/Link>\s*<\/h3>/);
  assert.match(source, /<InfoGrid\s+entries=\{shortageRequestEntries\(record, items, employees\.data \|\| \[\]\)\}\s*\/>/);
  assert.equal((source.match(/useCatalog\(\)/g) || []).length, 1);
  assert.equal((source.match(/useChoices\(API\.employees\)/g) || []).length, 1);
});

// UC-27 AC-1: Mở form nhập bổ sung từ yêu cầu còn thiếu
test("only a request with shortages links to the receipt form for that request", () => {
  assert.doesNotMatch(source, /\bButton\b|\baction\s*=|useWrite|useMutation|writeResource|mutate|\.(post|put|patch|delete)\s*\(|\bfetch\s*\(/);
  assert.doesNotMatch(source, /API\.receipts|onClick|<form\b|<button\b/);
  const shortageBranch = source.match(/\{record\.da_du \? \([\s\S]*?\) : \(\s*<>([\s\S]*?)<\/>\s*\)\}/)?.[1];
  assert.ok(shortageBranch);
  assert.match(shortageBranch, /<DataTable[\s\S]*?\/>\s*<div className="actions actions-end">\s*<Link\s+className="btn btn-secondary"\s+to=\{`\/kho\/phieu-nhap\/moi\?yeu_cau_san_xuat_id=\$\{record\.id\}`\}\s*>\s*Lập phiếu nhập bổ sung\s*<\/Link>\s*<\/div>/);
  assert.equal((source.match(/Lập phiếu nhập bổ sung/g) || []).length, 1);
  assert.equal((source.match(/<Link\b/g) || []).length, 2);
  assert.match(source, /useResource\(API\.shortages\)/);
});

// UC-27 AC-1: Trang hiển thị một khối yêu cầu chờ bổ sung
test("page loads shortages once and uses shared layout and query states", () => {
  assert.equal(API.shortages, "/nhu_cau_bo_sung_linh_kien");
  assert.equal((source.match(/useResource\(/g) || []).length, 1);
  assert.equal((source.match(/<QueryState query=\{query\}>/g) || []).length, 1);
  assert.match(source, /return \(\s*<>\s*<PageHeader\s+title="Nhu cầu bổ sung linh kiện"\s+subtitle="Xem linh kiện còn thiếu của từng yêu cầu sản xuất đang chờ và lập phiếu nhập bổ sung\."\s*\/>/);
  assert.deepEqual([...source.matchAll(/<Card title="([^"]+)">/g)].map((match) => match[1]), [
    "Yêu cầu chờ bổ sung",
  ]);
  assert.match(source, /query\.data\?\.data \|\| \{\}/);
  assert.doesNotMatch(source, /style=|\.css["']|<Field|Pagination|sort\(|\.reverse\(|tone="warning"|chưa có API/);
});

// UC-27 AC-1: Danh sách rỗng hiển thị thông báo của luồng A1
test("empty waiting list uses the approved request notice", () => {
  assert.deepEqual(shortageRows([]), []);
  assert.match(source, /yeu_cau: requests = \[\]/);
  assert.doesNotMatch(source, /tong_hop|Không có linh kiện cần bổ sung\./);
  assert.match(source, /\{requests\.length \? \(?\s*requests\.map/);
  assert.match(source, /\)\)\s*\)?\s*: \(\s*<Notice>Không có yêu cầu chờ bổ sung linh kiện\.<\/Notice>/);
});

// UC-27 AC-2: Yêu cầu đã đủ chờ kiểm tra lại
test("replenished request shows waiting for recheck notice instead of its shortage table", () => {
  assert.match(source, /\{record\.da_du \? \(\s*<Notice>Đã đủ linh kiện, chờ nhân viên kiểm tra lại\.<\/Notice>\s*\) : \(\s*<>\s*<DataTable/);
  assert.doesNotMatch(source, /requests\.filter|record\.da_du\s*&&|tone=/);
  assert.match(source, /<section key=\{record\.id\} className="stack">/);
});

// UC-27 AC-1: Quản lý kho truy cập trang từ menu Vận hành
test("manager navigation and protected route expose the shortage page after production requests", () => {
  const group = navigationFor("quan_ly").find(({ title }) => title === "Vận hành");
  const index = group.items.findIndex(([path]) => path === "/kho/nhu-cau-bo-sung");
  assert.ok(index >= 0);
  assert.deepEqual(group.items.slice(index, index + 2), [
    ["/kho/nhu-cau-bo-sung", "Nhu cầu bổ sung LK"],
    ["/kho/yeu-cau", "Yêu cầu sản xuất"],
  ]);
  for (const [role, allowed] of [["quan_ly", true], ["nhan_vien", false], ["quan_tri_vien", false]]) {
    assert.equal(canAccessPath(role, "/kho/nhu-cau-bo-sung"), allowed);
    assert.equal(navigationFor(role).some(({ items }) => items.some(([path]) => path === "/kho/nhu-cau-bo-sung")), allowed);
  }
  assert.match(routes, /import \{ ShortagePage \} from "\.\.\/features\/production\/ShortagePage\.jsx"/);
  const warehouseGate = routes.match(/<Route element=\{<RoleGate \/>\}>\s*<Route path="\/kho"[\s\S]*?(?=<Route element=\{<RoleGate \/>\}>)/)?.[0];
  assert.ok(warehouseGate);
  assert.match(warehouseGate, /<Route path="\/kho\/nhu-cau-bo-sung" element=\{<ShortagePage \/>\} \/>/);
});
