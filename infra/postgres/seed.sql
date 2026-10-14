-- Seed for updated data model v3. All non-identity PKs are explicit.
-- DEVELOPMENT FIXTURES ONLY. Not a production import or login implementation.
-- Sample BOM quantities are illustrative: the SRS does not specify technical quantities.
-- Opening inventory uses an approved stocktake adjustment plus ledger and audit.
-- No automatic ledger/stock trigger: all fixture rows are inserted in one transaction.
-- Execute once on a database initialized by the updated PostgreSQL init(1).sql (model v3); rerun fails without changing data.
-- Demo bcrypt password for admin, quanly, nhanvien: XbikeDemo@2026
-- Do not deploy demo users or demo inventory to production.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = public;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM nhan_vien) OR EXISTS (SELECT 1 FROM mat_hang)
       OR EXISTS (SELECT 1 FROM vai_tro) OR EXISTS (SELECT 1 FROM giao_dich_kho) THEN
        RAISE EXCEPTION 'seed.sql requires empty business tables; demo data already exists';
    END IF;
END;
$$;

INSERT INTO vai_tro (id, ma_vai_tro, ten_vai_tro) VALUES
(1, 'quan_tri_vien', 'Quản trị viên'),
(2, 'quan_ly', 'Quản lý kho'),
(3, 'nhan_vien', 'Nhân viên');

-- pgcrypto bcrypt cost 12, compatible with the repository bcrypt verifier.
-- tai_khoan_id remains NULL: no account table is defined in data model v2.
INSERT INTO nhan_vien (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien,
                       ho_ten, email, ngay_vao_lam, trang_thai) VALUES
(1, 1, 'admin', crypt('XbikeDemo@2026', gen_salt('bf',12)), 'NV001',
 'Quản trị viên mẫu', 'admin@xbike.local', DATE '2026-10-14', 'hoat_dong'),
(2, 2, 'quanly', crypt('XbikeDemo@2026', gen_salt('bf',12)), 'NV002',
 'Quản lý kho mẫu', 'quanly@xbike.local', DATE '2026-10-14', 'hoat_dong'),
(3, 3, 'nhanvien', crypt('XbikeDemo@2026', gen_salt('bf',12)), 'NV003',
 'Nhân viên mẫu', 'nhanvien@xbike.local', DATE '2026-10-14', 'hoat_dong');

INSERT INTO nha_cung_cap (id, ma_ncc, ten_ncc, dia_chi, tinh) VALUES
(1, 'NCC001', 'Nhà cung cấp linh kiện mẫu', 'Địa chỉ mẫu 1', 'TP. Hồ Chí Minh'),
(2, 'NCC002', 'Nhà cung cấp vật tư mẫu', 'Địa chỉ mẫu 2', 'TP. Hồ Chí Minh');

INSERT INTO mat_hang (id, ma_mat_hang, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, is_active) VALUES
(1, 'TP001', 'Xe đạp Mountain Pro', 'XB-TP001', 'thanh_pham', 'chiec', 5000000, TRUE),
(2, 'TP002', 'Xe đạp City Ride', 'XB-TP002', 'thanh_pham', 'chiec', 3500000, TRUE),
(3, 'TP003', 'Xe đạp Speed Sport', 'XB-TP003', 'thanh_pham', 'chiec', 7000000, TRUE),
(4, 'TP004', 'Xe đạp Kids Fun', 'XB-TP004', 'thanh_pham', 'chiec', 2000000, TRUE),
(5, 'BTP001', 'Cụm bánh xe', 'XB-BTP001', 'ban_thanh_pham', 'chiec', 350000, TRUE),
(6, 'LK001', 'Khung xe', 'XB-LK001', 'linh_kien', 'chiec', 600000, TRUE),
(7, 'LK002', 'Phuộc xe', 'XB-LK002', 'linh_kien', 'chiec', 200000, TRUE),
(8, 'LK003', 'Vành bánh xe', 'XB-LK003', 'linh_kien', 'chiec', 120000, TRUE),
(9, 'LK004', 'Moay-ơ', 'XB-LK004', 'linh_kien', 'chiec', 80000, TRUE),
(10, 'NVL001', 'Nan hoa', 'XB-NVL001', 'nguyen_vat_lieu', 'chiec', 2000, TRUE),
(11, 'LK005', 'Lốp xe', 'XB-LK005', 'linh_kien', 'chiec', 100000, TRUE),
(12, 'LK006', 'Xích xe', 'XB-LK006', 'linh_kien', 'chiec', 60000, TRUE),
(13, 'LK007', 'Bàn đạp', 'XB-LK007', 'linh_kien', 'chiec', 40000, TRUE),
(14, 'NVL002', 'Dây phanh', 'XB-NVL002', 'nguyen_vat_lieu', 'chiec', 20000, TRUE),
(15, 'LK008', 'Yên xe', 'XB-LK008', 'linh_kien', 'chiec', 80000, TRUE),
(16, 'LK009', 'Đĩa xích', 'XB-LK009', 'linh_kien', 'chiec', 70000, TRUE),
(17, 'NVL003', 'Bộ ốc vít', 'XB-NVL003', 'nguyen_vat_lieu', 'bo', 15000, TRUE);
INSERT INTO bom (id, mat_hang_id, version, start_time, is_active) VALUES
(1, 1, 1, TIMESTAMP '2026-10-14 08:00:00', TRUE),
(2, 2, 1, TIMESTAMP '2026-10-14 08:00:00', TRUE),
(3, 3, 1, TIMESTAMP '2026-10-14 08:00:00', TRUE),
(4, 4, 1, TIMESTAMP '2026-10-14 08:00:00', TRUE),
(5, 5, 1, TIMESTAMP '2026-10-14 08:00:00', TRUE);
INSERT INTO chi_tiet_bom (id,bom_id,mat_hang_id,so_luong) VALUES
(1, 1, 6, 1),
(2, 1, 7, 1),
(3, 1, 5, 2),
(4, 1, 11, 2),
(5, 1, 12, 1),
(6, 1, 13, 2),
(7, 1, 14, 2),
(8, 1, 15, 1),
(9, 1, 16, 1),
(10, 1, 17, 1),
(11, 2, 6, 1),
(12, 2, 7, 1),
(13, 2, 5, 2),
(14, 2, 11, 2),
(15, 2, 12, 1),
(16, 2, 13, 2),
(17, 2, 14, 2),
(18, 2, 15, 1),
(19, 2, 16, 1),
(20, 2, 17, 1),
(21, 3, 6, 1),
(22, 3, 7, 1),
(23, 3, 5, 2),
(24, 3, 11, 2),
(25, 3, 12, 1),
(26, 3, 13, 2),
(27, 3, 14, 2),
(28, 3, 15, 1),
(29, 3, 16, 1),
(30, 3, 17, 1),
(31, 4, 6, 1),
(32, 4, 7, 1),
(33, 4, 5, 2),
(34, 4, 11, 2),
(35, 4, 12, 1),
(36, 4, 13, 2),
(37, 4, 14, 2),
(38, 4, 15, 1),
(39, 4, 16, 1),
(40, 4, 17, 1),
(41, 5, 8, 1),
(42, 5, 9, 1),
(43, 5, 10, 36);

