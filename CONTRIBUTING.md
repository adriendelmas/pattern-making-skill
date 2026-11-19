# Contributing

This skill is only as good as the pattern-making knowledge in it, and most of that knowledge has not been checked
against real patterns yet ([COVERAGE.md](COVERAGE.md) says exactly how much). If you draft patterns, you know things
this project does not. You do not need to write code to add them.

**The simplest way: let the skill do it with you.** Install it in your agent, lay your pattern on the table and
say "add this pattern to the library". The skill runs its intake protocol
([pattern-intake.md](skills/pattern-making/references/pattern-intake.md)): it digitises each piece, names the
points, measures every dimension itself, tells you what is missing, and writes the file. The same steps can be done
by hand; they are below.

Either way, one command says whether the result is sound:

```
python skills/pattern-making/scripts/pattern.py check
```

It needs Python 3.9 or newer and nothing else. No `!!` line means your pull request will pass.

## Pick what you have

| You have | You do | Time |
|---|---|---|
| A value you know is wrong | [Correct it](#correct-a-value) | 5 minutes |
| A real pattern to compare with an entry | [Verify a knowledge-base entry](#verify-a-knowledge-base-entry) | 20 minutes |
| A size chart: a method, a brand, a country | [Add a measurement table](#add-a-measurement-table) | 20 minutes |
| The proportions of a collar, a hood, a fit | [Add a construction preset](#add-a-construction-preset) | 15 minutes |
| A real pattern, one piece or all of them | [Add a pattern](#add-a-pattern) | 30 minutes a piece |
| CLO3D and an avatar | [List its arrangement points](#list-an-avatars-arrangement-points) | 15 minutes |
| No time for any of that | [Open an issue](../../issues/new/choose): "this is wrong, it should be X" is already useful | 2 minutes |

## The two rules

**Share only what you may share.** Your own patterns and measurements, public-domain material, or values cited
from a book with the book named. Every data file says where it comes from in its `provenance` block, and
[CREDITS.md](CREDITS.md) is built from that. Contributions are published under the MIT licence of the repository.

**Data only, never the material.** The repository holds the numbers and the points taken from a pattern, and
never the pattern itself: no photo, no scan, no tracing, no PDF, not even your own. The picture you digitise from
stays on your machine. The pictures you see in the repository are drawn by the skill from the data, automatically,
when a contribution is merged; a pull request that adds an image or edits a generated file is refused by the check.

Nothing from your studio needs to leave it. A table of numbers and an outline carry no garment, no brand and no
client.

How data is taken, the same way for everyone, is written in
[EXTRACTION.md](skills/pattern-making/data/EXTRACTION.md).

## How sure are you: four words

Every entry and every data file says how far it can be trusted, with one of these:

| Level | Meaning |
|---|---|
| `measured` | taken from a real pattern or garment by the contributor |
| `published` | from a cited book, standard or published pattern |
| `practice` | common trade values, consistent with the technique sheets, not traced to one source |
| `unverified` | a description or a guess nobody has checked against a real pattern or a toile |

Be honest rather than generous. `practice` from someone who drafts for a living is worth more than a doubtful
`published`.

## Correct a value

1. Find it: `python skills/pattern-making/scripts/pattern.py kb search <words>` for the knowledge base, or
   `... data list` for the tables. Knowledge-base entries are one file each in
   `skills/pattern-making/references/kb/<family>/<id>.md`.
2. Change the value. Say in the `Confidence` line (entries) or in `provenance.notes` (data) what you changed and how
   you know.
3. Run `check`.

## Verify a knowledge-base entry

[COVERAGE.md](COVERAGE.md) lists every entry still marked `unverified`, by family. Pick one you know.

1. Open its file and compare the `Shape`, `Drafting` and `Sewing order` fields with a real pattern.
2. Correct what is wrong, in your own words. Where the entry describes a shape in words, give the proportions and
   the named points you read on the pattern; better still, [add the pattern](#add-a-pattern) and name it in the
   entry.
3. Change the last line to `- **Status**: measured` (your own pattern) or `published` (a cited one), and name the
   source in the `Confidence` line. Add the source to `SOURCES.md` in the same folder if it is not there.
4. Run `check`.

To add an entry that does not exist, copy the template of
[FORMAT.md](skills/pattern-making/references/kb/FORMAT.md) into `<family>/<id>.md`.

## Add a measurement table

1. Copy `skills/pattern-making/data/measurements/standard-eu.json` to a new name, for example
   `aldrich-women.json`.
2. Type the numbers; a size chart with one row per size is the simplest form
   ([data/README.md](skills/pattern-making/data/README.md) shows both forms). Keep only the bodies you have.
   Where the source measures differently from the skill, convert and say how
   ([method](skills/pattern-making/data/EXTRACTION.md#a-measurement-table-datameasurements)).
3. Fill the `provenance` block.
4. Run `check`: it drafts every block in every size of your table and names any size that does not make a pattern.
5. Try it: `python skills/pattern-making/scripts/pattern.py block all --table aldrich-women --size 12 --out out`.

## Add a construction preset

The proportions of a collar, a hood or a fit are a few numbers. The files that hold the engine's own values describe
each one: see `skills/pattern-making/data/constructions/notched-collar.json`.

1. Create a file with only the values that differ, and `applies_to` set to the same construction
   ([format](skills/pattern-making/data/README.md#constructions)). Measure each value the way the default file
   describes it.
2. Run `check`, then draft a garment with it: in a spec, `"collar": {"preset": "<your id>"}`
   ([garment specs](skills/pattern-making/references/garment-spec.md), examples in
   `skills/pattern-making/examples/`).
3. Look at the drawing (`pattern.svg`). If it looks like the collar you know, send the preset. A spec added to
   `examples/` gets its picture drawn at merge.

To correct one of the engine's own values, edit the default file directly and explain why.

## Add a pattern

This is what the project needs most: real outlines in place of described ones. The full method is in
[EXTRACTION.md](skills/pattern-making/data/EXTRACTION.md); in short:

**1. Digitise each piece**, seam line, grain vertical, with a ruler next to it. Three ways in, the same result:

```
python skills/pattern-making/scripts/pattern.py digitize back.png    --id my-jacket --outline back --type bodice_back
python skills/pattern-making/scripts/pattern.py digitize tracing.svg --id my-jacket --scale-length 10
python skills/pattern-making/scripts/pattern.py digitize points.csv  --id my-jacket --outline sleeve --type sleeve
```

- A photo (PNG) opens a window: click the two ends of a known length on the ruler, then click along the outline.
  Left click for a point on a curve, right click for a corner, N to name the point just clicked, U to undo, Enter
  to finish.
- A tracing made in a drawing program: one path per piece, a straight line named `scale` over the ruler, a named
  circle on a point to name it.
- Points measured on the paper with a ruler: one `x, y` per line in centimetres, then optionally a name and the
  word `corner`.

**2. Name the points and say how it goes together**, in `skills/pattern-making/data/shapes/<id>.json`: the standard
point names of each piece type, the seams between them, what every other edge is (fold, hem, free...), and the
body measurements the pattern was made for.

**3. Let the skill measure it:**

```
python skills/pattern-making/scripts/pattern.py shape my-jacket --out preview    # print preview/pattern.svg at 100 %
python skills/pattern-making/scripts/pattern.py analyze my-jacket                # every dimension, seam and ease
python skills/pattern-making/scripts/pattern.py check
```

Lay the paper on the print: the largest gap goes in `provenance.extraction.deviation_mm`, 2 mm at most. `analyze`
lists what is missing: a standard point not named, two sewn edges of different lengths, an edge nobody accounts
for. When it prints no `!!` line, the pattern is complete.

**4. Send the `.json` file only.** Its picture and its analysis sheet are drawn by the skill at merge.

No Python at hand? Open a "share a pattern piece" issue and paste the points you measured with a ruler.

## List an avatar's arrangement points

The 3D shell is placed on the avatar by point name, and the names differ between avatars. With CLO3D and
[clo3d-mcp](https://github.com/Ubani-Studio/clo3d-mcp), the `get_scene_summary` tool lists the points of the avatar
that is loaded. Copy `skills/pattern-making/data/avatars/clo-library.json`, put the right point after each piece,
and say in `provenance` which avatar and which CLO3D version you read them on.

## Code

The engine is four files with no dependency: `pattern.py` (blocks, checks, exports), `garment.py` (whole garments
from a spec), `templates.py` (typical pieces) and `library.py` (the data library, digitising, analysis). A new
construction goes in `garment.py`, a new typical piece in `templates.py`, and its numbers in `data/constructions/`,
never in the code.

```
python skills/pattern-making/scripts/pattern.py test     # must print "All tests pass."
python skills/pattern-making/scripts/pattern.py check
```

The engine's own laws apply to everything it drafts: edges sewn together have the same length within 1 mm unless
an ease is declared with its reason, a piece meets its fold at a right angle, no outline crosses itself. A draft
that breaks one prints a `!!` line; fix the draft, not the check.

## Sending it

1. Fork, branch, commit. One subject per pull request.
2. Leave out `INDEX.md`, `COVERAGE.md`, `CREDITS.md`, and every `.svg` and analysis `.md` next to a data file or an
   example: they are rebuilt from the data when your pull request is merged.
3. Open the pull request. `check` and `test` run on it automatically.

Plain English, metric units, no emojis in the files. Thank you.
