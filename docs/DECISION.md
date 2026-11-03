# Quyết định đã chốt

Tài liệu này ghi các quyết định nghiệp vụ và kỹ thuật dev đã chốt, để đối chiếu khi triển khai và review. Mỗi quyết định ghi ngày, nguồn đã đối chiếu và lý do. Khi tài liệu này mâu thuẫn với contract hoặc code, hỏi lại dev trước khi sửa (AGENTS.md §2, §6).

## Module BOM (chốt ngày 02/11/2026)

Nguồn đã đối chiếu:
- `api-contract-v2.md` v2.0.0 (Drive của project): §2 quy ước, §3 phân quyền, §6 BOM, §14 mã lỗi. Bản v1 nêu trong checklist không còn trong thư mục Drive; dev chốt dùng v2.
- `infra/postgres/init.sql`: bảng `"Bom"`, `"ChiTietBom"`, index `uq_bom_hien_hanh`, trigger `bao_ve_bom_da_dung`. File này là schema đã thống nhất với team.
- `infra/postgres/seed.sql`.

Kế hoạch triển khai: `.handoff/plan-bom.md`.

### D-BOM-01. Contract áp dụng

Dùng contract v2 §6, có các ngoại lệ ghi ở D-BOM-10.

### D-BOM-02. Sửa BOM = tạo version mới (SCD2), không có PATCH

- Bảng `Bom` thiết kế theo kiểu SCD type 2: mỗi dòng (`version`, `start_time`, `end_time`, `is_active`) là một bản chụp cố định của công thức trong khoảng thời gian hiệu lực của nó.
- Không có endpoint PATCH (bỏ API-026). Muốn thay đổi định mức thì tạo version mới.
- **Lý do:** sửa trực tiếp `ChiTietBom` sẽ làm version không còn đúng với nội dung đã áp dụng trong kỳ hiệu lực, khiến lịch sử chỉ còn trong audit. Ngoài ra, sửa BOM đang hiện hành sẽ làm thay đổi ngay dữ liệu đầu vào của cấu trúc và kế hoạch sản xuất.
- **Đánh đổi chấp nhận:** BOM nhập sai có hiệu lực ngay. Cách sửa là tạo version mới, hoặc kích hoạt lại version cũ (D-BOM-04).

### D-BOM-03. Tạo BOM là kích hoạt ngay

- `POST /bom` do server cấp `version = max(version) + 1` theo mặt hàng đầu ra. BOM mới có `is_active=true` và `start_time=now()`.
- BOM hiện hành cũ (nếu có) được đóng trong cùng transaction: `is_active=false`, `end_time=now()`.
- Đóng BOM cũ trước rồi mới tạo BOM mới, vì `uq_bom_hien_hanh` là partial unique index không deferrable.
- Client không gửi `version`, `is_active`, `start_time`, `end_time`; gửi các field này nhận 422.

### D-BOM-04. Kích hoạt = quay lại một version

- `POST /bom/{id}/kich_hoat` đóng BOM hiện hành của cùng mặt hàng, rồi mở BOM được chọn (`is_active=true`, `end_time=NULL`).
- **Giữ nguyên `start_time`**, vì trigger `bao_ve_bom_da_dung` cấm đổi `start_time` của BOM đã được lệnh dùng. Lịch sử bật/tắt đầy đủ nằm trong `LichSuThaoTac`.
- Kích hoạt một BOM đang hoạt động sẵn: trả 200 cùng BOM hiện tại, không ghi audit (idempotent).
- Kích hoạt chạy lại các kiểm tra của D-BOM-07 và D-BOM-08, áp dụng cho chính `chi_tiet` của BOM đó.

### D-BOM-05. Xóa = xóa mềm

