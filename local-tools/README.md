# sheng 12 GiB：构建并测试 macOS 27.3 启动镜像

这份说明写的是小米平板 6S Pro（sheng，SM8550）12 GiB 内存这台机器上，从源码构建 macOS 27.3（profile `macos-27.3-26C5035r`）、
做试验启动镜像、只从内存启动测试、再把验证过的镜像刷进 `boot_a` 的做法。通用流程以上游文档为准，这里只写这台机器上不同的地方和这套试验方法：

- `docs/zh/porting/macos.md`：macOS profile 的输入、Data 种子、构建和检查点
- `docs/zh/building.md`：`unixnu` 的命令、选项和输出目录
- `docs/zh/guide/requirements.md`：主机工具和外部输入
- `docs/zh/guide/boot.md`：fastboot 刷写、启动菜单、恢复
- `docs/zh/devices/models/sheng-macos.md`：sheng 上 macOS 各子系统的实现

本目录里每个脚本开头都写了用法和它拒绝做的事，下面只给常用的写法。

## 1. 源码和分支

三个仓库并排放在同一个目录下，相对路径是构建约定的，不要挪动：

| 目录 | 分支 | 说明 |
| --- | --- | --- |
| `UniXNU/` | `integrate/upstream-20261116` | 上游 main 加本机的改动：9 GiB 窗口的生成器、22 页的引导页表、窗口外内存收编、构建修复和本目录的工具 |
| `UniXNU-sheng/` | `integrate/upstream-20261116` | 上游 main 加 12 GiB 的 `board.toml`、合盖处理、键盘壳和触控板诊断、`enable-jobs`、默认 `ci-mps=0` |
| `uefi-sheng/` | `local/sheng-12g-memory-map` | 固件里这台机器的 DRAM 内存表 |

核心仓库钉住的子模块里有三个用的是本机分支，`git submodule update --init --recursive` 会按钉住的提交取下来：
`drivers/DarwinBoot`（`local/window-9g`，接受最大 9 GiB 的窗口和窗口下限）、`drivers/Adreno740`（`local/owned-map-on-main`，
GPU 的页表盖住窗口以下的内存）、`drivers/ArmCpu`（`local/platform-sleep`，平台睡眠，只有带 `platform-sleep=1` 才生效，日常和试验镜像都不带）。

上机最稳的一组是 cd9：核心 `38a2a30`、sheng `bb0d65b`、uefi-sheng `20331338`，它的 s2 镜像连续开着两个多小时。分支头比它新，新提交要按第 5、6 节自己构建和上机确认。

平板 `boot_a` 里的日常镜像，源码在三个仓库的 `repro/daily-40234c20` 分支上（核心另有 `repro/daily-40234c20-firmware`，是固件里 UniXNU 程序的来源）。
按它们重编，功能上等于日常镜像，不保证逐字节相同。

## 2. 主机准备（一次）

- 工具：`docs/zh/guide/requirements.md` 列得不全，以 `../UniXNU-sheng/.github/workflows/package.yml` 里的 `brew install` 一行为准，
  另装 `rustup toolchain install 1.98.0 --profile minimal --component rust-src`。Mesa 的 Turnip 要 Bison 3.7 以上，系统自带的是 2.3：`brew install bison`。
- Xcode 27.2 和 Homebrew LLVM/LLD 23 能编过。kernel 构建的引导编译在链接时报 `ld: symbol(s) not found` 是正常的，只看最终退出码。
- 本地配置 `UniXNU/unixnu.local.toml`（git 忽略，格式见 `unixnu.example.toml`）：`[build]` 里写 `device`、`uefi`、`out` 和 `unique_chip_id`。
  - 芯片号是平板 `adb shell getprop ro.serialno` 读到的 8 位十六进制数，它是平台种子，会写进镜像。只写在这个文件里，不进任何提交、日志或文档。
