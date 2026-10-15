-- xBike MRP — Dữ liệu mẫu theo mrp-xbike-data-model-v3.txt cập nhật 15/10/2026.
-- Chạy bằng psql, sau init.sql tương ứng, trên cơ sở dữ liệu nghiệp vụ còn trống.
-- Đây là tệp khởi tạo dữ liệu mẫu, không phải migration hoặc tệp cập nhật dữ liệu cũ.
-- Tên hiển thị có dấu; danh mục dùng snake_case tiếng Việt không dấu.
-- Mã danh mục: NV/MH/NCC-NNNNNN. Mã chứng từ: TIEN_TO-YYYYMM-NNNNNN.
-- Giữ tháng 202610 theo thời điểm tạo dữ liệu mẫu, múi giờ Asia/Ho_Chi_Minh.
-- SRS quy định cấu trúc BOM; số lượng và đơn giá dưới đây là ví dụ thử nghiệm.
-- Bốn xe có BOM riêng; các mã linh kiện dùng chung chỉ là giả định của dữ liệu mẫu.
-- Nhãn đối chiếu SRS: xe leo núi, xe đô thị, xe thể thao, xe trẻ em theo đúng thứ tự model.
-- Tồn đầu kỳ được ghi bằng phiếu kiểm kê độc lập đã duyệt, sổ kho và lịch sử.
-- Phiếu nháp/chờ duyệt/lỗi không làm đổi tồn; không có trigger tự cộng/trừ kho.
-- Tài khoản mẫu: quan_tri_vien / quan_ly / nhan_vien. Mật khẩu: XeDapMau@2026.
-- Mật khẩu lưu bcrypt chi phí 12; không dùng tài khoản và dữ liệu mẫu ở môi trường thật.
-- V3 hiện tại dùng nhan_vien.loai_nhan_vien, phieu_xuat.nhan_vien_id, ticket.ma_ticket.
-- Phải đồng bộ init.sql cũ trước khi nạp; tệp này không tự sửa schema.
-- Hai FK 1–1 phải trỏ từ ton_kho tới mat_hang và từ ticket tới phieu_dieu_chinh_kho.
-- Nguồn DBML 15/10 đang ghi ngược hai Ref dấu '-'; cần sửa nguồn trước khi export init.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = public;

-- Dừng trước khi nạp nếu schema chưa khớp phiên bản nguồn mới nhất.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
                   AND table_name='nhan_vien' AND column_name='loai_nhan_vien')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
                   AND table_name='phieu_xuat' AND column_name='nhan_vien_id')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
                   AND table_name='ticket_loi_dieu_chinh' AND column_name='ma_ticket') THEN
        RAISE EXCEPTION 'Schema chưa khớp v3 ngày 15/10: cần nhan_vien.loai_nhan_vien, phieu_xuat.nhan_vien_id và ticket_loi_dieu_chinh.ma_ticket. Hãy đồng bộ init.sql trước.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE contype='f' AND (
            (conrelid='public.mat_hang'::regclass AND confrelid='public.ton_kho'::regclass)
            OR (conrelid='public.phieu_dieu_chinh_kho'::regclass AND confrelid='public.ticket_loi_dieu_chinh'::regclass)
        )
    ) THEN
        RAISE EXCEPTION 'Hai FK 1–1 đang ngược nghiệp vụ. Cần ton_kho.mat_hang_id -> mat_hang.id và ticket_loi_dieu_chinh.phieu_dieu_chinh_kho_id -> phieu_dieu_chinh_kho.id.';
    END IF;
