# CS 6050 Graduate Algorithm Project 2

One dynamic programming algorithm, implemented in Python, tested on 10 inputs
of increasing size, and timed to check the runtime against the theoretical
bound.

| folder | algorithm | source | expected runtime |
|---|---|---|---|
| [`knuth_plass/`](knuth_plass/) | Knuth-Plass optimum-fit line breaking | Knuth & Plass, Software: Practice and Experience 11(11), 1981 | O(B·W): B legal breakpoints, W words per line |

The write-up is [`writeup/writeup.pdf`](writeup/writeup.pdf).

## Requirements

* Python 3.8 or newer. The algorithm, test cases and test runner use only the
  standard library.
* `numpy` and `matplotlib` are needed only to remake the plot (`make_plots.py`).

```
pip install -r requirements.txt
```

## Running the test cases

From the folder, run the 10 test cases:

```
cd knuth_plass && python run_tests.py && cd ..
```

The runner prints PASS/FAIL and the runtime for every case and saves the
timings to `results.csv` in that folder. Every case runs at least 3 times and
the fastest time is kept. On an M1 Max the slowest single run takes about
7 s, and a full run with repeats takes about 50 s. Pass
`--quick` to skip the two largest cases.

The extra edge-case tests are separate from the timed cases:

```
cd knuth_plass && python -m unittest -v test_knuth_plass
```

## Remaking the plot

After `python run_tests.py --width` in `knuth_plass/` (the `--width` pass is
needed for the line-width panel), run:

```
python make_plots.py
```

This writes `writeup/figures/knuth_plass.{svg,png}`.

## Regenerating the test cases

The test files in `tests/` were made by `generate_tests.py` with fixed seeds,
so re-running it produces identical files. The expected answers come from a
DP that runs backward from the end of the paragraph on its own model of the
text. It shares only the table of letter widths with the implementation being
tested.

## Layout

```
knuth_plass/
    knuth_plass.py       implementation
    generate_tests.py    makes tests/case01..case10.txt
    run_tests.py         checks + times the 10 cases -> results.csv
    test_knuth_plass.py  unit tests (edge cases, randomized checks)
    worked_example.py    prints the worked example in the write-up
    tests/               the 10 test case files
    README.md
make_plots.py            figure for the write-up
writeup/                 writeup.pdf and the figure
```