"""Test custom TileMatrixSet."""
from rasterio.crs import CRS

from memdem.constants import ELEVATION_TILE_SIZE
from memdem.tms import default_tms


def test_elevationwebmercatorquad():
    assert "ElevationWebMercatorQuad" in default_tms.list()
    tms = default_tms.get("ElevationWebMercatorQuad")
    assert tms.crs == CRS.from_epsg(3857)
    matrix = tms.matrix(0)
    assert matrix.tileHeight == ELEVATION_TILE_SIZE
    assert matrix.tileWidth == ELEVATION_TILE_SIZE
