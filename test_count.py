import ee
import json

ee.Initialize(project='ai-sandbox-company')

bbox = [103.601, 1.229, 104.043, 1.474]
geom = ee.Geometry.Rectangle(bbox)

col_2016 = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(geom).filterDate('2016-01-01', '2016-05-28')
col_2026 = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(geom).filterDate('2024-01-01', '2024-05-28') # using 2024 since 2026 doesn't exist yet

print("2016 count:", col_2016.size().getInfo())
print("2024 count:", col_2026.size().getInfo())
