# Knuth-Plass optimum-fit line breaking

`knuth_plass.py` is a Python translation of the algorithm in D. E. Knuth and
M. F. Plass, "Breaking Paragraphs into Lines", Software: Practice and
Experience 11(11), 1981:

* `text_to_paragraph(text)` turns text into the paper's boxes, glue and
  penalties. A `|` in a word marks a place it may be hyphenated.
* `break_paragraph(par, line_lengths)` is the main algorithm. It returns the
  breakpoints with the fewest total demerits, or `None` if nothing is feasible.
  It also handles varying line lengths, the paper's looseness parameter (`q`)
  and TeX's overfull fallback (`overfull=True`).
* `score_breaks(par, breaks, line_lengths)` scores a break sequence from
  scratch. It is only used by the tests.
* `render_lines(par, breaks)` returns the text of each line.

The paper gives the running time as O(B·W), where B is the number of legal
breakpoints and W is the maximum number of words per line.

To see it set the paper's example paragraph (the width is optional):

```
python knuth_plass.py 500
```

## Run the 10 test cases

```
python run_tests.py              # all 10, about 50 s
python run_tests.py --quick      # skip the 2 largest
python run_tests.py --width      # also run case 5 at wider columns, and with
                                 # fitness classes off, to test the W factor
                                 # (about 3 min in total)
```

An answer passes if its total demerits equal the expected value in the file and
rescoring its breaks from scratch gives the same total with every line feasible.
Ties are possible, so the breaks themselves aren't compared. Timings go to
`results.csv`. When `--width` is used, the line-width results go to `width.csv`
and active nodes by position in the paragraph go to `startup.csv`.

## Worked example

```
python worked_example.py
```

This prints the worked example in the write-up. It applies the recurrence
directly, trying every legal predecessor break and every fitness class, and
shows every candidate for each DP entry, the minimum and its predecessor, and
the traceback to the final line breaks. It then checks that the answer matches
`break_paragraph` and a search over every possible set of breaks.

## Test cases

`tests/caseNN.txt` holds one paragraph of 2^(NN+10) words, so 2,048 for case 1
up to 1,048,576 for case 10. The words are sampled at random from the paper's
Grimm paragraph, which keeps the word lengths, punctuation and hyphenation
points realistic. All cases use a 500-unit column and the paper's production
settings. Each file has these lines:

```
width <column width>
rho <tolerance>
alpha <flagged demerits>
gamma <fitness demerits>
expected_demerits <value>
text <the paragraph>
```

The expected value comes from `oracle_demerits` in `generate_tests.py`, a DP
that runs backward from the end of the paragraph on its own model of the text.
It shares only the letter widths with the code being tested. To regenerate the
files:

```
python generate_tests.py
```

## Unit tests

```
python -m unittest -v test_knuth_plass
```

These cover the paper's published ratios and demerits, the items it lists for
its example, the 21 line breaks in its Figures 3 and 4(c), hand-computed
demerits for stretching, shrinking, penalties and flagged and contrasting lines,
infeasible input, a paragraph where only the fitness classes give the optimum,
and thousands of random paragraphs against an exhaustive search of every feasible
break sequence, including varying line lengths and looseness. They also check the
backward oracle itself.
