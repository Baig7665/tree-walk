# Tree Walk

Tree Walk provides deterministic, depth-first directory walking with the ability to prune subtrees during the walk.

```python
from tree_walk import Prune, walk

for entry in walk("."):
    print(entry.path)

def on_enter(directory):
    if directory.path.endswith("node_modules"):
        raise Prune

for entry in walk(".", on_enter=on_enter):
    print(entry.path)
```

The exported names are `walk`, `WalkEntry`, `DirectoryEntry`, and `Prune`.

## Why this exists

Filesystem APIs return entries in arbitrary order, and many tree walkers either follow symlinks or make it difficult to exclude large subtrees. This library makes a single trade-off: it sorts every directory's entries by name before visiting them, which guarantees a stable output order across runs and platforms. The cost is that sorting requires reading a full directory into memory before yielding any of its entries.

## Edge cases

Directories themselves are never yielded as `WalkEntry` objects; use the `on_enter` callback to observe them. Symbolic links are not followed, and a symlink to a directory is treated as a regular file. Raising `Prune` from `on_enter` skips that directory and all of its descendants without affecting its siblings.