- 输出目录 `out` 要在 APFS 卷上（exFAT 不支持符号链接）。下文 `<output>` 指 `<out>/sheng/macos-27.3-26C5035r/sheng_macos`。
  - `out` 设在仓库外时，在 `out` 的上一级建 `scripts` 链接指向 `UniXNU/scripts`（`UniXNU-sheng/scripts/build-gop-legacy-display-27.py` 按相对位置找它）。
  - 输出在外置盘的磁盘映像里时，每次构建前先挂上，否则输出会写回系统盘。挂接报 "Container superblock is invalid" 时，先 `hdiutil detach` 再用 `-nomount` 重新挂接、`fsck_apfs -n` 只读检查，不要直接修。
- 厂商输入：在 `../UniXNU-sheng` 下跑 `python3 scripts/extract-files.py`（触摸、键盘、VPU 固件，逐个核对 SHA-256）；
  WCN7850 的 `amss.bin`、`m3.bin`、`board-2.bin` 从 linux-firmware 的 `ath12k/WCN7850/hw2.0/` 取，放进 `firmware/wcn7850/`，大小和哈希要和同目录的 `manifest.json` 一致。
- 系统卷是 AEA 加密的，解密要 `ipsw`（`brew install ipsw`）。
- Data 种子：第一次 `./unixnu build kernel payload --os macos-27` 会在编译前停下，打印制作种子的命令。按 `docs/zh/porting/macos.md` 账户一节，
  在自己的终端里用 `sudo` 跑它，输出 `<output>/runtime/data.dbr`。之后每次构建都带同一个 `--data-ramdisk`。
- 根卷策略：这台机器用本地生成的钥匙。在 `UniXNU/` 下跑 `python3 scripts/make-root-policies.py --tree <output>/tree --output ../UniXNU-sheng/scripts/policies/macos-27.3-26C5035r --window OS=<ipsw>/141-22233-021.dmg:<UUID> --window SystemOS=<ipsw>/141-22145-021.dmg:<UUID> --window App=<ipsw>/141-22106-021.dmg:<UUID>`，UUID 取自 profile 的 `[root]` 段。
  - 生成的钥匙、header 和改过的 `verification.json` 在设备仓库里显示为"已修改"，永远不提交。私钥在 `<output>/tree/build/verified-root-host/keys`。
  - 合并上游时上游的策略文件会覆盖这些文件：合并前备份，合并后放回。丢了可以用 `recover-root-policies.py` 从构建好的载荷里取回。
  - 换了钥匙，kernel、userdata、payload 和启动镜像要一起重做，不能混用不同批次的产物。
- 每条 `./unixnu` 命令都带 `--os macos-27`，漏了会按 iPadOS 构建。

## 3. 平板准备（一次）

平板要先解锁 bootloader。这台机器的 ABL 不启动 header v0 的镜像，v4 模式下通用 ramdisk 又取自 `init_boot`，所以要先改两个分区（原厂镜像在 ROM 里，可以还原）：

```sh
fastboot erase init_boot_a
python3 -I local-tools/make-vendor-boot-noramdisk.py <ROM>/images/vendor_boot.img out/flash/vendor_boot-noramdisk.img
fastboot flash vendor_boot_a out/flash/vendor_boot-noramdisk.img
```

userdata：`./unixnu build userdata --os macos-27`（每个根卷带上它的哈希表，例如 `--object OS.vroot=<output>/tree/build/verified-root-OS/hashes.bin`，SystemOS、App 同样）。
直接 `fastboot flash` 原始镜像会失败，先转成 sparse 再刷：

```sh
python3 scripts/make-android-sparse.py <output>/userdata/userdata-root.img <output>/userdata/userdata-root.sparse.img
fastboot flash userdata <output>/userdata/userdata-root.sparse.img
```

第一次启动要新建持久化的 Data store，否则进桌面后写盘一律失败（黑屏加指针，日志里是 `device is not ready`、`cluster_push() failed with 16`）。
macOS 没有 iPadOS 菜单里的安装项，做法是打一份只启动一次的安装镜像：在一次完整的 kernel 加 payload 构建之后，
`./unixnu build payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr --kernel-arg data-reset=1`，按第 5 节打成 v4 镜像、从内存启动一次，
然后不带 `data-reset` 重跑一次 payload 构建，把 `<output>/payload/payload.img` 恢复成普通的那份。之后的镜像带着 `data-reset` 会在每次启动时清空 Data。

