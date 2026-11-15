# sheng 内存路线 A：把内核窗口做大 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把这台 12 GiB 平板的内核窗口从 6 GiB 加到 9 GiB（`0x8C0000000`–`0xB00000000`），再加上低位内存区的收编，让 `hw.memsize` 从 5.95 GiB 提高到约 9.4 GiB，并分四步在平板上验证。

**Architecture:** 内核只改一个常量（引导页表 16 页改 22 页）。生成器和加载器的窗口上限从 8 GiB 改成 9 GiB。板级配置填新的窗口、下限、保留列表，并用 `vm_compression_limit` 钉住压缩器。内核只编一次；各步的镜像都是同一份载荷的副本，只换设备树里的两个数和启动参数。

**Tech Stack:** XNU 补丁（diff 文件）；C（EDK II 加载器，主机上用 clang 编测试）；Python 3 标准库（`python3 -I -B`）；GNU mtools；`./unixnu`；`fastboot`。

**Spec:** `docs/superpowers/specs/2026-11-15-memory-large-window-design.md`（用户 2026-11-15 确认："开始实施验证"）

## Global Constraints

- 内核只改 `patches/xnu-12377/native-4k-bootstrap-capacity.patch` 里的一个常量和它的注释，别的内核源码、补丁、驱动都不改。
- 本计划的镜像只从内存启动（`local-tools/boot-sheng.py`）。写 `boot_a` 不在本计划的自动步骤里，要用户当次明确同意。
- 上机（Task 6）每一次都要用户在场并当次说可以开始。Task 1 到 Task 5 只在 Mac 上做。
- 不切槽位 b；`fastboot set_active a` 只在重试次数降到 2 或以下时用（用户已允许）。不刷也不启动带 `data-reset` 的镜像。不碰 `userdata`、abl、xbl。
- 日常那一套不覆盖：`out/flash/boot-v4-flash*.img`、`out/flash/boot-v4-payload*.img`、`<output>/boot/boot.img`（sha256 前 8 位 `35f03ec4`）、`<output>/boot/boot.json`、`<output>/payload/payload.img`（`8a36fe56`）、`<output>/kernel/kernel.macho`（`33d294c8`）。构建会改写的，构建完用备份还原并核对哈希。新文件名一律带 `bigwin`。
- `<output>` 指 `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos`。
- 芯片序列号不写进任何文件或提交，文档里写 `<序列号>`。每次提交前在 diff 里搜一遍。
- 只在本地分支提交，逐个列出文件，不 push：
  - UniXNU：`local/sheng-16g-macos`。
  - 子模块 `drivers/DarwinBoot`：新分支 `local/window-9g`（从 `local/window-floor` 的 `3cd02b2` 起）。不提交 `Test/__pycache__/`。
  - `../UniXNU-sheng`：新分支 `local/sheng-12g-large-window`（从 `4ff0ecf` 起），只提交 `board.toml`。工作区里别的改动不带上。
  - `../uefi-sheng` 不改。
- `drivers/Adreno740` 保持在 `462dd74`，`drivers/AdrenoMetal` 保持在 `73d582f`。
- Python 一律 `python3 -I -B`，只用标准库。`./unixnu …` 在 `UniXNU/` 下按原样执行（不加 `cd`、管道、变量前缀），关沙箱。`fastboot`、`hdiutil`、写兄弟仓库和外置盘也要关沙箱。
- 提交信息末尾带 `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`。

## Review Focus

1. 板级保留列表里漏掉或写错高位内存区那一项：内核一页也不收编，而且不报错。期望测试直接失败（Task 4：`test_without_the_bank_1_kept_range_nothing_is_adopted`、`test_kernel_adopts_only_the_low_bank`）。
2. 生成器、加载器、引导页表三个上限不一致（比如工具放行 9 GiB，页表只够 8 GiB）：期望主机测试把三者钉在一起（Task 1：`test_capacity_covers_the_tool_bound`；Task 2：`test_loader_bound_matches_the_generator`）。
3. 做变体载荷时输出覆盖了输入或日常文件、要改的属性不存在或不是 8 字节、参数行超过 1000 字节：工具拒绝，不留下半成品（Task 3）。
4. 变体载荷带上了 `data-reset`：工具拒绝这个参数名，输入的参数行里已有它时也拒绝（Task 3：`test_refuses_data_reset`）。
5. 补丁改完后行数变了、打不上：期望主机测试在构建之前就发现（Task 1：`test_first_hunk_still_adds_five_lines`）。

---

### Task 1: 内核补丁，引导页表 16 页改 22 页

