# Handoff：小米平板 6S Pro（sheng）构建 macOS 27.3

更新时间：2026-11-14
**内存更正（2026-11-14 实测）：这台平板是 12 GiB 内存，不是之前一直写的 16 GiB，见文末"用户想把内存拉满"一条。本文件其他地方的"16 GiB"都指这台机器。**

目标：用 UniXNU 为小米平板 6S Pro（代号 sheng，SM8550）构建 macOS 27.3（profile `macos-27.3-26C5035r`）镜像，刷入 `userdata` 后用 `fastboot boot` 启动。

当前阶段（2026-11-14 21:12）：**路线一开始上机（Task 6）。** 21:11 按用户同意把 `boot_a` 刷回 `out/flash/boot-v4-flash.prev.img`（sha256 `40234c20…`，旧内存表，卡死之前一直用的那份），刷完重试 7；21:11:56 从内存启动对照镜像 `out/flash/boot-v4-payload.topwin-k443.img`，`Booting OKAY`，45 秒内引导程序没有回来，屏幕结果等用户反馈。文件没有改名：`out/flash/boot-v4-flash.img`（`c244f53d…`，实测内存表）现在不在任何分区里。读数记在文末"路线一上机"。

上一阶段（2026-11-14 21:00）：**内存路线一在 Mac 上的部分做完了，并经过一次独立审阅；三个新镜像还没有上机。** 审阅结论：可以只从内存启动做 Task 6（先 `out/flash/boot-v4-payload.topwin-k443.img`，再 `out/flash/boot-v4-payload.topwin.img`）；写 `boot_a` 之前要先请用户决定 GPU 驱动那一条已知限制（见文末"路线一的主机部分"）。

上一阶段（2026-11-14 20:05）：**内存路线一在 Mac 上的部分做完了，三个新镜像还没有上机。** 平板这边：`boot_a` 里仍是带实测内存表的镜像（`out/flash/boot-v4-flash.img`，sha256 `c244f53d…`，6.38 GiB），从它启动的两次出现过终端卡住和整机卡死，原因没分清；19:21 起平板在跑从内存启动的对照镜像（旧内存表，5.95 GiB），终端正常。已建议用户下次进 fastboot 时把 `boot_a` 刷回 `out/flash/boot-v4-flash.prev.img`，等用户同意。路线一：设计 `docs/superpowers/specs/2026-11-14-memory-top-window-design.md`（用户已确认），计划 `docs/superpowers/plans/2026-11-14-memory-top-window.md`，Task 1 到 5 完成，Task 6（上机）等用户在场；镜像和读数见文末"路线一的主机部分"。之后做路线二。没解决的：卡死的原因、槽位重试次数、睡眠、macOS 下不充电和不识别 USB 外设、键盘盖和触控板掉线、交换文件能不能用没验证、iPadOS。都在文末"待处理问题"。

上一阶段（2026-11-14 19:05）：**`boot_a` 里是带实测内存表的镜像，macOS 看到 6.38 GiB。** 19:01 刷入 `out/flash/boot-v4-flash.img`（sha256 `c244f53d…`），刷完重试次数 7，重启后 60 秒内引导程序没有回来（屏幕上的结果还没有用户的确认）。这份镜像的内核带上游 #244、#245 和 `vm-swapin-io=1`。正在做：内存路线一（窗口挪到内存顶部，收编下面的 4 GiB），设计在 `docs/superpowers/specs/2026-11-14-memory-top-window-design.md`，等用户确认；用户已定之后做路线二。没解决的：槽位重试次数、睡眠、macOS 下不充电和不识别 USB 外设、键盘盖待机久了失效、交换文件能不能用没验证、iPadOS。都在文末"待处理问题"。

上一阶段（2026-11-14 02:29）：**自启动和关机都已在真机上确认。** 用户反馈"开机键生效了，可以正常开关机"：按电源键能自己进到 macOS，在 macOS 里点 Shut Down 能断电。`boot_a` 里是 `out/flash/boot-v4-flash.img`（sha256 `4cb441e0…`）。唯一没解决的是槽位重试次数：每次正常开机扣 1 次，扣完要接 Mac 补（第 8 节"槽位重试次数"和"日常使用"）。还没开始的：iPadOS / 双系统（等用户说明用途）。新报告、还没处理的：睡眠不工作；只看到约 6 GB 内存（带上游两条内存修复的新镜像 18:07 已内存启动，还没刷 `boot_a`；用户想拉满 16 GB，还没有设计）；macOS 下不充电、不识别 USB 外设（上游已知）。都在文末"待处理问题"。

上一阶段（2026-11-14 02:25）：**`boot_a` 里是带关机修复的新镜像，macOS 里点 Shut Down 能断电（用户 02:19 确认）。** 02:21 刷入 `out/flash/boot-v4-flash.img`（sha256 `4cb441e0…`），刷完读到重试次数 7，重启后从 `boot_a` 启动。没解决的：① 用户说"现在还不能正常关机键开机"，具体现象还没问清（第 8 节"关机修复"末尾）；② 槽位重试次数每次正常开机扣 1，用户已允许用 `fastboot set_active a` 补（第 8 节"槽位重试次数"）。

上一阶段（2026-11-14 02:00）：**macOS 已经能从 `boot_a` 自启动。** 01:43 把 `out/flash/boot-v4-flash.img` 刷进了 `boot_a`，重启后平板没有用 Mac 的启动命令就进了系统。还有两个问题没解决：① 刷 `boot_a` 清掉了槽位 a 的 successful 标记，现在每次正常开机扣一次重试，01:55 读到还剩 6 次（第 8 节"槽位重试次数"）；② 在 macOS 里点 Shut Down 不会关机，平台层没有断电实现，参考仓库有补丁（第 8 节"关机"）。还没做：冷开机复测（不接 Mac，按电源键开机）。

上一阶段（2026-11-14 01:00）：**macOS 已经启动到登录窗口。** 带校验补丁的新内核 00:48 用"首次安装"镜像启动，用户 00:56 反馈"已经看到锁屏登录页面"，WindowServer 崩溃循环已修复。下一步是用户用制作 seed 时 `--user` 填的账户登录（密码只有用户知道，本文件不记录），再看桌面是否正常。以后每次开机都用日常镜像 `out/flash/boot-v4-payload.img`（sha256 `4abcc8976c9c94a2…`，新内核，不带 `data-reset`）；**`out/flash/boot-v4-install.img` 每启动一次就清空一次 Data，除非要重置，否则不要再用。** 启动命令是 `python3 -I local-tools/boot-sheng.py <镜像> --serial <fastboot 序列号>`（要关沙箱）。注意：外置盘 00:56 前后从 Mac 断开了，下次构建前要先接回并重新挂载，见"第二个问题"末尾。细节见下面"黑屏加鼠标的根因"和"第二个问题"两条。 **01:10 用户提出新需求：开机自启动 macOS，并再装一个 iPadOS；调研结论在第 8 节，方案还没定，等用户回答 iPadOS 的用法后再设计，未经确认不要动平板。**

镜像构建完成时的状态（2026-11-13 21:10）：
- `userdata/userdata-root.img`：17603493888 字节，19:58 生成。
- `payload/payload.img`：200 MiB，21:07 生成，内核已包含种子 UUID `CONFIG_XNU_OWNER_DATA_VOLUME_UUID`。
- `boot/boot.img`：210903040 字节，`ramdisk_bytes` 为 209715200，打包命令是 `./unixnu bootimg --os macos-27 --dtb <output>/tree/build/sheng/sheng.dtb`。单独运行 bootimg 时必须传 `--dtb`，只有 `release` 会自动补上。
- 这些产物彼此绑定：根卷策略的所有者密钥、种子 UUID 和芯片 ID。改了其中任何一项，都要按 userdata → kernel payload → bootimg 的顺序全部重做。

**已刷入并启动（2026-11-13 约 21:28）**
- 用户确认已经备份。
- 执行 `adb reboot bootloader`，进入 fastboot 后确认 `unlocked: yes`，userdata 分区大小 `0x77AD3BB000`。
- `fastboot flash userdata userdata-root.sparse.img`：22 批全部 OKAY，用时 494 秒。
- `fastboot reboot bootloader` 之后要等 USB 重新识别再继续，否则会报 `usb_write failed e00002ed`。
- `fastboot boot boot.img`：`Booting OKAY`。
- 屏幕上的启动结果要等用户反馈。之后每次开机都要重新执行 `fastboot boot boot.img`；如果卡住，按电源键加音量下键回到 fastboot。

**启动失败排查（2026-11-13 21:30–21:50）**
- **header v0 启动不了**：bootloader 回复 `Booting OKAY` 之后 0.4 秒就又能响应 `fastboot getvar`，说明在 BootLinux 阶段就失败、退回了 fastboot，屏幕保持黑屏。完整镜像和空 ramdisk 镜像（`--ramdisk none`）结果一样，所以和 200 MiB 的 payload 无关。
  - 注意：`fastboot devices` 只是枚举 USB，判断 bootloader 是否还在运行要用 `getvar`。
  - 失败一次之后，再执行 `fastboot boot` 会一直报 `Load Error`，必须先 `fastboot reboot bootloader`。
  - 槽位 a 正常（successful=yes，retry=6），不是重试次数耗尽。
- **header v4、空签名区可以启动**：用同一个 kernel blob 重新打包，`signature_size` 设为 0，并去掉签名页（scratchpad 里的 `make-v4-test.py`）。之后 bootloader 不再响应，说明已经跳进固件。屏幕显示 "failed to load system"，随后关机。判断是 UniXNU 内置菜单（`no boot entry found`，10 秒后默认执行 Return to firmware）退回平台启动管理器，平台启动管理器没有可启动项，于是关机。这和 `docs/devices/erhai-xingxing19035.md:797` 记录的现象一致。
- **推测的根本原因**：平板运行的是安卓 14 国行固件（UKQ1.231003.002），而 UEFI 输入和 DTB 都提取自 board.toml 锁定的 OS3.0.305.0.WNXMIXM（安卓 16 国际版）。ABL 版本不同，v0 镜像的处理方式也就不同（可能是附加 DTB 匹配不上，也可能是根本不支持 v0）。
- **v4 带 payload 的难点**：v4 的 initrd 由原厂 vendor ramdisk 和我们的 ramdisk 拼接而成，而 `UniXNURamDiskDxe.c` 只在 initrd 开头找 FAT。另外，原厂 vendor_boot 头只给 ramdisk 留了 15 MiB 窗口（见 `docs/guide/boot.md`）。
- 测试镜像：`UniXNU/out/flash/boot-noramdisk.img`（v0）和 `boot-v4-noramdisk.img`（v4），都在 gitignore 里。
- **用户录屏确认（`UniXNU/data/mp4/IMG_6352.MOV`，未纳入 git，不要提交）**：用 v4 空 ramdisk 镜像，屏幕依次显示 Project Silicium logo → UniXNU 菜单（`version 0.1.0 | built-in configuration`，`no boot entry found`，`drivers 0 loaded / 0 failed`）→ 倒计时结束后执行 Return to firmware → BDS 报 `Booting Return Status = Not Found`、`USB boot desired, but no USB devices found` → 警告三角图标 → 关机。这说明固件和显示都正常，问题只在 v0 头部上。
- **决定（2026-11-13 21:50，用户选择）**：把平板升级到项目锁定的 OS3.0.305.0.WNXMIXM 线刷包，与维护者环境保持一致，然后重新刷 userdata，再用标准 v0 boot.img 启动。线刷包下载到 `/Volumes/UniXNUBuild/rom/`，要核对 board.toml `[firmware.image]` 里的 sha256、md5 和字节数。运行前要先通读包里的 `flash_all.sh`，不能用 `flash_all_lock`。
- **线刷包已下载并校验（22:44）**：从新加坡 OSS 直连单线程只有约 0.4 MB/s，改用 24 路并发分段下载，均速约 2.4 MB/s，用时 52 分钟。下载脚本在 scratchpad 的 `range-download.py`，大小、md5、sha256 全部一致。其他小米 CDN 更慢或返回 403；通过 hk2 服务器中转时，Mac 与 HK 之间只有约 40 KB/s，没有用。解压到 `/Volumes/UniXNUBuild/rom/extract/`，并复制到内置盘 `UniXNU/out/flash/`（gitignore），这样刷机时不依赖外置盘；我们的 `userdata-root.sparse.img` 也一起复制过去了。
- **刷 OS3.0 之后（23:00–23:25）**：
  - `flash_all.sh` 刷写 104 项全部 OKAY，进入国际版安卓 16 正常。
  - 之后重刷 macOS userdata（22 批 OKAY）。
  - v0 的 boot.img 和 v0 空 ramdisk 镜像，仍然在 0.4 秒内退回 fastboot，所以根因不是固件版本，之前的推测是错的。
  - v4 加完整 payload 能进入固件，但菜单里没有 `payload:` 行。录屏（`data/mp4/IMG_6355.MOV`）里固件日志显示：`UNIXNURAMDISK: initrd 0xB604B000-0xB7FFEADC rounded to 0x1FB3C00 bytes ... Success`。initrd 只有约 31.7 MB，等于原厂 vendor ramdisk（30996100 字节）加约 2.2 MB（应该是 init_boot 的 ramdisk），boot.img 里的 200 MiB payload 完全没有带进来。说明 GKI 的 ABL 在 v4 模式下，通用 ramdisk 取自 init_boot 分区。
  - DTB ID 核对：stock vendor_boot 里有 8 个 SoC 基础 DTB（board-id 0）；dtbo 里所有小米 8550 机型都是 board-id `0x10008`。我们 `sheng.dtb` 的 msm-id 是 `0x218 v2`、board-id 是 `0x10008`，和 KALAMAP 一致，没有发现不匹配。
  - 维护者记录里 macOS 27.3 在 sheng 实机上跑过（run139 等），用的是 `fastboot boot boot.img`（v0），所以差异在设备一侧，现在还不知道具体是什么。
- **GKI 分区方案打通 payload（23:29–23:40）**：
  - 改了两个分区（ROM 里有原厂镜像，可还原）：
    - `fastboot erase init_boot_a`
    - `fastboot flash vendor_boot_a out/flash/vendor_boot-noramdisk.img`（用 `local-tools/make-vendor-boot-noramdisk.py` 生成：保留原厂 DTB 和 bootconfig，去掉 vendor ramdisk）
  - 启动镜像：用 `local-tools/make-bootimg-v4.py` 把 v0 boot.img 的 kernel 重新打包成 v4，签名区为空，ramdisk 用 payload.img，输出 `out/flash/boot-v4-payload.img`。
  - 第一次启动：UniXNU 找到了 payload，但 DxeCore 在清零 `0x8B9D00000..0x8BB300000` 时触发 `Synchronous external abort`。这台机器是 16+512 版本，受保护区域比维护者那台的低。
  - 处理：把 `../uefi-sheng/Platforms/Xiaomi/shengPkg/Library/MemoryMapLib/MemoryMapLib.c` 里的 "DRAM bank 1 low" 改为 `0x880000000 + 0x20000000`（到 `0x8A0000000` 为止；改动未提交）。然后执行 `./unixnu build firmware`、`./unixnu bootimg --dtb ...`，再重新生成 v4 镜像。
  - 第二次启动（录屏 `data/mp4/IMG_6358.MOV`）：
    - UniXNU 菜单出现 `config: \EFI\UniXNU\unixnu.toml`，启动项是 `Boot`。
    - 自动启动后，内核日志滚动约 40 秒，随后黑屏并出现鼠标指针，说明 WindowServer 已经起来了。
    - 但日志结尾大量报 `IOBlockStorageDriver ... executeRequest: request failed to start!` 和 `disk2s1 ... cluster_push() failed with 16`（EBUSY），夹杂 `device is not ready`，用户反馈一直黑屏。
    - 推测：持久化 Data store 窗口没有打开。依据是 `UniXNU-sheng/drivers/ShengUfs/RootCommands.h:590`：窗口没开时 `hostSyncCache` 返回 NotReady。打开失败的原因（off / no root layout / size / overlaps / window refused）会在更早的日志里打印，录屏读不清。
    - 下一步可选：①对录屏做 Vision OCR（`local-tools/ocr-frames.swift`，做到一半被用户叫停）；②重新启动后近距离拍摄屏幕左侧的日志；③通过 `log=1` 写在 userdata 末尾 32 MiB 的诊断日志读取（需要 `read-sheng-log.py` 配套的 Linux 镜像，目前还没有构建）。
