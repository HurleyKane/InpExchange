# InpExchange

InpExchange 是一个用于读取/写入 Abaqus `.inp` 的轻量库。

当前能力（按你最近需求优先级实现）：

- 流式读取 `*Part` 内的 `*Node`、`*Element`、`*Nset`、`*Elset`、`*Solid Section/*Shell Section`
- 流式读取 `*Assembly` 内的 `*Instance`、`*Nset/*Elset`（读入；暂不写回）
- 重新写入 inp：**暂时只写出 Part 块（parts-only）**

## 安装（工作区内）

在仓库根目录执行：

```bash
pip install -e ./
```

## 快速示例

```python
from InpExchange import GmshToAbaqus

gmsh_model = GmshToAbaqus.from_file("gmsh_mesh.inp")
gmsh_model.app("output_mesh.inp")
```

## 说明

- `generate` 类型的 Nset/Elset 不会立刻展开成巨大的数组；需要时用 `nset.ids` / `elset.ids` 按需展开。
- 写回目前只覆盖 Part 块；Assembly/Materials/Steps 等仍需后续扩展。
