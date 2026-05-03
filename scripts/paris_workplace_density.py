from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable, Sequence

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data" / "Paris"
OUTPUT_DIR = ROOT / "outputs" / "etap1" / "paris" / "spatial"

DEFAULT_PARQUET = DATA_DIR / "StockEtablissement_utf8/StockEtablissement_utf8.parquet"
DEFAULT_SCHEMA_CSV = DATA_DIR / "StockEtablissement_utf8/StockEtablissement_utf8.csv"
DEFAULT_GRID = OUTPUT_DIR / "pop_grid_1km_metric.geojson"
DEFAULT_GRID_XYZ = DATA_DIR / "fra_pd_2020_1km_ASCII_XYZ.csv"
DEFAULT_BOUNDARY = DATA_DIR / "boundary_admin.geojson"
DEFAULT_OUTPUT_GEOJSON = OUTPUT_DIR / "workplace_density_1km.geojson"
DEFAULT_OUTPUT_HTML = OUTPUT_DIR / "workplace_density_1km_folium.html"
DEFAULT_DEPARTMENT_PREFIXES = ("75", "92", "93", "94")

WGS84 = "EPSG:4326"
LAMBERT_93 = "EPSG:2154"
GRID_SIZE_M = 1000.0

ACTIVE_STATUS_VALUES = {"A", "ACTIF", "ACTIVE"}

# Mapowanie kodów trancheEffectifsEtablissement (INSEE) na punkt środkowy przedziału etatów.
# Źródło: https://www.sirene.fr/static-resources/htm/v_sommaire.htm
# Kod NN oznacza brak deklaracji (nowo zarejestrowane lub brak obowiązku) — traktujemy jako 0.
TRANCHE_EFFECTIFS_MIDPOINT: dict[str, float] = {
    "NN": 0.0,   # nieokreślony
    "00": 0.0,   # 0 pracowników najemnych
    "01": 1.5,   # 1–2
    "02": 4.0,   # 3–5
    "03": 7.5,   # 6–9
    "11": 14.5,  # 10–19
    "12": 34.5,  # 20–49
    "21": 74.5,  # 50–99
    "22": 149.5, # 100–199
    "31": 224.5, # 200–249
    "32": 374.5, # 250–499
    "41": 749.5, # 500–999
    "42": 1499.5,# 1000–1999
    "51": 3499.5,# 2000–4999
    "52": 7499.5,# 5000–9999
    "53": 10000.0,# 10 000+
}

LATITUDE_COLUMNS = ("latitude", "latitudeEtablissement")
LONGITUDE_COLUMNS = ("longitude", "longitudeEtablissement")
LAMBERT_X_COLUMNS = (
    "coordonneeLambertAbscisseEtablissement",
    "coordonneeLambertAbscisseEtablissement ",
)
LAMBERT_Y_COLUMNS = (
    "coordonneeLambertOrdonneeEtablissement",
    "coordonneeLambertOrdonneeEtablissement ",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a 1km workplace density grid for Paris from SIRENE establishments."
    )
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET, help="Path to SIRENE parquet.")
    parser.add_argument(
        "--schema-csv",
        type=Path,
        default=DEFAULT_SCHEMA_CSV,
        help="Optional CSV with SIRENE schema metadata for diagnostics.",
    )
    parser.add_argument(
        "--grid",
        type=Path,
        default=DEFAULT_GRID,
        help="Reference 1km Paris grid in EPSG:2154. If absent, a fallback grid is generated.",
    )
    parser.add_argument(
        "--grid-xyz",
        type=Path,
        default=DEFAULT_GRID_XYZ,
        help="Population XYZ source used to rebuild the Stage I Paris grid if needed.",
    )
    parser.add_argument(
        "--boundary",
        type=Path,
        default=DEFAULT_BOUNDARY,
        help="Administrative boundary used to clip fallback grids.",
    )
    parser.add_argument(
        "--output-geojson",
        type=Path,
        default=DEFAULT_OUTPUT_GEOJSON,
        help="GeoJSON output path for workplace density grid.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=DEFAULT_OUTPUT_HTML,
        help="HTML output path for the folium choropleth map.",
    )
    parser.add_argument(
        "--department-prefixes",
        nargs="*",
        default=list(DEFAULT_DEPARTMENT_PREFIXES),
        help=(
            "Department prefixes used for a coarse prefilter before the exact boundary clip. "
            "Defaults to 75/92/93/94 to match the Paris study area used in Etap I."
        ),
    )
    return parser.parse_args()


