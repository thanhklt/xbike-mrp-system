# Sequence phiếu xuất v4 — UC-34 đến UC-40

Nguồn: [spec](../../specs/use_cases/goods_issue/README.md),
[plan và kết quả](../../specs/use_cases/goods_issue/PLAN.md),
`phieu_xuat/{router,schemas,service,ports,repository,models}.py`,
`inventory/{ports,repository}.py`, `audit/{service,repository,schemas,models}.py`,
`dependencies.py`, `core/{request_context,sqlalchemy_transaction}.py` và `init.sql` v4.

| Endpoint hiện có | UC | PNG |
|---|---|---|
| GET `/api/v1/phieu_xuat` | UC-40 | [Danh sách](assets/phieu_xuat/01-danh-sach.png) |
| GET `/api/v1/phieu_xuat/{id}` | UC-40 | [Chi tiết](assets/phieu_xuat/02-chi-tiet.png) |
| POST `/api/v1/phieu_xuat` | UC-34/37 | [Tạo nháp](assets/phieu_xuat/03-tao-nhap.png) |
| POST `/api/v1/phieu_xuat/{id}/gui` | UC-34/37 | [Gửi hoặc gửi lại](assets/phieu_xuat/06-gui.png) |
| POST `/api/v1/phieu_xuat/{id}/duyet` | UC-35/38 | [Duyệt](assets/phieu_xuat/07-duyet.png) |
| POST `/api/v1/phieu_xuat/{id}/tu_choi` | UC-36/39 | [Từ chối](assets/phieu_xuat/08-tu-choi.png) |

Chỉ sáu endpoint trên được đăng ký. PATCH/DELETE `/{id}` trả 405; `/{id}/ve_nhap`
và các alias xuất cũ không có route. Không tạo route `gui_lai`: gửi lại dùng `/gui`.
QLK (`quan_ly`) đọc danh sách/chi tiết, duyệt, từ chối. NV (`nhan_vien`) đọc/lập/gửi
phiếu thuộc yêu cầu hiện được giao. QTV không được vào các endpoint này. JWT được
kiểm tra chữ ký/hạn, tài khoản, hash phiên mật khẩu và vai trò hiện tại từ DB.
Phần auth hiện hữu chưa được nâng sang `phien_ban_dang_nhap` v4 trong tác vụ này.

Thành công dùng `{data,meta}`; lỗi nghiệp vụ `{error,meta}` có `request_id`. POST tạo
201 + Location + ETag; các thao tác và GET chi tiết 200 + ETag. Tiền là integer VND
trong BIGINT, giá/tổng null trước duyệt. Thời gian UTC với Z. ETag là SHA-256 JSON
canonical của header và chi tiết sắp theo ID, gồm metadata/phien_ban, không có request_id.
If-Match bắt buộc với gửi/duyệt/từ chối: thiếu/trắng 428; weak/wildcard/nhiều header/
nhiều tag/sai định dạng 412; tag cũ 412, ngoại lệ replay duyệt bên dưới.
Sơ đồ biểu diễn nhóm lỗi, không cam kết ưu tiên giữa auth và validation khi cùng sai.

## GET /api/v1/phieu_xuat

QLK-only. Bộ lọc AND: `q` chứa mã (không phân biệt hoa thường, `%`/`_` là ký tự thường),
`loai_phieu`, `trang_thai`, `nhan_vien_id`, `yeu_cau_san_xuat_id`, `tu_ngay`, `den_ngay`.
Ngày theo Asia/Ho_Chi_Minh, hai đầu bao gồm cả ngày. Page 1, size 20, tối đa 100.
Sort whitelist `id`, `created_at`, `ma_phieu_xuat`, có tiền tố `-`; mặc định
`-created_at`, ID tăng dần khi trùng. Không có lọc theo lệnh, không ETag danh sách.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client QLK
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_xuat + JWT + query
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Read current employee and role
    break Missing / invalid / revoked credentials
        R-->>C: 401
    end
    break Locked account or role other than quan_ly
        R-->>C: 403
    end
    R->>R: Validate query, reject repeated keys and GET body
    break Invalid / unknown filters, range or pagination
        R-->>C: 422
    end
    R->>S: list_issues(query, actor, request_id)
    S->>S: Require quan_ly
    S->>P: begin_read_snapshot
    P->>DB: Roll back auth read TX, start REPEATABLE READ READ ONLY
    S->>P: list_issues
    P->>DB: COUNT with AND filters
    P->>DB: Page headers sorted with ID tie-break
    opt Nonempty page
        P->>DB: One query for all page lines ordered by ID
    end
    P-->>S: RecordPage of detached read DTOs
    S-->>R: data + pagination + request_id
    R-->>C: 200, including valid empty page
    Note over P,DB: No INSERT / UPDATE / DELETE or row locks, session close ends read TX
