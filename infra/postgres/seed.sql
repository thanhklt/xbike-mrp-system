-- xBike MRP data model v4.0 — dữ liệu demo cố định, không phải dữ liệu vận hành.
-- Tương thích init.sql v4.0. Giá, hồ sơ, liên hệ, địa chỉ đều là dữ liệu minh họa.
-- Yêu cầu: init.sql đã chạy thành công và các bảng chưa có dữ liệu.
-- Không chạy lại trên DB đã seed; không xóa/ghi đè dữ liệu có sẵn.
-- 4 tài khoản demo dùng mật khẩu DemoXbike2026! (bcrypt cost 12).
--
-- Tồn kho chỉ dựng qua chứng từ đã ghi nhận + GiaoDichKho (data model v4 mục 3.7):
--   PN-202611-000001 hoàn tất -> cộng linh kiện.
--   YCSX-202611-000001 (đáp ứng, 5 Mountain Pro): chạy trọn luồng; chứng từ hoàn thành bị từ chối 1 lần
--     rồi gửi lại; xuất thành phẩm -> Hoàn thành.
--   YCSX-202611-000002 (sản xuất cho kho, 3 Mountain Pro): xuất linh kiện, sản xuất, duyệt chứng từ hoàn thành
--     -> cộng 3 xe vào kho, không giữ -> Hoàn thành. Đây là nguồn tồn thành phẩm còn dùng được.
--   YCSX-202611-000003 (4 City Ride, công thức v2): Đang thực hiện, giữ linh kiện; phiếu xuất linh kiện
--     bị từ chối 1 lần, đã gửi lại, đang chờ duyệt.
--   YCSX-202611-000004 (2 City Ride): đã kiểm tra và giữ linh kiện, sau đó bị hủy -> trả hàng.
--   YCSX-202611-000005 (đáp ứng, 10 Mountain Pro): kịch bản BR-008 "Tồn 3 xe, cần 10" -> dùng 3 xe có sẵn,
--     sản xuất 7; Đang thực hiện, giữ 3 xe và linh kiện cho 7 xe.
--   YCSX-202611-000006 (10 Speed Sport): Chờ bổ sung linh kiện, thiếu 4 khung xe.
--   YCSX-202611-000007 (3 Kids Fun): Đã gửi, chưa kiểm tra.
--   YCSX-202611-000008 (2 Mountain Pro): Nháp.
--   PN-202611-000002: phiếu nháp bổ sung khung, chưa cộng tồn.
BEGIN;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL search_path = public, pg_catalog;

DO $$
DECLARE t record; used boolean;
BEGIN
  FOR t IN SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = ANY(ARRAY[
    'VaiTro','NhanVien','NhaCungCap','MatHang','Bom','ChiTietBom','PhieuNhap','ChiTietPhieuNhap',
    'YeuCauSanXuat','NhuCauLinhKien','GiuHang','ChungTuHoanThanhSx','PhieuXuat','ChiTietPhieuXuat',
    'GiaoDichKho','LichSuThaoTac','LuuLuongTruyCap']) LOOP
    EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I.%I)', t.schemaname, t.tablename) INTO used;
    IF used THEN RAISE EXCEPTION 'seed.sql yêu cầu DB trống; bảng % đã có dữ liệu', t.tablename; END IF;
  END LOOP;
END $$;

-- Hàm tạm cho seed: ghi một dòng sổ kho và cập nhật tồn như backend làm khi ghi nhận chứng từ.
CREATE FUNCTION pg_temp.ghi_so(p_mat_hang int, p_loai text, p_luong int, p_ctpn int, p_ctpx int,
                               p_htsx int, p_nhan_vien int, p_at timestamptz) RETURNS int
LANGUAGE plpgsql AS $$
DECLARE v_ton int;
BEGIN
  UPDATE public."MatHang" SET so_luong_ton = so_luong_ton + p_luong, ton_kho_updated_at = p_at
  WHERE id = p_mat_hang RETURNING so_luong_ton INTO v_ton;
  INSERT INTO public."GiaoDichKho" (mat_hang_id, loai_giao_dich, so_luong_bien_dong, so_luong_ton_sau,
    chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id, chung_tu_hoan_thanh_sx_id, nhan_vien_id, posted_at)
  VALUES (p_mat_hang, p_loai, p_luong, v_ton, p_ctpn, p_ctpx, p_htsx, p_nhan_vien, p_at);
  RETURN v_ton;
END $$;

-- Hàm tạm cho seed: duyệt phiếu xuất (chốt giá theo MatHang.don_gia) rồi ghi sổ từng dòng.
CREATE FUNCTION pg_temp.duyet_phieu_xuat(p_id int, p_nguoi int, p_at timestamptz, p_phien_ban int) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_tong bigint; r record; v_loai text;
BEGIN
  UPDATE public."ChiTietPhieuXuat" c SET don_gia_thuc = m.don_gia, tong_gia = c.so_luong::bigint * m.don_gia
  FROM public."MatHang" m WHERE m.id = c.mat_hang_id AND c.phieu_xuat_id = p_id;
  SELECT sum(tong_gia) INTO v_tong FROM public."ChiTietPhieuXuat" WHERE phieu_xuat_id = p_id;
  UPDATE public."PhieuXuat" SET trang_thai = 'da_duyet', tong_tien = v_tong, nguoi_xu_ly_id = p_nguoi,
    xu_ly_at = p_at, updated_at = p_at, phien_ban = p_phien_ban
  WHERE id = p_id RETURNING loai_phieu INTO v_loai;
  FOR r IN SELECT * FROM public."ChiTietPhieuXuat" WHERE phieu_xuat_id = p_id ORDER BY id LOOP
    PERFORM pg_temp.ghi_so(r.mat_hang_id, v_loai, -r.so_luong, NULL, r.id, NULL, p_nguoi, p_at);
  END LOOP;
  RETURN v_tong;
END $$;

-- ---------------------------------------------------------------------
-- identity_access
-- ---------------------------------------------------------------------

INSERT INTO public."VaiTro" (id, ma_vai_tro, ten_vai_tro, mo_ta) VALUES
  (1, 'quan_tri_vien', 'Quản trị viên', 'Quản trị tài khoản: thêm, khóa, mở khóa, đổi vai trò, đổi mật khẩu; tra cứu mặt hàng và nhà cung cấp chỉ đọc; xem lịch sử thao tác. Không làm nghiệp vụ kho.'),
  (2, 'quan_ly', 'Quản lý kho', 'Quản lý mặt hàng, nhà cung cấp, công thức; nhập kho; lập, gửi, hủy yêu cầu sản xuất; duyệt phiếu xuất và chứng từ hoàn thành; xem báo cáo và lịch sử thao tác.'),
  (3, 'nhan_vien', 'Nhân viên', 'Xử lý yêu cầu sản xuất được giao: kiểm tra và giữ hàng, lập phiếu xuất linh kiện, bắt đầu sản xuất, lập chứng từ hoàn thành, lập phiếu xuất thành phẩm.');

