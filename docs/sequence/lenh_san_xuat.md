# Sequence — lenh_san_xuat

## Lệnh sản xuất — contract v3 §9, API-045–051

Bảy endpoint được triển khai trong module `lenh_san_xuat`, qua `router.py`, `LenhSanXuatService` và `SqlAlchemyLenhSanXuatRepository`. Lệnh chỉ sinh khi gửi yêu cầu, không có POST tạo thủ công hoặc endpoint hoàn tất trực tiếp. `AuditService.append → SqlAlchemyAuditRepository.append` dùng chung session/transaction. Không endpoint nào dưới đây ghi tồn/ledger. Hoàn tất vẫn do duyệt chứng từ đầu ra hiện có.

Module sở hữu đủ `models.py` (LenhSanXuat/ChiTietLenhSanXuat), `ports.py` (LenhContext/repository/kiểm tra nhân viên) và `schemas.py` (input/output/envelope). ORM đăng ký qua `app/models.py`; yêu cầu/kế hoạch, phiếu xuất và hoàn thành dùng cùng các class này. Không có khai báo ORM lệnh trùng trong `san_xuat`.

Q đọc toàn bộ, N chỉ đọc/bắt đầu lệnh có `nhan_vien_id` của mình, A bị chặn. Thiếu/sai/hết hạn/thu hồi JWT trả 401, tài khoản khóa hoặc sai role/phạm vi trả 403, ID không tồn tại 404, input/query/header lặp sai 422.

GET chi tiết và vật tư cùng trả strong ETag từ lệnh (BOM/nhu cầu/tiến độ/ID con), trạng thái yêu cầu và snapshot vật tư đã cấp/tồn hiện tại. Khi một phần snapshot đổi, tải lại để lấy ETag mới. PATCH/actions bắt buộc If-Match: thiếu/blank 428, cũ/weak/wildcard/list 412. So sánh dưới khóa `yêu cầu → lệnh`, cùng thứ tự phiếu xuất và hoàn thành sản xuất. GET dùng khóa chia sẻ, không thay đổi trạng thái.

`du_dieu_kien_bat_dau` chỉ true khi lệnh da_gui, nguồn cho phép và đã cấp đủ, không dựa vào tồn hiện tại. Lệnh bắt đầu chuyển yêu cầu da_gui sang dang_thuc_hien, nhưng giữ cho_bo_sung_vat_tu. Hủy chỉ đổi trạng thái lệnh và ghi lý do trong audit, không tự xóa hoặc đổi chứng từ nháp/chờ duyệt liên quan. Phân công không thay đổi là no-op, không audit trùng.

| Endpoint | Ảnh PNG |
|---|---|
| `GET /api/v1/lenh_san_xuat` | [danh-sach](assets/lenh_san_xuat/lenh-01-danh-sach.png) |
| `GET /api/v1/lenh_san_xuat/{id}` | [chi-tiet](assets/lenh_san_xuat/lenh-02-chi-tiet.png) |
| `PATCH /api/v1/lenh_san_xuat/{id}` | [phan-cong](assets/lenh_san_xuat/lenh-03-phan-cong.png) |
| `GET /api/v1/lenh_san_xuat/{id}/vat_tu` | [vat-tu](assets/lenh_san_xuat/lenh-04-vat-tu.png) |
| `POST /api/v1/lenh_san_xuat/{id}/gui` | [gui](assets/lenh_san_xuat/lenh-05-gui.png) |
| `POST /api/v1/lenh_san_xuat/{id}/bat_dau` | [bat-dau](assets/lenh_san_xuat/lenh-06-bat-dau.png) |
| `POST /api/v1/lenh_san_xuat/{id}/huy` | [huy](assets/lenh_san_xuat/lenh-07-huy.png) |

## GET /api/v1/lenh_san_xuat

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: GET /api/v1/lenh_san_xuat
    R->>A: JWT, pwdv, active và role Q/N
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: LenhQuery: page, page_size, q, filters, sort, ngày địa phương
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: list_entries(actor, request_id)
            S->>P: list_orders: N chỉ thấy nhan_vien_id = JWT sub
            P->>D: COUNT + SELECT với filter/sort và ID phụ ổn định
            P->>D: Đọc nhu cầu trực tiếp, con và tổng đầu ra đã duyệt
            P-->>S: RecordPage LenhRead
            S-->>C: 200 LenhListResponse, meta phân trang, request_id
        end
    end
```

## GET /api/v1/lenh_san_xuat/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: GET /api/v1/lenh_san_xuat/{id}
    R->>A: JWT, pwdv, active và role Q/N
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: ID dương INT32, không query
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: get_entry(actor, request_id)
            S->>P: get_context(lock=false)
            P->>D: FOR SHARE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S-->>C: 200 LenhRead + strong ETag
            end
        end
    end
```

