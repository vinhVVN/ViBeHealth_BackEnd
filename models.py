from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    # Ta dùng String cho ID thay vì UUID của Postgres để đỡ lỗi extension
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False) # Cần thêm cột này để lưu pass
    role = Column(String, default="patient")
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Thiết lập quan hệ: Một User có nhiều Medication
    medications = relationship("Medication", back_populates="owner")
    
class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True) # ID tự tăng
    name = Column(String, index=True)
    dosage = Column(String)    # Liều lượng (1 viên)
    frequency = Column(String) # Giờ uống (08:00)
    notes = Column(String, nullable=True)
    
    # Khóa ngoại: Thuốc này thuộc về User nào
    user_id = Column(String, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="medications")