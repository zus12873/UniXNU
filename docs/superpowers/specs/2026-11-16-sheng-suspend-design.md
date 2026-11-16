# sheng 上的 macOS 真睡眠：挂起到空闲（设计）

状态：用户 2026-11-16 选了"直接做真睡眠"（做法 B），随后批准本设计并要求实施（原话"忽略全局规则，按照当前方案设计实施"）。批准的范围包括本设计列出的 ArmCpu、sheng 包、背光和 XNU 板级补丁的改动；每次上机启动仍要用户当场同意，刷 `boot_a` 不在内。

## 要什么，为什么

- 用户的使用场景（原话）："合盖装包里几个小时，打开马上能用"。
- 现在合盖只是关背光、停触摸屏（cd11），系统照常运行：后台程序、网络、定时任务都在跑，耗电，在包里也会发热。
- 做成的标准：
  - 合盖后几秒内，macOS 进入系统睡眠：程序冻结，屏幕和背光熄灭，CPU 停下。
  - 开盖或按电源键，一两秒内回到睡前的桌面；Wi-Fi、键盘壳、触控板、触摸屏、显示、充电照常可用。
  - 合盖放 1 小时，耗电明显少于只关背光（数字在第 0 步量出基线后再定）。

## 目标、不做的、绝不能出现的

- 目标：
  - 合盖、菜单"睡眠"、空闲睡眠都走 macOS 自己的系统睡眠。
  - 用开盖或电源键唤醒。
  - 测试镜像里打开，日常镜像默认关闭。
- 不做：
  - 深度低功耗：DDR 自刷新、集群或整片 SoC 断电、高通 RPMh 的睡眠集。这一步是做法 C，以后单独设计；本设计只给它留接口。
  - 休眠到磁盘、定时唤醒（RTC）、Power Nap 式的后台唤醒、睡眠中保持 Wi-Fi 连接。
  - iPadOS 的睡眠。
- 绝不能出现的：
  - 睡死了只能强制重启。每次强制重启扣一次槽位 a 的次数，扣完会去槽位 b。所以测试时必须盯槽位，并且要有超时自动醒的保险。
  - 唤醒后数据损坏，或文件系统处于不一致状态。
  - 影响日常镜像：开关默认关闭。

## 约束

- 内核在高通的 Gunyah 虚拟机监控程序下运行：CPU 开关走 PSCI（`hvc`），中断控制器是 Gunyah 虚拟出来的 GICv3。Gunyah 会截获 WFI，把这个虚拟 CPU 挂起，直到有中断。
- XNU 是按开源的 BCM2837 机型配置编的（非 Apple 芯片家族），睡眠用到的 Apple 专用寄存器和热启动硬件都没有。
- 驱动、内核、固件的改动要用户同意。用户这次说"直接做"，同意的是本设计批准后的实现。
- 只从内存启动测试镜像；每次启动都要用户当场同意；不刷 `boot_a`。
- 每个问题动手前先查上游（2026-11-16 21:0x 查过：没有任何仓库、PR、issue 做过挂起或恢复）。

## 现状（已查清的事实）

- 睡眠被故意关掉：设备树 `/defaults` 有 `sleep-disabled = 1`。XNU 在开机完成时读它，置 `gSleepDisabledFlag`（`IOPMrootDomain.cpp:8502`），之后所有系统睡眠都被 `privateSleepSystem` 拒绝。cd8 的载荷设备树核对过。
- XNU 的睡眠路径（`iokit/Kernel/IOCPU.cpp` `IOCPUSleepKernel`）：
  1. 依次对每个非启动核调 `haltCPU()` 和 `processor_sleep()`。后者由调度器让那个核从自己的上下文进入 `cpu_sleep`。本配置没有 `USE_APPLEARMSMP`，`cpu_sleep`（cpu.c:320-365）只调 `PE_cpu_machine_quiesce` → CPU 驱动的 `quiesceCPU()`；它返回内核就 panic（"zombie processor"）。`ml_arm_sleep` 只有 Apple 的 `AppleARMSMP` 会调，本配置不会自己走到。
  2. 最后对启动核做同样的事。
  3. 启动核在 `ml_arm_sleep`（`osfmk/arm64/cpu.c:1056`）里等其他核都进入睡眠路径，记下 `wake_abstime`，然后调 `arm64_prepare_for_sleep(true)`。
