import math
import ee

def generate_tiles(boundary: ee.FeatureCollection, tile_size_px: int, scale_m: float = 10.0):
    """
    Generates a grid of tiles covering the boundary.
    
    Args:
        boundary: ee.FeatureCollection representing the city boundary.
        tile_size_px: The dimension of the tile in pixels (e.g., 512).
        scale_m: The physical size of a pixel in meters (e.g., 10.0 for Dynamic World).
        
    Returns:
        A list of dictionaries containing tile metadata and geometry.
    """
    # Get bounding box of the feature
    bounds = boundary.geometry().bounds().coordinates().getInfo()[0]
    
    xmin = min(p[0] for p in bounds)
    xmax = max(p[0] for p in bounds)
    ymin = min(p[1] for p in bounds)
    ymax = max(p[1] for p in bounds)
    
    # Calculate physical tile size in meters
    tile_size_m = tile_size_px * scale_m
    
    # 1 degree latitude is approximately 111.32 km
    lat_deg_per_m = 1.0 / 111320.0
    
    # Use average latitude to approximate longitude scaling
    avg_lat = (ymin + ymax) / 2.0
    lon_deg_per_m = 1.0 / (111320.0 * math.cos(math.radians(avg_lat)))
    
    tile_h_deg = tile_size_m * lat_deg_per_m
    tile_w_deg = tile_size_m * lon_deg_per_m
    
    tiles = []
    row = 0
    curr_y = ymax
    
    while curr_y > ymin:
        col = 0
        curr_x = xmin
        while curr_x < xmax:
            tile_xmin = curr_x
            tile_xmax = curr_x + tile_w_deg
            tile_ymin = curr_y - tile_h_deg
            tile_ymax = curr_y
            
            tile_geom = ee.Geometry.Rectangle([tile_xmin, tile_ymin, tile_xmax, tile_ymax])
            
            # Ensure the tile actually overlaps the city boundary to save space
            intersection = boundary.geometry().intersection(tile_geom, 100)
            area = intersection.area(100).getInfo()
            
            if area > 0:
                tiles.append({
                    'row': row,
                    'col': col,
                    'geom': tile_geom,
                    'bbox': [tile_xmin, tile_ymin, tile_xmax, tile_ymax]
                })
            
            curr_x += tile_w_deg
            col += 1
            
        curr_y -= tile_h_deg
        row += 1
        
    return tiles

def format_tile_name(row: int, col: int) -> str:
    """Formats the tile name with padded coordinates."""
    return f"tile_r{row:03d}_c{col:03d}"
