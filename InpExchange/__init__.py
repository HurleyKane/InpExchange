"""InpExchange: 读取/写入 Abaqus .inp（当前以 Part 为主）。

快速使用：

```python
from InpExchange import InpModel
m = InpModel.from_file("Job-1.inp")
print(m.parts[0].nodes.shape)

# 仅写回 Part 块（parts-only）
m.write_inp("Job-1_parts_only.inp")
```
"""
