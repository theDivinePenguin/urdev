# UrDev: Urban & Environmental Expansion Engine

**UrDev** is an automated spatial analysis pipeline that leverages **Google Earth Engine (GEE)** to analyze and visualize urban expansion and environmental metrics globally. 

Using multi-petabyte satellite catalogs (like Sentinel-2, MODIS, and Sentinel-5P), the CLI fetches geographic boundaries via OSMnx, securely accesses Earth Engine imagery through your local Google Cloud Project credentials, and generates composite images comparing environmental shifts across customizable timeframes.

---

## How It Works

UrDev is designed to be highly modular and automated. The execution flow follows these core steps:

1.  **Boundary Geocoding (`generate.py`):** The user provides a natural language location (e.g., "Singapore"). UrDev uses `osmnx` to query OpenStreetMap's Nominatim API, retrieving the exact mathematical multi-polygon boundary of that location. If the location resolves to a singular Point (e.g., geocoding a broad region name that lacks a polygon in OSM), the system will automatically query and suggest valid sub-boundaries (like states or counties).
2.  **Dataset Profiling (`pipeline/datasets.py`):** The system looks up the requested dataset in the Dataset Registry to determine its Earth Engine Collection ID, native scale (resolution in meters), and mathematical reducer (e.g., `mode` for categorical data, `mean` for continuous data).
3.  **Tiling & Fetching (`scripts/build_dataset.py`):** The exact boundary is divided into manageable mathematical tiles. UrDev async-queries Earth Engine, filters images by date and region, and downloads the raw GeoTIFF tiles to local storage. 
    *   *Edge Case Handling:* If the satellite coverage for a specific year is too sparse (e.g., early years like 2016 for Sentinel-2), UrDev automatically detects the low image count and expands its temporal search window to the entire calendar year to guarantee a complete, uncorrupted image.
4.  **Mosaicking & Colorization (`scripts/generate_mosaic.py`):** The individual GeoTIFF tiles are stitched back together using `rasterio`. The system applies a pure-NumPy mathematical gradient (such as *Inferno* or *Viridis*) to colorize the data seamlessly without relying on bulky external dependencies like Matplotlib.
5.  **Statistical Analysis (`pipeline/generate_analysis.py`):** The system scans the final mathematical arrays. For landcover, it computes the exact physical area (in km²) of every class (water, trees, built-up). For environmental data (temperature, ozone), it computes the regional Mean, Min, Max, and Standard Deviation.

---

## Quick Start

### 1. Requirements and Setup
Ensure you have the Python dependencies installed (`osmnx`, `rasterio`, `geopandas`, `numpy`, etc.), and authenticate your local environment with Earth Engine:
```bash
earthengine authenticate
```
*Note: Your Earth Engine authentication must be associated with a valid Google Cloud Project. If initialization fails, link your project by running `earthengine set_project YOUR_PROJECT_ID`.*

### 2. Generating Geospatial Data
You can pass any globally recognized location to the entrypoint script. The pipeline will automatically geocode the administrative boundary, update the configuration, download the requisite tiles from Earth Engine, and generate the final image mosaics.

You can specify different environmental maps using the `--dataset` flag:

**Generate a Landcover Map (Default):**
```bash
python generate.py --location "Manhattan, New York" --start-year 2020 --end-year 2021
```

**Generate a Temperature Heatmap:**
```bash
python generate.py --location "Singapore" --start-year 2020 --end-year 2021 --dataset temperature
```

**Generate an Ozone Air Quality Map:**
```bash
python generate.py --location "Abuja Municipal Area Council, Nigeria" --start-year 2020 --end-year 2021 --dataset ozone
```

