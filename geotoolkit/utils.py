 # Read/ extract geojson file from folder
import os
def list_files(folder):
    files=[]
    filepath=os.listdir(folder)
    for file in filepath:
      if file.endswith(".geojson"):
        directory=os.path.join(folder,file)
        files.append(directory)
    return files