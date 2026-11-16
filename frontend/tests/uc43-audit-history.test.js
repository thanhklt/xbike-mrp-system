import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  AUDIT_ACTION_OPTIONS,
  AUDIT_OBJECT_OPTIONS,
  AUDIT_SORT_OPTIONS,
  auditFilters,
  auditActorLookup,
  auditDetailEntries,
  auditShortageRows,
} from "../src/features/reports/auditHistory.js";
import { dateFilters, dateRangeError } from "../src/components/filterFields.js";
import {
  auditActionLabel,
  auditObjectLabel,
  formatAuditAction,
} from "../src/features/dashboard/auditFormat.js";
import { auditParams } from "../src/lib/api/contract.js";
import { canAccessPath } from "../src/features/auth/permissions.js";
import { dateTime } from "../src/lib/format.js";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const page = source("../src/features/reports/AuditPage.jsx");
const history = source("../src/features/reports/auditHistory.js");
const schemas = source("../../backend/app/modules/audit/schemas.py");
const employees = [
  { id: 5, ma_nhan_vien: "NV-000005", ho_ten: "Nguyễn An" },
  { id: 8, ma_nhan_vien: "NV-000008", ho_ten: "Trần Bình" },
];
const actors = auditActorLookup(employees);
const record = {
  id: 42,
  created_at: "2026-11-15T02:30:00Z",
  nhan_vien_id: 5,
  loai_doi_tuong: "yeu_cau_san_xuat",
  doi_tuong_id: 9,
  thao_tac: "kiem_tra",
  trang_thai_truoc: "da_gui",
  trang_thai_sau: "cho_bo_sung_vat_tu",
  ly_do: "Thiếu khung",
  du_lieu_truoc: null,
  du_lieu_sau: {
    danh_sach_thieu: [
      {
        mat_hang_id: 1,
        ma_mat_hang: "MH-000001",
        ten_mat_hang: "Khung",
        don_vi_tinh: "cai",
        so_luong_can: 15,
        so_luong_con_dung: 5,
        so_luong_thieu: 10,
      },
    ],
  },
};

function literalValues(pattern) {
  const block = schemas.match(pattern)?.[1];
  assert.ok(block, "Expected a Literal declaration in the backend audit schema");
  return [...block.matchAll(/"([^"]+)"/g)].map((match) => match[1]);
}

// UC-43 AC-1: Lưu danh sách thiếu tại thời điểm chuyển trạng thái
test("shortages preserve the stored row including the historical shortage of ten", () => {
  const original = structuredClone(record);
  assert.deepEqual(auditShortageRows(record), [
    {
      mat_hang_id: 1,
      ma_mat_hang: "MH-000001",
      ten_mat_hang: "Khung",
      don_vi_tinh: "cai",
      so_luong_can: 15,
      so_luong_con_dung: 5,
      so_luong_thieu: 10,
      id: 0,
    },
  ]);
  assert.deepEqual(record, original);
  for (const value of [
    null,
    {},
    { danh_sach_thieu: null },
    { danh_sach_thieu: {} },
    { danh_sach_thieu: "10" },
  ]) {
    assert.equal(auditShortageRows({ du_lieu_sau: value }), null);
  }
  assert.equal(auditShortageRows({}), null);
  assert.deepEqual(auditShortageRows({ du_lieu_sau: { danh_sach_thieu: [] } }), []);
});

