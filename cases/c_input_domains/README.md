# C 输入域：完整类型范围与关系约束

这是可组合契约的第一步，新增输入 schema 3。旧 schema 1/2 保持显式
min/max 的约定。本阶段发布时保持既有 C 语义、循环检查和小数组限制。
该域阶段现有用户回传 13/13；随后扩展的容量/有效长度见
[新数组协议](../c_array_capacity/README.md)。仍未实现结构体、有符号整数、浮点数或无界循环。

## 运行正式验收

使用现有修改版 ESBMC，在仓库根目录运行：

```bash
bash cases/c_input_domains/test_domains.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

目标：`C INPUT DOMAIN ACCEPTANCE: 13/13 passed; inputs/tools unchanged=True`。
脚本保存单独的运行目录、输入与引擎副本、逐项报告和 `c-input-domains-*.tar.gz`。
本地测试中的模拟证明与原生运行不算正式证明；缺失求解器时整阶段必须失败。
已有历史实验的引擎锁不更新。需要重现 popcount 固定引擎实验时，使用独立
checkout `79e6aa0` 或相应历史提交，不能在新引擎上把旧实验称作引擎未变。

## 新输入格式

`ordered_full.json` 的主要部分：

```json
{
  "schema": 3,
  "name": "ordered_full",
  "original": {"source": "maximum.c", "entry": "choose", "args": ["x", "y"]},
  "candidate": {"source": "second.c", "entry": "choose", "args": ["x", "y"]},
  "inputs": {"x": {"type": "uint32_t"}, "y": {"type": "uint32_t"}},
  "constraints": "x <= y",
  "return_type": "uint32_t",
  "observations": ["return"],
  "unwind": 8
}
```

原程序求最大值，候选程序直接返回第二个参数。每个整数默认覆盖
0..4294967295，而整个研究域是其中满足 x <= y 的所有输入组合。
预期结果 true 的含义是**这个声明域内全部等价**，不是对所有无约束整数对的结论。

```bash
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract cases/c_input_domains/ordered_full.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

## 约束语法与含义

- schema 3 允许省略任一 min/max；省略的边界分别取 0 和类型最大值。
  uint32_t 最大值 4294967295，bool 最大值 1。数组默认作用于每个元素。
- 可选 `constraints` 默认为 JSON `true`。允许 JSON true/false、比较原子、
  `{"all": [...]}`、`{"any": [...]}`、`{"not": ...}`，可组合嵌套。
- 原子支持声明字段之间或字段与常量之间的 `== != < <= > >=`，以及裸 bool 字段。
  常量是非负十进制整数或 UINT32_MAX。字符串不是任意 C/Python 表达式。
- 数组初始元素通过 `a_0`、`a_1` 等字段引用。例如 `"a_0 == a_1"`。
- 最多 128 个表达式节点、深度 12。当前不接受算术表达式、量词、函数调用、
  取模、输出字段或未声明字段。约束属于用户契约，不是搜索器偷偷增加的假设。
- `n < capacity` 与 `capacity <= 2` 的组合见 `array_index.json`：数组的
  物理长度仍固定为 2，capacity 是受约束的逻辑输入，不代表动态内存支持。

```json
{"all": ["n < capacity", "capacity <= 2"]}
```

类型边界与关系约束共同用于安全、可行性、等价、补集及验收复核查询。
原生输入筛选、生成的探针和 agent seed 检查使用同一约束语义。
所有 safety 义务仍覆盖整个声明域，展开不足仍失败；不自动删除不安全输入。
约束或源码变动会使已有 agent 会话身份失效，必须重新开始。

搜索仍从完整声明域开始。边界样本未命中域内输入，不意味着域为空；由后端检查
可行性。约束矛盾时应报告 EMPTY_DOMAIN，不发布 vacuous 的等价结论。
报告同时保留原始输入声明、补全后的范围、关系约束和全部原有证明义务。

## 验收案例

| 案例 | 目的 |
|---|---|
| type_default | 不填写上下界，完整 uint32 域上的奇偶实现比较 |
| ordered_full | 在 x <= y 下，最大值计算可替换为返回 y |
| ordered_region | 同一个关系域内，最大值与最小值只在 x == y 时等价 |
| safe_division | 在 x < y 的无符号域内，x/y 等于 0，且约束排除除零 |
| array_index | n < capacity <= 2 下，数组访问与带判断的访问一致 |
| array_equal | 数组初始元素关系与完整数组观察组合 |
| mixed_bool | bool/整数与 all/any/not 组合约束 |
| no_boundary_seed | 合法域只有 x=7,y=11，默认边界样本为空仍应发现可行输入 |
| empty_relation | x < y 且 y <= x，只报告空域 |
| unsafe_division | 移除关系约束，除零必须阻止等价发布 |
| unsafe_index | 移除关系约束，越界必须阻止等价发布 |
| missing-solver | 缺失求解器保持 UNKNOWN，零原生执行样本 |
| agent-domain | 域外 seed 被拒绝，域内条件仍可认证；脚本化协议控制 |

验收预期条件只在发现之后独立检查，不传给发现器。这是功能集成验收，
不是独立盲测，也不是自主 agent 性能实验。

[本阶段回传记录](../../docs/validation/c-input-domains/user-reported-results.md)保存 13/13 与归档路径；
它不代替后续容量/长度阶段的正式验收。本阶段建立共享输入域语义。
[当前契约指南](../../docs/C_SCALAR_TOOL.md) · [项目交接](../../docs/PROJECT_STATUS.md)