- **黑屏加鼠标的根因（2026-11-14，读代码确认，没靠屏幕日志）**：
  - 现象对应的代码：`UniXNU/drivers/RamBlock/NativeRamBlock.cpp:471-495`。Data 盘是 `isBig`（210 GiB），持久化 store（`direct`）没挂上时，写入一律返回 `kIOReturnNotReady`，也就是屏幕上的 `device is not ready`、`request failed to start`、`cluster_push() failed with 16`。
  - 为什么没挂上：`PersistOverlay.h:87-110`。store 窗口里没有这份种子的覆盖层，又没有要求重置时，结果是 `Kept`，原样保留、不挂载。`NativeRamBlock.cpp:210-212` 的注释写明，`data-reset=1/2` 是新建 store 的唯一途径。
  - macOS 没有入口：iPadOS 用菜单项 "Install and boot" 传 `data-reset`；macOS 的 override 把 `payload.install` 去掉了（`board.toml:284`），`docs/porting/macos.md` 也没写第一次启动要带这个参数。这是文档缺口，可以反馈给上游。
  - 做法：构建一个"首次安装"镜像，只启动一次：`./unixnu build payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr --kernel-arg data-reset=1`。只重建 payload 就行，参数在 payload 步骤合并并封存（`payload.py:114-120`）。再用 `local-tools/make-bootimg-v4.py` 转成 `out/flash/boot-v4-install.img`。
  - 之后的日常启动用不带 `data-reset` 的 `out/flash/boot-v4-payload.img`，否则每次启动都会清空 Data。
  - 构建 payload 前要先把 OS 镜像只读挂到系统盘目录（见上面"payload 挂载 OS 镜像"一条）。
  - 注意：这次构建会把 `<output>/payload/payload.img` 覆盖成带 `data-reset=1` 的版本，之后要重跑一次不带参数的 payload 构建，把它恢复成普通版。
  - 执行记录（2026-11-14 00:04–00:11）：
    - payload 构建成功，`payload.json` 的 `kernel_args` 以 `data-reset=1` 开头，payload sha256 `7e22ec74f3370d823461902dfc2d3d903173ddc3493ddb0101546a1dff3b495a`。
    - `out/flash/boot-v4-install.img`：210903040 字节，sha256 `b52c8e1e5e584d20a25ea7b75f50f49e335f381048864133d95348329f6b1302`。kernel blob 与能启动的 `boot-v4-payload.img` 逐字节一致，ramdisk 等于新的 payload.img。
    - 它等价于 iPadOS 菜单里的 "Erase Data, skip Hello, boot"：`board.toml:87-91` 的 `[payload.install]` 只做一件事，就是追加 `confirm_args`（`data-reset=1` 或 `2`）。
    - store 窗口放得下：Data 盘 210 GiB（`runtime/request.json` 的 `data_gib`），userdata 分区 `0x77AD3BB000`（约 478.7 GiB），末尾保留 1024 MiB 给日志（`NativeUfs.cpp` 的 `log-reserve`），根镜像 16.39 GiB，互不重叠。窗口位置是"分区末尾 − 1 GiB − 窗口大小"，所以 `log-reserve` 以后不能改，改了旧 store 会被当成空白。
    - 00:10 用 `local-tools/boot-sheng.py` 启动：`Booting OKAY`，之后 45 秒 bootloader 没有再响应，说明镜像在运行。
    - 结果（用户 00:15 的照片，`data/png/IMG_6360–6364.HEIC`，未纳入 git，不要提交）：Data 写入报错消失，说明 store 已建好；但屏幕一直滚日志，进不了桌面。原因见下一条。
- **第二个问题：WindowServer 崩溃循环，根因是内核 text fixup 与 4K 页校验冲突（2026-11-14 00:18–00:35，已用计算证实）**：
  - 屏幕日志：`apfs_announce_hash_mismatch ... disk3s1 Data hash mismatch using hash type 1 for 16384 bytes at offset 98435072 in compressed data stream 11400 of inode 11399: expected 035febab…, got 28a001fd6ad8768…`，`decmpfs_pagein_compressed: Verification failed with error 94 ... valid_pages = 3, invalid_pages = 1`，随后 `apfs_pagein ... f_offset 98447360 ... error 94 (WindowServer)`，`exit: pid 904 WindowServer status 0xa reason 2:10`（SIGBUS）。
  - inode 11399 是 SystemOS 卷的 `/System/Library/dyld/dyld_shared_cache_arm64e.03`（把 `141-22145-021.dmg` 只读挂载后用 `find -inum` 查到）。
  - 镜像没坏：原始镜像、两份 sparse 镜像展开后的 sha256 都等于 `userdata-root.json` 的记录，三个窗口和三个 `.vroot` 表也都一致。ShengUfs 读窗口时每个 4K 块都按 `.vroot` 表校验（`RootWindowRead.h`），所以介质上的数据也是对的。
  - 冲突点：macOS profile 的 `board.toml:240` 有 `text_fixups = ["dyld_shared_cache_arm64e.03,5de1134,08060037,1f2003d5"]`（把 QuartzCore 的一条 `tbnz` 改成 NOP，让 WindowServer 输出 8 位 BGRA）。`patches/xnu-12377/native-text-fixup.patch` 在页面通过代码签名校验后，直接改写页缓存里的那一页（文件偏移 `0x5de1000`）。
  - APFS 的校验块是 16 KiB，本项目内核是 4 KiB 页。`bsd/kern/decmpfs.c` 的 `decmpfs_pagein_compressed` 在同一个 16K 块里只有部分页缺失时，只解压缺失的页，然后对内存里的整块做 `VNOP_VERIFY`。块里已有的那一页带着 fixup，哈希就对不上，返回 EBADMSG。
  - 证实：取原始文件 `0x5de0000` 起的 16K，sha256 是 `035febab6e1c…`（等于屏幕上的 expected）；把 `0x5de1134` 的 4 字节换成 `1f2003d5` 后是 `28a001fd6ad87685…`（等于屏幕上的 got）。
  - 这是上游缺陷，是否触发取决于同块的相邻页有没有被回收后重新读入，所以维护者的机器上不一定每次都出现。
  - 修复：新增设备补丁 `../UniXNU-sheng/patches/xnu-12377/sheng-text-fixup-verified-pagein.patch`，并追加到同目录的 `series`（都未提交）。做法是校验前复制这一块，把 fixup 的字节还原成原值再校验；只在块内有 fixup 且有已存在页时才走这条路。补丁已对 `tree/.cache/xnu-work` 做过 `git apply --check`，两个文件也用构建记录里的编译参数做过语法检查。
  - 改了补丁序列后，`./unixnu build kernel` 会重新克隆并打全部补丁（144 个，新补丁排最后）。这次 `kernel payload` 一起构建用了十几分钟，00:47 完成：`kernel.macho` sha256 `5e03486e40894e22…`，链接产物里有 `_cs_text_fixup_restore`；payload sha256 `c2f84d7fe958e8c6…`。
  - 00:48 用新的 `out/flash/boot-v4-install.img` 启动：`Booting OKAY`，45 秒内 bootloader 没有再响应。屏幕结果待用户反馈。
  - 00:51 普通 payload 重建完成：`payload.json` 的 `kernel_args` 不含 `data-reset`，`kernel_sha256` 是 `5e03486e…`，payload sha256 `16947138daf9d705…`。`out/flash/boot-v4-payload.img` 重新生成：sha256 `4abcc8976c9c94a2628637d3c6f507b595f1e770d1183058933723370c9e8368`，UEFI blob 与 install 镜像逐字节一致，ramdisk 等于 `payload.img`，里面没有 `data-reset=1`。OS 镜像已从 scratchpad 的 `os-mount` 卸载，下次构建 payload 前要重新只读挂载。
  - **实机结果（00:56，用户反馈）：屏幕出现锁屏登录页面。** 也就是 WindowServer 和 loginwindow 都起来了，哈希不匹配导致的崩溃循环没有再出现，补丁在真机上有效。这次启动带 `data-reset=1`，Data 是全新的。
  - 输入：按 `docs/zh/porting/macos.md` 第 6 节，触摸屏（`ShengNovatekTouch` + `ShengHidInput`）与显示器配对后当指针用，键盘保护套提供键盘和指针。没有键盘时输不了密码，可以重做 seed 加 `--auto-login`（要同时带 `--volume-uuid <原 UUID>`，否则得重建内核；换 seed 后还要再用一次带 `data-reset=1` 的镜像）。
  - 外置盘断开（00:56 前后）：Mac 的 USB 扩展坞连同外置盘（PSSD T7）从总线上消失，当时构建盘镜像还挂着但没有构建在跑（最后一次写入是 00:51）。OS 镜像在 00:54 已正常卸载；残留的构建盘镜像设备用 `hdiutil detach disk6 -force` 清掉了。下次构建前：接回外置盘，执行 `hdiutil attach /Volumes/12873/UniXNU-build.sparsebundle`，先用 `diskutil verifyVolume /Volumes/UniXNUBuild` 检查卷，再核对 `kernel/kernel.macho` 的 sha256 是否仍是 `5e03486e40894e225c9fe4e7252661d3e4b0ca9e77369fbc6264b604d0f80699`。开机用的镜像都在内置盘 `out/flash/`，不依赖外置盘。
  - `locationd` 每次启动都被 `reason 28:261`（PAC 校验失败）杀掉，出现在哈希错误之前，是另一个问题，目前没查。
- **flash_all.sh 审查结果**：与 lock 版本相比只有最后一行不同（`reboot` 与 `oem lock`）。它会检查防回滚（包内 `anti_version`=1，设备的 `anti` 大于 1 就拒绝刷）。刷写范围是两个槽位的引导链和固件，以及 super/boot/init_boot/vendor_boot/dtbo/vbmeta/recovery/metadata/userdata/misc，最后执行 `set_active a`、`reboot`。
- 平板已用 adb 连上：型号 24018RPACC，bootloader 已解锁（`ro.boot.flash.locked=0`，verifiedbootstate 为 orange），当前槽位 `_a`。
- 芯片 ID 用平板 adb 的 `ro.serialno`（8 位十六进制），只写在 `unixnu.local.toml` 的 `unique_chip_id`，本文件不记录它的值。
- 重启或重新插拔外置盘后，要先执行 `hdiutil attach /Volumes/12873/UniXNU-build.sparsebundle`。
- `adb` 和 `fastboot` 在沙箱里看不到 USB 设备，也起不了 adb 服务，要关掉沙箱运行。

---

## 1. 仓库布局与版本

三个仓库并排放在 `~/Downloads/Projects/personal_projects/` 下，这是文档约定的相对路径，不要挪动：

| 目录 | 来源 | 版本 | 状态 |
| --- | --- | --- | --- |
| `UniXNU/` | github.com/UniXNU/UniXNU | `dff2765` | 干净；20 个 submodule 已初始化；本文件未提交 |
| `UniXNU-sheng/` | github.com/UniXNU/UniXNU-sheng | `1108068` | `unixnu.lock` 被 fetch 改了（见第 5 节） |
| `uefi-sheng/` | github.com/UniXNU/uefi-sheng | `66421cb7` | 干净；所有 submodule 已初始化，5.7 GB |

- **Fork（2026-11-13）**：GitHub 账号 `zus12873` 下已 fork 了 UniXNU、UniXNU-sheng、uefi-sheng（默认分支 `sheng`）和 UniXNU-sm8550-common。本地三个仓库的远端：`origin` 是你的 fork，`upstream` 是 UniXNU 官方，`main` 仍然跟踪 `upstream/main`。2026-11-13 已把 UniXNU（落后 12 个提交）和 UniXNU-sheng（落后 9 个）快进到上游最新，submodule 已同步（Adreno740、AdrenoMetal 的指针更新了）；uefi-sheng 本来就是最新的。新提交包括 macOS 原生 APFS 容器存储、`restore macOS root windows`。更新后已重跑 `--check`（2026-11-13，退出码 0，仍是 143 个补丁，锁定的源码都已在缓存里，没有重新下载）。
- **输出目录在外置盘上（2026-11-13）**：外置 SSD 卷 `12873` 是 exFAT，不支持符号链接，所以在上面建了一个 APFS 稀疏磁盘映像 `/Volumes/12873/UniXNU-build.sparsebundle`（上限 200 GB，按实际写入量占用空间），挂载点是 `/Volumes/UniXNUBuild`。原来的 `out/`（832 MB，20653 个文件，大小逐一核对过）已搬到 `/Volumes/UniXNUBuild/unixnu-out` 并删除了旧目录。`UniXNU/unixnu.local.toml`（已被 git 忽略）里写了 `device`、`uefi`、`out` 三项。**重启或拔盘后要先重新挂载**：`hdiutil attach /Volumes/12873/UniXNU-build.sparsebundle`，否则构建会把输出写回系统盘。`TM-Backup` 是 Time Machine 备份盘、`WININSTALL` 是 FAT32，两个都没有动。
- 状态文件 `state.json`（已随 out/ 搬到外置盘）已经记住设备仓库 `-D ../UniXNU-sheng` 和 `sheng_macos_defconfig`，后续命令不用再带 `-D`。
- 输出目录：`/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/`（下文写 `<output>` 的地方都指它）

## 2. 已完成（都验证过）

**主机工具**
- Homebrew：llvm 23.1.5、lld 23.1.5、ninja 1.13.2、unifdef 2.12、mtools 4.0.50、dtc 1.8.1、cmake 4.4.4
- fastboot：`/opt/homebrew/bin/fastboot`
- Python 3.13：`unixnu` 只用标准库，不需要建虚拟环境
- Xcode 27.2（27B52）：已经用 `xcode-select` 选中；许可协议和首次启动组件都已完成；iPhoneOS 27.2 和 MacOSX 27.2 两个 SDK 都实际编译过 `arm64e` 目标；mig、iig、ld、libtool、metal、compression_tool 都能找到

**依赖检查**：`cd ../UniXNU-sheng && scripts/package.sh --os macos-27 --check` 退出码 0，最后一行：
`check done: 143 patches, configuration sheng_macos_defconfig, OS macos-27.3-26C5035r`
- `out/feeds/` 有 10 个源码：xnu、libplatform、libdispatch、AvailabilityVersions、libpthread、corecrypto-2023、IOStorageFamily、IOHIDFamily，以及 mu_basecore 和它的 submodule
- `out/ipsw/26C5035r/` 有 kernelcache.decompressed（119 MB）、DeviceTree.k114cap.im4p，以及 Static、System、App 三个 trust cache
- `out/` 一共 835 MB

**package 和 firmware 已构建完成（2026-11-13，`./unixnu build package firmware --os macos-27`，退出码 0）**
- `<output>/package/Build/Out/AARCH64-DEBUG/`：UniXNU.efi、UniXNUDxe.efi、UniXNURamDiskDxe.efi 等 6 个 EFI 程序
- 固件 `uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd`：3145728 字节，正好等于要求的 FD_SIZE 0x300000
- 固件预检结果：`0 static errors; 0 vendor inputs still missing`；启动镜像要用的设备树已生成在 `<output>/tree/build/sheng/sheng.dtb`
- 外置盘已用 11 GiB，剩 188 GiB；uefi-sheng 工作区仍然干净

## 3. 还没解决的问题

