# Đặc tả backend Goods Issue — UC-34 đến UC-40

**SPEC APPROVED — dev đã duyệt spec tổng thể và Q1–Q6 ngày 14/11/2026.**
[Plan và danh sách task](PLAN.md) đã được duyệt; đã triển khai backend v4 và kiểm
thử PostgreSQL riêng. Kết quả và giới hạn tại mục 7–8. Phần khảo sát mục 2 lưu
baseline trước triển khai, không mô tả code hiện tại. Không sửa SQL hoặc DB ứng dụng.

Phạm vi: cả bảy UC trong thư mục `goods_issue`, chỉ backend, triển khai tại module
`backend/app/modules/phieu_xuat/`. `goods_issue` là tên bounded context trong tài liệu,
không tạo thêm module runtime trùng trách nhiệm. Frontend để sau.

## 1. Mục tiêu và nguồn đối chiếu

Phiếu xuất lấy nguyên lượng đã chốt cho yêu cầu sản xuất, chỉ xuất khi QLK duyệt;
mỗi yêu cầu tối đa một phiếu mỗi loại. Tồn, giữ hàng, giá xuất, ledger, trạng thái
phiếu/yêu cầu và audit phải nhất quán, không trừ kho hai lần hoặc âm tồn.

| Nguồn đã đọc | Nội dung sử dụng |
|---|---|
| [UC-34](UC-34.md), [UC-35](UC-35.md), [UC-36](UC-36.md) | NV lập/gửi linh kiện, QLK duyệt/từ chối, gửi lại trực tiếp |
| [UC-37](UC-37.md), [UC-38](UC-38.md), [UC-39](UC-39.md) | Thành phẩm của yêu cầu xuất giao, điều kiện hoàn thành sản xuất, đóng yêu cầu |
| [UC-40](UC-40.md) | Danh sách riêng QLK; bộ lọc được dev chốt tại Q3 |
| [BR giai đoạn 1](../../business_requirements/BR-GIAIDOAN1.md) | BR-001/004/007/008/010/011/012/013/014/015/016 |
| [Data model v4](../../entity_model/data_model_v4.md) §3.4–3.8; [entity model](../../entity_model/entity_model.md) | Yêu cầu, nhu cầu chốt, giữ hàng, phiếu xuất, tiền và nguồn ledger |
| [init.sql](../../../infra/postgres/init.sql) | Schema v4 thực trong repository: PascalCase, Identity, BIGINT, FK/check/index/trigger |
| [UC-12](../catalog/UC-12.md) | R6/R7 có cách hiểu cần chốt; dev đã chọn Q6 bên dưới |
| [UC-28](../production/UC-28.md) | Ràng buộc hủy yêu cầu; phần E2E sản xuất giữ hoãn theo Q5 |
| [UC-43](../audit/UC-43.md) | Actor, trạng thái, snapshot trước/sau, lý do; audit cùng transaction |
| Source `phieu_xuat`, `inventory`, `mat_hang`, `audit`, `san_xuat`, dependencies/core và [sequence hiện tại](../../../docs/sequence/phieu_xuat.md) | Hiện trạng v3, phần cần thay đổi và các caller nội bộ cần giữ |

Nguồn đích đã được dev chốt là UC/BR/model/SQL **v4**, không dùng quy tắc contract v3
trong code để thay thế. Nếu phát hiện thêm mâu thuẫn nghiệp vụ chưa thuộc Q1–Q6 thì
dừng phần phụ thuộc và hỏi dev; không tự thay spec để làm test pass.

## 2. Khảo sát chỉ đọc

### 2.1. Mốc checkout và stack

- Khảo sát bắt đầu trên `main`, HEAD `f461ecd`; sau lần ngắt dev chuyển sang
  `feature/phieu_xuat`, cùng HEAD. Working tree sạch trước khi tạo spec này.
- Nhánh hiện tại chưa có source/test BOM và Catalog vừa thực hiện trên các nhánh
  khác. Không tự merge, cherry-pick, khôi phục hoặc giả định các phần đó đang có.
- Python >=3.11, FastAPI, Pydantic v2, SQLAlchemy async, asyncpg/PostgreSQL;
  manifest ở `backend/pyproject.toml`. pytest/pytest-asyncio, Ruff, mypy đã có.
- Router ghép prefix `/api/v1` tại `app/main.py`. DI tại `app/dependencies.py`.
  Actor/role/account đọc qua auth hiện có; router đã dùng require_roles.
- Module có router/schema/service/ports/repository/models/errors. Service dùng
  Transaction và port; repository dùng AsyncSession, không commit riêng.
- Audit phiếu đã đi `PhieuXuatService → AuditService → SqlAlchemyAuditRepository`.
  Cột trạng thái và mã `gui_lai` của audit chưa được đồng bộ đầy đủ trong ORM/DTO.
- Writer tồn hiện là `SqlAlchemyInventoryRepository` qua InventoryIssueWriter,
  được service phiếu điều phối trong cùng transaction. InventoryService hiện chủ
  yếu đọc; không mặc định thêm tầng/abstraction mới khi chưa có plan được duyệt.

### 2.2. Chín endpoint đang có, chưa phải hợp đồng đích v4

