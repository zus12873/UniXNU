# sheng macOS 开机自启动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已验证能启动的 macOS 启动镜像重新打包到 192 MiB 以内，刷进 `boot_a`，让平板按电源键直接进 macOS。

**Architecture:** 一个本地打包工具从现有 v4 镜像里取出 UEFI 部分和 payload 卷里的文件，新建一个 190 MiB 的 FAT32 卷放回同样的文件，再拼成 v4 镜像。上机分四步，每步有检查点：只读查询、内存启动测试、刷入并重启、冷开机复测。

**Tech Stack:** Python 3 标准库（`python3 -I` 运行，不装任何包）；GNU mtools 4.0.50（`mformat`、`mcopy`、`mdir`）；`fastboot`。

**Spec:** `docs/superpowers/specs/2026-11-14-macos-autoboot-design.md`

## Global Constraints

- 全程不执行 `fastboot set_active`。
- 不刷也不启动 `out/flash/boot-v4-install.img`，不碰 `userdata`。
- 只允许写 `boot_a`；只有按回退表操作时才允许写 `vbmeta_a`。不碰 abl、xbl 等引导链分区。
- 镜像字节数不超过 `fastboot getvar partition-size:boot_a` 的值（预期 `0xC000000`，即 201326592）。
- 芯片 ID 和 fastboot 序列号不写进任何文件，文档和脚本里一律写 `<序列号>`，由命令行传入。
- 不改上游文件。新文件只放在 `local-tools/`、`docs/superpowers/`，进度写进 `HANDOFF.md`。
- `adb`、`fastboot` 要关沙箱运行。
- 提交只在本地分支 `local/sheng-16g-macos` 上做，逐个列出文件，不 push。`data/` 下的照片和录像不提交。

## Review Focus

1. 卷缩小后簇数低于 65525，固件不再把它当 FAT32：工具必须拒绝（Task 1 `test_refuses_volume_that_is_not_fat32`）。
2. 文件放不进新卷：工具必须失败，并且不留下输出文件（Task 1 `test_refuses_when_files_do_not_fit`）。
3. 输入不是 v4 头，或签名区不为空：工具必须拒绝（Task 1 `test_rejects_source_that_is_not_v4`、`test_rejects_source_with_signature`）。
4. 输出超过分区大小：工具必须拒绝，并且不留下输出文件（Task 1 `test_refuses_output_larger_than_partition`）。
5. 长文件名和多级目录在重新打包后丢失或改名：逐文件比对路径和 sha256（Task 1 `test_repack_keeps_kernel_and_files`，样本里有 `kernel.macho.crypto-hmac.json`）。

---

### Task 1: 打包工具

**Files:**
- Create: `local-tools/make-flash-bootimg.py`
- Test: `local-tools/tests/test_make_flash_bootimg.py`

**Interfaces:**
- Consumes: 一个 v4 头的 Android 启动镜像，ramdisk 是 FAT32 卷（真机输入是 `out/flash/boot-v4-payload.img`）。
- Produces: 命令行 `python3 -I local-tools/make-flash-bootimg.py SOURCE OUTPUT [--fat-mib N] [--partition-bytes BYTES]`。
  - 默认 `--fat-mib 190`、`--partition-bytes 201326592`。
  - 成功时退出码 0，最后一行输出 `OUTPUT: v4, kernel K, ramdisk R, signature 0, N bytes, sha256 H`。
  - 任何拒绝或失败都以非 0 退出码结束，stderr 给出原因，并且 `OUTPUT` 不存在。

- [x] **Step 1: 写失败的测试**

`local-tools/tests/test_make_flash_bootimg.py`，用 `unittest`，把工具当子进程调用。测试自己用 mtools 造小的输入镜像（48 MiB 的 FAT32 卷，卷标 `SHENGESP`，序列号 `53484e47`，文件有 `EFI/UniXNU/unixnu.toml`、`EFI/UniXNU/Payloads/kernel.macho`、`EFI/UniXNU/Payloads/kernel.macho.crypto-hmac.json`，UEFI 部分用 5000 字节的固定内容）。

