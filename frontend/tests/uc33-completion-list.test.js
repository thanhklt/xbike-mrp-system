import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import React from "react";
import { ArrowDownUp, CalendarDays, ChevronDown, ChevronUp, Filter, LayoutGrid, Layers, Search } from "lucide-react";
import { renderToStaticMarkup } from "react-dom/server";
import { transformWithEsbuild } from "vite";
import { completionListFilters } from "../src/features/production/completionForm.js";
import { REQUEST_TYPES, REQUEST_TYPE_LABELS } from "../src/features/production/requestForm.js";
import { dateFilters, dateRangeError } from "../src/components/filterFields.js";
import { canAccessPath } from "../src/features/auth/permissions.js";
import { navigationFor } from "../src/layouts/navigation.js";
import { API } from "../src/lib/api/endpoints.js";
import { apiClient, readResource } from "../src/lib/api/client.js";
import { dateTime, employeeName, itemName, number, STATUS_LABELS } from "../src/lib/format.js";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const source = read("features/production/CompletionListPage.jsx");
const routes = read("routes/index.jsx");
const items = [
  { id: 5, ma_mat_hang: "MH-5", ten_mat_hang: "Xe đạp", loai_mat_hang: "thanh_pham" },
  { id: 6, ma_mat_hang: "MH-6", ten_mat_hang: "Khung", loai_mat_hang: "linh_kien" },
  { id: 7, ma_mat_hang: "MH-7", ten_mat_hang: "Xe trẻ em", loai_mat_hang: "thanh_pham" },
];
const employees = [
  { id: 20, ma_nhan_vien: "NV-20", ho_ten: "Nguyễn An" },
  { id: 21, ma_nhan_vien: "NV-21", ho_ten: "Trần Bình" },
];
const row = {
  id: 12, ma_phieu: "HTSX-202611-000012", yeu_cau_san_xuat_id: 101,
  ma_yeu_cau_san_xuat: "YCSX-202611-000101", mat_hang_id: 5, nhan_vien_id: 20,
  loai_yeu_cau: "nhap_kho", so_luong_hoan_thanh: 7,
  finish_time: "2026-11-15T17:00:00Z", trang_thai: "cho_duyet",
};

async function compile(input, filename) {
  const { code } = await transformWithEsbuild(input
    .replace(/^import[\s\S]*?;\s*/gm, "")
    .replace(/^export \{[^}]*\} from [^;]+;\s*/gm, "")
    .replace(/export /g, ""), filename, { loader: "jsx" });
  return (ports, name) => new Function(...Object.keys(ports), `${code}; return ${name};`)(...Object.values(ports));
}
const [pageFactory, collectionFactory, tableFactory, choicesFactory, queryFactory, hookFactory] = await Promise.all([
  compile(source, "page.jsx"),
  compile(read("components/Collection.jsx"), "collection.jsx"),
  compile(read("components/DataTable.jsx"), "table.jsx"),
  compile(read("components/ResourceFields.jsx").split("export const statusFilter")[1]
    .split("export function ItemSelect")[0].replace(/^/, "const statusFilter"), "choices.jsx"),
  compile(read("components/QueryState.jsx"), "query.jsx"),
  compile(read("lib/api/useResources.js").split("export function useCollection")[1]
    .split("export function useWrite")[0].replace(/^/, "function useCollection"), "hooks.jsx"),
]);
const statusFilter = choicesFactory({ STATUS_LABELS }, "statusFilter");

function page(rows = [row]) {
  const state = { slots: [], fields: new Map(), requests: [], reads: [], lookups: [], collection: null };
  let slot = 0;
  const useState = (initial) => {
    const index = slot++;
    if (!(index in state.slots)) state.slots[index] = initial;
    return [state.slots[index], (next) => {
      state.slots[index] = typeof next === "function" ? next(state.slots[index]) : next;
    }];
  };
  const jsx = { ...React, createElement: (type, props, ...children) => {
    if (type === "form") state.submit = props.onSubmit;
    return React.createElement(type, props, ...children);
  } };
  const Button = ({ children, disabled, onClick, type }) => React.createElement("button", { disabled, onClick, type }, children);
  const Link = ({ to, children }) => React.createElement("a", { href: to }, children);
  const Field = (props) => {
    state.fields.set(props.name, props);
    return React.createElement("label", null, props.label,
      React.createElement(props.as || "input", { name: props.name, value: props.value, onChange: props.onChange },
        props.options?.map((option) => React.createElement("option", { key: option.value, value: option.value }, option.label))));
  };
  const query = { data: { data: rows, meta: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 } } };
  const useResource = (path, params) => {
    state.reads.push({ path, params });
    state.requests.push(readResource(path, params));
    return query;
  };
  const useCollection = hookFactory({ useState, useResource }, "useCollection");
  const QueryState = queryFactory({ React: jsx, Button, Link }, "QueryState");
  const tablePorts = { React: jsx, Button, number };
  const DataTable = tableFactory(tablePorts, "DataTable");
  const Pagination = tableFactory(tablePorts, "Pagination");
  const Collection = collectionFactory({
    React: jsx, useState, useEffect: () => {}, useId: React.useId, useRef: React.useRef, Field, Button, DataTable, Pagination, QueryState, DateInput: () => null,
    ArrowDownUp, CalendarDays, ChevronDown, ChevronUp, Filter, LayoutGrid, Layers, Search,
    Card: ({ children }) => React.createElement("section", null, children),
  }, "Collection");
  const Component = pageFactory({
    React: jsx, API, useCollection, completionListFilters, statusFilter, dateRangeError,
    dateTime, employeeName, itemName, REQUEST_TYPE_LABELS, Link,
    useCatalog: () => { state.lookups.push(API.catalog); return { data: { data: items } }; },
    useChoices: (path) => { state.lookups.push(path); return { data: employees }; },
    PageHeader: ({ title, subtitle }) => React.createElement("header", null,
      React.createElement("h1", null, title), React.createElement("p", null, subtitle)),
    Badge: ({ status }) => React.createElement("span", { "data-status": status }, status),
    Collection: (props) => { state.collection = props; return React.createElement(Collection, props); },
  }, "CompletionListPage");
  return {
    state,
    render: () => { slot = 0; state.fields.clear(); return renderToStaticMarkup(React.createElement(Component)); },
    select: (name, value) => state.fields.get(name).onChange({ target: { value } }),
    submit: () => state.submit({ preventDefault() {} }),
  };
}

