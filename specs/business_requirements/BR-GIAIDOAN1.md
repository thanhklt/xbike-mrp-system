# BR-001: xBike MRP — Đăng nhập và phân quyền theo vai trò

## Goal
Mỗi người dùng chỉ thấy và chỉ làm được đúng phần việc của vai trò mình (Quản trị viên, Quản lý kho, Nhân viên), để không ai thao tác nhầm hoặc vượt quyền trên dữ liệu kho.

## Success Metrics
- unauthorized_action_success = 0 (đo qua kịch bản nghiệm thu: mỗi vai trò thử mọi chức năng không thuộc quyền của mình)
- locked_account_access = 0 (tài khoản bị khóa không thao tác được, kể cả khi đang đăng nhập)

## In Scope (Giai đoạn 1)
- Đăng nhập bằng tên đăng nhập và mật khẩu
- Đăng xuất; sau khi đăng xuất phải đăng nhập lại mới thao tác được
- Chỉ Quản trị viên đổi được mật khẩu, trong chức năng quản trị tài khoản (xem BR-002)
- Ba vai trò: Quản trị viên, Quản lý kho, Nhân viên
- Giao diện Quản trị viên tách riêng với giao diện nghiệp vụ; người không có quyền gõ thẳng đường dẫn quản trị vẫn bị chặn
- Tài khoản bị khóa mất quyền truy cập ngay

## Out of Scope
- Quên mật khẩu, lấy lại mật khẩu qua email
- Quản lý kho, Nhân viên tự đổi mật khẩu
- Đăng nhập một lần (SSO)
- Phân quyền chi tiết theo từng chức năng ngoài 3 vai trò
- Ứng dụng mobile

---

# BR-002: xBike MRP — Quản trị tài khoản người dùng

## Goal
Quản trị viên tự quản lý toàn bộ tài khoản (cấp mới, khóa, đổi vai trò, đổi mật khẩu) mà không cần can thiệp kỹ thuật, và mọi thay đổi đều truy được ai làm, vì sao.

## Success Metrics
- account_change_traceability = 100% (mỗi lần thêm, khóa, mở khóa, đổi vai trò đều có người thực hiện, thời điểm, lý do; mỗi lần đổi mật khẩu có người thực hiện, thời điểm; đo qua lịch sử thao tác)
- active_admin_count >= 1 (luôn còn ít nhất một Quản trị viên đang hoạt động)

## In Scope (Giai đoạn 1)
- Xem, tìm kiếm, lọc, sắp xếp danh sách tài khoản
- Thêm tài khoản với bất kỳ vai trò nào: Quản trị viên, Quản lý kho, Nhân viên
- Khóa và mở khóa tài khoản, bắt buộc ghi lý do (khóa thay cho xóa)
- Đổi vai trò giữa cả ba vai trò: Quản trị viên, Quản lý kho, Nhân viên; bắt buộc ghi lý do
- Vai trò mới có hiệu lực ngay: mọi phiên đang đăng nhập của tài khoản đó kết thúc, người dùng phải đăng nhập lại
- Không đổi vai trò của Nhân viên đang được giao yêu cầu sản xuất chưa kết thúc (Nháp, Đã gửi, Chờ bổ sung linh kiện, Đang thực hiện)
- Đổi mật khẩu cho bất kỳ tài khoản nào, kể cả của chính mình; chỉ Quản trị viên làm được; không cần nhập mật khẩu hiện tại
- Mật khẩu tối thiểu 6 ký tự
- Khi mật khẩu bị đổi, mọi phiên đang đăng nhập của tài khoản đó kết thúc ngay, kể cả khi Quản trị viên đổi mật khẩu của chính mình
- Có thể có nhiều Quản trị viên; Quản trị viên đầu tiên được tạo sẵn khi cài đặt
- Không khóa hoặc hạ quyền được Quản trị viên đang hoạt động cuối cùng
- Khóa tài khoản không làm mất các yêu cầu sản xuất đang giao cho người đó

## Out of Scope
- Xóa hẳn tài khoản
- Quản lý kho, Nhân viên tự đổi mật khẩu
- Quản trị viên làm nghiệp vụ kho (nhập, xuất, duyệt)