**Files:**
- Modify: `patches/xnu-12377/native-4k-bootstrap-capacity.patch`（第一个 hunk 里的常量和三行注释）
- Create: `local-tools/tests/test_bootstrap_tables.py`

**Interfaces:**
- Produces（测试文件内部）：`bootstrap_pages(phys_base: int, size: int, virt_base: int | None = None) -> int`。返回 `2 + P + V`：`P` 是 `[phys_base 向下取 2 MiB, 加 size)` 碰到的 1 GiB 区域个数；`V` 在给了 `virt_base` 时同样算，没给时取最坏情况 `ceil(size / 1 GiB) + 1`。

- [ ] **Step 1: 写失败的测试**

常量：`LINK = 0xfffffff007004000`，`PATCH = ROOT / 'patches/xnu-12377/native-4k-bootstrap-capacity.patch'`，`GENERATOR_BOUND = 0x240000000`。

| 测试 | 断言 |
| --- | --- |
| `test_patch_reserves_22_pages` | 补丁里以 `+#define BOOTSTRAP_TABLE_SIZE (ARM_PGBYTES * ` 开头的行正好一行，数字是 22 |
| `test_first_hunk_still_adds_five_lines` | 第一个 hunk 的头是 `@@ -115,6 +115,11 @@`，它下面到下一个 `diff --git` 之前有 5 行以 `+` 开头、6 行以空格开头 |
| `test_planned_windows_at_the_link_address` | `bootstrap_pages(0x980004000, 0x180000000, LINK) == 15`；`(0x920004000, 0x1E0000000, LINK) == 18`；`(0x8C0004000, 0x240000000, LINK) == 21`；`(0x900004000, 0x200000000, LINK) == 19` |
| `test_planned_windows_with_the_worst_virtual_base` | 同样四个窗口不给 `virt_base`：15、19、21、19 |
| `test_sixteen_pages_were_not_enough` | 第 1 步和第 2 步的窗口在两种算法下都大于 16 |
| `test_capacity_covers_the_tool_bound` | 对 `GENERATOR_BOUND` 大小的窗口，物理起点取 `0x880000000 + k * 0x200000`（k 从 0 到 511）时，最坏情况的页数最大值正好是补丁里的数字 |

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `test_patch_reserves_22_pages` 和 `test_capacity_covers_the_tool_bound` FAIL（现在是 16）；其余新测试通过；原有 32 个通过。

- [ ] **Step 3: 改补丁**

第一个 hunk 里：`ARM_PGBYTES * 16` 改成 `ARM_PGBYTES * 22`；注释三行改成说明"两个根，加上每遍映射最多十个二级页，9 GiB；物理和虚拟的起点各可能多跨一个 1 GiB 区域"。注释仍是三行，hunk 头不动。别的 hunk 不动。

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 38 tests`，`OK`。

- [ ] **Step 5: 提交**

```bash
git add patches/xnu-12377/native-4k-bootstrap-capacity.patch local-tools/tests/test_bootstrap_tables.py
git commit -m "feat(xnu): 22 bootstrap table pages, enough for a 9 GiB window"
```

---

### Task 2: 生成器和加载器的窗口上限改成 9 GiB

**Files:**
- Modify: `scripts/unixnu/devicetree.py`（第 340–344 行的检查抽成函数）
- Create: `local-tools/tests/test_devicetree_window_size.py`
- Modify（子模块）: `drivers/DarwinBoot/DarwinBootPkg/Driver/WindowSize.h`、`drivers/DarwinBoot/Test/window-size.c`、`drivers/DarwinBoot/Test/make-fixtures.py:85`

**Interfaces:**
- Produces: `devicetree.memory_size(options) -> list[tuple[str, bytes]]`。没有 `owned_memory_size` 时返回 `[]`；合法时返回 `[('darwinboot-memory-size', struct.pack('<Q', size))]`；不在 `0x10000000`–`0x240000000` 或不是 `0x200000` 的倍数时抛 `Error('Owned memory must be 256 MiB to 9 GiB in 2 MiB steps')`。`generate()` 在原来的位置用 `chosen += memory_size(options)`，属性顺序不变。

- [ ] **Step 1: 在子模块里建分支**

Run: `git -C drivers/DarwinBoot switch -c local/window-9g`

- [ ] **Step 2: 写失败的测试**

`local-tools/tests/test_devicetree_window_size.py`（写法照 `test_devicetree_floor.py`）：

| 测试 | 断言 |
| --- | --- |
| `test_absent_gives_no_property` | `memory_size({}) == []` |
| `test_accepts_the_bounds` | `'0x10000000'`、`'0x180000000'`、`'0x200000000'`、`'0x240000000'`、整数 `0x1E0000000` 都返回对应的 8 字节小端值 |
| `test_refuses_above_9_gib` | `'0x240200000'`、`'0x280000000'` 抛 `Error`，信息以 `Owned memory must be 256 MiB to 9 GiB` 开头 |
| `test_refuses_too_small_and_off_grid` | `'0xfe00000'`、`'0x10001000'` 抛 `Error` |
| `test_loader_bound_matches_the_generator` | `WindowSize.h` 的文本里有 `0x240000000ULL`，没有 `0x200000000ULL` |

`drivers/DarwinBoot/Test/window-size.c`：`yes` 里加 `0x240000000ULL`（`0x200000000ULL` 保留）；`no` 里的 `0x200200000ULL` 换成 `0x240200000ULL`。

- [ ] **Step 3: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: 新的 5 个测试 ERROR 或 FAIL（`devicetree` 没有 `memory_size`；头文件里还是 8 GiB）。

Run: `cc -Wall -Wextra -Werror drivers/DarwinBoot/Test/window-size.c -o "$TMPDIR/window-size" && "$TMPDIR/window-size"`
Expected: 断言失败退出（`0x240000000ULL` 还不被接受）。

- [ ] **Step 4: 实现**

- `devicetree.py`：加 `memory_size(options)`（放在 `memory_floor` 上面），`generate()` 里那五行换成 `chosen += memory_size(options)`。
- `WindowSize.h`：`0x200000000ULL` 改成 `0x240000000ULL`。
- `make-fixtures.py:85`：`large-memory-window` 的 `0x200200000` 改成 `0x240200000`。

- [ ] **Step 5: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 43 tests`，`OK`。

