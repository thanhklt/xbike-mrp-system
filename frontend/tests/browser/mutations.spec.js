import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("employee profile save confirms via ADM-05 popup and sends profile fields separately from role and account state", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan/3");
  await page.getByRole("button", { name: "Chỉnh sửa", exact: true }).click();
  await page.getByLabel("Họ tên", { exact: true }).fill("Nhân viên cập nhật");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  const dialog = page.locator("dialog.confirmation.confirmation-profile-save");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Xác nhận thay đổi", exact: true })).toBeVisible();
  await expect(dialog).toContainText("Bạn có chắc chắn muốn thay đổi thông tin tài khoản không?");
  await dialog.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("Họ tên", { exact: true })).toHaveValue("Nhân viên cập nhật");
  expect(state.calls.filter((call) => call.method === "PATCH")).toHaveLength(0);

  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  const successDialog = page.locator("dialog.confirmation-save-success");
  await expect(successDialog).toBeVisible();
  await expect(
    successDialog.getByRole("heading", { name: "Lưu thành công", exact: true }),
  ).toBeVisible();
  await successDialog.getByRole("button", { name: "Đóng", exact: true }).click();
  await expect(successDialog).toHaveCount(0);
  const patch = state.calls.find((call) => call.method === "PATCH" && call.path === "nhan_vien/3");
  expect(patch.body.ho_ten).toBe("Nhân viên cập nhật");
  expect(Object.keys(patch.body).sort()).toEqual(
    ["email", "he_so_luong", "ho_ten", "ngay_sinh", "ngay_vao_lam", "so_dien_thoai"].sort(),
  );
  expect(patch.headers["if-match"]).toBe('"v1"');
});

test("deactivating an item keeps its nonzero stock and historical record", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho/mat-hang/4");
  await page.getByRole("button", { name: "Ngừng sử dụng…" }).click();
  await expect(page.locator("dialog.confirmation")).toContainText("Giữ nguyên mặt hàng, số dư tồn");
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page.getByRole("button", { name: "Dùng lại thành phẩm", exact: true })).toBeVisible();
  expect(state.resources.mat_hang[3].so_luong_ton).toBe(18);
  expect(
    state.calls.find((call) => call.path === "mat_hang/4" && call.method === "DELETE").headers[
      "if-match"
    ],
  ).toBe('"v1"');
});

test("BOM creation explicitly confirms activation and sends no state or version fields", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/bom/1");
  await page.getByRole("button", { name: "Tạo phiên bản mới", exact: true }).click();
  await page.getByLabel("Số lượng dòng 1", { exact: true }).fill("2");
  await page.getByRole("button", { name: "Tạo và kích hoạt phiên bản", exact: true }).click();
  await expect(page.locator("dialog.confirmation")).toContainText("ngừng phiên bản hiện hành");
  expect(state.calls.filter((call) => call.path === "bom" && call.method === "POST")).toHaveLength(
    0,
  );
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page).toHaveURL(/\/kho\/bom\/2$/);
  const versionCall = state.calls.find((call) => call.path === "bom/1/phien_ban" && call.method === "POST");
  expect(versionCall.headers["if-match"]).toBe('"v1"');
  expect(versionCall.body).toEqual({
    chi_tiet: [{ mat_hang_id: 1, so_luong: 2 }, { mat_hang_id: 3, so_luong: 2 }],
  });
});

// UC-20 AC-4/5, UC-21: DELETE không body; hoàn tất POST giữ body {} và ETag đã xem.
for (const operation of [
  {
    name: "draft deletion",
    button: "Xóa nháp",
    method: "DELETE",
    suffix: "",
    body: null,
    status: 204,
  },
  {
    name: "completion",
    button: "Hoàn tất nhập kho",
    method: "POST",
    suffix: "/hoan_tat",
    body: "{}",
    status: 200,
  },
]) {
  test(`receipt ${operation.name} sends its required body and the reviewed ETag`, async ({
    page,
  }) => {
    const state = await installApi(page);
    const stock = state.resources.mat_hang.map((item) => item.so_luong_ton);
    const path = `/api/v1/phieu_nhap/1${operation.suffix}`;
    await page.route("**/api/v1/phieu_nhap/1**", async (route) => {
      const request = route.request();
      if (new URL(request.url()).pathname !== path || request.method() !== operation.method) {
        return route.fallback();
      }
      if (request.postData() !== operation.body) {
        return route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify({ error: { message: "Body is not allowed" }, meta: {} }),
        });
      }
      return route.fallback();
    });
    await page.goto("/kho/phieu-nhap/1");
    const detail = page.locator("dialog.record-dialog");
    const confirmation = page.locator("dialog.confirmation");
    await detail.getByRole("button", { name: operation.button, exact: true }).click();
    await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
    expect(state.calls.filter((call) => call.method !== "GET")).toEqual([]);

    await detail.getByRole("button", { name: operation.button, exact: true }).click();
    const requested = page.waitForRequest(
      (request) =>
        new URL(request.url()).pathname === path && request.method() === operation.method,
    );
    const responded = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === path &&
        response.request().method() === operation.method,
    );
    await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();
    const request = await requested;
    expect(request.postData()).toBe(operation.body);
    expect(request.headers()["if-match"]).toBe('"v1"');
    expect((await responded).status()).toBe(operation.status);
    await expect(confirmation).toHaveCount(0);
    if (operation.method === "DELETE") {
      await expect(page).toHaveURL(/\/kho\/phieu-nhap$/);
      expect(state.resources.phieu_nhap.some((record) => record.id === 1)).toBe(false);
      expect(state.resources.mat_hang.map((item) => item.so_luong_ton)).toEqual(stock);
    } else {
      await expect(detail.getByText("Hoàn thành", { exact: true })).toBeVisible();
    }
    expect(state.calls.filter((call) => call.method !== "GET")).toHaveLength(1);
  });
}

