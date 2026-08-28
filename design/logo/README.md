# Joule Coach: Logo Directions

**Decided (2026-08-28): mark 07, In the Overlap.** Extracted to
`marks/07-in-the-overlap.svg` and in use in prototype 05. The write-up
below is kept as-is, including the honest risk notes on 07, because they
are still the right things to watch as it gets used at more sizes.

Five candidate marks, with the reasoning behind each. Open `index.html`
for the visual presentation: every mark is shown large, in lockup with
the wordmark, on light and dark, in one colour, and at 32px and 16px.

Standalone SVGs are in `marks/`. They use `currentColor` for the neutral
so they invert cleanly, with the orange hard-coded.

---

## The philosophy

### 1. The mark should say what only this product can say

Joule Coach's one unfakeable claim is **multi-camera triangulation**.
Two calibrated views resolve a joint in true 3D, including frontal-plane
knee travel that no single camera can see at all. A phone propped against
a water bottle cannot produce that reading, ever.

The engine carries a hard install rule that comes straight out of this:
two cameras must converge between **47° and 133°**, and must never sit
opposite each other, because measured joint-angle error roughly doubles
at 180° (`CAMERA_PLACEMENT.md` rule 4: 7.7 to 11.8° at good convergence
against 16.5 to 18.2° at ~180°). That constraint is a gift to a logo. It
is a real number, it belongs to this product alone, and it is a shape.

Four of the five marks are drawn from that geometry. The fifth is drawn
from what the geometry produces.

### 2. The mark should carry the product's ethic, not just its mechanism

`PRODUCT_SPEC.md` §3.1 sets the tone as **calibrated confidence, not
hype**. The product's credibility rests on drawing what it did not
measure as carefully as what it did, which the app does with a solid
stroke against a dashed one on every screen.

Two of the marks build that same convention into their own construction
rather than applying it as decoration. In 02, the calibration baseline is
dashed because it is known rather than observed, while the sightlines are
solid because they were measured. In 05, ink is what should have
happened and orange is what did.

### 3. The logo introduces no new brand colours

It is built entirely from the palette the product already uses to tell
the truth, which is why the mark sits inside the app rather than on top
of it. The only new value is the mark orange, chosen deeper than the UI
amber so it holds on white as well as on black.

---

## Rejected before drawing

Every one of these is what the category reaches for by default:

lightning bolt · dumbbell silhouette · flexing bicep · heartbeat line ·
camera aperture · neural node cluster · gradient mesh blob · a J in a
rounded square

The **lightning bolt is the worst trap**, because "Joule" is the SI unit
of energy and the bolt is the first thing anyone draws. It describes the
name and says nothing about the product. The camera aperture is the
second trap: it is the literal reading, every camera app already owns it,
and it pulls the brand toward surveillance rather than measurement.

---

## The five marks

| # | Name | Thesis | Best at |
|---|---|---|---|
| 01 | The Overlap | Truth is only where two views agree | Smallest sizes, app icon |
| 02 | Triangulation | The algorithm, drawn | Large format, the fullest story |
| 03 | The Angle | The output, not the apparatus | Instrument feel, wide use |
| 04 | The Measure | Two heights, honestly compared | One colour, print |
| 05 | The Plumb J | A letter that is also a measurement | Conventional brand use |

### 01 The Overlap
Two camera frames, offset. The filled rectangle is their intersection,
which is exactly the volume the engine can measure in 3D. Step outside it
and the product honestly declines to score you, which is the same idea
the app draws as a ghost cell. The mark is the calibrated volume itself.

*Risk:* overlapping-rectangle marks are not rare, so this leans on
execution rather than novelty. It is the most conventional of the five,
which is also why it is the safest.

### 02 Triangulation
Two camera positions, two sightlines, one solved joint. The baseline is
dashed because calibration knows it, the sightlines are solid because
observation measured them. The sightlines meet at 65°, inside the
validated band.

*Risk:* it reads as a diagram. That is either the whole point or a
disqualifier, depending on whether the brand should feel like an
instrument company or a consumer app.

### 03 The Angle
Two limbs and the arc between them, drawn the way a clinician annotates a
joint angle. Where 01 and 02 describe how the product works, this
describes what it hands you. The arc is the single number the whole
engine exists to produce, so it takes the orange.

*Risk:* close to a generic geometry or architecture mark. It needs the
wordmark beside it to land in the right category.

### 04 The Measure
Two dimension lines, the drafting convention for a distance that has
actually been measured rather than estimated. Ink is the reference depth,
orange is what the set reached. Joule is the unit of work, and work is
force applied over a distance.

*Risk:* the most abstract and the least specific to cameras. It says
measurement and comparison clearly but says nothing about 3D, so it leans
hardest on the wordmark.

### 05 The Plumb J
A J whose stem is the reference plumb the app draws down through the
knee, and whose hook is the measured path departing from it. The
letterform and the finding are the same drawing.

*Risk:* ties the identity to a single initial, which is harder to extend
if the product is renamed.

---

## Round two: body and exercise marks

Round one carried the mechanism but had **no body in it**, so nothing on
the page said gym. Round two adds eight marks with a figure, in two
treatments (drawn skeleton and solid figure), split between body alone
and body fused into a round-one mark. Open `body.html`.

