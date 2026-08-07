import os
import csv
import rasterio
import numpy as np
import argparse
from collections import defaultdict

def get_tiles_by_year(dataset_dir: str):
    csv_path = os.path.join(dataset_dir, "metadata", "tiles.csv")
    tiles = defaultdict(dict)
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row['year'])
            r, c = row['row'], row['col']
            tiles[year][(r, c)] = os.path.join(dataset_dir, row['path'])
    return tiles

def analyze_vegetation_change(dataset_dir: str, year_start: int, year_end: int):
    tiles_by_year = get_tiles_by_year(dataset_dir)
    
    if year_start not in tiles_by_year or year_end not in tiles_by_year:
        print(f"Data not found for {year_start} or {year_end}.")
        return

    out_csv = os.path.join(dataset_dir, "analysis", f"vegetation_change_{year_start}_{year_end}.csv")
    pixel_area_km2 = 100 / 1_000_000  # 10m x 10m pixels
    
    # We will classify the NDVI change into buckets
    # Note: NDVI is scaled by 10000. So 1000 means a 0.1 change in NDVI.
    categories = {
        "Significant Loss (<-0.2)": 0.0,
        "Minor Loss (-0.2 to -0.05)": 0.0,
        "Stable (-0.05 to 0.05)": 0.0,
        "Minor Gain (0.05 to 0.2)": 0.0,
        "Significant Gain (>0.2)": 0.0
    }
    
    common_tiles = set(tiles_by_year[year_start].keys()).intersection(set(tiles_by_year[year_end].keys()))
    print(f"Analyzing changes across {len(common_tiles)} tiles from {year_start} to {year_end}...")

    for tile_id in common_tiles:
        path_start = tiles_by_year[year_start][tile_id]
        path_end = tiles_by_year[year_end][tile_id]
        
        try:
            with rasterio.open(path_start) as src1, rasterio.open(path_end) as src2:
                data_start = src1.read(1).astype(np.float32)
                data_end = src2.read(1).astype(np.float32)
                
                # Ignore nodata values (assumed to be 255 if it was categorical, but usually -32768 or similar for continuous)
                # For MODIS NDVI, nodata is typically -3000 but we'll use a valid range mask based on datasets.py config (-2000 to 10000)
                valid_mask = (data_start >= -2000) & (data_start <= 10000) & (data_end >= -2000) & (data_end <= 10000)
                
                start_valid = data_start[valid_mask]
                end_valid = data_end[valid_mask]
                
                # Calculate difference (End - Start). 
                # Scaled by 10000, so we divide by 10000 to get actual NDVI difference
                diff = (end_valid - start_valid) / 10000.0
                
                categories["Significant Loss (<-0.2)"] += np.sum(diff < -0.2) * pixel_area_km2
                categories["Minor Loss (-0.2 to -0.05)"] += np.sum((diff >= -0.2) & (diff < -0.05)) * pixel_area_km2
                categories["Stable (-0.05 to 0.05)"] += np.sum((diff >= -0.05) & (diff <= 0.05)) * pixel_area_km2
                categories["Minor Gain (0.05 to 0.2)"] += np.sum((diff > 0.05) & (diff <= 0.2)) * pixel_area_km2
                categories["Significant Gain (>0.2)"] += np.sum(diff > 0.2) * pixel_area_km2

        except Exception as e:
            print(f"Error processing {tile_id}: {e}")

    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["change_category", "area_km2"])
        for cat, area in categories.items():
            writer.writerow([cat, round(area, 4)])
            print(f"{cat.ljust(30)}: {area:.4f} km^2")
            
    print(f"\nResults saved to {out_csv}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True, help="Path to the dataset directory")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2021)
    args = parser.parse_args()
    
    analyze_vegetation_change(args.dataset_dir, args.start_year, args.end_year)
