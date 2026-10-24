# Generated from explicitly reviewed author source; vendor is unchanged.
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np
import pandas as pd
import pytweening

LINE_SHAPES = [
    'x', 'h_lines', 'v_lines', 'wide_lines', 'high_lines', 'slant_up',
    'slant_down', 'center', 'star', 'down_parab'
]

def get_values(df):
    """Calculates the summary statistics for the given set of points

    Args:
        df (pd.DataFrame): A ``DataFrame`` with ``x`` and ``y`` columns

    Returns:
        list: ``[x-mean, y-mean, x-stdev, y-stdev, correlation]``
    """
    xm = df.x.mean()
    ym = df.y.mean()
    xsd = df.x.std()
    ysd = df.y.std()
    pc = df.corr().x.y

    return [xm, ym, xsd, ysd, pc]

def is_error_still_ok(df1, df2, decimals=2):
    """Checks to see if the statistics are still within the acceptable bounds

    Args:
        df1 (pd.DataFrame): The original data set
        df2 (pd.DataFrame): The test data set
        decimals (int):     The number of decimals of precision to check

    Returns:
        bool: ``True`` if the maximum error is acceptable, ``False`` otherwise
    """
    r1 = get_values(df1)
    r2 = get_values(df2)

    # check each of the error values to check if they are the same to the
    # correct number of decimals
    r1 = [math.floor(r * 10**decimals) for r in r1]
    r2 = [math.floor(r * 10**decimals) for r in r2]

    # we are good if r1 and r2 have the same numbers
    er = np.subtract(r1, r2)
    er = [abs(n) for n in er]

    return np.max(er) == 0

