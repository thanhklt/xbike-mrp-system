import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const checkPath = "yeu_cau_san_xuat/1/kiem_tra";
const component = {
  mat_hang_id: 1, ma_mat_hang: "MH-000001", ten_mat_hang: "Khung thử nghiệm",
  don_vi_tinh: "chiếc", so_luong_can: 10,
};
const availableComponent = {
  ...component, mat_hang_id: 2, ma_mat_hang: "MH-000002", ten_mat_hang: "Linh kiện đã đủ",
  so_luong_con_dung: 10, so_luong_thieu: 0,
};

function checkPreview(missing, { first = false, production = 10 } = {}) {
  return {
    lan_dau: first, so_luong: 20, so_luong_dung_thanh_pham: 20 - production,
    so_luong_can_san_xuat: production, du_linh_kien: missing === 0,
    trang_thai_du_kien: missing > 0 ? "cho_bo_sung_linh_kien" : "dang_thuc_hien",
    giu_thanh_pham: 0,
    linh_kien: production ? [
      { ...component, so_luong_con_dung: 10 - missing, so_luong_thieu: missing },
      availableComponent,
    ] : [],
  };
}

test("reload and reopening show current shortage without changing the request", async ({ page }) => {
  let missing = 5;
  const state = await installApi(page, {
    role: "nhan_vien",
    intercept: (call) => call.path === checkPath && {
      json: { data: checkPreview(missing) },
    },
  });
  const [record] = state.resources.yeu_cau_san_xuat;
  record.trang_thai = "cho_bo_sung_linh_kien";
  const original = { ...record };
  const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
  const shortage = detail.getByRole("row").filter({ hasText: component.ten_mat_hang });
  const previewCalls = () => state.calls.filter((call) => call.path === checkPath);
  await page.goto("/nv/yeu-cau/1");
  await expect(shortage.getByRole("cell").last()).toHaveText("5");
  await expect(detail.getByText(availableComponent.ten_mat_hang)).toHaveCount(0);
  missing = 3;
  await page.reload();
  await expect(shortage.getByRole("cell").last()).toHaveText("3");
  await detail.getByRole("button", { name: "Đóng", exact: true }).click();
  missing = 0;
  await page.getByRole("link", { name: record.ma_yeu_cau_san_xuat }).click();
  await expect(detail.getByText("Đã đủ linh kiện, chờ xác nhận")).toBeVisible();
  await expect(detail.getByText("Chờ bổ sung linh kiện", { exact: true })).toBeVisible();
  await expect(shortage).toHaveCount(0);
  expect(previewCalls().map(({ method }) => method)).toEqual(["GET", "GET", "GET"]);
  expect(state.calls.every(({ method }) => method === "GET")).toBe(true);
  expect(record).toEqual(original);

  await detail.getByRole("button", { name: "Đóng", exact: true }).click();
  record.trang_thai = "dang_thuc_hien";
  state.versions["yeu_cau_san_xuat/1"] = 2;
  await page.getByRole("link", { name: record.ma_yeu_cau_san_xuat }).click();
  await expect(detail.getByText("Đang thực hiện", { exact: true })).toBeVisible();
  await expect(detail.getByText("Đã đủ linh kiện, chờ xác nhận")).toHaveCount(0);
  expect(previewCalls().map(({ method }) => method)).toEqual(["GET", "GET", "GET"]);
});

