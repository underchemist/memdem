"""Module for VRT creation."""
from typing import Any, Iterable, Sequence, Tuple
from xml.etree import ElementTree as ET

import morecantile
import rasterio
from affine import Affine

from memdem.constants import ELEVATION_TILE_SIZE, ELEVATION_BLOCK_SIZE


def buildvrt(
    urls: Sequence[str],
    shape: Tuple[int, int],
    offsets: Sequence[Tuple[int, int, int, int]],
    transform: Affine,
    crs: rasterio.crs.CRS = rasterio.crs.CRS.from_epsg(3857),
    dtype: str = "int16",
    nodata: Any = None,
) -> str:
    """
    Create a VRT document of mosaic'd Elevation Tiles for a given zoom level,
    representing a single DEM over the area defined.

    Parameters
    ----------
    urls : Sequence of str
        Sequence of s3 urls pointing to valid Elevation Tiles, which collectively
        represent a DEM.
    shape : Two-tuple of int
        The pixel height and width of DEM.
    offsets : Sequence of Four-tuple
        Sequence of tuples of the form (xoff, yoff, xsize, ysize) mapping the individual
        tile coordinates to the DEM image coordinate space.
    transform : Affine
        The geotransform for the DEM.
    crs : rasterio.crs.CRS
        The crs of the DEM, inheriting from the crs of the TileMatrixSet.
    dtype : str, optional
        Valid string identifier of a numpy datatype, determines the DEM dtype.
        Defaults to "int16".
    nodata : int or float, optional
        The nodata value to set for the DEM. Defaults to -32768

    Returns
    -------
    str:
        An XML formatted string of a valid VRT dataset.
    """
    if nodata is None:
        nodata = min(rasterio.dtypes.dtype_ranges[dtype])
    height, width = shape
    parsed_paths = [rasterio.parse_path(ds) for ds in urls]
    vsi_paths = [p.as_vsi() for p in parsed_paths]

    # root element
    root = ET.Element("VRTDataset")
    root.set("rasterXSize", str(width))
    root.set("rasterYSize", str(height))

    # crs/SRS
    wkt = crs.to_wkt()
    axis_mapping = "1,2"
    if rasterio.crs.epsg_treats_as_latlong(
        crs
    ) or rasterio.crs.epsg_treats_as_northingeasting(crs):
        axis_mapping = "2,1"
    srs = ET.SubElement(root, "SRS")
    srs.set("dataAxisToSRSAxisMapping", axis_mapping)
    srs.text = wkt

    # geotransform
    transform_str = ", ".join(
        list(map(lambda x: "{:.16e}".format(x), transform.to_gdal()))
    )
    geotransform = ET.SubElement(root, "GeoTransform")
    geotransform.text = transform_str

    # bands
    vrtrasterband = ET.SubElement(root, "VRTRasterBand")
    vrtrasterband.set("dataType", rasterio.dtypes._gdal_typename(dtype))
    vrtrasterband.set("band", "1")
    vrtnodata = ET.SubElement(vrtrasterband, "NoDataValue")
    vrtnodata.text = str(nodata)
    vrtcolorinterp = ET.SubElement(vrtrasterband, "ColorInterp")
    vrtcolorinterp.text = "Gray"

    for offset, uri in zip(offsets, vsi_paths):
        source = ET.SubElement(vrtrasterband, "ComplexSource")
        sourcefilename = ET.SubElement(source, "SourceFilename")
        sourcefilename.set("relativeToVRT", "0")
        sourcefilename.text = uri
        sourceband = ET.SubElement(source, "SourceBand")
        sourceband.text = "1"
        sourceproperties = ET.SubElement(source, "SourceProperties")
        sourceproperties.set("RasterXSize", str(ELEVATION_TILE_SIZE))
        sourceproperties.set("RasterYSize", str(ELEVATION_TILE_SIZE))
        sourceproperties.set("DataType", "Int16")
        sourceproperties.set("BlockXSize", str(ELEVATION_BLOCK_SIZE))
        sourceproperties.set("BlockYSize", str(ELEVATION_BLOCK_SIZE))
        srcrect = ET.SubElement(source, "SrcRect")
        srcrect.set("xOff", "0")
        srcrect.set("yoff", "0")
        srcrect.set("xSize", str(ELEVATION_TILE_SIZE))
        srcrect.set("ySize", str(ELEVATION_TILE_SIZE))
        xoff, yoff, xsize, ysize = offset
        dstrect = ET.SubElement(source, "DstRect")
        dstrect.set("xOff", str(xoff))
        dstrect.set("yOff", str(yoff))
        dstrect.set("xSize", str(xsize))
        dstrect.set("ySize", str(ysize))
        srcnodata = ET.SubElement(source, "NODATA")
        srcnodata.text = str(nodata)

    return ET.tostring(root, "utf-8").decode("utf-8")
