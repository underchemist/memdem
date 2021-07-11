"""Module for generating DEM."""
from contextlib import contextmanager
from functools import wraps
from os import PathLike
from typing import Iterator, Optional, Sequence, Tuple, Union

import morecantile
import rasterio
import rasterio.shutil

from memdem.constants import ELEVATION_TILE_SIZE, SERVICE_S3_URL
from memdem.tms import default_tms
from memdem.vrt import buildvrt


class DEMTiles:
    """
    DEM tiles.

    Attributes
    ----------
    tms : morecantile.TileMatrixSet
        Custom TileMatrixSet for Elevation Tiles dataset. Adapted from
        WebMercatorQuad with 512x512 tile size.
    """

    tms: morecantile.TileMatrixSet = default_tms.get("ElevationWebMercatorQuad")

    def __init__(
        self,
        bounds: Union[Tuple[float, float, float, float], rasterio.coords.BoundingBox],
        zoom: int = 8,
        pixel_size: Optional[float] = None,
    ):
        """
        Define the parameters needed to build a virtual DEM.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float] or rasterio.coords.BoundingBox
            The bounding box describing the area of interest in geographic coordinates.
            Tiles overlapping this bounding box will be collected for the specified
            zoom level.
        zoom : int
            Zoom level to use.
        pixel_size : float, optional
            Desired pixel size. Used to compute a suitable zoom level from
            TileMatrixSet.zoom_for_res.

        Attributes
        ----------
        tileset : Sequence of morecantile.Tile
            The tiles overlapping the bounds.
        zoom : int
            The zoom level to use, either as specified or as computed by
            TileMatrixSet.zoom_for_res using the zoom_level_strategy="upper"
        nx, ny : int
            The number of tiles in the x and y dimensions, respectively.
        """
        self.zoom = zoom
        if pixel_size:
            self.zoom = self.tms.zoom_for_res(pixel_size, zoom_level_strategy="upper")

        tileset = self.tms.tiles(*bounds, zooms=self.zoom)
        self.tileset, self.nx, self.ny = self._extract_tileset(tileset)

        self._width = self._get_width()
        self._height = self._get_height()
        self._shape = self._get_shape()
        self._offsets = self._get_offsets()
        self._transform = self._get_transform()
        self._bounds = self._get_bounds()

    @property
    def width(self):
        """Return the width of the DEM in pixels."""
        return self._width

    def _get_width(self):
        return self.nx * ELEVATION_TILE_SIZE

    @property
    def height(self):
        """Return the height of the DEM in pixels."""
        return self._height

    def _get_height(self):
        return self.ny * ELEVATION_TILE_SIZE

    @property
    def shape(self):
        """Return the (height, width) of the DEM in pixels."""
        return self._shape

    def _get_shape(self):
        return (self.height, self.width)

    @property
    def offsets(self):
        """Return a sequence of (xoffset, yoffset, xsize, ysize) corresponding to each Tile in tileset. Used to mosaic individual tiles into a single DEM."""
        return self._offsets

    def _get_offsets(self):
        offsets = []
        first_tile = next(iter(self.tileset))
        startx = first_tile.x
        starty = first_tile.y
        for tile in self.tileset:
            dst_idxx = tile.x - startx
            dst_idxy = tile.y - starty
            offsets.append(
                (
                    ELEVATION_TILE_SIZE * dst_idxx,
                    ELEVATION_TILE_SIZE * dst_idxy,
                    ELEVATION_TILE_SIZE,
                    ELEVATION_TILE_SIZE,
                )
            )
        return offsets

    @property
    def bounds(self):
        """Return bounds of tileset in tile crs."""
        return self._bounds

    def _get_bounds(self):
        left, bottom, right, top = (0, self.height, self.width, 0)
        left, bottom = self.transform * (left, bottom)
        right, top = self.transform * (right, top)
        return rasterio.coords.BoundingBox(
            left=left, bottom=bottom, right=right, top=top
        )

    @property
    def transform(self):
        """Return geotransform for tileset in tile crs."""
        return self._transform

    def _get_transform(self):
        matrix = self.tms.matrix(self.zoom)
        pixel_size = self.tms._resolution(matrix)

        ul_tile = min(self.tileset)
        coords = self.tms.ul(ul_tile)
        coords_xy = self.tms.xy(*coords)
        return rasterio.transform.from_origin(*coords_xy, pixel_size, pixel_size)

    def _extract_tileset(
        self, tiles: Iterator[morecantile.Tile]
    ) -> Tuple[Sequence[morecantile.Tile], int, int]:
        tileset = []
        x = []
        y = []
        for tile in tiles:
            tileset.append(tile)
            x.append(tile.x)
            y.append(tile.y)

        nx = len(set(x))
        ny = len(set(y))

        return (tileset, nx, ny)

    def get_tile_urls(self) -> Sequence[str]:
        """Build s3 urls from tileset."""
        return [SERVICE_S3_URL.format(z=t.z, x=t.x, y=t.y) for t in self.tileset]

    def to_string(self):
        """Generate VRT string."""
        urls = self.get_tile_urls()
        return buildvrt(urls, self.shape, self.offsets, self.transform, self.tms.crs)

    def to_file(self, fname: Union[str, PathLike]):
        """Write VRT to file."""
        rasterio.shutil.copy(self.to_string(), fname, driver="VRT")

    @contextmanager
    def open(self):
        """Yield rasterio dataset of DEM VRT."""
        with rasterio.Env(aws_unsigned=True):
            with rasterio.MemoryFile(ext=".vrt") as mem:
                rasterio.shutil.copy(self.to_string(), mem.name, driver="VRT")
                with mem.open() as dem:
                    yield dem

    @classmethod
    def from_dataset(
        cls,
        dataset: rasterio.DatasetReader,
        zoom: int = 8,
        pixel_size: Optional[float] = None,
    ):
        """Create DEMTiles using bounds defined by dataset.

        Bounds in non-geographic coordinates will be transformed automatically.

        Parameters
        ----------
        dataset : rasterio.DatasetReader
            A rasterio dataset opened in 'r' mode. Must have a geotransform
            and crs.
        zoom : int
            Zoom level to use.
        pixel_size : float, optional
            Desired pixel size. Used to compute a suitable zoom level from
            TileMatrixSet.zoom_for_res.
        """
        if dataset.transform.is_identity:
            raise ValueError("Dataset must have a geotransform")
        if not dataset.crs:
            raise ValueError("Dataset has no CRS")

        # ensure bounds in geographic (lon, lat) coordinates
        bounds = dataset.bounds
        bounds = rasterio.warp.transform_bounds(
            dataset.crs, rasterio.crs.CRS.from_epsg(4326), *bounds
        )

        return cls(bounds, zoom=zoom, pixel_size=pixel_size)
