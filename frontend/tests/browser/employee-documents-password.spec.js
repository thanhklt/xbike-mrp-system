import { expect, test } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test.describe("Employee Documents & Password Workflows", () => {
  test("sidebar navigation shows Phiếu xuất and Chứng từ hoàn thành for employee only", async ({ page }) => {
    // 1. As employee: links are present in sidebar
    await installApi(page, { role: "nhan_vien" });
    await page.goto("/nv");
    const sidebar = page.locator("#main-navigation");
    await expect(sidebar.getByRole("link", { name: "Phiếu xuất" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Chứng từ hoàn thành" })).toBeVisible();

    // Clicking Phiếu xuất opens issues dashboard
    await sidebar.getByRole("link", { name: "Phiếu xuất" }).click();
    await expect(page).toHaveURL(/\/nv\/phieu-xuat/);
    await expect(page.getByRole("heading", { name: "Phiếu xuất", exact: true })).toBeVisible();

    // Clicking Chứng từ hoàn thành opens completion dashboard
    await sidebar.getByRole("link", { name: "Chứng từ hoàn thành" }).click();
    await expect(page).toHaveURL(/\/nv\/chung-tu-hoan-thanh/);
    await expect(page.getByRole("heading", { name: "Chứng từ hoàn thành", exact: true })).toBeVisible();
  });

  test("manager and admin profiles do not show self password change card", async ({ page }) => {
    await installApi(page, { role: "quan_ly" });
    await page.goto("/ho-so");
    await expect(page.getByRole("heading", { name: "Hồ sơ nhân viên" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Đổi mật khẩu" })).toBeHidden();

    await installApi(page, { role: "quan_tri_vien" });
    await page.goto("/ho-so");
    await expect(page.getByRole("heading", { name: "Hồ sơ nhân viên" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Đổi mật khẩu" })).toBeHidden();
  });

  test("request detail has single CTA 'Xem phiếu xuất' navigating to filtered issue dashboard", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    // Setup request assigned to employee (user id 3)
    const req = state.resources.yeu_cau_san_xuat.find((r) => r.id === 1);
    req.nhan_vien_duoc_giao_id = 3;

    // Add two issues for this request (one LK, one TP)
    state.resources.phieu_xuat = [
      {
        id: 101,
        ma_phieu_xuat: "PX-LK-000101",
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        trang_thai: "cho_duyet",
        created_at: "2026-11-15T08:00:00Z",
        updated_at: "2026-11-15T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 1, so_luong: 5 }],
      },
      {
        id: 102,
        ma_phieu_xuat: "PX-TP-000102",
        loai_phieu: "xuat_thanh_pham",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        trang_thai: "da_duyet",
        created_at: "2026-11-16T08:00:00Z",
        updated_at: "2026-11-16T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 4, so_luong: 2 }],
      },
      // Issue for another request
      {
        id: 201,
        ma_phieu_xuat: "PX-LK-000201",
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 2,
        nhan_vien_id: 3,
        trang_thai: "cho_duyet",
        created_at: "2026-11-15T08:00:00Z",
        updated_at: "2026-11-15T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 1, so_luong: 10 }],
      },
    ];

    await page.goto("/nv/yeu-cau/1");
    // Verify there are NO multiple "Mở phiếu" buttons
    await expect(page.getByRole("button", { name: /Mở phiếu/ })).toBeHidden();
    // Exactly ONE CTA "Xem phiếu xuất"
    const cta = page.getByRole("link", { name: "Xem phiếu xuất" });
    await expect(cta).toBeVisible();
    await cta.click();

    // Navigates to /nv/phieu-xuat?yeu_cau_san_xuat_id=1
    await expect(page).toHaveURL(/\/nv\/phieu-xuat\?yeu_cau_san_xuat_id=1/);

    // Filtered list shows only PX-LK-000101, NOT PX-LK-000201
    await expect(page.getByText("PX-LK-000101")).toBeVisible();
    await expect(page.getByText("PX-LK-000201")).toBeHidden();

    // Switch to TP tab
    await page.getByRole("tab", { name: "Xuất thành phẩm" }).click();
    await expect(page).toHaveURL(/tab=xuat_thanh_pham/);
    await expect(page).toHaveURL(/yeu_cau_san_xuat_id=1/);
    await expect(page.getByText("PX-TP-000102")).toBeVisible();

    // Reload (F5) preserves tab and filter
    await page.reload();
    await expect(page.getByRole("tab", { name: "Xuất thành phẩm" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("PX-TP-000102")).toBeVisible();
  });

  test("employee issues dashboard has exactly one view action per row opening exact document ID", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    state.resources.yeu_cau_san_xuat[0].nhan_vien_duoc_giao_id = 3;
    state.resources.phieu_xuat = [
      {
        id: 101,
        ma_phieu_xuat: "PX-LK-000101",
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        trang_thai: "cho_duyet",
        created_at: "2026-11-15T08:00:00Z",
        updated_at: "2026-11-15T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 1, so_luong: 5 }],
      },
    ];

    await page.goto("/nv/phieu-xuat");
    // Code column is plain text (not a link)
    const codeCell = page.getByRole("cell", { name: "PX-LK-000101" });
    await expect(codeCell.getByRole("link")).toBeHidden();

    // Exactly one action button per row
    const viewButton = page.getByRole("link", { name: "Xem chi tiết" });
    await expect(viewButton).toBeVisible();
    await viewButton.click();

    // Opens record panel for ID 101
    await expect(page).toHaveURL(/\/nv\/phieu-xuat\/101/);
    await expect(page.getByRole("heading", { name: "Chi tiết phiếu xuất" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "PX-LK-000101" })).toBeVisible();

    // Closing panel preserves list URL
    await page.getByRole("button", { name: "Đóng", exact: false }).first().click();
    await expect(page).toHaveURL(/\/nv\/phieu-xuat$/);
  });

  test("employee completion dashboard hides search, includes draft, and confirms send with full details", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    const req = state.resources.yeu_cau_san_xuat.find((r) => r.id === 1);
    req.nhan_vien_duoc_giao_id = 3;
    req.trang_thai = "dang_thuc_hien";

    state.resources.chung_tu_hoan_thanh_sx = [
      {
        id: 501,
        ma_phieu: "HTSX-202611-000501",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        so_luong_hoan_thanh: 7,
        finish_time: null,
        trang_thai: "nhap",
        created_at: "2026-11-16T08:00:00Z",
      },
    ];

    await page.goto("/nv/chung-tu-hoan-thanh");

    // Search input is hidden (search={false})
    await expect(page.getByPlaceholder("Tìm mã hoặc tên…")).toBeHidden();

    // Draft completion is visible
    await expect(page.getByText("HTSX-202611-000501")).toBeVisible();

    // Code column is plain text (not a link)
    const codeCell = page.getByRole("cell", { name: "HTSX-202611-000501" });
    await expect(codeCell.getByRole("link")).toBeHidden();

    // Open detail
    await page.getByRole("link", { name: "Xem chi tiết" }).click();
    await expect(page).toHaveURL(/\/nv\/chung-tu-hoan-thanh\/501/);
    await expect(page.getByRole("heading", { name: "Chi tiết chứng từ hoàn thành" })).toBeVisible();

    // Click Gửi button opens confirmation dialog
    const sendButton = page.getByRole("button", { name: "Gửi", exact: true });
    await expect(sendButton).toBeVisible();
    await sendButton.click();

    // Confirmation dialog shows product, quantity, unit
    const dialog = page.getByRole("dialog", { name: "Gửi chứng từ hoàn thành" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Số lượng hoàn thành")).toBeVisible();
    await expect(dialog.getByText("7")).toBeVisible();
    await expect(dialog.getByText("Đơn vị tính")).toBeVisible();
    await expect(dialog.locator(".notice-info")).toHaveCount(0);

    // Confirm send
    await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();

    // Verify completion sent (status changes to cho_duyet)
    await expect.poll(() => state.calls.some((c) => c.path === "chung_tu_hoan_thanh_sx/501/gui" && c.method === "POST")).toBe(true);
  });

  test("self password change on /ho-so validates confirm, handles wrong password, and logs out on success", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    await page.goto("/ho-so");

    await expect(page.getByRole("heading", { name: "Đổi mật khẩu" })).toBeVisible();
    const confirmation = page.locator("dialog.confirmation");

    // 1. Mismatched confirm password -> frontend error, no confirmation, no POST
    await page.getByLabel("Mật khẩu hiện tại", { exact: true }).fill("123456");
    await page.getByLabel("Mật khẩu mới", { exact: true }).fill("newsecret123");
    await page.getByLabel("Nhập lại mật khẩu mới", { exact: true }).fill("different123");
    await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();

    await expect(page.getByText("Mật khẩu nhập lại không khớp")).toBeVisible();
    await expect(confirmation).toHaveCount(0);
    expect(state.calls.some((c) => c.path === "nhan_vien/me/doi_mat_khau")).toBe(false);

    // 1b. Valid inputs -> opens confirmation dialog without sending POST
    await page.getByLabel("Nhập lại mật khẩu mới", { exact: true }).fill("newsecret123");
    await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();

    await expect(confirmation).toBeVisible();
    await expect(confirmation.getByRole("heading", { name: "Xác nhận đổi mật khẩu" })).toBeVisible();
    // Never show secrets in rendered confirmation
    await expect(confirmation).not.toContainText("123456");
    await expect(confirmation).not.toContainText("newsecret123");
    expect(state.calls.filter((c) => c.path === "nhan_vien/me/doi_mat_khau")).toHaveLength(0);

    // 1c. Escape cancels confirmation without sending POST and preserves inputs
    await page.keyboard.press("Escape");
    await expect(confirmation).toHaveCount(0);
    expect(state.calls.filter((c) => c.path === "nhan_vien/me/doi_mat_khau")).toHaveLength(0);
    await expect(page.getByLabel("Mật khẩu hiện tại", { exact: true })).toHaveValue("123456");
    await expect(page.getByLabel("Mật khẩu mới", { exact: true })).toHaveValue("newsecret123");

    // 1d. Cancel via Hủy button also sends 0 POST
    await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "Hủy", exact: true }).click();
    await expect(confirmation).toHaveCount(0);
    expect(state.calls.filter((c) => c.path === "nhan_vien/me/doi_mat_khau")).toHaveLength(0);

    // 2. Wrong current password -> confirm send, 400 error, session preserved
    await page.getByLabel("Mật khẩu hiện tại", { exact: true }).fill("wrongpassword");
    await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();

    await expect.poll(() => state.calls.some((c) => c.path === "nhan_vien/me/doi_mat_khau")).toBe(true);
    await expect(confirmation).toHaveCount(0);
    await expect(page.getByText("Mật khẩu hiện tại không chính xác")).toBeVisible();
    // User remains on /ho-so (session preserved)
    await expect(page).toHaveURL(/\/ho-so/);
    await expect(page.getByLabel("Mật khẩu mới", { exact: true })).toHaveValue("newsecret123");

    // 3. Correct current password -> confirm send, success 204, logout to /dang-nhap
    await page.getByLabel("Mật khẩu hiện tại", { exact: true }).fill("123456");
    await page.getByRole("button", { name: "Đổi mật khẩu", exact: true }).click();
    await expect(confirmation).toBeVisible();
    await confirmation.getByRole("button", { name: "Xác nhận", exact: true }).click();

    // Redirected to login page with success notification
    await expect(page).toHaveURL(/\/dang-nhap/);
    await expect(page.getByText("Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")).toBeVisible();
  });

  test("initial query validation for both endpoints rejects unsupported parameters and fixture handles oversized IDs", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });

    // 1. Visit /nv/phieu-xuat
    await page.goto("/nv/phieu-xuat");
    await expect.poll(() => state.calls.find((c) => c.path === "phieu_xuat/cua_toi")).toBeDefined();
    const issueCall = state.calls.find((c) => c.path === "phieu_xuat/cua_toi");
    // Only allowed parameters: page, page_size, loai_phieu
    const issueKeys = Object.keys(issueCall.params);
    expect(issueKeys.sort()).toEqual(["loai_phieu", "page", "page_size"].sort());
    expect(issueCall.params.loai_phieu).toBe("xuat_linh_kien");

    // 2. Visit /nv/chung-tu-hoan-thanh
    await page.goto("/nv/chung-tu-hoan-thanh");
    await expect.poll(() => state.calls.find((c) => c.path === "chung_tu_hoan_thanh_sx/cua_toi")).toBeDefined();
    const completionCall = state.calls.find((c) => c.path === "chung_tu_hoan_thanh_sx/cua_toi");
    // Only allowed parameters: page, page_size
    const compKeys = Object.keys(completionCall.params);
    expect(compKeys.sort()).toEqual(["page", "page_size"].sort());

    // 3. Rejection of forbidden parameters (422)
    const rejectIssueRes = await page.evaluate(async () => {
      const res = await fetch("/api/v1/phieu_xuat/cua_toi?nhan_vien_id=2", {
        headers: { Authorization: "Bearer test" },
      });
      return { status: res.status };
    });
    expect(rejectIssueRes.status).toBe(422);

    const rejectCompRes = await page.evaluate(async () => {
      const res = await fetch("/api/v1/chung_tu_hoan_thanh_sx/cua_toi?sort=id", {
        headers: { Authorization: "Bearer test" },
      });
      return { status: res.status };
    });
    expect(rejectCompRes.status).toBe(422);

    // 4. Oversized ID query handling (returns 200 with empty list)
    const oversizedRes = await page.evaluate(async () => {
      const res = await fetch("/api/v1/chung_tu_hoan_thanh_sx/cua_toi?mat_hang_id=999999999999", {
        headers: { Authorization: "Bearer test" },
      });
      return { status: res.status, body: await res.json() };
    });
    expect(oversizedRes.status).toBe(200);
    expect(oversizedRes.body.data).toEqual([]);
    expect(oversizedRes.body.meta.total).toBe(0);
  });

  test("pagination >= 21 rows, URL-state synchronization on filter change, F5 reload, and browser Back on both pages", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    // Prepare 22 valid assigned sources sharing real finished product item 4 (plus 1 negative sample)
    const sources = [];
    for (let i = 1; i <= 22; i++) {
      const pad = String(i).padStart(3, "0");
      sources.push({
        id: 100 + i,
        ma_yeu_cau_san_xuat: `YCSX-202611-${pad}`,
        nhan_vien_duoc_giao_id: 3,
        mat_hang_id: 4,
        so_luong: 10,
        trang_thai: "dang_thuc_hien",
        loai_yeu_cau: "xuat_giao",
      });
    }
    // Negative sample source for another employee
    sources.push({
      id: 999,
      ma_yeu_cau_san_xuat: "YCSX-202611-999",
      nhan_vien_duoc_giao_id: 99,
      mat_hang_id: 4,
      so_luong: 10,
      trang_thai: "dang_thuc_hien",
      loai_yeu_cau: "xuat_giao",
    });
    state.resources.yeu_cau_san_xuat = sources;

    // Populate 22 LK issues for employee (exactly 1 per source, unique source+type)
    const lkIssues = [];
    for (let i = 1; i <= 22; i++) {
      const pad = String(i).padStart(3, "0");
      lkIssues.push({
        id: 300 + i,
        ma_phieu_xuat: `PX-LK-202611-${pad}`,
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 100 + i,
        nhan_vien_id: 3,
        trang_thai: i <= 5 ? "cho_duyet" : "da_duyet",
        created_at: `2026-11-${String(Math.min(28, 10 + Math.floor(i / 2))).padStart(2, "0")}T08:00:00Z`,
        chi_tiet: [{ mat_hang_id: 1, so_luong: i }],
      });
    }
    // Negative sample issue for another employee's source
    lkIssues.push({
      id: 999,
      ma_phieu_xuat: "PX-LK-202611-999",
      loai_phieu: "xuat_linh_kien",
      yeu_cau_san_xuat_id: 999,
      nhan_vien_id: 99,
      trang_thai: "cho_duyet",
      created_at: "2026-11-25T08:00:00Z",
      chi_tiet: [{ mat_hang_id: 1, so_luong: 5 }],
    });
    // Add 1 TP issue for source 101 (unique per type)
    lkIssues.push({
      id: 400,
      ma_phieu_xuat: "PX-TP-202611-400",
      loai_phieu: "xuat_thanh_pham",
      yeu_cau_san_xuat_id: 101,
      nhan_vien_id: 3,
      trang_thai: "da_duyet",
      created_at: "2026-11-20T09:00:00Z",
      chi_tiet: [{ mat_hang_id: 4, so_luong: 10 }],
    });
    state.resources.phieu_xuat = lkIssues;

    // --- 1. Test /nv/phieu-xuat ---
    await page.goto("/nv/phieu-xuat");
    await expect(page.getByText("Trang 1 / 2")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-022")).toBeVisible();

    // Navigate to Page 2
    const nextBtn = page.getByRole("button", { name: "Trang sau" });
    await expect(nextBtn).toBeEnabled();
    await nextBtn.click();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.getByText("Trang 2 / 2")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-001")).toBeVisible();

    // Change status filter to "Chờ duyệt" -> MUST reset page to 1
    await page.locator("#filter-trang_thai").selectOption("nhap");
    await expect(page).toHaveURL(/trang_thai=nhap/);
    await page.locator("#filter-trang_thai").selectOption("cho_duyet");

    await expect(page).not.toHaveURL(/page=2/);
    await expect(page).toHaveURL(/trang_thai=cho_duyet/);
    await expect(page.getByText("Trang 1 / 1")).toBeVisible();

    // Reload (F5) -> preserves filter and page 1 results
    await page.reload();
    await expect(page).toHaveURL(/trang_thai=cho_duyet/);
    await expect(page.getByText("Trang 1 / 1")).toBeVisible();

    // Back visits the preceding choice, then restores page 2 and "Tất cả".
    await page.goBack();
    await expect(page).toHaveURL(/trang_thai=nhap/);
    await expect(page.locator("#filter-trang_thai")).toHaveValue("nhap");
    await page.goBack();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.getByText("Trang 2 / 2")).toBeVisible();
    await expect(page.locator("#filter-trang_thai")).toHaveValue("");

    // Switch to TP tab, open detail, close detail, F5
    await page.getByRole("tab", { name: "Xuất thành phẩm" }).click();
    await expect(page).toHaveURL(/tab=xuat_thanh_pham/);
    await expect(page.getByText("PX-TP-202611-400")).toBeVisible();

    await page.getByRole("link", { name: "Xem chi tiết" }).click();
    await expect(page).toHaveURL(/\/nv\/phieu-xuat\/400\?tab=xuat_thanh_pham/);
    await page.getByRole("button", { name: "Đóng", exact: false }).first().click();
    await expect(page).toHaveURL(/\/nv\/phieu-xuat\?tab=xuat_thanh_pham$/);
    await page.reload();
    await expect(page.getByRole("tab", { name: "Xuất thành phẩm" })).toHaveAttribute("aria-selected", "true");

    // --- 2. Test /nv/chung-tu-hoan-thanh ---
    // Exactly 1 completion per corresponding source
    const completions = [];
    for (let i = 1; i <= 22; i++) {
      const pad = String(i).padStart(3, "0");
      completions.push({
        id: 700 + i,
        ma_phieu: `HTSX-202611-${pad}`,
        yeu_cau_san_xuat_id: 100 + i,
        nhan_vien_id: 3,
        mat_hang_id: 4,
        so_luong_hoan_thanh: i,
        finish_time: `2026-11-${String(Math.min(28, 10 + Math.floor(i / 2))).padStart(2, "0")}T10:00:00Z`,
        trang_thai: i <= 5 ? "nhap" : "da_duyet",
        created_at: `2026-11-${String(Math.min(28, 10 + Math.floor(i / 2))).padStart(2, "0")}T08:00:00Z`,
      });
    }
    // Negative sample completion
    completions.push({
      id: 999,
      ma_phieu: "HTSX-202611-999",
      yeu_cau_san_xuat_id: 999,
      nhan_vien_id: 99,
      mat_hang_id: 4,
      so_luong_hoan_thanh: 5,
      finish_time: "2026-11-25T10:00:00Z",
      trang_thai: "da_duyet",
      created_at: "2026-11-25T08:00:00Z",
    });
    state.resources.chung_tu_hoan_thanh_sx = completions;

    await page.goto("/nv/chung-tu-hoan-thanh");
    await expect(page.getByText("Trang 1 / 2")).toBeVisible();

    // Navigate to Page 2
    await page.getByRole("button", { name: "Trang sau" }).click();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.getByText("Trang 2 / 2")).toBeVisible();

    // Filter by "Nháp" -> resets page to 1
    await page.locator("#filter-trang_thai").selectOption("nhap");

    await expect(page).not.toHaveURL(/page=2/);
    await expect(page).toHaveURL(/trang_thai=nhap/);
    await expect(page.getByText("Trang 1 / 1")).toBeVisible();

    // Reload (F5) preserves filter
    await page.reload();
    await expect(page).toHaveURL(/trang_thai=nhap/);

    // Browser Back restores page 2
    await page.goBack();
    await expect(page).toHaveURL(/page=2/);
    await expect(page.getByText("Trang 2 / 2")).toBeVisible();
    await expect(page.locator("#filter-trang_thai")).toHaveValue("");
  });

  test("delayed detail navigation from record A to record B does not show stale sibling data during load or on error", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    const req1 = state.resources.yeu_cau_san_xuat.find((r) => r.id === 1);
    req1.nhan_vien_duoc_giao_id = 3;
    req1.ma_yeu_cau_san_xuat = "YCSX-AAA";

    let req2 = state.resources.yeu_cau_san_xuat.find((r) => r.id === 2);
    if (!req2) {
      req2 = { id: 2, ma_yeu_cau_san_xuat: "YCSX-BBB", nhan_vien_duoc_giao_id: 3, mat_hang_id: 1, trang_thai: "dang_thuc_hien" };
      state.resources.yeu_cau_san_xuat.push(req2);
    } else {
      req2.nhan_vien_duoc_giao_id = 3;
      req2.ma_yeu_cau_san_xuat = "YCSX-BBB";
    }

    state.resources.chung_tu_hoan_thanh_sx = [
      {
        id: 501,
        ma_phieu: "HTSX-AAA",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        so_luong_hoan_thanh: 5,
        finish_time: null,
        trang_thai: "nhap",
        created_at: "2026-11-16T08:00:00Z",
      },
      {
        id: 502,
        ma_phieu: "HTSX-BBB",
        yeu_cau_san_xuat_id: 2,
        nhan_vien_id: 3,
        so_luong_hoan_thanh: 10,
        finish_time: null,
        trang_thai: "nhap",
        created_at: "2026-11-17T08:00:00Z",
      },
    ];

    // Intercept source request 2 to simulate delay/error
    await page.route("**/api/v1/yeu_cau_san_xuat/2", async (route) => {
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: { message: "Server error" } }) });
    });

    // Open record A
    await page.goto("/nv/chung-tu-hoan-thanh/501");
    await expect(page.getByRole("heading", { name: "HTSX-AAA" })).toBeVisible();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("YCSX-AAA")).toBeVisible();

    // Navigate to record B where source 2 fails
    await page.goto("/nv/chung-tu-hoan-thanh/502");
    await expect(page.getByRole("heading", { name: "HTSX-BBB" })).toBeVisible();
    // Must NOT display YCSX-AAA (sibling record A's data)
    await expect(dialog.getByText("YCSX-AAA")).toBeHidden();
  });

  test("password change duplicate submission gate prevents duplicate requests and logs out only on 204", async ({ page }) => {
    await installApi(page, { role: "nhan_vien" });
    await page.goto("/ho-so");

    let passwordChangeCalls = 0;
    await page.route("**/api/v1/nhan_vien/me/doi_mat_khau", async (route) => {
      passwordChangeCalls++;
      // Delay response slightly so pending state can be tested
      await new Promise((resolve) => setTimeout(resolve, 300));
      await route.fulfill({ status: 204 });
    });

    await page.getByLabel("Mật khẩu hiện tại", { exact: true }).fill("123456");
    await page.getByLabel("Mật khẩu mới", { exact: true }).fill("validnewsecret123");
    await page.getByLabel("Nhập lại mật khẩu mới", { exact: true }).fill("validnewsecret123");

    const submitBtn = page.getByRole("button", { name: "Đổi mật khẩu" });
    await submitBtn.click();

    const confirmation = page.locator("dialog.confirmation");
    await expect(confirmation).toBeVisible();

    const confirmBtn = confirmation.getByRole("button", { name: "Xác nhận", exact: true });
    await confirmBtn.click();

    // While pending: confirmation button is disabled with loading text
    const busyBtn = confirmation.getByRole("button", { name: "Đang xử lý…" });
    await expect(busyBtn).toBeDisabled();

    // Rapid second click attempt
    await busyBtn.click({ force: true }).catch(() => {});

    // Waits for completion and logout
    await expect(page).toHaveURL(/\/dang-nhap/);
    await expect(page.getByText("Đổi mật khẩu thành công. Vui lòng đăng nhập lại.")).toBeVisible();

    // Verify only 1 POST was dispatched
    expect(passwordChangeCalls).toBe(1);
  });

  test("keyboard tab navigation with Arrow keys and mobile 375px responsive dialog layout", async ({ page }) => {
    await installApi(page, { role: "nhan_vien" });
    await page.setViewportSize({ width: 375, height: 812 });

    await page.goto("/nv/phieu-xuat");
    await expect(page.getByRole("heading", { name: "Phiếu xuất", exact: true })).toBeVisible();

    // Keyboard navigation on tabs
    const lkTab = page.getByRole("tab", { name: "Xuất linh kiện" });
    const tpTab = page.getByRole("tab", { name: "Xuất thành phẩm" });

    await lkTab.focus();
    await page.keyboard.press("ArrowRight");
    await expect(tpTab).toHaveAttribute("aria-selected", "true");
    await expect(page).toHaveURL(/tab=xuat_thanh_pham/);

    await page.keyboard.press("ArrowLeft");
    await expect(lkTab).toHaveAttribute("aria-selected", "true");
    await expect(page).not.toHaveURL(/tab=xuat_thanh_pham/);

    // Verify mobile 375px popup dialog on /nv/phieu-xuat/:id
    await page.goto("/nv/phieu-xuat/1");
    const issueDialog = page.locator("dialog.record-dialog");
    await expect(issueDialog).toBeVisible();
    const issueBox = await issueDialog.boundingBox();
    expect(issueBox).not.toBeNull();
    expect(issueBox.width).toBeLessThanOrEqual(375);
    expect(issueBox.x).toBeGreaterThanOrEqual(0);
    const issueCloseBtn = issueDialog.getByRole("button", { name: "Đóng" });
    await expect(issueCloseBtn).toBeVisible();
    await issueCloseBtn.click();
    await expect(issueDialog).not.toBeVisible();

    // Verify mobile 375px popup dialog on /nv/chung-tu-hoan-thanh/:id
    await page.goto("/nv/chung-tu-hoan-thanh/1");
    const compDialog = page.locator("dialog.record-dialog");
    await expect(compDialog).toBeVisible();
    const compBox = await compDialog.boundingBox();
    expect(compBox).not.toBeNull();
    expect(compBox.width).toBeLessThanOrEqual(375);
    expect(compBox.x).toBeGreaterThanOrEqual(0);
    const compCloseBtn = compDialog.getByRole("button", { name: "Đóng" });
    await expect(compCloseBtn).toBeVisible();
    await compCloseBtn.click();
    await expect(compDialog).not.toBeVisible();
  });

  test("issue search q submits partial query, matches business code, and preserves query/draft/data across F5 and browser Back", async ({ page }) => {
    const state = await installApi(page, { role: "nhan_vien" });
    const req1 = state.resources.yeu_cau_san_xuat.find((r) => r.id === 1);
    req1.nhan_vien_duoc_giao_id = 3;

    state.resources.phieu_xuat = [
      {
        id: 101,
        ma_phieu_xuat: "PX-LK-202611-000101",
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        trang_thai: "da_duyet",
        created_at: "2026-11-20T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 1, so_luong: 5 }],
      },
      {
        id: 202,
        ma_phieu_xuat: "PX-LK-202611-000202",
        loai_phieu: "xuat_linh_kien",
        yeu_cau_san_xuat_id: 1,
        nhan_vien_id: 3,
        trang_thai: "da_duyet",
        created_at: "2026-11-21T08:00:00Z",
        chi_tiet: [{ mat_hang_id: 1, so_luong: 10 }],
      },
    ];

    await page.goto("/nv/phieu-xuat");
    await expect(page.getByText("PX-LK-202611-000101")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-000202")).toBeVisible();

    // Fill partial query
    const searchInput = page.getByPlaceholder("Tìm mã phiếu xuất…");
    await expect(searchInput).toBeVisible();
    await searchInput.fill("000101");

    // Verify URL and API call params
    await expect(page).toHaveURL(/q=000101/);
    await expect.poll(() => state.calls.filter((call) => call.path === "phieu_xuat/cua_toi")
      .at(-1)?.params.q).toBe("000101");

    // Verify results filtered
    await expect(page.getByText("PX-LK-202611-000101")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-000202")).not.toBeVisible();

    // F5 reload preserves query, draft, and results
    await page.reload();
    await expect(page).toHaveURL(/q=000101/);
    await expect(page.getByPlaceholder("Tìm mã phiếu xuất…")).toHaveValue("000101");
    await expect(page.getByText("PX-LK-202611-000101")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-000202")).not.toBeVisible();

    // Browser Back to previous state (empty search)
    await page.goBack();
    await expect(page).not.toHaveURL(/q=000101/);
    await expect(page.getByPlaceholder("Tìm mã phiếu xuất…")).toHaveValue("");
    await expect(page.getByText("PX-LK-202611-000101")).toBeVisible();
    await expect(page.getByText("PX-LK-202611-000202")).toBeVisible();
  });

  test("default Collection without syncDraftWithParams preserves unsubmitted draft on pagination", async ({ page }) => {
    const state = await installApi(page, { role: "quan_ly" });
    // Seed 25 production requests for manager pagination
    const managerRequests = [];
    for (let i = 1; i <= 25; i++) {
      const pad = String(i).padStart(3, "0");
      managerRequests.push({
        id: 500 + i,
        ma_yeu_cau_san_xuat: `YCSX-202611-${pad}`,
        mat_hang_id: 4,
        so_luong: 10,
        nhan_vien_id: 2,
        nhan_vien_duoc_giao_id: 3,
        trang_thai: "dang_thuc_hien",
        loai_yeu_cau: "xuat_giao",
        created_at: `2026-11-${String(Math.min(28, 10 + Math.floor(i / 2))).padStart(2, "0")}T08:00:00Z`,
        updated_at: `2026-11-${String(Math.min(28, 10 + Math.floor(i / 2))).padStart(2, "0")}T08:00:00Z`,
      });
    }
    state.resources.yeu_cau_san_xuat = managerRequests;

    await page.goto("/kho/yeu-cau");
    await expect(page.getByText("Trang 1 / 2")).toBeVisible();

    // Type into search without clicking "Lọc"
    const searchInput = page.getByRole("searchbox", { name: "Tìm kiếm" });
    await searchInput.fill("unsubmitted-draft-text");

    // Click next page
    await page.getByRole("button", { name: "Trang sau" }).click();
    await expect(page.getByText("Trang 2 / 2")).toBeVisible();

    // Default Collection preserved the unsubmitted draft
    await expect(searchInput).toHaveValue("unsubmitted-draft-text");
  });
});
