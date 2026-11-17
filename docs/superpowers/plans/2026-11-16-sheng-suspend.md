# sheng macOS 挂起到空闲：实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** macOS 在 sheng 上能进入系统睡眠（挂起到空闲），开盖或按电源键一两秒内醒回原来的桌面。

**Architecture：** XNU 板级补丁在 `ml_arm_sleep` 里调一个平台钩子：非启动核由 ArmCpu 用 PSCI `CPU_OFF` 关掉；启动核在关中断状态下只留唤醒源的 SPI，WFI 等待，由 sheng 板级回调判定真唤醒；返回后走 `arm_init_cpu(cpu_data_ptr, 0)` 的唤醒分支，再 `CPU_ON` 开回副核。启动参数 `platform-sleep=1` 才清掉 `gSleepDisabledFlag`；默认一切照旧。

**Tech Stack：** XNU（xnu-12377，BCM2837 配置，SPTM 关着，用 `osfmk/arm/arm_init.c` 的 `arm_init_cpu`）、IOKit C++、GICv3（Gunyah 虚拟）、PSCI 0.2、主机测试用 C11/C++17 + ASan/UBSan。

**Spec：** `docs/superpowers/specs/2026-11-16-sheng-suspend-design.md`

## Global Constraints

- 启动参数：`platform-sleep=1` 打开；`platform-sleep-wake-after=<秒>` 超时自动醒（不设就不超时）。测试镜像默认带 `platform-sleep-wake-after=60`。
- 设备树 `/defaults/sleep-disabled = 1` 不改；日常镜像（`out/flash/boot-v4-flash.prev.img`、日常的 `kernel.macho` `33d294c8`、`payload.img` `8a36fe56`）不碰。
- XNU 钩子：`void (*arm64_platform_sleep_hook)(boolean_t boot_cpu)`，定义在 `osfmk/arm64/cpu.c`，初值 `NULL`。
- ArmCpu 对外：`extern "C" int armcpu_sleep_register(const struct armcpu_sleep_board *board)`（结构见 Task 1）。sheng 侧按现有做法本地声明并 `weak_import`。
- 唤醒源 SPI：208（TLMM 汇总，盖子 GPIO 171），481（PDC/SPMI，电源键）。PSCI：`CPU_OFF` = 0x84000002。
- 日志前缀：`armcpu sleep:`（ArmCpu）、`sheng sleep:`（板级）。等待循环里不写日志，唤醒后补打。
- 每次上机只从内存启动，要用户当场同意；fastboot 里先读两个槽位，a ≤4 就 `fastboot set_active a`。
- 不提交芯片号、`data/`、`scripts/policies/*` 的本机改动；不用 `git add .`/`-A`；不 amend、不 force push；推送等用户说。
- porting.toml 只写现在的行为，不写日期和测试记录。

## Review Focus

1. 睡眠中不是唤醒源的中断不停到来（键盘帧 GPIO 62 是电平中断、触摸屏报点、充电器插拔的 PMIC 事件）：应当被关掉或判为虚假唤醒后继续睡，而不是忙等或醒来。→ Task 1、Task 4 的测试。
2. 电源键在睡前已按着、或唤醒时按得很短：唤醒判定读的是 PON 实时状态，短按可能读到"未按"。要以锁存状态为准，并且不清掉它。→ Task 4 测试 `power_latched_counts_as_pressed`。
3. 盖子在进入等待前就已经打开（合盖后马上开盖）：等待循环开始时就该醒，不能等下一个边沿。→ Task 4 测试 `lid_open_before_wait_wakes_at_once`。
4. 一次睡醒后再睡：所有保存和还原的状态（GIC 使能、TLMM 使能、计数）第二次也要对。→ Task 1、Task 4 的"两轮"测试。
5. 超时自动醒和真唤醒同时发生：以真唤醒为准，原因记录不能丢。→ Task 1 测试 `timer_and_wake_source_prefers_source`。

---

### Task 1：ArmCpu 睡眠逻辑（纯函数头文件 + 主机测试）

**Files:**
- Create: `drivers/ArmCpu/ArmCpuSleep.h`
- Create: `drivers/ArmCpu/tests/armcpu_sleep_host.c`
- Create: `drivers/ArmCpu/tools/check-sleep-host.py`（照 sheng `scripts/check-lid-clamshell-host.py` 的样子：`cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined`，失败时打印 `FAIL`）

