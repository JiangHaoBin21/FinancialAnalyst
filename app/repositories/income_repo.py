"""利润表 Repository"""

from typing import Optional, List, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.db_models import Income
from app.repositories.helpers import should_replace_by_update_flag


class IncomeRepository:
    """利润表数据访问层"""

    def create(self, db: Session, income_data: dict) -> Income:
        """
        创建单条利润表记录

        :param db: 数据库 Session
        :param income_data: 利润表字段字典
        :return: 创建后的 Income 对象
        """
        record = Income(**income_data)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def bulk_create(self, db: Session, data: List[dict]) -> List[Income]:
        """
        批量创建利润表记录

        :param db: 数据库 Session
        :param data: 利润表字段字典列表
        :return: 创建后的 Income 对象列表
        """
        records = [Income(**item) for item in data]
        db.add_all(records)
        db.flush()

        for record in records:
            db.refresh(record)

        return records

    def get_by_id(self, db: Session, record_id: int) -> Optional[Income]:
        """
        按主键 ID 查询利润表记录
        """
        stmt = select(Income).where(Income.id == record_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_unique_key(
        self,
        db: Session,
        ts_code: str,
        end_date,
        report_type: Optional[str],
    ) -> Optional[Income]:
        """
        按唯一键查询利润表记录：
        (ts_code, end_date, report_type)
        """
        stmt = select(Income).where(
            Income.ts_code == ts_code,
            Income.end_date == end_date,
            Income.report_type == report_type,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_ts_code(
        self,
        db: Session,
        ts_code: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Income]:
        """
        查询某个股票代码的利润表记录列表（按报告期倒序）
        """
        stmt = (
            select(Income)
            .where(Income.ts_code == ts_code)
            .order_by(desc(Income.end_date), desc(Income.id))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def get_latest_by_ts_code(
        self,
        db: Session,
        ts_code: str,
    ) -> Optional[Income]:
        """
        查询某个股票代码最近一期利润表
        """
        stmt = (
            select(Income)
            .where(Income.ts_code == ts_code)
            .order_by(desc(Income.end_date), desc(Income.id))
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
    ) -> Sequence[Income]:
        """
        查询某个股票代码在指定报告期范围内的利润表记录
        """
        stmt = (
            select(Income)
            .where(
                Income.ts_code == ts_code,
                Income.end_date >= start_date,
                Income.end_date <= end_date,
            )
            .order_by(desc(Income.end_date), desc(Income.id))
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
        判断某条利润表记录是否存在
        """
        stmt = select(Income.id).where(
            Income.ts_code == ts_code,
            Income.end_date == end_date,
            Income.report_type == report_type,
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
    ) -> Optional[Income]:
        """
        按唯一键更新利润表记录
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
        income_data: dict,
    ) -> Income:
        """
        按唯一键执行 upsert：
        - 存在则更新
        - 不存在则插入
        """
        ts_code = income_data["ts_code"]
        end_date = income_data["end_date"]
        report_type = income_data.get("report_type")

        record = self.get_by_unique_key(
            db=db,
            ts_code=ts_code,
            end_date=end_date,
            report_type=report_type,
        )

        if record:
            if not should_replace_by_update_flag(
                    existing_update_flag=record.update_flag,
                    incoming_update_flag=income_data.get("update_flag"),
            ):
                return record
            for field, value in income_data.items():
                if hasattr(record, field):
                    setattr(record, field, value)
            db.flush()
            db.refresh(record)
            return record

        return self.create(db, income_data)

    def bulk_upsert(
        self,
        db: Session,
        data: List[dict],
    ) -> List[Income]:
        """
        批量 upsert 利润表记录
        """
        results = []
        for item in data:
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
        按唯一键删除利润表记录
        """
        record = self.get_by_unique_key(db, ts_code, end_date, report_type)
        if not record:
            return False

        db.delete(record)
        db.flush()
        return True
