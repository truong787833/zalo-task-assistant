import sys
import os
import webbrowser
import threading
import time
import uvicorn

# Đảm bảo import được module backend
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def open_browser(url, delay=1.5):
    time.sleep(delay)
    print(f"\n[*] Đang tự động mở trình duyệt tới: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Không thể tự mở trình duyệt: {e}")

if __name__ == "__main__":
    PORT = 8765
    HOST = "127.0.0.1"
    URL = f"http://{HOST}:{PORT}"

    print("=" * 65)
    print("   ZaloTask Assistant - Trợ lý Lập Lịch, Nhắc Việc & Gửi Zalo")
    print("=" * 65)
    print(f"[*] Máy chủ Web đang khởi động tại: {URL}")
    print("[*] Nhấn Ctrl + C để dừng máy chủ bất kỳ lúc nào.\n")

    # Mở trình duyệt sau 1.5 giây
    threading.Thread(target=open_browser, args=(URL,), daemon=True).start()

    from backend.app import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
