# Intent — Hệ thống xBike MRP

- Phiên bản: 1.0
- Ngày lập: 22/10/2026
- Bối cảnh: Đồ án học phần Hệ thống thông tin doanh nghiệp, Đại học Sài Gòn.
- Cơ sở: Nhu cầu và quyết định của người khởi xướng đã được làm rõ trong cuộc trao đổi, biên bản chấm đồ án, hai user-flow và tài liệu SRS hiện có.
- Mục đích tài liệu: Xác định vì sao cần xây dựng hệ thống, phục vụ ai, làm những gì và kết quả nào được xem là đạt. Đây là đầu vào để viết đặc tả và kế hoạch triển khai, không thay thế thiết kế CSDL hoặc API contract.

## 1. Vấn đề cần giải quyết

xBike quản lý công thức cấu tạo sản phẩm (BOM) bằng Excel. Các nghiệp vụ nhập kho, yêu cầu sản xuất, lệnh sản xuất và hoàn thành sản xuất được ghi nhận bằng phiếu viết tay và lưu trữ trên giấy.

Khó khăn ưu tiên là khả năng truy vết khi số lượng sai. Quản lý phải tìm và đối chiếu nhiều chứng từ giấy để xác định nghiệp vụ nào làm thay đổi số lượng, ai thực hiện và thay đổi vào thời điểm nào. Việc lưu trữ phân tán khiến tra cứu và đối soát khó khăn.

Hệ thống cần quản lý tập trung BOM, chứng từ, tồn kho và lịch sử xử lý; liên kết các bước từ yêu cầu thành phẩm đến xuất thành phẩm để hỗ trợ truy vết sai lệch.

## 2. Mục tiêu và kết quả mong muốn

1. Tra cứu được lịch sử tăng, giảm tồn của từng mặt hàng và chứng từ nguồn gây ra từng biến động.
2. Theo dõi được yêu cầu thành phẩm, các lệnh sản xuất và chứng từ thực hiện liên quan.
3. Tính được lượng thành phẩm cần sản xuất và nhu cầu vật tư theo BOM hai cấp, có sử dụng tồn bán thành phẩm sẵn có.
4. Ghi nhận nhập, xuất và hoàn thành sản xuất đúng thời điểm xác nhận hoặc phê duyệt; mỗi nghiệp vụ chỉ tác động tồn kho một lần.
5. Sửa sai số lượng phiếu nhập kho NVL bằng chứng từ điều chỉnh, bảo toàn lịch sử gốc.
6. Ghi nhận các điều chỉnh không hợp lệ thành ticket để quản lý đối soát và đóng thủ công.
7. Cung cấp bản mô phỏng MRP đủ luồng nghiệp vụ và đáp ứng các yêu cầu chung của đồ án.

Hệ thống hỗ trợ tìm nguyên nhân sai lệch qua dữ liệu đã ghi nhận. Việc xác định số lượng thực tế vẫn cần con người kiểm tra hàng và đối chiếu chứng từ.

## 3. Người dùng và trách nhiệm

| Vai trò | Trách nhiệm |
|---|---|
| Quản lý kho, đồng thời là quản lý sản xuất | Quản lý BOM và dữ liệu kho; lập và xác nhận phiếu nhập; tạo yêu cầu thành phẩm và lệnh sản xuất; giao việc; duyệt phiếu xuất và chứng từ hoàn thành; lập điều chỉnh; xử lý ticket; xem báo cáo. |
| Nhân viên | Nhận công việc; lập đề nghị xuất vật tư; thực hiện và ghi nhận sản xuất; lập chứng từ hoàn thành; lập đề nghị xuất thành phẩm. |
| Admin | Quản lý tài khoản và phân quyền; sử dụng giao diện quản trị riêng. Có chức năng tra cứu dữ liệu theo yêu cầu chung của đồ án, không mặc định có quyền xác nhận hoặc duyệt nghiệp vụ kho, sản xuất. |

## 4. Ranh giới và phạm vi

