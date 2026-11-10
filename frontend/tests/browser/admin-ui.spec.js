import { test, expect } from "@playwright/test";
import { adminActivityEntries, installApi } from "./api-fixture.js";

test("ADM-01 overview displays 4 KPI cards in order, role distribution including locked accounts, traffic chart per range, and 4-column recent activity", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call, current) => {
      if (call.path === "nhan_vien" && call.method === "GET" && !call.params.vai_tro_id) {
        current.resources.nhan_vien[2].trang_thai = "bi_khoa";
      }
      return null;
    },
  });
  state.resources.audit = adminActivityEntries();
  await page.goto("/admin");

  await expect(page.getByRole("heading", { name: "Tổng quan", exact: true })).toBeVisible();
  const statLabels = await page
    .locator(".admin-stat-card .admin-stat-label")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(statLabels).toEqual([
    "Tổng tài khoản",
    "Tổng vai trò",
    "Tài khoản đang hoạt động",
    "Tài khoản đã vô hiệu hóa",
  ]);
  const statValues = await page
    .locator(".admin-stat-card .admin-stat-value")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(statValues).toEqual(["3", "3", "2", "1"]);

  // Donut includes locked account (total 3, each role 1 (33.3%))
  await expect(page.locator(".admin-donut-center strong")).toHaveText("3");
  await expect(page.locator(".admin-donut-legend")).toContainText("Nhân viên: 1 (33.3%)");
  await expect(page.locator(".admin-donut-legend")).toContainText("Quản lý kho: 1 (33.3%)");
  await expect(page.locator(".admin-donut-legend")).toContainText("Quản trị viên: 1 (33.3%)");

  // Traffic chart: today by hour, 7 days by day, 30 days by day with a 7-day average
  const traffic = page.locator(".admin-traffic-card");
  const trafficCalls = () =>
    state.calls.filter((call) => call.path === "luu_luong_truy_cap").map((call) => call.params);
  const xLabels = () =>
    traffic
      .locator(".admin-traffic-xaxis span")
      .evaluateAll((nodes) => nodes.map((n) => n.textContent));
  const todayTab = traffic.getByRole("button", { name: "Hôm nay", exact: true });
  const weekTab = traffic.getByRole("button", { name: "7 ngày", exact: true });
  const monthTab = traffic.getByRole("button", { name: "30 ngày", exact: true });

  await expect(traffic.locator(".admin-traffic-line")).toHaveCount(1);
  expect(trafficCalls()).toEqual([{ khoang_thoi_gian: "hom_nay" }]);
  await expect(todayTab).toHaveAttribute("aria-pressed", "true");
  await expect(traffic.locator(".admin-card-subtitle")).toHaveText(
    "Tổng hợp theo số lượng request mỗi giờ",
  );
  expect(await xLabels()).toEqual(["00h", "03h", "06h", "09h", "12h", "15h", "18h", "21h"]);
  // Hours after the current one (15h) are null: dots only at 00h..15h
  await expect(traffic.locator(".admin-traffic-dot")).toHaveCount(6);
  await expect(traffic.locator(".admin-traffic-legend")).toHaveCount(0);
  await expect(traffic.locator(".admin-traffic-yaxis span").first()).toHaveText("4.000");
  await expect(traffic.locator(".admin-traffic-plot")).toHaveAttribute(
    "aria-label",
    "Biểu đồ lưu lượng truy cập Hôm nay: tổng 26.760 request",
  );

  await weekTab.click();
  await expect(weekTab).toHaveAttribute("aria-pressed", "true");
  await expect(todayTab).toHaveAttribute("aria-pressed", "false");
  await expect(traffic.locator(".admin-traffic-dot")).toHaveCount(7);
  expect(trafficCalls().at(-1)).toEqual({ khoang_thoi_gian: "7_ngay" });
  await expect(traffic.locator(".admin-card-subtitle")).toHaveText(
    "Tổng hợp theo số lượng request mỗi ngày",
  );
  expect(await xLabels()).toEqual(["03/11", "04/11", "05/11", "06/11", "07/11", "08/11", "09/11"]);
  await expect(traffic.locator(".admin-traffic-line.is-average")).toHaveCount(0);
  await expect(traffic.locator(".admin-traffic-yaxis span").first()).toHaveText("40.000");

  await monthTab.click();
  await expect(traffic.locator(".admin-traffic-line.is-average")).toHaveCount(1);
  expect(trafficCalls().at(-1)).toEqual({ khoang_thoi_gian: "30_ngay" });
  expect(await xLabels()).toEqual(["15/10", "20/10", "25/10", "30/10", "04/11", "09/11"]);
  await expect(traffic.locator(".admin-traffic-dot")).toHaveCount(6);
  await expect(traffic.locator(".admin-traffic-legend li")).toHaveText([
    "Request mỗi ngày",
    "Trung bình 7 ngày",
  ]);
  await page.screenshot({ path: "test-results/adm-01-traffic-30-ngay-1440x900.png" });
  await weekTab.click();
  await page.screenshot({ path: "test-results/adm-01-traffic-7-ngay-1440x900.png" });
  await todayTab.click();
  await expect(traffic.locator(".admin-traffic-dot")).toHaveCount(6);

  // Recent activity 4-column table
  const activityHeaders = await page
    .locator(".admin-activity-card th")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(activityHeaders).toEqual(["Thời gian", "Người thực hiện", "Hành động", "Chi tiết"]);
  await expect(page.locator(".admin-activity-card tbody")).toContainText("Nguyễn Văn An");
  expect(state.calls.filter((call) => call.path === "audit").map((call) => call.params)).toEqual([
    {
      page: "1",
      page_size: "5",
      bo_thao_tac: "thu_hoi_quyen",
      sort_by: "created_at",
      sort_order: "desc",
    },
  ]);
  await expect(page.locator(".admin-activity-card tbody tr")).toHaveCount(5);
  await expect(page.locator(".admin-activity-card tbody tr td:last-child")).toHaveText([
    'Tạo vai trò "Quản lý kho".',
    'Gán vai trò "Quản lý kho" cho tài khoản nv005 (Tên lịch sử) (trước đó: "Nhân viên").',
    "Cập nhật thông tin tài khoản nv003 (Tên lịch sử) (số điện thoại, email).",
    "Đăng nhập thành công vào hệ thống.",
    "Vô hiệu hóa tài khoản nv007 (Tên lịch sử) do không còn sử dụng.",
  ]);
  await expect(page.locator(".admin-activity-card tbody tr td:nth-child(3)")).toHaveText([
    "Tạo vai trò",
    "Phân quyền",
    "Cập nhật tài khoản",
    "Đăng nhập",
    "Vô hiệu hóa tài khoản",
  ]);
  await expect(page.locator(".admin-activity-card")).not.toContainText("private@example.test");
  await expect(page.locator(".admin-activity-card")).not.toContainText("0909999999");

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-01-overview-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-01-overview-1672x941.png" });
});