- `DELETE /bom/{id}` chỉ ngừng hiệu lực (`is_active=false`, `end_time=now()`); không xóa dòng nào khỏi DB.
- Cho phép với mọi BOM, kể cả BOM đã được lệnh sản xuất dùng; trigger cho phép đóng hiệu lực và lệnh cũ vẫn giữ `bom_id`.
- Xóa BOM đã không hoạt động: trả 204, không ghi audit (giống `mat_hang`).
- Sau khi xóa, mặt hàng đầu ra tạm thời không có BOM hiện hành.

### D-BOM-06. Không ETag/If-Match

- Không trả ETag và không yêu cầu If-Match ở mọi endpoint BOM.
- **Lý do:** nội dung BOM bất biến (D-BOM-02). Thay đổi duy nhất là bật/tắt hiệu lực, và các thao tác này được tuần tự hóa bằng advisory lock `pg_advisory_xact_lock(20261020, 2)`.

### D-BOM-07. Quy tắc loại mặt hàng

- Đầu ra của BOM: `ban_thanh_pham` hoặc `thanh_pham`.
- Thành phần: `nguyen_vat_lieu`, `linh_kien` hoặc `ban_thanh_pham`. `thanh_pham` không được làm thành phần.
- Sai loại trả **422 `du_lieu_khong_hop_le`**.
  - Giao diện phải cho chọn mặt hàng bằng dropdown đã lọc theo loại, không cho nhập tự do.
  - Backend vẫn kiểm tra để chặn payload bị can thiệp.
- Miền `loai_mat_hang` gồm 4 giá trị theo contract v2 §5 và CHECK trong init.sql. `seed.sql` hiện dùng 3 trong số đó và đã hợp lệ, không cần sửa.

### D-BOM-08. BOM con, chu trình, thành phần trùng

- **BOM con bắt buộc:** khi tạo hoặc kích hoạt, mọi thành phần `ban_thanh_pham` phải đang có BOM hiện hành; nếu không trả **409 `thieu_bom`**.
  - Xóa mềm BOM con sau đó không bị chặn.
  - Khi đó `GET /bom/{id}/cau_truc` trả `bom_id: null` cho node tương ứng.
- **Chu trình bị chặn**, ví dụ:
  - Tự tham chiếu: BOM của *Cụm bánh xe* chứa chính *Cụm bánh xe*.
  - Gián tiếp: BOM của *Cụm bánh xe* chứa X, trong khi BOM hiện hành của X chứa *Cụm bánh xe*. Chu trình dài hơn (A → B → C → A) cũng bị chặn.
  - Chu trình gián tiếp trả **409 `bom_co_chu_trinh`**. Đồ thị được kiểm tra dưới advisory lock của D-BOM-06, nên hai BOM tạo đồng thời không thể cùng hình thành chu trình.
  - Tự tham chiếu trả **422 `du_lieu_khong_hop_le`**, bắt ngay khi kiểm tra request (schema `BomCreate`) với `details[].field = "chi_tiet"`. Dropdown thành phần trên giao diện phải loại bỏ mặt hàng đầu ra đang chọn, nên lỗi này chỉ xảy ra khi payload bị can thiệp. Lý do chọn 422 (cùng lập luận với D-BOM-07):
    - Lỗi chỉ phụ thuộc payload: chặn trước khi chạm DB hay lấy khóa.
    - Mọi lỗi payload được trả về trong một lần gọi.
    - Chỉ ra đúng field sai.
  - Phòng thủ: khi kích hoạt một BOM cũ nạp từ DB (không đi qua schema), nếu dữ liệu chèn tay có cạnh tự trỏ thì kiểm tra đồ thị vẫn trả 409 `bom_co_chu_trinh`.
- **Thành phần trùng** trong cùng `chi_tiet`: 422 `du_lieu_khong_hop_le`, bắt khi kiểm tra request.

### D-BOM-09. Phân quyền

Theo contract v2 §6:

| Thao tác | Vai trò |
|---|---|
| Đọc (`GET /bom`, `GET /bom/{id}`, `GET /bom/{id}/cau_truc`) | `quan_ly`, `nhan_vien` |
| Ghi (`POST /bom`, `DELETE /bom/{id}`, `POST /bom/{id}/kich_hoat`) | `quan_ly` |

