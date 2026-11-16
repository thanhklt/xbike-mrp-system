import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  REQUEST_TYPES,
  REQUEST_TYPE_LABELS,
  initialRequestValues,
  missingRequestFields,
  requestCreateBody,
  sendConfirmEntries,
} from "../src/features/production/requestForm.js";

const source = readFileSync(
  new URL("../src/features/production/RequestsPage.jsx", import.meta.url),
  "utf8",
);
const resourceFields = readFileSync(
  new URL("../src/components/ResourceFields.jsx", import.meta.url),
  "utf8",
);
const values = {
  loai_yeu_cau: "dap_ung",
  mat_hang_id: "1",
  so_luong: "10",
  han_hoan_thanh: "2026-12-01",
  nhan_vien_duoc_giao_id: "20",
};
const items = [
  {
    id: 1,
    ten_mat_hang: "Mountain Pro",
    don_vi_tinh: "xe",
    loai_mat_hang: "thanh_pham",
    is_active: true,
  },
  {
    id: 2,
    ten_mat_hang: "Bánh xe",
    don_vi_tinh: "cai",
    loai_mat_hang: "linh_kien",
    is_active: true,
  },
  {
    id: 3,
    ten_mat_hang: "Kids Fun",
    don_vi_tinh: "xe",
    loai_mat_hang: "thanh_pham",
    is_active: false,
  },
];
const employees = [{ id: 20, ho_ten: "Nhân viên A" }];

