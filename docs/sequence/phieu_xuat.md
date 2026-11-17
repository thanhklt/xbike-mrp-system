# Luồng API phiếu xuất — main v4

Đối chiếu router/service/repository/schema module phieu_xuat, dependencies, inventory, audit và transaction hiện tại. Q = quản lý kho, N = nhân viên được giao yêu cầu hiện tại. Admin bị từ chối. Role/tài khoản/phiên được xác minh từ DB mỗi request; không tin role client khai báo.

Có tám endpoint dưới đây; không có PATCH, DELETE hoặc ve_nhap công khai. Các ảnh PNG v3 trong assets là lịch sử. Pydantic/OpenAPI sinh từ router là nguồn shape kiểm được bằng máy. Không đổi schema DB trong lần thêm GET nguồn/preview.

Các lỗi có error và meta.request_id: 401 sai token/phiên, 403 sai quyền, 422 đầu vào, 404 tài nguyên không có, 409 trạng thái/phụ thuộc/xung đột; lỗi hệ thống 500. If-Match của thao tác ghi thiếu trả 428, sai hoặc cũ trả 412.

## GET /api/v1/phieu_xuat

Chỉ Q. PhieuXuatQuery gồm page/page_size, q, sort, loai_phieu, trang_thai, nhan_vien_id, yeu_cau_san_xuat_id, tu_ngay/den_ngay. Ngày theo Việt Nam. Response data + meta phân trang; không ETag.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant DB as PostgreSQL
    U->>R: GET /api/v1/phieu_xuat + Bearer
    R->>DB: Xác minh tài khoản, role, phiên
    alt Sai xác thực/quyền/đầu vào
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: list_issues
        S->>P: begin_read_snapshot
        P->>DB: REPEATABLE READ READ ONLY
        S->>P: COUNT, lọc, phân trang và đọc dòng
        P->>DB: SELECT
        alt Không có tài nguyên hoặc ngoài phân công
            S-->>U: 404 hoặc 403
        else Trạng thái/phụ thuộc sai hoặc phiếu trùng khi preview
            S-->>U: 409 (chỉ preview)
        else Hợp lệ
            S-->>U: 200 data + meta; ETag chỉ chi tiết phiếu
        end
    end
```

## GET /api/v1/phieu_xuat/theo_yeu_cau/{id}

Q hoặc N; ID dương, cấm query/body. Response data: [{id, ma_phieu_xuat, loai_phieu, trang_thai}], meta.request_id. Chưa có trả []; mở cả yêu cầu hoàn thành/hủy. Không mở quyền danh sách toàn bộ phiếu, không ETag.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant DB as PostgreSQL
    U->>R: GET /api/v1/phieu_xuat/theo_yeu_cau/{id} + Bearer
    R->>DB: Xác minh tài khoản, role, phiên
    alt Sai xác thực/quyền/đầu vào
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: source_issues
        S->>P: begin_read_snapshot
        P->>DB: REPEATABLE READ READ ONLY
        S->>P: Đọc source không khóa; kiểm Q hoặc NV được giao; đọc tham chiếu phiếu
        P->>DB: SELECT
        alt Không có tài nguyên hoặc ngoài phân công
            S-->>U: 404 hoặc 403
        else Trạng thái/phụ thuộc sai hoặc phiếu trùng khi preview
            S-->>U: 409 (chỉ preview)
        else Hợp lệ
            S-->>U: 200 data + meta; ETag chỉ chi tiết phiếu
        end
    end
```

## GET /api/v1/phieu_xuat/xem_truoc/{id}?loai_phieu=...