**Interfaces:**
- Produces（`ArmCpuSleep.h`，C 头文件，C++ 可包含）：
  - `#define ARMCPU_SLEEP_SPI_WORDS 32u`（GICD_ISENABLER 1..31 覆盖 SPI 32..1019，下标 0 不用）
  - `struct armcpu_sleep_board { void (*prepare)(void); int (*should_wake)(uint32_t intid); void (*restore)(void); const uint32_t *wake_spis; uint32_t wake_spi_count; };`
  - `void armcpu_sleep_keep(const uint32_t saved[ARMCPU_SLEEP_SPI_WORDS], const uint32_t *wake_spis, uint32_t count, uint32_t keep[ARMCPU_SLEEP_SPI_WORDS])`：只留睡前已使能、且在唤醒表里的位。
  - `enum armcpu_wake_reason {ArmcpuWakeNone, ArmcpuWakeSource, ArmcpuWakeTimer};`
  - `enum armcpu_wake_reason armcpu_sleep_decide(uint32_t intid, int board_says_wake, uint32_t timer_intid)`：`intid` 是 `ICC_HPPIR1_EL1` 读出的号（1023 表示没有）；板级说醒 → Source；是计时器号 → Timer；否则 None。
  - `struct armcpu_sleep_stats { uint32_t phase, entries, spurious, last_intid, last_reason, cpu_off_failures; uint64_t asleep_ticks; };`
    `phase`：1 进钩子，2 副核都已关，3 在等，4 醒了，5 还原完。睡死时板级日志里能看到停在哪一步。

- [ ] **Step 1：写失败的测试** `drivers/ArmCpu/tests/armcpu_sleep_host.c`：
  - `keep_only_enabled_wake_spis`：saved 里 SPI 208、481、300 使能，唤醒表 {208, 481, 500} → keep 只有 208、481。
  - `keep_ignores_out_of_range`：唤醒表里有 31、1020 → 不越界、不置位。
  - `decide_board_wake` / `decide_timer` / `decide_none_1023`。
  - `timer_and_wake_source_prefers_source`：同一个 intid 既是计时器号、板级又说醒 → Source。
  - `two_rounds_same_result`：同样的输入连跑两次 keep，结果一致、saved 不被改。
- [ ] **Step 2：运行确认失败**：`python3 tools/check-sleep-host.py` → 编译失败（头文件不存在）。先放只返回 0 的桩，确认是断言失败。
- [ ] **Step 3：实现** `ArmCpuSleep.h` 里的两个 `static inline` 函数和类型。
- [ ] **Step 4：运行确认通过**：`python3 tools/check-sleep-host.py` → `PASS`。
- [ ] **Step 5：提交**（ArmCpu 仓库，分支 `local/platform-sleep`，从 `acba4ee` 开）：`git add ArmCpuSleep.h tests/armcpu_sleep_host.c tools/check-sleep-host.py`。

### Task 2：ArmCpu 驱动：停核、恢复、等唤醒、钩子

**Files:**
- Modify: `drivers/ArmCpu/ArmCpu.cpp`（`haltCPU` 982-990、`initCPU` 686-727、`quiesceCPU` 973-980；新增睡眠函数和登记）。本配置没有 `USE_APPLEARMSMP`：`cpu_sleep` 只调 `quiesceCPU`，它返回就 panic（"zombie processor"）。
- Modify: `drivers/ArmCpu/README.md`（描述现在的行为和两个启动参数）

**Interfaces:**
- Consumes：Task 1 的 `ArmCpuSleep.h`。XNU 补丁（Task 3）提供的 `extern "C" void (*arm64_platform_sleep_hook)(boolean_t);`。
- Produces：
  - `extern "C" int armcpu_sleep_register(const struct armcpu_sleep_board *board)`：返回 0 成功；`platform-sleep` 不是 1 时返回 `KERN_NOT_SUPPORTED`，并且不登记钩子。
  - `extern "C" volatile struct armcpu_sleep_stats armcpu_sleep_stats;`
  - 钩子函数 `static void armcpuPlatformSleep(boolean_t bootCpu)`，在 `ArmCpu::start`（启动核）里、`platform-sleep=1` 时登记给 `arm64_platform_sleep_hook`。

