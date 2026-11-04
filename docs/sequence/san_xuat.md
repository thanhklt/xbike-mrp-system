# Sequence — san_xuat

Triển khai contract v3 §8 (API-036–044); quyết định D-SX-01–19 tại `docs/DECISION.md`.
`Q = quan_ly`, `N = nhan_vien`. Admin bị chặn ở cả 9 endpoint. JWT được kiểm tra
bằng trạng thái tài khoản, vai trò và phiên bản mật khẩu hiện hành trong DB.
N chỉ đọc/tính thử yêu cầu có `nhan_vien_duoc_giao_id = sub`; ID không tồn tại trả
404 trước khi kiểm tra phạm vi, ngoài phạm vi trả 403.

Mọi lỗi dùng `{error: {code, message, details}, meta: {request_id}}`.
Body không hỗ trợ trường lạ; ID path phải dương (422), ID vượt INT32 trả 404.
GET chi tiết, POST tạo, PATCH, gửi và hủy trả strong ETag từ toàn bộ `YeuCauRead`,
gồm tổng lượng xuất và ID lệnh. PATCH/DELETE/gửi/hủy so `If-Match` dưới khóa yêu cầu:
thiếu/blank 428 `thieu_if_match`; cũ/weak/`*` 412 `du_lieu_da_thay_doi`.
Mọi ghi nghiệp vụ và audit dùng cùng session/transaction; lỗi rollback toàn bộ.
Chín endpoint yêu cầu sản xuất dưới đây không ghi kho, giữ chỗ hoặc tạo ledger.

## GET /api/v1/yeu_cau_san_xuat

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant D as PostgreSQL
    C->>R: GET (page, page_size, q, filters, sort)
    R->>A: JWT + danh tính hiện hành + role Q/N
    A->>D: Đọc nhân viên và vai trò
    alt Chưa xác thực / sai token / tài khoản bị khóa / ngoài role
        R-->>C: 401 / 403
    else Hợp lệ
        R->>R: Kiểm tra query, enum, ngày, sort, query lặp
        alt Query không hợp lệ hoặc trường lạ
            R-->>C: 422 du_lieu_khong_hop_le
        else Hợp lệ
            R->>S: list_entries(params, actor, request_id)
            S->>P: list_entries(params, N.id hoặc null với Q)
            P->>D: COUNT + SELECT yêu cầu trong phạm vi và trang
            P->>D: SELECT ID lệnh cho các yêu cầu trên trang
            S->>X: tong_da_xuat_thanh_pham(ids)
            X->>D: SUM dòng xuất thành phẩm da_duyet, GROUP BY yêu cầu
            S-->>C: 200 data[] + meta phân trang
        end
    end
```

Filter `q` tìm mã yêu cầu bằng ILIKE tham số hóa, escape ký tự wildcard. Bộ lọc
`mat_hang_id`, `trang_thai`, `nhan_vien_duoc_giao_id`, `tu_ngay`, `den_ngay` kết hợp
với phạm vi N. Ngày địa phương Asia/Ho_Chi_Minh chuyển sang khoảng UTC nửa mở.
Sort mặc định `-created_at`, whitelist `id`, `created_at`, `ma_yeu_cau_san_xuat`,
luôn thêm ID tăng dần. Meta có `request_id`, `page`, `page_size`, `total`, `total_pages`.
Projection Q/N cùng các field, khác phạm vi dòng. Không audit, không ETag danh sách.

## GET /api/v1/yeu_cau_san_xuat/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant D as PostgreSQL
    C->>R: GET id
    R->>A: Xác thực + role Q/N
    A->>D: Đọc danh tính hiện hành
    alt Xác thực / role thất bại
        R-->>C: 401 / 403
    else Cho phép
        R->>R: ID dương, không query (sai: 422)
        R->>S: get_entry(id, actor, request_id)
        S->>P: get_by_id(id), trừ ID vượt INT32
        P->>D: SELECT yêu cầu + ID lệnh
        alt Vượt INT32 / không tồn tại
            S-->>C: 404 khong_tim_thay
        else N ngoài phạm vi
            S-->>C: 403 khong_co_quyen
        else Trong phạm vi
            S->>X: tong_da_xuat_thanh_pham([id])
            X->>D: SUM xuất thành phẩm da_duyet
            S->>S: Tính còn phải xuất + ETag canonical
            S-->>C: 200 YeuCauRead + meta + ETag
        end
    end
```

Không audit. `so_luong_con_phai_xuat = max(so_luong - so_luong_da_xuat, 0)`.

