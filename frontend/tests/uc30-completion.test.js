import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { transformWithEsbuild } from "vite";
import {
  canCreateCompletion, canSendCompletion, completionEntries,
  completionConfirmEntries, completionSendLabel,
  // UC-31 thêm nút Duyệt vào cùng khối; khung dựng lại component cần các hàm này.
  canApproveCompletion, approveConfirmEntries, approveImpact,
} from "../src/features/production/completionForm.js";
import { API } from "../src/lib/api/endpoints.js";
import { dateTime, number } from "../src/lib/format.js";

const source = readFileSync(new URL("../src/features/production/RequestsPage.jsx", import.meta.url), "utf8");
const row = {
  id: 1, mat_hang_id: 5, nhan_vien_duoc_giao_id: 20, trang_thai: "dang_thuc_hien",
  started_at: "2026-11-16T08:00:00Z", so_luong_can_san_xuat: 7,
};
const draft = {
  id: 12, ma_phieu: "HTSX-202611-000012", so_luong_hoan_thanh: 7,
  trang_thai: "nhap", finish_time: null, ly_do_tu_choi: null,
};
const items = [{ id: 5, ma_mat_hang: "MH-000005", ten_mat_hang: "Xe đạp", don_vi_tinh: "xe" }];
const componentSource = source.slice(source.indexOf("function CompletionSection("));
const { code } = await transformWithEsbuild(componentSource, "completion.jsx", { loader: "jsx" });

function section({ completion = null, record = row, manager = false, userId = 20, failure = null } = {}) {
  const state = {
    slots: [false, null], buttons: new Map(), writes: [], notices: [], confirmations: [], queries: [],
    query: { data: { data: completion, etag: '"completion-reviewed"' }, isPending: false, isError: false },
    pending: false, failure,
  };
  let slot = 0;
  const ports = {
    React, API, number, canCreateCompletion, canSendCompletion,
    completionEntries, completionConfirmEntries, completionSendLabel,
    canApproveCompletion, approveConfirmEntries, approveImpact,
    useState: () => {
      const index = slot++;
      return [state.slots[index], (value) => { state.slots[index] = value; }];
    },
    useResource: (path, params, enabled) => { state.queries.push({ path, params, enabled }); return state.query; },
    useWrite: () => ({ isPending: state.pending, mutateAsync: async (input) => {
      state.writes.push(input);
      if (state.failure) throw state.failure;
      return { data: draft, etag: '"created"' };
    } }),
    useFeedback: () => ({
      confirm: (options) => state.confirmations.push(options),
      notify: (message) => state.notices.push(message),
    }),
    InfoGrid: ({ entries }) => React.createElement("dl", null,
      entries.map(([label, value]) => React.createElement("div", { key: label },
        React.createElement("dt", null, label), React.createElement("dd", null, value)))),
    Badge: ({ status }) => React.createElement("span", { "data-status": status }, status),
    Button: (props) => {
      state.buttons.set(props.children, props);
      return React.createElement("button", { disabled: props.disabled, "data-variant": props.variant }, props.children);
    },
    Notice: ({ children }) => React.createElement("aside", null, children),
    ErrorNotice: ({ error }) => error && React.createElement("div", { role: "alert" }, error.message),
    QueryState: ({ query, children }) => query.isPending ? "Đang tải dữ liệu…"
      : query.isError ? React.createElement("div", { role: "alert" }, query.error.message) : children,
  };
  const Component = new Function(...Object.keys(ports), `${code}; return CompletionSection;`)(...Object.values(ports));
  function render() {
    slot = 0;
    state.buttons.clear();
    return renderToStaticMarkup(React.createElement(Component, { record, items, manager, userId }));
  }
  function click(label) {
    const button = state.buttons.get(label);
    assert.ok(button, `Missing button: ${label}`);
    assert.equal(Boolean(button.disabled), false);
    return button.onClick();
  }
  return { state, render, click };
}

