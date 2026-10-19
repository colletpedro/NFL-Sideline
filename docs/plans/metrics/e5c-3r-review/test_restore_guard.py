"""Restore preflight must refuse before reading/copying or modifying a backup."""
import importlib.util
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'e5c-3r'))
spec = importlib.util.spec_from_file_location('review_restore', HERE.parent / 'e5c-3r/restore.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


@pytest.mark.parametrize('which', ['destination', 'config', 'report'])
def test_outputs_inside_backup_refused_before_read_or_copy(tmp_path, which):
    backup = tmp_path / 'backup'
    backup.mkdir()
    marker = backup / 'untouched.txt'
    marker.write_bytes(b'preserved')
    paths = {'destination': tmp_path / 'new-copy', 'config': tmp_path / 'operator/config.json',
             'report': tmp_path / 'operator/report.json'}
    paths[which] = backup / ('new-copy' if which == 'destination' else which + '.json')
    with patch.object(restore, 'hashes', side_effect=AssertionError('must reject before reading')) as reader, \
            patch.object(restore.shutil, 'copytree', side_effect=AssertionError('must not copy')) as copier:
        with pytest.raises(ValueError, match='disjoint from backup'):
            restore.restore(backup, **paths)
        reader.assert_not_called()
        copier.assert_not_called()
    assert list(backup.iterdir()) == [marker]
    assert marker.read_bytes() == b'preserved'
    assert not (tmp_path / 'operator').exists()


@pytest.mark.parametrize('which', ['backup', 'destination', 'config', 'report'])
def test_symlink_aliases_refused_before_read(tmp_path, which):
    backup = tmp_path / 'backup'
    backup.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(backup, target_is_directory=True)
    args = {'backup': backup, 'destination': tmp_path / 'new-copy',
            'config': tmp_path / 'config.json', 'report': tmp_path / 'report.json'}
    args[which] = alias if which == 'backup' else alias / ('new-copy' if which == 'destination' else which + '.json')
    with patch.object(restore, 'hashes', side_effect=AssertionError('must reject before reading')) as reader:
        with pytest.raises(ValueError, match='Unsafe path'):
            restore.restore(**args)
        reader.assert_not_called()
    assert not list(backup.iterdir())


def test_dotdot_destination_refused(tmp_path):
    backup = tmp_path / 'backup'
    backup.mkdir()
    with patch.object(restore, 'hashes', side_effect=AssertionError('must reject before reading')):
        with pytest.raises(ValueError, match='Unsafe path'):
            restore.restore(backup, backup / '..' / 'copy', tmp_path / 'config', tmp_path / 'report')


def test_valid_disjoint_paths_reach_reader_without_writing(tmp_path):
    backup = tmp_path / 'backup'
    backup.mkdir()
    with patch.object(restore, 'hashes', side_effect=RuntimeError('accepted preflight')) as reader:
        with pytest.raises(RuntimeError, match='accepted preflight'):
            restore.restore(backup, tmp_path / 'new-copy', tmp_path / 'config', tmp_path / 'report')
        reader.assert_called_once_with(backup)