| Method/path hiện tại | Service | Hiện trạng / khác biệt |
|---|---|---|
| GET `/api/v1/phieu_xuat` | list_issues | QLK và NV được đọc list; NV lọc theo công việc được giao. UC-40/Q3 chỉ cho QLK vào list này |
| GET `/api/v1/phieu_xuat/{id}` | get_issue | QLK/NV, có kiểm tra phạm vi NV và ETag; response chưa có lý do/metadata xử lý v4 |
| POST `/api/v1/phieu_xuat` | create_issue | QLK tạo; client gửi dòng/số lượng, loại vật tư dùng nguồn lệnh; khác Q1 |
| PATCH `/api/v1/phieu_xuat/{id}` | patch_issue | Cho đổi chi tiết nháp; phải gỡ theo Q2 |
| DELETE `/api/v1/phieu_xuat/{id}` | delete_issue | Xóa nháp công khai; phải gỡ theo Q2, giữ thao tác xóa nháp nội bộ khi hủy yêu cầu |
| POST `/api/v1/phieu_xuat/{id}/gui` | transition(gui) | QLK gửi, chỉ nhap → cho_duyet; chưa có NV gửi lại tu_choi → cho_duyet |
| POST `/api/v1/phieu_xuat/{id}/duyet` | approve | QLK duyệt, có chốt giá/ledger/replay; chưa kết thúc giữ hàng v4 |
| POST `/api/v1/phieu_xuat/{id}/tu_choi` | transition(tu_choi) | QLK từ chối có audit lý do; row/response chưa lưu metadata từ chối v4 đầy đủ |
| POST `/api/v1/phieu_xuat/{id}/ve_nhap` | transition(ve_nhap) | QLK đưa phiếu về nháp; phải gỡ theo Q2 |

Giữ tên endpoint nào, request/response cuối cùng và mã 404/405 khi gỡ route sẽ trình
chi tiết ở plan. Không coi bảng khảo sát là hợp đồng v4 đã được triển khai.

### 2.3. Chênh lệch dữ liệu và phụ thuộc

| Phần | Source hiện tại | UC/model/SQL v4 đã chốt |
|---|---|---|
| Loại / nguồn | xuat_vat_tu gắn LenhSanXuat, TP gắn YeuCauSanXuat | xuat_linh_kien / xuat_thanh_pham đều gắn YeuCauSanXuat; SQL v4 không có LenhSanXuat |
| Chi tiết | Client gửi mặt hàng/số lượng; chỉ chặn vượt nhu cầu, vẫn có thể thiếu dòng hoặc xuất ít hơn | Hệ thống lấy đủ, đúng toàn bộ nhu cầu đã chốt hoặc toàn bộ số thành phẩm yêu cầu; không sửa/từng phần |
| Người lập | QLK; nhan_vien_id lấy actor quản lý | NV được giao yêu cầu; người lập và người xử lý là hai thông tin khác nhau |
| Metadata phiếu | ORM thiếu updated_at, gui_at, nguoi_xu_ly_id, xu_ly_at, ly_do_tu_choi, phien_ban | SQL có các cột này cùng ràng buộc trạng thái/metadata; mỗi yêu cầu một phiếu mỗi loại |
| Giữ hàng | Writer trừ MatHang.so_luong_ton; chưa kết thúc GiuHang/giảm so_luong_dang_giu | Chỉ dùng giữ hàng của đúng yêu cầu; kết thúc giữ khi duyệt, không chiếm phần của yêu cầu khác |
| MatHang | ORM chưa có so_luong_dang_giu/so_luong_con_dung; còn loại v3 | SQL v4 có hai loại LK/TP, số đang giữ và cột còn dùng được tự sinh |
| Ledger | INSERT thiếu so_luong_ton_sau, còn mã xuat_vat_tu; ORM StockMovement map bảng chữ thường/nguồn điều chỉnh cũ | GiaoDichKho PascalCase, so_luong_ton_sau bắt buộc, xuat_linh_kien; đúng một FK nguồn và nguồn phải đã duyệt |
| Sản xuất | Source/caller còn lệnh, trạng thái v3; chưa có nhu cầu/giữ hàng v4 đầy đủ | Đọc nhu cầu chốt, loại yêu cầu, nhân viên được giao, chứng từ hoàn thành đã duyệt; không tính lại BOM |
| Audit | CreationAudit/ORM chưa có trạng thái trước/sau; read enum thiếu gui_lai | SQL v4 có hai trạng thái, mã gui_lai và audit bất biến |

Các chênh lệch này được xác định bằng source/SQL, chưa phải kết quả chạy trên DB
ứng dụng. Không sửa SQL ngược theo ORM cũ và không dùng metadata.create_all để suy
ra đã tương thích PostgreSQL. Không tự cập nhật database có dữ liệu.

### 2.4. Kết quả kiểm tra nền đã chạy

- Import app/OpenAPI thành công, xác nhận **9 endpoint phiếu xuất**. Không chạy
  lifespan, không kết nối database ứng dụng. Import được không chứng minh API chạy đúng.
- `ruff check backend/app/modules/phieu_xuat`: pass.
- `pytest tests -q --tb=line` tại backend: **8 fail**, đều ở fixture
  `test_nhan_vien_create_code.py:86` thiếu `VaiTroRead.mo_ta`. Không sửa lỗi nền này.
- Checkout hiện chỉ có test nhân viên, chưa có test phiếu xuất/BOM/Catalog.
  Chưa kiểm chứng PG/transaction/concurrency/ledger/holds của phiếu xuất.
- Structure map chỉ đọc không phát hiện cycle trong phần phiếu xuất; các báo cáo
  trùng tên/hình dạng là gợi ý review, không phải yêu cầu refactor ngoài phạm vi.

## 3. Phạm vi nghiệp vụ đích

### 3.1. Actor, trigger và tiền điều kiện