- [ ] **Step 1：`haltCPU`**：`kIOCPUStateStopped` 记下即返回（不关中断、不死循环）。先 `grep -rn haltCPU` 核对 xnu-work 里的调用者；只有 `IOCPUSleepKernel` 的话，原死循环删掉；有别的调用者就保留成 `parkSelf()` 给那条路径。
- [ ] **Step 1b：`quiesceCPU()`**：`ml_is_quiescing()` 为真时，关计时器后调 `ml_arm_sleep()`（`extern "C" void ml_arm_sleep(void) __attribute__((noreturn));`，已导出），不返回；否则保持原行为（`diagnosePower` 的 panic 只在非睡眠时保留）。
- [ ] **Step 2：`initCPU(boot=false)`**：
  - 启动核：`enableGic()` 只开本核接口和 Group 1，`enableCPUTimeBase(true)`，`setCPUState(kIOCPUStateRunning)`，不调 `initDistributor`。
  - 副核：走第一次启动的同一组步骤（`wakeRedistributor(true)`、`enableGic()`、`ml_install_interrupt_handler`、计时器、Running），`armcpu_smp_running` 不重复加。
  - 去掉两处 `panic`。
- [ ] **Step 3：非启动核的钩子分支**：关计时器、`icc_igrpen1_el1 = 0`，然后 `psciCall(hvc, 0x84000002, 0, 0, 0)`。不另外清缓存：`ml_arm_sleep` 已清过本核的 cpu_data，PSCI 规范要求 `CPU_OFF` 自己做关核所需的缓存维护。返回即失败：`cpu_off_failures++`，然后原 `wfi` 死循环。
- [ ] **Step 4：启动核的钩子分支（等唤醒）**，DAIF 全屏蔽下：
  1. 读 GICD_ISENABLER1..31 存进 `saved`；`armcpu_sleep_keep` 算出 `keep`；先写 ICENABLER 关掉全部，再写 ISENABLER 打开 `keep`。
  2. `board->prepare()`。
  3. `platform-sleep-wake-after` 有值时：设虚拟计时器 `cntv_tval_el0` 到那个时长、`cntv_ctl_el0 = 1`，计时器 PPI 号记为 `timer_intid`（虚拟计时器 PPI 27）。
  4. `icc_igrpen1_el1 = 1`，`phase = 3`；循环：
     - `dsb sy; wfi`；读 `ICC_HPPIR1_EL1` 得 `intid`；
     - `intid` 在唤醒表里时 `says = board->should_wake(intid)`，否则 `says = 0`；
     - `armcpu_sleep_decide(intid, says, timer_intid)`；
     - None：`intid` 是 SPI 时写 ICPENDR 清掉它的挂起，`spurious++`，继续；Source 或 Timer：跳出，`phase = 4`。
  5. `icc_igrpen1_el1 = 0`、计时器关；`board->restore()`；ICENABLER 全关后按 `saved` 写回 ISENABLER。挂起着的唤醒中断不清。
  6. 记 `last_intid`、`last_reason`、`asleep_ticks`，`entries++`。
  - 没登记板级时，只认计时器；计时器也没设，就记一次错误并立即返回（等于不睡，避免挂死）。
- [ ] **Step 5：唤醒后的日志**：（取舍见 ledger）不在 `initCPU` 里打，改由 Task 4 的睡醒通知打 `sheng sleep: woke by …`，带上 `armcpu_sleep_stats`。
- [ ] **Step 6：编译**：用构建树的内核参数单独编 `ArmCpu.cpp`（同 KeyboardCover 的做法：从 `IOPlatformExpert.cpo.json` 取参数，替换源文件，`-o` 到 scratchpad），rc 0，`nm` 里有 `_armcpu_sleep_register`、引用 `_arm64_platform_sleep_hook`。
- [ ] **Step 7：主机测试仍通过**：`python3 tools/check-sleep-host.py` → PASS。
- [ ] **Step 8：提交**（ArmCpu 仓库 `local/platform-sleep`）：`git add ArmCpu.cpp README.md`；然后核心仓库整合分支 `git add drivers/ArmCpu` 提交 gitlink（构建按 gitlink 取代码）。