// UC-23 AC-2: Loại mặc định Đáp ứng yêu cầu, đủ hai lựa chọn và không có lựa chọn rỗng
test("request type defaults to dap_ung and presents exactly the approved choices", () => {
  assert.deepEqual(initialRequestValues(), {
    loai_yeu_cau: "dap_ung",
    mat_hang_id: "",
    so_luong: "",
    han_hoan_thanh: "",
    nhan_vien_duoc_giao_id: "",
  });
  assert.deepEqual(REQUEST_TYPES, [
    { value: "dap_ung", label: "Đáp ứng yêu cầu" },
    { value: "cho_kho", label: "Sản xuất cho kho" },
  ]);
  assert.deepEqual(REQUEST_TYPE_LABELS, {
    dap_ung: "Đáp ứng yêu cầu",
    cho_kho: "Sản xuất cho kho",
  });
  assert.match(
    source,
    /<Field as="select" label="Loại yêu cầu" required \{\.\.\.field\("loai_yeu_cau"\)\}>\s*\{REQUEST_TYPES\.map/,
  );
  assert.doesNotMatch(source, /<option[^>]*value=""/);
});

// UC-23 AC-2: Thiếu hạn hoặc nhân viên được báo đúng trường; đủ thông tin không báo thiếu
test("required fields report missing deadline and assignee precisely", () => {
  assert.deepEqual(missingRequestFields(values), []);
  for (const empty of ["", "  ", null, undefined]) {
    assert.deepEqual(missingRequestFields({ ...values, han_hoan_thanh: empty }), [
      "han_hoan_thanh",
    ]);
    assert.deepEqual(missingRequestFields({ ...values, nhan_vien_duoc_giao_id: empty }), [
      "nhan_vien_duoc_giao_id",
    ]);
  }
  assert.deepEqual(missingRequestFields({}), [
    "loai_yeu_cau",
    "mat_hang_id",
    "so_luong",
    "han_hoan_thanh",
    "nhan_vien_duoc_giao_id",
  ]);
});

// UC-23 AC-5: Form chỉ truyền loại thành phẩm tới bộ chọn mặt hàng
test("product selector is required and restricts choices to finished products", () => {
  const selector = source.match(/<ItemSelect\b[\s\S]*?\/>/)?.[0];
  assert.ok(selector);
  assert.match(selector, /label="Thành phẩm"/);
  assert.match(selector, /\brequired\b/);
  assert.match(selector, /types=\{\["thanh_pham"\]\}/);
  assert.match(selector, /\{\.\.\.field\("mat_hang_id"\)\}/);
  assert.match(resourceFields, /types\.includes\(item\.loai_mat_hang\)/);
});

// UC-23 AC-6: Bộ chọn dùng danh sách mặt hàng hoạt động, không cho tạo bằng Kids Fun đã ngừng
test("new product selection retains the shared active item filter", () => {
  assert.match(source, /items=\{items\}/);
  assert.match(source, /initialRequestValues\(record\)/);
  assert.equal(initialRequestValues().mat_hang_id, "");
  const selector = resourceFields.slice(
    resourceFields.indexOf("export function ItemSelect"),
    resourceFields.indexOf("export function EmployeeSelect"),
  );
  assert.match(
    selector,
    /item\.is_active && \(!types \|\| types\.includes\(item\.loai_mat_hang\)\)/,
  );
  assert.match(selector, /item\.id === Number\(value\)/);
});

// UC-23 AC-7: Nhân viên bắt buộc; bộ chọn dùng chung lọc tài khoản hoạt động đúng vai trò
test("assignee selector is required and retains active employee filtering", () => {
  const selector = source.match(/<EmployeeSelect\b[\s\S]*?\/>/)?.[0];
  assert.ok(selector);
  assert.match(selector, /\brequired\b/);
  assert.match(selector, /label="Nhân viên được giao"/);
  assert.match(selector, /\{\.\.\.field\("nhan_vien_duoc_giao_id"\)\}/);
  assert.match(
    resourceFields,
    /employee\.ma_vai_tro === "nhan_vien" && employee\.trang_thai === "hoat_dong"/,
  );
});

// UC-23 AC-1: R6 hộp xác nhận đủ sáu thông tin (câu không đổi tồn nằm ở impact, xem test gửi)
test("send confirmation contains all six R6 values", () => {
  assert.deepEqual(sendConfirmEntries(values, items, employees), [
    ["Loại yêu cầu", "Đáp ứng yêu cầu"],
    ["Thành phẩm", "Mountain Pro"],
    ["Số lượng cần", "10"],
    ["Đơn vị tính", "xe"],
    ["Hạn hoàn thành", "01/12/2026"],
    ["Nhân viên được giao", "Nhân viên A"],
  ]);
});

// UC-23 AC-10: Body giữ loại cho_kho, ba xe, hạn và nhân viên; không gửi trường thừa
test("stock request payload preserves its type and all required fields", () => {
  assert.deepEqual(
    requestCreateBody({ ...values, loai_yeu_cau: "cho_kho", so_luong: "3", bom_id: 999 }),
    {
      loai_yeu_cau: "cho_kho",
      mat_hang_id: 1,
      so_luong: 3,
      han_hoan_thanh: "2026-12-01",
      nhan_vien_duoc_giao_id: 20,
    },
  );
  assert.equal(
    sendConfirmEntries({ ...values, loai_yeu_cau: "cho_kho" }, items, employees)[0][1],
    "Sản xuất cho kho",
  );
});

// UC-23 AC-1: Tạo dùng phản hồi data/etag; điều hướng chi tiết Nháp trước khi mở xác nhận
test("creation navigates to the saved draft before opening send confirmation", () => {
  const submit = source.slice(
    source.indexOf("  function submit("),
    source.indexOf("  function send("),
  );
  assert.match(submit, /method: record \? "patch" : "post"/);
  assert.match(submit, /body: requestCreateBody\(values\)/);
  assert.match(
    submit,
    /navigate\(`\$\{base\}\/\$\{result\.data\.id\}`\);\s*if \(!record\) send\(result\.data, result\.etag\);/,
  );
  assert.match(
    source,
    /<Button type="submit" disabled=\{busy\}>\s*\{record \? "Lưu nháp" : "Tạo"\}/,
  );
});

// UC-23 AC-3: Đóng hộp không gửi/xóa; yêu cầu đã ở trang chi tiết Nháp (A2)
test("confirmation leaves the saved draft in place when dismissed", () => {
  const send = source.slice(
    source.indexOf("  function send("),
    source.indexOf("  function cancel("),
  );
  assert.match(send, /confirm\(\{\s*title: "Gửi yêu cầu sản xuất"/);
  assert.match(send, /description: request\.ma_yeu_cau_san_xuat/);
  assert.match(
    send,
    /content: <InfoGrid entries=\{sendConfirmEntries\(request, items, employees\.data \|\| \[\]\)\} \/>/,
  );
  assert.doesNotMatch(send, /onClose|navigate\(|delete/);
  assert.ok(send.indexOf("onConfirm: async") < send.indexOf("mutation.mutateAsync"));
});

// UC-23 AC-8: A3 lỗi gửi truyền ra hộp xác nhận; thành công báo đã gửi, body rỗng và đúng ETag
test("send uses the creation etag and propagates failures to confirmation", () => {
  const send = source.slice(
    source.indexOf("  function send("),
    source.indexOf("  function cancel("),
  );
  assert.match(
    send,
    /onConfirm: async \(\) => \{\s*await mutation\.mutateAsync\(\{\s*path: `\$\{API\.requests\}\/\$\{request\.id\}\/gui`,\s*body: \{\},\s*etag,/,
  );
  assert.match(send, /impact: "Chưa thay đổi tồn kho và phần đang giữ\."/);
  assert.match(send, /notify\("Đã gửi yêu cầu cho nhân viên\."\)/);
  assert.doesNotMatch(send, /catch|finally|navigate\(/);
});

// UC-23 AC-1: D4 hạn bắt buộc kiểu date nhưng không giới hạn ngày quá khứ
test("deadline input is required without a minimum and past dates survive payload", () => {
  const field = source.match(/<Field label="Hạn hoàn thành"[^>]*\/>/)?.[0];
  assert.ok(field);
  assert.match(field, /type="date" required/);
  assert.match(field, /field\("han_hoan_thanh"\)/);
  assert.doesNotMatch(field, /\bmin=/);
  assert.equal(
    requestCreateBody({ ...values, han_hoan_thanh: "2000-01-01" }).han_hoan_thanh,
    "2000-01-01",
  );
});

// UC-23 AC-1: D1 gỡ tính kế hoạch, token, preview và cây lệnh; danh sách có hai cột mới
test("request page removes planning and displays request type and deadline columns", () => {
  assert.doesNotMatch(
    source,
    /tinh_ke_hoach|ke_hoach_token|\/ke_hoach|OrderTree|preview|Tính kế hoạch/,
  );
  assert.match(
    source,
    /key: "loai_yeu_cau",\s*label: "Loại",\s*render: \(row\) => REQUEST_TYPE_LABELS\[row\.loai_yeu_cau\]/,
  );
  assert.match(
    source,
    /key: "han_hoan_thanh",\s*label: "Hạn hoàn thành",\s*render: \(row\) => formatDate\(row\.han_hoan_thanh\)/,
  );
  assert.doesNotMatch(source, /Yêu cầu thành phẩm|yêu cầu thành phẩm/);
});