INSERT INTO public."NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien, ho_ten, ngay_sinh, so_dien_thoai, email, ngay_vao_lam, he_so_luong, trang_thai, phien_ban_dang_nhap, created_at) VALUES
  (1, 1, 'quan_tri', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000001', 'Nguyễn Minh An', '1990-03-15', '0900000001', 'minh.an@example.com', '2026-10-01', 3.50, 'hoat_dong', 0, '2026-11-01 07:00:00+07'),
  (2, 2, 'quan_ly_kho', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000002', 'Trần Thanh Bình', '1993-07-20', '0900000002', 'thanh.binh@example.com', '2026-10-01', 2.80, 'hoat_dong', 0, '2026-11-01 08:00:00+07'),
  (3, 3, 'nhan_vien_sx', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000003', 'Lê Hoàng Nam', '1998-11-05', '0900000003', 'hoang.nam@example.com', '2026-10-01', 2.00, 'hoat_dong', 0, '2026-11-01 08:01:00+07'),
  (4, 3, 'nhan_vien_lr', '$2b$12$b6WSrWrAkDHtQoaOGzhFdegb5SbNwkobaHO6IqEfNnaO.m58.hv5m', 'NV-000004', 'Phạm Thu Hà', '1999-04-12', '0900000004', 'thu.ha@example.com', '2026-10-15', 2.00, 'hoat_dong', 0, '2026-11-01 08:02:00+07');

-- ---------------------------------------------------------------------
-- catalog — mã MH-/NCC- do trigger cấp từ id, seed không truyền mã.
-- ---------------------------------------------------------------------

INSERT INTO public."NhaCungCap" (id, ten_ncc, so_dien_thoai, dia_chi, phuong, tinh, created_at) VALUES
  (1, 'Công ty TNHH Linh kiện Xe đạp Minh Phát', '0280000011', '123 Đường Mẫu (địa chỉ minh họa)', 'Phường Minh Họa', 'Thành phố Hồ Chí Minh', '2026-11-01 09:10:00+07'),
  (2, 'Công ty CP Phụ tùng Thành Công', '0240000022', '45 Đường Minh Họa (địa chỉ minh họa)', 'Phường Mẫu', 'Thành phố Hà Nội', '2026-11-01 09:12:00+07');

-- don_gia: giá danh mục (VND), dùng làm giá xuất lúc duyệt phiếu xuất.
INSERT INTO public."MatHang" (id, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, mau_sac, mo_ta, don_gia, is_active, created_at) VALUES
  (1, 'Xe Mountain Pro', 'XE-MOUNTAIN-PRO', 'thanh_pham', 'chiec', 'den', 'Xe đạp địa hình Mountain Pro.', 12500000, true, '2026-11-01 09:30:00+07'),
  (2, 'Xe City Ride', 'XE-CITY-RIDE', 'thanh_pham', 'chiec', 'xanh_duong', 'Xe đạp đô thị City Ride.', 8900000, true, '2026-11-01 09:30:00+07'),
  (3, 'Xe Speed Sport', 'XE-SPEED-SPORT', 'thanh_pham', 'chiec', 'do', 'Xe đạp thể thao Speed Sport.', 15800000, true, '2026-11-01 09:30:00+07'),
  (4, 'Xe Kids Fun', 'XE-KIDS-FUN', 'thanh_pham', 'chiec', 'vang', 'Xe đạp trẻ em Kids Fun, không có phuộc.', 3200000, true, '2026-11-01 09:30:00+07'),
  (5, 'Khung xe', 'KHUNG-XE', 'linh_kien', 'chiec', 'den', 'Khung xe dùng cho mọi mẫu xe.', 1800000, true, '2026-11-01 09:30:00+07'),
  (6, 'Phuộc xe', 'PHUOC-XE', 'linh_kien', 'chiec', 'den', 'Phuộc trước.', 950000, true, '2026-11-01 09:30:00+07'),
  (7, 'Cụm bánh xe', 'CUM-BANH-XE', 'linh_kien', 'chiec', 'bac', 'Cụm bánh xe mua nguyên cụm từ nhà cung cấp, nhập kho như linh kiện.', 650000, true, '2026-11-01 09:30:00+07'),
  (8, 'Lốp xe', 'LOP-XE', 'linh_kien', 'chiec', 'den', 'Lốp cao su, mỗi xe dùng hai chiếc.', 180000, true, '2026-11-01 09:30:00+07'),
  (9, 'Xích xe', 'XICH-XE', 'linh_kien', 'chiec', 'bac', 'Xích truyền động.', 220000, true, '2026-11-01 09:30:00+07'),
  (10, 'Bàn đạp', 'BAN-DAP', 'linh_kien', 'chiec', 'den', 'Bàn đạp tính theo chiếc, mỗi xe dùng hai chiếc.', 120000, true, '2026-11-01 09:30:00+07'),
  (11, 'Dây phanh', 'DAY-PHANH', 'linh_kien', 'chiec', 'den', 'Dây phanh trước và sau, mỗi xe dùng hai chiếc.', 45000, true, '2026-11-01 09:30:00+07'),
  (12, 'Yên xe', 'YEN-XE', 'linh_kien', 'chiec', 'den', 'Yên xe.', 250000, true, '2026-11-01 09:30:00+07'),
  (13, 'Đĩa xích', 'DIA-XICH', 'linh_kien', 'chiec', 'bac', 'Đĩa xích của hệ truyền động.', 320000, true, '2026-11-01 09:30:00+07'),
  (14, 'Bộ ốc vít', 'BO-OC-VIT', 'linh_kien', 'bo', 'bac', 'Bộ ốc vít phục vụ lắp ráp.', 60000, true, '2026-11-01 09:30:00+07');

-- ---------------------------------------------------------------------
-- bom — công thức một cấp; City Ride có phiên bản 2 (thêm 1 bộ ốc vít) thay phiên bản 1.
-- ---------------------------------------------------------------------

INSERT INTO public."Bom" (id, mat_hang_id, version, is_active, created_at, kich_hoat_gan_nhat_at) VALUES
  (1, 1, 1, true,  '2026-11-01 09:30:00+07', '2026-11-01 09:30:00+07'),
  (2, 2, 1, false, '2026-11-01 09:30:00+07', '2026-11-01 09:30:00+07'),
  (3, 2, 2, true,  '2026-11-01 10:00:00+07', '2026-11-01 10:00:00+07'),
  (4, 3, 1, true,  '2026-11-01 09:30:00+07', '2026-11-01 09:30:00+07'),
  (5, 4, 1, true,  '2026-11-01 09:30:00+07', '2026-11-01 09:30:00+07');

-- Định mức cho 1 xe. Kids Fun không có phuộc; City Ride v2 dùng 2 bộ ốc vít.
INSERT INTO public."ChiTietBom" (bom_id, mat_hang_id, so_luong)
SELECT b.bom_id, d.mat_hang_id, CASE WHEN b.bom_id = 3 AND d.mat_hang_id = 14 THEN 2 ELSE d.so_luong END
FROM (VALUES (1), (2), (3), (4), (5)) AS b(bom_id)
CROSS JOIN (VALUES (5, 1), (6, 1), (7, 2), (8, 2), (9, 1), (10, 2), (11, 2), (12, 1), (13, 1), (14, 1)) AS d(mat_hang_id, so_luong)
WHERE NOT (b.bom_id = 5 AND d.mat_hang_id = 6)
ORDER BY b.bom_id, d.mat_hang_id;

-- ---------------------------------------------------------------------
-- goods_receipt
-- ---------------------------------------------------------------------

INSERT INTO public."PhieuNhap" (id, ma_phieu_nhap, nhan_vien_id, ncc_id, ngay_nhap, ghi_chu, trang_thai, created_at, updated_at, phien_ban) VALUES
  (1, 'PN-202611-000001', 2, 1, '2026-11-02', 'Lô linh kiện đầu tháng 11.', 'nhap', '2026-11-02 08:30:00+07', '2026-11-02 08:30:00+07', 1),
  (2, 'PN-202611-000002', 2, 2, '2026-11-13', 'Bổ sung khung xe cho YCSX-202611-000006; còn nháp, chưa cộng tồn.', 'nhap', '2026-11-12 09:00:00+07', '2026-11-12 09:00:00+07', 1);

INSERT INTO public."ChiTietPhieuNhap" (phieu_nhap_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
SELECT phieu_nhap_id, mat_hang_id, so_luong, don_gia_thuc, so_luong::bigint * don_gia_thuc
FROM (VALUES
  (1, 5, 25, 1750000), (1, 6, 30, 920000), (1, 7, 60, 630000), (1, 8, 60, 170000), (1, 9, 30, 210000),
  (1, 10, 60, 115000), (1, 11, 60, 42000), (1, 12, 30, 240000), (1, 13, 30, 310000), (1, 14, 40, 58000),
  (2, 5, 10, 1760000)
) AS v(phieu_nhap_id, mat_hang_id, so_luong, don_gia_thuc)
ORDER BY phieu_nhap_id, mat_hang_id;

UPDATE public."PhieuNhap" p
SET tong_tien = (SELECT sum(c.tong_gia) FROM public."ChiTietPhieuNhap" c WHERE c.phieu_nhap_id = p.id);

-- Hoàn tất PN-202611-000001 rồi ghi sổ từng dòng.
UPDATE public."PhieuNhap"
SET trang_thai = 'hoan_thanh', hoan_thanh_at = '2026-11-02 09:00:00+07', nguoi_hoan_thanh_id = 2,
    updated_at = '2026-11-02 09:00:00+07', phien_ban = 2
WHERE id = 1;

SELECT count(pg_temp.ghi_so(c.mat_hang_id, 'nhap_linh_kien', c.so_luong, c.id, NULL, NULL, 2, '2026-11-02 09:00:00+07'))
FROM (SELECT * FROM public."ChiTietPhieuNhap" WHERE phieu_nhap_id = 1 ORDER BY id) c;

-- ---------------------------------------------------------------------
-- production — yêu cầu sản xuất ở trạng thái cuối, kèm nhu cầu đã chốt.
-- ---------------------------------------------------------------------

INSERT INTO public."YeuCauSanXuat" (id, ma_yeu_cau_san_xuat, loai_yeu_cau, mat_hang_id, so_luong, han_hoan_thanh, nhan_vien_id, nhan_vien_duoc_giao_id, bom_id, trang_thai,
  so_luong_dung_thanh_pham, so_luong_can_san_xuat, created_at, updated_at, gui_at, kiem_tra_lan_dau_at, started_at, completed_at, huy_at, nguoi_huy_id, ly_do_huy, phien_ban) VALUES
  (1, 'YCSX-202611-000001', 'dap_ung', 1, 5, '2026-11-10', 2, 3, 1, 'hoan_thanh', 0, 5,
   '2026-11-03 08:00:00+07', '2026-11-06 15:00:00+07', '2026-11-03 08:10:00+07', '2026-11-03 09:00:00+07', '2026-11-04 10:00:00+07', '2026-11-06 15:00:00+07', NULL, NULL, NULL, 5),
  (2, 'YCSX-202611-000002', 'cho_kho', 1, 3, '2026-11-08', 2, 4, 1, 'hoan_thanh', 0, 3,
   '2026-11-04 11:00:00+07', '2026-11-05 17:00:00+07', '2026-11-04 11:05:00+07', '2026-11-04 13:00:00+07', '2026-11-05 08:00:00+07', '2026-11-05 17:00:00+07', NULL, NULL, NULL, 5),
  (3, 'YCSX-202611-000003', 'dap_ung', 2, 4, '2026-11-15', 2, 3, 3, 'dang_thuc_hien', 0, 4,
   '2026-11-07 08:00:00+07', '2026-11-07 09:00:00+07', '2026-11-07 08:10:00+07', '2026-11-07 09:00:00+07', NULL, NULL, NULL, NULL, NULL, 3),
  (4, 'YCSX-202611-000004', 'dap_ung', 2, 2, '2026-11-12', 2, 4, 3, 'da_huy', 0, 2,
   '2026-11-07 08:15:00+07', '2026-11-10 08:30:00+07', '2026-11-07 08:20:00+07', '2026-11-08 09:00:00+07', NULL, NULL, '2026-11-10 08:30:00+07', 2, 'Khách hủy đơn, không còn nhu cầu.', 4),
  (5, 'YCSX-202611-000005', 'dap_ung', 1, 10, '2026-11-20', 2, 3, 1, 'dang_thuc_hien', 3, 7,
   '2026-11-09 09:00:00+07', '2026-11-09 10:00:00+07', '2026-11-09 09:10:00+07', '2026-11-09 10:00:00+07', NULL, NULL, NULL, NULL, NULL, 3),
  (6, 'YCSX-202611-000006', 'dap_ung', 3, 10, '2026-11-22', 2, 4, 4, 'cho_bo_sung_linh_kien', 0, 10,
   '2026-11-10 08:50:00+07', '2026-11-10 10:00:00+07', '2026-11-10 09:00:00+07', '2026-11-10 10:00:00+07', NULL, NULL, NULL, NULL, NULL, 3),
  (7, 'YCSX-202611-000007', 'dap_ung', 4, 3, '2026-11-25', 2, 4, 5, 'da_gui', NULL, NULL,
   '2026-11-11 07:50:00+07', '2026-11-11 08:00:00+07', '2026-11-11 08:00:00+07', NULL, NULL, NULL, NULL, NULL, NULL, 2),
  (8, 'YCSX-202611-000008', 'dap_ung', 1, 2, '2026-11-30', 2, 3, NULL, 'nhap', NULL, NULL,
   '2026-11-12 08:00:00+07', '2026-11-12 08:00:00+07', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 1);

-- Nhu cầu linh kiện = định mức của công thức đã chốt × số cần sản xuất.
INSERT INTO public."NhuCauLinhKien" (yeu_cau_san_xuat_id, mat_hang_id, so_luong_can)
SELECT y.id, c.mat_hang_id, c.so_luong * y.so_luong_can_san_xuat
FROM public."YeuCauSanXuat" y JOIN public."ChiTietBom" c ON c.bom_id = y.bom_id
WHERE y.so_luong_can_san_xuat > 0
ORDER BY y.id, c.mat_hang_id;

-- ---------------------------------------------------------------------
-- Phiếu xuất và chứng từ hoàn thành, theo đúng thứ tự thời gian ghi sổ.
-- ---------------------------------------------------------------------

INSERT INTO public."PhieuXuat" (id, ma_phieu_xuat, nhan_vien_id, loai_phieu, yeu_cau_san_xuat_id, trang_thai, created_at, updated_at, gui_at, phien_ban) VALUES
  (1, 'PX-202611-000001', 3, 'xuat_linh_kien', 1, 'cho_duyet', '2026-11-04 08:00:00+07', '2026-11-04 08:05:00+07', '2026-11-04 08:05:00+07', 2),
  (2, 'PX-202611-000002', 4, 'xuat_linh_kien', 2, 'cho_duyet', '2026-11-04 14:00:00+07', '2026-11-04 14:05:00+07', '2026-11-04 14:05:00+07', 2),
  (3, 'PX-202611-000003', 3, 'xuat_thanh_pham', 1, 'cho_duyet', '2026-11-06 14:30:00+07', '2026-11-06 14:35:00+07', '2026-11-06 14:35:00+07', 2),
  -- Bị từ chối 08/11 14:00, gửi lại 09/11 08:00, đang chờ duyệt (chưa ghi giá).
  (4, 'PX-202611-000004', 3, 'xuat_linh_kien', 3, 'cho_duyet', '2026-11-08 10:00:00+07', '2026-11-09 08:00:00+07', '2026-11-09 08:00:00+07', 4);

-- Dòng phiếu xuất linh kiện lấy đúng nhu cầu đã chốt; phiếu thành phẩm lấy đúng số lượng yêu cầu.
INSERT INTO public."ChiTietPhieuXuat" (phieu_xuat_id, mat_hang_id, so_luong)
SELECT p.id, n.mat_hang_id, n.so_luong_can
FROM public."PhieuXuat" p JOIN public."NhuCauLinhKien" n ON n.yeu_cau_san_xuat_id = p.yeu_cau_san_xuat_id
WHERE p.loai_phieu = 'xuat_linh_kien' ORDER BY p.id, n.mat_hang_id;
INSERT INTO public."ChiTietPhieuXuat" (phieu_xuat_id, mat_hang_id, so_luong)
SELECT p.id, y.mat_hang_id, y.so_luong
FROM public."PhieuXuat" p JOIN public."YeuCauSanXuat" y ON y.id = p.yeu_cau_san_xuat_id
WHERE p.loai_phieu = 'xuat_thanh_pham' ORDER BY p.id;

-- 04/11 09:30: duyệt PX 1 (linh kiện 5 Mountain Pro cho YCSX 1).
SELECT pg_temp.duyet_phieu_xuat(1, 2, '2026-11-04 09:30:00+07', 3);
-- 04/11 15:00: duyệt PX 2 (linh kiện 3 Mountain Pro cho YCSX 2, sản xuất cho kho).
SELECT pg_temp.duyet_phieu_xuat(2, 2, '2026-11-04 15:00:00+07', 3);

-- 05/11 17:00: duyệt HTSX 2 của YCSX 2 (cho kho) -> +3 Mountain Pro, không giữ, yêu cầu Hoàn thành.
-- 06/11 14:00: duyệt HTSX 1 của YCSX 1 (đáp ứng; bị từ chối 05/11 11:00, gửi lại 16:00) -> +5, giữ cho YCSX 1.
INSERT INTO public."ChungTuHoanThanhSx" (id, ma_phieu, yeu_cau_san_xuat_id, so_luong_hoan_thanh, nhan_vien_id, trang_thai, finish_time, created_at, updated_at, nguoi_xu_ly_id, xu_ly_at, phien_ban) VALUES
  (1, 'HTSX-202611-000001', 1, 5, 3, 'da_duyet', '2026-11-05 16:00:00+07', '2026-11-05 10:00:00+07', '2026-11-06 14:00:00+07', 2, '2026-11-06 14:00:00+07', 5),
  (2, 'HTSX-202611-000002', 2, 3, 4, 'da_duyet', '2026-11-05 15:00:00+07', '2026-11-05 14:55:00+07', '2026-11-05 17:00:00+07', 2, '2026-11-05 17:00:00+07', 3);
SELECT pg_temp.ghi_so(1, 'nhap_san_pham_san_xuat', 3, NULL, NULL, 2, 2, '2026-11-05 17:00:00+07');
SELECT pg_temp.ghi_so(1, 'nhap_san_pham_san_xuat', 5, NULL, NULL, 1, 2, '2026-11-06 14:00:00+07');

-- 06/11 15:00: duyệt PX 3 (5 Mountain Pro của YCSX 1) -> YCSX 1 Hoàn thành; còn 3 xe từ YCSX 2.
SELECT pg_temp.duyet_phieu_xuat(3, 2, '2026-11-06 15:00:00+07', 3);

-- ---------------------------------------------------------------------
-- Giữ hàng
-- ---------------------------------------------------------------------

-- Linh kiện giữ khi kiểm tra, kết thúc khi duyệt phiếu xuất linh kiện (YCSX 1, 2).
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, phieu_xuat_id, created_at, ket_thuc_at)
SELECT n.yeu_cau_san_xuat_id, n.mat_hang_id, 'linh_kien', n.so_luong_can, 'da_xuat', p.id, y.kiem_tra_lan_dau_at, p.xu_ly_at
FROM public."NhuCauLinhKien" n
JOIN public."YeuCauSanXuat" y ON y.id = n.yeu_cau_san_xuat_id
JOIN public."PhieuXuat" p ON p.yeu_cau_san_xuat_id = y.id AND p.loai_phieu = 'xuat_linh_kien' AND p.trang_thai = 'da_duyet'
ORDER BY n.yeu_cau_san_xuat_id, n.mat_hang_id;
-- YCSX 1: 5 xe vừa làm giữ khi duyệt HTSX 1, kết thúc khi duyệt PX 3. YCSX 2 (cho kho) không giữ thành phẩm.
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, chung_tu_hoan_thanh_sx_id, phieu_xuat_id, created_at, ket_thuc_at) VALUES
  (1, 1, 'thanh_pham_san_xuat', 5, 'da_xuat', 1, 3, '2026-11-06 14:00:00+07', '2026-11-06 15:00:00+07');
-- YCSX 3: đủ linh kiện, đang giữ (phiếu xuất linh kiện đang chờ duyệt).
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, created_at)
SELECT 3, n.mat_hang_id, 'linh_kien', n.so_luong_can, 'dang_giu', '2026-11-07 09:00:00+07'
FROM public."NhuCauLinhKien" n WHERE n.yeu_cau_san_xuat_id = 3 ORDER BY n.mat_hang_id;
-- YCSX 4: đủ linh kiện, đã giữ, sau đó bị hủy -> trả lại.
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, created_at, ket_thuc_at)
SELECT 4, n.mat_hang_id, 'linh_kien', n.so_luong_can, 'da_tra', '2026-11-08 09:00:00+07', '2026-11-10 08:30:00+07'
FROM public."NhuCauLinhKien" n WHERE n.yeu_cau_san_xuat_id = 4 ORDER BY n.mat_hang_id;
-- YCSX 5: dùng 3 Mountain Pro có sẵn (từ YCSX 2) và giữ đủ linh kiện cho 7 xe.
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, created_at) VALUES
  (5, 1, 'thanh_pham_co_san', 3, 'dang_giu', '2026-11-09 10:00:00+07');
