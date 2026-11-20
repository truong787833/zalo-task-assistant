import os
import time
import requests
import logging
from datetime import datetime
from . import zalo_dispatcher

logger = logging.getLogger("BridgeWorker")

CLOUD_URL = os.environ.get("CLOUD_URL", "https://zalo-task-assistant.onrender.com").rstrip("/")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

def run_bridge_worker(stop_event=None):
    """
    Tiến trình cầu nối chạy ngầm trên máy tính Windows.
    Liên tục đồng bộ với Cloud (Render), nhận lệnh gửi Zalo từ điện thoại và thực thi trên Zalo Desktop.
    """
    logger.info(f"Khởi động BridgeWorker kết nối tới Cloud: {CLOUD_URL}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            # 1. Kiểm tra xem Zalo Desktop có đang chạy trên Windows không
            zalo_info = zalo_dispatcher.get_zalo_window_info()
            zalo_is_running = (zalo_info is not None)
            
            # 2. Gửi Heartbeat lên Cloud
            try:
                requests.post(
                    f"{CLOUD_URL}/api/bridge/heartbeat",
                    json={"zalo_running": zalo_is_running, "pc_name": os.environ.get("COMPUTERNAME", "Windows PC")},
                    timeout=5
                )
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

            # 3. Lấy danh sách việc đang chờ từ Cloud
            try:
                res = requests.get(f"{CLOUD_URL}/api/bridge/pending-jobs", timeout=5)
                if res.status_code == 200:
                    jobs = res.json().get("jobs", [])
                    for job in jobs:
                        job_id = job.get("id")
                        task = job.get("task", {})
                        file_url = job.get("file_url")
                        filename = job.get("filename")

                        logger.info(f"Nhận lệnh từ điện thoại: {task.get('zalo_recipient')}")

                        # Nếu có file đính kèm trên cloud, tải về máy tính
                        local_file_path = ""
                        if file_url:
                            download_url = f"{CLOUD_URL}{file_url}" if file_url.startswith("/") else file_url
                            try:
                                r_file = requests.get(download_url, timeout=30)
                                if r_file.status_code == 200:
                                    local_file_path = os.path.join(UPLOAD_DIR, filename or "downloaded_file.tmp")
                                    with open(local_file_path, "wb") as f_out:
                                        f_out.write(r_file.content)
                                    task["attachment_path"] = local_file_path
                            except Exception as dl_err:
                                logger.error(f"Lỗi tải file từ cloud: {dl_err}")

                        # Thực thi gửi trực tiếp trên Zalo Desktop
                        dispatch_res = zalo_dispatcher.dispatch_zalo_task(task)
                        
                        # Báo cáo hoàn thành lên Cloud
                        try:
                            requests.post(
                                f"{CLOUD_URL}/api/bridge/complete-job/{job_id}",
                                json={"result": dispatch_res, "logs": dispatch_res.get("logs", [])},
                                timeout=10
                            )
                        except Exception as cp_err:
                            logger.error(f"Lỗi báo cáo hoàn thành: {cp_err}")

            except Exception as e:
                logger.debug(f"Job polling error: {e}")

        except Exception as e:
            logger.error(f"Lỗi vòng lặp bridge: {e}")

        time.sleep(3)
