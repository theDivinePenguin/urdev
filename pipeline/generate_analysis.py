import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import json
import rasterio
import numpy as np
import argparse
from collections import defaultdict

def load_class_names(dataset_dir: str) -> dict:
    json_path = os.path.join(dataset_dir, "dataset.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            classes = data.get("classes")
            if classes:
                return {int(k): v for k, v in classes.items()}
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

def generate_continuous_statistics(dataset_dir: str, tiles_by_year: dict, out_csv: str):
    years = sorted(tiles_by_year.keys())
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["year", "mean", "min", "max", "std_dev"])
        
        for year in years:
            all_valid_data = []
            for tile_id, path in tiles_by_year[year].items():
                try:
                    with rasterio.open(path) as src:
                        data = src.read(1)
                        valid_data = data[data != 255]
                        all_valid_data.append(valid_data)
                except Exception as e:
                    print(f"Error reading {path}: {e}")
            
            if all_valid_data:
                combined = np.concatenate(all_valid_data)
                if len(combined) > 0:
                    mean_val = np.mean(combined)
                    min_val = np.min(combined)
                    max_val = np.max(combined)
                    std_dev = np.std(combined)
                    writer.writerow([year, round(mean_val, 4), round(min_val, 4), round(max_val, 4), round(std_dev, 4)])
                    print(f"Computed continuous statistics for {year}")
                else:
                    writer.writerow([year, 0, 0, 0, 0])
            else:
                writer.writerow([year, 0, 0, 0, 0])

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True, help="Path to the dataset directory")
    parser.add_argument("--start-year", type=int, required=True, help="Start year")
    parser.add_argument("--end-year", type=int, required=True, help="End year")
    parser.add_argument("--dataset", type=str, default="dynamic_world", help="Dataset name")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir
    analysis_dir = os.path.join(dataset_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    
    from pipeline.datasets import get_dataset_profile
    dataset_profile = get_dataset_profile(args.dataset)
    
    tiles_by_year = get_tiles_by_year(dataset_dir)
    
    if dataset_profile['type'] == 'categorical':
        class_names = load_class_names(dataset_dir)
        print("Generating yearly landcover statistics...")
        yearly_csv = os.path.join(analysis_dir, "yearly_landcover.csv")
        generate_yearly_landcover(dataset_dir, tiles_by_year, class_names, yearly_csv)
        
        # Generate transitions for specific pairs requested by user:
        pairs = [(args.start_year, args.end_year)]
        for y1, y2 in pairs:
            print(f"Generating transition matrix for {y1} to {y2}...")
            generate_transition_matrix(y1, y2, dataset_dir, tiles_by_year, class_names)
    else:
        print("Generating continuous regional statistics...")
        stats_csv = os.path.join(analysis_dir, "yearly_statistics.csv")
        generate_continuous_statistics(dataset_dir, tiles_by_year, stats_csv)
        
    print("Analysis Phase Complete.")

if __name__ == '__main__':
    main()
