"""公司维表 Repository"""

from typing import Optional, List, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.db_models import Company


class CompanyRepository:
    """公司维表数据访问层"""

    def create(self, db: Session, company_data: dict) -> Company:
        """
        创建单个公司记录

        :param db: 数据库 Session
        :param company_data: 公司字段字典
        :return: 创建后的 Company 对象
        """
        company = Company(**company_data)
        db.add(company)
        db.flush()   # 先 flush，拿到主键等信息
        db.refresh(company)
        return company

    def bulk_create(self, db: Session, companies_data: List[dict]) -> List[Company]:
        """
        批量创建公司记录

        :param db: 数据库 Session
        :param companies_data: 公司字段字典列表
        :return: 创建后的 Company 对象列表
        """
        companies = [Company(**item) for item in companies_data]
        db.add_all(companies)
        db.flush()

        for company in companies:
            db.refresh(company)

        return companies

    def get_by_id(self, db: Session, company_id: int) -> Optional[Company]:
        """
        按主键 ID 查询公司
        """
        stmt = select(Company).where(Company.id == company_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_ts_code(self, db: Session, ts_code: str) -> Optional[Company]:
        """
        按 ts_code 查询公司
        """
        stmt = select(Company).where(Company.ts_code == ts_code)
        return db.execute(stmt).scalar_one_or_none()

    def exists_by_ts_code(self, db: Session, ts_code: str) -> bool:
        """
        判断某个 ts_code 是否已存在
        """
        stmt = select(Company.id).where(Company.ts_code == ts_code)
        result = db.execute(stmt).first()
        return result is not None

    def list_all(self, db: Session, limit: int = 100, offset: int = 0) -> Sequence[Company]:
        """
        查询公司列表
        """
        stmt = (
            select(Company)
            .order_by(Company.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def list_active(self, db: Session, limit: int = 100, offset: int = 0) -> Sequence[Company]:
        """
        查询有效公司列表
        """
        stmt = (
            select(Company)
            .where(Company.is_active.is_(True))
            .order_by(Company.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    def update_by_ts_code(self, db: Session, ts_code: str, update_data: dict) -> Optional[Company]:
        """
        按 ts_code 更新公司信息

        :param db: 数据库 Session
        :param ts_code: 股票代码
        :param update_data: 待更新字段
        :return: 更新后的 Company；不存在则返回 None
        """
        company = self.get_by_ts_code(db, ts_code)
        if not company:
            return None

        for field, value in update_data.items():
            if hasattr(company, field):
                setattr(company, field, value)

        db.flush()
        db.refresh(company)
        return company

    def upsert_by_ts_code(self, db: Session, company_data: dict) -> Company:
        """
        按 ts_code 执行 upsert：
        - 存在则更新
        - 不存在则插入
        """
        ts_code = company_data["ts_code"]
        company = self.get_by_ts_code(db, ts_code)

        if company:
            for field, value in company_data.items():
                if hasattr(company, field):
                    setattr(company, field, value)
            db.flush()
            db.refresh(company)
            return company

        return self.create(db, company_data)

    def delete_by_ts_code(self, db: Session, ts_code: str) -> bool:
        """
        按 ts_code 删除公司记录

        :return: 删除成功返回 True，不存在返回 False
        """
        company = self.get_by_ts_code(db, ts_code)
        if not company:
            return False

        db.delete(company)
        db.flush()
        return True
