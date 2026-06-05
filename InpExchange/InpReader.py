# %%
"""
File Name: reader.py
Created on: 2026/06/05
Author: Chen mingkai
github: chmtk@outlook.com
describe: 该代码提供gmsh和abaqus的inp文件的转换。具体功能：
1. 读取inp文件中的Part, node, element, nset, elset等部分
2. 读取abaqus inp文件中的part部分的几何设置
3. 重新写入abaqus inp文件（part部分）
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

from typing import Literal
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import io
1

class _PushbackLineIter:
    """可回退的行迭代器，用于流式解析关键字块。

    目的：解析 *Node/*Element 这类“读到下一个 * 关键字才结束”的块时，
    能把已经读到的下一条关键字行放回去，让外层循环继续处理。
    """

    def __init__(self, iterable):
        self._it = iter(iterable)
        self._buf: list[str] = []

    def push(self, line: str) -> None:
        self._buf.append(line)

    def __iter__(self):
        return self

    def __next__(self) -> str:
        if self._buf:
            return self._buf.pop()
        return next(self._it)


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
# Part
# ==========================================================
@dataclass
class Part:
    name: str
    nodes: np.ndarray | None = None
    elements: list[Element] = field(default_factory=list) # 每次创建 Part 对象时，自动调用 list() 创建一个新的空列表作为默认值。
    nsets: list[Nset] = field(default_factory=list)
    elsets: list[Elset] = field(default_factory=list)  
    sections: list[Section] = field(default_factory=list)

    def add_element(self, element: Element):
        self.elements.append(element)
    
    def add_nsets(self, nset: Nset):
        self.nsets.append(nset)
    
    def add_elsets(self, elset: Elset):
        self.elsets.append(elset)   

    def add_section(self, section: 'Section'):
        self.sections.append(section)

    @property
    def node_ids(self):
        if self.nodes is None:
            return None
        return self.nodes[:, 0].astype(int)

    @property
    def coordinates(self):
        if self.nodes is None:
            return None
        return self.nodes[:, 1:]

    def __repr__(self):
        n_nodes = 0 if self.nodes is None else len(self.nodes)
        return (
            f"Part(name='{self.name}', "
            f"n_nodes={n_nodes}, "
            f"n_element_blocks={len(self.elements)})"
            f""
        )

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
# Assembly / Instance
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

# ==========================================================
# INP Model
# ==========================================================
class InpModel:
    def __init__(self):
        self.parts: list[Part] = []
        # Assembly 结构（通常只有一个，但用 list 兼容多 Assembly）
        self.assemblies: list[Assembly] = []
        # 兼容：仍保留扁平化的 assembly 级别集合列表
        self.nsets: list[Nset] = []
        self.elsets: list[Elset] = []

    def add_part(self, part: Part):
        self.parts.append(part)

    def add_nset(self, nset: Nset):
        self.nsets.append(nset)

    def add_elset(self, elset: Elset):
        self.elsets.append(elset)

    def add_assembly(self, assembly: Assembly) -> None:
        self.assemblies.append(assembly)

    @classmethod
    def from_file(cls, file_path: str | Path):
        model = cls()
        model._read(file_path)
        return model

    def _try_read_part(self, line: str) -> Part | None:
        """尝试解析 *Part。

        解析成功则创建 Part、加入模型并返回该 Part；否则返回 None。
        """
        if not line.lower().startswith("*part"):
            return None

        name = self._parse_keyword_arg(line, "name")
        if name is None:
            raise ValueError(f"Part name not found in line: {line}")

        part = Part(name=name)
        self.add_part(part)
        return part

    @staticmethod
    def _is_end_part(line: str) -> bool:
        lower_line = line.lower().strip()
        return lower_line.startswith("*end part")

    @staticmethod
    def _is_start_assembly(line: str) -> bool:
        return line.lower().strip().startswith("*assembly")

    @staticmethod
    def _is_end_assembly(line: str) -> bool:
        return line.lower().strip().startswith("*end assembly")

    @staticmethod
    def _is_instance(line: str) -> bool:
        return line.lower().strip().startswith("*instance")

    @staticmethod
    def _is_end_instance(line: str) -> bool:
        return line.lower().strip().startswith("*end instance")

    @staticmethod
    def _has_flag(line: str, flag: str) -> bool:
        """判断关键字行里是否包含某个无等号 flag，比如 generate/internal。"""
        parts = [p.strip().lower() for p in line.split(",")]
        flag = flag.strip().lower()
        return any(p == flag for p in parts[1:])

    @staticmethod
    def _read_int_block(lines: _PushbackLineIter) -> list[int]:
        """读取直到下一个 * 关键字行出现，返回扁平化的 int 列表。"""
        buf: list[int] = []
        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break
            for v in row.split(","):
                v = v.strip()
                if v:
                    buf.append(int(v))
        return buf

    def _read_nset(self, current_part: Part | None, header_line: str, lines: _PushbackLineIter, *, in_assembly: bool) -> None:
        name = self._parse_keyword_arg(header_line, "nset")
        if name is None:
            raise ValueError(f"Nset name not found in line: {header_line}")
        instance = self._parse_keyword_arg(header_line, "instance")
        is_generate = self._has_flag(header_line, "generate")

        data = self._read_int_block(lines)

        if is_generate:
            if len(data) < 3:
                raise ValueError(f"Nset generate expects 3 integers (start,end,inc). Got: {data}")
            nset = Nset(nset=name, type="generate", generate=(data[0], data[1], data[2]), instance=instance)
        else:
            nset = Nset(nset=name, type="independent", node_ids=np.array(data, dtype=int), instance=instance)

        if in_assembly:
            # 兼容：仍写入扁平列表
            self.add_nset(nset)
            return
        if current_part is None:
            raise ValueError("Encountered *Nset before *Part")
        current_part.add_nsets(nset)

    def _read_elset(self, current_part: Part | None, header_line: str, lines: _PushbackLineIter, *, in_assembly: bool) -> None:
        name = self._parse_keyword_arg(header_line, "elset")
        if name is None:
            raise ValueError(f"Elset name not found in line: {header_line}")
        instance = self._parse_keyword_arg(header_line, "instance")
        is_generate = self._has_flag(header_line, "generate")

        data = self._read_int_block(lines)

        if is_generate:
            if len(data) < 3:
                raise ValueError(f"Elset generate expects 3 integers (start,end,inc). Got: {data}")
            elset = Elset(elset=name, type="generate", generate=(data[0], data[1], data[2]), instance=instance)
        else:
            elset = Elset(elset=name, type="independent", element_ids=np.array(data, dtype=int), instance=instance)

        if in_assembly:
            # 兼容：仍写入扁平列表
            self.add_elset(elset)
            return
        if current_part is None:
            raise ValueError("Encountered *Elset before *Part")
        current_part.add_elsets(elset)

    def _read_section(self, current_part: Part | None, header_line: str, lines: _PushbackLineIter) -> None:
        """读取 *Solid Section / *Shell Section 等 section 块。"""
        if current_part is None:
            raise ValueError("Encountered *Section before *Part")

        lower = header_line.lower().strip()
        if lower.startswith("*solid section"):
            keyword: Literal["Solid Section", "Shell Section", "Section"] = "Solid Section"
        elif lower.startswith("*shell section"):
            keyword = "Shell Section"
        else:
            keyword = "Section"

        elset = self._parse_keyword_arg(header_line, "elset")
        material = self._parse_keyword_arg(header_line, "material")

        data_lines: list[str] = []
        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break
            data_lines.append(row)

        current_part.add_section(
            Section(keyword=keyword, elset=elset, material=material, data_lines=data_lines)
        )

    def _read_nodes(self, current_part: Part | None, lines: _PushbackLineIter) -> None:
        """读取 *Node 块，写入 current_part.nodes。"""
        if current_part is None:
            # Abaqus 里 *Node 也可能出现在 *Part 外；这里保持严格。
            raise ValueError("Encountered *Node before *Part")

        node_buffer: list[list[float]] = []

        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break

            vals = [
                float(v.strip())
                for v in row.split(",")
                if v.strip()
            ]
            node_buffer.append(vals)

        current_part.nodes = np.array(node_buffer, dtype=float)

    def _read_elements(self, current_part: Part | None, elem_header_line: str, lines: _PushbackLineIter) -> None:
        """读取 *Element 块，并追加到 current_part.elements。"""
        if current_part is None:
            raise ValueError("Encountered *Element before *Part")

        elem_type = self._parse_keyword_arg(elem_header_line, "type")
        if elem_type is None:
            raise ValueError(f"Element type not found in line: {elem_header_line}")

        elem_buffer: list[list[int]] = []

        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break

            vals = [
                int(v.strip())
                for v in row.split(",")
                if v.strip()
            ]
            elem_buffer.append(vals)

        current_part.add_element(
            Element(
                type=elem_type,
                data=np.array(elem_buffer, dtype=int)
            )
        )

    def _read(self, file_path):

        current_part: Part | None = None
        in_assembly = False
        current_assembly: Assembly | None = None

        # 大文件优化：不要一次性读入整个文件（read_text/splitlines 会把全文加载到内存）。
        # 这里采用流式逐行解析，但仍会把 nodes/elements 数据存入 numpy 数组（这是模型本身需要的）。
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = _PushbackLineIter(f)

            for raw in lines:
                line = raw.strip()

                # --------------------------------------------------
                # 跳过空行和注释
                # --------------------------------------------------
                if not line or line.startswith("**"):
                    continue

                lower_line = line.lower()

                # ==================================================
                # End Part
                # ==================================================
                if self._is_end_part(line):
                    current_part = None
                    continue

                # ==================================================
                # Assembly
                # ==================================================
                if self._is_start_assembly(line):
                    in_assembly = True
                    assem_name = self._parse_keyword_arg(line, "name") or "Assembly"
                    current_assembly = Assembly(name=assem_name)
                    self.add_assembly(current_assembly)
                    continue
                if self._is_end_assembly(line):
                    in_assembly = False
                    current_assembly = None
                    continue

                # ==================================================
                # Instance (inside Assembly)
                # ==================================================
                if in_assembly and self._is_instance(line):
                    inst_name = self._parse_keyword_arg(line, "name")
                    part_name = self._parse_keyword_arg(line, "part")
                    if inst_name is None:
                        raise ValueError(f"Instance name not found in line: {line}")
                    inst = Instance(name=inst_name, part=part_name)
                    if current_assembly is not None:
                        current_assembly.add_instance(inst)

                    # Abaqus/CAE 的 *Instance 块通常只有 *End Instance，
                    # 这里流式跳过直到 *End Instance。
                    for raw2 in lines:
                        row = raw2.strip()
                        if not row or row.startswith("**"):
                            continue
                        if self._is_end_instance(row):
                            break
                        # 允许出现其他行，但不解析
                        continue
                    continue

                # ==================================================
                # Part
                # ==================================================
                maybe_part = self._try_read_part(line)
                if maybe_part is not None:
                    current_part = maybe_part
                    continue

                # ==================================================
                # Node
                # ==================================================
                if lower_line.startswith("*node"):
                    self._read_nodes(current_part, lines)
                    continue

                # ==================================================
                # Element
                # ==================================================
                if lower_line.startswith("*element"):
                    self._read_elements(current_part, line, lines)
                    continue

                # ==================================================
                # Nset
                # ==================================================
                if lower_line.startswith("*nset"):
                    self._read_nset(current_part, line, lines, in_assembly=in_assembly)
                    # 同步写入 assembly 对象
                    if in_assembly and current_assembly is not None:
                        current_assembly.add_nset(self.nsets[-1])
                    continue

                # ==================================================
                # Elset
                # ==================================================
                if lower_line.startswith("*elset"):
                    self._read_elset(current_part, line, lines, in_assembly=in_assembly)
                    if in_assembly and current_assembly is not None:
                        current_assembly.add_elset(self.elsets[-1])
                    continue

                # ==================================================
                # Section (Solid/Shell)
                # ==================================================
                if lower_line.startswith("*solid section") or lower_line.startswith("*shell section"):
                    self._read_section(current_part, line, lines)
                    continue
                

                # 其他关键字暂不处理：直接跳过
                # 例如：*Assembly, *Nset, *Elset, *Material 等
                continue

    @staticmethod
    def _parse_keyword_arg(
        line: str,
        key: str
    ) -> str | None:
        """
        从关键字行中解析参数值
        """
        parts = line.split(",")

        for item in parts[1:]:

            item = item.strip()

            if "=" not in item:
                continue

            k, v = item.split("=", 1)

            if k.strip().lower() == key.lower():
                return v.strip()

        return None

    def __repr__(self):
        return (
            f"InpModel(n_parts={len(self.parts)})"
        )


    # ==========================================================
    # Write INP (Parts only)
    # ==========================================================
    @staticmethod
    def _fmt_float(x: float) -> str:
        # Abaqus inp 对浮点格式不敏感；用通用格式减少无意义的小数位。
        try:
            return f"{float(x):.15g}"
        except Exception:
            return str(x)

    @staticmethod
    def _write_int_list(f, values: np.ndarray | list[int], *, per_line: int = 16, indent: str = "") -> None:
        arr = values if isinstance(values, list) else values.tolist()
        if not arr:
            f.write(f"{indent}\n")
            return
        for i in range(0, len(arr), per_line):
            chunk = arr[i:i + per_line]
            f.write(indent + ", ".join(str(int(v)) for v in chunk) + "\n")

    def _write_part(self, f, part: Part) -> None:
        f.write(f"*Part, name={part.name}\n")

        # Nodes
        if part.nodes is not None and len(part.nodes) > 0:
            f.write("*Node\n")
            for row in part.nodes:
                node_id = int(row[0])
                coords = row[1:]
                f.write(
                    str(node_id)
                    + ", "
                    + ", ".join(self._fmt_float(v) for v in coords)
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
                self._write_int_list(f, nset.ids)

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
                self._write_int_list(f, elset.ids)

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

    def to_inp_text(self) -> str:
        """导出 inp 文本（当前仅写出 *Part 块）。"""
        buf = io.StringIO()
        buf.write("*Heading\n")
        buf.write("** Generated by InpExchange (parts only)\n")
        buf.write("**\n")
        buf.write("** PARTS\n")
        buf.write("**\n")
        for part in self.parts:
            self._write_part(buf, part)
        return buf.getvalue()

    def write_inp(self, file_path: str | Path) -> None:
        """写入 inp 文件（当前仅写出 *Part 块）。"""
        file_path = Path(file_path)
        file_path.write_text(self.to_inp_text(), encoding="utf-8")


if __name__ == "__main__":
    model = InpModel.from_file(
        # "strike_slip.inp"
        "Job-1.inp"
    )
    part = model.parts[0]
    elem = part.elements[0]
    part.nsets

    # parts-only 写回示例
    model.write_inp("Job-1_parts_only.inp")