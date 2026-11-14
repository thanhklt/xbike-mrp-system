# Đặc tả backend Goods Receipt — UC-20 đến UC-22

**BACKEND IMPLEMENTED — spec, Q1–Q5 và plan/task đã được dev duyệt ngày 14/11/2026.**
Hoàn tất triển khai và kiểm chứng ngày 15/11/2026; xem [plan/kết quả T01–T12](PLAN.md).
80 test phiếu nhập pass trên PostgreSQL test riêng; không thay đổi database ứng dụng,
SQL bootstrap, migration hoặc frontend. Spec không phải thành phần được gọi khi chạy.

Phạm vi là cả ba use case trong `goods_receipt`, chỉ backend. Giữ module runtime
`backend/app/modules/phieu_nhap/`, không tạo module goods_receipt trùng trách nhiệm.
Giữ nguyên nội dung ba UC gốc; tài liệu này bổ sung luồng, tiêu chí backend và truy vết.

## 1. Mục tiêu và nguồn đã đối chiếu

QLK lập, sửa, xóa phiếu nhập linh kiện nháp; hoàn tất cộng tồn đúng một lần; xem
danh sách/chi tiết đúng quyền. Kho, ledger, phiếu và audit thành công hoặc rollback
cùng nhau. Phiếu nhập độc lập với yêu cầu sản xuất, không có bước gửi/duyệt riêng.

| Nguồn đã đọc | Nội dung sử dụng |
|---|---|
| [UC-20](UC-20.md) | Nội dung phiếu, chỉ linh kiện, nháp sửa/xóa được, audit |
| [UC-21](UC-21.md) | Xác nhận hoàn tất, cộng tồn một lần, tránh xác nhận dữ liệu cũ |
| [UC-22](UC-22.md) | QLK xem danh sách/chi tiết, QTV bị chặn; quyền NV/bộ lọc chốt Q2/Q3 |
| [BR giai đoạn 1](../../business_requirements/BR-GIAIDOAN1.md) | BR-001/003/004/006/015/016: quyền, dữ liệu nền, nhập, xác nhận và lịch sử |
| [Data model v4](../../entity_model/data_model_v4.md) §3.2/3.4/3.7/3.8 | BIGINT VND, metadata, phiên bản, nguồn ledger và audit |
| [Entity model](../../entity_model/entity_model.md) | Quan hệ PhieuNhap/ChiTietPhieuNhap/MatHang/GiaoDichKho |
| [init.sql](../../../infra/postgres/init.sql) | Schema PostgreSQL v4, nullable/default/Identity/FK/check/index/trigger |
| [UC-44 R8](../catalog/UC-44.md) | Thông tin NCC hiện tại, không chụp NCC trên phiếu |
| Source phieu_nhap, inventory, audit, dependencies và core transaction/request context | Chênh lệch triển khai, luồng thực tế và thành phần dùng lại |
| [Sequence đã cập nhật](../../../docs/sequence/phieu_nhap.md) | Sáu endpoint v4 cùng PNG, phản ánh code và kiểm chứng của tác vụ này |

Quyết định Q1 chọn UC/BR/schema v4 hiện trong repository làm chuẩn cho tác vụ.
README tổng thể và sequence cũ còn nội dung v3.1 không được dùng để sửa ngược v4.
Chưa kiểm tra schema database ứng dụng; đối chiếu hiện tại là với PostgreSQL DDL
trong init.sql. Khi triển khai phải kiểm chứng trên PostgreSQL test riêng tạo mới/trống.

## 2. Khảo sát hiện trạng — trước triển khai

### 2.1. Checkout, framework và test

- Nhánh `feature/phieu_nhap`, HEAD `f461ecd` (merge tài liệu/data model v4).
  Working tree sạch trước khi tạo file spec này. Không tự merge/cherry-pick nhánh khác.
- Backend modular monolith: FastAPI + Pydantic v2; SQLAlchemy async/asyncpg; PostgreSQL.
  Tổ chức router/schema/service/port/repository/ORM theo từng module.
- Đã đọc manifest và xác minh bản cài: FastAPI 0.144.0, Pydantic 2.14.1,
  SQLAlchemy 2.1.5, asyncpg 0.32.0, pytest 9.1.1, pytest-asyncio 1.4.0.
- Chỉ có `backend/tests/test_nhan_vien_create_code.py`; chưa có fixture hoặc test
  phiếu nhập, chưa có test/source mới của các nhánh BOM/Catalog/phiếu xuất trong checkout.
- Đã chạy `pytest tests -q --tb=line`: **8 fail**, cùng lỗi fixture tại dòng 86,
  `VaiTroRead.mo_ta` thiếu. Đây là baseline ngoài phạm vi, không sửa để làm xanh suite.
- Import app/OpenAPI thành công, xác nhận sáu endpoint bên dưới. Đây không phải
  bằng chứng các endpoint đã chạy đúng trên PostgreSQL v4.
