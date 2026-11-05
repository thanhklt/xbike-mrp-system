import { test, expect } from "@playwright/test";
import { installApi } from "./api-fixture.js";

test.beforeEach(async ({ page }) => {
  await page.clock.install();
  await installApi(page, { authenticated: false });
  await page.goto("/dang-nhap");
  await expect(page.getByRole("heading", { name: "Đăng nhập", exact: true })).toBeVisible();
});

const thumbs = (page) => page.locator(".login-thumbs button");
const dots = (page) => page.locator(".login-dots button");

test("login shows the designed form, branding and support", async ({ page }) => {
  await expect(page.getByText("Sử dụng tài khoản được quản trị viên cấp.")).toBeVisible();
  await expect(page.getByLabel("Tên đăng nhập", { exact: true })).toHaveAttribute("required", "");
  await expect(page.getByLabel("Mật khẩu", { exact: true })).toHaveAttribute("required", "");
  await expect(page.getByRole("button", { name: "Đăng nhập", exact: true })).toBeVisible();
  await expect(page.getByText("Hỗ trợ Admin")).toBeVisible();
  await expect(page.getByRole("link", { name: "0900 000 000" })).toHaveAttribute(
    "href",
    "tel:0900000000",
  );
  await expect(
    page.getByRole("heading", { name: "Kiểm soát kho. Điều phối sản xuất." }),
  ).toBeVisible();
  await expect(page.getByRole("img", { name: "XBIKE MRP System", exact: true })).toHaveCount(1);
  await expect(thumbs(page)).toHaveCount(3);
  await expect(dots(page)).toHaveCount(3);
  await expect(page.getByRole("banner")).toHaveCount(0);
  await expect(page.getByRole("contentinfo")).toContainText("XBIKE · Hệ thống nội bộ");
});