test("admin audit history still renders when the API includes both snapshots", async ({ page }) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/lich-su");
  await expect(page.getByRole("heading", { name: "Lịch sử thao tác", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "hoan_tat", exact: true })).toBeVisible();
  expect(state.calls.filter((call) => call.path === "audit")[0].params.bo_thao_tac).toBeUndefined();
});

test("ADM-02 account list supports Enter search, immediate filters, page reset, select-all on current page, and only 10 rows per page option", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "quan_tri_vien" });
  state.resources.nhan_vien[0].ngay_sinh = "1990-04-12";
  state.resources.nhan_vien[1].ngay_sinh = "1993-09-05";
  state.resources.nhan_vien[2].ngay_sinh = "1995-01-20";
  for (let index = 4; index <= 14; index += 1) {
    state.resources.nhan_vien.push({
      id: index,
      ten_dang_nhap: `user${index}`,
      ma_nhan_vien: `NV-0000${String(index).padStart(2, "0")}`,
      ho_ten: `Nhân sự ${index}`,
      ma_vai_tro: index % 2 === 0 ? "nhan_vien" : "quan_ly",
      vai_tro_id: index % 2 === 0 ? 3 : 2,
      trang_thai: index === 5 ? "bi_khoa" : "hoat_dong",
      email: `user${index}@example.test`,
      so_dien_thoai: "0901112233",
      ngay_sinh: "1995-08-19",
      ngay_vao_lam: "2025-02-10",
      he_so_luong: "2.35",
    });
  }

  await page.goto("/admin/tai-khoan");
  await expect(page.getByRole("heading", { name: "Quản lý tài khoản", exact: true })).toBeVisible();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(10);

  // Page size selector must offer ONLY [10]
  const pageSizeOptions = await page
    .getByLabel("Số dòng mỗi trang", { exact: true })
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => node.value));
  expect(pageSizeOptions).toEqual(["10"]);

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-02-accounts-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-02-accounts-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Select all selects only current page (10 rows)
  const selectAll = page.getByLabel("Chọn tất cả tài khoản trên trang");
  await selectAll.check();
  await expect(page.locator('.admin-table tbody input[type="checkbox"]:checked')).toHaveCount(10);

  // Navigate to page 2 -> resets selection and shows remaining 4 rows
  await page.getByRole("button", { name: "Trang 2", exact: true }).click();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(4);
  await expect(selectAll).not.toBeChecked();

  // Filter by status applies immediately and resets to page 1
  await page.getByLabel("Trạng thái", { exact: true }).selectOption("bi_khoa");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".admin-table tbody")).toContainText("NV-000005");
  expect(state.calls.at(-1).params).toMatchObject({
    page: "1",
    page_size: "10",
    trang_thai: "bi_khoa",
  });

  // Reset status filter, then search on Enter
  await page.getByLabel("Trạng thái", { exact: true }).selectOption("");
  const searchInput = page.getByLabel("Tìm tài khoản", { exact: true });
  await searchInput.fill("Nguyễn Văn An");
  await searchInput.press("Enter");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".admin-table tbody")).toContainText("NV-000002");
});