Chỉ N. loai_phieu bắt buộc xuat_linh_kien hoặc xuat_thanh_pham; cấm query thừa/lặp và GET body. Response data: {yeu_cau_san_xuat_id, loai_phieu, chi_tiet: [{mat_hang_id, so_luong}]}, meta.request_id. UI ghép mã/tên/đơn vị từ catalog thật. Cùng nguồn và validation với create: đang thực hiện; linh kiện có lượng cần sản xuất/nhu cầu; thành phẩm thuộc xuất giao và không cần SX hoặc có chứng từ đã duyệt. Kiểm loại mặt hàng và phiếu trùng. GET không tạo nháp/giữ hàng/audit/ETag; POST vẫn kiểm lại trong transaction.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant DB as PostgreSQL
    U->>R: GET /api/v1/phieu_xuat/xem_truoc/{id} + Bearer
    R->>DB: Xác minh tài khoản, role, phiên
    alt Sai xác thực/quyền/đầu vào
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: preview
        S->>P: begin_read_snapshot
        P->>DB: REPEATABLE READ READ ONLY
        S->>P: Đọc source/nhu cầu/chứng từ; kiểm phân công và trạng thái; đọc loại mặt hàng và phiếu trùng, không khóa
        P->>DB: SELECT
        alt Không có tài nguyên hoặc ngoài phân công
            S-->>U: 404 hoặc 403
        else Trạng thái/phụ thuộc sai hoặc phiếu trùng khi preview
            S-->>U: 409 (chỉ preview)
        else Hợp lệ
            S-->>U: 200 data + meta; ETag chỉ chi tiết phiếu
        end
    end
```

## GET /api/v1/phieu_xuat/{id}

Q hoặc N; kiểm người được giao hiện tại, không chỉ người lập. Cấm query/body. PhieuXuatResponse + strong ETag phiếu/dòng; tiền integer VND hoặc null trước ghi sổ.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant DB as PostgreSQL
    U->>R: GET /api/v1/phieu_xuat/{id} + Bearer
    R->>DB: Xác minh tài khoản, role, phiên
    alt Sai xác thực/quyền/đầu vào
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: get_issue
        S->>P: begin_read_snapshot
        P->>DB: REPEATABLE READ READ ONLY
        S->>P: Đọc phiếu/dòng không khóa; xác minh phân công
        P->>DB: SELECT
        alt Không có tài nguyên hoặc ngoài phân công
            S-->>U: 404 hoặc 403
        else Trạng thái/phụ thuộc sai hoặc phiếu trùng khi preview
            S-->>U: 409 (chỉ preview)
        else Hợp lệ
            S-->>U: 200 data + meta; ETag chỉ chi tiết phiếu
        end
    end
```

## POST /api/v1/phieu_xuat

Chỉ N. Body duy nhất {loai_phieu, yeu_cau_san_xuat_id}, cấm query/field thừa. Source đang thực hiện, phân công và điều kiện nguồn như preview. Server chốt dòng/số lượng, tạo nháp chưa trừ tồn. Mã theo tháng Việt Nam, advisory lock (20261022,3), xét snapshot audit.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant I as InventoryIssueWriter
    participant A as AuditService
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    U->>R: POST /api/v1/phieu_xuat + Bearer + body
    R->>DB: Xác minh tài khoản/role/phiên
    alt Sai xác thực/quyền/input
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: create_issue
        S->>T: Bắt đầu transaction
        S->>P: Khóa source, kiểm phân công/nhu cầu/mặt hàng/trùng; cấp mã, INSERT phiếu nháp và dòng
        P->>DB: SELECT FOR UPDATE/SHARE và ghi cùng session
        alt Sai ID/phân công/trạng thái/validator/phụ thuộc
            S->>T: Rollback
            S-->>U: 404 / 403 / 409; gui,duyet,tu_choi thêm 428 hoặc 412
        else Hợp lệ
            S->>A: append audit cùng session
            S->>T: Commit và flush audit
            alt Lỗi ghi/audit/commit
                T->>DB: Rollback toàn bộ
                S-->>U: 500 hoặc lỗi nghiệp vụ đã ánh xạ
            else Thành công
                S-->>U: 201 resource + Location + ETag
            end
        end
    end
