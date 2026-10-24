# Photo-to-pattern body and design contract

Use this before a new photo-based draft. It separates visual evidence, nominal sizing, construction
choices, and independently testable design targets. It does not infer a wearer's body from a photograph.

## Record before drafting

1. **Inventory:** name each garment/layer separately, visible views, coverage/occlusion, fabric behavior,
   and the executable starting point (whole recipe, primitive block, or a dedicated piece recipe).
2. **Evidence:** record visible landmarks and construction with qualitative confidence. Mark every
   hidden seam, waistband/rise, facing, pocket bag, and closure assumption. Record plausible alternate
   constructions when a photograph does not distinguish them.
3. **Scale:** record a measured, coplanar reference and perspective correction if one exists. Without it,
   record relative ranges such as “hem near the knee” or “outer layer below the inner hem.” Head/hand
   guesses, a declared height, a photographed screen, or projected garment width do not calibrate cm or
   circumference. Pose and perspective affect ratios too; avoid exact-looking confidence percentages.
4. **Body contract:** choose a named nominal body or real measurements with units and sources. Freeze
   bust/chest, waist, hip, neck-to-shoulder length, back-waist length, arm length, hip depth and seated rise;
   include relevant derived values (armhole depth, widths, bust point/intake). Resolve the whole body record
   and review every table/derived assumption. Height may be background context but is not an engine input.
5. **Design contract per garment:** freeze finished lengths and girths, wearing/easing allowances, fabric
   stretch/recovery, closure overlap excluded from girth, dart intake deducted when estimating sewn girth,
   cut quantities, and grain. Name endpoints for each length. Select target ranges before generating output.
6. **Cross-layer relations:** choose intended outer/inner hem relation, sleeve reveal, neckline depth,
   waistband placement, and clearance between layers. Compare distances measured from a common physical
   origin; two unrelated local pattern y coordinates cannot establish an assembled hem relationship.
7. **Acceptance:** reopen JSON/DXF, measure named landmarks, compare with frozen ranges, and inspect SVG/PNG.
   Validate seams, folded darts, net/CUT geometry and all marks. Fit remains a toile check.

## Generic worked contract (synthetic, no photo or wearer)

Inventory: one woven sleeveless top and an outer open layer. Construction assumptions: separate facing,
straight grain, side seams and an independently specified closure. The photo evidence in a real project
would be recorded separately; this example provides only selected nominal design values.

Nominal adult body: bust 88, waist 70, hip 96, neck 37, shoulder seam 12.2, back length 40, arm length 59,
hip depth 20, body rise 27 cm. Select armhole depth and front/back widths explicitly after reviewing the
chosen block. For a darted body, also choose bust depth/span and intake. These are assumptions, not an
official complete size table or estimated wearer measurements.

Design: top length from a defined neck datum 58–62 cm, outer layer from the same datum 64–68 cm,
outer hem 4–8 cm below the top. Choose bust/hip ease for the fabric and layers separately; do not derive
finished girths from projected photo widths. This is a contract example, not a ready-to-cut recipe.

## Executable landmark constraints

`piece` accepts `proportion_contract` and preserves it on reexport. Values are recomputed from the actual
piece nodes; saved `proportion_results` and pass flags are not trusted. Methods `distance`, `x`, and `y`
measure Euclidean distance or absolute coordinate difference in cm. Use landmarks that represent the
intended finished dimension. The helper does not infer sewn girths, dart closure or fit.

```json
{
  "proportion_contract": {
    "dimensions": [
      {"id": "body_length", "piece": "Front", "from": "neck_datum", "to": "hem_datum",
       "method": "y", "range_cm": [58, 62]},
      {"id": "reference_width", "piece": "Front", "from": "width_in", "to": "width_out",
       "method": "distance", "range_cm": [24, 26]}
    ],
    "ratios": [
      {"numerator": "body_length", "denominator": "reference_width", "range": [2.2, 2.6]}
    ]
  }
}
```

IDs can refer to different garments' piece landmarks, enabling independent cross-layer ratios when
origins and endpoints are comparable. Keep a written contract for difference constraints and assembly
measurements that this small helper does not implement. Never choose bounds by reading the result you
are checking. Tests include short/long negative controls, valid controls and preserved-contract reexports.

## Before a garment production run

Freeze each garment's inventory, body/design dimensions and construction first. Check that the chosen
entry point actually implements it. A women's jacket recipe cannot stand in for a men's tee, shirt,
knit vest, or complete jeans/shorts. Add a bounded dedicated piece recipe only when its construction and
independent targets are specified. Do not label blocks as completed outfits.
