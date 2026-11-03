# extra correctness tests, run with: python -m unittest -v test_knuth_plass

import random
import unittest
from generate_tests import oracle_demerits
from knuth_plass import (BOX, FINISH_STRETCH, FROG_KING, GLUE, INF_PENALTY, PENALTY,
                         Paragraph, break_paragraph, line_extent, ratio, render_lines,
                         score_breaks, text_to_paragraph)

# published optimum-fit results: last word on each line (Figures 3 and 4c), the
# demerits table on p. 1129, and the ratios printed beside Figures 3 and 12
PUBLISHED = {
    421: {
        "last_words": ["there", "and", "which", "shone", "dark", "was", "king's",
                       "side", "took", "it;", "plaything."],
        "demerits": [1, 64, 4803, 96, 33, 1274, 43, 581, 166, 1, 1],
        "ratios": [.121, .412, -.881, .444, -.363, .703, .381, -.614, -.491, .104, .001],
        "total": 7063,
    },
    500: {
        "last_words": ["a", "was", "was", "king's", "the", "king's", "the", "ball,",
                       "her", "plaything."],
        "demerits": [2357, 6, 938, 212, 1, 2, 27, 10, 476, 1],
        "ratios": [.780, .246, .667, .514, .027, .173, .346, .275, .593, .002],
        "total": 4030,
    },
}

def paragraph(*items):
    par = Paragraph()
    for kind, *values in items:
        getattr(par, kind)(*values)
    return par

def text_paragraph(boxes):
    par = Paragraph()
    for i, width in enumerate(boxes):
        if i:
            par.glue(6, 3, 2)
        par.box(width)
    par.glue(0, FINISH_STRETCH, 0)
    par.penalty(0, -INF_PENALTY, 1)
    return par

def mixed_paragraph(rng):
    # every feature at once: penalties, flagged breaks, forced breaks
    par = Paragraph()
    par.box(rng.randint(0, 20))
    for i in range(rng.randint(8, 20)):
        if i:
            par.glue(6, rng.choice([2, 3, 4]), rng.choice([1, 2]))
        for k in range(rng.choice([1, 1, 2])):
            if k:
                par.penalty(rng.choice([0, 6]), rng.choice([50, 0, -50]), rng.choice([0, 1]))
            par.box(rng.randint(10, 45))
        if rng.random() < 0.06:
            par.penalty(0, -INF_PENALTY, 0)
            par.box(rng.randint(10, 40))
    par.glue(0, FINISH_STRETCH, 0)
    par.penalty(0, -INF_PENALTY, 1)
    return par

def exhaustive(par, lengths, rho, alpha, gamma):
    # tries every feasible break sequence, returns {line count: fewest demerits}
    legal = par.legal_breakpoints()
    forced = {b for b in legal if par.t[b] == PENALTY and par.p[b] <= -INF_PENALTY}
    best = {}

    def extend(start, breaks):
        for b in legal:
            if b <= start:
                continue
            j = len(breaks) + 1
            length = lengths[j - 1] if j <= len(lengths) else lengths[-1]
            if -1 <= ratio(*line_extent(par, start, b), length) <= rho:
                seq = breaks + [b]
                if b == par.m:
                    score = score_breaks(par, seq, lengths, rho, alpha, gamma)
                    if score is not None and (len(seq) not in best or score < best[len(seq)]):
                        best[len(seq)] = score
                else:
                    extend(b, seq)
            if b in forced:
                return  # no line can run past a forced break

    extend(0, [])
    return best

def last_words(par, breaks):
    words = FROG_KING.replace("|", "").split()
    at_glue = {}
    count = 0
    for i in range(1, par.m + 1):
        if par.t[i] == GLUE:
            if count < len(words):
                at_glue[i] = words[count]
            count += 1
    at_glue[par.m] = words[-1]
    return [at_glue.get(b, "<hyphen>") for b in breaks]

