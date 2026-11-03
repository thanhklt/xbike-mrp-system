# Điều chỉnh kho

Nguồn: contract v2 dev cung cấp và xbike_mrp_data_model_v3.1_mermaid.md. Quyết định 03/11/2026: giữ 9 endpoint, chỉ quan_ly, dùng so_luong_dung, ticket độc lập, phiếu loi bất biến. Đây là luồng đã triển khai trong backend/app/modules/dieu_chinh_kho.

## Payload và response

POST tạo nhận `{"phieu_nhap_id":1,"ly_do":"Đối chiếu","chi_tiet":[{"giao_dich_goc_id":12,"so_luong_dung":986}]}`. PATCH chỉ nhận ly_do và chi_tiet; bỏ qua giữ nguyên, null bị từ chối; array thay toàn bộ. Gửi/duyệt nhận `{}`; từ chối/về nháp nhận `{"ly_do":"Lý do"}`. ID dòng, mặt hàng, lượng trước, biến động, mã, người tạo và thời gian do server xác định. ID dương, số lượng đúng nguyên không âm; không nhận bool/số lẻ, dòng trùng nguồn, array rỗng, lý do trắng hoặc field dư (422).

Chỉ sửa giao dịch nhap_vat_tu của đúng phiếu nhập hoan_thanh, mặt hàng NVL/linh kiện. Lượng hiệu lực = lượng nhập gốc + điều chỉnh đã ghi ledger. Delta = lượng đúng - lượng hiệu lực. Delta bằng 0/ngoài miền integer trả 409 trước ghi kho và ticket. Server tính lại dưới khóa khi duyệt.

Danh sách: q tìm mã phiếu; trang_thai, nhan_vien_id, tu_ngay, den_ngay; page mặc định 1, page_size mặc định 20/tối đa 100; sort id/created_at/ma_phieu với tiền tố -; ID làm tiêu chí phụ. Query dư, sort sai/ngày đảo trả 422. Ngày Asia/Ho_Chi_Minh đổi thành UTC [đầu ngày, đầu ngày sau). Response data/meta gồm request_id, page, page_size, total, total_pages.

GET chi tiết trả strong ETag bao gồm header và dòng; confirmed_at null được giữ. PATCH/DELETE/action so ETag dưới khóa, thiếu 428, cũ/weak/wildcard 412. Chỉ duyệt đã thành công được trả kết quả cũ trước kiểm tra ETag: giao_dich_kho_ids, da_ghi_so_truoc_do=true. Lần ghi sổ mới trả false. POST tạo trả 201 với Location; DELETE 204; còn lại 200. Một resource trả data/meta.request_id; action fields nằm cùng cấp data/meta.

## Transaction và ticket

Mutation dùng cùng session với AuditService; lỗi luôn rollback. Advisory transaction lock 73421 tuần tự hóa module, sau đó khóa phiếu nhập, phiếu điều chỉnh và MatHang theo ID tăng dần. Kiểm tra lại quyền quản lý sau chờ khóa. GET chi tiết giữ khóa để đọc header/dòng cùng phiên bản. Repository dùng SQL tham số hóa trên bảng PascalCase, không tạo ORM trùng legacy inventory. Nghiệp vụ module cũ không chuyển đổi.

DCK/TKDC dùng sequence identity không rollback, không tái dùng mã sau xóa nháp; hậu tố giới hạn 6 chữ số, dùng sequence toàn cục không reset theo tháng.

Ticket chỉ tham chiếu phiếu nhập, không FK tới phiếu điều chỉnh. DieuChinhRead không có ticket_id; response lỗi của lần thất bại có ticket_id khi đã commit. Không tự đóng/mở ticket; API quản lý ticket ngoài phạm vi 9 endpoint. /tu_choi chỉ cho_duyet, /ve_nhap chỉ tu_choi. Phiếu loi và da_duyet bất biến.

Nguồn/delta không hợp lệ ở tạo/sửa/gửi hoặc trước khi lập snapshot duyệt trả 404/409 không tạo ticket. Khi có snapshot hợp lệ mà kiểm tra tồn/ghi kho/audit thất bại: rollback kho, mở transaction riêng và kiểm tra lại phiên bản. Phiếu đã duyệt trả kết quả cũ; phiếu đã đổi trả 409 can_xu_ly_thu_cong. Nếu vẫn cho_duyet đúng phiên bản thì ghi ticket, mọi dòng snapshot, trạng thái loi và audit; commit rồi trả 409 dieu_chinh_khong_hop_le, ticket_da_luu=true. Lỗi SQL chưa có snapshot trả 503.

Nếu transaction lưu ticket lỗi SQL, snapshot được ghi file bằng fsync và atomic rename. DIEU_CHINH_INCIDENT_DIR chọn thư mục bền vững, mặc định .runtime/dieu_chinh_kho theo working directory; container cần mount đường dẫn này vào volume bền vững. Khi database phục hồi, chạy từ backend:

