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

cites: 
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

from InpExchange.Applications.SplitNodes import SplitNodesMethod

split_method = SplitNodesMethod.from_file("output_mesh.inp")
output_abaqus_model = split_method.app(nset_name="fault_surface_1", sur_ele_nodes_num=3)

print(f"分裂节点完成，输出模型： {output_abaqus_model}")