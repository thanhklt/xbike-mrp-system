# Luồng API phiếu nhập

Đối chiếu ngày 03/11/2026 với router, service, repository, schema, ORM và dependency hiện tại trong `backend/app/modules/phieu_nhap/`. Cấu trúc phiếu nhập/tồn nâng theo ERD v3.1 và quyết định của dev; giữ tên bảng snake_case.
Nguồn nghiệp vụ: [API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view), mục 2, 3, 5, 7, 13, 14 và quy ước mã trong `infra/postgres/init.sql`.

## Mở sơ đồ từng endpoint

Mỗi endpoint có mã Mermaid bên dưới và ảnh PNG tương ứng để mở trong trình duyệt hoặc đưa vào báo cáo. Q = `quan_ly`, A = `quan_tri_vien`, N = `nhan_vien`.

| Endpoint | Quyền | Ảnh sequence |
|---|---|---|
| GET `/api/v1/phieu_nhap` | Q | [Danh sách phiếu nhập](assets/phieu_nhap/01-danh-sach.png) |
| GET `/api/v1/phieu_nhap/{id}` | Q | [Chi tiết phiếu nhập](assets/phieu_nhap/02-chi-tiet.png) |
| POST `/api/v1/phieu_nhap` | Q | [Tạo phiếu nháp](assets/phieu_nhap/03-tao-nhap.png) |
| PATCH `/api/v1/phieu_nhap/{id}` | Q | [Sửa phiếu nháp](assets/phieu_nhap/04-sua-nhap.png) |
| DELETE `/api/v1/phieu_nhap/{id}` | Q | [Xóa phiếu nháp](assets/phieu_nhap/05-xoa-nhap.png) |
| POST `/api/v1/phieu_nhap/{id}/hoan_tat` | Q | [Hoàn tất và ghi sổ kho](assets/phieu_nhap/06-hoan-tat.png) |
| GET `/api/v1/receiving` | A/Q/N | [Danh sách qua route cũ](assets/phieu_nhap/07-receiving-danh-sach.png) |
| GET `/api/v1/receiving/{grn_id}` | A/Q/N | [Chi tiết qua route cũ](assets/phieu_nhap/08-receiving-chi-tiet.png) |
| POST `/api/v1/receiving` | A/Q/N | [Tạo nháp qua route cũ](assets/phieu_nhap/09-receiving-tao-nhap.png) |

Các bước xác thực và validation trong sơ đồ được nhóm để dễ đọc; FastAPI có thể xử lý dependency/validation xen kẽ trước khi vào handler. Transaction dùng chung session đã được mở khi xác thực. Mũi tên lỗi gửi về Client biểu diễn HTTP response sau exception handler, không phải repository tự tạo HTTP response.

## Quy ước đang triển khai