0. **缺 `ipsw` 命令行工具，目前卡在这里（2026-11-13）**：macOS 27.3 的系统卷 `141-22233-021.dmg.aea` 是 AEA 加密格式，解密前要用 blacktop 的 `ipsw` 工具获取密钥（`/usr/bin/aea` 系统自带，已经有）。系统卷已经完整下载并缓存在 `<out>/ipsw/26C5035r/141-22233-021.dmg.aea`（11.4 GB），不用重下。`brew install blacktop/tap/ipsw` 失败了：Homebrew 要求先把 Command Line Tools 更新到 Xcode 27.0 对应的版本；之后再次尝试被 auto 模式分类器拦下（Unauthorized Access）。需要用户自己安装 `ipsw`。Data 种子、userdata 镜像、内核、payload 和 bootimg 都卡在这一步。**已解决（15:25）**：用户执行了 `brew install ipsw`，装的是 homebrew/core 版本 3.1.745（和 tap 版是同一个工具，两者不能同时安装）。实测 `ipsw fw aea --key <dmg.aea>` 能返回一行 `base64:` 开头的密钥，正是 unixnu 需要的格式。之后重新运行了 `./unixnu build kernel payload --os macos-27`：系统卷已解密成 `<out>/ipsw/26C5035r/141-22233-021.dmg`（14.5 GB），命令按预期停下，打印了制作种子的命令（data_gib 是 210）。种子脚本在 sudo 下会用系统的 Python 3.9.6，实测 `--help` 能正常运行。**下一步由用户在自己的终端运行**（sudo 要交互输入密码）：
`sudo python3 <output>/tree/scripts/make-macos-data-seed.py <out>/ipsw/26C5035r/141-22233-021.dmg <output>/runtime/data.dbr --gib 210 --skip-setup --user '账户名:密码'`
同时在后台用 `./unixnu ipsw fetch "Cryptex1,SystemOS" "Cryptex1,AppOS" --os macos-27` 下载 userdata 需要的两个 cryptex 镜像（只下载、不挂载，不影响种子脚本）。
1. **芯片 ID `UNIXNU_UNIQUE_CHIP_ID`**：平板的平台种子，8 位十六进制，生成 payload 时要用，会写进镜像。只能由用户提供，**不要提交到任何仓库**。文档没写怎么获取。
2. **Xcode 版本风险**：项目是在 Xcode 26 上开发的，CI 固定用 26.6（`.github/workflows/macos.yml` 第 80 行附近）。CI 配置里记录过，换 Xcode 版本后 clang 不认识警告选项、加上 `-Werror` 导致编译失败的情况。本机的 Xcode 27.2 / clang 21.0.0 能不能编过，要等第一次编译内核才知道。如果因为警告失败：另外装 Xcode 26.6，然后用 `DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer ./unixnu ...` 运行。
3. **磁盘空间**：目前剩约 95 GB。`build userdata` 要把 IPSW 里完整的 OS、SystemOS、App 磁盘镜像装进去，可能要几十 GB。
4. **固件步骤可能缺 Python 包**：`uefi-sheng/pip-requirements.txt` 里列了 edk2-pytool 等包。UniXNU 是直接调用 EDK II 的 `build`，大概率用不到。如果真报缺包，用 uv 单独建一个虚拟环境来装，不要装进 conda base 环境。

## 4. 接下来的步骤

**每条命令都要带 `--os macos-27`，漏了就会按 iPadOS 构建。** 以下命令都在 `UniXNU/` 目录下执行。

```sh
# 0. 上游更新后先重跑依赖检查（拉取新锁定的源码），由用户自己运行
cd ../UniXNU-sheng && scripts/package.sh --os macos-27 --check && cd ../UniXNU

# 1. 内核 + payload。第一次运行会在编译前停下，打印制作 Data 种子的命令（含 OS 镜像路径、输出路径、data_gib）
./unixnu build kernel payload --os macos-27
#    用它打印的路径和大小运行（按 docs/zh/porting/macos.md#account，2026-11-13 上游更新后的写法）：
#    sudo python3 scripts/make-macos-data-seed.py "<OS image>" "<output>/runtime/data.dbr" --gib "<data_gib>" \
#      --skip-setup --user '账户名:密码'        # 可选 --auto-login；输出必须是新 seed
UNIXNU_UNIQUE_CHIP_ID=<8位hex> ./unixnu build kernel payload --os macos-27 --data-ramdisk "<output>/runtime/data.dbr"
#    后面执行 bootimg 时也要带上同一个 --data-ramdisk

# 2. package 和固件。固件预检会自动下载 board.toml [firmware.image] 里锁定的官方 fastboot 包，只保留需要的文件
./unixnu build package  --os macos-27
./unixnu build firmware --os macos-27 --uefi ../uefi-sheng

# 3. userdata 镜像（体积大，先 dry-run 看大小）
./unixnu build userdata --os macos-27 --dry-run
./unixnu build userdata --os macos-27

# 4. 启动镜像
./unixnu bootimg --os macos-27 --data-ramdisk "<output>/runtime/data.dbr"
```

第 1 到第 4 步中，除了 userdata，其余可以一条命令完成：
`cd ../UniXNU-sheng && UNIXNU_UNIQUE_CHIP_ID=<hex> scripts/package.sh --os macos-27 --uefi ../uefi-sheng`
（产物是 boot.img、payload.img、kernel.macho 和 manifest）

**刷入并启动（由用户自己操作）**
```sh
fastboot devices
fastboot flash userdata /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/userdata/userdata-root.img   # 会清空安卓数据
fastboot reboot bootloader
fastboot boot /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/boot/boot.img                          # 每次开机都要执行
```
- 卡住时：按电源键加音量下键回到 fastboot。
- 屏幕顶部出现绿带，说明内核之前的阶段都已通过，按 `docs/zh/guide/debugging.md` 的"绿条诊断"排查。
- 内核参数 `vc-text=1` 会把内核日志显示在屏幕上。

## 5. 踩过的坑和注意事项

- **Claude Code 沙箱**：在沙箱里，写 `.git/config`（例如 `git submodule update`）和写上一级目录都会被拒，只能关掉沙箱运行。自动模式的分类器曾以 "Code from External" 为由拒绝在沙箱外运行 `package.sh`。2026-11-13 起，`UniXNU/.claude/settings.local.json`（已被全局 gitignore 忽略）里加了放行规则：`./unixnu *` 和 `../UniXNU-sheng/scripts/package.sh *` 会自动放行，并自动在沙箱外运行。**前提是命令要在 `UniXNU/` 目录下、按这个写法开头，不能加 `cd`、管道或环境变量前缀**，否则就不匹配规则。所以芯片 ID 要写进 `unixnu.local.toml` 的 `unique_chip_id`，不要写成 `UNIXNU_UNIQUE_CHIP_ID=... ./unixnu`。`sudo` 制作 Data 种子的命令不在放行范围内，由用户自己运行。
- **lld**：Homebrew 新版本把 lld 拆成了单独的包，只装 llvm 时没有 `ld.lld`。脚本会去 `/opt/homebrew/opt/lld/bin` 找它。
- **unixnu.lock 被所有 profile 共用**：macOS 的 fetch 新加了 IOHIDFamily，并把 IOStorageFamily 的锁定版本从 `e45fbe30` 改成了 `7edb88fb`。只构建 macOS 不用管；以后要构建 iPadOS，先 `git -C ../UniXNU-sheng checkout unixnu.lock`。
- **sudo**：制作 Data 种子要用 root 运行，复制时保留文件属主。开着 SIP 的 Mac 上，有 19 个带 restricted 标记的条目会去掉这个标记再复制，这是预期行为。
- **macOS 根卷策略要在本地生成（2026-11-13）**：
  - 现象：第一次 `build kernel` 在 `component-ShengUfs` 停下，报错缺 `scripts/policies/macos-27.3-26C5035r/OS/trusted-key.bin`。
  - 原因：上游 UniXNU-sheng 只提交了每个系统卷的 `verification.json`。它 `.gitignore` 里的 `!policies/**/*.bin` 带斜杠，只锚定仓库根目录，匹配不到 `scripts/policies/`，所以 `.bin` 文件都被忽略了。
  - 做法：按 `docs/porting/macos.md` 第 208 行，在 `UniXNU/` 下运行：
    ```
    python3 scripts/make-root-policies.py --tree <output>/tree --output ../UniXNU-sheng/scripts/policies/macos-27.3-26C5035r \
      --window OS=<ipsw>/141-22233-021.dmg:84581E99-… --window SystemOS=<ipsw>/141-22145-021.dmg:6678E466-… --window App=<ipsw>/141-22106-021.dmg:F2AEA010-…
    ```
    UUID 来自 profile 的 `[root]` 段。要关掉沙箱运行，因为它要写外置盘和上一级目录。
  - 镜像校验：三个镜像的 SHA-256 都和 profile 一致。SystemOS 是用 `unixnu.ipsw.decrypt_aea` 单独解密出来的。
  - 产出：策略文件写进设备仓库，每次 tree 步骤都会复制过去。`.bin` 已被 gitignore，`verification.json` 会显示为已修改，不要提交。所有者私钥在 `<output>/tree/build/verified-root-host/keys`，不要提交。
  - **userdata 必须带上哈希表**：`--object OS.vroot=<output>/tree/build/verified-root-OS/hashes.bin`，SystemOS 和 App 同样各加一个。
  - 重新生成策略后，kernel、userdata、payload 和 bootimg 都要重做，不能混用不同批次的产物。
- **输出目录放在仓库外，要补一个符号链接（2026-11-13）**：`UniXNU-sheng/scripts/build-gop-legacy-display-27.py:402` 写死了 `ROOT.parents[4] / 'scripts/build-sheng-source-drivers.py'`，默认输出目录是 `UniXNU/out/` 时，这个路径正好指回 UniXNU 仓库。输出放在 `/Volumes/UniXNUBuild/unixnu-out` 时，它会去找 `/Volumes/UniXNUBuild/scripts`，于是 `archive-20` 失败。处理：建了符号链接 `/Volumes/UniXNUBuild/scripts -> UniXNU/scripts`，代码没改。换磁盘或换输出目录后要重新建这个链接。
- **上游 SoC 版本锁旧了（2026-11-13）**：`archive-20` 编译 `package/BluetoothProbe.cpp` 时报错 `'Sm8550GeniUart.h' file not found`。
  - 原因：这个文件是 UniXNU-sheng 的 5b744f6 引入的，它依赖 sm8550-common 在 009512d（11-07）新增的 GENI UART、GCC 和 QUP DMA 文件。但上游 `feeds.toml` 和 `unixnu.lock` 还锁在 a9f45dc（10-31）。
  - 改动：已把 `../UniXNU-sheng/feeds.toml` 的 sm8550 commit 改成上游 main 的 `2dc650ca76ae38715cd0712e60a44b14fe251745`，然后运行 `./unixnu fetch --os macos-27`，lock 文件会跟着更新。用 GitHub compare 核对过，两版之间只在 `kits/Sm8550Platform` 下新增文件、改了 README，`patches/` 没有改动。
  - 状态：这个改动没有提交。它属于上游 bug，可以提 PR。
- **厂商固件要单独提取（2026-11-13）**：`archive-20` 报 `nanosic/MCU_Upgrade.bin: run scripts/extract-files.py --section Keyboard`。preflight 显示的"0 vendor inputs missing"不包括 `proprietary-files.txt` 里的文件。解决方法：在 `../UniXNU-sheng` 下运行 `python3 scripts/extract-files.py`，不带参数时从 `@fetch` 指定的公开镜像下载，并逐个核对 SHA-256。要关掉沙箱运行。下载了三个文件：触摸固件、键盘固件和 VPU 固件，`--check` 全部显示 ok。
- **Wi-Fi 源码稀疏检出与 git 2.54 不兼容（2026-11-13）**：
  - 现象：`archive-20` 调用 `build-ath12k-wifi.py`，它执行 `Ath12kWifi/tools/fetch-sources.py` 时报 `fatal: specify directories rather than patterns (no leading slash)`。
  - 原因：`source-lock.json` 里的路径是带前导 `/`、并且包含单个文件的模式，只有非 cone 模式才能用。git 从 2.37 起，`clone --sparse` 默认用 cone 模式。
  - 处理：先手动把 `deps/linux` 切到非 cone 模式：`git sparse-checkout set --no-cone <paths>`。`deps/freebsd` 用脚本相同的参数克隆，同样切到非 cone 模式。再运行 `python3 tools/fetch-sources.py`，它会下载 wpa_supplicant，并核对全部锁定版本，`--check` 退出码为 0。这些操作都在构建脚本之外完成，所以不受它 300 秒超时的限制。
- **payload 挂载 OS 镜像时报 Permission denied（2026-11-13）**：
  - 现象：`build-boot-runtime.py` 用 `hdiutil attach -readonly -mountpoint <output>/runtime/prepare-*/os-mount` 挂载时失败。
  - 原因：普通用户不能在一个由用户挂载的磁盘映像卷（`/Volumes/UniXNUBuild`，mount 显示 `noowners, mounted by huanmeng`）里面再挂载别的映像。把挂载点放在系统盘上就能成功；用 root 运行的种子脚本也不受这个限制。
  - 处理：利用脚本自身的复用逻辑（第 40-49 行，已经只读挂载、并且里面有 `sbin/launchd` 的挂载点会直接复用），先执行 `hdiutil attach -readonly -nobrowse -mountpoint <系统盘上的目录> <ipsw>/141-22233-021.dmg`，再跑 payload。跑完后要 detach。
- **payload 构建 GPU 运行时需要 glslang（2026-11-13）**：`build-turnip-darwin.py` 用到 `glslangValidator`，`docs/guide/requirements.md` 的工具表里没有列出它。已通过 `brew install glslang` 安装 16.6.0。meson 由脚本自动装进 `<output>/tree/.cache/mesa-venv`，不需要手动安装。
- **Mesa 需要 bison 3.x（2026-11-13）**：
  - 现象：Turnip 构建在生成 `ir3_parser.c` 时失败，报 `/usr/bin/bison: invalid option -- W`。Apple 自带的 bison 是 2.3。
  - 原因：`build-turnip-darwin.py` 会把 `<output>/tree/.cache/mesa-tools/bin` 放到 PATH 最前面，但这个目录只有 `build-adreno-compiler-host.py` 会生成（它编译锁定版本的 bison 3.8.2，并校验 SHA-256）。macOS 流程里的 `build_plugin` 不会调用它。
  - 处理：手动执行 `python3 <output>/tree/scripts/build-adreno-compiler-host.py`，要关掉沙箱运行，之后再重跑 payload。
- **GPU 插件需要的主机工具以 CI 为准（2026-11-13）**：`docs/guide/requirements.md` 列得不全，完整清单在 `../UniXNU-sheng/.github/workflows/package.yml:56-63`：`brew install dtc llvm lld cmake mtools ninja glslang shaderc spirv-tools bison pkgconf rustup blacktop/tap/ipsw`，再加上 `rustup toolchain install 1.98.0 --profile minimal --component rust-src`。本机这次补装了 glslang、shaderc（提供 `glslc`）和 Rust 1.98.0 + rust-src（`build-adreno-metal-bridge.py` 用 `cargo +1.98.0 -Z build-std` 编译 arm64e 版本）。
- **WCN7850 Wi-Fi 固件需要自己提供（2026-11-13）**：`build-wifi-userspace.py` 要求 `../UniXNU-sheng/firmware/wcn7850/{amss.bin,m3.bin,board-2.bin}` 存在，且与同目录下 `manifest.json` 里记录的大小和 SHA-256 一致；这几个 `.bin` 已被 gitignore。没有 root 时 adb 读不到平板的 vendor 分区。来源：linux-firmware 上游的 `ath12k/WCN7850/hw2.0/`，下载地址形如 `https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/ath12k/WCN7850/hw2.0/<file>`。2026-11-13 下载的版本，三个文件的大小和 SHA-256 都与 manifest 完全一致。
- **kernel 和 payload 必须用同一条命令构建（2026-11-13）**：单独运行 `build payload` 会报 `Data seed UUID differs from the compiled configuration`。原因在 `scripts/unixnu/runtime.py:111`：只有当同一条命令里也有 `kernel` 时，它才会把种子的卷 UUID 写进 `.config`（`CONFIG_XNU_OWNER_DATA_VOLUME_UUID`），再编译内核。所以要一起运行：`./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。
- **刷 userdata 要先转成 sparse 镜像（2026-11-13）**：直接执行 `fastboot flash userdata userdata-root.img` 时，Homebrew 的 fastboot 37.0.0 在发送前就报错 `Failed reading from userdata`，设备上什么都没写。原因是分区比镜像大，fastboot 会先读整个 17.6 GB 文件，去复制 AVB footer。项目自带的 `scripts/make-android-sparse.py SRC DST` 已经说明了这个问题：转换后零块写成 FILL（不是 DONT_CARE），会展开回原内容核对 SHA-256，然后刷 `userdata-root.sparse.img`。
- **userdata 已构建（2026-11-13 19:58）**：`<output>/userdata/userdata-root.img` 大小 17603493888 字节（16.39 GiB），包含 OS、SystemOS、App 三个卷和三个 `.vroot` 表，SHA-256 都与 profile 一致。board.toml 里的 userdata 分区约 232 GiB，对应 256 GB 版本；这台平板的 `/data` 有 479G。不过内核运行时是读 GPT、按分区名查找 userdata 的（`ShengUfs/RootLayout.h` 的 `findRootLayout`），board.toml 的 LBA 只用于主机端检查容量，所以分区更大没有影响。
- `build kernel` 的引导编译会在链接时失败，日志里出现 `ld: symbol(s) not found` 是正常的（见 `scripts/unixnu/kernel.py:202`），只看最终退出码。
- xcodebuild 在沙箱里会刷 `DVTFilePathFSEvents: Failed to start fs event stream` 警告，可以忽略。
- 项目不分发 Apple 二进制文件，所有镜像都要自己构建；IPSW 是按需从 Apple CDN 读取的。

## 6. 对结果的预期（来自维护者记录，未验证）

依据 `docs/zh/devices/sheng.md` 和 `docs/zh/devices/sheng-macos.md`：
- 官方 sheng 默认构建 iPadOS 27，macOS 27.3 是挂在 `os_overrides` 下的第二个 profile。
- macOS 27.3 已在实机上确认的：键盘保护套能用，能走完键盘设置助理（2026-11-10）；Wi-Fi 能连上、能拿到 DHCP 地址；颜色正确（`fb-half=2`）；H.264 硬解可用。
- 还没做到的：GPU Metal 插件没打进 macOS 镜像（`gpu_addon = false`）；蓝牙配对没确认；触控板偶尔会失灵；很多改动标着 "Not yet run on hardware"。
- 结论：实验性质，不能当日常系统用。

## 7. 参考文档

- `docs/zh/porting/macos.md`：macOS profile 的完整流程（输入、Data 种子、构建、检查点）
- `docs/zh/building.md`：命令、选项、输出目录
- `docs/zh/guide/boot.md`：fastboot 刷写、启动菜单、恢复
- `docs/zh/guide/requirements.md`：主机工具和外部输入
- `docs/zh/devices/sheng.md`：sheng 各子系统的实现与证据
- `../UniXNU-sheng/README.md`：一键打包脚本和 GitHub Actions 构建

## 8. 新需求：开机自启动 macOS 与 iPadOS（2026-11-14；自启动和关机已完成并在真机确认，iPadOS 未开始）

用户原话："我现在想开机自启动macos，然后我想再往上刷个ipados"，并指定参考仓库 `https://github.com/CrossDarwin/UniXNU_macOS`（已克隆到 `../UniXNU_macOS`，默认分支 `test_27`，是 UniXNU 主仓库的 fork，与本地 main 的分叉点是 `2bbb39d`，领先 64 个提交）。