INSERT INTO public."GiuHang" (yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, trang_thai, created_at)
SELECT 5, n.mat_hang_id, 'linh_kien', n.so_luong_can, 'dang_giu', '2026-11-09 10:00:00+07'
FROM public."NhuCauLinhKien" n WHERE n.yeu_cau_san_xuat_id = 5 ORDER BY n.mat_hang_id;
-- YCSX 6: thiếu khung nên không giữ linh kiện nào; không có thành phẩm Speed Sport có sẵn.

-- Đồng bộ phần đang giữ trên MatHang từ GiuHang (backend làm việc này trong từng nghiệp vụ).
UPDATE public."MatHang" m
SET so_luong_dang_giu = COALESCE((SELECT sum(g.so_luong) FROM public."GiuHang" g
                                  WHERE g.mat_hang_id = m.id AND g.trang_thai = 'dang_giu'), 0);

-- ---------------------------------------------------------------------
-- audit
-- ---------------------------------------------------------------------

-- Tạo tài khoản; Quản trị viên đầu tiên tạo sẵn khi cài đặt nên không có bản ghi.
INSERT INTO public."LichSuThaoTac" (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, trang_thai_truoc, trang_thai_sau, du_lieu_truoc, du_lieu_sau, ly_do, created_at)
SELECT 1, 'nhan_vien', n.id, 'tao', NULL, 'hoat_dong', NULL,
       jsonb_build_object('ten_dang_nhap', n.ten_dang_nhap, 'ma_nhan_vien', n.ma_nhan_vien, 'vai_tro', v.ma_vai_tro), NULL, n.created_at
