#!/usr/bin/env python3
"""
07_filter_fire_cdps.py 🔥
=========================

Script 07 of 08 in the Networks Paper analysis pipeline.

PURPOSE:
--------
Extract data for fire-affected communities from the combined dataset.
This creates a focused subset of CDPs that have experienced significant
wildfires, enabling case study analysis of evacuation infrastructure
in communities where fires have actually occurred.

WHY THIS MATTERS:
-----------------
While the full dataset contains ~30,000 CDPs, we want to examine specific
communities that have experienced wildfires to understand:
- Did limited egress routes contribute to evacuation difficulties?
- What network characteristics do fire-affected communities share?
- How can we identify similar at-risk communities?

FIRE PLACES INCLUDED:
---------------------
The whitelist includes communities affected by major wildfires:
- Paradise (Camp Fire, 2018)
- Santa Rosa area (Tubbs Fire, 2017)
- Redwood Valley (Mendocino Complex, 2018)
- Berry Creek (North Complex, 2020)
- And many others defined in config.py

WORKFLOW:
---------
1. Load the combined CSV from step 06
2. Match place names against curated fire whitelist
3. Filter to California + explicit non-CA exceptions
4. Deduplicate by GEOID
5. Save filtered CSV
6. Copy corresponding visualization plots for convenience

DEPENDENCIES (must run first):
------------------------------
- 06_output_csv_join.py (combined dataset)
- 03_network_calc.py (visualization plots)

================================================================================
📥 INPUTS (Required Data Sources)
================================================================================
1. Combined CSV (from 06_output_csv_join.py):
   - Path: {NETWORKS_DATA_DIR}/output_csvs/combined_csv/combined_data.csv
   - Contains: All CDP attributes merged (demographics, WUI, network, burn, RPS)
   - Key columns: NAME, GEOID, state_name, STATE_NAME, STATEFP

2. Network Visualization Plots:
   - Path: {NETWORKS_DATA_DIR}/output_maps/{State}_{FIPS}/{Place}_{GEOID}/
   - Format: PNG files from 03_network_calc.py
   - Used for: Copying plots of fire-affected CDPs

3. Fire Places Whitelist (defined in config.py):
   - Contains: Curated list of fire-affected place names
   - Examples: "Paradise", "Happy Camp CDP", "Magalia", etc.

================================================================================
📤 OUTPUTS (Generated Files)
================================================================================
1. Filtered Fire CDPs CSV:
   - Path: <script_directory>/fire_cdps/combined_data_fire_cdps.csv
   - Contains: Subset of combined data for fire-affected CDPs only

2. Copied Visualization Plots:
   - Path: <script_directory>/fire_cdps/
   - Format: {Place}_{GEOID}_visualization_{buffer}m.png
   - Contains: Network plots for fire-affected CDPs (convenience copies)

================================================================================
"""

import os
from pathlib import Path
import re
import shutil
import glob
import pandas as pd
from datetime import datetime
import pytz

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

# =============================================================================
# 📝 Output Settings
# =============================================================================
VERBOSE = True                        # Print detailed output (True/False)

# =============================================================================
# 📊 Column Names (expected in combined CSV)
# =============================================================================
NAME_COLUMN = "NAME"                  # Place name column
GEOID_COLUMN = "GEOID"                # Geographic ID column
STATE_NAME_COLUMN = "state_name"      # State name column (created in 06)

# =============================================================================
# 🎨 Plot Configuration
# =============================================================================
PLOT_EXTENSION = ".png"               # Plot file extension
DEFAULT_BUFFER_METERS = 500           # Buffer distance used in plots (meters)

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
# Combined CSV (from 06_output_csv_join.py)
COMBINED_CSV = BASE_DATA_DIR / 'output_csvs' / 'combined_csv' / 'combined_data.csv'

# Source visualization plots (from 03_network_calc.py)
PLOTS_ROOT = BASE_DATA_DIR / 'output_maps'

# =============================================================================
# 📤 OUTPUT PATHS
# =============================================================================
# Output directory for fire CDPs (written next to this script)
OUTPUT_DIR = LOCAL_WORKING_DIR / 'fire_cdps'

# Filtered CSV output path
FILTERED_CSV_PATH = OUTPUT_DIR / 'combined_data_fire_cdps.csv'

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

################################################################################
#                            🔥 FIRE-AFFECTED PLACES WHITELIST                 #
################################################################################
# Curated list of fire-affected Census Designated Places (CDPs)
# These communities experienced significant wildfires and are included
# in the case study analysis.

