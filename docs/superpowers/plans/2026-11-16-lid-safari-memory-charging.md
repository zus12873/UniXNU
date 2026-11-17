# 方案调整：合盖睡眠、Safari、12 GiB 内存表、充电功率（sheng / macOS 27.3）

## Context

上一轮的状态清单之后，用户（2026-11-16）调整了方向：
1. 合盖时直接让系统进入睡眠（取代上一版"合盖只丢触摸屏报点"的修法）。
2. 查上游有没有修 Safari 使用问题的方案。
3. 做 12 GiB 的内存表，让系统内存尽量拉到 12 GiB。
4. 每处理一个问题前，先查上游/社区有没有同类 case，有就先用上游的方案（`.claude/rules/check-other-repos-first.md` 已有这条规则，这次把它写进每个工作流的第一步）。
5. 充电现在约 15 W，没用到平板充电固件的上限，要拉高。

共同前提（不变）：只从内存启动测试镜像、每次启动要用户当场同意；不刷 `boot_a`（刷要另问）；槽位 b 永不设为活动，进 fastboot 读两个槽位、a ≤4 就补；日常文件哈希构建前后核对；新产物带后缀；驱动/内核改动要用户同意；进度落到 `HANDOFF.md` 顶部和 `docs/superpowers/plans/`。

## 每个问题动手前的固定第一步（用户再次强调，规则见 `.claude/rules/check-other-repos-first.md`）

1. 拉取最新（关沙箱）：核心、`../UniXNU-sheng`、`../UniXNU_macOS`、`../uefi-sheng`、`drivers/*` 各 `git fetch --all --prune`；rponeawa、CrossDarwin 的 fork 按需 `git fetch <url>`。
2. 搜本地历史：`git log --all -S/-G/--grep '<关键词>'`。
3. 搜 GitHub：`gh search prs/issues/commits --owner UniXNU`、`--owner CrossDarwin`，以及 `--repo rponeawa/...`，已关闭的也算。`gh` 要关沙箱才读得到钥匙串。打开相关的 PR，看说明和 Device Test。
4. 查到了就先用上游的，合进来或在它上面接着做，写明出处。没查到，就在 `HANDOFF.md` 这一条里写"查过，没有"，列出仓库和关键词。

这次规划时已经查过一轮（11-16），结论写在各工作流里。执行时每个工作流开工前再查一次，因为上游一直在合。

## 工作流 0（前置，所有工作流共用）：整合分支跟上上游，构建 cd6

上游在本地拉取之后又合了一批，都和这次的事有关：
- 核心：#264 到 #270；
- sheng：#96、#101 到 #105；
- uefi-sheng：#6；
- AdrenoMetal：#36、#37；
- ShengUfs：#12。

多数内容已经通过 CrossDarwin 的分支进了整合分支，但要跟上游 main 对齐。

1. 拉取后，把三个仓库的上游 main（uefi-sheng 是 `sheng`）合进各自的 `integrate/others-20261115`。
   - 冲突的取舍和 11-15 那次一样：内存设置留本机的，`porting.toml` 两边都留。
   - 合完跑 `scripts/check-unixnu.py`、`tests/`、sheng 的 `porting-record.py check --base upstream/main` 和相关检查脚本。
   - 合之前先查"对方新增、本地被忽略"的文件（11-15 出过根卷策略文件被覆盖的事故）。