QTV = quan_tri_vien, QLK = quan_ly, NV = nhan_vien. Mọi actor cần đăng nhập và tài
khoản đang hoạt động. Actor/người xử lý lấy từ JWT đã xác thực và tài khoản hiện
tại; không nhận actor/role/người xử lý từ body. Kiểm tra quyền cả tại service.

| UC | Actor / trigger | Tiền điều kiện chính |
|---|---|---|
| UC-34 | NV được giao lưu/gửi/gửi lại phiếu LK | Yêu cầu dang_thuc_hien, so_luong_can_san_xuat > 0, nhu cầu chốt và giữ LK hợp lệ |
| UC-35 | QLK xác nhận duyệt LK | Phiếu cho_duyet, nguồn vẫn hợp lệ, đủ tồn và đúng phần giữ của yêu cầu |
| UC-36 | QLK từ chối LK | Phiếu cho_duyet, lý do không trắng |
| UC-37 | NV được giao hoặc QLK lưu/gửi/gửi lại phiếu TP | Yêu cầu xuat_giao đang thực hiện; không cần sản xuất hoặc chứng từ hoàn thành đã duyệt; đủ phần TP giữ khi duyệt |
| UC-38 | QLK xác nhận duyệt TP | Phiếu cho_duyet, xuất toàn bộ số yêu cầu, đủ tồn và giữ TP của đúng yêu cầu |
| UC-39 | QLK từ chối TP | Phiếu cho_duyet, lý do không trắng |
| UC-40 | QLK xem/lọc danh sách, mở chi tiết | Không tạo tác động ghi dữ liệu |

- QLK được lập/gửi phiếu thành phẩm, duyệt và từ chối. Lập/gửi phiếu linh kiện thuộc NV được giao. QTV không truy cập phiếu xuất.
- NV không vào danh sách QLK. NV chỉ đọc chi tiết và lập/gửi phiếu thuộc yêu cầu
  hiện được giao cho mình; không chỉ so actor với nhan_vien_id người lập phiếu.
- Yêu cầu đã hủy/hoàn thành không được tiếp tục tạo/gửi/duyệt mới. Riêng replay
  phiếu đã duyệt xử lý theo Q4, không bị coi là một lần xuất mới.
- Theo Q6, yêu cầu đã gửi hợp lệ trước khi TP bị ngừng vẫn được lập/gửi/duyệt phiếu
  để kết thúc theo dữ liệu đã chốt. Không dùng is_active hiện tại để chặn luồng cũ,
  không vì thế cho tạo/gửi yêu cầu sản xuất mới với TP đã ngừng.

### 3.2. Main flow theo từng UC

**UC-34 — Lập và gửi linh kiện**

1. NV mở yêu cầu được giao; hệ thống kiểm tra nguồn đang thực hiện và cần sản xuất.
2. Xác định toàn bộ dòng từ NhuCauLinhKien đã chốt; không đọc BOM hiện hành để tính lại.
3. NV lưu: hệ thống tạo nháp, mã tự cấp, người lập từ actor, nội dung đúng đủ nhu cầu;
   chưa có giá xuất/tổng tiền, không đổi tồn/giữ/ledger; ghi audit tạo.
4. Sau khi NV xem và xác nhận gửi, hệ thống kiểm tra lại quyền/nguồn/phiên bản,
   chuyển nhap → cho_duyet, ghi audit gui; tồn/giữ/ledger không đổi.
5. Nếu bị từ chối, NV xem lý do và xác nhận gửi lại cùng phiếu: tu_choi → cho_duyet,
   audit gui_lai; không sửa nội dung, không qua nháp, không tạo phiếu thay thế.

**UC-35 — Duyệt linh kiện**

1. QLK mở phiếu cho_duyet và xác nhận tác động kho.
2. Trong ranh giới nguyên tử, kiểm tra lại phiếu/nguồn/phiên bản, toàn bộ chi tiết,
   tồn và phần giữ của chính yêu cầu; không dùng hàng đang giữ của yêu cầu khác.
3. Chốt đơn giá mỗi dòng từ MatHang.don_gia tại lúc duyệt; tính tiền integer VND.
4. Trừ đúng lượng LK; giảm phần đang giữ tương ứng và chuyển GiuHang đó sang da_xuat,
   gắn phiếu/thời điểm kết thúc. Ghi giao dịch âm đúng nguồn và số tồn sau.
5. Ghi phiếu da_duyet, người/thời điểm xử lý và audit; mọi thay đổi cùng thành công
   hoặc rollback. Yêu cầu từ đây không được hủy; không tự bắt đầu sản xuất thay NV.

**UC-36 — Từ chối linh kiện**

1. QLK nhập lý do cho phiếu đang chờ duyệt.
2. Kiểm tra quyền, phiên bản và trạng thái; lý do không được null/trắng.
3. Chuyển sang tu_choi, lưu lý do/người/thời điểm xử lý và audit trước/sau.
4. NV được giao đọc được lý do và có thể gửi lại; không trả LK về khả dụng,
   không thay tồn/giữ/ledger và không mở thao tác về nháp.

**UC-37 — Lập và gửi thành phẩm**

1. NV mở yêu cầu xuat_giao được giao đang thực hiện hoặc QLK mở chi tiết yêu cầu xuat_giao đang thực hiện; cấm nguồn nhap_kho.
2. Kiểm tra không cần sản xuất, hoặc ChungTuHoanThanhSx của đúng yêu cầu đã da_duyet.
3. Hệ thống tạo nháp một dòng TP bằng đúng YeuCauSanXuat.so_luong; không chỉ xuất
   phần sản xuất thêm. Nguồn giữ có thể gồm TP có sẵn và TP vừa sản xuất cho yêu cầu.
