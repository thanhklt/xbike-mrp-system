-- xBike MRP: khởi tạo PostgreSQL từ mrp-xbike-data-model-v3.txt.
-- Chạy một lần trên database/schema public trống; không DROP hoặc ghi đè bảng.
-- Ví dụ: psql -v ON_ERROR_STOP=1 -d xbike_mrp -f init.sql
-- Giữ nguyên 20 bảng, tên/kiểu cột, nullability và 39 FK của v3.
-- Bổ sung đã thống nhất cho auth contract v2: nhan_vien.trang_thai,
-- NOT NULL, DEFAULT hoat_dong và CHECK hoat_dong/bi_khoa.
-- Giữ loai_nhan_vien cũ trong SQL để bảo toàn dữ liệu; API không dùng/trả cột này.
-- Chỉ hai id có [increment] dùng IDENTITY; các id khác do ứng dụng cung cấp.
-- tai_khoan_id chưa có bảng đích: giữ INTEGER, chưa tạo FK.
-- Không tự sinh ma_*; backend cấp mã theo quy ước v3, an toàn khi đồng thời.
-- Giữ TIMESTAMP WITHOUT TIME ZONE theo v3; các giá tiền vẫn INTEGER.
-- Các CHECK thực thi quy tắc cùng dòng; COMMENT giữ đầy đủ Note của DBML.
-- Backend phải xử lý: chuyển trạng thái hợp lệ, bất biến chứng từ/BOM đã dùng,
-- chống chu trình nhiều cấp, khớp mặt hàng/lượng với nguồn, phân quyền,
-- tổng lượng cấp/hoàn thành/xuất, ghi sổ + tồn + audit cùng transaction.
-- Điều chỉnh thất bại: rollback rồi transaction RIÊNG tạo/mở lại ticket.
-- Các quy tắc trên KHÔNG tự được thực thi chỉ bởi file khởi tạo này.

BEGIN;
SET LOCAL search_path TO public;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';

-- QUY ƯỚC MÃ NGHIỆP VỤ
-- Quy ước mã nghiệp vụ:
-- - Mã danh mục: TIEN_TO-NNNNNN; số thứ tự tăng riêng theo loại, không đặt lại theo tháng.
-- - Mã chứng từ và ticket: TIEN_TO-YYYYMM-NNNNNN.
-- - YYYYMM là năm tháng tại thời điểm tạo bản ghi theo múi giờ Asia/Ho_Chi_Minh;
-- backend lấy thời gian tạo, kể cả bảng chưa có cột created_at.
-- - NNNNNN gồm đúng 6 chữ số, từ 000001 đến 999999; bộ đếm riêng theo tiền tố
-- và tháng đối với mã có YYYYMM. Hết dải phải báo lỗi, không quay vòng.
-- - Backend sinh mã an toàn khi đồng thời; không dùng MAX + 1 không có khóa.
-- - Sinh một lần khi tạo; không đổi khi gửi/duyệt/hủy, không tái sử dụng mã đã cấp.
-- Cho phép khuyết số; không yêu cầu dãy liên tục khi rollback hoặc xóa nháp.
-- - Mã vai trò là mã cố định snake_case không dấu, không dùng bộ đếm.
-- - id là khóa chính và dùng cho FK; ma_* là mã nghiệp vụ để tra cứu/hiển thị.
-- - Định dạng trong Note phải được triển khai bằng backend và constraint phù hợp.
-- NOT NULL/UNIQUE không tự kiểm tra định dạng mã.

CREATE TABLE nhan_vien (
    id INTEGER PRIMARY KEY,
    vai_tro_id INTEGER,
    tai_khoan_id INTEGER,
    ten_dang_nhap VARCHAR NOT NULL UNIQUE,
    mat_khau VARCHAR NOT NULL,
    ma_nhan_vien VARCHAR NOT NULL UNIQUE,
    ho_ten VARCHAR,
    ngay_sinh DATE,
    so_dien_thoai VARCHAR,
    email VARCHAR,
    ngay_vao_lam DATE,
    he_so_luong NUMERIC(5,2),
    trang_thai VARCHAR NOT NULL DEFAULT 'hoat_dong',
    loai_nhan_vien VARCHAR,
    CONSTRAINT ck_nhan_vien_trang_thai CHECK (trang_thai IN ('hoat_dong', 'bi_khoa')),
    CONSTRAINT ck_nhan_vien_01 CHECK (loai_nhan_vien IN ('nhan_vien', 'quan_ly', 'quan_tri_vien')),
    CONSTRAINT ck_nhan_vien_02 CHECK (ma_nhan_vien ~ '^NV-[0-9]{6}$' AND right(ma_nhan_vien, 6) <> '000000')
);

CREATE TABLE vai_tro (
    id INTEGER PRIMARY KEY,
    ma_vai_tro VARCHAR NOT NULL UNIQUE,
    ten_vai_tro VARCHAR NOT NULL,
    CONSTRAINT ck_vai_tro_01 CHECK (ma_vai_tro IN ('nhan_vien', 'quan_ly', 'quan_tri_vien'))
);

CREATE TABLE mat_hang (
    id INTEGER PRIMARY KEY,
    ma_mat_hang VARCHAR NOT NULL UNIQUE,
    ten_mat_hang VARCHAR,
    sku VARCHAR NOT NULL UNIQUE,
    loai_mat_hang VARCHAR NOT NULL,
    don_vi_tinh VARCHAR NOT NULL,
    mau_sac VARCHAR,
    mo_ta VARCHAR,
    don_gia INTEGER,
    is_active BOOLEAN,
    CONSTRAINT ck_mat_hang_01 CHECK (loai_mat_hang IN ('nguyen_vat_lieu', 'linh_kien', 'ban_thanh_pham', 'thanh_pham')),
    CONSTRAINT ck_mat_hang_02 CHECK (don_vi_tinh ~ '^[a-z]+(_[a-z]+)*$'),
    CONSTRAINT ck_mat_hang_03 CHECK (mau_sac ~ '^[a-z]+(_[a-z]+)*$'),
    CONSTRAINT ck_mat_hang_04 CHECK (ma_mat_hang ~ '^MH-[0-9]{6}$' AND right(ma_mat_hang, 6) <> '000000')
);

