# Knuth-Plass optimum-fit line breaking
# Knuth & Plass, "Breaking Paragraphs into Lines", Software: Practice and
# Experience 11 (1981). Translated from the pseudocode on pp. 1156-1161.
# names follow the paper: b = breakpoint, a = active node, r = adjustment ratio,
# rho = tolerance, alpha/gamma = extra demerits, q = looseness
#
# each active node is a DP table entry: the fewest total demerits of any way to
# break at position b so the line ending there has fitness class c (and line
# number, when line numbers matter)

from collections import namedtuple

BOX, GLUE, PENALTY = 0, 1, 2
INF = float("inf")
INF_PENALTY = 1000  # penalties past +-1000 count as infinite, same as TeX

# widths in 1/18 em. The paper prints I n o l i m e t h g - . and word widths
# that imply r = 7. It doesn't print the rest or its kerning, so those are my
# estimates, picked to fit the ratios in its figures.
CHAR_WIDTHS = {
    "a": 9, "b": 10, "c": 8, "d": 10, "e": 8, "f": 6, "g": 9, "h": 10, "i": 5,
    "j": 6, "k": 10, "l": 5, "m": 15, "n": 10, "o": 9, "p": 10, "q": 10, "r": 7,
    "s": 7, "t": 7, "u": 10, "v": 9.5, "w": 13, "x": 10, "y": 9, "z": 8,
    "I": 6, "C": 14, ",": 5, ";": 5, ".": 5, "'": 5, "-": 6,
}
INDENT = 18
SPACE = (6, 3, 2)
HYPHEN_WIDTH = 6
HYPHEN_PENALTY = 50
FINISH_STRETCH = 100000

# the paper's example, Figure 1. "|" marks a place a word may be hyphenated
FROG_KING = (
    "In olden times when wish|ing still helped one, there lived a king whose "
    "daugh|ters were all beau|ti|ful; and the young|est was so beau|ti|ful that "
    "the sun it|self, which has seen so much, was aston|ished when|ever it shone "
    "in her face. Close by the king's castle lay a great dark for|est, and "
    "un|der an old lime-tree in the for|est was a well, and when the day was "
    "very warm, the king's child went out into the for|est and sat down by the "
    "side of the cool foun|tain; and when she was bored she took a golden ball, "
    "and threw it up on high and caught it; and this ball was her favor|ite "
    "play|thing."
)

Result = namedtuple("Result", "breaks demerits line_demerits legal examined max_active nodes")

class Paragraph:
    # the paper's six sequences t, w, y, z, p, f, indexed 1..m

    def __init__(self):
        self.t, self.w, self.y, self.z = [PENALTY], [0], [0], [0]
        self.p, self.f, self.text = [0], [0], [""]

    def add(self, t, w=0, y=0, z=0, p=0, f=0, text=""):
        self.t.append(t)
        self.w.append(w)
        self.y.append(y)
        self.z.append(z)
        self.p.append(p)
        self.f.append(f)
        self.text.append(text)

    def box(self, width, text=""):
        self.add(BOX, w=width, text=text)

    def glue(self, width, stretch, shrink):
        self.add(GLUE, w=width, y=stretch, z=shrink)

    def penalty(self, width, penalty, flagged=0):
        self.add(PENALTY, w=width, p=penalty, f=flagged)

    @property
    def m(self):
        return len(self.t) - 1

    def legal_breakpoints(self):
        return [b for b in range(1, self.m + 1)
                if (self.t[b] == PENALTY and self.p[b] < INF_PENALTY)
                or (self.t[b] == GLUE and self.t[b - 1] == BOX)]

def text_width(s):
    return sum(CHAR_WIDTHS.get(ch, 10) for ch in s)

def text_to_paragraph(text, per_char=False):
    # the five rules on p. 1123. per_char gives every letter its own box like the
    # paper's 601 item example, otherwise a box is a whole word fragment. Same
    # breakpoints and same answer either way.
    par = Paragraph()

    def add_boxes(s):
        if per_char:
            for ch in s:
                par.box(text_width(ch), ch)
        else:
            par.box(text_width(s), s)

    par.box(INDENT)
    for i, word in enumerate(text.split()):
        if i:
            par.glue(*SPACE)
        for k, piece in enumerate(word.split("|")):
            if k:
                par.penalty(HYPHEN_WIDTH, HYPHEN_PENALTY, 1)
            parts = piece.split("-")
            for n, part in enumerate(parts):
                has_hyphen = n < len(parts) - 1
                s = part + "-" if has_hyphen else part
                if s:
                    add_boxes(s)
                if has_hyphen:
                    par.penalty(0, HYPHEN_PENALTY, 1)
    par.glue(0, FINISH_STRETCH, 0)
    par.penalty(0, -INF_PENALTY, 1)
    return par

