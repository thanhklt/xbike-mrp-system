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
import { REQUEST_TYPE_LABELS } from "../src/features/production/requestForm.js";
import { API } from "../src/lib/api/endpoints.js";
import { apiClient, writeResource } from "../src/lib/api/client.js";
import { itemName, number } from "../src/lib/format.js";

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
      return mutate ? mutate(input) : { data: { ...document, trang_thai: "da_duyet" }, etag: '"approved"' };
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
  function approve() {
    const button = state.buttons.get("Duyệt");
    assert.ok(button);
    assert.equal(Boolean(button.disabled), false);
    button.onClick();
    assert.equal(state.confirmations.length, 1);
    return state.confirmations[0];
  }
  return { state, render, approve };
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
    Field: () => { throw new Error("Approval must not request a reason"); },
    ErrorNotice: ({ error }) => error && React.createElement("div", { role: "alert" }, error.message),
  };
  const Component = new Function(...Object.keys(ports), `${confirmationCode}; return Confirmation;`)(...Object.values(ports));
  function render() {
    slot = ref = 0;
    return renderToStaticMarkup(React.createElement(Component, { options, onClose: () => { state.closed = true; } }));
  }
  return { state, render };
}

// UC-31 AC-3: Chỉ QLK + Chờ duyệt + yêu cầu Đang thực hiện có nút Duyệt
test("approval button enforces manager document and request states", () => {
  assert.equal(canApproveCompletion(completion, row, true), true);
  const valid = section();
  const html = valid.render();
  assert.deepEqual([...valid.state.buttons.keys()], ["Duyệt"]);
  assert.match(html, /<div class="actions actions-end"><button>Duyệt<\/button><\/div>/);
  assert.doesNotMatch(html, /Từ chối/);
  for (const [document, record, manager] of [
    [completion, row, false], [null, row, true], [completion, null, true],
    ...["nhap", "tu_choi", "da_duyet"].map((trang_thai) => [{ ...completion, trang_thai }, row, true]),
    ...["nhap", "da_gui", "cho_bo_sung_linh_kien", "hoan_thanh", "da_huy"].map((trang_thai) => [completion, { ...row, trang_thai }, true]),
  ]) {
    assert.equal(canApproveCompletion(document, record, manager), false);
    if (record) {
      const ui = section({ document, record, manager });
      ui.render();
      assert.equal(ui.state.buttons.has("Duyệt"), false);
    }
  }
});

// UC-31 D4: Hộp xác nhận đủ năm dòng, nhãn loại từ REQUEST_TYPE_LABELS, số và ĐVT đúng
test("confirmation shows five approved fields and exact impact for both request types", () => {
  for (const kind of ["xuat_giao", "nhap_kho"]) {
    const record = { ...row, loai_yeu_cau: kind };
    const ui = section({ record });
    ui.render();
    const options = ui.approve();
    const expected = [
      ["Mã chứng từ", completion.ma_phieu], ["Loại yêu cầu", REQUEST_TYPE_LABELS[kind]],
      ["Thành phẩm", itemName(items, 5)], ["Số lượng hoàn thành", "7"], ["Đơn vị tính", "xe"],
    ];
    assert.equal(options.title, "Duyệt chứng từ hoàn thành");
    assert.equal(options.description, completion.ma_phieu);
    assert.deepEqual(options.content.props.entries, expected);
    assert.deepEqual(approveConfirmEntries(completion, record, items), expected);
    assert.equal(options.impact, kind === "xuat_giao"
      ? "Tồn thành phẩm tăng 7; 7 xe được giữ cho yêu cầu này."
      : "Tồn thành phẩm tăng 7; 7 xe còn dùng được; yêu cầu chuyển Hoàn thành.");
    const modal = confirmation(options);
    const html = modal.render();
    assert.match(html, /Duyệt chứng từ hoàn thành/);
    assert.equal((html.match(/<dt>/g) || []).length, 5);
    assert.deepEqual(ui.state.writes, []);
  }
});

// UC-31 D4: Câu tác động định dạng N qua number; thành phẩm chưa có trong catalog dùng fallback
test("approval helpers format quantities and preserve product and unit fallbacks", () => {
  const large = { ...completion, so_luong_hoan_thanh: 12345 };
  const n = number(12345);
  assert.equal(approveImpact(large, row), `Tồn thành phẩm tăng ${n}; ${n} xe được giữ cho yêu cầu này.`);
  assert.equal(approveImpact(large, { ...row, loai_yeu_cau: "nhap_kho" }),
    `Tồn thành phẩm tăng ${n}; ${n} xe còn dùng được; yêu cầu chuyển Hoàn thành.`);
  assert.deepEqual(approveConfirmEntries(large, row, []).slice(2), [
    ["Thành phẩm", itemName([], 5)], ["Số lượng hoàn thành", n], ["Đơn vị tính", "—"],
  ]);
});

