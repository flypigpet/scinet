"""Numerical and bounded author-generator checks for the paper review."""

import importlib
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from scinet.workspace import init_workspace


_FIXTURE = tempfile.TemporaryDirectory()
ROOT = init_workspace(_FIXTURE.name)
AUTHOR_REPO = ROOT / "vendor" / "same-stats"
DOZEN = AUTHOR_REPO / "samestats" / "datasets" / "generated" / "DatasaurusDozen.tsv"

def tearDownModule():
    _FIXTURE.cleanup()


class ComputeTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("scinet.compute")
        except ImportError as error:
            self.fail(f"Statistics feature is not implemented: {error}")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data.tsv"

    def run_data(self, content):
        self.path.write_text(content, encoding="utf-8")
        return self.module.compute(self.path)

    def test_hand_calculated_sample_standard_deviations_and_correlation(self):
        result = self.run_data("dataset\tx\ty\na\t1\t2\na\t2\t4\na\t3\t6\n")
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["dataset_count"], 1)
        self.assertEqual(result["stats"], [{"dataset": "a", "n": 3,
            "mean_x": 2.0, "mean_y": 4.0, "sd_x": 1.0, "sd_y": 2.0, "r": 1.0}])
        self.assertTrue(result["crosscheck"]["passed"])
        self.assertLessEqual(result["crosscheck"]["max_abs_error"], 1e-10)
        json.dumps(result, allow_nan=False)

    def test_floor_truncation_and_rounding_are_distinct_for_negative_correlation(self):
        result = self.run_data("dataset\tx\ty\na\t-1\t1\na\t0\t3\na\t1\t0\n")
        precision = result["precision"]
        self.assertEqual(precision["floor_2dp"]["unique_values"]["r"], [-0.33])
        self.assertEqual(precision["truncate_2dp"]["unique_values"]["r"], [-0.32])
        self.assertEqual(precision["round_2dp"]["unique_values"]["r"], [-0.33])
        self.assertEqual(precision["floor_2dp"]["unique_values"]["sd_y"], [1.52])
        self.assertEqual(precision["round_2dp"]["unique_values"]["sd_y"], [1.53])

    def test_different_groups_do_not_pass_precision_equality(self):
        result = self.run_data("dataset\tx\ty\na\t1\t2\na\t2\t4\na\t3\t6\nb\t2\t2\nb\t3\t4\nb\t4\t6\n")
        for mode in ("floor_2dp", "truncate_2dp", "round_2dp"):
            self.assertFalse(result["precision"][mode]["passed"])
        self.assertEqual(result["ranges"]["mean_x"], {"min": 2.0, "max": 3.0, "span": 1.0})

    def test_constant_coordinate_is_rejected(self):
        for rows in ("a\t1\t2\na\t1\t3", "a\t1\t2\na\t3\t2"):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "constant"):
                self.run_data("dataset\tx\ty\n" + rows + "\n")

    def test_nonfinite_coordinates_are_rejected(self):
        for value in ("NaN", "nan", "inf", "-Infinity"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "finite"):
                self.run_data(f"dataset\tx\ty\na\t1\t2\na\t3\t{value}\n")

    def test_missing_or_invalid_data_are_rejected(self):
        examples = ["", "dataset\tx\ty\n", "dataset\tx\na\t1\n",
                    "dataset\tx\ty\na\t1\t\n", "dataset\tx\ty\na\t1\n",
                    "dataset\tx\ty\na\t1\t2\n", "dataset\tx\ty\tother\na\t1\t2\t3\n",
                    "dataset\tx\ty\n\t1\t2\n", "dataset\tx\ty\na\ttext\t2\n"]
        for content in examples:
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.run_data(content)

    def test_author_dataset_has_expected_size_and_dino_statistics(self):
        result = self.module.compute(DOZEN)
        self.assertEqual((result["dataset_count"], result["rows"]), (13, 1846))
        self.assertEqual({row["n"] for row in result["stats"]}, {142})
        dino = next(row for row in result["stats"] if row["dataset"] == "dino")
        self.assertAlmostEqual(dino["sd_x"], 16.7651420391, places=9)
        self.assertAlmostEqual(dino["sd_y"], 26.9354034869, places=9)
        self.assertAlmostEqual(dino["r"], -0.0644718527, places=9)
        self.assertTrue(result["crosscheck"]["passed"])
        self.assertTrue(result["precision"]["floor_2dp"]["passed"])
        self.assertTrue(result["precision"]["truncate_2dp"]["passed"])
        self.assertFalse(result["precision"]["round_2dp"]["passed"])


class AuthorSmokeTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("scinet.compute")
        except ImportError as error:
            self.fail(f"Author smoke feature is not implemented: {error}")

    def test_missing_author_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                self.module.author_smoke(Path(temp) / "missing", temp)

    def test_lf_and_crlf_seed_line_endings_preserve_raw_input_and_same_result(self):
        original_seed = (AUTHOR_REPO / "samestats" / "datasets" / "seed" / "Datasaurus_data.csv").read_bytes()
        lf_seed = original_seed.replace(b"\r\n", b"\n")
        generated = []
        raw_hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for name, seed_bytes in (("lf", lf_seed), ("crlf", lf_seed.replace(b"\n", b"\r\n"))):
                with self.subTest(line_endings=name):
                    repo = Path(temp) / name / "repo"
                    source = repo / "samestats" / "samestats.py"
                    source.parent.mkdir(parents=True)
                    source.write_bytes((AUTHOR_REPO / "samestats" / "samestats.py").read_bytes())
                    seed = repo / "samestats" / "datasets" / "seed" / "Datasaurus_data.csv"
                    seed.parent.mkdir(parents=True)
                    seed.write_bytes(seed_bytes)
                    output = Path(temp) / name / "output"
                    try:
                        result = self.module.author_smoke(repo, output)
                    except ValueError as error:
                        self.fail(f"Valid {name.upper()} seed was rejected: {error}")
                    self.assertEqual(result["status"], "passed", result)
                    self.assertEqual((output / "seed-original.csv").read_bytes(), seed_bytes)
                    self.assertEqual(result["seed_data_sha256"], hashlib.sha256(seed_bytes).hexdigest())
                    self.assertEqual(result.get("seed_data_canonical_sha256"), hashlib.sha256(lf_seed).hexdigest())
                    self.assertEqual(result.get("seed_data_canonicalization"), "Replace CRLF with LF only; all other bytes unchanged")
                    generated.append((output / "generated.csv").read_bytes())
                    raw_hashes.append(result["seed_data_sha256"])
        self.assertEqual(len(generated), 2)
        self.assertEqual(generated[0], generated[1])
        self.assertNotEqual(raw_hashes[0], raw_hashes[1])

    def test_changed_author_seed_requires_review_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            source = repo / "samestats" / "samestats.py"
            source.parent.mkdir(parents=True)
            source.write_bytes((AUTHOR_REPO / "samestats" / "samestats.py").read_bytes())
            seed = repo / "samestats" / "datasets" / "seed" / "Datasaurus_data.csv"
            seed.parent.mkdir(parents=True)
            original_seed = (AUTHOR_REPO / "samestats" / "datasets" / "seed" / seed.name).read_bytes()
            lf_seed = original_seed.replace(b"\r\n", b"\n")
            for seed_bytes in (lf_seed, lf_seed.replace(b"\n", b"\r\n")):
                for changed in (seed_bytes.replace(b"55.3846", b"55.3847", 1),
                                seed_bytes.replace(b",", b", ", 1), seed_bytes + b"\n"):
                    with self.subTest(changed=changed[:25]):
                        seed.write_bytes(changed)
                        with self.assertRaisesRegex(ValueError, "seed.*reviewed|reviewed.*seed"):
                            self.module.author_smoke(repo, Path(temp) / "output")

    def test_real_generator_moves_points_and_preserves_author_floor_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.module.author_smoke(AUTHOR_REPO, temp)
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(result["seed"], 20261023)
            self.assertEqual(result["iterations_completed"], 1000)
            self.assertEqual(result["rows"], 142)
            self.assertTrue(result["author_constraint_passed"])
            self.assertTrue(result["author_get_values_crosscheck"]["passed"])
            self.assertGreater(result["moved_points"], 0)
            for name in ("adapter.py", "author-original.py", "seed-original.csv", "log.txt", "generated.csv"):
                self.assertTrue((Path(temp) / name).exists(), name)
            self.assertEqual(result["seed_data_sha256"],
                             hashlib.sha256((Path(temp) / "seed-original.csv").read_bytes()).hexdigest())
            self.assertFalse(result["full_figure_reproduction"])
            json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
