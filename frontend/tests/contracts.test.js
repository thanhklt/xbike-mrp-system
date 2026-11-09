import assert from "node:assert/strict";
import { test } from "node:test";
import {
  cleanParams,
  normalizeResponse,
  auditParams,
  toApiError,
  versionHeaders,
} from "../src/lib/api/contract.js";
import { documentPermissions, homeFor, isAllowed } from "../src/features/auth/permissions.js";
import {
  changedProfileFields,
  formatAuditAction,
  formatAuditDetail,
} from "../src/features/dashboard/auditFormat.js";
import {
  dateTime,
  formatAuditTime,
  formatCoefficient,
  formatDate,
  initials,
  localDateTime,
  money,
} from "../src/lib/format.js";

test("query preserves zero and false while omitting absent filters", () => {
  assert.deepEqual(
    cleanParams({ price: 0, active: false, q: "", page: 1, missing: null, optional: undefined }),
    { price: 0, active: false, page: 1 },
  );
});
test("normalizes legacy pagination without treating one page length as total", () => {
  const response = normalizeResponse({
    data: {
      data: [{ id: 1 }],
      pagination: { page: 2, page_size: 20, total_items: 81, total_pages: 5 },
    },
    headers: {},
  });
  assert.equal(response.meta.total, 81);
  assert.equal(response.meta.page, 2);
});
test("preserves contract meta and strong ETag", () => {
  const result = normalizeResponse({
    data: { data: { id: 9 }, meta: { request_id: "request-9" } },
    headers: { etag: '"revision-2"' },
  });
  assert.equal(result.etag, '"revision-2"');
  assert.equal(result.meta.request_id, "request-9");
});
test("audit adapter translates only to parameters supported by legacy endpoint", () => {
  assert.deepEqual(auditParams({ page: 2, page_size: 20, q: "phiếu", sort: "-created_at" }), {
    page: 2,
    page_size: 20,
    search: "phiếu",
    sort_by: "created_at",
    sort_order: "desc",
  });
});
test("missing weak or wildcard version cannot authorize a write", () => {
  for (const version of [null, undefined, "", 'W/"stale"', "*"])
    assert.throws(
      () => versionHeaders(version),
      (error) => error.status === 428,
    );
  assert.deepEqual(versionHeaders('"reviewed-version"'), { "If-Match": '"reviewed-version"' });
});
test("412 errors instruct reloading and reconfirming", () => {
  const error = toApiError({ response: { status: 412, data: {} } });
  assert.match(error.message, /Tải lại/);
});
test("failed writes with unknown outcome are distinguished from failed reads", () => {
  assert.equal(toApiError({ config: { method: "post" } }).uncertain, true);
  assert.equal(toApiError({ config: { method: "get" } }).uncertain, false);
});
test("ticket link is only offered when backend confirms the ticket was committed", () => {
  assert.equal(
    toApiError({
      response: { status: 409, data: { error: { ticket_id: 4, ticket_da_luu: false } } },
    }).ticketId,
    null,
  );
  assert.equal(
    toApiError({
      response: { status: 409, data: { error: { ticket_id: 4, ticket_da_luu: true } } },
    }).ticketId,
    4,
  );
});
test("admin does not inherit warehouse privileges", () => {
  assert.equal(isAllowed("quan_tri_vien", ["quan_ly", "nhan_vien"]), false);
  assert.equal(
    documentPermissions("issue", "quan_tri_vien", { trang_thai: "cho_duyet" }, 1).approve,
    false,
  );
  assert.equal(homeFor("unknown"), "/403");
});
test("employees can neither create issue documents nor edit someone else's completion", () => {
  assert.equal(documentPermissions("issue", "nhan_vien", { trang_thai: "nhap" }, 3).create, false);
  assert.equal(
    documentPermissions("completion", "nhan_vien", { trang_thai: "nhap", nhan_vien_id: 4 }, 3).edit,
    false,
  );
});
test("posted documents stay immutable and rejected completion can return to draft", () => {
  assert.equal(documentPermissions("issue", "quan_ly", { trang_thai: "da_duyet" }, 2).edit, false);
  assert.equal(
    documentPermissions("completion", "nhan_vien", { trang_thai: "tu_choi", nhan_vien_id: 3 }, 3)
      .returnDraft,
    true,
  );
});
test("timestamps display in Vietnam time independently of browser or runner timezone", () => {
  assert.equal(localDateTime("2026-11-04T18:05:00Z"), "2026-11-05T01:05");
  assert.match(dateTime("2026-11-04T18:05:00Z"), /01:05/);
  assert.equal(money(null), "Chưa chốt");
  assert.match(money(0), /0/);
});

test("admin formatters format dates as dd/MM/yyyy, salary coefficients to 2 decimals, and audit timestamps", () => {
  assert.equal(formatDate("2026-01-05"), "05/01/2026");
  assert.equal(formatDate(null), "—");
  assert.equal(formatCoefficient("3.5"), "3.50");
  assert.equal(formatCoefficient("1.50"), "1.50");
  assert.equal(formatCoefficient(null), "—");
  assert.equal(initials("Lê Văn Thành"), "VT");
  assert.equal(formatAuditTime("2026-11-04T18:05:00Z"), "01:05 - 05/11/2026");
});

const historicalEmployee = {
  ma_nhan_vien: "NV-000003",
  ho_ten: "Tên lịch sử",
  ma_vai_tro: "nhan_vien",
  trang_thai: "hoat_dong",
  email: "old@example.test",
  so_dien_thoai: null,
};
const employeeAudit = {
  loai_doi_tuong: "nhan_vien",
  doi_tuong_id: 3,
  du_lieu_truoc: historicalEmployee,
  du_lieu_sau: historicalEmployee,
};