- Ruff module phieu_nhap pass. Structure map không có cycle/misplaced/mixed/
  unreferenced trong module; các handler/cấu trúc giống nhau không buộc tạo abstraction mới.
- Chưa có `.clean/architecture.md`; chưa thể dùng boundary checker theo declaration.
  Không tạo config kiến trúc giả. Áp dụng hướng dẫn repository và đối chiếu source trực tiếp.

### 2.2. Endpoint hiện có

Prefix đầy đủ `/api/v1/phieu_nhap`. Router hiện chặn mọi endpoint ngoài `quan_ly`.

| Method / path | Service hiện hữu | Response hiện tại |
|---|---|---|
| GET `/api/v1/phieu_nhap` | list_receipts | 200, data/meta phân trang |
| GET `/api/v1/phieu_nhap/{id}` | get_receipt | 200, data/meta + ETag |
| POST `/api/v1/phieu_nhap` | create_receipt | 201, data/meta + Location + ETag |
| PATCH `/api/v1/phieu_nhap/{id}` | patch_receipt | 200, data/meta + ETag |
| DELETE `/api/v1/phieu_nhap/{id}` | delete_receipt | 204, không body |
| POST `/api/v1/phieu_nhap/{id}/hoan_tat` | complete_receipt | 200, resource + ledger IDs + cờ replay + ETag |

`/receiving` cũ đã được gỡ khỏi main; không khôi phục alias. Các method service đọc
chưa nhận actor, service ghi cũng chưa tự kiểm tra role; quyền hiện chủ yếu ở router.
Luồng mới phải có guard nghiệp vụ ở service theo cùng policy Q2.

### 2.3. Chênh lệch với v4

| Phần | Code hiện tại | Yêu cầu v4 / tác động |
|---|---|---|
| Tiền | Numeric(18,2)/Decimal, input chuỗi hoặc int, output chuỗi | BIGINT/JSON integer VND; chặn chuỗi/float/bool, không âm, không tràn tổng/dòng |
| Loại mặt hàng | Cho `nguyen_vat_lieu` hoặc `linh_kien` đang active | Chỉ `linh_kien`; không thêm nghiệp vụ ngừng linh kiện |
| Header phiếu | Thiếu updated_at/hoan_thanh_at/nguoi_hoan_thanh_id/phien_ban | Đồng bộ các cột/default/check/FK đúng init.sql |
| Chi tiết | Giá/tổng nullable, CHECK cũ chỉ không âm, tên unique index cũ | Giá/tổng NOT NULL BIGINT, tổng đúng tích, unique(parent,item) đúng SQL |
| mark_completed | Chỉ đổi trang_thai | Chưa đáp ứng CHECK metadata hoàn tất trong DDL v4; cần actor/time/version |
| receive_receipt | Mã `nhap_vat_tu`, không ghi so_luong_ton_sau | V4 cần `nhap_linh_kien`, tồn sau bắt buộc, một FK nguồn chi tiết |
| Tồn/giữ | Đã cộng trực tiếp MatHang.so_luong_ton, chưa xử lý đầy đủ mô hình v4 | Cộng tồn, giữ nguyên đang giữ và GiuHang; available tăng theo cột computed |
| Audit | Đã qua AuditService/repository chung TX, DTO/ORM thiếu hai cột trạng thái | Bổ sung metadata tối thiểu theo Q5; không refactor toàn UC-43 |
| ETag/If-Match | Hash resource chưa có metadata; blank không như missing, header lặp 422; replay bỏ kiểm tra format | Strong validator theo Q4, kiểm tra dưới khóa; phiên bản ngăn stale/no-op nhầm |
| GET | FOR SHARE header; COUNT/page chưa cùng snapshot ổn định | Không ghi dữ liệu, representation/ETag nhất quán; bộ lọc/count/page chính xác |
| Tài liệu/test | Sequence v3.1, không có test phiếu nhập | Cập nhật sau khi code đổi; không gắn nhãn pass trước khi chạy |

Các lỗi tương thích PostgreSQL ở bảng trên được xác định bằng đối chiếu tĩnh
code/DDL; chưa thực hiện mutation/API test trên DB v4 trong bước khảo sát này.

## 3. Phạm vi nghiệp vụ và quyết định đã chốt

### 3.1. Q1–Q5

| Mã | Dev xác nhận | Ảnh hưởng |
|---|---|---|
| Q1 | Dùng UC-20–22/BR/schema v4; module phieu_nhap; BIGINT/integer VND | Breaking tiền chuỗi Decimal; giữ PascalCase, không đổi DB hiện có/migration |
| Q2 | Chỉ QLK đọc và ghi cả sáu endpoint | QTV và NV đều 403; không có scope chủ phiếu riêng giữa các QLK |
| Q3 | Giữ bộ lọc và mặc định hiện tại | q mã, trạng thái, NCC, người lập, khoảng created_at giờ VN, AND; page 1/20/max100, sort mặc định id tăng |
| Q4 | Hoàn tất lại trả kết quả cũ, cho tag cũ đúng định dạng | Một If-Match vẫn bắt buộc; thiếu/trắng 428, weak/wildcard/nhiều tag/sai format 412; không ghi lần hai |
| Q5 | Phụ thuộc inventory/audit tối thiểu, chỉ backend | Không tự merge nhánh, không sửa đường xuất/điều chỉnh/sản xuất; E2E ngoài phiếu nhập chưa nghiệm thu |