4. NV được giao hoặc QLK xác nhận gửi/gửi lại. Chưa trừ tồn, chưa kết thúc giữ, chưa hoàn thành
   yêu cầu; giữ một phiếu cho yêu cầu/loại, không xuất từng phần.

**UC-38 — Duyệt thành phẩm**

1. QLK mở phiếu TP cho_duyet, kể cả phiếu do mình lập, xem và xác nhận tác động kho.
2. Kiểm tra lại nguồn xuat_giao, toàn bộ lượng yêu cầu, điều kiện hoàn thành sản xuất,
   tồn và các khoản giữ TP đúng yêu cầu.
3. Chốt giá, trừ đúng toàn bộ TP, kết thúc các khoản giữ tương ứng; ghi ledger âm
   có FK duy nhất theo dòng phiếu, số tồn sau, actor và thời điểm.
4. Cùng transaction, phiếu da_duyet và yêu cầu hoan_thanh có thời điểm hoàn thành,
   audit đầy đủ. Không đóng yêu cầu sớm ở bước lưu/gửi/từ chối.

**UC-39 — Từ chối thành phẩm**

1. QLK nhập lý do cho phiếu TP cho_duyet.
2. Kiểm tra quyền/phiên bản/trạng thái/lý do; chuyển tu_choi và ghi metadata/audit.
3. Tồn và giữ TP không đổi; yêu cầu chưa hoàn thành; NV được giao hoặc QLK gửi lại trực tiếp theo UC-37.

**UC-40 — Tra cứu**

1. QLK mở danh sách phiếu xuất cả hai loại.
2. Lọc AND theo Q3; phân trang/sort ổn định bằng ID phụ, dữ liệu rỗng vẫn là kết quả hợp lệ.
3. Mở chi tiết để xem lý do/trạng thái/giá đã chốt và chọn thao tác đang được phép.
4. GET không thay trạng thái, giữ hàng, số dư, ledger hoặc audit thành công.

### 3.3. Chuyển trạng thái, alternative flows và exceptions

| Thao tác | Chuyển trạng thái | Tác động kho / audit |
|---|---|---|
| NV lưu phiếu mới | Chưa có → nhap | Không đổi tồn/giữ; audit tao |
| NV gửi lần đầu | nhap → cho_duyet | Không đổi tồn/giữ; audit gui |
| NV gửi lại | tu_choi → cho_duyet | Giữ nguyên nội dung/tồn/giữ; audit gui_lai |
| QLK từ chối | cho_duyet → tu_choi | Bắt buộc lý do; không đổi tồn/giữ; audit tu_choi |
| QLK duyệt | cho_duyet → da_duyet | Chốt giá, xuất kho/kết thúc giữ/ledger/audit nguyên tử; TP đóng yêu cầu |
| QLK gọi duyệt lại theo Q4 | da_duyet → da_duyet | Trả kết quả cũ và da_ghi_so_truoc_do=true, không ghi lại |
| Hủy yêu cầu qua nghiệp vụ nội bộ | Nháp bị xóa; chờ duyệt → tu_choi | BR-013/UC-28; không được hủy nếu đã xuất, Q5 giới hạn E2E bên dưới |

- Sai quyền/ngoài phạm vi được giao: từ chối, không lộ dữ liệu hay thực hiện ghi.
- Nguồn không tồn tại, sai loại, chưa đủ điều kiện, đã có phiếu, không đúng trạng
  thái hoặc lượng/giữ/tồn không khớp: từ chối toàn bộ, không sửa dữ liệu để tự chữa.
- Không chấp nhận dòng thiếu/thừa, lượng ít hơn/nhiều hơn, mã/actor/giá/trạng thái
  do client tự đặt. Hệ thống sở hữu nội dung phiếu, không có sửa chi tiết tại chỗ.
- Phiếu thay đổi trong lúc xác nhận: yêu cầu tải lại với validator mới. Q4 là ngoại
  lệ đã chốt riêng cho retry duyệt phiếu đã ghi sổ; không áp dụng cho gửi/từ chối.
- Đóng hộp xác nhận: frontend không gửi lệnh ghi, không tạo tác động. Backend không
  tự tạo workflow xác nhận/token mới ở giai đoạn spec; chi tiết HTTP trình trong plan.
- Lỗi giữa chốt giá, cập nhật phiếu, trừ tồn, kết thúc giữ, ledger, đóng yêu cầu hoặc
  audit/commit: rollback toàn bộ. Không trả thành công nếu lưu một phần.

## 4. Quy tắc dùng chung, phân tầng và giới hạn

### 4.1. Nguyên tử và bảo toàn dữ liệu

- Dữ liệu tồn nằm ở MatHang, không tạo lại/đọc TonKho cũ cho luồng xuất này.
  Tồn thực tế và đang giữ không âm, còn dùng được là cột sinh; không ghi trực tiếp
  số khả dụng. Duyệt giảm tồn và đang giữ theo cùng lượng thuộc đúng yêu cầu.
- Kiểm tra giữ hàng theo yêu cầu + mặt hàng + loại giữ; không giải phóng/ghi da_xuat
  cho khoản giữ của nguồn khác. Khi chưa duyệt, giữ không đổi kể cả từ chối/gửi lại.
- Mỗi dòng xuất có đúng một ledger âm với FK chi_tiet_phieu_xuat_id, loại tương ứng,
  so_luong_ton_sau chính xác; không nguồn điều chỉnh, không duplicate ledger.