- Sáu endpoint `/phieu_nhap` chỉ dành cho Q (`quan_ly`). JWT, phiên bản mật khẩu và trạng thái tài khoản được kiểm tra ở mỗi request. A không mặc định có quyền Q.
- Response thành công: `{data, meta}`; danh sách có page/page_size/total/total_pages/request_id. Lỗi: `{error: {code, message, details}, meta: {request_id}}`.
- GET chi tiết và POST trả strong ETag tính trên toàn bộ PhieuNhapRead, bao gồm các dòng chi tiết được sắp theo ID. `request_id` không tham gia ETag.
- POST tạo mới chỉ tạo trạng thái `nhap`, không ghi `ton_kho` hoặc `giao_dich_kho`. PATCH/DELETE chỉ tác động nháp chưa có giao dịch kho. Chỉ action `hoan_tat` cộng tồn, ghi ledger và chuyển trạng thái.
- PATCH, DELETE và hoàn tất yêu cầu If-Match. Sau khi khóa phiếu, không tìm thấy trả 404, thiếu header trả 428. ETag cũ trả 412; riêng hoàn tất đã thành công cho phép retry với ETag cũ nhưng vẫn cần header. Header lặp trả 422.
- GET mới giữ khóa FOR SHARE trên phiếu đến khi đọc xong chi tiết để response và ETag cùng một phiên bản. GET không ghi dữ liệu. COUNT và trang danh sách là hai truy vấn, tổng số có thể thay đổi khi có request tạo/xóa đồng thời.
- Hoàn tất khóa phiếu, chi tiết rồi mặt hàng FOR UPDATE theo ID tăng dần. Cập nhật trực tiếp `mat_hang.so_luong_ton` và `ton_kho_updated_at`; không truy vấn hoặc ghi `ton_kho`, không cấp ID tồn hay lấy advisory lock tồn. Các phiếu dùng chung mặt hàng được tuần tự hóa bằng khóa dòng.
- Trước cộng tồn, số dư phải khớp tổng ledger và số lượng mới không vượt INTEGER. Sai lệch trả 409, không tự sửa số dư. Mỗi chi tiết sinh đúng một `nhap_vat_tu` dương với duy nhất FK nguồn `chi_tiet_phieu_nhap_id`. Tồn, ledger, trạng thái và audit cùng commit hoặc cùng rollback.
- PostgreSQL cấp ID phiếu và chi tiết bằng IDENTITY. Advisory transaction lock `(20261022, 1)` chỉ bảo vệ mã tháng; mã lớn nhất xét cả bảng và snapshot audit. Migration đồng bộ sequence theo ID đang có và lịch sử; rollback có thể tạo khoảng trống ID.
- Mã `PN-YYYYMM-NNNNNN` do server sinh theo tháng Asia/Ho_Chi_Minh, từ 000001 đến 999999. PostgreSQL chuyển múi giờ, không phụ thuộc tzdata trên máy Windows. Hết dải trả 409, không quay vòng.
- `created_at` là TIMESTAMPTZ, API mới trả UTC có Z; `ngay_nhap` là DATE bắt buộc, `ghi_chu` nullable. Người lập/NCC/thời gian không được NULL sau nâng cấp. Tiền NULL cũ được giữ nhưng phiếu có giá/tổng không hợp lệ không được hoàn tất.
- Tiền dùng Decimal/numeric(18,2), giá >= 0, tối đa 9999999999999999.99 và hai chữ số thập phân; request nhận chuỗi hoặc integer, từ chối float/bool. Response tiền là chuỗi hai chữ số. Số lượng/ID vẫn integer nghiêm ngặt trong dải INTEGER. Tổng do server tính.
- POST khóa nhà cung cấp bằng FOR KEY SHARE và mặt hàng bằng FOR UPDATE theo ID tăng dần trước khi kiểm tra; giữ khóa đến commit/rollback. Chỉ nhận mặt hàng active là NVL hoặc linh kiện. PATCH cũng khóa mặt hàng trước khi kiểm tra/thay dòng; tránh nâng khóa SHARE sang UPDATE khi hoàn tất.
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

Body: `ncc_id`, `ngay_nhap` (YYYY-MM-DD) và `chi_tiet` bắt buộc; `ghi_chu` tùy chọn nullable. Chi tiết có ít nhất một dòng `{mat_hang_id, so_luong, don_gia_thuc}`, không trùng mặt hàng. Không cần If-Match khi tạo mới. Nếu nhà cung cấp/mặt hàng không tồn tại trả 404; mặt hàng không active hoặc sai loại trả 409 `phu_thuoc_khong_hop_le`.

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
        R->>R: Validate NCC/ngày nhập, Decimal, số lượng, tổng tiền, dòng trùng và query
        alt Input không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Hợp lệ
            R->>S: create_receipt(payload, actor, request_id)
            S->>T: Vào transaction của session
            S->>P: lock_supplier(ncc_id)
            P->>DB: SELECT NCC FOR KEY SHARE
            S->>P: lock_parts(ids)
            P->>DB: SELECT FOR UPDATE mặt hàng theo ID tăng dần
            alt Không tồn tại tham chiếu hoặc mặt hàng không được nhập
                S->>T: Rollback
                S-->>C: 404 hoặc 409
            else Tham chiếu hợp lệ
                S->>S: Lấy người tạo từ JWT, tính tiền, đặt nhap và UTC
                S->>P: add_draft
                P->>DB: Advisory lock mã tháng, đọc mã trong bảng cùng audit
                alt Hết dải ID hoặc mã tháng
                    P-->>S: Conflict
                    S->>T: Rollback
                    S-->>C: 409
                else Cấp được mã
                    P->>DB: INSERT phiếu và mọi dòng chi tiết bằng IDENTITY
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
    Note over S,DB: Chỉ lưu nháp và audit, không cập nhật tồn mat_hang hoặc ghi giao_dich_kho
