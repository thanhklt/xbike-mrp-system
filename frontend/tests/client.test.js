import assert from "node:assert/strict";
import { test } from "node:test";
import { apiClient, readAll, readResource, TOKEN_KEY, writeResource } from "../src/lib/api/client.js";
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

test("bodyless v4 endpoints send zero request bytes while empty action objects remain JSON", async () => {
  const calls = [];
  apiClient.defaults.adapter = async (config) => {
    calls.push(config);
    return { config, status: 204, headers: {}, data: "" };
  };
  await writeResource({ path: "/bom/1", method: "delete", body: null, etag: '"v1"' });
  await writeResource({ path: "/bom/1/kich_hoat", body: {}, etag: '"v2"' });
  assert.equal(calls[0].data, undefined);
  assert.equal(calls[0].headers["If-Match"], '"v1"');
  assert.equal(calls[1].data, "{}");
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

const expiredMessage = "Could not validate credentials";
const disabledMessage = "Tài khoản đã bị vô hiệu hóa";
for (const { name, status, data, detail } of [
  {
    name: "authenticated 401 ends the session without a message",
    status: 401,
    data: { detail: expiredMessage },
    detail: undefined,
  },
  {
    name: "disabled account 403 ends the session with its message",
    status: 403,
    data: { error: { code: "tai_khoan_bi_vo_hieu_hoa", message: disabledMessage } },
    detail: disabledMessage,
  },
]) {
  test(name, async (t) => {
    const eventName = "xbike:session-ended";
    const details = [];
    const onSessionEnded = (event) => details.push(event.detail);
    const originalAdapter = apiClient.defaults.adapter;
    store.set(TOKEN_KEY, "test-token");
    window.addEventListener(eventName, onSessionEnded);
    t.after(() => {
      window.removeEventListener(eventName, onSessionEnded);
      store.delete(TOKEN_KEY);
      apiClient.defaults.adapter = originalAdapter;
    });
    apiClient.defaults.adapter = async (config) => {
      assert.equal(config.headers.Authorization, "Bearer test-token");
      throw Object.assign(new Error("Request failed"), { config, response: { status, data } });
    };

    await assert.rejects(readResource("/auth/me"), { status });
    assert.deepEqual(details, [detail]);
  });
}
