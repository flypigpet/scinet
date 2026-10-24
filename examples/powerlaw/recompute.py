"""Recompute bounded examples from the original 2014 powerlaw supplements.

Usage: python recompute.py INPUT_DIR OUTPUT_DIR

INPUT_DIR must contain the six pinned original text inputs below. OUTPUT_DIR
must not exist. This file contains SciNet's drivers, not the upstream module.
The caller must freeze every independent review before invoking this runner.
No old review marker is copied or fabricated here. The directed and extended
checks were developed for SciNet's previous single-review case; they are not
represented as tests independently designed by the current panel.

Python 3.12 is required for the recorded lib2to3 compatibility conversion.
The scientific runtime needs numpy, scipy and mpmath (see the project extra).
The bounded subprocesses are not a sandbox for arbitrary author programs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
import warnings


INPUT_HASHES = {
    "paper.txt": "83b2ec926d17aa4eae8e47a336d0781fd6bb2775a0fd061cdcad32d7ff3647ef",
    "author_powerlaw.py": "547c0e2d33b09ca8078e8d2abde686412ea1f548bb1a8e5b4d019006d929a105",
    "author_figures.py": "809d7a28227ede36ea90e1b611ef56a2575c3cd630b0c6894dd001e8554c3bdb",
    "blackouts.txt": "8187543b5700a75974661dd8349e172a83ce2d0972e79a81a7fcc06eafb96728",
    "words.txt": "cef3521f0f1d817df43cf35ef1f717e6f72d71f549646a51ba04acdc45a9b160",
    "worm.txt": "8754d06905e1d2318e19ba3e8b936f653657893b9ff8ce9fbc51ad9b26f992ac",
}
OPTIONAL_HASHES = {
    "paper.pdf": "578d1c7bfa991141f00575acea8a243cbf534608c6e1cb497705a7064bb54799",
    "AUTHOR_LICENSE.txt": "ec7e397e8ae8c4e0cf1571f61f435fbdec8f28080fce4befc96fd13554a726ef",
}
PAPER = {
    "title": "powerlaw: A Python Package for Analysis of Heavy-Tailed Distributions",
    "doi": "10.1371/journal.pone.0085777",
    "code_version": "Original PLOS Code S1 and Code S2, published 2014",
    "data_repository_commit": "d2b563a7a08bad96b4085fa69f351e9d9a20b1e7",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def validate_inputs(source, destination):
    if destination.exists():
        raise ValueError("Output directory already exists; refusing to overwrite evidence: " + str(destination))
    if source == destination or source in destination.parents:
        raise ValueError("Output directory must be outside the input directory")
    required = dict(INPUT_HASHES)
    required.update({name: digest for name, digest in OPTIONAL_HASHES.items() if (source / name).exists()})
    for name, expected in required.items():
        path = source / name
        if not path.is_file():
            raise ValueError("Missing required input: " + name)
        if sha(path) != expected:
            raise ValueError("SHA-256 mismatch for input: " + name)
    return required


def adapt_source(original):
    """Compatibility edits only; retain exact original and a full diff."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            from lib2to3.refactor import RefactoringTool
        except ModuleNotFoundError as error:
            raise RuntimeError("This historical-code conversion requires Python 3.12 with lib2to3") from error
    text = original.expandtabs(8)
    changes = [{"change": "expandtabs(8)", "reason": "Preserve Python tab stops in a spaces-only adapter."}]
    fixers = ["fix_print", "fix_raise", "fix_xrange", "fix_map", "fix_dict", "fix_filter", "fix_zip"]
    tool = RefactoringTool(["lib2to3.fixes." + fixer for fixer in fixers])
    text = str(tool.refactor_string(text, "published_powerlaw.py"))
    changes.append({"change": "lib2to3: " + ", ".join(fixers), "reason": "Python 2 syntax and eager sequence semantics on Python 3."})
    for expression, replacement in [(r"\b(data|parameters)\s*==\s*None", r"\1 is None"),
                                    (r"\b(data|parameters)\s*!=\s*None", r"\1 is not None")]:
        text, count = re.subn(expression, replacement, text)
        changes.append({"change": expression + " -> " + replacement, "count": count,
                        "reason": "Use identity checks rather than ambiguous modern NumPy array comparisons."})
    count = text.count("mask=-good_values")
    text = text.replace("mask=-good_values", "mask=~good_values")
    changes.append({"change": "mask=-good_values -> mask=~good_values", "count": count,
                    "reason": "Logical mask inversion for current NumPy; exact original NumPy behavior is not established."})
    count = text.count("from scipy.misc import comb")
    text = text.replace("from scipy.misc import comb", "from scipy.special import comb")
    changes.append({"change": "scipy.misc.comb -> scipy.special.comb", "count": count,
                    "reason": "Relocated SciPy API; the legacy negative-binomial path is not certified."})
    compile(text, "powerlaw_compat.py", "exec")
    return text, changes