Spec tổng thể đã được duyệt; Q1–Q5 và duyệt spec không thay thế cổng duyệt plan/task.
Không còn câu hỏi nghiệp vụ mở tại thời điểm viết; nếu phát sinh mâu thuẫn mới phải
dừng phần phụ thuộc và xin xác nhận, không tự chọn schema hoặc thay đổi scope.

### 3.2. Actor, trigger và tiền điều kiện

- Actor nghiệp vụ: tài khoản QLK (`quan_ly`) đang hoạt động. Role/trạng thái account
  được xác minh từ DB mỗi request bằng cơ chế auth hiện có, không tin riêng claim role.
- QLK được quản lý mọi phiếu nhập, không giới hạn chỉ người lập. Người lập và người
  hoàn tất lấy từ actor xác thực, client không được đặt các field này.
- Trigger: QLK lưu nháp, sửa/xóa nháp, xác nhận hoàn tất, hoặc tra cứu phiếu.
- Tạo/sửa: NCC tồn tại, ngày hợp lệ, ít nhất một dòng linh kiện, số lượng nguyên
  dương, đơn giá nguyên VND không âm, không trùng linh kiện, tổng không tràn BIGINT.
- Sửa/xóa/hoàn tất lần đầu: resource còn nháp và validator khớp resource đã đọc.
- Không phụ thuộc yêu cầu sản xuất hoặc tình trạng đã cấp/giữ của yêu cầu sản xuất.

### 3.3. Dữ liệu và giới hạn phạm vi

- POST nhận `ncc_id`, `ngay_nhap` (`YYYY-MM-DD`), `ghi_chu` optional/null và
  `chi_tiet[{mat_hang_id,so_luong,don_gia_thuc}]`. Không nhận mã/ID phiếu, actor,
  trạng thái, tổng tiền, metadata hoàn tất hoặc liên kết yêu cầu sản xuất.
- Tiền là integer VND `0..9223372036854775807`; ID/số lượng theo PostgreSQL INTEGER.
  Boolean/float/chuỗi tiền không được âm thầm chuyển đổi hoặc làm tròn.
  Server tính `tong_gia = so_luong * don_gia_thuc`, `tong_tien = SUM(tong_gia)`.
- Giá nhập là giá thực tế trên từng dòng do QLK nhập; không thay bằng đơn giá danh
  mục, không tự sửa MatHang.don_gia hoặc tính bình quân giá kho trong tác vụ này.
- `ngay_nhap` là DATE do QLK cung cấp, khác created_at do hệ thống cấp. Giữ validation
  ngày ISO hiện hữu; tài liệu chưa quy định cấm ngày tương lai, không tự bổ sung lệnh cấm.
- PATCH giữ semantics hiện tại: field bỏ qua giữ nguyên; `ghi_chu=null` xóa ghi chú;
  NCC/ngày/chi_tiet explicit null không hợp lệ; chi_tiet nếu gửi phải là danh sách
  đầy đủ không rỗng, thay toàn bộ chi tiết. PATCH không thay đổi thực tế theo phép so
  sánh hiện hữu không tạo audit mới; không tự tạo endpoint sửa dòng riêng.
- NCC chỉ liên kết bằng ncc_id, không chụp thông tin NCC lên phiếu. UI sau này đọc
  thông tin hiện tại qua API NCC; không mở rộng response bằng snapshot NCC mới.
  Không thay đổi tính bất biến của nội dung phiếu đã hoàn tất khi NCC được sửa.
- Giữ mã `PN-YYYYMM-NNNNNN` theo tháng Asia/Ho_Chi_Minh, không trùng/không tái dùng
  mã đã xóa nháp; ID do PostgreSQL Identity cấp. Hết dải mã trả lỗi, không quay vòng.
- Chỉ bootstrap mới/trống và DB test riêng được dùng để kiểm chứng sau duyệt plan.
  Không nâng dữ liệu v3.1 cũ, không seed lại DB ứng dụng, không giả định ORM đã cập nhật DB.
- Ngoài phạm vi: frontend/hộp thoại, trả NCC, nhập TP bên ngoài, phiếu điều chỉnh,
  undo hoàn tất, cấp duyệt riêng, ticket, đa kho, liên kết hoặc tự kiểm tra lại yêu cầu sản xuất.

## 4. Luồng sự kiện

### 4.1. UC-20 — Tạo nháp