CREATE TABLE ton_kho (
    id INTEGER PRIMARY KEY,
    mat_hang_id INTEGER NOT NULL UNIQUE,
    so_luong INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_ton_kho_01 CHECK (so_luong >= 0)
);

CREATE TABLE bom (
    id INTEGER PRIMARY KEY,
    mat_hang_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    start_time TIMESTAMP WITHOUT TIME ZONE,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    is_active BOOLEAN,
    UNIQUE (mat_hang_id, version),
    CONSTRAINT ck_bom_01 CHECK (version > 0)
);

CREATE TABLE chi_tiet_bom (
    id INTEGER PRIMARY KEY,
    bom_id INTEGER NOT NULL,
    mat_hang_id INTEGER NOT NULL,
    so_luong INTEGER NOT NULL,
    UNIQUE (bom_id, mat_hang_id),
    CONSTRAINT ck_chi_tiet_bom_01 CHECK (so_luong > 0)
);

CREATE TABLE nha_cung_cap (
    id INTEGER PRIMARY KEY,
    ma_ncc VARCHAR NOT NULL UNIQUE,
    ten_ncc VARCHAR,
    so_dien_thoai VARCHAR,
    dia_chi VARCHAR,
    phuong VARCHAR,
    tinh VARCHAR,
    CONSTRAINT ck_nha_cung_cap_01 CHECK (ma_ncc ~ '^NCC-[0-9]{6}$' AND right(ma_ncc, 6) <> '000000')
);