def environment_record():
    packages = {}
    for name in ["numpy", "scipy", "mpmath", "pandas", "matplotlib", "pypdf"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "packages": packages}


def compare_continuous(output):
    """Numerical comparison is distinct from the model's review assessment."""
    root = output / "verification"
    author = json.loads((root / "author_results.json").read_text(encoding="utf-8"))
    independent = json.loads((root / "independent_continuous.json").read_text(encoding="utf-8"))
    pairs = [("unconstrained_minD", "blackouts_default"), ("fixed_xmin_1", "blackouts_xmin_1"),
             ("xmin_range_250_300", "blackouts_xmin_range_250_300"),
             ("sigma_lt_0.1", "blackouts_sigma_0_1"), ("sigma_lt_0.001", "blackouts_sigma_0_001")]
    checks = []
    for independent_key, author_key in pairs:
        for key in ["xmin", "alpha", "sigma", "D", "n_tail"]:
            left = independent["results"][independent_key][key]
            right = author["fits"][author_key]["n" if key == "n_tail" else key]
            difference = abs(left - right)
            checks.append({"case": independent_key, "field": key, "independent": left,
                           "author": right, "absolute_difference": difference, "within_1e_12": difference <= 1e-12})
    candidates = independent["candidate_scan"]
    author_candidates = author["blackouts_xmin_candidates"]
    scan = {"same_candidate_count": len(candidates) == len(author_candidates), "checks": []}
    for index, (left, right) in enumerate(zip(candidates, author_candidates)):
        for key in ["xmin", "alpha", "sigma", "D"]:
            difference = abs(left[key] - right[key])
            scan["checks"].append({"index": index, "field": key, "absolute_difference": difference,
                                   "within_1e_12": difference <= 1e-12})
    result = {"absolute_tolerance": 1e-12, "relative_tolerance": 0, "selected_fits": checks, "candidate_scan": scan,
              "all_within_tolerance": all(row["within_1e_12"] for row in checks + scan["checks"]) and scan["same_candidate_count"],
              "scope": "Continuous power-law fits only. Independent analytic exponential MLE and the author numerical optimizer may differ; both results are retained. No whole-paper or modern-package certification."}
    write_json(root / "independent_comparison.json", result)
    return result