1. QLK gửi nội dung phiếu; router kiểm tra cấu trúc và actor/dependency.
2. Service kiểm tra quyền QLK, NCC và loại mặt hàng, tính đúng tổng/giới hạn.
3. Hệ thống cấp mã/Identity, lưu trạng thái nhap, header/chi tiết đầy đủ, phiên bản
   ban đầu; ghi audit tao với actor/thời gian/trạng thái/snapshot sau.
4. Commit một lần. Trả phiếu, ETag, Location. Tồn, giữ hàng và ledger không đổi.

Thay thế/lỗi: tài khoản sai/khóa bị chặn; input không hợp lệ 422; FK không tồn tại
404; mặt hàng sai loại hoặc xung đột mã/ràng buộc nghiệp vụ 409; audit/ghi lỗi rollback.

### 4.2. UC-20 — Sửa nháp

1. QLK đọc chi tiết/ETag, gửi PATCH các field cần sửa và If-Match.
2. Trong transaction, khóa resource và đọc lại chi tiết; service kiểm tra quyền,
   header/phiên bản, trạng thái nhap và chưa có ledger.
3. Validate các thay đổi/NCC/linh kiện, tính tổng từ đơn giá thực tế nếu thay chi tiết.
4. Có thay đổi: cập nhật resource/updated_at/phien_ban, audit sua trước/sau; commit.
   Không thay đổi: giữ resource/ETag và không tạo audit thành công mới.
5. Trả phiếu/ETag. Không sửa người lập, mã phiếu, tồn, giữ hoặc ledger.

Thay thế/lỗi: sai actor, không có phiếu, header thiếu/sai/cũ, đã hoàn tất, dữ liệu
hoặc FK sai đều bị chặn; không có cập nhật một phần. Đổi nội dung A→B→A vẫn là phiên
bản mới nên tag ban đầu không được dùng lại.

### 4.3. UC-20 — Xóa nháp

1. QLK gửi DELETE ID + If-Match.
2. Khóa resource/chi tiết trong transaction, kiểm tra quyền, tag, nháp, chưa ghi sổ.
3. Xóa chi tiết/header; audit xoa_nhap giữ snapshot trước, actor/thời điểm/trạng thái.
4. Commit cùng audit; trả 204, không body. Mã trong audit không được dùng lại.

Thay thế/lỗi: đã hoàn tất hoặc đã có ledger không được xóa; stale tag không được
xóa bản mới; lỗi audit/constraint/commit rollback cả xóa. Không cascade xóa ledger/audit.

### 4.4. UC-21 — Hoàn tất lần đầu

1. QLK xem phiếu và tác động; hành động xác nhận gửi POST hoan_tat với `{}` và tag.
   Đóng hộp thoại không gửi request; phần UI này chưa triển khai/kiểm chứng ở backend.
2. Service kiểm tra quyền hiện tại; trong cùng transaction, khóa phiếu/chi tiết,
   so validator dưới khóa, kiểm tra còn nháp/chưa có ledger, nội dung và tổng hợp lệ.
3. Khóa các mặt hàng liên quan theo ID ổn định. Kiểm tra số dư tồn khớp ledger;
   lượng tồn sau không vượt INTEGER; không tự sửa số dư sai lệch.
4. Chuyển phiếu hoan_thanh, ghi nguoi_hoan_thanh_id/hoan_thanh_at/updated_at,
   tăng phien_ban. Metadata và trạng thái cùng ghi, đáp ứng CHECK của SQL.
5. Cộng MatHang.so_luong_ton; giữ nguyên so_luong_dang_giu và các GiuHang. Cột
   so_luong_con_dung tự phản ánh số dư mới, không ghi tay vào cột computed.
6. Mỗi chi tiết tạo đúng một ledger dương loại nhap_linh_kien, đúng FK nguồn,
   mặt hàng/số lượng, actor/thời điểm và so_luong_ton_sau.
7. Ghi audit hoan_tat đầy đủ trạng thái/snapshot trước-sau, commit một lần.
8. Trả phiếu hiện tại, ledger IDs, `da_ghi_so_truoc_do=false`, ETag mới.

Không làm đổi YeuCauSanXuat/NhuCauLinhKien, không tự giữ hàng hoặc cấp bổ sung;
yêu cầu đang chờ vẫn chờ cho đến use case kiểm tra lại của NV. Lỗi ở trạng thái,
tồn, ledger, audit hoặc commit rollback tất cả, không để phiếu hoàn tất một phần.

### 4.5. UC-21 — Gọi lại / cạnh tranh

1. Vẫn xác thực QLK đang hoạt động và yêu cầu một If-Match đúng định dạng.
2. Khóa/đọc lại phiếu. Nếu đã hoan_thanh và ledger đầy đủ, khớp từng dòng/type/qty,
   trả resource hiện tại, ledger IDs cũ, `da_ghi_so_truoc_do=true`, tag hiện tại.
   Tag cũ được chấp nhận riêng nhánh này theo Q4.
3. Không cộng tồn, sửa giữ/giá/metadata, ghi ledger hoặc audit lần hai; không kiểm
   tra lại giá danh mục/tồn hiện tại để quyết định kết quả thành công cũ.