2. 你接上外置盘，我 `hdiutil attach /Volumes/12873/UniXNU-build.sparsebundle`，再 `diskutil verifyVolume`。
3. 我备份并核对日常文件的哈希：`kernel.macho` `33d294c8`、`payload.img` `8a36fe56`、`boot.img` `35f03ec4`、`boot.json`。
4. **构建要你在自己的终端里跑**：先 `sudo -v`，再 `./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。
   - 原因：`scripts/build-boot-runtime.py:80` 用 `sudo -n` 跑只读的 `scripts/list-metal-libraries.py`，而 sudo 的凭据按终端记，我这边带不过去。
   - 构建完我把产物另存成 `kernel.macho.cd6-*`、`payload.cd6-base.img`，再还原日常文件、核对哈希、卸载 OS 镜像。
5. 用 `local-tools/make-payload-variant.py` 从 `payload.cd6-base.img` 派生两份载荷：
   - `payload.cd6-s1.img`：7.5 GiB（`--set darwinboot-memory-size=0x1E0000000 --set darwinboot-memory-floor=0x920000000`），加 `--arg memory-outside=0 --arg enable-jobs=com.openssh.sshd --arg exec-env=iconservicesagent:CI_ENABLE_MPS=0`，不带 `ci-mps=0`；
   - `payload.cd6-s1-chg-noauth.img`：在上一份基础上再加 `--arg charge-auth=0`。
   - 参数行不超过 1000 字节。
6. 用 `local-tools/make-bootimg-v4.py` 加新固件 `boot-bigwin.img` 打成 v4 镜像，`bootimg-contents.py --payload` 核对，22 份日常镜像的哈希不变。
7. 上机 CD6-1（只从内存启动，要你说可以）。fastboot 里先读两个槽位，a ≤4 就补。要看的：
   - 能进桌面、SSH 能连；
   - 用户那份 iconservicesagent 的环境（`ps eww`）里有 `CI_ENABLE_MPS=0`；`launchctl print gui/501/...` 的崩溃次数不涨；日志里没有 `MPSImageUnaryKernel`；
   - `tablet-icon-stress.js` 跑两轮没有失败；
   - 数日志里的 GPU 复位次数（`GpuRecoveryVictim`、`MadeBeforeRecovery`）；
   - 关机和重启正常（PSCI，#101）；
   - 工作流 1 的 Safari 验证；
   - 工作流 4 的第一组充电读数。
8. 过了以后：Core Image PR 补上真机证据再开（`zus12873/UniXNU-sheng` 的 `fix/macos-icon-agent-mps`，先查上游有没有人做了同样的事）。推送整合分支和 `drivers/Adreno740` 的 `0848123`，都要你说推才推。

## 工作流 1：Safari

查到的上游方案：
- `UniXNU/ShengUfs#12` / `UniXNU-sheng#105` / `UniXNU#266`（2026-11-15 合并）：已验证的 UFS 窗口按"内部存储"发布，Disk Arbitration 不再卸掉 App cryptex 挂载；设备测试确认 Safari 在访达"应用程序"和启动台里可见、能启动（`reports/macos27-internal-storage.md`）。
- 已在整合分支里：sheng `integrate/others-20261115` 的 `drivers/ShengUfs` 钉在 `2b6638b`，和上游 PR 头 `a454768` 的树完全相同（`git diff --stat` 为空）；合并提交 `7683a86`、`6052849`。日常镜像里没有。
- 更早的、已在我们树里的：`392a41a`（11-10，内核挂 App cryptex，修 Safari 图标是问号）、`f6e4012`（WebKit 扩展从 OS cryptex 启动）。
- CrossDarwin `test_27` 的 `1c06906`、`d9334c5`（APFS 容器方案下修 Safari 入口和 LaunchServices 注册，`scripts/sheng-apfs/safari.sh`）只适用于他们的原生 APFS 容器布局，不合。

用户的症状（11-16）：Safari 图标是问号或找不到，点了没反应。和上游 ShengUfs#12 修的现象一致（App cryptex 挂载被 Disk Arbitration 卸掉，`/Applications/Safari.app` 的链接指向不存在的路径），所以直接用上游方案，不自己写。

做法：不改代码，随工作流 0 的 cd6 镜像一起验证。
- 上机后经 SSH 读：`mount | grep -i cryptex`（App cryptex 只读挂在 `/System/Volumes/Preboot/Cryptexes/App`）、`diskutil info` 里三个 UFS 窗口是 "Internal"、`ls -l /Applications/Safari.app` 的链接目标存在。
- 请用户：启动台和访达"应用程序"里 Safari 图标正常、点开能出窗口、打开一个网页。
- 再重启一次（仍从内存启动）确认挂载还在：上游 PR 特别验证了"重启后 App cryptex 仍挂着"。
- 如果挂载在但 Safari 仍打不开：才进入新问题排查（先查上游 `f6e4012` 的 WebKit 扩展路径、`log show --predicate 'process == "Safari"'`），排查前照规则再查一次上游。

