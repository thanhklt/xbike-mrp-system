import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { transformWithEsbuild } from "vite";
import {
  canApproveCompletion, approveConfirmEntries, approveImpact,
  canCreateCompletion, canSendCompletion, completionEntries,
  completionConfirmEntries, completionSendLabel,
} from "../src/features/production/completionForm.js";
import { API } from "../src/lib/api/endpoints.js";
import { apiClient, writeResource } from "../src/lib/api/client.js";
import { number } from "../src/lib/format.js";

const source = readFileSync(new URL("../src/features/production/RequestsPage.jsx", import.meta.url), "utf8");
const componentSource = source.slice(source.indexOf("function CompletionSection("));
const { code } = await transformWithEsbuild(componentSource, "completion.jsx", { loader: "jsx" });
const feedbackSource = readFileSync(new URL("../src/components/FeedbackProvider.jsx", import.meta.url), "utf8");
const { code: confirmationCode } = await transformWithEsbuild(
  feedbackSource.slice(feedbackSource.indexOf("function Confirmation(")), "confirmation.jsx", { loader: "jsx" },
);
const row = {
  id: 1, mat_hang_id: 5, loai_yeu_cau: "xuat_giao", nhan_vien_duoc_giao_id: 20,
  trang_thai: "dang_thuc_hien", started_at: "2026-11-16T08:00:00Z", so_luong_can_san_xuat: 7,
};
const completion = {
  id: 12, ma_phieu: "HTSX-202611-000012", so_luong_hoan_thanh: 7,
  trang_thai: "cho_duyet", finish_time: row.started_at, ly_do_tu_choi: null,
};
const items = [{ id: 5, ma_mat_hang: "MH-000005", ten_mat_hang: "Xe đạp", don_vi_tinh: "xe" }];

function section({ document = completion, record = row, manager = true, mutate } = {}) {
  const state = {
    slots: [false, null], buttons: new Map(), writes: [], notices: [], confirmations: [],
    query: { data: { data: document, etag: '"completion-reviewed"' }, isPending: false, isError: false },
    pending: false,
  };
  let slot = 0;
  const ports = {
    React, API, number, canApproveCompletion, approveConfirmEntries, approveImpact,
    canCreateCompletion, canSendCompletion, completionEntries, completionConfirmEntries, completionSendLabel,
    useState: () => {
      const index = slot++;
      return [state.slots[index], (value) => { state.slots[index] = value; }];
    },
    useResource: () => state.query,
    useWrite: () => ({ isPending: state.pending, mutateAsync: async (input) => {
      state.writes.push(input);
      return mutate ? mutate(input) : { data: { ...document, trang_thai: "tu_choi" }, etag: '"rejected"' };
    } }),
    useFeedback: () => ({
      confirm: (options) => state.confirmations.push(options),
      notify: (message) => state.notices.push(message),
    }),
    InfoGrid: ({ entries }) => React.createElement("dl", null, entries.map(([label, value]) =>
      React.createElement("div", { key: label }, React.createElement("dt", null, label), React.createElement("dd", null, value)))),
    Badge: ({ status }) => React.createElement("span", null, status),
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
    return renderToStaticMarkup(React.createElement(Component, { record, items, manager, userId: 20 }));
  }
  function reject() {
    const button = state.buttons.get("Từ chối");
    assert.ok(button);
    assert.equal(Boolean(button.disabled), false);
    button.onClick();
    assert.equal(state.confirmations.length, 1);
    return state.confirmations[0];
  }
  return { state, render, reject };
}

function confirmation(options) {
  const state = { slots: [false, null, ""], refs: [{ current: null }, { current: false }], buttons: new Map(), closed: false };
  let slot = 0;
  let ref = 0;
  const ports = {
    React: { ...React, createElement: (type, props, ...children) => {
      if (type === "form") state.submit = props.onSubmit;
      if (type === "dialog") state.cancel = props.onCancel;
      if (props?.["aria-label"] === "Đóng xác nhận") state.close = props.onClick;
      return React.createElement(type, props, ...children);
    } },
    useState: () => {
      const index = slot++;
      return [state.slots[index], (value) => { state.slots[index] = value; }];
    },
    useRef: () => state.refs[ref++],
    useEffect: () => {},
    Button: (props) => {
      state.buttons.set(props.children, props);
      return React.createElement("button", { disabled: props.disabled }, props.children);
    },
    Field: (props) => {
      state.field = props;
      return React.createElement("textarea", { required: props.required, value: props.value, onChange: props.onChange });
    },
    ErrorNotice: ({ error }) => error && React.createElement("div", { role: "alert" }, error.message),
  };
  const Component = new Function(...Object.keys(ports), `${confirmationCode}; return Confirmation;`)(...Object.values(ports));
  function render() {
    slot = ref = 0;
    return renderToStaticMarkup(React.createElement(Component, { options, onClose: () => { state.closed = true; } }));
  }
  return { state, render };
}

