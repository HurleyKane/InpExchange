from InpExchange.Applications.GmshToAbaqus import GmshToAbaqus

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
output_abaqus_model = gmsh_model.app("output_mesh.inp")

part = output_abaqus_model.parts[0]
if part.nodes is None:
    raise ValueError("Part has no nodes")
node_ids = part.nodes.ids

if node_ids is None:
    raise ValueError("Part has no nodes")

all_node = set(node_ids)
element_node = set(list(part.elements[0].node_ids.ravel()))

print(len(all_node))
print(len(element_node))
print(all_node - element_node)
