# -*- coding: utf-8 -*-

"""
/***************************************************************************
 GeosquareGrid
                                 A QGIS plugin
 Geosquare Grid
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2025-04-17
        copyright            : (C) 2025 by PT Geo Innovasi Nussantara
        email                : admin@geosquare.ai
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'PT Geo Innovasi Nussantara'
__date__ = '2025-04-17'
__copyright__ = '(C) 2025 by PT Geo Innovasi Nussantara'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

grid_size = {
    '50 m': 50,
    '100 m': 100,
    '500 m': 500,
    '1 km': 1000,
    '5 km': 5000,
    '10 km': 10000,
}

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum)
from .geosquare_grid import GeosquareGrid
from qgis.core import QgsField, QgsFields, QgsCoordinateReferenceSystem, QgsWkbTypes, QgsCoordinateTransform
from PyQt5.QtCore import QVariant
from qgis import processing
from qgis.core import QgsGeometry, QgsFeature, QgsVectorLayer


class PolyfillAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    geosquare_grid = GeosquareGrid()
    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    FULLCOVER = 'FULLCOVER'
    GRIDSIZE = 'GRIDSIZE'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr('Input layer'),
            [QgsProcessing.TypeVectorPolygon]
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

        # We add a boolean parameter to determine if we want to only
        # include features that are inside the polygon
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FULLCOVER,
                self.tr('Full cover area'),
                defaultValue=True,
                optional=True
            )
        )

        # We add a grid size parameter
        # option select from 50 m, 100 m, 500 m, 1 km, 5 km, 10 km
        self.addParameter(
            QgsProcessingParameterEnum(
                self.GRIDSIZE,
                self.tr('Grid size'),
                options=list(grid_size.keys()),
                defaultValue='50 m',
                allowMultiple=False,
                optional=False
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        fields = QgsFields()
        fields.append(QgsField('gid', QVariant.String))
        # Create a CRS using EPSG:4326 (WGS84)
        crs = QgsCoordinateReferenceSystem('EPSG:4326')
        
        source = self.parameterAsSource(parameters, self.INPUT, context)
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
            context, fields, QgsWkbTypes.Polygon, crs)
        
        # Check if the input layer is empty
        if source.featureCount() == 0:
            feedback.pushInfo(self.tr('Input layer is empty.'))
            return {self.OUTPUT: dest_id}
        
        # Check if the input layer has crs
        if source.sourceCrs() is None:
            feedback.pushInfo(self.tr('Input layer has no CRS.'))
            return {self.OUTPUT: dest_id}

        geometries = [feature.geometry() for feature in source.getFeatures()]
        geometry = QgsGeometry.unaryUnion(geometries).simplify(0.0004)

        # convert to WGS84 if not already
        if source.sourceCrs() != crs:
            feedback.pushInfo(self.tr('Input layer is not in WGS84. Converting to WGS84.'))
            transform = QgsCoordinateTransform(source.sourceCrs(), crs, context.project())
            geometry.transform(transform)

        gid10km = self.geosquare_grid.polyfill(
            geometry,
            10000,
            feedback=feedback,
        )
        count_10km = len(gid10km)
        total = 100 / count_10km if count_10km else 0
        current = 0
        for g10km in gid10km:
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break
            self.geosquare_grid.polyfill(
                self.geosquare_grid.gid_to_geometry(g10km).intersection(geometry),
                grid_size[list(grid_size.keys())[self.parameterAsEnum(parameters, self.GRIDSIZE, context)]],
                feedback=feedback,
                start=g10km,
                sink=sink,
                fullcover=self.parameterAsBool(parameters, self.FULLCOVER, context),
            )
            # Update the progress bar
            current += total
            feedback.setProgress(int(current))
        feedback.setProgress(100)

        return {self.OUTPUT: dest_id}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Geosquare grid - Polyfill'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'vector'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def shortHelpString(self):
        return self.tr("""Fills gaps in a Geosquare grid by generating a uniform grid of squares over a polygon.
                            
                            This algorithm creates a grid of squares (cells) that either completely covers the input polygon
                            or only fills the interior of the polygon. The user can specify the grid size from predefined
                            options (50m, 100m, 500m, 1km, 5km, or 10km), determining the resolution of the resulting grid.
                            
                            The algorithm offers two coverage modes:
                            - Full coverage: Creates grid cells that intersect any part of the input polygon
                            - Interior only: Creates grid cells that fall completely within the input polygon
                            
                            This is particularly useful for:
                            - Creating uniform sampling grids for spatial analysis
                            - Generating reference grids for data collection
                            - Filling holes or gaps in existing Geosquare grid datasets
                            - Creating standardized grid systems for reporting or visualization""")

    def icon(self):
        """
        Returns the icon for the algorithm. This should be a valid path to an
        icon file, or None if no icon is available.
        """
        return ':/plugins/geosquare_grid/icon.png'

    def createInstance(self):
        return PolyfillAlgorithm()
