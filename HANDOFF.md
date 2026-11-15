# Handoff：小米平板 6S Pro（sheng）构建 macOS 27.3

更新时间：2026-11-15
**内存更正（2026-11-14 实测）：这台平板是 12 GiB 内存，不是之前一直写的 16 GiB，见文末"用户想把内存拉满"一条。本文件其他地方的"16 GiB"都指这台机器。**

目标：用 UniXNU 为小米平板 6S Pro（代号 sheng，SM8550）构建 macOS 27.3（profile `macos-27.3-26C5035r`）镜像，刷入 `userdata` 后用 `fastboot boot` 启动。

当前阶段（2026-11-15 16:05）：**路线 A 的主机部分做完了（四个代码任务、新内核、新固件、六份载荷、五份只从内存启动的镜像）。7.5 GiB 的第 1 步镜像今天从内存启动过两次，都进了桌面，macOS 显示 7.50 GB，大窗口本身能启动。但两次都定住了：10:13 那次登录后约两分钟指针来回跳、然后定住；10:28 那次（诊断上机 D1，不恢复上次的应用）从约 5 分钟起应用一个个未响应，再过 10 分钟整机不应答。早上日常镜像的基线也有卡顿和指针抖动。每次都是内存第一次用满之后出事，原因还没有证据。第 1 步没有通过，后面几步都没有做，`boot_a` 没有动过。平板 10:55 在 fastboot（槽位 a，重试次数掉到过 0、已补回 7，见下面"槽位 a 的重试次数"一条；电压 3761，macOS 读的电量 23%），在等用户充电和决定下一次上机。用户 11:04 另外提出给 macOS 补充电驱动：驱动已经有了，缺的是 macOS 下充不进的原因，建议先量再定，在等用户答复（见下面"用户 11:04 提出"一条）。11:24 重启进日常镜像（上机 D2）：macOS 开着、接充电头能充（电池 +2 A），接 Mac 的口只进 0.45 A、电池在掉，停在 fastboot 基本不充。D2 在 11:34 以"终端全屏后卡死、键盘壳失灵、触屏还能用、已用 4.61 G / 5.95 G"结束，用户强制重启。11:39 再次重启进日常镜像（上机 D3，全程接 Mac 的线）：约 26 分钟时拍到了证据。整机没死，终端卡在重画自己的窗口里；已用 4.91 G 里被钉住的（Wired）占 3.26 G，程序只剩 1.02 G，交换 0、压力绿。交换不是瓶颈，下一步是查谁占着 Wired、卡住的程序最底层在等什么（见"11:39 上机 D3"一条）。D4（约 12:50 开机）的取样录像读完：终端主线程在等图标服务（IconServices）回一个同步请求，要的是标题栏上的文档小图标。下一步是看图标服务自己在做什么。13:19 平板在 fastboot，槽位 a 从 1 补回 7。16:04 用户说平板没电关机了，充电头只读到 2 W；在等它充上电再开机（见"16:04 用户"一条）。**

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
