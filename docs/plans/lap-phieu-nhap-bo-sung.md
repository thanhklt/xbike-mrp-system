# Plan: Lập phiếu nhập bổ sung từ yêu cầu chờ linh kiện; bỏ bảng tổng hợp UC-27

> Lập ngày 18/11/2026. **Dev duyệt 18/11/2026** (D1–D8 theo đề xuất). Dev đã chọn phương án A: điền sẵn phiếu nhập nháp, không gắn phiếu với yêu cầu. Dev yêu cầu thêm: bỏ thẻ "Tổng hợp theo linh kiện" trên trang Nhu cầu bổ sung LK.
> Người thực thi: Codex (`codex exec -m gpt-6.2-sol -s workspace-write`). Claude kiểm chứng (test liên quan, eslint, agent kiểm giao diện riêng) rồi báo dev. Không commit/push khi dev chưa cho phép.
> Spec chạm: [BR-009, BR-006](../../specs/business_requirements/BR-GIAIDOAN1.md), [UC-27](../../specs/use_cases/production/UC-27.md), [UC-20](../../specs/use_cases/goods_receipt/UC-20.md).

## Goal

1. Quản lý kho (QLK) đang xem một yêu cầu **Chờ bổ sung linh kiện** bấm "Lập phiếu nhập bổ sung" là mở form Tạo phiếu nhập đã điền sẵn các linh kiện thiếu của yêu cầu đó. QLK tự chọn nhà cung cấp, ngày nhập, sửa số lượng hoặc đơn giá, rồi Lưu nháp và Hoàn tất như bình thường.
2. Trang Nhu cầu bổ sung LK chỉ còn khối "Yêu cầu chờ bổ sung", mỗi yêu cầu còn thiếu có nút như trên.
3. Phiếu nhập vẫn **độc lập**: không lưu liên kết tới yêu cầu, không đổi API, không đổi DB. Yêu cầu vẫn ở Chờ bổ sung cho tới khi nhân viên kiểm tra lại (UC-26), như hiện nay.

## Hiện trạng

| Chỗ | Hiện trạng |
|---|---|
| `GET /api/v1/nhu_cau_bo_sung_linh_kien` (chỉ QLK) | Trả `{ yeu_cau: [{ id, ma_yeu_cau_san_xuat, …, linh_kien_thieu: [{ mat_hang_id, ma_mat_hang, ten_mat_hang, don_vi_tinh, so_luong_can, so_luong_con_dung, so_luong_thieu }], da_du }], tong_hop: [...] }`. Mỗi yêu cầu so riêng với "còn dùng được" hiện tại. |
| `ShortagePage.jsx` | 2 thẻ: "Tổng hợp theo linh kiện" (`SUMMARY_COLUMNS`) và "Yêu cầu chờ bổ sung". Không có thao tác nào (UC-27 AC-2). |
| `RequestsPage.jsx` chi tiết (QLK) | Hàng `.actions` có "Hủy yêu cầu…" và "Xem phiếu xuất kho →" (ẩn khi `cho_bo_sung_linh_kien`). |
| `ReceivingPage.jsx` `/kho/phieu-nhap/moi` | Form trống: NCC, ngày nhập, ghi chú, 1 dòng `newLine()`. Không đọc tham số URL nào cho form tạo. |
| Mẫu có sẵn | NV: `<Link className="btn btn-secondary" to={`/nv/xuat-nvl/moi?yeu_cau_san_xuat_id=${record.id}`}>Lập phiếu xuất linh kiện</Link>` (`RequestsPage.jsx` `IssueLinks`). QLK: `/kho/dieu-chinh/moi?phieu_nhap_id=…`, `AdjustmentsPage` đọc `useSearchParams` để điền sẵn. |

## Quyết định (dev xác nhận khi duyệt)

