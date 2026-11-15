# 用社区的 v0 外壳启动我们的系统（第一阶段）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把我们现有的内核和载荷装进社区的 v0 模板外壳（只换模板里的 DarwinBoot），从内存启动，先 6 GiB、再 7.5 GiB。

**Architecture:** 合并 CrossDarwin 核心仓库的 `boot/sheng-firmware-compat`，拿到它的 `scripts/unixnu/boot_template.py`。写一个本地工具：调用这个模块的 `parse_boot_image`、`loader_pe`、`replace_loader`，再按社区 `bootimg.py` 的做法打包：gzip(shim + 固件) 加上模板的设备树，载荷做 ramdisk，头部参数照抄模板。设备仓库的合并和全部重编是第二阶段，另写计划。

**Tech Stack:** Python 3 标准库（`python3 -I -B`），`../uefi-sheng/Resources/Scripts/mkbootimg.py`，fastboot。

**Spec:** `docs/superpowers/specs/2026-11-15-community-branch-test-design.md`（用户 18:39 说"帮我开始执行"批准；先做其中"先做的 v0 试验"一节的第 1 步）

## Global Constraints

- 只从内存启动（`python3 -I local-tools/boot-sheng.py <镜像>`），不刷 `boot_a`；每次启动要用户在场说可以。
- 每次进 fastboot 读两个槽位和电压；a 在 4 或以下就 `fastboot set_active a`。槽位 b 永远不设成活动的。
- 新镜像名一律 `out/flash/boot-v0-cd.<载荷名>.img`。不覆盖已有文件，尤其是 `boot-v4-flash*.img` 和不带 `bigwin` 的 `boot-v4-payload*.img`。
- 任何镜像都不带 `data-reset`。
- 芯片号（`unixnu.local.toml` 的 `unique_chip_id`）不写进任何文件；三个 `verification.json` 不提交；不推送。
- 模板：`out/downloads/cd-template-218fdcce/sheng-recovery-218FDCCE-boot.img.xz`，sha256 `8fed0304acdfac65421f8523d6be727311ee5f6f8826ac20736735de0e533124`，加载器 GUID `1b64af87-8415-4b57-9b16-680d70913b9f`（社区 `board.toml` 的值）。
- 换进去的 DarwinBoot 取自 `out/flash/SILICIUM_UEFI.bigwin-8407c84f.fd`（1b 用过，能进桌面）。
- 载荷：`<output>/payload/payload.bigwin-ctl6.img`（6 GiB 对照，sha256 `f1338e96…`）和 `<output>/payload/payload.bigwin-s1.img`（7.5 GiB，`ccd883c6…`）。`<output>` = `/Volumes/UniXNUBuild/unixnu-out/sheng/macos-27.3-26C5035r/sheng_macos`。

## Review Focus

- 我们的固件卷和模板的固件卷大小不同：社区的 `prepare` 会拒绝，本工具也必须拒绝，并说明两边的大小。
- 模板文件被换过或损坏（sha256 不符）：拒绝，不解压。
- 载荷的菜单参数行带 `data-reset`：拒绝。一次误启动就会清空用户数据。
- 输出路径已存在，或名字里没有 `boot-v0-cd.`：拒绝，避免覆盖日常文件。
- 固件里找不到这个加载器 GUID：拒绝（`loader_pe` 会报错，工具要把错误原样带出来、非零退出）。

---

### Task 1: 合并核心仓库的社区分支

**Files:**
- 合并提交（不手改文件）

**Interfaces:**
- Produces: `scripts/unixnu/boot_template.py`（`parse_boot_image(data) -> (shim, firmware, tree, image)`，`loader_pe(firmware, identifier) -> bytes`，`replace_loader(firmware, pe, identifier) -> (firmware, report)`），`scripts/unixnu/util.py` 里的 `Error`。

- [ ] **Step 1: 合并前核对**

Run: `git status --short`；`git merge-tree --write-tree --name-only HEAD crossdarwin/boot/sheng-firmware-compat`
Expected: 工作区只有 `?? data/` 和子模块的 `?` 标记；merge-tree 只输出一行树哈希（没有冲突）。

- [ ] **Step 2: 合并**

Run: `git merge --no-ff --no-edit crossdarwin/boot/sheng-firmware-compat -m "merge: CrossDarwin boot/sheng-firmware-compat (qualified sheng transport, signed-text revalidation)"`，消息末尾加 Co-Authored-By 行。
Expected: 合并成功，没有冲突；`git log -1` 是合并提交。

- [ ] **Step 3: 跑社区带来的测试**

Run: `python3 -B -m unittest discover -s scripts -p 'test_boot_template.py'`
Expected: 全部 OK。

### Task 2: 本地打包工具 `local-tools/make-bootimg-v0-template.py`

**Files:**
- Create: `local-tools/make-bootimg-v0-template.py`
- Test: `local-tools/test_make_bootimg_v0_template.py`

