import time
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from . import database
from . import zalo_dispatcher

logger = logging.getLogger("SchedulerEngine")

class SchedulerEngine:
    def __init__(self):
        self._running = False
        self._thread = None
        self.active_alerts: List[Dict[str, Any]] = []
        self.pending_previews: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("SchedulerEngine đã khởi động.")
        
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("SchedulerEngine đã dừng.")
        
    def _loop(self):
        while self._running:
            try:
                self._check_and_execute_due_tasks()
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp lập lịch: {e}")
            time.sleep(3)
            
    def _check_and_execute_due_tasks(self):
        due_tasks = database.get_due_tasks()
        now = datetime.now()
        
        for task in due_tasks:
            task_id = task["id"]
            countdown = int(task.get("safe_countdown_seconds", 0) or 0)
            
            # Kiểm tra xem tác vụ có đang trong thời gian đếm lùi xem trước (Safe Preview) không
            with self._lock:
                if task_id in self.pending_previews:
                    preview_info = self.pending_previews[task_id]
                    # Nếu đã hết thời gian đếm lùi -> Kích hoạt gửi tự động
                    if now >= preview_info["execute_at"]:
                        del self.pending_previews[task_id]
                        logger.info(f"Hết đếm lùi xem trước cho tác vụ {task_id}. Tiến hành gửi...")
                        threading.Thread(target=self._execute_single_task, args=(task,), daemon=True).start()
                    continue
                    
            if countdown > 0 and task.get("action_type") != "alert_only":
                # Kích hoạt chế độ đếm lùi xem trước
                execute_at = now + timedelta(seconds=countdown)
                with self._lock:
                    self.pending_previews[task_id] = {
                        "task": task,
                        "execute_at": execute_at,
                        "countdown": countdown
                    }
                    alert_event = {
                        "id": task_id,
                        "title": task["title"],
                        "description": task["description"],
                        "time": now.strftime("%H:%M:%S"),
                        "action_type": task["action_type"],
                        "zalo_recipient": task["zalo_recipient"],
                        "attachment_name": task["attachment_name"],
                        "is_preview": True,
                        "countdown": countdown
                    }
                    self.active_alerts.append(alert_event)
                logger.info(f"Bắt đầu đếm lùi an toàn {countdown}s cho tác vụ {task_id}")
            else:
                # Thực thi bình thường ngay lập tức
                alert_event = {
                    "id": task_id,
                    "title": task["title"],
                    "description": task["description"],
                    "time": now.strftime("%H:%M:%S"),
                    "action_type": task["action_type"],
                    "zalo_recipient": task["zalo_recipient"],
                    "attachment_name": task["attachment_name"],
                    "is_preview": False,
                    "countdown": 0
                }
                with self._lock:
                    self.active_alerts.append(alert_event)
                    if len(self.active_alerts) > 20:
                        self.active_alerts.pop(0)
                        
                threading.Thread(target=self._execute_single_task, args=(task,), daemon=True).start()
                
    def confirm_and_run_preview(self, task_id: int):
        """
        Người dùng bấm 'Gửi Ngay' bỏ qua đếm lùi.
        """
        with self._lock:
            if task_id in self.pending_previews:
                task = self.pending_previews[task_id]["task"]
                del self.pending_previews[task_id]
                threading.Thread(target=self._execute_single_task, args=(task,), daemon=True).start()
                return True
        return False
        
    def postpone_preview(self, task_id: int, minutes: int = 15):
        """
        Người dùng bấm 'Hoãn 15 phút' trên hộp thoại xem trước.
        """
        with self._lock:
            if task_id in self.pending_previews:
                del self.pending_previews[task_id]
        return database.postpone_task(task_id, minutes)
        
    def _execute_single_task(self, task: Dict[str, Any]):
        task_id = task["id"]
        action_type = task.get("action_type", "zalo_all")
        
        # Lấy cấu hình Telegram
        tele_token = database.get_setting("telegram_bot_token", "")
        tele_chat = database.get_setting("telegram_chat_id", "")
        tele_config = None
        if (task.get("notify_telegram") or database.get_setting("telegram_notify_all") == "1") and tele_token and tele_chat:
            tele_config = {"token": tele_token, "chat_id": tele_chat}
            
        try:
            if action_type == "alert_only":
                res = {"success": True, "logs": ["Chỉ nhắc nhở người dùng qua âm thanh & giao diện."]}
            else:
                res = zalo_dispatcher.dispatch_zalo_task(task, dry_run=False, telegram_config=tele_config)
                
            status = "SUCCESS" if res.get("success") else "FAILED"
            log_detail = "\n".join(res.get("logs", []))
            database.record_task_run(task_id, status, log_detail)
            logger.info(f"Hoàn thành tác vụ {task_id}: {status}")
            
        except Exception as e:
            err = f"Ngoại lệ khi thực thi tác vụ: {str(e)}"
            database.record_task_run(task_id, "FAILED", err)
            logger.error(err)
            
    def get_and_clear_alerts(self) -> List[Dict[str, Any]]:
        with self._lock:
            alerts = list(self.active_alerts)
            self.active_alerts.clear()
            return alerts

scheduler = SchedulerEngine()