---

# BR-003: xBike MRP — Tra cứu dữ liệu cho Quản trị viên

## Goal
Quản trị viên tra cứu nhanh thông tin sản phẩm và nhà cung cấp để hỗ trợ người dùng và rà soát dữ liệu, nhưng không làm thay đổi được dữ liệu nghiệp vụ.

## Success Metrics
- admin_data_modification = 0 (Quản trị viên không thêm, sửa, ngừng được mặt hàng hay nhà cung cấp; đo qua kịch bản nghiệm thu)
- advanced_search_correctness = 100% (tìm kiếm kết hợp nhiều tiêu chí trả đúng tập kết quả trên bộ dữ liệu mẫu)

## In Scope (Giai đoạn 1)
- Xem danh sách và chi tiết mặt hàng (thành phẩm, linh kiện) và nhà cung cấp, chỉ đọc
- Tìm kiếm theo từ khóa, tìm kiếm nâng cao kết hợp nhiều tiêu chí, lọc, sắp xếp, phân trang
- Tiêu chí cho mặt hàng: mã/tên, loại, đang dùng hay đã ngừng (chỉ áp dụng cho thành phẩm), đơn vị tính, màu sắc, khoảng đơn giá
- Tiêu chí cho nhà cung cấp: mã/tên, tỉnh, phường

## Out of Scope
- Thêm, sửa, ngừng mặt hàng hoặc nhà cung cấp
- Xem công thức sản phẩm, phiếu nhập, phiếu xuất, yêu cầu sản xuất

---

# BR-004: xBike MRP — Danh mục mặt hàng và nhà cung cấp

## Goal
Quản lý kho có một danh mục mặt hàng và nhà cung cấp chính xác, làm nền cho mọi nghiệp vụ nhập, xuất và sản xuất.

## Success Metrics
- duplicate_item_code = 0
- inactive_item_used_in_new_document = 0 (thành phẩm đã ngừng không xuất hiện trong chứng từ mới; ngoại lệ: chứng từ của yêu cầu sản xuất đã gửi trước khi thành phẩm bị ngừng)

## In Scope (Giai đoạn 1)
- Hai loại mặt hàng:
  - Thành phẩm: Mountain Pro, City Ride, Speed Sport, Kids Fun
  - Linh kiện: Khung xe, Phuộc xe, Cụm bánh xe, Lốp xe, Xích xe, Bàn đạp, Dây phanh, Yên xe, Đĩa xích, Bộ ốc vít
- Cụm bánh xe là linh kiện mua về, nhập kho như mọi linh kiện khác
- Quản lý kho tạo, sửa mặt hàng; ngừng và dùng lại thành phẩm; Nhân viên chỉ xem
- Chỉ thành phẩm có trạng thái đang dùng / đã ngừng (ngừng sản xuất); linh kiện không có trạng thái ngừng, chỉ được nhập
- Quản trị viên, Quản lý kho, Nhân viên đều tra cứu và tìm kiếm nâng cao mặt hàng theo các tiêu chí ở BR-003
- Thông tin mặt hàng: mã, tên, loại, đơn vị tính, đơn giá (VND), màu sắc, mô tả
- Tạo thành phẩm phải tạo kèm công thức của nó (xem BR-005); linh kiện không cần công thức
- Mỗi mặt hàng hiển thị ba con số: tồn thực tế, phần đang giữ cho yêu cầu sản xuất, phần còn dùng được
- Số tồn chỉ thay đổi qua chứng từ đã ghi nhận vào kho, không ai sửa tay
- Không đổi loại hoặc đơn vị tính của mặt hàng đã được dùng trong công thức hay chứng từ
- Quản lý kho tạo và xem nhà cung cấp: mã, tên; điện thoại và địa chỉ không bắt buộc
- Địa chỉ nhà cung cấp gồm tỉnh, phường (chọn từ danh mục đơn vị hành chính; phường phải thuộc tỉnh) và địa chỉ chi tiết
- Nhân viên không xem nhà cung cấp

