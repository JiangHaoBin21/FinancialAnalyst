"""资产负债表 Repository"""

from typing import Optional, List, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.db_models import BalanceSheet


class BalanceSheetRepository:
    """资产负债表数据访问层"""

    def create(self, db: Session, balance_data: dict) -> BalanceSheet:
        """
        创建单条资产负债表记录

        :param db: 数据库 Session
        :param balance_data: 资产负债表字段字典
        :return: 创建后的 BalanceSheet 对象
        """
        record = BalanceSheet(**balance_data)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def bulk_create(self, db: Session, balances_data: List[dict]) -> List[BalanceSheet]:
        """
        批量创建资产负债表记录

        :param db: 数据库 Session
        :param balances_data: 资产负债表字段字典列表
        :return: 创建后的 BalanceSheet 对象列表
        """
        records = [BalanceSheet(**item) for item in balances_data]
        db.add_all(records)
        db.flush()

        for record in records:
            db.refresh(record)

        return records

    def get_by_id(self, db: Session, record_id: int) -> Optional[BalanceSheet]:
        """
        按主键 ID 查询资产负债表记录
        """
        stmt = select(BalanceSheet).where(BalanceSheet.id == record_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        report_type: Optional[str],
    ) -> Optional[BalanceSheet]:
        """
        按唯一键查询资产负债表记录：
        (ts_code, end_date, report_type)
        """
        stmt = select(BalanceSheet).where(
            BalanceSheet.ts_code == ts_code,
            BalanceSheet.end_date == end_date,
            BalanceSheet.report_type == report_type,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_ts_code(
        self,
        db: Session,
        ts_code: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[BalanceSheet]:
        """
        查询某个股票代码的资产负债表记录列表（按报告期倒序）
        """
        stmt = (
            select(BalanceSheet)
            .where(BalanceSheet.ts_code == ts_code)
            .order_by(desc(BalanceSheet.end_date), desc(BalanceSheet.id))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def get_latest_by_ts_code(
        self,
        db: Session,
        ts_code: str,
    ) -> Optional[BalanceSheet]:
        """
        查询某个股票代码最近一期资产负债表
        """
        stmt = (
            select(BalanceSheet)
            .where(BalanceSheet.ts_code == ts_code)
            .order_by(desc(BalanceSheet.end_date), desc(BalanceSheet.id))
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
    ) -> Sequence[BalanceSheet]:
        """
        查询某个股票代码在指定报告期范围内的资产负债表记录
        """
        stmt = (
            select(BalanceSheet)
            .where(
                BalanceSheet.ts_code == ts_code,
                BalanceSheet.end_date >= start_date,
                BalanceSheet.end_date <= end_date,
            )
            .order_by(desc(BalanceSheet.end_date), desc(BalanceSheet.id))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def exists_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        report_type: Optional[str],
    ) -> bool:
        """
        判断某条资产负债表记录是否存在
        """
        stmt = select(BalanceSheet.id).where(
            BalanceSheet.ts_code == ts_code,
            BalanceSheet.end_date == end_date,
            BalanceSheet.report_type == report_type,
        )
        result = db.execute(stmt).first()
        return result is not None

    def update_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        report_type: Optional[str],
        update_data: dict,
    ) -> Optional[BalanceSheet]:
        """
        按唯一键更新资产负债表记录
        """
        record = self.get_by_unique_key(db, ts_code, end_date, report_type)
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
        balance_data: dict,
    ) -> BalanceSheet:
        """
        按唯一键执行 upsert：
        - 存在则更新
        - 不存在则插入
        """
        ts_code = balance_data["ts_code"]
        end_date = balance_data["end_date"]
        report_type = balance_data.get("report_type")

        record = self.get_by_unique_key(
            db=db,
            ts_code=ts_code,
            end_date=end_date,
            report_type=report_type,
        )

        if record:
            for field, value in balance_data.items():
                if hasattr(record, field):
                    setattr(record, field, value)
            db.flush()
            db.refresh(record)
            return record

        return self.create(db, balance_data)

    def bulk_upsert(
        self,
        db: Session,
        balances_data: List[dict],
    ) -> List[BalanceSheet]:
        """
        批量 upsert 资产负债表记录
        """
        results = []
        for item in balances_data:
            record = self.upsert(db, item)
            results.append(record)
        return results

    def delete_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        report_type: Optional[str],
    ) -> bool:
        """
        按唯一键删除资产负债表记录
        """
        record = self.get_by_unique_key(db, ts_code, end_date, report_type)
        if not record:
            return False

        db.delete(record)
        db.flush()
        return True
