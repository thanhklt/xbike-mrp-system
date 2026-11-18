import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CHECK_COLUMNS, unitCell } from "../src/features/production/requestForm.js";
import {
  SHORTAGE_COLUMNS,
  SUMMARY_COLUMNS,
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
const summary = {
  mat_hang_id: 2, ma_mat_hang: "MH-000002", ten_mat_hang: "Khung", don_vi_tinh: "cái",
  tong_can: 20, so_luong_con_dung: 0, so_luong_thieu: 20, so_yeu_cau: 2,
};
const record = {
  id: 1, ma_yeu_cau_san_xuat: "YCSX-202611-000001", mat_hang_id: 5,
  loai_yeu_cau: "xuat_giao", so_luong_can_san_xuat: 1200,
  han_hoan_thanh: "2026-12-01", nhan_vien_duoc_giao_id: 20,
  kiem_tra_lan_dau_at: "2026-11-16T08:00:00Z",
};

// UC-27 AC-1: Bảng tổng hợp hiển thị đúng các số từ API, giữ cả thiếu 0 và id ổn định
test("summary displays twenty required and missing frames for two requests", () => {
  const zero = { ...summary, mat_hang_id: 3, ma_mat_hang: "MH-000003", tong_can: 5,
    so_luong_con_dung: 6, so_luong_thieu: 0, so_yeu_cau: 1 };
  const input = [summary, zero];
  const before = structuredClone(input);
  const rows = shortageRows(input);
  assert.deepEqual(rows, [{ ...summary, id: 2 }, { ...zero, id: 3 }]);
  assert.deepEqual(SUMMARY_COLUMNS.map(({ key }) => rows[0][key]), [
    "MH-000002", "Khung", "cái", 20, 0, 20, 2,
  ]);
  assert.deepEqual(SUMMARY_COLUMNS.map(({ render: _render, ...column }) => column), [
    { key: "ma_mat_hang", label: "Mã" },
    { key: "ten_mat_hang", label: "Tên" },
    { key: "don_vi_tinh", label: "Đơn vị tính", render: unitCell },
    { key: "tong_can", label: "Tổng cần", numeric: true },
    { key: "so_luong_con_dung", label: "Còn dùng được", numeric: true },
    { key: "so_luong_thieu", label: "Thiếu", numeric: true },
    { key: "so_yeu_cau", label: "Số yêu cầu", numeric: true },
  ]);
  assert.deepEqual(input, before);
  assert.match(source, /<DataTable\s+rows=\{shortageRows\(summary\)\}\s+columns=\{SUMMARY_COLUMNS\}/);
});

// UC-27 D3: Bảng thiếu dùng đúng CHECK_COLUMNS UC-26, không định nghĩa lại sáu cột
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

// UC-27 D5: Đủ thông tin đã chốt, định dạng ngày/số, tên từ catalog và nhân viên dùng chung
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

// UC-27 AC-2: Chỉ xem, không Button/action/tạo phiếu nhập hoặc lời gọi ghi, Link duy nhất tới yêu cầu
test("page has no receipt creation action or write calls", () => {
  assert.doesNotMatch(source, /\bButton\b|\baction\s*=|useWrite|useMutation|writeResource|mutate|\.(post|put|patch|delete)\s*\(|\bfetch\s*\(/);
  assert.doesNotMatch(source, /phieu-nhap|API\.receipts|onClick|<form\b|<button\b/);
  const links = [...source.matchAll(/<Link\s+to=\{([^}]+\}[^}]*|[^}]+)\}/g)];
  assert.equal(links.length, 1);
  assert.match(links[0][0], /\/kho\/yeu-cau\//);
  assert.match(source, /useResource\(API\.shortages\)/);
});

// UC-27 D2: Trang dùng một query, QueryState từng Card và bố cục chỉ đọc theo checklist
test("page loads once and uses shared read only page layout and query states", () => {
  assert.equal(API.shortages, "/nhu_cau_bo_sung_linh_kien");
  assert.equal((source.match(/useResource\(/g) || []).length, 1);
  assert.equal((source.match(/<QueryState query=\{query\}>/g) || []).length, 2);
  assert.match(source, /return \(\s*<>\s*<PageHeader\s+title="Nhu cầu bổ sung linh kiện"\s+subtitle="[^"]+\."\s*\/>/);
  assert.deepEqual([...source.matchAll(/<Card title="([^"]+)">/g)].map((match) => match[1]), [
    "Tổng hợp theo linh kiện", "Yêu cầu chờ bổ sung",
  ]);
  assert.match(source, /query\.data\?\.data \|\| \{\}/);
  assert.doesNotMatch(source, /style=|\.css["']|<Field|Pagination|sort\(|\.reverse\(|tone="warning"|chưa có API/);
});

// UC-27 A1: Hai khối rỗng dùng câu chính xác, không dựng dòng giả
test("empty waiting list uses the approved table and request notices", () => {
  assert.deepEqual(shortageRows([]), []);
  assert.match(source, /yeu_cau: requests = \[\], tong_hop: summary = \[\]/);
  assert.match(source, /empty="Không có linh kiện cần bổ sung\."/);
  assert.match(source, /\{requests\.length \? \(?\s*requests\.map/);
  assert.match(source, /\)\)\s*\)?\s*: \(\s*<Notice>Không có yêu cầu chờ bổ sung linh kiện\.<\/Notice>/);
});

// UC-27 D3: da_du hiện Notice info thay bảng thiếu, không bỏ yêu cầu khỏi danh sách
test("replenished request shows waiting for recheck notice instead of its shortage table", () => {
  assert.match(source, /\{record\.da_du \? \(\s*<Notice>Đã đủ linh kiện, chờ nhân viên kiểm tra lại\.<\/Notice>\s*\) : \(\s*<DataTable/);
  assert.doesNotMatch(source, /requests\.filter|record\.da_du\s*&&|tone=/);
  assert.match(source, /<section key=\{record\.id\} className="stack">/);
});

// UC-27 D6: Menu QLK ngay sau yêu cầu, nhãn mới; route được bảo vệ, NV/Admin không truy cập
test("manager navigation and protected route expose the shortage page after production requests", () => {
  const group = navigationFor("quan_ly").find(({ title }) => title === "Sản xuất");
  const index = group.items.findIndex(([path]) => path === "/kho/yeu-cau");
  assert.ok(index >= 0);
  assert.deepEqual(group.items.slice(index, index + 2), [
    ["/kho/yeu-cau", "Yêu cầu sản xuất"],
    ["/kho/nhu-cau-bo-sung", "Nhu cầu bổ sung linh kiện"],
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