## Out of Scope
- Bán thành phẩm (giai đoạn 2)
- Vành bánh xe, moay-ơ, nan hoa (giai đoạn 2)
- Tách loại "nguyên vật liệu" riêng khỏi linh kiện (giai đoạn 2)
- Sửa, xóa nhà cung cấp
- Xóa hẳn mặt hàng
- Cảnh báo tồn kho thấp
- Nhiều kho, vị trí lưu trong kho

---

# BR-005: xBike MRP — Công thức sản phẩm (BOM) một cấp

## Goal
Mỗi mẫu xe có công thức linh kiện rõ ràng để hệ thống tự tính lượng linh kiện cần cho một lần sản xuất, và việc sửa công thức không làm sai các yêu cầu đang làm dở.

## Success Metrics
- material_calc_error = 0 (nhu cầu linh kiện luôn bằng định mức × số xe cần sản xuất trên mọi kịch bản nghiệm thu)
- in_progress_request_changed_by_bom_update = 0

## In Scope (Giai đoạn 1)
- Mỗi công thức dành cho một thành phẩm; thành phần chỉ là linh kiện; định mức là số nguyên dương cho 1 xe; không lặp thành phần
- Công thức được tạo cùng lúc với thành phẩm; mỗi thành phẩm ứng với một công thức (có nhiều phiên bản) và có tối đa một phiên bản đang dùng
- Sửa công thức bằng cách tạo phiên bản mới; phiên bản mới thay phiên bản cũ ngay
- Dùng lại một phiên bản cũ
- Thành phẩm đang dùng khi và chỉ khi có phiên bản công thức đang dùng:
  - Ngừng công thức thì thành phẩm ngừng theo; ngừng thành phẩm thì công thức ngừng theo
  - Dùng lại một phiên bản hoặc tạo phiên bản mới cho công thức đã ngừng thì thành phẩm tự chuyển về đang dùng
  - Dùng lại thành phẩm thì phiên bản đang dùng gần nhất (ngay trước khi ngừng) được dùng lại
- Thành phẩm đã ngừng không lập, không gửi được yêu cầu sản xuất mới; yêu cầu đã gửi vẫn thực hiện tiếp đến khi kết thúc
- Công thức được chốt vào yêu cầu sản xuất khi Quản lý kho gửi yêu cầu; yêu cầu đã gửi giữ nguyên công thức đó
- Quản lý kho quản lý công thức; Nhân viên chỉ xem

## Out of Scope
- Công thức nhiều cấp, ví dụ cụm bánh xe làm từ vành, moay-ơ, nan hoa (giai đoạn 2)
- Sản xuất bán thành phẩm (giai đoạn 2)

---

# BR-006: xBike MRP — Nhập kho linh kiện

## Goal
Quản lý kho nhập linh kiện từ nhà cung cấp; tồn kho chỉ tăng khi phiếu được xác nhận hoàn tất, và chỉ tăng đúng một lần.

## Success Metrics
- stock_increase_before_completion = 0 (lưu nháp không làm tăng tồn)
- duplicate_receipt_posting = 0 (bấm hoàn tất nhiều lần vẫn chỉ cộng một lần)

## In Scope (Giai đoạn 1)
- Quản lý kho lập phiếu nháp gồm: nhà cung cấp, ngày nhập, ghi chú, các dòng linh kiện kèm số lượng và đơn giá nhập thực tế
- Chỉ nhập linh kiện; mỗi linh kiện xuất hiện một lần trong phiếu
- Sửa, xóa phiếu khi còn nháp
- Hoàn tất nhập kho sau khi xác nhận thì cộng tồn linh kiện
- Phiếu nhập độc lập, không gắn với yêu cầu sản xuất nào; hoàn tất phiếu nhập không tự làm thay đổi yêu cầu sản xuất
- Phiếu đã hoàn tất không sửa, không xóa

## Out of Scope
- Phiếu điều chỉnh số lượng sau khi hoàn tất (giáo viên không yêu cầu)
- Trả hàng cho nhà cung cấp
- Nhập thành phẩm từ bên ngoài
- Bước duyệt riêng cho phiếu nhập
- Gắn phiếu nhập với yêu cầu sản xuất
- Kiểm kê kho

---

# BR-007: xBike MRP — Tạo và giao yêu cầu sản xuất