END;
$$;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM nhan_vien)
       OR EXISTS (SELECT 1 FROM vai_tro)
       OR EXISTS (SELECT 1 FROM mat_hang)
       OR EXISTS (SELECT 1 FROM ton_kho)
       OR EXISTS (SELECT 1 FROM bom)
       OR EXISTS (SELECT 1 FROM chi_tiet_bom)
       OR EXISTS (SELECT 1 FROM nha_cung_cap)
       OR EXISTS (SELECT 1 FROM phieu_nhap)
       OR EXISTS (SELECT 1 FROM chi_tiet_phieu_nhap)
       OR EXISTS (SELECT 1 FROM phieu_xuat)
       OR EXISTS (SELECT 1 FROM chi_tiet_phieu_xuat)
       OR EXISTS (SELECT 1 FROM yeu_cau_san_xuat)
       OR EXISTS (SELECT 1 FROM lenh_san_xuat)
       OR EXISTS (SELECT 1 FROM chi_tiet_lenh_san_xuat)
       OR EXISTS (SELECT 1 FROM chung_tu_hoan_thanh_sx)
       OR EXISTS (SELECT 1 FROM phieu_dieu_chinh_kho)
       OR EXISTS (SELECT 1 FROM chi_tiet_phieu_dieu_chinh_kho)
       OR EXISTS (SELECT 1 FROM ticket_loi_dieu_chinh)
       OR EXISTS (SELECT 1 FROM giao_dich_kho)
       OR EXISTS (SELECT 1 FROM lich_su_thao_tac) THEN
        RAISE EXCEPTION 'seed.sql yêu cầu các bảng nghiệp vụ trống; không nạp trùng dữ liệu mẫu';
    END IF;
END;
$$;

INSERT INTO vai_tro (id, ma_vai_tro, ten_vai_tro) VALUES
(1, 'quan_tri_vien', 'Quản trị viên'),
(2, 'quan_ly', 'Quản lý'),
(3, 'nhan_vien', 'Nhân viên');

-- Mật khẩu được băm bcrypt bằng pgcrypto, chi phí 12.
-- tai_khoan_id để NULL: v3 chưa định nghĩa bảng tài khoản tham chiếu.
INSERT INTO nhan_vien (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien,
                       ho_ten, email, ngay_vao_lam, loai_nhan_vien) VALUES
(1, 1, 'quan_tri_vien', crypt('XeDapMau@2026', gen_salt('bf',12)), 'NV-000001',
 'Quản trị viên mẫu', 'quan_tri_vien@xbike.local', DATE '2026-10-14', 'quan_tri_vien'),
(2, 2, 'quan_ly', crypt('XeDapMau@2026', gen_salt('bf',12)), 'NV-000002',
 'Quản lý kho mẫu', 'quan_ly@xbike.local', DATE '2026-10-14', 'quan_ly'),
(3, 3, 'nhan_vien', crypt('XeDapMau@2026', gen_salt('bf',12)), 'NV-000003',
 'Nhân viên mẫu', 'nhan_vien@xbike.local', DATE '2026-10-14', 'nhan_vien');

INSERT INTO nha_cung_cap (id, ma_ncc, ten_ncc, dia_chi, tinh) VALUES
(1, 'NCC-000001', 'Nhà cung cấp linh kiện mẫu', 'Địa chỉ mẫu 1', 'TP. Hồ Chí Minh'),
(2, 'NCC-000002', 'Nhà cung cấp vật tư mẫu', 'Địa chỉ mẫu 2', 'TP. Hồ Chí Minh');

INSERT INTO mat_hang (id, ma_mat_hang, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, is_active) VALUES
(1, 'MH-000001', 'Xe đạp leo núi', 'xe_dap_leo_nui', 'thanh_pham', 'chiec', 5000000, TRUE),
(2, 'MH-000002', 'Xe đạp đô thị', 'xe_dap_do_thi', 'thanh_pham', 'chiec', 3500000, TRUE),
(3, 'MH-000003', 'Xe đạp thể thao', 'xe_dap_the_thao', 'thanh_pham', 'chiec', 7000000, TRUE),
(4, 'MH-000004', 'Xe đạp trẻ em', 'xe_dap_tre_em', 'thanh_pham', 'chiec', 2000000, TRUE),
(5, 'MH-000005', 'Cụm bánh xe', 'cum_banh_xe', 'ban_thanh_pham', 'chiec', 350000, TRUE),
(6, 'MH-000006', 'Khung xe', 'khung_xe', 'linh_kien', 'chiec', 600000, TRUE),
(7, 'MH-000007', 'Phuộc xe', 'phuoc_xe', 'linh_kien', 'chiec', 200000, TRUE),
(8, 'MH-000008', 'Vành bánh xe', 'vanh_banh_xe', 'linh_kien', 'chiec', 120000, TRUE),
(9, 'MH-000009', 'Moay-ơ', 'moay_o', 'linh_kien', 'chiec', 80000, TRUE),
(10, 'MH-000010', 'Nan hoa', 'nan_hoa', 'nguyen_vat_lieu', 'chiec', 2000, TRUE),
(11, 'MH-000011', 'Lốp xe', 'lop_xe', 'linh_kien', 'chiec', 100000, TRUE),
(12, 'MH-000012', 'Xích xe', 'xich_xe', 'linh_kien', 'chiec', 60000, TRUE),
(13, 'MH-000013', 'Bàn đạp', 'ban_dap', 'linh_kien', 'chiec', 40000, TRUE),
(14, 'MH-000014', 'Dây phanh', 'day_phanh', 'nguyen_vat_lieu', 'chiec', 20000, TRUE),
(15, 'MH-000015', 'Yên xe', 'yen_xe', 'linh_kien', 'chiec', 80000, TRUE),
(16, 'MH-000016', 'Đĩa xích', 'dia_xich', 'linh_kien', 'chiec', 70000, TRUE),
(17, 'MH-000017', 'Bộ ốc vít', 'bo_oc_vit', 'nguyen_vat_lieu', 'bo', 15000, TRUE);
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

