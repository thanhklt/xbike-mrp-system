import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("employee status button cycles immediately through every choice and wraps without a list", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/yeu-cau");
  const status = page.locator("#filter-trang_thai");
  const choices = [
    ["Đã giao", "da_gui"],
    ["Chờ bổ sung linh kiện", "cho_bo_sung_linh_kien"],
    ["Đang thực hiện", "dang_thuc_hien"],
    ["Hoàn thành", "hoan_thanh"],
    ["Đã hủy", "da_huy"],
    ["Tất cả", undefined],
  ];
  for (const [label, value] of choices) {
    await status.click();
    await expect(status).toContainText(label);
    await expect(page.getByRole("listbox")).toHaveCount(0);
    await expect.poll(() => state.calls.filter((call) => call.path === "yeu_cau_san_xuat")
      .at(-1)?.params.trang_thai).toBe(value);
  }
  await status.focus();
  await page.keyboard.press("Enter");
  await expect(status).toContainText("Đã giao");
  await page.keyboard.press("Space");
  await expect(status).toContainText("Chờ bổ sung linh kiện");
  await expect(status).toBeFocused();
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

test("employee live search debounces and reset cancels pending text and restores inventory defaults", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.clock.install();
  await page.goto("/nv/ton-kho");
  await expect(page.getByRole("table")).toBeVisible();
  const search = page.getByPlaceholder("Tìm mã hoặc tên mặt hàng…");
  await search.fill("Kh");
  await search.fill("Khung");
  await search.fill("Khung xe");
  await page.clock.fastForward(350);
  await expect.poll(() => state.calls.filter((call) => call.path === "mat_hang" && call.params.q).length).toBe(1);
  expect(state.calls.find((call) => call.path === "mat_hang" && call.params.q).params.q).toBe("Khung xe");

  await page.locator("#filter-sort").click();
  await expect.poll(() => state.calls.filter((call) => call.path === "mat_hang").at(-1)?.params.sort).toBe("ten_mat_hang");
  await search.fill("must-not-run-after-reset");
  await page.getByRole("button", { name: "Reset tìm kiếm", exact: true }).click();
  await page.clock.fastForward(400);
  await expect(search).toHaveValue("");
  await expect(page.locator("#filter-sort")).toContainText("ID tăng dần");
  await expect.poll(() => state.calls.filter((call) => call.path === "mat_hang").at(-1)?.params.sort).toBe("id");
  expect(state.calls.some((call) => call.params.q === "must-not-run-after-reset")).toBe(false);
  const last = state.calls.filter((call) => call.path === "mat_hang").at(-1).params;
  expect(last.q).toBeUndefined();
  expect(last.page).toBe("1");
  expect(state.unexpected).toEqual([]);
});

test("inventory type and sort buttons wrap to their first choices", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/ton-kho");
  await expect(page.getByRole("table")).toBeVisible();
  const initialCodes = await page.locator("tbody tr td:first-child small").allTextContents();
  expect(initialCodes.length).toBeGreaterThan(0);
  for (const [field, values] of [
    ["loai_mat_hang", ["linh_kien", "thanh_pham", ""]],
    ["is_active", ["true", "false", ""]],
    ["sort", ["ten_mat_hang", "-don_gia", "id"]],
  ]) {
    for (const value of values) {
      await page.locator(`#filter-${field}`).click();
      await expect(page.locator(`input[name='${field}']`)).toHaveValue(value);
      if (value && value !== "id") {
        await expect.poll(() => state.calls.filter((call) => call.path === "mat_hang").at(-1)?.params[field]).toBe(value);
      }
    }
  }
  // Returning to the default query can use cached data, with the same visible rows.
  await expect(page.locator("tbody tr td:first-child small")).toHaveText(initialCodes);
  await expect(page.getByRole("listbox")).toHaveCount(0);
  expect(state.unexpected).toEqual([]);
});