class Node:
    # p. 1158. link is the next active node, previous is the best way to get here
    __slots__ = ("position", "line", "fitness", "totalwidth", "totalstretch",
                 "totalshrink", "totaldemerits", "previous", "link")

    def __init__(self, position, line, fitness, tw, ty, tz, demerits, previous, link):
        self.position = position
        self.line = line
        self.fitness = fitness
        self.totalwidth = tw
        self.totalstretch = ty
        self.totalshrink = tz
        self.totaldemerits = demerits
        self.previous = previous
        self.link = link

def break_paragraph(par, line_lengths, rho=1.26, alpha=3000, gamma=3000, q=0,
                    overfull=False):
    # line_lengths is l1, l2, ... and the last one repeats. Returns None if
    # nothing is feasible. overfull is TeX's fallback on p. 1162, it lets the
    # last active node's line stick out instead of failing
    t, w, y, z, p, f = par.t, par.w, par.y, par.z, par.p, par.f
    m = par.m

    lengths = list(line_lengths)
    while len(lengths) > 1 and lengths[-1] == lengths[-2]:
        lengths.pop()
    n_lengths = len(lengths)
    last_length = lengths[-1]
    # lines past j0 are all the same length so nodes don't need line numbers,
    # unless looseness has to count lines (p. 1159)
    j0 = INF if q != 0 else n_lengths - 1

    active = Node(0, 0, 1, 0, 0, 0, 0, None, None)
    sum_w = sum_y = sum_z = 0
    legal = examined = max_active = nodes = 0

    for b in range(1, m + 1):
        t_b = t[b]
        if t_b == BOX:
            sum_w += w[b]
            continue
        is_legal = t[b - 1] == BOX if t_b == GLUE else p[b] < INF_PENALTY

        if is_legal:
            legal += 1
            p_b, f_b = p[b], f[b]
            forced = p_b <= -INF_PENALTY
            extra = w[b] if t_b == PENALTY else 0
            a = active
            preva = None
            seen = 0

            # outer loop: one pass per group of equivalent line numbers
            while True:
                D = [INF, INF, INF, INF]
                A = [None, None, None, None]
                D_min = INF

                # inner loop: every active node in the group
                while True:
                    nexta = a.link
                    seen += 1
                    j = a.line + 1

                    # adjustment ratio r from a to b
                    L = sum_w - a.totalwidth + extra
                    l_j = lengths[j - 1] if j <= n_lengths else last_length
                    if L < l_j:
                        Y = sum_y - a.totalstretch
                        r = (l_j - L) / Y if Y > 0 else INF
                    elif L > l_j:
                        Z = sum_z - a.totalshrink
                        r = (l_j - L) / Z if Z > 0 else INF
                    else:
                        r = 0.0

                    # too long for this line means too long for any later b too
                    if r < -1 or forced:
                        if preva is None:
                            active = nexta
                        else:
                            preva.link = nexta
                        if overfull and active is None and D_min == INF and r < -1:
                            r = -1.0
                    else:
                        preva = a

                    if -1 <= r <= rho:
                        badness = 100 * abs(r) ** 3
                        if p_b >= 0:
                            d = (1 + badness + p_b) ** 2
                        elif not forced:
                            d = (1 + badness) ** 2 - p_b * p_b
                        else:
                            d = (1 + badness) ** 2
                        d += alpha * f_b * f[a.position]
                        c = 0 if r < -0.5 else 1 if r <= 0.5 else 2 if r <= 1 else 3
                        if abs(c - a.fitness) > 1:
                            d += gamma
                        d += a.totaldemerits
                        if d < D[c]:
                            D[c] = d
                            A[c] = a
                            if d < D_min:
                                D_min = d

                    a = nexta
                    if a is None or (a.line >= j and j < j0):
                        break

                # a costlier class still has to be kept if it could beat the best
                # one after that one pays gamma for a contrasting next line
                if D_min < INF:
                    tw, ty, tz = sum_w, sum_y, sum_z
                    i = b
                    while i <= m:
                        t_i = t[i]
                        if t_i == BOX:
                            break
                        if t_i == GLUE:
                            tw += w[i]
                            ty += y[i]
                            tz += z[i]
                        elif p[i] <= -INF_PENALTY and i > b:
                            break
                        i += 1
                    limit = D_min + gamma
                    for c in range(4):
                        if D[c] <= limit:
                            s = Node(b, A[c].line + 1, c, tw, ty, tz, D[c], A[c], a)
                            nodes += 1
                            if preva is None:
                                active = s
                            else:
                                preva.link = s
                            preva = s

                if a is None:
                    break

            examined += seen
            if seen > max_active:
                max_active = seen
            if active is None:
                return None  # the paper's "do something drastic"

        if t_b == GLUE:
            sum_w += w[b]
            sum_y += y[b]
            sum_z += z[b]

    # only nodes at position m are left, x_m is a forced break
    best = active
    a = active.link
    while a is not None:
        if a.totaldemerits < best.totaldemerits:
            best = a
        a = a.link

    if q != 0:
        k = best.line
        s = 0
        a = active
        d = best.totaldemerits
        while a is not None:
            delta = a.line - k
            if q <= delta < s or s < delta <= q:
                s = delta
                d = a.totaldemerits
                best = a
            elif delta == s and a.totaldemerits < d:
                d = a.totaldemerits
                best = a
            a = a.link

    chain = []
    node = best
    while node.previous is not None:
        chain.append(node)
        node = node.previous
    chain.reverse()

    line_demerits = []
    before = 0
    for node in chain:
        line_demerits.append(node.totaldemerits - before)
        before = node.totaldemerits
    return Result([n.position for n in chain], best.totaldemerits, line_demerits,
                  legal, examined, max_active, nodes)