## Goal
Quản lý kho giao việc đáp ứng một lượng thành phẩm cho đúng một nhân viên, kèm hạn rõ ràng, để nhân viên tự kiểm tra và xử lý đến cuối.

## Success Metrics
- request_sent_without_assignee_or_deadline = 0
- request_status_visibility = 100% (Quản lý kho xem được trạng thái của mọi yêu cầu)

## In Scope (Giai đoạn 1)
- Yêu cầu gồm: thành phẩm, số lượng, hạn hoàn thành, nhân viên được giao
- Yêu cầu sản xuất kiêm luôn lệnh sản xuất; không có lệnh sản xuất riêng
- Quản lý kho sửa, xóa yêu cầu khi còn nháp
- Chỉ lập yêu cầu cho thành phẩm đang dùng
- Gửi yêu cầu cần xác nhận; chỉ gửi được khi đã có hạn hoàn thành, nhân viên được giao đang hoạt động và thành phẩm đang dùng
- Gửi chuyển việc cho nhân viên và chốt phiên bản công thức đang dùng vào yêu cầu (xem BR-005); chưa tính nhu cầu, chưa giữ hàng, chưa đổi tồn
- Hạn hoàn thành chỉ dùng để theo dõi và sắp xếp
- Trạng thái: Nháp → Đã gửi → Chờ bổ sung linh kiện hoặc Đang thực hiện → Hoàn thành; hoặc Đã hủy (xem BR-013)
- Quản lý kho xem được mọi yêu cầu

## Out of Scope
- Quản lý kho tính thử nhu cầu trước khi gửi
- Đổi nhân viên, số lượng hoặc thành phẩm sau khi đã gửi
- Cảnh báo quá hạn
- Giao một yêu cầu cho nhiều nhân viên
- Đơn hàng khách, bán hàng

---

# BR-008: xBike MRP — Kiểm tra yêu cầu sản xuất và giữ hàng

## Goal
Nhân viên biết ngay yêu cầu của mình làm được tới đâu: dùng bao nhiêu thành phẩm có sẵn, cần sản xuất bao nhiêu, thiếu linh kiện gì. Phần hàng đã tính cho yêu cầu này không bị yêu cầu khác lấy mất.

## Success Metrics
- request_blocked_by_taken_stock = 0 (yêu cầu đã kiểm tra đủ không bao giờ bị từ chối xuất vì thiếu hàng)
- double_counted_stock = 0 (không có hai yêu cầu cùng được tính "đủ" trên cùng một lượng hàng)
- shortage_report_completeness = 100% (mỗi dòng thiếu có mã, tên, đơn vị tính, số cần, số còn dùng được, số thiếu)

## In Scope (Giai đoạn 1)
- Nhân viên chỉ thấy yêu cầu giao cho mình; mặc định yêu cầu cũ nhất lên đầu (chỉ là thứ tự hiển thị, không bắt buộc làm theo)
- "Còn dùng được" = tồn thực tế trừ phần đang giữ cho các yêu cầu khác
- Kiểm tra lần đầu:
  - Dùng thành phẩm còn dùng được trước; số cần sản xuất = số yêu cầu − thành phẩm dùng được (không âm)
  - Tính nhu cầu linh kiện theo công thức đã chốt lúc gửi (BR-007)
  - Chốt lại: số cần sản xuất, nhu cầu linh kiện, phần thành phẩm giữ cho yêu cầu
  - Đủ thành phẩm: Đang thực hiện, đi thẳng tới xuất thành phẩm
  - Đủ toàn bộ linh kiện: giữ toàn bộ linh kiện cho yêu cầu, Đang thực hiện
  - Thiếu linh kiện: không giữ linh kiện nào, chuyển Chờ bổ sung linh kiện. Đây chính là cách báo Quản lý kho cần nhập, không lập phiếu đề nghị riêng