FROM public."NhanVien" n JOIN public."VaiTro" v ON v.id = n.vai_tro_id WHERE n.id > 1 ORDER BY n.id;

INSERT INTO public."LichSuThaoTac" (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, trang_thai_truoc, trang_thai_sau, du_lieu_truoc, du_lieu_sau, ly_do, created_at) VALUES
  (2, 'nhan_vien', 2, 'dang_nhap', NULL, NULL, NULL, NULL, NULL, '2026-11-01 09:00:00+07'),
  (2, 'nha_cung_cap', 1, 'tao', NULL, NULL, NULL, '{"ma_ncc": "NCC-000001", "ten_ncc": "Công ty TNHH Linh kiện Xe đạp Minh Phát"}', NULL, '2026-11-01 09:10:00+07'),
  (2, 'nha_cung_cap', 2, 'tao', NULL, NULL, NULL, '{"ma_ncc": "NCC-000002", "ten_ncc": "Công ty CP Phụ tùng Thành Công", "so_dien_thoai": "0240000021"}', NULL, '2026-11-01 09:12:00+07');

INSERT INTO public."LichSuThaoTac" (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, trang_thai_truoc, trang_thai_sau, du_lieu_truoc, du_lieu_sau, ly_do, created_at)
SELECT 2, 'mat_hang', m.id, 'tao', NULL, CASE WHEN m.loai_mat_hang = 'thanh_pham' THEN 'dang_dung' END, NULL,
       jsonb_build_object('ma_mat_hang', m.ma_mat_hang, 'ten_mat_hang', m.ten_mat_hang, 'loai_mat_hang', m.loai_mat_hang,
                          'don_vi_tinh', m.don_vi_tinh, 'don_gia', m.don_gia), NULL, m.created_at
