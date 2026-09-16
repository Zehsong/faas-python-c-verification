# 有界数组输入与输出：单次调用

通用 C 接口的 `schema: 2` 支持固定长度数组参数及其最终内容观察。两边分别获得
独立、完整初始化的数组，初值来自同一组符号输入。函数可以原地修改自己的数组。
等价要求**返回值和每个数组的全部最终元素都相同**。

这是一项受限的单次调用能力：不支持别名、任意指针、动态长度、堆、全局状态或调用序列。
`schema: 1` 的标量/局部只读表约定继续使用原来的形式。

## 在 Codespace 运行

使用已有修改版 ESBMC。此次还修改了共享的原生观察比较，因此同时重跑只读表阶段；
两个阶段分别保存证据，不覆盖之前的归档。

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
ESBMC=/workspaces/esbmc-current/build/src/esbmc/esbmc
bash cases/c_readonly_tables/test_tables.sh "$ESBMC"
bash cases/c_bounded_arrays/test_arrays.sh "$ESBMC"
```

目标为只读表 `9/9` 和 `C BOUNDED ARRAY ACCEPTANCE: 10/10 passed`，然后打印新的
`c-bounded-arrays-*.tar.gz` 证据路径。用户已报告数组 **10/10**；[记录与来源](../../docs/validation/c-bounded-arrays/user-reported-results.md)。
本次只读表重跑结果尚未提供。
[本地记录](../../docs/validation/c-bounded-arrays/README.md)包含 149 项回归及缺少求解器的负向检查。

| 检查 | 比较内容 | 期望 |
|---|---|---|
| swap | 交换两个元素 vs 保持原数组，均返回 0 | EXACT：初始 a_0 == a_1 |
| increment | 逐项加一 vs 循环加一 | EXACT：true |
| copy_reverse | 正向复制 vs 逆序复制，src/dst 独立 | EXACT：初始 src_0 == src_1 |
| return_mutant | 数组均不变，但返回 0 vs 1 | EXACT：false |
| unsafe_index | 长度 2，索引域包含 2 | UNKNOWN：安全检查失败，无原生输入执行 |
| short_unwind | 两次循环但展开限制 1 | UNKNOWN：展开不足，无原生输入执行 |
| const_write | 试图修改 const 数组参数 | UNSUPPORTED_INPUT |
| alias_rejected | 把同一逻辑数组重复绑定到两个参数 | INPUT_REJECTED |
| missing-solver | 找不到指定 ESBMC | UNKNOWN |
| agent-array | 先提出 true，再提出 a_0 == a_1 | 第一项被原生数组反例否定，不增加求解查询；第二项认证为 EXACT |

前四项的预期公式只在发现结束后另做后端检查，不传入发现过程。agent 项是脚本协议
测试，不代表自主发现性能。`swap` 特意让返回值始终相同，以检查工具不会漏掉数组差异。

## 约定例子

输入代码使用固定长度的数组参数语法，以下两份代码都返回标量：

```c
/* original.c */
#include <stdint.h>
uint32_t transform(uint32_t a[2]) {
    uint32_t t = a[0u];
    a[0u] = a[1u];
    a[1u] = t;
    return 0u;
}
```

```c
/* candidate.c */
#include <stdint.h>
uint32_t transform(uint32_t a[2]) { return 0u; }
```

```json
{
  "schema": 2,
  "name": "swap",
  "original": {"source": "original.c", "entry": "transform", "args": ["a"]},
  "candidate": {"source": "candidate.c", "entry": "transform", "args": ["a"]},
  "inputs": {"a": {"type": "uint32_t[]", "length": 2, "min": 0, "max": 3}},
  "return_type": "uint32_t",
  "observations": ["return", "a"],
  "unwind": 4
}
```

现成案例可直接运行：

```bash
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract cases/c_bounded_arrays/swap.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

`a_0`、`a_1` 表示调用前的 `a[0]`、`a[1]`，不是最终数组元素。条件和 agent seeds
使用这些展开后的字段。所有元素各自取 min..max（含端点），相互独立。
约定内 `observations` 必须依次列出 return 和按输入声明顺序的所有数组，不能忽略修改。
纯输出数组本阶段也必须有声明的初始值域；没有未初始化输出缓冲区。

```bash
python3 tools/find-cond-equiv/agent_workflow.py start \
  --case c --contract cases/c_bounded_arrays/swap.json --goal exact \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

新会话可接收 `condition: "a_0 == a_1"` 和 `seeds: [{"a_0": 0, "a_1": 1}]`，
完整 proposal 仍需要会话 UUID 和轮次。不要重用升级前的会话。

## 支持边界与证据

- 每个数组长度 1..4；所有数组元素加普通标量输入合计最多四个值。支持 uint32_t/bool，
  函数仍须返回 uint32_t/bool；暂不支持 void。数组元素初始域使用统一 min/max。
- 参数声明使用 `uint32_t a[2]`、`const uint32_t src[2]` 或 bool 对应形式。
  普通 `T *p`、不定长、二维、static/restrict 参数，以及数组传给辅助函数均拒绝。
- 允许 uint32_t 索引读取，非 const 参数允许逐元素 `=` 和既有复合赋值运算。
  不允许数组取地址、指针算术、数组向指针转换表达式、数组整体赋值和元素自增表达式。
  C 对数组参数本身的指针调整仅用于经过检查的入口调用。
- 每个逻辑输入每边绑定一次。每边每个数组使用不同实际存储，禁止别名；
  候选程序无法读取原程序修改后的缓冲区。每次原生输入重新初始化所有副本。
- 全域安全与完整展开证明仍先于原生执行。越界路径不能被静默排除，也不能被误当作
  普通“不等价”的证据。局部只读表保持已有上限与检查。
- `scope.inputs` 是展开后的初始字段；`scope.declared_inputs` 是原数组约定；
  `scope.memory.entry_field_mapping` 和 `observation_order` 说明位置与含义。
- `traces.json` 的 `r_original/r_cached` 仍是实际返回值。新增
  `observations_original/observations_candidate` 向量，依次包含返回值与所有数组最终元素。
  搜索分裂、agent 原生筛查和求解器反例重放均比较完整向量；不能只读两个返回值字段。
- ESBMC 的 equal/different harness 使用同一完整观察表达式；不同是整个相等表达式的否定，
  表示至少一个被观察值不同。认证区域仍局限于声明的初始域和单次调用语义。

结果 JSON 保持 [v1 格式](../../docs/RESULT_FORMAT.md)，C 输入约定升级到 schema 2；
两者是不同的版本号。固定 transfer 实验仍需原 checkout。缓存不变量、初始化/保持义务
和任意调用序列的等价性不由本阶段自动获得。
