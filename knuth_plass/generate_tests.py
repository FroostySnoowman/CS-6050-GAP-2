# makes tests/case01.txt .. case10.txt
# one paragraph per case, word count doubles each case. words are sampled from
# the paper's Grimm paragraph so lengths and hyphenation points stay realistic.
# expected demerits come from oracle_demerits: a DP that runs backward from the
# end of the paragraph on its own model of the text, sharing only the letter widths

import os
import random
from knuth_plass import CHAR_WIDTHS, FROG_KING

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tests")

WORDS = [2 ** k for k in range(11, 21)]
WIDTH = 500  # the paper's Figure 4 column
RHO = 1.26   # the paper's production settings, pp. 1162-1163
ALPHA = 3000
GAMMA = 3000

def parse_breaks(text):
    # running totals at the end of a line that breaks at each break (end_*), and
    # at the start of the line after it (start_*), plus each break's penalty info
    def width(s):
        return sum(CHAR_WIDTHS.get(ch, 10) for ch in s)

    w, y, z = 18.0, 0, 0
    end_w, end_y, end_z = [0], [0], [0]
    start_w, start_y, start_z = [0], [0], [0]
    extra, pen, flag = [0], [0], [0]

    def add_break(x, p, fl, gw=0, gy=0, gz=0):
        end_w.append(w)
        end_y.append(y)
        end_z.append(z)
        start_w.append(w + gw)
        start_y.append(y + gy)
        start_z.append(z + gz)
        extra.append(x)
        pen.append(p)
        flag.append(fl)

    for i, word in enumerate(text.split()):
        if i:
            add_break(0, 0, 0, 6, 3, 2)
            w, y, z = w + 6, y + 3, z + 2
        for k, piece in enumerate(word.split("|")):
            if k:
                add_break(6, 50, 1)
            parts = piece.split("-")
            for n, part in enumerate(parts):
                if n < len(parts) - 1:
                    w += width(part + "-")
                    add_break(0, 50, 1)
                else:
                    w += width(part)

    # last line: the finishing glue, then a forced break with no penalty charged
    y += 100000
    add_break(0, 0, 1)
    return end_w, end_y, end_z, start_w, start_y, start_z, extra, pen, flag

def oracle_demerits(text, width, rho=RHO, alpha=ALPHA, gamma=GAMMA):
    # finish[a][p] = fewest demerits from break a to the end of the paragraph, if
    # the line ending at a has fitness class p. None if nothing is feasible
    end_w, end_y, end_z, start_w, start_y, start_z, extra, pen, flag = parse_breaks(text)
    n = len(end_w) - 1
    inf = float("inf")
    finish = [None] * (n + 1)
    finish[n] = [0, 0, 0, 0]
    for a in range(n - 1, -1, -1):
        by_class = [inf, inf, inf, inf]
        sw, sy, sz, fa = start_w[a], start_y[a], start_z[a], flag[a]
        for b in range(a + 1, n + 1):
            length = end_w[b] - sw + extra[b]
            shrink = end_z[b] - sz
            if length - shrink > width:
                break  # stays too long for every later b as well
            if length < width:
                stretch = end_y[b] - sy
                if stretch <= 0:
                    continue
                r = (width - length) / stretch
                if r > rho:
                    continue
            elif length > width:
                r = (width - length) / shrink
            else:
                r = 0.0
            d = (1 + 100 * abs(r) ** 3 + pen[b]) ** 2 + alpha * fa * flag[b]
            c = 0 if r < -0.5 else 1 if r <= 0.5 else 2 if r <= 1 else 3
            total = d + finish[b][c]
            if total < by_class[c]:
                by_class[c] = total
        finish[a] = [min(by_class[c] + (gamma if abs(c - p) > 1 else 0) for c in range(4))
                     for p in range(4)]
    return None if finish[0][1] == inf else finish[0][1]

def main():
    os.makedirs(OUT, exist_ok=True)
    vocabulary = FROG_KING.split()
    for i, words in enumerate(WORDS, start=1):
        rng = random.Random(4000 + i)
        text = " ".join(rng.choices(vocabulary, k=words))
        expected = oracle_demerits(text, WIDTH)
        assert expected is not None, f"case {i} has no feasible solution"
        path = os.path.join(OUT, f"case{i:02d}.txt")
        with open(path, "w") as f:
            f.write(f"# knuth-plass case {i}: {words} words sampled from the "
                    f"Grimm paragraph, seed {4000 + i}\n")
            f.write(f"width {WIDTH}\n")
            f.write(f"rho {RHO}\n")
            f.write(f"alpha {ALPHA}\n")
            f.write(f"gamma {GAMMA}\n")
            f.write(f"expected_demerits {expected!r}\n")
            f.write(f"text {text}\n")
        print(f"wrote {os.path.relpath(path, HERE)}  ({words} words, "
              f"demerits = {expected:.1f})")

if __name__ == "__main__":
    main()
