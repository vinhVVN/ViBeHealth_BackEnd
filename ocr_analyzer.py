import re
from thefuzz import process, fuzz
from drug_database import *

# Danh sách đơn vị chuẩn để so khớp
STANDARD_UNITS = ["viên", "vỉ", "hộp", "chai", "lọ", "tuýp", "gói", "ống", "ml", "mg"]

class OCRAnalyzer:
    def __init__(self):
        self.drugs = COMMON_DRUGS
        self.noise = NOISE_KEYWORDS
    
    
    def fuzzy_correct_unit(self, text):
        words = text.split()
        corrected_words = []
        
        for word in words:
            if len(word) <= 5: # thường các từ cần chỉnh <= 5 ký tự
                match = process.extractOne(word, STANDARD_UNITS, scorer= fuzz.ratio)
                if match:
                    best_unit, score = match
                    if score >= 85:
                        corrected_words.append(best_unit)
                        continue
            
            corrected_words.append(word)
        
        return " ".join(corrected_words)
                
    
    def clean_text(self, raw_text):
        lines = raw_text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 2: # Bỏ qua dòng quá ngắn (dưới 2 ký tự)
                continue
            
            is_noise = False
            for word in self.noise:
                if word in line.lower() and not re.match(r"^\d+\.", line): # tránh TH bắt đầu bằng stt của thuốc
                    is_noise = True
                    break
                
            if not is_noise:
                cleaned_lines.append(line)
                
        return cleaned_lines
    
    
    def is_drug_name(self, text_line): # tìm tên thuốc dựa vào stt và fuzzy search
        
        # TH bắt đầu bằng số thứ tự (vd: 1. Yesom) thì khả năng nó là thuốc cao
        if re.match(r"^\d+\.", text_line):
            clean_name = re.sub(r"^\d+\.\s*", "", text_line)
            match = process.extractOne(clean_name, self.drugs, scorer= fuzz.token_set_ratio)
            if match and match[1] >= 70: # Giảm ngưỡng xuống 70
                return match[0]
            
        
        # TH nếu ko đánh số
        match = process.extractOne(text_line, self.drugs, scorer = fuzz.token_set_ratio)
        if match:
            drug_name, score = match
            # Ngưỡng 80% và độ dài dòng không quá dài (tránh nhầm cả câu hướng dẫn là tên thuốc)
            if score >= 80 and len(text_line) < 60:
                return drug_name
        
        return None
    
    
    # gom dòng tên thuốc và các dòng phía sau nó vào chung một nhóm
    def segment_blocks(self, lines):
        blocks = []
        current_block = None
        for line in lines:
            drug_name = self.is_drug_name(line)
            if drug_name:
                # nếu phát hiện tên thuốc mới -> đóng gói block cũ (nếu có)
                if current_block:
                    blocks.append(current_block)
                
                current_block = {
                    "drug_name" : drug_name,
                    "lines" : [line]
                }
            
            else:
                # nếu nó không phải tên thuốc -> nó là thông tin bổ sung (liều, số lượng, ..)
                # Gán nó vào block đang mở
                if current_block:
                    current_block["lines"].append(line)
        
        # gán block cuối cùng
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def normalize_text(self, text):
        text = text.lower()
        
        # Bản đồ sửa lỗi (Typos Map)
        replacements = {
            "l/3": "1/3", "l/2": "1/2", "i/2": "1/2",
            "g2.": "2.", "g1.": "1.", "|1.": "1." 
        }
        for wrong, right in replacements.items():
            text = text.replace(wrong, right)
            
        # Xử lý "13" -> "1/3" (Rất nguy hiểm, cần ngữ cảnh)
        # Nếu thấy số 13 đứng cạnh chữ "viên" mà trước đó có chữ "uống" -> Khả năng cao là 1/3
        # Regex: uống 13 viên -> uống 1/3 viên
        text = re.sub(r"(uống|lần)\s+13\s+(viên|gói|chai|ống)", r"\1 1/3 \2", text)
        
        text = self.fuzzy_correct_unit(text)
        
        # Tìm các dòng bắt đầu bằng ký tự lạ rồi đến số chấm (VD: G2. -> 2.)
        lines = text.split('\n')
        normalized_lines = []
        for line in lines:
            # Regex: Ký tự rác + Số + Chấm (VD: G2., |1.) -> Thay bằng Số + Chấm
            line = re.sub(r"^[^0-9a-z]*(\d+)\s*[\.\)]", r"\1.", line.strip())
            normalized_lines.append(line)
            
        return "\n".join(normalized_lines)
        
    
    def extract_info_from_block(self, block): 
        drug_name = block['drug_name']
        full_text = " ".join(block['lines']) 

        info = {
            "name": drug_name,
            "dosage" : "",
            "frequency" : "",
            "total_quantity" : 0,
            "unit" : "viên"
        }
        
        # Tìm hàm lượng (regex: số + đơn vị mg, ml, g)
        dosage_pattern = r"(\d+(?:\.\d+)?(?:\+\d+)?\s*(?:mg|ml|g|mcg|%))"
        dosage_match = re.search(dosage_pattern, full_text, re.IGNORECASE)
        if dosage_match:
            info["dosage"] = dosage_match.group(1)
        
        # Tìm tổng số lượng 
        qty, unit = self.extract_total_quantity(full_text)
        if qty > 0:
            info["total_quantity"] = qty
            info["unit"] = unit
                
                
        # Tìm tần suất
        freq_keywords = ["sáng", "trưa", "chiều", "tối", "lần", "ngày", "uống", "sau ăn", "trước ăn", "mỗi"]
        freq_lines = []
        for line in block["lines"]:
            # Nếu dòng chứa từ khóa Frequency VÀ KHÔNG chứa từ khóa Tổng số (tránh nhầm lẫn)
            if any(k in line.lower() for k in freq_keywords):
                if not re.search(r"(SL|Số lượng|Tổng)", line, re.IGNORECASE):
                    freq_lines.append(line)
                    
        if freq_lines:
            info["frequency"] = ", ".join(freq_lines)
            
        return info
            
    
    def extract_total_quantity(self, full_text):
        temp = full_text
        
        # che đi các con số đi kèm với từ khoá tần suất để ko bắt nhầm
        mask_pattern = r"(mỗi|lần|uống|sáng|trưa|chiều|tối|ngày)\s+(\d+)\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống)?"
        temp = re.sub(mask_pattern, "#", temp)
        
        qty_matches = re.findall(r"(\d+)\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống)", temp, re.IGNORECASE)
        if not qty_matches:
            # Nếu xóa hết rồi mà không còn gì thì quay lại tìm số lớn nhất trong text gốc
            # (Phòng trường hợp OCR thiếu từ khóa "uống" làm logic mask không chạy)
            fallback_matches = re.findall(r"(\d+)\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống)", full_text, re.IGNORECASE)
            max_q = 0
            best_u = "viên"
            for q, u in fallback_matches:
                if int(q) > max_q:
                    max_q = int(q)
                    best_u = u
            return max_q, best_u

        # Nếu còn sót lại số -> Lấy số đầu tiên hoặc số lớn nhất trong đám còn lại
        max_q = 0
        best_u = "viên"
        for q, u in qty_matches:
            if int(q) > max_q:
                max_q = int(q)
                best_u = u
        
        return max_q, best_u
        
        
        
    
        
    
    def analyze(self, raw_text):
        raw_text = self.normalize_text(raw_text)
        cleaned_lines = self.clean_text(raw_text)
        blocks = self.segment_blocks(cleaned_lines)
        results = []
        
        for block in blocks:
            drug_info = self.extract_info_from_block(block)
            results.append(drug_info)
            
        return results
    
    
    
            
        
        
    