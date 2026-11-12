import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("login calls the backend with username and password; server profile determines landing page", async ({
  page,
}) => {
  const state = await installApi(page, { authenticated: false });
  await page.goto("/dang-nhap");
  await page.getByLabel("Tên đăng nhập", { exact: true }).fill(" manager ");
  await page.getByLabel("Mật khẩu", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Hiện mật khẩu" }).click();
  await expect(page.getByLabel("Mật khẩu", { exact: true })).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/kho$/);
  const login = state.calls.find((call) => call.path === "auth/dang_nhap");
  expect(login.body).toEqual({ ten_dang_nhap: "manager", mat_khau: "test-password" });
  expect(login.headers.authorization).toBeUndefined();
  expect(
    state.calls.some(
      (call) =>
        call.path === "auth/me" && call.headers.authorization === "Bearer browser-test-token",
    ),
  ).toBeTruthy();
});

test("bad credentials never grant a session or show a dashboard", async ({ page }) => {
  await installApi(page, {
    authenticated: false,
    intercept: (call) =>
      call.path === "auth/dang_nhap"
        ? { status: 401, json: { error: { message: "Thông tin đăng nhập không hợp lệ" } } }
        : null,
  });
  await page.goto("/dang-nhap");
  await page.getByLabel("Tên đăng nhập", { exact: true }).fill("wrong");
  await page.getByLabel("Mật khẩu", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Thông tin đăng nhập không hợp lệ");
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBeNull();
});

test("the latest /auth/me role takes precedence over the earlier login response", async ({
  page,
}) => {
  await installApi(page, {
    authenticated: false,
    intercept: (call, state) => {
      if (call.path === "auth/me") state.role = "nhan_vien";
      return null;
    },
  });
  await page.goto("/dang-nhap");
  await page.getByLabel("Tên đăng nhập", { exact: true }).fill("manager");
  await page.getByLabel("Mật khẩu", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/nv$/);
  await expect(page.getByRole("heading", { name: "Tổng quan công việc", exact: true })).toBeVisible();
});

test("admin sees no warehouse menu or snapshot and direct warehouse URL is denied", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/lich-su");
  await expect(page.getByRole("heading", { name: "Lịch sử thao tác", exact: true })).toBeVisible();
  await expect(page.getByText("MANAGER_ONLY")).toHaveCount(0);
  await expect(page.locator("#main-navigation").getByText("Mặt hàng và tồn kho")).toHaveCount(0);
  await page.goto("/kho/mat-hang");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
  expect(
    state.calls.filter((call) => ["mat_hang", "danh_muc_mat_hang"].includes(call.path)),
  ).toHaveLength(0);
});

test("employee can view issues but cannot create or approve them", async ({ page }) => {
  await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/xuat-nvl/1");
  await expect(page.getByRole("heading", { name: "Chi tiết phiếu xuất" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Duyệt phiếu xuất", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Tạo phiếu xuất", exact: true })).toHaveCount(0);
  await page.goto("/nv/xuat-nvl/moi");
  await expect(page.getByText("Bạn không có quyền lập phiếu xuất.")).toBeVisible();
});

test("saving a receipt keeps it draft and canceling confirmation sends no completion action", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/phieu-nhap/moi");
  await page.locator("form").getByLabel("Nhà cung cấp", { exact: true }).selectOption("1");
  await page.getByLabel("Mặt hàng dòng 1", { exact: true }).selectOption("1");
  await page.getByLabel("Số lượng dòng 1", { exact: true }).fill("3");
  await page.getByLabel("Đơn giá dòng 1", { exact: true }).fill("250000");
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/phieu-nhap\/3$/);
  const creation = state.calls.find((call) => call.path === "phieu_nhap" && call.method === "POST");
  expect(creation.body).toMatchObject({
    ncc_id: 1,
    chi_tiet: [{ mat_hang_id: 1, so_luong: 3, don_gia_thuc: 250000 }],
  });
  expect(creation.body.trang_thai).toBeUndefined();
  await page.getByRole("button", { name: "Hoàn tất nhập kho", exact: true }).click();
  await expect(page.locator("dialog.confirmation")).toContainText("Khung xe");
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Hủy", exact: true })
    .click();
  expect(state.calls.some((call) => call.path.endsWith("/hoan_tat"))).toBeFalsy();
});

