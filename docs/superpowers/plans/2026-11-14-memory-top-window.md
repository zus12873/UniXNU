# sheng 内存路线一：窗口挪到顶部 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让加载器能把内核窗口限制在指定地址以上，把这台 12 GiB 平板的窗口放到 `0x980000000`–`0xB00000000`，由内核收编窗口下方的 `0x880000000`–`0x980000000`，`hw.memsize` 从 6.38 GiB 提高到约 9.9 GiB。

**Architecture:** 改四处，内核不动。加载器（子模块 `drivers/DarwinBoot`）加一个窗口下限；生成器把板级选项 `owned_memory_floor` 写成 `/chosen/darwinboot-memory-floor`；固件内存表把 bank 1 列到 `0xB00000000`；板级配置填本机的值。先写主机测试，再构建另起文件名的镜像，上机只从内存启动。

**Tech Stack:** C（EDK II 驱动；主机上用 clang 编成动态库，Python `ctypes` 调用）；Python 3 标准库（`python3 -I -B`，不装任何包）；GNU mtools；`./unixnu`；`fastboot`。

**Spec:** `docs/superpowers/specs/2026-11-14-memory-top-window-design.md`

## Global Constraints

- 内核源码和内核补丁不改，内核不重新编译。
- 本计划里的镜像只从内存启动（`local-tools/boot-sheng.py`）。写 `boot_a` 不在本计划的自动步骤里，要用户当次明确同意。
- 上机步骤（Task 6）要等用户在场并明确说可以开始。Task 1 到 Task 5 只在 Mac 上做，不需要平板。
- 不切槽位 b；`fastboot set_active a` 只在重试次数不够时用（用户已允许）。不刷也不启动带 `data-reset` 的镜像（`out/flash/boot-v4-install.img`）。不碰 `userdata`、abl、xbl。
- 日常那一套文件不覆盖：`out/flash/boot-v4-flash*.img`、`out/flash/boot-v4-payload*.img`、`<output>/boot/boot.img`、`<output>/boot/boot.json`、`<output>/boot/boot.good.json`、`<output>/payload/payload.img`。新文件名一律带 `topwin`。
- `<output>` 指 `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos`（外置盘上的构建盘镜像，要先挂载）。
- 芯片序列号不写进任何文件或提交，文档里写 `<序列号>`。每次提交前在 diff 里搜一遍。
- 四个仓库都只在本地分支提交，逐个列出文件，不 push：
  - UniXNU：`local/sheng-16g-macos`。
  - 子模块 `drivers/DarwinBoot`：新分支 `local/window-floor`。不提交 `Test/__pycache__/`。
  - `../uefi-sheng`：`local/sheng-12g-memory-map`。
  - `../UniXNU-sheng`：新分支 `local/sheng-12g-top-window`，只提交 `board.toml`。工作区里别的改动（`feeds.toml`、`patches/xnu-12377/series`、`unixnu.lock`、三个 `verification.json`、未跟踪的补丁、`drivers/Ath12kWifi`）不带上。
- Python 一律 `python3 -I -B` 运行，只用标准库。
- `./unixnu …` 必须在 `UniXNU/` 下按原样执行（不加 `cd`、管道、变量前缀），关沙箱。`fastboot`、`hdiutil`、写兄弟仓库和外置盘也要关沙箱。
- 目标值：`hw.memsize` 不低于 10200547328（9.5 GiB），预期约 9.9 GiB。
- 这些地址只对 12 GiB 这台机器成立，不向上游提交。

## Review Focus

1. 下限以上没有哪个空闲段放得下窗口头部：加载器必须报找不到窗口，不能退回到下限以下（Task 1：`floor=0xAF0000000`、`floor=0xB00000000`、`floor=MAX` 都返回 `(0, 0)`）。
2. 下限落在 2 MiB 块中间：起点取下一个 2 MiB 边界加内核偏移，不低于下限（Task 1：`floor=0x980001000` 得 `0x980204000`；Task 3：生成器直接拒绝不是 2 MiB 倍数的值）。
3. 板级选项的写法和非法值：十六进制字符串、十进制字符串、整数都接受；零、负数、超过 64 位、不是数字、缺窗口大小或缺排除表时报错（Task 3）。
4. `0x880000000` 以下有一段空闲内存没被保留列表挡住：收编会被整个关掉，而且不报错（Task 4：`test_everything_below_bank_1_is_kept_out`、`test_without_the_new_kept_range_nothing_is_adopted`）。
5. `darwinboot-memory-floor` 重复出现、长度不是 8、放在 `/chosen` 之外，或有下限却没有排除表：加载器拒绝整棵树（Task 2）。

---

### Task 1: 加载器的 `DarwinWindowStart` 加下限参数

**Files:**
- Modify: `drivers/DarwinBoot/DarwinBootPkg/Driver/MemoryWindow.h`（`DarwinWindowStart` 和它上面的注释）
- Modify: `drivers/DarwinBoot/DarwinBootPkg/Driver/DarwinBoot.c:623`（唯一的调用处，本任务先传 `0`）
- Test: `drivers/DarwinBoot/Test/test-memory-window.py`、`drivers/DarwinBoot/Test/test-memory-outside.py:69`

**Interfaces:**
- Produces:
  ```c
  STATIC UINT64 DarwinWindowStart (CONST VOID *Map, UINTN MapSize, UINTN Stride, UINT64 Block, UINT64 Offset,
                                   UINT64 Head, UINT64 Size, UINT64 Floor, UINT64 SkipUsable, UINT64 SkipAddress,
                                   UINT64 *Usable)
  ```
  每个空闲段先裁成 `[max(Start, Floor), End)`，整段在下限以下的跳过；其余规则不变（候选是裁后起点按 `Block` 向上对齐再加 `Offset`；头部必须整个落在一段空闲内存里；按窗口内可用字节数排，相同取低地址）。`Floor` 为 0 时结果与现在完全相同。

