import { test as base, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";
import { dateTime, money } from "../../src/lib/format.js";

const test = base.extend({
  role: ["quan_tri_vien", { option: true }],
  readOnlyApi: [
    async ({ page, role }, use) => {
      const writes = [];
      page.on("request", (request) => {
        if (request.method() !== "GET") {
          writes.push({ method: request.method(), url: request.url() });
        }
      });
      const state = await installApi(page, { role });
      await use(state);
      expect(writes, "lookup screens must only issue GET requests").toEqual([]);
      expect(state.unexpected).toEqual([]);
    },
    { auto: true },
  ],
});

const lookupPages = [
  ["/admin/mat-hang", "Tra cứu mặt hàng"],
  ["/admin/nha-cung-cap", "Tra cứu nhà cung cấp"],
  ["/admin/lich-su", "Lịch sử thao tác"],
];

test("admin material statuses use the admin pill", async ({ page }) => {
  await page.goto("/admin/mat-hang");
  await expect(page.locator("table tbody tr").first().locator(".admin-pill.admin-pill-green"))
    .toHaveText("Đang dùng");
});

test("admin history keeps only object type and date filters", async ({ page }) => {
  await page.goto("/admin/lich-su");
  const filters = page.locator(".filters");
  await expect(filters.locator(".field-label label")).toHaveText([
    "Loại đối tượng", "Từ ngày", "Đến ngày",
  ]);
  for (const label of ["ID đối tượng", "Người thực hiện", "Thao tác", "Sắp xếp"])
    await expect(filters.getByLabel(label, { exact: true })).toHaveCount(0);
  await expect(page.getByRole("columnheader", { name: "Người thực hiện", exact: true })).toBeVisible();
});

for (const role of ["quan_tri_vien", "quan_ly"]) {
  test.describe(`history date filters for ${role}`, () => {
    test.use({ role });
    test("dates mask input, send ISO, block invalid dates and support the calendar", async ({ page, readOnlyApi }) => {
      const path = role === "quan_tri_vien" ? "/admin/lich-su" : "/kho/lich-su";
      await page.goto(path);
      const from = page.getByLabel("Từ ngày", { exact: true });
      await expect(from).toHaveAttribute("type", "text");
      await expect(from).toHaveAttribute("placeholder", "dd/mm/yyyy");
      const calls = () => readOnlyApi.calls.filter((call) => call.path === "audit" && call.method === "GET");
      await from.pressSequentially("05112026");
      await expect(from).toHaveValue("05/11/2026");
      await page.getByRole("button", { name: "Lọc", exact: true }).click();
      await expect.poll(() => calls().at(-1).params.tu_ngay).toBe("2026-11-05");
      expect(calls().at(-1).params.sort_by).toBe("created_at");
      expect(calls().at(-1).params.sort_order).toBe("desc");
      const count = calls().length;
      for (const invalid of ["31022026", "0511"]) {
        await from.fill(invalid);
        await expect(from).toHaveAttribute("aria-invalid", "true");
        expect(await from.evaluate((input) => input.checkValidity())).toBe(false);
        await page.getByRole("button", { name: "Lọc", exact: true }).click();
        expect(calls()).toHaveLength(count);
      }
      const field = page.locator(".filters .field").filter({ has: from });
      const calendar = field.getByRole("button", { name: "Chọn ngày", exact: true });
      await calendar.click();
      await page.keyboard.press("Escape");
      const picker = field.locator('input[type="date"]');
      await expect(picker).toHaveAttribute("tabindex", "-1");
      await expect(picker).toHaveAttribute("aria-hidden", "true");
      await picker.evaluate((input) => {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
        setter.call(input, "2026-11-07");
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
      await expect(from).toHaveValue("07/11/2026");
      expect(await from.evaluate((input) => input.checkValidity())).toBe(true);
      await page.getByRole("button", { name: "Lọc", exact: true }).click();
      await expect.poll(() => calls().at(-1).params.tu_ngay).toBe("2026-11-07");
      await picker.evaluate((input) => { input.showPicker = undefined; });
      await calendar.click();
      await expect(from).toBeFocused();
      await from.fill("");
      await page.getByLabel("Đến ngày", { exact: true }).fill("08112026");
      await page.getByRole("button", { name: "Lọc", exact: true }).click();
      await expect.poll(() => calls().at(-1).params).toMatchObject({ den_ngay: "2026-11-08" });
      expect(calls().at(-1).params).not.toHaveProperty("tu_ngay");
    });
  });
}

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1366, height: 768 },
  { width: 375, height: 812 },
]) {
  test(`all six admin tabs fit above the artwork at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/admin/mat-hang");
    if (viewport.width === 375) {
      await page.getByRole("button", { name: "Mở điều hướng", exact: true }).click();
    }
    const sidebar = page.getByRole("complementary", { name: "Thanh điều hướng" });
    const navigation = sidebar.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
    await expect(navigation.getByRole("link")).toHaveCount(6);
    for (const link of await navigation.getByRole("link").all()) {
      await expect(link).toBeInViewport();
    }
    expect(
      await navigation.evaluate((element) => element.scrollHeight <= element.clientHeight),
    ).toBe(true);
    const navBounds = await navigation.boundingBox();
    const artworkBounds = await sidebar.locator('div[aria-hidden="true"]').boundingBox();
    expect(artworkBounds.y).toBeGreaterThanOrEqual(navBounds.y + navBounds.height);
  });
}

for (const width of [1440, 375]) {
  test(`admin lookup headings match account management at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await page.goto("/admin/tai-khoan");
    const heading = page.locator("main .admin-page-heading h1");
    await expect(heading).toBeVisible();
    const fontSize = await heading.evaluate((element) => getComputedStyle(element).fontSize);
    expect(fontSize).toBe("40px");
    for (const [path, title] of lookupPages) {
      await page.goto(path);
      await expect(heading).toHaveText(title);
      await expect(heading).toBeVisible();
      await expect(heading).toHaveCSS("font-size", fontSize);
      await expect(heading).toHaveCSS("color", "rgb(255, 255, 255)");
      await expect(page.locator("main .page-heading")).toHaveCount(0);
      await expect(page.locator("main .admin-page-heading p")).toHaveCount(0);
      await expect(page.locator(`#main-navigation a[href="${path}"]`)).toHaveAttribute(
        "aria-current",
        "page",
      );
      const tableHead = page.locator("main th").first();
      await expect(tableHead).toHaveCSS("background-color", "rgb(44, 36, 30)");
      await expect(tableHead).toHaveCSS("color", "rgb(180, 168, 156)");
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    }
  });
}

