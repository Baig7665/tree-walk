"""Tests for tree_walk.core."""

import os
import tempfile
import unittest
from pathlib import Path

from tree_walk import Prune, WalkEntry, walk


class WalkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def make_file(self, relative: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return str(path)

    def test_empty_directory_yields_nothing(self) -> None:
        self.assertEqual(list(walk(self.root)), [])

    def test_yields_absolute_paths(self) -> None:
        file_path = self.make_file("a.txt")
        result = list(walk(self.root))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].path, os.path.abspath(file_path))
        self.assertEqual(result[0].depth, 0)

    def test_siblings_sorted_by_name(self) -> None:
        b = self.make_file("b.txt")
        a = self.make_file("a.txt")
        c = self.make_file("c.txt")
        result = list(walk(self.root))
        self.assertEqual(
            [entry.path for entry in result],
            [os.path.abspath(a), os.path.abspath(b), os.path.abspath(c)],
        )

    def test_depth_first_pre_order(self) -> None:
        self.make_file("root.txt")
        self.make_file("sub/nested.txt")
        self.make_file("sub/deep/file.txt")

        result = list(walk(self.root))
        names = [Path(entry.path).relative_to(self.root).as_posix() for entry in result]
        self.assertEqual(
            names,
            ["root.txt", "sub/deep/file.txt", "sub/nested.txt"],
        )

    def test_depth_values_follow_directory_nesting(self) -> None:
        self.make_file("top.txt")
        self.make_file("sub/inner.txt")
        result = list(walk(self.root))
        depths = {Path(entry.path).name: entry.depth for entry in result}
        self.assertEqual(depths["top.txt"], 0)
        self.assertEqual(depths["inner.txt"], 1)

    def test_on_enter_receives_directories_in_pre_order(self) -> None:
        self.make_file("sub/file.txt")
        self.make_file("sub/deep/other.txt")

        visited: list[str] = []

        def on_enter(directory) -> None:
            visited.append(directory.path)

        list(walk(self.root, on_enter=on_enter))

        self.assertEqual(len(visited), 3)
        self.assertTrue(all(os.path.isabs(path) for path in visited))
        self.assertEqual(Path(visited[0]).name, self.root.name)
        self.assertEqual(Path(visited[1]).name, "sub")
        self.assertEqual(Path(visited[2]).name, "deep")

    def test_prune_skips_directory_and_descendants(self) -> None:
        self.make_file("keep.txt")
        self.make_file("pruned/file.txt")
        self.make_file("pruned/deep/nested.txt")

        def on_enter(directory) -> None:
            if directory.path == os.path.abspath(str(self.root / "pruned")):
                raise Prune

        result = list(walk(self.root, on_enter=on_enter))
        names = [Path(entry.path).name for entry in result]
        self.assertEqual(names, ["keep.txt"])

    def test_prune_does_not_affect_sibling_directories(self) -> None:
        self.make_file("skip/file.txt")
        self.make_file("keep/file.txt")

        def on_enter(directory) -> None:
            if directory.path == os.path.abspath(str(self.root / "skip")):
                raise Prune

        result = list(walk(self.root, on_enter=on_enter))
        paths = [Path(entry.path).relative_to(self.root).as_posix() for entry in result]
        self.assertEqual(paths, ["keep/file.txt"])

    def test_prune_root_yields_nothing(self) -> None:
        self.make_file("a.txt")

        def on_enter(directory) -> None:
            if directory.path == os.path.abspath(self.root):
                raise Prune

        result = list(walk(self.root, on_enter=on_enter))
        self.assertEqual(result, [])

    def test_directories_themselves_are_not_yielded(self) -> None:
        self.make_file("sub/file.txt")
        result = list(walk(self.root))
        self.assertEqual(len(result), 1)
        self.assertEqual(Path(result[0].path).name, "file.txt")

    def test_symlinks_are_not_followed(self) -> None:
        self.make_file("real/file.txt")
        symlink_dir = self.root / "link"
        symlink_dir.symlink_to(self.root / "real", target_is_directory=True)

        result = list(walk(self.root))
        names = [Path(entry.path).relative_to(self.root).as_posix() for entry in result]
        # The symlink is treated as a file because is_dir(follow_symlinks=False)
        # returns False for symlinks.
        self.assertIn("link", names)
        self.assertNotIn("link/file.txt", names)

    def test_relative_root_produces_absolute_paths(self) -> None:
        self.make_file("file.txt")
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            result = list(walk("."))
            self.assertTrue(all(os.path.isabs(entry.path) for entry in result))
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
