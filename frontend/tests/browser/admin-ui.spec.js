import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("ADM-01 overview displays 4 KPI cards in order, role distribution including locked accounts, unwired traffic tabs, and 4-column recent activity", async ({
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

  // Traffic controls are present and make no API calls when clicked
  const beforeCalls = state.calls.length;
  await page.getByRole("button", { name: "7 ngày", exact: true }).click();
  await page.getByRole("button", { name: "30 ngày", exact: true }).click();
  expect(state.calls.length).toBe(beforeCalls);

  // Recent activity 4-column table
  const activityHeaders = await page
    .locator(".admin-activity-card th")
    .evaluateAll((nodes) => nodes.map((node) => node.textContent));
  expect(activityHeaders).toEqual(["Thời gian", "Người thực hiện", "Hành động", "Chi tiết"]);
  await expect(page.locator(".admin-activity-card tbody")).toContainText("Nguyễn Văn An");

  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();

  await page.screenshot({ path: "test-results/adm-01-overview-1440x900.png" });
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.screenshot({ path: "test-results/adm-01-overview-1672x941.png" });
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
  await expect(page.locator(".admin-detail-row").nth(5).locator("dd")).toHaveText("••••••••");
  await expect(page.locator(".admin-detail-row").nth(5).locator("input")).toHaveCount(0);
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

test("ADM-04 roles management disables Sửa and Xóa for all 3 system roles by role code, preserves disabled state under search, and simplified logout popup hides inventory impact notice", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/vai-tro");

  await expect(page.getByRole("heading", { name: "Quản lý vai trò", exact: true })).toBeVisible();
  await expect(page.locator(".admin-table tbody tr")).toHaveCount(3);
  await expect(page.locator(".admin-table tbody")).not.toContainText("Cộng tác viên");
  await expect(page.locator(".admin-table tbody")).not.toContainText("Hỗ trợ kỹ thuật");

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

  // Unwired "+ Tạo vai trò" button remains enabled and makes no API calls or fake toasts
  const beforeCalls = state.calls.length;
  await page.getByRole("button", { name: "Tạo vai trò", exact: true }).click();
  expect(state.calls.length).toBe(beforeCalls);
  await expect(page.locator(".toast")).toHaveCount(0);
  await expect(page.locator("dialog[open]")).toHaveCount(0);

  // Client-side search on Enter: "Nhân viên" becomes row 1 and its Sửa button remains disabled
  const search = page.getByLabel("Tìm vai trò", { exact: true });
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
      currentActorCache: queryClient.getQueryData(["resources", 1, "quan_tri_vien", "/nhan_vien/3", {}]),
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
  expect(
    state.calls.filter((c) => c.method === "PATCH" && c.path === "nhan_vien/3"),
  ).toHaveLength(1);
});
