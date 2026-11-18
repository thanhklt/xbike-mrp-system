import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

// The visible format must remain Vietnamese even when the browser locale is English.
test.use({ locale: "en-US", timezoneId: "America/Los_Angeles" });

const cases = [
  ["quan_ly", "/kho/phieu-nhap", "phieu_nhap"],
  ["quan_ly", "/kho/phieu-xuat", "phieu_xuat"],
  ["quan_ly", "/kho/yeu-cau", "yeu_cau_san_xuat"],
  ["quan_ly", "/kho/chung-tu-hoan-thanh", "chung_tu_hoan_thanh_sx"],
  ["quan_ly", "/kho/giao-dich", "bao_cao/bien_dong_kho"],
  ["quan_ly", "/kho/lich-su", "audit"],
  ["quan_ly", "/kho/dieu-chinh", "phieu_dieu_chinh_kho"],
  ["quan_ly", "/kho/ticket", "ticket_loi_dieu_chinh"],
  ["quan_tri_vien", "/admin/lich-su", "audit"],
  ["nhan_vien", "/nv/yeu-cau", "yeu_cau_san_xuat"],
];

for (const [role, path, endpoint] of cases) {
  test(`${path}: date range displays dd/mm/yyyy and queries ISO dates`, async ({ page }) => {
    const state = await installApi(page, { role });
    await page.goto(path);
    if (role === "nhan_vien") {
      await page.getByRole("button", { name: "Hiện thêm", exact: true }).click();
    }
    const from = page.getByLabel("Từ ngày", { exact: true });
    const to = page.getByLabel("Đến ngày", { exact: true });
    await expect(from).toHaveAttribute("placeholder", "dd/mm/yyyy");
    await expect(to).toHaveAttribute("placeholder", "dd/mm/yyyy");
    await from.fill("01/11/2026");
    await to.fill("30/11/2026");
    if (role !== "nhan_vien") {
      await page.getByRole("button", { name: "Lọc", exact: true }).click();
    }
    await expect
      .poll(() =>
        state.calls.some(
          (call) =>
            call.path === endpoint &&
            call.params.tu_ngay === "2026-11-01" &&
            call.params.den_ngay === "2026-11-30",
        ),
      )
      .toBe(true);
    await expect(from).toHaveValue("01/11/2026");
    await expect(to).toHaveValue("30/11/2026");
  });
}

test("date filters reject invalid days/ranges and reset both visible and picker values", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/phieu-nhap");
  const from = page.getByLabel("Từ ngày", { exact: true });
  const to = page.getByLabel("Đến ngày", { exact: true });
  const calls = () => state.calls.filter((call) => call.path === "phieu_nhap").length;
  await expect.poll(calls).toBeGreaterThan(0);
  const before = calls();
  await from.fill("31/02/2026");
  await page.getByRole("button", { name: "Lọc", exact: true }).click();
  expect(await from.evaluate((input) => input.checkValidity())).toBe(false);
  expect(calls()).toBe(before);
  await from.fill("29/02/2024");
  await to.fill("28/02/2024");
  await page.getByRole("button", { name: "Lọc", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Từ ngày không được sau Đến ngày.");
  expect(calls()).toBe(before);
  await page.getByRole("button", { name: "Xóa lọc", exact: true }).click();
  await expect(from).toHaveValue("");
  await expect(to).toHaveValue("");
  await expect(page.locator('input[type="date"]').first()).toHaveValue("");
  expect(await from.evaluate((input) => input.checkValidity())).toBe(true);
});

test("calendar selection formats date filters and receipt dates consistently", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await installApi(page);
  await page.goto("/kho/phieu-nhap");
  const from = page.getByLabel("Từ ngày", { exact: true });
  const fromField = page.locator(".field").filter({ has: from });
  await fromField.getByRole("button", { name: "Chọn ngày", exact: true }).click();
  await page.screenshot({ path: "test-results/date-filter-calendar.png" });
  await page.keyboard.press("Escape");
  await fromField.locator('input[type="date"]').fill("2026-11-13", { force: true });
  await expect(from).toHaveValue("13/11/2026");
  await page.screenshot({ path: "test-results/date-filter-format.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(from).toHaveValue("13/11/2026");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/date-filter-mobile.png", fullPage: true });
  await page.goto("/kho/phieu-nhap/moi");
  await expect(page.getByRole("dialog").getByLabel("Ngày nhập", { exact: true })).toHaveAttribute(
    "type",
    "text",
  );
  await expect(page.getByRole("dialog").getByLabel("Ngày nhập", { exact: true })).toHaveAttribute(
    "placeholder",
    "dd/mm/yyyy",
  );
  expect(errors).toEqual([]);
});

