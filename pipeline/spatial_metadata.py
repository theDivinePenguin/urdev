import os
import glob
import json
import csv
import rasterio
import numpy as np
from datetime import datetime

def generate_metadata(dataset_dir: str):
    raw_dir = os.path.join(dataset_dir, "raw", "dynamic_world")
    metadata_dir = os.path.join(dataset_dir, "metadata")
    verification_dir = os.path.join(dataset_dir, "verification")
    
    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(verification_dir, exist_ok=True)
    
    tiles_csv_path = os.path.join(metadata_dir, "tiles.csv")
    report_json_path = os.path.join(verification_dir, "dataset_report.json")
    
    # We will search for all tif files
    search_pattern = os.path.join(raw_dir, "**", "*.tif")
    tif_files = glob.glob(search_pattern, recursive=True)
    
    if not tif_files:
        print(f"No TIFF files found in {raw_dir}")
        return

    csv_rows = []
    
    # Variables for verification report
    years_found = set()
    total_tiles = 0
    invalid_tiles = []
    crs_set = set()
    
    print(f"Processing {len(tif_files)} tiles for metadata extraction...")
    
    for tif_path in tif_files:
        # Expected path structure: raw/dynamic_world/{year}/{filename}
        parts = tif_path.split(os.sep)
        year_str = parts[-2]
        filename = parts[-1]
        
        try:
            year = int(year_str)
            years_found.add(year)
        except ValueError:
            print(f"Warning: Unexpected directory structure for {tif_path}")
            continue
            
        tile_id = filename.replace(".tif", "")
        
        try:
            with rasterio.open(tif_path) as src:
                # Extract basic properties
                crs_val = src.crs.to_string() if src.crs else "UNKNOWN"
                crs_set.add(crs_val)
                
                # Bounds
                bounds = src.bounds
                bounds_str = f"[{bounds.left:.6f}, {bounds.bottom:.6f}, {bounds.right:.6f}, {bounds.top:.6f}]"
                
                res_x, res_y = src.res
                resolution = f"{res_x}x{res_y}"
                dimensions = f"{src.width}x{src.height}"
                
                # Calculate Area
                # Typically for geographic CRS (EPSG:4326), bounding box area is in degrees.
                # Since Dynamic World scale is often 10m but downloaded as degrees, we approximate
                # area if needed, but since we are extracting exact metadata, we can either store
                # bounds or estimate based on pixel count if we assume 10m scale.
                # The pipeline previously used 100/1_000_000 sq km per pixel (since 10x10m = 100sqm).
                pixel_area_sq_km = 100 / 1_000_000
                total_pixels = src.width * src.height
                area_km2 = total_pixels * pixel_area_sq_km
                
                # Read data for nodata and unique classes
                data = src.read(1)
                nodata_val = src.nodata if src.nodata is not None else 255
                
                nodata_mask = (data == nodata_val)
                nodata_pixels = int(nodata_mask.sum())
                
                valid_data = data[~nodata_mask]
                unique_classes = sorted(np.unique(valid_data).tolist())
                unique_classes_str = ",".join(map(str, unique_classes))
                
                # Calculate relative path from dataset_dir
                rel_path = os.path.relpath(tif_path, dataset_dir)
                
                csv_rows.append({
                    "tile_id": tile_id,
                    "filename": filename,
                    "year": year,
                    "bounds": bounds_str,
                    "crs": crs_val,
                    "resolution": resolution,
                    "dimensions": dimensions,
                    "path": rel_path,
                    "area_km2": round(area_km2, 6),
                    "nodata_pixels": nodata_pixels,
                    "unique_classes": unique_classes_str
                })
                total_tiles += 1
                
        except Exception as e:
            print(f"Error processing {tif_path}: {e}")
            invalid_tiles.append(tif_path)
            
    # Write to CSV
    if csv_rows:
        fieldnames = ["tile_id", "filename", "year", "bounds", "crs", "resolution", "dimensions", "path", "area_km2", "nodata_pixels", "unique_classes"]
        
        with open(tiles_csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(csv_rows, key=lambda x: (x['year'], x['tile_id'])):
                writer.writerow(row)
                
        print(f"Successfully generated {tiles_csv_path}")
        
    # Generate Verification Report
    report = {
        "total_tiles": total_tiles,
        "years": sorted(list(years_found)),
        "missing_tiles": [], # Could be calculated if we expect a perfect grid
        "invalid_tiles": invalid_tiles,
        "crs_consistent": len(crs_set) == 1,
        "crs_used": list(crs_set),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    with open(report_json_path, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"Successfully generated {report_json_path}")


if __name__ == '__main__':
    base_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'urdev', 'urban_dataset_v7')
    generate_metadata(base_dir)
