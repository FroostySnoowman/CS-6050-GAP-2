# makes the runtime plot in writeup/figures from knuth_plass/results.csv and width.csv
# usage: python make_plots.py

import csv
import json
import math
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "writeup", "figures")

MEASURED = "#2a78d6"
THEORY = "#eb6834"
OTHER = "#8a8984"
INK = "#1f1f1e"
INK2 = "#52514e"
GRID = "#e4e3df"

N_FIT = 5  # fit c on the largest 5 cases
LONG_W = 45  # same idea for the width panel, fit c once fitness classes level off

def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def style_axes(ax):
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.grid(False, which="minor")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b9b8b2")
    ax.tick_params(colors=INK2, labelsize=7)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)

def seconds_fmt(v, _):
    if v >= 1:
        return f"{v:g} s"
    if v >= 1e-3:
        return f"{v * 1e3:g} ms"
    return f"{v * 1e6:g} µs"

def fit(x, t, f):
    xs, ts = x[-N_FIT:], t[-N_FIT:]
    c = math.exp(np.mean(np.log(ts) - np.log(f(xs))))
    slope = np.polyfit(np.log(xs), np.log(ts), 1)[0]
    f_slope = np.polyfit(np.log(xs), np.log(f(xs)), 1)[0]
    return c, slope, f_slope

def label_ref_lines(ax, lines, x, t):
    # call after tight_layout, the angle depends on the axes size
    ax.set_xlim(ax.get_xlim())
    ax.set_ylim(ax.get_ylim())
    lx0, lx1 = np.log(ax.get_xlim())
    for g, lab, pos in lines:
        xl = math.exp(lx0 + pos * (lx1 - lx0))
        p0 = ax.transData.transform((xl, g(xl)))
        p1 = ax.transData.transform((xl * 1.5, g(xl * 1.5)))
        angle = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        below = g(x[0]) < t[0]
        ax.annotate(lab, (xl, g(xl)), xytext=(0, -3 if below else 3),
                    textcoords="offset points", fontsize=7, color=INK2,
                    rotation=angle, rotation_mode="anchor", ha="left",
                    va="top" if below else "bottom")