- Kiểm tra lại (yêu cầu đang Chờ bổ sung): so nhu cầu đã chốt với hàng còn dùng được; đủ thì giữ linh kiện và chuyển Đang thực hiện
- Hàng được giữ cho đến khi xuất thật hoặc yêu cầu bị hủy
- Thao tác kiểm tra cần xác nhận vì có giữ hàng
- Kịch bản nghiệm thu:
  - Tồn 3 xe, yêu cầu A cần 10 xe: A sản xuất 7. Sau đó yêu cầu B cần 3 xe: B sản xuất 3
  - Tồn 10 khung, A và B mỗi yêu cầu cần 10 khung: A kiểm tra trước, giữ 10 khung; B chuyển Chờ bổ sung, thiếu 10

## Out of Scope
- Giữ một phần linh kiện khi chưa đủ toàn bộ (giai đoạn 2)
- Tự kiểm tra lại khi Quản lý kho nhập hàng (giai đoạn 2)
- Tính lại theo công thức mới sau khi đã chốt
- Bắt buộc xử lý theo thứ tự tạo
- Phiếu đề nghị nhập linh kiện

---

# BR-009: xBike MRP — Theo dõi nhu cầu bổ sung linh kiện

## Goal
Quản lý kho nhìn một chỗ là biết phải nhập bao nhiêu mỗi loại linh kiện để gỡ toàn bộ các yêu cầu đang chờ.

## Success Metrics
- shortage_summary_accuracy = 100% (tổng thiếu khớp với tính tay trên kịch bản nghiệm thu)

## In Scope (Giai đoạn 1)
- Danh sách yêu cầu Chờ bổ sung linh kiện, cũ nhất lên đầu, kèm linh kiện thiếu của từng yêu cầu
- Tổng hợp theo linh kiện: tổng cần, còn dùng được, thiếu
- Chỉ để xem; Quản lý kho tự lập phiếu nhập theo BR-006
- Kịch bản nghiệm thu: hai yêu cầu mỗi yêu cầu thiếu 10 khung, khung còn dùng được là 0 → tổng thiếu 20

## Out of Scope
- Thông báo đẩy, email, realtime
- Tự tạo phiếu nhập từ danh sách thiếu
- Đề xuất nhà cung cấp

---

# BR-010: xBike MRP — Xuất linh kiện cho sản xuất

## Goal
Linh kiện chỉ rời kho khi Quản lý kho duyệt, và xuất đúng đủ cho một yêu cầu, để tồn kho khớp với thực tế ở xưởng.

## Success Metrics
- negative_stock = 0
- duplicate_issue_posting = 0
- issue_quantity_mismatch = 0 (lượng xuất luôn bằng nhu cầu đã chốt)

## In Scope (Giai đoạn 1)
- Nhân viên được giao lập phiếu xuất khi yêu cầu Đang thực hiện và cần sản xuất
- Mỗi yêu cầu một phiếu, xuất đủ toàn bộ nhu cầu; nội dung phiếu lấy đúng nhu cầu đã chốt, nhân viên không sửa
- Gửi phiếu cần xác nhận, chưa trừ tồn
- Quản lý kho duyệt (có xác nhận): trừ tồn, ghi giá xuất theo đơn giá mặt hàng tại lúc duyệt, kết thúc giữ linh kiện
- Quản lý kho từ chối phải ghi lý do; tồn không đổi, linh kiện vẫn được giữ; nhân viên đưa phiếu về nháp rồi gửi lại
- Quản lý kho không lập phiếu xuất; Nhân viên không duyệt
- Quản lý kho có màn hình danh sách phiếu xuất riêng, gồm cả phiếu xuất linh kiện và phiếu xuất thành phẩm, mở từ đó để duyệt hoặc từ chối

## Out of Scope
- Xuất nhiều đợt hoặc từng phần
- Trả linh kiện về kho (giai đoạn 2)
- Tính giá vốn theo FIFO hoặc bình quân

---

# BR-011: xBike MRP — Sản xuất và ghi nhận hoàn thành

## Goal
Thành phẩm chỉ vào kho khi Quản lý kho xác nhận sản xuất xong, đúng số lượng đã lên kế hoạch.

## Success Metrics
- finished_goods_added_without_approval = 0
- components_deducted_twice = 0