## 4. 试验固件（一次，内存表改动后再做）

试验镜像共用一份固件镜像 `<output>/boot/boot-bigwin.img`：uefi-sheng 在 `local/sheng-12g-memory-map`、DarwinBoot 在 `local/window-9g` 时构建：

```sh
./unixnu build firmware --os macos-27 --uefi ../uefi-sheng
./unixnu bootimg --os macos-27 --dtb <output>/tree/build/sheng/sheng.dtb -o <output>/boot/boot-bigwin.img
```

一定要带 `-o`，否则会覆盖 `<output>/boot/boot.img`。`bootimg` 无论如何都会改写 `<output>/boot/boot.json`，事后用备份还原。

## 5. 每一轮：构建、另存、做试验镜像

**构建前**

- 核对"日常文件"的哈希没变：`<output>/kernel/kernel.macho`、`<output>/payload/payload.img`、`payload.json`、`<output>/boot/boot.img`、`boot.json`、
  `<output>/runtime/data.dbr`、`<output>/boot/boot-bigwin.img`。构建会覆盖内核和载荷，`bootimg` 会改写 `boot.img` 和 `boot.json`，
  所以这几份各留一份带日常镜像哈希的只读备份（`kernel.macho.daily-<哈希>` 及同后缀的 `kernel.json`、`kernel.map.json`，`payload.daily-<哈希>.img` 和 `.json`，
  `boot.daily-<哈希>.img`、`boot.daily-<哈希>.json`），构建后用它们还原。
- 把 OS 镜像只读挂到系统盘上的一个目录：`hdiutil attach -readonly -nobrowse -mountpoint <系统盘上的目录> <ipsw>/141-22233-021.dmg`。
  普通用户不能在自己挂上的映像卷里再挂映像，输出在外置映像里时，payload 那一步自己去挂会报 Permission denied；`build-boot-runtime.py` 会复用已有的只读挂载。构建完 `hdiutil detach`。
- 只改了一两个内核侧源文件时，先用 `kernel-compile-check.py` 按构建参数单独编一遍，再跑整条构建。

**构建**（在自己的终端里，Metal 库清单要读受保护的系统路径，所以要 root；kernel 和 payload 必须同一条命令，否则报 Data 种子 UUID 不符）：

```sh
sudo -v && ./unixnu build kernel payload --os macos-27 --data-ramdisk <output>/runtime/data.dbr
```

构建中途停下的常见原因：

- `Bison 3.7 or newer is required`：装 Homebrew 的 bison。
- 缓存和新钉的版本对不上（metal2vulkan、Mesa 补丁数不同）：把 `<output>/tree/.cache/` 下对应目录改名留作备份，让脚本重新取。
- 挂载 cryptex 时 Permission denied：同上面 OS 镜像的原因，挂载点要在系统盘上。

**构建后，按顺序**

1. 记来源：`python3 -I local-tools/record-build-provenance.py cdN`，写到 `<output>/provenance/cdN.json` 和 `out/provenance/cdN.json`（git 忽略）。
   它记各仓库和子模块的提交、未提交的文件、工具链、产物哈希和载荷参数；芯片号只记 `present`，记录里出现芯片号就拒绝写。
2. 另存这一轮的产物并设为只读：`kernel.macho` 存成 `kernel.macho.cdN-<哈希前 8 位>`（`kernel.json`、`kernel.map.json` 同后缀），`payload.img` 存成 `payload.cdN-base.img`。
3. 用备份还原日常文件，再核对一遍哈希。

**做试验载荷**：在基础载荷上只改设备树里的窗口值和启动参数，不重新构建：