```sh
python -m app.modules.dieu_chinh_kho.incidents
```

Lệnh chỉ lưu lại ticket, không chạy lại duyệt hoặc đổi tồn. File được xóa sau lưu ticket thành công hoặc phát hiện phiếu đã duyệt; phiên bản khác/phiếu loi cần đối soát thủ công. Không suy đoán liên kết ticket từ phiếu nhập. Nếu cả database và ổ lưu sự cố đều hỏng, không bảo đảm lưu được snapshot; lỗi ổ đĩa được giữ để giám sát phát hiện.

## Sequence

API gồm router và dependency auth/validation. S là DieuChinhService, R là repository, U là AuditService. Lỗi SQL trả 503 bằng route handler; lỗi khác ngoài dự kiến trả 500 handler chung. Các nhánh ghi chỉ trả thành công sau COMMIT.

### API-73 — GET /api/v1/phieu_dieu_chinh_kho

Danh sách.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: GET /
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: repo.list(query)
    S->>R: Lọc, sort whitelist, phân trang
    R->>D: SELECT count, IDs, header và chi tiết
    D-->>R: Kết quả
    R-->>S: Records và total
    S-->>A: data/meta
    A-->>C: 200
```

### API-74 — GET /api/v1/phieu_dieu_chinh_kho/{id}

Chi tiết.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: GET /{id}
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: get(id)
    S->>R: lock(id), get(id)
    R->>D: Advisory lock, khóa nguồn/phiếu, SELECT dòng
    D-->>R: Kết quả
    R-->>S: Phiếu hoặc không tồn tại
    alt Không tồn tại
        A-->>C: 404
    else Tồn tại
        S-->>A: Resource và ETag
        A-->>C: 200 data/meta, ETag
    end
```

### API-75 — POST /api/v1/phieu_dieu_chinh_kho

Tạo nháp.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: POST /
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: create(payload, actor)
    S->>R: serialize, actor, lock_receipt, source
    R->>D: Khóa và kiểm tra nguồn, quyền hiện tại
    D-->>R: Dữ liệu hiện hành
    R-->>S: Kết quả
    break Nguồn thiếu/sai, delta không hợp lệ
        S->>D: ROLLBACK
        A-->>C: 404 / 409
    end
    S->>R: next_code, create_header, replace_lines
    R->>D: INSERT nhap và chi tiết
    S->>U: append tao
    U->>D: INSERT audit cùng transaction
    S->>D: COMMIT
    S-->>A: Resource và ETag
    A-->>C: 201, Location, ETag
```

### API-76 — PATCH /api/v1/phieu_dieu_chinh_kho/{id}

Sửa nháp.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: PATCH /{id}
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: mutate(id, sua, payload, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    S->>S: Kiểm tra tồn tại, ETag và trạng thái nhap
    break Không tồn tại, lỗi ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 404 / 428 / 412 / 409
    end
    S->>R: Sửa lý do, thay toàn bộ chi tiết nếu gửi
    R->>D: Truy vấn và cập nhật
    S->>U: append sua, trước/sau và lý do nếu có
    U->>D: INSERT audit cùng session
    S->>D: COMMIT
    Note over S,D: Không thay đổi tồn hoặc ledger
    A-->>C: 200 data/meta, ETag mới
    Note over S,U: Không đổi dữ liệu thì không thêm audit
```

### API-77 — DELETE /api/v1/phieu_dieu_chinh_kho/{id}

