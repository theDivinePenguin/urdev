import os
import json
import csv
from datetime import datetime

def init_dataset_manifest(output_dir: str, config: dict, software_version: str = "0.1"):
    """
    Creates the dataset.json manifest file and initializes tiles.csv.
    """
    os.makedirs(output_dir, exist_ok=True)
    metadata_dir = os.path.join(output_dir, "metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    
    # 1. Write dataset.json
    manifest_path = os.path.join(output_dir, "dataset.json")
    manifest = {
        "city": config.get("city"),
        "dataset_version": config.get("dataset_version"),
        "source": config.get("source"),
        "years": [config.get("start_year"), config.get("end_year")],
        "tile_size": config.get("tile_size_px"),
        "projection": "EPSG:4326", # By default our boundaries are WGS84
        "created_at": datetime.utcnow().isoformat() + "Z",
        "software_version": software_version,
        "config": config # Full config for reproducibility
    }
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=4)
        
    # 2. Initialize tiles.csv if it doesn't exist
    csv_path = os.path.join(metadata_dir, "tiles.csv")
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "tile_id", "row", "col", "year", "source", 
                "path", "bbox", "valid_pixels", "nodata_pixels"
            ])

def append_tile_metadata(output_dir: str, tile_record: dict):
    """
    Appends a single tile record to tiles.csv.
    """
    csv_path = os.path.join(output_dir, "metadata", "tiles.csv")
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            tile_record.get("tile_id"),
            tile_record.get("row"),
            tile_record.get("col"),
            tile_record.get("year"),
            tile_record.get("source"),
            tile_record.get("path"),
            json.dumps(tile_record.get("bbox")),
            tile_record.get("valid_pixels", 0),
            tile_record.get("nodata_pixels", 0)
        ])
