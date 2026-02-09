from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import zipfile


@dataclass(frozen=True)
class GtfsServiceDateRange:
    min_yyyymmdd: Optional[str]
    max_yyyymmdd: Optional[str]
    has_calendar: bool
    has_calendar_dates: bool

    def is_empty(self) -> bool:
        return not self.min_yyyymmdd or not self.max_yyyymmdd

    def min_date(self) -> Optional[date]:
        if not self.min_yyyymmdd:
            return None
        return datetime.strptime(self.min_yyyymmdd, "%Y%m%d").date()

    def max_date(self) -> Optional[date]:
        if not self.max_yyyymmdd:
            return None
        return datetime.strptime(self.max_yyyymmdd, "%Y%m%d").date()


def read_gtfs_service_date_range(gtfs_zip: Path) -> GtfsServiceDateRange:
    """Return min/max dates present in calendar/calendar_dates.

    It's a pragmatic helper for choosing an r5py `departure` within the GTFS service range.
    """
    if not gtfs_zip.exists():
        raise FileNotFoundError(gtfs_zip)

    with zipfile.ZipFile(gtfs_zip) as zf:
        names = set(zf.namelist())

        dates = []
        has_calendar = "calendar.txt" in names
        has_calendar_dates = "calendar_dates.txt" in names

        if has_calendar:
            cal = pd.read_csv(zf.open("calendar.txt"))
            for col in ("start_date", "end_date"):
                if col in cal.columns:
                    dates += cal[col].dropna().astype(str).tolist()

        if has_calendar_dates:
            cd = pd.read_csv(zf.open("calendar_dates.txt"))
            if "date" in cd.columns:
                dates += cd["date"].dropna().astype(str).tolist()

    dates = [d for d in dates if isinstance(d, str) and d.isdigit() and len(d) == 8]
    if not dates:
        return GtfsServiceDateRange(None, None, has_calendar, has_calendar_dates)

    return GtfsServiceDateRange(min(dates), max(dates), has_calendar, has_calendar_dates)


def _read_gtfs_tables_from_zip(gtfs_zip: Path) -> dict[str, pd.DataFrame]:
    """Read calendar/calendar_dates from a GTFS zip if present."""
    if not gtfs_zip.exists():
        raise FileNotFoundError(gtfs_zip)

    out: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(gtfs_zip) as zf:
        names = set(zf.namelist())
        if "calendar.txt" in names:
            out["calendar"] = pd.read_csv(zf.open("calendar.txt"))
        if "calendar_dates.txt" in names:
            out["calendar_dates"] = pd.read_csv(zf.open("calendar_dates.txt"))
    return out


def gtfs_has_any_service_on_date(gtfs_zip: Path, yyyymmdd: str) -> bool:
    """Return True if any service is active on the given date.

    Uses GTFS calendar.txt (weekly schedule) + calendar_dates.txt exceptions.
    Pragmatic: we only need to know whether *anything* runs that day.
    """
    if not (isinstance(yyyymmdd, str) and yyyymmdd.isdigit() and len(yyyymmdd) == 8):
        raise ValueError(f"Invalid yyyymmdd: {yyyymmdd}")

    tables = _read_gtfs_tables_from_zip(gtfs_zip)
    cal = tables.get("calendar")
    cd = tables.get("calendar_dates")

    d = datetime.strptime(yyyymmdd, "%Y%m%d").date()

    # calendar-based services
    active: set[str] = set()
    if cal is not None and len(cal) > 0:
        cal2 = cal.copy()
        # normalize
        cal2["start_date"] = pd.to_numeric(cal2.get("start_date"), errors="coerce")
        cal2["end_date"] = pd.to_numeric(cal2.get("end_date"), errors="coerce")
        di = int(yyyymmdd)

        wd = d.weekday()  # Mon=0..Sun=6
        wd_col = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][wd]
        if wd_col in cal2.columns:
            mask = (cal2["start_date"].notna()) & (cal2["end_date"].notna())
            mask &= (cal2["start_date"] <= di) & (cal2["end_date"] >= di)
            mask &= (pd.to_numeric(cal2[wd_col], errors="coerce").fillna(0).astype(int) == 1)
            if "service_id" in cal2.columns:
                active |= set(cal2.loc[mask, "service_id"].astype(str).tolist())

    # apply calendar_dates exceptions
    if cd is not None and len(cd) > 0 and "date" in cd.columns and "service_id" in cd.columns:
        cd2 = cd.copy()
        cd2["date"] = cd2["date"].astype(str)
        day_rows = cd2[cd2["date"] == yyyymmdd]
        if len(day_rows) > 0:
            # exception_type: 1=added, 2=removed
            if "exception_type" in day_rows.columns:
                added = set(day_rows[pd.to_numeric(day_rows["exception_type"], errors="coerce").fillna(0).astype(int) == 1]["service_id"].astype(str))
                removed = set(day_rows[pd.to_numeric(day_rows["exception_type"], errors="coerce").fillna(0).astype(int) == 2]["service_id"].astype(str))
                active |= added
                active -= removed
            else:
                # if exception_type missing, assume listed services are active
                active |= set(day_rows["service_id"].astype(str))

    # If no calendar but there are explicit calendar_dates, treat exception_type=1 as active
    if (cal is None or len(active) == 0) and cd is not None and len(cd) > 0:
        cd2 = cd.copy()
        cd2["date"] = cd2["date"].astype(str)
        day_rows = cd2[cd2["date"] == yyyymmdd]
        if len(day_rows) > 0:
            if "exception_type" in day_rows.columns:
                if (pd.to_numeric(day_rows["exception_type"], errors="coerce").fillna(0).astype(int) == 1).any():
                    return True
            else:
                return True

    return len(active) > 0