FROM public."MatHang" m ORDER BY m.id;

INSERT INTO public."LichSuThaoTac" (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, trang_thai_truoc, trang_thai_sau, du_lieu_truoc, du_lieu_sau, ly_do, created_at)
SELECT 2, 'cong_thuc', b.id, 'tao', NULL, 'dang_dung', NULL,
       jsonb_build_object('mat_hang_id', b.mat_hang_id, 'version', b.version,
                          'dinh_muc', (SELECT jsonb_agg(jsonb_build_object('mat_hang_id', c.mat_hang_id, 'so_luong', c.so_luong) ORDER BY c.mat_hang_id)
                                       FROM public."ChiTietBom" c WHERE c.bom_id = b.id)), NULL, b.created_at
FROM public."Bom" b WHERE b.version = 1 ORDER BY b.id;

INSERT INTO public."LichSuThaoTac" (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, trang_thai_truoc, trang_thai_sau, du_lieu_truoc, du_lieu_sau, ly_do, created_at) VALUES
  (2, 'cong_thuc', 3, 'tao_phien_ban', NULL, 'dang_dung', '{"phien_ban_dang_dung_id": 2, "version": 1}', '{"mat_hang_id": 2, "version": 2, "thay_doi": "Bộ ốc vít 1 -> 2"}', 'Bổ sung ốc vít cho giá chở hàng.', '2026-11-01 10:00:00+07'),
  (2, 'nha_cung_cap', 2, 'sua', NULL, NULL, '{"so_dien_thoai": "0240000021"}', '{"so_dien_thoai": "0240000022"}', NULL, '2026-11-01 10:30:00+07'),
  (2, 'phieu_nhap', 1, 'tao', NULL, 'nhap', NULL, '{"so_dong": 10}', NULL, '2026-11-02 08:30:00+07'),
  (2, 'phieu_nhap', 1, 'hoan_tat', 'nhap', 'hoan_thanh', NULL, '{"so_dong": 10}', NULL, '2026-11-02 09:00:00+07'),
  -- YCSX 1 (đáp ứng)
  (2, 'yeu_cau_san_xuat', 1, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 1, "so_luong": 5, "nhan_vien_duoc_giao_id": 3}', NULL, '2026-11-03 08:00:00+07'),
  (2, 'yeu_cau_san_xuat', 1, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 1}', NULL, '2026-11-03 08:10:00+07'),
  (3, 'nhan_vien', 3, 'dang_nhap', NULL, NULL, NULL, NULL, NULL, '2026-11-03 08:55:00+07'),
  (3, 'yeu_cau_san_xuat', 1, 'kiem_tra', 'da_gui', 'dang_thuc_hien', NULL, '{"so_luong_dung_thanh_pham": 0, "so_luong_can_san_xuat": 5, "giu_linh_kien": true}', NULL, '2026-11-03 09:00:00+07'),
  (3, 'phieu_xuat', 1, 'tao', NULL, 'nhap', NULL, '{"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": 1}', NULL, '2026-11-04 08:00:00+07'),
  (3, 'phieu_xuat', 1, 'gui', 'nhap', 'cho_duyet', NULL, NULL, NULL, '2026-11-04 08:05:00+07'),
  (2, 'phieu_xuat', 1, 'duyet', 'cho_duyet', 'da_duyet', NULL, '{"tong_tien": 27950000}', NULL, '2026-11-04 09:30:00+07'),
  (3, 'yeu_cau_san_xuat', 1, 'bat_dau', 'dang_thuc_hien', 'dang_thuc_hien', NULL, '{"started_at": "2026-11-04T10:00:00+07:00"}', NULL, '2026-11-04 10:00:00+07'),
  -- YCSX 2 (sản xuất cho kho)
  (2, 'yeu_cau_san_xuat', 2, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "cho_kho", "mat_hang_id": 1, "so_luong": 3, "nhan_vien_duoc_giao_id": 4}', NULL, '2026-11-04 11:00:00+07'),
  (2, 'yeu_cau_san_xuat', 2, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 1}', NULL, '2026-11-04 11:05:00+07'),
  (4, 'nhan_vien', 4, 'dang_nhap', NULL, NULL, NULL, NULL, NULL, '2026-11-04 12:55:00+07'),
  (4, 'yeu_cau_san_xuat', 2, 'kiem_tra', 'da_gui', 'dang_thuc_hien', NULL, '{"so_luong_dung_thanh_pham": 0, "so_luong_can_san_xuat": 3, "giu_linh_kien": true}', NULL, '2026-11-04 13:00:00+07'),
  (4, 'phieu_xuat', 2, 'tao', NULL, 'nhap', NULL, '{"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": 2}', NULL, '2026-11-04 14:00:00+07'),
  (4, 'phieu_xuat', 2, 'gui', 'nhap', 'cho_duyet', NULL, NULL, NULL, '2026-11-04 14:05:00+07'),
  (2, 'phieu_xuat', 2, 'duyet', 'cho_duyet', 'da_duyet', NULL, '{"tong_tien": 16770000}', NULL, '2026-11-04 15:00:00+07'),
  (4, 'yeu_cau_san_xuat', 2, 'bat_dau', 'dang_thuc_hien', 'dang_thuc_hien', NULL, '{"started_at": "2026-11-05T08:00:00+07:00"}', NULL, '2026-11-05 08:00:00+07'),
  -- Chứng từ hoàn thành
  (3, 'chung_tu_hoan_thanh_san_xuat', 1, 'tao', NULL, 'nhap', NULL, '{"so_luong_hoan_thanh": 5}', NULL, '2026-11-05 10:00:00+07'),
  (3, 'chung_tu_hoan_thanh_san_xuat', 1, 'gui', 'nhap', 'cho_duyet', NULL, '{"finish_time": "2026-11-05T10:05:00+07:00"}', NULL, '2026-11-05 10:05:00+07'),
  (2, 'chung_tu_hoan_thanh_san_xuat', 1, 'tu_choi', 'cho_duyet', 'tu_choi', NULL, NULL, 'Chưa có biên bản kiểm tra chất lượng của tổ lắp ráp.', '2026-11-05 11:00:00+07'),
  (4, 'chung_tu_hoan_thanh_san_xuat', 2, 'tao', NULL, 'nhap', NULL, '{"so_luong_hoan_thanh": 3}', NULL, '2026-11-05 14:55:00+07'),
  (4, 'chung_tu_hoan_thanh_san_xuat', 2, 'gui', 'nhap', 'cho_duyet', NULL, '{"finish_time": "2026-11-05T15:00:00+07:00"}', NULL, '2026-11-05 15:00:00+07'),
  (3, 'chung_tu_hoan_thanh_san_xuat', 1, 'gui_lai', 'tu_choi', 'cho_duyet', NULL, '{"finish_time": "2026-11-05T16:00:00+07:00"}', NULL, '2026-11-05 16:00:00+07'),
  (2, 'chung_tu_hoan_thanh_san_xuat', 2, 'duyet', 'cho_duyet', 'da_duyet', NULL, '{"nhap_kho": 3, "giu_cho_yeu_cau": 0, "yeu_cau_san_xuat_trang_thai": "hoan_thanh"}', NULL, '2026-11-05 17:00:00+07'),
  (2, 'chung_tu_hoan_thanh_san_xuat', 1, 'duyet', 'cho_duyet', 'da_duyet', NULL, '{"nhap_kho": 5, "giu_cho_yeu_cau": 5}', NULL, '2026-11-06 14:00:00+07'),
  (3, 'phieu_xuat', 3, 'tao', NULL, 'nhap', NULL, '{"loai_phieu": "xuat_thanh_pham", "yeu_cau_san_xuat_id": 1}', NULL, '2026-11-06 14:30:00+07'),
  (3, 'phieu_xuat', 3, 'gui', 'nhap', 'cho_duyet', NULL, NULL, NULL, '2026-11-06 14:35:00+07'),
  (2, 'phieu_xuat', 3, 'duyet', 'cho_duyet', 'da_duyet', NULL, '{"tong_tien": 62500000, "yeu_cau_san_xuat_trang_thai": "hoan_thanh"}', NULL, '2026-11-06 15:00:00+07'),
  -- YCSX 3 và 4
  (2, 'yeu_cau_san_xuat', 3, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 2, "so_luong": 4, "nhan_vien_duoc_giao_id": 3}', NULL, '2026-11-07 08:00:00+07'),
  (2, 'yeu_cau_san_xuat', 3, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 3}', NULL, '2026-11-07 08:10:00+07'),
  (2, 'yeu_cau_san_xuat', 4, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 2, "so_luong": 2, "nhan_vien_duoc_giao_id": 4}', NULL, '2026-11-07 08:15:00+07'),
  (2, 'yeu_cau_san_xuat', 4, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 3}', NULL, '2026-11-07 08:20:00+07'),
  (3, 'yeu_cau_san_xuat', 3, 'kiem_tra', 'da_gui', 'dang_thuc_hien', NULL, '{"so_luong_dung_thanh_pham": 0, "so_luong_can_san_xuat": 4, "giu_linh_kien": true}', NULL, '2026-11-07 09:00:00+07'),
  (4, 'yeu_cau_san_xuat', 4, 'kiem_tra', 'da_gui', 'dang_thuc_hien', NULL, '{"so_luong_dung_thanh_pham": 0, "so_luong_can_san_xuat": 2, "giu_linh_kien": true}', NULL, '2026-11-08 09:00:00+07'),
  (3, 'phieu_xuat', 4, 'tao', NULL, 'nhap', NULL, '{"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": 3}', NULL, '2026-11-08 10:00:00+07'),
  (3, 'phieu_xuat', 4, 'gui', 'nhap', 'cho_duyet', NULL, NULL, NULL, '2026-11-08 10:05:00+07'),
  (2, 'phieu_xuat', 4, 'tu_choi', 'cho_duyet', 'tu_choi', NULL, NULL, 'Kho đang kiểm đếm khu linh kiện, gửi lại sau 8h ngày 09/11.', '2026-11-08 14:00:00+07'),
  (3, 'phieu_xuat', 4, 'gui_lai', 'tu_choi', 'cho_duyet', NULL, NULL, NULL, '2026-11-09 08:00:00+07'),
  -- YCSX 5: dùng 3 xe có sẵn, sản xuất 7 (BR-008)
  (2, 'yeu_cau_san_xuat', 5, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 1, "so_luong": 10, "nhan_vien_duoc_giao_id": 3}', NULL, '2026-11-09 09:00:00+07'),
  (2, 'yeu_cau_san_xuat', 5, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 1}', NULL, '2026-11-09 09:10:00+07'),
  (3, 'yeu_cau_san_xuat', 5, 'kiem_tra', 'da_gui', 'dang_thuc_hien', NULL, '{"so_luong_dung_thanh_pham": 3, "so_luong_can_san_xuat": 7, "giu_thanh_pham": 3, "giu_linh_kien": true}', NULL, '2026-11-09 10:00:00+07'),
  (2, 'yeu_cau_san_xuat', 4, 'huy', 'dang_thuc_hien', 'da_huy', NULL, '{"tra_giu_hang": true}', 'Khách hủy đơn, không còn nhu cầu.', '2026-11-10 08:30:00+07'),
  -- YCSX 6: thiếu khung, lưu danh sách thiếu tại thời điểm kiểm tra.
  (2, 'yeu_cau_san_xuat', 6, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 3, "so_luong": 10, "nhan_vien_duoc_giao_id": 4}', NULL, '2026-11-10 08:50:00+07'),
  (2, 'yeu_cau_san_xuat', 6, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 4}', NULL, '2026-11-10 09:00:00+07'),
  (4, 'yeu_cau_san_xuat', 6, 'kiem_tra', 'da_gui', 'cho_bo_sung_linh_kien', NULL,
   '{"so_luong_dung_thanh_pham": 0, "so_luong_can_san_xuat": 10, "giu_linh_kien": false, "danh_sach_thieu": [{"mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Khung xe", "don_vi_tinh": "chiec", "so_luong_can": 10, "so_luong_con_dung": 6, "so_luong_thieu": 4}]}',
   NULL, '2026-11-10 10:00:00+07'),
  -- YCSX 7, 8 và phiếu nhập nháp
  (2, 'yeu_cau_san_xuat', 7, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 4, "so_luong": 3, "nhan_vien_duoc_giao_id": 4}', NULL, '2026-11-11 07:50:00+07'),
  (2, 'yeu_cau_san_xuat', 7, 'gui', 'nhap', 'da_gui', NULL, '{"bom_id": 5}', NULL, '2026-11-11 08:00:00+07'),
  (2, 'yeu_cau_san_xuat', 8, 'tao', NULL, 'nhap', NULL, '{"loai_yeu_cau": "dap_ung", "mat_hang_id": 1, "so_luong": 2, "nhan_vien_duoc_giao_id": 3}', NULL, '2026-11-12 08:00:00+07'),
  (2, 'phieu_nhap', 2, 'tao', NULL, 'nhap', NULL, '{"so_dong": 1}', NULL, '2026-11-12 09:00:00+07');

