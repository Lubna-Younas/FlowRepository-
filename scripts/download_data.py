"""Download the pinned public fixture catalog with provenance and byte validation.

Raw data are deliberately excluded from the software distribution. Repository
software licenses do not automatically settle all third-party data reuse rights.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(entry, destination):
    """Verify size and Git blob digest before publishing a complete download."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and verify(entry, destination):
        return 'cached'
    partial = destination.with_suffix(destination.suffix + '.part')
    for attempt in range(3):
        try:
            req = urllib.request.Request(entry['url'], headers={'User-Agent': 'FlowWorkbench/0.1'})
            with urllib.request.urlopen(req, timeout=45) as response, partial.open('wb') as out:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > entry['bytes']:
                        raise ValueError('Download exceeded catalog size')
                    out.write(chunk)
            if not verify(entry, partial):
                raise ValueError('Size or Git blob checksum mismatch')
            if entry['path'].lower().endswith('.fcs'):
                with partial.open('rb') as f:
                    if not f.read(6).startswith(b'FCS'):
                        raise ValueError('Expected FCS header; server may have returned HTML')
            partial.replace(destination)
            return 'downloaded'
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def verify(entry, path):
    if path.stat().st_size != entry['bytes']:
        return False
    h = hashlib.sha1(f"blob {entry['bytes']}\0".encode())
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest() == entry['git_blob_sha1']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', type=Path, default=ROOT / 'data/catalog/public_fixtures.json')
    p.add_argument('--output', type=Path, default=ROOT / 'data/raw')
    p.add_argument('--max-mb', type=float, default=150)
    args = p.parse_args()
    catalog = json.loads(args.catalog.read_text())
    entries = catalog['files']
    if sum(e['bytes'] for e in entries) > args.max_mb * 1024**2:
        raise SystemExit('Catalog exceeds download budget; increase --max-mb explicitly.')
    receipts = []
    for entry in entries:
        dest = args.output / entry['collection'] / entry['path']
        if not dest.resolve().is_relative_to(args.output.resolve()):
            raise SystemExit('Unsafe catalog path')
        record = {**entry, 'local_path': str(dest.resolve()), 'retrieved_utc': datetime.now(timezone.utc).isoformat()}
        try:
            record['status'] = fetch(entry, dest)
            record['sha256'] = sha256(dest)
        except Exception as exc:
            record.update(status='failed', error=str(exc))
        receipts.append(record)
        print(record['status'], entry['collection'], entry['path'], flush=True)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'download_manifest.json').write_text(json.dumps(receipts, indent=2))
    failed = sum(r['status'] == 'failed' for r in receipts)
    print(f'{len(receipts) - failed}/{len(receipts)} files verified; manifest: {args.output / "download_manifest.json"}')
    raise SystemExit(bool(failed))


if __name__ == '__main__':
    main()
