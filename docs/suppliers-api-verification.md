# Kiểm chứng API nhà cung cấp — cập nhật 20/10/2026

## Phạm vi và quyết định

Triển khai GET danh sách/chi tiết và POST/PATCH/DELETE `/api/v1/nha_cung_cap` theo
[API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view),
mục 2, 3, 5, 14. Dev xác nhận dùng v2 thay cho v1 trong ảnh, giữ tên module
`nha_cung_cap`, cập nhật import sau đổi tên và cho phép `ten_ncc=null` với dữ liệu cũ.
Ngày 20/10, dev xác nhận khôi phục hai GET bị mất khỏi router/service/repository hiện tại,
bổ sung ba API ghi; DELETE dùng audit `xoa_nhap` với snapshot trước khi xóa.
SQL khai báo ID nhà cung cấp là INTEGER không tự tăng, khác ORM Identity cũ. Dev chọn giữ SQL:
đã sửa ORM thành `autoincrement=False`, backend cấp ID dưới advisory transaction lock.
Không migration, không thay đổi schema hay cập nhật dữ liệu ứng dụng.

Hai GET cho `quan_tri_vien` và `quan_ly`; ba API ghi mới chỉ cho `quan_ly`.
JWT, trạng thái tài khoản, vai trò và
phiên bản mật khẩu được kiểm tra qua cơ chế auth dùng chung. Nhân viên bị từ chối 403.
Các endpoint `/suppliers` có sẵn giữ nguyên query/response và quyền cũ để tương thích.
Không mở rộng sang CRUD chứng từ, tồn kho hoặc frontend.

## Ví dụ sử dụng

Đăng nhập qua `/api/v1/auth/dang_nhap` hoặc nút Authorize của Swagger (dùng `/auth/token`).
Sau đó gửi Bearer token:

```http
GET /api/v1/nha_cung_cap?page=1&page_size=20&q=alpha&tinh=ha_noi&sort=ma_ncc
Authorization: Bearer <access-token>
```

Ví dụ minh họa response, không phải dữ liệu ứng dụng:

```json
{
  "data": [{
    "id": 1,
    "ma_ncc": "NCC-000001",
    "ten_ncc": "Alpha",
    "so_dien_thoai": null,
    "dia_chi": null,
    "phuong": "tay_ho",
    "tinh": "ha_noi"
  }],
  "meta": {"request_id": "<request-id>", "page": 1, "page_size": 20, "total": 1, "total_pages": 1}
}
```

`q` tìm chuỗi con trong mã/tên, không phân biệt hoa thường; `%` và `_` được escape.
`tinh`, `phuong` lọc bằng giá trị chính xác sau trim. Sort whitelist: id/ma_ncc/ten_ncc,
thêm dấu `-` để giảm dần, ID tăng dần làm tiêu chí phụ. Mặc định page=1, page_size=20,
sort=id. page_size tối đa 100. Trang vượt phạm vi trả danh sách rỗng với total thực tế.

```http
GET /api/v1/nha_cung_cap/1
Authorization: Bearer <access-token>
```

Chi tiết trả `{data: {...}, meta: {request_id: ...}}`, HTTP 200 và strong `ETag`.
ETag tính từ bảy trường dữ liệu, không gồm request_id. Không yêu cầu If-Match cho GET.
ID không tồn tại trả 404 `khong_tim_thay`; ID sai kiểu/không dương trả 422.
Query thừa/lặp hoặc sort sai trả 422 `du_lieu_khong_hop_le`.
Thiếu/sai/hết hạn/thu hồi token trả 401; tài khoản khóa hoặc không có quyền trả 403.
Lỗi dùng `{error: {code, message, details}, meta: {request_id}}`, không lộ SQL/stack trace.
Không có nhánh nghiệp vụ 409 cho hai GET chỉ đọc này.

## POST, PATCH, DELETE

