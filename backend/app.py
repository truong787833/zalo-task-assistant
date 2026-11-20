import os
from datetime import datetime
from typing import Optional, List

try:
    import psutil
except ImportError:
    psutil = None

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import database
from . import file_manager
from . import zalo_dispatcher
from . import ai_assistant
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

import time
import asyncio

BRIDGE_JOBS: dict = {}
PC_HEARTBEAT: dict = {
    "last_seen": 0,
    "zalo_running": False,
    "pc_name": ""
}

@app.get("/api/system-status")
def get_system_status():
    zalo_running = False
    is_win = (os.name == 'nt')
    if is_win:
        if psutil is not None:
            try:
                zalo_running = any("zalo" in (p.info["name"] or "").lower() for p in psutil.process_iter(["name"]))
            except Exception:
                zalo_running = False
    else:
        # Khi chạy trên Cloud Linux: kiểm tra tín hiệu từ Máy tính Windows cá nhân
        is_pc_online = (time.time() - PC_HEARTBEAT["last_seen"]) < 20
        zalo_running = is_pc_online and PC_HEARTBEAT.get("zalo_running", False)

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
    
    if os.name == 'nt':
        res = zalo_dispatcher.dispatch_zalo_task(sim_task, dry_run=dry_run)
        return {"success": res.get("success"), "result": res}
    else:
        # Chạy trên Cloud Linux -> Đẩy Job về Máy tính Windows của bạn qua Cầu Nối (Bridge)
        import uuid
        job_id = str(uuid.uuid4())
        filename = os.path.basename(attachment_path) if attachment_path else ""
        file_download_url = f"/api/files/download/{filename}" if filename else ""
        now_str = datetime.now().strftime("%H:%M:%S")

        job_data = {
            "id": job_id,
            "created_at": now_str,
            "task": sim_task,
            "file_url": file_download_url,
            "filename": attachment_name or filename,
            "status": "pending",
            "logs": [
                f"[{now_str}] [Điện thoại] Đã tiếp nhận yêu cầu gửi tới '{recipient}'",
                f"[{now_str}] [Cloud] Đã đưa vào hàng đợi, chuyển tiếp tới Máy Tính của bạn..."
            ]
        }
        BRIDGE_JOBS[job_id] = job_data

        # Chờ tối đa 6 giây xem máy tính có gửi xong và phản hồi lại ngay không
        start_wait = time.time()
        while time.time() - start_wait < 6:
            if BRIDGE_JOBS[job_id]["status"] == "completed":
                break
            await asyncio.sleep(0.5)

        job = BRIDGE_JOBS[job_id]
        if job["status"] == "completed":
            return {"success": True, "result": job.get("result", {"logs": job["logs"]})}
        else:
            pc_online = (time.time() - PC_HEARTBEAT["last_seen"]) < 20
            pc_status_note = "Máy tính đang kết nối, chuẩn bị thực hiện..." if pc_online else "Máy tính của bạn đang offline. Lệnh sẽ tự động thực hiện ngay khi bạn bật máy!"
            return {
                "success": True,
                "result": {
                    "logs": job["logs"] + [f"[{datetime.now().strftime('%H:%M:%S')}] {pc_status_note}"]
                }
            }

@app.post("/api/bridge/heartbeat")
def bridge_heartbeat(data: dict):
    PC_HEARTBEAT["last_seen"] = time.time()
    PC_HEARTBEAT["zalo_running"] = data.get("zalo_running", False)
    PC_HEARTBEAT["pc_name"] = data.get("pc_name", "Windows PC")
    return {"status": "ok", "server_time": time.time()}

@app.get("/api/bridge/pending-jobs")
def get_pending_jobs():
    pending = [job for job in BRIDGE_JOBS.values() if job["status"] == "pending"]
    return {"jobs": pending}

@app.post("/api/bridge/complete-job/{job_id}")
def complete_bridge_job(job_id: str, data: dict):
    if job_id in BRIDGE_JOBS:
        BRIDGE_JOBS[job_id]["status"] = "completed"
        BRIDGE_JOBS[job_id]["result"] = data.get("result", {})
        if "logs" in data:
            BRIDGE_JOBS[job_id]["logs"].extend(data["logs"])
        return {"status": "ok"}
    return {"status": "not_found"}

@app.get("/api/files/download/{filename}")
def download_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    raise HTTPException(status_code=404, detail="File không tồn tại trên Cloud")

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

@app.post("/api/ai-chat")
def handle_ai_chat(data: dict):
    user_msg = data.get("message", "")
    return ai_assistant.process_chat_message(user_msg)

