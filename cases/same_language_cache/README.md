# C→C 缓存等价验证：第一版

本案例通过现有 `tools/verify-equiv/verify_equiv.py` 的新 `--c-harness` 路由运行。
Python/C 路由、定制 GOTO 合并和原有实验保留。新路由接收**人工编写并审阅的组合 C harness**，尚不自动合并任意两个 C 文件，也不支持 C++ 对象模型。

## 本次已运行与待运行

2026-09-13，Windows x64 / MSVC：同一份 C 文件的原生回放编译成功，形式化入口通过 C 编译检查；20 项 Python 回归与原生回放测试通过。
空缓存输入 `1` 的实际回放为 `original=2, cached=0`。
这是代码执行证据。本机未发现 ESBMC 可执行文件，WSL 发行版列表为空，因此本次**尚未取得 ESBMC 证明或求解器反例**。
附件描述的另一次 ESBMC 8.5.0 实验不算本次结果。

## 在恢复的 Codespace 中运行

从仓库根目录运行，明确传入要使用的二进制：

```bash
python3 cases/same_language_cache/run_cache.py \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

也可以传原版 ESBMC 的绝对路径；结果会记录该路径及 `--version` 原始输出，不能据此声称执行了定制 GOTO 补丁。本 C 路由不需要那些跨语言扩展。
每个入口会保存 `result.json`、源码快照、版本日志、可达性探针日志及完整验证日志。默认目录为 `.verify-equiv-runs/same-language-cache/`。
缺失二进制、超时、意外性质失败或无法确认观察点可达时输出 `UNKNOWN`，整个案例套件返回 2。只有全部实际结果符合预期时套件才返回 0。

以下是**预期验收结果，不能当作本机已证明的结果**：

| 入口 | 预期 | 范围 |
|---|---|---|
| `good_sequence` | EQ | 空缓存起步，三次任意 uint32_t 调用 |
| `bad_sequence` | NEQ | 相同范围，错误 miss 返回值 |
| `good_induction` | EQ | 初始化及满足不变量的任意状态下一步返回等价、保持不变量 |
| `bad_induction` | NEQ | 任意不变量状态下无条件一步等价不成立 |
| `bad_conditional_step` | EQ | 人工条件下的一步等价及不变量保持 |
| `bad_empty_miss` | NEQ | 固定空缓存、x=1；便于原生回放同一见证 |

只执行一个入口：

```bash
python3 tools/verify-equiv/verify_equiv.py \
  --c-harness cases/same_language_cache/cache_demo.c \
  --entry good_induction \
  --scope-file cases/same_language_cache/scopes.json \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc
```

新路由的退出码继续为 `EQ=0 / NEQ=1 / UNKNOWN=2`。NEQ 只接受违反目标返回值等价断言的诊断；不变量、安全性质、展开失败归 UNKNOWN，并保留具体诊断。

## 原生回放和回归

```bash
mkdir -p .verify-equiv-runs/cache-native
cc -std=c11 -Wall -Wextra -DREPLAY cases/same_language_cache/cache_demo.c \
  -o .verify-equiv-runs/cache-native/cache-replay
.verify-equiv-runs/cache-native/cache-replay 1 1
# x=1 hit=0 original=2 cached=0 invariant=1；预期退出 1
.verify-equiv-runs/cache-native/cache-replay 0 7 7 8
# cached=8,8,9；预期退出 0
.verify-equiv-runs/cache-native/cache-replay 1 7 7 8
# cached=0,8,0；预期退出 1
.verify-equiv-runs/cache-native/cache-replay 1 4294967295 4294967295
# 两次返回 0；预期退出 0
CACHE_REPLAY="$PWD/.verify-equiv-runs/cache-native/cache-replay" \
  python3 -m unittest discover -s tools/verify-equiv -p test_verify_equiv.py -v
```

回放器第一个参数为 `0`（正确）或 `1`（错误），随后为任意多个十进制 uint32_t 输入。缓存只在进程开始时清空。退出 1 表示确实观察到返回值差异，退出 2 表示回放参数或内部不变量错误。这里的固定见证由案例提供；不是声称在本机从求解器自动提取了见证。

Windows 可在 Visual Studio x64 Native Tools 命令提示符中用：

```bat
cl /nologo /std:c11 /W4 /DREPLAY cases\same_language_cache\cache_demo.c /Fe:.verify-equiv-runs\cache-native\cache-replay.exe /Fo:.verify-equiv-runs\cache-native\cache-replay.obj
set CACHE_REPLAY=%CD%\.verify-equiv-runs\cache-native\cache-replay.exe
py -3 -m unittest discover -s tools/verify-equiv -p test_verify_equiv.py -v
```

没有设置 `CACHE_REPLAY` 时，5 项原生回放测试会明确跳过。测试中的模拟求解器输出只检查驱动的分类、异常处理及报告，不构成形式化证明。

## 模型及结论边界

- `original(x) = x + 1`，uint32_t 模 2^32 语义，允许 `UINT32_MAX + 1 == 0`。
- 原始实现无状态；优化实现拥有私有单条缓存。两侧使用同一个逻辑输入，原始调用不写状态，缓存跨调用保留。
- 观察每次返回值；不观察私有缓存布局、计时或调用次数。不含库调用、I/O、并发、分配和缓存被外部修改的情况。
- 人工不变量：`!cache.valid || cache.value == original(cache.key)`。
- `good_induction` 同时检查空缓存初始化和任意满足不变量的状态下一步保持、返回等价。仅在这些义务取得 EQ 后，结合数学归纳才能声称从空缓存开始任意有限序列的返回值等价。三次调用检查自身仅覆盖三次。
- 错误版的人工条件：`(cache.valid && cache.key == x) || x == UINT32_MAX`，在调用前解释。只报告该条件下的局部结论；没有自动发现条件。
- 不变量只约束缓存内容，不能单独保证返回值正确：错误版也会在 miss 后存入正确值。

`scopes.json` 是作者声明的模型说明，需与 C 源码一起审阅；驱动不会从文字生成或证明假设。C 路由不接受旧 `--domain` 参数：本案例的状态条件直接写在 harness 中，不能把 `key == x` 等关系默默降成一维区间。

## 集成与可达性检查

新适配器复用旧 oracle 的 `run`、结果分类、违反性质提取和反例赋值提取。一次正常验证之前，先定义 `VERIFY_EQUIV_REACHABILITY=1`，把观察断言替换成指定标记的失败断言。只有该探针确实失败在观察点，才继续正常验证，防止入口错误或互相矛盾的 assume 带来明显的空真。

这只是观察点存在可达路径的检查，不会证明作者建模了所有真实输入或每个声明的观察项。添加新 harness 时，应只让这个宏替换观察断言，不改变输入、状态或假设；仍需人工审阅源程序组合和观察定义。

默认安全检查及展开断言保留。验证命令开启 `--overflow-check`，未开启 `--unsigned-overflow-check`，以保留本案例刻意使用的无符号回绕语义。参数定义可核对 [ESBMC 官方源码](https://github.com/esbmc/esbmc/blob/master/src/esbmc/options.cpp)；实际兼容性仍以所运行二进制与日志为准。
