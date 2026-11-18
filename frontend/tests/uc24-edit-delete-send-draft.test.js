import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { dateTime } from "../src/lib/format.js";
import {
  canCancelRequest,
  canEditRequest,
  initialRequestValues,
  missingRequestFields,
  requestCreateBody,
  requestDetailEntries,
} from "../src/features/production/requestForm.js";

const source = readFileSync(
  new URL("../src/features/production/RequestsPage.jsx", import.meta.url),
  "utf8",
);
const feedback = readFileSync(
  new URL("../src/components/FeedbackProvider.jsx", import.meta.url),
  "utf8",
);
const record = {
  id: 1,
  ma_yeu_cau_san_xuat: "YCSX-202611-000001",
  trang_thai: "nhap",
  loai_yeu_cau: "nhap_kho",
  mat_hang_id: 1,
  so_luong: 15,
  han_hoan_thanh: "2026-12-01",
  nhan_vien_duoc_giao_id: 20,
  nhan_vien_id: 10,
  created_at: "2026-11-16T07:00:00Z",
  gui_at: null,
  completed_at: null,
};
const items = [{ id: 1, ten_mat_hang: "Mountain Pro", don_vi_tinh: "xe" }];
const employees = [{ id: 20, ho_ten: "Nhân viên A" }, { id: 10, ho_ten: "Quản lý kho", ma_nhan_vien: "NV-000010" }];

// UC-24 AC-1: Form sửa điền đủ năm giá trị hiện tại, body đúng kiểu và không có null
test("edit prefill and payload preserve all five current draft values", () => {
  const values = initialRequestValues(record);
  assert.deepEqual(values, {
    loai_yeu_cau: "nhap_kho",
    mat_hang_id: "1",
    so_luong: "15",
    han_hoan_thanh: "2026-12-01",
    nhan_vien_duoc_giao_id: "20",
  });
  assert.deepEqual(requestCreateBody({ ...values, so_luong: "25" }), {
    loai_yeu_cau: "nhap_kho",
    mat_hang_id: 1,
    so_luong: 25,
    han_hoan_thanh: "2026-12-01",
    nhan_vien_duoc_giao_id: 20,
  });
  assert.deepEqual(missingRequestFields(values), []);
  assert.equal(Object.values(requestCreateBody(values)).includes(null), false);
});