test("confirmation fetches fresh data, posts the reviewed ETag, and refreshes eligible previews", async ({ page }) => {
  let missing = 5;
  let actualMissing = 3;
  const state = await installApi(page, {
    role: "nhan_vien",
    intercept: (call, fixture) => {
      if (call.path !== checkPath) return null;
      if (call.method === "GET") return { json: { data: checkPreview(missing) } };
      // Inventory can change between the fresh preview and the transaction.
      missing = actualMissing;
      const actual = checkPreview(actualMissing);
      const [record] = fixture.resources.yeu_cau_san_xuat;
      record.trang_thai = actual.trang_thai_du_kien;
      if (!actualMissing) fixture.versions["yeu_cau_san_xuat/1"] = 2;
      return { json: { data: { yeu_cau: record, ket_qua: actual } } };
    },
  });
  state.resources.yeu_cau_san_xuat[0].trang_thai = "cho_bo_sung_linh_kien";
  const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
  const confirmation = page.getByRole("dialog", { name: "Kiểm tra lại yêu cầu sản xuất" });
  const check = detail.getByRole("button", { name: "Kiểm tra lại", exact: true });
  const shortage = detail.getByRole("row").filter({ hasText: component.ten_mat_hang });
  const previewCalls = () => state.calls.filter((call) => call.path === checkPath);
  await page.goto("/nv/yeu-cau/1");
  await expect(shortage.getByRole("cell").last()).toHaveText("5");
  missing = 0;
  await check.click();
  await expect(confirmation.getByText("Đủ", { exact: true })).toBeVisible();
  await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
  expect(previewCalls().map(({ method }) => method)).toEqual(["GET", "GET"]);

  await check.click();
  await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page.getByText("Vẫn thiếu linh kiện.")).toBeVisible();
  await expect(shortage.getByRole("cell").last()).toHaveText("3");
  expect(previewCalls().map(({ method }) => method)).toEqual(["GET", "GET", "GET", "POST", "GET"]);

  missing = 0;
  actualMissing = 0;
  await check.click();
  await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(detail.getByText("Đang thực hiện", { exact: true })).toBeVisible();
  await expect(detail.getByText("Đã đủ linh kiện, chờ xác nhận")).toHaveCount(0);
  await expect(check).toHaveCount(0);
  expect(previewCalls().map(({ method }) => method)).toEqual(["GET", "GET", "GET", "POST", "GET", "GET", "POST"]);
  const writes = previewCalls().filter(({ method }) => method === "POST");
  expect(writes.map(({ headers, body }) => [headers["if-match"], body])).toEqual([
    ['"v1"', {}], ['"v1"', {}],
  ]);
});

test("preview failure keeps detail readable and a retry can show sufficient finished products", async ({ page }) => {
  let payload = { status: 500, json: { error: { message: "Không tải được tồn khả dụng" } } };
  const state = await installApi(page, {
    role: "nhan_vien",
    intercept: (call) => call.path === checkPath && payload,
  });
  state.resources.yeu_cau_san_xuat[0].trang_thai = "da_gui";
  const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
  await page.goto("/nv/yeu-cau/1");
  await expect(detail.getByRole("alert")).toHaveText("Không tải được tồn khả dụng");
  await expect(detail.getByText("Đã giao", { exact: true })).toBeVisible();
  await expect(detail.getByText("Đã đủ linh kiện, chờ xác nhận")).toHaveCount(0);
  payload = { json: { data: null } };
  await detail.getByRole("button", { name: "Tải lại", exact: true }).click();
  await expect(detail.getByRole("alert")).toHaveText("Không tải được tình trạng linh kiện.");
  payload = { json: { data: checkPreview(0, { first: true, production: 0 }) } };
  await detail.getByRole("button", { name: "Tải lại", exact: true }).click();
  await expect(detail.getByText("Đã đủ thành phẩm, không cần sản xuất")).toBeVisible();
  await expect(detail.getByText("Số cần sản xuất", { exact: true }).locator("..").locator("dd")).toHaveText("0");
});

test("switching requests while availability is loading keeps results scoped to the open request", async ({ page }) => {
  let releaseFirst;
  const firstResponse = new Promise((resolve) => { releaseFirst = resolve; });
  const state = await installApi(page, {
    role: "nhan_vien",
    intercept: async (call) => {
      if (call.path === checkPath) {
        await firstResponse;
        return { json: { data: checkPreview(5, { first: true }) } };
      }
      if (call.path === "yeu_cau_san_xuat/2/kiem_tra") {
        return { json: { data: checkPreview(0, { first: true }) } };
      }
      return null;
    },
  });
  const [first, second] = state.resources.yeu_cau_san_xuat;
  first.trang_thai = second.trang_thai = "da_gui";
  const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
  try {
    await page.goto("/nv/yeu-cau/1");
    await expect(detail.getByText("Đang tải tình trạng linh kiện…")).toBeVisible();
    await expect.poll(() => state.calls.some((call) => call.path === checkPath)).toBe(true);
    await detail.getByRole("button", { name: "Đóng", exact: true }).click();
    await page.getByRole("link", { name: second.ma_yeu_cau_san_xuat }).click();
    await expect(detail.getByText("Đã đủ linh kiện, chờ xác nhận")).toBeVisible();
    await expect(detail.getByRole("heading", { name: second.ma_yeu_cau_san_xuat })).toBeVisible();
  } finally {
    releaseFirst();
  }
  await expect(detail.getByRole("heading", { name: "Linh kiện thiếu" })).toHaveCount(0);
});

