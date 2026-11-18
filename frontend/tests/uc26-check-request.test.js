import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { dateTime } from "../src/lib/format.js";
import {
  CHECK_COLUMNS,
  canCheckRequest,
  checkConfirmEntries,
  checkImpact,
  checkLines,
  requestDetailEntries,
  unitCell,
} from "../src/features/production/requestForm.js";

const source = readFileSync(new URL("../src/features/production/RequestsPage.jsx", import.meta.url), "utf8");
const record = {
  id: 1, ma_yeu_cau_san_xuat: "YCSX-202611-000001", trang_thai: "da_gui",
  loai_yeu_cau: "xuat_giao", nhan_vien_duoc_giao_id: 20,
};
const line = {
  mat_hang_id: 2, ma_mat_hang: "MH-000002", ten_mat_hang: "Khung", don_vi_tinh: "cái",
  so_luong_can: 7, so_luong_con_dung: 4, so_luong_thieu: 3,
};
const shortage = {
  lan_dau: true, so_luong: 10, so_luong_dung_thanh_pham: 3, so_luong_can_san_xuat: 7,
  du_linh_kien: false, trang_thai_du_kien: "cho_bo_sung_linh_kien",
  giu_thanh_pham: 3, linh_kien: [line],
};

// Exercise the real handler with its JSX-only content removed; DOM layout is checked below.
function handler({ result = shortage, readError, writeError } = {}) {
  const start = source.indexOf("  async function openCheck()");
  const end = source.indexOf("  // UC-23", start);
  assert.ok(start > 0 && end > start);
  const body = source.slice(start, end).replace(/content: <>[\s\S]*?<\/>,/, "content: null,");
  const state = { reads: [], writes: [], notices: [], errors: [], pending: [], options: null };
  const ports = {
    record, snapshot: { etag: '"reviewed"' }, checkPath: "/yeu_cau_san_xuat/1/kiem_tra", checkImpact,
    checkRead: { current: null },
    readCheckPreview: async (path) => {
      state.reads.push(path);
      if (readError) throw readError;
      return shortage;
    },
    checkMutation: { mutateAsync: async (input) => {
      state.writes.push(input);
      if (writeError) throw writeError;
      return { data: { yeu_cau: { ...record, trang_thai: result.trang_thai_du_kien }, ket_qua: result }, etag: '"new"' };
    } },
    confirm: (options) => { state.options = options; },
    notify: (message) => state.notices.push(message),
    setCheckError: (error) => state.errors.push(error),
    setCheckPending: (pending) => state.pending.push(pending),
  };
  const open = new Function(...Object.keys(ports), `return (${body.trim()});`)(...Object.values(ports));
  return { open, state, ports };
}

// UC-26 D6: Chỉ NV được giao ở Đã gửi hoặc Chờ bổ sung thấy thao tác
test("only assigned employees can check sent or waiting requests", () => {
  for (const trang_thai of ["nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"]) {
    const row = { ...record, trang_thai };
    const eligible = ["da_gui", "cho_bo_sung_linh_kien"].includes(trang_thai);
    assert.equal(canCheckRequest(row, false, 20), eligible);
    assert.equal(canCheckRequest(row, false, "20"), eligible);
    assert.equal(canCheckRequest(row, true, 20), false);
    assert.equal(canCheckRequest(row, false, 21), false);
  }
  assert.equal(canCheckRequest(null, false, 20), false);
  assert.equal(canCheckRequest(record, false, undefined), false);
  assert.match(source, /userId=\{user\.id\}/);
});

// UC-26 D6: Đúng nhãn nút, thanh thao tác, trạng thái bận và nội dung hộp xác nhận
test("check action uses approved labels and shared confirmation components", () => {
  assert.match(source, /<div className="actions actions-end">\s*<Button disabled=\{refreshing \|\| checkMutation\.isPending \|\| checkPending\} onClick=\{openCheck\}>\s*\{record\.trang_thai === "da_gui" \? "Kiểm tra" : "Kiểm tra lại"\}/);
  assert.match(source, /title: ketQua\.lan_dau \? "Kiểm tra yêu cầu sản xuất" : "Kiểm tra lại yêu cầu sản xuất"/);
  assert.match(source, /description: record\.ma_yeu_cau_san_xuat/);
  assert.match(source, /<InfoGrid entries=\{checkConfirmEntries\(ketQua, record\.loai_yeu_cau\)\} \/>/);
  assert.match(source, /<RequestCheckRows rows=\{checkLines\(ketQua\)\} \/>/);
  assert.match(source, /impact: checkImpact\(ketQua\)/);
});

