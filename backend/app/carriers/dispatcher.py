from app.carriers.base import BaseCarrier
from app.carriers.jd import JDCarrier
from app.carriers.sf import SFCarrier
from app.carriers.yimi import YimiCarrier
from app.core.config import get_settings


class LogisticsDispatcher:
    carriers = {
        "sf": SFCarrier,
        "jd": JDCarrier,
        "yimi": YimiCarrier,
    }

    def get(self, carrier: str | None = None) -> BaseCarrier:
        code = (carrier or get_settings().default_carrier).lower()
        carrier_class = self.carriers.get(code)
        if carrier_class is None:
            raise ValueError(f"不支持的物流公司：{carrier}")
        return carrier_class()
