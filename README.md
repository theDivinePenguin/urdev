# 🌍 UrDev: Urban Expansion CLI

**UrDev** is an automated spatial analysis pipeline that leverages **Google Earth Engine (GEE)** to analyze and visualize urban land-cover expansion globally. 

Using high-resolution (10-meter) satellite imagery from Google Dynamic World V1, the CLI fetches geographic boundaries via OSMnx, securely accesses Earth Engine imagery through your local Google Cloud Project credentials, and generates composite images comparing land-cover classification across customizable timeframes.

---

## ⚡ Quick Start

### 1. Requirements and Setup
Ensure you have the Python dependencies installed (`osmnx`, `rasterio`, `geopandas`, etc.), and authenticate your local environment with Earth Engine:
```bash
earthengine authenticate
```
*Note: Your Earth Engine authentication must be associated with a valid Google Cloud Project. If initialization fails, link your project by running `earthengine set_project YOUR_PROJECT_ID`.*

### 2. Generating Geospatial Data
You can pass any globally recognized location to the entrypoint script. The pipeline will automatically geocode the administrative boundary, update the pipeline configuration, download the requisite tiles from Earth Engine, and generate the final image mosaics.
```bash
python generate.py --location "Manhattan, New York" --start-year 2020 --end-year 2021
```

---

## 📸 Generated Outputs

Because the UrDev pipeline is dynamically driven by the configuration files and OSMnx queries, you can run it on varying geographical regions. Below are examples of the pipeline outputs demonstrating land-cover transitions over time.

### 🏙️ Manhattan, New York (2020 vs 2021)
| 2020 | 2021 |
|:---:|:---:|
| ![Manhattan 2020](assets/manhattan_2020.png) | ![Manhattan 2021](assets/manhattan_2021.png) |

### 🇮🇳 Hyderabad, India (2016 vs 2026)
| 2016 | 2026 |
|:---:|:---:|
| ![Hyderabad 2016](assets/hyderabad_2016.png) | ![Hyderabad 2026](assets/hyderabad_2026.png) |

*(Legend: Red denotes built-up/urban infrastructure, Green denotes vegetation, Blue denotes water bodies).*

---

## 📁 System Architecture
- **`generate.py`**: The main CLI orchestrator. It handles geocoding via OpenStreetMap, configuration file rewriting, and subprocess execution for the pipeline.
- **`pipeline/`**: The core modular Python codebase. It contains functions for fetching geometries (`boundary.py`), defining standardized grids (`tiler.py`), and managing metadata schemas (`metadata.py`).
- **`scripts/`**: Executable runners that perform the heavy lifting:
  - `build_dataset.py`: Coordinates the asynchronous fetching and downloading of Earth Engine tiles into a local storage structure.
  - `generate_mosaic.py`: Utilizes `rasterio` and `WarpedVRT` to merge the individual geographical tiles into a cohesive raster array, applying color mappings before exporting as a `.png` and `.tif`.
  - `visualize_dw.py`: Provides debugging tools to visually compare individual tile segments before the final merge.

### Data Output Structure
All raw and processed files are saved into an auto-generated, isolated data directory specific to the location queried. For example, running the pipeline for Manhattan generates the `urban_dataset_manhattan_new_york/` directory with the following structure:

```text
urban_dataset_manhattan_new_york/
├── dataset.json           # Master metadata file for the dataset (classes, region info)
├── metadata/
│   └── tiles.csv          # Catalog of every downloaded tile, bounding boxes, and pixel counts
├── dynamic_world/         # Raw, unmodified GeoTIFF tiles downloaded from Earth Engine
│   ├── 2020/
│   │   ├── tile_r000_c001.tif
│   │   └── ...
│   └── 2021/
└── verification/          # Final processed outputs and visual mosaics
    ├── 2020/
    │   ├── mosaic.png         # The fully stitched, color-mapped composite image
    │   └── mosaic_labels.tif  # The raw stitched raster data preserving original labels
    └── 2021/
```

*(Note: These data output directories are explicitly ignored by version control to prevent inflating repository size with large TIFF files).*