```sh
# s2：窗口按 board.toml（9 GiB，起点 0x8C0000000，收编低位内存条），主测试
python3 -I local-tools/make-payload-variant.py <output>/payload/payload.cdN-base.img <output>/payload/payload.cdN-s2.img \
  --arg enable-jobs=com.openssh.sshd --arg log-gpu=1

# s1：7.5 GiB，起点 0x920000000，不收编；s2 起不来或闪烁时用
python3 -I local-tools/make-payload-variant.py <output>/payload/payload.cdN-base.img <output>/payload/payload.cdN-s1.img \
  --set darwinboot-memory-size=0x1E0000000 --set darwinboot-memory-floor=0x920000000 \
  --arg memory-outside=0 --arg enable-jobs=com.openssh.sshd --arg log-gpu=1
```

- `enable-jobs=com.openssh.sshd` 让每次开机都开着 sshd。内核每次开机都会重写 launchd 的禁用列表，所以在系统里 `launchctl load -w` 开的服务重启后会失效。
- `log-gpu=1` 打开 Metal 插件的日志；`keyboard-backlight=0..100` 是键盘灯亮度，默认 0。
- 对照项一次只加一个参数，例如 `charge-auth=0`（充电认证）。
- 参数行不能超过 1000 字节。合进上游的桌面参数以后基础行是 920 字节，睡眠测试的四个参数放不下：用 `--replace-arg debug=334` 和 `--remove-arg log-gpu`（去掉 Metal 插件日志这个诊断参数）腾出位置，得到 994 字节。`--remove-arg NAME` 要求每一行里正好有一个 NAME。
- 工具拒绝 `data-reset` 和内核构建不接受的参数名，拒绝时不留输出文件。`adt-chosen.py` 能打印一份载荷交给加载器的窗口值。

**打成 v4 镜像并核对**：

```sh
python3 -I local-tools/make-bootimg-v4.py <output>/boot/boot-bigwin.img ../uefi-sheng/Resources/Scripts/mkbootimg.py \
  out/flash/boot-v4-payload.bigwin-cdN-s2.img <output>/payload/payload.cdN-s2.img
python3 -I local-tools/bootimg-contents.py out/flash/boot-v4-payload.bigwin-cdN-s2.img --payload <output>/payload/payload.cdN-s2.img
python3 -I local-tools/record-build-provenance.py cdN-images --artifact out/flash/boot-v4-payload.bigwin-cdN-s2.img
```

同一份固件打出的镜像大小都一样，分辨哪个镜像装的是哪份载荷，只能靠 `bootimg-contents.py --payload`。

## 6. 上机：只从内存启动

**每次到 fastboot 先读槽位**（按电源键加音量下键进 fastboot）：

```sh
fastboot getvar current-slot
fastboot getvar slot-retry-count:a     # 同样读 slot-successful:a、slot-unbootable:a，以及 b 的三项
fastboot getvar battery-voltage
```

- 这台机器没有安卓去把槽位标成"启动成功"，所以从 `boot_a` 每正常开机一次就扣一次重试次数，扣到 0 时槽位 a 被标成不可启动，下次开机会去启动槽位 b（b 里是原厂安卓，配不上现在的 userdata）。
- 槽位 a 的次数在 4 或以下就补：`fastboot set_active a`，次数回到 7。只补 a，不要切到 b。刷 `boot_a` 也会把次数重置为 7。
- `fastboot boot` 从内存启动、强制重启回 fastboot 都不扣次数。
- 插着电时不要在 macOS 里关机：平板会被充电事件重新拉起来，每次都可能扣一次次数，最后落进 fastboot。要关机先拔线。

**启动**：

```sh
python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.bigwin-cdN-s2.img
```

它等平板出现在 fastboot 里，启动一次，然后 45 秒内一直问引导程序：没有回应说明镜像在跑。
引导程序拒绝了镜像时，之后每次 `fastboot boot` 都会回 "Load Error"，要先 `fastboot reboot bootloader`。设备序列号就是芯片号，脚本不会写下来，连着一台设备时不用传 `--serial`。

**连上平板**：

