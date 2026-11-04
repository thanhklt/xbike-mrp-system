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

## Phân quyền quản trị viên (chốt ngày 02/11/2026)

Nguồn: yêu cầu dev thực thi `.handoff/plan-phan-quyen-quan-tri-vien.md`, contract v2 §3/§5/§7 và router/service hiện tại. Các quyết định này thay thế quyền đọc danh mục của admin trong contract v2. D-BOM-09 giữ nguyên.

### D-PQ-01. Phạm vi truy cập của quản trị viên

- `quan_tri_vien` chỉ xem và thay đổi dữ liệu nhân viên/vai trò qua `/api/v1/nhan_vien` và `/api/v1/vai_tro`, trong giới hạn của các endpoint đã triển khai.
- Admin được dùng `/api/v1/auth/*` để đăng nhập, xem hồ sơ và đổi mật khẩu của chính mình, cùng `GET /api/v1/audit`, `GET /health`, `GET /api/v1/ping`.
- Mọi endpoint nghiệp vụ còn lại trả 403 cho admin. Mỗi route nghiệp vụ phải có role guard loại trừ `quan_tri_vien`; kiểm thử chính sách rà soát toàn bộ route để phát hiện endpoint mới thiếu guard.
- Quyền của `quan_ly` và `nhan_vien` giữ nguyên trong phạm vi tác vụ này.

### D-PQ-02. Audit rút gọn cho quản trị viên

- Admin thấy tất cả dòng audit, không lọc `loai_doi_tuong`, và vẫn nhận `ly_do`.
- Response của admin bỏ hẳn hai key `du_lieu_truoc` và `du_lieu_sau`, kể cả audit nhân viên/vai trò. Không thay bằng `null`, vì `null` vẫn có nghĩa riêng trong response đầy đủ, ví dụ dữ liệu trước của thao tác tạo.
- Dev xác nhận khi thực thi ngày 02/11/2026: chỉ loại hai trường khỏi DTO/response. Giữ helper `select_page` và cách đọc ORM đầy đủ hiện tại; không yêu cầu loại hai cột khỏi câu SELECT hoặc bộ nhớ của session.
- Admin gửi `sort_by=du_lieu_truoc` hoặc `sort_by=du_lieu_sau` thì server chuyển sang `created_at`, giữ các tham số khác. Quản lý vẫn nhận đủ hai trường và giữ cách sắp xếp hiện tại. Nhân viên không được đọc audit.
- Đánh đổi chấp nhận: admin vẫn thấy ai thao tác, loại/ID đối tượng và thời điểm, kể cả siêu dữ liệu nghiệp vụ. Nội dung `ly_do` vẫn hiển thị và tìm được qua `search`; các cột JSON không được tìm kiếm.
- Admin cũng không thấy giá trị trước/sau khi đổi thông tin hoặc vai trò nhân viên trong audit; trạng thái hiện tại vẫn xem qua `/nhan_vien` theo quyền hiện có.

### D-PQ-03. Điểm lệch so với contract v2

- Contract v2 §3/§5 cho admin tra cứu danh mục, gồm `/mat_hang` và `/nha_cung_cap`. Quyết định mới bỏ quyền đó: admin nhận 403, kể cả `/danh_muc_mat_hang/`.
- Frontend cần ẩn menu mặt hàng/nhà cung cấp đối với admin và hỗ trợ response audit không có hai trường JSON. Frontend được xử lý trong tác vụ riêng.

### D-PQ-04. Bỏ API tồn kho riêng trong contract

- Bỏ API-029/030 (`/ton_kho`). Số dư và thời điểm cập nhật được trả qua `MatHangRead.so_luong_ton` và `ton_kho_updated_at`, là phần bổ sung so với contract v2 §5, chỉ quản lý/nhân viên đọc được.
- Endpoint legacy `GET /inventory/stock` vẫn tồn tại và được chặn admin trong tác vụ này; việc gỡ endpoint và chuyển đổi ORM tồn kho thuộc tác vụ sau.

Ghi chú triển khai/hoàn tác: thay đổi nằm ở role guard và projection audit, không đổi schema hay dữ liệu đã lưu. Khi cần hoàn tác, khôi phục các guard và hợp đồng đọc audit về bản trước tác vụ cùng lúc, kèm kiểm thử và sequence tương ứng; không cần migration hoặc phục hồi dữ liệu.

## Module sản xuất — yêu cầu sản xuất (chốt ngày 03/11/2026)

