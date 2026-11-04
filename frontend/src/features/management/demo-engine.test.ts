import assert from "node:assert/strict";
import test from "node:test";
import { DemoEngine } from "./demo-engine.ts";
import { initialWorkspace } from "./demo-data.ts";
import { calculatePlan, documentTotal } from "./planning.ts";
import type { Workspace } from "./types.ts";
const at = new Date("2026-11-04T02:00:00Z");
const clock = () => at;
const receipt = {
  date: "2026-11-04",
  supplierId: "supplier-an-phat",
  note: "",
  lines: [{ itemId: "frame", quantity: 20, price: 450000 }],
};
const requestInput = { productId: "mountain", quantity: 10, assigneeId: "employee-nam" };

test("receipt draft preserves stock; completion stores creator, stock timestamp and posts only once", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot();
  const draft = engine.saveReceipt(receipt);
  assert.equal(draft.status, "nhap");
  assert.equal(draft.creatorId, "manager-binh");
  assert.match(draft.code, /^PN-202611-\d{6}$/);
  assert.deepEqual(engine.snapshot().items, before.items);
  const posted = engine.confirmReceipt({ ...receipt, id: draft.id });
  assert.equal(posted.status, "hoan_thanh");
  assert.equal(engine.snapshot().items.find((item) => item.id === "frame")?.stock, 50);
  assert.equal(
    engine.snapshot().items.find((item) => item.id === "frame")?.stockUpdatedAt,
    at.toISOString(),
  );
  engine.confirmReceipt({ ...receipt, id: draft.id });
  assert.equal(engine.snapshot().items.find((item) => item.id === "frame")?.stock, 50);
  assert.throws(() => engine.saveReceipt({ ...receipt, id: draft.id }));
});
test("receipt accepts components and rejects manufactured output, inactive items and invalid dates", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  engine.saveReceipt({ ...receipt, lines: [{ itemId: "rim", quantity: 2, price: 123456 }] });
  for (const itemId of ["wheel", "mountain"])
    assert.throws(() =>
      engine.saveReceipt({ ...receipt, lines: [{ itemId, quantity: 1, price: 10 }] }),
    );
  for (const date of ["2026-02-30", "2026-13-01", "2026-1-1"])
    assert.throws(() => engine.saveReceipt({ ...receipt, date }));
  const state = initialWorkspace();
  const inactive = new DemoEngine({
    ...state,
    items: state.items.map((item) => (item.id === "frame" ? { ...item, active: false } : item)),
  });
  assert.throws(() => inactive.confirmReceipt(receipt));
  assert.equal(inactive.snapshot().receipts.length, 0);
});
test("nullable-assignee draft is saved and preview resolves versioned BOMs without reserving stock", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot().items;
  const request = engine.createRequest({ ...requestInput, assigneeId: null });
  assert.equal(request.status, "nhap");
  assert.equal(request.assigneeId, null);
  const preview = engine.previewRequest(request.id);
  assert.equal(preview.plan.bikesToMake, 7);
  assert.equal(preview.plan.wheelsToMake, 10);
  assert.equal(preview.plan.bikeBomId, "bom-mountain-v2");
  assert.equal(preview.plan.wheelMaterials.find((line) => line.itemId === "spokes")?.required, 360);
  assert.throws(() => engine.sendRequest(request.id, preview.token));
  assert.deepEqual(engine.snapshot().items, before);
});
test("sending short-material request generates draft parent and child with frozen direct demand", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot().items;
  const request = engine.createRequest(requestInput);
  const preview = engine.previewRequest(request.id);
  const sent = engine.sendRequest(request.id, preview.token);
  assert.equal(sent.status, "cho_bo_sung_vat_tu");
  const orders = engine.snapshot().orders.filter((order) => order.requestId === request.id);
  assert.equal(orders.length, 2);
  const parent = orders.find((order) => order.parentOrderId === null)!;
  const child = orders.find((order) => order.parentOrderId === parent.id)!;
  assert.equal(parent.quantity, 7);
  assert.equal(child.quantity, 10);
  assert.equal(parent.bomId, "bom-mountain-v2");
  assert.equal(child.bomId, "bom-wheel-v1");
  assert.equal(parent.status, "nhap");
  assert.equal(parent.assigneeId, null);
  assert.equal(
    parent.demand.some((line) => line.itemId === "spokes"),
    false,
  );
  assert.equal(child.demand.find((line) => line.itemId === "spokes")?.required, 360);
  assert.throws(() => engine.sendRequest(request.id, preview.token));
  assert.deepEqual(engine.snapshot().items, before);
});
test("editing draft, stock changes, and token expiry require a new preview", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const request = engine.createRequest(requestInput);
  const first = engine.previewRequest(request.id);
  engine.updateRequest(request.id, { ...requestInput, quantity: 11 });
  assert.throws(() => engine.sendRequest(request.id, first.token));
  const second = engine.previewRequest(request.id);
  engine.confirmReceipt(receipt);
  assert.throws(() => engine.sendRequest(request.id, second.token));
  let now = new Date(at);
  const expiring = new DemoEngine(initialWorkspace(), () => now);
  const draft = expiring.createRequest(requestInput);
  const preview = expiring.previewRequest(draft.id);
  now = new Date(at.getTime() + 600001);
  assert.throws(() => expiring.sendRequest(draft.id, preview.token));
});
test("stocked finished goods need no BOM and generate no orders", () => {
  const base = initialWorkspace();
  const engine = new DemoEngine({ ...base, boms: [] }, clock);
  const request = engine.createRequest({
    productId: "city",
    quantity: 2,
    assigneeId: "employee-an",
  });
  const preview = engine.previewRequest(request.id);
  assert.equal(preview.plan.bikeBomId, null);
  assert.equal(preview.plan.wheelBomId, null);
  assert.equal(engine.sendRequest(request.id, preview.token).status, "da_gui");
  assert.equal(
    engine.snapshot().orders.some((order) => order.requestId === request.id),
    false,
  );
});

