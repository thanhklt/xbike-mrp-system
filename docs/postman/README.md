# Bộ kiểm thử API xBike cho Postman

Xuất ngày **16/11/2026, Asia/Saigon**, từ Swagger đang chạy tại
`http://localhost:8000/docs`, sử dụng schema `http://localhost:8000/api/v1/openapi.json`.
Phiên bản API trong schema: `0.1.0`.

## File để import

| File | Mục đích |
| --- | --- |
| `xBike.Local.postman_environment.json` | URL, tài khoản, token, ID và ETag dùng chung |
| `xBike.Smoke.postman_collection.json` | 182 request: health, đăng nhập, đọc, lỗi xác thực/phân quyền/đầu vào và không tìm thấy |
| `xBike.Catalog.postman_collection.json` | 25 request theo thứ tự: vòng đời mặt hàng/BOM ban đầu/nhà cung cấp và lỗi 409/412/422/428 |
| `xBike.API.postman_collection.json` | 81 request bao phủ đủ 79 cặp method + đường dẫn của Swagger; đăng nhập JSON có thêm hai biến thể vai trò |

Collection dùng [định dạng Postman v2.1](https://schema.postman.com/collection/json/v2.1.0/draft-07/docs/index.html).

## Chạy nhanh

1. Khởi động backend và kiểm tra `http://localhost:8000/docs`.
2. Trong Postman, chọn **Import**, nhập bốn file JSON ở trên.
3. Chọn environment **xBike Local**. `base_url` mặc định là `http://localhost:8000`, không thêm `/api/v1` vào biến này.
4. Điền tài khoản đang có trong database vào các biến sau, lưu giá trị dùng tại máy của bạn:

   | Vai trò | Tên đăng nhập | Mật khẩu |
   | --- | --- | --- |
   | Quản trị viên — `quan_tri_vien` | `admin_username` | `admin_password` |
   | Quản lý — `quan_ly` | `manager_username` | `manager_password` |
   | Nhân viên — `nhan_vien` | `employee_username` | `employee_password` |

5. Chọn collection **xBike - Smoke and negative tests**, chọn **Run**, chạy một iteration theo thứ tự đã có.
6. Xem **Test Results** và **Postman Console**. Thiếu tài khoản, token hoặc dữ liệu thì request được bỏ qua với thông báo `SKIP`; request bị bỏ qua chưa được kiểm thử và không được tính là pass.

Mật khẩu và token được để trống trong file xuất. Các request đăng nhập lưu token vào
`admin_token`, `manager_token`, `employee_token`; `/auth/token` dùng form URL encoded và lưu
`manager_token`. Đăng nhập thành công có ghi audit theo hành vi ứng dụng.
Nếu dùng Postman trên web, chọn Desktop Agent có thể truy cập localhost.

Script dùng [`pm.execution.skipRequest()`](https://learning.postman.com/docs/tests-and-scripts/write-scripts/postman-sandbox-reference/pm-execution/#pmexecutionskiprequest);
cần bản Postman hỗ trợ API này. Chưa kiểm tra khả năng chạy bằng Newman.

## Nội dung bộ smoke

| Thư mục | Số request | Kiểm tra |
| --- | ---: | --- |
| `00 - Public health` | 3 | Root, health, ping |
| `01 - Login` | 3 | Đăng nhập theo ba vai trò, token, thời hạn, vai trò, header chống cache |
| `02 - Read APIs` | 34 | Các GET có xác thực, schema phản hồi, phân trang, header được khai báo |
| `03 - Missing or invalid token` | 75 | Thiếu token trên 74 operation có bảo vệ; token sai trên `/auth/me` |
| `04 - Employee forbidden` | 10 | Nhân viên bị từ chối ở các API dành cho quản lý/quản trị |
| `05 - Input validation` | 46 | Trang 0, page_size 101, ID không phải số, body đăng nhập thiếu/rỗng/thừa trường |
| `06 - Resource not found` | 11 | GET chi tiết với `missing_id`, mặc định `2147483647`; ID này phải không tồn tại |

Các kiểm tra đối chiếu **mã HTTP cụ thể**, schema khi OpenAPI có khai báo, mã lỗi và
envelope tương ứng. Lỗi 500 không được tính là thành công. Không đặt ngưỡng thời gian phản hồi tùy ý.

Các danh sách tự chọn ID đọc đầu tiên vào `read_<module>_id` khi biến này đang trống.
Nếu danh sách trống, GET chi tiết sẽ được bỏ qua. Xóa các biến `read_*_id` để chọn lại sau khi đổi database.
Hai GET preview kiểm tra/hủy yêu cầu sản xuất dùng `preview_yeu_cau_san_xuat_id` riêng:
chọn yêu cầu có trạng thái phù hợp và được giao cho tài khoản nhân viên đang dùng khi kiểm tra vật tư.
Các ca này không tự giả định mọi bản ghi đều đủ điều kiện nghiệp vụ.

Các ca thiếu token có cả POST/PATCH/PUT/DELETE với **No Auth** để kiểm tra từ chối trước
xử lý nghiệp vụ. Chúng không gắn token hợp lệ, và không phụ thuộc `allow_writes`.
Các GET và middleware ứng dụng có thể được ghi vào thống kê truy cập như thông thường.

## Chạy kịch bản danh mục có ghi dữ liệu

1. Trỏ `base_url` tới backend sử dụng **database test riêng** và điền `manager_username`, `manager_password`.
2. Đặt `allow_writes` thành chuỗi `true`.
3. Chạy toàn bộ collection **xBike - Catalog lifecycle scenario** theo thứ tự, một iteration.

Kịch bản tự tạo mã SKU theo thời điểm chạy, tạo linh kiện rồi thành phẩm có BOM ban đầu;
kiểm tra SKU trùng, thiếu tên, thiếu/sai ETag; sửa và đọc lại để kiểm chứng dữ liệu lưu;
ngừng thành phẩm, kiểm tra vẫn đọc được và kích hoạt lại; tạo/sửa/đọc lại nhà cung cấp.
Sau các PATCH bị từ chối, kịch bản đọc lại để kiểm tra giá chưa bị đổi.

Kịch bản lưu ID mới vào `component_id`, `finished_product_id`, `mat_hang_id`, `bom_id`,
`nha_cung_cap_id` cùng ETag. Nó giữ lại linh kiện, thành phẩm, BOM và nhà cung cấp để đối chiếu;
không rollback, seed hoặc xóa database. Không có API xóa nhà cung cấp trong Swagger này.
Sau khi chạy, đưa `allow_writes` về `false` nếu muốn chặn các thao tác ghi tiếp theo.

## Dùng bộ 79 endpoint theo module

**xBike - 79 endpoints (select requests manually)** là bộ request để chọn từng thao tác.
Không chạy toàn bộ như một luồng nghiệp vụ duy nhất: xóa nháp, hoàn tất, duyệt và từ chối
là các nhánh khác nhau, cần dữ liệu/trạng thái riêng.

- Request ghi chỉ gửi khi `allow_writes=true`; ID và token chưa có sẽ khiến request được bỏ qua.
- Chạy GET chi tiết đúng ID trước thao tác có `If-Match`. Script lưu ETag kèm ID; nếu đổi ID, phải GET lại. Giữ nguyên dấu nháy kép của ETag.
- Request tạo lưu ID từ phản hồi. Request danh sách trong bộ này chỉ điền ID khi đang trống; kiểm tra ID trước khi sửa, khóa hoặc xóa.
- Mẫu tạo mặt hàng mặc định là linh kiện. Nếu muốn ngừng mặt hàng bằng DELETE, chọn thành phẩm có BOM như trong kịch bản Catalog; code hiện từ chối ngừng linh kiện với 422.
- Tạo nhân viên: lấy `employee_role_id` từ GET `/vai_tro`; điền `test_employee_password`. Đặt lại mật khẩu dùng `test_employee_new_password`. Chỉ chọn tài khoản test.
- BOM: cần `component_id`; tạo thành phẩm với thuộc tính `bom` để có phiên bản đầu, sau đó lấy ID từ GET `/bom?mat_hang_id=<ID thành phẩm>`.
- Phiếu nhập: cần `nha_cung_cap_id`, `component_id`; body có ngày nhập, đơn giá và số lượng.
- Yêu cầu sản xuất: cần `finished_product_id`, `assigned_employee_id`, `due_date`. Đăng nhập nhân viên tự điền `assigned_employee_id`.
- Phiếu xuất và chứng từ hoàn thành: cần `yeu_cau_san_xuat_id`; nhân viên được giao lập/gửi, quản lý duyệt hoặc từ chối. Kiểm tra tồn, trạng thái và quyền sở hữu trước khi chọn action.
- Điều chỉnh: `source_receipt_id` là phiếu nhập nguồn đủ điều kiện; `source_movement_id` là giao dịch gốc của phiếu đó. Không dùng ID chứng từ thay cho ID giao dịch.
- Ticket cần ID có sẵn, chưa có endpoint tạo ticket trực tiếp. GET chi tiết trước khi nhận/giải quyết.
- Các query tùy chọn ở tab **Params** đang tắt; bật và điền giá trị khi cần lọc. Báo cáo dùng `report_year`, `report_month`.
- `today`, `due_date` và `test_run_id` tự điền khi trống. Xóa biến ngày để tạo lại cho lần chạy vào ngày khác.

## Nguồn đối chiếu và giới hạn

Đã đọc [api_contract_v3.1.md](https://drive.google.com/file/d/1Tlu5qwdwHaaz1G2aA--lfPeCp0kxiUZw/view)
và [mô hình dữ liệu v3.1](https://drive.google.com/file/d/1OdqHXKWbOwb47xcWwiraoKh9tGjecdQB/view),
đối chiếu OpenAPI runtime cùng router, schema, service và xử lý lỗi hiện tại.
Đây là bộ test API đang triển khai tại địa chỉ được yêu cầu; chưa phải bộ chứng nhận toàn bộ contract v3.1.

Những khác biệt cần lưu ý:

- Runtime còn `/audit`, `/inventory/*`; không tự thêm endpoint chỉ có trong contract.
- BOM và PATCH nhà cung cấp hiện dùng `If-Match`, dù contract v3.1 từng mô tả khác.
- Quyền đọc mặt hàng/nhà cung cấp và cấu trúc sản xuất đã thay đổi ở code hiện tại; test lấy quyền từ source tương ứng.
- `POST /inventory/movements` hiện ném `WorkflowNotImplemented`, handler trả **501**. Bộ API ghi rõ đây là giới hạn và kiểm tra 501, không coi là chức năng đã triển khai. OpenAPI đang khai báo 200 cho endpoint này.
- Chưa bao phủ đầy đủ cạnh tranh transaction, mọi trạng thái nghiệp vụ, ghi sổ/idempotency và đối chiếu ledger. Các action ngoài Catalog là request có assertion và điều kiện dữ liệu, chưa phải một kịch bản E2E tự dựng đủ dữ liệu sản xuất.

## Kết quả kiểm chứng khi xuất

- Cả ba collection hợp lệ với schema Postman v2.1 chính thức; URL/method khớp runtime OpenAPI, đủ **79/79 operation**, không thiếu biến environment được tham chiếu.
- **497 script** qua kiểm tra cú pháp Node.js; **245 schema phản hồi** biên dịch thành công bằng Ajv đang có trong workspace.
- Mô phỏng pre-request xác nhận **53 request ghi** trong bộ API/Catalog bị chặn khi giữ cấu hình mặc định.
- Đã quan sát **14 GET** trả status dự kiến trên backend: 3 public trả 200 và 11 request thiếu token trả 401. Đây là kiểm tra HTTP trực tiếp, chưa phải kết quả chạy bằng Postman.
- Sau đó kết nối bị reset; lần kiểm tra lại `GET /health` báo không kết nối được. Lần thử 38 GET tiếp theo không lấy được phản hồi do lỗi kết nối, nên không có kết quả assertion live cho lượt đó.
- Chưa chạy đăng nhập, các ca cần token, hoặc kịch bản ghi trên database ứng dụng; chưa có thông tin đăng nhập và database test riêng. Chưa chạy bằng Postman/Newman thực tế. Không xác nhận toàn bộ suite pass hoặc E2E pass.

Chỉ thêm các file xuất trong `docs/postman/`; không sửa frontend, backend, schema hay dữ liệu nghiệp vụ.
