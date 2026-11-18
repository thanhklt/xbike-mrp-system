import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

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
