# Luồng API phiếu nhập

Đối chiếu ngày 22/10/2026 với router, service, repository, schema, ORM và dependency hiện tại trong `backend/app/modules/phieu_nhap/`.
Nguồn nghiệp vụ: [API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view), mục 2, 3, 5, 7, 13, 14 và quy ước mã trong `infra/postgres/init.sql`.

## Quy ước đang triển khai

- Sáu endpoint `/phieu_nhap` chỉ dành cho Q (`quan_ly`). JWT, phiên bản mật khẩu và trạng thái tài khoản được kiểm tra ở mỗi request. A không mặc định có quyền Q.
- Response thành công: `{data, meta}`; danh sách có page/page_size/total/total_pages/request_id. Lỗi: `{error: {code, message, details}, meta: {request_id}}`.
- GET chi tiết và POST trả strong ETag tính trên toàn bộ PhieuNhapRead, bao gồm các dòng chi tiết được sắp theo ID. `request_id` không tham gia ETag.
- POST tạo mới chỉ tạo trạng thái `nhap`, không ghi `ton_kho` hoặc `giao_dich_kho`. PATCH/DELETE chỉ tác động nháp chưa có giao dịch kho. Chỉ action `hoan_tat` cộng tồn, ghi ledger và chuyển trạng thái.
- PATCH, DELETE và hoàn tất yêu cầu If-Match. Sau khi khóa phiếu, không tìm thấy trả 404, thiếu header trả 428. ETag cũ trả 412; riêng hoàn tất đã thành công cho phép retry với ETag cũ nhưng vẫn cần header. Header lặp trả 422.
- GET mới giữ khóa FOR SHARE trên phiếu đến khi đọc xong chi tiết để response và ETag cùng một phiên bản. GET không ghi dữ liệu. COUNT và trang danh sách là hai truy vấn, tổng số có thể thay đổi khi có request tạo/xóa đồng thời.
- Hoàn tất khóa phiếu và chi tiết FOR UPDATE, khóa mặt hàng FOR SHARE theo ID tăng dần, rồi lấy advisory transaction lock tồn kho `(20261022, 2)`. Khóa các dòng tồn theo mã mặt hàng, cấp ID cho dòng tồn chưa có bằng MAX(id)+1 dưới khóa, đúng SQL không Identity. Các lần ghi sổ phiếu nhập được tuần tự hóa tại khóa này.
- Trước cộng tồn, số dư phải khớp tổng ledger và số lượng mới không vượt INTEGER. Sai lệch trả 409, không tự sửa số dư. Mỗi chi tiết sinh đúng một `nhap_vat_tu` dương với duy nhất FK nguồn `chi_tiet_phieu_nhap_id`. Tồn, ledger, trạng thái và audit cùng commit hoặc cùng rollback.
- Theo quyết định của dev: giữ SQL, backend cấp ID phiếu và dòng dưới advisory transaction lock `(20261022, 1)`. Xét ID/mã lớn nhất trong bảng và snapshot audit để không tái sử dụng những giá trị đã lưu lịch sử.
- Mã `PN-YYYYMM-NNNNNN` do server sinh theo tháng Asia/Ho_Chi_Minh, từ 000001 đến 999999. PostgreSQL chuyển múi giờ, không phụ thuộc tzdata trên máy Windows. Hết dải trả 409, không quay vòng.
- `created_at` lưu UTC vào cột TIMESTAMP WITHOUT TIME ZONE, API mới trả UTC có Z. Dữ liệu cũ giữ NULL ở người tạo, tiền, thời gian và đơn giá; không tự sửa dữ liệu cũ.
- Tiền và số lượng đầu vào là JSON integer nghiêm ngặt. Số lượng > 0, giá >= 0; tổng tiền không vượt INTEGER PostgreSQL (2,147,483,647). ID dòng/mã phiếu/tổng/trạng thái/người tạo/thời gian do server quản lý.
- POST khóa nhà cung cấp bằng FOR KEY SHARE và mặt hàng bằng FOR SHARE theo ID tăng dần trước khi kiểm tra; giữ khóa đến commit/rollback. Chỉ nhận mặt hàng active là NVL hoặc linh kiện.
- Tạo phiếu, mọi dòng và audit `tao` cùng transaction. Audit lỗi thì rollback tất cả. Audit lưu snapshot PhieuNhapRead và người thực hiện từ JWT.
- `/receiving` là các route cũ vẫn được giữ để tương thích, có quyền/payload/envelope khác; không xem chúng là contract v2.

