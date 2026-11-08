# prints the worked example in the write-up: every candidate for every DP entry,
# the minimum and its predecessor, and the traceback to the final line breaks.
# usage: python worked_example.py
#
# this applies the recurrence exactly as written, over every legal predecessor a
# and every class c', instead of using the active list. It checks that it agrees
# with break_paragraph and with a search over every possible set of breaks.

from knuth_plass import (GLUE, INF_PENALTY, PENALTY, SPACE, FINISH_STRETCH,
                         Paragraph, break_paragraph, line_extent, ratio, render_lines,
                         text_width)
from test_knuth_plass import exhaustive

TEXT = "when she was bored she took a golden ball, and threw it up on"
WIDTH, RHO, ALPHA, GAMMA = 236, 1, 3000, 3000
CLASS_NAMES = ["tight", "normal", "loose", "very loose"]

def fitness(r):
    return 0 if r < -0.5 else 1 if r <= 0.5 else 2 if r <= 1 else 3

def line_demerits(par, b, r):
    badness = 100 * abs(r) ** 3
    p = par.p[b] if par.t[b] == PENALTY else 0
    if p >= 0:
        return (1 + badness + p) ** 2
    if p > -INF_PENALTY:
        return (1 + badness) ** 2 - p ** 2
    return (1 + badness) ** 2  # forced break, no penalty charged

def main():
    words = TEXT.split()
    par = Paragraph()
    for i, word in enumerate(words):
        if i:
            par.glue(*SPACE)
        par.box(text_width(word), word)
    par.glue(0, FINISH_STRETCH, 0)
    par.penalty(0, -INF_PENALTY, 1)

    # name each break by the word before it. The finishing glue is legal by the
    # paper's definition, but a break there leaves an empty last line, so skip it
    name = {0: "start"}
    count = 0
    for i in range(1, par.m):
        if par.t[i] == GLUE and count < len(words) - 1:
            name[i] = words[count]
            count += 1
    name[par.m] = words[-1] + " (end)"
    breaks = [b for b in par.legal_breakpoints() if b in name]

    print(f"text: {TEXT}")
    print(f"width {WIDTH}, spaces (6, 3, 2), rho = {RHO}, alpha = {ALPHA}, gamma = {GAMMA}")
    print("word widths: " + ", ".join(f"{w} {text_width(w)}" for w in words))
    print(f"{2 ** (len(breaks) - 1)} ways to choose breaks\n")

    no_line = []
    D = {(0, 1): 0.0}
    P = {(0, 1): None}
    for b in breaks:
        # every state (a, c') already in the table with a before b is a legal
        # predecessor. Each one either gives a candidate for some D[b, c] or its
        # line doesn't fit
        checks = []
        cands = {}
        for (a, c1), da in sorted(D.items()):
            if a >= b:
                continue
            L, Y, Z = line_extent(par, a, b)
            r = ratio(L, Y, Z, WIDTH)
            if not -1 <= r <= RHO:
                checks.append(f"  from ({name[a]}, {c1}): r = {r:+.3f}, "
                              f"{'too long' if r < -1 else 'too loose'}, no candidate")
                continue
            c = fitness(r)
            d = line_demerits(par, b, r)
            a_term = ALPHA * par.f[a] * par.f[b]
            g_term = GAMMA if abs(c - c1) > 1 else 0
            total = da + d + a_term + g_term
            line = render_lines(par, [a, b])[-1]
            cands.setdefault(c, []).append((total, a, c1))
            checks.append(f"  from ({name[a]}, {c1}): line '{line}', L = {L:g}, r = {r:+.3f}, class {c}, "
                          f"D[{name[a]}, {c1}] {da:.2f} + demerits {d:.2f} + alpha {a_term} + gamma {g_term} "
                          f"= {total:.2f} for D[{name[b]}, {c}]")
        if not cands:
            no_line.append(name[b])
            continue
        print(f"break after '{name[b]}':")
        print("\n".join(checks))
        for c, rows in sorted(cands.items()):
            best = min(rows)
            D[(b, c)] = best[0]
            P[(b, c)] = (best[1], best[2])
            print(f"  => D[{name[b]}, {c}] ({CLASS_NAMES[c]}) = {best[0]:.2f}, "
                  f"predecessor ({name[best[1]]}, {best[2]})"
                  + (f", min of {len(rows)} candidates" if len(rows) > 1 else ""))
        print()

    print(f"no line ending after these fits, so D = infinity for every c: {', '.join(no_line)}")
    final = min((D[k], k) for k in D if k[0] == par.m)
    print(f"\nanswer: min over c of D[{name[par.m]}, c] = {final[0]:.2f}, at c = {final[1][1]}")
    path = []
    k = final[1]
    while k is not None:
        path.append(k)
        k = P[k]
    path.reverse()
    print("traceback: " + "  <-  ".join(f"({name[b]}, {c})" for b, c in reversed(path)))
    chosen = [b for b, _ in path[1:]]
    for line in render_lines(par, chosen):
        print("  | " + line)

    res = break_paragraph(par, [WIDTH], RHO, ALPHA, GAMMA)
    brute = exhaustive(par, [WIDTH], RHO, ALPHA, GAMMA)
    assert res.breaks == chosen and abs(res.demerits - final[0]) < 1e-9
    assert abs(min(brute.values()) - final[0]) < 1e-9
    print("\nmatches break_paragraph and the exhaustive search")

if __name__ == "__main__":
    main()
