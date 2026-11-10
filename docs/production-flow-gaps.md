# Các vấn đề của luồng yêu cầu thành phẩm và sản xuất nhiều cấp

Ngày rà soát: **10/11/2026**. Code tham chiếu: commit `2ef564cb78ac5819b1e5af4603712d9ef58cc21e`, working tree sạch trước khi thêm tài liệu này.

**Trạng thái: ghi nhận vấn đề và checklist triển khai, chưa sửa code.** Các ô `- [ ]` là việc chưa hoàn tất hoặc quyết định còn chờ xác nhận. Chỉ đánh dấu hoàn tất khi có bằng chứng tương ứng; tài liệu này không tự phê duyệt thay đổi nghiệp vụ, schema hoặc quyền.

## 1. Mục tiêu, thuật ngữ và nguồn đối chiếu

Mục tiêu là đánh giá và hoàn thiện luồng từ yêu cầu xuất thành phẩm, sản xuất bù phần thiếu, sản xuất bán thành phẩm nhiều cấp, bổ sung vật tư, đến xuất đủ thành phẩm cho yêu cầu ban đầu.

| Thuật ngữ | Nghĩa trong tài liệu |
| --- | --- |
| Q | Quản lý kho, mã vai trò `quan_ly` |
| N | Nhân viên, mã vai trò `nhan_vien` |
| YCSX | Yêu cầu thành phẩm/sản xuất, bảng `"YeuCauSanXuat"` |
| LSX | Lệnh sản xuất, bảng `"LenhSanXuat"` |
| TP / BTP / NVL | Thành phẩm / bán thành phẩm / nguyên vật liệu; linh kiện cũng thuộc vật tư sản xuất |
| HTSX | Chứng từ hoàn thành sản xuất, bảng `"ChungTuHoanThanhSx"` |
| Nhu cầu trực tiếp | Các mặt hàng và lượng cần của riêng một LSX trong `"ChiTietLenhSanXuat"` |
| Ghi sổ | Tạo giao dịch `"GiaoDichKho"` và cập nhật `"MatHang".so_luong_ton` trong cùng transaction |

Nguồn đã đọc trong phiên rà soát:

