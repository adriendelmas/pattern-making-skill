# Measurements

All measurements in centimetres, taken close to the body, over fitted underwear, without pulling.
Mark the natural waist with a tape or an elastic before starting.

## Keys read by the script

| Key | How to take it | Blocks |
|---|---|---|
| `bust` | Horizontal round at the fullest part of the bust, or of the chest for men | bodice, sleeve |
| `waist` | Round at the natural waist, the narrowest point | all |
| `hip` | Horizontal round at the fullest part of the seat | skirt, trousers |
| `back_length` | From the prominent vertebra at the nape to the waist, along the spine | bodice |
| `hip_depth` | From the waist to the hip line, at the side | skirt, trousers |
| `skirt_length` | From the waist to the intended hem, at the side | skirt |
| `arm_length` | From the shoulder point to the wrist, arm slightly bent | sleeve |
| `wrist` | Round of the wrist over the bone | sleeve |
| `body_rise` | Seated on a hard chair, from the waist to the seat, at the side | trousers |
| `trouser_length` | From the waist to the intended hem, at the side | trousers |
| `knee_width` | Intended finished width at the knee, full round of the trouser leg | trousers |
| `hem_width` | Intended finished width at the hem, full round | trousers |

Derived measurements, calculated from the bust when missing:

| Key | How to take it |
|---|---|
| `neck` | Round at the base of the neck, passing over the nape vertebra |
| `shoulder` | From the side neck point to the shoulder point |
| `armhole_depth` | From the nape to the underarm line, at the back |
| `half_back_width` | Half the back width, from one arm crease to the other, halfway down the shoulder blade |
| `half_chest_width` | Half the front width, from one arm crease to the other, above the bust |
| `bust_depth` | Women: from the side neck point to the bust point |
| `bust_span` | Women: distance between the two bust points |
| `bust_dart` | Women: bust dart value, larger for a full cup |

The derivation formulas are in the script's `complete` function. They give average values: a real
measurement is always better.

## Personal measurements file

```json
{
  "body": "women",
  "bust": 92,
  "waist": 72,
  "hip": 100,
  "back_length": 40.5,
  "bust_dart": 5,
  "ease": {"bust": 10, "skirt_hip": 5}
}
```

Missing keys come from the explicitly chosen size, or the default table (women 38, men 48, children age 8).
The engine does not infer the nearest standard size. Saved pieces include `resolved_measurements`,
`resolved_ease`, `measurement_unit`, and per-field `measurement_provenance` (input/table/derived).
`python scripts/pattern.py measurements --measurements file.json` prints the complete set used.

## Standard sizes in the script

Indicative values, based on European practice. They serve as fallback and as grading basis.

- **Women**: reference size 38, from 34 to 48, with 4 cm of round between two sizes.
- **Men**: reference size 48, from 44 to 58, with 4 cm of round between two sizes.
- **Children**: by age, from 4 to 14. Lengths follow height.

## Adapting to a figure

- **Sway back**: lower the skirt or trouser center back by 1 to 2 cm at the waist.
- **Round back**: lengthen the back above the shoulder blade and add a back shoulder dart.
- **Full bust**: increase `bust_dart`. Beyond 6 cm, split the dart in two.
- **Sloping or square shoulders**: change the shoulder slope by 0.5 to 1.5 cm, and the armhole by as much.
- **Prominent stomach**: add length at center front and reduce or remove the front darts.
- **Asymmetry**: draft both sides separately rather than on the fold.

## Scope and provenance

`height` is not a supported input and does not scale the geometry. Explicitly select `back_length`,
`arm_length`, `hip_depth`, `body_rise`, `trouser_length` and any relevant finished design lengths.
`shoulder` is one neck-to-shoulder seam length, not full shoulder breadth. Children's preset lengths
are scaled from the built-in age table; this is not arbitrary stature-driven drafting.

Unknown fields, unknown ease keys and nonfinite measurements fail. `--measurements` plus `--sizes`
is rejected for body blocks and gloves. Standard-only grading and single personal sizes are distinct
supported workflows; personal-base grading is not implemented. Glove inputs under `hand` are in mm,
as documented in `techniques/accessories.md`; body inputs are cm.

A resolved body record lists all supported fields; each individual block consumes only its relevant
subset (see tables above). Table/derived values are assumptions. Preserve the original input and state
which chosen body and finished design dimensions remain to be confirmed on a toile.