## GET /api/v1/phieu_nhap

Query: page (1), page_size (20, tối đa 100), q tìm mã không phân biệt hoa/thường, trang_thai, ncc_id, nhan_vien_id, tu_ngay, den_ngay, sort. Sort cho phép id/created_at/ma_phieu_nhap và dạng `-` giảm dần, ID là tiêu chí phụ. Ký tự `%`/`_` trong q được hiểu theo nghĩa đen. Filter kết hợp AND.

Ngày lọc theo Asia/Ho_Chi_Minh, lấy cả hai ngày bằng khoảng UTC nửa mở. Không tìm thấy trả 200 với danh sách rỗng. Không ghi audit hay thay đổi trạng thái/tồn kho.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_nhap + JWT + query
    R->>D: Xác thực và require_roles Q
    D->>DB: Đọc tài khoản hiện tại và vai trò
    alt JWT thiếu, hết hạn hoặc bị thu hồi
        D-->>C: 401 chua_xac_thuc
    else Tài khoản bị khóa hoặc vai trò không phải Q
        D-->>C: 403
    else Được phép
        R->>R: Validate query, cấm tham số lạ và lặp
        alt Sai enum, ngày, phân trang hoặc sort
            R-->>C: 422 du_lieu_khong_hop_le
        else Hợp lệ
            R->>S: list_receipts(params, request_id)
            S->>P: list_receipts(params)
            P->>DB: COUNT theo bộ lọc và khoảng ngày UTC
            opt Trang còn dữ liệu
                P->>DB: SELECT phiếu phân trang FOR SHARE rồi đọc chi tiết liên quan
            end
            DB-->>P: Dữ liệu và tổng số phiếu
            P-->>S: RecordPage
            S-->>R: data + meta phân trang
            R-->>C: 200 PhieuNhapListResponse
        end
    end
    Note over R,DB: Lỗi nội bộ chưa phân loại trả 500 an toàn, không lộ SQL
```

## GET /api/v1/phieu_nhap/{id}

ID nguyên dương; không nhận query. ID vượt INTEGER PostgreSQL trả 404, không đưa giá trị tràn vào truy vấn. GET được đọc cả phiếu nháp và hoàn thành, kể cả dữ liệu lịch sử có mặt hàng ngừng hoạt động.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_nhap/id + JWT
    R->>D: Kiểm tra JWT và quyền Q
    D->>DB: Đọc trạng thái tài khoản và vai trò
    alt Xác thực hoặc quyền không hợp lệ
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID và cấm query
        alt Đầu vào không hợp lệ
            R-->>C: 422
        else Hợp lệ
            R->>S: get_receipt(id, request_id)
            S->>P: get_receipt(id) nếu ID trong dải INTEGER
            P->>DB: SELECT phiếu FOR SHARE rồi đọc chi tiết
            alt ID không tồn tại hoặc vượt dải
                S-->>C: 404 khong_tim_thay
            else Có phiếu
                P->>P: Chuyển ORM sang schema, chuẩn hóa UTC và thứ tự dòng
                P-->>S: PhieuNhapRead
                S->>S: Tính ETag trên PhieuNhapRead
                S-->>R: data + meta + ETag
                R-->>C: 200 và header ETag
            end
        end
    end
    Note over R,DB: Chỉ đọc dữ liệu, lỗi nội bộ trả 500 an toàn
```

## POST /api/v1/phieu_nhap