- [x] **Step 1: 在子模块里建分支**

Run: `git -C drivers/DarwinBoot switch -c local/window-floor`

- [x] **Step 2: 写失败的测试**

改 `Test/test-memory-window.py`：C 包装函数 `start` 在 `window` 后面多一个 `UINT64 floor` 并传给 `DarwinWindowStart`；Python 的 `start(descriptors, offset, head, size, skip=(MAX, 0), floor=0)` 和 `reference_start(descriptors, offset, head, size, floor=0)` 各加一个参数（参考实现里把每段的起点取 `max(start, floor)`，起点不小于终点的段跳过）。在现有 `sheng` 用例之后加：

```python
    # 12 GiB 机型、固件内存表列到顶之后：bank 1 的三段空闲内存，顶端 256 MiB 里是固件的分配，再加低端的空闲段。
    sheng12 = [
        (FREE, 0x880000000, 0x39D00000), (FREE, 0x8B9F00000, 0x01E00000), (FREE, 0x8C0000000, 0x230000000),
        (BS_DATA, 0xAF0000000, 0x04000000), (FREE, 0xAF4000000, 0x03000000), (RT_DATA, 0xAF7000000, 0x00100000),
        (FREE, 0xAF7100000, 0x00F00000), (LOADER_DATA, 0xAF8000000, 0x02000000), (RT_CODE, 0xAFA000000, 0x00200000),
        (BS_CODE, 0xAFA200000, 0x05E00000),
        (FREE, 0xBAB00000, 0x0D1C0000), (FREE, 0xC7CC0000, 0x05040000), (FREE, 0xCCF80000, 0x0B080000), (FREE, 0xE671D000, 0x190E3000),
    ]
    args = (0x4000, 0x11000000, 0x180000000)
    assert start(sheng12, *args) == (0x8C0004000, 0x180000000)
    assert start(sheng12, *args, floor=0x980000000) == (0x980004000, 0x175EFC000)
    assert start(sheng12, *args, floor=0x980001000) == (0x980204000, 0x175CFC000)
    assert start(sheng12, *args, floor=0x1000) == start(sheng12, *args)
    for nothing in (0xAF0000000, 0xB00000000, MAX):
        assert start(sheng12, *args, floor=nothing) == (0, 0), hex(nothing)
    found = start(sheng12, *args, floor=0x980000000)
    assert start(sheng12, *args, skip=(found[1], found[0]), floor=0x980000000) == (0, 0)
    # 固件在下限处占了一块：窗口往上挪，不往下。
    held = [entry for entry in sheng12 if entry[1] != 0x8C0000000] + [
        (FREE, 0x8C0000000, 0xC0000000), (RT_DATA, 0x980000000, 0x00400000), (FREE, 0x980400000, 0x16FC00000)]
    assert start(held, *args, floor=0x980000000) == (0x980404000, 0x175AFC000)
```

再加一轮 400 个随机内存表（种子 `20261114`，内存表的生成方式与现有那一轮相同）：每轮随机挑一段，从 {0，该段起点，起点加 `0x1000`，段中间按 4 KiB 取整的一点，该段终点} 里取一个下限；断言 C 实现与 `reference_start(…, floor)` 一致，并且找到的起点不低于下限。最后一行输出改为 `PASS: window start by usable memory, window floor, excluded-range table, table overflow, 800 random maps against the model`。

- [x] **Step 3: 运行，确认失败**

Run: `python3 -I -B drivers/DarwinBoot/Test/test-memory-window.py`
Expected: clang 报 `too many arguments to function call`（`DarwinWindowStart` 还没有这个参数），脚本以 `CalledProcessError` 结束。

- [x] **Step 4: 实现**

改 `MemoryWindow.h` 的 `DarwinWindowStart`：裁剪放在读出 `Start`、`End` 之后、现有的溢出检查之前，这样溢出检查看到的是裁后的起点。函数上方的注释补一句下限的含义。同时把另外两处调用补上参数：`DarwinBoot.c:623` 传 `0`，`Test/test-memory-outside.py:69` 的 `unused_start` 传 `0`。

- [x] **Step 5: 运行加载器的全部主机测试**

Run: `for t in test-memory-window test-memory-outside test-adt-window test-loader-inputs test-kernel-parser; do python3 -I -B drivers/DarwinBoot/Test/$t.py || echo "FAILED $t"; done`
Expected: 五行 `PASS: …`，没有 `FAILED`。（`test-packed-ramdisk.py` 在 `-I` 下本来就因为找不到同目录模块而失败，与本计划无关，不在这个列表里。）

- [x] **Step 6: 提交（子模块内）**

```bash
git -C drivers/DarwinBoot add DarwinBootPkg/Driver/MemoryWindow.h DarwinBootPkg/Driver/DarwinBoot.c Test/test-memory-window.py Test/test-memory-outside.py
git -C drivers/DarwinBoot commit -m "feat(boot): a floor for the start of the window"
```

---

### Task 2: 加载器读取 `/chosen/darwinboot-memory-floor`

**Files:**
- Modify: `drivers/DarwinBoot/DarwinBootPkg/Driver/DarwinBoot.c`（`AdtNode` 第 289 行起和第 411 行的递归调用；`AllocateSpan` 第 601 行；`Load` 里第 895、966 行两处调用和第 1034 行附近的打印）
- Modify: `drivers/DarwinBoot/README.md`（讲 `darwinboot-memory-excluded` 的那一段后面加一段）
- Test: `drivers/DarwinBoot/Test/test-adt-window.py`

