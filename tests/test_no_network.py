"""Importing the old live scripts must never reach the network."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
BLOCKER = """
import importlib, json, socket, sys
attempts = []
def refuse(*args, **kwargs):
    attempts.append(str(args[-1])[:60])
    raise OSError("network blocked")
socket.socket.connect = socket.socket.connect_ex = socket.getaddrinfo = refuse
sys.path.insert(0, ".")
importlib.import_module(sys.argv[1])
print("ATTEMPTS" + json.dumps(attempts))
"""


class ImportsStayOffline(unittest.TestCase):
    def test_live_script_import_makes_no_connection(self):
        result = subprocess.run(
            [sys.executable, "-c", BLOCKER, "test_nvidia"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-400:])
        line = next(l for l in result.stdout.splitlines() if l.startswith("ATTEMPTS"))
        self.assertEqual(json.loads(line[len("ATTEMPTS"):]), [])


if __name__ == "__main__":
    unittest.main()
