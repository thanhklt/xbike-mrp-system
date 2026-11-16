import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  REQUEST_SORT_OPTIONS,
  requestDetailEntries,
  requestListFilters,
} from "../src/features/production/requestForm.js";
import { cleanParams } from "../src/lib/api/contract.js";
import { STATUS_LABELS } from "../src/lib/format.js";

const source = readFileSync(
  new URL("../src/features/production/RequestsPage.jsx", import.meta.url),
  "utf8",
);
const page = source.slice(source.indexOf("export function RequestsPage()"), source.indexOf("function RequestEditor("));
const columns = page.slice(page.indexOf("columns={["), page.indexOf("<RecordPanel"));

// UC-25 A3: Cả hai vai trò có Tất cả và đúng hai loại yêu cầu đã chốt
test("request type filter offers all export and stock requests for both roles", () => {
  for (const manager of [true, false]) {
    assert.deepEqual(requestListFilters(manager).find(({ name }) => name === "loai_yeu_cau"), {
      name: "loai_yeu_cau",
      label: "Loại yêu cầu",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        { value: "xuat_giao", label: "Sản xuất để xuất giao" },
        { value: "nhap_kho", label: "Sản xuất nhập kho" },
      ],
    });
  }
});

// UC-25 A1: Cả hai vai trò có đủ năm lựa chọn sort, gồm hạn gần nhất/xa nhất
test("sort filter offers default deadline and creation ordering for both roles", () => {
  const options = [
    { value: "", label: "Mặc định" },
    { value: "han_hoan_thanh", label: "Hạn hoàn thành gần nhất" },
    { value: "-han_hoan_thanh", label: "Hạn hoàn thành xa nhất" },
    { value: "-created_at", label: "Mới nhất trước" },
    { value: "created_at", label: "Cũ nhất trước" },
  ];
  assert.deepEqual(REQUEST_SORT_OPTIONS, options);
  for (const manager of [true, false]) {
    assert.deepEqual(requestListFilters(manager).find(({ name }) => name === "sort"), {
      name: "sort", label: "Sắp xếp", as: "select", options,
    });
  }
});

// UC-25 AC-3: Trang không gửi sort mặc định; chọn Mặc định loại sort khỏi query
test("request list leaves default ordering to backend and omits blank sort", () => {
  assert.match(page, /const collection = useCollection\(API\.requests, \{\}\);/);
  assert.equal((page.match(/useCollection\(/g) || []).length, 1);
  assert.match(page, /filters=\{requestListFilters\(manager\)\}/);
  assert.deepEqual(cleanParams({ page: 1, page_size: 20, sort: "", loai_yeu_cau: "" }), {
    page: 1, page_size: 20,
  });
  assert.deepEqual(cleanParams({ sort: "han_hoan_thanh", loai_yeu_cau: "nhap_kho" }), {
    sort: "han_hoan_thanh", loai_yeu_cau: "nhap_kho",
  });
});

// UC-25 AC-5: NV bỏ Nháp, QLK đủ sáu trạng thái; nhãn dùng STATUS_LABELS
test("status filter hides drafts only for employees and keeps approved labels", () => {
  const states = ["nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"];
  for (const manager of [true, false]) {
    assert.deepEqual(requestListFilters(manager)[0], {
      name: "trang_thai",
      label: "Trạng thái",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        ...(manager ? states : states.slice(1)).map((value) => ({ value, label: STATUS_LABELS[value] })),
      ],
    });
  }
});

// UC-25 A3: Bộ lọc đúng thứ tự trạng thái, loại, sort, ngày; giữ cấu hình Collection
test("collection filters preserve the approved order and existing date fields", () => {
  for (const manager of [true, false]) {
    const filters = requestListFilters(manager);
    assert.deepEqual(filters.map(({ name }) => name), [
      "trang_thai", "loai_yeu_cau", "sort", "tu_ngay", "den_ngay",
    ]);
    assert.deepEqual(filters.slice(3), [
      { name: "tu_ngay", label: "Từ ngày", type: "date" },
      { name: "den_ngay", label: "Đến ngày", type: "date" },
    ]);
    assert.deepEqual(filters.slice(0, 3).map(({ as }) => as), ["select", "select", "select"]);
  }
  assert.match(page, /<Collection\s+collection=\{collection\}\s+filters=\{requestListFilters\(manager\)\}/);
});

// UC-25 AC-1: D5 tiêu đề/phụ đề theo vai trò; cột Số lượng cần dạng số và đủ loại/hạn/trạng thái
test("request page uses approved role headings and ordered list columns", () => {
  assert.match(page, /<PageHeader\s+title=\{manager \? "Yêu cầu sản xuất" : "Yêu cầu được giao"\}/);
  assert.match(page, /subtitle=\{manager\s*\? "Lập yêu cầu sản xuất và gửi cho nhân viên được giao\."\s*:\s*"Yêu cầu sản xuất được giao cho bạn, từ khi đã gửi\."\}/);
  assert.deepEqual([...columns.matchAll(/key: "([^"]+)"/g)].map(([, key]) => key), [
    "ma_yeu_cau_san_xuat", "mat_hang_id", "loai_yeu_cau", "han_hoan_thanh", "so_luong", "trang_thai", "action",
  ]);
  assert.deepEqual([...columns.matchAll(/label: "([^"]+)"/g)].map(([, label]) => label), [
    "Mã yêu cầu", "Thành phẩm", "Loại yêu cầu", "Hạn hoàn thành", "Số lượng cần", "Trạng thái", "Thao tác",
  ]);
  assert.match(columns, /\{ key: "so_luong", label: "Số lượng cần", numeric: true \}/);
  assert.match(columns, /render: \(row\) => REQUEST_TYPE_LABELS\[row\.loai_yeu_cau\]/);
  assert.match(columns, /render: \(row\) => formatDate\(row\.han_hoan_thanh\)/);
  assert.match(columns, /render: \(row\) => <Badge status=\{row\.trang_thai\} \/>/);
});

// UC-25 D6: Bỏ cột/dòng tiến độ xuất ở danh sách và chi tiết, giữ thông tin yêu cầu
test("list and detail remove export progress while retaining request information", () => {
  assert.doesNotMatch(page, /Đã xuất|Còn phải xuất|so_luong_da_xuat|so_luong_con_phai_xuat/);
  const entries = requestDetailEntries({
    loai_yeu_cau: "nhap_kho", mat_hang_id: 1, so_luong: 10,
    han_hoan_thanh: "2026-12-01", nhan_vien_duoc_giao_id: 20, nhan_vien_id: 10,
    created_at: null, gui_at: null, completed_at: null,
    so_luong_da_xuat: 7, so_luong_con_phai_xuat: 3,
  }, [{ id: 1, ten_mat_hang: "Mountain Pro", don_vi_tinh: "xe" }], [
    { id: 20, ho_ten: "Nhân viên A" }, { id: 10, ho_ten: "Quản lý kho" },
  ]);
  assert.deepEqual(entries, [
    ["Loại yêu cầu", "Sản xuất nhập kho"],
    ["Thành phẩm", "Mountain Pro"],
    ["Số lượng cần", "10"],
    ["Đơn vị tính", "xe"],
    ["Hạn hoàn thành", "01/12/2026"],
    ["Nhân viên được giao", "Nhân viên A"],
    ["Người lập", "Quản lý kho"],
    ["Tạo lúc", "—"],
    ["Gửi lúc", "—"],
    ["Hoàn thành lúc", "—"],
  ]);
});