### 4.1 Điểm bắt đầu và kết thúc

- Nhu cầu thành phẩm bắt nguồn từ đơn đặt hàng thuộc hệ thống khác.
- Trong MRP, luồng bắt đầu khi quản lý kho tạo **phiếu yêu cầu thành phẩm** với mặt hàng và số lượng cần đáp ứng.
- Không xây dựng nghiệp vụ quản lý đơn đặt hàng hoặc tích hợp tự động với hệ thống đơn hàng trong phạm vi này.
- Một yêu cầu được đáp ứng khi lượng xuất thành phẩm đã duyệt đáp ứng số lượng yêu cầu. Sản xuất xong chưa đồng nghĩa với hoàn tất yêu cầu.

### 4.2 Chức năng trong phạm vi

- Danh mục NVL/linh kiện, bán thành phẩm, thành phẩm và nhà cung cấp/nguồn nhập.
- Quản lý BOM hai cấp.
- Phiếu nhập kho NVL.
- Phiếu yêu cầu thành phẩm và kiểm tra khả năng đáp ứng theo tồn kho, BOM.
- Lệnh sản xuất xe và lệnh sản xuất cụm bánh xe riêng khi cần.
- Phiếu đề nghị xuất NVL/bán thành phẩm và phê duyệt xuất.
- Ghi nhận quá trình sản xuất và chứng từ hoàn thành có phê duyệt.
- Phiếu đề nghị xuất thành phẩm và phê duyệt xuất.
- Tra cứu chứng từ, lịch sử thao tác và biến động tồn kho.
- Điều chỉnh số lượng phiếu nhập kho NVL đã xác nhận.
- Ticket cho trường hợp điều chỉnh không hợp lệ, đóng thủ công.
- Báo cáo nhập, xuất, tồn theo tháng, quý, năm.
- Đăng nhập, phân quyền và giao diện Admin theo yêu cầu chấm.

### 4.3 Ngoài phạm vi phiên bản đồ án

- HRM, CRM, kế toán, thanh toán và quản lý đơn bán hàng.
- Quy trình mua hàng đầy đủ như đặt mua, duyệt mua và thanh toán nhà cung cấp. Thiếu vật tư chỉ làm phát sinh thông báo nhu cầu nhập bổ sung.
- Hoạch định năng lực máy móc, tối ưu lịch sản xuất hoặc MRP theo kỳ thời gian đầy đủ.
- Các ngoại lệ sản xuất như phế phẩm, hoàn trả vật tư thừa, hủy lệnh hoặc xử lý hoàn thành từng phần như một luồng riêng.
- Điều chỉnh sai số lượng trên phiếu xuất hoặc chứng từ hoàn thành sản xuất.
- Tự động suy luận nguyên nhân sai lệch, tự xử lý ticket hoặc tự liên kết ticket với phiếu điều chỉnh mới.

## 5. Thuật ngữ thống nhất

| Thuật ngữ | Ý nghĩa |
|---|---|
| Phiếu yêu cầu thành phẩm | Ghi nhận nhu cầu thực tế cần đáp ứng. Một số tài liệu cũ gọi là yêu cầu sản xuất; trong intent này dùng tên yêu cầu thành phẩm để phân biệt với công việc sản xuất. |
| Lệnh sản xuất | Công việc do quản lý kho chủ động tạo khi cần sản xuất phần thành phẩm hoặc bán thành phẩm còn thiếu. |
| Chứng từ hoàn thành sản xuất | Nhân viên báo sản lượng hoàn thành; chỉ được cộng kho khi quản lý duyệt. |
| Phiếu điều chỉnh | Chứng từ sửa sai số lượng phiếu nhập kho NVL đã xác nhận, có liên kết với phiếu nhập gốc. |
| Ticket | Hồ sơ sự việc điều chỉnh không hợp lệ cần xử lý riêng; không phải chứng từ cập nhật tồn kho. |

## 6. BOM sử dụng trong đồ án