**参考仓库里有什么（2026-11-14 逐提交核对；远端最新是 `c4f9d5e`（11-12），`../UniXNU_macOS` 已是这个版本）**
- 概况：fork 自己的工作是 55 个非合并提交，全部由 Jelly10086 在 11-10 到 11-12 提交；另有 9 个合并（Jelly10086 7 个、RinnRei 2 个，都是合并上游）。`test_27` 里 rponeawa 的 GPU、Mesa、Metal 提交来自上游，不是 fork 的工作。相对分叉点共改 87 个文件，+5338/−157 行（`git diff --stat upstream/main...origin/test_27`）。
- 分支和标签：
  - `test_27`：默认分支，也是主线。
  - `main`：上游的旧镜像，落后上游 61 个提交，没有自己的提交。
  - `sheng/macos-actions`：Actions 文档里让在这个分支上运行工作流，但它停在 11-11，比 `test_27` 旧。
  - `macos/retain-root-union-on-shutdown`：只有一个提交 `3350146`，内容是关机补丁。
  - 标签 `test_27-apfs-smoke-1`（`bdc3721`）和 `test_27-apfs-xart-1`（`b34ad0e`），都打在 11-11。
- `test_27` 落后上游 main 8 个提交，其中有上游 11-13 的 `51d1c56 feat(macos): build APFS containers with native tools`（作者 bluseliu50）和当天的回退 `dff2765 fix(macos): restore the previous root storage layout`。本地分支基于上游，已经带着这次回退。
- fork 做的五块工作：
  1. Actions 打包（`.github/workflows/sheng-macos.yml`、`docs/zh/guide/sheng-macos-actions.md`、`scripts/ci/`）：只能手动触发，在 `xcode-27` runner 上从下载 IPSW 一直做到 `boot.img` 和覆盖整个 userdata 的 `userdata-full.img`，分卷上传。平台种子放在 Secrets 的 `UNIXNU_UNIQUE_CHIP_ID`，第一次安装勾选 `init_data`。面向 256 GB 的 sheng（userdata 249497890816 字节）；这台是 16+512（`0x77AD3BB000`），整分区镜像不能直接刷。文档写明 `boot.img` 用于临时启动。
  2. 下载和构建：IPSW 按区间并发下载（`scripts/unixnu/ipsw.py`，`UNIXNU_IPSW_WORKERS`，默认 64，8 MiB 分块，只重试失败的块，分块缓存可以跨次复用）；GitHub 下载遇到限流会重试，或改走 Git 对象（`scripts/github_download.py`）；准备系统镜像前按固定哈希校验 WCN7850 固件、蓝牙源码等输入。
  3. 实验性的原生 APFS 容器（`scripts/sheng-apfs/README.md`）：用 macOS 自带工具做出 System、Data、AppOS 卷组，xART 可以之后在 Linux 上补，再用 mkosi 打包。替换现有 userdata 布局，单系统；内核绑定容器 UUID，Data 可写；没有封印和逐块校验；要配合 ShengUfs `57f031c9…`。`provision-data.py` 可以预置账户（支持 `--auto-login`）。
  4. 关机和重启：`macos-union-shutdown.patch`（`d95eaaf`）和 PSCI 断电和重启。`03c7486` 先把 `drivers/ArmDTPlatform` 子模块指到带 PSCI 的版本；`e29de06` 改回已发布的驱动版本，把 PSCI 改成构建时打的补丁 `scripts/data/armdt-platform-psci.patch`（由 `scripts/build-arm-driver.py` 打上）。
  5. 其他：QEMU 的 AMP 拓扑描述和可写覆盖盘、桌面诊断打包、panic 探针链接、终端重连；`AGENTS.md` 加了"等构建或刷机时交给只读监控子代理"的规则。
- 没有的东西："刷进 boot 分区自启动"和"双系统并存"的做法；睡眠（见第 9 节"睡眠不工作"）。
- 和本地分支的关系：
  - 已经拿过来：`fcbfc2e`（原样摘取 `d95eaaf`）和 `6ce74b5`（移植 PSCI 补丁，补丁文件和 fork 逐字节相同）。
  - 原生 APFS 暂时不搬：按 256 GB 分区打包，换布局要重刷整个 userdata，没有封印和逐块校验，上游 11-13 合入类似方案后当天就回退了，而现有布局已经能用。
  - 可以考虑借用：IPSW 并发下载。这部分相对独立，以后重建遇到下载慢再拿。
  - 没查到的：GitHub API 在沙箱里 TLS 校验失败（`gh` 报 `x509: OSStatus -26276`），所以没看 Releases 和 Actions 运行记录，不知道这个工作流实际有没有跑通。

**自启动 macOS：调研到的事实**
- 分区大小（ROM 的 `partition_dev_n81a.xml`，上机后要用 `fastboot getvar partition-size:boot_a` 复核）：`boot_a` 192 MiB，`vendor_boot_a` 96 MiB，`recovery_a` 100 MiB，`init_boot_a` 8 MiB。
- 现在的 v4 启动镜像是 210903040 字节（201.1 MiB），放不进 `boot_a`。payload 是 200 MiB 的 FAT32（`board.toml` macOS 段 `size_mib = 200`），实际用了 180.7 MiB：`kernel.macho` 137.1、`kernel.macho.gpuaddon` 22.7、`scratch-data.img` 20.5、trustcache 0.4。ramdisk 上限约 190.8 MiB，所以把 `size_mib` 改到 188 左右就能放进去。 **更正：这个办法行不通。`payload.py` 要求文件不超过卷的 95%，188 MiB 和 190 MiB 都过不了检查，实际做法见下面"自启动实施记录"（本地工具重新打包成 190 MiB 的卷）。**
- 设备仓库的 `scripts/build-flash-image.sh` 是维护者的同类做法（payload 176 MiB，刷 `boot_b` 后 `set_active b`），针对的是旧的 session image 流程和 v0 镜像，不能直接用。
- 原厂 `vbmeta.img`（flags 0）里 `boot`、`dtbo`、`init_boot`、`vendor_boot` 都是 hash descriptor，`boot` 的 `image_size` 是 47599616（45.39 MiB）；`recovery` 和 `vbmeta_system` 是 chain。按 libavb 的行为，从分区正常启动时只会读入 descriptor 记录的长度，我们的镜像会被截断。所以刷 `boot_a` 的同时要把 `vbmeta_a` 刷成关闭校验的版本（`fastboot --disable-verity --disable-verification flash vbmeta_a <ROM>/images/vbmeta.img`），可用原厂 `vbmeta.img` 还原。这一条是按 AVB 公开实现推断的，没有在这台机器上验证。
- 不要执行 `fastboot set_active`：它会清掉槽位 a 的 successful 标记并把重试次数重置为 7，之后每次开机减 1，减到 0 槽位就被标成不可启动（没有安卓来标记启动成功）。 **更正（01:55）：刷 `boot_a` 本身就会清掉这个标记，见下面"槽位重试次数"。**
- 没验证的点：正常开机路径是否和 `fastboot boot` 一样接受"v4 头 + boot 里带 ramdisk + init_boot 为空"。失败的表现应当是退回 fastboot，和现在一样，可以用 ROM 里的 `boot.img`、`vbmeta.img` 还原。
- 重建 payload 需要外置盘接回来。

**iPadOS：调研到的事实**
- `board.toml` 的默认 profile 就是 `ipados-27.0.1-24A446`，上游主要目标；构建需要另下 IPSW、另建内核和 payload、另做 Data 种子。
- 存储布局按"一台平板一个系统"设计：userdata 开头只有一份 `SHNGROOT` 清单，两个系统的窗口都叫 `OS`、`SystemOS`（`drivers/ShengUfs/RootPublication.h:13-14` 按字面名字查找）；持久化 Data store 的位置从分区末尾倒推（`NativeUfs.cpp:1500-1519`，`log-reserve` 默认 1024 MiB），两个系统的 store 会重叠。
- macOS 的 payload 一个就占 181 MiB，两个系统的 payload 放不进同一个 192 MiB 的 boot 分区。
- 所以"两个系统同时留在平板上"需要自己改存储布局和驱动，属于开发工作，结果不确定；"轮流刷"则每次切换都会清掉另一个系统的数据。

**自启动实施记录（2026-11-14，方案 `docs/superpowers/specs/2026-11-14-macos-autoboot-design.md`，计划 `docs/superpowers/plans/2026-11-14-macos-autoboot.md`）**
- 用户选了"直接刷 `boot_a`"。提交在本地分支 `local/sheng-16g-macos` 上，不 push。
- 更正：前面"必须关闭 `vbmeta_a` 校验"的说法不成立。AVB 公开源码 `avb_slot_verify.c` 里，允许校验错误（解锁）时 `load_and_verify_hash_partition` 读入整个分区。现在的做法是先不动 `vbmeta`，`boot_a` 启动失败再试。
- 官方 `payload.py` 要求文件总量不超过 `size_mib` 的 95%：190 MiB 过不了检查，191 MiB 放不进分区。所以新增本地工具 `local-tools/make-flash-bootimg.py`（测试在 `local-tools/tests/`，`python3 -I -B -m unittest discover -s local-tools/tests`；当时 8 个全过，02:40 按代码审查补强后是 12 个），从已验证的 `out/flash/boot-v4-payload.img` 重新打包。
- 产物 `out/flash/boot-v4-flash.img`：200417280 字节，sha256 `ae0d4179c7702492dbc916a73f35c851baa6722ad72486ee66d9c9bebaee7e4e`。FAT32 卷 190 MiB，簇 2048 字节，8 个文件，剩余 8.5 MiB。独立核对过：UEFI 部分与源镜像逐字节相同，头部只有 `ramdisk_size` 不同，8 个文件的路径、大小、sha256 与源镜像一致。
- 上机进度（顺序是只读查询 → `fastboot boot` 新镜像 → 刷 `boot_a` → 冷开机复测 → 槽位复核）：
  - 01:39 只读查询：`product: sheng`，`unlocked: yes`，`current-slot: a`，`partition-size:boot_a: 0xC000000`（201326592，镜像放得下，余 909312 字节），`partition-size:vbmeta_a: 0x20000`。
  - 槽位基线（刷入前）：`slot-successful:a: yes`，`slot-unbootable:a: no`，`slot-retry-count:a: 6`；`slot-successful:b: no`，`slot-unbootable:b: no`，`slot-retry-count:b: 7`。槽位 a 的重试次数和 11-13 晚上记录的一样，说明标记为 successful 的槽位开机不扣次数。电池 3892 mV。
  - 01:39 内存启动 `out/flash/boot-v4-flash.img`：`Booting OKAY`，45 秒内 bootloader 没有再响应，镜像在运行。屏幕结果等用户确认；确认到登录页之后才刷 `boot_a`。

  - 01:41 用户反馈内存启动到了登录页，同时反馈在 macOS 里点 Shut Down 没有关机。
  - 01:43 刷入：`fastboot flash boot_a out/flash/boot-v4-flash.img`，`Sending 'boot_a' (195720 KB) OKAY [4.488s]`，`Writing 'boot_a' OKAY [0.077s]`。刷完立刻读到 `slot-successful:a: no`（刷入前是 `yes`；重试次数当时没读）。`fastboot reboot` 之后 75 秒内 bootloader 没有回来。
  - 用户反馈：平板自己进了系统（这次启动没有用 Mac 的启动命令，从 `boot_a` 自启动成立）；在系统里点 Shut Down 仍然没有关机；之后用户手动按键进了 fastboot。
  - 01:55 槽位读数：`current-slot: a`；`slot-successful:a: no`，`slot-unbootable:a: no`，`slot-retry-count:a: 6`；`slot-successful:b: no`，`slot-unbootable:b: no`，`slot-retry-count:b: 7`；电池 3880 mV；`charger-screen-enabled: 1`。
  - 还没做：冷开机复测（不接 Mac，按电源键开机）。

**槽位重试次数（2026-11-14 01:55，未解决）**
- 事实：`fastboot flash boot_a` 清掉了槽位 a 的 successful 标记。刷入前是 `successful: yes`、重试 6；刷入并正常启动一次之后是 `successful: no`、重试 6；用户手动进 fastboot 没有再扣。之前刷 `vendor_boot_a`、擦 `init_boot_a` 都没有动这个标记。
- 解释（来自我记忆中的高通公开 ABL 源码 QcomModulePkg，本次没有逐行核对；和上面的读数吻合，但刷完当时的次数没读）：刷名字以 `boot` 开头的分区时，`FastbootUpdateAttr` 会清掉 successful 和 unbootable，并把重试次数设为 7；槽位没有 successful 标记时，每次正常开机在 `FindBootableSlot` 里扣 1；`fastboot boot`、按键进 fastboot、进 recovery 不扣。冷开机复测后再读一次，读到 5 就证实了这个解释。
- 后果：还能正常开机 6 次。扣到 0 之后 ABL 会把槽位 a 标成不可启动并切到槽位 b。ROM 的 `flash_all.sh` 给两个槽位刷的是同一套原厂安卓镜像（`fastboot flash boot_ab …`），而 userdata 现在是 macOS 的，所以槽位 b 起不来，平板会停在 fastboot 或原厂 recovery。**在 recovery 里不要选清除数据。** 这不是变砖：接上 Mac 执行 `fastboot set_active a`，或者重刷一次 `boot_a`，次数就回到 7。
- 四个仓库里都没有"把槽位标成 successful"的代码。安卓是系统启动完成后自己标记，postmarketOS 用 `qbootctl`。
- 设计文档里"全程不执行 `fastboot set_active` 就能保住标记"的前提不成立。**用户 2026-11-14 已允许：重试次数快用完时执行 `fastboot set_active a` 补回次数。** 只限槽位 a，不切到槽位 b；重刷 `boot_a` 也会把次数补满。长期方案做不做仍待用户决定。
- 长期方案的现状：UEFI 侧做不了。`../uefi-sheng/Platforms/Xiaomi/shengPkg/sheng.dsc` 里 `SHENG_VENDOR_HW = 0`，固件不加载原厂的 UFS 驱动，读写不了内部存储。只能放在内核侧（`ShengUfs` 驱动能访问 UFS），做法是改写 LUN 4 分区表里 `boot_a` 这一项的属性位和两处 CRC，主、备分区表各一份。这个 LUN 上还有 abl 等引导链分区，分区表写坏了可能要 EDL 才能救，所以必须先得到用户同意，并且先用 ROM 里的 `gpt_main4.bin`、`gpt_backup4.bin` 做主机侧测试。