test("audit profile changes only list the six supported fields without exposing values", () => {
  const before = {
    ...historicalEmployee,
    ngay_sinh: "2000-01-01",
    ngay_vao_lam: "2026-01-01",
    he_so_luong: "1.00",
  };
  const after = {
    ...before,
    ho_ten: "Tên mới",
    ngay_sinh: "2001-01-01",
    so_dien_thoai: "0900000000",
    email: "new@example.test",
    ngay_vao_lam: "2026-02-01",
    he_so_luong: "2.00",
    ma_vai_tro: "quan_ly",
  };
  assert.deepEqual(changedProfileFields(before, after), [
    "họ tên", "ngày sinh", "số điện thoại", "email", "ngày vào làm", "hệ số lương",
  ]);
  assert.deepEqual(changedProfileFields(null, after), []);
  assert.deepEqual(changedProfileFields(before, null), []);
  assert.deepEqual(changedProfileFields({}, { email: "new@example.test" }), []);
  assert.deepEqual(changedProfileFields(before, { ...before, ma_vai_tro: "quan_ly" }), []);
  assert.deepEqual(changedProfileFields({ email: null }, { email: "a@example.test" }), ["email"]);
});

test("account audit sentences describe creation, profile update, password change and unlock", () => {
  const scenarios = [
    [
      { thao_tac: "tao", du_lieu_truoc: null },
      "Tạo tài khoản",
      'Tạo tài khoản NV-000003 (Tên lịch sử) với vai trò "Nhân viên".',
    ],
    [
      { thao_tac: "sua", du_lieu_sau: { ...historicalEmployee, email: "new@example.test", so_dien_thoai: "0900000000" } },
      "Cập nhật tài khoản",
      "Cập nhật thông tin tài khoản NV-000003 (Tên lịch sử) (số điện thoại, email).",
    ],
    [
      { thao_tac: "sua", du_lieu_truoc: null, du_lieu_sau: { da_doi_mat_khau: true } },
      "Đổi mật khẩu",
      "Đổi mật khẩu tài khoản NV-000003 (Tên hiện tại).",
    ],
    [
      { thao_tac: "sua", du_lieu_truoc: { ...historicalEmployee, trang_thai: "bi_khoa" }, ly_do: "Đã xác minh" },
      "Mở khóa tài khoản",
      "Mở khóa tài khoản NV-000003 (Tên lịch sử) do Đã xác minh.",
    ],
    [
      { thao_tac: "vo_hieu_hoa", ly_do: "không còn sử dụng" },
      "Vô hiệu hóa tài khoản",
      "Vô hiệu hóa tài khoản NV-000003 (Tên lịch sử) do không còn sử dụng.",
    ],
    [
      { thao_tac: "dang_nhap", du_lieu_truoc: null, du_lieu_sau: null },
      "Đăng nhập",
      "Đăng nhập thành công vào hệ thống.",
    ],
  ];
  for (const [changes, action, detail] of scenarios) {
    const entry = { ...employeeAudit, ...changes };
    assert.equal(formatAuditAction(entry), action);
    assert.equal(formatAuditDetail(entry, [{ id: 3, ma_nhan_vien: "NV-000003", ho_ten: "Tên hiện tại" }]), detail);
  }
});

test("role audit uses historical roles and employee identity instead of current directory values", () => {
  const entry = {
    ...employeeAudit,
    thao_tac: "cap_quyen",
    du_lieu_sau: { ...historicalEmployee, ma_vai_tro: "quan_ly" },
  };
  assert.equal(formatAuditAction(entry), "Phân quyền");
  assert.equal(
    formatAuditDetail(entry, [{ id: 3, ma_nhan_vien: "NV-999999", ho_ten: "Tên hiện tại" }]),
    'Gán vai trò "Quản lý kho" cho tài khoản NV-000003 (Tên lịch sử) (trước đó: "Nhân viên").',
  );
  assert.equal(formatAuditAction({ ...entry, thao_tac: "thu_hoi_quyen" }), "Thu hồi quyền");
  assert.equal(formatAuditDetail({ ...entry, thao_tac: "thu_hoi_quyen" }), 'Thu hồi vai trò "Nhân viên" của tài khoản NV-000003 (Tên lịch sử).');
});

test("audit falls back without inventing missing history and keeps warehouse event text", () => {
  const directory = [{ id: 3, ma_nhan_vien: "NV-000003", ho_ten: "Tên hiện tại" }];
  for (const thao_tac of ["tao", "sua", "cap_quyen", "thu_hoi_quyen", "vo_hieu_hoa"]) {
    assert.equal(formatAuditDetail({ ...employeeAudit, thao_tac, du_lieu_truoc: null, du_lieu_sau: null }, directory), "NV-000003 (Tên hiện tại)");
  }
  assert.equal(formatAuditDetail({ ...employeeAudit, thao_tac: "cap_quyen", du_lieu_sau: { ma_nhan_vien: "NV-000003", ma_vai_tro: "unknown" } }), "NV-000003");
  assert.equal(formatAuditDetail({ ...employeeAudit, thao_tac: "sua", du_lieu_sau: { ...historicalEmployee, ma_vai_tro: "quan_ly" }, ly_do: "kiểm tra" }), "NV-000003 (Tên lịch sử) do kiểm tra.");
  const warehouse = { loai_doi_tuong: "phieu_nhap", doi_tuong_id: 2, thao_tac: "hoan_tat", ly_do: "đã kiểm tra" };
  assert.equal(formatAuditAction(warehouse), "Hoàn tất phiếu nhập");
  assert.equal(formatAuditDetail(warehouse), "phiếu nhập #2 · đã kiểm tra");
});