```http
POST /api/v1/nha_cung_cap
Authorization: Bearer <token-quan-ly>
Content-Type: application/json

{"ma_ncc":"NCC-900001","ten_ncc":"Nhà cung cấp mẫu","tinh":"ha_noi"}
```

Trả 201, `{data, meta}`, `Location: /api/v1/nha_cung_cap/<id>` và ETag.
`ma_ncc` do client gửi theo contract v2, định dạng NCC-000001..NCC-999999 theo CHECK SQL.
`ma_ncc`, `ten_ncc` bắt buộc, trim, không null/rỗng. Các field liên hệ/địa chỉ nullable.
Không nhận ID, trạng thái, audit, chi tiết hoặc query không khai báo.

```http
PATCH /api/v1/nha_cung_cap/<id>
Authorization: Bearer <token-quan-ly>
If-Match: "<etag-tu-get-chi-tiet>"
Content-Type: application/json

{"ten_ncc":"Tên mới","so_dien_thoai":null}
```

Trả 200 và ETag hiện tại. Field bỏ qua giữ nguyên; null chỉ được xóa field nullable.
GET có thể trả tên NULL legacy, nhưng CREATE/PATCH không được chủ động ghi tên NULL/rỗng.
PATCH `{}` hoặc giá trị không thay đổi trả 200 cùng ETag, không ghi audit.

```http
DELETE /api/v1/nha_cung_cap/<id>
Authorization: Bearer <token-quan-ly>
If-Match: "<etag-tu-get-chi-tiet>"
```

Trả 204, không body. Không xóa nếu có bất kỳ phiếu nhập tham chiếu, kể cả nháp.
PATCH cũng không đổi mã khi đã tham chiếu; vẫn cho sửa tên/liên hệ hoặc gửi lại mã cũ.
Thiếu If-Match trả 428, không khớp trả 412, mã trùng trả 409 `ma_bi_trung`, đang tham chiếu
trả 409 `dang_duoc_tham_chieu`. ID không có trả 404 trước khi kiểm tra ETag.
Yêu cầu một ETag cụ thể có dấu ngoặc kép; wildcard/weak/list/empty không khớp trả 412,
header If-Match lặp trả 422. A/N bị từ chối 403 ở ba đường dẫn ghi mới.

PATCH/DELETE dùng SELECT FOR UPDATE, đọc lại dữ liệu hiện tại, so ETag và kiểm tra
tham chiếu trong cùng transaction. Khóa parent phối hợp với FK của phiếu nhập để chống race.
POST cấp ID bằng `max(ID đang có, ID lịch sử audit nhà cung cấp)+1` dưới advisory lock
`(20261020, 1)` tới commit/rollback; cả POST legacy dùng cùng bộ cấp ID. Không dùng lại ID
đã xóa có audit; hết miền INTEGER trả 409. Không thêm sequence hoặc cột mới.

Ghi audit `tao`/`sua`/`xoa_nhap` và dữ liệu trong cùng transaction. PATCH lưu trước/sau,
DELETE lưu trước và sau là SQL NULL. Lỗi audit/commit rollback cả thay đổi dữ liệu.

## File thay đổi trong tác vụ

