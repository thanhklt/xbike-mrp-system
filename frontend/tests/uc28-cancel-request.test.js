import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { dateTime, employeeName, STATUS_LABELS } from "../src/lib/format.js";
import {
  CANCEL_HOLD_COLUMNS,
  CANCEL_ISSUE_COLUMNS,
  cancelConfirmEntries,
  canCancelRequest,
  canCheckRequest,
  canEditRequest,
  requestDetailEntries,
} from "../src/features/production/requestForm.js";

const source = readFileSync(new URL("../src/features/production/RequestsPage.jsx", import.meta.url), "utf8");
const feedback = readFileSync(new URL("../src/components/FeedbackProvider.jsx", import.meta.url), "utf8");
const record = { id: 1, ma_yeu_cau_san_xuat: "YCSX-202611-000001", trang_thai: "dang_thuc_hien" };
const preview = {
  duoc_huy: true, ly_do_khong_huy: null,
  hang_tra: [
    { id: 11, mat_hang_id: 2, ma_mat_hang: "MH-000002", ten_mat_hang: "Khung", don_vi_tinh: "cái", loai_giu: "linh_kien", so_luong: 10 },
    { id: 12, mat_hang_id: 5, ma_mat_hang: "MH-000005", ten_mat_hang: "Xe", don_vi_tinh: "xe", loai_giu: "thanh_pham_co_san", so_luong: 3 },
    { id: 13, mat_hang_id: 5, ma_mat_hang: "MH-000005", ten_mat_hang: "Xe", don_vi_tinh: "xe", loai_giu: "thanh_pham_san_xuat", so_luong: 2 },
  ],
  phieu_xuat: [
    { id: 1, ma_phieu_xuat: "PX-202611-000001", loai_phieu: "xuat_linh_kien", trang_thai: "cho_duyet", xu_ly: "tu_choi" },
    { id: 2, ma_phieu_xuat: "PX-202611-000002", loai_phieu: "xuat_thanh_pham", trang_thai: "nhap", xu_ly: "bo" },
  ],
};

// Execute the real handler, replacing its JSX fragment only; verify table wiring separately.
function handler({ result = preview, readError, writeError } = {}) {
  const start = source.indexOf("  function cancel(");
  const end = source.indexOf("  // UC-24", start + 1);
  assert.ok(start > 0 && end > start);
  const body = source.slice(start, end).replace(/content: <>[\s\S]*?<\/>,/, "content: null,");
  const state = { reads: [], writes: [], deletes: [], notices: [], errors: [], pending: [], options: null, navigations: [] };
  const ports = {
    record, snapshot: { etag: '"reviewed"' }, API: { requests: "/yeu_cau_san_xuat" }, cancelConfirmEntries,
    readResource: async (path) => {
      state.reads.push(path);
      if (readError) throw readError;
      return { data: result };
    },
    cancelMutation: { mutateAsync: async (input) => {
      state.writes.push(input);
      if (writeError) throw writeError;
      return { data: { ...record, trang_thai: "da_huy" } };
    } },
    mutation: { mutateAsync: async (input) => { state.deletes.push(input); } },
    confirm: (options) => { state.options = options; },
    notify: (message) => state.notices.push(message),
    setCancelError: (error) => state.errors.push(error),
    setCancelPending: (pending) => state.pending.push(pending),
    navigate: (path) => state.navigations.push(path), base: "/kho/yeu-cau",
  };
  const open = new Function(...Object.keys(ports), `return (${body.trim()});`)(...Object.values(ports));
  return { open, state, ports };
}

// UC-28 D4: Nội dung hộp giữ mã/tên/ĐVT/lượng và dịch đủ loại giữ, loại phiếu, xử lý
test("cancel confirmation describes every hold and affected issue without mutating preview", () => {
  const before = structuredClone(preview);
  const entries = cancelConfirmEntries(preview);
  assert.deepEqual(entries.hang_tra, [
    { ...preview.hang_tra[0], loai_giu: "Linh kiện", so_luong: "10" },
    { ...preview.hang_tra[1], loai_giu: "Thành phẩm có sẵn", so_luong: "3" },
    { ...preview.hang_tra[2], loai_giu: "Thành phẩm sản xuất", so_luong: "2" },
  ]);
  assert.deepEqual(entries.phieu_xuat, [
    { ...preview.phieu_xuat[0], loai_phieu: "Xuất linh kiện", trang_thai: STATUS_LABELS.cho_duyet, xu_ly: "Từ chối: Yêu cầu đã hủy" },
    { ...preview.phieu_xuat[1], loai_phieu: "Xuất thành phẩm", trang_thai: STATUS_LABELS.nhap, xu_ly: "Bỏ phiếu nháp" },
  ]);
  assert.deepEqual(preview, before);
  assert.deepEqual(cancelConfirmEntries({ hang_tra: [], phieu_xuat: [] }), { hang_tra: [], phieu_xuat: [] });
});