- 这个配置下的 `arm64_prepare_for_sleep`（`machine_routines_asm.s` 的非 Apple 分支）是 `dsb; isb; wfi; b` 的死循环，没有恢复路径。现在真去睡就是一去不回。
- XNU 的 VM 平台有一条"睡完立刻恢复"的路：`ml_arm_sleep` 里 `test_sleep_in_vm` 时直接调 `arm_init_cpu(cpu_data_ptr, 0)`（cpu.c:1145-1152）。本配置 SPTM 关着（`NCONFIG_SPTM 0`），用的是 `osfmk/arm/arm_init.c:720` 的 `arm_init_cpu`，复位入口是 `start_cpu_paddr`（`cpu_sleep` 写进 `cpu_reset_handler`）。VM 那条路没编进去，但 `arm_init_cpu` 的唤醒分支在，`ml_arm_sleep` 也导出了（`Private.arm64.exports`）。
- CPU 驱动 ArmCpu（`drivers/ArmCpu/ArmCpu.cpp`）：
  - `haltCPU()` 在**调用它的那个核**上关计时器、关 Group 1 中断，然后死循环 WFI。睡眠时调用者是启动核，第一个非启动核的 `haltCPU()` 就会把启动核挂死。
  - `initCPU(boot=false)` 直接 panic（"secondary resume is unsupported" / "resume CPU startup is unsupported"）。唤醒后 XNU 会对启动核和每个重新启动的核以 `boot=false` 调它。
  - `startCPU` 用 PSCI `CPU_ON`，入口是内核的复位向量页（开机时多核就是这样起来的）。
  - 没有任何地方调 PSCI `CPU_OFF`。
  - 带 `diag=1` 时会问固件 PSCI_VERSION 和 CPU_SUSPEND 的 PSCI_FEATURES（`armcpu_psci[4]`），但没有记录过答案。
- 唤醒源的接线：
  - 盖子霍尔传感器 GPIO 171（低电平有效）、折到背后 GPIO 172、键盘控制器的帧中断 GPIO 62，都走 TLMM 的汇总中断 **SPI 208**（`KeyboardProbe.cpp` `kTlmmIntid`）。触摸屏的中断脚也在 TLMM 上。
  - 电源键：PMK8550 PON（SPMI SID 0，外设 0x13，中断 7）→ SPMI 仲裁器的 periph_irq → PDC 第 1 脚 → **SPI 481**（`ButtonProbe.cpp` 开头）。同一条线还汇集其他 PMIC 外设中断。
- 合盖今天的情况（cd9 实测）：
  - 驱动把 clamshell 发给根电源域，`AppleClamshellCausesSleep = Yes`，powerd 收到。
  - WindowServer 只把状态转给显示驱动，自己不关屏（Mac 上靠随后的系统睡眠关屏）。
- 显示睡眠今天的情况：WindowServer 关显示时给出一帧空帧，背光不灭（用户看到灰光）。显示驱动没有面板电源开关。
- 背光驱动 `AppleARMBacklight.cpp`（cd11 起）：盖子合着时写 0。

## 做法（用户选了 B）

- **A. 合盖关屏，系统照常跑。** 合盖走和自动熄屏同一条路，外加背光跟着显示电源走。没有睡死的风险，但后台照常跑，电掉得快、会温。用户不选。
- **B. 挂起到空闲（本设计）。** macOS 正常走完系统睡眠；到最后一步，非启动核用 PSCI `CPU_OFF` 真正关掉，启动核在关中断状态下 WFI，只等唤醒源；唤醒后从 `arm_init_cpu` 的唤醒分支恢复，再用 `CPU_ON` 开回其他核。不需要固件支持。比 A 省电、凉；风险在驱动睡醒后的状态。
- **C. 深度睡眠。** B 之上再让高通的电源子系统进入低功耗（RPMh 睡眠集、PDC 唤醒、集群断电），依赖 Gunyah 和固件，Linux 主线在这台平板上也还卡着。以后在 B 的等待循环里换成 PSCI `CPU_SUSPEND` 的深层状态，单独设计。

选 B 的原因：用户要真睡眠；B 不依赖固件，复用 XNU 自己的睡眠和唤醒流程，改动集中在 CPU 停止和恢复这一层。

## 设计

### 1. 开关