**Interfaces:**
- Consumes: Task 1 的 `DarwinWindowStart (…, Size, Floor, SkipUsable, …)`。
- Produces:
  - `AdtNode (…, UINT64 *WindowSize, UINT64 *WindowFloor, BOOLEAN *KeepPacked, …)`：新参数插在 `WindowSize` 后面。属性 `darwinboot-memory-floor` 的长度必须是 8；同一节点里出现两次、出现在 `/chosen` 以外的节点、或此前已经读到一个非零值，返回 `FALSE`。值 0 等同于没有这个属性。任何非零值都接受，对齐由 `DarwinWindowStart` 处理。
  - `STATIC BOOLEAN AdtWindowConsistent (UINT64 WindowFloor, UINTN ExcludedOffset)`：下限非零而没有排除表（`ExcludedOffset == MAX_UINTN`）时返回 `FALSE`。放在 `AdtNode` 和 `ValidTrustCaches` 之间，这样测试截取的那段源码里有它。`Load` 在 `AdtNode` 成功后调用，不一致时按 `EFI_COMPROMISED_DATA` 失败。
  - `AllocateSpan (KERNEL *Kernel, UINT64 WindowSize, UINT64 WindowFloor, UINT64 HeadSize, EFI_PHYSICAL_ADDRESS *Address)`：把下限传给 `DarwinWindowStart`。找不到窗口时屏幕上的那一行改成 `NO WINDOW %lx HEAD %lx FLOOR %lx`。
  - 下限非零时，和 `DARWINBOOT: ARM64 …` 那一行一起多打印一行：`DARWINBOOT: window floor=0x%lx start=0x%lx`。

- [x] **Step 1: 写失败的测试**

改 `Test/test-adt-window.py`：C 入口 `parse` 多一个输出参数 `UINT64 *floor`（初值 0），返回 `AdtNode (…) && at == size && AdtWindowConsistent (*floor, *excluded)`；`parse_all` 返回六个值，最后一个是下限；`parse` 仍取前四个。设 `floor = ('darwinboot-memory-floor', struct.pack('<Q', 0x980000000))`，加这些用例：

| 用例 | 断言 |
| --- | --- |
| `chosen(size, table, floor)`，以及另外两种属性顺序 | 接受；下限是 `0x980000000`；前五个结果与不带 `floor` 时相同 |
| 没有这个属性 | 下限是 0 |
| 值为 0，带表和不带表各一次 | 接受；下限是 0 |
| 值 `0x980001000`（不在 2 MiB 边界上），带表 | 接受；原值返回 |
| 长度 0、4、12、16 | 拒绝 |
| 同一节点里出现两次 | 拒绝 |
| 放在根节点；放在 `memory-map` 里 | 拒绝 |
| 两个 `chosen` 节点各带一个非零下限 | 拒绝 |
| 非零下限，没有排除表 | 拒绝 |

最后一行输出改为以 `PASS: window size, floor, excluded-range table and loader input record of /chosen` 开头，拒绝用例的计数跟着加。

- [x] **Step 2: 运行，确认失败**

Run: `python3 -I -B drivers/DarwinBoot/Test/test-adt-window.py`
Expected: clang 报 `AdtNode` 的参数个数不符或 `AdtWindowConsistent` 未声明，脚本以 `CalledProcessError` 结束。

- [x] **Step 3: 实现**

按 Interfaces 改 `DarwinBoot.c`。`Load` 里新增局部变量 `WindowFloor`，初值 0。README 的新段落写清楚：属性名、8 字节、0 等于没有、只在有排除表时有效、屏幕上多出的那一行，并注明还没有上机。

`DarwinBoot.c` 整体只在固件构建时编译（Task 5 Step 3）；主机测试只编译 `AdtNode` 到 `ValidTrustCaches` 之间的那一段。

- [x] **Step 4: 运行加载器的全部主机测试**

Run: 同 Task 1 Step 5。
Expected: 五行 `PASS: …`，没有 `FAILED`。

- [x] **Step 5: 提交（子模块内）**

```bash
git -C drivers/DarwinBoot add DarwinBootPkg/Driver/DarwinBoot.c Test/test-adt-window.py README.md
git -C drivers/DarwinBoot commit -m "feat(boot): /chosen/darwinboot-memory-floor keeps the window at or above an address"
```

---

### Task 3: 生成器的板级选项 `owned_memory_floor`

**Files:**
- Modify: `scripts/unixnu/devicetree.py`（新函数 `memory_floor`；`generate()` 里排除表那一段之后调用）
- Modify: `docs/reference/configuration.md`、`docs/zh/reference/configuration.md`（`owned_memory_excluded_ranges` 那一行下面各加一行）
- Create: `local-tools/tests/test_devicetree_floor.py`
- UniXNU 里更新子模块 `drivers/DarwinBoot` 的指向

**Interfaces:**
- Produces: `memory_floor(options: dict) -> list[tuple[str, bytes]]`
  - 没有 `owned_memory_floor` 键：返回 `[]`。
  - 合法：返回 `[('darwinboot-memory-floor', struct.pack('<Q', value))]`。值可以是整数，也可以是 `int(text, 0)` 认识的字符串。
  - 其余情况抛 `unixnu.util.Error`，消息以 `Owned memory floor` 开头：值是布尔或不是数字；为 0；为负；不小于 `2**64`；不是 `0x200000` 的倍数；`options` 里没有 `owned_memory_size`；没有 `owned_memory_excluded_ranges`。
- `generate()`：`chosen += memory_floor(options)`，放在 `darwinboot-memory-excluded` 之后、`darwinboot-loader-inputs` 之前。

- [x] **Step 1: 写失败的测试**

`local-tools/tests/test_devicetree_floor.py`，用 `unittest`；开头 `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))`，然后 `from unixnu import devicetree` 和 `from unixnu.util import Error`。基准选项 `BASE = {'owned_memory_size': '0x180000000', 'owned_memory_excluded_ranges': 64}`。

