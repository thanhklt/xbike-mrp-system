import assert from "node:assert/strict";
import test from "node:test";
import { DemoEngine } from "./demo-engine.ts";

const receipt = {
  date: "2026-11-03",
  supplier: "Công ty Linh kiện An Phát",
  note: "",
  lines: [{ itemId: "frame", quantity: 20, price: 450000 }],
};

test("a saved draft does not affect stock, confirmation posts exactly once", () => {
  const engine = new DemoEngine();
  const initial = engine.snapshot().items.find((item) => item.id === "frame")!.stock;
  const draft = engine.saveReceipt(receipt);
  assert.equal(engine.snapshot().items.find((item) => item.id === "frame")!.stock, initial);
  engine.confirmReceipt({ ...receipt, id: draft.id });
  engine.confirmReceipt({ ...receipt, id: draft.id });
  assert.equal(engine.snapshot().items.find((item) => item.id === "frame")!.stock, initial + 20);
  assert.throws(() => engine.saveReceipt({ ...receipt, id: draft.id }));
});

test("creating demand computes two BOM levels and does not reserve stock", () => {
  const engine = new DemoEngine();
  const before = engine.snapshot().items;
  const request = engine.createRequest({
    productId: "mountain",
    quantity: 10,
    reference: "",
    assignee: "Lê Hoàng Nam",
    note: "",
  });
  assert.equal(request.plan.bikesToMake, 7);
  assert.equal(request.plan.wheelsToMake, 10);
  assert.equal(request.plan.wheelMaterials.find((line) => line.itemId === "spokes")!.required, 360);
  assert.deepEqual(engine.snapshot().items, before);
});

test("confirmed receipts retain their recorded before/after balances after later issues", () => {
  const engine = new DemoEngine();
  const confirmed = engine.confirmReceipt(receipt);
  engine.approveIssue("issue-26");
  assert.deepEqual(engine.snapshot().receipts.find((entry) => entry.id === confirmed.id)?.posting, [
    { itemId: "frame", before: 30, after: 50 },
  ]);
  assert.equal(engine.snapshot().items.find((item) => item.id === "frame")!.stock, 43);
});

test("work orders can be created with missing materials but cannot exceed the request", () => {
  const engine = new DemoEngine();
  const before = engine.snapshot().items;
  const payload = {
    requestId: "request-1",
    kind: "bike" as const,
    quantity: 7,
    assignee: "Lê Hoàng Nam",
    note: "",
  };
  engine.createOrder(payload);
  assert.deepEqual(engine.snapshot().items, before);
  assert.throws(() => engine.createOrder(payload));
});

test("approval validates every line and does not partially post insufficient inventory", () => {
  const engine = new DemoEngine();
  const before = engine.snapshot();
  assert.throws(() => engine.approveIssue("issue-29"));
  assert.deepEqual(engine.snapshot(), before);
});

test("approval decrements each stock once and retries return the approved result", () => {
  const engine = new DemoEngine();
  engine.approveIssue("issue-26");
  const posted = engine.snapshot();
  assert.equal(posted.items.find((item) => item.id === "frame")!.stock, 23);
  assert.equal(posted.items.find((item) => item.id === "fork")!.stock, 11);
  engine.approveIssue("issue-26");
  assert.deepEqual(engine.snapshot(), posted);
  assert.throws(() => engine.rejectIssue("issue-26", "Đã duyệt"));
});

test("rejection requires a reason and never changes stock", () => {
  const engine = new DemoEngine();
  const before = engine.snapshot().items;
  assert.throws(() => engine.rejectIssue("issue-27", "  "));
  engine.rejectIssue("issue-27", "Chưa cần cấp cụm bánh.");
  assert.equal(
    engine.snapshot().issues.find((issue) => issue.id === "issue-27")!.status,
    "rejected",
  );
  assert.deepEqual(engine.snapshot().items, before);
});

test("invalid quantities, duplicate lines, and tampered catalog values are rejected", () => {
  const engine = new DemoEngine();
  for (const quantity of [0, -1, 1.5, NaN]) {
    assert.throws(() =>
      engine.saveReceipt({ ...receipt, lines: [{ ...receipt.lines[0], quantity }] }),
    );
  }
  assert.throws(() =>
    engine.saveReceipt({ ...receipt, lines: [...receipt.lines, ...receipt.lines] }),
  );
  assert.throws(() =>
    engine.saveReceipt({ ...receipt, lines: [{ ...receipt.lines[0], itemId: "mountain" }] }),
  );
});