- 板级 XNU 补丁加启动参数 `platform-sleep=1`。只有它为 1、并且 CPU 驱动已经注册了平台睡眠钩子时，`gSleepDisabledFlag` 才清零；否则一切照旧（睡眠被拒）。
- 设备树里的 `sleep-disabled = 1` 不动，日常镜像不受影响。
- 测试镜像用 `make-payload-variant.py --arg platform-sleep=1` 打开。

### 2. 睡眠时序（打开之后）

1. 盖子合上 → `KeyboardProbe` 发 `kIOPMClamshellClosed`（已有）→ powerd 请求系统睡眠 → 根电源域开始睡眠流程：通知程序、冻结进程、文件系统同步、各驱动收到电源变化、WindowServer 关显示。
2. 背光：`AppleARMBacklight` 登记系统睡眠通知。收到 `kIOMessageSystemWillSleep` 就写 0，收到 `kIOMessageSystemHasPoweredOn` 就写回。（菜单"睡眠"时盖子开着，也要灭。）
3. `IOCPUSleepKernel`：
   - 对每个非启动核调 `haltCPU()`，新行为是只记下"准备睡眠"并返回。
   - `processor_sleep()` 让该核自己进入 `cpu_sleep` → `quiesceCPU()`。`quiesceCPU()` 在 `ml_is_quiescing()` 为真时调 `ml_arm_sleep()`（不返回），进入它的非启动核分支。补丁让这里调平台钩子 `platform_sleep(false)`：ArmCpu 关这个核的计时器和 Group 1 中断，然后 PSCI `CPU_OFF`。正常不返回；失败就记下错误码，退回原来的 WFI 死循环。
4. 启动核同样经 `cpu_sleep` → `quiesceCPU()` → `ml_arm_sleep()`，在里面等所有核都进了睡眠路径（原逻辑），记下 `wake_abstime`，然后补丁让它调平台钩子 `platform_sleep(true)`，即等唤醒（见第 3 节）。钩子返回后调 `arm_init_cpu(cpu_data_ptr, 0)`，走 XNU 自己的唤醒分支（同 VM 路径）。
5. 唤醒分支（`arm_init.c` 的 `arm_init_cpu`）：恢复启动核 → `PE_cpu_machine_init` → `ArmCpu::initCPU(boot=false)` → `IOCPUSleepKernel` 从 `processor_sleep(bootCPU)` 之后继续 → 对每个非启动核 `processor_wake()` → `ArmCpu::startCPU` → `CPU_ON`（这时那个核确实是关的）→ 那个核走复位向量 → `initCPU(boot=false)`。
6. 根电源域通知各驱动和程序唤醒，powerd 让 WindowServer 打开显示，背光写回。

### 3. 启动核等唤醒（ArmCpu，平台钩子 `platform_sleep(true)`）

在关中断（DAIF 全屏蔽）的状态下：

1. 保存 GIC 分发器所有 SPI 的使能位，然后只留唤醒源的 SPI：
   - SPI 208（TLMM 汇总，盖子）；
   - SPI 481（PDC/SPMI，电源键）；
   - 如果打开了"超时自动醒"，再留启动核的虚拟计时器 PPI。
2. 让板级代码准备唤醒源（板级回调 `prepare`，见第 4 节）。
3. 打开 CPU 接口的 Group 1（中断仍被 DAIF 屏蔽，不会进处理函数，只用来让 WFI 能醒）。
4. 循环：
   - `wfi`；
   - 读 `ICC_HPPIR1_EL1` 得到最高优先级的挂起中断号；
   - 交给板级回调 `should_wake(intid)` 判断是不是真的该醒；
   - 是就跳出；不是就由回调清掉那一路的来源，记一次"虚假唤醒"，继续循环。
5. 板级回调 `restore` 还原 TLMM 和 PMIC 的设置；GIC 的 SPI 使能还原成睡前的样子。挂起着的那个唤醒中断留着，唤醒后由原来的驱动正常处理：盖子驱动读到"开"，按键驱动读到"按下"。
6. 记下睡了多久、被谁叫醒、虚假唤醒几次，唤醒后打一行日志（等待循环里不能写日志）。

"超时自动醒"：启动参数 `platform-sleep-wake-after=秒`，默认不设。用来做无人值守的测试（例如 60 秒后自己醒），也是睡死时的保险。

### 4. 板级唤醒源（sheng 包，新增一个小文件，例如 `package/ShengSleep.cpp`，注册给 ArmCpu）

