# 私有缓存状态：证明检查与公共报告

本阶段将已有的单项缓存和配置缓存接入统一的状态检查与验收流程。
两个案例继续使用经过检查的 C 模型和手写 invariant，没有开放任意状态代码输入。

现在运行顺序是：编译 probe → 证明初始化和当前入口模式下的状态保持 → 原生采样 →
搜索条件 → 认证充分性与补集。找不到求解器或任何必要状态义务未通过时，停止采样，
结果保留 UNKNOWN。agent 后续轮次只有在源文件、配置和工具身份未变时才恢复这些证明。

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache
ESBMC=/workspaces/esbmc-current/build/src/esbmc/esbmc
bash cases/cache_state/test_state.sh "$ESBMC"
```

目标输出：`CACHE STATE ACCEPTANCE: 14/14 passed; inputs/tools unchanged=True`。
脚本单独保存 `cache-state-*.tar.gz`，不覆盖数组或之前的缓存归档。
使用现有修改版 ESBMC；用户已报告 **14/14 passed; inputs/tools unchanged=True**；
[原始输出与证据路径](../../docs/validation/cache-state/user-reported-results.md)，归档尚未独立审阅。

## 14 项验收

每个缓存家族运行以下七项，两家族共 14 项。

| 检查 | 预期 |
|---|---|
| good，从任意满足 invariant 的状态开始 | EXACT true；初始化与保持分别 PROVED |
| 有缺陷版本，从 invariant 状态开始 | EXACT 条件区域，发现后再独立检查预期公式 |
| 有缺陷版本，从空缓存开始 | EXACT，范围只限空缓存入口 |
| 错误初始化 | initialization REFUTED；整体 UNKNOWN；零原生输入 |
| 返回值正确但破坏缓存值 | preservation REFUTED；整体 UNKNOWN；零原生输入 |
| 缺少求解器 | UNKNOWN，SOLVER_NOT_FOUND；零查询、零原生输入 |
| agent 恢复会话 | true 被原生反例否定且不增加查询；随后给定的正确条件认证为 EXACT |

脚本 agent 项只验证协议，不衡量自主发现能力。所有正式义务重新运行，不复用历史证书。
修改版模型、sketch、probe、生成 harness、查询记录和报告均保存到独立目录。
记录源文件、输入副本和编译器/ESBMC 的身份，结束时检查是否发生变化。

单项缓存 `bad_miss` 的预期区域为：

```text
invariant 入口：(valid && x == key) || x == 4294967295
empty 入口：x == 4294967295
```

配置缓存 `stale` 的预期区域为：

```text
invariant 入口：!valid || x != key || config == cached_config
empty 入口：true
```

这些答案只用于发现之后的额外验证。它们不进入自动搜索的初始谓词或样本标签。

## 状态与观察的含义

- 参考函数是纯函数；候选持有独立的私有 Cache。每个符号入口、每条原生输入都重新
  构造缓存。不同测试输入不会共享上一次调用修改后的存储。
- 单项缓存的状态为 valid/key/value；配置缓存另有 cached_config。
  config 是当前调用的环境输入，调用期间不变，可以与 cached_config 不同。
- 两份程序比较的是返回值，同时要求候选保持 invariant。私有缓存字节不是公共输出，
  不能把它们与一个不存在的“参考缓存”做逐字节相等比较。
- 数组 schema 2 的所有数组最终元素都是显式输出；这里的私有缓存抽象与其不同。
- `scope.state_contract` 记录所有权、初始化、调用输入、保持证明的入口域与观察；
  `scope.required_state_obligations` 指明 initialization/preservation 缺一不可。
  `verification-result.json` 和 `report.md` 展示相同结果。
- 原生记录必须包含类型正确的全部 after_* 字段；后端重新检查这些值满足 invariant，
  不能仅信任打印出的 invariant_after 标记。原生样本本身不产生全称证明。
- `empty` 模式的保持义务只覆盖空入口；它不是任意 invariant 状态的归纳步骤。
  EXACT 始终描述一次调用的等价区域。条件在后续调用是否继续成立没有自动证明，
  因而本阶段不发布不受限调用序列的等价证书，也不自动合成 invariant。

[本地验收记录](../../docs/validation/cache-state/README.md)；
[公共结果格式](../../docs/RESULT_FORMAT.md)。旧 transfer 实验仍在其原 checkout 运行。