// UC-32 Main 2: Chỉ QLK + Chờ duyệt có Từ chối secondary trước Duyệt trong cùng actions
test("reject is secondary before approve with identical visibility and pending conditions", () => {
  const ui = section();
  const html = ui.render();
  assert.deepEqual([...ui.state.buttons.keys()], ["Từ chối", "Duyệt"]);
  assert.match(html, /<div class="actions actions-end"><button data-variant="secondary">Từ chối<\/button><button>Duyệt<\/button><\/div>/);
  for (const [document, record, manager] of [
    [completion, row, false], [null, row, true],
    ...["nhap", "tu_choi", "da_duyet"].map((trang_thai) => [{ ...completion, trang_thai }, row, true]),
    ...["nhap", "da_gui", "cho_bo_sung_linh_kien", "hoan_thanh", "da_huy"].map((trang_thai) => [completion, { ...row, trang_thai }, true]),
  ]) {
    const hidden = section({ document, record, manager });
    hidden.render();
    assert.equal(hidden.state.buttons.has("Từ chối"), false);
    assert.equal(hidden.state.buttons.has("Duyệt"), false);
  }
  ui.state.pending = true;
  ui.render();
  assert.equal(ui.state.buttons.get("Từ chối").disabled, true);
  ui.state.query.isPending = true;
  assert.match(ui.render(), /Đang tải dữ liệu/);
  assert.equal(ui.state.buttons.size, 0);
  ui.state.query.isPending = false;
  ui.state.query.isError = true;
  ui.state.query.error = new Error("Không tải được chứng từ");
  assert.match(ui.render(), /role="alert">Không tải được chứng từ/);
  assert.equal(ui.state.buttons.size, 0);
});

// UC-32 AC-1: Hộp đúng tiêu đề, mã, cảnh báo và bắt buộc lý do không rỗng sau trim
test("rejection confirmation requires a nonblank reason and shows exact warning", () => {
  const ui = section();
  ui.render();
  const options = ui.reject();
  assert.equal(options.title, "Từ chối chứng từ hoàn thành");
  assert.equal(options.description, completion.ma_phieu);
  assert.equal(options.reason, true);
  assert.equal(options.danger, true);
  assert.equal(options.impact, "Tồn không đổi; nhân viên sẽ gửi lại chứng từ.");
  const modal = confirmation(options);
  assert.match(modal.render(), /notice notice-warning/);
  assert.equal(modal.state.field.as, "textarea");
  assert.equal(modal.state.field.required, true);
  for (const reason of ["", " \t ", "Cần kiểm tra lại"]) {
    modal.state.field.onChange({ target: { value: reason } });
    modal.render();
    assert.equal(modal.state.buttons.get("Xác nhận").disabled, !reason.trim());
    assert.equal(modal.state.buttons.get("Xác nhận").variant, "danger");
  }
  assert.deepEqual(ui.state.writes, []);
  assert.deepEqual(ui.state.notices, []);
});

// UC-32 Main 2: Hủy, đóng hoặc Escape không POST và giữ nguyên chứng từ/yêu cầu
test("all dismissal paths leave completion and request untouched without a POST", () => {
  for (const action of ["cancel", "close", "escape"]) {
    const before = structuredClone({ completion, row });
    const ui = section();
    ui.render();
    const modal = confirmation(ui.reject());
    modal.render();
    modal.state.field.onChange({ target: { value: "Lý do chưa xác nhận" } });
    modal.render();
    if (action === "cancel") modal.state.buttons.get("Hủy").onClick();
    if (action === "close") modal.state.close();
    if (action === "escape") {
      let prevented = false;
      modal.state.cancel({ preventDefault: () => { prevented = true; } });
      assert.equal(prevented, true);
    }
    assert.equal(modal.state.closed, true);
    assert.deepEqual({ completion, row }, before);
    assert.deepEqual(ui.state.writes, []);
    assert.deepEqual(ui.state.notices, []);
  }
});

