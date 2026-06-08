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
        output_part.nsets = nsets 

        output_part.elsets = []
        output_abaqus_model.write_inp(output_file)


# 在 GmshToAbaqus.py 文件末尾添加

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        description="将 Gmsh 生成的 inp 文件转换为 Abaqus 兼容的 inp 文件"
    )
    parser.add_argument(
        "input_file", 
        type=str, 
        help="输入的 Gmsh .inp 文件路径"
    )
    parser.add_argument(
        "-o", "--output", 
        type=str, 
        default="output_mesh.inp", 
        help="输出的 Abaqus .inp 文件路径 (默认: output_mesh.inp)"
    )
    
    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 找不到输入文件 '{args.input_file}'")
        sys.exit(1)

    try:
        # 实例化类并读取文件
        # 假设 InpModel 或其父类有从文件初始化的方法，这里需要根据实际 InpReader 实现调整
        # 如果 InpModel 是通过 read_inp 静态方法或构造函数加载，请相应调整
        converter = GmshToAbaqus.from_file(args.input_file) # 假设存在此静态方法
        
        # 执行转换
        converter.app(output_file=args.output)
        
        print(f"成功: 转换完成，输出文件为 '{args.output}'")
        
    except Exception as e:
        print(f"错误: 转换过程中发生异常 - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()