import subprocess
import sys


from tortoise.contrib import test


class TestDecorator(test.TestCase):
    @test.requireCapability(dialect="sqlite")
    async def test_init_memory_sqlite(self):
        r = subprocess.run([sys.executable, "examples/basic.py"], capture_output=True)
        output = r.stdout.decode()
        s = "[{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]"
        self.assertIn(s, output)
