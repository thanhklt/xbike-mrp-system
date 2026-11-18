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
  await expect(page.getByRole("heading", { name: /Tổng quan|Việc được giao/ })).toBeVisible();
});

test("admin sees no warehouse menu or snapshot and direct warehouse URL is denied", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/lich-su");
  await expect(page.getByRole("heading", { name: "Lịch sử thao tác", exact: true })).toBeVisible();
  await expect(page.getByText("MANAGER_ONLY")).toHaveCount(0);
  await expect(page.locator("#main-navigation").getByText("Mặt hàng & tồn kho")).toHaveCount(0);
  await page.goto("/kho/mat-hang");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
  expect(
    state.calls.filter((call) => ["mat_hang", "danh_muc_mat_hang"].includes(call.path)),
  ).toHaveLength(0);
});

test("employee can view issues and needs an assigned request to create, but cannot approve", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/xuat-nvl/1");
  await expect(page.getByRole("heading", { name: "Chi tiết phiếu xuất" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Duyệt phiếu xuất", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Tạo phiếu xuất", exact: true })).toHaveCount(0);
  expect(state.calls.some((call) => call.path === "nhan_vien/2")).toBe(false);
  await page.goto("/nv/xuat-nvl/moi");
  await expect(page.getByText("Mở yêu cầu được giao để lập phiếu xuất.")).toBeVisible();
});

test("saving a receipt keeps it draft and canceling confirmation sends no completion action", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/phieu-nhap/moi");
  await page.locator("dialog.record-dialog").getByLabel("Nhà cung cấp", { exact: true }).selectOption("1");
  await page.getByLabel("Ngày nhập", { exact: true }).fill("17/11/2026");
  await page.getByLabel("Mặt hàng dòng 1", { exact: true }).selectOption("1");
  await page.getByLabel("Số lượng dòng 1", { exact: true }).fill("3");
  await page.getByLabel("Đơn giá dòng 1", { exact: true }).fill("250000");
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/phieu-nhap\/3$/);
  const creation = state.calls.find((call) => call.path === "phieu_nhap" && call.method === "POST");
  expect(creation.body).toMatchObject({
    ncc_id: 1,
    ngay_nhap: "2026-11-17",
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

// UC-29 D6: Gửi yêu cầu v4 không còn tính kế hoạch hoặc tạo lệnh v3
test("sending a draft request requires confirmation and does not create orders", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho/yeu-cau/1");
  expect(state.calls.some((call) => call.path === "yeu_cau_san_xuat/1/gui")).toBeFalsy();
  await page.getByRole("button", { name: "Gửi yêu cầu cho nhân viên" }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  const send = state.calls.find((call) => call.path === "yeu_cau_san_xuat/1/gui");
  expect(send.body).toEqual({});
  expect(send.headers["if-match"]).toBe('"v1"');
  expect(state.calls.some((call) => call.path.startsWith("lenh_san_xuat"))).toBeFalsy();
});

// UC-08 AC-6: Hồ sơ không còn form tự đổi mật khẩu, không gửi request ghi
test("profile displays employee information without a password form", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/ho-so");
  await expect(page.getByRole("heading", { name: "Hồ sơ", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Hồ sơ nhân viên", exact: true })).toBeVisible();
  await expect(page.getByLabel("Mật khẩu hiện tại", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Mật khẩu mới", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Đổi mật khẩu", exact: true })).toHaveCount(0);
  expect(state.calls.some((call) => call.method !== "GET")).toBeFalsy();
});

test("supplier, completed receipt and BOM details omit removed controls and notes", async ({ page }) => {
  const state = await installApi(page);
  const detail = page.locator("dialog.record-dialog");
  await page.goto("/kho/nha-cung-cap/1");
  await expect(detail.getByRole("link", { name: "Xem phiếu nhập của nhà cung cấp →" })).toBeVisible();
  await expect(detail.getByRole("button", { name: "Sửa", exact: true })).toHaveCount(0);
  await expect(detail.getByRole("button", { name: "Xóa…", exact: true })).toHaveCount(0);
  await expect(detail.getByText("API hiện chỉ hỗ trợ xem và tạo nhà cung cấp.")).toHaveCount(0);
  await expect(detail.getByText("Chưa có API xóa nhà cung cấp.")).toHaveCount(0);

  await page.goto("/kho/phieu-nhap/2");
  await expect(detail.getByRole("link", { name: "Tạo phiếu điều chỉnh", exact: true })).toBeVisible();
  await expect(detail.getByRole("button", { name: "Tạo ticket sự cố", exact: true })).toHaveCount(0);
  await expect(detail.getByText(/Ticket chỉ được sinh|Phiếu đã hoàn tất, nội dung bất biến/)).toHaveCount(0);

  await page.goto("/kho/bom/1");
  await expect(detail.getByRole("button", { name: "Tạo phiên bản mới", exact: true })).toBeVisible();
  await expect(detail.getByText(/Nội dung BOM đã lưu bất biến/)).toHaveCount(0);
  expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);
});

// UC-42 R2: Hai trang báo cáo chỉ đọc endpoint reporting, không gọi inventory cũ
test("read-only reports make no requests to unimplemented or legacy stock endpoints", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/thong-ke");
  await page.getByRole("button", { name: "Xem báo cáo", exact: true }).click();
  await expect(page.getByText("Không có mặt hàng thỏa bộ lọc.", { exact: true })).toBeVisible();
  expect(
    state.calls.some((call) => call.method === "GET" && call.path === "bao_cao/nhap_xuat_ton"),
  ).toBeTruthy();
  await page.goto("/kho/giao-dich");
  await expect(
    page.getByRole("heading", { name: "Lịch sử biến động kho", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Chưa có dữ liệu phù hợp.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Lọc", exact: true }).click();
  expect(
    state.calls.some((call) => call.method === "GET" && call.path === "bao_cao/bien_dong_kho"),
  ).toBeTruthy();
  expect(state.calls.some((call) => /inventory/.test(call.path))).toBeFalsy();
  expect(state.calls.some((call) => call.method !== "GET")).toBeFalsy();
  expect(state.unexpected).toEqual([]);
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
    "/admin/mat-hang",
    "/admin/mat-hang/1",
    "/admin/nha-cung-cap",
    "/admin/nha-cung-cap/1",
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
    "/kho/yeu-cau",
    "/kho/yeu-cau/1",
    "/kho/phieu-xuat",
    "/kho/phieu-xuat/moi",
    "/kho/phieu-xuat/2",
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
    "/nv/yeu-cau",
    "/nv/xuat-nvl",
    "/nv/xuat-tp/2",
    "/nv/phieu",
    "/nv/ton-kho/1",
    "/ho-so",
  ],
};
for (const [role, paths] of Object.entries(screens)) {
  test(`${role}: all assigned screens render without runtime errors`, async ({ page }) => {
    if (role === "quan_ly") test.slow();
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
