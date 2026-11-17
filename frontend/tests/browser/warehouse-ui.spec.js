import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

const writes = (state) => state.calls.filter((call) => call.method !== "GET");
const recordDialog = (page) => page.locator("dialog.record-dialog");
const confirmation = (page) => page.locator("dialog.confirmation");

test("QLK prototype theme covers all existing pages at desktop, tablet and phone without overflow", async ({
  page,
}) => {
  test.setTimeout(120000);
  const state = await installApi(page);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const section of [
      "",
      "mat-hang",
      "nha-cung-cap",
      "bom",
      "phieu-nhap",
      "yeu-cau",
      "nhu-cau-bo-sung",
      "chung-tu-hoan-thanh",
      "phieu-xuat",
      "giao-dich",
      "thong-ke",
      "lich-su",
    ]) {
      await page.goto(`/kho${section ? `/${section}` : ""}`);
      await expect(page.locator("html")).toHaveAttribute("data-warehouse-theme", "true");
      await expect(page.locator("main h1")).toBeVisible();
      await expect(page.locator(".page-heading p")).toBeHidden();
      await expect(page.locator('#main-navigation a[href="/kho/ticket"]')).toHaveCount(0);
      await page.waitForLoadState("networkidle");
      await expect(page.locator(".notice-error")).toHaveCount(0);
      await expect(page.locator(".warehouse-shell")).toHaveCSS(
        "background-color",
        "rgb(20, 17, 15)",
      );
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await expect(page.locator(".topbar")).not.toContainText(/PROTOTYPE|BACKEND V4|Ngoại tuyến/);
      const account = await page.locator(".user-menu").boundingBox();
      expect(account.x + account.width).toBeGreaterThan(width - 60);
      await page.screenshot({
        path: `test-results/warehouse-${section || "overview"}-${width}.png`,
        fullPage: true,
      });
    }
  }
  expect(writes(state)).toEqual([]);
  expect(errors).toEqual([]);
});

for (const role of ["quan_tri_vien", "nhan_vien"]) {
  test(`QLK styles do not leak into ${role} after the server changes the role`, async ({
    page,
  }) => {
    const state = await installApi(page);
    await page.goto("/kho");
    await expect(page.locator("html")).toHaveAttribute("data-warehouse-theme", "true");
    state.role = role;
    await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
    await expect(page).toHaveURL(/\/403$/);
    await expect(page.locator("html")).not.toHaveAttribute("data-warehouse-theme");
    await page.getByRole("link", { name: "Về trang chủ" }).click();
    await expect(page).toHaveURL(role === "quan_tri_vien" ? /\/admin$/ : /\/nv$/);
    await expect(page.locator(".warehouse-shell")).toHaveCount(0);
    if (role === "quan_tri_vien")
      await expect(page.locator("html")).toHaveAttribute("data-admin-theme", "true");
    else await expect(page.locator("html")).not.toHaveAttribute("data-admin-theme");
  });
}

test("UC-10/11: QLK creates and edits a component with generated code and v4 payload", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/mat-hang/moi");
  const dialog = recordDialog(page);
  await expect(dialog.getByLabel("Mã mặt hàng", { exact: true })).toHaveCount(0);
  await dialog.getByLabel("SKU", { exact: true }).fill("WHS-01");
  await dialog.getByLabel("Tên mặt hàng", { exact: true }).fill("Linh kiện thử giao diện");
  const units = dialog.getByRole("combobox", { name: "Đơn vị tính", exact: true });
  await expect(units.locator("option")).toHaveText(["cái", "chiếc", "bộ", "kg"]);
  await units.selectOption({ label: "bộ" });
  await dialog.getByLabel("Đơn giá (VND)", { exact: true }).fill("10000");
  await dialog.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/mat-hang\/5$/);
  const created = writes(state)[0];
  expect(created.path).toBe("mat_hang");
  expect(created.headers["if-match"]).toBeUndefined();
  expect(created.body).toEqual({
    sku: "WHS-01",
    ten_mat_hang: "Linh kiện thử giao diện",
    loai_mat_hang: "linh_kien",
    don_vi_tinh: "bo",
    don_gia: 10000,
    mau_sac: null,
    mo_ta: null,
  });
  expect(state.resources.mat_hang.find((item) => item.id === 5).ma_mat_hang).toBe("MH-000005");
  await expect(dialog.getByLabel("Mã mặt hàng", { exact: true })).toHaveCount(0);
  await expect(
    dialog.getByRole("button", { name: /Ngừng sử dụng|Dùng lại thành phẩm/ }),
  ).toHaveCount(0);
  await dialog.getByLabel("Tên mặt hàng", { exact: true }).fill("Linh kiện đã sửa");
  await units.selectOption({ label: "chiếc" });
  await dialog.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect.poll(() => writes(state).length).toBe(2);
  const changed = writes(state)[1];
  expect(changed.method).toBe("PATCH");
  expect(changed.headers["if-match"]).toBe('"v1"');
  expect(changed.body.ten_mat_hang).toBe("Linh kiện đã sửa");
  expect(changed.body.don_vi_tinh).toBe("chiec");
  for (const key of ["ma_mat_hang", "loai_mat_hang", "bom", "so_luong_ton", "is_active"])
    expect(changed.body).not.toHaveProperty(key);
});