Có năm BOM riêng: Mountain Pro, City Ride, Speed Sport, Kids Fun và Cụm bánh xe. Bốn model xe có BOM riêng, dù định mức trong dữ liệu minh họa hiện giống nhau. Các định mức dưới đây lấy từ hình BOM người khởi xướng cung cấp để dùng cho đồ án, không khẳng định là định mức kỹ thuật sản xuất thực tế.

### 6.1 BOM cho một chiếc xe của mỗi model

| Thành phần | Số lượng | Đơn vị |
|---|---:|---|
| Khung xe | 1 | Chiếc |
| Phuộc xe | 1 | Chiếc |
| Cụm bánh xe | 2 | Chiếc |
| Lốp xe | 2 | Chiếc |
| Xích xe | 1 | Chiếc |
| Bàn đạp | 2 | Chiếc |
| Dây phanh | 2 | Chiếc |
| Yên xe | 1 | Chiếc |
| Đĩa xích | 1 | Chiếc |
| Bộ ốc vít | 1 | Bộ |

### 6.2 BOM cho một cụm bánh xe

| Thành phần | Số lượng | Đơn vị |
|---|---:|---|
| Vành bánh xe | 1 | Chiếc |
| Moay-ơ | 1 | Chiếc |
| Nan hoa | 36 | Chiếc |

Cụm bánh xe là bán thành phẩm có tồn kho riêng. Hệ thống sử dụng cụm bánh có sẵn trước, chỉ phân rã phần thiếu thành nhu cầu vành, moay-ơ và nan hoa. Không đồng thời tính nhu cầu linh kiện cấp dưới cho các cụm đã có sẵn.

## 7. Luồng nghiệp vụ mong muốn

### 7.1 Nhập kho NVL

1. Quản lý kho lập phiếu nhập, chọn NVL, số lượng, ngày nhập, nhà cung cấp/nguồn nhập và ghi chú.
2. Hệ thống kiểm tra thông tin; quản lý có thể lưu nháp và sửa trước khi xác nhận.
3. Quản lý xác nhận hoàn tất nhập kho. Không có người duyệt độc lập.
4. Hệ thống ghi nhận phiếu hoàn tất, tăng tồn và lưu lịch sử nhập kho đồng thời.

### 7.2 Tiếp nhận nhu cầu và xác định sản xuất

1. Quản lý kho tạo phiếu yêu cầu thành phẩm.
2. Hệ thống kiểm tra tồn thành phẩm.
3. Nếu đủ, quản lý giao nhân viên lập phiếu xuất thành phẩm; quản lý duyệt rồi hệ thống trừ tồn.
4. Nếu thiếu, lượng cần sản xuất là phần còn thiếu. Quản lý chủ động tạo lệnh sản xuất; không bắt buộc phải đủ vật tư mới được tạo lệnh.
5. Hệ thống tính nhu cầu theo BOM, sử dụng tồn bán thành phẩm trước và xác định vật tư còn thiếu.
6. Nếu thiếu NVL, hiển thị danh sách, số lượng cần, hiện có và thiếu. Yêu cầu được giữ ở trạng thái **Chờ bổ sung vật tư**; lệnh đã tạo chưa được thực hiện khi chưa đáp ứng điều kiện cấp vật tư.
7. Sau khi nhập bổ sung, kiểm tra lại khả năng đáp ứng để tiếp tục yêu cầu hiện có.

### 7.3 Sản xuất bán thành phẩm và thành phẩm

