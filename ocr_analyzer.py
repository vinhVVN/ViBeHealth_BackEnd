import re
from thefuzz import process, fuzz
from drug_database import COMMON_DRUGS, NOISE_KEYWORDS

# Danh sách đơn vị chuẩn
STANDARD_UNITS = ["viên", "vỉ", "hộp", "chai", "lọ", "tuýp", "gói", "ống", "ml", "mg"]

class OCRAnalyzer:
    def __init__(self):
        self.drugs = COMMON_DRUGS
        self.noise = [w.lower() for w in NOISE_KEYWORDS]

    def normalize_text(self, text):
        text = text.lower()
        
        # 1. Map cứng sửa lỗi
        replacements = {
            "l/3": "1/3", "l/2": "1/2", "i/2": "1/2", "|/3": "1/3",
            "g2.": "2.", "g1.": "1.", "|1.": "1.", "1,": "1.",
            "vien": "viên", "goi": "gói", "ong": "ống", "lan": "lần", "làn": "lần",
            "gôi": "gói", "g0i": "gói"
        }
        for wrong, right in replacements.items():
            text = text.replace(wrong, right)

        lines = text.split('\n')
        normalized_lines = []
        for line in lines:
            # 2. Xử lý đầu dòng rác (VD: "G2." -> "2.")
            line = re.sub(r"^[^0-9a-z]*(\d+)\s*[,.\)]", r"\1.", line.strip())
            # 3. Sửa lỗi 13 -> 1/3
            line = re.sub(r"(uống|lần|mỗi)\s+13\s+(viên|gói|chai|ống)", r"\1 1/3 \2", line)
            normalized_lines.append(line)
        
        return "\n".join(normalized_lines)

    def clean_text(self, raw_text):
        lines = raw_text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 2 or not re.search(r'[a-z0-9]', line.lower()): 
                continue
            
            # Logic lọc rác: Nếu dòng bắt đầu bằng số thứ tự (1.) -> GIỮ LẠI LUÔN
            if re.match(r"^\d+\.", line):
                cleaned_lines.append(line)
                continue

            # Nếu không thì check từ khóa rác
            is_noise = False
            for word in self.noise:
                if word in line.lower():
                    is_noise = True
                    break
            
            if not is_noise:
                cleaned_lines.append(line)
                
        return cleaned_lines

    def is_start_of_drug(self, text_line):
        """
        [QUAN TRỌNG] Logic xác định thuốc mới
        """
        # 1. NẾU CÓ SỐ THỨ TỰ (1., 2., 3.) -> CHẮC CHẮN LÀ THUỐC
        # (Bất kể tên thuốc có trong DB hay không)
        if re.match(r"^\d+\.", text_line):
            clean_name = re.sub(r"^\d+\.\s*", "", text_line)
            # Cắt bỏ phần số lượng cuối dòng (Yesom... 63 viên -> Yesom)
            clean_name = re.sub(r"\d+\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống).*$", "", clean_name, flags=re.IGNORECASE)
            
            # Trả về ngay lập tức, không cần check DB
            return clean_name.strip()

        # 2. Nếu không có số thứ tự -> Mới check Database (Fuzzy)
        if len(text_line) > 3:
            match = process.extractOne(text_line, self.drugs, scorer=fuzz.token_set_ratio)
            if match:
                drug_name, score = match
                if score >= 80: 
                    return drug_name
        
        return None

    def segment_blocks(self, lines):
        blocks = []
        current_block = None
        for line in lines:
            drug_name = self.is_start_of_drug(line)
            
            if drug_name:
                # Tìm thấy thuốc mới -> Đóng block cũ
                if current_block: blocks.append(current_block)
                # Mở block mới
                current_block = {"drug_name": drug_name, "lines": [line]}
            else:
                # Không phải thuốc mới -> Là dòng mô tả của thuốc hiện tại
                if current_block: current_block["lines"].append(line)
        
        if current_block: blocks.append(current_block)
        return blocks

    def extract_total_quantity(self, full_text):
        """Chiến thuật Masking (Che số liều dùng)"""
        # 1. Tìm rõ ràng (SL: 20)
        explicit = re.search(r"(?:sl|số lượng|cộng|tổng)[:\.]?\s*(\d+)", full_text, re.IGNORECASE)
        if explicit: return int(explicit.group(1)), "viên"

        # 2. Che các số đi sau từ khóa tần suất
        temp_text = full_text
        mask_pattern = r"(mỗi|lần|uống|sáng|trưa|chiều|tối|ngày)\s+(\d+)"
        temp_text = re.sub(mask_pattern, "FREQ_HIDDEN", temp_text)
        
        # 3. Tìm số còn lại
        qty_matches = re.findall(r"(\d+)\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống)", temp_text, re.IGNORECASE)
        
        # Fallback: Tìm trong text gốc nếu xoá hết
        if not qty_matches:
            qty_matches = re.findall(r"(\d+)\s*(viên|vỉ|hộp|chai|lọ|tuýp|gói|ống)", full_text, re.IGNORECASE)
        
        max_q = 0
        best_u = "viên"
        for q, u in qty_matches:
            val = int(q)
            # Lấy số lớn nhất (hoặc số > 3 để tránh nhầm liều 1,2,3)
            if val > max_q:
                max_q = val
                best_u = u
        
        return max_q, best_u

    def extract_info_from_block(self, block):
        drug_name = block['drug_name']
        full_text = " ".join(block['lines']) 

        info = {
            "name": drug_name,
            "dosage": "",
            "frequency": "",
            "total_quantity": 0,
            "unit": "viên"
        }
        
        # Hàm lượng
        dosage_match = re.search(r"(\d+(?:\.\d+)?(?:\+\d+)?\s*(?:mg|ml|g|mcg|%))", full_text, re.IGNORECASE)
        if dosage_match: info["dosage"] = dosage_match.group(1)
        
        # Tổng số lượng
        qty, unit = self.extract_total_quantity(full_text)
        if qty > 0:
            info["total_quantity"] = qty
            info["unit"] = unit

        # Tần suất
        freq_keywords = ["sáng", "trưa", "chiều", "tối", "lần", "ngày", "uống", "sau ăn", "trước ăn", "mỗi"]
        freq_lines = []
        for line in block["lines"]:
             if any(k in line.lower() for k in freq_keywords):
                # Không lấy dòng chứa tiêu đề 'Số lượng'
                if not re.search(r"(SL|Số lượng|Tổng)", line, re.IGNORECASE):
                    freq_lines.append(line)
        if freq_lines: info["frequency"] = ", ".join(freq_lines)
            
        return info

    def analyze(self, raw_text):
        raw_text = self.normalize_text(raw_text)
        cleaned_lines = self.clean_text(raw_text)
        blocks = self.segment_blocks(cleaned_lines)
        results = []
        for block in blocks:
            drug_info = self.extract_info_from_block(block)
            results.append(drug_info)
        return results