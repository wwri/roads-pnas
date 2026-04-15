#!/usr/bin/env python3
"""
08_network_plot_fire_cdps.py 🔥🗺️
==================================

Script 08 of 08 in the Networks Paper analysis pipeline.

PURPOSE:
--------
Generate visualization plots for fire-affected Census Designated Places (CDPs).
This script creates road network maps showing egress routes for communities that
have experienced significant wildfires, allowing visual analysis of evacuation
infrastructure.

WORKFLOW:
---------
1. Load the filtered fire CDPs list from step 07
2. For each fire-affected CDP:
   a. Load the pre-computed road network graph (GraphML from step 02)
   b. Load the place boundary geometry from Census shapefiles
   c. Buffer the boundary and clip the network
   d. Calculate boundary crossing statistics by road type
   e. Generate a color-coded visualization map
3. Save all plots to the output directory

DEPENDENCIES (must run first):
------------------------------
- 01_download_designated_places.ipynb (Census shapefiles)
- 02_osmnx_network_download.ipynb (GraphML road networks)
- 07_filter_fire_cdps.py (filtered fire CDPs list)

================================================================================
📥 INPUTS (Required Data Sources)
================================================================================
1. Fire CDPs Filtered CSV (from step 07):
   - Path: <script_directory>/fire_cdps/combined_data_fire_cdps.csv
   - Contains: Subset of CDPs identified as fire-affected
   - Key columns: GEOID, NAME, STATE_NAME, STATEFP

2. Road Network Graphs (from step 02):
   - Path: {NETWORKS_DATA_DIR}/output_maps/{State}_{FIPS}/{Place}_{GEOID}/
   - Format: GraphML files containing OSM road network topology
   - Required for: Loading road network for visualization

3. Census Place Shapefiles (from step 01):
   - Path: {NETWORKS_DATA_DIR}/us-census-designated-places/
   - Format: Shapefiles containing place boundary polygons
   - Required for: Place boundary geometries for buffering and clipping

================================================================================
📤 OUTPUTS (Generated Files)
================================================================================
1. Network Visualization Maps (PNG):
   - Path: <script_directory>/08_fire_cdp_plots/{State}_{FIPS}/{Place}_{GEOID}/
   - Format: {Place}_{GEOID}_visualization_{buffer}m.png
   - Contains: Color-coded road network maps showing:
     * CDP boundary (light blue fill)
     * Buffered boundary (black outline)
     * Roads by type (motorway=pink, trunk=orange, primary=yellow, etc.)
     * Boundary crossing statistics in legend

================================================================================
"""

import os
from pathlib import Path
import re
import sys
import glob
import traceback
from typing import Iterable, List, Optional, Set
from datetime import datetime
import pytz

import pandas as pd
import geopandas as gpd
import osmnx as ox
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm

################################################################################
#                            ⏰ TIMESTAMP UTILITY                              #
################################################################################

# Timezone for timestamps (Pacific Time)
TIMEZONE = pytz.timezone('America/Los_Angeles')

def get_timestamp():
    """Return current timestamp in Pacific Time for logging."""
    return datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z')

def print_timestamped(message):
    """Print a message with Pacific Time timestamp."""
    print(f"[{get_timestamp()}] {message}")

################################################################################
#                            🔧 SETTINGS                                       #
################################################################################
# These settings control the script's behavior. Modify as needed for your run.

# =============================================================================
# 🖥️ Processing Settings
# =============================================================================
NUM_WORKERS: int = 1                    # Number of workers (use 1 for reliability)

# =============================================================================
# 📐 Analysis Parameters
# =============================================================================
BUFFER_SIZES_METERS: List[int] = [500]  # Buffer distances in meters for plots

# =============================================================================
# 🎯 Filtering Options
# =============================================================================
SKIP_IF_PLOT_EXISTS: bool = True        # Skip places that already have plots
SELECTED_STATES: Optional[List[str]] = []  # Filter to specific states (empty = infer from CSV)
                                        # Example: ['California']

# =============================================================================
# 🎨 Visualization Settings
# =============================================================================
PLOT_DPI: int = 400                     # Plot resolution (dots per inch)