| 测试 | 断言 |
| --- | --- |
| `test_repack_keeps_kernel_and_files` | `--fat-mib 40 --partition-bytes 44040192` 退出码 0；输出头部 magic 为 `ANDROID!`、版本 4、`kernel_size` 不变、`ramdisk_size == 41943040`、签名长度 0；UEFI 部分逐字节相同；新卷里"路径到 sha256"的映射与输入相同；输出长度等于 `4096 + 8192 + 41943040` |
| `test_volume_label_and_serial_preserved` | 新卷引导扇区偏移 71 处的 11 字节是 `SHENGESP   `，偏移 67 处的 32 位小端值是 `0x53484e47` |
| `test_refuses_output_larger_than_partition` | `--fat-mib 40 --partition-bytes 41943040` 退出码非 0，输出文件不存在 |
| `test_refuses_when_files_do_not_fit` | 输入卷 96 MiB、含一个 45 MiB 的文件，`--fat-mib 40` 退出码非 0，输出文件不存在 |
| `test_refuses_volume_that_is_not_fat32` | `--fat-mib 16` 退出码非 0，输出文件不存在 |
| `test_rejects_source_that_is_not_v4` | 头部版本字段为 0 的输入，退出码非 0 |
| `test_rejects_source_with_signature` | 签名长度字段为 4096 的输入，退出码非 0 |

- [x] **Step 2: 运行测试，确认失败**

Run: `python3 -I -m unittest discover -s local-tools/tests -v`
Expected: 7 个测试全部 ERROR 或 FAIL，原因是 `local-tools/make-flash-bootimg.py` 不存在。

- [x] **Step 3: 实现工具**

要点（其余由实现者决定）：
- v4 头布局：magic 8 字节，`kernel_size` 在偏移 8，`ramdisk_size` 在偏移 12，`header_size` 在偏移 20（必须是 1584），版本在偏移 40，签名长度在偏移 1580；头占一页 4096 字节，后面各段按 4096 对齐。
- 新卷的建法与 `scripts/unixnu/payload.py` 的 `write_volume` 相同：`mformat -C -F -T <扇区数> -v <卷标> -N <序列号> -i <镜像> ::`，再对根目录每一项执行 `mcopy -i <镜像> -s -Q -m <项> ::/`，环境变量 `MTOOLS_SKIP_CHECK=1`、`TZ=UTC`。卷标和序列号从输入卷的引导扇区读取。
- 新卷建好后解析它的引导扇区：簇数低于 65525 或每簇扇区数与输入卷不同就拒绝。
- 把新卷里的文件取出来，与输入卷取出的文件比对路径集合和 sha256，不一致就拒绝。
- 输出头部只改 `ramdisk_size`，其余头部字节和 UEFI 部分原样复制。
- 先写到临时文件，全部检查通过后再改名为 `OUTPUT`。

- [x] **Step 4: 运行测试，确认通过**

Run: `python3 -I -m unittest discover -s local-tools/tests -v`
Expected: `Ran 7 tests`，`OK`。

- [x] **Step 5: 提交**

```bash
git switch -c local/sheng-16g-macos
git add docs/superpowers/specs/2026-11-14-macos-autoboot-design.md docs/superpowers/plans/2026-11-14-macos-autoboot.md
git commit -m "docs: add the sheng macOS autoboot design and plan"
git add local-tools/make-flash-bootimg.py local-tools/tests/test_make_flash_bootimg.py
git commit -m "feat(local-tools): repack the v4 boot image to fit boot_a"
```

### Task 2: 生成并核对真机镜像

**Files:**
- Create: `out/flash/boot-v4-flash.img`（`out/` 已在 gitignore 里，不提交）

**Interfaces:**
- Consumes: Task 1 的命令行；`out/flash/boot-v4-payload.img`（sha256 `4abcc8976c9c94a2628637d3c6f507b595f1e770d1183058933723370c9e8368`）。
- Produces: `out/flash/boot-v4-flash.img` 和它的 sha256，供 Task 3、Task 4 使用。

- [x] **Step 1: 确认输入镜像没变**

Run: `shasum -a 256 out/flash/boot-v4-payload.img`
Expected: `4abcc8976c9c94a2628637d3c6f507b595f1e770d1183058933723370c9e8368`

- [x] **Step 2: 打包**

Run: `python3 -I local-tools/make-flash-bootimg.py out/flash/boot-v4-payload.img out/flash/boot-v4-flash.img`
Expected: 最后一行是 `out/flash/boot-v4-flash.img: v4, kernel 1180683, ramdisk 199229440, signature 0, 200417280 bytes, sha256 <H>`。如果 190 MiB 放不下文件，工具会失败；那时不要加大卷，停下来报告。

- [x] **Step 3: 用独立脚本复核**

不调用工具里的函数，另写一段内联脚本检查：输出长度不超过 201326592；`4096` 到 `4096 + 1183744` 的字节与输入镜像相同；用 `mdir -/ -b` 列出的 8 个文件路径与输入一致；卷的剩余空间大于 4 MiB。
Expected: 四项都通过。

- [x] **Step 4: 把 sha256 写进 `HANDOFF.md` 第 8 节**