def load_schema_columns(schema_csv: Path) -> list[str]:
    if not schema_csv.exists():
        return []
    schema_df = pd.read_csv(schema_csv, nrows=0)
    if "Nom" not in schema_df.columns:
        return []
    schema_df = pd.read_csv(schema_csv, usecols=["Nom"])
    return schema_df["Nom"].dropna().astype(str).tolist()


def get_parquet_columns(parquet_path: Path) -> list[str]:
    try:
        import pyarrow.parquet as pq

        return pq.ParquetFile(parquet_path).schema.names
    except Exception:
        df = pd.read_parquet(parquet_path)
        return list(df.columns)


def pick_first_existing(candidates: Sequence[str], available_columns: Iterable[str]) -> str | None:
    available = set(available_columns)
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def required_sirene_columns(available_columns: list[str]) -> list[str]:
    columns = []

    status_column = pick_first_existing(("etatAdministratifEtablissement",), available_columns)
    if status_column is not None:
        columns.append(status_column)

    department_candidates = (
        "codeDepartementEtablissement",
        "departement",
        "codePostalEtablissement",
        "codeCommuneEtablissement",
    )
    for candidate in department_candidates:
        if candidate in available_columns:
            columns.append(candidate)

    x_col = pick_first_existing(LONGITUDE_COLUMNS, available_columns)
    y_col = pick_first_existing(LATITUDE_COLUMNS, available_columns)
    if x_col is not None and y_col is not None:
        columns.extend([x_col, y_col])
    else:
        lambert_x = pick_first_existing(LAMBERT_X_COLUMNS, available_columns)
        lambert_y = pick_first_existing(LAMBERT_Y_COLUMNS, available_columns)
        if lambert_x is not None and lambert_y is not None:
            columns.extend([lambert_x, lambert_y])

    identifier_columns = [c for c in ("siret", "siren") if c in available_columns]
    columns.extend(identifier_columns)

    # Kolumny do ważonej estymacji zatrudnienia z trancheEffectifs
    for col in ("trancheEffectifsEtablissement", "caractereEmployeurEtablissement"):
        if col in available_columns:
            columns.append(col)

    return sorted(set(columns))


def read_sirene(parquet_path: Path, schema_columns: list[str]) -> pd.DataFrame:
    available_columns = get_parquet_columns(parquet_path)
    selected_columns = required_sirene_columns(available_columns)
    has_unite_legale_only = "etatAdministratifUniteLegale" in available_columns and "etatAdministratifEtablissement" not in available_columns

    missing_geometry = not any(c in available_columns for c in LATITUDE_COLUMNS) or not any(
        c in available_columns for c in LONGITUDE_COLUMNS
    )
    has_lambert = any(c in available_columns for c in LAMBERT_X_COLUMNS) and any(
        c in available_columns for c in LAMBERT_Y_COLUMNS
    )

    if not selected_columns or (missing_geometry and not has_lambert):
        expected_columns = [
            "etatAdministratifEtablissement",
            "codePostalEtablissement or codeDepartementEtablissement",
            "latitude/longitude or coordonneeLambertAbscisseEtablissement/coordonneeLambertOrdonneeEtablissement",
        ]
        schema_hint = ""
        if schema_columns:
            schema_hint = (
                "\nSchema CSV contains establishment fields, but the parquet does not match that structure."
            )
        unite_legale_hint = ""
        if has_unite_legale_only:
            unite_legale_hint = (
                "\nDetected a `UniteLegale` extract rather than an `Etablissement` extract. "
                "`UniteLegale` describes legal entities and does not contain establishment coordinates."
            )
        raise ValueError(
            "Input parquet does not contain the columns required for establishment geocoding and filtering. "
            f"Expected at least: {expected_columns}. Found columns: {available_columns}."
            f"{schema_hint}{unite_legale_hint}\nThis usually means the provided parquet is not the full SIRENE establishment table "
            "(for example, a duplicates-only extract such as StockDoublons)."
        )

    print(f"Loading parquet columns: {selected_columns}")
    return pd.read_parquet(parquet_path, columns=selected_columns)


