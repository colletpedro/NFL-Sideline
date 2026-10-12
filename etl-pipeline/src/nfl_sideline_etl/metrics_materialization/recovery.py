"""Read-only archive recovery. Never instantiates the mutating Archive constructor."""
import base64
from pathlib import Path
import uuid

from ..metrics_persistence.archive import Archive, safe_root
from ..offline_metrics.inputs import load_json


class ReadOnlyArchive(Archive):
    def __init__(self, root, archive_id):
        supplied = Path(root).absolute()
        for component in (supplied, *supplied.parents):
            if component.is_symlink():
                raise ValueError('Archive root symlink forbidden')
        self.root = safe_root(root)
        marker = load_json(self.path('ARCHIVE.json').read_bytes())
        if set(marker) != {'archiveVersion', 'archive_id'} or marker['archiveVersion'] != 1:
            raise ValueError('Invalid archive marker')
        self.archive_id = str(uuid.UUID(marker['archive_id']))
        if self.archive_id != archive_id:
            raise ValueError('Explicit archive identity mismatch')


def recover(package, roots):
    """Return a closed byte bundle; references/origins are data, never locations."""
    receipts = package['relations']['metric_archive_receipt']
    aids = {s['archive_id'] for s in package['selection']}
    if set(roots) != aids:
        raise ValueError('Supply exactly the explicitly selected archive roots')
    recovered = {}
    for aid in sorted(aids):
        archive = ReadOnlyArchive(roots[aid], aid)
        blobs, documents = {}, {}
        for row in receipts:
            if row['archive_id'] != aid:
                continue
            sha = row['sha256']
            receipt = load_json(archive.path(f'receipts/{sha}.json').read_bytes())
            archive.validate_receipt(receipt, sha)
            if receipt != row['receipt_json']:
                raise ValueError('Disk and persisted receipts diverge')
            if sha in documents:
                raise ValueError('Duplicate archive/blob observation')
            documents[sha] = receipt
            blobs[sha] = base64.b64encode(archive.read(sha)).decode('ascii')
        recovered[aid] = {'archive_id': aid, 'archive_root': str(archive.root),
                           'blobs': blobs, 'receipts': documents}
    return recovered