| # | Điểm | Đề xuất |
|---|---|---|
| D1 | Đường dẫn | `/kho/phieu-nhap/moi?yeu_cau_san_xuat_id={id}`, cùng tên tham số với luồng lập phiếu xuất của NV. |
| D2 | Nút | `<Link className="btn btn-secondary">Lập phiếu nhập bổ sung</Link>`. **Chi tiết yêu cầu:** chỉ QLK, chỉ khi `trang_thai === "cho_bo_sung_linh_kien"`, đặt trong hàng `.actions` cạnh "Hủy yêu cầu…". **Trang Nhu cầu bổ sung LK:** mỗi yêu cầu `!da_du`, đặt ngay dưới bảng thiếu của yêu cầu đó, trong `<div className="actions actions-end">`. Yêu cầu `da_du` giữ nguyên câu "Đã đủ linh kiện, chờ nhân viên kiểm tra lại.", không có nút. |
| D3 | Dữ liệu điền sẵn | Lấy từ `API.shortages` (đã có, chỉ QLK), tìm yêu cầu theo `id`. Mỗi dòng `linh_kien_thieu` thành 1 dòng phiếu: `mat_hang_id`, `so_luong = so_luong_thieu`, `don_gia_thuc = MatHang.don_gia` (lấy từ catalog, không có thì `"0"`). Ghi chú: `Bổ sung linh kiện cho {ma_yeu_cau_san_xuat}`. Nhà cung cấp và ngày nhập để trống như form tạo hiện nay. |
| D4 | Không còn gì để điền | Yêu cầu không có trong danh sách chờ (đã kiểm tra lại, đã hủy, id sai) hoặc `da_du`/không có dòng thiếu: hiện `<Notice>Yêu cầu này không còn linh kiện thiếu. Phiếu nhập được tạo trống.</Notice>` trên form, form trống như bình thường. |
| D5 | Không gắn phiếu với yêu cầu | Body `POST /phieu_nhap` giữ nguyên, **không** gửi `yeu_cau_san_xuat_id`. Không sửa backend, schema, `init.sql`, `docs/sequence`. Liên kết duy nhất là câu ghi chú do QLK sửa hoặc xóa được. |
| D6 | Bỏ bảng tổng hợp | Chỉ sửa FE: xóa thẻ "Tổng hợp theo linh kiện", `SUMMARY_COLUMNS` và phần đọc `tong_hop`. **Backend vẫn trả `tong_hop`** (không sửa BE theo AGENTS §4). Nếu muốn bỏ hẳn ở API và test BE AC-1 thì làm việc riêng. |
| D7 | Spec | Sửa BR-009 (Goal, In Scope, Out of Scope, kịch bản nghiệm thu), UC-27 (mô tả, hậu điều kiện, R2–R3, main flow, A1, AC-1–AC-2), UC-20 (thêm luồng mở từ yêu cầu chờ; R5 giữ). Nội dung cụ thể ở mục "Sửa spec". |
| D8 | Nhánh | Tạo nhánh `feature/lap-phieu-nhap-bo-sung` từ `main` trước khi Codex sửa. Hai thay đổi chưa commit của dev (`infra/postgres/seed.sql`, `docs/production-flow-gaps.md` đã xóa) giữ nguyên, Codex không đụng. |

## Danh sách thay đổi

### FE

1. **`frontend/src/features/receiving/receiptPrefill.js`** (mới, file riêng của trang Phiếu nhập)
   - `export function prefillReceipt(request, items)` → `{ ghi_chu, lines }`. `request` là phần tử `yeu_cau` của API shortages hoặc `undefined`. Trả `null` khi không có request, `da_du`, hoặc `linh_kien_thieu` rỗng (D4).
   - `lines` dùng `newLine({ mat_hang_id: String(id), so_luong: String(so_luong_thieu), don_gia_thuc: String(item?.don_gia ?? 0) })` từ `components/ResourceFields.jsx`.
   - Hàm thuần, không mutate input.