Xóa nháp.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: DELETE /{id}
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: mutate(id, xoa_nhap, payload, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    S->>S: Kiểm tra tồn tại, ETag và trạng thái nhap
    break Không tồn tại, lỗi ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 404 / 428 / 412 / 409
    end
    S->>R: Audit snapshot, xóa dòng rồi header
    R->>D: Truy vấn và cập nhật
    S->>U: append xoa_nhap, trước/sau và lý do nếu có
    U->>D: INSERT audit cùng session
    S->>D: COMMIT
    Note over S,D: Không thay đổi tồn hoặc ledger
    A-->>C: 204 không body
```

### API-78 — POST /api/v1/phieu_dieu_chinh_kho/{id}/gui

Gửi.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: POST /{id}/gui
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: mutate(id, gui, payload, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    S->>S: Kiểm tra tồn tại, ETag và trạng thái nhap
    break Không tồn tại, lỗi ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 404 / 428 / 412 / 409
    end
    S->>R: Kiểm tra nguồn/delta, nhap sang cho_duyet
    R->>D: Truy vấn và cập nhật
    S->>U: append gui, trước/sau và lý do nếu có
    U->>D: INSERT audit cùng session
    S->>D: COMMIT
    Note over S,D: Không thay đổi tồn hoặc ledger
    A-->>C: 200 data/meta, ETag mới
```

### API-79 — POST /api/v1/phieu_dieu_chinh_kho/{id}/duyet

Duyệt.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: POST /{id}/duyet
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: approve(id, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    break Không tồn tại
        A-->>C: 404
    end
    break Đã da_duyet
        S->>R: ledger_ids
        R->>D: SELECT ledger
        S->>D: Kết thúc transaction đọc
        A-->>C: 200, ETag hiện tại, da_ghi_so_truoc_do=true
    end
    S->>S: Kiểm tra If-Match và cho_duyet
    break Thiếu/cũ ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 428 / 412 / 409
    end
    S->>R: lines, source, stock
    R->>D: Tính lượng hiệu lực, khóa MatHang theo ID
    D-->>R: Dữ liệu hiện hành
    R-->>S: Snapshot nguồn và tồn
    S->>S: Tổng delta theo mặt hàng, kiểm tra tồn/integer
    alt Hợp lệ và mọi bước ghi thành công
        S->>R: replace_lines rồi mark_approved
        R->>D: Ghi snapshot trước khi phiếu bất biến
        S->>R: update_stock, insert_movement
        R->>D: UPDATE MatHang, INSERT GiaoDichKho
        S->>U: append duyet
        U->>D: INSERT audit cùng transaction
        S->>R: ledger_ids
        S->>D: COMMIT
        A-->>C: 200, ETag mới, IDs, da_ghi_so_truoc_do=false
    else Snapshot hợp lệ nhưng kiểm tra tồn hoặc ghi thất bại
        S->>D: ROLLBACK toàn bộ
        S->>R: Transaction riêng, lock và đọc lại
        R->>D: Kiểm tra cạnh tranh
        alt Phiếu đã duyệt
            A-->>C: 200 kết quả đã duyệt
        else Phiếu đã thay đổi hoặc đã loi
            S->>D: ROLLBACK
            A-->>C: 409 can_xu_ly_thu_cong
        else Vẫn đúng phiên bản cho_duyet
            S->>R: create_ticket, create_ticket_line, mark_failed
            R->>D: Ticket độc lập, snapshot và trạng thái loi
            S->>U: append ghi_nhan_loi và tao ticket
            U->>D: INSERT audit cùng transaction lỗi
            alt Lưu thành công
                S->>D: COMMIT
                A-->>C: 409, ticket_id, ticket_da_luu=true
            else Lỗi SQL
                S->>D: ROLLBACK
                S->>S: IncidentStore lưu file bền vững
                A-->>C: 503, ticket_id=null, ticket_da_luu=false
            end
        end
    end
```

### API-80 — POST /api/v1/phieu_dieu_chinh_kho/{id}/tu_choi

Từ chối.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: POST /{id}/tu_choi
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: mutate(id, tu_choi, payload, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    S->>S: Kiểm tra tồn tại, ETag và trạng thái cho_duyet
    break Không tồn tại, lỗi ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 404 / 428 / 412 / 409
    end
    S->>R: cho_duyet sang tu_choi, ghi lý do
    R->>D: Truy vấn và cập nhật
    S->>U: append tu_choi, trước/sau và lý do nếu có
    U->>D: INSERT audit cùng session
    S->>D: COMMIT
    Note over S,D: Không thay đổi tồn hoặc ledger
    A-->>C: 200 data/meta, ETag mới
```

### API-81 — POST /api/v1/phieu_dieu_chinh_kho/{id}/ve_nhap

Về nháp.

```mermaid
sequenceDiagram
    actor C as Client
    participant A as API
    participant S as Service
    participant R as Repo
    participant U as AuditService
    participant D as PostgreSQL
    C->>A: POST /{id}/ve_nhap
    A->>A: JWT, tài khoản hoạt động, quyền quan_ly, validation
    break Auth hoặc đầu vào không hợp lệ
        A-->>C: 401 / 403 / 422
    end
    A->>S: mutate(id, ve_nhap, payload, If-Match, actor)
    S->>R: lock(id), actor
    R->>D: Khóa nguồn/phiếu, kiểm tra quyền hiện tại
    D-->>R: Dữ liệu
    R-->>S: Phiếu hiện hành
    S->>S: Kiểm tra tồn tại, ETag và trạng thái tu_choi
    break Không tồn tại, lỗi ETag hoặc sai trạng thái
        S->>D: ROLLBACK
        A-->>C: 404 / 428 / 412 / 409
    end
    S->>R: tu_choi sang nhap, ghi lý do
    R->>D: Truy vấn và cập nhật
    S->>U: append ve_nhap, trước/sau và lý do nếu có
    U->>D: INSERT audit cùng session
    S->>D: COMMIT
    Note over S,D: Không thay đổi tồn hoặc ledger
    A-->>C: 200 data/meta, ETag mới
```