Nguồn đã đối chiếu:
- `docs/api_contract_v3.md` v3.0.0 (03/11/2026): §2 quy ước, §3 phân quyền, §8 yêu cầu và kế hoạch sản xuất, §9 lệnh sản xuất, §10 phiếu xuất, §11 chứng từ hoàn thành, §14 trạng thái và mã lỗi.
- `infra/postgres/init.sql`: bảng `"YeuCauSanXuat"`, `"LenhSanXuat"`, `"ChiTietLenhSanXuat"`, `"ChungTuHoanThanhSx"`, `"PhieuXuat"`, `"ChiTietPhieuXuat"`, kèm `COMMENT ON` và trigger liên quan.
- `infra/postgres/seed.sql`.
- Checklist "08 · Yêu cầu và kế hoạch" (API-036 đến API-044) do dev cung cấp.

Kế hoạch triển khai: `.handoff/plan-yeu-cau-san-xuat.md`.

### D-SX-01. Một module sản xuất, tên `san_xuat`

- Yêu cầu sản xuất, lệnh sản xuất (kèm chi tiết lệnh) và chứng từ hoàn thành sản xuất thuộc **cùng một module**.
- Module `backend/app/modules/production/` được đổi tên thành `backend/app/modules/san_xuat/`, theo quy ước tên module tiếng Việt (contract v3 §1, QĐ-0311).
- **Lý do:**
  - Ba nhóm này nối với nhau bằng FK bắt buộc: yêu cầu → lệnh (có cây cha/con) → chứng từ hoàn thành.
  - Trạng thái của chúng đổi theo nhau trong cùng transaction: gửi yêu cầu tạo cây lệnh, duyệt chứng từ hoàn thành làm lệnh hoàn thành, hủy yêu cầu thì hủy lệnh.
  - Tách thành nhiều module sẽ tạo phụ thuộc vòng giữa các module.
- Các module khác giao tiếp với module sản xuất qua service công khai và dùng chung session của transaction (giống `AuditService`, `MatHangAvailabilityService`). Không import ORM hay repository của nhau.

### D-SX-02. Phạm vi branch `feature/yeu_cau_san_xuat`

- Chỉ triển khai 9 endpoint của contract v3 §8 (API-036 đến API-044):
  - `GET /yeu_cau_san_xuat`
  - `GET /yeu_cau_san_xuat/{id}`
  - `POST /yeu_cau_san_xuat`
  - `PATCH /yeu_cau_san_xuat/{id}`
  - `DELETE /yeu_cau_san_xuat/{id}`
  - `POST /yeu_cau_san_xuat/{id}/tinh_ke_hoach`
  - `POST /yeu_cau_san_xuat/{id}/gui`
  - `GET /yeu_cau_san_xuat/{id}/ke_hoach`
  - `POST /yeu_cau_san_xuat/{id}/huy`
- Endpoint `/lenh_san_xuat` (§9) và `/chung_tu_hoan_thanh_sx` (§11) làm ở branch sau. Branch này chỉ chuyển ORM của các bảng đó theo `init.sql`, vì 9 endpoint trên đọc/ghi các bảng này.

### D-SX-03. Gỡ 4 route `/production/work-orders`

- Gỡ toàn bộ route tiếng Anh `/production/work-orders` (list, get, POST tạo lệnh thủ công, PATCH status chưa triển khai), cùng schema và service cũ đi kèm.
- **Lý do:** contract v3 bỏ route tiếng Anh và không có POST tạo lệnh thủ công; lệnh chỉ được tạo khi gửi yêu cầu (§8, §9).
- Sau khi gỡ, sẽ không còn API đọc lệnh nào cho đến khi `/lenh_san_xuat` được triển khai ở branch sau. Frontend vẫn gọi `/production/work-orders` và chưa được cập nhật (contract §17.4).

### D-SX-04. ORM `PhieuXuat` tối thiểu trong module `phieu_xuat`

- Lúc này bảng `"PhieuXuat"` và `"ChiTietPhieuXuat"` chưa có module sở hữu theo `init.sql`. ORM cũ `phieu_xuat`/`chi_tiet_phieu_xuat` nằm trong `material_issuing` và là legacy.
- Tạo module `backend/app/modules/phieu_xuat/` chỉ gồm ORM theo `init.sql` và một service công khai nhỏ, phục vụ đúng nhu cầu của module sản xuất:
  - tính `so_luong_da_xuat` của yêu cầu từ phiếu `xuat_thanh_pham` `da_duyet`;
  - khi hủy yêu cầu: kiểm tra phiếu đã duyệt, xóa phiếu nháp, chuyển phiếu chờ duyệt sang `tu_choi`, ghi audit.
