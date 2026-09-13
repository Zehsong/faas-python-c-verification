# 质数计算与查表：第一阶段

研究目标是多种语言中的**同语言条件等价性**。本例继续使用当前 C 后端，
并不把研究限制为 C→C，也不涉及跨语言验证。接口为 `is_prime(x)`，
观察布尔返回值；“求第 n 个质数”是不同接口，未在本阶段实现。

## 模型与变体

`prime_model.h` 中原算法使用试除法判断质数；`d <= x / d` 避免平方乘法
溢出。查表覆盖 0..31，所有访问均先检查范围。

| 变体 | 实现 | 0..63 内的预期等价条件 |
|---|---|---|
| fallback | 表内查表，表外计算 | true |
| truncated | 表内查表，表外返回 false | x 不属于 {37,41,43,47,53,59,61} |
| mutant | 表内 9 的条目错误地为 true，表外计算 | x != 9 |

表外合数如 49 对 truncated 仍然等价。因此正确的答案不只是 `x <= 31`。
验收另外包含 truncated 的 0..31 子域（全等价）和 37..37 子域（无等价输入）。

这里的表是编译期固定数据，**没有可变缓存状态**。不实例化缓存初始化或
不变量义务；`state_obligations` 报告为空，scope/manifest 解释其不适用。
继承的进程调用、反例解析/回放、区域分类及最终充分性/补集检查仍然复用。
轨迹中的 `r_cached` 是兼容既有搜索引擎的候选返回值字段，不表示存在缓存。

## 自动发现与证据边界

finder 初始谓词只有 `x == 0`、`x == 1`、`x <= 31`，初始样本为少量边界
和普通输入。native C 提供结果标签，ESBMC 反例可增加 `x == 常量` 谓词。
finder 不导入验收文件、不调用 sieve，也不接收上述预期集合。

完成搜索后，独立验收器才使用筛法计算有限域的规格，并生成新的 ESBMC
断言检查发现条件与规格条件是否一致。原 C 算法使用试除法，native 测试
也用独立筛法检查 0..255 上原算法及三个候选的输出。

`EXACT` 仅表示声明的输入域内条件充分且补集均不等价。第一轮为 0..63；
CLI 允许 0..255 内的子区间，超出会拒绝，不默默缩小用户输入域。
循环展开上限取 `floor(sqrt(hi)) + 2`，保留 unwinding、数组越界等检查。
相关检查失败、超时或预算不足保留 UNKNOWN/PARTIAL，不记作证明成功。

当前表示可能退化为有限输入点的排除或枚举，尚未发现通用“合数”语义谓词。
这一步检验循环、只读数组和非连续条件，不宣称能在完整 uint32 域上归纳
质数规律、自动抽取任意源码或证明查表一定带来性能收益。

## Codespace

```bash
bash cases/prime_lookup/test_prime.sh /workspaces/esbmc-current/build/src/esbmc/esbmc
```

脚本先执行本地/native 测试及原有共享引擎回归，再运行新案例。预期输出：

```text
FINDER ACCEPTANCE: 5/5 passed
CONFIG CACHE ACCEPTANCE: 3/3 passed
SKETCH CONTROLS: 8/8 passed
PRIME ACCEPTANCE: 5/5 passed
```

以上是当前提交的验收目标，不是本地已完成的 ESBMC 证明。用户已反馈此前
cache/sketch 阶段 5/5、3/3、8/8 通过；新 prime 阶段正式验证待 Codespace。
本地 Windows/MSVC 共 **61 项测试通过**，其中新增 8 项；原有测试未跳过。

每组结果分别归档，prime 目录为 `.verify-equiv-runs/prime-stage/run-*`，
压缩包在 `$HOME/equiv-evidence/prime-lookup-*.tar.gz`。保留失败与 UNKNOWN
结果。每个案例默认 600 秒总预算、512 个查询，每次查询最多 30 秒。

单独重跑新验收（不重复旧回归）：

```bash
python3 cases/prime_lookup/run_checks.py --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

随后扩域实验应单独保存，例如：

```bash
python3 tools/find-cond-equiv/find_prime_conditions.py --variant truncated --domain 0:127 --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc --workdir .verify-equiv-runs/prime-0-127
```

先完成默认验收，再讨论扩域、谓词丰富程度、查询成本和第二种语言后端。
