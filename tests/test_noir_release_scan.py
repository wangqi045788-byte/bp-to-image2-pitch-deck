from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from public_release_check import scan_tree, REVIEWED_BINARY_SHA256


class NoirReleaseTests(unittest.TestCase):
    def test_only_exact_reviewed_font_bytes_are_allowed(self):
        relative = next(iter(REVIEWED_BINARY_SHA256))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            font = root / relative
            font.parent.mkdir(parents=True)
            font.write_bytes((ROOT / relative).read_bytes())
            self.assertEqual(scan_tree(root, []), [])
            font.write_bytes(b'unreviewed replacement')
            self.assertTrue(any(f['kind'] == 'reviewed binary changed' for f in scan_tree(root, [])))

    def test_other_binary_fonts_remain_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'unknown.ttf').write_bytes(b'unknown')
            self.assertTrue(any(f['kind'] == 'unreviewed file type' for f in scan_tree(root, [])))