// UC-31 A1: Hủy, đóng nút X hoặc Escape không POST và không đổi chứng từ/yêu cầu
test("all confirmation dismissal paths leave documents untouched without POST", () => {
  for (const kind of ["xuat_giao", "nhap_kho"]) {
    for (const action of ["cancel", "close", "escape"]) {
      const record = { ...row, loai_yeu_cau: kind };
      const before = structuredClone({ completion, record });
      const ui = section({ record });
      ui.render();
      const modal = confirmation(ui.approve());
      modal.render();
      if (action === "cancel") modal.state.buttons.get("Hủy").onClick();
      if (action === "close") modal.state.close();
      if (action === "escape") {
        let prevented = false;
        modal.state.cancel({ preventDefault: () => { prevented = true; } });
        assert.equal(prevented, true);
      }
      assert.equal(modal.state.closed, true);
      assert.deepEqual({ completion, record }, before);
      assert.deepEqual(ui.state.writes, []);
      assert.deepEqual(ui.state.notices, []);
    }
  }
});

// UC-31 D1: Xác nhận POST body {}, If-Match chứng từ đã xem, không lấy ETag cập nhật trong lúc xác nhận
test("confirmed approval sends actual POST with reviewed completion If-Match and notifies", async () => {
  const previousAdapter = apiClient.defaults.adapter;
  const previousStorage = globalThis.localStorage;
  const requests = [];
  globalThis.localStorage = { getItem: () => null };
  apiClient.defaults.adapter = async (config) => {
    requests.push(config);
    return { data: { data: { ...completion, trang_thai: "da_duyet" }, meta: {} },
      status: 200, statusText: "OK", headers: { etag: '"approved"' }, config };
  };
  try {
    const ui = section({ mutate: writeResource });
    ui.render();
    const modal = confirmation(ui.approve());
    modal.render();
    assert.equal(requests.length, 0);
    ui.state.query.data = { data: completion, etag: '"newer-version"' };
    await modal.state.submit({ preventDefault() {} });
    assert.equal(requests.length, 1);
    assert.equal(requests[0].method, "post");
    assert.equal(requests[0].url, "/chung_tu_hoan_thanh_sx/12/duyet");
    assert.equal(requests[0].data, "{}");
    assert.equal(requests[0].headers.get("If-Match"), '"completion-reviewed"');
    assert.deepEqual(ui.state.notices, ["Đã duyệt chứng từ hoàn thành."]);
    assert.equal(modal.state.closed, true);
  } finally {
    apiClient.defaults.adapter = previousAdapter;
    if (previousStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = previousStorage;
  }
});

// UC-31 A2: Lỗi duyệt giữ hộp mở, hiển thị trong hộp và không báo thành công hay lặp lỗi tại khối
test("approval conflict stays in the confirmation without duplicate section errors", async () => {
  for (const status of [409, 412]) {
    const failure = Object.assign(new Error("Chứng từ đã thay đổi"), { status });
    const ui = section({ mutate: async () => { throw failure; } });
    ui.render();
    const modal = confirmation(ui.approve());
    modal.render();
    await modal.state.submit({ preventDefault() {} });
    assert.match(modal.render(), /role="alert">Chứng từ đã thay đổi/);
    assert.equal(modal.state.closed, false);
    assert.doesNotMatch(ui.render(), /role="alert"/);
    assert.deepEqual(ui.state.slots, [false, null]);
    assert.equal(ui.state.writes.length, 1);
    assert.deepEqual(ui.state.notices, []);
  }
});

// UC-31 D4: Đang ghi vô hiệu nút; xác nhận chống submit lặp; tải/lỗi không có thao tác
test("pending loading and errors suppress approval and duplicate confirmation submissions", async () => {
  let finish;
  const ui = section({ mutate: () => new Promise((resolve) => { finish = resolve; }) });
  ui.state.pending = true;
  ui.render();
  assert.equal(ui.state.buttons.get("Duyệt").disabled, true);
  ui.state.pending = false;
  ui.render();
  const modal = confirmation(ui.approve());
  modal.render();
  const first = modal.state.submit({ preventDefault() {} });
  await modal.state.submit({ preventDefault() {} });
  assert.equal(ui.state.writes.length, 1);
  modal.render();
  assert.equal(modal.state.buttons.get("Đang xử lý…").disabled, true);
  assert.equal(modal.state.buttons.get("Hủy").disabled, true);
  finish({ data: completion });
  await first;
  assert.deepEqual(ui.state.notices, ["Đã duyệt chứng từ hoàn thành."]);
  ui.state.query.isPending = true;
  assert.equal(ui.render(), '<section class="stack"><h3>Chứng từ hoàn thành sản xuất</h3>Đang tải dữ liệu…</section>');
  assert.equal(ui.state.buttons.size, 0);
  ui.state.query.isPending = false;
  ui.state.query.isError = true;
  ui.state.query.error = new Error("Không tải được chứng từ");
  assert.match(ui.render(), /role="alert">Không tải được chứng từ/);
  assert.equal(ui.state.buttons.size, 0);
});