async function withApi(run) {
  const previousAdapter = apiClient.defaults.adapter;
  const previousStorage = globalThis.localStorage;
  const requests = [];
  globalThis.localStorage = { getItem: () => null };
  apiClient.defaults.adapter = async (config) => {
    requests.push({ method: config.method, url: config.url, params: config.params });
    return { status: 200, statusText: "OK", config, headers: {}, data: { data: [], meta: {} } };
  };
  try { await run(requests); } finally {
    apiClient.defaults.adapter = previousAdapter;
    if (previousStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = previousStorage;
  }
}

// UC-33 AC-1: Chỉ thành phẩm, đủ nhân viên; thao tác chọn cả hai gửi hai điều kiện qua GET thật
test("product and employee selections reach the API together", async () => withApi(async (requests) => {
  const ui = page();
  ui.render();
  assert.deepEqual(ui.state.fields.get("mat_hang_id").options, [
    { value: "", label: "Tất cả" }, { value: "5", label: "Xe đạp" }, { value: "7", label: "Xe trẻ em" },
  ]);
  assert.deepEqual(ui.state.fields.get("nhan_vien_id").options, [
    { value: "", label: "Tất cả" }, { value: "20", label: "NV-20 · Nguyễn An" }, { value: "21", label: "NV-21 · Trần Bình" },
  ]);
  ui.select("mat_hang_id", "5"); ui.render();
  ui.select("nhan_vien_id", "20"); ui.render();
  ui.submit(); ui.render();
  await Promise.all(ui.state.requests);
  assert.deepEqual(requests.at(-1), {
    method: "get", url: API.completions,
    params: { page: 1, page_size: 20, mat_hang_id: "5", nhan_vien_id: "20" },
  });
}));

// UC-33 AC-2: Đúng ba trạng thái đã gửi, không Nháp; chọn Chờ duyệt gửi đúng query
test("pending filter excludes drafts and sends cho_duyet", async () => withApi(async (requests) => {
  const ui = page(); ui.render();
  const filters = ui.state.collection.filters;
  assert.deepEqual(Object.keys(filters[0]), ["name", "label", "as", "options"]);
  assert.equal(filters[0].name, "trang_thai");
  assert.equal(filters[0].label, "Trạng thái");
  assert.equal(filters[0].as, "select");
  assert.deepEqual(filters[0].options, [
    { value: "", label: "Tất cả" }, { value: "cho_duyet", label: "Chờ duyệt" },
    { value: "da_duyet", label: "Đã duyệt" }, { value: "tu_choi", label: "Từ chối" },
  ]);
  ui.select("trang_thai", "cho_duyet"); ui.render(); ui.submit(); ui.render();
  await Promise.all(ui.state.requests);
  assert.deepEqual(requests.at(-1).params, { page: 1, page_size: 20, trang_thai: "cho_duyet" });
}));

// UC-33 R2: Thứ tự bộ lọc, loại yêu cầu, khoảng ngày và chặn khoảng đảo trước khi gọi API
test("approved filters include type and date range without search or sort", async () => withApi(async (requests) => {
  const ui = page(); const html = ui.render();
  assert.deepEqual([...ui.state.fields.keys()], ["trang_thai", "loai_yeu_cau", "mat_hang_id", "nhan_vien_id", "tu_ngay", "den_ngay"]);
  assert.deepEqual(ui.state.fields.get("loai_yeu_cau").options, [{ value: "", label: "Tất cả" }, ...REQUEST_TYPES]);
  assert.deepEqual(completionListFilters(items, employees).slice(-2), dateFilters);
  assert.doesNotMatch(html, /Tìm kiếm|Sắp xếp/);
  for (const [name, value] of [["loai_yeu_cau", "nhap_kho"], ["tu_ngay", "2026-11-16"], ["den_ngay", "2026-11-16"]]) {
    ui.select(name, value); ui.render();
  }
  ui.submit(); ui.render();
  await Promise.all(ui.state.requests);
  assert.deepEqual(requests.at(-1).params, {
    page: 1, page_size: 20, loai_yeu_cau: "nhap_kho", tu_ngay: "2026-11-16", den_ngay: "2026-11-16",
  });
  ui.select("tu_ngay", "2026-11-17"); ui.render(); ui.submit();
  assert.match(ui.render(), /Từ ngày không được sau Đến ngày\./);
  assert.equal(ui.state.collection.collection.params.tu_ngay, "2026-11-16");
  await Promise.all(ui.state.requests);
}));

// UC-33 D7: Chín cột đúng thứ tự, lookup tên, số numeric và finish_time định dạng giờ Việt Nam
test("list renders approved columns and catalog names", async () => withApi(async () => {
  const ui = page(); const html = ui.render();
  assert.match(html, /<h1>Chứng từ hoàn thành sản xuất<\/h1>/);
  assert.match(html, /Chứng từ nhân viên đã gửi; mở để duyệt hoặc từ chối\./);
  assert.deepEqual(ui.state.collection.columns.map(({ label }) => label), [
    "Mã chứng từ", "Mã yêu cầu", "Thành phẩm", "Loại yêu cầu", "Nhân viên",
    "Số lượng hoàn thành", "Thời điểm hoàn thành", "Trạng thái", "Thao tác",
  ]);
  assert.equal(ui.state.collection.columns[5].numeric, true);
  assert.ok(html.includes("<td class=\"numeric\">7</td>"));
  assert.ok(html.includes(`<td class="">${dateTime(row.finish_time)}</td>`));
  assert.match(html, /<td class="">Xe đạp<\/td>/);
  assert.match(html, /<td class="">Nguyễn An<\/td>/);
  assert.match(html, /<td class="">Sản xuất nhập kho<\/td>/);
  assert.match(html, /data-status="cho_duyet"/);
  assert.deepEqual(ui.state.lookups, [API.catalog, API.employees]);
  await Promise.all(ui.state.requests);
}));

// UC-33 R3: Mã chứng từ và Mở dẫn đến yêu cầu nguồn, không dùng id chứng từ
test("both document links open the source production request", async () => withApi(async () => {
  const ui = page(); const html = ui.render();
  assert.match(html, /<a href="\/kho\/yeu-cau\/101">HTSX-202611-000012<\/a>/);
  assert.match(html, /<a href="\/kho\/yeu-cau\/101">Mở →<\/a>/);
  assert.equal((html.match(/href="\/kho\/yeu-cau\/101"/g) || []).length, 2);
  assert.doesNotMatch(html, /href="\/kho\/yeu-cau\/12"/);
  await Promise.all(ui.state.requests);
}));

// UC-33 A1: Collection/DataTable thật hiện thông báo trống khi API trả data []
test("empty list uses the shared collection empty state", async () => withApi(async () => {
  const ui = page([]); const html = ui.render();
  assert.match(html, /class="empty-state">Chưa có dữ liệu phù hợp\.<\/td>/);
  assert.match(html, /0 kết quả/);
  assert.doesNotMatch(html, /HTSX-202611|Mở →/);
  await Promise.all(ui.state.requests);
}));

// UC-33 AC-3: Chỉ QLK truy cập/menu; mục ngay sau Nhu cầu và route nằm đúng RoleGate /kho
test("role access navigation placement and route gate enforce manager scope", () => {
  const path = "/kho/chung-tu-hoan-thanh";
  for (const role of ["quan_ly", "nhan_vien", "quan_tri_vien"]) {
    assert.equal(canAccessPath(role, path), role === "quan_ly");
    const links = navigationFor(role).flatMap((group) => group.items);
    assert.equal(links.some(([url]) => url === path), role === "quan_ly");
  }
  const operations = navigationFor("quan_ly").find(({ title }) => title === "Vận hành");
  const index = operations.items.findIndex(([url]) => url === path);
  assert.deepEqual(operations.items[index - 1], ["/kho/phieu-xuat", "Phiếu xuất kho"]);
  assert.deepEqual(operations.items[index], [path, "Hoàn thành sản xuất"]);
  const gates = [...routes.matchAll(/<Route element=\{<RoleGate \/>\}>([\s\S]*?)<\/Route>/g)].map((match) => match[1]);
  const managerGate = gates.find((gate) => gate.includes('path="/kho"'));
  assert.match(managerGate, /<Route path="\/kho\/chung-tu-hoan-thanh" element=\{<CompletionListPage \/>\} \/>/);
  assert.equal(gates.filter((gate) => gate.includes('path="/kho/chung-tu-hoan-thanh"')).length, 1);
});