### Task 3: 只读查询和内存启动测试

需要平板在 fastboot 并连上 Mac。本任务不写任何分区。

**Interfaces:**
- Consumes: `out/flash/boot-v4-flash.img`；`local-tools/boot-sheng.py`。
- Produces: 记录下来的分区大小和槽位状态（Task 5 要对比）；"新镜像能到登录页"的结论。

- [x] **Step 1: 只读查询**

Run（关沙箱）：对 `product`、`unlocked`、`current-slot`、`partition-size:boot_a`、`slot-successful:a`、`slot-unbootable:a`、`slot-retry-count:a`、`battery-voltage` 逐个执行 `fastboot -s <序列号> getvar <名字>`。
Expected: `product: sheng`，`unlocked: yes`，`current-slot: a`，`partition-size:boot_a` 不小于 `0xBF22000`（镜像的 200417280 字节）。任何一项不符就停下。把 `slot-successful:a` 和 `slot-retry-count:a` 的值记进 `HANDOFF.md`。

- [x] **Step 2: 内存启动新镜像**

Run（关沙箱）：`python3 -I local-tools/boot-sheng.py out/flash/boot-v4-flash.img --serial <序列号> --wait 60`
Expected: `Booting OKAY`，随后输出 `the bootloader stayed away for 45 s: the image is running`。

- [x] **Step 3: 用户确认屏幕**

Expected: 用户看到登录页。看不到就停下，不进入 Task 4，按 systematic-debugging 排查。

### Task 4: 刷入 `boot_a` 并验证自启动

需要平板回到 fastboot。

**Interfaces:**
- Consumes: Task 3 的两个结论（分区放得下、新镜像能到登录页）。
- Produces: 写入后的 `boot_a`；"不靠 Mac 也能到登录页"的结论。

- [x] **Step 1: 刷入前再确认一次镜像**

Run: `shasum -a 256 out/flash/boot-v4-flash.img`
Expected: 与 Task 2 记录的值相同。

- [x] **Step 2: 刷入**

Run（关沙箱）：`fastboot -s <序列号> flash boot_a out/flash/boot-v4-flash.img`
Expected: `Sending` 和 `Writing 'boot_a'` 都是 `OKAY`。出现 `FAILED` 就停下，不重启。

- [x] **Step 3: 重启并观察**

Run（关沙箱）：`fastboot -s <序列号> reboot`，之后 60 秒内每隔几秒用 `fastboot getvar product` 探测 bootloader 是否回来。
Expected: bootloader 不再响应，用户看到 UniXNU 菜单，随后到登录页。
其他结果按 spec 的"可能的结果和回退"表处理：回到 fastboot 就先试关闭 `vbmeta_a` 校验；菜单里没有启动项或反复重启就还原 `boot_a`。

- [ ] **Step 4: 冷开机复测**

用户长按电源键关机（或在 UniXNU 菜单选 Power off），拔掉数据线，再按电源键开机。
Expected: 不连 Mac 也能到登录页。

### Task 5: 槽位复核、记录、提交

**Files:**
- Modify: `HANDOFF.md`（当前阶段一行、第 8 节）
- Modify: `docs/superpowers/plans/2026-11-14-macos-autoboot.md`（勾选完成的步骤）

- [ ] **Step 1: 槽位复核**

下次平板进 fastboot 时（关沙箱）读取 `slot-successful:a`、`slot-unbootable:a`、`slot-retry-count:a`。
Expected: 与 Task 3 Step 1 记录的值相同。如果 `slot-retry-count:a` 变小了，说明每次开机都在消耗重试次数，要立刻告诉用户并停止依赖自启动，另找办法。
这一步需要打断一次正常使用，可以推迟到用户下次因为别的原因进 fastboot 时做；推迟的话在 `HANDOFF.md` 里写明"未复核"。

- [ ] **Step 2: 更新 `HANDOFF.md`**

写明：`boot_a` 现在的内容和 sha256、原厂镜像的还原命令、日常开机和回 fastboot 的方法、更新内核后的重新打包和刷写命令。

- [ ] **Step 3: 提交**

```bash
git add HANDOFF.md local-tools/boot-sheng.py local-tools/make-bootimg-v4.py local-tools/make-vendor-boot-noramdisk.py docs/superpowers/plans/2026-11-14-macos-autoboot.md
git commit -m "docs: record the sheng macOS bring-up and autoboot result"
```

`local-tools/` 里其他已有的脚本如果是产出交付物用的，也在这次提交里逐个列出；提交前先 `git status` 看清楚，并用 `grep` 确认要提交的文件里没有芯片 ID。
