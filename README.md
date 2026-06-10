# InpExchange

InpExchange 是一个用于读取/写入 Abaqus `.inp` 的轻量库。

当前能力：

- 流式读取 `*Part` 内的 `*Node`、`*Element`、`*Nset`、`*Elset`、`*Solid Section/*Shell Section`
- 流式读取 `*Assembly` 内的 `*Instance`、`*Nset`、`*Elset`、`*Surface`、`*Equation`
- 重新写入 inp：同时写出 Part 块和 Assembly 块
- 分裂节点法（SplitNodesMethod）：支持断层区域的节点分裂

## 安装（工作区内）

在仓库根目录执行：

```bash
pip install -e ./
```

## 快速示例

### 示例1：Gmsh 到 Abaqus 转换

```python
from InpExchange import GmshToAbaqus

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
gmsh_model.app("output_mesh.inp")
```

### 示例2：读取和写入标准 Abaqus inp（含 Assembly）

```python
from InpExchange.InpReader import InpModel

model = InpModel.from_file("input_model.inp")

# 访问模型信息
print(f"Parts: {len(model.parts)}")
print(f"Assemblies: {len(model.assemblies)}")

# 写出 inp（包含 Part 和 Assembly）
model.write_inp("output_model.inp")
```

### 示例3：分裂节点法（SplitNodesMethod）

```python
from InpExchange.Applications.SplitNodes import SplitNodesMethod

# 从文件加载模型
split_method = SplitNodesMethod.from_file("input_model.inp")

# 执行分裂节点法
# nset_name: 要分裂的节点集名称（如 fault_surface_1
# sur_ele_nodes_num: 2D 单元节点数（3 或 4）
output_model = split_method.app(
    nset_name="fault_surface_1",
    sur_ele_nodes_num=3,
    output_file="output_split_node.inp"
)
```

## 命令行工具

bin 目录提供命令行工具脚本：

### gmsh_to_abaqus_inp.py

```bash
python bin/gmsh_to_abaqus_inp.py gmsh_mesh.inp -o output_mesh.inp
```

### split_nodes_method.py

```bash
python bin/split_nodes_method.py input_model.inp --nset fault_surface_1 --surface-nodes 3 -o output_split_node.inp
```

## 说明

- `generate` 类型的 Nset/Elset 不会立刻展开成巨大的数组；需要时用 `nset.ids` / `elset.ids` 按需展开。
- `SplitNodesMethod` 通过法向量方向判断分裂节点归属，适用于分裂节点区域变化幅度并不剧烈的情况。
- 写回支持 Part 和 Assembly 块，包括 Instances、Nsets、Elsets、Surfaces、Equations。