## In Scope (Giai đoạn 1)
- Nhân viên bấm bắt đầu sản xuất sau khi phiếu xuất linh kiện được duyệt; hệ thống ghi thời điểm bắt đầu; tồn không đổi
- Nhân viên lập chứng từ hoàn thành sản xuất, mỗi yêu cầu một chứng từ
  - Số lượng hoàn thành bằng đúng số cần sản xuất, nhân viên không sửa
  - Nhân viên nhập thời điểm hoàn thành: không trước lúc bắt đầu, không ở tương lai
- Gửi chứng từ cần xác nhận, chưa cộng tồn
- Quản lý kho duyệt: cộng thành phẩm vào kho, số xe vừa làm được giữ cho chính yêu cầu đó; không trừ linh kiện lần nữa
- Quản lý kho từ chối phải ghi lý do; không cộng tồn; linh kiện đã xuất không được hoàn; nhân viên đưa về nháp, sửa, gửi lại
- Quản lý kho có màn hình danh sách chứng từ hoàn thành sản xuất riêng, lọc theo sản phẩm, nhân viên, khoảng thời gian, trạng thái, mở từ đó để duyệt hoặc từ chối

## Out of Scope
- Hoàn thành nhiều đợt
- Hoàn thành khác số kế hoạch; ghi nhận hao hụt, phế phẩm
- Theo dõi tiến độ chi tiết trong xưởng

---

# BR-012: xBike MRP — Xuất thành phẩm và hoàn thành yêu cầu

## Goal
Yêu cầu sản xuất chỉ được đóng khi toàn bộ số xe yêu cầu đã xuất kho có duyệt.

## Success Metrics
- completed_request_with_unissued_goods = 0
- request_stuck_waiting_finished_goods = 0

## In Scope (Giai đoạn 1)
- Nhân viên lập phiếu xuất thành phẩm khi: yêu cầu không cần sản xuất (đủ thành phẩm từ đầu), hoặc chứng từ hoàn thành đã được duyệt
- Mỗi yêu cầu một phiếu, đúng số lượng yêu cầu, nhân viên không sửa
- Gửi phiếu cần xác nhận, chưa trừ tồn
- Quản lý kho duyệt: trừ thành phẩm, ghi giá xuất, kết thúc giữ thành phẩm, yêu cầu chuyển Hoàn thành
- Từ chối và gửi lại như BR-010

## Out of Scope
- Xuất thành phẩm từng phần
- Giao hàng, bán hàng, hóa đơn

---

# BR-013: xBike MRP — Hủy yêu cầu sản xuất

## Goal
Quản lý kho dừng được một yêu cầu không còn cần, trước khi hàng rời kho, để trả phần hàng đang giữ cho các yêu cầu khác.

## Success Metrics
- stock_released_after_cancel = 100% (sau khi hủy, hàng còn dùng được tăng đúng bằng phần đã giữ)
- cancel_after_goods_issued = 0

## In Scope (Giai đoạn 1)
- Chỉ Quản lý kho được hủy; bắt buộc ghi lý do và xác nhận
- Chỉ hủy được khi yêu cầu chưa có phiếu xuất nào (linh kiện hay thành phẩm) được duyệt
- Khi hủy:
  - Trả lại toàn bộ hàng đang giữ
  - Phiếu xuất còn nháp bị bỏ
  - Phiếu xuất đang chờ duyệt bị từ chối với lý do "Yêu cầu đã hủy"
  - Tồn thực tế không đổi
- Không thao tác thêm trên yêu cầu đã hủy
- Yêu cầu còn nháp thì xóa, không cần hủy

## Out of Scope
- Hủy sau khi đã xuất linh kiện; trả linh kiện về kho (giai đoạn 2)
- Nhân viên tự hủy yêu cầu

---

# BR-014: xBike MRP — Báo cáo và tra cứu kho

## Goal
Quản lý kho nắm được biến động nhập, xuất, tồn theo kỳ và tra lại được chứng từ sản xuất, hoàn toàn dựa trên số liệu đã ghi nhận vào kho.

## Success Metrics
- closing_stock_mismatch = 0 (tồn cuối kỳ khớp tồn thực tế)
- unposted_document_in_report = 0 (phiếu nháp, chờ duyệt, bị từ chối không được tính)