| File | Mục đích |
|---|---|
| `backend/app/modules/nha_cung_cap/router.py` | Năm API contract, quyền đọc A/Q và ghi Q, validation/If-Match, header/status/OpenAPI; giữ router legacy. |
| `backend/app/modules/nha_cung_cap/schemas.py` | Query, Create/Patch/Read, envelope; phân biệt bỏ qua/null trong PATCH. |
| `backend/app/modules/nha_cung_cap/ports.py` | Thêm khóa bản ghi, kiểm tra tham chiếu, cập nhật/xóa. |
| `backend/app/modules/nha_cung_cap/repository.py` | Truy vấn GET, cấp ID dưới khóa, SELECT FOR UPDATE, tham chiếu, UPDATE/DELETE, dịch lỗi unique/FK. |
| `backend/app/modules/nha_cung_cap/service.py` | Envelope/ETag, precondition, bất biến mã, điều phối transaction và audit. |
| `backend/app/modules/nha_cung_cap/models.py` | Bỏ Identity trong ORM để khớp SQL đã chốt, ID do repository cấp. |
| `backend/app/modules/nha_cung_cap/errors.py` | Các lỗi domain 409/412/428. |
| `backend/app/main.py`, `dependencies.py`, `models.py` | Cập nhật import từ suppliers sang nha_cung_cap. |
| `backend/app/core/exceptions.py` | Envelope lỗi contract và mapping các code 409/412/428. |
| `backend/app/modules/audit/schemas.py`, `repository.py` | Snapshot trước/sau, snapshot vắng lưu SQL NULL thay vì JSON null. |
| `backend/tests/test_suppliers_api.py` | 44 test hồi quy GET và tương thích legacy. |
| `backend/tests/test_supplier_writes.py` | 67 test CRUD, validation, quyền, rollback, cấp ID và các race với phiếu tham chiếu. |
| `.gitignore` | Cho phép lưu file test mới trong Git. |
| `docs/sequence/nha_cung_cap.md` | Tám sequence: năm endpoint contract và ba endpoint legacy thực tế. |
| `docs/suppliers-api-verification.md` | Quyết định, ví dụ, kết quả kiểm chứng và giới hạn. |

Các thay đổi có sẵn trong `infra/postgres/init.sql`, `docs/sequence/users.md`, tài liệu auth
được giữ nguyên, không phải thay đổi mới của tác vụ nhà cung cấp.

## Kết quả kiểm chứng

Môi trường: Windows, Python 3.13, FastAPI 0.144.0, Pydantic 2.14.1, PostgreSQL 16
trong container test tạm riêng, cổng 55442, database `xbike_supplier_writes_test`.
Test tái sử dụng fixture auth: schema ngẫu nhiên, outer transaction/savepoint và rollback.
Không dùng database `xbike_mrp` hoặc database demo của dev.

Trước triển khai, test vòng đời CRUD thất bại HTTP 404 vì đường dẫn POST chưa tồn tại.
Sau triển khai:

- **111/111 test nhà cung cấp đạt** (44 GET, 67 ghi): phân trang/default/biên, filter/sort, chuỗi SQL và
  wildcard, query lạ/lặp, ID sai/quá lớn/không tồn tại, NULL legacy, ETag ổn định/thay đổi.
- Test quyền A/Q/N, thiếu token, khóa account ở API ghi; các test auth hiện có kiểm tra
  JWT sai/hết hạn/thu hồi và vai trò từ database.
- CRUD/audit cùng transaction, rollback khi audit lỗi, nullable/omitted field, snapshot SQL NULL,
  mã trùng, thiếu/cũ If-Match, ID hết miền, không dùng lại ID đã xóa, POST legacy dùng bộ cấp ID mới.
- Concurrency với connection độc lập: hai PATCH cùng ETag chỉ một thành công, PATCH/DELETE,
  hai DELETE, sáu POST khác mã và sáu POST trùng mã. Audit chỉ ghi cho request thắng.
- Race phiếu tham chiếu: quan sát `pg_blocking_pids` để xác nhận request đang chờ khóa thực tế.
  Phiếu thắng trước thì PATCH mã/DELETE bị 409; DELETE thắng trước thì INSERT phiếu bị FK chặn.
- Theo dõi câu SQL khi GET: chỉ SELECT và điều khiển savepoint/rollback, không INSERT/UPDATE/DELETE.
- Test OpenAPI: schema, query, security, status và header ETag; kiểm tra tương thích GET legacy.
- Kiểm tra lỗi nội bộ: HTTP 500 envelope an toàn, không echo thông tin nội bộ.
- **Toàn bộ backend: 146 passed, 1 failed**. Test có sẵn
  `test_legacy_login_endpoints_issue_revocable_tokens` thất bại vì `/api/v1/auth/login`
  không còn trong router auth, nhận 404. Đã đối chiếu `git show HEAD:backend/app/modules/auth/router.py`:
  đây là trạng thái của commit `b1e9499` trước tác vụ này, không sửa hoặc bỏ qua test.
