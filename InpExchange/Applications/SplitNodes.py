# %%
"""
File Name: test_split_node.py
Created on: 2026/06/09
Author: Chen mingkai
github: chmtk@outlook.com
describe: 目前的分裂节点法，实现是通过法向量旋转到z轴正方向，判断复制节点在旋转后z轴的正负方向来分裂节点的。
        正方向为: 上盘，或者垂直断层的话，指向y轴、x轴正方向的为正方向
        这种设计方式适用于分裂节点区域变化幅度并不剧烈的情况(1/4圆弧)
        下盘Nset用（BOT结尾）
        注意： 如果是完全垂直的断层下方，出现左右变倾角的情况，这种方式不能判断节点在断层的哪一侧需要优化代码逻辑

cites: 
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

import numpy as np
from copy import deepcopy

from InpExchange.InpReader import InpModel
from InpExchange.frame.ModuleObject import Part, Nset
from InpExchange.math.geometry import face_normal, angle_to_z_axis, point_plane_side

def find_max_len_common_nodes(ele, common_nodes_list, Two_dimension_element_nodes_num):
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

def determine_positive_direction(element_coords_centorid, nset_element_coords_centorid, nset_element_coords:np.ndarray):
    """判断法向量的正方向
    1. 如果断层为直立断层，则指向y轴、x轴方向的为正方向

    Args:
        element_coords_centorid (_type_): 体单元中心
        nset_element_coords_centorid (_type_): 面单元中心
        nset_element_coords (_type_): 面三点坐标

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    nset_element_coords = nset_element_coords[0:3, :] # 取前三个节点坐标计算法向量
    n = face_normal(*nset_element_coords)
    # 保证法向量指向z轴正方向, 即上盘
    tol = 1e-5 # 0.00364°的容差, 直接置0
    n = np.array([0.0 if abs(ni) < tol else ni for ni in n])

    if n[-1] < - tol:
        n = -1 * n
    elif - tol < n[-1] < tol: # z=0，证明为直立断层
        # 保证法向量指向y轴正方向，直立断层y方向为正
        if n[1] < - tol:
            n = -1 * n
        elif - tol < n[1] < tol: # y=0, z=0, 证明为平行于y轴的垂直断层
            # 保证法向量指向x轴正方向, 即上盘
            if n[0] < - tol:
                n = -1 * n    
    # position_direction恒定指向
    mark = point_plane_side(
        point = element_coords_centorid,
        plane_point = nset_element_coords_centorid,
        normal = n
    )
    return mark

def split_nodes_method_by_one_node(
        main_part: Part, one_node_id:int,
        old_nset: Nset, new_nset: Nset,
        Two_dimension_element_nodes_num:int,
        copy_element_data:np.ndarray, used_element_ids:np.ndarray   
        ):
    if old_nset.node_ids is None:
        raise ValueError("Nset has no node ids")

    # 计算该节点所有的单元
    element = main_part.elements[0]
    index_x, _ = np.where(element.node_ids == one_node_id)

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
            index = find_max_len_common_nodes(common_nodes_list[i], common_nodes_list, Two_dimension_element_nodes_num)
            nset_element = common_nodes_list[index]
        else:
            nset_element = common_nodes_list[i] 

        # 利用找出的单元，计算该单元的法向量正方向 
        element_coords = nodes.coordinates[np.array(ele) - 1]
        nset_element_coords = nodes.coordinates[np.array(nset_element) - 1]
        element_coords_centorid = np.mean(element_coords, axis=0)   
        nset_element_coords_centorid = np.mean(nset_element_coords, axis=0)

        # 计算nset element法向量
        mark = determine_positive_direction(
            element_coords_centorid, nset_element_coords_centorid, nset_element_coords
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

class SplitNodesMethod(InpModel):
    """
    分裂节点法
    """
    def app(
            self, 
            nset_name:str, 
            sur_ele_nodes_num:int,
            output_file:str="output_split_node.inp"
    ):
        """
        Args:
            sur_ele_nodes_num: 2维单元的节点数量，例如4节点面单元为4，3节点面单元为3
        """
        abaqus_model = self
        new_nset_name = "{}_BOT".format(nset_name) 
        output_abaqus_model = deepcopy(abaqus_model)
        main_part = abaqus_model.parts[0]   

        # 复制节点与创建虚拟节点
        dummy_nset_name = "{}_DUMMY".format(nset_name)
        output_part = main_part.copy_nodes_and_nset_frome_nset(nset_name, new_nset_name)
        output_part = output_part.copy_nodes_and_nset_frome_nset(new_nset_name, dummy_nset_name)
        output_abaqus_model.parts[0] = output_part

        new_nset = output_part.nsets[new_nset_name]

        # -------------------------------------------------------
        # 2. 根据分裂的节点，修改单元.
        # * 修改的单元需要看看在Elset中是否存在, 如果存在也需要进行修改
        # -------------------------------------------------------
        # def 从多个elements list中，找出包含相同单元节点最多的元素进行返回
        Two_dimension_element_nodes_num = sur_ele_nodes_num
        old_nset = main_part.nsets[nset_name] # fault节点


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
                old_nset, new_nset,
                Two_dimension_element_nodes_num,
                copy_element_data, used_element_ids 
            ) 

        output_abaqus_model.parts[0].elements[0].data[:, 1:] = copy_element_data
        output_abaqus_model.write_inp(output_file)
        return output_abaqus_model

        # -------------------------------------------------------
        # 3. 创建虚拟节点和构建关联
        # -------------------------------------------------------

if __name__ == "__main__":
    import os
    print(os.getcwd())
    file = os.path.abspath(os.path.join(os.getcwd(), "../tests/output_mesh.inp"))
    print(os.path.exists(file))
    print(file)
    split_method = SplitNodesMethod.from_file(file)
    output_abaqus_model = split_method.app(nset_name="fault_surface_1", sur_ele_nodes_num=3)