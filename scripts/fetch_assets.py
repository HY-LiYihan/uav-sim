#!/usr/bin/env python3
"""Download explicitly recorded assets and verify their SHA256 before publishing."""
import hashlib
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[1]


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    entries = yaml.safe_load((ROOT / 'assets/manifest.yaml').read_text())['resources']
    if not entries:
        print('No additional assets configured. Official PX4 models are managed by Git submodules.')
        return
    cache = ROOT / 'assets/cache'
    cache.mkdir(exist_ok=True)
    for entry in entries:
        name, expected = entry['filename'], entry['sha256'].lower()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name):
            raise ValueError(f'Invalid asset filename: {name}')
        if not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError(f'Invalid SHA256: {name}')
        if not entry['url'].startswith('https://') or not entry.get('license') or not entry.get('source'):
            raise ValueError(f'Asset requires HTTPS URL, source and license: {name}')
        destination = cache / name
        if destination.is_file() and checksum(destination) == expected:
            print(f'Verified cached asset: {name}')
            continue
        # Temporary download is private to this operation and removed automatically on failure.
        with tempfile.TemporaryDirectory(prefix='download-', dir=cache) as temporary:
            download = Path(temporary) / name
            with urllib.request.urlopen(entry['url'], timeout=60) as response, download.open('wb') as output:
                if not response.url.startswith('https://'):
                    raise ValueError('Asset redirected away from HTTPS')
                shutil.copyfileobj(response, output)
            if checksum(download) != expected:
                raise ValueError(f'SHA256 mismatch: {name}; cached asset was not replaced')
            assert destination.resolve().parent == cache.resolve()
            download.replace(destination)
        print(f'Downloaded and verified: {name}')


if __name__ == '__main__':
    main()
