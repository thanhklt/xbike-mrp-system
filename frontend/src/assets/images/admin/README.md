# Ảnh giao diện admin

| File | Mục đích | Kích thước | Định dạng | Dung lượng |
| --- | --- | --- | --- | --- |
| sidebar-artwork.webp | Hình trang trí cuối sidebar admin (hoàng hôn, xe touring) | 258 × 600 | WebP | 17022 byte |

Nguồn: cắt từ mockup `doc/ui-spec-admin/tong_quan.png` (commit `f1085ae`, thư mục `doc/` đã xoá ở `a9eb1f2`), vùng `x 0–258, y 331–931` — đúng phần sidebar của mockup, bỏ viền phải và dải trắng đáy ảnh chụp. Chuyển sang WebP chất lượng 88 bằng Pillow, ngày 16/11/2026.

Hiển thị trong `src/layouts/Sidebar.jsx` (khối `.adminArtwork`, chỉ khi `adminTheme`). CSS dùng `object-fit: cover` neo đáy, phủ gradient tối ở mép trên.

## Cách thay ảnh

1. Ảnh dọc khoảng 258 × 600 (hoặc gấp đôi cho màn hình retina), chủ thể ở nửa dưới, nửa trên tối để hoà vào nền `#1b1511`.
2. Nếu đổi tên hoặc định dạng, cập nhật import trong `src/layouts/Sidebar.jsx`.
3. Chạy `npm run build`, kiểm tra sidebar admin ở desktop và mobile.