-- Independent stocktake of opening balances, not purchase/production receipts.
INSERT INTO phieu_dieu_chinh_kho (id,ma_phieu,nhan_vien_id,ly_do,trang_thai,created_at)
VALUES (1,'DC-OPENING-001',2,'Kiểm kê độc lập: ghi nhận tồn đầu kỳ cho toàn bộ mặt hàng mẫu; không gắn chứng từ cũ.',
        'da_duyet',TIMESTAMP '2026-10-14 08:00:00');

INSERT INTO chi_tiet_phieu_dieu_chinh_kho (id,phieu_dieu_chinh_kho_id,mat_hang_id,so_luong_bien_dong) VALUES
(1,1,1,2),
(2,1,2,5),
(4,1,4,3),
(5,1,5,8),
(6,1,6,50),
(7,1,7,50),
(8,1,8,100),
(9,1,9,100),
(10,1,10,4000),
(11,1,11,100),
(12,1,12,50),
(13,1,13,100),
(14,1,14,100),
(15,1,15,50),
(16,1,16,50),
(17,1,17,50);
INSERT INTO giao_dich_kho (mat_hang_id,loai_giao_dich,so_luong_bien_dong,
                           chi_tiet_phieu_dieu_chinh_id,nhan_vien_id,posted_at)
SELECT mat_hang_id,'dieu_chinh_ton_kho',so_luong_bien_dong,id,2,TIMESTAMP '2026-10-14 08:00:00'
FROM chi_tiet_phieu_dieu_chinh_kho WHERE phieu_dieu_chinh_kho_id=1;
INSERT INTO ton_kho (id,mat_hang_id,so_luong,updated_at)
SELECT m.id,m.id,COALESCE(SUM(g.so_luong_bien_dong),0)::INTEGER,TIMESTAMP '2026-10-14 08:00:00'
FROM mat_hang m LEFT JOIN giao_dich_kho g ON g.mat_hang_id=m.id GROUP BY m.id;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau,ly_do)
VALUES (2,'phieu_dieu_chinh_kho',1,'duyet','{"trang_thai":"cho_duyet"}',
        '{"trang_thai":"da_duyet","nguon":"seed_demo","kiem_ke_doc_lap":true}',
        'Dữ liệu mẫu bootstrap: kiểm kê tồn đầu kỳ đã duyệt.');