- `prepare`：
  - TLMM：保存所有被用作中断的脚的 `INTR_CFG` 使能位，只留盖子 GPIO 171 的使能。键盘帧 GPIO 62、折叠 GPIO 172、触摸屏等全部关掉，避免睡眠中被不停叫醒。
  - PMIC：电源键的中断本来就开着（ButtonProbe），其他 APID 不动。
- `should_wake(intid)`：
  - SPI 208：读 GPIO 171 的电平，盖子开着才醒；否则清 GPIO 171 的中断状态，继续睡（去抖的抖动）。
  - SPI 481：读 PON 的 RT_STS 第 7 位和锁存状态，电源键按过才醒；否则清掉触发的那个 APID，继续睡（充电器插拔等其他 PMIC 事件不叫醒）。
  - 叫醒系统的那一下电源键（按下和松开）**不传给 macOS**：macOS 把短按电源键当作"睡眠"，传过去会立刻又睡。由 `ButtonProbe` 在唤醒后吞掉这一次按下和随后的松开。（实现者的决定，审阅时提出。）
  - 计时器 PPI：超时到了，醒。
- `restore`：把 TLMM 各脚的使能写回。
- 判定和寄存器计算写成能在主机上测的纯函数（参照 `LidClamshell.h` 的做法）。寄存器读写留在 `.cpp` 里。

### 5. ArmCpu 的改动（核心仓库的组件 `drivers/ArmCpu`）

- `quiesceCPU()`：`ml_is_quiescing()` 为真（系统睡眠）时调 `ml_arm_sleep()`，不返回；否则保持原行为。

- `haltCPU()`：睡眠时只把状态记为 Stopped 并返回，不在调用者核上死循环。原来的停机行为（关机、单核停用时）保留成单独的路径。实现时先确认 `haltCPU` 在本内核里还有哪些调用者。
- `initCPU(boot=false)`：
  - 启动核：重新打开计时器、Group 1，`setCPUState(Running)`。不重新初始化分发器。
  - 非启动核：走和第一次启动相同的步骤（核对 MPIDR、唤醒重分发器、开 GIC、装中断处理、开计时器）。只做一次的部分（统计、首次标记）跳过。
- 新增平台睡眠钩子：
  - `platform_sleep(false)` → `CPU_OFF`（PSCI 0.2 函数号 0x84000002）；
  - `platform_sleep(true)` → 第 3 节的等待。
  - 由 ArmCpu 在启动时登记给补丁里的函数指针。
- 板级回调接口：ArmCpu 只提供"登记 prepare / should_wake / restore"的函数，具体板子由 sheng 包登记；没登记时只认计时器超时。
- 计数（导出变量，唤醒后由日志打出）：进入睡眠次数、各核 `CPU_OFF` 结果、等待循环次数、唤醒中断号、虚假唤醒数、睡眠时长。

### 6. XNU 板级补丁（`UniXNU-sheng/patches/xnu-12377/`，加进 `series`）

- `osfmk/arm64/cpu.c` `ml_arm_sleep`：在调 `arm64_prepare_for_sleep` 之前，如果平台钩子已登记：
  - 非启动核调 `platform_sleep(false)`；
  - 启动核调 `platform_sleep(true)`，返回后调 `arm_init_cpu(cpu_data_ptr, 0)`。
  - 没登记就照旧。
- `IOPMrootDomain.cpp` 读 `sleep-disabled` 的地方：`platform-sleep=1` 并且钩子已登记时清零 `gSleepDisabledFlag`，并记一行日志。
- 钩子用一个全局函数指针，名字带平台前缀，不和 Apple 的符号冲突。

### 7. 各驱动在睡眠前后

逐项上机核对。下面是预期和要看的东西：

| 部分 | 预期 | 要看的 |
|---|---|---|
| 显示 | WindowServer 睡前关显示，醒后打开 | 醒后画面正常、不卡 |
| 背光 | 睡眠通知写 0，醒后写回（第 2 步） | 睡时无灰光 |
| 触摸屏 | 盖子合着已被门挡住；睡眠中 TLMM 脚被关 | 醒后能触摸 |
| 键盘壳 | 睡眠中帧中断被关；醒后 keepalive 过期，立即读一次；背光在盖子合着时已灭 | 醒后按键、触控板可用；有没有被当成掉线 |
| Wi-Fi | airportd 睡前断开或关电，醒后重新连 | 醒后能连上；自动连接本来就有问题（隐藏网络），手动连也算过 |
| UFS 存储 | 睡前 macOS 同步完文件系统；睡眠中没有 I/O；主控不断电 | 醒后读写正常，日志无 I/O 超时 |
| GPU | 空闲；醒后它的计时器看到时间跳了一大段 | 醒后没有误判 GPU 卡死、没有恢复风暴 |
| 电池、充电（ADSP） | 独立处理器，照常运行 | 醒后电量、充电读数正常 |
| 蓝牙、音频 | 睡前由系统停用 | 醒后可用 |
| 计时 | 计数器一直在走，醒后系统时间正确 | `date`、日志时间连续 |