**关机（2026-11-14 调研；已修复，见下面"关机修复"）**
- 现象：在 macOS 里点 Shut Down，平板不断电。用户反馈了两次，两次都是之后手动按键进的 fastboot。
- 原因：本仓库的 `drivers/ArmDTPlatform/ArmDTPlatform.cpp` 没有重写 `haltRestart`，只有调试用的 `platformStageReset`（PSCI SYSTEM_RESET）。内核走到平台层时，没有任何断电或重启的实现。
- 参考仓库 `../UniXNU_macOS` 的修法是两处补丁：
  - `scripts/data/armdt-platform-psci.patch`：给 `ArmDTPlatform` 加 `haltRestart`，关机调 PSCI SYSTEM_OFF（`0x84000008`），重启调 SYSTEM_RESET（`0x84000009`），调用方式（smc 或 hvc）取设备树 `psci` 节点的 `method`。fork 里由 `scripts/build-arm-driver.py:65` 在构建时打上。对本仓库执行 `git apply --check --directory=drivers/ArmDTPlatform` 通过。
  - `profiles/os/macos-27.3-26C5035r/patches/xnu-12377/macos-union-shutdown.patch`（fork 提交 `d95eaaf`）：关机时保留只读的根卷联合挂载。补丁说明写的是：sheng 上正常的卸载流程会卸掉 SystemOS 上层，PID 1 随后取指出错，内核在复位前 panic。它引用的 `native_union_identity` 在本仓库已有的 `macos-union-one-volume.patch` 里。
- 要修就得重建内核和 ArmDTPlatform 驱动，再重建 payload、重新打包、先 `fastboot boot` 验证、再刷 `boot_a`。动手前要把外置盘接回并校验。PSCI SYSTEM_OFF 在这台机器上能不能真的断电，没有验证过。
- 现成的替代办法（没验证过）：UniXNU 菜单有 Restart 和 Power off 两项（`boot_a` 里的 `unixnu.toml`，`action = "reset"` 和 `"shutdown"`；`package/UniXNUPkg/Library/UniXNULib/Boot.c:22,26` 调 `gRT->ResetSystem`）。菜单倒计时 3 秒。按键处理在 `Menu.c:219-232`：`SCAN_UP`、`SCAN_DOWN` 移动，回车、空格、`SCAN_RIGHT`、`SCAN_SUSPEND`（0x0102）确认。它们对应音量键和电源键，是按高通按键驱动的惯例推断的。
- 排除的原因：设备包 `../UniXNU-sheng/package/BootReset.c` 有"把重启原因写成 bootloader，之后任何重启都进 fastboot"的调试功能，只在启动参数带 `autoreset=<秒>` 时生效。`boot_a` 里的启动参数共 58 个，没有 `autoreset`，相关的只有 `debug=0x14e`、`log=1`、`disable-watchdogd=1`、`exec-log=1`。

**关机修复：已完成（02:09 开始构建，02:21 刷入 `boot_a`，用户 02:19 和 02:28 在真机确认）**
- 本地分支 `local/sheng-16g-macos` 上的改动：
  - 提交 `fcbfc2e`：从参考仓库原样摘取的 `d95eaaf`（`macos-union-shutdown.patch` 和 `patches/xnu/series` 里的一行，排在 `macos-union-one-volume.patch` 后面）。
  - 还没提交，等构建验证：`scripts/data/armdt-platform-psci.patch`（和 fork 逐字节相同）以及 `scripts/build-arm-driver.py` 里的 8 行（fork 提交 `e29de06` 的做法：把固定版本的驱动源码复制到输出目录再打补丁，不改 `drivers/ArmDTPlatform` 本身）。
- 动手前核对过：固定的驱动源码 blob 是 `317ce20`，正是补丁的基底；交给内核的设备树里有 `/device-tree/psci`，`method = "smc"`，补丁靠它决定调用方式。
- 外置盘 02:06 挂回，`diskutil verifyVolume` 通过，`kernel/kernel.macho` 的 sha256 仍是 `5e03486e…`。OS 镜像只读挂在 scratchpad 的 `os-mount`，构建完要卸载。
- 构建命令：`./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`（在后台运行）。
- 打包时的坑：v0 源镜像必须用 `<output>/boot/boot.img`，它的 UEFI 部分（sha256 前缀 `0770b709`）和 `boot_a` 里的一致。`out/flash/boot.img` 是 11-13 21:31 的旧 UEFI（前缀 `dd48bf6a`，没有内存映射修正），不能用。mkbootimg 在 `../uefi-sheng/Resources/Scripts/mkbootimg.py`。
- 构建完要做：核对内核里有 `retained for shutdown` 字符串、驱动里有 `haltRestart` → `local-tools/make-bootimg-v4.py` 出新的 `boot-v4-payload.img`（旧的先改名留作回退）→ `local-tools/make-flash-bootimg.py` 出新的 `boot-v4-flash.img` → `fastboot boot` 验证能进系统、Shut Down 能断电（拔掉 USB 线再点，插着线断电后会被充电事件重新拉起）→ 再刷 `boot_a`。
- 02:13 构建完成，退出码 0，用了约 5 分钟。日志里有 `== kernel: patch macos-union-shutdown.patch` 和 `== kernel: component-ArmDTPlatform`。
- 新内核 `<output>/kernel/kernel.macho`：143753216 字节，sha256 `f393f430de822cb8f09f87494ccbfca9869e46f7f7cad81eb1159e9f9c970bd8`。里面有字符串 `retained for shutdown`，有符号 `__ZN13ArmDTPlatform11haltRestartEj` 和 `_armdt_platform_power_conduit`。`payload.json` 的 `kernel_sha256` 与它一致，启动参数里没有 `data-reset`，也没有 `autoreset`。`payload.img` 的 sha256 是 `e4b1748dd73362af4b48d5faf08b5433f836758ee712c032fda3bfde7782a388`。
- 打包（旧镜像保持原名，新镜像先叫 `.new.img`，上机验证后再改名）：
  - `python3 -I local-tools/make-bootimg-v4.py <output>/boot/boot.img ../uefi-sheng/Resources/Scripts/mkbootimg.py out/flash/boot-v4-payload.new.img <output>/payload/payload.img`，210903040 字节，sha256 `57bd2a2f5cd7657654a681b53f2527737977e5ea9497981ee687b321b51a8d9a`。
  - `python3 -I local-tools/make-flash-bootimg.py out/flash/boot-v4-payload.new.img out/flash/boot-v4-flash.new.img`，200417280 字节，sha256 `4cb441e019308ab3c0db1ec3b1083e975b5221a1fee8d6606e10099950655f01`，卷里剩余 8.5 MiB。
- 独立核对：新镜像的 UEFI 部分和头部与 `boot_a` 里的镜像逐字节相同。8 个文件里 `kernel.macho`、`.adt`、`.crypto-hmac.json`、`.gpuaddon`、`.trustcache` 变了，`.vroot`、`scratch-data.img`、`unixnu.toml` 没变，文件总量仍是 189504632 字节。两个新镜像里的文件互相一致。
- OS 镜像已从 scratchpad 的 `os-mount` 卸载。外置盘的构建镜像还挂着。
- 02:15 内存启动 `out/flash/boot-v4-flash.new.img`（`local-tools/boot-sheng.py`）：`Booting OKAY`，45 秒内 bootloader 没有回来。等用户反馈两件事：能否到登录页；拔掉 USB 线后点 Shut Down 是否断电。
- 验证通过后要做：平板进 fastboot → `fastboot flash boot_a out/flash/boot-v4-flash.new.img` → 旧镜像改名为 `.prev.img`、新镜像改回正式名字 → 提交驱动部分的改动。验证不通过：`boot_a` 里仍是 01:43 刷的旧镜像，重启即回到之前的状态。
- **用户 02:19 反馈：能正常 Shut Down。** 这是内存启动的新镜像，拔掉 USB 线后在登录页点 Shut Down，平板断电。同一条反馈里还说"现在还不能正常关机键开机"，具体看到什么还没问清。
- 02:19:59 fastboot 读数：`slot-successful:a: no`，`slot-unbootable:a: no`，`slot-retry-count:a: 6`，槽位 b 不变，电池 3883 mV。次数从 01:55 起没变，说明这段时间没有发生过"正常开机"（内存启动和手动进 fastboot 不扣）。也就是说，用户关机后如果按过电源键，引导程序并没有走到从 `boot_a` 启动这一步。
- 02:21:04 刷入：`fastboot flash boot_a out/flash/boot-v4-flash.new.img`，`Sending 'boot_a' (195720 KB) OKAY [4.488s]`，`Writing 'boot_a' OKAY [0.075s]`。刷完、启动前读到 `slot-successful:a: no`，`slot-unbootable:a: no`，`slot-retry-count:a: 7`。**这次读数证实：刷 `boot_a` 会把重试次数重置为 7；01:55 读到的 6 就是 01:43 那次正常启动扣掉的 1 次。**
- 02:21:16 `fastboot reboot`，60 秒内 bootloader 没有回来，`boot_a` 里的新镜像在运行。按上面的规律，这次启动后次数应为 6，下次进 fastboot 时复核。
- 镜像改名（02:23）：
  - `out/flash/boot-v4-flash.img`：sha256 `4cb441e019308ab3c0db1ec3b1083e975b5221a1fee8d6606e10099950655f01`，**现在在 `boot_a` 里**。
  - `out/flash/boot-v4-payload.img`：sha256 `57bd2a2f5cd7657654a681b53f2527737977e5ea9497981ee687b321b51a8d9a`，内存启动用，内核相同。
  - 上一版留作回退：`boot-v4-flash.prev.img`（`ae0d4179…`）和 `boot-v4-payload.prev.img`（`4abcc897…`），内核是没有关机修复的 `5e03486e…`。
  - `boot-v4-install.img` 没有重做，里面还是旧内核。它只在重置 Data 时用；要用新内核重置，需要重新生成（`./unixnu build payload … --kernel-arg data-reset=1`，之后再跑一次不带参数的 payload 把 `payload.img` 恢复）。
- 驱动部分的改动已提交（见 `git log`）。
- 待办：问清"按电源键不能正常开机"的现象，再做冷开机复测（拔线 → Shut Down → 等彻底断电 → 按住电源键约 3 秒）。
- **用户 02:28 反馈："开机键生效了，可以正常开关机。"** 冷开机复测通过：不接 Mac，按电源键能从 `boot_a` 进到 macOS；Shut Down 能断电。之前那句"还不能正常关机键开机"指的是刷入新镜像之前的情况，用户没有再描述具体现象。

**日常使用（2026-11-14 起）**
- 开机：按住电源键约 3 秒。先出现 UniXNU 菜单（倒计时 3 秒），然后自己进 macOS 登录页，不需要 Mac。
- 关机：在 macOS 里点 Shut Down。插着 USB 线或充电器时，断电后可能被充电事件重新拉起，这一点没有验证过。
- 回 fastboot：关机状态下按住电源键和音量下键约 10 秒。
- 重试次数：每次正常开机消耗 1 次，刷完 `boot_a` 后是 7 次。扣到 0 之后平板会停在 fastboot 或原厂 recovery，**在 recovery 里不要选清除数据**。
  - 读次数：平板进 fastboot，`fastboot getvar slot-retry-count:a`。
  - 补次数：`fastboot -s <序列号> set_active a`（用户 2026-11-14 已允许，只限槽位 a），或者重刷一次 `boot_a`。
  - 02:21 刷入后是 7 次；之后 02:21 的重启和用户的冷开机复测各用掉 1 次，按推算还剩 5 次左右，用户如果多开过几次就更少。下次进 fastboot 时读一次为准。
- `boot_a` 的内容和还原：
  - 现在（2026-11-14 19:01 起）：`out/flash/boot-v4-flash.img`，sha256 `c244f53d501c2031fa69dacec595e539f7a694b0db8385539ac37703fa187a44`。实测内存表、上游 #244 和 #245、关机修复都在里面。
  - 回到上一版：`fastboot flash boot_a out/flash/boot-v4-flash.prev.img`（sha256 `40234c20…`，18:18 刷过的那份：没有实测内存表，其余相同）。
  - 更早的两份：`boot-v4-flash.prev2.img`（`4cb441e0…`，有关机修复，没有上游两条内存修复）、`boot-v4-flash.prev3.img`（`ae0d4179…`，没有关机修复）。
  - 对应的内存启动镜像（200 MiB 卷，不能刷）按同样的顺序叫 `boot-v4-payload.img`（`a9cb0b31…`）、`.prev`（`dd5d2475…`）、`.prev2`（`57bd2a2f…`）、`.prev3`（`4abcc897…`）。
  - 还原成原厂：`fastboot flash boot_a out/flash/sheng_global_images_OS3.0.305.0.WNXMIXM_16.0/images/boot.img`（sha256 `0a0d6aa6…`）。只还原这一个分区安卓仍然起不来：`init_boot_a` 已擦除，`vendor_boot_a` 没有 ramdisk，userdata 是 macOS 的。
  - `vbmeta_a` 没有动过，一直是原厂的。
- 更新内核或 payload 之后重新刷入的流程（都在 `UniXNU/` 下执行）：
  1. 接上外置盘，`hdiutil attach /Volumes/12873/UniXNU-build.sparsebundle`。
  2. 把 OS 镜像只读挂到系统盘上的一个目录：`hdiutil attach -readonly -nobrowse -mountpoint <目录> /Volumes/UniXNUBuild/unixnu-out/ipsw/26C5035r/141-22233-021.dmg`。
  3. `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`（改了补丁序列也只用了约 5 分钟）。
  4. `python3 -I local-tools/make-bootimg-v4.py <output>/boot/boot.img ../uefi-sheng/Resources/Scripts/mkbootimg.py out/flash/boot-v4-payload.new.img <output>/payload/payload.img`
  5. `python3 -I local-tools/make-flash-bootimg.py out/flash/boot-v4-payload.new.img out/flash/boot-v4-flash.new.img`
  6. 平板进 fastboot，先内存启动验证：`python3 -I local-tools/boot-sheng.py out/flash/boot-v4-flash.new.img`。
  7. 验证通过后再进 fastboot：`fastboot flash boot_a out/flash/boot-v4-flash.new.img`，`fastboot reboot`。然后把旧镜像改名为 `.prev.img`，新镜像改回正式名字。
  8. 卸载 OS 镜像（`hdiutil detach <目录>`）。

## 9. 待处理问题（按用户要求先记录，之后处理）

**睡眠不工作（用户 2026-11-14 02:31 报告，还没有调查）**
- 现象（用户原话）："选择系统中的sleep按键和快速单击开机键无法进入睡眠模式"。也就是两条路都不行：在 macOS 里选 Sleep；快速单击电源键。
- 当时的环境：`boot_a` 里是 `out/flash/boot-v4-flash.img`（sha256 `4cb441e0…`，内核 `f393f430…`，带关机修复）。开机和 Shut Down 正常。
- 还不知道的：选 Sleep 之后屏幕有没有变化（完全没反应、黑一下又亮、还是卡住）；单击电源键时系统有没有任何反应；有没有日志。处理时先向用户问清这几点。
- 线索，都没有验证过：
  - 上游的设备记录里，sheng 的睡眠和唤醒本来就没有测过：`docs/zh/devices/sheng-4545189wj.md` 第 351-356 行（iPadOS 27 睡眠时关背光"not verified"）、第 531 行（"sleep and wake, idle power and recovery are not tested"）、第 765-796 行（挂起和恢复、外设电源各自的覆盖情况）。`sheng-3364789753.md` 有同样的条目。
  - `boot_a` 里的启动参数没有和睡眠相关的项（只有一个 `gpu-power=9`）。
  - 这次的关机修复只给平台驱动加了关机和重启（`haltRestart` 里的 PSCI SYSTEM_OFF、SYSTEM_RESET），没有涉及睡眠。
  - 参考仓库也没有做睡眠，没有现成补丁可拿：`../UniXNU_macOS/docs/zh/drivers/arm-dt-platform.md:16` 写的是"睡眠和唤醒需要另行接入 CPU 与外设恢复"。
- 用户的要求："先落handoff，之后处理"。所以这里只记录，不动代码。