test("missing production BOM permits draft but blocks preview without creating orders", () => {
  const base = initialWorkspace();
  const engine = new DemoEngine({ ...base, boms: [] }, clock);
  const draft = engine.createRequest(requestInput);
  assert.equal(draft.status, "nhap");
  assert.equal(draft.plan, null);
  const before = engine.snapshot();
  assert.throws(() => engine.previewRequest(draft.id), /BOM/);
  assert.deepEqual(engine.snapshot(), before);
});

test("inactive direct BOM items block generated documents without changing draft", () => {
  const base = initialWorkspace();
  const engine = new DemoEngine(
    {
      ...base,
      items: base.items.map((item) => (item.id === "rim" ? { ...item, active: false } : item)),
    },
    clock,
  );
  const draft = engine.createRequest(requestInput);
  const before = engine.snapshot();
  assert.throws(() => engine.previewRequest(draft.id), /ngừng hoạt động/);
  assert.deepEqual(engine.snapshot(), before);
});
test("sufficient wheel stock avoids child order and child BOM lookup", () => {
  const base = initialWorkspace();
  const state: Workspace = {
    ...base,
    items: base.items.map((item) => (item.id === "wheel" ? { ...item, stock: 100 } : item)),
    boms: base.boms.filter((bom) => bom.outputId !== "wheel"),
  };
  const plan = calculatePlan(state.items, "mountain", 10, state.boms);
  assert.equal(plan.wheelsToMake, 0);
  assert.equal(plan.wheelBomId, null);
  const engine = new DemoEngine(state, clock);
  const request = engine.createRequest(requestInput);
  engine.sendRequest(request.id, engine.previewRequest(request.id).token);
  assert.equal(
    engine.snapshot().orders.filter((order) => order.requestId === request.id).length,
    1,
  );
});
test("draft orders accept active employees only; send allowed despite insufficient material", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot().items;
  assert.throws(() => engine.sendOrder("order-106"));
  assert.throws(() => engine.assignOrder("order-106", "manager-binh"));
  assert.equal(engine.assignOrder("order-106", "employee-huy").assigneeId, "employee-huy");
  assert.equal(engine.sendOrder("order-106").status, "da_gui");
  assert.throws(() => engine.assignOrder("order-106", "employee-nam"));
  assert.deepEqual(engine.snapshot().items, before);
});
test("approval snapshots catalog price, stock before/after, and never posts a second time", () => {
  const base = initialWorkspace();
  const engine = new DemoEngine(
    {
      ...base,
      items: base.items.map((item) => (item.id === "frame" ? { ...item, price: 500001 } : item)),
    },
    clock,
  );
  assert.equal(
    documentTotal(engine.snapshot().issues.find((issue) => issue.id === "issue-26")!.lines),
    null,
  );
  engine.approveIssue("issue-26");
  const posted = engine.snapshot();
  const issue = posted.issues.find((issue) => issue.id === "issue-26")!;
  assert.equal(issue.status, "da_duyet");
  assert.equal(issue.lines[0].price, 500001);
  assert.equal(documentTotal(issue.lines), 5740007);
  assert.equal(posted.items.find((item) => item.id === "frame")?.stock, 23);
  assert.equal(posted.items.find((item) => item.id === "fork")?.stock, 11);
  engine.approveIssue("issue-26");
  assert.deepEqual(engine.snapshot(), posted);
  engine.confirmReceipt(receipt);
  assert.deepEqual(
    engine.snapshot().issues.find((entry) => entry.id === issue.id)?.posting,
    issue.posting,
  );
});
test("short stock, excess direct demand, waiting finished-goods source fail atomically", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot();
  assert.throws(() => engine.approveIssue("issue-29"));
  assert.throws(() => engine.approveIssue("issue-28"));
  assert.deepEqual(engine.snapshot(), before);
  const over = {
    ...before,
    issues: before.issues.map((issue) =>
      issue.id === "issue-26"
        ? { ...issue, lines: [{ itemId: "frame", quantity: 8, price: null }] }
        : issue,
    ),
  };
  const overEngine = new DemoEngine(over);
  assert.throws(() => overEngine.approveIssue("issue-26"));
  assert.deepEqual(overEngine.snapshot(), over);
});
test("direct demand cap counts every previously approved issue for same order", () => {
  const base = initialWorkspace();
  const repeated = {
    ...base.issues.find((issue) => issue.id === "issue-26")!,
    id: "issue-repeat",
    code: "PX-202611-000099",
  };
  const engine = new DemoEngine({ ...base, issues: [...base.issues, repeated] });
  engine.approveIssue("issue-26");
  const posted = engine.snapshot();
  assert.throws(() => engine.approveIssue("issue-repeat"));
  assert.deepEqual(engine.snapshot(), posted);
});
test("finished-goods posting advances request to completed at requested quantity", () => {
  const base = initialWorkspace();
  const state = {
    ...base,
    requests: base.requests.map((request) =>
      request.id === "request-1" ? { ...request, quantity: 3, status: "da_gui" as const } : request,
    ),
  };
  const engine = new DemoEngine(state, clock);
  engine.approveIssue("issue-28");
  assert.equal(
    engine.snapshot().requests.find((request) => request.id === "request-1")?.status,
    "hoan_thanh",
  );
  assert.equal(engine.snapshot().items.find((item) => item.id === "mountain")?.stock, 0);
});
test("receipt rechecks residual direct demand without rewriting saved BOM or orders", () => {
  const base = initialWorkspace();
  const order = base.orders.find((order) => order.id === "order-108")!;
  const state: Workspace = {
    ...base,
    orders: [{ ...order, demand: [{ itemId: "spokes", perUnit: 1, required: 360 }] }],
    requests: base.requests.filter((request) => request.id === "request-1"),
    issues: [],
  };
  const engine = new DemoEngine(state, clock);
  const before = engine.snapshot().orders;
  engine.confirmReceipt({ ...receipt, lines: [{ itemId: "spokes", quantity: 60, price: 1800 }] });
  assert.equal(engine.snapshot().requests[0].status, "da_gui");
  assert.deepEqual(engine.snapshot().orders, before);
});
test("rejection saves nonempty reason and null prices, leaves stock intact", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot().items;
  assert.throws(() => engine.rejectIssue("issue-27", "  "));
  engine.rejectIssue("issue-27", "  Chưa cần cấp cụm bánh.  ");
  const issue = engine.snapshot().issues.find((issue) => issue.id === "issue-27")!;
  assert.equal(issue.status, "tu_choi");
  assert.equal(issue.reason, "Chưa cần cấp cụm bánh.");
  assert.equal(issue.lines[0].price, null);
  assert.deepEqual(engine.snapshot().items, before);
});
test("invalid quantity, duplicate rows and tampered foreign IDs never mutate state", () => {
  const engine = new DemoEngine(initialWorkspace(), clock);
  const before = engine.snapshot();
  for (const quantity of [0, -1, 1.5, NaN])
    assert.throws(() =>
      engine.saveReceipt({ ...receipt, lines: [{ ...receipt.lines[0], quantity }] }),
    );
  assert.throws(() =>
    engine.saveReceipt({ ...receipt, lines: [...receipt.lines, ...receipt.lines] }),
  );
  assert.throws(() => engine.saveReceipt({ ...receipt, supplierId: "unknown" }));
  assert.throws(() => engine.createRequest({ ...requestInput, assigneeId: "manager-binh" }));
  assert.deepEqual(engine.snapshot(), before);
});
