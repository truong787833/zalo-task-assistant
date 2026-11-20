import os
import psutil
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import database
from . import file_manager
from . import zalo_dispatcher
from .scheduler_engine import scheduler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

database.init_db()
scheduler.start()

app = FastAPI(title="ZaloTask Assistant API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def get_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ZaloTask Assistant API is running. Static index.html not found."}

@app.get("/api/system-status")
def get_system_status():
    zalo_running = any("zalo" in (p.info["name"] or "").lower() for p in psutil.process_iter(["name"]))
    return {
        "status": "online",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "zalo_desktop_running": zalo_running,
        "scheduler_active": scheduler._running,
        "pending_previews_count": len(scheduler.pending_previews)
    }

@app.get("/api/tasks")
def get_tasks():
    tasks = database.list_tasks()
    return {"tasks": tasks}

@app.post("/api/tasks")
async def create_new_task(
    title: str = Form(...),
    description: Optional[str] = Form(""),
    schedule_type: str = Form("daily"),
    schedule_time: Optional[str] = Form("08:00"),
    schedule_days: Optional[str] = Form(""),
    interval_minutes: Optional[int] = Form(60),
    action_type: str = Form("zalo_all"),
    zalo_recipient: Optional[str] = Form(""),
    zalo_message: Optional[str] = Form(""),
    file_source_mode: Optional[str] = Form("fixed"),
    watch_directory: Optional[str] = Form(""),
    file_pattern: Optional[str] = Form("*.*"),
    auto_zip: Optional[bool] = Form(False),
    safe_countdown_seconds: Optional[int] = Form(0),
    notify_telegram: Optional[bool] = Form(False),
    file: Optional[UploadFile] = File(None)
):
    attachment_path = ""
    attachment_name = ""
    
    if file and file.filename:
        file_bytes = await file.read()
        saved = file_manager.save_uploaded_file(file_bytes, file.filename)
        attachment_path = saved["path"]
        attachment_name = saved["original_name"]
        
    task_data = {
        "title": title,
        "description": description,
        "schedule_type": schedule_type,
        "schedule_time": schedule_time,
        "schedule_days": schedule_days,
        "interval_minutes": interval_minutes,
        "action_type": action_type,
        "zalo_recipient": zalo_recipient,
        "zalo_message": zalo_message,
        "attachment_path": attachment_path,
        "attachment_name": attachment_name,
        "file_source_mode": file_source_mode or "fixed",
        "watch_directory": watch_directory or "",
        "file_pattern": file_pattern or "*.*",
        "auto_zip": auto_zip,
        "safe_countdown_seconds": safe_countdown_seconds or 0,
        "notify_telegram": notify_telegram,
        "is_active": True
    }
    
    task = database.create_task(task_data)
    return {"success": True, "task": task}

@app.put("/api/tasks/{task_id}")
async def edit_task(
    task_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(""),
    schedule_type: str = Form("daily"),
    schedule_time: Optional[str] = Form("08:00"),
    schedule_days: Optional[str] = Form(""),
    interval_minutes: Optional[int] = Form(60),
    action_type: str = Form("zalo_all"),
    zalo_recipient: Optional[str] = Form(""),
    zalo_message: Optional[str] = Form(""),
    file_source_mode: Optional[str] = Form("fixed"),
    watch_directory: Optional[str] = Form(""),
    file_pattern: Optional[str] = Form("*.*"),
    auto_zip: Optional[bool] = Form(False),
    safe_countdown_seconds: Optional[int] = Form(0),
    notify_telegram: Optional[bool] = Form(False),
    file: Optional[UploadFile] = File(None),
    keep_existing_file: bool = Form(True)
):
    existing = database.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ")
        
    attachment_path = existing["attachment_path"]
    attachment_name = existing["attachment_name"]
    
    if file and file.filename:
        file_bytes = await file.read()
        saved = file_manager.save_uploaded_file(file_bytes, file.filename)
        attachment_path = saved["path"]
        attachment_name = saved["original_name"]
    elif not keep_existing_file:
        attachment_path = ""
        attachment_name = ""
        
    update_data = {
        "title": title,
        "description": description,
        "schedule_type": schedule_type,
        "schedule_time": schedule_time,
        "schedule_days": schedule_days,
        "interval_minutes": interval_minutes,
        "action_type": action_type,
        "zalo_recipient": zalo_recipient,
        "zalo_message": zalo_message,
        "attachment_path": attachment_path,
        "attachment_name": attachment_name,
        "file_source_mode": file_source_mode or existing.get("file_source_mode", "fixed"),
        "watch_directory": watch_directory or existing.get("watch_directory", ""),
        "file_pattern": file_pattern or existing.get("file_pattern", "*.*"),
        "auto_zip": auto_zip,
        "safe_countdown_seconds": safe_countdown_seconds or 0,
        "notify_telegram": notify_telegram,
        "is_active": existing["is_active"]
    }
    
    updated = database.update_task(task_id, update_data)
    return {"success": True, "task": updated}

