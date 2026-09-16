# C 条件等价工具：快速使用

当前工具接受两份**受支持的 C 函数**与一个明确的输入约定，自动生成 harness、寻找条件，
并用 ESBMC 认证条件。读取现有项目时，先从需要比较的一对函数入手。

## 看一次完整演示

在现有 Codespace 的仓库目录运行：

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
python3 -m pip install -r tools/find-cond-equiv/requirements.txt
ESBMC=/workspaces/esbmc-current/build/src/esbmc/esbmc
bash cases/c_tool_demo/run_demo.sh "$ESBMC"
```

打开输出中 `Open overview:` 指向的 README.md。它汇总标量、质数查表、数组和缓存的
实际结果，并链接输入副本、证明报告与已重放反例。脚本自动保存独立证据归档。
使用已有修改版 ESBMC；新环境安装参见[迁移指南](LINUX_IDE_MIGRATION.md)。

## 放入自己的两个函数

通用接口需要：原程序 C 文件、候选程序 C 文件、声明入口和输入域的 JSON 约定。
下面在一个新目录复制数组例子，便于修改而不覆盖仓库案例：

```bash
mkdir -p .verify-equiv-runs
PAIR_DIR=$(mktemp -d "$PWD/.verify-equiv-runs/my-pair-XXXXXX")
cp cases/c_bounded_arrays/swap.c cases/c_bounded_arrays/identity.c \
   cases/c_bounded_arrays/swap.json "$PAIR_DIR/"
printf 'Editable pair: %s\n' "$PAIR_DIR"

python3 tools/find-cond-equiv/find_c_conditions.py \
  --contract "$PAIR_DIR/swap.json" \
  --esbmc "$ESBMC" \
  --workdir "$PAIR_DIR/results"
```

替换两个函数体，并相应修改约定中的 source、entry、args、输入类型/范围、观察和 unwind。
普通受支持的新例子不需写 Python adapter，也不需手写关系 harness。
条件中的 a_0/a_1 表示调用前的元素值。

| 接口 | 当前支持 | 说明 |
|---|---|---|
| schema 1 | uint32_t/bool 标量输入和返回，局部只读表 | [完整约定](C_SCALAR_TOOL.md) |
| schema 2 | 固定长度数组与标量输入，标量返回，观察全部数组最终元素 | [数组约定](../cases/c_bounded_arrays/README.md) |
| schema 3 | 类型默认完整域、初始字段间的关系及布尔组合约束；可搭配现有固定数组 | [新契约和验收](../cases/c_input_domains/README.md)，正式验收待运行 |
| 私有缓存 | 已有两个经过检查的 adapter，显式 invariant 与状态义务 | [缓存范围](../cases/cache_state/README.md)；不是任意状态 C 输入接口 |

通用接口合计最多四个初始标量值，数组元素计入总数；数组长度 1..4，无别名、任意指针、
堆或全局状态。循环须在声明的展开界限内完成。未支持的语义会被拒绝或保留 UNKNOWN。
工具不会默默排除越界等不安全输入以宣称等价。

## 读结果

`report.md` 给出可读结论；`verification-result.json` 保存机器可读结果。
同目录还保留原始查询、harness、求解器日志、原生轨迹与工具身份。

- **EXACT**：在声明域内，条件精确描述等价输入；true 表示整个域，false 表示非空域内无等价输入。
- **PARTIAL**：条件内已证明等价，条件外尚未完全分类。
- **UNKNOWN**：没有认证条件；查看预算、展开、安全性、依赖或支持范围等诊断。
- **EMPTY_DOMAIN**：没有可用输入，不把空域上的真命题当作等价结果。

每次先核对输入域、观察、状态假设与证明界限。数组要求返回值和全部最终元素一致；
私有缓存的公共观察是返回值，另证明 invariant。单次调用的条件不自动成为任意序列证书。

目前的演示基于已知集成案例，用户已报告 READY 8/8。
[独立源码与 Python 环境复现](C_TOOL_REPRODUCTION.md)提供固定提交、新 venv 和依赖证据，
该复现已获用户回传 READY；外部来源案例也已回传必要项 5/5。全新主机复现与独立盲测仍未完成。
[当前 C 原型阶段总结](C_TOOL_MILESTONE.md)列出已具备的能力、规模实验结果和研究边界。
[结果格式](RESULT_FORMAT.md) · [agent 提案接口](AGENT_WORKFLOW.md) · [最新状态](PROJECT_STATUS.md)。
