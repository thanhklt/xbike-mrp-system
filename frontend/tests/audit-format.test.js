import test from "node:test";
import assert from "node:assert/strict";
import { formatAuditAction, formatAuditDetail } from "../src/features/dashboard/auditFormat.js";
import { auditParams } from "../src/lib/api/contract.js";
import { ROLE_LABELS } from "../src/lib/format.js";

const base = { loai_doi_tuong: "nhan_vien", doi_tuong_id: 5 };

test("password reset uses snapshot identity or current employee with the contract wording", () => {
  const entry = { ...base, thao_tac: "sua", du_lieu_sau: { da_dat_lai_mat_khau: true } };
  assert.equal(formatAuditAction(entry), "Đặt lại mật khẩu");
  assert.equal(
    formatAuditDetail(entry, [{ id: 5, ma_nhan_vien: "NV-000005", ho_ten: "Tên hiện tại" }]),
    "Đặt lại mật khẩu tài khoản NV-000005 (Tên hiện tại).",
  );
  assert.equal(
    formatAuditDetail({
      ...entry,
      du_lieu_sau: { ...entry.du_lieu_sau, ma_nhan_vien: "NV-000005", ho_ten: "Tên lịch sử" },
    }),
    "Đặt lại mật khẩu tài khoản NV-000005 (Tên lịch sử).",
  );
  assert.equal(formatAuditDetail(entry), "Đặt lại mật khẩu tài khoản #5.");
});

test("account actions without a reason or name omit the optional text", () => {
  const entry = { ...base, thao_tac: "vo_hieu_hoa", du_lieu_sau: { ma_nhan_vien: "NV-000005" } };
  assert.equal(formatAuditDetail(entry), "Vô hiệu hóa tài khoản NV-000005.");
  assert.equal(
    formatAuditDetail({
      ...entry,
      thao_tac: "sua",
      du_lieu_truoc: { trang_thai: "bi_khoa" },
      du_lieu_sau: { ...entry.du_lieu_sau, trang_thai: "hoat_dong" },
    }),
    "Mở khóa tài khoản NV-000005.",
  );
});

test("creation reuses the shared labels, including admin and missing roles", () => {
  for (const code of ["quan_tri_vien", "quan_ly"]) {
    assert.equal(
      formatAuditDetail({
        ...base,
        thao_tac: "tao",
        du_lieu_sau: { ma_nhan_vien: "NV-000005", ma_vai_tro: code },
      }),
      `Tạo tài khoản NV-000005 với vai trò "${ROLE_LABELS[code]}".`,
    );
  }
  assert.equal(
    formatAuditDetail({ ...base, thao_tac: "tao", du_lieu_sau: { ma_nhan_vien: "NV-000005" } }),
    "Tạo tài khoản NV-000005.",
  );
});

test("role grant without a known previous role omits the previous-role clause", () => {
  const entry = {
    ...base,
    thao_tac: "cap_quyen",
    du_lieu_sau: { ma_nhan_vien: "NV-000005", ma_vai_tro: "quan_ly" },
  };
  assert.equal(formatAuditDetail(entry), 'Gán vai trò "Quản lý kho" cho tài khoản NV-000005.');
  for (const code of ["toString", "__proto__"]) {
    assert.equal(
      formatAuditDetail({ ...entry, du_lieu_sau: { ...entry.du_lieu_sau, ma_vai_tro: code } }),
      "NV-000005",
    );
  }
});

const codes = {
  mat_hang: ["ma_mat_hang", "mặt hàng"],
  nha_cung_cap: ["ma_ncc", "nhà cung cấp"],
  phieu_nhap: ["ma_phieu_nhap", "phiếu nhập"],
  phieu_xuat: ["ma_phieu_xuat", "phiếu xuất"],
  yeu_cau_san_xuat: ["ma_yeu_cau_san_xuat", "yêu cầu sản xuất"],
  lenh_san_xuat: ["ma_lenh_san_xuat", "lệnh sản xuất"],
  chung_tu_hoan_thanh_san_xuat: ["ma_phieu", "chứng từ hoàn thành SX"],
  phieu_dieu_chinh_kho: ["ma_phieu", "phiếu điều chỉnh kho"],
  ticket_loi_dieu_chinh: ["ma_ticket", "ticket lỗi điều chỉnh"],
};
for (const [kind, [field, noun]] of Object.entries(codes)) {
  test(`${kind} keeps the warehouse wording and uses only its business code`, () => {
    const entry = {
      ...base,
      loai_doi_tuong: kind,
      thao_tac: "tao",
      du_lieu_sau: { [field]: "CODE-01", email: "secret" },
      ly_do: "lý do",
    };
    assert.equal(formatAuditDetail(entry), `${noun} CODE-01 · lý do`);
    assert.equal(formatAuditDetail({ ...entry, ly_do: null }), `${noun} CODE-01`);
    assert.equal(
      formatAuditDetail({ ...entry, du_lieu_truoc: entry.du_lieu_sau, du_lieu_sau: {} }),
      `${noun} CODE-01 · lý do`,
    );
  });
}

test("BOM has no business code and role events use the historical role name", () => {
  assert.equal(
    formatAuditDetail({ ...base, loai_doi_tuong: "cong_thuc", thao_tac: "tao" }),
    "BOM #5",
  );
  assert.equal(
    formatAuditDetail({
      ...base,
      loai_doi_tuong: "vai_tro",
      thao_tac: "tao",
      du_lieu_sau: { ten_vai_tro: "Quản lý kho" },
    }),
    'Tạo vai trò "Quản lý kho".',
  );
  assert.equal(
    formatAuditDetail({ ...base, loai_doi_tuong: "vai_tro", thao_tac: "tao" }),
    "Tạo vai trò #5.",
  );
});

test("auditParams preserves the exclusion filter for ADM-01", () => {
  assert.deepEqual(
    auditParams({ page: 1, page_size: 5, sort: "-created_at", bo_thao_tac: "thu_hoi_quyen" }),
    {
      page: 1,
      page_size: 5,
      bo_thao_tac: "thu_hoi_quyen",
      sort_by: "created_at",
      sort_order: "desc",
    },
  );
});