4. Nếu đã hoàn tất nhưng ledger thiếu/sai, trả 409; không tự sửa/ghi bù.
5. Hai lần hoàn tất cùng phiếu chỉ một lần thực sự ghi sổ. Sửa/xóa và hoàn tất
   cạnh tranh phải có một thứ tự hợp lệ, không mất cập nhật hoặc ghi chứng từ cũ.

### 4.6. UC-22 — Danh sách / chi tiết

1. Kiểm tra account/role hiện tại; chỉ QLK, QTV/NV không được đọc.
2. Kiểm tra path/query, filter/sort/page hợp lệ; GET không gây thay đổi nghiệp vụ.
3. Danh sách lọc AND theo Q3, COUNT và trang/chi tiết phải nhất quán; trả đủ cả nháp
   lẫn hoàn tất, phân biệt bằng trang_thai, [] là kết quả hợp lệ.
4. Chi tiết trả metadata v4 và chi tiết ổn định; ETag ứng với chính representation đó.
   ID không tồn tại hoặc quá dải INTEGER trả 404, không lỗi overflow asyncpg.
5. Session đọc kết thúc mà không ghi kho/phiếu/giữ/ledger/audit.

## 5. HTTP, trạng thái và lỗi quan sát được

Giữ sáu method/path trong mục 2.2, envelope thành công `{data,meta}` và lỗi
`{error:{code,message,details},meta:{request_id}}` đang có. Cấu trúc HTTP đầy đủ,
schema cụ thể và dependency được đối chiếu trong plan sau khi spec được duyệt.

| Tình huống | Kết quả |
|---|---|
| Tạo | 201 + Location + ETag; trạng thái nhap |
| Đọc/sửa | 200; chi tiết/sửa trả ETag, danh sách có meta phân trang |
| Xóa nháp | 204 không body |
| Hoàn tất / replay hợp lệ | 200 + ETag + ledger IDs/cờ replay |
| Chưa xác thực/token không hợp lệ | 401, header Bearer theo cơ chế chung |
| Không có quyền/account khóa | 403 |
| Phiếu/NCC/linh kiện không tồn tại | 404 |
| Thiếu hoặc toàn khoảng trắng If-Match | 428 |
| Weak/wildcard/sai format/nhiều header hoặc nhiều tag | 412 |
| Tag cũ | 412, trừ replay hoàn tất hợp lệ theo Q4 |
| Sai schema/duplicate item/tiền sai kiểu, tràn tính toán input/unknown hoặc repeated query | 422 |
| Sai loại linh kiện/trạng thái/ledger/số dư/giới hạn tồn hoặc constraint nghiệp vụ | 409 |
| Lỗi không dự kiến trong ghi/audit/commit | 500 an toàn và rollback, không lộ bí mật |

Nháp → hoàn tất là chuyển trạng thái duy nhất; không hủy/về nháp/duyệt/từ chối
phiếu nhập. Hoàn tất bất biến. PATCH/DELETE không được hưởng ngoại lệ replay của Q4.
Không cam kết ưu tiên auth/validation nếu request đồng thời sai nhiều điều kiện.

Q3: q tìm mã không phân biệt hoa/thường, `%`/`_` là ký tự thường. Bộ lọc trạng thái,
ncc_id, nhan_vien_id, tu_ngay/den_ngay theo **created_at**, bao gồm cả ngày theo giờ VN;
không thêm bộ lọc ngay_nhap. Page mặc định 1, size 20, max100. Sort id/created_at/
ma_phieu_nhap và dạng `-`, mặc định id tăng; ID tăng làm tiêu chí phụ khi bằng nhau.

Read DTO bổ sung updated_at, hoan_thanh_at, nguoi_hoan_thanh_id, phien_ban theo v4.
Thời gian TIMESTAMPTZ trả UTC/Z, ngay_nhap giữ DATE. Giá/tổng là JSON integer VND;
total có thể null theo DDL nhưng dữ liệu tạo mới luôn tính đầy đủ; không hoàn tất
resource có giá/tổng không nhất quán. Không nhận metadata do client tự gán.

## 6. Phân tầng, transaction và giới hạn tích hợp

Luồng runtime: `Router → PhieuNhapService → ReceivingRepository → PostgreSQL`.
Adapter persistence hiện hữu là `SqlAlchemyPhieuNhapRepository`.
Luồng audit: `PhieuNhapService → AuditService → SqlAlchemyAuditRepository → PostgreSQL`.
Đường ghi tồn: service điều phối port inventory → repository inventory → PostgreSQL.

- Router chỉ HTTP/schema/actor/dependency/response; không SQL hoặc chính sách kho.
- Service kiểm tra quyền, nguồn, trạng thái, điều kiện ghi nhận và điều phối audit/
  inventory. Comment/docstring chỉ rõ UC-20/21/22 và liên kết tới spec này.
