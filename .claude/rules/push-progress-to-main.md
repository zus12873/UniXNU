# 进度往上游 main 推：每项改动单独开分支、提 PR

用户 2026-11-17 定下的规则。适用于核心（`UniXNU`）、设备（`../UniXNU-sheng`）、固件（`../uefi-sheng`）和各组件仓库（`drivers/<名字>`）。

背景：之前的进度都堆在本地的 `integrate/*` 分支上，作者（rponeawa）只能从 fork 的大分支里挑着收，收到的还进了他自己的功能分支而不是 `main`。从这条规则起，进度以"能合进上游 `main` 的 PR"为单位推进。

## 规则

- **基线是上游 `main`。** 本地 `main` 只跟随 `upstream/main`，不在上面提交。
- **每一项可以进上游的改动（修复、功能、测试、文档）单独走一遍：**
  1. 先照 `check-other-repos-first.md` 查有没有人做过，包括作者还没合并的功能分支和开着的 PR。
  2. 开分支：`git fetch upstream` 后从最新的 `upstream/main` 开，名字用 `fix/…`、`feat/…`、`docs/…`，只带这一项改动。
     - 改动依赖上游还没合并的分支时（例如作者的 `feat/platform-sleep-wake`，sheng #127），从那个分支开，并在提交说明和 PR 说明里写明依赖。PR 的 base 选那个分支（它在上游仓库里，本身是往 `main` 的 PR）；它合进 `main` 以后把 base 改成 `main`，或从 `main` 重开。
     - 在单独的工作树里做（`git worktree add ../<仓库>-pr-<主题>`），不要切换主检出目录：构建会读主检出目录里的脚本。构建在跑的时候（`pgrep -fl 'unixnu build'`），主检出目录里只改文档，不合并、不切分支、不动子模块。
  3. 验证：改动对应的主机测试先失败后通过；设备仓库跑 `porting-record.py check --base upstream/main`；改过的内核侧源文件用构建参数单独编译。上过机的写清在哪个镜像上看到了什么；没上过机的如实写 "Not run on hardware"。
  4. **验证通过后直接推到用户的 fork**（`zus12873/<仓库>`）的同名分支，不用再问。推完告诉用户分支名和提交。
     - fork 的远端名各仓库不一样，推之前用 `git remote -v` 看：核心和 sheng 里 fork 是 `origin`、上游是 `upstream`；`drivers/<名字>` 里 fork 是 `mine`、上游是 `origin`。
  5. **向上游开 PR 之前先问用户一次。** 没上过机的开成 draft。说明里写清和相关 PR、相关分支的关系。命令：`gh pr create --repo UniXNU/<仓库> --base main --head zus12873:<分支>`（依赖别的分支时 `--base <那个分支>`）。
  6. 在 `HANDOFF.md` 里记下这一项：分支、提交、PR 号、状态（已推 / 已开 PR / 已合并 / 被作者以别的形式收了）。
- **组件里的改动先走组件自己的仓库。** 推到组件的 fork（如 `zus12873/Ath12kWifi`、`zus12873/ArmCpu`），向组件上游提 PR。设备或核心的 PR 里，子模块指针要指向上游取得到的提交；不要在 PR 里把 `.gitmodules` 改成指向 fork。组件 PR 没合并之前，设备那边的 PR 开成 draft 并写明在等哪个组件 PR。
- **开在上游改写历史之前的旧 PR 不再更新**（差异里带几百个提交的那些，如 sheng #109 到 #112）。内容已经在上游的，问过用户后关掉并写明在哪里；还没在的，照本规则重开一个，旧的关掉并指向新的。
- **只属于这台 12 GiB 机器的内容不提 PR，也不推：** `board.toml` 的本机设置、9 GiB 窗口相关的指针和补丁、`local-tools` 里的镜像工具、`HANDOFF.md`、计划和设计文档、这些规则文件。它们留在本地工作分支上。
- **本地工作分支**（现在是两个仓库的 `local/on-main-20261117`）＝ 上游 `main` ＋ 还没合进 `main` 的那些 PR 分支的内容 ＋ 本机这一层。上机用的测试镜像从它构建。
  - 上游 `main` 前进、或某个 PR 合并（或被作者改写后收进去）以后：从新的 `upstream/main` 重建工作分支，把还没进上游的提交和本机这一层重放上去。用上游的版本替换掉已经被收的提交，不要去合旧的 `integrate/*`。
  - 说"某项已经在上游"之前，分别核对 `upstream/main` 和功能分支，按内容比（作者常常压成一个提交再收）。

## 推送和 PR 的授权范围

这条规则覆盖全局规范里"等用户说 push 再推"的约定，但只到这里为止：

| 动作 | 要不要先问 |
| --- | --- |
| 把验证通过的主题分支推到用户 fork 的同名分支（非 `main`） | 不用问，推完说明 |
| 向上游开 PR、把 draft 改成 ready、在 PR 或 issue 里留言 | 每次先问 |
| 推 fork 的 `main`、任何 force push、删除远端分支 | 不做，除非用户当次明确要求 |
| 推本机这一层（工作分支、`integrate/*`） | 不做，除非用户当次明确要求 |

## 不变的约束

- 不 `git add .` / `-A`，不 `--amend`，不 force push。
- 不提交芯片号（`unixnu.local.toml` 的 `unique_chip_id`）、`data/` 下的录屏和日志、本地的根卷策略文件、局域网 IP、fastboot 序列号、SSID。PR 分支推之前用 `git diff upstream/main...HEAD --stat` 看一遍，确认只有这一项改动。
- 提交说明和 PR 说明用英文，照上游的写法（`type(scope): …`）；PR 说明末尾按会话里的署名要求写。主题分支上的提交说明和注释里不写本地的分支名和镜像名（`integrate/*`、`local/*`、`cd15` 之类）：从工作分支搬提交时用 `git cherry-pick -n`，重写说明后再提交。
