"""Independent statistics and a bounded, explicitly adapted author-code smoke run."""

from __future__ import annotations

import ast
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

import numpy as np
import pandas as pd


METRICS = ("mean_x", "mean_y", "sd_x", "sd_y", "r")
TOLERANCE = 1e-10
REVIEWED_AUTHOR_SHA256 = "dd2ae015b712f1c406ce8ada766b637840ed8cc930bb7d0f9eb47837ff71356c"
REVIEWED_SEED_CANONICAL_SHA256 = "6bb3ef074b5dcee8cabeffe57f79ad5adf298d7cad0b496ef3d425f4f6086097"
SMOKE_SEED = 20261023
SMOKE_ITERATIONS = 1000
SMOKE_TIMEOUT_SECONDS = 30


def _stdlib_values(xs: list[float], ys: list[float]) -> dict[str, float]:
    values = (statistics.mean(xs), statistics.mean(ys), statistics.stdev(xs),
              statistics.stdev(ys), statistics.correlation(xs, ys))
    return dict(zip(METRICS, map(float, values)))


def compute(data_path: str | Path) -> dict:
    """Read a long-form TSV and independently check five sample statistics.

    Accepts any number of named groups with at least two nonconstant points.
    The paper-specific 13 by 142 layout is checked by the pipeline/tests, while
    this function also accepts small hand-computable validation fixtures.
    """
    path = Path(data_path)
    groups: dict[str, tuple[list[float], list[float]]] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["dataset", "x", "y"]:
            raise ValueError("Expected exactly the TSV columns dataset, x, y")
        for line, row in enumerate(reader, start=2):
            name = row.get("dataset", "")
            if None in row or not name or not name.strip():
                raise ValueError(f"Incomplete or invalid data at line {line}")
            try:
                x, y = float(row["x"]), float(row["y"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Incomplete or nonnumeric coordinate at line {line}") from error
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"Coordinates must be finite at line {line}")
            xs, ys = groups.setdefault(name, ([], []))
            xs.append(x)
            ys.append(y)
    if not groups:
        raise ValueError("No observations found")
    stats = []
    for name, (xs, ys) in sorted(groups.items()):
        if len(xs) < 2:
            raise ValueError(f"Dataset {name!r} needs at least two observations")
        if min(xs) == max(xs) or min(ys) == max(ys):
            raise ValueError(f"Dataset {name!r} has a constant coordinate; correlation is undefined")
        values = _stdlib_values(xs, ys)
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError(f"Dataset {name!r} produced nonfinite statistics")
        stats.append({"dataset": name, "n": len(xs), **values})

    # A separate parser and numerical implementation make this a useful check,
    # rather than comparing two aliases for the same aggregate implementation.
    frame = pd.read_csv(path, sep="\t", dtype={"dataset": str},
                        keep_default_na=False, float_precision="round_trip")
    independent = []
    for name, group in frame.groupby("dataset", sort=True):
        array = group[["x", "y"]].to_numpy(dtype=np.float64)
        means, sds = np.mean(array, axis=0), np.std(array, axis=0, ddof=1)
        values = [means[0], means[1], sds[0], sds[1], np.corrcoef(array.T)[0, 1]]
        independent.append({"dataset": str(name), "n": int(len(group)),
                            **dict(zip(METRICS, map(float, values)))})
    if [(row["dataset"], row["n"]) for row in stats] != [
            (row["dataset"], row["n"]) for row in independent]:
        raise ValueError("Independent parsers disagree on dataset membership")
    errors = {metric: max(abs(a[metric] - b[metric]) for a, b in zip(stats, independent))
              for metric in METRICS}
    max_error = max(errors.values())
    ranges = {metric: {"min": min(row[metric] for row in stats),
                       "max": max(row[metric] for row in stats),
                       "span": max(row[metric] for row in stats) - min(row[metric] for row in stats)}
              for metric in METRICS}
    conventions = {
        "floor_2dp": (lambda value: math.floor(value * 100) / 100,
                      "floor(v * 100) / 100; towards negative infinity; author constraint"),
        "truncate_2dp": (lambda value: math.trunc(value * 100) / 100,
                         "trunc(v * 100) / 100; towards zero"),
        "round_2dp": (lambda value: float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                      "Decimal(str(v)), ROUND_HALF_UP; nearest hundredth, exact ties away from zero"),
    }
    precision = {}
    for name, (transform, definition) in conventions.items():
        unique = {metric: sorted({transform(row[metric]) for row in stats}) for metric in METRICS}
        precision[name] = {"passed": all(len(values) == 1 for values in unique.values()),
                           "unique_values": unique, "definition": definition}
    return {"rows": sum(row["n"] for row in stats), "dataset_count": len(stats),
            "stats": stats, "independent_stats": independent, "ranges": ranges,
            "crosscheck": {"max_abs_error": max_error, "tolerance": TOLERANCE,
                           "passed": max_error <= TOLERANCE, "per_metric_max_abs_error": errors,
                           "primary": "csv + statistics.mean/stdev/correlation",
                           "independent": "pandas.read_csv + NumPy mean/std(ddof=1)/corrcoef"},
            "precision": precision, "standard_deviation": "sample, denominator n - 1"}


_ADAPTER_HEADER = '''# Generated from explicitly reviewed author source; vendor is unchanged.
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np
import pandas as pd
import pytweening
'''

_ADAPTER_RUNNER = '''
if __name__ == "__main__":
    seed_path = Path(sys.argv[1])
    initial = pd.read_csv(seed_path, header=None, names=["x", "y"])
    if len(initial) != 142 or not np.isfinite(initial.to_numpy()).all():
        raise ValueError("Expected the 142 finite seed points")
    np.random.seed(20261023)
    start_values = [float(value) for value in get_values(initial)]
    xs, ys = initial.x.to_list(), initial.y.to_list()
    independent = [statistics.mean(xs), statistics.mean(ys), statistics.stdev(xs),
                   statistics.stdev(ys), statistics.correlation(xs, ys)]
    max_error = max(abs(a - b) for a, b in zip(start_values, independent))
    current = initial.copy()
    accepted = 0
    # Equivalent schedule to author run_pattern(iters=999), whose inclusive
    # loop performs 1000 proposals. Omit its image and animation-frame output.
    for iteration in range(1000):
        temperature = 0.4 * s_curve((999 - iteration) / 999)
        candidate = perturb(current.copy(), initial=initial,
                            target="circle", temp=temperature)
        if is_error_still_ok(initial, candidate, decimals=2):
            current = candidate
            accepted += 1
    end_values = [float(value) for value in get_values(current)]
    moved = np.linalg.norm(current.to_numpy() - initial.to_numpy(), axis=1)
    def target_distance(frame):
        radius = np.linalg.norm(frame.to_numpy() - np.array([54.26, 47.83]), axis=1)
        return float(np.mean(np.abs(radius - 30.0)))
    constraint_ok = bool(is_error_still_ok(initial, current, decimals=2))
    finite = bool(np.isfinite(current.to_numpy()).all())
    current.to_csv("generated.csv", index=False, float_format="%.17g")
    result = {
        "status": "passed" if constraint_ok and finite and max_error <= 1e-10 and np.any(moved > 0) else "failed",
        "seed": 20261023, "iterations_completed": 1000, "rows": int(len(current)),
        "target": "circle", "accepted_proposals": int(accepted),
        "rejected_proposals": int(1000 - accepted),
        "moved_points": int(np.count_nonzero(moved > 0)),
        "max_point_displacement": float(np.max(moved)),
        "finite_coordinates": finite, "author_constraint_passed": constraint_ok,
        "author_get_values_crosscheck": {"passed": max_error <= 1e-10,
            "max_abs_error": float(max_error), "tolerance": 1e-10},
        "metric_order": ["mean_x", "mean_y", "sd_x", "sd_y", "r"],
        "initial_stats": start_values, "final_stats": end_values,
        "initial_floor_2dp": [math.floor(value * 100) / 100 for value in start_values],
        "final_floor_2dp": [math.floor(value * 100) / 100 for value in end_values],
        "mean_circle_distance_before": target_distance(initial),
        "mean_circle_distance_after": target_distance(current),
        "full_figure_reproduction": False,
        "numpy_version": np.__version__, "pandas_version": pd.__version__,
    }
    Path("smoke-result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, allow_nan=False))
'''


def author_smoke(repo_dir: str | Path, output_dir: str | Path) -> dict:
    """Run reviewed author functions for 1000 proposals with a 30-second limit.

    This is a process with a timeout, not a security sandbox. Only the exact
    reviewed source and canonical seed digests can execute. Seed canonicalization
    replaces CRLF with LF only; the frozen input preserves its original bytes.
    Vendor files are not modified; the adapter documents compatibility changes.
    """
    repo, output = Path(repo_dir).resolve(), Path(output_dir).resolve()
    source_path = repo / "samestats" / "samestats.py"
    seed_path = repo / "samestats" / "datasets" / "seed" / "Datasaurus_data.csv"
    source_bytes = source_path.read_bytes()
    seed_bytes = seed_path.read_bytes()
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != REVIEWED_AUTHOR_SHA256:
        raise ValueError("Author source differs from the reviewed SHA-256; review it before execution")
    seed_digest = hashlib.sha256(seed_bytes).hexdigest()
    seed_canonical_digest = hashlib.sha256(seed_bytes.replace(b"\r\n", b"\n")).hexdigest()
    if seed_canonical_digest != REVIEWED_SEED_CANONICAL_SHA256:
        raise ValueError("Author seed differs from the reviewed canonical SHA-256; review it before execution")
    source = source_bytes.decode("utf-8")
    selected_names = {"get_values", "is_error_still_ok", "line_magnitude",
                      "distance_point_line", "dist", "get_points_for_shape", "perturb", "s_curve"}
    selected, found = [], set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in selected_names:
            selected.append(ast.get_source_segment(source, node))
            found.add(node.name)
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "LINE_SHAPES" for target in node.targets):
            selected.append(ast.get_source_segment(source, node))
    if found != selected_names:
        raise ValueError(f"Missing reviewed author functions: {sorted(selected_names - found)}")
    extracted = "\n\n".join(selected)
    modifications = []
    for column, coordinate in (("x", "xm"), ("y", "ym")):
        before = f"df['{column}'][row] = {coordinate}"
        after = f"df.loc[row, '{column}'] = {coordinate}"
        if extracted.count(before) != 1:
            raise ValueError(f"Expected one reviewed assignment: {before}")
        extracted = extracted.replace(before, after)
        modifications.append({"before": before, "after": after,
            "reason": "pandas 3 Copy-on-Write requires assignment to the DataFrame, not a chained Series"})
    adapter = _ADAPTER_HEADER + "\n" + extracted + "\n" + _ADAPTER_RUNNER
    output.mkdir(parents=True, exist_ok=True)
    (output / "author-original.py").write_bytes(source_bytes)
    (output / "seed-original.csv").write_bytes(seed_bytes)
    (output / "adapter.py").write_text(adapter, encoding="utf-8")
    # A previous interrupted run cannot be mistaken for this invocation's result.
    for name in ("smoke-result.json", "generated.csv"):
        (output / name).unlink(missing_ok=True)
    metadata = {
        "source_path": str(source_path), "source_sha256": digest,
        "seed_data_path": str(seed_path), "seed_data_sha256": seed_digest,
        "seed_data_canonical_sha256": seed_canonical_digest,
        "seed_data_canonicalization": "Replace CRLF with LF only; all other bytes unchanged",
        "adapter_sha256": hashlib.sha256(adapter.encode("utf-8")).hexdigest(),
        "extracted_author_functions": sorted(selected_names),
        "compatibility_modifications": modifications,
        "harness_changes": [
            "Extract only named functions and LINE_SHAPES; skip package imports, plotting, CLI, and resource loader.",
            "Use the author perturb and is_error_still_ok functions inside a bounded loop equivalent to run_pattern(iters=999): 1000 proposals.",
            "Keep the author run_pattern temperature schedule (0.4 to 0), circle target, perturb defaults including shake=0.1, and decimals=2.",
            "Verify and freeze the author dino seed in seed-original.csv; load that copy and omit all intermediate plots/animation frames; save final coordinates only.",
            "Set NumPy random seed to 20261023; limit numerical-library threads to one and subprocess wall time to 30 seconds.",
        ],
        "limitations": [
            "A bounded execution of selected author functions; not a complete package, paper figure, animation, or convergence reproduction.",
            "1000 proposals may retain much of the dinosaur shape; visible circular convergence is not the smoke-test criterion.",
            "The author perturb retry loop remains unchanged and can retry internally; the subprocess timeout bounds total wall time.",
            "The subprocess is not a security sandbox; execution is restricted to the reviewed source and seed digests.",
            "A fixed seed is repeatable in the recorded environment; numerical-library version changes can change the trajectory.",
        ],
        "timeout_seconds": SMOKE_TIMEOUT_SECONDS,
        "artifacts": {name: str(output / name) for name in (
            "adapter.py", "author-original.py", "seed-original.csv", "log.txt", "generated.csv", "smoke-result.json")},
        "seed": SMOKE_SEED, "iterations_requested": SMOKE_ITERATIONS,
        "full_figure_reproduction": False,
    }
    env = dict(os.environ)
    env.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "PYTHONIOENCODING": "utf-8"})
    started = time.perf_counter()
    try:
        process = subprocess.run([sys.executable, str(output / "adapter.py"), str(output / "seed-original.csv")],
                                 cwd=output, env=env, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=SMOKE_TIMEOUT_SECONDS,
                                 check=False)
        logs = process.stdout + "\nSTDERR:\n" + process.stderr
        result = {"status": "failed", "returncode": process.returncode,
                  "error": "Author adapter did not complete successfully"}
        if process.returncode == 0 and (output / "smoke-result.json").exists():
            result = json.loads((output / "smoke-result.json").read_text(encoding="utf-8"))
            result["returncode"] = 0
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        logs = decoded(error.stdout) + "\nSTDERR:\n" + decoded(error.stderr) + "\nTIMEOUT\n"
        result = {"status": "timeout", "error": "Author smoke exceeded 30 seconds; process terminated"}
    metadata["elapsed_seconds"] = time.perf_counter() - started
    (output / "log.txt").write_text(json.dumps(metadata, indent=2) + "\n\n" + logs, encoding="utf-8")
    return {**metadata, **result}
