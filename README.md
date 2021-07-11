# MEMDEM

Make use of open global elevation data from [Terrain Tiles](https://registry.opendata.aws/terrain-tiles) to create digital elevation models (DEM) on the fly.

The memdem project credits the [data source providers](ATTRIBUTION.md). Any use of memdem for redistribution, resale, presentation or publication of the data available from the Terrain Tiles dataset is required to make a similar attribution. See [here](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) for more information.

# Installation

memdem depends on 

- rasterio[s3] 
- morecantile

## Linux / OSX

```
pip install memdem
```

## Windows
**note**: Rasterio does not provide official windows wheels, ensure [GDAL](https://github.com/osgeo/gdal) is installed in order to install rasterio dependency.

### Unofficial wheels

[Unofficial rasterio wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/) (includes GDAL).

### Conda

```
conda create -yn memdem python=3.9
conda activate memdem
conda install -c conda-forge gdal
```

Once GDAL is installed, the environment variable `GDAL_VERSION` may need to be set in order to install rasterio dependency.

``` 
pip install memdem
```

# Quickstart

```python
import rasterio
from rasterio.crs. import CRS

import memdem

# define a bounding box
bounds = (-123.61735447008346, 48.91185687803928, -122.74734074899379, 49.52797572603976)

# create an instance of DEMTiles
demtiles = memdem.DEMTiles(
    bounds,
    zoom=10
)

# behold, a DEM created on the fly
with demtiles.open() as dem:
    lon, lat = (-123.17911189115098, 49.26435101976154)
    point_xy = rasterio.warp.transform(CRS.from_epsg(4326), dem.crs, [lon], [lat])
    print(next(dem.sample(zip(*point_xy))))  # 20


# save DEM to file for later use
demtiles.to_file("path/to/dem.vrt")
```

# Notes

## Coordinate Reference System

Terrain Tiles are referenced to the EPSG:3857 aka Web Mercator projection. However the vertical 
datum (what reference is used for elevation values e.g. WGS84 ellipsoid) [may vary depending on the source data](https://github.com/tilezen/joerd/issues/130). For accurate elevation results, it may be required to use source data with a well-defined vertical datum. For example, SRTM data has vertical datum EGM96. 

## AWS credentials

The Terrain Tiles dataset is avaiable freely and does not require aws credentials to access. Rasterio uses signed requests by default and may result in an error if it cannot locate your aws credentials. By default, memdem wraps the the `DEMTiles.open` context in a `rasterio.Env(aws_unsigned=True)` context. For operations requiring dataset reads outside of the `DEMTiles.open` context (e.g. when opening a previously saved VRT) ensure you do so within a `rasterio.Env(aws_unsigned=True)` block.