**Interfaces:**
- Consumes: Task 1 的 `boot_template` 模块（用 `sys.path` 加上仓库的 `scripts/` 后 `from unixnu import boot_template`）。
- Produces: 命令行 `python3 -I -B local-tools/make-bootimg-v0-template.py TEMPLATE_XZ FD PAYLOAD MKBOOTIMG OUT --sha256 PIN --loader-guid GUID`。成功时最后一行是 `<OUT>: v0, kernel K, ramdisk R, N bytes, sha256 H, loader sha256 L`，退出码 0；任何拒绝都写到 stderr、退出码 1、不留下输出文件。

- [ ] **Step 1: 写失败的测试**

`local-tools/test_make_bootimg_v0_template.py`，用 `subprocess` 跑工具：

| 测试 | 断言 |
| --- | --- |
| `test_refuses_existing_output` | 输出路径已存在 → 退出码 1，stderr 含 `exists`，文件内容不变 |
| `test_refuses_output_without_v0_cd_name` | 输出名 `boot-v4-flash.test.img` → 退出码 1，stderr 含 `boot-v0-cd.` |
| `test_refuses_wrong_template_checksum` | 随便写一个 `.img.xz`，`--sha256` 用真值 → 退出码 1，stderr 含 `checksum` |
| `test_refuses_data_reset_payload` | 载荷字节里有一行 `args = "data-reset=1 debug=0x14e"` → 退出码 1，stderr 含 `data-reset` |
| `test_end_to_end_with_cached_inputs` | 模板、固件、ctl6 载荷都在时才跑，否则 `skipTest`：输出到临时目录。断言头版本 0；ramdisk 字节等于载荷；kernel gzip 解开后等于 shim 加替换后的固件，剩余字节等于模板的设备树；固件里的加载器等于 `loader_pe(fd)`，不等于模板原来的；`os_version` 编码等于模板 |

- [ ] **Step 2: 运行，确认失败**

Run: `python3 -I -B -m unittest local-tools/test_make_bootimg_v0_template.py`（不行就用 `discover -s local-tools -p 'test_make_bootimg_v0_template.py'`）
Expected: FAIL（工具不存在）。

- [ ] **Step 3: 实现工具**

顺序：
1. 先检查输出名和是否已存在。
2. 再检查模板 sha256，然后解压 xz（`max_length=256<<20`）。
3. 扫描载荷：参数行 `args = "…"` 里含 `data-reset=` 就拒绝。
4. 调用 `parse_boot_image`；固件卷大小和 FD 不同就拒绝，报出两个大小。
5. 依次调用 `loader_pe`、`replace_loader`。
6. kernel = `gzip.compress(shim + firmware, mtime=0) + tree`。
7. mkbootimg 参数照抄模板：`header_version`、`base`、`kernel_offset`、`ramdisk_offset`、`tags_offset`、`pagesize`、`os_version`、`os_patch_level`。键名和社区 `bootimg.py` 的 `MKBOOTIMG_FLAGS` 一致。
8. 先写到同目录的临时文件，按测试表里的同一套条件回读核对，通过后才改名成 OUT；失败就删掉临时文件。

- [ ] **Step 4: 运行，确认通过**

Run: 同 Step 2
Expected: 5 个测试 OK（end-to-end 在输入齐全时也是 OK，不是 skip）。

- [ ] **Step 5: 提交**

```bash
git add local-tools/make-bootimg-v0-template.py local-tools/test_make_bootimg_v0_template.py
git commit -m "feat(local-tools): wrap a payload and our DarwinBoot in the community v0 template"
```

### Task 3: 打两份 v0 镜像

**Files:**
- 输出：`out/flash/boot-v0-cd.bigwin-ctl6.img`、`out/flash/boot-v0-cd.bigwin-s1.img`（不入库）
- Modify: `HANDOFF.md`

- [ ] **Step 1: 记下日常镜像的哈希**

在同一个 shell 命令里，先算 `out/flash/` 下 22 份日常镜像的 sha256，然后打包，最后再算一次、比较。

- [ ] **Step 2: 打包**

对 ctl6 和 s1 各运行一次 Task 2 的工具（参数见 Global Constraints）。
Expected：
- 每份的最后一行都是 `…: v0, kernel K, ramdisk R, …`，两份的 `K` 相同；
- 载荷的 sha256 和 Global Constraints 里的一致；
- 日常镜像的哈希前后相同。

- [ ] **Step 3: 记录并提交**

把两份镜像的 sha256、K、R 记进 `HANDOFF.md`；提交前用计数脚本查芯片号（0 处）。

### Task 4: 上机（每次都要用户说可以）

- [ ] **Step 1: 6 GiB（`boot-v0-cd.bigwin-ctl6.img`）**

进 fastboot → 读槽位和电压 → 核对 sha256 → `boot-sheng.py`。
通过：
- 出现我们自己的 UniXNU 菜单（3 秒倒计时），进到登录窗口和桌面；
- 活动监视器物理内存约 6.0 GB。

不通过：拍屏幕。停在彩条看颜色；panic 拍全文。

- [ ] **Step 2: 7.5 GiB（`boot-v0-cd.bigwin-s1.img`）**

同上。通过：物理内存约 7.50 GB。
6 GiB 过了、7.5 GiB 不过：模板里社区的板级固件放不下 7.5 GiB 窗口，记下来，第二阶段再看是否换成本机的固件。

- [ ] **Step 3: 记录**

每次的结果、读数、照片文件名记进 `HANDOFF.md` 并提交。
