# Entity Model — xBike MRP (giai đoạn 1)

Nguồn: `specs/business_requirements/BR-GIAIDOAN1.md` (BR-001 … BR-016), `specs/use_cases/` (UC-01 … UC-44), `specs/entity_model/data_model_v4.md` (đã chốt 13/11/2026).
Tên entity trùng tên bảng (PascalCase), tên thuộc tính snake_case. Tiền là VND (số nguyên). Thời điểm có múi giờ; kỳ báo cáo theo giờ Việt Nam.

## VaiTro

- id, ma_vai_tro, ten_vai_tro, mo_ta
- ma_vai_tro ("quan_tri_vien" | "quan_ly" | "nhan_vien")
- Ba dòng cố định tạo sẵn khi cài đặt; không thêm, sửa, xóa vai trò
- Có nhiều: NhanVien

## NhanVien

- id, ma_nhan_vien (NV-xxxxxx), ten_dang_nhap (duy nhất), mat_khau (hash), vai_tro_id
- ho_ten, so_dien_thoai, email, ngay_sinh, ngay_vao_lam, he_so_luong (không bắt buộc; BR không dùng)
- trang_thai ("hoat_dong" | "bi_khoa"), mặc định "hoat_dong"
- phien_ban_dang_nhap: tăng 1 khi khóa, đổi vai trò, đổi mật khẩu → mọi phiên đang đăng nhập kết thúc ngay
- created_at
- Mật khẩu tối thiểu 6 ký tự; chỉ Quản trị viên đổi, không cần mật khẩu hiện tại
- Khóa thay cho xóa; khóa, mở khóa, đổi vai trò không bắt buộc ghi lý do (nếu nhập thì lưu vào LichSuThaoTac.ly_do)
- Luôn còn ít nhất 1 Quản trị viên "hoat_dong"; Quản trị viên đầu tiên tạo sẵn khi cài đặt
- Không đổi vai trò khi đang được giao YeuCauSanXuat ở "nhap" | "da_gui" | "cho_bo_sung_linh_kien" | "dang_thuc_hien"
- Một VaiTro có nhiều NhanVien; một NhanVien lập/được giao/duyệt nhiều chứng từ

## NhaCungCap

- id, ma_ncc (NCC-xxxxxx, duy nhất, hệ thống cấp khi tạo, không sửa), ten_ncc (bắt buộc)
- so_dien_thoai, dia_chi (số nhà, đường), phuong, tinh: đều bắt buộc, không được null; địa chỉ là thuộc tính của NhaCungCap, nhập tay, hệ thống không kiểm tra tính chính xác
- created_at
- Tạo và sửa được (sửa mọi thông tin trừ ma_ncc), không xóa; sửa ghi lịch sử kèm giá trị trước/sau; lưu không thay đổi thì không ghi lịch sử
- PhieuNhap chỉ lưu ncc_id: mọi phiếu, kể cả đã hoàn tất, hiển thị thông tin nhà cung cấp hiện tại
- Chỉ QLK tạo, sửa; QTV chỉ xem; Nhân viên không xem nhà cung cấp
- Có nhiều: PhieuNhap

## MatHang

- id, ma_mat_hang (MH-xxxxxx, duy nhất, hệ thống cấp khi tạo, không sửa), ten_mat_hang, sku (duy nhất)
- loai_mat_hang ("thanh_pham" | "linh_kien"), không đổi sau khi tạo
- don_vi_tinh (không đổi khi đã dùng trong công thức hoặc chứng từ), don_gia (VND), mau_sac, mo_ta
- is_active: chỉ thành phẩm được ngừng; linh kiện luôn đang dùng
- so_luong_ton (tồn thực tế), so_luong_dang_giu, so_luong_con_dung = ton − dang_giu
- ton_kho_updated_at, created_at
- Tồn chỉ đổi qua chứng từ đã ghi nhận vào kho (kèm GiaoDichKho), không sửa tay; tồn không bao giờ âm
- Thành phẩm đang dùng ⇔ có một phiên bản Bom đang dùng
- Tạo thành phẩm phải tạo kèm Bom phiên bản 1 trong cùng lần lưu
- Danh mục ban đầu: 4 thành phẩm (Mountain Pro, City Ride, Speed Sport, Kids Fun), 10 linh kiện (Khung xe, Phuộc xe, Cụm bánh xe, Lốp xe, Xích xe, Bàn đạp, Dây phanh, Yên xe, Đĩa xích, Bộ ốc vít)
- Có nhiều: Bom (thành phẩm), ChiTietBom (linh kiện), dòng chứng từ, GiuHang, GiaoDichKho