### Supported Datasets & Variants
*   `dynamic_world`: Landcover (Built-up area, vegetation, water, etc.) via Sentinel-2. Native Scale: 10m.
*   `temperature`: Land Surface Temperature via MODIS. Native Scale: 1km. (Uses *Inferno* colormap).
*   `ozone`: Ozone Column Number Density via Sentinel-5P. Native Scale: ~7km. (Uses *Viridis* colormap).
*   `vegetation`: NDVI (Plant Health) via MODIS. Native Scale: 250m. (Uses *Viridis* colormap).

---

## Generated Outputs

Because the UrDev pipeline is dynamically driven by the configuration files and OSMnx queries, you can run it on varying geographical regions. Below are examples of the pipeline outputs demonstrating land-cover transitions over time.

### Manhattan, New York (2020 vs 2021)
| 2020 | 2021 |
|:---:|:---:|
| ![Manhattan 2020](assets/manhattan_2020.png) | ![Manhattan 2021](assets/manhattan_2021.png) |

*(Legend: Red denotes built-up/urban infrastructure, Green denotes vegetation, Blue denotes water bodies).*

### 10-Year Statistical Trend (Manhattan, NY)
Because the pipeline automatically runs `generate_analysis.py` after stitching the imagery, it exports exact pixel-area calculations (in km²) for every landcover class. 

Here is the exact progression of Manhattan's landcover over the decade:

| Year | Water | Trees | Grass | Flooded Veg | Crops | Shrub/Scrub | Built | Bare | Snow/Ice |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2016** | 95.25 | 5.85 | 2.35 | 4.25 | 0.80 | 1.97 | 266.76 | 2.65 | 2.11 |
| **2017** | 96.50 | 6.02 | 1.63 | 2.73 | 0.92 | 1.67 | 247.43 | 5.54 | 19.55 |
| **2018** | 93.82 | 5.65 | 2.07 | 4.50 | 0.84 | 2.68 | 267.89 | 2.93 | 1.61 |
| **2019** | 94.48 | 9.18 | 2.26 | 3.73 | 0.53 | 2.17 | 265.01 | 2.73 | 1.91 |
| **2020** | 93.67 | 9.07 | 2.61 | 4.21 | 0.70 | 2.37 | 264.01 | 3.90 | 1.45 |
| **2021** | 95.05 | 8.64 | 2.53 | 3.26 | 0.71 | 2.54 | 260.83 | 3.91 | 4.52 |
| **2022** | 94.79 | 6.73 | 2.55 | 3.75 | 0.63 | 2.66 | 263.05 | 3.74 | 4.10 |
| **2023** | 94.86 | 9.01 | 2.42 | 3.12 | 0.40 | 2.69 | 263.44 | 3.64 | 2.41 |
| **2024** | 94.89 | 9.72 | 2.22 | 2.84 | 0.99 | 2.18 | 261.09 | 2.66 | 5.38 |
| **2025** | 94.12 | 9.83 | 2.15 | 2.66 | 0.32 | 3.75 | 259.76 | 4.06 | 5.35 |
| **2026** | 94.68 | 12.30 | 2.15 | 2.36 | 0.70 | 1.73 | 261.74 | 2.34 | 4.00 |

---

## System Architecture
- **`generate.py`**: The main CLI orchestrator. It handles geocoding via OpenStreetMap, configuration file rewriting, and subprocess execution for the pipeline.
- **`pipeline/`**: The core modular Python codebase. It contains functions for fetching geometries (`boundary.py`), defining standardized grids (`tiler.py`), managing metadata schemas (`metadata.py`), and the **dataset registry** (`datasets.py`) for managing dataset-specific scales and reducers.
- **`scripts/`**: Executable runners that perform the heavy lifting:
  - `build_dataset.py`: Coordinates the asynchronous fetching and downloading of Earth Engine tiles into a local storage structure using dynamic parameters.
  - `generate_mosaic.py`: Utilizes `rasterio` and `WarpedVRT` to merge the individual geographical tiles into a cohesive raster array, applying color mappings (including pure NumPy mathematical gradients for continuous datasets, ensuring zero X11/matplotlib dependencies) before exporting as a `.png` and `.tif`.
  - `change_detection.py`: Analyzes per-pixel changes across temporal thresholds.
  - `visualize_dw.py`: Provides debugging tools to visually compare individual tile segments before the final merge.

