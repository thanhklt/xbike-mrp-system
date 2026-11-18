import { test, expect } from "@playwright/test";

async function login(page, username) {
  await page.goto("/dang-nhap");
  await page.getByLabel("Tên đăng nhập", { exact: true }).fill(username);
  await page.getByLabel("Mật khẩu", { exact: true }).fill("DemoXbike2026!");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).not.toHaveURL(/dang-nhap/);
}

async function confirm(page) {
  const dialog = page.locator("dialog.confirmation");
  await dialog.getByRole("button", { name: "Xác nhận", exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

function issueRow(page, issueId) {
  return page.getByRole("tabpanel").getByRole("row").filter({
    has: page.locator(`a[href^="/nv/phieu-xuat/${issueId}?"]`),
  });
}

test("real employee and manager complete the seeded production/export demo without API mocks", async ({ browser }) => {
  const employeeContext = await browser.newContext();
  const otherContext = await browser.newContext();
  const managerContext = await browser.newContext();
  try {
    const employee = await employeeContext.newPage();
    const other = await otherContext.newPage();
    const manager = await managerContext.newPage();
    const failures = [];
    employee.on("pageerror", (error) => failures.push(error.message));
    await login(employee, "nhan_vien_sx");
    await login(other, "nhan_vien_lr");
    await login(manager, "quan_ly_kho");
    await employee.goto("/nv/yeu-cau/5");
    await employee.getByRole("link", { name: "Lập phiếu xuất linh kiện", exact: true }).click();
    const detail = employee.locator("dialog.record-dialog");
    await expect(detail.getByRole("table", { name: "Danh sách dòng mặt hàng" })).toBeVisible();
    await detail.getByRole("button", { name: "Lưu nháp", exact: true }).click();
    await expect(employee).toHaveURL(/\/nv\/xuat-nvl\/\d+$/);
    const issueId = employee.url().split("/").pop();
    await employee.goto("/nv/yeu-cau/5");
    await detail.getByRole("link", { name: "Xem phiếu xuất", exact: true }).click();
    await expect(employee).toHaveURL(/\/nv\/phieu-xuat\?yeu_cau_san_xuat_id=5$/);
    await issueRow(employee, issueId).getByRole("link", { name: "Xem chi tiết", exact: true }).click();
    await expect(employee).toHaveURL((url) => url.pathname === `/nv/phieu-xuat/${issueId}`);
    await detail.getByRole("button", { name: "Gửi", exact: true }).click();
    await confirm(employee);
    await expect(detail.getByText("Chờ duyệt", { exact: true })).toBeVisible();
    await other.goto(`/nv/phieu-xuat/${issueId}`);
    const accessError = other.locator("dialog.record-dialog").getByRole("alert");
    await expect(accessError).toBeVisible();
    await expect(accessError).toContainText("Forbidden");
    await expect(other.getByRole("button", { name: /Gửi|Duyệt/ })).toHaveCount(0);
    await manager.goto(`/kho/phieu-xuat/${issueId}`);
    await manager.getByRole("button", { name: "Duyệt phiếu xuất", exact: true }).click();
    await confirm(manager);
    await employee.goto("/nv/yeu-cau/5");
    await employee.getByRole("button", { name: "Bắt đầu sản xuất", exact: true }).click();
    await employee.getByRole("button", { name: "Lập chứng từ hoàn thành", exact: true }).click();
    await employee.getByRole("button", { name: "Lưu", exact: true }).click();
    await employee.getByRole("button", { name: "Gửi", exact: true }).click();
    await confirm(employee);
    await manager.goto("/kho/yeu-cau/5");
    await manager.locator("dialog.record-dialog").getByRole("button", { name: "Duyệt", exact: true }).click();
    await confirm(manager);
    await employee.reload();
    await employee.getByRole("link", { name: "Lập phiếu xuất thành phẩm", exact: true }).click();
    await detail.getByRole("button", { name: "Lưu nháp", exact: true }).click();
    await expect(employee).toHaveURL(/\/nv\/xuat-tp\/\d+$/);
    const productIssueId = employee.url().split("/").pop();
    await detail.getByRole("button", { name: "Gửi", exact: true }).click();
    await confirm(employee);
    await manager.goto(`/kho/phieu-xuat/${productIssueId}`);
    await manager.getByRole("button", { name: "Duyệt phiếu xuất", exact: true }).click();
    await confirm(manager);
    await employee.goto("/nv/yeu-cau/5");
    await expect(detail.getByText("Hoàn thành", { exact: true }).first()).toBeVisible();
    await detail.getByRole("link", { name: "Xem phiếu xuất", exact: true }).click();
    await expect(employee).toHaveURL(/\/nv\/phieu-xuat\?yeu_cau_san_xuat_id=5$/);
    await expect(employee.getByRole("tab", { name: "Xuất linh kiện", selected: true })).toBeVisible();
    await expect(issueRow(employee, issueId).getByText("Đã duyệt", { exact: true })).toBeVisible();
    await employee.getByRole("tab", { name: "Xuất thành phẩm", exact: true }).click();
    await expect(issueRow(employee, productIssueId).getByText("Đã duyệt", { exact: true })).toBeVisible();
    expect(failures).toEqual([]);
    await employee.screenshot({ path: "test-results/employee-live-completed.png", fullPage: true });
  } finally {
    await Promise.allSettled([employeeContext.close(), otherContext.close(), managerContext.close()]);
  }
});