## Bom

- id, mat_hang_id (thành phẩm), version
- is_active: mỗi thành phẩm tối đa một phiên bản đang dùng
- created_at, kich_hoat_gan_nhat_at (lần gần nhất trở thành đang dùng)
- Mỗi dòng là một phiên bản công thức; phiên bản không bao giờ sửa
- Sửa công thức = tạo phiên bản mới, thay phiên bản cũ ngay; có thể dùng lại phiên bản cũ
- Ngừng công thức ⇒ ngừng thành phẩm và ngược lại; dùng lại thành phẩm ⇒ kích hoạt lại phiên bản có kich_hoat_gan_nhat_at lớn nhất
- Một MatHang (thành phẩm) có nhiều Bom; một Bom có nhiều ChiTietBom

## ChiTietBom

- id, bom_id, mat_hang_id (linh kiện), so_luong (định mức cho 1 xe, số nguyên > 0)
- Không lặp linh kiện trong một phiên bản; công thức một cấp, chỉ gồm linh kiện

## PhieuNhap

- id, ma_phieu_nhap (PN-YYYYMM-xxxxxx), nhan_vien_id (QLK lập), ncc_id
- ngay_nhap, ghi_chu, tong_tien
- trang_thai ("nhap" | "hoan_thanh")
- created_at, updated_at, hoan_thanh_at, nguoi_hoan_thanh_id
- phien_ban (khóa lạc quan, BR-015)
- Sửa, xóa chỉ khi "nhap"; hoàn tất cần xác nhận, cộng tồn đúng một lần; đã hoàn tất thì không sửa, không xóa
- Không gắn với YeuCauSanXuat; hoàn tất không làm đổi yêu cầu sản xuất
- Có nhiều: ChiTietPhieuNhap

## ChiTietPhieuNhap

- id, phieu_nhap_id, mat_hang_id (chỉ linh kiện), so_luong (> 0)
- don_gia_thuc (đơn giá nhập thực tế, VND), tong_gia = so_luong × don_gia_thuc
- Mỗi linh kiện xuất hiện một lần trong phiếu

## YeuCauSanXuat

- id, ma_yeu_cau_san_xuat (YCSX-YYYYMM-xxxxxx), mat_hang_id (thành phẩm), so_luong (> 0)
- han_hoan_thanh (ngày; chỉ để theo dõi, sắp xếp), nhan_vien_id (QLK lập), nhan_vien_duoc_giao_id (đúng một nhân viên)
- trang_thai ("nhap" | "da_gui" | "cho_bo_sung_linh_kien" | "dang_thuc_hien" | "hoan_thanh" | "da_huy")
- bom_id: phiên bản công thức chốt lúc gửi, không đổi sau đó
- so_luong_dung_thanh_pham, so_luong_can_san_xuat: chốt ở lần kiểm tra đầu; tổng = so_luong
- created_at, updated_at, gui_at, kiem_tra_lan_dau_at, started_at (bắt đầu sản xuất), completed_at
- huy_at, nguoi_huy_id, ly_do_huy
- phien_ban (khóa lạc quan)
- Yêu cầu sản xuất kiêm lệnh sản xuất, không có lệnh riêng
- Chỉ lập cho thành phẩm đang dùng; gửi khi có hạn, nhân viên được giao đang hoạt động, thành phẩm đang dùng
- Sửa, xóa chỉ khi "nhap"; sau khi gửi không đổi thành phẩm, số lượng, nhân viên, hạn
- Bắt đầu sản xuất (ghi started_at, tồn không đổi): chỉ sau khi phiếu xuất linh kiện được duyệt
- Hủy: chỉ QLK, bắt buộc lý do, chỉ khi chưa có PhieuXuat nào "da_duyet"; trả toàn bộ GiuHang, tồn thực tế không đổi
- Có nhiều: NhuCauLinhKien, GiuHang, PhieuXuat (tối đa 1 mỗi loại); có tối đa 1 ChungTuHoanThanhSx