test("admin item rows keep a dark background on hover", async ({ page }) => {
  await page.goto("/admin/mat-hang");
  const row = page.locator("table tbody tr").first();
  await expect(row).toContainText("MH-000001");
  await row.hover();
  await expect(row).toHaveCSS("background-color", "rgb(38, 31, 26)");
});

test("item type choices apply immediately without submitting the filters", async ({ page }) => {
  await page.goto("/admin/mat-hang");
  const type = page.getByRole("combobox", { name: "Loại mặt hàng", exact: true });
  await expect(type.locator("option")).toHaveText(["Tất cả loại", "Linh kiện", "Thành phẩm"]);
  const response = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" &&
      url.pathname === "/api/v1/mat_hang" &&
      url.searchParams.get("loai_mat_hang") === "thanh_pham";
  });
  await type.selectOption("thanh_pham");
  expect((await response).ok()).toBe(true);
  await expect(page.locator("table tbody tr")).toHaveCount(1);
  await expect(page.locator("table tbody tr")).toContainText("MH-000004");
  await expect(page.getByRole("button", { name: "Lọc", exact: true })).toBeVisible();
});

test("item status rejects component filters before sending a request", async ({ page, readOnlyApi }) => {
  await page.goto("/admin/mat-hang");
  const type = page.getByRole("combobox", { name: "Loại mặt hàng", exact: true });
  const status = page.getByRole("combobox", { name: "Trạng thái", exact: true });
  await expect(status.locator("option")).toHaveText(["Tất cả", "Đang dùng", "Ngừng dùng"]);
  const response = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" &&
      url.pathname === "/api/v1/mat_hang" &&
      url.searchParams.get("loai_mat_hang") === "linh_kien";
  });
  await type.selectOption("linh_kien");
  await response;
  const rows = page.locator("table tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(rows.getByRole("link", { name: /^MH-/ })).toHaveText([
    "MH-000001", "MH-000002", "MH-000003",
  ]);
  const itemCalls = () => readOnlyApi.calls.filter((call) => call.path === "mat_hang");
  const callCount = itemCalls().length;
  await status.selectOption("true");
  await expect(page.getByRole("alert")).toHaveText("Trạng thái chỉ lọc được cho thành phẩm.");
  await page.getByRole("button", { name: "Lọc", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Trạng thái chỉ lọc được cho thành phẩm.");
  expect(itemCalls()).toHaveLength(callCount);
  const recovery = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" &&
      url.pathname === "/api/v1/mat_hang" &&
      url.searchParams.get("loai_mat_hang") === "thanh_pham" &&
      url.searchParams.get("is_active") === "true";
  });
  await type.selectOption("thanh_pham");
  expect((await recovery).ok()).toBe(true);
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(itemCalls().some((call) =>
    call.params.loai_mat_hang === "linh_kien" && Object.hasOwn(call.params, "is_active"),
  )).toBe(false);
});

