import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";

// Run the pure TypeScript demo rules with the project's existing compiler; no test dependency.
const model = new URL("../src/features/operations/model.ts", import.meta.url);
const output = ts.transpileModule(readFileSync(model, "utf8"), {
  compilerOptions: {
    target: ts.ScriptTarget.ES2020,
    module: ts.ModuleKind.CommonJS,
    esModuleInterop: true,
  },
}).outputText;
const exports = {};
vm.runInNewContext(output, {
  exports,
  require: createRequire(model),
  structuredClone,
  Date,
  Map,
  Set,
  Intl,
});
const {
  initial,
  stock,
  effective,
  saveItem,
  adjustmentLines,
  confirmAdjustment,
  orderBlock,
  changeOrder,
} = exports;
let checks = 0;
const test = (name, run) => {
  run();
  checks++;
  console.log(`PASS ${name}`);
};
test("initial ledger reconciles", () => {
  assert.equal(stock(initial, 1), 211);
  assert.equal(effective(initial, 501), 495);
  assert.ok(initial.items.every((item) => stock(initial, item.id) >= 0));
});
test("confirm draft updates stock once and locks document", () => {
  const db = structuredClone(initial);
  confirmAdjustment(db, "Q", 303);
  assert.equal(stock(db, 1), 206);
  assert.equal(effective(db, 501), 490);
  assert.equal(db.adjustments[0].trang_thai, "da_xac_nhan");
  assert.throws(() => confirmAdjustment(db, "Q", 303));
  assert.equal(stock(db, 1), 206);
});
test("negative stock rolls back ALL ledger lines and creates one ticket", () => {
  const db = structuredClone(initial);
  db.adjustments[0].chi_tiet = adjustmentLines(
    db,
    [
      { source: 501, quantity: 0 },
      { source: 502, quantity: 1210 },
    ],
    41,
  );
  const ledger = JSON.stringify(db.ledger);
  confirmAdjustment(db, "Q", 303);
  assert.equal(JSON.stringify(db.ledger), ledger);
  assert.equal(db.adjustments[0].trang_thai, "loi");
  assert.equal(db.tickets.length, initial.tickets.length + 1);
  assert.equal(db.tickets.at(-1).chi_tiet.length, 2);
  assert.throws(() => confirmAdjustment(db, "Q", 303));
  assert.equal(db.tickets.length, initial.tickets.length + 1);
});
test("quantity, duplicate source, source receipt and zero delta validation", () => {
  for (const quantity of [-1, 1.5, NaN, Number.MAX_SAFE_INTEGER + 1, 495]) {
    assert.throws(() => adjustmentLines(initial, [{ source: 501, quantity }], 41));
  }
  assert.throws(() => adjustmentLines(initial, [], 41));
  assert.throws(() => adjustmentLines(initial, [{ source: 501, quantity: 490 }], 99));
  assert.throws(() =>
    adjustmentLines(
      initial,
      [
        { source: 501, quantity: 490 },
        { source: 501, quantity: 480 },
      ],
      41,
    ),
  );
  assert.equal(adjustmentLines(initial, [{ source: 501, quantity: 0 }], 41)[0].so_luong_dung, 0);
});
test("confirmation recalculates effective quantity", () => {
  const db = structuredClone(initial);
  db.adjustments[0].chi_tiet[0].so_luong_hieu_luc_truoc = 500;
  confirmAdjustment(db, "Q", 303);
  assert.equal(db.adjustments[0].chi_tiet[0].so_luong_bien_dong, -5);
});
test("N and A cannot change stock or items", () => {
  for (const role of ["N", "A"]) {
    const db = structuredClone(initial);
    assert.throws(() => confirmAdjustment(db, role, 303));
    assert.throws(() => saveItem(db, role, db.items[0]));
    assert.equal(JSON.stringify(db), JSON.stringify(initial));
  }
});
test("referenced identity immutable; price remains editable", () => {
  const db = structuredClone(initial);
  assert.throws(() => saveItem(db, "Q", { ...db.items[0], sku: "NEW" }));
  assert.throws(() => saveItem(db, "Q", { ...db.items[0], don_vi_tinh: "bo" }));
  saveItem(db, "Q", { ...db.items[0], don_gia: 0 });
  assert.equal(db.items[0].don_gia, 0);
  assert.equal(stock(db, 1), 211);
  assert.throws(() => saveItem(db, "Q", { ...db.items[0], id: 100, ma_mat_hang: "MH-000100" }));
});
test("inactive items blocked in new adjustments", () => {
  const db = structuredClone(initial);
  db.items[0].is_active = false;
  assert.throws(() => adjustmentLines(db, [{ source: 501, quantity: 490 }], 41));
});
test("assignment required; send allowed before materials supplied", () => {
  const db = structuredClone(initial);
  assert.throws(() => changeOrder(db, "Q", 105, "send", ""));
  changeOrder(db, "Q", 105, "assign", "21");
  changeOrder(db, "Q", 105, "send", "");
  assert.equal(db.orders.find((x) => x.id === 105).trang_thai, "da_gui");
  assert.throws(() => changeOrder(db, "N", 105, "start", ""));
});
test("only assigned N starts a fully supplied order; stock unchanged", () => {
  const db = structuredClone(initial);
  const ledger = JSON.stringify(db.ledger);
  assert.throws(() => changeOrder(db, "Q", 108, "start", ""));
  assert.throws(() => changeOrder(db, "N", 104, "start", ""));
  changeOrder(db, "N", 108, "start", "");
  assert.equal(db.orders.find((x) => x.id === 108).trang_thai, "dang_thuc_hien");
  assert.equal(JSON.stringify(db.ledger), ledger);
});
test("cancel refuses supplied, completed and active child orders", () => {
  const db = structuredClone(initial);
  for (const id of [101, 104, 106])
    assert.ok(
      orderBlock(
        db,
        "Q",
        db.orders.find((x) => x.id === id),
        "cancel",
      ),
    );
  assert.throws(() => changeOrder(db, "Q", 103, "cancel", "  "));
  changeOrder(db, "Q", 103, "cancel", "No longer needed");
  assert.equal(db.orders.find((x) => x.id === 103).trang_thai, "da_huy");
});
console.log(`${checks} domain checks passed.`);
