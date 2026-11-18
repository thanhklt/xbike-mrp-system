import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const prefillFile = new URL("../src/features/receiving/receiptPrefill.js", import.meta.url);
const { outputFiles } = await build({
  entryPoints: [fileURLToPath(prefillFile)],
  bundle: true,
  format: "esm",
  outdir: "out",
  write: false,
});
const bundle = outputFiles.find(({ path }) => path.endsWith(".js"));
const { prefillReceipt } = await import(`data:text/javascript,${encodeURIComponent(bundle.text)}`);
const receiving = readFileSync(new URL("../src/features/receiving/ReceivingPage.jsx", import.meta.url), "utf8");
const requests = readFileSync(new URL("../src/features/production/RequestsPage.jsx", import.meta.url), "utf8");
const request = {
  id: 1,
  ma_yeu_cau_san_xuat: "YCSX-202611-000001",
  da_du: false,
  linh_kien_thieu: [
    { mat_hang_id: 2, so_luong_can: 15, so_luong_thieu: 10 },
    { mat_hang_id: 3, so_luong_can: 12, so_luong_thieu: 4 },
  ],
};

// UC-27 AC-1: Điền sẵn linh kiện thiếu
test("prefill uses the missing quantities, catalog prices, and request code", () => {
  const items = [{ id: 3, don_gia: 120 }, { id: 2, don_gia: 350 }];
  const before = structuredClone({ request, items });

  const { ghi_chu, lines } = prefillReceipt(request, items);

  assert.equal(ghi_chu, "Bổ sung linh kiện cho YCSX-202611-000001");
  assert.deepEqual(lines.map(({ mat_hang_id, so_luong, don_gia_thuc }) => ({
    mat_hang_id, so_luong, don_gia_thuc,
  })), [
    { mat_hang_id: "2", so_luong: "10", don_gia_thuc: "350" },
    { mat_hang_id: "3", so_luong: "4", don_gia_thuc: "120" },
  ]);
  assert.ok(lines.every(({ key }) => key));
  assert.notEqual(lines[0].key, lines[1].key);
  assert.deepEqual({ request, items }, before);
});

// UC-20 A1: Dùng giá 0 khi danh mục thiếu giá hoặc mặt hàng
test("prefill uses zero for a missing item or price", () => {
  const { lines } = prefillReceipt(request, [{ id: 2, don_gia: null }]);
  assert.deepEqual(lines.map(({ don_gia_thuc }) => don_gia_thuc), ["0", "0"]);
});

// UC-20 A1: Mở form trống khi yêu cầu không còn linh kiện thiếu
test("prefill is absent for a missing request, replenished request, or no shortages", () => {
  for (const entry of [undefined, { ...request, da_du: true }, { ...request, linh_kien_thieu: [] }]) {
    assert.equal(prefillReceipt(entry, []), null);
  }
  assert.match(receiving, /prefillMissing=\{shouldPrefill && prefill === null\}/);
  assert.match(receiving, /const \[prefillMissing\] = useState\(initialPrefillMissing\)/);
  assert.match(receiving, /\{prefillMissing && \(\s*<Notice>Yêu cầu này không còn linh kiện thiếu\. Phiếu nhập được tạo trống\.<\/Notice>\s*\)\}/);
});

// UC-20 A1: Chỉ tra yêu cầu khi mở form tạo từ đường dẫn bổ sung
test("receipt creation reads the shortage for the requested id and resets when the id changes", () => {
  assert.match(receiving, /const requestId = search\.get\("yeu_cau_san_xuat_id"\)/);
  assert.match(receiving, /const shouldPrefill = id === "moi" && requestId !== null/);
  assert.match(receiving, /useResource\(API\.shortages, \{\}, shouldPrefill\)/);
  assert.match(receiving, /yeu_cau\?\.find\(\s*\(entry\) => entry\.id === Number\(requestId\)/);
  assert.match(receiving, /prefillReceipt\(request, items\)/);
  assert.match(receiving, /key=\{shouldPrefill \? requestId : undefined\}/);
  assert.match(receiving, /shouldPrefill \? <QueryState query=\{shortages\}>\{editor\}<\/QueryState> : editor/);
  assert.match(receiving, /ghi_chu: record \? record\.ghi_chu \|\| "" : prefill\?\.ghi_chu \?\? ""/);
  assert.match(receiving, /\) \|\| prefill\?\.lines \|\| \[newLine\(\)\]/);
});

// UC-20 A1: Lưu phiếu nhập độc lập với yêu cầu sản xuất
test("receipt submit keeps the existing POST body", () => {
  const submit = receiving.match(/function submit\(event\) \{([\s\S]*?)\n  \}/)?.[1];
  assert.ok(submit);
  const body = submit.match(/const body = \{([\s\S]*?)\};/)?.[1];
  assert.ok(body);
  assert.deepEqual([...body.matchAll(/^\s*(\w+):/gm)].map(([, key]) => key), [
    "ncc_id", "ngay_nhap", "ghi_chu", "chi_tiet",
  ]);
  assert.doesNotMatch(submit, /yeu_cau_san_xuat_id/);
  assert.match(submit, /method: record \? "patch" : "post",\s*body,/);
});

// UC-20 A1: Quản lý kho mở form từ chi tiết yêu cầu đang chờ bổ sung
test("request details link to receipt creation only in the manager's waiting request actions", () => {
  assert.match(requests, /const manager = user\.ma_vai_tro === "quan_ly"/);
  assert.match(requests, /\{canCancelRequest\(record, manager\) && \(\s*<div className="actions">\s*<Button\b[^>]*>[\s\S]*?Hủy yêu cầu…\s*<\/Button>\s*\{record\.trang_thai === "cho_bo_sung_linh_kien" && \(\s*<Link\s+className="btn btn-secondary"\s+to=\{`\/kho\/phieu-nhap\/moi\?yeu_cau_san_xuat_id=\$\{record\.id\}`\}\s*>\s*Lập phiếu nhập bổ sung\s*<\/Link>\s*\)\}/);
  assert.equal((requests.match(/Lập phiếu nhập bổ sung/g) || []).length, 1);
});
