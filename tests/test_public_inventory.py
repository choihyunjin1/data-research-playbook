"""Publication inventory mechanics; these tests do not establish legal rights."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_public_inventory.py"
SPEC = importlib.util.spec_from_file_location("public_inventory", SCRIPT)
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


def record(path):
    return {
        "path": path,
        "purpose": "Synthetic test fixture",
        "rights": "MIT",
        "selection": "Explicitly selected synthetic path",
        "privacy_review": "Synthetic content reviewed",
    }


class InventoryTests(unittest.TestCase):
    def validate(self, entries, tracked=("a.py",)):
        return inventory.validate_inventory({"entries": entries}, tracked)

    def test_complete_inventory_includes_both_metadata_files(self):
        paths = ["a.py", inventory.INVENTORY, "PUBLIC_MANIFEST.json"]
        result = self.validate([record(path) for path in paths], paths)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tracked_files"], 3)

    def test_missing_tracked_entry(self):
        result = self.validate([])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["missing_tracked"], ["a.py"])

    def test_duplicate_entry(self):
        result = self.validate([record("a.py"), record("a.py")])
        self.assertIn("duplicate inventory entry", [error["reason"] for error in result["errors"]])

    def test_unknown_or_deleted_path_is_stale(self):
        result = self.validate([record("a.py"), record("old.py")])
        self.assertEqual(result["stale_entries"], ["old.py"])
        self.assertEqual(result["status"], "FAIL")

    def test_attestation_fields_cannot_be_missing_or_empty(self):
        for field in inventory.REVIEW_FIELDS:
            for value in [None, "", " \n", [], 5]:
                entry = record("a.py")
                entry[field] = value
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.validate([entry])["status"], "FAIL")
            entry = record("a.py")
            del entry[field]
            self.assertEqual(self.validate([entry])["status"], "FAIL")

    def test_known_unreviewed_placeholders_fail(self):
        for value in ["unknown", " TBD ", "pending", "미확인", "검토 필요"]:
            entry = record("a.py")
            entry["rights"] = value
            with self.subTest(value=value):
                self.assertEqual(self.validate([entry])["status"], "FAIL")

    def test_unsafe_paths_fail_without_normalization(self):
        for path in ["../secret", "a/../secret", "/absolute", "D:/data", "a\\b", "a//b", "./a", "a/", "a\n.py", " a.py", "a.py ", ""]:
            with self.subTest(path=path):
                self.assertFalse(inventory.safe_relative_path(path))
                self.assertEqual(self.validate([record(path)], [path])["status"], "FAIL")

    def test_spaces_and_unicode_in_relative_paths_are_valid(self):
        path = "docs/새 사례.md"
        self.assertEqual(self.validate([record(path)], [path])["status"], "PASS")

    def test_malformed_inventory_fails(self):
        for document in [None, [], {}, {"entries": {}}, {"entries": [None]}]:
            with self.subTest(document=document):
                self.assertEqual(inventory.validate_inventory(document, ["a.py"])["status"], "FAIL")

    def test_check_and_pending_modes_do_not_modify_inventory_or_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, capture_output=True)
            (root / "provenance").mkdir()
            target = root / inventory.INVENTORY
            target.write_text(json.dumps({"entries": [record(inventory.INVENTORY), record("a.py")]}), encoding="utf-8")
            (root / "a.py").write_text("# synthetic\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", inventory.INVENTORY, "a.py"], cwd=root, check=True, capture_output=True)
            (root / "pending.md").write_text("Unreviewed draft\n", encoding="utf-8")
            before = target.read_bytes()
            index_before = (root / ".git" / "index").read_bytes()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = inventory.main(["--list-pending", "--root", str(root)])
            result = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["untracked_candidates"], ["pending.md"])
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual((root / ".git" / "index").read_bytes(), index_before)

            (root / "a.py").unlink()
            self.assertEqual(inventory.check(root)["status"], "FAIL")
            target.write_text("{broken", encoding="utf-8")
            self.assertEqual(inventory.check(root)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