- Module này **chưa có endpoint**. `/phieu_xuat` (§10) làm ở branch sau, trên chính module này.
- Module `material_issuing` và `finished_goods_issuing` giữ nguyên. Chỉ đổi chuỗi FK trỏ sang tên bảng mới (`"YeuCauSanXuat"`, `"LenhSanXuat"`, `"ChungTuHoanThanhSx"`) khi ORM tương ứng đổi tên, giống cách D-BOM-12 sửa FK `"Bom"`.

### D-SX-05. Sinh mã chứng từ: phần số bằng id

- `ma_yeu_cau_san_xuat = YCSX-YYYYMM-NNNNNN` và `ma_lenh_san_xuat = LSX-YYYYMM-NNNNNN`, trong đó `NNNNNN` là `id` của dòng (6 chữ số, thêm số 0 ở đầu).
- `YYYYMM` là tháng tạo theo giờ Asia/Ho_Chi_Minh.
- `id` được cấp trước khi insert bằng `nextval` của identity, để ghi mã ngay trong cùng câu INSERT.
- Phần số **không reset theo tháng**. Mã không tái sử dụng, vì id không tái sử dụng. Cách này khớp với `seed.sql` (`YCSX-202610-000001` có id 1) và ví dụ trong contract (`PX-202610-000601` có id 601).
- Giới hạn: CHECK chỉ cho 6 chữ số, nên id vượt 999999 sẽ bị CHECK chặn. Giới hạn này chấp nhận được trong phạm vi PoC.

### D-SX-06. Chỉ lập yêu cầu cho thành phẩm (P-01)

Dev yêu cầu thực thi `.handoff/plan-yeu-cau-san-xuat.md` ngày 03/11/2026; P-01–P-14
được triển khai theo yêu cầu đó. Đã đối chiếu bản `api_contract_v3.md` trên Drive,
`xbike_mrp_data_model_v3.1_mermaid.md`, `SRS_v4.txt`, `xbike_prd_v2.docx` và bootstrap.
Contract v3 §1 xác nhận SQL/contract mới thay thế các mô tả cũ liên quan.

`mat_hang_id` phải là `thanh_pham`; sai loại trả 422 `du_lieu_khong_hop_le`.
Kiểm tra tồn tại/active/loại bằng DB trong transaction ghi, giữ khóa FOR SHARE.

### D-SX-07. ETag cho yêu cầu (P-02)

Strong ETag là SHA-256 của JSON canonical `YeuCauRead`, gồm các trường tính toán.
GET chi tiết, tạo, sửa, gửi và hủy trả ETag. PATCH, DELETE, gửi, hủy so If-Match dưới
khóa yêu cầu; thiếu/blank trả 428, không khớp/weak/wildcard trả 412. Tính thử không cần.

### D-SX-08. Token kế hoạch ký riêng theo audience (P-03)

JWT dùng `settings.secret_key` và thuật toán cấu hình, `aud=ke_hoach_san_xuat`, TTL
10 phút. Payload gắn ID yêu cầu, người phụ trách, số lượng và hash kết quả canonical
(lệnh, BOM, nhu cầu, tồn đã đọc khi tính). Token này không xác thực được như access token.
Không lưu token trong audit.

### D-SX-09. Lỗi khi gửi kế hoạch (P-04)

Sai chữ ký/hết hạn/khác yêu cầu/kết quả tính lại khác trả 409 `ke_hoach_da_thay_doi`.
Kế hoạch khớp nhưng thiếu BOM hiện hành trả 409 `thieu_bom`. Thiếu, không còn tồn tại,
bị khóa hoặc sai vai trò người phụ trách khi gửi trả 409 `nguoi_duoc_giao_khong_hop_le`.
POST/PATCH vẫn trả 404 cho người được giao không tồn tại.

### D-SX-10. Lệnh mới chưa giao người thực hiện (P-05)

Gửi yêu cầu tạo lệnh `nhap`, `nhan_vien_id=NULL`. Giao người thực hiện qua API lệnh
ở tác vụ sau. Người phụ trách yêu cầu và người thực hiện từng lệnh là hai quan hệ khác nhau.

### D-SX-11. Điều kiện hủy (P-06)

Yêu cầu `hoan_thanh`/`da_huy` trả 409 `trang_thai_khong_hop_le`. Các trạng thái còn lại
được hủy nếu chưa có phiếu xuất `da_duyet` của yêu cầu/lệnh hoặc chứng từ hoàn thành
`da_duyet` của các lệnh; có ghi sổ trả 409 `phu_thuoc_khong_hop_le`.

### D-SX-12. Xóa nháp (P-07)

