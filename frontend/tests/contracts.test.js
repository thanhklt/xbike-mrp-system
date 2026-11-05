import assert from "node:assert/strict";
import { test } from "node:test";
import {
  cleanParams,
  normalizeResponse,
  auditParams,
  toApiError,
  versionHeaders,
} from "../src/lib/api/contract.js";
import { documentPermissions, homeFor, isAllowed } from "../src/features/auth/permissions.js";
import { dateTime, localDateTime, money } from "../src/lib/format.js";

test("query preserves zero and false while omitting absent filters", () => {
  assert.deepEqual(
    cleanParams({ price: 0, active: false, q: "", page: 1, missing: null, optional: undefined }),
    { price: 0, active: false, page: 1 },
  );
});
test("normalizes legacy pagination without treating one page length as total", () => {
  const response = normalizeResponse({
    data: {
      data: [{ id: 1 }],
      pagination: { page: 2, page_size: 20, total_items: 81, total_pages: 5 },
    },
    headers: {},
  });
  assert.equal(response.meta.total, 81);
  assert.equal(response.meta.page, 2);
});
test("preserves contract meta and strong ETag", () => {
  const result = normalizeResponse({
    data: { data: { id: 9 }, meta: { request_id: "request-9" } },
    headers: { etag: '"revision-2"' },
  });
  assert.equal(result.etag, '"revision-2"');
  assert.equal(result.meta.request_id, "request-9");
});
test("audit adapter translates only to parameters supported by legacy endpoint", () => {
  assert.deepEqual(auditParams({ page: 2, page_size: 20, q: "phiếu", sort: "-created_at" }), {
    page: 2,
    page_size: 20,
    search: "phiếu",
    sort_by: "created_at",
    sort_order: "desc",
  });
});
test("missing weak or wildcard version cannot authorize a write", () => {
  for (const version of [null, undefined, "", 'W/"stale"', "*"])
    assert.throws(
      () => versionHeaders(version),
      (error) => error.status === 428,
    );
  assert.deepEqual(versionHeaders('"reviewed-version"'), { "If-Match": '"reviewed-version"' });
});
test("412 errors instruct reloading and reconfirming", () => {
  const error = toApiError({ response: { status: 412, data: {} } });
  assert.match(error.message, /Tải lại/);
});
test("failed writes with unknown outcome are distinguished from failed reads", () => {
  assert.equal(toApiError({ config: { method: "post" } }).uncertain, true);
  assert.equal(toApiError({ config: { method: "get" } }).uncertain, false);
});
test("ticket link is only offered when backend confirms the ticket was committed", () => {
  assert.equal(
    toApiError({
      response: { status: 409, data: { error: { ticket_id: 4, ticket_da_luu: false } } },
    }).ticketId,
    null,
  );
  assert.equal(
    toApiError({
      response: { status: 409, data: { error: { ticket_id: 4, ticket_da_luu: true } } },
    }).ticketId,
    4,
  );
});
test("admin does not inherit warehouse privileges", () => {
  assert.equal(isAllowed("quan_tri_vien", ["quan_ly", "nhan_vien"]), false);
  assert.equal(
    documentPermissions("issue", "quan_tri_vien", { trang_thai: "cho_duyet" }, 1).approve,
    false,
  );
  assert.equal(homeFor("unknown"), "/403");
});
test("employees can neither create issue documents nor edit someone else's completion", () => {
  assert.equal(documentPermissions("issue", "nhan_vien", { trang_thai: "nhap" }, 3).create, false);
  assert.equal(
    documentPermissions("completion", "nhan_vien", { trang_thai: "nhap", nhan_vien_id: 4 }, 3).edit,
    false,
  );
});
test("posted documents stay immutable and rejected completion can return to draft", () => {
  assert.equal(documentPermissions("issue", "quan_ly", { trang_thai: "da_duyet" }, 2).edit, false);
  assert.equal(
    documentPermissions("completion", "nhan_vien", { trang_thai: "tu_choi", nhan_vien_id: 3 }, 3)
      .returnDraft,
    true,
  );
});
test("timestamps display in Vietnam time independently of browser or runner timezone", () => {
  assert.equal(localDateTime("2026-11-04T18:05:00Z"), "2026-11-05T01:05");
  assert.match(dateTime("2026-11-04T18:05:00Z"), /01:05/);
  assert.equal(money(null), "Chưa chốt");
  assert.match(money(0), /0/);
});