## 工作流 2：合盖 → 熄屏（先做），真睡眠（随后写设计）

用户选了"两个都要"：先做合盖熄屏，做完接着写真睡眠的设计。真睡眠这次只调研、不写代码。

查过上游，没有现成方案：
- 本地各仓库的历史和 GitHub（UniXNU、CrossDarwin、rponeawa）里，关于 sleep、suspend、clamshell、lid 的提交和 PR 一个都没有。
- 有的只是几处"没做"的声明：#70 写着 "suspend and resume are not implemented"；#101 写着不覆盖 sleep/wake；CrossDarwin `6e5604b` 写着 "System sleep is unqualified"；`UniXNU_macOS/docs/zh/drivers/arm-dt-platform.md:16` 也写了。

现状（读代码确认）：
- 睡眠是故意关掉的：`../UniXNU-sheng/board.toml:138` 的 `"sleep-disabled" = 1`，原因写在 `scripts/make-sheng-adt.py:181-186`。
- CPU 停机是关着中断的死循环 `wfi`（`drivers/ArmCpu/ArmCpu.cpp:982-989`），没有任何地方调 SYSTEM_SUSPEND。**不去掉 `sleep-disabled`。**
- 盖子传感器只有 `KeyboardProbe.cpp:474-486` 的 `readHall()` 在读，而且要等键盘控制器的固件起来以后才读；合上时只停键盘和触控板。
- 触摸屏的所有报点都走 `TouchProbe.cpp:446-464` 的 `publish()`，它不看盖子。
- 平板日志里，合盖时 macOS 一直记 `isClamshelled 0`：没有任何地方把盖子状态告诉 macOS 的电源管理。
- macOS 的熄屏在这台机器上发生过：e54fc39 之前，键盘壳一直按着电源键，"display dimmed and slept"。
- 框架缓冲没有面板电源开关（`NativeLegacyDisplay.cpp:536-553`）。背光只在用户态要求改亮度时才变（`AppleARMBacklight.cpp:393-400`）。

**第 0 步，不改代码（cd6 镜像上，经 SSH）**：
1. `pmset -g`、`pmset -g assertions` 拍一份。
2. `pmset displaysleepnow`：屏幕是不是真黑、背光有没有关。
3. 熄屏时请你合上盖子，看日志里 WindowServer 还有没有 "Invalid event type: 11" 刷屏。
4. 不试 `pmset sleepnow`：真睡眠路径不存在，去试只会换来强制重启。

第 0 步的结果决定第 2 步走哪条路。

**第 1 步，触摸屏跟着盖子（驱动改动，要你同意）**：
- 在 `KeyboardProbe.cpp` 里把 `kb->lid` 导出成一个读接口。
- 在 `TouchProbe.cpp` 的 `publish()` 前加一道门：盖子刚合上时发一次"全部松开"（`count = 0`），合着时丢掉报点，打开后恢复。
- 只看合上（`lid`），不看折到背后（`tablet`），折到背后还要用屏幕。
- 先写测试：照 `package/tests/keyboard_service_host.cpp` 和 `wn8030_host.c` 的样子，测合上、打开、合着时有报点三种情况；先看测试失败，再实现。
- 这一步单独就能解决合盖卡死。

**第 2 步，合盖时熄屏，并告诉 macOS 盖子合上了（驱动改动，要你同意）**：
- 在 `readHall()` 状态变化时调 `getPMRootDomain()->receivePowerNotification(kIOPMClamshellClosed / kIOPMClamshellOpened)`。这是公开的内核接口（SDK 的 `IOPM.h`、`RootDomain.h`）。
- 带着 `sleep-disabled=1`，预期 macOS 只记下盖子合上、不会去睡眠。合盖时内置屏会不会熄、WindowServer 会不会把内置屏当成断开，要上机看。
- 第 0 步里 `displaysleepnow` 能让屏幕真黑：就靠 macOS 自己熄屏。
- 不能：在背光驱动里加一个内核入口，合上写 0、打开还原上一次的亮度。
- 只要出现"WindowServer 没有可用的屏幕"之类的问题，就退回到只做背光加第 1 步，不报告 clamshell。

