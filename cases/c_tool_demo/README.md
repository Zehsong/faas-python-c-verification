# C 工具统一演示入口

一条命令运行标量、计算与查表、数组和两类私有缓存，生成可下载浏览的中文总览。
本阶段复用现有证明引擎与案例，改善使用和展示方式；不新增语言语义或搜索策略。

## 运行

在仓库根目录，使用已有修改版 ESBMC：

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
ESBMC=/workspaces/esbmc-current/build/src/esbmc/esbmc
bash cases/c_tool_demo/run_demo.sh "$ESBMC"
```

预期：`C TOOL DEMO: READY (8/8 checks; engine unchanged=True)`。
随后打印 `Open overview:` 和独立的 `c-tool-demo-*.tar.gz` 路径。
打开 **Open overview 指向的 README.md**，即可看到实际认证条件、域、观察和报告链接。
下载归档并解压后，打开 `results/demo-*/README.md`；本页的链接为相对路径。

| 演示 | 检查目标 |
|---|---|
| scalar-all | 标量全域等价，EXACT true |
| prime-lookup | 质数计算与错误查表，EXACT 条件区域 |
| array-swap | 交换数组与保持原样，比较全部最终元素 |
| cache-miss | 返回值条件等价，并通过初始化和保持义务 |
| config-cache | 配置变化下的条件等价，历史缓存配置显式建模 |
| no-equal-inputs | 数组相同但返回不同，EXACT false，输入域非空 |
| budget-limited | 实际用尽四次查询，保留 UNKNOWN 与具体诊断 |
| 数组反例 | 求解器反例已被原生重放：返回值相同，数组最终内容不同 |

总览里的条件来自本次 verification-result.json，演示不把预期公式传给搜索器。
没有合适的已重放反例，或者 UNKNOWN 原因是缺少求解器而非指定预算控制时，不能 READY。
本阶段没有 agent 提案或 API 调用。

## 证据与限制

每项保存输入副本、运行请求、JSON/Markdown 报告和原始查询日志。泛型 C 的源文件名在
副本中规范为 original.c/candidate.c，函数体字节保持不变。两个缓存案例实际使用复制的
模型与 sketch；invocation.json 会说明独立缓存 CLI 使用仓库绑定，而本演示使用副本绑定。

READY 还要求引擎、源案例、演示脚本、输入副本以及编译器/ESBMC 文件身份在运行前后相同。
这不是整个操作系统或所有动态依赖的封闭性检查。归档保留实际 Git 状态，不声称工作区
必然干净；底层日志里的绝对路径仍指向原运行机器。

案例均来自已开发的集成测试，不是独立盲测，也不用于宣称 agent 发现能力或性能提升。
M3 基础验收已有用户报告的数组 10/10 与缓存 14/14；本统一演示也已收到用户报告的 **READY 8/8**
（[输出与证据路径](../../docs/validation/c-tool-demo/user-reported-results.md)，原始归档尚未独立审阅）。
全新 Linux 环境复现、独立新案例验证和原始历史归档审阅仍是后续发布门槛。

继续接入自己的程序：[C 工具快速使用](../../docs/C_TOOL_QUICKSTART.md)。
[本地演示检查记录](../../docs/validation/c-tool-demo/README.md)。

需要排除当前工作目录和 Python 环境的影响：[独立源码与 Python 环境复现](../../docs/C_TOOL_REPRODUCTION.md)。
