from __future__ import annotations

import csv
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# Minimal safe GTFS merger.
# Contract:
# - Input: multiple GTFS zip feeds for one region.
# - Output: one GTFS zip that R5 can load.
# - Strategy: concatenate text tables, remap ids with per-feed prefixes to avoid collisions.
# - Notes: keeps agency.txt as-is and prefixes any *_id references found.


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


@dataclass(frozen=True)
class MergeStats:
    out_zip: Path
    in_zips: list[Path]
    tables_written: list[str]


# Common id columns we want to prefix.
# We also prefix shape_id etc. (R5 uses them).
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
}


def _read_table_from_zip(zf: zipfile.ZipFile, name: str) -> Optional[list[dict]]:
    try:
        with zf.open(name) as f:
            # GTFS is CSV; allow commas in fields via quoting.
            text = f.read().decode("utf-8-sig", errors="replace")
    except KeyError:
        return None

    # Some feeds can contain empty files; handle gracefully.
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


def merge_gtfs_zips(
    in_zips: Iterable[Path],
    out_zip: Path,
    feed_prefixes: Optional[dict[Path, str]] = None,
) -> MergeStats:
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

    # Build merged tables.
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

    # Write output zip.
    tmp = out_zip.with_suffix(out_zip.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf_out:
        for table, rows in merged.items():
            fieldnames = _union_fieldnames([rows])
            # Ensure deterministic ordering: keep common GTFS fields first where possible.
            fieldnames = list(dict.fromkeys(fieldnames))

            import io

            buff = io.StringIO()
            w = csv.DictWriter(buff, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            for r in rows:
                # Fill missing columns with empty.
                w.writerow({k: r.get(k, "") for k in fieldnames})

            zf_out.writestr(table, buff.getvalue().encode("utf-8"))

        # Also copy any non-standard files (e.g. attributions) from the first feed to help debugging.
        with zipfile.ZipFile(in_zips[0]) as zf0:
            for name in zf0.namelist():
                if name in merged:
                    continue
                if name.endswith("/"):
                    continue
                # Avoid huge binary extras; keep only small text-ish files.
                try:
                    info = zf0.getinfo(name)
                except KeyError:
                    continue
                if info.file_size > 2_000_000:
                    continue
                zf_out.writestr(name, zf0.read(name))

    shutil.move(str(tmp), str(out_zip))
    return MergeStats(out_zip=out_zip, in_zips=in_zips, tables_written=sorted(merged.keys()))