- Giá/tổng NULL trước duyệt; sau duyệt integer VND không âm, tổng = lượng × giá,
  kiểm tra dải BIGINT và tổng phiếu. Giá về sau không viết lại chứng từ đã duyệt.
- Phiếu, dòng, giá đã duyệt bất biến; không hoàn tác xuất, xuất từng phần, FIFO,
  bình quân, giao hàng hoặc hóa đơn. Không chỉnh nhu cầu chốt hoặc tính lại BOM.
- Mã PX-YYYYMM-NNNNNN do hệ thống cấp; mã không trùng/tái dùng, Identity do SQL v4.
  Cách giữ mã/tháng/khóa và lỗi hết dải sẽ đối chiếu trong plan, không đổi bootstrap.

### 4.2. Luồng chạy và truy vết

```text
Router → PhieuXuatService / Use Case → Repository → PostgreSQL
                         └────────→ AuditService → SqlAlchemyAuditRepository
```

- Router nhận HTTP/schema/actor/dependency, gọi service, trả response. Không SQL
  hoặc quyết định lượng/nguồn/quyền nghiệp vụ trong router.
- Service kiểm tra actor, điều kiện, trạng thái, ETag/đồng thời, điều phối nghiệp vụ
  giữ hàng/tồn/ledger và audit. Mỗi service/action ghi nguồn UC tương ứng.
- Repository chỉ truy cập dữ liệu; không HTTP/commit hoặc tự chọn chính sách nghiệp vụ.
- Cùng transaction cho toàn bộ thay đổi cần nguyên tử; không nested commit của
  Inventory/Audit. Giữ port công khai cho các caller sản xuất theo Q5.
- Spec là tài liệu truy vết, không phải thành phần runtime. Chuỗi cần kiểm chứng:
  Endpoint → service → UC/spec → test theo AC. Chưa tạo abstraction mới ở bước này.

### 4.3. Hợp đồng HTTP và thay đổi tương thích cần trình trong plan

- Giữ envelope/request_id và cơ chế xác thực hiện có; schema chỉ validation cấu trúc,
  service xử lý điều kiện phụ thuộc DB. Mã lỗi nền 401/403/404/409/422 và 428/412.
- Q1 thay quyền, mã loại, nguồn và cách nhận chi tiết. Không âm thầm nhận payload
  v3 rồi chuyển thành v4 theo suy đoán; các input không còn được hỗ trợ phải rõ ràng.
- Gỡ ba route công khai theo Q2, giữ route lấy chi tiết cho NV có quyền và list riêng
  QLK. Chi tiết đường dẫn/cách gửi lại, DTO/response mới và OpenAPI trình ở plan.
- GET detail trả strong ETag. Mutation dùng validator sau khi khóa/đọc lại resource;
  thiếu/blank 428, stale/weak/wildcard/nhiều validator 412 theo quy ước đã dùng.
- Với retry duyệt Q4: vẫn xác thực/phân quyền và cần một If-Match đúng định dạng;
  được dùng tag cũ khi phiếu đã duyệt hợp lệ, nhận kết quả cũ. Thiếu/blank 428,
  weak/wildcard/nhiều validator/sai định dạng 412; không bỏ qua quyền khi replay.
- Body/tag phải phát hiện được vòng từ chối → gửi lại dù trạng thái quay về giá trị
  cũ; SQL v4 có phien_ban. Công thức ETag và metadata response chốt trong plan.
- Q3: q tìm literal mã phiếu không phân biệt hoa/thường, %/_ không wildcard; AND
  loại/trạng thái/nhân viên lập/yêu cầu/ngày tạo. Ngày theo Asia/Ho_Chi_Minh, gồm cả
  hai đầu ngày. Giữ sort id/created_at/ma_phieu_xuat và dạng -, mặc định -created_at,
  ID ASC phụ; page 1/page_size 20/max 100. Query lạ/lặp, ngày/khoảng/sort sai bị từ chối.

### 4.4. Phụ thuộc tối thiểu Q5

Được đưa vào plan: phần ORM/projection thực sự cần của yêu cầu, nhu cầu, chứng từ
hoàn thành, GiuHang, MatHang/GiaoDichKho và metadata audit; đường ghi xuất trong
inventory cùng transaction; các tham chiếu/import/DI/caller trực tiếp cần thiết.
Tận dụng service/port hiện có, không mặc định sao chép cả module hoặc model owner.

Không tự merge BOM/Catalog, refactor toàn bộ sản xuất, sửa auth/nhân viên, frontend,
SQL/seed, dependency hoặc tạo/chạy migration. Chỉ dùng bootstrap DB test mới/trống,
không đụng database ứng dụng. Nếu phạm vi tối thiểu không đủ thì báo phụ thuộc và
chờ xác nhận, không mở rộng để làm xanh suite.

UC-35/AC-4 và các tình huống hủy/hoàn tất qua API sản xuất v4 chỉ được nghiệm thu
E2E khi module sản xuất tương thích và đã chạy thật. Test dữ liệu chốt/port/transaction
không thay cho E2E. Không giả định nhánh này đã có phần sản xuất v4 hoặc fixture BOM.

## 5. Acceptance Criteria backend bổ sung

AC gốc của bảy UC giữ nguyên. Mã GI-AC bên dưới bổ sung phần kiểm chứng backend,
chưa phải test đã tồn tại hoặc pass; các quyết định Q1–Q6 đã được dev xác nhận.

