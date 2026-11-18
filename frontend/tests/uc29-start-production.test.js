import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createRoutesFromChildren, matchRoutes, Navigate, Route, Routes } from "react-router-dom";
import { transformWithEsbuild } from "vite";
import { canStartProduction, requestDetailEntries } from "../src/features/production/requestForm.js";
import { API } from "../src/lib/api/endpoints.js";
import { dateTime, itemName } from "../src/lib/format.js";
import { navigationFor } from "../src/layouts/navigation.js";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const source = read("../src/features/production/RequestsPage.jsx");
const routes = read("../src/routes/index.jsx");
const dashboard = read("../src/features/dashboard/DashboardPage.jsx");
const row = {
  id: 1, ma_yeu_cau_san_xuat: "YCSX-202611-000001", trang_thai: "dang_thuc_hien",
  nhan_vien_duoc_giao_id: 20, so_luong_can_san_xuat: 7, started_at: null,
};

function handler(failure) {
  const start = source.indexOf("  async function start()");
  const end = source.indexOf("\n  //", start);
  assert.ok(start > 0 && end > start);
  const state = { errors: [], writes: [], notices: [], confirmations: [] };
  const ports = {
    record: row, snapshot: { etag: '"detail-reviewed"' }, API,
    setStartError: (error) => state.errors.push(error),
    notify: (message) => state.notices.push(message),
    confirm: (options) => state.confirmations.push(options),
    startMutation: { mutateAsync: async (input) => {
      state.writes.push(input);
      if (failure) throw failure;
      return { data: { ...row, started_at: "2026-11-16T08:00:00Z" } };
    } },
  };
  const run = new Function(...Object.keys(ports), `return (${source.slice(start, end).trim()});`)(...Object.values(ports));
  return { run, state };
}

// UC-29 D5: Nút chỉ dành cho NV được giao, đúng trạng thái, lượng dương, chưa bắt đầu
test("canStartProduction enforces every role state quantity and start-time condition", () => {
  assert.equal(canStartProduction(row, false, "20"), true);
  assert.equal(canStartProduction(row, true, 20), false);
  assert.equal(canStartProduction(row, false, 21), false);
  assert.equal(canStartProduction(null, false, 20), false);
  for (const trang_thai of ["nhap", "da_gui", "cho_bo_sung_linh_kien", "hoan_thanh", "da_huy"]) {
    assert.equal(canStartProduction({ ...row, trang_thai }, false, 20), false);
  }
  for (const quantity of [0, -1, null, undefined]) {
    assert.equal(canStartProduction({ ...row, so_luong_can_san_xuat: quantity }, false, 20), false);
  }
  assert.equal(canStartProduction({ ...row, started_at: "2026-11-16T08:00:00Z" }, false, 20), false);
});

