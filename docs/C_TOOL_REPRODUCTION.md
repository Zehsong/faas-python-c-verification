# 独立源码与 Python 环境复现

统一演示已有用户报告的 **READY 8/8**。本入口进一步检查：从固定 Git 提交复制源码，
在新 Python venv 中安装依赖后，能否得到同样的演示结果。

它复用当前 Linux 主机的编译器、修改版 ESBMC 与系统库；**不是全新主机或容器复现**。
不会安装、升级或替换 ESBMC，不会把未提交的源码改动带入新副本。

## 在现有 Codespace 运行

```bash
git switch codex/same-language-cache
git pull --ff-only origin codex/same-language-cache

python3 tools/reproduce_c_tool.py \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --workdir "$HOME/equiv-reproduction"
```

预期结束输出 **`ISOLATED C REPRODUCTION: READY`**。
打开 `Open overview:` 指向的 README.md，再点击其中的统一演示链接。
最后输出独立 tar.gz 归档；失败也会保存已有日志和诊断。

默认固定运行开始时 HEAD 对应的提交。可用 `--revision <commit>` 明确复现一个提交；
该提交必须包含统一演示入口。原工作区即使有未提交改动，也只记录它们的状态，不复制它们。
若要验证正在编辑的程序，应先使用[普通通用 C 入口](C_TOOL_QUICKSTART.md)，或提交后再复现。

## 实际检查的内容

1. 定位指定 ESBMC 和 C 编译器，记录二进制路径与 SHA-256；检查 ESBMC 帮助中的两个
   定制选项标记。标记只识别预期定制构建，不代替源码审计或字节级历史身份比对。
2. 创建独立、无硬链接的 Git clone，切到明确的提交，检查工作树干净；保存提交源码压缩包。
3. 创建不含系统 site-packages 的 venv，去掉继承的 Python/Git 路径覆盖。
   使用 Python 隔离模式；不把环境变量或凭据列表写入证据。
4. 下载仓库 requirements 中固定版本的二进制 wheel，再从此次 wheel 副本安装。
   执行 pip check，保存 pip freeze、实际导入路径和 wheel 文件。当前依赖为 pycparser==3.0，
   没有运行期传递依赖；本入口不自动解析未固定的传递依赖。
5. 在新 venv 中运行演示组装检查和完整演示。只有实际 READY 8/8、输入/引擎/工具未变，
   且复现工作树仍干净时，复现结果才为 READY。

需要 Linux、Git、Python 3.10+ 及 venv 支持、C 编译器和已有修改版 ESBMC。
默认仅依赖 wheel 下载需要网络。已有本次版本的 wheel 时，可离线执行：

```bash
python3 tools/reproduce_c_tool.py \
  --esbmc /workspaces/esbmc-current/build/src/esbmc/esbmc \
  --wheelhouse /absolute/path/to/unpacked-evidence/wheels \
  --workdir "$HOME/equiv-reproduction"
```

安装失败会停在相应步骤，不会退回当前 Python 环境。超时会终止该步骤的进程组并保留日志。
每步默认设置 600 秒上限；演示默认 3600 秒，可分别通过 setup-timeout/demo-timeout 参数调整。

## 保存和审阅证据

每次创建新的 reproduction-* 目录，包含 checkout、venv、evidence 和最终压缩包。
原仓库文件与全局 Python 安装不会被修改；运行目录会保留，便于检查。

压缩包只包含 evidence，不打包完整 Git 历史和 venv：

- README.md：本次复现状态与演示入口。
- results.json、steps.json、logs/：提交、实际工具身份、逐步命令和失败原因。
- source.tar.gz：指定提交的源码。
- requirements.txt、wheels/：依赖约定与此次安装的 wheel；实际包列表和导入路径在日志中。
- demo/：本次独立运行生成的案例、报告、求解与重放证据。
- SHA256SUMS：包内校验和；tar.gz 另有 SHA-256 文件。

失败时只包含已经产生的材料。总览链接为归档相对路径；原始日志中的绝对路径标识原运行环境。
不自动删除运行目录，不覆盖之前的归档。

READY 证明的是本次独立源码/venv 运行成功。它不覆盖操作系统或动态链接库的完整依赖封闭性，
也不建立独立盲测、任意状态 C 或任意调用序列的等价结论。
[开发状态](PROJECT_STATUS.md) · [本地检查记录](validation/c-reproduction/README.md)。