### Data Output Structure
All raw and processed files are saved into an auto-generated, isolated data directory specific to the location and dataset queried. For example, running the pipeline for Singapore's Temperature generates the `urban_dataset_singapore_temperature/` directory with the following structure:

```text
urban_dataset_singapore_temperature/
├── dataset.json           # Master metadata file for the dataset (classes, region info)
├── metadata/
│   └── tiles.csv          # Catalog of every downloaded tile, bounding boxes, and pixel counts
├── temperature/           # Raw, unmodified GeoTIFF tiles downloaded from Earth Engine
│   ├── 2020/
│   │   ├── tile_r000_c001.tif
│   │   └── ...
│   └── 2021/
├── analysis/              # Exported CSVs of mathematical metrics (Mean, Min, Max, StdDev)
└── verification/          # Final processed outputs and visual mosaics
    ├── 2020/
    │   ├── mosaic.png         # The fully stitched, color-mapped composite heatmap
    │   └── mosaic_labels.tif  # The raw stitched raster data preserving exact continuous values
    └── 2021/
```

*(Note: These data output directories are explicitly ignored by version control to prevent inflating repository size with large TIFF files).*

---

## Future Goals & Edge Case Handling

As UrDev scales into a global analysis tool, several future goals and edge cases have been identified for future implementation:

### 1. Ward-Level / Sub-Polygon Processing
**Goal:** Instead of generating one massive dataset for an entire administrative region (like the entirety of Hyderabad), users should be able to generate individual datasets and comparative statistics for every sub-ward or county within that boundary.
**Edge Case to Handle:** Some regions do not have standardized administrative sub-levels (e.g., `admin_level=9` might work in India but fail in the US). We must query `osmnx` gracefully and fallback to broader levels (or custom grid divisions) if strict wards are unavailable.

### 2. Multi-Band Computations
**Goal:** Instead of just downloading a single band (e.g., Temperature or Landcover), the pipeline should support multi-band mathematical operations (like calculating custom indices such as NDWI for water or NDBI for built-up indices) directly from raw spectral bands (B4, B8, etc.) before downloading.
**Edge Case to Handle:** Different satellites have different band nomenclatures (Landsat 8 vs Sentinel-2). The Dataset Registry must abstract these computations to prevent pipeline crashes when switching satellites.

### 3. Asynchronous Geocoding Failures
**Goal:** Ensure the pipeline never halts due to network timeouts when communicating with OpenStreetMap Nominatim.
**Edge Case to Handle:** If Nominatim rate-limits the user, UrDev should implement exponential backoff retries. If the location is fundamentally unmappable via OSM polygons, the CLI should prompt the user to upload a custom local `.geojson` boundary file instead.

### 4. Geospatial Math & Projection Refactoring
**Goal:** Currently, pixel-area calculation dynamically assumes WGS84 (EPSG:4326) pixels map perfectly to their nominal metric size, which introduces slight distortion away from the equator. The pipeline should force Earth Engine to export tiles in a localized UTM projection to ensure flawless surface area math.

### 5. Server-Side Execution & Cloud Scaling
**Goal:** The current architecture uses a local config file and synchronous subprocesses, meaning it acts strictly as a single-user CLI.
- **Config Management:** Migrate to in-memory configuration passing (via `argparse` and environment variables) to eliminate the `config.yaml` disk-race condition and allow concurrent multi-tenant execution.
- **Server-Side Reduction:** Instead of downloading raw GeoTIFF tiles to disk purely to count pixels in a local CSV, we can execute `ee.Reducer.frequencyHistogram()` directly on Google's massive server clusters, reducing disk I/O bottlenecks and preventing Out-Of-Memory (OOM) errors during heavy transition matrix comparisons.