// UC-32 Main 4: POST đúng lý do đã trim và ETag chứng từ chụp khi mở hộp, thông báo đúng
test("confirmed rejection posts reason with reviewed completion ETag and notifies", async () => {
  const previousAdapter = apiClient.defaults.adapter;
  const previousStorage = globalThis.localStorage;
  const requests = [];
  globalThis.localStorage = { getItem: () => null };
  apiClient.defaults.adapter = async (config) => {
    requests.push(config);
    return { data: { data: { ...completion, trang_thai: "tu_choi" }, meta: {} },
      status: 200, statusText: "OK", headers: { etag: '"rejected"' }, config };
  };
  try {
    const ui = section({ mutate: writeResource });
    ui.render();
    const modal = confirmation(ui.reject());
    modal.render();
    assert.equal(requests.length, 0);
    ui.state.query.data = { data: completion, etag: '"newer-version"' };
    modal.state.field.onChange({ target: { value: "  Số lượng chưa đạt  " } });
    modal.render();
    await modal.state.submit({ preventDefault() {} });
    assert.equal(requests.length, 1);
    assert.equal(requests[0].method, "post");
    assert.equal(requests[0].url, "/chung_tu_hoan_thanh_sx/12/tu_choi");
    assert.equal(requests[0].data, JSON.stringify({ ly_do: "Số lượng chưa đạt" }));
    assert.equal(requests[0].headers.get("If-Match"), '"completion-reviewed"');
    assert.deepEqual(ui.state.notices, ["Đã từ chối chứng từ hoàn thành."]);
    assert.equal(modal.state.closed, true);
  } finally {
    apiClient.defaults.adapter = previousAdapter;
    if (previousStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = previousStorage;
  }
});

// UC-32 A2: Lỗi 409/412 giữ hộp mở, hiện lỗi, không báo thành công hoặc lặp lỗi tại khối
test("changed document errors stay inside rejection confirmation", async () => {
  for (const status of [409, 412]) {
    const failure = Object.assign(new Error("Chứng từ đã thay đổi"), { status });
    const ui = section({ mutate: async () => { throw failure; } });
    ui.render();
    const modal = confirmation(ui.reject());
    modal.render();
    modal.state.field.onChange({ target: { value: "Cần kiểm tra lại" } });
    modal.render();
    await modal.state.submit({ preventDefault() {} });
    assert.match(modal.render(), /role="alert">Chứng từ đã thay đổi/);
    assert.equal(modal.state.closed, false);
    assert.equal(modal.state.field.value, "Cần kiểm tra lại");
    assert.doesNotMatch(ui.render(), /role="alert"/);
    assert.deepEqual(ui.state.slots, [false, null]);
    assert.equal(ui.state.writes.length, 1);
    assert.deepEqual(ui.state.notices, []);
  }
});

// UC-32 Main 4: Đang xử lý chặn submit lặp và vô hiệu nút xác nhận/hủy
test("pending rejection cannot be submitted twice", async () => {
  let finish;
  const ui = section({ mutate: () => new Promise((resolve) => { finish = resolve; }) });
  ui.render();
  const modal = confirmation(ui.reject());
  modal.render();
  modal.state.field.onChange({ target: { value: "Cần kiểm tra lại" } });
  modal.render();
  const first = modal.state.submit({ preventDefault() {} });
  await modal.state.submit({ preventDefault() {} });
  assert.equal(ui.state.writes.length, 1);
  modal.render();
  assert.equal(modal.state.buttons.get("Đang xử lý…").disabled, true);
  assert.equal(modal.state.buttons.get("Hủy").disabled, true);
  finish({ data: completion });
  await first;
  assert.deepEqual(ui.state.notices, ["Đã từ chối chứng từ hoàn thành."]);
});

// UC-32 AC-3: NV thấy đúng lý do, chỉ có Gửi lại trực tiếp và không có thao tác về nháp
test("employee sees rejection reason and resends directly without a draft action", async () => {
  const document = { ...completion, trang_thai: "tu_choi", ly_do_tu_choi: "Số lượng chưa đạt" };
  const ui = section({ document, manager: false });
  const html = ui.render();
  assert.match(html, /<dt>Lý do từ chối<\/dt><dd>Số lượng chưa đạt<\/dd>/);
  assert.deepEqual([...ui.state.buttons.keys()], ["Gửi lại"]);
  assert.doesNotMatch(html, /về nháp|Về nháp|Nháp/);
  ui.state.buttons.get("Gửi lại").onClick();
  assert.equal(ui.state.confirmations[0].title, "Gửi lại chứng từ hoàn thành");
  await ui.state.confirmations[0].onConfirm();
  assert.deepEqual(ui.state.writes, [{
    path: "/chung_tu_hoan_thanh_sx/12/gui", body: {}, etag: '"completion-reviewed"',
  }]);
  assert.deepEqual(ui.state.notices, ["Đã gửi chứng từ hoàn thành."]);
});

