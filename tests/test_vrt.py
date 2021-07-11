import rasterio
from affine import Affine

import memdem

from .conftest import fake_mem_dataset


def test_buildvrt():
    demtiles = memdem.DEMTiles((0, 0, 1, 1), zoom=10)
    urls = demtiles.get_tile_urls()
    vrt = memdem.vrt.buildvrt(
        urls, demtiles.shape, demtiles.offsets, demtiles.transform, demtiles.tms.crs
    )
    assert vrt.startswith("<VRTDataset")

    with rasterio.open(vrt) as src:
        assert src.count == 1
        assert src.shape == demtiles.shape
        assert src.crs == rasterio.crs.CRS.from_epsg(3857)
        assert src.transform == demtiles.transform


def test_buildvrt_axis_swap_crs():
    crs = rasterio.crs.CRS.from_epsg(4326)
    demtiles = memdem.DEMTiles((0, 0, 1, 1), zoom=10)
    urls = demtiles.get_tile_urls()
    vrt = memdem.vrt.buildvrt(
        urls, demtiles.shape, demtiles.offsets, demtiles.transform, crs
    )
    assert 'dataAxisToSRSAxisMapping="2,1"' in vrt