@app.post("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int):
    updated = database.toggle_task(task_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ")
    return {"success": True, "task": updated}

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    task = database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ")
    if task["attachment_path"]:
        file_manager.delete_file(task["attachment_path"])
    database.delete_task(task_id)
    return {"success": True, "message": "Đã xóa tác vụ"}

@app.post("/api/tasks/{task_id}/run-now")
def run_task_immediately(task_id: int, dry_run: bool = False):
    task = database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ")
        
    tele_token = database.get_setting("telegram_bot_token", "")
    tele_chat = database.get_setting("telegram_chat_id", "")
    tele_config = {"token": tele_token, "chat_id": tele_chat} if (task.get("notify_telegram") and tele_token and tele_chat) else None
    
    res = zalo_dispatcher.dispatch_zalo_task(task, dry_run=dry_run, telegram_config=tele_config)
    status = "SUCCESS" if res.get("success") else "FAILED"
    log_detail = "\n".join(res.get("logs", []))
    database.record_task_run(task_id, status, log_detail)
    
    return {"success": res.get("success"), "result": res}

@app.post("/api/tasks/{task_id}/confirm-preview")
def confirm_preview_task(task_id: int):
    """
    Xác nhận gửi ngay trên hộp thoại xem trước (bỏ qua đếm lùi).
    """
    success = scheduler.confirm_and_run_preview(task_id)
    return {"success": success}

@app.post("/api/tasks/{task_id}/postpone-preview")
def postpone_preview_task(task_id: int, minutes: int = 15):
    """
    Hoãn tác vụ N phút trên hộp thoại xem trước.
    """
    task = scheduler.postpone_preview(task_id, minutes)
    return {"success": bool(task), "task": task}

@app.post("/api/test-zalo")
async def test_zalo_direct(
    recipient: str = Form(...),
    message: Optional[str] = Form(""),
    dry_run: bool = Form(False),
    file_source_mode: Optional[str] = Form("fixed"),
    watch_directory: Optional[str] = Form(""),
    file_pattern: Optional[str] = Form("*.*"),
    file: Optional[UploadFile] = File(None)
):
    attachment_path = ""
    attachment_name = ""
    
    if file and file.filename:
        file_bytes = await file.read()
        saved = file_manager.save_uploaded_file(file_bytes, file.filename)
        attachment_path = saved["path"]
        attachment_name = saved["original_name"]
        
    sim_task = {
        "title": "Kiểm thử trực tiếp",
        "zalo_recipient": recipient,
        "zalo_message": message or "Tin nhắn kiểm tra từ ZaloTask Assistant",
        "attachment_path": attachment_path,
        "attachment_name": attachment_name,
        "file_source_mode": file_source_mode,
        "watch_directory": watch_directory,
        "file_pattern": file_pattern,
        "action_type": "zalo_all"
    }
    
    res = zalo_dispatcher.dispatch_zalo_task(sim_task, dry_run=dry_run)
    return {"success": res.get("success"), "result": res}

@app.get("/api/browse-directory")
def test_browse_directory(path: str, pattern: str = "*.*"):
    """
    Kiểm tra thư mục xem có file nào mới nhất phù hợp không.
    """
    if not path or not os.path.exists(path):
        return {"exists": False, "message": "Thư mục không tồn tại"}
    latest = file_manager.get_latest_file_in_directory(path, pattern)
    return {
        "exists": True,
        "latest_file": latest
    }

@app.get("/api/alerts")
def get_pending_alerts():
    alerts = scheduler.get_and_clear_alerts()
    return {"alerts": alerts}

@app.get("/api/logs")
def get_execution_history(limit: int = 50):
    logs = database.get_recent_logs(limit)
    return {"logs": logs}

@app.get("/api/settings")
def get_settings():
    return database.get_all_settings()

@app.post("/api/settings")
def update_settings(data: dict):
    for k, v in data.items():
        database.set_setting(k, v)
    return {"success": True, "settings": database.get_all_settings()}

@app.post("/api/test-telegram")
def test_telegram_connection(bot_token: str = Form(...), chat_id: str = Form(...)):
    """
    Gửi tin nhắn test về điện thoại qua Telegram Bot.
    """
    now_str = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    test_msg = (
        f"🎉 <b>[ZaloTask Assistant] Kết Nối Thành Công!</b>\n"
        f"Thiết bị của bạn đã được liên kết để nhận báo cáo gửi Zalo tự động.\n"
        f"🕒 <i>Thời gian test: {now_str}</i>"
    )
    success = zalo_dispatcher.send_telegram_notification(bot_token, chat_id, test_msg)
    return {
        "success": success,
        "message": "Đã gửi tin nhắn test đến Telegram thành công!" if success else "Gửi thất bại. Vui lòng kiểm tra lại Bot Token hoặc Chat ID!"
    }
