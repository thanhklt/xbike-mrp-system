-- xBike MRP data model v3.1 — dữ liệu demo cố định, không phải dữ liệu vận hành.
-- Tương thích init.sql v3.1: số dư tồn nằm trong public."MatHang".
-- Yêu cầu: init.sql đã chạy thành công và các bảng chưa có dữ liệu.
-- Không chạy lại trên DB đã seed; không xóa/ghi đè dữ liệu có sẵn.
-- 3 tài khoản demo dùng mật khẩu DemoXbike2026! (bcrypt cost 12).
BEGIN;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL search_path = public, pg_catalog;
DO $$
DECLARE t record; used boolean;
BEGIN
  FOR t IN SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' AND tablename=ANY(ARRAY['NhanVien','VaiTro','MatHang','Bom','ChiTietBom','NhaCungCap','PhieuNhap','ChiTietPhieuNhap','PhieuXuat','ChiTietPhieuXuat','YeuCauSanXuat','LenhSanXuat','ChiTietLenhSanXuat','ChungTuHoanThanhSx','PhieuDieuChinhKho','ChiTietPhieuDieuChinhKho','TicketLoiDieuChinh','ChiTietTicketLoiDieuChinh','GiaoDichKho','LichSuThaoTac']) LOOP
    EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I.%I)', t.schemaname, t.tablename) INTO used;
    IF used THEN RAISE EXCEPTION 'seed.sql yêu cầu DB trống; bảng % đã có dữ liệu',t.tablename; END IF;
  END LOOP;
END $$;

INSERT INTO public."VaiTro" (id, ma_vai_tro, ten_vai_tro) VALUES
  (1, 'quan_tri_vien', 'Quản trị viên'),
  (2, 'quan_ly', 'Quản lý'),
  (3, 'nhan_vien', 'Nhân viên');

