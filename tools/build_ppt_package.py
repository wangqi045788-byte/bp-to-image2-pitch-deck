#!/usr/bin/env python3
"""Package the reviewed full PPT skill suite, without jobs or machine settings."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
ROOT_FILES = ('README.md', 'README.zh-CN.md', 'LICENSE', 'SECURITY.md',
              'CONTRIBUTING.md', 'SKILL.md', 'pyproject.toml', '.gitignore',
              'PPT_REQUEST.md', 'NOIR_REQUEST.md', 'NOIR_STUDIO.md',
              'requirements-ppt.txt', 'requirements-noir.txt',
              'start-ppt.cmd', 'install-ppt.cmd', 'start-noir.cmd', 'install-noir.cmd')
DIRS = ('skills', 'tools', 'scripts', 'references', 'agents', 'examples', 'tests', 'team-kit', '.github')
SKIP = {'__pycache__', '.pytest_cache', '.mypy_cache', '.venv', 'venv'}

def build(repo: Path, output: Path, overwrite: bool = False) -> dict:
    repo = repo.resolve(strict=True)
    output = output.expanduser().resolve()
    if output == repo or repo in output.parents:
        raise ValueError('Package output must be outside the source repository.')
    if output.exists() and not overwrite:
        raise FileExistsError('Package already exists; choose a new path or use --overwrite.')
    if output.suffix.lower() != '.zip':
        raise ValueError('Package output must be a .zip file.')
    check = subprocess.run([sys.executable, str(repo / 'scripts/public_release_check.py'),
                            str(repo), '--skip-history', '--json'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
    if check.returncode:
        raise ValueError('Release scan did not pass; review the scanner findings before packaging.\n' + check.stdout)
    paths = [repo / name for name in ROOT_FILES]
    for name in DIRS:
        for path in (repo / name).rglob('*'):
            if SKIP.intersection(path.relative_to(repo).parts) or path.suffix == '.pyc':
                continue
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Package cannot follow links: ' + path.relative_to(repo).as_posix())
            if path.is_file():
                paths.append(path)
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError('The package is missing a required root file.')
    data = {p.relative_to(repo).as_posix(): p.read_bytes() for p in sorted(set(paths))}
    manifest = {'package': 'PPT Studio Full Skills', 'schema_version': 1,
                'entrypoint': 'skills/ppt-studio/SKILL.md',
                'files': [{'path': name, 'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)}
                          for name, blob in data.items()]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ppt-release-', dir=output.parent) as temp:
        candidate = Path(temp) / 'package.zip'
        with zipfile.ZipFile(candidate, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, blob in data.items():
                archive.writestr('ppt-studio/' + name, blob)
            archive.writestr('ppt-studio/PACKAGE_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(candidate) as archive:
            if archive.testzip() is not None:
                raise ValueError('Package CRC verification failed.')
        candidate.replace(output)
    return {'file': str(output), 'files': len(data) + 1,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'release_scan': 'passed'}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(build(REPO, args.out, args.overwrite), ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
