# 🛣️ Networks Paper - Evacuation Route Analysis

Analysis pipeline for assessing road network egress capacity and wildfire risk for U.S. Census-designated places (CDPs).

## 📋 Overview

This project analyzes road network connectivity and evacuation routes for communities across the United States, with a focus on wildfire-prone areas. The analysis combines:

- **Road network data** from OpenStreetMap
- **Census place boundaries** from the U.S. Census Bureau
- **Wildland-Urban Interface (WUI)** land cover data
- **Burn probability** raster data
- **Risk to Potential Structures (RPS)** metrics

## 🔄 Workflow Pipeline

The analysis follows a numbered sequence of scripts and notebooks:

```
01 → 02 → 03 → 04 → 05 → 06 → 07
```

| Step | File | Description |
|------|------|-------------|
| **01** | `01_download_designated_places.ipynb` | Download Census-designated place shapefiles and demographic data |
| **02** | `02_osmnx_network_download.ipynb` | Download road networks from OpenStreetMap for each CDP |
| **03** | `03_network_calc.py` | Compute network statistics (density, degree, boundary crossings) |
| **03a** | `03a_network_plot_subset.py` | Generate visualization plots for a subset of places |
| **04** | `04_wui_cdp_calculation.ipynb` | Calculate WUI land cover statistics using zonal statistics |
| **05** | `05_burn_prob_rps_calc.ipynb` | Compute burn probability and RPS zonal statistics |
| **06** | `06_output_csv_join.py` | Combine all CSV outputs into a single dataset |
| **07** | `07_filter_fire_cdps.py` | Filter to fire-affected communities of interest |

### Supporting Files

| File | Description |
|------|-------------|
| `config.py` | Centralized configuration (paths, settings, parameters) |
| `network_plot.py` | Network visualization utilities |

### Exploratory Notebooks

| File | Description |
|------|-------------|
| `data_exploration.ipynb` | Data exploration and bivariate mapping |
| `santa_barbara_visualization.ipynb` | Interactive Folium maps for California regions |
| `us_html.ipynb` | National-scale interactive HTML visualization |
| `zip_maps_for_publication.ipynb` | Package maps for publication |

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Access to the data directory (shapefiles, rasters)
- Census API key (for demographic data)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd networks_notebooks
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Census API key (get one at https://api.census.gov/data/key_signup.html)
   export CENSUS_API_KEY='your_api_key_here'
   
   # Optional: Custom data directories
   export NETWORKS_DATA_DIR='/path/to/data'
   export NETWORKS_OUTPUT_DIR='/path/to/outputs'
   export NETWORKS_NUM_CORES=60
   ```

### Configuration

Edit `config.py` to customize:

- **Base directories** for input data and outputs
- **Processing settings** (number of cores, buffer distances)
- **Visualization settings** (DPI, colors, figure sizes)
- **State filtering** (process specific states only)

## 📂 Directory Structure

```
networks_notebooks/
├── 01_download_designated_places.ipynb  # Step 1: Download places
├── 02_osmnx_network_download.ipynb      # Step 2: Download networks
├── 03_network_calc.py                   # Step 3: Compute metrics
├── 03a_network_plot_subset.py           # Step 3a: Plot subset
├── 04_wui_cdp_calculation.ipynb         # Step 4: WUI analysis
├── 05_burn_prob_rps_calc.ipynb          # Step 5: Burn probability
├── 06_output_csv_join.py                # Step 6: Join datasets
├── 07_filter_fire_cdps.py               # Step 7: Filter CDPs
├── config.py                            # Configuration
├── network_plot.py                      # Plotting utilities
├── requirements.txt                     # Python dependencies
├── README.md                            # This file
├── .gitignore                           # Git ignore rules
├── archive/                             # Archived notebooks
│   ├── 03_network_calc.ipynb
│   └── 06_output_csv_join.ipynb
├── fire_cdps/                           # Fire CDP outputs
│   ├── combined_data_fire_cdps.csv
│   └── *.png                            # Visualization plots
└── data_exploration.ipynb               # Exploratory analysis
```

## 🔧 Usage

### Running the Full Pipeline

```bash
# Step 1-2: Run notebooks interactively in Jupyter
jupyter notebook 01_download_designated_places.ipynb
jupyter notebook 02_osmnx_network_download.ipynb

# Step 3: Run network calculations (can be long-running)
python 03_network_calc.py

# Step 4-5: Run notebooks interactively
jupyter notebook 04_wui_cdp_calculation.ipynb
jupyter notebook 05_burn_prob_rps_calc.ipynb

# Step 6: Join all outputs
python 06_output_csv_join.py

# Step 7: Filter to fire-affected places
python 07_filter_fire_cdps.py
```

### Running Individual Steps

Each script can be run independently if the prerequisite data exists:

```bash
# Validate configuration
python config.py

# Generate plots for fire CDPs only
python 03a_network_plot_subset.py

# Filter and extract fire CDP data
python 07_filter_fire_cdps.py
```

## 📊 Output Files

### CSV Outputs

| File | Description |
|------|-------------|
| `network_egress_metrics_cdp.csv` | Network density, degree, boundary crossings |
| `wui_land_cover_cdp.csv` | WUI land cover statistics |
| `burn_prob_cdps_all_states.csv` | Burn probability statistics |
| `rps_cdps_all_states.csv` | Risk to Potential Structures |
| `combined_data.csv` | All metrics joined on GEOID |
| `combined_data_fire_cdps.csv` | Filtered to fire-affected places |

### Visualization Outputs

- Per-place network maps (PNG) showing road networks and boundary crossings
- Interactive HTML maps for web viewing
- Publication-ready ZIP archives of maps

## 🎨 Key Metrics

### Network Statistics
- **Graph density**: Edge density of the road network
- **Average degree**: Average connections per intersection
- **Boundary crossing edges**: Roads crossing the CDP boundary by highway type
- **Boundary crossing lanes**: Total lanes crossing by highway type

### Highway Types Analyzed
- 🔴 Motorway (highest capacity)
- 🟠 Trunk
- 🟡 Primary
- 🔵 Secondary
- 🟣 Tertiary
- ⚪ Residential

## 🔐 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CENSUS_API_KEY` | Census Bureau API key | Required for Step 1 |
| `NETWORKS_DATA_DIR` | Base directory for input data | See config.py |
| `NETWORKS_OUTPUT_DIR` | Base directory for outputs | See config.py |
| `NETWORKS_NUM_CORES` | Number of CPU cores for parallel processing | 60 |

## 📝 Notes

- **Processing time**: Step 3 (network calculations) can take several hours for all U.S. places
- **Disk space**: Downloaded networks and outputs can be 10+ GB
- **Memory**: Large parallel jobs may require 64+ GB RAM
- **Timestamps**: All print statements include Pacific Time timestamps

## 📚 Data Sources

- [U.S. Census Bureau](https://www.census.gov/) - Place boundaries and demographics
- [OpenStreetMap](https://www.openstreetmap.org/) - Road network data via OSMnx
- [USFS Wildfire Risk](https://wildfirerisk.org/) - Burn probability and RPS data
- [SILVIS Lab](https://silvis.forest.wisc.edu/data/wui-change/) - WUI data

## 📄 License

[Add your license here]

## 👥 Authors

[Add author information here]

## 🙏 Acknowledgments

[Add acknowledgments here]