- Wi-Fi 从控制中心手动连。自动加入还连不上：驱动约 7 s 交回扫描结果，系统把结果全部过滤掉，原因没查清（见 `HANDOFF.md` 的 cd16 一条）。
- SSH 用一把专用密钥，放在 `out/ssh/`（git 忽略），不碰 `~/.ssh`：

  ```sh
  ssh-keygen -t ed25519 -N '' -C unixnu-tablet-test -f out/ssh/tablet_ed25519
  ssh-copy-id -i out/ssh/tablet_ed25519.pub <账户>@<平板地址>      # 输一次登录密码，Data 是持久的，之后一直有效
  ssh -i out/ssh/tablet_ed25519 -o IdentitiesOnly=yes -o UserKnownHostsFile=out/ssh/known_hosts <账户>@<平板地址>
  ```

  平板地址只在当次用，不写进任何入库的文件。
- 平板的地址会变，不要用记下来的地址。`local-tools/tablet-ssh.py [命令]` 每次按主机密钥找到平板再连：
  - 它向默认网卡上开着 22 端口的主机要主机密钥，和 `out/ssh/known_hosts` 里那把相同的就是平板。先问上次的地址，再问 ARP 邻居，最后问整个网段（不超过 1022 台）。
  - 登录名写在 `out/ssh/tablet-account`；找到的地址记在 `out/ssh/tablet-address`，不打印。`--find` 只找不连。
  - 原因：记下来的地址如果在别的网段，这台 Mac 可能把它路由到隧道接口上。那条路由上任何端口都连得上，连上马上被关掉，看起来像平板的 sshd 坏了。
- 驱动的 Wi-Fi 日志 `kern.unixnu_wifi_log` 是约 500 行的环，每 10 s 一组的统计行约 6 分钟就把它填满。要留住没连网时（开机后、唤醒后、开关 Wi-Fi 后）的扫描记录，先在平板上启动 `tablet-wifi-capture.sh`，它每 2 s 把新行追加到文件：

  ```sh
  local-tools/tablet-ssh.py 'mkdir -p ~/unixnu-capture && cat > ~/unixnu-capture/tablet-wifi-capture.sh' < local-tools/tablet-wifi-capture.sh
  local-tools/tablet-ssh.py 'cd ~/unixnu-capture && nohup sh tablet-wifi-capture.sh ~/unixnu-capture/wifi-$(date +%H%M).log 60 >/dev/null 2>&1 &'
  local-tools/tablet-ssh.py "awk '!seen[\$0]++' ~/unixnu-capture/wifi-<时间>.log" > out/boot-logs/<目录>/wifi-capture.log
  ```

  脚本留在平板的 Data 卷上。开机后还没连网时，在平板的终端里跑 `sh ~/unixnu-capture/tablet-wifi-capture.sh ~/unixnu-capture/wifi-boot.log &`，再去连 Wi-Fi。
- `tablet-sleep-cycles.sh`：在平板上连续入睡若干次（默认 10 次），每次等它醒来，记一行（入睡和醒来的时刻、Sleep Count、WindowServer 的 pid）。唤醒后 Wi-Fi 不会自己连上，所以它不靠网络，放到平板上后台跑；跑完手动连上 Wi-Fi 再取结果。等入睡的 30 s 里碰键盘会取消那一轮，那一行会写 "no sleep"。
  ```
  local-tools/tablet-ssh.py 'cat > ~/unixnu-capture/tablet-sleep-cycles.sh' < local-tools/tablet-sleep-cycles.sh
  local-tools/tablet-ssh.py 'nohup sh ~/unixnu-capture/tablet-sleep-cycles.sh ~/unixnu-capture/sleep-cycles-$(date +%H%M).log 10 >/dev/null 2>&1 &'
  ```
  内核自己的记录事后用 `/usr/bin/log show --start '<日期 时刻>' --info | grep -E 'sheng sleep|IOCPUSleepKernel|panel back'` 取。
