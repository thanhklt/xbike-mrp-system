# Kiểm chứng API phiếu nhập — 22/10/2026

## Phạm vi và nguồn

Triển khai API-033 đến API-038 theo [API contract v2](https://drive.google.com/file/d/16hj1yTLvhQ4peRENCLjbCKhNdGy_L2Xz/view), mục 2, 3, 5, 7, 13, 14, 17; đối chiếu `infra/postgres/init.sql` và ORM đang có. Ảnh đầu việc dẫn contract v1, nhưng quyết định của project là tiếp tục contract v2. Đợt bổ sung hiện tại tập trung PATCH, DELETE và hoàn tất.

| API | Quyền | Kết quả |
|---|---|---|
| GET /api/v1/phieu_nhap | Q | 200, danh sách và meta phân trang |
| GET /api/v1/phieu_nhap/{id} | Q | 200, chi tiết và ETag; không tồn tại 404 |
| POST /api/v1/phieu_nhap | Q | 201, phiếu nháp, Location và ETag |
| PATCH /api/v1/phieu_nhap/{id} | Q | 200, chỉ sửa nháp, ETag mới nếu có thay đổi |
| DELETE /api/v1/phieu_nhap/{id} | Q | 204 không body, chỉ nháp chưa có phụ thuộc |
| POST /api/v1/phieu_nhap/{id}/hoan_tat | Q | 200, cộng tồn, ledger, trạng thái và audit atomic; retry không ghi lại |

Tạo/sửa/xóa nháp không cập nhật tồn hoặc ledger. Ba thao tác trên resource đã tồn tại yêu cầu If-Match: thiếu 428, cũ 412. Hoàn tất đã thành công cho phép ETag cũ khi retry, nhưng vẫn yêu cầu có header. PATCH và DELETE không có ngoại lệ retry này.

Phương án áp dụng:

- Giữ thư mục dev đã đổi tên thành `phieu_nhap`, cập nhật import từ `receiving`.
- Theo xác nhận của dev: giữ ID INTEGER không tự tăng trong SQL; bỏ Identity sai trong ORM, backend cấp ID hai bảng dưới khóa.
- Theo xác nhận của dev: GET giữ NULL của dữ liệu cũ. Thời gian không múi giờ đang lưu được hiểu là UTC; POST mới ghi đầy đủ, API mới trả ISO UTC có Z.
- Theo xác nhận bổ sung: giữ SQL `ton_kho.id` không tự tăng, bỏ Identity trong ORM và cấp ID dưới advisory transaction lock `(20261022, 2)`. Khôi phục route `/receiving` dùng chung allocator phiếu/chi tiết `(20261022, 1)`, giữ payload và quyền cũ.

Không thay đổi schema, không thêm migration/dependency, không sửa `.env`, không nạp seed hay ghi vào database ứng dụng. Route cũ `/receiving` giữ quyền/payload/response cũ, dùng chung bộ cấp ID với route mới.

## Các file thay đổi và vai trò

| File | Vai trò, thay đổi |
|---|---|
| `backend/app/modules/phieu_nhap/router.py` | Sáu route contract v2, quyền Q, validation query/body/header, OpenAPI; giữ ba route `/receiving` |
| `schemas.py` trong module | Create/Patch/Read/List/Action/error envelope; PATCH phân biệt bỏ trường và null, thay toàn bộ chi tiết; body hoàn tất chỉ `{}`; số nguyên nghiêm ngặt, nullable cũ và UTC |
| `service.py` trong module | Kiểm tra trạng thái, ETag dưới khóa, tính tiền, cập nhật/xóa nháp và audit; điều phối hoàn tất atomic và trả kết quả cũ khi retry |
| `repository.py` trong module | List/detail giữ khóa đọc để nhất quán phần đầu và chi tiết; FOR UPDATE khi sửa/xóa/hoàn tất, đọc nguồn ledger, thay dòng, xóa nháp, chuyển trạng thái; allocator chung với legacy |
| `ports.py` trong module | Interface khóa/cập nhật/xóa/hoàn tất và dữ liệu ReceiptPosting dùng kiểm tra ghi sổ lặp |
| `models.py` trong module | Hai PK dùng `autoincrement=False` khớp SQL; các cột hiện hữu giữ nguyên |
| `errors.py` trong module | Lỗi tham chiếu, trùng mã, ETag cũ 412, thiếu If-Match 428, đang được tham chiếu 409 |
| `backend/app/modules/inventory/models.py` | `StockLevel.id` dùng autoincrement=False đúng SQL; không thay schema database |
| `backend/app/modules/inventory/ports.py` | InventoryWriter và StockReceiptLine để service phiếu nhập không phụ thuộc repository SQL cụ thể |
| `backend/app/modules/inventory/repository.py` | Khóa tồn và cấp ID, kiểm tra số dư với ledger, chống tràn số, cộng tồn và tạo ledger trong transaction của bên gọi |
| `backend/app/core/exceptions.py` | Envelope v2 cho `/phieu_nhap`, mã lỗi phụ thuộc 409 |
| `backend/app/core/request_context.py` | Helper dùng chung kiểm tra query lặp và If-Match không lặp cho NCC/phiếu nhập |
| `backend/app/main.py`, `dependencies.py`, `models.py` | Wiring/import theo tên thư mục mới, phục hồi import router bị thiếu; inject inventory repository cùng session với receipt/audit |
| `backend/app/modules/nha_cung_cap/repository.py` | Import GoodsReceiptNote từ `phieu_nhap` để kiểm tra tham chiếu |
| `backend/app/modules/nha_cung_cap/router.py` | Dùng helper query và If-Match từ core, không đổi hành vi endpoint |
| `backend/tests/test_supplier_writes.py` | Đổi import model phiếu nhập theo tên thư mục mới |
| `backend/tests/test_phieu_nhap_api.py` | Test HTTP, database, concurrency, rollback, validation, legacy và OpenAPI |
| `backend/tests/test_phieu_nhap_actions.py` | 79 ca mới cho PATCH/DELETE/hoàn tất, quyền, ETag, retry, concurrency, rollback từng bước và GET nhất quán |
| `.gitignore` | Cho phép theo dõi test phiếu nhập mới |
| `docs/sequence/phieu_nhap.md` | Chín endpoint hiện hữu, chín sequenceDiagram, luồng thành công/lỗi, header và transaction |
| Tài liệu này | Bằng chứng kiểm thử, cách thử và hướng rollback |

Git hiển thị xóa `receiving/` và thêm `phieu_nhap/` vì thư mục đã được dev đổi trước tác vụ. Không phục hồi hoặc ghi đè việc đổi tên đó. `__init__.py` được giữ theo nội dung cũ.

## Kiểm thử tự động

Môi trường kiểm tra hiện tại: PostgreSQL 16 Alpine trong container riêng `xbike-receipt-actions-test-20261022`, cổng localhost 55444, database `xbike_receipt_actions_test`, tmpfs và tự xóa container khi dừng. Mỗi test thông thường dùng schema ngẫu nhiên và rollback; test concurrency dùng schema riêng, kết nối độc lập. Không dùng database ứng dụng.

Lệnh từ thư mục `backend`, `TEST_DATABASE_URL` phải trỏ tới PostgreSQL test có tên database kết thúc `_test`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_phieu_nhap_api.py tests/test_phieu_nhap_actions.py -q
..\.venv\Scripts\python.exe -m pytest -q
```

Phạm vi kiểm thử phiếu nhập:

- JWT thiếu 401, A/N bị chặn 403, account bị khóa chặn token còn hiệu lực; Q tạo/đọc được.
- JSON integer nghiêm ngặt, giá không âm, lượng dương, ID hợp lệ, trường dư, trường server quản lý, dòng trùng và overflow tổng tiền trả 422.
- Phân trang, whitelist sort, q literal `%`/`_`, query giả SQL, ngày đảo ngược, ngày đúng YYYY-MM-DD, UTC boundary của ngày Việt Nam, query lặp/lạ.
- GET chi tiết 404/422, envelope, request_id, ETag ổn định và thay đổi theo dòng chi tiết; kiểm tra GET không phát sinh INSERT/UPDATE/DELETE.
- Tiền server tính, người tạo từ JWT, trạng thái nhap, Location, UTC Z, dữ liệu cũ NULL.
- Thiếu NCC/mặt hàng 404; mặt hàng không active (kể cả NULL), bán thành phẩm/thành phẩm 409.
- Audit thất bại sau flush: rollback cả phiếu, mọi dòng và audit; HTTP 500 không lộ chi tiết lỗi nội bộ.
- Sáu POST đồng thời có barrier: mỗi phiếu/mã/dòng một ID riêng, audit đúng sáu bản ghi, không phát sinh tồn/ledger.
- Mã tháng đổi lúc 17:00 UTC; xét snapshot audit trước xóa; không dùng lại ID/mã đã được ghi lịch sử. Hết dải ID phiếu/dòng/mã trả 409.
- DELETE NCC hoặc khóa mặt hàng đang giữ transaction: POST thực sự chờ khóa (xác minh pg_blocking_pids), sau commit đọc lại và trả 404/409; không ghi phiếu/audit dở dang.
- Route cũ `/receiving` cùng allocator, giữ `items`/response cũ; OpenAPI cho sáu route mới đủ schema/status/header/security.
- PATCH giữ trường bỏ qua, cho xóa NCC bằng null, thay toàn bộ chi tiết và cấp ID mới; không đổi dữ liệu thì giữ ETag, không ghi audit. Từ chối null/rỗng/trùng dòng, trường do server quản lý, thiếu tham chiếu và mặt hàng không được nhập.
- If-Match thiếu 428, cũ/weak/wildcard 412, header lặp 422, ID không tồn tại 404; quyền A/N bị chặn cả ba action. Phiếu đã hoàn thành hoặc nháp có ledger không sửa/xóa được.
- Hoàn tất tạo một ledger mỗi dòng, cộng đúng tồn cho dòng mới và dòng đã tồn tại, đúng người ghi sổ; retry ETag cũ trả ID ledger cũ, không thêm audit hoặc cộng tồn. Trạng thái hoàn thành thiếu ledger không được coi là retry thành công.
- Nháp cũ sai tổng/thiếu giá/rỗng, lệch số dư-ledger, tràn tồn hoặc hết ID tồn trả 409; không ghi dở dang.
- Cố ý gây lỗi sau cập nhật tồn, ledger, trạng thái và audit: rollback tất cả, phiếu vẫn nháp; gửi lại thành công. PATCH/DELETE lỗi audit cũng rollback thay đổi/xóa.
- Hai request đồng thời có barrier: PATCH/PATCH, PATCH/DELETE, DELETE/DELETE, hoàn tất/hoàn tất, hoàn tất/PATCH, hoàn tất/DELETE. Sáu phiếu khác nhau hoàn tất song song cùng mặt hàng vẫn cộng đúng tổng tồn, đủ ledger và audit.
- Tái hiện GET đọc phần đầu cũ và chi tiết mới khi PATCH chen giữa: cả GET list/detail thất bại trước sửa; khóa FOR SHARE giúp hai test qua. Xác minh PATCH thực sự chờ khóa bằng pg_blocking_pids.

Kết quả cuối trên toàn backend: **299 passed, 1 failed** trong 52.78 giây, gồm **153/153 test phiếu nhập qua** (74 ca trước + 79 ca action). Lỗi baseline đã xác định: `test_legacy_login_endpoints_issue_revocable_tokens` gọi `/api/v1/auth/login` trả 404 vì route cũ không còn; tác vụ phiếu nhập không sửa module auth. Không có test bị skip. Kết quả này được chạy sau chỉnh OpenAPI và đăng ký ORM lần cuối.

Ruff check PASS, Ruff format check PASS trên 25 file trong phạm vi kiểm tra; git diff --check PASS. Ruff toàn backend còn unused `LoginRequest` và thiếu dòng trống trong `auth/router.py`, có từ trước. Test legacy receiving phát ra DeprecationWarning của `datetime.utcnow()` cũ; không gây thất bại.

Structure map: không thấy module misplaced/mixed, vòng phụ thuộc hoặc mã không được tham chiếu trong phạm vi phiếu nhập. Có các nhóm router/constructor giống hình dạng với module khác, giữ riêng theo nghiệp vụ. Boundary script không kiểm tra tự động được vì project chưa khai báo block `clean-architecture`; đã rà import thủ công: router gọi service, service dùng port/schema/transaction/audit port, SQL nằm trong repository.

Mermaid CLI render thành công **9/9 sơ đồ**. Kiểm tra đăng ký ORM bằng process độc lập: `import app.models`, đọc `Base.metadata.sorted_tables` nhận đủ **20 bảng**, bao gồm phiếu và chi tiết theo tên module mới. Structure map inventory không có cycle/mixed/misplaced; hai tên route cũ list_0/list_1 được giữ ngoài phạm vi thay đổi.

Trong vòng kiểm tra OpenAPI cuối, việc đặt min_length ngoài union có SkipJsonSchema làm explicit null ném TypeError. Test PATCH null đã phát hiện lỗi; chuyển ràng buộc vào nhánh list, kiểm tra lại 11 ca validation/OpenAPI qua, rồi chạy toàn suite cho kết quả cuối ở trên. Schema hiện công bố mảng minItems=1, không nullable; bỏ trường vẫn giữ nguyên chi tiết, gửi null trả 422.

## Kiểm thử HTTP trên schema SQL thật

Đã xác minh public có 0 bảng trước khi nạp `init.sql` và `seed.sql` vào database test riêng. Nạp thành công, bao gồm trigger append-only ledger/audit. Ba cột ID phiếu/chi tiết/tồn kho có `is_identity=NO` và không có column_default, đúng trường hợp cần backend cấp ID.

Chạy Uvicorn trên cổng 8022, gọi HTTP bằng httpx, đăng nhập tài khoản seed Q/A. Sau đăng nhập lấy checksum 20 bảng rồi thực hiện:

- A gọi PATCH/DELETE/hoàn tất: đều 403.
- Q tạo phiếu hai dòng: 201. PATCH thiếu header 428; PATCH có ETag đúng đổi lượng mỗi dòng từ 2 lên 3, tổng tiền 1200 và ETag mới.
- Hoàn tất với ETag trước PATCH trả 412; ETag hiện tại trả 200, trạng thái hoan_thanh. Phiếu ID 2 tạo ledger ID 17, 18; tồn mỗi mặt hàng tăng đúng 3, toàn bộ số dư khớp ledger.
- Retry hoàn tất với ETag cũ trả 200, da_ghi_so_truoc_do=true, cùng hai ID ledger; checksum cả 20 bảng giữ nguyên sau retry.
- GET chi tiết trả ETag giống action. DELETE phiếu đã hoàn tất trả 409.
- Tạo nháp thứ hai rồi DELETE trả 204 không body; GET sau xóa trả 404.
- Thêm đúng năm audit: hai tao, một sua, một hoan_tat, một xoa_nhap. Chỉ năm bảng phiếu, chi tiết, tồn, ledger và audit đổi checksum. **15/20 bảng còn lại giữ nguyên**.
- Uvicorn test đã dừng trong khối finally sau kiểm tra. Sau toàn suite cuối, xác minh đúng tên container, port 55444 và tmpfs rồi dừng container test (chế độ --rm tự xóa); không thay đổi cấu hình backend đang dùng của dev.

## Thử trên Swagger

Chạy Uvicorn như trước, vào `http://localhost:8000/docs`, Authorize bằng tài khoản Q. Dùng nhóm `phieu_nhap`.

```json
{
  "ncc_id": 1,
  "chi_tiet": [
    {"mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": 10000}
  ]
}
```

Thay ID bằng NCC và NVL/linh kiện đang active thực tế. Có thể bỏ `ncc_id` hoặc gửi null. Không gửi ma_phieu_nhap, nhan_vien_id, created_at, trang_thai, tong_tien, tong_gia hoặc ID dòng. Kết quả tổng tiền ví dụ là 30000; mã/ID server tự tạo. Sau POST, dùng Location để GET chi tiết.

Ví dụ lọc: `/api/v1/phieu_nhap?trang_thai=nhap&tu_ngay=2026-10-01&den_ngay=2026-10-31&sort=-created_at&page=1&page_size=20`.

Để sửa, sao chép nguyên ETag từ GET (kể cả dấu ngoặc kép) vào header If-Match của PATCH. Ví dụ body `{"ncc_id": null}` bỏ NCC; gửi `chi_tiet` sẽ thay toàn bộ bộ dòng. Lấy ETag mới từ response sau sửa.

Để hoàn tất, gọi `POST /api/v1/phieu_nhap/{id}/hoan_tat`, body `{}`, If-Match là ETag mới nhất. Thành công trả trạng thái hoan_thanh, danh sách ID ledger và `da_ghi_so_truoc_do=false`. Gửi lại cùng yêu cầu trả true mà không cộng thêm tồn. Để xóa nháp, gọi DELETE với ETag hiện tại; phiếu đã hoàn tất không được sửa/xóa. Mọi thao tác đều cần tài khoản `quan_ly`.

## Giới hạn và rollback

Mức rủi ro HIGH do thay đổi API ghi dữ liệu, quyền và concurrency. Chưa có CI từ xa, PR hoặc triển khai production; không commit/push.

Allocator phối hợp các writer đi qua repository này; writer SQL ngoài ứng dụng phải tuân thủ cùng khóa. Giữ được lịch sử cấp ID/mã nhờ snapshot audit hiện có; dữ liệu đã xóa ngoài ứng dụng mà không có lịch sử không thể được khôi phục để biết mã cũ. Việc quét lịch sử để cấp số phù hợp quy mô hiện tại, cần đo lại khi audit lớn.

Các route `/receiving` cũ vẫn có quyền A/Q/N và validation khác contract v2; loại bỏ hoặc đổi quyền của chúng là thay đổi tương thích riêng, chưa thực hiện trong tác vụ này. Hoàn tất sẽ kiểm tra lại các dòng và tiền của nháp cũ, không tự điền giá hoặc sửa tổng sai.

Ghi sổ tồn kho hiện tuần tự hóa các phiếu nhập qua khóa advisory chung để bảo vệ ID thủ công và dòng tồn chưa có. Writer kho tương lai/SQL ngoài ứng dụng phải phối hợp cùng khóa và thứ tự khóa, nếu không không được coi là đã bảo đảm concurrency. Cần đánh giá lưu lượng trước khi thay bằng chiến lược khóa tinh hơn. GET list dùng COUNT riêng nên không cam kết tổng số và trang là một snapshot khi có tạo/xóa đồng thời; nội dung mỗi phiếu và chi tiết được giữ nhất quán.

Rollback code theo từng thay đổi của tác vụ: ngừng expose các route bị ảnh hưởng và use case liên quan nếu cần, giữ việc đổi thư mục/import của dev và allocator phù hợp SQL cho writer cũ. Không rollback toàn working tree, không hoàn tác các thay đổi có sẵn của dev. Không có migration để chạy down. Phiếu đã hoàn tất và ledger/audit đã ghi không được xóa để rollback: cần đối soát và quy trình điều chỉnh kho được phê duyệt riêng. Rollback code không hoàn tác dữ liệu nghiệp vụ đã commit.
