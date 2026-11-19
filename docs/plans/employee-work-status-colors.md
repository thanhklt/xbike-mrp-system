# Kế hoạch sửa trạng thái Việc được giao

Quyết định: 18/11/2026. Hoàn tất triển khai và chạy Docker để dev thử: 19/11/2026.
Các mục 1–8 ghi kế hoạch đã chốt; mục 9 ghi kết quả thực hiện và giới hạn kiểm chứng.

## 1. Mục tiêu và quyết định đã chốt

Màn Việc được giao của Nhân viên hiển thị bước công việc cụ thể thay cho trạng thái yêu cầu tổng quát, kèm nền màu theo nhóm. Danh sách, chi tiết yêu cầu và bộ lọc phải dùng cùng quy tắc.

- Giữ đúng 9 nhãn ở mục 3. Bỏ ba nhãn Chờ gửi khỏi màn Việc được giao, vẫn giữ lưu nháp và gửi duyệt riêng.
- Giữ các trạng thái nghiệp vụ hiện có trong DB/API, không đổi chúng thành 9 trạng thái mới trong bảng.
- Mở form rồi Hủy khi chưa lưu: không tạo phiếu; yêu cầu vẫn hiển thị Đã giao. Hủy form khác với hủy yêu cầu.
- Khi kho thiếu linh kiện, NV vẫn được lập và gửi phiếu xuất linh kiện. QLK chờ đủ hàng mới duyệt xuất.
- Thiếu linh kiện hiển thị bằng cảnh báo, không là nhãn công việc riêng. Đủ hàng không tự duyệt phiếu.
- Chưa thêm nhãn mới cho các trường hợp sau từ chối; giữ luồng gửi lại và thông tin từ chối đang có.
- Bỏ notice giải thích kỹ thuật về giờ hệ thống ghi chứng từ; thông báo kiểm tra chỉ xác nhận thao tác, không hiển thị mã/trạng thái nội bộ cũ. Giữ lỗi và thông tin thiếu hàng.
- Chỉ đổi UI tại `/nv/yeu-cau`: bảng, chi tiết yêu cầu và bộ lọc xoay vòng. Không redesign Admin/QLK, KPI Tổng quan hoặc các dashboard chứng từ khác.

## 2. Nguồn đã đọc theo thứ tự spec → Drive → đối chiếu source

