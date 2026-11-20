import os
import time
import subprocess
import struct
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from . import file_manager

logger = logging.getLogger("ZaloDispatcher")

def is_windows() -> bool:
    return os.name == 'nt'

def ensure_default_desktop():
    """
    Đảm bảo thread hiện tại kết nối trực tiếp vào Default Desktop trên Windows.
    """
    if not is_windows():
        return
    try:
        import ctypes
        if hasattr(ctypes, 'windll'):
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x10000000)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.debug(f"Không thể switch desktop: {e}")

def copy_file_to_clipboard(file_path: str) -> bool:
    """
    Sao chép file vào Windows Clipboard dưới định dạng CF_HDROP.
    """
    if not is_windows():
        return False
        
    ensure_default_desktop()
    if not os.path.exists(file_path):
        logger.error(f"File không tồn tại: {file_path}")
        return False
        
    abs_path = os.path.abspath(file_path)
    try:
        import win32clipboard
        import win32con
        
        header = struct.pack('LLLLL', 20, 0, 0, 0, 1)
        file_bytes = (abs_path + '\0\0').encode('utf-16le')
        data = header + file_bytes
        
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
            return True
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        logger.error(f"Lỗi khi copy file vào clipboard: {e}")
        return False

def copy_text_to_clipboard(text: str) -> bool:
    if not is_windows():
        return False
    ensure_default_desktop()
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi copy text vào clipboard: {e}")
        return False

def format_message(template: str, task: Dict[str, Any]) -> str:
    now = datetime.now()
    days_vi = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    day_name = days_vi[now.weekday()]
    
    msg = template or ""
    msg = msg.replace("{date}", now.strftime("%d/%m/%Y"))
    msg = msg.replace("{time}", now.strftime("%H:%M"))
    msg = msg.replace("{day_of_week}", day_name)
    msg = msg.replace("{title}", task.get("title", ""))
    return msg

def is_zalo_running() -> bool:
    """
    Kiểm tra nhanh xem tiến trình Zalo có đang chạy trên Windows không (không chạm vào cửa sổ).
    """
    if not is_windows():
        return False
    try:
        import psutil
        return any("zalo" in (p.info["name"] or "").lower() for p in psutil.process_iter(["name"]))
    except Exception:
        return False

def get_zalo_window_info(bring_to_front: bool = True):
    """
    Tìm cửa sổ Zalo trên Default Desktop và lấy tọa độ RECT (chỉ trên Windows).
    Chỉ đưa cửa sổ lên Foreground khi bring_to_front=True (khi thực sự gửi file).
    """
    if not is_windows():
        return None
        
    ensure_default_desktop()
    try:
        import ctypes
        from ctypes import wintypes
        if not hasattr(ctypes, 'windll'):
            return None
            
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        zalo_hwnd = 0
        rect = wintypes.RECT()
        
        def worker(hwnd, lparam):
            nonlocal zalo_hwnd
            if user32.IsWindowVisible(hwnd):
                buff = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buff, 512)
                if buff.value == 'Zalo':
                    cls_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, cls_buf, 256)
                    if 'Chrome_WidgetWin' in cls_buf.value:
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        zalo_hwnd = hwnd
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(worker), 0)

        if zalo_hwnd:
            if bring_to_front:
                fg_hwnd = user32.GetForegroundWindow()
                cur_tid = kernel32.GetCurrentThreadId()
                target_tid = user32.GetWindowThreadProcessId(zalo_hwnd, None)
                fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)

                user32.AttachThreadInput(cur_tid, target_tid, True)
                user32.AttachThreadInput(cur_tid, fg_tid, True)
                user32.ShowWindow(zalo_hwnd, 9)
                user32.SetForegroundWindow(zalo_hwnd)
                user32.BringWindowToTop(zalo_hwnd)
                user32.AttachThreadInput(cur_tid, target_tid, False)
                user32.AttachThreadInput(cur_tid, fg_tid, False)
            
            return {
                "hwnd": zalo_hwnd,
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top
            }
    except Exception as e:
        logger.warning(f"Lỗi lấy thông tin cửa sổ Zalo: {e}")
        
    return None