`quan_tri_vien` nhận 403 ở mọi endpoint BOM.

### D-BOM-10. Điểm lệch so với contract v2 §6

| Contract v2 | Quyết định |
|---|---|
| POST tạo phiên bản mới chưa kích hoạt | POST tạo BOM kích hoạt ngay (D-BOM-03) |
| `PATCH /bom/{id}` (API-026) | Bỏ (D-BOM-02); gọi PATCH nhận 405 |
| If-Match bắt buộc cho DELETE và action | Bỏ ETag/If-Match (D-BOM-06) |
| DELETE chỉ cho BOM chưa dùng/tham chiếu | Xóa mềm, cho phép mọi BOM (D-BOM-05) |
| Tự tham chiếu xếp chung nhóm chu trình (409 `bom_co_chu_trinh`) | Tự tham chiếu trả 422 `du_lieu_khong_hop_le`; chu trình gián tiếp vẫn 409 (D-BOM-08) |

### D-BOM-11. Audit

Ghi vào `LichSuThaoTac` với `loai_doi_tuong='cong_thuc'`, cùng transaction với thao tác nghiệp vụ:

| Thao tác | Bản ghi audit |
|---|---|
| `POST /bom` | `tao` cho BOM mới; cộng `vo_hieu_hoa` cho BOM hiện hành cũ bị đóng (nếu có) |
| `POST /bom/{id}/kich_hoat` | `sua` (có `du_lieu_truoc`/`du_lieu_sau`) cho BOM được bật; cộng `vo_hieu_hoa` cho BOM bị thay (nếu có) |
| `DELETE /bom/{id}` | `vo_hieu_hoa` (chỉ khi BOM đang hoạt động) |

Enum `thao_tac` trong init.sql không có `kich_hoat` hay `xoa`, nên dùng các giá trị sẵn có. `vo_hieu_hoa` thống nhất với cách module `mat_hang` ghi khi xóa mềm.

### D-BOM-12. ORM theo init.sql

- Lớp ORM trùng tên bảng: `Bom`, `ChiTietBom` (AGENTS.md §9).
- Kiểu, nullable, default, FK, check và index giống hệt `infra/postgres/init.sql`.
- Trong module `production`, chỉ sửa FK trỏ sang `"Bom"`; các phần khác của module đó chưa chuyển đổi (AGENTS.md §10).

### D-BOM-13. Xác định `da_duoc_su_dung` trong response

- `da_duoc_su_dung` trong `BomRead` được tính khi truy vấn: `true` nếu có ít nhất một lệnh sản xuất trong bảng `"LenhSanXuat"` với `bom_id` bằng `id` của BOM đang trả về; không có thì `false`.
- Kiểm tra bằng `EXISTS`, không lọc theo trạng thái lệnh sản xuất. Chỉ cần có lệnh gắn với đúng version BOM đó là được xem là đã sử dụng.
- Đây là trường tính toán của response, không phải cột lưu trong bảng `"Bom"` và không phụ thuộc `is_active` của BOM.
- Nguồn đối chiếu: dev xác nhận ngày 02/11/2026 và truy vấn `_used` trong `backend/app/modules/bom/repository.py`.


## Điều chỉnh kho — 03/11/2026

Dev chốt giữ API-073–081, module dieu_chinh_kho, chỉ quan_ly. Payload nhận phieu_nhap_id, ly_do và chi_tiet(giao_dich_goc_id,so_luong_dung). Ticket độc lập theo v3.1, không FK tới phiếu điều chỉnh; phiếu loi bất biến. /tu_choi chỉ cho_duyet, /ve_nhap chỉ tu_choi. Bootstrap dùng nhap/cho_duyet/da_duyet/tu_choi/loi; confirmed_at chỉ có khi da_duyet. Không migration hoặc cập nhật database hiện hữu. Xem docs/sequence/dieu_chinh_kho.md về transaction và phục hồi ticket.