-- ---------------------------------------------------------------------
-- Lưu lượng truy cập minh họa cho biểu đồ Tổng quan admin.
-- Mỗi giờ một dòng, từ 00:00 của 35 ngày trước (giờ Asia/Ho_Chi_Minh) đến giờ lúc chạy seed.
-- Thấp về đêm, cao lúc 09h–11h và 14h–16h; cuối tuần bằng 55%; dao động cố định 0–20%, không random.
-- ---------------------------------------------------------------------
INSERT INTO public."LuuLuongTruyCap" (gio_bat_dau, so_request)
SELECT gio,
  round(
    (ARRAY[420, 380, 350, 330, 360, 450, 800, 1500, 2300, 3000, 2900, 2600,
           2200, 2700, 3400, 3550, 3200, 2600, 1900, 1400, 1100, 900, 700, 520])[extract(hour FROM gio)::int + 1]
    * CASE WHEN extract(isodow FROM gio) IN (6, 7) THEN 0.55 ELSE 1 END
    * (0.9 + ((extract(doy FROM gio)::int * 7 + extract(hour FROM gio)::int * 3) % 21) / 100.0)
  )::bigint
FROM generate_series(date_trunc('day', now()) - interval '35 days', date_trunc('hour', now()), interval '1 hour') AS gio;

