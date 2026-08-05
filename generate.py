import argparse
import os
import re
import yaml
import subprocess
import osmnx as ox
import requests
import time

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def get_polygon_suggestions(query):
    print(f"[*] OpenStreetMap returned a Point. Searching for valid boundary alternatives...")
    suggestions = []
    
    url = "https://nominatim.openstreetmap.org/search"
    headers = {'User-Agent': 'urdev-cli-bot'}
    try:
        resp = requests.get(url, params={'q': query, 'format': 'json'}, headers=headers)
        if resp.status_code == 200 and len(resp.json()) > 0:
            display_name = resp.json()[0].get('display_name', '')
            parts = [p.strip() for p in display_name.split(',')]
            
            for i in range(1, len(parts)):
                candidate = ", ".join(parts[i:])
                # Skip numeric parts like zip codes
                if re.match(r'^[\d\s\W]+$', candidate):
                    continue
                
                c_resp = requests.get(url, params={'q': candidate, 'format': 'json', 'polygon_geojson': 1}, headers=headers)
                if c_resp.status_code == 200:
                    for item in c_resp.json():
                        geom_type = item.get('geojson', {}).get('type')
                        if geom_type in ['Polygon', 'MultiPolygon']:
                            if candidate not in suggestions:
                                suggestions.append(candidate)
                            break
                
                if len(suggestions) >= 3:
                    break
    except Exception as e:
        pass
    return suggestions

def update_config(config_path, location_slug, start_year, end_year, dataset_name, **kwargs):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update root config
    if 'roi' in config:
        config['roi']['boundary'] = location_slug
    config['start_year'] = start_year
    config['end_year'] = end_year
    config['dataset_version'] = f"{location_slug}_{dataset_name}"
    config['endpoints_only'] = kwargs.get('endpoints_only', False)
    config['dataset'] = dataset_name
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)

def update_pipeline_config(config_path, location_slug, location_query, start_year, end_year, dataset_name):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    config['dataset']['name'] = f"urban_dataset_{location_slug}_{dataset_name}"
    config['visualizations']['years_to_mosaic'] = [start_year, end_year]
    config['regions']['osmnx_place_query'] = location_query
    
    # Update dynamic change maps
    config['visualizations']['change_maps'] = [{
        'name': f"change_{start_year}_{end_year}",
        'year1': start_year,
        'year2': end_year,
        'target_class': 6,
        'highlight_color': [255, 0, 128, 255]
    }]
    config['analysis']['transition_pairs'] = [[start_year, end_year]]
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description="Generate dynamic urban development images.")
    parser.add_argument('--location', type=str, required=True, help="City, State, Country (e.g., 'Austin, Texas, USA')")
    parser.add_argument('--start-year', type=int, default=2016, help="Start year (default 2016)")
    parser.add_argument('--end-year', type=int, default=2026, help="End year (default 2026)")
    parser.add_argument('--yes', action='store_true', help="Skip interactive boundary confirmation")
    parser.add_argument('--endpoints-only', action='store_true', help="Only download start and end years (skip middle years)")
    parser.add_argument('--dataset', type=str, default='dynamic_world', help="Dataset to process (e.g. dynamic_world, temperature, ozone)")
    args = parser.parse_args()

    args_location = args.location
    
    while True:
        slug = slugify(args_location)
        print(f"[*] Geocoding location: {args_location}")
        try:
            gdf = ox.geocode_to_gdf(args_location)
            area_km2 = gdf.to_crs(epsg=3857).area.iloc[0] / 1e6
            print(f"[*] Found boundary area: {area_km2:.2f} km²")
            os.makedirs('boundaries', exist_ok=True)
            geojson_path = f"boundaries/{slug}.geojson"
            gdf.to_file(geojson_path, driver="GeoJSON")
            print(f"[*] Saved boundary to {geojson_path}")
            
            if not args.yes:
                ans = input(f"[*] Do you want to proceed with downloading Earth Engine data for this {area_km2:.2f} km² area? [y/N]: ")
                if ans.lower() not in ['y', 'yes']:
                    print("[-] Aborted by user. Review the geojson boundary if it was too large.")
                    return
            break # successful geocoding
        except Exception as e:
            if "Nominatim did not geocode query" in str(e) or "geometry of type (Multi)Polygon" in str(e):
                suggestions = get_polygon_suggestions(args_location)
                if suggestions:
                    print("\n[!] OpenStreetMap returned a 'Point' instead of a 'Polygon'.")
                    print("[?] Did you mean one of these administrative boundaries?")
                    for idx, s in enumerate(suggestions, 1):
                        print(f"  {idx}. {s}")
                    print("  0. Exit")
                    
                    choice = input("Enter choice (0-{}): ".format(len(suggestions)))
                    try:
                        choice_idx = int(choice)
                        if choice_idx == 0:
                            print("[-] Aborted.")
                            return
                        elif 1 <= choice_idx <= len(suggestions):
                            args_location = suggestions[choice_idx - 1]
                            continue
                    except ValueError:
                        pass
            
            print(f"[!] Failed to fetch boundary for {args_location}: {e}")
            return

    print("[*] Updating configuration files...")
    update_config('config.yaml', slug, args.start_year, args.end_year, args.dataset, endpoints_only=args.endpoints_only)
    update_pipeline_config('pipeline/config.yaml', slug, args_location, args.start_year, args.end_year, args.dataset)

    # Run pipeline
    print("[*] Running dataset builder...")
    res = subprocess.run(["python", "scripts/build_dataset.py"])
    if res.returncode != 0:
        print("[!] Dataset building failed. (Check Earth Engine authentication)")
        return
        
    print("[*] Running mosaic generator...")
    subprocess.run(["python", "scripts/generate_mosaic.py"])
    
    print("[*] Running analysis generator...")
    subprocess.run([
        "python", "pipeline/generate_analysis.py", 
        "--dataset-dir", f"urban_dataset_{slug}_{args.dataset}",
        "--start-year", str(args.start_year),
        "--end-year", str(args.end_year),
        "--dataset", args.dataset
    ])

    print(f"[*] Done! Images for {args.location} generated in urban_dataset_{slug}_{args.dataset}/verification/")

if __name__ == "__main__":
    main()
