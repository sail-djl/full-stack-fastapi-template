"""偏振模型相关业务逻辑服务"""
import uuid
from typing import Any
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlmodel import Session, select, func

from app.models import Polarization, PolarizationCreate, PolarizationUpdate, Deviation, DeviationCreate


class PolarizationService:
    """偏振模型业务逻辑服务"""

    @staticmethod
    def get_polarization(
        session: Session, etf1_code: str, etf2_code: str
    ) -> Polarization | None:
        """
        获取偏振度数据
        """
        statement = select(Polarization).where(
            Polarization.etf1_code == etf1_code,
            Polarization.etf2_code == etf2_code
        )
        return session.exec(statement).first()

    @staticmethod
    def create_or_update_polarization(
        session: Session, polarization_in: PolarizationCreate
    ) -> Polarization:
        """
        创建或更新偏振度数据
        """
        existing = PolarizationService.get_polarization(
            session=session,
            etf1_code=polarization_in.etf1_code,
            etf2_code=polarization_in.etf2_code
        )
        
        if existing:
            # 更新
            for field, value in polarization_in.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # 创建
            polarization = Polarization.model_validate(polarization_in)
            session.add(polarization)
            session.commit()
            session.refresh(polarization)
            return polarization


class DeviationService:
    """偏差数据业务逻辑服务"""

    @staticmethod
    def get_deviations(
        session: Session,
        etf1_code: str,
        etf2_code: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 1000
    ) -> tuple[list[Deviation], int]:
        """
        获取偏差数据
        """
        statement = select(Deviation).where(
            Deviation.etf1_code == etf1_code,
            Deviation.etf2_code == etf2_code
        )
        
        if start_date:
            statement = statement.where(Deviation.date >= start_date)
        if end_date:
            statement = statement.where(Deviation.date <= end_date)
        
        statement = statement.order_by(Deviation.date.desc())
        
        count_statement = select(func.count()).select_from(Deviation).where(
            Deviation.etf1_code == etf1_code,
            Deviation.etf2_code == etf2_code
        )
        if start_date:
            count_statement = count_statement.where(Deviation.date >= start_date)
        if end_date:
            count_statement = count_statement.where(Deviation.date <= end_date)
        
        count = session.exec(count_statement).one()
        deviations = session.exec(statement.offset(skip).limit(limit)).all()
        
        return list(deviations), count

    @staticmethod
    def create_deviation(
        session: Session, deviation_in: DeviationCreate
    ) -> Deviation:
        """
        创建偏差数据
        """
        deviation = Deviation.model_validate(deviation_in)
        session.add(deviation)
        session.commit()
        session.refresh(deviation)
        return deviation