test("automatic date filters block reversed ranges and reset clears even incomplete or invalid dates", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/yeu-cau");
  await page.getByRole("button", { name: "Hiện thêm", exact: true }).click();
  const from = page.getByLabel("Từ ngày", { exact: true });
  const to = page.getByLabel("Đến ngày", { exact: true });
  const reset = page.getByRole("button", { name: "Reset tìm kiếm", exact: true });
  await from.fill("20/11/2026");
  await to.fill("10/11/2026");
  await expect(page.getByRole("alert")).toHaveText("Từ ngày không được sau Đến ngày.");
  expect(state.calls.some((call) => call.params.tu_ngay && call.params.den_ngay
    && call.params.tu_ngay > call.params.den_ngay)).toBe(false);
  await reset.click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(from).toHaveValue("");
  await expect(to).toHaveValue("");

  for (const text of ["12/", "29/02/2027"]) {
    await from.fill(text);
    await expect(from).toHaveAttribute("aria-invalid", "true");
    await reset.click();
    await expect(from).toHaveValue("");
    await expect(from).not.toHaveAttribute("aria-invalid", "true");
    expect(await from.evaluate((input) => input.checkValidity())).toBe(true);
  }
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

test("issue reset clears filters and page while preserving request context, active tab and browser history", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.yeu_cau_san_xuat.find((row) => row.id === 1).nhan_vien_duoc_giao_id = 3;
  state.resources.phieu_xuat = [
    { id: 101, ma_phieu_xuat: "PX-LK-101", loai_phieu: "xuat_linh_kien", yeu_cau_san_xuat_id: 1,
      nhan_vien_id: 3, trang_thai: "cho_duyet", created_at: "2026-11-15T08:00:00Z", chi_tiet: [] },
    { id: 102, ma_phieu_xuat: "PX-TP-102", loai_phieu: "xuat_thanh_pham", yeu_cau_san_xuat_id: 1,
      nhan_vien_id: 3, trang_thai: "cho_duyet", created_at: "2026-11-15T08:00:00Z", chi_tiet: [] },
  ];
  await page.goto("/nv/phieu-xuat?tab=xuat_thanh_pham&yeu_cau_san_xuat_id=1&q=PX&trang_thai=cho_duyet&tu_ngay=2026-11-01&den_ngay=2026-11-30&page=2");
  const search = page.getByPlaceholder("Tìm mã phiếu xuất…");
  await expect(search).toHaveValue("PX");
  await page.getByRole("button", { name: "Reset tìm kiếm", exact: true }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("page")).toBeNull();
  expect([...new URL(page.url()).searchParams.entries()].sort()).toEqual([
    ["tab", "xuat_thanh_pham"], ["yeu_cau_san_xuat_id", "1"],
  ]);
  await expect(search).toHaveValue("");
  await expect(page.locator("#filter-trang_thai")).toContainText("Tất cả");
  await expect(page.getByLabel("Từ ngày", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Đến ngày", { exact: true })).toHaveValue("");
  await expect(page.locator("tbody")).toContainText("PX-TP-102");
  await expect(page.locator("tbody")).not.toContainText("PX-LK-101");
  await page.goBack();
  await expect(search).toHaveValue("PX");
  await expect(page.locator("#filter-trang_thai")).toContainText("Chờ duyệt");
  await expect(page.getByLabel("Từ ngày", { exact: true })).toHaveValue("01/11/2026");
  await page.goForward();
  await expect(search).toHaveValue("");
  await expect(page.locator("tbody")).toContainText("PX-TP-102");
  const query = state.calls.filter((call) => call.path === "phieu_xuat/cua_toi").at(-1).params;
  expect(query.yeu_cau_san_xuat_id).toBe("1");
  expect(query.loai_phieu).toBe("xuat_thanh_pham");
  expect(query.q).toBeUndefined();
  expect(query.page).toBe("1");
});

test("completion filters cycle and reset removes dates, page and other query filters without unsupported search", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/chung-tu-hoan-thanh?mat_hang_id=4&loai_yeu_cau=nhap_kho&page=2");
  const status = page.locator("#filter-trang_thai");
  for (const label of ["Bản nháp", "Chờ duyệt", "Đã duyệt", "Từ chối", "Tất cả"]) {
    await status.click();
    await expect(status).toContainText(label);
  }
  await page.getByLabel("Từ ngày", { exact: true }).fill("01/11/2026");
  await page.getByLabel("Đến ngày", { exact: true }).fill("30/11/2026");
  await expect.poll(() => state.calls.filter((call) => call.path === "chung_tu_hoan_thanh_sx/cua_toi")
    .at(-1)?.params.den_ngay).toBe("2026-11-30");
  await page.getByRole("button", { name: "Reset tìm kiếm", exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/chung-tu-hoan-thanh$/);
  await expect(page.getByLabel("Từ ngày", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Đến ngày", { exact: true })).toHaveValue("");
  await expect(page.getByRole("searchbox")).toHaveCount(0);
  const queries = state.calls.filter((call) => call.path === "chung_tu_hoan_thanh_sx/cua_toi");
  expect(queries.every((call) => call.params.q === undefined && call.params.sort === undefined)).toBe(true);
  expect(state.unexpected).toEqual([]);
});

test("paging while search is waiting applies the keyword on page one instead of losing it", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.mat_hang = Array.from({ length: 25 }, (_, index) => ({
    ...state.resources.mat_hang[0], id: index + 1,
    ma_mat_hang: `MH-${String(index + 1).padStart(6, "0")}`,
    sku: `KHUNG-${index + 1}`, ten_mat_hang: `Khung xe ${index + 1}`,
  }));
  await page.clock.install();
  await page.goto("/nv/ton-kho");
  await expect(page.getByText("Trang 1 / 2")).toBeVisible();
  const search = page.getByPlaceholder("Tìm mã hoặc tên mặt hàng…");
  await search.fill("Khung");
  await page.getByRole("button", { name: "Trang sau", exact: true }).click();
  await page.clock.fastForward(350);
  await expect(search).toHaveValue("Khung");
  await expect.poll(() => state.calls.filter((call) => call.path === "mat_hang").at(-1)?.params.q).toBe("Khung");
  expect(state.calls.filter((call) => call.path === "mat_hang").at(-1).params.page).toBe("1");
});

test("all employee cycle and reset controls fit 375px", async ({ page }) => {
  await installApi(page, { role: "nhan_vien" });
  await page.setViewportSize({ width: 375, height: 812 });
  for (const route of ["/nv/yeu-cau", "/nv/ton-kho", "/nv/phieu-xuat", "/nv/chung-tu-hoan-thanh"]) {
    await page.goto(route);
    await expect(page.getByRole("button", { name: "Reset tìm kiếm", exact: true })).toBeVisible();
    const expand = page.getByRole("button", { name: "Hiện thêm", exact: true });
    if (await expand.count()) await expand.click();
    const controls = page.locator(".btn-dropdown-trigger");
    for (const control of await controls.all()) {
      await control.click();
      const bounds = await control.boundingBox();
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(375);
    }
    const reset = page.getByRole("button", { name: "Reset tìm kiếm", exact: true });
    const bounds = await reset.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(375);
    await expect(page.getByRole("listbox")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  }
});
