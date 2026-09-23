"""Tree Walk: deterministic directory walking with prune rules.

This package exposes the public API for walking directory trees in a
stable, predictable order while allowing callers to prune subtrees during
the walk itself.
"""

from .core import DirectoryEntry, Prune, WalkEntry, walk

__all__ = ["DirectoryEntry", "Prune", "WalkEntry", "walk"]