DELETE chỉ cho `nhap`, xóa cứng dòng yêu cầu; có lệnh/phiếu xuất tham chiếu trả 409
`dang_duoc_tham_chieu`. Xóa và audit dùng chung transaction.

### D-SX-13. Audit nghiệp vụ cùng transaction (P-08)

Tạo/sửa/xóa nháp ghi `tao`/`sua`/`xoa_nhap`. Gửi ghi `gui` yêu cầu và `tao` từng lệnh.
Hủy ghi `huy` yêu cầu và các lệnh thực sự đổi trạng thái; lệnh đã hủy giữ nguyên.
Chứng từ nháp bị xóa ghi `xoa_nhap`, chờ duyệt bị từ chối ghi `tu_choi`, kèm lý do.
GET/tính thử không ghi audit. Lưu snapshot trước/sau, snapshot trước khi xóa; không ghi kho.

### D-SX-14. Danh sách và khoảng ngày (P-09)

Sort mặc định `-created_at`, thêm ID tăng dần; whitelist theo contract §8. `q` tìm mã
ILIKE có tham số hóa/escape. Khoảng ngày Asia/Ho_Chi_Minh được đổi thành khoảng UTC
nửa mở, tính cả ngày kết thúc. N được lọc theo phụ trách cùng các filter của client.

### D-SX-15. Tính cây lệnh và snapshot nhu cầu (P-10)

Tính phần thiếu thành phẩm, dùng tồn BTP trước, BFS theo thứ tự chi tiết BOM; chỉ tạo
lệnh con cho phần BTP thiếu. Tồn còn lại dùng chung giữa các nhánh. Nhu cầu cha giữ
toàn bộ lượng trực tiếp, không gộp nguyên liệu của lệnh con.

Phát hiện chu trình theo tập tổ tiên của từng đường đi. Không giới hạn tổng số lệnh
bằng số mặt hàng/BOM: DAG hợp lệ có thể tạo nhiều lệnh cho một BTP ở nhiều nhánh.
Đây là cách hiện thực kiểm tra chu trình ở §4.3 bước 7 mà vẫn bảo đảm yêu cầu chia sẻ
tồn giữa các nhánh. Nhu cầu trực tiếp vượt INT32 trả 422 trước khi lưu.

### D-SX-16. Vật tư preview (P-11)

`vat_tu` gồm NVL/linh kiện và phần BTP lấy từ tồn. Chỉ phần BTP còn thiếu sinh lệnh con.
`thieu_vat_tu` khi có dòng thiếu; thiếu NVL không chặn gửi hoặc làm false
`du_dieu_kien_gui`. Cờ đủ điều kiện gửi phụ thuộc BOM và người phụ trách.

### D-SX-17. Response gửi (P-12)

`{data: {yeu_cau: YeuCauRead, ke_hoach: KeHoachRead}, meta}`, kèm ETag của yêu cầu.
Đủ thành phẩm không tạo lệnh, `ke_hoach.lenh=[]`.

### D-SX-18. Envelope và mã lỗi (P-13)

Nhóm `/yeu_cau_san_xuat` dùng contract error/meta envelope. Đăng ký status 409 cho
`trang_thai_khong_hop_le`, `nguoi_duoc_giao_khong_hop_le`, `ke_hoach_da_thay_doi`,
`phu_thuoc_khong_hop_le`, `dang_duoc_tham_chieu`.

### D-SX-19. Khóa đồ thị khi chốt kế hoạch (P-14)

Gửi yêu cầu gọi public `BomPlanningReader.lock_graph()` lấy advisory transaction lock
`pg_advisory_xact_lock(20261020, 2)` trước khi đọc graph, khóa mặt hàng và tính lại.
Khóa tuần tự hóa với thay đổi BOM theo D-BOM-06. Nhân viên được giao dùng FOR SHARE;
hủy khóa yêu cầu, lệnh, hoàn thành và phiếu xuất theo ID, rồi hủy lệnh sâu nhất trước.

Giới hạn/hoàn tác: không migration hoặc cập nhật schema DB đang chạy. Khi hoàn tác
code, hoàn tác cùng router, composition, ORM/FK, reporting và tài liệu; không xóa dữ liệu
sản xuất đã tạo để ép code cũ chạy. Frontend chuyển route và các endpoint lệnh/hoàn
thành/phiếu xuất thuộc tác vụ sau. Các module legacy còn lệch schema được giữ nguyên.

## Module phiếu xuất (chốt ngày 04/11/2026)

Nguồn đã đối chiếu:

