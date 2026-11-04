from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ppt_package', ROOT / 'tools/build_ppt_package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)

class PackageTests(unittest.TestCase):
    def test_complete_package_has_all_skills_verified_bytes_and_no_job_data(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'suite.zip'
            result = package.build(ROOT, output)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read('ppt-studio/PACKAGE_MANIFEST.json'))
                for name in ('ppt-studio','ppt-analysis','ppt-research','ppt-storyline','ppt-design','ppt-production','ppt-quality','noir-ppt-studio'):
                    self.assertIn(f'ppt-studio/skills/{name}/SKILL.md', archive.namelist())
                for record in manifest['files']:
                    self.assertEqual(hashlib.sha256(archive.read('ppt-studio/' + record['path'])).hexdigest(),record['sha256'])
                self.assertFalse(any('/.git/' in n or '/__pycache__/' in n or n.endswith('.pptx') for n in archive.namelist()))
            self.assertEqual(result['release_scan'],'passed')
            with self.assertRaises(FileExistsError):
                package.build(ROOT, output)

    def test_package_cannot_write_into_repository(self):
        with self.assertRaises(ValueError):
            package.build(ROOT, ROOT / 'unsafe.zip')
