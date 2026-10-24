"""The powerlaw runner rejects bad inputs before executing author code."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


DRIVER = Path(__file__).resolve().parents[1] / "examples" / "powerlaw" / "recompute.py"
REQUIRED = (
    "paper.txt", "author_powerlaw.py", "author_figures.py",
    "blackouts.txt", "words.txt", "worm.txt",
)


class PowerlawRunnerTests(unittest.TestCase):
    def load_driver(self):
        self.assertTrue(DRIVER.is_file(), "Portable runner has not been implemented")
        spec = importlib.util.spec_from_file_location("powerlaw_runner_under_test", DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def invoke(self, source, destination, cwd):
        return subprocess.run(
            [sys.executable, str(DRIVER), str(source), str(destination)],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )

    def test_missing_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            source.mkdir()
            destination = root / "new-results"
            result = self.invoke(source, destination, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing required input", result.stderr)
            self.assertFalse(destination.exists())

    def test_wrong_hash_does_not_execute_or_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            source.mkdir()
            for name in REQUIRED:
                (source / name).write_text("raise RuntimeError('must never execute')\n", encoding="utf-8")
            destination = root / "new-results"
            result = self.invoke(source, destination, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)
            self.assertNotIn("must never execute", result.stderr)
            self.assertFalse(destination.exists())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "old-evidence"
            destination.mkdir()
            sentinel = destination / "response.json"
            sentinel.write_bytes(b'{"historical":true}\n')
            result = self.invoke(root / "missing-input", destination, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Output directory already exists", result.stderr)
            self.assertEqual(sentinel.read_bytes(), b'{"historical":true}\n')
            self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_legacy_pointer_cannot_redirect_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "historical-run"
            old.mkdir()
            sentinel = old / "response.json"
            sentinel.write_bytes(b"untouched")
            (root / "output").mkdir()
            (root / "output" / "unguided-run.txt").write_text(str(old), encoding="utf-8")
            source = root / "new-input"
            source.mkdir()
            result = self.invoke(source, root / "new-results", root)
            self.assertIn("Missing required input", result.stderr)
            self.assertEqual(sentinel.read_bytes(), b"untouched")
            self.assertEqual(list(old.iterdir()), [sentinel])

    def test_compatibility_conversion_preserves_synthetic_calculation(self):
        driver = self.load_driver()
        original = "def demo(data):\n\tprint data\n\tgood_values = 1\n\tmask=-good_values\n\treturn map(lambda n: n * 2, xrange(3))\n"
        converted, changes = driver.adapt_source(original)
        namespace = {}
        exec(compile(converted, "synthetic_author.py", "exec"), namespace)
        from contextlib import redirect_stdout
        import io
        with redirect_stdout(io.StringIO()):
            self.assertEqual(namespace["demo"]([3]), [0, 2, 4])
        self.assertIn("mask=~good_values", converted)
        self.assertTrue(changes)
        self.assertIn("print data", original)

    def test_independent_fit_handles_synthetic_data(self):
        driver = self.load_driver()
        import math
        namespace = {"__name__": "synthetic_independent_test", "__file__": str(DRIVER)}
        exec(compile(driver.INDEPENDENT_SOURCE, "independent.py", "exec"), namespace)
        result = namespace["fit_at_xmin"]([1.0, 2.0, 4.0], 1.0, comparison=True)
        self.assertAlmostEqual(result["alpha"], 1.0 + 3.0 / math.log(8.0))
        self.assertEqual(result["n_tail"], 3)
        self.assertGreaterEqual(result["D"], 0)
        self.assertLessEqual(result["D"], 1)
        self.assertGreaterEqual(result["power_law_vs_exponential"]["p_two_sided"], 0)
        self.assertLessEqual(result["power_law_vs_exponential"]["p_two_sided"], 1)


if __name__ == "__main__":
    unittest.main()