Body: `ncc_id` tùy chọn nullable, `chi_tiet` bắt buộc có ít nhất một dòng `{mat_hang_id, so_luong, don_gia_thuc}`. Không trùng mặt hàng. Không cần If-Match khi tạo mới. Nếu nhà cung cấp/mặt hàng không tồn tại trả 404; mặt hàng không active hoặc sai loại trả 409 `phu_thuoc_khong_hop_le`.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant A as AuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_nhap + JWT + JSON
    R->>D: Kiểm tra JWT, account active và quyền Q
    D->>DB: SELECT tài khoản và vai trò
    alt Không xác thực hoặc không có quyền
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate body, số nguyên, tổng tiền, dòng trùng, cấm query
        alt Input không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Hợp lệ
            R->>S: create_receipt(payload, actor, request_id)
            S->>T: Vào transaction của session
            opt Có ncc_id
                S->>P: lock_supplier(ncc_id)
                P->>DB: SELECT FOR KEY SHARE
            end
            S->>P: lock_parts(ids)
            P->>DB: SELECT FOR SHARE theo ID tăng dần
            alt Không tồn tại tham chiếu hoặc mặt hàng không được nhập
                S->>T: Rollback
                S-->>C: 404 hoặc 409
            else Tham chiếu hợp lệ
                S->>S: Lấy người tạo từ JWT, tính tiền, đặt nhap và UTC
                S->>P: add_draft
                P->>DB: Advisory lock và đọc ID, mã trong bảng cùng audit
                alt Hết dải ID hoặc mã tháng
                    P-->>S: Conflict
                    S->>T: Rollback
                    S-->>C: 409
                else Cấp được ID và mã
                    P->>DB: INSERT phiếu và mọi dòng chi tiết
                    P-->>S: PhieuNhapRead
                    S->>A: append audit tao với snapshot sau tạo
                    A->>DB: Đưa audit vào cùng session
                    S->>T: Commit phiếu, chi tiết và audit
                    alt Lỗi ghi dữ liệu hoặc audit
                        T->>DB: ROLLBACK toàn bộ
                        T-->>C: 409 constraint hoặc 500 lỗi nội bộ
                    else Thành công
                        T->>DB: COMMIT
                        S-->>R: data + meta + ETag
                        R-->>C: 201, Location và ETag
                    end
                end
            end
        end
    end
    Note over S,DB: Không có thao tác ghi ton_kho hoặc giao_dich_kho
```

## PATCH /api/v1/phieu_nhap/{id}

Body nhận `ncc_id` và `chi_tiet` tùy chọn. Bỏ trường nghĩa là giữ nguyên; `ncc_id: null` bỏ liên kết NCC. `chi_tiet` nếu gửi phải là mảng có ít nhất một dòng, thay toàn bộ chi tiết, không nhận null hoặc mặt hàng trùng. Server tính lại tiền và cấp ID mới cho bộ chi tiết thay thế. Payload không làm thay đổi dữ liệu trả 200 với ETag cũ, không ghi audit. Không sửa phiếu hoàn thành hoặc phiếu có ledger.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant A as AuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: PATCH /api/v1/phieu_nhap/id + JWT + If-Match + JSON
    R->>D: Kiểm tra JWT, account và quyền Q
    D->>DB: Đọc tài khoản hiện tại
    alt Không xác thực hoặc không có quyền
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID, body, query và header không lặp
        alt Input sai
            R-->>C: 422
        else Input hợp lệ
            R->>S: patch_receipt
            S->>T: Vào transaction
            S->>P: lock_receipt
            P->>DB: FOR UPDATE phiếu rồi chi tiết
            alt Không tồn tại hoặc thiếu If-Match
                S->>T: Rollback
                S-->>C: 404 hoặc 428
            else Có phiếu và header
                S->>S: So sánh ETag dưới khóa
                S->>P: receipt_postings nếu ETag đúng và phiếu nhap
                P->>DB: Đọc ledger theo chi tiết
                alt ETag cũ, không phải nháp hoặc đã có ledger
                    S->>T: Rollback
                    S-->>C: 412 hoặc 409
                else Có thể sửa
                    S->>P: Khóa NCC mới nếu có và mặt hàng khi gửi chi_tiet
                    P->>DB: NCC FOR KEY SHARE, mặt hàng FOR SHARE theo ID
                    alt Tham chiếu thiếu hoặc mặt hàng inactive, sai loại
                        S->>T: Rollback
                        S-->>C: 404 hoặc 409
                    else Tham chiếu hợp lệ
                        S->>S: Tính tiền và xác định thay đổi
                        opt Dữ liệu thực sự thay đổi
                            S->>P: patch_draft
                            P->>DB: Khi thay chi tiết, advisory lock cấp ID rồi DELETE và INSERT dòng
                            P->>DB: UPDATE phiếu và đọc lại dữ liệu
                            S->>A: append sua với snapshot trước và sau
                            A->>DB: Ghi audit cùng session
                        end
                        S->>T: Commit
                        alt Lỗi ghi hoặc audit
                            T->>DB: ROLLBACK mọi thay đổi
                            T-->>C: 409 constraint hoặc 500 an toàn
                        else Thành công
                            T->>DB: COMMIT
                            S-->>R: PhieuNhapDetailResponse và ETag
                            R-->>C: 200 và ETag hiện tại
                        end
                    end
                end
            end
        end
    end
    Note over S,DB: Không ghi tồn kho hoặc ledger khi sửa nháp
```

