# Kiểm chứng DB thật và backend Nhân viên — 17/11/2026

Source: `03fb878`. Người dùng yêu cầu thử truy vấn DB thật và E2E backend. Không sửa source backend hoặc DB ứng dụng.

## Cập nhật sau khi người dùng chọn cách 3 — tạo lại DB theo main

Phần kiểm tra DB cũ bên dưới là lịch sử trước cập nhật. Sau khi giải thích mất dữ liệu và được người dùng chọn cách 3, đã sao lưu custom pg_dump, kiểm tra archive đọc được và lưu bản 129505 byte tại `C:/Users/binhb/AppData/Local/Temp/xbike-db-backup-20261117-114842/xbike_mrp.dump`. Cấu hình runtime cũ cũng được sao lưu cùng thư mục.

Đã drop/create đúng database `xbike_mrp` trong container `xbike_ui_nhanvien_postgres`, không xóa volume hay tác động database khác; chạy init.sql và seed.sql khớp main `b228193`, cả hai exit 0. DB hiện có các cột tồn/giữ/còn dùng mới, 4 tài khoản, 14 mặt hàng, 8 yêu cầu. Không tạo `xbike_mrp_main` vì người dùng đổi từ cách 1 sang cách 3 trước khi thao tác ghi.

Đã khởi động backend container hiện có, giữ cấu hình runtime trỏ postgres:5432/xbike_mrp, không sửa source hoặc Dockerfile. Kiểm HTTP thật tại localhost:8000: ba tài khoản demo `nhan_vien_sx`, `nhan_vien_lr`, `quan_ly_kho` đăng nhập 200; `/auth/me`, `/mat_hang`, `/yeu_cau_san_xuat` đều 200. Hai NV lần lượt nhận 3/4 yêu cầu, QLK nhận 8; mặt hàng đều 14. Không in token vào báo cáo. Đăng nhập tạo audit trên DB mới theo hành vi backend.

Backend và PostgreSQL đang chạy; browser preview fixture chưa được chuyển sang phiên đăng nhập API thật. Đây là smoke HTTP đọc dữ liệu, chưa chạy lại toàn bộ luồng ghi chứng từ trên DB demo mới. Log bootstrap tại `%TEMP%/xbike-main-init-20261117.log` và `xbike-main-seed-20261117.log`.

## DB ứng dụng

Khởi động lại container có sẵn `xbike_ui_nhanvien_postgres`, dùng volume hiện có. Truy vấn psql trong `BEGIN READ ONLY`/`COMMIT` thành công: database `xbike_mrp`, PostgreSQL 16.15, 21 bảng public.

DB còn bảng `LenhSanXuat`; bảng `MatHang` không có `so_luong_dang_giu` và `so_luong_con_dung`. Đây là khác biệt schema cụ thể với source main hiện tại; không kết luận DB ứng dụng đã sẵn sàng chạy backend main. Không chạy bootstrap/seed/ALTER/reset trên DB này, không khởi động backend ứng dụng để tránh background task ghi dữ liệu.

## Kiểm thử trên PostgreSQL test riêng

Tạo container `xbike-nv-e2e-20261117`, postgres:16-alpine, chỉ publish localhost:55465, không gắn volume ứng dụng. Dùng dependency có sẵn trong image backend và mount source hiện tại read-only. Không cài dependency hay build lại Dockerfile.

Chạy `python -m pytest -p no:cacheprovider tests/test_phieu_xuat_api.py tests/test_phieu_xuat_postgres.py -q`: **48 passed in 80.19s, exit 0**, không skip. Fixture tạo database UUID mới/trống cho từng ca và bootstrap từ init.sql hiện tại; các database test đó được dọn bởi fixture. Kiểm tra sau cùng không còn database `goods_issue_<uuid>_test`.

Phạm vi: API ASGI thực tế, dependency xác thực/role và PostgreSQL thật; tạo/gửi/duyệt phiếu linh kiện/thành phẩm, từ chối/gửi lại, ETag, quyền, cạnh tranh, ghi sổ một lần, ràng buộc và rollback. Các ca này tạo token test, không đi qua endpoint đăng nhập.

Bổ sung smoke tạm `test_nv_real_login_smoke_20261117.py`: **1 passed in 2.75s, exit 0**. Test đăng nhập thật qua `/api/v1/auth/dang_nhap` cho hai NV và một QLK, kiểm `/auth/me`, NV được giao tạo/gửi phiếu, NV khác bị chặn chi tiết, NV không đọc được danh sách QLK hoặc duyệt, QLK duyệt thành công. Truy vấn DB test xác nhận tồn linh kiện từ 100/100 về 93/86, giữ hàng về 0 và có ba audit đăng nhập. Không override auth hoặc service; chỉ override session DB sang database test theo fixture có sẵn.

Log và smoke tạm tại `%TEMP%`: `xbike-nv-backend-postgres-20261117.log`, `xbike-nv-real-login-20261117.log`, `test_nv_real_login_smoke_20261117.py`. Lần chạy smoke đầu không khởi động được do mount file dưới mount read-only (exit 125); đã đổi mount tạm sang `/audit` và lượt sau đạt như trên, không sửa assertion.

Container test đã dừng sau kiểm chứng, không xóa volume ứng dụng. PostgreSQL ứng dụng được giữ chạy sau truy vấn chỉ đọc.

## Giới hạn

Đây là kiểm thử tích hợp backend/API/PostgreSQL qua ASGI, chưa là browser E2E hoặc kiểm HTTP server/lifespan/CORS. Smoke chuẩn bị yêu cầu đang thực hiện bằng fixture SQL trên DB test; chưa kiểm toàn chuỗi tạo yêu cầu → kiểm vật tư → bắt đầu → hoàn thành → xuất bằng API thật. NV-MAIN-005/006, accessibility và nghiệm thu vẫn mở. Chưa cập nhật PR/commit/push trong lượt này.