test("R2-01 list row lock/unlock fetches snapshot before confirmation, uses reviewed ETag on confirm, fails on 412 without re-fetching ETag, and handles cancel or GET failure safely", async ({
  page,
}) => {
  let failGetId3 = false;
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) => {
      if (failGetId3 && call.path === "nhan_vien/3" && call.method === "GET") {
        return {
          status: 500,
          json: { error: { message: "Không tải được chi tiết nhân viên" } },
        };
      }
      return null;
    },
  });

  await page.goto("/admin/tai-khoan");
  await expect(page.getByRole("heading", { name: "Quản lý tài khoản", exact: true })).toBeVisible();

  // 1. Click row lock on NV-000002 -> GET nhan_vien/2 happens BEFORE confirmation opens
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000002", exact: true }).click();
  const dialog = page.locator("dialog.confirmation");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("NV-000002 · Nguyễn Văn An");
  const getCallsBeforeConfirm = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  );
  expect(getCallsBeforeConfirm).toHaveLength(1);

  // 2. Cancel confirmation -> no DELETE write is sent
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "DELETE"),
  ).toHaveLength(0);

  // 3. Re-open confirmation -> snapshot is v1, then external change bumps version to v2 while dialog is open
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000002", exact: true }).click();
  await expect(dialog).toBeVisible();
  const getCountWhenModalOpened = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  ).length;
  state.versions["nhan_vien/2"] = 2;

  await dialog.getByLabel("Lý do").fill("Nghỉ việc");
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  // Expect 412 error inside dialog, no new GET to refresh ETag, no success toast, single DELETE with If-Match: "v1"
  await expect(dialog.getByRole("alert")).toContainText("Dữ liệu đã thay đổi");
  await expect(page.locator(".toast")).toHaveCount(0);
  const getCountAfterConfirm = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "GET",
  ).length;
  expect(getCountAfterConfirm).toBe(getCountWhenModalOpened);
  const deleteCalls = state.calls.filter(
    (call) => call.path === "nhan_vien/2" && call.method === "DELETE",
  );
  expect(deleteCalls).toHaveLength(1);
  expect(deleteCalls[0].headers["if-match"]).toBe('"v1"');

  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);

  // 4. GET failure before confirmation shows error notice and never opens dialog or writes
  failGetId3 = true;
  await page.getByRole("button", { name: "Vô hiệu hóa NV-000003", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText("Không tải được chi tiết nhân viên");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/3" && call.method === "DELETE"),
  ).toHaveLength(0);
});

