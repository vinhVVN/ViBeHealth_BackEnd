import google.generativeai as genai
import json
import os
import time
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env")

genai.configure(api_key=api_key)

class GeminiOCRService:
    def __init__(self):
        
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-lite',
            generation_config={"response_mime_type": "application/json"}
        )

    def analyze_prescription(self, raw_text):
        prompt = f"""
        Bạn là trợ lý y tế. Trích xuất thông tin thuốc từ văn bản OCR (có thể sai chính tả).
        
        INPUT TEXT:
        '''
        {raw_text}
        '''

        YÊU CẦU:
        1. Tên thuốc (name): Ưu tiên tên thương mại. Nếu không có lấy tên hoạt chất. Tự sửa lỗi chính tả.
        2. Tổng số lượng (total_quantity): Tìm con số chỉ tổng lượng cấp phát.
        3. Đơn vị (unit): Chuẩn hóa (viên, vỉ, chai, gói, ống...).
        4. Tần suất (frequency): VD: Sáng 1 viên, Tối 1 viên.
        5. Hàm lượng (dosage): VD: 500mg.

        OUTPUT (JSON List):
        [
          {{
            "name": "Tên thuốc",
            "dosage": "500mg",
            "total_quantity": 20, 
            "unit": "viên",
            "frequency": "Sáng 1, Tối 1"
          }}
        ]
        Trả về [] nếu không tìm thấy.
        """

        # 2. CƠ CHẾ RETRY (Thử lại khi gặp lỗi 429)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Gọi API
                response = self.model.generate_content(prompt)
                
                # Parse kết quả
                data = json.loads(response.text)
                if isinstance(data, list):
                    return data
                return []
            
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ Gemini Error (Lần thử {attempt + 1}/{max_retries}): {error_msg}")
                
                # Nếu là lỗi 429 (Too Many Requests) -> Chờ một chút rồi thử lại
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = 2 * (attempt + 1) # Chờ 2s, 4s, 6s...
                    print(f"⏳ Đang chờ {wait_time}s để thử lại...")
                    time.sleep(wait_time)
                else:
                    # Nếu lỗi khác (VD: Sai Key, Mạng rớt) -> Dừng luôn để chuyển sang Regex Fallback
                    break
        
        return None # Trả về None để main.py biết đường chuyển sang Regex