## POST /api/v1/yeu_cau_san_xuat

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant M as MatHangAvailabilityService / repository
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant L as AuditService / repository
    participant D as PostgreSQL
    C->>R: POST YeuCauCreate
    R->>A: Xác thực + role Q (sai: 401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: Validate body, extra forbid, không query (sai: 422)
    R->>S: create_entry(payload, actor, request_id)
    S->>M: read_items([mat_hang_id], lock=true)
    M->>D: SELECT MatHang FOR SHARE, kiểm tra tồn tại/active
    alt Mặt hàng không tồn tại / ngừng hoạt động / không là thành phẩm
        S-->>C: 404 / 409 mat_hang_ngung_hoat_dong / 422
    else Thành phẩm hợp lệ
        opt Có người phụ trách
            S->>A: kiem_tra_nguoi_duoc_giao(id, lock=true)
            A->>D: SELECT NhanVien FOR SHARE + vai trò
            Note over A,D: Không tồn tại: 404; bị khóa/sai vai trò: 409 nguoi_duoc_giao_khong_hop_le
        end
        S->>P: add(payload, actor.id)
        P->>D: nextval identity + tháng Asia/Ho_Chi_Minh
        P->>D: INSERT YeuCauSanXuat nhap, mã YCSX, người tạo từ JWT
        S->>L: append tao (dữ liệu sau)
        L->>D: Thêm audit trong cùng session
        S->>D: COMMIT qua SqlAlchemyTransaction
        S-->>C: 201 YeuCauRead + meta + ETag + Location
    end
    Note over S,D: Mọi lỗi ghi/audit: rollback cả yêu cầu và audit
```

Người phụ trách tùy chọn, nullable. Không cần If-Match. Mã có phần số bằng ID 6 chữ số,
không reset theo tháng; giới hạn PoC 999999. `Location` trỏ GET chi tiết vừa tạo.

## PATCH /api/v1/yeu_cau_san_xuat/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant M as MatHangAvailabilityService / repository
    participant L as AuditService / repository
    participant D as PostgreSQL
    C->>R: PATCH YeuCauPatch + If-Match
    R->>A: Xác thực + role Q (sai: 401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: Không query; body không rỗng, null/extra hợp lệ (sai: 422)
    R->>S: patch_entry
    S->>P: get_for_update(id)
    P->>D: SELECT yêu cầu FOR UPDATE + ID lệnh
    Note over S,P: ID vượt INT32/không tồn tại: 404
    S->>X: Đọc tổng xuất thành phẩm da_duyet cho ETag
    X->>D: SELECT SUM dòng xuất
    S->>S: So If-Match (thiếu: 428, không khớp: 412)
    alt Không còn nhap
        S-->>C: 409 trang_thai_khong_hop_le, rollback
    else Nháp
        S->>M: Kiểm tra thành phẩm hiện hành, lock=true
        M->>D: FOR SHARE, tồn tại/active/loại (404/409/422)
        opt Người phụ trách sau PATCH khác null
            S->>A: kiem_tra_nguoi_duoc_giao(lock=true)
            A->>D: FOR SHARE, trạng thái/vai trò (404/409)
        end
        S->>P: update(chỉ field được gửi)
        P->>D: UPDATE yêu cầu
        S->>L: append sua (trước/sau)
        L->>D: INSERT audit
        S->>D: COMMIT; mọi lỗi rollback toàn bộ
        S-->>C: 200 YeuCauRead + meta + ETag mới
    end
```

Chỉ nhận `mat_hang_id`, `so_luong`, `nhan_vien_duoc_giao_id`. Hai trường đầu không nhận
null; trường phụ trách nhận null. Bỏ qua field giữ nguyên giá trị.

## DELETE /api/v1/yeu_cau_san_xuat/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant L as AuditService / repository
    participant D as PostgreSQL
    C->>R: DELETE id + If-Match
    R->>A: Xác thực + role Q (sai: 401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: ID dương, không query (sai: 422)
    R->>S: delete_entry
    S->>P: get_for_update(id)
    P->>D: FOR UPDATE yêu cầu + ID lệnh (không có: 404)
    S->>X: Tổng xuất thành phẩm để tạo ETag
    X->>D: SUM các dòng da_duyet
    S->>S: If-Match (thiếu: 428, cũ/weak/*: 412)
    alt Không nhap
        S-->>C: 409 trang_thai_khong_hop_le
    else Nháp
        S->>P: has_dependencies(id)
        P->>D: EXISTS LenhSanXuat hoặc PhieuXuat
        alt Có phụ thuộc
            S-->>C: 409 dang_duoc_tham_chieu
        else Không phụ thuộc
            S->>P: delete(id)
            P->>D: DELETE YeuCauSanXuat
            S->>L: append xoa_nhap (dữ liệu trước)
            L->>D: INSERT audit
            S->>D: COMMIT; lỗi rollback toàn bộ
            R-->>C: 204, không body
        end
    end
```

Xóa cứng yêu cầu nháp; không xóa nhân viên/mặt hàng, không cascade sang chứng từ khác.

## POST /api/v1/yeu_cau_san_xuat/{id}/tinh_ke_hoach

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant B as BomPlanningReader / repository
    participant M as MatHangAvailabilityService / repository
    participant X as PhieuXuatSanXuatService / repository
    participant D as PostgreSQL
    C->>R: POST body rỗng JSON
    R->>A: Xác thực + role Q/N (sai: 401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: ID/body/query validation (sai: 422)
    R->>S: tinh_ke_hoach
    S->>P: get_by_id + ID lệnh (không có/vượt INT32: 404)
    P->>D: SELECT yêu cầu
    S->>S: Phạm vi N (ngoài phạm vi: 403)
    S->>X: Đọc tiến độ yêu cầu
    X->>D: SUM xuất thành phẩm da_duyet
    alt Không ở nhap
        S-->>C: 409 trang_thai_khong_hop_le
    else Nháp
        S->>B: active_graph()
        B->>D: SELECT BOM active + chi tiết theo ID
        S->>M: read_items(mọi ID đi tới được, lock=false)
        M->>D: SELECT trực tiếp DB, không cache (thiếu ID: 404, inactive: 409)
        S->>S: calculate_plan BFS, tồn dùng chung; chu trình: 409 bom_co_chu_trinh
        S->>A: Kiểm tra người phụ trách, lock=false
        A->>D: SELECT nhân viên/vai trò
        S->>S: Tính du_dieu_kien_gui; ký JWT aud kế hoạch, TTL 10 phút
        S-->>C: 200 KeHoachPreview + meta
    end
```

Không If-Match, không khóa, không ghi/audit. Người phụ trách null/không còn hợp lệ hoặc
thiếu BOM làm `du_dieu_kien_gui=false`; thiếu NVL chỉ bật `thieu_vat_tu`.
Đủ thành phẩm trả hai mảng `lenh_du_kien`, `vat_tu` rỗng. BTP có sẵn dùng một lần giữa
các nhánh; chỉ phần thiếu sinh lệnh con. Nhu cầu cha vẫn là toàn bộ nhu cầu trực tiếp.
`vat_tu` gồm NVL/linh kiện cần lấy và phần BTP lấy từ tồn. Nhu cầu trực tiếp vượt INT32
trả 422 thay vì ghi một kế hoạch không thể lưu. Token không dùng làm access token.

## POST /api/v1/yeu_cau_san_xuat/{id}/gui

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant B as BomPlanningReader / repository
    participant M as MatHangAvailabilityService / repository
    participant L as AuditService / repository
    participant D as PostgreSQL
    C->>R: POST ke_hoach_token + If-Match
    R->>A: Xác thực + role Q (sai: 401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: Validate ID, token không rỗng, không query/extra (422)
    R->>S: gui
    S->>P: get_for_update(id)
    P->>D: FOR UPDATE yêu cầu, ID lệnh (không có/vượt INT32: 404)
    S->>X: Đọc tiến độ tạo ETag
    X->>D: SUM xuất thành phẩm đã duyệt
    S->>S: If-Match (428/412), phải nhap (409)
    S->>A: kiem_tra_nguoi_duoc_giao(lock=true)
    A->>D: FOR SHARE nhân viên, kiểm tra hoạt động/vai trò
    Note over S,A: Null/thiếu/sai phụ trách: 409 nguoi_duoc_giao_khong_hop_le
    S->>B: lock_graph(), active_graph()
    B->>D: pg_advisory_xact_lock(20261020,2), SELECT graph active
    S->>M: read_items(mọi ID đi tới được, lock=true)
    M->>D: FOR SHARE theo ID; thiếu: 404, inactive: 409
    S->>S: Tính lại BFS + so token/kết quả canonical
    alt Token sai/hết hạn/khác yêu cầu hoặc snapshot thay đổi
        S-->>C: 409 ke_hoach_da_thay_doi; rollback
    else Snapshot khớp nhưng thiếu BOM
        S-->>C: 409 thieu_bom; rollback
    else Hợp lệ
        S->>P: add_lenh_tree (cha trước con)
        P->>D: Cấp ID/mã LSX; INSERT lệnh nhap và nhu cầu trực tiếp
        Note over P,D: nhan_vien_id null; đủ TP thì không INSERT lệnh
        S->>P: update trạng thái yêu cầu
        P->>D: cho_bo_sung_vat_tu nếu thiếu, ngược lại da_gui
        S->>L: append gui cho yêu cầu + tao từng lệnh
        L->>D: INSERT audit cùng transaction
        S->>D: COMMIT; lỗi ghi/audit rollback toàn bộ
        S-->>C: 200 data.yeu_cau + data.ke_hoach + meta + ETag
    end
```

Không giữ chỗ hoặc thay số dư. Lệnh lưu `bom_id` và snapshot nhu cầu; đọc lại không
tính theo BOM/tồn mới. Người thực hiện của từng lệnh được giao ở tác vụ endpoint lệnh sau.

## GET /api/v1/yeu_cau_san_xuat/{id}/ke_hoach

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant D as PostgreSQL
    C->>R: GET id/ke_hoach
    R->>A: Xác thực + role Q/N (401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: ID dương, không query (sai: 422)
    R->>S: ke_hoach
    S->>P: get_by_id(id)
    P->>D: SELECT yêu cầu + ID lệnh (không có/vượt INT32: 404)
    S->>S: Phạm vi N (ngoài phạm vi: 403)
    S->>X: Đọc tiến độ yêu cầu
    X->>D: SUM xuất thành phẩm da_duyet
    alt Yêu cầu còn nhap
        S-->>C: 409 trang_thai_khong_hop_le
    else Đã gửi, kể cả da_huy
        S->>P: lenh_cua_yeu_cau(lock=false)
        P->>D: SELECT lệnh + snapshot chi tiết theo ID
        P->>D: GROUP BY tổng hoàn thành từ chứng từ da_duyet
        P->>P: Tính còn phải hoàn thành và ID lệnh con
        S-->>C: 200 KeHoachRead + meta
    end
```

Không audit, không phân trang cây lệnh, không đọc BOM hiện hành, không ETag cho kế hoạch.
Nhánh đủ hàng trả `lenh=[]`. Tiến độ chỉ tính chứng từ hoàn thành đã duyệt.

## POST /api/v1/yeu_cau_san_xuat/{id}/huy

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as YeuCauSanXuatService
    participant P as SqlAlchemyYeuCauSanXuatRepository
    participant X as PhieuXuatSanXuatService / repository
    participant L as AuditService / repository
    participant D as PostgreSQL
    C->>R: POST ly_do + If-Match
    R->>A: Xác thực + role Q (401/403)
    A->>D: Đọc danh tính hiện hành
    R->>R: Validate ID, lý do trim không rỗng, không extra/query (422)
    R->>S: huy
    S->>P: get_for_update(id)
    P->>D: FOR UPDATE yêu cầu + ID lệnh (không có/vượt INT32: 404)
    S->>X: Đọc tiến độ để tạo ETag
    X->>D: SUM xuất thành phẩm đã duyệt
    S->>S: If-Match (thiếu: 428, cũ/weak/*: 412)
    alt Yêu cầu hoan_thanh / da_huy
        S-->>C: 409 trang_thai_khong_hop_le
    else Trạng thái cho phép
        S->>P: lenh_cua_yeu_cau(lock=true), chung_tu_hoan_thanh_cua_lenh(lock=true)
        P->>D: FOR UPDATE lệnh theo ID rồi chứng từ hoàn thành theo ID
        S->>X: co_phieu_da_ghi_so(yeu_cau_id, lenh_ids)
        X->>D: FOR UPDATE phiếu xuất theo ID, lấy snapshot chi tiết
        alt Có phiếu xuất / chứng từ hoàn thành da_duyet
            S-->>C: 409 phu_thuoc_khong_hop_le; rollback
        else Chưa ghi sổ
            loop Lệnh sâu nhất trước, bỏ qua lệnh đã hủy
                S->>P: huy_lenh(id)
                P->>D: UPDATE lệnh da_huy
                S->>L: append huy (trước/sau + lý do)
            end
            S->>P: Xóa hoàn thành nhap; từ chối cho_duyet; giữ tu_choi
            P->>D: DELETE hoặc UPDATE chứng từ
            S->>L: append xoa_nhap / tu_choi + lý do
            S->>X: huy_phieu_chua_ghi_so(...)
            X->>D: Khóa/kiểm tra lại phiếu; DELETE chi tiết rồi nhap, UPDATE cho_duyet thành tu_choi
            X->>L: append xoa_nhap / tu_choi + lý do
            S->>P: update yêu cầu da_huy
            P->>D: UPDATE yêu cầu
            S->>L: append huy yêu cầu + lý do
            L->>D: INSERT audit cùng session
            S->>D: COMMIT; mọi lỗi rollback toàn bộ
            S-->>C: 200 YeuCauRead + meta + ETag mới
        end
    end
```

Hủy được cả nháp khi chưa ghi sổ. Chứng từ `tu_choi` và audit cũ giữ nguyên; snapshot
trước của chứng từ bị xóa được lưu audit. Service phiếu xuất không tự commit.

## Phạm vi và kiểm chứng

- Chưa có endpoint lệnh hoặc phiếu xuất; `phieu_xuat` chỉ là collaborator nội bộ.
- Gỡ bốn endpoint `/production/work-orders`; frontend cũ chưa chuyển đổi, sẽ nhận 404.
- ORM sáu bảng theo bootstrap; không migration, không sửa database ứng dụng.
- Kiểm chứng bằng unit/API và PostgreSQL riêng `_test` với rollback. Kết quả cụ thể
  được ghi trong `.handoff/plan-yeu-cau-san-xuat.md` khi bàn giao.

## Chứng từ hoàn thành sản xuất — quy ước chung

Chín endpoint API-061–069 dưới đây theo contract v3 §11 và
`.handoff/plan-chung-tu-hoan-thanh-sx.md`. `HoanThanhRead` thêm `mat_hang_id` từ lệnh;
giữ nguyên `ChungTuRead` dùng trong hủy yêu cầu. Q đọc toàn bộ, duyệt/từ chối;
N tạo cho lệnh được giao và chỉ đọc/sửa/xóa/gửi/về nháp chứng từ của mình khi vẫn
còn được giao lệnh. Admin 403. Đọc lịch sử không kiểm active mặt hàng.

Trong các sơ đồ, AuthService/NhanVienService đọc lại tài khoản, vai trò và phiên bản
mật khẩu từ DB: thiếu/sai/hết hạn JWT hoặc mật khẩu đã đổi trả 401; tài khoản bị khóa
hoặc sai vai trò trả 403. Không tự giải mã JWT trong service sản xuất.
Body/query lạ, query lặp, header If-Match lặp trả 422. Ngoài list cấm mọi query.
ID path phải dương (422), vượt INT32 được service trả 404 trước khi bind SQL.
Không có bản ghi trả 404; có nhưng ngoài owner/assignment trả 403.

PATCH/DELETE và bốn action cần If-Match: thiếu/blank 428; cũ/weak/wildcard 412.
Strong ETag từ JSON canonical `HoanThanhRead`, không gồm trường thêm của ActionRead.
Riêng duyệt lặp đã ghi sổ đúng cần header và Q, nhưng chấp nhận ETag cũ.
`gui`/`duyet` bắt buộc body `{}`; `tu_choi`/`ve_nhap` cần `ly_do` trim không rỗng.
ID/số lượng đầu vào phải integer dương INT32; `finish_time` ISO có múi giờ, chuẩn hóa UTC.

Mọi writer dùng chung AsyncSession/SqlAlchemyTransaction với AuditService.
Repository không commit. Thứ tự khóa yêu cầu → lệnh → chứng từ → mặt hàng,
giữ đến commit; tạo chưa có chứng từ nên chỉ khóa yêu cầu → lệnh trước mặt hàng.
Tạo/sửa/gửi đọc mặt hàng FOR SHARE; duyệt FOR UPDATE. Lỗi ghi, flush, audit hoặc
commit rollback toàn bộ; lỗi constraint trả 409, lỗi bất ngờ 500 qua envelope.
Luồng mới dùng SQL tham số hóa tới `"GiaoDichKho"`, không dùng ORM inventory cũ.
Chỉ duyệt cộng tồn; mọi thao tác còn lại không giữ chỗ và không ghi kho.

## GET /api/v1/chung_tu_hoan_thanh_sx

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant D as PostgreSQL
    C->>R: GET filters, page, page_size, sort
    R->>A: JWT và tài khoản hiện hành, Q/N
    A->>D: Đọc nhân viên và vai trò
    alt Auth hoặc role sai
        R-->>C: 401 / 403
    else Được phép
        R->>R: Validate query, enum, ngày, sort, query lặp
        alt Query sai
            R-->>C: 422
        else Hợp lệ
            R->>S: list_entries(params, actor)
            S->>P: list_entries(params, N.id hoặc null cho Q)
            P->>D: COUNT JOIN chứng từ-lệnh với filter và scope
            opt Offset nhỏ hơn total
                P->>D: SELECT cùng filter/scope, sort, offset, limit
            end
            S-->>C: 200 HoanThanhRead[] và meta phân trang
        end
    end
```

Phạm vi N lọc đồng thời chủ chứng từ và người đang được giao lệnh, trước COUNT/page.
Filter `q` tìm mã bằng ILIKE escape; thêm `lenh_san_xuat_id`, `mat_hang_id`,
`nhan_vien_id`, `trang_thai`, `tu_ngay`, `den_ngay`. Ngày theo `finish_time`,
Asia/Ho_Chi_Minh, đổi thành khoảng UTC nửa mở gồm ngày cuối bằng PostgreSQL timezone.
NULL không khớp filter ngày; không có filter vẫn đọc NULL. Sort mặc định `-id`,
whitelist `id`, `finish_time`, `ma_phieu` và chiều ngược; NULLS LAST, ID phụ tăng dần.
Q/N cùng projection. COUNT/SELECT là hai statement, có thể lệch total/page khi có
tạo/xóa đồng thời. Không ETag danh sách, audit hay ledger.

## GET /api/v1/chung_tu_hoan_thanh_sx/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant D as PostgreSQL
    C->>R: GET id
    R->>A: JWT và tài khoản hiện hành, Q/N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role sai hoặc path/query sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: get_entry(id, actor)
        opt ID trong INT32
            S->>P: get_by_id(id)
            P->>D: SELECT JOIN chứng từ-lệnh, không lọc quyền
        end
        alt Không tồn tại hoặc vượt INT32
            S-->>C: 404
        else N không là chủ hoặc không còn được giao lệnh
            S-->>C: 403
        else Trong phạm vi
            S-->>C: 200 HoanThanhRead và ETag
        end
    end
```

`finish_time=NULL` lịch sử vẫn đọc được; mặt hàng inactive vẫn đọc được.

## POST /api/v1/chung_tu_hoan_thanh_sx

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: POST lệnh, lượng, finish_time
    R->>A: JWT và tài khoản hiện hành, N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role sai hoặc body/query sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: create_entry(payload, actor)
        S->>T: Bắt đầu transaction dùng chung
        S->>P: lock_for_create(lệnh)
        P->>D: Khóa yêu cầu rồi lệnh FOR UPDATE
        alt Không có lệnh / không được giao / lệnh không đang thực hiện
            S->>T: Rollback
            S-->>C: 404 / 403 / 409
        else Lệnh hợp lệ
            S->>P: read_output(mặt hàng)
            P->>D: SELECT MatHang FOR SHARE
            S->>S: Kiểm tồn tại, active, loại đầu ra, thời gian và lượng
            alt Thiếu mặt hàng / inactive, sai loại, quá lượng, thiếu started_at / thời gian trước bắt đầu
                S->>T: Rollback
                S-->>C: 404 / 409 / 422
            else Hợp lệ
                S->>P: add(payload, actor.id)
                P->>D: nextval identity, sinh mã, INSERT nhap, flush
                S->>U: append tao, snapshot trước null và sau chứng từ
                U->>D: INSERT LichSuThaoTac
                S->>T: Commit
                alt Hết dải mã hoặc ghi/flush/audit/commit lỗi
                    T->>D: Rollback toàn bộ
                    R-->>C: 409 / 500
                else Thành công
                    S-->>C: 201 HoanThanhRead, Location và ETag
                end
            end
        end
    end
```

Mã `HTSX-YYYYMM-NNNNNN` dùng identity, tháng Asia/Ho_Chi_Minh; hậu tố không reset,
không tái sử dụng ID, có thể có khoảng trống; vượt 999999 trả 409.
Nháp có thể khai thời gian tương lai, nhưng không trước `started_at`.
Mỗi đợt không vượt lượng lệnh; nhiều nháp cùng lệnh không giữ chỗ lượng hoặc tồn.

## PATCH /api/v1/chung_tu_hoan_thanh_sx/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: PATCH lượng hoặc finish_time, If-Match
    R->>A: JWT và tài khoản hiện hành, N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/body/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: patch_entry
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại / ngoài owner-assignment
            S->>T: Rollback
            S-->>C: 404 / 403
        else Trong phạm vi
            S->>S: So If-Match, kiểm nhap
            S->>P: postings(id)
            P->>D: SELECT ledger nguồn
            alt Thiếu/cũ ETag hoặc sai state/có ledger
                S->>T: Rollback
                S-->>C: 428 / 412 / 409
            else Nháp chưa ghi sổ
                S->>S: Merge các field được phép
                alt Giá trị không thay đổi
                    S->>T: Commit không ghi
                    S-->>C: 200, giữ ETag, không audit
                else Có thay đổi
                    S->>S: Kiểm lượng, finish_time so với started_at
                    S->>P: read_output FOR SHARE, kiểm active và loại
                    P->>D: SELECT MatHang
                    alt Thời gian / lượng hoặc đầu ra sai
                        S->>T: Rollback
                        S-->>C: 422 / 404 / 409
                    else Hợp lệ
                        S->>P: update(changes), flush
                        P->>D: UPDATE chứng từ
                        S->>U: append sua với snapshot trước/sau
                        U->>D: INSERT audit
                        S->>T: Commit, lỗi ghi/flush/audit/commit rollback toàn bộ
                        S-->>C: 200 và ETag mới, hoặc 409 / 500 nếu lỗi
                    end
                end
            end
        end
    end
```

PATCH rỗng hoặc explicit null trả 422. Không yêu cầu lệnh đang thực hiện; không mở lại lệnh.

## DELETE /api/v1/chung_tu_hoan_thanh_sx/{id}

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: DELETE id, If-Match
    R->>A: JWT và tài khoản hiện hành, N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/path/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: delete_entry
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại / ngoài owner-assignment
            S->>T: Rollback
            S-->>C: 404 / 403
        else Trong phạm vi
            S->>S: If-Match, trạng thái nhap
            S->>P: postings(id)
            P->>D: SELECT ledger nguồn
            alt Thiếu/cũ ETag hoặc sai state/có ledger
                S->>T: Rollback
                S-->>C: 428 / 412 / 409
            else Nháp chưa ghi sổ
                S->>P: delete(id)
                P->>D: DELETE chứng từ
                S->>U: append xoa_nhap, trước chứng từ, sau null
                U->>D: INSERT audit
                S->>T: Commit, lỗi ghi/flush/audit/commit rollback toàn bộ
                S-->>C: 204 không body, hoặc 409 / 500 nếu lỗi
            end
        end
    end
```

Không yêu cầu lệnh đang thực hiện; không xóa ledger hoặc hoàn tồn.

## POST /api/v1/chung_tu_hoan_thanh_sx/{id}/gui

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: POST gui, body {}, If-Match
    R->>A: JWT và tài khoản hiện hành, N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/body/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: gui
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại / ngoài owner-assignment
            S->>T: Rollback
            S-->>C: 404 / 403
        else Trong phạm vi
            S->>S: If-Match, nhap, lệnh dang_thuc_hien
            S->>P: postings, read_output FOR SHARE
            P->>D: Đọc ledger nguồn và MatHang
            S->>S: Chưa ledger, active, loại đầu ra, lượng, started_at ≤ finish_time ≤ now
            alt ETag, state, thời gian, lượng hoặc mặt hàng sai
                S->>T: Rollback
                S-->>C: 428 / 412 / 404 / 409 / 422
            else Hợp lệ
                S->>P: update cho_duyet, flush
                P->>D: UPDATE chứng từ
                S->>U: append gui với snapshot trước/sau
                U->>D: INSERT audit
                S->>T: Commit, lỗi ghi/flush/audit/commit rollback toàn bộ
                S-->>C: 200 HoanThanhRead và ETag, hoặc 409 / 500 nếu lỗi
            end
        end
    end
```

Thiếu `finish_time`/`started_at` trả 409; trước bắt đầu hoặc tương lai trả 422.
Gửi không ghi kho, không kiểm giữ chỗ giữa các nháp.

## POST /api/v1/chung_tu_hoan_thanh_sx/{id}/duyet

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: POST duyet, body {}, If-Match
    R->>A: JWT và tài khoản hiện hành, Q
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/body/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: duyet
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại hoặc thiếu/blank If-Match
            S->>T: Rollback
            S-->>C: 404 / 428
        else Có header
            S->>P: postings(id)
            P->>D: SELECT ledger nguồn
            alt Chứng từ da_duyet
                S->>S: Đúng 1 ledger, khớp nguồn, mặt hàng, loại và lượng dương
                alt Thiếu hoặc sai ledger
                    S->>T: Rollback
                    S-->>C: 409, không tự sửa sổ
                else Khớp
                    S->>T: Commit không ghi
                    S-->>C: 200 ActionRead, replay true, ledger cũ và ETag hiện tại
                end
            else Chưa duyệt
                S->>S: So If-Match, cho_duyet, chưa ledger, lệnh đang thực hiện, thời gian
                alt ETag/state/thời gian sai
                    S->>T: Rollback
                    S-->>C: 412 / 409 / 422
                else Hợp lệ
                    S->>P: lock_output(mặt hàng)
                    P->>D: MatHang FOR UPDATE rồi SUM ledger mặt hàng
                    S->>S: Active, loại đầu ra, balance bằng ledger, không tràn INT32
                    S->>P: approved_quantity, material_quantities
                    P->>D: SUM lượng chứng từ da_duyet của lệnh
                    P->>D: Nhu cầu ChiTietLenhSanXuat, SUM ledger xuất vật tư đã duyệt
                    S->>S: Tổng không vượt lượng lệnh, đủ vật tư trực tiếp cả lệnh
                    alt Thiếu mặt hàng hoặc điều kiện đầu ra/vật tư/tổng sai
                        S->>T: Rollback
                        S-->>C: 404 / 409
                    else Cho phép ghi sổ
                        S->>P: update da_duyet và flush
                        P->>D: UPDATE trạng thái trước INSERT ledger
                        S->>P: post_output(actor Q, UTC now)
                        P->>D: Cộng tồn, cập nhật ton_kho_updated_at
                        P->>D: INSERT ledger nhap_san_pham_san_xuat dương
                        opt Tổng đã duyệt bằng lượng lệnh
                            S->>P: complete_order(now)
                            P->>D: Đọc snapshot lệnh trước/sau, UPDATE hoan_thanh và completed_at
                            S->>U: append lenh_san_xuat/hoan_tat trước/sau
                            U->>D: INSERT audit lệnh
                        end
                        S->>U: append chứng từ/duyet trước/sau
                        U->>D: INSERT audit chứng từ
                        S->>T: Commit
                        alt Ghi/flush/audit/commit lỗi
                            T->>D: Rollback state, stock, ledger, lệnh, audit
                            R-->>C: 409 constraint / 500
                        else Thành công
                            S-->>C: 200 ActionRead, replay false, ledger mới và ETag
                        end
                    end
                end
            end
        end
    end
```

Ledger và audit ghi ID Q; chủ chứng từ giữ nguyên N. Không trừ vật tư lần hai,
không đọc BOM hiện hành. Dùng nhu cầu đã đóng băng và ledger phiếu `xuat_vat_tu`
`da_duyet`; kiểm đủ toàn bộ nhu cầu cả lệnh. Quá lượng trả 409
`vuot_so_luong_hoan_thanh`; thiếu vật tư trả 409 `chua_du_vat_tu_da_cap`.
Khóa lệnh tuần tự hóa các đợt cùng lệnh; khóa output bảo vệ số dư giữa các lệnh.
Retry đúng không thêm audit/ledger/tồn và không yêu cầu lệnh vẫn đang thực hiện.
`completed_at` theo thời điểm duyệt cuối; `finish_time` vẫn là thời điểm N khai báo.
Không tự hoàn thành yêu cầu: yêu cầu hoàn thành theo thành phẩm đã xuất.

## POST /api/v1/chung_tu_hoan_thanh_sx/{id}/tu_choi

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: POST tu_choi, ly_do, If-Match
    R->>A: JWT và tài khoản hiện hành, Q
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/body/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: tu_choi, kiểm lý do
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại
            S->>T: Rollback
            S-->>C: 404
        else Tồn tại
            S->>S: If-Match, cho_duyet
            S->>P: postings(id)
            P->>D: SELECT ledger nguồn
            alt Thiếu/cũ ETag hoặc sai state/có ledger
                S->>T: Rollback
                S-->>C: 428 / 412 / 409
            else Hợp lệ
                S->>P: update tu_choi, flush
                P->>D: UPDATE chứng từ
                S->>U: append tu_choi, lý do và snapshot trước/sau
                U->>D: INSERT audit
                S->>T: Commit, lỗi ghi/flush/audit/commit rollback toàn bộ
                S-->>C: 200 HoanThanhRead và ETag, hoặc 409 / 500 nếu lỗi
            end
        end
    end
```

Không yêu cầu lệnh đang thực hiện, không ghi kho hoặc hoàn vật tư đã xuất.

## POST /api/v1/chung_tu_hoan_thanh_sx/{id}/ve_nhap

```mermaid
sequenceDiagram
    actor C as Client
    participant R as Router
    participant A as AuthService / NhanVienService
    participant S as ChungTuHoanThanhService
    participant P as SqlAlchemyHoanThanhRepository
    participant U as AuditService / repository
    participant T as SqlAlchemyTransaction
    participant D as PostgreSQL
    C->>R: POST ve_nhap, ly_do, If-Match
    R->>A: JWT và tài khoản hiện hành, N
    A->>D: Đọc nhân viên và vai trò
    alt Auth/role/body/query/header sai
        R-->>C: 401 / 403 / 422
    else Được phép
        R->>S: ve_nhap, kiểm lý do
        S->>T: Bắt đầu transaction
        S->>P: lock_context(id)
        P->>D: Khóa yêu cầu → lệnh → chứng từ
        alt Không tồn tại / ngoài owner-assignment
            S->>T: Rollback
            S-->>C: 404 / 403
        else Trong phạm vi
            S->>S: If-Match, tu_choi
            S->>P: postings(id)
            P->>D: SELECT ledger nguồn
            alt Thiếu/cũ ETag hoặc sai state/có ledger
                S->>T: Rollback
                S-->>C: 428 / 412 / 409
            else Hợp lệ
                S->>P: update nhap, flush
                P->>D: UPDATE chứng từ
                S->>U: append ve_nhap, lý do và snapshot trước/sau
                U->>D: INSERT audit
                S->>T: Commit, lỗi ghi/flush/audit/commit rollback toàn bộ
                S-->>C: 200 HoanThanhRead và ETag, hoặc 409 / 500 nếu lỗi
            end
        end
    end
```

Không ghi kho, không tự mở lại lệnh. Gửi lại vẫn phải đáp ứng điều kiện lệnh,
mặt hàng, lượng và thời gian. Mã audit đối tượng là
`chung_tu_hoan_thanh_san_xuat`, khác hậu tố `_sx` trên URL.

### Giới hạn kiểm chứng của phần hoàn thành

Các sơ đồ được đối chiếu router, schema, service, repository, dependency và bootstrap.
Chưa render/kiểm cú pháp bằng Mermaid. Theo yêu cầu dev, không tiếp tục kiểm thử DB
riêng; chưa xác nhận tính atomic và xử lý đồng thời bằng PostgreSQL thực tế.
API giao/gửi/bắt đầu lệnh chưa có; các API mới cần lệnh đã được giao và đang thực hiện.