test("ADM-03 detail view, inline edit, and ADM-05 confirmation/success popups preserve safety policies, masked password, draft on cancel/close, error handling, and prevent duplicate submits", async ({
  page,
}) => {
  let releasePatch;
  const patchGate = new Promise((resolve) => {
    releasePatch = resolve;
  });
  let failNextPatch = false;
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: async (call) => {
      if (call.path === "nhan_vien/2" && call.method === "PATCH") {
        if (failNextPatch) {
          failNextPatch = false;
          return {
            status: 422,
            json: { error: { message: "Hồ sơ nhân viên không hợp lệ" } },
          };
        }
        await patchGate;
      }
      return null;
    },
  });
  state.resources.nhan_vien[1].ngay_sinh = "1990-04-12";
  state.resources.nhan_vien[1].so_dien_thoai = "0901 234 567";

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/admin/tai-khoan/2");

  // Breadcrumb & 10 fields in order
  await expect(page.getByLabel("Đường dẫn trang")).toContainText("Quản lý tài khoản");
  await expect(page.getByLabel("Đường dẫn trang")).toContainText("Chi tiết tài khoản");
  const labels = await page
    .locator(".admin-detail-row dt span")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(labels).toEqual([
    "Họ tên",
    "Ngày sinh",
    "Số điện thoại",
    "Email",
    "Tên đăng nhập",
    "Mật khẩu",
    "Vai trò",
    "Ngày vào làm",
    "Hệ số lương",
    "Trạng thái",
  ]);
  await expect(page.locator(".admin-detail-row").nth(5).locator("dd")).toHaveText("••••••••");
  await expect(page.locator(".admin-detail-row").nth(7).locator("dd")).toHaveText("01/01/2026");
  await expect(page.locator(".admin-detail-row").nth(8).locator("dd")).toHaveText("1.50");

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-03-detail-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-03-detail-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Open inline edit mode and verify 10 rows remain in place with no old form sections
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await expect(page.locator(".admin-detail-row")).toHaveCount(10);
  await expect(page.getByRole("button", { name: "Lưu hồ sơ" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Phân quyền" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Trạng thái tài khoản" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Đặt lại mật khẩu…" })).toHaveCount(0);
  await expect(page.locator(".admin-detail-row").nth(4).locator("dd")).toHaveText("manager");
  await expect(page.locator(".admin-detail-row").nth(4).locator("input")).toHaveCount(0);
  await expect(page.locator("#inline-mat-khau")).toHaveAttribute("type", "password");
  await expect(page.locator("#inline-mat-khau")).toHaveValue("");
  await expect(page.locator("#inline-mat-khau")).toHaveAttribute("placeholder", "Để trống nếu không đổi");
  await expect(page.locator(".admin-detail-row").nth(9).locator("input, select")).toHaveCount(0);

  await page.screenshot({ path: "test-results/adm-03-inline-edit-1440x900.png" });
  await page.setViewportSize({ width: 1670, height: 941 });
  await page.screenshot({ path: "test-results/adm-03-inline-edit-1670x941.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: "test-results/adm-03-inline-edit-375x812.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Top-bar Hủy discards draft and returns to view mode without API calls
  await page.getByLabel("Họ tên", { exact: true }).fill("Bản nháp hủy");
  await page.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Chỉnh sửa", exact: true })).toBeVisible();
  await expect(page.locator(".admin-detail-row").first().locator("dd")).toHaveText("Nguyễn Văn An");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(0);

  // Re-open edit mode and trigger ADM-05 confirmation popup
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Họ tên", { exact: true }).fill("Nguyễn Văn An Mới");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  const dialog = page.locator("dialog.confirmation.confirmation-profile-save");
  await expect(dialog).toBeVisible();

  await page.screenshot({ path: "test-results/adm-05-confirm-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-05-confirm-1672x941.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Cancel button closes dialog without PATCH and keeps draft
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Họ tên", { exact: true })).toHaveValue("Nguyễn Văn An Mới");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(0);

  // Close (X) button closes dialog without PATCH and keeps draft
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Đóng xác nhận", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Họ tên", { exact: true })).toHaveValue("Nguyễn Văn An Mới");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(0);

  // API error keeps dialog open, shows alert, and never shows success popup
  failNextPatch = true;
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Hồ sơ nhân viên không hợp lệ");
  await expect(page.locator("dialog.confirmation-save-success")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();

  // Confirm and verify duplicate submit protection + Save Success popup
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Đang xử lý…" })).toBeDisabled();
  await dialog
    .locator("form")
    .evaluate((form) =>
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
    );
  releasePatch();
  await expect(dialog).toHaveCount(0);

  const successDialog = page.locator("dialog.confirmation-save-success");
  await expect(successDialog).toBeVisible();
  await expect(
    successDialog.getByRole("heading", { name: "Lưu thành công", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/adm-05-save-success-1440x900.png" });
  await page.setViewportSize({ width: 1670, height: 941 });
  await page.screenshot({ path: "test-results/adm-05-save-success-1670x941.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: "test-results/adm-05-save-success-375x812.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  await successDialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(successDialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Chỉnh sửa", exact: true })).toBeVisible();

  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2" && call.method === "PATCH"),
  ).toHaveLength(2); // 1 failed + 1 succeeded
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/2/vai_tro" && call.method === "PUT"),
  ).toHaveLength(0);

  // Admin account (id=1) cannot be locked or downgraded
  await page.goto("/admin/tai-khoan/1");
  await expect(page.getByRole("button", { name: "Vô hiệu hóa", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await expect(page.getByLabel("Vai trò", { exact: true })).toBeDisabled();
});

test("ADM-03 inline edit supports role-only write, combined profile+role ETag chaining, partial-save failure recovery without re-sending saved profile, and 412 without GET retry", async ({
  page,
}) => {
  let failRoleOnce = false;
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) => {
      if (failRoleOnce && call.path === "nhan_vien/3/vai_tro" && call.method === "PUT") {
        failRoleOnce = false;
        return {
          status: 500,
          json: { error: { message: "Lỗi máy chủ khi đổi vai trò" } },
        };
      }
      return null;
    },
  });

  // 1. Direct URL ?mode=edit & Role-only change sends ONLY PUT /vai_tro
  await page.goto("/admin/tai-khoan/3?mode=edit");
  await expect(page.getByLabel("Vai trò", { exact: true })).toHaveValue("3");
  await page.getByLabel("Vai trò", { exact: true }).selectOption("2");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  const confirmDialog = page.locator("dialog.confirmation.confirmation-profile-save");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  const successDialog = page.locator("dialog.confirmation-save-success");
  await expect(successDialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(successDialog).toHaveCount(0);

  expect(
    state.calls.filter((call) => call.path === "nhan_vien/3" && call.method === "PATCH"),
  ).toHaveLength(0);
  const rolePutsAfterRoleOnly = state.calls.filter(
    (call) => call.path === "nhan_vien/3/vai_tro" && call.method === "PUT",
  );
  expect(rolePutsAfterRoleOnly).toHaveLength(1);
  expect(rolePutsAfterRoleOnly[0].headers["if-match"]).toBe('"v1"');
  expect(rolePutsAfterRoleOnly[0].body).toEqual({ vai_tro_id: 2 });

  // 2. Partial save: profile PATCH succeeds ("v2" -> "v3"), role PUT fails -> reports partial save, does NOT show "Lưu thành công", retry sends ONLY PUT /vai_tro with "v3"
  failRoleOnce = true;
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Họ tên", { exact: true }).fill("Đặng Quốc Bình Mới");
  await page.getByLabel("Vai trò", { exact: true }).selectOption("3");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  await expect(confirmDialog.getByRole("alert")).toContainText(
    "Đã lưu thông tin hồ sơ, nhưng cập nhật vai trò thất bại: Lỗi máy chủ khi đổi vai trò",
  );
  await expect(successDialog).toHaveCount(0);
  await confirmDialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Đã lưu thông tin hồ sơ, nhưng cập nhật vai trò thất bại",
  );

  // Retry clicking Lưu -> only PUT /vai_tro is sent with If-Match: "v3"
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(successDialog).toBeVisible();
  await successDialog.getByRole("button", { name: "Đóng", exact: true }).click();

  const patches = state.calls.filter(
    (call) => call.path === "nhan_vien/3" && call.method === "PATCH",
  );
  expect(patches).toHaveLength(1);
  expect(patches[0].headers["if-match"]).toBe('"v2"');

  const rolePuts = state.calls.filter(
    (call) => call.path === "nhan_vien/3/vai_tro" && call.method === "PUT",
  );
  expect(rolePuts).toHaveLength(3); // 1 role-only + 1 failed + 1 retry succeeded
  expect(rolePuts[1].headers["if-match"]).toBe('"v3"');
  expect(rolePuts[2].headers["if-match"]).toBe('"v3"');

  // 3. Combined profile + role save in one pass chains ETag ("v4" -> "v5")
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Số điện thoại", { exact: true }).fill("0912345678");
  await page.getByLabel("Vai trò", { exact: true }).selectOption("2");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(successDialog).toBeVisible();
  await successDialog.getByRole("button", { name: "Đóng", exact: true }).click();

  const latestPatch = state.calls
    .filter((call) => call.path === "nhan_vien/3" && call.method === "PATCH")
    .at(-1);
  const latestPut = state.calls
    .filter((call) => call.path === "nhan_vien/3/vai_tro" && call.method === "PUT")
    .at(-1);
  expect(latestPatch.headers["if-match"]).toBe('"v4"');
  expect(latestPut.headers["if-match"]).toBe('"v5"');

  // 4. Stale ETag (412) on first write aborts second write and does not GET+retry
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Họ tên", { exact: true }).fill("Bình Xung Đột");
  await page.getByLabel("Vai trò", { exact: true }).selectOption("3");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  const getsBefore412 = state.calls.filter(
    (call) => call.path === "nhan_vien/3" && call.method === "GET",
  ).length;
  const putsBefore412 = state.calls.filter(
    (call) => call.path === "nhan_vien/3/vai_tro" && call.method === "PUT",
  ).length;
  state.versions["nhan_vien/3"] = 99;
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmDialog.getByRole("alert")).toContainText("Dữ liệu đã thay đổi");
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/3" && call.method === "GET").length,
  ).toBe(getsBefore412);
  expect(
    state.calls.filter((call) => call.path === "nhan_vien/3/vai_tro" && call.method === "PUT")
      .length,
  ).toBe(putsBefore412);
  await confirmDialog.getByRole("button", { name: "Hủy", exact: true }).click();

  // 5. Creating a new account at /admin/tai-khoan/moi still works
  await page.goto("/admin/tai-khoan/moi");
  const createDialog = page.locator("dialog.record-dialog");
  await expect(createDialog).toBeVisible();
  await createDialog.getByLabel("Tên đăng nhập", { exact: true }).fill("new_staff");
  await createDialog.getByLabel("Mã nhân viên", { exact: true }).fill("NV-000099");
  await createDialog.getByLabel("Mật khẩu ban đầu", { exact: true }).fill("secret123");
  await createDialog.getByLabel("Vai trò", { exact: true }).selectOption("3");
  await createDialog.getByLabel("Họ tên", { exact: true }).fill("Nhân Viên Mới");
  await createDialog.getByRole("button", { name: "Tạo tài khoản", exact: true }).click();
  await expect(page).toHaveURL(/\/admin\/tai-khoan\/4$/);
});

test("ADM-04 shows role descriptions, disables role writes, preserves disabled state under search, and simplified logout popup hides inventory impact notice", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/vai-tro");

  await expect(page.getByRole("heading", { name: "Quản lý vai trò", exact: true })).toBeVisible();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(3);
  await expect(page.locator(".admin-table tbody")).not.toContainText("Cộng tác viên");
  await expect(page.locator(".admin-table tbody")).not.toContainText("Hỗ trợ kỹ thuật");

  for (const role of state.resources.vai_tro) {
    const row = page.getByRole("row").filter({ hasText: role.ten_vai_tro });
    await expect(row.locator(".admin-role-desc")).toHaveText(role.mo_ta);
  }

  const createRole = page.getByRole("button", { name: "Tạo vai trò", exact: true });
  await expect(createRole).toBeDisabled();
  await expect(createRole).toHaveCSS("opacity", "0.55");

  // Page size selector must offer ONLY [10]
  const pageSizeOptions = await page
    .getByLabel("Số dòng mỗi trang", { exact: true })
    .locator("option")
    .evaluateAll((nodes) => nodes.map((node) => node.value));
  expect(pageSizeOptions).toEqual(["10"]);

  // Both Sửa and Xóa buttons for the 3 system roles are disabled by role code
  for (const roleName of ["Quản trị viên", "Quản lý kho", "Nhân viên"]) {
    const editBtn = page.getByRole("button", { name: `Sửa ${roleName}`, exact: true });
    const deleteBtn = page.getByRole("button", { name: `Xóa ${roleName}`, exact: true });
    await expect(editBtn).toBeDisabled();
    await expect(editBtn).toHaveClass(/admin-action-muted/);
    await expect(deleteBtn).toBeDisabled();
  }

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-04-roles-1440x900.png" });
  await page.setViewportSize({ width: 1670, height: 941 });
  await page.screenshot({ path: "test-results/adm-04-roles-1670x941.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: "test-results/adm-04-roles-375x812.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // A real pointer click on the disabled control makes no request or fake toast.
  const beforeCalls = state.calls.length;
  const createBox = await createRole.boundingBox();
  await page.mouse.click(createBox.x + createBox.width / 2, createBox.y + createBox.height / 2);
  expect(state.calls.length).toBe(beforeCalls);
  await expect(page.locator(".toast")).toHaveCount(0);
  await expect(page.locator("dialog[open]")).toHaveCount(0);

  const search = page.getByLabel("Tìm vai trò", { exact: true });
  await search.fill("BOM");
  await search.press("Enter");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.locator(".admin-table tbody tr")).toContainText("Quản lý kho");

  state.resources.vai_tro[2].mo_ta = null;
  await page.reload();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(3);
  await expect(
    page.getByRole("row").filter({ hasText: "Nhân viên" }).locator(".admin-role-desc"),
  ).toHaveText("—");

  // Client-side search on Enter keeps the system role's Sửa button disabled.
  await search.fill("Nhân viên");
  await search.press("Enter");
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Sửa Nhân viên", exact: true })).toBeDisabled();

  // Simplified logout confirmation popup (03-xac-nhan-dang-xuat.png)
  async function triggerLogout() {
    const userMenu = page.locator(".user-menu");
    const isOpen = await userMenu.evaluate((el) => el.hasAttribute("open"));
    if (!isOpen) {
      await page.locator(".user-menu summary").click();
    }
    await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  }

  await triggerLogout();
  const logoutDialog = page.locator("dialog.confirmation.confirmation-logout");
  await expect(logoutDialog).toBeVisible();
  await expect(logoutDialog.getByRole("heading", { name: "Đăng xuất", exact: true })).toBeVisible();
  await expect(logoutDialog).toContainText("Bạn có muốn kết thúc phiên làm việc?");
  await expect(logoutDialog.locator(".notice")).toHaveCount(0);
  await expect(logoutDialog).not.toContainText("Thao tác này không làm thay đổi tồn kho");

  await page.screenshot({ path: "test-results/adm-05-logout-1440x900.png" });
  await page.setViewportSize({ width: 1670, height: 941 });
  await page.screenshot({ path: "test-results/adm-05-logout-1670x941.png" });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: "test-results/adm-05-logout-375x812.png" });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Cancel and close (X) keep the user logged in
  await logoutDialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(logoutDialog).toHaveCount(0);
  await expect(page).toHaveURL(/\/admin\/vai-tro$/);

  await triggerLogout();
  await expect(logoutDialog).toBeVisible();
  await logoutDialog.getByRole("button", { name: "Đóng xác nhận", exact: true }).click();
  await expect(logoutDialog).toHaveCount(0);
  await expect(page).toHaveURL(/\/admin\/vai-tro$/);

  // Confirm logs out to /dang-nhap
  await triggerLogout();
  await logoutDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
});

test("ADM-03 regression: background refetch while confirm is open does not upgrade reviewed ETag or overwrite external changes", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan/2?mode=edit");
  await expect(page.locator("#inline-ho-ten")).toHaveValue(state.resources.nhan_vien[1].ho_ten);

  await page.locator("#inline-ho-ten").fill("Reviewed draft");
  await page.locator(".admin-detail-actions button[type=submit]").click();
  const confirmDialog = page.locator("dialog.confirmation-profile-save[open]");
  await expect(confirmDialog).toBeVisible();

  // External change bumps server version to 2 and modifies phone
  state.resources.nhan_vien[1].so_dien_thoai = "0999999999";
  state.versions["nhan_vien/2"] = 2;

  // Background refetch triggers while confirmation popup is open
  await page.evaluate(async () => {
    const { queryClient } = await import("/src/lib/query-client.js");
    await queryClient.invalidateQueries({ queryKey: ["resources"] });
  });

  // Confirming must send If-Match: "v1" (the reviewed ETag), NOT "v2"
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmDialog.getByRole("alert")).toContainText("Dữ liệu đã thay đổi");
  await expect(page.locator("dialog.confirmation-save-success")).toHaveCount(0);

  const patch = state.calls.find((c) => c.method === "PATCH" && c.path === "nhan_vien/2");
  expect(patch.headers["if-match"]).toBe('"v1"');
  expect(state.resources.nhan_vien[1].so_dien_thoai).toBe("0999999999");
});

test("ADM-03 regression: partial save then cancel reflects saved baseline in view mode and subsequent edit session", async ({
  page,
}) => {
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) =>
      call.path === "nhan_vien/3/vai_tro" && call.method === "PUT"
        ? { status: 500, json: { error: { message: "Role update failed" } } }
        : null,
  });

  await page.goto("/admin/tai-khoan/3?mode=edit");
  const originalName = state.resources.nhan_vien[2].ho_ten;
  await expect(page.locator("#inline-ho-ten")).toHaveValue(originalName);

  await page.locator("#inline-ho-ten").fill("Saved profile");
  await page.locator("#inline-vai-tro").selectOption("2");
  await page.locator(".admin-detail-actions button[type=submit]").click();

  const confirmDialog = page.locator("dialog.confirmation-profile-save[open]");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  await expect(confirmDialog.getByRole("alert")).toContainText(
    "Đã lưu thông tin hồ sơ, nhưng cập nhật vai trò thất bại: Role update failed",
  );
  expect(state.resources.nhan_vien[2].ho_ten).toBe("Saved profile");

  // Close confirmation, then cancel inline edit
  await confirmDialog.getByRole("button", { name: "Đóng xác nhận", exact: true }).click();
  await page.getByRole("button", { name: "Hủy", exact: true }).click();

  // View mode must truthfully display "Saved profile" (not stale original name)
  await expect(page.locator(".admin-detail-row").first().locator("dd")).toHaveText("Saved profile");

  // Re-opening edit must initialize from the saved baseline
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await expect(page.locator("#inline-ho-ten")).toHaveValue("Saved profile");
});