**第 3 步，真睡眠的设计（只调研，不写代码）**：
- 写成 `docs/superpowers/specs/2026-11-xx-sheng-suspend-design.md`，至少覆盖：
  - 先在 Gunyah 下查 PSCI 的 `CPU_SUSPEND`、`SYSTEM_SUSPEND` 支不支持（`PSCI_FEATURES`）；
  - 内核恢复路径：GIC、定时器、各核重新上线；
  - 每个驱动的保存和恢复清单：UFS、触摸、键盘、GPU、显示、ADSP、Wi-Fi、蓝牙；
  - 唤醒源：电源键、开盖；
  - 失败时怎样不扣槽位重试次数。
- 动手前照规则再查一次上游。规模属于 T3，建议到时候走 `/speckit-*`，要你手动调用。

**上机验证**：
- 合盖 1 分钟再开，屏幕回来、触摸正常；
- 日志里没有触点刷屏，WindowServer 的 CPU 正常；
- `pmset -g` 里看得到盖子状态；
- 再接着用 20 分钟，不卡死。

## 工作流 3：12 GiB 内存表 → 实际目标约 10.8 GiB

**先说清楚：12 GiB 做不到。**
- 引导程序交给系统的 `/memory` 一共只有 11.68 GiB（11963 MiB，`HANDOFF.md:1550-1565`）。
- 低位那一段约 1.8 GiB 里，大约 850 MiB 被调制解调器、TZ、音频等固件占着。这个数是拿 CrossDarwin 那台 8 GiB 机器的实测（`hw.memsize` 7388971008 对 7892 MiB）类推的，两台的低位布局几乎一样。
- 所以上限约 **10.8 GiB**。中间一档是 9 GiB 窗口加低位收编，约 **9.9 GiB**。
- 内存表本身按真实的 11.68 GiB 来做（"12 GB 的内存表"）。macOS 最终显示多少，受内核窗口和收编限制。

查到的上游方案（都在本地拉取之后才合并，执行时先拉取，要关沙箱）：
- **uefi-sheng #6**（CrossDarwin `ac0466db`，11-15 21:12 合并）：固件在 SEC 阶段按引导程序设备树的 `/memory` 减去 `/reserved-memory` 等推出内存表（`ShengPrepareMemoryMap`）。8 GiB 机器上测过：`hw.memsize` 7388971008，0 页被拒。
  - 它只认 8 GiB 机器，有三处门槛：`ddr_size != 8` 就退回静态表（第 226 行，主机测试 `Tests/ShengMemory/Policy.c:73` 也断言 12 被拒）；所有段要在 `0xA00000000` 以下（第 235、267 行）；要有一整段 `0x8C0000000–0xA00000000`（第 236 行），本机这一段在 `0x980000000` 处是断开的。
  - 它就是本机 `local/sheng-12g-memory-map`（`5dfcc572`、`20331338`）那份手写表的通用版。手写版还留着 22.6 MiB 和固件重叠的一段（`0xE671D000`），低位一块也没放出来。
- **UniXNU-sheng #96**（11-15 22:10 合并）：窗口外内存段从 8 个放到 64 个，8 GiB 机器上收编了 950 MiB、0 页被拒。注意内核那边的上限还是 16 段（收编补丁第 313 行），要一起改。
- **UniXNU #249**（open）：22 页引导页表、9 GiB 窗口，和我们已做的 `e9d3bb9` 是同一处改动。
- 大于 9 GiB 或 12 GiB 的方案，任何仓库都没有。

