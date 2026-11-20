import os
import glob
import shutil
import uuid
import zipfile
from typing import Optional, List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_file(file_bytes: bytes, original_filename: str) -> dict:
    """
    Lưu file upload vào thư mục uploads với tên an toàn và duy nhất.
    """
    ext = os.path.splitext(original_filename)[1]
    unique_name = f"{uuid.uuid4().hex[:8]}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    file_size = os.path.getsize(file_path)
    
    return {
        "original_name": original_filename,
        "saved_name": unique_name,
        "path": file_path,
        "size": file_size,
        "extension": ext.lower()
    }

def get_file_info(file_path: str) -> Optional[dict]:
    if not file_path or not os.path.exists(file_path):
        return None
    return {
        "exists": True,
        "path": file_path,
        "name": os.path.basename(file_path),
        "size": os.path.getsize(file_path)
    }

def delete_file(file_path: str) -> bool:
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception:
            return False
    return False

def get_latest_file_in_directory(dir_path: str, pattern: str = "*.*") -> Optional[Dict[str, Any]]:
    """
    Tự động quét thư mục chỉ định và tìm file mới nhất (theo thời gian sửa đổi mtime).
    Hỗ trợ lọc theo pattern (ví dụ: '*.xlsx', '*.pdf', '*.png').
    """
    if not dir_path or not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return None
        
    pattern = pattern.strip() if pattern else "*.*"
    search_path = os.path.join(dir_path, pattern)
    files = glob.glob(search_path)
    # Lọc chỉ lấy file thực sự, bỏ qua thư mục con
    files = [f for f in files if os.path.isfile(f)]
    
    if not files:
        # Nếu pattern cụ thể không thấy, thử tìm tất cả file
        if pattern != "*.*":
            all_files = [f for f in glob.glob(os.path.join(dir_path, "*.*")) if os.path.isfile(f)]
            if all_files:
                files = all_files
            else:
                return None
        else:
            return None
            
    # Sắp xếp theo mtime mới nhất
    latest_file = max(files, key=os.path.getmtime)
    
    return {
        "path": os.path.abspath(latest_file),
        "name": os.path.basename(latest_file),
        "size": os.path.getsize(latest_file),
        "modified_at": os.path.getmtime(latest_file)
    }

def compress_files_to_zip(file_paths: List[str], output_zip_path: Optional[str] = None) -> Optional[str]:
    """
    Nén danh sách file thành 1 file .zip để gửi một lần qua Zalo.
    """
    valid_files = [f for f in file_paths if os.path.exists(f) and os.path.isfile(f)]
    if not valid_files:
        return None
        
    if not output_zip_path:
        zip_name = f"tailieu_{uuid.uuid4().hex[:6]}.zip"
        output_zip_path = os.path.join(UPLOAD_DIR, zip_name)
        
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in valid_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))
        return output_zip_path
    except Exception as e:
        return None
