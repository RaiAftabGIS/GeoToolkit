import geopandas as gpd
class GeoToolKit:
    def __init__(self,filepath=None):
        self.filepath=filepath

    def load(self):
        gdf=gpd.read_file(self.filepath)
        return gdf
tool=GeoToolKit(tool = GeoToolKit(r"D:\Research_Work\Datasets\PAK_adm\LAHORE_Project.shp"))
data=tool.load()
print(data)
        