Run: `cc -Wall -Wextra -Werror drivers/DarwinBoot/Test/window-size.c -o "$TMPDIR/window-size" && "$TMPDIR/window-size" && for t in test-memory-window test-memory-outside test-adt-window test-loader-inputs test-kernel-parser; do python3 -I -B drivers/DarwinBoot/Test/$t.py || echo "FAILED $t"; done`
Expected: 五行 `PASS: …`，没有 `FAILED`，没有断言失败。

- [ ] **Step 6: 提交（先子模块，再主仓库）**

```bash
git -C drivers/DarwinBoot add DarwinBootPkg/Driver/WindowSize.h Test/window-size.c Test/make-fixtures.py
git -C drivers/DarwinBoot commit -m "feat(boot): accept a window of up to 9 GiB"
git add scripts/unixnu/devicetree.py local-tools/tests/test_devicetree_window_size.py drivers/DarwinBoot
git commit -m "feat(devicetree): owned_memory_size up to 9 GiB"
```

`scripts/check-darwinboot-window-parser.py` 不动：它要导入的 `scripts/make-sheng-adt.py` 已经不在这个仓库里，`AdtNode` 的参数也对不上，现在就跑不起来（2026-11-15 核对）。`../UniXNU-sheng/scripts/make-sheng-adt.py` 也不动。

---

### Task 3: 做变体载荷的工具

**Files:**
- Create: `local-tools/make-payload-variant.py`
- Create: `local-tools/tests/test_make_payload_variant.py`

**Interfaces:**
- Produces: 命令行

  ```
  python3 -I local-tools/make-payload-variant.py BASE OUT [--set NAME=VALUE]... [--arg NAME=VALUE]...
  ```

  - 把载荷卷 `BASE` 复制成 `OUT`，然后只改两个文件：`::/EFI/UniXNU/Payloads/kernel.macho.adt` 和 `::/EFI/UniXNU/unixnu.toml`。写回用 `MTOOLS_SKIP_CHECK=1 TZ=UTC mcopy -D o -Q -m -i OUT 文件 ::路径`。
  - `--set`：把设备树 `/chosen` 下名为 `NAME` 的 8 字节属性改成 `VALUE`（`int(VALUE, 0)`，小端 64 位）。文件长度不变。`NAME` 必须以 `darwinboot-` 开头，在 `/chosen` 里正好出现一次，现有长度是 8。
  - `--arg`：把 `NAME=VALUE` 加在 `unixnu.toml` 里每一行 `args = "…"` 的最前面。
  - 成功时最后一行输出 `OUT: N bytes, sha256 H, adt: <各 --set 的 名字=新值>, args: <加上的参数>`，退出码 0。
  - 拒绝时以非 0 退出，stderr 以 `make-payload-variant: ` 开头，不留下 `OUT`（先写到 `OUT.tmp`，成功后改名）。拒绝的情况：
    - `OUT` 已存在，或与 `BASE` 是同一个文件；`BASE` 不存在。
    - 既没有 `--set` 也没有 `--arg`。
    - `--set` 的属性不存在、出现多次、长度不是 8、名字不以 `darwinboot-` 开头，值不是 0 到 2^64-1 的整数。
    - `--arg` 的名字是 `data-reset`；现有参数行里已经有 `data-reset`；现有参数行里已经有同名参数；参数不匹配 `[A-Za-z0-9_.\-]+(=[A-Za-z0-9_.,/\-:=]+)?`；加上之后任何一行 `args` 的内容超过 1000 字节；文件里没有 `args = "` 行。
  - 写完后自己核对：从 `OUT` 取回这两个文件，和要写的内容逐字节相同；`OUT` 里其余文件的相对路径和 sha256 与 `BASE` 完全相同。不同就按拒绝处理。

