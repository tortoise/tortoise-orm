import subprocess
import sys
import tempfile
from pathlib import Path


from tortoise.contrib import test


class TestRunner(test.TestCase):
    @test.requireCapability(dialect="sqlite")
    async def test_init_memory_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            p = Path(tmp_path) / "output.txt"
            cmd = f"{sys.executable} examples/basic.py > {p}"
            subprocess.run(cmd, shell=True)
            s = "[{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]"
            self.assertIn(s, p.read_text())
