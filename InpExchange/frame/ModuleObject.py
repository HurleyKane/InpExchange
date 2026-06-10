# %%
"""
File Name: AbaqusObject.py
Created on: 2026/06/08
Author: Chen mingkai
github: chmtk@outlook.com
describe: 
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

import numpy as np
from copy import deepcopy
from dataclasses import dataclass, field

from InpExchange.frame.BaseObject import (
    Element, Nset, Elset, Section, Instance, Surface, Equation,
    Elements, Nsets, Elsets, Sections, Nodes, Instances, Surfaces, Equations
)


def fmt_float(x: float) -> str:
    # Abaqus inp 对浮点格式不敏感；用通用格式减少无意义的小数位。
    try:
        return f"{float(x):.15g}"
    except Exception:
        return str(x)

def write_int_list(f, values: np.ndarray | list[int], *, per_line: int = 16, indent: str = "") -> None:
    """
    将一个数组或列表写入文件，每行最多 per_line 个元素，每行开头添加 indent。
    """
    arr = values if isinstance(values, list) else values.tolist()
    if not arr:
        f.write(f"{indent}\n")
        return
    for i in range(0, len(arr), per_line):
        chunk = arr[i:i + per_line]
        f.write(indent + ", ".join(str(int(v)) for v in chunk) + "\n")

# ==========================================================
# Part
# ==========================================================
@dataclass
class Part:
    name: str
    nodes: Nodes | None = None
    elements: Elements = field(default_factory=Elements)
    nsets: Nsets = field(default_factory=Nsets)
    elsets: Elsets = field(default_factory=Elsets)
    sections: Sections = field(default_factory=Sections)

    def __repr__(self):
        n_nodes = 0 if self.nodes is None else len(self.nodes)
        return (
            f"Part(name='{self.name}', "
            f"n_nodes={n_nodes}, "
            f"n_element_blocks={len(self.elements)})"
            f""
        )

    def get_max_nset_node_id(self):
        # def 找出Nset或者中最大的节点编号
        if len(self.nsets) > 0:
            max_node_id = max([max(nset.ids) for nset in self.nsets])
        else:
            max_node_id = 0
        return max_node_id

    def find_element_position(self, element_id: int): 
        """ 
        找出element_id对应的element在part.elements中的位置。
        """
        for index, element in enumerate(self.elements):
            try:
                element[element_id]
                return index
            except IndexError:
                pass
        raise ValueError("element_id not found")    

    def to_inp_str(self) -> str:
        """输出Part的inp格式字符串"""
        buf = []
        buf.append(f"*Part, name={self.name}")

        # Nodes
        if self.nodes is not None and len(self.nodes) > 0:
            buf.append(self.nodes.to_inp_str().rstrip())

        # Elements
        for elem in self.elements:
            buf.append(elem.to_inp_str().rstrip())

        # Nsets (Part-level only)
        for nset in self.nsets:
            buf.append(nset.to_inp_str().rstrip())

        # Elsets (Part-level only)
        for elset in self.elsets:
            buf.append(elset.to_inp_str().rstrip())

        # Sections
        for sec in self.sections:
            buf.append(sec.to_inp_str().rstrip())

        buf.append("*End Part")
        return "\n".join(buf) + "\n"
    def merge_elsets(self):
        from copy import deepcopy 

        part = self
        new_part = deepcopy(part)
        elset_names = [elset.elset for elset in part.elsets] 
        used_array = np.zeros(len(elset_names), dtype=bool)  

        new_elsets = []
        # 第一次迭代找出重复的elset并合并
        for index, elset_name in enumerate(elset_names):
            if used_array[index]: # 如果已经使用过则跳过
                continue
            for index2 in range(index + 1, len(elset_names)):
                if elset_name == elset_names[index2]:
                    # 现在需要新定义一个elset来存储合并后的单元组
                    temp_elset = Elset(elset=elset_name, type="independent")
                    # temp_elset.element_ids
                    temp_element = set(list(part.elsets[index].element_ids) + list(part.elsets[index2].element_ids)) # type: ignore     
                    temp_elset.element_ids = np.array(list(temp_element), dtype=int)
                    new_elsets.append(temp_elset)
                    used_array[index2] = True # 标记为已使用
                    used_array[index] = True # 标记为已使用
        # 第二次迭代找出不重复的elset并添加到新的elset列表中
        for index, elset_name in enumerate(elset_names):    
            if not used_array[index]: # 如果没有使用过则说明是独立的elset
                new_elsets.append(part.elsets[index]) # type: ignore
        if len(new_elsets) == 0:
            raise ValueError("没有找到elset")
        new_elsets = Elsets(data=new_elsets)
        new_part.elsets = new_elsets
        return new_part

    def extract_nodes_from_nset(self, nset_name:str):
        """提取nset中的节点"""
        main_part = self
        nset = main_part.nsets[nset_name]
        nset.node_ids
    
        nodes = main_part.nodes
        if nset.node_ids is None or nodes is None:
            raise ValueError("Part has no nodes")
        needed_copy_nodes = nodes.data[np.int_(nset.node_ids - 1)]
        if nodes.ids is None:
            raise ValueError("Part has no node ids")
        last_node_id = np.max(nodes.ids)
    
        copied_nodes = deepcopy(needed_copy_nodes)
        copied_nodes[:, 0] = np.arange(last_node_id + 1, last_node_id + 1 + len(copied_nodes))
    
        copied_nodes = Nodes(data=copied_nodes) 
    
        return copied_nodes

    def copy_nodes_and_nset_frome_nset(self, nset_name:str, new_nset_name:str):
        # -------------------------------------------------------
        # 复制节点
        # -------------------------------------------------------
        main_part = self
        output_part = deepcopy(main_part)

        # 创建复制节点
        copied_nodes = main_part.extract_nodes_from_nset(nset_name)
        if main_part.nodes is None:
            raise ValueError("Part has no nodes")
        new_nodes = main_part.nodes +  copied_nodes
        output_part.nodes = new_nodes

        # -------------------------------------------------------
        # 2. 创建新的节点集
        # -------------------------------------------------------
        # copy_nodes_set
        new_nset = Nset(nset=new_nset_name, type="independent", node_ids=copied_nodes.ids)
        output_part.nsets.add(new_nset)
        return output_part



@dataclass
class Assembly:
    name: str
    instances: Instances = field(default_factory=Instances)
    nsets: Nsets = field(default_factory=Nsets)
    elsets: Elsets = field(default_factory=Elsets)
    surfaces: Surfaces = field(default_factory=Surfaces)
    equations: Equations = field(default_factory=Equations)

    def add_instance(self, inst: Instance) -> None:
        self.instances.add(inst)

    def add_nset(self, nset: Nset) -> None:
        self.nsets.add(nset)

    def add_elset(self, elset: Elset) -> None:
        self.elsets.add(elset)

    def add_surface(self, surface: Surface) -> None:
        self.surfaces.add(surface)

    def add_equation(self, equation: Equation) -> None:
        self.equations.add(equation)

    def to_inp_str(self) -> str:
        """输出Assembly的inp格式字符串"""
        buf = []
        buf.append(f"*Assembly, name={self.name}")

        # Instances
        for inst in self.instances:
            buf.append(inst.to_inp_str().rstrip())

        # Nsets (Assembly-level)
        for nset in self.nsets:
            buf.append(nset.to_inp_str().rstrip())

        # Elsets (Assembly-level)
        for elset in self.elsets:
            buf.append(elset.to_inp_str().rstrip())

        # Surfaces
        for surface in self.surfaces:
            buf.append(surface.to_inp_str().rstrip())

        # Equations
        for equation in self.equations:
            buf.append(equation.to_inp_str().rstrip())

        buf.append("*End Assembly")
        return "\n".join(buf) + "\n"