2. **`frontend/src/features/receiving/ReceivingPage.jsx`**
   - Đọc `search.get("yeu_cau_san_xuat_id")` (đã có `useSearchParams`). Chỉ khi `id === "moi"` và có tham số: `useResource(API.shortages, {}, enabled)`.
   - Trong `RecordPanel`: khi đang điền sẵn, bọc `ReceiptEditor` thêm `<QueryState query={shortages}>`, tìm request theo `Number(param)`, truyền `prefill={prefillReceipt(request, items)}` và `prefillMissing` (có tham số mà prefill `null`). `key` của editor theo tham số để đổi tham số là dựng lại form.
   - `ReceiptEditor`: `initial.ghi_chu` lấy `prefill?.ghi_chu` khi tạo mới. `lines` khởi tạo bằng `prefill?.lines` khi tạo mới, không có thì `[newLine()]`. Khi `prefillMissing`, hiện Notice D4 ngay trên form.
   - Không đổi `submit`, payload, luồng sửa, xóa, hoàn tất.
3. **`frontend/src/features/production/RequestsPage.jsx`**: trong khối `canCancelRequest(record, manager) && (<div className="actions">…)` thêm, sau nút "Hủy yêu cầu…": `{record.trang_thai === "cho_bo_sung_linh_kien" && <Link className="btn btn-secondary" to={`/kho/phieu-nhap/moi?yeu_cau_san_xuat_id=${record.id}`}>Lập phiếu nhập bổ sung</Link>}`. Khối này đã chỉ hiện cho QLK.
4. **`frontend/src/features/production/ShortagePage.jsx`**
   - Xóa `<Card title="Tổng hợp theo linh kiện">…</Card>`, `tong_hop: summary = []`, import `SUMMARY_COLUMNS`, `DataTable` nếu không còn dùng (vẫn dùng cho bảng thiếu nên giữ).
   - Nhánh `!record.da_du`: sau `<DataTable … SHORTAGE_COLUMNS />` thêm `<div className="actions actions-end"><Link className="btn btn-secondary" to={…}>Lập phiếu nhập bổ sung</Link></div>`. Bọc hai phần bằng fragment.
   - Đổi `subtitle` thành: "Xem linh kiện còn thiếu của từng yêu cầu sản xuất đang chờ và lập phiếu nhập bổ sung."
5. **`frontend/src/features/production/shortageView.js`**: xóa `SUMMARY_COLUMNS` (chỉ ShortagePage và test dùng). Sửa comment UC theo spec mới.

### Test FE

6. **`frontend/tests/uc27-shortage-page.test.js`**: bỏ test AC-1 bảng tổng hợp và import `SUMMARY_COLUMNS`. Test bố cục: danh sách `<Card title>` chỉ còn `["Yêu cầu chờ bổ sung"]`, `<QueryState query={query}>` còn 1, không còn `tong_hop`/"Không có linh kiện cần bổ sung.". Thay test "chỉ để xem / không có thao tác tạo phiếu nhập" (AC-2 cũ) bằng: nút `Lập phiếu nhập bổ sung` dẫn `/kho/phieu-nhap/moi?yeu_cau_san_xuat_id=${record.id}`, chỉ trong nhánh `!record.da_du`.
7. **`frontend/tests/uc27-lap-phieu-nhap-bo-sung.test.js`** (mới):
   - `prefillReceipt`: 2 dòng thiếu → 2 dòng đúng `mat_hang_id`/`so_luong_thieu`/`don_gia_thuc` từ `items`; thiếu giá → `"0"`; ghi chú đúng mã; trả `null` với `undefined`, `da_du: true`, `linh_kien_thieu: []`; không mutate input.
   - Đối chiếu nguồn `ReceivingPage.jsx`: đọc `yeu_cau_san_xuat_id`, gọi `API.shortages` có điều kiện, câu Notice D4 chính xác, `submit` body không có `yeu_cau_san_xuat_id`.
   - Đối chiếu nguồn `RequestsPage.jsx`: link chỉ khi `cho_bo_sung_linh_kien`, đúng nhãn và đường dẫn, dùng `btn btn-secondary`.
   - Mỗi test có comment `// UC-27 …` hoặc `// UC-20 …` theo quy ước.