test("confirming twice while a write is pending sends exactly one action with reviewed ETag", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const state = await installApi(page, {
    intercept: async (call) => {
      if (call.path === "phieu_nhap/1/hoan_tat") await gate;
      return null;
    },
  });
  await page.goto("/kho/phieu-nhap/1");
  await page.getByRole("button", { name: "Hoàn tất nhập kho", exact: true }).click();
  const confirm = page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true });
  await confirm.click();
  await expect(
    page.locator("dialog.confirmation").getByRole("button", { name: "Đang xử lý…" }),
  ).toBeDisabled();
  await page
    .locator("dialog.confirmation")
    .locator("form")
    .evaluate((form) =>
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })),
    );
  release();
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  const writes = state.calls.filter((call) => call.path === "phieu_nhap/1/hoan_tat");
  expect(writes).toHaveLength(1);
  expect(writes[0].headers["if-match"]).toBe('"v1"');
});

test("stale approval stays failed without retries or a false success message", async ({ page }) => {
  const state = await installApi(page, {
    intercept: (call) =>
      call.path === "phieu_xuat/1/duyet"
        ? {
            status: 412,
            json: {
              error: { code: "du_lieu_da_thay_doi", message: "Dữ liệu đã thay đổi" },
              meta: {},
            },
          }
        : null,
  });
  await page.goto("/kho/phieu-xuat/1");
  await page.getByRole("button", { name: "Duyệt phiếu xuất", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page.locator("dialog.confirmation").getByRole("alert")).toContainText(
    "Tải lại chi tiết",
  );
  expect(state.calls.filter((call) => call.path === "phieu_xuat/1/duyet")).toHaveLength(1);
  await expect(page.locator(".toast")).toHaveCount(0);
});

test("planning is explicit and submitting the plan requires a confirmation", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho/yeu-cau/1");
  await page.getByRole("button", { name: "Tính kế hoạch", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cây lệnh dự kiến" })).toBeVisible();
  expect(state.calls.some((call) => call.path === "yeu_cau_san_xuat/1/gui")).toBeFalsy();
  await page.getByRole("button", { name: "Gửi yêu cầu cho nhân viên" }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  const send = state.calls.find((call) => call.path === "yeu_cau_san_xuat/1/gui");
  expect(send.body).toEqual({ ke_hoach_token: "plan-test-token" });
  expect(send.headers["if-match"]).toBe('"v1"');
  await expect(page.getByText("plan-test-token", { exact: true })).toHaveCount(0);
});

test("changing password invalidates the local session and returns to login", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/ho-so");
  await page.getByLabel("Mật khẩu hiện tại", { exact: true }).fill("old-password");
  await page.getByLabel("Mật khẩu mới", { exact: true }).fill("new-password");
  await page.getByLabel("Nhập lại mật khẩu mới", { exact: true }).fill("new-password");
  await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Đổi mật khẩu", exact: true })
    .click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
  expect(await page.evaluate(() => localStorage.getItem("xbike_access_token"))).toBeNull();
  expect(state.calls.find((call) => call.path === "auth/doi_mat_khau").body).toEqual({
    mat_khau_hien_tai: "old-password",
    mat_khau_moi: "new-password",
  });
});

test("unsupported supplier actions are disabled with visible reasons", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho/nha-cung-cap/1");
  await expect(page.getByRole("button", { name: "Sửa", exact: true })).toBeDisabled();
  await expect(page.getByText("API hiện chỉ hỗ trợ xem và tạo nhà cung cấp.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Xóa…", exact: true })).toBeDisabled();
  expect(state.calls.some((call) => ["PATCH", "DELETE"].includes(call.method))).toBeFalsy();
});

test("read-only reports make no requests to unimplemented or legacy stock endpoints", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/thong-ke");
  await expect(page.getByRole("button", { name: "Xem thống kê" })).toBeDisabled();
  await page.goto("/kho/giao-dich");
  await expect(page.getByRole("button", { name: "Lọc giao dịch" })).toBeDisabled();
  expect(state.calls.some((call) => /inventory|bao_cao/.test(call.path))).toBeFalsy();
});