1. Khi cụm bánh xe không đủ, quản lý tạo lệnh sản xuất cụm bánh xe riêng, phục vụ nhu cầu của lệnh lắp xe.
2. Nhân viên lập đề nghị xuất vật tư cho lệnh tương ứng.
3. Quản lý duyệt phiếu xuất; hệ thống kiểm tra lại tồn, trừ lượng xuất hợp lệ và ghi lịch sử.
4. Nhân viên thực hiện sản xuất sau khi vật tư cần thiết đã được cấp, rồi lập và gửi chứng từ hoàn thành.
5. Quản lý duyệt chứng từ; hệ thống mới cộng kho đầu ra tương ứng. Không trừ lại vật tư đã xuất.
6. Cụm bánh xe đã được duyệt nhập kho mới được xuất cho lệnh lắp xe. Lệnh lắp xe áp dụng cùng cơ chế cấp vật tư và duyệt hoàn thành.
7. Sau khi xe được duyệt nhập kho, nhân viên lập phiếu xuất thành phẩm để đáp ứng yêu cầu ban đầu.
8. Quản lý duyệt phiếu xuất thành phẩm; hệ thống kiểm tra tồn, trừ kho và cập nhật kết quả đáp ứng yêu cầu.

### 7.4 Điều chỉnh sai số lượng phiếu nhập NVL

1. Quản lý mở phiếu nhập đã xác nhận, chọn điều chỉnh số lượng và nhập số lượng đúng cùng lý do.
2. Hệ thống tính chênh lệch so với số lượng có hiệu lực sau các lần điều chỉnh thành công trước đó, hiển thị tác động tồn kho để quản lý xác nhận.
3. Quản lý tự xác nhận điều chỉnh; không bổ sung vai trò duyệt độc lập.
4. Nếu hợp lệ: lưu phiếu điều chỉnh liên kết với phiếu nhập gốc, cập nhật tồn và lịch sử đồng thời; báo thành công kèm mã chứng từ.
5. Nếu không hợp lệ, chẳng hạn làm tồn kho âm: không áp dụng thay đổi tồn, lưu sự việc thất bại thành ticket và báo lý do cùng mã ticket.

Phiếu nhập gốc được giữ nguyên, không sửa đè hoặc xóa sau xác nhận. Ví dụ: nhập 100, đã điều chỉnh thành công về 80, sau đó xác định số đúng là 85 thì lần điều chỉnh tiếp theo cộng 5.

### 7.5 Xử lý ticket

- Ticket lưu bối cảnh sự việc ban đầu: mã phiếu nhập, mặt hàng, số lượng đề nghị điều chỉnh, nguyên nhân thất bại, người thực hiện và thời điểm.
- Quản lý đối soát và xử lý sự việc riêng, sau đó đóng ticket thủ công với kết quả xử lý bắt buộc.
- Lưu người đóng và thời điểm đóng để truy vết.
- Không thiết lập quan hệ CSDL giữa ticket và phiếu điều chỉnh mới được tạo sau đó.
- Phiếu điều chỉnh mới được xử lý độc lập, không tự cập nhật hoặc đóng ticket.
- Đóng ticket không cập nhật tồn kho và không yêu cầu phải có một phiếu điều chỉnh mới thành công.

## 8. Nguyên tắc kiểm soát và truy vết

| Nghiệp vụ | Mốc tác động tồn kho |
|---|---|
| Nhập NVL | Tăng khi quản lý xác nhận hoàn tất phiếu nhập. |
| Yêu cầu thành phẩm, tạo lệnh, tính nhu cầu | Không trực tiếp tăng hoặc giảm tồn. |
| Xuất NVL/bán thành phẩm | Giảm khi quản lý duyệt phiếu xuất. |
| Hoàn thành sản xuất | Tăng khi quản lý duyệt chứng từ hoàn thành. |
| Xuất thành phẩm | Giảm khi quản lý duyệt phiếu xuất thành phẩm. |
| Điều chỉnh phiếu nhập NVL | Tăng hoặc giảm theo chênh lệch khi xác nhận thành công. |
| Tạo hoặc đóng ticket | Không tác động tồn kho. |

