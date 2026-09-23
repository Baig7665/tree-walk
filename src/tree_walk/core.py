"""Core implementation of deterministic tree walking.

The walk is deliberately simple: a depth-first pre-order traversal over
directory entries. Entries are sorted by name within each directory so
that two calls over the same tree produce the same sequence, regardless
of filesystem ordering.

A caller may raise :class:`Prune` from the ``on_enter`` callback to
skip a directory and all of its descendants. Pruning only affects the
directory for which the callback was invoked; the parent directory
continues with its remaining entries.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Iterator, Optional


class Prune(Exception):
    """Raise from ``on_enter`` to skip a directory and its descendants."""


@dataclass(frozen=True)
class DirectoryEntry:
    """A directory encountered during a walk.

    Attributes:
        path: The absolute path to the directory.
        depth: The number of directories above this one, with the starting
            directory at depth 0.
    """

    path: str
    depth: int


@dataclass(frozen=True)
class WalkEntry:
    """A non-directory entry encountered during a walk.

    Attributes:
        path: The absolute path to the entry.
        depth: The depth of the containing directory, as defined by
            :class:`DirectoryEntry`.
    """

    path: str
    depth: int


OnEnterCallback = Callable[[DirectoryEntry], None]


def walk(
    root: str,
    on_enter: Optional[OnEnterCallback] = None,
) -> Iterator[WalkEntry]:
    """Walk the tree rooted at ``root`` in deterministic pre-order.

    Directories are visited before their entries. Within a directory,
    entries are yielded in lexicographic order by name. The root directory
    itself is never yielded as a :class:`WalkEntry`; use ``on_enter`` to
    observe directories.

    Args:
        root: The path at which the walk starts. It may be relative or
            absolute, but all yielded paths are absolute.
        on_enter: Optional callback invoked for each directory immediately
            before its contents are enumerated. If the callback raises
            :class:`Prune`, that directory and all descendants are skipped.

    Yields:
        A :class:`WalkEntry` for every non-directory entry that is not
        pruned, in depth-first pre-order with siblings sorted by name.

    Raises:
        OSError: If ``root`` cannot be listed or is not a directory.
    """
    root_abs = os.path.abspath(root)
    yield from _walk_directory(root_abs, 0, on_enter)


def _walk_directory(
    directory: str,
    depth: int,
    on_enter: Optional[OnEnterCallback],
) -> Iterator[WalkEntry]:
    """Recursive implementation for one directory."""
    if on_enter is not None:
        try:
            on_enter(DirectoryEntry(directory, depth))
        except Prune:
            return

    with os.scandir(directory) as entries:
        # os.scandir does not guarantee ordering across filesystems or
        # even across calls, so sorting by name is required for a stable
        # output sequence.
        ordered = sorted(entries, key=lambda entry: entry.name)

    for entry in ordered:
        if entry.is_dir(follow_symlinks=False):
            # Directories are not yielded as WalkEntry; only their contents
            # are. Recursing here gives a pre-order traversal.
            yield from _walk_directory(entry.path, depth + 1, on_enter)
        else:
            yield WalkEntry(entry.path, depth)