def normalize_string(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def department_mask(df: pd.DataFrame, department_prefixes: Sequence[str]) -> pd.Series:
    candidates = [
        "codeDepartementEtablissement",
        "departement",
        "codePostalEtablissement",
        "codeCommuneEtablissement",
    ]
    prefixes = [str(prefix).strip() for prefix in department_prefixes if str(prefix).strip()]
    if not prefixes:
        return pd.Series(True, index=df.index)

    masks = []
    for column in candidates:
        if column in df.columns:
            mask = pd.Series(False, index=df.index)
            normalized = normalize_string(df[column])
            for prefix in prefixes:
                mask = mask | normalized.str.startswith(prefix, na=False)
            masks.append(mask)
    if not masks:
        raise ValueError(
            "No department-related column found. Expected one of: "
            f"{candidates}. Available: {list(df.columns)}"
        )
    out = masks[0]
    for mask in masks[1:]:
        out = out | mask
    return out


def active_mask(df: pd.DataFrame) -> pd.Series:
    if "etatAdministratifEtablissement" not in df.columns:
        return pd.Series(True, index=df.index)
    status = normalize_string(df["etatAdministratifEtablissement"]).str.upper()
    return status.isin(ACTIVE_STATUS_VALUES)


def estimate_employment_from_tranche(df: pd.DataFrame) -> pd.Series:
    """Szacuje liczbę etatów dla każdego établissement na podstawie trancheEffectifsEtablissement.

    Jeśli kolumna trancheEffectifs jest dostępna, przypisuje punkt środkowy przedziału.
    Jednostki z kodem 'NN' lub '00' (brak pracowników / brak deklaracji) dostają 0.
    Jeśli kolumna jest niedostępna, fallback = 1.0 na podmiot (stara metodologia — liczenie firm).
    """
    if "trancheEffectifsEtablissement" not in df.columns:
        return pd.Series(1.0, index=df.index, name="employment_estimate")

    codes = df["trancheEffectifsEtablissement"].astype("string").str.strip().str.upper()
    estimates = codes.map(TRANCHE_EFFECTIFS_MIDPOINT)

    unknown_codes = codes[estimates.isna() & codes.notna()].unique()
    if len(unknown_codes) > 0:
        print(f"  [trancheEffectifs] Nieznane kody (traktuję jako 0): {unknown_codes.tolist()}")

    estimates = estimates.fillna(0.0)
    return estimates.rename("employment_estimate")


def build_establishment_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    # Szacowanie etatów z trancheEffectifs przed odrzuceniem wierszy bez koordynatów
    employment_estimates = estimate_employment_from_tranche(df)

    lon_col = pick_first_existing(LONGITUDE_COLUMNS, df.columns)
    lat_col = pick_first_existing(LATITUDE_COLUMNS, df.columns)
    lambert_x = pick_first_existing(LAMBERT_X_COLUMNS, df.columns)
    lambert_y = pick_first_existing(LAMBERT_Y_COLUMNS, df.columns)

    if lon_col is not None and lat_col is not None:
        x = pd.to_numeric(df[lon_col], errors="coerce")
        y = pd.to_numeric(df[lat_col], errors="coerce")
        valid = x.notna() & y.notna()
        filtered = df.loc[valid].copy()
        filtered[lon_col] = x.loc[valid]
        filtered[lat_col] = y.loc[valid]
        filtered["employment_estimate"] = employment_estimates.loc[valid]
        gdf = gpd.GeoDataFrame(
            filtered,
            geometry=gpd.points_from_xy(filtered[lon_col], filtered[lat_col]),
            crs=WGS84,
        )
        return gdf.to_crs(LAMBERT_93)

    if lambert_x is not None and lambert_y is not None:
        x = pd.to_numeric(df[lambert_x], errors="coerce")
        y = pd.to_numeric(df[lambert_y], errors="coerce")
        valid = x.notna() & y.notna()
        filtered = df.loc[valid].copy()
        filtered[lambert_x] = x.loc[valid]
        filtered[lambert_y] = y.loc[valid]
        filtered["employment_estimate"] = employment_estimates.loc[valid]
        return gpd.GeoDataFrame(
            filtered,
            geometry=gpd.points_from_xy(filtered[lambert_x], filtered[lambert_y]),
            crs=LAMBERT_93,
        )

    raise ValueError("No usable coordinate columns found in the parquet extract.")


def filter_points_to_boundary(points_gdf: gpd.GeoDataFrame, boundary_path: Path) -> gpd.GeoDataFrame:
    if not boundary_path.exists():
        raise FileNotFoundError(f"Missing boundary file: {boundary_path}")

    boundary = gpd.read_file(boundary_path)
    if boundary.crs is None:
        raise ValueError(f"Boundary file has no CRS: {boundary_path}")

    boundary_metric = boundary.to_crs(LAMBERT_93)
    joined = gpd.sjoin(
        points_gdf,
        boundary_metric[["geometry"]],
        how="inner",
        predicate="within",
    )
    return points_gdf.loc[joined.index.unique()].copy()


def build_paris_grid_from_xyz(
    csv_path: Path,
    crs_in: str = WGS84,
    crs_metric: str = LAMBERT_93,
) -> gpd.GeoDataFrame:
    df = pd.read_csv(csv_path)
    missing = [c for c in ["X", "Y", "Z"] if c not in df.columns]
    if missing:
        raise ValueError(f"Paris grid XYZ is missing columns: {missing}")

    points = gpd.GeoDataFrame(
        df.rename(columns={"Z": "pop"}).copy(),
        geometry=gpd.points_from_xy(df["X"], df["Y"]),
        crs=crs_in,
    )

    xs_sorted = np.sort(points.geometry.x.unique())
    ys_sorted = np.sort(points.geometry.y.unique())
    dx_native = float(np.median(np.diff(xs_sorted)))
    dy_native = float(np.median(np.diff(ys_sorted)))
    half_dx = dx_native / 2.0
    half_dy = dy_native / 2.0

    geoms_wgs84 = [
        box(x - half_dx, y - half_dy, x + half_dx, y + half_dy)
        for x, y in zip(points.geometry.x, points.geometry.y)
    ]
    cells_wgs84 = gpd.GeoDataFrame(
        points.drop(columns=["geometry"]).copy(),
        geometry=geoms_wgs84,
        crs=crs_in,
    )
    cells = cells_wgs84.to_crs(crs_metric)

    centroid_x = np.round(cells.geometry.centroid.x.values, 0).astype("int64")
    centroid_y = np.round(cells.geometry.centroid.y.values, 0).astype("int64")
    cells["cell_id"] = pd.Series(
        [f"PAR_GRID_{x}_{y}" for x, y in zip(centroid_x, centroid_y)],
        dtype="string",
    )

    keep_cols = ["cell_id", "pop", "X", "Y", "geometry"]
    return cells[keep_cols].copy()


def generate_metric_grid_from_bbox(boundary_gdf: gpd.GeoDataFrame, cell_size_m: float = GRID_SIZE_M) -> gpd.GeoDataFrame:
    boundary_metric = boundary_gdf.to_crs(LAMBERT_93)
    minx, miny, maxx, maxy = boundary_metric.total_bounds

    x_start = math.floor(minx / cell_size_m) * cell_size_m
    y_start = math.floor(miny / cell_size_m) * cell_size_m
    x_stop = math.ceil(maxx / cell_size_m) * cell_size_m
    y_stop = math.ceil(maxy / cell_size_m) * cell_size_m

    polygons = []
    cell_ids = []
    for x in np.arange(x_start, x_stop, cell_size_m):
        for y in np.arange(y_start, y_stop, cell_size_m):
            polygons.append(box(x, y, x + cell_size_m, y + cell_size_m))
            cell_ids.append(f"PAR_FALLBACK_{int(x)}_{int(y)}")

    grid = gpd.GeoDataFrame({"cell_id": cell_ids}, geometry=polygons, crs=LAMBERT_93)
    clipped = gpd.overlay(grid, boundary_metric[["geometry"]], how="intersection")
    if clipped.empty:
        raise ValueError("Fallback grid generation produced no cells after clipping to boundary.")
    clipped["cell_id"] = clipped["cell_id"].astype("string")
    return clipped[["cell_id", "geometry"]].copy()


def load_or_build_grid(grid_path: Path, grid_xyz_path: Path, boundary_path: Path) -> gpd.GeoDataFrame:
    if grid_path.exists():
        grid = gpd.read_file(grid_path)
        if grid.crs is None:
            raise ValueError(f"Grid file has no CRS: {grid_path}")
        return grid.to_crs(LAMBERT_93)

    if grid_xyz_path.exists():
        print(f"Reference grid not found. Rebuilding from XYZ: {grid_xyz_path}")
        grid = build_paris_grid_from_xyz(grid_xyz_path)
        if boundary_path.exists():
            boundary = gpd.read_file(boundary_path).to_crs(LAMBERT_93)
            centroids = gpd.GeoDataFrame(grid[["cell_id"]].copy(), geometry=grid.geometry.centroid, crs=LAMBERT_93)
            inside = gpd.sjoin(centroids, boundary[["geometry"]], how="inner", predicate="within")
            grid = grid.loc[grid["cell_id"].isin(inside["cell_id"])].copy()
        return grid

    if not boundary_path.exists():
        raise FileNotFoundError(
            "No reference grid found and no boundary available for fallback bbox grid generation."
        )

    print(f"Reference grid not found. Generating 1km bbox grid from boundary: {boundary_path}")
    boundary = gpd.read_file(boundary_path)
    return generate_metric_grid_from_bbox(boundary)


def ensure_cell_id(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid = grid.copy()
    if "cell_id" not in grid.columns:
        centroid_x = np.round(grid.geometry.centroid.x.values, 0).astype("int64")
        centroid_y = np.round(grid.geometry.centroid.y.values, 0).astype("int64")
        grid["cell_id"] = pd.Series(
            [f"PAR_GRID_{x}_{y}" for x, y in zip(centroid_x, centroid_y)], dtype="string"
        )
    return grid


def aggregate_points_to_grid(points: gpd.GeoDataFrame, grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    grid_metric = ensure_cell_id(grid.to_crs(LAMBERT_93))
    # Usuń kolumny, które będą nadpisane przez agregację, aby uniknąć konfliktów _x/_y przy merge
    cols_to_drop = [c for c in ("workplace_count", "employment", "workplace_density_km2") if c in grid_metric.columns]
    if cols_to_drop:
        grid_metric = grid_metric.drop(columns=cols_to_drop)
    points_metric = points.to_crs(LAMBERT_93)

    has_estimates = "employment_estimate" in points_metric.columns
    cols_to_join = [c for c in points_metric.columns if c != "geometry"] + ["geometry"]
    joined = gpd.sjoin(
        points_metric[cols_to_join],
        grid_metric[["cell_id", "geometry"]],
        how="inner",
        predicate="within",
    )

    # Liczba podmiotów (zachowane dla zgodności wstecznej i jako diagnostyka)
    counts = joined.groupby("cell_id").size().reset_index(name="workplace_count")

    if has_estimates:
        # Ważona suma etatów z trancheEffectifs: lepsza metodologicznie niż liczenie firm
        emp_sum = (
            joined.groupby("cell_id")["employment_estimate"]
            .sum()
            .reset_index(name="employment")
        )
        agg = counts.merge(emp_sum, on="cell_id", how="left")
    else:
        # Fallback: brak trancheEffectifs — traktuj każdy podmiot jako 1 etat
        print("  [aggregate] Brak kolumny employment_estimate — fallback: workplace_count = employment")
        agg = counts.copy()
        agg["employment"] = agg["workplace_count"].astype(float)

    print(f"  [aggregate] agg columns: {list(agg.columns)}, rows: {len(agg)}")

    result = grid_metric.merge(agg, on="cell_id", how="left")
    result["workplace_count"] = result["workplace_count"].fillna(0).astype(int)
    if "employment" in result.columns:
        result["employment"] = result["employment"].fillna(0.0)
    else:
        print(f"  [aggregate] WARN: 'employment' not in result after merge — columns: {list(result.columns)}")
        result["employment"] = 0.0
    result["workplace_density_km2"] = result["employment"]
    return result


def build_folium_map(grid: gpd.GeoDataFrame, output_html: Path) -> None:
    output_html.parent.mkdir(parents=True, exist_ok=True)

    grid_wgs84 = grid.to_crs(WGS84).copy()
    centroid = grid_wgs84.geometry.union_all().centroid
    map_center = [float(centroid.y), float(centroid.x)]

    base_map = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=grid_wgs84.to_json(),
        data=grid_wgs84[["cell_id", "employment"]],
        columns=["cell_id", "employment"],
        key_on="feature.properties.cell_id",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.2,
        line_weight=0.5,
        nan_fill_color="#f2f2f2",
        legend_name="Estimated employment (FTE midpoint) per 1 km grid cell",
    ).add_to(base_map)

    tooltip = folium.GeoJson(
        grid_wgs84,
        style_function=lambda _: {
            "color": "#444444",
            "weight": 0.4,
            "fillOpacity": 0.0,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["cell_id", "workplace_count", "employment"],
            aliases=["Cell ID", "Establishments (count)", "Employment estimate (FTE)"],
            localize=True,
            sticky=False,
        ),
    )
    tooltip.add_to(base_map)

    folium.LayerControl().add_to(base_map)
    base_map.save(output_html)


def main() -> None:
    args = parse_args()

    if not args.parquet.exists():
        raise FileNotFoundError(f"Missing parquet input: {args.parquet}")

    schema_columns = load_schema_columns(args.schema_csv)
    establishments_df = read_sirene(args.parquet, schema_columns=schema_columns)
    print(f"Loaded rows: {len(establishments_df):,}")

    filtered_df = establishments_df.loc[
        active_mask(establishments_df) & department_mask(establishments_df, args.department_prefixes)
    ].copy()
    print(f"Rows after active + coarse department prefilter: {len(filtered_df):,}")

    points_gdf = build_establishment_geodataframe(filtered_df)
    print(f"Rows with usable coordinates: {len(points_gdf):,}")

    points_gdf = filter_points_to_boundary(points_gdf, args.boundary)
    print(f"Rows inside Etap I Paris boundary: {len(points_gdf):,}")

    grid_gdf = load_or_build_grid(args.grid, args.grid_xyz, args.boundary)
    print(f"Grid cells available: {len(grid_gdf):,}")

    density_gdf = aggregate_points_to_grid(points_gdf, grid_gdf)
    covered_cells = int(density_gdf["workplace_count"].gt(0).sum())
    print(
        f"Spatial join complete: {len(points_gdf):,} points processed, "
        f"{covered_cells:,}/{len(density_gdf):,} grid cells with at least one establishment."
    )

    args.output_geojson.parent.mkdir(parents=True, exist_ok=True)
    density_gdf.to_file(args.output_geojson, driver="GeoJSON")
    build_folium_map(density_gdf, args.output_html)

    print(f"GeoJSON written to: {args.output_geojson}")
    print(f"Folium map written to: {args.output_html}")


if __name__ == "__main__":
    main()