def line_magnitude(x1, y1, x2, y2):
    """Calculates the distance between ``(x1, y1)`` and ``(x2, y2)``

    Args:
        x1 (float): The x coordinate of the first point
        y1 (float): The y coordinate of the first point
        x2 (float): The x coordinate of the second point
        y2 (float): The y coordinate of the second point
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def distance_point_line(px, py, x1, y1, x2, y2):
    """Calculates the minimum distance between a point and a line, used to
    determine if the points are getting closer to the target. Implementation
    based on `this VBA code`_

    .. this VBA code: http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/source.vba
    """
    line_mag = line_magnitude(x1, y1, x2, y2)

    if line_mag < 0.00000001:
        # Arbitrarily large value
        return 9999

    u1 = (((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1)))
    u = u1 / (line_mag * line_mag)

    if (u < 0.00001) or (u > 1):
        # closest point does not fall within the line segment, take the shorter
        # distance to an endpoint
        ix = line_magnitude(px, py, x1, y1)
        iy = line_magnitude(px, py, x2, y2)
        if ix > iy:
            distance = iy
        else:
            distance = ix
    else:
        # Intersecting point is on the line, use the formula
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        distance = line_magnitude(px, py, ix, iy)

    return distance

def dist(p1, p2):
    """Calculates the euclidean distance between ``p1`` and ``p2`` where these
    are 2-tuples (or lists, numpy arrays, etc).

    Args:
        p1 ((float, float)): The first point
        p2 ((float, float)): The second point
    """
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_points_for_shape(line_shape):
    """These are the hard-coded shapes which we perturb towards. It would useful
    to have a tool for drawing these shapes instead
    """
    lines = []
    if line_shape == 'x':
        l1 = [[20, 0], [100, 100]]
        l2 = [[20, 100], [100, 0]]
        lines = [l1, l2]
    elif line_shape == "h_lines":
        lines = [[[0, y], [100, y]] for y in [10, 30, 50, 70, 90]]
    elif line_shape == 'v_lines':
        lines = [[[x, 0], [x, 100]] for x in [10, 30, 50, 70, 90]]
    elif line_shape == 'wide_lines':
        l1 = [[10, 0], [10, 100]]
        l2 = [[90, 0], [90, 100]]
        lines = [l1, l2]
    elif line_shape == 'high_lines':
        l1 = [[0, 10], [100, 10]]
        l2 = [[0, 90], [100, 90]]
        lines = [l1, l2]
    elif line_shape == 'slant_up':
        l1 = [[0, 0], [100, 100]]
        l2 = [[0, 30], [70, 100]]
        l3 = [[30, 0], [100, 70]]
        l4 = [[50, 0], [100, 50]]
        l5 = [[0, 50], [50, 100]]
        lines = [l1, l2, l3, l4, l5]
    elif line_shape == 'slant_down':
        l1 = [[0, 100], [100, 0]]
        l2 = [[0, 70], [70, 0]]
        l3 = [[30, 100], [100, 30]]
        l4 = [[0, 50], [50, 0]]
        l5 = [[50, 100], [100, 50]]
        lines = [l1, l2, l3, l4, l5]
    elif line_shape == 'center':
        cx = 54.26
        cy = 47.83
        l1 = [[cx, cy], [cx, cy]]
        lines = [l1]
    elif line_shape == 'star':
        star_pts = [10, 40, 40, 40, 50, 10, 60, 40, 90, 40, 65, 60, 75, 90, 50, 70, 25, 90, 35, 60]
        pts = [star_pts[i:i + 2] for i in range(0, len(star_pts), 2)]
        pts = [[p[0] * 0.8 + 20, 100 - p[1]] for p in pts]
        pts.append(pts[0])
        lines = [pts[i:i + 2] for i in range(0, len(pts) - 1, 1)]
    elif line_shape == 'down_parab':
        curve = [[x, -((x - 50) / 4)**2 + 90] for x in np.arange(0, 100, 3)]
        lines = [curve[i:i + 2] for i in range(0, len(curve) - 1, 1)]
    else:
        raise ValueError(line_shape)

    return lines

def perturb(
        df,
        initial,
        target='circle',
        line_error=1.5,
        shake=0.1,
        allowed_dist=3,  # should be 2, just making it bigger for the sp example
        temp=0,
        x_bounds=[0, 100],
        y_bounds=[0, 100],
        custom_points=None):
    """This is the function which does one round of perturbation

    Args:
        df: is the current dataset
        initial: is the original dataset
        target: is the name of the target shape
        shake: the maximum amount of movement in each iteration
    """
    # take one row at random, and move one of the points a bit
    row = np.random.randint(0, len(df))
    i_xm = df['x'][row]
    i_ym = df['y'][row]

    # this is the simulated annealing step, if "do_bad", then we are willing to
    # accept a new state which is worse than the current one
    do_bad = np.random.random_sample() < temp

    while True:
        xm = i_xm + np.random.randn() * shake
        ym = i_ym + np.random.randn() * shake

        if target == 'circle':
            # info for the circle
            cx = 54.26
            cy = 47.83
            r = 30

            dc1 = dist([df['x'][row], df['y'][row]], [cx, cy])
            dc2 = dist([xm, ym], [cx, cy])

            old_dist = abs(dc1 - r)
            new_dist = abs(dc2 - r)

        elif target == 'bullseye':
            # info for the bullseye
            cx = 54.26
            cy = 47.83
            rs = [18, 37]

            dc1 = dist([df['x'][row], df['y'][row]], [cx, cy])
            dc2 = dist([xm, ym], [cx, cy])

            old_dist = np.min([abs(dc1 - r) for r in rs])
            new_dist = np.min([abs(dc2 - r) for r in rs])

        elif target == 'dots':
            # create a grid of "cluster points" and move if you are getting closer
            # (or are already close enough)
            xs = [25, 50, 75]
            ys = [20, 50, 80]

            old_dist = np.min([
                dist([x, y], [df['x'][row], df['y'][row]])
                for x, y in itertools.product(xs, ys)
            ])
            new_dist = np.min([
                dist([x, y], [xm, ym])
                for x, y in itertools.product(xs, ys)
            ])

        elif target in LINE_SHAPES:
            lines = get_points_for_shape(target)

            # calculate how far the point is from the closest one of these
            old_dist = np.min([
                distance_point_line(i_xm, i_ym, l[0][0], l[0][1], l[1][0], l[1][1])
                for l in lines
            ])
            new_dist = np.min([
                distance_point_line(xm, ym, l[0][0], l[0][1], l[1][0], l[1][1])
                for l in lines
            ])
        else:
            raise ValueError(target)

        # check if the new distance is closer than the old distance
        # or, if it is less than our allowed distance
        # or, if we are do_bad, that means we are accepting it no matter what
        # if one of these conditions are met, jump out of the loop
        close_enough = (new_dist < old_dist or new_dist < allowed_dist or do_bad)
        within_bounds = ym > y_bounds[0] and ym < y_bounds[1] and xm > x_bounds[0] and xm < x_bounds[1]
        if close_enough and within_bounds:
            break

    # set the new data point, and return the set
    df.loc[row, 'x'] = xm
    df.loc[row, 'y'] = ym
    return df

def s_curve(v):
    return pytweening.easeInOutQuad(v)

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