## PATCH /api/v1/lenh_san_xuat/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant U as AuditService
    participant V as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: PATCH /api/v1/lenh_san_xuat/{id}
    R->>A: JWT, pwdv, active và role Q
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: LenhPatch: chỉ nhan_vien_id int hoặc null, If-Match
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: patch_entry(actor, request_id)
            S->>T: Mở cùng transaction
            S->>P: get_context(lock=true)
            P->>D: FOR UPDATE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S->>S: So strong If-Match dưới khóa
                alt Thiếu/blank hoặc không khớp ETag
                    S-->>C: 428 hoặc 412
                else Phiên bản hiện hành
                    S->>S: Chỉ nhap, người được giao đang hoạt động và có role N
                    opt Có người được giao cần kiểm tra
                        S->>A: kiem_tra_nguoi_duoc_giao(lock=true)
                        A->>D: Nhân viên FOR SHARE, active + role N
                    end
                    alt Sai trạng thái/điều kiện hoặc người được giao không hợp lệ
                        S-->>C: 409, hoặc 404 nhân viên thiếu
                    else Đủ điều kiện
                        opt Thay đổi thực sự, không phải no-op
                        S->>P: update_order các trường được phép
                        P->>D: UPDATE + flush
                        S->>P: Đọc lại snapshot sau thay đổi
                        S->>U: append audit lệnh, trước/sau và lý do nếu hủy
                        U->>V: append
                        V->>D: INSERT LichSuThaoTac
                        end
                        S->>T: Commit
                        T->>D: COMMIT
                        S-->>C: 200 LenhRead + ETag mới
                    end
                end
            end
            opt Lỗi SQL/audit/commit trước thành công
                T->>D: ROLLBACK toàn bộ lệnh, yêu cầu và audit
                S-->>C: 409 constraint hoặc 500 lỗi nội bộ
            end
        end
    end
```

## GET /api/v1/lenh_san_xuat/{id}/vat_tu

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: GET /api/v1/lenh_san_xuat/{id}/vat_tu
    R->>A: JWT, pwdv, active và role Q/N
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: ID dương INT32, không query
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: materials(actor, request_id)
            S->>P: get_context(lock=false)
            P->>D: FOR SHARE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S->>S: Nhu cầu snapshot + tổng đã cấp từ phiếu xuất da_duyet + MatHang.so_luong_ton
                S->>S: Tính còn phải cấp, điều kiện bắt đầu
                S-->>C: 200 VatTuLenhRead + strong ETag
            end
        end
    end
```

## POST /api/v1/lenh_san_xuat/{id}/gui

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant U as AuditService
    participant V as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: POST /api/v1/lenh_san_xuat/{id}/gui
    R->>A: JWT, pwdv, active và role Q
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: Body bắt buộc {}, If-Match
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: send(actor, request_id)
            S->>T: Mở cùng transaction
            S->>P: get_context(lock=true)
            P->>D: FOR UPDATE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S->>S: So strong If-Match dưới khóa
                alt Thiếu/blank hoặc không khớp ETag
                    S-->>C: 428 hoặc 412
                else Phiên bản hiện hành
                    S->>S: Chỉ nhap, yêu cầu đã gửi/chờ bổ sung/đang làm, nhân viên N hợp lệ
                    opt Có người được giao cần kiểm tra
                        S->>A: kiem_tra_nguoi_duoc_giao(lock=true)
                        A->>D: Nhân viên FOR SHARE, active + role N
                    end
                    alt Sai trạng thái/điều kiện hoặc người được giao không hợp lệ
                        S-->>C: 409, hoặc 404 nhân viên thiếu
                    else Đủ điều kiện
                        S->>P: update_order các trường được phép
                        P->>D: UPDATE + flush
                        S->>P: Đọc lại snapshot sau thay đổi
                        S->>U: append audit lệnh, trước/sau và lý do nếu hủy
                        U->>V: append
                        V->>D: INSERT LichSuThaoTac
                        S->>T: Commit
                        T->>D: COMMIT
                        S-->>C: 200 da_gui + ETag mới
                    end
                end
            end
            opt Lỗi SQL/audit/commit trước thành công
                T->>D: ROLLBACK toàn bộ lệnh, yêu cầu và audit
                S-->>C: 409 constraint hoặc 500 lỗi nội bộ
            end
        end
    end