// UC-26 AC-9: Hộp nhập kho ẩn thành phẩm dùng từ kho, giữ đúng số cần sản xuất
// UC-26 A7: Nhập kho không dùng thành phẩm có sẵn
test("confirmation hides existing finished products for stock replenishment", () => {
  assert.deepEqual(checkConfirmEntries(shortage, "xuat_giao"), [
    ["Thành phẩm dùng từ kho", "3"], ["Số cần sản xuất", "7"], ["Linh kiện", "Thiếu"],
  ]);
  assert.deepEqual(checkConfirmEntries({ ...shortage, so_luong_can_san_xuat: 5, du_linh_kien: true }, "nhap_kho"), [
    ["Số cần sản xuất", "5"], ["Linh kiện", "Đủ"],
  ]);
});

// UC-26 AC-5: Bảng báo thiếu đủ 6 cột, cột số numeric và id ổn định
test("shortage table preserves all six report fields and numeric columns", () => {
  assert.deepEqual(CHECK_COLUMNS, [
    { key: "ma_mat_hang", label: "Mã" }, { key: "ten_mat_hang", label: "Tên" },
    { key: "don_vi_tinh", label: "Đơn vị tính", render: unitCell }, { key: "so_luong_can", label: "Cần", numeric: true },
    { key: "so_luong_con_dung", label: "Còn dùng được", numeric: true },
    { key: "so_luong_thieu", label: "Thiếu", numeric: true },
  ]);
  assert.equal(CHECK_COLUMNS[2].render({ don_vi_tinh: "chiec" }), "chiếc");
  const original = structuredClone(shortage);
  assert.equal(CHECK_COLUMNS[2].render({ don_vi_tinh: "chiec" }), "chiếc");
  assert.deepEqual(checkLines(shortage), [{ ...line, id: 2 }]);
  assert.deepEqual(shortage, original);
  assert.deepEqual(checkLines({ ...shortage, linh_kien: [], so_luong_can_san_xuat: 0 }), []);
});

// UC-26 A1: Đủ thành phẩm không có linh kiện, câu tác động chỉ giữ thành phẩm
test("impact explains finished product only and full component reservations without deducting stock", () => {
  assert.equal(checkImpact({ ...shortage, du_linh_kien: true }), "Giữ 3 thành phẩm và toàn bộ linh kiện; chưa trừ tồn.");
  assert.equal(checkImpact({ ...shortage, du_linh_kien: true, linh_kien: [] }), "Giữ 3 thành phẩm; chưa trừ tồn.");
  assert.equal(checkImpact({ ...shortage, du_linh_kien: true, giu_thanh_pham: 0 }), "Giữ toàn bộ linh kiện; chưa trừ tồn.");
});

// UC-26 A2: Thiếu không giữ linh kiện nào, nhập kho không nói giữ thành phẩm
test("shortage impact explains waiting and all or nothing component reservation", () => {
  assert.equal(checkImpact(shortage), "Giữ 3 thành phẩm, không giữ linh kiện nào; yêu cầu chuyển Chờ bổ sung linh kiện; chưa trừ tồn.");
  assert.equal(checkImpact({ ...shortage, giu_thanh_pham: 0 }), "Không giữ linh kiện nào; yêu cầu chuyển Chờ bổ sung linh kiện; chưa trừ tồn.");
});

// UC-26 D3: Kiểm tra lại vẫn thiếu không có gì thay đổi
test("recheck impact distinguishes unchanged shortages from newly held components", () => {
  assert.equal(checkImpact({ ...shortage, lan_dau: false, giu_thanh_pham: 0 }), "Không có gì thay đổi.");
  assert.equal(checkImpact({ ...shortage, lan_dau: false, giu_thanh_pham: 0, du_linh_kien: true }), "Giữ toàn bộ linh kiện; chưa trừ tồn.");
});

// UC-26 D5: Chi tiết chỉ hiện số chốt khi đã kiểm tra, nhập kho ẩn thành phẩm
test("checked detail displays finalized quantities and first check time after sent time", () => {
  const checked = { ...record, kiem_tra_lan_dau_at: "2026-11-16T08:00:00Z", so_luong_dung_thanh_pham: 3, so_luong_can_san_xuat: 7 };
  const entries = requestDetailEntries(checked, [], []);
  const index = entries.findIndex(([label]) => label === "Gửi lúc");
  assert.deepEqual(entries.slice(index + 1, index + 4), [
    ["Thành phẩm dùng từ kho", "3"], ["Số cần sản xuất", "7"],
    ["Kiểm tra lần đầu lúc", dateTime(checked.kiem_tra_lan_dau_at)],
  ]);
  const input = requestDetailEntries({ ...checked, loai_yeu_cau: "nhap_kho", so_luong_can_san_xuat: 10 }, [], []);
  assert.equal(input.some(([label]) => label === "Thành phẩm dùng từ kho"), false);
  assert.equal(Object.fromEntries(input)["Số cần sản xuất"], "10");
  const unchecked = requestDetailEntries(record, [], []);
  for (const label of ["Thành phẩm dùng từ kho", "Số cần sản xuất", "Kiểm tra lần đầu lúc"]) {
    assert.equal(unchecked.some(([key]) => key === label), false);
  }
});

