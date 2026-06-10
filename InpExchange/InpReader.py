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

from InpExchange.frame.BaseObject import (
    Element, Nset, Elset, Section, Instance, Nodes, Surface, Equation
)
from InpExchange.frame.ModuleObject import Part, Assembly

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
# INP Model
# ==========================================================
class InpModel:
    def __init__(self):
        self.parts: list[Part] = []
        self.assemblies: list[Assembly] = []

    def add_part(self, part: Part):
        self.parts.append(part)
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

    def _read_nset(
        self,
        current_part: Part | None,
        current_assembly: Assembly | None,
        header_line: str,
        lines: _PushbackLineIter,
        *,
        in_assembly: bool,
    ) -> None:

        name = self._parse_keyword_arg(header_line, "nset")
        if name is None:
            raise ValueError(f"Nset name not found in line: {header_line}")

        instance = self._parse_keyword_arg(header_line, "instance")
        is_generate = self._has_flag(header_line, "generate")

        data = self._read_int_block(lines)

        if is_generate:
            if len(data) < 3:
                raise ValueError(
                    f"Nset generate expects 3 integers (start,end,inc). Got: {data}"
                )

            nset = Nset(
                nset=name,
                type="generate",
                generate=(data[0], data[1], data[2]),
                instance=instance,
            )

        else:
            nset = Nset(
                nset=name,
                type="independent",
                node_ids=np.array(data, dtype=int),
                instance=instance,
            )

        if in_assembly:
            if current_assembly is None:
                raise ValueError("Assembly Nset found but current_assembly is None")

            current_assembly.add_nset(nset)
            return

        if current_part is None:
            raise ValueError("Encountered *Nset before *Part")

        current_part.nsets.add(nset)


    def _read_elset(
        self,
        current_part: Part | None,
        current_assembly: Assembly | None,
        header_line: str,
        lines: _PushbackLineIter,
        *,
        in_assembly: bool,
    ) -> None:

        name = self._parse_keyword_arg(header_line, "elset")
        if name is None:
            raise ValueError(f"Elset name not found in line: {header_line}")

        instance = self._parse_keyword_arg(header_line, "instance")
        is_generate = self._has_flag(header_line, "generate")
        is_internal = self._has_flag(header_line, "internal")

        data = self._read_int_block(lines)

        if is_generate:
            if len(data) < 3:
                raise ValueError(
                    f"Elset generate expects 3 integers (start,end,inc). Got: {data}"
                )

            elset = Elset(
                elset=name,
                type="generate",
                generate=(data[0], data[1], data[2]),
                instance=instance,
                internal=is_internal,
            )

        else:
            elset = Elset(
                elset=name,
                type="independent",
                element_ids=np.array(data, dtype=int),
                instance=instance,
                internal=is_internal,
            )

        if in_assembly:
            if current_assembly is None:
                raise ValueError("Assembly Elset found but current_assembly is None")

            current_assembly.add_elset(elset)
            return

        if current_part is None:
            raise ValueError("Encountered *Elset before *Part")

        current_part.elsets.add(elset)

    def _read_surface(
        self,
        current_assembly: Assembly | None,
        header_line: str,
        lines: _PushbackLineIter,
    ) -> None:
        """读取 *Surface 块。"""
        if current_assembly is None:
            raise ValueError("Encountered *Surface outside Assembly")

        name = self._parse_keyword_arg(header_line, "name")
        surf_type = self._parse_keyword_arg(header_line, "type") or "ELEMENT"
        if name is None:
            raise ValueError(f"Surface name not found in line: {header_line}")


        data_lines: list[str] = []
        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break
            data_lines.append(row)

        for dl in data_lines:
            parts = [p.strip() for p in dl.split(",") if p.strip()]
            if len(parts) >= 1:
                elset_name = parts[0]
                side = parts[1] if len(parts) > 1 else None
                surface = Surface(
                    name=name,
                    type=surf_type, # type: ignore
                    elset=elset_name,
                    side=side,
                )
                current_assembly.add_surface(surface)

    def _read_equation(
        self,
        current_assembly: Assembly | None,
        lines: _PushbackLineIter,
    ) -> None:
        """读取 *Equation 块。"""
        if current_assembly is None:
            raise ValueError("Encountered *Equation outside Assembly")

        terms: list[tuple[str, int, float]] = []

        for raw2 in lines:
            row = raw2.strip()
            if not row or row.startswith("**"):
                continue
            if row.startswith("*"):
                lines.push(raw2)
                break

            parts = [p.strip() for p in row.split(",") if p.strip()]
            if len(parts) >= 3:
                set_name = parts[0]
                dof = int(parts[1])
                coefficient = float(parts[2])
                terms.append((set_name, dof, coefficient))

        equation = Equation(terms=terms)
        current_assembly.add_equation(equation)

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

        current_part.sections.add(
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

        current_part.nodes = Nodes(data=np.array(node_buffer, dtype=float))

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

        current_part.elements.add(
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
                    if current_part is None:
                        current_part = Part(name="Part-1")
                        self.parts.append(current_part)
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
                    self._read_nset(
                        current_part,
                        current_assembly,
                        line,
                        lines,
                        in_assembly=in_assembly,
                    )
                    continue
                
                # ==================================================
                # Elset
                # ==================================================
                if lower_line.startswith("*elset"):
                    self._read_elset(
                        current_part,
                        current_assembly,
                        line,
                        lines,
                        in_assembly=in_assembly,
                    )
                    continue

                # ==================================================
                # Section (Solid/Shell)
                # ==================================================
                if lower_line.startswith("*solid section") or lower_line.startswith("*shell section"):
                    self._read_section(current_part, line, lines)
                    continue

                # ==================================================
                # Surface (inside Assembly)
                # ==================================================
                if in_assembly and lower_line.startswith("*surface"):
                    self._read_surface(current_assembly, line, lines)
                    continue

                # ==================================================
                # Equation (inside Assembly)
                # ==================================================
                if in_assembly and lower_line.startswith("*equation"):
                    self._read_equation(current_assembly, lines)
                    continue
                

                # 其他关键字暂不处理：直接跳过
                # 例如：*Material 等
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
            f"InpModel(n_parts={len(self.parts)}, n_assemblies={len(self.assemblies)})"
        )

    def to_inp_text(self) -> str:
        """导出 inp 文本（包含 Parts 和 Assembly）。"""
        buf = io.StringIO()
        buf.write("*Heading\n")
        buf.write("** Generated by InpExchange for abaqus 2025\n")
        buf.write("**\n")
        
        # Parts
        buf.write("** PARTS\n")
        buf.write("**\n")
        for part in self.parts:
            buf.write(part.to_inp_str())
        
        # Assembly
        if self.assemblies:
            buf.write("**\n")
            buf.write("** ASSEMBLY\n")
            buf.write("**\n")
            for assembly in self.assemblies:
                buf.write(assembly.to_inp_str())
        
        return buf.getvalue()

    def write_inp(self, file_path: str | Path) -> None:
        """写入 inp 文件（包含 Parts 和 Assembly）。"""
        file_path = Path(file_path)
        file_path.write_text(self.to_inp_text(), encoding="utf-8")


if __name__ == "__main__":
    model = InpModel.from_file(
        "./tests/Job-1.inp"
    )
    part = model.parts[0]
    elem = part.elements[0]
    part.nsets

    # # parts-only 写回示例
    model.write_inp("Job-1_parts_only.inp") 