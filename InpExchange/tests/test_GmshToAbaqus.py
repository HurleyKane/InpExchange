from InpExchange.Applications.GmshToAbaqus import GmshToAbaqus

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
gmsh_model.app("output_mesh.inp")

# gmsh_model.assemblies
from InpExchange.frame.ModuleObject import Assembly
from InpExchange.frame.BaseObject import Instance

part = gmsh_model.parts[0]

instance = Instance(name=part.name, part=part.name)
assembly = Assembly(name="Assembly-1")
assembly.instances.add(instance)