# Đặc tả backend BOM — UC-15 đến UC-19

**Trạng thái: SPEC APPROVED — dev đã duyệt spec và Q1–Q6 ngày 14/11/2026.**
**Plan/task đã được dev duyệt; backend trong phạm vi đã triển khai và kiểm thử ngày 14/11/2026.**
Xem [kết quả và truy vết thực tế](#8-kết-quả-triển-khai-và-truy-vết-thực-tế); không bao gồm nghiệm thu frontend/sản xuất v4.

Ngày khảo sát: 14/11/2026. Nhánh: `feature/bom`, HEAD khi khảo sát: `f461ecd`.
Dev xác nhận phạm vi: cả năm UC, chỉ backend; frontend để sau.
Dev đã xác nhận “Anh duyệt rồi nhé” sau khi review bản spec và sáu đề xuất Q1–Q6.
Phê duyệt spec không thay thế bước duyệt plan/task trước triển khai.

## 1. Mục tiêu và nguồn đối chiếu

Đưa nghiệp vụ BOM một cấp vào backend: xem phiên bản, tạo công thức cùng thành phẩm,
tạo phiên bản mới, dùng lại phiên bản cũ, ngừng công thức. Không thay đổi nội dung
các quy tắc và AC gốc khi bổ sung phần kiểm chứng backend.

| Nguồn đã đọc | Nội dung liên quan |
|---|---|
| [UC-15](UC-15.md) | QLK/NV xem công thức; QTV không được xem |
| [UC-16](UC-16.md) và [UC-10](../catalog/UC-10.md) | Thành phẩm mới và công thức v1 được tạo cùng lúc |
| [UC-17](UC-17.md) | Sửa bằng phiên bản mới; không đổi yêu cầu đã gửi |
| [UC-18](UC-18.md) | Dùng lại phiên bản cũ; tối đa một phiên bản đang dùng |
| [UC-19](UC-19.md) và [UC-12](../catalog/UC-12.md) | Trạng thái thành phẩm và công thức đi cùng nhau |
| [BR-GIAIDOAN1](../../business_requirements/BR-GIAIDOAN1.md) | BR-001, 003, 004, 005, 007, 016 |
| [Data model v4](../../entity_model/data_model_v4.md) §3.3, §4.4 | Bảng, thời gian kích hoạt, bất biến phiên bản và transaction |
| [init.sql](../../../infra/postgres/init.sql) | Schema bootstrap v4, FK, index và trigger thực tế trong repository |
| [Sequence hiện tại](../../../docs/sequence/bom.md) | Mô tả code cũ theo contract v2; chưa phải mô tả đích v4 |

Tài liệu này đối chiếu **SQL trong repository**, chưa xác nhận schema của database
ứng dụng đang chạy. Không kết nối, sửa hay bootstrap lại database ứng dụng trong bước khảo sát.
README ở gốc và sequence hiện tại còn mô tả BOM nhiều cấp; không dùng chúng để tự
ghi đè BR/UC v4. Nguồn đích đã được dev chốt tại Q1.

## 2. Kết quả khảo sát chỉ đọc (trước triển khai, giữ để đối chiếu)

### 2.1. Stack và phân tầng đang có

- FastAPI, Python async, Pydantic v2, SQLAlchemy async và asyncpg/PostgreSQL.
- Phiên bản trong môi trường kiểm tra: FastAPI 0.144.0, Pydantic 2.14.1,
  SQLAlchemy 2.1.5, pytest 9.1.1; manifest tại `backend/pyproject.toml`.
- Module đã có `router.py`, `service.py`, `ports.py`, `repository.py`, `models.py`,
  `schemas.py`. Router được ghép với prefix `/api/v1` tại `app/main.py`.
- `app/dependencies.py` ghép dependency; xác thực qua AuthService/NhanVienService,
  kiểm tra vai trò bằng `require_roles`. Vai trò hiện tại được đọc lại qua luồng auth.
- Service gọi repository qua Protocol, có transaction adapter dùng chung session.
  `SqlAlchemyTransaction` sở hữu commit/rollback; repository không commit.
- **Chênh lệch audit:** `get_bom_service` đang truyền thẳng
  `SqlAlchemyAuditRepository`, nên lời gọi `self.audit.append` chưa đi qua AuditService.
  Quy tắc nghiệp vụ về vai trò hiện chủ yếu ở dependency router, chưa có guard tương ứng
  tại các thao tác công khai của BomService.
- Module mặt hàng đọc qua cache; cập nhật DB thành công cần đồng bộ cache theo cơ chế
  đang có. Không được ghi trạng thái bằng BOM rồi để API mặt hàng trả snapshot cũ.

### 2.2. Endpoint thực tế

Đã import ứng dụng và đối chiếu OpenAPI, không chạy lifespan hoặc kết nối database:

| Endpoint đang có | Hành vi code hiện tại | Khác biệt chính với UC v4 |
|---|---|---|
| `GET /api/v1/bom` | Lọc, phân trang, đọc chi tiết từng phiên bản | Có field/sort thời gian cũ; truy vấn tình trạng sử dụng qua `LenhSanXuat` |
| `GET /api/v1/bom/{id}` | Đọc một phiên bản | ORM còn `start_time`/`end_time`, không khớp SQL v4 |
| `GET /api/v1/bom/{id}/cau_truc` | Mở rộng cây nhiều cấp theo BOM hiện hành của các node con | UC/BR giai đoạn 1 chỉ cho phép một cấp |
| `POST /api/v1/bom` | Tạo version kế tiếp cho mặt hàng đã có, đóng version đang dùng | Chưa tách đúng UC-16 tạo cùng thành phẩm và UC-17 tạo version |
| `DELETE /api/v1/bom/{id}` | Ngừng mềm version, không xóa dòng | Chưa đồng bộ trạng thái thành phẩm; audit dùng `vo_hieu_hoa` |
| `POST /api/v1/bom/{id}/kich_hoat` | Kích hoạt version cũ, đóng version trước đó | Chưa đồng bộ thành phẩm; audit dùng `sua`; không cập nhật thời điểm kích hoạt v4 |

Không coi bảng trên là API đích đã duyệt. Việc giữ/đổi đường dẫn, DTO và header sẽ
được nêu rõ trong plan sau khi spec được duyệt; không âm thầm thay nghĩa route cũ.

### 2.3. Dữ liệu và phụ thuộc chưa đồng bộ

| Phần | Code hiện tại | UC/SQL v4 |
|---|---|---|
| Công thức | Cho đầu ra bán thành phẩm, thành phần nhiều loại, kiểm tra chu trình | Đầu ra `thanh_pham`, thành phần chỉ `linh_kien` |
| Thời gian Bom | `start_time`, `end_time` | `created_at`, `kich_hoat_gan_nhat_at`, NOT NULL, timestamptz |
| Phiên bản đã dùng | `EXISTS LenhSanXuat` | Nguồn chốt là `YeuCauSanXuat.bom_id`; SQL v4 không tạo `LenhSanXuat` |
| MatHang | API nhận mã, bốn loại; tạo không nhận công thức; trạng thái sửa riêng | Hai loại, hệ thống cấp mã; thành phẩm tạo cùng v1 và đồng bộ trạng thái công thức |
| Audit | Code/schema cũ chưa có trạng thái trước/sau và các mã BOM mới | SQL có `tao_phien_ban`, `dung_lai_phien_ban`, `ngung`, các cột trạng thái |
| Sản xuất | `BomPlanningReader` còn được module `san_xuat` gọi để lập graph cũ | UC-23/24 chốt version khi gửi; UC-26 dùng đúng nhu cầu đã chốt |

Trigger SQL đã cấm xóa Bom, cấm sửa/xóa dòng định mức và bảo vệ version đã được chốt.
Không được bỏ trigger hoặc sửa SQL ngược theo ORM cũ để làm test pass.
Phần audit UC-43 của phiên làm việc trước **không có trong checkout này**; không tự merge
hay cherry-pick. Phạm vi xử lý tối thiểu đã được duyệt tại Q4.

### 2.4. Kiểm thử nền

- `..\.venv\Scripts\python.exe -m pytest tests -q` chạy từ `backend`:
  **8 failed**, đều trong `test_nhan_vien_create_code.py`, fixture dòng 86 thiếu
  trường bắt buộc `VaiTroRead.mo_ta`. Đây là lỗi nền trước mọi sửa đổi BOM.
- `backend/tests` hiện chưa có test BOM; không suy ra sáu endpoint đang chạy đúng từ
  việc import/OpenAPI thành công.
- Chưa chạy kiểm thử repository/PostgreSQL hay E2E BOM; chưa sửa test nhân viên.

## 3. Phạm vi nghiệp vụ đích

### 3.1. Phạm vi đã rõ từ UC/BR

| UC | Actor | Trigger | Kết quả |
|---|---|---|---|
| UC-15 | QLK, NV đang hoạt động | Yêu cầu xem danh sách hoặc một phiên bản | Chỉ đọc, xem cả version cũ và version đang dùng |
| UC-16 | QLK đang hoạt động | Lưu thành phẩm mới cùng công thức tại UC-10 | Thành phẩm và Bom v1 active cùng được lưu, hoặc cùng không được lưu |
| UC-17 | QLK đang hoạt động | Lưu công thức mới cho thành phẩm đã có lịch sử công thức | Version mới active, version trước thôi dùng; thành phẩm active |
| UC-18 | QLK đang hoạt động | Chọn dùng lại một version cũ | Version được chọn active, version trước thôi dùng; thành phẩm active |
| UC-19 | QLK đang hoạt động | Chọn ngừng version đang dùng | Không còn version active; thành phẩm inactive |

QTV không xem/ghi BOM; NV chỉ đọc. Kiểm tra cấu trúc input ở schema; các điều kiện
phụ thuộc loại mặt hàng, sự tồn tại, phiên bản và trạng thái nằm ở service.
Không sửa nội dung của phiên bản cũ, kể cả phiên bản chưa được dùng trong sản xuất.
Không sửa tồn, phần đang giữ hoặc tạo giao dịch kho trong bất kỳ thao tác BOM nào.

### 3.2. Chuyển trạng thái và tính nguyên tử

| Thao tác | Bom | MatHang thành phẩm | Lịch sử |
|---|---|---|---|
| Tạo cùng thành phẩm | Tạo v1 active | Tạo active, tồn 0 | Tạo mặt hàng và tạo công thức |
| Tạo version mới | Active cũ → inactive; version mới active | → active | Tạo phiên bản, lưu snapshot trước/sau |
| Dùng lại version | Active cũ → inactive nếu có; version chọn active | → active | Dùng lại phiên bản, lưu snapshot trước/sau |
| Ngừng | Active → inactive; không xóa | → inactive | Ngừng công thức và thay đổi trạng thái thành phẩm |

`created_at` của version không đổi; mỗi lần version thực sự trở thành active ghi
`kich_hoat_gan_nhat_at` mới. Ngừng không đổi thời điểm kích hoạt gần nhất. Version mới
có số lớn hơn mọi version trước của cùng thành phẩm. Chỉ tối đa một version active.

Tất cả thay đổi liên quan của một thao tác phải cùng commit hoặc cùng rollback:
thành phẩm + Bom + ChiTietBom + audit. Cache không được công bố dữ liệu chưa commit.
Yêu cầu đã gửi giữ nguyên `bom_id` và nhu cầu đã chốt. Các AC cần chạy qua module
sản xuất được đánh dấu riêng, không thay bằng test chỉ đọc giá trị giả rồi báo đạt E2E.

### 3.3. Luồng chạy và truy vết

Luồng chạy bắt buộc trong phạm vi triển khai sau phê duyệt:

```text
Router → Service/Use Case → Repository → PostgreSQL
                    └──→ AuditService → SqlAlchemyAuditRepository → PostgreSQL
```

Các service nghiệp vụ liên quan phối hợp qua API công khai/port phù hợp, không gọi
router của nhau và không commit transaction con. Cách phân công cụ thể được chốt ở plan.
Mỗi service phải ghi nguồn UC; endpoint và test phải liên kết tới spec.
Spec là tài liệu truy vết, không được gọi trong luồng chạy.

## 4. AC dùng chung cho backend

Các AC dưới đây bổ sung cho AC gốc trong từng UC, không thay thế chúng. Q1–Q6 đã
được dev duyệt ngày 14/11/2026; các nội dung gắn Q nay là yêu cầu của spec đã chốt.

### BOM-AC-01 — Quyền truy cập

Given: Tài khoản có vai trò hiện tại trong database.\
When: Đọc hoặc ghi BOM qua HTTP, hoặc gọi service nghiệp vụ với actor tương ứng.\
Then: QLK được đọc/ghi, NV chỉ đọc, QTV bị từ chối; không có thay đổi khi bị từ chối.
Token thiếu/sai/hết hạn trả 401; tài khoản khóa và vai trò không được phép bị chặn
theo quy ước auth đang có, không chỉ tin role do client gửi.

### BOM-AC-02 — Định mức và loại mặt hàng

Given: Input có thành phần không phải linh kiện, ID không tồn tại, định mức không
nguyên dương, thành phần lặp hoặc danh sách rỗng.\
When: Tạo v1 hoặc tạo version mới.\
Then: Từ chối toàn bộ; không tạo/sửa bất kỳ thành phẩm, version hay audit thành công nào.
Boolean không được coi là định mức 1; giá trị có phần lẻ không được làm tròn.
Danh sách không rỗng đã được dev chốt cùng Q1.

### BOM-AC-03 — Đọc không làm thay đổi dữ liệu

Given: Công thức có nhiều version, có thể không còn version active.\
When: QLK hoặc NV đọc danh sách, chi tiết, hoặc cấu trúc nếu route này được giữ.\
Then: Đọc đúng version, không tự kích hoạt, không thay đổi thời gian, tồn hay audit.

### BOM-AC-04 — Cập nhật và audit nguyên tử

Given: Một thao tác BOM hợp lệ cần ghi thêm audit và thay đổi trạng thái thành phẩm.\
When: Ghi Bom, ChiTietBom, MatHang, audit hoặc commit gặp lỗi.\
Then: Không để lại trạng thái nửa chừng; cache không công bố dữ liệu bị rollback;
thất bại không bị trả thành công. Audit đi qua AuditService trong transaction của caller.

### BOM-AC-05 — Đồng thời

Given: Hai request quản lý cùng một thành phẩm chạy đồng thời.\
When: Cùng tạo version, kích hoạt hoặc ngừng.\
Then: Không trùng version, không có hai active, không mất đồng bộ MatHang/Bom và
không ghi audit cho thao tác thất bại. Chính sách ETag/xung đột theo Q6 đã duyệt.

### BOM-AC-06 — Bất biến và không tác động kho

Given: Có version cũ và yêu cầu đã chốt version đó.\
When: Đổi version đang dùng hoặc ngừng công thức.\
Then: Không sửa/xóa định mức cũ, `bom_id` hay nhu cầu đã chốt; không đổi tồn,
phần đang giữ, giao dịch kho. Cần phân biệt test bất biến dữ liệu với E2E sản xuất.

### BOM-AC-07 — HTTP và dữ liệu đọc

Given: Request hợp lệ hoặc request có input không hợp lệ.\
When: Gọi endpoint thuộc phạm vi.\
Then: Response tuân thủ schema/OpenAPI đã duyệt, không lộ thông tin bí mật;
phân biệt 401/403, 404 không tồn tại, 409 xung đột và 422 sai input. Theo Q6 đã duyệt:
thiếu If-Match trả 428; ETag cũ/weak/wildcard trả 412. Không tự thêm If-Match cho GET
hoặc cho thao tác tạo thành phẩm mới.

### BOM-AC-08 — Trạng thái không hợp lệ (Q5 đã duyệt)

Given: Version muốn dùng lại đã active, hoặc version muốn ngừng đã inactive.\
When: Gọi thao tác tương ứng.\
Then: Trả 409, không tạo audit hay cập nhật thời điểm. Ngừng version cũ không được
ngừng nhầm version khác đang active. Điều kiện ETag được xét trước lỗi trạng thái
theo chính sách Q6 đã duyệt.

## 5. Các quyết định dev đã xác nhận ngày 14/11/2026

| Mã | Điểm đã chốt | Quyết định được duyệt | Ảnh hưởng |
|---|---|---|---|
| Q1 | Code/tài liệu cũ mô tả nhiều cấp; UC/BR/model/SQL v4 mô tả một cấp | Dùng UC-15–19 + BR giai đoạn 1 + model/SQL v4 làm đích; giữ tên bảng PascalCase. Công thức có ít nhất một dòng linh kiện. DTO dùng `created_at`, `kich_hoat_gan_nhat_at`, bỏ `start_time`/`end_time`; không giữ hành vi nhiều cấp. Chi tiết chuyển đổi endpoint/sort/DTO phải trình ở plan | API response và một số input/sort cũ có thể không tương thích; frontend chưa sửa trong tác vụ này |
| Q2 | UC-16 không thể hoàn chỉnh nếu chỉ sửa folder bom; UC-19/18 còn liên quan UC-12 | Cho phép phần backend phụ thuộc tối thiểu của `mat_hang`: tạo thành phẩm kèm v1, hệ thống cấp mã theo UC-10/SQL; ngừng/dùng lại thành phẩm và công thức cùng transaction; chặn đường sửa trạng thái cũ phá bất biến; đồng bộ cache. Không refactor toàn bộ catalog | Thay đổi request tạo thành phẩm, các đường ghi trạng thái liên quan và tài liệu sequence tương ứng; không sửa frontend |
| Q3 | Một số AC yêu cầu chạy cả luồng sản xuất v4, nhưng module san_xuat hiện còn mô hình cũ | Tác vụ này không refactor sản xuất. Giữ hợp đồng nội bộ còn cần thiết nếu tương thích được, kiểm chứng bất biến dữ liệu chốt; ghi rõ AC sản xuất còn phụ thuộc/chưa kiểm chứng. Nếu không giữ được hợp đồng cũ, dừng phần phụ thuộc và đưa phương án vào plan để dev chốt | Không được báo hoàn tất toàn bộ E2E của UC-17/18/19. Chặn lập/gửi mới và tiếp tục chứng từ của yêu cầu cũ cần tích hợp sản xuất v4 riêng |
| Q4 | Nhánh hiện không có phần audit UC-43 mới; schema đọc/ORM audit còn enum cũ | Chỉ cập nhật phần audit cần cho ghi/đọc được các mã BOM v4 và trạng thái trước/sau; DI truyền AuditService, cùng session/transaction. Không thêm endpoint audit mới hoặc tự merge UC-43 | Có thay đổi nhỏ ở module audit/dependencies để thực hiện đúng luồng; phân biệt với triển khai lại UC-43 |
| Q5 | UC chưa quy định kết quả khi dùng lại version đã active hoặc ngừng version đã inactive | Từ chối 409, không audit/đổi thời gian. Chỉ ngừng được version đang dùng | Khác code cũ đang trả thành công/no-op cho hai tình huống này |
| Q6 | Code cũ không ETag/If-Match; thao tác giữa nhiều quản lý có thể dựa trên dữ liệu cũ | Thêm strong ETag cho thông tin dùng để xác nhận, bắt buộc If-Match với tạo version mới/dùng lại/ngừng, so sánh và ghi trong cùng transaction dưới khóa. Thiếu 428, cũ/weak/wildcard 412. GET và tạo thành phẩm mới không yêu cầu | Client ghi phải lấy ETag mới. Plan phải xác định rõ resource dùng để tính ETag và thời điểm ETag đổi khi version active hoặc trạng thái thành phẩm thay đổi |

Q1–Q6 đã được duyệt; không tự mở rộng ra ngoài các quyết định này. Quy tắc trong UC/BR
không bị thay bằng các phương án tạm của code cũ. Không tạo/chạy migration, không sửa
database có dữ liệu; schema test dùng bootstrap trên database test mới/trống.

## 6. Bảng truy vết trước triển khai (lịch sử khảo sát)

Tại thời điểm khảo sát, các test dưới đây là nhóm dự kiến, chưa có test BOM.
Trạng thái đó đã được thay bằng [bảng kết quả thực tế ở §8](#8-kết-quả-triển-khai-và-truy-vết-thực-tế).
Endpoint/service đích và tên test cụ thể sẽ được điền sau khi duyệt spec, rồi cập nhật
thành symbol thực tế ở plan/triển khai; không mô tả endpoint chưa có là đang chạy.
Định danh AC đầy đủ là `UC-xx/AC-n` hoặc `BOM-AC-nn`, không đổi số AC gốc.

| UC | Endpoint/liên kết hiện tại, chưa phải API đích | Service hiện tại/liên quan | Spec | AC | Kiểm chứng cần có và trạng thái |
|---|---|---|---|---|---|
| UC-15 | Ba GET `/api/v1/bom`, `/{id}`, `/{id}/cau_truc` | `BomService.list_bom/get_bom/get_cau_truc` | [UC-15](UC-15.md) | AC-1–7; BOM-AC-01/03/07 | Service/API/repository: quyền, đọc version, lọc/page/sort, 404; chưa có test. AC-2/4 chỉ kiểm chứng backend, ẩn/hiện UI để sau |
| UC-16 | `POST /api/v1/mat_hang` đang có nhưng chưa nhận BOM; POST BOM cũ không đáp ứng atomic creation | `MatHangService.create_mat_hang`, `BomService.create_bom` chưa tích hợp | [UC-16](UC-16.md), [UC-10](../catalog/UC-10.md) | AC-1–7; BOM-AC-01/02/04/07 | Service/API/PG: tạo cùng lúc, input lỗi, rollback/audit/cache; chưa có test |
| UC-17 | `POST /api/v1/bom` hiện tạo version nhưng còn luật cũ | `BomService.create_bom` | [UC-17](UC-17.md) | AC-1–7; BOM-AC-02/04/05/06/07 | Service/API/PG cho version và transaction chưa có test; AC-1–4 có phần lập/gửi/kiểm tra sản xuất phụ thuộc Q3 |
| UC-18 | `POST /api/v1/bom/{id}/kich_hoat` hiện có nhưng chưa v4 | `BomService.activate_bom` | [UC-18](UC-18.md) | AC-1–6; BOM-AC-04/05/06/07/08 | Service/API/PG: chọn lại version, thời gian và rollback chưa có test; AC-2 và lập/gửi trong AC-3 phụ thuộc Q3 |
| UC-19 | `DELETE /api/v1/bom/{id}` hiện ngừng mềm nhưng thiếu đồng bộ | `BomService.delete_bom`, `MatHangService.delete_mat_hang` | [UC-19](UC-19.md) | AC-1–8; BOM-AC-04/05/06/07/08 | Service/API/PG: ngừng, audit, bất biến chưa có test; AC-2–4 và lập/gửi trong AC-5 phụ thuộc Q3 |
| Dùng chung | Các endpoint được duyệt trong plan | Service nghiệp vụ + `AuditService.append` | Tài liệu này §4 | BOM-AC-01–08 | Test auth thật qua DI; test hành vi service; PG thật cho khóa/rollback/concurrency/trigger; tất cả chưa triển khai |

Không dùng SQLite để kết luận đúng khóa/trigger/PostgreSQL. Không dùng database ứng
dụng làm nơi thử ghi. Các AC nói về giao diện chỉ kiểm chứng quyền backend ở giai đoạn
này; UI và nghiệm thu E2E liên module phải ghi riêng thay vì đánh dấu đạt toàn bộ.

## 7. Cổng duyệt

1. **Đã đạt:** dev duyệt năm UC và bản bổ sung này, gồm Q1–Q6, ngày 14/11/2026.
2. **Đã đạt:** dev duyệt [plan/task](PLAN.md): “Ok hết rồi nhé, thực hiện và test giúp tôi”.
3. **Đã triển khai:** source/test và tài liệu backend trong phạm vi Q1–Q6; xem §8.

Đã cập nhật `docs/sequence/bom.md`, `mat_hang.md` và 12 PNG cho endpoint thực tế.

## 8. Kết quả triển khai và truy vết thực tế

Ngày kiểm tra: 14/11/2026. Mức rủi ro HIGH, chỉ backend. Không thay đổi SQL bootstrap,
seed, migration, cấu hình/database ứng dụng, frontend hoặc các service sản xuất.

### 8.1. Hợp đồng hiện tại

- UC-15: giữ ba GET BOM; GET detail có ETag, cấu trúc chỉ gồm linh kiện một cấp.
- UC-16: POST `/api/v1/mat_hang` nhận `bom.chi_tiet` khi tạo thành phẩm. Mã hệ thống
  cấp; không nhận mã, trạng thái hoặc tồn từ client. Một transaction cho item/v1/audit.
- UC-17: POST `/api/v1/bom/{id}/phien_ban`, body `{chi_tiet: [...]}`. POST `/bom` cũ 405.
- UC-18: POST `/api/v1/bom/{id}/kich_hoat`, body `{}` bắt buộc.
- UC-19: DELETE `/api/v1/bom/{id}` ngừng mềm cả công thức và thành phẩm; không xóa dòng.
- Ba mutation BOM bắt buộc If-Match của GET detail cùng ID: thiếu 428, tag không
  khớp/weak/wildcard/nhiều giá trị 412; sai trạng thái với tag hiện tại 409.
- GET detail mặt hàng trả tag riêng có ngữ cảnh công thức; không dùng tag BOM cho
  PATCH/DELETE mặt hàng. List/catalog vẫn đọc cache; detail đọc snapshot DB.
- Audit: `BomService → AuditService → SqlAlchemyAuditRepository`. Catalog cũng dùng
  AuditService trong cùng session. Snapshot/version và trạng thái trước/sau được lưu.

### 8.2. Kiểm thử đã chạy

| Phần | Kết quả thực tế |
|---|---|
| `test_bom_service.py` | 22 pass: validation, strong If-Match, guard service |
| `test_bom_api.py` | 50 pass: real auth/DB roles, khóa tài khoản, query/body/path, HTTP, ETag, lifecycle, safe 500 |
| `test_bom_postgres.py` | 16 pass: bootstrap SQL v4 thật, reflection ORM, version, khóa/đồng thời, rollback, trigger và dữ liệu đã chốt |
| `test_mat_hang_bom.py` | 17 pass: tạo atomic, mã tự cấp/hết dải, rollback/cache, chọn version gần kích hoạt nhất |
| Toàn bộ suite `python -m pytest tests -q --tb=line` | **105 pass, 8 fail**; cả 8 fail vẫn ở fixture `test_nhan_vien_create_code.py:86` thiếu `VaiTroRead.mo_ta`, giống baseline; không sửa hoặc làm yếu test này |
| Ruff check/format | Đạt trên các file backend/test thuộc phạm vi |
| mypy | Đạt 25 source files với `--follow-imports=silent --disable-error-code import-untyped`; asyncpg thiếu stubs, không tuyên bố strict typing toàn backend |
| Mermaid | Render thành công 6 BOM + 6 catalog; PNG đã xuất, kiểm tra ảnh đại diện |
| Kiểm tra kiến trúc | Map không phát hiện cycle trong phần BOM; đối chiếu imports/lời gọi bằng source. Boundary checker không kết luận vì repository chưa có architecture declaration; không tạo cấu hình giả để làm xanh |
| Bằng chứng HTTP | [11 request/response thật](../../../docs/examples/bom-http.json), ASGI app thực + PostgreSQL test; không ghi JWT/secret ra artifact |

PostgreSQL chạy trên container test tạm, cổng 55464, tmpfs không volume. Fixture chỉ
tạo DB ngẫu nhiên `bom_<uuid>_test` trên server test và bootstrap khi xác nhận trống;
cleanup đúng DB do fixture tạo. Không lấy URL ứng dụng làm fallback. Không dùng
SQLite để suy ra đúng concurrency/trigger. API test không chạy lifespan với DB ứng dụng.
Container test đã được dừng/xóa sau kiểm thử; container PostgreSQL ứng dụng vẫn healthy.
Muốn chạy lại các test PostgreSQL/API phải cung cấp server test riêng đúng guard URL
trong fixture; không có URL thì các test đó skip và phải được báo là chưa kiểm chứng.

### 8.3. Truy vết UC/AC → endpoint → service → test

Tên file test đều ở `backend/tests/`. Một dòng gom nhiều AC chỉ khi ghi rõ phần
kiểm chứng; các phần UI và sản xuất không được coi là đã đạt từ test backend.

| UC/AC | Endpoint → service thực tế | Test thực tế / trạng thái |
|---|---|---|
| UC-15/AC-1,7 | GET list/detail/cấu trúc → `BomService.list_bom/get_bom/get_cau_truc` | `test_uc15_filter_pagination_and_legacy_planning_port`, `test_uc17_uc18_uc19_http_lifecycle`: đạt backend, đọc được version cũ/đã ngừng |
| UC-15/AC-2–4 | GET BOM + mutation → router auth và BomService guard | `test_uc15_roles_use_database_not_jwt_claims`, `test_bom_ac01_all_mutations_denied`, `test_bom_ac01_public_service_denies_before_io`: đạt quyền backend; UI ẩn/hiện nút hoãn |
| UC-15/AC-5 | GET list → `BomService.list_bom` | `test_uc15_ac5_stable_sort_ties_across_pages`, `test_uc15_filter_pagination_and_legacy_planning_port`: đạt |
| UC-15/AC-6 | GET BOM → schema/context | `test_uc15_ac6_bad_query`, `test_uc15_ac6_detail_errors`: đạt 404/422 |
| UC-16/AC-1–4,7 | POST mặt hàng → `MatHangService.create_mat_hang` → `BomService.create_initial_formula` | `test_uc16_ac1_to4_bad_formula_never_creates_item`, `test_uc16_ac1_wrong_type_or_missing_item_rolls_back`, `test_uc16_ac7_strict_positive_quantity`, `test_uc17_old_post_removed_and_openapi_trace`: đạt phần API, không có route tạo v1 riêng |
| UC-16/AC-5–6 | Cùng luồng tạo item/v1/audit/cache | `test_uc16_ac5_atomic_create_and_generated_code`, `test_uc10_uc16_create_response_and_reserved_input`, `test_uc16_ac6_atomic_create_failure`: đạt |
| UC-17/AC-1–3 | POST version → `BomService.create_version` | `test_uc17_ac1_to4_uc19_ac6_preserves_committed_request_and_balances`: đạt bất biến bom_id/nhu cầu; gửi/kiểm tra/kiểm tra lại qua API sản xuất thật **chưa kiểm chứng theo Q3** |
| UC-17/AC-4 | POST version khi thành phẩm ngừng → `create_version` | `test_uc17_ac4_new_version_reactivates_stopped_product`: đạt trạng thái/version; lập/gửi yêu cầu sản xuất sau đó **chưa kiểm chứng** |
| UC-17/AC-5–7 | POST version → `create_version` + mutation/audit | `test_uc17_uc18_uc19_lifecycle_and_stale_validators`, `test_bom_ac05_two_real_sessions_same_etag`, `test_bom_ac04_rollback_version_and_cache`, `test_uc17_ac7_invalid_formula_preserves_old_version`: đạt |
| UC-18/AC-1,3–6 | POST kích hoạt → `BomService.activate_bom` | `test_uc17_uc18_uc19_http_lifecycle`, `test_uc12_reuses_most_recently_activated_not_highest_version`, `test_bom_ac04_state_and_audit_rollback`: đạt trạng thái, timestamp, ID/định mức bất biến, 409 và rollback |
| UC-18/AC-2 | Gửi yêu cầu sản xuất sau dùng lại | **Chưa kiểm chứng**, ngoài phạm vi sản xuất theo Q3; không thay bằng mock để báo đạt |
| UC-19/AC-1,6–8 | DELETE BOM → `BomService.delete_bom` | `test_uc17_uc18_uc19_lifecycle_and_stale_validators`, `test_uc19_bom_ac06_trigger_blocks_hard_delete_and_detail_update`, `test_bom_ac04_state_and_audit_rollback`, `test_uc17_ac1_to4_uc19_ac6_preserves_committed_request_and_balances`: đạt backend |
| UC-19/AC-2–5 | Ngăn lập/gửi mới; tiếp tục sản xuất/cấp/xuất/hoàn thành yêu cầu cũ | Chỉ kiểm chứng trạng thái item và dữ liệu chốt giữ nguyên; **chưa đạt nghiệm thu E2E**, module sản xuất v4 để tác vụ sau |
| BOM-AC-01 | Auth dependency → service guards | `test_bom_ac01_unauthenticated`, `test_bom_ac01_changed_role_and_locked_account_take_effect`, các test role ở trên: đạt theo cơ chế auth hiện tại, không tuyên bố refactor auth v4 |
| BOM-AC-02 | Schema + `_validate` | Test strict quantity và bad formula/wrong type/missing item: đạt |
| BOM-AC-03 | Ba GET BOM | `test_uc15_bom_ac03_reads_do_not_write`: đạt, đối chiếu snapshot DB trước/sau |
| BOM-AC-04 | `MatHangMutation` + AuditService + repositories | Test atomic create failure, rollback version/cache và rollback activate/stop: đạt cho lỗi ghi/audit/commit mô phỏng; chưa thử mất kết nối thật đúng lúc COMMIT |
| BOM-AC-05 | ETag dưới khóa, advisory + item/version locks | `test_bom_ac05_two_real_sessions_same_etag`, `test_bom_ac05_independent_items_and_two_stops`, `test_bom_ac05_catalog_tag_changes_when_only_formula_changes`: đạt với hai session/cache độc lập |
| BOM-AC-06 | Mutation BOM không sửa kho/yêu cầu chốt | Test preserves_committed_request_and_balances + trigger_blocks_hard_delete_and_detail_update: đạt phần dữ liệu, không phải E2E sản xuất |
| BOM-AC-07 | Router/schema/headers/exception handler | Test write_preconditions, bad_query, detail_errors, no_body_endpoints_reject_body, safe_500 và HTTP lifecycle: đạt |
| BOM-AC-08 | `_activate` / `_stop` kiểm tra trạng thái | HTTP lifecycle + test stale_validators: đạt 409 khi active lặp; tag cũ được 412 trước trạng thái; ngừng version cũ không thể đổi version hiện hành |

### 8.4. Giới hạn bàn giao

- Chưa hoàn tất frontend, luồng sản xuất v4 hoặc E2E các phần AC ghi rõ ở trên.
- Database ứng dụng chưa được đối chiếu/cập nhật schema. Backend này cần schema v4;
  việc đổi ORM không tự cập nhật volume/database đang chạy. Không tự reset/seed/migrate.
- Không triển khai lại UC-43 đọc audit; chỉ bổ sung schema/mapping cần cho mã BOM và
  đưa đường ghi qua AuditService. Các caller legacy của module khác còn dùng mã v3
  không được chuyển đổi trong tác vụ này.
- Test không chứng minh mọi tình huống mất mạng/worker chết hoặc thời gian hội tụ
  cache giữa nhiều instance. Có xử lý cache unavailable khi commit không chắc chắn.
- Không sửa các lỗi nền nhân viên, không commit/push; dev review diff trước khi commit.
