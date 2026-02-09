

# Danh sách thuốc mẫu
# Mẹo: Nên ưu tiên các thuốc thông dụng tại Việt Nam
COMMON_DRUGS = [
    "Panadol", "Panadol Extra", "Panadol Cảm Cúm",
    "Paracetamol", "Efferalgan", "Hapacol",
    "Aspirin", "Ibuprofen", "Decolgen", "Tiffy",
    "Berberin", "Smecta", "Oresol",
    "Amoxicillin", "Cephalexin", "Augmentin",
    "Metformin", "Insulin", "Glucophage",
    "Amlodipin", "Losartan", "Concor",
    "Omeprazol", "Gaviscon", "Phosphalugel",
    "Vitamin C", "Vitamin B1", "Vitamin B12", "Multivitamin",
    "Hoạt Huyết Dưỡng Não", "Boganic", "Yesom", "sucrate gel", "arthur", "papaze",
    "biocid mh", "diglumisan" 
]

# Danh sách các từ khóa gây nhiễu cần loại bỏ (Rác OCR)
NOISE_KEYWORDS = [
    "nsx", "hsd", "số lô", "lô sx", "mfg", "exp", 
    "nhà thuốc", "pharmacy", "bác sĩ", "chẩn đoán",
    "ngày sinh", "địa chỉ", "tel", "fax", "email",
    "đơn thuốc", "toa thuốc", "bệnh viện"
]