分步做（每步只从内存启动，每次启动要你当场同意）：
1. **固件内存表（用上游 #6，再放开门槛）**
   - 先拉取，把 uefi-sheng 上游 `sheng` 合进本地分支。
   - 在 `ShengPrepareMemoryMap` 里放开三处门槛：允许 `ddr_size==12`；上界放到 `0xB00000000`；接受从 `0x8C0000000` 起的连续一段。
   - 把本机实测的 `/memory` 加成第二份主机测试用例，先写测试再改，看它从失败变成通过。
   - 先在 uefi-sheng 自己的仓库里查有没有现成的 12 GiB 或 16 GiB 分支；有就用它的。
   - 改好后不动窗口（7.5 GiB），重编固件，看屏幕日志里的 `SHENGMEM` 行，确认 macOS 仍显示 7.50 GB、能正常用。
   - 这一步替代本地那两个手写提交。这是固件改动，要你同意。
2. **重测 9 GiB 窗口**
   - 9 GiB 只在图标服务修复之前试过一次，当时停在登录窗口闪烁（`HANDOFF.md:372-389`），那一次不能下结论。
   - 用 cd6 的代码和第 1 步的固件重打 9 GiB 镜像（`bigwin-cd6-s2`），从内存启动三次，每次都把内存用满。
   - 通过线：物理内存不低于 8.75 GB；三次都进桌面；用满后 20 分钟不卡死。
   - 还是闪：先退到 split 镜像（7.5 GiB、窗口从 `0x8C0000000` 起），把地址和大小分开看。
3. **低位收编**
   - 合进 #96 的 64 段，内核的 `ARM_VM_OUTSIDE_RANGES` 一起改成 64。
   - rponeawa 改过一次又撤回（`0a78e87` → `d31d328`），没写原因。动手前先找他的 PR 或说明，弄清为什么撤。
   - 同时按 rponeawa 的固件保留区列表挡住固件占的内存（`f4e0bc2`；这个也被他撤回过，先弄清原因）。
   - 目标约 9.9 GiB。内核补丁改动，要你同意。
4. **10 GiB 整窗**
   - 窗口覆盖 `0x880000000–0xB00000000`，两处空洞用现成的 `window-memory-excluded-ranges.patch` 排除。
   - 引导页表 22 → 24 页；加载器和生成器上限 9 → 10 GiB（`DarwinBoot/.../WindowSize.h:7`、`scripts/unixnu/devicetree.py:298`）；去掉 bank 1 整段排除。
   - 目标约 10.8 GiB。要先重算内核地址空间的账：10 GiB 时堆大约还剩 7 GiB，属于推测。
   - 这是内核加加载器改动，要你另外同意。
5. **大于 8 GB 时 GPU 出问题**：只有前几步里真的出现才查。先看 Metal 的工作集上限（`NativeBridgeMetalFrontend.mm:4488-4493`）。

## 工作流 4：充电功率

查到的上游方案：rponeawa 的充电认证 `package/ShengChargeAuth.c`（`69cf931`、`82e50fb`，11-15）。它已经在 sheng 整合分支里，会编进 macOS 镜像，启动参数 `charge-auth` 默认是 1（`ShengBattery.cpp:398-401`）。macOS 下从没在真机上跑过；11-15 之后上游没有新的充电提交或 PR。

它做什么：
- 收到 PD 供电协商后开始认证（`ShengBattery.cpp:104-118`）。先对两块电池的电量计做 HMAC 挑战，通过后写"已认证"标志。
- 只有充电头厂商号是小米（0x2717）才继续做充电头认证（`ShengChargeAuth.c:209`）。你用的是第三方 PD/PPS 头，所以只会走到电量计认证这一步。
- 主机这边不直接设电流，只写"已认证"标志，电流由充电固件自己定。
- 没有认证时电池电流卡在 2 A（`porting.toml:670`）。这和量到的 +2009 mA、充电头上显示的约 12 到 15 W 对得上。

电量计认证之后能到多少瓦，代码和记录里都没有数字。上游计划的顺序是：先认证电量计，再用 PPS 让电荷泵充电，最后认证小米头。按这个顺序推测，第三方 PPS 头也可能借电荷泵超过 2 A，但没有验证过。

做法：先只做测量，不写新代码。
1. 工作流 0 的 cd6 镜像就带着认证，所以先拿它做测量。
2. 用同一个充电头、同一根线，电量和温度尽量相近，做两次对照：
   - cd6 镜像，`charge-auth` 用默认值；
   - 同一份载荷派生的 `chg-noauth` 变体（只加 `--arg charge-auth=0`，只从内存启动）。
