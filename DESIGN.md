# Habitat — Design Document

A colony-survival game for the Amstrad CPC 6128, Mode 0, 128 KB.

| | |
|---|---|
| Status | Design. No engine code written yet. |
| Target | Amstrad CPC 6128 (128 KB), Mode 0 (160×200, 16 colours), disc |
| Lineage | Systems modelled on *Planetbase* (Madruga Works, 2015), cut down to fit a Z80 |
| Art | [`assets/`](assets/) — already built, documented in [`assets/SPRITES.md`](assets/SPRITES.md) |
| Toolchain | `rasm` → `iDSK` → `cpcemu` (headless, scriptable) |

This document is the plan, not the code. Where a number is a first guess for tuning
it says so. Where a technique needs proving on real hardware it is listed in
[§15 Open risks](#15-open-risks).

---

## 0. At a glance

| Decision | Value | Where |
|---|---|---|
| World size | 128 × 128 tiles, origin `(0,0)` at the exact centre | [§3.2](#32-the-world) |
| Tile | 4 bytes × 16 scanlines = 8×16 px = 16×16 *visual* | [§3.1](#31-the-unit-ladder) |
| Position unit | **half-tile**, signed byte per axis, −128…+127 | [§3.4](#34-anchors-are-centres) |
| World state | 1 byte per tile → 16,384 bytes → one full 16 KB bank | [§3.5](#35-the-world-byte) |
| Terrain | seeded pyramid noise, generated once into the bank | [§5](#5-procedural-world-generation) |
| Seed | 16-bit, shown as 4 hex digits + generator version | [§5.2](#52-the-seed) |
| Agents | 80 colonists + 16 bots = 96, SoA tables | [§6.1](#61-entities) |
| Movement | node graph + edge progress, **batched over a 16-frame wheel** | [§6.3](#63-movement), [§7](#7-the-batch-scheduler) |
| Routing | all-pairs next-hop + distance matrices, 16 KB each | [§6.4](#64-routing) |
| Screen | play area 80×160 (20×10 tiles), HUD 80×40, raster split | [§8.1](#81-screen-layout) |
| Camera | whole-tile steps via CRTC R12/R13 offset | [§8.2](#82-camera) |

---

## 1. Premise

### 1.1 What Habitat is

A ship drops a construction pod on an unnamed world and leaves. You are the base
architect: you decide **where** things go, never **who** does what. Colonists walk
out of the pod and start working on whatever you have placed, in whatever order
their own needs and the job board dictate. If you place an oxygen generator with no
power, nobody stops you — they suffocate.

The loop is: **place → produce → survive the night → call the next ship → place more**.
Every structure you add consumes something another structure must make. The colony
is always one broken link away from dying, and you find out which link only when it
snaps.

### 1.2 What Habitat takes from Planetbase

Planetbase's core, in the order it matters:

- **Indirect control.** You place buildings; colonists are autonomous. No unit orders.
- **Nested production chains.** Power → oxygen → water → food → refined goods → bots
  and spares, each tier needing the one below it *and* the people to staff it.
- **Specialised colonists.** Workers, engineers, biologists, medics, guards. The right
  building without the right person is dead weight, and you control the mix only by
  choosing who to request on the next ship.
- **Domes and connections.** Round rooms, joined by corridors, with airlocks as the
  only way in and out. The base is a graph, and the graph's shape is the game.
- **Needs, not health bars.** Oxygen, water, food (with variety — a colony fed one
  crop gets sick), sleep, health, morale.
- **Disasters.** Sandstorms, solar flares, meteor strikes, intruders. Each attacks a
  different part of the chain.
- **No victory screen.** Milestones — population, self-sufficiency — rather than a win.

Sources consulted for the above: the [Steam store description](https://store.steampowered.com/app/403190/Planetbase/),
a [review](https://techraptor.net/gaming/reviews/planetbase-review-colonies-surviving-catastrophies)
and a [systems summary](https://shapes.inc/fandom/planetbase).

### 1.3 What Habitat cuts, and why

| Cut | Reason |
|---|---|
| 3D, free camera, rotation | Mode 0 top-down only. The art is already top-down. |
| Free-form dome placement | Everything snaps to the tile grid ([§3.3](#33-the-grid-is-not-a-choice)). |
| Hundreds of colonists | 80 is the agent-table ceiling; see [§6.1](#61-entities). |
| Interior walking, per-person pathing inside a dome | People occupy one of 8 ring slots. The art was drawn that way. |
| Separate Vegetables / Starch / Vitromeat bars | One **Food** bar plus a hidden 3-way variety counter ([§6.6](#66-needs)). |
| Four hand-authored planets | Four **palette + parameter** variants on one generator ([§5.7](#57-classification-and-planet-types)). |
| Arbitrary corridor shapes | Only H, V and 45° — the only corridor sprites that exist. |

Nothing above is a placeholder for "add later". Each cut buys frame time or RAM that
is spent elsewhere in this document.

---

## 2. Target and budget

### 2.1 The machine

- Z80 at 4 MHz, all instruction timings rounded up to whole microseconds by the
  gate array. **1 frame ≈ 19,968 µs ≈ 80,000 T-states.**
- 128 KB RAM as eight 16 KB banks. Banks 0–3 are the base 64 KB; banks 4–7 are paged
  into `&4000–&7FFF` by writing `&C4`…`&C7` to the gate array (port `&7Fxx`);
  `&C0` restores base bank 1 there. **Blocks 0, 2 and 3 are never re-mapped**, so the
  video circuitry's view of `&8000` and `&C000` is never disturbed by paging.
- CRTC 6845, AY-3-8912, µPD765 FDC.
- **The firmware is switched off** once loading finishes: own IM 1 handler, own
  disc routines. Nothing may live at `&A700–&BFFF` expecting AMSDOS to be there,
  because it will not be.

### 2.2 The frame budget

Everything in this document is costed against 19,968 µs. The two blit kernels:

| Kernel | Cost per data byte | Why |
|---|---|---|
| Opaque copy | ≈ 4 µs (`ldi`) | terrain, icons, machines, plants, slots |
| Masked copy | ≈ 14 µs (`and`/`or` pair) | domes, rings, corridors, connectors, structures |

Which follows from `assets/SPRITES.md` §2: masked sprites store `mask,data` interleaved,
so a masked line reads twice the bytes and does four times the work.

Consequences, computed once here and referred to throughout:

| Operation | Bytes | Cost | Frames |
|---|---|---|---|
| One terrain tile | 64 opaque | **929 µs measured** | 0.047 |
| One viewport column (10 tiles) | 640 | **9,300 µs** | 0.47 |
| One viewport row (20 tiles) | 1,280 | **18,600 µs** | 0.93 |
| Full play area (200 tiles) | 12,800 | **185,700 µs** | **9.3** |
| One colonist slot | 16 opaque | ≈ 64 µs | 0.003 |
| One machine / plant | 132 opaque | ≈ 530 µs | 0.027 |
| Small dome, ring + dome, all 4 quadrants | 2,048 masked data | ≈ 28,700 µs | **1.4** |
| Medium dome, likewise | 4,608 | ≈ 64,500 µs | **3.2** |
| Large dome, likewise | 8,192 | ≈ 114,700 µs | **5.7** |

> **The tile rows are measured, not estimated** — `tests/test_tiles.py` times ten
> full passes on the emulator. The original estimate was 320 µs, derived from
> "64 bytes × 4 µs, plus stepping". It was wrong by 2.9×, for two reasons the
> arithmetic did not include: per-line address stepping costs 40 T-states on top
> of 64 spent copying, and the CPC's gate array contention puts real throughput
> about 22% below nominal 4 MHz. Splitting the measurement: **579 µs is the blit
> and the loop, 350 µs is the per-tile logic** (class, variant, autotile, ore).
> See [§8.3](#83-the-tile-pass).

Read the dome rows carefully — **drawing one large dome costs almost six
frames.** That single fact drives the whole architecture: nothing may ever be
redrawn wholesale, and the one time it must (at construction) the work is split
across frames. `assets/SPRITES.md` §8 already gives the minimal-redraw table; this
design obeys it.

---

## 3. Coordinates and units

### 3.1 The unit ladder

Five units, each an exact multiple of the one below. Getting these straight removes
most of the arithmetic from the engine.

| Unit | Horizontal | Vertical | Note |
|---|---|---|---|
| Mode 0 pixel | 1 px | 1 line | 2 px per byte |
| Byte | 2 px | 1 line | the blit's unit |
| **Half-tile (HT)** | 2 bytes = 4 px | 8 lines | **the position unit** |
| **Tile** | 4 bytes = 8 px | 16 lines | the terrain unit |
| Screen (play area) | 80 bytes = 20 tiles | 160 lines = 10 tiles | |

Because Mode 0 pixels are double-width, a tile is **16 × 16 visual units** — square on
screen. A half-tile is 8 × 8 visual.

The half-tile is not arbitrary. It is exactly the CRTC's display-offset granularity:
one offset word is 2 bytes horizontally, and `R1` (= 40) offset words is one character
row of 8 lines. See [§8.2](#82-camera).

### 3.2 The world

**128 × 128 tiles.** Tile coordinates run **−64 … +63** on both axes; `(0,0)` is the
centre tile and the landing site. `+x` is east, `+y` is **south** (down the screen).

| | |
|---|---|
| In tiles | 128 × 128 |
| In half-tiles | 256 × 256, coordinates −128 … +127 |
| In bytes / lines | 512 bytes × 2,048 lines |
| In viewports | 6.4 wide × 12.8 tall |
| In world state | 16,384 bytes = exactly one 16 KB bank |

That last row is why 128 is the number. One byte per tile, one bank, and the address
arithmetic is two shifts:

```
index = ((y + 64) << 7) | (x + 64)          0 … 16383
H = &40 + (index >> 8)                      bank window base is &4000
L = index & 255
```

A signed-byte tile coordinate and a signed-byte half-tile coordinate both fit their
axis exactly, with no clamping logic and no 16-bit coordinate maths anywhere in the
hot loops. A 256×256 world would need 2 bits per tile (losing the room for occupancy
and variant) or a second bank; noted as a growth path in [§15](#15-open-risks), not
taken now.

For scale: a large dome is 8 × 8 tiles. A mature colony of 20–30 domes plus corridors
occupies roughly 40 × 40 tiles. The remaining world is where the mines, the lakes and
the next expansion are — far enough to matter, close enough to walk.

### 3.3 The grid is not a choice

The tile size was derived from the art, not imposed on it. Every sprite in
`assets/sprites.bin` is already an exact number of 4-byte × 16-line tiles:

| Sprite | Frame (bytes × lines) | Tiles |
|---|---|---|
| `dome_s` + `ring_s` | 16 × 64 | 4 × 4 |
| `dome_m` + `ring_m` | 24 × 96 | 6 × 6 |
| `dome_l` + `ring_l` | 32 × 128 | 8 × 8 |
| structure `s` | 4 × 16 | 1 × 1 |
| structure `m` | 8 × 32 | 2 × 2 |
| structure `l` | 12 × 48 | 3 × 3 |
| structure `xl` (`mine`, `pad`) | 16 × 64 | 4 × 4 |
| diagonal corridor step `(CORR_D_SX, CORR_D_SY)` | 4 × 16 | **1 × 1** |

The diagonal corridor advancing exactly one tile per step is the happy accident that
makes corridor routing ([§9.4](#94-corridor-routing)) a grid walk rather than a line
algorithm.

Corridors used **not** to align: they run on the dome's centre line, and `conn_points`
put them 4 lines either side of it, so a horizontal corridor straddled two tile rows
by 4 lines each. [ASSET-6](#12-asset-gaps) has since fixed that for the axis-aligned
doors, and **corridor redraw rectangles can now be computed in tiles, not lines**:

| Door | Corridor | Rule |
|---|---|---|
| `n`, `s` | vertical | `x` is a multiple of 4 px (2 bytes) |
| `e`, `w` | horizontal | `y` is a multiple of 8 lines |
| diagonals | diagonal | exempt — already one tile per step |

The diagonals are exempt on purpose, not by omission. On an axis-aligned door the
snap is **tangential**: it changes the radius by `d²/2r`, a fraction of a pixel. On a
diagonal door the same shift has a radial component of `0.707·d`, and the ring is
only 8 visual pixels thick — the door leaves the ring. Verification 12 in the
generator enforces the rule and its exemption.

### 3.4 Anchors are centres

Every placed object stores **its centre**, in half-tiles, as two signed bytes. Not a
corner, not a bounding box — the centre. `(0,0)` is therefore both the world centre
and the centre of the starting pod, and every "distance from home" is a subtraction.

For an object `W` tiles wide, the centre sits `W` half-tiles from its left edge, so:

```
left_tile = (centre_hx - W) / 2            exact, because centre_hx and W
top_tile  = (centre_hy - H) / 2            always share parity
```

Even footprints (4, 6, 8 tiles — all domes, `m` and `xl` structures) land on even
half-tiles, i.e. on tile corners. Odd footprints (3 tiles — `l` structures) land on
odd half-tiles, i.e. on tile centres. The build cursor snaps automatically by only
offering positions of the right parity for the thing being placed; the player never
sees this.

Screen position from world position, with the camera centre at `(chx, chy)`:

```
byte_x = (hx - chx) * 2 + 40               play area is 80 bytes wide
line_y = (hy - chy) * 8 + 80               play area is 160 lines tall
```

Two shifts and an add per axis. No multiply anywhere.

### 3.5 The world byte

One byte per tile holds everything about that tile that is not in an object list:

| Bits | Field | Values |
|---|---|---|
| 0–2 | terrain class | 0 ground · 1 dust · 2 rock · 3 mountain · 4 shallow water · 5 deep water · 6 crater · 7 foundation |
| 3 | resource | mountain: ore vein present · water: drillable depth · ground: fertile |
| 4–5 | occupancy | 0 free · 1 structure · 2 corridor · 3 blocked / reserved |
| 6–7 | decor | 4 art variants; doubles as the water animation phase |

**The autotile variant is deliberately not stored.** Which classes autotile is not
stored either: a class with 16 variants in `tile_variants` is autotiled, anything
else takes its variant from the decor bits. The rule falls out of the data, so
there is no second table to keep in step. It is recomputed at draw time
from the four orthogonal neighbours — four bank reads and a 16-entry lookup, which
is inside the measured 929 µs per tile ([§2.2](#22-the-frame-budget)); the blit
itself dominates. Paying that to free 4 bits of world state is a good trade, and it means terrain edits never have to fix up their
neighbours' stored variants.

Occupancy stores only *what kind*, not *which object*. Finding which dome covers a
tile means scanning the ≤64-entry dome list, which happens on a mouse-click, never in
a loop.

---

## 4. Memory map — all 128 KB

### 4.1 Paging

`&4000–&7FFF` is the only window that moves. Five pages rotate through it:

| Gate array value | Page in window |
|---|---|
| `&C0` | base bank 1 |
| `&C4` | bank 4 |
| `&C5` | bank 5 |
| `&C6` | bank 6 |
| `&C7` | bank 7 |

A page switch is one `out (c),c` — about 5 µs. That is cheap enough to switch inside
a draw loop, so sprites are grouped by bank and each render pass pages once.

**No code, no stack, no interrupt handler ever lives in the window.** Everything that
must always be reachable is in bank 0 (`&0000–&3FFF`) or bank 2 (`&8000–&BFFF`).

### 4.2 The eight banks

| Block | Bank | Contents | Bytes | Slack |
|---|---|---|---|---|
| `&0000–&3FFF` | 0 | engine code, ISR, blit kernels, generator, UI | 16,384 | — |
| window | 1 | **distance matrix** `DIST[128][128]` | 16,384 | 0 |
| window | 4 | **world plane** 128×128×1 byte | 16,384 | 0 |
| window | 5 | **next-hop matrix** `NEXTHOP[128][128]` | 16,384 | 0 |
| window | 6 | `flip_mode0` 256 · dome+ring `nw` quadrants 7,424 · slot figures 3,456 · entity tables 4,832 ([§6.1](#61-entities)) | 16,096 | 288 |
| window | 7 | external structures 11,264 · plants 1,584 · `plant_ptr` 24 · text 1,024 · audio 2,048 | 15,944 | 440 |
| `&8000–&BFFF` | 2 | graphics, flat · node graph + BFS workspace 1,536 · recipes 110 · economy 58 · job board 160 | 14,848 | **1,536** |
| `&C000–&FFFF` | 3 | play-area screen | 16,384 | 0 |

Every bank is spoken for. The two matrices in banks 1 and 5 are the clearest answer
to "what is the extra 64 KB actually *for*": they turn pathfinding from a per-agent
search into a single table read ([§6.4](#64-routing)).

**Every bank now fits, and the numbers above are produced by `tools/pack.py`,
which lays the assets out for real and refuses to build if anything overflows.**
`tests/test_pack.py` then checks the result structurally and
`tests/test_pack_z80.py` draws from all three regions on real hardware. ASSET-3 landed exactly on its
3,456-byte budget, so bank 6 holds at 640 slack; the font was built at 4 px, so
bank 2 closes at 233 with the `s` room icons intact; and bank 7 came back from
2,608 over to **464 slack** by two decisions taken together:

- **`solar_xl` is gone** (−2,048). The solar panel now has three sizes, not four.
  `struct_dims` still reserves four slots per structure, so the fourth reads `0,0`.
- **The landing pad is opaque** (−1,024). It is a poured slab that *replaces* the
  terrain rather than sitting on it, so it needs no mask — the octagon is painted
  on a square pad instead of being cut out of one. Its corners cannot imitate
  terrain anyway, because the terrain pens change per planet.

Bank 7 was 48 bytes over even before the pad and ship arrived: the airlock's 512
was never added to this table when it was delivered. That is corrected above.

Slack is thin — about 1.3 KB across the three windows. The next cheap cuts, in order:
four plant species (528 B), the `s` room-icon set (864 B), moving `plants` into
bank 6. The font's lowercase is **not** on that list ([§4.3](#43-bank-2-flat-again)).

### 4.3 Bank 2, flat again

Bank 2 was designed to do two jobs at once: the HUD's screen page *and* the small
graphics, with the graphics bin-packed into eight 1,648-byte arenas threaded
between the HUD's screen rows. Nothing could straddle an arena, and the measured
result was **397 bytes free but fragmented across eight boxes, seven of them
completely full** — so nothing larger than 392 bytes could ever be added again.

**The raster split turned out to be impossible** ([§8.1](#81-screen-layout)), so
the HUD moved into the play area's page and bank 2 became **flat 16 KB**:

| In bank 2 | Bytes |
|---|---|
| Terrain tiles | 3,584 |
| Room icons, 12 types × 3 sizes | 4,800 |
| Machines, 10 types packed of 12 in the asset set | 1,320 |
| Corridors + connectors | 896 |
| 4×8 font, 96 glyphs | 1,536 |
| Asset tables | 289 |
| Generated pointer tables (`tile_ptr`, `icon_{s,m,l}_ptr`, `mach_ptr`) | 108 |
| Cursor and UI chrome (reserve) | 256 |
| Node graph (`node_deg`, `node_adj`) and BFS workspace | 1,536 |
| Machine recipes + the "needs an operator" lookup | 110 |
| Economy state — 14 stocks, flows, clock, weather | 58 |
| Job board, 32 × 5 | 160 |
| **Total** | **14,850** of 16,384 — **1,534 free, contiguous** |

The graph is here and not in bank 6 because the BFS pages the window twice per
source ([§6.4](#64-routing)). That 1,536 bytes is the first real claim on the space
the failed raster split gave back, and it would not have fitted in the arenas at all.

A failed technique that leaves the memory map simpler and nine times roomier is
a good trade. The pointer tables stay: they were introduced because
`room_icons_l` needs 2,400 contiguous bytes and an arena was 1,648, but they are
also **faster** than the `*200` and `*132` multiplies they replace, so there is
no reason to undo them.

### 4.4 `--quads nw` is mandatory

`assets/sprites.bin` is **36,864 bytes**, built with `--quads nw` — of which 7,424 are
dome and ring quadrants. The same set built with `--quads all` is 59,136 bytes, with
29,696 in quadrants. **The full build does not fit this memory map; the `nw` build
fits.**

> Earlier revisions of this section quoted 50,432 / 28,160. Those predate the terrain
> tiles (+3,584), the four room icons (+1,600) and the airlock structure (+512).

The cost is that `ne`, `sw` and `se` are generated at blit time — reversed pair order
and a `flip_mode0` lookup per byte, per `assets/SPRITES.md` §3. That is roughly 40%
slower for three quadrants out of four. Since dome quadrants are drawn only when a
dome is built or repaired — and that work is already spread over frames
([§6.9](#69-construction)) — 22 KB is worth far more than the microseconds.

**Done.** `--quads nw` is now the generator's default, *and* `sync-assets.sh` refuses
to copy a build that was not made with it — it checks for the header the generator
writes only in the `nw` build. A stray `--quads all` can no longer reach this repo
silently.

---

## 5. Procedural world generation

### 5.1 The contract

> Given the same *seed*, the same *planet type* and the same *generator version*, the
> generator produces a byte-identical 16,384-byte world plane, on any machine, every
> time.

Which requires, and the implementation must be reviewed against:

- No use of the gameplay RNG, the `R` register, the frame counter, or anything timing-dependent.
- No dependence on iteration order beyond what is written down here.
- No dependence on uninitialised memory.
- Every table size and threshold is a compile-time constant baked into the version.

**The generator is versioned**, and the version is displayed with the seed
(`A3F2·1`). Changing a threshold changes every world; that is fine, but it must be
visible, or a player's seed silently stops meaning what it meant.

### 5.2 The seed

A **16-bit seed**, entered and displayed as four hex digits — 65,536 worlds, and four
characters is about the most a CPC keyboard should ask for. A blank entry takes the
seed from the frame counter at the keypress.

Optionally the player may type a word instead, hashed to 16 bits; `HABITAT` should be
a good map, and it is worth hand-checking that it is.

The seed does three things:

1. Shuffles the 256-byte permutation table `P[]`.
2. Places the feature anchors ([§5.6](#56-feature-anchors)).
3. Seeds the gameplay RNG — which then **diverges immediately** and never touches the
   world again. Same map, different events, every playthrough.

### 5.3 The pipeline

Eight passes, all pure functions of the seed:

```
1  derive sub-seeds        xorshift-16 from the seed
2  build P[256]            Fisher–Yates with the seeded PRNG, page-aligned
3  synthesise elevation    pyramid noise -> bank 4          (§5.4)
4  synthesise moisture     pyramid noise -> bank 5 (scratch) (§5.4)
5  shape                   centre plateau + world rim        (§5.5)
6  stamp                   feature anchors, locally          (§5.6)
7  classify                elevation+moisture -> world byte  (§5.7)
8  clean                   despeckle, carve landing zone     (§5.8)
```

Passes 3 and 4 need somewhere to put a 16 KB field each. Bank 4 is the world plane's
final home; **bank 5 is borrowed as scratch** for moisture and rebuilt as the next-hop
matrix afterwards, since there is no network to route until the player builds one.

The hash underneath everything:

```
H(gx, gy) = P[ (P[gx & 255] + gy) & 255 ]
```

Two page-aligned lookups and two adds — about 8 µs. The seed is already folded into
`P[]`, so the hash needs no extra mixing, and it is **order-independent**: any lattice
point can be evaluated at any time without evaluating its neighbours first. That
property is what lets the generator be restarted, resumed, or run backwards for a
test.

### 5.4 One interpolated octave, not a pyramid

The textbook approach — three octaves of bilinear value noise at every one of
16,384 tiles — costs roughly 2,500 µs per tile on a Z80, or **41 seconds**.
Unusable. The pyramid described in earlier revisions of this section fixed the
speed but not the memory: upsample-and-add needs 5.4 KB of intermediate buffers,
and the last expansion cannot be done in place (the write head overtakes the read
head at output row 14), so it needs two 4 KB buffers — in a bank layout where
every bank is already spoken for ([§4.2](#42-the-eight-banks)).

**What is implemented instead:** one interpolated coarse octave plus two
uninterpolated fine ones.

```
coarse   16×16 lattice, cell = 8 tiles, bilinear      -> the shape of the land
+ H(x>>2, y>>2) >> 3                                  -> 4-tile texture
+ H(x>>1, y>>1) >> 4                                  -> 2-tile texture
- 23                                                   (the mean of the two)
```

Only the coarse octave is interpolated, and it is interpolated **incrementally**:
vertically once per row into a 16-byte lattice, then horizontally with an 8.8
fixed-point accumulator, because `acc >> 8` after *f* steps equals
`a + ((b-a)*f >> 3)` exactly. No multiply per tile, and the whole scheme needs
**256 bytes of scratch** instead of 8 KB.

The fine octaves are blocky by construction — 4-tile and 2-tile squares of noise.
That is acceptable precisely because the autotiler quantises every class boundary
to the tile grid anyway ([§8.3](#83-the-tile-pass)); texture below the tile is
invisible, and shape is what the coarse octave is for.

> **The one that bit.** The difference of two bytes lives in −255…255 and does
> **not** fit a signed byte. An early version computed `b - a` with an 8-bit
> `sub` and then sign-extended *that*, so 195 was read as −61 and whole cells
> ramped the wrong way. The comparison against the reference found it in one run;
> no amount of looking at the map would have.

### 5.5 Centre plateau and world rim

Two radial adjustments, both driven by **Chebyshev distance** `r = max(|x|, |y|)` — two
absolute values and a compare, no square root, and it gives a square falloff that
matches a square world.

| Band | `r` | Adjustment |
|---|---|---|
| Plateau | ≤ 5 | elevation forced to mid-ground — guaranteed flat buildable start |
| Blend | 6 … 10 | linear blend from forced to natural |
| Open world | 11 … 56 | untouched |
| Rim | 57 … 64 | elevation ramped up into mountain — an impassable natural border |

Both bands are a single lookup in a 65-entry table indexed by `r`. The rim matters
more than it sounds: without it the world ends in a hard cut where the plane runs out,
and the player can see the edge of the simulation. With it, the world ends in
mountains, the way worlds do.

### 5.6 Feature anchors

A seed has to be playable, and noise alone does not promise a lake within walking distance, and a seed with no
reachable water is a seed that cannot be played. Rejection-sampling the whole map is
too slow. So the features are **placed, from the seed, before the classification**:

Six anchors, derived from the seed as `(direction, radius, kind)`:

| # | Kind | Radius | Effect |
|---|---|---|---|
| 1, 2 | lake | 12 … 27 | elevation blended toward 0 → water |
| 3, 4 | ore ridge | **14** … 29 | elevation blended toward 255, ore in the inner half |
| 5 | flat basin | 8 … 15 | elevation blended toward mid |
| 6 | wildcard | 20 … 35 | lake or ridge, from the seed |

Direction is one of 24, assigned as `k*4 + (rnd & 3)` so each anchor gets its own
60° sector, and the anchor sits at distance ≈ its own radius from the centre.

**Three things here were learned by measuring, not by design:**

- **A ridge of radius 10 is not a ridge.** It never lifts elevation past `M2`, so
  it never becomes mountain, so it carries no ore — and the seed is unplayable.
  The minimum radius of 14 is what makes the guarantee true rather than intended.
- **Anchors must blend, not replace.** Asserting `e = min(e, MID - bump)` does
  guarantee the lake, but the ceiling bites across the *whole* neighbourhood —
  including where the bump is zero — and the lakes come out literally square. The
  implemented form weights toward a target: `w` reaches 255 at the centre (so the
  guarantee holds) and falls to 0 at the rim (so the noise draws the edge).
  `w = min(255, (rad - d) * (256 / rad))`, one division per anchor.
- **Distance is octagonal**, `max + min/2`. Chebyshev gives squares; Euclidean
  needs a square root; this is within about 6% of Euclidean for the cost of a
  shift.

Precedence — lake over ridge over basin — replaces application order. With the
anchor distance equal to its radius, two neighbouring sectors always overlap, so
whichever was applied last used to erase the other, and seeds lost their water.

Measured over 512 seeds: **512 of 512 have water and an ore vein within 30 tiles
of the centre.**

Because the anchors are a pure function of the seed, the map stays pure. A seed is
still one number, and the guarantee — *water and ore within 30 tiles, always* — holds
for all 65,536 of them.

### 5.7 Classification and planet types

Per tile, from elevation `e` and moisture `m`:

```
e < W2                     -> deep water
e < W1                     -> shallow water
e > M2                     -> mountain          resource bit if ore noise > O
e > M1                     -> rock
otherwise, m > F           -> ground, fertile bit set
otherwise                  -> dust
decor bits                 = H(x,y) & 3
```

Seven thresholds — `W1 W2 M1 M2 F O` plus the ore noise scale — and **the four planet
types are nothing but seven different threshold sets plus a palette**:

| Planet | Character | Thresholds | Palette |
|---|---|---|---|
| Desert | Baseline. Water scarce, ore common. | `W` low, `M` mid | ochres, orange rock |
| Ice | Water everywhere but frozen (extractors need power). | `W` high, `F` high | white, cyan, pale blue |
| Storm | Broken terrain, constant wind (turbines strong, solar weak). | `M` low → lots of rock | greys, browns |
| Barren moon | Almost no water, no fertile ground, ore everywhere. | `W` very low, `F` unreachable | greys, black, hard white |

One tile set, four looks. The same water tiles read as ice under the ice palette;
the same ground reads as regolith under the moon palette. This is the single cheapest
content multiplier in the design — four planets for about 60 bytes of threshold tables.

### 5.8 Cleanup and the landing zone

A single 4-neighbour majority pass over the plane removes isolated specks (a lone
water tile inside a mountain, a one-tile island) and enforces a minimum feature size of
four tiles. One pass, 16,384 tiles at ≈ 60 µs ≈ 1 second.

Then the landing zone is carved unconditionally: every tile with `r ≤ 4` becomes
**foundation** class, occupancy free, whatever the noise said. The starting pod is
placed at `(0,0)`.

### 5.9 Cost — measured

| Pass | Measured |
|---|---|
| Permutation, anchors, coarse grids | negligible |
| Row fields (2 × 128 rows) plus the bank dump | 2.9 s |
| Per-tile: octaves, anchors, shape, classify | **8.9 s** |
| Despeckle | 0.7 s |
| **Total** | **13.5 s** |

**The estimate in earlier revisions was 3.5 s. The truth is 13.5 s** — 3.9×,
timed by `tests/test_worldgen.py` on the emulator. The per-tile pass dominates at
541 µs per tile, which is ~2,200 T-states: three hash lookups, about thirty
`ld a,(nn)` round-trips at 16 T-states each, and four calls. The identified win
is holding `u`, `v` and the world pointer in registers across `gen_tile` and
inlining the hash — worth perhaps 2×, and not taken yet.

The generator is still written to run in slices with a real progress bar, and
13.5 s behind one is tolerable for a new game. **It is not tolerable on load** —
see [§5.10](#510-player-modification).

### 5.10 Player modification

Terrain changes during play — a mined-out mountain becomes rock, a meteor leaves a
crater, a dome site becomes foundation. These are **not** regenerable from the seed.

Earlier revisions logged them to a 1.5 KB delta list and **regenerated the world from
the seed on load**, replaying the deltas over it. That was a good trade against a
3.5 s generator. Against the measured 13.5 s ([§5.9](#59-cost--measured)) it is not: it buys
about 15 KB of disc space at the price of a quarter-minute stare on every single
load.

**So the plane is saved.** All 16 KB of it, verbatim, in the save file
([§11](#11-save-and-load)). Loading becomes a disc read — an estimated 4 s for
16 KB at typical CPC floppy throughput, not yet measured — and modified tiles need
no special handling at all, because there is nothing to replay them over.

The delta list is gone with them. It only ever existed to avoid storing the plane.

The determinism contract in [§5.1](#51-the-contract) still earns its keep: it makes
the generator testable, lets a seed be shared as two bytes, and keeps *new game*
reproducible. It just no longer carries the load path.
### 5.11 Testing determinism

The headless emulator at `~/cpcemu` makes this mechanical, and it should be a test
from the first day the generator exists:

1. Boot, generate the seed, dump bank 4 to a file via a debug hook. The hook is
   needed because **the emulator's `read_ram` does not follow paging** — at
   `&4000` it sees base bank 1, not bank 4. `tests/gentest.asm` walks the plane
   down into base bank 1 in 256-byte steps, alternating the page each step,
   since no configuration shows both at once.
2. Repeat on a cold boot. **The two dumps must be byte-identical.**
3. Keep a checked-in golden dump per generator version for a handful of seeds; any
   diff is either a bug or a deliberate version bump.
4. Render each golden seed to a PNG and eyeball it — a map can be deterministic and
   still be a bad map.

---

## 6. Simulation

### 6.1 Entities

**96 agents: 80 colonists + 16 bots.** The ceiling is the table, and the table is sized
so that a whole wheel revolution ([§7.2](#72-the-wheel)) fits in the frame budget. It
is also, for a CPC, a lot of people.

All entity data is **structure-of-arrays, page-aligned**. One array per field, agent id
as the index:

```
ld h, field_page
ld l, agent_id
ld a, (hl)          ; one field, one instruction
```

Two 128-entry fields share a 256-byte page (`ld l,id` and `ld l,id+128`). Sixteen fields
is eight pages, 2,048 bytes.

| Field | Meaning |
|---|---|
| `flags` | alive · indoors · asleep · sick · idle |
| `role` | worker · engineer · biologist · medic · guard · constructor bot · carrier bot · driller bot |
| `node` | node currently at, or source node if in transit |
| `slot` | ring slot 0–7 at that node |
| `dest` | final destination node |
| `edge` | **index 0–7 into the source node's adjacency list**, 255 = not in transit |
| `progress` | 0–255 along that edge |
| `task` | job board entry, 255 = idle |
| `o2 water food sleep health morale` | needs, 0–255 |
| `skill` | experience, feeds work speed |
| `spare` | |

`edge` was specified as a global corridor id. It is **the neighbour's slot in the
node's own adjacency list** instead, so the far end of the hop is one read
(`node_adj[node*8 + edge]`) rather than a search through 96 corridor entries. The
change costs nothing and is why `ent_move_one` has no loops in its arrival path.

Buildings use the same pattern:

| Table | Entries | Fields |
|---|---|---|
| Domes | 64 | `cx cy size room state integrity power ops machines[8] health[8]` — **24 bytes** |
| Structures | 64 | `cx cy kind size state integrity output` |
| Corridors | 96 | `a b dir len state` |
| Jobs | 32 | `kind target agent priority age` |

One table is missing from the list above and is not optional: **`node_occ`, one
byte per node**, the bitmask of which ring slots are taken. [§6.2](#62-the-node-graph)
describes 8 slots per dome filled in `corr_fill` order, which cannot be enforced
without it.

Measured, as laid out by `tools/pack.py`:

| Table | Bytes |
|---|---|
| `agent_fields` — 16 fields × 128, **must be page-aligned** | 2,048 |
| `node_occ` — slot bitmasks (128 used, 128 spare in the page) | 256 |
| Domes, 64 × 24 | 1,536 |
| Structures, 64 × 8 | 512 |
| Corridors, 96 × 5 | 480 |
| **Total in bank 6** | **4,832** |

`machines[4]` was specified, but `machine_count` in the asset data gives a large dome
**eight** slots. The record is 24 bytes so the large dome has the slots the art draws.
The `slots` field became `ops` — how many colonists are currently standing in this
dome's work positions, which is what decides whether its machines turn.

The **job board (160 B) and the economy state (58 B) are not in bank 6**: the job
board reads `DIST` out of bank 1 while it assigns, and the HUD reads the stocks every
frame. Both live in bank 2 with the routing workspace, for the same reason
([§6.4](#64-routing)).

384 bytes over the 4,096 this section used to claim. Bank 6 absorbs it and closes
at 640 free, because the BFS workspace that used to sit there moved out
([§6.4](#64-routing)).

### 6.2 The node graph

The colony is a graph, and almost every system reads it rather than the tile grid.

- **Nodes** (≤128): every dome, every external structure, the landing pad, and up to 8
  transient construction sites.
- **Edges**: a corridor between two domes; an *outdoor edge* from an airlock dome to an
  external structure or construction site. A dome has at most 8 edges — one per
  `conn_points` direction.
- **Node capacity**: 8 ring slots per dome (`corr_slots`), filled in `corr_fill` order
  `0,4,2,6,1,5,3,7` so people never look stacked; 1–2 work slots per external structure.

**In memory** the graph is a fixed-width adjacency list, because the Z80 wants the
neighbour list's address from one shift:

```
node_deg[128]      1 byte per node          128 B
node_adj[128][8]   neighbour ids, row n at node_adj + n*8   1,024 B
```

Both live in **bank 2**, with the BFS workspace, for the reason in
[§6.4](#64-routing). 1,152 bytes.

External structures are never corridor-connected. Reaching one means leaving through an
airlock and walking — which is exactly why airlock placement is a real decision, and why
a sandstorm that kills people outdoors has teeth.

#### The airlock is now a structure too — and that is a choice to make

The asset set has gained a standalone **`airlock` structure**: 16×32 px (one tile wide,
two tall), masked, with two opposed doors and a hazard band, symmetric top-to-bottom so
a corridor can meet it from either side. This document was written when `airlock` was
only a *room type* — a whole dome spent on being a door.

Two readings, and they are not compatible:

| | Airlock is a **dome** (as written) | Airlock is a **structure** (new sprite) |
|---|---|---|
| Cost to the player | a whole dome, 1–8 machine slots wasted | one tile, cheap |
| Node graph | an airlock dome is an ordinary node | the **only** corridor-connected external structure |
| Placement decision | which dome to sacrifice | where the base meets the outside |
| Art | `icon_airlock` inside a dome | the structure sprite |

**Recommendation: the structure.** It is how Planetbase does it — the wiki notes an
airlock connects to exactly one interior structure — and it stops a 6×6-tile dome being
spent on a doorway. The `airlock` room type and its three icons then become redundant
and could be reclaimed (index 7, 400 bytes across the three sizes), though leaving them
costs nothing and keeps every index stable.

Until this is decided, the `airlock` structure sprite ships unused. It is
[§15](#15-open-risks).

### 6.3 Movement

An agent is in one of two states, and nothing else:

```
AT    node n, slot s        drawn: one 16-byte opaque blit at corr_slots[n][s]
TRANS edge e, progress p    drawn: optional walker sprite, or nothing (in the tube)
```

A movement update is:

```
if AT and dest != node:      claim edge NEXTHOP[node][dest], free slot, -> TRANS
if TRANS:                    p += speed
                             if p overflows: arrive, claim slot at far node -> AT
```

Two cases the sketch above leaves out, both of which the implementation has to
answer and neither of which is a special case:

- **The far node is full.** All 8 ring slots taken, so there is no slot to claim.
  The agent stays in `TRANS` with `progress` pinned at 255 and retries next
  revolution — it queues at the door. Deterministic, and it reads as a crowded dome.
- **`NEXTHOP` says unreachable.** The agent sets `dest = node` and gives up rather
  than standing still forever with an impossible order. This is what happens to
  anyone whose destination was cut off while they were walking to it.

**Measured at 130 µs per agent** (`tests/test_sim.py`), against the 150 µs estimated
here — one of the few numbers in this document that came in under. A full movement
slot of 12 agents is 1,560 µs against the 1,800 µs budgeted in
[§7.2](#72-the-wheel). No pathfinding, no collision,
no steering. **The art forced this and the art was right** — colonists in
`assets/sprites.bin` exist only as ring-slot figures, and the empty variant of a slot
restores exactly the pixels underneath it, so appearing and disappearing are both a
single opaque blit with no mask and no dome redraw (`assets/SPRITES.md` §5).

`speed` comes from role, terrain (outdoor edges are slower in a storm) and bot type,
and is **scaled by the wheel's current slice size** ([§7.3](#73-degradation)) so that
apparent walking speed does not change as the colony grows.

**Walkers.** Up to 12 agents on visible edges are drawn as a 4×8 figure interpolated
along the edge, with a 16-byte background save and restore. Four blits of 16 bytes each
per walker per step ≈ 256 µs for all twelve. Worth it: a base where nobody is visibly
walking between domes looks dead.

### 6.4 Routing

Two 128×128 byte matrices, a full 32 KB of the extra RAM:

| Matrix | Bank | `[from][to]` holds |
|---|---|---|
| `NEXTHOP` | 5 | the next node to step to, 255 = unreachable |
| `DIST` | 1 | hop count, 254 = far, 255 = unreachable |

Both rows come out of **one** breadth-first traversal per source, not two: when the
search first reaches a neighbour of the source, that neighbour *is* the first step;
every node discovered later inherits the first step of whoever discovered it. No
second pass, no stored paths.

Runtime routing is therefore **one table read**. Finding the nearest idle engineer to a
broken machine is a scan of idle agents with one `DIST` read each. There is no A*, no
open list, no per-agent path storage, and no frame-time spike when twenty people
re-path at once.

#### The workspace cannot live in a paged bank

The BFS writes its finished row into bank 1 *and* bank 5, so the `&4000` window
changes twice per source. Anything the search reads must therefore be **outside the
window**. The graph and the 384-byte workspace live in **bank 2**, which is always
visible — 1,536 bytes of the space [§4.3](#43-bank-2-flat-again) freed. Earlier
revisions put a "path workspace" in bank 6; that could not have worked.

#### The cost, measured

The estimate here was 1,024 relaxations per source × 30 µs. **Both halves were the
wrong thing to count.** Measured by `tests/test_routing.py`:

| Graph | Nodes | Avg degree | Full rebuild |
|---|---|---|---|
| Realistic colony | 48 | 2.2 | **0.62 s** |
| Sparse, at the node cap | 128 | 2.0 | 3.55 s |
| **The real ceiling** | 128 | 2.5 | **3.69 s** |
| (Degree 8 everywhere — cannot happen) | 128 | 8.0 | 5.03 s |

The last row is unreachable: the corridor table has **96 entries**
([§6.1](#61-entities)), and external structures are never corridor-connected, so the
graph cannot exceed 128 nodes with ~160 edges. Average degree tops out near 2.5, not 8.

That changes what dominates. The cost is not the edge relaxations — it is **taking a
node off the queue**, which happens `n` times per source and therefore **n² times per
rebuild**:

> **222 µs per node expansion, O(n²).**

| Colonists' worth of nodes | Full rebuild, CPU |
|---|---|
| 16 | 0.06 s |
| 32 | 0.23 s |
| 64 | 0.91 s |
| 128 | 3.64 s |

A young colony re-routes in a blink; only a maxed-out one pays seconds. Sources run
`0 .. n-1` where `n` is the **high-water node id + 1** — a demolished dome keeps its
id with degree 0 and its row correctly comes back "unreachable from everywhere", so
ids never need compacting and no 32 KB initialisation pass is needed.

The rebuild is **sliced by node expansion**, not by source: one source is 28 ms and
would blow the frame on its own. `rt_slice` takes a budget in expansions and
suspends anywhere, with four bytes of state.

At the 12-expansions-per-frame budget of [§7.2](#72-the-wheel) that is 3.8 s of
wall-clock for a 48-node colony and about 27 s for a full one. During that time the
old matrix stays live and agents route on slightly stale
information. Building a corridor and watching traffic start using it a few seconds
later is acceptable, and arguably reads as the colony reorganising. Destroying one is
not acceptable to get wrong, so **edges carry a live `state` byte**: an agent about to
enter a dead edge re-checks, and waits or re-routes. Stale routing is allowed to be
inefficient, never to be invalid.

### 6.5 Economy

Two **flows**, buffered and balanced every wheel revolution:

| Flow | Produced by | Consumed by | Failure |
|---|---|---|---|
| Power | `solar` (day only), `turbine` (wind), stored in `collector` | every machine, lighting at night | machines stop, then oxygen stops |
| Oxygen | `mach_oxygen` (small domes only) | every colonist, leaks | health drains, fast |

**Fourteen stocks**, 16-bit, capped by storage-dome capacity:

`Water · Food · Ore · Metal · Bioplastic · Processors · Spares · Medicine · Guns · Bots`
`· Starch · Vegetables · Medicinal · Vitromeat`

This section originally listed ten. The chain immediately below it consumes
**Starch, Vegetables, Medicinal and Vitromeat** — none of which were on the list, so
the greenhouse produced into nothing and three machines had no input. The four
intermediates are stocks like any other.

The chain, using the machines that exist in `assets/sprites.bin`:

```
extractor  (on water)      -> Water
mine       (on ore)        -> Ore                       needs 2 drillers
mach_iron      Ore         -> Metal
mach_bioplastic Starch     -> Bioplastic
mach_processors Metal      -> Processors
mach_spares    Metal+Bioplastic -> Spares
mach_robots    Metal+Processors+Bioplastic -> Bots
mach_weapons   Metal+Processors -> Guns
mach_medical   Medicinal plants -> Medicine
mach_vitromeat Water+Power -> Vitromeat (food, meat)
mach_food      Starch+Veg+Vitromeat -> Meals
mach_oxygen    Water+Power -> Oxygen flow
greenhouse plants          -> Starch / Vegetables / Medicinal / morale
```

Each machine type has one **recipe record** — `in1, qty1, in2, qty2, in3, qty3, out,
qty, power, flags` — **ten** bytes, 100 bytes for the lot. Eight was specified, with
two inputs; `mach_robots` and `mach_food` on the same page need three. Twenty bytes
buys the contradiction away.

`flags` carries `MF_OPERATOR` (the machine needs someone standing in its slot) and
`MF_FLOW` (the output is a flow, not a stock — only `mach_oxygen`).

The production tick is a table walk, not a switch statement, which is both smaller and
much easier to rebalance. It is generated into bank 2 by `tools/pack.py` straight from
`tools/econ.py`, so the reference implementation and the ROM data cannot drift apart.

**The two economy slots read each other one revolution late.** Production tests
`power_ok`, which the flow balance set last revolution; the flow balance uses
`mach_power`, which production published at the end of its last four-revolution sweep.
Without that buffer each slot would need the other's answer inside the same frame.
This section already said *buffered*; this is what it buys.

`machine_rules` in the asset data already constrains placement: `mach_oxygen` is
`bit0` only, meaning **oxygen generators fit only in small domes**. That is honoured as
a design constraint rather than patched around — it forces a spread of small life-support
domes rather than one oxygen cathedral, which is a better-shaped base.

First-pass balance, per sol (one sol = 4 real minutes):

| | Produces | Consumes |
|---|---|---|
| Colonist | — | 2 O₂, 2 Water, 1 Meal |
| `mach_oxygen` | 20 O₂ | 4 Power, 1 Water |
| `solar` s/m/l/xl | 2 / 8 / 18 / 32 Power | daylight only |
| `turbine` s/m/l | 3 / 12 / 27 Power | wind-dependent |
| `collector` s/m/l | stores 40 / 160 / 360 Power | |
| `extractor` s/m/l | 6 / 24 / 54 Water | 2 / 6 / 12 Power |
| `mine` | 20 Ore | 8 Power, 2 drillers |
| Greenhouse slot | 3 Starch / 2 Vegetables / 2 Medicinal, by `plant_class` | 1 Water, 1 Power |

These numbers are a starting point for tuning, not a balance claim — and three of
them turned out to be unlivable the first time the whole loop ran
([§6.6](#66-needs)).

**A greenhouse keeps plants in the same slots another dome keeps machines.** Same
field, different meaning, and the room type says which. `plant_class` decides the
output: starch, vegetables, medicine, or nothing at all for a tree, which is there for
morale. Every plant needs tending, so a greenhouse posts as many `Operate` jobs as it
has plants — biologists are what make it grow.

### 6.6 Needs

Six per colonist, decaying on the wheel: **oxygen, water, food, sleep, health, morale.**

- **Oxygen is a flow, not a journey.** Anyone inside the colony breathes its air: if
  `o2_ok`, oxygen refills; if life support is short, it drains and health follows fast.
  Nobody walks anywhere for it.
- Water and food are satisfied **at a canteen**, consuming the stock. Sleep is
  satisfied **in quarters**. Health is repaired **in a medbay**, consuming Medicine.
- Below `NEED_LOW` (64) the colonist goes looking. Below `NEED_CRIT` (16) health
  drains — 4/visit for oxygen, 2 for water, 1 for food. At health 0 they die.
- **Death** releases their ring slot, drops their job, takes their operator count off
  the dome, and raises colony-wide `gloom`, which pulls everyone's morale down until
  it decays away. Morale otherwise rises when everything is fine and falls when
  anything is critical.
- §10.3's only loss condition — everyone dead — is set by the flow pass, which is
  already counting the living for the oxygen demand.

#### Their own needs outrank the board

A colonist below a threshold **drops the job they were assigned** and walks off. The
job board's reap step notices and gives the work to someone else. Priority order is
health, food, water, sleep. That single rule is what makes a colony feel like people:
at some point everyone puts down what they are doing and goes to eat, and if the
canteen is on the far side of the base you will watch production die of walking.

#### Finding the right room

"Nearest canteen" would be a scan of 64 domes with a `DIST` read each — 1,300 µs per
hungry colonist. Instead the **free slot 14** rebuilds a room index once per
revolution: up to 8 domes per room type, 108 bytes. The search is then eight reads.
Slot 14 was emptied when routing left the wheel ([§7.2](#72-the-wheel)); this is what
moved into it.

A colonist already walking toward a room of the right type is left alone. Without
that check every colonist re-ran the search on every visit.

#### What the first working colony cost

This section estimated "six bytes of decay per colonist per visit, ≈ 40 µs. Cheap; the
expensive part is *deciding what to do about it*, which is the job board's problem."
Both halves were wrong. The deciding is **not** the job board's problem — that hands
out work, it does not send people to dinner — and the full pass measures **337 µs per
colonist**, not 40. There is no single hotspot; it simply does a great deal.

So the slice shrank, which is exactly the lever [§7.3](#73-degradation) describes:
**8 colonists per slot, 24 per revolution, each visited every fourth revolution.**
That is also *more* faithful to the economy in [§6.5](#65-economy), which gives a
colonist 2 water per sol: a 255-point bar now lasts about one and a half sols instead
of forty seconds.

**Three balance numbers had to change the first time the whole loop ran**, and all
three were wrong in the same direction — they made the colony unlivable:

| | Was | Now | Why |
|---|---|---|---|
| Decay per visit | 3 / 2 / 1 / 2 | 1 each | Six times faster than [§6.5](#65-economy)'s own per-sol figures |
| Walking speed | 40–64 | 88–144 | An edge took 6 revolutions; a 5-hop trip lasted as long as the need that sent you |
| Oxygen per colony | 2 generators | 10 | 40 O₂ against 192 demanded: everyone quietly asphyxiating from frame one |

With the first set, **no colonist ever reached a workplace** — the entire population
spent its life commuting. That is not something a budget or a unit test would have
caught; it only appears when the loop actually closes.

**Variety is deliberately not implemented.** This section wanted three hidden counters
per colonist so that eating one crop caps health. The trap it exists to create is
already enforced one level earlier: `mach_food` needs **Starch and Vegetables and
Vitromeat** together, so a one-crop greenhouse cannot produce a meal at all. A second
mechanism for the same lesson would cost 384 bytes and teach nothing new.

### 6.7 Jobs

A **32-entry job board**. Buildings post jobs; idle agents claim them.

| Kind | Posted by | Claimed by |
|---|---|---|
| Build | a construction site | engineer, constructor bot |
| Operate | a machine with inputs and no operator | worker, biologist (greenhouse) |
| Haul | a structure with output, or a machine short of input | worker, carrier bot |
| Drill | a mine with a free work slot | worker, driller bot |
| Repair | a damaged machine or structure | engineer |
| Heal | a sick colonist | medic |
| Defend | an intruder alert | guard |
| Rest / Eat / Drink | the colonist's own needs | anyone, highest priority |

Assignment is: for each idle agent, take the highest-priority compatible job, breaking
ties by `DIST[agent.node][job.node]`. Bounded at **4 assignments per visit**, examining
at most **32 agents** and posting from at most **4 domes**, so the pass cannot spike.

**A node id *is* a dome id** for ids 0–63, and structure `n − 64` above that. 64 + 64
is exactly the 128-node ceiling of [§6.2](#62-the-node-graph). Without this convention
there is no way to get from "job at node 12" to "dome 12", and the section never said it.

The pass does four things, in this order, and the order is the design:

1. **Reap** — anyone who died or changed their mind leaves the job open again.
2. **Arrive** — anyone standing on their job's node starts working: the dome's `ops`
   goes up and its machines begin to turn. *This is where the loop closes.* Without
   it the job board is a list that never does anything, and the test that proves the
   colony responds to people is the one that watches `ops` rise (61 → 64 over 40
   revolutions) and the power draw rise with it.
3. **Post** — 4 domes per visit, round-robin, one `Operate` job per dome that is short
   of operators.
4. **Assign** — as above.

Leaving is the mirror of arriving and lives in the movement pass: an agent with
`F_WORKING` that starts down an edge decrements the dome's `ops` on the way out.

**The steady state is the expensive one, not the busy one.** When every job is taken,
each idle agent still scanned all 32 entries to find nothing — 36,442 µs per visit,
nearly twice a frame. One pass over the board, before the agent loop, asking only
*is there any unassigned job at all*, brings it to 6,490 µs.

A colonist's own needs always outrank the board. That is the rule that makes the
colony feel like people rather than machines: at some point everyone puts down what
they are doing and goes to eat, and if the canteen is on the far side of the base you
will watch your production die of walking.

### 6.8 Rooms, machines, plants

A dome has a **size** (s/m/l), a **room type**, and 1 / 4 / 8 machine slots
(`machine_count`). The room type decides what may go in the slots and which icon is
drawn (`assets/SPRITES.md` §4).

| Room | Icon | Slots hold | Function |
|---|---|---|---|
| Empty | `empty` | — | unassigned / under construction |
| Control | `control` | `processors` | call ships, radar warning, colonist cap |
| Quarters | `quarters` | — | sleep capacity 2 / 6 / 12 |
| Canteen | `canteen` | `food` | meals, morale |
| Oxygen | `oxygen` | `oxygen` (small domes only) | life support |
| Greenhouse | `greenhouse` | 12 plant species | starch, vegetables, medicine, morale |
| Storage | `storage` | — | stock capacity 100 / 300 / 600 |
| Airlock | `airlock` | — | the only route outdoors — **but see [§6.2](#62-the-node-graph)**: this may become a structure instead of a dome |
| **Factory** | `factory` | `iron`, `bioplastic`, `spares`, `robots`, `weapons` | refining and manufacture |
| **Lab** | `lab` | `processors`, `medical`, `vitromeat` | medicine, printed meat, high-tech goods |
| **Medbay** | `medbay` | `beds`, `medstore` | healing, medicine stock |
| **Lounge** | `lounge` | — | morale |

All twelve icons exist ([ASSET-2](#12-asset-gaps), delivered), and the **Slots hold**
column is no longer prose: `room_machines + type*2` in the asset data is a 12-bit mask
of exactly this table, and the generator refuses to build if a machine has no room. A
machine may sit in more than one room — `processors` is in both Control and Lab.

Two machines were added to the asset set for the medical chain: **`beds`** and
**`medstore`** in the Medbay. The medicine bench and the meat printer already existed
as `medical` and `vitromeat` — those names describe the *product*, not the machine,
which is why they read as missing. They were **not** renamed: `tools/pack.py` and
`tools/econ.py` hold the list by name and a rename would break a working build. The
ten existing indices are unchanged; the two new machines are appended at 10 and 11,
so nothing shifts.

**Neither is packed yet.** `MACH` in `tools/pack.py` and `tools/econ.py` still lists
ten, so bank 2 is unchanged apart from `machine_rules` growing by two bytes. Adding
them costs **292 bytes**: 264 for the two sprites, 4 for `mach_ptr`, and 24 for
`room_machines` if that table is packed too — against 1,534 free, so it fits.

### 6.9 Construction

1. Player places a ghost. Validation: every footprint tile must be `ground`, `dust` or
   `foundation`, occupancy free, and (for domes) at least one corridor route must be
   possible. Invalid tiles are tinted; the ghost cannot be committed while any is.
2. On commit: footprint tiles become `foundation`, occupancy `reserved`; a construction
   site node is created; a Build job is posted; the cost in Metal / Bioplastic is
   *reserved*, not yet spent.
3. Engineers and constructor bots walk there and work. Progress is a byte.
4. On completion the object is drawn — and this is the expensive moment: **5.7 frames
   for a large dome** ([§2.2](#22-the-frame-budget)). It is split into 8 chunks, one
   quadrant per frame, in the order of `assets/SPRITES.md` §8: rings, domes, connectors,
   room icon, machines, slots. The dome appears over about a sixth of a second, which
   reads as materialising rather than as a stall.

### 6.10 Events and hazards

One check per wheel revolution (≈ 3 Hz), from the gameplay RNG — which is **separate
from the world generator's**, so the weather can never change the terrain a seed
produces.

| Event | Attacks | Countered by | Built? |
|---|---|---|---|
| Night | solar output = 0 for ~40% of each sol | collectors, turbines | ✅ |
| Sandstorm | solar output = 0; anyone outdoors loses health | turbines, collectors, indoor work | ✅ |
| Malfunction | one machine stops dead | engineer + 1 Spare | ✅ |
| Solar flare | three machines stop at once | spares, engineers | ✅ |
| Meteor shower | random structures destroyed, **crater tiles written to the world plane** | spread-out building, spares | ✗ |
| Intruders | arrive at the map edge, walk in, attack | guards, guns, airlock placement | ✗ |

Meteors and intruders are **not built**, and for the same reason: both need something
outside the simulation. Meteors write terrain, which means the world plane and the
dirty list that redraws it; intruders need agents that spawn at the map edge and a
notion of combat. Both belong after the renderer, not before it.

**A malfunction is not "damaged a bit": the machine's health goes to zero and stays
there** until an engineer arrives with a Spare. That is what closes the loop — the job
board posts the repair itself, and repair outranks staffing, because a stopped machine
does not need an operator, it needs a mechanic. The engineer arrives, spends the part,
and leaves; unlike an operator they do not stay.

Sandstorms hurt **anyone standing at an external structure**. That is precisely what
makes airlock placement a real decision ([§6.2](#62-the-node-graph)) rather than
decoration.

#### Three rolls, always, and each reads a different part of the number

The events tick always draws three values, whether it needs them or not: a conditional
roll would make the sequence depend on the previous outcome, and reproducibility would
become work.

The first version then tested the **low bits of two consecutive draws** — and a Galois
LFSR shifts right, so consecutive draws are very nearly the same number moved along.
The storm roll and the malfunction roll were reading almost the same bits, so they
fired together or not at all. Each test now reads a different field: low bits of the
first for wind, **high** bits of the second for storms, low bits of the third for a
malfunction and its high bits for a flare.

### 6.11 Ships and arrivals

A Control room lets you call ships to the landing pad:

- **Colonist ship** — you request a *mix* of roles; that is the only control you have
  over who you get. Costs nothing but takes time to arrive.
- **Merchant ship** — trade surplus stock for what you cannot make yet. This is the
  early-game lifeline and the mid-game trap: a colony that trades for spares forever
  never builds a factory.
- **Visitors** — arrive unbidden, consume resources, raise morale, leave. Manageable
  when things are going well, a genuine insult when they are not.

Ships need a landing pad sprite that does not exist yet — [ASSET-5](#12-asset-gaps).

---

## 7. The batch scheduler

This section is the load-bearing one. Every cost in this document was computed so that
it could live here.

### 7.1 The rules

1. **No subsystem may do unbounded work in one frame.** Every pass declares a maximum
   item count and a measured worst-case microsecond cost.
2. **Work is sliced by identity, not by time.** Agents 0–11 this frame, 12–23 the next.
   Never "as many as fit", which makes the sim depend on how long the last frame took.
3. **Order is fixed.** Ids are always processed in ascending order, phases always in
   wheel order. The simulation is reproducible, which makes bugs reproducible.
4. **The sim clock is allowed to slow; the frame rate is not.** A CPC that drops frames
   feels broken. A colony that thinks a little more slowly when it has eighty people in
   it feels like a colony with eighty people in it.

### 7.2 The wheel

**Sixteen slots, one advanced per frame. A full revolution is 16 frames = 320 ms ≈ 3.1 Hz.**

| Slot | Pass | Slice | Budgeted | **Measured** |
|---|---|---|---|---|
| 0–7 | Agent movement | 12 agents each | 1,800 µs | **1,298 µs** ✅ |
| 8–10 | Needs, health, death, deciding | 8 colonists each ([§6.6](#66-needs)) | 433 µs | **2,796 µs** ❌ 6.5× |
| 11 | Production, machines and plants | 16 domes | 4,000 µs | **6,290 µs** ❌ 1.6× |
| 12 | Flow balance | 64 structures, plus counting the living | 2,000 µs | **5,891 µs** ❌ 2.9× |
| 13 | Job board — reap, arrive, post, assign | 4 domes, 32 agents | 3,000 µs | **4,892 µs** ❌ 1.6× |
| 14 | Room index and amenity ([§6.6](#66-needs)) | 64 domes | *(was empty)* | **5,391 µs** |
| 15 | Events: clock, weather, hazards ([§6.10](#610-events-and-hazards)) | three rolls | 500 µs | **200 µs** ✅ |
| — | wheel dispatch itself | every frame | — | **94 µs** |

**A whole revolution costs about 68,000 µs spread over 16 frames — a fifth of the
machine — and the worst single frame is 6,290 µs, under a third of one.** That is the number the
design lives or dies by, and it has room.

Five of the seven budgets were low, by 1.3× to 6.2×. The one pass that came in under
budget is the one whose cost was derived from a measured blit rather than guessed.
**Budget the remaining passes pessimistically.**

#### These numbers are measured directly, not by difference

Earlier revisions of the test ran the wheel with one pass switched off and took the
difference. That stopped being valid the moment the passes began to depend on each
other: with movement disabled nobody ever arrives anywhere, so the needs pass sees a
completely different colony and its "cost" came out at 12,646 µs instead of 2,696.
The test now **pins the wheel to one slot** and runs it 200 times.

#### Routing is not a wheel slot any more

This section used to give the routing rebuild slot 14. A slot runs **once per 16
frames**, and at a measured 222 µs per node expansion with n² of them
([§6.4](#64-routing)), a full colony would need minutes. So the rebuild is taken out
of the wheel and given a **per-frame budget**, exactly like the dirty list: 12 node
expansions every frame, ≈ 2,700 µs, and only while the graph is dirty.

Slot 14 was left empty rather than renumbered, so every other slot kept its number.
The room index of [§6.6](#66-needs) has since moved into it.

Every frame, regardless of slot:Every frame, regardless of slot: read input, move cursor and camera, advance the dirty
list ([§8.5](#85-the-dirty-list)) up to a 20,000 µs cap, tick animation, service audio.

The worst *frame* is a production slot during a routing rebuild: 6,290 + 2,700 + 94
≈ **9,200 µs, under half the frame**. That leaves 10,800 µs for rendering — and a
single scroll column costs 9,300 µs ([§8.3](#83-the-tile-pass)). **The two together
very nearly fill the frame**, which is exactly why the dirty list is a *budget* rather
than a queue that must be drained: on a frame where the sim is heavy, the scroll edge
takes two frames instead of one.

### 7.3 Degradation

The wheel length is fixed at 16. As the colony grows, **slices grow, not the wheel**:

| Colonists | Agents per movement slot | Effective update rate |
|---|---|---|
| 20 | 4 | 3.1 Hz |
| 50 | 8 | 3.1 Hz |
| 80 + 16 bots | 12 | 3.1 Hz |

**The needs pass has already taken this lever**, and not because the colony grew: one
visit costs 337 µs per colonist, so three slots of 32 would not fit comfortably in a
frame. It runs 8 per slot and visits each colonist every fourth revolution
([§6.6](#66-needs)). Nothing else changes — needs simply last four times longer, which
the economy wanted anyway.

— because the slot count is fixed, every agent is still visited once per revolution.
The cost per slot rises from ≈ 600 µs to ≈ 1,800 µs, which the budget absorbs. If the
ceiling were ever raised past 96 the correct move is to visit each agent once every
*two* revolutions and double `speed`, so apparent walking pace is unchanged and only
the sim's decision latency degrades.

### 7.4 Batched work outside the wheel

Four more things are sliced, for the same reason:

| Work | Slicing | Total |
|---|---|---|
| World generation | one pyramid level or one classify chunk per frame | **13.5 s measured**, with a real progress bar — new game only ([§5.9](#59-cost--measured)) |
| Routing rebuild | 12 node expansions per frame, **not** a wheel slot | 3.8 s at 48 nodes, ~27 s at 128 ([§6.4](#64-routing)) |
| Dome construction blit | one quadrant per frame | ≈ 8 frames |
| Camera redraw after a jump | one tile column per frame | ≈ 20 frames |

---

## 8. Rendering

### 8.1 Screen layout

```
lines   0 .. 159    play area   80 bytes × 160 lines  = 20 × 10 tiles
lines 160 .. 199    HUD         80 bytes ×  40 lines  =  5 char rows
```

**Both halves come from the same page** — bank 3 at `&C000`. Earlier revisions
put the HUD on its own CRTC page and switched `R12` at a raster split on line
160. **That does not work, and it has been proven not to work**
(`tests/test_camera.py`):

> The 6845 latches its display start address **once per frame**. A write to
> `R12`/`R13` in the middle of a frame changes nothing until the next one.

The measurement is trustworthy because the test carries its own control: at the
*same* point in the frame it writes the **border** colour instead, and the border
changes at exactly line 160. The timing lands where it is aimed; the CRTC simply
ignores a mid-frame start address.

**What follows from that:**

- The HUD occupies the last 5 character rows of the same 1,024-word ring as the
  play area. When the camera scrolls, the ring rotates, and the HUD's *memory*
  moves even though its *screen position* does not. So the HUD must be
  **re-rendered after every scroll step** — at its new addresses, same pixels.
  Estimated ≈ 0.4 frames (roughly 1.2 KB of glyph and bar blits); to be measured
  when the HUD renderer exists.
- **Bank 2 stops being a screen page**, which is the good news hiding in the bad.
  It becomes a flat 16 KB of data ([§4.3](#43-bank-2-flat-again)).

**The escape hatch, if the re-render cost proves too high**, is *rupture*:
manipulating `R4`/`R9` to make the CRTC end the frame early and restart it
mid-screen, which does reload `R12`/`R13`. It is the standard CPC technique for a
true split, and it is deliberately not taken here — it is timing-critical and
behaves differently across CRTC types 0–4, so a HUD built on it would work on
some real machines and not others.

### 8.2 Camera

The camera moves in **whole tiles**, implemented entirely as a CRTC display-offset
change. **Measured on the emulator** (`tests/test_camera.py`):

| Step | Offset change | Measured |
|---|---|---|
| One offset word | +1 | image moves **exactly 4 Mode 0 pixels** (2 bytes) |
| One tile east/west | ± 2 words | 8 px |
| One tile south/north | ± 80 words (2 × `R1`) | 16 lines |

Offsets 1, 2, 4 and 8 were checked against the predicted pixel position and all
four matched to the pixel. **This half of §15's top risk is confirmed**: scrolling
costs a display-register write, not a redraw.

Then **only the newly exposed edge is drawn** — one column (0.47 frames) or one
row (0.93 frames), measured in [§8.3](#83-the-tile-pass) — plus the HUD
re-render that [§8.1](#81-screen-layout) now requires. Call it ≈ 0.9 frames per
horizontal tile step against the 9.3 frames a full redraw would cost.

Half-tile steps are possible (1 word, 40 words) and are what the position unit is
built for, but they leave a half-visible tile at two edges and need a partial-tile
blit variant. **Not taken now**; whole-tile steps keep the tile pass free of
clipping.

The 16 KB page wraps — the ring is 1,024 words — so the newly exposed strip's
addresses wrap too. The blit computes addresses from the current offset anyway,
so this is bookkeeping rather than a new mechanism.

### 8.3 The tile pass

Per tile: read the world byte from bank 4, unpack class and decor, read the four
orthogonal neighbours, index a 16-entry autotile table, and blit 4 bytes × 16 lines
opaque.

The line stepping is *not* nearly free, which is where the original estimate went
wrong. Within a character row line *n+1* is at *+&800*, so the high byte alone
advances — but **`ldi` increments DE, and when a tile's four bytes straddle a
256-byte boundary the low byte wraps and carries into the high byte.** An early
version saved only the column byte and restored it, leaving the carry in place;
the destination then drifted one page per line and wrote into the engine's own
code and stack. It survived an isolated test because the address chosen for that
test did not straddle. The whole of DE must be saved and restored — 24 T-states
per line that are not negotiable.

Measured cost, from `tests/test_tiles.py`:

| | µs per tile |
|---|---|
| `blit_tile` plus the column loop | 579 |
| class, variant, autotile, ore overlay | 350 |
| **total** | **929** |

A scroll step costs one column — 0.47 frames — which is the number that matters,
and it is comfortable. A full redraw is 9.3 frames and is already sliced
([§7.4](#74-batched-work-outside-the-wheel)).

**If it ever needs to be faster,** the identified win is blitting *tile pairs*:
eight bytes per line instead of four halves the per-line overhead per byte, worth
about 19% of the blit. It is not taken now — the viewport is 20 tiles wide so
pairing divides evenly, but it couples adjacent tiles' source lookups and the
current cost does not justify that.

Objects covering a tile (occupancy ≠ 0) still get their terrain drawn first; the dome
and structure sprites are masked and composite over it, which is exactly what those
masks were made for (`assets/SPRITES.md` §2). Pen 0 is both the background and the
transparent colour, so terrain shows through the gaps between a dome and its ring
without a single extra byte of art.

### 8.4 Object pass and draw order

Per `assets/SPRITES.md` §8, for each dome, back to front:

```
1  ring quadrants        masked
2  dome quadrants        masked     (never overlaps 1 — order between them is free)
3  connectors            masked     only on sides that have a corridor
4  room icon             opaque     at interior_ofs
5  machines or plants    opaque     at machine_slots
6  colonist slots        opaque     at corr_slots, in corr_fill order
```

Corridors are drawn between steps 2 and 3 of the domes they join. External structures
are drawn after all domes, sorted by `cy` so that southern structures overlap northern
ones.

### 8.5 The dirty list

After the initial draw, **nothing is redrawn unless it changed.** A 32-entry ring of
`(kind, id)` records what changed; the renderer knows the minimal redraw for each kind,
straight out of `assets/SPRITES.md` §8:

| Change | Redraw | Cost |
|---|---|---|
| Colonist enters or leaves a slot | one slot | 64 µs |
| Machine changes state or breaks | one machine | 530 µs |
| Plant grows a stage | one plant | 530 µs |
| Room type changes | one icon | ≈ 800 µs |
| Corridor added | one connector | ≈ 450 µs |
| Terrain tile changes (mine, meteor) | one tile + 4 neighbours' autotiles | ≈ 1,600 µs |
| Dome built | everything, sliced over 8 frames | 1.4 – 5.7 frames |

The list is processed under a **20,000 µs per-frame cap** with the remainder carried
over. A meteor shower that dirties forty tiles takes four frames to draw and never
drops one.

### 8.6 Palette

Sixteen pens, fixed by `palette_fw`. The current allocation spends nine of them on
icons and has **no pens reserved for terrain**, because there was no terrain when the
art was made. Proposed re-plan:

| Pens | Use |
|---|---|
| 0 | background / transparent (unchanged — masks depend on it) |
| 1–5 | dome, ring, corridor structure (unchanged) |
| 6 | colonists (unchanged) |
| **7, 11, 12, 14** | **terrain: ground, dark ground / rock, mountain, water** |
| 8–10, 13, 15 | icons and machines, re-quantised to five pens |

Two consequences, both good:

- The icons lose four colours. They are 12–20 px symbols; five pens is enough.
- **The four terrain pens are the planet palette.** Swapping those four values turns
  the desert into ice or regolith without touching a byte of art ([§5.7](#57-classification-and-planet-types)).
- Water animates by **cycling one pen** on a timer — no second frame, no blit, no cost.

This is an asset-side change and is [ASSET-7](#12-asset-gaps).

---

## 9. Interface

### 9.1 Controls

Keyboard and joystick, both complete — a CPC game that needs both hands on the keyboard
to pan and build is a chore.

| Input | Action |
|---|---|
| Cursors / joystick | move the build cursor; camera follows at the viewport edge |
| Fire / `COPY` | select, confirm, place |
| `ESC` | cancel, back |
| `SPACE` | open the build menu |
| `1`…`4` | speed: pause, normal, fast, very fast (wheel advances 0 / 1 / 2 / 4 slots per frame) |
| `TAB` | cycle alerts — jump the camera to the next problem |
| `H` | centre on `(0,0)` |

`TAB` matters more than it looks. In a base that is 6 viewports wide, the thing that is
killing you is usually off-screen.

### 9.2 HUD

Forty lines, five character rows, 80 bytes wide. Mode 0 gives 20 columns with an 8-px
font, which is not enough for anything, so Habitat uses a **4×8 font — 40 columns**
([ASSET-4](#12-asset-gaps)).

```
row 0   O2 ███████░░  PWR █████░░░░  H2O ████████░  FOOD ██░░░░░░░
row 1   Fe 120  BIO 40  PRC 12  SPR 8  MED 3  GUN 0  BOT 2
row 2   POP 34/40   sol 17   ☼ day        [ alert line ]
row 3-4 selection panel: what the cursor is over, or the open menu
```

Flows (O₂, power) are bars because what matters is the margin. Stocks are numbers
because what matters is the quantity. The alert line is the game's voice, and it should
be specific: `NO POWER — OXYGEN GEN 2` beats `WARNING`.

### 9.3 Build flow

`SPACE` → category (Dome / Corridor / Structure / Demolish) → item → size → a ghost
follows the cursor, snapped to the correct parity ([§3.4](#34-anchors-are-centres)),
with invalid footprint tiles tinted. Fire commits, `ESC` backs out. A dome's room type
is chosen immediately after placement, and can be changed later at a cost.

### 9.4 Corridor routing

The art gives four corridor sprites — `corr_h`, `corr_v`, `corr_dr`, `corr_dl` — so
corridors run in **eight directions only**, and a diagonal step is exactly one tile
diagonally.

Routing between two domes is therefore a grid walk, not a pathfinder: leave dome A by
the connector whose direction points at B, run diagonally while both axes still differ,
then run straight on the remaining axis, and enter B by the matching connector. **At
most three runs.** The route is previewed as a ghost, rejected if any tile is occupied
or is water or mountain, and committed as a single corridor record.

One gotcha from `assets/SPRITES.md` §6: **diagonal tiles overlap by 8 pixels.** Placing
them edge-to-edge leaves a visible staircase that the masks were drawn to close. The
router must step by `(±CORR_D_SX, +CORR_D_SY)`, not by tile width.

---

## 10. Progression

### 10.1 Start state

At `(0,0)`, on guaranteed flat foundation: a landing pad, one small **Oxygen** dome with
one `mach_oxygen`, one small **Quarters**, one small **Storage**, and the corridors
joining them. Four colonists: two workers, one engineer, one biologist. Starting stock:
60 Water, 40 Food, 30 Metal, 10 Bioplastic, 4 Spares.

Enough to live about two sols without doing anything, which is exactly how long it
should take to realise you need power before you need anything else.

### 10.2 Milestones

No victory screen — Planetbase's own choice, and the right one for a game about a
colony that either continues or does not.

| Milestone | Requirement |
|---|---|
| Foothold | 10 colonists, all needs green for one sol |
| Industry | Metal, Bioplastic and Spares produced on site |
| Independence | all ten stocks produced on site; no merchant trade for five sols |
| Automation | 8 bots working |
| Habitat | 80 colonists, independent, five consecutive sols with no deaths |

### 10.3 Failure

Every colonist dead. No other loss condition — a colony at 2 population with no power is
technically alive, and being allowed to try to save it is the point.

### 10.4 Time

| | |
|---|---|
| Frame | 20 ms |
| Wheel revolution | 16 frames = 320 ms |
| Sol | 4 minutes = 12,000 frames = 750 revolutions |
| Night | ≈ 40% of a sol |
| A full game | 40–80 sols, 3–5 hours |

---

## 11. Save and load

Three slots on disc, written by the game's own FDC routines — AMSDOS cannot be used,
because its workspace at `&A700–&BFFF` is occupied by bank 2 data.

| Section | Bytes |
|---|---|
| Header: magic, generator version, seed, planet, sol, camera, RNG state | 32 |
| **World plane, verbatim** | 16,384 |
| Entity tables (agents, domes, structures, corridors, jobs) | ≈ 4,100 |
| Economy: stocks, flows, buffers, milestone flags | 128 |
| **Total** | **≈ 20.2 KB** |

The world plane **is** saved, in full. Regenerating it from the seed would cost
13.5 s on every load ([§5.10](#510-player-modification)); reading 16 KB off the disc
costs an estimated 4 s and takes the modified-tile bookkeeping with it. A 178 KB
disc side holds eight such saves.

---

## 12. Asset gaps

Everything below is a change request against `CPCArt/planetbase/`, pulled in by
`sync-assets.sh`.

**ASSET-1, 2, 7 and 8 are delivered** (CPCArt `97b9653`, synced here as `f959f9e`).
**ASSET-3, 4, 5 and 6 are delivered too.** Every asset gap in this table is now
closed, and [§4.2](#42-the-eight-banks) shows every bank fitting. The rows are kept
with their sizes because the memory map in
[§4.3](#43-bank-2-flat-again) is built on those numbers.

| # | Asset | Size | Why |
|---|---|---|---|
| ✅ **ASSET-1** | **Terrain tiles**, 4 bytes × 16 lines opaque: ground ×4, dust ×4, rock ×4, mountain autotile ×16, shallow water autotile ×16, deep water fill ×4, crater ×2, foundation ×2; ore overlay ×2 masked | 3,584 B | There is no ground in the asset set. Nothing can be drawn without it. |
| ✅ **ASSET-2** | **Four room icons** — Factory, Lab, Medbay, Lounge — at all three sizes | 1,600 B | Six of the ten machines currently have no room to live in. |
| ✅ **ASSET-3** | **Four slot figures** — biologist, medic, guard, constructor bot — raising `SLOT_FIGS` 5 → 9 | +1,536 B | Five roles and three bot types share four figures today. |
| ✅ **ASSET-4** | **4×8 font**, 96 glyphs, 2 colours (a 6×8 set is also built) | 1,536 B | Mode 0 at 8 px gives 20 columns. The HUD needs 40. |
| ✅ **ASSET-5** | **Landing pad**, 4×4 tiles *opaque*, plus a ship sprite | 1,536 B | Ships, colonist arrival and trade are the mid-game. |
| ✅ **ASSET-6** | Move `conn_points` and corridor lanes onto the 8-line half-tile grid | 0 B | [§3.3](#33-the-grid-is-not-a-choice). Delivered — but it was **not** cosmetic; see below. |
| ✅ **ASSET-7** | **Palette re-plan**: four pens reserved for terrain, icons re-quantised to five; four planet palette variants | 64 B | [§8.6](#86-palette). Buys four planets for nothing. |
| ✅ **ASSET-8** | Pin the sprite build to **`--quads nw`** | −22,272 B | [§4.4](#44---quads-nw-is-mandatory). The `all` build does not fit. |

Delivery notes, for the record:

- **ASSET-7 came in at 16 bytes, not 64.** Only the four terrain pens change per
  planet, so `planet_pens` is 4 planets × 4 pens, not four whole palettes.
- **A new `tile_variants` table** (8 bytes) was added that this document did not ask
  for. The world byte gives 2 bits of decor, i.e. 0–3, but `crater` and `foundation`
  have only 2 variants each — without a mask, decor 2–3 on a crater indexes into
  `tile_foundation_0`. All counts are powers of two, so the engine does
  `variant AND (tile_variants[class] - 1)`. The generator refuses to build if a count
  ever stops being a power of two.
- The stale "two variants" prose in `assets/SPRITES.md` §5 is fixed; it now documents
  all nine (`SLOT_FIGS 9`, `SLOT_STRIDE 144`, `SLOT_BANK 1152`).
- **ASSET-3 swapped two pens this document did not specify.** The medic takes bright
  red (8) and the carrier bot the dark red (13), not the other way round: the two reds
  are indistinguishable at 6×6 visual pixels, and the figure you must find in an
  emergency is the medic, not the hauler. Verification 11 now refuses to build if any
  two figures share a dominant pen.
- **ASSET-6 was not cosmetic and not free.** Snapping every connector pushed the
  medium dome's `sw` door off the ring, because on a diagonal the snap is radial and
  the ring is 8 visual pixels thick; only the axis-aligned doors can be snapped. And
  once those moved, four colonist slots on the small dome touched a door by a single
  line — at that radius 22.5° is ~11 visual pixels while door and slot are 8 each.
  Slot placement is therefore now **computed against the doors**: a slot whose nominal
  angle collides slides along the ring, same radius, until it clears. Both failures
  were caught by existing verifications, not by inspection.
- **ASSET-5's pad is opaque, not masked** — this spec said masked. A poured slab
  replaces the terrain instead of sitting on it, so the mask bought nothing and cost
  1,024 bytes; the octagon is painted on a square pad rather than cut out of one.
  Whether a structure is masked is now a column of `STRUCTURES`, not a constant, and
  the pad is the only one set to `False`.
- **ASSET-4 ships at 4 px, as specified** — 40 columns, 1,536 bytes. A full 6×8 set
  was also built and is one constant away in `tools/font.py`; it reads better but
  costs 768 bytes and a third of the HUD width. The **lowercase glyphs stay** in
  either case. At 4 px, `M`, `N`, `W`, `m` and `w` are drawn with a single diagonal
  rather than two filled rows — two filled rows in three pixels is a solid block.

---

## 13. Build and test

```
assets/sprites.asm  ─┐
src/*.asm           ─┼─ rasm ──> habitat.bin ──> iDSK ──> habitat.dsk ──> cpcemu
data/*.bin          ─┘
```

| Tool | Path | Role |
|---|---|---|
| `rasm` | `~/rasm/rasm.exe` | assembler; handles banking directives and `align 256` |
| `iDSK` | `~/idsk/iDSK` | builds the `.dsk` image |
| `cpcemu` | `~/cpcemu/cpc.py` | **headless** CPC 6128 — Z80 + gate array + CRTC + PPI + FDC, renders to a framebuffer, dumps PNG |

The headless emulator is the most valuable thing in this list, because it makes the
tests in this document runnable rather than aspirational:

| Test | Method |
|---|---|
| Generator determinism | generate a seed twice from cold boot, diff bank 4 ([§5.11](#511-testing-determinism)) |
| Generator regression | golden bank-4 dumps per version, checked in |
| Map quality | render each golden seed to PNG, review by eye |
| Frame budget | instrument the ISR with a frame counter; assert no slot exceeds its budget |
| Blit correctness | render a known scene, compare against a golden PNG |
| Playability of every seed | headless run of N seeds, assert water and ore within 30 tiles of centre |

That last one is the kind of test that is impossible on real hardware and trivial here.
It should be run over a few thousand seeds before release.

---

## 14. Delivery plan

| # | Milestone | Proves |
|---|---|---|
| 1 | Boot, firmware off, palette, Mode 0, `sprites.bin` loaded into banks | the memory map |
| 2 | Opaque and masked blit kernels; draw one dome from `nw` quadrants | [§2.2](#22-the-frame-budget)'s cost table is real |
| 3 | Terrain tiles + tile pass; draw a hand-made 20×10 map | the tile grid |
| 4 | World generator; `GENERATING` screen; determinism test green | [§5](#5-procedural-world-generation) |
| 5 | Camera: CRTC offset scroll + edge redraw + HUD raster split | the riskiest rendering claim ([§15](#15-open-risks)) |
| 6 | Build mode: ghost, validation, place a dome, corridors | [§9.3](#93-build-flow), [§9.4](#94-corridor-routing) |
| 7 | Entities, node graph, routing matrices, **the wheel** | [§7](#7-the-batch-scheduler) |
| 8 | Needs, jobs, production; the colony runs itself | the game exists |
| 9 | Events, ships, trade, milestones | the game is a game |
| 10 | Save/load, audio, four planets, tuning | shippable |

Milestones 1–5 are the ones that can fail for hardware reasons. Do them first, in that
order, and do not build gameplay on top of a scroll that has not been proven on a real
6128.

---

## 15. Open risks

| Risk | Severity | Mitigation |
|---|---|---|
| ~~CRTC offset scrolling with a two-page raster split~~ | ~~High~~ | **Resolved at milestone 5, and split in two.** Offset scrolling works to the pixel ([§8.2](#82-camera)). The mid-frame page change does **not** — the CRTC latches the start address once per frame — so the HUD moved into the play page and bank 2 went flat ([§8.1](#81-screen-layout), [§4.3](#43-bank-2-flat-again)). |
| HUD re-render on every scroll step, ≈ 0.4 frames, **estimated not measured** | Medium | Measure when the HUD renderer exists. If it is too slow, the escape hatch is rupture — with the CRTC-type compatibility risk that comes with it. |
| Mid-frame writes land where aimed, but only on the emulator's CRTC | Low | The border control in `tests/test_camera.py` hits line 160 exactly. Real hardware still wants a check, but nothing now depends on a mid-frame *address* write. |
| Memory map slack: 1,536 contiguous in bank 2, **288 in bank 6**, 440 in bank 7 | Medium | Bank 6 is the tight one now and the entity tables grew into it. The next thing that needs space there moves `plants` out of bank 7 first, or takes the `s` room-icon set (864 B) as [§4.2](#42-the-eight-banks) names. |
| Routing rebuild latency of ≈ 5 s after a network change | Low | Stale routes are inefficient, never invalid ([§6.4](#64-routing)). If it grates: cache paths for the 16 busiest pairs and rebuild those first. |
| **13.5 s** world generation feels long even on a cassette-era machine, and it is 3.9× the original estimate | Medium | New game only — loads read the plane off disc ([§5.10](#510-player-modification)). Real progress bar, music keeps playing. The identified 2× win ([§5.9](#59-cost--measured)) is held in reserve. |
| A seed produces a technically valid but miserable map | Low | Feature anchors guarantee the necessities; the headless seed sweep ([§13](#13-build-and-test)) finds the rest. |
| **Airlock: dome or structure?** The asset set now has both an `icon_airlock` room type and a standalone `airlock` structure sprite; the node graph in [§6.2](#62-the-node-graph) only models the dome | Medium | Decide before the node graph is written — it changes what an *outdoor edge* connects to. Recommendation and the comparison are in [§6.2](#62-the-node-graph). Cheap either way: the unused half is 400–512 bytes. |
| A full-colony routing rebuild is ~27 s of stale routes at the current budget | Medium | Only at 128 nodes; 48 nodes is 3.8 s ([§6.4](#64-routing)). Two levers, both untaken: raise the per-frame budget while the camera is still, or tighten `rt_node` — its per-node setup re-reads the same three bytes and is worth about 2×. |
| ~~Slots 11, 12, 13 and 15 of the wheel are unwritten~~ | ~~Medium~~ | **Written and measured.** Four of six budgets were low, by 1.5× to 5× ([§7.2](#72-the-wheel)). The worst frame is a third of a frame, so the design holds. Remaining passes should be budgeted pessimistically. |
| A heavy sim slot and a scroll column in the same frame come to ~19 ms of 20 | Medium | The dirty list is a budget, so the edge redraw spreads over two frames. Costs nothing but a one-frame lag on the newly exposed column; needs watching once the HUD re-render ([§8.1](#81-screen-layout)) is measured too. |
| ~~Needs, health and death are not written~~ | ~~High~~ | **Written.** Colonists eat, drink, sleep, get treated, die, and grieve; the only loss condition is live ([§6.6](#66-needs)). |
| ~~Nothing produces food~~ | ~~High~~ | **Greenhouses grow.** Plants sit in the machine slots, `plant_class` decides the crop, and every plant needs a biologist ([§6.5](#65-economy)). |
| Meteors and intruders are unbuilt, and both need the renderer first | Medium | Meteors write terrain, so they need the world plane and the dirty list; intruders need edge spawning and combat. Neither is a simulation problem, which is why neither is in [§6.10](#610-events-and-hazards) yet. |
| Ships, trade and milestones are unbuilt — [§6.11](#611-ships-and-arrivals) and [§10.2](#102-milestones) | Medium | The colony sustains itself but cannot grow: no new colonists arrive and nothing can be traded for. This is what makes it a sandbox rather than a game. |
| The balance numbers in [§6.5](#65-economy) are first guesses and three of them were unlivable | Medium | Corrected against the first working colony ([§6.6](#66-needs)). Expect the same of the rest: they cannot be checked by reading, only by running the loop and looking at who is where. |
| Balance | Certain | Every number in [§6.5](#65-economy) is a first guess. The recipe table exists so that rebalancing is a data edit, not a code edit. |

---

## Appendix A — constants

| Name | Value | Meaning |
|---|---|---|
| `WORLD_TILES` | 128 | world edge, in tiles |
| `WORLD_MIN` / `WORLD_MAX` | −64 / +63 | tile coordinate range |
| `HT_MIN` / `HT_MAX` | −128 / +127 | half-tile coordinate range |
| `TILE_W` / `TILE_H` | 4 bytes / 16 lines | |
| `VIEW_W` / `VIEW_H` | 20 / 10 | viewport, in tiles |
| `PLAY_LINES` / `HUD_LINES` | 160 / 40 | |
| `MAX_AGENTS` | 96 | 80 colonists + 16 bots |
| `MAX_DOMES` / `MAX_STRUCTS` | 64 / 64 | |
| `MAX_CORRIDORS` | 96 | |
| `MAX_NODES` | 128 | domes + structures + pad + 8 build sites |
| `MAX_JOBS` | 32 | |
| `NODE_SLOTS` | 8 | ring slots per dome, `corr_fill` order |
| `N_STOCK` | 14 | ten goods plus four greenhouse intermediates ([§6.5](#65-economy)) |
| `DOME_REC` | 24 | bytes per dome — 8 machine slots, not 4 |
| `RECIPE_REC` | 10 | bytes per machine recipe — 3 inputs |
| `MAX_JOB` | 32 | job board entries |
| `JOB_SCAN` / `JOB_LOOK` / `JOB_ASSIGN` | 4 / 32 / 4 | domes posted from, agents examined, assignments — per visit |
| `NEED_LOW` / `NEED_CRIT` | 64 / 16 | go looking for a room / start losing health |
| `wh_need_n` | 8 | colonists per needs slot — each visited every 4th revolution |
| `N_ROOM` / `ROOM_MAX` | 12 / 8 | room types, and domes indexed per type ([§6.6](#66-needs)) |
| `ROLE_SPEED` | 88–144 | edge progress per movement visit, by role |
| `PROD_DOMES` | 16 | domes per production slot: a full sweep every 4 revolutions |
| `SOL_FRAMES` / `DAY_FRAMES` | 12,000 / 7,200 | a sol, and how much of it is daylight |
| `MAX_DEGREE` | 8 | edges per node — one per `conn_points` direction |
| `WHEEL_SLOTS` | 16 | 320 ms per revolution |
| `MOVE_SLOTS` | 8 | slots 0–7 |
| `wh_move_n` | 12 | agents per movement slot — **RAM, not an assembled constant** ([§7.3](#73-degradation)) |
| `wh_decay_n` | 32 | agents per decay slot, likewise |
| `WH_RT_B` | 12 | routing node expansions per frame ([§7.2](#72-the-wheel)) |
| `NO_EDGE` / `NO_SLOT` | 255 | "not in transit" / "holds no ring slot" |
| `RT_FAR` / `RT_UNREACH` | 254 / 255 | distance ceiling / no route |
| `R_PLATEAU` / `R_BLEND` / `R_RIM` | 5 / 10 / 57 | generator shaping radii |
| `ANCHORS` | 6 | feature anchors per world |
| `SOL_FRAMES` | 12,000 | 4 minutes |
| `FRAME_US` | 19,968 | the budget everything is measured against |

## Appendix B — where to look

| For | Read |
|---|---|
| Every sprite, its pointer, and how a dome is composed | [`assets/SPRITES.md`](assets/SPRITES.md) |
| Byte offsets and sizes of individual sprites | [`assets/sprites_map.txt`](assets/sprites_map.txt) |
| Constants to `include` | [`assets/sprites.asm`](assets/sprites.asm) |
| Where the art comes from and how to regenerate it | [`assets/README.md`](assets/README.md), [`sync-assets.sh`](sync-assets.sh) |
| What is actually in each bank, at real addresses | `build/layout.txt`, produced by [`tools/pack.py`](tools/pack.py) |
| The specification of every algorithm, in runnable form | [`tools/worldgen_ref.py`](tools/worldgen_ref.py), [`tools/graph.py`](tools/graph.py), [`tools/entity.py`](tools/entity.py), [`tools/world.py`](tools/world.py) |
| Whether any number in this document is still true | `./tools/build.sh` — every measured figure here is asserted by a test |