### Spec (D7)

8. **BR-009** (`specs/business_requirements/BR-GIAIDOAN1.md`)
   - Goal: "Quản lý kho xem các yêu cầu đang chờ bổ sung linh kiện, biết từng yêu cầu thiếu gì và lập nhanh phiếu nhập bổ sung."
   - In Scope: giữ dòng danh sách yêu cầu chờ; **bỏ** "Tổng hợp theo linh kiện…".
   - Thay "Chỉ để xem; Quản lý kho tự lập phiếu nhập theo BR-006" bằng: "Từ một yêu cầu còn thiếu, Quản lý kho mở form tạo phiếu nhập đã điền sẵn linh kiện thiếu (số lượng = thiếu, đơn giá = đơn giá mặt hàng) và ghi chú mã yêu cầu; Quản lý kho tự chọn nhà cung cấp, ngày nhập, sửa rồi lưu theo BR-006. Phiếu nhập không gắn với yêu cầu."
   - Success Metrics: đổi `shortage_summary_accuracy` thành `prefill_accuracy = 100%` (dòng điền sẵn khớp linh kiện thiếu của yêu cầu).
   - Kịch bản nghiệm thu: "Yêu cầu thiếu 10 khung và 4 lốp → form tạo phiếu nhập có 2 dòng: khung 10, lốp 4."
   - Out of Scope: thay "Tự tạo phiếu nhập từ danh sách thiếu" bằng "Hệ thống tự lưu hoặc tự hoàn tất phiếu nhập; gắn phiếu nhập với yêu cầu sản xuất". Thêm "Tổng hợp nhu cầu theo linh kiện trên nhiều yêu cầu". Giữ thông báo và đề xuất nhà cung cấp.
9. **UC-27**: cập nhật Mô tả, Hậu điều kiện. R2 → "Mỗi yêu cầu còn thiếu có thao tác Lập phiếu nhập bổ sung, mở form tạo phiếu nhập điền sẵn theo UC-20" (BR-009). R3 → "Trang không ghi dữ liệu; phiếu nhập chỉ được tạo khi Quản lý kho lưu ở UC-20, không gắn với yêu cầu" (BR-009, BR-006). Main flow bước 3–4 theo đó. A1 bỏ "bảng tổng hợp". AC-1 → kịch bản nghiệm thu mới. AC-2 → "Yêu cầu đã đủ (chờ kiểm tra lại) không có nút Lập phiếu nhập bổ sung". Giữ AC-3. Thêm dòng trong bảng thuộc tính: "Mở rộng (extend): UC-20".
10. **UC-20**: thêm Alternative Flow "Mở từ yêu cầu chờ bổ sung (UC-27 hoặc chi tiết yêu cầu)": form điền sẵn theo BR-009; yêu cầu không còn thiếu thì form trống kèm thông báo. R5 giữ nguyên. Ghi chú ngoài phạm vi giữ "gắn phiếu nhập với yêu cầu sản xuất".

## Checklist giao diện (chỉ cho 3 vùng thay đổi, không phải checklist cả trang)

| Vị trí | Cách viết | Căn cứ |
|---|---|---|
| Nút sang trang tạo chứng từ từ một yêu cầu | `<Link className="btn btn-secondary">Lập phiếu …</Link>`, query `yeu_cau_san_xuat_id` | 3/3 nút "Lập phiếu…" trong `RequestsPage` (`IssueLinks`) dùng đúng dạng này |
| Hàng nút trong chi tiết yêu cầu QLK | Đặt trong `.actions` có sẵn cạnh "Hủy yêu cầu…" | Hàng này đã chứa nút phụ cùng loại ("Xem phiếu xuất kho →") |
| Nút dưới bảng trong một khối danh sách | `<div className="actions actions-end">` | `IssueLinks`, các hàng nút cuối form trong RequestsPage và ReceivingPage |
| Thông báo trên form khi không điền được | `<Notice>` của `components/QueryState.jsx`, câu kết thúc bằng dấu chấm | ShortagePage dùng `<Notice>` cho trạng thái tương tự ("Đã đủ linh kiện…") |
| Điền sẵn form tạo từ tham số URL | `useSearchParams` trong trang, khởi tạo state một lần | `AdjustmentsPage` (`phieu_nhap_id`) |