```

## GET /api/v1/phieu_xuat/{id}

Missing ID hoặc lớn hơn PostgreSQL INTEGER trả 404; không đưa ID quá dải vào asyncpg.
NV ngoài phạm vi nhận 403. Không nhận query hoặc GET body.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client QLK / NV
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant DB as PostgreSQL
    C->>R: GET /api/v1/phieu_xuat/{id} + JWT
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current account, role, password version
    break Invalid credentials / locked or forbidden role
        R-->>C: 401 / 403
    end
    R->>R: Positive ID, no query or body
    break Structural validation failure
        R-->>C: 422
    end
    R->>S: get_issue(id, actor, request_id)
    S->>P: begin_read_snapshot
    P->>DB: REPEATABLE READ READ ONLY after releasing auth read TX
    S->>P: get_issue(lock=false)
    P->>DB: Read PhieuXuat and ordered ChiTietPhieuXuat
    break Not found / ID outside INTEGER range
        S-->>C: 404
    end
    opt NV
        S->>P: assigned_to(record, employee_id)
        P->>DB: Read current YeuCauSanXuat assignment in same snapshot
        break Assigned to another employee
            S-->>C: 403
        end
    end
    S->>S: Build canonical resource ETag
    S-->>R: resource and ETag
    R-->>C: 200 data/meta + strong ETag
    Note over S,DB: Same snapshot for representation, assignment and validator, no writes
```

## POST /api/v1/phieu_xuat

Input chỉ `{loai_phieu, yeu_cau_san_xuat_id}`. Loại `xuat_linh_kien` hoặc
`xuat_thanh_pham`. Source phải `dang_thuc_hien`, giao đúng NV. LK lấy đúng đủ
NhuCauLinhKien đã chốt, cần lượng sản xuất > 0. TP chỉ `xuat_giao`, lượng toàn bộ yêu
cầu; nếu cần sản xuất thì chứng từ hoàn thành của nguồn phải `da_duyet`. Không tính
lại BOM; TP đã ngừng vẫn được hoàn tất yêu cầu đã gửi hợp lệ (UC-12 R7).

```mermaid
sequenceDiagram
    autonumber
    actor C as Assigned NV
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_xuat + JWT + source/type
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current employee and role
    break Invalid credentials / not active NV
        R-->>C: 401 / 403
    end
    R->>R: Strict positive source ID, type, forbid extras and query
    break Invalid input / extra fields
        R-->>C: 422
    end
    R->>S: create_issue
    S->>T: Enter shared session transaction
    S->>P: lock_source(type, request_id)
    P->>DB: YCSX FOR UPDATE, frozen demand and completion projection
    break Source missing / NV outside assignment
        S->>T: Roll back
        S-->>C: 404 / 403
    end
    S->>S: Check source state, type and completion prerequisites
    S->>P: lock_parts, exists_for_source
    P->>DB: Item type snapshot FOR SHARE, existing issue lookup
    break Invalid source/demand or duplicate request/type
        S->>T: Roll back
        S-->>C: 409
    end
    S->>P: add(payload, actor_id, frozen demand)
    P->>DB: Advisory code lock, monthly VN code including audit history
    P->>DB: INSERT Identity header and exact lines with null prices
    S->>AU: append tao, state/snapshot after
    AU->>AR: append
    AR->>AR: session.add LichSuThaoTac
    S->>T: Commit
    T->>DB: Flush audit and COMMIT all writes
    alt Success
        S-->>R: Draft resource and ETag
        R-->>C: 201 + Location + ETag + data/meta
    else Constraint / unexpected write or commit error
        T->>DB: ROLLBACK
        R-->>C: 409 / safe 500
    end
    Note over S,DB: No stock, reservation or ledger writes during creation
```

## POST /api/v1/phieu_xuat/{id}/gui

Body bắt buộc `{}`. NV đúng nguồn gửi nháp hoặc gửi lại từ chối trực tiếp sang
`cho_duyet`; giữ nguyên ID/chi tiết. Tăng phiên bản, cập nhật gui_at/updated_at,
xóa metadata xử lý/lý do trên resource khi gửi lại; lý do cũ vẫn trong audit.

