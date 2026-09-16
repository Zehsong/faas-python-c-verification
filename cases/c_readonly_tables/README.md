# M3 第一步：通用 C 接口中的只读表

现在可以把“质数计算”和“查表”的两个 C 文件直接交给现有通用入口，通过 JSON
约定指定输入域和函数，不需要新增 Python adapter 或手写 harness。
这一步扩展 C 前端的接纳范围，复用现有条件搜索、ESBMC 认证、agent 文件协议和 M2 报告。

目前接纳的是**函数内、固定长度、完整字面量初始化的只读数组**。数组参数、输出数组、
可变数组、全局表、指针和缓存状态尚未接入；这不是整个 M3 已完成。

## 在 Codespace 验收

继续使用已有的修改版 ESBMC，不安装替代版本：

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
bash cases/c_readonly_tables/test_tables.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

目标输出：`C READONLY TABLE ACCEPTANCE: 9/9 passed`。脚本另存
`c-readonly-tables-时间-后缀.tar.gz`，其中有原始 C/JSON、生成代码、求解器日志、报告、
查询及重放记录。失败结果也保留。2026-09-16 用户已报告 **9/9 通过**，
包含 agent 对 0..31 域内 `n != 9` 的认证；[输出与证据路径](../../docs/validation/c-readonly-tables/user-reported-results.md)。
原始归档尚未独立审阅；
[本地验证](../../docs/validation/c-readonly-tables/README.md)不替代 ESBMC 证明。

| 检查 | 输入域 | 期望结果 |
|---|---|---|
| full_31 | n = 0..31 | 完整表与计算：EXACT，true |
| fallback_63 | n = 0..63 | 表范围外继续计算：EXACT，true |
| truncated_63 | n = 0..63 | 范围外返回 false：EXACT，排除 37、41、43、47、53、59、61 |
| mutant_31 | n = 0..31 | 表把 9 错标为质数：EXACT，n != 9 |
| unsafe_index | n = 0..63 | 无保护读取 32 元素表：UNKNOWN，真实安全检查失败，无原生输入执行 |
| short_unwind | n = 0..63 | 展开上限 2：UNKNOWN，展开不足，无原生输入执行 |
| readonly_write | n = 0..31 | 写入只读表：UNSUPPORTED_INPUT，无求解/原生执行 |
| missing-solver | n = 0..31 | UNKNOWN，SOLVER_NOT_FOUND |
| agent-table | n = 0..31 | 已知候选 n != 9 经共享后端认证为 EXACT |

前四项自动搜索完成后，验收脚本另调用后端检查实际条件是否与预期公式等价。
预期公式不作为搜索候选或种子。额外公式检查的查询单独记录，不计入 finder 的查询数。
agent 项使用脚本提供的已知答案，仅检查协议接入，不是自主发现能力的实验。
这些是已知质数案例的通用接口迁移，不能据此声称盲测发现或性能提升。

## 单独运行一对程序

```bash
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract cases/c_readonly_tables/truncated_63.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --max-queries 160 --max-seconds 600
```

这个 JSON 绑定 [prime_compute.c](prime_compute.c) 与
[prime_truncated.c](prime_truncated.c)，结构仍是 `schema: 1`、标量输入与
`observations: ["return"]`。没有数组输入或输出。对任一自己的受支持程序，仍按
[通用接入说明](../../docs/C_SCALAR_TOOL.md)绑定 C 文件、入口、参数和域。

局部表也可以用于非质数程序，例如：

```c
#include <stdint.h>
uint32_t lookup(uint32_t n) {
    const uint32_t values[4u] = {9u, 7u, 5u, 3u};
    return values[n];
}
```

这个例子需要把输入域限制在 0..3，或在 C 程序中加入正确的边界处理。
工具不会自动补条件把越界输入排除掉；它要求**整个声明输入域先通过安全与展开检查**。
因此，越界的程序即使在部分输入上正常，也不会被本阶段作为条件等价发现对象继续执行。

## 接纳规则与证明范围

- 表必须是自动存储期、单维、`const uint32_t` 或 `const bool`；每个源文件所有表的
  声明元素数总和最多 256。长度必须是 1..256 的十进制字面量，可带 `u` 后缀。
- 每个元素必须显式初始化：uint32_t 使用无符号整数字面量，bool 使用 true/false。
  不支持省略元素、指定初始化器、计算型初始化、可变长度、static 或 volatile 表。
- 只允许 `table[index]` 读取，index 必须为 uint32_t 表达式。不能写表、取地址、
  传表给函数或通过强制转换/逻辑表达式触发数组向指针转换。辅助函数可有自己的局部表。
- 原函数体保留给原生编译器和 ESBMC。两边函数独立命名，各有局部存储，
  不引入共享可变数组，也不把表内容当作待搜索的输入。
- 保留安全检查、展开断言和禁用切片设置。整个输入域安全性未证明时，没有原生采样或重放。
  真实索引越界及展开不足必须产生 UNKNOWN，不能作为普通“不等价”的反例。
- 报告在 `scope.memory` 中列出两边表的函数、名称、类型和长度；观察仍为单次返回值。
  表的内容由源文件快照/哈希保留。agent 会话身份绑定源文件与前端；升级后开启新会话。

保留旧 prime 专用 adapter 及冻结 transfer 实验，不把新运行和旧查询数直接混为一次实验。
下一步才考虑有界数组输入/输出及可变状态，届时需要显式的独立内存副本和观察约定。