// UC-30 AC-1: Form lập chỉ đọc đúng số cần sản xuất, không có ô nhập số lượng hoặc thời điểm
test("create form keeps fixed quantity and save/discard without a technical notice", () => {
  const ui = section();
  assert.match(ui.render(), /<h3>Chứng từ hoàn thành sản xuất<\/h3>/);
  assert.deepEqual([...ui.state.buttons.keys()], ["Lập chứng từ hoàn thành"]);
  ui.click("Lập chứng từ hoàn thành");
  const html = ui.render();
  assert.match(html, /<dt>Số lượng hoàn thành<\/dt><dd>7<\/dd>/);
  assert.doesNotMatch(html, /Thời điểm hoàn thành do hệ thống ghi khi bạn xác nhận gửi\./);
  assert.doesNotMatch(html, /<input|<select|<textarea/);
  assert.match(html, /data-variant="secondary">Bỏ/);
  assert.deepEqual([...ui.state.buttons.keys()], ["Bỏ", "Lưu"]);
  assert.deepEqual(ui.state.writes, []);
  ui.click("Bỏ");
  ui.render();
  assert.deepEqual([...ui.state.buttons.keys()], ["Lập chứng từ hoàn thành"]);
  assert.deepEqual(ui.state.writes, []);
});

// UC-30 AC-1: Lưu chỉ gửi id yêu cầu, không gửi số lượng/thời điểm và thông báo đúng
test("save posts only request id without If-Match and notifies success", async () => {
  const ui = section();
  ui.render();
  ui.click("Lập chứng từ hoàn thành");
  ui.render();
  await ui.click("Lưu");
  assert.deepEqual(ui.state.writes, [{
    path: "/chung_tu_hoan_thanh_sx", body: { yeu_cau_san_xuat_id: 1 }, versioned: false,
  }]);
  assert.deepEqual(ui.state.notices, ["Đã lưu chứng từ hoàn thành."]);
  assert.deepEqual(ui.state.slots, [false, null]);
  assert.deepEqual(ui.state.confirmations, []);
});

// UC-30 AC-4: Có chứng từ thì không hiện Lập/Lưu; hiển thị đủ thông tin và Badge
test("existing completion replaces creation actions with readonly detail and status badge", () => {
  const ui = section({ completion: draft });
  const html = ui.render();
  assert.deepEqual([...ui.state.buttons.keys()], ["Gửi"]);
  assert.match(html, /<dt>Mã chứng từ<\/dt><dd>HTSX-202611-000012<\/dd>/);
  assert.match(html, /data-status="nhap"/);
  assert.match(html, /<dt>Số lượng hoàn thành<\/dt><dd>7<\/dd>/);
  assert.match(html, /<dt>Thời điểm hoàn thành<\/dt><dd>—<\/dd>/);
  assert.doesNotMatch(html, /Lập chứng từ hoàn thành|>Lưu</);
  assert.deepEqual(completionEntries(draft), [
    ["Mã chứng từ", draft.ma_phieu], ["Trạng thái", "nhap"],
    ["Số lượng hoàn thành", "7"], ["Thời điểm hoàn thành", "—"],
  ]);
});

// UC-30 D3: Quyền lập/gửi theo NV được giao, trạng thái yêu cầu và chứng từ; QLK chỉ xem
// UC-33 D4: API ẩn Nháp với QLK, khối QLK nhận data null
test("creation and send permissions enforce all role scope and state conditions", () => {
  assert.equal(canCreateCompletion(row, null, false, "20"), true);
  assert.equal(canSendCompletion(row, draft, false, "20"), true);
  for (const [record, completion, manager, userId] of [
    [row, null, true, 20], [row, null, false, 21], [null, null, false, 20],
    [row, draft, false, 20], [{ ...row, started_at: null }, null, false, 20],
    ...[0, -1, null, undefined].map((n) => [{ ...row, so_luong_can_san_xuat: n }, null, false, 20]),
    ...["nhap", "da_gui", "cho_bo_sung_linh_kien", "hoan_thanh", "da_huy"].map((trang_thai) => [{ ...row, trang_thai }, null, false, 20]),
  ]) assert.equal(canCreateCompletion(record, completion, manager, userId), false);
  for (const [record, completion, manager, userId] of [
    [row, draft, true, 20], [row, draft, false, 21], [null, draft, false, 20],
    [row, null, false, 20],
    ...["cho_duyet", "da_duyet"].map((trang_thai) => [row, { ...draft, trang_thai }, false, 20]),
    ...["nhap", "da_gui", "cho_bo_sung_linh_kien", "hoan_thanh", "da_huy"].map((trang_thai) => [{ ...row, trang_thai }, draft, false, 20]),
  ]) assert.equal(canSendCompletion(record, completion, manager, userId), false);
  assert.equal(canSendCompletion(row, { ...draft, trang_thai: "tu_choi" }, false, 20), true);
  for (const manager of [true, false]) {
    const ui = section({ completion: manager ? null : draft, manager, userId: manager ? 20 : 21 });
    assert.match(ui.render(), manager ? /Chưa có chứng từ hoàn thành\./ : /HTSX-202611-000012/);
    assert.deepEqual([...ui.state.buttons.keys()], []);
  }
});

