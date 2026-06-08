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

from InpExchange.BaseObject import (
    Element, Nset, Elset, Section, Instance,
    Elements, Nsets, Elsets, Sections, Nodes
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

    def _write_part(self, f) -> None:
        part = self
        f.write(f"*Part, name={part.name}\n")

        # Nodes
        if part.nodes is not None and len(part.nodes) > 0:
            f.write("*Node\n")
            if part.nodes.data is None:
                raise ValueError("Part has no nodes")
            for row in part.nodes.data:
                node_id = int(row[0])
                coords = row[1:]
                f.write(
                    str(node_id)
                    + ", "
                    + ", ".join(fmt_float(v) for v in coords)
                    + "\n"
                )

        # Elements
        for elem in part.elements:
            f.write(f"*Element, type={elem.type}\n")
            if elem.data is None or len(elem.data) == 0:
                continue
            for row in elem.data:
                f.write(", ".join(str(int(v)) for v in row.tolist()) + "\n")

        # Nsets (Part-level only)
        for nset in part.nsets:
            if nset.type == "generate":
                f.write(f"*Nset, nset={nset.nset}, generate\n")
                if nset.generate is None:
                    f.write("\n")
                else:
                    s, e, inc = nset.generate
                    f.write(f"{int(s)}, {int(e)}, {int(inc)}\n")
            else:
                f.write(f"*Nset, nset={nset.nset}\n")
                write_int_list(f, nset.ids)

        # Elsets (Part-level only)
        for elset in part.elsets:
            if elset.type == "generate":
                f.write(f"*Elset, elset={elset.elset}, generate\n")
                if elset.generate is None:
                    f.write("\n")
                else:
                    s, e, inc = elset.generate
                    f.write(f"{int(s)}, {int(e)}, {int(inc)}\n")
            else:
                f.write(f"*Elset, elset={elset.elset}\n")
                write_int_list(f, elset.ids)

        # Sections
        for sec in part.sections:
            if sec.keyword == "Solid Section":
                header = "*Solid Section"
            elif sec.keyword == "Shell Section":
                header = "*Shell Section"
            else:
                header = "*Section"

            args: list[str] = []
            if sec.elset:
                args.append(f"elset={sec.elset}")
            if sec.material:
                args.append(f"material={sec.material}")

            if args:
                f.write(header + ", " + ", ".join(args) + "\n")
            else:
                f.write(header + "\n")

            if sec.data_lines:
                for dl in sec.data_lines:
                    f.write(dl.rstrip() + "\n")
            else:
                # Abaqus/CAE 常写一个逗号占位
                f.write(",\n")

        f.write("*End Part\n")
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

    def copy_nodes_from_nset(self, nset_name:str):
        from InpExchange.BaseObject import Nodes, Nset
    
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



@dataclass
class Assembly:
    name: str
    instances: list[Instance] = field(default_factory=list)
    nsets: list[Nset] = field(default_factory=list)
    elsets: list[Elset] = field(default_factory=list)

    def add_instance(self, inst: Instance) -> None:
        self.instances.append(inst)

    def add_nset(self, nset: Nset) -> None:
        self.nsets.append(nset)

    def add_elset(self, elset: Elset) -> None:
        self.elsets.append(elset)