test("admin item lookup shows all read-only fields and three stock balances", async ({ page, readOnlyApi }) => {
  const frame = readOnlyApi.resources.mat_hang.find((item) => item.id === 1);
  Object.assign(frame, { so_luong_dang_giu: 40, so_luong_con_dung: 80 });
  await page.goto("/admin/mat-hang");
  await expect(page.getByRole("heading", { name: "Tra cứu mặt hàng", exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Đơn giá", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Thêm mặt hàng" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Thêm mặt hàng" })).toHaveCount(0);
  const action = page.locator("table tbody tr").first().getByRole("link", { name: "Xem →" });
  await action.click();
  await expect(page).toHaveURL(/\/admin\/mat-hang\/1$/);
  const dialog = page.getByRole("dialog", { name: "Chi tiết mặt hàng", exact: true });
  await expect(dialog).toBeVisible();
  for (const [label, value] of [
    ["Mã", "MH-000001"],
    ["Tên mặt hàng", "Khung xe"],
    ["Loại", "Linh kiện"],
    ["SKU", "FRAME-01"],
    ["Đơn vị tính", "cái"],
    ["Đơn giá", money(250000)],
    ["Màu sắc", "Đen"],
    ["Mô tả", "Khung xe thép"],
    ["Trạng thái", "Đang dùng"],
    ["Tồn thực tế", "120 cái"],
    ["Đang giữ", "40 cái"],
    ["Còn dùng được", "80 cái"],
    ["Cập nhật tồn", dateTime("2026-11-05T01:00:00Z")],
  ]) {
    const entry = dialog.locator(".info-grid > div").filter({
      has: page.locator("dt").filter({ hasText: new RegExp(`^${label}$`) }),
    });
    await expect(entry.locator("dd")).toHaveText(value);
  }
  await expect(dialog.locator("input, select, textarea, form")).toHaveCount(0);
  await expect(dialog.getByRole("button", { name: /Lưu|Ngừng sử dụng/ })).toHaveCount(0);
  await expect(page.locator('.admin-breadcrumb a[href="/admin/mat-hang"]')).toHaveText(
    "Tra cứu mặt hàng",
  );
  await expect(page.locator('.admin-breadcrumb [aria-current="page"]')).toHaveText(
    "Chi tiết mặt hàng",
  );
  await expect(page.locator('#main-navigation a[href="/admin/mat-hang"]')).toHaveAttribute(
    "aria-current",
    "page",
  );
  await dialog.getByRole("button", { name: "Tải lại chi tiết", exact: true }).click();
  await expect(dialog.locator("dd").filter({ hasText: /^80 cái$/ })).toBeVisible();
  await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/mat-hang$/);
  await expect(action).toBeFocused();
});

test("admin supplier lookup has no edit, delete, create or receiving links", async ({ page }) => {
  await page.goto("/admin/nha-cung-cap");
  await expect(
    page.getByRole("heading", { name: "Tra cứu nhà cung cấp", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Thêm nhà cung cấp" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Thêm nhà cung cấp" })).toHaveCount(0);
  const action = page.locator("table tbody tr").first().getByRole("link", { name: "Xem →" });
  await action.click();
  await expect(page).toHaveURL(/\/admin\/nha-cung-cap\/1$/);
  const dialog = page.getByRole("dialog", { name: "Chi tiết nhà cung cấp", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".info-grid dt")).toHaveText([
    "Mã NCC",
    "Tên",
    "Số điện thoại",
    "Địa chỉ",
    "Phường / xã",
    "Tỉnh / thành",
  ]);
  await expect(dialog.locator(".info-grid dd").first()).toHaveText("NCC-000001");
  await expect(dialog.getByRole("button", { name: /Sửa|Xóa|Lưu/ })).toHaveCount(0);
  await expect(dialog.locator("input, select, textarea, form")).toHaveCount(0);
  await expect(page.locator('a[href*="/kho/phieu-nhap"]')).toHaveCount(0);
  await expect(page.locator('.admin-breadcrumb a[href="/admin/nha-cung-cap"]')).toHaveText(
    "Tra cứu nhà cung cấp",
  );
  await expect(page.locator('.admin-breadcrumb [aria-current="page"]')).toHaveText(
    "Chi tiết nhà cung cấp",
  );
  await expect(page.locator('#main-navigation a[href="/admin/nha-cung-cap"]')).toHaveAttribute(
    "aria-current",
    "page",
  );
  await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/nha-cung-cap$/);
  await expect(action).toBeFocused();
});

for (const [path, title] of lookupPages.slice(0, 2)) {
  test(`${path}/moi redirects to its read-only list`, async ({ page }) => {
    await page.goto(`${path}/moi`);
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
}

test.describe("warehouse history heading", () => {
  test.use({ role: "quan_ly" });
  test("warehouse history retains all seven filters", async ({ page }) => {
    await page.goto("/kho/lich-su");
    await expect(page.locator(".filters .field-label label")).toHaveText([
      "Loại đối tượng", "ID đối tượng", "Người thực hiện", "Thao tác", "Từ ngày", "Đến ngày", "Sắp xếp",
    ]);
  });
  for (const width of [1440, 375]) {
    test(`history heading is readable and item management stays unchanged at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
      await page.goto("/kho/lich-su");
      const heading = page.locator("main .admin-page-heading h1");
      await expect(heading).toHaveText("Lịch sử thao tác");
      await expect(heading).toBeVisible();
      await expect(heading).toHaveCSS("font-size", "40px");
      const warehouseColor = await page.locator(".warehouse-shell").evaluate(
        (shell) => getComputedStyle(shell).color,
      );
      expect(warehouseColor).toBe("rgb(244, 238, 232)");
      await expect(heading).toHaveCSS("color", warehouseColor);
      await expect(page.locator("main .page-heading")).toHaveCount(0);
      await expect(page.locator("main .admin-page-heading p.muted")).toHaveCount(0);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
      await page.goto("/kho/mat-hang");
      await expect(page.locator("main .page-heading h1")).toHaveText("Mặt hàng và tồn kho");
      await expect(page.locator("main .page-heading h1")).toHaveCSS(
        "font-size", width === 375 ? "24px" : "26px",
      );
      const subtitle = page.locator("main .page-heading p.muted");
      await expect(subtitle).toHaveText(
        "Linh kiện · Thành phẩm. Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ.",
      );
      await expect(subtitle).toBeHidden();
      await expect(page.getByRole("link", { name: "Thêm mặt hàng" })).toBeVisible();
    });
  }
});

test.describe("employee inventory lookup", () => {
  test.use({ role: "nhan_vien" });
  test("keeps its five detail fields and redirects creation to the list", async ({ page }) => {
    await page.goto("/nv/ton-kho/1");
    const dialog = page.getByRole("dialog", { name: "Chi tiết mặt hàng", exact: true });
    await expect(dialog.locator(".info-grid dt")).toHaveText([
      "Tên mặt hàng",
      "SKU",
      "Tồn kho",
      "Đơn vị tính",
      "Cập nhật tồn",
    ]);
    await expect(dialog.locator("input, select, textarea, form")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Đóng", exact: true }).click();
    await expect(page.getByRole("columnheader", { name: "Đơn giá", exact: true })).toHaveCount(0);
    await page.goto("/nv/ton-kho/moi");
    await expect(page).toHaveURL(/\/nv\/ton-kho$/);
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
});
