import os
import sys
import threading
import time
import webbrowser
import winreg
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import uvicorn

# Thêm đường dẫn project
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend.app import app
from backend.scheduler_engine import scheduler

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_KEY_NAME = "ZaloTaskAssistant"

def create_tray_icon_image():
    """
    Tạo icon khay hệ thống đẹp mắt kích thước 64x64: Nền xanh Zalo kèm biểu tượng chuông trắng.
    """
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Nền tròn xanh đậm Zalo (#0068ff)
    draw.rounded_rectangle([(2, 2), (62, 62)], radius=16, fill=(0, 104, 255, 255))
    
    # Vẽ biểu tượng quả chuông màu trắng
    # Thân chuông
    draw.ellipse([(20, 16), (44, 40)], fill=(255, 255, 255, 255))
    draw.rectangle([(16, 28), (48, 44)], fill=(255, 255, 255, 255))
    draw.ellipse([(12, 40), (52, 48)], fill=(255, 255, 255, 255))
    # Quả lắc chuông
    draw.ellipse([(27, 46), (37, 54)], fill=(255, 215, 0, 255))
    
    return image

def is_autostart_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, REG_KEY_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False

def toggle_autostart(icon, item):
    enabled = is_autostart_enabled()
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        if enabled:
            try:
                winreg.DeleteValue(key, REG_KEY_NAME)
            except Exception:
                pass
        else:
            # Đường dẫn chạy ngầm không hiện cửa sổ console
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            target_cmd = f'"{pythonw}" "{os.path.join(current_dir, "tray.py")}"'
            winreg.SetValueEx(key, REG_KEY_NAME, 0, winreg.REG_SZ, target_cmd)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Lỗi cài đặt khởi động cùng Windows: {e}")

def open_dashboard(icon=None, item=None):
    webbrowser.open(URL)

def toggle_scheduler(icon=None, item=None):
    if scheduler._running:
        scheduler.stop()
    else:
        scheduler.start()

def quit_app(icon, item):
    scheduler.stop()
    icon.stop()
    os._exit(0)

def run_uvicorn_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

def main():
    # 1. Khởi chạy Uvicorn Server trong background thread
    server_thread = threading.Thread(target=run_uvicorn_server, daemon=True)
    server_thread.start()
    
    # 2. Mở trình duyệt Dashboard lần đầu
    threading.Thread(target=lambda: (time.sleep(1.2), open_dashboard()), daemon=True).start()
    
    # 3. Tạo Menu Khay Hệ Thống
    menu = pystray.Menu(
        item("🌐 Mở Bảng Điều Khiển Web", open_dashboard, default=True),
        item("🔔 Bộ Lập Lịch", pystray.Menu(
            item("▶ Đang Bật", lambda i, it: None, checked=lambda it: scheduler._running),
            item("Bật/Tắt Lập Lịch", toggle_scheduler)
        )),
        item("🚀 Khởi Động Cùng Windows", toggle_autostart, checked=lambda it: is_autostart_enabled()),
        pystray.Menu.SEPARATOR,
        item("❌ Thoát Hoàn Toàn", quit_app)
    )
    
    icon_img = create_tray_icon_image()
    tray_icon = pystray.Icon(
        name="ZaloTaskAssistant",
        icon=icon_img,
        title="ZaloTask Assistant - Đang Chạy Ngầm",
        menu=menu
    )
    
    print("[*] ZaloTask Assistant đã thu nhỏ xuống Khay hệ thống (System Tray).")
    tray_icon.run()

if __name__ == "__main__":
    main()
