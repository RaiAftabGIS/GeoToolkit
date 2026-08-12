from geotoolkit.core import SimpleGeoFile
from geotoolkit.utils import list_files
files=list_files("geotoolkit/examples")
print(files)

geo=SimpleGeoFile()

geo.load("geotoolkit/examples/sample.geojson")
# print("Total features:", geo.count_features())
# print("Feature types:", geo.features_type())
# print(geo.get_bounding_box())
# print("Filtered features:")
# print(geo.filter_by_property("city", "Lahore"))