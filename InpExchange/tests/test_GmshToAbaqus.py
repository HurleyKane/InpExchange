from InpExchange import GmshToAbaqus

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
gmsh_model.app("output_mesh.inp")