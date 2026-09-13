# 同语言阶段：仓库核对与第一版开发记录

核对日期：2026-09-13。用户指定的基线为 `recovery-current-work`，不是附件中尚待确认的 main。
开发分支为从该基线建立的 `codex/same-language-cache`。以下记录描述本次实现及验证范围；实际提交与远端同步状态以 Git 记录为准。

## 仓库身份

- 仓库：<https://github.com/Zehsong/faas-python-c-verification>。
- 开始开发时 HEAD：`5bb7479`（Save current project state），克隆后工作区干净。
- 远端 main 经 `git ls-remote origin refs/heads/main` 核对：`8a686a57e525b6b3676b3cf393330a186472a057`。
- 测试分支比该 main 多 4 个提交：`612166a`、`94b1042`、`04e2559`、`5bb7479`。
- 未找到仓库内 `AGENTS.md`、`PROJECT_HANDOFF.md` 或附件提到的缓存 zip。用户另附的交接文件已阅读，但历史实验结果未当作本次执行证据。

## 资产核对

| 项目 | 找到的依据 | 本次状态 |
|---|---|---|
| 关系 oracle | `tools/verify-equiv/verify_equiv.py`、shell 包装入口 | 已核对；原生 solver 回归待 Linux/ESBMC |
| 定制 ESBMC 参数 | `ESBMC_LOCAL_CHANGES.patch` 中 `equiv-py-target` / `equiv-c-target` | 补丁存在；本机无定制二进制可核对 |
| Python 初始化保留 | 补丁中 `__ESBMC_PY_MODULE_ENTRY`；oracle 的 preflight 检查 | 源码存在；未重跑 GOTO 合并 |
| 条件域搜索 | `tools/find-cond-equiv/find_cond_equiv.py` | 区间递归划分存在，NEQ 非单点继续拆分、UNKNOWN 单独保留 |
| 结构状态 | `cases/ec2_instance_no_public_ip/`、`tools/faas-model/` | 文件存在；未重跑 128 状态实验 |
| 旧成功/变异案例 | `experiments/relational_regression.json` 中 helper/loop/list 共 6 例 | 找到输入与预期；未在本机执行定制 ESBMC |
| 纯 C Adler32 | `experiments/library_alignment/zlib/verify/slice_vs_zlib.c`、`sliced.c` | 找到原始 vs 特化 harness；缺少依赖内容，未复现 |
| wrapper 契约 | 同目录 `wrapper_contract.c` | 找到代码；未复现 |
| zlib 固定版本 | gitlink `third_party/zlib-v1.3` → `09155eaa2f9270dc4ed1fa13e2b4b2613e6e4851` | gitlink 存在，但无 `.gitmodules`，目录内容未随普通克隆恢复 |
| 另一 gitlink | `RealFaaS/aws-opensource-mailserver` → `5705ddf119be0f02391ae2c98f3a2304a0bb7c1b` | 同样无恢复 URL 配置 |
| 旧版本记录 | `experiments/esbmc_python_c_poc/inspect/esbmc_version.txt` | 历史日志记载 8.4.0 Linux；不能确定当前定制二进制版本 |

main 没有测试分支中随后保存的 ESBMC 补丁提交。因此今后的恢复与开发应以用户指定的测试分支为准。尚不能从仓库补丁推定外部 `/workspaces/esbmc-current` 工作区已完全同步。

本地运行 `git submodule status` 还遇到 Git for Windows 辅助脚本找不到 `basename/sed` 的环境问题；上述 gitlink 核对使用 `git ls-files --stage` 完成，不依赖失败的子模块命令。

## 实际修改

1. 在现有 oracle 增加 `--c-harness` 路由，适配器为 `tools/verify-equiv/verify_c_harness.py`。复用进程调用、三值分类、违反性质提取与反例赋值提取，保持旧 Python/C 路由。
2. 添加原始、正确缓存、错误缓存的 C 实现和 6 个验证入口；状态跨请求保留，初始化与归纳步明确，模型说明随入口保存。
3. 分类器改为只接受实际 `Violated property` 诊断中的目标标记；日志其他位置的标记不能把安全失败变成 NEQ。超时、矛盾状态和进程状态冲突保持 UNKNOWN。
4. 修复旧 `--domain` 的报告：已注入 `[0,1]` 时不再打印整个 int32 域。输入约束的注入位置仍在两侧执行之前。
5. 处理启动子进程失败并保存日志；新 C 路由增加观察点可达性探针、源码摘要与快照、版本输出、JSON 范围报告，以及旧日志清理。

新路由复用 oracle，但不调用定制的跨语言 GOTO 合并逻辑。因此以后即使在原版 ESBMC 上成功，也只说明新 C 路径成功，不能冒充定制补丁已回归。

## 当前验证证据

- MSVC 14.50.35717 / x64：使用 `/std:c11 /W4` 编译 replay；形式化部分使用 `/c` 编译，均成功且无警告。
- 同一源码原生执行：正确序列 `7,7,8` 返回 `8,8,9`；错误序列返回 `0,8,0`。
- 固定反例：空缓存 `x=1`，原始返回 `2`，错误版返回 `0`，缓存内容仍满足不变量。
- `UINT32_MAX` 的回绕例外原生执行通过。
- 回归包含分类、误判防护、可达性探针、超时与进程失败、实际 domain 报告、状态持续性、回绕及错误输入。模拟 solver 输出仅测试驱动，不算证明。
- 当前 Windows 环境无可用 ESBMC，WSL 已安装发行版列表为空。本次没有重跑附件提到的形式化证明、旧 Python/C solver 回归或 Adler32 证明。缓存套件在缺失默认二进制时应报告全部 UNKNOWN。

原生回放及测试记录见 `docs/validation/same-language-cache/`。操作命令、预期结果和精确范围见 `cases/same_language_cache/README.md`。

## 留待实际 Linux 环境核实的事项

- 明确实际 ESBMC 路径、版本、源码 commit 与工作区补丁，再执行新缓存套件及旧 `experiments/relational_regression.json`。新套件有失败时保留原始日志，不把 UNKNOWN 当成 NEQ。
- 恢复 zlib 的固定 commit 内容后，重新执行纯 C Adler32 harness；本次未修改 gitlink 或猜测 mailserver 的来源 URL。
- 旧 `export_goto` 仍接受“非空输出文件存在”，并没有完整验证特殊返回码或产物身份。这是原有风险，不能从本次 C 路由测试推断其已修复。
- 一维区间搜索仍只支持旧 Python/C CLI，尚未适配状态关系。缓存条件是人工提供并待 solver 验证，不是自动发现。
- Pattern/sketch 表示、性能优化生成、真实库副作用、C++、别名及并发均未在此最小实现中解决。