FIRE_PLACES_WHITELIST = [
    # Northern California fires
    "Happy Camp CDP",           # Happy Camp Complex Fire
    "Weed City",                # Mill Fire, Boles Fire
    "Klamath CDP",              # Various fires
    "Hornbrook",                # Klamathon Fire
    "Igo",                      # Carr Fire area
    "Keswick",                  # Carr Fire
    "Ono",                      # Various fires
    
    # Camp Fire area (2018)
    "Paradise",                 # Camp Fire - deadliest CA fire
    "Concow",                   # Camp Fire
    "Magalia",                  # Camp Fire
    "Berry Creek",              # North Complex Fire (2020)
    
    # Wine Country fires
    "Calistoga",                # Tubbs Fire area
    "Glen Ellen",               # Nuns Fire
    "Redwood Valley",           # Mendocino Complex
    "Hidden Valley Lake CDP, California",  # Valley Fire
    "Silverado Resort",         # Various Napa fires
    
    # Central/Southern California
    "Grass Valley",             # Various fires
    "Loma Rica",                # Various fires
    "Davenport",                # CZU Lightning Complex
    "Moskowite Corner CDP",     # Various fires
    "Allendale CDP",            # Various fires
    "Mountain Ranch",           # Butte Fire
    "Lake Isabella",            # Erskine Fire
    "East Hemet",               # Various fires
    "Calimesa",                 # Sandalwood Fire
    "Santa Paula",              # Thomas Fire area
    "Potrero",                  # Border fires
    "Walker",                   # Mountain View Fire
]

# Non-California exceptions that should also be included
# (Communities outside CA affected by significant fires)
NON_CA_FIRE_EXCEPTIONS = [
    "Colorado Springs, Colorado",   # Waldo Canyon Fire, Black Forest Fire
    "Gatlinburg, Tennessee",        # Great Smoky Mountains wildfires
    "Lahaina CDP, Hawaii",          # Maui wildfires (2023)
]

################################################################################
#                               🛠️ HELPER FUNCTIONS                            #
################################################################################

