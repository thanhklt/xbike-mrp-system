# xBike MRP — API Contract v3

- Phiên bản hợp đồng: 3.0.0
- Ngày: 03/11/2026
- Thay thế: `api-contract-v2.md` v2.0.0 (14/10/2026, [Drive](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view))
- Trạng thái: đặc tả để triển khai (PoC). Các nhóm nhân viên/vai trò, mặt hàng, nhà cung cấp và BOM đã có code theo bản này (xem `docs/sequence/`), trừ các điểm ở §16.3. Các nhóm §7–§12 và đường dẫn đã Việt hóa `/lich_su_thao_tac` chưa được triển khai theo contract.
- Base URL: `/api/v1`
- Định dạng: REST, JSON UTF-8; JWT Bearer.
- Backend mục tiêu: FastAPI, PostgreSQL.

## Cách đọc các thay đổi so với v2

| Ký hiệu | Ý nghĩa |
|---|---|
| **[v3-mới]** | Endpoint, field, mã lỗi hoặc quy tắc mới, không có trong v2 |
| **[v3-đổi]** | Có trong v2 nhưng hành vi, quyền hoặc schema đã đổi theo quyết định của dev |
| **[v3-SQL]** | Đổi để khớp `infra/postgres/init.sql` (schema đã chốt). Bảng tổng hợp ở [§17.3](#173-các-chỗ-đã-sửa-để-khớp-initsql) |
| **[v3-bỏ]** | Có trong v2, nay đã bỏ. Dòng bảng bị gạch ngang |
| `> v3:` | Ghi chú giải thích thay đổi, kèm nguồn |

Phần không có ký hiệu giữ nguyên như v2. Tổng hợp mọi thay đổi nằm ở [§17](#17-changelog-v2--v3).

Nguồn quyết định được trích theo mã:

- `SQL`: `infra/postgres/init.sql`, gồm cột, CHECK, trigger và `COMMENT ON` mô tả nghiệp vụ. Đây là schema đã chốt (AGENTS §10).
- `D-BOM-xx`, `D-PQ-xx`: [docs/DECISION.md](DECISION.md), chốt ngày 02/11/2026.
- `QĐ-MH`: quyết định hợp nhất mặt hàng ngày 01/11/2026, [docs/plans/2026-11-01-hop-nhat-mat-hang.md](plans/2026-11-01-hop-nhat-mat-hang.md).
- `QĐ-NCC`: quyết định nhà cung cấp ngày 01/11/2026, `.handoff/plan.md` và [docs/sequence/nha_cung_cap.md](sequence/nha_cung_cap.md).
- `QĐ-NV`: quyết định nhân viên ngày 01/11/2026 và chính sách admin ghi tại [docs/sequence/nhan_vien.md](sequence/nhan_vien.md).
- `QĐ-AUTH`: quyết định xác thực ngày 18/10 và 30/10/2026, [docs/auth-api-verification.md](auth-api-verification.md).
- `QĐ-0311`: dev trả lời các điểm còn mở ngày 03/11/2026.
- `AGENTS §9/§10`: quy ước tên bảng và schema đã chốt trong `AGENTS.md`.

## 1. Nguồn và phạm vi

Nguồn cấu trúc chính: **[v3-đổi]** `infra/postgres/init.sql`, gồm cả ràng buộc và mô tả nghiệp vụ trong `COMMENT ON`. Khi quy tắc nghiệp vụ của v2 mâu thuẫn với `init.sql`, contract theo `init.sql` (QĐ-0311). Mô hình tham chiếu: [xbike_mrp_data_model_v3.1_mermaid.md](https://drive.google.com/file/d/1OdqHXKWbOwb47xcWwiraoKh9tGjecdQB/view). Yêu cầu nghiệp vụ bổ sung lấy từ `SRS_v4.txt`, `xbike_prd_v2.docx`.

Ngoại lệ: **kiểu tiền là integer VND** (§2.1) và **`MatHang.don_gia` bắt buộc** (§5.1), trong khi `init.sql` đang khai báo các cột tiền là `numeric(18,2)` và `don_gia` nullable. `init.sql` phải được sửa theo hai quyết định này (QĐ-0311, §16.3).

> v3: tên bảng PascalCase (`"NhanVien"`, `"PhieuNhap"`…) chỉ ảnh hưởng SQL/ORM. Đường dẫn API, tên field, mã vai trò và giá trị enum dùng snake_case (AGENTS §9).

**[v3-mới] Chỉ có module và đường dẫn tiếng Việt (QĐ-0311).** Contract không có module hoặc route tiếng Anh. Đổi tên:

| v2 / code hiện tại | v3 |
|---|---|
| `/audit` (code hiện tại) | `/lich_su_thao_tac` (đường dẫn của v2) |
| `/inventory/stock` và các route tiếng Anh của module nhập/xuất/sản xuất | Bỏ; dùng các đường dẫn ở §5, §7–§11 |

**Ngoại lệ giữ nguyên tên (QĐ-0311):** module `auth` và các đường dẫn `/auth/dang_nhap`, `/auth/token`, `/auth/me`, `/auth/doi_mat_khau` giữ nguyên như code hiện tại. `/bom` giữ nguyên vì BOM là thuật ngữ dùng trong nghiệp vụ. `GET /health` và `GET /api/v1/ping` là endpoint hạ tầng, không phải module nghiệp vụ, giữ nguyên (QĐ-0311).

Tiếp tục dùng prefix `/api/v1`, không đổi thành `/api/v3`. Frontend chưa được cập nhật theo v3; danh sách việc ở §17.4.

Phạm vi nghiệp vụ: tài khoản, danh mục, BOM nhiều cấp, nhập/xuất, kế hoạch và lệnh sản xuất, hoàn thành nhiều đợt, điều chỉnh phiếu nhập, ticket, báo cáo và audit. Không có bán hàng, thanh toán, mua hàng hoặc nhiều kho.

## 2. Quy ước chung

### 2.1 Kiểu dữ liệu

| Kiểu | Quy ước |
|---|---|
| ID | JSON integer dương; do server tạo |
| Số lượng/định mức | Integer; không nhận số lẻ |
| Tiền | **[v3-đổi]** Integer không âm, đơn vị đồng Việt Nam (VND). Áp dụng cho mọi trường tiền: `don_gia`, `don_gia_thuc`, `tong_gia`, `tong_tien` |
| Decimal không phải tiền | Chuỗi JSON, ví dụ `he_so_luong` |
| Ngày | `YYYY-MM-DD` |
| Thời điểm | ISO 8601 có offset, trả UTC, ví dụ `2026-10-13T10:24:00Z` |
| Category | `snake_case`, tiếng Việt không dấu |
| Chuỗi | Trim; trường bắt buộc không được rỗng hoặc chỉ có khoảng trắng |

> v3 (QĐ-0311): tiền là integer VND như v2, áp dụng thống nhất cho mọi trường tiền. Quyết định này thay cho hướng decimal của QĐ-MH. `init.sql` (`numeric(18,2)`) và module mặt hàng (đang trả `don_gia` dạng chuỗi decimal) phải được sửa (§16.3).

Không nhận thuộc tính chưa khai báo: trả 422. PATCH phân biệt trường bỏ qua (giữ nguyên) với null (chỉ xóa nếu trường nullable). Trường bắt buộc không nhận null.

### 2.2 Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
If-Match: "<etag-tu-GET>"
```

`Authorization` bắt buộc, trừ đăng nhập. `If-Match` bắt buộc với PATCH, PUT, DELETE và POST action thay đổi resource đã tồn tại. Thiếu trả 428; dữ liệu cũ trả 412. Tạo resource, tính thử kế hoạch và đổi mật khẩu không cần If-Match; đổi mật khẩu xác minh mật khẩu hiện tại. GET chi tiết trả strong ETag. Wildcard hoặc weak ETag trong `If-Match` bị coi là không khớp và trả 412.

**[v3-mới] Ngoại lệ không dùng ETag/If-Match:**

| Resource | Lý do | Nguồn |
|---|---|---|
| `/bom` | Nội dung BOM bất biến; bật/tắt hiệu lực được tuần tự hóa bằng advisory lock | D-BOM-06 |
| `/nha_cung_cap` | Không có PATCH/DELETE; GET chi tiết và POST không trả ETag | QĐ-NCC |

ETag là token opaque do backend sinh từ biểu diễn phiên bản hiện tại, gồm dòng chi tiết và trạng thái liên quan. So sánh token và cập nhật phải diễn ra dưới khóa/transaction. ETag không thay thế kiểm tra tồn và giới hạn nghiệp vụ.

Thứ tự xử lý action: xác thực → phân quyền → khóa đối tượng → kiểm tra đã ghi sổ lặp → kiểm tra ETag → kiểm tra trạng thái/điều kiện → cập nhật atomic. Riêng action ghi sổ đã thành công (hoàn tất phiếu nhập, duyệt phiếu xuất/chứng từ hoàn thành, xác nhận điều chỉnh): người còn quyền gọi lại cùng endpoint nhận resource hiện tại với `da_ghi_so_truoc_do=true`, dù ETag cũ; không tạo giao dịch hay audit mới.

### 2.3 Response thành công

Một resource:

```json
{
 "data": {"id": 101, "trang_thai": "nhap"},
 "meta": {"request_id": "req-001"}
}
```

Danh sách:

```json
{
 "data": [],
 "meta": {"request_id": "req-002", "page": 1, "page_size": 20, "total": 0, "total_pages": 0}
}
```

**[v3-mới]** Danh mục không phân trang (hiện chỉ có `GET /danh_muc_mat_hang/`):

```json
{
 "data": [],
 "meta": {"request_id": "req-003", "total": 0}
}
```

| Trường hợp | HTTP |
|---|---|
| GET, PATCH, PUT, action thành công | 200 |
| POST tạo resource | 201, header `Location` trỏ chi tiết |
| DELETE thành công | 204, không body |

Action ghi sổ thêm `giao_dich_kho_ids` và `da_ghi_so_truoc_do`; đây là trường tính toán trong response, không phải cột mới. Sau thay đổi, server trả ETag mới (trừ các resource ở ngoại lệ §2.2).

**[v3-mới]** Mọi response của `/auth/*` có `Cache-Control: no-store` và `Pragma: no-cache` (QĐ-AUTH).

### 2.4 Query danh sách

- `page`: mặc định 1, tối thiểu 1.
- `page_size`: mặc định 20, từ 1 đến 100.
- `q`: tìm mã/tên/văn bản theo resource; tham số hóa SQL.
- `sort`: tên trường; tiền tố `-` là giảm dần, ví dụ `-created_at`.
- `tu_ngay`, `den_ngay`: ngày địa phương Asia/Ho_Chi_Minh, tính cả hai đầu. Backend đổi sang khoảng UTC `[đầu ngày bắt đầu, đầu ngày sau ngày kết thúc)`.
- Enum sai, ngày đảo ngược, sort ngoài whitelist, query lặp hoặc query không hỗ trợ trả 422.
- Sort luôn thêm ID làm tiêu chí phụ để ổn định phân trang.

**[v3-đổi]** Quy ước này áp dụng cho mọi danh sách, kể cả lịch sử thao tác (§13). Không còn `search`, `sort_by`, `sort_order` (QĐ-0311).

### 2.5 Payload chứng từ và quyền sở hữu

**[v3-SQL]** Mã chứng từ do server tạo, duy nhất, bất biến và không tái sử dụng, theo định dạng `<TIỀN_TỐ>-YYYYMM-NNNNNN` (phần số khác `000000`):

| Resource | Field | Tiền tố |
|---|---|---|
| Phiếu nhập | `ma_phieu_nhap` | `PN` |
| Phiếu xuất | `ma_phieu_xuat` | `PX` |
| Yêu cầu sản xuất | `ma_yeu_cau_san_xuat` | `YCSX` |
| Lệnh sản xuất | `ma_lenh_san_xuat` | `LSX` |
| Chứng từ hoàn thành | `ma_phieu` | `HTSX` |
| Phiếu điều chỉnh kho | `ma_phieu` | `DCK` |
| Ticket lỗi điều chỉnh | `ma_ticket` | `TKDC` |

Danh mục dùng mã không có tháng: `NV-NNNNNN` (nhân viên), `MH-NNNNNN` (mặt hàng), `NCC-NNNNNN` (nhà cung cấp).

Client không gửi mã chứng từ, trạng thái, người tạo, thời điểm tạo, đơn giá xuất, tổng tiền, số dư, audit hay tiến độ.

**[v3-SQL]** Người lập chứng từ (`nhan_vien_id`) của phiếu nhập, **phiếu xuất**, yêu cầu, chứng từ hoàn thành và phiếu điều chỉnh lấy từ ID nhân viên trong JWT. Ledger và audit lưu `nhan_vien_id` của người thực hiện action. Lệnh là ngoại lệ: `nhan_vien_id` là người được giao thực hiện. Ticket lưu `nguoi_tao_id` (người xác nhận điều chỉnh thất bại) và `nguoi_xu_ly_id`.

> v3: v2 dùng `ma_nhan_vien` cho phiếu xuất. `init.sql` lưu `"PhieuXuat".nhan_vien_id int NOT NULL` và không có cột `ma_nhan_vien`, nên phiếu xuất quay về `nhan_vien_id` như các chứng từ khác.

PATCH resource có `chi_tiet`: gửi array thì thay toàn bộ danh sách dòng trong cùng transaction; bỏ qua thì giữ nguyên. Client không gửi ID dòng. Chi tiết không có bộ CRUD độc lập.

Phiếu nháp phải có ít nhất một dòng hợp lệ. Số lượng dòng phải dương. Phiếu nhập/xuất, BOM và lệnh không được trùng mặt hàng trong cùng chứng từ. Phiếu điều chỉnh không được trùng `giao_dich_goc_id` trong cùng phiếu.

**[v3-mới] Mặt hàng ngừng hoạt động.** Mặt hàng có `is_active=false` không được dùng trong BOM, phiếu nhập/xuất, yêu cầu sản xuất, lệnh hoặc chứng từ mới. Backend kiểm tra bằng DB trong transaction của thao tác ghi, khóa các dòng `MatHang` theo thứ tự ID (`FOR SHARE`), không dựa vào cache. ID không tồn tại trả 404; mặt hàng bị khóa trả 409 `mat_hang_ngung_hoat_dong`. Chứng từ cũ vẫn đọc được và không bị tự hủy (QĐ-MH).

**[v3-SQL] Chứng từ đã chốt bất biến.** Trigger chặn sửa/xóa phiếu nhập `hoan_thanh`, phiếu xuất `da_duyet`, chứng từ hoàn thành `da_duyet`, phiếu điều chỉnh `da_xac_nhan`/`loi`, cùng các dòng của chúng. API trả 409 `trang_thai_khong_hop_le` trước khi chạm trigger.

## 3. Phân quyền

| Ký hiệu | Vai trò/phạm vi |
|---|---|
| A | `quan_tri_vien`: **[v3-đổi]** chỉ quản trị tài khoản nhân viên và vai trò; đọc lịch sử thao tác dạng rút gọn |
| Q | `quan_ly`: nghiệp vụ kho, BOM, giao việc, duyệt, **[v3-đổi]** lập và duyệt phiếu xuất, điều chỉnh kho và ticket |
| N | `nhan_vien`: công việc được giao và chứng từ do mình lập |
| ~~X~~ | **[v3-bỏ]** Không còn nhóm quyền X. Điều chỉnh kho và ticket chỉ dành cho Q (QĐ-0311) |

**[v3-đổi] Phạm vi của A (D-PQ-01, D-PQ-03).** A chỉ được gọi:

- `/nhan_vien/*` và `/vai_tro` trong phạm vi quyền ghi ở §4;
- `/auth/*`: đăng nhập, xem hồ sơ và đổi mật khẩu của chính mình;
- `GET /lich_su_thao_tac` dạng rút gọn (§13);
- **[FE-MISS-001]** `GET /luu_luong_truy_cap` (§13, D-LL-01). Chỉ A được gọi;
- `GET /health`, `GET /api/v1/ping`.

Mọi endpoint nghiệp vụ còn lại trả 403 cho A, kể cả các endpoint chỉ đọc `/mat_hang`, `/danh_muc_mat_hang/`, `/nha_cung_cap`. Mỗi route nghiệp vụ phải có role guard loại trừ `quan_tri_vien`; kiểm thử chính sách rà soát toàn bộ route.

Backend dùng `VaiTro.ma_vai_tro` qua `NhanVien.vai_tro_id` làm nguồn quyền duy nhất, đọc lại từ DB ở mỗi request thay vì tin vai trò trong JWT. Không nhận hoặc trả `loai_nhan_vien`. Mỗi nhân viên chỉ có một vai trò.

**[v3-mới] Một quản trị viên (QĐ-NV).** Hệ thống có đúng một tài khoản A được bootstrap sẵn. API chặn tạo thêm A, cấp vai trò A cho tài khoản khác, hạ quyền hoặc khóa A hiện tại.

N chỉ đọc yêu cầu mình phụ trách, lệnh mình thực hiện, chứng từ mình tạo trong các công việc đó và **[v3-đổi]** phiếu xuất gắn với lệnh/yêu cầu đó; chỉ sửa/xóa/gửi chứng từ do mình tạo (hiện chỉ còn chứng từ hoàn thành sản xuất). N không lập phiếu xuất (QĐ-0311). Q đọc toàn bộ nghiệp vụ. A không có quyền Q. Chỉ tài khoản `hoat_dong` được dùng API; tài khoản `bi_khoa` bị chặn ở mọi request (403), kể cả JWT cấp trước khi khóa.

Tài nguyên tồn tại nhưng ngoài phạm vi người dùng trả 403; ID không tồn tại trả 404. Endpoint danh sách tự giới hạn phạm vi. **[v3-SQL]** Kiểm tra chủ chứng từ (kể cả phiếu xuất) bằng `nhan_vien_id`.

## 4. Xác thực và nhân viên

| Method | Path | Quyền | Input / output |
|---|---|---|---|
| POST | `/auth/dang_nhap` | Công khai | LoginInput → TokenRead |
| POST | `/auth/token` | Công khai | **[v3-mới]** Form OAuth2 `username`, `password` → token phẳng; chỉ phục vụ Swagger |
| GET | `/auth/me` | A/Q/N | → NhanVienRead đầy đủ của chính mình, có ETag |
| POST | `/auth/doi_mat_khau` | A/Q/N | DoiMatKhauInput → `{da_doi: true}` |
| GET | `/nhan_vien` | A/Q | Danh sách NhanVienRead; Q chỉ nhận projection giao việc |
| GET | `/nhan_vien/{id}` | A/Q hoặc chính mình | Q đọc người khác chỉ có projection giao việc |
| POST | `/nhan_vien` | A | NhanVienCreate → NhanVienRead |
| PATCH | `/nhan_vien/{id}` | A | NhanVienPatch → NhanVienRead |
| DELETE | `/nhan_vien/{id}` | A | **[v3-đổi]** LyDoInput; soft delete: hoat_dong → bi_khoa; 204 |
| PUT | `/nhan_vien/{id}/vai_tro` | A | `{vai_tro_id: int}` → NhanVienRead |
| ~~POST~~ | ~~`/nhan_vien/{id}/vo_hieu_hoa`~~ | ~~A~~ | **[v3-bỏ]** Thay bằng DELETE |
| POST | `/nhan_vien/{id}/mo_khoa` | A | LyDoInput; bi_khoa → hoat_dong; NhanVienRead |
| GET | `/vai_tro` | A/Q | Danh sách `{id, ma_vai_tro, ten_vai_tro, mo_ta}`, phân trang, sắp theo ID tăng dần |

Theo D-VT-01 (09/11/2026), bộ vai trò cố định `quan_tri_vien`, `quan_ly`, `nhan_vien`; không có API tạo/sửa/xóa vai trò. `mo_ta` là `string | null`, chỉ đọc, tóm tắt phạm vi theo SRS_v4 §2. Bổ sung field này vào response không đổi quyền, query, phân trang hay thứ tự. Bootstrap `"VaiTro".mo_ta` dùng `varchar(255) NULL`, không default; database đã khởi tạo chưa tự cập nhật khi sửa bootstrap. Bản contract và data model v3.1 trên Drive cần dev cập nhật riêng.

> v3: module `auth` giữ nguyên tên và đường dẫn, là ngoại lệ của quy tắc Việt hóa (QĐ-0311). Bổ sung `POST /auth/token` cho Swagger (QĐ-AUTH). DELETE nhân viên là soft delete; `POST /vo_hieu_hoa` bị bỏ (QĐ-NV).

LoginInput: `{"ten_dang_nhap": "...", "mat_khau": "..."}`, cả hai bắt buộc. **[v3-mới]** Chỉ đăng nhập bằng tên đăng nhập; `ten_dang_nhap` trim, tối đa 255 ký tự; `mat_khau` giữ nguyên, tối đa 1024 ký tự. TokenRead gồm `access_token`, `token_type: "bearer"`, `expires_in` (giây), `nhan_vien: NhanVienRead`. Sai tài khoản/mật khẩu trả 401 với thông báo chung; tài khoản bị khóa trả 403 `tai_khoan_bi_vo_hieu_hoa`.

**[v3-mới] Token (QĐ-AUTH, QĐ-0311):**

- JWT access token, TTL 60 phút (`expires_in: 3600`). Không có refresh token.
- Token mang phiên bản mật khẩu (`pwdv`). Sau khi đổi mật khẩu, mọi token cũ bị từ chối 401. Client đăng nhập lại để lấy token mới. Token không có `pwdv` không được chấp nhận.
- Mật khẩu mới hash bằng Argon2id; hash bcrypt cũ vẫn đọc được.

DoiMatKhauInput: `mat_khau_hien_tai`, `mat_khau_moi` bắt buộc; mật khẩu mới 8–1024 ký tự. Đổi mật khẩu và ghi audit cùng transaction.

NhanVienCreate bắt buộc `ten_dang_nhap`, `mat_khau`, `ma_nhan_vien`, `vai_tro_id`; tùy chọn nullable `ho_ten`, `ngay_sinh`, `so_dien_thoai`, `email`, `ngay_vao_lam`, `he_so_luong`.

| Field | Ràng buộc |
|---|---|
| `ten_dang_nhap` | Trim, 1–255 ký tự, duy nhất |
| `mat_khau` | 8–1024 ký tự, không trim |
| `ma_nhan_vien` | **[v3-SQL]** `NV-NNNNNN`, khác `NV-000000`, duy nhất |
| `vai_tro_id` | Integer dương 32-bit; không được là vai trò A |
| `he_so_luong` | Decimal dạng JSON string, 0–999.99, tối đa 2 chữ số thập phân |

Trùng tên đăng nhập hoặc mã trả 409 `ma_bi_trung`. NhanVienPatch chỉ nhận các trường hồ sơ tùy chọn; gửi tên đăng nhập, mã, mật khẩu, vai trò hoặc trạng thái trả 422. Body rỗng hoặc không đổi là no-op. NhanVienRead gồm `id`, `ten_dang_nhap`, `ma_nhan_vien`, hồ sơ, `vai_tro_id`, `ma_vai_tro`, `trang_thai`. Không có `loai_nhan_vien`, `is_active`, `mat_khau`, `tai_khoan_id`.

Projection giao việc cho Q: `id`, `ma_nhan_vien`, `ho_ten`, `vai_tro_id`, `ma_vai_tro`, `trang_thai`. N không được xem danh sách nhân viên.

Filter `/nhan_vien`: `q` (mã/họ tên), `vai_tro_id`, `trang_thai`; sort mặc định `id`, cho phép `id`, `ma_nhan_vien`, `ho_ten`, `ten_dang_nhap`. Thao tác ghi không nhận query.

**[v3-đổi] Khóa và mở khóa.** Không xóa nhân viên, không đổi vai trò, không hủy công việc/chứng từ.

| | DELETE `/nhan_vien/{id}` | POST `/nhan_vien/{id}/mo_khoa` |
|---|---|---|
| Body | LyDoInput bắt buộc | LyDoInput bắt buộc |
| If-Match | Bắt buộc | Bắt buộc |
| Chuyển trạng thái | hoat_dong → bi_khoa | bi_khoa → hoat_dong |
| Response | 204 | 200 NhanVienRead, ETag mới |
| Gọi sai trạng thái (ETag hiện hành) | 409, không ghi audit | 409 |
| Audit | `vo_hieu_hoa` | `sua`, có `ly_do`, trước/sau |
| Chặn | Tự khóa mình; khóa A | — |

Người được giao yêu cầu/lệnh phải tồn tại, đang hoat_dong và có vai trò `nhan_vien`. Mở khóa không cấp JWT mới.

`PUT /nhan_vien/{id}/vai_tro`: chỉ đổi giữa các vai trò không phải A; ghi `thu_hoi_quyen` và `cap_quyen` cùng transaction.

```json
{"data":{"id":12,"ten_dang_nhap":"nhanvien","ma_nhan_vien":"NV-000012","ho_ten":"Nhân viên mẫu","vai_tro_id":3,"ma_vai_tro":"nhan_vien","trang_thai":"hoat_dong"},"meta":{"request_id":"req-account"}}
```

## 5. Mặt hàng và nhà cung cấp

| Method | Path | Quyền | Schema |
|---|---|---|---|
| GET | `/danh_muc_mat_hang/` | Q/N | **[v3-mới]** Toàn bộ MatHangRead, không phân trang |
| GET | `/mat_hang` | **[v3-đổi]** Q/N | Danh sách MatHangRead |
| GET | `/mat_hang/{id}` | **[v3-đổi]** Q/N | MatHangRead, có ETag |
| POST | `/mat_hang` | Q | MatHangCreate → MatHangRead |
| PATCH | `/mat_hang/{id}` | Q | MatHangPatch → MatHangRead |
| DELETE | `/mat_hang/{id}` | Q | **[v3-đổi]** Soft delete `is_active=false`; 204 |
| GET | `/nha_cung_cap` | **[v3-đổi]** Q | Danh sách NhaCungCapRead |
| GET | `/nha_cung_cap/{id}` | **[v3-đổi]** Q | NhaCungCapRead, không ETag |
| POST | `/nha_cung_cap` | Q | NhaCungCapCreate → NhaCungCapRead, có `Location`, không ETag |
| ~~PATCH~~ | ~~`/nha_cung_cap/{id}`~~ | ~~Q~~ | **[v3-bỏ]** Trả 405 |
| ~~DELETE~~ | ~~`/nha_cung_cap/{id}`~~ | ~~Q~~ | **[v3-bỏ]** Trả 405 |

> v3: A mất quyền đọc mặt hàng và nhà cung cấp (D-PQ-03). Nhà cung cấp không được sửa hoặc xóa vì phiếu nhập tham chiếu trực tiếp và không lưu bản sao thông tin (QĐ-NCC).

### 5.1 Mặt hàng

MatHangCreate: bắt buộc `ma_mat_hang` (**[v3-SQL]** `MH-NNNNNN`), `sku`, `ten_mat_hang`, `loai_mat_hang`, `don_vi_tinh`, **[v3-đổi]** `don_gia` (integer VND không âm); tùy chọn `mau_sac`, `mo_ta`, `is_active` (mặc định true). Thiếu hoặc null `don_gia` trả 422 (QĐ-0311). `ten_mat_hang` thiếu, null, rỗng hoặc chỉ khoảng trắng trả 422.

**[v3-đổi]** MatHangRead = các trường Create + `id` + **[v3-mới]** `so_luong_ton: int`, `ton_kho_updated_at: timestamp|null`. Hai trường tồn chỉ đọc; gửi chúng trong POST/PATCH trả 422. Mặt hàng mới có `so_luong_ton=0`.

> v3: số dư gộp vào `"MatHang"` và trả qua MatHangRead, thay cho `/ton_kho` (QĐ-MH, D-PQ-04).

MatHangPatch nhận các trường Create dạng optional; gửi null cho field NOT NULL (gồm `don_gia`) trả 422. `ma_mat_hang`, `sku` không đổi sau khi được tham chiếu; `loai_mat_hang`, `don_vi_tinh` bất biến khi đã có BOM/chứng từ. Mã và SKU duy nhất kể cả khi đã ngừng hoạt động. **[v3-mới]** Kích hoạt lại bằng PATCH `is_active=true`.

**[v3-mới]** `don_gia` là giá dùng để tính tiền phiếu xuất (§10). Đổi `don_gia` không làm thay đổi phiếu xuất đã chốt giá.

`loai_mat_hang`: `nguyen_vat_lieu | linh_kien | ban_thanh_pham | thanh_pham`. `don_vi_tinh`, `mau_sac` là danh mục mở snake_case không dấu.

**[v3-đổi] DELETE `/mat_hang/{id}`** (QĐ-MH): bắt buộc If-Match; chỉ đặt `is_active=false`, không xóa dòng, không đổi số dư; được phép cả khi có tham chiếu hoặc còn tồn; ghi audit `vo_hieu_hoa`. Gọi lại khi đã ngừng (ETag hiện hành): 204, không ghi audit.

**[v3-mới] Đọc từ bộ nhớ (QĐ-MH, QĐ-0311).** Ba endpoint GET đọc từ snapshot trong bộ nhớ backend, nạp khi khởi động và cập nhật sau mỗi ghi thành công qua API, qua LISTEN/NOTIFY và đối soát định kỳ. Snapshot chưa sẵn sàng: 503 `danh_muc_chua_san_sang`. Hệ thống chạy một instance, một worker; giữ thiết kế này tới khi cần scale.

GET mặc định trả cả mặt hàng hoạt động và đã ngừng; chỉ lọc khi client gửi `is_active`. Filter `/mat_hang`: `q` (mã/tên/SKU), `loai_mat_hang`, `is_active`, `don_vi_tinh`, `mau_sac`, `don_gia_min`, `don_gia_max`; sort `id`, `ma_mat_hang`, `ten_mat_hang`, `don_gia`.

### 5.2 Nhà cung cấp

NhaCungCapCreate: `ma_ncc` (**[v3-SQL]** `NCC-NNNNNN`), `ten_ncc` bắt buộc; `so_dien_thoai`, `dia_chi`, `phuong`, `tinh` nullable. Read thêm `id`. Mã trùng trả 409 `ma_bi_trung`. Filter `q`, `tinh`, `phuong`; sort `id`, `ma_ncc`, `ten_ncc`.

> v3: `init.sql` cho phép `ten_ncc` null; API vẫn bắt buộc như v2. Ràng buộc chặt hơn schema không vi phạm schema.

## 6. BOM

**[v3-đổi]** Mục này được viết lại theo D-BOM-01 đến D-BOM-13. BOM theo mô hình SCD type 2: mỗi dòng `Bom` (`version`, `start_time`, `end_time`, `is_active`) là bản chụp cố định của công thức trong kỳ hiệu lực. Muốn đổi định mức thì tạo version mới.

| Method | Path | Quyền | Schema / tác động |
|---|---|---|---|
| GET | `/bom` | Q/N | Danh sách BomRead |
| GET | `/bom/{id}` | Q/N | BomRead |
| GET | `/bom/{id}/cau_truc` | Q/N | BomTreeRead |
| POST | `/bom` | Q | BomCreate → BomRead; **[v3-đổi]** kích hoạt ngay |
| ~~PATCH~~ | ~~`/bom/{id}`~~ | ~~Q~~ | **[v3-bỏ]** Trả 405 (D-BOM-02) |
| DELETE | `/bom/{id}` | Q | **[v3-đổi]** Xóa mềm, cho phép mọi BOM; 204 |
| POST | `/bom/{id}/kich_hoat` | Q | Body `{}`; BomRead; **[v3-đổi]** quay lại một version |

A nhận 403 ở cả 6 endpoint (D-BOM-09). Không ETag/If-Match (D-BOM-06). Mọi ghi giữ `pg_advisory_xact_lock(20261020, 2)` tới khi commit/rollback.

**BomCreate:** `mat_hang_id`, `chi_tiet: [{mat_hang_id, so_luong}]` bắt buộc, `so_luong > 0`. Mỗi BOM mô tả một đơn vị đầu ra. **[v3-đổi]** Gửi `version`, `is_active`, `start_time`, `end_time` trả 422.

**[v3-đổi] Tạo = kích hoạt ngay (D-BOM-03).** Server cấp `version = max(version) + 1` theo mặt hàng đầu ra; BOM mới `is_active=true`, `start_time=now()`. BOM hiện hành cũ được đóng (`is_active=false`, `end_time=now()`) trong cùng transaction, trước khi chèn BOM mới.

**[v3-đổi] Kích hoạt = quay lại một version (D-BOM-04).** Đóng BOM hiện hành của cùng mặt hàng, mở BOM được chọn (`is_active=true`, `end_time=NULL`), giữ nguyên `start_time` vì trigger `bao_ve_bom_da_dung` cấm đổi `start_time` của BOM đã dùng. Kích hoạt BOM đang hoạt động: 200, không ghi audit. Kích hoạt BOM không hoạt động chạy lại kiểm tra loại mặt hàng, BOM con và chu trình.

**[v3-đổi] Xóa = xóa mềm (D-BOM-05).** Chỉ đặt `is_active=false`, `end_time=now()`; cho phép với mọi BOM. Xóa BOM đã không hoạt động: 204, không ghi audit.

**[v3-mới] Loại mặt hàng (D-BOM-07):** đầu ra là `ban_thanh_pham` hoặc `thanh_pham`; thành phần là `nguyen_vat_lieu`, `linh_kien` hoặc `ban_thanh_pham`. Sai loại trả 422 `du_lieu_khong_hop_le`. Mặt hàng ngừng hoạt động trả 409 `mat_hang_ngung_hoat_dong`.

**[v3-đổi] BOM con, chu trình, thành phần trùng (D-BOM-08):**

| Trường hợp | Kết quả |
|---|---|
| Thành phần `ban_thanh_pham` chưa có BOM hiện hành | 409 `thieu_bom` |
| Tự tham chiếu | **[v3-đổi]** 422 `du_lieu_khong_hop_le`, `details[].field = "chi_tiet"` |
| Chu trình gián tiếp | 409 `bom_co_chu_trinh` |
| Thành phần trùng; `so_luong <= 0` | 422 `du_lieu_khong_hop_le` |

**BomRead:** `id`, `mat_hang_id`, `version`, `start_time`, `end_time`, `is_active`, `da_duoc_su_dung`, `chi_tiet: [{id, mat_hang_id, so_luong}]`. **[v3-mới]** `da_duoc_su_dung` = có ít nhất một `"LenhSanXuat"` với `bom_id` này, mọi trạng thái (D-BOM-13).

**BomTreeRead:** `bom_id`, `mat_hang_id`, `version`, `children`; node con gồm `mat_hang_id`, `so_luong_tren_mot_don_vi_cha`, `bom_id: int|null`, `children`. **[v3-mới]** `bom_id: null` khi BOM con đã bị xóa mềm hoặc chưa có BOM hiện hành.

**[v3-mới] Audit (D-BOM-11)** với `loai_doi_tuong='cong_thuc'`: POST ghi `tao` (+ `vo_hieu_hoa` cho BOM cũ bị đóng); kích hoạt ghi `sua` (+ `vo_hieu_hoa` cho BOM bị thay); DELETE ghi `vo_hieu_hoa` nếu BOM đang hoạt động.

Filter: `mat_hang_id`, `version`, `is_active`; sort `id`, `version`, `start_time`.

## 7. Giao dịch kho và phiếu nhập

| Method | Path | Quyền | Schema / điều kiện |
|---|---|---|---|
| ~~GET~~ | ~~`/ton_kho`~~ | ~~Q/N~~ | **[v3-bỏ]** Dùng `GET /mat_hang` (D-PQ-04) |
| ~~GET~~ | ~~`/ton_kho/{mat_hang_id}`~~ | ~~Q/N~~ | **[v3-bỏ]** Dùng `GET /mat_hang/{id}` (D-PQ-04) |
| GET | `/giao_dich_kho` | Q | Danh sách GiaoDichRead |
| GET | `/giao_dich_kho/{id}` | Q | GiaoDichRead và nguồn/điều chỉnh |
| GET | `/phieu_nhap` | Q | Danh sách PhieuNhapRead |
| GET | `/phieu_nhap/{id}` | Q | PhieuNhapRead |
| POST | `/phieu_nhap` | Q | PhieuNhapCreate → PhieuNhapRead nhap |
| PATCH | `/phieu_nhap/{id}` | Q | PhieuNhapPatch; chỉ nhap |
| DELETE | `/phieu_nhap/{id}` | Q | Chỉ nhap |
| POST | `/phieu_nhap/{id}/hoan_tat` | Q | Body `{}`; cộng kho, ghi sổ; ActionRead |

**[v3-mới] Số dư luôn khớp ledger (QĐ-0311).** `MatHang.so_luong_ton` luôn bằng tổng `so_luong_bien_dong` của các giao dịch đã ghi sổ của mặt hàng. Mỗi lần ghi sổ cập nhật số dư, `ton_kho_updated_at`, giao dịch, chứng từ và audit cùng transaction. Không sửa số dư trực tiếp. Seed cũng theo quy tắc này: tạo chứng từ và giao dịch đã ghi sổ trước, rồi tính `so_luong_ton` từ tổng ledger (`seed.sql` hiện đã làm vậy).

GiaoDichRead: `id`, `mat_hang_id`, `loai_giao_dich`, `so_luong_bien_dong` (có dấu), `chi_tiet_phieu_nhap_id`, `chi_tiet_phieu_xuat_id`, `chung_tu_hoan_thanh_sx_id`, `chi_tiet_phieu_dieu_chinh_id` (đúng một khác null), `nhan_vien_id`, `posted_at`. **[v3-SQL]** GET chi tiết của giao dịch `nhap_vat_tu` bổ sung `dieu_chinh_ids: int[]` và `so_luong_hieu_luc` (lượng gốc + tổng điều chỉnh đã ghi sổ trỏ nguồn); các loại khác trả `dieu_chinh_ids=[]`, `so_luong_hieu_luc=null` vì chỉ giao dịch nhập vật tư được điều chỉnh. Filter `mat_hang_id`, `loai_giao_dich`, `nhan_vien_id`, `tu_ngay`, `den_ngay` (theo `posted_at`); sort `id`, `posted_at`.

**[v3-SQL] PhieuNhapCreate:**

| Field | Ràng buộc |
|---|---|
| `ncc_id` | **[v3-SQL]** Integer, **bắt buộc** (v2: tùy chọn, nullable). Nhà cung cấp phải tồn tại |
| `ngay_nhap` | **[v3-SQL] [v3-mới]** Ngày `YYYY-MM-DD`, **bắt buộc**. Ngày nhập nghiệp vụ do Q khai báo, có thể khác ngày tạo bản ghi |
| `ghi_chu` | **[v3-SQL] [v3-mới]** String hoặc null, tùy chọn. Ghi chú chung: nguồn nhập, tình trạng hàng, thông tin đối soát |
| `chi_tiet` | Bắt buộc: `[{mat_hang_id, so_luong, don_gia_thuc}]`; `so_luong > 0`; `don_gia_thuc` integer VND không âm, do Q khai báo theo giá mua thực tế |

Chỉ nhập `nguyen_vat_lieu`/`linh_kien`; nhập bán thành phẩm/thành phẩm phải qua chứng từ hoàn thành. PhieuNhapPatch nhận `ncc_id`, `ngay_nhap`, `ghi_chu`, `chi_tiet` optional; `ncc_id`, `ngay_nhap` không nhận null; `ghi_chu` null để xóa.

PhieuNhapRead: `id`, `ma_phieu_nhap`, `nhan_vien_id`, `ncc_id`, **[v3-SQL]** `ngay_nhap`, `ghi_chu`, `tong_tien`, `trang_thai`, `created_at`, `chi_tiet: [{id, mat_hang_id, so_luong, don_gia_thuc, tong_gia}]`. `tong_gia=so_luong*don_gia_thuc`; `tong_tien=sum(tong_gia)`.

Filter: `q`, `trang_thai`, `ncc_id`, `nhan_vien_id`, `tu_ngay`, `den_ngay` (**[v3-đổi]** lọc theo `ngay_nhap`); sort `id`, **[v3-mới]** `ngay_nhap`, `created_at`, `ma_phieu_nhap`.

Hoàn tất: `nhap → hoan_thanh`; mỗi dòng sinh một `nhap_vat_tu` dương, cộng tồn và ghi audit cùng transaction. **[v3-mới]** Trong cùng transaction, hệ thống tự kiểm tra lại các yêu cầu đang `cho_bo_sung_vat_tu` (§8). Lỗi thì rollback, giữ nhap. Không có bước duyệt độc lập. Phiếu `hoan_thanh` không sửa/xóa; sai lượng phải sửa bằng phiếu điều chỉnh (§12).

## 8. Yêu cầu và kế hoạch sản xuất

**[v3-SQL]** Mục này được chỉnh theo `"YeuCauSanXuat"`, `"LenhSanXuat"` và mô tả nghiệp vụ trong `init.sql`: thiếu nguyên vật liệu không chặn việc gửi yêu cầu và tạo lệnh; yêu cầu chuyển sang trạng thái mới `cho_bo_sung_vat_tu`.

| Method | Path | Quyền | Schema / điều kiện |
|---|---|---|---|
| GET | `/yeu_cau_san_xuat` | Q/N | Danh sách YeuCauRead |
| GET | `/yeu_cau_san_xuat/{id}` | Q/N | YeuCauRead |
| POST | `/yeu_cau_san_xuat` | Q | YeuCauCreate → nhap |
| PATCH | `/yeu_cau_san_xuat/{id}` | Q | YeuCauPatch; chỉ nhap |
| DELETE | `/yeu_cau_san_xuat/{id}` | Q | Chỉ nhap chưa có phụ thuộc |
| POST | `/yeu_cau_san_xuat/{id}/tinh_ke_hoach` | Q/N | Body `{}`; KeHoachPreview; chỉ yêu cầu nhap và người có phạm vi |
| POST | `/yeu_cau_san_xuat/{id}/gui` | Q | GuiYeuCauInput → YeuCauRead và KeHoachRead; **[v3-SQL]** không còn bị chặn khi thiếu vật tư |
| GET | `/yeu_cau_san_xuat/{id}/ke_hoach` | Q/N | KeHoachRead; chưa gửi trả 409 |
| POST | `/yeu_cau_san_xuat/{id}/huy` | Q | LyDoInput → YeuCauRead |

**[v3-SQL] YeuCauCreate:** `mat_hang_id` (thành phẩm), `so_luong > 0` bắt buộc; `nhan_vien_duoc_giao_id` integer **tùy chọn, nullable** khi còn nhap. v2 bắt buộc người được giao ngay khi tạo nháp; `init.sql` chỉ bắt buộc khi yêu cầu khác `nhap`/`da_huy`. Người được giao nếu gửi phải tồn tại (404), đang hoat_dong và có vai trò `nhan_vien` (409 `nguoi_duoc_giao_khong_hop_le`). YeuCauPatch nhận ba trường trên; `nhan_vien_duoc_giao_id` được đặt null khi còn nhap.

```json
{"mat_hang_id":1,"so_luong":10,"nhan_vien_duoc_giao_id":12}
```

YeuCauRead: `id`, `ma_yeu_cau_san_xuat`, `mat_hang_id`, `so_luong`, `nhan_vien_id` (người tạo), **[v3-SQL]** `nhan_vien_duoc_giao_id: int|null`, `trang_thai`, `created_at`, `completed_at`, và các trường tính toán `so_luong_da_xuat`, `so_luong_con_phai_xuat`, `lenh_san_xuat_ids`.

**Token kế hoạch.** `/tinh_ke_hoach` trả `ke_hoach_token`, một token có chữ ký gắn với yêu cầu, người phụ trách, tồn dùng khi tính, BOM và kết quả tính; TTL 10 phút (QĐ-0311). `/gui` nhận token này, tính lại dưới transaction và so với kết quả trong token; nếu token hết hạn hoặc kết quả khác, trả 409 `ke_hoach_da_thay_doi` để Q xem lại kế hoạch mới. Client không gửi cây lệnh hay định mức.

```json
{"ke_hoach_token": "opaque-token-tu-tinh-ke-hoach"}
```

KeHoachPreview:

```json
{
 "data": {
 "yeu_cau_san_xuat_id": 101,
 "tinh_luc": "2026-10-13T10:24:00Z",
 "ke_hoach_token": "opaque-token",
 "so_luong_yeu_cau": 10,
 "ton_thanh_pham": 3,
 "so_luong_can_san_xuat": 7,
 "du_dieu_kien_gui": true,
 "thieu_vat_tu": false,
 "lenh_du_kien": [
 {"ma_tam": "L1", "ma_cha_tam": null, "mat_hang_id": 1, "bom_id": 5, "so_luong": 7,
 "nhu_cau_truc_tiep": [{"mat_hang_id": 20, "so_luong_can": 14}]},
 {"ma_tam": "L2", "ma_cha_tam": "L1", "mat_hang_id": 20, "bom_id": 6, "so_luong": 6,
 "nhu_cau_truc_tiep": [{"mat_hang_id": 30, "so_luong_can": 6}]}
 ],
 "vat_tu": [{"mat_hang_id": 30, "ma_mat_hang": "MH-000030", "ten_mat_hang": "Vành bánh xe",
 "don_vi_tinh": "chiec", "so_luong_can_tu_kho": 6, "so_luong_hien_co": 20, "so_luong_thieu": 0}]
 },
 "meta": {"request_id": "req-plan"}
}
```

**[v3-SQL]** `du_dieu_kien_gui=false` chỉ khi thiếu BOM hiện hành cho mặt hàng cần sản xuất, hoặc người phụ trách chưa có/không hợp lệ. Thiếu vật tư không làm `du_dieu_kien_gui=false`; preview báo `thieu_vat_tu=true` và `so_luong_thieu` trên từng dòng `vat_tu`. `so_luong_hien_co`, `ton_thanh_pham` đọc từ `MatHang.so_luong_ton`.

Quy tắc tính: lượng sản xuất `max(yêu cầu - tồn thành phẩm, 0)`; dùng tồn bán thành phẩm trước; chỉ tạo lệnh con cho phần bán thành phẩm còn thiếu. Phân bổ tồn giữa các nhánh không dùng cùng tồn hai lần; đây không phải giữ chỗ kho. Kết quả tính là ảnh chụp; khi duyệt xuất vẫn kiểm tra lại tồn.

**[v3-SQL] Gửi yêu cầu:** kiểm tra người phụ trách đã có và hợp lệ, rồi trong cùng transaction lưu cây lệnh ở trạng thái `nhap` (mỗi lệnh có `bom_id` đã chọn và bản chụp nhu cầu trực tiếp) và chuyển yêu cầu:

- sang `da_gui` nếu đủ vật tư;
- sang **`cho_bo_sung_vat_tu`** nếu thiếu vật tư. Yêu cầu và các lệnh đã tạo được giữ nguyên.

Nhánh đủ thành phẩm gửi yêu cầu mà không tạo lệnh. Kế hoạch đã gửi không được tự tính lại theo BOM mới hoặc tồn mới; lệnh giữ đúng `bom_id` của version đã chọn (D-BOM-02).

**[v3-mới] [v3-SQL] Tự kiểm tra lại vật tư (QĐ-0311).** Mỗi lần phiếu nhập hoàn tất (`POST /phieu_nhap/{id}/hoan_tat`), trong cùng transaction, hệ thống kiểm tra lại mọi yêu cầu đang `cho_bo_sung_vat_tu`. Với từng yêu cầu, so tồn hiện tại với phần nhu cầu chưa cấp của các lệnh chưa hoàn thành/chưa hủy; không sửa lượng, BOM hay nhu cầu của lệnh:

- đủ: yêu cầu về `da_gui` nếu chưa bắt đầu, hoặc `dang_thuc_hien` nếu đã có lệnh bắt đầu; ghi audit `sua` cho yêu cầu đó;
- chưa đủ: giữ `cho_bo_sung_vat_tu`.

Không có endpoint kiểm tra thủ công. Vì không giữ chỗ kho, nhiều yêu cầu có thể cùng được đánh giá đủ dựa trên cùng một lượng tồn; khi duyệt phiếu xuất vật tư, hệ thống vẫn kiểm tra lại tồn. Yêu cầu chỉ vào `cho_bo_sung_vat_tu` lúc gửi yêu cầu.

KeHoachRead: `yeu_cau_san_xuat_id`, `lenh: [LenhRead]` với cha/con và nhu cầu đã lưu. Nhánh đủ hàng trả `lenh=[]`.

Hủy yêu cầu chỉ khi chưa phát sinh ghi sổ. Trong cùng transaction: hủy các lệnh từ dưới lên, xóa phiếu nháp, chuyển phiếu chờ duyệt sang tu_choi với lý do hủy. Có phụ thuộc đã ghi sổ thì trả 409.

Filter: `q`, `mat_hang_id`, `trang_thai`, `nhan_vien_duoc_giao_id`, `tu_ngay`, `den_ngay`; sort `id`, `created_at`, `ma_yeu_cau_san_xuat`.

## 9. Lệnh sản xuất

| Method | Path | Quyền | Schema / điều kiện |
|---|---|---|---|
| GET | `/lenh_san_xuat` | Q/N | Danh sách LenhRead |
| GET | `/lenh_san_xuat/{id}` | Q/N | LenhRead |
| PATCH | `/lenh_san_xuat/{id}` | Q | `{nhan_vien_id: int\|null}`; chỉ nhap |
| GET | `/lenh_san_xuat/{id}/vat_tu` | Q/N | VatTuLenhRead |
| POST | `/lenh_san_xuat/{id}/gui` | Q | Body `{}`; nhap → da_gui |
| POST | `/lenh_san_xuat/{id}/bat_dau` | N được giao | Body `{}`; da_gui → dang_thuc_hien |
| POST | `/lenh_san_xuat/{id}/huy` | Q | LyDoInput; chỉ khi chưa có cấp vật tư/đầu ra đã ghi sổ và không còn lệnh con hoạt động |

Không có POST tạo lệnh thủ công; lệnh được tạo khi gửi yêu cầu (§8). Không PATCH số lượng/BOM/cha/đầu ra. Không có endpoint hoàn tất lệnh trực tiếp.

LenhRead: `id`, `ma_lenh_san_xuat`, `yeu_cau_san_xuat_id`, `lenh_san_xuat_cha_id`, `mat_hang_id`, `bom_id`, `so_luong`, **[v3-SQL]** `nhan_vien_id: int|null`, `trang_thai`, `created_at`, `started_at`, `completed_at`, `nhu_cau_truc_tiep: [{id, mat_hang_id, so_luong_can}]`, `so_luong_da_hoan_thanh`, `so_luong_con_phai_hoan_thanh`, `lenh_con_ids`.

VatTuLenhRead: `lenh_san_xuat_id`, `du_dieu_kien_bat_dau`, `chi_tiet: [{mat_hang_id, so_luong_can, so_luong_da_cap, so_luong_con_phai_cap, ton_hien_tai}]`. **[v3-SQL]** Lượng đã cấp = tổng phiếu xuất vật tư `da_duyet` của lệnh; không có điều chỉnh phiếu xuất trong phiên bản này. Tổng đã cấp không vượt nhu cầu.

**[v3-SQL]** `nhan_vien_id` được để trống khi lệnh còn nhap; gửi lệnh bắt buộc có người thực hiện hợp lệ. Thiếu vật tư không chặn gửi lệnh. Chỉ bắt đầu khi mọi vật tư đã được cấp đủ qua phiếu xuất `da_duyet`; bắt đầu không đổi kho. Lệnh con phải được duyệt nhập đầu ra trước khi xuất đầu ra đó cho lệnh cha. Lệnh tự hoàn thành khi tổng đầu ra đã duyệt đạt `so_luong`. Gửi lệnh được phép khi yêu cầu ở `da_gui`, `cho_bo_sung_vat_tu` hoặc `dang_thuc_hien`.

Filter: `q`, `yeu_cau_san_xuat_id`, `lenh_san_xuat_cha_id`, `nhan_vien_id`, `mat_hang_id`, `trang_thai`, `tu_ngay`, `den_ngay`; sort `id`, `created_at`, `ma_lenh_san_xuat`.

## 10. Phiếu xuất

| Method | Path | Quyền | Input / điều kiện |
|---|---|---|---|
| GET | `/phieu_xuat` | Q/N | Danh sách PhieuXuatRead; N chỉ thấy phiếu của lệnh/yêu cầu được giao |
| GET | `/phieu_xuat/{id}` | Q/N | PhieuXuatRead |
| POST | `/phieu_xuat` | **[v3-đổi]** Q | PhieuXuatCreate → nhap |
| PATCH | `/phieu_xuat/{id}` | **[v3-đổi]** Q | Chỉ `chi_tiet`; trạng thái nhap |
| DELETE | `/phieu_xuat/{id}` | **[v3-đổi]** Q | Chỉ nhap |
| POST | `/phieu_xuat/{id}/gui` | **[v3-đổi]** Q | Body `{}` |
| POST | `/phieu_xuat/{id}/duyet` | Q | Body `{}`; chốt giá, trừ kho; ActionRead |
| POST | `/phieu_xuat/{id}/tu_choi` | Q | LyDoInput |
| POST | `/phieu_xuat/{id}/ve_nhap` | **[v3-đổi]** Q | LyDoInput; chỉ tu_choi |

> v3 (QĐ-0311): chỉ Q lập và xử lý phiếu xuất. v2 cho N lập, sửa, gửi và về nháp phiếu xuất. N vẫn đọc được phiếu xuất của công việc mình được giao. Các trạng thái `nhap/cho_duyet/da_duyet/tu_choi` giữ theo `init.sql`.

**[v3-đổi] PhieuXuatCreate:**

```json
{
 "loai_phieu": "xuat_vat_tu",
 "lenh_san_xuat_id": 201,
 "yeu_cau_san_xuat_id": null,
 "chi_tiet": [{"mat_hang_id": 20, "so_luong": 8}]
}
```

Đúng một FK bắt buộc theo loại (CHECK `ck_phieu_xuat_nguon`): `xuat_vat_tu` gắn lệnh `da_gui`/`dang_thuc_hien`, mặt hàng thuộc nhu cầu trực tiếp của lệnh (vật tư gồm NVL, linh kiện và bán thành phẩm); `xuat_thanh_pham` gắn yêu cầu `da_gui`/`dang_thuc_hien` và đúng mặt hàng yêu cầu; **[v3-mới]** yêu cầu đang `cho_bo_sung_vat_tu` không được xuất thành phẩm (409 `trang_thai_khong_hop_le`, QĐ-0311). Loại và nguồn bất biến sau tạo.

**[v3-đổi] Giá xuất lấy từ `MatHang.don_gia` lúc Q duyệt (QĐ-0311).** Client không gửi giá; gửi `don_gia_thuc` trả 422. Khi còn `nhap`, `cho_duyet` hoặc `tu_choi`, `don_gia_thuc`, `tong_gia` và `tong_tien` là `null`. Khi duyệt, trong cùng transaction ghi sổ, server đọc `MatHang.don_gia` của từng dòng (dòng `MatHang` đã được khóa), ghi `don_gia_thuc`, tính `tong_gia = so_luong * don_gia_thuc` và `tong_tien = sum(tong_gia)`. Sau khi duyệt, giá trên phiếu không đổi dù `MatHang.don_gia` thay đổi. Mọi mặt hàng đều có `don_gia` (§5.1), nên không có trường hợp thiếu giá lúc duyệt. Q được duyệt cả phiếu do chính mình lập (QĐ-0311).

> v3: v2 để người lập phiếu tự khai `don_gia_thuc`. `tong_tien` là giá trị hàng xuất tính theo đơn giá danh mục; đây không phải giá vốn FIFO/bình quân.

**[v3-SQL]** PhieuXuatRead: `id`, `ma_phieu_xuat`, **`nhan_vien_id`** (Q lập phiếu), `loai_phieu`, `yeu_cau_san_xuat_id`, `lenh_san_xuat_id`, `tong_tien: int|null`, `trang_thai`, `created_at`, `chi_tiet: [{id, mat_hang_id, so_luong, don_gia_thuc: int|null, tong_gia: int|null}]`. Không còn `ma_nhan_vien`.

Ví dụ phiếu xuất sau khi duyệt:

```json
{"data":{"id":601,"ma_phieu_xuat":"PX-202610-000601","nhan_vien_id":2,"loai_phieu":"xuat_vat_tu","yeu_cau_san_xuat_id":null,"lenh_san_xuat_id":201,"tong_tien":800000,"trang_thai":"da_duyet","created_at":"2026-10-14T15:25:00Z","chi_tiet":[{"id":701,"mat_hang_id":20,"so_luong":8,"don_gia_thuc":100000,"tong_gia":800000}]},"meta":{"request_id":"req-issue"}}
```

Gửi không trừ tồn. Duyệt khóa phiếu, dòng `MatHang` và lệnh/yêu cầu; kiểm tra đủ tồn và không vượt nhu cầu trực tiếp của lệnh hoặc tổng lượng yêu cầu; chốt giá; ghi giao dịch âm, trừ `MatHang.so_luong_ton`, cập nhật tiến độ và audit cùng transaction. Lỗi thì giữ cho_duyet. **[v3-SQL]** Phiếu `da_duyet` bất biến; chưa hỗ trợ điều chỉnh phiếu xuất.

Yêu cầu chuyển `dang_thuc_hien` khi lệnh đầu tiên bắt đầu hoặc khi ghi sổ xuất thành phẩm một phần, trừ khi đang `cho_bo_sung_vat_tu` (khi đó chỉ đổi qua bước tự kiểm tra lúc hoàn tất phiếu nhập, §8). Xuất đủ thành phẩm chuyển yêu cầu sang `hoan_thanh`, kể cả trực tiếp từ `da_gui`.

**[v3-SQL]** Filter: `q`, `loai_phieu`, `trang_thai`, `nhan_vien_id`, `yeu_cau_san_xuat_id`, `lenh_san_xuat_id`, `tu_ngay`, `den_ngay`; sort `id`, `created_at`, `ma_phieu_xuat`. Không còn filter `ma_nhan_vien`.

## 11. Chứng từ hoàn thành sản xuất

| Method | Path | Quyền | Input / điều kiện |
|---|---|---|---|
| GET | `/chung_tu_hoan_thanh_sx` | Q/N | Danh sách HoanThanhRead |
| GET | `/chung_tu_hoan_thanh_sx/{id}` | Q/N | HoanThanhRead |
| POST | `/chung_tu_hoan_thanh_sx` | N được giao lệnh | HoanThanhCreate → nhap |
| PATCH | `/chung_tu_hoan_thanh_sx/{id}` | N chủ phiếu | HoanThanhPatch; chỉ nhap |
| DELETE | `/chung_tu_hoan_thanh_sx/{id}` | N chủ phiếu | Chỉ nhap |
| POST | `/chung_tu_hoan_thanh_sx/{id}/gui` | N chủ phiếu | Body `{}` |
| POST | `/chung_tu_hoan_thanh_sx/{id}/duyet` | Q | Body `{}`; ActionRead |
| POST | `/chung_tu_hoan_thanh_sx/{id}/tu_choi` | Q | LyDoInput |
| POST | `/chung_tu_hoan_thanh_sx/{id}/ve_nhap` | N chủ phiếu | LyDoInput |

HoanThanhCreate: `lenh_san_xuat_id`, `so_luong_hoan_thanh > 0`, `finish_time` bắt buộc. HoanThanhPatch chỉ nhận `so_luong_hoan_thanh`, `finish_time`. Lệnh phải ở `dang_thuc_hien` khi tạo/gửi/duyệt. `finish_time` là thời điểm sản xuất xong do nhân viên khai báo, không trước `started_at` và không ở tương lai lúc gửi.

HoanThanhRead: `id`, `ma_phieu`, `lenh_san_xuat_id`, `so_luong_hoan_thanh`, `nhan_vien_id`, `trang_thai`, `finish_time`, **[v3-SQL]** `created_at`, + `mat_hang_id` lấy từ lệnh.

Duyệt khóa lệnh, kiểm tra tổng đầu ra đã duyệt không vượt lượng lệnh và phù hợp vật tư đã cấp; mỗi chứng từ một đợt, một giao dịch `nhap_san_pham_san_xuat` dương; cộng kho và cập nhật lệnh cùng transaction; không trừ lại vật tư. **[v3-SQL]** Không có điều chỉnh chứng từ hoàn thành; tiến độ chỉ tính từ chứng từ đã duyệt.

Filter: `q`, `lenh_san_xuat_id`, `mat_hang_id`, `nhan_vien_id`, `trang_thai`, `tu_ngay`, `den_ngay` (theo `finish_time`); sort `id`, `finish_time`, `ma_phieu`.

## 12. Điều chỉnh phiếu nhập và ticket lỗi

**[v3-SQL]** Mục này được viết lại theo `"PhieuDieuChinhKho"`, `"ChiTietPhieuDieuChinhKho"`, `"TicketLoiDieuChinh"`, `"ChiTietTicketLoiDieuChinh"` và trigger trong `init.sql`. Khác biệt chính so với v2:

- Phiếu điều chỉnh chỉ dùng để sửa số lượng của **một phiếu nhập đã `hoan_thanh`**. Không điều chỉnh kiểm kê, phiếu xuất hay chứng từ hoàn thành.
- Q tự xác nhận: `nhap → da_xac_nhan`. Không có gửi/duyệt/từ chối/về nháp.
- Xác nhận thất bại: phiếu chuyển `loi` và một **ticket mới** được tạo. Phiếu `loi` bất biến, không retry; muốn thử lại thì tạo phiếu mới.
- Ticket gắn với phiếu nhập, không gắn với phiếu điều chỉnh, và lưu bản chụp các dòng đề nghị thất bại.

Mọi endpoint chỉ dành cho Q (QĐ-0311); N và A nhận 403.

| Method | Path | Quyền | Input / điều kiện |
|---|---|---|---|
| GET | `/phieu_dieu_chinh_kho` | Q | Danh sách DieuChinhRead |
| GET | `/phieu_dieu_chinh_kho/{id}` | Q | DieuChinhRead |
| POST | `/phieu_dieu_chinh_kho` | Q | DieuChinhCreate → nhap |
| PATCH | `/phieu_dieu_chinh_kho/{id}` | Q | DieuChinhPatch; chỉ nhap |
| DELETE | `/phieu_dieu_chinh_kho/{id}` | Q | Chỉ nhap |
| POST | `/phieu_dieu_chinh_kho/{id}/xac_nhan` | Q | **[v3-mới] [v3-SQL]** Body `{}`; nhap → da_xac_nhan; ActionRead, hoặc lỗi kèm ticket |
| ~~POST~~ | ~~`/phieu_dieu_chinh_kho/{id}/gui`~~ | ~~X~~ | **[v3-bỏ] [v3-SQL]** Không có bước gửi |
| ~~POST~~ | ~~`/phieu_dieu_chinh_kho/{id}/duyet`~~ | ~~X~~ | **[v3-bỏ] [v3-SQL]** Thay bằng `xac_nhan` |
| ~~POST~~ | ~~`/phieu_dieu_chinh_kho/{id}/tu_choi`~~ | ~~X~~ | **[v3-bỏ] [v3-SQL]** |
| ~~POST~~ | ~~`/phieu_dieu_chinh_kho/{id}/ve_nhap`~~ | ~~X~~ | **[v3-bỏ] [v3-SQL]** Phiếu `loi` bất biến |
| GET | `/ticket_loi_dieu_chinh` | Q | Danh sách TicketRead |
| GET | `/ticket_loi_dieu_chinh/{id}` | Q | TicketRead |
| POST | `/ticket_loi_dieu_chinh/{id}/nhan_xu_ly` | Q | Body `{}`; cho_xu_ly → dang_xu_ly; người xử lý lấy từ JWT |
| POST | `/ticket_loi_dieu_chinh/{id}/giai_quyet` | Q | `{ket_qua_xu_ly: string}` không rỗng; đóng ticket |

### 12.1 Phiếu điều chỉnh

**DieuChinhCreate:**

```json
{
 "phieu_nhap_id": 41,
 "ly_do": "Phiếu nhập ghi 100, thực tế nhận 90",
 "chi_tiet": [{"giao_dich_goc_id": 501, "so_luong_dung": 90}]
}
```

| Field | Ràng buộc |
|---|---|
| `phieu_nhap_id` | **[v3-SQL] [v3-mới]** Bắt buộc; phiếu nhập phải `hoan_thanh` |
| `ly_do` | Bắt buộc, không rỗng |
| `chi_tiet[].giao_dich_goc_id` | **[v3-SQL]** Bắt buộc; phải là giao dịch `nhap_vat_tu` của chính phiếu nhập ở header. Không trùng trong cùng phiếu |
| `chi_tiet[].so_luong_dung` | **[v3-SQL] [v3-mới]** Integer ≥ 0; số lượng đúng do Q xác định, có thể bằng 0 |

> v3: v2 nhận `so_luong_bien_dong` và cho phép nguồn null (kiểm kê). `init.sql` bắt buộc giao dịch gốc và lưu số lượng đúng; biến động do server tính.

Server suy ra `mat_hang_id` từ giao dịch gốc và tính, rồi tính lại dưới khóa khi xác nhận:

- `so_luong_hieu_luc_truoc` = lượng nhập gốc + tổng điều chỉnh đã ghi sổ trỏ cùng nguồn;
- `so_luong_bien_dong` = `so_luong_dung - so_luong_hieu_luc_truoc`, phải khác 0. Bằng 0 trả 422.

Ví dụ nhập 100, điều chỉnh về 80, rồi về 85: lần thứ hai có biến động +5.

DieuChinhPatch: `ly_do`, `chi_tiet` optional; chỉ nhap; không đổi `phieu_nhap_id`.

**[v3-SQL]** DieuChinhRead: `id`, `ma_phieu`, `phieu_nhap_id`, `nhan_vien_id`, `ly_do`, `trang_thai` (`nhap | da_xac_nhan | loi`), `created_at`, `confirmed_at` (chỉ có khi xác nhận thành công), `chi_tiet: [{id, mat_hang_id, giao_dich_goc_id, so_luong_hieu_luc_truoc, so_luong_dung, so_luong_bien_dong}]`. Không còn `ticket_id`.

**Xác nhận** (`POST /xac_nhan`, bắt buộc If-Match): khóa phiếu nhập nguồn, phiếu điều chỉnh và các dòng `MatHang` theo thứ tự thống nhất; tính lại lượng hiệu lực; kiểm tra mọi dòng. Nếu mọi dòng hợp lệ: sinh giao dịch `dieu_chinh_ton_kho` cho từng dòng, cập nhật tồn, đặt `da_xac_nhan` và `confirmed_at`, ghi audit `xac_nhan`, cùng transaction. Không xác nhận từng phần. Gọi lại khi đã `da_xac_nhan` trả kết quả cũ với `da_ghi_so_truoc_do=true`. Gọi khi `loi` trả 409 `trang_thai_khong_hop_le`.

**Thất bại** (ví dụ giảm lượng làm tồn âm): rollback toàn bộ thay đổi kho. Một transaction riêng khóa lại phiếu, kiểm tra chưa có tiến trình khác xác nhận, chuyển phiếu sang `loi`, tạo ticket mới cho phiếu nhập kèm bản chụp mọi dòng đề nghị (kể cả dòng hợp lệ) và ghi audit `ghi_nhan_loi`. Nếu tiến trình khác đã xác nhận thành công thì trả kết quả đó, không tạo ticket.

Ví dụ lỗi xác nhận đã lưu ticket (HTTP 409):

```json
{
 "error": {
 "code": "dieu_chinh_khong_hop_le",
 "message": "Không đủ tồn để điều chỉnh; toàn bộ phiếu đã rollback.",
 "details": [{"mat_hang_id": 30, "so_luong_bien_dong": -10, "ton_hien_tai": 5}],
 "phieu_dieu_chinh_kho_id": 301,
 "trang_thai_phieu": "loi",
 "ticket_id": 401,
 "ticket_da_luu": true
 },
 "meta": {"request_id": "req-adjust"}
}
```

**[v3-đổi] Khi CSDL không dùng được (QĐ-0311).** PoC chưa xử lý trường hợp này. Contract không yêu cầu lưu sự cố bền vững hay tạo ticket bù sau phục hồi, dù comment của `"PhieuDieuChinhKho"` trong `init.sql` có mô tả cơ chế đó. Backend không tuyên bố đã lưu `loi` hay ticket khi chưa lưu được. Client tải lại phiếu sau khi hệ thống phục hồi, không tự gửi lại xác nhận.

Filter: `q`, `trang_thai`, `phieu_nhap_id`, `nhan_vien_id`, `tu_ngay`, `den_ngay`; sort `id`, `created_at`, `ma_phieu`.

### 12.2 Ticket lỗi điều chỉnh

**[v3-SQL]** TicketRead: `id`, `ma_ticket`, `phieu_nhap_id`, `nguoi_tao_id`, `mo_ta_loi`, `trang_thai` (`cho_xu_ly | dang_xu_ly | da_xu_ly`), `nguoi_xu_ly_id`, `ket_qua_xu_ly`, `created_at`, `closed_at`, `chi_tiet: [{id, chi_tiet_phieu_nhap_id, mat_hang_id, so_luong_hieu_luc_truoc, so_luong_de_nghi, so_luong_bien_dong, ton_kho_tai_thoi_diem}]`.

- Ticket chỉ được hệ thống tạo khi xác nhận điều chỉnh thất bại; không có endpoint tạo ticket thủ công. Mỗi lần thất bại tạo một ticket mới.
- Bối cảnh gốc (`ma_ticket`, `phieu_nhap_id`, `nguoi_tao_id`, `mo_ta_loi`, `created_at`) và các dòng chi tiết bất biến. Không xóa ticket.
- `nhan_xu_ly`: `cho_xu_ly → dang_xu_ly`, đặt `nguoi_xu_ly_id` là người gọi.
- **[v3-SQL]** `giai_quyet`: đóng từ `cho_xu_ly` hoặc `dang_xu_ly` sang `da_xu_ly`. Đặt `nguoi_xu_ly_id` là người đóng, `closed_at=now()`, lưu `ket_qua_xu_ly`. Nếu ticket đang `dang_xu_ly`, chỉ người đã nhận được đóng. Không yêu cầu phiếu điều chỉnh mới phải thành công trước.
- Ticket đã đóng không sửa và không mở lại. Tạo hoặc đóng ticket không đổi tồn. Phiếu điều chỉnh mới không tự đóng ticket cũ.

Filter: `trang_thai`, `phieu_nhap_id`, `nguoi_tao_id`, `nguoi_xu_ly_id`, `tu_ngay`, `den_ngay`; sort `id`, `created_at`, `ma_ticket`.

## 13. Báo cáo và lịch sử thao tác

| Method | Path | Quyền | Output |
|---|---|---|---|
| GET | `/bao_cao/nhap_xuat_ton` | Q | NhapXuatTonRead phân trang theo mặt hàng |
| GET | `/lich_su_thao_tac` | **[v3-đổi]** Q đầy đủ; A rút gọn | Danh sách AuditRead |
| ~~GET~~ | ~~`/lich_su_thao_tac/{id}`~~ | ~~Cùng phạm vi~~ | **[v3-bỏ]** Không có endpoint chi tiết |
| GET | `/luu_luong_truy_cap` | **[FE-MISS-001]** chỉ A | LuuLuongRead, không phân trang |

> v3: giữ đường dẫn `/lich_su_thao_tac` của v2 theo yêu cầu Việt hóa (QĐ-0311). D-PQ-01 và code hiện tại dùng `/audit`; code phải đổi (§16.3).

Báo cáo không đổi: bắt buộc `nam`, tùy chọn một trong `thang` (1..12) hoặc `quy` (1..4); gửi cả hai trả 422. Filter `mat_hang_id`, `loai_mat_hang`; sort `mat_hang_id`, `ton_cuoi_ky`. Kỳ theo Asia/Ho_Chi_Minh và `posted_at`.

Mỗi dòng: `mat_hang_id`, mã, tên, loại, đơn vị, `ton_dau_ky`, `nhap_trong_ky`, `xuat_trong_ky`, `dieu_chinh_trong_ky` (có dấu), `ton_cuoi_ky`. Meta thêm `tu_thoi_diem`, `den_thoi_diem_exclusive`, `timezone`.

```text
ton_dau_ky = tổng mọi giao dịch trước đầu kỳ
nhap_trong_ky = tổng nhap_vat_tu + nhap_san_pham_san_xuat trong kỳ
xuat_trong_ky = trị tuyệt đối tổng xuat_vat_tu + xuat_thanh_pham trong kỳ
dieu_chinh_trong_ky = tổng dieu_chinh_ton_kho có dấu trong kỳ
ton_cuoi_ky = ton_dau_ky + nhap_trong_ky - xuat_trong_ky + dieu_chinh_trong_ky
```

Chỉ tính ledger đã ghi sổ, mỗi giao dịch một lần.

**[v3-đổi] GET `/lich_su_thao_tac`:**

- Quyền: Q và A; N nhận 403.
- **[v3-đổi]** Response `{data: AuditRead[], meta: {request_id, page, page_size, total, total_pages}}`; lỗi theo §14.3 (QĐ-0311).
- **[v3-đổi]** Query theo §2.4: `page`, `page_size`, `q` (tìm trên các cột text, gồm `ly_do`; không tìm trong cột JSON), `sort` (whitelist `id`, `created_at`, mặc định `-created_at`), filter `loai_doi_tuong`, `doi_tuong_id`, `nhan_vien_id`, `thao_tac`, `tu_ngay`, `den_ngay`.
- AuditRead (Q): `id`, `nhan_vien_id`, `loai_doi_tuong`, `doi_tuong_id`, `thao_tac`, `ly_do`, `created_at`, `du_lieu_truoc`, `du_lieu_sau`.
- **[v3-mới] Rút gọn cho A (D-PQ-02):** A thấy mọi dòng, vẫn nhận `ly_do`; response bỏ hẳn hai key `du_lieu_truoc`, `du_lieu_sau`, không thay bằng `null`.
- **[v3-đổi]** Vì whitelist sort chỉ có `id`, `created_at`, mọi vai trò gửi `sort=du_lieu_truoc`/`du_lieu_sau` đều nhận 422. Quy tắc "server tự chuyển sang `created_at`" của D-PQ-02 không còn cần.
- Không có POST/PATCH/DELETE; trigger chặn UPDATE/DELETE bảng audit.

**[FE-MISS-001] GET `/luu_luong_truy_cap`** (D-LL-01, phục vụ khối "Lưu lượng truy website" của ADM-01):

- Quyền: chỉ A; Q và N nhận 403.
- Query duy nhất `khoang_thoi_gian` ∈ `hom_nay` (mặc định), `7_ngay`, `30_ngay`. Giá trị khác, tham số lặp hoặc tham số lạ trả 422.
- Response `{data: LuuLuongRead, meta: {request_id}}`. LuuLuongRead gồm `khoang_thoi_gian`, `buoc` (`gio` | `ngay`), `timezone` (`Asia/Ho_Chi_Minh`), `tu_thoi_diem`, `den_thoi_diem_exclusive`, `tong_request`, `diem[]`. Mỗi điểm gồm `bat_dau` (UTC, đầu giờ hoặc đầu ngày địa phương), `so_request` (`int | null`) và `trung_binh_7_ngay` (`number | null`).
- `hom_nay`: 24 điểm theo giờ của ngày hiện tại; giờ sau giờ hiện tại có `so_request = null`.
- `7_ngay` / `30_ngay`: 7 hoặc 30 điểm theo ngày lịch, điểm cuối là hôm nay (số tạm tính đến hiện tại).
- Chỉ `30_ngay` có `trung_binh_7_ngay`: trung bình của ngày đó và 6 ngày trước, làm tròn 1 chữ số; tính cả 6 ngày trước `tu_thoi_diem`. Các khoảng khác trả `null`. `tong_request` chỉ cộng các điểm hiển thị.
- Nguồn số liệu: bảng `"LuuLuongTruyCap"`, mỗi giờ một dòng. Middleware đếm mọi request `/api/v1` trừ `OPTIONS`, kể cả request lỗi.

## 14. Trạng thái, ghi sổ và lỗi

### 14.1 Luồng trạng thái

| Resource | Luồng | Mốc đổi tồn |
|---|---|---|
| nhan_vien | **[v3-đổi]** hoat_dong → bi_khoa bằng DELETE; bi_khoa → hoat_dong bằng `/mo_khoa` | Không |
| mat_hang | **[v3-mới]** is_active true → false bằng DELETE; false → true bằng PATCH | Không |
| bom | **[v3-mới]** POST mở version mới và đóng version cũ; `kich_hoat` mở version được chọn; DELETE đóng version | Không |
| phieu_nhap | nhap → hoan_thanh | hoan_tat cộng |
| yeu_cau_san_xuat | **[v3-SQL]** nhap → da_gui \| cho_bo_sung_vat_tu (gui); cho_bo_sung_vat_tu → da_gui \| dang_thuc_hien (tự kiểm tra khi hoàn tất phiếu nhập); da_gui → dang_thuc_hien → hoan_thanh; da_gui → hoan_thanh khi xuất đủ hàng sẵn có; hủy hợp lệ → da_huy | Không ghi kho trực tiếp |
| lenh_san_xuat | nhap → da_gui → dang_thuc_hien → hoan_thanh; hủy hợp lệ → da_huy | Không ghi kho trực tiếp |
| phieu_xuat | nhap → cho_duyet → da_duyet / tu_choi; tu_choi → nhap | duyet trừ |
| chung_tu_hoan_thanh_sx | nhap → cho_duyet → da_duyet / tu_choi; tu_choi → nhap | duyet cộng đầu ra |
| phieu_dieu_chinh_kho | **[v3-SQL]** nhap → da_xac_nhan (thành công) \| loi (thất bại) | xac_nhan cộng/trừ chênh lệch |
| ticket_loi_dieu_chinh | **[v3-SQL]** cho_xu_ly → dang_xu_ly → da_xu_ly; cho_xu_ly → da_xu_ly; không mở lại | Không |

Chứng từ đã ghi sổ bất biến. Mỗi mặt hàng có tối đa một BOM `is_active=true` (index `uq_bom_hien_hanh`).

### 14.2 Body action chung

- `LyDoInput = {ly_do: string}`, trim không rỗng; dùng cho từ chối, hủy, về nháp, khóa tài khoản và mở khóa.
- Các action ghi `{}` yêu cầu body JSON object rỗng.
- `ActionRead`: `data` là resource sau action, bổ sung `giao_dich_kho_ids: int[]`, `da_ghi_so_truoc_do: boolean`.

### 14.3 Error envelope

```json
{
 "error": {
 "code": "khong_du_ton_kho",
 "message": "Không đủ tồn kho để duyệt phiếu xuất.",
 "details": [{"mat_hang_id": 20, "so_luong_can": 8, "so_luong_hien_co": 5}]
 },
 "meta": {"request_id": "req-error"}
}
```

Frontend phân nhánh bằng `code`, không parse `message`. Không trả stack trace/SQL. Lỗi validation có `details: [{field, reason}]`, không echo input nhạy cảm. Lỗi 401 có `WWW-Authenticate: Bearer`. **[v3-mới]** 405 mặc định của FastAPI không dùng envelope này.

| HTTP | Code | Ý nghĩa |
|---|---|---|
| 401 | chua_xac_thuc, thong_tin_dang_nhap_khong_hop_le | JWT thiếu/hết hạn/sai phiên bản mật khẩu, hoặc đăng nhập sai |
| 403 | khong_co_quyen, tai_khoan_bi_vo_hieu_hoa | Không có quyền/phạm vi, hoặc tài khoản bị khóa |
| 404 | khong_tim_thay | ID không tồn tại |
| 405 | (mặc định FastAPI) | **[v3-mới]** Method không hỗ trợ |
| 409 | trang_thai_khong_hop_le | Action không hợp lệ ở trạng thái hiện tại |
| 409 | nguoi_duoc_giao_khong_hop_le | Người phụ trách/thực hiện thiếu, bị khóa hoặc sai vai trò |
| 409 | ma_bi_trung, dang_duoc_tham_chieu | Trùng unique, hoặc bị chặn xóa |
| 409 | **[v3-mới]** mat_hang_ngung_hoat_dong | Dùng mặt hàng đã ngừng cho tài liệu mới |
| 409 | bom_co_chu_trinh, thieu_bom | Ràng buộc BOM |
| 409 | ke_hoach_da_thay_doi | Kế hoạch đã đổi so với lúc tính |
| 409 | khong_du_ton_kho, vuot_nhu_cau, chua_du_vat_tu_da_cap | Ràng buộc xuất/bắt đầu |
| 409 | vuot_so_luong_hoan_thanh, phu_thuoc_khong_hop_le | Ràng buộc đầu ra/phụ thuộc |
| 409 | dieu_chinh_khong_hop_le | Xác nhận điều chỉnh thất bại; phiếu chuyển `loi`, có ticket |
| ~~409~~ | ~~bom_da_duoc_su_dung~~ | **[v3-bỏ]** BOM không có PATCH, xóa mềm được với mọi BOM |
| ~~409~~ | ~~thieu_vat_tu~~ | **[v3-bỏ] [v3-SQL]** Thiếu vật tư không còn chặn gửi yêu cầu |
| ~~409~~ | ~~can_xu_ly_thu_cong~~ | **[v3-bỏ] [v3-SQL]** Phiếu `loi` không retry; dùng `trang_thai_khong_hop_le` |
| ~~409~~ | ~~chua_du_dieu_kien_dong_ticket~~ | **[v3-bỏ] [v3-SQL]** Đóng ticket không phụ thuộc phiếu điều chỉnh |
| 412 | du_lieu_da_thay_doi | ETag cũ, wildcard hoặc weak |
| 422 | du_lieu_khong_hop_le | Sai kiểu/enum/trường bắt buộc/giá trị input; gồm sai loại mặt hàng trong BOM, BOM tự tham chiếu, biến động điều chỉnh bằng 0 |
| 428 | thieu_if_match | Thiếu điều kiện phiên bản |
| 500 | loi_noi_bo | Lỗi chưa phân loại |
| 503 | dich_vu_tam_thoi_khong_kha_dung | DB/dịch vụ không sẵn sàng; PoC chưa xử lý riêng |
| 503 | **[v3-mới]** danh_muc_chua_san_sang | Snapshot danh mục mặt hàng chưa sẵn sàng |

Lỗi xác thực, ETag, input sai hoặc action sai trạng thái trước khi thực sự ghi sổ không tạo ticket. Lỗi duyệt phiếu xuất/chứng từ hoàn thành giữ `cho_duyet` và không tạo ticket.

## 15. Luồng sử dụng và tiêu chí nghiệm thu

### 15.1 Đủ thành phẩm sẵn có

Tạo yêu cầu → tính kế hoạch (lượng sản xuất 0) → gán người phụ trách và gửi → **[v3-đổi]** Q lập/gửi phiếu xuat_thanh_pham → Q duyệt, chốt giá → trừ tồn, yêu cầu hoàn thành. Không tạo lệnh.

### 15.2 Sản xuất nhiều cấp

Tạo yêu cầu → tính kế hoạch → gửi, lưu cây lệnh → **[v3-SQL]** nếu thiếu vật tư, yêu cầu ở `cho_bo_sung_vat_tu`; Q nhập bổ sung, hoàn tất phiếu nhập làm hệ thống tự kiểm tra lại → giao/gửi lệnh → Q lập và duyệt phiếu xuất vật tư cho lệnh con → bắt đầu lệnh con → gửi/duyệt từng đợt hoàn thành để nhập bán thành phẩm → cấp và duyệt vật tư của lệnh cha → bắt đầu/hoàn thành và duyệt đầu ra cha → xuất thành phẩm cho yêu cầu. Nhu cầu của lệnh cha không chứa linh kiện trực tiếp của lệnh con.

### 15.3 **[v3-SQL]** Điều chỉnh phiếu nhập

Q tạo phiếu điều chỉnh cho một phiếu nhập `hoan_thanh`, nhập số lượng đúng cho từng dòng → xác nhận:

- hợp lệ: ghi sổ toàn phiếu, phiếu `da_xac_nhan`;
- không hợp lệ: rollback, phiếu `loi`, hệ thống tạo ticket mới → Q nhận xử lý, khắc phục nguyên nhân (ví dụ nhập thêm hoặc xuất sai), đóng ticket với kết quả → nếu vẫn cần điều chỉnh thì tạo phiếu điều chỉnh mới.

### 15.4 **[v3-mới]** Thay đổi công thức BOM

Q tạo BOM mới → version mới có hiệu lực ngay, version cũ đóng → lệnh đã tạo vẫn giữ `bom_id` cũ. Quay lại công thức cũ bằng `kich_hoat`. Ngừng công thức bằng DELETE; tính kế hoạch sau đó báo thiếu BOM.

### 15.5 Checklist tích hợp

- Tạo/sửa/gửi/từ chối/về nháp/bắt đầu không thay đổi tồn.
- N không thể duyệt, đọc công việc người khác hoặc giả người tạo bằng body.
- NhanVienRead/filter dùng `trang_thai`. Khóa tài khoản chặn cả JWT còn hạn; mở khóa không đổi vai trò.
- **[v3-mới]** `DELETE /nhan_vien/{id}` khóa chứ không xóa; không còn `/vo_hieu_hoa`.
- **[v3-mới]** Không tạo được A thứ hai, không cấp vai trò A, không hạ quyền hoặc khóa A hiện tại.
- **[v3-mới]** Đổi mật khẩu làm mọi token cũ trả 401; token mới hết hạn sau 60 phút.
- **[v3-mới]** Không còn route tiếng Anh ngoài `/auth/*`; `/audit`, `/inventory/*` trả 404.
- **[v3-mới]** Mọi trường tiền là integer VND.
- **[v3-đổi]** A nhận 403 ở mọi endpoint nghiệp vụ. N và A nhận 403 ở điều chỉnh kho và ticket.
- **[v3-mới]** A đọc `/lich_su_thao_tac` không có key `du_lieu_truoc`/`du_lieu_sau`; Q nhận đủ; response dạng `{data, meta}`.
- **[v3-mới]** Mặt hàng ngừng hoạt động vẫn đọc được, nhưng mọi đường tạo tài liệu mới trả 409 `mat_hang_ngung_hoat_dong`.
- **[v3-mới]** `so_luong_ton` khớp tổng ledger, kể cả ngay sau seed.
- **[v3-SQL]** Phiếu nhập bắt buộc `ncc_id` và `ngay_nhap`; lưu và trả `ghi_chu`.
- **[v3-SQL]** Phiếu xuất lưu, đọc, lọc và kiểm tra chủ phiếu bằng `nhan_vien_id`.
- **[v3-đổi]** Chỉ Q lập, sửa, gửi, duyệt phiếu xuất; N nhận 403 ở các thao tác ghi phiếu xuất.
- **[v3-đổi]** Phiếu xuất không nhận giá từ client; giá là null trước khi duyệt; khi duyệt, `don_gia_thuc` lấy từ `MatHang.don_gia` tại thời điểm đó và không đổi về sau; `tong_tien` khớp tổng dòng.
- **[v3-SQL]** Tạo yêu cầu nháp không cần người phụ trách; gửi yêu cầu khi chưa có người phụ trách bị từ chối.
- **[v3-SQL]** Gửi yêu cầu thiếu vật tư vẫn tạo lệnh và đưa yêu cầu sang `cho_bo_sung_vat_tu`. Hoàn tất phiếu nhập đủ bù thiếu thì yêu cầu tự về `da_gui`/`dang_thuc_hien` trong cùng transaction.
- **[v3-mới]** Yêu cầu đang `cho_bo_sung_vat_tu` không tạo được phiếu xuất thành phẩm.
- Hai người duyệt đồng thời không ghi trùng, không làm âm tồn, không vượt tổng lượng lệnh/yêu cầu.
- Gọi lại action ghi sổ đã thành công trả kết quả cũ, không sinh giao dịch/ticket mới.
- PATCH và action bằng ETag cũ bị từ chối (trừ BOM và nhà cung cấp).
- **[v3-đổi]** Nội dung BOM bất biến; đổi BOM hiện hành hoặc xóa mềm không làm thay đổi lệnh cũ. Mỗi mặt hàng tối đa một BOM active.
- Dùng tồn bán thành phẩm trước, không phân bổ trùng tồn giữa các nhánh.
- Hoàn thành nhiều đợt không vượt lượng lệnh; nhập đầu ra không trừ lại vật tư.
- Yêu cầu chỉ hoàn thành sau khi xuất đủ.
- **[v3-SQL]** Điều chỉnh chỉ trỏ giao dịch `nhap_vat_tu` của đúng phiếu nhập ở header; một dòng lỗi rollback mọi dòng; phiếu `loi` không xác nhận lại được; mỗi lần thất bại tạo một ticket mới.
- **[v3-SQL]** Ticket đóng được từ `cho_xu_ly` hoặc `dang_xu_ly`; ticket đã đóng không sửa/mở lại.
- Báo cáo tính điều chỉnh đúng một lần, khớp ledger; audit không chứa bí mật.

## 16. Quyết định và việc còn lại

### 16.1 Đã chốt

| Điểm | Kết quả v3 | Nguồn |
|---|---|---|
| Nguồn schema | `init.sql` là chuẩn; endpoint §7–§12 sửa theo SQL (bảng ở §17.3) | QĐ-0311 |
| Trạng thái tài khoản, `tai_khoan_id` | Theo `init.sql`; không expose `tai_khoan_id` | QĐ-AUTH |
| Access token | JWT 60 phút, không refresh; thu hồi qua `pwdv` khi đổi mật khẩu | QĐ-AUTH, QĐ-0311 |
| Chống dữ liệu cũ | ETag/If-Match, trừ BOM và nhà cung cấp | D-BOM-06, QĐ-NCC |
| Quyền điều chỉnh/ticket | Chỉ Q | QĐ-0311 |
| DB không sẵn sàng | PoC chưa xử lý | QĐ-0311 |
| Kiểu tiền | Integer VND cho mọi trường tiền | QĐ-0311 |
| Ngày nhập, ghi chú | Phiếu nhập có `ngay_nhap` (bắt buộc) và `ghi_chu` | QĐ-0311 |
| Giá phiếu xuất | Lấy từ `MatHang.don_gia` lúc Q duyệt; server tính `tong_tien` | QĐ-0311 |
| Người lập phiếu xuất | Chỉ Q; Q được duyệt phiếu do chính mình lập | QĐ-0311 |
| `MatHang.don_gia` | Bắt buộc khi tạo mặt hàng, không được null | QĐ-0311 |
| Thoát `cho_bo_sung_vat_tu` | Hệ thống tự kiểm tra mỗi khi phiếu nhập hoàn tất | QĐ-0311 |
| Xuất thành phẩm khi `cho_bo_sung_vat_tu` | Không cho phép | QĐ-0311 |
| Token kế hoạch | Giữ; TTL 10 phút | QĐ-0311 |
| Ngoại lệ Việt hóa | Giữ module `auth` và `/auth/*`; giữ `/bom`, `/health`, `/ping` | QĐ-0311 |
| Seed tồn | Theo ledger | QĐ-0311 |
| Lịch sử thao tác | Envelope `{data, meta}`; query `q`/`sort` | QĐ-0311 |
| Cache danh mục | Một instance, một worker | QĐ-0311 |
| Việt hóa | Không còn module/route tiếng Anh, kể cả `auth` và `audit` | QĐ-0311 |
| Frontend | Chưa cập nhật (§17.4) | QĐ-0311 |

### 16.2 Còn mở, chờ dev chốt

Không còn điểm nghiệp vụ mở trong contract.

### 16.3 Việc triển khai cần làm để code khớp v3

| Việc | Hiện trạng |
|---|---|
| Đổi các cột tiền về integer | `init.sql` khai báo `don_gia`, `don_gia_thuc`, `tong_gia`, `tong_tien` là `numeric(18,2)`; module mặt hàng trả `don_gia` dạng chuỗi decimal |
| Bắt buộc `MatHang.don_gia` | `init.sql` cho phép null; schema/ORM mặt hàng đang cho `don_gia` tùy chọn. `seed.sql` chưa có `don_gia` cho 17 mặt hàng, phải bổ sung giá trước khi đổi sang NOT NULL |
| Việt hóa đường dẫn và module | Còn `/audit`, `/inventory/stock` và các route tiếng Anh của module nhập/xuất/sản xuất/tồn kho (`auth` giữ nguyên) |
| Đổi envelope và query lịch sử thao tác | Đang trả `success`/`data`/`pagination`/`message`, dùng `search`/`sort_by`/`sort_order` |
| Triển khai §7–§12 theo v3 | Các module này vẫn dùng ORM/route legacy |
| Cập nhật frontend | Xem §17.4 |

## 17. Changelog v2 → v3

Lịch sử v1 → v2 xem tại §17 của `api-contract-v2.md`.

### 17.1 Endpoint

| Thay đổi | Endpoint | Nguồn |
|---|---|---|
| Thêm | `POST /auth/token` (Swagger) | QĐ-AUTH |
| Thêm | `GET /danh_muc_mat_hang/` | QĐ-MH |
| Thêm | `POST /phieu_dieu_chinh_kho/{id}/xac_nhan` | SQL |
| Bỏ | `POST /nhan_vien/{id}/vo_hieu_hoa` | QĐ-NV |
| Bỏ | `PATCH /nha_cung_cap/{id}`, `DELETE /nha_cung_cap/{id}` | QĐ-NCC |
| Bỏ | `PATCH /bom/{id}` | D-BOM-02 |
| Bỏ | `GET /ton_kho`, `GET /ton_kho/{mat_hang_id}` | D-PQ-04 |
| Bỏ | `GET /lich_su_thao_tac/{id}` | D-PQ-01 |
| Bỏ | `POST /phieu_dieu_chinh_kho/{id}/gui`, `/duyet`, `/tu_choi`, `/ve_nhap` | SQL |

Tổng: v2 có 89 cặp method + path; v3 bỏ 11, thêm 3, còn **81**. Prefix vẫn `/api/v1`.

### 17.2 Hành vi, quyền và schema theo quyết định của dev

| Nhóm | v2 | v3 | Nguồn |
|---|---|---|---|
| Quyền A | Quản trị tài khoản + tra cứu danh mục | Chỉ nhân viên/vai trò, xác thực của mình, lịch sử rút gọn | D-PQ-01, D-PQ-03 |
| Số lượng A | Chỉ chặn hạ quyền/khóa A cuối cùng | Đúng một A; không tạo/cấp thêm | QĐ-NV |
| Quyền điều chỉnh/ticket | Nhóm X | Chỉ Q | QĐ-0311 |
| Token | Chưa chốt | 60 phút; `pwdv`; chỉ đăng nhập bằng tên đăng nhập | QĐ-AUTH, QĐ-0311 |
| `DELETE /nhan_vien/{id}` | Xóa thật | Khóa tài khoản, có LyDoInput + If-Match | QĐ-NV |
| Đọc mặt hàng | A/Q/N | Q/N; đọc từ cache; trả cả hai trạng thái | D-PQ-03, QĐ-MH |
| `DELETE /mat_hang/{id}` | Chỉ khi chưa tham chiếu, tồn 0 | Soft delete, luôn được phép | QĐ-MH |
| `MatHangRead` | Không có số tồn | Thêm `so_luong_ton`, `ton_kho_updated_at` | QĐ-MH, D-PQ-04 |
| Mặt hàng ngừng hoạt động | Quy tắc UI | Backend chặn: 409 `mat_hang_ngung_hoat_dong` | QĐ-MH |
| Nhà cung cấp | A/Q đọc; sửa/xóa; ETag | Chỉ Q đọc/tạo; không sửa/xóa; không ETag | QĐ-NCC, D-PQ-03 |
| BOM | Tạo chưa kích hoạt; PATCH; If-Match; xóa khi chưa dùng; tự tham chiếu 409 | Tạo là kích hoạt; không PATCH; không ETag; xóa mềm; tự tham chiếu 422; quy tắc loại mặt hàng | D-BOM-02→13 |
| Tồn kho | `/ton_kho` | `MatHang.so_luong_ton`; seed theo ledger | QĐ-MH, D-PQ-04, QĐ-0311 |
| Kiểu tiền | Integer VND | Integer VND cho mọi trường (bỏ hướng decimal của QĐ-MH) | QĐ-0311 |
| Giá phiếu xuất | Client khai `don_gia_thuc` | Server lấy `MatHang.don_gia` lúc duyệt; null trước khi duyệt | QĐ-0311 |
| Người lập phiếu xuất | N lập, sửa, gửi, về nháp | Chỉ Q; N chỉ đọc phiếu của công việc được giao; Q được tự duyệt phiếu mình lập | QĐ-0311 |
| `MatHang.don_gia` | Tùy chọn, nullable | Bắt buộc, không null | QĐ-0311 |
| Thoát `cho_bo_sung_vat_tu` | (Không có trạng thái này) | Tự kiểm tra khi hoàn tất phiếu nhập; không có endpoint thủ công | QĐ-0311 |
| Token kế hoạch | Đề xuất TTL 10 phút | Giữ, TTL 10 phút | QĐ-0311 |
| Lịch sử thao tác | `/lich_su_thao_tac` + chi tiết; A chỉ đọc nhân viên/vai trò | Chỉ danh sách; `{data, meta}`; `q`/`sort`; A đọc mọi dòng nhưng ẩn trước/sau | D-PQ-01, D-PQ-02, QĐ-0311 |
| DB không sẵn sàng | Lưu sự cố bền vững, ticket bù | PoC chưa xử lý | QĐ-0311 |
| Đường dẫn | Không quy định | Chỉ tiếng Việt, trừ module `auth` giữ nguyên | QĐ-0311 |

### 17.3 Các chỗ đã sửa để khớp `init.sql`

| Mục | Thay đổi | Cột/ràng buộc trong `init.sql` |
|---|---|---|
| §2.5 | Mã chứng từ có tháng `<TIỀN_TỐ>-YYYYMM-NNNNNN`; mã danh mục `NV-`/`MH-`/`NCC-NNNNNN` | CHECK `ck_*_ma` |
| §2.5, §3, §10 | Phiếu xuất dùng `nhan_vien_id`, bỏ `ma_nhan_vien` (Create, Read, filter, kiểm tra chủ phiếu) | `"PhieuXuat".nhan_vien_id int NOT NULL` |
| §2.5 | Chứng từ đã chốt và dòng của chúng bất biến | Trigger `bao_ve_chung_tu`, `bao_ve_dong_chung_tu` |
| §7 | `ncc_id` bắt buộc; thêm `ngay_nhap` (bắt buộc), `ghi_chu`; lọc ngày theo `ngay_nhap` | `"PhieuNhap".ncc_id NOT NULL`, `ngay_nhap date NOT NULL`, `ghi_chu text` |
| §7 | `dieu_chinh_ids`, `so_luong_hieu_luc` chỉ cho giao dịch `nhap_vat_tu` | Trigger `kiem_tra_nguon_dieu_chinh` |
| §8 | `nhan_vien_duoc_giao_id` tùy chọn khi nhap, bắt buộc khi gửi | `ck_yeu_cau_nguoi_duoc_giao` |
| §7, §8, §14.1 | Thêm trạng thái `cho_bo_sung_vat_tu`; gửi không bị chặn khi thiếu vật tư; hoàn tất phiếu nhập tự kiểm tra lại các yêu cầu đang chờ bổ sung; preview có `thieu_vat_tu` | `ck_yeu_cau_san_xuat_trang_thai`, `COMMENT ON TABLE "YeuCauSanXuat"`, `"LenhSanXuat"` |
| §9 | `nhan_vien_id` của lệnh nullable khi nhap; thiếu vật tư không chặn gửi lệnh; lượng đã cấp không xét điều chỉnh | `ck_lenh_nguoi_thuc_hien`, `COMMENT ON TABLE "LenhSanXuat"`, `"ChiTietLenhSanXuat"` |
| §10 | Phiếu `da_duyet` bất biến, không điều chỉnh phiếu xuất | `COMMENT ON TABLE "PhieuXuat"` |
| §11 | Thêm `created_at` vào Read; không điều chỉnh chứng từ hoàn thành | `"ChungTuHoanThanhSx".created_at`, `COMMENT ON TABLE "ChiTietPhieuDieuChinhKho"` |
| §12 | Điều chỉnh gắn `phieu_nhap_id`; trạng thái `nhap/da_xac_nhan/loi`; `confirmed_at`; action `xac_nhan` thay gửi/duyệt/từ chối/về nháp; dòng nhận `so_luong_dung`, server tính `so_luong_hieu_luc_truoc`, `so_luong_bien_dong`; bỏ nguồn null và `ticket_id` | `"PhieuDieuChinhKho"`, `"ChiTietPhieuDieuChinhKho"`, `ck_dieu_chinh_xac_nhan`, `trg_dieu_chinh_nguon` |
| §12 | Ticket gắn `phieu_nhap_id`; có `ma_ticket`, `nguoi_tao_id`, `closed_at` và dòng chi tiết; mỗi lần lỗi một ticket mới; đóng từ `cho_xu_ly` hoặc `dang_xu_ly`; không mở lại | `"TicketLoiDieuChinh"`, `"ChiTietTicketLoiDieuChinh"`, `ck_ticket_dong`, `trg_ticket_boi_canh` |
| §14.3 | Bỏ `thieu_vat_tu`, `can_xu_ly_thu_cong`, `chua_du_dieu_kien_dong_ticket` | Theo các thay đổi §8, §12 |

### 17.4 Việc cần làm ở frontend

Frontend chưa cập nhật theo v3 (QĐ-0311):

- Giữ `/auth/*`; đổi `/audit` sang `/lich_su_thao_tac`; bỏ các route tiếng Anh khác.
- Ẩn menu mặt hàng, danh mục, nhà cung cấp, BOM với A; ẩn điều chỉnh kho và ticket với N và A.
- Màn hình lịch sử: đọc `{data, meta}`, dùng `q`/`sort`; với A phải chạy khi thiếu `du_lieu_truoc`/`du_lieu_sau`.
- Nút khóa nhân viên gọi `DELETE /nhan_vien/{id}` với `{ly_do}` và `If-Match`.
- Mọi trường tiền là integer VND. Phiếu xuất bỏ ô nhập đơn giá; giá và tổng là null trước khi duyệt, hiển thị giá do server chốt sau khi duyệt.
- Màn hình lập phiếu xuất chỉ mở cho Q; N chỉ xem.
- Form mặt hàng: `don_gia` bắt buộc.
- Lấy tồn từ `MatHangRead.so_luong_ton`.
- Nhà cung cấp: bỏ sửa/xóa; gọi `/nha_cung_cap`.
- BOM: bỏ sửa; "sửa" là tạo version mới; bỏ If-Match.
- Phiếu nhập: thêm ô `ngay_nhap` (bắt buộc), `ghi_chu`; `ncc_id` bắt buộc.
- Phiếu xuất: hiển thị `nhan_vien_id` thay cho `ma_nhan_vien`.
- Yêu cầu sản xuất: cho tạo nháp chưa gán người; hiển thị trạng thái `cho_bo_sung_vat_tu` (tự thoát khi phiếu nhập hoàn tất đủ bù thiếu); không cho lập phiếu xuất thành phẩm ở trạng thái này.
- Điều chỉnh: chọn phiếu nhập đã hoàn tất, nhập số lượng đúng cho từng dòng, một nút "Xác nhận"; hiển thị ticket theo phiếu nhập.
- Dropdown mặt hàng chỉ hiện `is_active=true`; dropdown BOM lọc theo loại.

### 17.5 Phân biệt contract và triển khai

`init.sql` là schema đã chốt, nhưng không phải bằng chứng backend đã thực hiện validation/transaction. Demo Docker chỉ bootstrap database mới/trống bằng `init.sql` và `seed.sql`, chưa có migration (AGENTS §6). Việc đổi kiểu cột tiền sang integer là thay đổi `init.sql` cho database mới/trống, không phải quyền sửa database đang chạy. Các module §7–§12 vẫn dùng code legacy; cho tới khi được chuyển đổi, hành vi thực tế có thể khác contract.
