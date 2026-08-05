# UrDev: Complete Code Architecture & Execution Flow

This document outlines the exact execution sequence of the UrDev Environmental Engine and provides a comprehensive dictionary of every module and function powering the pipeline.

## 1. High-Level Execution Sequence

When a user runs `python generate.py --location "Singapore" --start-year 2020 --end-year 2021 --dataset temperature`, the pipeline executes in the following sequence:

1. **Initialization (`generate.py`)**: The CLI orchestrator parses the arguments and geocodes the requested location using OpenStreetMap. If OSM returns a singular point, it falls back to suggesting valid multi-polygon sub-boundaries. It then dynamically rewrites `config.yaml` to point the entire pipeline to the target dataset and years.
2. **Data Acquisition (`scripts/build_dataset.py`)**: 
   - The dataset profile (e.g., Temperature, Landcover) is loaded from the Registry.
   - The city's spatial boundary is sliced into a standardized mathematical grid (tiles).
   - The script queries Google Earth Engine for the exact date range. (If the year is known to be sparse, like 2016 for Sentinel-2, it dynamically expands to a 12-month calendar).
   - Every tile is downloaded locally as a raw GeoTIFF to the `urban_dataset_...` directory.
3. **Mosaicking & Colorization (`scripts/generate_mosaic.py`)**:
   - The raw mathematical GeoTIFF tiles for a given year are stitched together into one massive seamless raster array.
   - Depending on the dataset type, a colorization algorithm is applied (Hardcoded categorical colors for Landcover, or pure-NumPy mathematical gradients like Inferno/Viridis for continuous datasets).
   - The final colorized map is exported as a lossless `.png` and `.tif`.
4. **Statistical Analysis (`pipeline/generate_analysis.py`)**:
   - The raw mathematical arrays are scanned pixel-by-pixel.
   - For categorical datasets, it exports total physical area (km²) per class.
   - For continuous datasets, it exports regional averages, mins, maxes, and standard deviations.

---

## 2. Module & Function Dictionary

### `generate.py`
The master entrypoint and CLI orchestrator.
- `get_polygon_suggestions(query)`: Queries Nominatim API. Detects if a location resolves to a point and automatically suggests broader polygon-based geometries (like counties or states).
- `update_config()`: Mutates the global `config.yaml` file to set the dataset, bounding region, and temporal targets for the current run.
- `update_pipeline_config()`: Helper function to rewrite deeply nested pipeline variables.
- *(Main Block)*: Executes the independent scripts sequentially via `subprocess`.

### `pipeline/datasets.py`
The centralized Dataset Registry governing how Earth Engine interacts with various satellites.
- `DATASET_REGISTRY`: Dictionary defining Earth Engine Collection IDs, native scales (resolution in meters), reducers (`mean` vs `mode`), and fallback rules (`sparse_before_year`).
- `get_dataset_profile(name)`: Validates and retrieves the configuration payload for a requested dataset (e.g., `dynamic_world`, `temperature`, `ozone`).

### `pipeline/boundary.py`
Handles all spatial geometry logic.
- `get_city_boundary(place_name)`: Interfaces with `osmnx` to download and project exact multipolygon boundaries for administrative zones.

### `pipeline/tiler.py`
Handles mathematical division of massive geometries into digestible chunks to prevent memory/API timeouts.
- `generate_tiles(boundary_gdf, tile_size)`: Generates a mathematically perfect grid of bounding boxes overlapping the target city boundary.
- `format_tile_name(row, col)`: Enforces standardized nomenclature for tile files (e.g., `tile_r001_c005.tif`).

### `pipeline/metadata.py`
Handles the logging of data acquisition metrics.
- `init_dataset_manifest()`: Bootstraps a `dataset.json` file in the output directory detailing the dataset classes and bounding parameters.
- `append_tile_metadata()`: Updates `tiles.csv` with the exact coordinate bounds, valid pixel count, and nodata pixel count for every downloaded tile.

### `pipeline/spatial_metadata.py`
Used for downstream applications requiring spatial indexing.
- `generate_metadata(dataset_dir)`: Scans the output directory and generates a structured JSON tree of all available files, sizes, and timestamps.

### `pipeline/generate_analysis.py`
The statistical engine.
- `load_class_names()`: Reads dataset labels from the manifest.
- `get_tiles_by_year()`: Recursively parses the local storage directories.
- `generate_yearly_landcover()`: Computes exact physical surface area (km²) by counting pixels multiplied by native scale for categorical data.
- `generate_continuous_statistics()`: Computes NumPy array statistics (Mean, Min, Max, StdDev) for continuous environmental data (e.g., temperature).
- `generate_transition_matrix()`: Scans identical pixels across two temporal points to compute exact change trajectories (e.g., X sq-km of Forest transitioned into Built-Up Area).

### `scripts/build_dataset.py`
The Earth Engine asynchronous downloader.
- `load_config()`: Parses `config.yaml`.
- `download_tile()`: Constructs an Earth Engine payload for a specific mathematical bounding box, applies the required reducer (`mode` or `mean`), formats it to the dataset's native scale, and downloads it locally.
- `main()`: Orchestrates the bounding boxes, validates the temporal fallback (`sparse_before_year`), and queues the downloads.

### `scripts/generate_mosaic.py`
The image processing and rendering engine.
- `hex_to_rgb_norm()`: Converts web hex codes to 0-255 RGB arrays for categorical color mapping.
- `apply_colormap()`: A custom pure-NumPy mathematical function that generates continuous thermal gradients (Inferno, Viridis) without relying on heavy external dependencies like Matplotlib.
- `main()`: Uses `rasterio`'s `WarpedVRT` to perfectly stitch dozens of disjointed GeoTIFF tiles together based on their geospatial headers, applies the colorization functions, and exports the final visual maps.

### `scripts/change_detection.py`
A specialized diff-engine for visualizing mathematical variance between years.
- `calculate_dataset_changes()`: Subtracts raster arrays to output a pure "change-only" visual map (e.g., rendering only pixels that have undergone deforestation).

### `scripts/visualize_dw.py`
A debugging utility.
- `visualize_tile()`: Renders side-by-side visual comparisons of single raw tiles before they are mosaicked, used for verifying Earth Engine reductions and boundary clipping.