```mermaid
sequenceDiagram
    autonumber
    actor C as Assigned NV
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_xuat/{id}/gui + JWT + If-Match + empty object
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current account and role
    break Invalid credentials / not active NV
        R-->>C: 401 / 403
    end
    R->>R: Validate ID, required empty body, no query, preserve all If-Match headers
    break Invalid structure
        R-->>C: 422
    end
    R->>S: submit_issue
    S->>T: Enter transaction
    S->>P: lock_context
    P->>DB: Lock YCSX then PhieuXuat, ordered lines, completion if present
    break Missing issue / wrong assignment
        S->>T: Roll back
        S-->>C: 404 / 403
    end
    S->>S: Validate one strong If-Match and compare under lock
    break Missing / malformed / stale validator
        S->>T: Roll back
        S-->>C: 428 / 412
    end
    S->>P: lock_parts
    P->>DB: Read item types FOR SHARE
    S->>S: Source eligible, nhap or tu_choi, exact frozen lines and null prices
    break Invalid source / workflow / demand
        S->>T: Roll back
        S-->>C: 409
    end
    S->>P: change_state cho_duyet, timestamps, version +1, clear processing metadata
    P->>DB: UPDATE PhieuXuat
    S->>AU: append gui or gui_lai, before/after state and snapshots
    AU->>AR: append
    AR->>AR: session.add
    S->>T: Commit
    T->>DB: Flush audit and COMMIT, any error ROLLBACK
    R-->>C: 200 + resource ETag, or 409 / safe 500
    Note over S,DB: Stock, holds, ledger unchanged, no separate gui_lai route
```

## POST /api/v1/phieu_xuat/{id}/duyet

Body bắt buộc `{}`, QLK-only. Thứ tự khóa: nguồn YCSX → phiếu/chi tiết → chứng từ
hoàn thành nếu có → MatHang tăng dần ID → GiuHang tăng dần item/ID. Nhu cầu đã chốt
bất biến; chứng từ hoàn thành đã duyệt bất biến. Service kiểm tra lượng đúng đủ,
giữ nguồn/loại/lượng/chứng từ đúng, tổng giữ khớp các khoản đang giữ, tồn khớp tổng
ledger, giá integer và không tràn BIGINT. Không dùng cache để quyết định giá/tồn.

```mermaid
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant I as SqlAlchemyInventoryRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_xuat/{id}/duyet + JWT + If-Match + empty object
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current account, role and credential version
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Validate ID, empty body, no query, retain physical If-Match values
    break Invalid structure
        R-->>C: 422
    end
    R->>S: approve
    S->>T: Enter shared transaction
    S->>P: lock_context
    P->>DB: YCSX FOR UPDATE then issue/lines and completion lock
    break Missing resource
        S->>T: Roll back
        S-->>C: 404
    end
    S->>S: Require one quoted SHA-256 validator even for replay
    break Missing / malformed, weak, wildcard or multiple validators
        S->>T: Roll back
        S-->>C: 428 / 412
    end
    alt Already da_duyet
        S->>P: postings(id)
        P->>DB: Read existing ledger rows
        S->>S: Check every line has matching item, kind and negative quantity
        alt Complete posting
            R-->>C: 200 current resource, old ledger IDs, replay=true, current ETag
        else Incomplete or inconsistent posting
            S-->>C: 409, no repair
        end
        Note over S,DB: Old well-formed tag accepted, no stock/price/source/audit writes
    else First approval
        S->>S: Compare current ETag, require pending state and eligible source
        break Stale validator / invalid workflow or frozen demand
            S->>T: Roll back
            S-->>C: 412 / 409
        end
        S->>P: postings(id), require no existing posting
        P->>DB: Read ledger for issue
        S->>I: lock_issue_stock(source, ordered item IDs)
        I->>DB: MatHang FOR UPDATE then active GiuHang FOR UPDATE, ledger SUM
        I-->>S: Detached stock, prices, all active reservations
        S->>S: Validate holds, stock/ledger, source quantities, price and overflow
        break Invalid holds / insufficient or inconsistent stock / money
            S->>T: Roll back
            S-->>C: 409
        end
        S->>P: freeze_prices(record, prices, actor, timestamp)
        P->>DB: UPDATE lines before parent becomes immutable
        P->>DB: UPDATE parent da_duyet, total, processor/time, version +1
        S->>I: issue_stock(validated lines and own reservations)
        I->>DB: UPDATE stock and held together for each item
        I->>DB: UPDATE own GiuHang to da_xuat with issue/end time
        I->>DB: INSERT negative GiaoDichKho with so_luong_ton_sau and unique line FK
        opt Finished goods
            S->>P: update_progress(source, timestamp)
            P->>DB: UPDATE YCSX hoan_thanh, completed_at, updated_at, version +1
            S->>AU: append source hoan_tat before/after
            AU->>AR: append, session.add
        end
        S->>AU: append issue duyet before/after
        AU->>AR: append, session.add
        S->>T: Commit once
        T->>DB: Flush audit and COMMIT
        alt Success
            R-->>C: 200 resource, ledger IDs, replay=false, ETag
        else Failure at any write, audit or commit
            T->>DB: ROLLBACK prices, state, stock, holds, ledger, progress and audit
            R-->>C: 409 constraint / safe 500
        end
    end
```

