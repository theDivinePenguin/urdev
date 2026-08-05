import os
import csv
import rasterio
import numpy as np

def calculate_dataset_changes(dataset_dir: str, year_start: int, year_end: int, dataset_name: str = "dynamic_world"):
    metadata_csv = os.path.join(dataset_dir, "metadata", "tiles.csv")
    if not os.path.exists(metadata_csv):
        print("Dataset metadata not found.")
        return

    # Load tiles mapped by (row, col)
    tiles_start = {}
    tiles_end = {}
    
    with open(metadata_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['source'] != source:
                continue
            r, c = row['row'], row['col']
            yr = int(row['year'])
            if yr == year_start:
                tiles_start[(r, c)] = row['path']
            elif yr == year_end:
                tiles_end[(r, c)] = row['path']

    pixel_to_sq_km = 100 / 1_000_000
    classes = {
        0: 'Water', 1: 'Trees', 2: 'Grass', 3: 'Flooded Vegetation',
        4: 'Crops', 5: 'Shrub & Scrub', 6: 'Built (Urban)',
        7: 'Bare', 8: 'Snow & Ice'
    }

    total_area_start = {k: 0.0 for k in classes}
    total_area_end = {k: 0.0 for k in classes}
    total_urban_sprawl = 0.0
    loss_sources = {k: 0.0 for k in classes}

    print(f"Comparing {year_start} vs {year_end} across the dataset...")
    
    for (r, c), path_start in tiles_start.items():
        if (r, c) not in tiles_end:
            continue
        
        path_end = tiles_end[(r, c)]
        
        with rasterio.open(os.path.join(dataset_dir, path_start)) as src1:
            img_start = src1.read(1).flatten()
            
        with rasterio.open(os.path.join(dataset_dir, path_end)) as src2:
            img_end = src2.read(1).flatten()
            
        for val in classes:
            total_area_start[val] += np.sum(img_start == val) * pixel_to_sq_km
            total_area_end[val] += np.sum(img_end == val) * pixel_to_sq_km
            
        new_urban_mask = (img_start != 6) & (img_end == 6)
        new_urban_pixels = img_start[new_urban_mask]
        
        total_urban_sprawl += len(new_urban_pixels) * pixel_to_sq_km
        unique, counts = np.unique(new_urban_pixels, return_counts=True)
        for val, count in zip(unique, counts):
            if val in loss_sources:
                loss_sources[val] += count * pixel_to_sq_km

    print("\n--- Total Area per Class (in Sq Km) ---")
    for val, name in classes.items():
        if val == 8: continue
        diff = total_area_end[val] - total_area_start[val]
        sign = "+" if diff > 0 else ""
        print(f"{name.ljust(20)}: {year_start}={total_area_start[val]:.1f}  |  {year_end}={total_area_end[val]:.1f}  |  Change={sign}{diff:.1f} sq km")

    print(f"\nTotal new urban sprawl: {total_urban_sprawl:.1f} sq km")
    print("What was destroyed to make room for this new city growth?")
    for val, sq_km in loss_sources.items():
        if sq_km > 1.0:
            print(f"  - Lost {sq_km:.1f} sq km of {classes[val]}")

if __name__ == '__main__':
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        config = __import__("yaml").safe_load(f)
    dataset_version = config.get("dataset_version", "ghmc_new")
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), f"urban_dataset_{dataset_version}")
    
    start_year = config.get("start_year", 2016)
    end_year = config.get("end_year", 2026)
    calculate_dataset_changes(base_dir, start_year, end_year)