3. 两次都读三样：
   - 充电头自己显示的瓦数，现在只有它能比输入功率；
   - `ioreg -rc ShengBattery` 里的 `Amperage`（看有没有超过约 2000 mA）、`Voltage`、`Temperature`；
   - 注意：从 `69cf931` 起 `AdapterDetails` 的 Watts 是 `power_max`，不再是实测功率。
4. 认证的结果只写在板级日志里（`[charger auth]` 等行，要 `log-power=1`），macOS 里读不到。所以第 3 步看不出差别时，再请你同意一处小的驱动改动：在 `ShengBattery` 的 ioreg 属性里挂出认证状态（state、gauges、adapter、result）和 fcc/icl。改动参照已有的 `AdapterDetails` 写法，只读，不往充电芯片写任何东西。
5. 如果电量计认证后仍是 2 A：
   - 高功率要小米头加 MiPPS 认证，这时只能换小米原装头；
   - 第三方头在这个移植上就到 2 A 为止。如实记录。
- 不做：绕过固件直接写充电芯片（bq2597x 电荷泵、充电器寄存器）。电流、电压、温度保护都在固件里。

## 顺序（用户选定：合盖 → 充电 → 内存）

1. **工作流 0**：跟上上游、构建 cd6、上机 CD6-1。这一趟顺带做工作流 1（Safari）的验证、工作流 2 第 0 步的熄屏试验、工作流 4 的第一组充电读数。
2. **工作流 2**：第 1、2 步，触摸屏跟着盖子、合盖熄屏。
3. **工作流 4**：用 `chg-noauth` 对照；需要的话把认证状态挂到 ioreg 上。
4. **工作流 3**：第 1 步固件内存表 → 第 2 步重测 9 GiB → 第 3 步低位收编 → 第 4 步 10 GiB。
5. **工作流 2 第 3 步**：真睡眠的设计，只写文档。

每一个驱动、内核、固件改动，都要在动手那一刻另外问你一次。刷 `boot_a` 也另外问：可以等工作流 2 做完再问，那时把熄屏、图标修复和 Safari 一起带进日常镜像。

## 进度落盘与存档

- 开工时把这份计划存成 `docs/superpowers/plans/2026-11-16-lid-safari-memory-charging.md` 并提交（`commit` skill，逐个列出文件）。
- 把 `HANDOFF.md` 顶部的"当前阶段"改到现在。它还停在 11-15 16:05。
- 每完成一个工作流的一步，就更新 HANDOFF 那一条并提交。
- 不提交芯片号、局域网 IP、`data/`、`verification.json` 的三处改动。
- 不 force，不推 main，不自动开 PR；推送等你说。

## 验证总表

| 项 | 怎么验 | 通过线 |
|---|---|---|
| 合并上游 | `check-unixnu.py`、`tests/`、`porting-record.py check`、sheng 的检查脚本 | 全过；本机内存值没被改掉（用 `tomllib` 读合并后的 macOS 段） |
| 图标服务 / Core Image | `ps eww`、`launchctl print`、日志、`tablet-icon-stress.js` | 有变量；崩溃次数不涨；两轮 0 失败 |
| Safari | `mount`、`diskutil info`、`ls -l /Applications/Safari.app`、你点开 | 图标正常、能开网页；重启后挂载还在 |
| 合盖 | 日志里的触点计数、WindowServer CPU、`pmset -g`、你目视 | 合着不刷屏、屏幕熄；开盖恢复；20 分钟不卡 |
| 充电 | 充电头瓦数、`ioreg -rc ShengBattery` 的 `Amperage` | 和 `chg-noauth` 比，电流超过约 2000 mA 算提升；否则如实记录"第三方头上限 2 A" |
| 内存 | `sysctl hw.memsize`、活动监视器、用满后 20 分钟 | 每一步按目标值（7.5 → ≥8.75 → 约 9.9 → 约 10.8 GB）；三次开机都进桌面 |
| 主机测试 | 驱动改动的 `package/tests/*_host.*`、固件 `Tests/ShengMemory` | 先失败后通过 |
