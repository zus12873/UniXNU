# sheng：macOS 开机自启动（短方案）

日期：2026-11-14
状态：用户已确认（2026-11-14），实施计划见 `docs/superpowers/plans/2026-11-14-macos-autoboot.md`
范围：只做 macOS 自启动。iPadOS 和双系统另行讨论。

## 目的

按电源键就进 macOS，不再靠 Mac 执行 `fastboot boot`。

## 目标、不做的事、不能出现的结果

- 目标：冷开机和重启都自动进入 UniXNU 菜单并启动 macOS；每一步都能回退到现在的状态。
- 不做：iPadOS、双系统、关机和重启补丁、任何 userdata 改动。
- 不能出现：
  - macOS 的 Data 被清空。不刷带 `data-reset` 的 install 镜像，不碰 userdata。
  - 槽位 a 被判为不可启动。全程不执行 `fastboot set_active`。
  - 平板进不了 fastboot。不碰 abl、xbl 等引导链分区。

## 已核实的事实

- 分区大小来自线刷包的 `partition_dev_n81a.xml`：`boot_a` 192 MiB。上机后用 `fastboot getvar partition-size:boot_a` 复核。
- 现在的启动镜像 `out/flash/boot-v4-payload.img` 是 210903040 字节（201.1 MiB），放不进 `boot_a`。
- 镜像里的 payload 是 200 MiB 的 FAT32 卷，8 个文件共 189504632 字节（180.73 MiB）。
- v4 头占 4096 字节，UEFI 部分按页对齐后占 1183744 字节，所以 ramdisk 最大 190.87 MiB。
- 官方 `scripts/unixnu/payload.py` 要求文件总量不超过 `size_mib` 的 95%：190 MiB 过不了这个检查，191 MiB 又放不进分区。
- 这台机器只接受 v4 头的镜像；`init_boot_a` 已擦除，`vendor_boot_a` 是去掉 ramdisk 的版本。在这个状态下 `fastboot boot` 能把 boot 镜像里的 ramdisk 交给 UEFI。
- 原厂 `vbmeta.img` 对 `boot` 用的是 hash descriptor（长度 45.39 MiB）。AVB 公开源码（`avb_slot_verify.c` 的 `load_and_verify_hash_partition`）在允许校验错误时读入整个分区，所以解锁状态下预计不用改 `vbmeta`。这一点没有在这台机器上验证过。

## 考虑过的做法

1. **直接刷 `boot_a`（选定）**：把 payload 的 FAT 卷缩到 190 MiB，镜像约 191.1 MiB。只改一个分区，可用线刷包的 `boot.img` 还原。设备仓库的 `scripts/build-flash-image.sh` 是同一思路的先例（iPadOS、v0 镜像、176 MiB）。
2. **payload 放 `vendor_boot`**（主仓库的 `unixnu vendor_boot` 命令）：`vendor_boot_a` 只有 96 MiB，放不下，排除。
3. **boot 只放 UEFI，payload 放别的大分区**：没有大小限制，但要先验证 UEFI 能读内部存储，改动的分区更多，没有先例。第 1 种失败时再考虑。

用户在 2026-11-14 选了第 1 种。

## 设计

### 打包工具

新增 `local-tools/make-flash-bootimg.py`，不改上游文件，不需要外置硬盘。

- 输入：已验证能启动的 `out/flash/boot-v4-payload.img`。
- 取出 UEFI 部分和 FAT 卷里的全部文件。
- 用和 `payload.py` 的 `write_volume` 相同的 `mformat`、`mcopy` 参数新建 190 MiB 的 FAT32 卷，卷标和序列号不变。
- 把新卷里的文件再取出来，和原文件逐个比对 sha256。
- 拼出 v4 镜像：头部只改 `ramdisk_size`，UEFI 部分逐字节不变，签名区长度为 0。
- 检查镜像不超过分区大小，输出 `out/flash/boot-v4-flash.img` 并打印 sha256。

### 上机步骤

每一步有检查点，不通过就停下。

1. **只读查询**：`partition-size:boot_a`、`current-slot`、`slot-successful:a`、`slot-unbootable:a`、`slot-retry-count:a`、`unlocked`。确认分区放得下镜像。
2. **内存启动测试**：`fastboot boot` 新镜像，不写任何分区。检查点：屏幕到登录页。这一步证明重新打包的卷固件能读。
3. **刷入**：`fastboot flash boot_a out/flash/boot-v4-flash.img`，然后 `fastboot reboot`。检查点：不靠 Mac 的命令也能到登录页。
4. **冷开机复测**：关机后按电源键再开一次。检查点：同上。
5. **槽位复核**：下次进 fastboot 时再读一次第 1 步的变量，确认 `slot-successful:a` 和 `slot-retry-count:a` 没变。

### 可能的结果和回退

| 结果 | 含义 | 处理 |
| --- | --- | --- |
| 到登录页 | 成功 | 做第 4、5 步 |
| 回到 fastboot | bootloader 没接受分区里的镜像 | 先试关闭 `vbmeta` 校验：`fastboot --disable-verity --disable-verification flash vbmeta_a <线刷包>/images/vbmeta.img`，再重启 |
| 进了 UniXNU 菜单但没有启动项 | ramdisk 没交给 UEFI | 还原，转第 3 种做法 |
| 反复重启 | 未知 | 按住电源键和音量下键回 fastboot，还原 |

还原命令：`fastboot flash boot_a <线刷包>/images/boot.img`；动过 `vbmeta_a` 的话再加 `fastboot flash vbmeta_a <线刷包>/images/vbmeta.img`。还原后回到现在的状态，`fastboot boot` 照常可用。

### 成功之后

- 开机：按电源键。回 fastboot：按住电源键和音量下键约 10 秒。
- 更新内核或 payload：重新构建，再用这个工具打包，刷 `boot_a`。
- `out/flash/boot-v4-install.img` 仍然只用于重置 Data，只通过 `fastboot boot` 使用，不刷进分区。

## 留给执行时决定

- FAT 卷大小在 189 到 190 MiB 之间取值，以 mtools 实际能放下全部文件为准。