```

## POST /api/v1/lenh_san_xuat/{id}/bat_dau

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant U as AuditService
    participant V as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: POST /api/v1/lenh_san_xuat/{id}/bat_dau
    R->>A: JWT, pwdv, active và role N được giao
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: Body bắt buộc {}, If-Match
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: start(actor, request_id)
            S->>T: Mở cùng transaction
            S->>P: get_context(lock=true)
            P->>D: FOR UPDATE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S->>S: So strong If-Match dưới khóa
                alt Thiếu/blank hoặc không khớp ETag
                    S-->>C: 428 hoặc 412
                else Phiên bản hiện hành
                    S->>S: Chỉ da_gui và đúng N được giao, mọi vật tư đã cấp đủ qua phiếu xuất da_duyet
                    alt Sai trạng thái/điều kiện hoặc người được giao không hợp lệ
                        S-->>C: 409, hoặc 404 nhân viên thiếu
                    else Đủ điều kiện
                        S->>P: update_order các trường được phép
                        P->>D: UPDATE + flush
                        S->>P: start_request nếu nguồn da_gui
                        P->>D: UPDATE yêu cầu sang dang_thuc_hien
                        opt Trạng thái yêu cầu đổi
                            S->>U: append audit yêu cầu
                            U->>V: append
                            V->>D: INSERT LichSuThaoTac
                        end
                        S->>P: Đọc lại snapshot sau thay đổi
                        S->>U: append audit lệnh, trước/sau và lý do nếu hủy
                        U->>V: append
                        V->>D: INSERT LichSuThaoTac
                        S->>T: Commit
                        T->>D: COMMIT
                        S-->>C: 200 dang_thuc_hien, started_at UTC, ETag mới
                    end
                end
            end
            opt Lỗi SQL/audit/commit trước thành công
                T->>D: ROLLBACK toàn bộ lệnh, yêu cầu và audit
                S-->>C: 409 constraint hoặc 500 lỗi nội bộ
            end
        end
    end
```

## POST /api/v1/lenh_san_xuat/{id}/huy

```mermaid
sequenceDiagram
    actor C as Client
    participant R as lenh_san_xuat.router
    participant A as AuthService / NhanVienService
    participant S as LenhSanXuatService
    participant P as SqlAlchemyLenhSanXuatRepository
    participant U as AuditService
    participant V as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    Note over R: Input/output từ lenh_san_xuat.schemas
    Note over S,P: Giao tiếp qua lenh_san_xuat.ports
    Note over P,D: ORM thuộc lenh_san_xuat.models
    C->>R: POST /api/v1/lenh_san_xuat/{id}/huy
    R->>A: JWT, pwdv, active và role Q
    A->>D: Đọc nhân viên và vai trò hiện hành
    alt Token thiếu/sai/hết hạn hoặc role/tài khoản không hợp lệ
        R-->>C: 401 hoặc 403
    else Xác thực hợp lệ
        R->>R: LyDoInput không rỗng, If-Match
        alt Schema/query/header không hợp lệ
            R-->>C: 422 du_lieu_khong_hop_le
        else Đầu vào hợp lệ
            R->>S: cancel(actor, request_id)
            S->>T: Mở cùng transaction
            S->>P: get_context(lock=true)
            P->>D: FOR UPDATE yêu cầu rồi lệnh, đọc snapshot
            P-->>S: LenhContext
            alt Không tồn tại hoặc N ngoài phạm vi
                S-->>C: 404 hoặc 403
            else Lệnh hợp lệ
                S->>S: So strong If-Match dưới khóa
                alt Thiếu/blank hoặc không khớp ETag
                    S-->>C: 428 hoặc 412
                else Phiên bản hiện hành
                    S->>S: Chưa đóng/hủy, không vật tư/đầu ra ghi sổ, không con hoạt động
                    S->>P: has_posted_dependency + has_active_children
                    P->>D: Đọc phiếu đã duyệt/ledger và con chưa hoàn thành/hủy
                    alt Sai trạng thái/điều kiện hoặc người được giao không hợp lệ
                        S-->>C: 409, hoặc 404 nhân viên thiếu
                    else Đủ điều kiện
                        S->>P: update_order các trường được phép
                        P->>D: UPDATE + flush
                        S->>P: Đọc lại snapshot sau thay đổi
                        S->>U: append audit lệnh, trước/sau và lý do nếu hủy
                        U->>V: append
                        V->>D: INSERT LichSuThaoTac
                        S->>T: Commit
                        T->>D: COMMIT
                        S-->>C: 200 da_huy + ETag mới
                    end
                end
            end
            opt Lỗi SQL/audit/commit trước thành công
                T->>D: ROLLBACK toàn bộ lệnh, yêu cầu và audit
                S-->>C: 409 constraint hoặc 500 lỗi nội bộ
            end
        end
    end
```