- Lưu nháp, gửi chờ duyệt hoặc từ chối duyệt không làm thay đổi tồn kho.
- Kiểm tra quyền, trạng thái chứng từ và tồn kho tại thời điểm thực hiện nghiệp vụ. Kết quả tính nhu cầu trước đó không bảo đảm tồn vẫn đủ khi xuất.
- Theo cơ chế hiện tại của SRS, tính nhu cầu không giữ chỗ vật tư; phải kiểm tra lại khi duyệt xuất, kể cả có nhiều yêu cầu đồng thời.
- Chứng từ, tồn kho và lịch sử biến động phải nhất quán; lỗi giữa chừng không được để cập nhật một phần hoặc ghi nhận hai lần.
- Sự việc điều chỉnh không hợp lệ phải được lưu thành ticket dù thao tác cập nhật kho không được áp dụng.
- Mỗi biến động kho phải tra được mặt hàng, lượng tăng/giảm, thời điểm, người thực hiện và chứng từ nguồn.
- BOM dùng cho một công việc sản xuất phải có căn cứ lịch sử để việc sửa BOM về sau không làm sai truy vết công việc đã lập; cách lưu cụ thể được xác định trong đặc tả.
- Báo cáo tồn kho sử dụng các biến động đã ghi nhận thành công, bao gồm điều chỉnh; không tính phiếu nháp, chờ duyệt hoặc thất bại là giao dịch kho đã xảy ra.

## 9. Tiêu chí nghiệm thu nghiệp vụ

| Mã | Tình huống | Kết quả cần đạt |
|---|---|---|
| AC-01 | Lưu nháp rồi xác nhận một phiếu nhập NVL | Nháp không tăng tồn; xác nhận tăng đúng số lượng một lần, tra được phiếu và lịch sử. |
| AC-02 | Yêu cầu 10 xe, tồn đủ 10 xe | Đi theo luồng xuất thành phẩm; không cần tạo lệnh sản xuất. Duyệt xuất mới giảm tồn. |
| AC-03 | Yêu cầu 10 xe, tồn 3 xe | Hệ thống xác định cần sản xuất 7 xe; quản lý tạo lệnh cho phần thiếu. |
| AC-04 | Lệnh cần sản xuất nhưng thiếu NVL | Yêu cầu được giữ ở trạng thái chờ bổ sung, hiển thị lượng thiếu; nhập thêm và kiểm tra lại để tiếp tục. |
| AC-05 | Cần sản xuất 7 xe, có sẵn 4 cụm bánh | Cần tổng cộng 14 cụm; chỉ sản xuất thêm 10 cụm, tương ứng 10 vành, 10 moay-ơ và 360 nan hoa. Các NVL trực tiếp khác tính theo 7 xe. |
| AC-06 | Nhân viên lập chứng từ hoàn thành cụm bánh hoặc xe | Chưa tăng tồn khi lập/gửi; chỉ tăng sau duyệt. Vật tư không bị trừ lần thứ hai. |
| AC-07 | Điều chỉnh phiếu nhập từ 100 về 80, tồn hiện tại đủ giảm 20 | Giảm tồn 20; giữ nguyên phiếu gốc và lưu chứng từ điều chỉnh cùng lý do. Điều chỉnh tiếp về 85 chỉ cộng 5. |
| AC-08 | Đề nghị giảm 20 nhưng tồn hiện tại chỉ còn 10 | Chặn điều chỉnh; giữ nguyên tồn; lưu ticket với lý do và thông tin sự việc. |
| AC-09 | Quản lý đóng ticket | Bắt buộc có kết quả xử lý, người đóng và thời điểm; tồn không đổi; không bắt buộc liên kết phiếu điều chỉnh mới. |
| AC-10 | Tạo một phiếu điều chỉnh mới sau khi có ticket | Phiếu xử lý độc lập, không có quan hệ CSDL tới ticket, không tự đóng ticket. |
| AC-11 | Tra cứu mặt hàng hoặc yêu cầu thành phẩm | Tìm được chứng từ và lịch sử liên quan để đối soát người thực hiện, thời điểm và số lượng. |
| AC-12 | Lặp thao tác xác nhận/duyệt hoặc xảy ra lỗi cập nhật | Không ghi nhận trùng và không để lại tồn kho, trạng thái chứng từ, lịch sử bị lệch nhau. |
| AC-13 | Xem báo cáo tháng/quý/năm | Nhập, xuất, điều chỉnh và tồn đối chiếu được với các biến động đã ghi nhận thành công. |
| AC-14 | Người dùng thao tác ngoài quyền | Hệ thống từ chối; Admin không mặc định được duyệt nghiệp vụ kho hoặc sản xuất. |