| AC | Given | When | Then |
|---|---|---|---|
| GI-AC-01 — Quyền | Role/account hiện tại có thể khác JWT cũ | Gọi endpoint hoặc service | QLK chỉ list/đọc/duyệt/từ chối; NV chỉ chi tiết/lập/gửi nguồn được giao; QTV bị chặn; account khóa/credential cũ không vượt quyền |
| GI-AC-02 — Phạm vi | Hai yêu cầu giao hai NV khác nhau | NV dùng ID nguồn/phiếu của người khác | Bị từ chối trước ghi; nhan_vien_id/người xử lý không do client đặt |
| GI-AC-03 — LK đúng đủ | Nhu cầu chốt 7 khung, 14 lốp | NV lưu nháp LK | Có đúng hai dòng 7/14, không tính lại BOM, không nhận lượng/giá tự chọn; kho/giữ/ledger không đổi |
| GI-AC-04 — Duy nhất | Yêu cầu đã có phiếu cùng loại hoặc hai request tạo đồng thời | Lưu thêm phiếu | Chỉ một phiếu hợp lệ; không chi tiết/audit thành công một phần; không dùng phiếu mới thay cho gửi lại |
| GI-AC-05 — TP đủ điều kiện | Nguồn xuat_giao, không cần sản xuất hoặc chứng từ hoàn thành đúng nguồn đã duyệt | NV lưu TP | Lượng bằng toàn bộ yêu cầu; nguồn nhap_kho/chứng từ chưa duyệt bị từ chối |
| GI-AC-06 — Không sửa nội dung | Có phiếu nháp/chờ/từ chối/đã duyệt | Gọi sửa dòng, đổi nguồn/loại, về nháp hoặc xóa công khai | Không có chức năng ghi này theo Q2; không đổi dữ liệu; xóa nháp nội bộ vẫn theo hủy yêu cầu |
| GI-AC-07 — Gửi và gửi lại | Nháp hoặc bị từ chối, NV được giao và nguồn hợp lệ | Xác nhận gửi/gửi lại | cho_duyet cùng ID/chi tiết, audit gui/gui_lai; tồn/giữ/ledger giữ nguyên |
| GI-AC-08 — Duyệt LK | Tồn khung 10, giữ 7 cho nguồn, phiếu 7 | QLK duyệt | Tồn 3, khoản giữ nguồn da_xuat/đang giữ giảm 7, ghi giá lúc duyệt, ledger -7 có tồn sau 3; không tự bắt đầu sản xuất |
| GI-AC-09 — Duyệt TP | Yêu cầu 10 xe, giữ đủ 10 gồm hàng có sẵn/vừa SX | QLK duyệt TP | Tồn giảm 10, giữ nguồn kết thúc, phiếu da_duyet, yêu cầu hoan_thanh/ghi thời điểm; giá/ledger/audit đúng |
| GI-AC-10 — Từ chối | Phiếu chờ và QLK | Từ chối với lý do trắng hoặc hợp lệ | Trắng bị chặn; hợp lệ lưu lý do/actor/thời gian/audit; kho/giữ không đổi, TP không đóng yêu cầu |
| GI-AC-11 — Metadata đọc | Phiếu bị từ chối/gửi lại/duyệt | Actor có quyền GET | Đủ lý do và trạng thái/metadata cần biết, UTC, không hash/token; không mất lý do khỏi audit khi gửi lại |
| GI-AC-12 — Xác nhận cũ | Resource thay đổi, kể cả vòng từ chối/gửi lại | Mutation dùng validator cũ | 412 và không ghi; tag/bản ghi được so dưới cùng khóa/transaction; missing 428, weak/wildcard/multiple 412 |
| GI-AC-13 — Đồng thời | Hai QLK hoặc duyệt và từ chối cùng tag | Ghi cạnh tranh từ hai session thật | Chỉ một thay đổi thắng; không âm tồn, không double ledger/giải phóng giữ/audit; request thua nhận kết quả đúng chính sách |
| GI-AC-14 — Retry đã duyệt | Phiếu đã ghi sổ, actor vẫn có quyền, một If-Match đúng định dạng có thể cũ | Gọi duyệt lại | Resource hiện tại + ID ledger cũ, da_ghi_so_truoc_do=true; không đổi tồn/giữ/giá/yêu cầu/audit lần hai |
| GI-AC-15 — Giữ hàng đúng nguồn | Hàng đang được nhiều yêu cầu giữ | Một phiếu được duyệt | Chỉ dùng/kết thúc phần giữ của nguồn; thiếu/sai khoản giữ hoặc tồn-ledger không nhất quán bị chặn, không tự sửa dữ liệu |
| GI-AC-16 — Rollback | Cần sửa phiếu/giá/tồn/giữ/ledger/yêu cầu/audit | Lỗi ở một bước ghi hoặc commit | Cùng rollback, không trạng thái hoặc audit thành công một phần; không công bố số dư bị rollback |
| GI-AC-17 — Giá bất biến | Giá MatHang đổi trước hoặc sau duyệt | Duyệt / GET phiếu đã duyệt | Dùng giá tại lúc duyệt, integer VND trong dải; phiếu cũ giữ giá đã chốt, không nhận giá từ client |
| GI-AC-18 — List | Hai loại, nhiều nguồn/NV/trạng thái/ngày, sort có giá trị trùng | QLK lọc/phân trang | AND/count đúng, ID phụ ổn định, không trùng trang tập dữ liệu tĩnh; [] hợp lệ; bộ lọc/Q3; NV/QTV không vào list |
| GI-AC-19 — Read-only | Dữ liệu kho/phiếu/audit đã có | GET list/detail | Không INSERT/UPDATE/DELETE, không đổi tồn/giữ/ledger/trạng thái; ETag và representation cùng phiên bản |
| GI-AC-20 — Yêu cầu cũ | Nguồn đã gửi hợp lệ, TP sau đó ngừng | Tiếp tục lập/gửi/duyệt theo lượng chốt | Hoàn tất nguồn cũ theo Q6; không tạo quyền lập/gửi yêu cầu mới với TP ngừng |
| GI-AC-21 — Schema/mã | PostgreSQL mới/trống dùng init.sql thực | Reflection, tạo đồng thời hoặc hết dải mã | Mapping đúng tên/kiểu/null/default/khóa/ràng buộc, code/ID server cấp, không trùng mã hay audit một phần |
| GI-AC-22 — Hủy nguồn | Đã có phiếu được duyệt, hoặc nguồn bị hủy trước khi xuất | Guard/port hủy hoặc ghi phiếu | Đã duyệt chặn hủy; nguồn hủy chặn ghi mới/gửi lại; E2E API hủy sản xuất vẫn hoãn theo Q5, không báo đạt chỉ bằng fixture |