def line_extent(par, start, b):
    # (L, Y, Z) of the line from break start to break b, summed item by item.
    # doesn't use the running totals, so it's a fair check of break_paragraph
    a = start + 1
    while a < b and not (par.t[a] == BOX or
                         (par.t[a] == PENALTY and par.p[a] <= -INF_PENALTY)):
        a += 1
    L = Y = Z = 0
    for i in range(a, b):
        if par.t[i] == BOX:
            L += par.w[i]
        elif par.t[i] == GLUE:
            L += par.w[i]
            Y += par.y[i]
            Z += par.z[i]
    if par.t[b] == PENALTY:
        L += par.w[b]
    return L, Y, Z

def ratio(L, Y, Z, length):
    if L == length:
        return 0.0
    if L < length:
        return (length - L) / Y if Y > 0 else INF
    return (length - L) / Z if Z > 0 else -INF

def score_breaks(par, breaks, line_lengths, rho=1.26, alpha=3000, gamma=3000):
    # total demerits of a break sequence from scratch, None if a line is infeasible
    lengths = list(line_lengths)
    total = 0.0
    fitness, prev = 1, 0
    for j, b in enumerate(breaks, 1):
        length = lengths[j - 1] if j <= len(lengths) else lengths[-1]
        r = ratio(*line_extent(par, prev, b), length)
        if not -1 <= r <= rho:
            return None
        badness = 100 * abs(r) ** 3
        pen = par.p[b] if par.t[b] == PENALTY else 0
        if pen >= 0:
            d = (1 + badness + pen) ** 2
        elif pen > -INF_PENALTY:
            d = (1 + badness) ** 2 - pen ** 2
        else:
            d = (1 + badness) ** 2
        if par.f[b] and par.f[prev]:
            d += alpha
        c = 0 if r < -0.5 else 1 if r <= 0.5 else 2 if r <= 1 else 3
        if abs(c - fitness) > 1:
            d += gamma
        total += d
        fitness, prev = c, b
    return total

def render_lines(par, breaks):
    lines = []
    start = 0
    for b in breaks:
        s = []
        for i in range(start + 1, b):
            if par.t[i] == BOX:
                s.append(par.text[i])
            elif par.t[i] == GLUE and s:
                s.append(" ")
        if par.t[b] == PENALTY and par.w[b] > 0:
            s.append("-")
        lines.append("".join(s).strip())
        start = b
    return lines

if __name__ == "__main__":
    import sys
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    paragraph = text_to_paragraph(FROG_KING)
    answer = break_paragraph(paragraph, [width], rho=1, gamma=0)
    if answer is None:
        sys.exit(f"no feasible way to break this at width {width}")
    print(f"width {width}: {len(answer.breaks)} lines, "
          f"{answer.demerits:.0f} demerits")
    print("\n".join(render_lines(paragraph, answer.breaks)))