- `docs/api_contract_v3.md` v3.0.0 §2.2, §2.5, §10, §14; đối chiếu bản `api_contract_v3.md` trên Drive của project.
- `infra/postgres/init.sql`: bảng `"PhieuXuat"`, `"ChiTietPhieuXuat"`, trigger `trg_xuat_bat_bien` và bảo vệ dòng chứng từ đã chốt.

Kế hoạch triển khai: `.handoff/plan-phieu-xuat.md`.

### D-PX-01. Gọi lại duyệt không kiểm tra If-Match

- Người còn quyền Q gọi lại `/phieu_xuat/{id}/duyet` trên phiếu `da_duyet` nhận resource hiện tại, `da_ghi_so_truoc_do=true` và các ID giao dịch kho đã có.
- Sau phân quyền và khóa đối tượng, bỏ qua If-Match hoàn toàn: thiếu, rỗng, wildcard, weak hoặc cũ đều được. Không ghi thêm giao dịch kho, trừ tồn hoặc audit.
- Phiếu chưa duyệt vẫn cần strong If-Match: thiếu/rỗng trả 428; sai định dạng, wildcard, weak hoặc cũ trả 412. Các action khác giữ nguyên.
- **Lý do:** contract §2.2 đặt kiểm tra đã ghi sổ lặp trước kiểm tra ETag.

### D-PX-02. Mặt hàng ngừng hoạt động trên phiếu chưa duyệt

- “Chứng từ cũ” tại §2.5 được hiểu là chứng từ đã xác nhận `da_duyet`; chúng vẫn đọc được và không bị tự hủy.
- Phiếu `nhap`/`cho_duyet`/`tu_choi` còn mặt hàng ngừng hoạt động không gửi hay duyệt được (409 `mat_hang_ngung_hoat_dong` khi kiểm tra mặt hàng); chỉ xóa theo điều kiện trạng thái hiện có. PATCH thay dòng đó bằng mặt hàng hợp lệ vẫn được phép khi phiếu ở `nhap`.
- Các giới hạn workflow vẫn áp dụng: chỉ xóa/sửa nháp; phiếu `cho_duyet` cần từ chối và về nháp trước khi sửa hoặc xóa. Không bổ sung đường xóa ở trạng thái khác.
- Code hiện tại giữ nguyên, chỉ ghi nhận cách hiểu đã chốt.

### D-PX-03. Mã lỗi mặt hàng ngoài nhu cầu hoặc sai loại

- Giữ 409 `phu_thuoc_khong_hop_le` khi mặt hàng ngoài nhu cầu nguồn hoặc sai loại.
- Dev xác nhận không cần thay mã lỗi này; không sửa code.

### D-PX-04. Không audit riêng cho yêu cầu khi duyệt xuất thành phẩm

- Audit `phieu_xuat` trong transaction duyệt đã đủ; không thêm audit riêng cho `YeuCauSanXuat` khi cập nhật tiến độ xuất thành phẩm.
- Code ghi audit hiện tại giữ nguyên.

### D-PX-05. Đọc phiếu xuất không khóa

- GET danh sách và chi tiết chạy trong transaction `REPEATABLE READ READ ONLY`, không dùng `FOR SHARE` trên phiếu hoặc chi tiết. COUNT, trang, dòng chi tiết và kiểm tra người được giao cùng snapshot, bảo đảm biểu diễn và ETag nhất quán.
- Danh sách lấy dòng chi tiết của cả trang bằng một truy vấn, sắp theo ID phiếu rồi ID dòng; loại bỏ N+1 và giữ nguyên thứ tự dòng trong resource.
- **Lý do:** tránh đọc chờ ghi, ghi chờ đọc và chi phí ghi thông tin khóa xuống đĩa của `FOR SHARE`.
- **Đánh đổi:** rollback transaction chỉ đọc do auth đã autobegin trước khi mở snapshot đọc. Payload nhân viên đã xác minh là dữ liệu độc lập với ORM. Session đóng kết thúc transaction đọc, không commit.
- Dùng execution options của SQLAlchemy với asyncpg: `isolation_level="REPEATABLE READ"`, `postgresql_readonly=True`; không cần fallback SQL.
- Phạm vi chỉ module `phieu_xuat`. Đường ghi và các lời gọi nội bộ giữ nguyên khóa hiện có; `phieu_nhap` còn pattern đọc `FOR SHARE`, xử lý ở tác vụ riêng.
- Hoàn tác bằng cách khôi phục đồng bộ service, port và repository trước thay đổi này; không có migration hoặc dữ liệu cần sửa. Không thay đổi schema/database ứng dụng.
