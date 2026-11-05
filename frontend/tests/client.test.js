import assert from "node:assert/strict";
import { test } from "node:test";
import { apiClient, readAll, readResource, writeResource } from "../src/lib/api/client.js";
const store = new Map();
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: { getItem: (key) => store.get(key) || null },
});
globalThis.window = new EventTarget();
function respond(config, data, meta = {}) {
  return { config, status: 200, data: { data, meta }, headers: { etag: '"response-version"' } };
}
test("writes send the version reviewed by the user without fetching a fresh version", async () => {
  const calls = [];
  apiClient.defaults.adapter = async (config) => {
    calls.push(config);
    return respond(config, { id: 1 });
  };
  await writeResource({ path: "/phieu_xuat/1/duyet", etag: '"reviewed"' });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].headers["If-Match"], '"reviewed"');
  assert.equal(calls[0].method, "post");
});
test("DELETE preserves required reason body and If-Match", async () => {
  let request;
  apiClient.defaults.adapter = async (config) => {
    request = config;
    return { config, status: 204, headers: {}, data: "" };
  };
  await writeResource({
    path: "/nhan_vien/3",
    method: "delete",
    body: { ly_do: "Nghỉ việc" },
    etag: '"v1"',
  });
  assert.deepEqual(JSON.parse(request.data), { ly_do: "Nghỉ việc" });
  assert.equal(request.headers["If-Match"], '"v1"');
});
test("choices fetch every page instead of truncating at the server page limit", async () => {
  apiClient.defaults.adapter = async (config) =>
    respond(config, [{ id: config.params.page }], { total: 201, total_pages: 3 });
  const rows = await readAll("/nha_cung_cap");
  assert.deepEqual(
    rows.map((row) => row.id),
    [1, 2, 3],
  );
});
test("cancellation signal reaches the HTTP request", async () => {
  const controller = new AbortController();
  apiClient.defaults.adapter = async (config) => {
    assert.equal(config.signal, controller.signal);
    return respond(config, []);
  };
  await readResource("/mat_hang", {}, controller.signal);
});
test("BOM and supplier creates do not send If-Match", async () => {
  apiClient.defaults.adapter = async (config) => {
    assert.equal(config.headers["If-Match"], undefined);
    return respond(config, { id: 1 });
  };
  await writeResource({ path: "/bom", versioned: false });
});