// UC-29 AC-2: Bắt đầu ngay trên yêu cầu, không qua xác nhận, gửi ETag chi tiết
test("assigned employee starts a request without a confirmation dialog", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  state.resources.phieu_xuat[0].trang_thai = "da_duyet";
  await page.goto("/nv/yeu-cau/2");
  await page.getByRole("button", { name: "Bắt đầu sản xuất", exact: true }).click();
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  await expect(page.getByText("Bắt đầu sản xuất lúc", { exact: true })).toBeVisible();
  const action = state.calls.find((call) => call.path === "yeu_cau_san_xuat/2/bat_dau");
  expect(action.body).toEqual({});
  expect(action.headers["if-match"]).toBe('"v1"');
});

test("adjustment allows correct quantity zero and sends original ledger ID instead of receipt-line ID", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/dieu-chinh/moi?phieu_nhap_id=2");
  await page.getByLabel("Lý do điều chỉnh", { exact: true }).fill("Phiếu ghi thừa");
  await page.getByLabel("ID giao dịch gốc dòng 1", { exact: true }).fill("101");
  await page.getByLabel("Số lượng đúng dòng 1", { exact: true }).fill("0");
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/dieu-chinh\/2$/);
  expect(
    state.calls.find((call) => call.path === "phieu_dieu_chinh_kho" && call.method === "POST").body,
  ).toEqual({
    phieu_nhap_id: 2,
    ly_do: "Phiếu ghi thừa",
    chi_tiet: [{ giao_dich_goc_id: 101, so_luong_dung: 0 }],
  });
});

test("ticket can be claimed and resolved with a required result without writing stock", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/ticket/1");
  await page.getByRole("button", { name: "Nhận xử lý", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await page.getByRole("button", { name: "Giải quyết", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByLabel("Kết quả xử lý", { exact: true })
    .fill("Đã đối chiếu phiếu nhập, chờ lập điều chỉnh mới");
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await expect(page.getByText("Kết quả xử lý:", { exact: true })).toBeVisible();
  const writes = state.calls.filter((call) => call.method !== "GET");
  expect(writes.map((call) => call.path)).toEqual([
    "ticket_loi_dieu_chinh/1/nhan_xu_ly",
    "ticket_loi_dieu_chinh/1/giai_quyet",
  ]);
  expect(writes[1].headers["if-match"]).toBe('"v2"');
});

test("committed shortage ticket opens from error and closes the failed confirmation", async ({
  page,
}) => {
  await installApi(page, {
    intercept: (call, state) => {
      if (call.path !== "phieu_dieu_chinh_kho/1/xac_nhan") return null;
      state.resources.phieu_dieu_chinh_kho[0].trang_thai = "loi";
      state.versions["phieu_dieu_chinh_kho/1"] = 2;
      return {
        status: 409,
        json: {
          error: {
            code: "khong_du_ton_kho",
            message: "Không đủ tồn kho",
            ticket_id: 1,
            ticket_da_luu: true,
          },
          meta: {},
        },
      };
    },
  });
  await page.goto("/kho/dieu-chinh/1");
  await page.getByRole("button", { name: "Xác nhận điều chỉnh", exact: true }).click();
  await page
    .locator("dialog.confirmation")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click();
  await page.locator("dialog.confirmation").getByRole("link", { name: "#1", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/ticket\/1$/);
  await expect(page.locator("dialog.confirmation")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Chi tiết ticket" })).toBeVisible();
});

test("validation and permission failures remain visible and do not report a successful save", async ({
  page,
}) => {
  let status = 422;
  const state = await installApi(page, {
    intercept: (call) =>
      call.path === "mat_hang/1" && call.method === "PATCH"
        ? {
            status,
            json: {
              error: {
                message: status === 422 ? "Dữ liệu không hợp lệ" : "Không có quyền",
                details: status === 422 ? [{ field: "sku", reason: "SKU đã tồn tại" }] : [],
              },
            },
          }
        : null,
  });
  await page.goto("/kho/mat-hang/1");
  await page.getByLabel("SKU", { exact: true }).fill("DUPLICATE");
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("SKU đã tồn tại");
  status = 403;
  await page.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Không có quyền");
  expect(state.calls.filter((call) => call.method === "PATCH")).toHaveLength(2);
  await expect(page.locator(".toast")).toHaveCount(0);
});