def normalize_name(name: str) -> str:
    """Normalize place names to improve matching robustness.

    - Lowercase
    - Strip commas and extra whitespace
    - Replace multiple spaces with single space
    - Replace common suffix variants (e.g., " city")
    """
    if not isinstance(name, str):
        return ""
    s = name.lower()
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    # Remove state postfixes like ", california" or " ca"
    s = re.sub(r"\b(california|ca)\b$", "", s).strip()
    # Normalize common suffix tokens
    s = re.sub(r"\b(city|cdp)\b", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def build_fire_whitelist() -> set:
    """Return a set of normalized fire place names (deduplicated)."""
    return {normalize_name(x) for x in FIRE_PLACES_WHITELIST if normalize_name(x)}


def build_non_ca_exceptions() -> set:
    """Return a set of normalized non-CA exception place names."""
    return {normalize_name(x) for x in NON_CA_FIRE_EXCEPTIONS if normalize_name(x)}


def filter_combined_csv(csv_path: str, whitelist_norm: set, non_ca_exceptions: set) -> pd.DataFrame:
    """Load the combined CSV and filter rows whose normalized NAME matches the
    provided whitelist. Restrict to California rows by default, while allowing
    explicit non-CA exceptions by name. Deduplicate by GEOID.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Combined CSV not found at: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    if NAME_COLUMN not in df.columns:
        raise KeyError(f"Expected column '{NAME_COLUMN}' not found in CSV")
    # Ensure GEOID is string and zero-padded (places are typically 7 digits: SS + PPPPP)
    if GEOID_COLUMN in df.columns:
        df[GEOID_COLUMN] = df[GEOID_COLUMN].astype(str).str.replace(".0", "", regex=False)
        # Determine expected length from data; default to 7 if ambiguous
        lengths = df[GEOID_COLUMN].str.len()
        expected_len = 7
        if not lengths.mode().empty:
            try:
                expected_len = int(lengths.mode()[0])
            except Exception:
                expected_len = 7
        df[GEOID_COLUMN] = df[GEOID_COLUMN].str.zfill(expected_len)
    df["_name_norm"] = df[NAME_COLUMN].apply(normalize_name)
    # First, filter by whitelist
    filtered = df[df["_name_norm"].isin(whitelist_norm)].copy()

    # Determine state name column to use
    state_name_col = None
    if "STATE_NAME" in filtered.columns:
        state_name_col = "STATE_NAME"
    elif "state_name" in filtered.columns:
        state_name_col = "state_name"

    # Restrict to California unless the place is in the explicit non-CA exceptions
    if state_name_col is not None:
        is_ca = filtered[state_name_col].astype(str).str.lower() == "california"
        is_exception = filtered["_name_norm"].isin(non_ca_exceptions)
        filtered = filtered[is_ca | is_exception].copy()

    # Deduplicate by GEOID (keep first occurrence)
    if GEOID_COLUMN in filtered.columns:
        filtered = filtered.drop_duplicates(subset=[GEOID_COLUMN]).copy()
    filtered.drop(columns=["_name_norm"], inplace=True)
    return filtered


def expected_plot_path(place_name: str, geoid: str, state_name: str, statefp: str, buffer_m: int) -> str:
    """Construct the exact expected plot path to avoid slow global searches.

    Matches the directory/file scheme in 03_network_calc.py:
      {PLOTS_ROOT}/{STATE_NAME}_{STATEFP}/{SanitizedName}_{GEOID}/{SanitizedName}_{GEOID}_visualization_{buffer_m}m.png
    """
    sanitized = re.sub(r"[^0-9a-zA-Z]+", "_", str(place_name)).strip("_")
    sfp = str(statefp).zfill(2)
    state_dir = f"{state_name}_{sfp}"
    place_dir = f"{sanitized}_{geoid}"
    filename  = f"{sanitized}_{geoid}_visualization_{buffer_m}m{PLOT_EXTENSION}"
    return os.path.join(PLOTS_ROOT, state_dir, place_dir, filename)


def find_plot_quick(row: pd.Series, buffer_m: int) -> str | None:
    """Try to resolve the plot path deterministically using CSV state fields.
    Falls back to a constrained local glob within the place directory.
    """
    place_name = str(row.get(NAME_COLUMN, ""))
    geoid = str(row.get(GEOID_COLUMN, ""))

    # Prefer STATE_NAME/STATEFP; fall back to state_name/State FIPS
    state_name = row.get("STATE_NAME") if pd.notna(row.get("STATE_NAME")) else row.get("state_name")
    statefp    = row.get("STATEFP") if pd.notna(row.get("STATEFP")) else row.get("State FIPS")

    if pd.isna(state_name) or pd.isna(statefp):
        return None

    exact_path = expected_plot_path(place_name, geoid, str(state_name), str(statefp), buffer_m)
    if os.path.exists(exact_path):
        return exact_path

    # Constrained fallback: search only the specific place directory
    sanitized = re.sub(r"[^0-9a-zA-Z]+", "_", str(place_name)).strip("_")
    place_dir = os.path.dirname(exact_path)
    pattern = os.path.join(place_dir, f"{sanitized}_{geoid}_*.png")
    matches = glob.glob(pattern)
    if matches:
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return matches[0]
    return None


def copy_recent_plots(filtered_df: pd.DataFrame, out_dir: str, buffer_m: int) -> list[tuple[str, str]]:
    """Copy the most recent plot for each row in filtered_df into out_dir.

    Returns a list of (source_path, dest_path) for successfully copied files.
    """
    copied = []
    for _, row in filtered_df.iterrows():
        place = str(row.get(NAME_COLUMN, ""))
        geoid = str(row.get(GEOID_COLUMN, ""))
        latest = find_plot_quick(row, buffer_m)
        if latest and os.path.exists(latest):
            dest = os.path.join(out_dir, os.path.basename(latest))
            try:
                shutil.copy2(latest, dest)
                copied.append((latest, dest))
                if VERBOSE:
                    print(f"🖼️ Copied: {latest} -> {dest}")
            except Exception as e:
                print(f"⚠️ Failed to copy plot for {place} ({geoid}): {e}")
        else:
            if VERBOSE:
                print(f"❌ No plot found for {place} ({geoid})")
    return copied


def main():
    print("🔥 Filtering to fire-affected CDPs...")
    whitelist = build_fire_whitelist()
    non_ca_exceptions = build_non_ca_exceptions()
    if VERBOSE:
        print(f"Whitelist places: {sorted(list(whitelist))}")
        print(f"Non-CA exceptions: {sorted(list(non_ca_exceptions))}")

    filtered = filter_combined_csv(COMBINED_CSV, whitelist, non_ca_exceptions)
    print(f"Found {len(filtered)} rows matching fire CDPs (after CA filter + exceptions).")

    # Save filtered CSV
    filtered.to_csv(FILTERED_CSV_PATH, index=False)
    print(f"💾 Saved filtered CSV: {FILTERED_CSV_PATH}")

    # Copy plots
    print("🖼️ Copying most recent plots for matched places...")
    copied = copy_recent_plots(filtered, OUTPUT_DIR, DEFAULT_BUFFER_METERS)
    print(f"✅ Copied {len(copied)} plots to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()


