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
| One terrain tile | 64 opaque | ≈ 320 µs | 0.016 |
| One viewport column (10 tiles) | 640 | ≈ 3,200 µs | 0.16 |
| One viewport row (20 tiles) | 1,280 | ≈ 6,400 µs | 0.32 |
| Full play area (200 tiles) | 12,800 | ≈ 64,000 µs | **3.2** |
| One colonist slot | 16 opaque | ≈ 64 µs | 0.003 |
| One machine / plant | 132 opaque | ≈ 530 µs | 0.027 |
| Small dome, ring + dome, all 4 quadrants | 2,048 masked data | ≈ 28,700 µs | **1.4** |
| Medium dome, likewise | 4,608 | ≈ 64,500 µs | **3.2** |
| Large dome, likewise | 8,192 | ≈ 114,700 µs | **5.7** |

Read the last three rows carefully — **drawing one large dome costs almost six
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
| structure `xl` (`solar_xl`, `mine`) | 16 × 64 | 4 × 4 |
| diagonal corridor step `(CORR_D_SX, CORR_D_SY)` | 4 × 16 | **1 × 1** |

The diagonal corridor advancing exactly one tile per step is the happy accident that
makes corridor routing ([§9.4](#94-corridor-routing)) a grid walk rather than a line
algorithm.

The one thing that does **not** align: corridors run on the dome's centre line, and
`conn_points` puts them 4 lines either side of it — so a horizontal corridor straddles
two tile rows by 4 lines each. That is harmless (corridors are drawn at absolute
positions, and occupancy simply marks both rows), but it is the reason corridor
redraw rectangles are computed in lines, not tiles. An optional art tidy-up to snap
connectors onto the 8-line half-tile grid is listed as [ASSET-6](#12-asset-gaps).

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

**The autotile variant is deliberately not stored.** It is recomputed at draw time
from the four orthogonal neighbours — four bank reads and a 16-entry lookup, ≈ 60 µs
per tile against a 320 µs blit. Paying 19% more per tile to free 4 bits of world
state is a good trade, and it means terrain edits never have to fix up their
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
| window | 6 | dome+ring `nw` quadrants 7,424 · slot figures 3,456 · entity tables 4,096 · job board 256 · path workspace 512 | 15,744 | 640 |
| window | 7 | external structures 11,264 · plants 1,584 · text 1,024 · audio 2,048 | 15,920 | 464 |
| `&8000–&BFFF` | 2 | HUD screen page 3,200 + graphics arenas 12,888 | 16,088 | 296 |
| `&C000–&FFFF` | 3 | play-area screen | 16,384 | 0 |

Every bank is spoken for. The two matrices in banks 1 and 5 are the clearest answer
to "what is the extra 64 KB actually *for*": they turn pathfinding from a per-agent
search into a single table read ([§6.4](#64-routing)).

Slack is thin — under 1.5 KB total. Cheap ways to buy more, in order of preference:
drop `solar_xl` (2,048 B), drop four plant species (528 B), move `plants` into bank 6's
slack and the slot figures into an arena.

### 4.3 The `&8000` page and its arenas

Bank 2 does double duty: it is the **HUD screen page** *and* it holds the small
graphics. That works because a 5-character-row HUD uses very little of a 16 KB screen
page. CPC screen addressing is `base + (line & 7) × &800 + (line >> 3) × &50 + x`, so
five character rows occupy only bytes `&000–&18F` of each of the eight `&800` sub-pages.

That leaves **eight independent arenas of 1,648 bytes each = 13,184 bytes.** Nothing
may straddle an arena boundary, so only small sprites go here — which is exactly what
these are:

| In the arenas | Bytes |
|---|---|
| Terrain tiles ([ASSET-1](#12-asset-gaps)) | 3,584 |
| Room icons, 12 types × 3 sizes | 4,800 |
| Machines, 10 types | 1,320 |
| Corridors + connectors | 896 |
| 4×8 font, 96 glyphs ([ASSET-4](#12-asset-gaps)) | 1,536 |
| Cursor and UI chrome | 512 |
| Data tables (`machine_slots`, `conn_points`, `corr_slots`, …) | 240 |
| **Total** | **12,888** |

Largest single item is a 200-byte `icon_l`, so bin-packing eight 1,648-byte arenas is
trivial. `flip_mode0` must be 256-byte aligned and lives in bank 6 with the quadrants
it serves.

### 4.4 `--quads nw` is mandatory

`assets/sprites.bin` is 50,432 bytes built with `--quads all`, of which 29,696 are dome
and ring quadrants. Built with `--quads nw` the whole set is 28,160 bytes and the
quadrants are 7,424. **The full build does not fit this memory map; the `nw` build fits
with room to spare.**

The cost is that `ne`, `sw` and `se` are generated at blit time — reversed pair order
and a `flip_mode0` lookup per byte, per `assets/SPRITES.md` §3. That is roughly 40%
slower for three quadrants out of four. Since dome quadrants are drawn only when a
dome is built or repaired — and that work is already spread over frames
([§6.9](#69-construction)) — 22 KB is worth far more than the microseconds.

**Action:** the asset sync must be pinned to `--quads nw`. Today `sync-assets.sh`
pulls the default build.

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

### 5.4 Pyramid noise, not per-tile fBm

The textbook approach — evaluate three octaves of bilinear value noise at every one of
16,384 tiles — costs roughly 2,500 µs per tile on a Z80, or **41 seconds**. Unusable.

Instead, synthesise **coarse-to-fine**, doing the interpolation once per output sample
rather than once per octave per sample:

```
grid 16×16    = H(gx,gy) at the coarsest lattice          256 samples
  upsample ×2 -> 32×32    (tent filter: average neighbours)
  add octave  += H(...)/2 at 32×32                      1,024 samples
  upsample ×2 -> 64×64
  add octave  += H(...)/4 at 64×64                      4,096 samples
  upsample ×2 -> 128×128
  add octave  += H(...)/4 at 128×128                   16,384 samples
```

Each upsample step is an average of two adjacent bytes — `add a,b` / `rra` — and each
octave add is a hash plus a shift. Total work ≈ 21,500 samples × ≈ 40 µs ≈ **0.9 s**
per field. Two fields, ≈ 1.8 s.

Three octaves at 8-, 4- and 2-tile lattice spacing give landmasses about 20 tiles
across with 4-tile coastline detail — which is the right texture for a world where a
large dome is 8 tiles and a walk across the map is 128.

The tent filter is not a true bilinear interpolation; it produces slightly boxier
features. At four visible tiles per lattice cell nobody will see the difference, and
it is four times cheaper.

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

Six anchors, derived from the seed as `(angle, radius, kind)`:

| # | Kind | Radius from centre | Effect |
|---|---|---|---|
| 1, 2 | lake | 12 … 28 tiles | elevation pushed down → water |
| 3, 4 | ore ridge | 10 … 30 tiles | elevation pushed up, resource bit forced |
| 5 | flat basin | 8 … 18 tiles | elevation pulled to mid → a second buildable area |
| 6 | wildcard | 20 … 50 tiles | one of the above, from the seed |

Each anchor stamps a radial bump into the elevation field, **inside its own bounding
box only** — radius ≤ 12 tiles means 625 tiles per anchor, so six anchors cost
6 × 625 × 40 µs ≈ 150 ms rather than the 4 seconds a full-map pass would take.

The angles are spread by construction (each anchor gets a 60° sector plus a seeded
jitter) so the features never all end up on one side.

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

### 5.9 Cost, and why it is still batched

| Pass | Cost |
|---|---|
| Permutation table | negligible |
| Elevation pyramid | ≈ 0.9 s |
| Moisture pyramid | ≈ 0.9 s |
| Shape + anchors | ≈ 0.2 s |
| Classify | ≈ 0.5 s |
| Clean | ≈ 1.0 s |
| **Total** | **≈ 3.5 s** |

Three and a half seconds behind a `GENERATING WORLD` screen is fine. But the generator
is still written as a resumable state machine that does one chunk per frame and returns,
for three reasons: the progress bar is real rather than a lie; the music keeps playing;
and a generator that can stop and resume is a generator that can be single-stepped when
a seed comes out wrong.

### 5.10 Player modification

Terrain changes during play — a mined-out mountain becomes rock, a meteor leaves a
crater, a dome site becomes foundation. These are **not** regenerable from the seed, so
they are logged to a **delta list**: `(tile index, new byte)`, 3 bytes each, 512 entries.

On load, the world is regenerated from the seed (3.5 s) and the deltas are replayed
(instant). A save therefore stores about 1.5 KB of world state instead of 16 KB.

If the list ever fills — 512 modified tiles is a great deal of mining — the oldest
entries are folded into a full 16 KB plane dump in the save file, and the list resets.

### 5.11 Testing determinism

The headless emulator at `~/cpcemu` makes this mechanical, and it should be a test
from the first day the generator exists:

1. Boot, generate seed `A3F2`, dump bank 4 to a file via a debug hook.
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
| `edge` | edge currently traversed, 255 = not in transit |
| `progress` | 0–255 along that edge |
| `task` | job board entry, 255 = idle |
| `o2 water food sleep health morale` | needs, 0–255 |
| `skill` | experience, feeds work speed |
| `spare` | |

Buildings use the same pattern:

| Table | Entries | Fields |
|---|---|---|
| Domes | 64 | `cx cy size room state integrity power slots machines[4] health[4]` |
| Structures | 64 | `cx cy kind size state integrity output` |
| Corridors | 96 | `a b dir len state` |
| Jobs | 32 | `kind target agent priority age` |

Total ≈ 4,096 bytes, the bank 6 allocation.

### 6.2 The node graph

The colony is a graph, and almost every system reads it rather than the tile grid.

- **Nodes** (≤128): every dome, every external structure, the landing pad, and up to 8
  transient construction sites.
- **Edges**: a corridor between two domes; an *outdoor edge* from an airlock dome to an
  external structure or construction site. A dome has at most 8 edges — one per
  `conn_points` direction.
- **Node capacity**: 8 ring slots per dome (`corr_slots`), filled in `corr_fill` order
  `0,4,2,6,1,5,3,7` so people never look stacked; 1–2 work slots per external structure.

External structures are never corridor-connected. Reaching one means leaving through an
airlock and walking — which is exactly why airlock placement is a real decision, and why
a sandstorm that kills people outdoors has teeth.

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

Roughly 150 µs including the occasional 64 µs slot blit. No pathfinding, no collision,
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
| `DIST` | 1 | hop-weighted distance, 254 = far, 255 = unreachable |

Runtime routing is therefore **one table read**. Finding the nearest idle engineer to a
broken machine is a scan of idle agents with one `DIST` read each. There is no A*, no
open list, no per-agent path storage, and no frame-time spike when twenty people
re-path at once.

The price is rebuild cost. An all-pairs BFS over 128 nodes is ≈ 1,024 relaxations per
source × ≈ 30 µs ≈ 30 ms — about 1.5 frames per source, 128 sources. So the rebuild is
**batched: half a source per frame, 256 frames, about 5 seconds**, triggered whenever
the network changes (a corridor built or destroyed — rare).

During those 5 seconds the old matrix stays live and agents route on slightly stale
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

Ten **stocks**, 16-bit, capped by storage-dome capacity:

`Water · Food · Ore · Metal · Bioplastic · Processors · Spares · Medicine · Guns · Bots`

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

Each machine type has one **recipe record** — `in1, qty1, in2, qty2, out, qty, power,
flags` — eight bytes, eighty bytes for the lot. The production tick is a table walk, not
a switch statement, which is both smaller and much easier to rebalance.

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
| Greenhouse slot | 3 Starch or 2 Vegetables | 1 Water, 1 Power |

These numbers are a starting point for tuning, not a balance claim.

### 6.6 Needs

Six per colonist, decaying on the wheel: **oxygen, water, food, sleep, health, morale.**

- Oxygen and water drain constantly; below a threshold, health drains.
- Food drains slower and is satisfied at a canteen. **Variety** is tracked as three
  hidden counters (starch / vegetable / meat consumed recently); eating one category
  exclusively caps health — Planetbase's malnutrition rule, which is what makes a
  greenhouse with one crop a trap.
- Sleep is satisfied in quarters. An unsleeping colonist works slower and then stops.
- Health is repaired in a medbay by a medic, consuming Medicine.
- Morale rises with a lounge, a tree in a greenhouse (`plant_class` 3 = morale), food
  variety and spare space; it falls with deaths, alarms and overcrowding. Low morale
  colonists stop working, then leave on the next ship.

Six bytes of decay per colonist per visit, ≈ 40 µs. Cheap; the expensive part is
*deciding what to do about it*, which is the job board's problem.

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
ties by `DIST[agent.node][job.node]`. Bounded at **4 assignments per visit** so the pass
cannot spike.

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
| Canteen | `canteen` | `food`, `vitromeat` | meals, morale |
| Oxygen | `oxygen` | `oxygen` (small domes only) | life support |
| Greenhouse | `greenhouse` | 12 plant species | starch, vegetables, medicine, morale |
| Storage | `storage` | — | stock capacity 100 / 300 / 600 |
| Airlock | `airlock` | — | the only route outdoors |
| **Factory** | *new* | `iron`, `bioplastic`, `spares`, `robots`, `weapons` | refining and manufacture |
| **Lab** | *new* | `processors`, `vitromeat` | high-tech goods |
| **Medbay** | *new* | `medical` | healing, medicine |
| **Lounge** | *new* | — | morale |

The last four need new icons — [ASSET-2](#12-asset-gaps). Without them, six of the ten
machines in the asset set have no home, which is not a gap worth designing around.

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

One check per wheel revolution (≈ 3 Hz), from the gameplay RNG.

| Event | Attacks | Countered by |
|---|---|---|
| Sandstorm | solar output ↓, outdoor structures damaged, outdoor agents take health damage | turbines, collectors, indoor work |
| Solar flare | processors and machine health, sickness | spares, medics, warning from Control |
| Meteor shower | random structures destroyed, **crater tiles written to the world plane** | spread-out building, spares |
| Intruders | arrive at the map edge, walk in, attack | guards, guns, airlock placement |
| Malfunction | one machine stops | engineer + 1 Spare |
| Night | solar output = 0 for ~40% of each sol | collectors, turbines |

Meteors are the only event that writes terrain, and they write through the same delta
list as mining ([§5.10](#510-player-modification)).

A Control room gives a warning some seconds ahead of storms and flares, which is what
makes Control worth building before it is obviously needed.

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

| Slot | Pass | Slice | Budget |
|---|---|---|---|
| 0–7 | **Agent movement** | 12 agents each — every agent moves once per revolution | ≈ 1,800 µs |
| 8–10 | Needs decay | 32 agents each | ≈ 1,300 µs |
| 11 | Production | 16 domes — every dome produces every 4 revolutions | ≈ 4,000 µs |
| 12 | Flow balance | power and oxygen supply vs demand, storage caps | ≈ 2,000 µs |
| 13 | Job board | reap finished jobs, post new ones, up to 4 assignments | ≈ 3,000 µs |
| 14 | Routing rebuild | half a BFS source, only when the network is dirty | ≈ 15,000 µs |
| 15 | Events | one roll: weather, disaster, ship, day/night | ≈ 500 µs |

Every frame, regardless of slot: read input, move cursor and camera, advance the dirty
list ([§8.5](#85-the-dirty-list)) up to a 20,000 µs cap, tick animation, service audio.

The worst frame is slot 14 during a routing rebuild: ≈ 15,000 µs of BFS plus input and
audio, with the dirty list getting whatever is left. That is why the rebuild is half a
source rather than a whole one, and why the dirty list is a *budget* rather than a
queue that must be drained.

### 7.3 Degradation

The wheel length is fixed at 16. As the colony grows, **slices grow, not the wheel**:

| Colonists | Agents per movement slot | Effective update rate |
|---|---|---|
| 20 | 4 | 3.1 Hz |
| 50 | 8 | 3.1 Hz |
| 80 + 16 bots | 12 | 3.1 Hz |

— because the slot count is fixed, every agent is still visited once per revolution.
The cost per slot rises from ≈ 600 µs to ≈ 1,800 µs, which the budget absorbs. If the
ceiling were ever raised past 96 the correct move is to visit each agent once every
*two* revolutions and double `speed`, so apparent walking pace is unchanged and only
the sim's decision latency degrades.

### 7.4 Batched work outside the wheel

Four more things are sliced, for the same reason:

| Work | Slicing | Total |
|---|---|---|
| World generation | one pyramid level or one classify chunk per frame | ≈ 3.5 s, with a real progress bar |
| Routing rebuild | half a BFS source per frame, slot 14 | ≈ 5 s, invisible |
| Dome construction blit | one quadrant per frame | ≈ 8 frames |
| Camera redraw after a jump | one tile column per frame | ≈ 20 frames |

---

## 8. Rendering

### 8.1 Screen layout

```
lines   0 .. 159    play area   80 bytes × 160 lines  = 20 × 10 tiles   from bank 3 (&C000)
lines 160 .. 199    HUD         80 bytes ×  40 lines  =  5 char rows    from bank 2 (&8000)
```

The two halves come from **different CRTC screen pages**. Bits 4–5 of `R12` select which
16 KB block the display reads, so a raster split at line 160 switches the HUD to page 2
with a fixed offset, while the play area keeps the whole of page 3's 16 KB as a
scrolling torus. Without the two-page split the HUD and the play area would have to
share one 1,024-word CRTC address ring, and a scrolling play area would eventually walk
over the HUD.

Interrupts arrive every 52 scanlines (0, 52, 104, 156, 208, 260), so line 160 is reached
by taking the interrupt at 156 and delaying four lines — 256 T-states — after a
stabilised interrupt. Standard CPC practice, but it does need proving on hardware
([§15](#15-open-risks)).

### 8.2 Camera

The camera moves in **whole tiles**, implemented entirely as a CRTC display-offset
change:

| Step | Offset change |
|---|---|
| One tile east/west | ± 2 offset words (2 × 2 bytes = 8 px) |
| One tile south/north | ± 80 offset words (2 × `R1` = 16 lines) |

Then **only the newly exposed edge is drawn** — one column (0.16 frames) or one row
(0.32 frames). That is the whole reason for hardware scrolling: the alternative, a full
play-area redraw, is 3.2 frames per step, twenty times worse.

Half-tile steps are possible (1 word, 40 words) and are what the position unit is built
for, but they leave a half-visible tile at two edges and need a partial-tile blit
variant. **Not taken now**; whole-tile steps keep the tile pass free of clipping. The
half-tile unit still earns its place for walkers and for odd-footprint structures.

The 16 KB page wraps, so the newly exposed strip's addresses wrap too. The blit
computes addresses from the current offset anyway, so this is bookkeeping rather than a
new mechanism — but it is the part most likely to need an afternoon with the emulator.

**Fallback if the wrap proves painful:** no hardware scroll, camera jumps 4 tiles at a
time with a full redraw sliced one column per frame (20 frames, ≈ 0.4 s per jump). Worse,
but shippable, and it changes nothing above the renderer.

### 8.3 The tile pass

Per tile: read the world byte from bank 4, unpack class and decor, read the four
orthogonal neighbours, index a 16-entry autotile table, and blit 4 bytes × 16 lines
opaque.

The line stepping is nearly free. Within a character row, line *n+1* is at address
*+ &800*, so eight consecutive lines are `ld a,h / add a,8 / ld h,a` — 11 T-states —
and only the crossing into the next character row needs the full computation.

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
| Entity tables (agents, domes, structures, corridors, jobs) | ≈ 4,100 |
| Economy: stocks, flows, buffers, milestone flags | 128 |
| World delta list, up to 512 × 3 | ≤ 1,536 |
| **Total** | **≈ 5.8 KB** |

The world plane itself is **not** saved — it is regenerated from the seed in 3.5 s on
load and the deltas replayed over it. That is the whole payoff of the determinism
contract in [§5.1](#51-the-contract): a 16 KB map costs two bytes in the save file.

If the delta list overflows, the save falls back to a full 16 KB plane dump and the
list resets. A save is never allowed to be lossy.

---

## 12. Asset gaps

Everything below is a change request against `CPCArt/planetbase/`, pulled in by
`sync-assets.sh`. Habitat cannot be built without the first four.

| # | Asset | Size | Why |
|---|---|---|---|
| **ASSET-1** | **Terrain tiles**, 4 bytes × 16 lines opaque: ground ×4, dust ×4, rock ×4, mountain autotile ×16, shallow water autotile ×16, deep water fill ×4, crater ×2, foundation ×2; ore overlay ×2 masked | 3,584 B | There is no ground in the asset set. Nothing can be drawn without it. |
| **ASSET-2** | **Four room icons** — Factory, Lab, Medbay, Lounge — at all three sizes | 1,600 B | Six of the ten machines currently have no room to live in. |
| **ASSET-3** | **Four slot figures** — biologist, medic, guard, constructor bot — raising `SLOT_FIGS` 5 → 9 | +1,536 B | Five roles and three bot types share four figures today. |
| **ASSET-4** | **4×8 font**, 96 glyphs, 2 colours | 1,536 B | Mode 0 at 8 px gives 20 columns. The HUD needs 40. |
| **ASSET-5** | **Landing pad**, 4×4 tiles masked, plus a ship sprite | ≈ 2,300 B | Ships, colonist arrival and trade are the mid-game. |
| **ASSET-6** | *Optional:* move `conn_points` and corridor lanes onto the 8-line half-tile grid | 0 B | Tidies corridor/tile alignment ([§3.3](#33-the-grid-is-not-a-choice)). Cosmetic. |
| **ASSET-7** | **Palette re-plan**: four pens reserved for terrain, icons re-quantised to five; four planet palette variants | 64 B | [§8.6](#86-palette). Buys four planets for nothing. |
| **ASSET-8** | Pin the sprite build to **`--quads nw`** | −22,272 B | [§4.4](#44---quads-nw-is-mandatory). The `all` build does not fit. |

Also worth correcting: `assets/SPRITES.md` §5 says corridor slots have "two variants",
but `sprites.asm` declares `SLOT_FIGS equ 5` (empty, colonist, carrier, driller,
engineer) with `SLOT_STRIDE 80` and `SLOT_BANK 640`. The assembly is right; the prose
is stale.

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
| **CRTC offset scrolling with a two-page raster split** — the interaction of the 1,024-word address ring, the `&800` line stride and a mid-frame `R12` page change is the least certain thing in this document | High | Prototype at milestone 5, before anything depends on it. Fallback: sliced full redraw on camera jumps ([§8.2](#82-camera)) — costs 0.4 s per jump and nothing else. |
| Raster split timing at line 160 | Medium | Stabilised interrupt + fixed delay is standard practice, but must be verified on hardware, not only in the emulator. |
| Memory map has under 1.5 KB of slack | Medium | Named cuts in priority order in [§4.2](#42-the-eight-banks). |
| Routing rebuild latency of ≈ 5 s after a network change | Low | Stale routes are inefficient, never invalid ([§6.4](#64-routing)). If it grates: cache paths for the 16 busiest pairs and rebuild those first. |
| 3.5 s world generation feels long on a cassette-era machine | Low | Real progress bar, music keeps playing. It is still faster than loading the game was. |
| A seed produces a technically valid but miserable map | Low | Feature anchors guarantee the necessities; the headless seed sweep ([§13](#13-build-and-test)) finds the rest. |
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
| `WHEEL_SLOTS` | 16 | 320 ms per revolution |
| `MOVE_SLOTS` | 8 | slots 0–7 |
| `DELTA_MAX` | 512 | world modifications before a full dump |
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
