# %%
"""
File Name: test_split_node.py
Created on: 2026/06/09
Author: Chen mingkai
github: chmtk@outlook.com
describe: 目前的分裂节点法，实现是通过法向量旋转到z轴正方向，判断复制节点在旋转后z轴的正负方向来分裂节点的。
        正方向为 0 < 顺时针角 < 180 度
        负方向为 0 < 逆时针角 < 180 度 
        这种设计方式适用于分裂节点区域变化幅度并不剧烈的情况(1/4圆弧)
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from InpExchange.ModuleObject import Part
if TYPE_CHECKING:
    pass

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
new_nodes = main_part.nodes +  copied_nodes
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
# def 从多个elements list中，找出包含相同单元节点最多的元素进行返回
from InpExchange.math.geometry import face_normal, angle_to_z_axis, point_plane_side
def find_max_len_common_nodes(ele, common_nodes_list):
    """
    找出包含相同单元节点最多的元素进行返回
    """
    max_len_accure_index = 0
    max_len_num = 0
    for index, common_nodes in enumerate(common_nodes_list):
        if set(ele) <= set(common_nodes):
            if len(common_nodes) == Two_dimension_element_nodes_num:
                max_len_accure_index = index
                return max_len_accure_index
            else:
                if max_len_num < len(common_nodes):
                    max_len_num = len(common_nodes)
                    max_len_accure_index = index
    return max_len_accure_index 
Two_dimension_element_nodes_num = 3


old_nset = main_part.nsets[nset_name] # fault节点

def split_nodes_method_by_one_node(
        main_part: Part, one_node:int,
        copy_element_data:np.ndarray, used_element_ids:np.ndarray   
        ):
    if old_nset.node_ids is None:
        raise ValueError("Nset has no node ids")
    
    # 计算该节点所有的单元
    element = main_part.elements[0]
    index_x, _ = np.where(element.node_ids == one_node)

    # 统计每个单元的节点信息
    common_nodes_list = []
    for id in index_x:
        ele = element.node_ids[id]

        # 判断该单元有几个节点在fault nset上
        common_nodes = set(ele) & set(old_nset.node_ids)
        common_nodes_list.append(list(common_nodes))

    # 获取单元对应的节点坐标
    nodes = main_part.nodes    
    if nodes is None:
        raise ValueError("Part has no nodes")
    if nodes.coordinates is None:
        raise ValueError("Nodes has no coordinates")

    # 遍历每个单元
    for i, id in enumerate(index_x):
        if used_element_ids[id]:
            continue
        
        ele = element.node_ids[id]
        if len(common_nodes_list[i]) < Two_dimension_element_nodes_num:
            # 找出nset中的最接近的单元
            index = find_max_len_common_nodes(common_nodes_list[i], common_nodes_list)
            nset_element = common_nodes_list[index]
        else:
            nset_element = common_nodes_list[i] 
        
        # 利用找出的单元，计算该单元的法向量正方向 
        element_coords = nodes.coordinates[np.array(ele) - 1]
        nset_element_coords = nodes.coordinates[np.array(nset_element) - 1]
        element_coords_centorid = np.mean(element_coords, axis=0)   
        nset_element_coords_centorid = np.mean(nset_element_coords, axis=0)
        
        # 计算nset element法向量
        n1, n2 = face_normal(*nset_element_coords)

        for temp_i in range(len(n1)):
            if np.isclose(n1[temp_i], 0, atol=1e-12):
                n1[temp_i] = 0
            if np.isclose(n2[temp_i], 0, atol=1e-12):    
                n2[temp_i] = 0  

        angle1 = angle_to_z_axis(n1) 
        angle2 = angle_to_z_axis(n2)
        if angle1[1] == "CW" and angle2[1] == "CCW": # n1 逆时针
            positive_direction = n2
        elif angle1[1] == "CCW" and angle2[1] == "CW": # n1 顺时针
            positive_direction = n1
        else:
            raise ValueError("无法判断法向量的旋转方向")

        mark = point_plane_side(
            point = element_coords_centorid,
            plane_point = nset_element_coords_centorid,
            normal = positive_direction
        )
        if mark == 1: # 单元中心在法向量正方向 
            # 不需要更改节点序号
            used_element_ids[id] = True # 标记为已使用  
            continue
        
        # 负法线方向的单元，需要分配给复制的节点
        current_nset_element = common_nodes_list[i]
        needed_nodes = set(current_nset_element)
        for node in needed_nodes:
            # 找出该节点在new_nset中的对应的位置
            new_nset_index = np.argwhere(old_nset.node_ids == node).ravel()[0]

            # 找出该单元中包含的节点在element中的索引, 并将这些节点替换为复制节点   
            try:
                arg = np.argwhere(ele == node).ravel()[0]
            except:
                pass
            if new_nset.node_ids is None:
                raise ValueError("new_nset_index is None")
            copy_element_data[id, arg] = new_nset.node_ids[new_nset_index]
            used_element_ids[id] = True

if old_nset.node_ids is None:
    raise ValueError("Nset has no node ids")

# 从一个需要分裂的节点出发，找出包含该节点的单元
element = main_part.elements[0]
copy_element_data = deepcopy(element.node_ids)       
used_element_ids = np.zeros(element.data.shape[0], dtype=bool)

one_node = old_nset.node_ids[0]

for one_node in old_nset.node_ids:
    split_nodes_method_by_one_node(
        main_part, one_node,
        copy_element_data, used_element_ids 
    ) 

output_abaqus_model.parts[0].elements[0].data[:, 1:] = copy_element_data
a = output_abaqus_model.parts[0].elements[0].data[used_element_ids]

output_abaqus_model.write_inp("output_split_node.inp")