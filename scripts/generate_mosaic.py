import os
import glob
import rasterio
from rasterio.merge import merge
from rasterio.vrt import WarpedVRT
from PIL import Image
import numpy as np
import yaml
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.datasets import get_dataset_profile

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
    dataset_dir = "data/urban_dataset_" + config['dataset_version']
    dataset_name = config.get('dataset', 'dynamic_world')
    data_dir = os.path.join(dataset_dir, dataset_name)
    if not os.path.exists(data_dir):
        return
        
    years = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    for year in sorted(years):
        input_dir = os.path.join(data_dir, year)
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
        
        dataset_name = config.get('dataset', 'dynamic_world')
        dataset_profile = get_dataset_profile(dataset_name)
        
        if dataset_profile['type'] == 'categorical':
            rgb_map = np.array([hex_to_rgb_norm(c) for c in dw_colors] + [(0,0,0)], dtype=np.uint8)
            data_masked = np.where(data == 255, 9, data)
            rgb_image = rgb_map[data_masked]
        else:
            def apply_colormap(norm_data, colormap='inferno'):
                if colormap == 'inferno':
                    colors = np.array([
                        [0, 0, 4],       
                        [87, 16, 110],   
                        [187, 55, 84],   
                        [249, 142, 9],   
                        [252, 255, 164]  
                    ])
                elif colormap == 'viridis':
                    colors = np.array([
                        [68, 1, 84],     
                        [59, 82, 139],   
                        [33, 145, 140],  
                        [94, 201, 98],   
                        [253, 231, 37]   
                    ])
                else:
                    colors = np.array([[0, 0, 0], [255, 255, 255]])
                
                n_colors = len(colors)
                scaled = norm_data * (n_colors - 1)
                
                idx0 = np.floor(scaled).astype(int)
                idx1 = np.clip(idx0 + 1, 0, n_colors - 1)
                frac = scaled - idx0
                
                rgb = np.zeros(norm_data.shape + (3,), dtype=np.uint8)
                for i in range(3):
                    c0 = colors[idx0, i]
                    c1 = colors[idx1, i]
                    rgb[..., i] = c0 + (c1 - c0) * frac
                return rgb

            min_val = dataset_profile['vis_min']
            max_val = dataset_profile['vis_max']
            cmap_name = dataset_profile.get('colormap', 'viridis')
            
            valid_mask = (data != 255)
            norm_data = (data.astype(np.float32) - min_val) / (max_val - min_val)
            norm_data = np.clip(norm_data, 0, 1)
            
            rgb_image = apply_colormap(norm_data, cmap_name)
            rgb_image[~valid_mask] = (0, 0, 0)
        
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
