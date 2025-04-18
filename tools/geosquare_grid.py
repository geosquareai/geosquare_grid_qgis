import functools
from typing import Tuple, List,Union
from qgis.core import QgsGeometry, QgsFeatureSink, QgsFeature, QgsProcessingFeedback


class GeosquareGrid:
    def __init__(self):
        # Initialize instance variables
        self.longitude = None
        self.latitude = None
        self.level = None
        self.gid = None
        self.address = None
        
        # Initialize constants
        self.CODE_ALPHABET = [
            ["2", "3", "4", "5", "6"],
            ["7", "8", "9", "C", "E"],
            ["F", "G", "H", "J", "L"],
            ["M", "N", "P", "Q", "R"],
            ["T", "V", "W", "X", "Y"],
        ]
        
        # Pre-compute derived constants for faster lookups
        self.CODE_ALPHABET_ = {
            5: sum(self.CODE_ALPHABET, []),
            2: sum([c[:2] for c in self.CODE_ALPHABET[:2]], []),
            "c2": ["2", "3"],
            "c12": ["V", "X", "N", "M", "F", "R", "P", "W", "H", "G", "Q", "L", "Y", "T", "J"],
        }
        
        self.CODE_ALPHABET_VALUE = {
            j: (idx_1, idx_2)
            for idx_1, i in enumerate(self.CODE_ALPHABET)
            for idx_2, j in enumerate(i)
        }
        
        self.CODE_ALPHABET_INDEX = {
            k: {val: idx for idx, val in enumerate(v)}
            for k, v in self.CODE_ALPHABET_.items()
        }
        
        self.d = [5, 2, 5, 2, 5, 2, 5, 2, 5, 2, 5, 2, 5, 2, 5]
        self.size_level = {
            10000000: 1, 5000000: 2, 1000000: 3, 500000: 4,
            100000: 5, 50000: 6, 10000: 7, 5000: 8,
            1000: 9, 500: 10, 100: 11, 50: 12,
            10: 13, 5: 14, 1: 15,
        }
        
        # Cache for expensive operations
        self._geometry_cache = {}
        self._lonlat_cache = {}
        self._bound_cache = {}

    # === Core coordinate/GID conversion methods ===
    
    @functools.lru_cache(maxsize=128)
    def lonlat_to_gid(self, longitude: float, latitude: float, level: int) -> str:
        """Convert longitude/latitude to GID with bounds checking and caching"""
        assert -180 <= longitude <= 180, "Longitude must be between -180 and 180"
        assert -90 <= latitude <= 90, "Latitude must be between -90 and 90"
        assert 1 <= level <= 15, "Level must be between 1 and 15"
        
        lat_ranged = (-216, 233.157642055036)
        lon_ranged = (-217, 232.157642055036)
        gid = ""
        
        for part in self.d[:level]:
            position_x = int((longitude - lon_ranged[0]) / (lon_ranged[1] - lon_ranged[0]) * part)
            position_y = int((latitude - lat_ranged[0]) / (lat_ranged[1] - lat_ranged[0]) * part)
            
            part_x = (lon_ranged[1] - lon_ranged[0]) / part
            part_y = (lat_ranged[1] - lat_ranged[0]) / part
            
            shift_x = part_x * position_x
            shift_y = part_y * position_y
            
            lon_ranged = (lon_ranged[0] + shift_x, lon_ranged[0] + shift_x + part_x)
            lat_ranged = (lat_ranged[0] + shift_y, lat_ranged[0] + shift_y + part_y)
            
            gid += self.CODE_ALPHABET[position_y][position_x]
            
        return gid

    @functools.lru_cache(maxsize=128)
    def gid_to_lonlat(self, gid: str) -> Tuple[float, float]:
        """Convert GID to longitude/latitude with caching"""
            
        lat_ranged = (-216, 233.157642055036)
        lon_ranged = (-217, 232.157642055036)
        
        for idx, char in enumerate(gid):
            part_x = (lon_ranged[1] - lon_ranged[0]) / self.d[idx]
            part_y = (lat_ranged[1] - lat_ranged[0]) / self.d[idx]
            
            shift_x = part_x * self.CODE_ALPHABET_VALUE[char][1]
            shift_y = part_y * self.CODE_ALPHABET_VALUE[char][0]
            
            lon_ranged = (lon_ranged[0] + shift_x, lon_ranged[0] + shift_x + part_x)
            lat_ranged = (lat_ranged[0] + shift_y, lat_ranged[0] + shift_y + part_y)
            
        result = (lon_ranged[0], lat_ranged[0])
        return result

    @functools.lru_cache(maxsize=128)
    def gid_to_bound(self, gid: str) -> Tuple[float, float, float, float]:
        """Convert GID to bounds (xmin, ymin, xmax, ymax) with caching"""
            
        lat_ranged = (-216, 233.157642055036)
        lon_ranged = (-217, 232.157642055036)
        
        for idx, char in enumerate(gid):
            part_x = (lon_ranged[1] - lon_ranged[0]) / self.d[idx]
            part_y = (lat_ranged[1] - lat_ranged[0]) / self.d[idx]
            
            shift_x = part_x * self.CODE_ALPHABET_VALUE[char][1]
            shift_y = part_y * self.CODE_ALPHABET_VALUE[char][0]
            
            lon_ranged = (lon_ranged[0] + shift_x, lon_ranged[0] + shift_x + part_x)
            lat_ranged = (lat_ranged[0] + shift_y, lat_ranged[0] + shift_y + part_y)
            
        result = (lon_ranged[0], lat_ranged[0], lon_ranged[1], lat_ranged[1])
        return result

    # === Public interface methods ===
    
    def from_lonlat(self, longitude: float, latitude: float, level: int) -> None:
        """Initialize grid from longitude/latitude coordinates"""
        assert -180 <= longitude <= 180, "Longitude must be between -180 and 180"
        assert -90 <= latitude <= 90, "Latitude must be between -90 and 90"
        assert 1 <= level <= 15, "Level must be between 1 and 15"
        
        self.longitude = longitude
        self.latitude = latitude
        self.level = level
        self.gid = self.lonlat_to_gid(self.longitude, self.latitude, self.level)

    def from_gid(self, gid: str) -> None:
        """Initialize grid from GID"""
        self.gid = gid
        self.level = len(gid)
        self.longitude, self.latitude = self.gid_to_lonlat(self.gid)

    def from_address(self, address: str) -> None:
        """Initialize grid from address"""
        self.address = address
        if not self.address_to_gid():
            raise ValueError("Address is not valid")

    def get_gid(self) -> str:
        """Get GID for current grid cell"""
        if self.gid is None:
            if None in (self.longitude, self.latitude, self.level):
                raise ValueError("Cannot get GID without longitude, latitude, and level")
            self.gid = self.lonlat_to_gid(self.longitude, self.latitude, self.level)
        return self.gid

    def get_lonlat(self) -> Tuple[float, float]:
        """Get longitude/latitude for current grid cell"""
        if self.longitude is None or self.latitude is None:
            if self.gid is None:
                raise ValueError("Cannot get lon/lat without GID")
            self.longitude, self.latitude = self.gid_to_lonlat(self.gid)
        return self.longitude, self.latitude

    def get_bound(self) -> Tuple[float, float, float, float]:
        """Get bounds for current grid cell"""
        return self.gid_to_bound(self.gid)

    def get_geometry(self) -> QgsGeometry:
        """Get geometry for current grid cell"""
        return self.gid_to_geometry(self.gid)

    def get_address(self) -> str:
        """Get address for current grid cell"""
        if self.level != 14:
            raise ValueError("Address is only available for level 14")
            
        if self.address is None:
            if self.gid is None:
                raise ValueError("Address is not available with no GID")
            self.gid_to_address()
            
        return self.address

    # === Geometry related methods ===
    
    @functools.lru_cache(maxsize=64)
    def gid_to_geometry(self, gid: str) -> QgsGeometry:
        """Convert GID to geometry with caching"""
        geom_wkt = self._gid_to_geometry_wkt(gid)
        result = QgsGeometry.fromWkt(geom_wkt)
        return result

    def _gid_to_geometry_wkt(self, gid: str) -> str:
        """Convert GID to WKT geometry string"""
        a = self.gid_to_bound(gid)
        return (
            f"Polygon (({a[0]} {a[1]},{a[0]} {a[3]},"
            f"{a[2]} {a[3]},{a[2]} {a[1]},{a[0]} {a[1]}))"
        )
    

    @staticmethod
    def _area_ratio(a: QgsGeometry, b: QgsGeometry) -> float:
        """Calculate area ratio with proper error handling"""
        try:
            intersect = a.intersection(b)
            if intersect.isEmpty():
                return 0
            return round(intersect.area() / a.area(), 20)
        except (ValueError, ZeroDivisionError):
            return 0


    def convert_to_gid_part(self, value: int, d_part: List[Union[int, str]]) -> List[str]:
        """Convert numeric value to GID parts"""
        gid_part = []
        _pow = len(d_part) - 1
        
        for i in d_part:
            if i in ["c2", "c12"]:
                div = value // (5**2) ** _pow
                value = value % (5**2) ** _pow
                gid_part.append(self.CODE_ALPHABET_[i][div])
            else:
                div = value // (i**2) ** _pow
                value = value % (i**2) ** _pow
                gid_part.append(self.CODE_ALPHABET_[i][div])
            _pow -= 1
            
        return gid_part

    # === Spatial operations ===
    
    def _to_children(self, key: str) -> Tuple[str, ...]:
        """Get all child GIDs for a given GID"""
        return tuple(key + i for i in self.CODE_ALPHABET_[self.d[len(key)]])

    def _to_parent(self, key: str) -> str:
        """Get parent GID for a given GID"""
        return key[:-1] if len(key) > 1 else key

    def _get_contained_keys(
        self,
        geometry: QgsGeometry,
        initial_key: str,
        resolution: List[int],
        feedback: QgsProcessingFeedback,
        fullcover: bool = True,
        sink: QgsFeatureSink = None
    ) -> List[str]:
        """Find all grid cells that overlap with geometry at specified resolution"""
           
        if initial_key != "2":
            geometry = geometry.intersection(self.gid_to_geometry(initial_key))
        contained_keys = []
        def func(key, approved):
            if approved:
                if resolution[0] <= len(key) <= resolution[1]:
                    if sink is not None:
                        geom = self.gid_to_geometry(key)
                        feature = QgsFeature()
                        feature.setGeometry(geom)
                        feature.setAttributes([key])
                        sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    else:
                        contained_keys.append(key)
                else:
                    for child_key in self._to_children(key):
                        if feedback.isCanceled():
                            break
                        func(child_key, True)
            else:
                area_ratio = self._area_ratio(
                    self.gid_to_geometry(key), geometry)
                if area_ratio == 0:
                    last_idx = self.CODE_ALPHABET_[self.d[0]].index(key[-1])
                    if (last_idx < 25) & (len(key) == 1):
                        func(
                            key[:-1] + self.CODE_ALPHABET_[self.d[0]
                                                           ][last_idx + 1][0],
                            False,
                        )
                    else:
                        return
                elif area_ratio == 1:
                    func(key, True)
                elif (len(key) == resolution[1]) & fullcover:
                    if sink is not None:
                        geom = self.gid_to_geometry(key)
                        feature = QgsFeature()
                        feature.setGeometry(geom)
                        feature.setAttributes([key])
                        sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    else:
                        contained_keys.append(key)
                elif (len(key) == resolution[1]) & (area_ratio > 0.5) & (~fullcover):
                    if sink is not None:
                        geom = self.gid_to_geometry(key)
                        feature = QgsFeature()
                        feature.setGeometry(geom)
                        feature.setAttributes([key])
                        sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    else:
                        contained_keys.append(key)
                elif len(key) == resolution[1]:
                    return
                else:
                    for child_key in self._to_children(key):
                        if feedback.isCanceled():
                            break
                        func(child_key, False)

        func(initial_key, False)
        return contained_keys

    def polyfill(
        self, 
        geometry: QgsGeometry, 
        size: Union[int, List[int]], 
        feedback: QgsProcessingFeedback,
        start: str = "2", 
        fullcover: bool = True,
        sink: QgsFeatureSink = None,
    ) -> List[str]:
        """Find all grid cells that overlap with geometry at specified size(s)"""
        # Handle size parameter - convert to resolution levels
        if isinstance(size, list):
            assert size[0] > size[1], "size must be in [min, max] format"
            assert size[0] in self.size_level, f"size must be in {list(self.size_level.keys())}"
            assert size[1] in self.size_level, f"size must be in {list(self.size_level.keys())}"
            resolution = [self.size_level[i] for i in size]
        else:
            assert size in self.size_level, f"size must be in {list(self.size_level.keys())}"
            resolution = [self.size_level[size], self.size_level[size]]
            
        return self._get_contained_keys(
            geometry,
            start,
            resolution,
            feedback,
            fullcover,
            sink
        )

    def __repr__(self) -> str:
        """String representation of the grid"""
        return f"PetainGrid(gid={self.gid}, address={self.address}, longitude={self.longitude}, latitude={self.latitude}, level={self.level})"