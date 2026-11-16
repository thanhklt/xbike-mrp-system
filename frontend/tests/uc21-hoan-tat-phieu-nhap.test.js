import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { transformWithEsbuild } from "vite";

const source = readFileSync(new URL("../src/features/receiving/ReceivingPage.jsx", import.meta.url), "utf8");
const { code } = await transformWithEsbuild(
  source.slice(source.indexOf("function ReceiptEditor(")), "receipt.jsx", { loader: "jsx" },
);
const feedback = readFileSync(new URL("../src/components/FeedbackProvider.jsx", import.meta.url), "utf8");
const { code: confirmationCode } = await transformWithEsbuild(
  feedback.slice(feedback.indexOf("function Confirmation(")), "confirmation.jsx", { loader: "jsx" },
);

function editor() {
  const record = {
    id: 1, ma_phieu_nhap: "PN-202611-000001", ncc_id: 1, ngay_nhap: "2026-11-16",
    ghi_chu: "", trang_thai: "nhap",
    chi_tiet: [{ id: 101, mat_hang_id: 1, so_luong: 50, don_gia_thuc: 100 }],
  };
  const state = { record, stock: 10, writes: [], confirmations: [], buttons: new Map() };
  const slots = [];
  let slot = 0;
  const ports = {
    React, base: "/kho/phieu-nhap", API: { receipts: "/api/v1/phieu_nhap" },
    useState: (initial) => {
      const index = slot++;
      if (!(index in slots)) slots[index] = typeof initial === "function" ? initial() : initial;
      return [slots[index], (value) => { slots[index] = value; }];
    },
    useNavigate: () => () => {},
    useFeedback: () => ({ confirm: (options) => state.confirmations.push(options), notify: () => {} }),
    useWrite: () => ({ mutateAsync: async (input) => {
      state.writes.push(input);
      return { data: { giao_dich_kho_ids: [1] } };
    } }),
    useSave: () => ({ save: () => {}, busy: false, error: null }),
    newLine: (line) => line,
    linePayload: (lines) => lines.map(({ mat_hang_id, so_luong, don_gia_thuc }) => ({
      mat_hang_id: Number(mat_hang_id), so_luong: Number(so_luong), don_gia_thuc: Number(don_gia_thuc),
    })),
    money: String, nullable: (value) => value || null,
    Badge: ({ status }) => React.createElement("span", null, status),
    Button: (props) => {
      state.buttons.set(props.children, props);
      return React.createElement("button", null, props.children);
    },
    Field: () => null, DocumentLines: () => null, SavedLines: () => null,
    ErrorNotice: () => null, QueryState: ({ children }) => children,
  };
  const Component = new Function(...Object.keys(ports), `${code}; return ReceiptEditor;`)(...Object.values(ports));
  renderToStaticMarkup(React.createElement(Component, {
    snapshot: { data: record, etag: '"draft-reviewed"' }, items: [], suppliers: { data: [] },
  }));
  const button = state.buttons.get("Hoàn tất nhập kho");
  assert.ok(button);
  assert.equal(button.reason, undefined);
  button.onClick();
  return state;
}

function confirmation(options) {
  const state = { buttons: new Map(), closed: false };
  const ports = {
    React: { ...React, createElement: (type, props, ...children) => {
      if (type === "dialog") state.cancel = props.onCancel;
      if (props?.["aria-label"] === "Đóng xác nhận") state.close = props.onClick;
      return React.createElement(type, props, ...children);
    } },
    useState: (initial) => [initial, () => {}], useRef: (value) => ({ current: value }), useEffect: () => {},
    Button: (props) => {
      state.buttons.set(props.children, props);
      return React.createElement("button", null, props.children);
    },
    Field: () => null, ErrorNotice: () => null,
  };
  const Component = new Function(...Object.keys(ports), `${confirmationCode}; return Confirmation;`)(...Object.values(ports));
  renderToStaticMarkup(React.createElement(Component, {
    options, onClose: () => { state.closed = true; },
  }));
  return state;
}

// UC-21 AC-1: Đóng bằng Hủy, nút X hoặc Escape không gọi API, giữ nháp và tồn 10
test("closing receipt confirmation leaves draft and stock untouched without API calls", () => {
  for (const action of ["cancel", "close", "escape"]) {
    const ui = editor();
    const before = structuredClone({ record: ui.record, stock: ui.stock });
    assert.equal(ui.confirmations.length, 1);
    const modal = confirmation(ui.confirmations[0]);
    if (action === "cancel") modal.buttons.get("Hủy").onClick();
    if (action === "close") modal.close();
    if (action === "escape") modal.cancel({ preventDefault() {} });
    assert.equal(modal.closed, true);
    assert.deepEqual(ui.writes, []);
    assert.deepEqual({ record: ui.record, stock: ui.stock }, before);
  }
});

// UC-21 R1: Chỉ xác nhận mới gửi yêu cầu hoàn tất với ETag của phiếu đã xem
test("completion API call is deferred until confirmation", async () => {
  const ui = editor();
  assert.deepEqual(ui.writes, []);
  const options = ui.confirmations[0];
  assert.equal(options.title, "Hoàn tất nhập kho");
  assert.match(options.description, /PN-202611-000001.*2026-11-16/);
  assert.deepEqual(options.content.props.lines, ui.record.chi_tiet);
  assert.match(options.impact, /Cộng số lượng từng mặt hàng vào kho/);
  await options.onConfirm();
  assert.deepEqual(ui.writes, [{
    path: "/api/v1/phieu_nhap/1/hoan_tat", method: "post", etag: '"draft-reviewed"',
  }]);
});