## DELETE /api/v1/phieu_nhap/{id}

Không nhận query. Xóa chi tiết rồi phiếu nháp trong cùng transaction với audit `xoa_nhap`, snapshot trước xóa và snapshot sau là NULL. Giữ lịch sử ID/mã trong audit để allocator không tái sử dụng. Thành công 204 không body. Phiếu hoàn thành hoặc đã có giao dịch phụ thuộc không được xóa.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant A as AuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: DELETE /api/v1/phieu_nhap/id + JWT + If-Match
    R->>D: Kiểm tra JWT, account và quyền Q
    D->>DB: Đọc tài khoản hiện tại
    alt Không xác thực hoặc không có quyền
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID, cấm query và header lặp
        alt Input sai
            R-->>C: 422
        else Hợp lệ
            R->>S: delete_receipt
            S->>T: Vào transaction
            S->>P: lock_receipt
            P->>DB: FOR UPDATE phiếu rồi chi tiết
            alt Không tìm thấy hoặc thiếu header
                S->>T: Rollback
                S-->>C: 404 hoặc 428
            else Có phiếu và If-Match
                S->>S: So sánh ETag và kiểm tra nhap
                S->>P: receipt_postings nếu kiểm tra trước hợp lệ
                P->>DB: SELECT ledger theo chi tiết
                alt ETag cũ, không phải nháp hoặc có phụ thuộc
                    S->>T: Rollback
                    S-->>C: 412 hoặc 409
                else Được xóa
                    S->>P: delete_draft
                    P->>DB: DELETE chi tiết rồi phiếu
                    S->>A: append xoa_nhap với snapshot trước xóa
                    A->>DB: Ghi audit cùng session
                    S->>T: Commit
                    alt Lỗi FK, ghi dữ liệu hoặc audit
                        T->>DB: ROLLBACK cả xóa và audit
                        T-->>C: 409 hoặc 500 an toàn
                    else Thành công
                        T->>DB: COMMIT
                        R-->>C: 204 không body
                    end
                end
            end
        end
    end
    Note over S,DB: Không xóa hoặc sửa ledger, không thay đổi tồn kho