test("UC-16: the BOM entry creates a finished item and initial formula atomically through MatHang", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/bom");
  await expect(page.getByRole("button", { name: "Xóa lọc", exact: true })).toHaveCount(0);
  await page
    .getByRole("link", { name: "Tạo thành phẩm", exact: true })
    .click();
  const dialog = recordDialog(page);
  await expect(dialog.getByLabel("Loại mặt hàng", { exact: true })).toHaveValue("thanh_pham");
  await dialog.getByLabel("SKU", { exact: true }).fill("BIKE-WHS");
  await dialog.getByLabel("Tên mặt hàng", { exact: true }).fill("Xe thử giao diện");
  await dialog
    .getByRole("combobox", { name: "Đơn vị tính", exact: true })
    .selectOption({ label: "chiếc" });
  await dialog.getByLabel("Đơn giá (VND)", { exact: true }).fill("0");
  await dialog.getByLabel("Mặt hàng dòng 1", { exact: true }).selectOption("1");
  await dialog.getByLabel("Số lượng dòng 1", { exact: true }).fill("2");
  await dialog.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/mat-hang\/5$/);
  const calls = writes(state);
  expect(calls).toHaveLength(1);
  expect(calls[0].path).toBe("mat_hang");
  expect(calls[0].body.don_vi_tinh).toBe("chiec");
  expect(calls[0].body.bom).toEqual({ chi_tiet: [{ mat_hang_id: 1, so_luong: 2 }] });
  expect(state.resources.bom.find((entry) => entry.mat_hang_id === 5)?.version).toBe(1);
});

test("UC-11: failed saves preserve the entered item values and never retry the write", async ({
  page,
}) => {
  const state = await installApi(page, {
    intercept: (call) =>
      call.method === "PATCH" && call.path === "mat_hang/4"
        ? {
            status: 409,
            json: {
              error: { code: "trang_thai_khong_hop_le", message: "SKU đã được tham chiếu" },
              meta: {},
            },
          }
        : null,
  });
  await page.goto("/kho/mat-hang/4");
  const dialog = recordDialog(page);
  await dialog.getByLabel("SKU", { exact: true }).fill("CHANGED-SKU");
  await dialog.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("SKU đã được tham chiếu");
  await expect(dialog.getByLabel("SKU", { exact: true })).toHaveValue("CHANGED-SKU");
  expect(writes(state)).toHaveLength(1);
});

test("UC-11/12: editing a legacy unit preserves it and stopping explains that stock is retained", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/mat-hang/4");
  const dialog = recordDialog(page);
  const units = dialog.getByRole("combobox", { name: "Đơn vị tính", exact: true });
  await expect(units).toHaveValue("chiếc");
  await expect(units.locator("option:checked")).toHaveText("chiếc");
  await dialog.getByRole("button", { name: "Ngừng sử dụng…", exact: true }).click();
  await expect(confirmation(page)).toContainText(
    "Mặt hàng, số dư tồn và chứng từ cũ vẫn sẽ được giữ nguyên số lượng nhưng không thể sử dụng mặt hàng.",
  );
  await confirmation(page).getByRole("button", { name: "Hủy", exact: true }).click();
  expect(writes(state)).toEqual([]);
  await dialog.getByLabel("Tên mặt hàng", { exact: true }).fill("Xe cập nhật tên");
  await dialog.getByRole("button", { name: "Lưu", exact: true }).click();
  await expect.poll(() => writes(state).length).toBe(1);
  expect(writes(state)[0].body).toEqual({ ten_mat_hang: "Xe cập nhật tên" });
  expect(state.resources.mat_hang.find((item) => item.id === 4).don_vi_tinh).toBe("chiếc");
});

