import numpy as np
from copy import deepcopy

from InpExchange.InpReader import InpModel  
abaqus_model = InpModel.from_file("output_mesh.inp") 
output_abaqus_model = deepcopy(abaqus_model)

main_part = abaqus_model.parts[0]   
main_part.nsets.data

# -------------------------------------------------------
# 复制节点
# -------------------------------------------------------
nset_name = "fault_surface_1"
copied_nodes = main_part.copy_nodes_from_nset(nset_name)
if main_part.nodes is None:
    raise ValueError("Part has no nodes")
new_nodes =main_part.nodes +  copied_nodes
output_abaqus_model.parts[0].nodes = new_nodes

# -------------------------------------------------------
# 2. 创建新的节点集
# -------------------------------------------------------
from InpExchange.BaseObject import Nodes, Nset

new_nset_name = "{}_copy".format(nset_name)
new_nset = Nset(nset=new_nset_name, type="independent", node_ids=copied_nodes.ids)
output_abaqus_model.parts[0].nsets.add(new_nset)

# -------------------------------------------------------
# 3. 根据分裂的节点，修改元素
# -------------------------------------------------------
new_nset # 复制的fault节点
old_nset = main_part.nsets[nset_name] # fault节点

if old_nset.node_ids is None:
    raise ValueError("Nset has no node ids")
one_node = old_nset.node_ids[0]

# 从单元中找出包好fault节点的单元下标
element = main_part.elements[0]
index_x, index_y = np.where(element.node_ids == one_node)
element.node_ids[index_x]

# 需要给出该单元是否访问的标记 

# 单元中如果只包含一个节点，则这个节点在断层面上有且只有一个
# 或者两个单元，给出这个单元的法向量，然后按照x，y,z 正轴
# 方向作为正方向，复制的节点自然分隔到负方向上去。
# 这里需要判断这个单元的重心在节点所在单元的重心方向的哪一侧（复制节点侧
# 还是源节点侧）


# 单元中如果包含两个节点 貌似和一个节点的情况差不多

# 单元中如果包含三个节点，fault面格网单元节点数一样多的情况。

# 总的逻辑，判断单元中的面上的节点形成的单元是否唯一。