- Ruff lint và format cho toàn bộ file Python thay đổi: đạt. Ruff toàn backend còn lỗi có sẵn
  `LoginRequest` import không dùng và thiếu dòng trống trong `app/modules/auth/router.py`.
- `git diff --check`: đạt.
- Mermaid CLI render thành công **8 sơ đồ** bằng Chromium headless.
- Structure map: không có misplaced/mixed/cycles/unreferenced trong module; ba nhóm
  đoạn giống nhau thuộc các hàm legacy đã tồn tại. Không refactor các module ngoài phạm vi.
- Kiểm tra boundary tự động không chạy được vì project chưa khai báo block `clean-architecture`.
  Đã rà soát import: SQL ở repository, service không import FastAPI/SQLAlchemy,
  composition ở dependencies/main, router xử lý HTTP và role dependency.

Kiểm tra bổ sung với HTTP thật qua Uvicorn cổng 8020:

1. Xác nhận schema public test trống, nạp `init.sql` và `seed.sql` thành công.
2. Đăng nhập ba vai trò seed, A/N tạo mới bị 403. Q thực hiện tạo/sửa/xóa nhận 201/200/204,
   Location/ETag khớp GET, nullable field được xóa đúng.
3. Trùng mã nhận 409, thiếu If-Match nhận 428, token ETag cũ nhận 412;
   xóa/đổi mã nhà cung cấp seed có phiếu tham chiếu nhận 409.
4. Lần smoke đầu phát hiện snapshot vắng bị lưu JSON null. Đã thêm test tái hiện thất bại,
   sửa repository audit bằng `exclude_none=True`, kiểm tra lại SQL NULL thành công.
5. Lần smoke cuối: **19/20 bảng public giữ nguyên checksum** sau vòng đời tạo/sửa/xóa,
   bao gồm nhà cung cấp, tồn kho và chứng từ. Audit thêm đúng 3 dòng tao/sua/xoa_nhap,
   snapshot trước/sau đúng. Uvicorn test đã dừng sau kiểm tra.

Lệnh chạy test từ `backend/`, sau khi chuẩn bị PostgreSQL test riêng:

```powershell
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://<user>:<password>@127.0.0.1:<port>/<database>_test'
$env:ENVIRONMENT = 'test'
..\.venv\Scripts\python.exe -m pytest tests/test_suppliers_api.py tests/test_supplier_writes.py -q
```

Không chạy GitHub Actions remote, không tạo PR, không commit/push. Full-suite/CI chưa xanh
do lỗi auth nêu trên. Không khẳng định bộ test toàn dự án đã đạt.

## Rollback

Mức rủi ro HIGH theo checklist clean-code vì có endpoint/phân quyền và handler lỗi dùng chung.
Không có migration hay dữ liệu ứng dụng đã bị agent thay đổi để rollback. Nếu cần gỡ tính năng,
gỡ các route ghi mới cùng dependency/nhánh service/repository tương ứng theo diff đã review.
Giữ hai GET và bảo đảm POST legacy vẫn cấp ID đúng với SQL không tự tăng. Không hoàn nguyên
verifier audit/ORM một phần làm mất khả năng đọc snapshot nullable hoặc làm POST thiếu ID.
Nếu API đã được dùng trên môi trường thật, rollback code không hoàn tác các thay đổi dữ liệu
người dùng đã thực hiện; không xóa audit hoặc phục hồi dữ liệu tự động.
Giữ việc đổi tên thư mục đã được dev xác nhận và các import đồng bộ với nó;
không chỉ khôi phục import `suppliers` khi thư mục cũ không còn. Không hoàn tác toàn bộ
working tree vì còn các thay đổi của dev ngoài tác vụ này.
