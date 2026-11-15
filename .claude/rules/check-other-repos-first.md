# 开始新的开发前，先查别人的仓库有没有同类修复

用户 2026-11-15 定下的规则。适用于这个项目里的所有开发：新功能、修问题、做新的试验镜像、准备 PR。

## 规则

- 动手写代码之前，先查下面这些仓库里有没有同一个问题（或同一处代码）的最新修复、进行中的 PR、讨论。
- 查到了：先用别人的。合进来、或在它上面接着做，并写明出处（仓库、PR 号、提交）。不要自己再写一份。
- 没查到：在 `HANDOFF.md` 当条里写"查过，没有"，列出查过的仓库和关键词，再开始做。
- 提交 PR 时不重复提交别人做过的内容：PR 分支从最新的上游 main 开，只带这一次的改动；描述里写清楚和相关 PR 的关系。

## 要查的仓库

| 范围 | 仓库 | 本地位置 |
| --- | --- | --- |
| 核心 | `UniXNU/UniXNU` | `UniXNU` 的 `upstream` |
| 核心（macOS） | `CrossDarwin/UniXNU_macOS`（默认分支 `test_27`，分支很多） | `../UniXNU_macOS` |
| 设备 | `UniXNU/UniXNU-sheng` | `../UniXNU-sheng` 的 `upstream` |
| 设备（分叉） | `CrossDarwin/UniXNU-sheng`、`rponeawa/UniXNU-sheng` | 按需 `git fetch <url>`，不常驻 |
| 组件 | `UniXNU/AdrenoMetal`、`CrossDarwin/AdrenoMetal`，以及 `components.toml` 里这次要碰的组件（`CrossDarwin/ShengUfs`、`QcaBluetooth`、`Ath12kWifi` 等） | `drivers/<名字>` |
| 固件 | `CrossDarwin/uefi-sheng` | `../uefi-sheng` |

做 PR 的人主要是：上游 `UniXNU` 组织自己的分支，CrossDarwin（Jelly10086 等），rponeawa，bluseliu50，filipnavara，wzc35418。

## 怎么查

1. 拉最新（要关沙箱）：`git -C <仓库> fetch --all --prune`。
2. 按报错原文、符号名、启动参数、文件名搜历史：`git -C <仓库> log --all --oneline -S '<关键词>'`（必要时用 `-G`）。
3. 搜 PR 和 issue，包括已关闭的：
   - `gh search prs --owner UniXNU "<关键词>"`、`gh search issues --owner UniXNU "<关键词>"`
   - `gh search prs --owner CrossDarwin "<关键词>"`
   - 打开看相关 PR 的说明和"Device Test"结果，不只看标题。
4. 看上游比本地新的提交有没有碰同一处：`git log --oneline HEAD..upstream/main -- <路径>`，CrossDarwin 的分支同样看。
5. 本地已有的东西（`git log --all -S`）也算，不要重复做自己做过的。