### Task 3：XNU 板级补丁 `sheng-platform-sleep.patch`

**Files:**
- Create: `UniXNU-sheng/patches/xnu-12377/sheng-platform-sleep.patch`
- Modify: `UniXNU-sheng/patches/xnu-12377/series`（加在 `zzye-sheng-cpu-idle.patch` 之后）
- Modify: `UniXNU-sheng/porting.toml`（power 或 cpu 所属区的 findings 和 paths）

**Interfaces:**
- Produces：`void (*arm64_platform_sleep_hook)(boolean_t boot_cpu) = NULL;`（`osfmk/arm64/cpu.c`，并在 `osfmk/arm/machine_cpu.h` 声明）。

- [ ] **Step 1**：在 `xnu-work` 的副本里改：
  - `ml_arm_sleep`：启动核分支在 `arm64_prepare_for_sleep(true)` 前 `if (arm64_platform_sleep_hook) { arm64_platform_sleep_hook(TRUE); arm_init_cpu(cpu_data_ptr, 0); }`；非启动核分支在 `arm64_prepare_for_sleep` 前 `if (arm64_platform_sleep_hook) arm64_platform_sleep_hook(FALSE);`。
  - `IOPMrootDomain.cpp` 读 `sleep-disabled` 之后：`gSleepDisabledFlag` 非 0、`arm64_platform_sleep_hook` 非空、启动参数 `platform-sleep` 为 1 → 清零并 `IOLog("PMRD: sleep enabled by platform-sleep\n")`。
- [ ] **Step 2**：先通读 `osfmk/arm/arm_init.c:720` 的 `arm_init_cpu` 唤醒分支（本配置 SPTM 关着，复位入口是 `start_cpu_paddr`），确认在 MMU 已开、从 `ml_arm_sleep` 直接调用时不会重复做只在复位时才做的初始化；有就加条件跳过，写进补丁注释。
- [ ] **Step 3**：用 `git diff` 生成补丁；在干净的 `xnu-work` 副本上 `git apply --check`，并照 `series` 顺序整体应用一次确认不冲突。
- [ ] **Step 4**：porting.toml 记现在的行为；`python3 -I -B scripts/porting-record.py check --device ../UniXNU-sheng --base upstream/main` → PASS。
- [ ] **Step 5：提交**（sheng 整合分支）：`git add patches/xnu-12377/sheng-platform-sleep.patch patches/xnu-12377/series porting.toml`。

### Task 4：sheng 板级唤醒源

**Files:**
- Create: `UniXNU-sheng/package/ShengSleep.h`（纯函数）
- Create: `UniXNU-sheng/package/ShengSleep.cpp`（寄存器读写、登记、睡醒通知）
- Create: `UniXNU-sheng/package/tests/sheng_sleep_host.c`、`UniXNU-sheng/scripts/check-sheng-sleep-host.py`
- Modify: `UniXNU-sheng/package/ButtonProbe.cpp`（导出睡眠时的电源键检查）
- Modify: `UniXNU-sheng/package/LegacyDisplayProbe.cpp:639` 之后加 `if (sheng_sleep_probe) sheng_sleep_probe();`（`weak_import` 声明）
- Modify: `UniXNU-sheng/scripts/build-gop-legacy-display-27.py`（board_objects 列表加 `('ShengSleep', ())`，键盘源文件表加 `ShengSleep.h`）
- Modify: `UniXNU-sheng/porting.toml`（paths 和 findings）

