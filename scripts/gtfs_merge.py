from __future__ import annotations

import csv
import io
import json
import math
import shutil
import warnings
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


# GTFS Merger z diagnostyką intersekcji dat, filtracją calendar_dates
# i generacją transferów między operatorami.
#
# Kontrakt:
# - Wejście: lista plików ZIP GTFS dla jednego regionu.
# - Wyjście: jeden ZIP GTFS ładowalny przez R5 + raport diagnostyczny (JSON).
# - Strategia: konkatenacja tabel, prefiksy ID per feed, intersekcja dat,
#   opcjonalna generacja transferów walking między operatorami.


GTFS_TABLES = [
    "agency.txt",
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "fare_attributes.txt",
    "fare_rules.txt",
    "shapes.txt",
    "frequencies.txt",
    "transfers.txt",
    "feed_info.txt",
]


@dataclass
class FeedDiagnostic:
    path: str
    prefix: str
    tables_present: list[str] = field(default_factory=list)
    tables_missing: list[str] = field(default_factory=list)
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    calendar_type: Optional[str] = None  # 'calendar', 'calendar_dates', 'both', 'none'
    n_stops: int = 0
    n_routes: int = 0
    n_trips: int = 0
    n_stop_times: int = 0
    route_types: dict = field(default_factory=dict)
    has_transfers: bool = False
    has_shapes: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class MergeStats:
    out_zip: Path
    in_zips: list[Path]
    tables_written: list[str]
    date_intersection: tuple[Optional[str], Optional[str]] = (None, None)
    feed_diagnostics: list[FeedDiagnostic] = field(default_factory=list)
    merge_warnings: list[str] = field(default_factory=list)
    transfers_generated: int = 0


# Kolumny ID do prefixowania — zapobiega kolizjom między feedami.
ID_COLS = {
    "agency_id",
    "stop_id",
    "route_id",
    "trip_id",
    "service_id",
    "shape_id",
    "fare_id",
    "zone_id",
    "level_id",
    "pathway_id",
    "from_stop_id",
    "to_stop_id",
    "from_trip_id",
    "to_trip_id",
}


def _read_table_from_zip(zf: zipfile.ZipFile, name: str) -> Optional[list[dict]]:
    try:
        with zf.open(name) as f:
            text = f.read().decode("utf-8-sig", errors="replace")
    except KeyError:
        return None

    if not text.strip():
        return []

    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    return rows


def _prefix_row_ids(row: dict, prefix: str) -> dict:
    out = dict(row)
    for k, v in row.items():
        if v is None:
            continue
        if k in ID_COLS and str(v).strip() != "":
            out[k] = f"{prefix}:{v}"
    return out


def _union_fieldnames(rows_by_feed: list[list[dict]]) -> list[str]:
    fields = []
    seen = set()
    for rows in rows_by_feed:
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    fields.append(k)
                    seen.add(k)
    return fields


def _diagnose_feed(p: Path, prefix: str) -> FeedDiagnostic:
    """Pełna diagnostyka pojedynczego feedu GTFS — tabele, daty, rozmiary."""
    diag = FeedDiagnostic(path=str(p), prefix=prefix)

    with zipfile.ZipFile(p) as zf:
        names = set(zf.namelist())

        for table in GTFS_TABLES:
            if table in names:
                diag.tables_present.append(table)
            else:
                diag.tables_missing.append(table)

        # Daty z calendar.txt
        has_cal = False
        cal_dates_list: list[str] = []
        if "calendar.txt" in names:
            rows = _read_table_from_zip(zf, "calendar.txt")
            if rows:
                has_cal = True
                for row in rows:
                    for col in ("start_date", "end_date"):
                        v = row.get(col, "").strip()
                        if v.isdigit() and len(v) == 8:
                            cal_dates_list.append(v)

        # Daty z calendar_dates.txt
        has_cd = False
        if "calendar_dates.txt" in names:
            rows = _read_table_from_zip(zf, "calendar_dates.txt")
            if rows:
                has_cd = True
                for row in rows:
                    v = row.get("date", "").strip()
                    if v.isdigit() and len(v) == 8:
                        cal_dates_list.append(v)

        if has_cal and has_cd:
            diag.calendar_type = "both"
        elif has_cal:
            diag.calendar_type = "calendar"
        elif has_cd:
            diag.calendar_type = "calendar_dates"
        else:
            diag.calendar_type = "none"
            diag.warnings.append("Brak calendar.txt i calendar_dates.txt — feed nie definiuje żadnych dni serwisu.")

        if cal_dates_list:
            diag.date_min = min(cal_dates_list)
            diag.date_max = max(cal_dates_list)

        # Rozmiary
        stops = _read_table_from_zip(zf, "stops.txt")
        diag.n_stops = len(stops) if stops else 0

        routes = _read_table_from_zip(zf, "routes.txt")
        diag.n_routes = len(routes) if routes else 0
        if routes:
            for r in routes:
                rt = r.get("route_type", "?")
                diag.route_types[rt] = diag.route_types.get(rt, 0) + 1

        trips = _read_table_from_zip(zf, "trips.txt")
        diag.n_trips = len(trips) if trips else 0

        st = _read_table_from_zip(zf, "stop_times.txt")
        diag.n_stop_times = len(st) if st else 0

        diag.has_transfers = "transfers.txt" in names and bool(_read_table_from_zip(zf, "transfers.txt"))
        diag.has_shapes = "shapes.txt" in names and bool(_read_table_from_zip(zf, "shapes.txt"))

        # Ostrzeżenia kontekstowe
        if diag.n_routes == 0:
            diag.warnings.append("Feed nie zawiera żadnych tras (routes.txt puste/brakujące).")
        if not diag.has_shapes:
            diag.warnings.append("Brak shapes.txt — geometria tras niedostępna.")

    return diag


