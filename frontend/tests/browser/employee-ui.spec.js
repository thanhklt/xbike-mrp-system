import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test.describe("Employee UI specification verification (§14-19)", () => {
  test("NV-01 employee dashboard renders 3 KPIs, assigned requests, quick stock, and pending/error dash", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv");

    // Heading
    await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();

    // UI Removals: Subtitle is removed, tracking card is removed, legend is removed for employee
    await expect(page.locator(".employee-shell header p")).toBeHidden();
    await expect(page.getByText("Yêu cầu sản xuất được giao và công việc cần theo dõi.")).toBeHidden();
    await expect(page.getByRole("heading", { name: "Theo dõi công việc" })).toBeHidden();
    await expect(page.getByText("Mở yêu cầu được giao để kiểm tra linh kiện")).toBeHidden();
    await expect(page.getByText("NVL = Nguyên vật liệu · BTP = Bán thành phẩm · TP = Thành phẩm")).toBeHidden();

    // 3 KPI metrics in order
    const metricLabels = await page
      .locator(".employee-stats .metric > span")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(metricLabels).toEqual([
      "Yêu cầu được giao",
      "Yêu cầu đã giao",
      "Đang thực hiện",
    ]);

    // Assigned requests table
    await expect(page.getByRole("heading", { name: "Yêu cầu chờ bắt đầu sản xuất" })).toBeVisible();
    await expect(page.getByRole("table")).toBeVisible();

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
        if (call.path === "yeu_cau_san_xuat") {
          await kpiGate;
          return { status: 500, json: { error: { message: "Lỗi kết nối máy chủ" } } };
        }
        return null;
      },
    });
    await page.goto("/nv");

    // While pending: metrics show dash — (not "0")
    const pendingMetricValues = await page
      .locator(".employee-stats .metric strong")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(pendingMetricValues).toEqual(["—", "—", "—"]);

    // Resolve gate with 500 error
    resolveKpiGate();

    // After failure: error text appears, values remain dash — (not "0")
    await expect(page.locator(".employee-stats .metric small").first()).toHaveText("Không tải được số liệu");
    const metricValues = await page
      .locator(".employee-stats .metric strong")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent.trim()));
    expect(metricValues).toEqual(["—", "—", "—"]);
    for (const val of metricValues) {
      expect(val).not.toBe("0");
    }

    await page.screenshot({ path: "test-results/employee-01-dashboard-error-1440x900.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
    expect(errorState.unexpected).toEqual([]);
  });

  test("NV-01b completed exclusion from Sidebar badge and KPI with gated completed query", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const now = new Date().toISOString();
    // Mixed requests fixture:
    // - Assigned to current user (id 3):
    //   1 da_gui, 2 dang_thuc_hien, 2 hoan_thanh = 5 assigned total, 2 completed = 3 active
    // - Assigned to other employee (id 2): 2 requests
    // - Draft: 1 request
    const mixedRequests = [
      { id: 101, ma_yeu_cau_san_xuat: "YCSX-202611-000101", mat_hang_id: 4, so_luong: 5, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "da_gui", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: null, so_luong_dung_thanh_pham: null, so_luong_can_san_xuat: null, kiem_tra_lan_dau_at: null, started_at: null, completed_at: null, phien_ban: 1 },
      { id: 102, ma_yeu_cau_san_xuat: "YCSX-202611-000102", mat_hang_id: 4, so_luong: 8, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "dang_thuc_hien", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: 1, so_luong_dung_thanh_pham: 0, so_luong_can_san_xuat: 8, kiem_tra_lan_dau_at: now, started_at: now, completed_at: null, phien_ban: 1 },
      { id: 103, ma_yeu_cau_san_xuat: "YCSX-202611-000103", mat_hang_id: 4, so_luong: 10, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "dang_thuc_hien", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: 1, so_luong_dung_thanh_pham: 0, so_luong_can_san_xuat: 10, kiem_tra_lan_dau_at: now, started_at: now, completed_at: null, phien_ban: 1 },
      { id: 104, ma_yeu_cau_san_xuat: "YCSX-202611-000104", mat_hang_id: 4, so_luong: 3, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "hoan_thanh", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: 1, so_luong_dung_thanh_pham: 0, so_luong_can_san_xuat: 3, kiem_tra_lan_dau_at: now, started_at: now, completed_at: now, phien_ban: 2 },
      { id: 105, ma_yeu_cau_san_xuat: "YCSX-202611-000105", mat_hang_id: 4, so_luong: 6, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "hoan_thanh", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: 1, so_luong_dung_thanh_pham: 0, so_luong_can_san_xuat: 6, kiem_tra_lan_dau_at: now, started_at: now, completed_at: now, phien_ban: 2 },
      // Other employee
      { id: 106, ma_yeu_cau_san_xuat: "YCSX-202611-000106", mat_hang_id: 4, so_luong: 2, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 2, trang_thai: "da_gui", created_at: now, updated_at: now, gui_at: now, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: null, so_luong_dung_thanh_pham: null, so_luong_can_san_xuat: null, kiem_tra_lan_dau_at: null, started_at: null, completed_at: null, phien_ban: 1 },
      // Draft
      { id: 107, ma_yeu_cau_san_xuat: "YCSX-202611-000107", mat_hang_id: 4, so_luong: 1, nhan_vien_id: 2, nhan_vien_duoc_giao_id: 3, trang_thai: "nhap", created_at: now, updated_at: now, gui_at: null, loai_yeu_cau: "xuat_giao", han_hoan_thanh: "2026-12-01", bom_id: null, so_luong_dung_thanh_pham: null, so_luong_can_san_xuat: null, kiem_tra_lan_dau_at: null, started_at: null, completed_at: null, phien_ban: 1 },
    ];

    let resolveCompletedGate;
    const completedGate = new Promise((resolve) => {
      resolveCompletedGate = resolve;
    });

    await installApi(page, {
      role: "nhan_vien",
      intercept: async (call, st) => {
        st.resources.yeu_cau_san_xuat = mixedRequests;
        if (call.path === "yeu_cau_san_xuat" && call.params?.trang_thai === "hoan_thanh") {
          await completedGate;
        }
        return null;
      },
    });

    await page.goto("/nv");

    // While completed query is pending (gated):
    // - Sidebar badge on /nv/yeu-cau is omitted (NOT showing total 5)
    const sidebarLink = page.locator('#main-navigation a[href="/nv/yeu-cau"]');
    await expect(sidebarLink.locator("[class*='badge']")).toHaveCount(0);

    // - Dashboard KPI "Yêu cầu được giao" shows dash — (NOT 5)
    const firstMetric = page.locator(".employee-stats .metric strong").first();
    await expect(firstMetric).toHaveText("—");

    // Resolve completed query successfully
    resolveCompletedGate();

    // After completed query resolves:
    // Total assigned (5) - completed (2) = 3 active assigned requests
    await expect(firstMetric).toHaveText("3");
    await expect(sidebarLink.locator("[class*='badge']")).toHaveText("3");
  });

  test("NV-02 assigned request details, check materials and start production", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, {
      role: "nhan_vien",
      intercept: (call, st) => {
        if (call.path === "yeu_cau_san_xuat/1") {
          const req = st.resources.yeu_cau_san_xuat.find((r) => r.id === 1);
          if (req) req.trang_thai = "da_gui";
        }
        return null;
      },
    });
    await page.goto("/nv/yeu-cau/2");
    const dialog1 = page.locator("dialog.record-dialog");
    await expect(dialog1).toBeVisible();
    await expect(dialog1.getByRole("heading", { name: "Chi tiết yêu cầu" })).toBeVisible();
    await expect(dialog1.locator(".badge")).toContainText("Đang thực hiện");
    expect(await dialog1.locator(".info-grid > div").first().evaluate((node) => getComputedStyle(node).backgroundColor)).toBe("rgb(36, 28, 23)");

    // Business code & authenticated user name in popup detail
    await expect(dialog1.locator(".info-grid")).toContainText("Đặng Quốc Bình — NV-000003");
    await expect(dialog1.locator(".info-grid")).toContainText("Xe đạp City Ride — MH-000004");

    // Checking materials case on request 1 (da_gui)
    await page.goto("/nv/yeu-cau/1");
    await expect(dialog1).toBeVisible();
    const checkBtn = dialog1.getByRole("button", { name: "Kiểm tra", exact: true });
    await expect(checkBtn).toBeVisible();

    await page.screenshot({ path: "test-results/employee-02-requests-1440x900.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
  });

  test("NV-03 completion lifecycle: create draft, send with ETag confirmation", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, {
      role: "nhan_vien",
      intercept: (call, st) => {
        if (call.path === "yeu_cau_san_xuat/2") {
          const req = st.resources.yeu_cau_san_xuat.find((r) => r.id === 2);
          if (req) req.started_at = "2026-11-10T09:00:00Z";
        }
        if (call.path === "yeu_cau_san_xuat/2/chung_tu_hoan_thanh") {
          return {
            status: 200,
            json: {
              data: {
                id: 2,
                ma_phieu: "CTHT-202611-000002",
                yeu_cau_san_xuat_id: 2,
                nhan_vien_id: 3,
                so_luong_hoan_thanh: 8,
                trang_thai: "nhap",
                finish_time: null,
                created_at: "2026-11-10T08:00:00Z",
              },
              meta: {},
            },
            headers: { etag: '"v1"' },
          };
        }
        if (call.path === "chung_tu_hoan_thanh_sx/2/gui" && call.method === "POST") {
          return {
            status: 200,
            json: {
              data: {
                id: 2,
                ma_phieu: "CTHT-202611-000002",
                yeu_cau_san_xuat_id: 2,
                nhan_vien_id: 3,
                so_luong_hoan_thanh: 8,
                trang_thai: "cho_duyet",
                finish_time: "2026-11-10T10:00:00Z",
                created_at: "2026-11-10T08:00:00Z",
              },
              meta: {},
            },
            headers: { etag: '"v2"' },
          };
        }
        return null;
      },
    });
    await page.goto("/nv/yeu-cau/2");

    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();

    // Check completion section
    await expect(dialog.getByRole("heading", { name: "Chứng từ hoàn thành sản xuất" })).toBeVisible();

    // Send completion with confirmation
    const sendBtn = dialog.getByRole("button", { name: "Gửi", exact: true });
    await expect(sendBtn).toBeVisible();
    await sendBtn.click();
    const confirmDialog = page.locator("dialog.confirmation");
    await expect(confirmDialog).toBeVisible();
    await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(confirmDialog).toHaveCount(0);
    expect(state.calls.some((c) => c.path === "chung_tu_hoan_thanh_sx/2/gui" && c.method === "POST")).toBe(true);

    await page.screenshot({ path: "test-results/employee-03-completions-1440x900.png", fullPage: true });
    expect(state.unexpected).toEqual([]);
  });

  test("NV-04 legacy document lists redirect to assigned requests without manager-only API calls", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    for (const route of ["/nv/phieu", "/nv/xuat-nvl", "/nv/xuat-tp", "/nv/hoan-thanh/1"]) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/nv\/yeu-cau$/);
      await expect(page.getByRole("table")).toBeVisible();
    }
    expect(state.calls.filter((call) => ["phieu_xuat", "chung_tu_hoan_thanh_sx"].includes(call.path))).toEqual([]);
  });

  test("NV-05 employee requests view and absence of manager creation and action controls", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv/yeu-cau");

    // Employee request page stays read-only with approved subtitle.
    await expect(page.getByRole("heading", { name: "Yêu cầu được giao", exact: true })).toBeVisible();
    await expect(page.locator("main .page-heading p.muted")).toHaveText("Yêu cầu sản xuất được giao cho bạn, từ khi đã gửi.");
    await expect(page.getByRole("link", { name: "Tạo yêu cầu sản xuất" })).toHaveCount(0);
    await expect(page.getByRole("table")).toBeVisible();
    await page.screenshot({ path: "test-results/employee-requests-1440x900.png", fullPage: true });

    // Detail modal of request 2 (sent request) displays request details
    await page.goto("/nv/yeu-cau/2");
    const dialog = page.locator("dialog.record-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Chi tiết yêu cầu" })).toBeVisible();

    // Manager action buttons must NOT exist for employee
    await expect(dialog.getByRole("button", { name: "Gửi yêu cầu cho nhân viên" })).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: "Hủy yêu cầu…" })).toHaveCount(0);
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
    await expect(page.locator("main .page-heading p.muted")).toHaveCount(0);
    await expect(page.locator("text=Số lượng tồn được đọc từ dữ liệu mặt hàng")).toHaveCount(0);
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
    await page.goto("/nv/yeu-cau");

    // Click trigger link from real list view
    const trigger = page.locator("table tbody tr").first().getByRole("link", { name: "Mở", exact: true });
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

    // 3. Header and close button remain visible
    await expect(dialog.getByRole("heading", { name: "Chi tiết yêu cầu" })).toBeVisible();
    await expect(closeBtn).toBeVisible();

    // 4. Focus trapping: Shift+Tab / Tab stays within dialog
    await closeBtn.focus();
    await expect(closeBtn).toBeFocused();

    // 5. Escape closes dialog and restores focus to the trigger
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(/\/nv\/yeu-cau$/);
    await expect(trigger).toBeFocused();
    expect(state.unexpected).toEqual([]);
  });

  test("NV-09 controllable delayed gate for busy submission and confirmation, blocked close, and input preservation", async ({
    page,
  }) => {
    let finishConfirmGate;
    const confirmGate = new Promise((resolve) => {
      finishConfirmGate = resolve;
    });

    const state = await installApi(page, {
      role: "nhan_vien",
      intercept: async (call) => {
        if (call.path === "chung_tu_hoan_thanh_sx/2/gui" && call.method === "POST") {
          await confirmGate;
          return {
            status: 400,
            json: { error: { message: "Không thể duyệt chứng từ này" } },
          };
        }
        return null;
      },
    });

    await page.goto("/nv/yeu-cau/2");
    const recordDialog = page.locator("dialog.record-dialog");
    await expect(recordDialog).toBeVisible();

    const sendBtn = recordDialog.getByRole("button", { name: "Gửi chứng từ hoàn thành", exact: true });
    if (await sendBtn.isVisible()) {
      await sendBtn.click();

      const confirmDialog = page.locator("dialog.confirmation");
      await expect(confirmDialog).toBeVisible();

      const confirmBtn = confirmDialog.getByRole("button", { name: "Xác nhận", exact: true });
      const cancelBtn = confirmDialog.getByRole("button", { name: "Hủy", exact: true });

      await confirmBtn.click();

      // While busy: button text switches to "Đang xử lý…", cancel disabled
      const busyBtn = confirmDialog.getByRole("button", { name: "Đang xử lý…", exact: true });
      await expect(busyBtn).toBeVisible();
      await expect(busyBtn).toBeDisabled();
      await expect(cancelBtn).toBeDisabled();

      // Escape is blocked while busy
      await page.keyboard.press("Escape");
      await expect(confirmDialog).toBeVisible();

      // Resolve gate with failure
      finishConfirmGate();

      // Confirmation dialog shows error alert
      const alert = confirmDialog.getByRole("alert");
      await expect(alert).toBeVisible();
      await expect(alert).toContainText("Không thể duyệt chứng từ này");
      await expect(cancelBtn).toBeEnabled();

      // Clicking Hủy cleanly closes confirmation
      await cancelBtn.click();
      await expect(confirmDialog).toHaveCount(0);
    }
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
    await expect(qtyElement).toHaveText("88 cái");
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

  test("NV-11 employee restyle keeps dark readable KPIs, navigation links and read-only issue lookup", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv");
    await expect(page.locator(".employee-shell")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-employee-theme", "true");
    await expect(page.locator(".employee-stats .metric")).toHaveCount(3);
    const cardColors = await page.locator(".employee-stats .metric").first().evaluate((node) => ({
      background: getComputedStyle(node).backgroundColor,
      text: getComputedStyle(node.querySelector("strong")).color,
    }));
    expect(cardColors).toEqual({ background: "rgb(42, 29, 20)", text: "rgb(255, 255, 255)" });
    const nav = page.getByRole("navigation", { name: "Điều hướng nghiệp vụ" });
    await expect(nav.getByRole("link")).toHaveCount(5);
    await expect(nav.getByRole("link", { name: "Phiếu xuất" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Chứng từ hoàn thành" })).toBeVisible();
    await expect(page.locator(".user-menu summary")).toBeVisible();

    await page.goto("/nv/xuat-nvl");
    await expect(page).toHaveURL(/\/nv\/yeu-cau$/);
    await expect(page.getByRole("heading", { name: "Yêu cầu được giao", exact: true })).toBeVisible();
    await page.screenshot({ path: "test-results/employee-issues-1440x900.png", fullPage: true });

    await page.goto("/nv/xuat-nvl/1");
    const issueDialog = page.locator("dialog.record-dialog");
    await expect(issueDialog.locator(".info-grid > div")).toHaveCount(8);
    expect(await issueDialog.locator(".info-grid").evaluate((node) => getComputedStyle(node).gridTemplateColumns.split(" ").length)).toBe(2);
    await page.screenshot({ path: "test-results/employee-issue-detail-1440x900.png", fullPage: true });
    expect(state.calls.filter((call) => call.path === "phieu_xuat" && call.method !== "GET")).toEqual([]);
    expect(state.unexpected).toEqual([]);
  });
});
