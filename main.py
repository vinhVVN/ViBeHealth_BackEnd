from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, get_db
import models
from models import Medication
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from ocr_analyzer import OCRAnalyzer
from utils.logger import log_ocr_input
# from gemini_service import GeminiOCRService
from groq_service import GroqOCRService

# Tự động tạo bảng trong DB nếu chưa có
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
groqservice= GroqOCRService()
regex_analyzer = OCRAnalyzer()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi nơi gọi vào (hoặc điền cụ thể domain nếu cần bảo mật cao)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Định nghĩa dữ liệu đầu vào (Schema)
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

# Schema dữ liệu đầu vào (Validation)
class MedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    notes: str | None = None
    total_quantity: int = 0
    unit: str = "viên"

# Schema nhận dữ liệu từ Android
class OCRRequest(BaseModel):
    raw_text: str
    
# Khởi tạo analyzer 1 lần để dùng mãi
analyzer = OCRAnalyzer()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
def get_current_user_email(token: str = Depends(oauth2_scheme)):
    # Đây là nơi giải mã Token. Tạm thời ta trả về email giả định hoặc decode thật nếu bạn muốn.
    # Logic giả: Token chính là email (để test nhanh)
    return "admin@test.com" # Hardcode để test luồng dữ liệu trước



# API Đăng ký (Test chơi để tạo user)
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Logic: Hash password rồi lưu vào DB (sẽ làm chi tiết sau)
    # Tạm thời lưu thô để test kết nối trước
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password, full_name=user.full_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# API Đăng nhập (Cái Android cần)
@app.post("/api/auth/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Tìm user trong DB
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect email")
    if db_user.hashed_password != user.password + "notreallyhashed":
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    # Trả về Token giả (Giai đoạn sau sẽ làm JWT thật)
    return {"access_token": "fake-jwt-token-cho-android-test", "token_type": "bearer", "role": db_user.role}


# API Thêm thuốc
@app.post("/api/medications")
def create_medication(
    med: MedicationCreate, 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    # Tìm user chủ sở hữu (Ở đây tôi hardcode lấy user đầu tiên trong DB để demo)
    # Giai đoạn sau ta sẽ lấy đúng user từ Token
    user = db.query(models.User).first() 
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_med = models.Medication(
        name=med.name,
        dosage=med.dosage,
        frequency=med.frequency,
        notes=med.notes,
        user_id=user.id, # Gán thuốc cho user này
        total_quantity= med.total_quantity,
        unit=med.unit
    )
    db.add(new_med)
    db.commit()
    db.refresh(new_med)
    return {"status": "success", "id": new_med.id}

# API Lấy danh sách thuốc của tôi
@app.get("/api/medications")
def get_my_medications(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).first() # Demo lấy user đầu tiên
    return user.medications


@app.post("/api/ocr/analyze")
def analyze_ocr(request: OCRRequest):
    
    try:
        print("🚀 Đang gọi Groq AI...")
        results = groqservice.analyze_prescription(request.raw_text)
        
        if results and len(results) > 0:
            print(f"✅ Groq thành công! Tìm thấy {len(results)} thuốc.")
            return {
                "status": "success", 
                "method": "GROQ_LLAMA3", 
                "data": results
            }
        else:
            print("⚠️ Groq trả về rỗng.")
            
    except Exception as e:
        print(f"❌ Groq Critical Error: {e}")

    # CHIẾN THUẬT 2: Fallback về Regex (Cổ điển, Ổn định, Offline logic)
    print("🔧 Chuyển sang chế độ Regex Fallback...")
    results = regex_analyzer.analyze(request.raw_text)
    
    return {
        "status": "success", 
        "method": "REGEX_ALGORITHM", 
        "data": results
    }