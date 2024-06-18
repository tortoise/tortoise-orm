import subprocess
import shlex
import sys


from tortoise.contrib import test


class TestDecorator(test.TestCase):
    @test.requireCapability(dialect="sqlite")
    async def test_init_memory_sqlite(self):
        cmd = f"{sys.executable} examples/basic.py"
        r = subprocess.run(shlex.split(cmd), capture_output=True)
        output = r.stdout.decode()
        s = "[{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]"
        self.assertIn(s, output)
