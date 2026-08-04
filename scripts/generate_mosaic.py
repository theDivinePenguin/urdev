import os
import glob
import rasterio
from rasterio.merge import merge
from rasterio.vrt import WarpedVRT
from PIL import Image
import numpy as np
import yaml

def hex_to_rgb_norm(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

dw_colors = [
    '#419BDF', '#397D49', '#88B053', '#7A87C6', '#E49635',
    '#DFC35A', '#C4281B', '#A59B8F', '#B39FE1'
]

def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    dataset_dir = "urban_dataset_" + config['dataset_version']
    dw_dir = os.path.join(dataset_dir, "dynamic_world")
    if not os.path.exists(dw_dir):
        return
        
    years = [d for d in os.listdir(dw_dir) if os.path.isdir(os.path.join(dw_dir, d))]
    
    for year in sorted(years):
        input_dir = os.path.join(dw_dir, year)
        out_dir = os.path.join(dataset_dir, "verification", year)
        os.makedirs(out_dir, exist_ok=True)
        
        tiles_paths = glob.glob(os.path.join(input_dir, "*.tif"))
        if not tiles_paths:
            continue

        print(f"[{year}] Stitching {len(tiles_paths)} tiles...")

        src_files = []
        vrts = []
        for fp in tiles_paths:
            src = rasterio.open(fp)
            src_files.append(src)
            vrt = WarpedVRT(src, src_nodata=255, nodata=255)
            vrts.append(vrt)
            
        mosaic, out_trans = merge(vrts, nodata=255)
        
        print(f"[{year}] Rendering lossless PNG and saving GeoTIFF...")
        data = mosaic[0]
        
        rgb_map = np.array([hex_to_rgb_norm(c) for c in dw_colors] + [(0,0,0)], dtype=np.uint8)
        data_masked = np.where(data == 255, 9, data)
        rgb_image = rgb_map[data_masked]
        
        png_path = os.path.join(out_dir, "mosaic.png")
        img = Image.fromarray(rgb_image, 'RGB')
        img.save(png_path)
        
        tif_path = os.path.join(out_dir, "mosaic_labels.tif")
        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "crs": src_files[0].crs
        })
        with rasterio.open(tif_path, "w", **out_meta) as dest:
            dest.write(mosaic)
        
        for vrt in vrts:
            vrt.close()
        for src in src_files:
            src.close()

if __name__ == '__main__':
    main()