def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "path",
                         "mathtext.fontset": "dejavusans"})
    rows = read_csv(os.path.join(HERE, "knuth_plass", "results.csv"))
    x = np.array([float(r["B"]) for r in rows])
    t = np.array([float(r["seconds"]) for r in rows])
    w_fixed = float(np.mean([float(r["W"]) for r in rows]))

    f = lambda b: b * w_fixed
    c, slope, f_slope = fit(x, t, f)
    ratio = t / (c * f(x))
    slope_all = np.polyfit(np.log(x), np.log(t), 1)[0]

    # one page limit, so the panels are stacked to sit in a column beside the text
    fig = plt.figure(figsize=(3.6, 3.95), layout="constrained")
    outer = fig.add_gridspec(2, 1, height_ratios=[2.95, 2.1])
    top = outer[0].subgridspec(2, 1, height_ratios=[2.15, 0.8], hspace=0.04)
    ax = fig.add_subplot(top[0])
    ax2 = fig.add_subplot(top[1])
    ax3 = fig.add_subplot(outer[1])

    xx = np.geomspace(x[0] / 1.3, x[-1] * 1.3, 200)
    ref_lines = []
    for g, lab, pos in [(lambda v: v ** 1.25, r"$B^{1.25}$", 0.2),
                        (lambda v: v * np.log2(v), r"$B\log B$", 0.3)]:
        k = t[-1] / g(x[-1])
        ax.plot(xx, k * g(xx), color=OTHER, lw=1.0, ls=(0, (4, 3)), zorder=1)
        ref_lines.append((lambda v, g=g, k=k: k * g(v), lab, pos))
    ax.plot(xx, c * f(xx), color=THEORY, lw=2, zorder=2,
            label=rf"$c\cdot B\cdot W$, $W$ = {w_fixed:.1f}")
    ax.plot(x, t, "o", ms=5.5, color=MEASURED, mec="white", mew=1, zorder=3,
            label="measured (min of runs)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(t.min() / 9, t.max() * 8)  # room for the legend, note and labels
    ax.yaxis.set_major_formatter(FuncFormatter(seconds_fmt))
    ax.set_ylabel("runtime", fontsize=7.5)
    style_axes(ax)
    ax.tick_params(labelbottom=False)
    ax.legend(loc="upper left", fontsize=6.8, frameon=False, labelcolor=INK)
    ax.set_title("Runtime vs. input size", loc="left",
                 fontsize=8.5, color=INK, fontweight="bold")
    note = (f"log-log slope, 5 largest: {slope:.3f}\n"
            f"log-log slope, all 10: {slope_all:.3f}")
    ax.text(0.98, 0.04, note, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.8, color=INK2, linespacing=1.4)

    ax2.axhline(1.0, color=THEORY, lw=1.2, zorder=1)
    ax2.axhspan(0.9, 1.1, color=THEORY, alpha=0.08, lw=0, zorder=0)
    ax2.plot(x, ratio, "-o", color=MEASURED, lw=1.5, ms=4.5, mec="white", mew=0.8,
             zorder=2)
    ax2.set_xscale("log")
    ax2.set_xlim(ax.get_xlim())
    lo, hi = min(ratio.min(), 0.8), max(ratio.max(), 1.2)
    ax2.set_ylim(lo - 0.05, hi + 0.05)
    ax2.set_ylabel(r"T / (c$\cdot$B$\cdot$W)", fontsize=7)
    ax2.set_xlabel("legal breakpoints B (the 10 test cases)", fontsize=7.5)
    style_axes(ax2)
    ax2.text(0.98, 0.08, "shaded band = ±10%", transform=ax2.transAxes,
             ha="right", va="bottom", fontsize=6.5, color=INK2)

    wrows = read_csv(os.path.join(HERE, "knuth_plass", "width.csv"))
    wx = np.array([float(r["W"]) for r in wrows])
    wt = np.array([float(r["seconds"]) for r in wrows])
    wt0 = np.array([float(r["seconds_gamma0"]) for r in wrows])
    wb = float(wrows[0]["B"])
    long_lines = wx >= LONG_W
    wc = math.exp(np.mean(np.log(wt[long_lines]) - np.log(wb * wx[long_lines])))
    wslope = np.polyfit(np.log(wx[long_lines]), np.log(wt[long_lines]), 1)[0]
    wslope_all = np.polyfit(np.log(wx), np.log(wt), 1)[0]
    wslope0 = np.polyfit(np.log(wx), np.log(wt0), 1)[0]

    wxx = np.geomspace(wx[0] / 1.15, wx[-1] * 1.15, 50)
    ax3.plot(wxx, wc * wb * wxx, color=THEORY, lw=2, zorder=1, label=r"$c\cdot B\cdot W$")
    ax3.plot(wx, wt, "-o", color=MEASURED, lw=1.5, ms=5.5, mec="white", mew=1, zorder=3,
             label=r"measured, $\gamma$ = 3000")
    ax3.plot(wx, wt0, "-s", color=OTHER, lw=1.5, ms=5, mec="white", mew=1, zorder=2,
             label=r"measured, $\gamma$ = 0 (no classes)")
    ax3.set_xscale("log")
    ax3.set_yscale("log")
    ax3.xaxis.set_major_locator(FixedLocator([12.5, 25, 50, 100, 200, 400]))
    ax3.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax3.xaxis.set_minor_locator(NullLocator())
    ax3.yaxis.set_major_formatter(FuncFormatter(seconds_fmt))
    ax3.set_ylim(wt0.min() / 4, wt.max() * 7)  # room for the legend and note
    ax3.set_ylabel("runtime", fontsize=7.5)
    ax3.set_xlabel(f"words per line W (case 5, B = {wb:,.0f})", fontsize=7.5)
    style_axes(ax3)
    ax3.legend(loc="upper left", fontsize=6.8, frameon=False, labelcolor=INK)
    ax3.set_title("Runtime vs. line width", loc="left", fontsize=8.5, color=INK,
                  fontweight="bold")
    ax3.text(0.98, 0.04, f"slope, W ≥ {LONG_W}: {wslope:.3f}\nslope, all: {wslope_all:.3f}\n"
             rf"slope, $\gamma$ = 0: {wslope0:.3f}", transform=ax3.transAxes, ha="right",
             va="bottom", fontsize=6.8, color=INK2, linespacing=1.4)

    fig.get_layout_engine().set(h_pad=0.03, hspace=0.04)
    fig.canvas.draw()
    fig.set_layout_engine("none")  # freeze the layout so the label angles stay right
    label_ref_lines(ax, ref_lines, x, t)
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(os.path.join(FIG_DIR, f"knuth_plass.{ext}"), dpi=200, facecolor="white")
    plt.close(fig)

    startup = [float(r["active"]) for r in read_csv(os.path.join(HERE, "knuth_plass", "startup.csv"))]
    active = [float(r["active"]) for r in wrows]
    active0 = [float(r["active_gamma0"]) for r in wrows]
    per_b = (t / x * 1e6).tolist()
    out = {"c": c, "slope_top5": slope, "slope_all": slope_all, "f_slope_top5": f_slope,
           "ratio": [float(r) for r in ratio], "x": x.tolist(), "t": t.tolist(),
           "W": w_fixed, "us_per_B": per_b,
           "doubling_ratio": (t[1:] / t[:-1]).tolist(),
           "active_per_B": [float(r["active"]) for r in rows],
           "width": {"W": wx.tolist(), "t": wt.tolist(), "t_gamma0": wt0.tolist(),
                     "slope_long": wslope, "slope_all": wslope_all, "slope_gamma0": wslope0,
                     "active_over_W": [a / w for a, w in zip(active, wx)],
                     "active_over_W_gamma0": [a / w for a, w in zip(active0, wx)]},
           "startup_first_250": startup[0],
           "startup_after": float(np.mean(startup[1:]))}
    with open(os.path.join(FIG_DIR, "fits.json"), "w") as fh:
        json.dump({"knuth_plass": out}, fh, indent=1)

    print(f"knuth_plass: c = {c:.3e}, slope (5 largest) = {slope:.3f}, "
          f"slope (all) = {slope_all:.3f}, T/(c f) = "
          + " ".join(f"{r:.2f}" for r in ratio))
    print(f"width: slope (W >= {LONG_W}) = {wslope:.3f}, slope (all) = {wslope_all:.3f}, "
          f"slope (gamma = 0) = {wslope0:.3f}")

if __name__ == "__main__":
    main()
