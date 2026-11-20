import os
import sys
import threading
import time
import uvicorn

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend import bridge_worker
from backend.app import app

def main():
    print("[*] Khởi động ZaloTask Local Agent (Cầu nối Cloud & Local Server)...")
    # Chạy Cầu nối Cloud Bridge trong background thread
    t = threading.Thread(target=bridge_worker.run_bridge_worker, daemon=True)
    t.start()
    
    # Chạy máy chủ nội bộ
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")

if __name__ == "__main__":
    main()