def _compute_date_intersection(diagnostics: list[FeedDiagnostic]) -> tuple[Optional[str], Optional[str]]:
    """Intersekcja zakresów dat ze wszystkich feedów."""
    global_min: Optional[str] = None
    global_max: Optional[str] = None

    for diag in diagnostics:
        if diag.date_min is None or diag.date_max is None:
            continue

        if global_min is None:
            global_min, global_max = diag.date_min, diag.date_max
        else:
            global_min = max(global_min, diag.date_min)
            global_max = min(global_max, diag.date_max)

    if global_min and global_max and global_min <= global_max:
        return global_min, global_max
    return None, None


def _filter_calendar_dates_to_intersection(
    rows: list[dict], date_start: str, date_end: str
) -> list[dict]:
    """Filtruje calendar_dates.txt do intersekcji dat — usuwa wpisy poza wspólnym zakresem."""
    filtered = []
    for r in rows:
        d = r.get("date", "").strip()
        if d and date_start <= d <= date_end:
            filtered.append(r)
    return filtered


def _filter_calendar_to_intersection(
    rows: list[dict], date_start: str, date_end: str
) -> list[dict]:
    """Przycina calendar.txt start/end_date do intersekcji — zachowuje service_id ale zwęża okno."""
    filtered = []
    for r in rows:
        sd = r.get("start_date", "").strip()
        ed = r.get("end_date", "").strip()
        if not sd or not ed:
            filtered.append(r)
            continue
        # Zwęź do intersekcji
        new_start = max(sd, date_start)
        new_end = min(ed, date_end)
        if new_start <= new_end:
            r_copy = dict(r)
            r_copy["start_date"] = new_start
            r_copy["end_date"] = new_end
            filtered.append(r_copy)
    return filtered


def _generate_inter_feed_transfers(
    merged_stops: list[dict],
    feed_prefixes_vals: set[str],
    max_distance_m: float = 200.0,
    min_transfer_time_s: int = 120,
) -> list[dict]:
    """Generuje transfery piesze między przystankami różnych operatorów.

    Przystanki w promieniu max_distance_m (Haversine) od siebie, należące do
    różnych feedów, otrzymują transfer typu 2 (minimum transfer time).
    """
    # Buduj listę (prefix, stop_id, lat, lon) z valid coords
    stop_recs = []
    for s in merged_stops:
        sid = s.get("stop_id", "")
        try:
            lat = float(s.get("stop_lat", ""))
            lon = float(s.get("stop_lon", ""))
        except (ValueError, TypeError):
            continue
        # Wyciągnij prefix feedu
        prefix = None
        for pfx in feed_prefixes_vals:
            if sid.startswith(f"{pfx}:"):
                prefix = pfx
                break
        if prefix is None:
            continue
        stop_recs.append((prefix, sid, lat, lon))

    if not stop_recs:
        return []

    # Haversine w metrach
    def _haversine(lat1, lon1, lat2, lon2):
        R = 6_371_000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.asin(min(1.0, math.sqrt(a)))

    # Grupuj per prefix
    by_prefix: dict[str, list[tuple[str, float, float]]] = {}
    for pfx, sid, lat, lon in stop_recs:
        by_prefix.setdefault(pfx, []).append((sid, lat, lon))

    prefixes = sorted(by_prefix.keys())
    transfers = []

    for i, pfx_a in enumerate(prefixes):
        for pfx_b in prefixes[i + 1:]:
            for sid_a, lat_a, lon_a in by_prefix[pfx_a]:
                for sid_b, lat_b, lon_b in by_prefix[pfx_b]:
                    # Szybki filtr bbox przed Haversine
                    if abs(lat_a - lat_b) > 0.003 or abs(lon_a - lon_b) > 0.004:
                        continue
                    dist = _haversine(lat_a, lon_a, lat_b, lon_b)
                    if dist <= max_distance_m:
                        # Czas przejścia = dystans / prędkość pieszego (1.2 m/s) z minimum
                        walk_time = max(min_transfer_time_s, int(dist / 1.2))
                        transfers.append({
                            "from_stop_id": sid_a,
                            "to_stop_id": sid_b,
                            "transfer_type": "2",
                            "min_transfer_time": str(walk_time),
                        })
                        # Dwukierunkowy
                        transfers.append({
                            "from_stop_id": sid_b,
                            "to_stop_id": sid_a,
                            "transfer_type": "2",
                            "min_transfer_time": str(walk_time),
                        })

    return transfers