- [ ] **Step 1: 写失败的测试**

`local-tools/tests/test_make_payload_variant.py`，把工具当子进程调用。夹具：照 `local-tools/tests/test_make_flash_bootimg.py` 的写法建一个 64 MiB 的 FAT 卷（`mformat -C -F -T <扇区数> … -i 卷 ::`，环境 `MTOOLS_SKIP_CHECK=1 TZ=UTC`），在 `::/EFI/UniXNU/` 和 `::/EFI/UniXNU/Payloads/` 下放进三个文件：

- `kernel.macho.adt`：用 `unixnu.devicetree.node` 造，`/chosen` 带 `random-seed`、`darwinboot-memory-size`（`0x240000000`）、`darwinboot-memory-excluded`（1024 个零字节）、`darwinboot-memory-floor`（`0x8C0000000`）；`chosen` 前面另有一个节点带同名的 `darwinboot-memory-floor`。
- `unixnu.toml`：两个启动项，各一行 `args = "debug=0x14e vm_compression_limit=1572864"`。
- `kernel.macho`：1 MiB 的固定字节。

| 测试 | 断言 |
| --- | --- |
| `test_sets_two_properties_and_prepends_an_argument` | `--set darwinboot-memory-size=0x1E0000000 --set darwinboot-memory-floor=0x920000000 --arg memory-outside=0`：退出码 0；从 `OUT` 取出的设备树用 `local-tools/adt-chosen.py` 读是 `darwinboot-memory-size 8 0x1e0000000`、`darwinboot-memory-excluded 1024 64 empty pairs`、`darwinboot-memory-floor 8 0x920000000`；设备树长度不变，`chosen` 前面那个节点里的同名属性没变；`unixnu.toml` 两行都是 `args = "memory-outside=0 debug=0x14e vm_compression_limit=1572864"`；`kernel.macho` 的 sha256 没变；`BASE` 的 sha256 没变 |
| `test_argument_only` | 只有 `--arg memory-outside=0`：设备树逐字节不变 |
| `test_refuses_existing_output_and_same_file` | `OUT` 已存在、`OUT` 等于 `BASE`：非 0，stderr 前缀对，已存在的 `OUT` 内容不变 |
| `test_refuses_bad_property` | 不存在的名字、`random-seed`（不以 `darwinboot-` 开头）、`darwinboot-memory-excluded`（长度不是 8）、值 `-1`、值 `0x10000000000000000`：都非 0，没有留下 `OUT` 和 `OUT.tmp` |
| `test_refuses_data_reset` | `--arg data-reset=1` 被拒绝；夹具的参数行里有 `data-reset=1` 时任何调用都被拒绝 |
| `test_refuses_duplicate_and_malformed_arguments` | `--arg debug=0x1`（已有同名）、`--arg 'a b=1'`、`--arg 'x="y"'` 被拒绝 |
| `test_refuses_line_over_1000_bytes` | 夹具的参数行是 990 字节时 `--arg memory-outside=0` 被拒绝 |
| `test_refuses_nothing_to_do` | 没有 `--set` 也没有 `--arg`：非 0 |

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: 新的 8 个测试 FAIL（工具不存在）。

- [ ] **Step 3: 实现工具**