Phần không đọc: kiểu chữ, khoảng cách, màu (không thay đổi), các vùng khác của 3 trang.

## Codex: giới hạn

- Chỉ sửa đúng các file ở mục 1–10. Không sửa backend, `infra/`, `docs/sequence`, các file chưa commit của dev.
- Chỉ chạy: `cd frontend && node --test tests/uc27-shortage-page.test.js tests/uc27-lap-phieu-nhap-bo-sung.test.js tests/uc21-hoan-tat-phieu-nhap.test.js tests/uc23-create-send-request.test.js tests/uc24-edit-delete-send-draft.test.js tests/uc25-request-list.test.js tests/uc26-check-request.test.js tests/uc28-cancel-request.test.js tests/uc29-start-production.test.js` và `npx eslint` trên các file FE đã sửa. Không chạy toàn bộ test suite, không commit.

## Kiểm chứng (Claude)

- Chạy lại các test trên + eslint. Chạy toàn bộ `npm test` của frontend một lần, vì test đối chiếu nguồn của các UC khác có thể đọc `RequestsPage.jsx`/`ReceivingPage.jsx`.
- Agent riêng (không phải người viết) kiểm 3 vùng giao diện theo checklist trên.
- Đối chiếu spec sau sửa: BR-009, UC-27, UC-20 không còn câu mâu thuẫn ("chỉ để xem", "bảng tổng hợp").
- Không chạy backend, không gọi API (frontend chỉ dùng endpoint có sẵn).

## Phụ lục 1: bỏ `tong_hop` ở backend (dev yêu cầu và duyệt 18/11/2026, D9–D11 theo đề xuất)

Thay D6: backend cũng bỏ bảng tổng hợp, response chỉ còn danh sách yêu cầu.

| # | Điểm | Đề xuất |
|---|---|---|
| D9 | Hợp đồng API | `GET /api/v1/nhu_cau_bo_sung_linh_kien` trả `{data: {yeu_cau: [...]}, meta}`. **Thay đổi không tương thích ngược**: client nào đọc `tong_hop` sẽ không còn thấy. Trong repo chỉ có fixture test trình duyệt đọc trường này, trang FE đã bỏ ở bước trước. Endpoint, quyền, tham số, mã lỗi không đổi. |
| D10 | Tên hàm | Đổi `tong_hop_nhu_cau_bo_sung` → `danh_sach_nhu_cau_bo_sung`, vì hàm không còn tổng hợp. Logic tính `linh_kien_thieu`/`da_du` của từng yêu cầu giữ nguyên. |
| D11 | Test BE | Bỏ assert về `tong_hop`, không bỏ phần kiểm từng yêu cầu. Test chỉ kiểm tổng hợp thì bỏ hoặc thay bằng assert tương ứng trên `yeu_cau[].linh_kien_thieu`. Thêm assert `set(data) == {"yeu_cau"}`. Đổi nhãn comment test theo AC mới của UC-27 (AC-1 nay là điền sẵn ở FE). Test BE không còn mang nhãn AC-1, chỉ R1, AC-2, AC-3, A1 và D đã có. |

### Danh sách thay đổi

11. `backend/app/modules/san_xuat/schemas.py`: xóa `TongHopLinhKien`, bỏ trường `tong_hop` khỏi `NhuCauBoSungData`.
12. `backend/app/modules/san_xuat/service/yeu_cau_san_xuat.py`:
    - đổi tên hàm theo D10 và bỏ phần `totals`;
    - bỏ import `TongHopLinhKien`;
    - sửa comment UC thành `Main 2; R1 linh kiện thiếu của từng yêu cầu`;
    - cập nhật lời gọi trong `xem_nhu_cau_bo_sung`.