// UC-30 AC-2: AC-3 xác nhận đủ bốn thông tin, POST body rỗng với ETag đã xem
test("send confirmation contains document product quantity and unit without an explanatory notice", async () => {
  const ui = section({ completion: draft });
  ui.render();
  ui.click("Gửi");
  assert.deepEqual(ui.state.writes, []);
  assert.equal(ui.state.confirmations.length, 1);
  const options = ui.state.confirmations[0];
  assert.equal(options.title, "Gửi chứng từ hoàn thành");
  assert.equal(options.description, draft.ma_phieu);
  assert.equal(options.hideImpact, true);
  assert.deepEqual(options.content.props.entries, [
    ["Mã chứng từ", draft.ma_phieu], ["Thành phẩm", "Xe đạp — MH-000005"],
    ["Số lượng hoàn thành", "7"], ["Đơn vị tính", "xe"],
  ]);
  ui.state.query.data = { data: draft, etag: '"updated-while-confirming"' };
  await options.onConfirm();
  assert.deepEqual(ui.state.writes, [{ path: "/chung_tu_hoan_thanh_sx/12/gui", body: {}, etag: '"completion-reviewed"' }]);
  assert.deepEqual(ui.state.notices, ["Đã gửi chứng từ hoàn thành."]);
});

// UC-30 A2: Đóng xác nhận Nháp/Bị từ chối không POST, không đổi dữ liệu hay ghi thời điểm
test("dismissing send or resend leaves the document and time untouched without POST", () => {
  for (const trang_thai of ["nhap", "tu_choi"]) {
    const completion = { ...draft, trang_thai, finish_time: trang_thai === "nhap" ? null : row.started_at };
    const before = structuredClone(completion);
    const ui = section({ completion });
    ui.render();
    ui.click(completionSendLabel(completion));
    ui.state.confirmations.pop();
    ui.render();
    assert.deepEqual(completion, before);
    assert.deepEqual(ui.state.writes, []);
    assert.deepEqual(ui.state.notices, []);
    assert.deepEqual(ui.state.slots, [false, null]);
  }
});

// UC-30 AC-5: A3 hiện lý do và giờ cũ; Gửi lại dùng cùng hộp, cùng endpoint, không về Nháp
test("rejected completion shows rejection and resends directly through the same confirmation", async () => {
  const completion = { ...draft, trang_thai: "tu_choi", finish_time: row.started_at, ly_do_tu_choi: "Kiểm tra lại" };
  const ui = section({ completion });
  const html = ui.render();
  assert.match(html, /<dt>Lý do từ chối<\/dt><dd>Kiểm tra lại<\/dd>/);
  assert.ok(html.includes(dateTime(row.started_at)));
  assert.deepEqual([...ui.state.buttons.keys()], ["Gửi lại"]);
  ui.click("Gửi lại");
  const options = ui.state.confirmations[0];
  assert.equal(options.title, "Gửi lại chứng từ hoàn thành");
  assert.equal(options.description, completion.ma_phieu);
  assert.equal(options.hideImpact, true);
  assert.deepEqual(options.content.props.entries, completionConfirmEntries(draft, row, items, true));
  await options.onConfirm();
  assert.deepEqual(ui.state.writes, [{ path: "/chung_tu_hoan_thanh_sx/12/gui", body: {}, etag: '"completion-reviewed"' }]);
  assert.deepEqual(ui.state.notices, ["Đã gửi chứng từ hoàn thành."]);
});

