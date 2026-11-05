# Plan: Thay giao diện trang đăng nhập theo thiết kế mới

> Ngày lập: 05/11/2026 (cập nhật cùng ngày: bổ sung font, logo SVG và số đo) · Phạm vi: chỉ frontend (`frontend/`) · Không đụng backend, API hay luồng auth.
> Lưu ý: repo chưa có `.handoff/config.md` nên plan này viết tay, không qua `/setup-handoff`.
> **Ảnh thiết kế gốc:** [.handoff/assets/login-design.png](assets/login-design.png) (1586×992 px). Mọi số đo trong plan lấy theo ảnh này. Đây là nguồn đối chiếu duy nhất về hình thức.

## Background

Trang `/dang-nhap` hiện tại ([LoginPage.jsx](../frontend/src/features/auth/LoginPage.jsx), CSS ở [App.css:825-905](../frontend/src/app/App.css#L825-L905)) là thẻ 2 cột nền sáng dùng IBM Plex Sans. Thiết kế mới là **giao diện tối**:

**Cột trái (panel ảnh)**
- Ảnh nền phủ toàn panel. **3 ảnh tự trượt vòng tròn**: ảnh mới vào **từ bên phải**, thumbnail và chấm đang chọn đi theo thứ tự 1→2→3→1 từ trái sang phải.
- Logo `XBIKE` (đậm, nghiêng, có nét swoosh) với `MRP SYSTEM` bên dưới, ở góc trên bên trái.
- Tagline 2 dòng màu trắng, rất đậm: `Kiểm soát kho.` / `Điều phối sản xuất.`
- Hàng 3 thumbnail. Thumbnail đang chọn có viền cam.
- 3 chấm chỉ báo. Chấm đang chọn là vạch trắng dài hơn, các chấm còn lại màu xám.

**Cột phải (form)**
- `Đăng nhập` (h1 rất đậm) và phụ đề `Sử dụng tài khoản được quản trị viên cấp.`
- Ô `Tên đăng nhập` (placeholder `Nhập tên đăng nhập`).
- Ô `Mật khẩu` có icon con mắt nằm trong ô.
- Nút cam full-width `Đăng nhập →`.
- Khối hỗ trợ gồm icon điện thoại │ vạch đứng │ `Hỗ trợ Admin` (đậm) / `0900 000 000`.

### Quyết định đã chốt với dev (05/11/2026)

| # | Câu hỏi | Quyết định |
|---|---|---|
| 1 | Hướng trượt | Ảnh mới vào từ phải. Khi quay vòng 3→1 hoặc khi click nhảy ngược, ảnh mới vẫn vào từ phải, không tua lùi. |
| 2 | Header navy và footer © hiện có | **Giữ cả hai**, đổi sang tông tối. |
| 3 | Số hỗ trợ | Hằng số trong code: `0900 000 000`. |
| 4 | Tương tác | Click thumbnail hoặc chấm để nhảy ảnh. Tạm dừng auto-play khi hover hoặc focus vào panel. Không auto-play khi bật `prefers-reduced-motion: reduce`. |
| 5 | Font | **Giao diện phải giống ảnh, kể cả font.** Font mới **tạm thời chỉ áp dụng cho trang đăng nhập**. Các trang khác giữ IBM Plex Sans. |
| 6 | Logo | **File SVG vẽ tay** (có swoosh), không dựng bằng font chữ. |

### Quyết định do plan đưa ra (dev có thể sửa trước khi execute)

- **Font mặc định** (chọn lại theo bước so sánh ở mục 2 nếu ứng viên khác giống ảnh hơn):
  - *Display* (h1 `Đăng nhập`, tagline): **Be Vietnam Pro 800**. Lý do: bo tròn hình học, `a` 2 tầng, `g` 1 tầng, dấu tiếng Việt xếp chồng gọn, giống nét đậm trong ảnh.
  - *Body* (phụ đề, label, input, nút, khối hỗ trợ): **Noto Sans 400/600**. Lý do: nét humanist hơi hẹp và chữ số `0` hình oval, giống phụ đề và số điện thoại trong ảnh.
- **Dấu `*` bắt buộc** (do `Field` tự thêm): ẩn trên form đăng nhập để giống thiết kế, vẫn giữ thuộc tính `required`.
- **Bỏ** các thành phần không có trong thiết kế: đoạn mô tả, `<hr>`, dòng `Dành cho…`, dòng `Gặp sự cố đăng nhập?…`.
- **Header giữ lại** nhưng thay chữ `XBIKE` bằng chính logo SVG (cao 32px) cạnh dòng nhỏ `Hệ thống quản lý kho & sản xuất`, để thương hiệu thống nhất.
- **Token màu và font** khai báo trong phạm vi `.login-page`, không đặt ở `:root`.
- **Không sửa component dùng chung** (`Button`, `Field`, `ErrorNotice`). Mọi khác biệt được override trong phạm vi `.login-page`.
- **Thumbnail dùng lại ảnh slide** (`object-fit: cover`), không sinh thêm file.

## Tổ chức folder ảnh (đề xuất)

```
frontend/src/
├── assets/                          ← MỚI: tài nguyên tĩnh được Vite bundle
│   └── images/
│       ├── brand/
│       │   └── xbike-logo.svg       ← logo XBIKE + MRP SYSTEM + swoosh (vẽ tay, toàn bộ là path)
│       └── login/
│           ├── README.md            ← nguồn gốc, prompt sinh ảnh, kích thước, cách thay ảnh
│           ├── slide-01-workshop.webp
│           ├── slide-02-touring.webp
│           └── slide-03-road.webp
└── features/auth/
    ├── LoginPage.jsx                ← sửa
    ├── LoginCarousel.jsx            ← MỚI
    └── loginSlides.js               ← MỚI: manifest import 3 ảnh + alt
```

**Lý do:**
- Đặt trong `src/assets/` và `import` qua ES module để Vite gắn hash vào tên file, và **build báo lỗi nếu thiếu hoặc gõ sai tên**. Nếu để trong `public/` thì lỗi chỉ lộ ra lúc chạy.
- `brand/` tách riêng khỏi `login/` vì logo là tài sản thương hiệu, sau này có thể dùng ở sidebar hoặc favicon. `login/` chỉ chứa ảnh riêng của màn đăng nhập. Màn hình khác có ảnh riêng thì thêm `images/<màn-hình>/` cùng cấp.
- Quy ước tên `slide-<số 2 chữ số>-<chủ-đề>.<ext>`: số quyết định thứ tự, phần chủ đề cho biết nội dung. Chỉ dùng chữ thường, gạch nối, không dấu.

**Định dạng ảnh slide:** hướng dọc, tỉ lệ khoảng 4:5 (ví dụ 1200×1500, hoặc cỡ gần nhất mà công cụ hỗ trợ). Ưu tiên WebP, mỗi ảnh ≤ 400 KB. Nếu công cụ chỉ trả PNG/JPG và máy không có công cụ chuyển đổi thì giữ JPG (đổi đuôi trong tên file và manifest). **Không cài dependency để chuyển định dạng.** Ảnh không chứa chữ, logo, watermark hay thương hiệu thật.

## Bảng số đo (theo ảnh 1586×992, đơn vị px)

Ở viewport rộng ≥ 1586px, dùng đúng các số này (tỉ lệ 1:1). Viewport hẹp hơn thì co theo tỉ lệ bằng `clamp(min, <giá trị/15.86>vw, <giá trị>px)`. Ví dụ title 62px viết thành `clamp(40px, 3.91vw, 62px)`.

| Thành phần | Số đo |
|---|---|
| Card | lề ngoài khoảng 50px; rộng tối đa 1486; cao khoảng 886; bo góc 18; viền 1px `#2a2725` |
| Tỉ lệ cột | trái 798 / phải 688, tức `grid-template-columns: 1.16fr 1fr` |
| Logo | cách mép trái và mép trên 45px; rộng khoảng 172, cao khoảng 62 (cả cụm XBIKE và MRP SYSTEM) |
| Tagline | cách mép trái panel 54; cỡ 46, weight 800, line-height 1.17; dòng 1 bắt đầu ở y≈612 |
| Thumbnail | 3 cái, mỗi cái 220×120, gap 18, bo góc 10; viền thường 2px `rgb(255 255 255 / .4)`, viền đang chọn 3px `#c8794a`; top y≈748 |
| Chấm | top y≈897; chấm đang chọn 32×6 màu trắng, chấm thường 28×5 `rgb(255 255 255 / .35)`; gap 12; căn giữa panel |
| Form panel | padding trái 82, phải 51; title bắt đầu ở y≈140 |
| h1 `Đăng nhập` | cỡ 62, weight 800, màu `#f4ede6`, letter-spacing −0.01em |
| Phụ đề | cỡ 24, weight 400, màu `#e6ddd4`, cách title 26 |
| Label | cỡ 22, weight 600, màu `#f4ede6`; cách phụ đề 62, cách input 14 |
| Input | cao 72, bo góc 8, viền 1.5px `#5b5550`, nền `#24211f`, padding-x 28, chữ 22; placeholder `#b3aaa0`; khoảng cách input → label kế tiếp 42 |
| Icon mắt | 30px, cách mép phải 28, màu `#e6ddd4` |
| Nút | cao 74, bo góc 8, cách input trên 45; chữ 26 weight 600 màu `#fff4ea`; mũi tên 26px cách chữ 14 |
| Khối hỗ trợ | cách nút 89; icon 40px; vạch đứng 1px cao 62 cách icon 28; chữ cách vạch 30; `Hỗ trợ Admin` cỡ 24 weight 600; số cỡ 24 weight 400, letter-spacing 0.04em |

## Change list

### 1. Sinh 3 ảnh và tạo `frontend/src/assets/images/login/`
Dùng skill `image-generation:image-generation`. Tông chung: hoàng hôn ấm (cam/hổ phách) trên nền tối, chất ảnh điện ảnh và chân thực, chừa vùng tối phía dưới cho tagline. Đối chiếu với [ảnh thiết kế](assets/login-design.png).

| File | Nội dung (prompt gợi ý) |
|---|---|
| `slide-01-workshop.webp` | Xe đạp thành phố khung đen mờ (có baga sau, phanh đĩa) đứng chân chống giữa xưởng lắp ráp xe đạp công nghiệp. Cửa sổ lưới sắt lớn, mặt trời lặn sau dãy núi. Bánh xe treo trên giá bên phải, kệ dụng cụ vàng mờ phía sau, sàn bê tông phản chiếu ánh hoàng hôn. Chụp ngang, xe nằm giữa khung. |
| `slide-02-touring.webp` | Xe touring/gravel màu xanh rêu có túi treo (pannier) đứng trên mỏm đá giữa núi lúc hoàng hôn, các lớp núi mờ sương phía xa. |
| `slide-03-road.webp` | Xe đạp đua khung bạc, ghi đông cong, trong studio/xưởng tối. Ánh sáng viền làm nổi khung, nền bokeh tối. |

Tạo `README.md` ghi mục đích từng ảnh, prompt đã dùng, kích thước và định dạng, ngày sinh, cách thay ảnh.

### 2. Font cho trang đăng nhập: chọn bằng so sánh, rồi nạp vào `frontend/index.html`
**2a. So sánh trước khi chốt** (làm trong thư mục tạm, **không** tạo file trong repo):
- Tạo một trang HTML tạm. Mỗi hàng hiển thị **một vùng cắt của ảnh thiết kế** (dùng `background-image` + `background-position` trỏ tới `.handoff/assets/login-design.png`, không cần công cụ cắt ảnh), và bên cạnh là cùng đoạn chữ đó render bằng từng font ứng viên, đúng cỡ và weight trong Bảng số đo:
  - Display (`Đăng nhập` 62/800, `Kiểm soát kho.` 46/800): **Be Vietnam Pro**, Plus Jakarta Sans, Lexend.
  - Body (`Sử dụng tài khoản được quản trị viên cấp.` 24/400, `Tên đăng nhập` 22/600, `Hỗ trợ Admin` 24/600, `0900 000 000` 24/400, `Đăng nhập` trên nút 26/600): **Noto Sans**, Fira Sans, Be Vietnam Pro.
- Chụp màn hình bằng Playwright (đã cài sẵn), đối chiếu các điểm: độ đậm, độ rộng chữ, hình `a`/`g`/`đ`/`ậ`, vị trí dấu, hình chữ số `0`. Chọn font giống nhất cho mỗi vai trò. **Ghi lại font đã chọn và lý do** trong báo cáo bàn giao và trong comment cạnh token CSS. Nếu không ứng viên nào khớp rõ ràng thì giữ mặc định (in đậm ở trên).

**2b. Nạp font:** sửa thẻ `<link>` Google Fonts hiện có trong [index.html](../frontend/index.html) thành một request gộp. Giữ IBM Plex Sans cho các trang khác:
```
https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Be+Vietnam+Pro:wght@800&family=Noto+Sans:wght@400;600&display=swap
```
(Thay family hoặc weight theo kết quả 2a. Chỉ nạp những weight thực sự dùng.) Trình duyệt chỉ tải file font khi có phần tử dùng đến, nên các trang khác không phải tải thêm. Google Fonts tự chia `unicode-range` cho tiếng Việt.

### 3. MỚI `frontend/src/assets/images/brand/xbike-logo.svg` (vẽ tay)
Đối chiếu vùng logo trong ảnh thiết kế (x 85–275, y 85–160).
- **Toàn bộ là `<path>` hoặc `<polygon>`, không dùng `<text>`**, vì SVG nhúng qua `<img>` không dùng được web font của trang.
- `XBIKE`: chữ in hoa rất đậm (độ dày nét khoảng 22% chiều cao chữ), nghiêng khoảng −12°, hình học, khoảng cách giữa các chữ hẹp. `B` có 2 bầu bo tròn; `K` và `X` có các đầu nét cắt xiên theo góc nghiêng.
- **Swoosh**: nét cong thon dần, bắt đầu dưới góc trái của `X`, vòng lên nối vào chân trái của `X`. Thêm một nét đuôi mảnh, ngắn, thon dần ở bên phải cuối dòng `MRP SYSTEM`.
- `MRP SYSTEM`: chữ in hoa nhỏ (chiều cao khoảng 30% chiều cao `XBIKE`), nét đều (có thể dùng `stroke` rồi chuyển thành path, hoặc giữ `stroke` với `stroke-linecap="square"`), letter-spacing rộng (khoảng 0.3em), không nghiêng, căn trái thẳng với chân của `X`.
- Màu `#FFFFFF`. `viewBox` bó sát nội dung (tỉ lệ khoảng 172:62). Có `<title>XBIKE MRP System</title>`. File ≤ 6 KB, không có metadata của trình soạn thảo.
- Dùng bằng `import logo from "…/brand/xbike-logo.svg"` và `<img src={logo} alt="XBIKE MRP System">`.

### 4. MỚI `frontend/src/features/auth/loginSlides.js`
```js
import workshop from "../../assets/images/login/slide-01-workshop.webp";
import touring from "../../assets/images/login/slide-02-touring.webp";
import road from "../../assets/images/login/slide-03-road.webp";
export const LOGIN_SLIDES = [
  { id: "workshop", src: workshop, alt: "Xe đạp thành phố trong xưởng lắp ráp lúc hoàng hôn" },
  { id: "touring", src: touring, alt: "Xe đạp touring trên núi lúc hoàng hôn" },
  { id: "road", src: road, alt: "Xe đạp đua khung bạc trong xưởng" },
];
export const LOGIN_SLIDE_INTERVAL_MS = 5000;
```
(Đuôi file khớp với ảnh thực tế ở bước 1.)

### 5. MỚI `frontend/src/features/auth/LoginCarousel.jsx`
Props: `slides`, `interval`. Render:
- `<section className="login-visual" aria-roledescription="carousel" aria-label="Hình ảnh giới thiệu XBIKE">`.
- `.login-visual-slides`: mỗi slide là `<img>` `position: absolute; inset: 0; object-fit: cover`. Slide không active có `aria-hidden="true"`.
- Lớp phủ gradient tối dần xuống dưới để chữ dễ đọc (tối nhất khoảng `rgb(0 0 0 / .75)` ở đáy, trong suốt từ khoảng 45% chiều cao trở lên).
- Logo: `<img className="login-logo" src={logo} alt="XBIKE MRP System" />` (bước 3).
- Tagline: `<h2 className="login-tagline">Kiểm soát kho.<br />Điều phối sản xuất.</h2>`.
- Thumbnail: `<div className="login-thumbs">` gồm 3 `<button type="button">` chứa `<img alt="">`, với `aria-label={`Xem ảnh ${i+1}: ${alt}`}` và `aria-current={active ? "true" : undefined}`.
- Chấm: `<div className="login-dots">` gồm 3 `<button type="button" aria-label={`Ảnh ${i+1}`}>`, dùng chung `aria-current`.

**Trượt một chiều (ảnh mới luôn vào từ phải):** state `{ active, leaving }`.
- Slide mặc định có `transform: translateX(100%); transition: none` (chờ bên phải, ngoài khung).
- `.is-active` là `translateX(0)`, `.is-leaving` là `translateX(-100%)`. Chỉ hai class này có `transition: transform 700ms ease`.
- `goTo(next)`: nếu `next === active` thì bỏ qua, ngược lại `setState({ active: next, leaving: active })`. Slide vừa rời đi sẽ nhảy về +100% ở lần chuyển kế tiếp mà không có transition, ngoài khung nên không thấy.
- Auto-play: `useEffect` đặt `setTimeout(interval)` rồi gọi `goTo((active + 1) % n)`. Effect phụ thuộc `active` và `paused`, nên mỗi lần click tay thì đếm lại.
- `paused` bật khi `onMouseEnter`/`onFocus`, tắt khi `onMouseLeave`/`onBlur` (chỉ khi `relatedTarget` nằm ngoài section). Khi tab bị ẩn (`document.visibilitychange`) thì dừng.
- Reduced motion: dùng `matchMedia("(prefers-reduced-motion: reduce)")` và lắng nghe `change`. Khi bật thì không auto-play, chuyển ảnh không có transition, click vẫn đổi ảnh.
- Ảnh đầu đặt `fetchpriority="high"`. Cả 3 ảnh `loading="eager"`.

### 6. Sửa `frontend/src/features/auth/LoginPage.jsx`
- **Giữ nguyên toàn bộ logic** (`useAuth`, `submit`, ref `pending`, `Navigate`, `ErrorNotice`, `trim` username, xoá password khi thành công).
- Header: `<header className="login-header">` chứa `<img src={logo} alt="XBIKE MRP System" className="login-header-logo" />` và `<small>Hệ thống quản lý kho & sản xuất</small>`.
- `<section className="login-intro">` thay bằng `<LoginCarousel slides={LOGIN_SLIDES} interval={LOGIN_SLIDE_INTERVAL_MS} />`.
- Form: giữ h1, phụ đề, `ErrorNotice` và `Field` tên đăng nhập.
- Mật khẩu: bọc trong `<div className="password-field">` gồm `Field` (thêm `placeholder="Nhập mật khẩu"`) và nút toggle `className="password-toggle"`, `aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}`, `aria-pressed={visible}`, icon `<Eye />`/`<EyeOff />` (lucide-react, `aria-hidden="true"`, size 30, `strokeWidth={1.75}`). **Giữ accessible name `Hiện mật khẩu`** vì test hiện có dùng tên này.
- Submit: `<Button type="submit" disabled={busy}>{busy ? "Đang đăng nhập…" : "Đăng nhập"}{!busy && <ArrowRight aria-hidden="true" size={26} strokeWidth={2.25} />}</Button>`. Accessible name vẫn là `Đăng nhập`.
- Thay `<small>Gặp sự cố…</small>` bằng khối hỗ trợ, đặt ngoài `<form>`, ở cuối `.login-form`:
  ```jsx
  const SUPPORT_PHONE = { display: "0900 000 000", tel: "0900000000" }; // đầu file
  <div className="login-support">
    <Phone aria-hidden="true" size={40} strokeWidth={1.5} />
    <div>
      <strong>Hỗ trợ Admin</strong>
      <a href={`tel:${SUPPORT_PHONE.tel}`}>{SUPPORT_PHONE.display}</a>
    </div>
  </div>
  ```
- Footer: giữ `© {năm} XBIKE · Hệ thống nội bộ`.

### 7. Sửa `frontend/src/app/App.css`: thay khối `.login-*` (dòng ~825-905) và các rule login trong `@media (max-width: 900px)` / `(max-width: 600px)`
**Token trên `.login-page`:**

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--login-font-display` | `"Be Vietnam Pro", "IBM Plex Sans", sans-serif` | h1, tagline (theo kết quả 2a) |
| `--login-font-body` | `"Noto Sans", "IBM Plex Sans", sans-serif` | toàn bộ phần còn lại của trang (theo kết quả 2a) |
| `--login-bg` | `#121212` | nền trang, header, footer |
| `--login-card` | `#1b1918` | nền cột form |
| `--login-card-border` | `#2a2725` | viền card, header, footer |
| `--login-input-bg` | `#24211f` | nền input |
| `--login-input-border` | `#5b5550` | viền input, vạch đứng ở khối hỗ trợ |
| `--login-text` | `#f4ede6` | tiêu đề, label, chữ input |
| `--login-muted` | `#e6ddd4` | phụ đề, icon mắt; footer dùng `#a39a90` |
| `--login-placeholder` | `#b3aaa0` | placeholder |
| `--login-accent` | `#c8794a` | nút, viền thumbnail đang chọn, focus ring |
| `--login-accent-hover` | `#d68a5b` | nút khi hover |
| `--login-accent-text` | `#fff4ea` | chữ trên nút |

**Rule chính** (cỡ và khoảng cách theo **Bảng số đo**, co giãn bằng `clamp` như đã nêu):
- `.login-page { font-family: var(--login-font-body); background: var(--login-bg); color: var(--login-text); }`. `.login-form h1`, `.login-tagline` dùng `font-family: var(--login-font-display); font-weight: 800`. Bật `-webkit-font-smoothing: antialiased` cho chữ sáng trên nền tối.
- `.login-header`: nền `--login-bg`, viền dưới `--login-card-border`. `.login-header-logo` cao 32px. `small` màu `--login-muted`.
- `.login-main`: padding 50px.
- `.login-card`: `max-width: 1486px; grid-template-columns: 1.16fr 1fr; min-height: 886px` (co theo viewport: `min-height: min(886px, 56vw)`), `border-radius: 18px`, viền `--login-card-border`, nền `--login-card`, `overflow: hidden`.
- `.login-visual`: `position: relative; overflow: hidden; isolation: isolate`. `.login-logo` đặt absolute ở `top: 45px; left: 45px; width: 172px`. Cột dưới (tagline, thumbnail, chấm) đặt absolute ở đáy, padding `0 48px 32px 54px`.
- `.login-tagline`: cỡ `clamp(26px, 2.9vw, 46px)`, line-height 1.17, `#fff`, `text-shadow: 0 2px 12px rgb(0 0 0 / .5)`, margin-bottom 34px.
- `.login-thumbs`: grid 3 cột, gap 18px. Thumbnail `aspect-ratio: 220 / 120; border-radius: 10px; border: 2px solid rgb(255 255 255 / .4); padding: 0; overflow: hidden; background: none`. `[aria-current="true"]` dùng `border: 3px solid var(--login-accent)`.
- `.login-dots`: margin-top 30px, căn giữa, gap 12px. Chấm `28×5` (đang chọn `32×6`, `#fff`), bo tròn. Vùng bấm tối thiểu 24px bằng `padding` trong suốt và `background-clip: content-box`.
- `.login-form`: padding `88px 51px 60px 82px`. h1 cỡ `clamp(40px, 3.91vw, 62px)`, letter-spacing −0.01em, line-height 1.1. Phụ đề cỡ `clamp(16px, 1.51vw, 24px)`, màu `--login-muted`, margin-top 26px.
- `.login-form .field label`: cỡ `clamp(15px, 1.39vw, 22px)`, weight 600. `.login-form .field input`: cao `clamp(52px, 4.54vw, 72px)`, padding `0 28px`, chữ `clamp(16px, 1.39vw, 22px)`, nền `--login-input-bg`, `border: 1.5px solid var(--login-input-border)`, bo góc 8px, chữ `--login-text`. Placeholder `--login-placeholder`.
- Khoảng cách dọc: phụ đề → label đầu 62px; label → input 14px; input → label kế tiếp 42px; input mật khẩu → nút 45px. Dùng `gap`/`margin` trên `.login-form .stack` và `.field`, không đổi `.stack` toàn cục.
- `.password-field { position: relative }`, input `padding-right: 72px`. `.password-toggle`: absolute, `right: 14px`, căn giữa theo chiều dọc của input (`bottom` bằng `(chiều cao input − 44) / 2`), 44×44, `border: 0; background: none; color: var(--login-muted)`, không gạch chân.
- `.login-form .btn-primary`: nền `--login-accent`, chữ `--login-accent-text`, cao `clamp(54px, 4.67vw, 74px)`, bo góc 8px, cỡ `clamp(17px, 1.64vw, 26px)`, weight 600, gap 14px. Hover dùng `--login-accent-hover`.
- `.login-form .required { display: none }`.
- `.login-page :focus-visible { outline-color: var(--login-accent) }`.
- `.login-form .notice-error { background: #3a1e1a; border-color: #7a3b31; color: #ffb9ad }`.
- `.login-support`: `display: flex; align-items: center; gap: 28px; margin-top: 89px`. Div chữ: `border-left: 1px solid var(--login-input-border); padding-left: 30px; min-height: 62px; display: flex; flex-direction: column; justify-content: center`. `strong` cỡ `clamp(16px, 1.51vw, 24px)` weight 600; `a` cùng cỡ, weight 400, letter-spacing 0.04em, màu `--login-text`, không gạch chân (gạch chân khi hover).
- `.login-footer`: màu `#a39a90`.
- Slide: rule `.login-visual-slides img`, `.is-active`, `.is-leaving` như bước 5. Thêm `@media (prefers-reduced-motion: reduce) { .login-visual-slides img { transition: none !important } }`, vì rule toàn cục ở [App.css:1075](../frontend/src/app/App.css#L1075) chỉ tắt `animation`.
- `≤ 1200px`: form padding `56px 40px`.
- `≤ 900px`: card 1 cột, `.login-visual` cao 320px, ẩn `.login-thumbs` (giữ chấm), logo rộng 140px.
- `≤ 600px`: `.login-main` padding `24px 16px`; `.login-visual` cao 240px, padding 24px; tagline 22px; form padding `32px 20px`; `.login-support` margin-top 40px. Xoá các rule cũ `.login-intro …`.

### 8. MỚI `frontend/tests/browser/login.spec.js` (Playwright)
Dùng `installApi(page, { authenticated: false })` như [workflows.spec.js](../frontend/tests/browser/workflows.spec.js).
1. Trang có đủ thành phần: heading `Đăng nhập`, phụ đề, 2 label, nút `Đăng nhập`, `Hỗ trợ Admin`, link `tel:0900000000`, tagline, logo (`img` có alt `XBIKE MRP System`), 3 thumbnail, 3 chấm, header, footer.
2. Auto-play: `page.clock.install()` trước `goto`, rồi `runFor(5000)`: `aria-current` chuyển từ 1 sang 2. Chạy thêm 2 nhịp thì quay về 1.
3. Click thumbnail 3 thì thumbnail 3 có `aria-current="true"`.
4. Hover lên panel và chạy 10s thì ảnh không đổi.
5. `emulateMedia({ reducedMotion: "reduce" })` và chạy 10s thì ảnh không đổi.
6. Bấm `Hiện mật khẩu` thì input đổi sang `type="text"` và nút đổi tên thành `Ẩn mật khẩu`.

Test font **không** đặt trong spec (phụ thuộc mạng Google Fonts). Font được kiểm ở bước kiểm chứng 5.

Các test login hiện có trong `workflows.spec.js` phải pass **mà không cần sửa**.

## Sync commands

(none: không thêm dependency. `lucide-react` 0.359 có sẵn `Eye`, `EyeOff`, `Phone`, `ArrowRight`. Font nạp qua Google Fonts, đúng cơ chế đang dùng cho IBM Plex Sans.)

## Test strategy

- Logic carousel test bằng Playwright với đồng hồ giả (bước 8).
- Kiểm tra hồi quy: chạy toàn bộ `tests/browser/`.
- **Đối chiếu bằng mắt với ảnh thiết kế** là tiêu chí nghiệm thu chính về hình thức, gồm cả font (bước kiểm chứng 5).

## Verification plan

Chạy trong `frontend/`:
1. `npm run lint`
2. `npm test`
3. `npm run build`: 3 ảnh và `xbike-logo.svg` phải xuất hiện trong `dist/assets/` có hash, không có lỗi import.
4. `npx playwright test`
5. **So sánh với thiết kế** (script Playwright trong thư mục tạm, không đưa vào repo):
   - Kiểm tra font đã nạp: `await document.fonts.ready`, sau đó `document.fonts.check('800 62px "Be Vietnam Pro"', 'Đăng nhập')` và `document.fonts.check('400 24px "Noto Sans"', 'Sử dụng')` (hoặc font đã chọn ở 2a) phải trả `true`. Đồng thời `getComputedStyle(h1).fontFamily` phải bắt đầu bằng font display.
   - Kiểm tra trang khác không bị đổi font: `getComputedStyle(document.body).fontFamily` ở `/kho` (sau khi đăng nhập bằng fixture) vẫn bắt đầu bằng `"IBM Plex Sans"`.
   - Chụp `/dang-nhap` ở viewport **1586×(chiều cao đủ chứa header, card, footer)**, cắt lấy vùng card, đặt cạnh `.handoff/assets/login-design.png`. Đối chiếu: font và độ đậm, cỡ chữ, vị trí từng thành phần (lệch ≤ 8px so với Bảng số đo), màu nền, input, nút, viền thumbnail, chấm, logo và swoosh.
   - Chụp thêm ở 900×1000 và 390×844 để kiểm tra layout co giãn, không có thanh cuộn ngang.

## Compile check

Không có typecheck (dự án JS thuần). Dùng `npm run build` làm bước kiểm tra biên dịch.

## Parallelization

- Nhóm A: bước 1 (sinh ảnh và README). Độc lập.
- Nhóm B: bước 2a và 3 (chọn font, vẽ logo). Độc lập với A.
- Bước 4 làm sau A (cần biết đúng đuôi file). Bước 5, 6, 7 làm sau B (cần font và logo). Bước 8 làm sau 5–7.

## Ngoài phạm vi

- Không đổi font hay theme của các trang khác (dev chốt font mới tạm thời chỉ dùng cho trang đăng nhập).
- Không sửa `Button`, `Field`, `ErrorNotice` dùng chung. Không đổi favicon hay `<title>`.
- Không commit hoặc push (AGENTS.md mục 1).