################################################################################
#                            📂 FILE PATHS                                     #
################################################################################
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  Configure BASE_DATA_DIR to point to your root data directory.          │
# │  You can also override it at runtime with an environment variable:      │
# │      export NETWORKS_DATA_DIR="/your/path/to/data"                      │
# │  Or edit the default path below.                                        │
# └─────────────────────────────────────────────────────────────────────────┘
BASE_DATA_DIR = Path(os.environ.get(
    "NETWORKS_DATA_DIR",
    "~/data/networks_paper"           # ← change this fallback if not using env var
)).expanduser()
LOCAL_WORKING_DIR = Path(__file__).parent

# =============================================================================
# 📥 INPUT PATHS
# =============================================================================
# Fire CDPs filtered list (from 07_filter_fire_cdps.py)
FILTERED_CSV_PATH: Path = LOCAL_WORKING_DIR / 'fire_cdps' / 'combined_data_fire_cdps.csv'

# GraphML source directory (from 02_osmnx_network_download.ipynb)
SOURCE_OUTPUT_DIR: Path = BASE_DATA_DIR / 'output_maps'

# Census place shapefiles (from 01_download_designated_places.ipynb)
US_CENSUS_PLACES_DIR: Path = BASE_DATA_DIR / 'us-census-designated-places'

# =============================================================================
# 📤 OUTPUT PATHS
# =============================================================================
# Output plots directory (written next to this script)
PLOTS_OUTPUT_DIR: Path = LOCAL_WORKING_DIR / '08_fire_cdp_plots'


################################################################################
#                           🧰 SMALL HELPER UTILITIES                          #
################################################################################


def zero_pad_geoid_series(series: pd.Series) -> pd.Series:
    """Normalize GEOID strings with zero-padding to 7 digits (Census standard: 2-digit state + 5-digit place)."""
    s = series.astype(str).str.replace(".0", "", regex=False)
    return s.str.zfill(7)


