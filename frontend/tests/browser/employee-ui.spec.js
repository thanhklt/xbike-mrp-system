import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test.describe("Employee UI specification verification (§14-19)", () => {
  test("NV-01 employee dashboard renders 4 KPIs, assigned requests, recent completions, quick stock, and pending/error dash", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv");

    // Heading and primary action
    await expect(page.getByRole("heading", { name: "Tổng quan công việc", exact: true })).toBeVisible();
    await expect(page.locator(".employee-current-date")).toHaveText(/\d{1,2} tháng \d{1,2}, \d{4}/);
    await expect(
      page.getByRole("link", { name: "Tạo chứng từ hoàn thành SX", exact: true }),
    ).toBeVisible();

    // 4 KPI metrics in order
    const metricLabels = await page
      .locator(".employee-stats .employee-stat-card > span")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(metricLabels).toEqual([
      "Yêu cầu phụ trách",
      "Lệnh đã giao",
      "Đang thực hiện",
      "Hoàn thành chờ duyệt",
    ]);

    // Assigned requests and recent completions use the real resource collections.
    await expect(page.getByRole("table", { name: "Yêu cầu sản xuất được giao" })).toBeVisible();
    const requestTable = page.getByRole("table", { name: "Yêu cầu sản xuất được giao" });
    const requestTabs = page.getByRole("tablist", { name: "Lọc yêu cầu sản xuất đang hiển thị" });
    await expect(requestTabs.getByRole("tab")).toHaveCount(3);
    await expect(requestTable.locator("tbody tr")).toHaveCount(2);
    await requestTabs.getByRole("tab", { name: "Cần sản xuất" }).click();
    await expect(requestTable.locator("tbody tr")).toHaveCount(1);
    await expect(requestTable).toContainText("YCSX-202611-000002");
    await requestTabs.getByRole("tab", { name: "Chờ duyệt chứng từ" }).click();
    await expect(requestTable.locator("tbody tr")).toHaveCount(1);
    await expect(requestTable).toContainText("YCSX-202611-000002");
    expect(state.calls.some((call) => call.path === "chung_tu_hoan_thanh_sx" && call.params.trang_thai === "cho_duyet")).toBe(true);
    await requestTabs.getByRole("tab", { name: "Tất cả" }).click();
    await expect(requestTable.locator("tbody tr")).toHaveCount(2);
    await requestTabs.getByRole("tab", { name: "Tất cả" }).press("ArrowRight");
    await expect(requestTabs.getByRole("tab", { name: "Cần sản xuất" })).toHaveAttribute("aria-selected", "true");
    await requestTabs.getByRole("tab", { name: "Cần sản xuất" }).press("Home");
    await expect(requestTabs.getByRole("tab", { name: "Tất cả" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("table", { name: "Chứng từ hoàn thành gần đây" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Việc tiếp theo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cảnh báo vật tư" })).toBeVisible();

    // Quick stock search interaction
    const searchInput = page.getByLabel("Tìm mã hoặc tên mặt hàng", { exact: true });
    await searchInput.fill("Khung");
    await page.getByRole("button", { name: "Tìm", exact: true }).click();
    await expect(page.locator(".compact-row strong").first()).toContainText("Khung xe");

    // Capture normal dashboard screenshot before introducing error
    await page.screenshot({ path: "test-results/employee-01-dashboard-1440x900.png", fullPage: true });

    // KPI loading and error state test with controllable gate: shows dash — instead of false 0
    let resolveKpiGate;
    const kpiGate = new Promise((resolve) => {
      resolveKpiGate = resolve;
    });

    const errorState = await installApi(page, {
      role: "nhan_vien",
      intercept: async (call) => {
        if (
          call.path === "yeu_cau_san_xuat" ||
          call.path === "lenh_san_xuat" ||
          call.path === "chung_tu_hoan_thanh_sx"
        ) {
          await kpiGate;
          return { status: 500, json: { error: { message: "Lỗi kết nối máy chủ" } } };
        }
        return null;
      },
    });
    await page.goto("/nv");

    // While pending: metrics show dash — (not "0")
    const pendingMetricValues = await page
      .locator(".employee-stats .employee-stat-card strong")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(pendingMetricValues).toEqual(["—", "—", "—", "—"]);

    // Resolve gate with 500 error
    resolveKpiGate();

    // After failure: error text appears, values remain dash — (not "0")
    await expect(page.locator(".employee-stats .employee-stat-card small").first()).toHaveText("Không tải được số liệu");
    const metricValues = await page
      .locator(".employee-stats .employee-stat-card strong")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(metricValues).toEqual(["—", "—", "—", "—"]);
    for (const val of metricValues) {
      expect(val).not.toBe("0");
    }

    await page.screenshot({ path: "test-results/employee-01-dashboard-error-1440x900.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
    expect(errorState.unexpected).toEqual([]);
  });

  test("NV-02 assigned order details, materials table caption, and negative materials disabling start", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    // 1. Order 1 is da_gui with sufficient materials -> Start button enabled
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/lenh-sx/1");
    const dialog1 = page.locator("dialog.record-dialog");
    await expect(dialog1).toBeVisible();
    await expect(dialog1.getByRole("heading", { name: "Chi tiết lệnh sản xuất" })).toBeVisible();
    await expect(dialog1.locator(".progress")).toBeVisible();
    await expect(dialog1.getByRole("table", { name: "Vật tư của lệnh sản xuất" })).toBeVisible();
    await expect(dialog1.getByRole("table", { name: "Chứng từ hoàn thành của lệnh" })).toBeVisible();
    await expect(dialog1.locator(".info-grid > div")).toHaveCount(9);
    await expect(dialog1.locator(".info-grid > div").filter({ hasText: "Trạng thái" })).toContainText("Đã giao");
    expect(await dialog1.locator(".info-grid > div").first().evaluate((node) => getComputedStyle(node).backgroundColor)).toBe("rgb(36, 28, 23)");
    const startBtn = dialog1.getByRole("button", { name: "Bắt đầu sản xuất", exact: true });
    await expect(startBtn).toBeVisible();
    await expect(startBtn).toBeEnabled();

    // 2. Negative materials case: when materials insufficient -> notice warning, button disabled, no mutation
    const stateNegative = await installApi(page, {
      role: "nhan_vien",
      intercept: (call) => {
        if (call.path === "lenh_san_xuat/1/vat_tu") {
          return {
            status: 200,
            json: {
              data: {
                lenh_san_xuat_id: 1,
                du_dieu_kien_bat_dau: false,
                chi_tiet: [
                  {
                    mat_hang_id: 1,
                    so_luong_dinh_muc: 10,
                    so_luong_da_cap: 0,
                    so_luong_con_phai_cap: 10,
                    ton_hien_tai: 0,
                  },
                ],
              },
              meta: {},
            },
          };
        }
        return null;
      },
    });
    await page.goto("/nv/lenh-sx/1");
    await expect(
      dialog1.getByText("Chưa cấp đủ vật tư; chưa thể bắt đầu sản xuất."),
    ).toBeVisible();
    await expect(dialog1.getByRole("button", { name: "Bắt đầu sản xuất", exact: true })).toBeDisabled();
    expect(stateNegative.calls.filter((c) => c.method !== "GET")).toEqual([]);

    // 3. Order 2 is dang_thuc_hien -> Offers "Tạo chứng từ hoàn thành SX"
    await page.goto("/nv/lenh-sx/2");
    const dialog2 = page.locator("dialog.record-dialog");
    await expect(dialog2).toBeVisible();
    await expect(
      dialog2.getByRole("link", { name: "Tạo chứng từ hoàn thành SX", exact: true }),
    ).toBeVisible();

    await page.screenshot({ path: "test-results/employee-02-orders-1440x900.png", fullPage: true });
    await dialog2.getByRole("link", { name: "Tạo chứng từ hoàn thành SX", exact: true }).click();
    await expect(page).toHaveURL(/\/nv\/hoan-thanh\/moi\?lenh_san_xuat_id=2$/);
    await expect(page.getByRole("dialog").getByLabel("Lệnh sản xuất", { exact: true })).toHaveValue("2");
    await expect(page.getByRole("dialog").getByLabel("Lệnh sản xuất", { exact: true })).toBeDisabled();
    await expect(page.getByLabel("Thời điểm hoàn thành (giờ Việt Nam)")).toHaveAttribute("readonly");
    expect(state.unexpected).toEqual([]);
    expect(stateNegative.unexpected).toEqual([]);
  });

  test("NV-03 completion draft lifecycle: creation POST, draft edit PATCH, submit for review, and rejected return-to-draft", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/hoan-thanh/moi");

    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Tạo chứng từ hoàn thành" })).toBeVisible();

    // 1. Create draft (POST)
    const orderSelect = dialog.getByLabel("Lệnh sản xuất", { exact: true });
    await expect(orderSelect).toBeEnabled();
    await orderSelect.selectOption("2");
    await expect(orderSelect).toBeDisabled();
    const finishTime = dialog.getByLabel("Thời điểm hoàn thành (giờ Việt Nam)");
    await expect(finishTime).toHaveAttribute("readonly");
    const initialFinishTime = await finishTime.inputValue();
    expect(initialFinishTime).toMatch(/^\d{4}-\d\d-\d\dT\d\d:\d\d$/);
    await page.getByLabel("Số lượng hoàn thành đợt này", { exact: true }).fill("5");
    await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();

    await expect.poll(() => state.calls.find(
      (call) => call.path === "chung_tu_hoan_thanh_sx" && call.method === "POST",
    )).toBeDefined();
    const postCall = state.calls.find(
      (call) => call.path === "chung_tu_hoan_thanh_sx" && call.method === "POST",
    );
    expect(postCall).toBeDefined();
    expect(postCall.body.lenh_san_xuat_id).toBe(2);
    expect(postCall.body.so_luong_hoan_thanh).toBe(5);
    expect(postCall.body.finish_time).toBe(`${initialFinishTime}:00+07:00`);

    // Switches to detail view
    await expect(page).toHaveURL(/\/nv\/hoan-thanh\/3$/);
    await expect(dialog.getByRole("button", { name: "Gửi duyệt", exact: true })).toBeVisible();

    // 2. Edit draft (PATCH)
    const qtyInput = page.getByLabel("Số lượng hoàn thành đợt này", { exact: true });
    await expect(dialog.getByLabel("Thời điểm hoàn thành (giờ Việt Nam)")).not.toHaveAttribute("readonly");
    await expect(qtyInput).toHaveValue("5");
    await qtyInput.fill("6");
    await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();

    await expect
      .poll(() =>
        state.calls.find(
          (call) => call.path === "chung_tu_hoan_thanh_sx/3" && call.method === "PATCH",
        ),
      )
      .toBeDefined();
    const patchCall = state.calls.find(
      (call) => call.path === "chung_tu_hoan_thanh_sx/3" && call.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    expect(patchCall.body.so_luong_hoan_thanh).toBe(6);

    // 3. Submit for review (POST /gui)
    await dialog.getByRole("button", { name: "Gửi duyệt", exact: true }).click();
    const confirmDialog = page.locator("dialog.confirmation");
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(confirmDialog).toHaveCount(0);

    const guiCall = state.calls.find(
      (call) => call.path === "chung_tu_hoan_thanh_sx/3/gui" && call.method === "POST",
    );
    expect(guiCall).toBeDefined();

    // Toast check: 44x44px hit target
    const toastCloseBtn = page.locator(".toast button");
    await expect(toastCloseBtn).toBeVisible();
    const box = await toastCloseBtn.boundingBox();
    expect(box.width).toBeGreaterThanOrEqual(44);
    expect(box.height).toBeGreaterThanOrEqual(44);

    // 4. Rejected completion return-to-draft (POST /ve_nhap) with required reason
    state.resources.chung_tu_hoan_thanh_sx.push({
      id: 4,
      ma_phieu: "HTSX-202611-000004",
      lenh_san_xuat_id: 2,
      mat_hang_id: 4,
      so_luong_hoan_thanh: 3,
      nhan_vien_id: 3,
      trang_thai: "tu_choi",
      finish_time: "2026-11-10T08:00:00Z",
      created_at: "2026-11-10T08:00:00Z",
    });
    await page.goto("/nv/hoan-thanh/4");
    await expect(dialog.getByRole("button", { name: "Chuyển về bản nháp", exact: true })).toBeVisible();
    await dialog.getByRole("button", { name: "Chuyển về bản nháp", exact: true }).click();

    const returnConfirm = page.locator("dialog.confirmation");
    await expect(returnConfirm).toBeVisible();
    const returnConfirmBtn = returnConfirm.getByRole("button", { name: "Xác nhận", exact: true });
    // Disabled while reason is empty
    await expect(returnConfirmBtn).toBeDisabled();

    // Fill reason and confirm
    await returnConfirm.locator("textarea").fill("Sửa lại số lượng theo biên bản kiểm kê");
    await expect(returnConfirmBtn).toBeEnabled();
    await returnConfirmBtn.click();
    await expect(returnConfirm).toHaveCount(0);

    const veNhapCall = state.calls.find(
      (call) => call.path === "chung_tu_hoan_thanh_sx/4/ve_nhap" && call.method === "POST",
    );
    expect(veNhapCall).toBeDefined();
    expect(veNhapCall.body.ly_do).toBe("Sửa lại số lượng theo biên bản kiểm kê");

    await page.screenshot({ path: "test-results/employee-03-completions-1440x900.png", fullPage: true });
  });

  test("NV-04 My Documents all 3 tabs switching, expected API calls, and filter reset", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/phieu");

    await expect(page.getByRole("heading", { name: "Phiếu của tôi" })).toBeVisible();
    const tabs = page.locator('.tabs button[type="button"]');
    await expect(tabs).toHaveCount(3);

    // Tab 1: Hoàn thành SX của tôi
    await expect(tabs.nth(0)).toHaveAttribute("aria-pressed", "true");
    const statusSelect1 = page.locator("form.filters").getByLabel("Trạng thái", { exact: true });
    await statusSelect1.selectOption("nhap");
    await page.getByRole("button", { name: "Lọc", exact: true }).click();
    expect(
      state.calls.some((c) => c.path === "chung_tu_hoan_thanh_sx" && c.params?.trang_thai === "nhap"),
    ).toBe(true);

    // Tab 2: Phiếu xuất NVL / BTP liên quan
    await tabs.nth(1).click();
    await expect(tabs.nth(1)).toHaveAttribute("aria-pressed", "true");
    await expect(tabs.nth(0)).toHaveAttribute("aria-pressed", "false");
    expect(
      state.calls.some((c) => c.path === "phieu_xuat" && c.params?.loai_phieu === "xuat_vat_tu"),
    ).toBe(true);
    // Filter is reset on tab switch
    const statusSelect2 = page.locator("form.filters").getByLabel("Trạng thái", { exact: true });
    await expect(statusSelect2).toHaveValue("");

    // Tab 3: Phiếu xuất thành phẩm liên quan
    await tabs.nth(2).click();
    await expect(tabs.nth(2)).toHaveAttribute("aria-pressed", "true");
    await expect(tabs.nth(1)).toHaveAttribute("aria-pressed", "false");
    expect(
      state.calls.some((c) => c.path === "phieu_xuat" && c.params?.loai_phieu === "xuat_thanh_pham"),
    ).toBe(true);
    const statusSelect3 = page.locator("form.filters").getByLabel("Trạng thái", { exact: true });
    await expect(statusSelect3).toHaveValue("");

    await page.screenshot({ path: "test-results/employee-04-my-docs-1440x900.png", fullPage: true });
  });

  test("NV-05 employee requests view and absence of manager creation and action controls", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/yeu-cau");

    // Employee request page stays read-only.
    await expect(page.getByRole("heading", { name: "Yêu cầu sản xuất", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tạo yêu cầu thành phẩm" })).toHaveCount(0);
    await expect(page.getByRole("table", { name: "Danh sách yêu cầu sản xuất" })).toBeVisible();
    await page.screenshot({ path: "test-results/employee-requests-1440x900.png", fullPage: true });

    // Detail modal of request 2 (sent request) displays request details and order tree
    await page.goto("/nv/yeu-cau/2");
    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Kế hoạch đã chốt" })).toBeVisible();
    await expect(dialog.locator(".tree a").first()).toHaveAttribute("href", /^\/nv\/lenh-sx\/\d+$/);

    // Manager action buttons must NOT exist for employee
    await expect(dialog.getByRole("button", { name: "Tính kế hoạch" })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "Gửi yêu cầu" })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "Hủy yêu cầu" })).toHaveCount(0);
    await expect(dialog.getByRole("link", { name: "Tạo phiếu xuất thành phẩm" })).toHaveCount(0);

    // Direct access to /nv/yeu-cau/moi displays notice and no form
    await page.goto("/nv/yeu-cau/moi");
    await expect(dialog.getByText("Bạn chỉ có thể xem yêu cầu được giao.")).toBeVisible();
    await expect(dialog.locator("form")).toHaveCount(0);
    expect(state.calls.filter((c) => c.method !== "GET")).toEqual([]);
  });

  test("NV-06 inventory read-only lookup: no add button, no price column, read-only detail", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/ton-kho");

    await expect(page.getByRole("heading", { name: "Tra cứu tồn kho" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Thêm mặt hàng" })).toHaveCount(0);

    const headers = await page.locator("table th").evaluateAll((ths) => ths.map((th) => th.textContent.trim()));
    expect(headers).not.toContain("Đơn giá");
    expect(headers).toContain("Tồn kho");

    await page.goto("/nv/ton-kho/1");
    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Lưu" })).toHaveCount(0);
    await expect(dialog.locator("input")).toHaveCount(0);
    await expect(dialog.locator(".info-grid > div")).toHaveCount(7);
    expect(await dialog.locator(".info-grid").evaluate((node) => getComputedStyle(node).gridTemplateColumns.split(" ").length)).toBe(2);

    await page.screenshot({ path: "test-results/employee-05-inventory-1440x900.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
  });

  test("NV-07 multi-device responsive inspection across breakpoints with single fixture install", async ({
    page,
  }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    const viewports = [
      { name: "desktop-1440x900", width: 1440, height: 900 },
      { name: "desktop-1024x768", width: 1024, height: 768 },
      { name: "tablet-768x1024", width: 768, height: 1024 },
      { name: "mobile-375x812", width: 375, height: 812 },
    ];

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/nv");

      // Verify no horizontal document overflow
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      expect(scrollWidth).toBeLessThanOrEqual(vp.width);

      // Verify user menu accessibility on mobile
      const userSummary = page.locator(".user-menu summary");
      await expect(userSummary).toHaveAttribute("aria-label", /Tài khoản:/);
      if (vp.width === 768) {
        await expect(page.locator("#main-navigation")).toBeVisible();
        await expect(page.getByRole("button", { name: "Mở điều hướng" })).toBeHidden();
      }
      if (vp.width === 375) await expect(page.locator("#main-navigation")).toBeHidden();

      await page.screenshot({
        path: `test-results/employee-responsive-${vp.name}.png`,
        fullPage: true,
      });
    }
    expect(state.unexpected).toEqual([]);
  });

  test("NV-08 mobile 375px dialog bounds, close visibility, internal scroll, focus wrap Tab/Shift+Tab, Escape and return focus", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 600 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/lenh-sx");

    // Click trigger link from real list view
    const trigger = page.locator("table tbody tr").first().getByRole("link", { name: "Xem lệnh →" });
    await trigger.click();

    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();

    // 1. Bounds check: dialog fits mobile viewport
    const dialogBox = await dialog.boundingBox();
    expect(dialogBox.x).toBeGreaterThanOrEqual(0);
    expect(dialogBox.x + dialogBox.width).toBeLessThanOrEqual(375);
    expect(dialogBox.y).toBeGreaterThanOrEqual(0);
    expect(dialogBox.y + dialogBox.height).toBeLessThanOrEqual(600);

    // 2. Close control visibility within viewport
    const closeBtn = dialog.getByRole("button", { name: "Đóng", exact: true });
    await expect(closeBtn).toBeVisible();
    const closeBox = await closeBtn.boundingBox();
    expect(closeBox.x).toBeGreaterThanOrEqual(0);
    expect(closeBox.x + closeBox.width).toBeLessThanOrEqual(375);
    expect(closeBox.y).toBeGreaterThanOrEqual(0);
    expect(closeBox.y + closeBox.height).toBeLessThanOrEqual(600);

    // 3. Internal scroll on .record-dialog .dialog-body
    const dialogBody = dialog.locator(".dialog-body");
    await expect(dialogBody).toBeVisible();
    const isScrollable = await dialogBody.evaluate((el) => el.scrollHeight > el.clientHeight);
    expect(isScrollable).toBe(true);

    await dialogBody.evaluate((el) => {
      el.scrollTop = 100;
    });
    const scrolledTop = await dialogBody.evaluate((el) => el.scrollTop);
    expect(scrolledTop).toBeGreaterThan(0);

    // Header and close button remain visible while body is scrolled
    await expect(dialog.getByRole("heading", { name: "Chi tiết lệnh sản xuất" })).toBeVisible();
    await expect(closeBtn).toBeVisible();

    // 4. Focus trapping boundary wrapping: exact first and last controls
    const refreshBtn = dialog.getByRole("button", { name: "Tải lại chi tiết", exact: true });
    const startBtn = dialog.getByRole("button", { name: "Bắt đầu sản xuất", exact: true });

    await refreshBtn.focus();
    await expect(refreshBtn).toBeFocused();

    // Shift+Tab from first control wraps to last control
    await page.keyboard.press("Shift+Tab");
    await expect(startBtn).toBeFocused();

    // Tab from last control wraps to first control
    await page.keyboard.press("Tab");
    await expect(refreshBtn).toBeFocused();

    // 5. Escape closes dialog and restores focus to the trigger
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/nv\/lenh-sx$/);
    await expect(trigger).toBeFocused();
    expect(state.unexpected).toEqual([]);
  });

  test("NV-09 controllable delayed gate for busy submission and confirmation, blocked close, and input preservation", async ({
    page,
  }) => {
    let finishFormGate;
    const formGate = new Promise((resolve) => {
      finishFormGate = resolve;
    });

    let finishConfirmGate;
    const confirmGate = new Promise((resolve) => {
      finishConfirmGate = resolve;
    });

    const state = await installApi(page, {
      role: "nhan_vien",
      intercept: async (call) => {
        if (call.path === "chung_tu_hoan_thanh_sx" && call.method === "POST") {
          await formGate;
          return null; // succeeds via default handler
        }
        if (call.path === "chung_tu_hoan_thanh_sx/3/gui" && call.method === "POST") {
          await confirmGate;
          return {
            status: 400,
            json: { error: { message: "Không thể duyệt chứng từ này do sai lệch số lượng" } },
          };
        }
        return null;
      },
    });

    // Part 1: Form submit busy state
    await page.goto("/nv/hoan-thanh/moi");
    const recordDialog = page.locator("dialog.record-dialog");
    await expect(recordDialog).toBeVisible();

    await recordDialog.getByLabel("Lệnh sản xuất", { exact: true }).selectOption("2");
    await page.getByLabel("Số lượng hoàn thành đợt này", { exact: true }).fill("5");

    const submitBtn = recordDialog.getByRole("button", { name: "Lưu nháp", exact: true });
    await submitBtn.click();

    // Form button is disabled while in-flight
    await expect(submitBtn).toBeDisabled();

    // Resolve form gate -> finishes creation, transitions to /nv/hoan-thanh/3
    finishFormGate();
    await expect(page).toHaveURL(/\/nv\/hoan-thanh\/3$/);

    // Part 2: Confirmation dialog busy state, blocked controls, and error display
    const sendBtn = recordDialog.getByRole("button", { name: "Gửi duyệt", exact: true });
    await sendBtn.click();

    const confirmDialog = page.locator("dialog.confirmation");
    await expect(confirmDialog).toBeVisible();

    const confirmBtn = confirmDialog.getByRole("button", { name: "Xác nhận", exact: true });
    const cancelBtn = confirmDialog.getByRole("button", { name: "Hủy", exact: true });
    const closeXBtn = confirmDialog.getByRole("button", { name: "Đóng xác nhận", exact: true });

    // Click confirm to start confirmation mutation
    await confirmBtn.click();

    // While busy: button text switches to "Đang xử lý…", all close/cancel controls disabled
    const busyBtn = confirmDialog.getByRole("button", { name: "Đang xử lý…", exact: true });
    await expect(busyBtn).toBeVisible();
    await expect(busyBtn).toBeDisabled();
    await expect(cancelBtn).toBeDisabled();
    await expect(closeXBtn).toBeDisabled();

    // Escape is blocked from closing confirmation dialog while busy
    await page.keyboard.press("Escape");
    await expect(confirmDialog).toBeVisible();

    // Resolve confirm gate with failure
    finishConfirmGate();

    // Confirmation dialog shows error alert, controls re-enabled, modal stays open
    const alert = confirmDialog.getByRole("alert");
    await expect(alert).toBeVisible();
    await expect(alert).toContainText("Không thể duyệt chứng từ này do sai lệch số lượng");
    await expect(cancelBtn).toBeEnabled();

    // Exactly one gui mutation was sent (no duplicate mutation)
    expect(
      state.calls.filter((c) => c.path === "chung_tu_hoan_thanh_sx/3/gui" && c.method === "POST"),
    ).toHaveLength(1);

    // Now clicking Hủy cleanly closes the confirmation dialog
    await cancelBtn.click();
    await expect(confirmDialog).toHaveCount(0);

    // Field value in record dialog is retained
    const qtyInput = recordDialog.getByLabel("Số lượng hoàn thành đợt này", { exact: true });
    await expect(qtyInput).toHaveValue("5");

    // Re-verify no duplicate gui mutation occurred after cancel
    expect(
      state.calls.filter((c) => c.path === "chung_tu_hoan_thanh_sx/3/gui" && c.method === "POST"),
    ).toHaveLength(1);

    expect(state.unexpected).toEqual([]);
  });

  test("NV-10 dashboard QuickStock unbroken long product name wraps within 375px viewport preserving visible stock quantity", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    const state = await installApi(page, { role: "nhan_vien" });

    // Fixture with a 167-character unbroken string (no spaces)
    const unbroken167 = "Khung_xe_dap_the_thao_sieu_ben_chong_gi_chuyen_dung_dia_hinh_hi_end_phien_ban_gioi_han_chinh_hang_nhap_khau_chong_va_dap_chong_bien_dang_kiem_dinh_chat_luong_quoc_te_iso9001_sieu_dai_123456".slice(0, 167);
    expect(unbroken167.length).toBe(167);

    state.resources.mat_hang.unshift({
      id: 999,
      ma_mat_hang: "MH-LONG-167",
      ten_mat_hang: unbroken167,
      sku: "LONG-167",
      loai_mat_hang: "nguyen_vat_lieu",
      don_vi_tinh: "cai",
      so_luong_ton: 88,
      is_active: true,
    });

    await page.goto("/nv");

    const quickStockCard = page.locator(".card", { hasText: "Tra cứu tồn kho nhanh" });
    await expect(quickStockCard).toBeVisible();

    const longRow = quickStockCard.locator(".compact-row").first();
    await expect(longRow).toBeVisible();

    // 1. Verify no horizontal document overflow
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(375);

    // 2. Stock quantity element is visible and within mobile viewport bounds
    const qtyElement = longRow.locator("> strong:last-child");
    await expect(qtyElement).toBeVisible();
    await expect(qtyElement).toHaveText("88 cai");
    const qtyBox = await qtyElement.boundingBox();
    expect(qtyBox).not.toBeNull();
    expect(qtyBox.x).toBeGreaterThan(0);
    expect(qtyBox.x + qtyBox.width).toBeLessThanOrEqual(375);

    // 3. Product name wraps without pushing stock quantity offscreen
    const nameElement = longRow.locator("div strong");
    await expect(nameElement).toBeVisible();
    const nameBox = await nameElement.boundingBox();
    expect(nameBox).not.toBeNull();
    expect(nameBox.x + nameBox.width).toBeLessThanOrEqual(qtyBox.x);
    // Unbroken text wrapped onto multiple lines -> height is greater than single-line ~20px
    expect(nameBox.height).toBeGreaterThan(30);

    await page.screenshot({ path: "test-results/employee-long-name-375px.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
  });

  test("NV-11 employee restyle keeps dark readable KPIs, six menu links, real order filters and read-only issue lookup", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv");
    await expect(page.locator(".employee-shell")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-employee-theme", "true");
    await expect(page.locator(".employee-stat-card")).toHaveCount(4);
    const cardColors = await page.locator(".employee-stat-card").first().evaluate((node) => ({
      background: getComputedStyle(node).backgroundColor,
      text: getComputedStyle(node.querySelector("strong")).color,
    }));
    expect(cardColors).toEqual({ background: "rgb(34, 28, 24)", text: "rgb(255, 255, 255)" });
    const nav = page.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
    await expect(nav.getByRole("link")).toHaveCount(6);
    await expect(page.locator(".user-menu summary")).toBeVisible();
    await expect(page.locator("aside img[src*='employee-bicycle']")).toBeVisible();

    await page.goto("/nv/lenh-sx");
    const filters = page.getByRole("group", { name: "Lọc lệnh theo trạng thái" });
    await expect(filters.getByRole("button")).toHaveCount(4);
    await filters.getByRole("button", { name: /Đang thực hiện/ }).click();
    await expect(filters.getByRole("button", { name: /Đang thực hiện/ })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".employee-progress progress").first()).toBeVisible();
    expect(state.calls.some((call) => call.path === "lenh_san_xuat" && call.params.trang_thai === "dang_thuc_hien")).toBe(true);

    await page.goto("/nv/phieu-xuat");
    await expect(page.getByRole("heading", { name: "Tra cứu phiếu xuất", exact: true })).toBeVisible();
    await expect(page.getByRole("table", { name: "Danh sách phiếu xuất" })).toBeVisible();
    await page.screenshot({ path: "test-results/employee-issues-1440x900.png", fullPage: true });
    await expect(page.getByRole("link", { name: /Tạo phiếu xuất/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Duyệt phiếu/ })).toHaveCount(0);
    await page.getByRole("table", { name: "Danh sách phiếu xuất" }).locator("tbody tr").first().getByRole("link", { name: /Xem phiếu/ }).click();
    const issueDialog = page.locator("dialog.record-dialog");
    await expect(issueDialog.locator(".info-grid > div")).toHaveCount(8);
    await expect(issueDialog.locator(".info-grid > div").filter({ hasText: "Trạng thái" })).toBeVisible();
    expect(await issueDialog.locator(".info-grid").evaluate((node) => getComputedStyle(node).gridTemplateColumns.split(" ").length)).toBe(2);
    await page.screenshot({ path: "test-results/employee-issue-detail-1440x900.png", fullPage: true });
    expect(state.calls.filter((call) => call.path === "phieu_xuat" && call.method !== "GET")).toEqual([]);
    expect(state.unexpected).toEqual([]);
  });
});