test("ADM-03 regression: missing new ETag in profile response halts role write with 428 and keeps draft", async ({
  page,
}) => {
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) =>
      call.path === "nhan_vien/3" && call.method === "PATCH"
        ? {
            status: 200,
            json: { data: { ho_ten: "ETag Missing Test" }, meta: {} },
            headers: {}, // Omit ETag
          }
        : null,
  });

  await page.goto("/admin/tai-khoan/3?mode=edit");
  await page.locator("#inline-ho-ten").fill("ETag Missing Test");
  await page.locator("#inline-vai-tro").selectOption("2");
  await page.locator(".admin-detail-actions button[type=submit]").click();

  const confirmDialog = page.locator("dialog.confirmation-profile-save[open]");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

  await expect(confirmDialog.getByRole("alert")).toContainText(
    "Phản hồi lưu hồ sơ không trả về ETag mới để tiếp tục cập nhật vai trò",
  );
  expect(
    state.calls.filter((c) => c.path === "nhan_vien/3/vai_tro" && c.method === "PUT"),
  ).toHaveLength(0);
});

test("ADM-03 regression: cache update scopes strictly to current actor/role and does not mutate other user or role projections", async ({
  page,
}) => {
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) =>
      call.path === "nhan_vien/3/vai_tro" && call.method === "PUT"
        ? { status: 500, json: { error: { message: "Role update failed" } } }
        : null,
  });

  await page.goto("/admin/tai-khoan/3?mode=edit");
  await expect(page.locator("#inline-ho-ten")).toBeVisible();

  // Seed another-user cache entry and same-user/different-role cache entry with distinct markers
  await page.evaluate(async () => {
    const { queryClient } = await import("/src/lib/query-client.js");
    queryClient.setQueryData(["resources", 999, "quan_ly", "/nhan_vien/3", {}], {
      data: { id: 3, ho_ten: "Other User Projection", email: "other@example.test" },
      etag: '"other-v1"',
    });
    queryClient.setQueryData(["resources", 1, "quan_ly", "/nhan_vien/3", {}], {
      data: { id: 3, ho_ten: "Same User Different Role Projection", email: "role@example.test" },
      etag: '"role-v1"',
    });
  });

  // Edit profile and role, triggering partial save (profile succeeds, role fails)
  await page.locator("#inline-ho-ten").fill("Scoped Saved Profile");
  await page.locator("#inline-vai-tro").selectOption("2");
  await page.locator(".admin-detail-actions button[type=submit]").click();

  const confirmDialog = page.locator("dialog.confirmation-profile-save[open]");
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmDialog.getByRole("alert")).toContainText(
    "Đã lưu thông tin hồ sơ, nhưng cập nhật vai trò thất bại: Role update failed",
  );

  // Inspect the two foreign projections in queryClient
  const { otherUserCache, diffRoleCache, currentActorCache } = await page.evaluate(async () => {
    const { queryClient } = await import("/src/lib/query-client.js");
    return {
      otherUserCache: queryClient.getQueryData(["resources", 999, "quan_ly", "/nhan_vien/3", {}]),
      diffRoleCache: queryClient.getQueryData(["resources", 1, "quan_ly", "/nhan_vien/3", {}]),
      currentActorCache: queryClient.getQueryData([
        "resources",
        1,
        "quan_tri_vien",
        "/nhan_vien/3",
        {},
      ]),
    };
  });

  // Foreign projections must remain completely untouched
  expect(otherUserCache.data.ho_ten).toBe("Other User Projection");
  expect(otherUserCache.data.email).toBe("other@example.test");
  expect(diffRoleCache.data.ho_ten).toBe("Same User Different Role Projection");
  expect(diffRoleCache.data.email).toBe("role@example.test");

  // Current actor's cache must hold the truthful partial-save baseline
  expect(currentActorCache.data.ho_ten).toBe("Scoped Saved Profile");
  expect(currentActorCache.etag).toBe('"v2"');
  expect(state.calls.filter((c) => c.method === "PATCH" && c.path === "nhan_vien/3")).toHaveLength(
    1,
  );
});

