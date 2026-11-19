# Worked specs: sleeves, collars, hoods, pockets

Specs for the `garment` command (`references/garment-spec.md`), women 38, one construction each. They run with
`python ../../scripts/pattern.py garment <spec>.json --out out_<name>` and pass every engine check.

| Spec | Construction |
|---|---|
| `raglan_coat.json` | boxy coat, one-piece raglan sleeve with the sleeve-top dart, stand collar, facing |
| `kimono_top.json` | kimono sleeve cut in one with the body, diamond gusset in a slash |
| `dolman_top.json` | dolman: kimono with slope 40, underarm 15 below the armhole, no gusset |
| `shirt.json` | shirt collar with a separate stand, one-piece sleeve, breast welt pocket |
| `camp_shirt.json` | convertible (camp) collar on a lowered neckline, short one-piece sleeve |
| `hooded_jacket.json` | two-piece hood, two-piece sleeve, lining, jetted hip pocket and breast welt |

Outlines are drafted from the technique sheets (trade practice), not yet compared with published patterns:
check them on a toile. The raglan dart width is an input (`dart`, 2 to 3 cm); the report prints where the
shoulder tips meet below the cap top (`cap_lower` adjusts it).