**macOS 只看到约 6 GB 内存，内存紧张时卡死（用户 2026-11-14 报告；已查上游，还没改代码）**
- 现象（用户原话）："物理内存只有6g，没有用满16g，然后没有swap，导致系统因为内存不足卡住了"。
- 6 GB 的来源有两处限制，都是按 8 GiB 版 sheng 写的：
  - 内核窗口：`../UniXNU-sheng/board.toml` 第 245-250 行，macOS 的 `owned_memory_size = 0x180000000`（6 GiB），从 `0x880000000` 开始。注释写的是"6 GiB is the most the 4 KiB bootstrap tables map"。窗口外的空闲内存由内核逐页收编（上游 #212，第 254-259 行，`owned_memory_outside_ranges = 8`），维护者那台机器收编了 458 MiB。
  - UEFI 内存表：`../uefi-sheng/.../MemoryMapLib.c` 第 54-67 行是静态表，DRAM 只写到 `0xA00000000`（bank 1 low 0.5 GiB + bank 1 high 5 GiB，加上低 2 GiB 里的空隙）。这份表取自维护者 8 GiB 机器的 SMEM 表，这台 16 GiB 机器多出来的内存 UEFI 不知道，内核也就拿不到。这台机器真实的 DRAM 布局还没读过。
- 上游现状（2026-11-14 用 `gh` 查，主仓库合到 #245，设备仓库合到 #95）：
  - 没有已合并的 16 GiB 支持。其他 16 GiB 机型也停在 6 GiB，见 `docs/.vitepress/device-records/elden-tay0123.toml` 第 130 行（"Keep 6GiB ... do not advertise a flat 16GiB"）。
  - 待合并：`uefi-sheng` #6（Jelly10086，head `ac0466db`）让 SEC 从 ABL 设备树的 `/memory` 和 `/reserved-memory` 推出内存表。但它只在 `ddr_size == 8`、所有范围都在 `0xA00000000` 以下时生效，其他情况退回静态表，所以对这台 16 GiB 机器不起作用。思路可以借来扩到 16 GiB。
  - 待合并：`UniXNU-sheng` #96（Jelly10086，head `085f67e1`）把窗口外可收编的范围从 8 个放宽到 64 个。只改 `board.toml` 和 `porting.toml`，不扩大内核窗口。
- swap：
  - 本地已有 `macos-vm-volume.patch`（11-10 起在 `series` 第 29 行），它把 `/System/Volumes/VM` 指到 Data 卷的 `/private/var/vm`，修的是"swap 文件 EROFS、压缩器满了以后桌面卡死"。这台机器上 swap 实际有没有生效，还没查（`sysctl vm.swapusage`）。
  - 上游 11-14 新合、本地还没有的两条：#244 `macos-4k-zone-va-budget.patch`（zone map 从 24 GiB 降到 16 GiB 虚拟地址，给压缩器和共享 I/O 留出地址空间）和 #245 `macos-swapin-io-priority.patch`（换入时临时提高 I/O 优先级；只在 `native-apfs-root` 启动时默认打开，其他情况要加 `vm-swapin-io=1`）。两条的 PR 都写着在 sheng 上 Device Test PASS。本地分支落后上游 `main` 9 个提交，其中 #238 就是已经摘进来的关机补丁。
- 第 1 步（用户同意：先带上 #244、#245 缓解卡死，内存仍是 6 GB）的进度：
  - 已做：上游 `main` 合进本地分支（合并提交 `ec761fd`，无冲突；补丁序列末尾多了 `macos-4k-zone-va-budget.patch` 和 `macos-swapin-io-priority.patch`，关机补丁只出现一次）。
  - 已做：`unixnu.local.toml`（不进 git）加了 `kernel_args = ["vm-swapin-io=1"]`。两个仓库里都没有任何地方设置 `native-apfs-root`，所以 #245 不加这个参数就是关的。加上后命令行 877 字节，上限 1000。
  - 外置盘（PSSD T7）中途又从 Mac 上断开过，残留的构建盘镜像设备用 `hdiutil detach disk6 -force` 清掉。用户接回后 exFAT 分区 `12873` 过了一会儿才挂上（`diskutil mount disk4s3`）；`diskutil verifyVolume /Volumes/UniXNUBuild` 通过，旧内核 sha256 仍是 `f393f430…`。
  - 18:06 重建完成：日志里 `macos-4k-zone-va-budget.patch`、`macos-swapin-io-priority.patch`、`macos-union-shutdown.patch`、`macos-vm-volume.patch`、`sheng-text-fixup-verified-pagein.patch` 都打上了，ArmDTPlatform 驱动 18:04 重新打补丁并编译。新内核 `kernel/kernel.macho` sha256 `33d294c83022a67b1ecfe4a8dd46564ca2b66169e11bc21c647e3981f2277b67`，`payload/payload.img` sha256 `8a36fe56…`。启动参数第一项是 `vm-swapin-io=1`。
  - 18:07 打包：`out/flash/boot-v4-payload.new.img`（sha256 `dd5d2475…`）和 `out/flash/boot-v4-flash.new.img`（sha256 `40234c20756ae087429988f78f638e7b43d8def5872ef729514b401ab3493298`，190 MiB 卷，8 个文件）。核对过：固件部分和头部与 `boot_a` 里的镜像逐字节相同，`unixnu.toml` 里有 `vm-swapin-io=1`，没有 `data-reset`。OS 镜像已卸载。
  - 18:07 fastboot 读数：槽位 a，`slot-retry-count:a: 4`，`slot-successful:a: no`，`slot-unbootable:a: no`，`unlocked: yes`，电池 4400 mV（02:19 是 3883 mV；这次是插着 USB 线读的，能不能说明 macOS 下在充电还不能下结论）。
  - 18:07:30 内存启动 `boot-v4-flash.new.img`：`Booting OKAY`，45 秒内引导程序没有回来。**还没刷 `boot_a`**，等用户确认能到登录页。
  - 用户确认后要做：平板再进 fastboot，`fastboot flash boot_a out/flash/boot-v4-flash.new.img`，`fastboot reboot`；旧镜像改名 `.prev.img`，新镜像改回正式名字。进系统后用 `sysctl vm.swapusage vm.swapin_iotier_boost vm.swapin_iotier_grants` 看 swap 和 #245 是否生效。
  - 用户随后反馈"当前macos进系统后…"，说明内存启动的新镜像能进系统。但发来的 `sysctl` 截图是在 Mac 上跑的，不是平板：主机名 `huanmeng-Air`，`hw.memsize` 17179869184（16 GiB），swap 12288M 已用 11285M，两个 `vm.swapin_iotier_*` 是 unknown oid。平板上的 swap 和 #245 状态仍然没有读数。`boot_a` 还没刷新镜像。

**用户想把内存拉满 16 GB（2026-11-14 提出；已查代码，还没有设计，没动代码）**
- 用户原话："当前内存仍为6gb，我想尝试拉满16gb"。
- 现有代码做不到的原因，除了前面两处限制，还有第三处：内核收编窗口外内存的补丁只接受窗口**下方**的内存。`window-outside-memory-adoption.patch` 里读取列表的地方写着"Only memory below the span"，条件是 `base < gDramBase || end > gPhysBase` 就跳过。窗口从 `0x880000000` 起 6 GiB，到 `0xA00000000`。16 GiB 机型多出来的内存按高通的惯例在 `0xA00000000` 以上（推测是到 `0xC00000000`，**这台机器没有实测过**），正好在窗口上方。
- 所以要做三件事：
  1. 读出这台机器真实的 DRAM 和保留区布局。
  2. UEFI 内存表按这个布局写（`uefi-sheng` #6 的做法可以借用，它现在只认 8 GiB）。
  3. 内核能用上窗口以外的内存。可选的路：把窗口挪到 DRAM 顶部，下面的全部走收编（收编区的地址跨度会从 2 GiB 变成约 40 GiB，内核地址空间够不够没算过）；或者改补丁让它也收编窗口上方的内存；或者把窗口本身做大（要改 4 KiB 引导页表）。
- 读布局的两个办法，都没试过：
  - 设备仓库有一个只从内存启动的 Linux 日志读取器（`../UniXNU-sheng/package/linux-log/`，主线内核加 busybox，通过 USB 串口给一个 shell，不挂载也不写 UFS）。在里面读 `/proc/device-tree/memory` 和 `/proc/iomem` 就是引导程序给的真实布局。问题：它是 v0 头加附带 DTB 的镜像，这台机器不接受 v0，要另想打包办法。它同时能用 `scripts/read-sheng-log.py` 取回 macOS 内核的启动日志，对查充电、USB、swap 都有用。
  - 做一个诊断用的 UEFI，把引导程序传来的设备树里的内存范围打到屏幕上，用户录屏，再用 `local-tools/ocr-frames.swift` 识别。
- 风险：内存表写错，UEFI 会在启动时崩（这台机器在 `0x8B9D00000` 出过一次）；把固件占用但能读的内存交给内核，可能破坏内存里的数据，进而写坏 Data 卷。所以每一步都只从内存启动验证，不刷分区。
- 上游没有人做成：其他 16 GiB 机型的记录是"Keep 6GiB … do not advertise a flat 16GiB"。
- 规模上这是多仓库、方向不确定的工作，要先写设计、用户确认后再动手。
- 第 0 步，读真实内存布局（用户 18:15 同意"可以，开始吧"；只读，不写分区）：
  - 18:18 先把带上游两条内存修复的新镜像刷进了 `boot_a`：`out/flash/boot-v4-flash.img`，sha256 `40234c20756ae087429988f78f638e7b43d8def5872ef729514b401ab3493298`，刷完重试次数 7。上一版改名 `boot-v4-flash.prev.img`（`4cb441e0…`，有关机修复、没有内存修复），再上一版是 `boot-v4-flash.prev2.img`（`ae0d4179…`）。payload 镜像同样顺延（`boot-v4-payload.img` 是 `dd5d2475…`）。
  - `fastboot getvar all` 不报内存信息。Linux 日志读取器没有试：材料本地没有，而且是 v0 镜像。
  - 改用诊断固件：`local-tools/diag/abl-memory-dump.patch` 给 `UniXNURamDiskDxe.c` 加一段输出，把引导程序设备树里的 `/memory`、保留块和 `/reserved-memory` 逐行打到屏幕日志上（每 10 行停 5 秒，每行带校验值）。`local-tools/diag/read-abl-memory.py` 读识别出来的文字，校验值不对的行丢弃。补丁只在构建诊断镜像时打上，不合进任何分支。
  - 诊断镜像：`out/flash/boot-v4-diag-ablmem.img`，sha256 `14c4e2e16b1451e206c9f2a96a3b918e1436665fb34ac62c8c3e5980c7653672`。payload 和日常镜像逐字节相同，只有固件不同；打完输出后照常进 macOS。只用 `local-tools/boot-sheng.py` 从内存启动，不刷。
  - 构建诊断镜像的做法：`git apply local-tools/diag/abl-memory-dump.patch`，`./unixnu build firmware --os macos-27 --uefi ../uefi-sheng`，`./unixnu bootimg --os macos-27 --dtb <output>/tree/build/sheng/sheng.dtb -o <output>/boot/boot-diag.img`（一定要带 `-o`，否则覆盖 `<output>/boot/boot.img`；`boot.json` 仍会被改写，事后用 `boot.good.json` 还原），再用 `make-bootimg-v4.py` 打成 v4。然后 `git checkout` 还原驱动。
  - 固件构建不能逐字节复现：还原驱动后重建，`SILICIUM_UEFI.fd` 是 `d187f851…`，不是真机验证过的 `36bd589f…`，原因没查。验证过的那份备份在 `out/flash/SILICIUM_UEFI.good-36bd589f.fd`，已拷回 `../uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/FV/`。`<output>/boot/boot.img`（`26d709b2…`）没被动过，日常打包仍然用它。
  - 18:25 内存启动诊断镜像，用户录屏 `data/mp4/IMG_6389.MOV`（74 秒，不进 git）。输出在屏幕上清晰可读。
  - 读数的做法：`ffmpeg -i data/mp4/IMG_6389.MOV -vf "fps=2,crop=1800:2000:470:90,scale=iw*2:ih*2:flags=lanczos" <目录>/c%04d.png`（整帧识别读不出小字，要裁到文字区域并放大两倍），`swift local-tools/ocr-frames.swift --boxes <目录>/c*.png > boxes.tsv`（要关沙箱），`python3 -I -B local-tools/diag/read-abl-memory.py boxes.tsv`。
- **实测结果：这台平板是 12 GiB 内存，不是 16 GiB。** 引导程序设备树里 `ddr_size` 是 `0xC`（55 帧读到同一个值）。`/memory` 一共 9 段，每段的校验值都对，加起来 `0x2EBAA0000`（11.682 GiB），和固件自己打印的 `ABLMEM total 02EBAA0000` 一致（66 帧）：

  | 起 | 止 | 大小 |
  | --- | --- | --- |
  | `0x080000000` | `0x080E00000` | 14 MiB（就是 hypervisor 保留区，no-map） |
  | `0x0811D0000` | `0x0D8000000` | 1390.19 MiB |
  | `0x0D8140000` | `0x0D8160000` | 0.12 MiB |
  | `0x0D8800000` | `0x0D8800000` | 0（长度为 0 的一项） |
  | `0x0E7CB0000` | `0x100000000` | 387.31 MiB |
  | `0x880000000` | `0x8B9D00000` | 925 MiB |
  | `0x8B9F00000` | `0x8BBD00000` | 30 MiB |
  | `0x8C0000000` | `0x980000000` | 3072 MiB |
  | `0x980000000` | `0xB00000000` | 6144 MiB |

  - DRAM 顶端是 `0xB00000000`。第二个 bank 是 `0x880000000` 到 `0xB00000000` 共 10 GiB，中间有两个引导程序不给的洞：`0x8B9D00000`–`0x8B9F00000`（2 MiB）和 `0x8BBD00000`–`0x8C0000000`（67 MiB）。之前 UEFI 在 `0x8B9D00000` 崩溃，正是第一个洞的起点。
  - `/reserved-memory` 读到 32 个有固定地址的保留区（校验通过），全部在低 4 GiB 里，bank 1 里没有固定保留区。没有固定地址的保留区（CMA、各种 heap）不带校验值，名字有识别错误，只作参考。保留块（`ABLMAP`）一项也没读到，是没有还是没识别出来没有确认。固件报 `ABLEND lines 75`。
  - 屏幕上还有 uefi-sheng 自带的 `ShengBootMemoryDxe` 的输出：`SHENGMEM: DT has 8 memory ranges and 35 reserved ranges`，并加回了三段低地址内存共 `0x7000000` 字节。也就是说上游固件里已经有一个读这棵设备树的驱动。
- 这对"拉满内存"的含义（都是读代码得出的，没有上机验证）：
  - 目标从 16 GiB 变成约 11.7 GiB。现在是 6 GiB 窗口（`0x880000000`–`0xA00000000`，其中 UEFI 表只列了 0.5 GiB + 5 GiB）加低 bank 收编的几百 MiB。
  - 窗口内白白没用上的：`0x8A0000000`–`0x8B9D00000`（413 MiB）和 `0x8B9F00000`–`0x8BBD00000`（30 MiB）。只改 UEFI 静态表就能拿回来，不用动内核。
  - 窗口上方的 4 GiB（`0xA00000000`–`0xB00000000`）现有内核用不上：收编补丁只收窗口下方的内存。
  - 不能简单地把整张表写全：DarwinBoot 的 `AllocateSpan` 会自动把窗口放到"6 GiB 内可用内存最多"的位置，并列时取最低地址（`MemoryWindow.h` 的 `DarwinWindowStart`），结果是 `0x8C0000000`。这样 `0x880000000`–`0x8BBD00000` 就落到窗口下方，收编区的地址跨度从 2 GiB 变成约 34 GiB。内核给收编区留的虚拟地址是"静态区下方 4 GiB 再往下一个跨度"（`arm_vm_init.c` 的 `arm_vm_outside_va`），这个内核的地址空间很紧，34 GiB 很可能放不下或者挤掉内核自己的分配。
  - 所以要用上那 4 GiB，内核一定要改，三条路：收编补丁支持窗口上方的内存；把窗口从 6 GiB 放大到 10 GiB（`scripts/unixnu/devicetree.py` 允许到 8 GiB，`board.toml` 说 4 KiB 引导页表最多映射 6 GiB，这个上限在哪还没查）；或者把窗口挪到顶部、收编补丁支持多个不相连的跨度。

