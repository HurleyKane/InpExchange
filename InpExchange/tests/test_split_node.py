# %%
"""
File Name: test_split_node.py
Created on: 2026/06/09
Author: Chen mingkai
github: chmtk@outlook.com
describe: 目前的分裂节点法，实现是通过法向量旋转到z轴正方向，判断复制节点在旋转后z轴的正负方向来分裂节点的。
        正方向为: 上盘，或者垂直断层的话，指向y轴、x轴正方向的为正方向
        这种设计方式适用于分裂节点区域变化幅度并不剧烈的情况(1/4圆弧)
        注意： 如果是完全垂直的断层下方，出现左右变倾角的情况，这种方式不能判断节点在断层的哪一侧需要优化代码逻辑
        定义： Ut - Ub - d = 0
cites: 
"""
from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING, Literal
if TYPE_CHECKING:
    pass

import numpy as np
from InpExchange.Applications.SplitNodes import SplitNodesMethod
from InpExchange.frame.BaseObject import Equation, Nset, Nsets, Instance

fault_plane_name = "fault_surface_1"
split_method = SplitNodesMethod.from_file("output_mesh.inp")
output_abaqus_model = split_method.app(nset_name=fault_plane_name, sur_ele_nodes_num=3)

part = output_abaqus_model.parts[0]
assembly = output_abaqus_model.assemblies[0]

TOP_nset = part.nsets[fault_plane_name]
BOT_nset = part.nsets[fault_plane_name + "_BOT"]
DUMMY_nset = part.nsets[fault_plane_name + "_DUMMY"]

# ====================================================================================
# equation的输入需要多个nset进行关联，现在每个nset中只能存放一个节点因此需要
# 创建nset (assembly.nsets)
# ====================================================================================
TOP_one_node_nsets = TOP_nset.create_one_node_nsets_from_nset(fault_plane_name + "_TOP")
BOT_one_node_nsets = BOT_nset.create_one_node_nsets_from_nset(fault_plane_name+"_BOT")
DUMMY_nsets = DUMMY_nset.create_one_node_nsets_from_nset(fault_plane_name + "_DUMMY")

def add_instance(nset:Nset, instance: Instance):
    """将nset中的节点添加到instance中

    Args:
        nset (Nset): _description_
        instance (Instance): _description_
    """
    if nset.node_ids is None:
        raise ValueError("nset.node_ids is None")
    new_nset = deepcopy(nset)
    new_nset.instance = instance.name
    return new_nset

def add_instance_to_nsets(nsets:Nsets, instance: Instance):
    """将nsets中的每个nset中的节点添加到instance中

    Args:
        nsets (Nsets): _description_
        instance (Instance): _description_
    """
    new_nsets = []
    for nset in nsets:
        new_nset = add_instance(nset, instance)
        new_nsets.append(new_nset)
    return Nsets(new_nsets)

TOP_one_node_nsets = add_instance_to_nsets(TOP_one_node_nsets, assembly.instances[0])
BOT_one_node_nsets = add_instance_to_nsets(BOT_one_node_nsets, assembly.instances[0])
DUMMY_nsets = add_instance_to_nsets(DUMMY_nsets, assembly.instances[0])

total_nsets = TOP_one_node_nsets + BOT_one_node_nsets + DUMMY_nsets
output_abaqus_model.assemblies[0].nsets += total_nsets


# ====================================================================================
# equation的输入需要多个nset进行关联，现在每个nset中只能存放一个节点因此需要
# 创建equation (assembly.equations)
# ====================================================================================
if len(TOP_one_node_nsets) != len(BOT_one_node_nsets) or len(TOP_one_node_nsets) != len(DUMMY_nsets):
    raise ValueError("TOP、BOT、DUMMY的one node nset数量不一致，无法构建方程")


total_quations = []
for i in range(len(TOP_one_node_nsets)):
    term = [TOP_one_node_nsets[i], BOT_one_node_nsets[i], DUMMY_nsets[i]]
    parameter = [1., -1., -1.] # Ut - Ub - slip = 0
    union_nsets = Nsets([TOP_one_node_nsets[i], BOT_one_node_nsets[i], DUMMY_nsets[i]])

    equation_U1 = union_nsets.create_equation_from_nsets("U1", parameter)
    equation_U2 = union_nsets.create_equation_from_nsets("U2", parameter)
    equation_U3 = union_nsets.create_equation_from_nsets("U3", parameter)

    total_quations.append(equation_U1)
    total_quations.append(equation_U2)
    total_quations.append(equation_U3)

output_abaqus_model.assemblies[0].equations +=  total_quations

output_abaqus_model.write_inp("output_split_node.inp")