import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const statuses = [
  ["da_giao", "Đã giao", "rgb(23, 37, 84)"],
  ["cho_duyet_xuat_linh_kien", "Chờ duyệt phiếu xuất linh kiện", "rgb(46, 16, 101)"],
  ["san_sang_san_xuat", "Sẵn sàng sản xuất", "rgb(8, 51, 68)"],
  ["dang_san_xuat", "Đang sản xuất", "rgb(8, 51, 68)"],
  ["cho_duyet_hoan_thanh", "Chờ duyệt chứng từ hoàn thành", "rgb(69, 26, 3)"],
  ["cho_lap_phieu_xuat", "Chờ lập phiếu xuất", "rgb(46, 16, 101)"],
  ["cho_duyet_phieu_xuat", "Chờ duyệt phiếu xuất", "rgb(46, 16, 101)"],
  ["hoan_thanh", "Hoàn thành", "rgb(5, 46, 22)"],
  ["da_huy", "Đã hủy", "rgb(69, 10, 10)"],
];

test("assigned work uses nine labels and six accessible background groups", async ({ page }) => {
  const state = await installApi(page, {
    role: "nhan_vien",
    intercept: (call, fixture) => {
      const rows = statuses.map(([status], index) => ({
        ...fixture.resources.yeu_cau_san_xuat[1], id: index + 10,
        ma_yeu_cau_san_xuat: `YCSX-202611-${String(index + 10).padStart(6, "0")}`,
        trang_thai_cong_viec: status,
      }));
      if (call.method === "GET" && call.path === "yeu_cau_san_xuat")
        return { json: { data: rows, meta: { total: 9, page: 1, page_size: 20, total_pages: 1 } } };
      if (call.method === "GET" && call.path === "yeu_cau_san_xuat/11")
        return { json: { data: rows[1], meta: {} }, headers: { etag: '"work-detail"' } };
    },
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/nv/yeu-cau");
  const badges = page.locator("tbody .badge");
  await expect(badges).toHaveCount(9);
  for (const [index, [, label, background]] of statuses.entries()) {
    await expect(badges.nth(index)).toHaveText(label);
    await expect(badges.nth(index)).toHaveCSS("background-color", background);
  }
  const contrasts = await badges.evaluateAll((elements) => {
    const luminance = (rgb) => rgb.match(/\d+/g).map(Number).map((value) => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    return elements.map((element) => {
      const style = getComputedStyle(element);
      const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => a - b);
      return (values[1] + 0.05) / (values[0] + 0.05);
    });
  });
  expect(contrasts.every((ratio) => ratio >= 4.5)).toBe(true);
  expect(state.calls.some((call) => /^yeu_cau_san_xuat\/\d/.test(call.path))).toBe(false);
  await page.screenshot({ path: "test-results/employee-work-status-desktop.png", fullPage: true });
  await page.getByRole("link", { name: "YCSX-202611-000011", exact: true }).click();
  const detail = page.getByRole("dialog", { name: "Chi tiết yêu cầu" });
  await expect(detail.locator(".badge-work-issue")).toHaveText("Chờ duyệt phiếu xuất linh kiện");
  await expect(detail.getByRole("button", { name: "Bắt đầu sản xuất", exact: true })).toHaveCount(0);
  await detail.getByRole("button", { name: "Đóng", exact: true }).click();
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(badges).toHaveCount(9);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  await page.screenshot({ path: "test-results/employee-work-status-mobile.png", fullPage: true });
});
