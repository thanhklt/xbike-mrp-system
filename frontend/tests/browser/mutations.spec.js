import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test("employee profile save sends profile fields separately from role and account state", async ({
  page,
}) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan/3");
  await page.getByLabel("Họ tên", { exact: true }).fill("Nhân viên cập nhật");
  await page.getByRole("button", { name: "Lưu hồ sơ" }).click();
  await expect(page.locator(".toast")).toContainText("Đã lưu");
  const patch = state.calls.find((call) => call.method === "PATCH" && call.path === "nhan_vien/3");
  expect(patch.body.ho_ten).toBe("Nhân viên cập nhật");
  expect(Object.keys(patch.body).sort()).toEqual(
    ["email", "he_so_luong", "ho_ten", "ngay_sinh", "ngay_vao_lam", "so_dien_thoai"].sort(),
  );
  expect(patch.headers["if-match"]).toBe('"v1"');
});

test("locking an employee requires a reason and preserves DELETE body", async ({ page }) => {
  const state = await installApi(page, { role: "quan_tri_vien" });
  await page.goto("/admin/tai-khoan/3");
  await page.getByRole("button", { name: "Khóa tài khoản…" }).click();
  await expect(
    page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }),
  ).toBeDisabled();
  await page.getByRole("dialog").getByLabel("Lý do", { exact: true }).fill("Tạm ngừng công việc");
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page.getByRole("button", { name: "Mở khóa tài khoản…" })).toBeVisible();
  expect(state.calls.find((call) => call.method === "DELETE").body).toEqual({
    ly_do: "Tạm ngừng công việc",
  });
});

test("deactivating an item keeps its nonzero stock and historical record", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho/mat-hang/1");
  await page.getByRole("button", { name: "Ngừng sử dụng…" }).click();
  await expect(page.getByRole("dialog")).toContainText("Giữ nguyên mặt hàng, số dư tồn");
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page.getByRole("button", { name: "Ngừng sử dụng…" })).toBeDisabled();
  expect(state.resources.mat_hang[0].so_luong_ton).toBe(120);
  expect(
    state.calls.find((call) => call.path === "mat_hang/1" && call.method === "DELETE").headers[
      "if-match"
    ],
  ).toBe('"v1"');
});

test("BOM creation explicitly confirms activation and sends no state or version fields", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/bom/moi");
  await page.getByLabel("Sản phẩm đầu ra", { exact: true }).selectOption("4");
  await page.getByLabel("Mặt hàng dòng 1", { exact: true }).selectOption("3");
  await page.getByLabel("Số lượng dòng 1", { exact: true }).fill("2");
  await page.getByRole("button", { name: "Tạo và kích hoạt phiên bản", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("ngừng phiên bản hiện hành");
  expect(state.calls.filter((call) => call.path === "bom" && call.method === "POST")).toHaveLength(
    0,
  );
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/bom\/2$/);
  expect(state.calls.find((call) => call.path === "bom" && call.method === "POST").body).toEqual({
    mat_hang_id: 4,
    chi_tiet: [{ mat_hang_id: 3, so_luong: 2 }],
  });
});

test("assigned employee starts an order only after checking issued materials", async ({ page }) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/lenh-sx/1");
  await page.getByRole("button", { name: "Bắt đầu sản xuất", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Tạo chứng từ hoàn thành SX", exact: true }),
  ).toBeVisible();
  const action = state.calls.find((call) => call.path === "lenh_san_xuat/1/bat_dau");
  expect(action.body).toEqual({});
  expect(action.headers["if-match"]).toBe('"v1"');
});

test("completion draft submits Vietnam time with offset even when browser timezone is UTC", async ({
  page,
}) => {
  const state = await installApi(page, { role: "nhan_vien" });
  await page.goto("/nv/hoan-thanh/moi");
  await page.getByLabel("Lệnh sản xuất", { exact: true }).selectOption("2");
  await page.getByLabel("Số lượng hoàn thành đợt này", { exact: true }).fill("2");
  await page
    .getByLabel("Thời điểm hoàn thành (giờ Việt Nam)", { exact: true })
    .fill("2026-11-05T09:30");
  await page.getByRole("button", { name: "Lưu nháp", exact: true }).click();
  await expect(page).toHaveURL(/\/nv\/hoan-thanh\/3$/);
  expect(
    state.calls.find((call) => call.path === "chung_tu_hoan_thanh_sx" && call.method === "POST")
      .body,
  ).toEqual({
    lenh_san_xuat_id: 2,
    so_luong_hoan_thanh: 2,
    finish_time: "2026-11-05T09:30:00+07:00",
  });
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
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await page.getByRole("button", { name: "Giải quyết", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Kết quả xử lý", { exact: true })
    .fill("Đã đối chiếu phiếu nhập, chờ lập điều chỉnh mới");
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
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
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận", exact: true }).click();
  await page.getByRole("dialog").getByRole("link", { name: "#1", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/ticket\/1$/);
  await expect(page.getByRole("dialog")).toHaveCount(0);
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
