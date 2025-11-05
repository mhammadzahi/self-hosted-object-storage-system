import os
from fastapi import UploadFile
from config import UPLOAD_DIR
import uuid

def save_file(file: UploadFile, folder: str = "") -> str:
    ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4()) + ext
    path = os.path.join(UPLOAD_DIR, folder)
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, file_id)
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    return file_id



def get_file(file_id: str, folder: str = "") -> str:
    file_path = os.path.join(UPLOAD_DIR, folder, file_id)
    if not os.path.exists(file_path):
        return None
        
    return file_path