test("ADM-03 password input toggles, validates, discards on cancel and skips blank resets", async ({ page }) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan/2");
  const passwordRow = page.locator(".admin-detail-row").nth(5);
  await expect(passwordRow.locator("dd")).toHaveText("••••••••");
  await expect(passwordRow.locator("input")).toHaveCount(0);
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  const input = page.locator("#inline-mat-khau");
  await expect(input).toHaveAttribute("autocomplete", "new-password");
  await expect(input).toHaveAttribute("maxlength", "1024");
  expect(await input.getAttribute("minlength")).toBeNull();
  await page.getByRole("button", { name: "Hiện mật khẩu", exact: true }).click();
  await expect(input).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Ẩn mật khẩu", exact: true }).click();
  await expect(input).toHaveAttribute("type", "password");

  // Seven characters fail before opening confirmation or issuing any write.
  await input.fill("1234567");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Mật khẩu mới phải có từ 8 đến 1024 ký tự.");
  await expect(page.locator("dialog")).toHaveCount(0);
  expect(state.calls.filter((call) => call.method !== "GET")).toHaveLength(0);

  await input.fill("draft-password");
  await page.getByRole("button", { name: "Hiện mật khẩu", exact: true }).click();
  await page.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(passwordRow.locator("dd")).toHaveText("••••••••");
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await expect(input).toHaveValue("");
  await expect(input).toHaveAttribute("type", "password");

  // Blank password permits a normal profile save without a reset request.
  await page.getByLabel("Email", { exact: true }).fill("blank-reset@example.test");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page.locator("dialog.confirmation-save-success")).toBeVisible();
  expect(state.calls.filter((call) => call.path.endsWith("/dat_lai_mat_khau"))).toHaveLength(0);
  await page.getByRole("button", { name: "Đóng", exact: true }).click();
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page.locator("#inline-mat-khau")).toHaveCount(0);
  await expect(page.locator("dialog")).toHaveCount(0);
});