- Repository chỉ đọc/ghi/khóa dữ liệu; không HTTP hoặc tự quyết định quyền nghiệp vụ.
- Một AsyncSession/transaction cho phiếu, chi tiết, stock, ledger và audit, một commit;
  service audit/repository/inventory không commit độc lập. Giữ cơ chế rollback hiện có.
- Q5 cho phép phần nhận hàng inventory và metadata audit tối thiểu để chạy v4;
  không chuyển toàn inventory, MatHang/Catalog/cache hoặc sản xuất sang v4 trong tác vụ.
  Không tạo bảng tồn cũ hoặc ORM trùng owner để chiều theo nhánh legacy.
- Kiểm tra source và tránh chu trình phụ thuộc khi lập plan; không tự tạo abstraction
  ngoài nhu cầu. Ranh giới khóa/conditional update và adapter cụ thể sẽ trình riêng.
- DB ứng dụng, SQL bootstrap/seed/migration, frontend và tích hợp E2E sản xuất/hủy/
  kiểm tra giữ hàng qua API legacy ngoài phạm vi. Dùng fixture raw v4 chỉ chứng minh
  bất biến dữ liệu, không thay cho nghiệm thu toàn luồng sản xuất.
- Sequence phieu_nhap và sáu PNG đã cập nhật cùng tác vụ, phản ánh sáu endpoint
  thực tế. Inventory legacy ngoài đường nhận vẫn được ghi rõ chưa nghiệm thu v4.

## 7. Acceptance Criteria backend bổ sung

AC gốc của ba UC được giữ nguyên. Các mã GR-AC bổ sung cách kiểm chứng backend;
phần frontend/confirmation dialog và API khác được ghi rõ thay vì mặc định đạt.

| Mã | Given | When | Then |
|---|---|---|---|
| GR-AC-01 — Quyền | QLK, NV, QTV, account khóa/token cũ | Gọi sáu endpoint hoặc service | Chỉ QLK hoạt động được phép; kiểm role/account từ DB, không tin claim cũ |
| GR-AC-02 — Input v4 | NCC/ngày/giá/lượng hoặc field server sai | Tạo/sửa | Reject field thừa, null không hợp lệ, money string/float/bool/âm, tổng quá BIGINT; không ghi một phần |
| GR-AC-03 — Chỉ LK/không trùng | Phiếu chứa TP hoặc lặp một LK | Lưu nháp | TP bị chặn nghiệp vụ, LK lặp bị chặn cấu trúc; không tạo phiếu/audit thành công |
| GR-AC-04 — Tạo nháp | Tồn khung 10 và nội dung nhập 50 | Lưu nháp | Phiếu/dòng/tổng/audit đúng, mã/actor server cấp; tồn 10, giữ/ledger không đổi |
| GR-AC-05 — Sửa nháp | Phiếu nháp có tag đúng | PATCH nội dung hoặc PATCH không đổi | Thay đổi hợp lệ cập nhật tổng/metadata/tag và audit trước-sau; no-op không ghi audit; kho không đổi |
| GR-AC-06 — Xóa | Phiếu nháp hoặc hoàn tất | DELETE với tag đúng | Chỉ nháp được xóa, audit giữ snapshot/code; hoàn tất bị chặn; không xóa ledger/audit |
| GR-AC-07 — Hoàn tất | Nháp nhập 50, tồn10, có giữ sẵn | QLK hoàn tất | Phiếu hoàn tất, tồn60, giữ/GiuHang không đổi, available tăng50; ledger dương +50 có tồn sau60 |
| GR-AC-08 — Giá nhập | Đơn giá nhập khác giá danh mục | Lưu/hoàn tất/xem lại | Tổng theo giá thực tế, JSON integer; không đổi giá danh mục hoặc giá phiếu đã hoàn tất |
| GR-AC-09 — Độc lập SX | Yêu cầu đang chờ bổ sung và có giữ hàng | Hoàn tất nhập | Yêu cầu/nhu cầu/giữ không đổi; không tự kiểm tra/cấp/giữ thay NV |
| GR-AC-10 — Stale/ABA | Phiếu bị sửa, kể cả A→B→A | Sửa/xóa/hoàn tất bằng tag cũ | 412 dưới cùng khóa/TX; không ghi, tag mới gắn phiên bản thực tế |
| GR-AC-11 — Retry | Phiếu đã hoàn tất/ledger đúng | Hoàn tất lại với tag cũ đúng format | Resource/ledger cũ, replay=true; không ghi lần hai; missing428, weak/wildcard/multiple412 |
| GR-AC-12 — Cùng phiếu | Hai session cùng hoàn tất hoặc sửa/xóa cạnh tranh | Xử lý thật trên PostgreSQL | Một thứ tự hợp lệ, cộng tồn một lần, không mất cập nhật/ledger/audit trùng |
| GR-AC-13 — Rollback | Đang ghi trạng thái/stock/ledger/audit | Lỗi bước ghi hoặc commit | Header/dòng/metadata/tồn/ledger/audit cùng rollback; không công bố số dư rollback |
| GR-AC-14 — Số dư/dải | Tồn lệch ledger hoặc cộng quá INTEGER | Hoàn tất | 409, không tự sửa lệch hoặc cộng một phần |
| GR-AC-15 — GET read-only | Phiếu và kho/audit đã có | GET list/detail | Không INSERT/UPDATE/DELETE; representation/ETag và trang/count nhất quán |
| GR-AC-16 — Bộ lọc | Nhiều NCC/người/ngày/trạng thái, sort trùng | QLK tìm/lọc/phân trang | AND/count đúng, ngày VN đúng biên, literal %/_, ID phụ ổn định, [] hợp lệ, Q3 đúng |
| GR-AC-17 — Metadata | Nháp và hoàn tất đã lưu | Đọc resource | Đủ actor/timestamp/version; UTC/Z, ngày DATE, tiền int, không hash/token |
| GR-AC-18 — Audit | Tạo/sửa/xóa/hoàn tất, kể cả lỗi/replay/no-op | Đọc lịch sử hoặc kiểm chứng persistence | Thành công có actor/state/snapshot đúng; no-op/replay không thêm audit; lỗi rollback; lịch sử bất biến |
| GR-AC-19 — Mapping/mã | PostgreSQL mới/trống từ init.sql | Reflection/trigger/cấp mã đồng thời/hết dải | Đúng kiểu/null/default/FK/check/index/Identity; không mã trùng/reuse; hoàn tất/dòng/ledger/audit được bảo vệ |
| GR-AC-20 — NCC hiện tại | NCC đã có phiếu cũ rồi được sửa | Đọc liên kết phiếu/NCC | ncc_id vẫn tham chiếu NCC hiện tại; không snapshot NCC vào phiếu; hiển thị UI UC-44 hoãn |
| GR-AC-21 — Chung mặt hàng | Hai phiếu cùng LK, có GiuHang nguồn khác | Hai session hoàn tất | Tồn tăng đúng tổng hai phiếu, không lost update, giữ nguồn khác nguyên vẹn |
| GR-AC-22 — Giới hạn | Sáu route hiện có và request ngoài hợp đồng | Gọi API | Chỉ sáu route, /receiving không phục hồi, không thêm duyệt/ticket/điều chỉnh; query/header/status đúng |