// UC-28 D4: Đúng cột, numeric, tiêu đề và empty theo checklist giao diện
test("cancel tables use approved headings columns and empty messages", () => {
  assert.deepEqual(CANCEL_HOLD_COLUMNS, [
    { key: "ma_mat_hang", label: "Mã" }, { key: "ten_mat_hang", label: "Tên" },
    { key: "don_vi_tinh", label: "Đơn vị tính" }, { key: "loai_giu", label: "Loại giữ" },
    { key: "so_luong", label: "Số lượng", numeric: true },
  ]);
  assert.deepEqual(CANCEL_ISSUE_COLUMNS, [
    { key: "ma_phieu_xuat", label: "Mã phiếu" }, { key: "loai_phieu", label: "Loại phiếu" },
    { key: "trang_thai", label: "Trạng thái" }, { key: "xu_ly", label: "Xử lý" },
  ]);
  assert.match(source, /<h3>Hàng sẽ trả lại<\/h3>\s*<DataTable rows=\{entries.hang_tra\} columns=\{CANCEL_HOLD_COLUMNS\} empty="Không có hàng đang giữ\." \/>/);
  assert.match(source, /<h3>Phiếu xuất bị ảnh hưởng<\/h3>\s*<DataTable rows=\{entries.phieu_xuat\} columns=\{CANCEL_ISSUE_COLUMNS\} empty="Không có phiếu xuất chưa duyệt\." \/>/);
});

// UC-28 A3: Đóng xác nhận chỉ GET, không POST hoặc thông báo thành công
test("dismissing cancellation only reads preview and leaves all writes untouched", async () => {
  const { open, state } = handler();
  await open();
  assert.deepEqual(state.reads, ["/yeu_cau_san_xuat/1/huy"]);
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.deletes, []);
  assert.deepEqual(state.notices, []);
  assert.equal(state.options.title, "Hủy yêu cầu sản xuất");
  assert.equal(state.options.description, record.ma_yeu_cau_san_xuat);
  assert.equal(state.options.impact, "Tồn thực tế không đổi.");
  assert.equal(state.options.reason, true);
  assert.equal(state.options.danger, true);
  assert.equal(typeof state.options.onConfirm, "function");
  assert.equal("onClose" in state.options, false);
  assert.equal("onCancel" in state.options, false);
  assert.deepEqual(state.pending, [true, false]);
});

// UC-28 A2: Phiếu đã duyệt báo lý do bằng ErrorNotice, không mở hộp
test("ineligible preview shows exact reason without confirming or writing", async () => {
  const reason = "Yêu cầu đã có phiếu xuất được duyệt, không thể hủy.";
  const { open, state } = handler({ result: { ...preview, duoc_huy: false, ly_do_khong_huy: reason } });
  await open();
  assert.equal(state.options, null);
  assert.equal(state.errors[0], null);
  assert.equal(state.errors.length, 2);
  assert.equal(state.errors[1].message, reason);
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.notices, []);
  assert.deepEqual(state.pending, [true, false]);
  assert.match(source, /<ErrorNotice error=\{cancelError\} \/>/);
});

// UC-28 D4: Lỗi tải xem trước báo riêng, không mở hộp hoặc ghi
test("preview failure uses separate error state and restores button availability", async () => {
  const failure = new Error("Không tải được xem trước");
  const { open, state } = handler({ readError: failure });
  await open();
  assert.deepEqual(state.errors, [null, failure]);
  assert.equal(state.options, null);
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.pending, [true, false]);
  assert.match(source, /<Button variant="secondary" disabled=\{cancelPending \|\| cancelMutation.isPending\} onClick=\{\(\) => cancel\(\)\}>\s*Hủy yêu cầu…/);
});