**内存 A 步：UEFI 内存表按实测布局改（用户 2026-11-14 选 A；验证通过，19:01 已刷进 `boot_a`）**
- 改动（`../uefi-sheng` 工作区，未提交）：`MemoryMapLib.c` 的 "DRAM bank 1 low" 从 `0x880000000 + 0x20000000` 改成 `0x880000000 + 0x39D00000`（到 `0x8B9D00000`），新增 "DRAM bank 1 mid" `0x8B9F00000 + 0x01E00000`。"DRAM bank 1 high" 没动，仍到 `0xA00000000`：如果把 `0xA00000000` 以上也列进去，加载器会把窗口挪走（见上一条）。预期多出约 443 MiB，窗口仍从 `0x880000000` 起。
- 没有改的一处不一致：静态表的 "DRAM gap 0xE671D000" 从 `0xE671D000` 开始，而引导程序的 `/memory` 在这一带从 `0xE7CB0000` 才开始，中间 22.6 MiB 引导程序没有算作内存。这是上游原样，一直这样启动，这次不动，留给 B 步一起处理。另外 `0xD4D00000`–`0xD8000000` 在引导程序那里是 modem 的 no-map 保留区（没有标 disabled），静态表把它当空闲内存，也是上游原样。
- 构建产物：固件 `SILICIUM_UEFI.fd` sha256 前缀 `9b21a09e`（备份 `out/flash/SILICIUM_UEFI.mem12g-9b21a09e.fd`；当时构建目录里就是这一份，不是验证过的 `36bd589f`。19:55 起构建目录里换成了路线一的 `e168abab`，见第 9 节"路线一的主机部分"）。v0 镜像 `<output>/boot/boot-mem12g.img`（`<output>/boot/boot.img` 没动）。`out/flash/boot-v4-payload.mem12g.img`（sha256 `a9cb0b31…`）和 `out/flash/boot-v4-flash.mem12g.img`（sha256 `c244f53d501c2031fa69dacec595e539f7a694b0db8385539ac37703fa187a44`）。payload 卷和 `boot_a` 里的只差卷标时间那 4 个字节。
- 18:41 fastboot 读数：槽位 a，重试 7（18:18 刷入后没有发生过正常开机），电池 4361 mV。18:41:55 内存启动 `boot-v4-flash.mem12g.img`：`Booting OKAY`，45 秒内引导程序没有回来。**没有刷 `boot_a`。**
- 结果（用户 2026-11-14 报告并拍了平板屏幕）：进了系统。平板终端里 `hw.memsize` 是 6848757760（6.38 GiB）；活动监视器显示物理内存 6.38 GB、已用 4.72 GB、联动内存 2.59 GB、已压缩 279.3 MB、已用交换 0，内存压力是绿色。
- 同一张照片里的其他读数：`vm.swapin_iotier_boost: 1`，说明上游 #245 的补丁在内核里并且开着（`vm-swapin-io=1` 生效）。`vm.swapusage: total = 0.00M`：当时没有内存压力，还没有建交换文件，所以交换能不能用仍然没有验证。`vm.swapin_iotier_grants` 用户敲错了名字，没读到。
- `../uefi-sheng` 的改动已在本地提交：分支 `local/sheng-12g-memory-map`，提交 `5dfcc572`，没有推送。
- 刷入（用户 2026-11-14 让平板进了 fastboot 并要求刷）：
  - 刷前读数：槽位 a，重试 6，`successful: no`，`unbootable: no`，`boot_a` 大小 `0xC000000`，电池 4326 mV。
  - 19:01:43 `fastboot flash boot_a out/flash/boot-v4-flash.mem12g.img`：`Sending 'boot_a' (195720 KB) OKAY [4.508s]`，`Writing 'boot_a' OKAY [0.071s]`。刷完重试 7。
  - 19:01:55 `fastboot reboot`，60 秒内引导程序没有回来。屏幕上是否进了登录页、内存是否仍是 6.38 GB，还没有用户的确认。
- 刷完后的文件名：
  - `out/flash/` 里 `.mem12g` 的两份改成了正式名字，旧的依次改成 `.prev`、`.prev2`、`.prev3`，没有删任何一份（哈希见第 8 节"日常使用"）。
  - `<output>/boot/boot.img` 现在就是这份固件的 v0 镜像（sha256 `35f03ec4…`，固件 `9b21a09e…`），用 `./unixnu bootimg` 重新生成并和 `boot-mem12g.img` 逐字节比过，一样；`boot.json` 和它对应，`boot.good.json` 是它的副本（以后带 `-o` 打包后用它还原 `boot.json`）。上一份验证过的留作 `boot.good-36bd589f.img` 和 `boot.good-36bd589f.json`。

**内存 B 步：用上窗口上方的 4 GiB（用户 2026-11-14 要求推进；在查代码，还没有设计）**
- 6 GiB 上限的出处找到了：`patches/xnu-12377/native-4k-bootstrap-capacity.patch` 把 `osfmk/arm/pmap/pmap.h` 的 `BOOTSTRAP_TABLE_SIZE` 定成 16 页，注释是"Native 4 KiB: two roots plus up to seven L2 pages per 6 GiB mapping"。引导页表要给整个窗口建两份映射（V=P 和内核线性映射），每个 L2 页管 1 GiB：N GiB 的窗口要 `2 + 2 × (N + 1)` 页，6 GiB 是 16 页，10 GiB 是 24 页。`arm_vm_init.c` 里有检查，不够会 panic："BOOTSTRAP_TABLE_SIZE too small for memory config"。
- 工具侧的上限：`scripts/unixnu/devicetree.py` 第 321 行，`owned_memory_size` 只允许 256 MiB 到 8 GiB。
- 内核地址空间：这个配置的 `VM_MIN_KERNEL_ADDRESS` 是 `0xffffffe000000000`，`VM_MAX_KERNEL_ADDRESS` 是 `0xfffffffbffffffff`（`osfmk/mach/arm/vm_param.h` 第 267、269 行），总共 112 GiB。窗口的线性映射从 `gVirtBase` 起，窗口每大 1 GiB 就多占 1 GiB。zone map、内核堆各段具体占多少、还剩多少，没算过。收编补丁的说明里提到过在 sheng 上内核堆几段一共只有约 3 GiB 可分，所以地址空间是这件事的主要风险。
- 已打好补丁的内核源码在 `<output>/tree/.cache/xnu-work/`，查代码看这里。
- 加大窗口不划算（查代码得出，没有上机试）：窗口每大 1 GiB，内核地址空间要付两份。一份是静态区（`arm_vm_init.c` 第 2254 行，`static_memory_end = physmap_base + mem_size + …`），一份是压缩器的预留（`vm_compressor.c` 第 865–870 行，这个布局下 `compressor_pool_size = max_mem`）。10 GiB 窗口比现在多占约 8 GiB，正好是上游 #244 把 zone map 从 24 GiB 减到 16 GiB 腾出来的量，各个堆又会回到 #244 之前只有约 3 GiB 可分的状态。
- 收编不占这部分地址：收编区的映射地址在静态区下方那 64 GiB 没人用的地址里（收编补丁的 `arm_vm_outside_va`）；各堆的地址划分（KMEM 阶段）在收编（EARLY_BOOT 阶段）之前，收编进来的内存不会让压缩器多占地址。
- 收编现在的限制（`profiles/os/macos-27.3-26C5035r/patches/xnu-12377/window-outside-memory-adoption.patch`）：只认窗口下方的内存（`end > gPhysBase` 的跳过）；所有内存段合成一个区，这个区超过 4 GiB 就整个放弃；上游机器上实测只收编到 458 MiB，其余被探测拒绝。窗口上方收不了的根源在 VM 层：`vm_resident.c` 里按页号找页的 radix 树只覆盖 `[pmap_first_pnum, vm_pages_first_pnum)`，页号在页数组之后的 `vm_page_find_canonical` 直接返回空。
- 加载器不用改就会列出窗口上下两边的空闲内存（`MemoryWindow.h` 的 `DarwinOutsideRanges`，留最大的 8 段）。但窗口位置没有选项可以指定：`DarwinWindowStart` 只在内存表每一段的起点上找，取可用内存最多的，一样多取地址低的。加载器的这些函数有主机上能跑的测试（`drivers/DarwinBoot/Test/test-memory-window.py`、`test-memory-outside.py`）。
- 由此得出的三条路线（2026-11-14 发给用户；用户选了"先路线一再路线二"。路线一的设计在 `docs/superpowers/specs/2026-11-14-memory-top-window-design.md`，等用户确认）：
  1. 窗口挪到最高的 6 GiB（`0x980000000`–`0xB00000000`，引导程序给的是一整块），收编它下面的 `0x880000000`–`0x980000000`（正好 4 GiB，卡在收编上限上）。内核不用改；加载器要加一个指定窗口位置的选项；低端那 2 GiB 要用 `owned_memory_outside_reserved` 整段挡掉，否则合成的区超过 4 GiB、收编整个失效，代价是丢掉低端现在收编到的约 0.45 GiB。预计约 9.9 GiB。
  2. 在 1 的基础上让收编支持多个区，把低端的 0.45 GiB 拿回来，预计约 10.4 GiB。要改内核（pmap 的每页表、`pa_valid`/`pa_index`/`pai_to_pa`、映射地址）。
  3. 窗口不动，让内核能收编窗口上方的内存。要改 VM 的 radix 树和页查找，再加多个区，改动最大。
- 上限：引导程序给的总量是 11.68 GiB，低端 2 GiB 里固件自己占了很多，实际能拿到的大约 10.4 GiB 上下，到不了 12。

**开机后终端卡在 `login`，不出提示符；同一次开机里键盘盖也掉线（用户 2026-11-14 在 19:02 到 19:20 之间报告，原因不明）**
- 经过：19:01 刷入带实测内存表的镜像并从 `boot_a` 启动。用户说"新开机打开的终端有点卡死了"，后来说"一直卡着没恢复，键盘触控板也掉了"，并拍了屏幕。
- 照片里能确定的：
  - 终端窗口标题是 `Terminal — login — 120×30`：前台进程是 `login`，还没有换成 shell。窗口里是恢复出来的旧内容，最后一行是 `[Restored 13 Nov 2026 at 10:13:19 AM]`，后面没有 `Last login` 也没有提示符。
  - 同一个窗口里上一次恢复（`[Restored 13 Nov 2026 at 10:06:48 AM]`）后面有 `Last login: Fri Nov 13 10:06:31 on console` 和提示符，说明上一次开机时终端是正常的。那一次应该是 18:41 之后、19:01 之前从 `boot_a` 的正常开机（19:01 读到重试次数是 6，少了 1 次）。
  - 界面没有整体卡死：前台是活动监视器，能切换。物理内存 6.38 GB，已用 5.10 GB，联动 2.93 GB（上一张照片是 2.59 GB），已压缩 383.7 MB，已用交换 0，内存压力绿色。
  - 系统时钟不对：程序坞日历和小组件显示 11 月 13 日周五，终端里的时间是上午 10 点多，实际是 11 月 14 日晚上 7 点。三次登录时间（10:06:34、10:06:31、这次恢复在 10:13:19）都在 10:06 前后，像是每次开机时钟都从差不多同一个时刻起算。这是从照片推的，没有验证，也不知道和卡住有没有关系。
- 不知道的：`login` 卡在哪一步；新开一个终端窗口是否也卡；键盘盖是什么时候掉的、重新吸上去能不能恢复；重启后能不能复现。
- 和这次镜像的关系：19:01 刷的镜像和 18:41 内存启动、用户跑过 `sysctl` 的那份内容相同（payload 卷只差大小和卷标时间），所以没有证据说明是这次刷入引起的。也没有证据排除。
- 已请用户做的（都能用触屏完成）：新开终端窗口看是否也卡；在活动监视器里找 `login` 进程；重新吸一次键盘盖；必要时重启看能否复现。
- 第二次开机（也在 19:02 到 19:20 之间，具体时间没有记）："重启登录后，系统彻底卡死了"。有没有 panic 画面、卡死前做了什么，用户没说。前面请用户做的几步没有回报结果。
- 到这里的统计：刷入实测内存表后从 `boot_a` 开机 2 次，2 次都出问题（一次终端卡在 `login` 加键盘盖掉线，一次整机卡死）。同样内容的镜像 18:41 从内存启动那一次，用户跑了 `sysctl`、拍了照，没有报问题，用了多久不知道。
- 三个候选原因，都没有证据定论：
  1. 实测内存表新列入的内存（`0x8A0000000`–`0x8B9D00000` 和 `0x8B9F00000`–`0x8BBD00000`，共约 443 MiB）里有不能用的部分。引导程序把它们列为普通内存，上游机器也在用到 `0x8BB300000` 为止的这一带，但夹在两个空洞之间的那 30 MiB 只有这台机器有。
  2. 18:07 起换的新内核。上游合并只带来三处内核和系统改动：#244（zone map 地址 24 → 16 GiB）、#245（换入的 I/O 优先级）、#238（关机时保持根文件系统挂载，之前已经单独拿过）。这份内核用的时间很短。
  3. 原来就有的不稳定。用户最早报过"内存不足卡住"和键盘盖待机失效。
- 对比用的镜像都在 `out/flash/`，从内存启动，不动 `boot_a`：
  - `boot-v4-payload.prev.img`（`dd5d2475…`）：新内核，旧内存表。先试这个：它卡，就不是内存表的事；它稳，内存表嫌疑最大。
  - `boot-v4-payload.prev2.img`（`57bd2a2f…`）：旧内核，旧内存表，用户用了一整天的那份。
- `boot_a` 现在仍是带实测内存表的那份（`c244f53d…`）。对比出结果之前没有改回去。
- 对比第一步（2026-11-14 19:20）：
  - 用户强制关机后进了 fastboot。读数：槽位 a，重试 5（19:01 刷完是 7，之后两次正常开机各扣 1），`successful: no`，`unbootable: no`，电池 4302 mV（18:41 是 4361，19:01 是 4326，macOS 下一直在掉电）。
  - 19:20:59 内存启动 `out/flash/boot-v4-payload.prev.img`（新内核，旧内存表）：`Booting OKAY`，45 秒内引导程序没有回来。没有刷任何分区。
  - 用户回报（19:21 之后，拍了屏幕）：终端正常，标题是 `-zsh`，有提示符；"但是触控板鼠标还是会掉"。照片里键盘盖在。
  - 这次的读数：`hw.memsize: 6384238592`（5.95 GiB），比带实测内存表时的 6848757760 少 464519168 字节，正好是实测内存表新列入的 443 MiB。`vm.swapin_iotier_boost: 1`，`vm.swapin_iotier_grants: 0`（这次名字敲对了），`vm.swapusage` 的 total 仍是 0。活动监视器：物理内存 5.95 GB，已用 4.68 GB，联动 3.07 GB，已压缩 484.8 MB，已用交换 0，内存压力绿色。
  - 同一张照片里终端窗口的历史补上了 19:01 那次开机的后续：`[Restored 13 Nov 2026 at 10:13:19 AM]` 后面有 `Last login: Fri Nov 13 10:06:46 on ttys000` 和 `Restored session: Fri 13 Nov 2026 10:11:07 PST`，说明那次 `login` 后来走完了，只是慢了很久。另外三次开机终端都是开机后 20 到 80 秒内恢复（时钟 10:06:48、10:07:20），那一次是 10:13:19，晚了约 6 分钟；而且那次 `Last login` 显示的是上一次开机的终端登录，不是本次开机的控制台登录，说明登录窗口那次登录的记录当时也没写进去。整机卡死的那次开机在窗口里没有留下任何记录。
  - 到这里的对照表（同一份内核）：

    | 时间 | 内存表 | 启动方式 | 结果 |
    | --- | --- | --- | --- |
    | 18:41 | 实测 | 内存启动 | 终端正常，跑了 `sysctl`；用了多久不知道 |
    | 18:41 到 19:01 之间 | 旧 | 从 `boot_a` | 终端正常，至少运行了约 5 分钟 |
    | 19:01 | 实测 | 从 `boot_a` | 终端晚 6 分钟才恢复，`login` 卡很久，键盘盖掉线 |
    | 19:02 到 19:20 之间 | 实测 | 从 `boot_a` | 登录后整机卡死 |
    | 19:21 | 旧 | 内存启动 | 终端正常；触控板掉线 |

  - 能下的结论：触控板和键盘盖掉线和实测内存表无关（旧内存表也掉，实测内存表之前用户就报过）。卡住和卡死只在"实测内存表 + 从 `boot_a` 启动"的两次里出现；18:41 那次用的是同一份镜像文件，从内存启动没有出问题。样本太少，还分不清是实测内存表的问题、和启动方式有关，还是碰巧。
  - 查过、没有找到机制的：引导程序放 ramdisk 的位置在低端（之前录屏读到过 initrd 结尾在 `0xB7FFEADC`，落在固件内存表保留的 `0xA8000000`–`0xB8000000` 里），不在新列入的内存里；固件自己的分配从内存顶往下取，也不在那里。
  - 下一步的想法（已告诉用户，等用户决定）：`boot_a` 先刷回 `boot-v4-flash.prev.img`；新列入的那 443 MiB 放到路线一里验证。路线一的窗口在顶部，这 443 MiB 在窗口外面，内核用不用它只由板级配置的保留列表决定，所以可以先挡掉它跑一轮、再放开跑一轮，一次只变一件事。