for (const [width, height] of [
  [1920, 872],
  [1366, 768],
  [1280, 720],
  [900, 1000],
  [390, 844],
  [375, 667],
]) {
  test(`login fits the viewport at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    const layout = await page.evaluate(() => {
      const form = document.querySelector(".login-form");
      const logo = document.querySelector(".login-logo").getBoundingClientRect();
      const tagline = document.querySelector(".login-tagline").getBoundingClientRect();
      const card = document.querySelector(".login-card").getBoundingClientRect();
      const footer = document.querySelector(".login-footer").getBoundingClientRect();
      return {
        width: document.documentElement.scrollWidth,
        height: document.documentElement.scrollHeight,
        formHeight: form.clientHeight,
        formScrollHeight: form.scrollHeight,
        logoBottom: logo.bottom,
        taglineTop: tagline.top,
        centerX: card.left + card.width / 2,
        centerY: card.top + card.height / 2,
        cardBottom: card.bottom,
        footerTop: footer.top,
      };
    });
    expect(layout.width).toBeLessThanOrEqual(width);
    expect(layout.height).toBeLessThanOrEqual(height);
    expect(Math.abs(layout.centerX - width / 2)).toBeLessThanOrEqual(1);
    expect(Math.abs(layout.centerY - height / 2)).toBeLessThanOrEqual(1);
    expect(layout.cardBottom).toBeLessThanOrEqual(layout.footerTop);
    expect(layout.formScrollHeight).toBeLessThanOrEqual(layout.formHeight + 1);
    expect(layout.logoBottom).toBeLessThanOrEqual(layout.taglineTop);
    await expect(page.getByRole("button", { name: "Đăng nhập", exact: true })).toBeInViewport();
    await expect(page.getByRole("link", { name: "0900 000 000" })).toBeInViewport();
  });
}

test("carousel advances every five seconds and wraps to the first image", async ({ page }) => {
  await expect(thumbs(page).nth(0)).toHaveAttribute("aria-current", "true");
  for (const index of [1, 2, 0]) {
    await page.clock.runFor(5000);
    await expect(thumbs(page).nth(index)).toHaveAttribute("aria-current", "true");
    await expect(dots(page).nth(index)).toHaveAttribute("aria-current", "true");
  }
});

test("thumbnails and dots select images, including backwards jumps", async ({ page }) => {
  await thumbs(page).nth(2).click();
  await expect(thumbs(page).nth(2)).toHaveAttribute("aria-current", "true");
  await dots(page).nth(0).click();
  await expect(thumbs(page).nth(0)).toHaveAttribute("aria-current", "true");
  await expect(page.locator(".login-visual-slides img:not([aria-hidden='true'])")).toHaveCount(1);
});

test("selecting the image that just left brings it in from the right", async ({ page }) => {
  await thumbs(page).nth(2).click();
  await page.locator(".login-visual-slides .is-active").evaluate((image) => {
    image.getAnimations().forEach((animation) => animation.finish());
  });
  await dots(page).nth(0).click();
  const position = await page.locator(".login-visual-slides .is-active").evaluate((image) => {
    image.getAnimations().forEach((animation) => {
      animation.pause();
      animation.currentTime = 350;
    });
    return {
      x: new DOMMatrixReadOnly(getComputedStyle(image).transform).m41,
      width: image.clientWidth,
    };
  });
  expect(position.x).toBeGreaterThan(0);
  expect(position.x).toBeLessThan(position.width);
});

test("hover pauses autoplay and leaving restarts its countdown", async ({ page }) => {
  await page.locator(".login-visual").hover();
  await page.clock.runFor(10000);
  await expect(dots(page).nth(0)).toHaveAttribute("aria-current", "true");
  await page.getByRole("heading", { name: "Đăng nhập", exact: true }).hover();
  await page.clock.runFor(5000);
  await expect(dots(page).nth(1)).toHaveAttribute("aria-current", "true");
});

test("keyboard focus pauses autoplay until focus leaves the panel", async ({ page }) => {
  await dots(page).nth(0).focus();
  await page.clock.runFor(10000);
  await dots(page).nth(1).focus();
  await page.clock.runFor(10000);
  await expect(dots(page).nth(0)).toHaveAttribute("aria-current", "true");
  await page.getByLabel("Tên đăng nhập", { exact: true }).focus();
  await page.clock.runFor(5000);
  await expect(dots(page).nth(1)).toHaveAttribute("aria-current", "true");
});

test("leaving with the pointer keeps autoplay paused while focus remains inside", async ({
  page,
}) => {
  await thumbs(page).nth(2).click();
  await page.getByRole("heading", { name: "Đăng nhập", exact: true }).hover();
  await page.clock.runFor(10000);
  await expect(dots(page).nth(2)).toHaveAttribute("aria-current", "true");
  await page.getByLabel("Tên đăng nhập", { exact: true }).focus();
  await page.clock.runFor(5000);
  await expect(dots(page).nth(0)).toHaveAttribute("aria-current", "true");
});

test("reduced motion stops autoplay but allows manual selection", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.clock.runFor(10000);
  await expect(dots(page).nth(0)).toHaveAttribute("aria-current", "true");
  await dots(page).nth(2).click();
  await expect(dots(page).nth(2)).toHaveAttribute("aria-current", "true");
  await expect(page.locator(".login-visual-slides .is-active")).toHaveCSS(
    "transition-duration",
    "0s",
  );
});

test("a hidden document pauses autoplay and visibility restarts it", async ({ page }) => {
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.clock.runFor(10000);
  await expect(dots(page).nth(0)).toHaveAttribute("aria-current", "true");
  await page.evaluate(() => {
    delete document.hidden;
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.clock.runFor(5000);
  await expect(dots(page).nth(1)).toHaveAttribute("aria-current", "true");
});

test("password visibility toggle keeps accessible names", async ({ page }) => {
  const password = page.getByLabel("Mật khẩu", { exact: true });
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Hiện mật khẩu" }).click();
  await expect(password).toHaveAttribute("type", "text");
  await expect(page.getByRole("button", { name: "Ẩn mật khẩu" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("button", { name: "Ẩn mật khẩu" }).click();
  await expect(password).toHaveAttribute("type", "password");
});
