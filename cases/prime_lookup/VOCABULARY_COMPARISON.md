# 有限域内的谓词表达能力对照

上一轮用户报告：截断查表在 0..63 为 86 次 finder 查询、17.742 秒，
在 0..127 为 204 次、43.174 秒；扩域验收 8/8 通过。原耗时包含独立
验收，属于单次观察，不用于直接宣称新方法加速。

本实验同时重跑两组，不复用上轮时间作为对照。

| 因素 | baseline | modulo |
|---|---|---|
| 初始谓词 | x==0、x==1、x<=31 | 同左，加 x%d==0，d 为全部整数 2..16 |
| 初始样本 | 固定边界/普通输入 | 完全相同，记录并检查摘要 |
| 模型与输入域 | 同一 C 源码，0..63 和 0..127 | 相同 |
| 版本 | fallback、truncated、mutant | 相同 |
| 总谓词预算 | 96 | 96（初始占用 18 个而非 3 个） |
| 查询与时间预算 | 512 次、每次 30 秒、每案例 600 秒 | 相同 |
| 后续常量细化、划分选择 | 原算法 | 相同 |
| 最终条件压缩、充分性/补集与独立验收 | 原流程 | 相同 |

取模除数包含合数，不通过 sieve 挑选。候选词汇是人工提供的通用整除
模板族；不会把“合数”等价条件直接提供给搜索器。语法只允许固定除数
2..16、合法余数、输入 x，不接受任意代码、零除数或输出值谓词。
解析接口也支持非零余数，但本次初始词汇只添加余数为零的候选。

后续 ESBMC 反例可以不同，因为搜索路径改变了。这不是保持完全相同的
后续样本实验，而是保持初始样本和搜索策略不变的词汇对照。
效果不能脱离当前信息增益划分策略解释；这不是“取模一定更快”的证明。

## 运行

```bash
bash cases/prime_lookup/test_vocabulary.sh /workspaces/esbmc-current/build/src/esbmc/esbmc
```

先跑旧 cache/sketch 回归及本地/native 测试，然后执行 2 个域 × 3 个
版本 × 2 种词汇 × 2 轮 = **24 次 finder 运行**。第二轮交换两种词汇
的先后顺序；全部串行，避免同时抢占求解器资源。可通过直接运行
`compare_vocabularies.py --repeats N` 改轮数，不应只挑有利的一轮报告。

正确性目标为：

```text
VOCABULARY COMPARISON: 24/24 certified; paired inputs match=True
```

这行只表示两组都通过精确性及独立规格检查，**不表示 modulo 更快**。
UNKNOWN、PARTIAL、失败运行也写入结果；时间汇总包含这些运行，记录
每组 certified 数量，不把少量成功运行的速度当作整组速度。

## 结果与测量

`results.csv` / `results.json` 保存每次运行，`summary.json` 保存中位数，
`experiment.json` 保存提交、验证器摘要、预算和配对检查结果。字段包括：

- `queries_used`：finder 查询数，不含独立规格验收查询。
- `finder_seconds`：整个 finder 的耗时，包含 native 编译/回放和最终证明。
- `elapsed_seconds`：再加上独立规格验收；对应上一轮 elapsed 的定义。
- `raw_condition_chars`：原始已证区域并集表示的字符数。
- `published_condition_chars`：有限域压缩后对外条件的字符数。
- 谓词数量、收集轨迹数、未解决区域数、状态、完整 artifacts 路径。

字符数是可读性代理，不是逻辑最小性度量。压缩可能把取模结果也转成
同一个排除集合，所以两组发布条件一样长不代表搜索过程一样。

归档名为 `$HOME/equiv-evidence/vocabulary-comparison-*.tar.gz`。下载后
保留全部记录。两轮只是探索性测量，不能据此给出统计显著性或跨项目
性能结论。研究仍是多语言中的同语言等价性，当前只比较 C 后端的实例。

## 已完成的本地验证

Windows/MSVC **69 项测试通过**，包括原 63 项与新增 6 项。新增检查
覆盖语法/除数边界、配对输入和预算、取模条件压缩、轮序交换、UNKNOWN
保留，以及真实 C 取模表达式对 0..255 和 UINT32_MAX 的求值。三个
真实 C 候选也在有限测试域上验证了取模词汇搜索的结果。

本地未运行 ESBMC。后续用户在 Codespace 反馈 **24/24 certified，paired
inputs match=True**；测量、来源和原始证据位置见[用户结果记录](../../docs/validation/vocabulary-comparison/user-reported-results.md)。该记录是用户日志转录，不是本地重新运行的正式证明。