**Interfaces:**
- Consumes：Task 2 的 `armcpu_sleep_register` 和 `struct armcpu_sleep_board`（sheng 侧本地声明同样的布局，`weak_import`）。
- Produces：
  - `ShengSleep.h`：
    - `#define SHENG_SLEEP_GPIO_COUNT 210u`、`#define SHENG_SLEEP_LID_GPIO 171u`
    - `void sheng_sleep_tlmm_keep(const uint32_t cfg[SHENG_SLEEP_GPIO_COUNT], uint32_t out[SHENG_SLEEP_GPIO_COUNT])`：除盖子脚外清掉 INTR_CFG 第 0 位（使能），其余位不动；盖子脚原样。
    - `int sheng_sleep_lid_wakes(uint32_t lid_io)`：IO 寄存器第 0 位是电平，低电平为合上 → 高电平（开）返回 1。
    - `int sheng_sleep_power_wakes(uint8_t rt_sts, uint8_t latched)`：第 7 位任一为 1 → 1。
  - `ButtonProbe.cpp`：`extern "C" int sheng_buttons_sleep_check(void)`：读 PON 的 RT_STS 和锁存状态，返回电源键是否按过；把别的 APID 的中断清掉（同 `buttonsIrq` 的做法）。叫醒系统的那次按下和松开不报给 macOS：它返回 1 时置 `gSwallowPower`，唤醒后的线程第一次看到电源键按下和随后的松开时不发 HID 报文，然后清掉标志。
  - 测试：`ShengSleep.h` 里加 `int sheng_sleep_swallow(int *pending, int pressed)`：pending 时吞掉按下和随后的松开，之后照常；主机测试 `wake_press_and_release_swallowed`、`next_press_reported`。
  - `ShengSleep.cpp`：`extern "C" void sheng_sleep_probe(void)`：映射 TLMM 的 0..209 脚（`TB_TLMM_BASE`、步长 `TB_GPIO_STRIDE`），`platform-sleep=1` 时向 ArmCpu 登记 {prepare, should_wake, restore, {208, 481}}，并登记系统睡醒通知：唤醒原因是盖子或电源键时 `getPMRootDomain()->requestUserActive(...)`，避免停在 dark wake。

- [ ] **Step 1：写失败的测试** `sheng_sleep_host.c`：
  - `tlmm_keep_only_lid`：210 个 cfg 全部带使能位 → out 里只有 171 有使能，其他位（极性、检测方式）不变。
  - `tlmm_two_rounds`：同输入跑两次结果一致，输入不被改。
  - `lid_open_wakes` / `lid_closed_sleeps`。
  - `lid_open_before_wait_wakes_at_once`：进入等待前盖子已开（IO=1）→ 1。
  - `power_pressed_wakes`、`power_latched_counts_as_pressed`（RT=0、锁存=0x80 → 1）、`power_idle_sleeps`。
- [ ] **Step 2：运行确认失败**：`python3 scripts/check-sheng-sleep-host.py` → 先桩后看到断言失败。
- [ ] **Step 3：实现** `ShengSleep.h`。
- [ ] **Step 4：运行确认通过**。
- [ ] **Step 5：实现** `ShengSleep.cpp` 和 `ButtonProbe.cpp` 的导出：
  - `prepare` 读出 210 个 INTR_CFG 存起来，写回 `sheng_sleep_tlmm_keep` 的结果。
  - `should_wake(intid)`：208 → 读 171 的 IO，`sheng_sleep_lid_wakes`；为 0 时清 171 的 INTR_STATUS。481 → `sheng_buttons_sleep_check()`。
  - `restore`：写回保存的 INTR_CFG。
  - 唤醒原因存在一个全局里，供睡醒通知用。
  - 睡醒通知里打一行 `sheng sleep: woke by lid|power|timer`。
- [ ] **Step 6：编译**：`ShengSleep.cpp`、`ButtonProbe.cpp`、`LegacyDisplayProbe.cpp` 用 `build-gop-legacy-display-27.py` 的板级参数编过（同 KeyboardProbe 的做法）。
- [ ] **Step 7**：porting.toml 记现在的行为、加 paths；记录检查 PASS；其他已有主机检查（lid clamshell、keyboard、wn8030）仍 PASS。
- [ ] **Step 8：提交**（sheng 整合分支，逐个列出文件）。

### Task 5：睡眠时关背光

**Files:**
- Modify: `UniXNU-sheng/package/LidClamshell.h`（新增 `static inline bool lid_backlight_dark(bool lid_closed, bool asleep)`；`lid_backlight_level` 不变）
- Modify: `UniXNU-sheng/package/tests/lid_clamshell_host.c`
- Modify: `UniXNU-sheng/package/AppleARMBacklight.cpp`

**Interfaces:**
- Consumes：cd11 已有的 `gLidClosed`、`gLidTimer`、`setLevel`、`lid_backlight_level`。
- Produces：`volatile uint32_t gSystemAsleep`；`setLevel` 写 `lid_backlight_level(value, lid_backlight_dark(gLidClosed, gSystemAsleep))`；背光服务登记 `registerPrioritySleepWakeInterest`：`kIOMessageSystemWillSleep` → 置位、给 `gLidTimer` 设 1 µs；`kIOMessageSystemHasPoweredOn` → 清零、同样设定时器。