test("expired authenticated request closes the workflow and returns to login", async ({ page }) => {
  await installApi(page, {
    intercept: (call) =>
      call.path === "phieu_xuat/1/duyet"
        ? { status: 401, json: { error: { message: "Phiên đăng nhập đã hết hạn" } } }
        : null,
  });
  await page.goto("/kho/phieu-xuat/1");
  await page.getByRole("button", { name: "Duyệt phiếu xuất", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page).toHaveURL(/\/dang-nhap$/);
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
});

const screens = {
  quan_tri_vien: [
    "/admin",
    "/admin/tai-khoan",
    "/admin/tai-khoan/moi",
    "/admin/tai-khoan/3",
    "/admin/vai-tro",
    "/admin/lich-su",
    "/ho-so",
  ],
  quan_ly: [
    "/kho",
    "/kho/mat-hang",
    "/kho/mat-hang/moi",
    "/kho/mat-hang/1",
    "/kho/nha-cung-cap/moi",
    "/kho/bom",
    "/kho/bom/moi",
    "/kho/bom/1",
    "/kho/phieu-nhap",
    "/kho/phieu-nhap/2",
    "/kho/yeu-cau/moi",
    "/kho/yeu-cau/2",
    "/kho/lenh-sx",
    "/kho/lenh-sx/1",
    "/kho/phieu-xuat",
    "/kho/phieu-xuat/moi",
    "/kho/phieu-xuat/2",
    "/kho/duyet-hoan-thanh/2",
    "/kho/dieu-chinh",
    "/kho/dieu-chinh/moi",
    "/kho/dieu-chinh/1",
    "/kho/ticket",
    "/kho/ticket/1",
    "/kho/thong-ke",
    "/kho/giao-dich",
    "/kho/lich-su",
  ],
  nhan_vien: [
    "/nv",
    "/nv/yeu-cau/2",
    "/nv/lenh-sx/1",
    "/nv/xuat-nvl",
    "/nv/xuat-tp/2",
    "/nv/hoan-thanh",
    "/nv/hoan-thanh/moi",
    "/nv/hoan-thanh/1",
    "/nv/phieu",
    "/nv/ton-kho/1",
    "/ho-so",
  ],
};
for (const [role, paths] of Object.entries(screens)) {
  test(`${role}: all assigned screens render without runtime errors`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const state = await installApi(page, { role });
    for (const path of paths) {
      await page.goto(path);
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.locator(".loading")).toHaveCount(0);
      await expect(page.locator(".notice-error")).toHaveCount(0);
      expect(errors, `runtime errors on ${path}`).toEqual([]);
      expect(state.unexpected, `unsupported endpoint on ${path}`).toEqual([]);
    }
  });
}

test("mobile navigation and form stay within the viewport; confirmation supports Escape", async ({
  page,
}) => {
  await installApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/kho");
  await page.getByRole("button", { name: "Mở điều hướng" }).click();
  await page
    .locator("#main-navigation")
    .getByRole("link", { name: "Phiếu nhập kho", exact: true })
    .click();
  await expect(page).toHaveURL(/\/kho\/phieu-nhap$/);
  await page.goto("/kho/phieu-nhap/1");
  await page.getByRole("button", { name: "Hoàn tất nhập kho", exact: true }).click();
  await expect(page.locator("dialog.confirmation")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Hoàn tất nhập kho", exact: true })).toBeFocused();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.screenshot({ path: "test-results/mobile-receipt.png", fullPage: true });
});

test("desktop reference captures", async ({ page }) => {
  await installApi(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/kho");
  await expect(page.getByRole("heading", { name: "Tổng quan kho & sản xuất" })).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  await page.screenshot({ path: "test-results/warehouse-dashboard.png", fullPage: true });
  await page.goto("/kho/mat-hang/1");
  await expect(page.getByLabel("Tên mặt hàng", { exact: true })).toHaveValue("Khung xe");
  await page.screenshot({ path: "test-results/items.png", fullPage: true });
});