-- Kiểm kê độc lập để ghi nhận số dư đầu kỳ cho dữ liệu mẫu.
INSERT INTO phieu_dieu_chinh_kho (id,ma_phieu,nhan_vien_id,ly_do,trang_thai,created_at)
VALUES (1,'DCK-202610-000001',2,'Kiểm kê độc lập: ghi nhận tồn đầu kỳ cho toàn bộ mặt hàng mẫu; không gắn chứng từ cũ.',
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
        '{"trang_thai":"da_duyet","nguon":"du_lieu_mau","kiem_ke_doc_lap":true}',
        'Dữ liệu khởi tạo mẫu: kiểm kê tồn đầu kỳ đã duyệt.');

-- Yêu cầu đã gửi: cần 10 xe leo núi, có sẵn 2 -> sản xuất 8.
-- Lệnh cha cần 16 cụm bánh, có sẵn 8 -> lệnh con sản xuất 8 cụm.
-- Bản chụp nhu cầu: gửi lệnh chưa xuất vật tư hoặc giữ chỗ tồn kho.
INSERT INTO yeu_cau_san_xuat
(id,ma_yeu_cau_san_xuat,mat_hang_id,so_luong,nhan_vien_id,nhan_vien_duoc_giao_id,trang_thai,created_at)
VALUES (1,'YCSX-202610-000001',1,10,2,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00'),
       (2,'YCSX-202610-000002',2,3,2,3,'nhap',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO lenh_san_xuat
(id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,lenh_san_xuat_cha_id,mat_hang_id,bom_id,so_luong,nhan_vien_id,trang_thai,created_at)
VALUES (1,'LSX-202610-000001',1,NULL,1,1,8,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00'),
       (2,'LSX-202610-000002',1,1,5,5,8,3,'da_gui',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_lenh_san_xuat (id,lenh_san_xuat_id,mat_hang_id,so_luong_can)
SELECT row_number() OVER (ORDER BY l.id,c.mat_hang_id)::INTEGER,l.id,c.mat_hang_id,c.so_luong*l.so_luong
FROM lenh_san_xuat l JOIN chi_tiet_bom c ON c.bom_id=l.bom_id;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau,ly_do)
SELECT 2,'lenh_san_xuat',id,'gui','{"trang_thai":"nhap"}',
       jsonb_build_object('trang_thai',trang_thai,'bom_id',bom_id,'so_luong',so_luong),
       'Kế hoạch mẫu đã gửi; chưa giữ chỗ, xuất vật tư hoặc cập nhật tồn.' FROM lenh_san_xuat;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau)
VALUES (2,'yeu_cau_san_xuat',1,'gui','{"trang_thai":"nhap"}','{"trang_thai":"da_gui","nhan_vien_duoc_giao_id":3}');

-- Phiếu nhập nháp: chưa cộng tồn kho.
INSERT INTO phieu_nhap (id,ma_phieu_nhap,nhan_vien_id,ncc_id,tong_tien,trang_thai,created_at)
VALUES (1,'PN-202610-000001',2,1,1200000,'nhap',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_phieu_nhap (id,phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia)
VALUES (1,1,8,10,120000,1200000);

-- Phiếu xuất vật tư chờ duyệt chỉ phục vụ lệnh con; chưa trừ tồn kho.
INSERT INTO phieu_xuat (id,ma_phieu_xuat,nhan_vien_id,loai_phieu,lenh_san_xuat_id,trang_thai,created_at)
VALUES (1,'PX-202610-000001',3,'xuat_vat_tu',2,'cho_duyet',TIMESTAMP '2026-10-14 09:00:00');
INSERT INTO chi_tiet_phieu_xuat (id,phieu_xuat_id,mat_hang_id,so_luong)
SELECT row_number() OVER (ORDER BY mat_hang_id)::INTEGER,1,mat_hang_id,so_luong_can FROM chi_tiet_lenh_san_xuat WHERE lenh_san_xuat_id=2;
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau)
VALUES (3,'phieu_xuat',1,'gui','{"trang_thai":"nhap"}','{"trang_thai":"cho_duyet"}');

-- Tình huống lỗi mẫu: giảm 200 vành khi chỉ có 100; không ghi biến động kho.
INSERT INTO phieu_dieu_chinh_kho (id,ma_phieu,nhan_vien_id,ly_do,trang_thai,created_at)
VALUES (2,'DCK-202610-000002',2,'Kiểm kê độc lập mẫu: giảm 200 vành; lỗi vì vượt tồn hiện có.','loi',TIMESTAMP '2026-10-14 09:30:00');
INSERT INTO chi_tiet_phieu_dieu_chinh_kho (id,phieu_dieu_chinh_kho_id,mat_hang_id,so_luong_bien_dong)
VALUES (18,2,8,-200);
INSERT INTO ticket_loi_dieu_chinh (id,ma_ticket,phieu_dieu_chinh_kho_id,mo_ta_loi,trang_thai,created_at)
VALUES (1,'TKDC-202610-000001',2,'Mặt hàng MH-000008: tồn 100, điều chỉnh -200; kết quả -100 không hợp lệ. Dữ liệu mẫu sau hoàn tác giao dịch, chưa đổi tồn.','cho_xu_ly',TIMESTAMP '2026-10-14 09:30:00');
INSERT INTO lich_su_thao_tac (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_truoc,du_lieu_sau,ly_do)
VALUES (2,'phieu_dieu_chinh_kho',2,'ghi_nhan_loi','{"trang_thai":"cho_duyet"}',
        '{"trang_thai":"loi","da_hoan_tac":true,"nguon":"du_lieu_mau"}',
        'Tình huống lỗi mẫu sau hoàn tác giao dịch; chưa thực thi duyệt phiếu.');

-- Đồng bộ bộ đếm của các cột IDENTITY sau khi nạp dữ liệu mẫu.
DO $$
DECLARE bang RECORD; ten_bo_dem TEXT; id_lon_nhat BIGINT;
BEGIN
    FOR bang IN SELECT table_name FROM information_schema.columns
             WHERE table_schema='public' AND column_name='id' AND is_identity='YES'
    LOOP
        ten_bo_dem := pg_get_serial_sequence(format('public.%I',bang.table_name),'id');
        EXECUTE format('SELECT MAX(id) FROM public.%I',bang.table_name) INTO id_lon_nhat;
        PERFORM setval(ten_bo_dem::regclass,COALESCE(id_lon_nhat,1),id_lon_nhat IS NOT NULL);
    END LOOP;
END;
$$;

-- Đối soát số dư với sổ giao dịch kho trước khi chốt giao dịch.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM ton_kho t LEFT JOIN (
            SELECT mat_hang_id,SUM(so_luong_bien_dong) AS so_luong_ghi_so
            FROM giao_dich_kho GROUP BY mat_hang_id
        ) g USING(mat_hang_id)
        WHERE t.so_luong <> COALESCE(g.so_luong_ghi_so,0)
    ) THEN
        RAISE EXCEPTION 'Tồn kho không khớp tổng biến động trong sổ giao dịch kho';
    END IF;
END;
$$;
COMMIT;