// UC-28 A4: Xác nhận POST lý do và ETag chi tiết đã xem, thông báo thành công
test("confirmation posts reason with captured detail ETag through its own mutation", async () => {
  const { open, state, ports } = handler();
  await open();
  ports.snapshot.etag = '"changed"';
  await state.options.onConfirm("Khách không cần nữa");
  assert.deepEqual(state.writes, [{ path: "/yeu_cau_san_xuat/1/huy", body: { ly_do: "Khách không cần nữa" }, etag: '"reviewed"' }]);
  assert.deepEqual(state.deletes, []);
  assert.deepEqual(state.notices, ["Đã hủy yêu cầu."]);
  assert.match(source, /const cancelMutation = useWrite\(\)/);
  assert.doesNotMatch(source, /<ErrorNotice error=\{cancelMutation.error\}/);
});

// UC-28 A4: POST lỗi giữ lỗi trong hộp, không thông báo thành công
test("confirmation failure propagates to dialog without a success notice", async () => {
  const failure = new Error("Dữ liệu đã thay đổi");
  const { open, state } = handler({ writeError: failure });
  await open();
  await assert.rejects(state.options.onConfirm("Hủy"), (error) => error === failure);
  assert.equal(state.writes.length, 1);
  assert.deepEqual(state.errors, [null]);
  assert.deepEqual(state.notices, []);
});

// UC-28 AC-5: Ô lý do bắt buộc và khóa xác nhận khi toàn khoảng trắng
test("shared confirmation enforces a nonblank cancellation reason", async () => {
  const { open, state } = handler();
  await open();
  assert.equal(state.options.reason, true);
  assert.match(feedback, /disabled=\{busy \|\| Boolean\(options.reason && !reasonOptional && !reason.trim\(\)\)\}/);
  assert.match(feedback, /const reasonOptional = options.reasonOptional \?\? false/);
  assert.match(feedback, /label=\{options.reasonLabel \|\| "Lý do"\}\s*required=\{!reasonOptional\}/);
  assert.match(feedback, /await options.onConfirm\(reason.trim\(\)\)/);
});

// UC-28 A5: Nháp chỉ xóa; QLK mới hủy ba trạng thái đã gửi
test("cancel action is unavailable to employees draft complete and cancelled requests", () => {
  for (const state of ["nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"]) {
    const row = { ...record, trang_thai: state };
    assert.equal(canCancelRequest(row, true), ["da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien"].includes(state));
    assert.equal(canCancelRequest(row, false), false);
  }
  assert.equal(canCancelRequest(null, true), false);
});

// UC-28 A5: Nhánh xóa nháp giữ nguyên, không GET xem trước hủy
test("draft deletion retains versioned DELETE confirmation and collection navigation", async () => {
  const { open, state } = handler();
  await open(true);
  assert.deepEqual(state.reads, []);
  assert.equal(state.options.title, "Xóa yêu cầu nháp");
  assert.equal(state.options.reason, false);
  await state.options.onConfirm("");
  assert.deepEqual(state.deletes, [{ path: "/yeu_cau_san_xuat/1", method: "delete", body: {}, etag: '"reviewed"' }]);
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.navigations, ["/kho/yeu-cau"]);
});

// UC-28 D5: Chi tiết đã hủy có thời điểm, người, lý do; không còn thao tác
test("cancelled detail shows all three metadata lines and has no edit check or cancel actions", () => {
  const row = { ...record, trang_thai: "da_huy", huy_at: "2026-11-16T08:00:00Z", nguoi_huy_id: 10, ly_do_huy: "Không còn nhu cầu" };
  const employees = [{ id: 10, ma_nhan_vien: "NV-000010", ho_ten: "Quản lý kho" }];
  assert.deepEqual(requestDetailEntries(row, [], employees).slice(-3), [
    ["Hủy lúc", dateTime(row.huy_at)], ["Người hủy", employeeName(employees, 10)], ["Lý do hủy", row.ly_do_huy],
  ]);
  assert.equal(requestDetailEntries(record, [], employees).some(([label]) => ["Hủy lúc", "Người hủy", "Lý do hủy"].includes(label)), false);
  assert.equal(canEditRequest(row, true), false);
  assert.equal(canCancelRequest(row, true), false);
  assert.equal(canCheckRequest(row, false, 20), false);
});
