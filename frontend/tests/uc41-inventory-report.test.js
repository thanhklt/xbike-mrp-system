import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canAccessPath } from "../src/features/auth/permissions.js";
import {
  defaultReportForm,
  periodLabel,
  REPORT_ITEM_TYPES,
  reportQuery,
} from "../src/features/reports/inventoryReport.js";
import { API } from "../src/lib/api/endpoints.js";

const source = readFileSync(
  new URL("../src/features/reports/ReportsPage.jsx", import.meta.url),
  "utf8",
);
const navigation = readFileSync(new URL("../src/layouts/navigation.js", import.meta.url), "utf8");

// UC-41 R1: Chọn kỳ tháng/quý/năm và gửi đúng tham số kỳ
test("report query sends only the selected period fields", () => {
  const form = defaultReportForm(new Date(2026, 4, 9));
  assert.deepEqual(form, {
    ky: "thang",
    nam: 2026,
    thang: 5,
    quy: 2,
    mat_hang_id: "",
    loai_mat_hang: "",
  });
  assert.deepEqual(reportQuery(form), { ky: "thang", nam: 2026, thang: 5 });
  assert.deepEqual(reportQuery({ ...form, ky: "quy" }), { ky: "quy", nam: 2026, quy: 2 });
  assert.deepEqual(reportQuery({ ...form, ky: "nam" }), { ky: "nam", nam: 2026 });
  assert.deepEqual(reportQuery({ ...form, nam: "2027", thang: "12" }), {
    ky: "thang",
    nam: 2027,
    thang: 12,
  });
  assert.equal(periodLabel(form), "Tháng 5/2026");
  assert.equal(periodLabel({ ...form, ky: "quy" }), "Quý 2/2026");
  assert.equal(periodLabel({ ...form, ky: "nam" }), "Năm 2026");
});

// UC-41 R2: Lọc theo mặt hàng và loại, chỉ gửi khi đã chọn
test("report filters use exactly the two v4 item types", () => {
  assert.deepEqual(REPORT_ITEM_TYPES, [
    { value: "linh_kien", label: "Linh kiện" },
    { value: "thanh_pham", label: "Thành phẩm" },
  ]);
  const form = defaultReportForm(new Date(2026, 0, 1));
  assert.deepEqual(reportQuery({ ...form, mat_hang_id: "19", loai_mat_hang: "thanh_pham" }), {
    ky: "thang",
    nam: 2026,
    thang: 1,
    mat_hang_id: 19,
    loai_mat_hang: "thanh_pham",
  });
  assert.deepEqual(reportQuery(form), { ky: "thang", nam: 2026, thang: 1 });
  assert.match(source, /useChoices\(API\.items\)/);
  assert.doesNotMatch(source, /itemTypeOptions|\.is_active/);
});

// UC-41 AC-1: Bảng có đủ số dư và phát sinh, không có điều chỉnh
test("report renders all eight columns with numeric formatting and the real endpoint", () => {
  assert.equal(API.inventoryReport, "/bao_cao/nhap_xuat_ton");
  for (const key of [
    "ma_mat_hang",
    "ten_mat_hang",
    "loai_mat_hang",
    "don_vi_tinh",
    "ton_dau_ky",
    "nhap_trong_ky",
    "xuat_trong_ky",
    "ton_cuoi_ky",
  ]) {
    assert.match(source, new RegExp(`key: "${key}"`));
  }
  for (const key of ["ton_dau_ky", "nhap_trong_ky", "xuat_trong_ky", "ton_cuoi_ky"]) {
    assert.match(
      source,
      new RegExp(`key: "${key}"[^}]*numeric: true[^}]*number\\(row\\.${key}\\)`),
    );
  }
  assert.doesNotMatch(source, /dieu_chinh_trong_ky|Điều chỉnh|chưa có API|<Notice/);
  assert.match(source, /id: row\.mat_hang_id/);
  assert.match(navigation, /\["\/kho\/thong-ke", "Báo cáo nhập – xuất – tồn"\]/);
});

// UC-41 A1: Không có mặt hàng thỏa bộ lọc
test("empty report and request errors use the specified states", () => {
  assert.match(source, /empty="Không có mặt hàng thỏa bộ lọc\."/);
  assert.match(source, /<QueryState query=\{query\}>/);
  assert.match(source, /<QueryState query=\{choices\}>/);
});

// UC-41 R1: Chỉ bấm xem mới áp dụng kỳ và bộ lọc
test("draft filters are separate from submitted query and period title", () => {
  assert.match(source, /\[form, setForm\] = useState\(defaultReportForm\)/);
  assert.match(source, /\[submitted, setSubmitted\] = useState\(null\)/);
  assert.match(
    source,
    /useResource\(API\.inventoryReport, submitted \?\? \{\}, submitted !== null\)/,
  );
  assert.match(source, /<form[^>]*onSubmit=\{submit\}/);
  assert.match(source, /const params = reportQuery\(form\)/);
  assert.match(source, /setSubmitted\(params\)/);
  assert.match(source, /periodLabel\(report \?\? submitted\)/);
  const change = source.slice(
    source.indexOf("function change("),
    source.indexOf("function submit("),
  );
  assert.doesNotMatch(change, /setSubmitted|refetch/);
});

// UC-41 A3: Người không có quyền gõ đường dẫn bị chặn
test("only managers can access the report path", () => {
  assert.equal(canAccessPath("quan_ly", "/kho/thong-ke"), true);
  assert.equal(canAccessPath("nhan_vien", "/kho/thong-ke"), false);
  assert.equal(canAccessPath("quan_tri_vien", "/kho/thong-ke"), false);
});
