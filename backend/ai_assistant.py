import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from . import database

def process_chat_message(user_message: str) -> Dict[str, Any]:
    """
    Xử lý câu lệnh / câu hỏi bằng ngôn ngữ tự nhiên tiếng Việt của người dùng.
    Hỗ trợ:
    1. Lên lịch nhắc việc tự động qua tin nhắn
    2. Tra cứu danh sách công việc hôm nay / sắp tới
    3. Trả lời hướng dẫn sử dụng, cài đặt trên điện thoại
    4. Trò chuyện và giải đáp thắc mắc
    """
    msg = (user_message or "").strip()
    msg_lower = msg.lower()

    if not msg:
        return {
            "reply": "Xin chào! Tôi là Trợ lý AI của bạn. Bạn có thể yêu cầu tôi lên lịch nhắc việc (ví dụ: 'Nhắc tôi nộp báo cáo lúc 16:30'), kiểm tra danh sách việc hôm nay, hoặc hướng dẫn sử dụng.",
            "action": None
        }

    # 1. Kiểm tra yêu cầu xem danh sách công việc
    if any(k in msg_lower for k in ["danh sách", "có việc gì", "lịch hôm nay", "việc cần làm", "nhắc nhở nào", "công việc"]):
        tasks = database.list_tasks()
        if not tasks:
            return {
                "reply": "📅 Hiện tại bạn chưa có lịch nhắc nhở nào trong hệ thống. Bạn có thể nhắn tôi tạo mới, ví dụ: <i>'Nhắc tôi nộp báo cáo chiều lúc 16:30'</i>.",
                "action": "list_tasks",
                "tasks": []
            }
        
        reply = f"📋 <b>Bạn đang có {len(tasks)} tác vụ trong hệ thống:</b><br><ul style='margin: 8px 0; padding-left: 20px;'>"
        for t in tasks:
            status_badge = "🟢 Đang bật" if t.get("is_active") else "⚪ Đã tắt"
            st = t.get("schedule_type", "once")
            rec_text = {
                "once": "Chỉ 1 lần",
                "daily": "Hàng ngày",
                "weekly": "Hàng tuần",
                "interval": "Lặp lại định kỳ"
            }.get(st, st)
            time_val = t.get("schedule_time", "--:--")
            zalo_info = f" • Gửi Zalo: <b>{t.get('zalo_recipient')}</b>" if t.get("zalo_recipient") else ""
            reply += f"<li><b>{t.get('title')}</b> - ⏰ <b>{time_val}</b> ({rec_text}) [{status_badge}]{zalo_info}</li>"
        reply += "</ul>"
        return {
            "reply": reply,
            "action": "list_tasks",
            "tasks": tasks
        }

    # 2. Kiểm tra yêu cầu tạo lịch mới (VD: "Nhắc tôi nộp báo cáo lúc 16:30", "Lên lịch họp ban chỉ huy lúc 08:30")
    if any(k in msg_lower for k in ["nhắc tôi", "nhắc mình", "lên lịch", "đặt lịch", "tạo việc", "tạo lịch"]):
        # Tìm giờ trong tin nhắn dạng: 16:30, 16h30, 8h, 08:00
        time_match = re.search(r'(\d{1,2})[:hH](\d{2})?', msg)
        hour, minute = "09", "00"
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2)) if time_match.group(2) else 0
            hour = f"{h:02d}"
            minute = f"{m:02d}"
        
        scheduled_time = f"{hour}:{minute}"

        # Trích xuất tiêu đề công việc
        title = msg
        for prefix in ["nhắc tôi", "nhắc mình", "hãy nhắc tôi", "lên lịch", "đặt lịch", "tạo việc", "tạo lịch"]:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()
                break
        
        title = re.sub(r'lúc\s+\d{1,2}[:hH]\d{0,2}', '', title, flags=re.IGNORECASE).strip()
        title = re.sub(r'\d{1,2}[:hH]\d{0,2}', '', title).strip()
        if not title:
            title = "Công việc cần làm"

        # Tạo task vào database
        new_task = {
            "title": title.capitalize(),
            "description": f"Tạo bởi Trợ lý AI lúc {datetime.now().strftime('%H:%M %d/%m/%Y')}",
            "schedule_type": "daily" if "hàng ngày" in msg_lower else "once",
            "schedule_time": scheduled_time,
            "schedule_days": '["0","1","2","3","4","5","6"]' if "hàng ngày" in msg_lower else "[]",
            "interval_minutes": 60,
            "action_type": "alert_only",
            "is_active": 1,
            "zalo_recipient": "My Documents" if ("my document" in msg_lower or "cloud" in msg_lower or "zalo" in msg_lower) else "",
            "zalo_message": f"Nhắc việc: {title} vào lúc {scheduled_time}",
            "attachment_path": "",
            "attachment_name": "",
            "file_source_mode": "fixed",
            "watch_directory": "",
            "file_pattern": "*.*",
            "auto_zip": 0,
            "safe_countdown_seconds": 15,
            "notify_telegram": 1
        }
        if new_task["zalo_recipient"]:
            new_task["action_type"] = "zalo_msg"

        task_id = database.create_task(new_task)

        reply = (
            f"✅ <b>Đã lên lịch nhắc việc thành công!</b><br>"
            f"📌 <b>Việc:</b> {title.capitalize()}<br>"
            f"⏰ <b>Thời gian:</b> <code>{scheduled_time}</code><br>"
            f"🔔 <b>Kiểu nhắc:</b> {'Hàng ngày' if 'hàng ngày' in msg_lower else 'Một lần'}<br>"
            f"📱 <i>Đến giờ hẹn, điện thoại và trang web sẽ tự động đổ chuông và hiện thông báo nhắc bạn!</i>"
        )
        return {
            "reply": reply,
            "action": "task_created",
            "task_id": task_id,
            "task": new_task
        }

    # 3. Hướng dẫn cài App trên điện thoại
    if any(k in msg_lower for k in ["cài app", "apk", "điện thoại", "màn hình chính", "cài đặt app"]):
        return {
            "reply": (
                "📲 <b>Cách cài đặt Web App lên màn hình chính điện thoại (dùng y hệt APK):</b><br><br>"
                "1. Trên điện thoại, bạn mở trình duyệt <b>Chrome</b> (hoặc Cốc Cốc, Safari).<br>"
                "2. Truy cập đường link: <code>https://zalo-task-assistant.onrender.com</code><br>"
                "3. Bấm vào nút <b>Ba chấm (⋮)</b> ở góc trên bên phải trình duyệt.<br>"
                "4. Chọn mục <b>'Thêm vào màn hình chính'</b> (hoặc <i>'Cài đặt ứng dụng'</i>).<br>"
                "5. Xong! Trên màn hình điện thoại của bạn sẽ xuất hiện biểu tượng ứng dụng ZaloTask. Khi mở ra sẽ hiển thị full màn hình như 1 app APK thực thụ, cực nhẹ và không tốn bộ nhớ máy!"
            ),
            "action": "guide_pwa"
        }

    # 4. Hỏi về trạng thái máy tính và Zalo
    if any(k in msg_lower for k in ["máy tính", "zalo", "kết nối", "desktop"]):
        return {
            "reply": (
                "🖥️ <b>Cơ chế hoạt động của Máy tính & Zalo:</b><br><br>"
                "• <b>Khi bạn dùng trên điện thoại:</b> Bạn có thể xem lịch, tạo việc, và điện thoại sẽ báo chuông nhắc nhở đúng giờ.<br>"
                "• <b>Khi máy tính của bạn bật (online):</b> Ứng dụng chạy ngầm trên máy sẽ tự động kích hoạt Zalo Desktop, mở chat và dán file gửi đi tự động 100%.<br>"
                "• <b>Khi máy tính tắt:</b> Hệ thống đám mây vẫn nhắc nhở bạn qua chuông báo và gửi tin về Telegram điện thoại!"
            ),
            "action": "guide_zalo"
        }

    # 5. Phản hồi chung / Trò chuyện
    return {
        "reply": (
            f"🤖 Tôi đã nhận được tin nhắn: <i>\"{msg}\"</i>.<br><br>"
            "Tôi có thể giúp bạn các việc sau:<br>"
            "• <b>Lên lịch nhắc việc:</b> Nhắn ví dụ <i>'Nhắc tôi nộp tài liệu lúc 17h00'</i><br>"
            "• <b>Xem việc hôm nay:</b> Nhắn <i>'Có việc gì hôm nay'</i><br>"
            "• <b>Cài đặt lên điện thoại:</b> Nhắn <i>'Cách cài lên điện thoại'</i>"
        ),
        "action": "general_chat"
    }

def json_all_days():
    return '["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]'