-- SENT request: need 10 Mountain Pro, opening stock 2 -> produce 8.
-- Parent requires 16 wheel assemblies, opening stock 8 -> child produces 8.
-- Snapshot only: sending these orders has NOT issued materials or reserved stock.
INSERT INTO yeu_cau_san_xuat
(id,ma_yeu_cau_san_xuat,mat_hang_id,so_luong,nhan_vien_id,nhan_vien_duoc_giao_id,trang_thai,created_at)
VALUES (1,'YC-DEMO-001',1,10,2,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00'),
       (2,'YC-DEMO-002',2,3,2,3,'nhap',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO lenh_san_xuat
(id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,lenh_san_xuat_cha_id,mat_hang_id,bom_id,so_luong,nhan_vien_id,trang_thai,created_at)
VALUES (1,'LSX-DEMO-001',1,NULL,1,1,8,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00'),
       (2,'LSX-DEMO-002',1,1,5,5,8,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_lenh_san_xuat (id,lenh_san_xuat_id,mat_hang_id,so_luong_can)
SELECT row_number() OVER (ORDER BY l.id,c.mat_hang_id)::INTEGER,l.id,c.mat_hang_id,c.so_luong*l.so_luong
FROM lenh_san_xuat l JOIN chi_tiet_bom c ON c.bom_id=l.bom_id;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau,ly_do)
SELECT 2,'lenh_san_xuat',id,'gui','{"trang_thai":"nhap"}',
       jsonb_build_object('trang_thai',trang_thai,'bom_id',bom_id,'so_luong',so_luong),
       'Kế hoạch mẫu đã gửi; chưa giữ chỗ, xuất vật tư hoặc cập nhật tồn.' FROM lenh_san_xuat;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau)
VALUES (2,'yeu_cau_san_xuat',1,'gui','{"trang_thai":"nhap"}','{"trang_thai":"da_gui","nhan_vien_duoc_giao_id":3}');

-- Draft receipt: does not affect balances.
INSERT INTO phieu_nhap (id,ma_phieu_nhap,nhan_vien_id,ncc_id,tong_tien,trang_thai,created_at)
VALUES (1,'PN-DEMO-001',2,1,1200000,'nhap',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_phieu_nhap (id,phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia)
VALUES (1,1,8,10,120000,1200000);

-- Pending material issue for the CHILD order only; no stock subtraction yet.
INSERT INTO phieu_xuat (id,ma_phieu_xuat,ma_nhan_vien,loai_phieu,lenh_san_xuat_id,trang_thai,created_at)
VALUES (1,'PX-VT-DEMO-001','NV003','xuat_vat_tu',2,'cho_duyet',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_phieu_xuat (id,phieu_xuat_id,mat_hang_id,so_luong)
SELECT row_number() OVER (ORDER BY mat_hang_id)::INTEGER,1,mat_hang_id,so_luong_can FROM chi_tiet_lenh_san_xuat WHERE lenh_san_xuat_id=2;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau)
VALUES (3,'phieu_xuat',1,'gui','{"trang_thai":"nhap"}','{"trang_thai":"cho_duyet"}');

-- Failed adjustment fixture: would subtract 200 rims from stock 100; no ledger.
INSERT INTO phieu_dieu_chinh_kho (id,ma_phieu,nhan_vien_id,ly_do,trang_thai)
VALUES (2,'DC-ERROR-DEMO-001',2,'Kiểm kê độc lập mẫu: giảm 200 vành; lỗi vì vượt tồn hiện có.','loi');
INSERT INTO chi_tiet_phieu_dieu_chinh_kho (id,phieu_dieu_chinh_kho_id,mat_hang_id,so_luong_bien_dong)
VALUES (18,2,8,-200);
INSERT INTO ticket_loi_dieu_chinh (id,phieu_dieu_chinh_kho_id,mo_ta_loi,trang_thai)
VALUES (1,2,'Mặt hàng LK003: tồn 100, điều chỉnh -200; kết quả -100 không hợp lệ. Fixture sau rollback, chưa đổi tồn.','cho_xu_ly');
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau,ly_do)
VALUES (2,'phieu_dieu_chinh_kho',2,'ghi_nhan_loi','{"trang_thai":"cho_duyet"}',
        '{"trang_thai":"loi","rollback":true,"nguon":"seed_demo"}',
        'Tình huống lỗi mẫu sau rollback; không phải một lần duyệt đã thực thi.');

-- Reset all identity sequences after explicit fixture IDs.
DO $$
DECLARE r RECORD; seq TEXT; max_id BIGINT;
BEGIN
    FOR r IN SELECT table_name FROM information_schema.columns
             WHERE table_schema='public' AND column_name='id' AND is_identity='YES'
    LOOP
        seq := pg_get_serial_sequence(format('public.%I',r.table_name),'id');
        EXECUTE format('SELECT MAX(id) FROM public.%I',r.table_name) INTO max_id;
        PERFORM setval(seq::regclass,COALESCE(max_id,1),max_id IS NOT NULL);
    END LOOP;
END;
$$;

-- Assert ledger/balance equality before commit.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM ton_kho t LEFT JOIN (
            SELECT mat_hang_id,SUM(so_luong_bien_dong) AS quantity
            FROM giao_dich_kho GROUP BY mat_hang_id
        ) g USING(mat_hang_id)
        WHERE t.so_luong <> COALESCE(g.quantity,0)
    ) THEN
        RAISE EXCEPTION 'Seed stock/ledger mismatch';
    END IF;
END;
$$;
COMMIT;
