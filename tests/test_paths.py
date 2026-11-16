"""Paths and project hashing."""

from __future__ import annotations

from pathlib import Path

from aiproof import paths


def test_project_hash_stable(tmp_path: Path) -> None:
    assert paths.project_hash(tmp_path) == paths.project_hash(tmp_path)
    assert len(paths.project_hash(tmp_path)) == 64


def test_project_dir_uses_short_hash(tmp_path: Path) -> None:
    directory = paths.project_dir(tmp_path)
    assert directory.name == paths.project_hash(tmp_path)[:16]


def test_canonical_is_absolute(tmp_path: Path) -> None:
    assert paths.canonical_path(tmp_path).is_absolute()


def test_git_toplevel_none_outside_repo(tmp_path: Path) -> None:
    assert paths.git_toplevel(tmp_path) is None


def test_project_root_is_cwd_outside_repo(tmp_path: Path) -> None:
    assert paths.project_root(tmp_path) == paths.canonical_path(tmp_path)