- [ ] **Step 1：写失败的测试** `backlight_dark_table`：`lid_backlight_dark` 四种组合 (0,0)→0、(1,0)→1、(0,1)→1、(1,1)→1；`asleep_darkens_even_with_lid_open`：`lid_backlight_level(1500, lid_backlight_dark(0, 1)) == 0`。
- [ ] **Step 2：确认失败；Step 3：实现；Step 4：确认通过**（`check-lid-clamshell-host.py`）。
- [ ] **Step 5**：AppleARMBacklight 登记睡醒通知，处理函数只置标志、给 `gLidTimer` 设 1 µs（不在通知里等工作循环）；在 `kIOMessageSystemWillSleep` 里 `acknowledgeSleepWakeNotification`。用板级参数编过。
- [ ] **Step 6**：porting.toml display 区更新；记录检查 PASS；提交。

### Task 6：构建测试镜像并逐级上机

**Files:** 无代码；进度写 `HANDOFF.md`。

- [ ] **Step 1**：用户在自己的终端里 `sudo -v && ./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr`。之前我核对日常文件哈希、只读挂 OS 镜像。
- [ ] **Step 2**：确认内核里有 `armcpu sleep:`、`sheng sleep:` 字符串和 `_arm64_platform_sleep_hook`；另存产物（`.cdN-<哈希>`），还原日常文件，`record-build-provenance.py`。
- [ ] **Step 3**：`make-payload-variant.py ... --arg enable-jobs=com.openssh.sshd --arg log-gpu=1 --arg keyboard-backlight=50 --arg platform-sleep=1 --arg platform-sleep-wake-after=60 --arg darkwake=1`（`darkwake=1`：DEVELOPMENT 内核上每次唤醒都直接是完整唤醒，见审查 Critical 2），打 v4 镜像，`bootimg-contents.py --payload` 核对；参数行不超过 1000 字节。
- [ ] **Step 3b**：请用户在平板上关掉空闲睡眠（用户 2026-11-16 定的）：`sudo pmset -a sleep 0`（Data 盘上，重启后仍在）；SSH 里 `pmset -g | grep -E '^ *sleep'` 应为 0。
- [ ] **Step 4：第 1 级**（用户同意后从内存启动）：SSH 里 `pmset sleepnow`，期望 60 秒后醒、SSH 重连、`log show` 有 `sheng sleep: sleeping …; wakes by lid yes, power key yes` 和 `sheng sleep: woke by timer`；`pmset -g log | tail` 看到 Sleep/Wake；记下 `spurious`、`masked`、`ticks`、`cpu_off failures`（应为 0）。醒不来：等 3 分钟，请用户长按电源键重启，进 fastboot 读槽位，再用 Linux 日志启动读板级日志。
- [ ] **Step 5：第 2 级**：`pmset sleepnow` 后按电源键，期望醒并且显示打开（不是 dark wake）。
- [ ] **Step 6：第 3 级**：合盖，`log` 里看到睡眠；开盖醒。
- [ ] **Step 7：第 4 级**：连续 10 次睡醒；每次后检查 Wi-Fi、键盘壳、触控板、触摸、显示、`ioreg -rc ShengBattery`、GPU 恢复计数。
- [ ] **Step 8：第 5 级**：拔掉充电器合盖 1 小时，记电量和温度，和第 0 步（cd11 只关背光）对比。
- [ ] **Step 9：睡眠中充电**：接着充电器合盖睡 30 分钟，前后读 `CurrentCapacity`、`Amperage`；电量不升，说明睡眠中不充电，记进 HANDOFF，交给用户决定要不要加"插着电不睡"。

### Task 0（随时可做，不依赖代码）：耗电基线

- [ ] cd11 构建并打 `cd11-s2`（9 GiB、`keyboard-backlight=50`），上机；拔掉充电器、合盖 1 小时，前后读 `ioreg -rc ShengBattery` 的 `CurrentCapacity`、`Voltage`、`Temperature`，记进 HANDOFF。
