# Ảnh trang đăng nhập

Ba ảnh nền carousel, tạo ngày 05/11/2026 bằng công cụ imagegen tích hợp (không dùng CLI/API fallback). Ảnh tham khảo hình thức: `.handoff/assets/login-design.png`; ảnh nền được tạo mới, không lấy từ thương hiệu hoặc thư viện ảnh bên ngoài.

| File | Mục đích | Kích thước | Định dạng | Dung lượng |
| --- | --- | --- | --- | --- |
| slide-01-workshop.webp | Xe thành phố trong xưởng; slide đầu | 1122 × 1402 | WebP | 153684 byte |
| slide-02-touring.webp | Xe touring trên núi; slide thứ hai | 1122 × 1402 | WebP | 126494 byte |
| slide-03-road.webp | Xe đua khung bạc trong xưởng; slide thứ ba | 1122 × 1402 | WebP | 105806 byte |

Đầu ra gốc là PNG. Chuyển sang WebP chất lượng 0.82 bằng Canvas trong Chrome qua Playwright có sẵn, giữ kích thước gốc; không cài dependency. Thumbnail dùng lại cùng file, cắt bằng CSS `object-fit: cover`.

## Prompt đã dùng

### 1. workshop

Use case: photorealistic-natural. Asset: portrait 4:5 login carousel background photograph, 1200x1500 or close. A matte black city bicycle with rear rack, disc brakes and kickstand in an industrial bicycle assembly workshop. Side-on view with the entire bicycle centered in the upper-middle area, both wheels visible. Large gridded windows with warm amber sunset over distant mountains, hanging bicycle wheels on right, muted yellow tool racks, concrete floor reflecting sunset. Cinematic realistic photography, warm amber against charcoal shadows. Leave the lower third dark for a UI text overlay. No people, no text, no logos, no watermark, no brands.

### 2. touring

Use case: photorealistic-natural. Asset: portrait 4:5 login carousel background photograph, 1200x1500 or close. Moss green touring/gravel bicycle with pannier bags, standing on rocky mountain overlook at warm amber sunset, layered misty mountain ranges in the distance. Cinematic realistic photography, warm orange highlights against charcoal shadows. Side-on view, whole bicycle visible in the upper-middle area, leave the lower third dark for a UI text overlay. No people, no text, no logos, no watermark, no brands.

### 3. road

Use case: photorealistic-natural. Asset: portrait 4:5 login carousel background photograph, 1200x1500 or close. Silver road racing bicycle with drop handlebars in a dark bicycle workshop studio. Cinematic realistic photography, warm amber rim lighting outlining the silver frame, dark blurred bokeh workshop background. Three-quarter side view, bicycle frame and both wheels visible in upper-middle area, lower third dark for a UI text overlay. No people, no text, no logos, no watermark, no brands.

## Cách thay ảnh

1. Thay file tương ứng bằng ảnh dọc xấp xỉ 4:5, dưới 400 KB, không chứa chữ, logo hoặc watermark. Chừa vùng tối dưới ảnh để tagline dễ đọc.
2. Nếu đổi tên hoặc định dạng, cập nhật import, thứ tự và alt trong `src/features/auth/loginSlides.js`.
3. Ghi lại nguồn, prompt, kích thước và ngày thay trong file này. Chạy `npm run build` và kiểm tra crop cả ảnh nền lẫn thumbnail ở desktop/mobile.