## 6. Quyết định Q1–Q6 đã xác nhận

| Mã | Quyết định của dev | Ảnh hưởng |
|---|---|---|
| Q1 | UC/BR/model/init.sql v4 làm chuẩn; giữ module phieu_xuat | Thay quyền người lập, loại xuat_linh_kien, nguồn yêu cầu và nội dung server lấy từ snapshot; không tương thích payload v3 |
| Q2 | Gỡ PATCH/DELETE/về nháp công khai; giữ xóa nháp nội bộ khi hủy yêu cầu | Không có API sửa lượng hoặc thao tác về nháp; client cũ phải cập nhật |
| Q3 | QLK-only list; q/loại/trạng thái/NV lập/yêu cầu/ngày tạo giờ VN, AND; page 1/20/max100, sort cũ không lệnh | Chốt R2 UC-40; NV chỉ đọc chi tiết nguồn được giao |
| Q4 | Duyệt lại trả kết quả cũ và da_ghi_so_truoc_do=true; vẫn cần một tag đúng định dạng, cho tag cũ | Ngoại lệ rõ ràng cho retry đã ghi sổ; không ghi lần hai hoặc bỏ kiểm tra quyền |
| Q5 | Chỉ phụ thuộc backend tối thiểu v4, giữ port sản xuất; không tự merge/refactor toàn sản xuất; hoãn E2E sản xuất | Cần nêu ranh giới owner/transaction trong plan; không mở rộng frontend/SQL/DB ứng dụng |
| Q6 | Cho yêu cầu cũ tiếp tục tới hoàn thành dù TP đã ngừng; chặn yêu cầu mới | Làm rõ R6/R7 UC-12 trong luồng phiếu xuất; không sửa quy tắc ngừng/dùng lại của catalog |

Không còn câu hỏi Q1–Q6. Chi tiết API/DTO, ETag, lock order, xử lý metadata gửi
lại và ranh giới tích hợp được trình trong [plan](PLAN.md), đã được dev duyệt.
Spec là tài liệu truy vết, không phải thành phần được gọi khi chương trình chạy.

## 7. Truy vết triển khai và kiểm thử

Prefix endpoint dưới đây là `/api/v1/phieu_xuat`. Các service thuộc
`PhieuXuatService`, spec chính là file này cùng bảy UC gốc được liên kết ở cột UC.
Test S/A/P tương ứng [service](../../../backend/tests/test_phieu_xuat_service.py),
[HTTP](../../../backend/tests/test_phieu_xuat_api.py),
[PostgreSQL](../../../backend/tests/test_phieu_xuat_postgres.py).
Tên test thực tế có mã UC/GI-AC. Chỉ phần backend được nghiệm thu ở đây; mọi thao
tác xác nhận/nút/màn hình và E2E API sản xuất gốc tiếp tục hoãn theo Q5.

| UC / spec | Endpoint → service | AC | Test / kiểm chứng |
|---|---|---|---|
| [UC-34](UC-34.md) | POST collection, POST /{id}/gui → create_issue/submit_issue | AC-1–6; GI-AC-01–04/07/12/16/20 | S `input_only_source_and_kind`, A `component_lifecycle`, `reject_resubmit`, P `concurrent_create`; UI xác nhận hoãn |
| [UC-35](UC-35.md) | POST /{id}/duyet → approve | AC-1–3; GI-AC-08/12–17/21 | A `component_lifecycle`, P `two_sessions_one_posting`, `all_writes_rollback`, `replay_validates_format_and_performs_no_write` |
| UC-35 | Port hủy → co_phieu_da_ghi_so/huy_phieu_chua_ghi_so | AC-4; GI-AC-22 | P `internal_cancel_ports`, `internal_cancel_joins_parent_rollback`; E2E hủy v4 hoãn, chưa báo toàn AC đạt |
| [UC-36](UC-36.md) | POST /{id}/tu_choi, GET /{id}, POST /{id}/gui → reject_issue/get_issue/submit_issue | AC-1–3; GI-AC-07/10/11/16 | A `reject_resubmit[xuat_linh_kien]`, P `reject_vs_submit_or_replay`; UI hoãn |
| [UC-37](UC-37.md) | POST collection, POST /{id}/gui → create_issue/submit_issue | AC-1–6; GI-AC-02/04/05/07/20 | A `finished_goods`, `manager_creates_sends_and_approves_finished_goods`, `db_auth_scope`; P `source_eligibility`, `inactive_output_before_creation`; UI `issue-main-flow.spec.js` |
| [UC-38](UC-38.md) | POST /{id}/duyet → approve, repository.update_progress | AC-1–3; GI-AC-09/12–17 | A `finished_goods`, P `all_writes_rollback[after_progress]`; E2E thực hiện sản xuất hoãn |
| [UC-39](UC-39.md) | POST /{id}/tu_choi, GET /{id}, POST /{id}/gui → reject_issue/get_issue/submit_issue | AC-1–2; GI-AC-07/10/11 | A `reject_resubmit[xuat_thanh_pham]`; nút UI hoãn |
| [UC-40](UC-40.md) | GET collection, GET /{id} → list_issues/get_issue | AC-1–3; GI-AC-01/18/19 | A `http_contract`, `db_auth_scope`, P `filter_dates_ties_and_readonly`; UI hoãn |
| Dùng chung | Router → PhieuXuatService → repository/AuditService | GI-AC-01–22 | Bảng AC bên dưới, fixture PostgreSQL thật từ init.sql, không dùng DB ứng dụng |