设备树的读法照 `local-tools/adt-chosen.py` 的 `read_node`（节点头是两个小端 32 位数：属性个数、子节点个数；每个属性是 32 字节名字、4 字节长度（只取低 31 位）、值，按 4 字节补齐）。本工具只需要找到 `/chosen` 下目标属性的值在文件里的偏移，原地改 8 个字节。

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 51 tests`，`OK`。

- [ ] **Step 5: 提交**

```bash
git add local-tools/make-payload-variant.py local-tools/tests/test_make_payload_variant.py
git commit -m "tools: derive a payload that differs in window values and arguments only"
```

---

### Task 4: 板级的值，和整机布局的主机测试

**Files:**
- Modify: `../UniXNU-sheng/board.toml`（`["os_overrides"."macos-27.3-26C5035r"."payload"]` 的 `kernel_args`，和 `…"payload"."adt"` 一段）
- Rename + modify: `local-tools/tests/test_top_window_layout.py` 改名为 `local-tools/tests/test_window_layout.py`

**Interfaces:**
- Consumes: Task 2 的 `devicetree.memory_size`；现有的 `devicetree.memory_floor`、`devicetree.generate`、`payload.check_args(arguments) -> str`；测试文件里现有的 `firmware_free()`、`memory_map(free)`、`adopted(pairs, kept, phys_base)`、`flattened(HARDWARE)` 和编译加载器头文件的 `setUpClass`。
- Produces（测试类内部）：`window(free, size=None, floor=None)`，给了 `size`、`floor` 时用它们代替板级的值；`outside(free)`、`adoption(free, kept=None)` 不变。

- [ ] **Step 1: 改名并改写测试**

Run: `git mv local-tools/tests/test_top_window_layout.py local-tools/tests/test_window_layout.py`

类名改成 `LargeWindowLayout`，文件开头的说明改成新布局。常量：`WINDOW = 0x8C0004000`，`LOW_RUNS = [(0xbab00000, 0xccd00000), (0xccf80000, 0xd0000000), (0xd0010000, 0xd8000000), (0xe6720000, 0xff800000)]`，`LOW_SPAN = (0xbaa00000, 0xff800000)`。下面的数字是 2026-11-15 用现在的固件内存表在模型上算出来的。

| 测试 | 断言 |
| --- | --- |
| `test_firmware_table_lists_bank_1_to_the_top` | 不变 |
| `test_board_window_is_the_9_gib_run` | 板级 `owned_memory_size` 是 `0x240000000`、`owned_memory_floor` 是 `0x8C0000000`；窗口起点是 `0x8C0004000` |
| `test_planned_windows_start_at_their_floors` | `window(free, size, floor)`：`(0x1E0000000, 0x920000000)` 得 `0x920004000`；`(0x180000000, 0x980000000)` 得 `0x980004000`；`(0x1E0000000, 0x8C0000000)` 得 `0x8C0004000`；`(0x200000000, 0x900000000)` 得 `0x900004000` |
| `test_generator_accepts_the_board_options` | `memory_floor(adt) == [('darwinboot-memory-floor', pack('<Q', 0x8C0000000))]`；`memory_size(adt) == [('darwinboot-memory-size', pack('<Q', 0x240000000))]` |
| `test_generated_tree_carries_the_window_and_the_kept_ranges` | `adt-chosen.py` 读回六行：`darwinboot-memory-size 8 0x240000000`、`darwinboot-memory-excluded 1024 64 empty pairs`、`darwinboot-memory-floor 8 0x8c0000000`、`darwinboot-loader-inputs 64 4 empty pairs`、`darwinboot-memory-outside 256 16 empty pairs`、`darwinboot-memory-outside-kept 32 0xd0000000+0x10000 0x880000000+0x280000000` |
| `test_kernel_adopts_only_the_low_bank` | `adoption(free)` 的各段是 `LOW_RUNS`，区是 `LOW_SPAN`，总字节数 `0x36350000`；每段的末尾不超过 `0x100000000` |
| `test_without_the_bank_1_kept_range_nothing_is_adopted` | 板级保留列表里有 `"0x880000000:0x280000000"`；`adoption(free, kept=[(0xd0000000, 0x10000)]) == ([], None)` |
| `test_bank_1_stays_out_whatever_the_low_bank_looks_like` | 低位换成一整段 `0x80000000`–`0x100000000` 的空闲内存：各段是 `[(0x80000000, 0xd0000000), (0xd0010000, 0x100000000)]`，区是 `(0x80000000, 0x100000000)`。低位换成 20 段 16 MiB（`0x90000000 + i * 0x2000000`）：窗口外的表是 16 段，收编 14 段，总字节数 `0xE000000`，每段末尾不超过 `0x100000000` |
| `test_command_line_fits_with_the_run_arguments` | 板级 macOS 的 `kernel_args` 里有 `vm_compression_limit=1572864`，没有名字是 `memory-outside` 或 `data-reset` 的项；`payload.check_args(['vm-swapin-io=1', 'memory-outside=0'] + kernel_args)` 不抛错，长度是 923 |

原来的 9 个测试里：1 个不变；2 个改写（`test_generator_accepts_the_board_options`，以及改名为 `test_generated_tree_carries_the_window_and_the_kept_ranges` 的那个）；另外 6 个只对路线一成立，删掉，由上表其余 6 个替代：`test_window_starts_at_the_floor`、`test_kernel_adopts_the_three_runs_below_the_window`、`test_everything_below_bank_1_is_kept_out`、`test_without_the_new_kept_range_nothing_is_adopted`、`test_keeping_the_newly_listed_memory_out`、`test_fragmented_low_bank_keeps_the_span`。测试总数不变。

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `LargeWindowLayout` 里除 `test_firmware_table_lists_bank_1_to_the_top` 和 `test_planned_windows_start_at_their_floors` 之外的测试 FAIL（板级还是路线一的值）；没有 ERROR。

- [ ] **Step 3: 改板级配置**

Run: `git -C ../UniXNU-sheng switch -c local/sheng-12g-large-window`

`board.toml`：
- macOS 27.3 的 `kernel_args` 末尾加 `"vm_compression_limit=1572864"`；上面的注释加一句说明：压缩器的池钉在 6 GiB（4 KiB 页的页数），窗口变大时它预留的内核地址不跟着变大。
- `"owned_memory_size" = "0x240000000"`，`"owned_memory_floor" = "0x8C0000000"`，`"owned_memory_outside_reserved" = ["0xd0000000:0x10000", "0x880000000:0x280000000"]`；`owned_memory_excluded_ranges`（64）、`loader_inputs`、`owned_memory_outside_ranges`（16）不变。
- 这一段的两处注释改写：窗口是 `0x8C0000000`–`0xB00000000` 的 9 GiB，引导页表补丁的 22 页正好够；高位内存区在窗口下面的两段（`0x880000000`–`0x8BBD00000`）整个保留，内核只收编低位内存区；保留它的原因有两个，一是 2026-11-14 上机时这一段不稳，二是不保留的话合成的区超过 4 GiB，内核一页也不收；这组值只对 12 GiB 机型成立。

- [ ] **Step 4: 运行，确认通过**

Run: `python3 -I -B -m unittest discover -s local-tools/tests -v`
Expected: `Ran 51 tests`，`OK`，没有 `skipped`。

- [ ] **Step 5: 提交（两个仓库）**

```bash
git -C ../UniXNU-sheng add board.toml
git -C ../UniXNU-sheng diff --cached --stat   # 只应有 board.toml
git -C ../UniXNU-sheng commit -m "feat(sheng): a 9 GiB window on the 12 GiB unit, low bank adopted"
git add local-tools/tests/test_window_layout.py
git commit -m "test: the large-window layout of the 12 GiB sheng unit"
```

---

### Task 5: 构建内核、固件和各步的镜像（主会话做，要关沙箱）

**Files:**
- Modify: `HANDOFF.md`（第 9 节记下新文件、哈希和构建时各仓库的提交）
- 产物（不入库）：见下表。

**Interfaces:**
- Consumes: Task 1 到 Task 4 的全部提交；Task 3 的工具。
- Produces: 五份只从内存启动的镜像。

  | 镜像（`out/flash/` 下） | 固件的 v0 镜像 | 载荷（`<output>/payload/` 下） | 载荷怎么来 |
  | --- | --- | --- | --- |
  | `boot-v4-payload.bigwin-s1.img` | `<output>/boot/boot-topwin.img`（现成的 `e168abab`） | `payload.bigwin-s1.img` | 基准载荷 `--set darwinboot-memory-size=0x1E0000000 --set darwinboot-memory-floor=0x920000000 --arg memory-outside=0` |
  | `boot-v4-payload.bigwin-s1b.img` | `<output>/boot/boot-bigwin.img`（新固件） | 同上 | 同上 |
  | `boot-v4-payload.bigwin-s2.img` | 新固件 | `payload.bigwin-s2.img` | 基准载荷 `--arg memory-outside=0` |
  | `boot-v4-payload.bigwin-s3.img` | 新固件 | `payload.bigwin-base.img` | 基准载荷本身 |
  | `boot-v4-payload.bigwin-ctl6.img`（对照） | 现成的 `e168abab` | `payload.bigwin-ctl6.img` | 基准载荷 `--set darwinboot-memory-size=0x180000000 --set darwinboot-memory-floor=0x980000000 --arg memory-outside=0` |

  另做两份载荷备用，要用时再打成镜像：`payload.bigwin-split.img`（`0x1E0000000`、`0x8C0000000`、`memory-outside=0`）和 `payload.bigwin-8g.img`（`0x200000000`、`0x900000000`、`memory-outside=0`）。

- [ ] **Step 1: 看上游有没有合进 22 页的改动**

Run: `git fetch upstream`，然后 `git log upstream/main --oneline -S'ARM_PGBYTES * 22' -- patches/`
有结果：把上游那个补丁里的常量和注释与 Task 1 的逐字比较，不同就改成上游的写法（数字应当相同），重跑 Task 1 的测试并补一个提交。没有结果：记进 `HANDOFF.md`，继续。不合并 `upstream/main`。

- [ ] **Step 2: 构建前核对**

`ls <output>/kernel/kernel.macho`（外置盘挂着）；`shasum -a 256 <output>/kernel/kernel.macho <output>/payload/payload.img <output>/boot/boot.img` 的前 8 位是 `33d294c8`、`8a36fe56`、`35f03ec4`，三份备份（`kernel.macho.daily-33d294c8`、`payload.daily-8a36fe56.img`、`boot.good.json`）都在。不符就停下来查。记下四个仓库和三个子模块的提交。

- [ ] **Step 3: 构建内核和基准载荷**

把 OS 镜像只读挂上：`hdiutil attach -readonly -nobrowse -mountpoint <会话临时目录>/os-mount /Volumes/UniXNUBuild/unixnu-out/ipsw/26C5035r/141-22233-021.dmg`。

Run: `./unixnu build kernel payload --os macos-27 --data-ramdisk /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/runtime/data.dbr`

核对：
- `nm -n <output>/kernel/kernel.macho | grep -A1 ' _bootstrap_pagetables$'`：两行地址相差 `0x16000`（现在的日常内核是 `0x10000`）。
- 内核里仍能搜到 `memory-outside-report`。
- 构建日志的 `kernel args:` 一行里有 `vm_compression_limit=1572864` 和 `vm-swapin-io=1`，没有 `memory-outside`、`data-reset`。
- 新载荷和 `<output>/payload/payload.topwin-adopt3g-diag-report0.img` 那一类昨晚的诊断载荷逐个文件比较：`kernel.macho.vroot`、`scratch-data.img` 相同；`kernel.macho`、`.adt`、`.crypto-hmac.json`、`.gpuaddon`、`.trustcache`、`unixnu.toml` 不同。别的不同就先查清。
- `python3 -I local-tools/adt-chosen.py <取出的 kernel.macho.adt>` 输出 Task 4 表里那六行。

另存：`<output>/kernel/kernel.macho` 复制成 `kernel.macho.bigwin-<sha256 前 8 位>`（`kernel.json`、`kernel.map.json` 同后缀）；`<output>/payload/payload.img` 复制成 `payload.bigwin-base.img`（`payload.json` 同样）。然后把日常的内核和载荷从备份复制回去，核对哈希前 8 位仍是 `33d294c8`、`8a36fe56`；`hdiutil detach` OS 镜像。

- [ ] **Step 4: 做各份变体载荷**

对上表每一份运行 `python3 -I local-tools/make-payload-variant.py <output>/payload/payload.bigwin-base.img <output>/payload/<名字> …`。每份做完用 `adt-chosen.py` 读一次设备树，并取出 `unixnu.toml` 看参数行：带 `memory-outside=0` 的在最前面，都没有 `data-reset`。

- [ ] **Step 5: 构建新固件并打包**

Run: `./unixnu build firmware --os macos-27 --uefi ../uefi-sheng`

核对：`../uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/AARCH64/DarwinBoot.efi` 的修改时间晚于 Task 2 的提交；里面仍能找到 UTF-16LE 的 `DARWINBOOT: window floor=`。把 `../uefi-sheng/Build/shengPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd` 复制成 `out/flash/SILICIUM_UEFI.bigwin-<sha256 前 8 位>.fd`。

```bash
./unixnu bootimg --os macos-27 --dtb /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/tree/build/sheng/sheng.dtb -o /Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos/boot/boot-bigwin.img
cp <output>/boot/boot.good.json <output>/boot/boot.json
python3 -I local-tools/make-bootimg-v4.py <固件的 v0 镜像> ../uefi-sheng/Resources/Scripts/mkbootimg.py out/flash/<镜像名> <output>/payload/<载荷名>   # 上表五份各一次
```

Expected: `<output>/boot/boot.img` 的哈希前 8 位仍是 `35f03ec4`；五个镜像各 210903040 字节；`make-bootimg-v4.py` 的最后一行是 `…: v4, kernel K, ramdisk R, signature 0, N bytes, sha256 H`，用同一个固件的镜像 `K` 相同。`out/flash/` 下日常那几份的哈希与 `HANDOFF.md` 第 8 节一致。

- [ ] **Step 6: 记录并提交**

`HANDOFF.md` 第 9 节记下：新内核、新固件、七份载荷、五个镜像的文件名、字节数、sha256；构建时各仓库和子模块的提交；它们都还没有上机；日常文件没有动；固件构建目录现在停在新固件上；`scripts/check-darwinboot-window-parser.py` 现在跑不起来、没有跟着改。

```bash
git add HANDOFF.md
git commit -m "docs: record the large-window kernel, firmware and images"
```

---

### Task 6: 上机验证（每一次都要用户在场并当次同意）

**Files:**
- Modify: `HANDOFF.md`、`docs/superpowers/specs/2026-11-15-memory-large-window-design.md`（状态行）

**Interfaces:**
- Consumes: Task 5 的五个镜像和两份备用载荷。

做法、通过标准和失败时的分支都照设计文档的"上机步骤和通过标准"和"失败时怎么办"，这里只列顺序和每一步用哪个镜像。

- [ ] **Step 1: 基线**

用户在日常系统里照设计"每次上机的做法"第 2 到 5 条做一次，计时满 30 分钟。把读数和有没有卡顿（连同当时内存压力的颜色）记进 `HANDOFF.md`。主机不用做任何事。

- [ ] **Step 2: 第 1 步，`boot-v4-payload.bigwin-s1.img`，三次**

每次先在 fastboot 里只读查询：`fastboot -s <序列号> getvar current-slot`（应为 `a`）、`getvar slot-retry-count:a`、`getvar battery-voltage`；核对镜像的 sha256。

Run: `python3 -I local-tools/boot-sheng.py out/flash/boot-v4-payload.bigwin-s1.img --serial <序列号>`
Expected: `Booting OKAY`，之后 45 秒 bootloader 没有再响应。

通过线：`hw.memsize` 不低于 7784628224，或活动监视器的物理内存不低于 7.25 GB；三次上机（一次计时满 30 分钟，另两次各 10 分钟以上）按设计的通过标准判。第一次上机时试 `sudo dmesg | grep -E "kmem_|compressor|zones|memory outside"`。

停在加载器之后、没有内核的字：先请用户拍屏幕顶部的颜色条，按设计"失败时怎么办"的表处理。要跑对照时用 `boot-v4-payload.bigwin-ctl6.img`。

- [ ] **Step 3: 第 1b 步，`boot-v4-payload.bigwin-s1b.img`，一次，5 分钟**

通过线：能进桌面，`hw.memsize` 和第 1 步的读数相差不到 16 MiB。不过：按设计"新固件（1b）起不来或读数不同"处理（退到 8 GiB 窗口，用 `payload.bigwin-8g.img` 和现成固件打一份镜像）。

- [ ] **Step 4: 第 2 步，`boot-v4-payload.bigwin-s2.img`，三次**

通过线：`hw.memsize` 不低于 9395240960，或物理内存不低于 8.75 GB。出事而第 1 步通过：用 `payload.bigwin-split.img` 和新固件打一份镜像，按设计"第 2 步出事而第 1 步通过"分开两个变量。

- [ ] **Step 5: 第 3 步，`boot-v4-payload.bigwin-s3.img`，三次**

通过线：`hw.memsize` 不低于第 2 步的读数加 409600000，或物理内存不低于第 2 步的读数加 0.38 GB。出事而第 2 步通过：交付物退到第 2 步。

- [ ] **Step 6: 通过后**

用 `python3 -I local-tools/make-flash-bootimg.py <通过的那份 v4 镜像> out/flash/boot-v4-flash.bigwin.img` 做一份放得进 `boot_a` 的版本（不超过 201326592 字节），从内存启动一次，照同样的做法确认。然后把结果和读数交给用户，问是否写 `boot_a`。写 `boot_a` 要用户明确同意后另做。

- [ ] **Step 7: 记录**

每次上机的时间、镜像、读数、现象写进 `HANDOFF.md` 第 9 节；更新设计文档的状态行；提交。同一个问题试三次还不行，就停下来和用户商量。
