# Wyckoff VPA Skill v1.0.2

面向中国 A 股的 Wyckoff/VPA 分析工具。

## CLI

唯一入口：

```bash
python vpa.py "<股票名称或代码>"
python vpa.py "<股票名称或代码>" --deep
```

行为：

- 直接接受股票名称、简称或 6 位代码
- 不再需要 `resolve` 或 `analyze`
- 找不到精确股票时，返回候选股票名称和代码，并提示重新输入
- `--deep` 用于长周期分析

## GitHub

- Repo: [tedeyang/wyckoffsoulskill](https://github.com/tedeyang/wyckoffsoulskill)
- Releases: [release packages](https://github.com/tedeyang/wyckoffsoulskill/releases)

对 agent 来说，主要安装方式就是读取这个 GitHub 项目地址，或直接下载对应 release zip，再执行安装或卸载命令。

## Install

### From release zip

```bash
curl -L -o wyckoff-vpa-1.0.2.zip https://github.com/tedeyang/wyckoffsoulskill/releases/download/v1.0.2/wyckoff-vpa-1.0.2.zip
unzip wyckoff-vpa-1.0.2.zip
cd wyckoff-vpa
python -m installer.install install --target codex
```

### From GitHub tag source

```bash
curl -L -o wyckoff-vpa-source.zip https://github.com/tedeyang/wyckoffsoulskill/archive/refs/tags/v1.0.2.zip
unzip wyckoff-vpa-source.zip
cd wyckoffsoulskill-1.0.2
python -m installer.install install --target codex
```

其他目标：

```bash
python -m installer.install install --target claudecode
python -m installer.install install --target all --adapters-root ./adapters-out
```

- `codex`: 自动写入 `~/.codex/skills/wyckoff-vpa`
- `claudecode`: 自动写入 `~/.claude/skills/wyckoff-vpa`
- `kimi` / `openclaw`: 导出 `PROMPT.md` 到 `--adapters-root`

## Uninstall

```bash
python -m installer.install uninstall --target codex
python -m installer.install uninstall --target all --adapters-root ./adapters-out
```

## Build Release

```bash
python -m installer.build_release --output-dir dist
```

输出：

```text
dist/wyckoff-vpa-1.0.2.zip
```