| 测试 | 断言 |
| --- | --- |
| `test_absent_gives_no_property` | `memory_floor(BASE) == []` |
| `test_accepts_hex_string_decimal_string_and_integer` | `'0x980000000'`、`'40802189312'`、`40802189312` 都得到 `[('darwinboot-memory-floor', bytes.fromhex('0000008009000000'))]` |
| `test_refuses_zero_negative_and_too_large` | `0`、`'0'`、`-0x200000`、`2**64` 抛 `Error`，消息以 `Owned memory floor` 开头 |
| `test_refuses_value_off_the_2_mib_grid` | `'0x980001000'`、`0x100000` 抛 `Error` |
| `test_refuses_non_number` | `'top'`、`True` 抛 `Error` |
| `test_requires_size_and_excluded_table` | 去掉 `owned_memory_size`，或去掉 `owned_memory_excluded_ranges`，抛 `Error` |

- [x] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: 新的 6 个测试 ERROR，原因是 `devicetree` 没有 `memory_floor`；原有 12 个通过。

- [x] **Step 3: 实现 `memory_floor` 并在 `generate()` 里调用，补两份配置文档各一行**

- [x] **Step 4: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 18 tests`，`OK`。

- [x] **Step 5: 提交**

```bash
git add scripts/unixnu/devicetree.py docs/reference/configuration.md docs/zh/reference/configuration.md local-tools/tests/test_devicetree_floor.py drivers/DarwinBoot
git commit -m "feat(devicetree): owned_memory_floor keeps the kernel window at or above an address"
```

子模块指向的两个提交只在本地，这个分支不能原样推给上游。

---

### Task 4: 本机的值，和整机布局的主机测试

**Files:**
- Create: `local-tools/tests/test_top_window_layout.py`
- Modify: `../uefi-sheng/Platforms/Xiaomi/shengPkg/Library/MemoryMapLib/MemoryMapLib.c`（"DRAM bank 1 high" 一行和它上面两行注释）
- Modify: `../UniXNU-sheng/board.toml`（`["os_overrides"."macos-27.3-26C5035r"."payload"."adt"]` 一段，现在第 242–260 行）

**Interfaces:**
- Consumes: Task 1 的 `DarwinWindowStart`（带下限）和现有的 `DarwinOutsideRanges`，像 `Test/test-memory-window.py` 那样把 `MemoryWindow.h` 编成动态库后调用；Task 3 的 `memory_floor`。
- Produces（测试文件内部用）：
  - `firmware_free()`：从 `MemoryMapLib.c` 里取出形如 `{"名字", 0x基址, 0x大小, AddMem, SYS_MEM, SYS_MEM_CAP, Conv, …}` 的行，返回 `(基址, 大小)` 列表。
  - `memory_map(free)`：这些段作为空闲内存，最高一段的顶端 `0x10000000` 字节改成 boot services data（模型：固件自己的分配在内存顶）。
  - `adopted(pairs, kept, phys_base)`：内核 `arm_vm_outside_init` 的 Python 版，返回 `(各段的 (起, 止) 列表, 合成的区或 None)`。

`adopted` 照内核补丁 `window-outside-memory-adoption.patch` 的 `arm_vm_outside_pair`、`arm_vm_outside_add`、`arm_vm_outside_init` 逐条写，逻辑如下：

```python
def adopted(pairs, kept, phys_base, dram_base=0x80000000, twig=0x200000, limit=16):
    table = []

    def add(base, end, first):
        for index in range(first, len(kept)):
            low, high = kept[index][0], kept[index][0] + kept[index][1]
            if high <= low or high <= base or low >= end:
                continue
            if base < low:
                add(base, low, index + 1)
            if end > high:
                add(high, end, index + 1)
            return
        base, end = (base + 0xfff) & ~0xfff, end & ~0xfff
        if base < end and len(table) < limit:
            table.append((base, end))

    for base, size in pairs:
        if size and base >= dram_base and base + size <= phys_base:
            add(base, base + size, 0)
    if not table:
        return [], None
    low = min(base for base, _ in table) & ~(twig - 1)
    high = min((max(end for _, end in table) + twig - 1) & ~(twig - 1), phys_base & ~(twig - 1))
    return (table, (low, high)) if low < high <= low + (4 << 30) else ([], None)
