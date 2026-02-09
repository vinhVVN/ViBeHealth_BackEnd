import logging
import os
from datetime import datetime

# Tạo thư mục logs nếu chưa có
if not os.path.exists("logs"):
    os.makedirs("logs")

# Cấu hình logger
logging.basicConfig(
    filename=f"logs/ocr_debug.log", # File log sẽ nằm ở thư mục logs/
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    encoding="utf-8"
)

def log_ocr_input(raw_text):
    separator = "=" * 50
    logging.info(f"\n{separator}\nRAW INPUT RECEIVED:\n{raw_text}\n{separator}")