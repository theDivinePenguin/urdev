import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import rasterio
from PIL import Image
import numpy as np
from pipeline.tiler import format_tile_name
import yaml
import argparse

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

dw_colors = [
    '#419BDF', '#397D49', '#88B053', '#7A87C6', '#E49635',
    '#DFC35A', '#C4281B', '#A59B8F', '#B39FE1'
]
palette_rgb = [hex_to_rgb(c) for c in dw_colors]
for _ in range(256 - len(palette_rgb)):
    palette_rgb.append((0, 0, 0))

def apply_palette(img):
    flat_palette = [val for rgb in palette_rgb for val in rgb]
    pil_img = Image.fromarray(img.astype(np.uint8), mode='P')
    pil_img.putpalette(flat_palette)
    return pil_img.convert('RGB')

def visualize_tile(dataset_dir: str, row: int, col: int, year_start: int, year_end: int, output_png: str):
    tile_name = format_tile_name(row, col)
    
    # We construct paths directly based on the dataset structure standard    # We need to get dataset_name. We can read from config or assume passed.
    import yaml
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        dataset_name = config.get('dataset', 'dynamic_world')
    except:
        dataset_name = 'dynamic_world'
        
    tif_start = os.path.join(dataset_dir, dataset_name, str(year_start), f"{tile_name}.tif")
    tif_end = os.path.join(dataset_dir, dataset_name, str(year_end), f"{tile_name}.tif")
    
    if not os.path.exists(tif_start) or not os.path.exists(tif_end):
        print(f"Skipping visualization, missing tiles for {tile_name}")
        return

    try:
        with rasterio.open(tif_start) as src1:
            img_start = src1.read(1)
        with rasterio.open(tif_end) as src2:
            img_end = src2.read(1)
            
        pil_start = apply_palette(img_start)
        pil_end = apply_palette(img_end)
        
        total_width = pil_start.width + pil_end.width + 20
        max_height = max(pil_start.height, pil_end.height)
        
        combined = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        combined.paste(pil_start, (0, 0))
        combined.paste(pil_end, (pil_start.width + 20, 0))
        
        combined.save(output_png)
        print(f"Successfully created visualization at {output_png}")
        
    except Exception as e:
        print(f"Error visualizing: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--row', type=int, default=2)
    parser.add_argument('--col', type=int, default=2)
    args = parser.parse_args()
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    dataset_version = config.get('dataset_version', 'ghmc_new')
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"urban_dataset_{dataset_version}")
    out_dir = os.path.join(base_dir, 'visualizations')
    os.makedirs(out_dir, exist_ok=True)
    
    start_year = config.get('start_year', 2016)
    end_year = config.get('end_year', 2026)
    
    out_png = os.path.join(out_dir, f"tile_r{args.row:03d}_c{args.col:03d}_comparison.png")
    visualize_tile(base_dir, args.row, args.col, start_year, end_year, out_png)