```

- [x] **Step 1: 写失败的测试**

常量：内核在 2 MiB 块里的偏移 `0x4000`，头部按 `0x11000000` 估，窗口外的段按 `0x10000` 对齐、不小于 `0x100000`（与 `DarwinBoot.c` 调用 `DarwinOutsideRanges` 的参数一致）。板级选项用 `tomllib` 从 `../UniXNU-sheng/board.toml` 的 `os_overrides."macos-27.3-26C5035r".payload.adt` 读；下限用 `adt.get('owned_memory_floor', '0')`，这样改配置之前测试是失败而不是报错。`窗口` 指 `DarwinWindowStart` 在 `memory_map(firmware_free())` 上按板级的窗口大小和下限算出的起点；`窗口外的表` 指 `DarwinOutsideRanges` 按板级的 `owned_memory_outside_ranges` 算出的各段。

| 测试 | 断言 |
| --- | --- |
| `test_firmware_table_lists_bank_1_to_the_top` | `firmware_free()` 里基址不低于 `0x880000000` 的段是 `[(0x880000000, 0x39D00000), (0x8B9F00000, 0x01E00000), (0x8C0000000, 0x240000000)]` |
| `test_window_starts_at_the_floor` | 窗口起点是 `0x980004000` |
| `test_generator_accepts_the_board_options` | `devicetree.memory_floor(adt) == [('darwinboot-memory-floor', struct.pack('<Q', 0x980000000))]` |
| `test_kernel_adopts_the_three_runs_below_the_window` | `adopted(窗口外的表, 板级保留列表, 窗口起点)` 的各段是 `[(0x880000000, 0x8B9D00000), (0x8B9F00000, 0x8BBD00000), (0x8C0000000, 0x980000000)]`，区是 `(0x880000000, 0x980000000)`，总字节数是 `0xFBB00000` |
| `test_everything_below_bank_1_is_kept_out` | 把内存表里 `0x880000000` 以下的段换成一整段 `0x80000000`–`0x880000000` 的空闲内存，收编结果仍是上面那三段 |
| `test_without_the_new_kept_range_nothing_is_adopted` | 板级保留列表里有 `"0x80000000:0x800000000"`；去掉它之后 `adopted(…)` 返回 `([], None)` |
| `test_keeping_the_newly_listed_memory_out` | 保留列表再加 `(0x8A0000000, 0x20000000)`：各段是 `[(0x880000000, 0x8A0000000), (0x8C0000000, 0x980000000)]`，总字节数是 `0xE0000000` |
| `test_fragmented_low_bank_keeps_the_span` | 低端换成 20 段 16 MiB 的空闲内存（`0x90000000 + i * 0x2000000`）：窗口外的表里仍有 bank 1 的三段。换成 20 段 40 MiB（`0x90000000 + i * 0x3000000`）：30 MiB 那段被挤出表，区仍是 `(0x880000000, 0x980000000)`，总字节数是 `0xF9D00000` |

兄弟仓库不在时整个测试类跳过（`skipUnless`）；在这台 Mac 上运行时输出里不能有 `skipped`。

- [x] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: 新的 8 个测试全部 FAIL（不是 ERROR），原有 18 个通过。

- [x] **Step 3: 改固件内存表**

`MemoryMapLib.c`："DRAM bank 1 high" 从 `0x8C0000000, 0x140000000` 改成 `0x8C0000000, 0x240000000`；上面两行注释改成说明依据（引导程序的 `/memory` 节点，2026-11-14 读出）和 `0xA00000000` 以上还没有上机验证过。其余行不动。

- [x] **Step 4: 改板级配置**

`board.toml` 的那一段：
- 新增 `"owned_memory_floor" = "0x980000000"`。
- `"owned_memory_outside_ranges"` 从 `8` 改成 `16`。
- `"owned_memory_outside_reserved"` 改成 `["0xd0000000:0x10000", "0x80000000:0x800000000"]`。
- 这一段里两处注释跟着改写：窗口是 bank 1 顶部的 6 GiB（`0x980000000`–`0xB00000000`）；内核收编的是窗口下方 `0x880000000`–`0x980000000` 的三段；`0x880000000` 以下全部保留，原因是合成的区不能超过 4 GiB；这组值只对 12 GiB 机型成立。

- [x] **Step 5: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 26 tests`，`OK`，没有 `skipped`。

- [x] **Step 6: 提交（三个仓库）**

```bash
git -C ../uefi-sheng add Platforms/Xiaomi/shengPkg/Library/MemoryMapLib/MemoryMapLib.c
git -C ../uefi-sheng commit -m "fix(sheng): bank 1 reaches 0xB00000000 on the 12 GiB unit"
git -C ../UniXNU-sheng switch -c local/sheng-12g-top-window
git -C ../UniXNU-sheng add board.toml
git -C ../UniXNU-sheng commit -m "feat(sheng): the window at the top of bank 1 on the 12 GiB unit"
git add local-tools/tests/test_top_window_layout.py
git commit -m "test: the top-window layout of the 12 GiB sheng unit"
```

提交前用 `git -C ../UniXNU-sheng diff --cached --stat` 确认暂存区里只有 `board.toml`。

---

### Task 5: 构建并核对镜像

**Files:**
- Create: `local-tools/adt-chosen.py`
- Create: `local-tools/tests/test_adt_chosen.py`
- Modify: `HANDOFF.md`（第 8、9 节记下新文件和哈希）
- 产物（不入库）：`out/flash/SILICIUM_UEFI.topwin-<sha256 前 8 位>.fd`、`<output>/boot/boot-topwin.img`、`<output>/payload/payload.daily-8a36fe56.img` 和 `.json`、`<output>/payload/payload.topwin.img`、`<output>/payload/payload.topwin-k443.img`、`out/flash/boot-v4-payload.topwin.img`、`out/flash/boot-v4-payload.topwin-k443.img`、`out/flash/boot-v4-flash.topwin.img`

**Interfaces:**
- Consumes: Task 1 到 Task 4 的全部提交。
- Produces: 命令行 `python3 -I local-tools/adt-chosen.py ADT`。`ADT` 是 payload 卷里的 `kernel.macho.adt`。按文件里的顺序，对 `/chosen` 下每个名字以 `darwinboot-` 开头的属性输出一行 `<名字> <长度> <值>`：长度 8 的值写成 `0x…`；长度是 16 的正整数倍的，全零写成 `N empty pairs`，否则逐对写成 `0x基址+0x大小`，用空格分开；其余长度写十六进制串。文件不是完整的设备树，或没有 `/chosen`，以非 0 退出码结束，stderr 以 `adt-chosen: ` 开头。属性长度字段只取低 31 位。

带 `k443` 的那份 payload 是对照用的：保留列表多一项 `0x8A0000000:0x20000000`，把 2026-11-14 实测内存表新列入的 443 MiB 挡在收编之外。19:01 之后两次卡死的原因还没分清，上机时先跑这一份，再跑完整的一份，一次只变一件事。

- [x] **Step 1: 写失败的测试**

`local-tools/tests/test_adt_chosen.py`，用 `unixnu.devicetree.node` 造树，把工具当子进程调用。

