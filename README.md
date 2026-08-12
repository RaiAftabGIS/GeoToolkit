# GeoToolkit

A Python toolkit for working with geospatial data, built incrementally from core Python fundamentals toward modern GIS, remote sensing, and GeoAI.

This project also serves as a learning log: each stage of the codebase represents a new Python or GIS concept as I learn and implement it.

## What It Does

The current `SimpleGeoFile` class provides basic operations on GeoJSON and CSV point data using Python's standard library.

### Current Features

- Load GeoJSON files
- Save GeoJSON files
- Convert CSV point data to GeoJSON
- Convert GeoJSON Point data to CSV
- Count features
- List geometry types
- Calculate a bounding box
- Filter features by property
- List files by extension
- Handle invalid JSON/GeoJSON using custom exceptions
- Handle unsupported CSV formats

## Project Structure

```text
GeoToolkit/
├── .gitignore
├── README.md
└── geotoolkit/
    ├── __init__.py
    ├── core.py
    ├── exceptions.py
    ├── utils.py
    └── examples/
        ├── demo.py
        └── sample.geojson
```

## Usage

### Load a GeoJSON File

```python
from geotoolkit.core import SimpleGeoFile

geo = SimpleGeoFile()

geo.load("geotoolkit/examples/sample.geojson")

print(geo.count_features())
print(geo.features_type())
print(geo.get_bounding_box())
```

### Count Features

```python
print(geo.count_features())
```

This returns the total number of features in the GeoJSON file.

### Get Geometry Types

```python
print(geo.features_type())
```

This returns the geometry types present in the dataset.

### Get Bounding Box

```python
print(geo.get_bounding_box())
```

This returns the minimum and maximum latitude and longitude values of the dataset.

### Filter Features by Property

```python
schools = geo.filter_by_property("type", "school")

print(schools)
```

This returns features whose specified property matches the given value.

## CSV to GeoJSON

CSV files containing latitude and longitude columns can be converted to GeoJSON Point features.

```python
geo.from_csv(
    "data.csv",
    col_lat="lat",
    col_lon="lon"
)
```

The latitude and longitude values are converted into GeoJSON coordinates using the standard `[longitude, latitude]` order.

## GeoJSON to CSV

GeoJSON Point features can be exported to CSV.

```python
geo.to_csv("output.csv")
```

The resulting CSV contains latitude, longitude, and feature properties.

## File Utilities

Files with a specific extension can be found inside a folder using the `list_files()` utility.

```python
from geotoolkit.utils import list_files

files = list_files(
    "geotoolkit/examples",
    extension=".geojson"
)

print(files)
```

## Error Handling

GeoToolkit includes custom exceptions for invalid geospatial data and unsupported formats.

### Custom Exceptions

```python
class InvalidGeoDataError(Exception):
    pass


class UnsupportedFormatError(Exception):
    pass
```

The toolkit handles errors such as:

- Missing files
- Invalid JSON/GeoJSON
- Missing latitude/longitude columns
- Unsupported formats

## Example Workflow

A complete basic workflow looks like this:

```python
from geotoolkit.core import SimpleGeoFile

geo = SimpleGeoFile()

geo.load("geotoolkit/examples/sample.geojson")

print("Number of features:")
print(geo.count_features())

print("\nGeometry types:")
print(geo.features_type())

print("\nBounding box:")
print(geo.get_bounding_box())
```

## Tech Stack

### Current

- Python 3
- `json`
- `csv`
- `os`

The current implementation uses only Python's standard library.

### Future

The project will gradually introduce:

- GeoPandas
- Shapely
- Rasterio
- PostGIS
- PyTorch / TorchGeo
- Web mapping libraries
- GeoAI tools

## Roadmap

This project is being developed step by step.

- [x] Python functions
- [x] Classes
- [x] File handling
- [x] GeoJSON operations
- [x] CSV to GeoJSON conversion
- [x] GeoJSON to CSV conversion
- [x] File utilities
- [x] Custom exception handling
- [x] Git version control
- [x] GitHub project setup
- [ ] GeoPandas and Shapely
- [ ] Spatial operations
- [ ] CRS handling
- [ ] Rasterio and remote sensing
- [ ] PostGIS integration
- [ ] Web mapping
- [ ] GeoAI
- [ ] Deployment

## Learning Goals

The purpose of GeoToolkit is to understand GIS programming from the ground up.

The project will gradually progress from:

```text
Python Fundamentals
        ↓
Functions
        ↓
Classes
        ↓
File Handling
        ↓
GeoJSON / CSV
        ↓
Error Handling
        ↓
GeoPandas / Shapely
        ↓
Rasterio / Remote Sensing
        ↓
PostGIS
        ↓
Web GIS
        ↓
GeoAI
```

## Author

Built as a hands-on project to learn GIS programming and progressively develop skills toward modern GIS, remote sensing, and GeoAI.