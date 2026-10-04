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
| One terrain tile | 64 opaque | **889 µs measured** | 0.045 |
| One viewport column (10 tiles) | 640 | **8,890 µs** | 0.45 |
| One viewport row (20 tiles) | 1,280 | **17,780 µs** | 0.89 |
| Full play area (200 tiles) | 12,800 | **177,700 µs** | **8.9** |
| One colonist slot, blit alone | 16 opaque | ≈ 64 µs | 0.003 |
| One machine / plant, blit alone | 132 opaque | ≈ 530 µs | 0.027 |
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
> See [§8.3](#83-the-tile-pass). The figure rose from 929 to **958 µs** when the
> camera moved into the address arithmetic: `scr_addr` now adds the display
> offset and the 2 KB ring needs masking at two points of the tile loop
> ([§8.2](#82-camera)). 3% for a camera that costs no redraw is a good trade.
> And to **968 µs** at milestone 42, when the terrain lookup came out of `tile_one`
> as `tile_src` so that an emptied ring slot could share it ([§8.5](#85-the-dirty-list)):
> one `CALL` and one `RET` per tile, one frame in the ten timed passes. And the
> first time it fell: **889 µs** at milestone 56, 570 of it the blit and the loop and
> 319 the per-tile logic ([§8.3](#smaller-and-faster-at-milestone-56)).

> **The two "blit alone" rows above are traps, and the dirty list found out how
> big a trap.** Drawing one colonist slot really is 64 µs of copying — but
> *reaching* it costs paging the bank, reading the dome record, computing the
> frame and testing visibility, and **that is 1,498 µs measured**
> ([§8.5](#85-the-dirty-list)). For small redraws the preparation is the cost
> and the blit is the rounding error.

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

**Bit 3 is read by two things now**, and until milestone 31 it was read by one: the
tile pass draws `ore_overlay` on a mountain that has it, and `bd_res` refuses to put a
mine anywhere else ([§6.5](#65-economy)). The *fertile* meaning on ground and the
*drillable depth* meaning on water are still unused — the generator never sets the
water one, so a pump asks for water tiles rather than for deep ones.

**The autotile variant is deliberately not stored.** Which classes autotile is not
stored either: a class with 16 variants in `tile_variants` is autotiled, anything
else takes its variant from the decor bits. The rule falls out of the data, so
there is no second table to keep in step. It is recomputed at draw time
from the four orthogonal neighbours — four bank reads and a 16-entry lookup, which
is inside the measured 889 µs per tile ([§2.2](#22-the-frame-budget)); the blit
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
| `&0000–&3FFF` | 0 | engine code, ISR, blit kernels, UI | 16,384 | **2,603** |
| window | 1 | **distance matrix** `DIST[96][128]` 12,288 · room icons `m` and `l` 3,936 | 16,384 | 160 |
| window | 4 | **world plane** 128×128×1 byte | 16,384 | 0 |
| window | 5 | **next-hop matrix** `NEXTHOP[96][128]` 12,288 · **object index** ≤ 960 ([§8.4](#84-object-pass-and-draw-order)) | 16,384 | 3,136 |
| window | 6 | `flip_mode0` 256 · dome+ring `nw` quadrants 7,424 · slot figures 3,456 · entity tables 4,832 ([§6.1](#61-entities)) · figure cache 512 | 16,356 | 28 |
| window | 7 | external structures 11,264 · plants 1,584 · `plant_ptr` 24 · text 1,024 (1,017 used) · **font 1,536** (was the `audio` reservation, milestone 33) | 15,432 | 952, 7 of them in the text block |
| `&8000–&BFFF` | 2 | graphics, flat 9,592 (font gone to bank 7) · ghost undo log 1,160 · code 5,515 ([§4.3](#43-bank-2-flat-again)) | 16,270 | **117** |
| `&C000–&FFFF` | 3 | play-area screen | 16,384 | 0 |

Every bank is spoken for. The two matrices in banks 1 and 5 are the clearest answer
to "what is the extra 64 KB actually *for*": they turn pathfinding from a per-agent
search into a single table read ([§6.4](#64-routing)).

**Bank 0's slack was a dash because nobody had measured it, and when the two halves
of the game were first assembled into one binary it came out at −4,443.** The
renderer and the build mode lived in `tests/uitest.asm`, the economy and the wheel
in `tests/simtest.asm`, and nothing linked both; 20,571 bytes of code and tables
wanted 16,128. Three decisions closed it:

- **The world generator is not resident** (2,931). It runs once, before anything
  else exists, and [§5.10](#510-player-modification) already says a load reads the
  plane off disc instead. It is a separate loadable — `GEN.BIN`, loaded at `&8000`
  and overwritten later by bank 2's data ([§13.1](#131-three-ways-a-loader-does-not-run)).
  Not at `&0100`, where the game goes: while the firmware is alive the lower ROM
  covers `&0000–&3FFF`, so code there cannot run.
- **`MAX_NODES` is 96, not 128.** Both routing matrices are *nodes* × 128 bytes, so
  96 nodes costs 12 KB instead of 16 and frees 4 KB in each of banks 1 and 5. The
  room icons `m` and `l` (3,936) moved into bank 1's share, which freed the same
  amount of **code** space in bank 2. A node is a dome's id or `MAX_DOME + `
  a structure's, so the split is now 64 domes + **32** structures. Bank 1 is the
  window's default content, so the icons cost a page switch only in the object
  pass, which has bank 6 in.
- **Bank 2 holds code.** It was always visible and always treated as data; its
  image is now trimmed to the 11,264 bytes it actually uses, and `build.asm`,
  `route.asm`, `sound.asm`, `save.asm`, `hw.asm` and the ghost's 1,600-byte undo
  log live above it.

**Milestone 30 measured where bank 0 actually goes, and moved three things.**
`tools/mapsize.py` assembles a copy of `main.asm` with a label before every
`include` and reads the sizes out of the symbol table — the first time the question
"who is eating bank 0?" had an answer instead of an estimate. The answer: `object`
2,908, `ui` 2,164, `econ` 1,418, `jobs` 1,091, `hud` 992, `needs` 963, and a tail of
twenty smaller ones. Nothing there is obviously wasteful, so the space came from
moving rather than shrinking:

| Moved | Bytes | Why it is safe |
|---|---|---|
| the 512-byte figure cache, bank 2 → **bank 6** | +512 to bank 2 | only the object pass touches it, and that pass already has bank 6 paged in for the quadrants and figures |
| `save.asm` + `hw.asm`, bank 0 → **bank 2** | +496 to bank 0 | both are cold — `S`/`L` and one call at boot — and bank 2 is always visible, so code there is simply code |
| the loader's endgame, `&3F80` → **`&3FC0`** | +64 to bank 0 | the endgame is 40 bytes and was being given 128; `tools/mkdsk.py` now reads the address out of `src/boot.asm` instead of keeping a second copy of it |

**Bank 0 went from 82 bytes free to 642**, bank 2's code area from 50 to 66, bank 6
from 668 to 156. The figure between banks is not fungible — what is scarce is bank 0
— so the trade is worth making again the next time it is available.

#### Milestone 31 found the floor under bank 0, and it is not `&3FC0`

The terrain rule of [§6.5](#65-economy) is 110 bytes and belongs in `build.asm`, which
runs from bank 2's code area — where 66 bytes were left. The obvious move was to send
`save.asm` (350) back to bank 0, which had 642: both areas are always visible, so
which one a routine lives in is pure allocation. It assembled, it fitted, and
**`tests/test_save.py` then reported that the disc no longer saves.**

It saved fine. `tests/plane.asm` — the probe that samples the world plane out of the
paged bank, because the emulator's `read_ram` cannot see it — ran at **`&3E00`**, and
so did two probes in `test_disc`. With 350 bytes more in bank 0 the game's code
reached `&3EA3`, so the test overwrote the code it was about to exercise and then
blamed the disc. The reserve had never been written down anywhere, which is how it
cost an hour.

Two things came out of that, and the 110 bytes went into `src/terrain.asm` in bank 0
instead, with a `jp` from bank 2:

- **The floor is a check now.** `tools/mkdsk.py` refuses to build if bank 0's code
  passes `TEST_FLOOR`, naming the three tests that live above it. The negative
  control is the same one every ceiling here gets: lower the constant, watch the
  build stop.
- **And it is 192 bytes higher than it was.** The scaffolding is 33 bytes of code and
  a 256-byte buffer, not 512, so it moved from `&3E00` to `&3EC0`. `mkdsk` also
  prints the distance to *that* floor rather than to the loader's endgame: the old
  line said 512 free where 320 were free, which is the kind of number that is worse
  than none.

So bank 0's usable ceiling is **`&3EC0`**, and the next thing that needs those last
320 bytes should take the probes' addresses from `ZZ_BANK0_END` and move their buffer
into bank 2's ghost log — rather than lower the floor and rediscover this.

The result was 2,108 free in bank 0 and 708 in bank 2 — about 2.8 KB for save/load,
audio, meteors and intruders, with bank 7's reserved 1,024-byte `text` block
untouched behind it. `tests/test_game.py` builds the whole thing, so the number
cannot drift back without a test failing to assemble.

**Save and load spent 842 of it** (`fdc.asm`, `save.asm`, and the two keys in the
UI), and the ceiling turned out to be lower than `&4000`: the loader leaves its
endgame at `&3F80` and copies it there *after* the game is in memory
([§13.1](#131-three-ways-a-loader-does-not-run)), so bank-0 code must stop below
that, checked by `tools/mkdsk.py` on every build — the failure mode otherwise is a
machine that loads perfectly and hangs, with nothing in the build to point at.

**That address was `&3E00` until milestone 26, and the endgame is forty bytes.** A
round number was holding 512 for a routine that needs 128 with room to spare, and
the rooms of [§6.1](#61-the-colony-as-tables) did not fit in what was left. Moving
it to `&3F80` handed bank 0 back **384 bytes** — the cheapest space in the project,
and it was sitting in a constant.


**Bank 0, module by module, measured** (milestone 22, by marking every `include` and
reading the symbol table back):

| | bytes | | bytes |
|---|---|---|---|
| `object.asm` | 2,891 | `newgame.asm` | 667 |
| `ui.asm` | 2,334 | `tiles.asm` | 629 |
| `econ.asm` | 1,391 | `ship.asm` | 571 |
| `hud.asm` | 1,072 | `blit.asm` | 415 |
| `jobs.asm` | 1,020 | `ghost.asm` | 396 |
| `needs.asm` | 957 | `save.asm` | 350 |
| `dirty.asm` | 669 | `graph.asm` | 314 |
| | | `input.asm` | 288 |
| | | `fdc.asm` | 284 |
| | | `view.asm` | 242 |
| | | `wheel.asm` | 212 |
| | | `hw.asm` + `screen.asm` | 267 |

**Milestone 22 ended with 37 bytes left**, and the cheapest move looked like sending
`fdc.asm` + `save.asm` (634) and `newgame.asm` (667) to bank 2, all three being code
that runs once or on a keypress and never inside the wheel — paid for out of `GH_LOG`.

#### The ghost log is not slack, and that was measured before anything moved

Milestone 22 ended with 37 free bytes in bank 0 and a plan: move `fdc.asm`,
`save.asm` and `newgame.asm` (1,301 bytes of cold code) into bank 2, paying for the
room out of `GH_LOG` — 1,600 bytes of ghost undo log that *looked* generous.

**It is not generous. A `DOME L` ghost logs 1,532 of those 1,600 bytes.** Measured by
reading `gh_ptr` while each ghost is on screen:

| footprint | logged |
|---|---|
| cursor alone (`LOOK`) | 124 |
| 2×2 | 348 |
| 3×3 | 592 |
| 4×4 | 776–876 |
| 6×6 (`DOME M`) | 1,204 |
| **8×8 (`DOME L`)** | **1,532** |

68 bytes of headroom. `gh_run` refuses to log a strip it cannot undo — it silently
*skips drawing* it — so a smaller log would not corrupt anything, it would quietly
drop pieces of the biggest ghost. The plan was wrong and the measurement cost an hour
instead of a milestone.

**Milestone 30 paid for the same move out of the other pocket.** With `GH_LOG` ruled
out, the 512-byte figure cache was the only other thing above `PAGE2_TOP` that did not
have to be there: every read and write of it happens inside the object pass, which
already has bank 6 paged in for the quadrants and the figures, so it moved into bank 6
and bank 2's code area grew by exactly its size. `save.asm` and `hw.asm` — 496 bytes
of code that runs on a keypress and at boot — moved up into the room that made, and
bank 0 went from **82 to 642 free** ([§4.2](#42-the-eight-banks)). A corridor route's
own ghost, measured the same way, logs 284 bytes for six tiles, so the log's headroom
is set by `DOME L` and nothing else.

**Milestone 40 measured the corridor side properly, since the rectangles of milestone
35 changed every figure above.** A corridor preview logs exactly the cursor's frame —
one tile, four rectangles, **56 bytes** — and one 2×4 mark, **12 bytes**, per route tile
in view. The route is monotone, one tile per column (or per row on a vertical run), so
the view's 20 columns bound it: an exhaustive search over `tools/route.py` — every size
pair, centres up to ±32 × ±24 tiles apart, 21,836 routable geometries, and every camera
that shows the destination — finds at most **21 visible tiles, 308 bytes**. The game
logs exactly that, and exactly `56 + 12·n` in thirty-six other geometries and cameras
(`tests/test_link.py` keeps six). The red `DOME L` over its own site is still the worst
ghost there is, **1,160 bytes** (frame 392 + 64 marks), measured again by
`tests/test_reveal.py`; nothing in placement marks more than its 64 tiles. **The log
held 1,600, so 440 bytes of it had never been used by anything** — the room bank 2's
code area had been short of since milestone 38.

**Milestone 41 cut it to exactly that ghost.** `GH_LOG` is no longer a number but a
formula in `src/const.asm` — the large dome's frame (four rectangles: two edges of
2 × 32 bytes, two sides of 124 × 1, a 4-byte header each) plus a 2×4 mark on each of
its 64 tiles — and comes to **1,160**. A larger footprint changes `GH_SIDE`, and the
log follows; the save's 512-byte header, which borrows the start of the log, is an
`assert`. Since nothing is spare any more, "it fits" became a check rather than a
measurement: `tests/test_reveal.py` requires the red `DOME L` to log **all** 1,160 bytes,
because a rectangle that does not fit is silently not drawn and 12 bytes fewer would be
the only trace of a missing mark — and with the limit one byte lower, it logs 1,148.
The 440 bytes paid for moving the cold half of the object index up into bank 2
([§8.4](#84-object-pass-and-draw-order)): bank 0 went from **88 to 428 free**, bank 2's
code area from 15 to 108. Milestone 42 spent 220 of the 428 on redrawing an emptied
ring slot properly ([§8.5](#85-the-dirty-list)), which left 208; milestone 43 took
737 back by shrinking the object pass ([§8.4](#84-object-pass-and-draw-order)), and
milestone 44 another 283 out of the interface the same way: **1,228**. Milestone 45
spent 750 of it on fitting a dome slot by slot
([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)): **478**. Milestone 46
took 422 back out of the economy the way 43 and 44 did out of the renderer and the
interface ([§6.5](#smaller-at-milestone-46)): **900**; milestone 47 another 272 out of the
job board ([§6.7](#smaller-at-milestone-47)): **1,172**; milestone 52 another 399 out of
the HUD ([§9.2](#smaller-at-milestone-52)): **1,571**; milestone 53 another 187 out of
the needs pass ([§6.6](#smaller-at-milestone-53)): **1,758**; milestone 54 another 173 out
of the dirty list ([§8.5](#smaller-at-milestone-54)): **1,931**; milestone 55 another 91
out of the fitting ([§9.3](#smaller-at-milestone-55)): **2,022**; milestone 56 another
112 out of the tile pass, which got 8% faster on the way
([§8.3](#smaller-and-faster-at-milestone-56)): **2,134**; milestone 57 another 197 out
of the ships and the milestones ([§10.2](#smaller-at-milestone-57)): **2,331**;
milestone 58 another 56 out of the ghost, which got faster everywhere
([§9.3](#smaller-and-faster-at-milestone-58)): **2,387**; milestone 59 another 124 out
of the agents' movement, whose slot of the wheel got 31 % faster
([§6.3](#smaller-and-faster-at-milestone-59)): **2,511**; milestone 60 another 92 out
of the rooms and the catalogue ([§6.5](#smaller-and-faster-at-milestone-60)):
**2,603**.

A first attempt at the same measurement said the log runs to 1,600 with nothing but
the cursor on screen. That was the *measurement* breaking the thing it measured:
filling the buffer with a marker byte destroys the records `gh_undo` is about to
replay, and `gh_undo` then walks garbage headers and scribbles over memory until it
happens to land on `gh_ptr`. Reading `gh_ptr` while the ghost is up costs nothing and
tells the truth.

**Milestone 23 spent the `text` block.** All 35 strings of `hud.asm` and `ui.asm` —
496 bytes — moved to `src/uitext.asm`, which assembles into bank 7 at `G_text`, and
bank 0 went from **37 to 488 free**. The mechanism is 14 bytes: `hud_text7` pages
bank 7 in, calls `hud_text`, pages bank 1 back. `ui_msg` does the same around both
its print *and* its length walk, and `sl_digit` around its three patches.

Three things that are true of that bank and of nothing else:

- **Only read-only data can go there.** Bank 7 lives in the `&4000–&7FFF` window, so
  code placed there would erase itself the moment it paged bank 4 or 6 in.
- **The address has two forms.** Inside rasm's `bankset 1` the bank sits at `&C000`;
  paged in the game it sits at `&4000`. `uitext.asm` writes the bytes at the first and
  defines every label as the second. (`bank 7` would give the right labels directly,
  but rasm refuses it once `bankset 1` has claimed the bank.)
- **The disc needs a ninth file.** `BANK7.BIN` is built by `tools/pack.py`, which
  knows nothing about the game's words, so the text is saved separately as `TEXT.BIN`
  and the loader drops it over the reserved hole — *after* `BANK7.BIN`, which would
  otherwise overwrite it.

What is left of the reserves: 528 bytes of the `text` block, the 2,048-byte `audio`
block (the sound of [§9.5](#95-sound) fitted in bank 2 instead), and bank 7's own 440.
Bank 2's code area is still 69 bytes and there is still no way to grow it.


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
| Machines, **all 12**, `beds` and `medstore` included | 1,584 |
| Corridors + connectors | 896 |
| ~~4×8 font, 96 glyphs~~ — **bank 7 since milestone 33** | ~~1,536~~ |
| Asset tables, `room_machines` included | 313 |
| Generated pointer tables (`tile_ptr`, `icon_{s,m,l}_ptr`, `mach_ptr`, `struct_ptr`) | 176 |
| ~~Cursor and UI chrome (reserve)~~ — **dropped at milestone 33** | ~~256~~ |
| Node graph (`node_deg`, `node_adj`) and BFS workspace | 1,536 |
| Machine recipes (12 × 10) + the "needs an operator" lookup | 132 |
| Economy state — stocks, flows, clock, weather, ships, milestones, meteors | 91 |
| Job board 160 · room index 108 | 268 |
| **Sub-total, the data arena** | **9,592** — what `tools/pack.py` lays out; the meteors' 5 bytes came out of the padding before the page-aligned routing tables |
| The ghost's undo log (`GH_BUF`, [§9.3](#93-build-flow)) — the worst ghost, computed, since milestone 41 | 1,160 |
| Code that runs from here: `build`, `route`, `sound`, `meteor`, `objindex`, `save`, `hw`, `fdc`, `newgame` | 5,524 |
| **Total** | **16,276** of 16,384 — **108 free** |

#### Milestone 33: two reservations nobody read, and what they bought

Two blocks in the map had been waiting since the first layout for something that never
came, and a search for readers found **none** for either:

- **`ui_cursor`, 256 bytes of bank 2.** The cursor turned out to be the ghost's own
  frame (`gh_box`, milestone 6b); nothing ever drew from here. It sat in front of three
  page-aligned routing tables, so it cost exactly 256 bytes of code space.
- **`audio`, 2,048 bytes of bank 7.** Reserved for in-game music, which
  [§9.5](#95-sound) decided *against*. The effects live in bank 2's code and the
  loading tune in the generator.

The font went into the second. It has exactly **one** reader — `hc_draw` in
`src/hud.asm` — and that reader writes to the screen at `&C000`, outside the window, so
it can have bank 7 paged in for the sixteen bytes of a glyph and see both. It pages back
to *whatever the caller had*, not to bank 1: `hud_text7` and `ui_msg` read the next
character of their string out of bank 7 straight afterwards, and "back to bank 1" there
would hand them `DIST`. The price, measured by `tests/test_hud.py`: a **cold** HUD
redraw 43,930 → 45,926 µs (+4.5%, two `out`s per glyph), a **warm** one unchanged at
22,963 µs, because cells the cache already holds never reach `hc_draw`.

Together that is 1,792 bytes out of bank 2's data arena, and everything after the arena
— the undo log, then the code — moved down by the same amount. The code area went from
62 bytes free to 1,854, which is the room [§15](#15-open-risks) had been waiting for
since milestone 30: **`newgame.asm` and `fdc.asm` (957 bytes) followed `save.asm` into
bank 2**, and bank 0 went from **80 bytes free to 1,037**.

Moving the arena turned up two things that had been true only because it never moved:

- **The save file named its block by number.** `sv_blocks` said `dw #A400`, and after
  the move the economy started at `&9D7D` — *below* the block. The disc would have saved
  graph and job board and no stocks at all, and the load would have reported success.
  The block is `G_hud_shadow − 2,048` now, with an `assert` that the economy is inside
  it, and `SV_VER` is 2 so a save from the old layout is refused rather than misread.
  `tests/test_save.py` had the same `0xA400` written a second time; it reads the layout
  now.
- **The loader had been clipping bank 2's data for some time.** `page2.bin` is loaded
  into bank 5 at `&4000` and `game2.bin` into the same bank at `&6C00`, and at 11,384
  bytes the first reached `&6C78`. The last 120 bytes — exactly the HUD's cell cache —
  arrived in the game full of bank-2 code. Harmless only because that cache is
  invalidated before it is read, and invisible from every test that boots a snapshot.
  `tools/mkdsk.py` checks both scratch ceilings now; the negative control, the old size,
  reports those same 120 bytes.
- **And at milestone 38 the code outgrew its own scratch.** `game2.bin` loads at
  `&6C00`, which left 5,120 bytes below `&8000`; the meteors took it to 5,186 and
  `tools/mkdsk.py` refused the disc. The data below ends at `&6578`, so the scratch
  moved down to **`&6800`**: 6,144 bytes, more than bank 2 itself can hold above
  `PAGE2_CODE`. The binding limit is bank 2 again, where it belongs.

That total used to read *15,163, 1,024 free, contiguous*, which stopped being true
when the undo log and the bank-2 code block moved in and was never corrected. The
authority is `build/layout.txt`, which is regenerated on every build; a figure copied
into prose drifts, and this document has now been caught doing it twice — here and in
bank 6's slack ([§15](#15-open-risks)).

`struct_ptr` is new: the renderer indexes external structures as
`kind*4 + size` and four of the eight kinds exist in one size only, so the table
carries zeros for the gaps exactly as `struct_dims` does. Adding 64 bytes cost
256, because the three 256-aligned routing tables that follow it had to move up a
page. That is the price of alignment and it is paid once.

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

**Since milestone 31 that guarantee is load-bearing rather than decorative.** A water
extractor can only be built at a lake and a mine only at a vein
([§6.5](#65-economy)), so a seed with no reachable water really is a seed that cannot
be played — which is what the first paragraph of this section claimed before anything
depended on it. In the game's own start seed the nearest shore that takes a 3×3 is 4
tiles from the colony and the nearest ground that takes a 4×4 next to a vein is 7.

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

**Built, and it cost 63 bytes of code.** The planet is `(seed_hi XOR seed_lo) AND 3`,
chosen by the generator, so two bytes of seed still name a whole world — planet
included. It travels in the four `worldinfo` bytes the generator leaves in bank 6,
goes into the save header, and reaches the screen as four pen writes
([§8.6](#86-palette)). Measured on seed `ACE1`, out of 16,384 tiles:

| Planet | Water | Mountain | Fertile ground |
|---|---|---|---|
| 0 desert | 4,070 | 3,914 | 3,394 |
| 1 ice | 6,743 | 4,167 | 2,453 |
| 2 storm | 2,840 | 5,297 | 1,961 |
| 3 barren | 1,134 | 4,729 | **0** |

All four are playable — water and ore within 30 tiles of the centre for 64 seeds
each (`tests/test_worldgen.py`). **The Z80 had never run with a planet other than
zero**, and when it finally did, it read the thresholds from `planet*4` instead of
`planet*6`: the comment said `*6`, the code said `*4`, and at planet 0 the two agree.
The reference comparison caught it on the first run.

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

13.5 s is tolerable for a new game. **It is not tolerable on load** — see
[§5.10](#510-player-modification).

The generator was going to run in slices behind a `GENERATING` progress bar. It
still runs in one blocking call from the loader, before the game's own code exists
— but **there is a progress bar now**, and it needed none of the game: the loader
puts the machine in Mode 1 and writes a title with firmware text calls, and the
generator pokes a 64-byte bar straight into screen memory, one byte per two rows of
`wg_plane` ([§13.2](#132-the-loading-screen)). Thirty bytes of code. The slice
structure is still unused, and the border codes are still there underneath.

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

- **The far node is full.** All 8 ring slots taken. The colonist **goes in
  anyway**, with `slot = 255`: present, but not drawn. The ring has eight places
  because the sprite has eight, and that is a *drawing* limit, not a door.

  It was a door in the first version — the colonist waited outside with `progress`
  pinned at 255 — and that produced a deadlock nobody would find by reading: **a full
  dome whose machine had broken could never be repaired.** The mechanic queued at the
  entrance, and the eight inside had no reason to leave, because their needs were met.
  The colony simply lost a machine permanently. Found by watching an engineer stand
  outside dome 12 for 2,560 frames with the repair job still in his hand.
- **`NEXTHOP` says unreachable.** The agent sets `dest = node` and gives up rather
  than standing still forever with an impossible order. This is what happens to
  anyone whose destination was cut off while they were walking to it.

  **And it drops the job as well**, which it did not until milestone 26. Giving up
  the destination while keeping `task` leaves the job board holding an assignment on
  someone who is never going to start: the board only reaps a job when the agent's
  task stops pointing at it ([§6.7](#67-jobs)). The window that makes this happen is
  ordinary — a building placed while the routing rebuild is still running
  ([§6.4](#64-routing)) is unreachable for about five seconds, and whoever is handed
  the Build job in those five seconds resigns and keeps it. Measured: the same small
  dome finished in **400 frames** or in **10,800**, and the 10,800 was how long it
  took the engineer to get hungry, because a need is the only other thing that clears
  a task.

**Measured at 130 µs per agent** (`tests/test_sim.py`), against the 150 µs estimated
here — one of the few numbers in this document that came in under. A full movement
slot of 12 agents was 1,560 µs against the 1,800 µs budgeted in
[§7.2](#72-the-wheel), and is **899** since milestone 59
([below](#smaller-and-faster-at-milestone-59)). No pathfinding, no collision,
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

#### Smaller and faster, at milestone 59

`src/entity.asm` went from 449 bytes to **325**, and movement got faster. Over the 723
operations below, measured with interrupts off:

- slices are 27 % faster;
- `ent_claim` is 26 % faster;
- `ent_release` is 7 % faster.

Not one operation got slower. In the game's own terms, the movement slot of
`test_sim.py` went from 1,298 µs to **899**, and a whole turn of the wheel from
40.9 ms to 36.9. `newgame.asm` gave 3 bytes of bank 2 back with it.

The check was a script kept out of the repository. It calls `ent_move_slice` directly,
on 40 agent states drawn from a fixed seed. The colony's graph gets what it lacks:

- structures hung on domes (nodes 64–71, one of them hung on another structure);
- a pair of nodes that reaches nothing, and a node on its own;
- after routing, a dome that loses its edges, and a dome with an adjacency entry that
  `NEXTHOP` does not know.

The states hold dead agents, and agents on an edge with progress at the line of
arrival. They hold agents at their destination, and agents whose destination is
reachable or unreachable. They hold working agents leaving a dome or a structure,
agents with and without a slot, and occupancy masks full, empty and half full.

Each state runs ten slices: whole, wrapped round 127, and empty. After every slice the
script compares all of bank 6, every `wh_push` (kind, B, C) and the time. It also calls
`ent_claim` and `ent_release` the way `newgame.asm` and `needs.asm` do. All 723
operations were identical with the old files and the new ones.

- **The agent's id stays in a register.** The fields are in pages, so a field is one
  `ld h` and one `set` or `res 7,l` away. The old code read `em_id` back from memory
  before each field — three times on the travelling path alone. Now the slice hands
  the id over in `L`. `em_id` is written only when someone leaves a node, where
  `ent_release` needs it.
- **The neighbour is found with `cpir`.** Each adjacency list starts on a multiple of
  8, so the neighbour's index is the low three bits of where the search stopped.
- **Two addresses without a 16-bit add:**
  - `G_node_adj + node × 8` is `(G_node_adj/8 + node) × 8`, with no carry in the low
    byte. That is `assert`ed.
  - `NEXTHOP`'s row is `(node + 128) / 2` in `H`. The bit that drops out lands above
    `dest` in `L`.
- **`ent_claim` takes the node in `A`**, which both its callers already had. `em_dst`
  is gone, and with it a store in `newgame.asm`. `ec_slot`, `er_slot` and `em_nh`
  became registers.
- **Smaller pieces:**
  - `F_WORKING` is tested and cleared with `bit`/`res 5`.
  - The slot's bit is cleared with `or (hl)` / `xor (hl)`.
  - Bank 6 is paged back with `ld c,PAGE_B6`, because `B` still holds the port.
  - The slice wraps with `res 7,c`.

`wh_push` says it clobbers whatever its handler clobbers. `dirty_push` happens to keep
`BC`, but `ent_claim` does not lean on that. It keeps the slot on the stack across the
call, for one byte.

**What the planted faults found.** Twenty-eight faults were run against the script and
against `test_sim.py`, `test_needs.py` and `test_game.py`. The script caught
twenty-six. Of the other two:

- One only costs time: an agent already at its destination looks `NEXTHOP` up
  anyway, and the lookup leads nowhere. The script's clock caught it: slices were 13 %
  faster instead of 27 %.
- The other is in `newgame.asm`, which the script does not run.

Nine passed all three tests:

- the slice not wrapping at 128;
- a node with no edges searching 64 KB;
- a stale `NEXTHOP` followed anyway;
- a working agent keeping its flag as it leaves;
- operators taken off a structure, which writes past the dome table;
- a `wh_push` for a structure, on a claim and on a release (two faults);
- the clock fault above;
- `ng_people` giving `ent_claim` the role instead of the node.

They are checked now:

- `test_sim.py` calls `ent_move_slice` directly in twelve such states, against
  `tools/entity.py`. After every slice it compares the fields, the masks, the dome
  table and the `wh_push`es that the reference implies. It also checks that the rest
  of bank 6 is untouched. The negative takes the wrap out.
  - The first version left the rare branches to the random draw, and the stale
    `NEXTHOP` fault still passed: no agent in twelve states happened to stand on
    dome 3 heading for the forgotten neighbour. Now four agents in every state are
    pinned there: stale, without edges, unreachable, and working on a structure.
- `test_game.py` checks that the starting colony's occupancy masks are exactly where
  its colonists stand.

Together they catch the eight faults that change behaviour. The clock fault changes
nothing a test can see, so it stays the script's. With the old `entity.asm`, every
new check passes except the negative, which looks for `res 7,c`.

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
| Power | `solar` (day only), `turbine` (wind), stored in `collector` | every machine, lighting at night | machines stop, **then** oxygen stops — three levels, [below](#machines-stop-then-oxygen-stops--and-that-then-was-missing) |
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

#### `(on water)` and `(on ore)` are rules now, not captions

The first two lines of that chain carried their terrain in brackets from the first
draft, and for thirty milestones nothing read them: a water extractor could be built
in the middle of the desert, inside the base, anywhere a 3×3 of ground was free, and
it produced the same 5 Water a cycle. So could a mine. The lake was scenery, the ore
vein was scenery, and the thirteen seconds of world generation ([§5](#5-procedural-world-generation))
bought a picture that no decision ever consulted.

The rule, in `bd_res`: **the footprint stays on buildable ground — ground, dust or
foundation, exactly as before — and the material must lie within two tiles of it.**
Water is a shallow or deep tile; ore is a mountain tile with bit 3 of the world byte
set ([§3.5](#35-the-world-byte)), which is the same bit `tile_ore_overlay` has been
drawing on the mountains all along. Neither structure can stand *on* its material,
because neither water nor mountain is buildable — so "on water" in the table above
means *at the water*, and the pump sits on the shore.

**Two tiles, and that number is measured.** With one, the pump was fine — a shore
is buildable ground touching water — and the mine was impossible *everywhere*:
elevation climbs mountain → rock → ground, rock is not buildable, so between a vein
and the nearest ground there is always at least one ring of rock. In the game's own
world the nearest buildable 4×4 to a vein is **exactly 2** tiles away, seven tiles
from the colony.

The check runs only when the footprint has already passed, which is both cheaper and
the reason the two-tile margin cannot read outside the plane: from `R_RIM` = 57
outward the generator adds 40 to the elevation per ring ([§5.5](#55-centre-plateau-and-world-rim)),
so at r ≥ 62 every tile clears the highest of the four planets' mountain thresholds
(205) and nothing there is buildable. A valid footprint therefore lives inside
±61 and the scan inside ±63.

**What it costs, measured** (2,000 calls of `bd_check` with the wheel stopped): a
3×3 footprint with no material to look for is **1,208 µs**; the pump at a shore, where
the water turns up early in the scan, is **1,817**; the pump on dry ground, which is
the full 7×7 with nothing in it, is **3,375**; and the mine's 8×8 worst case is
**3,994**. A cursor step cost 16,224 µs when this was measured
([§9.1](#91-controls)), so the worst case added about 15% to it — and only for the two
items that ask for anything. Milestone 35 made the step itself cheaper (6,240 µs in
`LOOK`), so the share is larger now; the cost is still 4 ms. Nothing else in the catalogue pays a byte or a
microsecond.

**This is what makes [§5.6](#56-feature-anchors)'s guarantee load-bearing.** *Water
and an ore vein within 30 tiles of the centre, 512 seeds out of 512* used to be a
promise about scenery; it is now the promise that the map you were given can be
played. And the refusal says which material is missing — `NEEDS WATER NEARBY`,
`NEEDS AN ORE VEIN` — because with no bad tile to tint red, a bare `BLOCKED` on clean
ground reads as a bug in the game ([§9.3](#93-build-flow)).

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

#### The economy has a clock, and it was missing

Every rate in the table below reads **per sol**. Nothing in the code did. Production
and the flow balance are wheel slots, so they ran **750 times a sol**: the oxygen
generator drank the colony's 60 Water in twenty seconds and everyone was dead inside a
sol and a half, with a solar panel or without one. The rates were not wrong. The clock
was missing. Measured by `tools/balance.py`, which runs the real binary at ×4 and
samples the economy every few seconds — the curve cannot be read off the source.

There is a clock now, and it has two hands:

- **`ECON_DIV = 16`.** Production visits 16 domes once every 16 revolutions, so a full
  64-dome sweep — and therefore **every machine** — comes round once per **64
  revolutions**: 11.7 times a sol. That is the economy's cycle.
- **`FLOW_DIV = 64`.** The battery charges and the pumps deliver on that same cycle.
  Charging per *revolution* made a 360-unit collector drain in 18 of them — 6% of a
  300-revolution night, a battery that was decoration. On the cycle the same 360 is
  more than thirty cycles of the opening colony's demand, which is what makes a
  collector a decision instead of a decoration.

Two things stay on the fast clock, and both for a reason. The **living are counted
every revolution**, because that is [§10.3](#103-win-and-loss)'s only loss condition
and it should not wait twenty seconds. And a **building that finishes kicks the
balance** to run on the next revolution instead of up to 64 later: without it the
player's first solar panel produced power while the HUD still said `NO POWER`.

#### Power is demand, not consumption

`mach_power` used to be what the machines *burned*. During a blackout they burn
nothing — so demand read zero, the balance found 0 ≥ 0, the power came back, the
machines ran, demand rose, and the power went out again. **At 50% duty, forever.** A
colony with no power source at all got half its oxygen free and lived five sols on it.
The accumulator now counts what each machine *would* draw — operator present, inputs
in stock, only the power missing — so a blackout stays a blackout until something
changes it, and [§10.1](#101-start-state)'s "you need power before anything else"
became true for the first time.

#### Machines stop, *then* oxygen stops — and that `then` was missing

The failure column of the flow table above has said *machines stop, then oxygen stops*
since the first draft. The code had no *then*: `power_ok` was one flag for the whole
colony, so the blackout that stopped the pumps stopped the oxygen generator in the
same revolution.

That is not a detail, because it punished the right move. Milestone 31 measured that
the answer to water is a second extractor; a second extractor takes demand from 22 to
28 against two panels' 36, the day banks about 50 and the night wants about 130. So
the colony blacked out **every** night — measured over 8,000 frames with two pumps:
**13 of 80 samples with no power, oxygen production 20 → 0, the worst colonist's
oxygen bar down to 208.**

There are three levels now, and the flow balance picks one per cycle:

| `EC_POK` | What runs | When |
|---|---|---|
| `P_ALL` = 1 | everything | production covers demand, or the battery covers the shortfall **and still keeps the reserve** |
| `P_ESS` = 2 | only `MF_FLOW` machines — life support | production or battery covers those, but not the rest |
| `P_NONE` = 0 | nothing | not even life support can be paid for |

**The battery keeps a reserve, and the negative control says exactly what that buys.**
The battery lends to the machines only while `essential × RESERVE_CYCLES` stays behind
it — eight cycles, because a night is 40% of a sol and a cycle is 1/11.7 of one (4.7
cycles), leaving room for a sandstorm. Setting that constant to zero and re-running the
colony **still passes**: on a four-person base the night is short enough that the
machines never quite empty the battery, so what saves the oxygen there is the *level*,
not the reserve. Where the reserve pays is a long night — a storm, or a bigger base.
Eight cycles of darkness at demand 16 against 4 of life support, measured on the
reference implementation:

```
with the reserve     P_ALL P_ESS P_ESS P_ESS P_ESS P_ESS P_ESS P_ESS   battery 12 at dawn
without it           P_ALL P_ALL P_ALL P_ESS P_ESS P_NONE P_NONE P_NONE   battery 0
```

Three cycles of machines, and then nobody breathes for three. That contrast is a check
of its own in `tests/test_power.py`, because a constant nobody can knock over is a
constant nobody has tested.

It also makes the collector a ladder rather than a switch: at 60 units the machines
run one more cycle into the night, at 200 they run all night, and the player can see
which by watching the battery. The essential demand is accumulated separately by the
production pass (`EC_ACCE` → `EC_EPOWER`) exactly as `EC_ACCP` → `EC_MPOWER` is, so it
costs one more accumulator and no scan.

Measured on the same colony after the change: **0 of 80 samples without power, oxygen
production never leaves 20, the worst oxygen bar 251 instead of 208** — and the price,
which is real and visible, is that the pumps are among the loads that fall, so water
climbs 63 → 147 over the window instead of 63 → 153. `tests/test_power.py` holds both
halves: the rule on the reference implementation, one unit either side of the
threshold, and the colony in the real binary.

**And the constant has to drive the code.** The first version of the reserve was three
hard-coded `add hl,hl` with `; × RESERVE_CYC` written beside them. Setting the constant
to zero changed **not one byte** of the binary, so the first negative control "passed"
with no reserve at all and proved nothing. It is `repeat RESERVE_SH` now, and the
control moves the binary — which is the only reason its result can be believed.

The alert line says `LOW POWER` while load is shed, and keeps `NO POWER` for a real
blackout ([§9.2](#92-hud)). The klaxon stays on the blackout only — a siren every
dusk would be noise — and a sol spent shedding does **not** count as an all-green sol
for [§10.2](#102-milestones).

#### The slot order is the room's order, not the table's

**Until milestone 45 a machine ran only if its slot index was below the dome's
operator count** ([§6.6](#66-needs)) — one person inside turned slot 0 and nothing
else — so the order the slots were filled in *was* what the room produced, and filling
them in the numeric order of `room_machines` left that to the asset table. The Lab accepts `processors`,
`medical` and `vitromeat`; numerically processors comes first, which Control makes
anyway, so **no Lab ever produced vitromeat**. The greenhouse was worse: `plant_class`
numbers plants 0–4 Starch and 5–9 Vegetables, so a medium greenhouse planted four
Starch and no Vegetables and a large one reached Vegetables at slot 5. `mach_food`
wants Starch *and* Vegetables *and* Vitromeat, so every food run in
`tools/balance.py` ended the same way: a colony with a greenhouse, a lab and a
canteen starving beside a warehouse full of starch. Nothing was broken — each rule
was doing what it said — and no state check could have found it, because the state
was consistent.

Two tables in `src/rooms.asm` fix it, and both say the same thing:

- **`rm_pref`** — one machine per room takes slot 0, the one no other room makes:
  Lab → `vitromeat`, Factory → `iron`, Medbay → `beds`. Every other room has a single
  machine and needs no rule.
- **`rm_plants`** — the planting order rotates through the *classes* instead of the
  numbering: `0 5 10 11 1 6 2 7 3 8 4 9`. Small greenhouse: Starch. Medium: Starch,
  Vegetables, Medicinal, Tree — which is also where the morale tree of
  [§6.6](#66-needs) starts appearing without being asked for. Large: that plus
  Starch, Vegetables, Starch, Vegetables, in different varieties so a dome is not
  four copies of one sprite.

`tests/test_build.py` calls `rm_build` directly and asserts both orders, with the
numeric order as the negative control. Since milestone 60 it checks every room and
size against a model ([below](#smaller-and-faster-at-milestone-60)).

**Since milestone 45 the slots are the player's** ([below](#a-room-says-what-fits-the-player-says-what-goes-in)),
and a player who puts one iron machine in slot 3 would, under that rule, have needed
four people in the dome to turn it. So the rule counts *machines* now: **the k-th
machine that wants an operator runs when the dome has k**, whatever slot it sits in
(`ed_k` in `src/econ.asm`, `k` in `tools/econ.py`). The two tables still earn their
place — `rm_pref`'s machine heads the fitting list and is its default, and
`rm_plants` is the greenhouse's MIXED crop. `tests/test_sim.py` checks the rule on the
reference: two iron machines in slots 3 and 6 make 0 / 1 / 2 / 2 Metal with 0–3
operators, where the old rule makes 0 / 0 / 0 / 0. Z80 against reference over sparse
slots is the shared run's job — the populated colony leaves one slot in five empty,
with random operator counts.

`machine_rules` in the asset data already constrains placement: `mach_oxygen` is
`bit0` only, meaning **oxygen generators fit only in small domes**. That is honoured as
a design constraint rather than patched around — it forces a spread of small life-support
domes rather than one oxygen cathedral, which is a better-shaped base.

Balance, with the clock above in force. **Power is a rate**, compared production
against demand once per cycle; **materials are amounts**, delivered once per cycle,
which is 11.7 times a sol (one sol = 4 real minutes):

| | Produces | Consumes | Per sol |
|---|---|---|---|
| Colonist | — | 2 O₂ | ≈ 1 Water, 1 Meal |
| `mach_oxygen` | 20 O₂ | 4 Power, 1 Water | 12 Water |
| `solar` s/m/l | 2 / 8 / 18 Power | daylight only | — |
| `turbine` s/m/l | 3 / 12 / 27 Power | wind-dependent | — |
| `collector` s/m/l | stores 40 / 160 / 360 Power | | fills at the day's surplus |
| `extractor` s/m/l | 1 / 2 / 5 Water | 1 / 3 / 6 Power | 12 / 23 / 58 Water |
| `mine` | 2 Ore | 8 Power, 2 drillers | 23 Ore |
| `mach_iron` | 1 Metal | 2 Ore, 3 Power | 12 Metal from 23 Ore |
| Greenhouse slot | 3 Starch / 2 Vegetables / 2 Medicinal, by `plant_class` | 1 Water, 1 Power | ×11.7 |
| `mach_vitromeat` | **2** Meat | 2 Water, 4 Power | a staffed lab: 6–7 Meat a sol |
| `mach_food` | 1 Meal | 1 Starch + 1 Vegetables + 1 Meat, 4 Power | one canteen feeds about six |

**The extractor also used to draw 12 Power**, two thirds of the large solar panel
that is the player's first building. That one number closed the opening: with the pump
running, the day's surplus fell to 1, a collector never charged, and the night took the
oxygen out whatever else was built ([§10.1](#101-start-state)). A pump is a third of a
panel now.

**The extractor and the mine used to read 6/24/54 Water and 20 Ore**, which were the
per-sol figures written straight into a per-cycle table: one small pump out-produced
the whole colony's thirst sixty-four times over and the water bar simply pinned at the
storage cap. The numbers above are the same intent at the cycle's scale — one large
pump covers the opening colony several times over — Water reaches 419 by sol 8 —
and one mine feeds exactly one `mach_iron`.

These numbers are a starting point for tuning, not a balance claim — and three of
them turned out to be unlivable the first time the whole loop ran
([§6.6](#66-needs)).

#### A room says what fits, the player says what goes in

This section was called *A room comes with its machines* until milestone 45: the
commit walked `room_machines`, kept what `machine_rules` let into that size, and dealt
the survivors **round robin** into the slots, and the dome's price covered them. A
large Factory came out with iron, bioplastic, weapons, robots, spares and iron again,
and there was no way to ask for eight iron machines when the colony was short of
metal (§15 carried it as a risk).

**Now, as in Planetbase, a dome is built empty and fitted slot by slot** — the
fitting screen, `UI_FIT` in `src/fit.asm` ([§9.3](#93-build-flow)):

- **`FIRE` on a dome in `LOOK`** opens it. Left/right picks a slot, which gets a box
  round it on the dome; up/down picks what goes in — `EMPTY`, or what `rm_build`
  allows in that room at that size, the room's main machine first and preselected.
  `FIRE` installs, `SPACE` installs the same thing into every slot as far as the
  materials go, `ESC` goes back. The panel says `< METAL    >  FE  8  BI  2` and
  `SLOT 2/8  UP/DN=PICK FIRE=FIT SPACE=ALL`; the box is green when the choice can be
  paid, red when it cannot, pink when it is already there.
- **A construction site can be fitted too.** The slots are written at once and drawn
  when the dome finishes (`dh_built` draws the machines); nothing is drawn onto a
  site, so `DK_MACH` is pushed only for a finished dome.
- **Every machine is paid for separately**, through the same `bd_afford` and
  `bd_stock_pay` as everything else that is built. Taking one out gives **half** its
  price back (rounded down, and not past the 600 cap). A replacement pays for the new
  machine *first* and then refunds the old, so its materials must be in store —
  as in Planetbase, where dismantling is its own act.
- **The greenhouse chooses a crop, not a variety:** Starch, Vegetables, Herbs, Tree —
  and MIXED. The variety follows the slot (the class's first plant, plus the slot
  mod 5 for the two five-variety crops) so a starch field is not eight copies of one
  sprite; MIXED is `rm_plants`, the old automatic mix, slot by slot.
- **A room still cannot change** after placement, and a room with no machines
  (Quarters, Storage, Lounge) does not open.

| | Metal | Bioplastic |
|---|---|---|
| Dome shell S / M / L | 12 / 24 / 40 | 8 / 14 / 24 |
| Oxygen, iron, bioplastic, spares, medical, vitromeat | 8 | 2 |
| Weapons, processors, robots | 10 | 4 |
| Food (`mach_food`) | 6 | 2 |
| Beds, medicine cabinet | 4 | 2 |
| A plant | 2 | 0 |

**A small dome with its one machine costs what it did, 20 / 10**, so the opening of
[§10.1](#101-start-state) is unchanged. Medium and large domes cost what they are
filled with: a large Factory full is 104 / 40 against 70 / 35 before, and an empty
one is 40 / 24.

**Taking a machine out needs a redraw nothing else did.** A machine is an opaque
6×22 sprite, so installing or replacing one is a blit over the old; an empty slot has
no sprite to blit. `dh_mach` sends an emptied slot to `dhv_rect` — the vacated ring
slot of milestone 42 ([§8.5](#85-the-dirty-list)), generalised from 2×8 to any
rectangle: the ground under the slot, then every object clipped to it. It is charged
`DHS_VAC_US` on top of the `DK_MACH` price, so nothing else follows it in that frame;
the worst loop round of the `FIRE` that empties a slot measured 40 ms.

`tests/test_fit.py` drives all of it with the keys, in the real binary.

**A greenhouse keeps plants in the same slots another dome keeps machines.** Same
field, different meaning, and the room type says which. `plant_class` decides the
output: starch, vegetables, medicine, or nothing at all for a tree, which is there for
morale.

**One biologist waters the whole garden.** This section used to say a greenhouse posts
as many `Operate` jobs as it has plants, and it did — the plant rule was the machine
rule, one slot one operator. A machine turned only while its slot index was below the
dome's operator count, so a medium greenhouse with one biologist grew **slot 0 and
nothing else**: 286 Starch and *zero* Vegetables while `mach_food` needs both. Four
plants meant four people, which is the entire opening colony, for one dome. A
greenhouse is a garden: whoever tends it tends all of it (`ops > 0`), and it asks the
job board for **one** person however many pots it has.

**And a machine that is "staffed" runs about 6 or 7 times a sol, not 11.7.** The
theoretical rate is one visit per 64 revolutions; the operator is also a person who
eats, sleeps and walks, and the night has no power. That gap is why the food chain
needs headroom rather than exact ratios, and why `mach_vitromeat` now yields **2** per
run: at 1 it matched `mach_food`'s consumption exactly, so a meal was cooked only when
the two machines happened to line up, and a colony of four with a full granary lost
Food every sol. Measured with `tools/agents.py`, which can read a dome's operator
count while the game runs.

#### Smaller, at milestone 46

`src/econ.asm` went from 1,549 bytes to **1,097** without changing a byte of what it
computes — `tests/test_sim.py` still compares every byte of the economy, the domes,
the structures and the agents against `tools/econ.py`, and found nothing to compare
differently. The same means as the object pass at milestone 43
([§8.4](#smaller-at-milestone-43)):

- **What was written twice is written once.** The machine and the plant each read
  the slot's health — it is read once, in the slot loop. The battery's "charge, up to
  the cap" served the colony and the shed load in two copies — `ef_charge`. The pump
  and the mine were two handlers — `ef_pump`. The three inputs of a recipe were three
  unrolled copies of the same check — `erm_in`, called three times, with the fixed
  `IX` offsets kept — and their removal one loop. The flare's three breaks are a
  three-row table.
- **"Made here" and "into the store" are one routine.** Every producer called
  `ec_mark` and then `ec_add_stock` with the same two arguments; `ec_make` marks and
  falls into the add. Both, with `ec_stock_ptr`, moved to **`src/stock.asm`**, which
  the game, the simulation harness *and* the interface harness include — so
  `fit.asm` lost its private copy of the capped add (`fit_give`, 23 bytes).
- **Arithmetic where the operands already are.** The deficit stays negative, as the
  subtraction left it: battery plus `(production − demand)` with a carry means "the
  battery covers it", and the remainder is compared with the reserve. It used to be
  recomputed positive, parked in a variable and subtracted twice. Production, cap and
  demand accumulate straight into `EC_PPROD`, `EC_PCAP` and `EC_PUSE` instead of
  three private copies published at the end — the cycle runs whole inside one call.
  `sbc a,a` turns a carry into a flag; a stock's address is `EC_STOCK + 2·A` in one
  page, so `D` is a constant (`assert`ed, as are `G_machine_count` and
  `G_plant_class`).
- **The structure loop walks `IX`** with the count on the stack, instead of loading
  `IX` from a pointer variable and storing it back each time.

It is faster, measured on the test colony with a 2 µs clock: a flow cycle that fires
5,900 → **5,036 µs**, a full production sweep (four calls) 25,918 → **23,704 µs**,
its worst call 14,870 → 14,002. The one thing slower is a production call over
sixteen *empty* domes, 1,228 → 1,356 µs — `ec_run_dome` reaches the record through
`jb_dome_ptr` now, 7 µs a dome, and inlining it back would cost 10 bytes for the call
that matters least. The state is checked before `IX` is set up, so an empty slot pays
nothing else.

**Two branches had never been compared.** The shared run passes whichever balance
branch it happens to, and its last cycle shows a surplus; a flare is one roll in
2,048 revolutions and the run is forty. So `tests/test_sim.py` now builds them: eleven
balance cases — surplus, the cap, production equal to demand, a deficit the battery
covers, the battery at *exactly* deficit plus reserve and one unit under, the night on
the battery, blackout, storm, no wind and a gale — each one cycle, the whole economy
compared; and the generator seeded so that the first roll of slot 15 throws a flare
(two machines stop), a fault, a storm and visitors. Negatives: the reserve's shifts
cut, the two boundary cases disagree; the flare's first offset 37 → 38, the run
disagrees.

#### Smaller and faster, at milestone 60

`src/rooms.asm` went from 372 bytes to **280**, and every routine in it got faster or
stayed the same. Over 13,406 calls, measured with interrupts off:

- `rm_build` is 36 % faster;
- `rm_fits` is 35 % faster;
- `rm_step` is 34 % faster;
- `rm_fix` is 31 % faster;
- `rm_room` and `rm_name` are 1.5 % faster.

The check was a script kept out of the repository. It calls each routine directly,
for every room, size, catalogue position and direction. It does this with the real
`room_machines` and `machine_rules`, and with 200 random tables, so that the main
machine lands at every place in the list, does not fit, or is not accepted at all.

It compares four kinds of result:

- the list and the byte in front of it;
- the count, `CY` and `Z`;
- `bd_rsel` after a step or a fix;
- `BC`, `DE` and `HL` across `rm_build`, which `fit_enter` relies on.

All 13,406 calls were identical with the old file and the new one.

- **The main machine is moved to the front instead of looked for first.** The old
  code shifted the 12-bit mask `pref` times to see whether the room accepts its main
  machine, tested its size, wrote it first, and then had the loop skip it. Now the
  loop simply collects every machine that is accepted and fits, in numeric order.
  Then `cpir` finds the main machine, and if it is there, `lddr` moves the ones before
  it back by one. The result is the same list.
- **Two tables are read with a constant page.** `room_machines` and
  `machine_rules` come out of `tools/pack.py` and do not cross a page, which is
  `assert`ed. The fit test is three instructions inside the loop, not a call that
  saved and restored two register pairs.
- **The loop shifts first and tests the carry.** It counts with `djnz`, and takes the
  count from where the pointer stopped, not from a counter of its own. `rm_rm` and
  `rm_pf` are gone.
- **Smaller pieces:**
  - `1 << size` is `size + 1 + size/2` for 0–2, not a three-byte table.
  - The greenhouse is one `ldir` of `rm_plants`.
  - `rm_fits` answers with `sbc a,a`.
  - `rm_room` and `rm_fits` share one lookup in `rm_list`.
  - `rm_step` wraps at both ends with one `cp`.

Calling `ob_addu` made `rm_room` and `rm_name` 5 µs slower than before. They read
their tables inline again, for 4 bytes.

**What the planted faults found.** Twenty-four faults were run against the script and
against `test_build.py`, `test_fit.py`, `test_game.py` and `test_reveal.py`. The script
caught all twenty-four. Eight passed every test:

- a room with no machines reported as not fitting (the catalogue then skips
  Quarters, Storage and Lounge);
- the last machine, 11, never listed;
- the last machine moved to the front instead of the main one;
- the catalogue wrapping to 8 instead of 9, or to 1 instead of 0;
- the catalogue trying only the next room;
- `rm_fix` moving a structure's room;
- `rm_build` handing back `BC` and `DE` swapped.

The tests only asked about the Lab, the Factory, the greenhouse and oxygen at two
sizes, and nothing walked the catalogue round its ends. `test_build.py` now checks
every room and size against a model written from the section above, with the real
tables and with 24 random ones. It also checks that `rm_build` keeps `BC`, `DE` and
`HL`, every step of the catalogue from every position, and `rm_fix` for a dome and for
a structure. The negative runs `rm_build` for 11 rounds instead of 12. It catches all
eight. With the old `rooms.asm`, every new check passes except the negative, which
looks for the new loop's `ld bc`.

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

**For twenty-seven milestones they dropped the job and the board handed it straight
back.** "Drops the job" was written as `NO_TASK` — which is also how the agent tables
spell *idle*, and the assignment pass gives work to the idle. So the needs pass set
the destination to the canteen, the assignment pass set it back to the machine, the
colonist turned round at the next node, and the two passes took turns until it **died
of hunger while working, with 39 Food in the warehouse**. Neither pass was wrong on
its own; every field held a legal value at every moment, which is why nothing in
[§13](#13-build-and-test)'s suite had anything to catch. It took reading one
colonist's fields every 25 frames (`tools/agents.py`) to see the oscillation:

```
7100 travelling node=1 dest=2 task=-    water=3 food=3 health=216
7125 standing   node=3 dest=3 task=#1   water=2 food=2 health=213
7150 travelling node=3 dest=2 task=-    water=0 food=0 health=207
7175 starting   node=1 dest=2 task=-    water=0 food=0 health=201
...   (and so on, every 25 frames, until health reached zero)
```

**Going to eat is a task, and [§6.7](#67-jobs)'s own table said so** — its last row is
*Rest / Eat / Drink · the colonist's own needs · anyone, highest priority*. It needs no
entry on the board: the needs pass writes **`T_NEED` (254)** into the task field. It is
not a job index — there are 32 — so the reap step reads "changed their mind" and frees
the work for someone else, and the assignment step reads "busy" and walks past. The
first needs visit that finds nothing missing writes `NO_TASK` back and the colonist is
available again. One value, no new column, no new pass.

Measured after, on the same colony (`tests/test_needs.py`, which builds it and watches
the bars rather than the corpses): work until the bars reach 63, a trip to the canteen
of about 125 frames, both bars back to 255, then back to work — **one canteen trip per
sol**, which is exactly the rate [§6.5](#65-economy)'s table always claimed. Nothing
now goes below 58. The negative control is the same test on the previous binary: bars
pinned at zero for 1,100 frames and the first colonist dead.

**A famine does not freeze the colony**, which was the thing to check before giving
needs a veto over work: with the store emptied by hand and every bar walked down to
zero, the colonists still spend **half their time working** — the colonist standing in
an empty canteen is the one already there, not everyone. So a colony that runs out of
food can still build and run the thing that fixes it.

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

**Three more came out of running the real binary for eight sols** (`tools/balance.py`,
milestone 25) — the first working colony was a *test* colony, ninety-six people on a
hand-built map; this was the colony the player is actually given:

| | Was | Now | Why |
|---|---|---|---|
| Eating and drinking | `+64` to the bar | fills it to **255** | A trip to the canteen that buys a quarter of a bar means twelve trips and twelve Meals a sol. The canteen is a journey, not a sip. One visit a sol, one Meal, one Water — which is what [§6.5](#65-economy)'s table said all along. |
| Visitor ships | 1 roll in 64 revolutions | 1 in 2,048 | Guests ate 70 Food a sol out of a start state holding 40 ([§6.11](#611-ships-and-arrivals)) |
| The economy's clock | there wasn't one | `ECON_DIV`, `FLOW_DIV` | Every per-sol rate in [§6.5](#65-economy) ran 750 times a sol |

With the first set, **no colonist ever reached a workplace** — the entire population
spent its life commuting. That is not something a budget or a unit test would have
caught; it only appears when the loop actually closes.

**Variety is deliberately not implemented.** This section wanted three hidden counters
per colonist so that eating one crop caps health. The trap it exists to create is
already enforced one level earlier: `mach_food` needs **Starch and Vegetables and
Vitromeat** together, so a one-crop greenhouse cannot produce a meal at all. A second
mechanism for the same lesson would cost 384 bytes and teach nothing new.

#### Smaller, at milestone 53

`src/needs.asm` went from 963 bytes to **776**, and slot 14 — the room index, which was
the worst frame of the wheel — from 6,889 µs to **4,692** (34 % of a frame to 23 %).
The needs slots came down a little, 2,796 → 2,696 µs; the whole revolution 43,930 →
40,934. Nothing they decide changed: `tests/test_sim.py` compares every agent field,
the domes and the economy against `tools/entity.py` and `tools/econ.py`.

- **What was a variable is a register.** The damage is gathered in `E` by rotating
  in the carry of each comparison — oxygen, water, food — which gives weights 4, 2, 1
  for nothing, and the sleep need is loaded into `E` only after the damage is spent.
  The morale minimum stays in `A` across the compare that used to need it stored. The
  node, the best distance and the candidate of the room search live in `D`, `C` and
  the list pointer.
- **Slot 14 reads its records through `IX`** — `(ix+D_STATE)`, `(ix+D_ROOM)`,
  `(ix+ST_KIND)` — where it pushed, added an offset and popped around every field.
  That is the 2.2 ms.
- **The room index is one page** (`G_room_n`, then `G_room_list`, 108 bytes), so a
  pointer into it is an add and an `ld l`; so are `G_machine_count` and
  `G_plant_class`, asserted. Saturating increments are `inc (hl)` / `jr nz` /
  `dec (hl)`.

**The slip, and the trap behind it.** The first version sent colonists to the wrong
domes, and `test_sim` said so at once — 325 bytes of agents apart. Halving the change
found the room search, and halving that found one line: `ld d,G_room_list / 256`.
**RASM evaluates expressions in floating point and rounds**: `&9E84 / 256` is
158.52, which assembles as `&9F` — the next page. `G_room_n`, at `&9E78`, rounds down
and was fine, which is why the count was right and the list was not. It is `>> 8` now.
Every other `/ 256` in the source was checked: all of them name a page-aligned table
or one whose low byte is under `&80`, so none was wrong — yet.

**And a check the economy did not have.** With the oxygen's weight in the damage
planted at 2 instead of 4, `test_sim` stayed green: in its colony nobody's needs ever
fall below the critical 16. So it now also sets every colonist to one of fifteen edge
cases — each critical need alone and together, damage to death, recovery and its
ceiling, morale at the floor, and each room a colonist can be sent to — and runs four
revolutions against the reference. The planted weight fails it.

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
ties by `DIST[agent.node][job.node]`.

**`Operate` has a priority per room, and it had to.** One shared number for every
machine meant every `Operate` job tied, and a tie is broken by distance — which never
changes. The nearest dome that wanted anyone took everyone, for ever: measured on the
food colony, the player's canteen sat **unassigned in 147 consecutive samples** while
the greenhouse next to it piled up 250 Starch that nobody was cooking. The table is
twelve bytes, one per room, and reads as what the colony dies without first: canteen
and life support **5**, greenhouse, lab and medbay **4**, everything else **3**. After
it, over the same window: canteen staffed 23% of the time → **93%**, and the colony's
Food stopped falling. Bounded at **4 assignments per visit**, examining
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

#### Smaller, at milestone 47

`src/jobs.asm` went from 1,089 bytes to **817**, and is faster, which matters here
more than anywhere: slot 13 is the one wheel slot over its budget
([§7.2](#72-the-wheel)). Nothing it decides changed — `tests/test_sim.py` compares
the board, the domes and every agent field against `tools/econ.py`, and it was that
comparison which caught the one slip on the way (below).

- **"Is this dome built, and how many slots has it?"** was written out in
  `jb_broken` and again in `jb_need`; it is `jb_slots`, and the slots are walked with
  `IX`, so a slot's health is always `(ix+8)` instead of a push, an add and a pop. A
  repair finds the broken slot with `jb_broken` and writes the health through the `IX`
  it left behind — the slot used to go through a variable and the address was built
  again from the dome number.
- **The three ways a job ends** — operator, repair, construction — share one
  `ja_done`; each had its own copy. Construction reaches its record through the
  meteor's `mt_rec` (a node is a dome below 64 and a structure above), which already
  did exactly that.
- **The assignment loop computes the agent's row of `DIST` once**, not once for each
  of the 32 jobs it compares, and takes a job's index from the loop counter instead of
  keeping a variable in step with it. Posting keeps the first free entry in a register
  rather than a variable it pushed and popped at every entry.
- `1 << role` is `#80` rotated `role + 1` times; "alive and not working" is one mask
  and one compare.

Measured on the test colony with a 2 µs clock, `jobs_tick` at five points of the run:
3,122–4,896 µs before, **3,094–4,398** after, and the worst call — the burst of
assignments at the start — 52,390 → **41,584 µs**. The pinned slot in
`tests/test_sim.py` reads 4,692 → 4,393.

**The slip:** `jb_slots` returns "built" in the zero flag, and the first version set
it with `cp DS_ACTIVE` and then looked up the slot count with `add a,n`, which
overwrites it. Every dome read as unbuilt: no `Operate` job was ever posted, no
machine ever repaired. The colony test showed 59 agent bytes wrong in the first
comparison — nobody had become a worker.

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
`room_machines` is packed with the other asset tables and the placement rule it
describes belongs to build mode ([§9.3](#93-build-flow)), which is not written.

### 6.9 Construction

1. Player places a ghost. Validation: every footprint tile must be `ground`, `dust` or
   `foundation`, occupancy free, and (for domes) at least one corridor route must be
   possible. Invalid tiles are tinted; the ghost cannot be committed while any is.
2. On commit: footprint tiles become `foundation`, occupancy `reserved`; a construction
   site node is created; a Build job is posted; the cost in Metal / Bioplastic is
   *reserved*, not yet spent.

**As built, three of those differ, and each for a reason:**

- **The machines go in at commit and appear at completion.** The record is filled
  the moment the site is paid for — nothing reads a dome that is not `DS_ACTIVE`
  ([§6.5](#65-economy), [§6.6](#66-needs)), so there is no second pass to write
  when the building finishes. What did have to change is the *drawing*: the object
  pass now gives a site the empty-room icon and skips its machines, or a
  half-built dome would show a finished interior from the first frame.
- **The cost is spent at commit, not reserved.** There is no reservation pool in
  the economy record and inventing one would have meant a second number beside
  every stock, kept in step by hand. A fake reservation is worse than an honest
  simplification. What the step *does* keep is the construction: the dome goes in
  as `DS_BUILDING` with integrity 0 and a Build job is posted against it — which
  is the first thing in the game to post a job a bot will take, so the Automation
  milestone of [§10.2](#102-milestones) stops being unreachable by definition.
- **A corridor is stamped `occupied` but not `foundation`.** It is a half-tile
  lane lying on the ground; pouring concrete under a whole diagonal would paint
  four times what it covers. Occupancy still goes down, or a dome gets built on
  top of a corridor.
- **A corridor commits as `DS_ACTIVE` and posts no job.** The job board addresses
  a *node* and a corridor is an *edge* — there is no node to post against.
  Fixing it means either giving corridors node ids or adding an edge-shaped job
  kind, and both are changes to [§6.7](#67-jobs) rather than to the build mode.
  Until then a corridor appears finished the moment it is paid for.
- **The site is linked to the nearest *other* dome.** A construction site is already
  "live" the moment it is written, and it sits exactly under the cursor, so the
  nearest live dome to it was **itself** — distance zero — and the self-check below
  that returned without building any edge at all. Every dome the player placed was
  therefore unreachable, its Build job permanently open, and nothing ever finished. Structures
  never showed it, because a structure takes a node id of 64 or more and can never
  equal a dome index; and no test had ever waited for a dome to be built. Found in
  milestone 26, by building one and watching.
- **"at least one corridor route must be possible" is not checked** when a dome is
  placed. It would need the router run against every existing dome on every cursor
  step; the router is cheap but the answer is also wrong, because the dome the
  player is about to connect to may not be built yet.
3. Engineers and constructor bots walk there and work. Progress is a byte.
   **Built, and the byte is the integrity byte** — `bd_commit` writes integrity 0
   and each visit adds 32, so eight visits (≈2.6 s) finish it. A half-built
   building and a half-wrecked one are then the same state, which is right and
   saves a byte per node. **A construction site also gets an edge**: without one
   the routing finds it unreachable, nobody ever sets out, and it stays
   `DS_BUILDING` for ever. It is linked to the nearest live dome — an *outdoor
   edge* in [§6.2](#62-the-node-graph)'s sense, one with no corridor to draw it.
4. On completion the object is drawn — and this is the expensive moment: **5.7 frames
   for a large dome** ([§2.2](#22-the-frame-budget)). It is split into 8 chunks, one
   quadrant per frame, in the order of `assets/SPRITES.md` §8: rings, domes, connectors,
   room icon, machines, slots. The dome appears over about a sixth of a second, which
   reads as materialising rather than as a stall.

   **As built, completion is not the expensive moment — placement is, and completion
   is one dirty-list item.** The site is drawn when it is placed (rings, dome,
   connectors, the empty-room icon — step 2's first bullet), so when it finishes only
   two things on screen are wrong: the room icon and the machines. The Build job
   pushes `DK_BUILT` with the node id through the simulation's own hook
   ([§8.5](#85-the-dirty-list)), and the handler draws exactly those — the icon, then
   every machine slot, all opaque, in the full pass's order. A structure pushes the
   same record and the handler draws **nothing**, because `ob_struct` draws a site and
   a finished structure alike; it only plays the sound.

   Until milestone 34 this was a full redraw, and it was not "0.8 s" but **360–920 ms,
   depending on what was on screen** — measured with a clock that keeps running across
   the seams between measurement calls, because the first measurement lost exactly the
   long frame at one. After: the frame in which a large Factory completes is
   **120 ms**, 60 of them the ghost being lifted and dropped because the player left
   it on the site ([§9.3](#93-build-flow)) — 100 at milestone 34, when that ghost was
   cut short by a full undo log; a solar panel's completion frame is the 40 ms of an
   ordinary HUD tick. `tests/test_reveal.py` holds it three ways: a canary
   byte far from the building survives (a full redraw would repaint it), the icon and
   machines match a full redraw byte for byte, and the worst frame is under 200 ms.

   **Placement was the same full redraw — and the eight-chunk reveal is written
   there, at milestone 35, because that is where the expensive moment went.** A dome
   is pushed into the dirty list as one `DK_SITE` record per **tile row** of its
   footprint, and the list lets one out per frame: the site materialises top to
   bottom over four, six or eight rows while the simulation, the sound and the
   cursor keep running. A row is drawn as the terrain under it and then **that dome
   only** — shell and fittings clipped to the row — not `ob_draw_all`: the footprint
   is the dome's by occupancy, so nothing else can be in it, and the general pass
   spent 18 ms per row asking 64 domes, 96 corridors and every structure to find the
   one. A structure is at most one 4×4 sprite and is drawn at once, the same way:
   terrain, then that structure. A corridor redraws the bounding box of the tiles it
   stands on, **without** a margin, and its two doors come from the dirty list as
   `DK_CONN` — a door never overlaps a ring slot, a machine or an icon at any size
   (checked from `conn_points`, `corr_slots` and `machine_slots`), so drawn alone
   over the shell it is what the full pass draws.

   | Placement, worst frame | before milestone 34 | 34 | **35** |
   |---|---|---|---|
   | Large Factory | 998 ms | 859 | **140** (80 for the press, 60–80 per row, 140 when the ghost comes back) |
   | Solar panel | 439 | 220 | **120** |
   | Straight corridor | — | 260 | **120** |
   | Diagonal or bent corridor | — | — | 160–220 at 36 → **80–100** at 37 |

   The diagonal row is new because until milestone 36 no such corridor could be
   built ([§9.4](#94-corridor-routing)), and at first it cost more for a plain
   reason: the bounding box of a diagonal of `n` steps is an `n × n` square, and a
   seven-step one redrew 64 tiles in one frame — 130 ms of `cr_redraw`, 45 of them
   terrain and 85 the object pass — to change a line across it. **Since milestone
   37 the diagonal appears a row per frame, like a dome.** Each tile row it crosses
   is one `DK_CROW` record: the three tiles the two diagonal pieces sharing that row
   touch ([§8.5](#85-the-dirty-list)). Only rows inside the view are pushed — a long
   diagonal would otherwise fill the 32-entry ring — and whatever scrolls in later
   is drawn whole by the scroll strip. The axial run of a bend is already a thin
   rectangle and is drawn at once. The ghost waits for the last row (`ui_owed`),
   as after a dome. The press now costs 60 ms (100 with a bend's axial run), each
   row 60–80, the worst frame 80–100.

   **Corridor rows draw no terrain.** Each object is written as
   `(screen AND mask) OR sprite`, so redrawing every object in order over a correct
   picture of a subset of them, with the same tiles underneath, gives the correct
   picture of all of them: whatever the terrain or an old object put there and no
   new object covers, the old object writes again. A corridor only adds — it lays
   no foundation — so its rectangles skip the tiles (`view_add`). With the tiles
   first, what was already on screen in the strip vanished until the object pass
   reached it, 30–85 ms, two to four frames: the bend drawn at the press, the
   corner of the dome. `tests/test_link.py` samples every frame of the reveal and
   counts bytes that had their final value and lose it: **13** in the worst frame
   (a door re-covered for a moment by the corridor under it), **96** with the
   terrain put back. A dome *does* change the tiles — its foundation — and keeps
   `view_rect`.

   Two more things had to change for the large dome. The ghost that `uip_after`
   put back over the new site — red, 64 invalid-tile marks — cost 263 ms, and with
   the site appearing row by row every row would have had to lift it and drop it
   again. Now it waits (`ui_owed`) and comes back one frame after the last row, at
   57 ms, drawn from a log of rectangles ([§9.3](#93-build-flow)). And the mirrored
   half of every dome shell no longer goes through a buffer: `blt_mask_flip` mirrors
   and masks in one pass, 34 µs a byte instead of 40 + 18, which took the whole large
   site from 450 ms to 351 and a full redraw of the view from 839 ms to 679.
   Placement now calls `hud_draw`, not `ui_hudall`: the latter forced the panel's rows
   3–4 to be rewritten, ~20 ms, for nothing the panel's own signature would not
   catch.

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
| Meteor shower | eight impacts round one building: **structures knocked back to sites**, one machine stopped per dome hit, **crater tiles written to the world plane** | spread-out building, spares, builders | ✅ |
| Intruders | arrive at the map edge, walk in, attack | guards, guns, airlock placement | ✗ |

Intruders are **not built**: they need agents that spawn at the map edge and a notion
of combat. Meteors waited for the same reason — they write terrain, so they needed the
world plane and the dirty list that redraws it — and came at milestone 38, below.

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

**And the victim has to come out of the bits the test did not use.** Picking the
machine with `r2` while testing `r3` looks like that same rule — it is the exact
opposite of it. `r2` is the *previous* draw, and the polynomial `#B400` has a zero low
byte, so it never touches the bottom eight bits: "the low seven bits of `r3` are zero"
forces `r2 % 64` to **zero**, every time — seven breaks a sol, every one of them on
dome 0, which in [§10.1](#101-start-state)'s colony is the only oxygen generator. That
was a tuning pass finding a trap in its own change, in a line that reads as though it
were following the rule above. The victim comes from `r3 >> 7`: the bits the test left
alone.

#### How often, measured

| | Was | Now | What that is |
|---|---|---|---|
| Sandstorm | 1 roll in 128 revolutions, 32 revolutions long | 1 in 512 | a quarter of every sol with the panels covered → **5%** |
| Malfunction | 1 roll in 32 | 1 in 128 | on the start colony, **1.1 breaks a sol** → 0.25 |
| Solar flare | 1 roll in 256, three machines each | 1 in 1,024 | three flares a sol → 0.7 |

The malfunction rate was the one that decided games. [§10.1](#101-start-state)'s colony
has two machines and four Spares; nothing in it makes Spares; one of the two machines
is the only thing producing oxygen, and two thirds of the breaks landed on it. The four
Spares were gone before sol 3 and the next break was fatal — the colony asphyxiated
with a full battery and 300 Water in the tanks. Something breaks every four sols now,
which is what a Spare is for, and the rate still scales with the base: `break_one`
picks a dome out of 64 and gives up if nothing is there, so a colony with forty domes
sees the same roll land fifteen times as often.

#### Meteor showers (milestone 38)

**The roll is the twelve high bits of `r1` all ones** — 1 in 4,096 revolutions, one
shower every ~5 sols (measured: 41 in 200 sols). Every other test reads *zeros*, so
the meteor is the only one that can use ones, and that alone keeps it apart from the
rest. "Apart" is checked rather than argued: only 16 values of `r1` start a shower
(`&FFF0–&FFFF`), the `r2` and `r3` that follow each are fixed by the polynomial, and
`tests/test_meteor.py` walks all 16 — **none** brings a storm, a malfunction, a flare
or a visitor in the same revolution.

A shower is **eight impacts, one a revolution** (2.6 s), within ±8 tiles of a centre.
The centre is a building — the first live node from a random start among the 96 — so
the shower falls on the colony and not on empty desert 60 tiles away. Positions come
from **the shower's own generator** (`EC_MRND`, seeded from `r1` and the clock, eight
Galois steps per byte): drawing them from the event generator would shift every
storm and malfunction after the shower, and the sequence would depend on whether
anything was built.

| An impact lands on | What happens |
|---|---|
| an active dome | one machine stops (`ec_break_d`, the slot from the draw) — an engineer and a Spare, as for a malfunction |
| an active structure | **back to a building site**: integrity 0, state `DS_BUILDING`, a Build job posted, the balance re-measured at once |
| a site of either kind | integrity 0 — the progress is lost |
| open ground — ground, dust, rock, foundation, unoccupied | **a crater** (`W_CRATER`, the decor bits kept), pushed onto the dirty list as `DK_TILE` |
| corridor, water, mountain, an existing crater | nothing |

**This diverges from the table's first version, which said "destroyed".** The game
has no demolition — no code that frees a dome record, unlinks its node, rewrites its
foundation and re-routes the graph — and a building's progress *is* its integrity
(`src/jobs.asm`), so "destroyed" would have meant writing all of that for one event.
Knocked back to a site costs the player the same thing that matters — the building
stops producing until builders spend another round on it — and reuses the build path
the player already knows: the struck structure gets the same Build job a new one gets
(`jb_post_build`, now shared by `build.asm` and the meteor).

A structure under construction is drawn exactly like a finished one (the renderer only
distinguishes a dome's site, which it draws empty), so a struck landing pad *looks*
untouched until it is rebuilt. The HUD says `METEOR SHOWER` for the length of the
shower — below power and oxygen, above food and water — and each impact plays a falling
noise (`SFX_METEOR`) from the main loop, not the wheel, because the wheel also runs in
the simulation harness, which has no sound.

The crater goes through the dirty list and never through a full redraw: measured in
the game binary, the worst frame during a shower is **60 ms** and the canary survives.
The reference (`tools/econ.py`) knows which buildings are hit and agrees with the Z80
byte for byte; the world plane it does not have, so `tests/test_meteor.py` predicts the
craters from the plane the game holds and checks that **exactly** those tiles change.

**Which building an impact hit was the expensive part.** The first version asked
every live node for its footprint — ~165 µs a node, **9.5 ms an impact** on a colony
of 54 buildings, in the wheel slot budgeted at 500 µs. No footprint reaches more than
four tiles from its record's centre (an L dome is 8×8; structures are at most 4×4),
so `mt_scan` walks the two tables with a pointer, rejects a centre more than
`MT_REACH` = 4 tiles away in x in six instructions, and pays for the footprint only
near the impact: **3.0 ms** on the same colony, 5.4 ms with all 54 piled on one spot.
That still exceeds slot 15's 500 µs, eight revolutions in a shower, but stays under
slot 14's 4.7 ms that runs *every* revolution, so a shower never sets the worst frame
of the wheel. The bound is tested from the side that can fail: a 120-impact shower
round an L dome lands eleven impacts in its left column, exactly four tiles from the
centre, and with `MT_REACH` patched to 3 the Z80 stops agreeing with the reference.

That same pinned-slot run turned up an old bug in `ship_crew`: a full crew of four,
or a population cap filled exactly, left by `ret` and skipped the line that adds the
newcomers to `EC_ALIVE`. Slot 12 recounts the living every revolution, so in the game
the count was short for at most 16 frames and no test that runs the whole wheel could
see it; with only slot 15 running, the reference said 4 and the Z80 said 0. Every exit
goes through `sk_full` now.

### 6.11 Ships and arrivals

A Control room lets you call ships to the landing pad. **One ship at a time**, and
none at all without a pad — the pad is a structure, and its node id is found by the
same pass that indexes rooms ([§6.6](#66-needs)).

| Ship | What it does | Built? |
|---|---|---|
| **Colonist** | four new colonists appear at the pad, full bars, roles spread | ✅ |
| **Visitor** | arrives unbidden, eats, raises everyone's morale, leaves | ✅ |
| **Merchant** | `trade()` swaps stock for stock while it is landed | ✅ mechanism |

A ship is `INCOMING` for 24 revolutions, `LANDED` for 8, then gone. Colonists take
the first free agent ids — which are usually the ids of people who have died, so
counting "was dead, now alive" is not how you detect an arrival.

**The colonist cap comes from Control rooms**, 48 each plus a base of 4. That number
is a first guess like every other in [§6.5](#65-economy): at 8 per Control a colony of
ninety could not legally contain itself, and no colonist ship meant anything.

**`C` calls a colonist ship, and that button was the last piece missing.** The
mechanism had been here since step 9 with nothing reaching it. `ui_ship` asks the
three questions `ship_call` cares about and says which one failed —
`NEED A CONTROL ROOM`, `NEED A LANDING PAD`, `A SHIP IS ALREADY DUE` — or
`COLONIST SHIP CALLED`. Measured end to end in `tests/test_game.py`: a colony with
no Control room refuses and says so on the message line; a small Control dome takes
the cap from 4 to 52; one press puts four colonists on the pad, **4 → 8 alive**.

**The refusal came out blank rather than wrong, and only the screen showed it.**
`ui_hide` jumps to `gh_undo`, which destroys `HL`. The message pointer was loaded
*before* that call, so `ui_msg` printed from whatever `HL` had become — which pointed
at a zero byte, so the row was cleared and nothing was said. Every state check passed;
the test that reads row 3 back as glyphs is what failed.

**Trade is a player action, not a wheel pass.** The mechanism lives here; the button
that calls it belongs in [§9](#9-interface). Trading sets a flag that breaks the
no-trade streak, which is the whole reason Independence in
[§10.2](#102-milestones) is hard to keep rather than hard to reach.

Merchants and colonist ships must be **called**; visitors arrive on their own roll —
**1 in 2,048 revolutions, one every 2.7 sols.** The roll was 1 in 64, which is a
visitor every twenty seconds of play, and a visitor eats 6 Food: seventy Food a sol
against a start state that holds forty. `tools/balance.py` showed the colony's food
running out inside one sol and the *visitors* eating it, not the colonists.

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

Rule 4 has exactly one exception, and the player asks for it: at double and quadruple
speed the loop runs two or four wheel slots per frame, the frame overruns, and the
screen drops frames ([§9.1](#91-controls)). Trading frame rate for simulation rate is
fine when it is a key press and not a surprise. Rule 1 still holds underneath — each
slot is still bounded; there are simply more of them.

### 7.2 The wheel

**Sixteen slots, one advanced per frame. A full revolution is 16 frames = 320 ms ≈ 3.1 Hz.**

| Slot | Pass | Slice | Budgeted | **Measured** |
|---|---|---|---|---|
| 0–7 | Agent movement | 12 agents each | 1,800 µs | **1,298 µs** ✅ |
| 8–10 | Needs, health, death, deciding | 8 colonists each ([§6.6](#66-needs)) | 433 µs | **2,696 µs** ❌ 6.2× (2,796 before milestone 53) |
| 11 | Production, machines and plants | 16 domes, **one revolution in 16** ([§6.5](#65-economy)) | 4,000 µs | **5,691 µs when it fires, 599 µs a visit** |
| 12 | Flow balance | the living every revolution, 64 structures **one in 64** | 2,000 µs | **5,990 µs on the cycle, 1,797 µs a visit** |
| 13 | Job board — reap, arrive, post, assign | 4 domes, 32 agents | 3,000 µs | **4,692 µs** ❌ 1.6× |
| 14 | Room index, amenity, pad, population cap | 64 domes | *(was empty)* | **4,692 µs** (6,889 before milestone 53) |
| 15 | Events, ships, meteors, and the milestone check once a sol | three rolls | 500 µs | **564 µs** ❌ 1.1× — **3.0 ms** on a meteor impact ([§6.10](#610-events-and-hazards)) |
| — | wheel dispatch itself | every frame | — | **94 µs** |

Slot 15's old **499 µs ✅** was the step of the measurement, not the slot: 200 calls
measured in whole frames resolve to 100 µs. Over 4,000 calls it is **524 µs** without the
meteor roll and **564 µs** with it (milestone 38) — over budget before the meteors came,
and by 40 µs more now.

**A whole revolution costs 61,400 µs spread over 16 frames — under a fifth of the
machine — and the worst single frame is 4,692 µs, 23 % of one** (6,889 and 34 % until
milestone 53, [§6.6](#smaller-at-milestone-53)). That is the number the design lives or
dies by, and it has room.

Four of the seven budgets were low, by 1.2× to 6.5×. The one pass that came in under
budget is the one whose cost was derived from a measured blit rather than guessed.
**Budget the remaining passes pessimistically.**

**Two of those slots now cost what they cost divided by their clock.** Production and
the flow balance run on the economy's cycle ([§6.5](#65-economy)) rather than every
revolution, which was done for the balance and not for the microseconds — but the
microseconds came too: the revolution dropped from 73,400 µs to 61,400. The *worst
frame* is unchanged in size and 64 times rarer, and the pinned-wheel measurement
reports the average across 200 calls, which is why both figures are given above.

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
list ([§8.5](#85-the-dirty-list)) up to a 20,000 µs cap, tick animation, service audio
(**measured: 100 µs silent, 195 µs while an effect plays**, [§9.5](#95-sound)).

The worst *frame* is a room-index slot during a routing rebuild: 4,692 + 2,700 + 94
≈ **7,500 µs, three-eighths of the frame** (9,700 until milestone 53) (it used to be the flow balance, at 10,700). That leaves 9,300 µs for rendering — and a
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

### 7.4 One convention per half, and they disagreed

Every simulation pass reads domes, structures and agents straight from `&4000`
without paging: `tests/simtest.asm` put bank 6 in the window once before the run
and never touched it again. The renderer does the opposite — it changes bank
dozens of times a frame and always leaves bank 1.

Put together, the economy counted the agents *inside the distance matrix* and the
population dropped to zero in ten seconds. **The wheel now owns the convention**:
one `out` on the way in, one on the way out, 30 T-states a frame. Passes that need
another bank put bank 6 back themselves — `rt_slice` was the exception and is now
wrapped, because it was written to be called from the renderer's world.

This is the class of bug that only exists between two subsystems, and the only
thing that finds it is linking them.

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

  **Measured: 2.55 frames** (`tests/test_hud.py`), against the 0.4 estimated
  here. Six times. 200 cells × 16 bytes is 3,200 bytes, and the addressing
  around each one costs more than the bytes do. Two cuts took it down from 3.5:
  the screen pointer is computed **once per row** instead of once per glyph, and
  the eighty blank cells of rows 3–4 are **filled with zeros rather than drawn**
  — glyph 32 of the font *is* sixteen zeros, so the result is byte-identical and
  ten times cheaper.

  **Now 1.75 after a camera step and 0.65 otherwise** (2.30 and 1.15 until milestone 52's smaller HUD; 2.20 cold until milestone 33 moved the font into bank 7), since the cell cache of
  [§9.2](#92-hud). The camera step is the expensive case by construction: the ring
  has moved every cell, so nothing in the cache is where it was.

  **The escape hatch, not yet taken:** a camera step moves the whole HUD block by
  a fixed distance inside the ring (4 bytes east, 160 bytes south), so the block
  could be **moved** with 3,200 bytes of `lddr` — about 0.85 frames — instead of
  re-rendered. It is held in reserve for the same reason as the tile-pair idea in
  [§8.3](#83-the-tile-pass): the current cost does not yet justify the
  complication.
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

#### The 2 KB ring is not bookkeeping

Earlier text here said the wrap was "bookkeeping rather than a new mechanism".
It is a mechanism, and it had to be built.

The 6845 hands the Gate Array a 14-bit address and **the Gate Array drops bits 10
and 11**: `MA9..MA0` go to `A10..A1`. So the scan wraps every **1,024 words =
2,048 bytes**, and the screen uses 2,000 of them. The moment the camera offset
passes 24 words, the wrap point lands *inside the visible image*. Every screen
address is therefore

```
p    = ((y>>3)*80 + x + 2*cam_off) mod 2048
addr = &C000 + (y&7)*&800 + p
```

and a sprite line that crosses `p = 2047` **must be written in two runs**. An
implementation that ignores it writes 2 KB earlier — somewhere else on the same
screen, silently, and only for some camera positions. The check is three
instructions per line (`(d&7)==7` is a necessary condition, true for one line in
eight at worst), not per byte; per byte it would cost 70%.

Tiles never straddle, and that is not luck: the camera moves in whole tiles, so
`cam_off` is always even, `p` is always a multiple of 4 for a tile, and a 4-byte
tile inside a 2,048-byte ring cannot cross. Sprites are not so lucky and go
through the split.

`tests/test_object.py` includes a camera whose wrap point falls inside a dome;
deleting the split makes three of its five cameras fail.

#### What a scroll step actually costs

| | frames per tile step |
|---|---|
| Terrain strip alone (one column) | 0.45 (0.48 before milestone 56) |
| Terrain strip alone (one row) | 0.89 (0.96) |
| **Whole step, open ground** | **0.6 – 1.0** (3.0 – 3.4 before milestone 39's object index) |
| **Whole step, through the middle of the base** | **1.6 – 5.0** (5.4 before milestone 43's smaller object pass; 4.0 – 7.8 before the index; 4.2 – 8.8 before milestone 35's one-pass mirror) |
| HUD re-render, on top of any of the above | **1.75** (2.30 before milestone 52) |

The 0.9 figure this section used to quote counted **only the terrain**. The rest
is the objects that overlap the strip, and they have to be redrawn because the
memory they occupied has just rotated in from the far edge of the ring.

The mechanism that makes this affordable is the **clip rectangle**, and it is the
same one that makes a partly off-screen dome legal: every blit is cut to a
rectangle, so redrawing a large dome for a 4-byte column costs an eighth of a
dome, not a dome. Three separate cuts were needed before the number was sane:

- **one rectangle test per dome**, before its eight doors, eight machine slots and
  eight colonist slots are each culled individually;
- **read the state byte before copying the record** — 52 of the 64 dome slots are
  empty and each was costing a 24-byte `ldir`;
- **mirror only the bytes that survive the clip** — a flipped quadrant was
  reversing 16 pairs to write 4;
- **and, at milestone 39, stop asking every record at all.** After the three cuts
  above, the object pass still spent **49 ms** deciding that nothing in a
  12-dome test colony touched a strip of open ground — two and a half frames of
  every step, before a single byte was drawn. The object index
  ([§8.4](#84-object-pass-and-draw-order)) makes that 2 ms.

`tests/test_scroll.py` proves the result by **equivalence**: start five tiles
back, draw fully, scroll five times, and the screen memory must be identical to a
full draw at the destination — in all four directions. Since milestone 39 the strip
and the full draw both go through the index, so an object missing from it would be
missing from both and the equivalence would still hold; `tests/test_index.py` closes
that gap by drawing every tile of the view on its own.

The 16 KB page wraps — the ring is 1,024 words — so the newly exposed strip's
addresses wrap too, and the blits handle it as described above.

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

| | µs per tile | before milestone 56 |
|---|---|---|
| `blit_tile` plus the column loop, with the camera's offset and ring ([§8.2](#82-camera)) | 570 | 599 |
| class, variant, autotile, ore overlay | 319 | 362 |
| **total** | **889** | **961** |

The first column is measured by taking `tile_src` out of `tile_one` in memory. The
split is new; the table used to read 579 + 350 + 29 for the camera = 958, before
milestone 42's `CALL` made it 968.

A scroll step costs one column of *terrain* — 0.45 frames — and that part is
comfortable. It is not the whole step ([§8.2](#82-camera)). A full redraw is 8.9
frames and is already sliced ([§7.4](#74-batched-work-outside-the-wheel)).

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

#### Smaller and faster, at milestone 56

`src/tiles.asm` went from 633 bytes to **521**, and a terrain tile from 961 µs to
**889** (−8%), with every byte on screen the same. The 961 → 889 is measured to 20 µs
at the first camera of `test_tiles.py`. At the other 65 cameras below the gain is
6–12%, depending on how much of the view is autotiled.

The check was a script kept out of the repository. It draws with the old file and the
new one and compares the whole screen memory:

- **66 cameras.** The four of `test_tiles.py`, the corners and edges, a grid of 42,
  and 14 cameras standing one row or column *outside* the world, where the camera can
  go ([§15](#15-open-risks)).
- **45 rectangles of `tile_draw_rect`.** They are drawn over a screen of rubbish, so
  a byte written outside the rectangle would show, and with display offsets that wrap
  the ring.

Every one came out identical, including the garbage drawn outside the world.

- **`blit_tile` stays unrolled.** A loop would have given back about 100 bytes and
  cost every scroll step. It lost only what did nothing:
  - The eighth line added `&800`, which the step to the second character row then
    took straight back off.
  - The sixteenth line saved and stepped a `DE` that nobody reads after it.

  That is 14 bytes and 66 T-states a tile.
- **The autotile walks.** The pointer goes W, S, E, N, one 16-bit add from each
  neighbour to the next, instead of reloading `t_wptr` four times.
  - `ta_same` compares against the family held in `C`. It gives "equal" as the borrow
    of `sub c / sub 1`, and leaves every other register alone.
  - The four answers therefore go into `B` with `rl b`, already in order.
  - `tile_family` and `t_fam` are gone.
- **Three tables each sit on one page:** `tile_variants`, `tile_ptr` and the ore
  overlay. `pack.py` places them, and an `assert` checks it. Each lookup is an 8-bit
  add with a constant high byte, 200 times per full pass.
- **The variant × 64 is two `rrca`s and a mask**, instead of six 16-bit doublings.
- **The row loop keeps less in memory.**
  - The column count stays in `B` across `tile_one`.
  - The row's start is read as a pair.
  - The screen pointer's ring is a `res 3` on its high byte, which is always
    `&C0–&C7` on a tile's first line.
- **`tile_addr` is shorter**, and still gives the same address for every input,
  including inputs outside the world. The row's odd bit goes in with `set 7`, an OR,
  as the old `or l` did.

**What the planted faults found.** Ten faults were run against the check above and
against the four tests that draw terrain:

- The check caught nine. The tenth changed nothing in any of its cameras.
- `test_tiles.py` caught six.
- `test_scroll.py` and `test_dirty.py` caught two each: the blit's carry and the
  variant.
- `test_index.py` caught none. These three tests compare two ways of drawing that
  share `tile_addr` and `tile_src`.

That left three gaps, all older than this milestone. `test_tiles.py` closes them now:

- **The last row of the world was never drawn.** The "far corner" camera was (44,
  53), whose ten rows stop at 62.
  - It is (44, 54) now. That camera alone still shows nothing, because the test world
    has no autotiled terrain down there.
  - So a second camera at (44, 54) writes a lake into the last three rows.
  - A `ta_same` that took `&7Fxx` for outside the world passed before.
- **Two autotiled families that differ by 1 never met.** The test world has no
  mountain touching water. A comparison that also said "equal" for a difference of 1
  changed nothing anywhere, not even in the check.
  - A ring of mountains is now written around the lake, in the emulator's world and
    in the reference's.
- **No row ever crossed the end of the 2 KB ring.** The display offset was always 0,
  so the `&C8 → &C0` between two tiles was never exercised, before or after.
  - One camera now draws with an offset of 2,008, so every row wraps at column 10.

The fault that changes only the garbage outside the world is caught by the check
alone, on purpose. What is drawn there is a bug ([§15](#15-open-risks)), not
behaviour to pin down in a test.

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

**Built and checked byte-for-byte** (`tests/test_object.py`) against an
independent Python renderer written from `assets/SPRITES.md` §10 rather than
from the Z80 (`tools/scene.py`), at five camera positions chosen to break things:
a dome clipped at the bottom edge, a dome clipped at the left edge — which is
where clipping meets *mirroring*, the hard case — the western structures, and a
camera whose ring wrap falls inside a dome.

Because corridors must be under the connectors but over the shells, the global
order is two passes over the domes rather than one: **all shells, then all
corridors, then all fittings, then the structures.**

#### The object index (milestone 39)

Every redraw — a scroll strip, a placed building, a corridor row, the ghost lifted
off a dome — goes through `ob_draw_all` with a clip, and until milestone 39 that
asked **every record**: 64 dome slots twice (shells, then fittings), all 96 corridor
slots, all 32 structure slots, plus an insertion sort of the structures. For a live
object, "is it in the clip?" meant copying its record, computing its frame and, for
a corridor, its runs. Measured on the 12-dome test colony with *nothing* visible:
**49 ms**. Half of it went to the domes, a quarter to the corridors.

The index keeps, for every live object, its **bounding box in world tiles** (+128,
so the comparisons are unsigned) and its id — five bytes — in draw order: domes,
corridors, structures already sorted by `cy`. `ob_draw_all` turns the clip into world
tiles once and walks the list; rejecting an object is four compares, and whatever
passes goes to the same routines as before, which clip exactly. **The same empty pass
is 2.0 ms** (2.2 since milestone 43, below).

- **It is measured, not computed.** `oi_build` sets the camera to (0, 0), where the
  screen *is* the world, raises `ob_meas`, and calls the drawing routines themselves:
  `ob_vis` records a dome's frame (the box that already culls its shell and fittings
  together), `oc_run` each run of a corridor, `ob_struct` its sprite. A box that
  disagreed with the drawing would need two codes to disagree; there is one.
- **It lives in bank 5**, above `NEXTHOP[96][128]`, which ends at `&6FFF`: the 4 KB
  freed when the node count went from 128 to 96 were never claimed. 960 bytes at most
  (64 + 96 + 32 entries). Load clears bank 5 and redraws, which rebuilds it.
- **It is rebuilt by class.** `ob_touch` invalidates everything (a full redraw, a load);
  placing a dome or structure invalidates its class through `ob_touch_n`, a corridor
  its own. Rebuilding everything costs 56 ms on the test colony — more than one old
  pass — and the first site row of a dome was paying it for corridors that had not
  changed. Domes alone are 16 ms, corridors 32, structures 8.
- **`ob_corr`'s one-dome cache had a reader nobody knew about.** It skips re-reading
  the corridor's source dome if `d_id` already names it, and that was right only
  because the shell pass had just read *every* live dome with the current camera.
  The walk reads only the visible ones, so `d_id` could hold a frame from the last
  camera — or from (0, 0), straight out of `oi_build`. `ob_draw_all` clears it first.

The cost was **538 bytes of bank 0** (626 → 88 free). At milestone 41 the part that runs
only when the colony changes — `oi_build`, its passes and the three measuring hooks —
moved into bank 2 as `src/objindex.asm`, paid for out of the ghost's log
([§4.2](#42-the-eight-banks)); the walk, the window and the structure sort stay in bank 0,
which is now **198 bytes** out of pocket for the whole index. A full redraw that rebuilds
everything is 20 ms slower (679 → 699 ms). Everything else got
faster: a scroll step in open ground 3.0–3.4 frames → 0.6–1.0, in the base 4.0–7.8 →
1.6–5.4 ([§8.2](#82-camera)); a diagonal corridor row 60 → 10 ms
([§8.5](#85-the-dirty-list)).

`tests/test_index.py` draws each of the 200 tiles of the view **on its own**, with a
one-tile clip over a black screen, at the five cameras of `test_object.py`, and every
one must equal the same tile of the full draw. A box smaller than what its object
draws cuts it out of the tiles at its edge, while the full draw — clipped to the whole
view — still has it. Negative control: without rounding a box's right edge up, 12
tiles lose a piece of something.

Three things the prose did not say and the implementation had to decide:

- **Position.** Every anchor is a centre in half-tiles ([§3.4](#34-anchors-are-centres)),
  so `sx = 2*cx - 4*cam_tx` and `sy = 8*cy - 16*cam_ty`, and the frame's top-left
  is that minus half the frame. Until now no dome had ever had coordinates: the
  simulation never looked at `cx`/`cy` and the first two bytes of every record
  were zero. The renderer is their first reader, and `tools/colony.py` their
  first writer.
- **Diagonal corridors do not start from the connector.** The axis-aligned ones
  do — the connector sits on the ring and the corridor continues where it ends.
  A diagonal step is one tile on both axes, so two domes a diagonal apart share
  the *same* lattice of tile positions measured from their centres, and the run
  must be placed on that lattice or its two ends will not meet. `DIAG_K` says at
  which lattice step the run begins, per dome size; it is three bytes and it was
  chosen **by looking**, because the step is 16 lines while the ring's diagonal
  radius is 17, 28 and 40 — never a multiple. The rule when in doubt is *a little
  overlap onto the ring, never a gap*: the corridor's grey and the ring's grey
  are the same grey.
- **The engineer has no figure.** The art has four robots (carrier, driller,
  engineer, constructor); the simulation has three, plus a **human** engineer.
  The human takes figure 7 — the one the art calls the robot engineer — because
  at 6×6 visual pixels the colour *is* the identity, and cyan already reads as
  "the one who fixes things" ([ASSET-9](#12-asset-gaps)).

#### Smaller, at milestone 43

`src/object.asm` was the biggest thing in bank 0, 3,130 bytes, and most of it was
the same few steps written out again by every routine that needed them. Milestone 43
took it to **2,490**, and the two other clients of its clip 97 more, without changing
what anything draws — `tests/test_object.py` still compares every byte against the
independent renderer:

- **One helper per repeated step.** "This slot's `(px, py)` from a per-size table,
  plus the dome's frame" was written four times — doors, machines, ring slots and the
  start of an axial corridor; it is `ob_slot_at`. "Move by a signed `(dx, dy)` pair"
  is `ob_move`, and with a count `ob_movek`, which replaced the multiply-by-adding
  of the diagonal start and the bend. "Set width, height and flags, then blit" is
  `ob_put`, which falls into `ob_blit`. The axial corridor went from 75 bytes to 17.
- **`ob_clip` takes its arguments in registers.** All eight callers stored a
  position, a length and a clip pair into memory for it: 9 bytes each.
- **Layout as a contract.** The nine bytes of a `corr_dir` row land in `ob_src`,
  `ob_w`, `ob_h` and the five corridor variables with one `ldir`, because the
  variables are declared in that order; `ob_corr` copies a record *and the next one*
  in one go for the bend test. Both orders are `assert`ed.
- **Arithmetic that fits in a byte.** A ring slot's source was
  `size·1,152 + slot·144 + figure·16`, two calls to `ob_mul` and a table; it is
  `16·((size·8 + slot)·9 + figure)`, and the bracket is at most 215.
- **`ob_blit` adds the left-edge skip once, not per line**, and reads the
  horizontal clip straight out of `ob_clip`'s results instead of copying them.

It is faster everywhere but one place. A scroll step through the base went from
1.6–5.4 frames to 1.6–5.0, a finished building 17,971 → 15,974 µs, a site row
54,912 → 49,920. The exception is `oi_window`, now a loop over its two axes: 21 bytes
smaller and 0.16 ms slower per `ob_draw_all`, so the empty pass above is 2.2 ms
instead of 2.0.

### 8.5 The dirty list

After the initial draw, **nothing is redrawn unless it changed.** A 32-entry ring of
`(kind, id)` records what changed; the renderer knows the minimal redraw for each kind,
straight out of `assets/SPRITES.md` §8:

| Change | Redraw | Estimated | **Measured** |
|---|---|---|---|
| Colonist enters a slot | one slot | 64 µs | **1,498 µs** |
| Colonist leaves a slot | the terrain under the slot's 2×8 (up to four tiles), then the whole object pass clipped to it | 64 µs | **16.4 ms** on average, **18.5 ms** at worst (18.0 and 20.9 before milestone 43), over the 20 visible occupied slots of the test colony; 1.3 ms when the slot is off screen. The table says 1,500 and `dhs_vacate` adds 18,000 to the running total itself, so it is alone in its frame |
| Machine changes state or breaks | one machine | 530 µs | **4,992 µs** |
| Plant grows a stage | one plant | 530 µs | **4,992 µs** |
| Room type changes | one icon | ≈ 800 µs | **1,997 µs** |
| Corridor added | one connector | ≈ 450 µs | **2,995 µs** |
| Terrain tile changes, open ground | 3×3 tiles | ≈ 1,600 µs | **9,984 µs** |
| Terrain tile changes, under a dome | 3×3 tiles + every object over them | — | **59,904 µs** (99,840 before the object index, [§8.4](#84-object-pass-and-draw-order)) |
| Building finished (`DK_BUILT`) | the room icon and every machine slot; a structure, nothing | 1.4 – 5.7 frames (the whole dome) | **15,974 µs** for a medium dome (17,971 before milestone 43); a large one ≈ 42,000 by the rows above ([§6.9](#69-construction)) |
| Site placed (`DK_SITE`, one per tile row) | the terrain of one footprint row, then that dome's shell and fittings clipped to it | — | **49,920 µs** for a medium dome's row (54,912 before milestone 43); always alone in its frame ([§6.9](#69-construction)) |
| Corridor row placed (`DK_CROW`, one per tile row of a diagonal) | the whole object pass clipped to three tiles, **no terrain** — the tiles a diagonal only touches are not the corridor's, so another dome, structure or crossing corridor can stand there | — | **9,984 µs** on open ground, 14,976 over a dome, in the test colony (59,904 and 64,896 before the object index); the table says 12,000, so it is still alone in its frame — two would be 24,000 ([§6.9](#69-construction)) |

**The figure cache is rebuilt from the agents, once per burst of pushes.**
`dome_fig` is what tells the slot redraw which figure belongs where, and when the
simulation moves colonists it is stale — the figure would be drawn back where it
left and never appear where it went. The rebuild walks all 128 agents and costs a
**measured 9,984 µs, half a frame**, so it runs only when a `DK_SLOT` has been
pushed since the last tick, not on every tick. The per-item budget below does not
include it; a frame that redraws a slot can therefore overrun by half a frame,
once.

**An emptied slot is not the reverse of a filled one.** A figure's 2×8 is opaque
and has the ring baked in, so drawing it gives exactly what the full pass would.
The *empty* variant is the ring over **black** — but in the full pass the ring
is drawn over terrain, and where the ring is transparent the terrain shows. So a
colonist leaving used to leave 1–8 wrong bytes in 12 of the 20 visible slots of
the test colony ([§15](#15-open-risks) blamed clipping; it was this). Since step
42 `dh_slot` calls `dhs_vacate` when the slot it drew is empty: the terrain under
the slot's 2×8, clipped to it, then `ob_draw_all` with the same clip — which is
the full pass, by construction. It costs what reaching every object over the
slot costs, ~25 blit attempts to write sixteen bytes, and it says so: it adds
`DHS_VAC_US` = 18,000 to `dt_spent` so that nothing else shares its frame.
`tests/test_slot.py` empties every visible occupied slot at the five object-test
cameras and compares each with a full redraw, byte for byte. Since milestone 45 it is
`dhv_rect`, any rectangle, and the fitting's emptied machine slot (6×22) goes through
it too.

**And it must give the clip back on every way out.** It narrows `clip_x` to the
slot's columns before it knows whether the rows are on screen; until milestone 45 a
slot visible across but off the top or bottom returned there with `ret z`, and left
the clip a two-byte column. Every later item of the list then drew into that column —
nothing. It took a dome finishing in view after such a vacancy to show: the fitting's
`test_link.py` runs, which give the builders time, found a large factory with neither
its room icon nor any of its eight machines. The exit is `jp z,ob_clip_full` now;
`test_slot.py` reads the clip after all 200 vacancies of its five cameras, visible or
not, and with the jump aimed at a bare `ret`, four leave it narrowed.

**All five estimates were low, by 2× to 21×, and for one reason.** The blit is
not the cost. Reaching it is: page the bank, read the 24-byte dome record,
compute the frame, test visibility — all of that to write sixteen bytes. The
estimates counted the bytes.

The one cut that mattered is in the last two rows. A terrain change only needs
the object pass if an object stands on it, and [§3.5](#35-the-world-byte)'s
occupancy bits already say so: two bits per tile, read while bank 4 is still
paged in, and a robot digging in open country costs 9,984 µs instead of 99,840.

The list is processed under a **20,000 µs per-frame cap** with the remainder carried
over, and **one item always comes out** — otherwise an item costing more than the
budget would block the list for ever. That is exactly the "under a dome" row: it
overruns its frame alone, deliberately, rather than never being drawn.

**The running total is 16 bits, and until milestone 37 it could wrap.** Two corridor
rows came to 40,000 + 40,000 = 80,000, which is 14,464 after the wrap — under the
cap, so both went out in one frame. Two site rows (55,000 each) wrap to 44,464 and
had been stopping by luck. A carry out of the addition now ends the tick: it can
only mean "over".

If the 32-entry ring fills, nothing is discarded: an **overflow flag** is raised
and the caller owes a full redraw. A dropped change leaves a lie on the screen
for ever; a full redraw only costs. **Nobody paid it until milestone 34.**
`dirty_push` raised the flag and nothing read it, which went unnoticed because every
finished building repainted the whole view anyway and covered whatever had been
lost. Once a finished building became a record in this ring, a lost one would have
left a dome looking unfinished until the camera passed over it — so the main loop
now checks the flag after the wheel and pays for the full redraw (`ml_over`).

**Anything the list paints under the ghost, it paints with the ghost lifted**
([§9.3](#93-build-flow)). `dt_prep`, which every dome-shaped item goes through,
compares the dome's frame with the bounding box of the ghost's undo log and lifts
the ghost only on overlap, so the cursor over open ground costs nothing.

`tests/test_dirty.py` checks the list by **equivalence** — the same mutation
applied once through the list and once by redrawing everything must leave
identical screen memory — plus a second check that the mutation changes the
picture at all, because two paths that both do nothing agree perfectly. That is
how it found the real defect: the **empty figure variant was never drawn**.
Skipping it is right in a full redraw, where the ring has just been painted
underneath; in the dirty list it meant a colonist who walked out stayed drawn in
a dome he had left.

#### Smaller, at milestone 54

`src/dirty.asm` went from 1,126 bytes to **953**, with every redraw the same: the
equivalence checks above, `test_slot.py`'s 200 vacancies, the meteor craters of
`test_meteor.py`, the fitting, the corridor reveals and the site rows all compare the
list's picture with a full redraw, byte for byte, and all pass unchanged.

- **The terrain change had its own copy of the clipping.** `dh_tile` clamped a 3×3
  to the view axis by axis, set the `td_*` rectangle and the clip — exactly what
  `vr_clip` does for the site row and the corridor row. It is now "the world
  rectangle around the tile is `vr_*`; `vr_tiles`", and `dh_occupied` pages bank 4
  in itself and answers in the flags. 70 bytes.
- **A dome off screen returns from `dt_prep` straight to the list.** Six handlers
  began `call dt_prep` / `jr z,dt_end`; `dt_prep` now drops its caller's return
  address when there is nothing to draw, and the handlers just go on. It sits
  between them so that all but one still reach `dt_end` with a `jr`.
- **The budget is one comparison**, `spent + cost > 20,000` as a carry out of
  `spent + cost − 20,001`, with the "first item always goes" test riding on the zero
  flag that a 16-bit add leaves alone; the item's arguments are read once, as a word,
  instead of again after the decision; the ring index wraps with `and 31`.
- Pairs that sit side by side are read and written as words: `dt_a`/`dt_b`,
  `vr_tx`/`vr_ty`, `vr_w`/`vr_h` (asserted in `view.asm`), the dome's centre, and a
  clip's start and end. The vacated rectangle's tile loop keeps its position in `DE`.

**What the planted faults found.** Each change was broken on purpose, in both the old
and the new code, to see which test notices.

- An occupied tile read as free fails `test_dirty.py` (111 bytes wrong).
- **A wrong budget did not fail anything.** `test_dirty.py` only asked for "at least
  two passes". Its seven items cost 29,000 µs, so a doubled budget still needed two
  passes, and so did a vacancy that forgot its 18,000 µs.
- Now `objtest` records how many items are left after every pass, and the test
  compares that with a model built from `dirty_cost`, `DIRTY_BUD` and `DHS_VAC_US`.
  The expected record is [2, 0]. A doubled budget leaves [1, 0], and so does a
  missing vacancy charge. A halved budget leaves [5, 2, 1, 0]. All three fail.

Two paths are still not covered, because the screen is the same with the fault in
place:

- **The neighbours of a changed tile.** Craters are not autotiled, so redrawing 2×2
  instead of 3×3 shows nothing. It will show once a change reaches a tile whose
  neighbours depend on it.
- **A dome off screen.** If `dt_prep` forgets to drop the return address, the dome is
  drawn anyway, and the clip cuts the whole drawing away.

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
  `pal_planet` does exactly that and nothing else.
- Water animates by **cycling one pen** on a timer — no second frame, no blit, no cost.

This is an asset-side change and is [ASSET-7](#12-asset-gaps).

**Three of the twenty-seven firmware-to-hardware colour entries were wrong from
milestone 1 to milestone 17, and two of them were in use.** Pen 6 is the colonists
and asks for firmware 24, bright yellow; the table sent the gate array `&50` and
painted them dark blue on a dark background. Pen 5 asks for 26, bright white, and got
a grey. Nothing caught it because **every other test compares pen numbers**: the
Python reference renderer and the Z80 blitter both work in pen indices, and the golden
PNGs are coloured by the same `palette.py` table that the hardware never sees.
`tests/test_palette.py` closes that gap — it fills the screen with a pattern in which
pen *n* covers *n+1* bytes, reads the emulator's framebuffer, and checks that each
colour's **share of the screen** is the one its pen asked for. It reproduces all three
errors when the old table is restored.

**For whoever draws, `assets/palette*.gpl`** (milestones 48–49): the sixteen pens as a
GIMP palette, which Aseprite also opens — one file per planet. `palette.gpl` is the
desert, `palette_fw` itself; `palette_ice.gpl`, `palette_storm.gpl` and
`palette_barren.gpl` are `palette_fw` with that planet's four terrain pens, which is
exactly what `pal_planet` loads. The position in the list **is** the pen number, each
colour is named `pen N name (fw N) — role`, and the comments carry the pinned pens,
the terrain pens and every planet's terrain. Some pens share a colour — 11/13 and 10/14
on the desert, 7/10 on the barren moon, always one terrain pen and one icon pen — so a
conversion to indexed must keep duplicates or the pen is lost. Like everything in
`assets/`, they are generated in `CPCArt` from the same `palette.py`.
`tests/test_gpl.py` reads them the way Aseprite does (an unnamed colour line is
silently skipped, and every later pen slides up one) and compares each with
`palette_fw` and its row of `planet_pens` in `sprites.bin` — the bytes the game loads,
not the table they came from.

The barren pair is the one that could show. Pen 10 is the cyan of the solar cells and
of the ship's hull, and on the barren moon it is also the ground. Rendered over
`tile_ground_0`: the solar panels survive it, framed in pen 4; the ship's hull, which
had no frame, **vanished** and left only the cockpit, the wingtips and the engines.
The game does not draw the ship sprite yet, and the pad it would stand on is pens 1,
4, 5 and 6 only — but an approach over open ground would have shown it.

**Milestone 50 outlined the ship** in pen 1, one pixel wide and two rows tall, which is
the same width on screen in Mode 0. Pen 1 was measured, not picked: it is the only pen
with a luminance gap of at least 75 against the ground of all four planets and 113
against the pad's floor; white would have had more, and would have merged with the
ship's own nose. The shape is drawn four rows shorter so the outline fits inside the
same 16×32 — the sprite stays 512 bytes at the same offset, and 188 of its bytes
changed. The rule for whoever draws next: **art that will stand on bare terrain needs
an edge in a colour no planet's ground uses** — `tests/test_silhouette.py` checks every
outdoor structure against all four.

---

## 9. Interface

### 9.1 Controls

Keyboard and joystick, both complete — a CPC game that needs both hands on the keyboard
to pan and build is a chore. **Built**, as the table says; every action has a key *and*
a joystick alternative, read in one pass over the PSG keyboard matrix.

| Input | Action |
|---|---|
| Cursors / joystick | move the build cursor; camera follows at the viewport edge. In the menu, left/right picks the item and up/down the room ([§9.3](#93-build-flow)) |
| Fire / `COPY` | select, confirm, place; in `LOOK`, on a dome, open its fitting ([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)) |
| `ESC` | cancel, back |
| `SPACE` | open the build menu |
| `1`…`4` | speed: pause, normal, fast, very fast — the wheel advances 0 / 1 / 2 / 4 slots per frame |
| `TAB` | cycle alerts — jump the camera to the next problem |
| `H` | centre on `(0,0)` |
| `S` / `L` | save to disc, load from disc ([§11](#11-save-and-load)) — only from `LOOK`. Each opens the slot chooser: left/right pick one of three, `FIRE` goes, `ESC` backs out |
| `C` | call a colonist ship ([§6.11](#611-ships-and-arrivals)) — only from `LOOK`, and only with a Control room and a free pad |

`TAB` matters more than it looks. In a base that is 6 viewports wide, the thing that is
killing you is usually off-screen.

**Speed is more work per frame, not faster work**, and it is the one place where
rule 1 of [§7.1](#71-the-rules) is deliberately broken: four wheel slots in a frame
is four times the simulation, the frame overruns, and the screen drops frames. That
is the player's choice to make. Measured against the wheel's own frame counter
(`tests/test_speed.py`), over 400 frames each:

| Key | Wheel slots/frame | Simulation runs at |
|---|---|---|
| `1` | 0 | **stopped** — and the HUD stops being redrawn with it |
| `2` | 1 | **1.00×** nominal (0.92 before milestone 52) |
| `3` | 2 | 2.00× (1.88) |
| `4` | 4 | 4.00× (3.76) |

**Normal speed is 1.00 since milestone 52, and the twelfth it used to lose was the
HUD.** A redraw cost 1.15 frames and happened every sixteen, so the simulation got 16
of every 17.2 — with `ret` poked over the HUD the ratio was exactly 1.00. It was 0.84
before the HUD learned to redraw only what changed ([§9.2](#92-hud)), and 0.92 until
milestone 52 made the redraw 0.65 frames, which now fits in the slack of the frames
around it ([§9.2](#smaller-at-milestone-52)). `tests/test_speed.py` holds `x1` at 0.97
or better, so a HUD that grows back is a failure, not a number that drifts.

Pause does not pause the player: the cursor still moves, the build menu still opens,
and a dome can be placed on a frozen colony. That is the useful kind of pause.

**Buttons are read on the edge, the cursor on the level, and that distinction was
not a style choice.** A `ui_tick` lasts one frame when nothing moves and **3 to 9**
when the camera scrolls ([§8.2](#82-camera)); a keypress shorter than the tick is
invisible to an edge test. The test held a direction for twelve ticks and got
eleven moves. Level-triggered movement also gives auto-repeat for free, at the
rate of the tick — which is the rate the screen can actually keep up with.

**A cursor step costs 6,240 µs — a third of a frame.** Half of it used to be the
HUD: `ui_panel` rewrote rows 3–4 on every step for eighty cells that almost always
said the same thing, and guarding it with a signature (state, selection, validity,
link anchor, run count, affordability) took the step from 29,952 µs to 16,224. The
rest was the ghost, drawn one line at a time until milestone 35 made its log a list of
rectangles ([§9.3](#93-build-flow)): 17,472 → **6,240 µs** in `LOOK`, 43,680 →
18,720 with a six-tile corridor ghost on screen (**16,224** since milestone 37
stopped marking the shared diagonal tiles twice, [§9.3](#93-build-flow)), and a
large dome's ghost 131 → **18 ms** on open ground. Asserted by
`tests/test_route.py`.

### 9.2 HUD

Forty lines, five character rows, 80 bytes wide. Mode 0 gives 20 columns with an 8-px
font, which is not enough for anything, so Habitat uses a **4×8 font — 40 columns**
([ASSET-4](#12-asset-gaps)).

Forty columns is not much, so the layout is fixed and every column is always
written — which is also why there is no clearing pass. **As built:**

```
col 0         10        20        30        39
row 0   O2 ██████ PWR ██████ H2O ████·· FOD ██····
row 1   FE120 BI 40 PR 12 SP  8 ME  3 BO  2
row 2   POP 34/48 SOL 17 DAY ALL SYSTEMS OK
row 3   < DOME L    >  FE 70  BI 35        (the selection panel, §9.3)
row 4   READY  FIRE TO BUILD
```

Four bars of six cells, six stocks of three digits, and a **nineteen**-character
alert line — twenty until row 2 turned out to read `POP 34/48SOL 17`, and the space
that fixes it had to come from somewhere. Flows (O₂, power) are bars because what matters is the margin; stocks are
numbers because what matters is the quantity. **A bar turns red below one third**,
which is the only place in the HUD where a colour carries meaning on its own.

The alert line is the game's voice and it should be specific: `NO POWER — OXYGEN
GEN 2` beats `WARNING`. Today it names the condition but not yet the machine —
`NO POWER`, `LOW POWER`, `NO OXYGEN`, `LOW ON FOOD`, `LOW ON WATER`, `SANDSTORM`,
`COLONY LOST`, `ALL SYSTEMS OK` — because naming the machine needs the selection the
build mode has not built yet. The order is *how long the player has*: `NO POWER`,
`NO OXYGEN`, `LOW POWER`, then the two supply lines.

**`LOW POWER` is milestone 32's, and it is not a smaller `NO POWER`.** It means the
colony shed its load and is running life support only ([§6.5](#65-economy)): the
oxygen is fine and the factories, pumps and greenhouses are stopped. That state is
otherwise **invisible** — the only symptom is that the stores stop climbing, in the
middle of the night, which nobody watches — so the line is the whole of the player's
notice. The klaxon does not sound for it; a siren every dusk would be noise.

**The two supply lines were added at milestone 29, and the reason is that hunger is
quiet.** Asphyxiation announces itself in seconds; a store that is running out takes
sols, and every measurement of a colony dying of hunger ended the same way — the alert
line said `ALL SYSTEMS OK` right up to the first death, because oxygen and power were
indeed fine. The threshold is **less than one portion per living colonist**, which is
the point where the player can still do something about it, and it clears itself the
moment the store recovers. They sit below `NO OXYGEN` in the order, because a colony
suffocates faster than it starves.

**A HUD redraw costs 0.65 frames warm, 1.75 cold — 1.15 and 2.30 until milestone 52
([below](#smaller-at-milestone-52)) — and it has its own clock: every 16 frames of real
time.** It used to run once per wheel rotation, which broke twice over when the speed
control arrived ([§9.1](#91-controls)): the gate was `wh_slot == 0`, and at double
speed the slot counter steps by two — if the speed changed on an odd slot, zero never
came round again and **the HUD froze while the colony carried on**. Worse, tying it to
rotations meant three frames of HUD per four of simulation at `x4`, which capped that
speed at 2.3×. A fixed real-time clock fixes both: the player sees the HUD 2.6 times a
second at every speed, and `x4` delivers 3.4×.

**It used to be a full rewrite of every cell, every time.** Two things fixed that:

- **A cell cache**, 120 bytes in bank 2 — one code per cell of rows 0–2, the
  character for a glyph and `&80 + pen` for a solid bar cell. A cell whose code has
  not changed is not drawn, only stepped over. The cache is invalidated by
  `view_cam`, because a camera step turns the ring and the HUD's *bytes* move even
  though its position on screen does not.
- **Rows 3–4 belong to the panel.** `hud_draw` used to blank all eighty of them and
  `ui_panel` immediately rewrote them — 160 cell writes per tick, more than the 120
  that show anything. Now `hud_draw` stops after row 2 and the panel's own signature
  decides when rows 3–4 are redrawn.

**Both caches are invalidated by the same call, and the second one was learned the
hard way.** `hud_inval` also bumps `hud_gen`, a counter that `ui_sig` reads as the
ninth byte of the panel's signature. Without it the panel was *correct by its own
lights* — nothing it draws had changed — while its pixels had been left behind by the
ring: seventeen tiles of scrolling and rows 3–4 were terrain, permanently. Nothing in
the suite failed. It was found by taking a screenshot of the running game and looking
at the bottom of it, and the same screenshot showed a second, older bug underneath:
`uip_row4` blanked `40 − 24` columns after a 20-character string, so four columns at
the right end had never been written by the panel at all — invisible for as long as
`hud_draw` was blanking those rows first. `tests/test_build.py` now marks the memory
of rows 3–4 with `#AA`, takes one camera step, and demands all eighty cells back.

2.55 frames became 1.15. What is left is arithmetic, not pixels: six stock values
converted to digits, four bars divided into cells, and 120 cache comparisons. Skipping
a whole *field* when its value has not changed would take most of that too; it needs a
per-field cache of the last value, and it has not been worth the state yet.

#### Smaller, at milestone 52

`src/hud.asm` went from 1,032 bytes to **642**, and `ui.asm` lost 9 to it. It is also
faster: on the test state, measured over 400 redraws, a cold redraw 45,327 → **34,844
µs** and a warm one 22,764 → **12,680 µs** — the warm tick almost halved, because what
it spends its time on is exactly what got cheaper.

- **One path for every cell.** A character, a blank and a bar cell are all one code,
  the code the cache already kept (`&80 + pen` for solid), so there is one `hud_char`
  with the cache check inline, where there were `hud_char`, `hud_cell` and a shared
  `hud_seen` that pushed and popped around a compare. A skipped cell costs ~45 µs
  instead of ~87.
- **A cell's eight lines are a loop, and the loop has no counter.** A HUD row starts at
  `(y&7) == 0`, so the destination's high byte is `&C0–&C7`; eight steps of `+&800`
  take it to `&100–&107`, and the carry comes up on exactly the eighth line. The
  unrolled glyph and solid-cell copies were 160 bytes; the loops are 18, and the glyph
  line costs what it did unrolled. It does tie the HUD to a screen at `&C000`.
- **Moving one cell right is two increments and a `res 3,h`** for the ring, instead of
  a general add of `B` columns kept in step with a column counter nobody read. The one
  caller that started mid-row — the speed indicator, at column 35 — now asks
  `hud_goc` for the column directly.
- **Numbers are subtractions of 10³, 10², 10, 1** instead of sixteen shift-and-compare
  steps per digit, with no buffer. A value with more digits than the field — the
  population cap past 99, say — shows the field's last digits with leading zeros
  blanked, as it always did: one subtraction of `10^B` first throws the rest away.
- **A bar keeps its state in registers.** Six times the value is `2v + 4v`, and `4v`
  is also the "below a quarter" test; each cell takes one `max` off and an empty cell
  gives it back, so every cell after it stays empty. The five variables are gone.
- Row 0's four flows go through one `hd_flow` (label, bar, space); row 1's stock row
  reads its pointer through `ec_stock_ptr` (`src/stock.asm`, which
  `tests/objtest.asm` now includes too).

**How it was checked.** `tests/test_hud.py` compares against `tools/hudref.py`, but in
two states that touched neither overflowing numbers nor half the alerts. So the old
and the new `hud.asm` were run side by side on 362 states — random flows, stocks up to
65,535, populations to 255, every alert, warm and cold redraws in turn — and eight
camera positions, three of which put a HUD row across the ring's wrap: 789 screens,
all 16 KB of each, **no difference**. Four planted faults (the modulo, the ring, a
bar's give-back, the cache) all showed up. Three of those states are now part of
`test_hud.py`, and getting them to pass meant bringing the reference up to date: it
did not know `LOW POWER`, the meteors, food or water, and it cut numbers as strings
(`1005` → `005`) where the Z80 has always shown `  5`.

**Found on the way, not fixed:** with two Control rooms the population cap is 100,
and the HUD's two-digit field shows it as ` 0`; from three on it is capped at 128 and
shows as `28`
([§15](#15-open-risks)).

Checked byte-for-byte against `tools/hudref.py` in five states: the second because
the first exercised neither leading-zero suppression nor the alert line, the other
three (milestone 52) for numbers wider than their field, zero capacities, and the
alerts the reference had not learned.
And checked at the **boundary**: the play area is filled with a marker, the world
is drawn without the HUD, and the marker must survive — opening the clip to line
200 puts 1,886 bytes of dome into the numbers.

Cost: **1.75 frames** after a camera step, **0.65** on an ordinary tick ([§8.1](#81-screen-layout)) — 2.30 and 1.15 until milestone 52 shrank the HUD; the cold figure was 2.20 until milestone 33 paged the font in from bank 7 for every glyph drawn.

### 9.3 Build flow

`SPACE` → item → a ghost follows the cursor, snapped to the correct parity
([§3.4](#34-anchors-are-centres)), with invalid footprint tiles tinted. Fire commits,
`ESC` backs out.

**The menu is flat, not `category → item → size`.** Eleven things — three dome
sizes, corridor, four energy structures, mine, airlock, landing pad — fit on one
40-column row with their costs, and left/right cycles them. The tree cost three
presses where the list costs one, and its only advantage appears at about thirty
items, which is where it should come back.

#### The room is the second axis of the same menu

This section used to say a dome's room type is *chosen immediately after placement,
and can be changed later at a cost*. It is chosen **before** placement, on the menu
row that is already there: **left/right picks the item, up/down picks the room**, and
a dome shows its room where the other items show their name — `< OXYGEN     S >`
rather than `< DOME S >`, because "oxygen, small" is what the player is actually
choosing. Ten rooms are offered in the order you need them: Oxygen, Canteen,
Quarters, Greenhouse, Factory, Lab, Medbay, Control, Storage, Lounge.

A screen that picks a room *after* placement would need its own interface state, its
own ghost and its own notion of "which dome are you pointing at"; the second axis of
a menu that exists costs none of those. What it gives up is changing a room later,
which nothing else in the game needs yet. **Milestone 45 built that screen for the
contents** — `FIT`, below — and it cost exactly those three things: a state, a box
round a slot for a ghost, and `ui_dome` for the pointing. The room stays a menu axis.

**Two structures also ask something of the ground under them.** The water extractor
wants a lake and the mine wants an ore vein, within two tiles of the footprint
([§6.5](#65-economy)); the panel says `NEEDS WATER NEARBY` or `NEEDS AN ORE VEIN`
rather than `BLOCKED`, because in this refusal there is no bad tile to tint red and a
bare "blocked" on clean ground reads as a bug. Everything else in the catalogue is
refused only by the tiles it covers.

**A room that cannot work in that size is not offered.** `machine_rules` says
`mach_oxygen` fits only small domes ([§6.5](#65-economy)), so the Oxygen room
disappears from a medium or large dome and the selection moves to the next one that
fits — otherwise the player would pay for a dome that can never produce. The choice
is sticky rather than remembered: coming back to a small dome keeps the room you
ended on, one press away from the one you wanted.

**The ghost keeps an undo log, and that is why the cursor is cheap.** Every
rectangle it writes is recorded with the bytes it covered — address, width, height,
then the bytes row by row — and hiding it writes them back, so a cursor step costs a
box, not a redraw. The log is 1,160 bytes and the drawing refuses to write anything it
cannot take back — silently: a rectangle that does not fit is not drawn. Since milestone
41 the log is *exactly* the worst ghost, a red `DOME L` — computed in `src/const.asm`,
checked to fit whole by `tests/test_reveal.py` and to the byte by `tests/test_ghost.py`
— while the worst corridor preview is 308 ([§4.2](#42-the-eight-banks)).

**A preview must never mark the same tile twice.** Two entries for one tile overlap, the
second saves the first mark as its "background", and the undo, which walks forward,
writes that mark back last. Milestone 37 removed the case where two diagonal pieces
share a tile; milestone 40 found the other one by counting bytes. Where a diagonal
*climbs* into a horizontal run (north-east to east, north-west to west), the run's first
tile is the last piece's back tile — a front tile the walk has already passed — while
the turn skip only remembered the last front. Every such preview left one 2×4 mark on
the ground when it was hidden: 8 bytes, and 12 more in the log than the route has tiles.
`crw_h1` now remembers the run's first tile instead, which is right because a climbing
diagonal never meets its last front (every turn kind was checked in the reference). The
reference in `tests/test_route.py` and `tests/test_link.py` had the same blind spot —
it skipped only the last tile too — so the two agreed and the duplicate passed; it now
skips any tile already walked.

**Rectangles, not lines, since milestone 35.** The unit used to be one horizontal
line, so each side of a large dome's frame was 124 one-byte lines — each with two
clips, a screen-address computation and a three-byte header — and every invalid-tile
mark was four. A large dome's red ghost needed **2,412 bytes** of log and got 1,600:
five of its eight rows of marks were simply not drawn. As rectangles it needs
**1,160**, the frame is four entries, and a mark is one entry written without any
clip at all — the camera is tile-aligned, so a mark on a visible tile is inside the
view by construction. The copy loops check the ring wrap once per row instead of once
per byte, and a one-byte-wide column (a frame side) walks down the screen without
saving its address per row. Large dome, open ground: show 131 → **18 ms**. Red, over
the site just placed: 263 → **57 ms**, all of it drawn.

**After a dome is placed, the ghost waits for it.** It used to come straight back,
red, over the new site; with the site now appearing a row per frame
([§6.9](#69-construction)), every row would have had to lift it and drop it again. So
`uip_fire` leaves it off and sets `ui_owed`, and `ui_tick` shows it one frame after
the last row is out (`rv_pend` = 0) — not in the same frame, where it cost 200 ms
together with that row. Any other `ui_show` in the meantime — the player moves the
cursor, cancels, saves — pays the debt instead.

**The order inside one step is binding: hide → move → scroll → show.** Undo-log
addresses are positions in the 2 KB ring ([§8.2](#82-camera)); once the ring has
rotated under them they name different pixels. Hiding after the scroll leaves a
trail that never goes away.

**The dirty list lifts the ghost when it paints under it, and puts it back the same
way.** A colonist stepping into a ring slot under the cursor, or a building finishing
under the red ghost the player left on it, would otherwise leave the undo log holding
bytes that are no longer on screen, and cancelling the ghost would write them back — a
patch of unfinished site inside a finished dome. Two pieces, milestone 34:

- `gh_rect` keeps the **bounding box** of everything the log holds. Not the cursor
  box: in `LINK` the corridor marks lie outside it.
- A dome-shaped dirty item that intersects it **swaps** screen and log (`gh_swap`)
  before drawing, and the tick swaps once more at the end. The swap is its own
  inverse: the first puts back what was under the ghost and parks the ghost in the
  log; the second drops the ghost in the same places and keeps the *new* bytes
  underneath. Since milestone 37 a corridor row does the same from its rectangle
  (`dt_ghost_rect`): the player can step the cursor onto a diagonal whose rows are
  still to come, and `ui_show` pays the debt at once.

**Entries must not overlap.** The undo and the swap both walk the log forwards; if
two entries cover the same byte, the later one saved the earlier one's ghost as its
"background", the undo writes that last, and the ghost stays on the ground. Neither
operation is then its own inverse. Nothing overlapped by design — a mark sits inside
its tile, the frame on the tile edges — but **`cr_walk` visited the tile shared by
two consecutive diagonal pieces twice**, and a bend's horizontal run starts on the
diagonal's last tile, so every diagonal preview marked six or seven tiles twice and
left a trail of marks behind the cursor (48–56 bytes per preview, measured). The
corridor that was then built repainted its whole bounding box and hid them; drawn row
by row, they showed. Since milestone 37 the walk visits each tile once — a diagonal
of `n` steps is `n + 1` tiles — which also makes the preview cheaper (a six-tile
route's log 152 → 128 bytes).

`ui_hide` / `ui_show` would do the same and recompute everything the ghost shows —
validation, the invalid-tile marks, the corridor plan — which for a large dome on bad
ground was ~300 ms. Two swaps of a full log are ~40 (a large red ghost's log, 1,160
bytes since milestone 35, is 30 ms a swap). **Once per tick, not per item:** a
second swap would drop the ghost before the second item drew and leave it lifted at the
end. `tests/test_save.py` found exactly that — the cursor frame vanished after a load,
which repaints many ring slots under it — and `tests/test_reveal.py` now stages it on
purpose, two items under the ghost in one tick.

Three states, not four: `LOOK`, `MENU`, `PLACE` — and `LINK`, which the corridor
needs because a corridor has two ends rather than a footprint
([§9.4](#94-corridor-routing)). And since milestone 45 **`FIT`**, a dome's fitting
([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)), which lives in its own
file, `src/fit.asm`, and borrows the rest: `ui_lr` for the slot and `ui_ud` — the same
code with down/up — for the choice; `ui_dome` for the dome under the cursor; the
catalogue's price row (`uip_item`, with the machine's name where the item's goes) and
`bd_afford`/`bd_stock_pay`, because a machine's price is written to `bd_metal` and
`bd_biop` like any item's. `FIRE` in `LOOK` opens it, so the `LOOK` row says
`LOOK SPACE=BUILD FIRE=FIT C=SHIP`, and the second row — which said `FIRE=PLACE ESC=BACK`
in `LOOK`, where neither did anything — is blank there. Asking for `FIRE` in `LOOK`
costs the cursor step 47 µs: 4,945 → **4,992 µs** (`tests/test_route.py`).

**Smaller at milestone 44, doing the same.** `src/ui.asm` went from 2,224 bytes to
1,941 by writing things once: "left/right, wrapping" for the save slot and the build
menu (`ui_lr`); "lift the ghost, change state, show it again" (`ui_goto`); a ghost mark
at a *world* tile (`ui_mark`), which the route preview and the footprint's bad tiles
each did their own way; one ending for "built — now wait for the rows or redraw the
HUD" after a dome and after a corridor; and cursor, camera, footprint and box
coordinates read and written as pairs, which `assert`s in `ui.asm` and `build.asm`
hold in place. One trap on the way: the object pass already turns half-tiles into
screen coordinates, and handing it `2·tx` looked like reuse — but a footprint at the
world's edge starts left of −64, where `2·tx` does not fit a byte, so `ui_sxt` doubles
in 16 bits and joins `ob_rel` after that step. A cursor step costs what it did —
4,945 µs against 4,942, measured to 20 µs; the table-driven signature of the panel that
first went in with this was 12 bytes smaller and 139 µs dearer on every step, and was
taken back out. The wrap-around of `ui_lr`, which no test had pressed, is now checked
in `tests/test_build.py`, with the `dec e` that makes "left" wrap patched out as its
negative.

#### Smaller, at milestone 55

`src/fit.asm` went from 734 bytes to **642**, and everything the player sees is the
same. That was checked with a trace, a script kept out of the repository, which takes
645 snapshots, one after every key:

- the factory and the greenhouse of `test_fit.py`;
- every room in an S, an M and an L dome — every choice, every slot, and each choice
  fitted and taken out again;
- refusals on open ground and on a dome in another state;
- `SPACE` with Metal for only some slots.

Each snapshot holds the record, the stocks, the price, the box and its colour, rows 3
and 4 of the panel, the sound that started, and the screen. All 645 were identical
with the old file and the new one.

- **Asking and doing share one routine.** `fit_set` and `fit_show` both asked "what
  would go in, what does it cost, and is it there already?" `fit_want` now answers
  that, and leaves the price where the panel and `bd_afford` read it.
  - `fit_set` keeps the new value and the old one in `BC` instead of two variables,
    since `bd_afford` and `bd_stock_pay` leave `BC` alone.
  - It gives the half back last. Its second stock falls into the code that adds the
    first.
- **The list is copied together with its empty choice.**
  - `rooms.asm` puts a `NO_MACH` byte in front of `rm_buf`, and `fl_green` begins
    with one. One `ldir` of count + 1 fills `fit_lst`, so a room without machines
    needs no special case.
  - `fit_list` went into `fit_enter`, its only caller.
  - `fit_pick` finds the slot's content with `cpir`.
- **The first variety of each crop class is the first four bytes of `rm_plants`**,
  where the old mixed rotation starts. `fw_base` was a second copy of those four
  bytes. MIXED and the four classes now take one path: the index is the slot (for
  MIXED) or the class, and starch and vegetables add the slot mod 5.
- **Smaller pieces:**
  - Each machine's price is one byte, Metal + 32 × Bioplastic. That is 12 bytes
    instead of 24, for 5 more bytes of code.
  - The box's red or green is `bd_afford`'s 0 or 1, `xor PEN_OK`.
  - The refusal's sound is the build sound minus one. Both of these are `assert`ed.
  - Variables that are read together sit side by side.

**What the planted faults found.** Ten faults were run against the trace and against
`test_fit.py`. The trace caught all ten. `test_fit.py` caught eight, and two passed:

- **`fit_pick` one place off.** The test's `pick()` presses up or down from wherever
  the choice stands, so a wrong starting point only cost it more presses.
- **The refusal playing the build sound.** No test listened to the sounds.

Both are checked now:

- The choice is read back in every slot, in the factory and in the greenhouse. The
  negative patches `fit_pick` one place off.
- `test_fit.py` records which effect starts during a key press: `sn_st` landing on an
  effect's first step. It expects the build sound on a replacement, and the refusal
  on a failed `FIRE` and on a `SPACE` with Metal for three slots out of eight.

A price decoded with one rotation short also fails the test. With the old `fit.asm`,
every new check passes except the patch, which looks for an instruction the old
search did not have.

#### Smaller and faster, at milestone 58

`src/ghost.asm` went from 484 bytes to **428**, and every operation on the ghost got
faster or stayed the same: a box 2.1 % faster, a mark 3.7 %, a swap 0.7 %, an undo
1.4 %. Not one of the 1,600 operations below got slower. That was measured with
interrupts off, to the microsecond, because at 10 µs steps the noise of the ISR was
larger than the difference.

The check was a script kept out of the repository. It calls the ghost's routines
directly on a screen full of noise, from four camera offsets, two of which wrap the
ring inside a row. It runs 1,600 operations:

- boxes at every position and size, inside and outside the view;
- marks, inside and outside;
- swaps, undos, resets, pens and clip windows.

After each one it compares the screen, the log up to `gh_ptr`, the pointer, the
bounding box and `gh_rect`'s inputs. All 1,600 were identical with the old file and
the new one.

- **"Does it fit?" is a carry.** The size check started `HL` at 4, added w × h and
  the log pointer, and subtracted the limit. It now starts at 4 *minus* the limit,
  so the last `add` carries exactly when the rectangle does not fit. There is no
  `sbc` and no second constant: 6 bytes, and 8 µs a rectangle. An `assert` holds
  w × h below the point where an earlier `add` could carry.
- **The bounding box loads what the screen address needs.** The box grows one axis
  at a time (`gh_bbox`, once for x and once for y), from a pair loaded as a word.
  Each pair's first byte is the x or the y that `scr_addr` wants, so neither is read
  from memory again.
- **The record's header comes from one load.** `gh_pen` sits in front of `gh_hs`,
  so `ld bc,(gh_pen)` brings the pen and the height together. `gh_swap` reads its
  header without going back through `IXH`.
- **Falling through instead of jumping:**
  - `gh_box` falls into `gh_rect`, and `gh_undo` into `gh_reset`.
  - The copy loop, which only `gh_rect` called, is inside it.
- **Smaller pieces:**
  - `gh_wrap` carries into `D` itself. The slow loops step with `inc e` and call it
    on zero, instead of `inc de` and a test of `E`.
  - The clipped height and start, and a mark's sizes, are written as words.
  - The frame's top writes `gh_bw` and `GH_EDGE` as one word.

An `ldir` for the top of the frame was 7 bytes smaller and 10 µs slower per box, and
stayed out. One thing is left for a milestone that is buying speed. The size check
loops over the width, which is right for the frame's sides (1 × 124). It is wrong
for the top and bottom (34 × 2), where it takes 34 rounds where 2 would do: about
4 % of a large dome's frame. Looping over the smaller of the two would cost about 9
bytes.

**What the planted faults found.** Twenty-two faults were run against the script and
against `test_build.py`, `test_reveal.py`, `test_route.py`, `test_fit.py` and
`test_map.py`. The script caught all twenty-two. Six passed those five tests:

- `gh_wrap` without its `inc d`;
- the ring stepping back 7 instead of 8;
- either slow loop not calling `gh_wrap`;
- every row taking the fast loop;
- a mark below the view's last row drawn anyway.

`test_link.py`, which takes two minutes, caught five of the six, all in one picture:
the north-east diagonal between two M domes. The ring stepping back 7 passed every
test. A seventh fault, a log one byte longer than `GH_LOG`, would write the first
byte of bank 2's code. It was caught only because `test_reveal.py` could no longer
find the constant it patches.

None of those tests looks at **where** the ghost is drawn. The undo writes back to
the same addresses it saved, so a ghost in the wrong place leaves just as cleanly.
`tests/test_ghost.py` does look. It runs 1,200 operations of the same kinds, from
the same four camera offsets, against a model written from the prose:

- `ob_clip`;
- the screen address of [§8.2](#82-camera);
- the record (address, width, height, bytes);
- the frame's four sides;
- the size check.

After every operation it compares the screen, the log and the bounding box, byte for
byte. It also checks the limit exactly: a mark goes in with 12 bytes left, and with
11 it touches nothing — not the screen, not the bounding box, not the byte after the
log. It has two negatives:

- `gh_wrap`'s `inc d` patched to `nop`;
- the limit raised by one byte.

It catches all twenty-two faults. With the old `ghost.asm`, every check passes
except the two patches, which look for instructions the old code did not have.

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

**As built: at most two runs, and the bend is the whole problem.** There is no
90° corner sprite in the set, so a route cannot be an L; the only turn that exists
is diagonal → axial, and it only works if the pieces land on the same grid.

The diagonal tile is 8×16 — **two tiles wide, one tall** — stepping `(4, 16)`, so
consecutive tiles overlap by a whole tile and the line they draw passes through the
lattice points `(4j, 16j)` measured from the dome centre. The horizontal corridor is
4×8: one tile wide, half a tile tall, sitting in the **top** half of its row. The
vertical is 2×16: half a tile wide, in the **left** half of its column. Both leave a
dome through a connector at the middle of a side, so their lane passes exactly through
the dome's centre — which is why an axial run only exists between centres that share a
coordinate.

From that, the two turns, and they are **not** symmetric:

| Turn | Diagonal stops at lattice | Axial run starts |
|---|---|---|
| → horizontal | `T` = the vertical distance in tiles | one tile **back**, on the last diagonal tile |
| → vertical | `S − 1`, one step **short** | at that same lattice row, in the destination's column |

The horizontal case can afford to overshoot because the diagonal tile is only one tile
tall — the lane covers it. The vertical case cannot: the tile is two tiles wide and a
vertical lane is half a tile, so a diagonal that ran to `S` would leave a tail sticking
out beside the lane. Both shapes were chosen by **rendering four candidates each and
looking**, not by algebra; the losing candidates are in the commit that added
`tools/route.py`.

**Two records, not one.** The corridor record holds a single run, so a bent route is
written as two adjacent records, the second with `C_A = 255` meaning *continues the
previous*. The graph ignores it — one edge, not two — and the renderer draws it
together with the first, from where that one stopped, without knowing anything about
routing. The door scan ignores it too, which it did not at first: `C_A = 255` indexed
`dome_conn + 255`, 191 bytes past the array.

**B's door belongs to the last run.** A corridor leaves A in the direction of its
first run and arrives at B against the direction of its **last** — for a bent route,
the continuation's. Until milestone 36 the door scan (`ob_conn_scan`) gave B the
door opposite the *diagonal*, at a point on the ring where nothing arrives, and the
axial run met a ring with no door in it. It was in `tests/golden/route_*.png` all
along — a stub on the north-west of the right-hand dome, attached to nothing — and no
check saw it because `tools/scene.py`, the Python reference, had the same rule, so the
two renderers agreed with each other. The scan now looks one record ahead, and so do
`scene.dome_dirs` and the `DK_CONN` that `cr_redraw` pushes for B.

**A tile in either end's footprint is the corridor's.** The check rejects a route
over any occupied tile, water or mountain — **except** inside the square footprint of
the two domes it joins. A diagonal starts `DIAG_K` lattice steps out, where the
*round* ring ends, and its first tiles are the corner of the *square* footprint,
which `bd_commit` stamps occupied; a pure diagonal ends in the destination's corner
the same way, and a large dome's diagonal crosses two of its corner tiles. Until
milestone 36 every one of them counted as blocked, so **no corridor with a diagonal
could be built between domes the player had placed** — only straight ones, and a dome
not in line with another could not join the colony. Nothing but the dome itself can
stand in its footprint, so occupancy has nothing to say there; whether a piece of
corridor lands on the ring is the geometry's call (`DIAG_K`, the turn table above),
and the geometry was already right. `tests/test_route.py` never saw it because it
plants its domes in the table without occupancy; `tests/test_link.py` places them
through the interface.

**The walk visits each tile once** (milestone 37): two consecutive diagonal pieces
share a tile, and the bend's horizontal run starts on the diagonal's last one. The
check, the stamp and the redraw box did not care; the ghost did ([§9.3](#93-build-flow)).

**Both directions are tried.** The diagonal is anchored on the lattice of whichever
dome the route *starts* from, so A→B and B→A are different questions; the router asks
both and keeps the one that works.

**There is a band it cannot route, and it is the art's limit, not the code's.** The
turn spends `|S − T|` tiles on the remaining axis and the destination dome eats its own
radius, so when the two axes differ by less than that radius there is no tile left for
the axial run and the route is refused — the panel says `NO ROUTE FROM THERE`. The
uncoverable band is the "nearly diagonal" one, 2–4 tiles wide. Closing it needs a
corner sprite or a free-floating diagonal anchored between two stubs, i.e. three runs;
neither is free and the second is a lot of geometry for a case the player can avoid by
moving the dome two tiles.

**Corridors commit as `DS_ACTIVE`, not `DS_BUILDING`** — see
[§6.9](#69-construction) for why, and it is a real divergence.

**Only pressurised things cost Bioplastic.** Domes, corridors and the airlock keep
their Bioplastic price; the solar panel, turbine, collector, extractor, mine and pad
are steel and glass and cost Metal only. The reason is the chain and not the fiction:
the single source of Bioplastic is `mach_bioplastic`, which wants a greenhouse *and*
a medium Factory — two domes, both of which cost Bioplastic. With everything priced
in both, a colony spent its opening 30 on four structures and could then build
**nothing at all, ever**, because the thing it needed to make more of was behind the
thing it could no longer afford. Metal has a mine and `mach_iron` behind it and can
recover; Bioplastic could not, so Bioplastic is the one that must not gate the first
hour ([§10.1](#101-start-state)).

Costed **per tile**: the catalogue's 6 Metal / 3 Bioplastic is the price of one
corridor tile, because the length is chosen by the geometry and not by the player —
and the panel shows the total for the route it is previewing, not the unit price,
for the same reason.

The whole thing has an independent Python twin, `tools/route.py`, and
`tests/test_route.py` compares the two over every pair of domes in the test colony —
66 pairs, 20 of them bent — on three things: whether a route exists, which dome it
starts from, and **which tiles it covers**. Then it compares the *picture*: the Z80's
screen against the Python renderer at two cameras, one per kind of bend. Moving the
bend by one tile changes 224 bytes, which is the negative control.

What that comparison cannot see is a rule both twins share, and two did slip through
it: the footprint corner and B's door, above. `tests/test_link.py` holds them in the
real binary with domes placed through the interface — eleven geometries, all three
sizes at the start and the end, both turns, the turn landing exactly on B's door, two
domes whose footprints touch — and asks the check for **0** bad tiles on routes that
cross **1 to 6** occupied tiles of their own ends. Its negatives: a stone in the middle
of a diagonal and a third dome across it must still block (the exemption is for the
two ends only), and with `crk_in` patched out the sweep finds the corners again.
Four corridors are then built, and each must match a full redraw byte for byte and
carry its doors on the first run's side and opposite the last; the old door scan
fails three of the four on both counts.

### 9.5 Sound

**The AY-3-8912 has no ports of its own on this machine.** It hangs off the PPI's
port A — and the *keyboard* hangs off the AY's own port A. One write to a sound
register is five port writes: PPI control `#82` (port A to output), port A = the
register number, port C = `#C0` then `#00` (latch the address), port A = the value,
port C = `#80` then `#00` (write it). Miss one and nothing reaches the chip, silently.
It is the same protocol `in_scan` uses to read keys ([§9.1](#91-controls)), and the
two now share their constants rather than each declaring their own.

**Bit 6 of R7 stays zero forever.** It is the direction of the AY's port A: set it and
every keyboard row reads `#FF` — every key pressed at once. The mixer is written only
from a shadow byte that starts `#3F` and never touches bits 6–7.

**Three channels, one effect each, and priority decides.**

| | bytes | meaning |
|---|---|---|
| effect header | 2 | channel 0–2, priority |
| step | 4 | frames, volume, period lo, period hi |
| end | 1 | a zero frame count |

A volume with bit 7 set makes the step *noise*: the low byte goes to R6 and the mixer
opens noise instead of tone on that channel. Tone period is `62500 / Hz` — the AY's
1 MHz clock divided by 16 — so 284 is A3 at 220 Hz and 120 is C5.

An effect takes its channel only if its priority is **greater than or equal to** what
is playing there. Without that rule the cursor — fifteen steps a second with the key
held — would cut the alarm to pieces.

| Effect | Channel | Priority | Fires when |
|---|---|---|---|
| `MOVE` | 2 | 1 | the cursor steps |
| `MENU` | 2 | 2 | the catalogue opens or the selection changes |
| `DENY` | 2 | 4 | invalid position, not enough material, no room in the tables |
| `BUILD` | 1 | 3 | a dome or a corridor is committed |
| `DONE` | 1 | 5 | a building finishes and turns `DS_ACTIVE` |
| `SHIP` | 0 | 6 | a ship touches the pad |
| `METEOR` | 0 | 7 | a meteor lands — noise, 15 → 4 over 20 frames, once per impact ([§6.10](#610-events-and-hazards)) |
| `ALERT` | 0 | 8 | power or oxygen **just** failed |
| `DEATH` | 0 | 9 | a colonist dies |

Channel 2 is the interface, 1 is building, 0 is the colony — so a placement never cuts
an alarm and the cursor never cuts either.

**The alarm is an edge, not a state.** `ml_alert` compares power-and-oxygen with a
shadow byte once every sixteen frames, on the HUD's clock, and sounds only on the fall.
The shadow starts at 0 — *things are already bad* — because [§10.1](#101-start-state)
starts with no power and an alarm in the first second of a new game says nothing.

**Cost: 100 µs a frame in silence, 195 µs while something plays** — half a percent of
a frame, against the "service audio" line in [§7](#7-the-batch-scheduler)'s per-frame
list. Registers are written only when a *step* changes, not every frame. The player
lives in bank 2 next to `build.asm` and `route.asm`, so it is callable from the
simulation without paging; `snd_ping` is the register-preserving door the simulation
uses, since `nd_die` and `st_land` are holding agent pointers when they ring.

**Testing sound is the same problem as testing pixels, and it has the same two
answers.** The headless emulator now exposes the AY's sixteen registers
(`cpcemu_psg_reg`), so `tests/test_sound.py` reads what reached the *chip*: every
effect is played tick by tick against a Python reference written from the format above,
and the keyboard is scanned alternately with the sound to prove the shared PPI survives.
Three negative controls: drop the PSG's "write" strobe and nothing changes; make a step
last one frame too long and the reference diverges at tick 1; set bit 6 of R7 and the
keyboard reports every key held.

And because sound cannot be looked at, it is **rendered**: `tools/ayrender.py` turns
the captured register timeline into `build/sounds.wav` — square waves, a 17-bit noise
LFSR and the chip's logarithmic volume curve. That is how the effects were judged, and
how the octave error in the renderer itself was caught: the first version clocked the
tone counter at clock/16 instead of clock/8, and everything came out an octave low.

**In-game music is not planned.** Three channels are three channels: a tune would have
to fight the effects for them, and a colony sim is listened to, not danced to. The
2,048-byte audio reservation in bank 7 ([§4.2](#42-the-eight-banks)) was never
touched, and at milestone 33 the font moved into it ([§4.3](#43-bank-2-flat-again));
the effects cost ~450 bytes in bank 2 and the loading music below lives in the
generator.
#### Music, and why the generator has a second player

**The thirteen and a half seconds of world generation now have a tune**, and it is
played by a *different* player from the one above. The game's sound lives in bank 2,
and bank 2 does not exist yet while the generator runs: `PAGE2.BIN` is sitting in
scratch memory waiting for the endgame to copy it down ([§13.1](#131-three-ways-a-loader-does-not-run)).
So `gen.asm` carries its own: two channels, a list of notes each, 420 bytes of the
768 it had spare.

**The clock is the world being built.** Interrupts are off — the generator pages bank 4
in and out and is not sharing that with the firmware — so there is no frame interrupt
to keep time. The tile loop keeps it instead: one beat every 32 tiles, which at the
measured 541 µs per tile is about 17 ms. **The tempo therefore wobbles**, and by more
than a little: measured note lengths of 22, 21, 30, 12, 74, 47, 56 and 112 frames
against a score that says 30, 30, 45, 15, 60, 30, 30, 60 beats. Tiles are not equal
work — water and mountains cost more than dust — so the music slows down where the
world gets complicated and stops entirely for `gen_despeckle`. It sounds like a music
box winding down, which for this particular thirteen seconds is not the worst thing.
The fix, if it ever matters, is to let the generator run with interrupts on and hang
the player off the firmware's ticker.

**The volume is software, not the AY's envelope generator.** The hardware envelope is
two register writes a note and would have been cheaper — but then `R8` says only *"use
the envelope"* and the actual loudness is invisible to anything reading the registers.
Neither `tests/test_disc.py` nor `tools/ayrender.py` could then tell whether a note
sounded. Instead every second beat drops the volume by one, 13 down to 0 in about half
a second, and **what is audible is exactly what the registers say**. That property is
what makes the whole sound chapter testable, and it was worth twenty bytes to keep it.

`tests/test_disc.py` samples the chip every 30 frames through the whole load: at least
five distinct pitches must appear, at least ten samples must have volume, and when the
game starts the chip must be **silent** — that last one caught a real bug.

**Every new game sounded the alarm in its first second.** `ml_alert` fires on the edge
from "fine" to "not fine", and the start state of [§10.1](#101-start-state) begins with
the economy's `POK` flag still saying *fine* — it only becomes 0 when the first
revolution of the wheel actually computes the power balance. So every game began with a
siren about a power failure that had always been true. The alarm now waits three calls
— about a second — before it starts watching.


---

## 10. Progression

### 10.1 Start state

At `(0,0)`, on guaranteed flat foundation: a landing pad, one small **Oxygen** dome with
one `mach_oxygen`, one small **Quarters**, one small **Storage**, and the corridors
joining them. Four colonists: two workers, one engineer, one biologist. Starting stock:
60 Water, 40 Food, **60 Ore, 75 Metal, 45 Bioplastic**, 4 Spares.

Enough to live about two sols without doing anything, which is exactly how long it
should take to realise you need power before you need anything else.

**The metal and bioplastic were 30 and 10, and that bought exactly one building.**
A colony that lives needs **three**: a solar panel (15 Metal) for oxygen by day, a
collector (14) for the 40% of the sol that has no sun
([§6.10](#610-events-and-hazards)), and an extractor (22) for water — 51 Metal, and
at the time 26 Bioplastic as well, because everything was priced in both. With 30 and
10 the player bought one building and it did not matter which: every line ended
before sol 5. 55 and 30 bought all three and left 4 and 4, which is not a fourth
building.

**It is now 60 Ore / 75 Metal / 45 Bioplastic, and the extra buys a Factory.** The
opening has to afford one thing more than survival — the dome that turns ore into
metal — or the colony is playing out of its allowance for ever
([§15](#15-open-risks) said so, and this is the measurement that closes it). At the
step-27 catalogue a panel, an extractor and a small Factory cost **57 Metal and 10
Bioplastic**, leaving 18 Metal; and those 18 are the point. Measured at ×4 over eight
sols (`tools/balance.py`, scenario 6), the Factory ate the whole 60 Ore by sol 4 and
turned it into **30 Metal — 18 → 48**, two Ore to one Metal. 48 is a mine (30) and
change, so the mine is bought out of production rather than out of the start state,
and from there the loop is closed: mine → Ore → `mach_iron` → Metal → mine.

The 60 Ore is there for exactly that reason. Without it the Factory has nothing to
eat until a mine is standing, and the mine is the thing the Factory is supposed to
pay for.

**And since milestone 31 the opening has a place in it, not just a shopping list.**
The extractor goes where the water is and the mine where the vein is
([§6.5](#65-economy)), so the first thing the player does with the cursor is look at
the map they were given. The start colony itself needs nothing of the sort — pad,
Oxygen, Quarters, Storage — and [§5.6](#56-feature-anchors) guarantees both materials
within 30 tiles of the centre; in this seed they are 4 and 7 tiles out, which is one
screen of scrolling.

**Measured, at ×4, eight sols, with nobody touching the controls afterwards**
(`tools/balance.py`, which builds through the real menu and then watches; since
milestone 45 it also fits every dome it builds through the fitting screen, round
robin over the room's list — what the dome used to do by itself — and the opening's
lines come out byte for byte as at milestone 44):

| The player builds | First death | Of what |
|---|---|---|
| nothing | **sol 2** | oxygen — 54 Water and 36 Food still in store |
| a solar panel | sol 7 | thirst, then hunger; life support runs in daylight |
| panel + collector | sol 5 | thirst — but oxygen never drops, day or night |
| panel + turbine | sol 5 | thirst — the same answer by the other route |
| panel + extractor | **none in 8 sols** | Water reaches 247, Food is gone by sol 6 |
| panel + collector + extractor | **none in 8 sols** | Food gone by sol 7 and still nobody dead — Water 373 and climbing, battery full |
| panel + extractor + small **Factory** | **none in 8 sols** | Ore 60 → 0 by sol 4, Metal 18 → **48**; Food gone by sol 6 and nobody dead by sol 8 |
| greenhouse + lab + canteen (with the materials given) | **none in 8 sols** | **The first colony that feeds itself**: Food 46 → **68** by sol 6 and 60 at sol 8, four colonists eating out of it the whole way. Water is the new tight one — 71 → 5, because every pot drinks. At milestone 45, with the domes fitted through the new screen: Food 41 → **61** by sol 4 and 50 at sol 8, Water 63 → 5, nobody dead |
| the same, plus two colonist ships — **twelve people** | **sol 6** | **Re-measured at milestone 45, and identical at 44** — the first death falls on the same frame, 24,426, in both builds. Water is gone by sol 2 and Food by sol 5. This row used to read "none in 8 sols; Food dips to 0 around sol 5 and climbs back to 26"; when that stopped being true was not tracked, which is the argument for re-running the table at each milestone that touches the economy |

Every line that solves water used to end at the same wall: **Food**, which needs a
greenhouse and a `mach_food`, which needs a dome that can be given a room. Rooms are
built ([§9.3](#93-build-flow)) and the chain runs — with the slot order fixed
([§6.5](#65-economy)) a greenhouse grows Starch *and* Vegetables, a Lab makes
Vitromeat, and `tools/balance.py` shows Food climbing **34 → 38** in a colony that is
eating out of it at the same time.

**The wall looked like people and was a bug.** That same run used to lose everyone
from sol 2 with 37 Food in the warehouse, and the reading was "four colonists cannot
staff seven machines and also eat". They could: they were being sent back to work
every time they set off for the canteen ([§6.6](#66-needs)). With that fixed the
colony runs the full eight sols with nobody dead and Food climbing again by sol 8.

**And then the chain itself was measured, and three things were wrong with it**
([§6.5](#65-economy), [§6.7](#67-jobs)): a greenhouse demanded one biologist per pot,
`mach_vitromeat` matched the canteen exactly instead of leaving headroom, and every
`Operate` job had the same priority so the nearest dome took everyone and the canteen
was never staffed. With those three fixed, the same twelve-person colony that used to
be wiped out by sol 5 **survives the full eight sols**, its store dipping to zero and
recovering. It has no margin: one chain feeds twelve only if nothing goes wrong, and
the honest advice is a second canteen — which the HUD now asks for out loud
([§9.2](#92-hud)).

That is the shape [§10.1](#101-start-state) always claimed and never had: before the
economy got a clock ([§6.5](#65-economy)) the answer was "sol 1½, of thirst, whatever
you build".

**Written** (`src/newgame.asm`), with three departures from the paragraph above.
The three domes sit 8 tiles apart centre to centre, because that is the closest
spacing that leaves a whole number of corridor tiles between two small domes
([§9.4](#94-corridor-routing)); **the pad is joined by an outdoor edge, not a
corridor**, because a corridor record can only name domes; and the third dome is a
**Canteen, not a Storage**, because the needs pass looks for exactly three room types
([§6.6](#66-needs)) and without a canteen nobody ever eats or drinks — the two sols
above would have been spent dying of thirst beside full tanks. Storage is the room no
pass reads yet, so it was the cheapest one to give up.

**And the Quarters came with a medbay fixture in them.** `mach_beds` wants an
operator and produces **nothing** — it is furniture that makes a *medbay* work, and
`room_machines` never puts it in a Quarters, so no dome the player builds has one. The
start state hand-placed one anyway, and because the job board cannot tell a useless
post from a useful one, **one of the four colonists spent 96% of the game making
beds** while the canteen next door waited for a cook. Sleep is satisfied by the room,
not by the beds ([§6.6](#66-needs)), so the machine is simply gone.

**And for a while the Quarters were a second oxygen generator.** `ob_domeadr`
destroys `DE`, which is where the setup loop was holding the machine id, so every
dome in the start state was given machine 0. Nothing looked wrong — sleep is
satisfied by the *room*, not by the beds — but life support drank twice the water and
demanded twice the power, and that is the whole of the opening's balance. It was
found by measuring the colony's curve, not by reading the loop.

The table that matters most is the job board: **its empty value is 255 and zero
means `J_BUILD`**, so a board that was never initialised reads as thirty-two Build
jobs and the build mode finds nowhere to post. Colonists likewise start with every
need at 255 — starting at zero kills them before they can walk to the fridge.

The generator is **not** part of this binary ([§4.2](#42-the-eight-banks)), so a
new game is two loads: generate the plane, then load the game over the generator.

### 10.2 Milestones

No victory screen — Planetbase's own choice, and the right one for a game about a
colony that either continues or does not.

| Milestone | Requirement | Reachable today? |
|---|---|---|
| Foothold | 10 colonists, all needs green for one sol | ✅ |
| Industry | Metal, Bioplastic and Spares produced on site | ✅ |
| Independence | all ten stocks produced on site; no merchant trade for five sols | ✅ |
| Automation | 8 bots working | ⚠️ — reachable now: the build mode posts Build jobs |
| Habitat | 80 colonists, independent, five consecutive sols with no deaths | ✅ |

**"All needs green" is the colony's indicator, not every colonist's bar.** With ninety
people somebody is always walking to the canteen, and a milestone that can never be
met is not a milestone. It reads oxygen, power, and whether there is any water and
food at all — which is what a player would see on the HUD.

Everything is counted **once per sol**, in one pass, and never inside the hot slots:
128 agents every 750 revolutions costs nothing. Milestones are sticky; streaks are not.

**Automation has a source now.** Bots are eligible only for Haul, Drill and Build
([§6.7](#67-jobs)). Haul and Drill still have no publisher — they need structures
with output — but **Build does**: every dome or structure the player places posts
one ([§6.9](#69-construction)). It is the only one of the three that a player can
cause on purpose, which makes it the right one to have arrived first.

**The sol length is data, not a constant.** A test that wants to watch five sols
cannot wait 60,000 frames, so `sollen` and `daylen` live in the economy record. The
game ships with 12,000 and 7,200.

#### Smaller, at milestone 57

`src/ship.asm` went from 574 bytes to **377**, a third of the file, and slot 15 got
faster where it does any work: a colonist landing 4,300 → 3,710 µs, visitors
4,220 → 4,000, the sol 3,850 → 2,450. Nothing else changed.

That was checked with a script kept out of the repository. It runs slot 15 pinned
through 93 states with the old file and the new one:

- a ship in every state, and an ETA that needs both bytes;
- colonists with the cap at every distance from full, and with two free agent ids
  or none;
- visitors with 100, 6, 5 and no Food;
- the visitor roll with the pad free, taken, and missing;
- each streak's condition, at 254 and 255;
- bots by count, role and flags;
- 33 production masks against three no-trade streaks;
- each Habitat condition on both sides of its line.

Every state came out byte for byte the same, the sound included, and the same as the
reference.

- **The milestones' goods are two constant masks.** Industry's three goods and
  Independence's ten went in as lists. A loop then rebuilt each bit with shifts every
  sol, and a routine compared them one by one. Now Industry is an `and`/`cp` on the
  low byte of `EC_PRODM`. Independence is "`(high | &FC) & low` is 255".
- **The milestones go straight into `EC_MILE`.** Each one is a `set n,(hl)`, with
  `HL` held on the byte. Habitat reads Independence with `bit`, including a bit set
  in the same sol. The copy (`sh_mile`), the routine that ORed into it, and the
  bots' counter in memory are gone.
- **The three streaks are one routine.** It takes a pointer to the counter and the
  zero flag: Z continues (+1, up to 255), NZ breaks (0). The sol's deaths and trades
  are read, cleared and turned into that flag. The streaks sit side by side, which an
  `assert` holds.
- **A new colonist is a table:** the six pages after the flags, low half and high
  half each. `ship_crew` writes the pad's node into the table. It also counts every
  birth into `EC_ALIVE` at once, so every exit finds the count right — the bug
  milestone 38 fixed can no longer be written.
- **Smaller pieces:**
  - "INCOMING → LANDED, LANDED → gone" is `add a,a / and 3`.
  - The visitors' Food is read and written at its own address, not through
    `ec_stock_ptr`.
  - Kind and state are written as one word in `ship_call`.

**The reference had a bug of its own.** `tools/econ.py` counted the green streak
without the ceiling the other two have. A colony on its 255th green sol would have
made it overflow the byte that `to_bytes` writes, which raised an error. The Z80 had
always stopped at 255. No test had come near 255 sols; the script above did.

**What the planted faults found.** Fifteen faults were run, one in each branch:

- The script caught all fifteen.
- `test_sim.py` caught five.
- `test_game.py` caught none.

Ten passed every test. `test_game.py` lands its four colonists on a colony with a cap
of 52 and four people, and its `C` key checks for the pad before `ship_call` does. The
ten were:

- the pad check in `ship_call`;
- the visitors' Food going below zero;
- morale running over 255;
- the population cap;
- a streak passing 255;
- bots counted from role 4;
- Automation from nine bots;
- Industry without Spares;
- Independence without the tenth good;
- Habitat reading the wrong milestone.

They are cases in `test_sim.py` now (`SHIP_CASES`), Z80 against the reference with
slot 15 pinned. Each of the ten faults fails it at its own case. The old `ship.asm`
passes it, negative included.

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
because its workspace at `&A700–&BFFF` is occupied by bank 2 data. **Built**: `S`
and `L` open a slot chooser, both only from `LOOK`.

| Sector | Section | Bytes |
|---|---|---|
| 0 | Header: magic, version, seed, planet, camera, cursor, slot | 512 |
| 1–32 | **World plane, verbatim** — bank 4 | 16,384 |
| 33–41 | Agents, domes, structures, corridors, slot occupancy, seed — bank 6 `&6C00–&7DFF` | 4,608 |
| 42–45 | Economy, job board, node graph — bank 2 `&A400–&ABFF` | 2,048 |
| | **Total** | **23,552** |

The world plane **is** saved, in full. Regenerating it from the seed would cost
13.5 s on every load ([§5.10](#510-player-modification)); the 46 sectors cost
**0.7 s measured in the emulator** (`tests/test_save.py`) — real hardware will be
several times that, because the emulator has no rotational latency and a real
drive waits for each sector to come round.

**Nothing derived is saved**, and that is the rule that makes the file this small:
not `NEXTHOP` (12 KB, rebuilt by the wheel), not the figure cache (rebuilt from the
agents), not the dirty list, not the wheel's position. Loading rebuilds all of it in
the same order a new game does — `wheel_reset`, `rt_mark`, `dirty_reset`, `gh_reset`,
then a full draw. `NEXTHOP` is **zeroed** first, exactly as the loader leaves it at
boot ([§13.1](#131-three-ways-a-loader-does-not-run)): a stale next-hop is not
garbage, it is a *valid neighbour of another world*, and an agent reading one walks
off in a direction that made sense in a game that no longer exists.

**Where on the disc.** A slot is 6 tracks (54 sectors, 46 used) and the three live at
tracks 24, 30 and 36 — the disc holds 42. `sv_save` and `sv_load` take a slot number,
and **all three are now reachable**: `S` and `L` no longer save and load on the spot,
they open a one-line chooser in the panel — `SAVE TO SLOT 2`, left and right to
change, `FIRE` to go, `ESC` to back out. The choice is *remembered*, because a player
who saves into slot 3 usually saves into slot 3 again. Until milestone 22 the UI
passed `xor a` and two of the three slots — 46 KB of disc — had never been written by
anything, test included; `tests/test_save.py` now writes slot 3 (tracks 36–41), reads
slot 1 back to prove it was untouched, and reads slot 3 back to prove it holds its own
game. They belong to no AMSDOS file: this is the game's own disc, `tools/mkdsk.py`
checks at build time that no file reaches track 24, and a save that overwrote one
would be silent otherwise.

The header is checked **before** a single byte of the game is overwritten. An empty
slot is `&E5` from end to end — perfectly valid bytes, an invalid game — and without
the magic, *load* on an untouched slot would fill the world with rubbish and hang the
simulation. `tests/test_save.py` loads from an empty slot on purpose and asserts that
nothing moves. An empty slot now **says so** — `NOTHING IN SLOT 2`, not `DISC ERROR`;
`sv_hdr_ok` returns `&FF` and the controller returns anything else, so the two are
told apart at no cost.

**And a message stays on screen for two seconds.** It used to live until the next
`ml_hud`, sixteen frames away. A save takes two seconds of disc, so its message was
visible the whole time by accident; a rejected empty slot is decided in one seek and
the player saw a flash. `ui_msg` sets a counter that `ui_panel` decrements instead of
repainting — six HUD ticks, sixteen bytes of code.

The seed survives the generator in four bytes of bank 6 (`worldinfo`), written by
`GEN.BIN` before the game's code exists. Without them the running game has no idea
which seed built its world, because the generator is a separate loadable that is
overwritten by bank 2's data ([§13](#13-build-and-test)).

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

**ASSET-8 — a broken machine looks exactly like a working one.** There is one
sprite per machine type and no damaged variant, so when a machine breaks
([§6.10](#610-events-and-hazards)) the dome shows no sign of it; only the HUD's
alert line knows. The dirty list already redraws a single slot for 4,992 µs, so a
second variant would cost 132 bytes per machine (1,584 for all twelve) and
nothing in time. Until then, **breakage is audible in the economy and invisible
on the screen**, which is the wrong way round for a game about watching a colony.

**ASSET-9 — the engineer is a robot in the art and a human in the simulation.**
`assets/SPRITES.md` §7 lists four robot figures (carrier, driller, engineer,
constructor); [§6.1](#61-entities) has three robots plus a human engineer. The
renderer maps the human onto figure 7 and nothing is lost visually — the figure
is six pixels of cyan — but the names disagree and someone will trip over it.
Renaming the figure is free; renaming the *role* is not, because `tools/econ.py`
and `tools/pack.py` hard-code the list.

---

## 13. Build and test

```
assets/sprites.asm ─┬─ tools/pack.py ─> page2 bank1 bank6 bank7 .bin ─┐
                    └─ tools/mkoffsets.py ─> sprite_consts.asm        │
src/main.asm ─┬─ rasm ─> game.bin + game2.bin ──────────────────────┐ │
src/gen.asm  ─┼─ rasm ─> gen.bin                                    ├─┴─ iDSK ─> habitat.dsk
src/boot.asm ─┴─ rasm ─> boot.bin                                   │
                         HABITAT.BAS (three lines) ─────────────────┘
```

`tools/mkdsk.py` runs that whole chain and `tests/test_disc.py` boots the result
from BASIC. Eight files, because AMSDOS gives one load address per file and the
game lives in seven places at once — see [§13.1](#131-three-ways-a-loader-does-not-run).

| File | Goes to | Bytes | |
|---|---|---|---|
| `HABITAT.BAS` | — | 3 lines | `MEMORY &8FFF` · `LOAD"LOADER.BIN",&9000` · `CALL &9000` |
| `LOADER.BIN` | `&9000` | 533 | the loader, plus the 40-byte endgame it copies to `&3FC0` |
| `BANK6.BIN` | bank 6 | 16,384 | quadrants, figures, entity tables |
| `BANK7.BIN` | bank 7 | 16,384 | structures, plants, and the reserved holes |
| `TEXT.BIN` | bank 7, over the hole | 1,017 | every string the game prints ([§4.2](#42-the-eight-banks)) |
| `BANK1.BIN` | `&7000` | 4,096 | room icons above the distance matrix |
| `PAGE2.BIN` | bank 5, then `&8000` | 11,264 | bank 2's graphics and tables |
| `GAME2.BIN` | bank 5, then `PAGE2_CODE` | 5,515 | bank 2's code — the address comes from the symbol table, not from a constant in the build script, because it moved once and the script did not |
| `GEN.BIN` | `&8000` | 3,072 | the world generator: runs once, returns |
| `GAME.BIN` | `&0100` | 15,330 | the game (sizes as of milestone 45 — `ls build/`, not this table, is the authority) |

**Measured: 31 s from `ENTER` to the colony** — 13.5 s of that is the generator
([§5.9](#59-cost--measured)), the rest is 68 KB off the floppy. The border changes
colour at each file, which is the only progress indicator there can be while the
firmware still owns the screen.

| Tool | Path | Role |
|---|---|---|
| `rasm` | `~/rasm/rasm.exe` | assembler; handles banking directives and `align 256` |
| `iDSK` | `~/idsk/iDSK` | builds the `.dsk` image |
| `tools/mapsize.py` | — | per-file byte counts for bank 0 and bank 2's code, by assembling a copy of `main.asm` with a label before every `include`. `tools/mkdsk.py` says how many bytes are left; this says who took them, which is the half that tells you what to move |
| `tools/agents.py` | — | reads the colonists' own fields out of bank 6 while the game runs: what each one is doing, where, and how full their bars are. [§6.6](#66-needs)'s oscillation is invisible in stocks and in the HUD; it is obvious in one colonist's `dest` sampled every 25 frames. It steals the CPU **only in the vsync wait at the top of the loop**, where the stack is at its base and only `BC` is live — taken anywhere else, the scaffolding leaves a nail on the stack per sample and the colony ends up with 217 living |
| `cpcemu` | `~/cpcemu/cpc.py` | **headless** CPC 6128 — Z80 + gate array + CRTC + PPI + FDC + PSG, renders to a framebuffer, dumps PNG. **Extended for milestone 20**: `cpcemu_psg_reg` / `cpcemu_psg_addr` in `cpcheadless.c` expose the AY's registers, because sound is otherwise invisible to every check — the emulator ran with `audio.volume = 0` and nothing outside the chip could say whether a write arrived. Additive; the old `.so` is kept beside the new one |

The headless emulator is the most valuable thing in this list, because it makes the
tests in this document runnable rather than aspirational:

| Test | Method |
|---|---|
| Generator determinism | generate a seed twice from cold boot, diff bank 4 ([§5.11](#511-testing-determinism)) |
| Generator regression | golden bank-4 dumps per version, checked in |
| Map quality | render each golden seed to PNG, review by eye |
| Frame budget | instrument the ISR with a frame counter; assert no slot exceeds its budget |
| Blit correctness | render a known scene, compare against a golden PNG |
| Terrain pass | independent Python renderer of the autotiling (`assets/SPRITES.md` §3), compared byte for byte at seven cameras: a lake with a deep centre and an ore vein, both corners of the world — the far one reaching row 63 since milestone 56 — craters and foundations, a lake written into the last three rows, a ring of mountains written around the lake (two autotiled families that differ by 1, which the test world never had), and a camera offset that makes every row wrap the 2 KB ring; plus the cost per tile, which must stay where §2.2 says (`test_tiles.py`) |
| Object pass | independent Python renderer from the prose, compared byte-for-byte at five camera positions (`test_object.py`) |
| Scrolling | equivalence: scroll *k* steps and compare with a full draw at the destination (`test_scroll.py`) |
| HUD | content against a reference in five states — numbers wider than their field, zero capacities, `LOW POWER`, food, meteors — boundary against a marker, cost against a limit (`test_hud.py`) |
| Sound | every effect tick by tick against a Python reference, read back from the AY's own registers; priority; the shared PPI with the keyboard; cost (`test_sound.py`) |
| Dirty list | equivalence: the same mutation through the list and through a full redraw (`test_dirty.py`) — the mutation moves an **agent**, not the renderer's figure cache, because the cache is now rebuilt from the agents; the budget by how many items are left after each pass, against a model built from `dirty_cost` (milestone 54) |
| An emptied ring slot | every visible occupied slot at the five cameras of `test_object.py` — 20 of them — emptied through the list and compared with a full redraw, byte for byte; with `dhs_vacate`'s call taken out, 12 differ. The clip whole again after every one of the 200 vacancies, visible or not; with the restore aimed at a bare `ret`, 4 leave it narrowed. Two emptied in one tick: one comes out, one waits; with its 18,000 µs charge patched to 0, both come out. Cost against a 25 ms limit (`test_slot.py`) |
| Input | every action, keyboard and joystick, one edge per press (`test_input.py`) |
| Build mode | cursor, ghost-leaves-no-trace, the panel rows after a camera step (marked with `#AA` first, so a cell nobody rewrote is visible), validation, placement, payment, and the dome placed **empty** (`test_build.py`) |
| Rooms and the catalogue | `rm_build` for every room and size against a model of §6.5 (what the room accepts, what fits the size, the main machine first, the greenhouse by class), with the real `room_machines` and `machine_rules` and with 24 random ones; `BC`, `DE`, `HL` kept across it; every catalogue step from every position in both directions, and `rm_fix` for a dome and a structure; 11 rounds instead of 12 as the negative (milestone 60, `test_build.py`) |
| Where the ghost is drawn | `gh_box`, `gh_mark`, `gh_swap`, `gh_undo`, `gh_reset` and `gh_setpen` called directly, 1,200 operations over a screen of noise at four camera offsets (two wrap the ring inside a row) and changing clip windows, against a Python model of `ob_clip`, the screen address and the record: screen, log and bounding box byte for byte after every one; the log's limit to the byte (a mark goes in with 12 left, and with 11 touches nothing, not even the byte after the log); `gh_wrap` without `inc d` and the limit one byte higher as negatives (milestone 58, `test_ghost.py`) |
| Fitting | in the real binary, with the keys: a finished large Factory fitted slot by slot — the record, the payment per `fit_cost`, the screen equal to a full redraw; a slot emptied — `NO_MACH`, half back, the slot's bytes changed, the canary alive, the screen exact, worst round 40 ms — and with `dh_mach`'s jump to `dhv_rect` patched out, the machine stays on screen and the comparison fails; a replacement, with the build sound; a refusal with 3 Metal (nothing changes, the box red, the refusal's sound); `SPACE` into all eight, and `SPACE` with Metal for three — the first three, and only the refusal's sound; the choice standing on what each slot already holds, in the factory and in the greenhouse, with `fit_pick` patched one place off as its negative (milestone 55: no test caught that before); Quarters refusing to open. A greenhouse site fitted crop by crop before it finishes — nothing drawn onto the site — and MIXED, then the plants appearing when it is done (`test_fit.py`). The operator rule over sparse slots in `test_sim.py`, the FIT panel and an oxygen generator fitted to the site in `test_game.py` |
| Corridor routing | independent Python router compared on every pair of domes, then the *picture* compared at both kinds of bend (`test_route.py`) |
| The whole game | `src/main.asm` booted: start state, the economy moving inside the loop, a building placed and **finished**, and the HUD following it with no input; after 14,000 frames the screen equals a full redraw with **zero** wrong bytes, and ring slots must have emptied on the way, or the equality proved nothing (`test_game.py`) |
| Building without a freeze | a large Factory, a solar panel and a corridor placed and finished in the real binary: a **canary** byte far from the building must survive (a full redraw repaints it), the screen must match a full redraw of the same state — exactly, outside the canary, since milestone 42 — and the worst frame is measured on a clock that does not lose it at a seam. The large dome must appear in exactly eight frames, one row each, and the ghost must be back after it. The ghost is left over the finishing dome and then moved, once with the lift cut out as a negative control; the red large-dome ghost must fill the undo log **exactly**, 1,160 bytes, and with the limit one byte lower it loses its last mark (`test_reveal.py`); a corridor **with a bend** is compared against a full redraw in `test_route.py` |
| Corridors between placed domes | diagonal and bent routes between domes placed through the interface, every size: 0 bad tiles where the route crosses its own ends' footprints, a stone and a third dome still block, the old check patched back in fails. Seven built in all four diagonal directions, byte-exact against a full redraw, with B's door opposite the **last** run; the diagonal comes out **one row per frame**, as many rows as are in view, worst frame under 160 ms, and the ghost comes back after. Every frame of a reveal is sampled: what was already on screen must not vanish (13 bytes, against 96 with the terrain repainted). The cursor stepped onto rows still to come must leave no trace (22 bytes with `dt_ghost_rect` cut), a diagonal preview hidden again must leave no marks, and a strip one tile off for `/` must show. Six previews hidden, two of them climbing into a horizontal run (a mark left behind with `crw_h1`'s fix cut out), and the ghost log of six routes equal to the cursor's frame plus one mark per visible tile — including the worst there is, 21 tiles, 308 bytes (`test_link.py`, [§9.4](#94-corridor-routing), [§4.2](#42-the-eight-banks)) |
| The economy's rare branches | in the simulation harness, one balance cycle for each of eleven built cases — surplus, cap, equality, a covered deficit, the reserve's boundary from both sides, shed load charging and drawing, blackout, storm, wind 0 and 3 — and slot 15's first roll seeded into a flare, a fault, a storm and visitors; the whole economy and the domes against `tools/econ.py`. Negatives: the reserve cut, a flare offset changed (`test_sim.py`, [§6.5](#smaller-at-milestone-46)). And the needs pass with every colonist set to one of fifteen edge cases — each critical need alone and together, damage to death, recovery to its ceiling, morale at the floor, each room a need sends you to — over four revolutions: 36 hurt, 5 dead, 31 healed, all against `tools/entity.py`. Negative: the oxygen's bit of the damage cut, which the ordinary run never noticed ([§6.6](#smaller-at-milestone-53)) |
| Ships, streaks and milestones at their edges | in the simulation harness, slot 15 pinned, eleven built cases against `tools/econ.py` byte for byte (milestone 57): visitors from the roll with no pad, visitors with 5 Food and morale up to 255, colonists with room for two and with the cap already passed, all three streaks at 255, eight bots of role 4 and of role 5, Metal and Bioplastic without Spares, nine goods of ten, Habitat independent but not industrial and the other way round. Negative: Automation from 9 bots makes the Z80 differ (`test_sim.py`) |
| Movement at its edges | in the simulation harness, `ent_move_slice` called directly in twelve agent states against `tools/entity.py`, on the colony's graph plus structures (nodes 64–71), a pair that reaches nothing and a node alone, with a dome stripped of its edges and a stale adjacency entry after routing: one agent pinned in each of the rare branches, the rest drawn — arrivals into a full ring and into a structure, working agents leaving a dome and a structure, slices that wrap round 127; after every slice the fields, the masks, the dome table and the `wh_push`es the reference implies, and the rest of bank 6 untouched; the wrap taken out as the negative (milestone 59, `test_sim.py`). The starting colony's occupancy masks exactly where its colonists stand (`test_game.py`) |
| Meteor showers | in the simulation harness, the roll, a shower and the rebuild byte for byte against the reference, and a 120-impact shower with the wheel pinned to slot 15 round an L dome — eleven impacts in its edge column, and `MT_REACH` patched to 3 must disagree (`test_sim.py`). In the game binary: a shower on the landing pad — **exactly** the craters the reference predicts from the game's own world plane and no other tile; drawn through the dirty list with the canary alive and the picture equal to a full redraw; worst frame 60 ms; the pad a site with a Build job, the oxygen machine stopped, `METEOR SHOWER` on the HUD and the impact on the AY; then the pad rebuilt and the machine repaired. Negative: `wh_push` cut, the same craters are in the world and 155 bytes of screen are wrong. The roll's 16 trigger values checked exhaustively against every other event, and its rate over 200 sols (`test_meteor.py`, [§6.10](#610-events-and-hazards)) |
| Object index | each of the 200 tiles of the view drawn **on its own** (a one-tile clip over a black screen) at the five cameras of `test_object.py`, and every one equal to the same tile of the full draw — the only check that sees an object missing from the index, since the strip and the full draw both go through it. Negative: a box's right edge rounded down, 12 tiles lose a piece. And the empty pass under 4 ms, against 49 before (`test_index.py`, [§8.4](#84-object-pass-and-draw-order)) |
| Needs beat the board | the food colony of [§6.6](#66-needs) run for 9,000 frames, watching the *bars* rather than the corpses, plus the player's canteen getting an operator (`test_needs.py`) |
| Who stops first | the reserve rule on the reference implementation — one unit either side of the threshold, and a storm-length night with the reserve knocked out beside it — then the two-pump colony in the real binary: load shed, oxygen never zero, pumps really stopped, `LOW POWER` on the screen (`test_power.py`) |
| The map is a constraint | the pump refused on dry ground **with the reason on screen**, accepted at the shore and actually built; the mine likewise at a vein; and a dome and a solar panel accepted on the same dry ground, which is what separates "this rule" from "this patch of dirt" (`test_map.py`) |
| The disc | `RUN"HABITAT` from a cold BASIC prompt: the game arrives, the start state is there, the HUD is drawn, and the world is **generated** rather than loaded (`test_disc.py`) |
| Disc driver | the μPD765 without AMSDOS: reads the disc's own **catalogue** and compares it with the host's `.dsk` byte for byte, then writes three sectors, reads them back, and checks the neighbouring sector is untouched (`test_fdc.py`) |
| Save and load | freeze the wheel, photograph the state, `S`, run 12,000 frames until it has moved, `L`, and assert the economy, the world plane and the **picture** are back — plus a load from an empty slot that must be refused (`test_save.py`) |
| Palette | the only test that looks at **colour** rather than pen number: a share-per-pen pattern on screen, weighed against `palette_fw` and against each planet's four pens (`test_palette.py`) |
| The palette for drawing | the four `assets/palette*.gpl` read as Aseprite reads them: sixteen named colours in pen order, equal to `palette_fw` with that planet's row of `planet_pens`, the file names from `PLANETS` in `sprites.asm`, no stray `.gpl`, and the terrain table equal to `planet_pens`. Negatives: two colours swapped, pens 11 and 13 swapped on the desert and 7 and 10 on the barren moon (same colour — only the name catches it), a name dropped, a table value changed, the header in the wrong case, the ice file holding the desert, a palette named after the wrong planet (`test_gpl.py`, [§8.6](#86-palette)) |
| Structures stay visible | every masked outdoor structure in `sprites.bin` — fifteen, solar to ship — decoded with its mask, and no pixel on the edge of its shape may have the colour of the ground's base on any planet. Negatives: the ship with its outline erased loses 26 edge pixels on the barren moon (exactly what the pre-milestone-50 `sprites.bin` gives), and a ground painted the solar frame's grey swallows `solar_m` (`test_silhouette.py`, [§8.6](#86-palette)) |
| Game speed | the four speed keys against the simulation's own frame counter, and the HUD indicator read back off the screen (`test_speed.py`) |
| Playability of every seed | headless run of N seeds, assert water and ore within 30 tiles of centre — **which is now a playability claim and not a cosmetic one** ([§6.5](#65-economy)) |

That last one is the kind of test that is impossible on real hardware and trivial here.
It should be run over a few thousand seeds before release.

### 13.1 Three ways a loader does not run

The snapshot the tests boot from is a *scene*: banks in place, firmware gone, jump
to `&0100`. A disc gives none of that, and three separate things made the loader
fail **without a single visible error** — no message, no wrong picture, just a
machine that went somewhere else.

**The ROMs are on while the firmware is alive.** The lower ROM covers
`&0000–&3FFF` and the upper ROM `&C000–&FFFF`. *Writes* go to RAM underneath, so a
file loads there perfectly and the bytes are provably correct — and then the
processor executes ROM. The first loader sat at `&C000` (16 KB free, ideal) and
reset the machine in two seconds; the second sat at `&3E00` and wandered into the
operating system, which eventually asked for a cassette. Only `&4000–&A6FF` can
hold code, and above `&A700` is AMSDOS's workspace. So the loader lives at `&9000`,
its 2 KB AMSDOS buffer at `&9800`, and the generator at `&8000`.

**AMSDOS unhooks itself when BASIC runs a binary.** `RUN"FILE.BIN"` loads from the
disc and then restores the *cassette* vectors before jumping: measured, `&BC77`
holds a far call into ROM at the `Ready` prompt and a low jump into the cassette
manager inside the running program, and `KL FIND COMMAND` no longer finds `DISC`.
The first `CAS IN OPEN` of the loader printed `Press PLAY then any key`. A program
reached by `CALL` from BASIC keeps AMSDOS hooked — also measured — which is why
there is a three-line `HABITAT.BAS` and why the CPC has always done it this way.

**The first byte of a loadable must be an instruction.** `gen.asm` began with its
includes, and `gen_tables.asm` emits *tables*; `call &8000` ran the table, returned
without complaint, and left bank 4 empty. The world came out a flawless infinite
field of ground, which looks exactly like a world. `jp gen_entry` is now the first
thing in the file.

The fourth constraint is a collision rather than a surprise: bank 2's data
(`&8000–&ABFF`) and code (`&B440`) both land inside AMSDOS's workspace. They are
loaded into bank 5 first and copied down by an **endgame** — forty bytes copied to
`&3F80` and entered with both ROMs off, because the copy passes over the loader
itself and over BASIC's stack. It takes its two lengths in `BC` and `IX` rather
than reading them from memory that is about to disappear.

### 13.2 The loading screen

**For thirty-one seconds the player looked at BASIC.** `Ready`, `|disc`,
`run"habitat`, and a border that changed colour seven times. Then the colony
appeared *on top of that text*, which stayed visible until the first full redraw
covered it. Nothing was wrong in any test; it was found by taking screenshots of the
disc boot and looking at them.

Three changes, in three different places, because the thirty-one seconds belong to
three different programs:

- **The loader** (`boot.asm`, firmware alive) calls `SCR SET MODE 1` as its first
  instruction — which clears the screen — then writes `HABITAT`, a subtitle, and
  `LOADING` through `TXT OUTPUT`. Every `ld_file` prints one dot, so the row of dots
  *is* the file count. Mode 1 rather than Mode 0 for one reason: forty columns hold
  words and twenty do not. The border codes are kept; they cost nothing and they say
  which file is loading if the screen is ever wrong.
- **The generator** (`gen.asm`, firmware alive but no calls to it) draws a progress
  bar **straight into screen memory**. It is the only part of the boot that takes
  real time — 13.5 s, [§5.9](#59-cost--measured) — and the only one with something
  to count: `wg_plane` walks 128 rows, the bar is 64 bytes wide, so one byte per two
  rows. `wg_prog` is 30 bytes and preserves every register; `worldgen.asm` calls it
  once per row and defines an empty default, so `tests/gentest.asm`, which has no
  screen, is unaffected.
- **The game** clears the screen before it draws anything (`hw_clear`, 16 KB of
  `ldir`, 86 ms). That is what removes the loader's own screen — and, on the snapshot
  path, whatever the emulator left behind.

`tests/test_disc.py` checks all three from the running disc: the two top character
rows are **empty** at the four-second mark (that is where `Amstrad 128K Microcomputer`
was) while the title rows are not; the bar is sampled every 30 frames through the
whole generation and must start at zero, never go backwards, and reach all 64; and
`hw_clear` is run against a screen filled with `#AA`. Negative controls: without
`SCR SET MODE` the BASIC text is still there (292 bytes in the top two rows), and
without the per-row call the bar stays at zero for the whole 13.5 seconds.

**And it has sound.** The tune is the generator's own, clocked by its own tile loop,
in 420 of the 768 spare bytes it had — [§9.5](#95-sound) has the reasons for both the
second player and the wobbling tempo.

---

## 14. Delivery plan

| # | Milestone | Proves |
|---|---|---|
| 1 | Boot, firmware off, palette, Mode 0, `sprites.bin` loaded into banks | the memory map |
| 2 | Opaque and masked blit kernels; draw one dome from `nw` quadrants | [§2.2](#22-the-frame-budget)'s cost table is real |
| 3 | Terrain tiles + tile pass; draw a hand-made 20×10 map | the tile grid |
| 4 | World generator; `GENERATING` screen; determinism test green | [§5](#5-procedural-world-generation) |
| 5 | Camera: CRTC offset scroll + edge redraw + HUD raster split | the riskiest rendering claim ([§15](#15-open-risks)) |
| 6a | **Renderer**: object pass, camera with strip scrolling, dirty list, HUD | [§8.4](#84-object-pass-and-draw-order), [§8.5](#85-the-dirty-list), [§9.2](#92-hud) |
| 6b | **Build mode**: input, ghost, validation, place a dome, corridors | [§9.3](#93-build-flow), [§9.4](#94-corridor-routing) |
| 7 | Entities, node graph, routing matrices, **the wheel** | [§7](#7-the-batch-scheduler) |
| 8 | Needs, jobs, production; the colony runs itself | the game exists |
| 9 | Events, ships, trade, milestones | the game is a game |
| 10 | Save/load, audio, four planets, tuning | shippable |

Milestones 1–5 are the ones that can fail for hardware reasons. Do them first, in that
order, and do not build gameplay on top of a scroll that has not been proven on a real
6128.

**Milestone 6 split in two once it was attempted.** It assumed a renderer that
did not exist: there is no ghost without an object pass, no validation without
occupancy on screen, and no build menu without a HUD. 6a is that renderer; 6b is
the half the player touches. **Both are done.** Milestones 7–9 were built before
either, out of order, because they needed no pixels.

**The wiring is done.** It was never a milestone in this table and it was what
stood between a colony that can be built and a colony that runs: `src/main.asm` is
one binary with one loop, `game_new` lays out the start state of
[§10.1](#101-start-state), a finished `J_BUILD` job turns a site `DS_ACTIVE`, and
the wheel pushes every visible change into the dirty list through a hook the
renderer installs ([§8.5](#85-the-dirty-list)). Two things only showed up once both
halves were assembled together: the two halves disagreed about which bank the
window holds ([§7.4](#74-one-convention-per-half-and-they-disagreed)), and a fresh
construction site had no graph edge, so nobody could ever walk to it.

**And it boots from a disc, and writes back to it.** `tools/mkdsk.py` builds
`build/habitat.dsk`; `RUN"HABITAT` on a 6128 generates a world and drops the player
into the colony ([§13](#13-build-and-test)), and `S` / `L` save and load a game
through the machine's own floppy controller ([§11](#11-save-and-load)). That is
milestone 10's delivery and save/load halves. **The four planets are built**
([§5.7](#57-planets)), **and so is the sound** ([§9.5](#95-sound)): eight effects on
the AY, checked against the chip's own registers. What is left of milestone 10 is
tuning. **Music is written too** — for the one place it belongs, the thirteen seconds
of world generation ([§9.5](#95-sound)); in-game music is a decision against, not a
gap.

---

## 15. Open risks

| Risk | Severity | Mitigation |
|---|---|---|
| ~~CRTC offset scrolling with a two-page raster split~~ | ~~High~~ | **Resolved at milestone 5, and split in two.** Offset scrolling works to the pixel ([§8.2](#82-camera)). The mid-frame page change does **not** — the CRTC latches the start address once per frame — so the HUD moved into the play page and bank 2 went flat ([§8.1](#81-screen-layout), [§4.3](#43-bank-2-flat-again)). |
| ~~HUD re-render on every scroll step, ≈ 0.4 frames, estimated not measured~~ | ~~Medium~~ | **Measured at 2.55 frames**, six times the estimate, and then cut ([§8.1](#81-screen-layout)). The cell cache of [§9.2](#92-hud) took an ordinary tick to 1.15, and milestone 52's smaller HUD to **0.65**; a camera step, which moves every cell, still pays **1.75** (2.30 before milestone 52, 2.20 before the font moved to bank 7 at milestone 33). The escape hatch for that one — *move* the HUD block inside the ring with `lddr`, ≈ 0.85 frames, instead of re-rendering it — is still untaken. |
| Mid-frame writes land where aimed, but only on the emulator's CRTC | Low | The border control in `tests/test_camera.py` hits line 160 exactly. Real hardware still wants a check, but nothing now depends on a mid-frame *address* write. |
| Memory map slack: 1,536 contiguous in bank 2, **288 in bank 6**, 440 in bank 7 | Medium | Bank 6 is the tight one now and the entity tables grew into it. The next thing that needs space there moves `plants` out of bank 7 first, or takes the `s` room-icon set (864 B) as [§4.2](#42-the-eight-banks) names. |
| Routing rebuild latency of ≈ 5 s after a network change | Low | Stale routes are inefficient, never invalid ([§6.4](#64-routing)). If it grates: cache paths for the 16 busiest pairs and rebuild those first. |
| **13.5 s** world generation feels long even on a cassette-era machine, and it is 3.9× the original estimate | Medium | New game only — loads read the plane off disc ([§5.10](#510-player-modification)). **Both halves are built**: the progress bar of [§13.2](#132-the-loading-screen) — title, a dot per file, a bar that moves once per two world rows — and, since milestone 24, **music** ([§9.5](#95-sound)), played by the generator's own player and clocked by its own tile loop, because interrupts are off down there. The identified 2× win ([§5.9](#59-cost--measured)) is held in reserve. |
| A seed produces a technically valid but miserable map | Low | Feature anchors guarantee the necessities; the headless seed sweep ([§13](#13-build-and-test)) finds the rest. |
| **Airlock: dome or structure?** The asset set now has both an `icon_airlock` room type and a standalone `airlock` structure sprite; the node graph in [§6.2](#62-the-node-graph) only models the dome | Medium | Decide before the node graph is written — it changes what an *outdoor edge* connects to. Recommendation and the comparison are in [§6.2](#62-the-node-graph). Cheap either way: the unused half is 400–512 bytes. |
| A full-colony routing rebuild is ~27 s of stale routes at the current budget | Medium | Only at 128 nodes; 48 nodes is 3.8 s ([§6.4](#64-routing)). Two levers, both untaken: raise the per-frame budget while the camera is still, or tighten `rt_node` — its per-node setup re-reads the same three bytes and is worth about 2×. |
| ~~Slots 11, 12, 13 and 15 of the wheel are unwritten~~ | ~~Medium~~ | **Written and measured.** Four of six budgets were low, by 1.5× to 5× ([§7.2](#72-the-wheel)). The worst frame is a third of a frame, so the design holds. Remaining passes should be budgeted pessimistically. |
| A heavy sim slot and a scroll column in the same frame come to ~19 ms of 20 | Medium | The dirty list is a budget, so the edge redraw spreads over two frames. Costs nothing but a one-frame lag on the newly exposed column; needs watching once the HUD re-render ([§8.1](#81-screen-layout)) is measured too. |
| ~~Needs, health and death are not written~~ | ~~High~~ | **Written.** Colonists eat, drink, sleep, get treated, die, and grieve; the only loss condition is live ([§6.6](#66-needs)). |
| ~~Nothing produces food~~ | ~~High~~ | **Greenhouses grow.** Plants sit in the machine slots, `plant_class` decides the crop, and one biologist tends the whole dome ([§6.5](#65-economy)). |
| ~~Ships, trade and milestones are unbuilt~~ | ~~Medium~~ | **Built**, except Automation, which waits on bot-eligible jobs ([§10.2](#102-milestones)). |
| ~~A heavy sim frame plus a scroll column comes to 19.9 ms of 20~~ | High | **Worse than that, and now measured.** A scroll step is 3.0–8.8 frames of world plus 2.30 of HUD (1.75 since milestone 52) ([§8.2](#82-camera)), so it was never going to fit in one frame and does not need to: the dirty list is a budget and the strip fills over several frames. What this costs is **latency, not frame rate** — about a quarter of a second per tile through a dense base. The flow-balance slot still wants the fix described below. |
| ~~The flow-balance wheel slot re-scans 64 structures every revolution~~ | ~~Medium~~ | **Resolved, and not for speed.** 7,887 µs for numbers that change slowly — but the reason it moved was [§6.5](#65-economy)'s clock: a battery that charges 750 times a sol is not a battery. The scan, the battery and the pumps now run once per 64 revolutions (`FLOW_DIV`), the living are still counted every revolution, and a finished building kicks the balance so the panel the player just paid for shows up at once. |
| ~~Nothing the player does exists: no build mode, no input, no HUD, nothing drawn since milestone 5~~ | ~~High~~ | **Resolved.** The colony is drawn, the camera scrolls, the dirty list keeps it honest, the HUD reports — and the player now moves a cursor, opens a menu, places a dome and routes a corridor between two of them ([§9.1](#91-controls), [§9.3](#93-build-flow), [§9.4](#94-corridor-routing), [§6.9](#69-construction)). |
| ~~The two halves have never been assembled into one binary~~ | ~~Medium~~ | **Assembled, and it did not fit: 20,571 bytes wanted 16,128.** Resolved by moving the generator out, cutting `MAX_NODES` to 96 and putting code in bank 2 ([§4.2](#42-the-eight-banks)). It also turned up duplicate constants in three files and, worse, [§7.4](#74-one-convention-per-half-and-they-disagreed)'s paging disagreement. |
| **Memory is the binding constraint from here on** | High | **2,603 bytes free in bank 0, 117 in bank 2's code area, 28 in bank 6, 952 in bank 7 (7 of the `text` block)** — after milestone 60 shrank the rooms, after milestone 59 shrank the movement, after milestone 58 shrank the ghost, after milestone 57 shrank the ships and milestones, after milestone 56 shrank the tile pass, after milestone 55 shrank the fitting, after milestone 54 shrank the dirty list, after milestone 53 shrank the needs pass, after milestone 52 shrank the HUD, after milestone 47 shrank the job board, after milestone 46 shrank the economy, after milestone 45 fitted domes slot by slot, after milestone 44 shrank the interface, after milestone 43 shrank the object pass by a fifth, after milestone 42 redrew an emptied ring slot as the full pass would, after milestone 41 cut the ghost's log to its worst case and moved the index's build up, after milestone 39 indexed the object pass, after milestone 38 brought the meteors, after milestone 37 drew diagonal corridors a row at a time, after milestone 36 joined them to the colony, after milestone 35 put the milestone-2 blit kernels, which only their own tests still call, behind `HAS_QUADS`, after milestone 34 spent 279 and 118 on building without a freeze, and after milestone 33, which found two reservations nobody had ever read (`ui_cursor` 256 in bank 2, `audio` 2,048 in bank 7), moved the font into the second, and let `newgame.asm` and `fdc.asm` follow `save.asm` into bank 2 ([§4.3](#43-bank-2-flat-again)). Bank 0's ceiling is `&3EC0`, where the tests' own scaffolding runs, and the loader's two scratch areas are checks now too. Bank 6's *156* was wrong by 128 — `tools/pack.py` has been printing **28** all along, which is what happens to a figure copied into a document instead of read out of the build. The ledger: 26–29 spent 671; 30 handed back 560; 31 spent 152 and took 192 back from the test floor; 32 spent 144; 33 handed back 957 and cost 29 in paging; 34 spent 279 in bank 0 (the ghost's swap and bounding box, `view_rect`, the `DK_BUILT` handler) and put its cold half — the two post-placement redraws — in bank 2 for 118; 35 spent 200 in bank 0 (the row-by-row reveal, the one-pass mirror, the ghost's rectangles) and 82 in bank 2, and took 268 back from `blit_quads` and `flip_span`, whose only callers left are `tests/blittest.asm` and `tests/packtest.asm`; 36 spent 23 in bank 0 (the door scan looking one record ahead) and 59 in bank 2 (`crk_in`, and B's door in `cr_redraw`); 37 spent 113 in bank 0 (the `DK_CROW` handler, `dt_ghost_rect`, `view_add`, the budget's carry) and 183 in bank 2 (pushing the rows, a walk that visits each tile once); 38 spent 64 in bank 0 (the shared Galois step, `ec_break_d`, the Build-job poster moved out of `build.asm`, the boom and the HUD line, two bytes for `ship_crew`'s exits) and 431 in bank 2 (`meteor.asm`, 48 of it the scan that keeps an impact at 3 ms, less the poster `build.asm` gave up), and moved the loader's code scratch to `&6800` ([§4.3](#43-bank-2-flat-again)); 39 spent 538 in bank 0 on the object index — the walk, `oi_build` and its measuring hooks, the class bits — and took 1 back in bank 2 ([§8.4](#84-object-pass-and-draw-order)), the most any milestone has spent on one thing, for 47 ms off every scroll step and every redraw of a strip. Bank 2's 23 went to 15 at milestone 40, for the climbing turn. **41 spent the last soft reserve**: the ghost's log went from 1,600 to the 1,160 its worst ghost needs — computed, and checked to fit whole ([§4.2](#42-the-eight-banks)) — and the 440 bytes took the object index's build up from bank 0 (`src/objindex.asm`, 347 bytes; the structure sort stayed below, because the whole file did not fit): bank 0 88 → **428**, bank 2's code area 15 → **108**. 42 spent 220 of it in bank 0: `dhs_vacate` (the terrain under an emptied slot and the object pass over it, both clipped to its 2×8, and its own charge to the budget) and `tile_src`, split out of `tile_one` so the two share the terrain lookup — 428 → 208. **43 took 737 back**, all of it by writing the same thing fewer times: `object.asm` 3,130 → 2,490, and its clip's register interface 76 out of `dirty.asm` and 21 out of `ghost.asm` — 208 → 945 ([§8.4](#84-object-pass-and-draw-order)). **44 took 283 more out of `ui.asm`** (2,224 → 1,941), by the same means: one routine for "left/right, cyclic" where the save slot and the build menu each had their own, one for "change state around the ghost", one for a ghost mark at a world tile (the route's tiles and the bad tiles of a footprint had one each), and coordinate pairs read and written as words — 945 → **1,228** ([§9.3](#93-build-flow)). It would have been 295: a table-driven `ui_sig` was 12 bytes smaller and 139 µs slower on every cursor step, and went back. **45 spent 750 in bank 0 on the fitting**: `src/fit.asm` 757, `ui.asm` 34 for its hooks and `ui_ud`, `dirty.asm` 40 for `dhv_rect`, the emptied machine slot and the clip's restore, less `rooms.asm`'s `rm_fitout` (75) and 6 out of `econ.asm`; bank 2's code area got 6 back from `bd_commit`'s call — 1,228 → **478**, 108 → **114**. The fitting's names and keys took 187 of the text block's 194. **46 took 422 back out of `econ.asm`** (1,549 → 1,097, 58 of it moved to the shared `stock.asm`, which let `fit.asm` drop its own copy of the capped add: 23 more), by the same means as 43 and 44 ([§6.5](#smaller-at-milestone-46)) — 478 → **900**. **47 took 272 out of `jobs.asm`** (1,089 → 817), and made slot 13 faster on the way ([§6.7](#smaller-at-milestone-47)) — 900 → **1,172**. **52 took 390 out of `hud.asm`** (1,032 → 642) and 9 out of `ui.asm`, which now asks the HUD for a column instead of stepping to it, and the HUD redraw got 23–44% faster ([§9.2](#smaller-at-milestone-52)) — 1,172 → **1,571**. **53 took 187 out of `needs.asm`** (963 → 776), and the room index, the worst frame of the wheel, went from 34 % of a frame to 23 % ([§6.6](#smaller-at-milestone-53)) — 1,571 → **1,758**. **54 took 173 out of `dirty.asm`** (1,126 → 953), most of it a second copy of the view clipping in the terrain handler ([§8.5](#smaller-at-milestone-54)) — 1,758 → **1,931**. **55 took 92 out of `fit.asm`** (734 → 642) and gave 1 to `rooms.asm`, the empty choice in front of `rm_buf` ([§9.3](#smaller-at-milestone-55)) — 1,931 → **2,022**. **56 took 112 out of `tiles.asm`** (633 → 521), and a full terrain pass went from 9.7 frames to 8.9 ([§8.3](#smaller-and-faster-at-milestone-56)) — 2,022 → **2,134**. **57 took 197 out of `ship.asm`** (574 → 377), a third of the file, most of it a loop that rebuilt two constant masks every sol and a new colonist written field by field ([§10.2](#smaller-at-milestone-57)) — 2,134 → **2,331**. **58 took 56 out of `ghost.asm`** (484 → 428), and every ghost operation got faster on the way — the size check became a carry, and the screen address is taken from what the bounding box has just loaded ([§9.3](#smaller-and-faster-at-milestone-58)) — 2,331 → **2,387**. **59 took 124 out of `entity.asm`** (449 → 325) and 3 out of `newgame.asm` in bank 2: the agent's id stays in a register instead of being read back before every field, and the movement slot of the wheel went from 1,298 µs to 899 ([§6.3](#smaller-and-faster-at-milestone-59)) — 2,387 → **2,511**, bank 2's code area 114 → **117**. **60 took 92 out of `rooms.asm`** (372 → 280): the main machine is moved to the front of the list after the scan instead of being looked for before it, and every routine got faster ([§6.5](#smaller-and-faster-at-milestone-60)) — 2,511 → **2,603**. There is no slack left in the log; the next room in bank 2 has to come from code. `tools/mapsize.py` says *who* is spending bank 0. The reserves that remain, in order: the rest of bank 7 (952, data only), the tests' 320-byte floor once the probes take their address from `ZZ_BANK0_END`, the 864-byte `s` room-icon set, and the same treatment for the largest files no milestone has yet read for size: `view.asm` (356), `graph.asm` (314), `input.asm` (292). Bank 2's code area at 117 and bank 6 at 28 are the tight ones. |
| ~~Nothing finishes what the player starts~~ | ~~High~~ | **Built.** A Build job is picked up, the agent routes to the site, works it 32 points a visit, and at 255 the building turns `DS_ACTIVE` and is drawn ([§6.9](#69-construction)). `tests/test_game.py` walks the whole chain: place a solar panel with 30 Metal, and about six seconds later the HUD says `ALL SYSTEMS OK` with no key pressed in between. |
| ~~A completed building stalls the game for 0.8 s~~ | ~~Medium~~ | **Resolved at milestone 34 — and it was 360–920 ms, not 0.8 s.** The site is already on screen from placement; what completion changes is the room icon and the machines, so the Build job pushes one dirty record (`DK_BUILT`) and the handler draws those two things — a structure, nothing at all ([§6.9](#69-construction)). The completion frame of a large Factory is **120 ms** (100 at milestone 34), 60 of them lifting the ghost the player left on it; a solar panel's is an ordinary 40 ms HUD tick. The freeze did not go away entirely, though — it was always at **placement** too, and that is the next row. |
| ~~Placing a large dome still freezes the game for 0.86 s~~ | ~~Medium~~ | **Resolved at milestone 35 with the eight-chunk reveal of [§6.9](#69-construction), at placement.** A dome goes into the dirty list one tile row at a time and each row draws only that dome; the ghost waits for the last row. Worst frame of a large Factory's placement: 998 → 859 → **140 ms**; solar panel 439 → 220 → **120**; straight corridor 260 → **120**. The levers this row named were all taken: the reveal, a one-pass mirror (`blt_mask_flip`: the whole large site 450 → 351 ms, a full redraw of the view 839 → 679), and marks without clips on a log of rectangles (red ghost 263 → 57 ms). |
| ~~The ghost of a large dome on bad ground overflows its undo log~~ | ~~Low~~ | **Resolved at milestone 35.** The log holds rectangles now, not lines ([§9.3](#93-build-flow)): the same ghost is 1,160 bytes instead of 2,412, and all eight rows of marks are drawn. |
| ~~No corridor with a diagonal run can be built between placed domes~~ | ~~High~~ | **Resolved at milestone 36, and it was both ends, not one.** Measured over 72 geometries: every route with a diagonal had bad tiles and **every** bad tile was in the footprint of one of its two domes — the start's corner (two tiles for a large dome), and for a pure diagonal the destination's corner too, up to 6 of 10. `cr_cb_chk` now lets the corridor cross the footprints of its own two ends and nothing else ([§9.4](#94-corridor-routing)); all 56 routes the planner finds among those geometries pass. Building them showed a second fault the check had been hiding: a bent corridor's destination got its door opposite the **diagonal**, at a ring point nothing reaches, in the Z80 and in the Python reference alike — it is visible in the old `tests/golden/route_*.png`. Fixed in both. A diagonal corridor's placement cost 160–220 ms against a straight one's 120, because its redraw box was a square; since milestone 37 it appears a row per frame and the worst frame is 80–100 ([§6.9](#69-construction)). |
| ~~A diagonal corridor preview leaves marks behind the cursor~~ | ~~Medium~~ | **Found and resolved at milestone 37, by looking at the row-by-row reveal.** The marks of the route still under the press stayed on the ground until a row painted over them. `cr_walk` visited the tile two consecutive diagonal pieces share twice, the ghost marked it twice, and the forward undo wrote the second entry's "background" — the first mark — last ([§9.3](#93-build-flow)). Every diagonal preview did it, built or not: 48–56 bytes left behind each time the cursor moved, hidden only when a corridor was built and its whole bounding box repainted. The walk now visits each tile once; `tests/test_link.py` hides four previews and compares with a full redraw. **Not quite: milestone 40** found the climbing turn into a horizontal run still marking its first tile twice — none of the four previews climbed into one ([§9.3](#93-build-flow)). The test hides six now. |
| ~~The simulation still pushes nothing into the dirty list~~ | ~~High~~ | **Wired for ring slots**, which is what moves: `ent_claim` and `ent_release` push a `DK_SLOT`, and the figure cache is rebuilt once per burst rather than once per slot ([§8.5](#85-the-dirty-list)). Machines breaking, plants growing and room changes still push nothing. |
| **A near-diagonal pair of domes cannot be connected** | Low | The turn in [§9.4](#94-corridor-routing) spends `\|S − T\|` tiles, so when the two axes differ by less than the destination's radius there is no route and the panel says so. The band is 2–4 tiles wide and the player can step out of it by moving the dome. Closing it needs a corner sprite the art does not have. |
| **The population cap has a two-digit field** | Low | `POP 34/48` gives the cap two digits, and the cap is 4 + 48 per Control room, at most 128 (`rooms_rebuild`): with two it is 100 and the HUD shows ` 0`, from three on 128 shows as `28`. The field shows the last digits of anything wider, as every number in the HUD does; the alive count has the same field but rarely gets there. A third digit costs a column in row 2, which has none spare ([§9.2](#92-hud)) — the alert line would go to eighteen. Found at milestone 52, not fixed. |
| **The rest of the dirty-list call sites** | Low | A machine breaking, a machine repaired and a plant growing push nothing — **and would change no pixels if they did**: there is no damaged-machine variant ([ASSET-8](#12-asset-gaps)) and a plant's sprite is chosen by class, not by stage. Ring slots were the only change the picture can show, and they are wired. A colonist who dies releases a slot, so that path is covered; one who arrives by ship gets no ring slot until they move. Wire the rest when the art gives them something to draw. |
| ~~The dirty redraw does not hide the ghost~~ | ~~Low~~ | **Resolved at milestone 34, without the bracket and without its cost.** Every dome-shaped dirty item compares the dome's frame with the bounding box of the ghost's undo log (kept by `gh_rect` since milestone 35) and, only on overlap, **swaps** screen and log before drawing — and once more at the end of the tick ([§9.3](#93-build-flow)). The cursor over open ground costs nothing; over a busy dome, two swaps of its log. The old binary fails `tests/test_reveal.py` on exactly this: 222 wrong bytes in 25 tiles after the ghost leaves a dome whose ring slots changed under it. |
| ~~A vacated ring slot leaves 2–7 wrong bytes~~ | ~~Medium~~ | **Resolved at milestone 42 — and the diagnosis here was wrong.** It was not clipping. A figure's 2×8 is opaque with the ring baked in, so a colonist *arriving* is exact; the *empty* variant is the ring over black, while the full pass draws the ring over terrain and shows it wherever the ring is transparent. The experiment that seemed to clear the art — "draw the whole dome clipped to the slot" — drew it over the empty variant's black, so of course it gave the same wrong pixels. Measured over the test colony: 12 of the 20 visible occupied slots went wrong when emptied, by up to 8 bytes. `dh_slot` now calls `dhs_vacate` for an empty slot: terrain under the 2×8, then the object pass, both clipped to it — the full pass by construction. It costs 18.0 ms on average and 20.9 at worst, and charges itself 18,000 µs in the dirty list so it has its frame to itself ([§8.5](#85-the-dirty-list)). `tests/test_slot.py` empties every one of the 20 and compares each with a full redraw byte for byte; with the call taken out, 12 differ. **Every shape tolerance went with it:** `tests/test_game.py` now requires zero wrong bytes after 14,000 frames *and* that ring slots actually emptied on the way (two do), and `tests/test_reveal.py`, `test_link.py` and `test_meteor.py` compare exactly outside their canary. |
| **The base is invisible on its own foundation** | Medium | The foundation tile, the dome rings and the corridors are all the same grey. Outside the base everything reads; inside it, the colony disappears into the slab. Found by looking at the first running build, not by any check. It is a palette question for [§8.6](#86-palette) — one pen, differently chosen. |
| **A full redraw at the west edge of the world draws the wrong rows** | Medium | Found at milestone 56, older than it. The camera is never clamped to the world: the cursor wraps and is always on a tile from −64 to 63, and `ui_follow` keeps one tile of margin, so with the cursor on the westmost column the camera stands at x = −65. `tile_addr` for −65 gives an address one byte before the row, and the row walk steps through it in 16 bits, so the first tile *inside* the world is read from the next page: two rows down for an even row, one for an odd one. A **full** redraw there — after a load, say — draws every tile of the view from the wrong row, while a scroll strip or a dirty rectangle, which starts inside the world, draws them right. The test world hides it for eight columns, which happen to be the same ground on every row. The east edge (x = 64) and the rows −65 and 64 read bytes outside bank 4, and show them. Milestone 56 kept every one of those bytes as it was, so that its own check could be exact. Proposed fix: clamp the camera to the world (x −64…44, y −64…54), which needs a decision on the cursor's margin at the edge. |
| **Scrolling is 6 to 15 tiles per second through a built-up base** | Medium | 0.6–1.0 frames per tile in open ground, 1.6–5.0 in the base (5.4 before milestone 43; 3.0–3.4 and 4.0–7.8 before milestone 39's object index; 8.8 before milestone 35 mirrored dome quadrants in one pass instead of through a buffer), plus 2.30 for the HUD — which is now the larger half of a step in open ground. Two levers left: move the HUD block instead of redrawing it ([§8.1](#81-screen-layout)), and blit tile pairs ([§8.3](#83-the-tile-pass)). ~~Index which objects overlap which strip instead of testing all 224 records~~ — taken at milestone 39 ([§8.4](#84-object-pass-and-draw-order)). |
| **A broken machine is invisible on screen** ([ASSET-8](#12-asset-gaps)) | Medium | One sprite per machine, no damaged variant. The economy knows, the alert line knows, the picture does not — wrong way round for a game about watching a colony. 132 bytes per machine would fix it. |
| Intruders are unbuilt ~~— and meteors~~ | Medium | **Meteors came at milestone 38** ([§6.10](#610-events-and-hazards)): they waited for the world plane and the dirty list, and use both. Intruders still need edge spawning and combat, which is not a simulation problem either. |
| A new game says `NO OXYGEN` for its first 10–20 seconds | Low | Found while testing the meteor alert, not fixed: `ng_stock` sets `EC_O2OK` to 1, but slot 12 recomputes it every revolution as production ≥ use, and production is only published by the flow cycle, once in 64 revolutions. Until then it is 0 and the HUD's second-highest alert stands over a colony that is fine. The klaxon is spared by `ml_warm`; the line is not. `tests/test_meteor.py` waits for the first publication before it starts. |
| A struck structure looks untouched | Low | A meteor knocks a structure back to a site, but the renderer only draws a *dome's* site differently ([§6.9](#69-construction)) — a structure under construction looks finished, the pad included. Consistent with how a new structure looks while it is being built; the player learns of the hit from the HUD, the noise and the builders walking out. |
| Ships, trade and milestones are unbuilt — [§6.11](#611-ships-and-arrivals) and [§10.2](#102-milestones) | Medium | The colony sustains itself but cannot grow: no new colonists arrive and nothing can be traded for. This is what makes it a sandbox rather than a game. |
| The balance numbers in [§6.5](#65-economy) are first guesses and three of them were unlivable | Medium | Corrected against the first working colony ([§6.6](#66-needs)). Expect the same of the rest: they cannot be checked by reading, only by running the loop and looking at who is where. |
| ~~A new dome has no room and no machines, and nothing can give it either~~ | ~~High~~ | **Built, and it took three bugs with it.** The room is the menu's second axis ([§9.3](#93-build-flow)), the dome fills its own slots from `room_machines` and `machine_rules` ([§6.5](#65-economy)), and a greenhouse comes up full of plants. On the way: a construction site linked itself to *itself* and no dome the player placed had ever been finished ([§6.9](#69-construction)); an agent that found its destination unreachable kept the job ([§6.3](#63-movement)); and the loader's endgame was holding 512 bytes for forty ([§4.2](#42-the-eight-banks)). |
| ~~A colony of four cannot staff the food chain~~ | ~~Medium~~ | **They could. They were dying on the way to the canteen.** [§6.6](#66-needs)'s "their own needs outrank the board" dropped the job by writing `NO_TASK`, which is how the tables spell *idle*, so the assignment pass handed the work straight back and the colonist oscillated between machine and canteen until it died with Food in store. Going to eat is now a task the board does not touch (`T_NEED`), and the same colony — greenhouse, lab, canteen, four people — runs **eight sols with no deaths**, Food bottoming at 12 on sol 6 and climbing back to 27. `tests/test_needs.py` watches the bars, and its negative control on the old binary is bars pinned at zero for 1,100 frames. |
| ~~One food chain feeds four, not twelve~~ | ~~Medium~~ | **It feeds twelve, once three things stopped fighting it** ([§6.5](#65-economy), [§6.7](#67-jobs)): one biologist per greenhouse instead of one per pot, `mach_vitromeat` at 2 per run instead of matching the canteen exactly, and `Operate` priorities per room instead of a tie broken by a distance that never changes. Measured: the twelve-person colony that used to die on sol 5 now runs eight sols with nobody dead. It has **no margin** — the store still touches zero — so the remaining work is a second chain, and the HUD now says `LOW ON FOOD` while there is still time to build one. |
| ~~Water is the next thing to run out~~ | ~~Medium~~ | **Measured, and no rate needed touching.** This row asked for one thing — *measure a two-extractor colony before changing any number* — and the answer is flat: with one pump the same food colony goes **83 → 0 by sol 4** and then hovers between 0 and 6, with the oxygen generator running dry alongside it; with a second pump it goes **85 → 288 and keeps climbing**. Demand is 4 pots + `mach_vitromeat` 2 + `mach_oxygen` 1 = 7 a cycle against one large pump's 5, and the second pump turns a 2-a-cycle deficit into a 3-a-cycle surplus. The lever was already in the player's hands; the HUD's `LOW ON WATER` is how they learn to reach for it. What the second pump *costs* is the next row. |
| ~~A second pump buys water with oxygen, after dark~~ | ~~Medium~~ | **Resolved at milestone 32, and the ordering was already written down.** [§6.5](#65-economy)'s failure column said *machines stop, then oxygen stops* and `power_ok` was one flag, so the blackout that stopped the pumps stopped life support in the same revolution — 13 of 80 samples dark, oxygen production 20 → 0, the worst bar at 208. There are three levels now (`P_ALL` / `P_ESS` / `P_NONE`) and the battery lends to the machines only while eight cycles of life support stay behind it. Same colony after: **0 of 80 dark, oxygen never leaves 20, the worst bar 251**, at the honest price of pumps that stop at dusk — water climbs 63 → 147 over the window instead of 63 → 153. The HUD says `LOW POWER` while the load is shed, and a shed sol is not an all-green sol. |
| ~~The map is scenery: the lake and the ore vein mean nothing~~ | ~~Medium~~ | **Resolved at milestone 31.** `extractor (on water)` and `mine (on ore)` had been in [§6.5](#65-economy)'s chain table from the first draft and nothing read them: a pump built in the middle of the desert pumped. Now the footprint must sit within two tiles of the material — measured, not chosen: the mine is impossible at one tile, because rock always rings a mountain — and the panel names what is missing. `tests/test_map.py` holds it, negative control included: with the rule stubbed out, the two "says no" checks fail and everything else still passes. |
| ~~A machine cannot be chosen, only its room~~ | ~~Medium~~ | **Resolved at milestone 45, as in Planetbase.** A dome is built empty and fitted slot by slot from what its room allows (`FIT`, `src/fit.asm`), each machine paid for separately and half refunded when taken out ([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)). The operator rule had to change with it — it counted slots, and a lone machine in slot 3 would have needed four people. A built dome still cannot change its *room*. |
| ~~The colony can spend its starting metal and never make more~~ | ~~High~~ | **Resolved and measured at milestone 27.** Two changes: the start state carries **60 Ore, 75 Metal, 45 Bioplastic**, and only pressurised structures cost Bioplastic ([§9.3](#93-build-flow)) — the old catalogue priced everything in both, so the colony's 30 Bioplastic ran out four buildings in and the only thing that makes more is behind two domes that cost it. A panel, an extractor and a small Factory now cost 57 Metal of the 75, and `tools/balance.py` measures the chain running: **60 Ore → 30 Metal by sol 4, 18 → 48**, which buys the 30-Metal mine that keeps the Factory fed ([§10.1](#101-start-state)). The opening is no longer the whole game's budget. |
| Balance | ~~Certain~~ Medium | Every number in [§6.5](#65-economy) was a first guess; the ones on the path a player actually walks are now **measured** rather than guessed, by `tools/balance.py` — which runs the real binary at ×4 for eight sols and prints the curve — and held by `tests/test_balance.py`. What measurement turned up was not mis-tuned numbers but three structural faults: the economy had no clock, power counted consumption instead of demand, and the start colony's quarters were a second oxygen generator ([§10.1](#101-start-state)). The rates past the first two buildings — the whole machine chain — are still guesses, and stay guesses until a dome can be given a room. |

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
| `MAX_DOMES` / `MAX_STRUCTS` | 64 / 32 | |
| `MAX_CORRIDORS` | 96 | |
| `MAX_NODES` | 96 | 64 domes + 32 structures (the pad and build sites are structures) |
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