CREATE TABLE phieu_nhap (
    id INTEGER PRIMARY KEY,
    ma_phieu_nhap VARCHAR NOT NULL UNIQUE,
    nhan_vien_id INTEGER,
    ncc_id INTEGER,
    tong_tien INTEGER,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    created_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_phieu_nhap_01 CHECK (trang_thai IN ('nhap', 'hoan_thanh')),
    CONSTRAINT ck_phieu_nhap_02 CHECK (ma_phieu_nhap ~ '^PN-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu_nhap, 6) <> '000000')
);

CREATE TABLE chi_tiet_phieu_nhap (
    id INTEGER PRIMARY KEY,
    phieu_nhap_id INTEGER NOT NULL,
    mat_hang_id INTEGER NOT NULL,
    so_luong INTEGER NOT NULL,
    don_gia_thuc INTEGER,
    tong_gia INTEGER,
    UNIQUE (phieu_nhap_id, mat_hang_id),
    CONSTRAINT ck_chi_tiet_phieu_nhap_01 CHECK (so_luong > 0)
);

CREATE TABLE phieu_xuat (
    id INTEGER PRIMARY KEY,
    ma_phieu_xuat VARCHAR NOT NULL UNIQUE,
    nhan_vien_id INTEGER,
    loai_phieu VARCHAR NOT NULL,
    yeu_cau_san_xuat_id INTEGER,
    lenh_san_xuat_id INTEGER,
    tong_tien INTEGER,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    created_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_phieu_xuat_01 CHECK (trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')),
    CONSTRAINT ck_phieu_xuat_02 CHECK (loai_phieu IN ('xuat_vat_tu', 'xuat_thanh_pham')),
    CONSTRAINT ck_phieu_xuat_03 CHECK ((loai_phieu = 'xuat_vat_tu' AND lenh_san_xuat_id IS NOT NULL AND yeu_cau_san_xuat_id IS NULL) OR (loai_phieu = 'xuat_thanh_pham' AND yeu_cau_san_xuat_id IS NOT NULL AND lenh_san_xuat_id IS NULL)),
    CONSTRAINT ck_phieu_xuat_04 CHECK (ma_phieu_xuat ~ '^PX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu_xuat, 6) <> '000000')
);

CREATE TABLE chi_tiet_phieu_xuat (
    id INTEGER PRIMARY KEY,
    phieu_xuat_id INTEGER NOT NULL,
    mat_hang_id INTEGER NOT NULL,
    so_luong INTEGER NOT NULL,
    don_gia_thuc INTEGER,
    tong_gia INTEGER,
    UNIQUE (phieu_xuat_id, mat_hang_id),
    CONSTRAINT ck_chi_tiet_phieu_xuat_01 CHECK (so_luong > 0)
);

CREATE TABLE yeu_cau_san_xuat (
    id INTEGER PRIMARY KEY,
    ma_yeu_cau_san_xuat VARCHAR NOT NULL UNIQUE,
    mat_hang_id INTEGER NOT NULL,
    so_luong INTEGER NOT NULL,
    nhan_vien_id INTEGER NOT NULL,
    nhan_vien_duoc_giao_id INTEGER,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_yeu_cau_san_xuat_01 CHECK (trang_thai IN ('nhap', 'da_gui', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')),
    CONSTRAINT ck_yeu_cau_san_xuat_02 CHECK (so_luong > 0),
    CONSTRAINT ck_yeu_cau_san_xuat_03 CHECK (ma_yeu_cau_san_xuat ~ '^YCSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_yeu_cau_san_xuat, 6) <> '000000')
);

CREATE TABLE lenh_san_xuat (
    id INTEGER PRIMARY KEY,
    ma_lenh_san_xuat VARCHAR NOT NULL UNIQUE,
    yeu_cau_san_xuat_id INTEGER NOT NULL,
    lenh_san_xuat_cha_id INTEGER,
    mat_hang_id INTEGER NOT NULL,
    bom_id INTEGER NOT NULL,
    so_luong INTEGER NOT NULL,
    nhan_vien_id INTEGER,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_lenh_san_xuat_01 CHECK (trang_thai IN ('nhap', 'da_gui', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')),
    CONSTRAINT ck_lenh_san_xuat_02 CHECK (so_luong > 0),
    CONSTRAINT ck_lenh_san_xuat_03 CHECK (lenh_san_xuat_cha_id IS NULL OR lenh_san_xuat_cha_id <> id),
    CONSTRAINT ck_lenh_san_xuat_04 CHECK (trang_thai NOT IN ('da_gui', 'dang_thuc_hien', 'hoan_thanh') OR nhan_vien_id IS NOT NULL),
    CONSTRAINT ck_lenh_san_xuat_05 CHECK (ma_lenh_san_xuat ~ '^LSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_lenh_san_xuat, 6) <> '000000')
);

CREATE TABLE chi_tiet_lenh_san_xuat (
    id INTEGER PRIMARY KEY,
    lenh_san_xuat_id INTEGER NOT NULL,
    mat_hang_id INTEGER NOT NULL,
    so_luong_can INTEGER NOT NULL,
    UNIQUE (lenh_san_xuat_id, mat_hang_id),
    CONSTRAINT ck_chi_tiet_lenh_san_xuat_01 CHECK (so_luong_can > 0)
);

CREATE TABLE chung_tu_hoan_thanh_sx (
    id INTEGER PRIMARY KEY,
    ma_phieu VARCHAR NOT NULL UNIQUE,
    lenh_san_xuat_id INTEGER NOT NULL,
    so_luong_hoan_thanh INTEGER NOT NULL,
    nhan_vien_id INTEGER,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    finish_time TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT ck_chung_tu_hoan_thanh_sx_01 CHECK (trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')),
    CONSTRAINT ck_chung_tu_hoan_thanh_sx_02 CHECK (so_luong_hoan_thanh > 0),
    CONSTRAINT ck_chung_tu_hoan_thanh_sx_03 CHECK (ma_phieu ~ '^HTSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu, 6) <> '000000')
);

CREATE TABLE phieu_dieu_chinh_kho (
    id INTEGER PRIMARY KEY,
    ma_phieu VARCHAR NOT NULL UNIQUE,
    nhan_vien_id INTEGER NOT NULL,
    ly_do TEXT NOT NULL,
    trang_thai VARCHAR NOT NULL DEFAULT 'nhap',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_phieu_dieu_chinh_kho_01 CHECK (trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi', 'loi')),
    CONSTRAINT ck_phieu_dieu_chinh_kho_02 CHECK (ma_phieu ~ '^DCK-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu, 6) <> '000000')
);

CREATE TABLE chi_tiet_phieu_dieu_chinh_kho (
    id INTEGER PRIMARY KEY,
    phieu_dieu_chinh_kho_id INTEGER NOT NULL,
    mat_hang_id INTEGER NOT NULL,
    giao_dich_goc_id INTEGER,
    so_luong_bien_dong INTEGER NOT NULL,
    CONSTRAINT ck_chi_tiet_phieu_dieu_chinh_kho_01 CHECK (so_luong_bien_dong <> 0)
);

CREATE TABLE ticket_loi_dieu_chinh (
    id INTEGER PRIMARY KEY,
    ma_ticket VARCHAR NOT NULL UNIQUE,
    phieu_dieu_chinh_kho_id INTEGER NOT NULL UNIQUE,
    mo_ta_loi TEXT NOT NULL,
    trang_thai VARCHAR NOT NULL DEFAULT 'cho_xu_ly',
    nguoi_xu_ly_id INTEGER,
    ket_qua_xu_ly TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_ticket_loi_dieu_chinh_01 CHECK (trang_thai IN ('cho_xu_ly', 'dang_xu_ly', 'da_xu_ly')),
    CONSTRAINT ck_ticket_loi_dieu_chinh_02 CHECK (trang_thai NOT IN ('dang_xu_ly', 'da_xu_ly') OR nguoi_xu_ly_id IS NOT NULL),
    CONSTRAINT ck_ticket_loi_dieu_chinh_03 CHECK (trang_thai <> 'da_xu_ly' OR (ket_qua_xu_ly IS NOT NULL AND btrim(ket_qua_xu_ly) <> '')),
    CONSTRAINT ck_ticket_loi_dieu_chinh_04 CHECK (ma_ticket ~ '^TKDC-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_ticket, 6) <> '000000')
);

CREATE TABLE giao_dich_kho (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    mat_hang_id INTEGER NOT NULL,
    loai_giao_dich VARCHAR NOT NULL,
    so_luong_bien_dong INTEGER NOT NULL,
    chi_tiet_phieu_nhap_id INTEGER UNIQUE,
    chi_tiet_phieu_xuat_id INTEGER UNIQUE,
    chung_tu_hoan_thanh_sx_id INTEGER UNIQUE,
    chi_tiet_phieu_dieu_chinh_id INTEGER UNIQUE,
    nhan_vien_id INTEGER NOT NULL,
    posted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_giao_dich_kho_01 CHECK (loai_giao_dich IN ('nhap_vat_tu', 'xuat_vat_tu', 'nhap_san_pham_san_xuat', 'xuat_thanh_pham', 'dieu_chinh_ton_kho')),
    CONSTRAINT ck_giao_dich_kho_02 CHECK (so_luong_bien_dong <> 0),
    CONSTRAINT ck_giao_dich_kho_03 CHECK (num_nonnulls(chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id, chung_tu_hoan_thanh_sx_id, chi_tiet_phieu_dieu_chinh_id) = 1),
    CONSTRAINT ck_giao_dich_kho_04 CHECK ((loai_giao_dich = 'nhap_vat_tu' AND chi_tiet_phieu_nhap_id IS NOT NULL AND so_luong_bien_dong > 0)
      OR (loai_giao_dich IN ('xuat_vat_tu', 'xuat_thanh_pham') AND chi_tiet_phieu_xuat_id IS NOT NULL AND so_luong_bien_dong < 0)
      OR (loai_giao_dich = 'nhap_san_pham_san_xuat' AND chung_tu_hoan_thanh_sx_id IS NOT NULL AND so_luong_bien_dong > 0)
      OR (loai_giao_dich = 'dieu_chinh_ton_kho' AND chi_tiet_phieu_dieu_chinh_id IS NOT NULL))
);

CREATE TABLE lich_su_thao_tac (
    id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nhan_vien_id INTEGER NOT NULL,
    loai_doi_tuong VARCHAR NOT NULL,
    doi_tuong_id INTEGER NOT NULL,
    thao_tac VARCHAR NOT NULL,
    du_lieu_truoc JSONB,
    du_lieu_sau JSONB,
    ly_do TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_lich_su_thao_tac_01 CHECK (loai_doi_tuong IN ('nhan_vien', 'vai_tro', 'mat_hang', 'nha_cung_cap', 'cong_thuc', 'phieu_nhap', 'phieu_xuat', 'yeu_cau_san_xuat', 'lenh_san_xuat', 'chung_tu_hoan_thanh_san_xuat', 'phieu_dieu_chinh_kho', 'phieu_loi_dieu_chinh')),
    CONSTRAINT ck_lich_su_thao_tac_02 CHECK (thao_tac IN ('tao', 'sua', 'xoa_nhap', 'gui', 'bat_dau', 'duyet', 'tu_choi', 've_nhap', 'hoan_tat', 'cap_quyen', 'thu_hoi_quyen', 'vo_hieu_hoa', 'huy', 'ghi_nhan_loi', 'nhan_xu_ly', 'mo_lai', 'giai_quyet'))
);

-- FK sau khi tạo toàn bộ bảng để xử lý quan hệ vòng điều chỉnh/giao dịch.

ALTER TABLE nhan_vien ADD FOREIGN KEY (vai_tro_id) REFERENCES vai_tro (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE ton_kho ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE bom ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_bom ADD FOREIGN KEY (bom_id) REFERENCES bom (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_bom ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_nhap ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_nhap ADD FOREIGN KEY (ncc_id) REFERENCES nha_cung_cap (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_nhap ADD FOREIGN KEY (phieu_nhap_id) REFERENCES phieu_nhap (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_nhap ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_xuat ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_xuat ADD FOREIGN KEY (yeu_cau_san_xuat_id) REFERENCES yeu_cau_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_xuat ADD FOREIGN KEY (lenh_san_xuat_id) REFERENCES lenh_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_xuat ADD FOREIGN KEY (phieu_xuat_id) REFERENCES phieu_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_xuat ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE yeu_cau_san_xuat ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE yeu_cau_san_xuat ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE yeu_cau_san_xuat ADD FOREIGN KEY (nhan_vien_duoc_giao_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lenh_san_xuat ADD FOREIGN KEY (yeu_cau_san_xuat_id) REFERENCES yeu_cau_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lenh_san_xuat ADD FOREIGN KEY (lenh_san_xuat_cha_id) REFERENCES lenh_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lenh_san_xuat ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lenh_san_xuat ADD FOREIGN KEY (bom_id) REFERENCES bom (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lenh_san_xuat ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_lenh_san_xuat ADD FOREIGN KEY (lenh_san_xuat_id) REFERENCES lenh_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_lenh_san_xuat ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chung_tu_hoan_thanh_sx ADD FOREIGN KEY (lenh_san_xuat_id) REFERENCES lenh_san_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chung_tu_hoan_thanh_sx ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE phieu_dieu_chinh_kho ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_dieu_chinh_kho ADD FOREIGN KEY (phieu_dieu_chinh_kho_id) REFERENCES phieu_dieu_chinh_kho (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_dieu_chinh_kho ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE chi_tiet_phieu_dieu_chinh_kho ADD FOREIGN KEY (giao_dich_goc_id) REFERENCES giao_dich_kho (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE ticket_loi_dieu_chinh ADD FOREIGN KEY (phieu_dieu_chinh_kho_id) REFERENCES phieu_dieu_chinh_kho (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE ticket_loi_dieu_chinh ADD FOREIGN KEY (nguoi_xu_ly_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (mat_hang_id) REFERENCES mat_hang (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (chi_tiet_phieu_nhap_id) REFERENCES chi_tiet_phieu_nhap (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (chi_tiet_phieu_xuat_id) REFERENCES chi_tiet_phieu_xuat (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (chung_tu_hoan_thanh_sx_id) REFERENCES chung_tu_hoan_thanh_sx (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (chi_tiet_phieu_dieu_chinh_id) REFERENCES chi_tiet_phieu_dieu_chinh_kho (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE giao_dich_kho ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE lich_su_thao_tac ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien (id) ON UPDATE NO ACTION ON DELETE NO ACTION;

-- Một BOM hiện hành cho mỗi mặt hàng; NULL/false không được xem là hiện hành.
CREATE UNIQUE INDEX uq_bom_hien_hanh ON bom (mat_hang_id) WHERE is_active IS TRUE;

CREATE INDEX ix_giao_dich_kho_1 ON giao_dich_kho (mat_hang_id, posted_at);
CREATE INDEX ix_lich_su_thao_tac_1 ON lich_su_thao_tac (loai_doi_tuong, doi_tuong_id, created_at);
CREATE INDEX ix_lich_su_thao_tac_2 ON lich_su_thao_tac (nhan_vien_id, created_at);

-- Bảo vệ sổ kho và audit khỏi UPDATE/DELETE/TRUNCATE thông thường.
CREATE FUNCTION chan_sua_xoa_lich_su() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Bang % chi cho phep them moi; khong duoc %', TG_TABLE_NAME, TG_OP;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_bao_ve_giao_dich_kho BEFORE UPDATE OR DELETE OR TRUNCATE ON giao_dich_kho
FOR EACH STATEMENT EXECUTE FUNCTION chan_sua_xoa_lich_su();
CREATE TRIGGER trg_bao_ve_lich_su_thao_tac BEFORE UPDATE OR DELETE OR TRUNCATE ON lich_su_thao_tac
FOR EACH STATEMENT EXECUTE FUNCTION chan_sua_xoa_lich_su();

-- Ghi chú nghiệp vụ từ DBML v3.

COMMENT ON COLUMN nhan_vien.tai_khoan_id IS 'Giữ từ model gốc; chưa có bảng tai_khoan để khai báo FK.';
COMMENT ON COLUMN nhan_vien.ma_nhan_vien IS 'Định dạng: NV-NNNNNN. Ví dụ: NV-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN nhan_vien.loai_nhan_vien IS 'Miền giá trị: nhan_vien / quan_ly / quan_tri_vien.';
COMMENT ON COLUMN vai_tro.ma_vai_tro IS 'Mã cố định, snake_case tiếng Việt không dấu: nhan_vien / quan_ly / quan_tri_vien. Dùng cho phân quyền; không đổi theo tên hiển thị.';
COMMENT ON COLUMN vai_tro.ten_vai_tro IS 'Tên hiển thị có dấu: Nhân viên / Quản lý / Quản trị viên. Có thể đổi tên hiển thị mà không đổi ma_vai_tro.';
COMMENT ON COLUMN mat_hang.ma_mat_hang IS 'Định dạng: MH-NNNNNN. Ví dụ: MH-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN mat_hang.loai_mat_hang IS 'Miền giá trị: nguyen_vat_lieu / linh_kien / ban_thanh_pham / thanh_pham.';
COMMENT ON COLUMN mat_hang.don_vi_tinh IS 'Danh mục mở, mã snake_case không dấu; ví dụ: chiec / bo / met / kilogam.';
COMMENT ON COLUMN mat_hang.mau_sac IS 'Danh mục mở, mã snake_case không dấu; ví dụ: do / tim / vang / den / trang.';
COMMENT ON TABLE mat_hang IS 'loai_mat_hang: nguyen_vat_lieu / linh_kien / ban_thanh_pham / thanh_pham.';
COMMENT ON TABLE ton_kho IS 'CHECK (so_luong >= 0). Chỉ cập nhật qua nghiệp vụ ghi sổ trong transaction.';
COMMENT ON TABLE bom IS 'Mỗi BOM mô tả một đơn vị đầu ra; version > 0.
    Mỗi mặt hàng chỉ có tối đa một BOM hiện hành.
    BOM và chi tiết đã được lệnh sử dụng không được sửa/xóa; tạo version mới.
    Không cho phép chu trình trực tiếp hoặc gián tiếp trong cấu trúc BOM.
    BOM con được chọn và khóa bằng bom_id của từng lệnh con.';
COMMENT ON TABLE chi_tiet_bom IS 'CHECK (so_luong > 0). Thành phần có thể là NVL, linh_kien hoặc bán thành phẩm có BOM riêng.';
COMMENT ON COLUMN nha_cung_cap.ma_ncc IS 'Định dạng: NCC-NNNNNN. Ví dụ: NCC-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN phieu_nhap.ma_phieu_nhap IS 'Định dạng: PN-YYYYMM-NNNNNN. Ví dụ: PN-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN phieu_nhap.trang_thai IS 'Miền giá trị: nhap / hoan_thanh.';
COMMENT ON TABLE phieu_nhap IS 'Trạng thái: nhap / hoan_thanh.
    nhap: được sửa/xóa, chưa cộng kho.
    nhap -> hoan_thanh: xác nhận hoàn tất, cộng kho và ghi giao dịch cùng transaction.
    hoan_thanh: không sửa/xóa; thay đổi lượng phải qua phiếu điều chỉnh.
    Hoàn tất thất bại: rollback, giữ nhap; không tồn tại nhập kho dở dang.';
COMMENT ON TABLE chi_tiet_phieu_nhap IS 'CHECK (so_luong > 0).';
COMMENT ON COLUMN phieu_xuat.ma_phieu_xuat IS 'Định dạng: PX-YYYYMM-NNNNNN. Ví dụ: PX-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN phieu_xuat.loai_phieu IS 'Miền giá trị: xuat_vat_tu / xuat_thanh_pham. Vật tư gồm NVL, linh kiện và bán thành phẩm cấp cho sản xuất.';
COMMENT ON COLUMN phieu_xuat.yeu_cau_san_xuat_id IS 'Nguồn nhu cầu khi xuất thành phẩm.';
COMMENT ON COLUMN phieu_xuat.lenh_san_xuat_id IS 'Nguồn cấp vật tư khi xuất cho sản xuất.';
COMMENT ON COLUMN phieu_xuat.trang_thai IS 'Miền giá trị: nhap / cho_duyet / da_duyet / tu_choi.';
COMMENT ON TABLE phieu_xuat IS 'loai_phieu: xuat_vat_tu / xuat_thanh_pham.
    xuat_vat_tu: lenh_san_xuat_id bắt buộc, yeu_cau_san_xuat_id NULL.
    xuat_thanh_pham: yeu_cau_san_xuat_id bắt buộc, lenh_san_xuat_id NULL.
    Mỗi phiếu phục vụ đúng một yêu cầu hoặc một lệnh.
    Trạng thái: nhap / cho_duyet / da_duyet / tu_choi.
    nhap -> cho_duyet: gửi, chưa trừ tồn.
    cho_duyet -> da_duyet: kiểm tra lại đủ tồn và giới hạn cấp/xuất;
    trừ kho, ghi giao dịch, cập nhật phiếu cùng transaction.
    cho_duyet -> tu_choi: từ chối, lý do lưu audit, không đổi tồn.
    tu_choi -> nhap: sửa và gửi lại, lưu audit.
    da_duyet: bất biến; sửa lượng bằng phiếu điều chỉnh.
    Lỗi khi duyệt: rollback, giữ cho_duyet.';
COMMENT ON TABLE chi_tiet_phieu_xuat IS 'CHECK (so_luong > 0). Xuất vật tư phải thuộc nhu cầu trực tiếp của lệnh; xuất thành phẩm phải khớp mặt hàng của yêu cầu.';
COMMENT ON COLUMN yeu_cau_san_xuat.ma_yeu_cau_san_xuat IS 'Định dạng: YCSX-YYYYMM-NNNNNN. Ví dụ: YCSX-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN yeu_cau_san_xuat.mat_hang_id IS 'Thành phẩm cần đáp ứng.';
COMMENT ON COLUMN yeu_cau_san_xuat.so_luong IS 'Tổng lượng thành phẩm cần xuất, không phải lượng cần sản xuất.';
COMMENT ON COLUMN yeu_cau_san_xuat.nhan_vien_id IS 'Người tạo yêu cầu.';
COMMENT ON COLUMN yeu_cau_san_xuat.nhan_vien_duoc_giao_id IS 'Người phụ trách đáp ứng yêu cầu, kể cả nhánh đủ tồn.';
COMMENT ON COLUMN yeu_cau_san_xuat.trang_thai IS 'Miền giá trị: nhap / da_gui / dang_thuc_hien / hoan_thanh / da_huy.';
COMMENT ON TABLE yeu_cau_san_xuat IS 'CHECK (so_luong > 0). Không lưu bom_id ở yêu cầu.
    Trạng thái: nhap / da_gui / dang_thuc_hien / hoan_thanh / da_huy.
    nhap: nhập nhu cầu, kiểm tra tồn và tính thử; chưa thay đổi kho.
    nhap -> da_gui: giao người phụ trách; lưu kế hoạch lệnh nếu thiếu thành phẩm.
    da_gui -> dang_thuc_hien: bắt đầu xử lý bằng lệnh sản xuất hoặc phiếu xuất thành phẩm.
    dang_thuc_hien -> hoan_thanh: lượng xuất thành phẩm đã ghi sổ đạt so_luong.
    Có thể hoàn tất trực tiếp từ da_gui khi xuất đủ hàng sẵn có.
    Lượng sản xuất dự kiến = max(so_luong - tồn thành phẩm lúc lập kế hoạch, 0).
    Nếu đủ thành phẩm: không tạo lệnh, đi thẳng đến phiếu xuất thành phẩm.
    Không giữ chỗ; kết quả tính là ảnh chụp, phải kiểm tra lại khi duyệt xuất.
    da_huy: chỉ hủy khi chưa phát sinh ghi sổ và đã hủy các lệnh/phiếu chưa ghi sổ.
    Yêu cầu có chứng từ đã ghi sổ không được sửa/xóa trực tiếp.
    Sản xuất xong chưa đồng nghĩa yêu cầu hoàn thành.';
COMMENT ON COLUMN lenh_san_xuat.ma_lenh_san_xuat IS 'Định dạng: LSX-YYYYMM-NNNNNN. Ví dụ: LSX-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN lenh_san_xuat.lenh_san_xuat_cha_id IS 'NULL: lệnh gốc; có giá trị: lệnh sản xuất bán thành phẩm.';
COMMENT ON COLUMN lenh_san_xuat.mat_hang_id IS 'Đầu ra của riêng lệnh này.';
COMMENT ON COLUMN lenh_san_xuat.bom_id IS 'Phiên bản BOM của đầu ra này, gồm cả lệnh con.';
COMMENT ON COLUMN lenh_san_xuat.so_luong IS 'Lượng thực tế cần sản xuất.';
COMMENT ON COLUMN lenh_san_xuat.nhan_vien_id IS 'Người thực hiện; bắt buộc khi gửi lệnh.';
COMMENT ON COLUMN lenh_san_xuat.trang_thai IS 'Miền giá trị: nhap / da_gui / dang_thuc_hien / hoan_thanh / da_huy.';
COMMENT ON TABLE lenh_san_xuat IS 'CHECK (so_luong > 0). BOM phải thuộc đúng mat_hang_id.
    Trạng thái: nhap / da_gui / dang_thuc_hien / hoan_thanh / da_huy.
    nhap -> da_gui: chốt BOM, lượng và bản chụp nhu cầu; giao nhân viên.
    da_gui -> dang_thuc_hien: đủ vật tư đã cấp bằng phiếu xuất da_duyet.
    dang_thuc_hien -> hoan_thanh: tổng đầu ra đã duyệt đạt so_luong.
    da_huy: chỉ khi chưa có cấp vật tư/đầu ra đã ghi sổ, không còn lệnh con hoạt động.
    Bắt đầu/hoàn thành lệnh không tự ghi kho; kho thay đổi qua chứng từ được duyệt.
    Mỗi lệnh con thuộc cùng yêu cầu với lệnh cha; không cho chu trình lệnh.
    Đầu ra lệnh con phải thuộc nhu cầu trực tiếp của lệnh cha.
    Lệnh gốc phải có cùng mặt hàng với yêu cầu.
    Một lệnh con phục vụ một lệnh cha; không chia sẻ lệnh con giữa nhiều cha.
    Tạo lệnh con chỉ cho phần bán thành phẩm còn thiếu sau khi tính lượng có sẵn.
    Khi nhiều nhánh cùng cần một mặt hàng, phân bổ tồn trong phép tính kế hoạch
    để không tính dùng cùng một lượng tồn hai lần; đây không phải giữ chỗ kho.
    Đầu ra lệnh con phải được duyệt nhập kho trước khi xuất cho lệnh cha.
    Kế hoạch đã gửi không được tự động tính lại theo BOM mới hoặc tồn mới.';
COMMENT ON TABLE chi_tiet_lenh_san_xuat IS 'CHECK (so_luong_can > 0).
    Bản chụp nhu cầu TRỰC TIẾP: định mức BOM đã chốt * lượng của lệnh.
    Lệnh xe lưu cụm bánh; lệnh cụm bánh lưu vành, moay-ơ, nan hoa.
    Không gộp linh kiện của lệnh con vào nhu cầu lệnh cha, tránh cấp/trừ hai lần.
    Ví dụ lệnh cha cần 20 cụm, kho có 8: nhu cầu cha vẫn là 20 cụm;
    tạo lệnh con 12 cụm với bom_id riêng và nhu cầu linh kiện cho 12 cụm.
    Nhu cầu bất biến sau khi gửi; BOM đã dùng cũng bất biến.
    Tổng vật tư đã cấp, tính cả điều chỉnh đã ghi sổ, không vượt nhu cầu của lệnh.';
COMMENT ON COLUMN chung_tu_hoan_thanh_sx.ma_phieu IS 'Định dạng: HTSX-YYYYMM-NNNNNN. Ví dụ: HTSX-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN chung_tu_hoan_thanh_sx.lenh_san_xuat_id IS 'Thay FK yêu cầu; không UNIQUE để cho phép nhiều đợt.';
COMMENT ON COLUMN chung_tu_hoan_thanh_sx.trang_thai IS 'Miền giá trị: nhap / cho_duyet / da_duyet / tu_choi.';
COMMENT ON TABLE chung_tu_hoan_thanh_sx IS 'CHECK (so_luong_hoan_thanh > 0).
    Trạng thái: nhap / cho_duyet / da_duyet / tu_choi.
    nhap -> cho_duyet: gửi, chưa cộng kho.
    cho_duyet -> da_duyet: cộng đầu ra của lệnh, không trừ lại vật tư.
    cho_duyet -> tu_choi: không đổi tồn; lý do lưu audit.
    tu_choi -> nhap: sửa/gửi lại; da_duyet bất biến.
    Một chứng từ ghi nhận một đợt, một loại đầu ra, một giao dịch kho.
    Tổng lượng hoàn thành đã duyệt, tính cả điều chỉnh, không vượt so_luong lệnh
    và phải phù hợp vật tư đã cấp. Khóa lệnh khi kiểm tra tổng lượng.
    Lỗi khi duyệt: rollback, giữ cho_duyet.';
COMMENT ON COLUMN phieu_dieu_chinh_kho.ma_phieu IS 'Định dạng: DCK-YYYYMM-NNNNNN. Ví dụ: DCK-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project.';
COMMENT ON COLUMN phieu_dieu_chinh_kho.nhan_vien_id IS 'Người tạo.';
COMMENT ON COLUMN phieu_dieu_chinh_kho.trang_thai IS 'Miền giá trị: nhap / cho_duyet / da_duyet / tu_choi / loi.';
COMMENT ON TABLE phieu_dieu_chinh_kho IS 'Trạng thái: nhap / cho_duyet / da_duyet / tu_choi / loi.
    nhap -> cho_duyet: xác nhận gửi; chưa đổi kho.
    cho_duyet -> da_duyet: quản lý duyệt khi mọi dòng đều hợp lệ.
    cho_duyet -> tu_choi: quản lý từ chối; không đổi kho, lý do lưu audit.
    tu_choi -> nhap: sửa/gửi lại có audit.
    da_duyet: bất biến; không sửa chứng từ/giao dịch nguồn đã ghi sổ.
    Mỗi dòng lưu lượng chênh lệch có dấu, không phải tồn cuối cùng.
    Duyệt nguyên phiếu: khóa phiếu, tồn và đối tượng liên quan theo thứ tự thống nhất;
    kiểm tra đủ tồn, lượng nguồn sau điều chỉnh và vật tư/đầu ra/xuất đã ghi nhận.
    Ghi giao dịch điều chỉnh, cập nhật tồn, trạng thái nghiệp vụ bị tác động và audit
    trong CÙNG transaction. Không duyệt một phần phiếu.
    Nếu bất kỳ dòng nào không hợp lệ hoặc ghi sổ lỗi: ROLLBACK toàn bộ transaction này.
    Sau rollback: transaction RIÊNG khóa lại phiếu, kiểm tra chưa được duyệt bởi
    tiến trình khác, chuyển loi, tạo/reopen ticket và ghi audit; không đổi tồn.
    loi chặn tự động thử lại; người có quyền xử lý thủ công -> nhap để sửa/gửi lại,
    hoặc -> tu_choi để dừng. Không được sửa trực tiếp số dư hay giao dịch cũ.
    Một yêu cầu duyệt lặp của phiếu da_duyet trả kết quả cũ, không tạo ticket/ghi sổ lại.
    Nếu CSDL không dùng được để lưu ticket, ứng dụng phải lưu sự cố bền vững và
    thử lưu ticket khi phục hồi; không báo đã tạo ticket khi chưa lưu thành công.';
COMMENT ON COLUMN chi_tiet_phieu_dieu_chinh_kho.giao_dich_goc_id IS 'NULL khi điều chỉnh kiểm kê không gắn chứng từ.';
COMMENT ON TABLE chi_tiet_phieu_dieu_chinh_kho IS 'CHECK (so_luong_bien_dong <> 0). Dương: cộng; âm: trừ.
    Sai lượng chứng từ đã ghi sổ: bắt buộc giao_dich_goc_id;
    giao dịch gốc phải cùng mặt hàng và không thuộc loại dieu_chinh_ton_kho.
    Kiểm kê độc lập có thể không có giao dịch gốc; lý do phải ghi rõ phạm vi.
    Ví dụ nhập +100 nhưng đúng là +90: thêm điều chỉnh -10 trỏ giao dịch nhập +100.
    Xét tổng các điều chỉnh đã duyệt của nguồn khi kiểm tra, không chỉ dòng hiện tại.
    Không đảo dấu nghiệp vụ gốc và không làm lượng hiệu lực vượt giới hạn liên quan.
    Đối với vật tư/đầu ra, phải bảo toàn quan hệ lượng đã cấp, đã hoàn thành và nhu cầu.
    Điều chỉnh khiến điều kiện bắt đầu/hoàn thành không còn đúng phải cập nhật trạng thái
    hợp lệ cùng transaction; nếu chứng từ phụ thuộc không cho phép thì rollback + ticket.';
COMMENT ON COLUMN ticket_loi_dieu_chinh.ma_ticket IS 'Định dạng: TKDC-YYYYMM-NNNNNN. Ví dụ: TKDC-202610-000001. Áp dụng quy ước mã nghiệp vụ chung của Project; mở lại ticket giữ nguyên mã.';
COMMENT ON COLUMN ticket_loi_dieu_chinh.trang_thai IS 'Miền giá trị: cho_xu_ly / dang_xu_ly / da_xu_ly.';
COMMENT ON TABLE ticket_loi_dieu_chinh IS 'Trạng thái: cho_xu_ly / dang_xu_ly / da_xu_ly.
    cho_xu_ly: lỗi điều chỉnh đã rollback, chờ xử lý thủ công.
    cho_xu_ly -> dang_xu_ly: người xử lý nhận ticket; nguoi_xu_ly_id bắt buộc.
    dang_xu_ly -> da_xu_ly: đã xử lý nguyên nhân và phiếu được duyệt thành công
    hoặc đã từ chối dừng điều chỉnh; bắt buộc ket_qua_xu_ly và lưu audit.
    Sửa phiếu về nhap chưa tự đóng ticket.
    Một ticket cho mỗi phiếu; thất bại lại thì reopen/cập nhật ticket hiện có,
    lưu từng lần lỗi và xử lý trong audit để không mất lịch sử.
    Mô tả lỗi ghi rõ dòng/mặt hàng, lượng điều chỉnh và điều kiện không đạt.
    Ticket không tự động làm thay đổi kho và không cho phép bỏ qua ràng buộc tồn.';
COMMENT ON COLUMN giao_dich_kho.loai_giao_dich IS 'nhap_vat_tu / xuat_vat_tu / nhap_san_pham_san_xuat / xuat_thanh_pham / dieu_chinh_ton_kho';
COMMENT ON TABLE giao_dich_kho IS 'CHECK (so_luong_bien_dong <> 0). Đúng một trong BỐN FK nguồn khác NULL.
    Loại giao dịch phải đúng loại nguồn; mặt hàng và lượng khớp chứng từ nguồn.
    nhap_vat_tu / nhap_san_pham_san_xuat: dương.
    xuat_vat_tu / xuat_thanh_pham: âm.
    dieu_chinh_ton_kho: có thể dương hoặc âm, nguồn là dòng điều chỉnh.
    UNIQUE FK nguồn ngăn ghi sổ cùng một dòng/đợt hai lần.
    Chỉ ghi khi nhập hoan_thanh hoặc chứng từ xuất/hoàn thành/điều chỉnh da_duyet.
    Ghi giao dịch, cập nhật tồn, trạng thái và audit cùng transaction.
    Không sửa/xóa giao dịch đã ghi sổ.
    Lượng hiệu lực của giao dịch nguồn = lượng gốc + tổng điều chỉnh đã ghi sổ trỏ nguồn.
    Khi đối soát số dư, cộng mọi giao dịch đúng một lần, gồm cả giao dịch điều chỉnh.';
COMMENT ON COLUMN lich_su_thao_tac.loai_doi_tuong IS 'nhan_vien / vai_tro / mat_hang / nha_cung_cap / cong_thuc / phieu_nhap / phieu_xuat / yeu_cau_san_xuat / lenh_san_xuat / chung_tu_hoan_thanh_san_xuat / phieu_dieu_chinh_kho / phieu_loi_dieu_chinh';
COMMENT ON COLUMN lich_su_thao_tac.thao_tac IS 'tao / sua / xoa_nhap / gui / bat_dau / duyet / tu_choi / ve_nhap / hoan_tat / cap_quyen / thu_hoi_quyen / vo_hieu_hoa / huy / ghi_nhan_loi / nhan_xu_ly / mo_lai / giai_quyet';
COMMENT ON TABLE lich_su_thao_tac IS 'Chỉ thêm, không sửa/xóa lịch sử. Backend kiểm tra tham chiếu đa hình.
    Mã loai_doi_tuong: cong_thuc -> bảng bom;
    chung_tu_hoan_thanh_san_xuat -> bảng chung_tu_hoan_thanh_sx;
    phieu_loi_dieu_chinh -> bảng ticket_loi_dieu_chinh; mã còn lại trùng tên bảng.
    Lưu người và thời điểm gửi/duyệt/từ chối, trạng thái, lý do và dòng chi tiết.
    Không cần nhân đôi cột người duyệt/lý do ở mọi bảng cho phạm vi model này.
    Audit thành công ghi cùng transaction nghiệp vụ.
    Audit lỗi điều chỉnh ghi trong transaction tạo/reopen ticket SAU rollback.
    Người ghi audit lỗi tự động là người yêu cầu duyệt phiếu tương ứng.
    Không lưu mật khẩu, hash hoặc token trong JSON.';

COMMIT;