| 测试 | 断言 |
| --- | --- |
| `test_prints_the_darwinboot_properties_of_chosen` | 树里 `chosen` 前面有一个别的节点，`chosen` 带 `random-seed` 和下面五个属性，下面还有 `memory-map` 子节点。退出码 0，标准输出正好是：`darwinboot-memory-size 8 0x180000000`、`darwinboot-memory-excluded 1024 64 empty pairs`、`darwinboot-memory-floor 8 0x980000000`、`darwinboot-memory-outside 256 16 empty pairs`、`darwinboot-memory-outside-kept 32 0xd0000000+0x10000 0x80000000+0x800000000` 五行 |
| `test_refuses_truncated_tree` | 同一棵树去掉最后 5 个字节：退出码非 0，stderr 以 `adt-chosen: ` 开头 |
| `test_refuses_tree_without_chosen` | 只有根节点的树：退出码非 0，stderr 以 `adt-chosen: ` 开头 |

- [x] **Step 2: 运行确认失败，实现工具，再运行确认通过，提交**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: 实现前新的 3 个测试 FAIL（工具不存在；两个拒绝用例因为断言了 stderr 的前缀，也会失败）；实现后 `Ran 29 tests`，`OK`。

```bash
git add local-tools/adt-chosen.py local-tools/tests/test_adt_chosen.py
git commit -m "tools: print the loader's properties of a device tree's /chosen"
```

- [x] **Step 3: 构建固件**

先确认外置盘挂着（`ls <output>/kernel/kernel.macho`），并核对日常文件的哈希：`shasum -a 256 <output>/payload/payload.img <output>/boot/boot.img`，前 8 位应是 `8a36fe56` 和 `35f03ec4`。不是就停下来查，不往下做。

Run: `./unixnu build firmware --os macos-27 --uefi ../uefi-sheng`

核对：`../uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/AARCH64/DarwinBoot.efi` 里能找到 UTF-16LE 的 `DARWINBOOT: window floor=`。把 `../uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd` 复制成 `out/flash/SILICIUM_UEFI.topwin-<sha256 前 8 位>.fd`。

- [x] **Step 4: 构建两份 payload**

准备：`cp <output>/payload/payload.img <output>/payload/payload.daily-8a36fe56.img`，`payload.json` 同样备份；把 OS 镜像只读挂到系统盘上的一个临时目录：`hdiutil attach -readonly -nobrowse -mountpoint "$TMPDIR/os-mount" /Volumes/UniXNUBuild/unixnu-out/ipsw/26C5035r/141-22233-021.dmg`。

对照的一份：在 `../UniXNU-sheng/board.toml` 的保留列表末尾临时加上 `"0x8A0000000:0x20000000"`，然后

Run: `./unixnu build payload --os macos-27 --data-ramdisk /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/runtime/data.dbr`

（如果报 `Data seed UUID differs from the compiled configuration`，改用 `./unixnu build kernel payload …`，并在下面的比对里特别看 `kernel.macho` 是否仍相同。）核对后把 `<output>/payload/payload.img` 复制成 `payload.topwin-k443.img`，再用 `git -C ../UniXNU-sheng checkout board.toml` 还原，`git -C ../UniXNU-sheng diff --stat board.toml` 应为空。

完整的一份：还原后再运行同一条命令，核对，复制成 `payload.topwin.img`。

每一份的核对：
1. 用 `MTOOLS_SKIP_CHECK=1 mcopy -s -n -i <镜像> ::/EFI <临时目录>` 把新的一份和日常的一份各取出来，`diff -rq` 比较。预期只有 `kernel.macho.adt` 不同（里面有随机种子和这次改的属性）。别的文件不同就先查清原因并记进执行记录，再决定能不能上机。
2. `python3 -I local-tools/adt-chosen.py <取出的 kernel.macho.adt>`。完整的一份预期六行：`darwinboot-memory-size 8 0x180000000`、`darwinboot-memory-excluded 1024 64 empty pairs`、`darwinboot-memory-floor 8 0x980000000`、`darwinboot-loader-inputs 64 4 empty pairs`、`darwinboot-memory-outside 256 16 empty pairs`、`darwinboot-memory-outside-kept 32 0xd0000000+0x10000 0x80000000+0x800000000`。对照的一份最后一行是 `darwinboot-memory-outside-kept 48 0xd0000000+0x10000 0x80000000+0x800000000 0x8a0000000+0x20000000`。

收尾：把日常的 payload 放回去（`cp <output>/payload/payload.daily-8a36fe56.img <output>/payload/payload.img`，`payload.json` 同样），核对哈希前 8 位仍是 `8a36fe56`；`hdiutil detach "$TMPDIR/os-mount"`。

- [x] **Step 5: 打包**

```bash
./unixnu bootimg --os macos-27 --dtb /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/tree/build/sheng/sheng.dtb -o /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/boot/boot-topwin.img
cp <output>/boot/boot.good.json <output>/boot/boot.json
python3 -I local-tools/make-bootimg-v4.py <output>/boot/boot-topwin.img ../uefi-sheng/Resources/Scripts/mkbootimg.py out/flash/boot-v4-payload.topwin-k443.img <output>/payload/payload.topwin-k443.img
python3 -I local-tools/make-bootimg-v4.py <output>/boot/boot-topwin.img ../uefi-sheng/Resources/Scripts/mkbootimg.py out/flash/boot-v4-payload.topwin.img <output>/payload/payload.topwin.img
python3 -I local-tools/make-flash-bootimg.py out/flash/boot-v4-payload.topwin.img out/flash/boot-v4-flash.topwin.img
```

Expected: `<output>/boot/boot.img` 的哈希前 8 位仍是 `35f03ec4`；两个 `boot-v4-payload.topwin*.img` 各 210903040 字节；`boot-v4-flash.topwin.img` 不超过 201326592 字节；三个文件的最后一行输出都是 `…: v4, kernel K, ramdisk R, signature 0, N bytes, sha256 H`，三者的 `K` 相同。日常的 `out/flash/boot-v4-flash.img`、`boot-v4-payload.img` 和各个 `.prev*` 的哈希与 `HANDOFF.md` 第 8 节一致。

- [x] **Step 6: 记录并提交**

