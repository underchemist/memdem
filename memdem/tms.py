"""Module defining custom TileMatrixSet specific to Elevation Tiles dataset."""
import morecantile

from memdem.constants import ELEVATION_TILE_SIZE


WEBMERCATORQUAD = morecantile.tms.get("WebMercatorQuad")

ELEVATIONWMQ = morecantile.TileMatrixSet.custom(
    extent=[
        *WEBMERCATORQUAD.boundingBox.lowerCorner,
        *WEBMERCATORQUAD.boundingBox.upperCorner,
    ],
    extent_crs=WEBMERCATORQUAD.boundingBox.crs,
    crs=WEBMERCATORQUAD.crs,
    tile_height=ELEVATION_TILE_SIZE,
    tile_width=ELEVATION_TILE_SIZE,
    identifier="ElevationWebMercatorQuad",
    title="WebMercatorQuad custom for Elevation Tiles",
    maxzoom=17,  # Elevation Tiles dataset contains at best 3 m resolution, so no sense going much beyond that
)

default_tms = morecantile.tms.register(ELEVATIONWMQ)