```

## POST /api/v1/phieu_xuat/{id}/gui

Chỉ N. Body {}, If-Match bắt buộc. Nháp/từ chối → chờ duyệt; gửi lại trực tiếp, nội dung bất biến; không trừ tồn/giữ thêm.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant I as InventoryIssueWriter
    participant A as AuditService
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    U->>R: POST /api/v1/phieu_xuat/{id}/gui + Bearer + body
    R->>DB: Xác minh tài khoản/role/phiên
    alt Sai xác thực/quyền/input
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: submit_issue
        S->>T: Bắt đầu transaction
        S->>P: Khóa source rồi phiếu/dòng; kiểm phân công, ETag, trạng thái và nhu cầu; đổi cho_duyet
        P->>DB: SELECT FOR UPDATE/SHARE và ghi cùng session
        alt Sai ID/phân công/trạng thái/validator/phụ thuộc
            S->>T: Rollback
            S-->>U: 404 / 403 / 409; gui,duyet,tu_choi thêm 428 hoặc 412
        else Hợp lệ
            S->>A: append audit cùng session
            S->>T: Commit và flush audit
            alt Lỗi ghi/audit/commit
                T->>DB: Rollback toàn bộ
                S-->>U: 500 hoặc lỗi nghiệp vụ đã ánh xạ
            else Thành công
                S-->>U: 200 resource + ETag
            end
        end
    end
```

## POST /api/v1/phieu_xuat/{id}/duyet

Chỉ Q. Body {}, If-Match bắt buộc. Kiểm nguồn/dòng/giá/tồn/giữ/sổ kho. Chốt giá, trừ tồn/giữ, ghi ledger, cập nhật tiến độ và audit cùng transaction. Replay phiếu ghi đủ trả da_ghi_so_truoc_do=true, không ghi lần hai; vẫn kiểm quyền và định dạng validator.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant I as InventoryIssueWriter
    participant A as AuditService
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    U->>R: POST /api/v1/phieu_xuat/{id}/duyet + Bearer + body
    R->>DB: Xác minh tài khoản/role/phiên
    alt Sai xác thực/quyền/input
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: approve
        S->>T: Bắt đầu transaction
        S->>P: Khóa source, phiếu/dòng; kiểm validator; chốt giá và cập nhật tiến độ
        P->>DB: SELECT FOR UPDATE/SHARE và ghi cùng session
        alt Sai ID/phân công/trạng thái/validator/phụ thuộc
            S->>T: Rollback
            S-->>U: 404 / 403 / 409; gui,duyet,tu_choi thêm 428 hoặc 412
        else Hợp lệ
            alt Đã ghi đủ trước đó
                S-->>U: 200 replay=true, không ghi kho/audit lần hai
            else Cần ghi sổ
                S->>I: Khóa/kiểm tồn và giữ; ghi ledger và trừ số dư
                I->>DB: Ghi cùng session
                S->>A: append audit duyệt
                S->>T: Commit, rollback toàn bộ nếu lỗi
                S-->>U: 200 replay=false + ETag; lỗi 409 hoặc 500
            end
        end
    end
```

## POST /api/v1/phieu_xuat/{id}/tu_choi

Chỉ Q. Body {ly_do} không trắng, If-Match bắt buộc. Chờ duyệt → từ chối, không đổi tồn/giữ hoặc dòng.

```mermaid
sequenceDiagram
    actor U as Người dùng được phép
    participant R as Router và auth dependency
    participant S as PhieuXuatService
    participant P as Repository
    participant I as InventoryIssueWriter
    participant A as AuditService
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    U->>R: POST /api/v1/phieu_xuat/{id}/tu_choi + Bearer + body
    R->>DB: Xác minh tài khoản/role/phiên
    alt Sai xác thực/quyền/input
        R-->>U: 401 / 403 / 422
    else Hợp lệ
        R->>S: reject_issue
        S->>T: Bắt đầu transaction
        S->>P: Khóa source/phiếu/dòng; kiểm ETag/trạng thái; đổi tu_choi, lưu lý do/người xử lý
        P->>DB: SELECT FOR UPDATE/SHARE và ghi cùng session
        alt Sai ID/phân công/trạng thái/validator/phụ thuộc
            S->>T: Rollback
            S-->>U: 404 / 403 / 409; gui,duyet,tu_choi thêm 428 hoặc 412
        else Hợp lệ
            S->>A: append audit cùng session
            S->>T: Commit và flush audit
            alt Lỗi ghi/audit/commit
                T->>DB: Rollback toàn bộ
                S-->>U: 500 hoặc lỗi nghiệp vụ đã ánh xạ
            else Thành công
                S-->>U: 200 resource + ETag
            end
        end
    end
```