## 8. Truy vết triển khai và kiểm chứng

Prefix mọi endpoint: `/api/v1/phieu_nhap`. Owner service:
[`PhieuNhapService`](../../../backend/app/modules/phieu_nhap/service.py);
owner HTTP: [router](../../../backend/app/modules/phieu_nhap/router.py).
S = [test service](../../../backend/tests/test_phieu_nhap_service.py),
A = [test API](../../../backend/tests/test_phieu_nhap_api.py),
P = [test PostgreSQL](../../../backend/tests/test_phieu_nhap_postgres.py).
Các tên test dưới đây là symbol thực tế; mã UC/GR-AC nằm trong tên test.

| UC / spec | Endpoint → service | AC | Test |
|---|---|---|---|
| [UC-20](UC-20.md) | POST collection → create_receipt | AC-1–3; GR-AC-01–04/08/17–19 | A.lifecycle, A.invalid_create; S.money/quantity; P.mapping/concurrent_codes |
| UC-20 | PATCH /{id} → patch_receipt | AC-2–4; GR-AC-02/03/05/10/13 | A.patch_noop_aba_and_delete; P.audit_failure/complete_vs_mutation |
| UC-20 | DELETE /{id} → delete_receipt | AC-4–5; GR-AC-06/10/13/18/19 | A.patch_noop_aba_and_delete/completed_receipt_cannot_change; P.audit_failure |
| [UC-21](UC-21.md) | POST /{id}/hoan_tat → complete_receipt | AC-2–3/5; GR-AC-07/08/10–14/17–19/21 | A.lifecycle; P.two_completes/every_write_rolls_back/two_receipts_same_item |
| UC-21 | Đóng hộp xác nhận → không gọi service | AC-1 | UI hoãn; API chỉ chứng minh lưu/đọc nháp không đổi kho |
| UC-21 | POST /{id}/hoan_tat → complete_receipt | AC-4; GR-AC-09 | A.lifecycle đối chiếu YCSX/NhuCau/GiuHang; E2E sản xuất hoãn Q5 |
| [UC-22](UC-22.md) | GET collection/detail → list_receipts/get_receipt | AC-1–2; GR-AC-01/15–17/20/22 | A.db_role/http_contract; P.readonly_filters/count_and_page/supplier |

### Từng GR-AC và test tương ứng

**Đạt phần backend** của 22 GR-AC dưới đây trong lần chạy thực tế 80 pass, 0 skip.
Ký hiệu ở bảng endpoint phía trên là tên rút gọn; bảng này ghi symbol đầy đủ.