// UC-26 AC-8: Mở rồi đóng xác nhận chỉ GET, không POST hoặc lưu kết quả
// UC-26 A5: Chỉ callback onConfirm được ghi dữ liệu
test("dismissing confirmation after GET makes no POST", async () => {
  const { open, state } = handler();
  await open();
  assert.deepEqual(state.reads, ["/yeu_cau_san_xuat/1/kiem_tra"]);
  assert.equal(state.options.title, "Kiểm tra yêu cầu sản xuất");
  assert.equal(typeof state.options.onConfirm, "function");
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.notices, []);
  assert.deepEqual(state.pending, [true, false]);
  assert.equal("onClose" in state.options, false);
  assert.equal("onCancel" in state.options, false);
});

// UC-26 D1: Xác nhận dùng body rỗng và ETag đã xem, hiển thị kết quả thật sau tính lại
test("confirmation posts the reviewed ETag and reports the actual recomputed result", async () => {
  const actual = { ...shortage, so_luong_dung_thanh_pham: 1, so_luong_can_san_xuat: 9,
    giu_thanh_pham: 1, linh_kien: [{ ...line, so_luong_can: 9, so_luong_thieu: 5 }] };
  const { open, state, ports } = handler({ result: actual });
  await open();
  ports.snapshot.etag = '"changed-during-confirmation"';
  await state.options.onConfirm();
  assert.deepEqual(state.writes, [{ path: "/yeu_cau_san_xuat/1/kiem_tra", body: {}, etag: '"reviewed"' }]);
  assert.deepEqual(state.notices, ["Yêu cầu Chờ bổ sung linh kiện."]);
});

// UC-26 AC-7: Thông báo phân biệt đủ và kiểm tra lại vẫn thiếu
test("notifications distinguish enough components from an unchanged recheck", async () => {
  for (const [result, message] of [
    [{ ...shortage, lan_dau: false }, "Vẫn thiếu linh kiện."],
    [{ ...shortage, du_linh_kien: true, trang_thai_du_kien: "dang_thuc_hien" }, "Yêu cầu Đang thực hiện."],
  ]) {
    const { open, state } = handler({ result });
    await open();
    await state.options.onConfirm();
    assert.deepEqual(state.notices, [message]);
  }
});

// UC-26 D1: Lỗi GET dùng ErrorNotice, không mở xác nhận hoặc POST
test("GET failure is shown through existing ErrorNotice and never confirms", async () => {
  const failure = new Error("Không tải được kết quả");
  const { open, state } = handler({ readError: failure });
  await open();
  assert.deepEqual(state.errors, [null, failure]);
  assert.deepEqual(state.pending, [true, false]);
  assert.equal(state.options, null);
  assert.deepEqual(state.writes, []);
  assert.match(source, /<ErrorNotice error=\{checkError\} \/>/);
});

// UC-26 A6: Lỗi POST truyền lên hộp xác nhận, không hiện thành công hoặc kết quả giả
test("POST failure propagates to confirmation without reporting success", async () => {
  const failure = new Error("Dữ liệu đã thay đổi");
  const { open, state } = handler({ writeError: failure });
  await open();
  await assert.rejects(state.options.onConfirm(), (error) => error === failure);
  assert.equal(state.writes.length, 1);
  assert.deepEqual(state.notices, []);
});

test("leaving the request while opening confirmation skips the stale GET response", async () => {
  const { open, state, ports } = handler();
  const pending = open();
  ports.checkRead.current.abort();
  await pending;
  assert.equal(state.options, null);
  assert.deepEqual(state.writes, []);
  assert.deepEqual(state.errors, [null]);
});

test("confirmation from an unmounted detail cannot post", async () => {
  const { open, state, ports } = handler();
  await open();
  ports.checkRead.current.abort();
  await assert.rejects(state.options.onConfirm(), /Chi tiết yêu cầu đã thay đổi/);
  assert.deepEqual(state.writes, []);
});
