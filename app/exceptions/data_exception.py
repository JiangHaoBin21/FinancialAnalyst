"""数据阶段的异常类"""

class MultiRecordException(Exception):
    """多条记录异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class CompanyNotFoundError(Exception):
    """未找到匹配公司。"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)