# Handoff：小米平板 6S Pro（sheng）构建 macOS 27.3

更新时间：2026-11-17
**内存更正（2026-11-14 实测）：这台平板是 12 GiB 内存，不是之前一直写的 16 GiB，见文末"用户想把内存拉满"一条。本文件其他地方的"16 GiB"都指这台机器。**

目标：用 UniXNU 为小米平板 6S Pro（代号 sheng，SM8550）构建 macOS 27.3（profile `macos-27.3-26C5035r`）镜像，刷入 `userdata` 后用 `fastboot boot` 启动。

**工作分支（2026-11-17 15:3x 起）：核心和 sheng 都在 `local/on-main-20261117` 上，不再用 `integrate/*`。**
- 用户说作者（rponeawa）告诉他"提交都合了"，要求切回 main。核对结果：上游 `main`（核心 `ae4ee0e`、sheng `8a85350`）里没有睡眠改动；作者当天 15:1x 建了两个还没合进 main 的功能分支：核心 `upstream/feat/sheng-sleep-wake`（`2e64418`）、sheng `upstream/feat/platform-sleep-wake`（`7ffbb0b`，比 main 多 15 个提交）。用户选的基线：main ＋ 作者的两个分支 ＋ 上游没有的本地修复。
- 分支的构成（`git log upstream/main..HEAD` 就是全部差异）：
  - 核心：作者的 `2e64418`（ArmCpu 换成 `5f37026`，含我们的睡眠和 GIC 修复，睡眠钩子改成弱引用），上面 4 个提交：`29e63b4`（12 GiB：9 GiB 窗口和下限、Adreno740 页表位图、`memory-outside-report`）、`c0f8627`（`--auto-login` 文档行）、`f09e70f`（`local-tools`）、`3440539`（HANDOFF、计划、设计、规则）。
  - sheng：作者的 15 个提交（睡眠主体、背光等画面、键盘壳和盖子），上面 6 个提交：`8a0c5f5`（SIGP 恢复的竞态，第 13 次入睡的 panic）、`8d1a536`（开盖入睡不再 3 ms 被唤醒）、`a28b056`（`kern.unixnu_wifi_log`）、`e92978e`（命名扫描、扫描带信道、Ath12kWifi 指向 fork 的 `b455da9`、`nwk_` 改名修复）、`ced5524`（porting.toml）、`8ca560d`（12 GiB 的 board.toml 设置）。
  - 上游哪里都没有的（就是上面 sheng 的前 4 个和两边的 12 GiB 提交）：其中 `8a0c5f5`、`8d1a536`、扫描信道还没上机验证；Wi-Fi 命名扫描和日志导出推过 fork，但作者这次没收（`7ffbb0b` 写着 "retain the existing network boundary"）。
- 做法：先在临时工作树里把 `integrate/upstream-20261117` 和作者的分支做三方合并（核心 2 处冲突、sheng 11 处；两边都有的用作者的，上游没有的修复用我们的），再从作者的分支出发按主题重新提交，最终内容和合并结果一致。和上次能通过编译的 sheng 内容相比，只多了作者的键盘壳日志常量和设备启动时发布计数器；内核补丁文件和补丁顺序没变（154 个能打上的结论仍成立）。
- 本地 `main` 两边都指到了上游 `main`（上游改写过历史，不能快进），旧位置留在 `backup/main-20261113`；`git branch -f` 顺带把 `main` 的跟踪分支设成了 `upstream/main`。`integrate/*` 分支原样保留，都没推。
- 检查（都在新分支上跑）：核心 `check-unixnu.py`、`scripts/unixnu` 和 `local-tools` 的测试、`tests/` 四组；ArmCpu 的 `check-mmio-access.py` 和 `check-sleep-host.py`；sheng porting record 18 个区、21 个主机检查和 `check-ath12k-exports.py`（不过的还是那 7 个无关的）；`ArmCpu.cpp`、`KeyboardProbe.cpp`、`ShengSleep.cpp` 用构建参数单独编译通过（`KeyboardCover.cpp` 没单独编）。
- 作者的功能分支以后可能改写或换个形式合进 main；到时候在 main 上重放我们这几个提交，不要去合旧的 `integrate/*`。
- **cd16 构建成功（用户 15:49 起第四次，16:04 完成），测试镜像已打好，等用户说可以再从内存启动。**
  - 构建用的提交：核心 `2804d8b`（构建期间只多了文档和规则的提交）、sheng `8ca560d`，都在 `local/on-main-20261117` 上。来源记录 `cd16-build.json`、`cd16-images.json`。
  - 内核 `e677dce5`，另存 `kernel.macho.cd16-e677dce5`（json、map 同后缀，只读）；载荷 `297adb02`，另存 `payload.cd16-base.img`（200 MiB 装得下上游的桌面配置）。日常文件已还原，7 个哈希都对；OS 镜像已卸载。
  - 内核里核对过：
    - 字符串：`wifi: scan request %u to the supplicant: ssid %u, %u frequencies`、`wifi: supplicant scan`、`sheng backlight: system awake, panel waits for the display`、`panel back to its level`、`sheng sleep: woke by`、`PMRD: sleep enabled by platform-sleep`、`SL st=`。
    - 符号：`_nw_wifi_scan_frequencies`、`_sysctl__kern_unixnu_wifi_log`、`_sysctl__kern_unixnu_prev_log`、`_arm64_platform_sleep_hook`、`_armcpu_sleep_register`、`_sheng_sleep_probe`、`_sheng_sigp_recover`、`_boot_reset_watchdog_ping`、`_sheng_buttons_sleep_check`、`_native_keyboard_lid_closed`。
    - 构建树里打过补丁的 `cpu_common.c` 第 423 行有 `cpu_running` 条件；这次的 `kernel.log` 没有 error，也没有未定义符号。
    - 没找到 `sheng keyboard: cover` 这行日志的字符串：键盘壳现在用作者的版本，措辞可能变了，没查。
  - 测试载荷 `payload.cd16-sleep.img`（`46fbd8be`）：加 `enable-jobs=com.openssh.sshd platform-sleep=1 platform-sleep-wake-after=60 darkwake=1`，`debug=0x14e` 改写成 `debug=334`，**去掉了 `log-gpu=1`**，参数行 994 字节。
    - 原因：上游的桌面参数合进来后基础行是 920 字节（cd15 是 877），四个睡眠参数加上去是 1004 字节，超过 1000。`board.toml` 那条"905 字节、放得下"的记录漏算了构建加在最前面的 `vm-swapin-io=1`。
    - 为此给 `make-payload-variant.py` 加了 `--remove-arg NAME`（核心 `c3e45d7`，新测试先失败后通过，`local-tools/tests` 91 项全过）。cd11 到 cd15 的睡眠镜像也都不带 `log-gpu=1`。
  - 测试镜像 `out/flash/boot-v4-payload.bigwin-cd16-sleep.img`（`c38f794f`），`bootimg-contents.py --payload` 核对过装的是 `46fbd8be`。固件还是 11-15 的 `boot-bigwin.img`（`5c926a3f`）：上游 `main` 钉的 DarwinBoot `5243c68` 是 11-11 的，我们的 `bdb6ff7` 只多 4 个本地提交，固件不用重做。
  - 上机要看的：开机自动连 Wi-Fi；唤醒没有彩条；开着盖 `pmset sleepnow` 不再 3 ms 被叫醒；合盖放 15 分钟以上（定时器每 60 s 叫醒一次，超过 13 轮）不 panic；唤醒后 Wi-Fi 重连；睡眠第 4、5 级；新的 Metal 运行库（R2507）有没有画面问题。上机前要用户在平板上 `sudo pmset -a sleep 0`。
  - **cd16 第一次启动（16:18，用户说进了 fastboot）**：
    - fastboot 里：当前槽位 a，a 重试 6 次、b 7 次，都没标成功也没标不可启动，电池 4137 mV；a 大于 4，没补。`boot-sheng.py` 启动后引导程序 45 s 没再回应，镜像在跑。
    - 进了桌面，持久的 Data 卷打开了（用户的账户和终端会话都在）。`hw.memsize` 10142334976；参数行 995 字节，`enable-jobs=com.openssh.sshd platform-sleep=1 platform-sleep-wake-after=60 darkwake=1 debug=334` 都在。
    - **SSH 一直是好的，16:20 到 16:33 是我连错了地址**（"连上就被对端关掉"不是平板的问题）：
      - 我用的是会话记录里出现次数最多的那个地址。它在另一个网段，这台 Mac 现在把那个网段路由到隧道接口 `utun8` 上。那条路由上任何端口都连得上（22、2222、2223、59999、81 都是 open），连上马上被关掉。
      - 平板这次的地址在 Mac 的 `en0` 网段里。16:34 用主机密钥找到的：对 `en0` 上开着 22 端口的邻居逐个 `ssh-keyscan`，密钥和 `out/ssh/known_hosts` 里那把相同的就是平板。
      - 为此加了 `local-tools/tablet-ssh.py`：每次按主机密钥找平板再连，记住的地址不在当前网段就不问它。测试 12 项，先失败后通过；`local-tools/tests` 103 项全过；在平板上试过三种情况（没有记住的地址、有、记住的地址在别的网段）。
      - 这段时间让用户在平板上跑了 `sudo /usr/sbin/sshd -p 2222` 和 `sudo /usr/sbin/sshd -d -p 2223`，都是白跑。16:40 核对：平板上只有 22 端口在监听，没有留下多余的 sshd。
    - **开机后 Wi-Fi 没有自动连上**，用户从控制中心手动连的（`WiFiNetworkJoinReason = ControlCenter`）。日志在 `out/boot-logs/cd16-1117-1635/`（本地）；`this-boot-prejoin.log` 是这次开机、手动连接之前的 airportd 日志，那时平板时钟还停在 11-16 07:0x：
      - 比 cd15 前进了一步：实时扫描在驱动的 12 s 期限内结束，结果交回了 airportd。四次实时扫描：
        | 发起方 | 要扫的信道 | 用时 | 交回的结果 |
        | --- | --- | --- | --- |
        | locationd | 没指定 | 7.26 s | 12 个 |
        | auto-join | 1 个（5g36） | 7.23 s | 13 个 |
        | auto-join | 2 个（5g36、2g6） | 7.26 s | 15 个 |
        | auto-join | 其余 18 个 | 8.98 s | 15 个 |
      - 但 auto-join 每次都记 `Scan SUCCEEDED (… results=0 …)`。第三行那次还有一行 `CWFFilteredScanResults: All scan results are filtered out. mutableScanResults count: 0, scanResults count: 6`：按请求的信道留下 6 个，CoreWiFi 又把这 6 个全部滤掉。连上以后链路在 5180 MHz（36 信道）、-34 dBm，所以要连的网络应该就在这 6 个里。
      - 滤掉的原因还不知道。auto-join 这次扫描的条件：`minRSSI=-80`、`maxCacheAge=10000`（之后是 20000）ms、名字列表（2 个存着的网络都被当成隐藏网络）。要看驱动交回去的每条结果：`wifi-net: scan result N: … MHz, … dBm, 名字`（每次实时扫描记前 24 条），以及 `fill_result` 填的 `age_ms`。
      - 只扫 1 个信道也要 7.2 s，18 个信道 9.0 s：每个信道约 0.1 s，另有约 7.1 s 的固定开销。在哪一步还不知道，要看 `scan request` → `supplicant scan` → `scan done` 三行的时间。
      - 驱动日志没读到开机那一段：`kern.unixnu_wifi_log` 是约 500 行的环，每 10 s 一组的统计行约 6 分钟就把它填满。我 16:35 才连上，开机时的扫描记录已经被冲掉。`log show --info --debug` 取那一刻的 airportd 日志，取回 0 行。
      - 为此加了 `local-tools/tablet-wifi-capture.sh`：在平板上每 2 s 读一次这个环，把新行追加到文件。16:48 已在平板上启动（`~/unixnu-capture/wifi-0048.log`，60 分钟；16:48 核对在写，530 行），用来留住睡眠唤醒后没连网时的扫描。脚本留在平板的 Data 卷上，以后开机可以先在平板终端里启动它再连 Wi-Fi。
      - 16:50 用 `local-tools/tablet-wifi-scan-probe.js` 读了 CoreWLAN 手里的 19 条结果：要连的网络是 36 信道、-34 dBm、名字 16 个字符、信道标志 0x12，都对；`AGE` 也对；但**每条结果的 `TIMESTAMP` 都是 0**。
      - 这台 Mac（27.2.1）上 CoreWiFi 的 `CWFFilteredScanResults` 按 15 种条件过滤，每滤掉一条都记一行调试级日志：`Filtering based on maxAge`、`minTimestamp`、`minRSSI`、`channel list`、`FILS DF`、`BG scan result`、`hidden scan result`、`SSID`、`short SSID`、`BSS type`、`network name prefix`、`incl. scan result list`、`predicate`、`duplicate`、`merge policy`。怀疑是 `minTimestamp`，没有验证。
      - 16:53 在平板上开了调试日志采集（`~/unixnu-capture/airportd-0053.log`，`log stream --level debug`，60 分钟）。下一次没连网时的 auto-join 扫描会留下每条结果被滤掉的原因。
    - **WindowServer 崩了 4 次**（用户 16:5x："一直在崩溃"）：16:30:04、16:31:58、16:50:41、16:52:44。报告在 `out/boot-logs/cd16-1117-1635/ws/`（本地）。
      - 四次是同一处：主线程 `EXC_BAD_ACCESS KERN_INVALID_ADDRESS`，在 `_platform_memmove` 里。出错地址正好是一块 CoreAnimation 内存区域结束后的第一个字节（区域 184K、244K、116K、32K）。寄存器：源地址等于出错地址，目的地址在栈上，剩余长度 0x1000（16:50 那次 0x400）。
      - 用构建目录里的调试符号翻出调用链（UUID `FB2E63C9-1A40`，和报告里的一致）：`-[NBCommandBuffer commitAndWaitUntilSubmitted]` → `waitUntilScheduled` → `CommandBuffer::settle_commit` → `commit_now`（`command_buffer/mod.rs:4785`）→ `CopiedBuffers::copy_in` → `copy_in_untagged` → `copy_in_run`（`copied.rs:1859`）。16:50 那次走 `copy_in_tagged` → `copy_in_blocks` → `tag_in_place` → `read_block`（`copied.rs:1069`）。
      - 含义：新的 Metal 运行库（metal2vulkan development `46e7cc96`，上游今天合的 R2507，AdrenoMetal `f7b4ed1`）给"不拷贝"的缓冲区留一份副本，每次提交命令缓冲时从应用给的内存里把改过的字节读进来。读的范围超出了那块内存映射的末尾。长度是怎么算错的，还没读代码。
      - 和睡眠改动、和 SSH 这边的操作无关：第一次崩溃在 16:30，我 16:34 才连上平板。Data 卷上只有这 4 份 WindowServer 崩溃报告，之前的镜像（旧运行库）一份都没有。
      - 查过上游，没有修复。搜了 `UniXNU`、`CrossDarwin` 的 PR 和 issue：`WindowServer memmove`、`wait_scheduled`、`R2507`、`WindowServer crash`、`metal2vulkan 46e7cc96`、`command buffer memmove`。`UniXNU/AdrenoMetal` 的 `main`（`8c7f950`）比我们用的多 2 个提交，都是着色器缓存应用的；开着的 #65 是诊断。
      - 16:59 第 5 个 WindowServer 已经跑了 6 分 48 秒，还在。
    - 睡眠测试还没做。16:48 平板上 `sleep 0`、`displaysleep 10`，电量 68%，在充电。

**往上游 `main` 推的进度（2026-11-17 16:0x 起，规则 `.claude/rules/push-progress-to-main.md`）**
- 做法：每项改动单独开分支（从 `upstream/main` 开；依赖作者分支的从那个分支开），在单独的工作树里验证，通过后直接推 fork，开 PR 前问用户。本机 12 GiB 这一层不推。
- 已推到 fork，还没开 PR（等用户说开）：

  | 项 | fork 上的分支 | 提交 | 基于 | 验证 |
  | --- | --- | --- | --- | --- |
  | `--auto-login` 文档行 | `zus12873/UniXNU` `docs/macos-auto-login-user` | `a07572d` | 核心 `upstream/main` `6213954` | 上游 `make-macos-data-seed.py` 第 90 行确有这条限制 |
  | 开盖入睡 3 ms 被唤醒 | `zus12873/UniXNU-sheng` `fix/sleep-open-lid-wake` | `bc00259` | 作者的 `feat/platform-sleep-wake` `5d8fedb`（sheng #127，draft） | 新测试在旧代码上编译失败（缺 `sheng_sleep_clear_lid_status`），带修复后 `check-sheng-sleep-host.py` 通过；porting record 18 个区；两个源文件和工作分支上单独编过的一致。没上机 |
  | 第 13 次入睡的 panic（SIGP 恢复） | `zus12873/UniXNU-sheng` `fix/sleep-sigp-recovery-race` | `e3a233b` | 同上 | `patches/` 整个目录和构建用的一致；15:03 那次构建里 `cpu_common.o` 带着这一段编过，只有警告（那次只败在链接 Wi-Fi 符号）。没有主机测试，没上机 |

  - 查过别人：`gh search prs`（UniXNU、CrossDarwin；`auto-login`、`sheng_sigp_recover`、`cpu_running SIGPdisabled`、`INTR_STATUS lid sleep`）和各仓库 `git log --all -S'target_proc->cpu_running'`，没有同类改动。
  - 主题分支上的提交说明重写过（不带 `integrate/*`、`cd15`）；测试注释里的 `cd15` 改成了 "seen on the tablet"，其余和工作分支的 `8d1a536`、`8a0c5f5`、核心 `c0f8627` 内容相同。
  - 工作树：`../UniXNU-pr-docs-autologin`、`../UniXNU-sheng-pr-sleep-lid`、`../UniXNU-sheng-pr-sleep-sigp`。
- 等用户决定：
  - Wi-Fi 两项（sheng `a28b056` 的 `kern.unixnu_wifi_log`、`e92978e` 的命名扫描和扫描信道）。作者在 #127 里写明没收网络这部分。要推就先向 `UniXNU/Ath12kWifi` 提组件 PR：本地两个提交 `0d8758a`（在 fork 的 `local/scan-diagnostics` 上）、`b455da9`（没推），基于 `39cc47b`，组件上游 main 已到 `26cf2da`；sheng 那边开 draft。
  - 旧 PR（sheng #109 到 #112，都开在上游改写历史之前，差异带 660 多个提交）。按新增的行逐行比过：
    - #109（策略测试桩）：4/4 在上游 main。
    - #110（`enable-jobs`）：检查脚本 7/7、`BootWatchdogPolicy.c` 8/12 在上游 main，差的 4 行是注释。
    - #112（`ci-mps=0`）：参数在上游 main 的 `board.toml` 第 243 行，只少注释。
    - #111（合盖丢触摸）：不在 main；在作者的 #119 和 #127 里（都是 draft），`TouchLid.h`、测试和检查脚本逐行相同。
- 上游的新动向（15:5x 拉取）：
  - 核心 `upstream/main` 多了 `6213954`（设备记录文档）。
  - 作者的 sheng 睡眠分支多了 `5d8fedb`：`BootLog.c` 的日志格式串放进 `__DATA_CONST`，让 `__TEXT` 放得进保留 kext 的空隙。
  - cd16 构建时工作分支不带这两个提交，构建没报 `__TEXT` 放不下。构建完成后把 `5d8fedb` 合进了 sheng 工作分支（合并提交 `23366db`，只动 `BootLog.c`；9 个策略文件哈希不变）：启动日志的两个主机检查、睡眠、盖子、Wi-Fi 的检查和 porting record 都过。`BootLog.c` 没能用内核参数单独编（`kernel-compile-check.py` 把它当 C++ 编，合并前的版本同样报错），要等下一次构建。**所以 cd16 之后的下一个镜像会多这一处改动。** 核心工作分支还差上游 `main` 的 `6213954`（只是设备记录文档）。
  - 作者开着的相关 PR（都是 draft）：核心 #299、sheng #127 和 #119、ArmCpu #7。

以下"当前阶段"写于 2026-11-17 09:3x，已被上面这一段取代：**真睡眠（suspend-to-idle，启动参数 `platform-sleep=1`）上机卡死的原因找到了：启动核进入睡眠时读 GIC 的方式 Gunyah 模拟不了，触发 panic。ArmCpu `a2c5dd3` 已修好，等用户构建 cd13 再上机。** 详情见下面"cd12 构建和上机"一条。 设计 `docs/superpowers/specs/2026-11-16-sheng-suspend-design.md`（用户批准），计划 `docs/superpowers/plans/2026-11-16-sheng-suspend.md`，进度和每条取舍在 `.superpowers/sdd/2026-11-16-sheng-suspend/progress.md`（本地，不入库）。
- 已提交：
  - ArmCpu `local/platform-sleep`：`6062866`（唤醒判定，主机测试）和 `a26ef5d`（副核 PSCI CPU_OFF、启动核屏蔽中断等唤醒、`initCPU(false)` 恢复）。核心 `3bec015` 指向它。
  - sheng：`97df6fa`（XNU 补丁 `sheng-platform-sleep.patch`，放在 series 最后）、`0fdf9db`、`35858cc`（盖子和电源键唤醒、吞掉叫醒系统的那次按键）、`c35f3bc`（睡眠时关背光）。
  - 主机检查全过；改过的内核和板级源文件都用构建参数单独编过（`local-tools/kernel-compile-check.py`）。
- 下一步：审查意见处理完后，请用户在自己的终端里构建（cd11），然后按计划 Task 6 分五级上机：
  1. 60 秒定时自动醒；
  2. 电源键叫醒；
  3. 开合盖；
  4. 连续 10 次；
  5. 拔电合盖 1 小时，以及插电睡眠时能不能充电。
  - 上机前要用户在平板上 `sudo pmset -a sleep 0`。
- Task 0（cd11 只关背光、拔电合盖 1 小时的对照）还没做。
- **审查问题已修完，cd11 已构建（11-16 23:39，用户在自己的终端里跑）**
  - 修复的提交：ArmCpu `bdb6151`（核心 `d330225`）、sheng `4abf408`。内容：
    - 恢复时发自我 IPI；补丁里把等 IPI 的时间限在 100 ms；
    - 开盖用 `kIOPMSetValue` 上报，电源键调 `requestUserActive`，让唤醒变成完整唤醒；
    - 睡眠中每 10 s 喂一次看门狗；
    - 不唤醒的中断要应答并结束（IAR1/EOIR1），反复触发的线路会被关掉；
    - 一个唤醒源都没开、也没有定时器时，直接返回不睡；
    - 板级日志加 `SL` 一行；
    - 定时器用绝对时间 `CNTV_CVAL`；
    - 只关掉中断目标是应用处理器的 TLMM 脚。
  - 用户报告构建里在 `kernel: patch platform-error-name-address.patch` 这一步看到 error。但 154 个补丁都在 23:35:46 打上了，含 `sheng-platform-sleep.patch`；补丁失败时构建会删掉工作目录并退出，实际构建一直跑完了。报错原文还没拿到。
  - 内核 `e2959f54`，另存 `kernel.macho.cd11-e2959f54`（json、map 同后缀，只读）。检查过：
    - 有 `_arm64_platform_sleep_hook`、`_armcpu_sleep_register`、`_sheng_sleep_probe`、`_boot_reset_watchdog_ping`、`_sheng_buttons_sleep_check`；
    - 字符串里有 `PMRD: sleep enabled by platform-sleep`、`sheng sleep: woke by`、`SL st=`、`sheng keyboard: cover %s`（掉线日志）、`sheng backlight: lid`、`sheng backlight: system`。
  - 载荷 `51274b10`，另存 `payload.cd11-base.img`（只读）。
  - 日常文件已还原，7 个哈希都对（含 `payload.json` `4d0e0464`）；OS 镜像已卸载。来源记录：`cd11-build.json`、`cd11-images.json`。
  - 测试载荷 `payload.cd11-sleep.img`（`723a635a`）：
    - 加了 `enable-jobs=com.openssh.sshd platform-sleep=1 platform-sleep-wake-after=60 darkwake=1`；
    - `debug=0x14e` 改写成同值的 `debug=334`，参数行才能压到 1000 字节以内；
    - 这次没带 `log-gpu=1` 和 `keyboard-backlight=50`，所以键盘灯是暗的。
  - 打成 `out/flash/boot-v4-payload.bigwin-cd11-sleep.img`（`7b60a68b`）。内核块是 `610fa1f6`（同 cd7–cd10 的大窗口固件），`bootimg-contents.py` 核对过。
  - 下一步：用户在平板上 `sudo pmset -a sleep 0` 并进 fastboot，然后从内存启动，做第 1 级：SSH 里 `pmset sleepnow`，60 秒后应自己醒。
- **CD11 第 1 级上机（11-17 00:0x–00:2x，只从内存启动 `cd11-sleep`，槽位 a 6 次、b 7 次，始终没变）**
  - 第一次睡眠（开机时空闲睡眠计时器 1 分钟触发）被系统自己取消了：
    - WindowServer 启动时上报用户活动（"ws.initialize"），根域判 `userActivityAtSleep 1`；loginwindow 30 s 没回应，之后回到完整唤醒。
    - 能确认的：`PMRD: sleep enabled by platform-sleep` 生效；"wakes by lid yes, power key yes"；背光随睡眠熄灭，唤醒后恢复。
    - ArmCpu 的 `phase 0`，CPU 睡眠没开始。和我们的代码无关。
  - 第二、三次（`pmset sleepnow`）屏幕全黑（背光已关），60 s 定时器没叫醒，按电源键也没反应，只能长按强制重启进 fastboot。强制重启没扣槽位次数。
  - 卡住时的痕迹：
    - 统一日志里没有：上一趟 07:57 之后的日志都还在内存里，强制重启后丢了；
    - 板级 UFS 日志也读不到：Linux 读取器是 v0 镜像，本机引导程序只认 v4；改成 v4 后用的是 vendor_boot 里小米的设备树，主线内核起不来。再开一次 macOS 又会把日志窗口盖掉。`NativeUfs` 只有写日志窗口的接口，没有读的。
  - 第三次开着 SSH 实时 `log stream`（`scratchpad/sleep3-stream.txt`，本地）：
    - 08:17:33 开始（Software Sleep），第一段 f→9 正常。这次 loginwindow 马上回应了，主要是等 powerd 等应用（powerd 回应用了 1.5 s）。
    - 08:18:04.608 第二段（`tellChangeDown ON_STATE->SLEEP_STATE`，trace point 0x12）：内核客户、DriverKit 都应答了，`disk_sync_callout` 也完成了。
    - 08:18:04.647 到 trace point **0x13**（SleepWillChangeInterests），之后网络断，日志流停。所以卡在 0x13 之后，具体在哪一步看不到。
  - 嫌疑最大：0x14（各驱动断电）里的 `NativeLegacyDisplay`。
    - 它是我们驱动里唯一实现了 `setPowerState` 的（启动参数 `offline-legacy-pm=1` 打开的逻辑电源模型），断电时调原厂 `IOMobileFramebufferLegacy::setPowerState(0)`。
    - 平时熄屏只走 WindowServer，从没调过它的 0 状态（熄屏前后 CurrentPowerState 都是 1），所以这条路在本机上从没跑过。
  - 准备好的对照镜像：`out/flash/boot-v4-payload.bigwin-cd11-sleep-nolpm.img`（`9af7623f`，载荷 `payload.cd11-sleep-nolpm.img` `08187642`），在 cd11-sleep 的基础上只改 `offline-legacy-pm=0`。
- **读板级日志（11-17 00:2x–01:1x）**
  - 卡死那一次的日志区（00:13 那次开机、08:17 睡眠）一直没被覆盖：之后只启动过 Linux 读取器，没进过 macOS。
  - v0 读取器（`sheng-log-reader-v0.img`，`os_version` 改成社区模板的 `0x220001a8`）引导程序 4 秒后退回 fastboot；把主线设备树的 `board-id` 改成 `0 0` 也一样。最可能是引导程序要把 `dtbo` 分区里原厂的叠加层套到主线树上。没有擦 `dtbo`。
  - v4 + 我们的固件 + `type = "linux"` 菜单项：`local-tools/make-linux-reader-payload.py`。
    - 第一次报 `Access Denied`：`board.toml` 固件 `ENABLE_SECUREBOOT=1`，未签名的 EFI 程序被拒。
    - 单独编了一份不带 Secure Boot 的固件（`board.toml` 临时改成 0，编完 `git checkout` 还原）：`<output>/boot/boot-reader-nosb.img`（`14a15bd0`）。日常固件 `8407c84f` 已放回构建目录，`boot.json` 从 `boot.good.json` 还原，日常哈希都对。
    - 用它启动，Linux 能起来：`earlycon=efifb` 看得到内核在滚动；随后灰白屏、再黑屏，加 `nomodeset` 也一样（推测是 SMMU 被重置，固件留下的画面没了）。USB 上什么都没出现，读取脚本是否跑到、USB 设备模式能不能起来，都不知道。
  - 用户选做法 3：让 macOS 开机时先读回上一次的日志。
    - sheng `28ae25a`：`BootLog.c` 的 `prev_log_copy` 在写第一笔之前，用 `native_ufs_part_read` 读回上一次的头、消息区、最新 64 个 slot 和启动检查点（约 4.3 MiB）；`kern.unixnu_prev_log`（`BootDiagExport.c`）给出这份拷贝；`read-sheng-log.py --prev` 还原后解码。
    - `check-boot-log-prev-host.py` 主机测试通过；两份源文件都用内核参数编过。`NativeUfs` 没有改。
  - 下一步：用户构建 cd12，然后从内存启动。SSH 里 `sysctl -b kern.unixnu_prev_log > prev.bin`，取回后用 `read-sheng-log.py --prev` 解码。
- **cd12 构建和上机（11-17 08:18–09:20）：找到睡眠卡死的原因**
  - cd12（用户在自己的终端里构建）：
    - 内核 `40dea98b`，另存 `.cd12-40dea98b`。有 `_boot_log_prev`、`_sysctl__kern_unixnu_prev_log` 和日志字符串 "the previous run's log is kept"。
    - 载荷 `26518ce3`，另存 `payload.cd12-base.img`。
    - 日常文件已还原，哈希都对。来源记录：`cd12-build.json`、`cd12-images.json`。
    - 中途外置盘断开过一次，重新挂上后 `verifyVolume` 没问题，哈希都对。
  - 测试镜像，内核块都是 `610fa1f6`：
    - `boot-v4-payload.bigwin-cd12-sleep.img`（`40166d15`），载荷 `d2ccd398`，参数和 cd11-sleep 逐字节相同；
    - `boot-v4-payload.bigwin-cd12-read.img`（`6dd01249`），载荷 `0c40c83a`，只多 `enable-jobs=com.openssh.sshd`，不开睡眠，专门用来读日志。
  - 第一趟 cd12-sleep（08:34）：
    - 用户是合着盖开机的，系统马上以 "Clamshell Sleep" 进入睡眠，然后黑屏，电源键叫不醒，只能强制重启。
    - 卡死那次（cd11）的日志拷贝只在这趟的内存里，跟着丢了。
    - 但这趟自己的板级日志记下了整个过程：86 s，44 个 slot，没有写入错误。
  - 第二趟 cd12-read（09:12，开着盖）：
    - SSH 取回 `kern.unixnu_prev_log`，3,084,288 字节，存在 `out/boot-logs/cd12-prev-1117-0916.bin`（本地，不入库），解码在同名目录。
    - Mac 这边的局域网换了网段，平板换过一次地址才连上。
  - 解码结果：
    - 睡眠一直走到底：0x12 → 0x13（tasks suspend，DriverKit 挂起）→ 0x14 → 0x15 → 0x16 → `PowerChangeDone` → 0x17 → 0x18（停副核）→ 0x19（启动核）。
    - 之后板级日志记下一次 panic：`Unhandled implementation specific error: esr 0x96000010 far 0xfffffff7ce74c104`。
    - 栈：`armcpuPlatformSleep+0xbc` ← `ml_arm_sleep+0x94` ← `processor_offline_intstack` ← `processor_offline`。
    - 所以显示驱动断电（0x14）没有问题，`nolpm` 对照镜像用不上了。cd11 的日志流停在 0x13，只是因为 Wi-Fi 在那里断了；那次多半也是这个 panic。
  - 原因：
    - `+0xbc` 是 `ldr w12, [x8], #4`，`sleepBootWait` 保存 `GICD_ISENABLER1..` 的循环。`read32` 原来是普通的 volatile 解引用，编译器把它编成了后变址（post-index）加载。
    - Gunyah 截获 GIC 的访问再模拟。带回写的访问 CPU 不给可解码的 syndrome（ISV=0），Gunyah 模拟不了，就注入同步外部中止（DFSC 0x10）。
    - 前一条 `ldr w9, [x8, #4]`（读 `GICD_TYPER`）是普通形式，读成功了。
    - 后面的 ICENABLER/ISENABLER 写循环同样编成了后变址 `str`，也会出同样的问题。
  - 查过上游，没有：
    - 仓库：UniXNU/ArmCpu（`origin/main` 新增的两个提交是文档和 owned-SGI probe）、UniXNU-sheng，以及 UniXNU、CrossDarwin 的 issue 和 PR。
    - 关键词：`Unhandled implementation specific error`、`external abort`、`esr 0x96000010`、`post-index`、`writeback`、`ldr %w0`。
  - 修复：ArmCpu `a2c5dd3`（`local/platform-sleep`）。
    - `read8/write8/read32/write32/read64/write64` 改成内联汇编，每次只用一条 `ldr`/`str`、地址放在寄存器里，和 Linux arm64 `__raw_readl` 的做法一样。
    - 原来绕开这些函数直接访问的 7 处（IROUTER、IPRIORITYR、GICR_TYPER）都改为走它们。
    - `tools/check-mmio-access.py`：检查没有访问绕开这些函数，并按驱动里的循环形状在 `-Os`/`-O2` 下编译，确认没有回写、成对或 SIMD 访问。改之前跑是失败的：读循环、两个写循环加 7 处直接访问；改之后通过。睡眠主机测试 1038 项也通过。
    - 用内核参数编出的 `ArmCpu.o` 里，设备访问都是单寄存器的 `ldr`/`str`；剩下的 SIMD 和成对访问都在栈或普通内存上。
  - sheng 板级的睡眠钩子不用改：
    - 在 cd12 内核里反汇编过 `prepare`、`restore`、`shouldWake`、`sheng_buttons_sleep_check`；
    - TLMM 和 PMIC 的访问都是单寄存器形式，SIMD 和成对访问只在 `gSaved`/`gAsleep` 数组上；
    - 这几个钩子还没真正跑过：panic 发生在它们之前。
  - 还没解决：
    - panic 之后系统没有重启，停在黑屏。以前的 panic 都会重启，睡眠里副核已经 CPU_OFF、启动核屏蔽了中断，可能是这个原因，没查。
    - 合着盖开机会直接进入睡眠：这是设计上合盖即睡眠的结果，不是 bug，但上机时要开着盖开机。
  - 下一步：用户构建 cd13（核心指向 `a2c5dd3`），打 cd13-sleep，重新做第 1 级（`pmset sleepnow`，60 s 后自己醒）。
- **cd13（11-17 09:41 构建，用户在自己的终端里跑）**
  - 内核 `e812d062`，另存 `.cd13-e812d062`；载荷 `531fa666`，另存 `payload.cd13-base.img`。
  - 内核里 ArmCpu 所有函数都反汇编扫过：`armcpuPlatformSleep` 没有带回写的访问；剩下两处在 `mapGic`，读的是对象自己的字段，不是设备寄存器。
  - 日常文件已还原，哈希都对；OS 镜像已卸载。来源记录：`cd13-build.json`、`cd13-images.json`。
  - 测试镜像 `out/flash/boot-v4-payload.bigwin-cd13-sleep.img`（`56ff05d0`），载荷 `10b1cce4`，参数和 cd12-sleep 逐字节相同，内核块 `610fa1f6`。
  - 09:57 从内存启动（槽位 a 6 次、b 7 次）。
  - 如果又卡住：用 `cd12-read` 镜像开机读 `kern.unixnu_prev_log`，它不开睡眠。
  - 10:10 用户报终端未响应，还没开始睡眠测试，开机 13 分钟。日志在 `out/boot-logs/cd13-terminal-1117-1011/`（本地）：`ps`、终端的 `sample`、`pmset`、统一日志、3 份崩溃报告。
    - 终端主线程每一次取样都停在同一处：画标题栏的文档图标（`NSThemeDocumentButtonCell` → `ISConcreteIcon generateImageWithDescriptor`），在等图标服务的同步 XPC 回复。终端本身没问题，和睡眠修复也无关。
    - 用户那份 `gui/501/com.apple.iconservices.iconservicesagent`：`runs = 15`、`successive crashes = 15`、`state = spawn scheduled`。
      - 每次拉起 0.4–0.5 s 后就 SIGABRT，日志是 `MPSImageUnaryKernel.mm, line 335`。
      - 崩溃栈：`CIBlurProcessor processWithInputs` → `MPSImage` → `MTLReportFailure` → `abort`。
    - 启动参数里有 `ci-mps=0`，但这次没有像 cd8/cd9 那样崩两次就稳住，开机 13 分钟后还在崩。原因没查。
    - `pmset -g` 里 `sleep 0`（被 powerd、Terminal 挡着），所以不用再执行 `sudo pmset -a sleep 0`。
  - **第 1 级通过（10:16，开着盖、插着电）**：SSH 里执行 `pmset sleepnow`。
    - 18:16:22（平板时间）`sheng sleep: sleeping, lid open; wakes by lid yes, power key yes`，背光关。之后约 30 s 是 powerd 等应用。
    - 18:16:53 走完 0x12→0x16，`System Sleep`，`IOCPUSleepKernel enter`，0x17→0x18→0x19，然后是唤醒那边的 0x23、0x22。
    - 18:17:53 唤醒：`sheng sleep: woke by timer (intid 27) after 60001 ms; sleeps 1, spurious 0, masked 0, ticks 5, unarmed 0, cpu_off failures 0, phase 5`，背光回到原来的亮度。
      - 看门狗 tick 正好 5 次（每 10 s 一次）；
      - 副核 CPU_OFF 没有失败；
      - 没有误唤醒，也没有关掉任何中断线。
    - `kern.sleeptime` 18:16:53，`kern.waketime` 18:17:53；`kern.boottime` 没变，所以是同一次开机，不是重启。
    - 完整唤醒：IOPMrootDomain `Wake Type = UserActivity Assertion`，airportd `FullWake:cpu disk net aud vid`。`hw.activecpu` 8，没有 panic。
    - 从 Mac 看，平板 10:16:58 断网，10:19:17 才重新连上，也就是醒来后过了约 84 s Wi-Fi 才回来。
    - 日志：`out/boot-logs/cd13-sleep1-stream.txt`（睡前的实时日志流）、`cd13-sleep1-reach.txt`（本地）。
  - **第 2 级通过（10:28，电源键叫醒）**：
    - 做法：`(sleep 30; pmset sleepnow)`；用户在屏幕黑了约 45 s 后短按一下电源键。
    - 18:28:33 `sleeping`，背光关；18:29:05 `IOCPUSleepKernel enter`。
    - 18:29:35 `sheng sleep: woke by power (intid 513) after 29660 ms; sleeps 2, spurious 0, masked 0, ticks 7, unarmed 0, cpu_off failures 0, phase 5`：
      - 比 60 s 定时器早；ticks 7 是累计数，加上第 1 级的 5 次；
      - 背光恢复，屏幕一直亮着（叫醒系统的那次按键被吞掉了）。
    - `kern.sleeptime`/`waketime` 18:29:05/18:29:35；开机时间不变；`hw.activecpu` 8；`Wake Type = UserActivity Assertion`。
    - Wi-Fi 又是用户从控制中心手动连的（`WiFiNetworkJoinReason = ControlCenter`），10:31:19 平板才重新出现在网络上。
    - 日志：`out/boot-logs/cd13-sleep2-stream.txt`、`cd13-sleep2-reach.txt`。
  - 下一步：第 3 级，合盖睡、开盖醒，应看到 `woke by lid`。
- **Wi-Fi 不自动连，接着 11-16 那条往下查（11-17 10:2x，cd13，只读）**：用户要已经连过的网络开机和唤醒后都能自动连上。
  - 日志：`out/boot-logs/cd13-wifi-1117-1023/`（本地，里面有网络名，不入库）。
  - 已存的网络能跨开机保留：数据卷上有 2 个，auto-join 每次都列出来。
  - 两个都被 airportd 当成隐藏网络（`Hidden SSIDs (2)`）。
    - 起因：18:08 用户从控制中心连上之后，airportd 记了 `Unable to detect <ssid> as broadcast or hidden`。它扫描确认没扫到，就按"可能隐藏"存了下来。
  - 唤醒后（18:17:53 起）auto-join 跑了约 6 轮（`user_wake`、`power_on`、`retry (ac)`），一次也没连上：
    - 带隐藏网络名的实时扫描都在 10 µs 内 `err[-3903]`，框架自己拒的，没到驱动；
    - 不带网络名、只扫 2 个信道的普通扫描，每次约 12 s，结果为 0；
    - 18:19:11 的那次连接是从控制中心发起的 `associateToWiFiNetwork`，不是 auto-join。
  - `-3903` 是哪里来的（本机 macOS 27.2.1 的 IO80211，`dyld_info -disassemble`）：
    - `Apple80211Scan` 在 `__getScanData` 之后：请求带了网络名列表、而且不是类型 3 时，检查缓存能力位的 `[ctx+0x5a]` bit 6，没有就 `mov w28, #-0xf3f`（-3903）。
    - 能力位图从 `ctx+0x58` 开始：驱动已经用的 bit 46 正是 `[ctx+0x5d]` bit 6，对得上。所以要的是**能力位 22**。
    - 驱动 `package/WifiNet.cpp` 的 `kCardCaps` 现在报的是 {2, 3, 6, 9, 10, 14, 17, 19, 46}，没有 22。
    - 平板的 26C5035r 是不是同一处判断，还没核对（要从 OS 镜像的 dyld 缓存里看）。
  - 查过上游，没有：
    - 仓库：Ath12kWifi（`origin/main` 只多了 #6 构建修复）、sheng（11-15 以后只有文档）、UniXNU 和 CrossDarwin 的 PR 和 issue；
    - 关键词：wifi hidden、auto-join、wifi、wifi auto、`CardCaps`、`directed`、`3903`。
  - 还不知道的：普通扫描为什么 12 s 拿到 0 个结果（扫描完成事件没来，还是没按指定信道扫）。要驱动的 `wifi-net` 日志才能分清。
  - 用户选了改驱动（11-17 10:2x）。平板的 26C5035r 也核对过：从 OS cryptex `141-22145-021.dmg` 的 dyld 缓存里看（shadow 方式挂载，原镜像不动；`ipsw dsc disass`）：
    - `Apple80211Scan` 一样是 `ldrb w8, [x19, #0x5a]; tbz w8, #0x6`；
    - `__getScanData` 填的类型 86 结构也一样：
      - `+0x8` 是网络名个数加 1，多的那一项是全零的通配项；
      - `+0xc` 起每项 40 字节 `{版本, 长度, 名字[32]}`，最多 9 个名字；
      - `+0x19c`/`+0x1a0` 是 BSSID，最多 15 个；`+0x200` 扫描类型；`+0x210`/`+0x214` 信道；结构共 0x14e8 字节。
  - 普通扫描 12 s、0 个结果的原因找到一层：
    - 驱动把扫描请求放进 `nw_mainline.c` 的 `ui` 信箱，由用户态的 `/private/var/ngpu/bin/unixnu-wpa_supplicant`（launchd `org.unixnu.wifi.supplicant`）取走去扫；
    - 12 s 内没有回报，就算这次扫描完成、没有结果（`scan_deadline = lx_now_ms() + 12000`）；
    - 所以唤醒后那一分钟，supplicant 没在处理扫描。为什么没处理还不知道：supplicant 不写统一日志，驱动日志只在板级日志里。
  - 改动（sheng `fcee9fa`，证据 `31562cb`）：
    - `package/WifiScan.h`：
      - 能力位表加上 22，其余照旧（46 等）；
      - 类型 86 的解析：有通配项或多个名字时扫全部网络，只有一个名字、没有通配项时定向扫它；
      - 一次定向扫多个名字（真正隐藏的网络）要同时改 Ath12kWifi 的 `ui` 信箱，没做。
    - `WifiNet.cpp` 改用这个头文件：类型 86 解析完以后，和类型 10 走同样的缓存、已连接和真正扫描三条路径；前 16 次请求会记一行 `wifi-net: named scan: ...`。
    - `kern.unixnu_wifi_log`（`BootDiagExport.c` + `package/WifiLogExport.h`）：只读，给出驱动最近 512 行日志，从旧到新。
    - 主机检查：
      - `check-wifi-scan-host.py` 31 项，改之前是失败的（能力位里没有 22）；
      - `check-wifi-log-export-host.py` 11 项，改之前同样是失败的。
    - 两份源文件用内核参数编过，没有新的警告。
    - sheng 其他主机检查里有 4 个失败，原来就失败，和这次改动无关：
      - `touch`、`boot-progress`、`gpu-power`：sheng 里没有 `drivers/QcomGeniSpi`；
      - `mhi-boot`：`mhi_boot_host.c:102` 报 `-Wmissing-field-initializers`。
  - **cd13 第 3 级（合盖）通过，但之后 Wi-Fi 一直连不上**。以下全部取自 cd14 开机后读到的、留在盘上的 cd13 统一日志（平板时间 19:08 起）：
    - 19:08:38 合盖：`sleep reason Clamshell Sleep`，`sleeping, lid closed`。
    - 合着盖时，60 s 定时器叫醒了 8 次，每次约 10 s 后又以 Clamshell Sleep 睡回去（sleeps 3→10）。
    - 19:19:59 `woke by lid (intid 240) after 36328 ms; sleeps 11`。之后盖子又报了合上、打开，19:22:19 `woke by lid after 3429 ms; sleeps 13`。全程 `cpu_off failures 0`。
    - 小毛病：入睡没走到处理器那一步就醒时，仍会打印一行 `woke by …`，带的是上一次的统计（19:20:07 那行和 19:19:59 完全相同）。
    - 19:22:47 其实已经连上了，拿到了 IPv6 地址。19:22:48 airportd 换了一个新的私有 MAC（`PRIVATE MAC: Successfully created private MAC`，`[DISASSOC] Will disassociate due to new association request`），之后每次连接都在约 10 s 后以 `-3905` 失败。用户手动连和关掉再开 Wi-Fi 都不行，只能强制重启。
    - 怀疑：真正的原因还是 supplicant 不处理请求，扫描 12 s 超时，连接也一样超时；换 MAC 可能只是碰巧。没有驱动日志，没法确认。
  - **cd14（11-17 11:13 构建，内核 `bb8e28de`，载荷 `32d330de`）**：
    - 另存 `.cd14-bb8e28de`、`payload.cd14-base.img`；测试镜像 `boot-v4-payload.bigwin-cd14-sleep.img`（`1f2dbcb8`），载荷 `c4585fd1`；日常文件已还原，哈希都对。
    - 12:03:59 从内存启动。
    - 构建卷又断开过一次，而且 sparsebundle 被挂了两份（disk6/7 和 disk8/9，都没装载）。两份都卸掉后只挂一份，`verifyVolume` 通过。
  - **cd14 上机：开机后还是没有自动连上**（等了 6 分钟，最后用户从系统设置手动连上，`WiFiNetworkJoinReason = Settings`，地址换成了 `.231`）：
    - 修复本身起作用了：auto-join 的带名字扫描不再 `-3903`，驱动收到了 `named scan: len 5352, read, names 1, wildcard 1, scan type 1`（5352 = 0x14e8）；
    - 但这些扫描约 12 s 后结束，结果为 0（15:39:07 那次 11.8 s；15:46:38 那次 11.97 s 后 `Operation canceled`）。也就是 supplicant 没有在 12 s 内回报。所以这个问题开机时也有，不只是唤醒后；
    - 连上后 airportd 又记了 `Unable to detect … as broadcast or hidden`；
    - 查 airportd 日志要按进程号：网络时间到了以后平板时钟会往前跳，`--last` 会漏掉开机早期的日志；
    - supplicant 处理 UI 扫描请求的地方是 `nw_supplicant_frontend.c`：执行 wpa_supplicant 的 `SCAN` 或 `SCAN ssid <hex>`；被拒绝时会马上报 BUSY，不会拖满 12 s。所以 12 s 说明它接下了请求却没有回报，或者请求根本没到它手上。
  - **cd14 开关 Wi-Fi 的实验（平板时间 20:26:38 关，20:26:52 开，之后用户手动连接）**，读到的驱动日志在 `out/boot-logs/cd14-1117-1214/wifi-toggle.log`：
    - `power set 1`、`wifi: radio on applied` 之后，`named scan … names 2, wildcard 1` 连续 3 次（后两次被合并）。100 ms 后只有一行 `Found new beacon on frequency: 5180 MHz`，再没有扫描完成的记录。
    - airportd 那边：实时扫描（5g36、2g6）`duration=12027ms, results=0`，正好是驱动的 12 s 超时。只查缓存的扫描结果为 0：驱动手里的 19 个结果是 20:12 连上之前扫的，`maxCacheAge=20000`。
    - 连着网时的扫描走"回缓存"那条路径，每次 2.00 s。
    - 用户手动连接：`join` 之后 0.4 s 就到了 sta 6（UP）。所以经 supplicant 的连接没问题，问题只在没连网时的扫描。
    - 扫描真正完成时，驱动收到 `NW_CONTROL_SCAN_DONE`，进 `nw_mainline.c` 的 `event()` 处理，但这一步不写日志。要分清是 supplicant 没发起扫描，还是 cfg80211 扫描没完成，得在 Ath12kWifi 里加日志：扫描请求交给 supplicant 的结果、`NW_CONTROL_SCAN`、`SCAN_DONE`（是否中止、BSS 数）。
  - **唤醒时的彩条**（用户：三种唤醒都有，黑屏 → 黑屏加不到 1 s 的彩条 → 桌面）。cd13 第 2 级唤醒，平板时间 18:29:35：
    - .046 背光恢复（`kIOMessageSystemHasPoweredOn`）；
    - .047 powerd："Display is asleep on activity tickle. Lets turn it on"；
    - .070 WindowServer `Display:Power Will Wake`、`set_display_state off→on`、`Display 1 set power state 1`；内核 `IOMobileGraphicsFamily request_power_change … powerstate 1`；
    - .161 `Did Wake`；.277 / .328 内核 `vt 5 first dfrm`、`vt 5 direct, 6 surfaces`。
    - WindowServer 醒来后不通过背光驱动重新设亮度，只设了 headroom hint。
    - 结论：背光比 WindowServer 打开显示器早约 25 ms，比第一批画面早约 0.25 s。修法：背光等显示器重新上电、出了第一批画面以后再恢复，并加一个超时兜底，免得屏幕一直不亮。
  - **cd15 的两处改动（11-17 12:5x，用户选的是"等画面出来再亮"和"先加诊断日志"）**：
    - 先查过上游，没有：UniXNU、CrossDarwin 的 PR 里搜 backlight wake、backlight、wifi scan；历史里搜 color bar、first frame、backlight 和 wake/resume。Ath12kWifi 上游只多了 #6，是构建修复。
    - 背光（sheng `1466e22`，证据 `7681063`）：
      - 醒来后背光先保持暗，每 20 ms 看一次显示驱动的帧计数 `native_legacy_swapstat` [7]+[9]+[10]（拷贝、翻页、latch，GopFramebuffer 导出，弱引用）；
      - 多出 2 帧，或者过了 1.5 s，就恢复亮度；拿不到计数时固定等 0.6 s；等的过程中又要睡，就取消；
      - 日志改成两行：`system awake, panel waits for the display`，和 `panel back to its level N ms after the wake, M frames shown`；
      - `lid_backlight_wake_ready`（LidClamshell.h），`check-lid-clamshell-host.py` 51 项，改之前是失败的；用内核参数编过，没有警告。
    - Ath12kWifi 本地分支 `local/scan-diagnostics` `0d8758a`（基于 `39cc47b`）；sheng `1c48ecb` 指向它，`5a17da0` 改了记录里的固定版本：
      - 只加日志，限频（前 64 次、之后每 64 次，失败的每次都记），不改行为；
      - 记四件事：扫描请求交给 supplicant（`scan request N to the supplicant: ssid L -> R`）、12 s 无人回（`unanswered after 12 s`）、supplicant 发起的 cfg80211 扫描（`supplicant scan N: S ssids, F frequencies -> R (held request X, message Y)`）、扫描完成（`scan done N: status S, K networks held`）。
      - 怀疑的原因：`nw_cfg80211_control.c scan()` 在 `rdev->scan_req || rdev->scan_msg` 时返回 `-EBUSY`。如果关 Wi-Fi 或睡眠打断的扫描一直没收尾，之后的扫描就会全部被拒；连接不走这条路径，所以不受影响。
      - `test-mainline-runtime.py`、`test-cfg80211-control.py`、`test-control.py`、`test-control-endpoint.py` 都过。
    - 没做的小问题：入睡没走到处理器那一步时，会打印一行带着上一次统计的 `woke by …`。
  - 11-17 13:0x 推送到用户自己的远端：核心 `21873ff`、ArmCpu `a2c5dd3`、sheng `6d9de92`。新建了 fork `zus12873/Ath12kWifi`（公开），推了 `local/scan-diagnostics`（`0d8758a`），sheng 的 `.gitmodules` 改成从这个 fork 取。
  - cd15（11-17 12:49 构建）：内核 `20acb2ca`，载荷 `dfd6c18b`，另存 `.cd15-20acb2ca`、`payload.cd15-base.img`。测试镜像 `boot-v4-payload.bigwin-cd15-sleep.img`（`65b985fa`），载荷 `90f8e10a`。内核里有两行背光新日志和四条扫描诊断。日常文件已还原；来源记录 `cd15-build.json`、`cd15-images.json`。
  - **cd15 上机（13:12 第二次启动；第一次 12:59 那趟用户没来得及连 Wi-Fi，重启了）：Wi-Fi 扫描为什么拿不到结果，查清了**。日志在 `out/boot-logs/cd15-1117-1315/wifi-boot.log`：
    - 每一轮都是：
      - `scan request N to the supplicant: ssid 0 -> 0`，送达成功；
      - 约 50 ms 后 `supplicant scan K: 1 ssids, 0 frequencies -> 0 (held request 0, message 0)`，cfg80211 扫描正常开始，没有 `-EBUSY`；
      - 12 s 后 `scan request K unanswered after 12 s`；
      - 再过约 3.7 s 才 `scan done K: status 0, 13 networks held`。
    - 全频段扫描每次约 15.7 s（30041→45774、48253→63985、64173→79893、81019→96739 ms），比驱动 12 s 的期限长。airportd 每次在结果出来之前就拿到"完成、0 个结果"，开机时 airportd 自己也会在约 12 s 时取消扫描。
    - `0 frequencies`：airportd 只要扫 2 个信道（5g36、2g6），驱动没把请求里的信道表交下去，supplicant 就扫了全部频段（WCN7850 还包括 6 GHz）。
    - 对照：连接时那次扫描（`2 ssids, 1 frequencies`）205 ms 就完成了。
    - 怀疑过的"`scan_req` 卡住、之后的扫描全部 `-EBUSY`"被排除了。
    - 这趟还是用户从控制中心手动连的（21:15:19，`WiFiNetworkJoinReason = ControlCenter`）。
    - 修法：把请求里的信道表一路交到 supplicant。WifiNet 解析类型 10 和类型 86 的信道表（类型 86：`+0x210` 个数，`+0x214` 起每项 12 字节）→ `nw_wifi_scan` 带上频点 → `ui` 信箱 → supplicant `SCAN freq=…`。要改 Ath12kWifi 的 `nw_abi`、`nw_mainline.c`、`nw_supplicant_frontend.c`，以及 sheng 的 `WifiNet.cpp`。
  - **cd15 彩条测试（平板时间 21:17:55 `pmset sleepnow`，开着盖）**：
    - 用户：没有彩条了，但按了很多次电源键才看到桌面，之后手动连上了 Wi-Fi。
    - 背光修复起作用了：两次唤醒都是 `panel back to its level 40 ms / 817 ms after the wake, 2 frames shown`。
    - **新问题：开着盖入睡，3 ms 就被"盖子"叫醒**：21:18:26.633 `IOCPUSleepKernel enter`，.709 `woke by lid (intid 240) after 3 ms; sleeps 1, spurious 0`。盖子一直开着，所以是误唤醒。
      - 推测：盖子那根 TLMM 线还留着之前锁存的中断状态。`ShengSleep.cpp prepare()` 只在盖子合着时清它（"A closed lid's status is … cleared"），开着盖时不清，一睡下汇总中断就挂着；`shouldWake(240)` 只看"盖子开着"，于是马上叫醒。
      - cd13 第 1、2 级也是开着盖，但没出现这个问题，可能那次开机后盖子没有动过，没有锁存状态。
    - 这次误唤醒是完整唤醒：`requestUserActive … for sheng lid`，21:18:26.809 `Display state: On`，loginwindow .875 `startUnlock`。之后一直到 21:28:37 才因为闲置 10 分钟 `Display state: Off`，中间没有任何睡眠。
      - 用户这段时间看到的是黑屏，按电源键没用，直到 21:32:03 合盖、21:32:10 开盖才看到桌面。是背光没亮，还是锁屏界面没画出来，日志分不清。
      - 21:32:33 那次唤醒同样是盖子 3 ms（开盖发生在入睡的 30 s 里，算正常），背光走同一条新路径，817 ms 后恢复，用户看到了桌面。所以新的背光路径本身是好的。
    - 吞键只在电源键叫醒时开启，这次没开，用户的按键都正常上报了。
  - **cd16 要带的修复（11-17 14:xx，用户选"两个一起修"）**：
    - Ath12kWifi `b455da9`（`local/scan-diagnostics`，只在本机，还没推到 fork）：
      - `nw_wifi_scan_frequencies()`，最多 `NW_WIFI_SCAN_FREQUENCIES_MAX`（32）个 2400–7125 MHz 的频点；
      - UI 请求带 `NW_CONTROL_ATTR_SCAN_FREQUENCIES` 交给 supplicant，前端把它放进刚排上的手动扫描的 `manual_scan_freqs`；
      - 不能用 `SCAN freq=`：它要用驱动的信道表把频点过一遍，`driver_sheng` 不报信道表，所以命令会返回 FAIL，测试里已确认；
      - `mainline_runtime_test.c` 新用例、`supplicant_test.c` 新增 `scan` 模式，改之前都是失败的；Ath12kWifi 其余测试都过，macOS 版 supplicant 能编过。
    - sheng `7d088df`（证据 `60f116d`）：
      - `WifiScan.h` `sheng_wifi_scan_frequencies` 解析类型 10 和类型 86 的信道表，转成频点交给 `nw_wifi_scan_frequencies`；
      - `ShengSleep` `sheng_sleep_clear_lid_status`：入睡准备时不管盖子开合，都清掉盖子线上的旧状态；
      - `check-wifi-scan-host.py` 45 项、`check-sheng-sleep-host.py` 467 项，改之前都是失败的；两份源文件都用内核参数编过。
  - **cd15 合盖很久以后，开盖和电源键都叫不醒（用户 13:5x）**：
    - 14:01 用 cd12-read 开机读出了 cd15 那趟的板级日志：`out/boot-logs/cd12read-1117-1405/`（本地）。日志写到开机后 2533 s（约 13:55）为止。
    - 合盖期间定时器叫醒 → Clamshell Sleep 正常循环了 12 次（`woke by timer … sleeps 12, cpu_off failures 0`）。
    - 第 13 次入睡到 trace point 0x18（停副核）时 panic：`machine_routines.c:948 Assertion failed: getCpuDatap()->cpu_signal == SIGPdisabled (0x0 == 0x80000000)`。panic 之后没有重启，所以一直黑屏。
    - 原因：
      - `ml_cpu_down` 先把 `cpu_running` 置 FALSE，再由 `cpu_signal_handler_internal(TRUE)` 给自己打上 `SIGPdisabled`，然后断言只剩这一位；
      - 启动补丁（bluseliu50，`zzzz-sheng-ipados27-bringup.patch`）里的 `sheng_sigp_recover`，会在别的核给一个"已启动但挂着 `SIGPdisabled`"的核发 IPI 时，把这个标志清掉，用来补救启动时丢掉的自我 IPI；
      - `ml_cpu_down` 并不清 `StartedState`，所以下线途中的核也会被这样"补救"。
    - 修复：sheng `59d0346`，在 `sheng-platform-sleep.patch` 里给 `sheng_sigp_recover` 加上 `cpu_running` 条件。
      - 不会误伤原本要补救的情况：启动时 `cpu_running` 在 `cpu_init` 里就置了 TRUE，早于 `processor_cpu_reinit` 等信号。
      - 验证：在构建树打过补丁的文件上先反向打回旧补丁，再 `git apply --check` 新补丁，能打上；改过的 `cpu_common.c` 用 XNU 自己的编译记录能编过。主机上测不了，要上机连续睡眠多次验证。
      - 上游 `01e3d92` 放宽的是另一个断言（`processor_cpu_reinit` 里的 `assert_ml_cpu_signal_is_enabled`），会随这次合并进来。
    - 没解决：睡眠中 panic 之后不会自动重启，cd12 和 cd15 各出现过一次，原因没查。
  - **用户要把 sheng 上游最新的 main 合进新镜像（11-17 14:xx）**：
    - `upstream/main` `8a85350`，比我们多 768 个提交。合并基点是 10-21 的 `7562a77`：上游把很多和我们分支上相同的改动压成了别的提交。
    - 在单独的工作树 `../UniXNU-sheng-merge`、新分支 `integrate/upstream-20261117` 上合并。`integrate/upstream-20261116` 和主检出目录都不动。
    - 33 个文件冲突，约 150 处。我们自己的提交按文件列在 `out/merge-own-commits-20261117.txt`（本地）。
    - 上游改了我们本地保管、从不提交的 9 个 macOS 27.3 根卷策略文件：主检出目录切分支前要先备份这 9 个文件，切完放回去，并核对哈希。
    - 上游 `4d86261` 去掉了启动参数的 `sheng-` 前缀；`49eb58e` 修了键盘壳输入恢复；`9c92108` 把 macOS 关机和重启接到了 PSCI。
    - **合并完成（11-17 14:1x）**：合并提交 `9e03d86`，再摘入 SIGP 修复 → `5909daa`。三个助手分领域解了冲突，由我统一复查、暂存（只暂存那 33 个文件）后提交。
      - 驱动和测试：这些文件在上游的版本，和我们第一次改它之前的版本逐字节相同，所以结果就是我们的版本，上游的内容不会丢。
      - 启动日志、复位、诊断、存储：结果是我们的版本，它包含了上游的全部内容；`BootWatchdogPolicy.c` 用上游的，上游已经收进了 `enable-jobs`。
      - 实验室和 CI 脚本：用上游的。
      - board.toml：保留我们 12 GiB 的内存值、200 MiB 载荷、内核表和 `ci-mps=0`；其余取上游的（GENI SPI、模板、`timeout=1`、install 表、桌面参数）。
        - 不要 `autoreset=7200`：加上它这一行就超过 1000 字节，而且平板开机 2 小时后会进 fastboot，在那里不充电。
        - 不要上游无人值守实验室用的诊断参数（`diag`、`diag-export`、`gpu-trace`、`log-video`、`log-bluetooth`、`build-tag`），这样测试镜像加的参数还放得下。现在这一行 905 字节。
        - 保留 `uefi-watchdog=1`：它和睡眠时的喂狗是同一套机制，panic 后停止喂狗，看门狗会把系统复位。
      - `.gitmodules`：用上游的，Ath12kWifi 指向 fork；子模块定在 `b455da9`。
      - 补丁序列：用上游的顺序，`sheng-platform-sleep.patch` 放在最后。
      - porting.toml：每个区两边取并集。
    - 合并后的整套 154 个 XNU 补丁，在干净的 XNU（`ac9718f`）上全部能打上，其中包括 `cpu_running` 修复。
    - 检查：porting record 18 个区；睡眠、Wi-Fi 扫描、日志导出、盖子、启动日志、读回上次日志、键盘壳、键盘服务、触摸、看门狗策略的主机检查；核心 `check-unixnu.py`。全部通过。
    - 主检出目录已切到 `integrate/upstream-20261117`。那 9 个根卷策略文件：先备份到 `out/policy-backup-20261117/`（附 sha256），再另外 stash 一份（stash@{0}），切换后放回，哈希 9/9 一致。合并用的工作树已经移除。
    - 子模块都已初始化，版本一致；ShengUfs 现在是上游的 `9d527ae`，里面仍有 `native_ufs_part_read`。
    - 还不确定：200 MiB 的载荷装不装得下上游的桌面配置（上游是 256 MiB），要真正构建才知道。
    - 第一次构建 cd16（11-17 14:2x）在 `archive-20-build-gop-legacy-display-27` 失败：
      - 报错：`build-sheng-source-drivers.py` 找不到 `<tree>/profiles/os/ipados-27.0.1-24A446/profile.toml`；
      - 原因：sheng 上游新的 `build-gop-legacy-display-27.py` 调这个核心脚本时不再传 `--profile`，依赖核心上游的 `66535d1`（rponeawa，"pass the selected OS profile to source driver compilation"）。
      - 修复：核心 `aff8f4f`，`cherry-pick -x 66535d1`。构建时用 `UNIXNU_OS_PROFILE` 指向选定的配置，没设时回到核心仓库自己的 `profiles`；内核的参考源码里加上 `IOHIDFamily`。
      - `check-unixnu.py` 通过；macOS 配置里 `IOHIDFamily` 和 `IOStorageFamily` 都钉了版本。
    - 第二次构建（用户 15:0x 重跑）过了 archive-20，在内核链接失败：`Undefined symbols: _nw_wifi_scan_frequencies, referenced from WifiNet.late.o`。
      - 原因：sheng 的 `scripts/build-ath12k-wifi.py` 给 Wi-Fi 模块的全局名加前缀 `nwk_`，只留 `keep` 里的入口；我在 Ath12kWifi `b455da9` 新加的 `nw_wifi_scan_frequencies` 不在里面，被改成了 `nwk_nw_wifi_scan_frequencies`。
      - 修复：sheng `011dacf`，把它加进 `keep`；新增 `scripts/check-ath12k-exports.py`：`include/nw_abi.h` 声明的函数只要会被改名就失败（先看它失败，再改，通过：24 个函数）。单独重编模块，`nw_mainline.o` 里是 `T _nw_wifi_scan_frequencies`。
      - 这是我们自己的新函数，上游不会有，没查别的仓库。
    - **核心合上游 main（11-17 15:xx，用户："先合，然后再构建"）**：新分支 `integrate/upstream-20261117`，合并提交 `4577fd6`（上游 `ae4ee0e`），之后不再落后上游。
      - 593 个上游提交里，大部分之前已经从 CrossDarwin、rponeawa、bluseliu50 的分支进来过。真正新的：AdrenoMetal R2507（`f7b4ed1`）、`toolchain` 模块（`--kernel-sdk`/`--kernel-tools`，不设时和原来一样用系统 Xcode；本机没设）、固件的 `clang_bin`、核对过的原始根卷镜像、macOS 27 桌面附加任务、上游收进去的 `local-tools`（rponeawa 又改过）。
      - 124 处冲突的取舍：
        - 设备页面、设备记录、`devices.toml` 由文档机器人生成：取上游。其他文档取上游，只保留两行我们的：`owned_memory_floor`（代码里还有），`--auto-login` 那行（`make-macos-data-seed.py` 仍要求 `--user`、`--user-stdin` 或 `--interactive-user`）。
        - DarwinBoot、Adreno740：我们的（上游的版本加我们的 9 GiB 窗口和页表位图提交）。AdrenoMetal：上游的 `f7b4ed1`，我们原来的 `26d4902` 在上游改写历史后归档的分支上，90 个提交按内容都已在 `f7b4ed1` 里（`git cherry` 全是 `-`）。`components.toml` 跟着这几个指针走。
        - `window-outside-memory-adoption.patch`：我们的（上游的加 `memory-outside-report` 诊断）。合并没有改任何内核补丁。
        - `scripts/unixnu/devicetree.py`：我们的（窗口到 9 GiB、`owned_memory_floor`）。
        - Metal 构建脚本、`build-boot-runtime.py`、`run-local-kernel.py`、`cli.py`、`firmware.py`、`ipsw.py`：上游的。我们那边只有同一批改动的旧版本；上游也已经有我那处"挂载点放到系统临时目录"的修复。上游还去掉了列 Metal 库时的 `sudo -n`（新的 `list-metal-libraries.py` 跳过要 root 的目录）。
        - `local-tools`：上游的，加回 `kernel-compile-check.py --record`，`record-build-provenance.py` 里加回 `boot/boot-bigwin.img`。注意上游的 `kernel-compile-check.py` 必须给 `--tree`。
      - 合并前查过：上游新增的 33 个文件，本地都没有同名的未跟踪或被忽略的文件，不会被悄悄覆盖。
      - 检查：`check-unixnu.py`；`scripts/unixnu/test_*.py` 5 组；`tests/build`、`tests/macos`、`tests/terminal`；`tests/codesign`（要用 `--source <tree>/.cache/xnu-work/bsd/kern/ubc_subr.c` 跑，9 个）；`local-tools/tests` 87 个；sheng 的 porting record 18 个区；sheng 脚本引用的核心文件现在都在。全部通过。
        - `local-tools/tests/test_window_layout.py` 原来钉的命令行长度是 923，sheng 合并后参数是 905 字节，实际是 937。已改，核心 `bd0a16d`。
        - sheng 有 7 个主机检查不过，和这两次合并无关：3 个要参数或样本（`quartzcore-blur`、`quartzcore-turnip-cache`、`vt-parameters`）；4 个在 sheng 上游 main 上也是坏的（`boot-progress`、`gpu-power` 找不到已删除的测试源文件；`touch` 去 sheng 里找已经搬到核心的 GENI SPI；`mhi-boot` 新 clang 下 `-Werror` 报 `missing field 'space' initializer`）。
    - 第三次构建（用户 15:43，已在 `local/on-main-20261117` 上；终端提示符里的 `integrate/upstream-20261116` 是切分支前的旧提示）：Metal 库清单过了（434 个路径），停在 `.cache/gpu-reference/metal2vulkan: source revision differs from its pin`。
      - 原因：上游 `5f93377`（rponeawa，R2507）把 metal2vulkan 钉到 development 的 `46e7cc96`；缓存里还是 cd7 取的 `555b13d`，加上构建打的补丁（66 个文件）。`build-boot-runtime.py` 的 `checkout()` 只在目录不存在时才取。
      - 处理（15:5x）：缓存改名留作 `metal2vulkan.555b13d-cd7-20261116`，照 `checkout()` 的步骤取了 `46e7cc96`（干净，0 个改动）。`git apply --check` 新补丁 `0063-main-optimizations-on-development-46e7cc96.patch` 能打上（70 个文件）。
      - `check-metal2vulkan-pin.py` 报 FAIL，但不影响构建：上游 AdrenoMetal `f7b4ed1` 的 `bridge/patches/` 里还留着 0002 到 0062 共 29 个旧补丁，构建只列 `0063`，检查要求目录里只有构建列出的补丁。构建脚本都不调这个检查。上游的问题，没报。
  - 上机要看（cd15）：
    - 唤醒时没有彩条，日志里 `panel back to its level` 的毫秒数和帧数合理；
    - 开机后、开关 Wi-Fi 后马上读 `sysctl -n kern.unixnu_wifi_log | grep -E "scan request|supplicant scan|scan done|unanswered"`，看扫描卡在哪一步。
  - 上机要看（cd14）：
    - 开机后不碰控制中心就自动连上；
    - 睡眠唤醒后很快自动重连；
    - airportd 不再记 `Unable to detect … as broadcast or hidden`，网络不再算隐藏；
    - `sysctl -n kern.unixnu_wifi_log` 里有 `named scan` 行。
- 整条分支的审查（11-16 晚）结论是"改完再构建"，下面是问题和处理情况：
  - 两处严重问题，正在改：
    - 启动核恢复时没给自己发 IPI，`processor_cpu_reinit` 会一直等，结果每次唤醒都挂住；
    - 黑屏唤醒（dark wake）里不会给 general interest 客户发唤醒通知，所以请求完整唤醒的代码根本跑不到。
  - 上机前要先确认 Gunyah 看门狗是不是开着：开着的话，超过 30 秒的睡眠会被复位。
  - 详情在 ledger。
- **cd9-s2 上的熄屏耗电和键盘壳掉线（11-16 平板时间 06:5x，只读）**
  - 这一趟跑的是 cd9-s2（04:16 起）。cd10 带掉线日志，但还没上过机。
  - 耗电：
    - 05:42:29 拔电时是 90%，05:42:39–06:48:30 熄屏 66 分钟。powerd 记录的电量依次是 06:46 89%、06:51 88%、07:02 86%。
    - 这个百分比是跳着变的：64 分钟没动，后来 16 分钟掉了 3 点，不能拿来算耗电。
    - 直接读电流：熄屏时稳定在约 1.0 A（4.24 V，约 4.3 W）；亮屏时 1.5–1.6 A（约 6.5 W）。按 9225 mAh 算，熄屏每小时约掉 11%。
    - 熄屏时背光仍在 1390/2047。
    - 电量计原始的 mAh 只在内核变量 `native_battery_raw` 里，ioreg 读不到；ioreg 里的 `AppleRawCurrentCapacity` 是 8，数值不对。
  - 键盘壳：
    - 时间线：06:51:15.246 HID 设备被移除，0.55 秒后（.792）重建；.863 macOS 重新加上 "Xiaomi Keyboard"；之后一直在。前面 06:50:49 刚自动熄屏。
    - 控制器仍是阶段 7，I2C 0 错误，中断和帧都在涨，attach 共 3 次（开机 1 次、04:23 用户插拔 1 次、这次 1 次）。
    - 结论：平板这一侧的 I2C 和 WN8030 没有崩溃或重载，是控制器自己报了 detach 再 attach，也就是控制器和键盘壳之间断了半秒。是触点问题还是键盘壳自己的 MCU 重启，要等带帧记录的 cd10 或之后的镜像才分得清。

上一阶段（2026-11-16）：**用户调整了方向，计划是 `docs/superpowers/plans/2026-11-16-lid-safari-memory-charging.md`（用户已批准）。** 顺序：工作流 0（整合分支跟上上游 main，构建 cd6，上机 CD6-1，顺带验 Safari、合盖熄屏的第 0 步、第一组充电读数）→ 合盖熄屏 → 充电 → 内存 → 真睡眠的设计。要点：
- 合盖：真睡眠在这块板子上不存在（`../UniXNU-sheng/board.toml:138` 的 `sleep-disabled = 1` 是故意的，没有挂起和恢复）。先做"合盖熄屏、停触摸、告诉 macOS 盖子合上了"，之后再写真睡眠的设计。上游没有现成的。
- Safari：用户的现象是图标是问号、点了没反应，正是上游 ShengUfs#12（11-15 合并）修的；它已经在 sheng 整合分支里，日常镜像里没有。不改代码，随 cd6 验证。
- 内存：引导程序只交出 11.68 GiB，扣掉固件占的部分，上限约 10.8 GiB，12 GiB 做不到。用上游 uefi-sheng #6 的内存表方案，放开它只认 8 GiB 的门槛，再把窗口分步推到 9 GiB、10 GiB。
- 充电：rponeawa 的充电认证已经在整合分支里，macOS 真机上没跑过。用户用的是第三方 PD/PPS 头，只会走到电量计认证；先量，和 `charge-auth=0` 的变体对照，再定。
- 11-15 23:40 起"整合别人领先的内容"的记录在本块后面那几条里；构建停在要 root 的 Metal 库清单这一步（要用户自己在终端里 `sudo -v` 后跑构建）。
- **工作流 0 第 1 步做完（11-16）：三个仓库的整合分支都合了最新的上游 main**（拉取在 11-16 上午）。
  - AdrenoMetal `033cb71`：上游只有合并提交，README 取上游的写法；`ci-mps=0`、`MadeBeforeRecovery` 兜底都还在。
  - 核心 `2d0d49f`：
    - 内核补丁列表改用上游 #268 的 `cshash-compressed-text-revalidation.patch`（用户 11-16 选的"用上游的"）；
    - `components.toml` 里 AdrenoMetal 指 `033cb71`，QcaBluetooth 取上游的 `effe4ec`；
    - `bootimg.py` 取上游的模板设置和"空 ramdisk 地址为 0"，留本地的 ramdisk 分块压缩和限额检查；
    - `util.py`、`test_boot_template.py` 取上游的；蓝牙文档取上游的，macOS 文档留本地的。
    - `check-unixnu.py` PASS；`scripts/unixnu` 42 个、`tests/macos` 41 个、`tests/build` 9 个测试 OK（要关沙箱，沙箱里不能开端口和伪终端）。
  - sheng `0b805a3`：
    - 本机的板级补丁 `sheng-text-fixup-verified-pagein.patch` 从 `series` 里拿掉，留注释说明原因；
    - `board.toml` 的内存设置全留本机的（合并后用 `tomllib` 读过：窗口 `0x240000000`、起点 `0x8C0000000`、bank 1 整段排除、outside 16 段；上游 #96 的 64 段等内存第 3 步和内核一起改）；上游去掉了 v0 模板一节，跟着去掉；
    - `porting.toml` 按键合并，用了 `local-tools/resolve-porting-conflicts.py` 新加的 `--base`：这次有多个合并基，git 拼出来的虚拟合并基里自己就有冲突标记，用 `6866eae`；
    - 显示、键盘、USB 三个区各补了一条 finding（显示构建脚本加编了 `ShengChargeAuth`）。
    - `porting-record check --base upstream/main` PASS（18 个区）。看门狗策略、电池、充电认证、键盘壳、键盘服务、wn8030 的检查都 PASS；`check-touch-host`、`check-boot-lifecycle` 要 SoC 的 kit 布局，本机没有，没跑。
  - 合并前查过"对方新增、本地被忽略"的文件，两个仓库都没有。
  - 已有的不一致，没改：`components.toml` 里 ArmCpu、DarwinBoot 记的是上游旧版本，实际子模块是它的后代（rponeawa 的 CPU 汇编修复、本机 9 GiB 加载器）。构建按子模块的 gitlink 拉代码（`feeds.py` 的 `update_submodules`），cd 系列以前都是这样构建的。
  - 风险：板级补丁换成上游补丁后，cd6 上机要专门看 WindowServer 有没有被代码签名杀掉、日志里有没有 APFS 哈希不符；出问题就换回板级补丁。
  - 下一步（第 2 步）：等用户接上外置盘。
- **工作流 0 第 2、3 步，加上合盖熄屏第 1 步（11-16）**
  - 外置盘接上后，构建盘的 APFS 卷挂不上，`diskutil verifyVolume` 报 "Container superblock is invalid"。
    - 原因是有一份残留的挂接。`hdiutil detach disk6` 后用 `-nomount` 重新挂接，`fsck_apfs -n /dev/rdisk6s2`（只读检查）报容器和卷都 OK，再 `diskutil mount disk7s1` 就挂上了。没做任何修复。
    - 以后遇到同样的报错，先卸掉再重新挂接一次，不要直接修。
  - **输出目录换了一层**：现在是 `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/`（下面记作 `<output>`）。
  - 日常文件哈希都对：`kernel.macho` `33d294c8`、`payload.img` `8a36fe56`、`boot.img` `35f03ec4`、`boot.json` `aeaf38ac`、`runtime/data.dbr` `39f9ad3f`、`boot/boot-bigwin.img` `5c926a3f`。
    - 原有的备份：`kernel.macho.daily-33d294c8`、`payload.daily-8a36fe56.img`。
    - 这次新补的：`boot/boot.daily-35f03ec4.img`、`boot/boot.daily-aeaf38ac.json`。
  - OS 镜像 `141-22233-021.dmg` 只读挂到了 scratchpad 的 `os-mount`，`build-boot-runtime.py` 会复用这个挂载。构建完要 `hdiutil detach`。
  - **合盖熄屏第 1 步：用户 11-16 同意现在就写，并进 cd6**。sheng 提交 `eb4639c`：
    - `KeyboardProbe.cpp`：把盖子霍尔传感器（GPIO 171）的状态写进 `native_keyboard_lid_closed`。只在线程进入服务循环（第 7 阶段）之后才写，控制器起不来时一直是 0；每次变化记一行内核日志 `sheng keyboard: lid closed/open`。
    - `TouchProbe.cpp` 的 `publish()`，只在 macOS 上：盖子合上后的第一帧改成"没有触点"，让所有触点松开，之后的帧都丢掉；打开后恢复。键盘折到背后时不挡。iPadOS 不变。
    - 判断逻辑在 `package/TouchLid.h`；主机测试 `scripts/check-touch-lid-host.py` 共 115 项，先失败、实现后通过。
    - 两个文件都用内核的编译参数单独编过：TouchProbe 弱引用 `_native_keyboard_lid_closed`，说明 macOS 分支生效；KeyboardProbe 导出这个符号。
    - porting 记录检查和键盘相关的主机检查都 PASS。还没上机。
  - 合盖时怎么检测（用户问的）：
    - 两个霍尔传感器感应键盘壳里的磁铁：GPIO 171 是盖子合在屏幕上，172 是折到背后，都是低电平有效。
    - 两根脚都配成双边沿中断，中断只给计数加一、叫醒键盘线程；线程去抖 15 ms 后读电平，没有中断时每 1 秒也读一次。
    - 合上时以前只停键盘和触控板，触摸屏、屏幕、macOS 的电源管理都不知道。
    - 开机时读一次初始值；之后的中断和轮询要等键盘控制器的固件加载成功才开始。
  - 下一步：用户在自己的终端里 `sudo -v` 后跑构建（命令见对话），我再另存 cd6 产物、还原日常文件。
- **cd6 构建中途修的三处（11-16，用户在自己的终端里跑）**
  - Metal 库清单要挂 SystemOS、App 两个 cryptex，脚本把它们挂在 `<output>/runtime/prepare-*/` 下面，`hdiutil attach` 报 Permission denied：普通用户不能在用户挂载的映像卷里再挂映像。
    - 核心 `d4da38c` 把挂载点改到系统临时目录。这段代码是 rponeawa 的（`make_prime_list`），上游的 `feat/manual-shader-cache-app` 分支也是同样写法，没人修过。
    - 之后清单列出来了：434 个路径，OS 406、SystemOS 28、App 0。
  - 缓存的 `<output>/tree/.cache/gpu-reference/metal2vulkan` 在 `555b13d`，有 65 个文件的改动，和新钉的 `d9236a8a` 对不上，构建停下。
    - 整个目录改名留作备份 `metal2vulkan.555b13d-preserved-20261116`，让脚本重新取。
  - 之后在 Turnip 这一步停下：`Bison 3.7 or newer is required by the IR3 parser`（11:05 那次）。
    - 原因：上游 `1be2950`（rponeawa，已在 `upstream/main`）新加的检查只认 PATH 里的 bison（`/usr/bin/bison` 是 2.3）和 Homebrew 的两个路径。`<output>/tree/.cache/mesa-tools/bin/bison` 里 11-13 放的 3.8.2 它不认。
    - 11:21 装了 Homebrew 的 bison 3.8.2 后就过了。脚本把 `mesa-tools/bin/bison` 换成指向 `/opt/homebrew/Cellar/bison/3.8.2/bin/bison` 的链接。不改代码。
    - 验证（11:53）：单跑 `build-turnip-darwin.py --target macos27` 输出 PASS，`libvulkan_freedreno.dylib` 18437176 字节，Meson 读到 `bison 3.8.2`。下一步：用户在自己的终端里 `sudo -v` 后重跑整条构建。
- **cd7：按最新的上游 main 重新整合（11-16 下午，用户："先按最新的上游 main 重新整合，打 cd7，再上机"）**
  - 为什么：上游三个仓库 10:04 前后都进了 rponeawa 的整合提交（sheng `6056637`、核心 `db9cd2e`、AdrenoMetal `57a1adc`），Adreno740 也合了 #29。主线 GPU 运行时定为 metal2vulkan `555b13d5` 加 `0046` 补丁。cd6 用的是 rponeawa 分支上的 `d9236a8a` 加 `0044`，测出来的不能当上游 main 的证据。sheng 的 main 在 `bc05635` 之后没有新提交。
  - 新分支都叫 `integrate/upstream-20261116`，从 `integrate/others-20261115` 开，cd6 的状态留在旧分支上：
    - **核心 `b35c738`**：合上游 `21d683d`。
      - 运行时、AdrenoMetal `26d4902`（#39，里面已经有我们的 `ci-mps=0` 和 WindowServer 重启兜底）、ArmCpu `acba4ee`、`components.toml`，都取上游的。
      - 删掉 `scripts/data/armdt-platform-psci.patch` 和它在 `build-arm-driver.py` 里的用法，和上游一样。
      - 只留这些：Adreno740 `fd7a0ca`；DarwinBoot `bdb6ff7`（上游目录里记的 `3c75734` 是 10-28 的旧值，比它自己用的子模块还旧）；22 页引导页表；窗口外收编补丁；`devicetree.py` 的 9 GiB；`build-boot-runtime.py` 的挂载修复。
      - `check-unixnu.py` 和三组测试都过。
    - **Adreno740 `local/owned-map-on-main`（`fd7a0ca`）**：上游 `1c9029b` 加上 `462dd74` 的内容。上游没有这个修复，能干净打上；`test_owned_below_window` 和 `test_memory` 都过。只在本地。
    - **sheng `e5a87a8`**：合上游 `bc05635`。
      - 除了下面几样，全取上游：合盖（和 #111 逐字节相同）、测试桩和 `enable-jobs`（和 #109、#110 相同）、`board.toml` 的 12 GiB 设置。
      - `porting.toml` 整份取上游的，再只给保留的改动加描述性 findings（输入、键盘、诊断、配置、USB、打包）。
      - 本机的板级补丁文件删掉；`board.toml` 注释里那句带日期的话改成描述行为。
      - porting 记录检查 PASS（18 个区）；合盖、键盘壳、键盘服务、wn8030、看门狗策略、电池、充电认证、启动日志、GENI I2C 的主机检查都 PASS。
      - 子模块都更新到钉的版本：QcaBluetooth `effe4ec`，ShengUfs `9d527ae`（和 `2b6638b` 同一棵树），QcomDwc3 `d4e96f3`。
  - **根卷策略文件**：上游现在把 rponeawa 的钥匙（`896b3246`）提交进了仓库。
    - 合并提交里这 6 个文件和上游完全相同。
    - 本机的钥匙（`74eace58`）、header 和 `verification.json` 合并前备份在 `out/policy-backup-cd7/`（git 忽略），合并后原样放回工作区，显示为"已修改"。**这 9 个文件的本地改动永远不提交。**
  - 缓存：cd6 的 metal2vulkan 留作 `tree/.cache/gpu-reference/metal2vulkan.d9236a8-cd6-20261116`，让 cd7 重新取 `555b13d5`。OS 镜像已只读挂到 scratchpad 的 `os-mount`。
  - 构建前日常文件：`33d294c8`、`8a36fe56`、`35f03ec4`、`aeaf38ac`、`39f9ad3f`。
  - cd7 构建中途又停了两次，都已处理，日常文件都没被动过：
    1. Mesa 缓存里是 cd6 打的 23 个补丁；上游补丁列表多了 `turnip-darwin-bo-finish-clears-under-lock.patch`（来自 `db9cd2e`），脚本只在全新取源码时才从头打补丁。
       - 旧缓存留作 `tree/.cache/mesa-work.cd6-23patches-20261116`；重新取 `85fda3b`，打了 24 个补丁。
    2. `[kernel] archives needs component entries for: SoftwareAES`：上游 sheng 的 `6056637` 删掉了整张 `["os_overrides"."macos-27.3-26C5035r"."kernel"]` 表（defconfig、配置片段、macOS 的 `archives`），没挪到别处。
       - 没了这张表，macOS 退回用 iPadOS 27 的 `archives`：里面没有 SoftwareAES，根卷策略也指向 iPadOS 的目录。上游核心加上游 sheng 就是这个结果，上游 macOS 构建眼下也会停在这里。
       - sheng `0ae7ceb` 原样恢复这张表（取自 `6056637^`），配置区加一条描述性 finding；porting 记录检查 PASS。
       - cd7 构建通过后，值得给上游提 PR；提之前照规则再查一次有没有人修过。
    3. ShengUfs 组件编不过，`SourceStorage.cpp:291: error: expected '}'`：上游 main 的 `package/SourceStorage.cpp` 被截断了。
       - 它只有 291 行，停在 `native_source_storage_start` 里的 `attempted = true;`。这 291 行正好是 rponeawa `fix/sheng-startup-diagnostics`（`14192f3`）那份 353 行完整版的开头；后面加载存储框架、验证根卷策略、注册存储类、启动 UFS 和 Data 盘的部分被截掉了。也是 `6056637` 造成的。
       - 扫过三个整合提交（sheng `6056637` 76 个文件、核心 `db9cd2e` 30 个、AdrenoMetal `57a1adc` 19 个）：拿上游版本和 rponeawa 原分支、cd6 整合分支的版本比，只有这一个文件是被截掉的。
       - sheng `406931d` 恢复成完整版（大括号配对，用到的函数在上游代码和 ShengUfs 里都有），存储区加一条描述性 finding；porting 记录检查 PASS。
       - 和第 2 条一起，cd7 构建通过后给上游提 PR。
  - **cd7 构建成功（第四次跑）**：
    - 内核 `582dec09`，另存 `kernel.macho.cd7-582dec09`（json、map 同后缀，只读）：
      - 有 `_cs_text_fixup_signed_copy`、`_cs_text_fixup_hash`，没有 `_cs_text_fixup_restore`；
      - 有 `_native_keyboard_lid_closed`、`_native_source_storage_start`、`_boot_reset_install_platform`；
      - 字符串里有 `enable-jobs`、`sheng keyboard: lid %s`、`charge-auth`、`SourceStorage: root policy handoff or authentication failed`；
      - 补丁 153 个；macOS 的 `archives` 完整，SoftwareAES 单独编，根卷策略用 `scripts/policies/macos-27.3-26C5035r`。
    - 载荷 `6e2cc0e2`，另存 `payload.cd7-base.img`（只读）。插件 14:37 重编，有 `ci-mps=0`、`MadeBeforeRecovery`。
    - 日常文件已还原，`out/flash/` 的 8 份日常镜像哈希不变，OS 镜像已卸载。来源记录：`out/provenance/cd7-build.json`、`cd7-images.json`。
    - 试验镜像，都只从内存启动，固件 `boot-bigwin.img`（`5c926a3f`，内存表来自 uefi-sheng `20331338`，DarwinBoot `bdb6ff7`）；都加 `enable-jobs=com.openssh.sshd log-gpu=1`：
      - `out/flash/boot-v4-payload.bigwin-cd7-s2.img`（`4e38f55f`）：窗口完全按本地 `board.toml`，9 GiB，起点 `0x8C0000000`，按本地设置收编低位内存条。用户要"按本地摸索出来的内存配置表"，所以这是主测试。
      - `…-cd7-s1.img`（`1617e923`）：7.5 GiB，起点 `0x920000000`，`memory-outside=0`。s2 起不来或闪烁时退回这份。
      - `…-cd7-s1-noauth.img`（`5677a84d`）：s1 加 `charge-auth=0`。
      - `…-cd7-s1-cimps.img`（`a4698d69`）：s1 加 `ci-mps=0`。
    - 上机清单同 CD6-1 那条，用 cd7 的镜像，先 s2。第 2 步的通过线改成：s2 的物理内存不低于 8.75 GB。
  - **把上游那两处问题的修复先提到自己的仓库（用户："先在自己仓库提pr"）**：
    - fork `zus12873/UniXNU-sheng` 的 main 原来停在 `1108068`，落后上游 69 个、没有自己的提交。用户选"先快进"：普通推送（没加 force），`1108068..bc05635`，现在和上游 main 一样。
    - 分支 `fix/macos-build-after-runtime-integration`（工作树 `../UniXNU-sheng-pr-restore`），从 `bc05635` 开，3 个提交：
      - `1f0d456` 恢复 macOS 内核表；
      - `7ade87d` 恢复 `SourceStorage.cpp`；
      - `cc97ba7` 在 USB、打包两个区补记录。
      - 两处内容和 cd7 编通时用的逐字节相同；porting 记录检查 PASS，没有芯片号。
    - **zus12873/UniXNU-sheng#1**：对 fork 的 main 开，3 个文件、+71/-4，可合并，Device Test 待测。之后要不要提到上游 `UniXNU/UniXNU-sheng`，等用户定。
    - 推送时出过两次手误，都被拒，没推上任何东西：一次手打了一个不存在的完整哈希；一次 zsh 把 `"$H:refs/…"` 里的 `:r` 当成了修饰符。以后写 `"${H}:refs/heads/…"`。
  - **查别的仓库的新提交和修复（11-16 17:00，用户："看下其他仓库的最新提交和问题修复"）**：
    - 拉取了核心、sheng、uefi-sheng、UniXNU_macOS 和 31 个组件仓库；又用 `git ls-remote` 查了 CrossDarwin、rponeawa 的 fork（UniXNU、UniXNU-sheng、AdrenoMetal、ShengUfs、QcaBluetooth、Ath12kWifi、uefi-sheng），每个分支头本地都有。
    - cd7 整合（上游 #272、#108、uefi-sheng #8，11-16 10:13 合并）之后，上游只多了核心的 `9931232`，内容是设备记录页的数据（`devices.toml` 和别人设备的记录），没有代码。sheng、uefi-sheng 和各组件都没有新提交。
    - GitHub 上 11-14 以来没有新 issue。开着的 PR 只有我们的 #109 到 #112，和 mccding 的 UniXNU-sheng#106（CI 打包流程，4 个文件，没有人评审，和本机无关）。
    - rponeawa 关掉的三个草稿（UniXNU#271、AdrenoMetal#38、UniXNU-sheng#107，Shader Cache 应用和手动会话）已经由 #272、#39、#108 合进 main。按文件比过：AdrenoMetal 那个分支动过的文件和 main 完全相同；核心那边只剩组件版本号，main 的更新。
    - rponeawa 其余的开发分支，按文件比都已合进 main，或者被 main 后来的改动取代：AdrenoMetal 的 `fix/*-d923`、`fix/main-consumer-optimizations-555b`、半精度几支，sheng 的 `fix/fastboot-load-error-recovery`、`fix/graphics-priming-override`。Adreno740 的 `fix/cached-import-visibility`、`fix/context-switch-recovery` 在它的 main 里，本机 `fd7a0ca` 也包含它的 main（`1c9029b`）。
    - zus12873/UniXNU-sheng#1 恢复的两处，和 rponeawa 自己的分支 `upstream/feat/manual-shader-cache-app` 逐字相同：`SourceStorage.cpp` 完全一样；`board.toml` 只差 v0 模板一节，是上游 main 故意删的。说明是整合提交 `6056637` 把这两处丢了，rponeawa 的原分支里本来是完整的。
    - 没合进任何地方、和本机有关的只有一处：Jelly10086 的兼容 DXE 内存表（uefi-sheng `crossdarwin/fix/memory-compatible-dxe` 的 `56cfd832`，加上 UniXNU_macOS 的 `fix/compat-memory-modules`），两处都没有开 PR。
      - 它用在保留了旧 SEC 的模板镜像上：DXE 阶段套用 #6 的 ABL 内存表，只拿还空着的页。
      - 内存表还是调 `ShengPrepareMemoryMap`，所以只认 8 GiB 的门槛还在。
      - 本机的固件是自己编的，SEC 里就有内存表，用不上这个模块。内存第 1 步放开门槛时可以参考它的主机测试（`Tests/ShengMemory/Host.h`）。
    - 不是新提交，但对后面有用：
      - rponeawa/sm8550-mainline 的默认分支叫 `suspend-hang-debug`（9-18）：在 Linux 主线上查 sheng 挂起后卡死，加了 DPM 看门狗、pstore 日志区，给 a6xx GMU 的等待加了上限。写真睡眠设计时要读。
      - 上一条只看了提交标题。
      - rponeawa/xiaomi-mipps-auth（Linux，7-03，只读了最后两个提交）：代码里有电量计的密钥表（`FG_KEYS`）和小米厂商号 `0x2717`。"write fast charge mode" 那个提交只写一个状态文件给通知用，不控制电流；它把第三方头里的 `PD_PPS` 归为 "PPS" 档。这是 Linux 上的行为，macOS 上没验证过。
    - 已知、这次也不合的：uefi-sheng #6（内存第 1 步再做）、#7（看门狗，重启会扣槽位 a 的次数）。
  - 运行时那一步这次是完整编过的（`runtime.log` 13:50 到 13:58）：metal2vulkan 新取的 `555b13d`，Mesa `85fda3b`，插件 13:53，`gpuaddon.bin` 13:58。终端里只打印步骤标题，细节在 `logs/runtime.log` 里。
- **CD7-1 上机（11-16 17:38，用户："我进fastboot了"）**
  - 17:38:24 只读查询：当前槽位 a；a 剩 6 次、unbootable no；b 剩 7 次、unbootable no；电压 4372 mV。a 在 4 以上，没补。
  - `cd7-s2` 的 sha256 `4e38f55f…` 相符。17:38:35 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd7-s2.img`：`Booting OKAY`，45 秒内引导程序没有回来（镜像在跑）。
  - 上机清单照 CD6-1 那条，用 cd7 的镜像；第 2 步的通过线是物理内存不低于 8.75 GB。
  - 17:41:14 SSH 通了（开机后约两分半）。读数（17:41 到 17:48）：
    - 内存：`hw.memsize` 10142334976（10.14 GB，9.45 GiB），过线。开机 6 分钟时 pageouts 12799、空闲 21%；联动 1027381 页（按 4 KiB 一页约 4.2 GB）。
    - 代码签名：日志里没有 `CODESIGNING` 和 `Code Signature Invalid`；`vm.cs_native4k_stats` 的 bad 0、err 0。上游 #268 换掉板级补丁之后没出问题。
    - GPU：WindowServer 没有 `MadeBeforeRecovery`、`GpuRecoveryVictim`，有 4 条 "timed out fence"。
    - Safari：App cryptex 挂在 `/System/Volumes/Preboot/Cryptexes/App`（disk5s1，只读）；`/Applications/Safari.app` 的链接在；Safari 进程在跑，能不能开网页要用户说。
    - **图标服务一直在崩**：用户那份 `gui/501/com.apple.iconservices.iconservicesagent` `runs = 15`、`successive crashes = 15`。每次跑 0.4 到 1.5 秒就 SIGABRT，日志里 30 条 `MPSImageUnaryKernel`。cd7 不带 `ci-mps=0`，所以上游 main（AdrenoMetal#37 等）在本机没有修好 Core Image 的 MPS 崩溃，#112 要做。用户说活动监视器比较卡，多半和这个有关（推测，没核对）。
    - 充电：电量 97%，`Amperage` 1393 mA，4446 mV，33.8 °C。快充满了，比不出功率，要等电量低的时候再量。
    - 指针乱跳还在（用户说的）。上游 11-14 以后没人动过 `Wn8030.c` 和指针相关的代码。原因和修法见 11-15 22:46 那条：抬手那一帧没收到时，下一次落指被当成同一根手指的一大步。
  - **Wi-Fi 不自动连（用户："能不能主动连接已经连接过的wifi"）**：
    - 这次是用户在控制中心手动连的：airportd 记 `WiFiNetworkJoinReason = ControlCenter`，驱动就绪后约 118 秒才开始连。
    - 开机时 macOS 自己发起过自动加入（`trigger=aj_enabled`、`power_on`、`login`），存的那个网络也在列表里（1 个，wpa3-transition）。可是 airportd 把它当成**隐藏网络**（`Hidden SSIDs (1)`），每次实时扫描都按名字定向扫描。驱动回 `Operation not supported`（`-3903`），5 毫秒就失败；只读缓存的扫描结果为 0，所以一直连不上。
    - 用户打开控制中心时，WiFiAgent 做的是普通扫描，能扫到。
    - 驱动这边：`package/WifiNet.cpp` 的扫描请求（类型 10、86）不会回 `EOPNOTSUPP`。回这个的只有未处理的请求类型（`:637`）和未处理的接口请求（`:721`），所以定向扫描走的是另一种请求。是哪一种要看驱动日志：日志走 `native_wifi_logf`，这次的统一日志里没有 `wifi-net` 行。
    - 驱动自带的 `wifi-aj=1/2` 是无人值守测试用的：要把网络名和密码明文编进镜像（`join.txt`），不用在日常镜像上。
    - 上游查过，没有：核心、sheng、Ath12kWifi 的历史（hidden、directed scan、ssid list、auto-join），UniXNU 和 CrossDarwin 的 PR 和 issue。
    - 再细一层：失败的那几次，airportd 记 `(IO80211) Apple80211Scan … total time [0.000010], err[-3903]`。框架 10 微秒内就自己回了"不支持"，没有发 ioctl 给驱动。所以多半是驱动报的能力位里少了定向扫描那一项（`WifiNet.cpp:646-651` 的 `kCardCaps`），不是扫描处理写错。具体是哪一位还没查。
  - **活动监视器"一直在加载中、无法交互"（用户 18:0x）**：
    - 平板时间 02:04:15.187，活动监视器记 `XPC_ERROR_CONNECTION_INTERRUPTED` 和 "Failed to generate image … Code=4097"。同一刻图标服务 [1986] 崩掉（02:04:15.188，`iconservicesd` 记客户端退出）。
    - 02:06 图标服务 `runs = 18`、`successive crashes = 18`、`state = spawn scheduled`。活动监视器的图标请求跟着图标服务一起断，所以一直在加载。
    - 另外看到 launchd 每 5 到 10 秒重启一次 `fairplayd`、`prngseedd`、`lskdd`（exit 0 / 92），以后再看。
  - **不重启、只对桌面会话关 MPS 的试验（用户 18:1x 说"可以"），没起作用，已撤回**：
    - `sudo launchctl bsexec <Dock 的 PID> launchctl setenv …` 被拒：`141: Reentrancy avoided`，什么也没设上。
    - `sudo launchctl asuser 501 launchctl setenv CI_ENABLE_MPS 0` 成功：`launchctl print gui/501` 的 environment 里有 `CI_ENABLE_MPS => 0`。但这个服务自己的 "inherited environment" 里仍只有 `SSH_AUTH_SOCK`。
    - `launchctl kickstart` 在服务处于 `spawn scheduled` 时会一直等着，不会立刻拉起。
    - launchd 对连崩的服务按 10、20、40……640 秒翻倍延后重启，第 19 次停在 1200 秒（`minimum runtime = 1200`）。
    - 02:24:15 照这个间隔拉起（[2665]），1.04 秒后又 SIGABRT。崩溃报告 `iconservicesagent-2026-11-16-022417.ips` 里有 `CIBlurProcessor`、`MPSImage`、`MPSCore`，还是 MPS 那一处。
    - 结论：靠 launchd 域的环境变量关不掉。要么没传进这个已经加载的服务，要么 Core Image 不认这样传进来的值。CD4 上验证过的是插件的 `ci-mps=0`。
    - 02:3x 已 `unsetenv`，桌面会话的环境回到只有 `SSH_AUTH_SOCK`。
  - **用户 18:3x 的回报**：
    - Safari 能打开网页。
    - 合盖：屏幕没熄、没锁屏、没睡眠；打开后触摸正常。熄屏是合盖第 2 步，还没做。合着的时候有没有触点刷屏要看日志。
    - 之后平板从网络上掉了：18:39 SSH 超时、ping 不通，也不在 fastboot。日志在 Data 盘上，下次开机再读这一趟合盖前后的 `sheng keyboard: lid` 和 "Invalid event type: 11"。
  - **指针乱跳的修复（用户 18:3x："先把指针乱跳的驱动修复写了"），sheng `f645114`**：
    - 上游查过，11-14 以后没人动过 `Wn8030.c` 和指针相关的代码。
    - `Wn8030.c` 新增 `wn8030_pointer_report_at`：报文离上一份超过 `WN8030_POINTER_GAP_MS`（60 ms），就当成一次新的触摸，从手指现在的位置起算，丢掉没发完的移动和滚动；按住的点击不变。原来的 `wn8030_pointer_report` 不带时间，行为不变。
    - `KeyboardCover.cpp` 给每份触控板报文打上到达时间（`absolutetime_to_nanoseconds(mach_absolute_time())`，毫秒）。
    - 先写测试：`wn8030_host.c` 新加停顿、正好 60 ms、61 ms、计数回绕、两指滚动、按住点击这几种情况；`keyboard_cover_host.cpp` 经 `submit()` 送一次停顿后的大跳。给主机编译加了 `tests/keyboard-hid/kern/clock.h` 替身。两处都先看到失败（`wn8030_host.c:293`、`keyboard_cover_host.cpp:88`），实现后通过：WN8030 5208 项，键盘 HID macOS 5112、iPadOS 5199 项，键盘服务 123 项，合盖门 PASS。
    - `KeyboardCover.cpp` 用构建里 `NativeHidInput.command.json` 那套内核编译参数单独编过，rc 0，引用 `_wn8030_pointer_report_at`。
    - `porting.toml` 键盘区那条 finding 改成描述现在的规则。记录检查 PASS（18 个区）。
  - **活动监视器的修复（用户："修下activity monitor，让我下次进入系统的时候不再出现当前问题"），sheng `8baf320`**：
    - 就是 #112（`9cd1c2a`）的内容，`cherry-pick -x` 过来。macOS 的 `kernel_args` 末尾加 `ci-mps=0`，留着本机的 `vm_compression_limit=1572864`。
    - `porting.toml` 用 `resolve-porting-conflicts.py --base 9cd1c2a^` 合并。核对过：#112 加的 4 条 finding（configuration、gpu、usb、packaging）都在，本分支原有的一条没少。
    - 插件那边读 `ci-mps=0` 的代码已经在 AdrenoMetal main（`26d4902`）里，cd7 就有。
  - **cd8 构建准备（18:5x）**：
    - 构建盘第三次自己卸掉，又照下面的办法重新挂上。
    - 日常文件哈希都对：`33d294c8`、`8a36fe56`、`35f03ec4`、`aeaf38ac`、`39f9ad3f`、`5c926a3f`。
    - OS 镜像只读挂到 scratchpad 的 `os-mount`（`/dev/disk9s1`）。
    - 下一步：用户在自己的终端里 `sudo -v` 后跑 `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。构建完我另存 cd8 产物、还原日常文件、卸载 OS 镜像，再打 9 GiB 的 `cd8-s2`。
  - **cd8 构建完成（用户在自己的终端里跑，内核 18:57）**：
    - 内核 `643f4bfe`，有 `_wn8030_pointer_report_at`、`_native_keyboard_lid_closed`。另存 `kernel.macho.cd8-643f4bfe`，json、map 同后缀，只读。
    - 载荷 `964c92c9`，参数 915 字节，有 `ci-mps=0` 和 `vm_compression_limit=1572864`。另存 `payload.cd8-base.img`、`.json`，只读。运行时那一步 18:55 重新生成。
    - 来源记录：`out/provenance/cd8-build.json`（还原日常文件之前记的）、`cd8-images.json`。
    - 日常文件已还原，6 个哈希都对：`33d294c8`、`8a36fe56`、`35f03ec4`、`aeaf38ac`、`39f9ad3f`、`5c926a3f`。OS 镜像已卸载。
    - 试验镜像，只从内存启动，固件 `boot-bigwin.img`：
      - `payload.cd8-s2.img`（`3bbc5fef`）：`cd8-base` 加 `enable-jobs=com.openssh.sshd log-gpu=1`，窗口按本地 `board.toml`，9 GiB。
      - `out/flash/boot-v4-payload.bigwin-cd8-s2.img`（`6fba6190`），`bootimg-contents.py --payload` 核对过。
      - 对照用的还是 `…-cd7-s2-cimps.img`（`39ee6fa4`）：只有 `ci-mps=0`，没有指针修复。
    - **CD8-1 已开始（用户 19:02："我进fastboot了，可以"）**：19:02:30 只读查询，槽位 a 剩 6 次、b 剩 7 次，都可启动，没补；电压 4426 mV。`cd8-s2` 哈希 `6fba6190` 相符。19:02:36 `boot-sheng.py`：`Booting OKAY`，45 秒内引导程序没有回来。
    - CD8-1 读数（19:05 起，平板时间 03:05 起）：
      - 19:04:59 SSH 通；`hw.memsize` 10142334976；启动参数有 `ci-mps=0`。
      - 图标服务：开机 05:17:49、05:17:52 两次 SIGABRT（都有 `MPSImageUnaryKernel`），05:17:57 第三次拉起（"because incomplete work"）后一直在跑，`runs = 3`、`successive crashes = 2`，03:09 仍是这样。和 CD4 一样，先崩两次再稳住。前两次为什么还走 MPS 没查。活动监视器开着（用户打开的）。
      - GPU 没有复位；代码签名 0 条，`cs_native4k` bad 0、err 0。
      - Wi-Fi 又是用户在控制中心手动连的（`WiFiNetworkJoinReason = ControlCenter`）。
      - 上一趟（cd7-s2）的合盖：`sheng keyboard: lid closed/open` 在 02:36:38 到 41、02:38:06 到 19、02:38:24 到 27、02:38:27 到 29。这几段里 WindowServer 一条 "Invalid event type: 11" 都没有（同一时间段它记了 815 行别的）。触摸屏门起作用了，不过最长只合了 13 秒。
      - 指针第一次采样（03:07，开机约 4 分钟，1 分钟负载约 7 到 21），数据在 `data/tablet-logs/20261116-pointer-cd8/`（不入库），用新写的 `local-tools/pointer-csv-stats.py` 和 11-15 那份比：
        - 11-15（修之前）：停顿 117、154、444 ms 之后各一大步，511、597、258 px，方向都掉头（156 到 176 度），就是丢了抬手帧的跳法。
        - cd8：停顿超过 100 ms 后大于 150 px 的只有两步（427 ms 后 352 px 转 102 度，621 ms 后 298 px 转 63 度），没有掉头式的大跳。分不清是快速起手还是跳。
        - 新情况：移动中指针更新间隔变长。30 到 80 ms 的间隔有 209 次（每次约 50 到 70 px），11-15 那份几乎没有，看着会一顿一顿的。可能是开机初期负载高；也可能是控制器报文间隔变大。后者的话，超过 60 ms 的那几帧会被新规则当成新触摸丢掉位移。
        - 03:09:46 负载降到 2.25 后开了第二次采样（`pointer-cd8b.csv`），请用户只慢划、停、抬手、换位置：
          - 停顿（60 ms 以上）后的第一步共 44 次，中位 6 px。
          - 大于 150 px 的 5 步都是快速起手或快划中途，前后几步方向一致。比如 9.3 s 静止后 175、351、46、41、72 px 连着往右下。没有掉头式的跳。
          - 两次合计 77 秒，没出现 11-15 那种停顿后掉头的大跳（修之前 16 秒 3 次）。用户体感还没说。
          - 还在的：快划时指针隔 40 到 80 ms 才更新一次，一步 180 到 350 px。分不清是 WindowServer 合并了事件，还是控制器或驱动的报文本身隔这么久。如果是报文本身，几帧的位移攒成一帧，macOS 的加速曲线会把它放得更大。要分清得在驱动里数报文间隔和新规则触发的次数，挂到 ioreg 上，属于驱动改动。
    - **用户 19:1x："不跳了，快，慢划都有点顿，加上计数查一下，合盖不熄屏，修下icon显示的问题"**；图标是"空白或透明"，合盖第 2 步"现在就做"：
      - 合盖第 0 步（不改代码）：
        - `pmset -g` 里 sleep 1（被 powerd 阻止），displaysleep 10。
        - 03:17:19 `pmset displaysleepnow`：WindowServer 记 `IOMFBDisplay::set_display_state … target_state=off`，用户看到**全黑、背光也灭**。所以靠 macOS 自己熄屏就行。
      - 合盖会不会去睡：
        - XNU 的 `IOPMrootDomain` 收到 `kIOPMClamshellClosed` 后走 `privateSleepSystem` → `checkSystemSleepEnabled` → `gSleepDisabledFlag`。这个标志来自 `PE_get_default("sleep-disabled")`，即 `/defaults`。
        - cd8 载荷里的 macOS 设备树 `/defaults` 有 `sleep-disabled = 1`、`kern.maxvnodes = 0x13400`。平板上 `kern.maxvnodes` 正是 78848，说明 XNU 读的就是这个节点。所以告诉它合盖不会去睡。
        - `receivePowerNotification` 只是把消息排进 `pmPowerStateQueue`，从键盘线程调不会卡住。
        - 上游查过，没有做合盖或 clamshell 的；`dby-w09` 只在电池驱动里用了 `receivePowerNotification`。
      - sheng `bb0d65b`（合盖第 2 步）：
        - `package/LidClamshell.h`：只在盖子状态变化时发消息，开机时盖子开着不发。
        - `KeyboardProbe.cpp` 的 `publishLid` 在 macOS 上调 `getPMRootDomain()->receivePowerNotification(kIOPMClamshellClosed/Opened)`，并记一行 `sheng keyboard: clamshell closed/open sent to the power manager`。
        - 主机测试 `scripts/check-lid-clamshell-host.py` 30 项，先失败后通过。`KeyboardProbe.cpp` 用 `build-gop-legacy-display-27.py` 的板级参数编过；新头文件加进了该脚本的键盘源文件表。
      - sheng `eaa95d5`（触控板计数）：
        - `wn8030_pointer_report_at` 记录：报文数、发出的指针报文数、60 ms 规则重新起算的次数；手指按着时两份报文的间隔，分 8 档（<10、20、30、45、60、100、250 ms，其余）。
        - `KeyboardCover.cpp` 在第一份触控板报文时、之后最多每秒一次，把这些和控制器的 17 个计数一起挂成 `ShengTouchpadTiming`（32 位小端），用 `ioreg -r -c ShengKeyboardCover` 读。
        - 主机测试：WN8030 5222 项，键盘 HID macOS 5119、iPadOS 5199 项；内核参数编过。
      - **图标空白**：
        - 用 rponeawa 的 `scripts/macos-lab/icon-probe.m`（照 `prepare-sheng-gpu-lab.py` 的参数编，ad-hoc 签名）在平板上跑，结果在 `data/tablet-logs/20261116-icons-cd8/`（不入库）。
        - 默认模式：`/System/Applications` 56 个 App 图标都正常；偏好设置面板是通用的 PREF 图标。
        - `--settings-icons` 模式（系统设置侧栏的 28 项，每项两张）：左边走 NSWorkspace，白色符号都在；右边是图标服务新渲染的（`ISIcon getCGImageForImageDescriptor`、ignoreCache、24pt@2x），28 项里 21 项**只有彩色底、没有白色符号**。正常的只有 @、锁、铃、月亮、开关。
        - 也就是 SF Symbol 那一层在图标服务的 GPU 渲染里出来是透明的。
        - 上游：rponeawa 11-16 在 AdrenoMetal `fix/runtime-development-d923` 上有 `8f350aa`（"capture the sampled inputs of blank icon renders"）、`3efc76a`（隔离图标绘制、重放 alpha 输入）、`a2c34d6`（`icon-cb=FIRST:COUNT` 把图标命令缓冲区写进日志），只是诊断，没有修复，也没写原因。
        - 在 Mac 的 dyld 缓存里没找到能让图标服务改走软件渲染的开关。下一步用他的 `icon-cb` 和 RenderBox alpha 重放，抓出符号那一层的着色器和输入。
      - cd9 构建准备：日常文件 6 个哈希都对；OS 镜像只读挂到 scratchpad 的 `os-mount`（`/dev/disk9s1`）。等用户在自己的终端里构建。
    - **用户 20:0x："还需要定位下键盘壳频繁掉线的原因……通信丢失还是固件崩溃"；"测试下键盘灯，当前键盘灯是暗的"**：
      - 掉线现有的证据，都是统一日志里 IOKit 自己记的 `force close (ShengKeyboardCover` 和随后的 `start for ShengKeyboardCover`：
        - 3 天里共 48 行。cd8 这一趟三次：03:10:44.99、03:25:23.16、04:01:08.34（平板时间），每次 0.6 到 0.85 s 后设备重建。
        - 都不在合盖或开盖的时刻：03:10:44 离开盖 30.9 s；02:37:42 离开盖 61 s；03:25 和 04:01 附近没有盖子事件。
        - 驱动只在控制器自己发来 "cover detached"（a2 帧 `attached == 0`）时删设备（`KeyboardProbe.cpp` `detachCover`）。所以这几次 WN8030 都还在 I2C 上应答。
        - WN8030 的 RAM 固件如果崩了，表现应该是读取或命令失败，服务连续 3 次后重载固件，不会有干净的 0→1 attach 帧。所以更像是控制器到键盘壳的那段链路掉了，或者键盘壳自己复位。两者现在分不清：驱动以前不往 macOS 日志写任何掉线信息，计数只在板级日志里。
      - sheng `e035422`（诊断，不改行为）：
        - 每个状态变化的 attach 帧（attached、detached、changing）记一行 `sheng keyboard: cover …`，内容有：帧第 5 到 16 字节；之前 16 帧的种类（`KeyboardTrace.h`：k 键盘、c consumer、t 触控板、a attach、x 加速度计、u 认证、o 其他、- 无效）；距上一帧、上一个输入帧、上一个加速度计帧的毫秒数；帧数、中断数、I2C 失败、最后的 I2C 错误、认证、attach、重载次数。
        - 固件重载时记原因（读和命令失败、I2C 失败、最后错误）和结果；keep-awake 命令失败时记一次唤醒。
        - 主机测试 `scripts/check-keyboard-trace-host.py` 10 项，先失败后通过；`KeyboardProbe.cpp` 用板级参数编过。
        - `porting.toml`：盖子相关的三个文件归到 keyboard 区；display 区记下构建脚本的键盘源文件表。记录检查 PASS。
      - 键盘灯：驱动的亮度只来自启动参数 `keyboard-backlight=0..100`（`KeyboardProbe.cpp:679-681`），默认 0，所以是暗的。macOS 里没有调键盘亮度的通路。
      - **用户 20:04 已经跑完一次构建**（在 `e035422` 之前，内核里有 clamshell 字符串、`_wn8030_gap_bucket`，没有 cover 日志），记作 cd9：
        - 内核 `aa7c0355`（另存 `.cd9-aa7c0355`）。载荷 `89fc742e`，参数 915 字节，有 `ci-mps=0`，另存 `payload.cd9-base.img`。
        - `out/provenance/cd9-build.json` 是在 sheng 已经到 `e035422` 时记的，比实际构建多一个提交；那个提交只加日志和 `porting.toml`。
        - 日常文件已还原，6 个哈希都对。OS 镜像还挂着，留给 cd10。
        - `payload.cd9-s2.img`（`9a6f7b7f`）：`cd9-base` 加 `enable-jobs=com.openssh.sshd log-gpu=1 keyboard-backlight=50`。打成 `out/flash/boot-v4-payload.bigwin-cd9-s2.img`（`3b5401e2`），核对过；记录在 `cd9-images.json`。
      - 下一步：cd9-s2 上机测合盖熄屏、触控板计数、键盘灯。同时用户可以跑 cd10 构建（带掉线日志）。
      - **CD9-1 已开始（用户 20:15："我进fastboot了，可以"）**：20:15:55 只读查询，槽位 a 剩 6 次、b 剩 7 次，都可启动，没补；电压 4332 mV。`cd9-s2` 哈希 `3b5401e2` 相符。20:16:04 `boot-sheng.py`：`Booting OKAY`，45 秒内引导程序没有回来。
        - 20:20:27 SSH 通（Wi-Fi 又是从控制中心手动连的）。`hw.memsize` 10142334976；启动参数有 `keyboard-backlight=50`、`ci-mps=0`。
        - 图标服务还是开机先崩 2 次再稳住（`runs = 3`），日志里 4 条 MPS。GPU 没有复位，代码签名 0。
        - 根电源域还没有 `AppleClamshellState`：开机时盖子开着，按设计不发消息。
        - **触控板计数（新工具 `local-tools/touchpad-timing.py` 解码）**：开机到 04:20（平板时间），共 2378 份报文，发出指针报文 1193 份，60 ms 规则重新起算 6 次。手指按着时的报文间隔：<10 ms 867（37%），10–20 ms 1432（61%），20–30 ms 24，30–100 ms **0**，100–250 ms 4，≥250 ms 2。控制器：中断 2598、帧 2621、I2C 失败 0、认证 4。
        - 所以在驱动这一侧，报文是稳定的 10 到 20 ms 一份，没有 cd8 采样里那种 30 到 80 ms 的间隔。"顿"不在键盘壳、控制器或驱动读取这一段，在报文交给 macOS 之后（HID 事件驱动、hidd、WindowServer）。04:21:56 开了同时段的指针采样（`pointer-cd9.csv`）来核对。
        - 采样中途键盘壳又掉了一次：04:23:43.218 `force close`，04:23:44.084 `start for`（0.87 s），约在开始滑动后 10 s。之后设备重建，计数从 0 开始，attach 计数到 2，所以前后两次读数不能直接相减。cd9 里还没有掉线日志。
        - 重建后的设备：报文 739 份，发出指针报文 484 份，间隔 <10 ms 占 40%，10–20 ms 占 59%，30–100 ms 为 0；I2C 失败 0。
        - 指针那一侧（`pointer-csv-stats.py`，以及按间隔分档的步长）：
          - cd9 掉线之后，30–100 ms 的间隔有 44 次。其中 30–60 ms 那 32 次步长中位 12 px，有 13 次 ≥20 px。
          - cd8 第一次（开机约 4 分钟，负载 7 到 21，快划）：30–60 ms 129 次，步长中位 36 px。
          - cd8 第二次（慢划）：中位 2 px。
          - 长间隔后跟着大步，说明几份报文的位移是攒在一起到的。驱动一侧报文没断过，所以"顿"出在驱动之后的 macOS HID 链路上（`IOHIDInterface` → DriverKit 的 `AppleUserHIDEventDriver` → hidd → WindowServer），负载高时更明显。
          - 慢划时长间隔本来就会有：驱动只在有位移时才发报文。
          - 还没查的：DriverKit 驱动和 WindowServer 的调度、CPU 调频（`cpufreq=4`）在滑动时的频率。
        - **用户 20:3x 的回报**：
          - Wi-Fi 连上了。
          - **键盘灯亮了**（`keyboard-backlight=50`）。
          - 触控板测完了。
          - **04:23:43 那次掉线是用户主动断开触点再接上的**，cd10 有日志后可以拿来当"触点断开"的对照样本。cd8 的 03:10、03:25、04:01 三次是不是人为的，还没问。
          - 设置里的图标还是空白。
          - 合盖还没测。
        - **图标空白，接着查（cd9）**：
          - `icon-probe --settings-icons` 在 cd9 上的结果和 cd8 完全一样：同样 21 项空白，同样 7 项正常。是确定性的。
          - 结果图是从下往上画的（第 0 项在左下角）。
            - 空白的：Apple 账户、跟进、Wi-Fi、蓝牙、网络、VPN、通用、墙纸、辅助功能、外观、桌面、显示器、声音、屏幕使用时间、隐私、触控 ID、用户、键盘、鼠标、游戏控制器、光盘、打印机。
            - 正常的：控制中心（`switch.2`）、通知、专注（月亮）、锁定屏幕、互联网账户（@）。
          - 能排除的：声明方式。通用（`ISSymbolName = gear`，灰底白符号）空白，控制中心（`switch.2`，同样灰底白符号）正常；用 `ISTypeIdentifier` 的也是有的空白（蓝牙）、有的正常（通知、专注）。差别在符号本身。
          - 渲染期间，用户那份 `iconservicesagent`（[513]）在统一日志里一行都没记，没有报错，符号层就是空的。每个渲染约 5 ms。
          - 插件在堆满时会退回单独建纹理（`NativeBridgeMetalFrontend.mm:4398-4415`），不会给调用方 nil，所以 "heap texture refused" 应该不是原因。
          - 下一步只能抓 GPU：rponeawa 的 `icon-cb=FIRST:COUNT` 抓图标命令缓冲区，以及 RenderBox alpha 重放。这两样在 AdrenoMetal `fix/runtime-development-d923`（`a2c34d6`、`3efc76a`、`8f350aa`），不在 main。要把它们合进插件、重编运行时，再开一个只从内存启动的镜像。
        - **用户纠正（20:3x）**：04:23:43 那次是"发现键盘壳功能失灵之后"才主动断开再接上的。所以失灵在前，而且失灵时控制器**没有**发 detach：是一种不声不响的失灵，和那几次 0.6 秒的自动掉线不是一回事。哪项功能失灵（按键、触控板还是灯）还没问。
          - cd9 只有 IOKit 的设备重建记录，失灵那一段看不出控制器有没有还在送帧。触控板计数只在有触控板报文时才更新，失灵时会停在旧值。
          - cd10 的 detach 日志能回答这个问题：用户手动断开时，那一行记下距上一个输入帧和加速度计帧多少毫秒、I2C 失败次数和重载次数。
            - 帧早就停了、I2C 没失败：键盘壳那边或链路断了。
            - 有 I2C 失败或重载：平板里的控制器停了。
            - 帧一直到断开前都在来：数据到了驱动，问题在交给 macOS 这一段。
      - **cd10 构建完成**（用户在自己的终端里跑，20:20，含 `e035422` 的掉线日志和 `bb0d65b`）：
        - 内核 `128d45e0`（另存 `.cd10-128d45e0`）。载荷 `03e8c6f9`，参数 915 字节，有 `ci-mps=0`，另存 `payload.cd10-base.img`。来源记录 `cd10-build.json`、`cd10-images.json`。
        - 日常文件已还原，6 个哈希都对；OS 镜像已卸载。
        - `payload.cd10-s2.img`（`467fdc1d`）：加 `enable-jobs=com.openssh.sshd log-gpu=1 keyboard-backlight=50`，打成 `out/flash/boot-v4-payload.bigwin-cd10-s2.img`（`dd79bca5`），核对过。
        - 用法：键盘壳失灵时先别动，告诉我；我先读日志，再请用户断开接上，然后读 detach 那一行。
      - **用户 20:4x："按键和触控板都不灵，合盖，没有熄屏，当前是合盖状态"**：
        - 04:23 那次失灵，按键和触控板都不灵。
        - cd9 合盖（平板时间 04:40:03 合、04:40:06 开、04:40:06.442 又合）：
          - 驱动每次都记了 `clamshell closed/open sent to the power manager`。根电源域 `AppleClamshellState = Yes`、`AppleClamshellCausesSleep = Yes`。
          - powerd 记 "ClamshellState. Closed : 1. ClamshellSleepState: isSleepDisabled : 0"。
          - WindowServer 记 `clamshell state:2 sent to IOMFB`，它自己的显示电源状态机 `Work (D/C/W/S/P/R): 0/0/0/0/0/0`，什么也没做。
          - 屏幕没熄。也没看到系统睡眠的尝试或报错。
        - 原因：在 Mac 上合盖、没有外接屏时，是随后的系统睡眠把屏关掉的，这块板子拒绝睡眠。显示驱动是 Apple 原来的 `IOMobileFramebufferLegacy`（GopFramebuffer 的 `NativeLegacyDisplay` 子类），它收到 clamshell 状态不关屏。`pmset displaysleepnow` 走的是 `set_display_state`，那条路能关。
        - sheng `d66ef66`（照计划的退路：盖子合着时关背光）：
          - `AppleARMBacklight.cpp` 新增 `sheng_backlight_lid(bool)`：记下盖子状态，用工作循环上的定时器重新写一次当前亮度，键盘线程不等待。
          - `setLevel` 写给两颗 KTZ8866 的是 `lid_backlight_level`（`LidClamshell.h`：合着为 0）。`IODisplayParameters` 里仍发布 CoreBrightness 要的亮度，开盖后写回。背光服务发布之前就合上的，发布时补一次。
          - `KeyboardProbe` 的 `publishLid` 在每个 clamshell 消息旁边调它（弱链接，只在 macOS 上）。
          - 主机测试 34 项；两个文件都用板级参数编过；记录检查 PASS。
        - cd11 构建准备：日常文件 6 个哈希都对，OS 镜像只读挂好（`/dev/disk9s1`）。等用户构建。
      - **用户 20:5x："拉上游对于睡眠问题的修复"——查过，上游没有**：
        - 21:0x 拉取了核心、sheng、uefi-sheng、UniXNU_macOS 和全部组件仓库。CrossDarwin、rponeawa 的 fork 用 `ls-remote` 查过，没有本地没有的分支。
        - 搜了 11-15 以来所有分支的提交（sleep、suspend、clamshell、lid、resume、wake、hibernate、display off、backlight、psci），只有本机自己的提交。UniXNU_macOS 那几条是 "valid" 之类的字面误中。
        - GitHub 上 UniXNU 和 CrossDarwin 的 PR、issue（sleep、suspend、clamshell、lid、display off、backlight、hibernate）：只有旧的亮度和键盘 PR、#101（关机和重启接 PSCI，已在树里）、我们的 #111。没有挂起或恢复的实现。
        - 上游的新内容：
          - 核心 main 到 `4a654d1`（三个文档提交）。
          - sheng main 到 `4d9dcff`（三个文档提交，记录 CI 的 macOS 桌面构建）。
          - 两边都有 rponeawa 的 `fix/sheng-main-build-parity`，没合进 main：
            - sheng 的 `b69faf1` 恢复了 `SourceStorage.cpp`（和 zus12873/UniXNU-sheng#1 只差 11 行），也恢复了 macOS 的内核表。
            - 它的 macOS `kernel_args` 里也有 `ci-mps=0`，还有实验室参数（autoreset、uefi-watchdog、diag 等）。
            - 等它合进 main 再整合，PR #1 和 #112 那时可以撤。
      - **用户 21:0x："帮我看下如何修复睡眠功能"——调研（没改代码）**：
        - XNU 的睡眠路径：`IOCPUSleepKernel` 先让非启动核 `haltCPU()` + `processor_sleep`，最后让启动核 `haltCPU()` + `processor_sleep`，各核进 `ml_arm_sleep`（`osfmk/arm64/cpu.c:1056`）。启动核最后调 `arm64_prepare_for_sleep(true)`。
        - 这个内核是 XNU 源码按 **BCM2837** 机型配置编的（`DEVELOPMENT_ARM64_BCM2837`），不是 Apple 芯片家族，也不是 `APPLEVIRTUALPLATFORM`。所以 `arm64_prepare_for_sleep` 是非 Apple 的那个版本（`machine_routines_asm.s`，`#else` 分支）：`dsb; isb; wfi; b` **死循环**，没有恢复路径。XNU 指望平台断电，再从复位向量热启动回来，本移植没有这条路。
        - VM 平台那条"睡完立刻跳回恢复点"的捷径（`test_sleep_in_vm` → `arm_init_cpu(cpu_data, 0)`，cpu.c:1145-1152）不在这个配置里。不过 `IOPMrootDomain.cpp:8472` 的 `test_sleep_in_vm` 启动参数照样会清掉 `gSleepDisabledFlag`。
        - `ArmCpu::haltCPU` 是关掉计时器和 Group 1 中断后的 `wfi` 死循环；`quiesceCPU` 关计时器。没有调 PSCI `CPU_OFF`。醒来时 `processor_wake` 会对还"开着"的核再发 `CPU_ON`，会失败。
        - ArmCpu 带 `diag=1` 时会问固件 PSCI_VERSION 和 CPU_SUSPEND 的 PSCI_FEATURES（`armcpu_psci[4]`），但没在任何记录里找到答案。
        - 所以现在一旦真去睡，就是一去不回；这正是 `sleep-disabled = 1` 存在的原因。
        - 用户 21:1x 回答使用场景：**"合盖装包里几个小时，打开马上能用"**。我给了 A、B、C 三种做法：
          - A：合盖关屏，系统照常跑；
          - B：挂起到空闲，即 PSCI `CPU_OFF` 关掉副核、主核原地等唤醒，再从 `arm_init_cpu` 恢复；
          - C：深度睡眠。
          - 建议先量 A 的耗电，再决定要不要上 B。用户还没选。
      - **自动熄屏是怎么走的（用户问的，cd9 上查，21:3x）**：
        - powerd 判定空闲（`displaysleep 10`），发 `requestDisplayState: state 3` → WindowServer `Display 1 setEnabled:0`、`IOMFBDisplay::set_display_state … off` → `Display 1 set power state 0` → 内核 `(IOMobileGraphicsFamily) request_power_change … powerstate 0`。
        - 平板时间 05:08:52 就这样自己熄了一次（上次操作后 10 分钟）。按电源键能回到桌面；SSH 里 `caffeinate -u -t 2` 也能唤醒（05:39:42 `set power state 1`）。
        - **熄屏时背光不灭**：用户在暗处看到"隐约有一层灰光"，`AppleARMBacklight` 的 `IODisplayParameters` 仍是 1390。之前"全黑无光"是在亮处看错了。
        - 显示驱动这一侧：`NativeLegacyDisplay` 的 IOKit 电源状态熄屏前后都是 1（`IOPowerManagement` CurrentPowerState=1），熄屏不走 IOKit PM。`NativeLegacyDisplay.cpp:537-539` 写明 GOP 没有面板电源开关。
        - 熄屏前后框架缓冲的属性只有 "IOMFB Debug Info" 变了：熄屏时最后一帧没有图层（surface 0、宽高 0），亮屏时是 3048 宽的桌面。
        - Apple 原代码里接 `request_power_change` 的是哪个虚函数，`OriginalMobileFramebufferABI.h` 里没有命名（大多是 `unclassified…`）。
        - 能用的钩子：空帧（持续一段时间）→ 关背光；再出现图层 → 恢复。
        - 合盖时 macOS 不熄屏（见上），但 `pmset displaysleepnow` 和 `caffeinate -u` 在普通用户的 SSH 里都能用。所以一个用户级 LaunchAgent 盯着 `AppleClamshellState`，合上就熄屏、打开就唤醒，就能让合盖走和自动熄屏同一条路（WindowServer 停止绘制）。
      - **用户 21:4x："直接做真睡眠"（做法 B）**：设计草稿 `docs/superpowers/specs/2026-11-16-sheng-suspend-design.md`，等用户批准。补查到：`ArmCpu::initCPU(boot=false)` 直接 panic（唤醒后启动核和每个重启的核都会这样调），`haltCPU` 会把调用它的启动核挂死；电源键走 PMIC SPMI → PDC → SPI 481，盖子、键盘帧、触摸都走 TLMM 汇总 SPI 208；`arm_init_cpu`（`arm_init_sptm.c:1155`）有启动核唤醒分支。
    - CD8-1 上机要看的：图标服务的崩溃次数不涨、日志里没有 MPS 报错、活动监视器能操作；用 `tablet-pointer-probe.js` 采样指针，抬手换位置不跳；物理内存不低于 8.75 GB；先读上一趟合盖时的日志，再合盖 1 分钟；GPU 复位、代码签名、Safari 照旧。
  - 构建盘又是残留挂接（卷挂不上），照上次的办法处理：`hdiutil detach disk6`，再 `-nomount` 挂接，`fsck_apfs -n` 容器和卷 OK，然后 `diskutil mount disk7s1`。
  - 下一次启动用的镜像（只打包，没启动）：
    - `payload.cd7-s2-cimps.img`（`251e93eb`，只读）：`payload.cd7-s2.img` 加 `--arg ci-mps=0`，设备树不变。
    - `out/flash/boot-v4-payload.bigwin-cd7-s2-cimps.img`（`39ee6fa4`），内核块和 `cd7-s2` 相同（`610fa1f6`），`bootimg-contents.py --payload` 核对过。
- **cd6 构建完成（11-16 下午，用户在自己的终端里跑 `sudo -v && ./unixnu build kernel payload …`）**
  - 再修两处才过：
    - metal2vulkan 缓存重新取到 `d9236a8`；
    - Turnip 要 Bison 3.7 以上：上游 `aac6e04` 只找 `PATH` 和 Homebrew 的 Bison，不认缓存里自己编的 3.8.2。照报错 `brew install bison` 装了 3.8.2 到 `/opt/homebrew/opt/bison`（`HOMEBREW_NO_AUTO_UPDATE=1`，没碰别的包，没改 `~/.zshrc`）。
  - 产物：
    - 内核 `4983b3a8`，另存 `kernel.macho.cd6-4983b3a8`（json、map 同后缀，只读）。
      - 有 `_cs_text_fixup_signed_copy`（上游 #268）、`_cs_text_fixup_hash`，没有 `_cs_text_fixup_restore`（本机板级补丁已拿掉）；
      - 有 `_native_keyboard_lid_closed`，字符串里有 `enable-jobs`、`sheng keyboard: lid %s`、`charge-auth`；
      - 补丁 153 个。
    - 载荷 `ffdc7563`，另存 `payload.cd6-base.img`（只读）。插件 13:15 重编，有 `ci-mps=0`、`MadeBeforeRecovery`、`ending %s so launchd`。
  - 日常文件已还原：`kernel.macho` `33d294c8`、`payload.img` `8a36fe56`、`payload.json` `4d0e0464`；`boot.img` `35f03ec4`、`boot.json` `aeaf38ac`、`data.dbr` `39f9ad3f` 没被动过。OS 镜像已卸载。
  - 来源记录：`out/provenance/cd6-build.json`（构建刚结束时），`out/provenance/cd6-images.json`（加了下面的镜像）。构建期间核心只多了文档和 `local-tools/` 的提交，`scripts/` 没变。
  - 试验载荷和镜像，都只从内存启动，固件用 `boot-bigwin.img`（`5c926a3f`）：
    - 共同参数：7.5 GiB（`0x1E0000000`，起点 `0x920000000`），`memory-outside=0 enable-jobs=com.openssh.sshd log-gpu=1`；
    - `payload.cd6-s1.img`（`ae4e58c7`）→ `out/flash/boot-v4-payload.bigwin-cd6-s1.img`（`91d7a39d`）：不带 `ci-mps`，验证上游的 Core Image 修复；
    - `payload.cd6-s1-noauth.img`（`c5d09530`）→ `…-cd6-s1-noauth.img`（`78c4989c`）：加 `charge-auth=0`，充电对照；
    - `payload.cd6-s1-cimps.img`（`6385d605`）→ `…-cd6-s1-cimps.img`（`75fc0f28`）：加 `ci-mps=0`，MPS 还崩时对照；
    - `bootimg-contents.py --payload` 都核对过；`out/flash/` 的 8 份日常镜像哈希不变。
  - sheng 整合分支 `837813f`：合盖那部分的注释和 findings 改成和 #111 一样的写法。
  - **CD6-1 上机要做的**（要用户在场、说可以）：
    1. fastboot 读两个槽位，a ≤4 就补，读电压；`boot-sheng.py out/flash/boot-v4-payload.bigwin-cd6-s1.img`。
    2. 进桌面连 Wi-Fi 后经 SSH 看：`kern.bootargs`（有 `enable-jobs`，没有 `ci-mps`）、`hw.memsize`（约 7.50 GB）。
    3. Core Image：拷 `local-tools/tablet-ci-blur-probe.js` 过去跑。看它出不出图；`launchctl print gui/501/com.apple.iconservices.iconservicesagent` 的崩溃次数；日志里有没有 `MPSImageUnaryKernel`。结果决定 #112。
    4. 上游 #268 换掉板级补丁之后：日志里 WindowServer 有没有 `Code Signature Invalid` 或 `CODESIGNING`；`sysctl vm.cs_native4k_stats` 的 `bad` 是不是 0。
    5. Safari：`mount | grep -i cryptex`、`ls -l /Applications/Safari.app`；请用户点开 Safari、开一个网页。
    6. 合盖：先 `pmset -g`、`pmset displaysleepnow`（合盖熄屏第 0 步）；请用户合盖 1 分钟再打开，看日志里的 `sheng keyboard: lid closed/open`，确认没有 "Invalid event type: 11" 刷屏、开盖后触摸正常。结果决定 #111。
    7. 充电：用户读充电头的瓦数，同时读 `ioreg -rc ShengBattery` 的 `Amperage`、`Voltage`、`Temperature`；下一趟换 `noauth` 镜像对照。
    8. `tablet-icon-stress.js` 跑两轮，数 GPU 恢复次数。
  - 插着电不要关机（槽位重试次数）；关机和重启的测试放到最后单独问。
- **构建来源记录和日常镜像的源码还原（11-16，用户问"sheng 的 main 编出来的能不能复现本机正在跑的"，答不能；用户选"1+2"）**
  - 1，来源记录：`local-tools/record-build-provenance.py LABEL [--artifact IMG ...]`（`12a7809`，测试 `local-tools/test_record_build_provenance.py` 6 项）。
    - 每次构建完跑一次，写到 `<output>/provenance/LABEL.json` 和 `out/provenance/LABEL.json`（git 忽略）。
    - 记的内容：各仓库和子模块的提交号、未提交的文件及其哈希、`git diff HEAD` 的哈希、本地设置（芯片号只写 `present`）、工具链版本、产物和根卷策略文件和固件卷的哈希、载荷的启动参数、补丁列表。
    - **事故，已处理**：第一版只在顶层找 `unique_chip_id`，而 `unixnu.local.toml` 把它放在 `[build]` 表里。自测时芯片号被写进了两个 git 忽略的自测文件，也出现在会话输出里。
      - 两个文件都已删掉；`out/` 下没有别的副本，所有分支的 git 历史里也没有。没有提交，没有推送，没有发到 GitHub。
      - 已修：任何深度的 `unique_chip_id` 都脱敏；本地配置里找不到芯片号时拒绝运行；记录里只要含芯片号就不写文件。都有测试覆盖。
  - 2，平板 `boot_a` 里的日常镜像 `out/flash/boot-v4-flash.prev.img`（`40234c20`）的来源，按 reflog 和产物哈希还原。分支都只在本地，没推送：
    - **固件卷 `36bd589f`**：从镜像 kernel 段解出来，和 `out/flash/SILICIUM_UEFI.good-36bd589f.fd` 逐字节相同。
      - uefi-sheng `repro/daily-40234c20`（`82ce0110`，工作树 `../uefi-sheng-repro-daily`）：`66421cb7` 加上当时没提交的那一行，"DRAM bank 1 low" 改成 `0x20000000`。
      - 其中 UniXNU 的 UEFI 程序和加载器来自核心 `repro/daily-40234c20-firmware`，即 `dff2765`（11-13 全天的 HEAD），DarwinBoot 是 `5243c68`。
    - **设备树 `e0bb2ed8`、内核 `33d294c8`、载荷 `8a36fe56`**：
      - 核心 `repro/daily-40234c20`，即 `ec761fd`（11-14 18:00:56 合了 #244、#245；18:06 编完；之后的 `51db5b2` 只改了文档）。`make-flash-bootimg.py` 等打包工具也在这个提交里。
      - sheng `repro/daily-40234c20`（工作树 `../UniXNU-sheng-repro-daily`）：`1108068`（11-13 09:01 到 11-14 19:53 的 HEAD），加两个提交，都是当时工作区里没提交的改动：`d59a70d` 板级补丁（和 `ba18a9f` 逐字节相同），`cbbd940` 是 `feeds.toml`、`unixnu.lock`（stash `pre-cd2` 的内容）。
    - **不在 git 里、要另外取的**：
      - `unixnu.local.toml`：`kernel_args = ["vm-swapin-io=1"]` 和芯片号；
      - Data 种子 `<output>/runtime/data.dbr`（`39f9ad3f`）；
      - sheng 工作区里 `verification.json` 的三处改动，现在还在，规定不提交；
      - 本地生成、被 git 忽略的根卷策略钥匙和 header：钥匙哈希 `74eace58…`，可以用 `local-tools/recover-root-policies.py` 从载荷里取回。据记录日常载荷用的是同一把，没单独核对。
    - 按这些重编，功能上等于日常镜像，但不保证逐字节相同：同一份固件源码重编过一次，得到 `d187f851` 不是 `36bd589f`；工具链也可能已经更新。要原样的东西，用保存下来的二进制：`kernel.macho.daily-33d294c8`、`payload.daily-8a36fe56.img`、`SILICIUM_UEFI.good-36bd589f.fd`、`out/flash/boot-v4-flash.prev.img`。
- **开到上游的 PR（11-16，用户："将和sheng中main不同的地方全pr一下，不允许把doc写成changelog和测试记录"）**
  - 三个分支都从最新的 `upstream/main`（`bc05635`）开，工作树在 `../UniXNU-sheng-pr-harness`、`../UniXNU-sheng-pr-jobs`、`../UniXNU-sheng-pr-lid`，推到 `zus12873/UniXNU-sheng`：
    - **UniXNU-sheng#109** `test: stub POLICY_CALL in the launch policy harness`：上游 main 上 `check-boot-watchdog-policy.py` 编不过，这个修好它。
    - **UniXNU-sheng#110** `feat(launch): enable launchd jobs from the enable-jobs boot argument`：叠在 #109 上，说明里写了依赖；上机证据是 CD3-1。
    - **UniXNU-sheng#111**（draft）`fix(input): drop macOS touchscreen reports while the cover is closed`：还没上机，上机过了再转成正式 PR。
  - 文档按 `CONTRIBUTING.md` 和记录指南写：`porting.toml` 只加描述当前行为的 findings，没加 evidence 条目，不写日期，也不写"某天测过"。代码注释里那句带日期的话也改成描述行为。验证结果只写在 PR 说明里。
  - 没提的差异和原因：
    - rponeawa 的那批改动今天上午已由他压扁合进上游（`6056637`）；CrossDarwin 的 #101 到 #105 上游也已合并。照规则不重复提交。
    - 12 GiB 机型的内存窗口、200 MiB 载荷、测试菜单：直接写进 `board.toml` 会让 8 GiB 机型坏掉，要先做按内存大小分机型的配置（内存第 1 步的固件内存表做完后再看）。
    - 本机的代码页校验板级补丁已被上游 #268 取代。
    - **Core Image（更正，11-16 稍后核对）**：
      - 本机插件那一处 `ci-mps=0`（`19d6bcf`，作者 huanmeng）和 WindowServer 重启兜底（`adddc7b`），rponeawa 带进了 `fix/runtime-development-d923`，今天随 **UniXNU/AdrenoMetal#39** 合进了 AdrenoMetal 的 main（`26d4902`；`origin/main` 里能搜到 `ci-mps=0` 和 `MadeBeforeRecovery`）。
      - sheng 的 main 里，macOS 默认启动参数（`board.toml:239`）没有 `ci-mps=0`；只有上游的实验镜像脚本 `prepare-sheng-gpu-lab.py:216` 加它。
      - 上游报告里的 `coreimage_blur_mps_1: passed` 是 `agent.sh:80` 显式设了 `CI_ENABLE_MPS=1` 时的结果，插件不会覆盖已有的值。所以他们的新运行时（`ce8986f`）下强制走 MPS 也通过了；但那是他们的机器、他们的探测程序。
      - 结论：`exec-env` 的写法不提。sheng 要不要提"默认加 `ci-mps=0`"的一行 PR，看 cd6 上我们的复现脚本：不带 `ci-mps`、走 MPS 时还崩不崩。
      - 用户 11-16："先提draft"。**UniXNU-sheng#112**（draft）`fix(macos): keep Core Image's blurs off MPS by default`：
        - 分支 `fix/macos-ci-mps-default`（`9cd1c2a`，工作树 `../UniXNU-sheng-pr-cimps`），从 `upstream/main` `bc05635` 开；
        - macOS 载荷的启动参数末尾加 `ci-mps=0`，871/1000 字节；`porting.toml` 的配置、USB、打包、GPU 四个区各一条描述性 finding。
        - cd6 上机按这个分：不带 `ci-mps` 跑 `tablet-ci-blur-probe.js` 还 abort，就把 #112 转成正式 PR；通过就关掉 #112。
    - 之前那条（已被上面更正）：上游的 `reports/sheng-macos27-coreimage.json` 显示，rponeawa 的新 Metal 运行时下，MPS 开和关两种模糊都 `passed`，`iconservicesagent_fresh_crash` 是 false。
      - 所以 cd6 的第一份试验载荷不带 `exec-env`，先验证上游这个修复在本机有没有效（经 SSH 跑 `local-tools/tablet-ci-blur-probe.js`，它走 MPS）。
      - 不行再加 `exec-env` 对照。`zus12873/UniXNU-sheng` 的 `fix/macos-icon-agent-mps` 分支先留着，没删。
    - 上游那份报告里还记着："Icon float components are nonfinite"，图标缺失、颜色错误。
  - 整合分支里本地的 `porting.toml` findings 和 `TouchLid.h` 注释还是带日期的旧写法；构建结束后照 PR 分支的写法改。

上一阶段（2026-11-15 16:05）：**路线 A 的主机部分做完了（四个代码任务、新内核、新固件、六份载荷、五份只从内存启动的镜像）。7.5 GiB 的第 1 步镜像今天从内存启动过两次，都进了桌面，macOS 显示 7.50 GB，大窗口本身能启动。但两次都定住了：10:13 那次登录后约两分钟指针来回跳、然后定住；10:28 那次（诊断上机 D1，不恢复上次的应用）从约 5 分钟起应用一个个未响应，再过 10 分钟整机不应答。早上日常镜像的基线也有卡顿和指针抖动。每次都是内存第一次用满之后出事，原因还没有证据。第 1 步没有通过，后面几步都没有做，`boot_a` 没有动过。平板 10:55 在 fastboot（槽位 a，重试次数掉到过 0、已补回 7，见下面"槽位 a 的重试次数"一条；电压 3761，macOS 读的电量 23%），在等用户充电和决定下一次上机。用户 11:04 另外提出给 macOS 补充电驱动：驱动已经有了，缺的是 macOS 下充不进的原因，建议先量再定，在等用户答复（见下面"用户 11:04 提出"一条）。11:24 重启进日常镜像（上机 D2）：macOS 开着、接充电头能充（电池 +2 A），接 Mac 的口只进 0.45 A、电池在掉，停在 fastboot 基本不充。D2 在 11:34 以"终端全屏后卡死、键盘壳失灵、触屏还能用、已用 4.61 G / 5.95 G"结束，用户强制重启。11:39 再次重启进日常镜像（上机 D3，全程接 Mac 的线）：约 26 分钟时拍到了证据。整机没死，终端卡在重画自己的窗口里；已用 4.91 G 里被钉住的（Wired）占 3.26 G，程序只剩 1.02 G，交换 0、压力绿。交换不是瓶颈，下一步是查谁占着 Wired、卡住的程序最底层在等什么（见"11:39 上机 D3"一条）。D4（约 12:50 开机）的取样录像读完：终端主线程在等图标服务（IconServices）回一个同步请求，要的是标题栏上的文档小图标。下一步是看图标服务自己在做什么。13:19 平板在 fastboot，槽位 a 从 1 补回 7。16:04 用户说平板没电关机了，充电头只读到 2 W；在等它充上电再开机（见"16:04 用户"一条）。**

- 细节在文末"路线 A：主机部分做完，基线有了第一份结果"一条：提交、审阅结论、每个文件的字节数和 sha256、基线的读数。
- 计划 `docs/superpowers/plans/2026-11-15-memory-large-window.md` 的六个任务：
  1. 内核引导页表从 16 页改成 22 页。**完成**：`e9d3bb9`。
  2. 生成器和加载器的窗口上限从 8 GiB 改成 9 GiB。**完成**：`294936c`，子模块 `drivers/DarwinBoot` 的 `bdb6ff7`。
  3. 从一份载荷派生变体（只换设备树里的窗口数值和启动参数）的工具。**完成**：`64c26a0`、`60a61ba`，整体审阅后的修补 `822e47d`。
  4. 板级配置（9 GiB 窗口、下限、保留列表、钉住压缩器）和布局测试。**完成**：`b47b5f5`，`../UniXNU-sheng` 的 `5877d2c`。
  5. 构建内核、固件，打五份镜像。**完成**。
  6. 上机。**只开了个头**：基线进行中；第 1 步到第 3 步都没开始，每一次都要用户在场并当次说可以开始。
- 平板现在：09:46:40 我按用户的话（"现在在fastboot为我启动"）执行了 `fastboot reboot`，从 `boot_a` 起日常系统（`boot-v4-flash.prev.img`，`40234c20`）。重启前读到 `slot-retry-count:a` 是 5，这次开机用掉一次。
- 10:08:56 平板又在 fastboot 里了（不是我放进去的，是只读查询时看到的；我没有启动任何东西）：槽位 a，`slot-retry-count:a` 3，`slot-successful:a` no，`slot-unbootable:a` no，`battery-voltage` 3776，`unlocked` yes。重试次数比 09:46 那次开机之后应有的 4 又少了一次：要么其间槽位又启动过一次（系统自己重启，或用户重启），要么进 fastboot 本身也扣一次。哪一种还没问到；如果是系统自己重启，要记进基线。到 2 或以下就 `fastboot set_active a`（用户 11-14 允许）。
- **10:13 第 1 步第一次上机已经开始**：用户 10:12 说"直接做第1步"（没有先补完基线，也还没回答上面两个问题）。10:13:00 只读查询（槽位 a，重试 3，电压 3774，镜像 sha256 `8bc7b897…` 相符），10:13:03 `boot-sheng.py out/flash/boot-v4-payload.bigwin-s1.img`：`Booting OKAY`，之后 45 秒引导程序没有回来。
  - 第一份读数（用户 10:16 说"结果放入mp4了，指针漂移闪烁"；录屏 `data/mp4/IMG_6403.MOV`，开机后约两分钟拍的）：进了桌面，物理内存 **7.50 GB**（通过线 7.25 GB，过了）；已使用 5.13 GB，缓存 2.37 GB，交换 0，联动 2.80 GB，已压缩 628.2 MB，压力图绿色。指针是彩色转圈，在两个位置之间每一到三帧跳一次，和早上基线那段是同一种跳法。终端还卡在启动命令上（标题栏 `mkdir -m 700 -p ~/.zsh_sessions`，最后一行没有提示符）。
  - 这是 6 GiB 以上的窗口第一次在本机这个内核上跑起来：22 页的引导页表和下限 `0x920000000` 的 7.5 GiB 窗口，配现成固件，能进桌面。
  - **结果：定住，这一次不过。** 用户 10:20 的原话："仍然在抖动，系统卡死没有其他反应"。10:24:21 平板已被用户强制重启回 fastboot：槽位 a，重试 3（没有变，说明内存启动之后强制重启进 fastboot 不扣重试；早上从 5 掉到 3 是槽位其间启动了两次），电压 3762。
  - **翻旧记录发现的规律（10:21）：有读数的每一次定住，都出在"已用加缓存"第一次等于物理内存、同时上次会话的应用正在登录后一起恢复的时候。**
    - 11-14 21:56：6.50 GB，5.36 + 1.14，连 Wi-Fi 时卡屏。
    - 11-14 22:09：6.50 GB，4.48 + 2.03，开机约 1.5 分钟定住。
    - 11-15 09:48（日常镜像）：5.95 GB，4.72 + 1.21，卡顿加指针跳，后来怎样用户还没说。
    - 11-15 10:15（第 1 步）：7.50 GB，5.13 + 2.37，定住。
    - 反例一个：11-14 22:25 那次也是满的（6.50 GB，5.46 + 1.05），只开了几个应用，7.5 分钟以上没事。
    - 所以单是"内存满"不够，共同点是"内存满，加上一批应用同时启动"。三种不同的内存布局、有没有收编都一样，日常镜像也在内。照这个规律，窗口再大也只是晚几秒填满，现在比较哪份镜像都会被登录时那一阵搅乱。
  - 还不知道的：定住时是整个系统停了，还是只有画面停了；早上日常系统最后有没有定住；登录时不让应用恢复能不能避开。
  - 向用户建议的下一步（要用户当次同意才启动，10:27 提的）：登录时按住 Shift 不让应用恢复；进桌面后先在终端里起一个记录器 `while :; do date; vm_stat; sleep 3; done >> ~/hb.txt &`，再把内存用起来。定住之后强制重启，下次进系统看 `tail -60 ~/hb.txt`：记录器最后一条的时间比定住画面上的时钟晚一两分钟以上，说明系统还活着、只是画面停了；停在同一分钟，说明系统或读写盘停了，最后几条 `vm_stat` 就是出事前的内存状态。设计里写的"第 1 步定住就跑对照"先不做，因为对照也会撞上登录那一阵。
  - 屏幕诊断页用不上：macOS 的内核里没有编进去（见下面 11-14 22:52 的记录），要用得改内核配置，不在这次确认的范围里。
  - **诊断上机 D1（不算第 1 步的通过次数）**：用户 10:28 说"可以开始"。10:28:31 只读查询（槽位 a，重试 3，电压 3759，镜像 sha256 `8bc7b897…` 相符），10:28:34 再次内存启动 `boot-v4-payload.bigwin-s1.img`，`Booting OKAY`，45 秒内引导程序没有回来。请用户做的就是上面那几条（按住 Shift 登录、起记录器、应用一个一个开）。
  - **D1 的结果（用户 10:40 报告，附一张照片，照片没有放进 `data/`）**。用户原话："shift+enter可以直接进系统，打开terminal和activity monitor会需要加载很久，当activity monitor正常工作之后，terminal和我尝试打开的messages都陷入not responding，触控模式还能拖动activity monitor，activity monitor切换到energy页再想切回memory页的时候卡住了，但窗体仍然可以被拖动"。
    - 照片里读到的：菜单栏时钟 Sat 14 Nov 1:40 AM，终端里这次登录是 01:35:13，所以是登录后约 5 分钟。活动监视器：物理内存 7.50 GB，已用 5.50 GB，缓存文件 1.97 GB（合计 7.47 GB），交换 0，App 内存 2.93 GB，联动内存 2.42 GB，压缩 134.7 MB，压力绿色；进程列表只有占位的灰条。终端窗口上是转圈的指针。
    - **记录器没有跑起来**：输入的那行是 `while :; do date; vm_stat; sleep 3; dobe >>~/.hb.txt &`（`done` 打成了 `dobe`），终端停在 `while>` 续行提示符。这次没有 `~/hb.txt`。命令太长，下次要换成不容易打错的办法。
    - 这次说明的三件事：
      1. 按住 Shift 登录能不恢复上次的应用，但内存照样在 5 分钟内用满。"登录时那一批应用"不是必要条件。
      2. 这次画面和触控都活着（窗口拖得动），卡住的是单个应用：终端、信息，然后是活动监视器切页。没有报告指针抖动。所以这一次不是显示一侧停了；窗口服务器在应答，应用在等别的东西。等的是什么还不知道（数据盘、某个系统服务、还是换页）。
      3. 应用从一开始启动就慢，不是内存满了以后才慢。
    - 顺带看到：今天两次内存启动，平板时钟都是从 Sat 14 Nov 01:35 开始走的（终端的恢复记录里有 1:35:30 和 1:36:09），5 分钟内没有对上真实时间。Wi-Fi 连没连上不知道，已问用户。
    - 10:41 请用户做的（平板还在那个状态，都不用打字）：放 5 分钟看终端和活动监视器会不会自己恢复；恢复后拍活动监视器的 CPU 页（按 % CPU 从大到小）和 Disk 页（按 Bytes Written 从大到小），连底部那一条；还点得动就从苹果菜单正常关机，点不动再强制进 fastboot。
    - **10:46 用户第二次报告，D1 以定住结束**。原话："两个程序彻底卡死，点击force quit没有反应，系统卡死"。照片：菜单栏时钟 1:50 AM（比上一张晚 10 分钟）；强制退出窗口开着，是普通的那种文字，列着 Activity Monitor（未响应）、Messages、Terminal、Finder；活动监视器停在 Energy 页，底部写着 Remaining charge 23%；终端还停在 `while>`，它的红黄绿按钮被画成一小块浮在窗口内容上（画面错误）。
      - 从登录后约 5 分钟开始，应用一个个未响应，10 分钟内没有一个恢复，最后整机不应答。是一步步蔓延开的：先启动慢，再是单个应用，最后整机。强制退出杀不掉应用。
      - 所以 7.5 GiB 的窗口两次上机两次定住，恢复不恢复上次的应用都一样。
      - 10:48:40 用户强制重启后的只读查询：一台设备，槽位 a，重试 3（没有变），`slot-successful:a` no，`slot-unbootable:a` no，电压 3746，已解锁。没有启动任何东西。**电量只有 23%**（macOS 读的；macOS 下不充电），已请用户先充电。
    - **日常镜像和第 1 步镜像差在哪（10:53 读文件核对，`out/flash/boot-v4-flash.prev.img` 的载荷解到了临时目录）**
      - 命令行：日常 57 个参数，第 1 步 59 个，多出来的正好是 `memory-outside=0` 和 `vm_compression_limit=1572864`，其余一样。第 1 步和 6 GiB 对照（`bigwin-ctl6`）的命令行完全相同。
      - 窗口：日常是 `0x180000000`（6 GiB），没有下限属性；第 1 步是 `0x1e0000000`，下限 `0x920000000`。
      - 窗口外内存表：日常 8 格，保留 `0xd0000000+0x10000`；第 1 步 16 格，多保留整个高位内存区。
      - 固件部分：日常 1180683 字节 sha256 `0770b709…`；第 1 步 1180573 字节 `6d40d584…`。
      - 日常镜像里没有 `data-reset`。
    - **现在的判断（都是推测，没有一条有证据）**：每一种布局都是"内存第一次用满"之后出事，所以窗口做大只是把出事往后推几分钟。停住的是什么不知道。候选：
      1. 数据盘这条路：刷盘锁、数量固定的中转缓冲、所有等待都不可打断（`drivers/RamBlock/NativeRamBlock.cpp:160-193`、`:565-586`），后面还有 UFS 主机那一层。
      2. 内存满了以后，系统第一次回收"可丢弃"的 GPU 缓冲区，驱动或 Metal 插件没处理好。
      3. 页回收里别的环节。
      - 不太像的两个：内核地址空间不够（按设计里的账，7.5 GiB 时三个堆还有约 9.5 GiB）；"交换空间不足，系统暂停应用"（压力是绿的，压缩只有 135 MB）。
    - **还没用过、不用改内核就能拿到证据的三个地方**
      1. macOS 自己的卡死报告：`/Library/Logs/DiagnosticReports` 里的 `.hang`、`.spin` 文件，里面有卡住的线程停在内核哪个函数。只要当时写到了盘上，重启后还在。
      2. `sudo dmesg`：从来没试过，顺便能知道 `sudo` 认不认登录密码。
      3. 在终端里开着 `log stream --process 0`，当实时的内核日志，出事时拍下来。
  - **等 D1 时在主机上读代码得到的事实（10:30 到 10:40，只读，没有改任何东西）**
    - GPU 的缓冲区在 macOS 上全部来自系统内存，每份镜像都一样：内建参数里有 `gpu-pool=0`（`../UniXNU-sheng/package/BootWatchdogPolicy.c:59-61`），窗口外内存的池子关着；每个缓冲区是可换页内存，由驱动 `prepare()` 钉住（`drivers/Adreno740/NativeAdrenoMemory.cpp:217-252`）。命令行里没有 `gpu-bo-contig`，找连续内存的那条路也关着。所以 GPU 和应用抢的是同一份内存，联动内存里有一部分是它。
    - 数据盘的写入：写回模式下，一次刷盘独占 `flushRw`，每次写入共享它（`drivers/RamBlock/NativeRamBlock.cpp:116-141`、`:566-585`），所以刷盘期间所有写入都在等。驱动自己记了等锁时间、最长的一次请求、刷盘时间（`native_data_io_gate_ticks`、`native_data_io_max_ticks`、`native_data_flush_ticks`），但只有板级日志会把它们打出来（`../UniXNU-sheng/package/BootLog.c:632` 的 `DIO` 行）。这是"应用在等磁盘"的一个候选出处，没有证据。
    - 板级日志一直在写：命令行里有 `log=1`，`BootLog.c` 每 2 秒把诊断页文字、GPU 各行、内核消息缓冲写到用户数据分区最后 32 MiB。macOS 里读不到这个窗口（`NativeUfsBlock` 只发布只读的根窗口，`NativeUfs.cpp:1885-1965`）。要读它，得有能在本机启动的 Linux 读取镜像（见 00:20 的记录），或者改驱动把这个窗口只读地露出来（改驱动要用户同意）。
    - 显示相关的参数（第 1 步镜像的命令行）：`dpu-scanout=2`（面板直接扫合成器的表面，4 个槽位，`drivers/GopFramebuffer/NativeLegacyDisplay.cpp:283-320`）、`ca-triple-buffer=1`、`vsync=120`、`vsync-fixed=1`、`fb-gpu=1`。
  - 没做、先放着的一个办法：在 Mac 上开一个接收端，平板用 `nc` 每几秒发一行心跳过来，Mac 这边打上自己的时间。这样卡住时系统还活不活，不经过平板的盘和屏幕也能知道。要平板连着 Wi-Fi，也要用户同意在 Mac 上开一个端口。
- **槽位 a 的重试次数 10:48 到 10:54 之间从 3 掉到 0，槽位被标成不可启动；10:55 已补回（这一条关系到"不能启动槽位 b"，每次接手都要先读）**
  - 读数：10:48:40 是 3、`slot-unbootable:a` no；10:54:36 是 **0、yes**；`off-mode-charge` 1，`charger-screen-enabled` 1。10:55:06 读槽位 b：重试 7，`slot-successful:b` no，**`slot-unbootable:b` no**。也就是当时引导程序眼里只剩槽位 b 能启动，再开一次机很可能去启动 b。
  - 处理：10:55:19 执行 `fastboot set_active a`（用户 11-14 允许过用它补次数），回读：当前槽位 a，重试 7，`slot-unbootable:a` no；槽位 b 没有变。除此之外没有向平板发任何命令。
  - 用户 10:54 的原话："插上电，在系统中进行shutdown会直接进fastboot，没法正常关机进行设备补电"。
  - 推测的原因（还没向用户核对那 6 分钟里做了什么）：每从槽位 a 开一次机用掉一次，系统从不把槽位标成成功；插着电时在 macOS 里关机，平板不会停在关机状态，引导程序会因为 `off-mode-charge` 再把它启动，每次又用掉一次，用完就落进 fastboot。早上那一次没解释的启动（09:46 到 10:08 之间 5 变 3）也可能是这样来的。
  - 另一种同样说得通的读法（10:58 补记）：那 3 次是用户在 6 分钟里手动开了 3 次机用掉的，"插着电关机"本身只是落进 fastboot、不耗次数。两种读法分不开，要等用户说那几分钟里开了几次机。
  - 为什么本机做不到关机充电（用户 10:58 问）：这类平板插着电时没有真正的关机状态，电源一接上主板就上电，引导程序按 `off-mode-charge` 用"充电模式"启动安卓，由安卓里的充电程序画电池动画、定充电电流。本机的 `boot_a` 是 macOS 镜像，`init_boot_a` 清空了，`vendor_boot_a` 没有 ramdisk（11-14 的记录），安卓起不来，这个充电程序也就没有了。引导程序这时具体走了哪一步没有观察到，用户看到的结果是落进 fastboot。
  - 以后的做法：**每次到 fastboot 都读两个槽位；a 的次数在 4 或以下就补**（原计划写的是 2 或以下）。**不要在插着电时关机，也不要让它关机充电。** 槽位 b 仍然标着可启动，这个隐患还在，用户给过的许可里没有能改它的。
- **用户 11:04 提出："给 macOS 补上充电驱动"。读了代码和上游记录，还没有动任何东西（11:20）**
  - 结论：驱动已经有了，也在跑。缺的是"macOS 内核下为什么充不进"这个故障的原因，上游 11-10 记下它，到今天没有修好的提交。
  - 现有的这条路（日常镜像和第 1 步镜像的命令行都有 `adsp=2 usb=1 keyboard=1`，没有 `usb-sdp-ma`、`battery`、`ucsi-delay`）：
    - 充电由平板里的 DSP 固件自己做。上游原话："The ADSP firmware runs charging and PD/PPS negotiation without host requests"（`docs/zh/devices/sheng.md:939`）。
    - macOS 这边是 `../UniXNU-sheng/package/ShengBattery.cpp`（一个 `IOPMPowerSource`）加 `ShengBattmgr.c`（PMIC GLINK 上的电池管理协议）。
      - 读：电量、电压、电流、USB 口有没有电、口的类型、输入上限。
      - 写：只有两样，键盘盖状态，和"接电脑 USB 口时的输入电流上限"。
    - 上限只对标准口（类型 1，默认 900 mA，启动参数 `usb-sdp-ma` 可改，最多 3000）和 CDP（类型 3，1.5 A）生效；充电头、Type-C 电流、PD 都听固件的（`ShengBattmgr.c:62`、`:140-156`，`ShengBattery.cpp:295`）。
    - 菜单栏的充电图标：固件最近一次读成功的"USB 有电"不为 0，并且电池状态是"充电中"（`ShengBattmgr.c:255`、`:262`）；读失败时保留上一次读到的值。用户看到的 23% 和充电图标就是它报的。
    - 同一个通道上还有 USB-C 口管理（UCSI，`../UniXNU-sheng/drivers/QcomDwc3/QcomUcsi.h`）：通道一通就发一次 PPM_RESET，之后只开通知、读口的状态，用来决定 USB 做主机还是设备。这个文件里没有改供电方向的命令。
  - 上游的记录，按时间：
    - 10-25（`0e1f6e5`）：量过，能充。PPS 充电头 8.72 V、1.3 A 进，电池 +1.99 A；接 Mac 是 PD 5 V、1.1 A 进（上限 1.2 A），电池在桌面上 +0.25 到 +0.4 A（`docs/zh/devices/sheng.md:943-945`、`:978`）。那时的文字按 iOS 写，是在哪个内核上量的没有写明。
    - 11-06（`42ec454`、`40f803b`）：加了 USB 控制器驱动，UCSI 开始和电池共用通道。
    - 11-10（`da6da85`、`7cc0958`）：记下故障，"Under this kernel the charger firmware reports no USB input (online 0, 6 to 44 mV) although the bootloader charges on the same cable; the cause is not known"（`docs/zh/devices/sheng.md:938`）。同时加了两个只读的诊断开关 `log-power=1`、`ucsi-delay=<秒>`（最多 600），提交说明写着 "Not run on hardware yet"。诊断输出在板级日志里，本机读不到。
    - 键盘盖一节（`docs/zh/devices/sheng.md:523`）："their effect on the reported macOS charging and idle failures is not yet measured on hardware"。上游自己也把 macOS 充电当作未解决的故障。
    - 11-15（`5ae8b48`）：只在 `porting.toml` 里登记了 `package/*ChargeAuth*`、`scripts/check-charger-auth-host.py`、`scripts/charge-sheng-linux.py` 的归属；这些文件在已拉取的任何分支里都还没有（11:08 拉取过 `upstream`）。上游在做充电，没有修好的提交可拿。
    - 另一件事：没有认证时充电电流停在 2 A（`../UniXNU-sheng/porting.toml:551`）。这是充得快不快的事，不是充不进的事。
  - 本机知道的和不知道的：
    - 知道：macOS 显示在充电；接 Mac 的线时电压每 20 分钟掉 13 到 18 mV，电量一直显示 23%。
    - 这和上游那条"online 0"对不上（online 为 0 时不会有充电图标），除非图标用的是旧读数。是"有输入但不够用"还是"没有输入"，没有量过。
    - 不知道：充电头在 macOS 下、在 fastboot 下各能不能充；用户 11-14 说"充电口无法正常充电"时接的是什么。
    - 上游记录说引导程序在同一根线上能充，所以眼下补电最可能的办法是停在 fastboot 接充电头。本机未量。
  - 建议的做法：先量，不写新驱动。
    - 第 1 步，不改任何东西：进 macOS 后在终端输 `ioreg -rc ShengBattery` 拍一张；换到充电头，等半分钟再输一次拍一张。看 `ExternalConnected`、`IsCharging`、`Amperage`（正数是电池在进电）、`AdapterDetails` 里的电压和电流。
    - 结果是"充电头能充"：不用改，记下怎么充。
    - 结果是"有输入但太小"：看口的类型和上限。标准口可以用 `usb-sdp-ma` 调（`make-payload-variant.py --arg`，不改内核）；PD 口的上限驱动不管。
    - 结果是"没有输入"（上游那个故障）：用现成的启动参数逐个排除，都是内存启动的变体，不改内核，一次只改一个。
      - `ucsi-delay=600`：前 10 分钟不发 PPM_RESET。
      - `keyboard=0`：不起键盘盖驱动，也就不写键盘盖状态（`KeyboardProbe.cpp:640`）。
      - `usb=0`：不起 USB 控制器（`UsbProbe.cpp:44`）。
    - 上面都指不出原因时才需要改内核：把充电、USB、UCSI 的计数（`native_charger_stats`、`native_usb_stats`）挂到 `ioreg` 能看到的地方。这一步要用户另外同意。
  - 不做：绕开固件直接写充电芯片的寄存器。电流、电压、温度保护都在固件的充电算法里。
  - 规模：中等以上（可能要改内核驱动，方向没定）。设计要用户点头才动手；第 1 步的测量不算动手，但每次启动仍要用户在场说可以。
  - 11:15 `fastboot devices` 数到 0 台：平板不在 Mac 上了（多半是用户拿去接充电头）。回来时先读两个槽位和电压。
- **11:24 上机 D2（日常镜像）量充电。结果：macOS 开着、接充电头能充，电池进 2 A；充不进的是接 Mac 的口**
  - 用户 11:22 说"可以开始"。做法记在 `docs/superpowers/specs/2026-11-15-macos-charging-design.md`（批准的范围：量，和只多一个启动参数的内存启动变体；改内核、刷 `boot_a` 不在内）。
  - 启动：11:22:56 在 fastboot 读数（槽位 a 7 次、可启动；槽位 b 7 次、可启动；电压 3764）。11:24:21 `fastboot reboot`，进 `boot_a` 里的日常镜像，用掉槽位 a 一次（下次读应是 6）。
  - 用户 11:30 的话："11:00 到 11:22 之间，平板是接在充电头上，macos进系统后可以9.1v，1，5A进行充电，我充电头可以读到充电功率"。附一张终端照片，里面是两次 `ioreg -rc ShengBattery`。
  - 第一次，接着 Mac 的线：
    - 电池电流 `Amperage` −661 mA（照片里是 18446744073709550955，64 位补码），电池在放电。
    - USB 进来（`AdapterDetails`）：4832 mV、447 mA、2 W。
    - 电池电压 3730 mV，`IsCharging` Yes，`ExternalConnected` Yes，电量 21%，温度 29.10 ℃。
  - 第二次，换到充电头：
    - 电池电流 +2009 mA，电池在充。
    - USB 进来：8648 mV、1347 mA、12 W。用户的充电头自己显示 9.1 V、1.5 A。
    - 电池电压 3819 mV，`IsCharging` Yes，`ExternalConnected` Yes，电量 21%，温度 29.10 ℃。
  - 两次都有的：`DesignCapacity` 9800，`AppleRawMaxCapacity` 9145，`CycleCount` 116，`TimeRemaining` 65535（没有估计），`FamilyCode` 0xe0004000（电脑口）。
  - 结论：
    - macOS 开着、接充电头：能充。数字和上游 10-25 量到的一样（8.72 V、1.3 A 进，电池 +1.99 A）。上游 11-10 记的"没有 USB 输入"这一次在本机没有出现。
    - 接 Mac 的口：只进 0.45 A（约 2.2 W），系统用得比这多，电池每小时掉约 7%。固件仍报"充电中"，所以图标显示在充、电量却往下走。之前看到的"充不进"就是这个。
    - 停在 fastboot 接充电头 22 分钟（11:00 到 11:22）：3761 → 3764，基本没充进去。
    - 所以本机现在能充电的办法只有一个：macOS 开着，接充电头。从 21% 到 80% 约 2.7 小时，到满约 4 小时（按 2 A 算，末段会变慢）。
  - 顺带看到的两处读数问题，没有动：
    - `AppleRawCurrentCapacity` 是 1，按 21% 应在 1900 上下，像是单位差了 1000 倍。
    - `FamilyCode` 接充电头时也是"电脑口"。上游已知：属性 6 在每种口上都读成 SDP。
  - 没量的：
    - 开机时就接着充电头，会不会一样能充（上游把 "charging at boot" 列为待测）。
    - 系统定住时充电是否继续。用户的充电头有功率显示，可以直接看。
    - 接 Mac 用的是什么线、什么口；固件把它认成哪种口、上限是多少（`ioreg` 里看不到）。
  - 设计的第 2 步走"充电头能充：不改"这一支。接 Mac 的口进电太少要不要调，等用户定；不改内核能试的只有 `usb-sdp-ma`，口被认成标准口时才起作用。
  - D2 的结尾，11:34 用户的话："全屏终端后，终端卡死，键盘壳不可用，触屏操作仍然可用，内存5.95g物理内存容量，4.61g使用"。
    - 这是日常镜像、不恢复应用的登录，只开了终端和活动监视器。缓存、交换、内存压力没有读到。
    - 和早上日常镜像的基线对得上：那次是"使用内存"跳到 4.72 G 之后卡顿。
    - 这一趟多了一个变量：系统开着的时候把线从 Mac 换到了充电头（换线后第二次 `ioreg` 还能输，键盘那时是好的）。
    - 要了三样只用触屏就能取的证据（内存页、给卡住的终端取样、充电头功率），用户没来得及做，11:37 已经强制重启回 fastboot。
    - 11:38:48 在 fastboot 读数：槽位 a 6 次、可启动；槽位 b 7 次、可启动；电压 3790（上机前 3764，接充电头的那几分钟充进去了）。
- **11:39 上机 D3（日常镜像，对照）：全程接 Mac 的线、不换充电头、终端先不全屏，看日常镜像自己会不会卡**
  - 用户 11:37 的话："我已经进入fastboot了，帮我进系统之后，我再进行测试流程"。
  - 顺序：先开活动监视器的内存页，再开终端输 `sudo dmesg | tail -30` 和 `ls -t /Library/Logs/DiagnosticReports | head`；之后只看不动。一有东西卡住就拍内存页，并在活动监视器里双击那个程序点 Sample 拍前两屏。15 分钟没事再把终端全屏。
  - 11:39:08 `fastboot reboot`，槽位 a 用掉一次（下次读应是 5）。全程接 Mac 的线。
  - 用户 12:05 问："终端软件这部分应该如何优化，如何增加swap缓存区"；12:08 说"视频记录放到mp4路径下了"。录像是 `data/mp4/IMG_6412.MOV`（22 秒，12:07:43 拍，不入库；抽的帧在临时目录）。
  - 录像里的活动监视器内存页（平板时钟 10:34，约开机后 26 分钟）：
    - Physical Memory 5.95 GB，Memory Used 4.91 GB，Cached Files 1.03 GB，Swap Used 0 bytes，内存压力图是绿的。
    - Memory Used 的三项：App Memory 1.02 GB，**Wired Memory 3.26 GB**，Compressed 615.4 MB。
    - 进程表最上面：WindowServer 1.25 GB，Maps 370.6 MB，WallpaperAerialsExtension 312.4 MB，Activity Monitor 304.9 MB，Terminal 241.9 MB。Music 标着 Not Responding。
  - 录像里对终端（pid 732）的取样，`/usr/bin/sample`，2063 次：
    - 终端 10:29:39 启动，10:32:30 取样；Recent hangs 22；CPU 0.03%；Physical footprint 241.9M（峰值 290.0M）。
    - 主线程 2063 次全在同一条路上：`-[NSApplication run]` → `CA::Transaction::commit()` → `CA::Layer::display_if_needed` → `-[NSViewBackingLayer display]` → `-[NSViewBackingLayer drawInContext:]` → `-[NSView _recursive:displayRectIgnoringOpacity:inContext:stopAtLayerBackedViews:]` → `_NSViewDrawRect`。也就是卡在重画自己的窗口里。
    - 再往下的几层没有拍到（触屏滚不动那段文字），所以它在重画里具体等什么还不知道。取样文字最后有一段 "Sort by top of stack"，那里能看到。
  - 这一趟说明的事：
    - 不换线、终端不全屏，日常镜像自己也会出现程序未响应。换线和全屏都不是必要条件。
    - 整机没有死：26 分钟时触屏、活动监视器、取样都还能用。和 D1（7.5 GiB 窗口，十几分钟内整机不应答）不一样。
    - 交换一直是 0，压力图一直是绿的。卡住发生在系统开始用交换之前。
    - 被钉住的内存（Wired）占了 3.26 GB，D1 约 5 分钟时是 2.42 GB。留给程序、缓存和压缩的只有约 2.7 GB。谁占着这 3.26 GB 没有量过；我的猜测是图形缓冲（WindowServer 一个进程就 1.25 GB），没有验证。
  - 交换在这个内核里的设置（读的是构建用的源码 `tree/.cache/xnu-work/osfmk/vm/vm_compressor_backing_store.c` 和上游记录）：
    - 默认开着（`VM_PAGER_COMPRESSOR_WITH_SWAP`），交换文件按需建在 `/System/Volumes/VM/`，每个最大 1 GiB。
    - 这套移植把个数上限定成 5 个（共 5 GiB），原因写在源码里：小地址空间布局下，压缩池要按交换文件个数预留内核地址空间。
    - 内核是 DEVELOPMENT 构建，启动参数 `vm_max_num_swap_files=<个数>` 有效，不改内核就能调上限；调之前要重算内核地址空间的账。
    - 上游在同型号上测过（run139，2026-11-12，`../UniXNU-sheng` 的 `reports/macos27-memory-run139.md`）：压 5120 MiB 不可压缩的数据，交换涨到 4 个 1 GiB 文件再缩回，测试正常结束。压力前也是 "vm.swapusage: total = 0.00M"。
    - 所以加大交换现在不解决问题：每次卡住时交换都是 0，而且交换只能换出程序内存（1.02 GB），换不走被钉住的 3.26 GB。
  - 还缺的证据，都不用改内核：
    - 卡住的程序最底下一层停在哪：取样窗口拖右边的滚动条到最底，拍 "Sort by top of stack" 那一屏。
    - 开机后先在终端输 `vm_stat` 和 `sysctl vm.swapusage` 各拍一张，留作对照。
    - 卡住时活动监视器 CPU 页拍一张，看 kernel_task 占多少。
    - 谁占着 Wired：`sudo zprint -t` 的最后一屏（没试过，不一定能用）。
  - 12:25 回答用户时定的下一趟顺序（日常镜像，要用户说可以才启动）：
    - 开机登录后先输 `vm_stat` 拍照；再输 `sudo purge`（清掉文件缓存；也顺便知道 `sudo` 认不认登录密码），然后开两个程序看卡不卡。
      - 当场卡：问题在"被回收的文件页再读回来"这条路上。
      - 不卡：这条路基本排除，往图形和 Wired 上查。
      - `purge` 在这个内核里做的事（`bsd/vfs/vfs_syscalls.c:14994`）：逐个卷清缓存，再清文件页的 VM pager；只有 root 能调。
    - 活动监视器内存页在开机后 2、10、20 分钟各拍一张，看 Wired 是不是一直涨。
      - 已有的读数来自几次不同的开机，不能直接连成一条线：约 1.5 分钟 1.69 GB（11-14 22:09），约 5 分钟 2.42 GB（D1），约 26 分钟 3.26 GB（D3）；11-14 21:56 卡住时 3.14 GB。
    - 有程序卡住时：取样窗口点 Save… 存到默认位置，不用滚动；下次开机用文本编辑打开，搜 "Sort by" 拍那一屏。
    - 交换上限实际是多少，内核启动时会打一行 `Maximum number of VM swap files: N`（`vm_compressor_backing_store.c:495`），本机没读过。
  - 电：D3 全程接 Mac 的线。按 11:30 量到的 −0.66 A 估算，到 12:20 又掉了约 5%（没有读数）。已请用户换到充电头。
  - 12:19 `fastboot devices` 数到 0 台，平板不在 fastboot。
- **13:02 用户发来照片："终端卡在这里很久了"（又一次开机，暂记 D4；不是我启动的）**
  - 照片里：终端窗口只有上次会话的 `Last login: Fri Nov 13 10:06:45`、一行提示符、`[Restored 13 Nov 2026 at 10:13:03 AM]`，下一行是光标，指针是彩球。新的 shell 还没有输出任何东西。
  - 按日常镜像的时钟从约 10:05:30 起算，终端是开机后约 7.5 分钟恢复出来的。D3 里它是 24 分钟时启动的。所以这是 D3 之后的又一次开机：槽位 a 又用掉一次，没读数，下次到 fastboot 先读，按 4 或以下补。
  - 后果：下一趟顺序里的第 1、2 步（`vm_stat`、`sudo purge`）要终端能用才做得了，这次做不了。
  - 13:03 请用户只用触屏取证：活动监视器 Memory 页拍一张；双击 Terminal 点 Sample，取样窗口放到全屏拍一张，再点 Save…；并回答键盘壳还能不能用、这次怎么开的机。结果还没有。
  - 到现在记下的卡住，都发生在"要画新内容"的时候：开程序（终端、Messages、Music）、切标签页（活动监视器 Energy 切回 Memory）、终端全屏。已经在画的窗口照常更新，窗口能拖。这是归纳，不是量出来的。
  - 13:04 读了图形驱动分配缓冲的代码（`drivers/Adreno740/NativeAdrenoMemory.cpp`），读到的：
    - 图形缓冲是"可换页的内核内存 + `prepare()`"，从分配到释放一直钉着（`:219-252`）。
    - 程序交给 GPU 的内存（import）也从导入到释放一直钉着，"whether or not the GPU maps them"（`:25-28`）。所以图形内存全算在 Wired 里。Wired 里它占多少，本机没量过。
    - 上游遇到过一种同样症状的卡：向内核要一段连续物理内存，空闲内存给不出时要扫完所有空闲页才放弃，中位 163 ms 一次，卡在调用的人身上，注释原话 "the stalls at an app launch and on the widget page"（`:224-229`）。现在的做法：只有 `gpu-bo-contig` 到 128 KiB 之间的缓冲才要连续内存，失败后 5 秒内不再要；`gpu-bo-contig` 不给就是 0，即从不要。
    - 日常镜像的命令行里有没有 `gpu-bo-contig`、`gpu-pool` 是多少：还没读（`boot.json` 里没有命令行，要从载荷里读）。
    - 分配失败时驱动置一个 `pressure` 标志，经 `NativeAdrenoUserClient.cpp:211` 报给用户态的图形运行库。运行库拿它做什么没读。
    - 驱动自己记着"哪个进程占多少图形内存"（`native_adreno_bo_owners`、`native_adreno_import_owners`），但只写进板级日志（`../UniXNU-sheng/package/BootLog.c:1073-1100`），本机读不到，`ioreg` 里也没有。
  - 13:06:56 用户发来第二张照片（平板时钟 10:22，取样窗口加活动监视器 Memory 页）：
    - 内存页：Physical 5.95 GB，Memory Used 4.61 GB，Cached Files 1.22 GB，Swap Used 0 bytes，压力图绿；App Memory 1.79 GB，Wired Memory 2.50 GB，Compressed 325.3 MB。已用加缓存是 5.83 GB，又是满的。
    - 进程表：WindowServer 899.1 MB（pid 172），WallpaperAerialsExtension 344.5 MB（557），Activity Monitor 317.3 MB（1009），Notification Center 79.5 MB，Control Center 68.2 MB，System Settings 63.6 MB（970）；Terminal 标着 Not Responding。
    - 终端（pid 841）：10:11:53.559 启动，10:22:13.646 取样，2281 次；Recent hangs 13；CPU 0.00%；Physical footprint 44.4M（峰值 53.7M）；Real 77.8 MB，Private 27.0 MB；版本 2.15 (489.10)。
    - 取样的主线程 2281 次全在同一条路上，和 D3 逐层相同：`-[NSApplication run]` → `CA::Transaction::commit()` → `CA::Context::commit_transaction` → `CA::Layer::display_if_needed` → `-[NSViewBackingLayer display]` + 1268 → AppKit 里三层没有名字的（`0x191bb5000 + 0x11b9288`、`+ 0x11b8b00`、第三层被窗口底边截掉）。再往下没拍到。窗口没有放到全屏。
    - 时间：终端启动到打出 `[Restored …10:13:03]` 用了 70 秒；到取样时已经 10 分 20 秒，还在同一条路上。
    - 按两张照片对时间，这次开机大约在真实时间 12:50（推算，没有读数）；取样时是开机后约 16.7 分钟，终端启动时是开机后约 6.4 分钟。
    - 要收回的一句：上面"卡住都发生在要画新内容的时候"说得太宽。活动监视器（pid 1009）和系统设置（pid 970）都是在终端（pid 841）之后启动的，开窗口、开取样窗口、开信息面板都正常。卡的是某些程序（终端、Music、Messages），不是所有新画面。
    - 13:08 请用户接着做：在取样窗口右边滚动条的空白处点一下翻页，连拍 3 页；信息面板的 Statistics 页拍两张，隔半分钟；最后点 Save…。结果还没有。
  - 13:09 到 13:13 读代码，和"为什么偏偏是终端"有关的几件事：
    - 终端画字走的是普通的 CPU 画字接口。这台 Mac（macOS 27.2.1）上的 Terminal 2.15 (488.9) 导入的是 `CTFontDrawGlyphsWithAdvances`，没有导入 Metal、IOSurface、Core Image 的符号。平板上是 2.15 (489.10)，没有直接读过。所以"终端卡是因为它自己在用 GPU"基本排除。
    - 日常镜像的命令行（从 `out/flash/boot-v4-flash.prev.img` 里读出来）没有 `gpu-pool`、`gpu-bo-contig`、`cs-lazy`。但内核里还有一串内置参数（`../UniXNU-sheng/package/BootWatchdogPolicy.c:58-60`，在日常内核 `kernel.macho` 里也搜到了 `cs-lazy=1` 和 `gpu-pool=0`）：`timebase-user=1 cs-lazy=1 keyboard-lone=1 armcpu-edge=1 boot-payload-release=1 thermal=1 thermal-ms=100 thermal-level=1 board-clock=7 gpu-pool=0`。
    - 所以 `gpu-bo-contig` 是 0，驱动从不要连续内存，上游注释里"扫描空闲页"那种卡在本机排除。
    - `cs-lazy=1` 是开着的。这是代码页读入时校验签名的一条路（`profiles/os/macos-27.3-26C5035r/patches/xnu-12377/cshash-native4k-lazy.patch`）：内核用 4 KiB 页，签名按 16 KiB 一块；一块里的某一页第一次要用时，把这一块的页逐页读进来、拼起来算哈希，再让缺页重试（`VM_FAULT_RETRY`）。补丁开头写着 "Has not run on hardware"，设备文档 298 行写着 "Not yet run on hardware"。
    - 本机自己加的 `../UniXNU-sheng/patches/xnu-12377/sheng-text-fixup-verified-pagein.patch` 也在同一带：封存卷按 16 KiB 一块校验，块里已经在内存的页可能被改写过，所以校验前先把原字节放回一份副本。
    - 和内存满的关系（推断，没有验证）：内存没满时，代码页读进来就一直在；满了以后被回收的页要重新读、重新校验，这两条路才被大量走到，而且常常是一块里只缺一两页。终端要用别的程序不用的字体和代码页，先中招说得通，但没有证据。
    - 能读这条路计数的现成命令：`sysctl vm.cs_native4k_stats`（`bsd/kern/ubc_subr.c:6789`）。会打出 lazy、auth、bad、err、ms、各处的 retry 和 unready；补丁说 unready 必须一直是 0。本机从没读过。
    - 下一趟顺序里的第一条命令改成它：登录后先输 `sysctl vm.cs_native4k_stats` 拍照，再输 `vm_stat`、`sudo purge`；`purge` 之后再输一次 `sysctl vm.cs_native4k_stats`。
    - 13:17 核对后要降级的一点：上游 run139（2026-11-12，同型号，macOS 27.3）用的源码基线 UniXNU `2bbb39dc`、UniXNU-sheng `b9223ad4`，两者都已经包含 `cs-lazy=1`（本仓库 `268bfa1`，设备仓库 `81f43eb` 把它写进内置参数）。那次压了 5120 MiB，交换涨到 4 GiB，正常结束。所以 `cs-lazy=1` 在上游硬件上经受过内存压力，补丁头和设备文档里 "not run on hardware" 是旧话。它仍是候选，但不是首选：run139 压的是一个程序的匿名内存，不是"内存满了以后再开新程序"。
    - 能做、但没做的对照：命令行加 `cs-lazy=0` 就能关掉它，不用改内核（内置参数只在命令行没有这个名字时才查，`zzzz-sheng-ipados27-bringup.patch` 里 `PE_parse_boot_argn` 先查命令行；`cs-lazy` 是 `TUNABLE`，经 `osfmk/kern/startup.c:301` 的 `PE_parse_boot_argn` 读）。日常命令行 877 字节，加上是 887，在 1000 以内。要做得先有证据指向它，并且用户同意。
    - 上游和本机的一个明显差别：上游压力下交换会涨；本机每次卡住时交换都是 0、压力都是绿的。
- **13:19 用户："terminal的sample日志的视频记录放到mp4路径下了，键盘壳断开重新吸回可以恢复，然后平板现在在fastboot模式下，视频内容提取可以使用grok的api来做内容提取和整理"**
  - 录像 `data/mp4/IMG_6418.MOV`（92 秒，4K，13:09:48 存；不入库）。我在本机用 ffmpeg 抽帧直接读，没有传给 Grok：帧里的字读得清，录像也不出本机。抽的帧在临时目录 `d4-6418/`。
  - **终端卡住的原因找到了一层：它在等图标服务回话。** 取样（pid 841，2281 次）主线程每一次都是同一条完整的路：
    - `-[NSView _recursive:displayRectIgnoringOpacity:…]` → `_NSViewDrawRect` → `-[NSControl drawRect:]` → `-[NSThemeDocumentButtonCell drawWithFrame:inView:]`（标题栏上的文档小图标）
    - → `-[NSImage CGImageForProposedRect:context:hints:]` → `NSISIconImageRepGetCGImage` → `-[ISIcon prepareImagesForImageDescriptors:]`（IconServices）→ `-[ISConcreteIcon generateImageWithDescriptor:]` → `_ISRetryRequest`
    - → `_NSXPCDistantObjectSimpleMessageSend2` → `-[NSXPCConnection _sendInvocation:…]` → `__NSXPCCONNECTION_IS_WAITING_FOR_A_SYNCHRONOUS_REPLY__` → `xpc_connection_send_message_with_reply_sync` → `mach_msg2_trap`。
    - 也就是：主线程向图标服务发了一个同步请求，要标题栏那个图标，一直没等到回复。CPU 0% 和"在重画里卡住"都由此而来。终端本身没毛病。
  - 取样末尾的汇总："Sort by top of stack" 是 `__psynch_cvwait` 13686、`kevent` 4562、`mach_msg2_trap` 2281、`__workq_kernreturn` 2281、`read` 2281、`semaphore_wait_trap` 2281；其余线程都在空等（6 个在 `NativeAdrenoMetal` 里等条件变量，tty 线程在 `read`）。终端也加载了 GPU 插件（`NativeAdrenoMetal.bundle`、`libvulkan_freedreno.dylib`）。
  - D3 的取样只拍到 `_NSViewDrawRect`，前面每一层都和这次一样，多半是同一个原因（没拍到底，不算证实）。
  - 上游记过的图标服务问题（`docs/zh/devices/sheng.md`）：
    - 246 行：macOS 内核原先带着 iPadOS 的内存上限策略，五次开机里 iconservicesagent（450 MB）被杀 62 次。修正是 `profiles/os/macos-27.3-26C5035r/patches/xnu-12377/xnuconfig-macos-memorystatus-policy.patch`，在我们的补丁序列里（`patches/xnu/series:32`），所以本机不会因为"超过软上限"杀它；但"页面不足"等几种杀法还在。
    - 218 行（iPadOS）：一次同步 XPC 等 iconservicesagent，挡住了 4.444 秒的画面。
    - `../UniXNU-sheng/package/BootWatchdogPolicy.c:30`（iPadOS）："iconservicesagent also dies in CI::GLContext::init"；关掉它图标就全没了，所以留着。
  - 还不知道的：图标服务这时在做什么——忙着画（GPU 或内存在等）、在等别的服务、还是被杀了正在反复重启。和"内存满了才卡"的关系也还没对上。
  - 键盘壳：拔下再吸上就能恢复。
  - fastboot（13:19:32）：当前槽位 a；a 剩 1 次、unbootable no、successful no；b 剩 7 次、unbootable no、successful no；电压 3916 mV。a 在 4 以下，13:19:41 `fastboot set_active a`，读回 a 7 次、b 7 次没变。
  - 下一趟要拍的（日常镜像，等用户说可以再启动）：有程序卡住时，在活动监视器搜索框输 `icon`，拍 iconservicesagent 那一行（PID、内存、CPU），再对它点 Sample，像这次一样录像翻完。PID 隔一会儿再看一次，变了就是被杀后重启过。
- **16:04 用户："设备空电关机了，充电头只有2w的功率，我要怎么开机"**（16:04:28 `fastboot devices` 数到 0 台，平板不在 Mac 上）
  - 13:19 之后平板做了什么不知道。13:19 时它在 fastboot、3916 mV；fastboot 不充电还耗电，如果一直停在那里，电多半是这样耗光的（推测）。
  - 我的判断（没量过）：如果是 11:30 那个能到 9 V 以上的充电头，关机时只有 2 W 是正常的。快充要平板里的充电固件和充电头谈，这个固件跟着系统起来；关机时只剩充电芯片自己的慢充。
  - 风险：电池几乎空时开机，开机头一段进电仍约 2 W，可能开到一半断电，插着电又自己重启；每从槽位 a 开一次扣一次，扣完引导程序会去槽位 b。
  - 给用户的做法：插着放约 1 小时不按键（估的），再按住电源键约 3 秒；进 macOS 后看读数升到十几瓦。开不起来别连着按；落进 fastboot 就接 Mac，先读两个槽位；出现安卓或恢复界面什么都别选，电源加音量下进 fastboot。
  - 如果这个头本身只有 2 W：开着 macOS 也充不进（11:30 接 Mac 的口约 2.2 W 进，电池照样 −0.66 A），要换头。
  - 如果关机时真有 2 W 在进电池，下面那条"关机插线充电在本机做不到"就要改成"能慢充"。等量到再改。
  - 16:13 用户：充电头现在读到 7.1 W，问半小时后能不能开机。我答可以（屏幕黑着的前提下）。2 W 升到 7 W 像是电池过了最低那一段、充电芯片从涓流转成正常电流（推测，没量电压）。屏幕是不是黑的还没问到。
- **16:15 用户："不能把当前系统的充电瓦数拉更高么"**（16:23 读完代码，没有改任何东西）
  - 结论：现在的系统拉不高。11:30 量到电池 +2009 mA，正好是固件的上限。上游原话："Charge current stays at 2 A without fuel gauge and adapter authentication"（`../UniXNU-sheng/porting.toml` 的 power 一节）。
    - 这个上限没有启动参数能调。`usb-sdp-ma` 只管接电脑的标准口。
    - 换 PPS 充电头也一样。上游量过："A PPS adapter gets a 3 A input limit at about 8.7 V; the battery charges at the 2000 mA charge current with the charge pump off"。
  - 能拉高的路是认证，上游贡献者已经写了：
    - 代码在 `rponeawa/UniXNU-sheng` 的 `fix/sheng-macos27-bringup` 分支，比 upstream/main 多 63 个提交，没有合进主线。16:20 拉到 `../UniXNU-sheng` 的 `refs/remotes/rponeawa/*`，只拉取，没有合并。
    - `package/ShengChargeAuth.c`（11-15 05:12 `69cf931`）先用 HMAC-SHA256 认证两块电池的电量计，再认证小米充电头（SVID 0x2717）。认证用的密钥写在源码里，这里不抄。
    - macOS 一侧已经接上：`package/ShengBattery.cpp:398-401`，启动参数 `charge-auth`，默认 1。
    - 上游 14:14 和 15:19 两个文档提交（`ec384c1`、`78796d8`）记了它。真机证据只有一次 Linux 读数，接的是电脑口（CDP，5.18 V、0.144 A）。"用真充电头量 PD/PPS/MiPPS 功率"还在上游的待办里，macOS 真机上没有跑过。
  - 要用它就是改驱动，要用户另外同意。我的建议：先读这 63 个提交，看充电那几个能不能单独拿出来，不构建、不碰平板。读完再写短设计。测试镜像只从内存启动，文件名带 `chg`。
  - 还不知道：用户的充电头是不是小米的。小米认证要小米头；别的 PPS 头只过电池认证，能升多少上游没量。
- **16:24 用户："终端中断的问题当前有尝试有修复么，63 个提交中哪些能优化当前已知问题的"**（16:28 读完，没有改任何东西）
  - 终端卡住：没有试过修复。只查到它在等图标服务（见 13:19 一条），图标服务为什么不回没有证据。
    - 上游也没有：两个上游仓库 11-12 以后的提交和那 63 个提交，都没有提到 iconservices（搜 `iconservic|IconServices`，0 处）。
    - 和内存压力有关的两个上游修复，我们的树里已经有了：内核的 macOS 内存策略补丁；`9074eb7`（按需换入给临时 I/O 优先级，日常命令行 `vm-swapin-io=1`）。键盘壳的 `b952733`（指针精度、键盘壳输入恢复）也已经在 `../UniXNU-sheng` 的 HEAD 里。
    - 能先试的绕开办法，不改系统：终端 设置 → Profiles → Window → Title，取消勾选 "Working directory or document"。这台 Mac 的 Terminal 有这个选项（`TTAppPreferences.nib`），对应设置项 `ShowRepresentedURLInTitle`。推测关掉后标题栏不再要文档小图标，平板上没试过。音乐、信息等别的程序如果也在等图标服务，照样会卡；关掉后正好能检验这一点。
  - 63 个提交（`rponeawa/fix/sheng-macos27-bringup`，以 upstream/main `78796d8` 为基）按已知问题分：
    - 有用的只有充电：`69cf931`、`82e50fb`，`ShengBattery.cpp`、`ShengBattmgr.c`，加上 QcomDwc3 子模块的 `bcae997`、`42f7c2d`（UCSI 为认证要主机数据角色、重连时换代）。对应"充电卡在 2 A"。macOS 真机没有验证。
    - 小的正确性修复，没对应到已知现象：`4485ff3`、`8bb16e6`。macOS 把 `mach_absolute_time` 换算成 24 MHz，硬件计数器 CNTFRQ 仍是 19.2 MHz，原来有几处混着算。改后诊断时长、触摸时间戳和看门狗的计时都按 Mach 时基走。
    - 不能照搬：看门狗接管（`4b95220`、`c30fec2`，内置参数加 `uefi-watchdog=1`）。系统彻底不动时会被硬件复位；本机每次重启都扣槽位 a 的一次，扣完会去槽位 b。
    - 内存：`171dbe6` 把窗口外的空闲段从 8 个放到 64 个（`owned_memory_outside_ranges`），是上游给 8 GB 机器的那条路，和路线 A 重叠。
    - ShengUfs 子模块的 `72ddbec`、`b6fe07b`：支持 APFS 容器布局，我们现在的布局用不上。
    - 其余是实验室自动化、CI、诊断导出、打包脚本和报告，不改系统行为。
    - 键盘壳、睡眠、指针抖动、内存满后卡住：63 个里都没有。
  - 另外在 upstream/main 找到一个我们没有的修复：`1e3c3ae`（11-14，PR #95），`package/HidInputProbe.cpp` 10 行。
    - 触摸屏的检查线程读数字化仪的两个属性（`PrimaryUsagePage`、`PrimaryUsage`），驱动可能同时把它们换掉；原来的读法没有持有引用，可能读到已释放的对象。
    - 这段代码在服务注册后的约 10 秒里每 2 ms 跑一次，之后每秒一次。日常镜像开着 `offline-hid-input=1`、`touch-hid=1`，所以会跑。
    - 没对应到已知现象（我们遇到的是卡住，不是崩溃重启），但值得带上。属于驱动改动，要用户同意。
- **16:30 用户："平板进fastboot了"**
  - fastboot（16:31:23）：当前槽位 a；a 剩 5 次、unbootable no、successful no；b 剩 7 次、unbootable no、successful no；电压 3705 mV（有记录以来最低），`battery-soc-ok` yes；`off-mode-charge` 1，`charger-screen-enabled` 1。
  - 13:19 补到 7 之后用掉了 2 次，也就是从槽位 a 正常开过两次机。是用户自己开的，还是没电后插着充电头自己启动的，不知道。
  - 16:31:39 `fastboot set_active a`，读回 a 7 次、b 7 次。按规定 5 次还不用补；这次提前补，是因为电池几乎空，开机中途断电会连着扣次数，提前补留出余量。
  - 16:32 用户说"可以"。16:33:07 电压 3703 mV，`fastboot reboot` 从 `boot_a` 启动日常镜像，这次会扣槽位 a 一次。请用户一看到 UniXNU 菜单就把线换到充电头上。
- **16:38 用户："先解决内存问题"**（16:40 定下这一趟的做法；就用 16:33 开的这次，暂记 D5，不改系统）
  - 我的理解：扩内存（路线 A）被"内存第一次用满就卡"挡着，每种内存布局都这样，窗口做大只把卡住往后推几分钟。所以先查卡住的原因。
  - 现有的线索：终端在等图标服务，图标服务为什么不回不知道。几种可能：
    - 它自己在等 GPU；
    - 它在等别的服务；
    - 它被杀后反复重启；
    - 它要的文件页被回收了，读回来的那条路卡住。这一条最贴"第一次用满才卡"：用满时才第一次有文件页被回收。
  - 这一趟要拿的关键证据是图标服务的内核栈。活动监视器的 Sample 只有用户态的栈；`spindump` 连内核栈一起取（`man spindump`："samples user and kernel callstacks"）。内核帧多半没有符号，回到 Mac 上用日常镜像的内核来解。
  - 步骤：
    1. 先在终端 设置 → Profiles → Window 里取消勾选 "Working directory or document"。卡住时终端要能打字；终端不再卡，本身也是对图标这条线索的检验。
    2. 输 `vm_stat` 拍照，再输 `sudo purge`，然后打开以前卡过的程序（音乐、信息）。
       - 当场卡：问题在文件页读回来这条路上。
       - 不卡：这条基本排除。
    3. 活动监视器搜 `icon`，拍 iconservicesagent 那一行；内存页在开机后 2、10、20 分钟各拍一张。
    4. 任何程序卡住时，在终端输 `sudo spindump iconservicesagent -onlyTarget -open TextEdit`。等约 10 秒，文本编辑会打开报告，录像从头翻到尾。再拍一次 iconservicesagent 那一行，看 PID 变没变。
    5. 终端也卡了，就退回到活动监视器：选 iconservicesagent，点 Sample，录像。
- **16:42 用户："系统app卡住了，我手动进的fastboot"**（D5 从 16:33 开机算，约 8 分钟就卡住）
  - 16:42:58 fastboot：a 剩 6 次、b 剩 7 次，两个都是 unbootable no；电压 3715 mV（16:33 时 3703）。不用补。
  - `data/mp4/` 里最新的还是 13:09 的 IMG_6418，这一趟没有录像。哪些程序卡了、步骤做到哪一步，还没问。
  - 16:43:06 用户要求启动，`fastboot reboot` 进日常镜像（D6），会扣槽位 a 一次。
- **16:47 用户："能不能在镜像里改终端的默认配置，我现在终端打开就是在not responding"**（D6，开机后几分钟）
  - 新情况：D6 一打开终端就不响应，不是到内存用满才卡。这时内存满没满还不知道，要看活动监视器的内存页。如果没满，"每次都是内存用满后出事"这条要重看。
  - 回答"在镜像里改"：不划算。终端的设置存在用户数据（userdata 上的 `~/Library/Preferences/com.apple.Terminal.plist`），不在启动镜像里；系统卷是封住校验的，`Terminal.app` 里的默认值也改不了。要从镜像写进用户数据，得新做一个开机时写文件的机制。
  - 改成不用终端取证据：活动监视器的菜单里有 "Sample Process" 和 "Run Spindump"（这台 Mac 上 `Activity Monitor.app` 的资源里有这两项）。Spindump 带内核栈，正好替代 `sudo spindump`。
  - 请用户现在就做：
    1. 拍内存页；
    2. 搜 `icon`，拍 iconservicesagent 那一行；
    3. 对 iconservicesagent 点 Sample Process，录像；
    4. Run Spindump，在报告里 ⌘F 搜 iconservicesagent，录那一段。
- **16:53 用户发来照片 #11："能不能清除内存中的缓存，fastboot中纯净启动macos"**（D6，平板时钟 10:14，开机约 8 分钟）
  - 内存页：物理 5.95 GB；已用 4.66 GB = 程序 1.54 + Wired 2.69 + 压缩 0.4188；缓存文件 1,019.6 MB；交换 0；压力绿。已用加缓存 5.68 GB，又是满的。所以这次一开终端就卡，也还是在内存满了以后，"每次都是内存用满后出事"这条仍然成立；只是这次 8 分钟就满了。
  - WindowServer 1,009.9 MB（PID 171、24 个线程、1,421 个端口），排第一。
  - 用户把 `icon` 输进了聚焦搜索，没有输进活动监视器自己的搜索框。聚焦搜到的：
    - `IconCache`（今天 10:06，DB）；
    - `com.apple.iconservices`（今天 9:14，在 `C`，即用户缓存目录）；
    - `com.apple.iconservicesagent`（今天 10:06，在 `T`，即临时目录）。
    - 访达里开着一个 `com.apple.icon…` 文件夹。
  - 回答：
    - 内存里的东西每次重启都清空了，满是开机后几分钟内自己又涨满的，大头是 Wired 2.69 GB 和 WindowServer 1 GB。
    - 能跨重启留下来的只有磁盘上的东西：登录时重开的窗口、登录项、磁盘上的图标缓存。"纯净启动"（安全模式 `-x`）一次改动很多东西，在这个移植上也没试过，现在不建议。
    - 图标缓存先别删：证据拿到之前，删了就看不到它出问题时的样子了。
    - 请用户在活动监视器自己的搜索框里搜 `icon`，接着做 Sample Process 和 Run Spindump。
- **16:57 用户："activity monitor中只有iconserviced"**（D6，终端仍不响应）
  - 也就是卡住的这时候，iconservicesagent 根本没在跑，只有系统的 iconservicesd。
  - 日常镜像没有关掉它：命令行里没有 `lite=`，内置参数只关了 `com.apple.cameracaptured`。只有 `lite=2` 会关它（`../UniXNU-sheng/package/BootWatchdogPolicy.c:117-118`）。
  - 新的推测（没有证据）：iconservicesagent 没了，launchd 没有再把它拉起来，终端发给它的请求就一直排在端口上，所以终端零 CPU、永远等。它是怎么没的，有三种可能：
    - 内存满时被内核杀掉（页面不足等几种杀法还在）；
    - 启动时崩溃（上游在 iPadOS 上见过它死在 `CI::GLContext::init`，同一文件第 30 行）；
    - 被杀或崩溃后，launchd 推迟重启。
  - 请用户拿两样（都不用终端）：
    1. 控制台 App 左栏的崩溃报告（Crash Reports）和日志报告（Log Reports）：拍列表，看有没有 iconservicesagent 或 JetsamEvent 开头的报告；打开最新的一份录像。
    2. 活动监视器选中终端 → ⋯ → Run Spindump，在报告里找终端主线程那一段。spindump 会写出等待的线程被谁挡着，能看出终端的请求停在谁手里。
- **17:00 用户："iconservicesagent现在启动了，点开sample卡在please wait while the sample is taken"**
  - 所以 launchd 过了一阵是把它拉起来了，但对它取样完成不了。D4 时对终端取样是正常的，取样这件事本身能用。
  - 我的读法（推测）：取样要暂停目标、读它的线程状态和栈内存，还要读系统库来解符号。目标停在内核里某个出不来的地方，或者它的内存页要从磁盘读回来、而读回来这条路卡着，取样就会跟着等。这和"文件页被回收后读不回来"的推测对得上，但也可能是它卡在显卡驱动里，还分不出来。
  - Spindump 用内核的栈快照，不暂停目标，也不去读不在内存里的页，所以取样卡住时它多半还能出结果。
  - 请用户：
    1. 先拍 iconservicesagent 那一行（PID、CPU、内存、线程数）。
    2. 取样窗口能取消就取消；活动监视器整个卡住就用 ⌥⌘Esc 强制退出它再打开。
    3. 直接 Run Spindump（菜单栏 View 里或 ⋯ 里）；找 iconservicesagent 和终端两段，录像。
    4. 控制台的崩溃报告列表也拍一张。
- **17:05 用户发来照片 #12、#13**（D6；#13 上平板时钟 10:13）
  - #12，活动监视器搜 icon，只有两行：
    - `iconservicesagent`：1.4 MB，2 个线程，43 个端口，PID 806，用户 **root**；
    - `iconservicesd`：1.3 MB，2 个线程，52 个端口，PID 131，用户 `_iconservices`。
    - 以用户身份（huanmeng）跑的那个 iconservicesagent 不在。
  - 这台 Mac 上的启动配置（宿主机的 macOS，平板上没核对）：iconservicesagent 有两份。
    - 一份是每个用户的代理 `/System/Library/LaunchAgents/com.apple.iconservices.iconservicesagent.plist`；
    - 一份是 root 的守护进程 `/System/Library/LaunchDaemons/` 下同名文件（参数 `runAsRoot`）。
    - 两份都提供 `com.apple.iconservices` 服务，都是 `RunAtLoad false`（有请求才起），`EnablePressuredExit true`、`EnableTransactions true`：内存紧张、手上没活时，launchd 可以让它退出，下次有请求再拉起来。
    - iconservicesd 是 `_iconservices` 用户，`RunAtLoad true`，提供 `com.apple.iconservices.store`。
    - 终端是用户进程，找的是用户那一份。那一份不在，root 那一份 1.4 MB、2 个线程，像是刚起、停在很早的地方。对它取样一直停在 "please wait while the sample is taken"（#13，有 Cancel 按钮）。用户也对 iconservicesd 取过样，那个窗口出来了（内容没拍）。
  - #13，聚焦搜 `spin` 有一个大发现：`/Library/Logs/DiagnosticReports/` 里已经有系统自己写的 spin 报告。用户以前强制退出没响应的终端时，系统会自动跑 spindump。这些报告带每个进程的内核栈，正是要的证据。
    - `Terminal_2026-11-14-082152_MacBook-Pro.spin`（4.4 MB）
    - `Terminal_2026-11-14-063545_MacBook-Pro.spin`（4.5 MB）
    - `Terminal_2026-11-13-151057_MacBook-Pro.spin`（4.4 MB）
    - `Terminal_2026-11-13-104357_MacBook-Pro.spin`
    - `Sharing_2026-11-14-063449_MacBook-Pro.spin`（3.4 MB）
    - 文件名里的时间是平板的时钟，不可信。
  - 菜单里 "Run Spindump" 在活动监视器的 View 下（聚焦的菜单项结果写的是 "Activity Monitor > View"）。
  - 请用户：
    1. 取消那个取样；
    2. View → Run Spindump，在结果里 ⌘F 搜 `iconservicesagent`、`Terminal`，各录一段；
    3. 用聚焦打开 `Terminal_2026-11-14-082152_MacBook-Pro.spin`（会用控制台打开），从头录到终端主线程的栈结束，再 ⌘F 搜 `iconservicesagent` 录一段。
- **17:08 用户："我没办法cancel，你能给我个新镜像让我尝试测试大内存的解决方案么"**
  - 不用新做：路线 A 的镜像 10:01 就打好了，都只从内存启动。
  - 定下的做法（记在台账里）：下一次直接从内存启动第 2 步 `out/flash/boot-v4-payload.bigwin-s2.img`（9 GiB 窗口，新固件；17:09 核对 sha256 `e373b41a…` 相符）。
    - 计划原本要第 1 步通过、再做 1b 才到第 2 步；这次先跑第 2 步，是用户要现在就试大内存。
    - 设计的批准包括这些镜像从内存启动（用户在场）；从内存启动也不扣槽位次数。
    - 进不了桌面，下一次换 1b（`bigwin-s1b`，sha256 `f356cae5…`，新固件、7.5 GiB），把固件和窗口分开看。
  - 跟用户说清楚：这不修卡住。它能看出两件事：9 GiB 能不能起来；内存晚多久才满、卡住晚多久才来。通过线照计划：物理内存不低于 8.75 GB。
  - 这一趟的顺序：
    1. 进桌面就拍内存页；
    2. 趁系统还顺，用聚焦打开以前的 `Terminal_2026-11-14-082152_MacBook-Pro.spin` 录像。文件在磁盘上，重启不会丢。
    3. 开机后 2、10、20 分钟各拍一次内存页；
    4. 卡住时用 View → Run Spindump，不要用 Sample。
  - 现在的平板：取样窗口卡着取消不了。要用户按住电源键加音量下键约 10 秒进 fastboot，接 Mac 后告诉我。
- **17:11 用户："我现在进fastboot了，帮我启动这份镜像"**（第 2 步第一次上机，暂记 S2-1）
  - fastboot（17:12:00）：当前槽位 a；a 剩 **3** 次、b 剩 7 次，都是 unbootable no；电压 3753 mV。
    - 16:43 那次开机后应剩 5 次，所以这中间又从槽位 a 正常开过两次机。怎么开的没问。
    - 在 4 以下，17:12:08 `fastboot set_active a`，读回 a 7、b 7。
  - sha256 `e373b41a…` 相符。17:12:14 `python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.bigwin-s2.img`：`Booting OKAY`，45 秒内引导程序没有回来（镜像在跑）。从内存启动不扣次数。
  - **17:14 用户："新镜像卡登录开屏了，登录开屏闪烁"**：第 2 步到了登录窗口，在那里闪，没进桌面。
    - 和以前的"多收内存就闪"像是同一类：11-14 收编 3.5 GiB（都在 4 GiB 以上）时闪，关掉收编就不闪；收编 3 GiB 的同一份镜像四次里闪过一次。原因一直没找到，也从没录到过闪烁的样子。
    - 第 1 步（旧固件、7.5 GiB，窗口从 `0x920000000` 起）进过桌面。第 2 步多了两样：新固件；窗口往下多出 `0x8C0000000`–`0x920000000` 这 1.5 GiB。
    - 下一步照 17:09 定的做法：从内存启动 1b（新固件、7.5 GiB），把固件和窗口分开看。
      - 1b 也闪：是新固件的问题。
      - 1b 不闪：再用 split（新固件、7.5 GiB、窗口从 `0x8C0000000` 起）分开地址和大小。split 镜像还没打包，载荷 `payload.bigwin-split.img` 已经有了。
    - 请用户先录 20 到 30 秒闪烁的样子：动一动指针、按一下键，看还跟不跟手；再进 fastboot。
- **17:15 用户："进fastboot了"**（1b 第一次上机，暂记 S1b-1）
  - fastboot（17:15:56）：a 7、b 7，都是 unbootable no；电压 3787 mV。`data/mp4/` 里还没有闪烁的录像，最新的仍是 13:09 的 IMG_6418。
  - sha256 `f356cae5…` 相符。17:16:05 `boot-sheng.py out/flash/boot-v4-payload.bigwin-s1b.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - 计划里 1b 的通过线：进得了桌面，物理内存和第 1 步差不到 16 MiB（第 1 步是 7.50 GB）。
  - **约 17:20 用户："进桌面了，开机，activitymonitor中先出现了iconservicesd，iconservicesagent在点开terminal后在activity monitor中出现了，terminal还是卡死的状态"**
    - 1b 进了桌面：新固件能起 7.5 GiB 窗口。第 2 步在登录窗口闪，问题多半在多出来的那 1.5 GiB（`0x8C0000000`–`0x920000000`）或 9 GiB 这个大小上，不在固件（各只一次）。1b 的内存读数还没拍。
    - 图标服务：开机后先只有 iconservicesd；打开终端，iconservicesagent 才被拉起来（按需启动，正常）。但终端仍然一打开就卡。
      - 也就是说，它被拉起来了，可是不回话。
      - 这次是刚开机、内存多半还没满就卡。"内存满了才卡"可能只是巧合：也许每当图标服务真要画一个图标（缓存里没有）就会卡。要看内存页确认。
    - 请用户趁系统还顺：
      1. 拍内存页；
      2. 拍 iconservicesagent 那一行（用户、内存、线程数）；
      3. View → Run Spindump，在结果里搜 `iconservicesagent` 和 `Terminal`，各录一段。
    - **约 17:25 用户："View → Run Spindump这个卡住了"**。
      - 对图标服务取样卡住，Run Spindump 也卡住。可能的共同点（推测）：这些界面要画图标（授权窗口、取样窗口），也在等图标服务。只要图标服务卡着，靠界面取证据就不可靠。
      - 以前强制退出没响应的程序时，系统自动写下的 spin 报告是成功的（磁盘上那几份）。
    - 17:29 给用户两条路：
      1. 先花一分钟试一个只改设置的办法：系统设置 → 辅助功能 → 显示 → "Show window title icons"（这台 Mac 的辅助功能设置里有这一项）。开着就关掉，然后强制退出终端再打开。
         - 能打开：说明触发点就是标题栏图标，也有了能用的终端，用 `sudo spindump iconservicesagent 3 -onlyTarget -noFile` 在终端里看图标服务的栈。
         - 没这一项、或者本来就关着：走第 2 条。
      2. 做一份只多一个启动参数的测试镜像，关掉图标服务：
         - 在 7.5 GiB 载荷 `payload.bigwin-s1.img` 上加 `disable-jobs=com.apple.cameracaptured,com.apple.iconservices.iconservicesagent`。命令行的同名参数盖过内置参数，内置的那一项是 `disable-jobs=com.apple.cameracaptured`，所以照机也一起留着。65 个字符，缓冲区 200（`BootWatchdogPolicy.c:63`），字符都在允许范围内（同一文件第 102 行）。
         - 打包用 1b 的新固件。
         - 预期：有的地方图标会缺（上游 iPadOS 上见过），但程序不会再等它。终端能用之后，读 `log show` 里图标服务以前的记录和那几份 spin 报告，并看内存满了以后还卡不卡。
         - 这份镜像不在设计点名的那几份里，不是内核或驱动改动，但要用户说可以才做、才启动。
- **17:32 用户发来照片 #14、#15："是不是当前内核内存回收存在问题，导致已占用的内存未释放，新开直接卡死"**（1b，平板时钟这次是 Sat 14 Nov 1:42，两张同一分钟）
  - 1b 的物理内存 **7.50 GB**，和第 1 步一样，1b 的读数这一条过了。
  - #14 的内存页：已用 5.38 = 程序 2.49 + Wired 2.63 + 压缩 0.2364；缓存 1.66；交换 0；压力绿。
  - #15 的内存页：已用 5.57；Wired **2.82**（同一分钟里比 #14 多了 0.19 GB）；程序 2.49；压缩 0.2364；缓存 1.66。
  - 图标服务：iconservicesd PID 131（`_iconservices`，1.4 MB，2 线程，54 端口）；iconservicesagent PID **790，root**（1.4 MB，2 线程，43 端口）。
    - 终端是 PID 774，图标服务比它晚起，和"点开终端后它才出现"一致。
    - 被拉起来的是 root 那一份，不是用户那一份。43 个端口说明它已经连上了好几个服务，不像卡在刚启动加载库的阶段。
  - 进程表（按内存）：
    - WindowServer 944.0 MB；活动监视器 549.9 MB（偏大，可能和前面卡住的取样、Spindump 有关）；WallpaperAerialsExtension 344.4 MB（动态壁纸）；Terminal (Not Responding) 139.9 MB。
    - 其后依次是 Notification Center 101.3、Control Center 91.7、Dock Extra 68.0、mediaanalysisd 58.6、Siri 54.2 MB 等。
  - 对照这台 Mac（macOS 27.2，`launchctl print`）：用户域那一份 iconservicesagent 跑过 37 次，root 那一份 9 次。两份最后一次退出的原因都是 `JETSAM_REASON_MEMORY_IDLE_EXIT`。所以在正常的 Mac 上，内核按"空闲退出"杀掉它、要用时再拉起，是平常事；平时给用户程序服务的是用户域那一份。
  - 回答用户：
    - 照片不像"占着的内存放不出来"。缓存 1.66 GB 内核随时能丢；压缩只有 236 MB；交换 0；压力绿，回收还没被逼紧。前几趟内存满了以后，活动监视器、系统设置照样能开；这次活动监视器也涨到了 550 MB。
    - 卡的是要图标的新窗口，图标服务本身才 1.4 MB，不是在等大块内存。
    - 但"内存满"和卡住确实连着，可能有两条：
      1. 内存满正是内核开始回收、也开始按空闲退出杀它的时候，之后再拉起来的那一份卡住（推测）；
      2. Wired 一分钟里涨了 0.19 GB，Wired 不能回收，一直涨下去就真没东西可回收了。
    - 要分清，得在卡住时看图标服务的内核栈和 launchd 对它的记录（`launchctl print`），这些都要能用的终端。
- **约 17:35 用户："Show window title icons默认是关着的"**：辅助功能那一项本来就关着，这条路不通。
- **17:43 做好了不带图标服务的测试镜像（只从内存启动，还没启动，等用户说可以）**
  - 载荷 `<output>/payload/payload.bigwin-s1-noicon.img`，sha256 `b14c6424…`。从 `payload.bigwin-s1.img`（`ccd883c6…`）做出来，和它只差两处：
    - `disable-jobs=com.apple.cameracaptured,com.apple.iconservices.iconservicesagent`：命令行盖过内置参数，所以照机也照旧关着；
    - `debug=0x14e` 写成 `debug=334`：同一个值，短 2 字节，因为参数行超了上限 2 字节。
    - 参数行正好 1000 字节，工具的上限是不超过 1000。没有 `data-reset`，没有 `lite`。
    - 菜单文件 `EFI/UniXNU/unixnu.toml` 里只有默认项 `xnu` 有参数行。镜像里另外两行 `args = …` 是空闲簇里的旧数据。
  - 镜像 `out/flash/boot-v4-payload.bigwin-s1b-noicon.img`：新固件（`boot-bigwin.img`，`5c926a3f…`）加这份载荷，210903040 字节，sha256 `61cff115…`。`bootimg-contents.py` 核对过装的是这份载荷。
  - 打包时没给 22 份日常镜像加上只读保护：文件清单写进了沙箱的临时目录，不在沙箱里跑的打包命令读不到。打包前后算的 sha256 完全一样，日常镜像没有被动过。
  - 注意：这条策略写的是系统域的 `disabled.plist`，可能管不到每个用户自己那一份 iconservicesagent。所以启动后要看活动监视器里还有没有它，是谁的身份。
  - 启动后要做的：
    1. 活动监视器搜 icon，拍一张；
    2. 打开终端，看能不能用；
    3. 能用就在终端的 设置 → Profiles → Window 里取消 "Working directory or document"，这样以后正常镜像里终端也不会因为标题栏图标卡住；
    4. `launchctl print system/com.apple.iconservices.iconservicesagent | head -30`，再把 `system` 换成 `gui/$(id -u)` 各拍一张；
    5. `cd /Library/Logs/DiagnosticReports`，`less Terminal_2026-11-14-082152_MacBook-Pro.spin`，输入 `/iconservicesagent` 回车跳过去，拍那一屏；
    6. 照常用 20 分钟，看内存满了以后新开程序还卡不卡。
- **17:45 用户："看看远端提交有没有新的镜像编译分支"**（17:46 拉取了四个仓库的全部远端，另外拉了 rponeawa 和 CrossDarwin 的 UniXNU-sheng、CrossDarwin 的 uefi-sheng；只拉取，没有合并）
  - 远端没有现成镜像：仓库里只有源码，镜像要用本机的芯片号自己打。上游 CI 用的是他们自己的私有芯片号。
  - 和内存问题有关的两个：
    1. **CrossDarwin/UniXNU_macOS 的 `vm/signed-text-revalidation`**（`3be2a10`，11-14 19:49），新增内核补丁 `profiles/os/macos-27.3-26C5035r/patches/xnu-12377/cshash-signed-text-revalidation.patch`，加进 `patches/xnu/series`，还带 `tests/codesign/test_text_fixup.py`。
       - 它的说明："Signed-text fixups leave resident vnode pages different from their signed bytes. Hash exact configured replacements as their original bytes during eager and lazy 16 KiB authentication and derived 4 KiB validation."
       - 我们的内核在开机时改两处代码页：`../UniXNU-sheng/board.toml:242` 的 `text_fixups`（`dyld_shared_cache_arm64e.03` 偏移 `0x5de1134`，`08060037` 换成 `1f2003d5`）；`timebase-user=1` 改 libsystem 里读时钟的例程（`timebase-user-scaled-read.patch`）。
       - 这些页在内存里和签名不一样。等内存满了、同一个 16 KiB 块里有页被回收再读回来时，按块重新校验（`cs-lazy=1` 走的就是按块校验）会对不上。块被记成 bad，`cshash-native4k-lazy.patch:349-352` 会给 `cs_native4k_lazy_bad` 加一。
       - 这和"内存第一次用满之后才出事"对得上：那正是代码页第一次被回收、再读回来的时候。
       - 不在 upstream/main 里，也不在我们的内核里。我们自己的 `sheng-text-fixup-verified-pagein.patch` 只管 decmpfs 读页那一条路，不管按块校验。
       - 校验失败以后进程是被杀还是卡住，没核对。先看证据：`sysctl vm.cs_native4k_stats` 里 `bad` 不为 0，就基本坐实。
       - 我 13:17 因为上游 run139 也开着 cs-lazy 而把它降了级。现在看，上游 11-14 晚上专门修了这条路，降级的理由不够。
    2. **rponeawa 的 `f4e0bc2`**（今天 17:42，"fix: reserve firmware-owned DRAM during memory adoption"）：`board.toml` 把 4 GiB 以下几块固件自己用的内存排除在收编之外，改了 `package/GpuMemoryPool.cpp`。这几块是 mpss、mpss_dsm、TZ/XBL/QTEE、trusted UI、llcc_lpi 等，原来只排除了音频 DSP 的 64 KiB。
       - 这关系到低位内存区的收编：第 3 步，以及日常镜像默认的收编。
       - 管不到 9 GiB 那次在登录窗口闪：那 1.5 GiB 在 4 GiB 以上。
  - 其他分支：
    - CrossDarwin `boot/sheng-firmware-compat`（"Record the qualified desktop boot"，UniXNU_macOS 同名分支 "Preserve the qualified sheng firmware transport"）；
    - uefi-sheng upstream `sheng` 合进了早期看门狗 PR #7（看门狗不要照搬，见 16:24 一条）；
    - rponeawa 的三个充电分支；
    - 上游主线今天下午的几个只有文档。
  - 建议：先启动刚打好的不带图标服务的测试镜像，拿到能用的终端，输 `sysctl vm.cs_native4k_stats` 拍一张。`bad` 不为 0，再请用户同意把这个补丁加进内核（这是内核改动），打一份 7.5 GiB 的测试镜像从内存启动，看内存满了以后还卡不卡。
- **17:50 用户："可以，启动"**（测试镜像第一次上机，暂记 NI-1）
  - fastboot（17:50:25）：a 剩 **3** 次、b 7 次，都是 unbootable no；电压 3848 mV。
    - 17:15 时是 7 次，中间只有一次内存启动（不扣次数），却少了 4 次。多半是用户强制重启时，平板先从槽位 a 正常起了一段，然后才进的 fastboot（推测）。
    - 17:50:36 `fastboot set_active a`，读回 a 7、b 7。
  - sha256 `61cff115…` 相符。17:50:37 `boot-sheng.py out/flash/boot-v4-payload.bigwin-s1b-noicon.img`：`Booting OKAY`，45 秒内引导程序没有回来。
- **约 17:57 用户："最早的镜像版本terminal是有一段时间可用的，你修改了什么造成了它后面变得不可用了"**（17:59 查记录回答）
  - 日常镜像从 11-14 21:11 起没动过。这次会话的命令记录里一次 `fastboot flash` 都没有。`boot_a` 里一直是 `boot-v4-flash.prev.img`（`40234c20…`，18:18 那一份）。
  - 11-14 晚上终端正常的那次（18:41 到 19:01 之间从 `boot_a` 开机，"至少运行了约 5 分钟"）用的就是这一份。同一份镜像，那时能用，今天一开就卡。
  - 记录里的解释：差别在打开终端时内存满没满。
    - 那时每次只开几分钟，终端在内存满之前就打开了。
    - 今天 D6 开机约 8 分钟就满了。每次强制重启后系统会把上次的窗口重新打开（终端、活动监视器 550 MB），还有动态壁纸进程 344 MB，终端常常是在内存满了以后才打开的。
    - 所有记录都没有出过"内存没满就卡"的反例。
  - 我改过的东西：
    - 11-14 刷过 `boot_a` 五次：
      - 01:43，`ae0d4179…`，没有关机修复；
      - 02:21，`4cb441e0…`，加了关机修复；
      - 18:18，`40234c20…`：在 02:21 那份的基础上，补丁加了 `macos-4k-zone-va-budget`、`macos-swapin-io-priority`（上游 #244、#245）、`macos-union-shutdown`、`macos-vm-volume`，命令行加 `vm-swapin-io=1`；
      - 19:01，`c244f53d…`，实测内存表，出过终端卡住，已撤回；
      - 21:11，刷回 18:18 那份。
    - 今天的大内存测试镜像都只从内存启动。
    - 所有镜像共用平板上同一个用户数据卷。几十次强制重启、没电关机都发生在它上面，缓存有没有损坏不知道。
    - `timebase-user=1`、`cs-lazy=1`、`text_fixups` 是上游 11-11 的提交带进来的，每一份镜像都有，不是后来加的。
  - 不知道的：02:21 那份（没有 18:18 加的内存补丁）在内存满了以后还能不能用。记录里它从没跑到内存满。
  - 可以做的对照：从内存启动 `out/flash/boot-v4-flash.prev2.img`（`4cb441e0…`，17:59 核对过，文件还在），一直用到内存满，看终端卡不卡。不动 `boot_a`；要用户说可以才启动。
- **约 18:01 用户："现在启动的系统都会默认带之前运行的缓存，能不能纯净启动os而不是通过shift+enter登录"**（18:02 回答）
  - 内存每次开机都是空的。带过来的是用户数据卷里的"上次的会话"：重开的程序和窗口、登录项、动态壁纸。这些是用户设置，存在用户数据里，不在启动镜像里。改一次，所有镜像都生效（它们共用一个用户数据卷）。
  - 不用终端就能做的：
    1. 系统设置 → 桌面与程序坞，打开 "Close windows when quitting an application"（这台 Mac 的 `DesktopSettingsIntents.appex` 里有这一项）：程序再打开时不恢复旧窗口。
    2. 系统设置 → 通用 → 登录项：把"登录时打开"里的都去掉。
    3. 系统设置 → 墙纸：换成静态图片，不用动态（Aerial）的。省下 WallpaperAerialsExtension 的 344 MB。
    4. 从苹果菜单重启或关机时，去掉 "Reopen windows when logging back in"。
  - 终端能用时再加一条：`defaults write com.apple.loginwindow TALLogoutSavesState -bool false`，不再记录要重开哪些程序，强制重启后也不重开。这台 Mac 的 `loginwindow` 里有 `TALLogoutSavesState` 和 `TALAppsToRelaunchAtLogin` 这两个键。强制重启后是否也生效，平板上没验证。
  - 真正的"全新系统"只有 `data-reset`，会清空整个用户数据，不建议；只有用户明确要重置时才考虑。
  - 这只让每次开机的起点一样、内存晚一些满，不修卡住本身。
- **约 18:03 用户："清空用户数据之后启动大内存的镜像"**（18:04 回答，等用户确认，还没有动）
  - 做法：
    1. 从内存启动现成的 `out/flash/boot-v4-install.img`。18:04 核对 sha256 `75fb800a…`，参数行以 `data-reset=1` 开头，内核是 11-14 00:48 那份，6 GiB。它清空用户数据、按种子新建，账户还是做种子时 `--user` 那个，Setup 跳过。
    2. 登录一次，确认进了桌面。
    3. 再进 fastboot，从内存启动 1b（新固件、7.5 GiB，已经进过桌面）。
    - 不新做带 `data-reset` 的镜像，只用这份现成的。
  - 这一趟本身也是个对照：干净的用户数据上内存满了以后终端还卡不卡。不卡，就是旧用户数据有问题；还卡，就和用户数据无关。
  - 会丢的东西：平板上的文件和设置；`/Library/Logs/DiagnosticReports/` 里那几份 spin 报告；统一日志。spin 报告是还没读的证据。如果测试镜像里终端能用，清空前可以先花几分钟把 spin 报告里 iconservicesagent 那一段拍下来。
  - 清空不可恢复。请用户进 fastboot 后回复"确认清空"再做。
- **18:05 用户："确认清空"**
  - fastboot（18:05:43）：a 7、b 7，都是 unbootable no；电压 3782 mV。`boot-v4-install.img` sha256 `75fb800a…` 相符。
  - 18:05:52 `boot-sheng.py out/flash/boot-v4-install.img`：`Booting OKAY`，45 秒内引导程序没有回来。用户数据正在清空、按种子新建。spin 报告和统一日志随之没了。
  - 下一步：用户登录一次，确认进了桌面；再进 fastboot，从内存启动 1b，在干净的用户数据上看内存满了以后终端还卡不卡。
- **约 18:13 用户："当前启动的镜像还是不使用swap分区"**（18:14 回答）
  - 现在跑的是清空用的 `boot-v4-install.img`，内核是 11-14 00:48 的。交换文件的修复 `macos-vm-volume.patch` 是 11-14 18:18 那一版才加进来的（`patches/xnu/series:29`）。
    - 补丁说明：没有它时第一个交换文件打开就报 EROFS（"Failed to open swap file 30"）；压缩区满了以后，交换线程空转，桌面卡住。
    - 所以这次开机本来就用不了交换，这一趟只是为了清空。日常镜像和大窗口内核都带这个补丁。
  - 就算交换能用，活动监视器里交换是 0 也是正常的：压力是绿的、文件缓存还在时，macOS 先丢缓存、再压缩，最后才写交换。以前每次卡住时都是交换 0、压力绿，还没走到要用交换的那一步，所以卡住不是因为缺交换。被钉住的 2.6 到 3.3 GB 也换不出去。
  - 1b 上验证交换：`sysctl vm.swapusage`。要逼它用交换，可以用 `memory_pressure -l warn`：一直分配内存，直到系统发出警告级别的低内存通知（`man memory_pressure`）。这也是一个可控的"把内存用满"的办法，Ctrl-C 结束。
  - 1b 这一趟的顺序：
    1. 一登录就开终端，趁内存还没满，取消 "Working directory or document"；
    2. `sysctl vm.cs_native4k_stats` 和 `sysctl vm.swapusage` 各拍一张；
    3. 照常用到内存满，或者用 `memory_pressure -l warn`，再拍一次这两条，看程序卡不卡。
- **约 18:15 用户："用社区最新的镜像打包方法进行测试"**（18:19 查完，给了做法，等用户选；没有改代码）
  - 社区最新的是 CrossDarwin 两个仓库的 `boot/sheng-firmware-compat`（11-15 15:55 到 16:00）。拉到了核心仓库的 `refs/remotes/crossdarwin/*`，以及 `../UniXNU-sheng` 的 `refs/remotes/crossdarwin/*`。
    - 打包："The sheng macOS profile uses a SHA-256-pinned firmware template for its ABL transport. `unixnu bootimg` replaces only DarwinBoot with the loader from the current firmware build, preserving the qualified shim, board firmware, DTB and Android header settings."（`docs/porting/macos.md`，`3181584`）
    - 结果：报告 `reports/macos-desktop-20261115.md` 是 8 GiB 的机器，用模板镜像临时启动，选数据初始化后进了桌面。重启后的保持、Wi-Fi、蓝牙、长时间 GPU 都没测。
    - 这个分支已经合进了代码页重新校验的修复 `3be2a10`。
    - 核心仓库比我们多 20 个提交：修复、Metal 和蓝牙的源码版本、种子工具、IPSW 下载、各组件的源码版本、模板打包。`git merge-tree` 试合并到我们的 HEAD 没有冲突。
    - 设备仓库比我们多 14 个：SoC feed、触摸和存储的源码版本、Wi-Fi 和蓝牙、数据初始化、模板传输。`git merge-tree` 报 "failure to merge"，要手动合。
  - 原样用不了：
    - 模板里的固件是按 8 GiB 机器的内存布局做的，本机的受保护内存位置更低（`../uefi-sheng` 里没提交的那处改动）；
    - 本机引导程序只认 v4 头，他们的是 v0。
  - 给用户的三个做法：
    - **A（推荐先做）**：只把 `cshash-signed-text-revalidation.patch` 加进我们的内核补丁序列。重编内核，做 7.5 GiB 载荷，用新固件打包，只从内存启动。
      - 我们的 `cshash-native4k-lazy/parallel/stats`、`native-text-fixup` 四个补丁和它父提交里的逐字节一样，能直接接上。
      - 设备补丁 `sheng-text-fixup-verified-pagein.patch` 也改 `ubc_subr.c`（7186 行附近），新补丁在 7141 行附近加 52 行，要试打一遍确认。
    - **B**：把两个仓库的社区分支整个合进来，保留本机的固件、v4 头和 7.5 GiB 设置，重编内核、载荷和固件。一次改很多。
    - **C**：原样用他们的镜像。不做，理由见上。
  - A 和 B 都是内核改动，要用户点头。
- **约 18:22 用户："先B，然后尝试下v0格式"**。18:24 写了短设计 `docs/superpowers/specs/2026-11-15-community-branch-test-design.md`（`539e534`），等用户批准。
  - 设备仓库试合并只有 `board.toml` 两处冲突，都是内存设置，打算保留本机的。
  - `../uefi-sheng` 已经没有未提交的改动：本机内存表在本地分支 `local/sheng-12g-memory-map` 的两个提交里（`5dfcc572`、`20331338`）。
  - 日常镜像的固件比这两个提交早，用的是上游的内存表，在本机一直正常。
- **约 18:25 用户："先试 v0 格式"**（改了顺序：先做设计里的第二部分）
  - 18:25 下载社区模板到 `out/downloads/cd-template-218fdcce/`（`out/` 不入库）：
    - 地址取自社区 `board.toml`：`https://github.com/CrossDarwin/macOS-ForSheng/releases/download/sheng-recovery-218fdcce-preview1/sheng-recovery-218FDCCE-boot.img.xz`；
    - 11822220 字节，sha256 `8fed0304…`，和社区钉住的值相符；解压后 165343232 字节，sha256 `6d96d27a…`。
  - 镜像内容：
    - 头版本 0，页大小 4096，cmdline 为空；os_version 解出来是 17.0.0、补丁 2026-08；
    - kernel 4905304 字节，gzip 压缩（社区说的 shim 加板级固件、设备树）；
    - ramdisk 160432128 字节，是 FAT 卷，里面是 `EFI/UniXNU/unixnu.toml`、`Payloads/kernel.macho`、`kernel.macho.adt`。
  - 菜单：`timeout = -1`（等按键），`fallback_timeout = 30`（这个键我们的代码里没有，含义不知道），只有一项 "SHENG macOS 26 - UFS+ISC+LOG+UI+REC 218FDCCE"。
    - 参数带 `-v`、`cpus=1`、`native-ufs-root=1`、`native-ufs-diagnostics=1`，没有 `data-reset`。
    - 这是社区一份 macOS 26 的诊断内核，不是我们的系统。
  - 11-13 本机试 v0 的结果（本文件"header v0 启动不了"一条）：`Booting OKAY` 后 0.4 秒引导程序就回来了，屏幕黑；之后再 `fastboot boot` 一直报 `Load Error`，要先 `fastboot reboot bootloader`。当时的推测是本机的安卓 14 国行引导程序不支持 v0，或者附带的设备树对不上。
  - 这次的做法：原样从内存启动这份模板，只看引导程序接不接受。
    - 接受了，会出现社区的菜单。用户拍照，然后按住电源键加音量下键回 fastboot，不进它的内核。
    - 不接受，`fastboot reboot bootloader` 一次再继续。
    - 都不写 `boot_a`。要用户进 fastboot、说可以再启动。
- **18:29 用户："可以"**（v0 模板第一次上机，暂记 V0-1）
  - fastboot（18:29:22）：a 7、b 7，都是 unbootable no；电压 3780 mV。模板解压后的 sha256 `6d96d27a…` 相符。
  - 18:29:31 `boot-sheng.py out/downloads/cd-template-218fdcce/sheng-recovery-218FDCCE-boot.img`：`Sending 'boot.img' (161468 KB) OKAY`，`Booting OKAY`，**45 秒内引导程序没有回来**（18:30:26 数到 0 台）。
  - 11-13 我们自己的 v0 是 0.4 秒就回来；这次引导程序接受了社区的 v0 模板，镜像在跑。屏幕上是什么，等用户的照片。
  - **约 18:33 用户发来照片 #16："启动卡在这了"**。
    - 菜单没有停住，自己进了社区的 macOS 26 诊断内核，多半就是那个 `fallback_timeout = 30`。内核在挂系统卷时 panic：
      - "SHENG - FIRST PANIC / PANIC: UFS ROOT FAILURE: no userdata partition"
      - "stage=GPT entries prepared=0 published=0 reads=0 failures=0 … result=00000000"
      - "HC cap=3587031f ver=00000400 hcs=0000010f hce=00000001"
      - "CMD n=6 type=01 op=28 lun=00 ocs=00 rsp=21000000"
      - "SMMU slot=104"
      - 异常是 "Synchronous exception taken while SP1 selected at pc 0xfffffe00073bc878, esr 0x96000021"，屏幕上还有一个二维码。
    - 说明社区的 v0 外壳在本机能走完整条链：引导程序 → 社区固件 → 加载器 → XNU 内核 → UFS 驱动（读了 GPT）。
    - 停住的原因是社区这份旧诊断内核的 UFS 驱动没在 GPT 里找到 userdata。它没有找到数据分区，也就没有写用户数据。这和我们的系统无关。
    - 要用户按住电源键加音量下键回 fastboot。
  - 下一步（等用户批准设计）：
    - 先只合并核心仓库的社区分支（试合并无冲突），用里面的模板打包工具，把我们自己的内核和载荷装进这个 v0 外壳，从内存启动；
    - 再做设备仓库合并和全部重编。设计文件已按这个顺序改好。
- **18:39 用户："进fastboot了，帮我开始执行"**：批准了设计。
  - fastboot（18:39:45）：a 7、b 7，都是 unbootable no；电压 3772 mV。
  - 计划 `docs/superpowers/plans/2026-11-15-community-v0-wrap.md`（`9de4d61`），由我自己执行。
  - Task 1：`git merge --no-ff crossdarwin/boot/sheng-firmware-compat`，合并提交 `4ad8cab`，没有冲突。
    - 社区带来的 `test_boot_template.py` 10 个测试 OK。
    - 这次合并把 `drivers/AdrenoMetal` 和 `drivers/RamBlock` 两个子模块的指针改到了社区的版本，工作区里还是旧的检出（`git status` 显示 `M`）。第二阶段重编之前要 `git submodule update` 这两个。
  - Task 2：`local-tools/make-bootimg-v0-template.py` 加测试 `local-tools/test_make_bootimg_v0_template.py`，`8dc1b5d`。
    - 先写的测试，5 个都失败；实现后 5 个 OK，端到端那个也真跑了，不是跳过。
    - 和计划的小差别：先查载荷里有没有 `data-reset`，再查模板校验值，这样两个拒绝的测试互不依赖。
  - Task 3（18:45 前做完）：用模板 `8fed0304…`、加载器取自 `SILICIUM_UEFI.bigwin-8407c84f.fd`，打了两份：
    - `out/flash/boot-v0-cd.bigwin-ctl6.img`：载荷 `payload.bigwin-ctl6.img`（`f1338e96…`，6 GiB），214626304 字节，sha256 `d1dfe732…`；
    - `out/flash/boot-v0-cd.bigwin-s1.img`：载荷 `payload.bigwin-s1.img`（`ccd883c6…`，7.5 GiB），214626304 字节，sha256 `5e747915…`。
    - 两份的 kernel 都是 4904432 字节，ramdisk 209715200 字节，换进去的加载器 sha256 都是 `717d5649…`。
    - 22 份日常镜像的 sha256 和 17:43 记的一样。打包脚本里第一次的前后核对没起作用：zsh 不按空格拆变量，算出来的是空的。之后按 17:43 的文件清单重算才比对上。
  - Task 4 Step 1（V0-2）：
    - fastboot（18:45:17）：a 7、b 7，都是 unbootable no；电压 3772 mV；sha256 `d1dfe732…` 相符。
    - 18:45:27 `boot-sheng.py out/flash/boot-v0-cd.bigwin-ctl6.img`：`Sending 'boot.img' (209596 KB) OKAY`，`Booting OKAY`，45 秒内引导程序没有回来。
    - 屏幕结果等用户。
    - **约 18:49 用户："先卡登录屏，然后黑屏"**。
      - 社区外壳加我们的加载器和内核，走到了登录窗口，比社区那份诊断内核走得远。之后停在登录窗口，再黑屏。
      - 还不知道：有没有指针、能不能输密码、是输完密码才黑的还是自己黑的、黑屏时有没有指针。
      - 社区报告见过相似的现象：新清空的数据卷普通启动后"cursor on a black screen"，日志说数据请求没准备好，要用菜单里的"数据初始化"。
      - 清空后，用户有没有用清空镜像登录过一次，没确认。
    - **约 18:52 用户："卡黑屏之后，会在回到登录页面"**：登录窗口 → 黑屏 → 登录窗口，在循环。
      - 像是 WindowServer 或登录会话崩了又被拉起来。本机 11-14 见过 WindowServer 因为系统卷哈希不符而循环崩溃，后来靠设备补丁修好；这份内核带着那个补丁。
      - 是否和输不输密码有关，还没答。
    - **约 18:55 用户："进系统了，但是桌面是黑的"**（多半还是这次 V0-2，循环几次后登进去了）。
      - 还不知道菜单栏和程序坞在不在、能不能开程序。
      - 新清空的数据卷，默认墙纸可能是动态的那种，墙纸进程起不来时桌面就是黑的（推测）。
      - 请用户：
        - 菜单栏、程序坞都在：拍活动监视器的内存页，在终端输 `sysctl vm.cs_native4k_stats` 拍一张，再在墙纸里换成静态图片；
        - 只有指针：拍一张，然后做 v4 对照。
    - **约 18:57 用户："windows server奔溃后，又回到登录页面了"**：确认是 WindowServer 在反复崩溃。社区外壳加我们的系统，这一趟算不通过。
      - 崩溃报告会写在数据卷的 `/Library/Logs/DiagnosticReports/WindowServer-*.ips`，重启后还在。
      - 下一步：做 v4 对照（同一载荷，我们自己的旧固件）。能进桌面的话，在控制台的崩溃报告里打开 v0 这次留下的 WindowServer 报告，拍第一屏：异常类型、终止原因、崩溃的线程。
      - 我的推测（没证据）：社区外壳里的板级固件是按他们机器做的，内存保留区或显示设置和本机对不上。
- **约 19:03 用户："进fastboot了先试我们的"**（v4 对照，暂记 C6-1）
  - 19:01 两次都数到 0 台。用户说屏幕上是 FASTBOOT，19:04:48 再查数到 1 台：a 7、b 7，都是 unbootable no；电压 3833 mV。
  - sha256 `e9b25075…` 相符。19:04:57 `boot-sheng.py out/flash/boot-v4-payload.bigwin-ctl6.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - **约 19:18 用户发来照片 #18、#19、#20："现在这份是好的可以正常进桌面，切屏之后activity monitor卡住了"**
    - #19（这次 v4 对照，平板时钟 1:45）：
      - 内存页：物理 **6.00 GB**；已用 4.74 GB = 程序 0.9684 + Wired 3.13 + 压缩 0.6638；缓存 1.25 GB；交换 0；压力绿。已用加缓存 5.99 GB，又满了。
      - 墙纸是静态图片。进程表里 JournalWidget 那一行上有彩色转圈的指针。
    - #20，控制台的崩溃报告列表（由新到旧）：
      - 1:47 WindowServer ×2；
      - 1:46 iconservicesagent ×2、spotlightknowledged.updater；
      - 1:39 mds_stores、ReportCrashService、iconservicesagent ×2、WindowServer、iconservicesagent；
      - 1:38 iconservicesagent ×2（User）……
      - 图标服务在反复崩溃。
    - #20 打开的 **WindowServer 报告**：
      - WindowServer [3287]，User ID 88；Date/Time 2026-11-14 01:47:17.3156，Launch Time 01:47:11.8445（起来 6 秒就崩）；Time Awake Since Boot 1100 秒。
      - "Exception Type: EXC_BAD_ACCESS (SIGKILL (Code Signature Invalid))"，"Exception Subtype: UNKNOWN_0x32 at 0x00000001a2319048"，"Termination Reason: Namespace CODESIGNING, Code 2, Invalid Page"。
      - VM Region：`0x1a2319048` 落在 `/System/Library/Frameworks/QuartzCore.framework/Versions/A/QuartzCore` 的 `__TEXT`（`0x1a1f5c000-0x1a23ed000`，r-x，SM=COW）。
      - "Kernel Triage: VM - (arg = 0x0) A memory corruption was found in executable text"。
    - 这正是开机时改过的那一页。`../UniXNU-sheng/board.toml:237-242` 的 `text_fixups` 改的就是 QuartzCore 的 `IOMFBDisplay::framebuffer_pixel_format`，在 `dyld_shared_cache_arm64e.03` 文件偏移 `0x5de1134`。注释里写着："a write into the mapped page … made the page invalid and code signing killed WindowServer"。
      - 崩溃地址在它那个 16 KiB 块里的偏移是 `0x1048`，补丁点是 `0x1134`，都在块里的第 2 个 4 KiB 页，相差 236 字节。地址和文件偏移的对应关系没核对，但多半就是同一页。
      - 社区的 `cshash-signed-text-revalidation.patch` 修的正是这件事："Signed-text fixups leave resident vnode pages different from their signed bytes"。这次合并已经把它带进了核心仓库，但现在跑的内核是合并前编的，没有它。
    - #18 打开的 **iconservicesagent 报告**：
      - iconservicesagent [1555]，User ID 501（用户那一份）；Launch 01:44:41.5806，崩于 01:46:55.7476。
      - "Triggered by Thread: 1, Dispatch Queue: com.apple.iconservices.cleanup"；"EXC_CRASH (SIGABRT)"，"Namespace SIGNAL, Code 6, Abort trap: 6"。
      - 崩溃线程：`__pthread_kill` ← `abort` ← `__assert_rtn` ← `MTLReportFailure.cold.1` ← `MTLReportFailure + 840`（Metal）← Metal `0x1d7f91000 + 119176` ← MPSImage `+[CIBlurProcessor processWithInputs:arguments:output:error:]_block_invoke.219` ← CoreImage `CIImageProcessorKernel applyWithExtent` ← `CI::ProcessorNode::render` ← `CI::MetalContext::render_node` … `CI::Context::render`。
      - 也就是 CoreImage 用 MPS 做模糊时，Metal 的校验断言失败，图标服务被 abort。崩了以后 launchd 按"exponential throttling"推迟重启（这台 Mac 上 `launchctl print` 能看到这个属性），这段时间里要图标的程序就一直等。这就是终端卡住的那一层。
      - 断言的具体文字没拍到。
      - 社区合并带进来的 AdrenoMetal 有一个提交 `6d4a3f3 fix(metal): Distinguish missing library functions from specialization errors`，是否相关不知道。
    - 两份报告的 Time Awake 都是 1100 秒。这次 v4 是 19:04:57 启动的，19:20 才 15 分钟，所以这几份崩溃多半出自上一次 v0 那一趟（18:45 启动，18 分钟后约 19:03，正是用户说 WindowServer 循环崩溃的时候）。平板的时钟不可信，这一点没有坐实。
    - 结论：要的两个修复都已经在合并进来的社区代码里，是设计的第二阶段（设备仓库合并、全部重编）。
  - 第二阶段计划 `docs/superpowers/plans/2026-11-15-community-merge-rebuild.md`（`7a8068b`）。
    - Task 1：设备仓库 `ba18a9f` 把设备补丁和 `series` 那一行提交到本地分支。`feeds.toml`、`unixnu.lock` 暂存为 `stash@{0}`（pre-cd2）。
      - `af5304a` 合并社区分支：`board.toml` 用 `git merge-file --ours` 解决，窗口 `0x240000000`、`owned_memory_outside_ranges = 16` 是本机的，社区的模板一节、`size_mib = 187`、`max_image_bytes` 照收。
      - 子模块按记录的版本检出：设备仓库 Ath12kWifi `39cc47b`、QcaBluetooth `68e2e605`、ShengNovatekTouch `69fdd622`、ShengUfs `b6fe07b3`；核心仓库 AdrenoMetal `6d4a3f38`、RamBlock `00a6e5dd`。
    - Task 2：构建前日常文件 `33d294c8`、`8a36fe56`、`35f03ec4`，备份都在。19:24 OS 镜像只读挂到 scratchpad 的 `os-mount`（`/dev/disk11s1`，构建完要卸载）。19:24 起后台跑 `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。
      - 第一次（19:28 前结束）：内核编好了，`<output>/kernel/kernel.macho` 现在是 `ed6a1794…`，日常内核被盖掉了，要从 `kernel.macho.daily-33d294c8` 还原。日志里 `cshash-signed-text-revalidation.patch`（第 137 行）和 `sheng-text-fixup-verified-pagein.patch`（第 157 行）都打上了。
      - 载荷停在："unixnu: the payload files take 180 MiB; raise size_mib (now 187) in board.toml [payload]"。`payload.img` 没被改（仍是 `8a36fe56`）。
      - 设备仓库 `b172096`：macOS 的 `size_mib` 改回合并前的 200（测试镜像只从内存启动）。之后重跑同一条构建命令。
      - 第二次（19:31 前结束）成功。内核仍是 `ed6a1794`。
        - `nm` 里有 `_cs_text_fixup_hash`（社区补丁加的）和 `_cs_text_fixup_restore`（设备补丁加的）。
        - 载荷 `cfbbe5c9`，但菜单是社区的新样子：`timeout = -1`（有按键设备时等按键），还多一项 "Initialize macOS Data and boot"（要确认，确认后才加 `confirm_args = ["data-reset=1"]`）。
        - 我们的 `make-payload-variant.py` 拒绝任何提到 `data-reset` 的载荷（"unixnu.toml already mentions data-reset"），所以这份只另存为 `payload.cd2-base.img`（只读），不用。
      - 设备仓库 `7fe7546`（本地）：macOS 覆盖里把 `payload.install` 放回 `remove` 列表，去掉社区加的 install 一节和 `"timeout" = -1`。
        - 菜单因此和合并前一样，3 秒倒计时，只有 Boot、Restart、Power off。
        - 菜单代码 `package/UniXNUPkg/Library/UniXNULib/Config.c:1622` 本来就保证倒计时不会启动要确认的项。不留这一项，是为了守住"测试镜像不带 data-reset"这一条。
      - 19:35 先把 cd2 内核放回原位，再只跑 `./unixnu build payload`，得到 `payload.cd2-base-noinstall.img`（`d018afc5…`，只读）。日常内核和载荷再从备份还原，核对 `33d294c8`、`8a36fe56`、`35f03ec4`。
      - 另存的：`<output>/kernel/kernel.macho.cd2-ed6a1794`（`kernel.json`、`kernel.map.json` 同后缀）、`payload.cd2-base.img`（`cfbbe5c9`，带初始化项，不用）、`payload.cd2-base-noinstall.img`（`d018afc5`）。
    - Task 3（19:38 前做完）：
      - 载荷 `payload.cd2-s1.img`（`768f8e83…`，`darwinboot-memory-size=0x1e0000000`、`floor=0x920000000`、`memory-outside=0`）和 `payload.cd2-ctl6.img`（`53917b0d…`，`0x180000000`、`0x980000000`、`memory-outside=0`）。参数行都是 923 字节。
      - 镜像（新固件 `boot-bigwin.img`；v0 用社区模板，加载器 `717d5649…`）：
        - `out/flash/boot-v4-payload.bigwin-cd2-s1.img` `aaa4e60c…`
        - `out/flash/boot-v4-payload.bigwin-cd2-ctl6.img` `543a135a…`
        - `out/flash/boot-v0-cd.cd2-s1.img` `d538e492…`
        - `out/flash/boot-v0-cd.cd2-ctl6.img` `66bd8552…`
        - `bootimg-contents.py` 核对过 v4 两份装的载荷。
      - 22 份日常镜像的 sha256 和 17:43 记的一样。19:38 OS 镜像已卸载。
    - 下一步 Task 4：先启动 `boot-v4-payload.bigwin-cd2-s1.img`（7.5 GiB，本机固件），要用户说可以。
  - **约 19:45 用户："可以"**（cd2 第一次上机，暂记 CD2-1）
    - fastboot（19:46:33）：a 7、b 7，都是 unbootable no；电压 3756 mV；sha256 `aaa4e60c…` 相符。
    - 19:46:40 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd2-s1.img`：`Booting OKAY`，45 秒内引导程序没有回来。
    - **约 19:56 用户发来照片 #21、#22："avtivity monitor和terminal在我打开系统设置之后，就开始进入卡顿不可交互状态，系统设置在短暂卡顿后，可交互但图标加载异常"**
      - #22（平板时钟 11:30）：
        - 进了桌面，终端能用，标题栏也画出了文件夹小图标；
        - 物理内存 **7.50 GB**；已用 5.43 = 程序 2.17 + Wired 2.67 + 压缩 0.5761；缓存 2.08；交换 0；压力绿；
        - `sysctl vm.cs_native4k_stats`：`lazy 1 blobs 822 auth 90167 bad 0 err 0 … reval 0 range 0`；
        - 进程表前几名：mediaanalysisd 393.8 MB、WallpaperAerialsExtension 344.7 MB、Terminal 255.1 MB。
      - #21（11:32，打开系统设置之后）：
        - 第二次 `sysctl`：`auth 90368 bad 0 err 0 … reval 0`；
        - 内存：已用 5.50 = 程序 2.38 + Wired 2.76 + 压缩 0.3394；缓存 1.94。已用加缓存 7.44，已经满了；
        - 系统设置左栏的图标大多是空白方块；活动监视器上是彩色转圈。
      - 读法：
        - 第一处问题（WindowServer 被代码签名杀掉）这一趟还没出现。内存满时校验失败数仍是 0，但时间还短。
        - 第二处问题还在：系统设置一下子要很多图标，图标服务多半又在 Metal 断言里崩了、被推迟重启；活动监视器和终端也要图标，跟着卡住。待崩溃报告证实。
      - 一条线索：`../UniXNU-sheng/board.toml:83-85` 给 iPadOS 的 iconservicesagent 设了环境变量 `FORCE_SOFTWARE_RENDERER = "0"`、`CI_ENABLE_METAL_GPU = "0"`。上游文档说这是 24A446 原厂的设置。macOS 的覆盖把 `payload.runtime.launchd_job_environment` 整个去掉了，macOS 上的 iconservicesagent 没有这两个变量（这台 Mac 上它的 plist 里 `EnvironmentVariables` 也是空的）。
      - 下一步：
        1. 控制台崩溃报告里这次的 iconservicesagent，拍断言原文；
        2. 不改镜像先试：终端能用时 `launchctl setenv CI_ENABLE_METAL_GPU 0`、`launchctl setenv FORCE_SOFTWARE_RENDERER 1`、`killall iconservicesagent`，再开系统设置看图标。这是让 CoreImage 改走 CPU 的推测，不一定生效；重启就失效。
- **约 20:05 用户："我要怎么构建你连接我新macos测试环境的隧道，ssh可以么，我让设备进fastboot，帮我重启当前系统，我去用terminal配置sshd"**
  - 做法：走局域网 SSH。
    - macOS 上 Wi-Fi 由 en0 承载，上游写着"Association, DHCP and traffic are verified on the device"（`docs/zh/devices/sheng.md:805`）。本机上没试过。
    - 平板连上和 Mac 同一个 Wi-Fi，开 sshd，用一把专用密钥登录。
  - 20:07 在 `out/ssh/` 生成专用密钥 `tablet_ed25519`（ed25519，无口令，注释 `unixnu-tablet-test`）。`out/` 不入库，`git check-ignore` 确认过。不碰 `~/.ssh`。
  - sshd：这台 Mac 的 `/System/Library/LaunchDaemons/ssh.plist` 是 `com.openssh.sshd`，`Disabled = true`，按 socket 启动。
    - 开启用 `sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist`。
    - 注意：我们的内核每次开机都会重写 `/private/var/db/com.apple.xpc.launchd/disabled.plist`（`BootWatchdogPolicy.c:123-133`，O_TRUNC），开启的记录重启后就没了，每次开机要重新运行一次。
  - 公钥由用户在 Mac 自己的终端里用 `ssh-copy-id` 装上去（要输一次平板的登录密码）。我连的时候用 `-o IdentitiesOnly=yes` 和单独的 `out/ssh/known_hosts`。平板的 IP 不写进入库的文件。
  - fastboot（20:07）：a 7、b 7，都是 unbootable no；电压 3793 mV。20:07:42 再次从内存启动 `boot-v4-payload.bigwin-cd2-s1.img`（`aaa4e60c…`），`Booting OKAY`，45 秒内引导程序没有回来。
  - **约 20:10 用户："进桌面鼠标闪烁了，再次启动试下"**：这一趟（CD2-2）进了桌面，指针在闪。指针闪以前也在内存满的时候出现过，这次是一进桌面就闪。
    - fastboot（20:10:45）：a 7、b 7，都是 unbootable no；电压 3775 mV。
    - 20:10:54 第三次从内存启动同一份镜像（CD2-3）：`Booting OKAY`，45 秒内引导程序没有回来。
    - 同一份镜像，一次正常、一次指针闪，又是"单次开机不能拿来比较"。
- **约 20:23 用户："连接远程设备ssh -i out/ssh/tablet_ed25519 -o 'UserKnownHostsFile=out/ssh/known_hosts' …，拉取设备上的报错日志"**（SSH 通了；平板地址只在对话里，不写进文件）
  - 20:24 平板：
    - 内核 "Darwin Kernel Version 25.5.0: Sun Nov 15 19:27:32 +08 2026"（cd2 内核），开机 13 分钟；
    - `hw.memsize` 8053047296；`vm.swapusage` total 0；
    - 平板的时钟这次是对的（连上网对了时）。
  - 崩溃和卡顿报告拷到本机 `data/tablet-logs/20261115-2025/`（`data/` 不入库）：
    - cd2 那几趟里**没有** WindowServer 的崩溃报告，也没有 iconservicesagent 的 `.ips`；
    - 有 `Terminal_2026-11-14-113246/113552_MacBook-Pro.spin`、`Terminal_…113729.hang`（11:3x 是 CD2-1 时平板的时钟），以及 `Console_2026-11-15-040554_MacBook-Pro.spin`；
    - 旧的 WindowServer 和 iconservicesagent 报告都在 Nov 14 01:35-01:47，出自 cd2 之前那几趟。
  - Terminal 的 spin（"Slow response to HID event"，开机 692 秒，内存 7.50 GB）：主线程还是那条路，`NSThemeDocumentButtonCell` → `ISConcreteIcon generateImageWithDescriptor` → NSXPC 同步等待 → `mach_msg2_trap`，242 个样本里 231 个。
  - 同一份 spin 里有两个 iconservicesagent：
    - [769] 是 root 那一份，空闲，2 个线程，1457 KB；
    - [848] 是新起的，"Execed from xpcproxy"，11:31:36.939 起、11:31:37.565 止，只活了 0.6 秒，203 KB 涨到 90.99 MB，29 个线程。
    - [848] 最后几个样本停在 `+[CIBlurProcessor processWithInputs:…]` → MPSImage → `MPSDevice::GetLibrary` → NativeAdrenoMetal `nmb_library_new` → NativeAdrenoMetal 内部加缺页，然后就没了。下一份 spin 里换成了 [927]。
  - 统一日志（`/usr/bin/log show --last 3d`，远端 zsh 的 `log` 是内建命令，要写全路径）：
    - 每次启动 iconservicesagent 都记两条 "[com.apple.renderbox:error] precondition failure: <private>"（Fault），时间是 11:31:07、11:31:28、11:32:09、11:33:29、04:19:59、04:25:20；
    - 还有写不进 `com.apple.iconservicesagent` 偏好、"user tccd unavailable" 这两种。
    - 断言原文被隐去了；`.ips` 的 `asi` 也是空的。
  - **launchd 的记录（`launchctl print gui/501/com.apple.iconservices.iconservicesagent`，04:27）**：
    - `state = spawn scheduled`；`runs = 17`、`successive crashes = 17`；
    - `last terminating signal = Abort trap: 6`；
    - `minimum runtime = 640`（base 10）。
    - root 那一份（`system/…`）`runs = 1`，`last exit code = (never exited)`。
  - **结论（这一层有证据了）**：
    - 用户那一份图标服务每次启动都在画图那条路上 abort（RenderBox 的 precondition failure，或 CoreImage 的 MPS 模糊在 Metal 断言里）；
    - launchd 按 exponential throttling 推迟重启，16 分钟里已经推到 640 秒；
    - 这段时间里要图标的程序都在等它，所以终端、活动监视器卡住，系统设置的图标空白。
    - 这和内存满不满没有关系。"越往后卡得越久"是推迟时间指数增长的结果，正好和内存慢慢用满同时发生，看起来就像"内存满了才卡"。
  - 第一处问题（WindowServer 被代码签名杀掉）在 cd2 内核下没有再出现。
- **约 20:28 用户同意试验（原话"可以"）**：经 SSH 让图标服务改走 CPU 再重启它。
  - 20:29 在 SSH 会话里 `launchctl setenv CI_ENABLE_METAL_GPU 0`、`FORCE_SOFTWARE_RENDERER 1`。`getenv` 读得到，但 `gui/501` 里这项服务的 "inherited environment" 只有 `SSH_AUTH_SOCK`：SSH 会话的设置到不了桌面会话那个域。
  - `launchctl kickstart -k gui/501/…` 一直没返回，放到后台后停掉了。
  - 20:31 已 `unsetenv` 还原。
  - `launchctl debug gui/501/… --stderr …`（下次启动时带环境变量、并把它的标准错误写进文件）报 "This subcommand requires root privileges"。不带 `-k` 的 `kickstart` 也没把它拉起来，还是 `spawn scheduled`、`runs = 17`。
  - 要往下做，得有 root。我不碰密码，请用户二选一：
    - 在 Mac 自己的终端里用 `ssh -t` 逐条输 sudo；
    - 或者临时加一个 sudoers 文件，只放行 `/bin/launchctl`、`/usr/bin/log`，以及删这个文件本身。试完删掉。
- **约 20:33 用户："最好还是使用修复gpu渲染，cpu先看下是否可行，以及是否能恢复部分功能"**（还没选哪种 root 方式）
  - 20:34 不用 root 又从日志里读到一条公开的。每次图标服务启动后不到一秒都有：
    - "(Metal) /AppleInternal/…/MetalPerformanceShaders/MPSImage/Filters/MPSImageUnaryKernel.mm, line 335: error '<private>'"；
    - 时间：11:31:07、11:31:28、11:32:09、11:33:30、04:24:15、04:25:20。
    - 这是 MPS 一元图像核（模糊属于这一类）报错，接着断言 abort。错误原文被隐去了。
  - 同一份日志里还有 SkyLight 的 "On-demand launch of the Window Server is allowed for root user only"、"This user is not allowed access to the window system right now"、"Invalid display 0x00000000"。是否相关不知道。
  - 修 GPU 要先知道我们的 Metal 实现在哪一步拒绝了 MPS 的核。
    - 插件 `drivers/AdrenoMetal/NativeBridgeMetalFrontend.mm:566-574`：拒绝的原因走 `NBLOG`。
    - 只有设了 `SHENG_LOG_GPU` 时，才作为公开字符串写进系统日志（插件读启动参数 `log-gpu=1`，`NativeAdrenoMetalPlugin.mm:389-390`）。
    - 设了 `NMB_LOG_STDERR` 时也写标准错误。
  - 20:36 做了只多一个启动参数的测试镜像（只从内存启动）：
    - 载荷 `payload.cd2-s1-loggpu.img`（`ac42cf3a…`，在 `payload.cd2-s1.img` 上 `--arg log-gpu=1`，参数行 933 字节）；
    - 镜像 `out/flash/boot-v4-payload.bigwin-cd2-s1-loggpu.img`（`691717af…`）；
    - 22 份日常镜像没变。
    - 用它开机后，经 SSH 读日志就能看到插件拒绝的原因，不用 root。
  - CPU 那条路仍要 root（`launchctl debug --environment`），或者开机后趁终端还能用，由用户在平板终端里 `launchctl setenv` 再 `killall iconservicesagent`。
- **约 20:38 用户："可以"**（日志镜像上机，暂记 LG-1）
  - 20:39 数到 0 台。我起了一个最多等 150 秒的等待，被用户打断（用户说"continue"）。
  - 20:40:38 数到 1 台：a 7、b 7，都是 unbootable no；电压 3805 mV。
  - 20:40:43 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd2-s1-loggpu.img`（`691717af…`）：`Booting OKAY`，45 秒内引导程序没有回来。
- **约 20:47 用户发来截图 #24**：用户按方式一在平板上装了 sudoers 文件（"parsed OK"、"OK"）。SSH 用的地址和上次一样。
  - `sudo -n -l` 显示规则是 `(root) NOPASSWD: /bin/launchctl, /usr/bin/log, /bin/rm/etc/sudoers.d/zz-unixnu-test`：`/bin/rm` 和路径之间少了空格（截图里的命令就是这样），所以删这个文件的那一项不生效。
  - 试完要请用户用密码自己删：`sudo rm /etc/sudoers.d/zz-unixnu-test`。这个文件在数据卷上，重启后还在。
  - 20:48 这一趟开机 7 分钟，用户那一份图标服务已经 `runs = 15`、`successive crashes = 15`，`minimum runtime = 160`。
  - 插件日志（`log-gpu=1` 起作用了）：每次启动都是：
    - "native-metal: no device answer: the device has no answer for gpuCoreCount / maxVertexAmplificationCount / maxComputeThreadgroupMemory / isLargeMRTSupported / supportsComputeCompressedTextureWrite / supportsConditionalLoadStore"；
    - 接着 "base limits: 22 fields of 264 bytes filled"；
    - 约 0.13 秒后就是 MPS 第 335 行的错误；
    - 中间插件没有记下任何拒绝（`NBLOG` 的 "refused"）。
  - 20:49 `sudo launchctl debug gui/501/…` 报 "Configuration failed: 150: Operation not permitted while System Integrity Protection is engaged"。`sudo log config --mode "private_data:on"` 报 "Invalid Modes"。两条路都走不通。
  - **20:50 用 JXA 在 SSH 里复现了**：探测脚本 `local-tools/tablet-ci-blur-probe.js`，用 `osascript -l JavaScript` 跑，对棋盘图做 CoreImage 高斯模糊。
    - sigma=2、128 px 就触发，标准错误里是全文："MPSImageUnaryKernel.mm:335: failed assertion `[MPSImageGaussianBlur apply...] source may not be nil'"，退出码 134。
    - 纯色图不触发（纯色模糊了还是自己）。
    - 也就是 CoreImage 交给 MPS 模糊核的输入纹理是空的。
  - **CPU 这条路不通**（20:51）：
    - `CI_ENABLE_METAL_GPU=0` 时 `CIContext contextWithOptions:` 直接返回 nil；
    - `FORCE_SOFTWARE_RENDERER=1`，或者用 `kCIContextUseSoftwareRenderer` 建上下文，都还是 "(metal 1)"，同一个断言；
    - macOS 27 的 CoreImage 没有 CPU 后备。只能修 GPU。
  - 修 GPU 的线索：
    - `NMB_LOG_STDERR=1` 跑探测，插件在断言前没有任何 "refused"。新建纹理（`NativeBridgeMetalFrontend.mm:4500-4512`）、IOSurface 纹理（4515-4534）、纹理视图（1393-1394）失败时都会记。
    - `NBTexture` 加了 `MTLTexture` 协议（`IOGPUMetalDeviceShim.h:217-234`）。
    - 所以空纹理不是插件明着拒绝的，原因还没找到。上游以前修过几处 iconservicesagent 拿到 nil Metal 对象的问题（`NativeBridgeMetalFrontend.mm:552`、`:1660`、`:1764`、`:4214`）。
- **约 20:52 用户："能不能在新的镜像中，默认开启ssh服务，便于后续联调"**（这是对内核改动的明确要求）
  - 做法：在每次开机都会重写的 launchd 策略文件里，把 `com.openssh.sshd` 写成启用（`<false/>`）。系统自带的 `ssh.plist` 是 `Disabled = true`，这样就盖过去了。
    - 加的是启动参数 `enable-jobs=<label>[,…]`，只放进测试镜像的载荷，日常镜像不受影响。
  - 设备仓库 `1939cc1`（本地）：
    - `package/BootWatchdogPolicy.c` 加 `enable_jobs[200]`、`append_job_state(cursor, disabled)`，字符检查和 `disable-jobs` 相同。只给了 `enable-jobs` 时也写这个文件。
    - `scripts/check-boot-watchdog-policy.py` 加了三条测试：只启用；和禁用并存；非法字符返回 EINVAL。先跑过一遍是失败的（第 245 行的断言），实现后整份通过（"PASS: production policy initializer…"）。
  - 20:55 构建前日常文件 `33d294c8`、`8a36fe56`。OS 镜像只读挂到 scratchpad 的 `os-mount`。20:55 起后台跑 `./unixnu build kernel payload`。
  - 20:58 前构建成功：
    - 内核 `347fa01f…`：字符串里有 `enable-jobs`，`nm` 里 `_cs_text_fixup_hash`、`_cs_text_fixup_restore` 都在；
    - 载荷 `ae7ab7ea`：菜单 3 秒、只有 Boot、Restart、Power off。
    - 另存为 `kernel.macho.cd3-347fa01f`（`json`、`map.json` 同后缀）和 `payload.cd3-base.img`（只读）。日常文件已还原，核对 `33d294c8`、`8a36fe56`、`35f03ec4`。OS 镜像已卸载。
  - 测试载荷 `payload.cd3-s1-ssh.img`（`85e28889…`）：7.5 GiB（`0x1e0000000`、`0x920000000`），加 `memory-outside=0 enable-jobs=com.openssh.sshd log-gpu=1`，参数行 962 字节。
  - 镜像 `out/flash/boot-v4-payload.bigwin-cd3-s1-ssh.img`（`c02657ed…`，新固件），`bootimg-contents.py` 核对过。22 份日常镜像没变。
  - 只从内存启动，要用户说可以。开机后 SSH 应该不用手动开（公钥已经在平板的用户数据里）。
- **约 21:11 用户："进入fastboot了"**（cd3 第一次上机，暂记 CD3-1）
  - fastboot（21:12:20）：a 7、b 7，都是 unbootable no；电压 3742 mV；sha256 `c02657ed…` 相符。
  - 21:12:35 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd3-s1-ssh.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - 约 21:14 用户连上 Wi-Fi。21:15 SSH 直接连上，平板上什么都没输：`launchctl print-disabled system` 里是 `"com.openssh.sshd" => enabled`，`kern.bootargs` 里有 `enable-jobs=com.openssh.sshd`、`log-gpu=1`。默认开 SSH 这一条成立。
  - 21:16-21:26 经 SSH 查 GPU 这条路（探测脚本都在平板的 `/tmp`，主要的一份在 `local-tools/tablet-ci-blur-probe.js`）：
    - 直接用 MPS：两张插件建的 RGBA16Float 纹理，`MPSImageGaussianBlur` 编码执行，`status 4`，没有错误。`MPSSupportsMTLDevice` 是 true。MPS 本身能用。
    - 只画棋盘、只画原始像素，都能出图。只要加上模糊就报 "source may not be nil"。
    - CoreImage 渲染图（`CI_PRINT_TREE`，PDF 拷到 scratchpad 的 `ci-tree/`）：处理器节点是 "processor CIBlurProcessor-2.000 … outputFormat=RGBAh canReduceChannels supportsCompressed onlyMetal"，输入是 RGBAh 的中间图。
    - **换工作格式就好**：`kCIContextWorkingFormat = kCIFormatRGBA8`（或环境变量 `CI_WORKING_FORMAT=RGBA8`）能出图；默认的 RGBAh 不行。关缓存不行。
    - IOSurface 的 BGRA、RGBA、RGhA、`&RhA`、`&BGA`、RGfA 都建得出来，也都能包成纹理，不是这里的问题。
    - CoreImage 读的环境变量（从这台 Mac 的 `dyld_shared_cache_arm64e.05` 里搜出来的 `CI_*`）里试了几个：
      - **`CI_ENABLE_MPS=0` 能出图**（CoreImage 改用自己的模糊核，仍然用 GPU）；
      - `CI_LOSSLESS_COMPRESSED_INTERMEDIATES=0`、`CI_LOSSY_COMPRESSED_INTERMEDIATES=0`、`CI_IOSURFACE_INTERMEDIATES=0`、`CI_RECYCLE_METAL_TEXTURES=0`、`CI_USE_INFLIGHT_INTERMEDIATES=0`、`CI_ENABLE_HALF_KERNELS=0`、`CI_INTERMEDIATE_SRGB_TEXTURES=0` 都不行。
    - `CI_LOG_TEXTURE_CACHE=1`：RGBAh 时分配两张纹理就断言了，RGBA8 时分配了三张、正常出图。
    - 把变量送进图标服务，试了三条，都不成：
      - `sudo launchctl asuser 501 launchctl setenv` 进的不是桌面会话那个域；
      - `sudo launchctl bsexec <Dock> launchctl setenv` 报 "141: Reentrancy avoided"；
      - 在 `~/Library/LaunchAgents` 装一个登录时跑 `launchctl setenv CI_ENABLE_MPS 0` 的代理：`gui/501` 的 environment 里有了 `CI_ENABLE_MPS => 0`，但图标服务这项任务的 "inherited environment" 是登录时定下的，之后又起的几个实例照样报 MPS 错。
      - 重新加载 Apple 的服务（`kickstart -k`）被 SIP 拒绝。这个代理 21:25 已从平板上删掉。
    - **可行的做法（21:26 验证）**：CoreImage 在第一次模糊时才读 `CI_ENABLE_MPS`。在已经建好上下文（插件已加载）之后再 `setenv("CI_ENABLE_MPS","0",1)`，模糊照样出图。
      - 所以可以由我们的 Metal 插件在加载时自己设这个变量，和它从启动参数设 `SHENG_LOG_GPU` 一样（`drivers/AdrenoMetal/NativeAdrenoMetalPlugin.mm:388-391`）。
      - 打算加启动参数 `ci-mps=0`，只放进测试载荷，不覆盖环境里已有的值。
      - 这是驱动改动，要用户同意。
    - 根因（为什么 RGBAh 中间图交给 MPS 时是空的）还没找到。上面这个是绕开它的办法，图标仍由 GPU 画。
- **约 21:28 用户："可以，开始改"**（同意改 Metal 插件）
  - 插件子模块 `drivers/AdrenoMetal`：在本地分支 `local/sheng-ci-mps` 上提交 `74ec0ff`。
    - 改的是 `NativeAdrenoMetalPlugin.mm`，在 `log-gpu` 那几行后面加 `#if TARGET_OS_OSX` 段：`if (bootArgSet("ci-mps=0")) setenv("CI_ENABLE_MPS", "0", 0);`，不覆盖环境里已有的值。
  - 核心仓库 `bc40cd0`：子模块指针和 `components.toml` 里 AdrenoMetal 的 `revision` 一起改到 `74ec0ffa…`。
    - 构建开始时 `update_submodules` 会把子模块拉回记录的版本（`scripts/unixnu/feeds.py:208-228`），所以记录的版本必须跟着改。
  - 没有写主机测试：这一行在插件的进程初始化里，没有现成的测试架子。用平板上的行为来验证：
    - 改前：探测脚本必定断言，图标服务一直崩；
    - 改后：带 `ci-mps=0` 的镜像里，探测脚本要出图，`launchctl print` 里的 successive crashes 不再涨。
  - 21:31 把 cd3 内核（`347fa01f`，带 `enable-jobs`）放回原位，OS 镜像只读挂上。后台跑 `./unixnu build payload`。完了要另存载荷、还原日常文件。
  - 21:34 前构建成功：
    - 插件 `<output>/tree/build/adreno-metal-plugin-macos27/NativeAdrenoMetal.bundle` 21:33:48 重编，二进制里有 `ci-mps=0`；
    - 载荷 `0df8f588`，另存为 `payload.cd4-base.img`（只读）。
    - 日常文件已还原（`33d294c8`、`8a36fe56`、`35f03ec4`），OS 镜像已卸载。
  - 测试载荷 `payload.cd4-s1-ssh-cimps.img`（`9c58d5c1…`）：7.5 GiB，加 `memory-outside=0 enable-jobs=com.openssh.sshd log-gpu=1 ci-mps=0`，参数行 971 字节。
  - 镜像 `out/flash/boot-v4-payload.bigwin-cd4-s1-ssh-cimps.img`（`4ba1bede…`，新固件），`bootimg-contents.py` 核对过。22 份日常镜像没变。只从内存启动，要用户说可以。
- **约 21:37 用户："看下仓库最新的pr是不是已经有修复方案了"**（21:37-21:39 用 `gh` 查，只读）
  - 没有修这个问题的 PR。在 UniXNU 组织下搜 PR 和 issue：`MPSImage`、`source may not be nil`、`CI_ENABLE_MPS`、`CoreImage` 都是 0 条。`iconservicesagent` 只搜到 11-09 及以前已合并的诊断类 PR（AdrenoMetal#15、UniXNU-sheng#62、UniXNU#176，以及 10-22 的两条 GPU 权限）。
  - 相关但不是同一个修复：
    - **AdrenoMetal#36**（OPEN，CrossDarwin 的 `metal/function-lookup-errors`）："Return MTLLibraryErrorFunctionNotFound when a requested function name is absent, allowing clients such as Core Image to continue searching other libraries"。
      - 就是我们合并进来的 `6d4a3f3`。带着它，模糊照样断言，所以不是这个。
    - **UniXNU#250**（OPEN，filipnavara）："launchd job environment without the Wi-Fi or Bluetooth runtime"。
      - 让 board 里 `launchd_job_environment` 的值在不带 Wi-Fi、蓝牙运行时时也生效：合并、签名后的 OS launchd 缓存放进附加包的 `xpc/`。
      - 这是给系统任务加环境变量的正路（比如给 iconservicesagent 加 `CI_ENABLE_MPS=0`），但它验证的是 iPadOS 27（asteroids），macOS 的覆盖把 `payload.runtime.launchd_job_environment` 整个去掉了，能不能用在 macOS 上没验证。
    - **UniXNU#249**（OPEN，filipnavara）："bootstrap page tables for windows up to 9 GiB on native 4 KiB"，16 页改 22 页，在 Nothing Phone (3a) 8 GiB 上验证。和我们路线 A 的 Task 1 是同一件事、同一个数字。
  - AdrenoMetal 的分支（CrossDarwin、leoforney、lss717、FFT-infra）最近的提交里都没有和 MPS、CoreImage 模糊有关的。
- **约 21:54 用户："可以"**（cd4 第一次上机，暂记 CD4-1）
  - fastboot（21:55:03）：a 7、b 7，都是 unbootable no；电压 3798 mV；sha256 `4ba1bede…` 相符。
  - 21:55:10 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd4-s1-ssh-cimps.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - **约 21:57 用户："看下ssh是否可连接，当前鼠标指针闪烁，画面卡住"**
    - SSH 能连（21:57:45，开机 2 分钟）。`kern.bootargs` 有 `ci-mps=0`、`enable-jobs=com.openssh.sshd`。
    - **`ci-mps` 这一处起作用了**：
      - 21:58:34 在平板上跑 `local-tools/tablet-ci-blur-probe.js 2 20`，128、512、1024 px 全部 "ok"，退出码 0。之前的镜像上同一个脚本在第一张就断言。
      - 用户那一份图标服务 05:58:06（平板时间）启动的 [880]，到 21:58:49 还活着，没有 MPS 报错。`runs = 3`、`successive crashes = 2` 不再涨。那两次崩溃在这之前，日志里没取到原因。
    - **新问题：画面卡住是 GPU 复位后 WindowServer 恢复不过来**：
      - WindowServer 一直占约 185%-200% CPU。日志从平板时间 05:57:08 起，两分钟里有：
        - 3591 条 "native-metal: command buffer refused: renderCommandEncoder: render encoder: NotImplemented(MadeBeforeRecovery)"；
        - 几千条 "[com.apple.SkyLight] Detected command buffer completion failure. Error code = 0xffffffffffffffff"；
        - 以及 CoreAnimation 的 "MTLCommandBuffer … error = … MadeBeforeRecovery"。
      - `MadeBeforeRecovery`（metal2vulkan 运行时 `crates/metal2vulkan-runtime/src/error.rs:2032-2036`、`detach.rs:19-22`）：VkDevice 丢了又恢复了，恢复前建的对象在新设备上一律拒绝，要重新建。WindowServer 一直拿旧对象画，所以一直失败。
      - 设备丢失来自内核的 hangcheck（`drivers/Adreno740/NativeAdrenoPublish.cpp:271-300`）：每 500 ms 看一次环有没有进展，没进展就复位 GPU，"only the client whose submission hung sees its device lost"。它用 `IOSleep` 和栅栏值，不看墙钟。
      - 也就是说，平板时间 05:57:08 前后 WindowServer 的一次提交真的卡住了，GPU 被复位，WindowServer 没能重建自己的对象。插件在 iPadOS 上遇到这种情况会结束 backboardd 让它重启（`NativeBridgeMetalFrontend.mm:575-583`），macOS 上没人重启 WindowServer。
      - 时间上的巧合：平板时间 05:57:02.548，连上 Wi-Fi 后系统对时，"Time Change: accumulated change of 66485.520 seconds"（往前跳了约 18.5 小时），6 秒后开始出错。hangcheck 不看墙钟，所以多半只是巧合，没坐实。
      - 跳之前，`com.apple.dock.extra` 有 "binary archive refused: … IconRendering.framework/Resources/binary.metallib" 和两次 "heap texture refused: OutOfMemory(Heap)"（这个会退回到单独建纹理）。
      - 内核的 GPU 恢复计数（`native_adreno_recovery`）不在 sysctl 里，读不到复位了几次。
      - 和 `ci-mps` 有没有关系分不清：CD2-2（没有 `ci-mps`）一进桌面也是指针闪。
    - 这时 WindowServer 是 `_windowserver` 用户的进程，SSH 的账户杀不了；`launchctl kickstart` 系统服务会被 SIP 拒绝。只能重启。
- **约 22:04 用户："可以"**（同一份镜像第二次上机，暂记 CD4-2）
  - fastboot（22:05:18）：a 7、b 7，都是 unbootable no；电压 3829 mV；sha256 `4ba1bede…` 相符。
  - 22:05:24 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd4-s1-ssh-cimps.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - **约 22:12 用户："连上wifi了，现在桌面上，鼠标指针会闪，从一个地方突然跳到另个地方，但我实际位移没有那么多跳"**（终端、系统设置的情况用户还没说）
    - 22:12:40 SSH，开机 7 分钟，负载 2.01。WindowServer 不在 CPU 前几名。
    - **这一趟没有 GPU 复位**：
      - 12 分钟里没有 "MadeBeforeRecovery"，也没有 "command buffer completion failure"。
      - 平板时间 06:08:14 连上 Wi-Fi 时照样有 "Time Change: accumulated change of 67099.739 seconds"，之后没出事。
      - 所以上一趟的卡死不是对时引起的，那次 GPU 卡住是偶发的。WindowServer 在 GPU 复位后恢复不过来，这个问题还在，以后要处理。
    - **图标服务稳定**：
      - 用户那一份 [863] 06:08:37 启动，到 22:13 还在跑；`runs = 3`、`successive crashes = 2`（那两次在 06:08:37 之前）。
      - 这一趟日志里没有 `MPSImageUnaryKernel` 报错。
      - root 那一份 [506] 开机就在，日志里时不时还有 "[com.apple.renderbox:error] precondition failure: <private>"（Fault），但进程没退出。
      - 用 `NSWorkspace iconForFile:` 取终端、/Applications、系统设置的图标都成功。
      - 系统设置（[831]，开了 4 分 44 秒）和活动监视器都在跑。
    - 指针乱跳是老问题：今天早上日常镜像的基线、第 1 步（10:13）都记过"指针在两个位置之间每一到三帧跳一次"，和这次的改动无关，单独查。
  - **约 22:16 用户："当前桌面画面卡死了，你能尝试读到相关中断日志么"**（22:16-22:21 经 SSH 读）
    - 又是一次 GPU 复位，WindowServer 没恢复过来。
      - WindowServer 115% CPU；10 分钟里 6957 条 `MadeBeforeRecovery`。
      - 平板时间 06:15:32.023 WindowServer 记 "[com.apple.coreanimation:Render] timed out fence 743029343556"；06:15:32.957 记 "Detected command buffer completion failure. Error code = 0x1" 和 "MTLCommandBuffer … error = GpuRecoveryVictim"；06:15:34 起一直是 `MadeBeforeRecovery`。
      - 卡住前几秒，root 那一份图标服务 [506] 一直在建纹理（"heap texture refused: … OutOfMemory(Heap)"，会退回单独建）。MPS 关掉以后，它用的是 CoreImage 自己的核。
      - 新的崩溃报告没有。
    - **和 `ci-mps` 无关，是老问题**。统一日志里 WindowServer 的 `MadeBeforeRecovery` 按 10 分钟计：
      - Nov 14 11:20 那一格 2065 条：平板时间，即 CD2-1，用户"打开系统设置之后，活动监视器和终端卡住"那一次；
      - Nov 15 04:30 那一格 455 条：CD2-3 或 LG-1，都没有 `ci-mps`；
      - 05:50 9288、06:00 5697（CD4-1），06:10 8271（CD4-2）。
      - 第一条 "Error code = 0x1" 出现在 2026-11-14 11:28:31.130、2026-11-15 05:57:02.697、06:15:32.957。
      - 用 `--start/--end` 按时间段取以前那几次的上下文，取回来的是新的行：时钟跳过以后，日志按时间筛不可靠。
    - **WindowServer 为什么不重启**：插件只在命令缓冲区的 Metal 错误码是 11（DeviceLost）时结束渲染服务器（`NativeBridgeMetalFrontend.mm:3463-3472` 调 `endRenderServerAfterGpuLoss`，`:580-587` 发 SIGTERM）。
      - 现在的运行时会自己恢复设备，WindowServer 拿到的是 `GpuRecoveryVictim`（错误码 1，`metal2vulkan-runtime/src/error.rs` 的 `metal_code`），之后是本地拒绝的 `MadeBeforeRecovery`（`- (void)refuse:`，`:3180-3182`），都不是 11，所以从不结束。
      - 渲染服务器在 macOS 上就是 WindowServer（`NativeRenderServer.h`）。
    - 打算的改法（驱动改动，要用户同意）：
      - 在 `refuse:` 里，拒绝原因含 `MadeBeforeRecovery` 时也调 `endRenderServerAfterGpuLoss()`，WindowServer 被 launchd 重启。
      - 代价：GPU 卡住时会退回登录窗口，程序会关掉，但不再整屏卡死。
      - GPU 为什么会卡住，另外查：现在能看到的只有"卡住前在画图标"这一点，内核的复位记录只在板级日志里，读不到。
  - **约 22:23 用户："有没有更好的优化方案，不让gpu hung"**（22:23-22:26 查，给了做法，等用户选）
    - 板级日志在 userdata 最后 8192 个 4 KiB 块（`../UniXNU-sheng/scripts/read-sheng-log.py:38`）。macOS 里 `diskutil list` 只有存储驱动开的几个窗口：disk1 是 Data 的物理存储，225.5 GB；还有 disk0、disk4、disk6 等。日志那一段不在任何一个里，从 macOS 读不到。
    - 以前读不了，是因为 Linux 读取器是 v0 镜像。现在社区的 v0 外壳在本机能启动（18:29），按它的头部参数重打读取器也许能行，没试。
    - 不改代码就能做的排除试验（只加启动参数）：
      - `gpu-preempt=0`：只用一个环，没有环间抢占。默认是 2：高优先级走环 0，其余走环 1（`docs/zh/devices/sheng.md:562`）。
      - `gpu-dcvs=0`：GPU 不随负载调频（`gpu-dcvs=1` 时随忙闲调频，`:921`）。
      - 抢占和调频是 Adreno 移植里最常见的两个挂起来源，这只是经验判断，没有证据。
    - 触发：已知三次卡住都发生在大量画图标的时候（打开系统设置、程序坞画图标、图标服务画图）。可以经 SSH 用 JXA 连续取一批程序图标来压，也可以请用户反复开关系统设置，再数日志里的 `MadeBeforeRecovery`。
    - WindowServer 在 GPU 复位后自己重启这一条，作为兜底照样要做。
- **约 22:27 用户："可以"**（同意三件事：兜底改动，A `gpu-preempt=0`，B `gpu-dcvs=0`）
  - 插件子模块 `local/sheng-ci-mps` 上提交 `2b9a743`（`NativeBridgeMetalFrontend.mm`）：
    - `- (void)refuse:` 遇到含 `MadeBeforeRecovery` 的拒绝原因时，调 `endRenderServerAfterGpuLoss()`；
    - 那条日志改成按 `NATIVE_RENDER_SERVER` 写进程名（macOS 上是 WindowServer）。
  - 核心仓库 `d3e5fe4`：子模块指针和 `components.toml` 的 AdrenoMetal `revision` 改到 `2b9a743f…`。
  - 22:29 cd3 内核放回原位，OS 镜像挂上，后台跑 `./unixnu build payload`。
  - 压测脚本 `local-tools/tablet-icon-stress.js`：把系统和 /Applications 里每个程序的图标按 16 到 512 六种大小取成位图，逼图标服务画图。
  - 打算从这次的载荷做三份镜像，共同的参数是 7.5 GiB、`memory-outside=0 enable-jobs=com.openssh.sshd log-gpu=1 ci-mps=0`：
    - 基线；
    - A：再加 `--arg gpu-preempt=0`；
    - B：`--replace-arg gpu-dcvs=0`（参数行里本来是 `gpu-dcvs=1`）。
  - 22:32 前载荷构建成功：
    - 插件 22:31:37 重编，二进制里 `ending %s so launchd` 和 `ci-mps=0` 都有，`MadeBeforeRecovery` 出现 4 处；
    - 载荷 `8225f8f3`，另存为 `payload.cd5-base.img`（只读）。
    - 日常文件已还原（`33d294c8`、`8a36fe56`、`35f03ec4`），OS 镜像已卸载。
  - 载荷和镜像（新固件；22 份日常镜像没变）：
    - 基线：`payload.cd5-s1.img`（`b75a3dce…`，971 字节）→ `out/flash/boot-v4-payload.bigwin-cd5-s1.img`（`c5aa28e9…`）
    - A：`payload.cd5-s1-nopreempt.img`（`8772a4c4…`，985 字节，`gpu-preempt=0`）→ `…-cd5-s1-nopreempt.img`（`6fdbc718…`）
    - B：`payload.cd5-s1-nodcvs.img`（`9feae9e8…`，971 字节，`gpu-dcvs=0`）→ `…-cd5-s1-nodcvs.img`（`5bb6b594…`）
  - 比法：
    - 每份开机、连 Wi-Fi 后，经 SSH 跑 `tablet-icon-stress.js` 若干轮，请用户开关系统设置几次；
    - 数日志里 WindowServer 的 `GpuRecoveryVictim`、`MadeBeforeRecovery`、插件的 "the render server's GPU context is lost; ending WindowServer"，以及 WindowServer 的 PID 有没有变；
    - 同时看兜底有没有起作用：卡住后应该回到登录窗口，而不是整屏卡死。
- **约 22:35 用户："可以"**（基线上机，暂记 CD5-BASE-1）
  - fastboot（22:35:39）：a 7、b 7，都是 unbootable no；电压 3852 mV；sha256 `c5aa28e9…` 相符。
  - 22:35:50 `boot-sheng.py out/flash/boot-v4-payload.bigwin-cd5-s1.img`：`Booting OKAY`，45 秒内引导程序没有回来。
  - 约 22:38 用户连上 Wi-Fi。
    - 22:39 起在平板上跑 `tablet-icon-stress.js 6`，同时用 `log stream` 把事件录进 `/tmp/gpu-events.log`：GpuRecoveryVictim、MadeBeforeRecovery、"GPU context is lost"、"timed out fence"、图标服务启动。
    - 用 `log show --last 10m` 数不准：上一趟 WindowServer 也是 PID 173，尾巴算进来了，所以改用 stream。
    - 约 22:44 用户开关了系统设置几次（用户原话"好了，鼠标渲染会飘"）。
  - **基线结果**（平板时间 06:39:51 到 06:45:21，事件拷到 `data/tablet-logs/20261115-hang-ab/`）：
    - 压测 6 轮，66 个程序，2376 张位图，0 个失败，每轮约 42 秒。
    - **一次 GPU 恢复，落在 NotificationCenter [456]**：06:44:09 到 06:44:30，18 条 "command buffer refused: setDepthStencilState: depth/stencil state: NotImplemented(MadeBeforeRecovery)"。
    - WindowServer 只记了两次 "timed out fence"（06:44:24、06:44:33），没有被拒绝。PID 一直是 173，CPU 1.2%，画面没卡死，兜底也就没触发。
    - 也就是这次挂住的是 NotificationCenter 的提交，只有它的设备被恢复；它的对象之后都被拒绝（小组件之类可能画不出来），它不会被重启。
    - 图标服务：06:39:51 启动的 [911] 一直在，`successive crashes = 2` 没变。
    - 指针"飘"仍在，是另一回事。
  - 下一步：A（`gpu-preempt=0`）同样的做法。
    - 下一步的对照：同一份 6 GiB 载荷的 v4 镜像 `out/flash/boot-v4-payload.bigwin-ctl6.img`（我们自己的旧固件，sha256 `e9b25075…`）。
      - 它能进桌面：问题在社区外壳里的固件；
      - 它也卡：问题在载荷或新数据卷上。
      - 要用户说可以再启动。
- **约 22:46 用户："但现在鼠标渲染有时候会出现漂移问题"；22:53 用户："会不会是键盘壳的信号问题，检查下键盘壳为什么会掉线"**（CD5-BASE-1 还开着，只经 SSH 读，没改东西）
  - 采样脚本 `local-tools/tablet-pointer-probe.js`：每 5 ms 读一次窗口系统里的指针位置（`NSEvent mouseLocation`），等到第一次移动后记 30 秒，每次变化一行写进 CSV。原始数据在 `data/tablet-logs/20261115-pointer/`（不入库）。
  - **跳是输入里就有的，不是画的问题**。22:51:45 前后一次 30 秒的读数（用户按要求先慢慢左右划、再快划）：327 次变化，移动中两次变化相隔中位 13 ms（p10 7、p90 29），文档里"每秒约 20 帧"（`docs/zh/devices/sheng.md:510`）和这次不符。
    - 三次大跳（511、597、258 px）都紧跟在一段静止之后（117、154、444 ms）：手指减速到 0，抬起，落到别处，第一步就是一大跳，之后从新位置照原方向接着走。例：往左划到 748,44 停 117 ms，下一步到 1242,174。
    - 同一段里静止超过 60 ms 的有 29 次，26 次之后的第一步只有 0 到 35 px，只有这 3 次跳了。
    - 解释（读代码得出，和数据对得上）：`../UniXNU-sheng/package/Wn8030.c:235-245` 只有在两帧之间手指数或接触编号变了才从新位置重新起算。控制器给第一根手指的编号多半一直是同一个，如果抬手那一帧（没有手指的帧）没收到，落下的那一帧就和抬手前的最后一帧"同一根手指"，抬起点到落点的距离整个算成一次移动。抬手那一帧是控制器没发还是驱动没读到，分不清。
    - 上游没有更新：`upstream/main` 新的 5 个提交、`fix/keyboard-cover-recovery`（内容和本地相同，#93 是合并过的）、`input/digitizer-property-lifetime` 都没动这几处。
  - **键盘壳"掉线"有两种，走的是驱动里不同的路**：
    - 设备被删掉、约 1 秒后重建：统一日志里 `force close (ShengKeyboardCover` 加 `start for ShengKeyboardCover`，从 11-14 以来 9 次（平板时间 11-15 04:04、04:24、04:52、06:43:51 两次连着、06:51:30 等）。驱动只在一个地方删设备：控制器发来"保护套已拿下"的报文（`KeyboardProbe.cpp:514-516` → `detachCover`）。所以是控制器自己看到保护套断开又接上：可能是保护套和平板之间的触点瞬断或保护套自己复位；控制器重载固件后会不会先报一次"拿下"没核对，所以也可能是通信失败后的重载。
    - 一直不好、只有重启能恢复、重新吸附也不行（11-14 两次，见"开机待机久了"一条）：这时设备不删。读或控制连续失败 3 次后驱动释放输入、重载控制器固件，重载失败按 2、4、8、16、32 秒退避一直重试（`KeyboardService.h:14-20、53-57`），失败的原因只记在板级日志的 K 行（I2C 失败次数 `native_keyboard_stats[11]`、最后一次错误 `[13]`），macOS 里读不到。
    - 22:58 设备还在（06:51:30 建的那个），22:57 用户打字能到终端。
  - 打算的做法（驱动改动，要用户同意）：
    - 指针：转换函数拿到每帧的时间，离上一帧超过约 60 ms（移动中约 5 个帧间隔）就当成新的一次触摸，从当前位置起算。先在 `package/tests/wn8030_host.c` 加用例：同一编号、中间没有抬手帧、隔 150 ms、位置差很多 → 不动；隔 13 ms → 照常动。
    - 掉线：把那 17 个计数（阶段、读到的帧、I2C 失败、最后的错误、贴附次数）再加一个重载次数，每秒挂到注册表上一次，SSH 里用 `ioreg` 就能读，下次掉线时当场看是哪一步失败。
    - 不用改代码的试验：一边录日志一边请用户轻按、轻晃保护套和平板接缝处约 20 秒，看会不会出现删设备、重建。
      - 23:01:44 起在平板上录了 10 分钟（`/tmp/cover-wiggle.log`），用户还没做这个试验，就先合上了保护套（下一条）。
- **约 23:08 用户："看下造成当前desktop桌面卡死的原因，记录问题，我刚刚把键盘壳合上了一会，没做其他操作"**（CD5-BASE-1，开机约 33 分钟，只经 SSH 读；日志拷在 `data/tablet-logs/20261115-cover-close-freeze/`，不入库）
  - **原因：保护套合上后压在触摸屏上，触摸屏一直在报触点，WindowServer 的手势处理卡死，不是 GPU 卡住**。
    - 平板时间 07:02:2x 到 07:08:01，WindowServer 每 10 秒记 900 到 1300 条 "hid_event_callback: Invalid event type: 11"（11 是触控 digitizer 事件），约每秒 130 条，和触摸屏 120 Hz 的报点频率相符。
    - 同一段里 BackBoard 记了触点 1 到 10 一个个"touching"又"none"：十个触点全用上了，忽有忽无，像是盖子贴在玻璃上。
    - 07:02:42.946 起 WindowServer 主线程（26e）开始记 "[com.apple.Gestures:Critical] [!] … has been in … phase for …"：有个手势一直停在某个阶段。触点 07:08 停了以后这条还在涨（07:08 那一分钟 658 条，07:10 前一分钟 752 条）。
    - 07:10:24：WindowServer（PID 173，没重启过）CPU 99.7%，问它一次指针位置 5 秒没回；整机别的进程正常，SSH 正常。
    - 这 12 分钟里没有 `MadeBeforeRecovery`、`GpuRecoveryVictim`、"GPU context is lost"，只有 07:02 两条 "timed out fence"。所以兜底（WindowServer 遇 GPU 复位自己重启）不会管这种卡死。
    - 保护套设备 07:06:40 被删、07:06:46 重建（`cover-events.log`），多半是打开或挪动保护套的时候。
  - **缺的那一块（读代码确认）**：盖子霍尔传感器（GPIO 171）只有键盘驱动在读，合上时只停键盘和触控板的输入（`../UniXNU-sheng/package/KeyboardProbe.cpp:474-486`）。触摸屏驱动 `package/TouchProbe.cpp` 不看盖子，屏幕也不熄。iPadOS 上合盖会关触摸和屏幕；macOS 的 WindowServer 本来就不收触摸屏事件（"Invalid event type: 11"），它的手势识别碰上十个忽有忽无的触点就卡住了。
  - 打算的修法（驱动改动，要用户同意）：盖子合上时触摸屏驱动先发一次"全部松开"，之后丢掉报点，打开后再恢复；只看盖子（lid），不看折到背后（tablet），折到背后还要用屏幕。能不能顺便把背光关掉另说。
  - WindowServer 现在这样多半自己好不了，只能重启（SIP 不让杀它）。
- 同一时间暂停的事：Core Image 修复的 PR。查过没人做过（AdrenoMetal#37 改的是纹理优化设置，它自己在 sheng 上的图标测试是 FAIL，崩溃原因写着"待分析"）。打算走 sheng 仓库自己的路：macOS 启动参数加 `exec-env=iconservicesagent:CI_ENABLE_MPS=0`（内核补丁 `profiles/os/macos-27.3-26C5035r/patches/xnu-12377/macos-droidvm-k27-parity.patch` 的 exec-env，上游已有），不碰插件；插件那份在 AdrenoMetal 仓库，进不了 sheng 的 PR。提交前要上机验证一次；外置构建盘 `/Volumes/UniXNUBuild` 现在没挂上。
  - 约 23:20 用户选"先验证再提交"（原话"1"）。
  - 已提交 `92e6e78`，推到 `zus12873/UniXNU-sheng` 的 `fix/macos-icon-agent-mps`（用户要求先以 draft 形式推送），基于 `upstream/main` `c2bcd72`；工作树 `../UniXNU-sheng-pr-mps`。提交说明写着 "Not run on hardware in this configuration."，没开 PR。上游和本地的 `porting-record.py check --base upstream/main` 都过。
    - `board.toml`：macOS `kernel_args` 末尾加 `exec-env=iconservicesagent:CI_ENABLE_MPS=0`，上面加说明；命令行 862 → 905 字节。
    - `porting.toml`：board.toml 归 configuration、usb、packaging 三个区，CI 要求三个区都改 findings（照 `c73f9c0` 的写法），再加 gpu 区一条。本地的和上游 main 的 `scripts/porting-record.py check --base upstream/main` 都过。
  - 试验镜像（等盘接上）：`payload.cd5-base.img` → `payload.cd5-s1-execenv.img`，参数是 `--set darwinboot-memory-size=0x1E0000000 --set darwinboot-memory-floor=0x920000000 --arg memory-outside=0 --arg enable-jobs=com.openssh.sshd --arg exec-env=iconservicesagent:CI_ENABLE_MPS=0`。
    - 不带 `ci-mps=0`，变量只能从 exec-env 来；去掉 `log-gpu=1`，否则约 1005 字节超限。
    - 用 `make-bootimg-v4.py <output>/boot/boot-bigwin.img … out/flash/boot-v4-payload.bigwin-cd5-s1-execenv.img`，再用 `bootimg-contents.py --payload` 核对。
  - 上机要看：
    - `kern.bootargs` 里有 exec-env、没有 ci-mps；
    - 用户那份 iconservicesagent 的环境（`ps eww`）里有 `CI_ENABLE_MPS=0`；
    - 日志里没有 `MPSImageUnaryKernel`；`launchctl print gui/501/com.apple.iconservices.iconservicesagent` 的崩溃次数不涨；
    - `tablet-icon-stress.js` 跑两轮没有失败、代理 PID 不变。
  - 过了再在 gpu 区加 device 证据（另起一个提交），再开 PR 到 `UniXNU/UniXNU-sheng`。PR 里写明：和 AdrenoMetal#37 不重复；插件里的 `ci-mps` 改动只在本地，不提交。
- **约 23:35 用户：克隆 `CrossDarwin/UniXNU_macOS`，定规则"每次新开发前先查别人的仓库"，再对比别人和我的进度**
  - `../UniXNU_macOS` 早就克隆过（干净），快进到 `test_27` `4a67177`。
  - 规则写在 `.claude/rules/check-other-repos-first.md`（`2a9badd`）。
  - 对比工具 `local-tools/compare-progress.py`：按内容比，不只按提交。上游是压扁合并的，所以看分支改过的文件在我这边是不是一样。
  - 拉到了：核心 `crossdarwin-macos/*`；sheng 的 `crossdarwin/*`、`rponeawa/*`；AdrenoMetal 的 `crossdarwin/*`；uefi-sheng 的 `crossdarwin/*`。
  - 和上游 main 比我基本是新的：核心落后 26 个（多是文档），sheng 落后 15 个（文档），AdrenoMetal 落后 3 个（文档）。领先的都在别人没合进上游的分支里。
  - **和我眼下的问题最相关的（都没验证）**：
    - 内存。
      - rponeawa `f4e0bc2`（11-15，`fix/sheng-startup-diagnostics`）：收编低位内存时把固件占着的 8 段（modem、TZ/XBL/QTEE、可信 UI 和 OEM 虚拟机、LLCC 附近）也挡掉。以前只有 GPU 池挡这些，内核收编只挡音频的 64 KiB；CPU 写进这些地方是同步外部异常。
      - 我本地 `board.toml` 还是旧的 `["0xd0000000:0x10000", "0x880000000:0x280000000"]`。日常镜像和第 1 步镜像都收编低位内存，"每次都在内存第一次用满后定住"和这个对得上。
      - **更正（11-16 00:30 合并时发现）**：rponeawa 自己在 17:42 加了这一条，18:13 就用 `ca1e6a5`（"revert: restore upstream sheng memory configuration and pool"，没写原因）撤掉了，他分支的最新提交里没有它。所以这条线索是"作者试过又撤了，原因不明"，整合分支里也没有。要试得另做，先弄清他为什么撤。
      - CrossDarwin `uefi-sheng` 的 `memory/abl-reservations-8g`（11-14）、`fix/memory-compatible-dxe`（11-16）：固件按 ABL 实际的保留区出内存表（ShengBootMemoryDxe），他们的是 8 GiB 机型；上机还没验，上一版显示 6.44 GB。sheng 侧对应 `crossdarwin/fix/compat-abl-memory` `c4d5a19`。
    - GPU 运行时：rponeawa 在 AdrenoMetal 上 11-15 有 8 个分支。
      - 接了 metal2vulkan development `400efe79` / `d9236a8a`，加了 A740 原生路径（并发分箱、快速边框色）。
      - 改了半精度 FMA 和除法；着色器预热收反射输入；有 GPU 验收探针。
      - "Vulkan 设备恢复后停止原生校准"，图形故障和自动恢复的测试。
      - 接着做卡死 A/B 之前先看这些。
    - 充电：rponeawa `fix/sheng-charge-*`，小米电量计和 MiPPS 充电器认证（HMAC、VDM，约 750 行），Linux 充电读取器。宿主机测过，上机待验；和"只充 2 A"有关。
  - 别的领先项：
    - CrossDarwin 的启动传输进了标准构建（UniXNU#263、sheng#103）；持久 Data 初始化（#102）。
    - 原生 APFS 容器镜像（`test_27`：容器扩到整盘，交换绑到 VM 卷）。
    - 内部 UFS 介质身份（#105/#266，上机 PASS）。
    - PSCI 关机和重启（#101，上机确认）。
    - 蓝牙发现和持久 HCI 日志（#104/#267，PASS）。
    - GitHub Actions 出整套测试包。
    - rponeawa 约 100 个诊断和实验室自动化提交：持久化启动检查点、panic 文本、固件看门狗交接、无人值守 GPU 实验。
  - 我领先的：
    - 12 GiB 机型的 7.5 GiB 窗口（别人 6.0 到 6.9 GB）；
    - 图标服务崩溃的真正原因和修法（#37 自己测还是 FAIL）；
    - GPU 复位后 WindowServer 自己重启；
    - `enable-jobs`（默认开 SSH）；
    - 指针漂移、合盖卡死这两个问题的原因。
- **约 23:40 用户："别人设备是8+256，然后把他们领先的内容整合到自己本地仓库先，然后同步到自己的仓库上"；23:40 "落文档，然后开始继续测试"**
  - 计划：`docs/superpowers/plans/2026-11-15-integrate-others.md`（`134756e`）。
  - 每个仓库开 `integrate/others-20261115`，原来的工作分支没动。
  - **AdrenoMetal** `acadac3`（从 `local/sheng-ci-mps` 开）：
    - 合了上游 main、rponeawa `fix/sync-development-d923`（新运行时，含他另外 5 个分支）、CrossDarwin #37（只有 README 冲突，两段都留）；
    - 本机的 `ci-mps=0` 和 `MadeBeforeRecovery` 兜底都还在；
    - 主机检查 `scripts/check-native-metal-frontend-host.py` 要 MoltenVK，本机没装，没跑。
  - **核心** `0e4503c`（从 `local/sheng-16g-macos` 开）：
    - 合了上游 main（账户输入的四处冲突取本地，本地是 #258 加一条修复，已包含上游那版）；
    - 合了 CrossDarwin `integration/desktop-repairs-20261115`（状态颜色取 CrossDarwin 较新的；AdrenoMetal 指针和 `components.toml` 指 `acadac3`）、`vm/signed-text-revalidation`；
    - QcomDwc3 改指 `42f7c2d`，和 sheng 一致。
    - `check-unixnu.py` PASS；`tests/macos` 7 个 OK；`tests/build` 关沙箱 6 个 OK（沙箱里开不了伪终端）。
  - **sheng** `31d0686`（从 `local/sheng-12g-large-window` 开），依次合了：
    - 上游 main；
    - CrossDarwin 的 `integration/desktop-repairs`、#103、#102、#105、#104（`diagnostics/persistent-desktop-hci`）；
    - rponeawa 的 `fix/sheng-startup-diagnostics`、`fix/sheng-charge-panic-recovery`（后者的内容已全在前者里）。
  - sheng 的冲突取舍：
    - `porting.toml` 用新工具 `local-tools/resolve-porting-conflicts.py` 逐键三方合并。
    - `board.toml` 内存全留本机：窗口 `0x240000000`、起点 `0x8C0000000`、bank 1 整段排除。
    - `size_mib` 200：超过合格外壳的 193 MiB，只能进我们的 v4 镜像。
    - #102 的"初始化 Data"菜单项没要：试验镜像不能带 `data-reset`。
    - 内核补丁列表两边都留：本地的改 `decmpfs.c`/`ubc_subr.c`，他的 5 个改别的文件。
  - sheng 的子模块：ShengUfs `2b6638b`、QcaBluetooth `e853395`（只在 CrossDarwin 的 fork 里，已取到本地）、Ath12kWifi 留 `39cc47b`。
  - sheng 的检查：
    - 上游和本地的 `porting-record.py check --base upstream/main` 都过；为此补了 network、input、arm64e-os、gpu 四个区的 findings。
    - battery、charger-auth、keyboard-cover/service、wn8030、boot-log、geni-i2c、gpu-trace 都 PASS。
    - `check-boot-watchdog-policy` 编不过：rponeawa 加的 `POLICY_CALL` 在被抽取的代码外面。补了测试桩（`31d0686`）后 PASS。
    - 另 5 个检查要 `kits/` 目录布局或 `UniXNU-sm8550-common`，本机没有，没跑。
  - **事故（已恢复）**：
    - 合 rponeawa 时，他提交进仓库的 `scripts/policies/macos-27.3-26C5035r/*/{trusted-key.bin,manifest.header.bin}` 覆盖了我们本地构建生成、被 git 忽略的同名文件。git 把被忽略的文件当可丢弃的，不报错。
    - 我们的钥匙哈希是 `74eace58…`，他的是 `896b3246…`。他的这 6 个文件没进合并提交。
    - 我们的 3 份 header 和钥匙用新工具 `local-tools/recover-root-policies.py`，从 `out/flash/boot-v4-payload.bigwin-cd5-s1.img` 的载荷里取回：钥匙在 `kernel.macho` 偏移 `0x1f1c84`，header 在 `kernel.macho.vroot`。三个窗口都核对过：钥匙和策略一致，header 和镜像一致。
    - 以后合别人的分支前先查"对方新增、本地被忽略"的文件。
  - 本地 `verification.json` 三处改动还是没提交（先 stash，合完放回）。
  - 11-16 00:05 推送做完：新建 fork `zus12873/AdrenoMetal`（子模块 remote `mine`）。
    - 核心、sheng、AdrenoMetal 各推了 `integrate/others-20261115` 和原来的工作分支，uefi-sheng 推了 `local/sheng-12g-memory-map`；远端哈希都核对过。
    - 不 force，不推 main，不建 PR。
- **约 00:10 用户："现在在fastboot状态"，00:12 "磁盘连上了"**（Task 5）
  - fastboot（00:10:37）：a 7、b 7，都是 unbootable no；电压 3875 mV。
  - 构建盘：`UniXNU-build.sparsebundle` 同时挂着两份设备（`disk6` 是上次拔盘留下的，`disk8` 是新的），卷都没挂上。两份都 detach，重新 attach 一次，`diskutil verifyVolume` 通过。日常文件 `33d294c8`、`8a36fe56`、`35f03ec4`、`boot.json` `aeaf38ac` 都在。
  - 00:13 第一次 `./unixnu build kernel payload` 53 秒就失败，日常文件没动。
    - 原因：核心 `scripts/build-adreno-metal-bridge.py` 还列着旧的桥接补丁（`0002-…`），而 rponeawa 的新运行时只有一个 `0044-unixnu-runtime-on-development-d9236a8a.patch`。
    - 配套的核心改动在 **rponeawa 自己的核心 fork**（`rponeawa/UniXNU`，之前对比时漏了）的 `fix/sync-metal-development-d923`，提交 `176b93e`：改补丁列表，metal2vulkan 从 `400efe79` 改到 `d9236a8a`。
  - 合了这个分支（`1ad16c2`；里面还有他的 bringup 和 Data 身份两条分支，共 38 个提交）。
    - 他"要求导出的工具链"那几条只改 `run-local-kernel.py`、`relocate-xnu-cache.py`，正常构建不走。
    - `drivers/Adreno740` 两边分叉：我们的 `462dd74`（大窗口要的页归属表修正），他的 `eb6d5af`（"Preserve pending jobs during context-switch recovery"）。在子模块里合成 `0848123`（干净），`components.toml` 也指过去。
    - macOS 内核补丁列表没要他的 `cshash-compressed-text-revalidation.patch`：和本机板级的 `sheng-text-fixup-verified-pagein.patch` 改的是 `decmpfs.c` 同一处，两个打不到一起；本机的那个在本机跑过。列表里写了注释。
    - `bootimg.py` 两边的功能都留：他的 ramdisk 分块压缩，加 CrossDarwin 的限额检查和"验证后再发布"。
    - 两个测试取他的版本，是我们的超集。
    - `check-unixnu.py` 和 `tests/` 都过。
  - 推送要补：`drivers/Adreno740` 的 `462dd74`、`0848123` 只在本地，用户没有 Adreno740 的 fork，GitHub 上的核心分支指向的提交别人取不到。
  - 00:19:57 第二次构建，00:21:06 失败，日常文件没动。
    - 这次卡在 rponeawa 的 `260cb6b`（"enumerate protected macOS library paths with root access"）：建 macOS GPU 插件前要列出 OS 镜像里所有 `.metallib`，给着色器预热用。
    - 不是 root 时用 `sudo -n` 跑 `scripts/list-metal-libraries.py`，没有免密 sudo 就失败。
    - 那个脚本只读：遍历只读挂载的 OS 镜像，打印路径；要 root 是因为镜像里有普通用户读不了的目录。
    - 我这边的命令没有终端，输不了密码，`sudo -v` 也带不过来（sudo 的凭据按终端记）。请用户在自己的终端里先 `sudo -v`、再跑构建。
  - 11-16 补推（用户："帮我将有贡献价值的都推到我线上库"）：核心两个分支钉住的 `drivers/DarwinBoot` `bdb6ff7` 和 `drivers/Adreno740` `462dd74` 之前只在本地。
    - 新建 fork `zus12873/DarwinBoot`、`zus12873/Adreno740`（`--default-branch-only`），子模块 remote 都叫 `mine`。
    - DarwinBoot 推了 `local/window-floor`（`3cd02b2`）和 `local/window-9g`（`bdb6ff7`），Adreno740 推了 `local/owned-map-below-window`（`462dd74`）。远端哈希核对一致。
    - 用 `.gitmodules` 里的上游地址按哈希取这两个提交，取得到（GitHub 的 fork 网络），所以从 `zus12873/UniXNU` 克隆后 `git submodule update` 能拉下来，不用改 `.gitmodules`。
    - 没推的：`verification.json` 三处（本机根卷钥匙的哈希）；sheng 的 stash `pre-cd2`（三处版本号已经在 `integrate/others-20261115` 里）；`data/`。Core Image 修复已按用户要求以 draft 形式推送，见"同一时间暂停的事"一条。
  - 还没做：构建和上机（Task 5，等构建盘，00:06 仍没挂上）；CrossDarwin 的 8 GiB ABL 内存表和 `test_27` 没合（见计划"这次不合的"）。
- 电：**macOS 开着、接充电头能充（11:30 量到电池 +2 A）；接 Mac 的口只进 0.45 A，电池每小时掉约 7%；停在 fastboot 基本不充**（见"11:24 上机 D2"一条；之前写的"macOS 下不充电"是错的，那只是接 Mac 的口）。关机插线充电在本机做不到（见"槽位 a 的重试次数"一条）。fastboot 里接 Mac 的口基本不涨：10:48:40 是 3746，10:54:36 和 10:55:19 都是 3761，其中一部分只是负载撤掉后的回升。fastboot 里接充电头能不能充还没量过。macOS 在 10:46 的照片里显示电量 23%。电压 09:46 是 3794，10:08 是 3776，10:13 是 3774（在 fastboot 里插着线五分钟没有涨），是有记录以来最低的。每次上机前读一次；电不够时一次上机中途断电会被当成"自己关机"，30 分钟的那一次要等充过电再做。
- 等用户的三样东西：
  1. 基线剩下的结果：不动它等几分钟之后指针还抖不抖；退出几个应用之后还抖不抖；`sysctl hw.memsize vm.pages vm.pages_excluded` 和活动监视器内存页的照片；重新填满后计时到 30 分钟，有没有变成定住或自己重启。
  2. 一个决定：内存占满时的"闪烁"还算不算这一步不过。设计写的是出现一次就不过，但日常系统自己在内存占满时就有，照原样判没法比。我的建议写在文末那一条里，用户还没答。
  3. 第 1 步可以开始的那句话。用的镜像是 `out/flash/boot-v4-payload.bigwin-s1.img`（sha256 `8bc7b897…`），做法在计划的 Task 6 Step 2。
- 整体审阅后那一轮修补的复审 10:16 回来了：要修的十一项都修到了，没有新的 Critical 或 Important；产物不受影响，五份载荷和五份镜像不用重做。剩下三条小问题和一条已知的缺口都没有再改，记在文末那一条的最后。
- 执行方式：Task 1 到 4 各交给一个子代理实现，再由另一个子代理审阅；Task 5、6 由主会话自己做。逐条记录在 `.superpowers/sdd/2026-11-15-memory-large-window/progress.md`（不入库，只在本机），新会话接手先读它，再对 `git log`。
- 用户确认涵盖的范围没有变：一处内核补丁加一次内核重编（已用掉）；加载器上限加一次固件重建（已用掉）；设计里点名的那几份镜像从内存启动；一次 30 分钟的基线。**不含刷 `boot_a`**，那要在第 3 步之后另外问。别的内核或驱动改动也都要另外问。

上一阶段（2026-11-15 08:30）：路线 A 的设计用户已确认（原话"开始实施验证"），计划写好，Task 1 做完，Task 2 到 6 还没做，没有构建，没有碰平板。

上一阶段（2026-11-15 01:45）：**用户选了内存路线 A：把内核窗口本身做大（先 7.5 GiB，再 9 GiB，最后加上低位内存区的收编，预计约 9.4 GiB），不再收编高位内存区。设计在 `docs/superpowers/specs/2026-11-15-memory-large-window-design.md`，等用户确认。确认之前不改内核、加载器、生成器和板级配置，不构建，不动平板。** 确认之后先写计划（放 `docs/superpowers/plans/`），再动手；第 1 步上机之前还要用户在日常系统里做一次 30 分钟的基线。要点见文末"路线 A：把窗口做大"一条。

- 下面 00:35 那一段里"下一步的方向"已被这次选择取代，其余（平板现在、主机现在）没有变；00:35 之后没有重新核对过平板。
- 这个会话只读了代码、写了设计和本文件，没有构建，没有碰平板。

上一阶段（2026-11-15 00:35，用户要求落交接）：**内存路线一上机做到一半（计划的 Task 6），没有可以刷进去日常用的结果。下一个会话先读文末"2026-11-15 00:35 收尾小结"，那里有全部读数、能确定的事、撤回的结论、平板和主机的现状、镜像清单和建议的下一步。**

- 一句话现状：窗口放在高位内存区顶部（`0x980000000` 起 6 GiB）、内核收编窗口下面的内存，这个做法在本机上不稳。不收编正常（6.0 GB）；只收编紧贴窗口的 512 MiB 跑过一次、十多分钟正常（6.5 GB）；收编 3 GiB 的同一份镜像四次上机，三次不闪、一次还没进系统就闪，不闪的那几次里也有"终端"未响应和应用卡顿加载；收编高位内存区最前面 512 MiB 的两份都在一两分钟内定住。原因都没找到。
- 平板现在：00:13 起在跑从内存启动的诊断镜像 `out/flash/boot-v4-payload.topwin-adopt3g-diag-report0.img`（收编 3 GiB、显示 6.0 GB）。`boot_a` 从 21:11 起没动过，里面是 `out/flash/boot-v4-flash.prev.img`（sha256 `40234c20…`），正常重启就回到日常系统。`slot-retry-count:a` 是 5。
- 主机现在：日常内核和载荷已放回，`../UniXNU-sheng/board.toml` 已还原，OS 镜像已卸载；工作区没有未提交的改动（`data/` 是用户放照片和短片的地方，不入库）。没有 push 过。
- 下一步的方向（要用户同意才动手的都标在小结里）：不再靠换镜像对比来猜原因，先拿到系统内部的证据；想先用上多一点内存，6.5 GB 那份是唯一干净跑过的。

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
  - 结果（用户 2026-11-14 约 21:15 报告）：进了系统，物理内存显示 9.5 GB（活动监视器，对照镜像的通过线是 9.07 GiB，收编生效了），**但是系统卡住了**。用户描述卡住的样子：**屏幕在闪烁，指针和导航栏都在抖动，没有自己恢复**。终端读数没拿到。
  - 读代码得到的推测（没有验证）：这像是画面在新旧两帧之间来回跳，问题在显示或 GPU 这一层，不是内核整个停住了。显示控制器那一路（`GopFramebuffer` 经 `native_ufs_dpu_map` 写 DPU 的页表）直接写物理地址，原来的窗口就在 4 GiB 以上，新地址也都在它能寻址的范围内，看不出问题。可疑的是 GPU 驱动的页归属表（`drivers/Adreno740/NativeAdrenoMemory.cpp:97-116`）：它按"收编的内存都在 4 GiB 以下"写，这在上游的布局里成立，在新布局里不成立。驱动放在收编内存里的缓冲区查不到，导入的内存就被当成独占，跳过冲突检查（`NativeAdrenoVm.cpp:296-311`、`:377`），同一页可能按两种缓存属性映射。关掉收编的那份镜像能分清是不是收编这一侧的问题。
  - 21:25:34 fastboot 读数：槽位 a，重试 7（强制关机后直接进的 fastboot，没有正常开机），电池 4196 mV。从内存启动 `out/flash/boot-v4-payload.topwin-k443-noadopt.img`（核对 sha256 `fa01e8c3…`）：`Booting OKAY`，45 秒内引导程序没有回来。结果等用户反馈。
  - 结果（用户约 21:30 报告）：进了系统，物理内存 6.0 GB，**没有闪烁**。所以窗口挪到顶部和固件内存表的改动都没有问题，闪烁出在收编这一侧。
  - 对照三次的结果：日常镜像收编 0.45 GiB，都在 4 GiB 以下，正常；k443 收编 3.5 GiB，都在 4 GiB 以上，闪烁、指针和导航栏抖动；关掉收编，正常。读代码核对过的、对收编的页是完整的：内核的 `pa_valid`、`pa_index`、页面缓存属性改变时对内核映射的更新（补丁里 `pai_to_pa` 两处）、GPU 驱动的缓存维护（`pmap_valid_address` 加 `phystokv`）、显示控制器的页表。唯一按地址区分、在新布局下会出错的，是 GPU 驱动的页归属表（`NativeAdrenoMemory.cpp` 的 `ownedIndex`：只给窗口里的页和 4 GiB 以下的页编号）。这是推测，还没验证。
  - 改它的代价：`Adreno740` 是编进内核的（板级配置内核 `archives` 里的 `component:Adreno740`），改了要 `./unixnu build kernel payload` 重新构建内核，超出了设计里"内核不动"的约束，要用户同意。打算的改法：页归属表里查不到的页当作"可能是驱动自己的"，这类导入走完整的冲突检查（正确但慢一些的那条路）；先写驱动的主机测试（`drivers/Adreno740/tests/test_system_memory.cpp` 那类）。新镜像仍然只从内存启动。改完还闪，说明推测不对，改动撤回。
  - 按计划 Task 6 Step 6 的"卡住"一行，下一份只关掉收编：`out/flash/boot-v4-payload.topwin-k443-noadopt.img`（210903040 字节，sha256 `fa01e8c3f698a170290ee6175668fb357194fdbd3f167e55ae03f88e9d6996c3`）。做法：复制 `<output>/payload/payload.topwin-k443.img` 为 `payload.topwin-k443-noadopt.img`（sha256 `ba5fabbe…`），只把 `unixnu.toml` 的参数行前面加上 `memory-outside=0`（894 字节，上限 1000），再用 `make-bootimg-v4.py` 和 `boot-topwin.img` 打包。卷里其他文件和 k443 那份逐个相同；内核签名脚本只拒绝 `validation_disables`、`serverperfmode`、`lcks` 三个参数，`memory-outside` 不影响签名，内核文件不用变。整份镜像和 k443 那份相比，镜像头和固件部分相同，只有 payload 卷里 1277 个字节不同。窗口仍在 `0x980004000`，内核不收编，预期 `hw.memsize` 约 5.9 GiB。
  - 两种结果的含义：这份也卡住，原因在窗口挪到顶部（`0xA00000000`–`0xB00000000` 第一次被使用）或固件内存表的改动（A 和这次都列入了那 443 MiB），和收编无关；这份不卡住，原因在收编（收编量是原来的 8 倍，或者 GPU 驱动那条已知限制）。
  - **21:50 复查（用户问"有没有更优解法"）：页归属表的推测解释不了闪烁，上面"打算的改法"先不做。**
    - 页归属表只用在两处：`NativeAdrenoVm.cpp:305` 的 `importsOnly` 和 `:327` 的 `exclusivePages`。两处都只决定"要不要做跨缓存类别的冲突检查"。页没有编号时检查变宽松，不会让映射失败，没找到通向画面出错的路径。
    - 内核驱动（`drivers/`、`../UniXNU-sheng/drivers`、`../UniXNU-sheng/package`）里和 `gPhysBase`、`gPhysSize` 作比较的只有三处：GPU 内存池（`NativeAdrenoPool.cpp:165`）、RamBlock（`NativeRamBlock.cpp:371`、`:705`，只管启动数据）、页归属表。
    - GPU 内存池在收编时是关的，有两道：内建参数 `gpu-pool=0`（`../UniXNU-sheng/package/BootWatchdogPolicy.c:60`）；`sheng_gpu_pool_probe` 在 `ml_outside_memory_pages` 非 0 时直接返回（`../UniXNU-sheng/package/GpuMemoryPool.cpp`）。所以没有"内核和 GPU 同时用一块内存"的情况。
    - 上游驱动提交 `14dc2d7`（11-11）已经把缓存维护、写合并属性、采样读取改成问内核这页是不是它管理的（`pmap_valid_address`），不再按地址比较。它只在收编 458 MiB 时上机验证过。上游三个分支之后没有相关修复。
    - 内存本身没问题：k443 收编的 `0x880000000`–`0x8A0000000` 和 `0x8C0000000`–`0x980000000`，在日常镜像里是窗口内的内存（窗口 `0x880000000`–`0xA00000000`），一直正常。差别只在这些页现在是收编来的。
    - 内核收编补丁同样可疑：补丁说明里上游的验证是 117264 页（458 MiB）、低端 bank、跨度约 2 GiB；这里是 917504 页，跨度正好 4 GiB（上限）。收编区虚拟地址的位置有 panic 守卫（`arm_vm_init.c`），这次没有 panic，9.5 GB 也显示出来了，所以不是地址放不下。
    - 物理内存读数是二进制单位：关掉收编 6.0（窗口 6 GiB），k443 是 6.0 + 3.5 = 9.5。
    - 闪烁那次没有留下证据：持久日志（`log=1`）只保留一次启动，已被关掉收编的那次覆盖；`data/mp4` 里没有闪烁的录屏。下次复现时请用户录一段。
    - 还不知道的：闪烁是登录后多久开始的；当时指针还能不能跟手（系统活着还是整个停住）。
  - **下一步：只换 payload 的内存启动，不动内核，不写 `boot_a`。**
    - 第一份（已做好，还没上机）：`out/flash/boot-v4-payload.topwin-adopt512m.img`，210903040 字节，sha256 `760f642243d98fe7a6bd760f296dc641f4ded2d8a984da794dca7aef0aeb234a`。只收编 `0x880000000`–`0x8A0000000`（131072 页，512 MiB），量和日常镜像收编的 458 MiB 相当，只有"地址在 4 GiB 以上"这一点不同。预期物理内存 6.5，`sudo dmesg | grep "memory outside"` 是 131072 页。
    - 做法：`<output>/payload/kernel.macho.topwin-k443.adt` 的 `darwinboot-memory-outside-kept` 第三对的长度从 `0x20000000` 改成 `0xe0000000`（挡掉 `0x8A0000000`–`0x980000000`，文件只差 1 个字节），存为 `kernel.macho.topwin-adopt512m.adt`；复制 `payload.topwin-k443.img` 为 `payload.topwin-adopt512m.img`（sha256 `fa877674…`），用 `mcopy` 换掉卷里的 `EFI/UniXNU/Payloads/kernel.macho.adt`；再用 `make-bootimg-v4.py` 和 `boot-topwin.img` 打包。核对：两个卷取出来 `diff -rq` 只有 `kernel.macho.adt` 不同；`adt-chosen.py` 最后一行是 `darwinboot-memory-outside-kept 48 0xd0000000+0x10000 0x80000000+0x800000000 0x8a0000000+0xe0000000`。
    - 闪烁：问题和地址有关。这时改页归属表才有依据，用精确改法：窗口下方的每一页都编号（表按 `gPhysSize/4096 + gPhysBase/4096` 位分配，约 1.25 MiB），不拖慢，不依赖新的内核符号。先写驱动主机测试，再重建内核，要用户同意。
    - 不闪烁（试用 15 到 20 分钟，开几个带动画的应用）：问题和收编量或跨度有关，接着二分（下一份收编 `0x900000000`–`0x980000000` 的 2 GiB，预期 8.0）。这条路可能不改内核就得到一个稳定的中间值。
    - 备选的第二份（还没做）：k443 的参数行加 `dpu-scanout=0`（上游默认值，现在的参数行是 2），看是不是显示直出这条路。不闪的话 9.5 GB 当场可用；代价按文档推断是画面要先拷到固件帧缓冲再显示，没有在代码里核对。
  - **21:53 只收编 512 MiB 的那份上机（用户说"同意重建，平板在fastboot"）**
    - 21:53:18 fastboot 读数：槽位 a，重试 7，`slot-successful:a: no`，电池 4152 mV。21:53:23 从内存启动 `out/flash/boot-v4-payload.topwin-adopt512m.img`（核对 sha256 `760f6422…`）：`Booting OKAY`，45 秒内引导程序没有回来。
    - 结果（用户约 21:56 报告，短片 `data/mp4/IMG_6396.MOV`，2.35 秒）：**尝试连接 Wi-Fi 时卡屏**。短片里活动监视器显示物理内存 6.50 GB（收编生效），已用 5.36 GB，联动内存 3.14 GB，压缩 589.5 MB，交换 0，App 内存 1.63 GB，缓存文件 1.14 GB。Wi-Fi 菜单开着，一个已知网络旁边是连接中的转圈，指针是彩球。
    - 画面是彻底定住，不是闪烁：从 0.5 秒起取连续 12 帧（60 帧每秒），屏幕内容逐帧相同，彩球不转。和 k443 那次"闪烁、指针和导航栏抖动"不是同一个样子。离启动约 2 分半。
    - 还不能下结论的原因：多了"连 Wi-Fi"这个变量。可能一：这个内核在新布局上连 Wi-Fi 本来就卡，和收编无关。可能二：收编的页一被用上就出事，连 Wi-Fi 或弹出带模糊效果的菜单只是触发点。
    - 读代码：Wi-Fi 端点的 DMA 不直接碰普通内存页。`../UniXNU-sheng/drivers/ShengUfs/NativeUfs.cpp:1276-1345`：`wifi>=2` 时给端点的 SMMU 上下文建一张一级页表，把 `0x10000000` 起的 128 MiB 映到一块开机时分配的连续内存（端点只能出 32 位地址），固件内存和收发环都在这块里。所以"Wi-Fi 的 DMA 落到收编页上"这条路看不出来。
    - 已问用户、还没回答：k443 闪烁那次是不是也在连 Wi-Fi 之后；关掉收编那次连过 Wi-Fi 没有；日常镜像平时能不能连上（菜单里它是"已知网络"，说明以前连上过）。
    - 下一份：对照，`out/flash/boot-v4-payload.topwin-k443-noadopt.img`（sha256 `fa01e8c3…`），进系统后同样打开 Wi-Fi 菜单连同一个已知网络，顺便记下活动监视器的内存读数作基线。不卡，问题在收编；也卡，和收编无关，之前的闪烁也要重新看。"连 Wi-Fi"如果能稳定复现，以后每份镜像几分钟就能分出结果。
  - **GPU 驱动页归属表的修正（用户同意重建后做的，和卡住有没有关系还不知道）**
    - 驱动子模块 `drivers/Adreno740` 本地分支 `local/owned-map-below-window`，提交 `462dd74`：`NativeAdrenoMemory.cpp` 的页归属表给内核范围下方的每一页都编号（原来只编到 4 GiB），表按 `gPhysSize/4096 + gPhysBase/4096` 位分配。新测试 `tests/test_owned_below_window.cpp`：内核范围放在 `0x980000000` 起 6 GiB，检查窗口里、4 GiB 以上收编区、4 GiB 以下、范围下方两端的缓冲区，以及释放。
    - 先看到失败再改：改之前新测试停在 `line 39: owned(0x8C0000000)…`，改之后通过；驱动原有的 `test_system_memory`、`test_memory` 仍通过（带 ASan 和 UBSan）。
    - 驱动仓库没有主机测试的运行脚本。本仓库加了 `local-tools/tests/test_adreno_owned_map.py`（提交 `81072de`），编译方法照 `../UniXNU-sheng/scripts/check-native-adreno-memory.py`：把源码包含的内核头文件都做成一行 `#include "XnuMemoryFixture.h"`。`python3 -I -B -m unittest discover -s local-tools/tests` 现在是 32 个通过。
  - **22:01 主机上的临时状态（内核重建期间；22:08 已全部还原，见下一条"22:08 重建完成"）**
    - 后台在跑 `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`（22:00 开始，以前用时 5 到十几分钟）。构建目录 `<output>/tree/drivers/Adreno740` 是指向本仓库子模块的符号链接，所以用的是带修正的工作区。
    - `../UniXNU-sheng/board.toml` 第 267 行临时加了 `"0x8A0000000:0x20000000"`（k443 的保留列表），**没有提交，构建完用 `git -C ../UniXNU-sheng checkout board.toml` 还原**。
    - 日常内核备份在 `<output>/kernel/kernel.macho.daily-33d294c8`（sha256 `33d294c83022a67b1ecfe4a8dd46564ca2b66169e11bc21c647e3981f2277b67`），`kernel.json`、`kernel.map.json` 同样带 `.daily-33d294c8` 后缀。日常 payload 备份是原来的 `<output>/payload/payload.daily-8a36fe56.img` 和 `.json`。**构建完 `<output>/kernel/kernel.macho` 和 `<output>/payload/payload.img` 就不是日常的了**，回到日常状态要把这几个备份复制回去。
    - OS 镜像只读挂在 scratchpad 的 `os-mount`（`/dev/disk9s1`），构建完要 `hdiutil detach`。
    - 构建完要做的：核对新 payload 和 k443 那份只有 `kernel.macho`、`kernel.macho.adt`（以及随内核变的文件）不同；复制成 `payload.topwin-k443-ownfix.img`；用改保留列表第三对的办法做 `payload.topwin-adopt512m-ownfix.img`；各打成 `out/flash/boot-v4-payload.…-ownfix.img`。只从内存启动。
  - **22:08 重建完成，带修正的 512 MiB 镜像已上机**
    - 用户 22:03 前后回答："6g的时候没有出现类似问题，只是时间久了，键盘壳会掉"。所以问题跟着"收编 4 GiB 以上的内存"走，512 MiB 就够触发；对照启动先不跑。没确认的一点：用户说的 6 GB 主要是旧布局的日常镜像，新布局关掉收编后有没有连过 Wi-Fi 不确定。带修正的镜像如果还卡，要补跑这次对照。
    - 构建 22:00 到 22:04:30，退出码 0。新内核 `<output>/kernel/kernel.macho.ownfix-311d37e3`（sha256 `311d37e3ec94237383f2a87315afc4b9a5f2e119fe29e2db27dae296714f45ac`），`libAdreno740.a` 22:03:39 重新生成（3340128 字节，原来 3340168）。
    - 新 payload 和 k443 那份逐个文件比较，不同的有五个：`kernel.macho`、`kernel.macho.adt`、`kernel.macho.crypto-hmac.json`、`kernel.macho.gpuaddon`、`kernel.macho.trustcache`。参数行（`unixnu.toml`）相同。
    - **多出来的一个变量**：`build kernel payload` 的 runtime 步骤会重新构建 Metal 插件（`scripts/build-boot-runtime.py` 的 `build_plugin`），`<output>/runtime/gpuaddon.bin` 22:02:51 重新生成。插件源码没变（`drivers/AdrenoMetal` 在 `73d582f`，工作区干净），但产物不能逐字节复现：addon 前 10.6 MB 逐块不同，信任缓存差 75 个字节。所以带修正的镜像和原来的相比，除了内核还换了一份同源重编的插件。如果带修正的镜像不卡，这一点要留意；还卡就无关。
    - 镜像（都只从内存启动）：`out/flash/boot-v4-payload.topwin-k443-ownfix.img`（sha256 `f11489e492148f353f8a98904cd287e1b696b1eacc7e3dbf80da0c7ba753ba45`，收编 3.5 GiB）；`out/flash/boot-v4-payload.topwin-adopt512m-ownfix.img`（sha256 `5aee5598b2e79c48d9e11808614f585fbd106cca6e27b2b08b6ee10e70f1cd3a`，收编 512 MiB，做法同前：新设备树保留列表第三对的长度改成 `0xe0000000`，和 k443-ownfix 的卷只差 `kernel.macho.adt`）。payload 在 `<output>/payload/payload.topwin-k443-ownfix.img`、`payload.topwin-adopt512m-ownfix.img`。
    - 主机已还原：`../UniXNU-sheng/board.toml` 已 `git checkout`（差异为空）；`<output>/kernel/kernel.macho` 回到 `33d294c8…`，`<output>/payload/payload.img` 回到 `8a36fe56…`；OS 镜像已卸载。`<output>/tree/build`、`<output>/runtime`、`<output>/payload/stage` 里是这次构建的中间产物。
    - 22:08:03 从内存启动 `out/flash/boot-v4-payload.topwin-adopt512m-ownfix.img`：fastboot 应答槽位 a、电池 4125 mV，`Booting OKAY`，45 秒内引导程序没有回来。请用户做同样的动作（打开 Wi-Fi 菜单连同一个已知网络），结果等用户反馈。
  - **22:09 带修正的那份也卡了（用户："进桌面就卡，放mp4下了"）**
    - 录像 `data/mp4/IMG_6398.MOV`（22:09:45，3.28 秒）：画面定在桌面，启动后约 1.5 分钟。活动监视器读数：物理内存 6.50 GB，已用 4.48 GB，缓存文件 2.03 GB，交换 0，App 内存 2.76 GB，联动内存 1.69 GB，压缩 0。恢复出来的窗口有地图（空白网格）、活动监视器、终端、系统设置。菜单栏右侧只画出了聚焦图标，时钟和 Wi-Fi 图标还没出来，说明是刚进桌面就定住。右上角的黄色方块在窗口后面，是桌面上的东西，不是移植层画的标记（`../UniXNU-sheng/package/BootProgress.c` 的彩色角标只画在诊断页的启动帧缓冲上）。
    - 结论：**GPU 驱动页归属表不是原因。** 那个修正对这个布局是对的，留在子模块分支上，但解决不了卡住。
    - 之后读过的代码，都没有找到按地址区别对待被收编页的地方：
      - 存储：`../UniXNU-sheng/drivers/ShengUfs/NativeUfs.cpp` 的直读（`hostDmaAddress`，1121 行起）用 `ml_vtophys`，上限 `gDmaLimit` 取自 SMMU 的地址宽度（1410 行起），和页在窗口内外无关。
      - 显示直接扫描输出：`drivers/GopFramebuffer/NativeLegacyDisplay.cpp` 的 `directSlot` 用 `getPhysicalSegment` 取 64 位物理地址，`native_ufs_dpu_map`（`NativeUfs.cpp:1664`）原样写进显示的页表，输出宽度 48 位。
      - RAM 盘和 GPU addon：`drivers/RamBlock/NativeRamBlock.cpp:371,705` 要求启动数据在内核自己的范围内，否则不启动；能进桌面说明它们在窗口里。
      - 内核收编补丁全文：`pa_valid`、`pa_index`、`pai_to_pa` 和页号基数树（`osfmk/vm/vm_resident.c` 的 `vm_pages_radix_*`，层数按 `vm_pages_first_pnum - pmap_first_pnum` 算，没有固定上限）都不依赖地址大小。
      - 固件内存表（`../uefi-sheng/Platforms/Xiaomi/shengPkg/Library/MemoryMapLib/MemoryMapLib.c`）：固件自己的区域都在低内存条（`0xA7000000` 一带），内存条 1 列出的全是普通内存。
    - **之前说得太满的一点**：我说过"被收编的页在日常布局里是窗口页，用着没事"。日常布局里内核映像和启动数据（RAM 盘等）就装在窗口开头，也就是 `0x880000000` 起的这一段，所以这 512 MiB 在日常布局里有相当一部分是静态内容，没有当普通页用过。"这一段物理内存当普通页用有问题"还没有排除。
    - **画面定住也可能是内核 panic**，现在分不出来：启动参数 `debug=0x14e` 会把 panic 信息画到启动帧缓冲上，但 `dpu-scanout=2` 时面板不扫那块内存，看不到。
    - 现在的三个假设：H1，`0x880000000`–`0x8A0000000` 这段内存当普通页用有问题；H2，收编机制在这个布局下有还没找到的错；H3，新布局下连 Wi-Fi 会卡，和收编无关。
    - **下一份（已做好，只从内存启动）**：`out/flash/boot-v4-payload.topwin-adopt512m-hi-ownfix.img`（sha256 `4c833b1adb26345d6f0d1bcd3a6e56ec307b8a41576cda610f81308ca8c3fa39`）。内核带修正，收编量不变（512 MiB），换成紧贴窗口下方的 `0x960000000`–`0x980000000`（日常布局里是普通窗口页）。做法：`kernel.macho.topwin-adopt512m-ownfix.adt` 保留列表第三对的起点 `0x8a0000000` 改成 `0x880000000`（1 个字节），长度 `0xe0000000` 不变，即保留 `0x880000000`–`0x960000000`。预期收编 131072 页，读数 6.50 GB。payload 是 `<output>/payload/payload.topwin-adopt512m-hi-ownfix.img`，设备树是同目录的 `kernel.macho.topwin-adopt512m-hi-ownfix.adt`（读回卷里的文件核对过 sha256 一致）。
      - 不卡（并且连上 Wi-Fi 用 5 分钟以上）：H1 成立，H3 排除。下一步收编 `0x8C0000000`–`0x980000000`（3 GiB，预期 9.0 GB），`0x880000000`–`0x8C0000000` 留着不用。
      - 还卡：H1 排除。接着跑两份：关掉收编连 Wi-Fi（`out/flash/boot-v4-payload.topwin-k443-noadopt.img`，分 H3）；收编不变、`dpu-scanout=0`（面板扫启动帧缓冲，panic 信息能看到，也能分出是不是直接扫描输出这条路的问题；这份还没做）。
    - 还没做、之后可能需要的：把 Linux 日志读取器打成这台机器接受的 v4 镜像，读 `log=1` 的持久日志。日志只留一次启动，下一次启动 macOS 就会盖掉 22:08 那次的。
    - **22:25:56 这份已上机**：平板当时已经在 fastboot（用 `fastboot getvar current-slot` 限时 6 秒探到的）。镜像 sha256 核对一致；槽位 a，`slot-retry-count:a` 是 5（21:53 是 7，两次强制重进 fastboot 各用掉一次），`slot-unbootable:a` 为 no，电池 4113 mV。`Booting OKAY`，45 秒内引导程序没有回来。22:08 那次的持久日志从这一刻起被盖掉了。
      - 重试次数降到 2 或以下时，按用户以前的许可执行 `fastboot set_active a` 补满（绝不切到 b）。
    - **22:33 中间读数（用户发来照片，这份还在跑）**：启动后约 7.5 分钟没有卡，比前两次卡住的时间（1.5 和 2.5 分钟）都长。活动监视器：物理内存 6.50 GB（符合预期），已用 5.46 GB，缓存文件 1.05 GB，交换 0。Wi-Fi 连没连上照片里看不到，还要问。**这只是中间读数，H1 还没有定论**：要等连上 Wi-Fi 再用 5 分钟以上。
    - **用户同时报告的另一件事（22:33，还没查）**：在系统设置 → 通用 → 共享里打开"远程登录"时，弹出的管理员授权框不接受登录时用的密码（用户原话："这个密码不是登录的时候的密码"）。已知的：系统里只有制作 seed 时 `--user` 加的那个账户，`scripts/make-macos-data-seed.py` 的 `add_user` 把它写进了 `admin` 和 `staff` 两个组（`users` 和 `groupmembers` 都写了），密码只存了 `SALTED-SHA512-PBKDF2`，所以按设计授权框要的就是登录密码。为什么不接受不知道；上游文档没有提到管理员授权。请用户在终端里试 `dscl . -authonly $USER`（直接走目录服务）和 `sudo -v`（走 PAM）来分是密码校验的问题还是授权框这条路的问题。远程登录如果能开，之后卡住时可以从 Mac 上连进去看日志。
    - **22:35 前后的结果：换了收编位置就不卡了**（用户："现在不卡了，但是我尝试打开terminal后，我的键盘壳掉了之后没再连上，触屏还是能用的"）
      - 这份和 22:08 卡住的那份只差一个字节（收编 `0x960000000`–`0x980000000` 而不是 `0x880000000`–`0x8A0000000`），内核、收编量、参数都一样。所以卡住跟着被收编的是哪一段走。H2 里"收编机制整体有错"这一半排除。
      - 还没分清的：是这段物理内存本身当普通页用有问题，还是内核或驱动里有依赖收编范围位置的错（比如范围离内核自己的范围 3.5 GiB 远和紧贴着的区别）。两者下一步相同。
      - H3（连 Wi-Fi 会卡）基本排除，但这次启动 Wi-Fi 有没有连上还没向用户确认。
      - 键盘保护套掉线是另一个问题，旧镜像上也有，记在"键盘和触控板失效"一节。
    - **再下一份（已做好，只从内存启动）**：`out/flash/boot-v4-payload.topwin-adopt3g-ownfix.img`（sha256 `a1dc907c6ee1980c53e151d15e6cc0cf54086d00825cf0dabedfefe3636fcdef`）。保留列表第三对改成 `0x880000000` 起、长度 `0x40000000`（在上一份的设备树上再改 1 个字节），即内存条 1 的第一个 GiB（`0x880000000`–`0x8C0000000`，里面本来就有引导程序留出的两个洞）整个不用，收编 `0x8C0000000`–`0x980000000`。预期收编 786432 页，读数 9.00 GB。payload 是 `<output>/payload/payload.topwin-adopt3g-ownfix.img`，设备树是同目录的 `kernel.macho.topwin-adopt3g-ownfix.adt`（读回核对过）。
      - 不卡、不闪，跑满 30 分钟：路线一按 9.0 GB 收尾（原设计预期 9.9 GB，少掉的是这第一个 GiB）。然后才是 `boot-v4-flash` 版本和问用户要不要刷 `boot_a`。板级配置的保留列表要相应加上 `"0x880000000:0x40000000"`，设计文档和计划的结果栏要写明这一点和原因未明。
      - 闪或卡（像 21:11 那份 3.5 GiB 的）：说明还有和收编量有关的第二个问题，回到 512 MiB 往上二分。
      - 想把第一个 GiB 里能用的部分要回来（最多约 0.9 GiB），要在 `0x880000000`–`0x8A0000000` 里二分找出问题页，每一步一次上机，放到路线一收尾之后。
    - **22:39:55 这份已上机**：平板已在 fastboot（限时 5 秒探到）。镜像 sha256 核对一致；槽位 a，`slot-retry-count:a` 还是 5，`slot-unbootable:a` 为 no，电池 4084 mV。`Booting OKAY`，45 秒内引导程序没有回来。
      - 更正上面 22:25:56 那条的说法：重试次数这次没有变（5 → 5），所以"每次强制重进 fastboot 用掉一次"不成立。21:53 到 22:25 之间少掉的两次是怎么用掉的不知道（可能是卡住后重启时先从 `boot_a` 起了一下）。
    - **22:45 前后的结果：9.0 GB，闪烁、指针抖动、卡住**（用户："9GB，那份 9.5 GB 的一样闪烁、指针抖动，卡住，没有重建镜像来进行修复么"）
      - 读数符合预期（收编 786432 页）。症状和 21:11 的 k443（9.5 GB）一样。这次没有录像。
      - 所以有两个互相独立的问题：
        - ① 收编 `0x880000000`–`0x8A0000000`：一两分钟内画面定住（21:53、22:08 两次）。
        - ② 收编量大：闪烁、指针和菜单栏抖动、卡住。3 GiB（不含①那段）和 3.5 GiB（含）都这样；紧贴窗口的 512 MiB 不这样（22:25 那份跑了十分钟以上）。
      - 对②我现在的猜测（没有验证）：被收编的页是启动早期最后放进空闲队列的，会最先被用掉。只收编 512 MiB 时它们在进桌面之前就被内核和早期进程占完了；收编 3 GiB 时还剩很多，于是窗口服务和 GPU 的缓冲区落在被收编的页上。也就是"被收编的页拿去做 GPU 或显示缓冲区会出问题"。日常镜像收编的 0.45 GiB 同理早早用完，所以上游没碰到。另一个没排除的可能是总内存超过某个数（比如 8 GiB）后用户态行为变了。
      - 22:45 之后又读过、没有发现问题的代码：`drivers/Adreno740/NativeAdrenoCpu.cpp` 的缓存同步（`NativeAdrenoMaintainPhysicalPages`，对内核管理的页经 `phystokv` 的别名做，被收编的页 `pmap_valid_address` 为真）、`NativeAdrenoSetPagesCacheMode`、`NativeAdrenoVm.cpp` 的 `kernelDram` 四处用法。设备包里没有按内存总量走不同分支的代码。
      - 用户问的"有没有重建镜像来修复"：没有。22:25、22:39 两份和之前的都只差设备树里一个字节，是对照，不是修复；到现在唯一改过代码的是 GPU 驱动页归属表，已证明不是原因。原因没找到之前没有东西可修。
    - **下一份（已做好，只从内存启动）**：`out/flash/boot-v4-payload.topwin-adopt3g-ownfix-scan0.img`（sha256 `e6427c375a413e667a27560c44fe3f6d37cc9e66886f3bfd9da94a608fd19bbd`）。和 9.0 GB 那份只差启动参数一个字节：`dpu-scanout=2` 改成 `dpu-scanout=0`（上游默认值；面板改回扫固件帧缓冲 `0xb8000000`，每帧由 GPU 转写进去，显示不再直接读合成器的缓冲区）。payload 是 `<output>/payload/payload.topwin-adopt3g-ownfix-scan0.img`，卷里的 `unixnu.toml` 读回核对过。
      - 不闪：②出在显示直接扫描输出读被收编的页这条路上；同时 9.0 GB 加 `dpu-scanout=0` 就是一个能用的配置（代价是每帧多一次转写）。
      - 还闪：②出在 GPU 渲染这一侧（导入、映射被收编的页），接着查 `NativeAdrenoVm.cpp` 的导入路径。
      - 这个模式下内核 panic 的画面能看到（panic 画在固件帧缓冲上），卡住时请用户拍屏幕。
      - **22:49:32 已上机**（用户："平板已进fastboot"）：镜像 sha256 核对一致；槽位 a，`slot-retry-count:a` 5，`slot-unbootable:a` 为 no，电池 4058 mV。`Booting OKAY`，45 秒内引导程序没有回来。
    - **22:50 这份的结果：刚进桌面黑一下，然后画面定住**（用户："刚进桌面直接黑屏了下之后，画面卡死了"）。没有看到 panic 文字，没有录像。
      - 所以②不是显示直接扫描输出这条路特有的：两种显示方式下图形都坏，只是样子不同。
      - 这之后查过并排除的一点：内存压缩器的地址空间。`osfmk/vm/vm_compressor.c` 的 `vm_compressor_set_size` 在 KMEM 阶段按当时的 `max_mem`（窗口的 6 GiB）算好并预留，macOS 上 `vm_compressor_init` 不会重算（只有 `CONFIG_JETSAM` 加应用交换时才重算），所以收编后不会超出预留。顺带解释了以前记的"窗口每加 1 GiB 要多占两份内核地址空间"：物理映射一份，压缩器一份。
      - 新看到的一点：Metal 插件按上报的内存总量给预算。`drivers/AdrenoMetal/NativeBridgeMetalFrontend.mm:4394` 的 `recommendedMaxWorkingSetSize` 是 `min(hw.memsize/4, 2 GiB)`，`IOGPUMetalDeviceShim.h:42` 的 `workingSetSize` 是物理内存的三分之二，`sharedMemorySize` 是全部物理内存。上游和这台机器以前都没有在上报 8 GB 以上时跑过。
      - 现在对②有两个假设，靠读代码分不出来：
        - H-GPU：被收编的页一旦被 GPU 或窗口服务拿去用就出问题（只收编 512 MiB 时这些页在进桌面前已被内核占完，所以碰不到）。但读到的驱动和内核代码都没有按地址区别对待被收编的页。
        - H-SIZE：上报的内存总量变大（比如过了 8 GiB）之后，用户态图形栈的行为变了，这个移植的 GPU 驱动接不住。
      - 22:52 做过一份加了 `boot-progress=2 boot-diag-resume=10` 的镜像，**没有用，已删除**：macOS 内核里根本没有编进诊断页（内核文件里搜不到 `boot-progress` 字样）。`CONFIG_XNU_BOOT_PROGRESS=y` 只在 `../UniXNU-sheng/configs/sheng_defconfig` 里，`sheng_macos_defconfig` 没有。
    - **建议的下一步（要重建内核，等用户同意；都只从内存启动，不是修复）**：
      - 在 `sheng_macos_defconfig` 里临时加 `CONFIG_XNU_BOOT_PROGRESS=y`，让诊断页可用（页面内容见 `../UniXNU-sheng/package/BootProgress.c` 第 400 行起：panic 日志开头、显示的 SWAP 和 COPY 计数、内存、GPU 状态行）。配上 `dpu-scanout=0 boot-progress=2 boot-diag-resume=10`，画面停 10 秒后诊断页接管面板，请用户拍照。macOS 配置下这个层能不能编过没试过。
      - 在收编补丁的 `ml_adopt_outside_memory` 里加一个启动参数（默认行为不变），值为 0 时照样收编，但不增加 `max_mem`、`sane_size` 等上报的总量。带这个参数收编 3 GiB：不坏就是 H-SIZE，还坏就是 H-GPU。
      - 不重建内核的替代办法：在 8 GiB 两侧各收编一次（比如读数 7.9 和 8.1 GB），看界限是不是正好在 8 GiB。要两次上机，结论没有上面的开关干净。
    - **23:04 诊断内核（用户 23:02 同意："同意重建诊断内核，平板在fastboot"）**
      - 改动一处：`profiles/os/macos-27.3-26C5035r/patches/xnu-12377/window-outside-memory-adoption.patch` 的 `ml_adopt_outside_memory` 里加启动参数 `memory-outside-report=<MiB>`。不带这个参数时行为和原来一样；带上时页照样全部收编，但 `max_mem`、`max_mem_actual`、`mem_actual`、`sane_size`、`machine_info.max_mem` 最多只增加这么多 MiB（0 就是完全不增加，系统显示 6 GB）。补丁的行数头从 `+2278,94` 改成 `+2278,99`。验证：在 scratchpad 里克隆内核源码，按 `<output>/xnu-patches.list` 的顺序 147 个补丁全部打上（`applied 147 of 147`）。
      - **屏幕诊断页这次没有加**：它不是一个配置开关就能打开的。`CONFIG_XNU_BOOT_PROGRESS` 之外还要在 `board.toml` 的内核归档列表里加 `build-boot-progress.py`（基础配置和 iPadOS 26 有，iPadOS 27 和 macOS 的列表里上游已经去掉），这个脚本还会再编一份 `BootWatchdogPolicy.c`，并且依赖旧构建流程留下的编译记录（`build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/…/startup.o.json`）。在 macOS 配置下能不能编过、会不会重复定义，都要另花时间试，所以先不做。
      - **主机上的临时状态（构建完要还原）**：
        - `../UniXNU-sheng/board.toml` 第 267 行临时加了第三对 `"0x880000000:0x40000000"`（收编 3 GiB 的保留列表），没有提交，构建完用 `git -C ../UniXNU-sheng checkout board.toml` 还原。
        - OS 镜像只读挂在 scratchpad 的 `os-mount`（`/dev/disk9s1`），构建完要 `hdiutil detach`。
        - 构建会覆盖 `<output>/kernel/kernel.macho` 和 `<output>/payload/payload.img`。日常的备份还在：`<output>/kernel/kernel.macho.daily-33d294c8`（以及同后缀的 `kernel.json`、`kernel.map.json`）和 `<output>/payload/payload.daily-8a36fe56.img`，23:03 核对过 sha256 和当时的现用文件一致。构建完把新内核另存为 `kernel.macho.diag-<sha 前 8 位>`，再把日常的复制回去。
        - 补丁改了内容，构建会重新克隆内核源码并全量重编，比上次的 4.5 分钟长。
      - 构建完要做的两份镜像（都只从内存启动）：收编 3 GiB、`dpu-scanout=2`、`memory-outside-report=0`（预期显示 6.0 GB；不闪就是总量引起的，还闪就是被收编的页引起的）；如果不闪，再用同一个内核试 `memory-outside-report=1900`（显示约 7.9 GB）和更大的值找界限。
    - **23:07 诊断内核编好，23:11 第一份诊断镜像上机**
      - 构建 23:04 开始、23:07 结束，退出码 0。新内核 `<output>/kernel/kernel.macho.diag-980a9895`（sha256 `980a98953b8a621527d8f1d8f2ad047e851dd6103837fc8bba588419d6c4f624`，同后缀还有 `kernel.json`、`kernel.map.json`）；内核里能搜到字符串 `memory-outside-report`。
      - 新载荷和 22:39 那份（`payload.topwin-adopt3g-ownfix.img`）逐个文件比过 sha256：`kernel.macho.vroot`、`scratch-data.img`、`unixnu.toml` 相同；`kernel.macho`、`kernel.macho.crypto-hmac.json`、`kernel.macho.gpuaddon`、`kernel.macho.trustcache` 不同（内核变了，GPU 附加件每次构建都会重编且不可复现）；设备树只有 `random-seed` 那 256 字节不同，保留列表读出来是 `0xd0000000:0x10000`、`0x80000000:0x800000000`、`0x880000000:0x40000000`（收编 `0x8C0000000`–`0x980000000`）。
      - 两份镜像，都用 `<output>/boot/boot-topwin.img` 打成 v4，只从内存启动：
        - `out/flash/boot-v4-payload.topwin-adopt3g-diag-report0.img`，sha256 `414f2ddb32ed3b1c5e6ebc93a5afde6e653c3ec5743887136466f6aa535d4f21`：启动参数在原样后面加 `memory-outside-report=0`（`dpu-scanout=2` 不变）。载荷 `<output>/payload/payload.topwin-adopt3g-diag-report0.img`。
        - `out/flash/boot-v4-payload.topwin-adopt3g-diag.img`，sha256 `e63b1849850aa72dacf78642d6a305b60040237934b70af0868c10800e1f1ac7`：同一个内核、不带这个参数，是对照（预期和 22:39 那份一样显示 9.0 GB 并且闪）。载荷 `<output>/payload/payload.topwin-adopt3g-diag.img`。
      - 主机已还原（23:09）：`<output>/kernel/kernel.macho` 回到 `33d294c8…`，`<output>/payload/payload.img` 回到 `8a36fe56…`，`../UniXNU-sheng/board.toml` 已 `git checkout`（第 267 行回到两对），OS 镜像已卸载。补丁的改动还留在工作区、没有提交，等结果出来再决定提交还是撤掉。
      - 23:10 上机前读数：槽 a，`slot-retry-count:a` 5，`slot-unbootable:a` no，电池 4044 mV。23:11 `python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.topwin-adopt3g-diag-report0.img`，bootloader 45 秒没回来，镜像在运行。
      - 怎么读结果：活动监视器的物理内存应当是 6.0 GB（如果显示 9.0 GB，说明参数没生效，这次不算数）。
        - 显示 6.0 GB 且不闪不卡：②跟上报的内存总量有关。先跑对照镜像确认它还会闪（排除"重编一次就好了"），再用 report0 这份的载荷只改参数值（例如 1024、1900、2100、3072，分别显示约 7.0、7.9、8.1、9.0 GB）找界限，不用重编内核。
        - 显示 6.0 GB 但仍然闪或卡：②跟被收编的页本身有关，下一步在 GPU 导入路径上加记录。
    - **23:41 用户："重试，闲置太久键盘掉了"；23:42 同一份镜像重新上机**
      - 23:11 那次用户没有报物理内存读数，也没有报闪不闪、卡不卡，只说放着太久键盘壳掉了。所以那次对②没有读数。能确定的只有：从 23:11 到用户让它回 fastboot（23:41 之前）这段时间里，用户没有报卡死。键盘壳闲置后掉线是日常 6 GB 镜像上就有的老问题（见"开机待机久了，键盘和触控板失效"一节），不算这份镜像的新现象。
      - 23:41 读数：槽 a，`slot-retry-count:a` 5，`slot-unbootable:a` no，电池 4004 mV；镜像 sha256 核对为 `414f2ddb…`。23:42 `boot-sheng.py` 启动，bootloader 45 秒没回来，镜像在运行。
    - **23:45 前后的结果（23:42 那次，`memory-outside-report=0`）：用户"已进系统，物理内存6.0g，没有闪烁，终端 not responding之后恢复，又not responding"**
      - 读法：参数生效（显示 6.0 GB）。同样收编 `0x8C0000000`–`0x980000000` 这 3 GiB，22:39 那份照实上报 9.0 GB，一进桌面就闪；这份不上报，不闪。这和 H-SIZE（上报的内存总量变大引起）相符。**还不能算证实**：两份之间除了参数，内核也重编过一次、GPU 附加件也重编过（不可复现）；要有一次"新内核、总量变大、又闪了"才算排除掉重编的影响。
      - "终端"时而未响应是新报的现象，原因不知道，也不知道日常 6 GB 镜像上有没有（已问用户）。之前两次键盘壳掉线都发生在刚打开"终端"之后（见键盘那一节），这三件事有没有关系也不知道。可能的方向只有猜测，没有证据：和收编的页有关（H-GPU 的轻一些的表现）；和总量与实际页数不一致有关（这是这份诊断镜像独有的状态）；或者和内存无关、日常就有。
      - 驱动里按内存总量取值的地方只有 Metal 插件三处（`drivers/AdrenoMetal/NativeBridgeMetalFrontend.mm:4394` `recommendedMaxWorkingSetSize` = `min(hw.memsize/4, 2 GiB)`，`:4344` `sharedMemorySize` = 物理内存，`IOGPUMetalDeviceShim.h:42` `workingSetSize` = 物理内存的 2/3）。其中第一处在 8 GiB 处封顶到 2 GiB（`0x80000000`，有符号 32 位放不下）：6.5 GB 时是 1.625 GiB，9.0 和 9.5 GB 时都是 2 GiB。这只是一个候选，系统自带的窗口服务器、图形框架也会按总量取值，那些看不到源码。所以下面两份镜像选在 8 GiB 两侧。
      - 23:46 做好两份只改参数值的镜像（载荷从 report0 那份复制，只换 `unixnu.toml`，读回核对过）：
        - `out/flash/boot-v4-payload.topwin-adopt3g-diag-report2100.img`，sha256 `789a2fd8f1e014f9107d2ba4a6ba3087a78d77c617e6d703b792b2754496e6da`：`memory-outside-report=2100`，应显示约 8.05 GB。
        - `out/flash/boot-v4-payload.topwin-adopt3g-diag-report1900.img`，sha256 `589d4df60179038ec41bb18a427ed7949c6ecf2f2dc1570b02cec7d0125c20df`：`memory-outside-report=1900`，应显示约 7.86 GB。
      - 顺序和读法：先跑 2100。闪了 → 新内核在总量大时照样闪（对照成立），分界在 8.05 GB 以下，再跑 1900：不闪就把分界夹在 7.86–8.05 GB 之间，指向 8 GiB 封顶那一类取值；1900 也闪就继续往下二分（1024 等）。2100 不闪 → 分界在 8.05–9.0 GB 之间，或者是重编改变了行为，这时跑不带参数的对照镜像 `…-diag.img`（`e63b1849…`）来分清。
    - **23:49 用户补充（report0 那次）："其他功能没受影响，有几个已打开的app会卡顿加载"；23:51 `report2100` 上机**
      - 所以 report0 那次不只是"终端"：几个已经打开的应用也会卡一下再加载出来，其他功能正常，没有闪烁。日常 6 GB 镜像上有没有同样的卡顿，用户还没答。
      - 23:49 读数：槽 a，`slot-retry-count:a` 5，`slot-unbootable:a` no，电池 3981 mV（今晚一路在降：22:49 4058、23:10 4044、23:41 4004）；镜像 sha256 核对为 `789a2fd8…`。23:51 `boot-sheng.py` 启动，bootloader 45 秒没回来，镜像在运行。
    - **23:55 前后的结果（23:51 那次，`memory-outside-report=2100`）：用户"已进系统，物理内存8.05g，闪烁了"**
      - 这是一次干净的单变量对比：`report0` 和 `report2100` 两份镜像的内核、设备树、GPU 附加件、信任缓存全都相同（载荷是复制出来的，只换了 `unixnu.toml` 里的一个参数值），收编的页也相同。0 不闪，2100 闪。所以**②是上报的内存总量引起的（H-SIZE），不是被收编的页被图形用到引起的（H-GPU）**；"重编一次就好了"也排除了，对照镜像不用跑了。
      - 还不知道的：分界在哪（已知 6.5 GB 正常、8.05 GB 闪）；是哪个东西按总量取值。候选之一是 Metal 插件的 `recommendedMaxWorkingSetSize`（8 GiB 起封顶到 2 GiB = `0x80000000`），没有证据，只是它的取值正好在这个区间里变。
      - 顺带核对过一处：补丁给被收编内存建的内核映射用的是普通可缓存属性（`ARM_PTE_ATTRINDX(CACHE_ATTRINDX_DEFAULT)`，`window-outside-memory-adoption.patch` 第 148–149 行），不是设备内存那种不走缓存的映射，所以"被收编的页访问慢"这个猜测不成立。
      - 23:56 起后台等待：平板出现在 fastboot 后读槽、`slot-retry-count:a`、`slot-unbootable:a`、电池，槽是 a 且次数不少于 3 才 `boot-sheng.py out/flash/boot-v4-payload.topwin-adopt3g-diag-report1900.img`（sha256 已核对 `589d4df6…`）。
      - 1900 的读法：不闪 → 分界在 7.86–8.05 GB 之间，指向 8 GiB 这一类取值；可以做的直接验证是把插件的封顶改到 2 GiB 以下、照实上报 9 GB 再看（要重编，要用户同意）。闪 → 继续往下二分（1024 → 约 7.0 GB）。
    - **23:58 用户的补充和猜测；空闲页队列的顺序（改正之前的说法）**
      - 用户："会不会是内存分区页不同造成的内存同步问题，然后造成的卡顿，我看这次，系统加载app，内存用到5g之后就开始系统闪烁了"。也就是 `report2100` 那次不是一进桌面就闪，而是已用内存到 5 GB 左右才开始。
      - 源码事实（`<output>/tree/.cache/xnu-work/osfmk/vm/vm_resident.c`）：普通页进空闲队列是排到队尾（`vm_page_free_queue_enter` 里 `enter_first = false`，第 1014、1047–1054 行），取页从队头取（`vm_page_free_queue_grab`，第 1719 行 `vm_page_queue_remove_first`）。所以是先进先出：窗口里的页在启动早期先入队、先被发出去；被收编的页在 `ml_adopt_outside_memory` 里后入队（每段从低地址往高地址），排在后面；运行中释放的页又排到它们后面。**之前文档和记忆里写的"空闲队列是后进先出，512 MiB 在进桌面前就用掉了"是错的，以这里为准。**
      - 推论：被收编的页大约在窗口初始空闲的 5 GiB 多全部发出去一遍之后才第一次被用到，也就是"已用 + 文件缓存"接近窗口容量的时候。这和三件事的时间对得上：`report2100` 用到 5 GB 开始闪；9.0 GB 那两份在进桌面前后出事；①那两份在进桌面一两分钟内定住。22:25 那份（只收编紧贴窗口的 512 MiB）照片里已用 5.46 GB，没出事。
      - 因此 23:57 的结论要收回：`report0` 和 `report2100` 的对比只有在两次都把内存用到同样多时才是单变量，`report0` 那次已用内存到了多少没有记录。`report0` 那次的"终端未响应、应用卡顿加载"也可能就是被收编的页开始被用到时的表现。
      - 关于"内存分区的页不同"：这段物理内存本身没问题（日常镜像的窗口是 `0x880000000`–`0xA00000000`，`0x8C0000000`–`0x980000000` 天天当普通内存用）；内核页大小都是 4 KiB；补丁给它们建的内核映射是普通可缓存属性。所以如果是页的问题，出在"软件怎么对待窗口外面的页"，不是内存条。哪段代码有这种区别对待，还没找到（GPU 的自有页位图已经排除）。上游把低位内存区（4 GiB 以下）收编 458 MiB 在真机上是正常的，本机日常也显示过 6.38 GB；窗口下面、4 GiB 以上的页被收编，上游没有人跑过。
    - **00:00 上游的做法（用户："看下最新的其他人的仓库的最新提交，应该有人做到8gb内存了"）**
      - 拉取：`git fetch upstream`（三个仓库，只更新远程跟踪引用），另把 CrossDarwin 的几个分支取到 `refs/remotes/crossdarwin/*`（没有加 remote，没有动任何本地分支）。副作用：UniXNU 的拉取顺带给子模块 `drivers/AdrenoMetal` 取了一个远程分支，`drivers/ArmDTPlatform` 的子模块拉取报错（`not our ref a0577afa…`），都不影响工作区。
      - 做这件事的是 Jelly10086，11 月 14 日（+0900）的提交，还没合进 UniXNU 组织的主线：
        - 设备包 `CrossDarwin/UniXNU-sheng` 分支 `memory/outside-window-ranges`：`7e64b48 fix(memory): Preserve all outside-window handoff ranges`、`085f67e`（文档）。`board.toml` 里 `owned_memory_outside_ranges` 从 8 改成 64，别的不动：窗口还是高位内存区的 6 GiB（`owned_memory_size = 0x180000000`），保留列表还是只有 `0xd0000000:0x10000`。意思是把低位内存区（`0x80000000`–`0x100000000`）里零散的空闲段全部交给内核收编，原来表只有 8 项，真机上只收编到 458 MiB（`hw.memsize` 约 6.4 GB）。
        - 固件 `CrossDarwin/uefi-sheng` 分支 `memory/abl-reservations-8g`：`ac0466db fix(memory): Derive the 8 GiB sheng map from ABL reservations`。SEC 阶段读 bootloader 交过来的设备树（`/memory`、`/reserved-memory`、保留块），把静态表里标成保留、而 bootloader 说是空闲的几段放出来（`NOMAP 811D0000`、`RSRV0 gap0`、`XBL Ramdump`、`RSRV1`、`PIL Reserved gap1`、`NOMAP FFE00000`，调制解调器那段只在 bootloader 标了 disabled 时放）。**只对 `ddr_size == 8`、高位内存区是 `0x8c0000000`–`0xa00000000` 的机器生效**，别的机器直接返回、沿用静态表，所以在本机（12 GiB）上不起作用。
        - 他们记录的数字：8 GiB 机型的恢复模式内核报 7643456 KiB；主机上按抓到的设备树算出 7312 MiB 空闲内存（UEFI 自己分配之前）；"Verify hw.memsize and hw.memsize_usable on the next macOS boot"，也就是仓库里还没有真机读数。
      - 和我们的关系：这就是我们说的"路线二"（收编低位内存区），用的是同一个内核补丁（`window-outside-memory-adoption.patch`，rponeawa 11 月 11 日）。它在 8 GiB 机型上最多到约 7.1–7.3 GiB，**上报总量没有超过 8 GiB，被收编的页全在 4 GiB 以下**，所以对"②是总量还是页"两种解释都不提供反例。本机高位内存区多出来的 4 GiB，上游的布局用不上（收编只管窗口下面的内存）。把 `owned_memory_outside_ranges` 改成 64 这一处，做路线二时可以直接照用。
    - **00:05 `report0` 第三次上机（这次要加压）**
      - 00:03 读数：槽 a，`slot-retry-count:a` 5，`slot-unbootable:a` no，电池 3949 mV；镜像 sha256 核对为 `414f2ddb…`。00:05 `boot-sheng.py` 启动，bootloader 45 秒没回来，镜像在运行。
      - 要用户看的：显示 6.0 GB；多开应用把活动监视器的"已用内存"推过 5.5–6 GB；记下开始闪（或卡）时的已用内存数。
      - 读法：推过去就闪 → 被收编的页一被用到就出事，和上报的总量无关；下一步用同一个内核换收编位置找边界（只改设备树里保留列表的第三对，例如只收编 `0x900000000`–`0x980000000` 这 2 GiB）。推到 6 GB 以上也不闪 → 上报的总量引起，接着跑 `report1900`。
    - **00:08 前后的结果（00:05 那次，`report0` 第三次）：用户"没进系统就在闪屏幕了"**
      - 同一份镜像（sha256 `414f2ddb…`）三次上机，三种表现：23:11 约半小时没人报闪；23:42 不闪但应用卡；00:05 还没进系统就闪。差别不在镜像里。
      - 这推翻了什么："上报总量大才闪"（这份上报 6.0 GB 也闪了）；"已用内存到 5 GB、被收编的页开始被用到才闪"（还没进系统，已用内存到不了 5 GB；除非启动阶段累计发出去的页已经超过窗口的初始空闲量，这一点没有数据）。
      - 没有排除的：和上一次运行留下的状态有关（这次的上一次是正在闪的 `report2100`，中间只是强制回 fastboot，没有断电；但 21:11 闪过之后 21:25 不收编的那份是正常的）；和每次开机时序不同、哪些东西拿到了被收编的页有关；这次的"闪"和之前的"闪"是不是同一种现象（比如是窗口服务器反复重启）也不知道。
      - 结论：换镜像对比这条路在结果不稳定时得不出结论，三次上机就可能看到三种结果。要先拿到证据：屏幕的短片（看是新旧两帧交替、黑帧，还是登录界面反复重启），以及内核自己的日志（`log=1` 的持久日志，本机还读不出来）。
    - **00:11 用户："重试，我已经进fastboot了"；00:13 `report0` 第四次上机**
      - 00:05 那次没有短片，也没有说明是在哪个阶段开始闪的。
      - 00:11 读数：槽 a，`slot-retry-count:a` 5，`slot-unbootable:a` no，电池 3947 mV；镜像 sha256 核对为 `414f2ddb…`。00:13 `boot-sheng.py` 启动，bootloader 45 秒没回来，镜像在运行。
      - 这次算第四个样本：只用来数"同一份镜像闪几次、不闪几次"，不从单次结果下结论。
    - **00:16 用户（00:13 那次，`report0` 第四次）："正常启动没闪"**
      - 同一份镜像到现在四次：23:11 没人报闪、23:42 不闪、00:05 没进系统就闪、00:13 不闪。已请用户接着加压（已用内存过 5.5 GB），出问题时记数字、先拍短片。
    - **00:20 日志读取工具：为什么本机用不了，有哪几条路（只读了代码，没有动手）**
      - 它是什么：`../UniXNU-sheng/package/linux-log/build-linux-log-boot.py` 把 `ianchb/sm8550-mainline` 发布的 `boot_sheng_singleboot.img`（头版本 v0，内核后面附着设备树）原样取出内核，加一个 busybox 的 initramfs（`package/linux-log/init`），打成 v0 镜像；`fastboot boot` 它之后，init 只读用户数据分区最后 8192 个 4096 字节块（32 MiB 的日志窗口）到内存，在 USB 串口上开一个 shell，`scripts/read-sheng-log.py` 从 Mac 上取走并解码，然后让平板回 fastboot。分区不挂载、不写。
      - 为什么本机不行：本机的 bootloader 不启动 v0 镜像；改成 v4 后，bootloader 不再去内核后面找附着的设备树，而是用 `vendor_boot` 分区里的（小米原厂的）设备树，主线内核配不上它。`local-tools/make-bootimg-v4.py` 能把固件镜像改成 v4，是因为固件不依赖 bootloader 给的设备树；Linux 内核依赖。
      - 可走的路（都没试过）：
        - 让固件来启动这个 Linux（把内核、initramfs、设备树放进载荷，由固件加载）。要先确认固件或加载器有没有启动 Linux 的入口（构建脚本里提到的 `linux-ref`），工作量不小。
        - 不用 Linux：在平板的 macOS 里开"终端"，用 `sudo dmesg` 和 `sysctl vm.outside_memory` 看内核消息，拍照。只能看当次开机、且系统还能操作时的内容；`sudo` 认不认登录密码还没试过。
        - 打开远程登录后经网络取日志。之前卡在系统设置的授权框不认密码；`sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist` 没试过。
      - 读取镜像的输入（发布包里的内核镜像、busybox、`linux-xiaomi-sheng.deb` 里的模块）本机都没有下载过，`out/sheng/inputs/` 不存在。
    - **00:25 用户问"如何优化系统运行卡顿的问题"，答复的要点**
      - 判断（只有一张照片作依据，没有专门的读数）：主因多半是内存不够。22:25 那次只开了几个应用，6.50 GB 里已用 5.46 GB；内存一满就压缩、换页，表现是应用加载卡一下、"未响应"一会儿又恢复。
      - 请用户确认瓶颈的两个读数（还没拿到）：活动监视器"内存"页的内存压力颜色和"已使用的交换"；"CPU"页排在最前的进程（`mds_stores`、`mdworker` 长期在前就是在建搜索索引）。
      - 用户自己能做的：系统设置 → 辅助功能里打开"减少透明度"和"减弱动态效果"（通用经验，本机没量过）；少开标签页、退出不用的应用；确认是索引在占用时 `sudo mdutil -a -i off`。
      - 构建这边：加内存是根本办法；同步上游拿不到更多流畅度（`upstream/main` 比本地多出来的提交只有构建工具和一处触控修正，核对过提交列表）。
      - 两件已知没解决的：指针移动时约每秒顿一下（`docs/zh/devices/sheng.md` 第 519 行记着原因未知）；诊断镜像实际有 9 GiB、只上报 6 GB，它的卡顿不代表最终效果。
    - **2026-11-15 00:35 收尾小结（用户："落handoff"）**
      - **今晚全部上机读数**（都只从内存启动；除标明的以外 `dpu-scanout=2`）：

        | 时间 | 镜像（`out/flash/boot-v4-payload.` 开头） | 收编的范围 | 显示 | 结果 |
        | --- | --- | --- | --- | --- |
        | 21:11 | `topwin-k443` | `0x880000000`–`0x8A0000000` 和 `0x8C0000000`–`0x980000000` | 9.5 GB | 进系统后卡住，闪烁，指针和菜单栏抖动 |
        | 21:25 | `topwin-k443-noadopt` | 不收编 | 6.0 GB | 25 分钟正常 |
        | 21:53 | `topwin-adopt512m` | `0x880000000`–`0x8A0000000` | 6.50 GB | 约 2.5 分钟定住 |
        | 22:08 | `topwin-adopt512m-ownfix` | 同上 | 6.50 GB | 进桌面约 1.5 分钟定住 |
        | 22:25 | `topwin-adopt512m-hi-ownfix` | `0x960000000`–`0x980000000` | 6.50 GB | 十多分钟不卡不闪；打开"终端"后键盘壳掉线 |
        | 22:39 | `topwin-adopt3g-ownfix` | `0x8C0000000`–`0x980000000` | 9.0 GB | 闪烁、指针抖动、卡住 |
        | 22:49 | `topwin-adopt3g-ownfix-scan0`（`dpu-scanout=0`） | 同上 | 没报 | 刚进桌面黑一下，画面定住 |
        | 23:11 | `topwin-adopt3g-diag-report0` | 同上 | 没报 | 放了约半小时，只报键盘壳掉线 |
        | 23:42 | 同上（第二次） | 同上 | 6.0 GB | 不闪；"终端"时而未响应，几个应用卡顿加载 |
        | 23:51 | `topwin-adopt3g-diag-report2100` | 同上 | 8.05 GB | 加载应用、已用内存到约 5 GB 后开始闪 |
        | 00:05 | `topwin-adopt3g-diag-report0`（第三次） | 同上 | 没报 | 还没进系统就闪 |
        | 00:13 | 同上（第四次） | 同上 | 没报 | 正常启动没闪；加压后的结果没有报 |

      - **能确定的**
        - 不收编正常；收编与否是唯一稳定地把好坏分开的变量。
        - 同一份镜像（`report0`）四次上机表现不同，所以单次上机的好坏不能用来比较两份镜像。
        - GPU 驱动的自有页位图不是原因（修正前后表现一样）。
        - 内核空闲页队列是先进先出（源码核对过）：窗口的页先发，被收编的页排在后面。
        - 补丁给被收编内存建的内核映射是普通可缓存属性；这段物理内存本身没问题（日常镜像的窗口就包含 `0x8C0000000`–`0x980000000`）。
        - `memory-outside-report` 参数生效（0 时显示 6.0 GB，2100 时显示 8.05 GB）。
      - **撤回的结论（不要再引用）**
        - 23:57 的"②是上报的内存总量引起的"：`report0` 上报 6.0 GB，第三次也闪了。
        - 00:05 的"被收编的页一被用到（已用约 5 GB）才闪"：解释不了还没进系统就闪；它只是和一次观察对得上。
        - 更早的"空闲队列后进先出、512 MiB 在进桌面前就用掉了"：队列是先进先出。
        - "每次强制回 fastboot 会用掉一次 `boot_a` 的重试次数"：次数一直是 5。
      - **值得追的线索（都没有证据，按我看值不值得先查排序）**
        - "终端"卡住在本机上和收编内存一起出现过三回：11 月 14 日 19 点前后那份显示 6.38 GiB 的镜像（收编的是低位内存区）有"终端卡住和整机卡死"，对照（5.95 GiB）终端正常；23:42 `report0` "终端"时而未响应；键盘壳掉线有两次发生在刚打开"终端"之后（22:25 那次是其中一次，见键盘那一节）。如果这是同一件事，问题就在"收编"这条路径本身，和收编哪一段关系不大。上游在 8 GiB 机型上收编低位内存区 458 MiB 是正常的，所以也可能和本机（12 GiB、固件内存表是我们自己改的）有关。
        - 这次的"闪"有没有可能是窗口服务器或登录界面反复重启，而不是画面缓冲出错：没有短片，分不清。
        - 上一次运行留下的状态（强制回 fastboot 不断电）会不会影响下一次：00:05 那次的上一次正在闪；但 21:11 闪过之后 21:25 是正常的。
      - **平板现状**：见本文件开头"当前阶段"。电池 00:11 时 3947 mV，今晚一路在降（macOS 下不充电是已知问题），再上机前最好先充电。
      - **主机现状**
        - UniXNU `local/sheng-16g-macos`：补丁里的诊断参数已提交（`a5deddc`），交接文档随后提交；没有 push。`upstream/main` 已拉到 `0c1bac3`，本地没有合并。
        - `../UniXNU-sheng` `local/sheng-12g-top-window` 在 `4ff0ecf`，`board.toml` 已还原（第 267 行是两对）；它原有的未提交改动（`feeds.toml`、`patches/xnu-12377/series`、`unixnu.lock`、三份 `verification.json`、未跟踪的补丁和 `drivers/Ath12kWifi`）照旧不提交。
        - 三个仓库里多了 `refs/remotes/crossdarwin/*`（只读引用，可以用 `git update-ref -d` 删掉）。
        - `<output>/kernel/kernel.macho` 是日常的 `33d294c8…`，`<output>/payload/payload.img` 是日常的 `8a36fe56…`；诊断内核另存为 `kernel.macho.diag-980a9895`。
        - 诊断镜像的启动参数文件在 scratchpad 里，会被清掉；要重做时，取载荷里的 `::/EFI/UniXNU/unixnu.toml`，在 `args` 末尾加 ` memory-outside-report=<MiB>` 即可。
      - **镜像清单（`out/flash/`，不入库；都用诊断内核 `980a9895`，收编 `0x8C0000000`–`0x980000000`）**
        - `boot-v4-payload.topwin-adopt3g-diag-report0.img` `414f2ddb32ed3b1c5e6ebc93a5afde6e653c3ec5743887136466f6aa535d4f21`：上报 6.0 GB，上过四次机。
        - `boot-v4-payload.topwin-adopt3g-diag-report2100.img` `789a2fd8f1e014f9107d2ba4a6ba3087a78d77c617e6d703b792b2754496e6da`：上报 8.05 GB，上过一次机。
        - `boot-v4-payload.topwin-adopt3g-diag-report1900.img` `589d4df60179038ec41bb18a427ed7949c6ecf2f2dc1570b02cec7d0125c20df`：上报 7.86 GB，没上过机。
        - `boot-v4-payload.topwin-adopt3g-diag.img` `e63b1849850aa72dacf78642d6a305b60040237934b70af0868c10800e1f1ac7`：不带参数（上报 9.0 GB），没上过机。
        - 更早的几份（`topwin-adopt512m-hi-ownfix` `4c833b1a…` 等）见上面各条。
      - **建议的下一步（按顺序；标"要同意"的先问用户）**
        1. 先拿证据，不再换镜像猜。最省事的是用户在平板"终端"里跑 `sysctl vm.outside_memory hw.memsize` 并拍照（看内核实际收编和拒绝了多少页），出现闪时拍 10–20 秒短片放 `data/mp4/`（慢动作最好），卡的时候看活动监视器的内存压力颜色、交换用量和 CPU 排第一的进程。
        2. 让持久日志能读出来（见"00:20 日志读取工具"一条的三条路）。这是之后每一次排查都要用的，值得单独做；属于新工作，先和用户确认范围。
        3. 想先用上多一点内存：把 6.5 GB 那份（`topwin-adopt512m-hi-ownfix`）多跑几次、每次半小时以上，包括打开"终端"；稳定了再谈写进 `boot_a`（**要同意**，每次写都要单独同意）。注意它只跑过一次。
        4. 查"终端卡住和收编一起出现"这条线索：同一个诊断内核，不收编（启动参数加 `memory-outside=0`，不用重编）时"终端"是否正常；再只收编低位内存区时是否复现。
        5. 路线二（收编低位内存区）可以照用上游的一处改动：`owned_memory_outside_ranges` 从 8 改成 64。注意内核补丁里 `ARM_VM_OUTSIDE_RANGES` 是 16，段数多于 16 时后面的会被丢掉，要一起核对。上游固件那处改动只对 8 GiB 机型生效，本机用不上。
        6. 用户问过但没查的：系统设置的授权框不认登录密码；键盘壳掉线后重新吸附不能恢复。
    - 设备包里还有现成的诊断手段没用过：启动参数 `boot-progress=1|2` 和 `boot-diag-resume=<秒>`（`../UniXNU-sheng/package/BootProgress.c` 第 88 行：系统停止输出画面超过这么多秒，诊断页接管面板）。现在的参数行里都没有。下一步证据不够时加上。
- **路线 A：把窗口做大（2026-11-15 00:55 到 01:45；用户选定，设计等用户确认，什么都还没动）**
  - 起因：用户要我根据试错记录，构思怎么扩大能稳定使用的内存。我给了四条路：
    - A：把窗口本身做大，不收编高位内存区（约 9.4 GiB；要改内核一个常量）。
    - B：顶部 6 GiB 窗口，只收编低位内存区（约 6.4 GiB；不改内核）。
    - C：继续修"收编高位内存区"（约 10.4 GiB；原因未知）。
    - D：验证交换文件能不能用（不加物理内存）。
  - 我建议先 B 再 A，用户回的是"A"。我的理解（写进了设计，用户可以改）：只做 A 的几步，B 不单独做，D 不放进这份设计。
  - 设计：`docs/superpowers/specs/2026-11-15-memory-large-window-design.md`。
  - 依据：试错记录里不稳的只有两样，"收编高位内存区"和"高位内存区的第一个 GiB"。窗口里的页和低位内存区的收编在本机一直是稳的。`0x8C0000000`–`0xB00000000` 正好 9 GiB，连续，全部当窗口页用过。
  - 上一份设计否掉"加大窗口"，理由是窗口每大 1 GiB 要花两份内核地址（静态区一份，压缩器一份）。压缩器那一份可以用现成的启动参数钉住：`vm_compression_limit=<页数>`（内核源码 `osfmk/vm/vm_compressor.c:174`、`:827-829`），1572864 是 6 GiB。这是读代码的结论，没有上机。
  - 要改的（都还没动）：
    - 内核补丁 `patches/xnu-12377/native-4k-bootstrap-capacity.patch`：引导页表 16 页改成 22 页。16 页只够 6 GiB；不够时内核停在入口，屏幕上没有内核的字，只有颜色条（见下面审阅的第一条）。
    - 生成器 `scripts/unixnu/devicetree.py:342` 和加载器 `drivers/DarwinBoot/DarwinBootPkg/Driver/WindowSize.h`：窗口上限 8 GiB 改成 9 GiB。加载器编在固件里，要重建一次固件。
    - 板级配置 `../UniXNU-sheng/board.toml`：窗口大小、下限、保留列表，`kernel_args` 加 `vm_compression_limit=1572864`。
  - 上游的情况：`docs/.vitepress/device-records/asteroids.toml:71` 记着别的机型试 7.75 GiB 窗口时停在内核入口，原因就是这 16 页，并提到一个改成 22 页的提交 `2867796`（"staged, not built"）。这个提交不在本地任何已拉取的引用里；`upstream/main`（`0c1bac3`）和 `crossdarwin/*` 各分支都还是 16 页、8 GiB 上限。动手前再拉一次上游，合进来了就直接用。
  - 分步（都只从内存启动，每一步过了才做下一步）：
    - 第 1 步，7.5 GiB 窗口：下限 `0x920000000`，不收编，用现成的固件 `e168abab`。它不过 8 GB，只检验"窗口变大"本身。
    - 第 1b 步：同一份载荷换新固件，短跑一次，只为确认新固件。
    - 第 2 步，9 GiB 窗口：下限 `0x8C0000000`，不收编。这一步会正面碰到"上报 8 GB 以上的 4 次全部出事"那条没解释的相关性；碰到了就停在约 7.5 到 7.9 GB。
    - 第 3 步，再加低位内存区的收编：保留列表第二项换成 `0x880000000:0x280000000`，把整个高位内存区挡在收编之外（漏掉这一项，收编会整个关掉而且不报错）。
  - 每一步至少上机三次，每次都把内存用满，没有闪烁和定住才算过。单次上机正常不作数。
  - 第 1 步之前要用户在日常系统里做一次 30 分钟的基线（同样的做法把内存用满，不用主机，不换镜像）。原因：把内存用满本身就会带来"应用未响应一会儿又恢复"，没有基线分不清它是窗口变大带来的还是本来就有的。卡顿怎么判（看当时内存压力的颜色，对着基线比）写在设计的"通过标准"里，是我定的，用户还没看过。
  - 确认设计等于同意：改一处内核补丁并重编一次内核；改加载器上限并重建一次固件；上面几步和设计里写明的几份对照镜像的内存启动（每次仍要用户在场并说可以开始）；那一次基线。写 `boot_a` 不在内，最后一步通过后另外问。
  - 设计写完后让一个独立的审阅者读了一遍（只读，没有构建，没有碰平板），它指出的都对着代码核实过，已改进设计：
    - 引导页表不够时屏幕上不是什么都没有。载荷里的内核带入口探针（`../UniXNU-sheng/board.toml:59` 的 `panic_screen`；`<output>/logs/payload-patch.log` 写着 `stage 1 blue bar, stage 2 magenta bar`）：加载器画绿条，内核入口画蓝条，开 MMU 之前画品红条。页表不够的样子是"有绿条和蓝条，没有品红条"，上游那次记录的就是这样。以后任何"停在内核入口"的情况都先拍颜色条。
    - `vm_compression_limit=1572864` 不是和现在完全一样：预留的地址是 6 GiB（日常镜像约 5.5 GiB），压缩器最多收 1480336 页（日常约 144 万页），而且这个上限不再随内存变大（`vm_compressor.c:923-931`）。
    - 内核地址预算的参照：约 3 GiB 可分时两次短跑没有分配失败；出过分配失败的是只剩约 1.2 GiB 的那一版（收编补丁开头的说明）。
    - 8 GiB 的上限还写在另外三处：`drivers/DarwinBoot/Test/make-fixtures.py:85`（要跟着改）、`scripts/check-darwinboot-window-parser.py:37,42`（没人调用，能跑通就跟着改）、`../UniXNU-sheng/scripts/make-sheng-adt.py:110-112`（旧生成器，不动）。
  - 顺带核实：收编补丁没有 `vm.outside_memory` 这个 sysctl，上面"建议的下一步"第 1 条里写的那条命令读不到东西。内核只在启动时打一行 `memory outside the span: N pages adopted, M refused`（`osfmk/arm64/machine_routines.c:2369`），要用 `sudo dmesg` 看；从 `hw.memsize` 的差值也能算出来。
- **路线 A：主机部分做完，基线有了第一份结果（2026-11-15 08:20 到 10:05；新镜像一份都还没上机）**
  - 用户确认设计（原话"开始实施验证"）之后又说过三句话，都照做了："审阅完直接开始构建"；"镜像打好后告诉我，我来做基线"；"现在在fastboot为我启动"（我理解成把日常系统起起来做基线，执行的是 `fastboot reboot`）。
  - 提交（都在本地，没有推送）：
    - `UniXNU`（分支 `local/sheng-16g-macos`）：`e9d3bb9` 引导页表 22 页；`294936c` 生成器上限 9 GiB；`64c26a0`、`60a61ba` 变体载荷工具和它的第一轮修补；`b47b5f5` 布局测试；整体审阅后的一轮修补 `822e47d`（变体工具）、`1f60234`（新工具 `local-tools/bootimg-contents.py`）、`005dca4`（测试）、`30e521d`（文档里的 9 GiB 和测试注释）。
    - 子模块 `drivers/DarwinBoot`：`bdb6ff7`（分支 `local/window-9g`），加载器上限 9 GiB。
    - `../UniXNU-sheng`：`5877d2c`（分支 `local/sheng-12g-large-window`），只改 `board.toml`：窗口 `0x240000000`、下限 `0x8C0000000`、保留列表第二项 `0x880000000:0x280000000`、macOS 27.3 的 `kernel_args` 末尾加 `vm_compression_limit=1572864`。这个仓库里原有的未提交改动没有动。
    - `../uefi-sheng`：`20331338`，没有改。
  - 主机测试：`python3 -I -B -W error -m unittest discover -s local-tools/tests`，87 个全过。
  - 三处上限现在一致：补丁 22 页；生成器 `scripts/unixnu/devicetree.py:298` 的 `0x240000000`；加载器 `drivers/DarwinBoot/DarwinBootPkg/Driver/WindowSize.h:7` 的 `0x240000000ULL`。
  - 审阅：
    - 每个任务做完都由另一个子代理审阅。Task 3 的审阅查出两处要紧的，都修了（`60a61ba`）并复审过：输入文件恰好叫 `OUT.tmp` 时会被工具删掉；`data-reset` 的检查只看 `args` 行，而生成器是用 `confirm_args` 送它的。
    - 四个任务做完后、构建之前做了一次整体审阅：可以构建，没有 Critical；补丁、生成器、加载器、板级的值都不用改。两条 Important 都是计划的毛病：没有哪一步核对"哪份载荷进了哪个镜像"（现在每份打完都用 `bootimg-contents.py --payload` 核对）；设计里"把压缩器钉到 4 GiB"那份诊断镜像用原来的工具做不出来（工具现在有 `--replace-arg`）。
    - 那一轮修补的复审见本条最后。
  - 上游：`upstream/main`（`0c1bac3`）仍是 16 页，没有可对齐的东西，没有合并。
  - 构建产物（`<output>` 是 `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos`）：
    - 内核：`<output>/kernel/kernel.macho.bigwin-6e3cfce7`，143753216 字节，sha256 `6e3cfce7a80ce84c78131ae83ed8596d1c52ab3d317f7522529f177e6d8a48ba`（同后缀的 `kernel.json`、`kernel.map.json` 在旁边）。`_bootstrap_pagetables` 到下一个符号相差 `0x16000`，就是 22 页。
    - 新固件：`out/flash/SILICIUM_UEFI.bigwin-8407c84f.fd`，3145728 字节，sha256 `8407c84f0d6287ca6610f30a40e8103a39d63cf2f851f66e9ca1705b6d3b4f08`。构建前后子模块都是 `bdb6ff7` 且没有改动；`DarwinBoot.efi` 是这次构建重编的（09:36:59）。
    - 带新固件的 v0 镜像：`<output>/boot/boot-bigwin.img`，210903040 字节，sha256 `5c926a3fd28cf7a13dfd6e941cff3b9dfd936ef97c43dadf62282cf4353ea333`。现成固件（`e168abab`）的 v0 镜像仍是 `<output>/boot/boot-topwin.img`（`85f9dbf8…`）。
    - 六份载荷，都在 `<output>/payload/` 下，各 209715200 字节（计划里写"七份"是把 `s1` 数了两次）：
      - `payload.bigwin-base.img`（只读）：窗口 `0x240000000`（9 GiB），下限 `0x8C0000000`，参数行就是板级的那一行。sha256 `9d3b3004a68da52cd8f7f2057b97c51a00c64702621771278fa696c8a9e5f4d9`。
      - `payload.bigwin-s1.img`：`0x1E0000000`（7.5 GiB），`0x920000000`，加 `memory-outside=0`。sha256 `ccd883c6634c10286f78f820064890d6004f3a471830b045fad38e8236113311`。
      - `payload.bigwin-s2.img`：9 GiB，`0x8C0000000`，加 `memory-outside=0`。sha256 `2b7471107c7548608175ba2447eefd143a6bec9e13940226619553e8376ea3aa`。
      - `payload.bigwin-ctl6.img`（对照）：`0x180000000`（6 GiB），`0x980000000`，加 `memory-outside=0`。sha256 `f1338e96e26956af1ca6d736a4904c922b50bdd75d2d31fe12054d4341630312`。
      - `payload.bigwin-split.img`（备用）：7.5 GiB，`0x8C0000000`，加 `memory-outside=0`。sha256 `4d9f365e3e4ac99ce29a20f7e5bda9d9a3f55c03c88461e1b920f759d2ca32c7`。
      - `payload.bigwin-8g.img`（备用）：`0x200000000`（8 GiB），`0x900000000`，加 `memory-outside=0`。sha256 `440a3df9c6c6c2f55cf0d2f662007e76713a6ad2db781da6b994ce170e0acd25`。
    - 五份镜像，都在 `out/flash/` 下，各 210903040 字节，都只从内存启动：
      - `boot-v4-payload.bigwin-s1.img`（第 1 步）：现成固件加 `payload.bigwin-s1.img`。sha256 `8bc7b897dddbfa4f9afe849381f5f00f811f402defa99583ff17458664088a92`。
      - `boot-v4-payload.bigwin-s1b.img`（第 1b 步）：新固件加 `payload.bigwin-s1.img`。sha256 `f356cae56352bbb480c9e91143551174b1d6873401bbf0f10692659bf5609bcb`。
      - `boot-v4-payload.bigwin-s2.img`（第 2 步）：新固件加 `payload.bigwin-s2.img`。sha256 `e373b41a779e7331258eeec9ac69883e821231b071f507b84591dcc21ffdae1f`。
      - `boot-v4-payload.bigwin-s3.img`（第 3 步）：新固件加 `payload.bigwin-base.img`。sha256 `6b663facda158b2badf877dbebd974eb6ef4a535bd81309c07405bdef6eaf774`。
      - `boot-v4-payload.bigwin-ctl6.img`（对照）：现成固件加 `payload.bigwin-ctl6.img`。sha256 `e9b250753e2ae9a42885f24e4c674d326b5096a22079a3d81c2d26342e8196bf`。
  - 载荷和镜像是怎么核对的（都没有只信工具自己打印的那一行）：
    - 每份变体用 `local-tools/adt-chosen.py` 读回设备树的 `/chosen`：窗口大小和下限是上面的值，另外四个 `darwinboot-*` 属性和基准一样。
    - 每份变体的卷里 8 个文件逐个和基准比哈希：只有 `kernel.macho.adt` 和 `unixnu.toml` 不同（`s2` 只有 `unixnu.toml` 不同）。
    - 每份变体的 `unixnu.toml` 只有一行 `args`，等于 `memory-outside=0`、一个空格、再接基准那一行（923 字节 59 个参数；基准 906 字节 58 个）；文件其余部分和基准一样；没有 `data-reset`，没有 `confirm_args`。
    - 每份镜像跑 `bootimg-contents.py --payload`：第二行是 `ramdisk is <载荷路径>`，退出码 0，也就是镜像里的 ramdisk 和载荷文件逐字节相同。
    - 用现成固件的两份（`s1`、`ctl6`）里固件那一段是 1180573 字节、sha256 `6d40d584…`，和昨晚跑过的 `boot-v4-payload.topwin.img`、`boot-v4-payload.topwin-adopt3g-diag-report0.img` 里的是同一段；用新固件的三份是 1180698 字节、sha256 `610fa1f6…`。
    - 打包期间把 `out/flash/` 下 23 份旧镜像（`boot-v4-flash*.img`、不带 `bigwin` 的 `boot-v4-payload*.img`、`boot-v4-install.img`）设成只读，打完改回 644；前后各算一次 sha256，完全一样。
  - 日常文件没有动：`<output>/kernel/kernel.macho` `33d294c8`，`<output>/payload/payload.img` `8a36fe56`，`<output>/boot/boot.img` `35f03ec4`，`boot.json` 和 `boot.good.json` 相同；`out/flash/` 下 `boot-v4-flash.img` `c244f53d`、`.prev` `40234c20`（`boot_a` 里的那份）、`.prev2` `4cb441e0`、`.prev3` `ae0d4179`、`.topwin` `40fb63bd`，`boot-v4-payload.img` `a9cb0b31`，`boot-v4-install.img` `75fb800a`（带 `data-reset`，这次没有启动也没有刷）。
  - 现在的状态里要记住的：
    - 固件构建目录（`../uefi-sheng/Build/`）停在新固件 `8407c84f` 上，之后直接跑 `./unixnu bootimg` 得到的是带新固件的镜像。
    - `<output>/boot/boot.json` 已从 `boot.good.json` 复制回去；OS 镜像已卸载。
    - 计划文档在整体审阅后加了几处做法（基准载荷先设只读、固件构建前后记子模块的提交、每份镜像核对载荷、诊断镜像用 `--replace-arg` 做），都标了日期。
  - 没做的和已知的缺口：
    - QEMU 的加载器测试 `scripts/test-darwinboot.py` 没跑（本机没有 `qemu-system-aarch64`）；加载器的五个主机测试和 `Test/window-size.c` 跑过。
    - `scripts/check-darwinboot-window-parser.py` 现在跑不起来，没有跟着改。
    - `patches/xnu/native-4k-bootstrap-capacity.patch`（另一个 XNU 版本的那份）仍是 16 页。macOS 27.3 用的是 `patches/xnu-12377/` 那份（`<output>/xnu-patches.list` 第 8 行）。用 `patches/xnu` 的 profile 配 6 GiB 以上的窗口会停在内核入口。
    - 变体工具拒绝名字是 `data-reset` 的参数，基准载荷里出现这几个字时任何调用都拒绝；但 `--arg=-data-reset`、`--arg=x=data-reset`、`--replace-arg=debug=data-reset` 这三种写法不会被拒绝，产物的 `unixnu.toml` 里会出现 `data-reset` 这几个字。计划里用到的参数是固定的几条，都不沾边；没有改，记在这里。
    - `local-tools/boot-sheng.py` 不检查镜像里有没有 `data-reset`。可以以后加，这次没做。
  - 基线（用户在日常系统里做，Task 6 的第一项，还没做完）：
    - 平板怎么起来的：09:46:28 在 fastboot 里只读查询（一台设备；`current-slot` a；`slot-retry-count:a` 5；`slot-successful:a` no；`slot-unbootable:a` no；`battery-voltage` 3794；`unlocked` yes），09:46:40 `fastboot reboot`，之后 60 秒 bootloader 没有再出现。
    - 用户约 09:50 的原话："进系统后，使用内存在3g+卡了一会，然后跳到4.72g使用内存之后，卡顿，鼠标指针闪烁，视频放到mp4路径下了"。
    - 录屏 `data/mp4/IMG_6402.MOV`（不入库；23724175 字节，文件时间 09:48:30，3.63 秒，218 帧）。文件时间离重启不到两分钟，所以这是刚登录之后的事；程序坞里很多应用带着运行的小点。
    - 我从录屏里读到的（全片每 4 帧取一帧，前 48 帧逐帧，内存面板另取一张原分辨率的截图）：
      - 活动监视器内存页（上半被一个"信息"窗口挡住）：物理内存 5.95 GB（这一行只露出下半），已使用 4.72 GB，缓存文件 1.21 GB，交换 0，App 内存 1.44 GB，联动内存 2.83 GB，已压缩 456.3 MB；压力图露出来的一段是绿色。
      - 指针画在相距不远的两个位置上，每一到三帧换一次位置，中间的帧两个位置各有一个淡的；窗口内容在看过的帧里没有变化。
      - 平板自己的时钟不准：菜单栏显示周五 11 月 13 日 10:07，主机当时是 11 月 15 日 09:48。录屏里的时间不能当时间戳用。
    - 按设计的叫法，这是"卡顿"加"闪烁"（指针抖动），出在**日常系统**上（6 GiB 窗口，不收编）。当时内存是占满的：已用加缓存 5.93 GB，物理 5.95 GB；已用占 79%（设计里"填满"的线是 80%）。压力是绿的。
    - 它说明的：卡顿和指针抖动不是"窗口变大"或"收编"才有的，日常系统自己就有。
    - 它还不说明的：
      - 抖动是内存占满带来的，还是负载带来的。当时刚登录，一批应用同时在启动，CPU 和读盘都很重；指针抖动也可能只是那一阵负载的结果，和内存多少无关。"已用加缓存接近物理内存"在正常的 macOS 上是常态，本身不算压力，当时压力图也是绿的。
      - 昨晚收编那几版的闪烁是不是同一回事（昨晚有一次是进桌面之前就闪）。
    - 所以基线还要补两个观察，后面几步才能"同样的情形比同样的情形"：
      1. 刚登录、应用正在恢复的那一两分钟：已经有了（卡顿加指针抖动）。
      2. 不动它等几分钟，应用都起来之后，内存仍然占满：指针还抖不抖。
      3. 退出几个应用，内存不再占满：指针还抖不抖。
    - 顺带看到的一个数：联动内存 2.83 GB，占了已用的六成。今天留给应用和缓存的只有约 3.1 GB（5.95 减 2.83）。如果联动内存大致不随窗口变，7.5 GiB 窗口留给应用和缓存的约 4.6 GB，9 GiB 约 6.1 GB。这是估计：联动内存会随窗口略增，而且它为什么有 2.83 GB 没有查过。
    - 10:02 请用户趁系统还在那个状态做的：退出几个应用，让已用加缓存掉到 5 GB 以下，看指针还抖不抖；拍 `sysctl hw.memsize vm.pages vm.pages_excluded` 的输出和整个内存页；之后重新填满，计时到 30 分钟。稍后补了一条：退应用之前先不动它等几分钟，看抖动自己停不停。结果还没回来。
  - 等用户定的一件事。设计写的是"闪烁、定住、自己重启出现一次，这一步就不过"。照这条，日常系统自己也不过，没法拿来比。我的建议（用户没答之前不算数）：
    1. 判每一步时，同样的情形和基线比。情形分三种：刚登录应用正在恢复的那一两分钟；安静下来且内存占满（已用加缓存离物理内存不到 0.5 GB）；安静下来且内存没占满。某种情形下基线没有闪烁而这一步有，这一步不过；基线也有的，记录下来，不单凭它判不过。
    2. 每一步上机先照基线的样子来一遍（登录后让同一批应用恢复出来），再往上填内存。7.5 GiB 的窗口在那一阵里内存还空着 1 GB 多；如果照样抖，抖动就不是内存占满带来的。
    3. 定住和自己重启照旧，出现一次就不过。
  - 第 1 步怎么开始（用户说可以之后）：平板进 fastboot；只读查询 `current-slot`（应为 a）、`slot-retry-count:a`、`battery-voltage`；核对镜像的 sha256 是 `8bc7b897…`；`python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.bigwin-s1.img --serial <序列号>`。通过线是 `hw.memsize` 不低于 7784628224。其余照计划的 Task 6。
  - 整体审阅后那一轮修补的复审（10:16 回来，只读）：
    - 结论：要修的十一项都修到了，没有新的 Critical 或 Important。它自己搭了一份 64 MiB 的替身载荷，把六条变体命令各跑了一遍，结果都和命令说的一样；87 个测试它也跑了一遍，全过。产物不受影响。
    - 不再做第二轮修补。留下没改的：
      - 上面"变体工具"那一条缺口（`data-reset` 这几个字可以作为值或带横线的名字进到产物里）。我读了两处读这个参数的代码（`drivers/RamBlock/NativeRamBlock.cpp:213`、`../UniXNU-sheng/package/BootWatchdogPolicy.c:105`）和构建内核用的解析函数（`<output>/tree/.cache/xnu-work/pexpert/gen/bootargs.c` 的 `PE_parse_boot_argn_internal`）：都是按名字取，名字要和 `=` 之前的整段完全相同（横线也算在内），值只认 1 和 2。所以那几种写法都不会被当成 `data-reset`。没有找到按子串匹配的读法。
      - 三条小的：有一个测试分不出"名字是 `data-reset` 被拒"和"这一行没有这个参数被拒"（两种都是拒绝）；"基准载荷里缺文件"没有测试，悬空链接那个测试没有断言链接还在；工具开头的说明读起来像"别的写法的 `args` 行一律拒绝"，实际只在给了 `--arg` 或 `--replace-arg` 时才拒绝。
    - 用工具时要知道的：一次运行被杀掉会留下 `OUT.tmp`，要手动删掉才能再跑；产物镜像的空闲簇里还留着基准的旧设备树和旧参数行，直接在镜像里搜字节会两份都搜到，要看内容就用 mtools 把文件取出来看。
- **启动页上的 `SetupKeypad: Failed to Locate STI Device Path! Status = Not Found`（用户 2026-11-15 问有没有影响）**
  - 没有影响，已这样答复用户。这一行是 Silicium 固件的启动管理器打的：`../uefi-sheng/Silicon/Silicium/SiliciumPkg/Library/BootManagerLib/BootManager.c:114` 调 `RegisterKeyCallback`，它在 `KeyCallback.c:103` 调 `SetupKeypad`，找不到按键输入设备时在 `KeyCallback.c:55` 打这一行并返回，启动管理器继续往下走。
  - 本机的固件里没有可用的按键输入设备，所以每次开机都有这一行；11-13 的录屏 `data/mp4/IMG_6358.MOV` 里就有。
  - 实际少的只是"开机时按音量上键进 Silicium 启动管理器"这个热键。UniXNU 自己的菜单能不能读音量键，没有核对。

**开机待机久了，键盘和触控板失效（用户 2026-11-14 报告，还没有调查）**
- 用户原话："开机待机久了之后，键盘+触控板的固件会失效"。指的是键盘保护套（键盘加触控板）。
- 还不知道的：大约待机多久出现；失效时屏幕触摸是否正常；重新吸附键盘套能不能恢复，还是必须重启；出现时平板有没有接 USB 线。处理时先问清。
- 线索，都没有验证过：
  - 上游已知并且没在硬件上测过：`docs/zh/devices/sheng.md` 第 523 行（"…their effect on the reported macOS charging and idle failures is not yet measured on hardware"）和第 528 行（待办："keyboard/touchpad response after extended idle"）。
  - 同一文件第 496、1084 行描述了键盘服务的恢复逻辑：读失败 100 ms 后重试，保活失败时用 sleep GPIO 唤醒控制器，连续三次失败就释放输入并重新加载固件，重载失败会退避。用户看到的"固件失效"可能就是这条恢复路径没有成功。
  - 设备仓库的 #93（"fix(keyboard): preserve touchpad precision and recover cover input"，11-12 合并）已经在本地构建里。上游还有一个分支 `fix/keyboard-cover-recovery`（bluseliu50，11-13，23 个文件），和 #93 是什么关系没看。
  - 设备仓库本地落后上游 3 个提交，是 #95（"fix(input): Retain digitizer properties during concurrent updates"），和输入有关，没合进来。
- 新的观察（2026-11-14 22:35 前后，从内存启动的测试镜像 `boot-v4-payload.topwin-adopt512m-hi-ownfix.img`，启动后约 8 到 10 分钟）：用户打开终端之后键盘保护套掉线，没有自己连回来，触摸屏正常。重新吸附能不能恢复还没试。
- 2026-11-14 22:39 前后用户试了重新吸附："把键盘壳拿下来再吸回去 不能恢复"。上面"还不知道的"里这一条有答案了：重新吸附不行，目前只有重启能恢复。
  - 我的推断（没有验证）：键盘控制器（Nanosic WN8030，I2C9，`docs/zh/devices/sheng.md` 第 475 行）在平板这一侧，保护套吸上、拿下只是它发来的一种报文（第 503 行，`0xa2`），所以吸附动作不会让控制器重新上电。重新吸附不恢复，说明卡住的是平板这一侧：控制器不应答，或者键盘服务停在了恢复路径里（第 496 行：重载固件失败会退避到 32 秒一次）。要分清得读持久日志里的 K 行（第 490 行）。
- 和"打开终端"连在一起出现已经两次：19:01 之后那份实测内存表的镜像也是"新开机打开的终端有点卡死"，随后"键盘触控板也掉了"。是不是巧合不知道，处理时先看这一点。
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
