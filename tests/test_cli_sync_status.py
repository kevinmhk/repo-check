"""Sync status tests for repo-check CLI logic."""

from __future__ import annotations

from typing import List, Tuple

from repo_check import cli


GitCall = Tuple[str, ...]
GitResult = Tuple[int, str, str]


def _sequential_run_git(script: List[Tuple[GitCall, GitResult]]):
    calls: List[GitCall] = []

    def _fake_run_git(path: str, args: List[str]) -> GitResult:
        assert path == "/tmp/repo"
        call = tuple(args)
        calls.append(call)
        idx = len(calls) - 1
        assert idx < len(script), f"Unexpected git call: {call}"
        expected_call, response = script[idx]
        assert call == expected_call
        return response

    return _fake_run_git


def test_check_repo_fetches_upstream_and_maps_ahead_behind(monkeypatch):
    script = [
        (("rev-parse", "--is-inside-work-tree"), (0, "true", "")),
        (("rev-parse", "--abbrev-ref", "HEAD"), (0, "main", "")),
        (("status", "--porcelain"), (0, "", "")),
        (("remote", "get-url", "origin"), (0, "git@example.com:org/repo.git", "")),
        (
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
            (0, "origin/main", ""),
        ),
        (("fetch", "--quiet", "--prune", "--no-tags", "origin"), (0, "", "")),
        (("rev-list", "--left-right", "--count", "HEAD...@{u}"), (0, "3 1", "")),
    ]
    monkeypatch.setattr(cli, "_run_git", _sequential_run_git(script))

    result = cli._check_repo("/tmp/repo", "repo")

    assert result.error is None
    assert result.upstream_ref == "origin/main"
    assert result.ahead_count == 3
    assert result.behind_count == 1


def test_check_repo_continues_when_fetch_fails(monkeypatch):
    script = [
        (("rev-parse", "--is-inside-work-tree"), (0, "true", "")),
        (("rev-parse", "--abbrev-ref", "HEAD"), (0, "main", "")),
        (("status", "--porcelain"), (0, "", "")),
        (("remote", "get-url", "origin"), (0, "git@example.com:org/repo.git", "")),
        (
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
            (0, "origin/main", ""),
        ),
        (("fetch", "--quiet", "--prune", "--no-tags", "origin"), (128, "", "offline")),
        (("rev-list", "--left-right", "--count", "HEAD...@{u}"), (0, "0 2", "")),
    ]
    monkeypatch.setattr(cli, "_run_git", _sequential_run_git(script))

    result = cli._check_repo("/tmp/repo", "repo")

    assert result.error is None
    assert result.ahead_count == 0
    assert result.behind_count == 2


def test_upstream_remote_name():
    assert cli._upstream_remote_name("origin/main") == "origin"
    assert cli._upstream_remote_name("upstream/feature/foo") == "upstream"
    assert cli._upstream_remote_name("main") is None