This is not decoration. `PRODUCT_SPEC.md` §3.2 already names the
**skeleton overlay as the brand's visual signature**: use the real joint
overlay as a first-class design element, derived from actual pose data
rather than a generic icon, because it is the one thing a copycat cannot
fake. The app draws that figure on the report screen. A mark built from
it is the identity agreeing with the product.

Every figure is a **squat at depth, seen from the front**. That is the
exercise the engine measures best and the only view in which knee travel
is visible.

| # | Name | Treatment | Kind |
|---|---|---|---|
| 06 | Framed | Solid | Mixed: body plus camera frame |
| 07 | In the Overlap | Skeleton | Mixed: limb inside two frames |
| 08 | The Measured Knee | Skeleton | Mixed: goniometer arc on a limb |
| 09 | Sightlines | Skeleton | Mixed: two cameras, one lifter |
| 10 | Bottom Position | Skeleton | Body alone |
| 11 | The Lifter | Solid | Body alone |
| 12 | The Chain | Skeleton | Body alone, reduced to one limb |
| 13 | The Rep | Skeleton | Body alone, two positions |

**Pick:** 06 Framed. It is the only mark in either round that draws the
product's hardest constraint, the rule that the whole body including the
feet must stay inside the calibrated volume, and it turns a limitation
into the identity. 12 The Chain is the reduction play and the only mark
that survives 12px. 10 and 11 are the same idea in the two treatments,
so pick the register rather than the drawing.

**09 Sightlines is the weakest and I would not ship it.** Noted below.

### What the drawing process caught

- **The squat pose was wrong twice.** The signature of a front-view
  squat is that the **knees sit wider than both the hips and the feet**.
  The first pass drew hips, knees and feet at similar widths, and every
  figure read as a person standing with their arms out. Corrected to
  hips 14 units, knees 36, feet 22.
- **09 was recomposed three times.** With cameras overhead, the
  sightlines read as raised arms. Removing the figure's own arms made it
  worse, because then the sightlines simply became the arms. Moving the
  cameras to the sides and dashing the lines fixed the ambiguity but left
  the mark cluttered. Two cameras plus a full figure is more than a logo
  can hold. If the mechanism needs stating, round one's 02 does it
  cleanly without a body.
- **07 originally held a whole figure** inside the frame intersection and
  it became a smudge below 48px. It carries a single limb now.
- **13's extended state was a dead-straight vertical** that read as a
  pole rather than a leg. Both states now share a hip and a foot, so only
  the knee moves, which is what makes it read as one limb flexing.

---

## Palette

| Role | Hex | Rule |
|---|---|---|
| Instrument orange | `#E85D0C` | The mark. Deeper than the UI amber so it holds on white and on black. |
| Signal amber | `#F5A623` | Pinned in `PRODUCT_SPEC.md` §3.2 for coaching cues. Secondary tone, never the mark. |
| Ink | `#121416` | Never pure black. The ground the app is built on. |
| Warm white | `#F4F2EE` | Never pure white. The spec's light surface. |
| Confirmed teal | `#2A9D8F` | Reserved for confirmed-good states in the product. Not part of the logo. |

`#E85D0C` measures 5.29:1 against ink and 3.49:1 against warm white. It
is safe as a graphic mark on both, and safe as text only on dark. **Never
set orange body text on a light ground.**

## Typography

Wordmark is **Archivo**, the same variable family the product UI uses, so
the logo and the app speak in one voice. JOULE at weight 800, COACH at
weight 300, both at width 88% and tracking -0.028em. The weight contrast
carries the lockup, so no second typeface is needed.

## Usage

- **Clear space:** one cap-height of the wordmark on all sides.
- **Minimum size:** 24px for 01, 02, 03 and 05. 04 holds to 16px.
- Do not recolour the mark outside the palette above.
- Do not add effects. No gradients, glows, bevels or drop shadows.
- On photography, place the mark on a solid field rather than over the
  image.

---

## Honest notes

- **Two concepts were cut during the work, not before it.** A corridor
  mark drawn as a closed lens with a dot above it read unmistakably as an
  eye, which is the surveillance association this product least wants.
  Redrawn as an open band, it read as a scribble. It was replaced by 04
  rather than defended.
- **05 originally carried a dashed plumb** continuing below the hook. At
  logo scale it read as debris rather than as a line, so it was cut. The
  colour split now carries that meaning alone.
- **The 16px test is the real filter.** 01 and 04 pass it cleanly. 02, 03
  and 05 hold at 24px and above but want a simplified small-size variant
  drawn for favicon use, which is a normal thing to do and is not yet
  done here.
- None of these has been tested against a trademark search or against
  competitor marks. That should happen before anything is committed.

## Files

```
design/logo/
  index.html              round one, geometry only, marks 01 to 05
  body.html               round two, body and exercise, marks 06 to 13
  README.md               this file
  marks/01-overlap.svg
  marks/02-triangulation.svg
  marks/03-angle.svg
  marks/04-measure.svg
  marks/05-plumb-j.svg
```

Round two's marks live in `body.html` rather than as standalone SVGs,
because several are still moving. Say which ones you want and I will cut
them out as individual files the same way.
