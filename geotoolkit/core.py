import os
import json
import csv

from geotoolkit.exceptions import InvalidGeoDataError
from geotoolkit.exceptions import UnsupportedFormatError


class SimpleGeoFile:

    def __init__(self, filepath=None):
        self.filepath = filepath
        self.data = None

    # Load GeoJSON file
    def load(self, filepath):
        try:
            with open(filepath, "r") as file:
                self.data = json.load(file)

        except FileNotFoundError:
            raise FileNotFoundError("File not found: " + filepath)

        except json.JSONDecodeError:
            raise InvalidGeoDataError(
                "File data is not valid JSON/GeoJSON"
            )

    # Convert CSV file into GeoJSON format
    def from_csv(self, filepath, col_lat="lat", col_lon="lon"):
        features = []

        try:
            with open(filepath, "r") as csv_file:
                read_file = csv.DictReader(csv_file)

                if (
                    col_lat not in read_file.fieldnames
                    or col_lon not in read_file.fieldnames
                ):
                    raise UnsupportedFormatError(
                        "lat/lon columns are not found"
                    )

                for row in read_file:
                    properties = {}

                    for key, value in row.items():
                        if key != col_lat and key != col_lon:
                            properties[key] = value

                    feature = {
                        "type": "Feature",
                        "properties": properties,
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                float(row[col_lon]),
                                float(row[col_lat])
                            ]
                        }
                    }

                    features.append(feature)

        except FileNotFoundError:
            raise FileNotFoundError(
                "CSV file not found: " + filepath
            )

        self.data = {
            "type": "FeatureCollection",
            "features": features
        }

    # Convert GeoJSON to CSV
    def to_csv(self, filepath):
        try:
            with open(filepath, "w", newline="") as csv_file:

                first_feature = self.data["features"][0]
                properties = first_feature["properties"]

                fieldname = list(properties.keys())
                fieldname.append("lat")
                fieldname.append("lon")

                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=fieldname
                )

                writer.writeheader()

                for feature in self.data["features"]:

                    row = feature["properties"].copy()

                    lon, lat = feature["geometry"]["coordinates"]

                    row["lat"] = lat
                    row["lon"] = lon

                    writer.writerow(row)

        except FileNotFoundError:
            raise FileNotFoundError(
                "Could not create CSV file: " + filepath
            )

    # Count total features
    def count_features(self):
        total_features = len(self.data["features"])
        return total_features

    # Get geometry types
    def features_type(self):
        feature_types = set()

        for feature in self.data["features"]:
            geometry_type = feature["geometry"]["type"]
            feature_types.add(geometry_type)

        return feature_types

    # Get bounding box
    def get_bounding_box(self):

        first_feature = self.data["features"][0]
        geom_type = first_feature["geometry"]["type"]

        if geom_type == "Point":
            max_lon, max_lat = first_feature["geometry"]["coordinates"]

        elif geom_type == "LineString":
            max_lon, max_lat = (
                first_feature["geometry"]["coordinates"][0]
            )

        elif geom_type == "Polygon":
            max_lon, max_lat = (
                first_feature["geometry"]["coordinates"][0][0]
            )

        min_lon = max_lon
        min_lat = max_lat

        for feature in self.data["features"]:

            geom_type = feature["geometry"]["type"]

            if geom_type == "Point":

                coordinates = [
                    feature["geometry"]["coordinates"]
                ]

            elif geom_type == "LineString":

                coordinates = feature["geometry"]["coordinates"]

            elif geom_type == "Polygon":

                coordinates = []

                for ring in feature["geometry"]["coordinates"]:
                    for point in ring:
                        coordinates.append(point)

            else:
                continue

            for coord in coordinates:

                lon, lat = coord

                if lat > max_lat:
                    max_lat = lat

                if lon > max_lon:
                    max_lon = lon

                if lat < min_lat:
                    min_lat = lat

                if lon < min_lon:
                    min_lon = lon

        return (
            f"Maximum Latitude = {max_lat}\n"
            f"Minimum Latitude = {min_lat}\n"
            f"Maximum Longitude = {max_lon}\n"
            f"Minimum Longitude = {min_lon}"
        )

    # Filter features by property
    def filter_by_property(self, key, value):

        properties = []

        for feature in self.data["features"]:

            try:
                if feature["properties"][key] == value:
                    properties.append(feature)

            except KeyError:
                raise InvalidGeoDataError(
                    f"Property '{key}' doesn't exist on this feature"
                )

        return properties

    # Save GeoJSON file
    def save(self, outpath):

        try:
            with open(outpath, "w") as outfile:
                json.dump(self.data, outfile)

        except FileNotFoundError:
            raise FileNotFoundError(
                "Could not save file: " + outpath
            )

    # String representation
    def __str__(self):
        return (
            f"Features: {self.count_features()}, "
            f"Types: {self.features_type()}"
        )