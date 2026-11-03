# runs break_paragraph on every case in tests/, checks the answer and times it
# usage: python run_tests.py [--quick] [--repeat N] [--width]
# --width also runs case 5 at wider columns to test the W factor (width.csv) and
# measures active nodes by position in the paragraph (startup.csv)

import argparse
import csv
import gc
import glob
import os
import sys
import time
from knuth_plass import break_paragraph, score_breaks, text_to_paragraph

HERE = os.path.dirname(os.path.abspath(__file__))

WIDTHS = [500, 1000, 2000, 4000, 8000, 16000]  # narrower than 500 isn't feasible
SEGMENTS = [250, 500, 1000, 2000, 4000, 8000, 16000, 32000]

def load_case(path):
    fields = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            key, _, val = line.rstrip("\n").partition(" ")
            fields[key] = val
    return (fields["text"], int(fields["width"]), float(fields["rho"]),
            int(fields["alpha"]), int(fields["gamma"]),
            float(fields["expected_demerits"]))

def best_time(fn, repeat, min_total=1.0):
    times = []
    result = None
    gc.collect()
    gc.disable()
    try:
        while len(times) < repeat or (sum(times) < min_total and len(times) < 1000):
            t0 = time.perf_counter()
            result = fn()
            times.append(time.perf_counter() - t0)
    finally:
        gc.enable()
    return min(times), len(times), result

def width_sweep(path, repeat):
    text, _, rho, alpha, gamma, _ = load_case(path)
    words = len(text.split())
    par = text_to_paragraph(text)
    rows = []
    print(f"\nwider columns, {os.path.basename(path)[:-4]} ({words} words):")
    print(f"{'width':>7}{'W':>8}{'active/B':>10}{'time (s)':>11}{'active/B, g=0':>15}{'time (s)':>11}")
    for width in WIDTHS:
        t, runs, res = best_time(lambda: break_paragraph(par, [width], rho, alpha, gamma), repeat)
        t0, _, res0 = best_time(lambda: break_paragraph(par, [width], rho, alpha, 0), repeat)
        w = words / len(res.breaks)
        active = res.examined / res.legal
        active0 = res0.examined / res0.legal
        print(f"{width:>7}{w:>8.1f}{active:>10.1f}{t:>11.4f}{active0:>15.1f}{t0:>11.4f}")
        rows.append({"width": width, "B": res.legal, "W": w, "active": active,
                     "seconds": t, "runs": runs, "active_gamma0": active0,
                     "seconds_gamma0": t0})
    return rows

def startup_profile(path):
    # active nodes per breakpoint in each stretch of the same paragraph
    text, width, rho, alpha, gamma, _ = load_case(path)
    words = text.split()
    rows = []
    done_seen = done_b = start = 0
    print("\nactive nodes per breakpoint by position in the paragraph:")
    for end in SEGMENTS:
        res = break_paragraph(text_to_paragraph(" ".join(words[:end])), [width],
                              rho, alpha, gamma)
        active = (res.examined - done_seen) / (res.legal - done_b)
        print(f"  words {start:>6} to {end:>6}: {active:6.2f}")
        rows.append({"from_word": start, "to_word": end, "active": active})
        done_seen, done_b, start = res.examined, res.legal, end
    return rows

def write_csv(name, rows):
    with open(os.path.join(HERE, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="skip cases 9 and 10")
    ap.add_argument("--width", action="store_true")
    args = ap.parse_args()

    all_cases = sorted(glob.glob(os.path.join(HERE, "tests", "case*.txt")))
    if not all_cases:
        sys.exit("no test cases found, run generate_tests.py first")
    cases = all_cases[:8] if args.quick else all_cases

    rows = []
    failed = 0
    print(f"{'case':<8}{'words':>9}{'B':>9}{'lines':>7}{'W':>7}{'active/B':>10}"
          f"{'time (s)':>11}{'runs':>6}   result")
    for path in cases:
        name = os.path.basename(path)[:-4]
        text, width, rho, alpha, gamma, expected = load_case(path)
        par = text_to_paragraph(text)
        t, runs, res = best_time(lambda: break_paragraph(par, [width], rho, alpha, gamma),
                                 args.repeat)

        # ties are possible so check the demerits, then rescore the breaks from
        # scratch to make sure they're feasible and really cost that much
        ok = False
        if res is not None:
            rescored = score_breaks(par, res.breaks, [width], rho, alpha, gamma)
            ok = (abs(res.demerits - expected) <= 1e-9 * expected
                  and rescored is not None
                  and abs(rescored - expected) <= 1e-9 * expected)
        failed += not ok
        words = len(text.split())
        lines = len(res.breaks) if res else 0
        w = words / lines if lines else 0
        active = res.examined / res.legal if res else 0
        print(f"{name:<8}{words:>9}{res.legal if res else 0:>9}{lines:>7}{w:>7.1f}{active:>10.1f}"
              f"{t:>11.4f}{runs:>6}   {'PASS' if ok else 'FAIL'} "
              f"(demerits {res.demerits if res else 0:.1f}, expected {expected:.1f})")
        rows.append({"case": name, "words": words, "B": res.legal if res else 0,
                     "lines": lines, "W": w, "active": active, "seconds": t,
                     "runs": runs, "passed": ok})

    # separate pass, so these big allocations can't slow the timings above
    if args.width:
        write_csv("width.csv", width_sweep(all_cases[4], args.repeat))
        write_csv("startup.csv", startup_profile(all_cases[-1]))

    write_csv("results.csv", rows)
    print(f"\n{len(rows) - failed}/{len(rows)} passed, timings in results.csv")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