for (const changeRole of [false, true]) {
  test(`ADM-03 reset follows profile${changeRole ? " and role" : ""} with chained If-Match and clears secret`, async ({ page }) => {
    const state = await installApi(page, { role: "quan_tri_vien" });
    state.resources.nhan_vien[2].trang_thai = "bi_khoa";
    await page.goto("/admin/tai-khoan/3?mode=edit");
    await page.getByLabel("Email", { exact: true }).fill("reset-target@example.test");
    if (changeRole) await page.getByLabel("Vai trò", { exact: true }).selectOption("2");
    const password = " new-password-with-spaces ";
    await page.locator("#inline-mat-khau").fill(password);
    await page.getByRole("button", { name: "Lưu", exact: true }).click();
    await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(page.locator("dialog.confirmation-save-success")).toBeVisible();
    const writes = state.calls.filter((call) => call.method !== "GET");
    expect(writes.map((call) => `${call.method} ${call.path}`)).toEqual([
      "PATCH nhan_vien/3",
      ...(changeRole ? ["PUT nhan_vien/3/vai_tro"] : []),
      "POST nhan_vien/3/dat_lai_mat_khau",
    ]);
    expect(writes.map((call) => call.headers["if-match"])).toEqual(changeRole ? ['"v1"', '"v2"', '"v3"'] : ['"v1"', '"v2"']);
    expect(writes.at(-1).body).toEqual({ mat_khau_moi: password });
    await expect(page.locator("#inline-mat-khau")).toHaveCount(0);
    expect(await page.content()).not.toContain(password);
    expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(password);
    expect(page.url()).not.toContain(password.trim());
    await page.getByRole("button", { name: "Đóng", exact: true }).click();
    await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
    await expect(page.locator("#inline-mat-khau")).toHaveValue("");
  });
}

