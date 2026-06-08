from InpExchange.InpReader import Part
from InpExchange.GmshToAbaqus import GmshToAbaqus
import numpy as np

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
gmsh_model.app("output_mesh.inp")