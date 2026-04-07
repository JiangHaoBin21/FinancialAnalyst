"""财务指标表 Repository"""

from typing import Optional, List, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.db_models import FinaIndicator


class FinaIndicatorRepository:
    """财务指标表数据访问层"""

    def create(self, db: Session, indicator_data: dict) -> FinaIndicator:
        """
        创建单条财务指标记录

        :param db: 数据库 Session
        :param indicator_data: 财务指标字段字典
        :return: 创建后的 FinaIndicator 对象
        """
        record = FinaIndicator(**indicator_data)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def bulk_create(self, db: Session, indicators_data: List[dict]) -> List[FinaIndicator]:
        """
        批量创建财务指标记录

        :param db: 数据库 Session
        :param indicators_data: 财务指标字段字典列表
        :return: 创建后的 FinaIndicator 对象列表
        """
        records = [FinaIndicator(**item) for item in indicators_data]
        db.add_all(records)
        db.flush()

        for record in records:
            db.refresh(record)

        return records

    def get_by_id(self, db: Session, record_id: int) -> Optional[FinaIndicator]:
        """
        按主键 ID 查询财务指标记录
        """
        stmt = select(FinaIndicator).where(FinaIndicator.id == record_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
    ) -> Optional[FinaIndicator]:
        """
        按唯一键查询财务指标记录：
        (ts_code, end_date)
        """
        stmt = select(FinaIndicator).where(
            FinaIndicator.ts_code == ts_code,
            FinaIndicator.end_date == end_date,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_ts_code(
        self,
        db: Session,
        ts_code: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[FinaIndicator]:
        """
        查询某个股票代码的财务指标记录列表（按报告期倒序）
        """
        stmt = (
            select(FinaIndicator)
            .where(FinaIndicator.ts_code == ts_code)
            .order_by(desc(FinaIndicator.end_date), desc(FinaIndicator.id))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def get_latest_by_ts_code(
        self,
        db: Session,
        ts_code: str,
    ) -> Optional[FinaIndicator]:
        """
        查询某个股票代码最近一期财务指标
        """
        stmt = (
            select(FinaIndicator)
            .where(FinaIndicator.ts_code == ts_code)
            .order_by(desc(FinaIndicator.end_date), desc(FinaIndicator.id))
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_ts_code_and_date_range(
        self,
        db: Session,
        ts_code: str,
        start_date,
        end_date,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[FinaIndicator]:
        """
        查询某个股票代码在指定报告期范围内的财务指标记录
        """
        stmt = (
            select(FinaIndicator)
            .where(
                FinaIndicator.ts_code == ts_code,
                FinaIndicator.end_date >= start_date,
                FinaIndicator.end_date <= end_date,
            )
            .order_by(desc(FinaIndicator.end_date), desc(FinaIndicator.id))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def exists_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
    ) -> bool:
        """
        判断某条财务指标记录是否存在
        """
        stmt = select(FinaIndicator.id).where(
            FinaIndicator.ts_code == ts_code,
            FinaIndicator.end_date == end_date,
        )
        result = db.execute(stmt).first()
        return result is not None

    def update_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        update_data: dict,
    ) -> Optional[FinaIndicator]:
        """
        按唯一键更新财务指标记录
        """
        record = self.get_by_unique_key(db, ts_code, end_date)
        if not record:
            return None

        for field, value in update_data.items():
            if hasattr(record, field):
                setattr(record, field, value)

        db.flush()
        db.refresh(record)
        return record

    def upsert(
        self,
        db: Session,
        indicator_data: dict,
    ) -> FinaIndicator:
        """
        按唯一键执行 upsert：
        - 存在则更新
        - 不存在则插入
        """
        ts_code = indicator_data["ts_code"]
        end_date = indicator_data["end_date"]

        record = self.get_by_unique_key(
            db=db,
            ts_code=ts_code,
            end_date=end_date,
        )

        if record:
            for field, value in indicator_data.items():
                if hasattr(record, field):
                    setattr(record, field, value)
            db.flush()
            db.refresh(record)
            return record

        return self.create(db, indicator_data)

    def bulk_upsert(
        self,
        db: Session,
        indicators_data: List[dict],
    ) -> List[FinaIndicator]:
        """
        批量 upsert 财务指标记录
        """
        results = []
        for item in indicators_data:
            record = self.upsert(db, item)
            results.append(record)
        return results

    def delete_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
    ) -> bool:
        """
        按唯一键删除财务指标记录
        """
        record = self.get_by_unique_key(db, ts_code, end_date)
        if not record:
            return False

        db.delete(record)
        db.flush()
        return True