for (const [role, path] of [
  ["quan_ly", "/kho/mat-hang"],
  ["nhan_vien", "/nv/ton-kho"],
]) {
  test(`UC-09/12: ${role} sees no component status and invalid status filters make no request`, async ({
    page,
  }) => {
    const state = await installApi(page, { role });
    await page.goto(path);
    const component = page
      .locator("tbody tr")
      .filter({ has: page.getByRole("link", { name: "MH-000001", exact: true }) });
    await expect(component).toBeVisible();
    await expect(component.locator(".badge")).toHaveCount(0);
    await expect(component).not.toContainText(/Đang dùng|Ngừng dùng/);
    const finished = page
      .locator("tbody tr")
      .filter({ has: page.getByRole("link", { name: "MH-000004", exact: true }) });
    await expect(finished.locator(".badge")).toHaveText("Đang dùng");
    await page.getByLabel("Loại mặt hàng", { exact: true }).selectOption("linh_kien");
    const requestCount = state.calls.filter((call) => call.path === "mat_hang").length;
    for (const status of ["true", "false"]) {
      await page.getByLabel("Trạng thái", { exact: true }).selectOption(status);
      await page.getByRole("button", { name: "Lọc", exact: true }).click();
      await expect(page.getByRole("alert")).toHaveText("Linh kiện không có trạng thái");
      expect(state.calls.filter((call) => call.path === "mat_hang")).toHaveLength(requestCount);
    }
    await page.getByLabel("Loại mặt hàng", { exact: true }).selectOption("thanh_pham");
    await page.getByRole("button", { name: "Lọc", exact: true }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect
      .poll(() =>
        state.calls.some(
          (call) =>
            call.path === "mat_hang" &&
            call.params.loai_mat_hang === "thanh_pham" &&
            call.params.is_active === "false",
        ),
      )
      .toBe(true);
    expect(writes(state)).toEqual([]);
  });
}

test("UC-17: a stale BOM keeps its edited formula and uses only the reviewed ETag", async ({
  page,
}) => {
  const state = await installApi(page, {
    intercept: (call) =>
      call.path === "bom/1/phien_ban"
        ? { status: 412, json: { error: { message: "BOM đã được thay đổi" }, meta: {} } }
        : null,
  });
  await page.goto("/kho/bom/1");
  await recordDialog(page).getByRole("button", { name: "Tạo phiên bản mới", exact: true }).click();
  await page.getByLabel("Số lượng dòng 1", { exact: true }).fill("3");
  await page.getByRole("button", { name: "Tạo và kích hoạt phiên bản", exact: true }).click();
  await expect(confirmation(page).locator(".dialog-footer")).toHaveCSS(
    "background-color",
    "rgb(42, 33, 27)",
  );
  await expect(
    confirmation(page).getByRole("columnheader", { name: "Số lượng", exact: true }),
  ).toBeInViewport();
  await page.screenshot({ path: "test-results/warehouse-bom-confirmation.png", fullPage: true });
  const detailReads = state.calls.filter(
    (call) => call.method === "GET" && call.path === "bom/1",
  ).length;
  await confirmation(page).getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(confirmation(page).getByRole("alert")).toContainText("BOM đã được thay đổi");
  await page.screenshot({ path: "test-results/warehouse-bom-stale.png", fullPage: true });
  expect(writes(state)[0].headers["if-match"]).toBe('"v1"');
  expect(state.calls.filter((call) => call.method === "GET" && call.path === "bom/1")).toHaveLength(
    detailReads,
  );
  await confirmation(page).getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(page.getByLabel("Số lượng dòng 1", { exact: true })).toHaveValue("3");
});

for (const action of ["duyet", "tu_choi"]) {
  test(`UC-34–40: QLK only reviews issues; ${action} sends an immutable snapshot and validator`, async ({
    page,
  }) => {
    const state = await installApi(page);
    state.resources.phieu_xuat[0].nhan_vien_id = 3;
    await page.goto("/kho/phieu-xuat/moi");
    await expect(page).toHaveURL(/\/kho\/phieu-xuat$/);
    await expect(page.getByRole("link", { name: "Tạo phiếu xuất", exact: true })).toHaveCount(0);
    await page.goto("/kho/phieu-xuat/1");
    const dialog = recordDialog(page);
    await expect(
      dialog.locator(".info-grid > div").filter({ has: page.locator("dt", { hasText: /^Người lập$/ }) }),
    ).toContainText("Đặng Quốc Bình");
    await expect(dialog.getByText(/Chi tiết lấy từ yêu cầu đã chốt/)).toHaveCount(0);
    await expect(
      dialog
        .locator(".info-grid > div")
        .filter({ has: page.locator("dt", { hasText: /^Nguồn$/ }) }),
    ).toContainText("YCSX-202611-000002");
    await expect(
      dialog.getByRole("button", { name: /Lưu nháp|Xóa nháp|Gửi duyệt|Chuyển về/ }),
    ).toHaveCount(0);
    await expect(dialog.locator("input,select,textarea")).toHaveCount(0);
    await dialog
      .getByRole("button", {
        name: action === "duyet" ? "Duyệt phiếu xuất" : "Từ chối…",
        exact: true,
      })
      .click();
    if (action === "tu_choi") {
      await expect(
        confirmation(page).getByRole("button", { name: "Xác nhận", exact: true }),
      ).toBeDisabled();
      await confirmation(page)
        .getByLabel("Lý do", { exact: true })
        .fill("Cần kiểm tra lại yêu cầu");
    }
    await confirmation(page).getByRole("button", { name: "Hủy", exact: true }).click();
    expect(writes(state)).toEqual([]);
    await dialog
      .getByRole("button", {
        name: action === "duyet" ? "Duyệt phiếu xuất" : "Từ chối…",
        exact: true,
      })
      .click();
    if (action === "tu_choi")
      await confirmation(page)
        .getByLabel("Lý do", { exact: true })
        .fill("Cần kiểm tra lại yêu cầu");
    await confirmation(page).getByRole("button", { name: "Xác nhận", exact: true }).click();
    await expect(confirmation(page)).toHaveCount(0);
    expect(writes(state)).toHaveLength(1);
    expect(writes(state)[0]).toMatchObject({
      path: `phieu_xuat/1/${action}`,
      method: "POST",
      body: action === "duyet" ? {} : { ly_do: "Cần kiểm tra lại yêu cầu" },
    });
    expect(writes(state)[0].headers["if-match"]).toBe('"v1"');
  });
}

test("QLK request detail links to the issue list and never offers issue creation", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/yeu-cau/2");
  await expect(page.getByRole("link", { name: /Tạo phiếu xuất/ })).toHaveCount(0);
  await recordDialog(page).getByRole("link", { name: "Xem phiếu xuất kho →", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/phieu-xuat$/);
  expect(writes(state)).toEqual([]);
});

test("UC-18/19: stopping and reusing a BOM preserve stock and send the current reviewed validator", async ({
  page,
}) => {
  const state = await installApi(page);
  const stock = state.resources.mat_hang.map((item) => item.so_luong_ton);
  await page.goto("/kho/bom/1");
  await recordDialog(page)
    .getByRole("button", { name: "Ngừng dùng phiên bản", exact: true })
    .click();
  const stopping = page.waitForRequest(
    (request) => request.method() === "DELETE" && request.url().endsWith("/bom/1"),
  );
  await confirmation(page).getByRole("button", { name: "Xác nhận", exact: true }).click();
  expect((await stopping).postData()).toBeNull();
  await expect(
    recordDialog(page).getByRole("button", { name: "Dùng lại phiên bản", exact: true }),
  ).toBeVisible();
  await recordDialog(page).getByRole("button", { name: "Dùng lại phiên bản", exact: true }).click();
  await confirmation(page).getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(
    recordDialog(page).getByRole("button", { name: "Ngừng dùng phiên bản", exact: true }),
  ).toBeVisible();
  expect(writes(state).map((call) => [call.method, call.path, call.headers["if-match"]])).toEqual([
    ["DELETE", "bom/1", '"v1"'],
    ["POST", "bom/1/kich_hoat", '"v2"'],
  ]);
  expect(writes(state)[1].body).toEqual({});
  expect(state.resources.mat_hang.map((item) => item.so_luong_ton)).toEqual(stock);
});

test("UC-14: creating a supplier omits the generated code and supplies all required v4 fields", async ({
  page,
}) => {
  const state = await installApi(page);
  await page.goto("/kho/nha-cung-cap/moi");
  const dialog = recordDialog(page);
  await expect(dialog.getByLabel("Mã NCC", { exact: true })).toHaveCount(0);
  for (const [label, value] of [
    ["Tên nhà cung cấp", "Nhà cung cấp thử"],
    ["Số điện thoại", "0901234567"],
    ["Địa chỉ", "12 Đường thử"],
    ["Phường / xã", "Phường 1"],
    ["Tỉnh / thành", "Hà Nội"],
  ])
    await dialog.getByLabel(label, { exact: true }).fill(value);
  await dialog.getByRole("button", { name: "Tạo nhà cung cấp", exact: true }).click();
  await expect(page).toHaveURL(/\/kho\/nha-cung-cap\/2$/);
  expect(writes(state)[0].body).toEqual({
    ten_ncc: "Nhà cung cấp thử",
    so_dien_thoai: "0901234567",
    dia_chi: "12 Đường thử",
    phuong: "Phường 1",
    tinh: "Hà Nội",
  });
  expect(writes(state)[0].headers["if-match"]).toBeUndefined();
});

test("QLK filters and page sizes query the server; report labels keep exact server figures", async ({
  page,
}) => {
  const state = await installApi(page, {
    intercept: (call) =>
      call.path === "bao_cao/nhap_xuat_ton"
        ? {
            json: {
              data: {
                ky: "thang",
                nam: 2026,
                thang: 11,
                mat_hang: [
                  {
                    mat_hang_id: 4,
                    ma_mat_hang: "MH-000004",
                    ten_mat_hang: "Xe đạp City",
                    loai_mat_hang: "thanh_pham",
                    don_vi_tinh: "chiec",
                    ton_dau_ky: 7,
                    nhap_trong_ky: 10,
                    xuat_trong_ky: 3,
                    ton_cuoi_ky: 14,
                  },
                ],
              },
              meta: {},
            },
          }
        : null,
  });
  await page.goto("/kho/mat-hang");
  await expect(page.getByRole("columnheader", { name: "Đang giữ", exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Còn dùng", exact: true })).toBeVisible();
  await page.getByLabel("Loại mặt hàng", { exact: true }).selectOption("linh_kien");
  await page.getByRole("button", { name: "Lọc", exact: true }).click();
  await expect
    .poll(() =>
      state.calls.some(
        (call) => call.path === "mat_hang" && call.params.loai_mat_hang === "linh_kien",
      ),
    )
    .toBe(true);
  await page.getByLabel("Số dòng mỗi trang", { exact: true }).selectOption("50");
  await expect
    .poll(() =>
      state.calls.some(
        (call) =>
          call.path === "mat_hang" && call.params.page_size === "50" && call.params.page === "1",
      ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Xóa lọc", exact: true }).click();
  await expect(page.getByLabel("Loại mặt hàng", { exact: true })).toHaveValue("");
  await page.goto("/kho/thong-ke");
  await page.getByLabel("Năm", { exact: true }).fill("2026");
  await page.getByLabel("Tháng", { exact: true }).fill("11");
  await page.getByRole("button", { name: "Xem báo cáo", exact: true }).click();
  await expect(page.locator("tbody tr").first()).toContainText("chiếc");
  await expect(page.locator("tbody tr").first().locator("td.numeric")).toHaveText([
    "7",
    "10",
    "3",
    "14",
  ]);
  await page.screenshot({ path: "test-results/warehouse-report-filled.png", fullPage: true });
  expect(writes(state)).toEqual([]);
});