```

## POST /api/v1/phieu_nhap/{id}/hoan_tat

Body bắt buộc là `{}`, không nhận query hay trường thêm. Kết quả gồm PhieuNhapRead, `giao_dich_kho_ids` và `da_ghi_so_truoc_do`. ETag tính từ PhieuNhapRead, giống GET chi tiết, không tính hai trường action. Người ghi ledger/audit là người đang thực hiện action, không đổi người tạo phiếu. Thời điểm ghi sổ là UTC, dùng chung cho mọi dòng của một lần hoàn tất.

Retry phải còn quyền Q và có If-Match. Nếu phiếu hoàn thành, đối chiếu chính xác ledger với từng dòng trước khi trả `da_ghi_so_truoc_do=true`; không tạo thêm audit/ledger hoặc cộng lại tồn. Trạng thái hoàn thành nhưng thiếu/sai ledger trả 409. Nháp cũ thiếu giá, sai tổng hoặc rỗng trả 409 để sửa trước khi hoàn tất.

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant I as InventoryRepository
    participant A as AuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_nhap/id/hoan_tat + JWT + If-Match + {}
    R->>D: Kiểm tra JWT, account và quyền Q
    D->>DB: Đọc tài khoản hiện tại
    alt Không xác thực hoặc không có quyền
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate ID, body rỗng, cấm query và header lặp
        alt Input sai
            R-->>C: 422
        else Input hợp lệ
            R->>S: complete_receipt
            S->>T: Vào transaction
            S->>P: lock_receipt
            P->>DB: FOR UPDATE phiếu rồi chi tiết
            alt Không tìm thấy hoặc thiếu If-Match
                S->>T: Rollback
                S-->>C: 404 hoặc 428
            else Có phiếu và header
                S->>P: receipt_postings
                P->>DB: Đọc ledger theo chi tiết
                alt Phiếu đã hoàn thành
                    S->>S: Đối chiếu đủ nguồn, mặt hàng, loại và lượng ledger
                    alt Ledger không khớp
                        S->>T: Rollback
                        S-->>C: 409
                    else Đã ghi sổ đúng
                        S->>T: Kết thúc transaction không ghi thêm
                        S-->>C: 200 resource hiện tại, ID ledger cũ, da_ghi_so_truoc_do=true, ETag
                    end
                else Phiếu nháp
                    S->>S: So sánh ETag, kiểm tra chưa có ledger và dữ liệu tiền/dòng
                    alt ETag cũ hoặc dữ liệu nháp không hợp lệ
                        S->>T: Rollback
                        S-->>C: 412 hoặc 409
                    else Nháp hợp lệ
                        S->>P: lock_parts theo ID tăng dần
                        P->>DB: FOR SHARE mặt hàng
                        alt Thiếu mặt hàng, inactive hoặc không phải NVL/linh kiện
                            S->>T: Rollback
                            S-->>C: 404 hoặc 409
                        else Được nhập
                            S->>I: receive_receipt(lines, actor, posted_at)
                            I->>DB: Advisory lock tồn kho rồi FOR UPDATE các dòng tồn theo mặt hàng
                            I->>DB: Đọc tổng ledger và MAX ID tồn kho
                            alt Số dư không khớp ledger hoặc tràn INTEGER
                                S->>T: Rollback
                                S-->>C: 409
                            else Có thể ghi sổ
                                I->>DB: UPDATE tồn hoặc INSERT dòng tồn với ID cấp dưới khóa
                                I->>DB: INSERT một nhap_vat_tu dương cho mỗi chi tiết
                                I-->>S: Danh sách ID giao dịch
                                S->>P: mark_completed
                                P->>DB: UPDATE hoan_thanh và đọc lại phiếu
                                S->>A: append hoan_tat với snapshot trước và sau
                                A->>DB: Ghi audit cùng session
                                S->>T: Commit
                                alt Lỗi ở bất kỳ bước ghi hoặc commit
                                    T->>DB: ROLLBACK tồn, ledger, trạng thái và audit
                                    T-->>C: 409 constraint hoặc 500 an toàn
                                else Thành công
                                    T->>DB: COMMIT
                                    S-->>R: PhieuNhapActionResponse và ETag mới
                                    R-->>C: 200, da_ghi_so_truoc_do=false
                                end
                            end
                        end
                    end
                end
            end
        end
    end
```