def run(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    hashes = validate_inputs(source, destination)
    destination.mkdir(parents=True)
    record = {"started_at_utc": now(), "status": "started", "paper": PAPER,
              "input_directory": str(source), "output_directory": str(destination), "input_sha256": hashes,
              "runner_sha256": sha(__file__), "environment": environment_record(), "stages": [],
              "review_gate": "Caller must freeze all reviews before invoking this runner; the runner does not fabricate or copy review evidence.",
              "check_origin": "Directed and extended checks are reused from the previous single-review SciNet case, not independently designed by this panel.",
              "scope": "Nine selected author fits, independent continuous checks, four directed historical-code checks and four bounded extended checks. Not all paper figures, simulations, or current package versions.",
              "security_limit": "Pinned inspected historical source plus timeouts; not a secure arbitrary-code sandbox.",
              "preprocessing": {"blackouts": "raw values / 1000 as Code S2", "words": "raw counts", "worm": "positive values only as Code S2"}}
    write_json(destination / "execution.json", record)
    try:
        inputs = destination / "inputs"
        runtime = destination / "verification" / "runtime"
        inputs.mkdir()
        runtime.mkdir(parents=True)
        for name in hashes:
            shutil.copy2(source / name, inputs / name)
            if sha(inputs / name) != hashes[name]:
                raise ValueError("Input changed during copy: " + name)
        shutil.copy2(__file__, destination / "recompute.py")
        original = (inputs / "author_powerlaw.py").read_text(encoding="utf-8")
        converted, changes = adapt_source(original)
        adapter = runtime / "powerlaw_compat.py"
        adapter.write_bytes(converted.encode("utf-8"))
        (runtime / "compatibility.diff").write_bytes("".join(difflib.unified_diff(
            original.splitlines(keepends=True), converted.splitlines(keepends=True),
            fromfile="original/author_powerlaw.py", tofile="runtime/powerlaw_compat.py")).encode("utf-8"))
        write_json(runtime / "compatibility.json", {"source_sha256": hashes["author_powerlaw.py"],
            "adapter_sha256": sha(adapter), "changes": changes,
            "limit": "Compatibility edits are disclosed; the historical execution environment is not reconstructed. Original Code S2 is used as preprocessing reference, not executed in full."})
        scripts = [("author_driver.py", AUTHOR_SOURCE, [str(destination)], 180),
                   ("independent_continuous.py", INDEPENDENT_SOURCE, [], 180),
                   ("concern_checks.py", CONCERN_SOURCE, [], 540),
                   ("extended_checks.py", EXTENDED_SOURCE, [], 540)]
        for name, content, _, _ in scripts:
            compile(content, name, "exec")
            (destination / "verification" / name).write_text(content, encoding="utf-8")
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        for name, _, arguments, timeout in scripts:
            command = [sys.executable, str(destination / "verification" / name), *arguments]
            item = {"script": name, "command": command, "started_at_utc": now(), "timeout_seconds": timeout}
            started = time.perf_counter()
            record["stages"].append(item)
            write_json(destination / "execution.json", record)
            try:
                with (destination / "verification" / (name + ".stdout.log")).open("wb") as out, \
                     (destination / "verification" / (name + ".stderr.log")).open("wb") as err:
                    child = subprocess.run(command, cwd=destination, env=env, stdout=out, stderr=err, timeout=timeout)
                item.update(exit_code=child.returncode, status="completed" if child.returncode == 0 else "failed")
            except subprocess.TimeoutExpired:
                item.update(status="timeout")
            item.update(finished_at_utc=now(), elapsed_seconds=time.perf_counter() - started)
            write_json(destination / "execution.json", record)
        status = "completed" if all(stage["status"] == "completed" for stage in record["stages"]) else "partial"
        root = destination / "verification"
        author_path = root / "author_results.json"
        if author_path.exists() and (root / "independent_continuous.json").exists():
            compare_continuous(destination)
            if json.loads(author_path.read_text(encoding="utf-8"))["errors"]:
                status = "partial"
        for filename, collection, key in [("concern_checks.json", "checks", "execution_status"),
                                           ("extended_execution.json", "cases", "status")]:
            if (root / filename).is_file():
                children = json.loads((root / filename).read_text(encoding="utf-8"))[collection]
                if len(children) != 4 or any(child[key] != "completed" for child in children):
                    status = "partial"
            else:
                status = "partial"
        unchanged = all(sha(source / name) == digest and sha(inputs / name) == digest for name, digest in hashes.items())
        record.update(status=status, original_inputs_unchanged=unchanged)
        if not unchanged:
            raise ValueError("Input integrity changed during computation")
    except BaseException as error:
        record.update(status="failed", error=type(error).__name__ + ": " + str(error), traceback=traceback.format_exc())
        raise
    finally:
        record["finished_at_utc"] = now()
        write_json(destination / "execution.json", record)
        files = {path.relative_to(destination).as_posix(): sha(path)
                 for path in sorted(destination.rglob("*")) if path.is_file() and path.name != "manifest.json"}
        write_json(destination / "manifest.json", {"algorithm": "sha256", "files": files,
            "limit": "Local integrity inventory only, not a blockchain anchor, signature, or trusted timestamp."})
    print(json.dumps({"status": record["status"], "output": str(destination), "stages": record["stages"]}))
    return 0 if record["status"] == "completed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    arguments = parser.parse_args()
    try:
        return run(arguments.input_dir, arguments.output_dir)
    except (ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


# The following script bodies are SciNet's original verification code. They do
# not include the upstream powerlaw implementation or any historical output.


AUTHOR_SOURCE = r'''import json,math,pathlib,importlib.util,sys,time,traceback
import numpy as np
run=pathlib.Path(sys.argv[1]); runtime=run/'verification/runtime'
spec=importlib.util.spec_from_file_location('published_powerlaw',runtime/'powerlaw_compat.py')
pl=importlib.util.module_from_spec(spec);spec.loader.exec_module(pl)
b=np.loadtxt(run/'inputs/blackouts.txt')/1000.0
w=np.loadtxt(run/'inputs/words.txt'); worm=np.loadtxt(run/'inputs/worm.txt');worm=worm[worm>0]
result={'dataset_inventory':{'blackouts_n':len(b),'words_n':len(w),'worm_positive_n':len(worm)},'fits':{},'errors':[]}
def scalar(x):
 if x is None:return None
 if isinstance(x,(bool,np.bool_)):return bool(x)
 if isinstance(x,(int,np.integer)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x
def describe(f):
 return {k:scalar(getattr(f.power_law,k)) for k in ['alpha','D','sigma']}|{k:scalar(getattr(f,k,None)) for k in ['xmin','xmax','n','n_tail','noise_flag','fixed_xmin','discrete']}
def fit_case(name,data,**kw):
 try:
  start=time.perf_counter();f=pl.Fit(data,**kw);result['fits'][name]=describe(f)|{'elapsed_seconds':time.perf_counter()-start,'options':kw};return f
 except Exception as e:result['errors'].append({'case':name,'error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc()});return None
f=fit_case('blackouts_default',b)
fit_case('blackouts_xmin_1',b,xmin=1.0)
fit_case('blackouts_xmin_range_250_300',b,xmin=(250.0,300.0))
fit_case('blackouts_discrete_estimate',b,xmin=230.0,discrete=True,estimate_discrete=True)
fit_case('blackouts_discrete_exact',b,xmin=230.0,discrete=True,estimate_discrete=False)
fit_case('blackouts_sigma_0_1',b,sigma_threshold=.1)
fit_case('blackouts_sigma_0_001',b,sigma_threshold=.001)
fw=fit_case('words_discrete',w,discrete=True)
fit_case('worm_discrete',worm,discrete=True)
if f:
 for name,dist,normalize in [('power_vs_exponential','exponential',False),('power_vs_exponential_normalized','exponential',True),('power_vs_lognormal','lognormal',False)]:
  try:
   R,p=f.distribution_compare('power_law',dist,normalized_ratio=normalize)
   result.setdefault('comparisons',{})[name]={'R':scalar(R),'p':scalar(p)}
  except Exception as e:result['errors'].append({'case':name,'error':type(e).__name__+': '+str(e)})
 try:result['lognormal_parameters']={'mu':scalar(f.lognormal.mu),'sigma':scalar(f.lognormal.sigma)}
 except Exception as e:result['errors'].append({'case':'lognormal_parameters','error':str(e)})
 result['blackouts_xmin_candidates']=[{'xmin':scalar(x),'alpha':scalar(a),'D':scalar(d),'sigma':scalar(s)} for x,a,d,s in zip(f.xmins,f.alphas,f.Ds,f.sigmas)]
(run/'verification/author_results.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({'cases':len(result['fits']),'errors':result['errors']},ensure_ascii=False))
'''


INDEPENDENT_SOURCE = r'''"""Independent continuous Pareto/exponential checks using Python stdlib only.

No author module, author results, or model response is loaded. The panel coordinator controls review-before-computation ordering. Empirical CDF is
P(X < x), including ties, as specified for this verification task.
"""

from bisect import bisect_left
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time


RUN = Path(__file__).resolve().parents[1]
OUT = RUN / "verification"
INPUT = RUN / "inputs" / "blackouts.txt"
START_MONOTONIC = time.perf_counter()
START_UTC = datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_deadline():
    if time.perf_counter() - START_MONOTONIC > 175:
        raise TimeoutError("Independent computation exceeded 175 seconds")


def fit_at_xmin(data, xmin, comparison=False):
    check_deadline()
    tail = data[bisect_left(data, xmin):]
    n = len(tail)
    if n < 2:
        raise ValueError("At least two tail observations are required")
    logs = [math.log(x / xmin) for x in tail]
    sumlogs = math.fsum(logs)
    if sumlogs <= 0:
        raise ValueError("Continuous Pareto MLE is undefined for this tail")
    alpha = 1.0 + n / sumlogs
    sigma = (alpha - 1.0) / math.sqrt(n)

    # For repeated x, bisect_left / n gives P(X < x), without counting the
    # mass at the current observation. Evaluate the analytic CDF at each x.
    differences = [
        -math.expm1((1.0 - alpha) * math.log(x / xmin))
        - bisect_left(tail, x) / n
        for x in sorted(set(tail))
    ]
    d_plus = max(differences)
    d_minus = -min(differences)
    result = {
        "xmin": xmin,
        "n_tail": n,
        "alpha": alpha,
        "sigma": sigma,
        "D": max(d_plus, d_minus),
        "D_plus": d_plus,
        "D_minus": d_minus,
    }
    if comparison:
        # Both distributions have the same tail support [xmin, infinity).
        # Shifted exponential MLE lambda = 1 / mean(X - xmin).
        rate = n / math.fsum(x - xmin for x in tail)
        ll_power = [math.log(alpha - 1.0) - math.log(xmin) - alpha * v for v in logs]
        ll_exponential = [math.log(rate) - rate * (x - xmin) for x in tail]
        ll_difference = [a - b for a, b in zip(ll_power, ll_exponential)]
        ratio = math.fsum(ll_difference)
        mean_difference = ratio / n
        variance = math.fsum((v - mean_difference) ** 2 for v in ll_difference) / n
        normalized = ratio / math.sqrt(n * variance)
        result["power_law_vs_exponential"] = {
            "exponential_rate_mle": rate,
            "power_law_loglikelihood": math.fsum(ll_power),
            "exponential_loglikelihood": math.fsum(ll_exponential),
            "R": ratio,
            "normalized_R": normalized,
            "p_two_sided": math.erfc(abs(normalized) / math.sqrt(2.0)),
            "per_observation_logratio_population_variance": variance,
        }
    return result


def main():
    raw_data = [float(line.strip()) for line in INPUT.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if any(not math.isfinite(x) for x in raw_data):
        raise ValueError("Nonfinite input")
    if any(x < 0 for x in raw_data):
        raise ValueError("Unexpected negative blackout measurement")
    data = sorted(x / 1000.0 for x in raw_data if x > 0)
    candidates = [fit_at_xmin(data, x) for x in sorted(set(data))[:-1]]
    best = min(candidates, key=lambda row: row["D"])

    def selected_record(candidate, eligible, fallback=False):
        row = fit_at_xmin(data, candidate["xmin"], comparison=True)
        row["eligible_candidate_count"] = eligible
        row["fallback_to_unconstrained_minD"] = fallback
        return row

    range_candidates = [row for row in candidates if 250.0 <= row["xmin"] <= 300.0]
    if not range_candidates:
        raise ValueError("No observed xmin candidate in requested 250..300 range")
    results = {
        "unconstrained_minD": selected_record(best, len(candidates)),
        "fixed_xmin_1": fit_at_xmin(data, 1.0, comparison=True),
        "xmin_range_250_300": selected_record(min(range_candidates, key=lambda row: row["D"]), len(range_candidates)),
    }
    for threshold in (0.1, 0.001):
        eligible = [row for row in candidates if row["sigma"] < threshold]
        candidate = min(eligible, key=lambda row: row["D"]) if eligible else best
        row = selected_record(candidate, len(eligible), fallback=not eligible)
        row["sigma_threshold_strict"] = threshold
        results[f"sigma_lt_{threshold:g}"] = row

    # Guard result validity without relying on any expected manuscript value.
    for row in results.values():
        assert row["alpha"] > 1 and row["sigma"] > 0
        assert 0 <= row["D"] <= 1
        assert 0 <= row["power_law_vs_exponential"]["p_two_sided"] <= 1

    result = {
        "method": {
            "independence": "Standard-library implementation. No author module, author output, or model response read.",
            "scale": "blackouts.txt positive observations divided by 1000",
            "tail_support": "X >= xmin",
            "candidate_xmin": "Every distinct observed positive scaled value except the largest; ascending order; first minimum on exact D ties",
            "alpha": "1 + n / sum(log(X / xmin))",
            "sigma": "(alpha - 1) / sqrt(n)",
            "distance": "max absolute difference between analytic continuous Pareto CDF and empirical P(X < x), evaluated at distinct tail observations",
            "exponential": "Support [xmin,infinity); lambda MLE = n / sum(X - xmin)",
            "ratio": "sum(log f_power(X) - log f_exponential(X))",
            "normalized_ratio": "R / sqrt(n * population_variance(log f_power - log f_exponential))",
            "p": "erfc(abs(normalized_R) / sqrt(2))",
        },
        "provenance": {
            "input_path": str(INPUT),
            "input_sha256": sha256(INPUT),
            "script_path": str(Path(__file__).resolve()),
            "script_sha256": sha256(Path(__file__)),
            "review_ordering": "Enforced by caller, no historical review marker copied",
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "third_party_dependencies": "none; Python standard library only",
            "start_utc": START_UTC,
            "end_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.perf_counter() - START_MONOTONIC,
        },
        "input_summary": {
            "n_raw": len(raw_data),
            "n_positive_used": len(data),
            "n_zero_removed": len(raw_data) - len(data),
            "min_scaled": min(data),
            "max_scaled": max(data),
            "n_distinct_scaled": len(set(data)),
            "n_xmin_candidates": len(candidates),
        },
        "results": results,
        "candidate_scan": candidates,
    }
    destination = OUT / "independent_continuous.json"
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"destination": str(destination), "input_summary": result["input_summary"], "results": results, "provenance": result["provenance"]}, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
'''


CONCERN_SOURCE = r'''"""Bounded post-review checks of historical Code S1; does not modify it."""
from __future__ import annotations
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_runtime():
    spec = importlib.util.spec_from_file_location('historical_powerlaw', HERE/'runtime/powerlaw_compat.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def common():
    import numpy as np
    import scipy
    import mpmath
    return dict(python=sys.version, platform=platform.platform(), numpy=np.__version__,
                scipy=scipy.__version__, mpmath=mpmath.__version__,
                source_sha256=sha(RUN/'inputs/author_powerlaw.py'),
                adapter_sha256=sha(HERE/'runtime/powerlaw_compat.py'),
                check_origin='Directed tests reused from previous SciNet case; current reviews supplied no input to this script',
                script_sha256=sha(__file__))

def test_c1(pl):
    import numpy as np
    from scipy.integrate import quad
    x = np.array([1., 2., 5., 10.])
    cont = pl.Power_Law(xmin=1, xmax=10, parameters=[2.], discrete=False)
    mass, err = quad(lambda z: float(cont.pdf(np.array([z]))[0]), 1., 10., epsabs=1e-12)
    unnorm = np.array([quad(lambda z: float(cont.pdf(np.array([z]))[0]), 1., float(v))[0] for v in x])
    disc = pl.Power_Law(xmin=1, xmax=10, parameters=[2.], discrete=True)
    support = np.arange(1., 11.)
    pmf = disc.pdf(support)
    left = np.array([pmf[support<v].sum() for v in x])
    return dict(
        status='measured',
        continuous=dict(xmin=1, xmax=10, alpha=2, pdf_integral=mass, integral_error_estimate=err,
                        points=x.tolist(), author_cdf=cont.cdf(x).tolist(),
                        integrated_raw_pdf=unnorm.tolist(), normalized_integral=(unnorm/mass).tolist(),
                        max_pdf_cdf_mass_discrepancy=float(np.max(abs(cont.cdf(x)-unnorm)))),
        discrete=dict(support=support.tolist(), pmf=pmf.tolist(), pmf_total=float(pmf.sum()),
                      points=x.tolist(), author_cdf=disc.cdf(x).tolist(),
                      independent_left_cdf=left.tolist(),
                      max_cdf_discrepancy=float(np.max(abs(disc.cdf(x)-left)))),
        scope='Fixed-parameter Power_Law paths only. No xmax default fits are unaffected by this test; finite-xmax real-data figure and other subclasses not tested. No modern-version claim.')

def fit_summary(f):
    return {k: float(getattr(f, k)) for k in ['alpha','xmin','D','sigma','n']}

def test_c2(pl):
    import numpy as np
    from scipy.optimize import minimize_scalar
    a=np.loadtxt(RUN/'inputs/blackouts.txt')/1000.
    tail=np.sort(a[a>=230.]); x=np.unique(tail)
    empirical=np.searchsorted(tail,x,side='left')/len(tail)
    def dist(alpha): return float(np.max(abs((1-(x/230.)**(1-alpha))-empirical)))
    like=pl.Power_Law(data=a,xmin=230.,fit_method='Likelihood')
    ks=pl.Power_Law(data=a,xmin=230.,fit_method='KS')
    opt=minimize_scalar(dist,bounds=(1.000001,6.),method='bounded',options={'xatol':1e-13,'maxiter':1000})
    grid=np.linspace(1.000001,6,10001)
    gd=np.array([dist(v) for v in grid]); gi=int(gd.argmin())
    return dict(status='measured',
                dataset='blackouts.txt divided by 1000',fixed_xmin=230.,n_tail=len(tail),
                likelihood=fit_summary(like),requested_ks=fit_summary(ks),
                independent_bounded_minimization=dict(alpha=float(opt.x),D=float(opt.fun),
                     success=bool(opt.success),nfev=int(opt.nfev),bounds=[1.000001,6.],
                     objective='max absolute difference from left ECDF at unique observed points'),
                independent_dense_grid=dict(n=10001,alpha=float(grid[gi]),D=float(gd[gi])),
                D_improvement=float(ks.D-opt.fun),
                empirical_points=x.tolist(),empirical_left_cdf=empirical.tolist(),
                scope='Fixed xmin; outer xmin selection not tested here. Default MLE is not contradicted. Discrete fit_method branch not executed in this check.')

def test_c3(pl):
    import numpy as np
    raw=np.loadtxt(RUN/'inputs/blackouts.txt'); scaled=raw/1000.
    rounded=np.floor(scaled+0.5)
    def count(a,xmin):
        tail=a[a>=xmin]; bad=~np.isclose(a,np.rint(a),atol=1e-10,rtol=0)
        tb=~np.isclose(tail,np.rint(tail),atol=1e-10,rtol=0)
        return dict(n=len(a),n_noninteger=int(bad.sum()),n_tail=len(tail),n_tail_noninteger=int(tb.sum()),
                    noninteger_values=a[bad].tolist())
    configs=[('persons_discrete_approx',raw,230000.,True,True),
             ('persons_discrete_exact',raw,230000.,True,False),
             ('thousands_continuous',scaled,230.,False,True),
             ('thousands_noninteger_discrete_approx',scaled,230.,True,True),
             ('thousands_noninteger_discrete_exact',scaled,230.,True,False),
             ('rounded_thousands_discrete_approx',rounded,230.,True,True),
             ('rounded_thousands_discrete_exact',rounded,230.,True,False)]
    fits=[]
    for name,a,xmin,discrete,estimate in configs:
        f=pl.Power_Law(data=a,xmin=xmin,discrete=discrete,estimate_discrete=estimate)
        fits.append(dict(name=name,discrete=discrete,estimate_discrete=estimate,**fit_summary(f)))
    return dict(status='measured',
                counts=dict(original_persons=count(raw,230000.),scaled_thousands=count(scaled,230.),
                            rounded_thousands=count(rounded,230.)),
                quantization='floor(raw_persons / 1000 + 0.5); nearest integer thousands, ties upward; threshold 230 after quantization',
                fits=fits,
                scope='Original-person and rounded-thousand models have different support and likelihood measures; alpha comparison is a sensitivity demonstration, not model equivalence. Continuous original-paper examples not invalidated.')

def test_c4(pl):
    import numpy as np
    a=np.loadtxt(RUN/'inputs/blackouts.txt')/1000.
    fit=pl.Fit(a,xmin=230.,discrete=False)
    pp=fit.power_law; tp=fit.truncated_power_law
    params={'power_law':[float(pp.alpha)],'truncated_power_law':[float(tp.alpha),float(tp.Lambda)]}
    ll={n:getattr(fit,n).loglikelihoods(fit.data) for n in params}
    rows=[]
    for first,second in [('power_law','truncated_power_law'),('truncated_power_law','power_law')]:
        for nested in [None,True,False]:
            r,p=fit.distribution_compare(first,second,nested=nested)
            dr,dp=pl.loglikelihood_ratio(ll[first].copy(),ll[second].copy(),nested=nested)
            row=dict(first=first,second=second,requested_nested=nested,object_interface=dict(R=float(r),p=float(p)),
                     direct_same_argument=dict(R=float(dr),p=float(dp)),
                     direct_nested_true=list(map(float,pl.loglikelihood_ratio(ll[first].copy(),ll[second].copy(),nested=True))),
                     direct_nested_false=list(map(float,pl.loglikelihood_ratio(ll[first].copy(),ll[second].copy(),nested=False))))
            try:
                mr,mp=pl.distribution_compare(fit.data,first,params[first],second,params[second],False,230.,None,nested=nested)
                row['legacy_function_interface']=dict(R=float(mr),p=float(mp))
            except Exception:
                row['legacy_function_interface_error']=traceback.format_exc()
            rows.append(row)
    return dict(status='compare_rows_for_explicit_false_override',dataset='blackouts / 1000, continuous fixed xmin=230',
                n_tail=len(fit.data),parameters=params,rows=rows,
                data=fit.data.tolist(),loglikelihoods={k:v.tolist() for k,v in ll.items()},
                scope='Control-flow/options correctness test, not a calibration test. nested=None intentionally enables name-based inference; explicit False is the tested override. Fitted truncation optimizer convergence not independently certified.')

def child(test):
    started=now(); begin=time.perf_counter()
    try:
        pl=load_runtime()
        result=globals()['test_'+test.lower()](pl)
        result.update(test=test,started_at_utc=started,completed_at_utc=now(),elapsed_seconds=time.perf_counter()-begin,
                      environment=common(),execution_status='completed')
    except Exception:
        result=dict(test=test,started_at_utc=started,completed_at_utc=now(),elapsed_seconds=time.perf_counter()-begin,
                    execution_status='error',traceback=traceback.format_exc())
    print('SCINET_RESULT_JSON='+json.dumps(result,ensure_ascii=False,allow_nan=False))

def main():
    out=HERE/'concern_checks.json'
    if out.exists(): raise RuntimeError('Refusing to overwrite completed evidence')
    results=dict(started_at_utc=now(),environment=common(),per_test_timeout_seconds=120,checks=[])
    env=os.environ.copy(); env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg',PYTHONIOENCODING='utf-8')
    with (HERE/'concern_checks_stdout.log').open('w',encoding='utf-8') as stdout, (HERE/'concern_checks_stderr.log').open('w',encoding='utf-8') as stderr:
        for test in ['C1','C2','C3','C4']:
            start=now(); begin=time.perf_counter()
            try:
                p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--test',test],cwd=HERE,env=env,
                                 capture_output=True,text=True,encoding='utf-8',timeout=120)
                stdout.write(f'\n=== {test} {start} ===\n'+p.stdout);stdout.flush()
                stderr.write(f'\n=== {test} {start} ===\n'+p.stderr);stderr.flush()
                records=[line.removeprefix('SCINET_RESULT_JSON=') for line in p.stdout.splitlines() if line.startswith('SCINET_RESULT_JSON=')]
                result=json.loads(records[-1]) if records else dict(test=test,execution_status='no_result',returncode=p.returncode)
                result['returncode']=p.returncode
            except subprocess.TimeoutExpired as e:
                def text(v): return v.decode('utf-8','replace') if isinstance(v,bytes) else (v or '')
                stdout.write(text(e.stdout));stdout.flush();stderr.write(text(e.stderr));stderr.flush()
                result=dict(test=test,execution_status='timeout',started_at_utc=start,elapsed_seconds=time.perf_counter()-begin)
            results['checks'].append(result)
            out.write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            print(test,result['execution_status'],flush=True)
    results['completed_at_utc']=now()
    out.write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--test': child(sys.argv[2])
    else: main()
'''


EXTENDED_SOURCE = r'''import pathlib,json,hashlib,subprocess,sys,time,os,traceback,importlib.util
from datetime import datetime,timezone
run=pathlib.Path(__file__).resolve().parents[1]
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
if len(sys.argv)==1:
 record={'started_at_utc':now(),'purpose':'Bounded extended checks reused from the previous SciNet case, not full sensitivity or simulation calibration','script_sha256':sha(pathlib.Path(__file__)),'cases':[]}
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 for case in ['exponential_precision','worm_comparisons','words_lognormal','blackouts_discrete_auto']:
  t=time.perf_counter();item={'case':case,'started_at_utc':now(),'timeout_seconds':120}
  try:
   with (run/f'verification/{case}_stdout.log').open('wb') as out,(run/f'verification/{case}_stderr.log').open('wb') as err:
    p=subprocess.run([sys.executable,__file__,case],cwd=run/'verification',env=env,stdout=out,stderr=err,timeout=120)
   item.update(exit_code=p.returncode,status='completed' if p.returncode==0 else 'failed')
  except subprocess.TimeoutExpired:item.update(status='timeout')
  item.update(finished_at_utc=now(),elapsed_seconds=time.perf_counter()-t);record['cases'].append(item);write(run/'verification/extended_execution.json',record)
 record['finished_at_utc']=now();write(run/'verification/extended_execution.json',record);print(json.dumps(record));sys.exit(0)
import numpy as np
case=sys.argv[1];t=time.perf_counter();result={'case':case,'started_at_utc':now()}
spec=importlib.util.spec_from_file_location('historical',run/'verification/runtime/powerlaw_compat.py');pl=importlib.util.module_from_spec(spec);spec.loader.exec_module(pl)
def compare(f,d):
 R,p=f.distribution_compare('power_law',d)
 a=f.power_law.loglikelihoods(f.data);b=getattr(f,d).loglikelihoods(f.data)
 params={k:float(getattr(getattr(f,d),k)) for k in ['parameter1','parameter2','parameter3'] if getattr(getattr(f,d),k,None) is not None}
 return {'R':float(R),'p':float(p),'xmin':float(f.xmin),'tail_n':len(f.data),'alpha':float(f.power_law.alpha),'alternative_parameters':params,'pointwise_loglikelihoods':{'x':f.data.tolist(),'power_law':a.tolist(),d:b.tolist()},'optimizer_warning_status':'Original Distribution.fit discards warnflag; no claim of optimizer convergence.'}
try:
 if case=='exponential_precision':
  b=np.loadtxt(run/'inputs/blackouts.txt')/1000;f=pl.Fit(b);f.exponential
  lam=1/(float(np.mean(f.data))-float(f.xmin));author_lam=float(f.exponential.Lambda)
  result.update(analytic_lambda=lam,author_lambda=author_lam,author=compare(f,'exponential'))
  exact=pl.Exponential(xmin=f.xmin,parameters=[lam]);a=f.power_law.loglikelihoods(f.data);b=exact.loglikelihoods(f.data)
  R,p=pl.loglikelihood_ratio(a,b,normalized_ratio=True)
  result['analytic_lambda_with_author_likelihoods']={'raw_R':float(sum(a-b)),'normalized_R':float(R),'p':float(p),'exponential_loglikelihood_gain':float(sum(b)-sum(f.exponential.loglikelihoods(f.data)))}
 elif case=='worm_comparisons':
  d=np.loadtxt(run/'inputs/worm.txt');f=pl.Fit(d[d>0],discrete=True)
  result['power_vs_exponential']=compare(f,'exponential');write(run/f'verification/{case}.json',result)
  result['power_vs_truncated']=compare(f,'truncated_power_law')
 elif case=='words_lognormal':
  f=pl.Fit(np.loadtxt(run/'inputs/words.txt'),discrete=True);result['comparison']=compare(f,'lognormal')
 elif case=='blackouts_discrete_auto':
  d=np.loadtxt(run/'inputs/blackouts.txt')/1000;result['fits']=[]
  for estimate in [True,False]:
   start=time.perf_counter();f=pl.Fit(d,discrete=True,estimate_discrete=estimate)
   result['fits'].append({'estimate_discrete':estimate,'xmin':float(f.xmin),'alpha':float(f.power_law.alpha),'D':float(f.power_law.D),'n':int(f.n),'elapsed_seconds':time.perf_counter()-start});write(run/f'verification/{case}.json',result)
 result['status']='completed'
except Exception as exc:
 result.update(status='failed',error=repr(exc),traceback=traceback.format_exc());raise
finally:
 result.update(finished_at_utc=now(),elapsed_seconds=time.perf_counter()-t);write(run/f'verification/{case}.json',result)
'''


if __name__ == "__main__":
    raise SystemExit(main())
