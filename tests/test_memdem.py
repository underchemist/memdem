"""Test DEMTiles."""
import os
from unittest import mock

import pytest
import rasterio
from affine import Affine

import memdem

from .conftest import fake_mem_dataset


def test_dem():
    dem = memdem.DEMTiles((0, 0, 1, 1), zoom=0)
    extent = [*dem.tms.boundingBox.lowerCorner, *dem.tms.boundingBox.upperCorner]
    assert dem.zoom == 0
    assert dem.width == 512
    assert dem.height == 512
    assert dem.shape == (512, 512)
    assert len(dem.tileset) == 1
    assert list(dem.bounds) == pytest.approx(extent)
    assert dem.transform == pytest.approx(
        Affine(
            78271.51696402031,
            0.0,
            -20037508.3427892,
            0.0,
            -78271.51696402031,
            20037508.3427892,
        )
    )
    assert dem.offsets == [(0, 0, 512, 512)]


@pytest.mark.parametrize(
    "pixel_size,expected",
    [(156543, 0), (4891.97, 4), (4891.0, 5), (305.75, 8), (4.777, 15)],
)
def test_dem_zoom_for_res(pixel_size, expected):
    """
    Ensure that we get the expected zoom levels.

    ref: https://docs.microsoft.com/en-us/azure/azure-maps/zoom-levels-and-tile-grid
    """
    d = memdem.DEMTiles((0, 0, 1, 1), pixel_size=pixel_size)
    assert d.zoom == expected


def test_dem_max_res():
    d = memdem.DEMTiles((0, 0, 1, 1), pixel_size=0.5)
    assert d.zoom == 17


def test_dem_get_s3_urls():
    d = memdem.DEMTiles((0, 0, 1, 1), zoom=0)
    assert "s3://elevation-tiles-prod/geotiff/0/0/0.tif" == d.get_tile_urls()[0]


def test_dem_from_dataset():
    mem, src = fake_mem_dataset()
    with mem:
        with src:
            d = memdem.DEMTiles.from_dataset(src, zoom=8)
            assert len(d.tileset) == 1
            assert d.zoom == 8
            tile = d.tileset[0]
            assert tile.x == 40
            assert tile.y == 87
            assert tile.z == 8


def test_dem_from_dataset_no_geotransform():
    src = mock.MagicMock()
    src.transform = Affine.identity()
    with pytest.raises(ValueError):
        memdem.DEMTiles.from_dataset(src, zoom=8)


def test_dem_from_dataset_no_crs():
    src = mock.MagicMock()
    src.crs = None
    with pytest.raises(ValueError):
        memdem.DEMTiles.from_dataset(src, zoom=8)


def test_dem_to_string():
    mem, src = fake_mem_dataset()
    with mem:
        with src:
            d = memdem.DEMTiles.from_dataset(src, zoom=8)
            assert d.to_string().startswith("<VRTDataset")


def test_dem_to_file(tmp_path):
    mem, src = fake_mem_dataset()
    with mem:
        with src:
            d = memdem.DEMTiles.from_dataset(src, zoom=8)
            out = tmp_path.joinpath("test.vrt")
            d.to_file(out)
            assert os.path.exists(out)
            with out.open() as f:
                s = f.read()
            assert s.startswith("<VRTDataset")


def test_dem_open():
    mem, src = fake_mem_dataset()
    with mem:
        with src:
            d = memdem.DEMTiles.from_dataset(src, zoom=8)
            with d.open() as dem:
                assert isinstance(dem, rasterio.DatasetReader)
                assert dem.count == 1
                assert dem.shape == dem.shape
                assert dem.crs == rasterio.crs.CRS.from_epsg(3857)
                assert dem.transform == dem.transform