13. `backend/tests/test_uc27_nhu_cau_bo_sung.py` theo D11. Các test liên quan:
    - `test_two_requests_aggregate_twenty_frames`
    - `test_available_five_means_fifteen_total_and_five_each`
    - `test_replenished_requests_remain_without_missing_lines`
    - `test_pure_summary_keeps_zero_shortages_and_orders_by_shortage_then_code`
    - `test_empty_waiting_list_returns_empty_arrays`
    - `test_service_is_read_only_and_preserves_request_id`
    - `test_other_states_never_contribute_to_shortages`
    - `test_next_read_uses_current_availability`
14. `docs/sequence/san_xuat.md`, mục `GET /api/v1/nhu_cau_bo_sung_linh_kien` (AGENTS §8):
    - response mới;
    - tên hàm mới;
    - bỏ ghi chú tổng hợp;
    - nguồn ghi theo UC-27 mới (R1–R3, AC-2, AC-3, A1).
15. `frontend/tests/browser/api-fixture.js`: fixture trả `{ yeu_cau: [] }`.

### Kiểm chứng

- Codex chỉ chạy: `backend/.venv/Scripts/python -m pytest backend/tests/test_uc27_nhu_cau_bo_sung.py`, `ruff check` trên 3 file Python sửa, `node --test tests/uc27-*.test.js` trong `frontend/`.
- Claude chạy lại các lệnh trên. Grep `tong_hop|TongHopLinhKien` không còn trong `backend/app`, `backend/tests`, `docs/sequence`, `frontend`. Chạy toàn bộ backend pytest một lần, vì đây là thay đổi hợp đồng API.

## Kết quả

Kiểm chứng 18/11/2026 trên nhánh `feature/lap-phieu-nhap-bo-sung` (chưa commit):

- Codex (`gpt-6.2-sol`) sửa đúng mục 1–10. Không đụng backend, `infra/` (`seed.sql` vẫn là bản sửa của dev ngày 17/11), `docs/sequence`.
- `npm test` toàn bộ frontend: **313/313 pass**. ESLint trên 7 file sửa: 0 lỗi. `vite build` thành công (`dist/` đã được ignore).
- Kiểm giao diện bằng agent riêng: bước hiệu chỉnh tìm ra chỗ cố ý làm lệch (inline style, thiếu `actions-end`). Bản thật khớp checklist ở cả 3 vùng.
  - Điểm khác họ trang: `ReceivingPage` tự đặt `isPending` khi `isFetching && !isFetchedAfterMount` để form điền sẵn chờ dữ liệu mới, không khởi tạo từ cache cũ (state form chỉ khởi tạo một lần). Giữ lại vì có chủ ý.
  - Chưa render nên chưa kiểm khoảng cách và màu thực tế.
- Còn lệch nhỏ: vài comment test đổi nhãn chưa chuẩn. Ví dụ test danh sách rỗng ghi `UC-27 AC-1`, đúng ra là `UC-27 A1`. Các test bảng cột và thông tin yêu cầu cũng gắn `AC-1`.
- ~~Backend vẫn trả `tong_hop` (D6).~~ Đã xử lý ở Phụ lục 1.

Phụ lục 1, kiểm chứng 18/11/2026:

- Codex sửa đúng mục 11–15: bỏ `TongHopLinhKien`/`tong_hop`, đổi tên hàm thành `danh_sach_nhu_cau_bo_sung`, sửa test UC-27 backend (không còn nhãn AC-1), `docs/sequence/san_xuat.md`, fixture trình duyệt.
- Grep `tong_hop|TongHopLinhKien` chỉ còn một chỗ, là assert *không có* `tong_hop` trong `uc27-shortage-page.test.js`.
- Toàn bộ backend pytest: **1038 passed, 366 skipped**. Phần skip là test PostgreSQL, không có DB test khi chạy. Ruff trên 3 file Python: sạch.
- Toàn bộ frontend `npm test`: **313/313 pass**.
- Chưa render Mermaid, chỉ đối chiếu sơ đồ với code.