def sanitize_place_name_for_path(name: str) -> str:
    """Match the sanitization used in 03 for directory/file naming."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_")


def expected_plot_path(plots_root: str, place_name: str, geoid: str,
                       state_name: str, statefp: str, buffer_m: int) -> str:
    """Construct the expected plot path (mirrors 03's directory scheme)."""
    sanitized = sanitize_place_name_for_path(place_name)
    state_dir = f"{state_name}_{str(statefp).zfill(2)}"
    place_dir = f"{sanitized}_{geoid}"
    filename = f"{sanitized}_{geoid}_visualization_{buffer_m}m.png"
    return os.path.join(plots_root, state_dir, place_dir, filename)


def extract_hw_types(hw):
    """Flatten and normalize possible highway attribute values to a list of strings."""
    types: List[str] = []
    if isinstance(hw, str):
        s = hw.strip()
        # If the string looks like a list representation, do a best-effort parse
        if s.startswith('[') and s.endswith(']'):
            try:
                import ast
                parsed = ast.literal_eval(s)
                return extract_hw_types(parsed)
            except Exception:
                types.append(s)
        else:
            types.append(s)
    elif isinstance(hw, (list, tuple)):
        for item in hw:
            types.extend(extract_hw_types(item))
    else:
        types.append(str(hw))
    return types


def load_filtered_fire_df(filtered_csv_path: str) -> pd.DataFrame:
    """Load the filtered CSV of fire CDPs and normalize key columns."""
    if not os.path.exists(filtered_csv_path):
        raise FileNotFoundError(f"Filtered CSV not found: {filtered_csv_path}")
    df = pd.read_csv(filtered_csv_path, low_memory=False)
    if "GEOID" in df.columns:
        df["GEOID"] = zero_pad_geoid_series(df["GEOID"])
    return df


def infer_states_from_df(df: pd.DataFrame) -> List[str]:
    """Infer a list of state names from common state name columns if available."""
    candidates: List[str] = []
    for col in ("STATE_NAME", "state_name"):
        if col in df.columns:
            vals = (
                df[col]
                .dropna()
                .astype(str)
                .str.strip()
                .tolist()
            )
            candidates.extend(vals)
    # De-duplicate while preserving order
    seen: Set[str] = set()
    ordered: List[str] = []
    for s in candidates:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def load_census_places_gdf(places_root: str, selected_states: Optional[List[str]]) -> gpd.GeoDataFrame:
    """Load Census place shapefiles, optionally limited to selected states.

    This mirrors the loading approach in 03, but allows state restriction for speed.
    """
    state_dirs = [
        d for d in glob.glob(os.path.join(places_root, "*")) if os.path.isdir(d)
    ]
    if not state_dirs:
        raise RuntimeError(f"No state directories found in: {places_root}")

    gdf_all = gpd.GeoDataFrame()
    for sd in state_dirs:
        base = os.path.basename(sd)
        if "_" not in base:
            continue
        state_name, state_fp = base.rsplit("_", 1)
        if selected_states is not None and len(selected_states) > 0:
            if state_name not in selected_states:
                continue
        for shp in glob.glob(os.path.join(sd, "*.shp")):
            try:
                gdf = gpd.read_file(shp)
                if gdf.crs is None:
                    gdf = gdf.set_crs(epsg=4326, allow_override=True)
                else:
                    gdf = gdf.to_crs(epsg=4326)
                gdf["STATEFP"] = state_fp
                gdf["STATE_NAME"] = state_name
                gdf_all = pd.concat([gdf_all, gdf], ignore_index=True)
            except Exception as e:
                print(f"⚠️ Error reading {shp}: {e}")

    if gdf_all.empty:
        raise RuntimeError("No places loaded from shapefiles.")
    return gdf_all


def plot_place_figure(
    polygon_wgs84,
    buf_polygon_wgs84,
    edges_full: gpd.GeoDataFrame,
    clipped_edge_keys: set,
    stats: dict,
    place_name: str,
    state_name: str,
    out_path: str,
) -> None:
    """Render the visualization plot matching the visual style used in 03.

    Saves the figure to `out_path`.
    """
    color_map = {
        'motorway':    "#CC5A5A",
        'trunk':       "#D7898D",
        'primary':     "#B6A1B7",
        'secondary':   "#8C8BAF",
        'tertiary':    "#57A5D9",
        'residential': "#E0E0E0",
    }

    fig, ax = plt.subplots(figsize=(10, 10), dpi=PLOT_DPI)

    # CDP polygon
    gpd.GeoSeries([polygon_wgs84]).plot(
        ax=ax, facecolor='#ccf2ff', edgecolor='none', alpha=0.5
    )

    # Buffered polygon
    gpd.GeoSeries([buf_polygon_wgs84]).plot(
        ax=ax, facecolor='none', edgecolor='black', lw=2
    )

    # Clipped edges overlay - draw each road type in its own color
    clipped = edges_full[edges_full.index.isin(clipped_edge_keys)]
    if not clipped.empty:
        overlay_order = ['residential', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway']
        # Track which edges get classified so unclassified ones can be drawn in gray
        classified_idx = set()
        for hw_type in overlay_order:
            col = color_map.get(hw_type)
            if not col:
                continue
            if 'highway' in clipped.columns:
                mask = clipped['highway'].apply(lambda h: hw_type in extract_hw_types(h))
            else:
                mask = pd.Series(False, index=clipped.index)
            subset = clipped[mask]
            if not subset.empty:
                classified_idx.update(subset.index.tolist())
                lw = 2 if hw_type in ['motorway', 'trunk'] else 1.5
                z = 1 if hw_type == 'residential' else 2
                subset.plot(ax=ax, linewidth=lw, color=col, zorder=z)
        # Draw any unclassified edges (e.g. service roads, unclassified) in gray
        unclassified = clipped[~clipped.index.isin(classified_idx)]
        if not unclassified.empty:
            unclassified.plot(ax=ax, linewidth=1, color='gray', zorder=0)

    # Clean axes
    ax.set_xticks([])
    ax.set_yticks([])

    # Legend
    legend_handles = [
        Patch(facecolor='#ccf2ff', edgecolor='none', label='Original CDP'),
        Line2D([0], [0], color='black', lw=2, label='Buffered CDP boundary'),
        Line2D([0], [0], color='gray', lw=2, label='Other roads'),
        Line2D([0], [0], color="#CC5A5A", lw=4, label='Motorway'),
        Line2D([0], [0], color="#D7898D", lw=4, label='Trunk'),
        Line2D([0], [0], color="#B6A1B7", lw=4, label='Primary'),
        Line2D([0], [0], color="#8C8BAF", lw=4, label='Secondary'),
        Line2D([0], [0], color="#57A5D9", lw=4, label='Tertiary'),
        Line2D([0], [0], color="#E0E0E0", lw=1.5, label='Residential'),
    ]
    ax.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc='upper left')

    # Scale bar (stylistic)
    scale_len = 5 / 111.32  # 5 km in degrees (1 degree latitude ~ 111.32 km)
    sb = AnchoredSizeBar(
        ax.transData, scale_len, "",
        loc='lower center', pad=0.1, borderpad=0.5,
        color='black', frameon=False, size_vertical=0.001,
        fontproperties=fm.FontProperties(size=10),
        bbox_to_anchor=(0.5, 0.075), bbox_transform=fig.transFigure,
    )
    ax.add_artist(sb)

    # Stats text and title
    plt.tight_layout(rect=[0, 0.18, 0.85, 1])
    stats_txt = (
        f"Boundary Crossing Roads:\n"
        f"Motorway: {stats.get('boundary_crossing_edges_motorway', 0)} roads, "
        f"{stats.get('boundary_crossing_lanes_motorway', 0)} lanes\n"
        f"Trunk: {stats.get('boundary_crossing_edges_trunk', 0)} roads, "
        f"{stats.get('boundary_crossing_lanes_trunk', 0)} lanes\n"
        f"Primary: {stats.get('boundary_crossing_edges_primary', 0)} roads, "
        f"{stats.get('boundary_crossing_lanes_primary', 0)} lanes\n"
        f"Secondary: {stats.get('boundary_crossing_edges_secondary', 0)} roads, "
        f"{stats.get('boundary_crossing_lanes_secondary', 0)} lanes\n"
        f"Tertiary: {stats.get('boundary_crossing_edges_tertiary', 0)} roads, "
        f"{stats.get('boundary_crossing_lanes_tertiary', 0)} lanes"
    )
    fig.text(0.08, 0.02, stats_txt, ha='left', va='bottom', fontsize=12,
             bbox=dict(facecolor='white', alpha=0.7))
    fig.text(0.5, 0.97, f"{state_name} - {place_name}", ha='center', va='top',
             fontsize=14, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=PLOT_DPI)
    plt.close(fig)


################################################################################
#                                    🚀 MAIN                                    #
################################################################################

def main() -> None:
    print("🧭 Starting rapid plotting for fire CDPs...")

    # Load the filtered places from 07 output
    fire_df = load_filtered_fire_df(FILTERED_CSV_PATH)
    if "GEOID" not in fire_df.columns:
        raise KeyError("Expected 'GEOID' column in filtered CSV")

    target_geoids: Set[str] = set(fire_df["GEOID"].astype(str))
    print(f"📋 Found {len(target_geoids)} target GEOIDs from filtered CSV")

    # Determine which states to load
    if SELECTED_STATES is None:
        states_to_load: Optional[List[str]] = None
    elif len(SELECTED_STATES) == 0:
        states_to_load = infer_states_from_df(fire_df)
        if not states_to_load:
            print("ℹ️ No state names in CSV; will scan all states (may be slower)")
            states_to_load = None
    else:
        states_to_load = SELECTED_STATES

    # Load Census place shapefiles
    gdf_all = load_census_places_gdf(US_CENSUS_PLACES_DIR, states_to_load)

    # Normalize GEOID, filter to target subset
    if "GEOID" not in gdf_all.columns:
        raise KeyError("Shapefiles are expected to contain 'GEOID' column")
    gdf_all["GEOID"] = zero_pad_geoid_series(gdf_all["GEOID"])

    subset = gdf_all[gdf_all["GEOID"].isin(target_geoids)].copy()
    if subset.empty:
        print("❌ No matching places found in shapefiles for provided GEOIDs.")
        return

    print(f"🗺️ Will attempt plotting for {len(subset)} places...")

    # Use local output directory for this 03a workflow
    plots_root = PLOTS_OUTPUT_DIR
    os.makedirs(plots_root, exist_ok=True)

    # Iterate through places and (re)generate plots
    generated_count = 0
    skipped_count = 0
    for _, place_row in subset.iterrows():
        place_name = place_row.get("NAME")
        geoid = str(place_row.get("GEOID"))
        state_name = str(place_row.get("STATE_NAME"))
        statefp = str(place_row.get("STATEFP"))

        # Determine which buffers still need plotting (if skipping existing)
        buffers_needed: List[int] = []
        for buf in BUFFER_SIZES_METERS:
            if not SKIP_IF_PLOT_EXISTS:
                buffers_needed.append(buf)
                continue
            out_path = expected_plot_path(
                plots_root, str(place_name), geoid, state_name, statefp, buf
            )
            if os.path.exists(out_path):
                skipped_count += 1
            else:
                buffers_needed.append(buf)

        if not buffers_needed:
            continue

        try:
            # Load GraphML for the place
            sanitized = sanitize_place_name_for_path(place_name)
            place_dir = os.path.join(SOURCE_OUTPUT_DIR, f"{state_name}_{str(statefp).zfill(2)}", f"{sanitized}_{geoid}")
            graph_path = os.path.join(place_dir, f"{sanitized}_{geoid}.graphml")
            if not os.path.exists(graph_path):
                print(f"❌ GraphML not found for {place_name} ({geoid}) at {graph_path}")
                continue

            G = ox.load_graphml(graph_path)

            # Prepare geometries
            poly_ser = gpd.GeoSeries([place_row.geometry], crs='EPSG:4326')
            utm_crs = poly_ser.estimate_utm_crs()
            poly_utm = poly_ser.to_crs(utm_crs)

            # Extract edges_full
            nodes_full, edges_full = ox.graph_to_gdfs(G)
            if edges_full is None or edges_full.empty:
                print(f"ℹ️ No edges for {place_name} ({geoid})")
                continue
            if edges_full.crs is None:
                edges_full.set_crs(epsg=4326, inplace=True)
            elif edges_full.crs.to_string() != 'EPSG:4326':
                edges_full = edges_full.to_crs(epsg=4326)

            # For each needed buffer: clip, compute boundary crossings, and plot
            for buf in buffers_needed:
                buf_poly_utm = poly_utm.buffer(buf)
                buf_polygon = buf_poly_utm.to_crs('EPSG:4326').iloc[0]

                try:
                    G_clip = ox.truncate.truncate_graph_polygon(
                        G, buf_polygon, retain_all=True, truncate_by_edge=True
                    )
                except ValueError:
                    continue

                if G_clip.number_of_nodes() == 0:
                    continue

                # Build stats for legend text (boundary crossings)
                stats: dict = {
                    'boundary_crossing_edges_motorway': 0,
                    'boundary_crossing_lanes_motorway': 0,
                    'boundary_crossing_edges_trunk': 0,
                    'boundary_crossing_lanes_trunk': 0,
                    'boundary_crossing_edges_primary': 0,
                    'boundary_crossing_lanes_primary': 0,
                    'boundary_crossing_edges_secondary': 0,
                    'boundary_crossing_lanes_secondary': 0,
                    'boundary_crossing_edges_tertiary': 0,
                    'boundary_crossing_lanes_tertiary': 0,
                }

                from shapely.geometry import Polygon, MultiPolygon, MultiLineString
                def get_exterior_boundary(polygon):
                    if isinstance(polygon, Polygon):
                        return polygon.exterior
                    elif isinstance(polygon, MultiPolygon):
                        return MultiLineString([p.exterior for p in polygon.geoms])
                    else:
                        raise ValueError("Unsupported geometry type for boundary extraction.")

                boundary_edges = edges_full[edges_full.geometry.crosses(get_exterior_boundary(buf_polygon))]
                if 'highway' in boundary_edges.columns:
                    relevant_types = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
                    relevant = boundary_edges[boundary_edges['highway'].apply(
                        lambda h: any(t in extract_hw_types(h) for t in relevant_types)
                    )]
                else:
                    relevant = gpd.GeoDataFrame(columns=edges_full.columns)

                for _, row in relevant.iterrows():
                    hw_vals = extract_hw_types(row.get('highway'))
                    lanes = row.get('lanes', 1)
                    try:
                        lane_count = int(lanes) if pd.notna(lanes) else 1
                    except Exception:
                        lane_count = 1
                    for t in hw_vals:
                        t_s = str(t).replace(' ', '_')
                        if t_s in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']:
                            stats[f'boundary_crossing_edges_{t_s}'] += 1
                            stats[f'boundary_crossing_lanes_{t_s}'] += lane_count

                # Plot using helper
                out_path = expected_plot_path(plots_root, str(place_name), geoid, state_name, statefp, buf)
                clipped_edge_keys = set(G_clip.edges())
                plot_place_figure(place_row.geometry, buf_polygon, edges_full, clipped_edge_keys,
                                   stats, str(place_name), str(state_name), out_path)

            generated_count += 1
        except Exception as e:
            print(
                f"⚠️ Failed to generate for {place_name} ({geoid}): {e}\n{traceback.format_exc()}"
            )

    print(
        f"✅ Done. Generated (or attempted) {generated_count} places; "
        f"skipped {skipped_count} buffer(s) due to existing plots."
    )


if __name__ == "__main__":
    main()