LK không tự bắt đầu sản xuất. TP đóng yêu cầu chỉ khi duyệt thành công, thêm audit
`yeu_cau_san_xuat/hoan_tat`. Replay không kiểm tra lại giá/tồn hiện tại hay ghi audit.
NOTIFY mặt hàng do trigger gửi sau commit; không bảo đảm cache module khác cập nhật
đồng bộ tức thì. Hai session thật, rollback từng bước và replay có test PostgreSQL.

## POST /api/v1/phieu_xuat/{id}/tu_choi

QLK, body `{ly_do: string}` không trắng. Chỉ `cho_duyet` → `tu_choi` khi nguồn đang
thực hiện; lưu processor/time/reason, updated_at, phien_ban +1. Không đóng nguồn TP.

```mermaid
sequenceDiagram
    autonumber
    actor C as QLK
    participant R as phieu_xuat.router / dependencies
    participant A as AuthService / NhanVienService
    participant N as SqlAlchemyNhanVienRepository
    participant S as PhieuXuatService
    participant P as SqlAlchemyPhieuXuatRepository
    participant AU as AuditService
    participant AR as SqlAlchemyAuditRepository
    participant T as SqlAlchemyTransaction
    participant DB as PostgreSQL
    C->>R: POST /api/v1/phieu_xuat/{id}/tu_choi + JWT + If-Match + reason
    R->>A: current_payload / get_auth_identity
    A->>N: get_credentials_by_id
    N->>DB: Current employee and role
    break Invalid credentials / not active QLK
        R-->>C: 401 / 403
    end
    R->>R: Validate ID, strip nonempty reason, no extra fields/query
    break Missing or blank reason / invalid structure
        R-->>C: 422
    end
    R->>S: reject_issue
    S->>T: Enter transaction
    S->>P: lock_context
    P->>DB: YCSX then issue/lines and completion if present
    break Missing issue
        S->>T: Roll back
        S-->>C: 404
    end
    S->>S: Validate one strong If-Match and compare under lock
    break Missing / invalid / stale tag
        S->>T: Roll back
        S-->>C: 428 / 412
    end
    S->>S: Require cho_duyet and source dang_thuc_hien
    break Invalid workflow
        S->>T: Roll back
        S-->>C: 409
    end
    S->>P: change_state tu_choi, reason, processor/time, version +1
    P->>DB: UPDATE PhieuXuat
    S->>AU: append tu_choi with reason and state/snapshots
    AU->>AR: append
    AR->>AR: session.add
    S->>T: Commit
    T->>DB: Flush audit and COMMIT, any failure ROLLBACK
    R-->>C: 200 + resource ETag, or 409 / safe 500
    Note over S,DB: Stock, reservations, ledger and source status unchanged
```

## Port nội bộ hủy yêu cầu — không phải endpoint

`YeuCauSanXuatService → PhieuXuatService → SqlAlchemyPhieuXuatRepository`:

- `co_phieu_da_ghi_so(yeu_cau_id)` gọi `lock_by_sources(yeu_cau_id)`; khóa mọi phiếu
  của yêu cầu theo id bằng `FOR UPDATE`, có `da_duyet` thì chặn hủy.
- `huy_phieu_chua_ghi_so(yeu_cau_id, ly_do, actor_id)` kiểm lại R2 trên các phiếu đã
  khóa; Nháp xóa chi tiết rồi header và audit `xoa_nhap`; Chờ duyệt chuyển
  `tu_choi`, ghi người/thời điểm/phiên bản, `ly_do_tu_choi = "Yêu cầu đã hủy"`,
  audit `tu_choi`. Audit lưu lý do truyền vào và snapshot trước/sau. UC-28 truyền
  lý do `Yêu cầu đã hủy`; lý do QLK nhập thuộc lịch sử yêu cầu. Giữ phiếu `tu_choi`.
- `phieu_cua_yeu_cau(yeu_cau_id)` chỉ SELECT id, mã, loại, trạng thái theo id,
  không khóa, không ghi; phục vụ GET xem trước và snapshot tác động khi hủy.
- `tong_da_xuat_thanh_pham(yeu_cau_ids)` giữ nguyên.

Đã bỏ `lenh_ids` khỏi hai hàm hủy/kiểm tra và `lock_by_sources`; không truy vấn
bảng lệnh. Caller khóa yêu cầu trước, sở hữu transaction và trả giữ hàng; thứ tự
khóa yêu cầu → phiếu → MatHang → GiuHang. Cổng dùng chung session, không commit
riêng; lỗi lịch sử/ghi dữ liệu rollback cả phiếu, giữ hàng, yêu cầu và audit.
Luồng endpoint hủy v4 được mô tả trong `san_xuat.md`. Kiểm thử ASGI/service và SQL
không thay thế nghiệm thu E2E hay kiểm tranh chấp PostgreSQL thật.
