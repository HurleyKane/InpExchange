# %%
"""
File Name: BaseObject.py
Created on: 2026/06/08
Author: Chen mingkai
github: chmtk@outlook.com
describe: 
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from InpExchange.frame.ModuleObject import Part

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

# ==========================================================
# Nodes 
# ==========================================================
@dataclass
class Nodes:
    data: np.ndarray
    def __repr__(self):
        num = 0 if self.data is None else len(self.data)
        return (
            f"Nodes(n_nodes={num})"
        )
    
    def __add__(self, other: Nodes):
        if self.data is None:
            return other
        if other.data is None:
            return self
        new_data = np.vstack((self.data, other.data))
        return Nodes(data=new_data)

    def __len__(self):
        if self.data is None:
            return 0
        return self.data.shape[0]

    @property
    def ids(self):
        if self.data is None:
            return None
        return self.data[:, 0].astype(int)

    @property
    def coordinates(self):
        if self.data is None:
            return None
        return self.data[:, 1:]

    def get_max_node_id(self):
        """找出Nset或者中最大的节点编号"""
        max_node_id = max(self.ids) if self.ids is not None else 0
        return max_node_id


# ==========================================================
# Element
# ==========================================================
@dataclass
class Element:
    type: str
    data: np.ndarray

    def __repr__(self):
        return (
            f"Element(type='{self.type}', "
            f"n_elements={len(self.data)})"
        )

    def __getitem__(self, idx:int):
        """
        返回element的结点
        """
        if not isinstance(idx, int):
            raise TypeError("Element indices must be integers")
        index = np.argwhere(self.element_ids == idx).flatten()
        return self.node_ids[index][0]

    @property
    def element_ids(self):
        return self.data[:, 0].astype(int)
    
    @property
    def node_ids(self):
        return self.data[:, 1:].astype(int)


# ==========================================================
# Nset
# ==========================================================
@dataclass 
class Nset:
    nset: str # name
    type: Literal["generate", "independent"]
    node_ids: np.ndarray | None = None
    generate: tuple[int, int, int] | None = None
    instance: str | None = None

    def __repr__(self):
        return (
            f"Nset(nset='{self.nset}', "
            f"type='{self.type}')"
        )   

    @property
    def ids(self) -> np.ndarray:
        """返回节点编号数组；generate 类型时按需展开。"""
        if self.type == "generate":
            if self.generate is None:
                return np.array([], dtype=int)
            start, end, inc = self.generate
            return np.arange(start, end + 1, inc, dtype=int)
        return np.array([], dtype=int) if self.node_ids is None else self.node_ids


# ==========================================================
# Elset
# ==========================================================
@dataclass 
class Elset:
    elset: str
    type: Literal["generate", "independent"]
    element_ids: np.ndarray | None = None
    generate: tuple[int, int, int] | None = None
    instance: str | None = None

    def __repr__(self):
        return (
            f"Elset(elset='{self.elset}', "
            f"type='{self.type}')"
        )

    @property
    def ids(self) -> np.ndarray:
        """返回单元编号数组；generate 类型时按需展开。"""
        if self.type == "generate":
            if self.generate is None:
                return np.array([], dtype=int)
            start, end, inc = self.generate
            return np.arange(start, end + 1, inc, dtype=int)
        return np.array([], dtype=int) if self.element_ids is None else self.element_ids

    def transform_to_nset(self, part: Part):
        """将elset转换为nset
        Part: 从part中获取nset需要的node的ids
        """
        if part.nodes is None: 
            raise ValueError("part.nodes is None")
        elset = self
        name = elset.elset
        nset = Nset(nset=name, type="independent")

        temp_set = set()
        elset_element_ids = elset.element_ids
        for element_id in elset_element_ids: # type: ignore
            arg = part.find_element_position(int(element_id))
            temp_element = part.elements[arg]
            node_ids = temp_element[int(element_id)]
            temp_set = temp_set.union(set(node_ids))

        nset.node_ids = np.array(list(temp_set), dtype=int)
        nset.node_ids.shape
        return nset

# ==========================================================
# Section
# ==========================================================
@dataclass
class Section:
    """单元截面定义（如 *Solid Section / *Shell Section）。

    说明：Abaqus 的 Section 数据行格式很多，这里先保留原始数据行，
    仅解析关键字行里常用的 elset/material。
    """

    keyword: Literal["Solid Section", "Shell Section", "Section"]
    elset: str | None = None
    material: str | None = None
    data_lines: list[str] = field(default_factory=list)

    def __repr__(self):
        return (
            f"Section(keyword='{self.keyword}', "
            f"elset={self.elset!r}, material={self.material!r}, "
            f"n_lines={len(self.data_lines)})"
        )


# ==========================================================
# Instance
# ==========================================================
@dataclass
class Instance:
    name: str
    part: str | None = None

    def __repr__(self):
        return (
            f"Instance(name={self.name!r}, part={self.part!r})"
        )

@dataclass
class Elements:
    elements: list[Element] = field(default_factory=list)

    def add(self, element):
        self.elements.append(element)
    
    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    def __repr__(self) -> str:
        return f"Elements(n_blocks={len(self.elements)})"

    def __getitem__(self, key)->Element:
        return self.elements[key]   

@dataclass
class Nsets:
    data: list[Nset] = field(default_factory=list)

    def __len__(self):
        return len(self.data)

    def add(self, nset):
        self.data.append(nset)

    def __iter__(self):
        return iter(self.data)

    def __repr__(self) -> str:
        return f"Nsets(n_blocks={len(self.data)})"
    
    def __getitem__(self, key:str|int):
        if isinstance(key, int):
            return self.data[key] 
        elif isinstance(key, str):
            for nset in self.data:
                if nset.nset == key:
                    return nset
            raise KeyError(f"Nset not found: {key}")
        else:
            raise TypeError(f"Key must be int or str, not {type(key)}")

@dataclass
class Elsets:
    data: list[Elset] = field(default_factory=list)

    def __len__(self):
        return len(self.data)

    def add(self, elset):
        self.data.append(elset)

    def __iter__(self):
        return iter(self.data)

    def __repr__(self) -> str:
        return f"Elsets(n_blocks={len(self.data)})"
    
    def __getitem__(self, key):
        return self.data[key]

@dataclass
class Sections:
    data: list[Section] = field(default_factory=list)

    def __len__(self):
        return len(self.data)

    def add(self, section):
        self.data.append(section)

    def __iter__(self):
        return iter(self.data)  
    
    def __repr__(self) -> str:
        return f"Sections(n_blocks={len(self.data)})" 
    
    def __getitem__(self, key):
        return self.data[key]

# ==========================================================
# Instance (assembly组件)
# ==========================================================
@dataclass 
class Instances: 
    data: list[Instance] = field(default_factory=list)

    def __len__(self):
        return len(self.data)

    def add(self, instance):
        self.data.append(instance)

    def __iter__(self):
        return iter(self.data)  
    
    def __repr__(self) -> str:
        return f"Instances(n_blocks={len(self.data)})" 
    
    def __getitem__(self, key):
        return self.data[key]
    

# =========================================================
# Equation (constraint组件)
# =========================================================
@dataclass 
class Equation:
    pass 

@dataclass 
class Equations:
    data: list[Equation] = field(default_factory=list)