## NhuCauLinhKien

- id, yeu_cau_san_xuat_id, mat_hang_id (linh kiện), so_luong_can
- so_luong_can = định mức (ChiTietBom của bom_id đã chốt) × so_luong_can_san_xuat
- Chụp một lần ở lần kiểm tra đầu, không sửa; chỉ có khi so_luong_can_san_xuat > 0
- Dùng cho: kiểm tra lại, nhu cầu bổ sung linh kiện, nội dung phiếu xuất linh kiện

## GiuHang

- id, yeu_cau_san_xuat_id, mat_hang_id
- loai_giu ("thanh_pham_co_san" | "linh_kien" | "thanh_pham_san_xuat")
- so_luong (> 0)
- trang_thai ("dang_giu" | "da_xuat" | "da_tra")
- chung_tu_hoan_thanh_sx_id (khi loai_giu = "thanh_pham_san_xuat"), phieu_xuat_id (khi "da_xuat")
- created_at, ket_thuc_at
- Kiểm tra: giữ thành phẩm có sẵn; giữ toàn bộ linh kiện chỉ khi đủ tất cả, thiếu thì không giữ linh kiện nào
- Duyệt chứng từ hoàn thành: tạo dòng "thanh_pham_san_xuat"
- Duyệt phiếu xuất: các dòng tương ứng → "da_xuat"; hủy yêu cầu: mọi dòng "dang_giu" → "da_tra"
- Từ chối phiếu xuất không đổi phần giữ
- Tổng các dòng "dang_giu" của một mặt hàng = MatHang.so_luong_dang_giu

## PhieuXuat

- id, ma_phieu_xuat (PX-YYYYMM-xxxxxx), nhan_vien_id (NV được giao lập), yeu_cau_san_xuat_id
- loai_phieu ("xuat_linh_kien" | "xuat_thanh_pham")
- tong_tien (ghi lúc duyệt)
- trang_thai ("nhap" | "cho_duyet" | "da_duyet" | "tu_choi")
- created_at, updated_at, gui_at, nguoi_xu_ly_id (QLK), xu_ly_at, ly_do_tu_choi
- phien_ban (khóa lạc quan)
- Mỗi yêu cầu tối đa một phiếu mỗi loại; xuất đủ toàn bộ, nhân viên không sửa nội dung
- Lập phiếu linh kiện: yêu cầu "dang_thuc_hien" và so_luong_can_san_xuat > 0
- Lập phiếu thành phẩm: so_luong_can_san_xuat = 0, hoặc ChungTuHoanThanhSx đã "da_duyet"
- Duyệt: trừ tồn, ghi giá theo MatHang.don_gia lúc duyệt, kết thúc giữ hàng; phiếu thành phẩm ⇒ yêu cầu "hoan_thanh"
- Từ chối bắt buộc lý do; gửi lại thẳng "tu_choi" → "cho_duyet", không về nháp
- Hủy yêu cầu: phiếu "nhap" bị xóa hẳn, phiếu "cho_duyet" → "tu_choi" với lý do "Yêu cầu đã hủy"
- Có nhiều: ChiTietPhieuXuat

## ChiTietPhieuXuat

- id, phieu_xuat_id, mat_hang_id, so_luong (> 0)
- don_gia_thuc, tong_gia: trống đến khi duyệt
- Số lượng lấy từ NhuCauLinhKien (phiếu linh kiện) hoặc YeuCauSanXuat.so_luong (phiếu thành phẩm)

## ChungTuHoanThanhSx