```

## PATCH /api/v1/phieu_nhap/{id}

Body nhận `ncc_id`, `ngay_nhap`, `ghi_chu` và `chi_tiet` tùy chọn. Bỏ trường nghĩa là giữ nguyên; chỉ `ghi_chu` được gửi null để xóa ghi chú. `chi_tiet` nếu gửi phải là mảng có ít nhất một dòng, thay toàn bộ chi tiết, không nhận null hoặc mặt hàng trùng. Server tính lại tiền; database cấp ID mới cho bộ chi tiết thay thế. Payload không làm thay đổi dữ liệu trả 200 với ETag cũ, không ghi audit. Không sửa phiếu hoàn thành hoặc phiếu có ledger.

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
                    P->>DB: NCC FOR KEY SHARE, mặt hàng FOR UPDATE theo ID
                    alt Tham chiếu thiếu hoặc mặt hàng inactive, sai loại
                        S->>T: Rollback
                        S-->>C: 404 hoặc 409
                    else Tham chiếu hợp lệ
                        S->>S: Tính tiền và xác định thay đổi
                        opt Dữ liệu thực sự thay đổi
                            S->>P: patch_draft
                            P->>DB: Khi thay chi tiết, DELETE và INSERT dòng với IDENTITY
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

Không nhận query. Xóa chi tiết rồi phiếu nháp trong cùng transaction với audit `xoa_nhap`, snapshot trước xóa và snapshot sau là NULL. Giữ lịch sử trong audit; sequence không quay lùi khi xóa nháp, mã xét cả lịch sử. Thành công 204 không body. Phiếu hoàn thành hoặc đã có giao dịch phụ thuộc không được xóa.

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
                        P->>DB: FOR UPDATE mặt hàng
                        alt Thiếu mặt hàng, inactive hoặc không phải NVL/linh kiện
                            S->>T: Rollback
                            S-->>C: 404 hoặc 409
                        else Được nhập
                            S->>I: receive_receipt(lines, actor, posted_at)
                            I->>DB: SELECT mat_hang FOR UPDATE theo ID tăng dần (khóa đã giữ từ validate)
                            I->>DB: Đọc tổng biến động ledger cho từng mặt hàng
                            alt Số dư không khớp ledger hoặc tràn INTEGER
                                S->>T: Rollback
                                S-->>C: 409
                            else Có thể ghi sổ
                                I->>DB: UPDATE mat_hang.so_luong_ton và ton_kho_updated_at
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
        D-->>C: 401 hoặc 403 qua exception handler
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

Route cũ vẫn cho A/Q/N, giữ mã do client cung cấp, `items` và response trực tiếp. Do ràng buộc v3.1, bắt buộc NCC/ngày nhập, ít nhất một dòng và giá không NULL; kiểm tra mặt hàng active NVL/linh kiện như API mới. Người tạo luôn lấy từ JWT; giá trị tổng client gửi được tính lại. IDENTITY cấp ID, chung khóa mã với API mới; tiền response là chuỗi Decimal.

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
            S->>T: Vào transaction
            S->>P: lock_supplier và lock_parts theo ID
            P->>DB: NCC FOR KEY SHARE, mặt hàng FOR UPDATE
            alt Thiếu NCC/mặt hàng hoặc mặt hàng không hợp lệ
                S-->>C: 404 hoặc 409, rollback transaction
            else Tham chiếu hợp lệ
                S->>S: Lấy nhan_vien_id từ JWT, tính lại tổng bằng Decimal
                S->>P: add
                P->>DB: Advisory lock mã tháng, database cấp IDENTITY phiếu/dòng
                P->>DB: INSERT phiếu và items
                P-->>S: CreatedRecord và snapshot
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
    end
    Note over R,DB: Không ghi tồn kho/ledger, không Location hay ETag trên route cũ
```