// UC-30 D4: Lỗi lập hiện riêng, giữ form và không báo thành công
test("create failure stays in its own ErrorNotice and preserves the form", async () => {
  const failure = Object.assign(new Error("Yêu cầu đã có chứng từ hoàn thành #12"), { status: 409 });
  const ui = section({ failure });
  ui.render();
  ui.click("Lập chứng từ hoàn thành");
  ui.render();
  await ui.click("Lưu");
  assert.deepEqual(ui.state.slots, [true, failure]);
  assert.match(ui.render(), /role="alert">Yêu cầu đã có chứng từ hoàn thành #12/);
  assert.deepEqual([...ui.state.buttons.keys()], ["Bỏ", "Lưu"]);
  assert.deepEqual(ui.state.notices, []);
});

// UC-30 D4: Lỗi gửi truyền tới hộp xác nhận, không lặp ở lỗi lập và không báo thành công
test("send failure remains in confirmation without a duplicate creation error", async () => {
  const failure = Object.assign(new Error("Dữ liệu đã thay đổi"), { status: 412 });
  const ui = section({ completion: draft, failure });
  ui.render();
  ui.click("Gửi");
  await assert.rejects(ui.state.confirmations[0].onConfirm(), (error) => error === failure);
  assert.deepEqual(ui.state.slots, [false, null]);
  assert.deepEqual(ui.state.notices, []);
  assert.equal(ui.state.writes.length, 1);
});

// UC-30 D4: Chặn thao tác khi đang ghi, tải qua useResource/QueryState và đặt khối đúng vị trí
test("completion uses its own query and mutation with loading error and disabled states", () => {
  const ui = section();
  ui.render();
  assert.deepEqual(ui.state.queries, [{ path: "/yeu_cau_san_xuat/1/chung_tu_hoan_thanh", params: {}, enabled: true }]);
  ui.click("Lập chứng từ hoàn thành");
  ui.state.pending = true;
  ui.render();
  assert.equal(ui.state.buttons.get("Bỏ").disabled, true);
  assert.equal(ui.state.buttons.get("Lưu").disabled, true);
  const sendUi = section({ completion: draft });
  sendUi.state.pending = true;
  sendUi.render();
  assert.equal(sendUi.state.buttons.get("Gửi").disabled, true);
  ui.state.query.isPending = true;
  assert.match(ui.render(), /Đang tải dữ liệu/);
  assert.equal(ui.state.buttons.size, 0);
  ui.state.query.isPending = false;
  ui.state.query.isError = true;
  ui.state.query.error = new Error("Không tải được chứng từ");
  assert.match(ui.render(), /role="alert">Không tải được chứng từ/);
  assert.equal(ui.state.buttons.size, 0);
  const info = source.indexOf("<InfoGrid entries={requestDetailEntries(");
  const block = source.indexOf("<CompletionSection record={record}");
  const actions = source.indexOf("{canCheckRequest(record, manager, userId) && (");
  assert.ok(info < block && block < actions);
  assert.match(componentSource, /const completionMutation = useWrite\(\)/);
  assert.match(componentSource, /className="actions actions-end"/);
});

// UC-30 D4: Khối chỉ xuất hiện khi đã bắt đầu hoặc đã có chứng từ; QLK xem cả Chờ duyệt/Đã duyệt
// UC-33 D4: QLK chỉ nhận chứng từ đã gửi, không nhận Nháp
test("section visibility follows production start or existing completion and manager is readonly", () => {
  const record = { ...row, started_at: null };
  assert.equal(section({ record }).render(), "");
  for (const trang_thai of ["tu_choi", "cho_duyet", "da_duyet"]) {
    const ui = section({ record, completion: { ...draft, trang_thai }, manager: true });
    const html = ui.render();
    assert.match(html, /Chứng từ hoàn thành sản xuất/);
    assert.match(html, /HTSX-202611-000012/);
    assert.ok(html.includes(`data-status="${trang_thai}"`));
    // UC-32 thêm Từ chối trước Duyệt khi chứng từ Chờ duyệt; QLK không lập/gửi.
    assert.deepEqual([...ui.state.buttons.keys()], trang_thai === "cho_duyet" ? ["Từ chối", "Duyệt"] : []);
  }
});

// UC-33 D4: QLK nhận data null khi đang thực hiện hiện thông báo, không có nút lập/gửi/duyệt/từ chối
test("manager sees empty completion notice without any actions for hidden draft", () => {
  const ui = section({ completion: null, manager: true });
  const html = ui.render();
  assert.match(html, /Chưa có chứng từ hoàn thành\./);
  assert.doesNotMatch(html, /<button|Lập chứng từ|>Gửi|>Duyệt|>Từ chối/);
  assert.deepEqual([...ui.state.buttons.keys()], []);
  assert.deepEqual(ui.state.writes, []);
});

// UC-30 D4: Khối không để trơ tiêu đề khi người xem không lập được; chỉ đọc chứng từ sau khi bắt đầu sản xuất
test("completion block shows an empty notice and only loads after production started", () => {
  assert.ok(source.includes("<Notice>Chưa có chứng từ hoàn thành.</Notice>"));
  assert.match(source, /chung_tu_hoan_thanh`, \{\}, Boolean\(record\.id && record\.started_at\)\)/);
});
