# 整合别人领先的内容（2026-11-15）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 CrossDarwin、rponeawa 和上游已经做了、我们还没有的内容合进本地，按 12 GiB 机型处理内存相关的部分。主机检查过了就推到用户自己的 fork，再按顺序上机测试。

**Architecture:** 每个仓库从当前工作分支新开 `integrate/others-20261115`，在上面逐个合并别人的分支、解决冲突，现有的工作分支和镜像都不动。顺序是 AdrenoMetal → 核心 → sheng，因为核心要指向 AdrenoMetal 合并后的提交。构建和上机等构建盘接上、用户同意启动后再做。

**Tech Stack:** git（`merge`、`merge-tree` 试合并），`gh`，Python 3 标准库的检查脚本，`./unixnu build`。

**Spec:** 本文件"设计"一节，是用户 2026-11-15 23:38 看过的做法；用户 23:40 回复"落文档，然后开始继续测试"。对比依据见 `HANDOFF.md`"约 23:35 用户：克隆 `CrossDarwin/UniXNU_macOS`"一条和 `local-tools/compare-progress.py`。

## 设计

- 别人的机型是 8 GB 内存 + 256 GB，本机是 12 GB。内存相关的设置一律按本机来。
- **要合的**：
  - AdrenoMetal：
    - 上游 `main`；
    - rponeawa 的 `fix/sync-development-d923`（新运行时，已包含 `primer-reflected-inputs`、`runtime-policy-capture`、两个半精度分支、`a740-gpu-acceptance`）；
    - CrossDarwin 的 `metal/texture-layout-policy`（AdrenoMetal#37）。
  - 核心：
    - 上游 `main`；
    - CrossDarwin 的 `integration/desktop-repairs-20261115`（启动传输和 DTB、FAT 容量、状态颜色、蓝牙、UFS、纹理策略的组件选择）；
    - `vm/signed-text-revalidation`（rponeawa 的两条加固）。
  - sheng：
    - 上游 `main`；
    - CrossDarwin 的 `integration/desktop-repairs-20261115`（PSCI 关机重启 #101、蓝牙和 App 挂载诊断 #104）；
    - `boot/qualified-macos-transport`（#103）、`boot/explicit-macos-data`（#102）、`build/ufs-internal-media`（#105）；
    - rponeawa 的 `fix/sheng-startup-diagnostics`（已包含 `fix/sheng-macos27-bringup`；有固件保留区 `f4e0bc2`、看门狗交接、启动检查点）；
    - rponeawa 的 `fix/sheng-charge-panic-recovery`（已包含 `fix/sheng-charge-disconnect`；电量计和 MiPPS 认证）。
- **这次不合的**：
  - CrossDarwin 的 8 GiB ABL 内存表：`uefi-sheng` 的 `memory/abl-reservations-8g`、`fix/memory-compatible-dxe`，sheng 的 `fix/compat-abl-memory`。它们会换掉本机 12 GiB 的内存表，先读代码，看能不能按 12 GiB 改，另做。
  - CrossDarwin 的 `test_27`：分叉很大的另一条主线（570 个文件不同），原生 APFS 容器是给他们 256 GB 盘的另一套存储方案；里面的内容大多已经拆成上面这些分支。
- **冲突的取舍**：
  - 内存：保留本机的窗口（`owned_memory_size`、`owned_memory_floor`、`owned_memory_excluded_ranges`）、`owned_memory_outside_ranges` 和 bank 1 整段排除（`0x880000000:0x280000000`）。
  - 固件保留区：取 rponeawa 的固件保留区列表（都在 4 GiB 以下，和内存大小无关），和 bank 1 那一段并在一起，要在 macOS 那一段配置里真正生效。
  - 本机已经有、而且更新的东西保留本机的：WindowServer 兜底、`ci-mps`、`enable-jobs`、12 GiB 的内核补丁。
  - `porting.toml` 两边的 findings 和 evidence 都留。
- **推送**：
  - 推到 `zus12873/UniXNU`、`zus12873/UniXNU-sheng`、`zus12873/uefi-sheng`。用户没有 AdrenoMetal 的 fork，用 `gh repo fork UniXNU/AdrenoMetal` 建一个。
  - 推整合分支，也推现在的工作分支作备份。
  - fork 是公开的，`HANDOFF.md` 也会公开（用户已知道）；`data/`、`out/` 不入库。

## Global Constraints

- 不 `git add .` / `-A`；不 `--amend`；不 force push；不推 `main`；不建 PR。
- 芯片号（`unixnu.local.toml` 的 `unique_chip_id`）不进任何文件，每次提交前数一遍；局域网 IP、fastboot 序列号不进入库文件；`verification.json` 的改动不提交。
- 只从内存启动，不刷 `boot_a`；每次启动要用户说可以；槽位 b 永远不设成活动；进 fastboot 读两个槽位，a 在 4 或以下就补。
- 日常文件不能被覆盖：`<output>/kernel/kernel.macho`（`33d294c8`）、`<output>/payload/payload.img`（`8a36fe56`）、`<output>/boot/boot.img`（`35f03ec4`）、`<output>/boot/boot.json`、`out/flash/boot-v4-flash*.img`、不带 `bigwin` 的 `out/flash/boot-v4-payload*.img`。构建前后核对哈希。
- 新的构建产物带 `cd6` 后缀；试验镜像不带 `data-reset`。
- 写 `../` 下的仓库要关沙箱；`./unixnu ...` 在 `UniXNU/` 下原样运行、关沙箱。