| Nguồn | Nội dung dùng để lập plan |
|---|---|
| `specs/use_cases/production/UC-25.md` | Quyền NV theo phân công, không thấy yêu cầu nháp; tìm/lọc trước phân trang |
| `specs/use_cases/production/UC-26.md` | Chốt số cần sản xuất và nhu cầu; giữ hàng; thiếu linh kiện không giữ một phần |
| `specs/use_cases/production/UC-29.md` | Chỉ bắt đầu sau khi phiếu xuất linh kiện đã duyệt |
| `specs/use_cases/production/UC-30.md`, `UC-31.md` | Chứng từ nháp/gửi/duyệt; hai cách hoàn thành theo loại yêu cầu |
| `specs/use_cases/goods_issue/UC-34.md`, `UC-35.md` | Một phiếu xuất linh kiện cho mỗi yêu cầu; gửi không trừ tồn, duyệt mới xuất |
| `specs/use_cases/goods_issue/UC-37.md`, `UC-38.md` | Điều kiện xuất thành phẩm; sản xuất nhập kho không có phiếu xuất thành phẩm |
| [API contract trên Drive](https://drive.google.com/file/d/1Tlu5qwdwHaaz1G2aA--lfPeCp0kxiUZw/view) | Đối chiếu sau spec; tài liệu còn mô tả lệnh sản xuất riêng và luồng không giữ hàng, khác spec hiện hành |
| Source FE/BE của yêu cầu, phiếu xuất, chứng từ và inventory | Xác định nơi cần thay đổi và các kiểm tra phải giữ |

Khác biệt đã xác định và cách xử lý:

- UC-34 R1/A1/AC-2 và code hiện chặn lập phiếu khi yêu cầu Chờ bổ sung linh kiện. Quyết định mới của dev trong phiên này cập nhật đúng điều kiện đó: cho lập/gửi sau khi nhu cầu đã chốt, dù thiếu hàng.
- Không lấy luồng lệnh riêng, tự kiểm tra khi nhập hoặc bỏ giữ hàng từ Drive để thay thế spec. Không đổi pipeline phiếu nhập trong tác vụ này.
- UC-26 vẫn là căn cứ chốt nhu cầu/giữ hàng. Phần bổ sung cần có để thực hiện quyết định mới là xử lý yêu cầu chưa giữ được linh kiện khi QLK duyệt xuất.
- Khi triển khai, cập nhật spec liên quan cùng code, ghi rõ quyết định mới. Không ghi chức năng chưa triển khai thành hiện trạng đã chạy.

## 3. Bảng nhãn hiển thị cuối cùng

| Mã bước công việc dự kiến | Nhãn UI | Điều kiện | Nhóm màu |
|---|---|---|---|
| `da_giao` | Đã giao | Yêu cầu đã gửi cho NV, chưa đến bước sau; phiếu xuất linh kiện chưa có hoặc còn nháp | Được giao |
| `cho_duyet_xuat_linh_kien` | Chờ duyệt phiếu xuất linh kiện | Phiếu xuất linh kiện đã gửi và đang chờ duyệt, kể cả còn thiếu hàng | Phiếu xuất |
| `san_sang_san_xuat` | Sẵn sàng sản xuất | Số cần sản xuất > 0, phiếu xuất linh kiện đã duyệt, chưa bắt đầu | Sản xuất |
| `dang_san_xuat` | Đang sản xuất | Đã bắt đầu, chứng từ hoàn thành chưa có hoặc còn nháp | Sản xuất |
| `cho_duyet_hoan_thanh` | Chờ duyệt chứng từ hoàn thành | Chứng từ hoàn thành đã gửi và đang chờ duyệt | Chứng từ hoàn thành |
| `cho_lap_phieu_xuat` | Chờ lập phiếu xuất | Yêu cầu xuất giao đủ điều kiện xuất thành phẩm; phiếu thành phẩm chưa có hoặc còn nháp | Phiếu xuất |
| `cho_duyet_phieu_xuat` | Chờ duyệt phiếu xuất | Phiếu xuất thành phẩm đã gửi và đang chờ duyệt | Phiếu xuất |
| `hoan_thanh` | Hoàn thành | Yêu cầu đã hoàn thành theo loại nhập kho/xuất giao | Hoàn thành |
| `da_huy` | Đã hủy | Yêu cầu đã hủy | Đã hủy |

Quy tắc xác định nhãn:

1. Xét Hoàn thành/Đã hủy của yêu cầu trước; sau đó xét bước hợp lệ mới nhất của các chứng từ liên quan. Phiếu xuất linh kiện đã duyệt không được che bước sản xuất hoặc xuất thành phẩm phía sau.
2. Chưa kiểm tra hoặc số cần sản xuất còn null không được coi là đã đủ thành phẩm. Chỉ đi thẳng tới Chờ lập phiếu xuất sau khi kiểm tra đã chốt số cần sản xuất = 0.
3. Yêu cầu cần sản xuất: xuất linh kiện được duyệt → Sẵn sàng sản xuất → ghi nhận bắt đầu → Đang sản xuất.
4. Duyệt chứng từ hoàn thành: loại nhập kho → Hoàn thành; loại xuất giao → Chờ lập phiếu xuất.
5. Chỉ gửi thành công mới hiện Chờ duyệt. Hộp xác nhận bị đóng hoặc request gửi thất bại không làm thay đổi nhãn.
6. Bản nháp được gộp vào bước trước như bảng trên; nút thao tác phải mở đúng bản nháp đã có, không tạo phiếu/chứng từ trùng.
7. Sau từ chối chưa thuộc 9 nhãn mới: không bổ sung field bước công việc vào response, dùng trạng thái nghiệp vụ tổng quát hiện có và giữ chi tiết từ chối/gửi lại. Không gán nhầm thành chưa lập hoặc đang chờ duyệt; bộ lọc Tất cả vẫn thấy các yêu cầu này.
8. Lỗi API phải hiện lỗi/tải lại, không giả là chưa có phiếu hay Đã giao.

## 4. Nhóm màu UI

| Nhóm | Nền | Chữ | Nhãn sử dụng |
|---|---|---|---|
| Được giao | `#172554` | `#BFDBFE` | Đã giao |
| Phiếu xuất | `#2E1065` | `#DDD6FE` | Hai nhãn chờ duyệt phiếu xuất và Chờ lập phiếu xuất |
| Sản xuất | `#083344` | `#A5F3FC` | Sẵn sàng sản xuất, Đang sản xuất |
| Chứng từ hoàn thành | `#451A03` | `#FDE68A` | Chờ duyệt chứng từ hoàn thành |
| Hoàn thành | `#052E16` | `#BBF7D0` | Hoàn thành |
| Đã hủy | `#450A0A` | `#FECACA` | Đã hủy |

Tận dụng Badge hiện có, bổ sung tùy chọn màu theo nhóm công việc và CSS giới hạn trong Việc được giao của NV. Không đổi bảng màu toàn cục của các màn hình dùng Badge chung. Kiểm tra độ tương phản chữ/nền, nhãn dài và mobile.

## 5. Thiết kế thay đổi tối thiểu

### A. Dữ liệu đọc và bộ lọc

- Bổ sung `trang_thai_cong_viec` vào dữ liệu đọc danh sách/chi tiết yêu cầu cho NV. Giá trị là một trong 9 mã tại mục 3; không có field này cho QLK hoặc nhánh chưa thiết kế.
- Giữ field `trang_thai` và query lọc nghiệp vụ cũ để các caller hiện tại tiếp tục hoạt động. Dữ liệu bước công việc không lưu thành cột ORM và không thay đổi DB khi chỉ đọc.
- Bổ sung query `trang_thai_cong_viec` cho bộ lọc NV. Tính/lọc dựa trên trạng thái yêu cầu và phiếu/chứng từ liên quan trước COUNT/OFFSET/LIMIT, luôn trong phạm vi phân công.
- Tái sử dụng cùng quy tắc cho danh sách và chi tiết. Đọc quan hệ theo lô hoặc join, không thêm GET theo từng dòng và không tải toàn bộ chứng từ về FE để tự ghép.
- Danh sách, số đếm và nhãn dùng cùng snapshot REPEATABLE READ READ ONLY, theo mẫu đọc chứng từ hiện có; không trộn dữ liệu ở hai thời điểm khi có người đang duyệt.
- Tách dữ liệu trình bày khỏi snapshot nghiệp vụ dùng tạo ETag hiện tại. Không mở rộng dữ liệu nháp cho QLK qua field mới.
- Giữ giới hạn truy cập, tìm kiếm, sắp xếp, ngày, phân trang, reset và kiểu nút lọc xoay vòng hiện có.

### B. Cho lập/gửi phiếu xuất linh kiện khi thiếu

- Vẫn cần bước Kiểm tra/xác nhận để chốt BOM, số cần sản xuất và toàn bộ nhu cầu. Không tự lấy BOM/tồn mới để đổi số lượng khi mở form.
- Mở điều kiện tạo/gửi/xem trước phiếu xuất linh kiện cho yêu cầu đang Chờ bổ sung linh kiện và đã chốt nhu cầu; giữ nhánh Đang thực hiện hiện có.
- Phiếu giữ đúng toàn bộ nhu cầu, không sửa số lượng, không xuất từng phần; một phiếu mỗi loại cho mỗi yêu cầu.
- Lưu/gửi không trừ tồn và không giữ một phần linh kiện khi thiếu. Nếu đã đủ/đã giữ theo UC-26 thì tái sử dụng phần giữ đó.
- UI thể hiện cảnh báo thiếu hàng. Hủy form chưa lưu không tạo phiếu; lưu nháp vẫn hiện Đã giao; gửi thành công hiện Chờ duyệt phiếu xuất linh kiện.

### C. QLK duyệt khi đủ linh kiện

- Nhập bổ sung vẫn dùng phiếu nhập hiện có; nhập hàng không tự duyệt phiếu xuất, không bắt NV phải thực hiện thêm Kiểm tra lại chỉ để QLK duyệt được phiếu đã gửi.
- Trong transaction duyệt: khóa yêu cầu/phiếu và các mặt hàng theo thứ tự ổn định; tính hàng còn dùng được sau phần giữ của yêu cầu khác.
- Nếu yêu cầu đã giữ đủ: dùng đúng phần giữ hiện có. Nếu trước đó thiếu và chưa giữ: đủ toàn bộ thì giữ đủ nhu cầu, cập nhật trạng thái nội bộ phù hợp rồi tiếp tục duyệt trong cùng transaction.
- Tái sử dụng kiểm tra giữ hàng/tồn/ledger và thao tác xuất hiện có; thiếu hàng thì không duyệt, không đổi phiếu sang từ chối, không ghi tồn hoặc giữ một phần.
- Thành công: phiếu đã duyệt, trừ tồn đúng một lần, kết thúc phần giữ linh kiện, yêu cầu hiển thị Sẵn sàng sản xuất. Lỗi bất kỳ bước nào phải rollback toàn bộ.
- Mở rộng adapter inventory và hợp đồng writer hiện có nếu cần ghi phần giữ trước khi xuất; không tạo vòng phụ thuộc giữa service yêu cầu và service phiếu xuất.
- Giữ kiểm tra quyền QLK, ETag, xác nhận và audit. Không sửa điều kiện xuất thành phẩm hoặc thay đổi phương pháp giá.

## 6. File dự kiến sửa và phần được tái sử dụng

| File/nhóm file hiện có | Nội dung sửa |
|---|---|
| `backend/app/modules/san_xuat/schemas.py`, `router.py`, `ports.py` | Field đọc/query mới; giữ hợp đồng nghiệp vụ cũ |
| `backend/app/modules/san_xuat/repository/yeu_cau_san_xuat.py`, `service/yeu_cau_san_xuat.py` | Quy tắc bước công việc, đọc/lọc đúng phân trang; tái sử dụng nhu cầu đã chốt và kiểm tra giữ hàng |
| `backend/app/modules/phieu_xuat/service.py`, `ports.py`, `repository.py` | Mở điều kiện lập/gửi/xem trước cho nhánh thiếu; hoàn thiện điều kiện duyệt và cập nhật yêu cầu trong transaction |
| `backend/app/modules/inventory/ports.py`, `repository.py` | Chỉ bổ sung thao tác giữ đủ linh kiện phục vụ duyệt nếu hợp đồng hiện có chưa đáp ứng; giữ nguyên `lock_issue_stock`/`issue_stock` và các kiểm tra liên quan |
| `backend/app/dependencies.py` | Chỉ sửa wiring khi hợp đồng dependency thay đổi; dùng chung DB/transaction |
| `frontend/src/features/production/RequestsPage.jsx`, `requestForm.js` | Nhãn, bộ lọc, điều kiện nút kiểm tra/bắt đầu, mở phiếu đã có; bảng và chi tiết cùng quy tắc |
| `frontend/src/features/material-issuing/issueForm.js`, `MaterialIssuingPage.jsx` | Điều kiện tạo/gửi theo BE; giữ Lưu nháp/Gửi, xác nhận, xử lý lỗi và ETag |
| `frontend/src/components/Badge.jsx`, `Collection.jsx`, `frontend/src/app/App.css` | Tái sử dụng Badge, thêm nhóm màu; bộ lọc công việc luôn ở hàng chính như bộ lọc trạng thái cũ |
| Test/fixture liên quan ở mục 8 | Bổ sung case mới, cập nhật contract fixture; giữ các bảo đảm tồn/phân quyền |
| Spec UC-25/26/34/35 và BR-008/010 tại `specs/business_requirements/BR-GIAIDOAN1.md` | Cập nhật phần điều kiện lập/gửi/duyệt và phân biệt nhãn UI với trạng thái nghiệp vụ theo quyết định mới |
| `docs/sequence/san_xuat.md`, `docs/sequence/phieu_xuat.md` | Cập nhật endpoint đọc/lọc, xem trước/tạo/gửi/duyệt bị ảnh hưởng, transaction và nhánh lỗi |

Chưa cần tạo file helper/component mới. Nếu quy tắc nhãn cần tách để kiểm thử thì đặt trong module production hiện có và nối đầy đủ caller; không tạo bộ máy trạng thái hoặc thư viện mới.

## 7. Thứ tự triển khai

1. Viết case kiểm thử cho điều kiện mới: cho lập/gửi khi thiếu, chặn duyệt khi thiếu và duyệt được sau nhập bổ sung; giữ các case đã giữ hàng.
2. Sửa BE luồng phiếu và giữ hàng, bảo đảm tạo/gửi/duyệt/rollback đúng trước khi đổi UI.
3. Bổ sung dữ liệu bước công việc và query lọc; kiểm tra quyền, phân trang và tương thích caller cũ.
4. Cập nhật danh sách/chi tiết/bộ lọc và nút thao tác NV; giữ lưu nháp, bỏ ba nhãn Chờ gửi.
5. Áp 6 nhóm màu; kiểm tra component chung và các màn hình ngoài phạm vi không bị đổi theo.
6. Đồng bộ spec/sequence với implementation; chạy kiểm tra, review diff và bàn giao cho dev.

## 8. Mức rủi ro và kiểm chứng

Rủi ro cao ở phần duyệt xuất vì liên quan tồn kho, giữ hàng và transaction. Phần nhãn/màu có rủi ro thấp hơn. Không thay schema, không thêm migration/dependency, không triển khai hoặc thử ghi vào DB ứng dụng trong tác vụ lập plan này.

| Nhóm kiểm tra khi triển khai | Bằng chứng cần đạt |
|---|---|
| Nhãn | Đủ 9 nhãn; nháp gộp đúng bước trước; sau từ chối không bị gán nhầm; kết thúc ưu tiên; null không thành 0 |
| Luồng thiếu hàng | Chốt nhu cầu → lưu/gửi khi thiếu → phiếu chờ duyệt → nhập đủ → QLK duyệt được; không bắt thêm thao tác NV |
| Duyệt/concurrency | Không lấy phần giữ của yêu cầu khác; không giữ hai lần; thiếu thì rollback; hai người duyệt chỉ xuất/ghi sổ một lần |
| Quyền/API | NV đúng phân công, QLK đúng quyền; ETag cũ bị chặn; response/query cũ tương thích; lọc đúng total/page trên nhiều trang |
| Luồng hiện có | Đã giữ đủ hàng vẫn duyệt được; bắt đầu chỉ sau duyệt linh kiện; đủ thành phẩm bỏ qua sản xuất; nhập kho hoàn tất sau duyệt chứng từ |
| UI | Hủy form chưa lưu không tạo phiếu; bản nháp mở/gửi được; refresh nhãn sau mutation; lỗi API không giả nhãn; màu/độ tương phản/mobile |
| Hồi quy | Admin/QLK, KPI và dashboard chứng từ giữ hành vi hiện có; không đổi màu toàn bộ Badge |

Các test hiện có cần chạy/cập nhật: `backend/tests/test_uc25_danh_sach_yeu_cau_san_xuat.py`, `test_uc26_kiem_tra_giu_hang.py`, `test_uc29_bat_dau_san_xuat.py`, `test_uc30_chung_tu_hoan_thanh.py`, `test_uc31_duyet_chung_tu.py`, `test_phieu_xuat_service.py`, `test_phieu_xuat_api.py`, `test_phieu_xuat_reads.py`, `test_phieu_xuat_postgres.py`; test FE UC-25/26/29/30/31 và browser fixture liên quan.

Lệnh kiểm tra dự kiến: `python -m pytest` với các file backend bị ảnh hưởng trong môi trường test; `npm test`, `npm run lint`, `npm run build` tại frontend; browser test chọn theo phạm vi. Kiểm tra cú pháp/render Mermaid nếu có công cụ. Báo riêng lỗi có sẵn của module tồn kho cũ, không sửa ngoài phạm vi hoặc làm yếu test.

Kiểm thử ghi dùng DB test riêng và rollback/dọn tài nguyên test. Nếu cần hoàn tác implementation thì hoàn tác đúng diff đã triển khai sau review; không reset DB/volume hoặc seed lại dữ liệu.

Không còn câu hỏi nghiệp vụ đang chờ trong phạm vi đã chốt. Chưa bổ sung các nhãn sau từ chối.

## 9. Kết quả thực hiện và bàn giao — 19/11/2026

- Đã triển khai 9 nhãn/6 nhóm màu, dữ liệu đọc và bộ lọc NV; giữ API và UI nghiệp vụ của QLK/Admin. Component chung chỉ thêm hỗ trợ trường công việc và màu được chọn riêng cho NV.
- Đã mở lập/gửi khi thiếu linh kiện và xử lý giữ hàng/duyệt nguyên tử khi QLK có đủ hàng; kiểm chứng nhập bổ sung không tự duyệt, hai phiếu không lấy trùng tồn và lỗi sau giữ hàng rollback toàn bộ.
- Giữ lưu nháp/gửi riêng; nháp gộp vào bước trước; Hủy form chưa lưu không tạo phiếu. Đã bỏ notice kỹ thuật và nhãn trạng thái nội bộ trong thông báo kiểm tra.
- Không thay schema, bootstrap SQL, dependency hoặc Dockerfile trong repository. Không commit/push, reset/seed hoặc dùng DB ứng dụng để thử nghiệp vụ ghi.

| Kiểm tra đã chạy | Kết quả thực tế |
|---|---|
| Toàn bộ pytest backend trên runner/DB test riêng | 1.107 passed, 307 skipped; không còn failure |
| Giới hạn test backend | Chỉ cấu hình PostgreSQL riêng cho goods issue; các fixture cần TEST_DATABASE_URL/GOODS_RECEIPT_TEST_DATABASE_URL và môi trường tùy chọn khác chưa cấu hình vẫn skip theo suite |
| Frontend unit | 319 passed |
| Browser theo phạm vi | 30 passed; sau điều chỉnh notice, chạy lại 11 test kiểm tra linh kiện đều passed |
| ESLint và Vite build | Passed trên phiên bản cuối |
| Ruff trên các file Python thay đổi | Passed |
| git diff --check | Passed |
| Mermaid | 7/7 sơ đồ endpoint thay đổi parse thành công bằng Mermaid 11; chưa render ảnh |
| Mermaid ngoài phạm vi | Đối chiếu HEAD: san_xuat có 8 lỗi cũ, phieu_xuat còn 1 lỗi cũ; không phát sinh lỗi mới. Một lỗi cũ tại sơ đồ preview đã được sửa trong phạm vi endpoint đang cập nhật |
| Kiến trúc | Map không phát hiện vòng phụ thuộc hoặc file sai tầng; check_boundaries không tự kiểm tra được vì repo chưa khai báo layers. Đã đối chiếu imports với cấu trúc hiện có |

### Docker để dev thử Nhân viên

- Đã build/chạy `xbike-mrp-work-status-backend:local` và `xbike-mrp-work-status-frontend:local`, mount đúng worktree `hotfix-UI-nhanvien-2`; restart Nginx để nhận các container mới.
- Truy cập: `http://localhost:5173/nv/yeu-cau` hoặc `http://localhost/nv/yeu-cau`, đăng nhập bằng tài khoản NV hiện có.
- Backend `/health`: ok. OpenAPI `/api/v1/openapi.json` có query công việc và đủ 9 mã. Frontend trả HTTP 200 và phục vụ module nhãn mới.
- ID, thời điểm khởi động và mount của `xbike_postgres` giữ nguyên; volume vẫn `xbike-mrp-system_pgdata`. Không restart DB hoặc nạp lại bootstrap/seed.
- Runtime override ngoài repo: `%LOCALAPPDATA%/xBike/docker-runtime/hotfix-UI-nhanvien-2/compose.runtime.yml`, kèm bản sao cấu hình backend đang chạy. Backend dùng lại môi trường dependency đã kiểm thử trong image cũ; không sửa Dockerfile nguồn đang tham chiếu poetry.toml chưa có ở worktree này.
- Ở bước kiểm chứng source chưa ghi nghiệp vụ trên DB ứng dụng; luồng ghi đã được kiểm tra bằng DB test riêng. Sau đó dev cho phép thêm dữ liệu demo vào DB hiện tại như mục dưới, không chạy thêm test.

### Dữ liệu demo dev cho phép thêm vào DB hiện tại

Ngày 19/11/2026, dev chọn thêm mới vào DB Docker đang dùng, giữ nguyên bản ghi có sẵn và gán cho tài khoản `nhan_vien_lr` (ID 4).

- Đã thêm 9 yêu cầu `YCSX-202611-000011` đến `YCSX-202611-000019`, đủ 9 nhãn công việc.
- Mặt hàng riêng: `[DEMO] Xe LR - 9 trang thai` (ID 16), linh kiện demo ID 15; kèm BOM, nhà cung cấp và chứng từ của bộ demo. Có thể tìm `DEMO` trên màn Việc được giao để xem riêng bộ này.
- Dùng các service hiện có để chốt nhu cầu, tạo/gửi/duyệt chứng từ và ghi tồn/giữ hàng/audit trên chính các mặt hàng mới; toàn bộ bộ dữ liệu được commit trong một transaction ngoài, không cập nhật bản ghi nghiệp vụ cũ.
- Không reset database, không chạy lại seed.sql, không đổi mật khẩu hoặc tạo tài khoản mới. Không chạy thêm bộ kiểm thử theo yêu cầu dev.

### Tài nguyên tạm và hoàn tác

Hai container test `xbike-status-test-runner` và `xbike-status-test-postgres` đã dừng. Bộ xét duyệt tự động chặn lệnh xóa container/volume test, thư mục công cụ Mermaid trong TEMP và log `.work-status-frontend-test.log` với thông báo `blocked by policy`; các tài nguyên tạm này còn giữ lại. Chúng không phải database ứng dụng.

Hoàn tác source theo đúng diff sau review, không reset DB. Nếu chuyển lại code cũ sau khi đã có phiếu gửi từ nhánh thiếu hàng, cần xử lý phần kiểm tra/giữ đủ linh kiện theo luồng cũ trước khi duyệt; không xóa phiếu để hoàn tác.


### Danh sach file cua dot trien khai

AGENTS.md la thay doi theo yeu cau truoc do, duoc giu nguyen trong dot trien khai nay.

```text
backend/app/modules/inventory/ports.py
backend/app/modules/inventory/repository.py
backend/app/modules/phieu_xuat/ports.py
backend/app/modules/phieu_xuat/repository.py
backend/app/modules/phieu_xuat/service.py
backend/app/modules/san_xuat/ports.py
backend/app/modules/san_xuat/repository/yeu_cau_san_xuat.py
backend/app/modules/san_xuat/schemas.py
backend/app/modules/san_xuat/service/yeu_cau_san_xuat.py
backend/tests/test_phieu_xuat_postgres.py
backend/tests/test_phieu_xuat_service.py
backend/tests/test_uc23_lap_gui_yeu_cau_san_xuat.py
backend/tests/test_uc25_danh_sach_yeu_cau_san_xuat.py
backend/tests/test_uc26_kiem_tra_giu_hang.py
backend/tests/test_work_status_postgres.py
docs/plans/employee-work-status-colors.md
docs/sequence/phieu_xuat.md
docs/sequence/san_xuat.md
frontend/src/app/App.css
frontend/src/components/ApprovalActions.jsx
frontend/src/components/Badge.jsx
frontend/src/components/Collection.jsx
frontend/src/features/material-issuing/issueForm.js
frontend/src/features/production/EmployeeCompletionPage.jsx
frontend/src/features/production/RequestsPage.jsx
frontend/src/features/production/requestForm.js
frontend/src/layouts/Sidebar.jsx
frontend/tests/browser/api-fixture.js
frontend/tests/browser/employee-filter-cycle.spec.js
frontend/tests/browser/employee-documents-password.spec.js
frontend/tests/browser/employee-request-filters.spec.js
frontend/tests/browser/employee-ui.spec.js
frontend/tests/browser/employee-work-status.spec.js
frontend/tests/browser/issue-main-flow.spec.js
frontend/tests/browser/request-check-layout.spec.js
frontend/tests/issue-form.test.js
frontend/tests/uc24-edit-delete-send-draft.test.js
frontend/tests/uc25-request-list.test.js
frontend/tests/uc26-check-request.test.js
frontend/tests/uc29-start-production.test.js
frontend/tests/uc30-completion.test.js
specs/business_requirements/BR-GIAIDOAN1.md
specs/use_cases/goods_issue/UC-34.md
specs/use_cases/goods_issue/UC-35.md
specs/use_cases/production/UC-25.md
specs/use_cases/production/UC-26.md
specs/use_cases/production/UC-30.md
```

### Gỡ notice giải thích thừa theo yêu cầu ngày 19/11/2026

- `ApprovalActions.jsx`: bỏ notice “Chưa trừ tồn; hàng vẫn được giữ cho yêu cầu.” và câu nhắc kiểm tra nội dung khi Nhân viên gửi/gửi lại phiếu xuất linh kiện hoặc thành phẩm.
- `RequestsPage.jsx`, `EmployeeCompletionPage.jsx`: dùng `hideImpact` có sẵn để bỏ notice giải thích giữ hàng và chưa cộng tồn trong hộp kiểm tra yêu cầu, gửi/gửi lại chứng từ hoàn thành ở cả hai màn hình. Xóa helper `checkImpact` cùng các kiểm tra câu chữ đã bỏ.
- Vẫn hiển thị nội dung cần xác nhận, bảng thiếu hàng, lỗi thao tác, lý do từ chối và cảnh báo đăng xuất khi đổi mật khẩu. Không sửa API hoặc dữ liệu trong đợt gỡ notice này.
- Đối chiếu và cập nhật UC-26, UC-30, UC-34 để phản ánh yêu cầu giao diện mới; nghiệp vụ tồn kho giữ nguyên.
- Kiểm chứng đợt gỡ notice: 316/316 unit test frontend, 32/32 browser test trong ba file luồng phiếu xuất, chứng từ/mật khẩu và kiểm tra yêu cầu; lint, build, `git diff --check` đạt. Browser kiểm tra không còn `.notice-info` trong ba hộp xác nhận, vẫn kiểm tra gửi với ETag và lỗi thao tác. Không chạy lại backend test.
- Đã restart riêng `xbike_frontend` vì Vite trong Docker chưa nhận thay đổi file qua mount Windows. HTTP trên cổng 5173 đã phục vụ `hideImpact` mới ở cả ba component; không restart hoặc ghi DB.

### Hiển thị người lập ngày 19/11/2026

- `requestForm.js` đổi Người lập trong chi tiết yêu cầu thành `Họ tên — NV-xxxxxx`, giống Nhân viên được giao theo ảnh dev xác nhận. Dùng mã nhân viên thực của người lập, không tự tạo từ ID số hoặc dùng tài khoản đang đăng nhập thay thế.
- Backend `san_xuat` (schema, port, repository, service) bổ sung `nguoi_lap_ho_ten`, `nguoi_lap_ma_nhan_vien` vào GET chi tiết cho NV sau kiểm tra quyền yêu cầu. Chỉ SELECT họ tên và mã từ `NhanVien`; không mở quyền API hồ sơ/danh sách nhân viên, không đổi schema DB hoặc ETag. QLK tiếp tục dùng danh sách nhân viên đã được phép đọc để hiển thị.
- Cập nhật fixture backend/browser, kỳ vọng có sẵn của UC-24/25, spec UC-25 và sequence san_xuat theo dữ liệu mới. Không chạy test, lint, build hoặc kiểm tra Mermaid theo yêu cầu không test của dev.

### Số cạnh Việc được giao ngày 19/11/2026

- `Sidebar.jsx`: lấy thêm tổng Đã hủy bằng bộ lọc API có sẵn. Số hiển thị = tổng được giao − Hoàn thành − Đã hủy; ẩn số nếu chưa tải đủ hoặc có lỗi. Không phụ thuộc phân trang danh sách.
- Cập nhật quy tắc trong UC-25. Không sửa API, dữ liệu hoặc KPI dashboard. Không chạy test theo yêu cầu trước đó.

### Kiểm thử trước PR theo yêu cầu ngày 19/11/2026

Dev yêu cầu kiểm thử lại Nhân viên từ nhận việc đến hoàn thành, rồi tạo PR vào `main`.

- Backend: **329 passed** trong 9 file `test_work_status_postgres.py`, `test_phieu_xuat_postgres.py`, `test_phieu_xuat_service.py`, UC-23, UC-25, UC-26, UC-29, UC-30, UC-31. Bộ PostgreSQL chạy trên server test cổng 55465, mỗi test tự tạo DB riêng theo guard hiện có.
- Frontend: **316 passed**, lint và build đạt. Browser: **55 test riêng biệt đạt** trong 7 file Nhân viên (lượt đầu 54/55, sau cập nhật kỳ vọng nhãn cũ chạy lại cả `employee-ui.spec.js`: 12/12; sau bổ sung kiểm tra đúng tên/mã người lập, NV-02 chạy lại đạt).
- Cập nhật 3 file test: fixture UC-26 trả đúng tuple tên/mã người lập và kiểm tra dữ liệu/ETag; kỳ vọng fallback khi thiếu tên là `—`; NV-02 dùng nhãn Chờ duyệt phiếu xuất linh kiện và kiểm tra Người lập theo tên/mã thực.

Kiểm thử trình duyệt nối API thật dùng 2 phiên đăng nhập QLK/NV riêng, không mock API. Backend tạm cổng 18001, Vite cổng 5175, schema từ `init.sql` và dữ liệu nền từ fixture hàng hóa hiện có, trên DB mới `employee_browser_4ef7987a7785475bb0749a064cab7ded_test` của server test. Các thao tác tạo/gửi yêu cầu, kiểm tra, lập/gửi/duyệt phiếu, bắt đầu sản xuất và chứng từ hoàn thành đều thực hiện trên UI.

| Nhánh | Kết quả |
| --- | --- |
| Xuất giao 107 xe, dùng 100 xe có sẵn và sản xuất 7 | Đã giao → Chờ duyệt phiếu xuất linh kiện → Sẵn sàng sản xuất → Đang sản xuất → Chờ duyệt chứng từ hoàn thành → Chờ lập phiếu xuất → Chờ duyệt phiếu xuất → Hoàn thành |
| Sản xuất nhập kho 7 xe | Nhận việc, kiểm tra, xuất linh kiện, sản xuất và duyệt chứng từ → Hoàn thành; không có thao tác lập phiếu xuất thành phẩm |
| Sản xuất nhập kho 120 xe khi thiếu linh kiện | Lập/gửi phiếu khi thiếu; QLK duyệt bị chặn và phiếu vẫn chờ duyệt; nhập đủ không tự duyệt; QLK duyệt được, NV sản xuất và hoàn thành |

Đối chiếu SQL chỉ đọc: 3 yêu cầu có thời điểm bắt đầu/kết thúc và trạng thái `hoan_thanh`; 4 phiếu xuất và 3 chứng từ hoàn thành mới đã duyệt. Tồn cuối 2 linh kiện = 0, thành phẩm = 127; từng số dư khớp tổng biến động sổ kho, không âm và không còn giữ hàng. UI xác nhận tên/mã người lập đúng và không có notice giải thích thừa trong hộp xác nhận NV.

Lượt live đầu gặp timeout khi nối PostgreSQL test qua cổng host Windows; lượt cuối dùng IP mạng nội bộ của đúng container test, cả 3 nhánh đạt. Không chỉnh timeout hoặc nghiệp vụ của ứng dụng. Kết quả JSON và ảnh từng bước lưu ngoài repo tại `%TEMP%/xbike-employee-lifecycle-20261119/` (`browser-results.json`, `database-results.json`, `*-finished.png`). Không ghi dữ liệu hoặc reset DB Docker ứng dụng. Không khẳng định toàn hệ thống đã đạt E2E hoặc kiểm thử bản merge vào `main`.