INSERT INTO public."NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien, ho_ten, ngay_vao_lam, trang_thai) VALUES
  (1, 1, 'quan_tri', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000001', 'Nguyễn Minh An', '2026-10-01', 'hoat_dong'),
  (2, 2, 'quan_ly_kho', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000002', 'Trần Thanh Bình', '2026-10-01', 'hoat_dong'),
  (3, 3, 'nhan_vien_sx', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000003', 'Lê Hoàng Nam', '2026-10-01', 'hoat_dong');

INSERT INTO public."MatHang" (id, ma_mat_hang, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, is_active) VALUES
  (1, 'MH-000001', 'Xe Mountain Pro', 'XE-MOUNTAIN-PRO', 'thanh_pham', 'chiec', true),
  (2, 'MH-000002', 'Xe City Ride', 'XE-CITY-RIDE', 'thanh_pham', 'chiec', true),
  (3, 'MH-000003', 'Xe Speed Sport', 'XE-SPEED-SPORT', 'thanh_pham', 'chiec', true),
  (4, 'MH-000004', 'Xe Kids Fun', 'XE-KIDS-FUN', 'thanh_pham', 'chiec', true),
  (5, 'MH-000005', 'Cụm bánh xe', 'CUM-BANH-XE', 'ban_thanh_pham', 'chiec', true),
  (6, 'MH-000006', 'Khung xe', 'KHUNG-XE', 'linh_kien', 'chiec', true),
  (7, 'MH-000007', 'Phuộc xe', 'PHUOC-XE', 'linh_kien', 'chiec', true),
  (8, 'MH-000008', 'Lốp xe', 'LOP-XE', 'linh_kien', 'chiec', true),
  (9, 'MH-000009', 'Xích xe', 'XICH-XE', 'linh_kien', 'chiec', true),
  (10, 'MH-000010', 'Bàn đạp', 'BAN-DAP', 'linh_kien', 'chiec', true),
  (11, 'MH-000011', 'Dây phanh', 'DAY-PHANH', 'linh_kien', 'chiec', true),
  (12, 'MH-000012', 'Yên xe', 'YEN-XE', 'linh_kien', 'chiec', true),
  (13, 'MH-000013', 'Đĩa xích', 'DIA-XICH', 'linh_kien', 'chiec', true),
  (14, 'MH-000014', 'Bộ ốc vít', 'BO-OC-VIT', 'linh_kien', 'bo', true),
  (15, 'MH-000015', 'Vành bánh xe', 'VANH-BANH-XE', 'linh_kien', 'chiec', true),
  (16, 'MH-000016', 'Moay-ơ', 'MOAY-O', 'linh_kien', 'chiec', true),
  (17, 'MH-000017', 'Nan hoa', 'NAN-HOA', 'linh_kien', 'chiec', true);

INSERT INTO public."NhaCungCap" (id, ma_ncc, ten_ncc, dia_chi, tinh) VALUES
  (1, 'NCC-000001', 'Nhà cung cấp linh kiện xe đạp Minh Phát', 'Địa chỉ minh họa', 'Thành phố Hồ Chí Minh');

-- Năm BOM riêng; bốn model xe cùng định mức minh họa, mỗi BOM đầu ra một đơn vị.

INSERT INTO public."Bom" (id, mat_hang_id, version, start_time, is_active) VALUES
  (1, 1, 1, '2026-10-01 08:00:00+07', true),
  (2, 2, 1, '2026-10-01 08:00:00+07', true),
  (3, 3, 1, '2026-10-01 08:00:00+07', true),
  (4, 4, 1, '2026-10-01 08:00:00+07', true),
  (5, 5, 1, '2026-10-01 08:00:00+07', true);

INSERT INTO public."ChiTietBom" (id, bom_id, mat_hang_id, so_luong) VALUES
  (1, 1, 6, 1),
  (2, 1, 7, 1),
  (3, 1, 5, 2),
  (4, 1, 8, 2),
  (5, 1, 9, 1),
  (6, 1, 10, 2),
  (7, 1, 11, 2),
  (8, 1, 12, 1),
  (9, 1, 13, 1),
  (10, 1, 14, 1),
  (11, 2, 6, 1),
  (12, 2, 7, 1),
  (13, 2, 5, 2),
  (14, 2, 8, 2),
  (15, 2, 9, 1),
  (16, 2, 10, 2),
  (17, 2, 11, 2),
  (18, 2, 12, 1),
  (19, 2, 13, 1),
  (20, 2, 14, 1),
  (21, 3, 6, 1),
  (22, 3, 7, 1),
  (23, 3, 5, 2),
  (24, 3, 8, 2),
  (25, 3, 9, 1),
  (26, 3, 10, 2),
  (27, 3, 11, 2),
  (28, 3, 12, 1),
  (29, 3, 13, 1),
  (30, 3, 14, 1),
  (31, 4, 6, 1),
  (32, 4, 7, 1),
  (33, 4, 5, 2),
  (34, 4, 8, 2),
  (35, 4, 9, 1),
  (36, 4, 10, 2),
  (37, 4, 11, 2),
  (38, 4, 12, 1),
  (39, 4, 13, 1),
  (40, 4, 14, 1),
  (41, 5, 15, 1),
  (42, 5, 16, 1),
  (43, 5, 17, 36);

-- Phiếu nhập hoàn tất có 12 dòng NVL/linh kiện. Phiếu thứ hai còn nháp, không cộng kho.

INSERT INTO public."PhieuNhap" (id, ma_phieu_nhap, nhan_vien_id, ncc_id, ngay_nhap, ghi_chu, trang_thai, created_at) VALUES
  (1, 'PN-202610-000001', 2, 1, '2026-10-22', 'Lô linh kiện demo cho sản xuất 10 xe; số nan hoa sẽ được điều chỉnh.', 'nhap', '2026-10-22 08:30:00+07'),
  (2, 'PN-202610-000002', 2, 1, '2026-10-23', 'Phiếu nháp bổ sung khung xe; chưa xác nhận, chưa tăng tồn.', 'nhap', '2026-10-22 08:35:00+07');

INSERT INTO public."ChiTietPhieuNhap" (id, phieu_nhap_id, mat_hang_id, so_luong) VALUES
  (1, 1, 6, 10),
  (2, 1, 7, 10),
  (3, 1, 8, 20),
  (4, 1, 9, 10),
  (5, 1, 10, 20),
  (6, 1, 11, 20),
  (7, 1, 12, 10),
  (8, 1, 13, 10),
  (9, 1, 14, 10),
  (10, 1, 15, 20),
  (11, 1, 16, 20),
  (12, 1, 17, 1000),
  (13, 2, 6, 100);

UPDATE public."PhieuNhap" SET trang_thai='hoan_thanh' WHERE id=1;

INSERT INTO public."GiaoDichKho" (id, mat_hang_id, loai_giao_dich, so_luong_bien_dong, chi_tiet_phieu_nhap_id, nhan_vien_id, posted_at) VALUES
  (1, 6, 'nhap_vat_tu', 10, 1, 2, '2026-10-22 09:00:00+07'),
  (2, 7, 'nhap_vat_tu', 10, 2, 2, '2026-10-22 09:00:00+07'),
  (3, 8, 'nhap_vat_tu', 20, 3, 2, '2026-10-22 09:00:00+07'),
  (4, 9, 'nhap_vat_tu', 10, 4, 2, '2026-10-22 09:00:00+07'),
  (5, 10, 'nhap_vat_tu', 20, 5, 2, '2026-10-22 09:00:00+07'),
  (6, 11, 'nhap_vat_tu', 20, 6, 2, '2026-10-22 09:00:00+07'),
  (7, 12, 'nhap_vat_tu', 10, 7, 2, '2026-10-22 09:00:00+07'),
  (8, 13, 'nhap_vat_tu', 10, 8, 2, '2026-10-22 09:00:00+07'),
  (9, 14, 'nhap_vat_tu', 10, 9, 2, '2026-10-22 09:00:00+07'),
  (10, 15, 'nhap_vat_tu', 20, 10, 2, '2026-10-22 09:00:00+07'),
  (11, 16, 'nhap_vat_tu', 20, 11, 2, '2026-10-22 09:00:00+07'),
  (12, 17, 'nhap_vat_tu', 1000, 12, 2, '2026-10-22 09:00:00+07');

-- Quản lý duyệt điều chỉnh nan hoa: 1000 -> 980 (-20), rồi 980 -> 985 (+5).

INSERT INTO public."PhieuDieuChinhKho" (id, ma_phieu, phieu_nhap_id, nhan_vien_id, ly_do, trang_thai, created_at) VALUES
  (1, 'DCK-202610-000001', 1, 2, 'Đối chiếu số nan hoa thực nhập với chứng từ nhà cung cấp.', 'nhap', '2026-10-22 09:10:00+07');

INSERT INTO public."ChiTietPhieuDieuChinhKho" (id, phieu_dieu_chinh_kho_id, mat_hang_id, giao_dich_goc_id, so_luong_hieu_luc_truoc, so_luong_dung, so_luong_bien_dong) VALUES
  (1, 1, 17, 12, 1000, 980, -20);

UPDATE public."PhieuDieuChinhKho" SET trang_thai='da_duyet',confirmed_at='2026-10-22 09:10:30+07' WHERE id=1;

INSERT INTO public."GiaoDichKho" (id, mat_hang_id, loai_giao_dich, so_luong_bien_dong, chi_tiet_phieu_dieu_chinh_id, nhan_vien_id, posted_at) VALUES
  (13, 17, 'dieu_chinh_ton_kho', -20, 1, 2, '2026-10-22 09:10:30+07');

INSERT INTO public."PhieuDieuChinhKho" (id, ma_phieu, phieu_nhap_id, nhan_vien_id, ly_do, trang_thai, created_at) VALUES
  (2, 'DCK-202610-000002', 1, 2, 'Đối chiếu số nan hoa thực nhập với chứng từ nhà cung cấp.', 'nhap', '2026-10-22 09:20:00+07');

INSERT INTO public."ChiTietPhieuDieuChinhKho" (id, phieu_dieu_chinh_kho_id, mat_hang_id, giao_dich_goc_id, so_luong_hieu_luc_truoc, so_luong_dung, so_luong_bien_dong) VALUES
  (2, 2, 17, 12, 980, 985, 5);

UPDATE public."PhieuDieuChinhKho" SET trang_thai='da_duyet',confirmed_at='2026-10-22 09:20:30+07' WHERE id=2;

INSERT INTO public."GiaoDichKho" (id, mat_hang_id, loai_giao_dich, so_luong_bien_dong, chi_tiet_phieu_dieu_chinh_id, nhan_vien_id, posted_at) VALUES
  (14, 17, 'dieu_chinh_ton_kho', 5, 2, 2, '2026-10-22 09:20:30+07');

-- Yêu cầu 10 xe có lệnh cha 10 xe và lệnh con 20 cụm. Không có tồn TP/BTP ban đầu.

INSERT INTO public."YeuCauSanXuat" (id, ma_yeu_cau_san_xuat, mat_hang_id, so_luong, nhan_vien_id, nhan_vien_duoc_giao_id, trang_thai, created_at) VALUES
  (1, 'YCSX-202610-000001', 1, 10, 2, 3, 'dang_thuc_hien', '2026-10-22 09:25:00+07'),
  (2, 'YCSX-202610-000002', 2, 100, 2, 3, 'cho_bo_sung_vat_tu', '2026-10-22 09:30:00+07');

INSERT INTO public."LenhSanXuat" (id, ma_lenh_san_xuat, yeu_cau_san_xuat_id, lenh_san_xuat_cha_id, mat_hang_id, bom_id, so_luong, nhan_vien_id, trang_thai, created_at, started_at) VALUES
  (1, 'LSX-202610-000001', 1, NULL, 1, 1, 10, 3, 'da_gui', '2026-10-22 09:26:00+07', NULL),
  (2, 'LSX-202610-000002', 1, 1, 5, 5, 20, 3, 'dang_thuc_hien', '2026-10-22 09:27:00+07', '2026-10-22 10:01:00+07'),
  (3, 'LSX-202610-000003', 2, NULL, 2, 2, 100, 3, 'da_gui', '2026-10-22 09:31:00+07', NULL),
  (4, 'LSX-202610-000004', 2, 3, 5, 5, 200, 3, 'da_gui', '2026-10-22 09:32:00+07', NULL);

INSERT INTO public."ChiTietLenhSanXuat" (id, lenh_san_xuat_id, mat_hang_id, so_luong_can) VALUES
  (1, 1, 6, 10),
  (2, 1, 7, 10),
  (3, 1, 5, 20),
  (4, 1, 8, 20),
  (5, 1, 9, 10),
  (6, 1, 10, 20),
  (7, 1, 11, 20),
  (8, 1, 12, 10),
  (9, 1, 13, 10),
  (10, 1, 14, 10),
  (11, 2, 15, 20),
  (12, 2, 16, 20),
  (13, 2, 17, 720),
  (14, 3, 6, 100),
  (15, 3, 7, 100),
  (16, 3, 5, 200),
  (17, 3, 8, 200),
  (18, 3, 9, 100),
  (19, 3, 10, 200),
  (20, 3, 11, 200),
  (21, 3, 12, 100),
  (22, 3, 13, 100),
  (23, 3, 14, 100),
  (24, 4, 15, 200),
  (25, 4, 16, 200),
  (26, 4, 17, 7200);

-- Xuất đủ vật tư cho lệnh 20 cụm: 20 vành, 20 moay-ơ, 720 nan hoa. Chỉ trừ một lần.

INSERT INTO public."PhieuXuat" (id, ma_phieu_xuat, nhan_vien_id, loai_phieu, lenh_san_xuat_id, trang_thai, created_at) VALUES
  (1, 'PX-202610-000001', 3, 'xuat_vat_tu', 2, 'nhap', '2026-10-22 09:40:00+07');

INSERT INTO public."ChiTietPhieuXuat" (id, phieu_xuat_id, mat_hang_id, so_luong) VALUES
  (1, 1, 15, 20),
  (2, 1, 16, 20),
  (3, 1, 17, 720);

UPDATE public."PhieuXuat" SET trang_thai='da_duyet' WHERE id=1;

INSERT INTO public."GiaoDichKho" (id, mat_hang_id, loai_giao_dich, so_luong_bien_dong, chi_tiet_phieu_xuat_id, nhan_vien_id, posted_at) VALUES
  (15, 15, 'xuat_vat_tu', -20, 1, 2, '2026-10-22 10:00:00+07'),
  (16, 16, 'xuat_vat_tu', -20, 2, 2, '2026-10-22 10:00:00+07'),
  (17, 17, 'xuat_vat_tu', -720, 3, 2, '2026-10-22 10:00:00+07');

INSERT INTO public."ChungTuHoanThanhSx" (id, ma_phieu, lenh_san_xuat_id, so_luong_hoan_thanh, nhan_vien_id, trang_thai, finish_time, created_at) VALUES
  (1, 'HTSX-202610-000001', 2, 20, 3, 'cho_duyet', '2026-10-22 10:25:00+07', '2026-10-22 10:30:00+07');

-- Hoàn thành còn chờ duyệt: không có giao dịch nhập sản xuất, tồn cụm bánh vẫn bằng 0.

-- Hai sự việc giảm nan hoa không hợp lệ; ticket thứ hai đóng thủ công, không có phiếu điều chỉnh mới.

INSERT INTO public."TicketLoiDieuChinh" (id, ma_ticket, phieu_nhap_id, nguoi_tao_id, mo_ta_loi, trang_thai, nguoi_xu_ly_id, ket_qua_xu_ly, created_at, closed_at) VALUES
  (1, 'TKDC-202610-000001', 1, 2, 'Đề nghị sửa lượng nhập nan hoa 985 về 200: giảm 785 nhưng tồn chỉ còn 265.', 'cho_xu_ly', NULL, NULL, '2026-10-22 11:00:00+07', NULL),
  (2, 'TKDC-202610-000002', 1, 2, 'Đề nghị sửa lượng nhập nan hoa 985 về 300: giảm 685 nhưng tồn chỉ còn 265.', 'da_xu_ly', 2, 'Đã đối chiếu lại, đề nghị 300 là nhầm. Giữ số lượng có hiệu lực 985; không cần lập điều chỉnh mới.', '2026-10-22 11:10:00+07', '2026-10-22 12:00:00+07');

INSERT INTO public."ChiTietTicketLoiDieuChinh" (id, ticket_id, chi_tiet_phieu_nhap_id, mat_hang_id, so_luong_hieu_luc_truoc, so_luong_de_nghi, so_luong_bien_dong, ton_kho_tai_thoi_diem) VALUES
  (1, 1, 12, 17, 985, 200, -785, 265),
  (2, 2, 12, 17, 985, 300, -685, 265);

-- Số dư demo dựng duy nhất từ các giao dịch thành công; không tính phiếu nháp/chờ duyệt/ticket.

-- Chỉ dùng phép tổng hợp này để dựng dữ liệu demo, trong cùng transaction seed.
-- Khi vận hành, backend phải cập nhật tồn theo từng nghiệp vụ với kiểm soát đồng thời.
UPDATE public."MatHang" AS m
SET so_luong_ton = totals.so_luong_ton,
    ton_kho_updated_at = '2026-10-22 12:00:00+07'
FROM (
  SELECT item.id, COALESCE(sum(g.so_luong_bien_dong),0)::int AS so_luong_ton
  FROM public."MatHang" item
  LEFT JOIN public."GiaoDichKho" g ON g.mat_hang_id=item.id
  GROUP BY item.id
) AS totals
WHERE m.id=totals.id;

INSERT INTO public."LichSuThaoTac" (id, nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, du_lieu_truoc, du_lieu_sau, ly_do, created_at) VALUES
  (1, 2, 'phieu_nhap', 1, 'hoan_tat', '{"trang_thai": "nhap"}', '{"trang_thai": "hoan_thanh", "so_dong": 12}', 'Quản lý tự xác nhận nhập.', '2026-10-22 09:00:00+07'),
  (2, 2, 'phieu_nhap', 2, 'tao', NULL, '{"trang_thai": "nhap"}', 'Phiếu nháp không ghi kho.', '2026-10-22 08:35:00+07'),
  (3, 2, 'phieu_dieu_chinh_kho', 1, 'duyet', '{"trang_thai": "nhap", "so_luong_hieu_luc": 1000}', '{"trang_thai": "da_duyet", "so_luong_dung": 980, "chenh_lech": -20}', 'Duyệt phiếu điều chỉnh.', '2026-10-22 09:10:30+07'),
  (4, 2, 'phieu_dieu_chinh_kho', 2, 'duyet', '{"trang_thai": "nhap", "so_luong_hieu_luc": 980}', '{"trang_thai": "da_duyet", "so_luong_dung": 985, "chenh_lech": 5}', 'Duyệt phiếu điều chỉnh.', '2026-10-22 09:20:30+07'),
  (5, 2, 'yeu_cau_san_xuat', 1, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nguoi_phu_trach": 3}', 'Giao nhân viên phụ trách.', '2026-10-22 09:25:00+07'),
  (6, 2, 'yeu_cau_san_xuat', 2, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nguoi_phu_trach": 3}', 'Giao nhân viên phụ trách.', '2026-10-22 09:30:00+07'),
  (7, 2, 'yeu_cau_san_xuat', 2, 'sua', '{"trang_thai": "da_gui"}', '{"trang_thai": "cho_bo_sung_vat_tu"}', 'Thiếu vật tư; giữ yêu cầu và lệnh hiện có.', '2026-10-22 09:33:00+07'),
  (8, 2, 'lenh_san_xuat', 1, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nhan_vien_id": 3}', 'Quản lý chốt BOM, nhu cầu và giao việc.', '2026-10-22 09:26:00+07'),
  (9, 2, 'lenh_san_xuat', 2, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nhan_vien_id": 3}', 'Quản lý chốt BOM, nhu cầu và giao việc.', '2026-10-22 09:27:00+07'),
  (10, 2, 'lenh_san_xuat', 3, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nhan_vien_id": 3}', 'Quản lý chốt BOM, nhu cầu và giao việc.', '2026-10-22 09:31:00+07'),
  (11, 2, 'lenh_san_xuat', 4, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "da_gui", "nhan_vien_id": 3}', 'Quản lý chốt BOM, nhu cầu và giao việc.', '2026-10-22 09:32:00+07'),
  (12, 2, 'phieu_xuat', 1, 'duyet', '{"trang_thai": "cho_duyet"}', '{"trang_thai": "da_duyet", "cap_vat_tu_cho_lenh": 2}', 'Đủ vật tư cho 20 cụm bánh.', '2026-10-22 10:00:00+07'),
  (13, 3, 'lenh_san_xuat', 2, 'bat_dau', '{"trang_thai": "da_gui"}', '{"trang_thai": "dang_thuc_hien"}', 'Vật tư đã cấp đủ.', '2026-10-22 10:01:00+07'),
  (14, 3, 'yeu_cau_san_xuat', 1, 'bat_dau', '{"trang_thai": "da_gui"}', '{"trang_thai": "dang_thuc_hien"}', 'Bắt đầu thực hiện lệnh con.', '2026-10-22 10:01:00+07'),
  (15, 3, 'chung_tu_hoan_thanh_san_xuat', 1, 'gui', '{"trang_thai": "nhap"}', '{"trang_thai": "cho_duyet", "so_luong": 20}', 'Chờ quản lý duyệt; chưa cộng kho.', '2026-10-22 10:30:00+07'),
  (16, 2, 'ticket_loi_dieu_chinh', 1, 'ghi_nhan_loi', NULL, '{"trang_thai": "cho_xu_ly", "so_luong_de_nghi": 200, "ton": 265}', 'Điều chỉnh không hợp lệ; kho không thay đổi.', '2026-10-22 11:00:00+07'),
  (17, 2, 'ticket_loi_dieu_chinh', 2, 'ghi_nhan_loi', NULL, '{"trang_thai": "cho_xu_ly", "so_luong_de_nghi": 300, "ton": 265}', 'Điều chỉnh không hợp lệ; kho không thay đổi.', '2026-10-22 11:10:00+07'),
  (18, 2, 'ticket_loi_dieu_chinh', 2, 'giai_quyet', '{"trang_thai": "cho_xu_ly"}', '{"trang_thai": "da_xu_ly", "nguoi_xu_ly_id": 2, "ket_qua_xu_ly": "Đề nghị 300 là nhầm; giữ lượng hiệu lực 985."}', 'Đóng thủ công, không cần phiếu điều chỉnh mới.', '2026-10-22 12:00:00+07');

-- Đồng bộ sequence sau khi dùng id cố định trong dữ liệu minh họa.
DO $$
DECLARE r record; seq text; maximum bigint;
BEGIN
  FOR r IN SELECT table_schema,table_name FROM information_schema.columns
    WHERE table_schema='public' AND table_name=ANY(ARRAY['NhanVien','VaiTro','MatHang','Bom','ChiTietBom','NhaCungCap','PhieuNhap','ChiTietPhieuNhap','PhieuXuat','ChiTietPhieuXuat','YeuCauSanXuat','LenhSanXuat','ChiTietLenhSanXuat','ChungTuHoanThanhSx','PhieuDieuChinhKho','ChiTietPhieuDieuChinhKho','TicketLoiDieuChinh','ChiTietTicketLoiDieuChinh','GiaoDichKho','LichSuThaoTac']) AND column_name='id' LOOP
    seq := pg_get_serial_sequence(format('%I.%I',r.table_schema,r.table_name),'id');
    IF seq IS NOT NULL THEN
      EXECUTE format('SELECT max(id) FROM %I.%I',r.table_schema,r.table_name) INTO maximum;
      PERFORM setval(seq,COALESCE(maximum,1),maximum IS NOT NULL);
    END IF;
  END LOOP;
END $$;

-- Tự kiểm tra các số liệu trọng yếu trước COMMIT.
DO $$
BEGIN
  IF (SELECT count(*) FROM public."Bom") <> 5 OR (SELECT count(*) FROM public."ChiTietBom") <> 43 THEN
    RAISE EXCEPTION 'Seed phải có 5 BOM, 43 dòng định mức'; END IF;
  IF (SELECT so_luong_ton FROM public."MatHang" WHERE id=17) <> 265 THEN
    RAISE EXCEPTION 'Tồn nan hoa phải là 1000 -20 +5 -720 = 265'; END IF;
  IF (SELECT so_luong_ton FROM public."MatHang" WHERE id=5) <> 0 THEN
    RAISE EXCEPTION 'Cụm bánh chưa được duyệt nhập kho'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."MatHang" t LEFT JOIN (
      SELECT mat_hang_id,sum(so_luong_bien_dong) qty FROM public."GiaoDichKho" GROUP BY mat_hang_id
    ) g ON g.mat_hang_id=t.id WHERE t.so_luong_ton<>COALESCE(g.qty,0)
  ) THEN RAISE EXCEPTION 'Số dư không khớp sổ kho'; END IF;
END $$;
COMMIT;