- 没有登记电源管理的驱动，睡眠中不会收到通知，它们的线程也不会运行（所有核都停了），中断被关在分发器那里。醒来时一次补上积压的中断。
- 假设：Gunyah 的看门狗在本机没有接管（固件里没有 uefi-sheng #7）。实现前核对一次；如果有，就要在等待循环里处理。

### 8. 诊断，以及出错时怎么办

- 睡前、睡后各打一行内核日志：进入时间；各核关掉的结果；醒来的原因和中断号；睡了多少秒；虚假唤醒次数。SSH 里 `log show --predicate 'eventMessage CONTAINS "sheng sleep"'` 就能读。
- 睡死时没法从 macOS 读日志：板级日志会写进 UFS 的日志窗口，可以用 Linux 日志启动（`package/linux-log`）读出来。补丁在每个阶段写板级检查点。
- 测试时启动参数默认带 `platform-sleep-wake-after=60`，即便唤醒源判定有问题，60 秒后也会自己醒。

### 9. 测试

- 主机测试，先写测试、看它失败再实现：
  - 唤醒判定：盖子电平、电源键状态、中断号 → 醒或继续，以及要清哪一路；
  - GIC 使能位的保存、筛选、还原；
  - TLMM 使能位的保存、只留 171、还原。
- 编译：ArmCpu 和 sheng 新文件用构建的内核参数编过；补丁在 `xnu-work` 上能打上。
- 上机，逐级进行，每级都只从内存启动，每次启动都要用户同意：
  1. `pmset sleepnow`，配 60 秒自动醒：看能不能醒、醒后 SSH 能连、桌面正常，读睡眠日志。
  2. 同上，用电源键唤醒。
  3. 合盖睡、开盖醒。
  4. 连续 10 次睡醒，看有没有越来越差。
  5. 拔掉充电器合盖 1 小时（和只关背光的 A 对照），量电量和温度。
- 每一级都先在 fastboot 里读槽位次数，不够就补。

## 风险和未知

- Gunyah 的虚拟 GIC：分发器的使能位筛选、关中断下 WFI 的唤醒、`ICC_HPPIR1_EL1` 的读法，都要在真机上验证。第 1 级测试就能看出来。
- 直接从 `ml_arm_sleep` 调 `arm_init_cpu`（非 SPTM 版，`osfmk/arm/arm_init.c:720`）是否完整；VM 平台用过，但不是这个配置。补丁实现前通读它的唤醒分支。
- 非启动核 `CPU_OFF` 之后再 `CPU_ON`：开机时已经走过 `CPU_ON` 的复位路径，但"关掉再开"没走过。
- 某个驱动醒后状态错乱（GPU 最可疑）。
- powerd 在醒后可能马上又要睡（盖子还合着时被电源键叫醒）：这是 macOS 正常行为，记录即可。
- 睡眠被某个断言挡住：用 `pmset -g assertions` 查。

## 交付顺序

1. 第 0 步，量基线：cd11（合盖只关背光）拔电合盖 1 小时的耗电和温度。不改代码。
2. ArmCpu：`haltCPU` 只做准备、`initCPU` 支持恢复、`CPU_OFF`、等待循环和钩子。先写主机测试。
3. sheng：板级唤醒源回调和背光的睡眠通知。先写主机测试。
4. XNU 板级补丁和 `platform-sleep` 开关。
5. 构建测试镜像，按第 9 节逐级上机。
6. 稳定之后，再决定日常镜像要不要打开，以及要不要往 C 走。

## 留给实现的

- 钩子和回调的具体名字、计数的布局、日志的措辞。
- ArmCpu 改动先在核心仓库的分支上做，和 sheng 的改动一起测；要不要提给上游，等上机稳定后再问用户。
- `haltCPU` 的原停机行为保留在哪条路径上，看完调用者再定。