def _synthesize_feed_info(start_date: str, end_date: str) -> list[dict]:
    return [{
        "feed_publisher_name": "merged",
        "feed_publisher_url": "https://example.com",
        "feed_lang": "mul",
        "feed_start_date": start_date,
        "feed_end_date": end_date,
        "feed_version": f"merged_{datetime.utcnow().strftime('%Y%m%d')}",
    }]


def _write_table_to_zip(zf_out: zipfile.ZipFile, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(dict.fromkeys(k for r in rows for k in r.keys()))
    buff = io.StringIO()
    w = csv.DictWriter(buff, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fieldnames})
    zf_out.writestr(table, buff.getvalue().encode("utf-8"))


def merge_gtfs_zips(
    in_zips: Iterable[Path],
    out_zip: Path,
    feed_prefixes: Optional[dict[Path, str]] = None,
    generate_inter_feed_transfers: bool = True,
    transfer_max_distance_m: float = 200.0,
    filter_dates_to_intersection: bool = True,
) -> MergeStats:
    """Scalanie feedów GTFS z diagnostyką, filtracją dat i generacją transferów.

    Parametry:
    - generate_inter_feed_transfers: czy generować transfery piesze między operatorami
    - transfer_max_distance_m: maks. dystans Haversine dla transferów (domyślnie 200m)
    - filter_dates_to_intersection: czy filtrować calendar/calendar_dates do intersekcji dat
    """
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    in_zips = [Path(p) for p in in_zips]
    if not in_zips:
        raise ValueError("No input GTFS zips provided")

    for p in in_zips:
        if not p.exists():
            raise FileNotFoundError(p)

    if feed_prefixes is None:
        feed_prefixes = {p: p.stem.replace(" ", "_") for p in in_zips}

    merge_warnings: list[str] = []

    # --- Diagnostyka per feed ---
    diagnostics = []
    for p in in_zips:
        diag = _diagnose_feed(p, feed_prefixes[p])
        diagnostics.append(diag)
        for w in diag.warnings:
            merge_warnings.append(f"[{diag.prefix}] {w}")

    # --- Intersekcja dat ---
    date_start, date_end = _compute_date_intersection(diagnostics)

    if date_start and date_end:
        from datetime import datetime as _dt
        try:
            d0 = _dt.strptime(date_start, "%Y%m%d")
            d1 = _dt.strptime(date_end, "%Y%m%d")
            span_days = (d1 - d0).days
        except ValueError:
            span_days = -1
        if span_days < 7:
            merge_warnings.append(
                f"OSTRZEŻENIE: Intersekcja dat obejmuje tylko {span_days} dni ({date_start}–{date_end}). "
                f"Wyniki analiz mogą nie być reprezentatywne. "
                f"Rozważ pozyskanie feedów z pokrywającym się okresem ważności."
            )
        elif span_days < 30:
            merge_warnings.append(
                f"Uwaga: Intersekcja dat obejmuje {span_days} dni ({date_start}–{date_end}). "
                f"Zalecane minimum to 30 dni dla stabilnych analiz."
            )
    else:
        merge_warnings.append(
            "BŁĄD KRYTYCZNY: Brak wspólnego zakresu dat między feedami. "
            "Scalony feed może nie zawierać żadnych aktywnych serwisów."
        )

    # --- Budowa scalonego feedu ---
    merged: dict[str, list[dict]] = {}

    for table in GTFS_TABLES:
        rows_all_feeds: list[list[dict]] = []
        for p in in_zips:
            with zipfile.ZipFile(p) as zf:
                rows = _read_table_from_zip(zf, table)
            if rows is None:
                continue
            prefix = feed_prefixes[p]
            rows_pref = [_prefix_row_ids(r, prefix) for r in rows]
            rows_all_feeds.append(rows_pref)

        if rows_all_feeds:
            merged[table] = [r for rows in rows_all_feeds for r in rows]

    # --- Filtracja dat do intersekcji ---
    if filter_dates_to_intersection and date_start and date_end:
        if "calendar.txt" in merged:
            n_before = len(merged["calendar.txt"])
            merged["calendar.txt"] = _filter_calendar_to_intersection(
                merged["calendar.txt"], date_start, date_end
            )
            n_after = len(merged["calendar.txt"])
            if n_before != n_after:
                merge_warnings.append(
                    f"calendar.txt: przycięto {n_before} -> {n_after} serwisów do intersekcji {date_start}–{date_end}."
                )

        if "calendar_dates.txt" in merged:
            n_before = len(merged["calendar_dates.txt"])
            merged["calendar_dates.txt"] = _filter_calendar_dates_to_intersection(
                merged["calendar_dates.txt"], date_start, date_end
            )
            n_after = len(merged["calendar_dates.txt"])
            if n_before != n_after:
                merge_warnings.append(
                    f"calendar_dates.txt: przefiltrowano {n_before} -> {n_after} wpisów do intersekcji dat."
                )

    # --- Synthesize feed_info.txt ---
    if date_start and date_end:
        merged["feed_info.txt"] = _synthesize_feed_info(date_start, date_end)

    # --- Generacja transferów między operatorami ---
    n_transfers_generated = 0
    if generate_inter_feed_transfers and "stops.txt" in merged:
        inter_transfers = _generate_inter_feed_transfers(
            merged["stops.txt"],
            set(feed_prefixes.values()),
            max_distance_m=transfer_max_distance_m,
        )
        if inter_transfers:
            existing = merged.get("transfers.txt", [])
            merged["transfers.txt"] = existing + inter_transfers
            n_transfers_generated = len(inter_transfers)
            merge_warnings.append(
                f"Wygenerowano {n_transfers_generated} transferów pieszych między operatorami "
                f"(max. {transfer_max_distance_m}m)."
            )

    # --- Zapis ZIP ---
    tmp = out_zip.with_suffix(out_zip.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf_out:
        for table, rows in merged.items():
            _write_table_to_zip(zf_out, table, rows)

        # Skopiuj niestandardowe pliki z pierwszego feedu (np. attributions)
        with zipfile.ZipFile(in_zips[0]) as zf0:
            for name in zf0.namelist():
                if name in merged:
                    continue
                if name.endswith("/"):
                    continue
                try:
                    info = zf0.getinfo(name)
                except KeyError:
                    continue
                if info.file_size > 2_000_000:
                    continue
                zf_out.writestr(name, zf0.read(name))

    shutil.move(str(tmp), str(out_zip))

    stats = MergeStats(
        out_zip=out_zip,
        in_zips=in_zips,
        tables_written=sorted(merged.keys()),
        date_intersection=(date_start, date_end),
        feed_diagnostics=diagnostics,
        merge_warnings=merge_warnings,
        transfers_generated=n_transfers_generated,
    )

    # --- Zapis raportu diagnostycznego ---
    report_path = out_zip.with_suffix(".merge_report.json")
    report = {
        "generated_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "out_zip": str(out_zip),
        "date_intersection": {"start": date_start, "end": date_end},
        "feeds": [
            {
                "path": d.path,
                "prefix": d.prefix,
                "date_range": {"min": d.date_min, "max": d.date_max},
                "calendar_type": d.calendar_type,
                "tables_present": d.tables_present,
                "tables_missing": d.tables_missing,
                "n_stops": d.n_stops,
                "n_routes": d.n_routes,
                "n_trips": d.n_trips,
                "n_stop_times": d.n_stop_times,
                "route_types": d.route_types,
                "has_transfers": d.has_transfers,
                "has_shapes": d.has_shapes,
                "warnings": d.warnings,
            }
            for d in diagnostics
        ],
        "tables_written": stats.tables_written,
        "transfers_generated": n_transfers_generated,
        "warnings": merge_warnings,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Wydruk ostrzeżeń
    for w in merge_warnings:
        print(f"  [MERGE] {w}")

    return stats