- `tablet-wifi-scan-probe.js`：打印 CoreWLAN 手里每条扫描结果的信道、信号、有没有名字、名字是不是已存的网络（`known`），以及扫描记录里的 `AGE`、`TIMESTAMP` 和标志（不打印名字和地址）。已存的网络 `AGE` 很大，就是列表里留着的、其实已经不在的网络。用法在文件开头。
- 系统为什么滤掉扫描结果，要看调试级日志，平时不落盘。先在平板上开采集，再让它扫描：

  ```sh
  local-tools/tablet-ssh.py 'cd ~/unixnu-capture && nohup /usr/bin/log stream --level debug --style compact --timeout 60m --predicate "process == \"airportd\" AND (eventMessage CONTAINS \"Filtering\" OR eventMessage CONTAINS \"filtered out\" OR eventMessage CONTAINS \"AUTO-JOIN: Scan\")" > airportd-$(date +%H%M).log 2>&1 &'
  ```

**每次上机都看的**：

- `sysctl kern.bootargs hw.memsize`：参数是不是这份载荷的；s2 的物理内存约 10.1 GB，s1 约 7.5 GB。
- 图标服务：`launchctl print gui/501/com.apple.iconservices.iconservicesagent` 里的 `runs` 和 `successive crashes`，
  日志里有没有 `MPSImageUnaryKernel`。远端 zsh 的 `log` 是内建命令，要写 `/usr/bin/log show --last 10m`。
- 代码签名：日志里 WindowServer 有没有 `Code Signature Invalid`，`sysctl vm.cs_native4k_stats` 的 `bad` 是不是 0。
- 电量和充电：`ioreg -rc ShengBattery` 的 `Amperage`、`Voltage`。macOS 显示的百分比是跳着变的，算耗电要用电流。
- 平板上的探测脚本拷过去用 `osascript -l JavaScript <脚本>` 跑：`tablet-icon-stress.js`（大量画图标，GPU 卡住的对照）、
  `tablet-ci-blur-probe.js`（Core Image 模糊这条路）、`tablet-pointer-probe.js`（指针跳动，结果用 `pointer-csv-stats.py` 比较）。
  触控板的报文间隔用 `ioreg` 读出来交给 `touchpad-timing.py` 解码。
- 崩溃和卡顿报告、照片、录屏放到 `data/`（git 忽略）。

同一份镜像两次开机的表现可能不同（卡顿、指针闪），下结论前同一份镜像至少开两次。

## 7. 转成日常镜像：刷 `boot_a`

只刷从内存启动验证过的镜像。v4 试验镜像比 192 MiB 的 `boot_a` 大，先把载荷文件原样装进一个更小的 FAT32 卷：

```sh
python3 -I local-tools/make-flash-bootimg.py out/flash/boot-v4-payload.<名字>.img out/flash/boot-v4-flash.new.img
python3 -I local-tools/boot-sheng.py out/flash/boot-v4-flash.new.img      # 这份也先从内存启动一次
fastboot flash boot_a out/flash/boot-v4-flash.new.img
```

刷之前把旧的日常镜像改名为 `boot-v4-flash.prev.img` 留作回退。`vbmeta` 不用动。刷完 `fastboot reboot`，之后平板按电源键就会自己进 macOS。

充电：只有 macOS 开着、接充电头时能充；接 Mac 的口电流不够，电池照样在掉；停在 fastboot 里基本不充。上机前读一次电压，电量低时先充电，中途断电会被误当成"自己关机"。

## 8. 已知限制

- 睡眠：`board.toml` 里是 `sleep-disabled = 1`，没有挂起和恢复。合盖时停触摸屏，并告诉 macOS 的电源管理盖子合上了；合盖时关背光是 cd9 之后加的，还没上机。熄屏时电流约 1.0 A。
- 屏幕自动熄灭时背光还亮着，显示驱动只看到一帧空画面。
- 键盘壳偶尔断开半秒再接上，是键盘壳控制器自己报的断开。
- Wi-Fi 自动加入连不上，见第 6 节。
- 设置里有一部分图标是空白的，每次都是同样那些。

## 9. 不入库的东西

`unixnu.local.toml`（芯片号）、设备仓库里本地生成的根卷策略文件、Data 种子、`out/`（专用 SSH 密钥、镜像、来源记录）、`data/`（照片、日志、录屏）。
推送前拿 `unixnu.local.toml` 里芯片号的实际值，在要推的提交里搜一遍，确认没有。