for (const scenario of [
  { role: "quan_ly", assignment: 3, status: "da_gui", base: "/kho", label: "manager" },
  { role: "nhan_vien", assignment: 2, status: "da_gui", base: "/nv", label: "unassigned employee" },
  { role: "nhan_vien", assignment: 3, status: "dang_thuc_hien", base: "/nv", label: "ineligible state" },
]) {
  test(`does not request availability for ${scenario.label}`, async ({ page }) => {
    const state = await installApi(page, { role: scenario.role });
    const [record] = state.resources.yeu_cau_san_xuat;
    record.nhan_vien_duoc_giao_id = scenario.assignment;
    record.trang_thai = scenario.status;
    await page.goto(`${scenario.base}/yeu-cau/1`);
    const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
    await expect(detail.getByRole("heading", { name: record.ma_yeu_cau_san_xuat })).toBeVisible();
    await expect(detail.getByRole("button", { name: /^Kiểm tra/ })).toHaveCount(0);
    expect(state.calls.filter((call) => call.path === checkPath)).toEqual([]);
  });
}

for (const width of [375, 587, 768, 1440]) {
  test(`request check shows every material field without horizontal scrolling at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 720 });
    const lines = Array.from({ length: 10 }, (_, index) => ({
      mat_hang_id: index + 1, ma_mat_hang: `MH-${String(index + 1).padStart(6, "0")}`,
      ten_mat_hang: `Linh kiện có tên dài để kiểm tra xuống dòng ${index + 1}`,
      don_vi_tinh: "chiếc", so_luong_can: 10, so_luong_con_dung: 6, so_luong_thieu: 4,
    }));
    const state = await installApi(page, { role: "nhan_vien", intercept: (call) =>
      call.path === "yeu_cau_san_xuat/1/kiem_tra" && call.method === "GET" ? {
        json: { data: { lan_dau: false, so_luong: 10, so_luong_dung_thanh_pham: 0,
          so_luong_can_san_xuat: 10, du_linh_kien: false,
          trang_thai_du_kien: "cho_bo_sung_linh_kien", giu_thanh_pham: 0, linh_kien: lines }, meta: {} },
      } : null });
    state.resources.yeu_cau_san_xuat[0].trang_thai = "cho_bo_sung_linh_kien";
    await page.goto("/nv/yeu-cau/1");
    const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
    const inline = detail.locator(".request-check-results");
    const firstInlineRow = width <= 640
      ? inline.locator(".request-check-cards > section").first().locator("dd")
      : inline.locator("tbody tr").first().locator("td");
    await expect(firstInlineRow).toHaveText([
      lines[0].ma_mat_hang, lines[0].ten_mat_hang, "chiếc", "10", "6", "4",
    ]);
    const detailOverflow = await inline.evaluate((element) => element.scrollWidth - element.clientWidth);
    expect(detailOverflow).toBeLessThanOrEqual(1);
    await page.getByRole("button", { name: "Kiểm tra lại", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Kiểm tra lại yêu cầu sản xuất", exact: true });
    await expect(dialog).toBeVisible();
    if (width <= 640) {
      await expect(dialog.locator(".request-check-table")).toBeHidden();
      const cards = dialog.locator(".request-check-cards > section");
      await expect(cards).toHaveCount(10);
      for (const label of ["Mã", "Tên", "Đơn vị tính", "Cần", "Còn dùng được", "Thiếu"]) {
        await expect(cards.first().locator("dt").filter({ hasText: new RegExp(`^${label}$`) })).toBeVisible();
      }
      await expect(cards.first().locator("dd")).toHaveText([
        lines[0].ma_mat_hang, lines[0].ten_mat_hang, "chiếc", "10", "6", "4",
      ]);
    } else {
      await expect(dialog.locator(".request-check-cards")).toBeHidden();
      await expect(dialog.getByRole("columnheader")).toHaveCount(6);
      await expect(dialog.locator("tbody tr").first().locator("td")).toHaveText([
        lines[0].ma_mat_hang, lines[0].ten_mat_hang, "chiếc", "10", "6", "4",
      ]);
      await dialog.locator("tbody tr").first().hover();
      await expect(dialog.locator("tbody tr").first()).toHaveCSS("background-color", "rgb(48, 38, 31)");
    }
    const overflow = await dialog.evaluate((element) => [element, ...element.querySelectorAll(".dialog-body, .table-scroll, .request-check-cards")]
      .filter((node) => node.getClientRects().length).map((node) => node.scrollWidth - node.clientWidth));
    expect(overflow.every((amount) => amount <= 1)).toBe(true);
    await dialog.getByRole("button", { name: "Hủy", exact: true }).scrollIntoViewIfNeeded();
    await expect(dialog.getByRole("button", { name: "Xác nhận", exact: true })).toBeInViewport();
    await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
    expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
  });
}
