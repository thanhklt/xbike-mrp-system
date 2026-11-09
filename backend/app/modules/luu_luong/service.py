"""Build the traffic series the admin overview chart draws."""

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.luu_luong.ports import LuuLuongReader
from app.modules.luu_luong.schemas import (
    DiemLuuLuong,
    KhoangThoiGian,
    LuuLuongRead,
    LuuLuongResponse,
    ResponseMeta,
)

TIMEZONE = "Asia/Ho_Chi_Minh"
LOCAL_TZ = ZoneInfo(TIMEZONE)
SO_NGAY: dict[str, int] = {"7_ngay": 7, "30_ngay": 30}
CUA_SO_TRUNG_BINH = 7


def moving_average_7(values: Sequence[int]) -> list[float]:
    """Average of each value and the 6 before it; the first 6 values only feed the window."""
    window = CUA_SO_TRUNG_BINH
    return [
        round(sum(values[index - window + 1 : index + 1]) / window, 1)
        for index in range(window - 1, len(values))
    ]


def _local_midnight_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=LOCAL_TZ).astimezone(UTC)


class LuuLuongService:
    def __init__(
        self, reader: LuuLuongReader, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ):
        self.reader = reader
        self.clock = clock

    async def get_series(self, khoang: KhoangThoiGian, request_id: str) -> LuuLuongResponse:
        today = self.clock().astimezone(LOCAL_TZ).date()
        den = _local_midnight_utc(today + timedelta(days=1))
        if khoang == "hom_nay":
            tu = _local_midnight_utc(today)
            diem = await self._by_hour(tu, den)
        else:
            tu = _local_midnight_utc(today - timedelta(days=SO_NGAY[khoang] - 1))
            diem = await self._by_day(khoang, today, den)
        data = LuuLuongRead(
            khoang_thoi_gian=khoang,
            buoc="gio" if khoang == "hom_nay" else "ngay",
            timezone=TIMEZONE,
            tu_thoi_diem=tu,
            den_thoi_diem_exclusive=den,
            tong_request=sum(point.so_request or 0 for point in diem),
            diem=diem,
        )
        return LuuLuongResponse(data=data, meta=ResponseMeta(request_id=request_id))

    async def _by_hour(self, tu: datetime, den: datetime) -> list[DiemLuuLuong]:
        counts = await self.reader.sum_by_hour(tu, den)
        now = self.clock()
        points = []
        for hour in range(24):
            start = tu + timedelta(hours=hour)
            # Hours not reached yet are null so the line stops at the current hour.
            value = None if start > now else counts.get(start, 0)
            points.append(DiemLuuLuong(bat_dau=start, so_request=value, trung_binh_7_ngay=None))
        return points

    async def _by_day(
        self, khoang: KhoangThoiGian, today: date, den: datetime
    ) -> list[DiemLuuLuong]:
        so_ngay = SO_NGAY[khoang]
        # 30 days also reads the 6 days before so every shown day has a full 7-day average.
        extra = CUA_SO_TRUNG_BINH - 1 if khoang == "30_ngay" else 0
        first = today - timedelta(days=so_ngay - 1 + extra)
        counts = await self.reader.sum_by_day(_local_midnight_utc(first), den, TIMEZONE)
        days = [first + timedelta(days=offset) for offset in range(so_ngay + extra)]
        values = [counts.get(day, 0) for day in days]
        averages: list[float | None] = list(moving_average_7(values)) if extra else [None] * so_ngay
        return [
            DiemLuuLuong(
                bat_dau=_local_midnight_utc(day), so_request=value, trung_binh_7_ngay=average
            )
            for day, value, average in zip(days[extra:], values[extra:], averages, strict=True)
        ]
