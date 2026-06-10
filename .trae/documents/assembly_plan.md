# Assembly部分读入与写出实现计划

## 一、需求分析

根据用户提供的Job-1.inp文件，需要完善以下功能：

### 1.1 Assembly部分读入
- Instance定义（已有）
- Nset（带有instance属性和generate模式）（已有基础）
- Elset（带有instance属性、generate模式和internal标志）（缺少internal支持）
- Surface定义（完全缺失）
- **Equation定义（完全缺失）**

### 1.2 Assembly部分写出
- 目前`to_inp_text()`只输出Part部分，需要扩展输出Assembly部分

### 1.3 Frame结构完善
- 需要添加Surface类支持
- 需要在Elset中添加internal属性支持
- **需要完善Equation类**

### 1.4 新增需求：每个组件添加to_inp_str方法
- Nodes类：添加`to_inp_str()`方法
- Element类：添加`to_inp_str()`方法
- Nset类：添加`to_inp_str()`方法
- Elset类：添加`to_inp_str()`方法
- Section类：添加`to_inp_str()`方法
- Instance类：添加`to_inp_str()`方法
- **Equation类：添加`to_inp_str()`方法**
- Assembly类：添加`to_inp_str()`方法
- Part类：修改`_write_part`为`to_inp_str()`方法

## 二、现有代码分析

### 2.1 InpReader.py
- 已支持读取Assembly、Instance、Nset、Elset
- 缺少Surface关键字解析
- Elset的internal标志未处理
- **缺少Equation关键字解析**
- `to_inp_text()`只输出Part部分

### 2.2 BaseObject.py
- 已有Nset、Elset、Instance、Nodes、Element、Section类
- 缺少Surface类
- Elset缺少internal属性
- **Equation类为空实现**
- 所有类都缺少`to_inp_str()`方法

### 2.3 ModuleObject.py
- Assembly类已有基本结构（instances, nsets, elsets）
- 缺少`surfaces`属性和Surface相关方法
- **缺少`equations`属性和Equation相关方法**
- Part类使用`_write_part()`方法，需要改为`to_inp_str()`

## 三、修改计划

### 3.1 BaseObject.py 修改
1. **Elset类**：添加`internal`属性（布尔类型），添加`to_inp_str()`方法
2. **Surface类**：新建类定义，添加`to_inp_str()`方法
3. **Surfaces容器类**：新建，类似NsSets/ElsSets
4. **Equation类**：完善实现，添加必要属性和`to_inp_str()`方法
5. **Equations容器类**：完善实现
6. **Nodes类**：添加`to_inp_str()`方法
7. **Element类**：添加`to_inp_str()`方法
8. **Nset类**：添加`to_inp_str()`方法
9. **Section类**：添加`to_inp_str()`方法
10. **Instance类**：添加`to_inp_str()`方法

### 3.2 ModuleObject.py 修改
1. **Assembly类**：
   - 添加`surfaces`属性（Surfaces类型）
   - 添加`equations`属性（Equations类型）
   - 添加`add_surface()`方法
   - 添加`add_equation()`方法
   - 添加`to_inp_str()`方法
2. **Part类**：
   - 将`_write_part()`改为`to_inp_str()`方法

### 3.3 InpReader.py 修改
1. 添加Surface解析方法`_read_surface()`
2. 添加Equation解析方法`_read_equation()`
3. 在Elset解析中处理internal标志
4. 修改`to_inp_text()`方法，添加Assembly输出，层层调用各组件的`to_inp_str()`方法

## 四、文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `frame/BaseObject.py` | 添加Surface类、Surfaces容器类、完善Equation类、修改Elset类、为所有组件添加to_inp_str方法 |
| `frame/ModuleObject.py` | 完善Assembly类（添加surfaces、equations属性及相关方法、to_inp_str方法）、修改Part类的_write_part为to_inp_str |
| `InpReader.py` | 添加Surface解析、添加Equation解析、处理Elset的internal标志、修改to_inp_text输出Assembly |

## 五、实现步骤

1. 修改`BaseObject.py`：
   - 在Elset类中添加`internal`属性和`to_inp_str()`方法
   - 创建Surface类和Surfaces容器类，添加`to_inp_str()`方法
   - 完善Equation类和Equations容器类，添加`to_inp_str()`方法
   - 为Nodes、Element、Nset、Section、Instance类添加`to_inp_str()`方法

2. 修改`ModuleObject.py`：
   - 在Assembly类中添加`surfaces`、`equations`属性和`add_surface()`、`add_equation()`方法
   - 为Assembly类添加`to_inp_str()`方法
   - 将Part类的`_write_part()`方法改为`to_inp_str()`方法

3. 修改`InpReader.py`：
   - 添加Surface解析方法
   - 添加Equation解析方法
   - 在Elset解析中处理internal标志
   - 修改`to_inp_text()`方法，调用各组件的`to_inp_str()`方法输出完整内容

4. 测试验证

## 六、to_inp_str方法设计

### 6.1 Nodes.to_inp_str()
```
*Node
node_id, x, y, z
...
```

### 6.2 Element.to_inp_str()
```
*Element, type=elem_type
elem_id, node1, node2, ...
...
```

### 6.3 Nset.to_inp_str()
```
*Nset, nset=name[, instance=instance_name][, generate]
data...
```

### 6.4 Elset.to_inp_str()
```
*Elset, elset=name[, instance=instance_name][, generate][, internal]
data...
```

### 6.5 Section.to_inp_str()
```
*Solid Section/Shell Section, elset=..., material=...
data_lines...
```

### 6.6 Instance.to_inp_str()
```
*Instance, name=name, part=part_name
*End Instance
```

### 6.7 Equation.to_inp_str()
```
*Equation
num_terms
set_name, dof, coefficient
...
```

### 6.8 Part.to_inp_str()
```
*Part, name=name
[Nodes]
[Elements]
[NsSets]
[ElsSets]
[Sections]
*End Part
```

### 6.9 Assembly.to_inp_str()
```
*Assembly, name=name
[Instances]
[NsSets]
[ElsSets]
[Surfaces]
[Equations]
*End Assembly
```

## 七、Equation数据结构设计

根据inp文件格式：
```
*Equation
2
Set-2, 1, 1.
Set-3, 1, -1.
```

Equation类需要包含：
- terms: List[Tuple[str, int, float]] - (set_name, dof, coefficient)
- 或者分开存储：set_names, dofs, coefficients

## 八、风险与注意事项

1. **Surface格式变体**：Surface可能有ELEMENT类型、NODE类型等，需要支持多种格式
2. **internal标志传递**：Elset的internal标志需要正确传递到输出
3. **generate模式输出**：generate模式和独立模式的输出格式需要保持一致
4. **instance属性处理**：Assembly级别的Nset/Elset需要正确输出instance属性
5. **方法命名一致性**：所有组件使用统一的`to_inp_str()`方法命名
6. **Equation格式**：Equation的第一行是项数，后续每行是(set_name, dof, coefficient)