`HANDOFF.md` 记下：三个新镜像和固件备份的文件名、字节数、sha256；它们都还没有上机；日常文件没有动。

```bash
git add HANDOFF.md
git commit -m "docs: record the top-window images"
```

---

### Task 6: 上机验证（要用户在场并同意）

**Files:**
- Modify: `HANDOFF.md`、`docs/superpowers/specs/2026-11-14-memory-top-window-design.md`（状态行）

**Interfaces:**
- Consumes: Task 5 的 `out/flash/boot-v4-payload.topwin-k443.img` 和 `out/flash/boot-v4-payload.topwin.img`（两者只差保留列表和随机种子）。`out/flash/boot-v4-flash.topwin.img` 只在写 `boot_a` 之前用（Step 6）。

两次内存启动，先对照的一份，再完整的一份。每次都请用户录屏并拍终端。

已知限制（最终审阅发现，2026-11-14）：GPU 驱动用一张页表判断导入的内存会不会和驱动自己的缓冲区冲突（`drivers/Adreno740/NativeAdrenoMemory.cpp:97-116`），这张表只给窗口里的页和物理地址 4 GiB 以下的页编了号。新布局收编的 `0x880000000`–`0x980000000` 不在表里，驱动放在那里的缓冲区查不到，本来会被拒绝的冲突映射会被放过。审阅没有找到越界或 panic 的路径，也没能确定实际会不会遇到。所以这两份镜像上出现的画面错乱或 GPU 卡住，不能直接当成内存的问题。写 `boot_a` 之前要决定改不改驱动（Step 6）。

- [ ] **Step 1: 只读查询**

平板进 fastboot 后：`fastboot -s <序列号> getvar current-slot`（应为 `a`）、`getvar slot-retry-count:a`、`getvar battery-voltage`。重试次数不到 2 时先告诉用户，再执行 `fastboot set_active a`。

- [ ] **Step 2: 内存启动对照的一份**

Run: `python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.topwin-k443.img --serial <序列号>`
Expected: `Booting OKAY`，之后 45 秒 bootloader 没有再响应。

- [ ] **Step 3: 读结果**

从录屏里读加载器的输出（`swift local-tools/ocr-frames.swift`）：

| 屏幕上的行 | 预期 |
| --- | --- |
| `DARWINBOOT: window floor=… start=…` | `floor=0x980000000 start=0x980004000` |
| `DARWINBOOT: ARM64 … pa=… owned=…` | `pa=0x980004000`，`owned=0x180000000` |
| `DARWINBOOT: free memory outside the window: N ranges of 16, …` | 各段里有 `0x880000000 + 0x39d00000`、`0x8b9f00000 + 0x1e00000`、`0x8c0000000 + 0xc0000000` |
| `DARWINBOOT: window head=… usable=… excluded ranges=…` | 记下 `usable` |

进系统后请用户在终端运行 `sysctl hw.memsize kern.boot_payload_memory` 和 `sudo dmesg | grep "memory outside"`。

| 镜像 | 最多收编 | `hw.memsize` 通过线 |
| --- | --- | --- |
| 对照（`k443`） | 917504 页（3.5 GiB） | 不低于 9736028160 |
| 完整 | 1030912 页（3.93 GiB） | 不低于 10200547328 |

键盘用不了、读不到 `dmesg` 时：收编量按 `hw.memsize` 减去屏幕上的 `usable` 估。

`start=` 不是 `0x980004000` 时，说明固件在下限处占了内存，窗口被推高了。这时窗口下面那几段加起来超过 4 GiB，内核一页也不收编，`dmesg` 显示 `memory outside the span: 0 pages adopted, 0 refused`。原因要到下限附近找，不在 `0x880000000` 以下。

- [ ] **Step 4: 试用 30 分钟**

多开几个应用，看有没有卡住、卡死、重启。结束时再读一次 `sysctl hw.memsize vm.swapusage`。

- [ ] **Step 5: 完整的一份**

对照的一份通过后，再用 `out/flash/boot-v4-payload.topwin.img` 重复 Step 2 到 Step 4。用它而不用 `boot-v4-flash.topwin.img`，是因为它和对照的一份是同样的 200 MiB 卷，两次之间只差保留列表，一次只变一件事。

- [ ] **Step 6: 按结果决定下一步**

| 对照的一份 | 完整的一份 | 结论和下一步 |
| --- | --- | --- |
| 稳定 | 稳定 | 路线一可用。写 `boot_a` 之前：先请用户决定 GPU 驱动那一条（上面的"已知限制"）；再从内存启动一次 `boot-v4-flash.topwin.img`（写进 `boot_a` 的就是它，190 MiB 卷），重复 Step 2 到 Step 4；然后问用户是否刷入 |
| 稳定 | 卡住或卡死 | 新列入的 443 MiB 有问题。把那一项保留写进 `board.toml`，重新出刷机用的镜像，约 9.5 GiB |
| 卡住或卡死 | 不做 | 问题在路线一本身，或者和内存无关。按设计文档"失败时怎么办"处理：用 `memory-outside=0` 再启动一次，分清是窗口换位置还是收编 |
| 起不来 | 不做 | 看录屏停在哪一层，按设计文档"失败时怎么办"处理 |

同一个问题试三次还不行，就停下来和用户商量。

- [ ] **Step 7: 记录**

把每次启动的时间、镜像、屏幕读数、`hw.memsize`、试用结果写进 `HANDOFF.md` 第 9 节，更新设计文档的状态行，提交。刷 `boot_a` 要用户明确同意后另做：按 `HANDOFF.md` 第 8 节的办法把现有镜像轮换成 `.prev`，再 `fastboot flash boot_a`。

## 执行结果（Task 1 到 5，2026-11-14）