## GET /api/v1/receiving

Route cũ: mọi tài khoản A/Q/N hợp lệ được đọc, dùng PageParams (`page`, `page_size`, `search`, `sort_by`, `sort_order`) và PaginatedResponse cũ, trường dòng là `items`. Không có ETag.

```mermaid
sequenceDiagram
    actor C as Client cũ
    participant R as Legacy router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/receiving
    R->>D: Kiểm tra JWT và tài khoản
    D->>DB: Đọc account hiện tại
    alt JWT sai hoặc tài khoản không hoạt động
        D-->>C: 401 hoặc 403 theo envelope cũ
    else Hợp lệ
        R->>R: Validate PageParams
        alt Phân trang sai
            R-->>C: 422
        else Hợp lệ
            R->>S: list_entries
            S->>P: list_entries
            P->>DB: COUNT và SELECT phân trang kèm items
            P-->>S: RecordPage
            S-->>R: PaginatedResponse
            R-->>C: 200 theo envelope cũ
        end
    end
    Note over R,DB: Không ghi kho/audit, lỗi chưa phân loại trả 500
```

## GET /api/v1/receiving/{grn_id}

Route cũ trả GoodsReceiptNoteResponse trực tiếp, không có meta/ETag. Giữ validation path integer cũ.

```mermaid
sequenceDiagram
    actor C as Client cũ
    participant R as Legacy router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/receiving/grn_id
    R->>D: Kiểm tra JWT và tài khoản
    D->>DB: Đọc account hiện tại
    alt Không xác thực hoặc account bị khóa
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate grn_id là integer
        alt Sai kiểu
            R-->>C: 422
        else Hợp lệ
            R->>S: get_entry
            S->>P: get_by_id
            P->>DB: SELECT phiếu và items
            alt Không tồn tại
                S-->>C: 404
            else Tồn tại
                S-->>R: GoodsReceiptNoteResponse
                R-->>C: 200, không ETag
            end
        end
    end
    Note over R,DB: Không ghi kho/audit, lỗi chưa phân loại trả 500
```

## POST /api/v1/receiving

Route cũ vẫn cho A/Q/N, nhận ma_phieu_nhap, items, tổng tiền và giá dòng theo schema cũ, cho phép nháp rỗng. Người tạo luôn được ghi đè bằng JWT. Đây không phải validation của contract v2. Cùng allocator dưới khóa với API mới để không cấp trùng ID; route cũ vẫn giữ mã do client cung cấp.

```mermaid
sequenceDiagram
    actor C as Client cũ
    participant R as Legacy router
    participant D as Auth dependencies
    participant S as ReceivingService
    participant P as ReceivingRepository
    participant A as AuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/receiving + body cũ
    R->>D: Kiểm tra JWT và vai trò A/Q/N
    D->>DB: Đọc account hiện tại
    alt Không xác thực hoặc account bị khóa
        D-->>C: 401 hoặc 403
    else Được phép
        R->>R: Validate GoodsReceiptNoteCreate
        alt Input không hợp lệ
            R-->>C: 422
        else Hợp lệ
            R->>S: create_entry
            S->>S: Ghi đè nhan_vien_id bằng JWT
            S->>T: Vào transaction
            S->>P: add
            P->>DB: Advisory lock, cấp ID phiếu và dòng
            P->>DB: INSERT phiếu và items
            P-->>S: CreatedRecord và snapshot cũ
            S->>A: append audit tao
            A->>DB: Đưa audit vào cùng session
            S->>T: Commit
            alt Trùng mã, constraint, hết dải hoặc lỗi nội bộ
                T->>DB: ROLLBACK
                T-->>C: 409 hoặc 500
            else Thành công
                T->>DB: COMMIT
                R-->>C: 201 GoodsReceiptNoteResponse trực tiếp
            end
        end
    end
    Note over R,DB: Không ghi tồn kho/ledger, không Location hay ETag trên route cũ
```