- **路线一的主机部分（2026-11-14 19:50 到 20:05，都在 Mac 上，没有动平板）**。计划是 `docs/superpowers/plans/2026-11-14-memory-top-window.md`，Task 1 到 5 做完，Task 6（上机）没做。
  - 改了四处，都只在本地分支提交，没有 push：
    - 加载器（子模块 `drivers/DarwinBoot`，分支 `local/window-floor`，提交 `bf802ae`、`96cee50`）：`DarwinWindowStart` 多一个下限参数；认识 `/chosen/darwinboot-memory-floor`（8 字节，0 等于没有；有下限却没有排除表的树被拒绝）；有下限时屏幕多打一行 `DARWINBOOT: window floor=… start=…`，找不到窗口时打 `NO WINDOW … HEAD … FLOOR …`。
    - 生成器（UniXNU `74a17c8`）：板级选项 `owned_memory_floor`，写成 `darwinboot-memory-floor`。
    - 固件内存表（`../uefi-sheng` 分支 `local/sheng-12g-memory-map`，提交 `20331338`）："DRAM bank 1 high" 列到 `0xB00000000`。
    - 板级配置（`../UniXNU-sheng` 新分支 `local/sheng-12g-top-window`，提交 `4ff0ecf`，只含 `board.toml`）：下限 `0x980000000`，窗口外的表 16 格，保留列表加 `0x80000000:0x800000000`。
  - 主机测试：加载器 5 个脚本通过；`python3 -I -B -m unittest discover -s local-tools/tests` 30 个通过（审阅后补了 1 个，`test-adt-window.py` 也多了对 `Boot` 的检查，见下面"最终审阅"）。其中 `test_top_window_layout.py` 用固件内存表、板级配置和加载器自己的代码算出（固件自己的分配按假设放在 bank 1 顶端 256 MiB，这是模型，不是从本机读到的内存表）：窗口起点 `0x980004000`，内核收编 `0x880000000`–`0x8B9D00000`、`0x8B9F00000`–`0x8BBD00000`、`0x8C0000000`–`0x980000000` 三段，共 `0xFBB00000` 字节（1030912 页）。内核那一步是照补丁写的 Python 版，不是内核本身。
  - 新工具 `local-tools/adt-chosen.py`：打印 payload 里设备树 `/chosen` 下加载器用的属性，用来在上机前核对。
  - 构建结果（日常那一套没有动，哈希都核对过）：

    | 文件 | 字节数 | sha256 | 说明 |
    | --- | --- | --- | --- |
    | `out/flash/SILICIUM_UEFI.topwin-e168abab.fd` | 3145728 | `e168abab069eca6edd8cf317d064974decb3a31829fc078a21f18b53d245ff90` | 新固件：带下限的加载器，内存表列到 `0xB00000000` |
    | `<output>/boot/boot-topwin.img` | 210903040 | `85f9dbf8…` | 新固件的 v0 镜像 |
    | `out/flash/boot-v4-payload.topwin-k443.img` | 210903040 | `3cf2e6480638de189bb35fb018baf45150ded9cc6102115ecb09fa12bb582a09` | 对照：保留列表多一项 `0x8A0000000:0x20000000`，把新列入的 443 MiB 挡在收编之外 |
    | `out/flash/boot-v4-payload.topwin.img` | 210903040 | `af5cdf8e11e5bc3d95f6e982a20969ff67289fc782af19ca12f776ae3c8c7dd2` | 完整方案 |
    | `out/flash/boot-v4-flash.topwin.img` | 200417280 | `40fb63bdcad05b97f70b63d9141a46d25ccd33052c2803fe70e20269ff68b649` | 完整方案，190 MiB 卷，放得进 `boot_a`（余 909312 字节） |

  - 这三个 v4 镜像**都没有上机**。它们和日常镜像只差两处：固件，以及 payload 卷里的 `kernel.macho.adt`。设备树里变的只有 `darwinboot-memory-floor`（新增）、`darwinboot-memory-outside`（8 格变 16 格）、`darwinboot-memory-outside-kept` 和随机种子；两个新镜像之间只差保留列表和随机种子。内核、GPU 附加包、信任缓存、Data 种子都和日常镜像逐字节相同。
  - 做法上的一点偏离：`./unixnu build payload` 每跑一次都会重新生成 `kernel.macho.gpuaddon` 和 `kernel.macho.trustcache`（信任缓存里的 UUID 和一部分代码哈希每次都不同，大小不变；连跑两次、输入相同也不同）。为了上机时只变固件和设备树，两份 payload 没有直接用构建结果，而是在日常 payload 的副本里只替换设备树：
    `cp <output>/payload/payload.daily-8a36fe56.img <output>/payload/payload.topwin.img`，再 `MTOOLS_SKIP_CHECK=1 TZ=UTC mcopy -D o -Q -m -i <output>/payload/payload.topwin.img <output>/payload/kernel.macho.topwin.adt ::/EFI/UniXNU/Payloads/kernel.macho.adt`。两份设备树留在 `<output>/payload/kernel.macho.topwin.adt` 和 `kernel.macho.topwin-k443.adt`（里面有芯片序列号，不入库）。日常 payload 的备份是 `<output>/payload/payload.daily-8a36fe56.img` 和同名 `.json`，`payload.img` 已放回日常那一份。
  - 上机时的预期读数（Task 6）：屏幕上 `DARWINBOOT: window floor=0x980000000 start=0x980004000`，`pa=0x980004000`，窗口外的段里有 `0x880000000 + 0x39d00000`、`0x8b9f00000 + 0x1e00000`、`0x8c0000000 + 0xc0000000`。`sudo dmesg | grep "memory outside"`：对照镜像最多 917504 页，完整镜像最多 1030912 页。`hw.memsize` 通过线：对照 9736028160，完整 10200547328。先跑对照的一份，再跑完整的一份，各试用 30 分钟。完整的一份用 `out/flash/boot-v4-payload.topwin.img`：它和对照的一份都是 200 MiB 卷，只差保留列表。`boot-v4-flash.topwin.img`（190 MiB 卷）留到写 `boot_a` 之前再从内存启动一次。窗口起点不是 `0x980004000` 时，内核一页也不收编（`0 pages adopted, 0 refused`），原因要在下限附近找。
  - 已知限制（最终审阅发现）：GPU 驱动判断导入内存会不会和自己的缓冲区冲突时用一张页表（`drivers/Adreno740/NativeAdrenoMemory.cpp:97-116`），只给窗口里的页和物理地址 4 GiB 以下的页编了号。新布局收编的 `0x880000000`–`0x980000000` 不在表里，本来会被拒绝的冲突映射会被放过。审阅没找到越界或 panic 的路径，也没能确定实际会不会遇到。所以这几份镜像上的画面错乱或 GPU 卡住，不能直接当成内存问题。改它要重建驱动，在设计之外，没有改；写 `boot_a` 之前请用户决定。
  - 回到日常状态：两个兄弟仓库和固件构建目录现在都是路线一的状态：`../uefi-sheng` 在 `local/sheng-12g-memory-map` 的 `20331338`（bank 1 列到 `0xB00000000`），构建目录里的固件是 `e168abab`；`../UniXNU-sheng` 在 `local/sheng-12g-top-window`。要重建日常镜像，两处都要回去：`../uefi-sheng` 回到 `5dfcc572`（或者把 `out/flash/SILICIUM_UEFI.mem12g-9b21a09e.fd` 放回构建目录），`../UniXNU-sheng` 切回 `main`（工作区里没提交的改动会跟过去）。只切回板级配置、固件还是路线一的，窗口会落在 `0x8C0004000`，内核一页也不收编（审阅者按模型算的）。另外 `<output>/runtime/` 里的 GPU 附加包和信任缓存、`<output>/payload/stage` 是路线一那两次 payload 构建留下的，和日常 payload 里的不同；日常的 `payload.img` 已放回。
  - 最终审阅（约 21:00，一个新的审阅者，只读）：没有严重问题，可以只从内存启动做 Task 6。审阅结果、补的测试和推迟的小问题记在计划文档末尾"最终审阅"。
- **路线一上机（Task 6，2026-11-14 21:11 起）**
  - 21:11:26 fastboot 只读：槽位 a，`slot-successful:a: no`，`slot-unbootable:a: no`，重试 5，电池 4226 mV。
  - 21:11:35 `fastboot flash boot_a out/flash/boot-v4-flash.prev.img`（刷前核对 sha256 `40234c20…`）：`Sending 'boot_a' (195720 KB) OKAY [4.508s]`，`Writing 'boot_a' OKAY [0.073s]`；刷完重试 7，当前槽位 a。
  - 21:11:50 `python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.topwin-k443.img`（刷前核对 sha256 `3cf2e648…`）：`Sending 'boot.img' (205960 KB) OKAY`，`Booting OKAY`，45 秒内引导程序没有回来。屏幕读数、`hw.memsize` 和试用结果等用户反馈。

**开机待机久了，键盘和触控板失效（用户 2026-11-14 报告，还没有调查）**
- 用户原话："开机待机久了之后，键盘+触控板的固件会失效"。指的是键盘保护套（键盘加触控板）。
- 还不知道的：大约待机多久出现；失效时屏幕触摸是否正常；重新吸附键盘套能不能恢复，还是必须重启；出现时平板有没有接 USB 线。处理时先问清。
- 线索，都没有验证过：
  - 上游已知并且没在硬件上测过：`docs/zh/devices/sheng.md` 第 523 行（"…their effect on the reported macOS charging and idle failures is not yet measured on hardware"）和第 528 行（待办："keyboard/touchpad response after extended idle"）。
  - 同一文件第 496、1084 行描述了键盘服务的恢复逻辑：读失败 100 ms 后重试，保活失败时用 sleep GPIO 唤醒控制器，连续三次失败就释放输入并重新加载固件，重载失败会退避。用户看到的"固件失效"可能就是这条恢复路径没有成功。
  - 设备仓库的 #93（"fix(keyboard): preserve touchpad precision and recover cover input"，11-12 合并）已经在本地构建里。上游还有一个分支 `fix/keyboard-cover-recovery`（bluseliu50，11-13，23 个文件），和 #93 是什么关系没看。
  - 设备仓库本地落后上游 3 个提交，是 #95（"fix(input): Retain digitizer properties during concurrent updates"），和输入有关，没合进来。
- 用户的要求：先记录。

**macOS 下充电口不充电、不识别外接 USB 设备（用户 2026-11-14 报告；上游已知，没有修复）**
- 用户原话："仍存在充电口无法正常充电，无法正常识别外部usb设备"。
- 充电：上游设备记录 `docs/zh/devices/sheng.md` 第 938 行写着，在这个内核下充电固件报告没有 USB 输入（online 0，6 到 44 mV），而引导程序用同一根线能充电，原因不明。第 523、528 行把 macOS 下的充电问题列为还没在硬件上测量。和本机读数一致：18:07 在 fastboot 里读到 4400 mV，凌晨是 3883 mV，说明关机或 fastboot 状态下能充。
- USB 外设：同一文件第 761、769 行，主机模式下苹果的 xHCI 驱动能跑、命令能完成，但"enumerating a peripheral is not verified"。第 713 行有启动参数 `usb-host=<秒>`（延时后强制主机模式）和 `usb-back=<秒>`，没试过。
- 眼下的办法：要充电就关机或进 fastboot 再插线。

**其他还开着的问题（前面各节有详细记录，这里汇总）**
- 槽位重试次数每次正常开机扣 1，要接 Mac 补；长期方案（内核侧自动标记启动成功）等用户决定。见第 8 节"槽位重试次数"和"日常使用"。
- iPadOS / 双系统：等用户说明用途。见第 8 节"iPadOS：调研到的事实"。
- macOS 下能否给电池充电，没有确认。电压记录：01:39 是 3892 mV，01:55 是 3880 mV，02:19 是 3883 mV（都是 fastboot 里读的）。
- 插着 USB 线或充电器关机，会不会被充电事件重新拉起，没有验证。
- `locationd` 每次启动都被 `reason 28:261`（PAC 校验失败）杀掉，没有查。
- 这台机器为什么不接受 v0 头的启动镜像，没有查清。
- 可以反馈给上游的文档和构建缺口，散落在第 5 节和第 8 节（例如 macOS 第一次启动要带 `data-reset=1`、`payload.py` 的 95% 规则让 190 MiB 的卷做不出来）；用户没有要求提 issue 或 PR。

**代码审查（2026-11-14 02:40）**
- 独立审查的结论："With fixes"，没有严重问题。已刷进平板的镜像逐文件核对无误，关机补丁的集成也核对无误。
- 已修（提交 `550f18e`）：`make-flash-bootimg.py` 原来在读输入之前就删除 OUTPUT，所以 SOURCE 和 OUTPUT 写成同一个文件时会删掉输入；现在会拒绝。缺 mtools 时残留旧 OUTPUT 的问题也修了。测试从 8 个补到 12 个。
- 新发现：这个工具的输出**不能逐字节复现**。mformat 会把当前时间写进卷标的目录项，所以同样的输入每次打包，sha256 都不一样（差 4 个字节）。核对镜像要用文件内容，不能只比 sha256。02:40 用修好的工具重新打包 `boot-v4-payload.img`，和 `boot_a` 里的 `boot-v4-flash.img` 只差这 4 个字节。
- 运行测试要加 `-B`。`-I` 会让 Python 忽略 `PYTHONDONTWRITEBYTECODE`，不加 `-B` 会在仓库里留下 `__pycache__`。

**代码审查里没修的小问题（2026-11-14，都不影响已刷入的镜像）**
- `local-tools/make-flash-bootimg.py`：
  - 几种异常输入会打印 Python traceback，而不是一行原因：SOURCE 不存在、没有 ramdisk 的 v4 镜像、卷标含非 ASCII 字符、OUTPUT 的目录不存在、OUTPUT 是个目录。退出码都不是 0，也不会生成镜像。
  - 大小不符的拒绝分支里，先删临时文件再读它的大小，会崩成 traceback（仍然不生成镜像）。
  - 最后写文件失败（比如磁盘满）时，会留下 `OUTPUT.tmp`。
  - 自检是"用 mtools 取出来再比"，看不到 FAT 属性位、卷之后的多余数据；也没有清理调用者环境里的 `MTOOLS_*` 变量。用 `payload.py` 做的卷不受影响。
  - 在 `LC_ALL=C` 下会拒绝所有 payload（mtools 把 `EFI` 取成 `EFI_`），报错信息会误指卷有问题。
  - 输出不能逐字节复现（卷标时间戳），只在上面记了说明，没有改。
- `scripts/build-arm-driver.py` 的驱动补丁步骤（照搬参考仓库）：
  - `patch` 没有加 `--fuzz=0`，也不核对补丁前后的 blob。换了驱动版本时可能偏移着打上去。
  - 补丁失败会在 `build/armdt-platform/` 留下半成品、`.orig` 和 `.rej`，下次构建会覆盖。`components.toml` 记的驱动版本 `417ff95` 和子模块固定的 `e8bd8d5` 不一致，这一点也是从参考仓库继承来的。
  - 用这个仓库给别的板子构建 `ArmDTPlatform` 也会带上这个补丁。单核设备树里没有 `psci` 节点，那时调试用的 stage reset 会空转，不会复位。
  - 启动参数 `platform-power-test` 没有写进文档。提交说明写的是"power off and restart"，真机只验证了关机。
- 其他：`local-tools/make-bootimg-v4.py` 的说明里用法还写着旧名字 `make-v4-test.py`；提交 `c08feb7` 标成 `docs:`，实际还加了三个脚本（不改写已有提交）。
