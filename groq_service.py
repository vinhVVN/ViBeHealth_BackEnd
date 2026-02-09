import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

class GroqOCRService:
    def __init__(self):
        if not api_key:
            raise ValueError("Chưa cấu hình GROQ_API_KEY trong .env")
        
        self.client = Groq(api_key=api_key)
        # Khuyên dùng model này: Rất thông minh và miễn phí trên Groq
        self.model = "llama-3.1-8b-instant" 

    def analyze_prescription(self, raw_text):
        # Prompt hệ thống: Yêu cầu trả về JSON Object
        system_prompt = """
        You are a medical text extraction assistant.
        Your task is to extract medication information from Vietnamese prescription OCR text.
        
        RULES:
        1. Extract: name, dosage, total_quantity, unit, frequency.
        2. Correct typos based on medical context (e.g., "Pnadol" -> "Panadol").
        3. If info is missing, use null.
        4. OUTPUT MUST BE A VALID JSON OBJECT with a key "medications" containing the list.
        """

        # Prompt người dùng: Đưa văn bản OCR vào
        user_prompt = f"""
        INPUT TEXT:
        '''
        {raw_text}
        '''
        
        Output format example:
        {{
            "medications": [
                {{
                    "name": "Panadol Extra",
                    "dosage": "500mg",
                    "total_quantity": 20,
                    "unit": "viên",
                    "frequency": "Sáng 1 viên, Tối 1 viên"
                }}
            ]
        }}
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # Giảm nhiệt độ để tăng độ chính xác
                max_tokens=2048,
                top_p=1,
                stream=False, # Tắt stream để dễ parse JSON
                # QUAN TRỌNG: Bắt buộc trả về JSON
                response_format={"type": "json_object"} 
            )

            # Lấy kết quả chuỗi JSON
            json_str = completion.choices[0].message.content
            
            # Parse sang Python Dictionary
            data = json.loads(json_str)
            
            # Trả về danh sách thuốc (key 'medications')
            return data.get("medications", [])

        except Exception as e:
            print(f"❌ Groq Error: {e}")
            return None # Trả về None để kích hoạt Fallback