// UC-24 AC-2: Năm trường dùng chung form tạo đều required, thiếu từng trường được phát hiện
test("edit form requires every field and retains active product and employee selectors", () => {
  for (const name of Object.keys(initialRequestValues(record))) {
    const control = [...source.matchAll(/<(?:Field|ItemSelect|EmployeeSelect)\b[\s\S]*?(?:\/>|>)/g)]
      .map(([tag]) => tag)
      .find((tag) => tag.includes(`field("${name}")`));
    assert.ok(control, name);
    assert.match(control, /\brequired\b/, name);
    for (const empty of ["", "  ", null, undefined]) {
      assert.deepEqual(missingRequestFields({ ...initialRequestValues(record), [name]: empty }), [name]);
    }
  }
  assert.match(source, /types=\{\["thanh_pham"\]\}/);
  assert.match(source, /<EmployeeSelect\s+employees=\{employees\.data\}/);
  const deadline = source.match(/<Field\s+label="Hạn hoàn thành"[^>]*\/>/)[0];
  assert.doesNotMatch(deadline, /\bmin=/);
  assert.match(source, /const showForm = manager && \(!record \|\| \(editable && editing\)\)/);
  assert.match(source, /\{showForm && \([\s\S]*?<form className="stack" onSubmit=\{submit\}>/);
});

// UC-24 AC-1: Chi tiết chỉ đọc đủ nhãn và giá trị, tên NV/người lập và các dòng tiến độ (D3)
test("read only detail contains all approved information with employee names", () => {
  assert.deepEqual(requestDetailEntries(record, items, employees), [
    ["Loại yêu cầu", "Sản xuất nhập kho"],
    ["Thành phẩm", "Mountain Pro"],
    ["Số lượng cần", "15"],
    ["Đơn vị tính", "xe"],
    ["Hạn hoàn thành", "01/12/2026"],
    ["Nhân viên được giao", "Nhân viên A"],
    ["Người lập", "Quản lý kho — NV-000010"],
    ["Tạo lúc", dateTime(record.created_at)],
    ["Gửi lúc", "—"],
    ["Hoàn thành lúc", "—"],
  ]);
  const sent = { ...record, trang_thai: "da_gui", gui_at: "2026-11-17T08:00:00Z" };
  const entries = Object.fromEntries(requestDetailEntries(sent, items, []));
  assert.equal(entries["Nhân viên được giao"], "Nhân viên #20");
  assert.equal(entries["Người lập"], "Chưa có họ tên");
  assert.equal(entries["Gửi lúc"], dateTime(sent.gui_at));
  assert.match(source, /<InfoGrid entries=\{requestDetailEntries\(record, items, employees\.data \|\| \[\]\)\} \/>/);
  assert.equal((source.match(/<InfoGrid entries=\{requestDetailEntries/g) || []).length, 1);
});

// UC-24 AC-7: Chỉ QLK với Nháp được Sửa/Xóa/Gửi; sau gửi và các trạng thái khác chỉ đọc
test("draft actions are restricted to managers and drafts", () => {
  assert.equal(canEditRequest(record, true), true);
  for (const status of ["nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"]) {
    assert.equal(canEditRequest({ ...record, trang_thai: status }, true), status === "nhap");
    assert.equal(canEditRequest({ ...record, trang_thai: status }, false), false);
  }
  assert.equal(canEditRequest(null, true), false);
  assert.match(source, /const editable = canEditRequest\(record, manager\)/);
  assert.match(source, /\{editable && !editing && \(\s*<div className="actions actions-end">/);
  const actions = source.slice(source.indexOf("{editable && !editing"), source.indexOf("{canCancelRequest"));
  assert.match(actions, /<Button variant="secondary" onClick=\{edit\}>\s*Sửa/);
  assert.match(actions, /<Button variant="secondary" onClick=\{\(\) => cancel\(true\)\}>\s*Xóa nháp/);
  assert.ok(actions.indexOf("Sửa") < actions.indexOf("Xóa nháp"));
  assert.ok(actions.indexOf("Xóa nháp") < actions.indexOf("Gửi yêu cầu cho nhân viên"));
});

// UC-24 AC-3: Nháp không có nút Hủy; các trạng thái hủy được giữ quyền hiện tại (D2)
test("cancel request is hidden for drafts completed requests and canceled requests", () => {
  for (const status of ["nhap", "hoan_thanh", "da_huy"]) {
    assert.equal(canCancelRequest({ ...record, trang_thai: status }, true), false);
  }
  for (const status of ["da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien"]) {
    assert.equal(canCancelRequest({ ...record, trang_thai: status }, true), true);
    assert.equal(canCancelRequest({ ...record, trang_thai: status }, false), false);
  }
  assert.equal(canCancelRequest(null, true), false);
  assert.match(source, /\{canCancelRequest\(record, manager\) && \([\s\S]*?Hủy yêu cầu…/);
});

// UC-24 A1: Bấm Sửa mới mở form điền sẵn; Bỏ sửa phục hồi thông tin và về chế độ xem
test("edit and discard use local state and restore the saved draft values", () => {
  assert.match(source, /const \[editing, setEditing\] = useState\(false\)/);
  const edit = source.slice(source.indexOf("  function edit("), source.indexOf("  function discardEdit("));
  assert.match(edit, /setValues\(initialRequestValues\(record\)\);\s*setEditing\(true\)/);
  const discard = source.slice(source.indexOf("  function discardEdit("), source.indexOf("  if (!record && !manager)"));
  assert.match(discard, /setValues\(initialRequestValues\(record\)\);\s*setEditing\(false\)/);
  assert.doesNotMatch(edit + discard, /save\(|mutateAsync|confirm\(|navigate\(/);
  assert.match(source, /\{record \? \(\s*<div className="actions actions-end">\s*<Button type="button" variant="secondary" onClick=\{discardEdit\} disabled=\{busy\}>\s*Bỏ sửa/);
});

// UC-24 AC-1: Lưu nháp gọi save ngay với đủ body/ETag, thành công mới thoát sửa, không xác nhận (D4)
test("save draft writes immediately and returns to viewing only on success", () => {
  const submit = source.slice(source.indexOf("  function submit("), source.indexOf("  function send("));
  assert.match(submit, /save\(\s*\{[\s\S]*?method: record \? "patch" : "post"/);
  assert.match(submit, /body: requestCreateBody\(values\),\s*etag: snapshot\?\.etag,\s*versioned: Boolean\(record\)/);
  assert.match(submit, /\(result\) => \{\s*if \(record\) setEditing\(false\)/);
  assert.match(submit, /if \(!record\) send\(result\.data, result\.etag\)/);
  assert.doesNotMatch(submit, /confirm\(/);
  assert.equal((submit.match(/setEditing\(false\)/g) || []).length, 1);
  // Lỗi lưu chỉ hiện khi form đang mở; Bỏ sửa không để lại lỗi cũ ở chế độ xem.
  assert.ok(source.includes("<ErrorNotice error={(showForm && error) || mutation.error} />"));
  assert.match(source, /<Button type="submit" disabled=\{busy\}>\s*\{record \? "Lưu nháp" : "Tạo"\}/);
});

// UC-24 AC-3: Xóa nháp giữ hộp danger và chỉ điều hướng về danh sách sau khi API thành công
test("delete draft confirms a versioned delete then navigates to the collection", () => {
  const cancel = source.slice(source.indexOf("  function cancel("), source.indexOf("  function edit("));
  assert.match(cancel, /confirm\(\{/);
  assert.match(cancel, /danger: true/);
  assert.match(cancel, /onConfirm: async \(reason\) => \{\s*await mutation\.mutateAsync\(/);
  assert.match(cancel, /method: remove \? "delete" : "post"/);
  assert.match(cancel, /etag: snapshot\.etag/);
  assert.match(cancel, /if \(remove\) navigate\(base\)/);
  assert.ok(cancel.indexOf("await mutation.mutateAsync") < cancel.indexOf("navigate(base)"));
});

// UC-24 AC-4: Gửi lại dùng record/ETag đang xem và hộp xác nhận UC-23, không lưu ngầm
test("resend uses the viewed draft and its etag through the existing confirmation", () => {
  assert.match(source, /onClick=\{\(\) => send\(record, snapshot\.etag\)\}/);
  const send = source.slice(source.indexOf("  function send("), source.indexOf("  function cancel("));
  assert.match(send, /content: <InfoGrid entries=\{sendConfirmEntries\(request, items, employees\.data \|\| \[\]\)\} \/>/);
  assert.match(send, /impact: "Chưa thay đổi tồn kho và phần đang giữ\."/);
  assert.match(send, /onConfirm: async \(\) => \{\s*await mutation\.mutateAsync\(\{\s*path: `\$\{API\.requests\}\/\$\{request\.id\}\/gui`,\s*body: \{\},\s*etag,/);
  assert.match(send, /notify\("Đã gửi yêu cầu cho nhân viên\."\)/);
  assert.doesNotMatch(send, /save\(|catch|finally/);
});

// UC-24 AC-8: Đóng/Hủy xác nhận chỉ đóng hộp, API gửi chỉ nằm trong onConfirm (A3)
test("dismissing send confirmation cannot call the send API", () => {
  const send = source.slice(source.indexOf("  function send("), source.indexOf("  function cancel("));
  assert.equal((source.match(/\/gui`/g) || []).length, 1);
  assert.equal((send.match(/mutation\.mutateAsync\(/g) || []).length, 1);
  const beforeConfirm = send.slice(0, send.indexOf("onConfirm: async"));
  assert.doesNotMatch(beforeConfirm, /mutation\.mutateAsync|\/gui/);
  assert.doesNotMatch(send, /onClose|onCancel|navigate\(/);
  const confirmation = feedback.slice(feedback.indexOf("function Confirmation("));
  assert.equal((confirmation.match(/options\.onConfirm\(/g) || []).length, 1);
  assert.match(confirmation, /async function submit\(event\)[\s\S]*?await options\.onConfirm\(reason\.trim\(\)\)/);
  assert.match(confirmation, /onCancel=\{\(event\) => \{\s*event\.preventDefault\(\);\s*if \(!busy\) onClose\(\);\s*\}\}/);
  assert.match(confirmation, /<Button variant="secondary" onClick=\{onClose\} disabled=\{busy\}>\s*Hủy/);
  assert.match(confirmation, /aria-label="Đóng xác nhận"\s*disabled=\{busy\}\s*onClick=\{onClose\}/);
});
