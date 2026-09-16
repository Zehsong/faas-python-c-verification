# C 条件等价工具：从输入到报告

这份演示把已验收的 M1 标量 C 接口和 M2 结果报告串起来。输入是两个受支持的 C
函数和一个 JSON 约定，工具生成 harness、搜索条件并调用 ESBMC 认证，最后输出
可读报告、版本化 JSON 和原始证据。演示复用已知集成案例，不是新的盲测基准。

## 1. 在 Codespace 运行

在仓库根目录执行，继续使用现有的**修改版 ESBMC**。命令不会安装或替换它。
需要 Python 3.10+、原生 C11 编译器以及项目依赖。

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
bash cases/c_scalar_demo/run_demo.sh \
  /workspaces/esbmc-current/build/src/esbmc/esbmc
```

预期末尾为 `C SCALAR DEMO: READY (5/5 checks; tools unchanged=True)`，并打印：

- `Open overview:`：本次演示的总览 Markdown，可在编辑器预览。
- `Evidence directory:` 和 `Downloadable archive:`：独立证据目录与 `.tar.gz`。

每次运行创建新目录，保留失败结果；缺少求解器等问题会显示 `INCOMPLETE`。
`READY` 表示四种预期结果和一次反例重放均出现，不代表五个程序全域等价。
2026-09-16 用户已报告本演示 **READY，5/5 检查通过**，包含预算不足与反例重放检查。
[输出、证据路径与解释](../../docs/validation/c-demo/user-reported-results.md)；原始归档尚未独立审阅。

## 2. 展示顺序

| 示例 | 输入及观察 | 预期结果 |
|---|---|---|
| all-inputs | uint32_t n 全范围；奇偶函数返回值 | EXACT，全部等价 |
| conditional | x,y 各为 0..31；maximum 与 minimum 返回值 | EXACT，等价条件逻辑上为 x == y |
| no-equal-inputs | x,low,high 各为 0..31；区间检查函数与加一变体返回值 | EXACT，条件 false，域非空但没有等价输入 |
| budget-limited | 与 conditional 相同；查询预算设为 4 | UNKNOWN，QUERY_BUDGET_EXHAUSTED |

程序可能输出比 `x == y` 更长的等价公式；展示的是实际已认证公式，演示脚本不会
拿预期答案替换输出，也不会将答案作为候选条件传给搜索。

先打开总览，再点击 `conditional` 的报告：

1. 确认输入域、单次调用返回值观察和安全/展开要求。
2. 查看认证条件。充分性证明条件内相等；补集证明条件外不相等。
3. 回到总览查看反例输入和两个返回值，点击求解器日志与查询记录。
   这必须是后端实际重放过的相等性反例；解析或重放失败时不会补造。
4. 打开 `budget-limited`：UNKNOWN 表示没有认证条件，不能解释为不等价。

反例来自 `queries.json` 的 `native_replay`，后端在全域安全检查通过后已执行它。
单个反例只推翻“所有输入都相等”；区域的结论仍需要 ESBMC 的证明。
总览的链接相对归档目录，下载解压后可浏览；原始记录中的绝对路径保留原机器位置。

## 3. 拿两个自己的 C 函数试用

下面建立一个独立、可编辑的三文件例子。保留新目录，修改其 C 文件和约定即可；
不会改仓库中的测试样例。实际接入新函数前请核对[支持范围](../../docs/C_SCALAR_TOOL.md)。

```bash
mkdir -p .verify-equiv-runs/my-pairs
PAIR_DIR="$(mktemp -d "$PWD/.verify-equiv-runs/my-pairs/pair-XXXXXX")"
cp cases/c_scalar/maximum.c "$PAIR_DIR/original.c"
cp cases/c_scalar/minimum.c "$PAIR_DIR/candidate.c"
cat > "$PAIR_DIR/contract.json" <<'JSON'
{
  "schema": 1,
  "name": "my_pair",
  "original": {"source": "original.c", "entry": "choose", "args": ["x", "y"]},
  "candidate": {"source": "candidate.c", "entry": "choose", "args": ["x", "y"]},
  "inputs": {
    "x": {"type": "uint32_t", "min": 0, "max": 31},
    "y": {"type": "uint32_t", "min": 0, "max": 31}
  },
  "return_type": "uint32_t",
  "observations": ["return"],
  "unwind": 40
}
JSON
printf 'Edit these files: %s\n' "$PAIR_DIR"
```

这个例子中的两个程序分别是：

```c
/* original.c */
#include <stdint.h>
uint32_t choose(uint32_t a, uint32_t b) { return a > b ? a : b; }
```

```c
/* candidate.c */
#include <stdint.h>
uint32_t choose(uint32_t a, uint32_t b) { return a < b ? a : b; }
```

约定里的 `entry` 是函数名，`args` 将逻辑输入按顺序绑定到函数参数。
`min/max` 是包含端点的输入域；`observations` 声明比较返回值；`unwind` 指定展开上限，
工具仍会检查展开是否足够。约定决定证明的问题，不能为了得到好结果偷偷缩小域。

修改完成后在同一终端运行（换终端时先把 `PAIR_DIR` 设为上面打印的目录）：

```bash
PAIR_RUN="$(mktemp -d "$PAIR_DIR/run-XXXXXX")"
python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract "$PAIR_DIR/contract.json" \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --cc "${CC:-cc}" --workdir "$PAIR_RUN"
printf 'Read report: %s/report.md\n' "$PAIR_RUN"
```

返回码 0 表示 EXACT，2 表示其他结果，包括 PARTIAL/UNKNOWN；请查看报告。
这段单例命令不自动调用演示归档器：保留整个 `PAIR_DIR`，其中同时包含编辑输入和结果。

自动生成的材料在报告标出的运行目录内：

| 文件 | 用途 |
|---|---|
| report.md | 阅读条件、范围和诊断 |
| verification-result.json | 版本化结果，供其他程序读取 |
| inputs/bound_model.h | 两边函数绑定后的模型 |
| inputs/scalar_probe.c | 原生运行程序 |
| query-*/harness.c | 每次 ESBMC 查询的 harness |
| query-*/verify.log、result.json | 求解器日志和该次检查结果 |
| queries.json、replays.json、traces.json | 查询、实际重放与采样记录 |

启动失败时部分执行文件可能不存在，以报告诊断为准。
无需手写 harness，也无需新增 Python backend；目前通用接口支持 1..4 个
uint32_t/bool 输入、纯函数和单个标量返回值。最新前端另增加了[局部只读表](../c_readonly_tables/README.md)，
其独立验收已由用户报告 9/9 通过。[schema 2 有界数组接口](../c_bounded_arrays/README.md)
现已实现，另有待运行验收；任意指针和全局状态仍不支持。原有 prime/table 与 cache 专用适配器继续保留。完整含义见[结果格式](../../docs/RESULT_FORMAT.md)。

## 4. 保存演示证据

将终端打印的真实归档路径填入下面命令：

```bash
bash tools/prepare_evidence_download.sh \
  /home/codespace/equiv-evidence/c-scalar-demo-实际时间与后缀.tar.gz
```

在 Codespace 文件树找到打印的 `evidence-downloads/bundle-...` 目录，下载归档和
`SHA256SUMS`。总览及源码、结果、日志都在归档的 `results/demo-.../` 目录内。
归档内 `run_demo.py` 是执行脚本快照；重新运行仍需项目 checkout、依赖和修改版 ESBMC。

完成演示后，先检查报告是否足够清楚，再按[计划](../../docs/DEVELOPMENT_PLAN.md)进入
M3 有界数组/状态支持。此步骤不改变证明引擎或旧 transfer 实验的冻结版本。
