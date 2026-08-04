import argparse
import os
import re
import yaml
import subprocess
import osmnx as ox

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def update_config(config_path, location_slug, start_year, end_year):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update root config
    if 'roi' in config:
        config['roi']['boundary'] = location_slug
    config['start_year'] = start_year
    config['end_year'] = end_year
    config['dataset_version'] = location_slug
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)

def update_pipeline_config(config_path, location_slug, location_query, start_year, end_year):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    config['dataset']['name'] = f"urban_dataset_{location_slug}"
    # Optionally update visualizations if they use specific years
    config['visualizations']['years_to_mosaic'] = [start_year, end_year]
    config['regions']['osmnx_place_query'] = location_query
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description="Generate dynamic urban development images.")
    parser.add_argument('--location', type=str, required=True, help="City, State, Country (e.g., 'Austin, Texas, USA')")
    parser.add_argument('--start-year', type=int, default=2016, help="Start year (default 2016)")
    parser.add_argument('--end-year', type=int, default=2026, help="End year (default 2026)")
    args = parser.parse_args()

    slug = slugify(args.location)
    
    print(f"[*] Geocoding location: {args.location}")
    try:
        gdf = ox.geocode_to_gdf(args.location)
        area_km2 = gdf.to_crs(epsg=3857).area.iloc[0] / 1e6
        print(f"[*] Found boundary area: {area_km2:.2f} km²")
        os.makedirs('boundaries', exist_ok=True)
        geojson_path = f"boundaries/{slug}.geojson"
        gdf.to_file(geojson_path, driver="GeoJSON")
        print(f"[*] Saved boundary to {geojson_path}")
    except Exception as e:
        print(f"[!] Failed to fetch boundary for {args.location}: {e}")
        return

    print("[*] Updating configuration files...")
    update_config('config.yaml', slug, args.start_year, args.end_year)
    update_pipeline_config('pipeline/config.yaml', slug, args.location, args.start_year, args.end_year)

    # Run pipeline
    print("[*] Running dataset builder...")
    res = subprocess.run(["python", "scripts/build_dataset.py"])
    if res.returncode != 0:
        print("[!] Dataset building failed. (Check Earth Engine authentication)")
        return
        
    print("[*] Running mosaic generator...")
    subprocess.run(["python", "scripts/generate_mosaic.py"])

    print(f"[*] Done! Images for {args.location} generated in urban_dataset_{slug}/verification/")

if __name__ == "__main__":
    main()