Các số liệu trên là kịch bản kiểm chứng, không phải dữ liệu vận hành thực tế. Chưa đặt mục tiêu định lượng về thời gian tra cứu vì chưa có số liệu khảo sát ban đầu.

## 10. Ràng buộc của đồ án

Chọn phần MRP trong ba lựa chọn HRM/CRM/MRP của biên bản chấm. Vẫn phải đáp ứng các phần dùng chung:

- Báo cáo gồm giới thiệu doanh nghiệp, khảo sát ít nhất 15 câu hỏi và kết luận khảo sát, mô tả bài toán, sơ đồ chức năng, sơ đồ ngữ cảnh và luồng dữ liệu mức đỉnh.
- Thiết kế CSDL với mô tả bảng, thuộc tính; trình bày giao diện và chức năng.
- Phương án cài đặt, chuyển đổi từ cách quản lý cũ, hướng dẫn sử dụng, sao lưu và phục hồi CSDL.
- Giao diện Admin tách biệt về chức năng/điều hướng, quản lý tài khoản và phân quyền; hỗ trợ tra cứu, tìm kiếm nâng cao, lọc và sắp xếp theo yêu cầu chấm.
- Chuẩn bị dữ liệu mẫu, tài khoản theo vai trò và các giao dịch demo; bàn giao source code, script SQL, báo cáo và readme thông tin nhóm.
- Lập kế hoạch công việc và ghi nhận đóng góp thành viên theo biểu mẫu chấm; phần kế hoạch trong báo cáo được yêu cầu thể hiện 15 tuần.

Ưu tiên hoàn thiện các luồng trên và khả năng truy vết. Không mở rộng sang một hệ thống ERP đầy đủ. Công nghệ, schema, endpoint và phân công triển khai sẽ được xác định trong tài liệu tiếp theo.

## 11. Nguồn và cách xử lý khác biệt

1. Quyết định của người khởi xướng trong cuộc trao đổi ngày 22/10/2026: mục tiêu truy vết; ranh giới đơn hàng; vai trò; thời điểm tạo lệnh; BOM hai cấp; chờ bổ sung vật tư; phê duyệt hoàn thành; điều chỉnh phiếu nhập NVL; ticket độc lập với phiếu điều chỉnh mới.
2. [Biên bản chấm đồ án](https://drive.google.com/file/d/1iePUtVWO3AgFa8VFVj9H-y_FkqgqBLt4/view).
3. [User-flow tạo phiếu nhập kho](https://drive.google.com/file/d/196HsOmEUyZ3HpRqHUl1i9RB2JoFmxBNb/view).
4. [User-flow tạo yêu cầu sản xuất](https://drive.google.com/file/d/1QU7haR5iD8ff_edQNhrFKcnbpAjQudTV/view).
5. [SRS_v4.txt](https://drive.google.com/file/d/1GTqAuq1JTyMBt-Xu6BXorSJAFDhg87zn/view) làm nền cho các quy tắc không bị thay đổi trong cuộc trao đổi.
6. Hình BOM do người khởi xướng đính kèm: “xBike MRP – 5 BOM riêng biệt”.

Khi có khác biệt về nghiệp vụ, ưu tiên các quyết định mới đã chốt với người khởi xướng. Cụ thể: nhánh thiếu vật tư giữ yêu cầu thay vì kết thúc; quản lý tạo lệnh ngay khi xác định cần sản xuất, không phải đợi đủ vật tư; ticket không liên kết với phiếu điều chỉnh mới. Các tài liệu SRS, user-flow, data model và API contract cũ cần được đối chiếu, cập nhật riêng; việc tạo intent này không đồng nghĩa các tài liệu đó đã được sửa.
