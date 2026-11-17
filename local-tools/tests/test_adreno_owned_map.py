"""The GPU driver's owned-page map, built for the host from the driver's own tests (drivers/Adreno740/tests).

The driver's repository has no runner for its host tests. This one compiles NativeAdrenoMemory.cpp with the authored
doubles of XnuMemoryFixture.h the way ../UniXNU-sheng/scripts/check-native-adreno-memory.py does: every kernel header the
source includes is a one-line file that includes the fixture.

    python3 -I -B -m unittest discover -s local-tools/tests -p test_adreno_owned_map.py
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / 'drivers/Adreno740'
STUBS = ('IOKit/IOTypes.h', 'IOKit/IOReturn.h', 'IOKit/IOBufferMemoryDescriptor.h', 'IOKit/IOLib.h', 'kern/task.h')


def run_host_test(name):
    """Compile tests/<name>.cpp against the memory source and run it: the finished process."""
    with tempfile.TemporaryDirectory(prefix='adreno-host-') as temporary:
        work = Path(temporary)
        for stub in STUBS:
            path = work / 'include' / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#include "XnuMemoryFixture.h"\n')
        binary = work / name
        subprocess.run(['xcrun', 'clang++', '-std=c++23', '-O2', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                        '-I', work / 'include', '-I', KIT / 'tests', '-I', KIT, KIT / 'NativeAdrenoMemory.cpp',
                        KIT / 'tests/HostKernelHooks.cpp', KIT / f'tests/{name}.cpp', '-o', binary], check=True, timeout=180)
        return subprocess.run([binary], capture_output=True, text=True, timeout=60)


class OwnedMap(unittest.TestCase):
    def test_adopted_memory_above_4_gib_has_a_bit_a_page(self):
        result = run_host_test('test_owned_below_window')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: owned-page map with the kernel's range above 4 GiB", result.stdout)

    def test_the_drivers_own_map_test_still_passes(self):
        result = run_host_test('test_system_memory')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS: system BOs', result.stdout)


if __name__ == '__main__':
    unittest.main()
