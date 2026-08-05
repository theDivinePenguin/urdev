import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ee
import yaml
import requests
import zipfile
import io
import rasterio

from pipeline.boundary import get_city_boundary
from pipeline.tiler import generate_tiles, format_tile_name
from pipeline.metadata import init_dataset_manifest, append_tile_metadata
from pipeline.datasets import get_dataset_profile

def load_config(config_path="config.yaml"):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_pixel_counts(tif_path):
    try:
        with rasterio.open(tif_path) as src:
            data = src.read(1)
            nodata_val = 255
            valid_mask = (data != nodata_val)
            return int(valid_mask.sum()), int((~valid_mask).sum())
    except Exception as e:
        print(f"Error reading {tif_path}: {e}")
        return 0, 0

def download_tile(image, tile, year, source, output_dir, scale=10):
    tile_name = format_tile_name(tile['row'], tile['col'])
    filename = f"{tile_name}.tif"
    year_dir = os.path.join(output_dir, source, str(year))
    os.makedirs(year_dir, exist_ok=True)
    filepath = os.path.join(year_dir, filename)
    
    if os.path.exists(filepath):
        print(f"Skipping {filepath}, already exists.")
        valid, nodata = get_pixel_counts(filepath)
        return filepath, valid, nodata

    try:
        url = image.getDownloadURL({
            'scale': scale,
            'region': tile['geom'],
            'format': 'GEO_TIFF'
        })
        print(f"Downloading {tile_name} for {year}...")
        response = requests.get(url)
        if response.status_code == 200:
            try:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    tif_files = [f for f in z.namelist() if f.endswith('.tif')]
                    if tif_files:
                        with open(filepath, 'wb') as f:
                            f.write(z.read(tif_files[0]))
                    else:
                        print(f"No tif found in zip for {tile_name}")
                        return None, 0, 0
            except zipfile.BadZipFile:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
            
            valid, nodata = get_pixel_counts(filepath)
            return filepath, valid, nodata
        else:
            print(f"Failed to download {tile_name}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Earth Engine error on {tile_name}: {e}")
    return None, 0, 0

def build_dataset(config):
    dataset_dir = f"urban_dataset_{config['dataset_version']}"
    os.makedirs(dataset_dir, exist_ok=True)
    
    # 1. Initialize Metadata Manifest
    init_dataset_manifest(dataset_dir, config)
    
    # 2. Get Boundary
    print(f"Fetching boundary for {config['roi']['boundary']}...")
    boundary = get_city_boundary(config)
    
    # 3. Generate Tiles
    print("Generating tiles...")
    tiles = generate_tiles(boundary, config['tile_size_px'])
    if not tiles:
        print(f"No tiles generated for {config['roi']['boundary']}. Exiting.")
        return
        
    print(f"Generated {len(tiles)} tiles intersecting {config['roi']['boundary']}.")
    
    # 4. Download per year
    start_year = config['start_year']
    end_year = config['end_year']
    
    endpoints_only = config.get('endpoints_only', False)
    if endpoints_only and start_year != end_year:
        years_to_process = [start_year, end_year]
    else:
        years_to_process = range(start_year, end_year + 1)
    
    dataset_name = config.get('dataset', 'dynamic_world')
    dataset_profile = get_dataset_profile(dataset_name)
    
    for year in years_to_process:
        start_date = f"{year}-{config['season']['start_month']:02d}-01"
        end_date = f"{year}-{config['season']['end_month']:02d}-28"
        
        collection = ee.ImageCollection(dataset_profile['collection']) \
               .filterBounds(boundary.geometry()) \
               .filterDate(start_date, end_date)
               
        # Handle globally sparse early years cleanly
        sparse_year = dataset_profile.get('sparse_before_year')
        if sparse_year and year < sparse_year:
            print(f"[{year}] Year is prior to reliable dense coverage (sparse_before_year={sparse_year}). Expanding search to full year {year}...")
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            collection = ee.ImageCollection(dataset_profile['collection']) \
                   .filterBounds(boundary.geometry()) \
                   .filterDate(start_date, end_date)
               
        if dataset_profile['reducer'] == 'mode':
            image = collection.select(dataset_profile['band']).mode().unmask(255)
        elif dataset_profile['reducer'] == 'mean':
            image = collection.select(dataset_profile['band']).mean().unmask(255)
        else:
            image = collection.select(dataset_profile['band']).first().unmask(255) # fallback
        
        for tile in tiles:
            filepath, valid_px, nodata_px = download_tile(
                image, tile, year, dataset_name, dataset_dir, scale=dataset_profile['scale']
            )
            
            if filepath:
                # Append to metadata
                # Use relative path for portability
                rel_path = os.path.relpath(filepath, dataset_dir)
                tile_id = f"{source}_{year}_{format_tile_name(tile['row'], tile['col'])}"
                record = {
                    "tile_id": tile_id,
                    "row": tile['row'],
                    "col": tile['col'],
                    "year": year,
                    "source": source,
                    "path": rel_path,
                    "bbox": tile['bbox'],
                    "valid_pixels": valid_px,
                    "nodata_pixels": nodata_px
                }
                append_tile_metadata(dataset_dir, record)

        print(f"--- Completed {year} ---")

    print("\n--- Pipeline Execution Complete ---")

if __name__ == '__main__':
    try:
        ee.Initialize()
    except Exception as e:
        print(f"Earth Engine Initialization Failed: {e}")
        print("If you see 'no project found', you need to set a default Google Cloud project.")
        print("Run: earthengine set_project YOUR_PROJECT_ID")
        sys.exit(1)
        
    cfg = load_config()
    build_dataset(cfg)
