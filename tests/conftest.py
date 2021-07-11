import rasterio
from affine import Affine

from memdem.constants import ELEVATION_TILE_SIZE
from memdem.tms import default_tms

SEED_XY = (-123.17911189115098, 49.26435101976154)
SEED_ZOOM = 10
METERS_PER_TILE_AT_Z10 = 39135.8
INT16_NODATA = -32768


def fake_mem_dataset(index=0):
    crs = rasterio.crs.CRS.from_epsg(3857)
    tms = default_tms.get("ElevationWebMercatorQuad")
    seed_tile = tms.tile(*SEED_XY, zoom=SEED_ZOOM)
    transform = rasterio.transform.from_bounds(
        *tms.xy_bounds(seed_tile), ELEVATION_TILE_SIZE, ELEVATION_TILE_SIZE
    )
    transform = transform * Affine.translation(0, METERS_PER_TILE_AT_Z10 * index)
    mem = rasterio.MemoryFile()
    src = mem.open(
        driver="GTiff",
        width=ELEVATION_TILE_SIZE,
        height=ELEVATION_TILE_SIZE,
        count=1,
        crs=crs,
        dtype="int16",
        transform=transform,
        nodata=INT16_NODATA,
    )
    return (mem, src)