- id, ma_phieu (HTSX-YYYYMM-xxxxxx), yeu_cau_san_xuat_id (duy nhất), nhan_vien_id (NV lập)
- so_luong_hoan_thanh = YeuCauSanXuat.so_luong_can_san_xuat, nhân viên không sửa
- trang_thai ("nhap" | "cho_duyet" | "da_duyet" | "tu_choi")
- finish_time: hệ thống ghi tại lần xác nhận gửi gần nhất
- created_at, updated_at, nguoi_xu_ly_id (QLK), xu_ly_at, ly_do_tu_choi
- phien_ban (khóa lạc quan)
- Lập sau khi bắt đầu sản xuất (YeuCauSanXuat.started_at có giá trị)
- Duyệt: cộng thành phẩm vào kho và giữ cho chính yêu cầu; không trừ linh kiện lần nữa
- Từ chối bắt buộc lý do, không cộng tồn, linh kiện đã xuất không hoàn; gửi lại thẳng "tu_choi" → "cho_duyet"

## GiaoDichKho

- id, mat_hang_id, nhan_vien_id (người ghi nhận), posted_at
- loai_giao_dich ("nhap_linh_kien" | "xuat_linh_kien" | "nhap_san_pham_san_xuat" | "xuat_thanh_pham")
- so_luong_bien_dong (dương khi nhập, âm khi xuất), so_luong_ton_sau
- Đúng một nguồn: chi_tiet_phieu_nhap_id | chi_tiet_phieu_xuat_id | chung_tu_hoan_thanh_sx_id; mỗi nguồn chỉ ghi nhận một lần
- Chỉ sinh từ phiếu nhập hoàn tất, phiếu xuất đã duyệt, chứng từ hoàn thành đã duyệt
- Chỉ thêm, không sửa, không xóa; là nguồn của báo cáo và tra cứu biến động kho

## LichSuThaoTac

- id, nhan_vien_id (người thực hiện), created_at
- loai_doi_tuong ("nhan_vien" | "mat_hang" | "nha_cung_cap" | "cong_thuc" | "phieu_nhap" | "phieu_xuat" | "yeu_cau_san_xuat" | "chung_tu_hoan_thanh_san_xuat"), doi_tuong_id
- thao_tac ("dang_nhap" | "tao" | "sua" | "xoa_nhap" | "gui" | "gui_lai" | "kiem_tra" | "duyet" | "tu_choi" | "hoan_tat" | "bat_dau" | "huy" | "khoa" | "mo_khoa" | "doi_vai_tro" | "doi_mat_khau" | "ngung" | "dung_lai" | "tao_phien_ban" | "dung_lai_phien_ban")
- trang_thai_truoc, trang_thai_sau
- du_lieu_truoc, du_lieu_sau: giá trị trước/sau của thao tác sửa; danh sách thiếu khi yêu cầu chuyển "cho_bo_sung_linh_kien"
- ly_do: bắt buộc với từ chối, hủy; không bắt buộc với khóa, mở khóa, đổi vai trò và các thao tác khác
- Không ai sửa, xóa; không bao giờ chứa mật khẩu
- QLK và QTV xem, lọc theo đối tượng, người, thao tác, khoảng thời gian; Nhân viên không xem

## NhuCauBoSungLinhKien (view, không phải table)

- Danh sách YeuCauSanXuat "cho_bo_sung_linh_kien", cũ nhất lên đầu, kèm linh kiện thiếu của từng yêu cầu
- Tổng hợp theo linh kiện: tổng cần (từ NhuCauLinhKien), còn dùng được (MatHang.so_luong_con_dung), thiếu
- Chỉ để xem; QLK tự lập PhieuNhap

## BaoCaoNhapXuatTon (view, không phải table)

- Theo kỳ tháng | quý | năm (giờ Việt Nam), lọc theo mặt hàng và loại
- Mỗi mặt hàng: tồn đầu kỳ, nhập, xuất, tồn cuối kỳ
- Tính từ GiaoDichKho; tồn đầu kỳ = so_luong_ton_sau của giao dịch cuối cùng trước kỳ (không có thì 0)
- Tồn cuối kỳ hiện tại khớp MatHang.so_luong_ton
