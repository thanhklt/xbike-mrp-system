# Sequence — bom

Module có 6 endpoint theo contract v2 §6 và các quyết định [D-BOM-01 đến D-BOM-12](../DECISION.md#module-bom-chốt-ngày-02112026). Các ngoại lệ so với contract nằm tại [D-BOM-10](../DECISION.md#d-bom-10-điểm-lệch-so-với-contract-v2-6): POST tạo version active ngay; không có PATCH; không ETag/If-Match; DELETE là xóa mềm kể cả BOM đã dùng; tự tham chiếu trả 422, chu trình gián tiếp trả 409.

Đọc cho `quan_ly`/`nhan_vien`; ghi chỉ `quan_ly`. `quan_tri_vien` nhận 403 ở cả 6 endpoint. Auth đọc danh tính, trạng thái và credential hiện hành qua public `NhanVienService`; nhân viên service dùng repository của chính module đó. Không có projection khác nhau giữa hai vai trò được đọc BOM.

Response thành công có `{data, meta: {request_id}}`; list bổ sung `page`, `page_size`, `total`, `total_pages`. Lỗi ứng dụng/validation có `{error: {code, message, details}, meta: {request_id}}`. Lỗi constraint trong transaction được chuyển thành 409 `trang_thai_khong_hop_le`; lỗi bất ngờ là 500 `loi_noi_bo`. Gọi PATCH nhận 405 mặc định FastAPI, không thuộc error envelope này.

Mọi ghi dùng chung session/transaction với audit, giữ `pg_advisory_xact_lock(20261020, 2)` tới COMMIT/ROLLBACK. POST và kích hoạt BOM inactive kiểm tra đầu ra và thành phần bằng `MatHangAvailabilityService` (`FOR SHARE`, thứ tự ID), loại mặt hàng, BOM con và chu trình trước khi đóng BOM hiện hành. DELETE và kích hoạt BOM đã active không chạy lại guard. Không cập nhật tồn kho hoặc sửa chi tiết công thức.

## GET /api/v1/bom

Query: `page` ≥ 1 (mặc định 1), `page_size` 1–100 (mặc định 20); filter `mat_hang_id`, `version`, `is_active`; sort `id`, `version`, `start_time` và tiền tố `-`. Tham số lạ bị từ chối. ID làm tiêu chí phụ; trang ngoài phạm vi trả data rỗng. Không có nhánh 404 cho danh sách.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly hoặc nhan_vien
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: Validate BomListQuery
    alt Query sai, page/page_size/sort không hợp lệ hoặc field lạ
        R-->>C: 422 du_lieu_khong_hop_le + details
    else Hợp lệ
        R->>S: list_bom(params, request_id)
        S->>B: list_bom(params)
        B->>P: COUNT có filter
        opt Offset nhỏ hơn total
            B->>P: SELECT Bom + EXISTS LenhSanXuat, ORDER BY, LIMIT/OFFSET
            B->>P: SELECT ChiTietBom theo các BOM (selectin)
        end
        B-->>S: RecordPage BomRead với chi_tiet và da_duoc_su_dung
        S-->>R: BomListResponse với total_pages
        R-->>C: 200 data + meta phân trang
    end
```

## GET /api/v1/bom/{id}

`id` phải dương; lớn hơn INT32 hoặc không tồn tại trả 404. Không nhận query. `da_duoc_su_dung` được tính bằng EXISTS trên bảng SQL `"LenhSanXuat"`, không dùng ORM production cũ. BOM inactive và mặt hàng bị khóa vẫn đọc được lịch sử.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly hoặc nhan_vien
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: Validate Path id và reject_query
    alt id không dương/không phải số hoặc có query
        R-->>C: 422 du_lieu_khong_hop_le
    else Hợp lệ
        R->>S: get_bom(id, request_id)
        alt id lớn hơn INT32
            S-->>C: 404 khong_tim_thay
        else Trong miền INT32
            S->>B: get_by_id(id)
            B->>P: SELECT Bom + EXISTS LenhSanXuat, SELECT ChiTietBom
            alt Không tồn tại
                S-->>C: 404 khong_tim_thay
            else Tìm thấy
                S-->>R: BomDetailResponse
                R-->>C: 200 data BomRead + meta.request_id
            end
        end
    end
```

## GET /api/v1/bom/{id}/cau_truc

Gốc dùng đúng chi tiết của version được chọn, kể cả inactive. BOM con tra hiện hành tại thời điểm đọc; node thiếu BOM con trả `bom_id: null`, `children: []`. Số lượng node là định mức trên một đơn vị cha, không nhân dồn. Đây là cấu trúc công thức, không phải kế hoạch đã chốt của lệnh sản xuất.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly hoặc nhan_vien
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: Validate id dương và reject_query (lỗi 422)
    R->>S: get_cau_truc(id, request_id)
    alt id lớn hơn INT32
        S-->>C: 404 khong_tim_thay
    else Trong miền INT32
        S->>B: get_by_id(id)
        B->>P: SELECT Bom + EXISTS LenhSanXuat, SELECT ChiTietBom
        alt Không có BOM gốc
            S-->>C: 404 khong_tim_thay
        else Có BOM gốc
            S->>B: load_active_graph()
            B->>P: SELECT Bom LEFT JOIN ChiTietBom WHERE is_active
            S->>S: Dựng cây từ chi tiết gốc, giữ path riêng cho mỗi nhánh
            alt Gặp lại mặt hàng trên path
                S-->>C: 409 bom_co_chu_trinh
            else Không có chu trình
                S-->>R: BomTreeResponse
                R-->>C: 200 data cây + meta.request_id
            end
        end
    end
```

## POST /api/v1/bom

`BomCreate` chỉ nhận `mat_hang_id` và `chi_tiet` không rỗng; từng dòng có ID dương, số lượng integer > 0. Field thừa, dòng trùng và tự tham chiếu trả 422 trước khi ghi DB; lỗi trùng/tự tham chiếu có `details[].field=chi_tiet` và chỉ số dòng (từ 0). Server cấp version tăng dần theo đầu ra. Đóng cũ trước khi insert mới để không vi phạm partial unique index. Thành công trả 201 và `Location`.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant G as MatHangAvailabilityService
    participant I as MatHang repository
    participant U as SqlAlchemyAuditRepository
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: reject_query và validate BomCreate
    alt Payload/query sai, trùng dòng hoặc tự tham chiếu
        R-->>C: 422 du_lieu_khong_hop_le, không ghi audit
    else Hợp lệ
        R->>S: create_bom(payload, actor, request_id)
        S->>T: Enter transaction dùng chung session
        S->>B: lock_bom_graph()
        B->>P: pg_advisory_xact_lock(20261020, 2)
    S->>G: require_active_items([đầu ra, thành phần...])
    G->>I: lock_items(tập ID)
    I->>P: SELECT MatHang ORDER BY id FOR SHARE
    alt Thiếu mặt hàng hoặc mặt hàng inactive
        G-->>S: 404 khong_tim_thay hoặc 409 mat_hang_ngung_hoat_dong
        S->>T: Thoát với lỗi
        T->>P: ROLLBACK
        S-->>C: Error envelope
    else Các mặt hàng đang hoạt động
        S->>B: get_item_types(ids)
        B->>P: SELECT MatHang.id, loai_mat_hang
        S->>S: Đầu ra BTP/TP#59; thành phần NVL/linh_kien/BTP
        alt Sai loại
            S->>T: Thoát với InvalidInputException
            T->>P: ROLLBACK
            S-->>C: 422 du_lieu_khong_hop_le, message nêu mat_hang_id
        else Đúng loại
            S->>B: load_active_graph()
            B->>P: SELECT Bom LEFT JOIN ChiTietBom WHERE is_active
            S->>S: BTP con phải có BOM hiện hành, thay cạnh đầu ra rồi duyệt đồ thị
            alt Thiếu BOM con hoặc có chu trình
                S->>T: Thoát với lỗi nghiệp vụ
                T->>P: ROLLBACK
                S-->>C: 409 thieu_bom hoặc bom_co_chu_trinh
            else Đồ thị hợp lệ
                S->>B: get_active_for_item(output)
                B->>P: SELECT BOM hiện hành và chi tiết
                opt Có BOM hiện hành cũ
                    S->>B: deactivate(old.id)
                    B->>P: UPDATE is_active=false, end_time=now()#59; đọc lại
                    S->>U: append vo_hieu_hoa với trước/sau
                end
                S->>B: next_version(output)
                B->>P: SELECT coalesce(max(version), 0) + 1
                S->>B: add(output, version, chi_tiet)
                B->>P: INSERT Bom active, start_time=now()#59; INSERT ChiTietBom#59; FLUSH#59; đọc lại
                S->>U: append tao với snapshot BomRead
                Note over U,P: Audit được add vào cùng session, flush khi commit
                S->>T: Exit transaction
                alt Constraint hoặc persistence/audit lỗi
                    T->>P: ROLLBACK mọi thay đổi
                    S-->>C: 409 trang_thai_khong_hop_le hoặc 500 loi_noi_bo
                else Thành công
                    T->>P: COMMIT BOM và LichSuThaoTac, giải phóng khóa
                    S-->>R: BomDetailResponse
                    R-->>C: 201 data + meta, Location=/api/v1/bom/id
                end
            end
        end
    end
    end
```

## DELETE /api/v1/bom/{id}

Xóa mềm cho cả BOM đã được lệnh sử dụng; không xóa Bom/ChiTietBom hoặc quan hệ của lệnh. BOM đã inactive trả 204 và không thêm audit. Không yêu cầu If-Match; không kiểm tra trạng thái mặt hàng hoặc BOM cha.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant G as MatHangAvailabilityService
    participant I as MatHang repository
    participant U as SqlAlchemyAuditRepository
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: Validate id dương và reject_query (lỗi 422)
    R->>S: delete_bom(id, actor)
    S->>T: Enter transaction
    S->>B: lock_bom_graph()
    B->>P: pg_advisory_xact_lock(20261020, 2)
    S->>B: get_by_id(id), bỏ SELECT nếu id vượt INT32
    B->>P: SELECT Bom + EXISTS LenhSanXuat, SELECT ChiTietBom
    alt Không có BOM hoặc id vượt INT32
        S->>T: Thoát với NotFoundException
        T->>P: ROLLBACK
        S-->>C: 404 khong_tim_thay
    else BOM đã inactive
        S->>T: Exit, không update hoặc audit
        T->>P: COMMIT, giải phóng khóa
        R-->>C: 204 không body
    else BOM đang active
        S->>B: deactivate(id)
        B->>P: UPDATE is_active=false, end_time=now()#59; đọc lại
        Note over B,P: Trigger cho phép đóng hiệu lực cả BOM đã dùng
        S->>U: append vo_hieu_hoa với trước/sau
        S->>T: Exit transaction, flush audit
        alt Constraint hoặc persistence/audit lỗi
            T->>P: ROLLBACK
            S-->>C: 409 trang_thai_khong_hop_le hoặc 500 loi_noi_bo
        else Thành công
            T->>P: COMMIT BOM và audit
            R-->>C: 204 không body
        end
    end
```

## POST /api/v1/bom/{id}/kich_hoat

Body `{}` tùy chọn; field thừa bị từ chối. Kích hoạt một BOM đã active trả 200 và không ghi audit. Khi mở lại, `start_time` giữ nguyên (nếu null mới gán now); `end_time=NULL`. Việc này tương thích trigger bảo vệ BOM đã dùng. Audit lưu toàn bộ lịch sử đóng/mở. BOM cũ có cạnh tự trỏ trả 409 `bom_co_chu_trinh`, kể cả đầu ra chưa có version hiện hành khác.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Bom router
    participant A as AuthService và require_roles
    participant N as NhanVienService
    participant NR as NhanVien repository
    participant S as BomService
    participant B as SqlAlchemyBomRepository
    participant P as PostgreSQL
    participant T as SqlAlchemyTransaction
    participant G as MatHangAvailabilityService
    participant I as MatHang repository
    participant U as SqlAlchemyAuditRepository
    C->>R: Request + Bearer JWT
    R->>A: Kiểm tra JWT và quyền quan_ly
    A->>N: get_auth_identity(sub, credential_version)
    N->>NR: get_credentials_by_id(sub)
    NR->>P: SELECT NhanVien JOIN VaiTro
    P-->>NR: Tài khoản và vai trò
    NR-->>N: Credentials
    N-->>A: AuthIdentity hiện hành
    alt Thiếu token, token lỗi/hết hạn hoặc credential cũ
        A-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa
        A-->>C: 403 tai_khoan_bi_vo_hieu_hoa
    else Vai trò không được phép
        A-->>C: 403 khong_co_quyen
    end
    R->>R: Validate id, reject_query, KichHoatBomInput (lỗi 422)
    R->>S: activate_bom(id, actor, request_id)
    S->>T: Enter transaction
    S->>B: lock_bom_graph()
    B->>P: pg_advisory_xact_lock(20261020, 2)
    S->>B: get_by_id(id), bỏ SELECT nếu id vượt INT32
    B->>P: SELECT Bom + EXISTS LenhSanXuat, SELECT ChiTietBom
    alt Không tồn tại hoặc id vượt INT32
        S->>T: Thoát với NotFoundException
        T->>P: ROLLBACK
        S-->>C: 404 khong_tim_thay
    else BOM đã active
        S->>T: Exit, không guard/update/audit
        T->>P: COMMIT, giải phóng khóa
        R-->>C: 200 BomDetailResponse hiện tại
    else BOM inactive
    S->>G: require_active_items([đầu ra, thành phần...])
    G->>I: lock_items(tập ID)
    I->>P: SELECT MatHang ORDER BY id FOR SHARE
    alt Thiếu mặt hàng hoặc mặt hàng inactive
        G-->>S: 404 khong_tim_thay hoặc 409 mat_hang_ngung_hoat_dong
        S->>T: Thoát với lỗi
        T->>P: ROLLBACK
        S-->>C: Error envelope
    else Các mặt hàng đang hoạt động
        S->>B: get_item_types(ids)
        B->>P: SELECT MatHang.id, loai_mat_hang
        S->>S: Đầu ra BTP/TP#59; thành phần NVL/linh_kien/BTP
        alt Sai loại
            S->>T: Thoát với InvalidInputException
            T->>P: ROLLBACK
            S-->>C: 422 du_lieu_khong_hop_le, message nêu mat_hang_id
        else Đúng loại
            S->>B: load_active_graph()
            B->>P: SELECT Bom LEFT JOIN ChiTietBom WHERE is_active
            S->>S: BTP con phải có BOM hiện hành, thay cạnh đầu ra rồi duyệt đồ thị
            alt Thiếu BOM con hoặc có chu trình
                S->>T: Thoát với lỗi nghiệp vụ
                T->>P: ROLLBACK
                S-->>C: 409 thieu_bom hoặc bom_co_chu_trinh
            else Đồ thị hợp lệ
                S->>B: get_active_for_item(output)
                B->>P: SELECT BOM hiện hành và chi tiết
                opt Có BOM hiện hành khác
                    S->>B: deactivate(current.id)
                    B->>P: UPDATE is_active=false, end_time=now()#59; đọc lại
                    S->>U: append vo_hieu_hoa với trước/sau
                end
                S->>B: activate(id)
                B->>P: UPDATE is_active=true, end_time=NULL, start_time=coalesce(start_time, now())#59; đọc lại
                S->>U: append sua với trước/sau BOM được kích hoạt
                S->>T: Exit transaction, flush audit
                alt Constraint hoặc persistence/audit lỗi
                    T->>P: ROLLBACK
                    S-->>C: 409 trang_thai_khong_hop_le hoặc 500 loi_noi_bo
                else Thành công
                    T->>P: COMMIT mọi thay đổi và audit, giải phóng khóa
                    S-->>R: BomDetailResponse
                    R-->>C: 200 data + meta.request_id
                end
            end
        end
    end
    end
```