## In Scope (Giai đoạn 1)
- Báo cáo nhập-xuất-tồn theo tháng, quý, năm: tồn đầu kỳ, nhập, xuất, tồn cuối kỳ; lọc theo mặt hàng và loại
- Chỉ tính chứng từ đã ghi nhận: phiếu nhập đã hoàn tất, phiếu xuất đã duyệt, chứng từ hoàn thành đã duyệt
- Kỳ báo cáo tính theo giờ Việt Nam
- Tra cứu chứng từ hoàn thành sản xuất theo sản phẩm, nhân viên, khoảng thời gian, trạng thái
- Tra cứu lịch sử biến động kho theo mặt hàng, loại nghiệp vụ, nhân viên, khoảng thời gian

## Out of Scope
- Xuất Excel, PDF
- Dashboard, biểu đồ
- Báo cáo giá trị tiền
- Thống kê chứng từ theo trạng thái
- Cột điều chỉnh tồn

---

# BR-015: xBike MRP — Lưu nháp và xác nhận thao tác

## Goal
Không thao tác nào làm thay đổi kho mà người dùng chưa nhìn thấy và xác nhận rõ ràng.

## Success Metrics
- stock_change_without_confirmation = 0
- duplicate_posting = 0 (bấm nhiều lần, mạng chập chờn, hai người cùng duyệt)

## In Scope (Giai đoạn 1)
- Áp dụng cho: phiếu nhập, yêu cầu sản xuất, phiếu xuất linh kiện, chứng từ hoàn thành sản xuất, phiếu xuất thành phẩm
- Mọi chứng từ bắt đầu ở nháp; lưu nháp không gửi, không duyệt, không đổi tồn
- Mỗi lần gửi, duyệt, hoàn tất nhập, kiểm tra có giữ hàng, hủy yêu cầu đều mở hộp xác nhận riêng
  - Hộp xác nhận hiển thị: chứng từ, mặt hàng, số lượng, đơn vị tính, tác động tới kho (ghi rõ khi thao tác chưa làm đổi tồn)
  - Đóng hộp xác nhận thì không có gì thay đổi
- Không sửa chứng từ đang chờ duyệt hoặc đã ghi nhận; chứng từ bị từ chối phải đưa về nháp mới sửa được
- Nếu chứng từ bị người khác thay đổi trong lúc đang xác nhận, hệ thống báo và yêu cầu xem lại
- Tồn kho không bao giờ âm; mỗi chứng từ chỉ ghi nhận vào kho một lần
- Tiền tính bằng VND

## Out of Scope
- Hoàn tác chứng từ đã ghi nhận
- Phê duyệt nhiều cấp

---

# BR-016: xBike MRP — Lịch sử thao tác

## Goal
Mọi thao tác quan trọng đều truy được ai làm, lúc nào, thay đổi gì và vì sao.

## Success Metrics
- critical_action_traceability = 100%
- audit_record_modified = 0 (không bản ghi lịch sử nào bị sửa hoặc xóa)

## In Scope (Giai đoạn 1)
- Ghi lịch sử cho:
  - Đăng nhập
  - Tạo, sửa, xóa nháp
  - Gửi, kiểm tra, duyệt, từ chối, đưa về nháp, hoàn tất nhập, bắt đầu sản xuất, hủy yêu cầu
  - Thao tác tài khoản, kể cả đổi vai trò và đổi mật khẩu
  - Thao tác dữ liệu nền: tạo, sửa mặt hàng; ngừng, dùng lại thành phẩm; tạo nhà cung cấp; tạo công thức, tạo phiên bản mới, dùng lại, ngừng công thức. Thao tác sửa ghi giá trị trước và sau
- Mỗi bản ghi có: người thực hiện, thời điểm, đối tượng, trạng thái trước và sau, lý do
- Khi yêu cầu chuyển Chờ bổ sung linh kiện, lưu lại danh sách thiếu tại thời điểm đó
- Không ai sửa hay xóa lịch sử; không lưu mật khẩu
- Quản lý kho và Quản trị viên xem, lọc theo đối tượng, người, thao tác, khoảng thời gian

## Out of Scope
- Nhân viên xem lịch sử thao tác
- Xuất lịch sử ra file