- [AGENTS.md](../AGENTS.md): phạm vi, bảo vệ dữ liệu, bootstrap, tài liệu sequence và quy tắc xử lý mâu thuẫn.
- [Thư mục Drive project](https://drive.google.com/drive/folders/1AVkmFGSHI-zgRTCzaxAh9qyD1_FkFFd9).
- [SRS_v4.txt](https://drive.google.com/file/d/1GTqAuq1JTyMBt-Xu6BXorSJAFDhg87zn/view): yêu cầu tổng thể và luồng nghiệp vụ. Nội dung file tự ghi phiên bản 3.0; không suy ra phiên bản nội dung chỉ từ tên file.
- [API contract v3 trên Drive](https://drive.google.com/file/d/1yznre1rfIK6IIp8UTWb_D842r8vrNTIE/view), [bản trong repository](./api_contract_v3.md): §7 nhập kho, §8 yêu cầu/kế hoạch, §9 lệnh, §10 xuất kho, §11 HTSX.
- [Data model v3.1](https://drive.google.com/file/d/1OdqHXKWbOwb47xcWwiraoKh9tGjecdQB/view), [init.sql](../infra/postgres/init.sql), [các quyết định đã chốt](./DECISION.md).
- Sơ đồ swimlane do dev cung cấp ngày 10/11/2026, có ba làn **Nhân viên / Quản lý kho / Hệ thống**. Ảnh chưa được lưu thành file trong repository; mục 2 diễn giải đầy đủ các bước cần đối chiếu để người tiếp nhận không cần xem hội thoại.

**Cách sử dụng:** source cho biết hành vi đã triển khai; contract và quyết định cho biết hành vi đã chốt. Sơ đồ có các khác biệt với contract. Phải giải quyết quyết định ở mục 5 trước khi sửa phần phụ thuộc, không tự chọn sơ đồ hoặc contract làm chuẩn thay dev.

## 2. Luồng trong sơ đồ cần đối chiếu

1. Q tạo YCSX, kèm hạn hoàn thành, rồi gửi/giao N.
2. N nhận YCSX và kiểm tra tồn TP.
3. Nếu đủ TP: N lập phiếu đề nghị xuất TP → Q duyệt → hệ thống trừ tồn TP → kết thúc.
4. Nếu thiếu TP: N báo thiếu cho Q → Q tạo LSX TP cho lượng thiếu và chụp BOM.
5. Kiểm tra tồn cụm bánh xe, là BTP của TP. Nếu thiếu thì tạo LSX con cho phần cụm thiếu; nếu đủ thì dùng cụm có sẵn.
6. Q gửi LSX cho N; xử lý lệnh con trước ở nhánh cần sản xuất cụm.
7. N kiểm tra vật tư của lệnh. Nếu thiếu thì gửi yêu cầu nhập NVL cho Q; Q lập/hoàn tất phiếu nhập → hệ thống cộng tồn NVL → kiểm tra lại khả năng cấp vật tư.
8. Khi đủ vật tư: N lập phiếu xuất vật tư theo lệnh → Q duyệt → hệ thống trừ tồn vật tư.
9. N ghi nhận bắt đầu và thời điểm sản xuất xong, lập/gửi chứng từ HTSX.
10. Q duyệt HTSX → hệ thống cộng kho đầu ra của lệnh.
11. Đầu ra lệnh con đã nhập kho được cấp cho lệnh cha qua phiếu xuất vật tư. Tiếp tục sản xuất và duyệt đầu ra lệnh cha.
12. Sau khi có TP, quay lại kiểm tra tồn và lập/duyệt phiếu xuất TP cho yêu cầu ban đầu. Hoàn thành sản xuất chưa đồng nghĩa hoàn thành YCSX; phải xuất đủ lượng yêu cầu.

Đây là diễn giải **sơ đồ**, không phải xác nhận toàn bộ bước đã có API hoặc được contract v3 cho phép.

## 3. Phần hiện có cần giữ và kiểm thử hồi quy

| Công đoạn | Hiện trạng source | Vị trí chính |
| --- | --- | --- |
| Tạo nháp, gán N, tính và gửi YCSX | Có; có token kế hoạch và ETag | `san_xuat/schemas.py`, `service/yeu_cau_san_xuat.py` |
| Tính lượng TP cần sản xuất | `max(so_luong - ton_thanh_pham, 0)`; đủ TP thì không tạo LSX | `calculate_plan()` |
| BOM nhiều cấp | Dùng tồn BTP trước, chỉ tạo lệnh con cho phần thiếu; tồn dùng chung không phân bổ hai lần giữa các nhánh | `calculate_plan()` |
| Chụp kế hoạch | Khi gửi YCSX, lưu `bom_id`, lượng và nhu cầu trực tiếp cho cây lệnh | `YeuCauSanXuatService.gui()`, repository `add_lenh_tree()` |
| Giao/gửi LSX | Q gán N và gửi từng lệnh; tạo cây lệnh chưa tự gán người thực hiện | `service/lenh_san_xuat.py`, repository yêu cầu |
| Điều kiện bắt đầu | N được giao lệnh; lệnh đã gửi; mọi vật tư đã được cấp đủ qua phiếu xuất `da_duyet` | `LenhSanXuatService.start()` |
| Nhập NVL | Hoàn tất phiếu nhập mới cộng tồn và ghi ledger | `PhieuNhapService.complete_receipt()` |
| Xuất vật tư/TP | Q lập/gửi/duyệt; kiểm tra tồn và tổng nhu cầu; chỉ duyệt mới trừ kho | `PhieuXuatService`, inventory repository |
| HTSX | N lập/gửi; Q duyệt; cộng đầu ra, kiểm tra tổng hoàn thành, tự hoàn thành LSX khi đủ lượng | `ChungTuHoanThanhService.duyet()` |
| Kết thúc YCSX | Chỉ khi xuất đủ TP đã duyệt | `PhieuXuatService.approve()`, repository `update_progress()` |

Các đường dẫn module trong bảng tính từ `backend/app/modules/`. Các bước trên đã được đọc source; chưa được chứng nhận E2E với PostgreSQL trong phiên rà soát.

## 4. SX-01 — YCSX không thoát trạng thái chờ sau khi nhập đủ NVL

**Ưu tiên cao: làm đứt luồng. Đây là khoảng thiếu triển khai so với contract v3 §7–§8.**

### 4.1 Hiện trạng và nguyên nhân

- `YeuCauSanXuatService.gui()` chuyển YCSX sang `cho_bo_sung_vat_tu` nếu kế hoạch thiếu vật tư, đồng thời giữ cây LSX đã sinh.
- `PhieuNhapService.complete_receipt()` hoàn tất phiếu, gọi `inventory.receive_receipt()` và ghi audit; chưa gọi xử lý đánh giá lại YCSX đang chờ.
- Trong source và các trigger của `init.sql` chưa tìm thấy cơ chế khác thực hiện chuyển trạng thái này sau nhập kho.
- `SqlAlchemyLenhSanXuatRepository.start_request()` chỉ đổi YCSX từ `da_gui`; bắt đầu LSX khi YCSX đang chờ không giúp thoát chờ.
- Với `xuat_thanh_pham`, `PhieuXuatService._source_state()` chỉ chấp nhận nguồn `da_gui` hoặc `dang_thuc_hien`; yêu cầu còn chờ bị từ chối với lỗi trạng thái HTTP 409.
- Frontend `RequestsPage.jsx` cũng ẩn liên kết tạo phiếu xuất TP khi YCSX còn `cho_bo_sung_vat_tu`.

**Hậu quả:** có thể nhập đủ NVL, cấp vật tư và sản xuất xong, nhưng vẫn không lập/gửi/duyệt xuất TP để kết thúc yêu cầu.

### 4.2 Dữ liệu và trình tự tái hiện

Thực hiện trên database test riêng. Fixture tối giản sau là dữ liệu kiểm thử tổng hợp, không phải BOM kỹ thuật của sản phẩm demo. Khi tạo tồn đầu kỳ phải có ledger tương ứng, không chỉ sửa số dư `MatHang`.

| Mặt hàng | Loại | Tồn ban đầu | BOM |
| --- | --- | --- | --- |
| TP-A | `thanh_pham` | 0 | 1 TP-A cần 2 NVL-A |
| NVL-A | `nguyen_vat_lieu` | 0 | Không có |

1. Q tạo YCSX 5 TP-A, gán N hợp lệ; gọi `tinh_ke_hoach`, nhận nhu cầu 10 NVL-A và thiếu 10.
2. GET lại ETag khi cần, gửi YCSX với `ke_hoach_token` còn hạn và `If-Match` hợp lệ.
3. Kiểm tra YCSX ở `cho_bo_sung_vat_tu`, có LSX 5 TP-A với nhu cầu cố định 10 NVL-A.
4. Q tạo phiếu nhập 10 NVL-A, có nhà cung cấp, ngày nhập và đơn giá hợp lệ; hoàn tất phiếu.
5. Đọc lại YCSX: hiện vẫn chờ. Kỳ vọng theo contract: trở về `da_gui` vì chưa có lệnh bắt đầu.
6. Để chứng minh ảnh hưởng cuối luồng: gán/gửi LSX, Q lập/gửi/duyệt xuất 10 NVL-A; N bắt đầu, lập/gửi HTSX 5 TP-A; Q duyệt HTSX.
7. Q thử lập phiếu `xuat_thanh_pham` 5 TP-A gắn YCSX: hiện bị chặn trạng thái dù tồn TP-A đã đủ.

Mọi URL trong tài liệu có prefix `/api/v1`; ví dụ `POST /api/v1/phieu_nhap/{id}/hoan_tat`. Dùng JWT đúng vai trò, ETag mới sau thay đổi; không dùng ETag giả để tái hiện.

### 4.3 Hành vi cần triển khai theo contract hiện có

- [ ] Khi hoàn tất một phiếu nhập mới thành công, đánh giá lại **mọi** YCSX đang `cho_bo_sung_vat_tu` trong cùng transaction nhập kho.
- [ ] Đọc nhu cầu đã chụp của các LSX chưa hoàn thành/chưa hủy; không gọi tính lại kế hoạch theo BOM hiện hành, không tạo thêm cây lệnh.
- [ ] Tính lượng đã cấp từ tổng phiếu `xuat_vat_tu` của đúng LSX ở `da_duyet`; bỏ qua phiếu nháp, chờ duyệt, từ chối. Lượng còn cấp của mỗi dòng là `max(so_luong_can - so_luong_da_cap, 0)`.
- [ ] Cộng gộp lượng còn cần theo mặt hàng trong cùng YCSX trước khi so tồn, tránh dùng một số tồn hai lần cho nhiều lệnh. Xử lý BTP sẽ sản xuất trong cây lệnh theo quyết định D-05 ở mục 5; không tự suy diễn phần đó.
- [ ] Nếu đủ điều kiện và chưa có lệnh bắt đầu, chuyển YCSX về `da_gui`; nếu đã có lệnh bắt đầu thì về `dang_thuc_hien`. Dấu hiệu đã bắt đầu phải xét cả lệnh đã hoàn thành có `started_at`, không chỉ tìm lệnh đang chạy.
- [ ] Nếu chưa đủ, giữ nguyên trạng thái; không ghi audit thay đổi trạng thái giả.
- [ ] Ghi audit `sua` cho mỗi YCSX thực sự đổi trạng thái, gồm người thực hiện, trước/sau và cùng transaction với phiếu nhập.
- [ ] Không giữ chỗ/trừ kho khi đánh giá lại. Nhiều YCSX có thể cùng được đánh giá đủ dựa trên cùng tồn; duyệt xuất vẫn phải khóa và kiểm tra tồn thực tế.
- [ ] Giữ nguyên quyền, ETag và cơ chế gọi lại phiếu đã hoàn tất; không cộng kho/ledger/audit lần hai hoặc dùng retry để che lỗi thiếu kiểm tra của lần ghi sổ đầu.
- [ ] Nếu đánh giá lại hoặc ghi audit lỗi, rollback toàn bộ phiếu nhập, số dư, ledger và trạng thái YCSX trong transaction đó.
- [ ] Không sửa điều kiện cho phép xuất TP để bỏ qua `cho_bo_sung_vat_tu`; phải sửa chỗ chuyển trạng thái còn thiếu. Không thêm endpoint kiểm tra thủ công vì contract hiện quy định tự động.

### 4.4 Hướng đặt code và các file cần xem

- [ ] Đặt quy tắc đánh giá lại trong module `san_xuat`, công khai qua service/port phù hợp. Module `phieu_nhap` gọi nghiệp vụ công khai này; không nhúng truy vấn bảng sản xuất vào router nhập kho.
- [ ] Gắn lời gọi sau khi số dư/ledger nhập đã được ghi trong session và trước commit. Dùng chung `AsyncSession` và transaction hiện có; tránh gọi một public action tự commit ở giữa luồng nhập.
- [ ] Bổ sung truy vấn nhu cầu, tổng đã cấp và khóa trong repository sản xuất. Xem lại thứ tự khóa so với gửi yêu cầu, duyệt xuất, bắt đầu lệnh và duyệt HTSX để tránh deadlock; không chỉ thêm khóa ở từng nơi một cách độc lập.
- [ ] Cập nhật dependency wiring và test fake/fixture nếu thay constructor; không đổi request/response phiếu nhập nếu không cần.
- [ ] Cập nhật sequence `phieu_nhap.md` và phần liên quan trong `san_xuat.md` để thể hiện kiểm tra lại, audit và rollback.

| File | Symbol/trách nhiệm liên quan |
| --- | --- |
| [phieu_nhap/service.py](../backend/app/modules/phieu_nhap/service.py) | `PhieuNhapService.complete_receipt()` |
| [inventory/repository.py](../backend/app/modules/inventory/repository.py) | `receive_receipt()`, `issue_stock()`, số dư/ledger |
| [san_xuat/service/yeu_cau_san_xuat.py](../backend/app/modules/san_xuat/service/yeu_cau_san_xuat.py) | `calculate_plan()`, `gui()`, nghiệp vụ YCSX |
| [san_xuat/repository/yeu_cau_san_xuat.py](../backend/app/modules/san_xuat/repository/yeu_cau_san_xuat.py) | Nhu cầu/cây lệnh đã chụp, đọc/khóa YCSX |
| [san_xuat/repository/lenh_san_xuat.py](../backend/app/modules/san_xuat/repository/lenh_san_xuat.py) | `start_request()`, tổng vật tư đã cấp |
| [san_xuat/ports.py](../backend/app/modules/san_xuat/ports.py) | Hợp đồng truy vấn và giao tiếp nghiệp vụ |
| [phieu_xuat/service.py](../backend/app/modules/phieu_xuat/service.py) | `_source_state()`, `approve()` |
| [phieu_xuat/repository.py](../backend/app/modules/phieu_xuat/repository.py) | `lock_source()`, `approved_quantities()`, `update_progress()` |
| [dependencies.py](../backend/app/dependencies.py) | `get_receiving_service()`, service và transaction dùng chung |
| [core/sqlalchemy_transaction.py](../backend/app/core/sqlalchemy_transaction.py) | Commit/rollback adapter |
| [RequestsPage.jsx](../frontend/src/features/production/RequestsPage.jsx) | Hiển thị trạng thái và điều kiện tạo phiếu xuất TP |
| [sequence/phieu_nhap.md](./sequence/phieu_nhap.md), [sequence/san_xuat.md](./sequence/san_xuat.md) | Luồng endpoint thực tế |

### 4.5 Checklist nghiệm thu SX-01

- [ ] Tái hiện lỗi bằng fixture ở §4.2 trước khi sửa; sau sửa nhập đủ 10 NVL-A làm YCSX về `da_gui` ngay trong lần hoàn tất nhập đó.
- [ ] Nhập 9/10 NVL-A vẫn chờ; nhập thêm 1 bằng phiếu khác mới thoát chờ.
- [ ] Với yêu cầu đã có lệnh bắt đầu, nhập đủ phần còn thiếu đưa yêu cầu về `dang_thuc_hien`; tính cả nhu cầu đã cấp thay vì đòi lại toàn bộ định mức.
- [ ] Nhiều lệnh trong một yêu cầu cùng cần NVL-A: so tồn với tổng lượng còn thiếu; không đánh giá đủ bằng cách so từng lệnh độc lập.
- [ ] Lệnh hoàn thành/hủy không góp nhu cầu chưa cấp; phiếu xuất chưa duyệt không được tính là đã cấp.
- [ ] Hoàn tất phiếu nhập kiểm tra mọi yêu cầu đang chờ, không chỉ yêu cầu có mặt hàng trùng dòng nhập. Không sửa yêu cầu đã hoàn thành/hủy.
- [ ] Lỗi đánh giá lại hoặc audit rollback toàn bộ phiếu nhập, số dư và ledger; không để nhập thành công nhưng yêu cầu đổi trạng thái dở dang.
- [ ] Gọi lại phiếu nhập đã hoàn tất không ghi trùng; hai lần hoàn tất đồng thời không cộng kho hoặc tạo audit chuyển trạng thái hai lần.
- [ ] Kiểm thử cạnh tranh với duyệt xuất/bắt đầu/hủy yêu cầu trên PostgreSQL thật trong môi trường test, xác nhận không mất cập nhật hoặc để tồn âm.
- [ ] Chạy toàn bộ chuỗi ở §4.2 đến duyệt xuất TP: YCSX `hoan_thanh`, tồn TP-A = 0, NVL-A = 0 và ledger khớp số dư.

## 5. Các quyết định nghiệp vụ cần dev chốt

Những mục dưới đây chưa được chốt bởi yêu cầu viết tài liệu. Có thể sửa phần độc lập đã rõ của SX-01; phải hỏi dev trước khi triển khai hành vi phụ thuộc các quyết định này. Khi được chốt, ghi ngày, nội dung và nguồn trong tài liệu quyết định/contract, rồi cập nhật checklist tương ứng.

| ID | Điểm chưa thống nhất | Thông tin cần xác nhận |
| --- | --- | --- |
| D-01 | Sơ đồ cho N lập phiếu xuất; contract v3 §10 và code chỉ cho Q | Giữ Q lập cả hai loại phiếu và sửa sơ đồ, hay đổi contract để N lập? Nếu đổi: quyền sửa/gửi/về nháp, phạm vi sở hữu, người duyệt và Q có còn được lập không? |
| D-02 | Sơ đồ có hạn hoàn thành; contract/schema hiện chưa có | Là ngày hay thời điểm? Tên trường, bắt buộc khi tạo/gửi hay tùy chọn, timezone, kiểm tra ngày quá khứ, ai sửa ở trạng thái nào? Hạn của YCSX có áp vào LSX con không? |
| D-03 | Có hai bước N báo thiếu nhưng chưa có nghiệp vụ gửi/lưu riêng | Chỉ là thông tin thiếu trên kế hoạch hay phải có bản ghi/yêu cầu riêng? Ai nhận/xử lý, dữ liệu và trạng thái, có cần thông báo trong ứng dụng không? Không suy ra yêu cầu gửi email/Slack. |
| D-04 | Sơ đồ tạo LSX sau khi N báo thiếu; code tạo cây lệnh khi Q gửi YCSX | Giữ tính/chụp/tạo cây lệnh trước khi gửi, hay bổ sung bước sau tiếp nhận? Nếu đổi: khi nào khóa kế hoạch, ai xác nhận, xử lý tồn/BOM thay đổi và ngăn tạo trùng thế nào? |
| D-05 | Contract yêu cầu so nhu cầu chưa cấp nhưng chưa mô tả chi tiết đầu ra BTP tương lai khi tự kiểm tra lại | Ví dụ cha cần 10 cụm, tồn cụm 0, đã có lệnh con 10 cụm và vừa nhập đủ linh kiện: đánh giá YCSX đủ ngay dựa trên khả năng sản xuất, hay tiếp tục chờ đủ cụm? Nếu chờ, khi duyệt HTSX con có cần kích hoạt kiểm tra lại không? Chốt cách trừ nhu cầu được lệnh con đáp ứng để không đếm trùng hoặc kẹt chờ. |

- [ ] Chốt D-01 và cập nhật sơ đồ/contract trước khi đổi quyền.
- [ ] Chốt D-02 trước khi thêm trường API/DB/UI.
- [ ] Chốt D-03 trước khi tạo module, endpoint, bảng hoặc thông báo mới.
- [ ] Chốt D-04 trước khi thay thời điểm sinh LSX/chụp BOM.
- [ ] Chốt D-05 trước khi viết thuật toán đánh giá lại cho cây nhiều cấp và tiêu chí E2E của nhánh đó.

## 6. SX-02 — Khác biệt quyền lập phiếu xuất

**Phân loại: mâu thuẫn yêu cầu; code hiện phù hợp contract v3, chưa phải lỗi quyền.**

Bằng chứng: `ReadActor` cho Q/N, `WriteActor` chỉ cho Q trong [router phiếu xuất](../backend/app/modules/phieu_xuat/router.py); `PhieuXuatService._role(write=True)` cũng chỉ cho Q. Frontend [permissions.js](../frontend/src/features/auth/permissions.js) và [MaterialIssuingPage.jsx](../frontend/src/features/material-issuing/MaterialIssuingPage.jsx) cho N chỉ xem. Quy tắc áp dụng cho cả `xuat_vat_tu` và `xuat_thanh_pham`.

- [ ] Sau D-01, nếu giữ contract: sửa tài liệu/sơ đồ để Q lập/gửi/duyệt, N xem phiếu liên quan công việc được giao; không mở quyền N chỉ để khớp hình cũ.
- [ ] Nếu cho N lập: đặc tả ma trận quyền tạo/đọc/sửa/xóa nháp/gửi/về nháp/duyệt/từ chối cho Q, N, admin trước khi sửa.
- [ ] Nếu đổi quyền, cập nhật cả router và service; kiểm tra nguồn là YCSX/LSX được giao đúng N. Lấy người lập từ JWT; không tin ID người tạo trong body.
- [ ] Cập nhật UI và contract đồng bộ; chỉ ẩn nút không thay được kiểm soát backend. Giữ các kiểm tra trạng thái, ETag, nhu cầu và tồn lúc duyệt.
- [ ] Kiểm thử Q/N/admin, N ngoài phạm vi, hai loại phiếu và đọc trực tiếp URL/API; thêm ca 401/403 đúng ma trận đã chốt.
- [ ] Cập nhật `docs/sequence/phieu_xuat.md` nếu hành vi endpoint thay đổi.

## 7. SX-03 — Thiếu hạn hoàn thành YCSX

Bằng chứng: `YeuCauCreate`/`YeuCauPatch` chỉ có `mat_hang_id`, `so_luong`, `nhan_vien_duoc_giao_id`; `YeuCauRead`, ORM `YeuCauSanXuat`, bảng SQL và form [RequestsPage.jsx](../frontend/src/features/production/RequestsPage.jsx) chưa có hạn. Schema dùng `extra="forbid"`; thử gửi `han_hoan_thanh` hiện bị từ chối, không được lưu ngầm. `completed_at` là thời điểm hoàn thành thực tế, không thể dùng thay hạn.

- [ ] Chốt D-02, ghi định nghĩa và validation chính xác. Không coi tên thử nghiệm `han_hoan_thanh` là tên API đã được duyệt.
- [ ] Nếu triển khai, cập nhật đồng bộ create/patch/read, ORM, repository, `init.sql`, contract và UI tạo/sửa/chi tiết. Chỉ bổ sung seed nếu quyết định nullable/default thực sự yêu cầu.
- [ ] Kiểm tra tác động đến ETag và token kế hoạch khi hạn thay đổi; tài liệu hóa thay đổi hợp đồng và tương thích client.
- [ ] Kiểm thử lưu/đọc lại, thiếu/null/sai định dạng, biên timezone/ngày, quyền và trạng thái được sửa theo D-02.
- [ ] Không tự thêm cảnh báo quá hạn, lọc/sort, kế thừa hạn LSX hoặc tác vụ nhắc hạn nếu dev chưa duyệt.
- [ ] Cập nhật sequence YCSX và đối chiếu schema trên PostgreSQL test mới/trống.

## 8. SX-04 — Chưa có bước N gửi báo thiếu/yêu cầu nhập NVL riêng

Hiện có `KeHoachPreview.thieu_vat_tu` và các dòng `vat_tu` gồm mã, tên, đơn vị, cần từ kho, hiện có, còn thiếu. Frontend hiển thị cảnh báo và bảng thiếu khi Q tính kế hoạch. `GET /lenh_san_xuat/{id}/vat_tu` cho biết cần/đã cấp/còn cấp/tồn hiện tại. Các dữ liệu này không phải bản ghi “N đã gửi báo thiếu”; chưa tìm thấy endpoint/UI lưu và chuyển báo thiếu cho Q.

- [ ] Chốt riêng D-03 cho báo thiếu TP và đề nghị nhập NVL; không mặc định chúng là cùng một chứng từ.
- [ ] Nếu chỉ dùng hiển thị tính toán, cập nhật sơ đồ và mô tả thao tác thực tế; xác nhận cách N/Q xem số thiếu sau khi YCSX đã gửi, vì `tinh_ke_hoach` hiện chỉ cho YCSX nháp.
- [ ] Nếu có bản ghi gửi riêng, chốt trước schema/API: nguồn YCSX hoặc LSX, mặt hàng, lượng thiếu, người gửi/nhận, thời điểm, ghi chú, trạng thái, xử lý gửi lặp và kết quả xử lý.
- [ ] Chốt số thiếu được chụp tại lúc gửi hay luôn tính lại; backend kiểm tra nguồn và phạm vi N. Không tin số tồn do client gửi.
- [ ] Báo thiếu không trực tiếp cộng/trừ tồn, không tự tạo/hoàn tất phiếu nhập hoặc LSX ngoài luồng đã chốt.
- [ ] Chốt thiết kế UI, cập nhật contract/sequence và tích hợp backend/frontend trong phạm vi được phép. Khi triển khai UI có phụ thuộc chưa đáp ứng, ghi vào `doc/MISSING.md` theo `doc/FRONTEND_RULES.md`.
- [ ] Kiểm thử N được giao/N khác/Q/admin, số lượng không hợp lệ, nguồn đã đóng, gửi lại và gửi khi tồn vừa thay đổi; không tạo ghi sổ kho từ thao tác báo thiếu.

## 9. SX-05 — Khác biệt thời điểm tạo LSX và chụp BOM

Code hiện tại yêu cầu tính kế hoạch ở YCSX nháp, gửi với token TTL 10 phút và `If-Match`; `gui()` kiểm tra lại rồi gọi `add_lenh_tree()`. Khi đã gửi, cây lệnh giữ lượng/BOM/nhu cầu đã chụp. Nhánh đủ TP trả cây rỗng. Không có API tạo LSX thủ công. Điều này phù hợp contract §8–§9 nhưng khác thứ tự trong sơ đồ.

- [ ] Sau D-04, nếu giữ luồng hiện tại: sửa sơ đồ thành Q tính/chốt/sinh cây khi gửi YCSX, sau đó phân công và gửi từng LSX; N tiếp nhận để thực hiện.
- [ ] Nếu đổi sang tạo LSX sau báo thiếu: chốt endpoint, trạng thái trung gian, người được thao tác, thời điểm chụp và chống tạo trùng trước khi viết code. Không tự thêm `POST /lenh_san_xuat`.
- [ ] Giữ nguyên nguyên tắc chỉ sản xuất phần TP thiếu, dùng tồn BTP trước, nhu cầu cha không lẫn linh kiện của con và không thay kế hoạch đã chốt theo BOM mới.
- [ ] Kiểm thử đủ TP không tạo lệnh, thiếu một phần TP, đủ/thiếu BTP, BOM thiếu/đổi phiên bản, token hết hạn và hai request gửi đồng thời.

## 10. Kịch bản nghiệm thu toàn luồng

Các số liệu sau là fixture kiểm thử, không thay định mức kỹ thuật đã chốt của project. Tạo mặt hàng active, có đơn giá hợp lệ, N hoạt động và BOM hợp lệ. Tồn đầu kỳ phải khớp ledger. Dùng vai trò lập phiếu theo D-01; trước khi có quyết định mới, dùng Q như contract hiện hành.

| Ca | Dữ liệu và hành động | Kết quả bắt buộc |
| --- | --- | --- |
| E2E-01: TP có sẵn | Cần 5 TP, tồn 5; tính/gửi rồi lập/gửi/duyệt xuất 5 | Không có LSX; chỉ duyệt xuất mới trừ tồn về 0, YCSX hoàn thành |
| E2E-02: BTP đủ | Cần 5 TP, tồn TP 2; BOM mỗi TP cần 2 cụm; tồn cụm 6 | Chỉ có LSX cha 3 TP; xuất 6 cụm, sản xuất/duyệt 3 TP, cuối cùng xuất đủ 5 TP; không tạo lệnh con |
| E2E-03: BTP thiếu | Như trên nhưng tồn cụm 2; BOM mỗi cụm cần 3 linh kiện, tồn linh kiện 12 | LSX cha 3 TP cần 6 cụm; LSX con 4 cụm cần 12 linh kiện. Duyệt đầu ra con trước khi cấp lượng cụm mới cho cha; cuối cùng xuất đủ 5 TP |
| E2E-04: Thiếu NVL một cấp | Fixture §4.2, bổ sung 9 rồi 1 NVL-A | Chưa đủ vẫn chờ; đủ thì thoát chờ, sản xuất và xuất TP kết thúc được |
| E2E-05: Thiếu NVL nhiều cấp | E2E-03 nhưng ban đầu chỉ có 5 linh kiện; bổ sung 7 | Không tạo lại cây/BOM. Trạng thái sau nhập và tác nhân kiểm tra BTP đúng D-05; có đường hoàn tất con → cha → xuất đủ TP, không kẹt chờ |
| E2E-06: Nhiều đợt | LSX cần 5, HTSX lần lượt 2 và 3; thêm đợt 1 | Hai đợt hợp lệ cộng tổng 5; đợt vượt bị từ chối, không thêm tồn. YCSX vẫn chưa hoàn thành nếu chưa xuất đủ TP |
| E2E-07: Gửi lại/cạnh tranh | Gọi lại duyệt xuất/HTSX đã thành công và gửi hai request đồng thời | Không ghi trùng ledger/audit, không âm tồn, không vượt lượng; response và ETag đúng contract |
| E2E-08: Quyền và rollback | N sai phạm vi, admin nghiệp vụ, ETag cũ, lỗi ghi audit | Bị chặn đúng contract; lỗi trong transaction không để số dư/ledger/trạng thái cập nhật một phần |

- [ ] Thực thi E2E-01 đến E2E-04 và lưu bằng chứng request/response cùng số dư, ledger, trạng thái.
- [ ] Thực thi E2E-05 sau D-05; không tự điền kỳ vọng còn chưa được dev chốt.
- [ ] Thực thi E2E-06 đến E2E-08, gồm kiểm tra PostgreSQL thực tế cho transaction/khóa/trigger.
- [ ] Kiểm thử UI với backend thật cho các thao tác tạo/gửi/duyệt/xuất cuối. Test browser dùng API mock chỉ chứng minh tương tác UI, không thay thế E2E dữ liệu.

## 11. Kiểm chứng đã thực hiện và giới hạn

Kết quả dưới đây thuộc **phiên rà soát ngày 10/11/2026**, không phải bằng chứng các checklist sửa lỗi đã hoàn thành:

| Kiểm tra | Kết quả và giới hạn |
| --- | --- |
| Đọc router/service/repository/schema/model, SQL và UI liên quan | Xác định các hiện trạng ở trên; không đọc trạng thái database ứng dụng |
| Chạy độc lập `calculate_plan()` trích từ AST source, dùng schema thực | 5 ca đạt: đủ TP, thiếu TP nhưng đủ cụm, chỉ sản xuất cụm thiếu, tính NVL thiếu, phát hiện thiếu BOM. Không import toàn bộ service, không gọi HTTP/DB |
| Schema và policy độc lập | Xác nhận trường hạn chưa được chấp nhận, N không ghi phiếu xuất, Q được ghi và nguồn đang chờ bị chặn xuất TP |
| Frontend build bằng Vite | Thành công; output tạm đã được dọn, không sửa source |
| `node --test tests/client.test.js tests/contracts.test.js tests/navigation.test.js` trong `frontend/` | 14 ca đạt; 1 file test lỗi import `src/features/dashboard/auditFormat.js` không tồn tại. Không phải toàn bộ suite đã xanh |
| Backend API/PostgreSQL/E2E | Chưa chạy: Python hệ thống thiếu SQLAlchemy; `backend/.venv/Scripts/python.exe` thiếu FastAPI; checkout hiện không có `backend/tests` |

- [ ] Khôi phục/chuẩn bị môi trường backend và xác định vị trí bộ test thực tế trước khi triển khai; không coi các con số kiểm thử lịch sử trong docs là kết quả hiện tại.
- [ ] Có test tái hiện SX-01 và các ca nghiệm thu; nếu tạo bộ test mới, theo cấu hình pytest trong `backend/pyproject.toml`, dùng database test riêng.
- [ ] Phân loại lỗi import frontend nói trên và báo phạm vi xử lý; không xóa/làm yếu test để lấy kết quả xanh hoặc tự sửa ngoài phạm vi.
- [ ] Chạy lint/type/test phù hợp phần thay đổi và ghi chính xác lệnh, môi trường, số ca đạt/thất bại/chưa chạy.

## 12. Giới hạn triển khai và bàn giao

- [ ] Đọc lại source và trạng thái Git trước khi bắt đầu; giữ nguyên thay đổi của dev. Không áp dụng skill superpowers hoặc dùng skill GitNexus để điều phối theo `AGENTS.md`.
- [ ] Chỉ sửa phần được dev cho phép. Tài liệu này là đặc tả vấn đề; không tự coi các quyết định D-01 đến D-05 là đã được phê duyệt.
- [ ] Dùng `MatHang.so_luong_ton` và `GiaoDichKho`, không tạo lại bảng tồn kho legacy để chữa luồng này.
- [ ] Nếu bổ sung schema theo quyết định đã chốt, đồng bộ ORM/SQL/contract và ghi ảnh hưởng tương thích. Phạm vi demo hiện chỉ bootstrap DB mới/trống bằng `init.sql`/`seed.sql`; không tạo/chạy migration hoặc sửa database đã có dữ liệu.
- [ ] Không xóa volume, reset DB, seed lại dữ liệu, dùng `make clear` hoặc `docker compose down -v`. Không dùng database ứng dụng làm nơi thử ghi.
- [ ] Cập nhật sequence cho mọi endpoint có luồng thay đổi, dù không đổi URL; kiểm tra/render Mermaid nếu có công cụ và báo giới hạn nếu chưa kiểm tra được.
- [ ] Chỉ đóng một vấn đề khi đã triển khai và kiểm chứng, hoặc dev chốt bỏ/đổi yêu cầu và tài liệu đã được cập nhật. Không đóng vì chỉ ẩn nút hoặc sửa mô tả.
- [ ] Bàn giao danh sách file, quyết định áp dụng, request/response hoặc schema thay đổi, kết quả kiểm thử và phần còn chờ. Không tự accept, commit hoặc push.
