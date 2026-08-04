import os
import csv
import json
import rasterio
import numpy as np
from collections import defaultdict

def load_class_names(dataset_dir: str) -> dict:
    json_path = os.path.join(dataset_dir, "dataset.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.get("classes", {}).items()}
    # Fallback
    return {
        0: 'Water', 1: 'Trees', 2: 'Grass', 3: 'Flooded vegetation',
        4: 'Crops', 5: 'Shrub and scrub', 6: 'Built', 7: 'Bare ground',
        8: 'Snow and ice'
    }

def get_tiles_by_year(dataset_dir: str):
    csv_path = os.path.join(dataset_dir, "metadata", "tiles.csv")
    tiles = defaultdict(dict)
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row['year'])
            tile_id = row['tile_id']
            # Important: the path in CSV is relative to dataset_dir
            tiles[year][tile_id] = os.path.join(dataset_dir, row['path'])
    return tiles

def generate_yearly_landcover(dataset_dir: str, tiles_by_year: dict, class_names: dict, out_csv: str):
    pixel_area_km2 = 100 / 1_000_000  # 10m x 10m
    years = sorted(tiles_by_year.keys())
    
    with open(out_csv, 'w', newline='') as f:
        # Header: year,water,trees,grass,flooded_vegetation,crops,shrub,built,bare,snow
        class_ids = sorted(class_names.keys())
        header = ["year"] + [class_names[c].lower().replace(' ', '_') for c in class_ids]
        writer = csv.writer(f)
        writer.writerow(header)
        
        for year in years:
            class_totals = {c: 0.0 for c in class_ids}
            for tile_id, path in tiles_by_year[year].items():
                try:
                    with rasterio.open(path) as src:
                        data = src.read(1)
                        # np.unique returns unique values and their counts
                        unique, counts = np.unique(data, return_counts=True)
                        for val, count in zip(unique, counts):
                            if val in class_totals:
                                class_totals[val] += count * pixel_area_km2
                except Exception as e:
                    print(f"Error reading {path}: {e}")
                    
            row = [year] + [round(class_totals[c], 6) for c in class_ids]
            writer.writerow(row)
            print(f"Computed landcover for {year}")

def generate_transition_matrix(year1: int, year2: int, dataset_dir: str, tiles_by_year: dict, class_names: dict):
    out_csv = os.path.join(dataset_dir, "analysis", f"transition_matrix_{year1}_{year2}.csv")
    pixel_area_km2 = 100 / 1_000_000
    
    tiles_y1 = tiles_by_year.get(year1, {})
    tiles_y2 = tiles_by_year.get(year2, {})
    
    common_tiles = set(tiles_y1.keys()).intersection(set(tiles_y2.keys()))
    
    transitions = defaultdict(float)
    
    for tile_id in common_tiles:
        try:
            with rasterio.open(tiles_y1[tile_id]) as src1, rasterio.open(tiles_y2[tile_id]) as src2:
                data1 = src1.read(1).flatten()
                data2 = src2.read(1).flatten()
                
                # We only care about valid transitions (ignore 255)
                valid = (data1 != 255) & (data2 != 255)
                d1_valid = data1[valid]
                d2_valid = data2[valid]
                
                # Create a 2D histogram/confusion matrix
                # Max class value is typically 8, so we can use bincount or histogram2d
                # Or simply zip and count (can be slow in python, so numpy is better)
                # Combine class ids: since they are 0-8, we can do d1 * 10 + d2
                combined = d1_valid * 10 + d2_valid
                unique, counts = np.unique(combined, return_counts=True)
                
                for val, count in zip(unique, counts):
                    c1 = val // 10
                    c2 = val % 10
                    transitions[(c1, c2)] += count * pixel_area_km2
        except Exception as e:
            print(f"Error processing transition for {tile_id}: {e}")
            
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["from_class", "to_class", "area_km2"])
        for (c1, c2), area in sorted(transitions.items()):
            from_name = class_names.get(c1, str(c1))
            to_name = class_names.get(c2, str(c2))
            writer.writerow([from_name, to_name, round(area, 6)])
            
    print(f"Generated transition matrix {year1} -> {year2}")

def main():
    dataset_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'urdev', 'urban_dataset_v7')
    analysis_dir = os.path.join(dataset_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    
    class_names = load_class_names(dataset_dir)
    tiles_by_year = get_tiles_by_year(dataset_dir)
    
    print("Generating yearly landcover statistics...")
    yearly_csv = os.path.join(analysis_dir, "yearly_landcover.csv")
    generate_yearly_landcover(dataset_dir, tiles_by_year, class_names, yearly_csv)
    
    # Generate transitions for specific pairs requested by user:
    # 2016-2026, 2016-2020, 2020-2026
    pairs = [(2016, 2026), (2016, 2020), (2020, 2026)]
    for y1, y2 in pairs:
        print(f"Generating transition matrix for {y1} to {y2}...")
        generate_transition_matrix(y1, y2, dataset_dir, tiles_by_year, class_names)
        
    print("Analysis Phase Complete.")

if __name__ == '__main__':
    main()
