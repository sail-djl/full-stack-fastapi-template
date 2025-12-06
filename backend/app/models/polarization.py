from __future__ import annotations

import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel


# ============================================
# Polarization (偏振模型) 相关模型
# ============================================
class PolarizationBase(SQLModel):
    etf1_code: str = Field(max_length=20, index=True)
    etf2_code: str = Field(max_length=20, index=True)
    current_polarization: float
    avg_polarization: float  # 3年平均偏振度
    status: str = Field(max_length=20)  # low, moderate, high
    trend: str = Field(max_length=20)  # rising, falling, stable


class PolarizationCreate(PolarizationBase):
    pass


class PolarizationUpdate(SQLModel):
    current_polarization: float | None = None
    avg_polarization: float | None = None
    status: str | None = None
    trend: str | None = None


class Polarization(PolarizationBase, table=True):
    __tablename__ = "polarization"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class PolarizationPublic(PolarizationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PolarizationsPublic(SQLModel):
    data: list[PolarizationPublic]
    count: int


# ============================================
# Deviation (偏差数据) 相关模型
# ============================================
class DeviationBase(SQLModel):
    etf1_code: str = Field(max_length=20, index=True)
    etf2_code: str = Field(max_length=20, index=True)
    date: datetime
    deviation: float
    etf1_price: float
    etf2_price: float


class DeviationCreate(DeviationBase):
    pass


class Deviation(DeviationBase, table=True):
    __tablename__ = "deviation"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class DeviationPublic(DeviationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DeviationsPublic(SQLModel):
    data: list[DeviationPublic]
    count: int