def choose_service_day_within_gtfs(
    gtfs_zip: Path,
    prefer_weekdays: bool = True,
    prefer: str = "recent",
    search_days: int = 60,
) -> str:
    """Choose a yyyymmdd inside GTFS range that is an actual service day.

    Starts from a linkable "anchor" date (similar to choose_departure_datetime_within_gtfs)
    and searches forward/backward for a date where any service is active.
    """
    rng = read_gtfs_service_date_range(gtfs_zip)
    if rng.is_empty():
        raise ValueError(f"No service dates found in {gtfs_zip}")

    # anchor day
    if prefer == "min":
        anchor = datetime.strptime(rng.min_yyyymmdd, "%Y%m%d").date()
        direction = +1
    elif prefer == "max":
        anchor = datetime.strptime(rng.max_yyyymmdd, "%Y%m%d").date()
        direction = -1
    elif prefer == "mid":
        min_d = rng.min_date(); max_d = rng.max_date()
        mid_d = min_d + (max_d - min_d) / 2
        anchor = mid_d
        direction = -1
    else:  # recent
        max_d = rng.max_date()
        today = date.today()
        if max_d and max_d > today:
            min_d = rng.min_date()
            anchor = today if (min_d and min_d <= today <= max_d) else max_d
        else:
            anchor = max_d
        direction = -1

    min_d = rng.min_date(); max_d = rng.max_date()

    def ok_weekday(d: date) -> bool:
        return (d.weekday() <= 4) if prefer_weekdays else True

    # try anchor first, then search around
    for delta in range(0, int(search_days) + 1):
        for cand in [anchor + direction * delta * pd.Timedelta(days=1), anchor - direction * delta * pd.Timedelta(days=1)]:
            # pd.Timedelta returns Timestamp-like; normalize
            if hasattr(cand, "date"):
                cand = cand.date()  # type: ignore[assignment]
            if cand < min_d or cand > max_d:
                continue
            yyyymmdd = cand.strftime("%Y%m%d")
            if prefer_weekdays and not ok_weekday(cand):
                continue
            try:
                if gtfs_has_any_service_on_date(gtfs_zip, yyyymmdd):
                    return yyyymmdd
            except Exception:
                continue

    # fallback: ignore weekday preference
    if prefer_weekdays:
        for delta in range(0, int(search_days) + 1):
            for cand in [anchor + direction * delta * pd.Timedelta(days=1), anchor - direction * delta * pd.Timedelta(days=1)]:
                if hasattr(cand, "date"):
                    cand = cand.date()  # type: ignore[assignment]
                if cand < min_d or cand > max_d:
                    continue
                yyyymmdd = cand.strftime("%Y%m%d")
                try:
                    if gtfs_has_any_service_on_date(gtfs_zip, yyyymmdd):
                        return yyyymmdd
                except Exception:
                    continue

    # as a last resort, return anchor even if no service detected
    return anchor.strftime("%Y%m%d")


def choose_departure_datetimes(
    gtfs_zip: Path,
    time_hhmmss_list: Iterable[str],
    prefer_weekdays: bool = True,
    prefer: str = "recent",
) -> list[datetime]:
    """Return a list of departure datetimes that are within range and on a service day."""
    yyyymmdd = choose_service_day_within_gtfs(gtfs_zip, prefer_weekdays=prefer_weekdays, prefer=prefer)
    d = datetime.strptime(yyyymmdd, "%Y%m%d").date()
    out: list[datetime] = []
    for t in time_hhmmss_list:
        hh, mm, ss = (int(x) for x in str(t).split(":"))
        out.append(datetime(d.year, d.month, d.day, hh, mm, ss))
    return out


def choose_departure_datetime_within_gtfs(
    gtfs_zip: Path,
    time_hhmmss: str = "08:00:00",
    prefer: str = "min",
) -> datetime:
    """Choose a departure datetime that won't trigger 'outside of GTFS time range' warnings.

    prefer:
    - 'min': picks min service date
    - 'max': picks max service date
    - 'mid': picks middle of service date range
    - 'recent': picks most recent date that's not too far in future
    """
    rng = read_gtfs_service_date_range(gtfs_zip)
    if rng.is_empty():
        raise ValueError(f"No service dates found in {gtfs_zip}")

    if prefer == "min":
        chosen = rng.min_yyyymmdd
    elif prefer == "max":
        chosen = rng.max_yyyymmdd
    elif prefer == "mid":
        # Pick middle of range
        min_d = rng.min_date()
        max_d = rng.max_date()
        mid_d = min_d + (max_d - min_d) / 2
        chosen = mid_d.strftime("%Y%m%d")
    elif prefer == "recent":
        # Pick most recent date that's not too far in future (within 1 year from now)
        max_d = rng.max_date()
        today = date.today()
        if max_d and max_d > today:
            # If max is in future, use today if in range, else use max
            min_d = rng.min_date()
            if min_d <= today <= max_d:
                chosen = today.strftime("%Y%m%d")
            else:
                chosen = rng.max_yyyymmdd
        else:
            chosen = rng.max_yyyymmdd
    else:
        chosen = rng.min_yyyymmdd

    hh, mm, ss = (int(x) for x in time_hhmmss.split(":"))
    d = datetime.strptime(chosen, "%Y%m%d").date()
    return datetime(d.year, d.month, d.day, hh, mm, ss)
