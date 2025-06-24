# Geosquare Plugin for QGIS

Geosquare Plugin for QGIS designed to seamlessly export vector and raster layers into Geosquare. This plugin simplifies the process of splitting geospatial data to GeoSquare for advanced analytics, visualization, and sharing.

QGIS plugins page: https://plugins.qgis.org/plugins/geosquare_grid_qgis/

## Open GeoSquare
This algorithm converts tabular data (CSV or Parquet) containing Geosquare GIDs into a spatial layer with polygon geometries.

![opengeosquare](https://raw.githubusercontent.com/geosquareai/geosquare_grid_qgis/refs/heads/main/docs/img/open_geosquare.png)

## Polyfill
Fills gaps in a Geosquare grid by generating a uniform grid of squares over a polygon.

![polyfill](https://raw.githubusercontent.com/geosquareai/geosquare_grid_qgis/refs/heads/main/docs/img/polyfill.png)

## Raster to Geosquare
This algorithm converts raster data into a geosquare vector grid.

![rastertogeosquare](https://raw.githubusercontent.com/geosquareai/geosquare_grid_qgis/refs/heads/main/docs/img/raster_to_geosquare.png)

## Vector to Geosquare
This algorithm converts vector polygons to geosquare grid cells.

![vectortogeosquare](https://raw.githubusercontent.com/geosquareai/geosquare_grid_qgis/refs/heads/main/docs/img/vector_to_geosquare.png)