// UC-29 AC-2: Bấm gọi ngay POST body rỗng, ETag chi tiết đã xem, không mở xác nhận
test("start posts the reviewed detail ETag immediately and notifies success", async () => {
  const { run, state } = handler();
  await run();
  assert.deepEqual(state.writes, [{ path: "/yeu_cau_san_xuat/1/bat_dau", body: {}, etag: '"detail-reviewed"' }]);
  assert.deepEqual(state.confirmations, []);
  assert.deepEqual(state.errors, [null]);
  assert.deepEqual(state.notices, ["Đã ghi nhận bắt đầu sản xuất."]);
  const client = read("../src/lib/api/client.js");
  assert.match(client, /writeResource\(\{ path, method = "post", body = \{\}, etag, versioned = true \}/);
  assert.match(client, /headers: versioned \? versionHeaders\(etag\) : \{\}/);
});

// UC-29 A1: 409 hiển thị nguyên lỗi backend qua trạng thái lỗi riêng, không báo thành công
test("start failure preserves backend error and leaves other action errors alone", async () => {
  const failure = Object.assign(new Error("Phiếu xuất linh kiện chưa được duyệt"), { status: 409 });
  const { run, state } = handler(failure);
  await run();
  assert.deepEqual(state.errors, [null, failure]);
  assert.deepEqual(state.notices, []);
  assert.deepEqual(state.confirmations, []);
  assert.equal(state.writes.length, 1);
  assert.match(source, /const \[startError, setStartError\] = useState\(null\)/);
  assert.match(source, /const startMutation = useWrite\(\)/);
  assert.match(source, /<ErrorNotice error=\{startError\} \/>/);
});

// UC-29 D5: Đúng khối actions, nhãn, điều kiện hiển thị và khóa nút khi đang ghi
test("start button follows the approved actions and pending-state checklist", () => {
  assert.match(source, /\{canStartProduction\(record, manager, userId\) && \(\s*<div className="actions actions-end">\s*<Button disabled=\{startMutation.isPending\} onClick=\{start\}>Bắt đầu sản xuất<\/Button>/);
  const resources = read("../src/lib/api/useResources.js");
  assert.match(resources, /writeResource/);
  assert.match(resources, /invalidateQueries/);
});

// UC-29 AC-3: Sau bắt đầu nút biến mất, thời điểm hiển thị ngay sau lần kiểm tra đầu
test("started detail shows the saved Vietnam time in the approved position", () => {
  const record = { ...row, kiem_tra_lan_dau_at: "2026-11-16T07:00:00Z", started_at: "2026-11-16T08:00:00Z" };
  const entries = requestDetailEntries(record, [], []);
  const index = entries.findIndex(([label]) => label === "Kiểm tra lần đầu lúc");
  assert.deepEqual(entries[index + 1], ["Bắt đầu sản xuất lúc", dateTime(record.started_at)]);
  assert.equal(canStartProduction(record, false, 20), false);
  assert.equal(requestDetailEntries(row, [], []).some(([label]) => label === "Bắt đầu sản xuất lúc"), false);
});

// UC-29 D6: Menu không còn lệnh/chứng từ v3; NV có đúng đường vào Việc được giao
test("menus point to requests and remove retired production entries", () => {
  assert.deepEqual(navigationFor("nhan_vien"), [
    { title: "Chung", items: [["/nv", "Tổng quan"]] },
    {
      title: "Sản xuất",
      items: [
        ["/nv/yeu-cau", "Việc được giao"],
        ["/nv/phieu-xuat", "Phiếu xuất"],
        ["/nv/chung-tu-hoan-thanh", "Chứng từ hoàn thành"],
      ],
    },
    { title: "Theo dõi", items: [["/nv/ton-kho", "Tra cứu tồn kho"]] },
  ]);
  const managerItems = navigationFor("quan_ly").flatMap((group) => group.items);
  assert.ok(managerItems.some(([path, label]) => path === "/kho/yeu-cau" && label === "Yêu cầu sản xuất"));
  assert.equal(managerItems.some(([path]) => /lenh-sx|duyet-hoan-thanh/.test(path)), false);
});

// UC-29 D6: Gỡ import/trang/API v3 và chuyển hướng cả đường dẫn lệnh con
test("retired pages and APIs are gone and order wildcard routes redirect", async () => {
  assert.doesNotMatch(routes, /ProductionPage|CompletionsPage/);
  const routeSource = routes.slice(routes.indexOf("export function AppRoutes()")).replace("export ", "");
  const { code } = await transformWithEsbuild(routeSource, "routes.jsx", { loader: "jsx" });
  const ports = { React, Routes, Route, Navigate };
  for (const [, name] of routeSource.matchAll(/<([A-Z]\w*)/g)) {
    if (!ports[name]) ports[name] = () => null;
  }
  const AppRoutes = new Function(...Object.keys(ports), `${code}; return AppRoutes;`)(...Object.values(ports));
  const config = createRoutesFromChildren(AppRoutes().props.children.props.children);
  for (const role of ["kho", "nv"]) {
    assert.ok(routes.includes(`<Route path="/${role}/lenh-sx/*" element={<Navigate to="/${role}/yeu-cau" replace />} />`));
    for (const suffix of ["", "/1", "/1/deeper"]) {
      const leaf = matchRoutes(config, `/${role}/lenh-sx${suffix}`).at(-1).route.element;
      assert.equal(leaf.type, Navigate);
      assert.equal(leaf.props.to, `/${role}/yeu-cau`);
      assert.equal(leaf.props.replace, true);
    }
  }
  for (const path of ["/nv/hoan-thanh", "/nv/hoan-thanh/1", "/nv/phieu"]) {
    const leaf = matchRoutes(config, path).at(-1).route.element;
    assert.equal(leaf.type, Navigate);
    assert.equal(leaf.props.to, "/nv/yeu-cau");
    assert.equal(leaf.props.replace, true);
  }
  assert.equal(matchRoutes(config, "/kho/duyet-hoan-thanh/1").at(-1).route.element.props.code, 404);
  assert.doesNotMatch(routes, /path="\/kho\/duyet-hoan-thanh/);
  assert.equal(Object.hasOwn(API, "orders"), false);
  assert.equal(API.completions, "/chung_tu_hoan_thanh_sx");
  for (const page of ["ProductionPage", "CompletionsPage"]) {
    assert.equal(existsSync(new URL(`../src/features/production/${page}.jsx`, import.meta.url)), false);
  }
});

async function renderDashboard(name, records = []) {
  const start = dashboard.indexOf(`function ${name}()`);
  const end = dashboard.indexOf("\nfunction ", start + 1);
  assert.ok(start > 0 && end > start);
  const { code } = await transformWithEsbuild(dashboard.slice(start, end), "dashboard.jsx", { loader: "jsx" });
  const state = { queries: [], metrics: [], table: null };
  const ports = {
    React, API, itemName,
    useResource: (path, params) => {
      state.queries.push({ path, params });
      return { data: { data: path === API.requests ? records : [{ id: 5, ten_mat_hang: "Xe" }] } };
    },
    Metric: (props) => { state.metrics.push(props); return React.createElement("a", { href: props.href }, props.label); },
    Card: ({ title, action, children }) => React.createElement("section", null, title, action, children),
    PageHeader: ({ title, subtitle, action }) => React.createElement("header", null, title, subtitle, action),
    Link: ({ to, children }) => React.createElement("a", { href: to }, children),
    QueryState: ({ children }) => children,
    Badge: ({ status }) => React.createElement("span", null, status),
    DataTable: (props) => {
      state.table = props;
      return React.createElement("table", null, React.createElement("tbody", null,
        props.rows?.length ? props.rows.map((record) => React.createElement("tr", { key: record.id },
          props.columns.map((column) => React.createElement("td", { key: column.key }, column.render ? column.render(record) : record[column.key]))))
          : React.createElement("tr", null, React.createElement("td", null, props.empty))));
    },
    QuickStock: () => null,
    PendingCompletions: () => React.createElement("section", null, "Chứng từ hoàn thành chờ xác nhận"),
    WaitingComponentRequests: () => React.createElement("section", null, "Yêu cầu chờ bổ sung linh kiện"),
  };
  const Component = new Function(...Object.keys(ports), `${code}; return ${name};`)(...Object.values(ports));
  return { html: renderToStaticMarkup(React.createElement(Component)), state };
}

// UC-29 D6: Thẻ NV lọc trước rồi mới lấy 5 dòng, không báo rỗng khi 5 dòng đầu đã bắt đầu
test("employee dashboard filters before limiting waiting requests to five", async () => {
  const started = Array.from({ length: 5 }, (_, index) => ({ ...row, id: 10 + index, started_at: "2026-11-16T08:00:00Z" }));
  const waiting = Array.from({ length: 7 }, (_, index) => ({ ...row, id: 20 + index }));
  const { state } = await renderDashboard("EmployeeDashboard", [...started, ...waiting]);
  assert.deepEqual(state.table.rows.map((item) => item.id), [20, 21, 22, 23, 24]);
});

// UC-29 D6: Thẻ NV dùng yêu cầu Đang thực hiện, lọc chưa bắt đầu và cần sản xuất dương
test("employee dashboard renders only requests waiting to start and approved columns", async () => {
  const records = [
    { ...row, mat_hang_id: 5 },
    { ...row, id: 2, started_at: "2026-11-16T08:00:00Z" },
    { ...row, id: 3, so_luong_can_san_xuat: 0 },
  ];
  const { html, state } = await renderDashboard("EmployeeDashboard", records);
  assert.deepEqual(state.queries[0], { path: API.requests, params: { page: 1, page_size: 100, trang_thai: "dang_thuc_hien" } });
  assert.equal(state.metrics[0].label, "Yêu cầu được giao");
  assert.deepEqual(state.table.rows, [records[0]]);
  assert.deepEqual(state.table.columns.map(({ key, label, numeric }) => ({ key, label, numeric })), [
    { key: "ma_yeu_cau_san_xuat", label: "Mã yêu cầu", numeric: undefined },
    { key: "mat_hang_id", label: "Thành phẩm", numeric: undefined },
    { key: "so_luong_can_san_xuat", label: "Số cần sản xuất", numeric: true },
    { key: "trang_thai", label: "Trạng thái", numeric: undefined },
    { key: "action", label: "Thao tác", numeric: undefined },
  ]);
  assert.deepEqual(state.metrics.slice(1), [
    { label: "Yêu cầu đã giao", path: API.requests, params: { trang_thai: "da_gui" }, href: "/nv/yeu-cau" },
    { label: "Đang thực hiện", path: API.requests, params: { trang_thai: "dang_thuc_hien" }, href: "/nv/yeu-cau" },
  ]);
  assert.match(html, /Yêu cầu chờ bắt đầu sản xuất/);
  assert.match(html, /href="\/nv\/yeu-cau">Xem yêu cầu của tôi<\/a>/);
  assert.match(html, /href="\/nv\/yeu-cau\/1">YCSX-202611-000001/);
  assert.match(html, /href="\/nv\/yeu-cau\/1">Mở<\/a>/);
  assert.match(html, /<span>dang_thuc_hien<\/span>/);
  assert.match(html, /Xe/);
  assert.doesNotMatch(html, /Lệnh|lệnh|Hoàn thành chờ duyệt|Tạo chứng từ hoàn thành/);
});

// UC-29 D6: Không có yêu cầu phù hợp hiển thị đúng empty trong thẻ NV
test("employee dashboard renders the approved empty state", async () => {
  const { html, state } = await renderDashboard("EmployeeDashboard", [{ ...row, so_luong_can_san_xuat: 0 }]);
  assert.deepEqual(state.table.rows, []);
  assert.match(html, /Không có yêu cầu chờ bắt đầu sản xuất\./);
});

// Tổng quan QLK giữ metric UC-29 và thêm hai hàng đợi theo yêu cầu giao diện đã chốt.
test("warehouse dashboard keeps request metrics and shows the two pending queues", async () => {
  const { html, state } = await renderDashboard("WarehouseDashboard");
  assert.deepEqual(state.queries, []);
  assert.deepEqual(state.metrics, [
    { label: "Yêu cầu đã gửi", path: API.requests, params: { trang_thai: "da_gui" }, href: "/kho/yeu-cau" },
    { label: "Yêu cầu đang thực hiện", path: API.requests, params: { trang_thai: "dang_thuc_hien" }, href: "/kho/yeu-cau" },
    { label: "Chờ bổ sung linh kiện", path: API.requests, params: { trang_thai: "cho_bo_sung_linh_kien" }, href: "/kho/yeu-cau" },
  ]);
  assert.match(html, /Chứng từ hoàn thành chờ xác nhận/);
  assert.match(html, /Yêu cầu chờ bổ sung linh kiện/);
  assert.doesNotMatch(html, /Tra cứu tồn kho nhanh|Hoạt động gần đây|Lệnh/);
});

test("retired employee document list redirects to assigned requests instead of a manager-only API", () => {
  assert.match(read("../src/routes/index.jsx"), /path="\/nv\/phieu" element=\{<Navigate to="\/nv\/yeu-cau" replace/);
  assert.doesNotMatch(read("../src/features/dashboard/DashboardPage.jsx"), /to="\/nv\/(phieu|xuat-nvl|xuat-tp)"/);
  assert.doesNotMatch(read("../src/components/ApprovalActions.jsx"), /Lệnh sản xuất|lenh_san_xuat_id/);
  assert.match(read("../src/features/dashboard/auditFormat.js"), /lenh_san_xuat/);
});