for (const reopenDialog of [false, true]) {
  test(`ADM-03 failed password reset preserves draft and retries only reset${reopenDialog ? " after reopening confirmation" : " in confirmation"}`, async ({ page }) => {
    let failOnce = true;
    const state = await installApi(page, {
      role: "quan_tri_vien",
      intercept: (call) => {
        if (failOnce && call.path === "nhan_vien/3/dat_lai_mat_khau") {
          failOnce = false;
          return { status: 500, json: { error: { message: "Lỗi đặt lại mật khẩu" } } };
        }
        return null;
      },
    });
    await page.goto("/admin/tai-khoan/3?mode=edit");
    await page.getByLabel("Email", { exact: true }).fill("partial-reset@example.test");
    await page.getByLabel("Vai trò", { exact: true }).selectOption("2");
    await page.locator("#inline-mat-khau").fill("retry-password");
    await page.getByRole("button", { name: "Lưu", exact: true }).click();
    const dialog = page.locator("dialog.confirmation-profile-save");
    await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText("Đã lưu thông tin hồ sơ và vai trò, nhưng đặt lại mật khẩu thất bại: Lỗi đặt lại mật khẩu");
    await expect(page.locator("dialog.confirmation-save-success")).toHaveCount(0);
    await expect(page.locator("#inline-mat-khau")).toHaveValue("retry-password");
    if (reopenDialog) {
      await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
      await page.getByRole("button", { name: "Lưu", exact: true }).click();
    }
    await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(page.locator("dialog.confirmation-save-success")).toBeVisible();
    const writes = state.calls.filter((call) => call.method !== "GET");
    expect(writes.map((call) => call.method)).toEqual(["PATCH", "PUT", "POST", "POST"]);
    expect(writes.slice(-2).map((call) => call.headers["if-match"])).toEqual(['"v3"', '"v3"']);
  });
}

test("ADM-03 self reset logs in immediately with new password before any authenticated refetch", async ({ page }) => {
  let releaseLogin;
  const loginGate = new Promise((resolve) => { releaseLogin = resolve; });
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: async (call) => {
      if (call.path === "auth/dang_nhap") await loginGate;
      return null;
    },
  });
  await page.goto("/admin/tai-khoan/1?mode=edit");
  const password = "self-reset-password";
  await page.locator("#inline-mat-khau").fill(password);
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect.poll(() => state.calls.some((call) => call.path === "auth/dang_nhap")).toBe(true);
  const resetIndex = state.calls.findIndex((call) => call.path.endsWith("/dat_lai_mat_khau"));
  expect(state.calls.slice(resetIndex + 1).map((call) => call.path)).toEqual(["auth/dang_nhap"]);
  const login = state.calls.at(-1);
  expect(login.body).toEqual({ ten_dang_nhap: "admin", mat_khau: password });
  expect(login.headers.authorization).toBeUndefined();
  await expect(page.locator("#inline-mat-khau")).toBeDisabled();
  releaseLogin();
  await expect(page.locator("dialog.confirmation-save-success")).toBeVisible();
  await expect(page).toHaveURL(/\/admin\/tai-khoan\/1$/);
  const afterReset = state.calls.slice(resetIndex + 1);
  expect(afterReset[1].path).toBe("auth/me");
  for (const call of afterReset.slice(1)) expect(call.headers.authorization).toBe("Bearer browser-test-token-renewed");
  await expect(page.locator("#inline-mat-khau")).toHaveCount(0);
  expect(await page.content()).not.toContain(password);
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(password);
  expect(state.unexpected).toEqual([]);
});

test("ADM-03 self reset login failure logs out with the agreed notice", async ({ page }) => {
  const state = await installApi(page, {
    role: "quan_tri_vien",
    intercept: (call) => call.path === "auth/dang_nhap"
      ? { status: 500, json: { error: { message: "Lỗi đăng nhập" } } }
      : null,
  });
  await page.goto("/admin/tai-khoan/1?mode=edit");
  await page.locator("#inline-mat-khau").fill("fallback-password");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await page.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
  await expect(page.getByRole("status")).toContainText("Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.");
  await expect(page.locator("dialog.confirmation-save-success")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBeNull();
  const resetIndex = state.calls.findIndex((call) => call.path.endsWith("/dat_lai_mat_khau"));
  expect(state.calls.slice(resetIndex + 1).map((call) => call.path)).toEqual(["auth/dang_nhap"]);
  expect(await page.content()).not.toContain("fallback-password");
});
