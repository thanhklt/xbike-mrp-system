import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

function addSupplier(state) {
  state.resources.nha_cung_cap.push({
    ...state.resources.nha_cung_cap[0],
    id: 2,
    ma_ncc: "NCC-000002",
    ten_ncc: "Phụ tùng Thành Công",
  });
}

const posts = (state) =>
  state.calls.filter((call) => call.path === "phieu_nhap" && call.method === "POST");

async function setLine(dialog, index, { item, supplier, price }) {
  if (index > 1) await dialog.getByRole("button", { name: "+ Thêm dòng" }).click();
  await dialog.getByLabel(`Mặt hàng dòng ${index}`, { exact: true }).selectOption(item);
  await dialog.getByLabel(`Nhà cung cấp dòng ${index}`, { exact: true }).selectOption(supplier);
  await dialog.getByLabel(`Đơn giá dòng ${index}`, { exact: true }).fill(price);
}

test("receipt creation groups line suppliers and allows the same item on separate drafts", async ({
  page,
}) => {
  const state = await installApi(page);
  addSupplier(state);
  await page.goto("/kho/phieu-nhap/moi");
  const dialog = page.getByRole("dialog", { name: "Tạo phiếu nhập" });
  await dialog.getByLabel("Ngày nhập", { exact: true }).fill("18/11/2026");
  await dialog.getByLabel("Ghi chú", { exact: true }).fill("Bổ sung linh kiện");
  await setLine(dialog, 1, { item: "1", supplier: "1", price: "1000" });
  await setLine(dialog, 2, { item: "2", supplier: "1", price: "2000" });
  await setLine(dialog, 3, { item: "1", supplier: "1", price: "3000" });
  const save = dialog.getByRole("button", { name: "Lưu nháp", exact: true });
  await save.click();
  await expect(dialog.getByRole("alert")).toContainText(
    "chỉ được chọn một lần cho cùng nhà cung cấp",
  );
  expect(posts(state)).toHaveLength(0);

  await dialog.getByLabel("Nhà cung cấp dòng 3", { exact: true }).selectOption("2");
  await expect(dialog.getByText("Sẽ tạo 2 phiếu nháp, mỗi nhà cung cấp một phiếu.")).toBeVisible();
  await save.click();
  await expect(page).toHaveURL(/\/kho\/phieu-nhap$/);
  expect(posts(state).map(({ body }) => body)).toEqual([
    {
      ncc_id: 1,
      ngay_nhap: "2026-11-18",
      ghi_chu: "Bổ sung linh kiện",
      chi_tiet: [
        { mat_hang_id: 1, so_luong: 1, don_gia_thuc: 1000 },
        { mat_hang_id: 2, so_luong: 1, don_gia_thuc: 2000 },
      ],
    },
    {
      ncc_id: 2,
      ngay_nhap: "2026-11-18",
      ghi_chu: "Bổ sung linh kiện",
      chi_tiet: [{ mat_hang_id: 1, so_luong: 1, don_gia_thuc: 3000 }],
    },
  ]);
  await expect(page.getByRole("status")).toContainText("Đã lưu 2 phiếu nhập nháp.");
});

for (const status of [422, 500]) {
  test(`receipt creation keeps successful drafts separate when the next supplier returns ${status}`, async ({
    page,
  }) => {
    let reject = true;
    const state = await installApi(page, {
      intercept: (call) =>
        reject && call.path === "phieu_nhap" && call.method === "POST" && call.body.ncc_id === 2
          ? { status, json: { error: { message: "Lỗi khi lưu phiếu thứ hai" } } }
          : null,
    });
    addSupplier(state);
    await page.goto("/kho/phieu-nhap/moi");
    const dialog = page.getByRole("dialog", { name: "Tạo phiếu nhập" });
    await dialog.getByLabel("Ngày nhập", { exact: true }).fill("18/11/2026");
    await setLine(dialog, 1, { item: "1", supplier: "1", price: "1000" });
    await setLine(dialog, 2, { item: "2", supplier: "2", price: "2000" });
    const save = dialog.getByRole("button", { name: "Lưu nháp", exact: true });
    await save.click();
    await expect(dialog.getByRole("alert")).toContainText("Lỗi khi lưu phiếu thứ hai");
    await expect(dialog.locator('a[href="/kho/phieu-nhap/3"]')).toBeVisible();
    await expect(dialog.getByLabel("Mặt hàng dòng 1", { exact: true })).toHaveValue("2");
    await expect(dialog.getByLabel("Nhà cung cấp dòng 1", { exact: true })).toHaveValue("2");
    await expect(dialog.getByLabel("Mặt hàng dòng 2", { exact: true })).toHaveCount(0);

    if (status === 500) {
      await expect(save).toBeDisabled();
      await expect(dialog.getByRole("link", { name: "danh sách phiếu nhập" })).toBeVisible();
      expect(posts(state).map(({ body }) => body.ncc_id)).toEqual([1, 2]);
    } else {
      reject = false;
      await save.click();
      await expect(page).toHaveURL(/\/kho\/phieu-nhap$/);
      expect(posts(state).map(({ body }) => body.ncc_id)).toEqual([1, 2, 2]);
      expect(
        state.resources.phieu_nhap.filter(({ id, ncc_id }) => id > 2 && ncc_id === 1),
      ).toHaveLength(1);
    }
  });
}
