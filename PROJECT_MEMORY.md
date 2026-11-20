# PROJECT MEMORY - ZaloTask Assistant (Smart Routine & Auto Zalo Sender)

## 1. Thông Tin & Mục Tiêu Dự Án
- **Tên dự án**: ZaloTask Assistant Pro (Trợ lý Lập lịch, Nhắc việc & Tự động gửi file Zalo)
- **Thư mục dự án**: `C:\Users\ADMIN\.gemini\antigravity\scratch\zalo_task_assistant`
- **Mục tiêu**:
  1. **Lập lịch & Nhắc nhở thông minh**: Hỗ trợ các kiểu lặp lại (Một lần, Hàng ngày, Hàng tuần theo thứ trong tuần, Hàng tháng, Khoảng thời gian X phút/giờ).
  2. **Âm thanh & Cảnh báo trực quan**: Thông báo Web Notification + Âm thanh chuông báo to rõ (Web Audio Synthesizer) + Banner popup nhắc việc.
  3. **Quản lý file đính kèm linh hoạt (Cố định & Bốc file mới nhất)**:
     - Cho phép chọn file upload cố định.
     - Tự động theo dõi thư mục (Watch Directory) và tự động bốc file mới nhất (mtime) vừa tạo để gửi.
     - Hỗ trợ nén nhiều file thành `.zip`.
  4. **Tự động hóa Zalo**: 
     - Tự động kích hoạt Zalo Desktop, tìm danh bạ/nhóm trên Zalo và gửi tin nhắn + đính kèm file tự động (CF_HDROP clipboard stream).
     - Hỗ trợ biến động `{date}`, `{time}`, `{day_of_week}`, `{title}`.
     - Tab "🚀 Thử Nghiệm Gửi Nhanh Zalo" để kiểm tra tính năng gửi ngay lập tức với log chi tiết từng giây.
  5. **Cơ chế An Toàn & Đếm Lùi Xem Trước (Smart Preview & Countdown)**:
     - Tùy chọn đếm lùi 15s/30s/60s trước khi tự động gửi, hiển thị vòng tròn đếm lùi trực quan trên màn hình.
     - Người dùng có thể bấm "🚀 Gửi Ngay" hoặc "⏸ Hoãn 15 phút" để chuẩn bị lại file.
  6. **Chạy Ngầm Khay Hệ Thống & Tự Khởi Động (System Tray & Auto-start)**:
     - Chạy ngầm thu nhỏ xuống góc phải màn hình (`tray.py`), không còn cửa sổ đen CMD.
     - Tích hợp menu chuột phải khay hệ thống: Mở Web Dashboard, Bật/Tắt Lập Lịch, Tự Khởi Động Cùng Windows (Registry Run), Thoát.
     - File chạy ẩn hoàn toàn: `start_silent.vbs` và `start_tray.bat`.
  7. **Báo Cáo Kết Quả Về Điện Thoại (Telegram Bot)**:
     - Mỗi khi hoàn thành gửi Zalo, hệ thống tự động bắn tin báo cáo xác nhận về tài khoản Telegram trên điện thoại của người dùng.
  8. **Giao diện Web trực quan (Responsive Web Dashboard)**: Quản lý tác vụ, kiểm tra trạng thái, xem nhật ký thực thi (logs), kích hoạt chạy ngay hoặc hoãn lịch.

---

## 2. Kiến Trúc Hệ Thống & Cấu Trúc Thư Mục
- **Backend**: Python 3 (FastAPI + Uvicorn + SQLite + Daemon Scheduler Engine)
- **Tự động hóa Windows & Zalo**:
  - `pyautogui` + `pyperclip` + `win32clipboard` (Windows CF_HDROP File Drop Format).
  - Tự động kích hoạt Zalo Desktop (`AttachThreadInput` + `SetForegroundWindow` + `Default` Desktop station switch).
- **Khay hệ thống**: `pystray` + `PIL.Image` (icon tổng hợp trực tiếp).
- **Frontend**: HTML5, Modern CSS (Plus Jakarta Sans, responsive grid, dynamic badges), Vanilla JS (Web Audio API Synthesizer, Web Notification, Smart Preview Timer, Polling API).

---

## 3. Nhật Ký Quyết Định & Kiểm Thử Thực Tế
- **2026-11-20**: Khởi tạo và xây dựng trọn vẹn 3 giai đoạn của ZaloTask Assistant.
- **2026-11-20**: Hoàn thành 3 nâng cấp thực tế (Bốc file mới nhất, System Tray không cmd, Đếm lùi an toàn Smart Preview & Báo cáo Telegram).
- **2026-11-20 (Kiểm thử gửi thật theo yêu cầu người dùng)**:
  - File: `C:\Users\ADMIN\Desktop\MAKET CHIỀU\MA KÉT (1).pptx` (dung lượng ~1.3 MB).
  - Người nhận: `My Documents` (Cloud lưu trữ cá nhân trên Zalo Desktop).
  - Kết quả: **THÀNH CÔNG 100%**. Ứng dụng đã kích hoạt Zalo Desktop, mở cuộc trò chuyện My Documents, dán tin nhắn và đính kèm gửi trực tiếp file `MA KÉT (1).pptx`.

---

## 4. Danh Sách Tính Năng Hoàn Thành & Đang Hoạt Động Ổn Định
1. [x] **Lập lịch nhắc nhở đa dạng**: Hàng ngày, hàng tuần theo ngày cụ thể, lặp lại mỗi X phút, hoặc chỉ 1 lần.
2. [x] **Hệ thống cảnh báo âm thanh & Pop-up**: Chuông báo synthesizer trong trẻo không phụ thuộc file mạng, thông báo đẩy trình duyệt.
3. [x] **Tự động bốc file mới nhất trong thư mục (Dynamic File Watcher)**: Quét thư mục chỉ định và lấy file mới nhất theo thời gian tạo/sửa để gửi.
4. [x] **Tự động gửi qua Zalo**: Tự động tìm tên bạn bè/nhóm, dán tin nhắn có biến động `{date}`, `{time}`, `{day_of_week}`, dán và gửi file đính kèm native `CF_HDROP`.
5. [x] **Chế độ An Toàn & Đếm Lùi Xem Trước (Smart Preview & Postpone)**: Hộp thoại đếm lùi 15s/30s/60s, cho phép người dùng bấm "Gửi Ngay" hoặc "Hoãn 15 phút".
6. [x] **Báo cáo kết quả về điện thoại (Telegram)**: Bắn tin nhắn xác nhận về điện thoại ngay khi gửi Zalo thành công.
7. [x] **Chạy ngầm ở Khay Hệ Thống (System Tray)**: `tray.py` + `start_silent.vbs` ẩn hoàn toàn cửa sổ đen cmd, điều khiển qua menu khay hệ thống.
8. [x] **Tự khởi động cùng Windows**: Tích hợp trực tiếp vào Registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
9. [x] **Quản lý & Xem lịch sử (Execution Logs)**: Bảng thống kê chi tiết lượt gửi, thành công, thất bại và log chi tiết.