// UC-43 AC-2: Không sửa, xóa được lịch sử
test("audit presentation has no write or export controls and renders JSON as React text", () => {
  assert.doesNotMatch(
    page,
    /useWrite|mutateAsync|dangerouslySetInnerHTML|<button\b|<form\b|download=|writeResource/,
  );
  // Nút duy nhất được phép là "Tải lại" danh sách nhân viên (chỉ đọc, gọi refetch).
  const buttons = page.match(/<Button\b[\s\S]*?<\/Button>/g) || [];
  assert.equal(buttons.length, 1);
  assert.match(
    buttons[0],
    /onClick=\{\(\) => employees\.refetch\(\)\}[\s\S]*>\s*Tải lại\s*<\/Button>/,
  );
  assert.doesNotMatch(
    history,
    /useWrite|mutateAsync|writeResource|\bfetch\s*\(|\bmethod\s*:|\.(post|put|patch|delete)\s*\(/i,
  );
  assert.match(page, /<pre className="audit-json">\{JSON\.stringify\(value, null, 2\)\}<\/pre>/);
});

// UC-43 AC-3: Nhân viên bị chặn
test("employees cannot open either audit list or detail and permitted roles can", () => {
  for (const path of ["/admin/lich-su", "/admin/lich-su/5", "/kho/lich-su", "/kho/lich-su/5"]) {
    assert.equal(canAccessPath("nhan_vien", path), false, path);
  }
  assert.equal(canAccessPath("quan_tri_vien", "/admin/lich-su/5"), true);
  assert.equal(canAccessPath("quan_ly", "/kho/lich-su/5"), true);
  const routes = source("../src/routes/index.jsx");
  assert.deepEqual(
    [...routes.matchAll(/<Route path="([^"]*lich-su[^"]*)" element=\{<AuditPage \/>\}/g)].map(
      (match) => match[1],
    ),
    ["/admin/lich-su/:id?", "/kho/lich-su/:id?"],
  );
  assert.match(routes, /function RoleGate\(\)[\s\S]*?canAccessPath\(user\.ma_vai_tro, pathname\)/);
  for (const path of ["/admin/lich-su/:id?", "/kho/lich-su/:id?"]) {
    const group = routes
      .slice(0, routes.indexOf(`path="${path}"`))
      .split("<Route element={<RoleGate />}>")
      .at(-1);
    assert.doesNotMatch(group, /<\/Route>/);
  }
});

// UC-43 AC-4: Không hiện mật khẩu
test("password change details use redacted evidence without inventing credentials", () => {
  const redacted = {
    ...record,
    loai_doi_tuong: "nhan_vien",
    thao_tac: "doi_mat_khau",
    trang_thai_truoc: null,
    trang_thai_sau: null,
    ly_do: null,
    du_lieu_truoc: null,
    du_lieu_sau: { da_doi_mat_khau: true },
  };
  const original = structuredClone(redacted);
  const entries = auditDetailEntries(redacted, actors);
  assert.equal(entries.find(([label]) => label === "Thao tác")[1], "Đổi mật khẩu");
  assert.doesNotMatch(
    JSON.stringify(entries.filter(([label]) => label !== "Thao tác")),
    /mật khẩu|password/i,
  );
  assert.deepEqual(redacted, original);
});

// UC-43 AC-5: Ghi thao tác dữ liệu nền
test("BOM version filtering sends the approved object and action codes", () => {
  assert.deepEqual(
    AUDIT_OBJECT_OPTIONS.find(({ value }) => value === "cong_thuc"),
    { value: "cong_thuc", label: "BOM" },
  );
  assert.deepEqual(
    AUDIT_ACTION_OPTIONS.find(({ value }) => value === "tao_phien_ban"),
    { value: "tao_phien_ban", label: "Tạo phiên bản" },
  );
  assert.deepEqual(
    auditParams({
      loai_doi_tuong: "cong_thuc",
      thao_tac: "tao_phien_ban",
      page: 1,
      sort: "-created_at",
    }),
    {
      loai_doi_tuong: "cong_thuc",
      thao_tac: "tao_phien_ban",
      page: 1,
      sort_by: "created_at",
      sort_order: "desc",
    },
  );
});

// UC-43 AC-6: Lọc theo người và thời gian
test("actor select contains all employees by ID with code and name labels", () => {
  assert.deepEqual(
    auditFilters(employees).find(({ name }) => name === "nhan_vien_id"),
    {
      name: "nhan_vien_id",
      label: "Người thực hiện",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        { value: 5, label: "NV-000005 · Nguyễn An" },
        { value: 8, label: "NV-000008 · Trần Bình" },
      ],
    },
  );
  assert.equal(actors("5"), "NV-000005 · Nguyễn An");
  assert.equal(actors(8), "NV-000008 · Trần Bình");
  assert.equal(actors(99), "Nhân viên #99");
  assert.equal(auditActorLookup([])(5), "Nhân viên #5");
  assert.equal(auditActorLookup()(5), "Nhân viên #5");
  assert.equal(
    auditActorLookup([{ id: 5, ma_nhan_vien: "NV-000005", ho_ten: null }])(5),
    "NV-000005 · Chưa có họ tên",
  );
  assert.deepEqual(auditFilters().find(({ name }) => name === "nhan_vien_id").options, [
    { value: "", label: "Tất cả" },
  ]);
  assert.match(page, /useChoices\(API\.employees\)/);
  assert.match(page, /useMemo\(\(\) => auditActorLookup\(employeeRows\), \[employeeRows\]\)/);
  assert.match(page, /render: \(row\) => actorLabel\(row\.nhan_vien_id\)/);
  // Nhãn dùng chung với EmployeeSelect qua employeeLabel, không tự ghép chuỗi riêng.
  assert.match(history, /employeeLabel\(employee\)/);
  assert.doesNotMatch(history, /ma_nhan_vien/);
  assert.match(source("../src/components/ResourceFields.jsx"), /\{employeeLabel\(employee\)\}/);
});

// UC-43 AC-6: Lỗi tải danh sách nhân viên được báo, không lặng lẽ hạ cấp
test("employee list failure shows a warning instead of silently degrading", () => {
  assert.match(
    page,
    /\{employees\.isError && \(\s*<div className="stack">\s*<Notice tone="warning">\s*Không thể tải danh sách nhân viên\./,
  );
  assert.match(
    page,
    /onClick=\{\(\) => employees\.refetch\(\)\}\s*disabled=\{employees\.isFetching\}/,
  );
});

// UC-43 AC-10: Lọc kết hợp người, đối tượng, thao tác và ngày
test("all six filters use backend names and dates match the shared UI definitions", () => {
  const filters = auditFilters(employees);
  assert.deepEqual(
    filters.map(({ name }) => name),
    ["loai_doi_tuong", "doi_tuong_id", "nhan_vien_id", "thao_tac", "tu_ngay", "den_ngay", "sort"],
  );
  assert.deepEqual(
    filters.find(({ name }) => name === "doi_tuong_id"),
    { name: "doi_tuong_id", label: "ID đối tượng", type: "number", min: 1, step: 1 },
  );
  for (const name of ["loai_doi_tuong", "nhan_vien_id", "thao_tac"]) {
    const filter = filters.find((field) => field.name === name);
    assert.equal(filter.as, "select");
    assert.deepEqual(filter.options[0], { value: "", label: "Tất cả" });
  }
  // Một nguồn duy nhất: auditHistory dùng đúng các object dateFilters mà ResourceFields re-export.
  const dates = filters.filter(({ name }) => ["tu_ngay", "den_ngay"].includes(name));
  assert.equal(dates.length, 2);
  dates.forEach((filter, index) => assert.equal(filter, dateFilters[index]));
  const resourceFields = source("../src/components/ResourceFields.jsx");
  assert.match(resourceFields, /export \{ dateFilters \} from "\.\/filterFields\.js";/);
  assert.doesNotMatch(resourceFields, /export const dateFilters/);
  assert.doesNotMatch(history, /const dateFilters/);
  assert.match(page, /useMemo\(\(\) => auditFilters\(employeeRows\), \[employeeRows\]\)/);
  assert.match(page, /filters=\{filters\}/);
});

// UC-43 AC-11: Khoảng ngày sai bị chặn ngay trên form, không gửi request
test("date range is validated on the form before querying", () => {
  assert.equal(dateRangeError({}), null);
  assert.equal(dateRangeError(), null);
  assert.equal(dateRangeError({ tu_ngay: "2026-11-01" }), null);
  assert.equal(dateRangeError({ den_ngay: "2026-11-01" }), null);
  assert.equal(dateRangeError({ tu_ngay: "2026-11-10", den_ngay: "2026-11-10" }), null);
  assert.equal(dateRangeError({ tu_ngay: "2026-11-01", den_ngay: "2026-11-15" }), null);
  assert.equal(
    dateRangeError({ tu_ngay: "2026-11-20", den_ngay: "2026-11-10" }),
    "Từ ngày không được sau Đến ngày.",
  );
  assert.match(page, /validate=\{dateRangeError\}/);
  const collection = source("../src/components/Collection.jsx");
  assert.match(
    collection,
    /const message = validate\?\.\(draft\) \?\? null;\s*setFilterError\(message\);\s*if \(!message\) collection\.filter\(draft\);/,
  );
  assert.match(
    collection,
    /\{filterError && \(\s*<div className="notice notice-error" role="alert">/,
  );
});

// UC-43 AC-19: Màn chỉ đọc không có chế độ tạo mới
test("the /moi path redirects back to the list instead of opening an empty dialog", () => {
  assert.match(page, /if \(id === "moi"\) return <Navigate to=\{base\} replace \/>;/);
  assert.ok(page.indexOf('if (id === "moi")') > page.indexOf("useMemo(() => auditFilters"));
});

// UC-43 AC-10: Không có ô tìm kiếm tự do — backend chỉ tìm mã thô, dùng bộ lọc thay thế
test("audit list hides the free-text search box", () => {
  assert.match(page, /<Collection[\s\S]*?search=\{false\}[\s\S]*?\/>/);
});

// UC-43 AC-10: Lọc kết hợp người, đối tượng, thao tác và ngày
test("combined filters preserve pagination and search while removing blank fields", () => {
  assert.deepEqual(
    auditParams({
      nhan_vien_id: "5",
      loai_doi_tuong: "cong_thuc",
      doi_tuong_id: "9",
      thao_tac: "tao_phien_ban",
      tu_ngay: "2026-11-01",
      den_ngay: "2026-11-15",
      page: 3,
      page_size: 20,
      q: "BOM",
      sort: "-created_at",
    }),
    {
      nhan_vien_id: "5",
      loai_doi_tuong: "cong_thuc",
      doi_tuong_id: "9",
      thao_tac: "tao_phien_ban",
      tu_ngay: "2026-11-01",
      den_ngay: "2026-11-15",
      page: 3,
      page_size: 20,
      search: "BOM",
      sort_by: "created_at",
      sort_order: "desc",
    },
  );
  assert.deepEqual(
    auditParams({
      nhan_vien_id: "5",
      tu_ngay: "2026-11-01",
      den_ngay: "2026-11-15",
      loai_doi_tuong: "",
      doi_tuong_id: null,
      thao_tac: undefined,
      q: "",
      page: 2,
      sort: "-id",
    }),
    {
      nhan_vien_id: "5",
      tu_ngay: "2026-11-01",
      den_ngay: "2026-11-15",
      page: 2,
      sort_by: "id",
      sort_order: "desc",
    },
  );
});

// UC-43 AC-07: Hai actor đọc đúng phạm vi đã chốt
test("both roles use the same data columns and detail component", () => {
  assert.equal((page.match(/ma_vai_tro/g) || []).length, 1);
  assert.match(
    page,
    /const base = user\.ma_vai_tro === "quan_tri_vien" \? "\/admin\/lich-su" : "\/kho\/lich-su"/,
  );
  assert.doesNotMatch(page, /\bmanager\b|quan_ly|chưa được hỗ trợ|không được xem snapshot/);
  assert.doesNotMatch(history, /ma_vai_tro|quan_tri_vien|quan_ly/);
  assert.equal(auditDetailEntries.length, 1);
  assert.match(page, /<AuditDetail record=\{snapshot\.data\} actorLabel=\{actorLabel\}/);
});

// UC-43 AC-12: Phân trang và thứ tự xác định
test("all four sort choices map exactly to the backend sort whitelist", () => {
  assert.deepEqual(AUDIT_SORT_OPTIONS, [
    { value: "-created_at", label: "Mới nhất" },
    { value: "created_at", label: "Cũ nhất" },
    { value: "-id", label: "ID giảm dần" },
    { value: "id", label: "ID tăng dần" },
  ]);
  const allowed = literalValues(/sort_by:\s*Literal\[([^\]]+)\]/);
  assert.deepEqual(
    [
      ...new Set(AUDIT_SORT_OPTIONS.map(({ value }) => auditParams({ sort: value }).sort_by)),
    ].sort(),
    allowed.sort(),
  );
  for (const { value } of AUDIT_SORT_OPTIONS) {
    assert.deepEqual(auditParams({ sort: value, page: 2, page_size: 20 }), {
      page: 2,
      page_size: 20,
      sort_by: value.replace(/^-/, ""),
      sort_order: value.startsWith("-") ? "desc" : "asc",
    });
  }
  assert.match(page, /useCollection\(API\.audit, \{ sort: "-created_at" \}, auditParams\)/);
});

// UC-43 AC-13: Chi tiết không tồn tại và trường nullable
test("nullable evidence stays null without deriving status from snapshots", () => {
  const nullable = {
    ...record,
    trang_thai_truoc: null,
    trang_thai_sau: null,
    ly_do: null,
    du_lieu_truoc: null,
    du_lieu_sau: null,
  };
  const original = structuredClone(nullable);
  const details = Object.fromEntries(auditDetailEntries(nullable, actors));
  assert.equal(details["Trạng thái trước"], null);
  assert.equal(details["Trạng thái sau"], null);
  assert.equal(details["Lý do"], null);
  assert.deepEqual(nullable, original);
  assert.equal(nullable.du_lieu_truoc, null);
  assert.equal(nullable.du_lieu_sau, null);
  assert.equal(
    Object.fromEntries(
      auditDetailEntries({ ...nullable, du_lieu_sau: { trang_thai: "da_duyet" } }, actors),
    )["Trạng thái sau"],
    null,
  );
  assert.match(
    page,
    /value === null \|\| value === undefined \?\s*\(\s*<p className="empty-state">Không có dữ liệu<\/p>/,
  );
  assert.match(page, /<InfoGrid entries=\{entries\}/);
});

// UC-43 AC-19: Giao diện thực hiện đúng luồng đọc
test("action and object options exactly match backend literals and have translated labels", () => {
  assert.equal(AUDIT_ACTION_OPTIONS.length, 20);
  assert.equal(AUDIT_OBJECT_OPTIONS.length, 8);
  assert.deepEqual(
    AUDIT_ACTION_OPTIONS.map(({ value }) => value).sort(),
    literalValues(/ThaoTac = Literal\[([\s\S]*?)\]/).sort(),
  );
  assert.deepEqual(
    AUDIT_OBJECT_OPTIONS.map(({ value }) => value).sort(),
    literalValues(/AuditObject = Literal\[([\s\S]*?)\]/).sort(),
  );
  for (const { value, label } of [...AUDIT_ACTION_OPTIONS, ...AUDIT_OBJECT_OPTIONS]) {
    assert.equal(typeof label, "string");
    assert.notEqual(label, value);
    assert.ok(label.trim().length > 0);
  }
  for (const [code, label] of Object.entries({
    dang_nhap: "Đăng nhập",
    gui_lai: "Gửi lại",
    kiem_tra: "Kiểm tra",
    ngung: "Ngừng",
    dung_lai: "Dùng lại",
    tao_phien_ban: "Tạo phiên bản",
    dung_lai_phien_ban: "Dùng lại phiên bản",
    doi_mat_khau: "Đổi mật khẩu",
  })) {
    assert.equal(auditActionLabel(code), label);
  }
  assert.equal(auditObjectLabel("cong_thuc"), "BOM");
  assert.equal(auditActionLabel("unknown_action"), "unknown_action");
  assert.equal(auditObjectLabel("unknown_object"), "unknown_object");
  assert.equal(
    formatAuditAction({ thao_tac: "doi_mat_khau", loai_doi_tuong: "nhan_vien" }),
    auditActionLabel("doi_mat_khau"),
  );
});

// UC-43 AC-19: Giao diện thực hiện đúng luồng đọc — Main 1: Quản trị viên có lối vào lịch sử
test("administrator dashboard activity card links to the audit history", () => {
  const dashboard = source("../src/features/dashboard/DashboardPage.jsx");
  const admin = dashboard.slice(
    dashboard.indexOf("function AdminDashboard()"),
    dashboard.indexOf("function", dashboard.indexOf("function AdminDashboard()") + 1),
  );
  const card = admin.slice(admin.indexOf("<h2>Hoạt động gần đây</h2>"));
  assert.match(card, /<Link to="\/admin\/lich-su">Xem tất cả →<\/Link>/);
  assert.equal(canAccessPath("quan_tri_vien", "/admin/lich-su"), true);
});

// UC-43 AC-19: Giao diện thực hiện đúng luồng đọc
test("detail entries keep the approved order, labels, actor and original states", () => {
  assert.deepEqual(auditDetailEntries(record, actors), [
    ["Thời gian", dateTime(record.created_at)],
    ["Người thực hiện", "NV-000005 · Nguyễn An"],
    ["Đối tượng", "yêu cầu sản xuất #9"],
    ["Thao tác", "Kiểm tra"],
    ["Trạng thái trước", "da_gui", "status"],
    ["Trạng thái sau", "cho_bo_sung_vat_tu", "status"],
    ["Lý do", "Thiếu khung"],
  ]);
  // Badge chọn theo kiểu "status", không theo chữ nhãn hiển thị.
  assert.match(
    page,
    /kind === "status" && value !== null && value !== undefined \? <Badge status=\{value\} \/> : value/,
  );
  assert.doesNotMatch(page, /\["Trạng thái trước", "Trạng thái sau"\]\.includes/);
});

// UC-43 AC-19: Giao diện thực hiện đúng luồng đọc
test("details load by route ID in RecordPanel and retain the final open link column", () => {
  assert.match(page, /const \{ id \} = useParams\(\)/);
  assert.match(page, /useDetail\(API\.audit, id\)/);
  assert.match(
    page,
    /<RecordPanel id=\{id\} query=\{detail\} base=\{base\} title="Chi tiết lịch sử thao tác"/,
  );
  assert.match(
    page,
    /label: "Chi tiết",\s*render: \(row\) => <Link to=\{`\$\{base\}\/\$\{row\.id\}`\}>Mở →<\/Link>,\s*\},\s*\]\}/,
  );
  const layout = source("../src/layouts/MainLayout.jsx");
  assert.match(
    layout,
    /pathname\.startsWith\("\/admin\/lich-su\/"\)[\s\S]*?label: "Lịch sử thao tác", to: "\/admin\/lich-su"[\s\S]*?label: "Chi tiết lịch sử"/,
  );
  assert.match(layout, /pathname === "\/admin\/lich-su"/);
});

// UC-43 AC-1: Lưu danh sách thiếu tại thời điểm chuyển trạng thái
test("shortage table uses snapshot codes and numeric quantities before both JSON sections", () => {
  // Một chỗ quyết định có danh sách thiếu hay không: auditShortageRows trả null khi không lưu.
  assert.match(page, /const shortage = auditShortageRows\(record\);/);
  assert.match(page, /\{shortage && \(/);
  assert.match(page, /rows=\{shortage\}/);
  assert.doesNotMatch(page, /Array\.isArray/);
  assert.match(page, /<h3>Danh sách thiếu tại thời điểm thao tác<\/h3>/);
  assert.match(
    page,
    /\[row\.ma_mat_hang, row\.ten_mat_hang\]\.filter\(Boolean\)\.join\(" · "\) \|\|\s*`#\$\{row\.mat_hang_id\}`/,
  );
  assert.match(page, /key: "don_vi_tinh", label: "Đơn vị"/);
  for (const [key, label] of [
    ["so_luong_can", "Cần"],
    ["so_luong_con_dung", "Còn dùng"],
    ["so_luong_thieu", "Thiếu"],
  ]) {
    assert.ok(page.includes(`key: "${key}", label: "${label}", numeric: true`));
  }
  assert.ok(
    page.indexOf("Danh sách thiếu tại thời điểm thao tác") <
      page.indexOf('["Dữ liệu trước", record.du_lieu_truoc]'),
  );
  assert.ok(
    page.indexOf('["Dữ liệu trước", record.du_lieu_truoc]') <
      page.indexOf('["Dữ liệu sau", record.du_lieu_sau]'),
  );
  assert.doesNotMatch(page, /useCatalog|API\.catalog|API\.materials/);
});
