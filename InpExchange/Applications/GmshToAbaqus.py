# %%
"""
File Name: GmshToAbaqus.py
Created on: 2026/06/05
Author: Chen mingkai
github: chmtk@outlook.com
describe: 该脚本实现功能：
1. 读取gmsh生成的inp文件，并将inp文件中的材料部分的分组信息转换为abaqus能识别的nset和elset信息
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

from copy import deepcopy
from InpExchange.InpReader import InpModel
from InpExchange.frame.ModuleObject import Assembly
from InpExchange.frame.BaseObject import Instance, Nsets, Elsets
        
class GmshToAbaqus(InpModel):
    def app(self, output_file:str="output_mesh.inp"):
        "将gmsh生成的inp文件转换为abaqus能识别的inp文件"
        gmsh_model = self
        output_abaqus_model = deepcopy(gmsh_model)
        part = gmsh_model.parts[0]
        # 合并同名的elsets
        part = part.merge_elsets()
        output_part = output_abaqus_model.parts[0]

        # ------------------------------------------
        # 统一单元类型
        # def 删除part中多余element组
        # output part加入element
        # ------------------------------------------
        max_shape = 0
        max_index = 0
        for index, element in enumerate(part.elements):
            if element.node_ids.shape[1] > max_shape:
                max_shape = element.node_ids.shape[1] 
                max_index = index
        output_part.elements = [part.elements[max_index]] # type: ignore

        # ------------------------------------------
        # output part加入nsets
        # ------------------------------------------
        nsets = []
        for elset in part.elsets:
            if elset.elset.startswith("material"): 
                material_name =  "material_" + elset.elset.split(":")[1]
                elset.elset = material_name 
            print(f"Processing elset: {elset.elset}")
            temp_nset = elset.transform_to_nset(part)
            nsets.append(temp_nset)
        nsets = Nsets(nsets)
        output_part.nsets = nsets 
        output_part.elsets = Elsets([])

        # ==========================================================
        #  新建assembly
        # ==========================================================
        part = output_abaqus_model.parts[0]
        assembly = Assembly(name="Assembly-1")
        instance = Instance(name=part.name, part=part.name)
        assembly.instances.add(instance)
        output_abaqus_model.assemblies.append(assembly)
        
        output_abaqus_model.write_inp(output_file)
        print(f"gmsh mesh转换为abaqus模型完成，输出模型： {output_abaqus_model}")
        return output_abaqus_model


if __name__ == "__main__":
    pass