### Kết quả từng AC backend

Tên bên dưới là hậu tố test thực tế, sau tiền tố `test_uc..._gi_ac..._` trong các file S/A/P.

| AC | Test quan sát hành vi | Kết quả / giới hạn |
|---|---|---|
| GI-AC-01 | S list_requires_manager/manager_cannot_create_directly, A db_auth_scope | Đạt quyền DB, khóa, pwdv cũ; chưa nâng auth sang cột phien_ban_dang_nhap v4 |
| GI-AC-02 | S assignment_before_catalog_or_write, A db_auth_scope | Đạt |
| GI-AC-03 | S input_only_source_and_kind/strict_source_id, A component_lifecycle/forbid_client_content | Đạt |
| GI-AC-04 | P concurrent_create | Đạt hai session, 1 phiếu/1 audit tạo |
| GI-AC-05 | A finished_goods, P source_eligibility | Đạt |
| GI-AC-06 | A http_contract/forbid_client_content, P internal_cancel_ports | Đạt phạm vi backend; UI hoãn |
| GI-AC-07 | A reject_resubmit | Đạt cả LK/TP |
| GI-AC-08 | A component_lifecycle | Đạt giá/tồn/giữ/ledger, không tự bắt đầu SX |
| GI-AC-09 | A finished_goods | Đạt tồn/giữ/ledger/đóng nguồn và audit nguồn |
| GI-AC-10 | A reject_resubmit | Đạt nonblank, metadata, không đổi kho/nguồn |
| GI-AC-11 | A reject_resubmit/component_lifecycle | Đạt resource UTC, audit đọc được gui_lai và trạng thái |
| GI-AC-12 | S missing_validator/only_one_canonical_strong_validator, A http_contract/reject_resubmit | Đạt 428/412, chống tag quay lại cùng trạng thái |
| GI-AC-13 | P two_sessions_one_posting/two_sources_share_items/reject_vs_submit_or_replay | Đạt barrier + connection độc lập |
| GI-AC-14 | A component_lifecycle, P replay_validates_format_and_performs_no_write/incomplete_posting_is_not_repaired | Đạt replay và SQL spy không ghi |
| GI-AC-15 | P inconsistent_data_rejected/other_request_reservations_untouched/wrong_completion_reservation_rollback | Đạt, không tự sửa dữ liệu lệch |
| GI-AC-16 | P all_writes_rollback (6 điểm lỗi) | Đạt rollback dữ liệu, không mô phỏng crash worker/kết nối thật |
| GI-AC-17 | A component_lifecycle, P inconsistent_data_rejected[overflow/null_price_pair], S stock_policy_rejects_non_integer_prices | Đạt |
| GI-AC-18 | A http_contract, P filter_dates_ties_and_readonly | Đạt AND/count/page/sort/ngày VN/ký tự literal |
| GI-AC-19 | P filter_dates_ties_and_readonly | Đạt SQL spy GET không ghi |
| GI-AC-20 | P inactive_output_before_creation, A finished_goods | Đạt luồng phiếu cũ; không nghiệm thu policy tạo yêu cầu mới |
| GI-AC-21 | P mapping_matches_actual_bootstrap/concurrent_codes_different_sources/code_exhaustion_rollback/posted_rows_and_history_immutable | Đạt reflection, mã/Identity/trigger, code sau xóa nội bộ |
| GI-AC-22 | P internal_cancel_ports/internal_cancel_joins_parent_rollback | Đạt guard/port; E2E API hủy sản xuất hoãn Q5 |

## 8. Cổng duyệt, bàn giao và giới hạn

1. **Đã xong:** khảo sát chỉ đọc, baseline và xác nhận Q1–Q6; giữ nguyên bảy UC gốc.
2. **Đã duyệt:** dev xác nhận “ok rồi nhé” với bản spec tổng thể này.
3. **Đã duyệt:** [plan và danh sách task](PLAN.md), gồm API/schema, owner,
   service/repository/dependency, transaction/lock/ETag, test và sequence/PNG.
4. **Đã triển khai backend:** sáu endpoint v4, port nội bộ, phụ thuộc inventory/audit,
   test và [sequence/PNG](../../../docs/sequence/phieu_xuat.md). Xem kết quả T01–T12 trong plan.

Không sửa frontend/SQL/bootstrap/config/migration hoặc DB ứng dụng; không commit/push.
Không báo toàn hệ thống đạt E2E: sản xuất và các đường inventory legacy chưa nâng v4.
Test nhân viên baseline còn 8 lỗi fixture; type check inventory legacy còn 4 lỗi.