- Task 1 到 Task 5 完成，都在 Mac 上做，没有动平板。所有提交都在本地分支上，没有 push：
  - 子模块 `drivers/DarwinBoot`（分支 `local/window-floor`）：`bf802ae`、`96cee50`，以及审阅后补测试的提交。
  - UniXNU：`74a17c8`、`39daf83`、`c8697e9`、`f6f3414`，以及审阅后的提交。
  - `../uefi-sheng`：`20331338`。
  - `../UniXNU-sheng`：`4ff0ecf`。
- 镜像、哈希和上机时的预期读数见 `HANDOFF.md` 第 9 节"路线一的主机部分"。Task 6 还没做。

### 执行中的偏差和裁决（原记在 git 忽略的执行记录里，这里抄一份）

- 没有另开 git worktree，直接在 `local/sheng-16g-macos` 上做，因为 `./unixnu`、`unixnu.local.toml` 和两个兄弟仓库都按这个路径找。代价是两个兄弟仓库和固件构建目录现在停在路线一的状态。怎样回到日常状态写在 HANDOFF 里。
- 执行方式是我定的：交接时用户没有选，我按"本会话内逐任务做"执行。理由是设计已确认，Task 1 到 5 只在 Mac 上做、可以回退，Task 6 要等用户。用户的全局说明在能用子代理时优先"每个任务一个子代理，加两段审阅"；这次只在最后做了一次整体审阅。审阅找到的第 2 条（衔接处没有测试）正是逐任务审阅会查的那类问题。
- Task 1：计划里的"先失败"是编译错误（参数还不存在），不是断言失败。所以另外把裁剪那一行删掉跑了一次，下限的断言确实失败（`AssertionError`），然后恢复。
- Task 2：计划说"前五个结果和没有下限时相同"。这只在下限排在排除表后面时成立，因为排除表的偏移就是它在树里的位置。所以测试在这种顺序下比较全部五个结果；另外两种顺序下，只检查偏移仍然指向排除表。
- Task 5：`./unixnu build payload` 每跑一次都会重新生成 GPU 附加包和信任缓存，输入相同、连跑两次也不一样。所以"只有设备树不同"对构建出来的 payload 不成立。两份新 payload 都是日常 payload 的副本，只用 `mcopy` 换了 `kernel.macho.adt`，逐个文件核对过。审阅确认加载器和构建里没有任何东西（哈希、大小、清单）把设备树和卷里的其他文件绑在一起。
- Task 5：OS 镜像挂在会话的临时目录下，而不是 `$TMPDIR`，因为沙箱内外的 `$TMPDIR` 不一样。这对产物没有影响。

### 最终审阅（2026-11-14 约 21:00）

一个新的审阅者读了四个仓库的全部改动，重跑了测试，做了 35 处变异，并解码了构建出的设备树。结论是没有严重问题，可以只从内存启动做 Task 6，但写 `boot_a` 之前要先处理第 1 条。

- 重要 1：GPU 驱动的页表不覆盖 4 GiB 以上的收编内存，见上面 Task 6 的"已知限制"。这次没有改。原因有两个：改驱动不在已确认的设计里（设计只改四处）；而且要重新生成 GPU 附加包，测试镜像和日常镜像之间就会多一个变量。写 `boot_a` 之前请用户决定。
- 重要 2：从 `board.toml` 到窗口的几处衔接没有自动测试；还有一个测试通过的原因不对（`test-adt-window.py` 的包装函数自己调用了 `AdtWindowConsistent`）。为此补了两个测试，都先用变异看到失败、恢复后再看到通过：
  - `test_top_window_layout.py` 的 `test_generated_tree_carries_the_floor_and_the_kept_ranges`：用板级配置的真实选项走一遍 `generate()`，再用 `adt-chosen.py` 读回 `/chosen`。去掉 `chosen += memory_floor(options)`，或者把保留区间写成"大小在前、起点在后"，测试都会失败。
  - `test-adt-window.py` 末尾从源码检查 `Boot`：解析之后马上拒绝"有下限、没有排除表"的树；`AllocateSpan` 收到下限，并交给 `DarwinWindowStart`。删掉那一行检查，或者在 `Boot` 或 `AllocateSpan` 里传 0，测试都会失败。
  - 没有加"分配之后起点低于下限就拒绝"的检查：那要改 `DarwinBoot.c`，再重新构建固件和三份镜像。审阅者已经逐处读过现在的代码，是对的；上机时屏幕上的 `start=` 一行也会直接显示起点。留到上机之后再说。
- 第 4、7、8 条是审阅者标的小问题，我按实际影响改成要处理，已改：
  - 第 4 条：HANDOFF 里关于固件构建目录的旧说法改正了，并写明怎样回到日常状态。
  - 第 7 条：Task 6 第 5 步改用 `boot-v4-payload.topwin.img`，一次只变一件事。
  - 第 8 条：HANDOFF 里的预期读数注明是按模型算的。
  - 另外，第 3 条里讲怎样诊断的那句话写进了 Task 6 Step 3。
- 推迟的小问题：
  - 第 3 条的另一半：下限处只要有一个固件页，收编就整个关掉，这个后果没有测试（加载器那一侧有测试）。
  - `floor=MAX` 的断言偏弱：把溢出检查挪到裁剪前面也能通过。补一个低地址的空闲段就能测出来。
  - 窗口外那张表的格数（16）和窗口大小（6 GiB）都没有测试钉住。
  - 设计文档第 126 行还写着 `vm.outside_memory`，这个 sysctl 不存在。
  - 两份配置文档把 `owned_memory_floor` 的类型写成字符串，其实整数也接受。
  - 第一个 `/chosen` 没有下限时，第二个 `/chosen` 里的下限会被接受。不过生成器不会写两个 `chosen`，`adt-chosen.py` 也拒绝这种树。
  - `owned_memory_floor` 拼错时，既不生成属性也不报错。这个文件里的选项都是这样。