-- Đồng bộ sequence sau khi dùng id cố định.
DO $$
DECLARE r record; seq text; maximum bigint;
BEGIN
  FOR r IN SELECT table_schema, table_name FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'id' AND table_name = ANY(ARRAY[
      'VaiTro','NhanVien','NhaCungCap','MatHang','Bom','ChiTietBom','PhieuNhap','ChiTietPhieuNhap',
      'YeuCauSanXuat','NhuCauLinhKien','GiuHang','ChungTuHoanThanhSx','PhieuXuat','ChiTietPhieuXuat',
      'GiaoDichKho','LichSuThaoTac']) LOOP
    seq := pg_get_serial_sequence(format('%I.%I', r.table_schema, r.table_name), 'id');
    IF seq IS NOT NULL THEN
      EXECUTE format('SELECT max(id) FROM %I.%I', r.table_schema, r.table_name) INTO maximum;
      PERFORM setval(seq, COALESCE(maximum, 1), maximum IS NOT NULL);
    END IF;
  END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- Tự kiểm tra số liệu trọng yếu trước COMMIT.
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF (SELECT count(*) FROM public."MatHang" WHERE loai_mat_hang = 'thanh_pham') <> 4
     OR (SELECT count(*) FROM public."MatHang" WHERE loai_mat_hang = 'linh_kien') <> 10 THEN
    RAISE EXCEPTION 'Danh mục phải có 4 thành phẩm và 10 linh kiện (BR-004)'; END IF;
  IF EXISTS (SELECT 1 FROM public."MatHang" WHERE ma_mat_hang <> 'MH-' || lpad(id::text, 6, '0'))
     OR EXISTS (SELECT 1 FROM public."NhaCungCap" WHERE ma_ncc <> 'NCC-' || lpad(id::text, 6, '0')) THEN
    RAISE EXCEPTION 'Mã mặt hàng/nhà cung cấp phải do hệ thống cấp từ id'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."MatHang" m WHERE m.loai_mat_hang = 'thanh_pham'
      AND m.is_active <> EXISTS (SELECT 1 FROM public."Bom" b WHERE b.mat_hang_id = m.id AND b.is_active)
  ) THEN RAISE EXCEPTION 'Thành phẩm đang dùng khi và chỉ khi có công thức đang dùng (BR-005)'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."MatHang" m
    WHERE m.so_luong_ton <> COALESCE((SELECT sum(g.so_luong_bien_dong) FROM public."GiaoDichKho" g WHERE g.mat_hang_id = m.id), 0)
       OR m.so_luong_ton <> COALESCE((SELECT g.so_luong_ton_sau FROM public."GiaoDichKho" g WHERE g.mat_hang_id = m.id
                                      ORDER BY g.posted_at DESC, g.id DESC LIMIT 1), 0)
  ) THEN RAISE EXCEPTION 'Tồn thực tế không khớp sổ kho'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."MatHang" m
    WHERE m.so_luong_dang_giu <> COALESCE((SELECT sum(g.so_luong) FROM public."GiuHang" g
                                           WHERE g.mat_hang_id = m.id AND g.trang_thai = 'dang_giu'), 0)
  ) THEN RAISE EXCEPTION 'Phần đang giữ không khớp GiuHang'; END IF;
  IF (SELECT row(so_luong_ton, so_luong_dang_giu, so_luong_con_dung) FROM public."MatHang" WHERE id = 5) IS DISTINCT FROM row(17, 11, 6) THEN
    RAISE EXCEPTION 'Khung xe phải là tồn 17, đang giữ 11, còn dùng được 6'; END IF;
  IF (SELECT row(so_luong_ton, so_luong_dang_giu, so_luong_con_dung) FROM public."MatHang" WHERE id = 1) IS DISTINCT FROM row(3, 3, 0) THEN
    RAISE EXCEPTION 'Mountain Pro: +3 cho kho, +5 -5 của YCSX 1 -> tồn 3, giữ 3 cho YCSX 5'; END IF;
  IF (SELECT row(loai_yeu_cau, trang_thai) FROM public."YeuCauSanXuat" WHERE id = 2) IS DISTINCT FROM row('cho_kho'::varchar, 'hoan_thanh'::varchar)
     OR EXISTS (SELECT 1 FROM public."PhieuXuat" p JOIN public."YeuCauSanXuat" y ON y.id = p.yeu_cau_san_xuat_id
                WHERE y.loai_yeu_cau = 'cho_kho' AND p.loai_phieu = 'xuat_thanh_pham')
     OR EXISTS (SELECT 1 FROM public."GiuHang" g JOIN public."YeuCauSanXuat" y ON y.id = g.yeu_cau_san_xuat_id
                WHERE y.loai_yeu_cau = 'cho_kho' AND g.loai_giu <> 'linh_kien') THEN
    RAISE EXCEPTION 'Yêu cầu cho kho: Hoàn thành khi duyệt chứng từ, không phiếu xuất/giữ thành phẩm'; END IF;
  IF (SELECT row(so_luong_dung_thanh_pham, so_luong_can_san_xuat) FROM public."YeuCauSanXuat" WHERE id = 5) IS DISTINCT FROM row(3, 7) THEN
    RAISE EXCEPTION 'YCSX 5 phải dùng 3 xe có sẵn, sản xuất 7 (BR-008)'; END IF;
  IF (SELECT n.so_luong_can - m.so_luong_con_dung FROM public."NhuCauLinhKien" n JOIN public."MatHang" m ON m.id = n.mat_hang_id
      WHERE n.yeu_cau_san_xuat_id = 6 AND n.mat_hang_id = 5) <> 4
     OR EXISTS (SELECT 1 FROM public."NhuCauLinhKien" n JOIN public."MatHang" m ON m.id = n.mat_hang_id
                WHERE n.yeu_cau_san_xuat_id = 6 AND n.mat_hang_id <> 5 AND n.so_luong_can > m.so_luong_con_dung) THEN
    RAISE EXCEPTION 'YCSX 6 phải chỉ thiếu 4 khung xe (BR-009)'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."PhieuNhap" p
    WHERE p.tong_tien IS DISTINCT FROM (SELECT sum(c.tong_gia) FROM public."ChiTietPhieuNhap" c WHERE c.phieu_nhap_id = p.id)
  ) THEN RAISE EXCEPTION 'Tiền phiếu nhập không khớp tổng dòng'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."PhieuXuat" p
    WHERE p.trang_thai = 'da_duyet'
      AND (p.tong_tien IS DISTINCT FROM (SELECT sum(c.tong_gia) FROM public."ChiTietPhieuXuat" c WHERE c.phieu_xuat_id = p.id)
           OR EXISTS (SELECT 1 FROM public."ChiTietPhieuXuat" c JOIN public."MatHang" m ON m.id = c.mat_hang_id
                      WHERE c.phieu_xuat_id = p.id AND c.don_gia_thuc IS DISTINCT FROM m.don_gia))
  ) OR (SELECT tong_tien FROM public."PhieuXuat" WHERE id = 1) <> 27950000
    OR (SELECT tong_tien FROM public."PhieuXuat" WHERE id = 2) <> 16770000
    OR (SELECT tong_tien FROM public."PhieuXuat" WHERE id = 3) <> 62500000 THEN
    RAISE EXCEPTION 'Giá phiếu xuất đã duyệt phải lấy từ MatHang.don_gia'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."PhieuXuat" p JOIN public."YeuCauSanXuat" y ON y.id = p.yeu_cau_san_xuat_id
    WHERE p.nhan_vien_id <> y.nhan_vien_duoc_giao_id
  ) THEN RAISE EXCEPTION 'Phiếu xuất do nhân viên được giao lập (BR-010)'; END IF;
  IF EXISTS (
    SELECT 1 FROM public."ChiTietPhieuXuat" c JOIN public."PhieuXuat" p ON p.id = c.phieu_xuat_id
    WHERE p.loai_phieu = 'xuat_linh_kien' AND c.so_luong IS DISTINCT FROM (
      SELECT n.so_luong_can FROM public."NhuCauLinhKien" n
      WHERE n.yeu_cau_san_xuat_id = p.yeu_cau_san_xuat_id AND n.mat_hang_id = c.mat_hang_id)
  ) THEN RAISE EXCEPTION 'Phiếu xuất linh kiện phải đúng nhu cầu đã chốt (BR-010)'; END IF;
END $$;

COMMIT;