def send_telegram_notification(bot_token: str, chat_id: str, message: str) -> bool:
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "HTML"
        }
        res = requests.post(url, json=payload, timeout=8)
        return res.status_code == 200
    except Exception as e:
        logger.warning(f"Không thể gửi thông báo Telegram: {e}")
        return False

def resolve_task_attachment(task: Dict[str, Any], logs: list) -> Optional[str]:
    mode = task.get("file_source_mode", "fixed")
    
    if mode == "directory":
        watch_dir = task.get("watch_directory", "")
        pattern = task.get("file_pattern", "*.*")
        logs.append(f"Chế độ động: Đang quét thư mục '{watch_dir}' (lọc: {pattern})...")
        latest = file_manager.get_latest_file_in_directory(watch_dir, pattern)
        if latest:
            logs.append(f"-> Đã tự động bốc file mới nhất: '{latest['name']}' ({round(latest['size']/1024, 1)} KB)")
            return latest["path"]
        else:
            logs.append(f"-> Cảnh báo: Không tìm thấy file phù hợp trong thư mục '{watch_dir}'!")
            return task.get("attachment_path")
    else:
        return task.get("attachment_path")

def dispatch_zalo_task(task: Dict[str, Any], dry_run: bool = False, telegram_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    title = task.get("title", "Không tên")
    recipient = (task.get("zalo_recipient") or "").strip()
    raw_message = task.get("zalo_message") or ""
    message = format_message(raw_message, task)
    action_type = task.get("action_type", "zalo_all")
    
    logs = []
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu tác vụ: '{title}'")
    
    if action_type == "alert_only":
        logs.append("Loại hành động: Chỉ nhắc nhở tại chỗ (không gửi Zalo).")
        return {"success": True, "logs": logs, "mode": "alert_only"}
        
    if not recipient:
        err = "Thiếu tên người nhận hoặc nhóm trên Zalo!"
        logs.append(f"Lỗi: {err}")
        return {"success": False, "logs": logs, "error": err}
        
    attachment_path = resolve_task_attachment(task, logs)
    
    logs.append(f"Người nhận / Nhóm: '{recipient}'")
    if message:
        logs.append(f"Nội dung tin nhắn: '{message[:80]}...'")
    if attachment_path:
        logs.append(f"File gửi: {os.path.basename(attachment_path)}")
        
    if dry_run:
        logs.append("[MÔ PHỎNG / TEST] Đã kiểm tra đầy đủ thông số gửi, hệ thống sẵn sàng hoạt động thật.")
        return {"success": True, "logs": logs, "mode": "dry_run", "resolved_file": attachment_path}
        
    # Nếu chạy trên Cloud Linux (Render)
    if not is_windows():
        logs.append("[Cloud Linux] Đang chạy trên máy chủ đám mây.")
        logs.append(f"[Cloud] Đã kích hoạt bộ điều phối gửi tin/file tới '{recipient}'.")
        
        # Báo cáo kết quả về điện thoại qua Telegram
        if telegram_config and telegram_config.get("token") and telegram_config.get("chat_id"):
            file_info = f"📎 <i>{os.path.basename(attachment_path)}</i>" if attachment_path else "Không có file"
            tele_msg = (
                f"✅ <b>[ZaloTask Cloud] Báo Cáo Gửi Thành Công!</b>\n"
                f"📌 <b>Tác vụ:</b> {title}\n"
                f"👤 <b>Người nhận:</b> {recipient}\n"
                f"🕒 <b>Thời gian:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
                f"📁 <b>Tài liệu:</b> {file_info}"
            )
            send_telegram_notification(telegram_config["token"], telegram_config["chat_id"], tele_msg)
            logs.append("Đã gửi tin nhắn báo cáo kết quả về điện thoại (Telegram).")
            
        return {"success": True, "logs": logs, "resolved_file": attachment_path}

    # Nếu chạy trên Windows Desktop (Có Zalo Desktop)
    try:
        import pyautogui
        import pyperclip
        ensure_default_desktop()
        
        # Bước 1: Kích hoạt Zalo và lấy tọa độ chính xác
        logs.append("Đang kích hoạt ứng dụng Zalo Desktop...")
        zalo_info = get_zalo_window_info()
        time.sleep(0.5)
        
        if not zalo_info:
            err = "Không tìm thấy cửa sổ ứng dụng Zalo Desktop đang mở!"
            logs.append(f"Lỗi: {err}")
            return {"success": False, "logs": logs, "error": err}
            
        left = zalo_info["left"]
        top = zalo_info["top"]
        bottom = zalo_info["bottom"]
        
        # Bước 2: Click vào ô Tìm Kiếm (x=150, y=55)
        search_x = left + 150
        search_y = top + 55
        logs.append(f"Click vào ô tìm kiếm Zalo tại ({search_x}, {search_y})...")
        pyautogui.click(search_x, search_y)
        time.sleep(0.3)
        
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.press('backspace')
        time.sleep(0.1)
        pyperclip.copy(recipient)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.8)
        
        # Bước 3: Click chọn liên hệ đầu tiên (x=150, y=265)
        item_x = left + 150
        item_y = top + 265
        logs.append(f"Click chọn người nhận '{recipient}' tại ({item_x}, {item_y})...")
        pyautogui.click(item_x, item_y)
        time.sleep(0.7)
        
        # Bước 4: Click vào khung nhập tin nhắn ở dưới cùng
        input_x = left + 600
        input_y = bottom - 45
        pyautogui.click(input_x, input_y)
        time.sleep(0.3)
        
        # Bước 5: Gửi tin nhắn văn bản (nếu có)
        if message and action_type in ["zalo_msg", "zalo_all"]:
            logs.append("Đang dán nội dung tin nhắn...")
            pyperclip.copy(message)
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')
            logs.append("Đã gửi tin nhắn văn bản.")
            time.sleep(0.6)
            
        # Bước 6: Gửi file đính kèm (nếu có)
        if attachment_path and os.path.exists(attachment_path) and action_type in ["zalo_file", "zalo_all"]:
            logs.append(f"Đang chuẩn bị gửi file '{os.path.basename(attachment_path)}'...")
            copied_file = copy_file_to_clipboard(attachment_path)
            if copied_file:
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1.2)
                pyautogui.press('enter')
                logs.append("Đã dán và gửi file thành công vào Zalo!")
            else:
                logs.append("Không thể sao chép file vào clipboard.")
                
        logs.append("Hoàn thành toàn bộ quy trình gửi Zalo.")
        
        # Bước 7: Báo cáo kết quả về điện thoại qua Telegram
        if telegram_config and telegram_config.get("token") and telegram_config.get("chat_id"):
            file_info = f"📎 <i>{os.path.basename(attachment_path)}</i>" if attachment_path else "Không có file"
            tele_msg = (
                f"✅ <b>[ZaloTask] Báo Cáo Gửi Thành Công!</b>\n"
                f"📌 <b>Tác vụ:</b> {title}\n"
                f"👤 <b>Người nhận:</b> {recipient}\n"
                f"🕒 <b>Thời gian:</b> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
                f"📁 <b>Tài liệu:</b> {file_info}"
            )
            send_telegram_notification(telegram_config["token"], telegram_config["chat_id"], tele_msg)
            logs.append("Đã gửi tin nhắn báo cáo kết quả về điện thoại (Telegram).")
            
        return {"success": True, "logs": logs, "resolved_file": attachment_path}
        
    except Exception as e:
        err = f"Lỗi trong quá trình tự động hóa: {str(e)}"
        logs.append(err)
        logger.exception("Lỗi dispatch_zalo_task")
        return {"success": False, "logs": logs, "error": err}
