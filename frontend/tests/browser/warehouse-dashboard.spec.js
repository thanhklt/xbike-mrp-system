import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const completionTitle = "Chứng từ hoàn thành chờ xác nhận";
const shortageTitle = "Yêu cầu chờ bổ sung linh kiện";
const card = (page, title) =>
  page
    .locator("section.card")
    .filter({ has: page.getByRole("heading", { name: title, exact: true }) });
const writes = (state) => state.calls.filter((call) => call.method !== "GET");

function seedPendingQueues(state) {
  const request = state.resources.yeu_cau_san_xuat[1];
  for (let index = 0; index < 6; index++) {
    const missingId = 10 + index;
    const completionRequestId = 20 + index;
    state.resources.yeu_cau_san_xuat.push(
      {
        ...request,
        id: missingId,
        ma_yeu_cau_san_xuat: `YCSX-202611-${String(missingId).padStart(6, "0")}`,
        trang_thai: "cho_bo_sung_linh_kien",
        so_luong_can_san_xuat: 3 + index,
        han_hoan_thanh: "2026-11-30",
      },
      {
        ...request,
        id: completionRequestId,
        ma_yeu_cau_san_xuat: `YCSX-202611-${String(completionRequestId).padStart(6, "0")}`,
      },
    );
    state.resources.chung_tu_hoan_thanh_sx.push({
      id: 100 + index,
      ma_phieu: `HTSX-202611-${String(100 + index).padStart(6, "0")}`,
      yeu_cau_san_xuat_id: completionRequestId,
      ma_yeu_cau_san_xuat: `YCSX-202611-${String(completionRequestId).padStart(6, "0")}`,
      mat_hang_id: 4,
      loai_yeu_cau: request.loai_yeu_cau,
      nhan_vien_id: 3,
      so_luong_hoan_thanh: 2 + index,
      trang_thai: "cho_duyet",
      finish_time: "2026-11-17T08:00:00Z",
    });
  }
  state.resources.chung_tu_hoan_thanh_sx.push({
    ...state.resources.chung_tu_hoan_thanh_sx[0],
    id: 99,
    ma_phieu: "HTSX-202611-000099",
    yeu_cau_san_xuat_id: request.id,
    ma_yeu_cau_san_xuat: request.ma_yeu_cau_san_xuat,
    trang_thai: "da_duyet",
  });
}

test("warehouse overview shows five pending rows per queue and opens existing request pages", async ({
  page,
}) => {
  const state = await installApi(page);
  seedPendingQueues(state);
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/kho");
    const completions = card(page, completionTitle);
    const shortages = card(page, shortageTitle);
    await expect(completions.locator(".compact-row")).toHaveCount(5);
    await expect(shortages.locator(".compact-row")).toHaveCount(5);
    await expect(completions).toContainText("HTSX-202611-000100");
    await expect(completions).toContainText("YCSX-202611-000020");
    await expect(completions).toContainText("Xe đạp City Ride · 2 chiếc");
    await expect(completions).not.toContainText("HTSX-202611-000099");
    await expect(completions).not.toContainText("HTSX-202611-000105");
    await expect(shortages).toContainText("YCSX-202611-000010");
    await expect(shortages).toContainText("Hạn hoàn thành: 30/11/2026");
    await expect(shortages).not.toContainText("YCSX-202611-000001");
    await expect(shortages).not.toContainText("YCSX-202611-000015");
    await expect(
      completions.getByRole("link", { name: "Mở →", exact: true }).first(),
    ).toHaveAttribute("href", "/kho/yeu-cau/20");
    await expect(
      shortages.getByRole("link", { name: "Mở →", exact: true }).first(),
    ).toHaveAttribute("href", "/kho/yeu-cau/10");
    await expect(
      page.getByRole("heading", { name: "Tra cứu tồn kho nhanh", exact: true }),
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Hoạt động gần đây", exact: true })).toHaveCount(
      0,
    );
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({
      path: `test-results/warehouse-pending-queues-${width}.png`,
      fullPage: true,
    });
  }
  expect(
    state.calls.some(
      (call) =>
        call.path === "chung_tu_hoan_thanh_sx" &&
        call.params.trang_thai === "cho_duyet" &&
        call.params.page_size === "5",
    ),
  ).toBe(true);
  expect(
    state.calls.some(
      (call) =>
        call.path === "yeu_cau_san_xuat" &&
        call.params.trang_thai === "cho_bo_sung_linh_kien" &&
        call.params.page_size === "5",
    ),
  ).toBe(true);
  expect(state.calls.some((call) => ["audit", "mat_hang"].includes(call.path))).toBe(false);
  await card(page, completionTitle)
    .getByRole("link", { name: "Mở →", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/kho\/yeu-cau\/20$/);
  await page.goto("/kho");
  await card(page, shortageTitle).getByRole("link", { name: "Mở →", exact: true }).first().click();
  await expect(page).toHaveURL(/\/kho\/yeu-cau\/10$/);
  expect(writes(state)).toEqual([]);
});

test("warehouse queues keep their empty states and links to the full lists", async ({ page }) => {
  const state = await installApi(page);
  await page.goto("/kho");
  await expect(card(page, completionTitle)).toContainText(
    "Không có chứng từ hoàn thành chờ xác nhận.",
  );
  await expect(card(page, shortageTitle)).toContainText("Không có yêu cầu chờ bổ sung linh kiện.");
  await card(page, completionTitle)
    .getByRole("link", { name: "Xem danh sách chứng từ →", exact: true })
    .click();
  await expect(page).toHaveURL(/\/kho\/chung-tu-hoan-thanh$/);
  await page.goto("/kho");
  await card(page, shortageTitle)
    .getByRole("link", { name: "Xem nhu cầu bổ sung →", exact: true })
    .click();
  await expect(page).toHaveURL(/\/kho\/nhu-cau-bo-sung$/);
  expect(writes(state)).toEqual([]);
});

test("a failed completion queue can retry without hiding the shortage queue", async ({ page }) => {
  let failing = true;
  const state = await installApi(page, {
    intercept: (call) =>
      failing && call.path === "chung_tu_hoan_thanh_sx"
        ? {
            status: 500,
            json: { error: { message: "Không tải được chứng từ hoàn thành" }, meta: {} },
          }
        : null,
  });
  seedPendingQueues(state);
  await page.goto("/kho");
  await expect(card(page, completionTitle).getByRole("alert")).toContainText(
    "Không tải được chứng từ hoàn thành",
  );
  await expect(card(page, shortageTitle).locator(".compact-row")).toHaveCount(5);
  failing = false;
  await card(page, completionTitle).getByRole("button", { name: "Tải lại", exact: true }).click();
  await expect(card(page, completionTitle).locator(".compact-row")).toHaveCount(5);
  await expect(card(page, completionTitle).getByRole("alert")).toHaveCount(0);
  expect(writes(state)).toEqual([]);
});