## Review Focus

- 合并后的 `board.toml` 里，同一个键可能在基础段和 macOS 覆盖段各有一份，macOS 用的是覆盖段。要读合并后的值，不能只看有没有冲突。
- rponeawa 的 `revert: restore upstream sheng memory configuration and pool` 会把内存设置改回上游。合完要核对本机的窗口值没被改掉。
- rponeawa 改了内核补丁列表 `patches/xnu-12377/series`，本机也加过补丁。两边的补丁都要在，顺序要能打上（构建时才知道，构建前先用 `git apply --check` 试）。
- 核心的 `drivers/AdrenoMetal` 指针和 `components.toml` 的 `revision` 要一起指向 AdrenoMetal 的整合提交，否则构建会把子模块重置回旧的。
- CrossDarwin 的组件选择可能指向只在 CrossDarwin fork 里才有的提交（ShengUfs#12、QcaBluetooth#2/#3），构建取源时要能取到。

---

### Task 1: AdrenoMetal 整合分支

**Files:** `drivers/AdrenoMetal` 子模块，分支 `integrate/others-20261115`

- [ ] 从 `local/sheng-ci-mps`（`2b9a743`）开分支，依次合 `origin/main`、`origin/fix/sync-development-d923`、`crossdarwin/metal/texture-layout-policy`；README 冲突两边都留。
- [ ] 核对本机的两条还在：`NativeAdrenoMetalPlugin.mm` 里有 `ci-mps=0`，`NativeBridgeMetalFrontend.mm` 的 `refuse:` 里有 `MadeBeforeRecovery`。
- [ ] `git diff --check` 干净；能跑的主机检查都跑一遍（看仓库里现有的检查脚本）。
- [ ] 记下整合提交的哈希，给 Task 2 用。

### Task 2: 核心整合分支

**Files:** `UniXNU`，分支 `integrate/others-20261115`

- [ ] 从 `local/sheng-16g-macos` 开分支，合 `upstream/main`。冲突在 `docs/porting/macos.md`、`docs/zh/porting/macos.md`、`scripts/make-macos-data-seed.py`、`tests/macos/test_seed_account.py`：先看本机改了什么、上游改了什么，两边的功能都要留。
- [ ] 合 `crossdarwin-macos/integration/desktop-repairs-20261115`。`components.toml` 的 AdrenoMetal `revision` 和子模块指针改成 Task 1 的提交，其余组件取 CrossDarwin 的选择。
- [ ] 合 `crossdarwin-macos/vm/signed-text-revalidation`。
- [ ] 跑 `python3 -I -B scripts/check-unixnu.py` 和 `tests/` 下相关的测试，要过。

### Task 3: sheng 整合分支

**Files:** `../UniXNU-sheng`，分支 `integrate/others-20261115`

- [ ] 从 `local/sheng-12g-large-window` 开分支，依次合：
  - `upstream/main`、`crossdarwin/integration/desktop-repairs-20261115`；
  - `crossdarwin/boot/qualified-macos-transport`、`crossdarwin/boot/explicit-macos-data`、`crossdarwin/build/ufs-internal-media`；
  - `rponeawa/fix/sheng-startup-diagnostics`、`rponeawa/fix/sheng-charge-panic-recovery`。
- [ ] 按"冲突的取舍"处理 `board.toml`；合完用 `tomllib` 读出 macOS 段最终的内存和保留区，和本机原值、rponeawa 的保留区列表逐项对一遍。
- [ ] `patches/xnu-12377/series` 两边的补丁都在；`porting.toml` 两边都留。
- [ ] 跑核心的 `scripts/porting-record.py check --device ../UniXNU-sheng --base upstream/main`，以及 sheng 里和这些改动相关的检查脚本（watchdog、battery、keyboard 等），要过。

### Task 4: 推到用户的 fork

- [ ] 推之前扫一遍要推的提交：芯片号、局域网 IP、邮箱、私钥都没有。
- [ ] 建 `zus12873/AdrenoMetal`（`gh repo fork UniXNU/AdrenoMetal --clone=false`），子模块加一个 remote 指过去。
- [ ] 推整合分支和现在的工作分支：核心、sheng、AdrenoMetal 各两个；uefi-sheng 只推 `local/sheng-12g-memory-map`。不推 `main`，不 force。
- [ ] 核对远端分支的哈希和本地一致。

### Task 5: 测试（构建盘接上、用户同意启动以后）

- [ ] 备份并核对日常文件的哈希，用整合分支构建内核和载荷，另存成带 `cd6` 后缀的副本，再还原日常文件。
- [ ] 试验镜像：7.5 GiB 窗口、`memory-outside=0`、`enable-jobs=com.openssh.sshd`、`exec-env=iconservicesagent:CI_ENABLE_MPS=0`，不带 `ci-mps=0`（同时验证 Core Image 那个 PR）。
- [ ] 上机看这些：
  - 能进桌面、SSH 能连；
  - iconservicesagent 的环境里有 `CI_ENABLE_MPS=0`，不再崩溃；
  - `tablet-icon-stress.js` 跑两轮没有失败；
  - GPU 复位次数；
  - 关机和重启（PSCI）。
- [ ] 之后另做一份 `memory-outside` 打开的镜像，看固件保留区挡上以后内存用满还会不会卡。