class KnuthPlassTests(unittest.TestCase):

    def demerits(self, par, width, rho=10, alpha=0, gamma=0):
        return break_paragraph(par, [width], rho, alpha, gamma).demerits

    def test_published_ratios_give_published_demerits(self):
        for width, data in PUBLISHED.items():
            self.assertEqual(sum(data["demerits"]), data["total"])
            for r, d in zip(data["ratios"], data["demerits"]):
                # ratios are printed to 3 digits so allow for rounding
                self.assertLessEqual(abs((1 + 100 * abs(r) ** 3) ** 2 - d), max(1.5, 0.015 * d))

    def test_items_match_the_paper(self):
        par = text_to_paragraph(FROG_KING, per_char=True)
        self.assertEqual(par.w[1:4], [18, 6, 10])
        self.assertEqual((par.w[4], par.y[4], par.z[4]), (6, 3, 2))
        self.assertEqual((par.t[313], par.w[313]), (BOX, 6))
        self.assertEqual((par.t[314], par.w[314], par.p[314], par.f[314]), (PENALTY, 0, 50, 1))

    def test_figure_breaks(self):
        par = text_to_paragraph(FROG_KING)
        for width, data in PUBLISHED.items():
            res = break_paragraph(par, [width], rho=1, alpha=3000, gamma=0)
            self.assertEqual(last_words(par, res.breaks), data["last_words"], width)

    def test_stretch_and_shrink(self):
        par = paragraph(("box", 100), ("glue", 10, 10, 5), ("box", 100),
                        ("penalty", 0, -INF_PENALTY, 0))
        # L = 210, stretch 5 of 10 is r = 0.5, so (1 + 100 * 0.125)^2 = 182.25
        self.assertEqual(self.demerits(par, 215), 182.25)
        # shrink 2.5 of 5 is r = -0.5
        self.assertEqual(self.demerits(par, 207.5), 182.25)
        self.assertEqual(self.demerits(par, 210), 1)

    def test_penalties(self):
        def two_lines(pen, flagged, end_flagged=0):
            return paragraph(("box", 100), ("penalty", 6, pen, flagged), ("box", 106),
                             ("penalty", 0, -INF_PENALTY, end_flagged))
        self.assertEqual(self.demerits(two_lines(50, 0), 106), 51 ** 2 + 1)
        self.assertEqual(self.demerits(two_lines(-50, 0), 106), 1 - 50 ** 2 + 1)
        self.assertEqual(self.demerits(two_lines(0, 1, 1), 106, alpha=3000), 1 + 1 + 3000)

    def test_contrasting_lines_cost_gamma(self):
        # a tight line (r = -0.8) forced next to a loose one (r = 0.8)
        par = paragraph(("box", 100), ("glue", 10, 10, 10), ("box", 98),
                        ("penalty", 0, -INF_PENALTY, 0), ("box", 100), ("glue", 10, 10, 10),
                        ("box", 82), ("penalty", 0, -INF_PENALTY, 0))
        res = break_paragraph(par, [200], 10, 0, 500)
        self.assertAlmostEqual(res.demerits, 2 * (1 + 100 * 0.8 ** 3) ** 2 + 500)

    def test_no_feasible_solution(self):
        # the first two words can't fit on one line, or be split up
        par = text_paragraph([150, 150, 30, 30])
        self.assertIsNone(break_paragraph(par, [100], rho=1))
        res = break_paragraph(par, [100], rho=1, overfull=True)
        self.assertEqual(len(res.breaks), 2)

    def test_render_lines(self):
        par = text_to_paragraph("aaaa bbb|bb cccc")
        res = break_paragraph(par, [100], rho=10, alpha=0, gamma=0)
        self.assertEqual(render_lines(par, res.breaks), ["aaaa bbb-", "bb cccc"])

    def test_legal_breakpoint_count(self):
        # the paper counts 129, not counting x_m. the finishing glue is also legal
        # by its definition but can't be used, since it would leave an empty line
        par = text_to_paragraph(FROG_KING, per_char=True)
        self.assertEqual(len(par.legal_breakpoints()) - 2, 129)

    def test_fitness_classes_are_needed(self):
        # out of 148000 random paragraphs, keeping only the cheapest class at each
        # break gave a worse answer on 40. this is one. the optimum goes through a
        # costlier break because the cheaper one forces a contrasting next line
        par = text_paragraph([15, 8, 7, 19, 16, 6, 16, 20, 8, 5, 15, 11, 22, 21, 16, 18, 19])
        res = break_paragraph(par, [94], 2, 0, 1000)
        self.assertAlmostEqual(res.demerits, min(exhaustive(par, [94], 2, 0, 1000).values()))
        self.assertEqual(res.breaks, [12, 22, 30, 35])

    def test_random_against_exhaustive(self):
        rng = random.Random(1)
        solved = 0
        for _ in range(2000):
            par = mixed_paragraph(rng)
            lengths = [rng.randint(140, 320) for _ in range(rng.choice([1, 1, 3]))]
            rho = rng.choice([1.26, 2, 4, 10])
            alpha, gamma = rng.choice([0, 100, 3000]), rng.choice([0, 100, 3000])
            best = exhaustive(par, lengths, rho, alpha, gamma)
            res = break_paragraph(par, lengths, rho, alpha, gamma)
            if not best:
                self.assertIsNone(res)
                continue
            solved += 1
            self.assertAlmostEqual(res.demerits, min(best.values()))
            self.assertAlmostEqual(score_breaks(par, res.breaks, lengths, rho, alpha, gamma),
                                   res.demerits)
        self.assertGreater(solved, 500)

    def test_short_words_against_exhaustive(self):
        # short words give lots of breaks with different fitness classes
        rng = random.Random(2)
        for _ in range(2000):
            par = text_paragraph([rng.randint(4, 22) for _ in range(rng.randint(12, 20))])
            width, rho = rng.randint(80, 150), rng.choice([1, 1.26, 2, 3])
            gamma = rng.choice([100, 500, 1000, 3000])
            best = exhaustive(par, [width], rho, 0, gamma)
            res = break_paragraph(par, [width], rho, 0, gamma)
            if best:
                self.assertAlmostEqual(res.demerits, min(best.values()))
            else:
                self.assertIsNone(res)

    def test_looseness_against_exhaustive(self):
        # q moves toward 0 until the line count is feasible (p. 1156)
        rng = random.Random(3)
        checked = 0
        for _ in range(1500):
            par = mixed_paragraph(rng)
            lengths = [rng.randint(140, 320) for _ in range(rng.choice([1, 1, 3]))]
            rho, gamma = rng.choice([1.26, 2, 4, 10]), rng.choice([0, 100, 3000])
            q = rng.choice([-1, 1, 2])
            best = exhaustive(par, lengths, rho, 0, gamma)
            if not best:
                continue
            k = len(break_paragraph(par, lengths, rho, 0, gamma).breaks)
            target = k + q
            while target not in best and target != k:
                target += -1 if q > 0 else 1
            res = break_paragraph(par, lengths, rho, 0, gamma, q=q)
            self.assertEqual(len(res.breaks), target)
            self.assertAlmostEqual(res.demerits, best[target])
            checked += 1
        self.assertGreater(checked, 300)

    def test_backward_oracle(self):
        rng = random.Random(4)
        vocabulary = FROG_KING.split()
        solved = 0
        for _ in range(1000):
            text = " ".join(rng.choices(vocabulary, k=rng.randint(1, 150)))
            width = rng.randint(150, 900)
            rho, alpha, gamma = rng.choice([1, 1.26, 2, 4]), rng.choice([0, 3000]), rng.choice([0, 100, 3000])
            res = break_paragraph(text_to_paragraph(text), [width], rho, alpha, gamma)
            expected = oracle_demerits(text, width, rho, alpha, gamma)
            if res is None:
                self.assertIsNone(expected)
            else:
                solved += 1
                self.assertAlmostEqual(res.demerits, expected, places=6)
        self.assertGreater(solved, 300)

    def test_backward_oracle_against_exhaustive(self):
        rng = random.Random(5)
        vocabulary = FROG_KING.split()
        for _ in range(200):
            text = " ".join(rng.choices(vocabulary, k=rng.randint(4, 14)))
            width = rng.randint(120, 300)
            best = exhaustive(text_to_paragraph(text), [width], 2, 3000, 100)
            expected = oracle_demerits(text, width, 2, 3000, 100)
            if best:
                self.assertAlmostEqual(expected, min(best.values()), places=6)
            else:
                self.assertIsNone(expected)

if __name__ == "__main__":
    unittest.main()
