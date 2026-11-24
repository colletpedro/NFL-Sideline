"""Local CAS with exclusive publication and first-observation receipts.

Files may outlive a rolled-back SQL transaction. Never remove published blobs.
Hashes establish integrity, not authenticity, completeness or historical timing.
"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile
import uuid

from ..offline_metrics.artifact import identity, json_bytes
from ..offline_metrics.inputs import load_json


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_root(path):
    root = Path(path).resolve()
    parts = root.parts
    if any(parts[i:i + 3] == ('web-ui', 'public', 'data') for i in range(len(parts) - 2)):
        raise ValueError('Archive under public/data is forbidden')
    return root


def publish(path, data):
    """Fsync then hard-link without replacement; competing writers reuse bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        os.unlink(temporary)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Archive destination is not a regular file')
    return path.read_bytes()


class Archive:
    def __init__(self, root):
        self.root = safe_root(root)
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.path('ARCHIVE.json')
        candidate = json_bytes({'archiveVersion': 1, 'archive_id': str(uuid.uuid4())})
        document = load_json(publish(marker, candidate))
        if set(document) != {'archiveVersion', 'archive_id'} or document['archiveVersion'] != 1:
            raise ValueError('Invalid archive marker')
        self.archive_id = str(uuid.UUID(document['archive_id']))

    def path(self, relative):
        path = self.root / relative
        current = path
        while current != self.root:
            if current.is_symlink():
                raise ValueError('Archive symlink component forbidden')
            current = current.parent
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Archive locator escapes root')
        return path

    @staticmethod
    def locator(sha256):
        if len(sha256) != 64 or any(c not in '0123456789abcdef' for c in sha256):
            raise ValueError('Invalid byte hash')
        return f'blobs/sha256/{sha256[:2]}/{sha256}'

    def read(self, sha256):
        path = self.path(self.locator(sha256))
        if path.is_symlink() or not path.is_file():
            raise ValueError('Archive blob missing or not regular')
        data = path.read_bytes()
        if digest(data) != sha256:
            raise ValueError('Archive blob hash mismatch')
        return data

    def put(self, data, sha256, origin):
        if digest(data) != sha256:
            raise ValueError('Provided bytes hash mismatch')
        path = self.path(self.locator(sha256))
        if digest(publish(path, data)) != sha256:
            raise ValueError('Existing archive blob conflicts with hash')
        self.read(sha256)
        # The instant refers to a verified local observation, not event closure.
        observation = {'receiptVersion': 1, 'archive_id': self.archive_id,
                       'archive_root': str(self.root), 'sha256': sha256,
                       'locator': self.locator(sha256),
                       'observed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                       'origin': origin}
        receipt = {'receipt_id': identity(observation), **observation}
        receipt_path = self.path(f'receipts/{sha256}.json')
        saved = load_json(publish(receipt_path, json_bytes(receipt)))
        self.validate_receipt(saved, sha256)
        return saved

    def validate_receipt(self, receipt, sha256):
        content = {k: v for k, v in receipt.items() if k != 'receipt_id'}
        if (identity(content) != receipt.get('receipt_id') or
                content.get('receiptVersion') != 1 or
                content.get('archive_id') != self.archive_id or
                content.get('archive_root') != str(self.root) or
                content.get('sha256') != sha256 or
                content.get('locator') != self.locator(sha256)):
            raise ValueError('Archive receipt integrity mismatch')
        instant = datetime.fromisoformat(content['observed_at'].replace('Z', '+00:00'))
        if instant.tzinfo is None or instant.utcoffset().total_seconds() != 0:
            raise ValueError('Receipt requires UTC observation')
        self.read(sha256)
