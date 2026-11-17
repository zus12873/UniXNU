# 社区分支合并与全部重编（第二阶段）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在合并后的核心仓库之上合并设备仓库的社区分支，重编内核和载荷。打 6 GiB 和 7.5 GiB 的 v4 镜像（本机固件）和 v0 镜像（社区外壳），从内存启动验证。

**Architecture:** 设备仓库照设计合并，`board.toml` 的两处内存冲突保留本机设置，其余社区改动照收。按路线 A 的老办法构建：先备份日常文件，构建完另存带后缀的副本，再还原日常文件。v4 用 `make-bootimg-v4.py` 和 1b 的固件镜像 `boot-bigwin.img`；v0 用第一阶段的 `make-bootimg-v0-template.py`。

**Tech Stack:** `./unixnu build kernel payload`，Python 3 标准库，mtools，fastboot。

**Spec:** `docs/superpowers/specs/2026-11-15-community-branch-test-design.md`（第一部分第 2 到 6 步）

**为什么现在做（19:18 的证据）：**
- v0 那一趟 WindowServer 是因为 "CODESIGNING, Code 2, Invalid Page" 被杀，地址落在开机时改过的那一页 QuartzCore 代码上。社区的 `cshash-signed-text-revalidation.patch` 修的就是这个，已经在合并后的核心仓库里，要重编内核才生效。
- 图标服务在 Metal 校验断言里 abort（`MTLReportFailure`，CoreImage 的 MPS 模糊）。社区的 AdrenoMetal 有一个相关的修复，重编载荷时一起带上。

## Global Constraints

- 只从内存启动，不刷 `boot_a`；每次启动要用户说可以；每次进 fastboot 读两个槽位，a 在 4 或以下就补。
- 日常文件不能被覆盖：`<output>/kernel/kernel.macho`（`33d294c8`）、`<output>/payload/payload.img`（`8a36fe56`）、`<output>/boot/boot.img`（`35f03ec4`）、`<output>/boot/boot.json`、`out/flash/boot-v4-flash*.img`、不带 `bigwin` 的 `out/flash/boot-v4-payload*.img`。构建前后核对哈希。
- 新文件名带 `cd2`：内核 `kernel.macho.cd2-<sha8>`，载荷 `payload.cd2-<名>.img`，镜像 `boot-v4-payload.bigwin-cd2-<名>.img` 和 `boot-v0-cd.cd2-<名>.img`。
- 不带 `data-reset`；芯片号不写进任何文件（不复制 `unixnu.local.toml`）；`verification.json` 不提交；不推送。
- `./unixnu ...` 在 `UniXNU/` 下原样运行、关沙箱；`<output>` = `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos`。

## Review Focus

- 设备补丁 `sheng-text-fixup-verified-pagein.patch` 和社区的 `cshash-signed-text-revalidation.patch` 都改 `ubc_subr.c`。打补丁失败时构建会停，不能跳过任何一个。
- 合并后的载荷是 187 MiB（社区改的）。`make-payload-variant.py` 和 `make-bootimg-v4.py` 要能处理新大小，参数行仍不超过 1000 字节。
- 新内核要能认出现有的数据卷（11-15 18:05 用清空镜像新建的）。认不出就是黑屏加指针，要先问用户才能用"数据初始化"。
- 构建会改 `unixnu.lock`。改动只能留在工作区，提交时只列出要提交的文件。
- 日常镜像和日常构建产物的哈希，构建前后要一样。

---

### Task 1: 合并设备仓库

**Files:** `../UniXNU-sheng`：`patches/xnu-12377/sheng-text-fixup-verified-pagein.patch`、`patches/xnu-12377/series`、`board.toml`（合并时解决冲突）

- [ ] **Step 1：** 把设备补丁和 `series` 那一行提交到 `local/sheng-12g-large-window`。
- [ ] **Step 2：** `git stash push -m pre-cd2 -- feeds.toml unixnu.lock`。`feeds.toml` 和社区的一样，`unixnu.lock` 是构建写进去的。
- [ ] **Step 3：** `git merge --no-ff crossdarwin/boot/sheng-firmware-compat`。`board.toml` 用 `git merge-file --ours` 解决：冲突的两处取本机的，社区不冲突的改动照收。
- [ ] **Step 4：** 核对：`board.toml` 里窗口是 `0x240000000`，`owned_memory_outside_ranges = 16`，有社区的 `bootimg.template` 一节，`size_mib = 187`。然后提交合并。
- [ ] **Step 5：** 更新子模块到记录的版本：设备仓库的 `drivers/Ath12kWifi drivers/QcaBluetooth drivers/ShengNovatekTouch drivers/ShengUfs`，核心仓库的 `drivers/AdrenoMetal drivers/RamBlock`。

### Task 2: 构建内核和载荷

- [ ] **Step 1：** 核对日常文件的哈希（Global Constraints 里那三个）和备份都在。
- [ ] **Step 2：** 把 OS 镜像只读挂上，然后在后台运行 `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。
- [ ] **Step 3：** 核对：
  - 构建日志里 `cshash-signed-text-revalidation.patch` 和 `sheng-text-fixup-verified-pagein.patch` 都打上了；
  - `kernel args:` 那一行里没有 `data-reset`；
  - 新内核里能搜到 `cs_text_fixup_hash`（新补丁加的函数）。
- [ ] **Step 4：** 另存 `kernel.macho.cd2-<sha8>`（`kernel.json`、`kernel.map.json` 同后缀）和 `payload.cd2-base.img`（`payload.json` 同样），再把日常文件从备份还原，核对哈希。

### Task 3: 做载荷变体并打包

- [ ] **Step 1：** 从 `payload.cd2-base.img` 做两份：
  - `payload.cd2-s1.img`：参数照 `payload.bigwin-s1.img`，窗口 `0x1E0000000`，下限 `0x920000000`，`--arg memory-outside=0`；
  - `payload.cd2-ctl6.img`：窗口 `0x180000000`，下限 `0x980000000`，`--arg memory-outside=0`。
  - `--set` 和 `--arg` 的名字取自 HANDOFF 里 `payload.bigwin-s1.img` 的做法。做完用 mtools 读 `unixnu.toml`，看参数行。
- [ ] **Step 2：** v4：`make-bootimg-v4.py <output>/boot/boot-bigwin.img … out/flash/boot-v4-payload.bigwin-cd2-{s1,ctl6}.img <载荷>`，用 `bootimg-contents.py` 核对。
- [ ] **Step 3：** v0：`make-bootimg-v0-template.py` 打 `out/flash/boot-v0-cd.cd2-{s1,ctl6}.img`。
- [ ] **Step 4：** 核对日常镜像的哈希没变；把所有哈希记进 `HANDOFF.md` 并提交。

### Task 4: 上机（每次要用户说可以）

- [ ] **Step 1：** 先启动 `boot-v4-payload.bigwin-cd2-s1.img`（7.5 GiB，本机固件）。通过的标准：
  - 进桌面，物理内存约 7.50 GB；
  - 用到内存满以后，WindowServer 不再因为 CODESIGNING 被杀，终端不卡；
  - 拍一张 `sysctl vm.cs_native4k_stats`；
  - 控制台崩溃报告里没有新的 WindowServer 和 iconservicesagent。
- [ ] **Step 2：** 再启动 `boot-v0-cd.cd2-s1.img`（社区外壳）。看 WindowServer 的循环崩溃还在不在。
- [ ] **Step 3：** 每次的结果记进 `HANDOFF.md` 并提交。
