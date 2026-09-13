# 从 Agentic Concolic Execution 到条件等价 finder

本实现借鉴 Luo 等人的 [Agentic Concolic Execution（IEEE S&P 2026）](https://srg.doc.ic.ac.uk/publications/26-concollmic-sp.html)，主要对应论文 Figure 2、§3.1–3.3 的具体执行、候选约束和反馈循环。

论文 §5 明确讨论：LLM 推理存在不可靠性，其 concolic 方法不能直接用于程序验证。因此这里采用的边界是：**真实轨迹和 agent 建议指导搜索，ESBMC 检查未插桩 C 程序上的完整候选区域。** 测试通过、自然语言总结和 coverage 提升都不赋予 EQ。

## 已实现什么

- 新入口：`python3 tools/find-cond-equiv/find_cond_equiv.py --cache`。原 Python/C 区间 CLI 保留。
- 缓存族的一步模型：uint32_t 输入、私有单条缓存、人工不变量、初始化与保持义务。四个变体共享同一份 `cache_model.h`。
- 原生 `cache_probe.c` 记录实际 hit/miss、输入状态、返回值和更新后状态。初始样本来自类型边界及普通值；样本的 equal/unequal 标签来自 C 执行。
- 有限谓词划分：原始词汇为 `valid`、`x == key`，以及 x/key/value 分别与 0、1、UINT32_MAX 的比较。轨迹信息增益决定划分顺序，反例可以补充新的输入常量。
- 可选 `--hypotheses` 接受 agent/人工建议的谓词和输入。语法限定为调用前字段的比较；不允许函数调用、输出比较、赋值或代码。所有输入重新执行，建议不能改变合法域和不变量。
- 每个搜索区域先查询可满足性，再检查普遍等价；必要时另查普遍不等价。两个性质都有反例的区域才作为 MIXED 继续划分。
- 已证明区域做纯布尔逻辑合并，再独立检查最终条件与其补集。

这是可复现的 **trace-guided 基线**。没有接入 LLM API，没有复现论文的自动任意语言插桩、自然语言 symbolization 或自主多 agent 调度。这里的分区可满足性查询可以产生跨分支的新输入，但不是完整的逐路径前缀翻转 concolic 引擎。后续 agent 可读取每次运行的 `agent-context.json`，提出新假设后再次运行。

## 正确性边界

固定域 D 和人工状态关系 I 下，对区域 R 分别提出以下义务：

| 查询 | 实际性质 | 解释 |
|---|---|---|
| feasible | 在 D∧I∧R 下断言 false | 指定断言被反驳表示区域可满足；证明成功表示 EMPTY |
| equal | 所有 D∧I∧R 下返回相同，且调用后不变量成立 | 证明成功才记录 EQ 区域 |
| different | 所有 D∧I∧R 下返回不同，且调用后不变量成立 | 证明成功才记录 ALL_NEQ 区域 |
| initialization | 空缓存满足 I | 独立检查模型的初始化 |
| preservation | D∧I 下一步保持 I | 独立检查状态维护 |

equal 查询被反驳只表示 **存在不等输入**。必须独立证明 different，才能把整个区域标成 ALL_NEQ。different 被反驳则说明 **存在相等输入**。日志只把请求的断言标记识别成 REFUTED；其他安全或不变量失败、超时和进程错误保持 UNKNOWN。

若能从 solver 日志解析完整的调用前状态，就通过实际 C 重新执行；返回关系和目标谓词区域必须吻合。无法解析的反例仍保留原始正式日志，并明确标记未完成原生回放。搜索正确性不依赖成功解析每个反例。

最后对发现的 φ 独立检查：

```text
D ∧ I ∧ φ  => 返回相等且不变量保持
D ∧ I ∧ ¬φ => 返回不等且不变量保持
```

两项都 PROVED 才报告 `EXACT`，表示 **这个模型的一步返回等价域** 已完整刻画。仅有部分已证区域时报告 `PARTIAL`，未知范围单独保留。没有有用已证条件时为 `UNKNOWN`。预算耗尽不能升级为成功。

`EXACT` 不意味着整个项目、任意依赖库或任意调用序列已经等价。对错误缓存，φ 在每次调用前解释；初始不变量成立不会让后续所有调用自动满足 φ。本实现不产生部署 guard/fallback。

## Sketch 的当前含义

当前的 cache-family adapter 是一个可运行的局部验证方法原型：共享状态映射、初始化/保持义务、返回观察定义和候选词汇；通过切换 candidate 函数复用于不同变体。

它仍由人工建模，没有自动识别 pattern、提取不变量、推断库契约或泛化参数化定理。搜索器自动组合并验证条件；词汇语法、状态关系和初始种子策略是人工设计的。不能将它描述为自动生成任意 sketch 的系统。

搜索实现只读取 `cache_model.h` 和 `cache_probe.c`，不读取旧 `bad_conditional_step` 或 `scopes.json` 中的答案。最终验收公式仅位于独立的 `run_finder_checks.py`，在搜索完成后才用于检查，不提供给搜索过程。

## Codespace 一键运行

在项目目录，确认当前是 `codex/same-language-cache`，工作区干净后拉取：

```bash
git pull --ff-only origin codex/same-language-cache
bash cases/same_language_cache/test_finder.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

依赖为 Python 3.10+、C11 编译器和支持 Z3 的 ESBMC；不需要 Python z3 包、LLM API key 或 ConcoLLMic 安装。默认编译器是 `cc`，可用 `CC=gcc` 或 `CC=clang` 指定单个可执行程序。脚本启用 `set -euo pipefail`，测试失败或证明不完整会停止并返回非零。

脚本顺序：20 项旧测试（包含实际 native replay）、20 项新测试、原先 6 个缓存验证入口，以及 5 个条件搜索验收案例。**新增 finder 的 ESBMC 验收尚待在用户 Codespace 运行；下表是预期，不是本次 Windows 上已取得的证明。**

| 变体/状态域 | 预期等价条件（允许逻辑等价的其他写法） |
|---|---|
| good / invariant | true |
| bad_miss / invariant | hit ∨ x == UINT32_MAX |
| bad_hit / invariant | ¬hit ∨ x == UINT32_MAX |
| bad_miss_two / invariant | hit ∨ x == 1 |
| bad_miss / empty | x == UINT32_MAX |

其中 `hit = valid && key == x`。每个条件都先自动搜索并检查充分性、补集，再由独立 ESBMC 查询检查与验收公式一致。最终预期为 `FINDER ACCEPTANCE: 5/5 passed`。

若还要重跑原 Python/C 的 6 个回归，使用之前的命令；这个旧套件仍使用历史固定目录：

```bash
python3 tools/verify-equiv/run_suite.py experiments/relational_regression.json
```

## 单独运行与预算

```bash
python3 tools/find-cond-equiv/find_cond_equiv.py --cache \
  --variant bad_miss --state-mode invariant \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --timeout 30 --max-seconds 300 --max-queries 96 \
  --workdir .verify-equiv-runs/my-finder
```

`--timeout` 是每条属性查询的秒数；`--max-seconds` 是单次 finder 的时间预算；`--max-queries` 包含初始化、保持、可满足性、性质与最终检查。默认保留两次查询给最终条件和补集。编译与原生回放也受时间预算约束。`EXACT` 返回 0，`PARTIAL/UNKNOWN` 返回 2；这些是搜索报告状态，旧 oracle 的 EQ=0/NEQ=1/UNKNOWN=2 不变。

每次运行创建独立子目录，保存源码快照、编译命令、版本、逐查询完整命令与日志、条件划分历史、原生输入/输出回放和源文件 SHA256。父目录的 `result.json` 指向最新报告，旧运行目录保留。

```bash
python3 -m json.tool .verify-equiv-runs/my-finder/result.json
python3 -m json.tool .verify-equiv-runs/finder-acceptance/results.json
```

## Agent 接口

先运行一次，再将输出目录的 `agent-context.json` 交给 agent。它包含固定模型、当前轨迹、未解决区域及已有证据。可以提供如下建议文件：

```json
{
  "predicates": ["x == 42", "x <= key"],
  "seeds": [{"x": 42, "valid": 0, "key": 7, "value": 8}]
}
```

使用 `--hypotheses suggestions.json` 重新运行。谓词允许 `valid`，或 x/key/value 与这些字段、uint32_t 常量之间的 `== != < <= > >=` 比较。建议种子不满足固定域时不纳入探索。当前为批次重跑接口，不会自动调用外部模型或在运行中等待 agent。

## 已在本地实际检查的内容

Windows/MSVC 下：20 项旧测试及 20 项新测试通过，包含四个变体的真实 C 轨迹、插桩/未插桩输出与后状态对照、所有生成义务的 C 编译检查，以及小型有限状态集合上的搜索/合并逻辑检查。

有限状态测试只检验算法实现，不能替代 uint32_t 全域证明。当前主机缺少 ESBMC，新 finder 的缺失二进制路径保持 UNKNOWN；不能把旧缓存案例在用户 Codespace 上已通过的结果算作新 finder 已通过。

## 下一轮研究比较

可以在相同模型、谓词预算和 solver 预算下比较固定顺序划分、轨迹信息增益划分、agent 建议谓词三种设置；记录 EQ/ALL_NEQ/UNKNOWN 区域、查询数、耗时与 native witness 回放比例。再增加未参与模板构建的缓存/计算复用实例，测量修改模型和新增义务的人工成本。当前没有声称已证明优于原有方法。
