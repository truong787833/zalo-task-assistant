import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zalo_tasks.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Bảng lưu trữ tác vụ (tasks)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        schedule_type TEXT NOT NULL, -- 'once', 'daily', 'weekly', 'interval'
        schedule_time TEXT,          -- 'HH:MM' hoặc ISO string cho 'once'
        schedule_days TEXT,          -- '0,1,2,3,4' (0=Thứ 2, 6=Chủ nhật) cho 'weekly'
        interval_minutes INTEGER DEFAULT 60, -- cho 'interval'
        action_type TEXT NOT NULL DEFAULT 'zalo_all', -- 'alert_only', 'zalo_msg', 'zalo_file', 'zalo_all'
        zalo_recipient TEXT,         -- Tên bạn bè hoặc nhóm trên Zalo
        zalo_message TEXT,           -- Nội dung tin nhắn
        attachment_path TEXT,        -- Đường dẫn file đính kèm
        attachment_name TEXT,        -- Tên file hiển thị
        is_active INTEGER DEFAULT 1, -- 1: Đang hoạt động, 0: Tạm dừng
        next_run TEXT,               -- Thời gian chạy tiếp theo (ISO format: YYYY-MM-DDTHH:MM:SS)
        last_run TEXT,
        last_status TEXT,            -- 'success', 'failed', 'pending'
        created_at TEXT NOT NULL
    )
    """)
    
    # Bảng nhật ký thực thi (execution history)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS execution_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        task_title TEXT,
        executed_at TEXT NOT NULL,
        status TEXT NOT NULL, -- 'SUCCESS', 'FAILED', 'INFO'
        recipient TEXT,
        message TEXT,
        attachment_name TEXT,
        details TEXT,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE SET NULL
    )
    """)
    
    # Bảng cài đặt hệ thống (app_settings)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Cập nhật thêm các cột mới cho tasks nếu chưa có (Migration an toàn)
    existing_cols = [c[1] for c in cursor.execute("PRAGMA table_info(tasks)").fetchall()]
    new_cols = [
        ("file_source_mode", "TEXT DEFAULT 'fixed'"),
        ("watch_directory", "TEXT DEFAULT ''"),
        ("file_pattern", "TEXT DEFAULT '*.*'"),
        ("auto_zip", "INTEGER DEFAULT 0"),
        ("safe_countdown_seconds", "INTEGER DEFAULT 0"),
        ("notify_telegram", "INTEGER DEFAULT 0")
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()

def calculate_next_run(schedule_type, schedule_time, schedule_days=None, interval_minutes=60, from_time=None):
    """
    Tính thời điểm kích hoạt tiếp theo dựa vào kiểu lịch trình.
    """
    now = from_time or datetime.now()
    
    if schedule_type == 'once':
        if not schedule_time:
            return None
        try:
            target = datetime.fromisoformat(schedule_time)
            return target.isoformat() if target > now else None
        except Exception:
            return None
            
    elif schedule_type == 'interval':
        minutes = max(1, int(interval_minutes or 60))
        next_time = now + timedelta(minutes=minutes)
        return next_time.strftime("%Y-%m-%dT%H:%M:00")
        
    elif schedule_type == 'daily':
        if not schedule_time:
            schedule_time = "08:00"
        hours, mins = map(int, schedule_time.split(':')[:2])
        target_today = now.replace(hour=hours, minute=mins, second=0, microsecond=0)
        if target_today > now:
            return target_today.strftime("%Y-%m-%dT%H:%M:00")
        else:
            target_tomorrow = target_today + timedelta(days=1)
            return target_tomorrow.strftime("%Y-%m-%dT%H:%M:00")
            
    elif schedule_type == 'weekly':
        if not schedule_time:
            schedule_time = "08:00"
        hours, mins = map(int, schedule_time.split(':')[:2])
        if not schedule_days:
            days_list = [0] # Mặc định Thứ 2
        else:
            days_list = [int(d.strip()) for d in str(schedule_days).split(',') if d.strip().isdigit()]
            if not days_list:
                days_list = [0]
                
        for day_offset in range(0, 8):
            check_date = now + timedelta(days=day_offset)
            if check_date.weekday() in days_list:
                candidate = check_date.replace(hour=hours, minute=mins, second=0, microsecond=0)
                if candidate > now:
                    return candidate.strftime("%Y-%m-%dT%H:%M:00")
                    
        fallback = now + timedelta(days=7)
        return fallback.replace(hour=hours, minute=mins, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:00")
        
    return None

def create_task(data):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    next_run = calculate_next_run(
        schedule_type=data.get('schedule_type', 'daily'),
        schedule_time=data.get('schedule_time', '08:00'),
        schedule_days=data.get('schedule_days'),
        interval_minutes=data.get('interval_minutes', 60)
    )
    
    cursor.execute("""
    INSERT INTO tasks (
        title, description, schedule_type, schedule_time, schedule_days,
        interval_minutes, action_type, zalo_recipient, zalo_message,
        attachment_path, attachment_name, is_active, next_run, created_at,
        file_source_mode, watch_directory, file_pattern, auto_zip,
        safe_countdown_seconds, notify_telegram
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('title'),
        data.get('description', ''),
        data.get('schedule_type', 'daily'),
        data.get('schedule_time', '08:00'),
        data.get('schedule_days', ''),
        data.get('interval_minutes', 60),
        data.get('action_type', 'zalo_all'),
        data.get('zalo_recipient', ''),
        data.get('zalo_message', ''),
        data.get('attachment_path', ''),
        data.get('attachment_name', ''),
        1 if data.get('is_active', True) else 0,
        next_run,
        now_str,
        data.get('file_source_mode', 'fixed'),
        data.get('watch_directory', ''),
        data.get('file_pattern', '*.*'),
        1 if data.get('auto_zip') else 0,
        int(data.get('safe_countdown_seconds', 0) or 0),
        1 if data.get('notify_telegram') else 0
    ))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_task(task_id)

def get_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY is_active DESC, next_run ASC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task(task_id, data):
    task = get_task(task_id)
    if not task:
        return None
        
    conn = get_connection()
    cursor = conn.cursor()
    
    schedule_type = data.get('schedule_type', task['schedule_type'])
    schedule_time = data.get('schedule_time', task['schedule_time'])
    schedule_days = data.get('schedule_days', task['schedule_days'])
    interval_minutes = data.get('interval_minutes', task['interval_minutes'])
    
    next_run = calculate_next_run(
        schedule_type=schedule_type,
        schedule_time=schedule_time,
        schedule_days=schedule_days,
        interval_minutes=interval_minutes
    )
    
    cursor.execute("""
    UPDATE tasks SET
        title = ?,
        description = ?,
        schedule_type = ?,
        schedule_time = ?,
        schedule_days = ?,
        interval_minutes = ?,
        action_type = ?,
        zalo_recipient = ?,
        zalo_message = ?,
        attachment_path = ?,
        attachment_name = ?,
        is_active = ?,
        next_run = ?,
        file_source_mode = ?,
        watch_directory = ?,
        file_pattern = ?,
        auto_zip = ?,
        safe_countdown_seconds = ?,
        notify_telegram = ?
    WHERE id = ?
    """, (
        data.get('title', task['title']),
        data.get('description', task['description']),
        schedule_type,
        schedule_time,
        schedule_days,
        interval_minutes,
        data.get('action_type', task['action_type']),
        data.get('zalo_recipient', task['zalo_recipient']),
        data.get('zalo_message', task['zalo_message']),
        data.get('attachment_path', task['attachment_path']),
        data.get('attachment_name', task['attachment_name']),
        1 if data.get('is_active', task['is_active']) else 0,
        next_run,
        data.get('file_source_mode', task.get('file_source_mode', 'fixed')),
        data.get('watch_directory', task.get('watch_directory', '')),
        data.get('file_pattern', task.get('file_pattern', '*.*')),
        1 if data.get('auto_zip', task.get('auto_zip', 0)) else 0,
        int(data.get('safe_countdown_seconds', task.get('safe_countdown_seconds', 0)) or 0),
        1 if data.get('notify_telegram', task.get('notify_telegram', 0)) else 0,
        task_id
    ))
    conn.commit()
    conn.close()
    return get_task(task_id)

def toggle_task(task_id, is_active=None):
    task = get_task(task_id)
    if not task:
        return None
    new_status = 1 if (is_active if is_active is not None else not task['is_active']) else 0
    
    conn = get_connection()
    cursor = conn.cursor()
    next_run = None
    if new_status == 1:
        next_run = calculate_next_run(
            task['schedule_type'],
            task['schedule_time'],
            task['schedule_days'],
            task['interval_minutes']
        )
    cursor.execute("UPDATE tasks SET is_active = ?, next_run = ? WHERE id = ?", (new_status, next_run, task_id))
    conn.commit()
    conn.close()
    return get_task(task_id)

def postpone_task(task_id, minutes=15):
    """
    Hoãn tác vụ lại N phút (dùng khi người dùng bấm 'Hoãn 15 phút' trên hộp thoại xem trước).
    """
    task = get_task(task_id)
    if not task:
        return None
        
    now = datetime.now()
    postponed_time = now + timedelta(minutes=minutes)
    next_run_str = postponed_time.strftime("%Y-%m-%dT%H:%M:00")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET next_run = ? WHERE id = ?", (next_run_str, task_id))
    conn.commit()
    conn.close()
    return get_task(task_id)

def delete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return True

def record_task_run(task_id, status, details=""):
    task = get_task(task_id)
    now_str = datetime.now().isoformat()
    if not task:
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    if task['schedule_type'] == 'once':
        next_run = None
        is_active = 0
    else:
        next_run = calculate_next_run(
            task['schedule_type'],
            task['schedule_time'],
            task['schedule_days'],
            task['interval_minutes'],
            from_time=datetime.now()
        )
        is_active = task['is_active']
        
    cursor.execute("""
    UPDATE tasks SET
        last_run = ?,
        last_status = ?,
        next_run = ?,
        is_active = ?
    WHERE id = ?
    """, (now_str, status, next_run, is_active, task_id))
    
    cursor.execute("""
    INSERT INTO execution_logs (
        task_id, task_title, executed_at, status, recipient, message, attachment_name, details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id,
        task['title'],
        now_str,
        status,
        task['zalo_recipient'],
        task['zalo_message'],
        task['attachment_name'],
        details
    ))
    conn.commit()
    conn.close()

def get_due_tasks():
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:59")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE is_active = 1 
      AND next_run IS NOT NULL 
      AND next_run <= ?
    """, (now_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_logs(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Cài đặt hệ thống (app_settings)
def get_setting(key, default=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO app_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM app_settings")
    rows = cursor.fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}