| GR-AC | Test đã chạy (file S/A/P ở trên) |
|---|---|
| GR-AC-01 | A.test_uc20_uc22_gr_ac01_all_routes_use_current_db_role; S.test_uc20_uc21_uc22_gr_ac01_direct_service_rejects_unauthorized_actor |
| GR-AC-02 | S.test_uc20_gr_ac02_money_is_strict_integer_vnd; S.test_uc20_gr_ac02_quantity_is_positive_strict_integer; A.test_uc20_gr_ac02_03_invalid_create_is_atomic |
| GR-AC-03 | A.test_uc20_gr_ac02_03_invalid_create_is_atomic |
| GR-AC-04 | A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle |
| GR-AC-05 | A.test_uc20_gr_ac05_06_10_patch_noop_aba_and_delete |
| GR-AC-06 | A.test_uc20_gr_ac06_completed_receipt_cannot_change; P.test_uc20_uc21_gr_ac19_posted_data_immutable |
| GR-AC-07 | A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle |
| GR-AC-08 | A.test_uc20_uc21_gr_ac02_08_money_boundaries_and_code_month; A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle |
| GR-AC-09 | A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle (fixture v4; E2E API sản xuất chưa nghiệm thu) |
| GR-AC-10 | A.test_uc20_gr_ac05_06_10_patch_noop_aba_and_delete; P.test_uc21_gr_ac10_conditional_update_rejects_changed_version; P.test_uc20_uc21_gr_ac10_12_complete_vs_mutation |
| GR-AC-11 | P.test_uc21_gr_ac11_replay_header_and_sql_no_writes; P.test_uc21_gr_ac11_incomplete_posting_no_repair; S.test_uc21_gr_ac11_missing_validator; S.test_uc21_gr_ac11_invalid_validator |
| GR-AC-12 | P.test_uc21_gr_ac12_two_completes_post_once; P.test_uc20_uc21_gr_ac10_12_complete_vs_mutation |
| GR-AC-13 | P.test_uc21_gr_ac13_every_write_rolls_back; P.test_uc20_gr_ac13_audit_failure_rolls_back_draft_mutation |
| GR-AC-14 | P.test_uc21_gr_ac14_inconsistent_data_is_not_repaired; P.test_uc21_gr_ac14_integer_stock_overflow_with_valid_ledger |
| GR-AC-15 | P.test_uc22_gr_ac15_16_readonly_filters_dates_ties; P.test_uc22_gr_ac15_count_and_page_share_snapshot_during_insert |
| GR-AC-16 | P.test_uc22_gr_ac15_16_readonly_filters_dates_ties; A.test_uc21_uc22_gr_ac10_11_16_22_http_contract |
| GR-AC-17 | A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle |
| GR-AC-18 | A.test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle; A.test_uc20_gr_ac05_06_10_patch_noop_aba_and_delete; P.test_uc20_gr_ac13_audit_failure_rolls_back_draft_mutation |
| GR-AC-19 | P.test_uc20_gr_ac19_mapping_reflects_bootstrap; P.test_uc20_uc21_gr_ac19_posted_data_immutable; P.test_uc20_gr_ac19_concurrent_codes; P.test_uc20_gr_ac19_code_exhaustion_is_atomic |
| GR-AC-20 | P.test_uc22_gr_ac20_supplier_is_live_reference (backend đạt; hiển thị UI UC-44 hoãn) |
| GR-AC-21 | P.test_uc21_gr_ac21_two_receipts_same_item |
| GR-AC-22 | A.test_uc21_uc22_gr_ac10_11_16_22_http_contract |

## 9. Bàn giao và giới hạn

- Spec/Q1–Q5 và plan/task đã duyệt; T01–T12 đã thực hiện, chi tiết lệnh/kết quả ở [PLAN](PLAN.md#kết-quả-thực-hiện-t01t12).
- [Sequence sáu endpoint và PNG](../../../docs/sequence/phieu_nhap.md) và
  [request/response HTTP thực tế](../../../docs/examples/goods-receipt-http.json).
- Toàn suite: **80 pass, 8 fail**; tám lỗi fixture nhân viên thiếu `VaiTroRead.mo_ta`
  đã có ở baseline, không sửa kỳ vọng/skip hoặc sửa module ngoài phạm vi.
- Chưa nghiệm thu UI UC-21 AC-1, UI NCC UC-44 R8 hoặc E2E sản xuất qua API legacy;
  fixture chỉ chứng minh yêu cầu/nhu cầu/giữ hàng không bị phiếu nhập làm thay đổi.
- Auth giữ cơ chế `pwdv` hiện có, chưa nâng toàn bộ login version v4. Inventory
  đọc/xuất/điều chỉnh legacy và toàn UC-43 không được refactor trong tác vụ Q5.
- Không thay SQL/bootstrap/seed/migration, DB ứng dụng, frontend hoặc tự merge nhánh.
  Không commit/push. API mới yêu cầu DB schema v4; không tự cập nhật database đang chạy.
