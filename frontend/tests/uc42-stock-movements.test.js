import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { canAccessPath } from "../src/features/auth/permissions.js";
import {
  MOVEMENT_TYPES,
  SOURCE_LABELS,
  movementParams,
  signedQuantity,
} from "../src/features/inventory/stockMovements.js";
import { API } from "../src/lib/api/endpoints.js";
import { navigationFor } from "../src/layouts/navigation.js";

const source = readFileSync(
  new URL("../src/features/inventory/MovementsPage.jsx", import.meta.url),
  "utf8",
);

// UC-42 AC-1: Số lượng có dấu và nhãn chứng từ nguồn đúng
test("movement quantities preserve signs and source labels identify all headers", () => {
  assert.equal(signedQuantity(5), "+5");
  assert.equal(signedQuantity(-3), "−3");
  assert.equal(signedQuantity(0), "0");
  assert.equal(signedQuantity(-0), "0");
  assert.deepEqual(SOURCE_LABELS, {
    phieu_nhap: "Phiếu nhập",
    phieu_xuat: "Phiếu xuất",
    chung_tu_hoan_thanh_sx: "Chứng từ hoàn thành SX",
  });
});

// UC-42 AC-1: Bảng có đủ dữ liệu mỗi lần biến động và không link sang phiếu
test("movement table renders seven columns with source headers and ledger actors", () => {
  for (const [key, label] of [
    ["posted_at", "Thời điểm"],
    ["mat_hang", "Mặt hàng"],
    ["loai_giao_dich", "Loại nghiệp vụ"],
    ["so_luong_bien_dong", "Số lượng thay đổi"],
    ["so_luong_ton_sau", "Tồn sau"],
    ["chung_tu", "Chứng từ gốc"],
    ["nhan_vien", "Nhân viên"],
  ])
    assert.match(source, new RegExp(`key: "${key}",\\s*label: "${label}"`));
  assert.match(source, /dateTime\(row\.posted_at\)/);
  assert.match(source, /row\.mat_hang\.ma_mat_hang.*row\.mat_hang\.ten_mat_hang/);
  assert.match(source, /row\.nhan_vien\.ma_nhan_vien.*row\.nhan_vien\.ho_ten/);
  assert.match(source, /row\.chung_tu\.ma/);
  assert.match(source, /SOURCE_LABELS\[row\.chung_tu\.loai\]/);
  assert.match(
    source,
    /key: "so_luong_bien_dong"[^}]*numeric: true[^}]*signedQuantity\(row\.so_luong_bien_dong\)/,
  );
  assert.match(
    source,
    /key: "so_luong_ton_sau"[^}]*numeric: true[^}]*number\(row\.so_luong_ton_sau\)/,
  );
  assert.doesNotMatch(source, /<Link|href=|to=|writeResource|useWrite/);
});

// UC-42 AC-3: Đúng bốn mã v4 và nhãn nhập kho theo phiếu nhập
test("movement types use the four approved codes and receipt filter", () => {
  assert.deepEqual(MOVEMENT_TYPES, [
    { value: "nhap_linh_kien", label: "Nhập kho" },
    { value: "xuat_linh_kien", label: "Xuất linh kiện" },
    { value: "nhap_san_pham_san_xuat", label: "Nhập thành phẩm sản xuất" },
    { value: "xuat_thanh_pham", label: "Xuất thành phẩm" },
  ]);
  assert.deepEqual(movementParams({ loai_giao_dich: "nhap_linh_kien" }), {
    loai_giao_dich: "nhap_linh_kien",
  });
  assert.match(source, /\.\.\.MOVEMENT_TYPES/);
});

// UC-42 R1: Chỉ gửi các bộ lọc được duyệt và tham số phân trang
test("movement params convert IDs and pagination while dropping empty and unknown filters", () => {
  const params = {
    page: 2,
    page_size: 100,
    mat_hang_id: "19",
    nhan_vien_id: "7",
    loai_giao_dich: "xuat_linh_kien",
    q: "khung",
    sort: "id",
    sort_by: "id",
    other: "bad",
  };
  assert.deepEqual(movementParams(params), {
    page: 2,
    page_size: 100,
    mat_hang_id: 19,
    nhan_vien_id: 7,
    loai_giao_dich: "xuat_linh_kien",
  });
  assert.equal(params.mat_hang_id, "19");
  assert.deepEqual(
    movementParams({
      mat_hang_id: "",
      nhan_vien_id: null,
      loai_giao_dich: "",
      tu_ngay: "",
      den_ngay: undefined,
      page: "1",
      page_size: "20",
    }),
    { page: 1, page_size: 20 },
  );
  assert.deepEqual(movementParams({}), {});
  assert.match(source, /useChoices\(API\.items\)/);
  assert.match(source, /useChoices\(API\.employees\)/);
  assert.match(source, /search=\{false\}/);
  assert.match(source, /useCollection\(API\.stockMovements, \{\}, movementParams\)/);
});

// UC-42 R3: Gửi nguyên ngày địa phương, giao diện ghi rõ giờ Việt Nam
test("movement date filters preserve local calendar days without UTC conversion", () => {
  assert.deepEqual(movementParams({ tu_ngay: "2026-01-31", den_ngay: "2026-01-31" }), {
    tu_ngay: "2026-01-31",
    den_ngay: "2026-01-31",
  });
  assert.deepEqual(movementParams({ tu_ngay: "2026-01-31" }), { tu_ngay: "2026-01-31" });
  assert.deepEqual(movementParams({ den_ngay: "2026-01-31" }), { den_ngay: "2026-01-31" });
  assert.match(source, /name: "tu_ngay", label: "Từ ngày", type: "date"/);
  assert.match(source, /name: "den_ngay", label: "Đến ngày", type: "date"/);
  assert.match(source, /Khoảng thời gian tính theo giờ Việt Nam\./);
});

// UC-42 R2: Trang đọc API báo cáo đã ghi sổ và menu mới, bỏ khung vô hiệu
test("movement page uses the reporting endpoint and the approved navigation label", () => {
  assert.equal(API.stockMovements, "/bao_cao/bien_dong_kho");
  assert.match(source, /title="Lịch sử biến động kho"/);
  assert.match(source, /Mỗi lần tồn kho thay đổi do chứng từ đã ghi nhận vào kho\./);
  assert.doesNotMatch(source, /<Notice|chưa đồng bộ|Lọc giao dịch|inventory\/movements|disabled/);
  assert.deepEqual(
    navigationFor("quan_ly")
      .flatMap((group) => group.items)
      .filter(([path]) => path === "/kho/giao-dich"),
    [["/kho/giao-dich", "Lịch sử biến động kho"]],
  );
});

// UC-42 A1: Dùng Collection và trạng thái tải/lỗi sẵn có, giữ thông báo trống mặc định
test("movement page uses collection empty state and handles choice query errors", () => {
  assert.match(source, /<Collection/);
  assert.match(source, /collection=\{collection\}/);
  assert.match(source, /<QueryState query=\{items\}>/);
  assert.match(source, /<QueryState query=\{employees\}>/);
  assert.doesNotMatch(source, /empty=|<DataTable/);
});

// UC-42 A2: Chỉ quản lý kho được mở đường dẫn lịch sử
test("only managers can access stock movement history", () => {
  assert.equal(canAccessPath("quan_ly", "/kho/giao-dich"), true);
  assert.equal(canAccessPath("nhan_vien", "/kho/giao-dich"), false);
  assert.equal(canAccessPath("quan_tri_vien", "/kho/giao-dich"), false);
});