test("receipt create and edit display dd/mm/yyyy while sending ISO dates and rejecting invalid days", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/phieu-nhap/moi");
  const dialog = page.locator("dialog.record-dialog");
  const date = dialog.getByLabel("Ngày nhập", { exact: true });
  await expect(date).toHaveValue("");
  await expect(date).toHaveAttribute("placeholder", "dd/mm/yyyy");
  await dialog.getByLabel("Nhà cung cấp", { exact: true }).selectOption("1");
  await dialog.getByLabel("Mặt hàng dòng 1", { exact: true }).selectOption("1");
  await dialog.getByLabel("Số lượng dòng 1", { exact: true }).fill("2");
  await dialog.getByLabel("Đơn giá dòng 1", { exact: true }).fill("1000");
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  expect(await date.evaluate((input) => input.validity.valueMissing)).toBe(true);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
  await date.fill("31/02/2026");
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  expect(await date.evaluate((input) => input.checkValidity())).toBe(false);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
  await date.fill("17/11/2026");
  await dialog.getByRole("button", { name: "Mở lịch: Ngày nhập", exact: true }).click();
  await page.keyboard.press("Escape");
  await dialog.locator('input[type="date"]').fill("2026-11-18", { force: true });
  await expect(date).toHaveValue("18/11/2026");
  await date.fill("17/11/2026");
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/phieu-nhap\/\d+$/);
  const created = state.calls.find((call) => call.path === "phieu_nhap" && call.method === "POST");
  expect(created.body.ngay_nhap).toBe("2026-11-17");
  expect(created.body).not.toHaveProperty("ma_phieu_nhap");
  await expect(date).toHaveValue("17/11/2026");
  await date.fill("18/11/2026");
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect
    .poll(() => state.calls.find((call) => call.method === "PATCH")?.body.ngay_nhap)
    .toBe("2026-11-18");
  expect(state.calls.find((call) => call.method === "PATCH").headers["if-match"]).toBe('"v1"');
  await expect(date).toHaveValue("18/11/2026");
});

test("production deadline uses dd/mm/yyyy for create and edit while API dates stay ISO", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/yeu-cau/moi");
  const dialog = page.locator("dialog.record-dialog");
  const deadline = dialog.getByLabel("Hạn hoàn thành", { exact: true });
  const create = dialog.getByRole("button", { name: "Tạo", exact: true });
  await expect(deadline).toHaveAttribute("type", "text");
  await expect(deadline).toHaveAttribute("placeholder", "dd/mm/yyyy");
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const buttonBox = await create.boundingBox();
    const formBox = await dialog.locator("form").boundingBox();
    expect(Math.round(buttonBox.height)).toBe(36);
    expect(buttonBox.width).toBeGreaterThanOrEqual(80);
    expect(buttonBox.width).toBeLessThan(160);
    expect(Math.abs(buttonBox.x + buttonBox.width - formBox.x - formBox.width)).toBeLessThan(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await dialog.screenshot({ path: `test-results/request-create-compact-${width}.png` });
  }
  await dialog.getByLabel("Thành phẩm", { exact: true }).selectOption("4");
  await dialog.getByLabel("Số lượng cần", { exact: true }).fill("5");
  await dialog.getByLabel("Nhân viên được giao", { exact: true }).selectOption("3");
  await deadline.fill("31/02/2026");
  await create.click();
  expect(await deadline.evaluate((input) => input.checkValidity())).toBe(false);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
  await deadline.fill("25/11/2026");
  await expect(deadline).toHaveValue("25/11/2026");
  await dialog.getByRole("button", { name: "Mở lịch: Hạn hoàn thành", exact: true }).click();
  await page.keyboard.press("Escape");
  await dialog.locator('input[type="date"]').fill("2026-12-02", { force: true });
  await expect(deadline).toHaveValue("02/12/2026");
  await deadline.fill("25/11/2026");
  await create.click();
  const confirmation = page.locator("dialog.confirmation");
  await expect(confirmation).toBeVisible();
  expect(
    state.calls.find((call) => call.path === "yeu_cau_san_xuat" && call.method === "POST").body
      .han_hoan_thanh,
  ).toBe("2026-11-25");
  await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
  await dialog.getByRole("button", { name: "Sửa", exact: true }).click();
  await expect(deadline).toHaveValue("25/11/2026");
  await deadline.fill("26/11/2026");
  await dialog.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect
    .poll(() => state.calls.find((call) => call.method === "PATCH")?.body.han_hoan_thanh)
    .toBe("2026-11-26");
  expect(state.calls.some((call) => call.path.endsWith("/gui"))).toBe(false);
});
