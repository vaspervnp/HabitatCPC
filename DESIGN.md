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
| Commands | a bar of buttons in six groups, Planetbase style, each with its key's letter; a help screen on `?` | [§9.3](#graphical-buttons-at-milestone-84) |
| Building | after the first, every building within 12 tiles of another: domes get corridors to every dome in reach, structures a path on the ground; the ghost is red, with the reason, where not | [§9.3](#every-building-needs-a-neighbour-at-milestone-85) |

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

**Milestone 96 gave the rule up for the corridors themselves.** The snapped door has
its left byte or top line exactly on the dome's axis, so a corridor run from it sat
half its width off centre, and the player asked for it centred
([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)).
A centred axis corridor straddles two half-tiles again, and where the dome's axis is
on a tile boundary, two tiles: the one beside its own is stamped as occupied when it
is free, and the redraw of a new corridor takes that column or row into its box. The
doors themselves are no longer drawn; a joint of a few pixels takes their place.

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
| 4–5 | occupancy | 0 free · 1 structure, dome or corridor · 2 path on the ground (milestone 85; until then unused) · 3 blocked / reserved |
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
Two exceptions, each for code that only ever runs with its bank in: the wheel's in
bank 6 since milestone 92 ([§4.2](#code-in-bank-6-at-milestone-92)), and the
placement's in bank 1, the window's default, since 94
([§4.2](#code-in-bank-1-at-milestone-94)).

### 4.2 The eight banks

| Block | Bank | Contents | Bytes | Slack |
|---|---|---|---|---|
| `&0000–&3FFF` | 0 | engine code, ISR (milestone 83, 266 bytes at `&0103`), blit kernels, UI, the button bar and the help screen (milestone 84), the merchant's line (milestone 93) and its carriers (milestone 98), the machines carried and installed (milestone 99), the marks of the machines that do not run (milestone 100), the demolition's button and the two kinds of its redraw (milestone 101) · in the snapshots only, the test colony after the code (milestone 87, 251 bytes, [§10.1](#beside-the-ship-at-milestone-87)) | 16,384 | **287**, 95 of them under the tests' floor at `&3E00` (`&3D60` until milestone 95, [below](#milestone-31-found-the-floor-under-bank-0-and-it-is-not-3fc0)) (479 before milestone 107, [§9.3](#a-cursor-step-near-the-colony-at-milestone-107); 232 before milestone 103, [below](#memory-again-at-milestone-103); 264 before milestone 101, 238 before 100, 398 before 99, 224 before 98, 240 before 97, 256 before 96, 401 before 95, 383 before 94, 380 before 93, 369 before 92, 718 before 91, 752 before 90, 744 before 89, 746 before 88, 840 before 87, the same before 86; 855 before 85, 2,304 before 84, 2,991 before 83) |
| window | 1 | **distance matrix** `DIST[96][128]` 12,288 · room icons `m` and `l` 3,936 · **code of the placement** 160 at `&7F60` (`b1code`, milestone 94, [below](#code-in-bank-1-at-milestone-94)) · **code of the demolition** 1,086 in the matrix's unused columns 96–127 (milestone 101 with 901, [below](#code-in-the-routing-matrixs-holes-at-milestone-101)), and **of the save** 630 in the rows after it (milestone 103, [below](#memory-again-at-milestone-103)), and their image at `&6800` until the start spreads it there (milestone 102, at `&6B78` until 103) | 16,384 | 7, in `b1code` (160 before milestone 94); 1,344 in the matrix's unused columns (1,984 before milestone 103, 2,144 before 102, 3,072 before 101) |
| window | 4 | **world plane** 128×128×1 byte | 16,384 | 0 |
| window | 5 | **next-hop matrix** `NEXTHOP[96][128]` 12,288 · **object index** ≤ 960 ([§8.4](#84-object-pass-and-draw-order)) · **machine sprites** 1,584 at `&7400` (milestone 85) · **room icons `s`** 864 after them (milestone 87) · `mach_ptr` 24 after those (milestone 90, from bank 2) · **joints** 328 after it (milestone 96) · the machines' **marks** 24 after those (milestone 100, [§6.10](#seen-at-milestone-100)) · **code of the short bends** 248 at `&7F08`, the window's last bytes (`b5code`, milestone 97 with 272, [below](#code-in-bank-5-at-milestone-97)) | 16,384 | 83: 64 between the object index and the machines, 19 in `b5code` (107 before milestone 100, 336 before 97, 664 before 96, 688 before 90, 1,552 before 87, 3,136 before 85) |
| window | 6 | `flip_mode0` 256 · dome+ring `nw` quadrants 7,424 · **figures** 1,152: the outdoor list 256, the eight figures with shadow 256 and without 256, the 24 empty ring slots 384 (milestone 89; until then 3,456 of slot figures, every figure baked into every slot) · corridors 640 (from bank 2 with the connectors' 256, milestone 89; the connectors gone at 96) · the object pass's own tables 238 at `&6600` (`struct_ptr`, `icon_{s,m,l}_ptr`, `corr_slots`, `conn_points`, `interior_ofs`; from bank 2, milestone 90, [§4.3](#43-bank-2-flat-again)) · entity tables 4,576 ([§6.1](#61-entities)), `agent_fields` pinned at `&6C00` · `worldinfo` 4 · figure cache 512 · **code of the wheel** and since milestone 96 of the joints, 1,554 at `&65EE`, right under `agent_fields` (`b6code`, milestone 92 with 256 at `&6B00`, milestone 93 with 1,280 at `&6700`, milestone 94 with 1,298, milestone 96 with 1,554 in the connectors' place, [below](#code-in-bank-6-at-milestone-92)) | 16,356 | **28** — and 11 of `b6code`'s 1,554 not yet used (21 before milestone 97, 25 before 96, 16 before 95, 46 and 61 before 94, 1,070 before 93, 1,326 before 92, 1,564 before 90, 28 before 89) |
| window | 7 | external structures 11,264 · plants 1,584 · `plant_ptr` 24 · text 2,138, every byte used (milestone 101; 2,120 until then, 2,115 of them used — 2,113 at milestone 93; 2,100 until milestone 90, 2,080 until 87, 2,064 until 86, 2,048 until 85, 1,280 until 84, 1,024 until 79) · **font 768**: the 4×8 font in Mode 1 up to `z` plus five bar cells at codes `&7B–&7F`, generated by `tools/pack.py` from `font_gfx` (milestone 83; 808 until milestone 101, with `{|}~` and DEL, which no text uses, and the cells after them; 1,536 in Mode 0 since milestone 33, where the `audio` reservation was) · **button symbols 595** (milestone 84, from `tools/buttons.py`; 578 until the demolition's at 101, 561 until the merchant's at 93) | 16,379 | 5, and none in the text block (6 and 5 before milestone 101, which spent 17 on the demolition's symbol and 23 on its two texts, and took 40 from the font; 23 before milestone 93, which spent 17 on the merchant's symbol; 39 before milestone 90, which spent 20 on `SUIT AIR LOW` and got 4 back from the font's alignment; 63 before 88: 20 went to `NO ENGINEER`, 4 to the font's alignment) |
| `&8000–&BFFF` | 2 | graphics, flat 6,008 (font gone to bank 7, machines to bank 5 at milestone 85, the `s` room icons to bank 5 at 87, the corridors and connectors to bank 6 at 89, the object pass's tables to banks 6 and 5 at 90) · ghost undo log 1,160, where the demolition runs (milestone 101), and the save (milestone 103) · code 9,077 ([§4.3](#43-bank-2-flat-again)) | 16,380 | **139** (214 before milestone 107, 455 before 106, 541 before 105, 598 before 104, 1 before 103, 22 before 102; 202 after milestone 101's shrink and 3 before it; 19 before milestone 100, 74 before 99, 4 before 98, 5 before 96, 9 before 95, 8 before 94, 10 before 93, 77 before 91, 45 before 90, 154 before 89, 607 before 88, 333 before 87, 608 before 86, 52 before 85, 798 before 84) |
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

**Milestone 91 did, in part.** `tests/test_loop.py` puts its stubs at
`ZZ_BANK0_END` rounded up to 16 and its log right after them — 220 bytes of stubs
and room for a revolution's 20 entries, under `&3EC0`, which allows code up to
`&3D6C`. `test_bar.py`, `test_place.py` and `test_corridor.py` keep fixed stubs, at
`&3D60` now (`&3C00` until 90). So **bank 0's code may reach `&3D60`**, and
`src/main.asm` asserts it.

**Milestone 95 moved the floor to `&3E00`**, for the hauling's 127 bytes. The game
writes nothing between its code and the loader's epilogue at `&3FC0`, so the probes
went to `&3E00`, the three tests' stubs to `&3F00`, and `test_loop.py`'s scaffolding —
its hook, its counters, the end of its log — to `&3F80–&3FB5`; its check that the
stubs' log stops at the scaffolding is now exact. 160 more bytes for the code, none
taken from the tests.

#### Code in bank 6, at milestone 92

The bots wanted about 80 bytes of code ([§6.11](#bots-at-milestone-92)); bank 0 had
17 to its floor and bank 2's code area 10. Bank 6 had 1,298 free in one gap under
`agent_fields` — and **the wheel has bank 6 in the window from its entry to its exit**
([§7.4](#74-one-convention-per-half-and-they-disagreed)), so code that runs only
inside the wheel can live there, at its `&4000`-window address. Bank 7's texts were
the model ([§9.2](#92-hud)), with code instead of data:

- `tools/pack.py` reserves **`b6code`, 256 bytes at `&6B00`**, right under
  `agent_fields`; the gap under it is 1,042.
- `src/main.asm` assembles `src/bots.asm` into it — rasm's `org` with the window
  address as the logical one and bankset 1's as the physical — between two halves of
  `bank6.bin`, asserts that it fits and that the reservation ends where
  `agent_fields` begins, and saves it as `build/b6code.bin`.
- The disc carries it as **`B6CODE.BIN`**, and the loader drops it on the
  reservation after `BANK6.BIN`, as it drops `TEXT.BIN` after `BANK7.BIN`.
  `tests/test_disc.py` checks the bytes arrived; a loader without that step leaves
  151 of the 153 different, and the game crashes on its first revolution, before
  it draws its HUD.
- `tests/simtest.asm` includes the same file in its flat memory.

**The rule:** a routine there is reached only from the wheel, and calls only what
leaves bank 6 in the window when it returns — which every pass of the wheel already
does. Nothing writes under `&6C00`: the generator writes `worldinfo`, a new game
clears from `agent_fields` up, saves and loads move `&6C00–&7DFF`. It held 165 of
its 256. It is where the next pieces of the simulation can go, and the cheapest way
to give bank 0 room: whatever in bank 0 only the wheel calls can move there.

**Milestone 93 did exactly that, three times.** The merchant's line wanted 792 bytes
of bank 0, which had 28 to its floor ([§6.11](#trade-at-milestone-93)). The
reservation grew to **1,280 bytes at `&6700`**, leaving 18 of the gap, and three
pieces of bank 0 that only the wheel calls moved in, unchanged:

- **`src/ship.asm`**, all of it but `ship_call` (the ship's button calls that too; it
  went to `src/econ.asm`, beside the visitors' roll): the ship's revolution, the
  landing, the merchant's cargo, the sol's reckoning — 368 bytes, and 146 new.
- **The specialties' count and pick** (`cw_count`, `cw_pick`, 188): `src/crew.asm`
  is the wheel's half now, and the ship's line, which the HUD draws with bank 7 in
  the window, went to `src/lines.asm` with the merchant's.
- **Slot 12, the flow balance** (`econ_flow`, `ef_o2`, `ef_charge`: 352), out of
  `src/econ.asm` into `src/flow.asm`. Its variables stayed in bank 0: the job board
  and the meteors write `ec_fdiv`.

None of them pages, and their only callers are passes of the wheel with bank 6 in:
`econ_events`, `bot_tick`, the wheel's slot table. The same bytes run at the same
speed in any bank — slot 12 measured 1,782 µs whole and 684 for the oxygen alone
before and after, slot 15 304 — and every test that patched them in base memory
(`test_bots.py`, `test_crew.py`, `test_outside.py`) patches bank 6 now. `b6code`
holds 1,219 of its 1,280; `B6CODE.BIN` is 1,219 bytes.

**Milestone 94 took the last 18 bytes of the gap**: `b6code` is 1,298 bytes at `&66EE`
and holds 1,282 — 63 more, for the mines in the flow balance and the bots' new rule
(`dr_need`, 20, [§6.7](#drilling-at-milestone-94)), less what the balance saved on the
empty structure slots. Milestone 95 gave 9 back: it holds 1,273, with the flow's sum
of the Ore gone into the mines' piles ([§6.7](#hauling-at-milestone-95)).
**Milestone 96 gave it the 256 bytes under it**, the connectors' sprites, which nothing
draws any more, and put the first code of the renderer in it, `src/joint.asm`
([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)):
`b6code` is 1,554 bytes at `&65EE`, with 21 free. Milestone 97 took 10 of them for the
short bends ([§8.4](#the-short-bends-at-milestone-97)): 11 free.

#### Code in bank 1, at milestone 94

Bank 1 is the window's default: the UI, the main loop and the renderer run with it
in, and every routine that pages another bank in puts bank 1 back before it returns.
So code there can be reached from anything that runs in the default configuration,
as long as whatever it calls returns with bank 1 — `b6code`'s rule, mirrored.
`tools/pack.py` reserves **`b1code`, 160 bytes at `&7F60`**, above the room icons `m`
and `l`, where bank 1 had 160 free. `src/main.asm` assembles `src/commit.asm` into it
and saves the whole of `&7000–&7FFF`, icons and code, as `build/bank1c.bin`, which is
the disc's `BANK1.BIN`: loaded where the icons always were, so the loader did not
change. `tests/test_disc.py` checks it arrives byte for byte.

What moved there is the half of the placement that pages nothing itself:
`al_commit`, the structure's path (`alc_pth`, and `al_lgo`, which the ghost calls too),
the legs' redraw (`al_leg`, `al_vr`) and the new ground link (`lk_draw`,
[§9.3](#paths-on-the-ground-at-milestone-94)) — 153 bytes, 120 of them out of bank 2,
whose code area had 8 left; `al_lgo` went last, to make room for the job board's mask
([§6.7](#drilling-at-milestone-94)). What runs per tile
with bank 4 in (`al_cbs`, `al_cbr`, `al_cbb`) stays in bank 2, and so does the leg's
walk (`al_s4`, which pages bank 4 around `al_seg`): code in bank 1 that paged bank 4
in would vanish under its own feet. The UI's test build (`tests/uitest.asm`) includes
the file with the rest; there the calls are absolute and bank 1 holds nothing of its
own. The FIRE of an airlock measured 149 ms in its worst round before and 152 after,
with the ground link drawn.

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

#### Code in bank 5, at milestone 97

The short bends ([§8.4](#the-short-bends-at-milestone-97)) wanted a flag per dome, 64 bytes, and their code;
bank 0 had 48 to its floor and `b6code` 21. Bank 5 had 272 free at the top of its
window, above the joints. `tools/pack.py` reserves them as **`b5code`, 272 bytes at
`&7EF0`**, and `src/main.asm` assembles `src/bend.asm` there and saves the window's
top 3 KB, machines, icons, joints and code, as `build/bank5c.bin`, the disc's
`BANK5.BIN` (`tools/mkdsk.py`; `tests/test_disc.py` checks it arrives byte for byte).
It holds the flags (`jtb_flags`), their clearing and marking, the drawing of a dome's
bends, and `jtb_cc`, the push of a new corridor's joint at `b`, which moved out of
`src/ui.asm` to give bank 0 17 bytes back. Milestone 100 took 24 of the 272 for the
machines' marks ([§6.10](#seen-at-milestone-100)): `b5code` is 248 bytes at `&7F08`
since.

Code there runs only while bank 5 is in the window, and every other routine that
pages bank 5 in puts its own bank back, so it is entered only through `jt_b5`
(`src/object.asm`): HL is the routine,
bank 5 goes in, and the return goes through `ob_b6`, which puts bank 6 back — every
caller runs with bank 6 in — or, through `jt_b5c`, through the routine in DE: `dt_end`
puts bank 1 back for the UI. Nothing in `src/bend.asm` pages, and what it calls
(`ob_put`, `ob_addu`, `dirty_push`) is in bank 0. `tests/objtest.asm` assembles it
flat, with stubs for what it lacks (`bit_tab`, and `cr_plan`'s results, since
`jtb_cc` is never called there); `tests/uitest.asm` puts it in bank 5 as the game
does. 43 bytes are free; bank 5's other 64 are between the object index and the
machines.

**The UI's test build had no room for it flat.** `tests/uitest.asm` assembles almost
all of `src` from `&0100` in bank 0, and at milestone 96 it already reached `&3FFD` —
over the probes that `tests/test_build.py`, `test_terrain.py`, `test_view.py` and
`test_game.py` write at `&3F00–&3FFF`, which had been erasing the tail of the sound
code unnoticed. `src/bend.asm` flat took it to `&4108`, and the probe landed on
`rm_build`: `tests/test_build.py` failed in the full suite while every test of the
bends passed. The UI build now does what the game does — `src/bend.asm` in bank 5,
and its own buffers (`walk_buf`, `snoop_buf`) and `src/sound.asm` at `PAGE2_CODE`,
in bank 2, where the game has its bank-2 code and this build had nothing — and an
`assert` stops its flat code at `&3F00`. It ends at `&3DE9`.

#### Smaller, at milestone 98

The merchant's carriers ([§6.11](#carried-at-milestone-98)) wanted **239 bytes of bank 0**
and 8 of bank 2's code area:

- `src/carry.asm` 187;
- `tr_deal` 47 more (125 → 172 with `trd_post`);
- 5 in the job pass.

Bank 0 had 32 to its floor and bank 2 had 4. Three searches of the code, one per group
of files, found the room by shrinking, not by moving. Each change is behaviour-identical,
each was checked against the tests that look at those bytes, and none is on a per-frame
path:

| Files | Saved | How |
|---|---|---|
| `src/ui.asm`, `bar.asm`, `fit.asm` (bank 0) | **304** | tail calls; `jr` where in range; two adjacent bytes written as one word (`ui_state`/`ui_sel`, `cam_tx`/`cam_ty`); state dispatch by `dec a`; the keys read from `act_hit`'s bits instead of `in_hit` one by one; shared exits (`ui_golook`, the slot screen falling into `ui_doload`) |
| `src/lines.asm`, `help.asm` (bank 0) | **109** | `tr_mul` gone for `ob_mul`; bank 7 paged once in `ac_panel`; `ln_tick` and `ln_panel` gone for two jumps; `tr_netc`/`tr_neta` and `ln_row4` shared; the help screen's cursor through `hud_go`'s own tail |
| `src/act.asm`, `info.asm` (bank 2) | **78** | `cw_lr` shared by three lines; `hud_page1`; fixed-width texts padded with `hud_to` instead of counted blanks |

**What it costs**, against milestone 97 (`tests/test_bar.py`, `tests/test_trade.py`):

| Path | Milestone 97 (µs) | Milestone 98 (µs) |
|---|---|---|
| a frame in LOOK | 984 | 845 |
| a frame in PLACE | 1,036 | 894 |
| a frame in MENU | 862 | 860 |
| a frame in the merchant's line | 980 | 840 |
| the bar redrawn, on a key | 8,620 | 8,800 |
| the help screen, on a key | 365,100 | 365,180 |
| the merchant's line redrawn, on a key | 17,347 | 17,448 |

LOOK and PLACE got faster because the keys are read from `act_hit`'s bits. Nothing that
runs every frame got slower, and a whole revolution of the wheel is 28,954 µs, as
before (`tests/test_sim.py`).

**The saving in `ui.asm` counts only in steps of 16.** Everything between `src/hud.asm`
and the `align 16` that `bar.asm` keeps for `sl_ctg` moves the rest of bank 0 by whole
sixteens. Within bank 0 the help screen and the merchant's line came after the align, so
every byte saved there counted.

**`role_speed` moved and still sits inside its page.** The shrink moves `src/entity.asm`
too, and its 8-byte table is read with a page-local add (`assert (role_speed & 255) <=
248`). It sits at `&2D5D` now, and the assert will say so if a later shrink pushes it
over.

**The test builds needed one label.** `sp_arrive` (`src/supply.asm`) jumps to
`tr_arrive` for a `J_TRADE`. `tests/uitest.asm` and `tests/objtest.asm` assemble
`supply.asm` without the job pass, so there `tr_arrive` is one more name on the `ret`
of `nd_die`, which costs nothing. The UI build's flat code ends at `&3D34` (it was at
`&3DE9`).

#### Code in the routing matrix's holes, at milestone 101

The routing matrices have a row of 128 bytes for each of 96 nodes ([§6.4](#64-routing)):
column *n* of row *s* is node *n* seen from *s*. Columns 96–127 stand for nodes that do
not exist. The rebuild wrote them all the same, as "unreachable", and nothing read them.
**Since this milestone `rt_flush` writes 96 columns**, and those 32 bytes of each of the
distance matrix's 96 rows — 3,072 bytes of bank 1 — hold code: the demolition of
[§9.3](#demolition-at-milestone-101), 1,086 bytes since milestone 102 (901 at 101),
which runs only when the player asks and always with the ghost hidden.

- **Where it runs.** It is assembled for `GH_BUF`, the ghost's undo log, which is empty
  while the ghost is hidden ([below](#the-ghost-log-is-not-slack-and-that-was-measured-before-anything-moved)).
  `ov_run` (`src/demolish.asm`) copies it there, 32 bytes from each row, and jumps in.
  `dm_go` hides the ghost first, and `ui_goto_h` shows it again after.
- **How it gets there.** At `OV_LOAD`, in bank 1 right under the icons: the last rows of
  the distance matrix, which the first rebuild writes and nothing reads before it —
  `&6B78`, 1,160 bytes, rows 86–95, at milestone 102, and `&6800`, 2 KB, rows 80–95,
  since 103 brought the save's image there too ([below](#memory-again-at-milestone-103)). `BANK1.BIN` starts there (`src/main.asm` saves `bank1c.bin` from `OV_LOAD` to
  `&8000`, and `tools/mkdsk.py` checks that the loader's own `OV_LOAD` is the same), the
  loader's epilogue clears the matrix only up to it, and the snapshots carry it there
  too. `ov_install`, at the start and before `game_new`, spreads it into the rows; the
  image and the rows it fills do not overlap (an assert). Until milestone 102 it came in
  at `GH_BUF` itself, as the tail of `PAGE2.BIN` ([below](#and-milestone-102-moved-where-it-comes-in)).
- **What keeps it there.** Nothing else writes columns 96–127 of bank 1: the routing
  writes 96 columns, a new game clears the tables and a load clears bank 5's matrix
  too, and neither touches bank 1. `tests/test_routing.py` compares the matrices with its reference on columns
  0–95 and checks that a rebuild leaves the rest alone; `tests/test_demolish.py` reads
  the rows back against `build/ovl.bin`, and since milestone 102 `tests/test_disc.py`
  does after a boot from the disc.
- **Row 0 runs where it is.** The dirty list runs with bank 1 in the window and every
  handler returns with it ([§8.5](#85-the-dirty-list)), so the first 32 bytes are the
  two handlers of the demolition's redraw, `DK_RSIZE` and `DK_RECT`, run at `&4060`.
  They are written for `GH_BUF` and run 21 KB lower, so they never name themselves:
  they only call out. `dm_do` follows them, at `GH_BUF + 32`.
- **Its variables are not in it.** They follow the code in `GH_BUF` and are written
  before they are read; rasm's `nocode` gives them addresses without bytes, and
  `code skip` takes the address back after them (a plain `code` does not).
- **The limit is the log.** The code and its variables take 1,135 of its 1,160 bytes
  since milestone 102; 25 are left, and an `assert` keeps them below `&9C00`. Until then
  the limit was the test colony ([below](#and-milestone-102-moved-where-it-comes-in)).

The holes had 1,984 bytes more, in rows 34–95: the only large free space in the
machine. Milestone 103 put the save in 20 of those rows, and 1,344 are left, in rows 54–95
([below](#memory-again-at-milestone-103)). It is not cheap space. Code there runs from `GH_BUF` and so only with the
ghost hidden, it pays about 7 ms to be copied in (`ov_run`, 34 rows), and it is not
there for the tests' own builds (`tests/objtest.asm` and `tests/uitest.asm` define the
two handlers' addresses as 0, and nothing there pushes them).

**Bank 2's code area got 199 bytes back first.** It had 3, and the demolition's resident
half needed 180. The survey of milestone 98 ([above](#smaller-at-milestone-98)) had
listed more in bank 2's files than that milestone took; its 75 edits in 15 files were
taken now:

- the structure table's single page (milestone 100) in six more places, an 8-bit
  index instead of a 16-bit multiply;
- `call dt_end` or `jp dt_end` where bank 1 was paged in by hand;
- shared code: `fdc_cmd3` for the first three bytes of SEEK and READ/WRITE DATA,
  `asc_b1`/`asc_b6`, `pal_border` through `pal_pen`, and `ng_zero` as the tail of
  `hw_clear` (moved from `src/newgame.asm` to `src/hw.asm`);
- tail calls, fall-throughs and `jr` where in range.

Each is behaviour-identical, and the cost tests of the whole suite say nothing that
runs per frame got slower ([§9.3](#demolition-at-milestone-101)).

#### And milestone 102 moved where it comes in

The paths of [§9.3](#paths-that-go-at-milestone-102) took the overlay from 901 bytes to
1,086, and it had 3. Its limit was not the log but the test colony: in the snapshots the
colony's setup code ([§10.1](#beside-the-ship-at-milestone-87)) sits in the log's last
page, at `&9B00`, and the overlay's image sat under it in the same snapshot, since both
had to be there at the start. The colony runs once, in `game_new`, after `ov_install`
and before any demolition; the image is read once, by `ov_install`. Only the snapshot
made them share the page.

So the image no longer comes in at `GH_BUF`. It comes in at `OV_LOAD = &7000 − GH_LOG`
(`&6800` since milestone 103, [below](#memory-again-at-milestone-103)),
in bank 1 under the icons, where the loader already loads `BANK1.BIN`: that file now
starts 1,160 bytes lower, and `PAGE2.BIN` is bank 2's data alone again — 259 bytes more
on the disc, and one constant in the loader, which its epilogue uses to clear the matrix
only that far. The whole log is the overlay's, and the first demolition writes over the
colony's code as a big ghost always could.

`tools/mkdsk.py` refuses a loader whose `OV_LOAD` is not the game's (it reads the
loader's constant and the length of `bank1c.bin`), and `tests/test_disc.py` now reads
the holes back after a boot from the disc: with `ov_install` reading 32 bytes off, 1,070
of the 1,086 differ. Its check that the loader's scratch is cleared as in the snapshot
stops at `OV_LOAD`.

#### Memory again, at milestone 103

No feature: the player chose a step for memory alone, before the next one. Bank 0 had 232
bytes to the tests' scaffolding, 40 of them under the floor; bank 2's code area had 1; the
demolition's overlay 25. **Bank 0 got 247 bytes back and bank 2's code area 597.** Nothing
the game does changed, the save's format included, and nothing that runs every frame got
slower.

**Bank 0: the edits milestone 101 put aside.** While milestone 101 looked for bank 2's
bytes, a search of bank 0's files found two kinds of edits that leave the behaviour as it
is: 164 bytes that are never slower, and 83 that are slower only where a key is pressed or
a state changes. They were written against the tree before milestone 101 and waited. They
went in now, both kinds, with the changes of three milestones merged in by hand:

| Files | Saved | How |
|---|---|---|
| `src/ui.asm`, `fit.asm`, `bar.asm`, `help.asm` | **144** | the keys read from `act_hit`'s bits, not with `in_hit`, as milestone 98 began; shared tails (`ui_redo`, `uh_show`, `uipi_bl`, `ac_cur`); a table inside one page read with an 8-bit add instead of `ob_addu`; an instruction skipped by hiding it in a `db #21` or `db #FE`; flags from an `add` instead of a compare; the help screen's text pointer on the stack |
| `src/lines.asm`, `hud.asm` | **42** | the stocks' names already ×8 in `t_f_names`; `tr_netc` returns the flags its four callers tested again; a number's last digit without `hn_div`, and its table of powers from 10; the crew line's counter on the stack |
| `src/input.asm` | **23** | `in_hit` and `in_held` are not in the game any more ([§9.1](#91-controls)) |
| `src/jobs.asm` | **15** | `jb_dome_ptr` was `ob_domeadr` again, the same instructions; it is that label now, and keeps its own copy only in `tests/simtest.asm` |
| `src/rooms.asm` | **10** | the size's bit written into the `and` that tests it; a count on the stack; `rm_fix` falls into what followed it |
| `src/graph.asm` | **7** | `rt_node` inside `rt_slice`, its only caller: a `call`, a `ret` and a `jr` less for each node |
| `src/main.asm`, `isr.asm` | **6** | `is_init` inside `start`, its only caller; `ob_b6` where bank 6 was paged by hand |

Three places in the layout move with every byte saved before them: `role_speed`, read with
an add inside its page (an `assert`, [above](#smaller-at-milestone-98)), at `&2C9F`;
`rm_nbuf`'s table, which `src/rooms.asm` aligns to a page only if it would cross one, at
`&25EF`, 3 bytes before it would; and `sl_ctg`'s `align 16`, which moves everything after
it by whole sixteens. Bank 0's code ends at `&3CE1`.

**What it costs**, against milestone 102:

| Path | Milestone 102 (µs) | Milestone 103 (µs) |
|---|---|---|
| a frame in LOOK (`tests/test_bar.py`) | 844 | 842 |
| a frame in MENU | 859 | 858 |
| a frame in PLACE | 894 | 892 |
| a frame in the merchant's line (`tests/test_trade.py`) | 840 | 838 |
| the HUD drawn whole | 12,002 | 11,466 |
| a whole revolution of the wheel (`tests/test_sim.py`) | 28,954 | 28,954 |
| a button, on its key | 2,914 | 2,916 |
| the bar redrawn, on a key | 8,660 | 8,700 |
| the help screen, on a key | 372,480 | 372,660 |

Some paths got faster:

- the HUD's tick when nothing changed, from 12,979 to 11,981 µs, and from 42,931 to 41,933
  after a jump of the camera (`tests/test_hud.py`);
- the routing, with `rt_node` inside its loop: the bounded case of 128 nodes takes 2.64 s
  of CPU where it took 2.84, and the test colony's 48 nodes take 0.42 s where they took
  0.44 (`tests/test_routing.py`);
- so `x2` now runs 800 frames of the simulation in 400, where it ran 752
  (`tests/test_speed.py`).

The keys pay for the second kind of edit: 40 µs on the bar, 180 on the help screen, 2 on
a button.

One number grew, and it is a frame's worst, not a path's. The airlock of
`tests/test_reach.py` puts its `FIRE` iteration at 156 ms, where it was 148 (the ceiling
is 200), and the iteration after it at 11 ms, where it was 21. The two together take
167.3 ms against 168.7: the same work, split differently. Placing it costs what it did:
`tests/test_place.py`'s numbers did not move.

**Bank 2: the save goes into the holes.** The save and the disc's driver, `src/save.asm`
and `src/fdc.asm`, 633 bytes, run only on `S` and `L`, from `LOOK`, with the ghost hidden:
what the demolition's overlay asks of its code ([above](#code-in-the-routing-matrixs-holes-at-milestone-101)).
They are a second overlay now:

- **assembled for `SV_ORG = GH_BUF + 512`**, right after the 512 bytes of the ghost's log
  the header already borrowed (`SV_HDR`), and stored in the holes' rows after the
  demolition's, 34–53;
- **brought in on every `S` and `L`** by `sv_save` and `sv_load`, which stay in bank 2
  (`src/demolish.asm`) with the names `src/ui.asm` calls: 20 rows of `ldir`, through the
  `ov_copy` that `ov_run` now shares, and a call in ([§11](#where-the-code-is-since-milestone-103));
- **630 bytes, not 633**: a load no longer shows the cursor from inside, `sv_load` does
  after the code has returned, because showing the ghost writes its log in `GH_BUF`.

The resident part is 36 bytes, so bank 2's code area went from 1 free to **598**. The save
overlay ends at `&9BEE`, 18 bytes under the end of the log. The holes have 1,344 bytes
left, in rows 54–95.

**And both images come in at `OV_LOAD = &6800`**, 2 KB under the icons: the demolition's
1,086 bytes padded to whole rows (1,088), then the save's 630. The last 16 rows of the
distance matrix hold them until `ov_install` spreads them, which an `assert` keeps apart
from the 54 rows it fills. `BANK1.BIN` grew by 888 bytes and starts there, `GAME2.BIN`
shrank by 597 and `GAME.BIN` by 247: the disc grew by 44, to 79,597 bytes.
`tests/test_disc.py` reads both overlays back from the holes after a boot from the disc,
and `tests/test_save.py` saves with `rst 0` written over the whole save overlay's place
first; with `sv_ovl`'s copy taken out, the same save never says `SAVED`.

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
**2,603**; milestone 61 another 75 out of the camera and the view's rectangles
([§8.2](#smaller-at-milestone-61)): **2,678**; milestone 62 another 91 out of the
routing rebuild, which got 18 % faster ([§6.4](#smaller-and-faster-at-milestone-62)):
**2,769**; milestone 63 spent 30 of them on a cheaper opening of a source, which let
the routing budget go from 12 expansions a frame to 15
([§6.4](#a-cheaper-opening-and-a-budget-of-15-at-milestone-63)): **2,739**; milestone 64
another 120 out of the controls, which got four times cheaper to read
([§9.1](#smaller-and-faster-at-milestone-64)): **2,859**; milestone 65 another 32 out
of the wheel ([§7.2](#smaller-at-milestone-65)): **2,891**; milestone 66 another 92 out
of the blit kernels and `scr_ringtop`, and every line they draw got faster
([§8.2](#smaller-and-faster-at-milestone-66)): **2,983**; milestone 67 another 37 out
of the pump's and the mine's search, which got about twice as fast
([§6.5](#smaller-and-faster-at-milestone-67)): **3,020**; milestone 68 another 63 out
of the screen addressing, whose row table became four additions
([§8.2](#smaller-and-faster-at-milestone-68)): **3,083**; milestone 69 another 5 out of
the stocks ([§6.5](#smaller-and-faster-at-milestone-69)): **3,088**; milestone 70 another 5
out of the Build job's poster ([§6.7](#smaller-and-faster-at-milestone-70)): **3,093**;
milestone 71 another 29 out of the main loop itself, and every round of it got faster
([§7.1](#smaller-and-faster-at-milestone-71)): **3,122**; milestone 77 another 2, out of
`ob_index` and a variable the object index's build no longer needs
([§8.4](#smaller-and-faster-at-milestone-77)): **3,124**; milestone 78 spent 35 of it
on the world's edge ([§8.2](#the-world-has-an-edge-at-milestone-78)): **3,089**; and
milestone 79 spent 56 on `I`, what is under the cursor
([§9.1](#what-is-under-the-cursor-at-milestone-79)): **3,033**; and milestone 80 29
on the action menu ([§9.1](#what-can-be-done-here-at-milestone-80)): **3,004**; and
milestone 81 13 on `TOO FAR` ([§9.4](#no-corridor-past-63-tiles-at-milestone-81)): **2,991**;
milestone 83 687 on the Mode 1 bands ([§8.1](#two-modes-and-two-palettes-the-raster-splits-at-milestone-83)):
**2,304**; and milestone 84 1,449 on the button bar and the help screen
([§9.3](#graphical-buttons-at-milestone-84)): **855**. Bank
2's code area, at 117
since milestone 59, went to **608** at milestone 72, when the corridor router lost 491
of its 1,672 bytes and got faster everywhere
([§9.4](#smaller-and-faster-at-milestone-72)), to **888** at milestone 73, when
the build flow lost 280 of its 1,068 and the check under the cursor got twice as fast
([§9.3](#smaller-and-faster-at-milestone-73)), to **1,164** at milestone 74, when
the new game lost 276 of its 670 ([§10.1](#smaller-at-milestone-74)), to **1,366**
at milestone 75, when the sound lost 202 of its 540 and every call got faster
([§9.5](#smaller-and-faster-at-milestone-75)), to **1,427** at milestone 76, when
the meteors lost 61 of their 438 ([§6.10](#smaller-and-faster-at-milestone-76)), and to
**1,464** at milestone 77, when the object index's build lost 37 of its 347 and every
call got faster ([§8.4](#smaller-and-faster-at-milestone-77)). Milestone 78 spent 27 of
it on the same edge: **1,437**, and milestone 79 273 on `I`'s `src/info.asm`:
**1,164**, and milestone 80 304 on the action menu's `src/act.asm`: **860**, and milestone 81 45
on refusing corridors past 63 tiles: **815**, and milestone 82 2 on forgetting the
screen's dome before the index is measured: **813**, and milestone 83 15 on the disc's
`di` and `is_on`: **798**, and milestone 84 746 on drawing a button (`src/button.asm`)
and the bar's half of `src/act.asm`: **52**.

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
- **The hole is 1,280 bytes since milestone 79**, when the ground names of
  [§9.1](#what-is-under-the-cursor-at-milestone-79) did not fit in the 7 bytes left of
  1,024. Two files hold the number: `tools/pack.py` reserves the hole and puts the
  font straight after it, and `uitext.asm` checks its texts against `TEXT_MAX`.
  An `assert` holds the two together. If `TEXT_MAX` ran past the start of the font
  (`G_font_gfx`), the texts would be written over it.

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
- **At milestone 86 the three stopped fitting in bank 5 at all.** Milestone 85 had
  put the machine sprites between the data and the code (`&6000`, with the code at
  `&6640`); with the airlocks the code reached 6,835 bytes, and data 8,056 + machines
  1,584 + code 6,835 is 16,475 — 91 more than the whole bank. `tools/mkdsk.py`
  refused the disc (243 bytes past `&8000`). The data now waits in **base bank 1**
  at `&4000`, where the distance matrix will be (the routing builds it; nothing loads
  it), under the room icons at `&7000`; the code waits in bank 5 at `&4000`, under
  the machines, which load straight into `&7400`. The endgame copies the code,
  clears bank 5 up to the machines, pages bank 1, copies the data and clears
  `DIST` — 53 bytes of its 64. `tools/mkdsk.py` checks both ceilings
  (data under `&7000`, code under `B5_BASE`), and `tests/test_disc.py` now catches
  the endgame as it jumps to `&0100` and checks every byte it handed over
  ([§13.1](#131-three-ways-a-loader-does-not-run)).

- **At milestone 87 the `s` room icons went to bank 5 too**, after the machines
  (864 bytes, `B5_LEN` 1,584 → 2,448), which brought `PAGE2_CODE` down three pages,
  `&A400` → `&A100`. `ob_icon` pages bank 5 for the small size, as it pages bank 1 for
  the other two. It was the last reserve on the list ([§15](#15-open-risks)), spent on
  the inside/outside code — `door.asm`, `edges.asm`, the ground links, the ship — 494
  bytes in bank 2, with 607 left.

  **And everything after the icons moved, and two tables broke without an `assert`
  failing.** Six tables are read by their low byte and must not cross a page. Until
  86 they did not by luck; now the packer says it: a run can carry `page=n`, "these
  n bytes stay in one page", and `pack_flat` steps to the next page only when they
  would not — 96 bytes of padding in all. That was the visible half. The other half was
  `ld d,G_mach_op / 256`: **rasm's `/` rounds to nearest**, so with `mach_op` at
  `&93EA` the page came out as `&94`, and the job board read the operator flags from
  the economy's stocks. The asserts check the low byte, not the division. The test
  that found it was a timing one — slot 13 went from 4.3 ms to 40 ms, every job open
  to every agent — and every address division in `src/` is a shift now (`>> 8`,
  `>> 3`, `>> 11`).

- **At milestone 90 the object pass's tables left bank 2.** The suits
  ([§6.6](#suits-at-milestone-90)) needed ~200 bytes of bank 2's code area and it had
  45. Eight generated tables have one reader, `src/object.asm`, which runs with bank 6
  in the window: `struct_ptr` 64, `icon_{s,m,l}_ptr` 72, `corr_slots` 48,
  `conn_points` 48 and `interior_ofs` 6 went into bank 6's gap under `agent_fields`
  (238 bytes at `&6600`, a page of their own so the low-byte reads stay in it), and
  `mach_ptr` 24 into bank 5 after the `s` icons, where `om_prep` already pages for
  the machine it points at. The arena went 6,264 → **6,008** and `PAGE2_CODE` came
  down a page, `&9D00` → `&9C00`. `tests/packtest.asm`, which reads `icon_m_ptr`,
  pages bank 6 for it now. Nothing else reads them, and `tests/test_oibuild.py`'s 300
  timed states pass under the same ceilings.

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
**ground**, occupancy free, with the decor the noise gave it, whatever the noise said.
The starting pod is placed at `(0,0)`. **It was foundation until milestone 94**: the
first domes are built here, beside the ship, and sat on a grey 9 × 9 slab — the
player asked for no foundations under domes, and ground is as buildable (`bd_ok`).
Every world's centre changed with it, so `GEN_VERSION` is 2.

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
| `flags` | alive · indoors · asleep · sick · idle · working · suit phase (milestone 90: which of two needs visits empties the suit) |
| `role` | worker · engineer · biologist · medic · guard · constructor bot · carrier bot · driller bot |
| `node` | node currently at, or source node if in transit |
| `slot` | ring slot 0–7 at that node |
| `dest` | final destination node |
| `edge` | **index 0–7 into the source node's adjacency list**, 255 = not in transit |
| `progress` | 0–255 along that edge |
| `task` | job board entry, 255 = idle |
| `o2 water food sleep health morale` | needs, 0–255 |
| `suit` | air left in the suit, in units of 128 frames — 234 at the start, 70 on every exit ([§6.6](#suits-at-milestone-90)); `skill` until milestone 90, which nothing read |
| `spare` | the load being carried (milestone 88) |

`edge` was specified as a global corridor id. It is **the neighbour's slot in the
node's own adjacency list** instead, so the far end of the hop is one read
(`node_adj[node*8 + edge]`) rather than a search through 96 corridor entries. The
change costs nothing and is why `ent_move_one` has no loops in its arrival path.

Buildings use the same pattern:

| Table | Entries | Fields |
|---|---|---|
| Domes | 64 | `cx cy size room state integrity power ops machines[8] health[8]` — **24 bytes** |
| Structures | 32 | `cx cy kind size state integrity joined owed` |
| Corridors | 96 | `a b dir len state` |
| Jobs | 32 | `kind node agent priority site` |

**Two last bytes changed meaning at milestone 88** ([§6.9](#built-at-milestone-88)).
A structure's eighth byte, planned as `output` and never written, is what a
construction site is still owed (the seventh is the airlock's `joined`, milestone 87).
A job's fifth, `age`, was written 0 and never read; it is now the node the job belongs
to, and `node` is where its agent is going — the two differ only on the first leg of
a Supply. (The structures were 64 in this table since before milestone 30, when they
became 32.)

One table is missing from the list above and is not optional: **`node_occ`, one
byte per node**, the bitmask of which ring slots are taken. [§6.2](#62-the-node-graph)
describes 8 slots per dome filled in `corr_fill` order, which cannot be enforced
without it.

Measured, as laid out by `tools/pack.py`:

| Table | Bytes |
|---|---|
| `agent_fields` — 16 fields × 128, **must be page-aligned**, and since milestone 89 **pinned at `&6C00`**: a save writes `&6C00–&7DFF` of bank 6 as it is, nine sectors, so the entity tables cannot move when the graphics above them do | 2,048 |
| `node_occ` — slot bitmasks (128), and one **figure mark** per agent (128, milestone 89, [§8.5](#85-the-dirty-list)) | 256 |
| Domes, 64 × 24 | 1,536 |
| Structures, 32 × 8 | 256 |
| Corridors, 96 × 5 | 480 |
| **Total in bank 6** | **4,576** |

(The structures read 64 × 8 = 512 here, and the total 4,832, until milestone 89 —
thirty milestones after they became 32. `tools/pack.py` had the 256 all along.)

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

#### Colonists and bots, at milestone 92

The 80 + 16 of this section became addresses: **ids 0–79 are colonists, 80–95
bots.** The wheel moves 96 agents — eight slots of twelve
([§7.3](#73-degradation)) — and visits 96 for their needs; from milestone 92 the needs
pass stops at 80 (its slices are eight, so a slice is all colonists or all bots), the
living that slot 12 counts into `EC_ALIVE` and the oxygen demand are the 80, the
Control rooms' cap stops at 80, and a ship's newcomers take ids under 80 only. Bots
are born at 80–95 from the Bots stock ([§6.11](#bots-at-milestone-92)).

**Ids 96 to 127 were never moved, and the cap reached 128.** Nothing in the wheel
went past 95, but the cap was 4 + 48 per Control room up to 128 — 100 with two — and
`ship_crew` took any free id up to 127: a colony's 97th colonist would have stood
where it landed for ever, never hungry and never working. No colony had got there.
The cap is 80 now, and ids 96–127 hold nobody.

### 6.2 The node graph

The colony is a graph, and almost every system reads it rather than the tile grid.

- **Nodes** (≤128): every dome, every external structure, the landing pad, and up to 8
  transient construction sites.
- **Edges**: a corridor between two domes, or between a dome and an airlock; an
  *outdoor edge*, a path on the ground, between an airlock and a structure or between
  two structures (milestone 86). A dome has at most 8 edges — one per `conn_points`
  direction.
- **Node capacity**: 8 ring slots per dome (`corr_slots`), filled in `corr_fill` order
  `0,4,2,6,1,5,3,7` so people never look stacked; 1–2 work slots per external structure.

**In memory** the graph is a fixed-width adjacency list, because the Z80 wants the
neighbour list's address from one shift:

```
node_deg[128]      1 byte per node          128 B
node_adj[128][8]   neighbour ids, row n at node_adj + n*8   1,024 B
```

There are 96 nodes, so entries 96–127 of `node_deg` belong to no node. Since milestone
102 they keep where each structure's own link goes (`LK_OWN`,
[§9.3](#paths-that-go-at-milestone-102)).

Both live in **bank 2**, with the BFS workspace, for the reason in
[§6.4](#64-routing). 1,152 bytes.

External structures are never corridor-connected. Reaching one means leaving through an
airlock and walking — which is exactly why airlock placement is a real decision, and why
a sandstorm that kills people outdoors has teeth.

**Since milestone 85 the walk is on the map.** A structure is joined to its nearest
building by a *path on the ground* — foundation tiles with occupancy 2, no cover — and
that is its outdoor edge; a dome is joined by corridors to every dome in reach
([§9.3](#every-building-needs-a-neighbour-at-milestone-85)). Until then every building
got an edge to the nearest dome however far, drawn by nothing.

#### The airlock is a structure, and the only door — decided at milestone 86

The asset set has a standalone **`airlock` structure**: 2×2 tiles, masked, with two
opposed doors, symmetric top to bottom so that a corridor can meet it from either
side. The document was written when `airlock` was only a *room type*, a whole dome
spent on being a door, and the two readings waited here as an open question. The
player settled it, in so many words: *airlocks join only the nearest building, and they
are the entrances and exits of the base.* So:

- **An airlock is joined to its nearest dome by one covered corridor**, which meets it
  from the north or the south ([§9.3](#airlocks-are-the-doors-at-milestone-86)). It is the
  one structure a corridor ever reaches.
- **A structure's path goes to the nearest airlock or other structure — never to a
  dome.** Whoever goes out goes out through an airlock, and walks the paths.
- **A dome is joined only by corridors**, to domes, and to an airlock that has none
  yet; a dome with no corridor is red. The path that milestone 85 gave such a dome
  would have been a door.

The `airlock` room type and its three icons are now redundant (index 7, 400 bytes
across the three sizes). They stay, which keeps every index stable.

#### Inside and outside — milestone 87

The graph now knows which of its places have air. **Inside** is a finished dome, a
finished airlock, and a corridor between two of them; **outside** is everything else
— the ship, a structure, a construction site of any kind, and the ground between them.
An agent carries it as `F_INDOORS` (bit 1 of its flags), and three systems read it:
oxygen ([§6.6](#66-needs)), the sandstorm, which hurts anyone outside and no longer
"anyone at a structure", and the oxygen demand, which counts only those inside.

**The ship is structure 0**, node 64, kind `K_SHIP`, at `(0, 0)`, finished and at
integrity 255 from the first frame; its 2×2 tiles are occupied but carry no
foundation. It is **not a building**: it is never "near" a new one, it does not make
a solar panel stop being the first structure, meteors pass over it, and `I` calls it
`SHIP`. It stands in slot 0 always — `game_new` puts it there and nothing demolishes
it — so the structure scan starts at 1 when slot 0 is the ship: one check, not one per
record.

**Walking on the ground is free, and drawn by nothing.** Whatever is placed without a
path — a dome, an airlock, the first structure — gets a *ground link*, an edge to the
nearest ship or airlock: nearest by max(|dx|, |dy|) in half tiles, finished or still a
site, not itself, with a free edge (degree under 8); the first on a tie (`lk_anchor`,
`src/link.asm`). It is the user's choice: free walking outside, with the visible paths
kept for structures. A structure's path is already such an edge. **Since milestone 94
an airlock's ground link is drawn too**, and the first structure's: an L of
foundation over the free ground on the way ([§9.3](#paths-on-the-ground-at-milestone-94)).

**A dome's site is reached from outside.** Its corridors are planned, paid and
written into the corridor table at placement, as before, but **they become edges only
when both their ends are finished**: a corridor to a site would be a corridor to a
place with no air. At placement one end is always the new site, so `cr_commit` makes
no edge at all; only `LINK`, which joins two domes that may both be standing already,
asks (`cr_commit_ln` → `cr_lnk`, `src/route.asm`). The first version asked inside
`cr_commit` for every corridor of every placement — 133 µs for a question whose answer
was known, which `tests/test_corridor.py`'s ceilings caught. When the dome is done
(`lk_done`, `src/door.asm`, from the Build job's last visit):

1. it is **sealed**: every edge it has is a ground link, and all go, from both ends —
   the neighbour's list closes the gap with its last entry, so whoever is walking an
   edge there still arrives where they were going;
2. its builder, who worked from outside, is **put out** at the place the first of
   those links led to, outside, with that as their destination. Without this the first
   dome locked the only engineer inside the only dome there was, and the airlock that
   would have let them out was never built. **Since milestone 88 everyone standing
   there is put out**, the carriers too ([§6.9](#built-at-milestone-88));
3. every corridor that touches it and whose other end is finished becomes an edge —
   unless it already is one, which is the case for an airlock rebuilt after a meteor.

An airlock keeps its ground link when it is done: it is the door. Its builder is then
standing in a place with air, and is inside — since milestone 88 so is everyone else
standing in it. A structure keeps its path.

**"Has its corridor" is a byte now.** Until milestone 86 an airlock without a corridor
was an airlock of degree 0. With ground links every airlock has an edge from the start,
so the struct record's byte 6, `ST_JOINED`, says it instead; `al_commit` sets it when a
dome's corridor reaches the airlock or the airlock's own corridor is planned.

**The flag is set where it changes.** `en_in` (`src/door.asm`) answers "does this node
have air?" straight from the dome or structure record — 40 µs for a dome, where the
general `gr_live` cost 60. Movement asks it as little as it can:

- **Leaving:** whoever starts outside stays outside — the flag decides, not a second
  look at the node. Whoever starts inside stays inside only on a corridor to a place
  with air, and never between two structures: two airlocks are joined only by the
  ground.
- **Arriving:** whoever travelled inside arrives inside — the departure already asked
  about the target. Only someone coming from outside asks: are they stepping into an
  airlock?

So the flag is the truth until the agent next moves. A place that changes state under
someone standing there is handled where it happens for the two cases that matter —
the dome's builder (put out) and the airlock's (put in) — everyone standing there,
since milestone 88; anyone else keeps the flag
they had until they move. Since milestone 90, when being outside costs air, a meteor
that knocks an **airlock** back to a site puts the people standing in it outside, with
a full suit, as its builder would be (`lk_air_out`, [§6.6](#suits-at-milestone-90)).
Since milestone 104 so does someone in the tube on the way to it
([below](#who-was-in-the-tube-at-milestone-104)). A meteor never knocks a dome back: it
stops one of its machines ([§6.10](#610-events-and-hazards)).

#### Who was in the tube, at milestone 104

Milestone 90 left two cases open, and this milestone found that one of them never
happens. **A meteor does not knock a dome back.** `mt_hit` has made a working dome stop
one machine since milestone 38, and only a structure goes back to a site. The row of
[§15](#15-open-risks) that said a dome knocked back keeps its people inside was wrong
when milestone 90 wrote it. `tests/test_impact.py` holds every impact on a
dome to that rule, and every other byte of the machine — the people inside included —
to staying as it was.

**The other case was real.** Whoever travels inside arrives inside: the departure
asked about the target, and when someone left a dome for its airlock, the airlock had
air. If a meteor knocks the airlock back while they are in the tube, they arrived at a
site with `F_INDOORS` set. Until they next moved they breathed the colony's air, and the
oxygen balance counted them inside.

**They are put outside at the moment of the impact**, as if they had set off after it:
outside, with a full suit, marked to be drawn, and walking the rest of the way on the
ground. It is the rule a departure would have applied
([above](#inside-and-outside--milestone-87)). They then arrive at the site outside and
go on outside. Someone in the same tube going the other way, from the airlock to the
dome, is going somewhere with air, and stays inside.

**Where it is done.** In `lk_air_out` (`src/door.asm`), after the people standing in
the airlock, one pass over the 128 agents' edges. Someone on the road whose edge ends
at the airlock — `node_adj[node × 8 + edge]`, the node their arrival would read — and
who is alive and inside is put out by the same `lks_out`. The arrival itself was not
changed: it runs for every agent on every step of the wheel, and a check there would
add an `en_in` to every trip from a dome into an airlock, for an event that happens a
few times in a game.

**`lk_each` got faster on the way**, because `lk_air_out` now makes two passes. It
finds the node with `cpir`: 21 T for each agent elsewhere, where the old loop took 31.
A dead agent or an empty slot is now passed over without a `push` and a `pop`. The
empty slots all have node 0, because `game_new` clears them, so a pass for dome 0 used
to stop 124 times. Measured in `tests/test_suit.py`'s world, a dome and an airlock in
`main.sna`:

| | Milestone 103 (µs) | Milestone 104 (µs) |
|---|---|---|
| `lk_each` for a node with nobody at it | 1,194 | 811 |
| `lk_each` for dome 0, with the 124 empty slots | 6,154 | 3,163 |
| `lk_air_out`, three people standing in the airlock | 1,644 | 2,571 |
| a whole impact on that airlock (`mt_tick`) | 6,025 | 6,952 |

`lk_each` is what a dome's completion and a demolition call too. **An impact on a
working airlock was never timed.** `tests/test_impact.py`'s 400 random impacts never hit
one, and its ceiling for a building, 5,270 µs, did not cover the 6,025 it already cost.
`tests/test_suit.py` now times it, with a ceiling of 7,100. The cost falls once, in the
frame of an impact on a working airlock.

**What checks it** (`tests/test_suit.py`):

- **In the game**, `main.sna` with a dome and an airlock:
  - one colonist leaves the dome for the ship and another leaves the airlock for the
    dome, both inside in the tube, while a third stays in the dome;
  - a real meteor shower is aimed at the airlock, and the impact falls while the two
    are in the tube;
  - the first is outside at that moment, with three minutes of suit, on the same edge,
    and reaches the site and then the ship outside;
  - the second reaches the dome inside, and the third does not change.
- **At random**, 400 calls of `lk_air_out` on random flags, nodes, edges and suits of
  the 128 agents and a random graph, with half and doubled edges. They are compared
  with the reference (`tools/entity.py`, `air_out`): flags, suits and the figure marks
  of all 128, and nothing else in their fields.

Four planted faults are caught:
- `lk_air_out` without the tube, as at milestone 103 — the game and the random calls
  both fail;
- the tube applied to people already outside;
- always the node's first edge;
- `lk_each` without the last agent.

The code is 57 bytes of bank 2's code area, which has 541 left. **The save did not
change** (`SV_VER` 8).

### 6.3 Movement

An agent is in one of two states, and nothing else:

```
AT    node n, slot s        drawn: in a dome, the ring slot at corr_slots[n][s];
                            at a structure or the ship, beside it (milestone 89)
TRANS edge e, progress p    drawn: outside, on the line between the two nodes
                            (milestone 89); in the tube, nothing
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
walking between domes looks dead. **Built differently at milestone 89**
([below](#seen-outside-at-milestone-89)): the 2×8 ring figure, no saved background, up
to 64, and ≈ 5 ms a step rather than 21 µs.

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

#### Seen outside, at milestone 89

Until milestone 89 a colonist was seen only in the eight ring slots of a dome. At the
ship, at a structure and on the ground between they were present and invisible, and
since milestone 87 the game starts with four people beside the ship — so its first
screen showed the ship and nobody ([§15](#15-open-risks)). Now everyone **outside** is
drawn ([§8.4](#colonists-outside-at-milestone-89) says how):

- **Standing at a structure or the ship**, in their slot's place: slots 0, 4, 2, 6 in
  the half-tile row just below the footprint, at columns `cx−1`, `cx`, `cx−2`, `cx+1`;
  slots 1, 5, 3, 7 in the row just above it. A ninth (`NO_SLOT`) is not drawn, as in a
  dome. A colonist born at the pad now takes a slot there (`ent_claim` in `sh_born`),
  as every arrival does; until milestone 89 they were born without one, which nothing
  could see.
- **Walking outside** (on an edge, `F_INDOORS` clear): on the straight line from one
  node's **front point** — `(cx, cy + half its height)`, where slot 0 stands — to the
  other's, at `a + (b − a)·progress/256`, in slot 0's column. From centre to centre the
  figure started on the ship's roof.
- **Anything else**, nothing: in a dome the ring draws them, in the tube nobody is seen,
  and the dead are not drawn.

**One step per movement update — the player's decision.** An edge takes the same time
whatever its length ([§6.2](#62-the-node-graph)), so on a long ground link the figure
moves up to ~4 tiles a step, three steps a second. Making the time follow the distance
would have changed every walk in the balance; drawing only the stops would have hidden
the carriers again. Asked, the player chose the steps as they are.

**The simulation only marks.** Wherever something visible outside changes — a step
on an outdoor edge, leaving or arriving outside, a birth at the pad, a death, the
colonists turned out of a sealed dome (`lko_one`) — the movement calls `fg_mark`
(`src/entity.asm`): one byte per agent, and one `DK_AGENT` into the dirty list if the
byte was 0 ([§8.5](#85-the-dirty-list)). Steps in the tube mark nothing. Where the
figure *is* is the renderer's to compute (`fg_want`), when it gets there.

**And the movement got faster for it**: the per-agent body of `ent_move_one` is now
inside the slice's loop, so every exit is a jump to the next agent instead of a `ret`
to a `call`, and the role's speed is a one-page lookup. Measured in the pinned wheel
of [§7.2](#72-the-wheel): 841.8 → **781.4 µs** a slot (842.8 → 781.9 with everyone
inside).

### 6.4 Routing

Two 128×128 byte matrices, a full 32 KB of the extra RAM:

| Matrix | Bank | `[from][to]` holds |
|---|---|---|
| `NEXTHOP` | 5 | the next node to step to, 255 = unreachable |
| `DIST` | 1 | hop count, 255 = unreachable |

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

| Graph | Nodes | Avg degree | Full rebuild | before milestone 62 |
|---|---|---|---|---|
| Realistic colony | 48 | 2.2 | **0.46 s** (0.50 at milestone 62) | 0.62 s |
| Sparse, at the node cap | 128 | 2.0 | 2.78 s | 3.55 s |
| **The real ceiling** | 128 | 2.5 | **2.90 s** | 3.69 s |
| (Degree 8 everywhere — cannot happen) | 128 | 8.0 | 4.15 s | 5.03 s |

The last row is unreachable: the corridor table has **96 entries**
([§6.1](#61-entities)), and external structures are never corridor-connected, so the
graph cannot exceed 128 nodes with ~160 edges. Average degree tops out near 2.5, not 8.

That changes what dominates. The cost is not the edge relaxations — it is **taking a
node off the queue**, which happens `n` times per source and therefore **n² times per
rebuild**:

> **174 µs per node expansion, O(n²)** — 222 before milestone 62.

| Colonists' worth of nodes | Full rebuild, CPU |
|---|---|
| 16 | 0.04 s |
| 32 | 0.18 s |
| 64 | 0.71 s |
| 128 | 2.85 s |

A young colony re-routes in a blink; only a maxed-out one pays seconds. Sources run
`0 .. n-1` where `n` is the **high-water node id + 1** — a demolished dome keeps its
id with degree 0 and its row correctly comes back "unreachable from everywhere", so
ids never need compacting and no 32 KB initialisation pass is needed. (Demolition came
at milestone 101 and does exactly that, [§9.3](#demolition-at-milestone-101); the id is
free for the next building.)

**`rt_flush` writes 96 columns of each row, not 128** (milestone 101). Columns 96–127
stand for nodes that do not exist, and in the distance matrix they hold code
([§4.2](#code-in-the-routing-matrixs-holes-at-milestone-101)). `tests/test_routing.py`
compares the matrices on columns 0–95 and checks that the rebuild leaves the others
as they were.

The rebuild is **sliced by node expansion**, not by source: one source is 23 ms and
would blow the frame on its own. `rt_slice` takes a budget in expansions and
suspends anywhere, with four bytes of state.

At the 15-expansions-per-frame budget of [§7.2](#72-the-wheel) that is 3.4 s of
wall-clock for a 48-node colony and about 22 s for a full one. Until milestone 63 the
budget was 12: 4.2 s and 27.7 s. During that time the
old matrix stays live and agents route on slightly stale
information. Building a corridor and watching traffic start using it a few seconds
later is acceptable, and arguably reads as the colony reorganising. Destroying one is
not acceptable to get wrong, so **edges carry a live `state` byte**: an agent about to
enter a dead edge re-checks, and waits or re-routes. Stale routing is allowed to be
inefficient, never to be invalid.

#### Smaller and faster, at milestone 62

`src/graph.asm` went from 314 bytes to **223**, and the rebuild got 18 % faster. A node
expansion went from 222 µs to 174, and the real ceiling, 128 nodes at degree 2.5, from
3.69 s of CPU to 2.90. Over 218,144 calls, measured with interrupts off, not one got
slower:

- a whole rebuild is 18.5 % faster;
- `rt_slice` with the game's B = 12 is 18 % faster, and 16–18 % with B = 1, 2, 3, 7
  and 255.

The wait for new routes is unchanged, because the budget is counted in expansions: a
full colony still routes on stale tables for ~27 s. What changed is what the 12
expansions of a frame cost on average, about 2.1 ms instead of 2.7.

**The worst frame of a rebuild is not expansions, and the budget did not go up.**
`rt_slice` counts the opening of a source (clearing 256 bytes) and its closing (two
copies of 128) as one unit each, like a node. Each costs about 1.3 ms, as much as
eight nodes.

- `rt_n` is always 96. In a young colony most of those sources are alone, and each
  costs three units: open, itself, close.
- A slice of 12 is then four lone sources: **13.1 ms**, 13.4 before milestone 62.
  That was measured on 12 nodes with `rt_n` = 96, the colony's shape for its first
  hours.
- At 15 it would be five, **16.4 ms**. So raising `WH_RT_B` to spend the 22 %, as
  this section first proposed, would have made the worst frame 3 ms worse in the
  common case to save ~5 s in the rare one. It stayed 12 until milestone 63 made the
  opening cheap (below).

The check was a script kept out of the repository. It used 28 graphs: the ten of
`tools/graph.py` and eighteen random ones, from 1 node to 128, some with `rt_n` above
the highest id. On each it ran a whole rebuild, and sliced ones with B = 1, 3 and 12
(and 2, 7 and 255 on five of them). Banks 1 and 5 were filled with a pattern first,
so that a stray write would show. After every call it compared:

- the carry, `rt_src`, and whether a source is open;
- the 256-byte row;
- the queue up to its tail, and its head;
- which bank was left in the window, and both banks whole.

All 218,144 calls were identical with the old file and the new one.

- **The queue's tail lives in `HL'`.** Appending to the queue was twelve instructions:
  `push de`, the tail read twice, the address built, the tail written back. It is now
  `exx`, `ld (hl),a`, `inc l`, `exx`. Nothing else uses `BC'`, `DE'` or `HL'` —
  not even the interrupt handler that milestone 83 brought in ([§8.1](#81-screen-layout)),
  which touches only `AF` and `BC`, on the stack. (`AF'` is not swapped by `exx`; since
  milestone 66 the blit kernels keep a count in it, [§8.2](#smaller-and-faster-at-milestone-66).)
  The tail is loaded once per node and stored once.
- **The queue's indices are stored as 128 + k**, which is the low byte of their slot
  in `RT_QUEUE`.
  - While a source is open, `rt_phase` is `NODEPG` instead of 1. So the word at
    `rt_tail` *is* the queue's address, and loads in one go.
  - The head and tail are read as one word and compared.
  - The 128th entry wraps both to 0 together, so "empty" still means "equal".
- **`u` stays in `L`.** `rt_u` was written once and read back three times.
- **The distance cap is gone.** `RT_FAR` clamped `dist + 1` at 254. A breadth-first
  search over at most 128 nodes never gets there: the longest path is 127 hops.
- **The first hop is compared with the source.** `rt_open` sets `next[src]` to the
  source itself. For any other `u`, `next[u]` is a neighbour of the source, never the
  source. So `IXL = next[u]` and `IXH = src` replace the branch that put 255 in `IXL`
  at the source.
- **The adjacency row is `(G_node_adj/8 + u)·8`**, as in `entity.asm` (`assert`ed),
  and the loop steps through it with `inc e`.
- **`rt_flush` writes bank 5 first.** Bank 1, the default, is then the one left in
  the window, and the third `out` goes. The destination is computed once into `DE`
  and kept on the stack for the second copy, so `rt_dst` is gone.
- **`rt_mark` falls into `rt_begin`.** `rt_slice` returns on a carry that is already
  clear, instead of clearing it again.
- **`rt_rebuild` moved to the tests.** Nothing in the game calls it: only
  `tests/graphtest.asm` and `tests/simtest.asm`, which now carry their own copy. That
  is 11 of the 91 bytes.

**What the planted faults found.** Twenty-nine faults were run against the script and
six tests: `test_routing.py`, `test_sim.py`, `test_route.py`, `test_game.py`,
`test_needs.py` and `test_speed.py`. The script caught twenty-five. It missed:

- the three in `rt_mark` and `rt_begin`, because it never calls `rt_mark` in the
  middle of a rebuild;
- `djnz` back to the top of `rt_slice`, which only costs time.

Four passed every test:

- **Two were in the slice's accounting:** the opening of a source not counted, and the
  closing not counted. The tables come out the same; only some frames do 13 units of
  work instead of 12. `test_routing.py` accepted anything within ±30 % of the
  expected number of calls.
- **One costs only time:** `djnz` back to `rt_slice`, which re-reads the phase at
  every node.
- **One leaves bank 5 in the window:** the two rows written in the other order.
  Nothing depends on it, since the wheel pages bank 6 straight after, so it stays
  the script's.

`tests/test_routing.py` checks two more things now:

- **The number of calls is exactly ⌈Σ (R(s) + 2) / B⌉**, where R(s) is how many
  nodes source s reaches. Each source costs one opening, one dequeue per node reached,
  and the empty dequeue that closes it. Checked on five graphs with B = 1, 3 and 12.
- **`rt_mark` in the middle of a rebuild.** The degree-8 graph is being rebuilt; the
  colony's graph is written in its place, `rt_mark` is called, and the slices run to
  the end. This is tried in the middle of source 4, straight after a source closed,
  and straight after one opened. What comes out must be the new graph whole, and
  `rt_dirty` must be raised.
  - This is what happens every time a corridor is built while the wheel is routing,
    and nothing tested it.
  - The three `rt_mark`/`rt_begin` faults were caught anyway, by `test_game.py` and
    `test_needs.py`, but only as a colony that stops working.

There are two negatives: the opening not counted, and `rt_begin` not resetting
`rt_src`. With the old file, less `rt_rebuild`, both checks pass. The first negative
fails there, because it looks for the new code's `call rt_open` · `dec b`.

**One test broke, and the fault was the test's.** `test_link.py` counts the rounds of
the main loop in which a diagonal corridor appears, and wants one row per round.

- **How it counted.** A round was "the PC inside the wait for vsync", sampled every
  100 µs. With the rebuild cheaper, one round of the S → L case ended a few µs before
  vsync. The sample never saw it wait, so two rounds counted as one with two rows.
  - Sampled every 20 µs, the same run shows one row per round.
  - Sampling closer only makes the miss rarer: the wait can be as short as it likes.
- **How it counts now.** The rounds are counted inside the game. `test_reveal.Game`
  sends the main loop's closing `jp main_loop` through 23 bytes in the tests' own
  scaffolding at `&3EC0`, about 27 µs a round.
  - Those bytes store the round's `rv_pend` in a ring of 16, then bump an 8-bit
    counter.
  - The order matters. The first version bumped the counter first, and a sample
    between the two read a slot not yet written.
- **A negative was added.** With a diagonal row costing 6,000 instead of 12,000, three
  come out in one round, and the test must say so.

`test_reveal.py`, `test_link.py`, `test_fit.py`, `test_meteor.py` and `test_ghost.py`
share that clock. All pass with it, with the old `graph.asm` too.

#### A cheaper opening and a budget of 15, at milestone 63

Milestone 62 left the budget at 12 because the worst frame was a young colony's lone
sources. Half of what a lone source costs is the opening, and that half did not have
to be paid.

- **`rt_open` clears only what the previous source wrote.** A search writes `dist`
  and `next` only for the nodes it puts in its queue. So between two sources the row
  is 255 everywhere except `queue[0..k)`, and that holds in the middle of a source
  too. The opening resets those k entries instead of clearing 256 bytes.
  - Measured: 112 + 14·k µs, against 1,644 for the `ldir`.
  - A lone source (k = 1) opens in 0.13 ms instead of 1.6.
- **The `ldir` stays for two cases.**
  - k > 109, where it is cheaper. That happens only on the tests' 128-node graphs.
  - k = 0, which `rt_begin` now sets to mean "the row is unknown". The save block
    covers the row and the queue (`&9D00–&A4FF`) but not `rt_tail`, so after a load
    they no longer agree.
- **`WH_RT_B` is 15.** With the cheap opening, no slice of 15 costs more than the
  worst slice of 12 did before milestone 62, on any of the 28 graphs.
  - The worst of all went from 13.5 ms to 10.4. A young colony's went from 13.4 to
    9.1.
  - The average slice on the 128-node ceiling is 2.64 ms, against 2.70 for 12 then.
  - Every rebuild takes a fifth fewer frames.
- **The cost is 30 bytes:** the loop, the choice, and `rt_begin`'s marker. It also
  costs 6 µs on the openings that still use `ldir`. In the game that is the first
  opening of each rebuild; in the tests, also every opening after a source that
  reached more than 109 nodes.

In the game, a rebuild of the starting colony (4 nodes with edges, 96 sources) after
`rt_mark` went from 26 rounds of the main loop to 21. No round got longer. The rounds
over 20 ms are the HUD's, and they are there with routing or without.

The first version returned from `rt_open` with the carry left set by the comparison
with `RT_RESET`. A slice that ended straight after an opening then said "finished".
The exact slice count of milestone 62 caught it at once; the whole rebuild did not,
because it never ends a slice there.

The check was the same script. All 218,144 calls were identical to the file before
milestone 62, because the row after an opening is the same whichever way it was
cleared.

**What the planted faults found.** Nine faults in the new opening and in
`rt_begin`'s marker were run against the script and four tests: `test_routing.py`,
`test_sim.py`, `test_game.py` and `test_needs.py`.

- `test_routing.py` caught all nine.
- The script caught eight. The ninth, the opening always using `ldir`, costs only
  time. The new negative catches it anyway: without the cheap opening, taking
  `rt_begin`'s marker away no longer matters, and the test says so.
- `test_game.py` missed five and `test_needs.py` six. A stale `next` or `dist` only
  shows on a graph in several pieces, or after a load.

`tests/test_routing.py`'s `rt_mark` check now scribbles the row and the queue before
the mark, as a load leaves them. A third negative takes `rt_begin`'s marker away.

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
mine       (on ore)        -> Ore                       needs 1-3 drillers (94), carried (95)
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
`LOOK`), so the share is larger now; the cost was still 4 ms, until milestone 67 took
it under 3 ([below](#smaller-and-faster-at-milestone-67)). Nothing else in the catalogue pays a byte or a
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
| `mine` | 2 / 3 / 4 Ore with 1 / 2 / 3 at work, nothing with none (milestone 94), into a pile of up to 30 at the mine that is carried away in tens (milestone 95) | 8 Power; a worker or driller bot each | 23 Ore with one |
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
  as in Planetbase, where dismantling is its own act. Since milestone 99 a machine
  is then stopped until its materials are carried to it and an engineer installs it
  ([§6.9](#machines-carried-at-milestone-99)); a plant works at once.
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

#### Smaller and faster, at milestone 67

`src/terrain.asm`, which is `bd_res` and nothing else, went from 115 bytes to **78**,
and the search for water or ore got about twice as fast. Measured through the whole
of `bd_check`, as above, with interrupts off:

| Placement | Before | After |
|---|---|---|
| a 3×3 that needs no material | 1,207 µs | 1,206 µs |
| the pump at a shore, the water in the first row of the scan | 1,337 µs | 1,288 µs |
| the pump on dry ground, 7×7 with nothing in it | 3,339 µs | **1,972 µs** |
| the mine with no vein, 8×8 | 4,305 µs | **2,747 µs** |

`bd_res` on its own is 57 % faster over 3,000 calls, and no call got slower. (The
figures in the section above were measured at milestone 31. `bd_check` has changed
since, so both columns here were measured now.)

- **The two materials are one question:** `(byte & D) == E`. Water is class 4 or 5,
  so `(b & 6) == 4`. Ore is a mountain with the resource bit, so `(b & 15) == 11`.
  - A tile is now four instructions.
  - It used to be a call to `bdr_test`, which read `bd_nres` back from memory to
    decide which question it was asking.
- **One `tile_addr` for the whole margin.**
  - It is taken at the footprint's corner. Moving back two rows and two columns is
    −258, and each row after that is 128 bytes further.
  - The old loop called `tile_addr` for every row and kept its place in `bd_cy` and
    `bd_row`, which were `build.asm`'s variables. `bd_res` no longer touches them
    (and since milestone 73 they no longer exist).
  - The subtraction cannot leave the plane, because the scan stays inside ±63 (see
    above).
- **The kind and the parameter are read as one word.** `bd_param` follows `bd_kind`
  and `BK_STRUCT` is 1, so the test is `dec l`; both are `assert`ed in `build.asm`.
  The material's number is the parameter minus 2, since `K_MINE` is
  `K_EXTRACT + 1`, also `assert`ed.
- **"Nothing needed" and "found" share one exit:** `xor a`, `ld (bd_nres),a`, `ret`.

The check was a script kept out of the repository, on the game's own binary,
`build/main.sna`. It used six planes in bank 4:

- the uitest's world;
- the game's world;
- noise;
- three sparse planes with near misses: crater, foundation, a mountain without the
  bit, the bit on water and on other classes. Each has a mountain rim at |x|, |y| ≥ 62,
  as the generator leaves it.

It made 3,000 direct calls of `bd_res`, for every kind in the catalogue, at sizes from
1×1 to 8×8, with `bd_nres` starting from garbage. It also made 1,500 calls of
`bd_check` from cursor positions anywhere, outside the world included. It compared
`A` and `bd_nres`, and for `bd_check` also `bd_nbad`, `bd_bad`, `bd_tx` and `bd_ty`.
All 4,500 were identical with the old file and the new one.

**The first run was on the wrong binary.** It ran on `tests/uitest.sna`, and all 4,500
calls agreed there. In the game, the search looked in the wrong place.

- `ld bc,-RES_NEAR * 129` had assembled as **+258**. The scan started two rows and
  two columns *inside* the footprint instead of outside it.
- So a pump could be refused at a shore and accepted on dry ground.
- rasm drops a unary minus in front of an `equ` that is defined further down the
  source. `-X`, `-X * k` and `-X + 1` all come out positive; a label is negated
  correctly.
- `main.asm` includes `terrain.asm` before `build.asm`, where `RES_NEAR` was defined.
  The uitest includes `build.asm` first, so the same source gave the right bytes
  there.
- No other unary minus in `src/` is in front of a symbol defined later. The two
  that exist, `-DIRTY_BUD` and `-WORLD_W`, are defined higher up in their own files.
- `RES_NEAR` is in `const.asm` now, which every build includes first. The script and
  the new test both run on `main.sna`.

Three tests catch that bug.

- `test_map.py` would have stopped the commit: the pump said yes on dry ground.
- `test_power.py` catches it only since this milestone. When the colony it builds
  could not be set up, it printed `ΛΑΘΟΣ` and exited 0, so it passed with the pump
  refused. The failed setup now fails the test.
- The new `test_terrain.py` catches it too.

**What the planted faults found.** Eighteen faults were run against the script and
seven tests: `test_build.py`, `test_needs.py`, `test_map.py`, `test_power.py`,
`test_balance.py`, `test_game.py` and `test_sim.py`. The script caught all eighteen.

Five passed every test, as the tests stood before this milestone:

- deep water not counting, only shallow;
- `bd_nres` left as it was on the "found" and "nothing needed" exit. The panel only
  reads it on a refusal, so nothing showed it;
- the kind never tested. Through `bd_check` the zero flag always arrives set, so
  `jr nz` never jumps, and the domes' and links' parameters are never 3 or 4.
  Only a direct call shows it;
- the scan one column short;
- the scan stepping back two columns but no rows.

The last two fail in `test_power.py` now, through the same fix as the sign bug
above. `test_map.py` checks one shore, one foot of a vein and one spot away from
each. A search that is off by a row or a column can still give the right answer at
all four.

`tests/test_terrain.py` calls `bd_res` directly in `main.sna`:

- 1,200 calls on three planes: the uitest's world, the game's, and a synthetic one
  with the near misses above;
- every kind in the catalogue, at sizes from 1×1 to 8×8;
- checked against the rule of this section written in Python, `A` and `bd_nres`,
  with `bd_nres` starting from garbage;
- the two worst searches in the catalogue may take no longer than this milestone
  measured: the mine with no vein, 1,021 µs, and the pump with no water, 818 µs,
  each with the probe's own setup.

It catches all eighteen faults, and the sign bug. There are three negatives: deep
water not counting, the row stepping 127 bytes, and `bd_nres` left alone on the way
out. With the old file every answer is right, but both timings fail (2,579 and
2,185 µs), and the negatives look for the new code's instructions.

#### Smaller and faster, at milestone 69

`src/stock.asm` went from 58 bytes to **53**. `ec_make` is 3.7 % faster and
`ec_add_stock` 1 %, over 750 calls each with interrupts off, and no call got slower.

- **`ec_make`'s mask is `#80` rotated n + 1 times**, with `rlca` and `djnz`.
  - The old loop shifted a 1 with `sla c` and counted down `A` with a test for zero
    in front, so it cost 24 T-states a step against 17 now.
  - n is the stock & 7, and the stock goes to `C` for the add that follows.
- **`ec_add_stock` has no `or a` before its `sbc`.**
  - The `add hl,bc` in front of it leaves the carry clear whenever stock plus
    quantity stays under 65,536.
  - It always does in the game: a stock is at most `EC_CAP` (600). The largest
    quantity is a cycle of pumps and mines, a few hundred.

The check was a script kept out of the repository, on the game's own binary,
`build/main.sna`. It made 1,500 calls of `ec_make` and `ec_add_stock` over all
fourteen stocks, with quantities at and around the cap and random ones up to 64,236.
Stocks were random, at the cap, above it and below it, and `EC_PRODM` was random too.
It also called `ec_stock_ptr` for every `A`. After each call it compared the 28 bytes
of stocks, `EC_PRODM`, `A`, `F`, `BC`, `DE` and `HL`.

All 1,756 calls were identical with the old file and the new one except one.
Eighteen calls had stock plus quantity above 65,535, which is outside the game. In
one of them the old code stored 259 and the new one 258. The right answer was the
cap, 600, and neither gave it: the sum had already wrapped.

**What the planted faults found.** Fifteen faults were run against the script and
seven tests: `test_sim.py`, `test_game.py`, `test_fit.py`, `test_needs.py`,
`test_hud.py`, `test_balance.py` and `test_power.py`.

- **`test_sim.py` caught every fault but one.** It runs a whole economy against
  `tools/econ.py`. For half of the faults it was the only test that noticed.
- **The one it missed was `ec_make` without its `and 7`.** For stocks 8–13 that
  gives the same bit after eight more turns of the loop, about 40 µs later.
  Nothing timed `ec_make`.
- **The script missed the same one, and a second.** It sent `ec_make` only odd stocks,
  because it alternated the two routines on the parity of its counter and there are
  fourteen stocks. So `cp 9`, which marks stock 8 in the wrong byte, passed it.
  `test_sim.py` caught that one. The script now gives both routines every stock, and
  that is how the run above was made.

`tests/test_stock.py` checks the three routines on `main.sna`:

- 336 calls over the fourteen stocks, against the rule written in Python: the capped
  add, the `EC_PRODM` bit, and every other stock left alone;
- `ec_stock_ptr` for each stock, with `HL` kept;
- `ec_make` for each stock may take no longer than this milestone measured, 99 to
  134 µs with the probe.

It catches all fifteen faults, the slow one included. There are three negatives: the
mask starting from `#01`, a cap of 599, and `ec_stock_ptr` without its ×2. With the
old file every answer is right, but all fourteen timings fail, by 1 to 8 µs.

### 6.6 Needs

Six per colonist, decaying on the wheel: **oxygen, water, food, sleep, health, morale.**

- **Oxygen is a flow, not a journey.** Anyone inside the colony breathes its air: if
  `o2_ok`, oxygen refills; if life support is short, it drains and health follows fast.
  Nobody walks anywhere for it.
- **Only inside** (milestone 87, `F_INDOORS`, [§6.2](#inside-and-outside--milestone-87)).
  Outside — at the ship, on the ground, at a structure or a site — a colonist breathes
  from the **suit**, which empties: ten minutes at the start, three a trip, and death
  the moment it is empty ([below](#suits-at-milestone-90); until milestone 90 the suit
  never emptied, the user's interim rule). The colony's oxygen demand is two per
  colonist *inside*, not two per colonist alive. Water, food and sleep decay
  everywhere, as before. **And no room gives anything to someone outside** — the
  only way to stand at a dome from outside is at its site.
- **Bots have none** (milestone 92, [§6.1](#colonists-and-bots-at-milestone-92)). The
  pass visits ids 0–79 and stops; the bots at 80–95 do not eat, drink, sleep or
  breathe, and the oxygen demand does not count them. **Until then the pass visited
  every agent under 96, whatever its role**: a bot breathed the colony's air, grew
  hungry, thirsty and tired, walked to the canteen and the quarters, and could starve
  — only the suit asked the role ([below](#suits-at-milestone-90)). §15 said bots
  did not breathe, eat or sleep; the code had never done it. A slice of eight bots now
  costs 15 µs instead of 2,752, and a slice of colonists one µs more
  (1,481 → 1,482, the test of the slice's first id).
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

#### The oxygen step, at milestone 87

Inside, the oxygen step is one addition: decay by one with a floor at zero, then the
flow's +2 capped at 255, is `o2 + 1` — except at zero, where it is 2. The pass reads
`EC_O2OK` **once per slice**, not once per colonist: it writes the address of one of
two entry points, `nd_ok` or `nd_def`, into its own `call` (as `hmc_call` does in the
HUD), and each colonist then does only the inside test. The caller hands the flags
over in `E`, read by the alive test it already did.

Measured, the needs slot with **every** colonist inside (the worst case) went from
**2,649 µs at milestone 86 to 2,607** — the extra test paid for, and some. Written
the obvious way, the flag test in front of the old two steps, it was two more tests
per colonist and 92 T-states more than milestone 86 on the worst path.

The flow pass counts the living and those inside in one loop unrolled by eight
(`en_count`, `src/door.asm`): 11½ µs a colonist where the old loop, counting the living
alone, was 12, and the balance slot went from **1,766 µs to 1,582**.

#### Suits, at milestone 90

The user's rules, three of them standing since milestone 85 and three asked for
here: **ten minutes of air at the start** (the four beside the ship), **three a
trip**, **death the moment the suit is empty** — no health lost on the way; a
colonist down to **one minute drops the job and walks to the nearest airlock on
their own**, and dies only if none can be reached; the suit is **refilled on every
exit, free** — breathing inside is already paid for by the colony's oxygen; and the
alert line says **`SUIT AIR LOW`** while anyone outside has less than a minute. Robots
(roles 5–7) do not breathe.

**A unit is two needs visits.** A colonist is visited every 64 frames (96 in three
slots of eight, [§7.2](#72-the-wheel)), and ten minutes are 469 visits — not a byte.
So the suit empties on every *second* visit, and which one is a bit in the colonist's
own flags (`F_SUITPH`, 64): no counter that has to turn with the wheel, nothing for
anyone inside. One unit is 128 frames, 2.56 s; the agent field `skill`, which nothing
had ever read, is now `suit`:

| | Units | Time |
|---|---|---|
| `SUIT_START`, the four at the ship | 234 | 9:59 |
| `SUIT_TRIP`, every exit, every birth at the pad | 70 | 2:59 |
| `SUIT_LOW`, turn back | 23 | 0:59 |

**Where it lives.** `src/suit.asm`, 187 bytes in bank 2. The needs pass sends an
outside colonist to it instead of the oxygen step — `jr nc,nd_out`, and `nd_out` is
one `jp su_tick` — and `su_tick` ends with a `jp` too: to `nd_die` when the suit is
empty, otherwise to `nd_load`, having done the water, food and sleep decay itself.
On the *half* visit it only sets the bit (9 µs to the decay); on the other it reads
the role, takes a unit, and at `SUIT_LOW` or below sets the alarm and, unless the
colonist is already on `T_NEED`, asks `su_lock` for the nearest active airlock
(`DIST`, the first structure on a tie) and writes it as the destination with
`T_NEED` — "my own need", which the board leaves alone ([above](#their-own-needs-outrank-the-board)).
Outside, the satisfied branch no longer clears `T_NEED`: there it means "going in",
and clearing it would hand the colonist back to the board, the suit would send them
back, and the two would take turns until the suit ran out — milestone 28's
oscillation, in a new place. The first visit **inside** clears it as before.

The fill is one store in `emd_put` (`src/entity.asm`), where a departure leaves
`F_INDOORS` behind: whoever steps out of an airlock has `SUIT_TRIP`, however much was
left. `sh_born` gives a newborn at the pad the same, `game_new` gives the four
`SUIT_START`, and `lk_air_out` (`src/door.asm`) puts those standing in an airlock a
meteor has knocked back to a site outside with a full suit, and marks them to be drawn
([§6.10](#610-events-and-hazards)). Since milestone 104 it also does this for those in
the tube on the way to it ([§6.2](#who-was-in-the-tube-at-milestone-104)).

**`su_lock` walks a page.** The structure table is 32 × 8 = 256 bytes at `&7B00`, so
the pointer sits on `ST_KIND` and steps with `add a,8 · ld l,a · jr nc`: 13 µs a
structure that is not an airlock, and the node comes from `L` only when one is. With
`IX` and `add ix,bc` it was 25 µs and **800 µs** a call; it is **451** with no airlock
and 511 with one. It runs once per colonist per trip, when the suit first reaches a
minute, and again every 128 frames only while no airlock can be reached — at the
start, before one is built, four colonists at once: 1.8 ms on that slot every 128
frames, under the room index's 4.7 ms.

**The alert line.** `su_tick` sets `su_alarm` to 10 on every visit that finds a suit
at a minute or less, and `su_hud` counts it down at the top of `hud_alert`, on every
HUD tick, whatever the line then says. `SUIT AIR LOW` sits after `NO OXYGEN` and before
`LOW POWER`: below what kills everyone, above what kills in sols. The first version
counted only when the line got that far, so under `NO OXYGEN` the count stood still,
and when the oxygen came back the line said `SUIT AIR LOW` for whoever had gone in a
minute before; `tests/test_suit.py` has that as a negative.

**What it cost, and what paid.** In the pinned wheel of [§7.2](#72-the-wheel), the
needs slot:

| Needs slot | Milestone 89 | Milestone 90 |
|---|---|---|
| the ordinary run (half outside, standing at domes) | 1,748.2 µs | **1,684.3** |
| everyone inside | 2,591.9 | **2,585.8** |
| everyone outside, walking | 2,223.2 | 2,375.2 |
| everyone outside, standing at domes | 2,935.2 | **2,375.2** |
| eight per slot, everyone dead | 290.0 | 290.0 |

The suit costs about **19 µs a visit** to someone walking outside: the bit, and on
every second visit the role, the unit and the minute. What paid for it is a jump:
`call su_tick`, its `ret` and the `jp z`/`jr` after it were 15 µs where two `jp`s
are 6, and **outside the `nd_sat` test is skipped** — 13 µs walking, 21 at a
structure. Inside nothing changed
but a redundant `ld l,a` (the slice's loop already leaves the id in `L`), and the
slot's worst case is still everyone inside, 2,585.8 against 2,591.9.

**And skipping it fixed something.** `nd_satisfy` never asked whether the dome is
finished, and since milestone 87 a dome's builder stands at its site, outside — so a
colonist building quarters slept there, and one building a canteen ate from the store
at it. Outside no room gives anything now (`tools/entity.py` says the same, and
`tests/test_sim.py` compares every byte); `tests/test_suit.py`'s site scenario sets
the builder of a quarters site to sleep 10 and fails on the old jump with 255.

**Measured.** `tests/test_sim.py` puts 42 colonists outside in ten cases — one unit
left, the minute, robots, no airlock in reach (nodes 90–91), three airlocks at
different distances, leaving through one — and runs 640 wheel ticks (40
revolutions) against the reference: Z80 and Python agree to the byte; three die (only those with one unit),
seven walk into an airlock, none from 90–91, seventeen robots untouched, five leave
with a full suit. Four negatives disagree: the suit emptying every visit, no airlock
found, `T_NEED` cleared outside, no fill on exit. `tests/test_suit.py` runs the game:
the start (234 units, one per 128 frames to within two, nobody moves without an
airlock, the line silent until someone is under a minute, death at zero with health
255 to the end), a trip (out with 5, on the ground with 70; back at a minute to the
airlock, in, alive, available), the meteor, the site, and milestone 90's other fix,
below. Seven negatives. Milestone 104 added the tube, the random calls of `lk_air_out` and
the cost of an impact on an airlock ([§6.2](#who-was-in-the-tube-at-milestone-104)), and
four negatives.

**The pad was being looked for in the corridor table.** `rooms_rebuild` finds the
landing pad by scanning the structures, and the scan counted **64** of them: the
second 32 records were the corridor table, read eight bytes at a time. Any corridor
whose bytes fell on `ST_KIND` = 6 (`K_PAD`) and `ST_STATE` = 2 — corridor 0, finished,
with direction 6, for one: `C_DIR` sits exactly where `ST_KIND` would — became the pad
at a node from 96 up, which does not exist, in any colony without a pad (every new
game, until one is built); and without one the scan read all 64 every revolution.
It is `MAX_STRUCT` now; `tests/test_suit.py` plants that corridor 0 and fails with
the old count.

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
| Build | a construction site **whose materials have all arrived** (milestone 88 — [§6.9](#built-at-milestone-88)), or a structure a meteor knocked down; a dome in use with a fitted machine whose materials have arrived, which it installs (milestone 99, [§6.9](#machines-carried-at-milestone-99)) | engineer, constructor bot |
| Supply | a construction site still owed Metal or Bioplastic, one job per material (milestone 88, [below](#supply-at-milestone-88)); a machine fitted at `FIT`, one job per material per dome, shared with the dome's site (milestone 99) | anyone: every colonist, carrier bot |
| Trade | a deal with the merchant: two jobs at the pad that carry its goods both ways (milestone 98, [§6.11](#carried-at-milestone-98)) | anyone: every colonist, carrier bot |
| Operate | a machine with inputs and no operator | worker, biologist (greenhouse) |
| Haul | a mine whose pile holds a load of Ore (milestone 95, [below](#hauling-at-milestone-95)); a machine short of input, not yet | worker, carrier bot |
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

#### Smaller and faster, at milestone 70

`src/jobpost.asm` is `jb_post_build`, the Build job that `build.asm` and the meteor
post. It went from 32 bytes to **27** and is 6.1 % faster over 412 calls, with no
call slower.

- **`inc (hl)` asks and answers.** A free slot's kind is `NO_JOB`, 255, and
  255 + 1 is 0, which is `J_BUILD`. So the slot is claimed and its kind written in
  one instruction. A taken slot gets `dec (hl)` back. Nothing can see the moment in
  between: until milestone 83 interrupts were off, and the handler that runs since then
  never reads the job board.
  - The node stays in `A` instead of going to `C`.
  - The record step is loaded into `DE` once, before the loop. It used to be loaded
    on every pass.
  - `D` = 0 is the record's last byte.
- **The constants are `assert`ed:** `NO_JOB` = 255, `J_BUILD` = 0, and a record
  under 256 bytes.

The check was a script kept out of the repository, on the game's own binary,
`build/main.sna`. It used 412 tables:

- empty and full;
- the first free slot at each of the 32 positions;
- random ones.

The other bytes of every record were random. It compared the whole table and,
after the planted faults showed why, 32 bytes on each side of it. All 412 were
identical with the old file and the new one.

**What the planted faults found.** Eleven faults were run against the script and
seven tests: `test_build.py`, `test_game.py`, `test_meteor.py`, `test_sim.py`,
`test_needs.py`, `test_balance.py` and `test_fit.py`.

- **Two passed every test.**
  - The last slot, 31, never used.
  - A full table falling through into the write, which puts the Build job in the
    five bytes after the table. The script missed this one too, because it only
    compared the table.
- **Four more were caught by `test_sim.py` alone:** the record step one short, the
  "unassigned" byte, the priority and the last byte.
- The tests build a few things, or drop a meteor, on a table with a handful of jobs
  in it.

`tests/test_jobpost.py` calls `jb_post_build` on `main.sna`:

- 106 tables: empty, full, the only free slot at each position, the first free slot
  at each position with more after it, and random ones;
- checked against the rule: the first free slot becomes `[J_BUILD, node, 255, 5, 0]`
  and nothing else changes, inside the table or 64 bytes either side of it;
- the post at slot 0, at slot 31, and the full table may take no longer than this
  milestone measured: 47, 512 and 502 µs with the probe.

It catches all eleven faults. Its three negatives are the `ret` after a full table,
31 slots, and no `dec (hl)`. With the old file every table is right, and all three
timings fail.

**At milestone 88 `jb_post_build` moved to bank 2** (`src/supply.asm`; `jobpost.asm`
is gone), the same bytes but the last: the new job's `site` is its node, not 0. The
test's rule changed with it, and its three timings are still 47, 512 and 502 µs.

#### Supply, at milestone 88

The job that carries a site's materials ([§6.9](#built-at-milestone-88)). It is the
first job with **two destinations**, and it gets them without a new field: the fifth
byte of the record is the job's own node — the site — and `node` is where its agent is
going. Every other job has the two equal.

1. **Taking it** (`jb_take`, then `sp_take`): the agent is sent first to the nearest
   **source** — measured from where *he* stands, by `DIST` — among the ship (structure
   0, when it is the ship) and the Storage domes in use (the room index, up to eight).
   A source he cannot reach does not count; with none at all he goes straight to the
   site and the load counts as in hand. That happens only in the test colony, which
   has no ship. His `spare` is cleared: he carries nothing yet.
2. **At the source** (`jb_arrive`, then `sp_arrive`): one load — `spare` is the stock he
   carries, Metal or Bioplastic — and `node` and his destination become the site. The
   job stays his.
3. **At the site**: the load is delivered. If that material is still owed the job
   opens again (like a repair that found no spare part); if not, it ends, and if the
   site owes nothing at all, **its Build job is posted**.

If he drops it on the way — hunger, death, a route that does not exist — the reap
gives the job back to the board and copies `site` into `node`. That one copy is right
for every job, so it is not even asked which kind it was. The load he was carrying is
lost and the site is still owed it; nothing comes out of the stocks twice, because the
cost left them at placement.

**One job per material, so one carrier per material at a time.** A solar panel's two
loads are two trips by one colonist; a small dome's Metal and Bioplastic go at once,
by two. More hands would mean more jobs per site, and the board has 32 entries
([§15](#15-open-risks)).

**Priority 4**: under Build (5), so an idle engineer builds before he carries, and
under the canteen and life support's Operate (5); level with the greenhouse, lab and
medbay. **Roles `#5F`**: worker, engineer, biologist, medic, guard and the carrier
bot — everyone but the constructor and driller bots.

**The board's own slot got faster, not slower.** Asking "is this a Supply?" in
`jb_take` and at arrival cost the pinned job slot 0.2 µs on average, and two changes
took more than that back: the reap, arrival and "any job open?" loops test for an
empty entry with `inc a` instead of `cp NO_JOB` (3 T-states each, 32 entries, every
visit), and arrival asks an Operate job two questions instead of three (`or a` for
Build, then one `cp J_REPAIR` for repair-or-supply). `jb_take` asks its question as
it reads the record and answers it at the end, because nothing in between touches the
carry. **Slot 13: 4,323.6 → 4,228.2 µs** in 10 µs steps ([§7.2](#72-the-wheel)).

#### Drilling, at milestone 94

**Until this milestone a mine with power made 2 Ore a cycle with nobody in it**, and
the Drill job was a row in [the table above](#67-jobs) — workers and driller bots,
priority 4 — that nothing posted; the bots of milestone 92 were never drillers for
that reason. The player's decisions:

- **As in Planetbase**, where a mine takes up to three workers or driller bots, at
  100, 150 and 200%.
- **One at work makes what the mine made alone**: none 0, one 2, two 3, three 4 Ore a
  cycle of the flow balance, with power; its 8 Power is drawn either way. (Since
  milestone 95 into a pile at the mine, [below](#hauling-at-milestone-95).)
- **A new bot is a driller while the mines have places without one** — three each —
  and a constructor or a carrier by its slot otherwise, as at milestone 92.

**Who digs is counted on the mine**, in the seventh byte of its record (`ST_OPS`),
which only airlocks used (`ST_JOINED`). It goes up when someone arrives with Drill —
`ja_oper`, which gives the dome its operator — and down when they leave or die,
the same three places that keep a dome's `D_OPS`; they share `op_ptr` now (dome or
structure, `src/jobs.asm`, 21 bytes that the three callers paid for). Those who
arrive stand at the mine with `F_WORKING`, outside: a bot stays for ever, a colonist
until the suit sends them back ([§6.6](#suits-at-milestone-90)) — **people drill in
stretches**, which is what the drillers are for.

**The Drill job is posted from the flow balance**, which already visits every finished
mine once a cycle (64 revolutions, and at once when a building finishes): a mine
with fewer than three gets one job — node 64 + structure, priority 4 — in the first
free entry, through the same `jp_have` as the board's own posting, with or without
power. Not from slot 13, the heaviest of the wheel, which would have paid for the
look every revolution. The search of the 32 entries costs ~900 µs, and a mine with
one worker paid it every cycle to find its job already there; so **bit 7 of
`ST_OPS` says the job exists**: `dr_post` sets it, the arrival clears it, and a Drill
job leaves the board only at an arrival, so the bit cannot lie. With the board full
nothing is set and the next cycle tries again.

**The cycle counts the mines** (`EC_MINES`, the economy's 107th byte), and `dr_need`
reads it when a bot wakes: places are three a mine, less the living drillers. A
scan of the 32 structures there made a waking 1,412 µs instead of 715. It is 20 bytes
in `b6code`, which took the last 18 of the gap under it
([§4.2](#code-in-bank-6-at-milestone-92)); with no mine it returns before looking at
the bots.

| | 93 | 94 |
|---|---|---|
| the flow cycle, no mine | 1,787 µs | **1,577** |
| the flow cycle, three mines (0, 2, 3 at work) | 2,065 | **1,941**; 3,841 on the cycle that posts two jobs |
| slot 12 between cycles; slot 13 | 684; 2,841 | 684; **2,763**, below |
| a bot waking in the second factory, no mine (`test_bots.py`) | 715 | 733 |
| a bot waking, one mine | 699 | 918 |

The cycle came out cheaper because the empty structure slots, most of the 32, stopped
paying a `push bc` / `pop bc` each; with the mines' checks that paid for them twice
over.

**The job board had to learn to skip people.** A Drill job stays open while its mine
has a place and no worker comes, which with people drilling in stretches is most of
the time. The assignment (slot 13) looked at its 32 agents whenever *any* job was open
and ran `jb_best` — the 32 jobs, ~1 ms — for every idle one, whatever their role: with
drilling the identity run of `tests/test_sim.py` went from 70 frames to 100, its slot
13 from 363 ms to 982 over the 640 ticks, with ticks of 20–42 ms in nearly every
revolution. Now the pass over the board that asked "any open?" collects the roles that
have an open job (`jb_open`, a mask of `job_roles`, in bank 2 beside `dr_post`), an idle
agent whose role is not in it costs an `and`, and `jb_best` runs only for one who will
find something — the same results, since `jb_best` turns nobody down for anything but
the role. After each assignment the mask is taken again (~500 µs, at most four times;
a mask corrected on a failed `jb_best` instead measured 361 ms against 314), and with
none left the assignment stops. That pass no longer stops at the first open job, which
cost ~450 µs when one is open; the agents' loop paid for it, with the agent in a
register and the dead and the busy skipped in ~70 T instead of ~155.

| slot 13 (`test_drill.py`, the test colony, `rep94/c13.py` for 93) | 93 | 94 |
|---|---|---|
| no open job | 2,841 µs | **2,763** |
| a Drill nobody takes, nobody idle in the window | 3,864 | **3,446** |
| the same, the colony's four idle in the window, of other roles | 6,117 | **3,555** |
| the same, an idle worker takes it | 8,384 | **4,539** |
| `test_sim.py`, pinned (200 calls) | 4,293 | **3,694** |
| `test_sim.py`, identity run: a whole revolution; slot 13 over 640 ticks; its worst tick | 34,944; 363 ms; 40.3 ms | **32,947; 292 ms; 13.6 ms** |

**What the planted faults found.** `tests/test_drill.py`: the tables against the prose
and the reference; a cycle with four finished mines at 0–3 and a mine site, with power
and without, against `tools/econ.py`'s `flow_cycle` byte for byte — Ore, `EC_MINES`, the
board, the structures — no second post, nothing with the board full; who wakes, in six
states against `bot_tick`; and in the running game a mine on the vein beside the test
colony, built by the engineer, a worker arriving, the Ore a cycle for each number at
work, the suit sending them back, someone dying there, and a driller bot that comes and
stays. Sixteen faults, each caught: no posting, mines uncounted, Ore with nobody as in
93, one making 1, four at a mine, no bit 7, the bit never cleared, arrival, leaving and
death uncounted, the count in the eighth byte, never a driller, dead drillers counted,
one place a mine, the assignment without the mask (slot 13 over its ceilings) and a mask
that collects no role (nobody ever arrives). `tests/test_sim.py` gives every mine of its colony one at work and
compares the structures after every movement slice.

#### Hauling, at milestone 95

**Until this milestone the flow balance put a mine's Ore straight into the stocks**,
and Haul was a row in [the table above](#67-jobs) — workers and carrier bots,
priority 2 — that nothing posted, as Drill had been until 94. The player's decisions:

- **The Ore stays at the mine**, in a pile of at most **30**, three loads. A full
  pile stops the mine however many dig there, until someone carries.
- **Loads of 10**, as Supply's; a Haul job is posted when the pile reaches 10.
- **To the nearest Storage dome in use, otherwise the ship** — Supply's sources,
  chosen by the same `sp_take`.
- The merchant's goods are still delivered instantly; carrying them to the pad is for
  later ([§15](#15-open-risks)). Milestone 98 did it ([§6.11](#carried-at-milestone-98)).

**The pile is the eighth byte of the mine's record** (`ST_OWED`), which a site uses for
the loads it is owed and a finished structure never used; **bit 6 of `ST_OPS` says the
Haul exists**, beside bit 7 for the Drill and the two low bits for who digs. A mine a
meteor knocks down is rebuilt with a Build job and no Supply
([§6.10](#610-events-and-hazards)), so nothing reads the byte as owed loads, and the
pile is there again when the mine is.

**The pile fills in the flow balance's own scan** (`hl_pile`, `src/haul.asm`, 47
bytes in bank 0), for each finished mine after its Drill: with power and someone
digging, the 2, 3 or 4 of [above](#drilling-at-milestone-94), up to 30; with or
without, a pile of 10 or more and no bit 6 gets a Haul — node 64 + structure, through
`st_post`, the poster `dr_post` became (`src/drill.asm`, 33 bytes with it). **"With
power" is the last balance's verdict**, the `EC_POK` that slot 11's machines and
gardens already read, not the one this scan is about to make. The first version
waited for this cycle's verdict, as the Ore had until 94, and searched the 32
structures again after it for the mines: 13 µs for every slot up to the last mine,
~400 with one in slot 31, and the three-mine cycle 1,941 → 2,108 µs. In the scan it
costs the mines there are, ~55 µs each, wherever they stand in the table; and the
empty slots, most of the 32, stopped reloading `DE` with the record's size (3 µs
each), which paid for the rest:

| `tests/test_drill.py`, the test colony | 94 | 95 |
|---|---|---|
| the flow cycle, no mine | 1,577 µs | **1,472** |
| the flow cycle, three mines (0, 2, 3 at work) | 1,941; 3,841 on the cycle that posts two Drill | **1,834; 3,799** |
| the same, the mines in the table's last three slots | 1,941 | **1,834** |
| slot 12 between cycles | 684 | 684 |

**Two legs, as Supply's but the other way round** (`hl_arrive`, 80 bytes in bank 0,
from the arrival of [the job pass](#67-jobs)). The job is posted with `node` = `site` =
the mine.

1. **At the mine**: bit 6 clears, 10 leave the pile, and `sp_take` picks the
   destination from where the agent stands — the mine — as it picks a Supply's
   source; `node` and their destination become it, and `spare` is Ore. The job stays
   theirs. A pile under 10 — not possible while one Haul exists per pile — ends the
   job with nothing taken. With no destination they can reach, the load is delivered
   there and then.
2. **At the destination**: +10 Ore through `ec_make`, so it counts as made in the
   colony for Independence ([§10.2](#102-milestones)), `spare` 0, and the job ends.

`site` stays the mine, so the arrival knows which leg it is on. **A load dropped half
way is not lost**: the reap gives a Haul back to the board without copying `site` into
`node` (the one kind for which it does not, until milestone 98 made the merchant's
`J_TRADE` the second), so the next taker goes straight to the
destination and delivers it. Slot 13 with a Haul arriving: 322 µs over the same visit
with no job at the mine, 255 at the destination (`tests/test_haul.py`).

**Priority 5, above Drill's 4** — the one decision here that was not the player's. With
the table's 2, a colony with few workers put them all on the Drill, the pile reached 30
and stayed there, and the mine stopped for good with its drillers at work. At 5 an idle
worker carries first; level with Build and the canteen's and life support's Operate.

**What the planted faults found.** `tests/test_haul.py`: the tables against the prose
and the reference; a cycle with five finished mines — 0 + 2, 8 + 4 = 12, 29 + 3 capped
at 30, 15 with the bit, 30 full — and a site owed 0x21, with power and without, against
`flow_cycle` byte for byte, Drill and Haul posted structure by structure, no second
post, nothing with the board full; slot 13 in the test colony — loading with the ship
as the destination, loading with none and delivering there, a pile under 10, delivery
at the ship, a loaded carrier dying (the Haul stays open towards the ship, a Supply
goes back to its site as at 88), and a free worker with a Haul and a Drill open at the
same mine taking the Haul; and in the running game a mine built on the vein, a Haul
once its pile reaches 10, a worker loading it and delivering to the ship with the Ore
up by 10, then a carrier bot doing the same. Eleven
faults, each caught: `hl_pile` not called, Ore without power, no cap, the Haul without
bit 6, the Drill seeing bit 6, the bit kept at loading, loading that takes nothing from
the pile, delivery that makes no Ore, never a destination, the reap sending a loaded
Haul back to the mine, and the Haul at 94's priority. `tests/test_sim.py` found that
its colony's mines had never been reachable — its graph had no structures — so no one
had ever arrived at one there; now they are linked to its domes, and the run found a
bug in the reference's mine arrival that the Z80 did not have. Its colony is not the
same one any more, so its numbers moved: a whole revolution reads 28,954 µs against
32,947, and the needs slot pinned 1,797 against 1,697. That is the graph, not the
code: milestone 94's code on the new graph pins the same 1,797, and on either graph
all seven pinned slots are equal in both, to the microsecond.

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
| Airlock | `airlock` | — | unused: the airlock is a structure since milestone 86 ([§6.2](#62-the-node-graph)) |
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
- **So is a dome, since milestone 94** (the player: *no foundations under the
  domes*): its ground, the resource bit and the decor stay, and only the occupancy
  goes down. Structures still become foundation.
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
  **Milestone 85 checks more than that, on every cursor step**: a building after
  the first needs another within 12 tiles, a dome takes a corridor to every dome
  a corridor reaches, and sites count — the dome to connect to need not be built
  yet ([§9.3](#every-building-needs-a-neighbour-at-milestone-85)).
3. Engineers and constructor bots walk there and work. Progress is a byte.
   **Built, and the byte is the integrity byte** — `bd_commit` writes integrity 0
   and each visit adds 32, so eight visits (≈2.6 s) finish it. A half-built
   building and a half-wrecked one are then the same state, which is right and
   saves a byte per node. **A construction site also gets an edge**: without one
   the routing finds it unreachable, nobody ever sets out, and it stays
   `DS_BUILDING` for ever. It is linked to the nearest live dome — an *outdoor
   edge* in [§6.2](#62-the-node-graph)'s sense, one with no corridor to draw it.
   **Since milestone 85 the edges are the corridors and the path that the ghost
   showed** (`al_commit`); the first building in an empty world has none, and
   [§15](#15-open-risks) says what that means.
4. On completion the object is drawn — and this is the expensive moment: **5.7 frames
   for a large dome** ([§2.2](#22-the-frame-budget)). It is split into 8 chunks, one
   quadrant per frame, in the order of `assets/SPRITES.md` §8: rings, domes, connectors,
   room icon, machines, slots. The dome appears over about a sixth of a second, which
   reads as materialising rather than as a stall.

   **As built, completion is not the expensive moment — placement is, and completion
   is one dirty-list item.** The site is drawn when it is placed (rings, dome,
   connectors until milestone 96, the empty-room icon — step 2's first bullet), so
   when it finishes only
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
   over the shell it is what the full pass draws. Since milestone 96 they are joints,
   pushed the same way, and the box takes the half tile a centred corridor needs
   ([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)).

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
   corner of the dome. `tests/test_link.py` samples the reveal and counts bytes
   that had their final value and lose it: **13** in the worst frame (a door
   re-covered for a moment by the corridor under it), **96** with the terrain put
   back. Since milestone 80 it samples four times a frame, and reads **18** and
   **96**, on milestone 79's binary as on 80's. Once at the end of each frame saw
   one phase only. Milestone 80 reached the press a little differently — two
   `SPACE`s to the build menu, and a `LOOK` tick 21 µs cheaper. After that the
   bare ground fell between two samples, and the negative read 18, the same as
   the positive. A dome *does* change the tiles — its foundation — and keeps
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

#### Materials first, then an engineer — planned at milestone 86

**Decided with the user after milestone 86, built at milestone 88**
([below](#built-at-milestone-88)). Until then the cost left the stocks at placement
and the site waited only for an engineer's eight visits; nothing was carried. The user's rule: *a building
needs an Engineer, who has to go outside and walk to it — and before that its
materials have to get there, carried by anyone.* That is also how Planetbase works:
Engineers and Constructor bots build, and the materials are carried to the site
first.

A site goes through four states:

1. **Placed.** As now: milestone 86's rule, the payment, the site on the map. The
   cost still leaves the stocks **at placement** (the user's choice): the HUD shows
   it at once, there is no second set of "reserved" stocks to keep in step (the reason
   the first bullet above gives), and the site keeps what it is still **owed**. A
   cancelled or destroyed site gives back whatever was not yet delivered.
2. **Supplied.** The site posts a **Supply** job per material it is owed, at most two.
   *Anyone* takes it — every colonist and the carrier bots. A trip has two legs: to the
   nearest source (the ship's cargo, outside, at the start; Storage domes once there
   are any), then to the site, with **one load of 10 units** of one material (the
   user's choice). A solar panel (15 Metal) is 2 trips, a small dome with its machine
   (20/10) 3, a large dome with its corridors about 10. The job stays open until the
   last load arrives.
3. **Built.** Only then is the Build job posted, and only an **engineer or a
   constructor bot** takes it (the user's choice); the eight visits of +32 integrity
   are unchanged. With no engineer alive the site waits and the HUD says
   `NO ENGINEER`.
4. **Done.** Its corridors become walkable from inside only now — they are part of the
   construction.

**A site has no air, so it is reached from outside — built at milestone 87**
([§6.2](#inside-and-outside--milestone-87)). A structure's site already is, by its
path. A dome's site gets a ground link to the nearest airlock or the ship instead of
its corridors, and loses it when it is done; its corridors become edges then, and its
builder is put outside. Everyone who carries or builds therefore leaves through an
airlock, and the suits apply to them (milestone 90, [§6.6](#suits-at-milestone-90)).

**Where the bytes go.** No new tables: a dome that is being built does not use
`power` or `ops` yet, and a structure does not use `output` — they hold the loads
still owed. The load an agent carries goes in its `spare` byte. The code is an
estimate, 300–450 bytes, not yet measured; since milestone 87 bank 0 has 746 free
(42 under the tests' stubs) and bank 2 607, and
`jobs.asm` is already the wheel's heaviest slot ([§7.2](#72-the-wheel)), so whatever
it costs there has to be paid back. `NO ENGINEER` comes out of bank 7's 63 spare
bytes, because the text block is full.

**The order:** milestone 87 inside and outside in the graph, and the start beside
the ship with its cargo outside — **done** ([§10.1](#101-start-state)); **88** this
section — Supply, Build only by engineers, `NO ENGINEER` — **done** (below); **89**
the colonists drawn outside ([§6.3](#seen-outside-at-milestone-89)) and **90** the
suits ([§6.6](#suits-at-milestone-90)) — **done**. Machines fitted inside domes follow
the same rule since milestone 99 ([below](#machines-carried-at-milestone-99)).

#### Built, at milestone 88

`src/supply.asm`, 354 bytes in bank 2, and the job board's half of it in
[§6.7](#supply-at-milestone-88). As planned, with these decisions of its own:

- **What a site owes is what it cost: the building and its corridors.** `al_plan`'s
  total — the number the panel shows and the player paid — is turned into loads of ten
  in `bd_commit`, rounded **up**: a solar panel's 15 Metal is 10 and 5, two trips. A
  large dome with four corridors of twelve tiles owes at most 36 loads of Metal and 18
  of Bioplastic. Machines fitted on a site were still paid when fitted and not carried,
  until milestone 99 ([below](#machines-carried-at-milestone-99)).
- **Where it is kept.** A dome being built has no power and no operators: Metal in
  `power`, Bioplastic in `ops`, a byte each. A structure has one free byte, the eighth:
  Metal in its high four bits, Bioplastic in its low four — the seventh is the
  airlock's `joined`. The dearest structure is the landing pad (45, no corridor) or an
  airlock with its one corridor of up to twelve tiles (82 and 42), so 15 loads is
  enough, and an `assert` in `src/link.asm` keeps it so. A dome is finished with both
  bytes back at 0, which is what `ops` must be.
- **The undelivered part is not refunded, because nothing can be undelivered.** The
  plan said a cancelled or destroyed site gives back what had not arrived. Nothing in
  the game cancels or destroys a site: a meteor takes only its progress
  ([§6.10](#610-events-and-hazards)), and a structure it knocks down is rebuilt without
  materials, by a Build job alone. When demolition comes it will need the remainder of
  the last load, which a count of tens does not keep. **It did not, at milestone 101**
  ([§9.3](#demolition-at-milestone-101)): every load was paid at placement, so a site
  taken down gives back what it cost, and the loads still owed are simply not carried.
- **Placement got faster, not slower.** Writing the loads costs `bd_commit` a few
  hundred T-states, and posting two jobs a second scan of the board. Its search for a
  free record paid for both: the dome search called `ob_dome_live`, which computes the
  record's address — a multiply by 24 — for every dome, 168 T-states each; it is now
  one walk with a pointer for domes and structures, four records per loop, 32. The
  foundation stamp keeps its mask and value in registers and steps with `inc l`.
  With the probe of `tests/test_place.py`, the worst dome placement went from
  **4,656 µs to 1,486**, the worst structure from **892 to 881**.
- **`NO ENGINEER`** is the HUD's line when a Build job waits and no engineer or
  constructor bot is alive ([§9.2](#92-hud)). It is asked once a HUD tick, after the
  food and water lines. A new byte at the end of the economy, `EC_NBUILD` (byte 91),
  counts the Build jobs on the board — `sp_build` adds one, a finished building takes
  it away, and nothing else posts or removes a Build — so with none waiting, which is
  nearly always, the question costs 26 T-states; scanning the board would cost
  ~380 µs. With one, the agents are walked to the first who can build; when nobody is
  alive, none of the jobs can be held, because the reap returns them. Making the
  economy one byte longer let `game_new` clear all of it: since milestone 38 it had
  cleared 86 of the 91 bytes, and a new game started during a meteor shower kept the
  shower.

**And the people who carried are at the site when it is done**, which milestone 87
never had to think about: only the builder stood there. A dome's site is outside, and
when the dome is finished it is sealed and loses its ground link (`lk_done`); `lk_out`
put the builder out at the anchor and left the two carriers who had just unloaded
**inside a dome with no edge**. They took the next site's Supply jobs first — they are
agents 0 and 1, and the assignment looks at its agents in order — found no route, gave
the jobs back, and took them again, for ever, while the two at the ship waited.
`tests/test_outside.py` showed it as an airlock that was never finished, and
`tests/test_needs.py` as colonists who never went to eat. `lk_out` is now `lk_each`
with a routine to call: **everyone standing at the node** — on a dome, out at the
anchor; on an airlock, `F_INDOORS`, the carriers as well as the builder (until 87,
`en_put` on the builder alone). One pass of the 128 agents with the node in `A` and the
agent in `L`, 36 T-states each, ~1.2 ms once per dome or airlock finished; whoever is
already walking away arrives as before (`lk_cut`).

Measured in the game, from `FIRE` beside the ship (`tests/test_supply.py`): the solar
panel owes `#20`, one colonist loads Metal at the ship and brings it twice (`#20` →
`#10` → `#00`), the Build job appears only then and the engineer takes it — **450
frames** from the press to a finished panel. A small dome owes 2 and 1, Metal and
Bioplastic are carried at once by two colonists, and it is finished in 450 frames with
`power` and `ops` at 0 and nobody left inside it. With the engineer made a worker the panel is supplied, its
Build job waits unassigned for 2,000 frames and the HUD says `NO ENGINEER`, which it
never said while materials were still being carried; give him his role back and he
builds it and the line clears.

#### Machines carried, at milestone 99

**Until this milestone a machine was paid at `FIT` and ran at once.** That was the last
thing milestone 88 left as it was ([above](#built-at-milestone-88)). In Planetbase the
colonists carry a machine's materials and an engineer installs it. The player's
decisions:

- **Paid at `FIT`**, as sites and the merchant's goods are. The stocks drop at once,
  and the loads are carried afterwards.
- **Materials first, then an engineer.** There is one Supply job per material, which
  anyone takes. When both materials have arrived, a Build job is posted, and only an
  engineer or a constructor bot takes it, as for a site. The user chose this over
  "the materials are enough".
- **Shown at once, stopped.** The slot is drawn at `FIT`, and the machine does nothing
  until it is installed. The user chose this over "an empty slot until the materials
  arrive". Since milestone 100 it wears a yellow and black mark until then
  ([§6.10](#seen-at-milestone-100)).
- **Plants stay instant.** A greenhouse's plants (2 Metal each) are paid and work at
  once.

**What a machine still owes is kept in its health byte**, so no byte was added. Until
this milestone the health was only ever 0 (stopped) or `MACH_HP`, 200 (running).
Production, the operator count and the malfunction now look only at bit 7. Every value
below 128 is a machine that waits:

| health | meaning |
|---|---|
| 0 | broken, withered, or an empty slot: wants Repair |
| `MACH_OWED` = 7 | new: owes Metal (bit 0) and Bioplastic (bit 1) |
| 4 + 32 × k | its materials are here: a Build installs it, `BUILD_STEP` a visit |
| `MACH_HP` = 200 | running (bit 7) |

No machine costs more than ten of either material
([table](#a-room-says-what-fits-the-player-says-what-goes-in)), so each material is
one load and one bit. When the last bit clears, the health is `MACH_READY` = 4. Four
visits take it through 36, 68 and 100, past 127, and then it is 200.

**One Supply per material per dome, shared by the site and its machines.**

- **At `FIT`**, `mc_order` (`src/supply.asm`) posts a Supply for each material, unless
  the dome already has one. The check is `sp_find`, a scan of the 32 jobs. Four
  machines fitted at once make two jobs, not eight. A site with machines fitted shares
  the site's own jobs.
- **On arrival**, a load goes to the site first, if the site still owes that material.
  Otherwise it goes to the first machine that owes it (`mc_arrive`,
  `src/install.asm`).
- **The job reopens** while the site or any machine still owes that material.
- **A dome in use owes nothing itself.** Its `power` and `ops` bytes are power and
  operators again, so `mc_live` sends a load for a finished dome straight to its
  machines.

**The Build that installs a machine.**

- **In a dome in use**, when a machine's second material arrives (health 4), a Build is
  posted for the dome, unless it already has one. It goes through `sp_build`, which
  counts it in `EC_NBUILD`, so `NO ENGINEER` covers it.
- **On a site**, no Build is posted. When the building is finished, the same builder
  goes on to its machines in the same visit (`ja_build`, `src/jobs.asm`).
- **Each visit** installs the first ready slot: a health of 4 to 127 with no material
  owed. The job stays while it finds one, and ends on the first visit that finds none.

**The builder put outside.** When a dome is finished, `lk_done` puts everyone standing
there outside, at the airlock or the ship, and the builder too
([above](#built-at-milestone-88)). Until this milestone the builder's job ended there.
Now it can go on to the machines, so the builder kept the job while their destination
stayed outside. They waited there for ever, with the machine at 36.
`tests/test_game.py` found it: its oxygen generator is fitted to the site. Every
install visit now sets the builder's destination back to the dome (6 bytes), and they
come back in through the airlock.

**Stopped means stopped.** Until its health is 200, a machine:

- does not produce;
- does not ask for an operator;
- is not a Repair, since its health is not 0;
- is not broken by a malfunction or a meteor. `ec_break` breaks only a machine that
  runs; otherwise a Spare would have installed it.

**A machine taken out before its materials arrive.** The loads that come find no
machine to give them to, and the job ends. They were paid at `FIT`, and half came
back when the machine was taken out, as for any machine.

**A full board** posts nothing, as for a site
([§15](#15-open-risks)). A machine fitted then gets no Supply. A machine whose
materials are in gets no Build. Either way it waits, stopped.

**The save format did not change** (`SV_VER` is still 8). The health bytes and the job
board were already saved.

**Memory.** Bank 0 has 160 bytes more:

- `src/install.asm`: 85;
- `src/jobs.asm`: 60 (875 → 935): the install path in `ja_build`, and `mc_rec`,
  which walks the slots of a dome in any state;
- `src/fit.asm`: 15, for the health and the call to `mc_order`.

`src/econ.asm` is 1 byte smaller, and the `align 16` before the bar took 1. In bank
2's code area, `src/supply.asm` grew by 55 (359 → 414): `mc_order`, `sp_find`, and
the machine path in `sp_arrive`. Bank 0 now ends at `&3DD2`, 46 bytes under the
tests' floor, and bank 2's code area has 19 bytes left.

**What it costs, measured** (`tests/test_install.py`): slot 13 with the arrival, minus
the same slot with no job, in the test colony, using the 1 µs probe.

| slot 13 | µs | milestone 98 |
|---|---|---|
| a load to a machine | 422 | |
| a load to a machine, the job reopens | 1,081 | |
| a machine's last load, posting its Build | 1,869 | |
| a visit that installs | 323 | |
| a load to a site, the job reopens | 976 | 918 |
| a site's last load of one material | 495 | 267 |
| a site's last load, posting its Build | 1,231 | 1,003 |

- **The sites' paths are slower**: 58 µs for `mc_live` on every load to a dome, and
  `mc_tail`'s walk of the slots when the site's last load of a material arrives.
- **A machine's last load is the dearest**, because `sp_find` scans the 32 jobs before
  posting the Build. That happens once per machine.
- **The paths that run on every revolution are faster.** The production loop's
  `bit 7,(hl)` is 12 T-states where `inc (hl)` and `dec (hl)` were 22. `jb_need`'s
  `bit 7,(ix+8)` is 20 where a load and an `or` were 23.
- **A whole revolution of the wheel is 28,954 µs**, as at milestone 98, and the pinned
  slot costs did not move (`tests/test_sim.py`).

**What the planted faults found.** `tests/test_install.py` runs in the test colony with
slot 13 alone. Dome 1 is turned into a medium Factory, and all the living agents are
kept busy so that nothing is assigned. It checks:

- eight loading scenes:
  - in a dome in use: one machine; two that owe the same material; the last load and
    its Build; a second Build that is not posted;
  - on a site: no Build for the machine; the site's own debt first; the site paid and
    its own Build posted while the job reopens for the machine;
  - a machine taken out in the meantime;
- the install visit by visit:
  - 4 → 36 → 68 → 100 → 200, then the next ready slot;
  - a broken slot and one that owes, left alone;
  - the job ending with `EC_NBUILD` back to 0;
  - a site finished and its ready machine started in the same visit;
- a stopped machine:
  - production at each health, where only 200 makes Metal;
  - the operator count, where only 200 asks for one, and no Repair is posted;
  - the malfunction, which breaks only 200;
- `FIT` with the keys: four machines in a Factory of the test colony, each at health
  7, paid 34 / 10, and two Supply jobs;
- the running game from a new game: the first dome and its airlock, an oxygen
  generator fitted. Two colonists loaded Metal and Bioplastic at the ship, both
  arrived within the same five frames, and only the engineer took the Build. The
  health went 7, 4, 36, 68, 100, 200 in 340 frames;
- the same game with a second dome and its generator fitted at placement. The
  builder was put outside when the dome was finished, came back in, and installed
  it: 7, 5, 4, 36, 68, 100, 200 in 840 frames;
- seven costs.

Twelve faults, each caught:

- `FIT` posting no jobs;
- no "unless it already has one", which made eight jobs;
- a dome in use treated as a site, which took a load out of its operators;
- no Build for the machine;
- a Build for a machine on a site;
- the job ending when the site is paid while a machine still owes;
- installing a machine that still owes;
- a Build that never installs;
- the builder left outside when the building is finished;
- production that runs any health that is not 0, as at milestone 98;
- the operator count doing the same;
- the malfunction doing the same.

`tests/test_sim.py` fits machines in two domes in use and one site in its colony and
runs 2,400 ticks. Every slot goes through the stages in order and reaches 200, the
Builds are taken only by roles 1 and 5, and the Z80 matches the reference byte for
byte. With no Build for the machine, and with production running any health that is
not 0, the Z80 differs from the reference.

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
there** until an engineer arrives with a Spare. Since milestone 99 only a machine that
runs can break: one still waiting for its materials or its engineer is left as it is
([§6.9](#machines-carried-at-milestone-99)). That is what closes the loop — the job
board posts the repair itself, and repair outranks staffing, because a stopped machine
does not need an operator, it needs a mechanic. The engineer arrives, spends the part,
and leaves; unlike an operator they do not stay. Since milestone 100 a broken machine
shows a red mark until then ([below](#seen-at-milestone-100)).

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
| Merchant (milestone 93) | — | 1 in 2,048 | the low eleven bits of `r2` equal to `#5A5`, where zero is a visitor; one every 2.7 sols, **1 in 1,986 measured over three periods of the generator**, never in the same revolution as any other roll ([§6.11](#trade-at-milestone-93)) |

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
(Milestone 101 wrote it, for the player's own demolition,
[§9.3](#demolition-at-milestone-101); a meteor still knocks back.)
Knocked back to a site costs the player the same thing that matters — the building
stops producing until builders spend another round on it — and reuses the build path
the player already knows: the struck structure gets the same Build job a new one gets
(`jb_post_build`, now shared by `build.asm` and the meteor). **An airlock knocked back
has no air** (milestone 90): whoever stood in it is outside from that moment, with a
full suit as if they had just stepped out, and is marked to be drawn there
(`lk_air_out`, [§6.6](#suits-at-milestone-90)). Since milestone 104 so is whoever was
in the tube on the way to it ([§6.2](#who-was-in-the-tube-at-milestone-104)). A dome is
never knocked back, so it has no such case: a meteor stops one of its machines.

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

#### Smaller and faster, at milestone 76

`meteor.asm` went from 438 bytes to **377**, and bank 2's code area from 1,366 bytes
free to **1,427**. Every path got faster or stayed equal, in every case the check
tried.

| bytes | Milestone 75 | Milestone 76 |
|---|---|---|
| the start of a shower | 78 | 85 |
| one impact (`mt_impact`, `mt_hit`) | 132 | 110 |
| the crater (`mt_ground`) | 66 | 50 |
| the scan and the footprint (`mt_scan`, `mt_state`, `mt_foot`) | 121 | 100 |
| `mt_rec` | 22 | 16 |
| `mt_byte` | 15 | 15 |
| variables | 4 | 1 |

- **The footprint test is inside the scan.** `mt_state` and `mt_foot` were two calls
  for every record whose centre was near. Now a near record is read in one pass: its
  size (or kind and size), its state, then the footprint. Which table it belongs to
  comes from the record size in `E` — bit 4 is set for a dome's 24 and clear for a
  structure's 8 — not from the node number.
- **The node is worked out only on a hit.** The scan hands back the record and how
  many records were left, and `mt_hit` takes the node as 64 (or 96) minus that.
  `mt_end` and `mt_n` were written for every near record; they are gone, and so is
  `mt_hit`'s second lookup of a record the scan had just read.
- **The structures follow the domes.** The two tables are one block (an `assert`
  holds it), so the second scan starts where the first ended.
- **The machine is the byte before the impact's.** `mt_s` kept the high byte of
  `EC_MRND` for a dome hit. `EC_MRND + 1` still holds it when the hit comes.
- **The world's edge is one sign**: (x + 64) | (y + 64), then `ret m`, as in the
  router ([§9.4](#smaller-and-faster-at-milestone-72)).
- **A crater is one mask and one way back.** Occupancy and terrain are tested
  together (`and #37`). Both outcomes leave through the same return to bank 6, which
  pushes the tile onto the dirty list only when the zero flag says the map changed.
  The tile's address is four instructions shorter: (y + 64) | `&80` shifted right
  gives the high byte, and the carry it leaves is the half row.
- **`mt_rec` no longer checks its range.** Of its callers, only the search for a
  centre can ask for nodes 96 to 127, and it now skips them itself. `ja_build` and the
  hit never could.

The check was a script kept out of the repository, on `build/main.sna`. It called
`mt_tick` from 600 random states:

- buildings bunched round the centre, with domes and structures at separate
  densities;
- in three states out of ten, only one to three nodes alive, taken from the ends of
  the tables (0, 62–65, 94, 95);
- centres at the world's edges, and empty records with a centre near;
- sites and active buildings, every kind of tile, and job tables full and empty;
- `r1` on, at and next to the sixteen values that start a shower, and a seed that
  would come out 0.

Of the 600 calls, 56 started a shower and 196 hit a building: 25 of those changed a
structure, and 9 posted a Build job. 83 made a crater, and 171 fell outside the world
or on a tile that takes none. The script compared every byte that changed, in all
eight banks, and which bank the CPU saw at `&4000` afterwards. All 600 calls were
identical. **Time**: 1,199,756 µs in total before, 1,035,708 after. 506 calls got
faster, 94 stayed equal — no shower and no start, which runs the same instructions as
before — and none got slower. `test_sim.py`'s pinned slot 15 measures **2,662 µs an
impact** on its 54-building colony, from 2,829.

**What the planted faults found.** Forty-one faults were run against the script and
three tests: `test_sim.py`, `test_meteor.py` and `test_loop.py`.

- **Two change nothing with the game's data.** The masks after the rotations that
  turn a structure's sprite size into tiles (`and #3F`, `and #0F`) cut nothing: every
  width in `struct_dims` is a whole number of tiles, at most 16 bytes, and every height
  at most 64 lines. They stay, for a sprite that is not.
- **The script caught thirty-eight of the other thirty-nine.** It missed the last dome,
  node 63, counted as a structure: none of its 300 states hit that dome while it was
  active.
- **The three tests together caught thirty-two.** `test_sim.py` caught twenty-four,
  `test_meteor.py` twenty-two, `test_loop.py` none. The seven they let through:
  - a seed left at 0, which happens only when the clock equals `r1`;
  - structure 95 never taken as a centre;
  - a centre that looks at the integrity instead of the state;
  - the world's edge tested in x only;
  - the last dome counted as a structure;
  - a crater on a corridor too;
  - bank 4 left in the window after a crater. Every test compares memory, and
    none looked at what the CPU sees at `&4000` afterwards.
- **`tests/test_impact.py` catches all thirty-nine.** Its first two versions missed
  six between them: `or #1F` in the trigger, a struck structure left active, a
  structure's size read from the wrong place (caught by its time ceiling alone), then
  structure 95 as a centre, the last dome, and the bank left in. What it needed is
  below.

`tests/test_impact.py` calls `mt_tick` directly in `main.sna` from 400 random states
like the script's, with every footprint inside the world, as building guarantees.
After every call it compares the whole of memory, in all eight banks, against:

- **the reference** (`meteor_tick` in `tools/econ.py`) for the shower, the buildings
  and the jobs;
- **the crater rule** for the world: an unoccupied tile of ground, dust, rock or
  foundation becomes a crater with its decor kept;
- **the dirty list** for the screen: a crater goes in as `DK_TILE` with its tile, or
  raises the overflow flag when the list is full;
- `mt_boom` set on every impact, `ec_fdiv` when a structure is knocked back, and
  `eb_d`/`eb_s` when a dome loses a machine;
- and nothing else.

It also checks that bank 6 is still in the window when `mt_tick` returns. It holds
each kind of call — no shower, a start, an impact outside the world, on a building,
on the ground — to no slower than this milestone measured; milestone 75's file fails
every one but the first, which runs the same instructions. Its five
negatives are:

- a crater on a corridor too;
- an impact outside the world that does not return;
- domes with side 2 + 2 × size;
- the machine from the wrong byte;
- the "near" window at 3 tiles.

**Five things the test's own first runs got wrong**, all in the random states and
none in the Z80. Two made it fail where old and new code agree:

- **A dome of size 174.** Its side, 4 + 2 × 174, is 352 to the reference and 96 to
  the Z80, which counts in eight bits. No dome is that size: the states now give every
  dome a size from 0 to 2.
- **A dome half outside the world.** A dome at x = −61 with side 8 starts at −65, and
  in eight bits that wraps to +63. The reference finds it there; the Z80's "near"
  filter, which compares centres, does not. Building never puts a footprint outside
  the world, and now neither do the states.

Three let faults through:

- **`r1` beside the sixteen values.** `or #1F` in the trigger starts a shower on
  32 values of `r1`, and the states almost never drew one of the extra 16. They now
  draw `&FFEx`, and `&FFF0` with one bit flipped.
- **Structures were almost never hit.** Domes are scanned first, and dense domes
  round the centre cover every tile. Domes and structures now have separate
  densities, with scenes that have no domes at all.
- **The ends of the tables were never alone.** Node 63 counted as a structure, or
  node 95 skipped as a centre, only shows when that node is the one found. Three
  states in ten now keep only one to three of nodes 0, 62–65, 94 and 95 alive.

The paging is checked too: after every call the CPU must see bank 6 at `&4000`, as
`mt_tick` found it. The script's figures above are from its run with all of this.

#### The ship, and a cheaper "near", at milestone 87

**A meteor that falls on the ship does nothing.** The ship is not a building
([§6.2](#inside-and-outside--milestone-87)): it does not go back to a site, and no
Build job is posted for it. The scan still finds it — `I` uses the same scan and must
say `SHIP` — and `mth_struct` returns on `K_SHIP`.

That check cost 18 µs on every hit on a structure, and `tests/test_impact.py`'s
ceilings, set at milestone 76, have no slack. **It was paid for by the scan's
"near".** A record's centre was near when `cx/2 − x + MT_REACH` fell in `0…2·MT_REACH`:
an `add` on every one of 96 records. `B` now carries `x − MT_REACH` through the scan.
`mt_impact` computes it with the same subtraction that made `x` (`sub 8 + MT_REACH`),
the world-edge test and the crater's address add it back in their constants, and only
the footprint test of a near record and the crater's dirty-list entry pay an
instruction for it. `info.asm` subtracts it before its two scans and adds it back
after. Measured over the same 400 calls: an impact on a building **5,152 µs**, on the
ground **4,988** — the ceilings are 5,270 and 5,170.

#### Seen, at milestone 100

**Until this milestone a machine that did not run looked like one that did.** Only
the HUD's alert line knew ([ASSET-8](#12-asset-gaps)). Since milestone 99 the same
was true of a new machine waiting for its materials or its engineer. The player's
decisions:

- **A mark drawn over the machine**, as Planetbase puts an icon over a broken
  component. It is chosen over a dark silhouette of the machine, and over text in
  the INFO panel only.
- **Two marks.** **Broken** (health 0) is red, with a white exclamation mark: it wants
  an engineer with a Spare. **Waiting** (health 1 to 127, [§6.9](#machines-carried-at-milestone-99))
  has yellow and black stripes, as a construction site has. Whether it waits for
  materials or for the engineer is not shown apart.
- **A withered plant** (health 0, from a malfunction or a meteor) shows the broken
  mark too.

**The marks are drawn, not taken from the art.** `tools/pack.py` draws them from two
lines of text per mark into bank 5, as `tools/buttons.py` draws the buttons'
symbols ([§9.3](#graphical-buttons-at-milestone-84)). Each is 2 bytes × 6 lines, opaque, in pens 8
(red), 5 (white), 6 (yellow) and 0 (black). None of these is one of the ground's
pens 7, 11, 12 and 14, which change from planet to planet ([§8.6](#86-palette)).
Before any code was written, a preview drew them over all twelve machines and four
plants, to see that they show on every one.

**Top left, inside the machine.** `ob_mach_one` draws the mark after the machine's
sprite, at the slot's own corner. Since the machine is an opaque 6 × 22 block, a
redraw of the slot alone erases the mark. No mark needs its own redraw, and the
machine does not move, so drawing it top right would only have cost 8 bytes to move
it.

**The banks.** The machines live in bank 5 and the plants in bank 7, and
`ob_mach_one` runs with the bank of the slot's own sprites in the window. The marks
are in bank 5, beside the machines. For a mark, `ob_put_in` pages bank 5 in and
returns with bank 6, so `om_prep` puts the sprites' bank back for the next slot. A
greenhouse without that drew its next plant out of bank 6. The fault shows only in a
full redraw, and `tests/test_mark.py` catches it there.

**What changes it, now pushed.** A slot is redrawn (`DK_MACH`) whenever its mark
appears or goes:

- **`FIT`** already pushed it, so a new machine is drawn with its waiting mark;
- **a malfunction, a solar flare or a meteor** — `ec_break_d`, which now breaks only a
  machine that runs (milestone 99);
- **a repair** — `ja_repair`, which keeps the slot in `B` across `ec_have` and
  `ec_sub`, since both keep it;
- **an install that reaches 200** — `jab_inst`, which counts the slot in `E` as it
  walks them.

All three go through `jb_mpush` (`src/jobs.asm`) and the wheel's hook (`wh_push`), as
`DK_BUILT` does. A waiting machine that gets its last material keeps the same mark,
so nothing is pushed then. A plant that grows a stage still changes no pixels, and
pushes nothing ([§15](#15-open-risks)).

**What it costs, measured** (`tests/test_dirty.py`): redrawing one slot is
**5,990 µs** with a mark and 4,992 without. The list charges 5,000 for either, inside
the table's factor of two, and a mark appears only on these rare events. A full
redraw pays the same 1 ms for each marked slot in view. The pushes happen once per
event, so the wheel's whole revolution is still **28,954 µs** (`tests/test_sim.py`).
A meteor that stops a machine pays for its push inside `mt_tick`: an impact on a
building is **5,182 µs** at worst over `tests/test_impact.py`'s 400 calls, 30 more
than before, under its ceiling of 5,270.

**The save format did not change** (`SV_VER` is still 8). A mark is read from the
slot's health byte, which the save already holds, and the full redraw after a load
draws it.

**Memory.** The marks and their pushes cost bank 0 46 bytes:

- `src/object.asm`: 35, for the mark;
- `src/jobs.asm`: 24, for the pushes of the repair and the install, and `jb_mpush`;
- `src/econ.asm`: 7, for the malfunction's push.

To fit, `mc_live` (16 bytes) moved from `src/install.asm` to bank 2's code area, in
`src/supply.asm`. The `align 16` before the bar gave back 3, and two exits got 1 byte
smaller each:

- `mc_tail`'s "NZ, CY" is `scf / sbc a,a`;
- the three pushes share `jb_mpush`.

That put bank 0's end exactly on the tests' floor.

**Then 72 bytes back, and nothing slower.** A read-only survey of bank 0 listed 29
candidates. This milestone took the 21 that make no path slower:

- **Flags that were already set:**
  - four `or a` after `ob_vis`, since `ob_clip` returns Z exactly when A is 0;
  - two `or a` after a `sub` in `ui_follow`;
  - one in `dt_ghost` and one in `ob_box`, where CY was already 0.
- **Registers instead of memory:**
  - `ob_fig_scan` keeps the slot and the node in `B` and `C`, which saves 14 bytes
    with its two variables;
  - `ob_struct` keeps its flags in `E`;
  - `rooms_rebuild` counts straight into `EC_AMENITY`, since `nd_gloom` reads it
    in another slot of the wheel;
  - `hud_num` has a second entry, `hn_de`, for the stocks;
  - `view_cam` returns the old `cam_p` in `DE` to its two callers;
  - `ob_figures` jumps past `ob_fig_one`'s second `of_at` (`obfo_have`).
- **One page:** the structure table is page-aligned and 256 bytes long, which an
  `assert` checks. So `ob_struct`, `osa_gskip` and `osa_key` index it in 8 bits.
- **Code and data shared:**
  - `ui_dome` does the `cp 255` that its three callers did;
  - `ui_hold` sits just before `uip_sig`, so two loads became an `inc hl`;
  - `ui_hide` is a label on `gh_undo`, not a `jp` to it;
  - `bar_want` fills its two arrays in one loop;
  - `dirty_reset` clears `dirty_head` and `dirty_num` with one 16-bit store;
  - `ob_addsx` extends the sign itself;
  - `ob_mul`, `uds_go`, `jb_best` and `ob_icon` each take a byte from a register.

Four contracts changed, and every caller was checked:

- `dirty_reset` also clobbers `HL`;
- `ob_addsx` leaves sext(A) in `DE`;
- `bar_want` clobbers `DE`;
- `osa_key` now keeps `BC`.

60 of the bytes come before the bar's `align 16`, which turns them into 64; 8 come
after it. Eight candidates were left:

- `jb_dome_ptr` is the same code as `ob_domeadr`, but sharing it saves its 15
  bytes only through the repository's first `ifdef` on a label;
- seven others, about 19 bytes, would each make a cold UI path 10 to 27 T slower.

Bank 0 ends at **`&3DB8`**, 72 bytes under the tests' floor and 26 below where
milestone 99 left it. Bank 2's code area has 3 bytes left. In bank 5 the marks took
24 of the 43 bytes free in `b5code`'s reserve, which is 248 bytes now, not 272.

**What the planted faults found.** `tests/test_mark.py` runs the real game in the
test colony, with the player's keys:

- the tables: both marks in bank 5 as the prose draws them;
- `FIT` of four machines in a medium Factory: four waiting marks, then the colonists
  carry and the engineer installs. The marks go one by one and the machines' own
  sprites are left; it took 16 s of game time;
- a malfunction (`ec_break_d`) in a Factory with no Spares: the broken mark. With
  Spares the engineer repairs it and the mark goes;
- a withered plant in a medium greenhouse: the broken mark, and the other three plants
  as they were.

Each check reads the slot's corner bytes with the cursor hidden, since the cursor's
frame sits over the dome in `LOOK`, and compares the screen with a full redraw.

Seven faults, each caught:

- never a mark;
- a mark on machines that run;
- the two marks swapped;
- a malfunction without `DK_MACH`;
- a repair without `DK_MACH`;
- an install without `DK_MACH`;
- the next slot drawn without its bank.

`tests/test_dirty.py`'s mutation now breaks the weapons of dome 1. The list and the
full redraw both draw the mark, and the slot's cost with a mark is measured beside
the slot without.

`tests/test_impact.py` caught the meteor's new push first. Its model of memory after
an impact knew only the crater's `DK_TILE`, so a stopped machine's `DK_MACH` was a
byte it did not expect. The model now pushes it whenever the hit stops a machine that
ran, and all six of its negatives are still caught. `tests/test_install.py` lost the
label `jabi_st`, since the health is now written once before the builder's
destination; its negative looks for the same bytes from `jabi_go`.

### 6.11 Ships and arrivals

A Control room lets you call ships to the landing pad. **One ship at a time**, and
none at all without a pad — the pad is a structure, and its node id is found by the
same pass that indexes rooms ([§6.6](#66-needs)).

| Ship | What it does | Built? |
|---|---|---|
| **Colonist** | four new colonists appear at the pad, full bars, each the specialty the colony lacks most against the player's shares — no bots ([milestone 91](#who-comes-at-milestone-91)) | ✅ |
| **Visitor** | arrives unbidden, eats, raises every colonist's morale (not the bots', since milestone 93), leaves | ✅ |
| **Merchant** | arrives unbidden every 2.7 sols with three or four goods and its own markup, stays half a sol, trades once as in Planetbase ([milestone 93](#trade-at-milestone-93)); its goods are carried both ways, and it leaves when they are ([milestone 98](#carried-at-milestone-98)) | ✅ — until 93 only in `tools/econ.py` |

A ship is `INCOMING` for 24 revolutions, `LANDED` for 8 — a merchant for half a sol —
then gone. Colonists take
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
Since milestone 91 `C` and the ship's button open the ship's line first, and
`FIRE` there calls ([below](#who-comes-at-milestone-91)).

**The refusal came out blank rather than wrong, and only the screen showed it.**
`ui_hide` jumps to `gh_undo`, which destroys `HL`. The message pointer was loaded
*before* that call, so `ui_msg` printed from whatever `HL` had become — which pointed
at a zero byte, so the row was cleared and nothing was said. Every state check passed;
the test that reads row 3 back as glyphs is what failed.

**Trade is a player action, not a wheel pass.** The merchant's line is the player's
([below](#trade-at-milestone-93)); the wheel only brings the merchant and takes it
away. Trading sets a flag that breaks the no-trade streak, which is the whole reason
Independence in [§10.2](#102-milestones) is hard to keep rather than hard to reach —
and until milestone 93 nothing could trade, so it was neither.

Colonist ships must be **called**; visitors and, since milestone 93, merchants arrive
on their own roll —
**1 in 2,048 revolutions, one every 2.7 sols.** The roll was 1 in 64, which is a
visitor every twenty seconds of play, and a visitor eats 6 Food: seventy Food a sol
against a start state that holds forty. `tools/balance.py` showed the colony's food
running out inside one sol and the *visitors* eating it, not the colonists.

#### Who comes, at milestone 91

The player asked whether the shares of the specialties arriving on the next ships
could be set. Until milestone 90 a newcomer's role was its agent id `& 7`, so three
in eight arrivals were bots — the only source of bot agents in the game. The
player's decisions:

- **One line, like the save slot's chooser.** `C` and the ship's button open it;
  left and right pick a specialty, up and down change it, `FIRE` calls the ship,
  `ESC` closes.
- **Shares in steps of 10%, always summing to 100**, Planetbase-like.
- **Toward the colony**: each newcomer takes the specialty the living colony lacks
  most against the shares. Deaths are made up by the next ship.
- **Ships bring no bots.** Bots made from the Bots stock (the robots machine) are
  the next milestone, 92. Until then nothing makes a bot, and **Automation is
  unreachable** ([§10.2](#102-milestones)). Built at 92 ([below](#bots-at-milestone-92)).

**The line** is rows 3 and 4:

    row 3   SHIP UP/DN=10% FIRE=CALL ESC=BACK  PAUSE
    row 4    >WRK 20 ENG 20 BIO 20 MED 20 GRD 20

The list is on row 4 because the two rows are **one screen line** — 35 columns, the
speed in 5, then row 4's 40. Five `>WRK 20` are 35 columns, and on row 3 they ran
into `PAUSE`; the screenshot showed it, the state did not. Up gives 10% to the
selected specialty and takes 10% from the largest of the others; down takes 10% and
gives it to the smallest of the others; on a tie, the first. Nothing at 100% or at
0%. `SPACE` calls as well as `FIRE`, as it chooses everywhere else in the menu.
`ESC` keeps the shares and the selection; the line reopens as it was. Without a
Control room, `FIRE` says `NEED A CONTROL ROOM`, as `C` did. A new game starts at
20% each.

The shares are `EC_LAND`, five bytes of tenths at the economy's +92 — saved with it
([§11](#11-save-and-load)). The line is a third mode of the action menu
(`ac_mode` 2, `CW_MODE`, [§9.1](#91-controls)), so its keys and its redraw come from
the menu's own dispatch and it needed nothing in bank 0's: `cw_open` and `cw_tick`
are in `src/act.asm` (bank 2), the adjusting and the panel in `src/crew.asm`.

**The rule.** With N living humans and c_r of specialty r, after the newcomer there
should be t_r (N + 1) / 10 of it, and it lacks **d_r = t_r (N + 1) − 10 c_r** tenths.
The largest wins, the first on a tie. The d_r sum to 10, so one is always positive,
and a specialty at 0% (d ≤ 0) never comes. Bots and the dead are not counted.
`tools/econ.py` has it as `pick_role`. Shares 10/10/10/50/20 and a colony of two
workers, an engineer and a biologist bring MED MED MED GRD.

**And what it costs.** `ship_crew` runs once per ship, in slot 15:

- `cw_count` fills eight records `[d, t]` in bank 2: the living counted by role, then
  d + 2,048 for each specialty. **It stops as soon as it has counted `EC_ALIVE`
  agents**: the counter is never below the living — births raise it at once, deaths
  are taken off at slot 12's next count — so everyone after that is dead. It also
  hands back the **first dead id**, and `ship_crew` looks for free ids from there
  instead of from 0. Bots are counted too, into three records nobody reads: one `cp`
  fewer per living agent.
- `cw_pick`, per birth: d += t for everyone (one more in the colony), the largest
  wins and loses 10 (one more of its kind).

Measured in `tests/test_crew.py`, four newcomers landing with 4, 48 and 124 alive:
**3,198, 4,386 and 6,438 µs** — milestone 90's `ship_crew` was 1,692, 2,220 and
3,132, and this milestone's first version 6,655, 8,151 and 10,735 (it worked each
d out again for every birth, with ten additions for 10 c, and walked all 128 agents
with `set`/`res` and a `cp`). The landing happens once per ship, at least 24
revolutions apart. **It is heavier than any other slot for colonies past about
sixty**: the room index, the heaviest frame of every revolution, is 4,692 µs. Since
milestone 92 the colonists are at most 80, and the third case is 76 alive:
**5,148 µs**.

**The simulation test diverged first, and the game was right.** The newcomers are
people now, so they look for work from the pad — node 93 — and the identity run of
`tests/test_sim.py` routed only the domes' rows of `DIST` (`g.hw` = 48). The Z80 read
an unbuilt row and gave a job to agent 21 that the reference gave to 41. Until 90
ids 5, 21, 37 and 53, the run's newcomers, were all bots (role 5) and never asked.
The run now routes every row, as the ship cases already did.

`tests/test_crew.py`: the line key by key against a model of the prose — 95 keys,
the screen and `EC_LAND` compared after each — `ESC`, the button, `FIRE`, `SPACE`, no
Control room; the rule in nine colonies, written out by hand *and* recomputed by
`pick_role` (an empty colony, 100% guards, missing medics among 18 bots, one of
each, 30 dead workers, 76 alive with 0% workers (120 until milestone 92), gaps between the living with a bot
at 127, `EC_ALIVE` seven above the living); a whole voyage — shares from the keys,
the ship called, landed, the four checked against the colony at that moment; and
the three ceilings. Negatives: up without a donor, no ceiling at 100%, no floor at
0%, down giving to the largest, no redraw, `SPACE` that does not call, `C` calling
at once as in 90; id & 7 as in 90, no `cw_count`, the last on a tie, the dead
counted, the first dead id taken as the last; and the count without its early stop,
over the first ceiling. `tests/test_sim.py` lands a ship with 50% biologists and 50%
medics in its 96-agent colony, byte for byte against the reference.

#### Bots, at milestone 92

Milestone 91 took the bots off the ships, and the robots machine had been making a
Bots stock that nothing spent. The player's decisions:

- **On their own, with no button.** While the stock has a Bot and a bot's place is
  free, one bot wakes in the factory that has the robots machine, and the stock drops
  by one.
- **Constructor and carrier bots**, alternately. No drillers then: no Drill job was
  posted, and the mine produced with nobody in it. **Since milestone 94 a new bot is a
  driller while the mines have places without one** ([§6.7](#drilling-at-milestone-94)).
- **Automation is eight living bots** ([§10.2](#automation-at-milestone-92)).
- **Up to sixteen, outside the cap**: the 80 + 16 of [§6.1](#colonists-and-bots-at-milestone-92).

**The rule**, `bot_tick` in `src/bots.asm`, once a revolution in slot 15 before the
ship: with the Bots stock above zero, the **first free id of 80–95** (none: nothing),
and the **first Factory of the room index with the robots machine in any of its eight
slots** (none: nothing — the empty ones are `NO_MACH`, `bd_commit` writes all
eight), a bot is born there: inside (`F_ALIVE | F_INDOORS`), on the ring by the fill
order or with no slot, with a newborn's bars and no task, **constructor on an even
id, carrier on an odd one** — a missing one is replaced by its own kind — and the
stock drops by one. The rest of the birth is the colonist's own (`sb_rest`, after
`sh_born`'s flags and role); `tools/econ.py` has it as `bot_tick`. One a revolution
is one every 16 frames: with five Bots in stock, five bots in 80 frames. The robots
machine makes a Bot out of 2 Metal, a Processor and a Bioplastic, and in the test
colony, with its machine just placed, the first bot is awake in under a thousand
frames.

**And they work.** In a new game whose engineer is a worker, a solar panel is
supplied by the carrier bot and built by the constructor bot, in 340 frames; they
stay outside without suits and live.

**It lives in bank 6** ([§4.2](#code-in-bank-6-at-milestone-92)), 165 bytes, with
nothing more than a few bytes in bank 0: the jump to it, the needs pass's test, the
cap. Bank 0 went from 17 to 28 bytes under its floor: counting the bots for
Automation over their sixteen places is 12 bytes smaller than reading every agent's
role and flags.

**What it costs, measured** (slot by slot, with a 1 µs probe, the same colony in 91
and 92):

| | 91 | 92 |
|---|---|---|
| slot 15, no ship, no Bots | 299 µs | **309** — `bot_tick` reads the stock; `econ_events` jumps to it and it jumps to `ship_tick`, 10 µs instead of 16 with a call |
| slot 12 (`econ_flow`), 4 colonists | 1,044 | **684** — the living counted over 80 ids, not 128 |
| slot 12, 76 colonists and 16 bots | 1,396 | **972** |
| a needs slice of colonists | 1,481 | 1,482 |
| a needs slice of eight bots | 2,752 | **15** |
| a landing, 4 and 48 alive | 3,198, 4,386 | 3,198, 4,386 |
| `bot_tick` with Bots and sixteen bots | — | 112 — every revolution while the machine fills the stock; 181 with a `djnz` loop, before it was unrolled |
| `bot_tick` waking a bot, robots in the second factory | — | 715 |

**What the planted faults found.** `tests/test_bots.py` runs nine states of the
rule against the prose *and* `tools/econ.py`, the chain from the machine to the bot
and one a revolution, the needs over 3,000 frames, `EC_ALIVE`, the oxygen demand and
`POP`, the cap with three Control rooms and a ship with the 80 places full, the solar
panel, Automation with eight and with seven, and the three costs. Eleven faults, each
caught: no stock test, no decrement, always a constructor, fifteen places, born
outside, only the first factory, needs for the bots too, the living counted over 128,
the cap at 128, a ship's newcomers at 80–83 as in 91, Automation by `F_WORKING` as
in 91. `tests/test_sim.py` has six of the rule's cases with slot 15 pinned, against
the reference byte for byte, and compares the ring masks too, which no ship case had.

#### Trade, at milestone 93

**Until this milestone the game had no trade at all.** The table above said the
merchant was built, and that was true of `tools/econ.py` only: nothing passed
`SK_MERCHANT` to `ship_call`, nothing set `EC_TRADED`, and so Independence's "no
merchant trade for five sols" came free to every colony that made its ten goods. The
player's decisions:

- **It comes on its own**, every two or three sols, like the visitors; the alert line
  says so, and the merchant's button opens the trade while it is here.
- **The sale as close to Planetbase as it can be.**
- **A few goods, different every time.**
- **It stays half a sol.**

**What Planetbase does, and what this game does with it.** A trader brings a random
selection of goods; here, **three or four of the thirteen** — everything but Water,
which Planetbase does not trade either — one to four lots of each. Each trader has its
own **markup, 35% to 65%**, on *its* goods, and values yours at their base: here
`EC_MARKUP`, and a trader's price per unit is value + (value × markup + 50) / 100, so
Bioplastic at 40% is 14, Planetbase's own example. The **values are Planetbase's**:
Meal 5, Ore 10, Metal 15, Bioplastic 10, Semiconductors 40, Spares 15, Medical
supplies 25, Gun 80, Starch, Vegetables and Vitromeat 5, Medicinal plants 10. A Bot is
120 — between Planetbase's carrier (80) and constructor (160), because a Bot here
becomes one or the other in turn ([above](#bots-at-milestone-92)); bought ones wake in
the robots factory by the same rule. Planetbase's window has four columns — the
trader's goods, what you take, what you give, your goods — and its trade button works
when what you give is worth at least what you take; here that is one line, below. When
a trade is agreed there, colonists and carrier bots carry the goods to the ship, and
the trader leaves when it has them. **Here the exchange was instant and the merchant
left at once**: one trade a visit, as there, and no hauling — the Haul job of
milestone 95 carries only the mines' Ore. Milestone 98 carries the goods, as there
([below](#carried-at-milestone-98)). Coins and technologies are not traded: this game
has neither.

**The roll.** The visitors' test was "the low eleven bits of `r2` are zero"; the
merchant's is "they are `#5A5`", so both cost one comparison of the low byte —
`econ_events` measured 304 µs with no ship before and after. `#5A5` has a one in
bit 0 (no change of wind), bit 2 (no malfunction) and bit 7 (no storm, no flare) and a
zero in bit 3 (no meteors): over three periods of the generator, 196,605 revolutions,
it came 99 times — 1 in 1,986 — and never together with another roll. It goes
through `ship_call`, so it needs the pad and an empty sky.

**The cargo**, when it lands (`sm_land`, `src/ship.asm`; `tools/econ.py`
`land_merchant`): three bytes, each from eight steps of the Galois LFSR seeded with
`EC_RND` and not advancing it — the events' sequence is the same with or without a
merchant, as with the meteors' own generator. The first gives the markup (its low five
bits, mod 31, + 35) and whether it brings four (bit 5); the second the first good (low
four bits, mod 13) and the step between goods (high four, mod 12, + 1); the third the
lots, two bits a good. Thirteen is prime, so t, t + d, t + 2d, t + 3d (mod 13) never
repeat. **A lot is ~50–100 of value**: 10 Food, Ore, Bioplastic, Starch, Vegetables,
Medicinal plants or Vitromeat, 5 Metal or Spares, 4 Medical supplies, 2 Processors,
1 Gun, 1 Bot (`tr_lot`, `src/stock.asm`) — so a good's cargo is worth 50 to 480, and
over all 65,535 seeds a Bot is in one merchant in four. It stays **`EC_SOLLEN` / 32
revolutions**, half a sol from the sol's own length, which tests shorten. The
markup and the cargo are nine bytes at the economy's end, `+97..+105`, saved with it:
`SV_VER` is 7 ([§11](#11-save-and-load)).

**The line.** `M` on the TRANSPORT bar, red while no merchant has landed:

    row 3   +40% TAKE  210 GIVE  250 FIRE=DEAL
    row 4    <METAL  > SHIP 20 TAKE 10 HAVE  75 @ 15

Row 3 is the balance — what you take at its prices, what you give at their values,
and `FIRE=DEAL` only when you take something and give at least as much. Row 4 is
one good with Planetbase's four columns: what it brings, what you take or give, what
you have, and its value. Left and right walk the thirteen goods, **its own first** in
the cargo's order, then the rest in stock order. **Up** takes one more lot from it
— or gives one fewer — up to what it brings and to the store's cap of 600; **down**
gives one more — or takes one fewer — up to what you have and to 99, the field's two
digits. `FIRE` or `SPACE`: if it is not enough, the deny sound and nothing else; if
something you are giving has run down meanwhile — the colony keeps eating while you
haggle — `NOT ENOUGH MATERIAL` and nothing else; otherwise the stocks change, the
no-trade streak breaks, the merchant leaves, `TRADE DONE` (since milestone 98 what you
take is carried and the merchant waits for it: [below](#carried-at-milestone-98)). `ESC` closes and forgets
the offer. When the half sol runs out the line closes on its own. The offer lives
in `src/crew.asm`'s work area: only a colonists' landing uses it, and none comes
while the merchant is here.

**The ship's line shows TRANSPORT now, too** — with its button white. Since
milestone 91 it had shown the MANAGE bar, and MANAGE's letters worked from inside it.

**Memory.** The line is 792 bytes of bank 0 (`src/lines.asm`), the alert,
`mer_here` and the padding 26, the button and the bars 32, the values and lots 28, the
merged roll 21; bank 0 had 28 to its floor, and three wheel-only pieces moved to bank 6
for them ([§4.2](#code-in-bank-6-at-milestone-92)) — bank 0 is 31 under its floor
now. The texts went to bank 7 after the alert line's lost their trailing spaces: 90
bytes, and `hd_say` pads with `hud_to` instead, which made the warm HUD 5 µs faster.

**What it costs, measured** (1 µs probe, the same colony in 92 and 93):

| | 92 | 93 |
|---|---|---|
| slot 15, no ship | 304 µs | 304 |
| slot 12 whole, oxygen only | 1,782, 684 | 1,782, 684 |
| the HUD, warm | 12,046 | **12,041** |
| a merchant landing (`ship_tick`, six seeds) | — | ≤ 1,233, once in 2.7 sols |
| a frame in the line, no key (`ui_tick`) | — | 980 |
| the line redrawn | — | 17,347, on a key |

**What the planted faults found.** `tests/test_trade.py`: the Z80's values and lots
against the prose and the reference; the cargo at six seeds on its edges (three and
four goods, markup 31 → 35%, first good 13–15, step 12–15 and 0) against
`land_merchant`; a whole voyage in the running game — the roll, 24 revolutions, the
cargo, 50 revolutions of a 1,600-frame sol and gone; the line key by key against a
model of the prose, 319 keys, every bound reached; the deals; the line closing as it
leaves, the red button that opens nothing, the ship's line on TRANSPORT, the alert;
the streak; five costs. Eighteen faults, each caught: always three goods, the markup
without mod 31, the step without + 1, a stay of eight revolutions; no store cap, no
99, no "what you have", a price without rounding, its goods not first; no balance,
no stock check, no streak, a merchant that stays; a line that stays open, a button
that never reds, a button that opens without a merchant, the ship's line on MANAGE
as in 92, no alert. `tests/test_sim.py` runs nine merchant cases with slot 15 pinned
against the reference, and `tests/test_newgame.py` found that a new game did not
clear the new bytes: a previous game's cargo would have survived.

#### Carried, at milestone 98

**Until this milestone a deal changed the stocks at `FIRE` and the merchant left at
once** ([above](#trade-at-milestone-93)). In Planetbase colonists and carrier bots carry
the goods both ways, and the trader leaves when it has them. The player's decisions:

- **As construction sites do** ([milestone 88](#built-at-milestone-88)). What you give
  leaves the stocks at `FIRE`. What you take enters them only as each load reaches a
  Storage dome or the ship.
- **The merchant waits** as long as that takes, then leaves. The half sol applies only
  when there is no deal, and while it waits no other ship comes.
- **Anyone carries**, as for Supply: every colonist and the carrier bots (`job_roles`
  `#5F`).

**What is owed lives in the merchant's own bytes**, which milestone 93 already saves, so
the save format did not change (`SV_VER` is still 8). After a deal (`tr_deal`,
`src/lines.asm`):

- `EC_SHKIND` becomes `SK_DEALT`. `mer_here` stops answering yes, so the line does not
  open again: one deal a visit, as before. The alert line's `MERCHANT LANDED` goes
  quiet with it, since there is nothing left to do with the merchant.
- `EC_SHETA` becomes `#FFFF`, 4,096 sols: `ship_tick` never sends it away on its own.
- `EC_MARKUP` counts the loads owed *to* the merchant. The line, the only reader of the
  markup, is closed by then.
- The quantities of `EC_CARGO` become what you took and is still on its ship.

A load is up to `TRADE_LOAD` = 10 units of one good, as Supply's and Haul's are. The
loads given are counted per good, rounded up: 99 Meals are ten loads, the last one 9.
The streak of [§10.2](#102-milestones) breaks at `FIRE`, as before.

**Two jobs, `J_TRADE`, at the pad** (`TRADE_JOBS`), posted by the same `sp_post` as
Supply's, at Supply's priority 4. The board and the pad are checked first: with no free
entry, or with the pad knocked down, there is no deal at all, because the merchant
would wait for ever for carriers that cannot be posted. With one free entry there is one
carrier.

**The load belongs to the job, not to the carrier.** It is the job's `J_SITE` byte:

| value | meaning |
|---|---|
| 0 | empty |
| `TRADE_GIVE` (`#0F`) | one load for the merchant |
| quantity × 16 + stock | one load of the merchant's |

The pad is `EC_PADNODE`. The first version kept the load in the carrier's `spare`, as
Haul and Supply do. That lost it whenever the carrier went to eat or sleep, which the
reap ([§6.7](#67-jobs)) allows at any time. A lost Supply load costs nothing, since
materials are paid at placement and only counted at delivery. A lost Ore load is ten Ore
off a pile that refills. A lost trade load is goods the colony has already paid for. So
the reap leaves a `J_TRADE` alone, as it leaves a Haul, and whoever takes it next carries
the same load on.

**The round** (`tr_arrive`, `src/carry.asm`, entered from `sp_arrive` with Supply's
protocol). As with Supply, `jb_take` sends the taker first to the nearest Storage dome
in use or the ship (`sp_take`). Then:

- **At a store**, a load of the merchant's goes into the stocks, capped at 600 by
  `ec_add_stock`. If a load is owed to the merchant, they take one and go to the pad.
  They also go to the pad empty if something is still on the merchant's ship. A load for
  the merchant that was abandoned half way, and so arrives at a store, simply goes on to
  the pad.
- **At the pad**, what they bring stays with the merchant. They take the next load off
  its ship (the first cargo slot with anything left, up to ten units) and go to the
  nearest store. They also go empty if more is owed to the merchant.

So every trip carries both ways. With no store anyone can reach, the load is delivered
at the pad, as Haul's is at the mine.

**When nothing is left on either side**, the job ends (`tra_bye`). The other `J_TRADE`
jobs that are open and empty are deleted. If no other remains, `EC_SHETA` becomes 0 and
`ship_tick` takes the merchant away at the next revolution. An open job that still holds
a load keeps the merchant waiting until someone takes it and delivers it.

**A pad knocked down meanwhile.** A meteor can knock the pad down while the merchant
waits, and until it is rebuilt the room pass (`src/needs.asm`) writes `EC_PADNODE` =
255. The first test of the running game found this: its pad was the test colony's
airlock, so the room pass, which recomputes the pad from the structures, wrote 255 and
sent both carriers to node 255, which does not exist. Now whoever would go to the pad
stays where they are, keeping the job and its load, and asks again on every pass.

**Memory.** `src/carry.asm` is 187 bytes of bank 0, `tr_deal` grew from 125 to 172 with
`trd_post`, and the job pass 5. That is 239 bytes; bank 0 had 32 to its floor. The rest
came from the interface ([§4.2](#smaller-at-milestone-98)). In bank 2, 8 bytes: the
`J_TRADE` test at the head of `sp_arrive` and `ac_clr4`, the row-4 clear now shared by
the ship's line and the deal.

**What it costs, measured** (1 µs probe, `tests/test_carry.py`; slot 13 over the same
visit with no job):

| | µs | for comparison |
|---|---|---|
| slot 13, a carrier at the pad (`sp_take`) | 331 | a Haul loading at the mine: 322 |
| slot 13, a carrier at a store | 265 | a Haul delivering: 255 |
| slot 13, the end (`tra_bye` scans the 32 jobs) | 799 | once per merchant |
| a frame in the merchant's line, no key | 840 | 980 at milestone 93 |
| the line redrawn, on a key | 17,448 | 17,347 at milestone 93 |

Slot 15 with no ship (304), the warm HUD (12,041) and a merchant's landing (≤ 1,233)
are where milestone 93 left them.

**What the planted faults found.** `tests/test_carry.py`, in the test colony with slot
13 alone, its airlock standing in for the pad:

- the tables;
- fifteen scenes: at the pad and at the ship, the next good, the end and the next
  revolution's departure, empty either way, the other jobs at the end (one carrying, one
  open and empty, one open with a load), no store, the cap, a carrier who leaves for a
  need and one who dies half way, a load for the merchant abandoned at a store, no pad
  either way;
- three costs;
- in the running game, a pad built from the interface beside the ship (800 frames at
  ×4), a deal from the line, and two colonists carrying +10 Metal and +2 Processors
  until the merchant left.

Twelve faults, each caught:

- the job taken for a Supply;
- the pad taken for a store;
- never a ship;
- no limit of ten;
- the merchant's load not entering the stocks;
- no load for the merchant;
- an abandoned load for the merchant paid twice;
- the reap sending a `J_TRADE` back;
- open jobs deleted with their loads;
- a merchant leaving while another carries;
- a merchant that never leaves;
- carriers sent to node 255 with no pad.

`tests/test_trade.py` checks the deal: nothing with the board full or no pad, the give
leaving, the take staying on its ship, two empty jobs, the loads per good (99 Meals are
ten). Its six new faults, each caught:

- a line that opens again;
- no carriers;
- a deal with the board full;
- a deal with no pad;
- one load per good;
- the ship keeping its whole cargo.

`tests/test_sim.py` carries a deal to the end in its colony, with a store and without,
and the Z80 matches the reference byte for byte. A fault in the load limit, and one in
the departure, each make them differ. The reap's exemption cannot show there, since no
carrier in that run leaves a job half way, so `tests/test_carry.py` holds it.

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

#### Smaller and faster, at milestone 71

`main.asm`'s own code — `start`, the loop and its helpers — went from 187 bytes to
**158**. The loop's own part of every round got faster: 8 µs at normal speed, 5 in
the pause, 16–21 when the HUD's clock strikes.

- **Everything is inline.** `ml_wheel`, `ml_boom`, `ml_over` and `ml_hud` had one
  caller each: a `call` and a `ret` for what can be a `jr`. Only `ml_alert` is still
  a routine. It has three exits, and `tests/test_sound.py` calls it on its own.
- **`ml_alert` lost 10 of its 34 bytes.**
  - **The warm-up is `srl (hl)` on 15:** 7, 3, 1, then 0, which stays 0. That is
    three calls, as before. It takes the same time as the old
    `ld a,(hl)` · `or a` · `jr z`.
  - **The power level is no longer mapped to 1 before the `and`.** `EC_POK` is a
    level (`P_ESS` = 2), not a flag. `A` is now `EC_O2OK` when there is any power and
    0 when there is none. That is the same thing, because `EC_O2OK` is 0 or 1.
  - **The edge is one carry.** The alarm sounds on 1 → 0 only, which is exactly when
    `cp (hl)` sets carry. `ret nc` replaces `ret z` · `or a` · `ret nz`.
  - **Its interface is `HL` = `ml_hudw`.** `ml_hudw`, `ml_warm` and `ml_alarm` are
    three adjacent bytes (`assert`ed), so `ml_alert` reaches the other two with
    `inc hl` from the clock the loop has just reloaded.
- **`mt_boom` is cleared with `ld (hl),b`.** `B` is 0 after the wheel: `djnz` leaves
  it there. In the pause, `ld b,a` has already put `ui_spd`'s 0 there, before the
  `jr z`.
- **The vsync wait loads `B` only.** The PPI listens to A11, and nothing below it.
- **`wh_hook` starts out pointing at `dirty_push`.** It sits in `src/wheel.asm`,
  behind `HAS_VIEW`, which only `main.asm` defines. `start` used to spend two
  instructions, six bytes, writing a value that never changes. `tests/simtest.asm`
  still gets 0.
- **`start` puts bank 1 back with `ld c`.** `B` still holds the gate array's port.

The check was a script kept out of the repository, on `build/main.sna`. It ran the
game for 1,500 rounds of the loop, with the same inputs in the same round on both
binaries. The closing `jp main_loop` goes to a hook that waits, and the script puts the
next round's inputs in while the Z80 stands still. The inputs were:

- speeds 0, 1, 2 and 4;
- 17 meteors and 6 overflows of the dirty list;
- 83 changes of power and oxygen;
- the joystick, the speed keys, ESC, H, C and the menu.

After every round the script compared the screen, banks 1, 2 and 4–7 whole, and the
PSG. It compared bank 0 byte for byte through its labels, because everything after
`main.asm` moved by 29 bytes. All 1,500 rounds were identical.

**Time:** 1,498 rounds faster, and one slower, by 5.9 ms in 2.1 s. That round is a
full redraw with the camera at row −65, beyond the world. What it draws there is
bank 2 read as terrain ([§15](#15-open-risks)), and bank 2's code calls into bank 0,
whose addresses all moved. 22 of the round's 2,541 outside tiles came out a different
class, and some of them cost more to draw. The loop's own part of that round was
faster, like every other. Another such round got 262 µs *faster* for the same reason.
Any milestone that changes bank 0's size moves those tiles.

**What the planted faults found.** Eighteen faults were run against the script and
three tests: `test_sound.py`, `test_game.py`, and `test_loop.py` as first written.

- **The script caught fourteen.**
  - Twelve by comparison.
  - Without `dirty_reset`, every round became a full redraw, and the script did not
    finish.
  - Reading the vsync from port A hung the game before its first round.
- **It missed four:**
  - a warm-up one call shorter;
  - a warm-up one call longer;
  - a border of colour 1;
  - `start` leaving bank 6 in the window.
- **`test_sound.py` and `test_game.py` together caught four:**
  - the alarm on `ret c`;
  - no mapping of the power level;
  - `wh_hook` at 0;
  - the vsync on port A.

  Among the ones they let through: a 15-round HUD clock, a `mt_boom` left at 245
  after a meteor in the pause, and an alarm on 0 → 1 as well.
- **`test_loop.py` caught sixteen at first.** A warm-up one call shorter was caught
  only by its timing, and the border not at all. It now also checks `ml_alarm` after
  every round. The power is on at round 32, the third call of the warm-up, so a
  shorter warm-up raises the shadow early and a longer one fails to raise it at round
  48. It also checks the border's four corners after `start`.
- **It catches seventeen now.** The one left is bank 6 after `start`, which nothing
  can see: `game_new` pages bank 6 in itself before it touches the window (in
  `ng_wipe` until milestone 74). The `out`
  stays anyway, for [§7.4](#74-one-convention-per-half-and-they-disagreed)'s
  convention.

`tests/test_loop.py` runs the loop one round at a time on `main.sna`, 399 rounds:

- **A stub on each of the twelve routines the loop calls** logs the call, with `A`,
  `EC_POK` and `EC_O2OK`. It logs only when the return address is the loop itself, so
  the calls inside `ui_tick` or `view_draw` do not count.
- **The script:** speeds 0, 1, 2 and 4; meteors and overflows at every speed, the
  pause included; the power falling and coming back across the alarm's warm-up; and a
  pause that catches the HUD's clock at 1. The wheel drops no meteors of its own.
- **Every round's calls are checked against the rule, in order:**
  - `wheel_tick` `ui_spd` times;
  - the meteor's sound, with `mt_boom` back at 0;
  - the full redraw after an overflow;
  - the HUD every 16 rounds outside the pause, with the alarm on 1 → 0 only;
  - `snd_tick`, `dirty_tick` and `ui_tick`.

  `ml_hudw` and `ml_alarm` are checked after every round.
- **And the time.** A second pass without stubs counts the µs spent in the loop's own
  code, not in what it calls or in the vsync wait. No kind of round may be slower
  than this milestone measured: 73 at normal speed, 89 at double, 121 at quadruple,
  51 in the pause, 167 for the HUD, 81 for a meteor, 92 for an overflow, and 34,871
  over the 399.
  - With milestone 70's `main.asm` every one fails: 81, 97, 129, 56, 183, 91, 101
    and 38,177.

The test also checks two things about `start`: that the snapshot's `wh_hook` is
`dirty_push`, and that the border is black. It has six negatives:

- a 15-round clock;
- `ret z` for `ret nc` in the alarm;
- a `mt_boom` that is never cleared;
- no `ui_show` after the full redraw;
- a warm-up one call shorter;
- `inc a` for the `xor a` in front of `pal_border`.

**Two traps the test hit, both now in its comments:**

- **The emulator shows `PC` = X − 1 during the first µs of an instruction at X.**
  - `scr_nextline` starts right after `ml_alert`. So without a one-byte margin, 838
    µs of a full redraw counted as the loop's own.
  - A hook found by its `PC` also looked "left" while the Z80 was still waiting in it:
    one round counted 0, and the next one got the wrong kind.
  - The hook now counts rounds in a byte of its own.
- **`ui_show` ends in `jp ui_panel`** in the LOOK state. Its return address is the
  loop's, so the stub sees a call to `ui_panel` after every full redraw. The rule
  says so.

### 7.2 The wheel

**Sixteen slots, one advanced per frame. A full revolution is 16 frames = 320 ms ≈ 3.1 Hz.**

| Slot | Pass | Slice | Budgeted | **Measured** |
|---|---|---|---|---|
| 0–7 | Agent movement | 12 agents each | 1,800 µs | **782 µs** ✅ (842 at milestone 88, 855 at 86, 1,298 before 59) |
| 8–10 | Needs, health, death, deciding | 8 colonists each ([§6.6](#66-needs)) | 433 µs | **2,592 µs** ❌ 6.0×, everyone inside (2,607 at milestone 88, 2,649 at 86, 2,796 before 53) |
| 11 | Production, machines and plants | 16 domes, **one revolution in 16** ([§6.5](#65-economy)) | 4,000 µs | **5,691 µs when it fires, 599 µs a visit** |
| 12 | Flow balance | the living every revolution, 64 structures **one in 64** | 2,000 µs | **5,990 µs on the cycle, 1,582 µs a visit** (1,766 at milestone 86) |
| 13 | Job board — reap, arrive, post, assign | 4 domes, 32 agents | 3,000 µs | **3,694 µs** ❌ 1.2× pinned in `test_sim.py` (4,293 at milestone 93; [§6.7](#drilling-at-milestone-94)) |
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

#### Inside and outside, paid for — milestone 87

`F_INDOORS` put a test on three hot paths: every arrival and departure, every colonist
in the needs pass, every agent in the flow pass's count. Written plainly they cost
movement +97 µs a slot, needs +40 T-states a colonist (counted) and the balance
+257 µs, which took it over its 2,000 µs budget. All three came back below milestone 86,
measured in 10 µs steps rather than whole frames (`tests/test_sim.py` prints the
frame-resolution figures; these are the fine ones, from the same pinned wheel):

| Slot | Milestone 86 | Milestone 87 | How |
|---|---|---|---|
| movement | 854.6 µs | **841.8** | the slice's counter and id in the shadow `BC` (two `exx`, 2 µs, where `push`/`pop` was 7); the travel code moved in front of `ent_move_one` so its `jr` reaches (a `jp` costs a microsecond on every agent that stands still); `en_in` reads the record directly; leaving or arriving inside asks nothing ([§6.2](#inside-and-outside--milestone-87)) |
| needs, all inside | 2,649.1 | **2,607.2** | `EC_O2OK` once a slice through the `call`'s own address, decay and flow as one addition ([§6.6](#the-oxygen-step-at-milestone-87)) |
| balance | 1,766.5 | **1,582.5** | the count unrolled by eight, both bits in one pass |

Production (539.9), the job board (4,323.6) and events (516.8) are unchanged to the
tenth.

**Milestone 88 took 95 µs off the job board** while adding the Supply job to it:
4,323.6 → **4,228.2 µs**, the other slots unchanged ([§6.7](#supply-at-milestone-88)). The whole revolution of `tests/test_sim.py`'s ordinary run reads 36,941 µs
against 36,442: that run is no longer the same colony — its people breathe only
inside, so its oxygen deficit, and the needs and walks that follow from it, differ —
while every slot pinned to the same state is at or below milestone 86.

**Milestone 89 marks every visible change outside for the renderer** — a call to
`fg_mark` on each outdoor step, departure and arrival, birth and death
([§6.3](#seen-outside-at-milestone-89)) — and paid for it before it was asked:

| Slot | Milestone 88 | Milestone 89 | How |
|---|---|---|---|
| movement | 841.8 µs | **781.4** | `ent_move_one`'s body inside the slice's loop: every way out is a jump to the next agent, not a `ret` to a `call`; the role's speed from a table that cannot cross a page. The mark is one `call` on the paths that are outside |
| movement, all inside | 842.8 | **781.9** | the same; nobody inside marks |
| needs | 1,763.2 | **1,748.2** | the slice's agent index wraps with `res 7` |
| needs, all inside | 2,607.2 | **2,591.9** | |
| events | 516.8 | **513.7** | the ship's crew cap is asked once after the births, not per birth |

Production (539.9), the flow balance (1,582.5) and the job board (4,228.2) are
unchanged to the tenth.

**Milestone 90 gave the needs slot the suits** ([§6.6](#suits-at-milestone-90)) and
took `nd_sat` away from everyone outside, which paid for them where it matters:

| Slot | Milestone 89 | Milestone 90 | How |
|---|---|---|---|
| needs | 1,748.2 µs | **1,684.3** | outside, no room is served: the ordinary run has half its colony outside at domes |
| needs, all inside | 2,591.9 | **2,585.8** | the slice's loop already leaves the id in `L`; the `ld l,a` went |
| needs, all outside and walking | 2,223.2 | 2,375.2 | the suit, 19 µs a visit: worse, and still under the slot's worst case, everyone inside |
| movement | 781.4 | 781.5 | the fill on exit, one store on the departure's outside path |
| events | 513.7 | 514.1 | a newborn's suit: `sh_born` fills seven field pages from its template, not six |

Production (539.9), the flow balance (1,582.5) and the job board (4,228.2) are
unchanged to the tenth. The two that moved up by a few tenths are the new rules'
own stores on paths that were already taken.

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
of the wheel and given a **per-frame budget**, exactly like the dirty list: 15 node
expansions every frame (12 until milestone 63), ≈ 2,600 µs on average, and only while
the graph is dirty.

Slot 14 was left empty rather than renumbered, so every other slot kept its number.
The room index of [§6.6](#66-needs) has since moved into it.

Every frame, regardless of slot: read input, move cursor and camera, advance the dirty
list ([§8.5](#85-the-dirty-list)) up to a 20,000 µs cap, tick animation, service audio
(**measured: 85 µs silent, 136 µs while an effect plays** — 100 and 195 until milestone
75 — [§9.5](#95-sound)).

The worst *frame* is a room-index slot during a routing rebuild: 4,692 + 2,700 + 94
≈ **7,500 µs, three-eighths of the frame** (9,700 until milestone 53) (it used to be the flow balance, at 10,700).
The 2,700 is the routing's *average*, though. Its worst slice is 10.4 ms (13.5 until
milestone 63), in a young colony whose sources are mostly alone
([§6.4](#a-cheaper-opening-and-a-budget-of-15-at-milestone-63)). A young colony's
slots are light, but the frame is not the 7,500 the sum says. That leaves 9,300 µs for rendering — and a
single scroll column costs 9,300 µs ([§8.3](#83-the-tile-pass)). **The two together
very nearly fill the frame**, which is exactly why the dirty list is a *budget* rather
than a queue that must be drained: on a frame where the sim is heavy, the scroll edge
takes two frames instead of one.

#### Smaller, at milestone 65

`src/wheel.asm` went from 211 bytes to **179**, and each frame of the wheel is 13–20 µs
cheaper. That was measured over 7,100 frames with interrupts off, and no frame got
slower.

- **`wh_push` tests the hook's high byte.** A handler in page 0 cannot exist, because
  the code starts at `&0100`. So "no hook" is `H = 0`, and `inc h` · `dec h` asks
  without touching `A`. `whp_kind`, which kept the kind across the old test, is gone.
- **The routing is inside `wh_frame`,** its only caller. It keeps the carry of
  `rt_slice` across the `ld bc`/`out` that puts bank 6 back. Neither touches the
  flags, so the `push af`/`pop af` around them went.
- **One multiply serves both kinds of slice.**
  - Movement and needs each had their own "first = slot × count" loop. `wh_go` does it
    for both, and reaches the slice routine through the stack.
  - The needs slots work out which of the three they are with `res 3,e`. Slot 10 is
    `E = 2`, instead of `wh_slot` read back.
- **`wh_todo`,** the empty slot's `ret`, had no slot left pointing at it.

The check was a script kept out of the repository, on `tests/simtest.sna`. It loads
the colony of `test_sim.py` and calls `wheel_tick` one frame at a time:

- 2,000 frames as it is;
- 1,500 frames with `rt_mark` at the start and again in the middle;
- 400 frames each for six combinations of `wh_move_n`, `wh_decay_n` and
  `wh_need_base`, including empty slices and a base that wraps;
- 800 frames with slots switched off and on;
- 400 frames with no hook.

After every frame it compared banks 6, 2, 1 and 5 whole, the wheel's and the
routing's variables, which bank was left in the window, and every `wh_push` of the
frame. All 7,100 frames were identical with the old file and the new one.

**What the planted faults found.** Twenty faults were run against the script and seven
tests: `test_sim.py`, `test_game.py`, `test_needs.py`, `test_save.py`, `test_speed.py`,
`test_meteor.py` and `test_power.py`. The script caught nineteen. It missed
`wheel_reset`, because it never calls it.

Three faults passed every test, and a fourth was caught by only one:

- the routing budget one expansion short, which only makes a rebuild slower;
- `wheel_tick` leaving bank 6 in the window. Nothing after it reads `&4000` before
  paging, so the game still works, but it breaks the convention of
  [§7.4](#74-one-convention-per-half-and-they-disagreed);
- `wheel_reset` not starting the wheel at slot 0;
- switched-off slots running anyway, caught only by `test_meteor.py`.

`tests/test_sim.py` now checks the wheel itself:

- after `rt_mark`, the graph is clean in exactly ⌈Σ (R(s) + 2) / 15⌉ frames, with
  bank 1 in the window after each one;
- with every slot switched off for 32 frames, nothing in bank 6 or in the economy
  changes;
- `wheel_reset` starts at slot 0, with the graph clean.

There are four negatives, one for each fault.

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
| Routing rebuild | 15 node expansions per frame (12 until milestone 63), **not** a wheel slot | 3.4 s at 48 nodes, ~22 s at 128 ([§6.4](#64-routing)) |
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
lines   0 ..  15    HUD, top band      Mode 1   80 bytes ×  16 lines  =  2 char rows
lines  16 .. 175    play area          Mode 0   80 bytes × 160 lines  = 20 × 10 tiles
lines 176 .. 199    HUD, bottom band   Mode 1   80 bytes ×  24 lines  =  3 char rows
```

**Since milestone 83 the HUD is two Mode 1 bands with a palette of their own**, one
above the play area and one below it; until then it was five Mode 0 rows at lines
160–199. The play area is the same 20 × 10 tiles, sixteen lines lower on the screen.
How the screen changes mode twice a frame is [below](#two-modes-and-two-palettes-the-raster-splits-at-milestone-83).

**All three parts come from the same page** — bank 3 at `&C000`. Earlier revisions
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

- The HUD occupies the first 2 and the last 3 character rows of the same 1,024-word
  ring as the play area: `R12/R13` point 80 words *before* `cam_off`, so the top band
  is the 160 bytes before `cam_p` and the bottom band the 240 from `cam_p + 1600`.
  `cam_p` is still the top of the play area, and every world address is computed as
  before. When the camera scrolls, the ring rotates, and the HUD's *memory* moves even
  though its *screen position* does not. Until milestone 83 the HUD was therefore
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

  **The escape hatch, taken at milestone 83:** a camera step moves the whole HUD block
  by a fixed distance inside the ring (±4 bytes east and west, ±160 south and north),
  so the block is **moved** instead of re-rendered — `hud_move`, 3,200 bytes of
  unrolled `ldi`/`ldd`, **17,680–18,820 µs** at every one of the 512 ring positions
  and four directions (`tests/test_split.py`). Each band is cut into pieces that do
  not cross the ring's wrap, neither at the source nor at the destination, and each
  piece is copied in all eight lines; with Δ > 0 the top band goes first, because the
  bottom band's destination lands on the top band's source (and the other way round
  for Δ < 0). What it replaced cost ~19,500 µs per step (rows 3–4 rewritten by the
  panel) and left rows 0–2 as rubble until the next HUD tick — **and forever while
  paused**, because the paused game has no HUD clock: that was a bug in every build up
  to milestone 82, found while measuring this one. A camera *jump* (centre, load)
  still clears both bands and redraws them (`hud_inval` from `view_draw`).
- **Bank 2 stops being a screen page**, which is the good news hiding in the bad.
  It becomes a flat 16 KB of data ([§4.3](#43-bank-2-flat-again)).

**The escape hatch, if the re-render cost proves too high**, is *rupture*:
manipulating `R4`/`R9` to make the CRTC end the frame early and restart it
mid-screen, which does reload `R12`/`R13`. It is the standard CPC technique for a
true split, and it is deliberately not taken here — it is timing-critical and
behaves differently across CRTC types 0–4, so a HUD built on it would work on
some real machines and not others.

#### Two modes and two palettes: the raster splits, at milestone 83

The HUD wanted more than Mode 0 gives it: the buttons of milestone 84 need Mode 1's
320-pixel width, and 80 columns of the 4×8 font fit where 40 did. The play area stays
Mode 0. So the screen changes mode twice a frame, and the bands get **their own pens
1–3** — bright red, bright green, bright white, with pen 0 black in both palettes —
because Mode 1 sees only pens 0–3 and those three are structure colours in the play
area.

**What the Gate Array allows.** A mode write takes effect at the *next* HSYNC; a
colour write takes effect at once. A split at the edge of a visible line would have
the ~24 µs of the right border for both. Instead **each split sits on a blank line**:
line 15 is glyph line 7 of the top band's second row, which no character uses, and line
176, the first line of the bottom band, is never written. On a blank line neither the
mode nor pens 1–3 show, so the top split has the window from the end of line 14's
display to the start of line 16's for the pens, and from line 13's HSYNC to line 15's
for the mode: ~88 µs instead of ~24. The bottom one is the same around line 176.

**When the interrupts come — measured, and one line off the estimate.** The Gate Array
raises an interrupt every 52 HSYNCs and restarts the count two lines into VSYNC. With
`R7 = 33` VSYNC starts on line 264, and the interrupts come at the end of the HSYNC
*before* lines 266, 6, 58, 110, 162 and 214. The estimate had said 7; the border
colour, written by a handler on a cleared screen, said 6. None of them is where a
split is wanted, so the handler waits:

| Interrupt | Handler | Work |
|---|---|---|
| 266 | `is_vs` | Mode 1 and the top band's pens: the frame starts right even if the last one lost its bottom split |
| 6 | `is_top` | waits to line 15; Mode 0 **and a reset of the Gate Array's counter** in one `out`, then the play pens |
| 67, 119 | `is_i2`, `is_i3` | nothing |
| 171 | `is_bot` | waits to line 176; Mode 1 and the bottom band's pens |
| 223 | `is_i5` | nothing |

The reset (bit 4 of the mode register) moves every later interrupt to 52 lines after
it, which brings the fourth one to 171 instead of 162 — nine lines less waiting at
the bottom. As placed and measured: at the top the mode and the reset at ~15:9 µs (µs
from the start of the line's display), pens 1–3 at 15:21, 15:34, 15:47; at the bottom
the mode at ~175:46 and the pens at 175:58, 176:7, 176:20. Every one of them has at
least 10 µs to spare against the ~6 µs an interrupt can wait for the instruction in
progress, and the reset is well away from the end of HSYNC, where the counter steps —
on the wrong side of it, every later interrupt would move a line.

**A chain, not a counter.** Each handler writes the next one's address into `&0039`,
and the Z80 jumps straight there; the three that do nothing cost 25 µs instead of the
51 of a first version that counted interrupts and asked the PPI for VSYNC each time.
The low byte is all that changes, so the handlers share one page: `&0100` is a
`jp start` and the handlers follow it, the one place in bank 0 that nothing else moves.
Only `is_vs` asks the PPI: if it is not VSYNC, it stays the next handler until it is.

**Interrupts back on after a long `di` go through `is_on`, not a bare `ei`.** While they
are off they are lost, and the first one after `ei` comes wherever it comes: the
handler waiting for line 6 runs at line 100, another one takes the VSYNC interrupt,
and the chain needed up to **two** frames to find its step — `tests/test_save.py`
caught it, with the play area in Mode 1 in the picture after a load. Pointing the
chain at `is_vs` first is not enough either: if an interrupt fell in the 32 lines
before VSYNC, the Gate Array gives no interrupt at 266 at all, and another frame goes.
`is_on` does what the Gate Array would: it waits for VSYNC, resets the counter (which
also drops the pending interrupt), does `is_vs`'s work and points the chain at
`is_top`. The Gate Array then resets the counter itself at the end of line 265's
HSYNC — with the count below 32, so without an interrupt — and the next one comes at
line 6 as always. Measured, the reset is right anywhere from VSYNC's start to the end
of line 266 (1 to 43 loops; 22 are used), and the first frame after it is right in
every pixel. It costs up to 20 ms, once per save or load. The loop's own `ei` cannot
do it: it would wait for a VSYNC every frame.

**`R7 = 33`, not the firmware's 30**, moves the picture 24 lines up the monitor. With 30
the first interrupt after VSYNC falls on line 30, and the wait to line 15 would be a
whole period.

**What it costs: 1,177 µs per frame, 5.9 %** (`tests/test_split.py`, a counter in a loop
for 200 frames with and without interrupts). It was estimated at 3.8 % before anything
was measured, and the estimate was wrong twice: the top wait is nine lines, not eight,
and the pens of the bottom split cannot start before line 175's display ends. The two
waits are ~850 µs and fixed by the geometry; the rest is six entries a frame. The lever
left is `R7 = 34`: the interrupt after VSYNC would land on line 14 and the top wait
would be one line instead of nine, ~500 µs a frame less, with the picture eight lines
higher still. A second lever is to do work inside the top wait — `snd_tick` would fit
in its ~550 µs — but that brings the sound player into interrupt context with
`snd_play` racing it from the loop.

**Interrupts were off in the whole game until now**, and three things leaned on it:
the routing queue's tail in `HL'`, the blit kernels' count in `AF'`, and the job
board's one-instruction claim. The handler uses only `AF` and `BC`, on the stack, and
touches nothing but the Gate Array and its own byte at `&0039`, so all three still
hold. **Where interrupts stay off:**

- **The disc.** The FDC gives a byte every 27 µs and the top handler waits 550. For
  the ~35 frames of a save or a load (`sv_begin`), the bands are cleared and the whole
  screen is Mode 0 with the play pens (`is_flat`): black bands while the disc runs,
  rather than Mode 1 bytes shown as Mode 0 noise. `sv_stop` and `sv_after` turn them
  back on through `is_on` and redraw the HUD. A save went from 34 frames to 35 and a
  load from 59 to 60: the `is_on` wait.
- **The palette.** Choosing a pen and giving it a colour are two `out`s, and a handler
  in between would send the colour to its own pen. `pal_pen` runs only at start and in
  `sv_after`, both before their `ei`.

The loop's first instruction is still `ei`, every frame, so that nothing leaves them off
for good — a test probe that runs with `di` and jumps back to the loop, say. Such a
return can leave the bands wrong for up to two frames; the tests that photograph the
screen after one go through `is_on`, as the disc does.

**How it is checked** (`tests/test_split.py`). The emulator's picture is one scanline
per line, 16 pixels per µs; the test decodes screen memory line by line with the mode
and palette that line should have and compares every pixel. Once with the bands and
the lines on either side of each split filled with a pattern that has all four pens,
while the Z80 runs `ex (sp),hl` (6 µs) and `nop` (1 µs) loops in 24 different phases;
once in the running game at `x4`, on the 12,000 lines whose memory did not change
during their frame. Five negatives each break it: no counter reset, the top split
48 µs early or 20 µs late, the bottom one 20 µs early or 48 µs late. And after
interrupts were off for 1–56 ms, in 16 lengths, `is_on` gives a right frame from the
first VSYNC on; a bare `ei` does not (6 of 16), nor an `is_on` that resets after line
266 (11 of 16).

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
row (0.93 frames), measured in [§8.3](#83-the-tile-pass) — plus the HUD's own
cost of a step, a re-render until milestone 83 and a move of the two bands since
([§8.1](#81-screen-layout)). Call it ≈ 0.9 frames per horizontal tile step against
the 9.3 frames a full redraw would cost.

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
| HUD, on top of any of the above | **0.89 – 0.94**: the bands moved with the ring (milestone 83); a re-render was 1.75 (2.30 before milestone 52), and in the game only rows 3–4 of it ran at once |

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

#### Smaller, at milestone 61

`src/view.asm` went from 356 bytes to **284**, and `dk_clamp` in `dirty.asm`, which
only the view uses, lost 3 more. Nothing got slower. Over 4,350 calls, measured with
interrupts off:

- `vr_clip` is 18 % faster;
- `view_cliprect` is 5 % faster;
- `view_cam` is 4 % faster, most of it `hud_inval`;
- a scroll step, `view_rect`, `view_add` and `view_draw`, which are almost all tile
  and object drawing, are the same or a little faster.

The check was a script kept out of the repository. It calls each routine directly:

- `view_cam` at 900 cameras, including the ones outside the world the cursor
  reaches;
- `view_cliprect` with 300 random rectangles;
- `vr_clip` with 3,000 rectangles at eight cameras — inside, outside, on the edges,
  zero wide;
- 96 scroll steps from six cameras;
- `view_rect`, `view_add` and `view_draw`.

After each call it compares `cam_off`, `cam_p`, the CRTC's R12/R13 as the emulator
sees them, `td_*`, the clip, the zero flag and the screen. All 4,350 calls were
identical with the old files and the new ones.

- **`(ty+64)·40 mod 512` is `ty·40 mod 512`.** `cam_off` is twice
  `(tx+64) + (ty+64)·40`, mod 1,024. Inside the mod 512 of that sum, `ty`'s +64 adds
  `64·40 = 5·512`, so it drops out, and `5·ty` fits a byte, so it is computed in `A`
  and multiplied by 8 in `HL`. `tx`'s +64 stays, in 8 bits as before, because the
  camera reaches −65 and −65 + 64 must still be 255.
- **R12/R13 are four `out`s.** The CRTC ignores the low byte of the port, so the
  value goes out with `out (c),a` and `out (c),l` with `B` stepped between `&BC` and
  `&BD`. The old code needed two `push`/`pop` pairs and a fresh `ld bc` for each
  write. `CRTC_VAL == CRTC_SEL + 256` is `assert`ed.
- **`vs_tab` is in the order of the `td_*`**, so a scroll step fills them with two
  pairs of `ldi`. Its terrain goes through `vr_paint`, and its "objects, then the full
  clip" ending is shared with `view_rect` and `view_add`.
- **`dk_clamp` takes the start in `A` and answers in the zero flag.** Its only caller
  is `vr_clip`, which used to store each start in a variable (`dk_c0`, `dk_r0`) for
  `dk_clamp` to read back. Both are gone.
  - A zero length must still answer "outside". The success path can be reached
    with a count of 0, so `dkc_ok` tests `B`.
  - The first version did not test it, and the script caught it at once.
- **`view_cliprect` reads `td_nc`/`td_c0` and `td_r0`/`td_nr` as words and writes
  the clip as two words.**

**What the planted faults found.** Twenty-five faults were run against the script and
eight tests: `test_scroll.py`, `test_camera.py`, `test_object.py`, `test_dirty.py`,
`test_build.py`, `test_reveal.py`, `test_game.py` and `test_fit.py`. The script caught
twenty-four. The twenty-fifth, `view_cam` without `hud_inval`, was caught by
`test_build.py`'s panel rows, since the script does not look at the HUD's cache.

Eight passed every test:

- **Three were in the CRTC write:** the screen page wrong, R12 written twice and R13
  never, R13 given the high byte. The tests compare screen *memory* and the `cam_off`
  variable. Nothing read the registers that decide what the monitor shows.
- **Three were in `vr_clip`:**
  - zero-length rectangles passing;
  - `dk_clamp` answering NZ outside the view;
  - `vr_clip` without its final `or 1`.
  No test sent a rectangle outside the view.
- **Two cost only time:** `view_rect` and `view_add` going on when their rectangle
  is outside. They redraw every object for the same picture, 28 ms instead of 0.15.

`tests/test_view.py` checks them now, on the routines called directly:

- `view_cam` at 1,024 cameras: `cam_off`, `cam_p` and the CRTC as the emulator sees
  it, against the formula above.
- `vr_clip` with 2,400 rectangles, against the intersection with the view. Outside
  or zero-length answers Z and touches nothing. Otherwise it answers NZ with the
  `td_*` and the clip.
- `view_rect` and `view_add` outside the view: Z, the screen untouched, under 1 ms.

There are two negatives: R13 left unwritten, and `dk_clamp` answering NZ outside the
view. It catches seven of the eight faults. The eighth, the missing `or 1`, only
differs for rectangles more than 245 tiles long, where `dk_clamp`'s 8-bit add
overflows, and nothing sends one. With the old files, every check passes except the
two negatives, which look for the new code's instructions.

#### Smaller and faster, at milestone 66

`src/blit.asm` went from 205 bytes to **120** in the game, and `scr_ringtop` left
`screen.asm` (121 → 114): bank 0 got 92 bytes back. Nothing got slower. Per call, with
interrupts off:

- every line costs 1 µs less: the filter is `or #F8` · `inc a`, not `and 7` · `cp 7`;
- a mirrored line costs 2 µs less per byte as well: `ld l,(ix+n)` reads the table
  index straight, without going through `A`;
- a line that crosses the wrap point costs 1 µs less opaque, 8 µs less masked and
  11 µs less mirrored (plus the 2 µs a byte);
- `blit_mask`, the ore overlay's W × H, is 5 % faster;
- over thirteen cameras, a full draw of the view is 1.4 % faster (0.1–1.9 %) and the
  object pass alone 2.3 % (0.4–2.9 %).

The changes:

- **One split for three kernels.** Each of `blt_op_line`, `blt_mask_line` and
  `blt_mask_flip` had its own copy of the split. Now each puts its loop's address in
  `IY` and goes to `bl_wrap`, which runs that loop up to the wrap point, moves `DE`
  back to the start of the ring, and runs it again for the rest.
  - `IY` is free: only the world generator uses it, and that runs before the game.
  - The remainder waits in `AF'`. Nothing else in the game uses it — the interrupt
    handler of milestone 83 included, which saves `AF` and never swaps it. It cannot go in `C`, which two of the kernels use.
  - The first version kept the remainder on the stack and called `scr_ringtop`. It
    was 7 µs slower on every wrapping masked line and 14 µs on an opaque one. The
    script found all 151 of those calls in each of the two kernels, and the split
    was rewritten before anything else was checked.
- **`scr_ringtop` is gone.** After the first part, `DE` is `(d+1):00`, so `E` is
  already 0. Moving it back to the start of the ring is `d − 8`, three instructions
  in `bl_wrap`. They are 10 µs cheaper than the call, and the kernels were its only
  callers.
- **`blit_op` went behind `HAS_QUADS`**, with `blit_mline` and the variables `bo_w`,
  `bo_h` and `bm_h`. Only `tests/packtest.asm` calls it: tiles have `blit_tile`, and
  objects call `blt_op_line` directly.
- **`blit_mask` keeps W and H in `BC`**, pushed across each line, instead of in
  `bq_w` and `bm_h`.

The check was a script kept out of the repository.

- **The kernels, on `tests/packtest.sna`.** 700 calls to each line kernel, at random
  positions with B from 1 to 80. 40 % sit on the wrap point, and 15 % have
  `(d & 7) = 7` without crossing it. Then 250 calls each to `blit_mask` and
  `blit_op`, W × H up to 24 × 40. After each call it compared the whole screen,
  `HL`, `DE` and `IX`, and checked that the source and the other banks were
  untouched.
- **Whole scenes, on `tests/objtest.sna`.** A full draw and the object pass alone,
  at the five cameras of `test_object.py` and eight more, several of them with the
  wrap point inside a dome.

All 2,626 calls were identical with the old files and the new ones, except for `B`
after `blit_mask` and `blit_op`: it used to be 0 and is now W. Nothing reads it.
`blit_mask`'s only caller is `tile_one`, through a tail call, and `tile_one`'s only
caller pushes `BC` around it.

**What the planted faults found.** Twenty-one faults were run against the script and
seven tests: `test_blit.py`, `test_pack_z80.py`, `test_object.py`, `test_scroll.py`,
`test_tiles.py`, `test_dirty.py` and `test_index.py`. The script caught all of them,
and every one failed at least one test. But the line kernels were only ever seen
through whole scenes, and that was thin:

- `test_blit.py` and `test_pack_z80.py` draw at fixed places, never on the wrap
  point. Between them they caught only `or` instead of `and` and the two faults in
  `blit_mask`.
- `test_scroll.py` missed ten of the twenty-one.
- Most faults in the split failed in `test_object.py` and `test_index.py` at one or two
  cameras. The opaque kernel's filter with the wrong mask differed by **3 bytes**, at
  two of the five cameras, and the same kernel's check one byte short by 4.
- Nothing timed a kernel. The first version of this milestone was slower on every
  wrapping line, and only the script said so.

`tests/test_blitline.py` calls the three line kernels directly:

- 600 calls to each, half of them on the wrap point;
- checked against a model of the ring above, where byte *i* goes to
  `base | ((p + i) & &7FF)`, and of mode 0's mirror. The model is written from this
  section, not from the Z80.
- It checks the whole screen, `HL` (or `IX`), and that nothing outside the screen
  was written.
- An 80-byte line, plain and wrapping, may take no longer than this milestone
  measured: 532/570 µs opaque, 1,489/1,521 masked, 2,619/2,654 mirrored, each
  with the probe's own setup.

It catches all nineteen faults in the line kernels, each within the first few calls.
There are three negatives: the filter with the wrong mask,
`DE` not moved back to the start of the ring, and the mirror stepping one byte
instead of a pair. With the old files every line is drawn correctly, but all six
timings fail, and the negatives look for the new code's instructions.

#### Smaller and faster, at milestone 68

`src/screen.asm` went from 114 bytes to **51**. `scr_addr` is 20 µs cheaper on every
call: 74 µs to 54, call included, measured with interrupts off. `scr_nextline` is
the same code.

- **No table.**
  - `scr_rowtab` held r × 80 for the 25 character rows: 50 bytes, and a word read
    through `HL` on every call.
  - r × 80 is (y & `&F8`) × 10, which is 8r → ×4 → +8r → ×2: four additions of `HL`.
    They cost less than the table lookup did.
- **No `push`/`pop`.** The old routine saved `AF` for the y and `BC` around the
  lookup. The y now stays in `A` from start to finish, `BC` is only read, and `D`
  stays 0 from the multiply, so adding x is `ld e,c` · `add hl,de`.
- **No `and 7` on the y.** Three `add a,a` put y & 7 in bits 3–5 and leave junk in
  bits 6–7. The `or #C0` that follows overwrites those anyway. The planted faults
  found this: `and 15` in its place changed nothing.
- **The outputs are the same:** `DE`, and `A` = `D`. `HL` is r × 80 + x + `cam_p`
  before the mod, as before. `BC`, `IX` and `IY` are kept.

The check was a script kept out of the repository, on the game's own binary,
`build/main.sna`.

- **`scr_addr`, every position.** For fourteen values of `cam_p`, odd ones and the
  2,008 where every row wraps included, it called `scr_addr` for every (x, y) of the
  screen, with `DE` holding garbage on the way in. It compared `DE`, `HL`, `A` and
  `BC`. That is 224,000 calls.
- **Whole scenes, on `tests/objtest.sna`,** as at milestone 66: a full draw and the
  object pass at thirteen cameras.

All were identical with the old file and the new one. The thirteen screens are also
byte for byte those of milestone 66. The full draw got 0.2 % faster and the object
pass 0.3 %, and none of the calls got slower.

**What the planted faults found.** Fifteen faults were run against the script and
eleven tests: `test_blit.py`, `test_pack_z80.py`, `test_tiles.py`, `test_object.py`,
`test_scroll.py`, `test_view.py`, `test_camera.py`, `test_index.py`, `test_hud.py`,
`test_dirty.py` and `test_ghost.py`.

- **One was not a fault.** `and 15` in place of `and 7` changed nothing, and the
  `and` went (see above).
- **Each of the other fourteen failed at least four tests.** Each one moves whole
  rows or columns of every picture, and every drawing test draws through these two
  routines.
- **The script missed three.**
  - It called `scr_addr` with `D` = 0 left over from its own loop, so a missing
    `ld d,0` changed nothing there. It now loads garbage into `DE` first, which is
    how the run above was made.
  - It never called `scr_nextline`, so it could not see that routine's two faults.

What no test did was time `scr_addr`, or look at more than the few positions a
scene asks for: one per tile row, one per object. `tests/test_screen.py` checks
both routines on `main.sna`:

- for seven values of `cam_p`, 2,008 included, every (x, y) of the screen;
- `DE` holds garbage on the way in;
- against the formula above: `DE`, `A`, `HL` and `BC` after `scr_addr`, and after
  `scr_nextline` the address of the next line with `HL` and `BC` kept;
- one call of each, and `scr_nextline` on both of its paths, may take no longer
  than this milestone measured.

It catches all fourteen faults. Putting the `and 7` back fails its timing, at 65 µs
against 63. Its three negatives are `and #F0` for the 8r, a missing `ld d,0`, and
`scr_nextline` without its ring. With the old file every
position is right, and `scr_addr`'s timing fails, 83 µs against 63, each with the
probe's own setup.

#### The world has an edge, at milestone 78

The world is tiles −64 to 63 on both axes, and the camera had no limit. The cursor's
half-tile position is a signed byte, so pressing west at x = −64 wrapped it to 63.
`ui_follow` then walked the camera west, one strip at a time, through the 128 columns
that are not the world. The player watched about a minute of garbage scroll past.
Even without the wrap, the one-tile margin put the camera at x = −65 whenever the
cursor stood on the westmost column, and a full redraw there read every tile from the
wrong row ([§15](#15-open-risks)).

- **The cursor stops at the last tile.** Half-tiles −128 to 127 are exactly tiles −64
  to 63, so "the cursor would leave the world" is the overflow of `ui_move`'s 8-bit
  add. An axis that overflows does not move. When neither axis moves, the press does
  nothing: no ghost redrawn, no sound.
- **The camera stops at the edge.** Its top-left stays within x −64…44 and y −64…54,
  so the view never shows a tile outside the world. At the edge the one-tile margin is
  given up, and the cursor reaches the last tile.
- **The half-tile snap does not wrap.** A footprint with an odd width has its centre in
  the middle of a tile. The 3×3 solar collector reaches 127 at the east edge.
  Choosing a dome next moved the centre half a tile further, to 128, which as a byte
  is −128: the other side of the world. At 127 the snap now goes half a tile back, to
  126. `tests/test_place.py`'s rule for `bd_select` says so, and tries 127 on purpose.
- **A save made before this milestone has its camera clamped on load.** It may hold
  x = −65, or worse.

The cost is 35 bytes in bank 0 (`ui.asm` 1,966 → 2,001) and 27 in bank 2 (`build.asm`
+10, `save.asm` +17). A cursor step that does not scroll takes 11 µs longer, 5,153 →
5,164 µs. One that scrolls takes 17 µs longer, 33,854 → 33,871. A tick with nothing
pressed is unchanged, at 176 µs.

`tests/test_edge.py` drives the real game from the start to the four corners of the
world, with two directions held at once. On every frame it requires:

- the cursor inside the world;
- the camera inside its limits;
- neither moving backwards, or more than one tile at a time.

At each corner the cursor must stand on the corner tile and the camera on its own
corner. The view, built strip by strip on the way, must equal a full redraw at that
camera. A second scenario takes the solar collector to the east edge and then chooses
a small dome. The cursor must stay at 126 and the camera at x = 44. Milestone 77's
code fails all five: at every corner the camera goes a tile past its limit, and the
cursor wraps before the solar collector ever stands at 127. With only the snap
patched back, the cursor lands at −128 and the camera starts back across the world.
The four negatives patch the code in memory:

- the cursor with no limit in x;
- the camera with no west limit;
- the camera with no south limit;
- the snap that wraps.

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
3  connectors            masked     only on sides that have a corridor — since
                                    milestone 96 joints, a few pixels each
4  room icon             opaque     at interior_ofs
5  machines or plants    opaque     at machine_slots
6  colonist slots        opaque     at corr_slots, in corr_fill order: the empty
                                    slot with the figure masked over it, in one
                                    pass (ob_fig, milestone 89)
```

and after every dome, corridor and structure, **the colonists outside**, masked, last
of all ([below](#colonists-outside-at-milestone-89)).

Corridors were drawn between steps 2 and 3 of the domes they join until milestone 95;
since 96 they are drawn **before step 1**, under every shell, end at the ring's outer
edge, and step 3's joint joins them to it
([below](#centred-and-joined-to-the-ring-at-milestone-96)).
External structures are drawn after all domes, sorted by `cy` so that southern
structures overlap northern ones.

**Built and checked byte-for-byte** (`tests/test_object.py`) against an
independent Python renderer written from `assets/SPRITES.md` §10 rather than
from the Z80 (`tools/scene.py`), at five camera positions chosen to break things:
a dome clipped at the bottom edge, a dome clipped at the left edge — which is
where clipping meets *mirroring*, the hard case — the western structures, and a
camera whose ring wrap falls inside a dome.

The global order is two passes over the domes rather than one: **all corridors, then
all shells, then all fittings, then the structures** — and since milestone 89 the
figures outside, over everything. Until milestone 95 the shells came first, because the
corridors had to be under the connectors but over the shells.

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
view — still has it. Negative control: with a box's right edge one tile short, 21
tiles lose a piece of something. (Until milestone 77 the negative took away only the
rounding up, which spares the edges that fall on a tile boundary: 12 tiles.)

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
  are the same grey. Since milestone 96 the overlap is under the ring, and what
  the diagonal door covered is the joint's
  ([below](#centred-and-joined-to-the-ring-at-milestone-96)).
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

#### Smaller and faster, at milestone 77

`objindex.asm` went from 347 bytes to **310**, and bank 2's code area from 1,427
bytes free to **1,464**. Bank 0 got 2 back, from 3,122 to **3,124**: one byte out of
`ob_index`, and `oi_mask`, a variable nothing needs any more. Every call got faster,
in every case the check tried.

| bytes | Milestone 76 | Milestone 77 |
|---|---|---|
| `oi_build` | 105 | 84 |
| `oi_pass` | 89 | 68 |
| `oi_st` | — | 14 |
| the box (`oi_gx`, `oi_gy`, `oi_grow`, `oi_t4`, `oi_t16`) | 71 | 65 |
| the hooks (`ov_meas`, `oc_meas`, `os_meas`) | 72 | 71 |
| variables | 10 | 8 |

- **The classes come in `A`.** `ob_index` stored `ob_idx` in `oi_mask`, and
  `oi_build` loaded and shifted that variable again for every class. Now `ob_index`
  shifts the figures bit out once, with `rra`, since its own `or a` has already
  cleared the carry. It hands the rest over in `A`, which waits on the stack while a
  pass runs.
- **A pass returns its count.** `oi_pass` was given the address of its class's
  counter and incremented it through a pointer for every record it wrote. Now it
  counts into `oi_k`, the byte after its own pointer, which the `inc hl` that
  finishes storing the pointer reaches. It hands the count back in `A`, and the
  caller stores it. The first record's address arrives in `HL` instead of being
  stored by every caller.
- **The structures look up their own ids.** `oi_pass` asked on every record whether
  the ids came from `st_ord`. The structure pass now calls `oi_st`, which looks the
  id up, writes it into the record and goes on to `ob_struct`. The loop takes the id
  from its counter for every class.
- **One formula for both ends of a box.** The far end was rounded up with `+3` or
  `+15` before the shift. Now it is ⌊(e−1)/n⌋ + 1: a `dec hl` before the shift and an
  `inc a` after, the same on both axes.
- **Shifts that land in `A`.** A tile was `sra h` / `rr l` two or four times and then
  `ld a,l`. `oi_t4` shifts straight into `A` with `rr h` / `rra`. The bits that come
  in from above never reach the tile. `oi_t16` does four `add hl,hl` and takes `H`.
- **A dome's hook returns straight to the pass.** `ov_meas` used to return 0 so that
  `ob_shell` would return in turn. Now it drops `ob_shell`'s return address, and the
  box's last `ret` goes back to `oi_pass`.
- **No call when there are no structures.** `oi_pass` used to be called to find
  `B` = 0 and leave. Now it is not called.

The check was a script kept out of the repository, on `build/main.sna`. It called
`ob_index` from 300 random states:

- 0 to 64 domes, gathered round a hub or at the edges of the half-tile range;
- corridors between live domes, with continuations after diagonals and the last
  record alive;
- structures of every kind and size, some with an equal `cy`;
- the old index and its counters full of garbage;
- every camera, and every combination of classes;
- in a third of the states, `d_id` naming a dome read at another camera.

It compared every byte that changed, in all eight banks, and which bank the CPU saw at
`&4000` afterwards. `object.asm`'s variables were set to the same values in both
versions, by label. The snapshot after 400 frames is not the same in the two, because
the code does not run at the same speed.

All 300 calls were identical but for two differences in scratch, both expected:

- After a structure pass, `oiw_fn` holds `oi_st` instead of `ob_struct`.
- With no live structures, the old code wrote `oiw_fn` and `oi_ptr` before it found
  that `B` was 0. `oi_walk` writes `oiw_fn` before it reads it, and every pass
  writes `oi_ptr`.

**Time**: 13,796,912 µs in total before, 13,526,100 after, and all 300 calls faster.
By class, domes alone were 4.8 % faster, corridors 2.0 % and structures 0.6 %. With
only the figures bit set, a call saved 5 µs. Most of a pass is the drawing routines it
calls, which this milestone did not touch.

**What the planted faults found.** Forty-five faults were run against the script,
`test_index.py`, `test_object.py`, `test_scroll.py` and `test_dirty.py`.

- **One changes nothing.** `rrca` in place of `rra` in `ob_index` puts the figures bit
  into bit 7 as well. Three more shifts in `oi_build` take it no further than bit 4.
- **One changes only the time.** `ov_meas` without its `pop` goes back through
  `ob_shell`. The box's last `ret` leaves 0 in `A`, so `ob_shell` returns, 128 µs
  later on the worst dome pass. That is still faster than milestone 76, so the script
  saw nothing.
- **The script caught the other forty-three.**
- **The four tests let eleven through**:
  - the last dome left out, and the last corridor left out;
  - the corridors written one record late;
  - a pass over garbage, 256 records long, when there are no structures;
  - one structure fewer;
  - a count that runs on from one class into the next;
  - the pointer's high byte not stored;
  - a structure's id taken from its place in `st_ord`, or from the place next to it;
  - a box one tile too low wherever an object ends on a tile boundary;
  - and the time fault.

  They compare drawings, and a box that is too large, an id the colony happens not to
  expose, or a table the test colonies never fill draws the same.
- **`tests/test_oibuild.py` catches all forty-four.**

`tests/test_oibuild.py` calls `ob_index` directly in `main.sna` from 300 random
states like the script's, with every record valid as the game writes it. After every
call it compares the whole of memory, in all eight banks, against the prose:

- **The index.** Every live object of each class being rebuilt has its box in world
  tiles + 128 and its id. The order is domes by id, corridors by id, and structures
  by `cy`, stable. A dome is its frame, a corridor is the union of its tiles and of
  the continuation after its bend, and a structure is its sprite, with positions from
  `tools/scene.py`, the reference of `test_object.py`. Nothing that would not be
  drawn is indexed.
- **The counters**, and `st_n` and `st_ord` when the structures are rebuilt.
- **`dome_conn`**, when the corridors are rebuilt — the joints' bits (until
  milestone 96 the doors', with the figures bit).
- **The classes that are not rebuilt**, which must be untouched.
- **The state left behind**: `ob_idx` and `ob_meas` at 0, the camera as it was, and
  bank 6 in the window.
- **Nothing else**, beyond the stack and the pass's scratch.

It holds each kind of call (domes, corridors, structures, all three, and all three
with the figures, until milestone 96 with the doors too) to no slower than this
milestone measured. Milestone 76's file fails all five. Its five negatives:

- a structure's id taken from its place in `st_ord`;
- a box's bottom edge rounded down;
- `ob_meas` left at 1;
- empty records written into the index;
- the classes taken from the `A` that the scans leave behind.

`d_id` is 255 before every call, because the script found a bug this milestone did
not fix, in old and new code alike. `ob_draw_all` clears `d_id` only *after*
`ob_index`. When only the corridors are rebuilt, as they are after a corridor is
placed, the dome pass does not run first, and `d_id` still names the last dome that
the previous walk read with the current camera. The first corridor that starts from
that dome is then measured from the wrong frame. Its box is off by the camera's
position in tiles: in all 40 states of a probe that set this up. The fix belongs in
`oi_build`, which should clear `d_id` before its passes. Milestone 82 did that
([below](#the-corridor-pass-forgets-the-screens-dome-at-milestone-82)).

#### The corridor pass forgets the screen's dome, at milestone 82

**The bug that milestone 77 found was visible in the game.** The player builds two
domes 50 tiles from the colony, links them, and scrolls back with the arrow keys. The
colony comes back without its corridors: 125 bytes of the frame differ from a full
redraw, and they stay wrong until the next full redraw.

- **How it happens.** Placing a corridor rebuilds only the corridor part of the index.
  `d_id` still names the last dome the screen's walk read, at the camera out in the
  field. The first corridor that starts from that dome is measured in that frame
  instead of (0, 0). The start colony's first two corridors got boxes 49 tiles east and
  21 north of where they are: the camera's position, (−49, 21), with its sign turned.
  A scroll strip asks the index what lies in it, gets nothing for those corridors,
  and draws ground where they are.
- **The fix.** `oi_build` sets `d_id` to 255 before its passes. When the domes are
  rebuilt too, their pass fills it again correctly, at (0, 0), and the corridors keep
  using it. `d_id` moved to the byte before `ob_meas`, so one store does both:
  `dec l · inc h · ld (d_id),hl` writes 255 and 1, from the `HL` = 0 that has just
  zeroed the camera. That replaced `ld hl,ob_meas · inc (hl)`.
- **The cost** is 2 bytes in bank 2 (`objindex.asm` 310 → 312) and **1 µs per
  rebuild**, on every kind of call. `tests/test_oibuild.py`'s ceilings went up by that
  microsecond, and say why.
- **A first version cost 430 µs.** It cleared `d_id` just before the corridor pass.
  That threw away a dome the dome pass had just read correctly, and forced a re-read.
  Clearing before every pass loses nothing that is right.

`tests/test_oibuild.py` no longer sets `d_id` to 255 before each call. In half the
states it reads a dome first with the state's camera, usually the source of a live
corridor. That reproduces what the screen's walk leaves behind. It has its own random
stream, so the 300 states and the ceilings stay the same. Milestone 81's code fails it
in state 21, a corridor-only rebuild. A sixth negative puts milestone 81's bytes
back. `tests/test_return.py` plays the trip in the real game: three corridors built
in the field, the arrow keys back to the colony, and the frame built by the strips
equal to a full redraw from a clean index. Milestone 81's `oi_build` makes the first
of them differ by those 125 bytes.

#### Colonists outside, at milestone 89

[§6.3](#seen-outside-at-milestone-89) says where a colonist outside stands or walks.
Drawing them took four pieces.

**A list of what is drawn, not of what is true.** `fig_list` (bank 6, page-aligned)
holds up to 64 figures as four columns of 64 bytes: the cell's `x` and `y` in half
tiles (+128, so the window test is unsigned), the figure 1–8 and the agent. A figure
is exactly one half-tile cell, 2 bytes × 8 lines ([§3.1](#31-the-unit-ladder)), so
a position is a pair of bytes and a cell never touches a second terrain tile. The list
is where each figure **is on the screen**: the erase reads the old cell from it
instead of recomputing anything, and a change nobody marked — a neighbour moving in
the adjacency list under someone walking (`lk_cut`) — leaves a figure one step behind,
never a trace.

**Drawn last, by the pass itself.** `ob_draw_all` ends with `fg_draw`, which turns the
clip into a window of half tiles and draws every entry inside it — one subtraction and
one compare per axis, 12 µs for an entry rejected on `x`, 24 on `y`. Every redraw that
goes through the object pass (a scroll strip, a vacated slot, a site row, a terrain
change under a building) therefore puts the figures back over what it painted.
`view_draw` rebuilds the list from the agents (`fg_build`, which decides exactly as
the dirty handler does) and clears every mark.

**One masked 2×8 blit, `ob_fig`.** `ob_put` is general — clipping on every side,
mirroring, line pointers in memory — and measured ~110 µs a line for a figure's two
bytes. `ob_fig` is ~50 in the ring, where it lays the empty slot under the figure in
the same pass, and **34 outside**: an outdoor cell starts on a character row, so each
line is the last plus `&800`, with no `scr_nextline` and no `push`/`pop`. A cell whose
second byte is in the next screen page ("one in 256": milestone 105 found it is none, [below](#a-cheaper-erase-at-milestone-105)) and a figure the clip cuts in half
across go through `ob_put`. Measured: **785 µs a figure** outside, with its position
(`fg_in`: inside the view the position is a byte, ~45 µs where `ob_sx`/`ob_sy` were
~150).

**The ring is no longer baked.** Until milestone 89 every figure was baked into every
slot of every dome size: 3,456 bytes of opaque 2×8s (`corr_slot_gfx`). The empty slot
(24 × 16 = 384) with the figure masked over it is the same picture byte for byte —
`tools/pack.py` proves it for all 8 × 24 before it writes anything (`check_ring`) — so
bank 6 now holds the empty slots, the eight figures twice (with a one-pixel shadow
down and right for outside, where they stand on terrain; without it for the ring) and
the list: 1,152 bytes. The corridor and connector sprites (896) came over from bank 2,
which is what made room in bank 2's code area for `src/figure.asm`; `agent_fields` is
pinned at `&6C00` by the save format, so the rest of what was freed is one 1,536-byte
gap under it ([§4.2](#42-the-eight-banks)).

**And `ob_index` paid back what the move cost it.** Nothing in the index's code
changed, but `corr_dir` and `dome_conn` now straddle a page boundary, and `ob_addu`
takes the slow side of `ret nc` past it: up to **+134 µs** a rebuild, on 169 of
`tests/test_oibuild.py`'s 300 states. The six lookups of a fixed table on the index's
path (`dome_geo`, `dome_conn`, `corr_dir`, `diag_k`, `struct_dims`, `struct_ptr`) are
written out — `add a,lo · ld l,a · adc a,hi · sub l · ld h,a`, 7 µs wherever the table
falls, where the `call` was 13–16. None of the 300 states is slower than milestone 88,
the worst ("all + doors") is 158,841 → **157,476 µs**, and the five ceilings moved
down to what was measured.

`tests/test_figure.py` writes the model from the prose — where each one stands or
walks — and checks it against the list and the screen: the start (four in a row below
the ship, each with their role's figure, every opaque pixel there), a solar panel's
carriers coming and going (36 samples; the list equals the model for all 128 agents,
every figure is visible, and the screen is byte for byte a full redraw made on a
**copy** of the machine, so the real list is never rebuilt and whatever drifts stays),
the first dome (figures leave the list for the site's ring and come back out when it
is sealed), and a meteor under a walker in open ground. Negatives: no `fg_draw` in the
pass, no mark in the step, no erase, no paint, no `fg_build` in the full redraw, no
figures after a terrain change.

#### Centred, and joined to the ring, at milestone 96

The player, looking at a screenshot of milestone 95: *the corridors are not centred,
and they should stop at the outer circle, not the inner one* — and then, on the first
version of this milestone: *one pixel further in.* The first two came from the art's own
rules, `assets/SPRITES.md` §8 and §10, which this game followed to the letter:

- **Half a corridor off the axis.** [ASSET-6](#12-asset-gaps) put the axis doors on
  the half-tile grid ([§3.3](#33-the-grid-is-not-a-choice)), and `conn_points` has the
  left byte of an `n`/`s` door and the top line of an `e`/`w` door exactly on the
  dome's axis. A corridor 2 bytes wide and 8 lines tall ran from the axis outwards:
  one byte, two Mode 0 pixels, right of it, or four lines below. Measured on the
  screenshot: a small dome centred on x 384 (image pixels), its corridor 384–399.
- **Through the ring.** The doors, `conn_{dir}`, were drawn after the shells, as the
  art says, "opening the door on the ring" down to the inner circle, and every
  corridor was drawn over the shells.

**The axis corridors go half their width back.** `corr_dir`'s start offsets are
−1 byte for `n` and `s` and −4 lines for `e` and `w`, and the bend into an axis run
(`oc_bend`) moved the same way. On the test colony's cameras they are centred to the
pixel: a dome spanning 64–255 has its corridor at 152–167, another at 480–607 has
536–551, and a dome from 112 to 291 has its horizontal one at 194–209.

**The corridors are drawn before the shells, and the doors not at all.** `ob_draw_all`
walks the corridors first, then the shells, then the fittings, and a ring's mask covers
whatever part of a corridor lies inside its circle. An axis corridor already started at
the edge of the dome's frame, the ring's outermost point; the diagonals were built to
overlap the ring a little, and that overlap now disappears under it.

**The joints.** Stopping exactly at the outer circle left the ring's white outline as
a line between the corridor's grey and the ring's grey, and the diagonal door had also
covered a small triangle of ground between the ring and the first diagonal tile. Both
are closed by a **joint**, drawn over the shell as step 3 of each dome, where the doors
were, in every direction that has a corridor. A joint is:

- **the gap of a diagonal**: the pixels of the tile one step before the first
  (`DIAG_K` − 1) that show — inside the dome's frame, not under the shell and not
  under the first tile. None at a large dome;
- **the one pixel in**: the pixels of the shell's outer outline (opaque, with a
  transparent 4-neighbour) that touch, 4-neighbour, a grey pixel of the corridor that
  shows. They turn grey, the grey inside `corr_h`.

So a joint is 2 pixels on a vertical corridor, 6 on a horizontal one, 14, 41 and 5 on a
diagonal of a small, medium and large dome. It is a property of the dome's size and the
direction, at a fixed place in its frame, computed for a lone corridor. At the far end
of a route and after a bend the geometry is the same — 53 of 62 random route ends —
except where a short axis run after a bend leaves the diagonal close to the ring: there
a few outline pixels beside the diagonal stay white — until milestone 97
([below](#the-short-bends-at-milestone-97)). `DIAG_K` itself stays what
routing uses (`src/route.asm`, `tools/route.py`), so lengths, footprints and costs did
not change.

**Two implementations of the rule.** `tools/pack.py` computes the joints from the
sprites — the ring and dome quadrants mirrored into a frame, the corridor tiles at
`conn_points` or on the `DIAG_K` lattice — and packs nine masked drawings into bank 5,
328 bytes: north, west and east, and north-west and north-east for each size. The
southern ones are the northern ones mirrored vertically, which needs no table; a
horizontal mirror needs `flip_mode0`, which is in bank 6 and not visible while bank 5
is, so the eastern ones are drawings of their own. `build/joint_tab.asm` gives each
size and direction its place in the frame and its drawing (`jt_tab`), and each drawing
its address and size (`jt_spr`). `tools/scene.py` computes the same rule its own way,
by drawing a lone dome and a lone corridor (`scene.joint`), and
`tests/test_object.py` compares the two at five cameras, byte for byte.

**Which joints a dome has** is `dome_conn`, 64 bytes, a bit per direction: the first
run's direction at `a`, the opposite of the **last** run's at `b`, and nothing at an
airlock — the rule of milestone 95's `ob_conn_scan`, for its doors. That scan walked the
96 corridors whenever the index of the figures was rebuilt, which is often. Now the
bits are set while the corridors' index is measured (`jt_mark`, called by `ob_corr`
when `ob_meas` is set), and cleared when that index is rebuilt (`jt_clear`, from
`oi_build`), so only a change of corridors pays for them. A new corridor's two joints
come from the dirty list again (`DK_CONN`, `crr_conns`, `dh_conn` → `jt_one`), because
they fall outside its box and rows. A joint never falls on a ring slot, a machine or an
icon (`tests/test_object.py` checks the slots), so drawn alone over the shell it is
what the full pass draws.

**Code.** `src/joint.asm` (`jt_mark`, `jt_dome`, `jt_one` and the tables) is the first
renderer code in `b6code` ([§4.2](#code-in-bank-6-at-milestone-92)): it runs only
with bank 6 in the window — in `ob_corr`, `ob_fittings` and `dt_prep` — and the only
thing it calls that pages, `ob_put_in`, puts bank 6 back before it returns.
`tests/objtest.asm` and `tests/uitest.asm` assemble it flat.

**Centred corridors straddle tiles.** When a dome's axis falls on a tile boundary (an
even `cx` or `cy` in half-tiles, the usual case), a centred vertical corridor has one
byte in the column left of its tiles, and a horizontal one four lines in the row above.
Those tiles had no occupancy. Every redraw that paints only terrain where occupancy
says "free" — a meteor's crater (`dh_tile`), an outdoor figure's step — then painted
over that strip: `tests/test_meteor.py` found 32 bytes, `tests/test_reach.py` the same
thing after a build. **`cr_stampx` stamps those tiles too**, the ones that are free
(`W_OCC_STRUCT`), in the same walk as `cr_stamp`, from `cr_commit` and the test
colony's builder. `tools/reach.py` (`half_tiles`) models it, for `tests/test_reach.py`
and for the fixture of `tests/test_newgame.py`, and `tests/test_meteor.py` has the
first version back as a negative (`cr_stampx` jumping to `cr_stamp`). A tile
already occupied keeps what it had: a dome, a structure or a corridor makes the object
pass run anyway, and a path stays a path. The new corridor's own route check
(`cr_check`) does not look at them, but a stamped tile is taken like any other:
nothing is built on it and no later corridor runs through it. The walk computes each
tile's address itself, from the bounds it has just checked, and the neighbour is one
byte or one row back; a second walk had made `cr_commit` up to 1.9 ms slower than
milestone 72, and this one costs the axial geometry 107 µs against 95 (3,172 against
a ceiling of 3,193) and the others less, or nothing. The first try, widening
`dh_occupied` by a column and a row, failed `tests/test_dirty.py`: a crater on free
ground next to anything cost the whole object pass, 29,952 µs against the 11,000 the
budget assumes, and every outdoor figure walking beside a building would have paid it.
The redraw of a new corridor takes the extra column or row into its box too
(`crr_half`).

**The doors are gone.** `ob_conns` and `ob_conn_scan`, the eight `conn_{dir}` sprites
(256 bytes, not packed any more, `tools/pack.py`), and with them `b6code`'s room grew
from 1,298 to **1,554** bytes. Bank 0 has 48 bytes under the tests' floor (64 at
milestone 95), bank 2's code area 4 (5), `b6code` 21 (25), bank 5 336 (664). In bank 0
the doors' code went and `jt_clear`, `dh_conn`, `crr_conns` and `cr_stampx` came, and
`src/rooms.asm`'s `align 16` is now padded only when its 15 bytes would cross a page.

**The costs**, against milestone 95: the worst build of the corridors' index
117,082 µs (117,518); of all three classes 148,201 (148,748); with the figures 147,178
(157,476 with the doors' scan); domes and structures unchanged to the microsecond.
`ob_box` multiplies by a step of 4 or 16 with shifts instead of the eight-round `ob_mul`,
and that paid for `jt_mark`. A full redraw of `tests/test_object.py`'s five cameras is
1,515,190 µs against 1,515,650: the joints take 35,560 of it, where the doors took
48,720. One camera is 13.8 ms slower — without doors or joints 15.4 ms: a vertical
corridor on its left edge, cut whole until 95, shows a column now that it is centred,
more picture and not slower code — and of the other four, three are faster and one
the same to 10 µs. While a new corridor's rows come out, the worst frame of
`tests/test_link.py` loses 9 bytes of what was already shown (18 at milestone 95,
limit 24; 88 with the terrain first, 96 at 95), and a joint redrawn from the list
costs 1,997 µs where a door cost 2,995.

`assets/SPRITES.md` still describes the doors — it is the art's document and is not
edited here — so this is the place that says they are not drawn.

#### The short bends, at milestone 97

The player, on milestone 96: *close the white pixels after the bends too.* The joints
of 96 are fixed drawings per size and direction, computed for a lone corridor, and
96 said where that falls short: after a bend, a few outline pixels beside the
diagonal stayed white.

**Measured first.** The joint's rule — the shell's outer-outline pixels that touch
visible corridor grey turn grey — applied by `tools/scene.py` at both ends of every
route up to 12 tiles, every size at either end and every half-tile parity of the far
dome: 1,512 end geometries, 48 of them needing a pixel the fixed joint does not draw.
All 48 are one case, the **short bend**: the corridor reaches the dome horizontally,
with exactly one tile after the diagonal. The diagonal then touches the ring one pixel
below or above the horizontal joint — always one pixel, always at the same place in
the dome's frame: the first column's left pixel on the west side, the last column's
right pixel on the east, on line qh + 4 when the diagonal comes from below and qh − 5
from above. One vertical tile after the bend, or two of anything, leaves nothing, and
neither does the start of a route.

**Which domes have one** is `jtb_flags`, a byte per dome with a bit for the side the
diagonal is on (1 north-east, 3 south-east, 5 south-west, 7 north-west). It is written
like `dome_conn`, while the corridors' index is measured: `jt_mark` calls `jtm_bend`
for a corridor with a continuation and a dome at `b`, which looks at the continuation —
one tile, horizontal — and calls `jtb_mark`. `jt_clear` clears it (`jtb_clr`). The
pixel is drawn after the dome's joints (`jtb_dome`, `jtb_px`) with `ob_put`, from the
first row of the west or the east joint (`jt_pxl`, `jt_pxr`), which `tools/pack.py`
checks is exactly that pixel. `scene.dome_bends` and `scene.bend` find the same from
the colony and by drawing, and `tests/test_object.py` compares the two in twelve
scenes, each size and side, and two controls where nothing may be drawn: two tiles
after the bend, and one vertical tile with a horizontal corridor on the same dome. The
code and the flags are in bank 5, the only place with room
([§4.2](#code-in-bank-5-at-milestone-97)).

**A new corridor needs nothing from the list.** The first version also gave the `b`
joint's `DK_CONN` the bend (direction + 8 + 16 × the diagonal's side) and drew the
pixel in `dh_conn`. It never mattered, and `tests/test_link.py` said so: its negative,
that code cut, still showed the pixel. Measured over all 2,024 short bends up to 12
tiles, every size and parity: the pixel always falls in one of the diagonal's **last
two rows** (506 in the last, 1,518 in the one before), the three tiles of a `DK_CROW`,
which redraws everything there, the dome included — after the index, so with the flag
set. With the rows one tile right (`crr_rows` without its `dec b`), 411 fall
outside. `tests/test_corridor.py` checks every fourth of them in the Z80's own redraw
log, and `tests/test_link.py` the pixel itself on screen after a build, with
`jtb_mark` cut for its negative: the full redraw is no reference for it, since without
the flag it lacks the pixel too.

**The cost, and a switch.** Checking the flag on every dome with an east or west
joint, through `jt_b5`, cost about 65 µs a dome: a full redraw of the five cameras of
`tests/test_object.py` was 696 µs slower, in a colony with no short bend at all. So
`jt_dome` ends with a jump to `jtd_end` in bank 0, whose first byte is a **switch**:
`ret` (`&C9`) while the colony has no short bend, written by `jt_clear` before the
corridors are measured, and `ld hl,jtb_dome` (`&21`, the next two bytes are the
address) as soon as `jtm_bend` finds one, falling into `jt_b5`. Off, a dome with
joints pays a `jp`, 3 µs, and `jt_one` paid that back: the `and 7` it had since 96 (A
is always 0–7) and `ld a,0 · rla · add a,a` turned into `sbc a,a · and 2`, 3 µs a
joint. The five cameras take **1,515,110 µs** against 96's 1,515,190, each one no
slower. With the switch on — one short bend anywhere — 1,515,540, +350, about 43 µs
for each dome with joints, all of which then go through bank 5. A joint redrawn from
the list still costs 1,997 µs, and the worst frame of a new corridor's rows loses the
same 9 bytes.

The marking paid for itself in the index: `jtm_set` takes the bit from `bit_tab`
instead of an eight-round `rlca`/`djnz` loop, and `jtm_bend` makes its checks before
the bank switch, so a long bend never pays for it. The worst build of the corridors'
index is 116,310 µs (117,082 at 96), of all three classes 147,468 (148,201), with the
figures 146,651 (147,178).

**A bug a control scene found.** The flag was first looked up with `ob_addu`, which
leaves the carry set when it crosses a page, and the loop over the bits began with
`rra`: in the test build, where the table crossed a page, the carry came in as a bend
on side 8 — one wrong byte on the vertical control. The loop shifts with `srl` now,
and the carry going in does not matter.

**Memory.** Bank 0 has 32 bytes under the tests' floor (48): the switch's two writes
and `jtm_bend` came, `crr_conns` gave its `b` half to `b5code`. `b6code` has 11 (21):
`jt_mark`'s call and `jtm_set`'s table, less `jt_one`'s 3. `b5code` has 43 of its 272.

### 8.5 The dirty list

After the initial draw, **nothing is redrawn unless it changed.** A 32-entry ring of
`(kind, id)` records what changed; the renderer knows the minimal redraw for each kind,
straight out of `assets/SPRITES.md` §8:

| Change | Redraw | Estimated | **Measured** |
|---|---|---|---|
| Colonist enters a slot | one slot | 64 µs | **1,498 µs** |
| Colonist leaves a slot | the terrain under the slot's 2×8 (up to four tiles), then the whole object pass clipped to it | 64 µs | **16.4 ms** on average, **18.5 ms** at worst (18.0 and 20.9 before milestone 43), over the 20 visible occupied slots of the test colony; 1.3 ms when the slot is off screen. The table says 1,500 and `dhs_vacate` adds 18,000 to the running total itself, so it is alone in its frame |
| Machine changes state or breaks | one machine, and its mark since milestone 100 | 530 µs | **4,992 µs**; **5,990** with a mark ([§6.10](#seen-at-milestone-100)) |
| Plant grows a stage | one plant | 530 µs | **4,992 µs** |
| Room type changes | one icon | ≈ 800 µs | **1,997 µs** |
| Corridor added | one connector — since milestone 96 one joint, at each end | ≈ 450 µs | **2,995 µs**; a joint **1,997 µs** |
| Terrain tile changes, open ground | 3×3 tiles | ≈ 1,600 µs | **9,984 µs** |
| Terrain tile changes, under a dome | 3×3 tiles + every object over them | — | **59,904 µs** (99,840 before the object index, [§8.4](#84-object-pass-and-draw-order)) |
| Building finished (`DK_BUILT`) | the room icon and every machine slot; a structure, nothing | 1.4 – 5.7 frames (the whole dome) | **15,974 µs** for a medium dome (17,971 before milestone 43); a large one ≈ 42,000 by the rows above ([§6.9](#69-construction)) |
| Site placed (`DK_SITE`, one per tile row) | the terrain of one footprint row, then that dome's shell and fittings clipped to it | — | **49,920 µs** for a medium dome's row (54,912 before milestone 43); always alone in its frame ([§6.9](#69-construction)) |
| Corridor row placed (`DK_CROW`, one per tile row of a diagonal) | the whole object pass clipped to three tiles, **no terrain** — the tiles a diagonal only touches are not the corridor's, so another dome, structure or crossing corridor can stand there | — | **9,984 µs** on open ground, 14,976 over a dome, in the test colony (59,904 and 64,896 before the object index); the table says 12,000, so it is still alone in its frame — two would be 24,000 ([§6.9](#69-construction)) |
| A colonist outside moves (`DK_AGENT`, milestone 89) | the old 2×8 cell: its terrain, then whatever stands there, then the figures in it; then the figures of the new cell over what is there | — | **4.9–5.3 ms** a step on screen in the test, 7.4 over a building; 0.7–1.2 ms when nothing visible changes or it is off screen ([below](#a-colonist-outside-moves-at-milestone-89)) |
| A building demolished (`DK_RSIZE` + `DK_RECT`, milestone 101, one pair per rectangle) | the terrain of a rectangle of tiles, then whatever stands on it, clipped to it and to the view; the ghost lifted if it is there | — | measured as whole frames of the test colony: **77–125 ms** with one rectangle in them, 18–35 without; the dearest are a corridor's rectangle across a neighbour's shell. `DK_RSIZE` is charged the whole budget and `DK_RECT` nothing, so a rectangle is always alone in its pass, and its two records never part ([§9.3](#demolition-at-milestone-101)) |

**The figure cache is rebuilt from the agents, once per burst of pushes.**
`dome_fig` is what tells the slot redraw which figure belongs where, and when the
simulation moves colonists it is stale — the figure would be drawn back where it
left and never appear where it went. The rebuild walks all 128 agents and costs a
**measured 9,984 µs, half a frame**, so it runs only when a `DK_SLOT` has been
pushed since the last tick, not on every tick. The per-item budget below does not
include it; a frame that redraws a slot can therefore overrun by half a frame,
once.

**An emptied slot is not the reverse of a filled one.** A figure's 2×8 is opaque
and has the ring under it (baked in until milestone 89, laid under it by `ob_fig`
since), so drawing it gives exactly what the full pass would.
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

#### A colonist outside moves, at milestone 89

**The simulation marks, the renderer computes.** `fg_mark` keeps one byte per agent in
the spare upper half of the `node_occ` page and pushes a `DK_AGENT` only when that byte
was 0; `dh_agent` clears it first thing. So an agent is in the ring **at most once**,
however fast it moves and however far behind the list is, and the handler always draws
where the agent is *now* — two steps taken before the list reached it cost one redraw.

`dh_agent` asks `fg_want` where the figure should be, finds where it was drawn with a
`cpir` over the list's agent column, and does nothing if the cell and figure are the
same. Otherwise:

- **The old cell is erased by asking the occupancy, as `dh_tile` does.** Objects are
  drawn only on tiles something occupies or beside them, so if the 3×3 tiles around
  the cell's tile hold no object (paths, occupancy 2, are terrain), the cell is its
  terrain and the figures in it — `fg_draw` alone, not the object pass. If a neighbour
  is occupied, the object pass clipped to the cell, which the index makes cheap when
  the cell's own tile is free. If the cell's own tile is occupied there may be a dome
  under it, and the dome cut to 2×8 is the vacated slot's ~25 blits: it is charged as
  one (`DHS_VAC_US`).
- **The new cell gets its figures over whatever is there** (`fg_paint`): all those
  the list has in it, in the list's order, as in a full redraw.

**Every redraw through the pass now draws the figures too.** `dh_tile` in open ground
redrew the 3×3 tiles and, with nothing occupying them, no objects — a meteor under a
walker erased him until his next step; it now draws the figures of those tiles
(`fg_objs`). `dh_site` draws them after a site row. The vacated slot and the others
call the whole pass, which ends with them.

**The charges follow the list, because a constant would not.** A full list is 64
entries and every scan of it costs 1.5 ms. So `fg_draw` charges `dt_spent` itself,
**24 µs per entry** it looks at and **800 µs per figure** it draws (785 measured),
whoever called it — `dh_agent`, `dh_tile`, a vacated slot. On top of those, measured
in `tests/test_figure.py` on every figure outside of a running colony with the camera
over it, and again with the list made nearly full against it (62 entries before the
walker, so the `cpir` passes them all; 60 in its column, which is the dearest scan; two
standing on its cell, drawn every time it is):

| Charge | µs | Worst measured |
|---|---|---|
| `DK_AGENT`, in `dirty_cost`: `fg_want` and the `cpir` over a full list | 1,300 (1,200 since milestone 106) | 1,224 (1,098 since 106) |
| `FG_ERASE_US`, the old cell in open ground | 2,200 (1,200 since milestone 105, [below](#a-cheaper-erase-at-milestone-105); 1,100 since 106, [below](#the-cells-own-way-at-milestone-106)) | 1,946 |
| `FG_ERASE_NEAR`, beside a building | 2,600 (1,600 since 105) | 2,320 |
| `DHS_VAC_US`, on one | 18,000 | 5,454 |
| `FG_PAINT_US`, the new cell, figures apart | 800 (500 since 106) | 284 alone; with the erase, 2,812 and 3,220 for the two together |

With the scan's charge taken out of `fg_draw`, five of the test's nine cost checks fail.

#### A cheaper erase, at milestone 105

[§15](#15-open-risks) had the price of a step outside since milestone 89: about 5 ms, and
twenty walkers in view a third of the machine. It also had the cheaper way, which waited
for bytes. Milestone 103 gave bank 2's code area 597, and this milestone spent 86 of
them on it. Nothing on the screen changed, except that a vein no longer goes missing
(below).

**The old cell was a whole tile through `ob_put`, cut to 2×8.** Erasing a figure's old
cell redraws its terrain, then whatever stands there. The terrain went through
`dhv_rect_us`'s loop: every tile the rectangle touches goes through the general
`ob_put`, which clips on every side and keeps line pointers in memory. That is about
1 ms for 16 bytes. A profile of one step (`tests/test_figure.py`'s world, the PC sampled
every µs) put that third of the step in `ob_put`'s clipping and line loops.

**Now `fg_tile` writes the 16 bytes.** For the erase, the `call ob_put` in that loop is
patched to `call fg_tile` and patched back after (`fge_go`), so the vacated slot and the
machine that goes out, the loop's other callers, pay nothing. Four facts make the copy
plain:

- the cell is wholly in the view (`fg_in`), so the clip is the cell;
- it starts on a character row, so each line is the last plus `&800`, as in `ob_fig`;
- its address is even, since its `x` is even and `cam_p` is a multiple of 4
  (`view_cam`), so its two bytes are never split across a screen page — `ob_fig`'s
  check for that case can never be true;
- inside the tile, 4 bytes a line, it is one quarter: + 32 for the lower half, + 2 for
  the right.

**What a step costs**, `dh_agent` with the list as in a running colony, the worst of each
case (`tests/test_figure.py`):

| Case | Milestone 104 (µs) | Milestone 105 (µs) |
|---|---|---|
| a walker steps, in open ground | 4,836 | 3,810 |
| a walker steps, beside a building | 5,270 | 4,244 |
| the old cell only, in open ground | 2,978 | 1,952 |
| the old cell only, beside a building | 3,364 | 2,338 |
| the new cell only | 2,122 | 2,122 |
| with the list nearly full, the worst of all | 13,070 | 12,044 |

About a fifth of a step. The charges came down by the same 1,000: `FG_ERASE_US` 1,200,
`FG_ERASE_NEAR` 1,600. So the dirty list, which fits its work into a frame by those
charges, now fits more steps into each. The test holds every case to its charge, as
before. With the patch taken out — `ob_put` as at milestone 104 — four of its nine cost
checks fail.

**One worst frame grew, and it is phase, not work.** In `tests/test_reveal.py` the frame
in which a straight corridor is placed went from 90 ms to 119. Running the same build
with `fg_tile` taken out and the old charges put back gives 90.3 ms again. With
`fg_tile` and the old charges it gives 119.2, so it is the copy, not the charges. A
profile of everything after `FIRE` (the PC every 100 µs, the vsync waits counted
apart) shows 377.1 ms of work with `fg_tile` against 380.5 without. The work is less;
a piece of it lands in the first frame instead of the third. Elsewhere the same thing
went the other way: an airlock placed in `tests/test_reach.py` is 144 ms where it was
156, a corridor in `tests/test_link.py` 60 where it was 73.

**A vein went missing under a walker.** `tile_one` draws a mountain tile with the ore bit
and then the vein over it (`tile_ore_overlay`). The erase drew the tile alone, so a
walker crossing a vein left plain mountain behind, until a full redraw. On the test's
seed, 18 of the 36 cells of nine vein tiles lost pixels when erased, each one erased
alone on a fresh copy of the machine. Mines stand at most two
tiles from a vein ([§6.5](#65-economy)), so drillers can cross one. `fg_tile` lays the vein
over the cell with its mask, as `tile_one` does.

**What checks it** (`tests/test_figure.py`). Eight cameras: over the test's Solar panel,
over veins, and over open ground of every class. In each, garbage is written into a cell
and then `fg_erase` is run, and the screen must be the full redraw again. That makes 457
cells: 350 in open ground, 48 beside a building, 37 on one and 22 on veins. Then a
vacated slot whose 2×8 does not start on a character row, which `fg_tile` would draw on
the wrong lines if the patch were not undone. Four planted faults are caught:
- always the tile's top-left quarter;
- no vein;
- the call not patched back;
- no `fg_tile`, caught by the cost checks.

Milestone 104 fails the scene on its first vein.

#### The cell's own way, at milestone 106

Milestone 105 took the terrain copy out of a step outside. The rest of the step was the
same general machinery, used for one cell that is always wholly in the view. A profile
of a step (`tests/test_figure.py`'s world, the PC sampled every µs) showed where the
3.8 ms went:
- `dhv_clip`'s four `ob_clip`s and `ob_fig`'s two: about 600 µs to cut a 2×8 that needs
  no cutting;
- `fg_draw`'s window, twice: about 200 µs;
- each figure through `ob_fig`'s clipping: about 300 µs more than its 16 bytes;
- the 3×3 occupancy through `vr_clip`, which also set a clip nobody used, and
  `dh_occ_a`, which looked up each row's address: about 370 µs;
- `fg_want`'s two multiplications in a loop: about 220 µs.

**Now the erase and the paint know they hold a cell** (`src/figure.asm`):
- **The clip is the cell** (`fg_cclip`), set from `ob_x` and `ob_y`, which `fg_in` found
  in the view.
- **The 3×3 is read straight from the world.** `tile_addr` gives one address, and each
  row is three bytes, with the next row 128 further on. A tile outside the view now
  counts too: its object can reach into the cell, which the clamp to the view used to
  miss. Outside the world (column or row −65 or 64), a different byte is read; the
  worst that can do is a dearer erase.
- **In open ground the erase has its own path** (`fge_free`): the tile through
  `fg_tile`, then the cell's figures, with no loop over tiles and no object pass. Beside
  a building it is still `dhv_rect_us`'s loop and the object pass, entered after the clip
  (`dhv_rect_c`).
- **The figures of a cell are found with `cpir`** (`fg_cell`). A figure outside stands on
  a cell, so one that touches a cell is in it, with the same `ux` and the same `uy`.
  `cpir` searches the `ux` column (5 µs an entry against `fg_draw`'s 11), each match has
  its `uy` checked, and each figure goes straight to `obfs_lp` at the cell's one screen
  address. The figures come in the list's order, as in a full redraw.
- **One charge for all of it.** `fg_cell` adds the caller's charge, 8 µs an entry, 24 an
  entry with the same `ux`, and 300 a figure, and calls `dhv_charge` once. Each call
  costs about 20 µs, and before there were four or five of them.
- **`fg_want` has no loop in its multiplication** (unrolled, about 25 µs an axis). Its two
  table lookups are a `ld` within a page instead of `ob_addu`. Every outdoor walker pays
  this on every step, in view or not.
- **The figure and tile loops step the low byte only.** The figures are 8 × 32 bytes in
  one page, and the tiles are 64 bytes on 64-byte boundaries (asserted).

**What a step costs**, `dh_agent` with the list as in a running colony, the worst of each
case (`tests/test_figure.py`):

| Case | Milestone 105 (µs) | Milestone 106 (µs) |
|---|---|---|
| a walker steps, in open ground | 3,810 | 2,294 |
| a walker steps, beside a building | 4,244 | 3,056 |
| the old cell only, in open ground | 1,952 | 1,166 |
| the old cell only, beside a building | 2,338 | 1,870 |
| the new cell only | 2,122 | 1,388 |
| nothing changes | 686 | 586 |
| it changes out of the view | 844 | 744 |
| with the list nearly full, the worst of all | 12,044 | 9,116 |

The charges came down with the costs:
- `DK_AGENT` from 1,300 to 1,200;
- `FG_ERASE_US` from 1,200 to 1,100;
- `FG_PAINT_US` from 800 to 500;
- the figures in a cell from 800 to 300 each.

A walker's step in open ground is now charged about 3,200 µs where it was 4,300, so the
dirty list fits a third more steps into a frame.

**Two worst iterations moved, and the work did not.**
- In `tests/test_unlink.py` the demolished Solar panel's worst iteration went from 89.1 ms to 101.8, under the
  ceiling of 150. Its first three iterations were 89, 30 and 71 ms and are now 102, 36 and 53.
  The work after `FIRE` (the PC sampled every 100 µs, without the vsync waits) is the same: 439.1 ms
  against 437.6.
- The airlock before it went the other way, from 99.4 ms to 96.2, with 30 ms less work in the same
  eleven iterations.
- `tests/test_reveal.py`'s straight corridor went from 119 ms to 118.

**The parts cost more than they were charged.** At milestone 105, measured alone on every
cell of two cameras:
- the erase in open ground cost 1,564–1,900 µs against a charge of 1,296;
- on a vein it cost 3,290–3,360, because `fg_tile` laid the vein with the general `ob_put`
  (about 1,700 µs for 16 bytes) and nothing charged it;
- beside a building it cost 1,958–2,208 against 1,696.

The step's total was still covered by the room in `DK_AGENT` (1,300 for the computation
and a full list's `cpir`, about 700 with an ordinary list). That is why the step's cost check
passed, and why milestone 105 wrote "~920" for an erase that was 1,500. Now each part is
under its own charge. The vein is drawn directly, like `obfs_lp`, in about 280 µs, and
charged on its own (`FG_VEIN_US`, 300).

**What checks it** (`tests/test_figure.py`):
- **STACKS.** A list written by the test is drawn by the full redraw, with `fg_build`
  patched to `jp ob_touch`. It has cells in eight columns and three rows, every third
  one with two figures, and cells around the Solar panel. Each cell is erased over
  garbage, then emptied of figures and painted, and each time the screen equals the full
  redraw. The cells are in open ground, beside and on a building, and on a vein.
- **PARTS.** `fg_erase` and `fg_paint` run alone on every cell of two cameras, except
  under the ghost. Each costs at most its charge: 878–1,038 µs in open ground, 1,332–1,342
  on a vein, 1,502–1,634 beside a building, and 406–470 for the paint.
- **CEILINGS** on the averages:
  - a step at most 2,400 µs in open ground and 3,150 beside a building;
  - "nothing" at most 620;
  - "out of the view" at most 780.

Nine new negatives:
- no `uy` check in `fg_cell`;
- only the first entry with the same `ux`;
- no `fg_scr` in the paint;
- one row of the 3×3;
- the vein's wrong quarter;
- the multiplication's last step without `rra` (the first is caught by nothing: it moves a
  figure by at most one cell, and only when the progress is odd);
- the vein uncharged;
- the same-`ux` entries uncharged;
- the general pass forced onto open ground, which breaks the ceilings.

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
to pan and build is a chore. **Built**, as the table says. Every action has a key, and
the six a joystick has (the four directions and two buttons) have the joystick too, read
in one pass over the PSG keyboard matrix.

| Input | Action |
|---|---|
| Cursors / joystick | move the build cursor; camera follows at the viewport edge, and both stop at the world's edge ([§8.2](#the-world-has-an-edge-at-milestone-78)). In the menu, left/right picks the item and up/down the room ([§9.3](#93-build-flow)), and the button bar follows the item's group |
| Fire / `COPY` | select, confirm, place; in `LOOK`, on a dome, open its fitting ([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)) |
| `ESC` | cancel, back |
| `SPACE` | focus the button bar: left/right picks one of the six groups or `?`, `FIRE` or `SPACE` presses it ([§9.3](#graphical-buttons-at-milestone-84)). It opens on the group last built from, so `SPACE` `SPACE` is the build menu where it was left |
| the letter on a button | presses that button, while the button is on the bar. In `LOOK`: `D` domes, `R` corridor, `P` power, `E` resources, `T` transport, `M` manage. Inside a group, its items ([§9.3](#graphical-buttons-at-milestone-84)) |
| `?` (the `/` key) | the help screen: every button, its name and one line on what it does, until any key ([§9.3](#the-help-screen-at-milestone-84)) |
| `1`…`4` | speed: pause, normal, fast, very fast — the wheel advances 0 / 1 / 2 / 4 slots per frame |
| `I` | what is under the cursor — the building, its state and integrity, and the ground, in the HUD's two message rows until the cursor moves or `ESC` ([below](#what-is-under-the-cursor-at-milestone-79)). Only from `LOOK` |
| `H` | centre on `(0,0)` |
| `S` / `L` | save to disc, load from disc ([§11](#11-save-and-load)) — only from `LOOK`. Each opens the slot chooser: left/right pick one of three, `FIRE` goes, `ESC` backs out. Shown at once, paused too, since milestone 80 |
| `C` | call a colonist ship ([§6.11](#611-ships-and-arrivals)) — only from `LOOK`, and only with a Control room and a free pad |

The table had a `TAB` row, "cycle alerts — jump the camera to the next problem", from the
first draft to milestone 79. The key was in the action table and nothing ever read it:
the alerts it would cycle were never built. Its slot is `I` now ([below](#what-is-under-the-cursor-at-milestone-79)).
The reason it was there still stands — in a base 6 viewports wide, the thing that is
killing you is usually off-screen — and an alert key needs a slot of its own when the
alerts come.

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

`3` measured 1.88× again at milestone 102, and 2.00× at 103
([§4.2](#memory-again-at-milestone-103)).

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

#### Smaller and faster, at milestone 64

`src/input.asm` went from 292 bytes to **172**, and reading the controls got almost
four times cheaper. `in_read` went from about 2.3 ms a frame to 0.65:

- the keyboard scan went from 367 µs to 275;
- the rest went from 1,937 µs on average to 374;
- `in_hit` and `in_held` are 5 % faster.

That was measured with interrupts off. Nothing got slower. **Since milestone 103 the game has
neither:** every caller reads the bits of `act_hit` or `act_now` itself, as most already did, and
the 23 bytes are assembled only for the tests' own build (`tests/inputtest.asm`), where
`tests/test_input.py` still checks them ([§4.2](#memory-again-at-milestone-103)).

- **The joystick is an `or`.** Bits 0–5 of line 9 are actions 0–5 in order: up,
  down, left, right, fire 1, and fire 2 (cancel). The action table's second column,
  which only those six used, is gone (32 bytes), and so is the second lookup per
  action.
- **The table is two bytes per action:** the low byte of the action's row in
  `key_now`, and the mask. It shares one page with `key_now` (`assert`ed).
  - The loop walks it backwards, from action 15 to 0. Each answer goes in at the
    right of `DE` with `rl`: after sixteen shifts the first one is in bit 15, and
    whatever `DE` held before has been shifted out.
  - No calls, no `push`/`pop`, and no `inr_acc` or `inr_mask`.
- **`key_now` holds the rows as the PSG gives them: 0 = pressed.** The scan stores
  them with `ini`, which reads and stores in one instruction. The loop asks with
  `and` and then `sub 1`, which leaves the carry set exactly when the key is down.
  The row number goes out with `out (c),a`; the PPI decodes only the high byte of
  the port.
- **`act_prev` is gone.** It was written every frame and read nowhere.
- **`in_bit` rotates n + 1 times and answers with `sbc a,a`.** It returns NZ and
  `A = #FF` when the bit is set, where it used to return `A = 1`. Every call site
  was checked: none uses `A`, only the flag.

The check was a script kept out of the repository, on `tests/inputtest.sna`.

- **The logic.** `in_scan` is cut out and `key_now` written directly, for 1,500
  states in sequence, so that there are presses, holds and releases. This includes
  COPY, TAB, C and the second fire button, which the emulator cannot press. After
  each call it compares `act_now`, `act_hit`, and `in_hit`/`in_held` for all sixteen
  actions, with `C` and `DE` checked.
- **The scan.** 400 real scans, with keys and the joystick pressed through the
  emulator, then `in_scan` and `in_read`.

All 1,932 were identical with the old file and the new one. The first run of the
scans disagreed, but each file disagreed with itself as much as with the other. The
emulator updates its key matrix inside a frame, and the script pressed and released
keys without running one. It runs one now.

**What the planted faults found.** Twenty-two faults were run against the script and
seven tests: `test_input.py`, `test_sound.py`, `test_speed.py`, `test_build.py`,
`test_game.py`, `test_save.py` and `test_fit.py`.

- **Two tests had to change with `key_now`.** `test_input.py`'s raw-bit column and
  `test_sound.py`'s "the keyboard survives the sound" both read it as 1 = pressed.
  Until they were changed, `test_sound.py` failed for every fault, which said
  nothing.
- **Four faults pass everything, the script included.** They are steps 1 and 4 of
  the scan, and the two writes that end it: port A back to output, and the PSG idle.
  - The emulator reads the keyboard without them, and the sound sets step 1 itself.
  - They are the protocol of [§9.5](#95-sound) as the hardware documents it. Only a
    real CPC can say what leaving one out does.
  - The code keeps all seven steps, as before.
- **One fault is not a fault.** `in_bit` without `sub 8` gives the same answers,
  because `rrca` rotates eight bits. It costs eight more rotations, 34 µs on every
  question about actions 8–15, so the `sub 8` stays.
- **TAB on the wrong bit passed every test.** No test presses TAB, because its
  code is the emulator's `KEY_RIGHT`. The other keys the emulator cannot press were
  caught elsewhere: the second fire by `test_game.py` and `test_fit.py`, C by
  `test_game.py`.
  Since milestone 79 that slot is `I`, which the emulator can press, and
  `test_input.py` presses it.

`tests/test_input.py` now checks the logic too.

- `in_scan` is cut out and `key_now` written from the CPC's matrix, not from the
  table in `input.asm`.
- Every key in the table and every bit of line 9 is pressed, held and released.
  Each time, `in_hit` and `in_held` are checked for all sixteen actions, along with
  `C` and `DE`.
- There are three negatives: TAB on bit 5 (since milestone 79, `I` on bit 4, where
  `L` is), the joystick without the second fire, and `in_held` reading `act_hit`.
- With the old file the logic check fails, because it writes `key_now` the new way.

**At milestone 66 the table moved.** The page `assert` did its job the first time
anything in front of the table changed size. `blit.asm` lost 86 bytes, the table
and `key_now` slid down across `&1800`, and the build stopped.

- The table, `key_now` and `act_now`/`act_hit` are now the first thing in
  `input.asm`.
- `main.asm` includes `input.asm` straight after the main loop's `jp main_loop`,
  not after `ghost.asm`.
- In front of the table there is only `start` and the loop. The table is at
  `&016C`, `key_now` ends at `&0195`, and the loop could grow by over 100 bytes
  before the `assert` fires again.
- The files that milestones shrink can no longer move it.
- Nothing changed in size or speed. A table aligned to a page, or a pointer walk
  that did not need one, would each have cost one or the other.

`tools/mapsize.py` learned something from this. It used to put a label only *before*
each `include`. So whatever `main.asm` itself has after an `include` was counted as
part of that file, and the 187 bytes of the main loop had always been printed as
`sprite_consts_asm`. There is now a label after each `include` too, and the pieces
of `main.asm` are added up into one row.

#### What is under the cursor, at milestone 79

`I` in `LOOK` turns the HUD's two message rows into a description of the tile under the
cursor. The speed stays where it always is, in columns 35–39 of row 3.

```
row 3   DOME S   OXYGEN     ACTIVE HP 100%     a dome: size, room
        SOLAR               SITE   HP  40%     a structure: kind
        CORRIDOR                               occupied, with no building over it
        NOTHING BUILT
row 4   MOUNTAIN   ORE VEIN                    the ground
```

- **The building is found the way a meteor finds it.** `mt_scan`
  ([§6.10](#610-events-and-hazards)) asks the dome table, then the structures from where the domes
  end. The name comes from the build menu's own list, by size or kind. The room's name
  comes from its position in `rm_list`. An airlock or an empty dome has none.
- **SITE or ACTIVE, and HP.** Integrity is a byte, 0–255, and a site's progress is the
  same byte ([§6.9](#69-construction)). The HUD shows it out of a hundred as × 101 / 256,
  so 255 reads 100 % and 254 reads 99 %.
- **A corridor has no record under a tile.** `cr_stamp` marks its tiles with the same
  occupancy bit as a building, `W_OCC_STRUCT`, so a tile that is occupied but under no
  dome or structure footprint is a corridor.
- **Row 4 is the world byte.** The class, by name, and ORE VEIN on a mountain with the
  resource bit, which is the test `terrain.asm` uses for a mine
  ([§6.5](#smaller-and-faster-at-milestone-67)).
- **It is a state, `UI_INFO` (6), that runs `LOOK`'s code.** The cursor, the camera and
  every key of `LOOK` work as before. The rows stay until the cursor moves or `ESC` is
  pressed, and then show `LOOK`'s line again. They are a snapshot: `ui_panel` redraws
  rows 3–4 only when its signature changes, so a meteor on the dome under the cursor
  does not change them. A second `I` reads the tile again.
- **`I` does not wait behind a message.** A message — saved, loaded, the ship — holds
  rows 3–4 for six calls of `ui_panel`, and while the game is paused no clock calls
  it. The first version went through `ui_goto` like every other state, so `I` straight
  after a message showed nothing at all, paused. `ui_ask` clears the hold first: the
  player asked for these rows.
- **The key is `I`, and `L` stays Load.** Action 7 was `TAB`, "next alert", which
  nothing ever read ([§9.1](#91-controls)). It is line 4, bit 3 of the matrix now. The
  emulator can press `I` and could not press `TAB`, so `tests/test_input.py` presses
  it, and `COPY` is the one key left that only the logic check reaches.
- **`LOOK`'s line lost its first word** to say so: `SPACE=BUILD I=INFO FIRE=FIT
  C=SHIP`. Since milestone 80 it is `SPACE=MENU I=INFO FIRE=FIT C=SHIP`.

The cost is 273 bytes in bank 2 (`src/info.asm`), 56 in bank 0 (`ui.asm` 2,001 →
2,057), and 132 in bank 7's text block. The 1,024-byte block had 7 bytes left, and the
eight ground names alone are 88, so it is **1,280** now. `tools/pack.py` places the font
straight after it, and an `assert` in `uitext.asm` keeps `TEXT_MAX` from running into
it ([§4.2](#42-the-eight-banks)). Bank 7 went from 952 free to 696.

A `LOOK` tick with nothing pressed, `in_read` and `uist_look`, went from 481 µs to
**493**, and a cursor step from 4,679 to **4,700**. The first draft asked `in_hit`
twice on every tick, once for `I` and once for `ESC`, which was about 100 µs. One `and`
on `act_hit` asks both.

`tests/test_info.py` pauses the game, then presses `I` on 705 tiles:

- every tile of the starting domes' and structures' footprints, and the ring just
  outside them;
- more domes and structures written into the tables far from the colony, in every size,
  kind, room and state, with integrity 0, 32, 128, 254 and 255;
- corridor tiles;
- one tile of every ground the world has, and a mountain with and without ore;
- the four corners of the world.

Rows 3 and 4 must read as the prose above formats them. A step and `ESC` must each bring
`LOOK`'s line back, and a second `I` must refresh, including with a message held on the
rows. The five negatives patch the code in memory:

- the structures never searched;
- the ground names taken ten bytes apart instead of eleven;
- a step that does not leave `INFO`;
- integrity × 100 instead of × 101;
- `I` waiting behind a message.

#### What can be done here, at milestone 80

**Replaced by the button bar at milestone 84** ([§9.3](#graphical-buttons-at-milestone-84)).
What follows is the text menu as it was; what changed is listed at the end.

`SPACE` in `LOOK` opens a menu of what can be done where the cursor is, and only that.
Left/right picks, and the cursor and camera stay where they are. `FIRE` or `SPACE`
does it, and `ESC` goes back to `LOOK`.

```
row 3   < SHIP   >  FIRE=GO ESC=BACK
row 4    BUILD FIT INFO[SHIP]SAVE LOAD CENTRE
```

| Item | Shown | Does what this key does in `LOOK` |
|---|---|---|
| BUILD | always, and first | the build menu ([§9.3](#93-build-flow)) |
| FIT | where `FIRE` would open the fitting: a dome under the cursor whose room takes machines | `FIRE` |
| INFO | always | `I` ([above](#what-is-under-the-cursor-at-milestone-79)) |
| SHIP | with a Control room, a landing pad, and no ship already coming | `C` |
| SAVE, LOAD | always | `S`, `L` |
| CENTRE | always | `H` |

- **The menu opens on BUILD every time.** `SPACE` `SPACE` is the build menu, as one
  `SPACE` was before this milestone. A player who knows the keys loses one press.
  Every key still works, and the menu is the way in for a player who does not know
  them.
- **"Possible" is asked the way the action asks it.** FIT comes from `fit_can`, which
  is `fit_enter` with the entering split off. A dome whose room takes no machine at
  its size opens nothing, so it shows no FIT. Among the domes the test tries, these
  are an airlock, an empty dome, small quarters and a large lounge. SHIP asks the
  three things `ui_ship` and `ship_call` refuse on. A hidden item hides its reason: `C` on
  its own still says NEED A CONTROL ROOM.
- **No ALERT.** The menu as agreed had one, from the `TAB` row of the first
  table. The alerts of [§9.2](#92-hud) are states of the whole colony — no
  oxygen, no power — with no place to jump the camera to, so nothing would be
  possible there. It is waiting for alerts that have a place.
- **The list is built once, when the menu opens.** `ac_list` holds the items that are
  possible, in order. Left/right is then `ui_lr` over that list, as for the build
  menu, with nothing to skip. The game runs while the menu is open, and an item can
  stop being possible meanwhile: visitors arrive on their own, a meteor takes a dome.
  It then does what its key would do. SHIP says why not, and FIT refuses with the
  deny sound.
- **An action starts from `LOOK`, as if its key had been pressed.** The cursor is the
  same in both states, so nothing is redrawn. SHIP blanks row 4 first, because its
  message writes only row 3 (`ui_msg`), and the list would stay there for the length
  of the message — or, paused, for good.
- **`ui_tick` asks for `LOOK` first.** It used to reach `LOOK` by falling through
  five comparisons, and the menu would have made it six. A `LOOK` tick with nothing
  pressed went from 1,472 µs to **1,451**, and a cursor step from 6,074 to **6,053**.

**The slot chooser was invisible when paused, and the menu's SAVE found it.**
`ui_askslot` changed state without redrawing rows 3–4. Neither did a change of slot:
`sl_pick` is in `ui_panel`'s signature, so the rows caught up at the next tick of the
HUD clock — 16 frames later, or never while paused. With the game paused, `S`
showed nothing at all. Both redraw at once now: `ui_askslot` goes through `ui_ask`,
which also clears a held message, and a change of slot calls `ui_panel`.

The cost is 304 bytes in bank 2 (`src/act.asm`) and 29 in bank 0: `ui.asm` 2,057 →
2,076, and `fit.asm` 642 → 652 for `fit_can`. The text block has 65 more bytes in use,
for the names and the key line, and is at 1,214 of 1,280.

`tests/test_act.py` plays the real game, paused:

- **FIT, from the game itself.** On the middle of every dome — the starting domes,
  and more written into the table in all three sizes and six rooms, with the airlock,
  an empty dome and a lounge among them — and on tiles with no dome, `FIRE` in `LOOK` first. Whether it opened the fitting
  decides whether `SPACE` must show FIT. The rows must be exactly the format above.
- **SHIP**, in the eight combinations of the three conditions.
- **Left/right**, round the whole list and back past the start, with every row checked
  and the cursor and camera unmoved.
- **Every item**, once with `FIRE` and once with `SPACE`. For each, the test checks
  the state it leads to and what rows 3–4 say: the build menu, the fitting, `I`'s
  rows, the ship called with row 4 blank, the slot chooser in either mode, the cursor
  at (0, 0).
- **Behind a held message**, the menu still opens.
- **`S` and `L`, paused**: the chooser and each change of slot must show at once.

There are seven negatives:

- FIT everywhere;
- SHIP with a ship already coming;
- `SPACE` that does not choose;
- the bracket after the chosen item missing;
- row 4 left behind by SHIP;
- the menu missing from `ui_tick`'s dispatch, so that left/right moves the cursor;
- a change of slot that is not shown.

`tests/test_link.py`'s flicker measurement samples four times a frame now. With
one sample a frame, its negative stopped failing on this milestone's timing
([§6.9](#69-construction)).

**Since milestone 84** the same `src/act.asm` drives the bar instead of a row of
text. `SPACE` focuses the six groups and `?`, on the group of the last item built
from; `M` opens MANAGE — INFO, FIT, SAVE, LOAD, CENTRE — on INFO. BUILD is gone: the
groups *are* the build menu. Nothing is hidden any more: FIT and SHIP (in TRANSPORT)
are drawn red where they cannot be done, which the player can see without the item
moving. Row 3 says the chosen button's name and row 4 its line from the help screen.
`tests/test_act.py` checks the same seven kinds of thing against the bar instead of
row 4: FIT red or not from the game itself on every dome, SHIP in the eight
combinations, left/right round the seven both ways with the cursor and camera
unmoved, every MANAGE item and the ship with `FIRE` and `SPACE`, the menu behind a
held message, `S` and `L` paused. The bracket negative is gone with the brackets;
"`SPACE` forgets the group" is new.

**Since milestone 91 SHIP opens a third mode of the menu**, the ship's line of
[§6.11](#who-comes-at-milestone-91) (`ac_mode` 2): left/right, up/down, and `FIRE` or
`SPACE` to call. `tests/test_act.py` checks that `T` `C` shows the line, then calls
with each. The text block was full, so sixteen messages lost their trailing spaces
— 70 bytes — and `uip_say` blanks to column 40 with `hud_to` (until then `ac_to`, in
`src/act.asm`) instead of 20 columns past the text; the cursor's panel costs what it
did (`test_bar.py`: `LOOK` 984–985 µs and `ui_panel` 295–296 µs in both builds).

Everything that opened the build menu with one `SPACE` presses it twice now:
`test_game.py`, `test_link.py`, `test_reveal.py`, `test_edge.py`, and the `build` of
`tools/balance.py`, which seven tests build with (`test_fit.py`, `test_map.py`,
`test_needs.py` and `test_power.py` among them). In `test_sound.py` the first
`SPACE` still has to click, and it does. `test_build.py` and `test_route.py` run on
`tests/uitest.sna`, which has no simulation and no action menu: there `SPACE` is
still the build menu (`ui_build`).

### 9.2 HUD

Five logical rows of forty columns, in the 4×8 font ([ASSET-4](#12-asset-gaps)). Until
milestone 83 they were the five Mode 0 character rows at the bottom of the screen;
since then they live in the two Mode 1 bands of [§8.1](#81-screen-layout), where a
glyph is one byte per line and a line holds eighty of them:

```
top band     line 0-7     row 0 (columns 0-39)  |  row 1 (columns 40-79)
             line 8-15    row 2                 |  (black)
bottom band  line 176      black (the raster split)
             line 177-191 the button bar (§9.3, milestone 84)
             line 192-199 row 3                 |  row 4
```

Nothing that writes a row knows where it is: `hud_goc` turns (row, column) into the
ring address, and a cell steps right one byte. Forty columns is not much, so the
layout is fixed and every column is always written — which is also why there is no
clearing pass. **As built:**

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
`NO POWER`, `LOW POWER`, `NO OXYGEN`, `SUIT AIR LOW`, `LOW ON FOOD`, `LOW ON WATER`,
`NO ENGINEER`, `SANDSTORM`, `MERCHANT LANDED`, `COLONY LOST`, `ALL SYSTEMS OK` — because naming the
machine needs the selection the build mode has not built yet. The order is *how long
the player has*: `NO POWER`, `NO OXYGEN`, then `SUIT AIR LOW` (milestone 90: someone
outside has under a minute of air, [§6.6](#suits-at-milestone-90)), `LOW POWER`, the
two supply lines, then `NO ENGINEER` (milestone 88: a Build job waits and nobody alive
can build, [§6.9](#built-at-milestone-88)), and last `MERCHANT LANDED` (milestone 93:
news, not danger, [§6.11](#trade-at-milestone-93)).
At the empty start the line reads `ALL SYSTEMS OK`, so the first building that waits
for an engineer is said. **Since milestone 93 the texts have no trailing spaces**:
`hd_say` pads the row with `hud_to`, a blank cell cheaper than a letter, and the
90 bytes went to the merchant's texts.

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

**A HUD redraw costs 0.60 frames warm, 2.20 cold — 1.15 and 2.30 until milestone 52
([below](#smaller-at-milestone-52)), 0.62 and 1.75 until milestone 83, whose cold redraw
clears the bands first and happens only after a camera jump
([below](#mode-1-bands-at-milestone-83)) — and it has its own clock: every 16 frames
of real time.** It used to run once per wheel rotation, which broke twice over when the speed
control arrived ([§9.1](#91-controls)): the gate was `wh_slot == 0`, and at double
speed the slot counter steps by two — if the speed changed on an odd slot, zero never
came round again and **the HUD froze while the colony carried on**. Worse, tying it to
rotations meant three frames of HUD per four of simulation at `x4`, which capped that
speed at 2.3×. A fixed real-time clock fixes both: the player sees the HUD 2.6 times a
second at every speed, and `x4` delivers 3.4×.

**It used to be a full rewrite of every cell, every time.** Two things fixed that:

- **A cell cache**, 120 bytes in bank 2 — one code per cell of rows 0–2, the
  character for a glyph and `&80 + pen` for a solid bar cell. A cell whose code has
  not changed is not drawn, only stepped over. Until milestone 83 the cache was
  invalidated by `view_cam`, because a camera step turns the ring and the HUD's
  *bytes* move even though its position on screen does not; since then the bytes are
  moved with the ring ([§8.1](#81-screen-layout)) and the cache stays true. Only a
  camera *jump* invalidates it.
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
`hud_draw` was blanking those rows first. `tests/test_build.py` took one camera step
and demanded all eighty cells back, with the memory of rows 3–4 marked `#AA` first
until milestone 83; since the bands are moved rather than rewritten, a missing move
reads four columns out of place and the same comparison catches it.

2.55 frames became 1.15. What is left is arithmetic, not pixels: six stock values
converted to digits, four bars divided into cells, and 120 cache comparisons. Skipping
a whole *field* when its value has not changed would take most of that too; it needs a
per-field cache of the last value, and it has not been worth the state yet.

#### Mode 1 bands, at milestone 83

The rows did not change; where they live did ([§8.1](#81-screen-layout)), and with it
three things about how they are drawn.

- **A glyph is eight bytes, one per line.** The font in bank 7 is the asset's 4×8 Mode 0
  font converted by `tools/pack.py` — ink becomes pen 3, everything else pen 0 — 768
  bytes where the Mode 0 one was 1,536, aligned to 8 so that a glyph's lines step with
  `inc e`. The tests do not trust that conversion: `tools/hudref.py` does its own from
  the pixels, and `tests/test_pack.py` compares the two.
- **The bar cells are glyphs too**, codes `&80–&84` right after character 127: blank,
  red, green, white and the empty cell. They used to be solid cells eight lines tall
  with a path of their own; now they are the height of the capitals (lines 1–5), the
  empty cell is an outline top and bottom — side by side they make a hollow bar — and
  `hud_char` has one path. A first try drew the empty cell as white-and-black stripes,
  and the screenshot read `||||||`.
- **A camera step moves the bands** instead of rewriting rows 3–4, and a camera jump
  clears them (`hud_inval`, 400 columns with the eight lines unrolled in Gray-code
  order over bits 3–5 of `H`, ~16 ms) and redraws.

Measured in `main.sna`, paused, through a probe with interrupts off, against milestone
82: a warm `hud_draw` **12,351 → 12,032 µs**, the panel **18,741 → 16,030**, and a whole
camera step — `ui_hide`, `view_scroll`, `ui_show` — **1.4 ms cheaper** in each of the
four directions (east 33,528 → 32,069). Nothing got slower but the cold redraw after a
jump, **34,844 → 43,930 µs**, because it now clears the bands first; it happens on
centre and load, which redraw the whole world as well.

**What the screen says, checked.** `tests/hudread.py` reads the logical rows out of the
bands for every test that reads the HUD — nine of them had their own copy of the old
Mode 0 reader. `tests/test_hud.py` compares all forty band lines with
`tools/hudref.py`, black where no row is, and its boundary check marks both bands.

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

Cost: **1.75 frames** after a camera step, **0.65** on an ordinary tick ([§8.1](#81-screen-layout)), measured 0.60 by `tests/test_hud.py` at milestone 106 and **0.50** since milestone 107, when rows 3–4 got their own cache and a cell stepped over moves one pointer instead of two ([§9.3](#a-cursor-step-near-the-colony-at-milestone-107)) — 2.30 and 1.15 until milestone 52 shrank the HUD; the cold figure was 2.20 until milestone 33 paged the font in from bank 7 for every glyph drawn.

### 9.3 Build flow

A group's button, or `SPACE` `SPACE` ([below](#graphical-buttons-at-milestone-84)) →
item → a ghost follows the cursor,
snapped to the correct parity
([§3.4](#34-anchors-are-centres)) — half a tile on, or half a tile back at the world's
east and south edges ([§8.2](#the-world-has-an-edge-at-milestone-78)) — with invalid
footprint tiles tinted. Fire commits,
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

#### Smaller and faster, at milestone 73

`src/build.asm` went from 1,068 bytes to **788**, and bank 2's code area from 608
bytes free to **888**. Every routine got faster or stayed the same in every case the
check tried. The one that matters is `bd_check`, which runs on every step of the
cursor in PLACE: a large dome's footprint went from 5.5 ms to **2.1 ms**, a 3 × 3
structure's from 1.2 to 0.6.

- **`bd_ok` is six instructions, 8 bytes instead of 25.** A tile is allowed when
  `byte & #37` is 0, 1 or 7: no occupancy, and ground, dust or foundation. `and`,
  `ret z`, `dec a`, `ret z`, `cp 6`, `ret`. It leaves every register but `A` alone. The old one saved `BC` and set `A`
  to 0 or 1, which no caller reads — they all test `Z`.
- **So `bd_check` stopped saving registers around it.** Every tile paid three `push`
  and three `pop`. The bad tiles are now counted in `C`, and `bd_nbad` is gone. Each
  row starts 128 bytes after the last one, the layout `tile_addr` already uses, so
  the check calls `tile_addr` once instead of once a row. The commit's stamp does the
  same.
- **`bd_rect` works in 8 bits.** The centre plus 128 is an unsigned byte. Its
  difference from the width keeps a ninth bit in the borrow, and `rra` halves all
  nine at once. The result is the first tile plus 64, which is inside the world
  exactly when it is at most 128 − W, one unsigned `cp`. Until milestone 72 this was
  16 bits through `ob_sext`, and a `bd_range` with two subtractions of its own. The x
  axis still returns before it touches `bd_ty`, as before, because `ui_rect` reads
  the pair either way.
- **`bd_link` walks the dome table with a pointer.** It used to pay an
  `ob_dome_live` and an `ob_domeadr`, two multiplications by 24, for every one of
  the 64 slots. It now runs straight after the record is written, while bank 6 is
  still in the window, and its "itself" check after the loop is gone: the loop
  already skips the new dome.
- **Both records come from one routine** (`bdk_rec`): `cx`, `cy`, the parameter, one
  byte (the room or the structure's size), `DS_BUILDING`, two zeros. The search that
  found the free slot leaves `HL` on its state byte, so the record starts four bytes
  back instead of at a second address calculation.
- **The commit pages less.** Bank 6 for the search, the record and the link; bank 4
  for the stamp; then bank 1. Payment, the edges, the Build job and `ob_touch_n`
  live in banks 0 and 2 and do not care. `bd_stamp`, `bd_link` and `bd_postjob` had
  one caller each and are now inside `bd_commit`. `jb_post_build` keeps `A`, so the
  node is loaded once for it and for `ob_touch_n`.
- **`bd_afford` and `bd_stock_pay` load both costs with one `ld de,(bd_metal)`** and
  take each from its stock a byte at a time, instead of building `DE` and an
  `sbc hl,de` per material. `bd_afford` turns the last borrow into its 0 or 1 with
  `sbc a,a` · `neg`.
- **`bd_select`** tests the parity with `rra` instead of `and 1`, reaches `cur_hy`
  with `inc hl`, and works out the structure's size with `cp` · `sbc a,a` · `and 2`.
- **Six variables are gone:** `bd_item`, which was written and never read; `bd_span`,
  which was neither; `bd_cy`, `bd_row`, `bd_nbad` and `bl_i`.

[§6.5](#smaller-and-faster-at-milestone-67)'s table for the whole of `bd_check`,
measured again the same way, through a probe with interrupts off:

| Placement | Milestone 72 | Milestone 73 |
|---|---|---|
| a 3×3 that needs no material | 1,221 µs | **599 µs** |
| the pump at a shore, the water in the first row of the scan | 1,291 µs | **669 µs** |
| the pump on dry ground, 7×7 with nothing in it | 1,987 µs | **1,365 µs** |
| the mine with no vein, 8×8 | 2,761 µs | **1,778 µs** |

The check was a script kept out of the repository, on `build/main.sna`. It called
every routine directly and recorded `A`, `F` and every byte that changed in all eight
banks. Bank 2's code area moved by 280 bytes, so a byte there was keyed by the label
before it and the offset from it. It made 2,378 calls:

- `bd_ok` for all 256 bytes;
- `bd_select` 200 times, for every item and two that do not exist, at every cursor
  parity;
- `bd_rect` 400 times, with every centre and size from 1 to 8;
- `bd_check` 400 times, on random planes, near the edges and outside the world;
- `bd_afford` and `bd_stock_pay` 400 times each, around the cost and with random
  16-bit stocks;
- `bd_commit` 400 times, on random dome, structure and job tables. These included
  full tables and 27 first buildings with no dome to join;
- `bd_redraw` 126 times, after a commit, with the camera near the site.

All 2,378 were identical. The flags of `bd_ok` and `bd_afford` were compared as `Z`
only, because the old routines' other flags and `bd_ok`'s `A` were never read.

| | Milestone 72 | Milestone 73 | Faster in |
|---|---|---|---|
| `bd_ok` | 13,528 µs | 10,936 µs (−19 %) | 256 of 256 |
| `bd_select` | 37,724 | 35,747 (−5 %) | 165 of 200; the other 35 are the items that do not exist, the same |
| `bd_rect` | 85,472 | 35,688 (−58 %) | 400 of 400 |
| `bd_check` | 715,170 | 346,238 (−52 %) | 400 of 400 |
| `bd_afford` | 26,600 | 24,039 (−10 %) | 400 of 400 |
| `bd_stock_pay` | 30,400 | 28,000 (−8 %) | 400 of 400 |
| `bd_commit` | 3,454,245 | 1,526,005 (−56 %) | 400 of 400 |
| `bd_redraw` | 1,915,451 | 1,897,516 (−1 %) | 126 of 126 |

One commit was 2 µs *slower* at first: with the dome table full, the search fell into
a `jr` to the shared failure exit. The failure now follows the dome search, and the
structure search, whose loop got 10 T-states a slot faster, does the jumping.

**A trap the rewrite hit:** an `assert cur_hy == cur_hx + 1` in `build.asm` assembled
in `main.sna` and failed in the uitest build, where `ui.asm` comes after `build.asm`
and the labels are not known yet. It was redundant anyway — `ui.asm` asserts the
same pair, and `view.asm` the `vr_*` pairs `bd_redraw` now writes as words — so both
asserts stayed where the labels are. Like milestone 67's lost sign
([§6.5](#smaller-and-faster-at-milestone-67)) and milestone 72's rounded `/ 256`
([§9.4](#smaller-and-faster-at-milestone-72)), it showed up in only one of the two
builds: the uitest-based tests have to run too.

**What the planted faults found.** Thirty-five faults were run against the script and
six tests: `test_build.py`, `test_terrain.py`, `test_reveal.py`, `test_map.py`,
`test_game.py` and `test_link.py`.

- **The script caught thirty-four.** One of them only by never finishing: a
  structure's redraw box with the width taken from `bd_tx` ran past three seconds. It
  missed `bd_check` clearing seven rows of `bd_bad` instead of eight. Every case
  started from the same snapshot, and nothing in it had ever left the eighth row
  dirty.
- **The six tests together caught twenty.** `test_reveal.py` caught thirteen,
  `test_game.py` eleven, `test_build.py` nine, `test_link.py` six, `test_map.py` five
  and `test_terrain.py` none. They let fifteen through:
  - all three in `bd_select`: the cursor not snapped to the footprint's parity in x,
    the parity tested with `and`, and a mine given size 2;
  - a dome's redraw returning `Z`, so the ghost would not wait for its rows; and the
    structure's box with the wrong width;
  - three in `bd_rect`: the east edge one tile short, `bd_ty` overwritten when x is
    out, and the ninth bit dropped;
  - three in `bd_check`: seven rows cleared, a footprint outside the world allowed,
    and the row carry lost where a row crosses a page;
  - both in `bd_afford`: Bioplastic ignored, and `A` = 255 for "no";
  - the payment losing its borrow;
  - the stamp keeping bit 3.

  The tests build through the interface at a handful of places, so the world's
  edges, odd parities and empty tables are where they do not go.
- **`tests/test_place.py` catches all thirty-five.** Its first version missed the
  stamp keeping bit 3: none of its planes had a byte with bit 3 set under a
  footprint. They do now.

`tests/test_place.py` calls `build.asm`'s entry points directly in `main.sna`, against
rules written from the prose:

- **`bd_ok`** for all 256 bytes.
- **`bd_select`** for every item and two that do not exist, at random cursors: the
  record copied, the cursor on the footprint's parity, the structure's size.
- **`bd_rect`** at every centre and size from 1 to 8. When x is out, `bd_ty` must be
  what it was.
- **`bd_check`** on random planes with a mountain rim at |x|, |y| ≥ 62, as the
  generator leaves it, so that `bd_res`'s margin stays on the plane. Cursors are near
  the edges, outside the world, and anywhere. `bd_bad` and `bd_nres` start from
  garbage. The material is `test_terrain.py`'s model.
- **`bd_afford` and `bd_stock_pay`** around the cost, and with random 16-bit stocks.
- **300 commits** on random dome, structure, graph and job tables, full ones and
  first buildings included. The rule covers the slot and its record, the stamp, the
  payment, the edges to the nearest live dome (in 8 bits, as the Z80 does it, ties to
  the first), the Build job and `ob_idx` — or 255 and nothing at all.
- **200 redraws** with stubs on `dirty_push`, `vr_tiles`, `ob_struct` and
  `ob_clip_full`. A dome must push one `DK_SITE` per row and return `NZ`. A structure
  must fill `vr_*` and, if visible, draw itself.
- **Time**, in ten cases, none slower than this milestone measured:
  - `bd_check` for 4 × 4, 6 × 6, 8 × 8 and 3 × 3 on clear ground, for a mine finding
    its vein, and outside the world;
  - `bd_rect`, and `bd_afford`;
  - a dome's and a structure's commit into the last free slot.

  With milestone 72's `build.asm` all ten fail.
- **Seven negatives:**
  - foundation refused;
  - the first tile one to the right;
  - the check's next row +64;
  - seven `NO_MACH`;
  - the link counting the new dome itself;
  - `A` = 255 from `bd_afford`;
  - a dome's redraw returning `Z`.

**A contract the test made visible:** `bd_commit` stamps the footprint at `bd_tx`,
`bd_ty`, which the check left there — it does not work them out again. The interface
always validates before it commits, so this holds. A test that calls the commit on its
own has to set them first, and the first draft of this one did not: it stamped a
structure at (0, 0).

#### Graphical buttons, at milestone 84

The commands are a bar of buttons in groups, as in Planetbase, in the bottom Mode 1
band of [§8.1](#81-screen-layout). Sixteen slots of 20 pixels on lines 177–191; line
176 stays black, because the raster split happens there. In `LOOK` the bar holds the
six groups and `?`. A group opens its own buttons in the same bar, with itself white
in slot 0. `?` is in slot 15 of every bar.

| Group | Key | Its buttons |
|---|---|---|
| DOMES | `D` | `S` `M` `L` the size · `O` oxygen, `C` canteen, `Q` quarters, `G` greenhouse, `F` factory, `B` lab, `E` medbay, `N` control, `T` storage, `U` lounge |
| CORRIDOR | `R` | none: the group is the corridor |
| POWER | `P` | `S` solar panel, `T` wind turbine, `C` collector |
| RESOURCES | `E` | `X` extractor, `M` mine |
| TRANSPORT | `T` | `A` airlock, `P` landing pad, `C` the ship's line, where `FIRE` calls ([§6.11](#who-comes-at-milestone-91)), `M` the merchant's line, red until a merchant lands ([§6.11](#trade-at-milestone-93)) |
| MANAGE | `M` | `I` info, `F` fit, `S` save, `L` load, `H` centre, `D` demolish (milestone 101, [below](#demolition-at-milestone-101)) |

```
 ...######....        a button: an octagon 18 x 15 at pixels 1-18 of the slot,
 ..#........#..       12-pixel top and bottom, corners cut by three; the
 .#.symbol...#.       symbol 12 x 11 at pixels 4-15 (bytes 1-3), lines 2-12;
 #..12 x 11...#       the key's letter, the HUD font's 3 x 5 body, in byte 0
 D#...........#       of lines 10-14, over the bottom-left corner
```

**The Planetbase look.** Planetbase's buttons are black octagons with a green rim and
a flat green symbol, which is what the band's pens already are (black, red, green,
white; [§8.1](#81-screen-layout)). Green is a button, white is chosen (the open group,
the item, the dome's size and room), and red is a button that cannot be used here: a
room that does not fit the size, FIT off a dome, SHIP without a Control room, a pad or
with a ship already coming, DEMOLISH where nothing can be taken down (milestone 101). A red button is drawn, not hidden, so nothing moves under
the player's eye.

**The symbols are drawn, not converted — a change from what was agreed.** The plan
was to convert the Mode 0 room and structure icons into the buttons. Tried at 12 × 11
in one colour, most of them are blobs: the oxygen, greenhouse, storage, mine and pad
icons carry their meaning in colour, not shape, and Planetbase's symbols are shapes.
The 33 symbols are drawn as 1-bit pixel art in `tools/buttons.py` and packed by
`tools/pack.py` into bank 7 (`btn_gfx`, 33 × 17 bytes; 35 since milestone 101). `assets/` is untouched; the
file is tool data like `tools/econ.py`'s tables, and art from `CPCArt` can replace it.

**The collector is in POWER, not RESOURCES — also a change.** The groups were agreed
with the collector among the resources. In this game it stores Power
([§6.5](#65-economy): 40 / 160 / 360), so it sits with the panels and turbines that
fill it.

**A group's letter opens it in `MENU`**, with the item it had last if that belongs to
it, its first otherwise, and closes it again from `MENU`, `PLACE` or `LINK`. **An
item's letter goes straight to `PLACE`.** A size changes the dome without changing
state. A room goes to `PLACE` if it fits the size and does nothing if it is red;
a room that stops fitting when the size changes gives way to the next that fits
(`rm_fix`). CORRIDOR is a group of one: `MENU` with the corridor, `FIRE` for `LINK`.
MANAGE opens the menu of [§9.1](#what-can-be-done-here-at-milestone-80).

**Only the letters on the bar work, and a press does one thing.** `bk_scan` reads the
visible bar's keys straight from `key_now`, in code `bk_gen` writes when the bar
changes: `ld a,(key_now + line) : and mask : jr z,hit : inc c`, 9 µs a key. Seven
letters in `LOOK` cost 63 µs; a table and a loop would be 112. The held key is
remembered by its *key*, not its slot: `E` opens RESOURCES from slot 3, and in the bar
that appears `E` is slot 0. Remembering the slot, the same press closed the group it
had just opened. The bar is not scanned in the slot chooser or the fitting, which have
keys of their own.

**The arrows in `MENU` still walk the flat list of this section**, and the bar follows
the item's group; `SPACE` `SPACE` reopens the last group on the same item. Every test
and tool that drives the build menu by arrows (`tools/balance.py`'s `build`,
`test_game.py`, `test_link.py`, `test_reveal.py`, `test_edge.py`, `test_far.py`)
works unchanged.

**The bar is redrawn only where it changes.** `bar_sync`, at the top of `ui_panel` and
outside its held message, compares ten bytes as it reads them (state, item, room,
the menu's choice and mode, FIT's answer, `hud_gen`, the three conditions of a
ship); if any differs, `bar_want` says what each slot should be and the slots that
differ are drawn. After a camera jump `hud_gen` has changed and every slot is drawn
again; a camera step moves the bar with the bands ([§9.2](#mode-1-bands-at-milestone-83)).
The red rooms come from ten `rm_fits`, 3.3 ms, so `bar_want` keeps them per size.

**Two buttons a frame.** A button costs 2.9 ms (`sl_draw`, in bank 2; an empty slot
1.4). The first draft drew the whole bar at once — 84 ms, then 60 after a faster
composition — and `test_game.py` lost a press: the arrow that crossed from one group to
the next held the frame for three, and the next arrow, down for three frames, fell
inside it. `bar_more` now draws at most two a frame and `ui_tick` calls it while any
remain: a group opens in eight frames, from left to right. The worst frame is
**8.6 ms** (the DOMES bar after a camera jump).

#### The help screen, at milestone 84

`?` (the `/` key) on any bar shows every button with its name in white and one line
in green on what it does, in three columns of twelve, and a last row that says the
letter on a button is its key. Any key goes back, and does nothing else.

- **The whole screen in Mode 1, with interrupts off**, as the disc does the opposite
  ([§11](#11-save-and-load)): `is_m1` sets Mode 1 and the bottom band's pens
  everywhere. The buttons are drawn by the bar's own `sl_draw`, so the screen shows
  exactly what the bar shows; groups white, the rest green.
- **Going back is a camera jump to the same place**: a clear screen, `is_on`, the
  view, the bands from scratch, the ghost. The state, the bar and the view are what
  they were.
- **It waits for the key to be let go** — the `?` that opened it, and the key that
  closes it. Without that, a key held past the redraw (0.4 s) acted in the game as
  well: `D` closed the help *and* the DOMES group behind it.
- **The text is the 33 buttons' names and lines, 790 bytes** of bank 7's text block,
  which grew from 1,280 to 2,048 for it. MANAGE's menu reads its rows from there too.
  Opening takes **358 ms** (screen clear 86, buttons 96, text the rest); the names
  are walked once in order, not looked up per button (90 ms less).

**Cost, frame by frame.** A `ui_tick` with nothing pressed must not get slower, and
seven to fifteen letters a frame are new work. They are paid for by questions that
asked `in_hit` one key at a time on every frame: the speed keys (four `in_hit`,
~230 µs) and `H` (~50) are one `and` each, `LOOK`'s `S`, `L`, `C`, `FIRE` and
`SPACE` two, and `PLACE`'s and `LINK`'s `ESC` and `FIRE` one; `MENU` returns at once
when no key edge came. `ui_panel`'s signature is compared as it is read, as the
bar's is. Measured in the real game, paused:

| Nothing pressed | Milestone 83 | Milestone 84 |
|---|---|---|
| `ui_tick` in `LOOK` | 1,455 µs | **985** |
| `ui_tick` in `MENU` | 1,259 | **862** |
| `ui_tick` in `PLACE` (DOMES: 15 letters) | 1,252 | **1,036** |
| `ui_panel`, nothing changed | 344 | **297** |

**Memory**: bank 0 1,449 bytes (`bar.asm` 1,073: the button table, `bk_scan`, the
bar's signature and `bar_want`, and `sl_draw`'s tables and buffer; `help.asm` 280;
`ui.asm` 96), bank 2 746 (`button.asm` 637, `act.asm` 109), bank 7 1,329 (the text
block 768 more, the symbols 561). Bank 2's code area has **52** bytes left
([§15](#15-open-risks)).

`tests/test_bar.py` plays the real game against a bar it draws itself
(`tests/barread.py`: the octagon, the symbols from `tools/buttons.py`, the font from
`tools/hudref.py`, the letters from its own prose, not from `bt_tab`): every group,
the three sizes and the ten rooms in each with the right ones red, every item, a
letter not on the bar, closing and remembering, the corridor, a key held 25 frames,
the arrows across groups, `SPACE` `SPACE`, `1`–`4`, `H` as a camera jump and as a
step, `FIRE` on a dome, and the help screen entry by entry, closed with a key held
for 45 frames, after which state, bar and view are as before. Nine negatives: no
scan, no held key, a bar that ignores `hud_gen`, no red rooms, no letters, a help
screen that does not wait, the speed mask, `LOOK`'s `FIRE` and `H` lost. Its cost
ceilings are the table above, a button ≤ 3,100 µs, a frame of the bar ≤ 10,000 and
the help screen ≤ 400 ms.

`tests/test_loop.py`'s stubs moved from `&3B00` to `&3C00` and `tests/test_screen.py`'s
buffer into bank 1's window: the code of bank 0 now ends at `&3B69`.

#### Every building needs a neighbour, at milestone 85

The player asked for it in so many words: *corridors are worked out by themselves
when a building is placed, from where it is relative to the other rooms; apart from
the first, every building needs a room near it to be built and joined; the build
cursor is red wherever you cannot build, for distance or for ground. Structures
need other structures near them, joined not by a corridor but by a path on the
ground, with no cover.* And, asked once: **near is 12 tiles**, and a new dome is
joined to **every** dome near it, not only the nearest. `src/link.asm` is that
rule; `tools/reach.py` is the same rule in Python, written from this text.

- **The first building in the world goes anywhere the ground allows.** Every
  other needs some building — dome or structure, built or still a site — within
  `AL_RANGE` = 12 tiles.
- **A dome gets a covered corridor to every dome a corridor reaches in at most 12
  pieces** ([§9.4](#94-corridor-routing)'s router, both ends tried, in table
  order), over ground that can be built on, **up to `AL_MAX` = 4**. Each chosen
  corridor holds its tiles for the next: two corridors of the same dome never
  share a tile. The `ΔΙΑΔΡΟΜΟΣ` button stays, for anything the rule did not join.
- **A structure — or a dome that found no corridor — gets a path on the ground**
  to the nearest building: an L from its centre tile to the other's centre tile,
  along x first or along y first, counting only the tiles outside both footprints:
  at most 12, every one buildable. The shorter wins; on a tie the first found.
  The path becomes foundation with **occupancy 2** — the value the world byte
  always had for "corridor" and nothing used ([§3.5](#35-the-world-byte)) — so it
  looks like levelled ground, nothing can be built on it, and `I` calls it `PATH`.
  It is an *outdoor edge* of [§6.2](#62-the-node-graph): whoever walks it is
  outside.
- **Otherwise the ghost is red and row 4 says why**: `TOO FAR` when nothing is in
  range, `PATH BLOCKED` when something is but every L within 12 crosses ground or a
  building that blocks it. Red tiles still mean the footprint itself.

**What the ghost shows is exactly what `FIRE` builds.** The check runs on every
cursor step, so the ghost carries the corridors or the path in green, and the
panel's cost is the total — the building plus 6 Metal and 3 Bioplastic per
corridor piece, the catalogue's price. `FIRE` replays the same list: `cr_commit`
and `cr_redraw` for each corridor, the stamp, the edge and a redraw of the two
legs for a path.

**The site's rows go on the dirty list before the corridors.** A diagonal starts
in the corner of the square footprint, and a site row ([§6.9](#69-construction),
`dh_site`) draws only the dome over the ground, for speed. With the corridors
committed first, their rows came off the list first and the site's rows erased
the corner after them: 7 bytes of the diagonal gone until the next full redraw.
`tests/test_fit.py` found it, on the greenhouse it builds; `uip_fire` now calls
`bd_redraw` and then `al_commit`, keeping the first one's flags for the ghost.

**A path redraws its own tiles, not the L's rectangles.** The first version redrew
the two legs from centre to corner to centre, which take in a strip of both
footprints: a solar's `FIRE` took 171 ms, 68 of them redrawing the dome across the
way. `al_leg` walks each leg again, keeps the first and the last tile that lies
outside both footprints, and redraws that strip — terrain, then whatever stands on
it. No neighbour's autotile can change: a path is laid only on ground, dust or
foundation, and no variant counts those. The worst round of the loop around a
`FIRE`, from `tests/test_reach.py` and `tests/test_reveal.py`:

| `FIRE` | Worst round |
|---|---|
| Dome S, one corridor | 100 ms |
| Dome S, three corridors (the most the start colony allows) | 106 |
| Dome M, a diagonal from its own corner | 120 |
| Dome L, a diagonal (`test_reveal`, 8 site rows and 3 corridor rows after it) | 110 |
| Solar, a path of 7 tiles | **127** (171 with the rectangles; 105 with no path at all) |

Five things the rule decided that the request did not say:

- **A dome with no corridor falls back to a path** — until milestone 86, when the
  player made airlocks the only doors and such a dome became red, with
  `NO CORRIDOR FITS` to say why ([below](#airlocks-are-the-doors-at-milestone-86)). A
  dome close to another but in the near-diagonal zone that has no corridor shape
  ([§9.4](#94-corridor-routing)), or with a rock across the way, was joined on the
  ground instead.
- **At most four corridors.** The ghost's undo log is sized for the worst ghost
  ([§4.2](#42-the-eight-banks)): an L dome's frame and four corridors of 13 marks
  is 1,016 of its 1,160 bytes, and a fifth would not fit. A dome with five domes
  within 12 tiles, all routable and not crossing, is rare; the cap is in
  [§15](#15-open-risks).
- **Corridors are held while the search runs.** A chosen corridor's tiles get bit 5
  of the world byte — occupancy 2 — for as long as `al_plan` runs, outside both
  footprints only, and lose it before it returns. Inside the footprints is not
  needed (the router never checks there) and was wrong: the test found a world
  where the other dome's footprint already had the bit.
- **`ui_bad` carries the reason.** It was the count of bad tiles, 255 off the
  world, or 1 for a missing water or ore; with four reasons and the panel's
  signature keyed on `ui_bad`, a pump moving from one bad tile to dry ground kept
  saying `BLOCKED` (a milestone 31 bug nobody had seen). It is now `&F0` plus the
  reason when the tiles are fine — `&F1` water, `&F2` ore, `&F3` too far, `&F4`
  blocked — and `bd_nres` starts from zero on every check.
- **The panel's signature holds the cost, not the corridor's length**: in `PLACE`
  the total changes with the corridors. The low byte is enough — two totals of the
  same item differ by 6k, k ≤ 48, and 256 is not a multiple of 6.

`bd_link` no longer links anything. Until now every site got an outdoor edge to
the nearest live dome, however far, with nothing drawn: the reason buildings could
be scattered anywhere. The edge was also the only thing that made a site reachable
([§6.9](#69-construction)); `al_commit` does that now, right after `bd_commit`.
`bd_commit` got faster for it: 9,362 → **4,656** µs for a dome, 5,591 → **892**
for a structure.

**The cost, honestly: a cursor step near buildings is slower.** The check walks
both tables and up to two L's per candidate. A first version paid a page switch, a
multiply and a footprint for every slot of both tables, and two L's for everything
within 20 tiles: 29 ms for a solar beside the colony, 40 for a dome. Now a pointer
walks the tables with bank 6 in (six instructions per empty slot), a candidate is
dropped unless its centre is within 40 half-tiles on both axes — exact: two
footprints reach at most 8 half-tiles from their centres, so 41 leaves a gap of
13 — and an L is walked only when the gap in x plus the gap in y, a lower bound on
any L, beats the best so far; the second L only when the first missed that bound.
`ui_validate` with the probe, in the colony of [§10.1](#101-start-state):

| | Milestone 84 (`bd_check`) | Milestone 85 |
|---|---|---|
| Dome S, one corridor | 813 µs | **9,124** |
| Dome S, no corridor, path | 823 | **14,684** |
| Solar, path | 607 | **6,956** |
| Solar, too far | 610 | **3,558** |

In the game a step of the cursor with a solar beside the colony went from 31 ms to
40–46 when it does not scroll; with the camera scrolling, 81–99 ms against 81–88.
Far from everything the check is the walk of the tables, ~3 ms.

**Memory.** `link.asm` is 1,041 bytes in **bank 2**, and bank 2 had 52. They came from
the twelve machine sprites, 1,584 bytes, which moved to **bank 5** above the object
index ([§4.2](#42-the-eight-banks)): the object pass already pages bank 7 for the
greenhouse's plants in the same slots, and now pages bank 5 for machines. The disc
loads `BANK5.BIN` into the loader's scratch and the endgame copies it into place
after bank 2's code; a load clears bank 5 only up to it. Bank 2's code area has
**608** bytes left; bank 0 grew by 15 (`ui.asm`), and bank 7's text block by 16
for `PATH BLOCKED`.

`tests/test_reach.py`: 504 placements — random worlds, domes and structures around
the cursor, every item, four scenes exactly at the range — against `tools/reach.py`:
`ui_bad`, the corridors and their length, the path and its shape, `bd_nres`, the
total cost, and a world left exactly as it was. 160 ghosts, mark by mark against
the rule, and the undo puts the screen back. `FIRE` in the real game for a dome S,
a solar and a dome M whose diagonal starts in its own corner: the world, the
edges, the corridor table, the payment, the screen byte for byte the full redraw
once the last row is out, and the worst round of the loop under 200 ms, the
ceiling of an L dome's placement in `tests/test_reveal.py`. The panel in six
steps, one where only the reason changes and one where only the cost does.
Ceilings on the four costs above, and ten negatives: range 13, no hold, no
release, only the first L, the coarse test one tile short, a path with occupancy
1, the corridors on the list before the site, a stale `bd_nres`, `ui_bad` without
the reason, and no cost in the signature. `tools/balance.py` places what the
scenarios build where the rule allows: its spots are checked against the start
colony with `tools/reach.py`, and `build()` moves anything the colony grown so far
no longer accepts to the nearest place that does. Three scenarios build domes in a
field far from the colony and then ask for the corridor by hand —
`tests/test_link.py`, `tests/test_return.py`, and `tests/test_reveal.py`, whose L
must appear in eight rows with no corridor rows between them; they switch the rule
off with `balance.no_link`, which makes `al_find` return at once, as if every
building were the first.

#### Airlocks are the doors, at milestone 86

The player, after milestone 85: *airlocks join only the nearest building, and they are
the entrances and exits of the base* — and then, asked, that an airlock's join is a
covered corridor to the nearest dome, that structures join an airlock or another
structure but never a dome, and that a dome with no corridor is red
([§6.2](#62-the-node-graph)). `src/link.asm` and `tools/reach.py` now tell three kinds
apart:

| New building | Joins | With | When there is none |
|---|---|---|---|
| Dome | every dome a corridor reaches in at most 12 pieces, and every airlock that has no corridor yet — up to 4 | covered corridors | red, unless no dome exists |
| Airlock | the dome whose corridor is shortest (the first on a tie) | one covered corridor, meeting the airlock from the north or the south | red, unless no dome exists |
| Structure | the nearest airlock or other structure | a path on the ground | red, unless no structure exists |

**"The first building needs nothing" holds per kind.** The player said the first
building stands alone. Taken literally, a solar panel built first would leave no dome
anything to join, and no dome could ever be built. So a building is free when nothing
of the kind it would join exists anywhere in the world: the first dome, the first
airlock with no dome, the first structure. That is my reading, and it is the one
`tools/reach.py` states.

**Why red, now three ways.** `TOO FAR` when nothing it could join is within range;
`PATH BLOCKED` when a corridor or a path within 12 crosses ground or a building that
blocks it; and, new, **`NO CORRIDOR FITS`** when a dome was close enough that an axial
corridor would have been at most 12 pieces, but no shape exists — the near-diagonal
zone of [§9.4](#94-corridor-routing), or two domes too close for any corridor. Without
it, a dome right beside another said `TOO FAR`, which reads as a bug. `ui_bad` is
`&F5` for it, and the text block grew by 16 bytes.

**The airlock is a corridor end of size −1.** The router computes a radius in tiles as
size + 2, so −1 gives 1: exactly the airlock's 2×2. Its doors are north and south, so
`cr_side` refuses to start anything from an airlock, and allows into one only the two
shapes that arrive vertically: the axial run north–south, or a diagonal that bends to
vertical. The corridor record therefore always has the dome as `a`, the end it is
drawn from, and the airlock's node (64 + structure) as `b`. `cr_read` reads that node
from the structure table, and the two places that give the far end a door —
`ob_conn_scan` and `cr_redraw` — skip a `b` of 64 or more, because the airlock's doors
are part of its sprite. Since milestone 96 they are the two that give it a joint,
`jt_mark` and `crr_conns`, and they skip it the same way.

The checks cost `cr_plan` 15–38 µs per geometry, and `tests/test_corridor.py` holds it
to milestones 72 and 81. They were paid back in the same two routines. The "not from
an airlock" test sits where `cr_side` already loads the size: `add a,2` became
`inc a / ret z / inc a`, 6 T instead of 22. `cr_read` copies the three bytes with three
`ldi` and reads the state after them, instead of a separate lookup before an `ldir`:
56 T less per end. Every geometry of `cr_plan` is now faster than before the airlock,
the axial 447 → 429 µs, the far side 808 → 800.

The door scan paid for its own check the same way. `ob_conn_scan` walked the corridor
table with `HL`, round the stack three times a record, and made each door's bit with
a loop; the airlock's `cp MAX_DOME` put the worst object index of
`tests/test_oibuild.py` at 165,502 µs against milestone 82's 165,237. It walks with
`IX` now and reads the bit from an 8-byte table: **158,843 µs**, 6.4 ms under 82 and
two bytes smaller, and the ceiling is the new figure.

**An airlock alone waits for its dome, and a counter says so.** A dome joins an
airlock that has no corridor yet. Looking for one means walking the 32 structure
slots on every cursor step with a dome in hand: 740 µs. But such an airlock exists
only when one was built with no dome in the world, so `al_commit` counts them in
`EC_FREELK` (byte 63 of the economy, saved with it): +1 for an airlock that went in
alone, −1 for each corridor a dome gives one. The walk runs only while the count is
not zero.

**The start colony has an airlock** ([§10.1](#101-start-state)), north of the Oxygen
dome, at (0, −10): a vertical corridor of two pieces, and the airlock on
(−1..0, −6..−5). North is the water, and west the vein, so the first pump and the
first mine of every scenario join it.

**The cost, honestly.** `ui_validate` with the probe, in the start colony:

| | Milestone 85 | Milestone 86 |
|---|---|---|
| Dome S, one corridor | 9,124 µs | **9,180** (+56) |
| Dome S, no corridor | 14,684 (a path) | **6,790** (red) |
| Solar, path | 6,956 (to the Oxygen dome) | **7,525** (to the airlock) |
| Solar, too far | 3,558 | **2,249** (only the structures) |
| Airlock, corridor | — | **6,441** |

The dome with a corridor is slower by 56 µs, the airlock checks in the router and
`al_set` less what `cr_read` gave back. Without `EC_FREELK` it would have been some
800. A `FIRE` of an airlock with its corridor takes 144 ms in the worst round, under
the 200 of an L dome.

`tests/test_reach.py` covers it in all four of its parts:

- the random scenes now carry airlocks, the degree of every node, and footprints
  marked occupied, as `bd_commit` leaves them. Before, a corridor could pass through a
  third dome, and the ghost drew the same tile from two corridors: the Z80 and the rule
  agreed, on a world that cannot exist. 12 domes joined an airlock and 11 airlocks a
  dome, and 20 scenes said `NO CORRIDOR FITS`;
- scenes at the edge: an airlock 12 and 13 pieces under an L, a dome above an airlock
  with and without an edge, an airlock between two domes, the near nearer than the far;
- `FIRE` of an airlock south of the Canteen, checking which end each corridor record
  names;
- a first airlock in a world without domes, then the dome that joins it.

Its seven new negatives:

- into an airlock horizontally or diagonally;
- a corridor that starts from an airlock;
- a structure joined to a dome;
- an airlock with an edge taking another;
- `NO CORRIDOR FITS` said as `TOO FAR`;
- the airlock keeping the last dome rather than the nearest;
- an airlock alone not counted.

**Milestone 87 changed what it reads, not what it asks.** "Has its corridor" is
`ST_JOINED` now ([§6.2](#inside-and-outside--milestone-87)): the random scenes take
it from the same degree draw that meant "has an edge" at 86, so the scenes are the
same scenes. The ship sits in slot 0 of half of them, drawn from a generator of its
own, and two scenes at the edge put a solar panel next to it — alone, it is the first
structure; with an airlock further off, the path goes to the airlock. `FIRE` checks
the ground link to `reach.anchor` and **no** corridor edge instead of the corridors'
edges; the first airlock in a world without domes is tied to the colony's airlock by
the ground, and the dome after it to the new airlock, the nearer. That scene now
clears the graph along with the domes: the first new dome takes node 0, and would
have inherited the old one's row. The scenes at the edge draw from their own generator
too, so adding one no longer moves the random ones — which had dropped four-corridor
domes to two in 500 — and three of them are four-corridor domes. Three new negatives:
the ship counted as a structure, an anchor that does not keep the nearest, and an
airlock never marked `ST_JOINED`. The airlock-with-a-corridor negative needed a scene
with a second, lone airlock far away: with none, `EC_FREELK` is 0 and the Z80 never
looks at the structures at all, so the cut check was never reached.

#### Paths on the ground, at milestone 94

The player, looking at milestone 93's pictures: *no foundations under the domes; use
the foundation's sprite for the paths outside.* The colony sat on grey — the landing
zone's 9 × 9 of foundation ([§5.8](#58-cleanup-and-the-landing-zone)) and every dome's
square — and the walks between airlocks and the ship, free since milestone 87, were
drawn by nothing. Now:

- **A dome keeps its ground** (`bd_link`): only the occupancy goes down. A structure
  still becomes foundation, and its path ([§9.3](#every-building-needs-a-neighbour-at-milestone-85))
  is unchanged.
- **The landing zone is ground**, so the first domes beside the ship stand on the
  planet ([§5.8](#58-cleanup-and-the-landing-zone)). The test colony's buildings stand
  on ground too (`src/colony.asm`: the pad and the airlock would keep foundation,
  but telling them apart there takes 8 bytes and 5 are left).
- **An airlock's ground link is drawn, and the first structure's** — the ones that
  stay; a dome site's goes when the dome is finished and would leave a path to
  nowhere. `lk_draw` (in bank 1, [§4.2](#code-in-bank-1-at-milestone-94)) walks an L
  from the new building's centre tile to the other end's, along x first, outside both
  footprints, and `al_cbr` makes foundation **only of free ground that can be built
  on** (`bd_ok`): water, mountain, rock, craters, corridors and buildings stay, and the
  path passes over them unseen, as the colonists do. **Without occupancy**: a ground
  link has no length limit, and a path from the ship to a far airlock must not cut the
  ground the player will build on. It is drawn **after** the corridors, so an
  airlock's own corridor is not floored under, and each leg is redrawn only **from its
  first to its last tile that changed**: an airlock south of the Canteen walks its L
  straight through the colony, where nothing changes, and redrawing the whole leg had
  its `FIRE` at 219 ms against the ceiling of 200. It is 152, from 149.

`tests/test_reach.py` checks the world after `FIRE` against `tools/reach.py`, which has
the rule too (`ground`): a dome's footprint ground and occupied, an airlock's L. Its
first airlock, in a world without domes, draws 34 tiles of foundation over the field
and the desert and none through the colony. Five more faults, each caught: a dome with
foundation as in 93, the ground link not drawn, drawn with occupancy like a path, drawn
over water and buildings, the whole leg redrawn. `tests/test_place.py` and
`tests/test_build.py` say the same of a dome placed by `bd_commit` and by the keys.

#### Demolition, at milestone 101

Until this milestone nothing the player placed could be taken back. A dome in the wrong
place stayed there with its corridors, and the code that would free a record, unlink
its node and rewrite its ground did not exist ([§6.10](#610-events-and-hazards)). The
player's decisions:

- **Domes and structures, finished or still sites, but never the ship.** A dome's
  corridors go with it, as they came with it
  ([§9.3](#every-building-needs-a-neighbour-at-milestone-85)). A corridor alone cannot
  be taken down.
- **Half the materials come back**, as for a machine taken out at `FIT`
  ([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)): half the price of the
  building, of its corridors (6 Metal and 3 Bioplastic a tile) and of its machines.
  **A site gives back everything paid for it**: all of it was paid at placement and
  nothing has been built with it yet ([§6.9](#built-at-milestone-88)).
- **At once**, at `FIRE`, as `FIT` is. No constructor walks over to take it apart.
- **Whoever is inside leaves, and whatever work was there stops.** Demolition is not
  refused while the building is occupied.

**`M`, `D`, `FIRE`.** `MANAGE` has a sixth button, `D` (`DEMOLISH`, a box with a cross,
the 35th symbol of `tools/buttons.py`). Its line says `DEMOLISH` and `MATERIAL BACK`.
`FIRE`, or `D` again, takes down what is under the cursor; `ESC` does not. The button
is red where nothing can be taken down, and there `D` only gives the refusal's
sound:

- on the ship;
- on the landing pad, and on a dome whose room is Storage, while a ship is coming or
  standing (`EC_SHSTATE`): colonists come down at the pad, and the merchant's goods
  are carried to and from the stores ([§6.11](#carried-at-milestone-98));
- on open ground.

`dm_can` (`src/demolish.asm`) decides, from what `I` reads under the cursor
(`mt_cursor`, which `in_panel` in `src/info.asm` now shares). It asks when `M` opens
the line and again at `FIRE`, since a ship may have been called in between. Then one
call, `dm_do`, does everything:

1. **The price.** The building's row of `bld_items`, each machine's `fit_price` (a
   greenhouse's plants included) and every corridor tile, halved if the building was
   finished. Everything goes into the stocks through `ec_add_stock`, so a full store
   stops at 600, as with any income.
2. **The corridors.** Each record with the node at either end is freed. So is the
   second record of a bent one (`C_A` = 255): otherwise a straight corridor placed
   later in the record before it would take it for its own bend. An airlock at the
   other end is left without its corridor: `ST_JOINED` 0, and it counts again among
   the free airlocks (`EC_FREELK`), as one placed alone does.
3. **The jobs.** A job whose site is the node is deleted, and a Build lowers
   `EC_NBUILD`. A job that only starts or ends there is put back the way the job board
   puts back a dropped one ([§6.7](#supply-at-milestone-88)): `J_NODE` = `J_SITE`, so a
   Supply whose store went chooses another store when someone takes it. Whoever was
   doing either lets it go (`NO_TASK`). A `J_TRADE` is left alone, since no ship can be
   there.
4. **The people** standing in it go to the airlock or ship nearest the cursor
   (`lk_anchor`), with a full suit (3 minutes, [§6.6](#suits-at-milestone-90)) and no
   task. They are no longer operators, so leaving next time does not take an operator
   from someone else's machine. They are indoors if that airlock is finished, outside
   otherwise: someone who wanted air would look for the nearest airlock, find the one
   they stand on, and never arrive.
5. **The graph.** `lk_cut` takes the node's edges and marks the routing for a rebuild.
   One more thing was needed. Where the node was the last entry of a neighbour's list,
   the slot after that list still held it, and a colonist on the way to the node would
   reach a node with no edges and stay there. That slot now names the neighbour itself.
6. **The record.** Its state is `DS_EMPTY`, no ring slot is taken, and its id is free
   for the next building: "a demolished dome keeps its id with degree 0", as
   [§6.4](#64-routing) foresaw. The other bytes stay, since a colonist still leaving is
   drawn from the building's centre.
7. **What is counted from the buildings.** The room lists are rebuilt **at once**, not
   at the wheel's next slot 14, so nobody looks for a canteen in a dome that is gone.
   The flow balance is asked to measure power and the mines again (`ec_fdiv`).

**The occupancy is written again, not unwritten.** A corridor marks the half-width
tiles that were free when it was placed
([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)), and nothing remembers which;
a tile can also belong to another corridor or footprint. So `dm_world` clears bit 4
in a list of rectangles and writes it again from everything that remains: every
footprint (`al_node`, and a copy of the fill that placement uses), and every corridor
whose own rectangle meets one of them, with placement's own stamp (`cr_plan`,
`cr_stampx`). The rectangles are the node's footprint and, for each of its corridors,
centre to centre with a tile around: whatever got the bit from the node is inside
them, a bend included. A padded box around all of them, the first version, covered two
thirds of the view. The paths (bit 5) are not its business: since milestone 102 they go
first ([below](#paths-that-go-at-milestone-102)), and the foundation stays.

**The picture is the same rectangles, one per pass of the dirty list.** A full redraw
is 360–920 ms depending on what is in view ([§6.9](#69-construction)). The first
version did that, and took 217–374 ms in the test colony; drawing all the rectangles
at once took 136–272. Now each rectangle is two records of the dirty list
([§8.5](#85-the-dirty-list)). `DK_RSIZE` carries its size and is charged the whole
budget, so that it goes only as the first record of a pass. `DK_RECT` carries its corner
and is charged nothing, so that it always follows at once, and `vr_w` is never left
between two passes for something else to change. `DK_RECT` lifts the ghost if the
rectangle is under it, and draws the ground and whatever stands on the rectangle,
clipped to the view (`view_rect`'s two halves). Records still waiting for the
demolished dome are skipped by `dt_prep`, as for any dome that is not live, and a list
that overflows makes a full redraw, as it always did.

**What it costs**, measured from `FIRE` until the list is empty, in `colony.sna`:

| Demolished | The `FIRE` frame | The worst frame after it |
|---|---|---|
| a medium Factory beside the colony | 91 ms | 92–99 ms |
| dome 0, the colony's middle, two domes and the airlock beside it | 97 | **125** |
| dome 1 | 89 | 121 |
| dome 2, the pad, the airlock | 88–93 | 77–85 |

`tests/test_demolish.py`'s ceiling is 150 ms, under the 200 of a placement's worst
frame ([§6.9](#69-construction)). The `FIRE` frame is the demolition itself, 34–45 ms
in the colony (about 6 of them copying the code in), and the frame's own bar and HUD.
The demolition was 50–59 ms before its corridor scan stopped reading both ends of
every empty record. Nothing that runs
every frame changed, and a whole revolution of the wheel is the same as before
(`tests/test_sim.py`).

**The save did not change** (`SV_VER` is still 8). A demolished record is an empty one,
and nothing else is new.

**Memory**, about 1.2 KB, and only 32 bytes of it in bank 0:

- **bank 0, 32**: the button's row and the second red button of the `MANAGE` bar
  (`src/bar.asm` 21), the two kinds in `dirty_jmp` and `dirty_cost` (8), and
  `call ov_install` at the start (3);
- **bank 2's code area, 180**: `src/demolish.asm` 120 (`dm_can`, `dm_go`, `ov_run`,
  `ov_install`), `src/act.asm` 46 (`ac_demo`, and `AF_DEMO` beside `AF_FIT`), and
  `mt_cursor` 14 net;
- **the demolition itself, 901, in the routing matrix's unused columns**
  ([§4.2](#code-in-the-routing-matrixs-holes-at-milestone-101));
- **bank 7**: the symbol 17 and the two texts 23, paid by the font's last five
  characters, 40, which no text uses. The bar's five cells moved down to `&7B–&7F`
  (`HUD_CELL0` in `src/hud.asm`).

**The fill is a copy, not shared.** `dm_world` clears and sets its rectangles with the
same 24-byte loop that `bd_link` uses to lay a building's foundation. Shared, a
structure's placement paid a `call` and a `ret` for it, 6 µs, and
`tests/test_place.py`'s ceiling caught it (895 µs against 892). The copy lives in the
overlay, which had the room once `dm_do` took the footprint before paging bank 6 in
and started its totals from the building's own price.

Bank 2's code area had 3 bytes, and got 199 back first
([§4.2](#code-in-the-routing-matrixs-holes-at-milestone-101)): 22 are left. Bank 0 ends at
**`&3DD8`**, 40 bytes under the tests' floor.

**What the planted faults found.** `tests/test_demolish.py` plays the real game in
`colony.sna` with the player's keys, and holds every result against something the
game did not compute. The occupancy is compared with `tools/reach.py` and
`tools/route.py` (footprints, corridor tiles and half-width tiles, from the records
that remain), and the screen with a full redraw, before and after the cursor moves off.

- **The tables**: the holes hold `build/ovl.bin` byte for byte; the test colony's world
  is the model, and rewritten whole it does not change.
- **At once**: dome 0 leaves its room list inside `dm_do`, before the wheel's turn.
- **A medium Factory** with two machines installed: half of its 66 Metal and 32
  Bioplastic back; the dome, its corridor and the Factory count gone.
- **A bend**: a medium dome where the rule puts it beside the colony, joined to dome 0
  by a diagonal with a bend. Both records go, and half of its nine tiles is paid back.
- **A site** with its Supply jobs: everything paid comes back, the jobs go, and
  `EC_NBUILD` equals the Build jobs left on the board.
- **Dome 0, with two colonists inside**: both go to the airlock, indoors, with no task,
  not operators and a full suit, and are alive 30 s later. It was the last entry of two
  neighbours' lists.
- **The airlock**: half of its price and of its two tiles back. When dome 0 goes
  instead, the airlock is unjoined and there is one more free airlock.
- **Refusals**: the ship in `main.sna`, the pad with a ship coming, open ground. The
  button is red and nothing changes.
- **The cost**: the factory and dome 0, against the ceiling.

Sixteen faults were planted, and each was caught:

- no refund;
- everything back from a finished building;
- the corridors left;
- the world not rewritten;
- a corridor's rectangle without the tile around it;
- no corridor rectangles;
- the rooms left until the wheel;
- the jobs left;
- the people left;
- the edges left;
- the neighbour's list still naming the node;
- the airlock still joined;
- the ship demolished;
- no rectangle in the list;
- a rectangle drawn under the ghost;
- all the rectangles in one pass (211 ms).

The other tests that know the bar learned the button from their own prose:
`tests/barread.py` and `tests/test_bar.py` (the help screen's 35 entries),
`tests/test_act.py` (DEMOLISH red by the rule above on every tile it visits, `FIRE` and
`SPACE` on the line each taking down a dome of its scene, and an eighth negative, the
button always green; its negative for `FIT` now reads `bww_man`, which reds two
buttons from one byte), and `tests/test_pack.py` (the font up to `z`).
`tests/test_info.py` finds `mt_cursor` where `in_panel` read the cursor itself, and
`tests/test_figure.py` reads only the number it needs from `dirty_cost`.

#### Paths that go, at milestone 102

Until this milestone a demolished structure left its path behind: foundation with the
path bit, refusing a building or a corridor for the rest of the game, because which L it
had taken was kept nowhere ([§15](#15-open-risks)). The player chose this step: **when a
structure is demolished, its path goes, and so does every path that ended at it.** Three
things were decided here, not asked, each the nearer one to what the game already does:

- **The tiles stay foundation**, without the path bit: levelled ground, as a demolished
  footprint is ([above](#demolition-at-milestone-101)), and it builds again. Nothing on
  the screen changes, since the bit is not drawn, so nothing is drawn again.
- **What hung from it hangs from its parent.** A structure whose own link — path or
  ground link — ended at the demolished one gets a ground link, drawn as every ground
  link is ([milestone 94](#every-building-needs-a-neighbour-at-milestone-85)), to
  wherever the demolished one hung from. At milestone 101 it was left without an edge:
  a site nobody could reach to finish, a mine nobody could reach to dig, an airlock that
  was the colony's way to the ship.
- **A dome still being built** whose ground link went is not linked again
  ([§15](#15-open-risks)).

**Not the nearest airlock**, which is what `lk_ground` gives anything placed without a
path. The nearest is often one that hangs from the orphan itself — two airlocks in a row
from the demolished one — and then the two link to each other, with a doubled edge, an
island with no way to the ship. In `tests/test_unlink.py`'s scene the nearest airlock of
A2, once A1 is gone, is A3, which hangs from A2. Keeping every orphan and everything under
it out of the search means walking the whole tree, about 40 bytes the overlay did not
have. The parent is higher up the same tree: no cycle, no doubled edge, and the same way
to the ship they had. Where the demolished structure hung from nothing (the test colony's
airlock, a save from before this milestone), or its parent has eight edges already, what
hung from it stays without a link, as at milestone 101.

**Where it is kept.** One byte for each structure, `LK_OWN` (`src/link.asm`): entries
96–127 of `node_deg` ([§6.2](#62-the-node-graph)). The graph has 96 nodes and that table 128,
`game_new` clears all 128, and the save holds them with the graph
([§11](#11-save-and-load)). The byte is the node at the other end (64–95), bit 5
(`LKO_GROUND`) for a ground link, and bit 7 for a path that goes y first (`al_po`); 0 is
"nothing kept": the test colony's own links, which `src/colony.asm` makes by hand, and
every link of an older save. Node 64 + *s* with bit 5 set is 96 + *s*, so the byte is one
`set 5,l` from the node. `alc_pth` keeps it with the path (`lk_keepp`, in front of
`cr_link_bc`), and `lk_ground` with a structure's ground link. A dome writes nothing: its
ground link goes when it is finished (`lk_done`).

**Demolition reads it twice** (`src/dm_ovl.asm`):

1. **`dm_paths`**, before the graph and the record, while the records still give
   footprints: the node's own path, and every path whose byte names the node, walk
   their L again with placement's own walk (`al_walk`, the two footprints from
   `al_node`, the shape from the byte) and clear bit 5 on its tiles. No other path has
   to be written again: a path takes only tiles that build (`bd_ok`), and a path tile
   does not, so two paths never share one. The node's own parent is remembered
   (`dm_par`); every structure that hung from the node is marked `LKO_LOST`.
2. **`dm_relink`**, after the graph, the record and `dm_world`, so the parent is not the
   node and the ground link sees the occupancy as it stays: each lost structure gets
   `lk_keep` to the parent, which keeps the byte and makes the edge, and `lk_draw`. Its
   legs do not go to the screen at once. `al_vr`'s last jump (`alv_jp`, in `b1code`)
   points for the while at `dmv_leg`, which puts each leg on the dirty list as a
   `DK_RSIZE` and a `DK_RECT`, after the demolition's own rectangles, one per pass
   ([above](#demolition-at-milestone-101)).

**The first version wrote that jump with bank 6 in the window**, where `rooms_rebuild`
left it. The jump stayed `view_rect`, two bytes of bank 6 changed, and every leg was drawn
in the `FIRE` frame: 196 ms where the legs on the list give 139. `dm_relink` pages bank 1
in first. The frame's time gave it away; nothing would have caught the two bytes.

**What it costs**, the worst frame from `FIRE` until the dirty list is empty
(`tests/test_unlink.py`, ceiling 150 ms as for any demolition):

| Demolished | Hanging from it | Worst frame |
|---|---|---|
| a Solar panel with its path, in the test colony | — | 109 ms |
| an airlock, in `main.sna` | a Solar panel and an airlock, linked to the ship | 96.5 |
| that Solar panel | another one, linked to the ship | 89 |

With nothing linked again the two passes over the 32 bytes cost about 2 ms: the test
colony's airlock with two airlocks being built beside it, 131 ms against 129 at milestone
101. A link of 30 tiles cost about 8 ms more. Placing a structure with a path costs about
14 µs more, outside `bd_commit`, whose ceilings in `tests/test_place.py` did not move.
Nothing that runs every frame changed.

**Memory.** Bank 2's code area, 21: `lk_keep`, `lk_keepp`, and 9 in `lk_ground`; 1 is
left. The overlay, 185: `dm_paths` 107, `dm_relink` 68, `dmv_leg` 20, less its own copy of
`mt_rec` (13), which it no longer needs. That did not fit under the test colony, and the
overlay now comes in somewhere else ([§4.2](#and-milestone-102-moved-where-it-comes-in)).
The bytes it keeps were unused. **The save did not change** (`SV_VER` 8).

**What the planted faults found.** `tests/test_unlink.py` plays the real game with the
player's keys, in `colony.sna` and in `main.sna` with the ship, and holds the world after
each demolition to a model built in Python: the world before, without bit 5 on the paths
that go, with bit 4 from the records that stay (`tests/test_demolish.py`), and with the new
ground links one by one in node order (`tools/reach.py`). And bit 5 across the whole world
is the union of the paths the `LK_OWN` bytes describe.

- **Kept**: two Solar panels, one with a path x first to the colony's airlock and one
  with a path y first, an airlock with a ground link, and a dome that writes nothing.
- **Its own**: the y-first Solar panel goes. Its six tiles are foundation without the
  bit and with their decor; the other path stays; a Solar panel then goes in on top of
  the old path.
- **The anchor**: in `main.sna`, the airlock A1 (hanging from the ship) goes. The path of
  the Solar panel S1 goes with it, S2's path to S1 stays, S1 and the airlock A2 hang from
  the ship, A3 stays on A2, and all of them reach the ship (`DIST`). Then S1 goes, and S2
  hangs from the ship.
- **No parent**: two airlocks hanging from the test colony's own airlock, which hangs
  from nothing. They stay without a link, and no edge is made.

Nine faults were planted, and each was caught: the path left; always x first; nothing
kept; a ground link kept as a path; only the node's own path cleared; no linking again;
the parent forgotten; a link made with no parent; the legs not drawn.

**The screen is checked at once, and if it differs, two seconds later.** A colonist at an
airlock's door is drawn differently from a full redraw for a few frames, by 9 bytes in one
tile, at the same moment and the same place at milestone 101 ([§15](#15-open-risks)). A
leg that was not drawn does not mend itself, and fails both: with `dmv_leg` returning at
once, 592 bytes in 11 tiles. The first look puts the screen back as the game drew it,
since the full redraw it compares with would mend the second.

**Milestone 103 found that putting the screen back was not enough.** The full redraw also
rewrites the renderer's own records: where each figure was drawn, and the ghost's log. With
only the screen put back, a look that fell on two colonists overlapping left the records
saying where the full redraw had drawn them, and a later erase went there: pixels the game
never left, in one tile, which the second look then found, in one of the suite's copies
and not in the others, since it needs the look to fall on the overlap.
The look now keeps all eight banks at the top of the main loop and puts them all back, and
it looks up to five times, two seconds apart: two colonists leaving by the same edge
overlap in a different order for a few frames ([§15](#15-open-risks)).

#### A cursor step near the colony, at milestone 107

[§15](#15-open-risks) had carried "a cursor step near buildings costs 7–15 ms more" since
milestone 85. This milestone measured the whole step in the game rather than
`ui_validate` alone: the main-loop iteration that moves the cursor, with the PC sampled
every 20 µs and the vsync waits (`ml_low`, `ml_high`) left out. The test's two scenes
were a Solar panel and a dome S in `PLACE` beside the colony of [§10.1](#101-start-state).

**Where the step went.**
- **Dome S, 43.8 ms of work.** About 17 ms was the panel. The corridors' cost changes on
  almost every step, so the panel's signature changes with it ([§9.2](#92-hud)), and
  all eighty cells of rows 3–4 were redrawn to change two digits. Another 13 ms was the
  ghost.
- **Solar, 23.0 ms of work.** About 9 ms was the ghost and 7.5 ms the neighbour check of
  [above](#every-building-needs-a-neighbour-at-milestone-85).

**Rows 3–4 got their own cell cache** (`hud_s34`, 80 bytes in bank 0).
- `hud_go` points `hud_sp` into it, as it does into `G_hud_shadow` for rows 0–2, and a
  cell whose code has not changed is stepped over.
- Rows 0–2 stay at `row × 40 + column` in their page-aligned cache. In rows 3–4,
  `hud_to` subtracts the row's start in the cache (`hud_tb`) to get the column back.
- `hud_inval` clears both caches.
- The help screen still draws with `hud_sp = 0` and no cache, then ends with
  `hud_inval`.
- The signature stays: it saves generating the text at all.

**One pointer, not two.** The screen address of a cell is `hud_sp` plus a constant for
its row (`hud_dd`, set by `hud_go`). A cell that is stepped over now only increments
`hud_sp`; until now `hud_next` carried a second 16-bit pointer through memory for every
cell. An ordinary HUD tick went from 11,981 µs to **9,984** (0.60 → 0.50 frames,
`tests/test_hud.py`).

**The ghost's columns step their own lines.**
- The two sides of a building's frame are 1-byte columns, 88–120 lines in all, written
  by `ghr_put` and taken back by `gh_swap` on every step.
- Each line was a `call scr_nextline` and a `dec ixl`. Now `d += 8` is in the loop, with
  `call c,scr_nlw` only when a character row ends, and `djnz` counts.
- About 21 µs a line where it was 26. The rows of the frame get the same inline step.
- `gh_rect` no longer clips a rectangle that is wholly inside the clip (`ghr_in`): two
  `ob_clip`s, about 110 µs a side, four sides a step.

**The L's walk carries its two footprints in its instructions.**
- `al_emit` tested every tile against the new footprint and the other end's with two
  calls to `al_in`: about 54 µs for a tile outside both, which is nearly all of them.
- Now `al_rsync` writes the two rectangles into `al_emit`'s `sub`/`cp` immediates at the
  start of each L (`al_w4`, and `al_s4` as well). Such a tile is about 22 µs.
- `al_s4`'s two callers do not depend on the sync today: `alc_pth` comes straight after
  an `al_w4` with the same footprints, and `lk_draw`'s `al_cbr` touches only free
  ground, which a footprint never is. So the sync there is defence, 3 bytes, and no
  planted fault shows it.
- The validation's callback `al_cbk` has `tile_addr` and `bd_ok` inline.

**What a step costs**, work per step without the vsync waits, the mean of six steps
(`tests/test_reach.py`, STEP):

| | Milestone 106 | Milestone 107 |
|---|---|---|
| Dome S beside the colony | 43,798 µs | **31,666** |
| Solar beside the colony | 22,992 | **19,693** |
| `ui_validate`, Solar with a path | 7,500 | **6,045** |

With the joystick held for a second, the cursor makes:
- dome S: 15 steps left and 21 right (12 and 19 before);
- Solar: 19 left and 23 right (17 and 21 before).

Up and down are unchanged. Those steps leave the view and the camera scrolls, which
is a cost of its own ([§15](#15-open-risks)). A single iteration's time still depends on
where its work ends against the vsync. The Solar's 19.7 ms of work is one frame's worth,
so its step iteration is 27 ms or 37 ms depending on the step.

**Two worst iterations went up, from phase rather than work.** The iterations before a
test presses FIRE are shorter now, so the counters that advance once per iteration are
somewhere else when FIRE comes. Those are the HUD clock, which fires every 16 iterations,
and the wheel's slots.
- `tests/test_link.py`, M → M diagonal: 74 → 96 ms. The HUD clock now falls in the FIRE
  iteration, where before it fell five iterations later. The work after FIRE, without the
  vsync waits, went down from 231 to 204 ms, and the HUD tick within it from 28.4 to 17.0.
- `tests/test_reveal.py`, placing the dome L: 104 → 112 ms. The FIRE iteration has 3.5 ms
  more vsync wait, and a job-board slot (`jb_arrive`, 1.6 ms) that now falls in it. Its
  drawing is the same within 0.5 ms, and the whole placement's work went 762 → 732 ms.

**Memory.**
- Bank 0 took 192 bytes: the cache's 80, the HUD's pointer and column (`hud_tb`), and
  the ghost's loops and clip test. It has 287 left, 95 of them under the tests' floor.
- Bank 2's code area took 75 bytes for `al_rsync`, the inline tests and `al_cbk`. It has
  139 left.

**What checks it.**
- **SHADOW** (`tests/test_reach.py`). In the game, a dome S and then a Solar in `PLACE`
  beside the colony. The sequence covers:
  - cursor steps in all four directions, until the camera scrolls;
  - a camera jump;
  - a change of item;
  - `ESC`.

  After each one, rows 0–4 on screen equal their drawing from nothing. The test makes
  the bands black, the caches empty and the signature invalid itself, not through the
  `hud_inval` under test.
- **STEP**, with ceilings of 33,000 µs and 20,800 µs. `ui_validate`'s ceiling for the
  Solar with a path is now 6,400.
- Five negatives in `tests/test_reach.py`:
  - `hud_inval` not clearing `hud_s34`;
  - `hud_to` without `hud_tb`;
  - `hud_char` not writing the cache;
  - `al_emit` without the new footprint;
  - `al_w4` without `al_rsync`.
- Four negatives in `tests/test_ghost.py`, whose model already changes the clip:
  - the clip's end not cutting;
  - its start not cutting;
  - a column without `scr_nlw`;
  - `gs_col` without its counter.

  The first draft of `ghr_in` compared with the view instead of the clip, and that model
  caught it.

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
`scene.dome_dirs` and the `DK_CONN` that `cr_redraw` pushes for B. Since milestone 96
the doors are joints and the scan is gone; `jt_mark` reads the continuation the
corridors' measure already holds
([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)).

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

#### Smaller and faster, at milestone 72

`route.asm` went from 1,672 bytes to **1,181**, and bank 2's code area from 117 bytes
free to **608**. Every routine the check timed got faster, in every case it tried.

- **The two ends are two four-byte records, and the other side is a swap.** `cr_a` and
  `cr_b` are each followed by the dome's `cx`, `cy` and size, and `cr_from` *is*
  `cr_a`. When the route does not leave from A, the two records trade places and
  `cr_side` runs again. Until milestone 71 the positions were read into a third pair
  and copied to whichever side was being tried.
- **Both bends are one formula** (`crs_bend`), with m = min(S, T):
  - the diagonal runs m − `ka`, plus one when the turn is to horizontal;
  - the axial run is max(S, T) − m − `rb` + 1;
  - the vertical bend enters with S and T swapped.

  The pure diagonal and the pure axial run share their tail (`crs_one`) the same way.
- **A diagonal is walked as a straight line.** A diagonal piece's front tile is the
  next piece's back tile, so its n + 1 tiles are each (`ux`, `uy`) from the last, and
  the walk sends them through `cr_line` like an axial run. Until milestone 71 every
  step worked out the piece's two tiles with two multiplications. Most of the walk's
  and the check's gain is this.
- **A direction is one table lookup**, `cr_dtab[3·uy + ux + 4]`.
- **The world's edge is one sign test.** (x + 64) | (y + 64) has bit 7 set exactly
  when either coordinate is outside −64..63, so the check and the stamp each spend one
  `jp m` / `ret m` on it.
- **The check and the stamp share their paging** (`crw_b4`): bank 4 in, the walk with
  their callback, bank 1 back.
- **The commit writes both records through one routine** (`crm_put`), backwards from
  the state byte, and the link adds both edges through one `cr_edge` with `B` and `C`
  swapped.
- **The cost is one multiply per material**, Metal last, so `cr_afford` tests Metal
  first, as it did before. A first version tested Bioplastic first and was slower than
  milestone 71 in eight cases of the check.
- **Ten variables are gone**: `cr_pax`, `cr_pbx`, `cr_lx`, `cr_ly`, `cr_j`, `crw_dx`,
  `crw_dy`, `cr_ntile`, `cr_radt` and `cr_kt`.

The check was a script kept out of the repository, on `build/main.sna`. It put two
domes in slots 50 and 51 of the table, 3,000 times: axial, diagonal and nearly
diagonal, odd distances, empty slots, every size at either end. For each it called:

- `cr_plan`;
- `cr_walk`, with a callback that logs every tile;
- `cr_check`, in the game's world and in a random one;
- `cr_cost`, and `cr_afford` three times around the cost;
- on every eighth, `cr_commit` and `cr_redraw`, comparing all eight banks after.

It also called `cr_edge` 400 times. 1,652 of the pairs had a route, and all of it was
identical. **Time**, in total over the same calls:

| | Milestone 71 | Milestone 72 | Faster in |
|---|---|---|---|
| `cr_plan` | 2,043,250 µs | 1,635,024 µs (−20 %) | 3,000 of 3,000 |
| `cr_walk` | 3,704,482 | 2,281,309 (−38 %) | 1,652 of 1,652 |
| `cr_check` | 8,657,351 | 6,078,380 (−30 %) | 1,652 of 1,652 |
| `cr_cost` | 492,980 | 478,112 (−3 %) | 1,652 of 1,652 |
| `cr_afford` | 1,678,287 | 1,605,757 (−4 %) | 1,652 of 1,652 |
| `cr_commit` | 910,616 | 644,563 (−29 %) | 218 of 218 |
| `cr_redraw` | 2,869,653 | 2,750,884 (−4 %) | 212 of 212 |

**A trap the rewrite hit: rasm's `/` rounds.** It evaluates `/` in floating point and
rounds the result, so `cr_dtab / 256` is the high byte only while `cr_dtab`'s low byte
is below `&80`. In `main.sna` it was, and the script passed. In the uitest build,
where `test_route.py` runs, `cr_dtab` was `&23F5`, the "high byte" came out `&24`, and
every direction was read from the wrong page. High bytes are now `>> 8` here. Other
`/ 256`s in `src/` are right today only because of where their labels happen to land;
they are not touched by this milestone.

**A tile can leave the world, in y only.** A bend to horizontal whose destination sits
on row −64 puts the diagonal's front tile on row −65. In a sweep of 2,709,202 routes
of `tools/route.py`, with one dome within four half tiles of an edge, 289,549 reach row
−65, and none leaves the world in x. The check counts such a tile as bad, and the stamp
skips it. Neither the script nor any existing test had ever produced one.

**Domes more than 127 half tiles apart on one axis are routed the wrong way, and were
before this milestone.** `cr_side` subtracts the centres in 8 bits, so a difference past
±127 wraps, and the route is planned towards the other side. Old and new agree on 600
such pairs, so this is not the rewrite's. In 37 of the 427 that have a route, the wrong
corridor stays inside the world and passes the check. `tools/route.py` does not wrap,
and the test below keeps its pairs within 127 for that reason. See [§15](#15-open-risks).
Milestone 81 refuses such pairs ([below](#no-corridor-past-63-tiles-at-milestone-81)).

**What the planted faults found.** Twenty-eight faults were run against the script and
three tests: `test_route.py`, `test_link.py` and `test_game.py`.

- **The script caught twenty-five.** Four of those only by stopping: the fault made a
  route exist on one side and not on the other, and the comparison stopped at the first
  such case. It missed three:
  - a dome under construction read as an empty slot — the script only ever put empty
    or finished domes in the table;
  - a bent route given the table's last slot, writing its second record over
    `G_worldinfo` — the script never left exactly the last slot free;
  - the check blind to x outside the world, which no route within 127 half tiles
    reaches.
- **The three tests together caught twenty-one.** `test_route.py` caught sixteen,
  `test_link.py` eighteen and `test_game.py` one. The seven they let through:
  - odd distances in x routed as if they were even;
  - an axial run out of a north or west door starting on the wrong side of the dome's
    centre;
  - the stamp marking corridor tiles as dome rather than structure;
  - `cr_afford` not looking at Bioplastic at all;
  - the last-slot pair;
  - a diagonal row whose three columns start just left of the view, never pushed;
  - the x check.
- **`tests/test_corridor.py` catches twenty-seven**, each on a wrong answer. It also
  fails on the twenty-eighth, the x check, but only because its negatives can no longer
  find the bytes they patch. No route within 127 half tiles leaves the world in x, so no
  behaviour shows that fault.

`tests/test_corridor.py` calls `route.asm`'s entry points directly in `main.sna` —
`cr_pay`, `cr_link` and `cr_edge` through the commit — with two domes written straight
into slots 50 and 51 of the table:

- **1,500 pairs, against the references.** Axial, diagonal and nearly diagonal, odd
  distances, empty and unfinished domes, every size at either end; 40 of them chosen
  so that the route reaches row −65.
  - `cr_plan` against `tools/route.py`: the runs, and which dome it starts from.
  - `cr_walk`'s tiles, in order, against `test_route.py`'s `tiles_of`.
  - `cr_check` and `cr_stamp` against their rules in a random world. The stamp must
    change nothing else in any bank.
  - `cr_cost` and `cr_afford` against the arithmetic.
- **400 commits on random corridor tables:** full, only the last slot free, the last
  two, one gap, two adjacent gaps, sparse, empty. Both the table and the 32 bytes after
  it are compared against the rule: the first free slot, two adjacent ones for a bent
  route, never past the last. Payment and the graph's edges happen only when a slot is
  found, and an edge is added only to a node with room for it.
- **500 redraws**, with stubs on `dirty_push` and `view_add`, at cameras around the
  route. Expected: the two doors (since milestone 96 the two joints); one `DK_CROW` for
  each diagonal row in view; the box of the axial part, a column or a row wider where
  a centred corridor straddles a tile boundary (since 96); and `Z` only when no row is
  pending.
- **Time.** Six geometries: axial, diagonal, diagonal then horizontal, diagonal then
  vertical, from the other side, and none. For each, `cr_plan`, `cr_walk` with an empty
  callback, `cr_check`, `cr_afford`, and `cr_commit` with only the last two slots free.
  None may be slower than this milestone measured. With milestone 71's `route.asm`
  every one fails.
- **Seven negatives:**
  - a radius of size + 3;
  - the direction table one byte back;
  - the check's footprint one tile smaller;
  - the check blind to y outside the world;
  - the stamp without the world's edge;
  - a pair in the last slot;
  - a diagonal row visible only from column −1.

**Two traps the test hit, both now in its comments:**

- **The bytes after the corridor table decide whether the last-slot fault shows.** A
  97th record would be `G_worldinfo` and the first byte of `G_dome_fig`, the figure
  cache, and that byte is its state: the fault only writes when it is 0. With random
  bytes there, the negative passed. The test now zeroes it in half the cases.
- **A climbing bend whose horizontal run is one tile long has nothing of its own to
  redraw.** Its one tile is the diagonal's last back tile, so the box's minimum stays at
  +127 and its maximum at −128. `view_add` gets (127, 127), 2 × 2: outside the world, so
  nothing is drawn, and the diagonal's row has already redrawn that tile. Milestone 71
  did the same. The rule in the test says so rather than pretend otherwise.

#### No corridor past 63 tiles, at milestone 81

Two domes whose centres are **64 tiles or more apart on either axis** get no corridor.
In `LINK` row 4 says `TOO FAR` instead of `NO ROUTE FROM THERE`, the ghost is red
(`ui_bad` = 2, where a shape that does not fit is 1), and `FIRE` builds nothing. The
player links them through a dome in between. Corridors up to 63 tiles are routed as
before. A longer one would have been a 9-bit difference, a few bytes. But it would also
have been corridor lengths that the object index, the dirty rectangles, the ghost and
the save had never seen, so the game refuses them instead.

- **Why it had to be one or the other.** `cr_side` subtracted the two centres — half
  tiles, −128…127 — in 8 bits. Past ±127 the difference wrapped, and the route was
  planned towards the other side of the world. Most such routes leave the world, and
  the check refused them as `BLOCKED`, 55 bad tiles for the test's pair. Some stayed
  inside, passed, and joined the two domes in the graph through a corridor that does
  not reach the second one ([above](#smaller-and-faster-at-milestone-72)).
- **The rule is symmetric.** An overflow of the subtraction (`jp pe`) catches every
  difference from 128 half tiles up, except −128: that one fits in 8 bits, so on its own
  the overflow check would let a pair exactly 64 tiles apart through from one dome
  and not the other. `S` and `T` are at most 64 after that, so one `bit 6` of `S | T`
  catches the 64.
- **It is answered once.** Distance and parity do not depend on which dome is the
  start. When either fails, `cr_side` drops its return address and leaves `cr_plan`
  at once, instead of swapping the ends and asking the same question again.
  `cr_far` is written only when there is no route, which is the only time
  `ln_plan` reads it. So clearing it costs the routes that exist nothing.
- **It costs nothing in time.** `cr_sgn` and `crs_rk` are written out in `cr_side`
  instead of being called twice each. That paid for the three checks and more. `cr_plan`
  went from 475 µs to **447** for an axial route, 486 → **458** diagonal, 551 → **523**
  for either bend, 865 → **808** from the other side, and 376 → **275** with no route.

The cost is 45 bytes in bank 2 (`route.asm` 1,181 → 1,226), 13 in bank 0 (`ln_plan` and
`uip_ln`) and 21 in the text block for `TOO FAR`. `tools/route.py` has the rule
(`too_far`), so `tests/test_corridor.py` now draws pairs across the whole range, and
its ceiling for `cr_plan` is now these numbers rather than milestone 72's. Pairs
at 126, 128 and 130 half tiles and up to 254, from both ends — 166 of the 1,500 — must
give no route, with `cr_far` = 1. There are two more negatives: the x axis without its
overflow check, and `bit 7` for `bit 6`.

`tests/test_far.py` plays it in the game, paused. Domes are written into the table,
far from the colony, and the player's own keys open `LINK`:

- 64 tiles on x, with each dome picked first: `TOO FAR`, `ui_bad` = 2, and `FIRE`
  leaves the corridor table and the state as they were;
- 65 tiles on y, the same;
- 63 tiles, both ways: a route, and neither message;
- a near-diagonal pair that `tools/route.py` does not route: `NO ROUTE FROM THERE`,
  `ui_bad` = 1.

There are three negatives:

- row 4 saying `NO ROUTE` for far too;
- `ln_plan` that does not tell the two apart;
- the milestone-80 router, without the three checks: `A → B` then says `BLOCKED`.

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
| effect header | 1 | priority × 16 + channel × 4 |
| tone step | 4 | volume, period lo, period hi, frames |
| noise step | 3 | `&80` + volume, noise period, frames |
| end | 1 | a zero volume |

A volume with bit 7 set makes the step *noise*: the next byte goes to R6 and the mixer
opens noise instead of tone on that channel. The volume goes to the chip as it is, bit
7 and all: R8–R10 hold five bits, and bit 7 is not one of them. Bit 4 is — it hands
the channel to the envelope — so a volume stops at 15, and the `TONE` and `NOISE`
macros that write the steps assert it. A tone at volume 0 is the end; a rest would be
a noise step at volume 0. Tone period is `62500 / Hz` — the AY's 1 MHz clock divided
by 16 — so 284 is A3 at 220 Hz and 120 is C5. `sn_tab` gives each effect as its
distance, in one byte, from its own entry in the table.

A channel's state is four bytes: the frames left in its step (0 only when it is
silent), the address of its next step, and its effect's header byte. On one channel
the header bytes compare as their priorities do, so `snd_play` compares those.

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

**Cost: 85 µs a frame in silence, 136 µs while something plays** (100 and 195 until
milestone 75) — under one percent of a frame, against the "service audio" line in [§7](#7-the-batch-scheduler)'s per-frame
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
the effects cost 338 bytes in bank 2 (540 until milestone 75) and the loading music
below lives in the generator.

#### Smaller and faster, at milestone 75

`sound.asm` went from 540 bytes to **338**, and bank 2's code area from 1,164 bytes
free to **1,366**. Every call got faster, in every case the check tried, and
`build/sounds.wav` came out the same to the byte.

| bytes | Milestone 74 | Milestone 75 |
|---|---|---|
| `snd_init` and `snd_off` | 52 | 23 |
| `snd_play` | 45 | 34 |
| `snd_ping` | 10 | 8 |
| `snd_tick`, with `snt_one` and `sn_mixset` | 216 | 97 |
| `snd_reg` | 36 | 34 |
| variables | 24 | 13 |
| the effects and `sn_tab` | 157 | 129 |

- **The data is 28 bytes smaller.** A noise step has no high byte, channel and
  priority are one byte, and `sn_tab` is one byte an effect instead of an address.
  The steps are written by two macros, `TONE` and `NOISE`, that assert their ranges.
- **A step goes to the chip straight from the effect.** `snd_reg` takes the register
  in `A` and the value at `(HL)`, moves `HL` on, and keeps `A`, `DE` and the flags:
  there is no arithmetic in it. So a step is three or four calls with only the
  register number between them, and the period's high register is `inc a` from the
  low one. The carry that says "noise" is set before the first call and is still there
  after the last, where `sbc a,a` turns it into the mixer's bits. Until milestone 74
  every value went through a variable, and `BC` was saved around every call.
- **The mixer is one formula**, `((A ^ m) & E) ^ m`. `E` is the channel's two bits (9,
  18 or 36), and `A` says which of them are closed after the step: `&38` after a tone,
  `7` after noise, `&FF` at the end. It was 51 bytes, with two tables and a variable.
- **The wait is the frames left in the step, and 0 means silent.** One byte answers
  both "does this channel play" and "is its step over"; the pointer's two bytes and the
  wait were two tests. `snd_play` sets it to 1, so the next tick loads the first step,
  as before.
- **A channel is two registers**: `D` its volume register, `E` its mixer bits, and
  `E & 6` its period register. Five variables and two tables are gone: `sn1_lo`,
  `sn1_hi`, `sn1_vol`, `sn1_r`, `sn1_nf`, `sn_tb` and `sn_nb`.
- **`snd_init` is `snd_off`.** The PPI goes to output in the first `snd_reg`, as on
  every write. `snd_init`'s own `out` and its own clearing loop did the same twice.
- **`snd_play` keeps `BC`**, so `snd_ping` saves two registers, not three. And it **no
  longer checks `A` against `SFX_N`**: every caller passes a constant.
- **A trap: an index within a page.** The first version found the channel's record by
  adding to the low byte of `sn_st`'s address, with an `assert` that the three records
  sit in one page. In `main.sna` they do. In the build shared by `test_object.py`,
  `test_scroll.py`, `test_index.py`, `test_hud.py`, `test_dirty.py` and
  `test_slot.py`, which places `sound.asm` elsewhere, they do not, and the assert
  stopped the assembly. The record is now found with a 16-bit add — one byte and 8 µs
  more — so the player works wherever it lands.

The check was a script kept out of the repository, on `build/main.sna`. It ran 30
sequences of 121 calls, each from `snd_init`: `snd_tick`, `snd_play` and `snd_ping`
of a random effect, `snd_off` and `snd_init`, in random order. After every call it
compared:

- the AY's registers 0–13;
- the three channels by meaning — effect, step, frames left, priority — since the
  record's layout changed;
- the mixer's shadow;
- every other byte that changed, in all eight banks;
- `BC`, `DE` and `HL` across `snd_ping`.

All 3,630 calls were identical. **Time**, the average per call, with the probe's own
44 µs:

| | Milestone 74 | Milestone 75 | Faster in |
|---|---|---|---|
| `snd_tick` | 432.3 µs | 296.6 (−31 %) | 2,201 of 2,201 |
| `snd_play` | 118.0 | 98.4 (−17 %) | 1,062 of 1,062 |
| `snd_ping` | 146.5 | 120.1 (−18 %) | 210 of 210 |
| `snd_off` | 445.0 | 416.0 (−7 %) | 69 of 69 |
| `snd_init` | 553.0 | 416.0 (−25 %) | 88 of 88 |

In `tests/test_sound.py`'s own measure the player costs **85 µs a frame in silence
and 136 µs while an effect plays**, where it cost 100 and 195.

**What the planted faults found.** Thirty-four faults were run against the script and
four tests: `test_sound.py`, `test_fit.py`, `test_meteor.py` and `test_loop.py`.

- **The script caught all thirty-four.** Four of them stopped it on its own
  invariant — a channel's record holding another channel's header — before it
  compared anything.
- **The four tests together caught twenty-seven.** `test_sound.py` caught
  twenty-six, `test_fit.py` ten, `test_meteor.py` two and `test_loop.py` none. The
  seven they let through:
  - `snd_off` clearing one byte short, or leaving R10 alone;
  - `snd_ping` losing `DE`;
  - the pointer's high byte not written back, which only shows when a step crosses a
    page;
  - the ship at priority 5;
  - `snd_play` with `ret z` for `ret c`, and `snd_play` not storing the priority.
    Both let the ship cut the alarm.
- **`test_sound.py` missed those last two because it looked at the wrong
  registers.** Its "the alarm is not cut by the ship" compared R0 and R1 only, and the
  ship is noise: it never writes them. It now compares R0–R10, and catches both.
- **`tests/test_sfx.py` catches all thirty-four.**

`tests/test_sfx.py` calls the player inside `main.sna`: twelve sequences of 110 calls
in random order, a tick where all three channels load a step (noise, tone, tone), and
one where all three end. After every call it compares against a model written from
this section and from the header of `sound.asm`, not from the Z80:

- the AY's registers 0–13, masked to the bits the chip keeps;
- each channel's four bytes;
- the mixer's shadow, equal to R7 and with bits 6–7 clear;
- every other byte in all eight banks, apart from the stack;
- `BC`, `DE` and `HL` across `snd_ping`, and `BC` across `snd_play`.

It also reads the nine effects back through the format and checks them against the
table above and against their steps as they were judged by ear. It holds each
routine's worst case to no slower than this milestone measured; milestone 74's file
fails every one. Its five negatives are:

- the mixer merged with `D` instead of `E`;
- the PSG's write strobe left out;
- the first step a frame late;
- a `snd_ping` that loses `DE`;
- one period of the alarm changed.

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

**Since milestone 87 the game starts with nothing built.** The four colonists stand
outside beside the **ship** at `(0, 0)` — structure 0, not a building
([§6.2](#inside-and-outside--milestone-87)) — with its cargo: **60 Water, 40 Food,
60 Ore, 189 Metal, 107 Bioplastic, 4 Spares**, and a population cap of 4, since there
is no Control dome yet. The first thing the player builds is the first dome, from
outside, and the second is the airlock that lets anyone into it. The rest of this
section is the colony the game started with until milestone 86, which is still how
most tests start ([below](#beside-the-ship-at-milestone-87)).

Until then: at `(0,0)`, on guaranteed flat foundation (ground since milestone 94): a landing pad, one small **Oxygen** dome with
one `mach_oxygen`, one small **Quarters**, one small **Storage**, and the corridors
joining them. Since milestone 86, also an **airlock** north of the Oxygen dome, at
`(0, −10)` in half tiles, with its own short corridor
([§9.3](#airlocks-are-the-doors-at-milestone-86)): structures join airlocks and other
structures now, never domes, and without one the first pump or mine would have had
nothing to join but the pad. Four colonists: two workers, one engineer, one biologist. Starting stock:
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

#### Smaller, at milestone 74

`src/newgame.asm` went from 670 bytes to **394**, and bank 2's code area from 888
bytes free to **1,164**. A new game got 1.7 ms faster. That is the same in every case,
and it is all `game_new`'s own part: the rest of the 480 ms is `ui_init`'s first full
redraw.

- **One flow.** `ng_wipe`, `ng_colony`, `ng_people` and `ng_stock` were four routines
  with one caller each, and `ng_stamp`, `ng_ff` and `ng_full` were called from inside
  them. `game_new` is now one body, in the same order.
- **Bank 6's five tables are one block.** The agents, the node occupancy, the domes,
  the structures and the corridors sit end to end from `&6C00` to `&7DE0`. One `ldir`
  clears them where five did, and four `assert`s hold the layout to that.
- **The three agent columns that start at 255 are one loop.** They are the +128
  halves of three consecutive pages — the ring slot, the edge and the task — so the
  fill moves on with `set 7,l` after each one.
- **Only what is not zero is written.** The tables are clear when the colony goes in,
  so a dome's power and operators are left alone instead of being written as 0.
- **The domes and the pad share a template.** A dome record and a structure record
  both begin with `cx`, `cy` and two bytes (size and room, or kind and size),
  followed by the state and 255. So four rows of four bytes describe all four sites,
  and `ngc_rec` writes each one.
  - The stamp reads the same table: each site's 4 × 4 starts at centre / 2 − 2. The
    separate list of rectangles is gone.
  - So is the template's machine column, which held `NO_MACH` for two domes out of
    three. The one machine, the first dome's oxygen generator, is two stores.
- **The stamp takes `tile_addr` once a site** and steps 128 bytes a row. Its four
  variables are gone.
- **Both corridors come from one loop**, and the graph's three edges from
  `cr_link_bc`. This is a label inside `route.asm`'s `cr_link` that takes `B` and `C`
  and adds both directions. It ends in `rt_mark`, which a new game calls anyway:
  `wheel_reset` clears `rt_dirty`, and `game_new`'s own `rt_mark` sets it again.
- **The stocks and the clock are pairs.** Each is the low byte of an address in the
  economy's page and a value, for the 17 bytes that are not zero. Each pair is
  `assert`ed to the page.
  - Two macros, `NG_BYTE` and `NG_WORD`, name the fields.
  - The old table of fourteen stocks was half zeros, and ten more stores set the
    clock, the random seed and the flags.

The check was a script kept out of the repository, on `build/main.sna`. It ran the
game for 400 frames and then called `game_new` from 40 starting states:

- the first as the game left it;
- the other 39 with random bytes in everything `game_new` clears or writes: bank 6
  from the agents to `&7FFF`, bank 2 from the economy to the end of the graph, and the
  whole world plane.

It compared every byte that changed in all eight banks, and all 40 were identical.

**What the planted faults found.** Thirty-six faults were run against the script and
fourteen tests that start from `game_new`:

- `test_game.py`, `test_loop.py`, `test_needs.py`, `test_power.py`,
  `test_balance.py`, `test_save.py` and `test_map.py`;
- `test_build.py`, `test_meteor.py`, `test_fit.py`, `test_sound.py`,
  `test_reveal.py`, `test_speed.py` and `test_disc.py`.

- **One changes nothing.** Not writing `cr_a` back to 0 before the second corridor
  is the same program: both corridors leave from dome 0, so `cr_plan` never swaps the
  ends. The script found every byte the same. The write stays, for a start colony
  whose second corridor does not.
- **The script caught the other thirty-five.**
- **The fourteen tests together caught seventeen.** `test_game.py` caught fourteen,
  `test_power.py` twelve, `test_save.py` eight, `test_meteor.py` seven. `test_map.py`,
  `test_build.py` and `test_speed.py` caught none. The eighteen they let through:
  - **all five faults in the stamp**: no foundation under the pad, every site one
    tile east, bit 3 kept, the next row 64 bytes on, three rows instead of four. None
    of the fourteen looks at the plane under the start colony;
  - the second corridor: its record not written, or its tiles never stamped;
  - each wipe one byte short: the economy, the graph, the bank-6 block, and the last
    job slot;
  - integrity 254, and the oxygen generator at 100 health;
  - the colonists not indoors, without a destination, or with the third page of
    needs empty;
  - the last economy pair (the population cap) missing;
  - `wheel_reset` left out.
- **`tests/test_newgame.py` catches all thirty-five** that change anything.

`tests/test_newgame.py` calls `game_new` directly in `main.sna` from eight starts:

- the game as it runs;
- seven with garbage in everything `game_new` clears or writes, and in the whole
  plane.

It checks the result against [§10.1](#101-start-state) written from the prose, not
from the Z80:

- **The economy**: cleared, except for the stocks, the clock, the seed, the flags, the
  living and the cap. The five meteor bytes past the cleared 86 are left alone.
- **The job board**: every slot `NO_JOB`, and nothing else in it touched.
- **The graph**: 0–1, 0–2, 2–64 and, since milestone 86, 0–65 (the airlock), both
  ways, and no other degree.
- **Bank 6's block**: clear, except for the three domes and their one machine, the
  pad, the airlock, the three corridors, the three agent columns at 255, and four
  colonists. Their needs are full and their ring slots come from `corr_fill`.
- **The world**: foundation and occupancy under the four sites and the airlock's 2×2,
  with the decor kept.
  The corridors' tiles get occupancy alone, as `cr_stamp` gives them; the tiles come
  from `tools/route.py` and `tiles_of`. Nothing else changes.
- **`rt_dirty` and `wh_slot`.**

It holds the whole call, `ui_init`'s first redraw included, to no slower than this
milestone measured; milestone 73's file fails. Its four negatives are:

- two agent columns at 255 instead of three;
- three rows of foundation;
- one economy pair fewer;
- the needs on two pages.

**Two things the test's own first runs got wrong:**

- **A corridor is not foundation.** The rule first stamped the corridors' tiles like
  the domes'. `cr_stamp` sets occupancy only, as [§9.4](#94-corridor-routing) says it
  should: concrete under a diagonal would paint four times what the corridor stands
  on.
- **The figure cache is not `game_new`'s.** It sits right after the corridor table in
  bank 6, and `ui_init`'s first redraw rebuilds it. The check stops at the table's
  end.

#### Beside the ship, at milestone 87

The user's choices: the ship carries **today's stocks plus what the old start colony
was worth, without the landing pad** — three small domes (36 Metal, 24 Bioplastic),
the oxygen generator (8, 2), ten corridor tiles (60, 30) and the airlock (10, 6), so
Metal 75 → **189** and Bioplastic 45 → **107**. The pad (45) is built later, for ships.
Water and food need a canteen from the start, as before; outside, the four breathe
from suits that last ten minutes (milestone 90, [§6.6](#suits-at-milestone-90)).

`game_new` (`src/newgame.asm`, 442 → **289** bytes) wipes as before, writes the ship
record and the occupancy of its 2×2 (no foundation: it landed, nobody built under it),
and puts the four at node 64 with `F_ALIVE` alone. The graph has no edges at all.

**Measured from the empty start** (scratch scenarios through the real menu, as
`tools/balance.py` builds; the four have the same needs and move together, so they
mostly die together):

| The player builds | First death | Of what |
|---|---|---|
| nothing | sol 1.72 (1.75 before the suits), all four | thirst — there is no canteen. Their suits had 74 units left, three minutes: thirst comes first |
| a Canteen and its airlock | sol 1.72 (1.67), three | **oxygen, inside** — they went in to drink and stayed in a dome with no generator |
| an Oxygen dome fitted, a Canteen, the airlock, a solar panel | sol 4.42 (4.33), all four | oxygen at night: no power, no generator |
| the same and a collector | sol 5.05 (5), all four | thirst — Water 60 → 0 by sol 4.5, oxygen full all the way |

Measured again at milestone 90, with the suits (`tests/test_suit.py`'s world, the
same builds, at ×4): nobody died of a suit. Those who reached a minute outside
while building walked back to the airlock and went on from there, and the four
dates moved by a few hundredths of a sol, the walks back being the difference.

The last two are milestone 86's "panel" and "panel + collector" lines, with the
domes built rather than given: the opening has the same shape, and the cargo pays
for it with 94 Metal and 71 Bioplastic left — an extractor (22) is the next thing.
The second line was the interim rule showing: until the suits of milestone 90, the
safest place without a generator was outside. Now it is for ten minutes.

**The old colony is a test fixture now.** Most tests need domes, corridors and people
inside to test anything, and building them through the menu would make every one of
them a scenario. So the old start lives on as `src/colony.asm`, in
`build/main.sna` but not on the disc. Until milestone 90 it was assembled after
`zz_bank0_end`; since 91 it is in **the last page of the ghost's log** (`GH_BUF`,
bank 2, just under `PAGE2_CODE`), outside `game2.bin` as it was outside `game.bin`,
and bank 0's code took its place. The cursor writes the log from its start, so only a
very large ghost reaches that page, and a `game_new` of the colony after one would
not find it — no test does that. `tests/test_game.py` writes `build/colony.sna`, the same snapshot with the
byte `ng_colony` set, and `game_new` jumps to the fixture when it is. Nineteen tests
start from it directly, more through `test_place.py` and `test_reveal.py`, and so does
`tools/balance.py`; it sets the airlock's `ST_JOINED`, puts the four
inside, and sets the stocks and cap of milestone 86 (75, 45, 8). An `assert` keeps
it inside that page.

**`tests/test_newgame.py` checks both**, each from the prose: the empty start
(economy, an empty graph, the ship's record and occupancy, four outside) and the
fixture (the old rule, with `ST_JOINED`). Its negatives are now two agent columns, the
ship with one row of occupancy, the colonists inside, one economy pair fewer, the needs
on two pages, and — on the fixture — three rows of foundation and the airlock without
`ST_JOINED`. A new game with `ui_init`'s first redraw takes **249,931 µs**, half the
480,535 of milestone 74: there is nothing to draw (**249,986** since milestone 88,
which clears the whole economy, 92 bytes instead of 86).

### 10.2 Milestones

No victory screen — Planetbase's own choice, and the right one for a game about a
colony that either continues or does not.

| Milestone | Requirement | Reachable today? |
|---|---|---|
| Foothold | 10 colonists, all needs green for one sol | ✅ |
| Industry | Metal, Bioplastic and Spares produced on site | ✅ |
| Independence | all ten stocks produced on site; no merchant trade for five sols | ✅ — and since milestone 93 trading is possible, so the second half means something ([§6.11](#trade-at-milestone-93)); since 94 the Ore must be dug ([§6.7](#drilling-at-milestone-94)), and since 95 carried to a store or the ship, where it counts as made ([§6.7](#hauling-at-milestone-95)) |
| Automation | 8 bots | ✅ from milestone 92 — and never before ([below](#automation-at-milestone-92)) |
| Habitat | 80 colonists, independent, five consecutive sols with no deaths | ✅ |

**"All needs green" is the colony's indicator, not every colonist's bar.** With ninety
people somebody is always walking to the canteen, and a milestone that can never be
met is not a milestone. It reads oxygen, power, and whether there is any water and
food at all — which is what a player would see on the HUD.

Everything is counted **once per sol**, in one pass, and never inside the hot slots:
128 agents every 750 revolutions costs nothing. Milestones are sticky; streaks are not.

#### Automation, at milestone 92

**It was never reachable, not even while the ships brought bots.** It counted bots
that were alive *and working* (`F_WORKING`), and `F_WORKING` is set only by the
arrival of an Operate, Heal or Defend job ([§6.7](#67-jobs)) — none of which a bot can
take. A bot builds (Build), carries (Supply, Haul) and drills (Drill), and none of
those sets it. The slot-15 test made its eight bots by writing the flag by hand.

The player chose **eight living bots**, counted at the sol's change over their
sixteen places ([§6.1](#colonists-and-bots-at-milestone-92)), and bots come from the
Bots stock ([§6.11](#bots-at-milestone-92)). `tests/test_bots.py` makes eight from the
stock in the running game and the next sol sets the bit; with seven it does not.
What bots could do then was Build and Supply: Haul and Drill had no publisher, so a
colony's bots worked when there was something to build, and stood in the factory when
there was not. Since milestone 94 driller bots dig, and since 95 carrier bots carry
the mines' Ore ([§6.7](#hauling-at-milestone-95)).

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
| 42–45 | Economy, job board, node graph — bank 2, the 2 KB under `hud_shadow` (`&8F00–&96FF` since milestone 90; `&A400` until 33) | 2,048 |
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

**The version is 8 since milestone 94** (`SV_VER`), and a save of another version is
refused, not misread. 8 adds the finished mines to the economy (`EC_MINES`), 106 → 107
bytes, so everything after it moved by one, into the gap before `rt_nodes`, which has
one left; and the seventh byte of a mine counts who digs there, with bit 7 for its
Drill job ([§6.7](#drilling-at-milestone-94)). **Milestone 95 kept 8**: a mine's pile
is its eighth byte and its Haul bit 6 of the seventh, both in the structure table the
save already holds, and a save of 94 loads with every pile empty and every Haul to be
posted. **Milestone 102 kept 8 too**: where each structure's link goes is one byte in
`node_deg`'s unused entries 96–127, inside the block, and a save of 101 loads with all of
them 0 — its paths stay as they were when one of their ends is demolished
([§9.3](#paths-that-go-at-milestone-102)). **Milestone 103 kept 8**: only where the code
that saves lives moved ([below](#where-the-code-is-since-milestone-103)). So did 104, which
changed only what an impact does to the people on their way to an airlock. 7 added the merchant's markup and cargo to the economy, 97 → 106
bytes, which moved the job board, the room index and `src/crew.asm`'s work area by
nine — into the gap before `rt_nodes`, which had exactly eleven; the save test
changes the cargo after saving and checks the load brings back the saved one.
6 is 5's layout with other meanings: ids 80–95 are bots without
needs, and a save of 91 with more than 80 colonists would hand some of them over as
bots. 5 added the ships' shares (`EC_LAND`) to the economy, 92 → 97
bytes, which moved the job board and the room index by five; `tests/test_save.py`'s
table has the new places, and the save test now changes the shares after saving and
checks the load brings back the saved ones. 4 came with milestone 90. 2 came with milestone 33's bank-2 layout, 3 with milestone 87's
meanings (`F_INDOORS`, corridors to a site that are not edges, `ST_JOINED`). Milestone
89 moved the economy inside the bank-2 block, from its first byte to its 109th, with
the machines' operator flags now in front of it, **without** a new version — a
save from 88 would have loaded its stocks from the wrong place and said nothing.
Milestone 90 moved it again, by six bytes, and turned `skill` into the suit. The
block's address comes from `hud_shadow` in the layout, so the game is never wrong
about its *own* saves; what it cannot see is that an older save means something
else. So `tests/test_save.py` now holds the format of each version — where every
table of the two saved blocks is — and fails when the build's layout differs from
the one its `SV_VER` names: with version 3 written as milestone 88 had it, milestone
89's layout fails. And it saves a game stamped `SV_VER − 1`, loads it, and checks it
is refused with nothing touched; with `sv_hdr_ok`'s comparison taken out, the same
save loads.

The seed survives the generator in four bytes of bank 6 (`worldinfo`), written by
`GEN.BIN` before the game's code exists. Without them the running game has no idea
which seed built its world, because the generator is a separate loadable that is
overwritten by bank 2's data ([§13](#13-build-and-test)).

#### Where the code is, since milestone 103

`src/save.asm` and the disc's driver, `src/fdc.asm`, are not in bank 2's code area any
more. They are 630 bytes of the routing matrix's holes in bank 1, after the demolition's
([§4.2](#memory-again-at-milestone-103)), and run in the ghost's log, as the demolition
does: the log already lent its first 512 bytes to the header (`SV_HDR`), and the code
runs right after them, at `SV_ORG = GH_BUF + 512`. `S` and `L` hide the ghost before
they start (`ui_dosave`, `ui_doload`), so the log is empty.

`sv_save` and `sv_load` keep their names and their place in bank 2 (`src/demolish.asm`):
each copies the 20 rows to `SV_ORG` and calls in (`svo_save`, `svo_load`). The copy is
made on every `S` and every `L`, because a demolition or a ghost in between writes over
the log. A load used to show the cursor again from inside; it now does that in
`sv_load`, after the code has returned, since showing the ghost writes its log in
`GH_BUF`, under the code that would still be running. A save still takes 35 frames and a
load 54 (`tests/test_save.py`), and the format did not change.

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
**Milestone 100 drew a mark instead of a variant:** 24 bytes for two marks, broken
and waiting, over any machine or plant ([§6.10](#seen-at-milestone-100)).

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
| `LOADER.BIN` | `&9000` | 533 | the loader, plus the 53-byte endgame it copies to `&3FC0` |
| `BANK6.BIN` | bank 6 | 16,384 | quadrants, figures, entity tables |
| `BANK7.BIN` | bank 7 | 16,384 | structures, plants, and the reserved holes |
| `TEXT.BIN` | bank 7, over the hole | 1,017 | every string the game prints ([§4.2](#42-the-eight-banks)) |
| `BANK1.BIN` | `&7000` | 4,096 | room icons above the distance matrix |
| `PAGE2.BIN` | base bank 1 at `&4000` (bank 5 until milestone 86), then `&8000` | 7,288 (8,056 until milestone 87) | bank 2's graphics and tables |
| `BANK5.BIN` | `&7400` in bank 5 | 2,448 | the twelve machine sprites (milestone 85) and, since milestone 87, the small room icons: straight into place since milestone 86; at 85 they waited in bank 5's scratch between the data and the code ([§4.3](#43-bank-2-flat-again)) |
| `GAME2.BIN` | bank 5 at `&4000`, then `PAGE2_CODE` | 7,329 | bank 2's code — the address comes from the symbol table, not from a constant in the build script, because it moved once and the script did not |
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
| `tools/mapsize.py` | — | per-file byte counts for bank 0 and bank 2's code, by assembling a copy of `main.asm` with a label before every `include` — and, since milestone 66, one after it, so that `main.asm`'s own code is counted as `main.asm` wherever it sits. `tools/mkdsk.py` says how many bytes are left; this says who took them, which is the half that tells you what to move |
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
| Object pass | independent Python renderer from the prose, compared byte-for-byte at five camera positions (`test_object.py`); since milestone 96 the corridors centred and under the shells, and the joints computed twice, from the sprites (`tools/pack.py`) and by drawing (`scene.joint`) — six negatives: the south and the east corridor back on the axis, no joints, no joint at `b`, the south joints not mirrored, the east joint a byte off ([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)); since 97 the short bends, twelve scenes and two controls against `scene.bend` — five negatives: the switch kept closed, the diagonal on the other side, no length check, no horizontal check, the pixel a line up ([§8.4](#the-short-bends-at-milestone-97)) |
| Scrolling | equivalence: scroll *k* steps and compare with a full draw at the destination (`test_scroll.py`) |
| Screen addresses | `scr_addr` and `scr_nextline` in the game's own binary for every (x, y) of the screen at seven values of `cam_p`, 2,008 included, against §8.2's formula: `DE`, `A`, `HL` and `BC`; one call of each no slower than milestone 68 measured it — three negatives (`test_screen.py`) |
| The blit kernels, line by line | `blt_op_line`, `blt_mask_line` and `blt_mask_flip` called directly, 600 calls each, half of them on the ring's wrap point, against a model of §8.2's ring (byte *i* goes to `base | ((p + i) & &7FF)`) and of mode 0's mirror: the whole screen, `HL` or `IX`, nothing written outside the screen; an 80-byte line, plain and wrapping, no slower than milestone 66 measured it — three negatives (`test_blitline.py`) |
| The camera and the view's rectangles | `view_cam` at 1,024 cameras, including the ones outside the world: `cam_off`, `cam_p` and the CRTC's R12/R13 read back from the emulator against the formula of §8.2; `vr_clip` with 2,400 rectangles against the intersection with the view, Z outside and for zero length, the `td_*` and the clip otherwise; `view_rect` and `view_add` outside the view: Z, the screen untouched, under 1 ms; R13 left unwritten and `dk_clamp` answering NZ outside as the negatives (milestone 61, `test_view.py`) |
| The world's edge | the real game driven from the start to the four corners of the world, two directions held: on every frame the cursor in −64…63 and the camera in x −64…44, y −64…54, neither going back or more than a tile at a time; at each corner the view built by the scroll strips equal to a full redraw; the solar collector taken to the east edge and a small dome chosen, the cursor at 126 and not across the world — four negatives (`test_edge.py`, [§8.2](#the-world-has-an-edge-at-milestone-78)) |
| What is under the cursor | `I` pressed on 705 tiles of the real game, paused: every tile of the starting domes' and structures' footprints and the ring outside, more domes and structures written into the tables in every size, kind, room and state with integrity 0, 32, 128, 254 and 255, corridors, every ground and a mountain with and without ore, the four corners; rows 3–4 as [§9.1](#what-is-under-the-cursor-at-milestone-79) formats them, `LOOK`'s line back after a step and after `ESC`, a second `I` refreshing, `I` not waiting behind a held message — five negatives (`test_info.py`) |
| The action menu | the real game, paused: on the middle of every dome (the starting ones, and more in all three sizes and six rooms, airlock, empty and lounge among them) and on tiles with none, `FIRE` in `LOOK` decides whether `M` must show FIT red, and the prose's rule whether DEMOLISH is red (milestone 101); SHIP red or not in the eight combinations of Control room, pad and ship already coming; left/right round the seven of `SPACE` both ways with the cursor and camera unmoved, rows and bar following; every MANAGE item and the ship with `FIRE` and with `SPACE`, and the state and rows it leads to — DEMOLISH taking down a dome of the scene each time; the menu behind a held message; `S` and `L` paused, the chooser and each change of slot shown at once — eight negatives, DEMOLISH always green the eighth (`test_act.py`, [§9.1](#what-can-be-done-here-at-milestone-80)) |
| The button bar and the help screen | the real game, paused, against a bar drawn by the test itself (`barread.py`): every group and item by its letter, the three sizes and the ten rooms in each with the right ones red, a letter that is not on the bar, closing and remembering, the corridor, a key held 25 frames, the arrows across groups, `SPACE` `SPACE`, `1`–`4`, `H` as jump and step, `FIRE` in `LOOK`; the help screen entry by entry — 34 since milestone 93's merchant — and back to the same state, bar and view; `ui_tick` idle in `LOOK`/`MENU`/`PLACE` and `ui_panel` unchanged no slower than milestone 83, a button ≤ 3,100 µs, a frame of the bar ≤ 10,000, the help ≤ 400 ms — nine negatives (`test_bar.py`, [§9.3](#graphical-buttons-at-milestone-84)) |
| HUD | content against a reference in five states — numbers wider than their field, zero capacities, `LOW POWER`, food, meteors — all forty lines of the two Mode 1 bands; boundary against a marker in both bands; cost against a limit (`test_hud.py`) |
| The raster splits and the bands | the emulator's picture against screen memory decoded with each line's mode and palette, every pixel of 200 lines, the Z80 in `ex (sp),hl`/`nop` loops in 24 phases and in the live game at `x4`; the bands identical on screen before and after 40 camera steps, paused and running, ten of them across the ring's wrap; `hud_move` alone at all 512 ring positions × 4 directions, ≤ 18,900 µs; the interrupt ≤ 1,200 µs a frame; after interrupts were off for 1–56 ms, `is_on` gives a right frame from the first VSYNC on. Negatives: no counter reset, each split early and late, a bare `ei`, an `is_on` that resets too late, no `hud_move`, a `hud_move` that stops after the first piece (`test_split.py`) |
| Sound | every effect tick by tick against a Python reference, read back from the AY's own registers; priority; the shared PPI with the keyboard; cost (`test_sound.py`) |
| Dirty list | equivalence: the same mutation through the list and through a full redraw (`test_dirty.py`) — the mutation moves an **agent**, not the renderer's figure cache, because the cache is now rebuilt from the agents; the budget by how many items are left after each pass, against a model built from `dirty_cost` (milestone 54); since milestone 100 the mutation breaks dome 1's weapons, so both draw the broken mark, and the slot is timed with its mark and without |
| An emptied ring slot | every visible occupied slot at the five cameras of `test_object.py` — 20 of them — emptied through the list and compared with a full redraw, byte for byte; with `dhs_vacate`'s call taken out, 12 differ. The clip whole again after every one of the 200 vacancies, visible or not; with the restore aimed at a bare `ret`, 4 leave it narrowed. Two emptied in one tick: one comes out, one waits; with its 18,000 µs charge patched to 0, both come out. Cost against a 25 ms limit (`test_slot.py`) |
| Input | every action, keyboard and joystick, one edge per press; and the logic with the scan cut out, `key_now` written from the CPC's matrix: every key of the table (COPY and C too, which the emulator cannot press; `I`, which took TAB's slot at milestone 79, it can) and every bit of line 9 pressed, held and released, `in_hit` and `in_held` for all sixteen actions, `C` and `DE` kept — three negatives (`test_input.py`) |
| The Build job's poster | `jb_post_build` in the game's own binary on 106 job tables — empty, full, the first free slot at every position — against the rule: the first free slot becomes `[J_BUILD, node, 255, 5, node]` (the last byte 0 until milestone 88) and nothing else changes, inside the table or 64 bytes either side; slot 0, slot 31 and a full table no slower than milestone 70 measured it; `sp_post` on the same tables for both kinds of Supply, `[kind, node, 255, 4, node]`, with `A` and `C` kept — three negatives (`test_jobpost.py`) |
| The main loop, round by round | `main.sna` for 399 rounds, the next round's inputs put in while a hook holds the Z80: a stub on each routine the loop calls logs it when the return address is the loop's own, and every round's calls are checked in order against §7.1's rule — `wheel_tick` `ui_spd` times, the meteor's sound and `mt_boom` cleared, the full redraw after an overflow, the HUD every 16 rounds outside the pause, the alarm on 1 → 0 after three calls; `ml_hudw` and `ml_alarm` after every round; the loop's own µs per kind of round no more than milestone 71 measured (the sum over the 399 is 34,874 since milestone 87, 3 more, because `main.sna` now starts empty and the rounds are other rounds: the same binary on the test colony, stubs moved above it, gives 34,871 — the test cannot live there, since it writes its stubs at `&3C00` before the start and the colony's code is there); `wh_hook` set at assembly time and a black border after `start` — six negatives (`test_loop.py`) |
| Stocks | `ec_stock_ptr`, `ec_add_stock` and `ec_make` in the game's own binary for all fourteen stocks, 336 calls against the rule — the cap, the `EC_PRODM` bit, the other stocks untouched; `ec_make` for every stock no slower than milestone 69 measured it — three negatives (`test_stock.py`) |
| Water and ore near a pump or a mine | `bd_res` called directly in the game's own binary (`main.sna`, not a test build: the same source assembled differently there at milestone 67), 1,200 times on three planes (the uitest's world, the game's, and a synthetic one with near misses), for every kind in the catalogue at sizes 1×1 to 8×8, against the rule of §6.5 written in Python: `A` and `bd_nres`, the latter starting from garbage; the mine's and the pump's search with nothing to find, no slower than milestone 67 measured it — three negatives (`test_terrain.py`) |
| Build mode | cursor, ghost-leaves-no-trace, the panel rows after a camera step (marked with `#AA` first, so a cell nobody rewrote is visible), validation, placement, payment, the dome placed **empty**, and owing its shell and corridors in loads with two Supply jobs and no Build (milestone 88) (`test_build.py`) |
| Materials first, then an engineer | the real game from the empty start, the player's keys (milestone 88): a solar panel beside the ship owes `#20`, one Supply and no Build at `FIRE`, 15 Metal gone once; loaded at the ship, `#20` → `#10` → `#00`, the stocks untouched while it is carried, no Build before the last load, only the engineer builds it; a small dome owes 2 and 1, both materials loaded, finished with `power` and `ops` at 0; with no engineer the Build waits 2,000 frames unassigned and row 2 says `NO ENGINEER`, never while materials are carried, and clears when he is back; nobody left inside the dome when it is sealed — four negatives: the Build at `FIRE` as until milestone 87, the Build open to anyone, an `sp_noeng` that never answers, an `lk_each` that puts out only the builder (`test_supply.py`). In the simulation harness: three domes made sites owing loads, with their Supply jobs, 2,400 frames byte for byte against `tools/econ.py`, once with a Storage dome as the source (carriers seen, the source in `node`) and once with none (nobody loads), every site supplied before its Build and built only by roles 1 and 5 — two negatives that must disagree: no Storage domes as sources, and a delivery that closes the job while more is owed (`test_sim.py`) |
| The build flow, routine by routine | `build.asm`'s entry points called directly in `main.sna`, against rules written from the prose: `bd_ok` for all 256 bytes; `bd_select` for every item and none, at every cursor parity; `bd_rect` at every centre and size, the world's edges included and `bd_ty` left alone when x is out; `bd_check` on random planes with a mountain rim, near the edges and out of the world, with `test_terrain.py`'s model for the material; `bd_afford` and `bd_stock_pay` around the cost; 300 commits on random dome, structure, graph and job tables — the slot, the record, the stamp, the payment, the edges to the nearest dome, the loads owed in the record and the Supply jobs — or the Build, when nothing is owed — from random totals (milestone 88), `ob_idx`, or 255 and nothing; 200 redraws with stubs; the check, `bd_rect`, `bd_afford` and the commit no slower than milestone 73 measured, with the item's own cost owed — eight negatives, the eighth a dome that does not owe its Bioplastic (`test_place.py`) |
| Rooms and the catalogue | `rm_build` for every room and size against a model of §6.5 (what the room accepts, what fits the size, the main machine first, the greenhouse by class), with the real `room_machines` and `machine_rules` and with 24 random ones; `BC`, `DE`, `HL` kept across it; every catalogue step from every position in both directions, and `rm_fix` for a dome and a structure; 11 rounds instead of 12 as the negative (milestone 60, `test_build.py`) |
| Where the ghost is drawn | `gh_box`, `gh_mark`, `gh_swap`, `gh_undo`, `gh_reset` and `gh_setpen` called directly, 1,200 operations over a screen of noise at four camera offsets (two wrap the ring inside a row) and changing clip windows, against a Python model of `ob_clip`, the screen address and the record: screen, log and bounding box byte for byte after every one; the log's limit to the byte (a mark goes in with 12 left, and with 11 touches nothing, not even the byte after the log); `gh_wrap` without `inc d` and the limit one byte higher as negatives (milestone 58), and since milestone 107 four more: the clip's end not cutting, its start not cutting, a column without `scr_nlw`, `gs_col` without its counter (`test_ghost.py`) |
| Every building needs a neighbour | `ui_validate` against `tools/reach.py` on 504 random placements — domes, structures, airlocks, corridors, paths, ranges, blocks; the ghost's marks exactly the tiles of the links; `FIRE` in the game building what the ghost showed, the world, graph and payment against the rule, the screen a full redraw, the worst iteration under 200 ms (a path 140, the airlock beside the canteen 170 since milestone 107); the first airlock alone and the dome that comes after it; the panel's total and reason; `ui_validate`'s cost in five places under ceilings; and since milestone 107 the HUD's rows 0–4 equal to their drawing from nothing after every cursor step, scroll, camera jump, change of item and `ESC`, and a cursor step's work in the game under 33,000 µs for a dome S and 20,800 for a Solar — thirty negatives ([§9.3](#every-building-needs-a-neighbour-at-milestone-85), [§9.3](#a-cursor-step-near-the-colony-at-milestone-107), `test_reach.py`) |
| Fitting | in the real binary, with the keys: a finished large Factory fitted slot by slot — the record, the payment per `fit_cost`, every machine waiting (health under 128, milestone 99), the screen equal to a full redraw, waiting marks and all since milestone 100; a slot emptied — `NO_MACH`, half back, the slot's bytes changed, the canary alive, the screen exact, worst round 40 ms — and with `dh_mach`'s jump to `dhv_rect` patched out, the machine stays on screen and the comparison fails; a replacement, with the build sound; a refusal with 3 Metal (nothing changes, the box red, the refusal's sound); `SPACE` into all eight, and `SPACE` with Metal for three — the first three, and only the refusal's sound; the choice standing on what each slot already holds, in the factory and in the greenhouse, with `fit_pick` patched one place off as its negative (milestone 55: no test caught that before); Quarters refusing to open. A greenhouse site fitted crop by crop before it finishes — the plants at health 200 at once, nothing drawn onto the site — and MIXED, then the plants appearing when it is done (`test_fit.py`). The operator rule over sparse slots in `test_sim.py`, the FIT panel and an oxygen generator fitted to the site in `test_game.py` — since milestone 99 at health 7, carried and installed by the site's builder before it produces |
| The routing rebuild | both matrices byte for byte against `tools/graph.py` in ten graphs chosen to break different things, and every `NEXTHOP` path as long as `DIST` says; the sliced rebuild equal to the whole one, in **exactly** ⌈units / B⌉ calls on five graphs with B = 1, 3, 12; `rt_mark` in the middle of a rebuild on another graph (mid-source, after a close, after an open), with the row and the queue scribbled as a load leaves them, gives the new graph whole and raises `rt_dirty`; the cost (`test_routing.py`) |
| Corridor routing | independent Python router compared on every pair of domes, then the *picture* compared at both kinds of bend (`test_route.py`) |
| The whole game | `src/main.asm` booted: start state, the economy moving inside the loop, a building placed and **finished**, and the HUD following it with no input; after 14,000 frames the screen equals a full redraw with **zero** wrong bytes, and ring slots must have emptied on the way, or the equality proved nothing (`test_game.py`) |
| The start state | `game_new` called directly in `main.sna` from eight starts — the game as it runs, and seven with garbage in everything it clears or writes and in the whole plane — against [§10.1](#101-start-state) written from the prose: since milestone 87 the empty start — the economy cleared but for the ship's cargo, the clock, the seed and the flags, the meteor fields left alone, and since milestone 93 the merchant's nine bytes cleared too (a previous game's cargo survived until then); every job slot `NO_JOB`; no edge at all; bank 6's tables clear but for the ship's record and four colonists **outside** at node 64 with full needs in `corr_fill`'s ring slots and three agent columns at 255; occupancy alone under the ship's 2×2 — and the test colony of `colony.sna` against the old rule, with the airlock's `ST_JOINED` and since milestone 96 the corridors' half tiles; `rt_dirty` and `wh_slot` — no slower than milestone 74 measured, `ui_init` included — seven negatives (`test_newgame.py`, [§10.1](#beside-the-ship-at-milestone-87)) |
| The sound player, routine by routine | `snd_tick`, `snd_play`, `snd_ping`, `snd_off` and `snd_init` called in `main.sna` in random order — 12 × 110 calls, a tick where three channels load a step and one where three end — against a model written from [§9.5](#95-sound): the AY's registers 0–13, each channel's wait, pointer and header, the mixer's shadow equal to R7 with bits 6–7 clear, no other byte in any bank, `BC`/`DE`/`HL` across `snd_ping`; the nine effects read back through the format against §9.5's table and their steps; each routine's worst case no slower than milestone 75 measured — five negatives (`test_sfx.py`) |
| The meteor, impact by impact | `mt_tick` called directly in `main.sna` from 400 random states — buildings bunched round the centre at separate densities for domes and structures, the ends of the tables alone, centres at the world's edges, every kind of tile, `r1` on and beside the sixteen values that start a shower — against the reference (`meteor_tick`) for the shower, the buildings and the jobs, the crater rule for the world, the dirty list for the screen (since milestone 100 with the `DK_MACH` of a machine the hit stopped), `mt_boom`, `ec_fdiv`, `eb_d`/`eb_s`, bank 6 still in the window, and no other byte in any bank; each kind of call no slower than milestone 76 measured — six negatives, the sixth since milestone 87 the ship knocked back to a site (`test_impact.py`) |
| Building without a freeze | a large Factory, a solar panel and a corridor placed and finished in the real binary: a **canary** byte far from the building must survive (a full redraw repaints it), the screen must match a full redraw of the same state — exactly, outside the canary, since milestone 42 — and the worst frame is measured on a clock that does not lose it at a seam. The large dome must appear in exactly eight frames, one row each, and the ghost must be back after it. The ghost is left over the finishing dome and then moved, once with the lift cut out as a negative control; the red large-dome ghost must fill the undo log **exactly**, 1,160 bytes, and with the limit one byte lower it loses its last mark (`test_reveal.py`); a corridor **with a bend** is compared against a full redraw in `test_route.py` |
| Corridors between placed domes | diagonal and bent routes between domes placed through the interface, every size: 0 bad tiles where the route crosses its own ends' footprints, a stone and a third dome still block, the old check patched back in fails. Seven built in all four diagonal directions, byte-exact against a full redraw, with B's door (since milestone 96 its joint) opposite the **last** run; the diagonal comes out **one row per frame**, as many rows as are in view — the rounds counted by a hook on the main loop since milestone 62, and a row costing 6,000 must show three in one — worst frame under 160 ms, and the ghost comes back after. Every frame of a reveal is sampled: what was already on screen must not vanish (13 bytes, against 96 with the terrain repainted; since milestone 96, with the corridors under the shells, 9 against 88). The cursor stepped onto rows still to come must leave no trace (22 bytes with `dt_ghost_rect` cut), a diagonal preview hidden again must leave no marks, and a strip one tile off for `/` must show. Since milestone 97 two short bends, the flag at `b` and the pixel grey on screen, not only equal to a full redraw that would lack it too (negative: `jtb_mark` cut, [§8.4](#the-short-bends-at-milestone-97)). Six previews hidden, two of them climbing into a horizontal run (a mark left behind with `crw_h1`'s fix cut out), and the ghost log of six routes equal to the cursor's frame plus one mark per visible tile — including the worst there is, 21 tiles, 308 bytes (`test_link.py`, [§9.4](#94-corridor-routing), [§4.2](#42-the-eight-banks)) |
| The corridor router, routine by routine | `route.asm`'s entry points called directly in `main.sna`, two domes written straight into the table: 1,500 pairs — axial, diagonal, nearly diagonal, odd distances, empty and unfinished domes, every size at either end, 40 of them reaching row −65, 166 at 64 tiles or more on an axis (no route, `cr_far` = 1, milestone 81) — with `cr_plan` against `tools/route.py`, `cr_walk`'s tiles in order against `test_route.py`'s, `cr_check` and `cr_stamp` against their rules in a random world (the stamp changing nothing else in any bank), `cr_cost` and `cr_afford` against the arithmetic; 400 commits on random tables — the first slot that fits, never past the last, payment only then, and since milestone 87 through `cr_commit_ln` with one or both domes a site in a fifth of them: the graph's edges only when both are standing (negative: an edge to a site); 500 redraws with stubs on `dirty_push` and `view_add` — the doors (since milestone 96 the joints), the diagonal's rows in view, the axial box, since 96 a column or a row wider where a centred corridor straddles a tile boundary; every fourth of the 2,024 short bends up to 12 tiles, the bend's pixel in a tile the redraw pushes (milestone 97, [§8.4](#the-short-bends-at-milestone-97)); in six geometries plan no slower than milestone 81 measured, and walk, check, afford and commit no slower than milestone 72 — twelve negatives, 96's no half column or row and 97's rows one tile right, which leave short bends out (`test_corridor.py`) |
| `TOO FAR` | the real game, paused, the player's keys into `LINK`, domes written into the table: 64 tiles on x with either dome picked first and 65 on y — row 4 `TOO FAR`, `ui_bad` = 2, `FIRE` changing neither the corridor table nor the state; 63 tiles routed both ways; a near-diagonal pair `NO ROUTE FROM THERE`, `ui_bad` = 1 — three negatives, one of them milestone 80's router (`test_far.py`, [§9.4](#no-corridor-past-63-tiles-at-milestone-81)) |
| The economy's rare branches | in the simulation harness, one balance cycle for each of eleven built cases — surplus, cap, equality, a covered deficit, the reserve's boundary from both sides, shed load charging and drawing, blackout, storm, wind 0 and 3 — and slot 15's first roll seeded into a flare, a fault, a storm and visitors; the whole economy and the domes against `tools/econ.py`. Negatives: the reserve cut, a flare offset changed (`test_sim.py`, [§6.5](#smaller-at-milestone-46)). And the needs pass with every colonist set to one of fifteen edge cases — each critical need alone and together, damage to death, recovery to its ceiling, morale at the floor, each room a need sends you to — over four revolutions: 36 hurt, 5 dead, 31 healed, all against `tools/entity.py`. Negative: the oxygen's bit of the damage cut, which the ordinary run never noticed ([§6.6](#smaller-at-milestone-53)). Since milestone 87 the first 64 also at oxygen 0, 1, 254 and 255, every fifth outside, with oxygen enough and in deficit — negatives: the "was 0" of `nd_ok`, the outside test of `nd_def` ([§6.6](#the-oxygen-step-at-milestone-87)) |
| Ships, streaks and milestones at their edges | in the simulation harness, slot 15 pinned, twelve built cases against `tools/econ.py` byte for byte (milestone 57): visitors from the roll with no pad, visitors with 5 Food and morale up to 255, colonists with room for two and with the cap already passed, all three streaks at 255, Metal and Bioplastic without Spares, nine goods of ten, Habitat independent but not industrial and the other way round, (milestone 91) colonists with 50% biologists and 50% medics, and (milestone 92) seven and eight bots in their places and eight in the colonists', and six of the bots' births — the robots machine in the second factory, in the first, in none, sixteen bots, a hole at 85, the eighth born in the revolution that ends a sol; and (milestone 93) the merchant from the roll, without a pad and with a ship already due, its cargo with three and four goods, markup 31, first good 13–15 and step 12–15, and its leaving — twenty-eight cases, the ring masks compared since 92. Negative: Automation from 9 bots makes the Z80 differ (`test_sim.py`) |
| Who comes on a colonist ship | `colony.sna`, paused: the ship's line key by key against a model of the prose, the screen and `EC_LAND` after each of 95 keys, `ESC`, the button, `FIRE`, `SPACE`, no Control room; the rule in nine colonies by hand and by `tools/econ.py`; a whole voyage from the keys to the landing; the landing's cost with 4, 48 and 76 alive under ceilings (124 until milestone 92) — thirteen negatives, the rule's in bank 6 since milestone 93 (`test_crew.py`, [§6.11](#who-comes-at-milestone-91)) |
| The merchant | `colony.sna`: the values and lots of the Z80, the reference and the prose; the cargo at six seeds on its edges against `tools/econ.py`; a whole voyage in the running game, roll to departure; the line key by key against a model of the prose, 319 keys; the balance, the stock rechecked, two deals by `SPACE` and `FIRE`; the line closing when it leaves, the red button, the ship's line on TRANSPORT, the alert; the no-trade streak; five costs — eighteen negatives (`test_trade.py`, [§6.11](#trade-at-milestone-93)) |
| Bots from the Bots stock | `colony.sna`: `bot_tick` in nine states against the prose and `tools/econ.py`; the robots machine making a Bot and the bot waking in its factory, one a revolution; 3,000 frames with no bot's bar moving and no bot going for a need; `EC_ALIVE`, the oxygen demand and `POP` without the bots; the cap at 80 with three Control rooms, no newcomer in a bot's place; in a new game without an engineer, a solar panel supplied and built by bots; Automation with eight and not with seven; three costs under ceilings — eleven negatives (`test_bots.py`, [§6.11](#bots-at-milestone-92)) |
| Drilling | `colony.sna`: the Drill tables against the prose and the reference; the flow cycle with four finished mines at 0–3 at work and a site, with and without power, against `flow_cycle` byte for byte — the Ore, `EC_MINES`, the board, the structures and bit 7 — no second post, nothing with the board full; who wakes in six states against `bot_tick`; a mine on the vein built by the engineer, a worker arriving, the Ore of each cycle for the number at work, the suit sending them back, a death there, a driller bot that stays; eight costs, slot 13's three under what they were in 93 — sixteen negatives (`test_drill.py`, [§6.7](#drilling-at-milestone-94)). Since milestone 95 the Ore is the piles' (power is the last balance's `EC_POK`), the flow cycle's ceilings are under 94's measures, and a ninth cost puts the three mines in the table's last slots under the same ceiling |
| The merchant's goods carried | `colony.sna`: the `J_TRADE` tables against the prose and the reference; slot 13 in fifteen scenes — at the pad and at the ship, the next good, the end and the next revolution's departure, empty either way, the other jobs at the end (one carrying, one open and empty, one open with a load), no store, the cap, a carrier who leaves for a need or dies half way, a load for the merchant abandoned at a store, no pad either way; a pad built by the player in the running game, a deal from the line and two carriers to the end; three costs; twelve negatives (`test_carry.py`). The deal itself: no deal with the board full or no pad, the loads owed rounded up per good, 99 Meals as ten — six more negatives (`test_trade.py`). In the simulation harness, a deal carried to the end with a store and without, the Z80 against the reference byte for byte, two negatives (`test_sim.py`) ([§6.11](#carried-at-milestone-98)) |
| Machines carried | `colony.sna`, slot 13 alone in a medium Factory: eight loading scenes — in a dome in use one machine, two owing the same material, the last load and its Build, no second Build; on a site no Build for the machine, the site's own debt first, the site paid and its Build posted while the job reopens; a machine taken out meanwhile — the install visit by visit (4, 36, 68, 100, 200, the next slot, a broken one and one that owes left alone, `EC_NBUILD` back to 0) and a site finished with its machine started in the same visit; a stopped machine that does not produce, ask for an operator or break; `FIT` with the keys, four machines and two Supply jobs; from a new game, the first dome, its airlock and an oxygen generator carried from the ship and installed only by the engineer, and a second dome fitted at placement whose builder is put outside and comes back; seven costs — twelve negatives (`test_install.py`). In the simulation harness, machines in two domes in use and a site, the Z80 against the reference byte for byte, two negatives (`test_sim.py`) ([§6.9](#machines-carried-at-milestone-99)) |
| Machines marked | `colony.sna` with the player's keys, each slot's corner bytes read with the cursor hidden: both marks in bank 5 as `tools/pack.py` draws them; four machines fitted to a medium Factory, four waiting marks, then carried and installed and the marks gone one by one with the machines' own sprites left; a malfunction with no Spares, the broken mark, and with Spares the repair that takes it away; a withered plant in a medium greenhouse, the broken mark and the other three as they were; every screen equal to a full redraw — seven negatives: never a mark, a mark on machines that run, the two swapped, no push from the malfunction, the repair or the install, and the next slot drawn without its bank (`test_mark.py`, [§6.10](#seen-at-milestone-100)) |
| Demolition | `colony.sna` with the player's keys (`M`, `D`, `FIRE`): the overlay's 901 bytes in the routing matrix's holes as built; the occupancy after every demolition equal to a model from `tools/reach.py` and `tools/route.py` built from the records that remain, and the colony's own world unchanged when rewritten whole; the room lists without the dome inside `dm_do`; a Factory with two machines (half of 66 and 32 back), a dome joined by a diagonal with a bend (both records gone), a site (all back, its jobs gone, `EC_NBUILD` right), dome 0 with two colonists (at the airlock, indoors, no task, a full suit, alive 30 s later), the airlock and its far end (`ST_JOINED`, `EC_FREELK`), and the ship, the pad with a ship coming and open ground refused; every screen equal to a full redraw, again after the cursor leaves; the worst frame from `FIRE` until the list is empty ≤ 150 ms — sixteen negatives (`test_demolish.py`, [§9.3](#demolition-at-milestone-101)) |
| Paths that go | `colony.sna` and `main.sna` with the player's keys: the byte each structure keeps — two paths, x first and y first, a ground link, nothing for a dome — against the placement's own rule (`tools/reach.py`); after every demolition the world equal to a model (the world before, bit 5 off the paths that go, bit 4 from the records that remain, the new ground links in node order), bit 5 everywhere equal to the paths the bytes describe, no doubled edge, the cursor where it was, and the screen a full redraw; a Solar panel built on the old path; an airlock with two structures and a chain of airlocks hanging from it, relinked to its parent and reaching the ship; a parentless airlock leaving its children unlinked; the worst frame under 150 ms — nine negatives (`test_unlink.py`) |
| Hauling | `colony.sna`: the Haul tables against the prose and the reference; a cycle with five finished mines and a site, with and without power, against `flow_cycle` byte for byte — the piles, the cap, bit 6, Drill and Haul posted structure by structure — no second post, nothing with the board full; slot 13 with a Haul at the mine and at the ship, with no destination, a pile under 10, a loaded carrier dying, a worker choosing it over a Drill; in the running game a mine on the vein, a worker's trip and a carrier bot's, each Ore +10 at the ship; two costs — eleven negatives (`test_haul.py`, [§6.7](#hauling-at-milestone-95)) |
| The wheel | the colony of the simulation harness, `wheel_tick` one frame at a time: after `rt_mark` the graph is clean in exactly ⌈Σ (R(s) + 2) / 15⌉ frames with bank 1 in the window after each; every slot switched off for 32 frames and bank 6 and the economy untouched; `wheel_reset` at slot 0 — four negatives (`test_sim.py`) |
| Movement at its edges | in the simulation harness, `ent_move_slice` called directly in twelve agent states against `tools/entity.py`, on the colony's graph plus structures (nodes 64–71), a pair that reaches nothing and a node alone, with a dome stripped of its edges and a stale adjacency entry after routing: one agent pinned in each of the rare branches, the rest drawn — arrivals into a full ring and into a structure, working agents leaving a dome and a structure, slices that wrap round 127; after every slice the fields, the masks, the dome table and the `wh_push`es the reference implies, and the rest of bank 6 untouched; the wrap taken out as the negative (milestone 59, `test_sim.py`). The starting colony's occupancy masks exactly where its colonists stand (`test_game.py`) |
| Meteor showers | in the simulation harness, the roll, a shower and the rebuild byte for byte against the reference, and a 120-impact shower with the wheel pinned to slot 15 round an L dome — eleven impacts in its edge column, and `MT_REACH` patched to 3 must disagree (`test_sim.py`). In the game binary: a shower on the landing pad — **exactly** the craters the reference predicts from the game's own world plane and no other tile; drawn through the dirty list with the canary alive and the picture equal to a full redraw; worst frame 60 ms; the pad a site with a Build job, the oxygen machine stopped, `METEOR SHOWER` on the HUD and the impact on the AY; then the pad rebuilt and the machine repaired. Negative: `wh_push` cut, the same craters are in the world and 155 bytes of screen are wrong. The roll's 16 trigger values checked exhaustively against every other event, and its rate over 200 sols (`test_meteor.py`, [§6.10](#610-events-and-hazards)) |
| The object index, build by build | `ob_index` called directly in `main.sna` from 300 random states — 0 to 64 domes of every size, axial and diagonal corridors with their continuations, structures of every kind and size and some with no shape, equal `cy`s, only the ends of the tables alive, every camera, every combination of classes, and in half of them a dome left in `ob_corr`'s cache at the state's camera, as the screen's walk leaves it (milestone 82) — against [§8.4](#84-object-pass-and-draw-order) written from the prose, positions from `tools/scene.py`: each rebuilt class's records in draw order, a box from ⌊start/n⌋ to ⌈end/n⌉, nothing that would not be drawn; the counters, `st_n`/`st_ord`, `dome_conn` with the corridors (until milestone 96 with the figures bit), and since 97 `jtb_flags` in bank 5 and the switch `jtd_sw`, `&21` with a short bend anywhere and `&C9` without; the classes not rebuilt untouched; `ob_idx` and `ob_meas` 0, the camera back, bank 6 in the window, and no other byte in any bank but the pass's scratch; each kind of call no slower than milestone 77 measured plus the fix's 1 µs, and since milestone 96 no slower than its own: the corridors 117,082 µs, all three classes 148,201 and with the figures 147,178, against 95's 117,518, 148,748 and 157,476 with the doors' scan (97: 116,310, 147,468 and 146,651) — eight negatives, one of them milestone 81's `oi_build`, and 97's switch that does not close or does not open (`test_oibuild.py`) |
| Back to the colony | the real game: two domes built from the interface 50 tiles from the colony and linked, the arrow keys back to the colony, and the frame the scroll strips built equal to a full redraw from a clean index, in three geometries — the negative puts milestone 81's `oi_build` back, and the colony's corridors go missing, 125 bytes (`test_return.py`, [§8.4](#the-corridor-pass-forgets-the-screens-dome-at-milestone-82)) |
| Object index | each of the 200 tiles of the view drawn **on its own** (a one-tile clip over a black screen) at the five cameras of `test_object.py`, and every one equal to the same tile of the full draw — the only check that sees an object missing from the index, since the strip and the full draw both go through it. Negative: a box's right edge one tile short, 21 tiles lose a piece. And the empty pass under 4 ms, against 49 before (`test_index.py`, [§8.4](#84-object-pass-and-draw-order)) |
| Needs beat the board | the food colony of [§6.6](#66-needs) run for 9,000 frames, watching the *bars* rather than the corpses, plus the player's canteen getting an operator (`test_needs.py`) |
| Who stops first | the reserve rule on the reference implementation — one unit either side of the threshold, and a storm-length night with the reserve knocked out beside it — then the two-pump colony in the real binary: load shed, oxygen never zero, pumps really stopped, `LOW POWER` on the screen (`test_power.py`) |
| The map is a constraint | the pump refused on dry ground **with the reason on screen**, accepted at the shore and actually built; the mine likewise at a vein; and a dome and a solar panel accepted on the same dry ground, which is what separates "this rule" from "this patch of dirt" (`test_map.py`) |
| The disc | `RUN"HABITAT` from a cold BASIC prompt: the game arrives, the start state is there, the HUD is drawn, the wheel's code is in bank 6 byte for byte (milestone 92; 1,219 bytes since 93, 1,282 since 94), the icons and the placement's code in bank 1 (milestone 94), the demolition's code in the routing matrix's holes, 1,086 bytes byte for byte (milestone 102), and the save's 630 in the rows after it (milestone 103), and the world is **generated** rather than loaded (`test_disc.py`) |
| Disc driver | the μPD765 without AMSDOS: reads the disc's own **catalogue** and compares it with the host's `.dsk` byte for byte, then writes three sectors, reads them back, and checks the neighbouring sector is untouched (`test_fdc.py`) |
| Save and load | a small dome placed beside the ship first (since milestone 87 the empty start never moves by itself), freeze the wheel, photograph the state, `S`, run 18,000 frames until it has moved, `L`, and assert the economy, the world plane and the **picture** are back, the ships' shares and the merchant's cargo too, changed in between — plus a load from an empty slot that must be refused; since milestone 103 the save's code comes in from the routing matrix's holes on every `S` and `L`, so the first save runs with `rst 0` written over all of it, and a last negative without the copy does not save (`test_save.py`) |
| Inside and outside | the real game from the empty start, the player's keys: the four at the ship outside and no oxygen demand; the first dome tied to the ship by the ground, its engineer at the site **outside**, and when it is done no edge left and the engineer at the ship, outside; the airlock below it with its corridor in the table, `ST_JOINED`, the ground to the ship and **no** corridor edge until it is done, then the edge and its builder inside; nobody left in the sealed dome and everyone standing in the finished airlock inside (milestone 88, when the carriers stand there too); a colonist sent from the ship to the dome — outside on the ground with oxygen still 255 after two buildings' time, inside from the airlock on, and losing oxygen in the dome; one of those inside sent back to the ship, the demand two per colonist inside, and in that deficit those outside keeping their oxygen for 600 frames — six negatives: the dome keeping its ground link, the builder kept in, the corridor an edge at placement, the airlock without air, breathing outside, the demand counting everyone — in bank 6 since milestone 93 (`test_outside.py`, [§6.2](#inside-and-outside--milestone-87)) |
| Suits | `main.sna`: ten minutes of suit at the start, one unit every 128 frames, death at zero with health untouched, `SUIT AIR LOW` under a minute; out of an airlock with a full suit, back to it alone at a minute; a meteor on an airlock puts those standing in it outside, and since milestone 104 those in the tube on the way to it — a real shower aimed at the airlock, one colonist in the tube each way, and 400 random calls of `lk_air_out` against `tools/entity.py`; an impact on a working airlock under 7,100 µs; nothing served at a site outside; 32 structures in `rooms_rebuild` — eleven negatives (`test_suit.py`, [§6.6](#suits-at-milestone-90), [§6.2](#who-was-in-the-tube-at-milestone-104)) |
| Figures outside | `main.sna`: the four below the ship, each with their role's figure, every opaque pixel on the screen; a Solar panel's carriers coming and going, the list equal to a model written from the prose for all 128 agents and the screen byte for byte a full redraw made on a copy of the machine; the first dome's ring; a meteor under a walker; every step's cost under its charge, in five cases and again with the list nearly full; and since milestone 105 457 cells erased over garbage, in open ground, beside and on a building and on veins, each equal to a full redraw, then a vacated slot off the character rows; since milestone 106 a list written by the test, two figures to every third cell, erased and painted cell by cell equal to its full redraw, the erase and the paint alone on every cell of two cameras each under its own charge, and ceilings on a step's average (2,400 µs in open ground, 3,150 beside a building) — twenty negatives (`test_figure.py`, [§8.5](#a-colonist-outside-moves-at-milestone-89), [§8.5](#a-cheaper-erase-at-milestone-105), [§8.5](#the-cells-own-way-at-milestone-106)) |
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
loaded into scratch first and copied down by an **endgame** — 53 bytes copied to
`&3FC0` and entered with both ROMs off, because the copy passes over the loader
itself and over BASIC's stack. It takes its two lengths in `BC` (code) and `IX`
(data) rather than reading them from memory that is about to disappear. Since
milestone 86 the scratch is two banks — the code in bank 5, the data in base bank 1
([§4.3](#43-bank-2-flat-again)) — and the endgame empties and zeroes each before it
pages the next, so the disc starts with the same zeros in `DIST` and `NEXTHOP` as
the snapshot. `tests/test_disc.py` boots the disc a second time and stops it in
steps of 10 µs as the endgame jumps to `&0100`: bank 2's data and code, the
machines and the icons are the build's to the byte, and both scratch areas are zero;
a third boot, from the same disc with the endgame's two clearing `ldir`s made
`nop`s, leaves 5,240 bytes in `DIST` and 6,517 in `NEXTHOP` and fails it.

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
| ~~HUD re-render on every scroll step, ≈ 0.4 frames, estimated not measured~~ | ~~Medium~~ | **Measured at 2.55 frames**, six times the estimate, and then cut ([§8.1](#81-screen-layout)). The cell cache of [§9.2](#92-hud) took an ordinary tick to 1.15, and milestone 52's smaller HUD to **0.65**; a camera step, which moves every cell, still pays **1.75** (2.30 before milestone 52, 2.20 before the font moved to bank 7 at milestone 33). The escape hatch for that one — *move* the HUD block inside the ring instead of re-rendering it — **was taken at milestone 83**: 0.89–0.94 frames per step, cheaper than what it replaced, and the HUD is never rubble after a scroll, paused or not ([§8.1](#81-screen-layout)). |
| Mid-frame writes land where aimed, but only on the emulator's CRTC | Low | The border control in `tests/test_camera.py` hits line 160 exactly. Real hardware still wants a check, but nothing now depends on a mid-frame *address* write. |
| **The raster splits of milestone 83 are timed on the emulator** | Medium | Mode and palette writes, not addresses, and timed from the Gate Array's own interrupt, which every CPC has. Each write has ≥ 10 µs of margin against a late interrupt (`tests/test_split.py` breaks it at 20 µs). Real hardware is the check still owed, and a different Gate Array (the Plus) would want its own measurement. |
| **The interrupt costs 5.9 % of every frame** (1,177 µs), estimated at 3.8 % | Medium | The waits are fixed by `R7 = 33`. `R7 = 34` would save ~500 µs a frame with the picture eight lines higher; the top wait could host `snd_tick` ([§8.1](#two-modes-and-two-palettes-the-raster-splits-at-milestone-83)). |
| Memory map slack: 1,536 contiguous in bank 2, **288 in bank 6**, 440 in bank 7 | Medium | Bank 6 is the tight one now and the entity tables grew into it. The next thing that needs space there moves `plants` out of bank 7 first, or takes the `s` room-icon set (864 B) as [§4.2](#42-the-eight-banks) names. |
| Routing rebuild latency of ≈ 4 s after a network change | Low | Stale routes are inefficient, never invalid ([§6.4](#64-routing)). If it grates: cache paths for the 16 busiest pairs and rebuild those first. |
| **13.5 s** world generation feels long even on a cassette-era machine, and it is 3.9× the original estimate | Medium | New game only — loads read the plane off disc ([§5.10](#510-player-modification)). **Both halves are built**: the progress bar of [§13.2](#132-the-loading-screen) — title, a dot per file, a bar that moves once per two world rows — and, since milestone 24, **music** ([§9.5](#95-sound)), played by the generator's own player and clocked by its own tile loop, because interrupts are off down there. The identified 2× win ([§5.9](#59-cost--measured)) is held in reserve. |
| A seed produces a technically valid but miserable map | Low | Feature anchors guarantee the necessities; the headless seed sweep ([§13](#13-build-and-test)) finds the rest. |
| A full-colony routing rebuild is ~22 s of stale routes at the current budget | Medium | Only at 128 nodes; 48 nodes is 3.4 s ([§6.4](#64-routing)). It was 27.7 s until milestone 62 made `rt_node` 22 % cheaper and milestone 63 made a lone source's opening 0.13 ms instead of 1.6 ([§6.4](#a-cheaper-opening-and-a-budget-of-15-at-milestone-63)). Together they let the budget go from 12 to 15 with no frame worse than before: the worst slice measured went from 13.5 ms to 10.4. One lever is left untaken: raise the per-frame budget while the camera is still. A lone source's largest cost is now its closing, two 128-byte copies, 1.7 ms. |
| ~~Slots 11, 12, 13 and 15 of the wheel are unwritten~~ | ~~Medium~~ | **Written and measured.** Four of six budgets were low, by 1.5× to 5× ([§7.2](#72-the-wheel)). The worst frame is a third of a frame, so the design holds. Remaining passes should be budgeted pessimistically. |
| A heavy sim slot and a scroll column in the same frame come to ~19 ms of 20 | Medium | The dirty list is a budget, so the edge redraw spreads over two frames. Costs nothing but a one-frame lag on the newly exposed column; needs watching once the HUD re-render ([§8.1](#81-screen-layout)) is measured too. |
| ~~Needs, health and death are not written~~ | ~~High~~ | **Written.** Colonists eat, drink, sleep, get treated, die, and grieve; the only loss condition is live ([§6.6](#66-needs)). |
| ~~Nothing produces food~~ | ~~High~~ | **Greenhouses grow.** Plants sit in the machine slots, `plant_class` decides the crop, and one biologist tends the whole dome ([§6.5](#65-economy)). |
| ~~Ships, trade and milestones are unbuilt~~ | ~~Medium~~ | **Built**, Automation last: from milestone 91 ships bring no bots, and from milestone 92 they come from the Bots stock — and it was unreachable before that too ([§10.2](#automation-at-milestone-92)). |
| ~~A heavy sim frame plus a scroll column comes to 19.9 ms of 20~~ | High | **Worse than that, and now measured.** A scroll step is 3.0–8.8 frames of world plus 2.30 of HUD (1.75 since milestone 52) ([§8.2](#82-camera)), so it was never going to fit in one frame and does not need to: the dirty list is a budget and the strip fills over several frames. What this costs is **latency, not frame rate** — about a quarter of a second per tile through a dense base. The flow-balance slot still wants the fix described below. |
| ~~The flow-balance wheel slot re-scans 64 structures every revolution~~ | ~~Medium~~ | **Resolved, and not for speed.** 7,887 µs for numbers that change slowly — but the reason it moved was [§6.5](#65-economy)'s clock: a battery that charges 750 times a sol is not a battery. The scan, the battery and the pumps now run once per 64 revolutions (`FLOW_DIV`), the living are still counted every revolution, and a finished building kicks the balance so the panel the player just paid for shows up at once. |
| ~~Nothing the player does exists: no build mode, no input, no HUD, nothing drawn since milestone 5~~ | ~~High~~ | **Resolved.** The colony is drawn, the camera scrolls, the dirty list keeps it honest, the HUD reports — and the player now moves a cursor, opens a menu, places a dome and routes a corridor between two of them ([§9.1](#91-controls), [§9.3](#93-build-flow), [§9.4](#94-corridor-routing), [§6.9](#69-construction)). |
| ~~The two halves have never been assembled into one binary~~ | ~~Medium~~ | **Assembled, and it did not fit: 20,571 bytes wanted 16,128.** Resolved by moving the generator out, cutting `MAX_NODES` to 96 and putting code in bank 2 ([§4.2](#42-the-eight-banks)). It also turned up duplicate constants in three files and, worse, [§7.4](#74-one-convention-per-half-and-they-disagreed)'s paging disagreement. |
| **Memory is the binding constraint from here on** | High | **287 bytes free in bank 0 (95 under the tests' floor at `&3E00`), 139 in bank 2's code area, 28 in bank 6 (and 11 of `b6code`'s 1,554 for code), 7 in bank 1's `b1code` and 1,344 in the routing matrix's unused columns, 5 in bank 7 and none in its `text` block, 83 in bank 5 (19 of them in `b5code`'s 248; this row said 664 through milestone 96, which was 336)** — after milestone 107 made a cursor step beside the colony a quarter cheaper with 192 bytes of bank 0 (80 of them the panel's cache) and 75 of bank 2, after milestone 106 made a step outside a third cheaper again, with 241 bytes of bank 2, and charged the vein it draws, after milestone 105 made a step outside a fifth cheaper and kept the veins under the walkers, after milestone 104 put whoever was in the tube to a struck airlock outside, after milestone 103, a step for memory alone, took 247 bytes back from bank 0 without slowing what runs every frame and moved the save and the disc's driver into the routing matrix's holes, 597 bytes of bank 2, after milestone 102 took a demolished structure's paths with it and hung what hung from it from its parent, after milestone 101 let the player demolish, with the code in the routing matrix's holes, and took 199 bytes back from bank 2, after milestone 100 marked the machines that do not run and took 72 bytes back from bank 0 without slowing anything, after milestone 99 carried the machines' materials and had an engineer install them, after milestone 98 carried the merchant's goods and shrank the interface's code by 491 bytes to make room, after milestone 97 closed the short bends, after milestone 96 centred the corridors and gave the doors' place to the joints, after milestone 95 carried the mines' Ore, after milestone 94 made the mines need people and drew the paths outside, after milestone 93 brought the merchant, after milestone 92 made bots from the Bots stock, after milestone 91 let the player choose who comes on a ship, after milestone 90 gave the colonists suits, after milestone 89 drew the colonists outside, after milestone 88 carried the materials to the sites, after milestone 87 put the colonists outside beside their ship, after milestone 86 made airlocks the doors, after milestone 85 joined every building to a neighbour, after milestone 84 put the commands on buttons with a help screen, after milestone 83 put the HUD in two Mode 1 bands, after milestone 82 fixed the corridors that went missing after a trip, after milestone 81 refused corridors past 63 tiles, after milestone 80 put what can be done on `SPACE`, after milestone 79 showed what is under the cursor, after milestone 78 gave the world an edge, after milestone 77 shrank the object index's build, after milestone 76 shrank the meteors, after milestone 75 shrank the sound, after milestone 74 shrank the new game, after milestone 73 shrank the build flow, after milestone 72 shrank the corridor router, after milestone 71 shrank the main loop, after milestone 70 shrank the Build job's poster, after milestone 69 shrank the stocks, after milestone 68 shrank the screen addressing, after milestone 67 shrank the search for water and ore, after milestone 66 shrank the blit kernels, after milestone 65 shrank the wheel, after milestone 64 shrank the controls, after milestone 63 spent 30 on the routing's opening, after milestone 62 shrank the routing rebuild, after milestone 61 shrank the view, after milestone 60 shrank the rooms, after milestone 59 shrank the movement, after milestone 58 shrank the ghost, after milestone 57 shrank the ships and milestones, after milestone 56 shrank the tile pass, after milestone 55 shrank the fitting, after milestone 54 shrank the dirty list, after milestone 53 shrank the needs pass, after milestone 52 shrank the HUD, after milestone 47 shrank the job board, after milestone 46 shrank the economy, after milestone 45 fitted domes slot by slot, after milestone 44 shrank the interface, after milestone 43 shrank the object pass by a fifth, after milestone 42 redrew an emptied ring slot as the full pass would, after milestone 41 cut the ghost's log to its worst case and moved the index's build up, after milestone 39 indexed the object pass, after milestone 38 brought the meteors, after milestone 37 drew diagonal corridors a row at a time, after milestone 36 joined them to the colony, after milestone 35 put the milestone-2 blit kernels, which only their own tests still call, behind `HAS_QUADS`, after milestone 34 spent 279 and 118 on building without a freeze, and after milestone 33, which found two reservations nobody had ever read (`ui_cursor` 256 in bank 2, `audio` 2,048 in bank 7), moved the font into the second, and let `newgame.asm` and `fdc.asm` follow `save.asm` into bank 2 ([§4.3](#43-bank-2-flat-again)). Bank 0's ceiling is `&3EC0`, where the tests' own scaffolding runs, and the loader's two scratch areas are checks now too. Bank 6's *156* was wrong by 128 — `tools/pack.py` has been printing **28** all along, which is what happens to a figure copied into a document instead of read out of the build. The ledger: 26–29 spent 671; 30 handed back 560; 31 spent 152 and took 192 back from the test floor; 32 spent 144; 33 handed back 957 and cost 29 in paging; 34 spent 279 in bank 0 (the ghost's swap and bounding box, `view_rect`, the `DK_BUILT` handler) and put its cold half — the two post-placement redraws — in bank 2 for 118; 35 spent 200 in bank 0 (the row-by-row reveal, the one-pass mirror, the ghost's rectangles) and 82 in bank 2, and took 268 back from `blit_quads` and `flip_span`, whose only callers left are `tests/blittest.asm` and `tests/packtest.asm`; 36 spent 23 in bank 0 (the door scan looking one record ahead) and 59 in bank 2 (`crk_in`, and B's door in `cr_redraw`); 37 spent 113 in bank 0 (the `DK_CROW` handler, `dt_ghost_rect`, `view_add`, the budget's carry) and 183 in bank 2 (pushing the rows, a walk that visits each tile once); 38 spent 64 in bank 0 (the shared Galois step, `ec_break_d`, the Build-job poster moved out of `build.asm`, the boom and the HUD line, two bytes for `ship_crew`'s exits) and 431 in bank 2 (`meteor.asm`, 48 of it the scan that keeps an impact at 3 ms, less the poster `build.asm` gave up), and moved the loader's code scratch to `&6800` ([§4.3](#43-bank-2-flat-again)); 39 spent 538 in bank 0 on the object index — the walk, `oi_build` and its measuring hooks, the class bits — and took 1 back in bank 2 ([§8.4](#84-object-pass-and-draw-order)), the most any milestone has spent on one thing, for 47 ms off every scroll step and every redraw of a strip. Bank 2's 23 went to 15 at milestone 40, for the climbing turn. **41 spent the last soft reserve**: the ghost's log went from 1,600 to the 1,160 its worst ghost needs — computed, and checked to fit whole ([§4.2](#42-the-eight-banks)) — and the 440 bytes took the object index's build up from bank 0 (`src/objindex.asm`, 347 bytes; the structure sort stayed below, because the whole file did not fit): bank 0 88 → **428**, bank 2's code area 15 → **108**. 42 spent 220 of it in bank 0: `dhs_vacate` (the terrain under an emptied slot and the object pass over it, both clipped to its 2×8, and its own charge to the budget) and `tile_src`, split out of `tile_one` so the two share the terrain lookup — 428 → 208. **43 took 737 back**, all of it by writing the same thing fewer times: `object.asm` 3,130 → 2,490, and its clip's register interface 76 out of `dirty.asm` and 21 out of `ghost.asm` — 208 → 945 ([§8.4](#84-object-pass-and-draw-order)). **44 took 283 more out of `ui.asm`** (2,224 → 1,941), by the same means: one routine for "left/right, cyclic" where the save slot and the build menu each had their own, one for "change state around the ghost", one for a ghost mark at a world tile (the route's tiles and the bad tiles of a footprint had one each), and coordinate pairs read and written as words — 945 → **1,228** ([§9.3](#93-build-flow)). It would have been 295: a table-driven `ui_sig` was 12 bytes smaller and 139 µs slower on every cursor step, and went back. **45 spent 750 in bank 0 on the fitting**: `src/fit.asm` 757, `ui.asm` 34 for its hooks and `ui_ud`, `dirty.asm` 40 for `dhv_rect`, the emptied machine slot and the clip's restore, less `rooms.asm`'s `rm_fitout` (75) and 6 out of `econ.asm`; bank 2's code area got 6 back from `bd_commit`'s call — 1,228 → **478**, 108 → **114**. The fitting's names and keys took 187 of the text block's 194. **46 took 422 back out of `econ.asm`** (1,549 → 1,097, 58 of it moved to the shared `stock.asm`, which let `fit.asm` drop its own copy of the capped add: 23 more), by the same means as 43 and 44 ([§6.5](#smaller-at-milestone-46)) — 478 → **900**. **47 took 272 out of `jobs.asm`** (1,089 → 817), and made slot 13 faster on the way ([§6.7](#smaller-at-milestone-47)) — 900 → **1,172**. **52 took 390 out of `hud.asm`** (1,032 → 642) and 9 out of `ui.asm`, which now asks the HUD for a column instead of stepping to it, and the HUD redraw got 23–44% faster ([§9.2](#smaller-at-milestone-52)) — 1,172 → **1,571**. **53 took 187 out of `needs.asm`** (963 → 776), and the room index, the worst frame of the wheel, went from 34 % of a frame to 23 % ([§6.6](#smaller-at-milestone-53)) — 1,571 → **1,758**. **54 took 173 out of `dirty.asm`** (1,126 → 953), most of it a second copy of the view clipping in the terrain handler ([§8.5](#smaller-at-milestone-54)) — 1,758 → **1,931**. **55 took 92 out of `fit.asm`** (734 → 642) and gave 1 to `rooms.asm`, the empty choice in front of `rm_buf` ([§9.3](#smaller-at-milestone-55)) — 1,931 → **2,022**. **56 took 112 out of `tiles.asm`** (633 → 521), and a full terrain pass went from 9.7 frames to 8.9 ([§8.3](#smaller-and-faster-at-milestone-56)) — 2,022 → **2,134**. **57 took 197 out of `ship.asm`** (574 → 377), a third of the file, most of it a loop that rebuilt two constant masks every sol and a new colonist written field by field ([§10.2](#smaller-at-milestone-57)) — 2,134 → **2,331**. **58 took 56 out of `ghost.asm`** (484 → 428), and every ghost operation got faster on the way — the size check became a carry, and the screen address is taken from what the bounding box has just loaded ([§9.3](#smaller-and-faster-at-milestone-58)) — 2,331 → **2,387**. **59 took 124 out of `entity.asm`** (449 → 325) and 3 out of `newgame.asm` in bank 2: the agent's id stays in a register instead of being read back before every field, and the movement slot of the wheel went from 1,298 µs to 899 ([§6.3](#smaller-and-faster-at-milestone-59)) — 2,387 → **2,511**, bank 2's code area 114 → **117**. **60 took 92 out of `rooms.asm`** (372 → 280): the main machine is moved to the front of the list after the scan instead of being looked for before it, and every routine got faster ([§6.5](#smaller-and-faster-at-milestone-60)) — 2,511 → **2,603**. **61 took 72 out of `view.asm`** (356 → 284) and 3 out of `dirty.asm`: the camera's offset without the +64 that drops out of the mod, R12/R13 in four `out`s, and `dk_clamp` answering in the zero flag ([§8.2](#smaller-at-milestone-61)) — 2,603 → **2,678**. **62 took 91 out of `graph.asm`** (314 → 223), 11 of it `rt_rebuild`, which only the tests call and now carry themselves, and a rebuild got 18 % faster: the queue's tail in `HL'`, and its indices stored as the low byte of their slot ([§6.4](#smaller-and-faster-at-milestone-62)) — 2,678 → **2,769**. **63 spent 30 of it**: `rt_open` resets only the entries the previous source wrote, and the routing budget went from 12 to 15 expansions a frame with no frame worse than before ([§6.4](#a-cheaper-opening-and-a-budget-of-15-at-milestone-63)) — 2,769 → **2,739**. **64 took 120 out of `input.asm`** (292 → 172): the joystick is one `or`, because line 9's bits are the first six actions in order, the table is two bytes an action, and `key_now` keeps the PSG's own polarity ([§9.1](#smaller-and-faster-at-milestone-64)) — 2,739 → **2,859**. **65 took 32 out of `wheel.asm`** (211 → 179): `wh_push` tests the hook's high byte and keeps `A`, the routing lives in `wh_frame` and keeps its carry across the paging, and one multiply serves movement and needs ([§7.2](#smaller-at-milestone-65)) — 2,859 → **2,891**. **66 took 85 out of `blit.asm`** (205 → 120) and 7 out of `screen.asm`: one split at the wrap point for the three line kernels, with the kernel in `IY` and the remainder in `AF'`, `scr_ringtop` folded into it, and `blit_op` behind `HAS_QUADS`; every line got faster ([§8.2](#smaller-and-faster-at-milestone-66)) — 2,891 → **2,983**. **67 took 37 out of `terrain.asm`** (115 → 78): water and ore are one test, `(byte & D) == E`, and the margin is walked from a single `tile_addr`; the pump on dry ground went from 3.3 ms to 2.0 ([§6.5](#smaller-and-faster-at-milestone-67)) — 2,983 → **3,020**. **68 took 63 out of `screen.asm`** (114 → 51): `scr_rowtab`'s 50 bytes became four additions, (y & `&F8`) × 10, and `scr_addr` lost its `push`/`pop` and 20 µs a call ([§8.2](#smaller-and-faster-at-milestone-68)) — 3,020 → **3,083**. **69 took 5 out of `stock.asm`** (58 → 53): `ec_make`'s mask is `#80` rotated with `rlca`/`djnz`, and `ec_add_stock` lost an `or a` its own `add` makes unnecessary ([§6.5](#smaller-and-faster-at-milestone-69)) — 3,083 → **3,088**. **70 took 5 out of `jobpost.asm`** (32 → 27): `inc (hl)` turns a free slot's 255 into `J_BUILD`'s 0 ([§6.7](#smaller-and-faster-at-milestone-70)) — 3,088 → **3,093**. **71 took 29 out of `main.asm`'s own code** (187 → 158): the loop's four one-caller helpers inline, `ml_alert`'s edge one carry, `wh_hook` set at assembly time; every round of the loop got 5–21 µs faster ([§7.1](#smaller-and-faster-at-milestone-71)) — 3,093 → **3,122**. **72 took 491 out of `route.asm`** (1,672 → 1,181), in bank 2: the two ends are records that trade places, both bends are one formula, and a diagonal is walked as a straight line; planning got 20 % faster, the walk 38 %, the check 30 % ([§9.4](#smaller-and-faster-at-milestone-72)) — bank 2's code area 117 → **608**. **73 took 280 out of `build.asm`** (1,068 → 788): `bd_ok` in six instructions that leave every other register alone, so `bd_check` no longer saves three around each tile; `bd_rect` in 8 bits; `bd_link` walking the dome table with a pointer; the footprint check under the cursor got twice as fast ([§9.3](#smaller-and-faster-at-milestone-73)) — 608 → **888**. **74 took 276 out of `newgame.asm`** (670 → 394): one flow instead of four routines, bank 6's five tables cleared as the one block they are, the domes and the pad from one template that the stamp reads too, and the stocks and the clock as (address, value) pairs ([§10.1](#smaller-at-milestone-74)) — 888 → **1,164**. **75 took 202 out of `sound.asm`** (540 → 338): the data 28 bytes smaller (a noise step without a high byte, channel and priority in one byte, one-byte distances for `sn_tab`), the step's bytes sent to the chip straight from the effect through `HL`, the mixer one formula, five variables and two tables gone; every call got faster, and `build/sounds.wav` is the same to the byte ([§9.5](#smaller-and-faster-at-milestone-75)) — 1,164 → **1,366**. **76 took 61 out of `meteor.asm`** (438 → 377): the footprint test inside the scan, which hands its record and its count back so the node is worked out only on a hit, the structures walked on from where the domes end, the world's edge one `or`, a crater one mask and one way back to bank 6, and three variables gone; every path got faster or stayed equal ([§6.10](#smaller-and-faster-at-milestone-76)) — 1,366 → **1,427**. **77 took 37 out of `objindex.asm`** (347 → 310) and 2 out of `object.asm` in bank 0: the classes to rebuild passed in `A` instead of a variable, a pass that counts into a byte beside its own pointer and hands the count back, the structures' ids looked up by a routine of their own instead of a flag asked on every record, and both ends of a box from one formula; every call got faster ([§8.4](#smaller-and-faster-at-milestone-77)) — 1,427 → **1,464**, bank 0 3,122 → **3,124**. **78 spent 35 in bank 0 and 27 in bank 2 on the world's edge**: the cursor stops at the last tile, the camera at x −64…44 and y −64…54, the half-tile snap goes back at 127, and a camera loaded from an old save is clamped ([§8.2](#the-world-has-an-edge-at-milestone-78)) — bank 0 3,124 → **3,089**, bank 2 1,464 → **1,437**. **79 spent 56 in bank 0, 273 in bank 2 and 256 of bank 7 on `I`**: `src/info.asm` reads the tile under the cursor into the HUD's message rows, `ui.asm` gives it a state, and the text block grew from 1,024 to 1,280 for the ground names, with the font moved up behind it ([§9.1](#what-is-under-the-cursor-at-milestone-79)) — bank 0 3,089 → **3,033**, bank 2 1,437 → **1,164**, bank 7 952 → **696**. **80 spent 29 in bank 0, 304 in bank 2 and 65 of the text block on the action menu**: `src/act.asm` builds the list of what is possible under the cursor and runs the chosen key's own code, `fit_can` splits the question out of `fit_enter`, `ui_tick` asks for `LOOK` first, and the slot chooser is redrawn as soon as it opens or changes ([§9.1](#what-can-be-done-here-at-milestone-80)) — bank 0 3,033 → **3,004**, bank 2 1,164 → **860**. **81 spent 13 in bank 0, 45 in bank 2 and 21 of the text block on `TOO FAR`**: domes 64 tiles or more apart on an axis get no corridor instead of one planned the wrong way, `cr_side` asks that and parity once and writes out the two routines it called twice, so `cr_plan` got 28–101 µs faster ([§9.4](#no-corridor-past-63-tiles-at-milestone-81)) — bank 0 3,004 → **2,991**, bank 2 860 → **815**. **82 spent 2 in bank 2**: `oi_build` clears `d_id` together with setting `ob_meas`, so a corridor-only rebuild no longer measures from the screen's camera, and the colony keeps its corridors after the player scrolls back from building one far away ([§8.4](#the-corridor-pass-forgets-the-screens-dome-at-milestone-82)) — bank 2 815 → **813**. **83 spent 687 in bank 0 and 15 in bank 2 on the Mode 1 bands, and gave 728 back in bank 7**: the interrupt handler, its set-up and `is_on`, 267 at `&0103` behind a 3-byte `jp start` ([§8.1](#two-modes-and-two-palettes-the-raster-splits-at-milestone-83)); `hud.asm` 642 → 1,019, almost all of it `hud_move`, the band clear and the band addressing ([§9.2](#mode-1-bands-at-milestone-83)); `view.asm` 25; the loop's `ei` and the call 4; 6 of alignment in `rooms.asm`, whose `rm_buf` crossed a page when everything moved; `save.asm` 15 for the disc's `di` and `is_on`; and the font in Mode 1 is half the bytes — bank 0 2,991 → **2,304**, bank 2 813 → **798**, bank 7 696 → **1,424**. **84 spent 1,449 in bank 0, 746 in bank 2 and 1,329 of bank 7 on the buttons**: `bar.asm` 1,073 (the 33-button table, the letters' generated scan, the bar's signature and `bar_want`, `sl_draw`'s colour tables and buffer), `help.asm` 280, `ui.asm` 96 for its hooks and the faster signature; `button.asm` 637 in bank 2 (one button on screen, the key code generator, the two-a-frame drawing) and `act.asm` 109; the text block grew by 768 for the help screen's 790 bytes of names and lines, and the 33 symbols are 561 ([§9.3](#graphical-buttons-at-milestone-84)) — bank 0 2,304 → **855**, bank 2 798 → **52**, bank 7 1,424 → **95**. **85 moved the twelve machine sprites, 1,584 bytes, out of bank 2's graphics to bank 5 above the object index, and spent 980 of them in bank 2's code area and 15 in bank 0 on the building rule**: `link.asm` 1,041 (the search, the ghost's marks, the commit, the path's redraw), `route.asm` 14 for the entry points it shares, `info.asm` 8 for `PATH`, less 83 out of `build.asm` (`bd_link`'s search for the nearest dome); `ui.asm` 19 for its hooks, the reason in `ui_bad` and the cost in the panel's signature, `object.asm` 2 for paging bank 5, less 1 out of `terrain.asm` (`bd_nres` went to `build.asm`) and 5 of `rooms.asm`'s alignment; and the text block 16 for `PATH BLOCKED` ([§9.3](#every-building-needs-a-neighbour-at-milestone-85)) — bank 0 855 → **840**, bank 2 52 → **608**, bank 7 95 → **79**. **86 spent 275 in bank 2's code area and nothing in bank 0 on the airlocks**: `link.asm` 1,041 → 1,216 (three kinds, the airlock's nearest dome, `NO CORRIDOR FITS`, `EC_FREELK`), `route.asm` 1,240 → 1,292 (the airlock as an end of size −1 in `cr_read` and `cr_side`, and no door for it in `cr_redraw`), `newgame.asm` 394 → 442 for the start colony's airlock; in bank 0 `ui.asm` 6 for the new reason, paid by `object.asm` 2 (`ob_conn_scan` rewritten round `IX` and an 8-byte bit table, which also paid back the airlock's check in time) and 4 of `rooms.asm`'s alignment; and the text block grew by 16 for `NO CORRIDOR FITS` (21 bytes, 5 of them the block's old slack) ([§9.3](#airlocks-are-the-doors-at-milestone-86)) — bank 0 **840** as before, bank 2 608 → **333**, bank 7 79 → **63**. Bank 2's code no longer fitted in bank 5 beside its data at load, and the loader's scratch became two banks ([§4.3](#43-bank-2-flat-again)). **87 spent the `s` room icons**: 864 bytes of bank 2's graphics moved to bank 5 after the machines, and bank 2's code area took 494 of them — `door.asm` 370 (a site finished: sealing, putting the builder out, the corridors' edges; `en_in`, `en_put` and the unrolled count), `edges.asm` 63 (`cr_link_bc`, `cr_edge` and `gr_live`, for every build), `link.asm` 1,216 → 1,398 (the ground link and its anchor, `ST_JOINED`, the ship skipped), `meteor.asm` 14 (the ship, and `x − MT_REACH` carried in `B`), `build.asm` 10 (`SHIP`), `info.asm` 7, `route.asm` 1 (`cr_lnk` and `cr_commit_ln`, less the edges that went to `edges.asm`), less `newgame.asm` 442 → 289 (the old colony is a test fixture after `zz_bank0_end`, 251 bytes in the snapshots and none on the disc); bank 0 paid 94 — `entity.asm` 325 → 380 (the indoor rules and the shadow-register loop), `needs.asm` 776 → 806 (two entry points), `object.asm` 8 (paging bank 5 for the small icons), `rooms.asm` 8 of alignment, `jobs.asm` 6, less `econ.asm` 13 (the count went to bank 2); and 96 bytes of padding keep six low-byte tables inside their pages ([§4.3](#43-bank-2-flat-again)) — bank 0 840 → **746**, bank 2 333 → **607**, bank 5 1,552 → **688**. **88 spent 453 in bank 2's code area, 2 in bank 0 and 24 of bank 7 on carrying the materials** ([§6.9](#built-at-milestone-88)): `supply.asm` 354 (the poster that `jobpost.asm` was, the Supply's two legs, the source, `NO ENGINEER`), `build.asm` 725 → 779 (the loads written into the record, and the search for a free record that made placement three times faster for a dome), `door.asm` 370 → 415 (everyone standing at a finished dome or airlock, not only its builder); in bank 0 `jobs.asm` 823 → 852 (the arrival, the source on taking, the reap's copy, two roles, `EC_NBUILD`) and `hud.asm` 8, less `jobpost.asm`'s 27, gone to bank 2, and 8 of `rooms.asm`'s alignment; the text block grew by 20 — bank 0 746 → **744**, bank 2 607 → **154**, bank 7 63 → **39**. **89 spent 1,133 in bank 2's code area on drawing the colonists outside, and took 8 back in bank 0** ([§8.4](#colonists-outside-at-milestone-89)): `figure.asm` 1,131 and `door.asm` 2; the ring stopped being baked, so bank 6's 3,456 bytes of slot figures became 1,152, and the corridors and connectors (896) moved there from bank 2, whose graphics shrank by 1,024 — `PAGE2_CODE` `&A100` → `&9D00`; in bank 0 `object.asm` 2,496 → 2,550 (`ob_fig`, and the six fixed-table lookups written out), `entity.asm` 380 → 430 (the marks, and the movement's body inside the slice's loop), `ship.asm` 377 → 398, `tiles.asm` 521 → 540, `needs.asm` 1, less `dirty.asm` 950 → 797 (`dhs_vacate` is gone: an emptied slot is the empty slot now) — bank 0 744 → **752**, bank 2 154 → **45**, bank 6 28 → **1,564**. **90 spent 224 in bank 2's code area, 34 in bank 0 and 20 of the text block on the suits** ([§6.6](#suits-at-milestone-90)), **and moved the object pass's eight tables out of bank 2 to make the room** ([§4.3](#43-bank-2-flat-again)): 238 bytes into bank 6's gap, 24 into bank 5, `PAGE2_CODE` `&9D00` → `&9C00`; `suit.asm` 187 (the unit, the minute, `su_lock`, the alarm, the outside decay), `door.asm` 417 → 441 (`lk_air_out`), `meteor.asm` 391 → 400, `newgame.asm` 289 → 293; in bank 0 `hud.asm` 1,027 → 1,039 (`SUIT AIR LOW`, and the count on every tick), `needs.asm` 807 → 819 (`nd_out`, `T_NEED` kept outside), `entity.asm` 4 (the fill on exit), `ship.asm` 2 (a newborn's suit) and 4 of `rooms.asm`'s alignment — bank 0 752 → **718**, bank 2 45 → **77**, bank 6 1,564 → **1,326**, bank 5 688 → **664**, bank 7 39 → **23**. **91 spent 340 in bank 0, 67 in bank 2's code area and 54 of the text block on who comes on a ship** ([§6.11](#who-comes-at-milestone-91)), **and made the room by moving the tests' floor and the colony fixture**: `crew.asm` 340 (`cw_count` 126, `cw_pick` 62, and the line — `cw_ud` 37, `cw_ext` 28, `cw_panel` 83 — and 4 of variables), `ship.asm` 400 → 409 (`ship_crew` searching from the first dead id), `hud.asm` 1,039 → 1,046 (`hud_to`, out of `act.asm`), less 7 of `rooms.asm`'s alignment; in bank 2 `act.asm` 413 → 470 (the line's mode, `cw_open`, `cw_tick`) and `newgame.asm` 293 → 303 (20% each); in the text block the five names and the keys' line, paid by 70 bytes of trailing spaces (2,120 → 2,104 used); and `cw_count`'s 33 bytes of records in bank 2's data, in the gap before `rt_nodes` (44 → 11). The colony fixture (251) left the space after bank 0's code for the last page of the ghost's log, and the tests' floor went from `&3C00` to `&3D60`, with `tests/test_loop.py`'s stubs taking their address from `ZZ_BANK0_END` ([§4.2](#42-the-eight-banks)) — bank 0 718 → **369**, bank 2 77 → **10**. Bank 0's code ends at `&3D4F`, 17 bytes under the floor, and the floor cannot rise further: `test_loop.py`'s 220 bytes of stubs and its log fit under `&3EC0` only from `&3D60`. There is no slack left in the log; room in bank 2 has to come from code, as milestones 72 to 77's did, or from data that only one bank's reader needs, as milestone 90's did. `tools/mapsize.py` says *who* is spending bank 0. The reserves that remain, in order: bank 6's gap (1,298, data the object pass or the entity code reads), the rest of bank 5 (664, data only) and of bank 7 (23, data only), and the tests' scaffolding itself — `test_loop.py`'s stubs and log would have to move to bank 2 for bank 0 to grow; the `s` room icons were spent at milestone 87. Every file in bank 0 has now had its milestone; `main.asm`'s own loop was the last, at milestone 71. Bank 0's 17 under the floor and bank 2's 10 are both tight now: the next milestone's code has to be paid for, the text block has 16, and bank 5 has 600 above the icons for data (664 with the 64 under the machines). **92 opened a third code area**: 256 bytes of bank 6 under `agent_fields`, for code only the wheel calls ([§4.2](#code-in-bank-6-at-milestone-92)), and `bot_tick` took 165 of them; in bank 0 the jump to it, the needs pass's test and the cap cost nothing in all — the bots' count for Automation over their sixteen places is 12 bytes smaller than reading every agent's role, `sh_born` gave its tail to the bots as `sb_rest` and `econ_events` jumps instead of calling — bank 0 369 → **380**, 17 → **28** under the floor; bank 6 1,326 → **1,070**. The cells of [§4.2](#42-the-eight-banks)'s table for banks 0 and 2 still said 718 and 77 after milestone 91; they say 380 and 10 now. **93 spent bank 6's gap on code, to pay for the merchant's line**: `b6code` 256 → 1,280 at `&6700`, and `src/ship.asm` but `ship_call` (368), the specialties' count and pick (188) and slot 12 (`src/flow.asm`, 352) moved into it from bank 0, unchanged, with the merchant's cargo (146); bank 0 spent 792 on the line (`src/lines.asm`, which took the ship's line's 152 from `src/crew.asm`), 32 on the button and the bars, 26 on the HUD (the alert, `mer_here`, the padding, `hn_pow`'s 10,000), 28 on the values and lots, 21 on the merged roll and 6 of `rooms.asm`'s alignment; bank 2's code area 2 for the button's action; bank 7 17 on its symbol, and the text block got 90 back from the alert line's padding and spent 99 on the merchant's texts and help; the economy 9 bytes, out of the 11 before `rt_nodes` ([§6.11](#trade-at-milestone-93)) — bank 0 380 → **383**, 28 → **31** under the floor; bank 2 10 → **8**; bank 6 1,070 → **46**; bank 7 23 → **6**. Bank 6's gap is spent: the next code has to come out of what is there, or bank 0's wheel-only code that remains — `econ_events`, 220, which did not fit — out of somewhere else. **94 found the somewhere else in bank 1**: 160 bytes above the room icons, where the window's default bank lets the UI's code run ([§4.2](#code-in-bank-1-at-milestone-94)); `al_commit` and the structure's path moved there from bank 2 (120 with `al_lgo`), with the new ground link (32); bank 2 spent 19 on `al_cbr`, 12 on `al_s4`, 29 on posting Drill (`src/drill.asm`), 45 on the job board's mask (`jb_open`) and 14 on domes without foundation and keeping the ground link's other end; bank 0 got 18 bytes back, one with `op_ptr` (21) shared by the three places that kept a dome's operators and bit 7 cleared at the arrival, 17 with the assignment's loop rewritten round the mask; `b6code` took the gap's last 18 and spent 63 on the flow's mines and the bots' rule (`dr_need`, 20), less what the empty slots' fast path saved; the economy one byte (`EC_MINES`), out of the 2 before `rt_nodes` — bank 0 383 → **401**, 31 → **49** under the floor; bank 2 8 → **9**; bank 6 46 → **28**, `b6code` 61 → **16** free; bank 1 160 → **7**. **95 moved the tests' floor** from `&3D60` to `&3E00`, 160 bytes the game never wrote ([§4.2](#milestone-31-found-the-floor-under-bank-0-and-it-is-not-3fc0)), and bank 0 spent 127 of them on hauling (`src/haul.asm`: `hl_pile` 47, `hl_arrive` 80) and 20 on the job board (the arrival's dispatch, `ja_haul`, the reap's exception), and got 2 back from the Ore's sum (`ef_ore`); bank 2 spent 4 making `dr_post` the general `st_post`; `b6code` got 9 back — the Ore's sum and its `ec_make` gone from the flow, `ld de` out of the empty slots — less the call to `hl_pile` — bank 0 401 → **256**, 49 → **64** under the floor; bank 2 9 → **5**; `b6code` 16 → **25** free. |
| ~~Nothing finishes what the player starts~~ | ~~High~~ | **Built.** A Build job is picked up, the agent routes to the site, works it 32 points a visit, and at 255 the building turns `DS_ACTIVE` and is drawn ([§6.9](#69-construction)). `tests/test_game.py` walks the whole chain: place a solar panel with 30 Metal, and about six seconds later the HUD says `ALL SYSTEMS OK` with no key pressed in between. |
| ~~A completed building stalls the game for 0.8 s~~ | ~~Medium~~ | **Resolved at milestone 34 — and it was 360–920 ms, not 0.8 s.** The site is already on screen from placement; what completion changes is the room icon and the machines, so the Build job pushes one dirty record (`DK_BUILT`) and the handler draws those two things — a structure, nothing at all ([§6.9](#69-construction)). The completion frame of a large Factory is **120 ms** (100 at milestone 34), 60 of them lifting the ghost the player left on it; a solar panel's is an ordinary 40 ms HUD tick. The freeze did not go away entirely, though — it was always at **placement** too, and that is the next row. |
| ~~Placing a large dome still freezes the game for 0.86 s~~ | ~~Medium~~ | **Resolved at milestone 35 with the eight-chunk reveal of [§6.9](#69-construction), at placement.** A dome goes into the dirty list one tile row at a time and each row draws only that dome; the ghost waits for the last row. Worst frame of a large Factory's placement: 998 → 859 → **140 ms**; solar panel 439 → 220 → **120**; straight corridor 260 → **120**. The levers this row named were all taken: the reveal, a one-pass mirror (`blt_mask_flip`: the whole large site 450 → 351 ms, a full redraw of the view 839 → 679), and marks without clips on a log of rectangles (red ghost 263 → 57 ms). |
| ~~The ghost of a large dome on bad ground overflows its undo log~~ | ~~Low~~ | **Resolved at milestone 35.** The log holds rectangles now, not lines ([§9.3](#93-build-flow)): the same ghost is 1,160 bytes instead of 2,412, and all eight rows of marks are drawn. |
| ~~No corridor with a diagonal run can be built between placed domes~~ | ~~High~~ | **Resolved at milestone 36, and it was both ends, not one.** Measured over 72 geometries: every route with a diagonal had bad tiles and **every** bad tile was in the footprint of one of its two domes — the start's corner (two tiles for a large dome), and for a pure diagonal the destination's corner too, up to 6 of 10. `cr_cb_chk` now lets the corridor cross the footprints of its own two ends and nothing else ([§9.4](#94-corridor-routing)); all 56 routes the planner finds among those geometries pass. Building them showed a second fault the check had been hiding: a bent corridor's destination got its door opposite the **diagonal**, at a ring point nothing reaches, in the Z80 and in the Python reference alike — it is visible in the old `tests/golden/route_*.png`. Fixed in both. A diagonal corridor's placement cost 160–220 ms against a straight one's 120, because its redraw box was a square; since milestone 37 it appears a row per frame and the worst frame is 80–100 ([§6.9](#69-construction)). |
| ~~A diagonal corridor preview leaves marks behind the cursor~~ | ~~Medium~~ | **Found and resolved at milestone 37, by looking at the row-by-row reveal.** The marks of the route still under the press stayed on the ground until a row painted over them. `cr_walk` visited the tile two consecutive diagonal pieces share twice, the ghost marked it twice, and the forward undo wrote the second entry's "background" — the first mark — last ([§9.3](#93-build-flow)). Every diagonal preview did it, built or not: 48–56 bytes left behind each time the cursor moved, hidden only when a corridor was built and its whole bounding box repainted. The walk now visits each tile once; `tests/test_link.py` hides four previews and compares with a full redraw. **Not quite: milestone 40** found the climbing turn into a horizontal run still marking its first tile twice — none of the four previews climbed into one ([§9.3](#93-build-flow)). The test hides six now. |
| ~~The simulation still pushes nothing into the dirty list~~ | ~~High~~ | **Wired for ring slots**, which is what moves: `ent_claim` and `ent_release` push a `DK_SLOT`, and the figure cache is rebuilt once per burst rather than once per slot ([§8.5](#85-the-dirty-list)). Machines breaking, plants growing and room changes still push nothing. |
| **A near-diagonal pair of domes cannot be connected** | Low | The turn in [§9.4](#94-corridor-routing) spends `\|S − T\|` tiles, so when the two axes differ by less than the destination's radius there is no route and the panel says so. The band is 2–4 tiles wide and the player can step out of it by moving the dome. Closing it needs a corner sprite the art does not have. |
| ~~**Domes more than 63 tiles apart on one axis get a corridor that goes the wrong way**~~ | ~~Medium~~ | **Resolved at milestone 81: they get none, and the panel says `TOO FAR`** ([§9.4](#no-corridor-past-63-tiles-at-milestone-81)). Found at milestone 72, older than it. `cr_side` subtracted the two centres — half tiles, −128…127 — in 8 bits, so a difference past ±127 wrapped and the route was planned in the opposite direction; some of those stayed inside the world, passed the check, and would have joined the two domes in the graph through a corridor that does not reach B. The two fixes on offer were refusing such routes or routing them with a 9-bit difference; the player chose refusal, with its own message. |
| ~~The population cap has a two-digit field~~ | ~~Low~~ | **Closed at milestone 92**: the cap is at most 80 ([§6.1](#colonists-and-bots-at-milestone-92)), so `POP 34/48`'s two digits always hold it and the count. It was 4 + 48 per Control room up to 128 — 100 with two, shown as ` 0`. Found at milestone 52. |
| **The rest of the dirty-list call sites** | Low | A plant growing pushes nothing — **and would change no pixels if it did**: a plant's sprite is chosen by class, not by stage. A machine breaking, repaired or installed pushes `DK_MACH` since milestone 100, which gave it a mark to draw ([§6.10](#seen-at-milestone-100)). Ring slots were the only change the picture can show, and they are wired. A colonist who dies releases a slot, so that path is covered; one who arrives by ship gets no ring slot until they move. Wire the rest when the art gives them something to draw. |
| ~~The dirty redraw does not hide the ghost~~ | ~~Low~~ | **Resolved at milestone 34, without the bracket and without its cost.** Every dome-shaped dirty item compares the dome's frame with the bounding box of the ghost's undo log (kept by `gh_rect` since milestone 35) and, only on overlap, **swaps** screen and log before drawing — and once more at the end of the tick ([§9.3](#93-build-flow)). The cursor over open ground costs nothing; over a busy dome, two swaps of its log. The old binary fails `tests/test_reveal.py` on exactly this: 222 wrong bytes in 25 tiles after the ghost leaves a dome whose ring slots changed under it. |
| ~~A vacated ring slot leaves 2–7 wrong bytes~~ | ~~Medium~~ | **Resolved at milestone 42 — and the diagnosis here was wrong.** It was not clipping. A figure's 2×8 is opaque with the ring baked in, so a colonist *arriving* is exact; the *empty* variant is the ring over black, while the full pass draws the ring over terrain and shows it wherever the ring is transparent. The experiment that seemed to clear the art — "draw the whole dome clipped to the slot" — drew it over the empty variant's black, so of course it gave the same wrong pixels. Measured over the test colony: 12 of the 20 visible occupied slots went wrong when emptied, by up to 8 bytes. `dh_slot` now calls `dhs_vacate` for an empty slot: terrain under the 2×8, then the object pass, both clipped to it — the full pass by construction. It costs 18.0 ms on average and 20.9 at worst, and charges itself 18,000 µs in the dirty list so it has its frame to itself ([§8.5](#85-the-dirty-list)). `tests/test_slot.py` empties every one of the 20 and compares each with a full redraw byte for byte; with the call taken out, 12 differ. **Every shape tolerance went with it:** `tests/test_game.py` now requires zero wrong bytes after 14,000 frames *and* that ring slots actually emptied on the way (two do), and `tests/test_reveal.py`, `test_link.py` and `test_meteor.py` compare exactly outside their canary. |
| **The base is invisible on its own foundation** — **mostly closed at milestone 94** | Low | Domes stand on their own ground and the landing zone is ground ([§9.3](#paths-on-the-ground-at-milestone-94)); what is left on foundation is the structures and the paths. Until then: the foundation tile, the dome rings and the corridors are all the same grey. Outside the base everything reads; inside it, the colony disappears into the slab. Found by looking at the first running build, not by any check. It is a palette question for [§8.6](#86-palette) — one pen, differently chosen. |
| ~~A full redraw at the west edge of the world draws the wrong rows~~ | ~~Medium~~ | **Resolved at milestone 78.** The camera stays within x −64…44 and y −64…54, the cursor stops at the last tile instead of wrapping, and at the edge the cursor's one-tile margin is given up ([§8.2](#the-world-has-an-edge-at-milestone-78)). Found at milestone 56, older than it. The camera is never clamped to the world: the cursor wraps and is always on a tile from −64 to 63, and `ui_follow` keeps one tile of margin, so with the cursor on the westmost column the camera stands at x = −65. `tile_addr` for −65 gives an address one byte before the row, and the row walk steps through it in 16 bits, so the first tile *inside* the world is read from the next page: two rows down for an even row, one for an odd one. A **full** redraw there — after a load, say — draws every tile of the view from the wrong row, while a scroll strip or a dirty rectangle, which starts inside the world, draws them right. The test world hides it for eight columns, which happen to be the same ground on every row. The east edge (x = 64) and the rows −65 and 64 read bytes outside bank 4, and show them. Milestone 56 kept every one of those bytes as it was, so that its own check could be exact. Proposed fix: clamp the camera to the world (x −64…44, y −64…54), which needs a decision on the cursor's margin at the edge. That is what milestone 78 did, after a player walked off the map and watched the scroll run through a minute of garbage. |
| **Scrolling is 6 to 15 tiles per second through a built-up base** | Medium | 0.6–1.0 frames per tile in open ground, 1.6–5.0 in the base (5.4 before milestone 43; 3.0–3.4 and 4.0–7.8 before milestone 39's object index; 8.8 before milestone 35 mirrored dome quadrants in one pass instead of through a buffer), plus 2.30 for the HUD — which is now the larger half of a step in open ground. Two levers left: move the HUD block instead of redrawing it ([§8.1](#81-screen-layout)), and blit tile pairs ([§8.3](#83-the-tile-pass)). ~~Index which objects overlap which strip instead of testing all 224 records~~ — taken at milestone 39 ([§8.4](#84-object-pass-and-draw-order)). |
| ~~**A broken machine is invisible on screen**~~ ([ASSET-8](#12-asset-gaps)) | ~~Medium~~ | **Resolved at milestone 100, with a mark instead of a sprite.** A broken machine or a withered plant shows red with a white `!` at its top left, and a machine waiting for its materials or its engineer (milestone 99) shows yellow and black stripes ([§6.10](#seen-at-milestone-100)). Two marks of 2 × 6 bytes, drawn by `tools/pack.py`, instead of the 132 bytes per machine a damaged variant would cost; a malfunction, a repair and an install push the slot's redraw. |
| Intruders are unbuilt ~~— and meteors~~ | Medium | **Meteors came at milestone 38** ([§6.10](#610-events-and-hazards)): they waited for the world plane and the dirty list, and use both. Intruders still need edge spawning and combat, which is not a simulation problem either. |
| A new game says `NO OXYGEN` for its first 10–20 seconds | Low | Found while testing the meteor alert, not fixed: `game_new` sets `EC_O2OK` to 1, but slot 12 recomputes it every revolution as production ≥ use, and production is only published by the flow cycle, once in 64 revolutions. Until then it is 0 and the HUD's second-highest alert stands over a colony that is fine. The klaxon is spared by `ml_warm`; the line is not. `tests/test_meteor.py` waits for the first publication before it starts. |
| A struck structure looks untouched | Low | A meteor knocks a structure back to a site, but the renderer only draws a *dome's* site differently ([§6.9](#69-construction)) — a structure under construction looks finished, the pad included. Consistent with how a new structure looks while it is being built; the player learns of the hit from the HUD, the noise and the builders walking out. |
| ~~Ships, trade and milestones are unbuilt — [§6.11](#611-ships-and-arrivals) and [§10.2](#102-milestones)~~ | ~~Medium~~ | **Closed at milestone 93** — this second copy of the row above was left open since milestone 9. Ships came then, the milestones with them, bots at 92, and trade at 93 ([§6.11](#trade-at-milestone-93)). |
| The balance numbers in [§6.5](#65-economy) are first guesses and three of them were unlivable | Medium | Corrected against the first working colony ([§6.6](#66-needs)). Expect the same of the rest: they cannot be checked by reading, only by running the loop and looking at who is where. |
| ~~A new dome has no room and no machines, and nothing can give it either~~ | ~~High~~ | **Built, and it took three bugs with it.** The room is the menu's second axis ([§9.3](#93-build-flow)), the dome fills its own slots from `room_machines` and `machine_rules` ([§6.5](#65-economy)), and a greenhouse comes up full of plants. On the way: a construction site linked itself to *itself* and no dome the player placed had ever been finished ([§6.9](#69-construction)); an agent that found its destination unreachable kept the job ([§6.3](#63-movement)); and the loader's endgame was holding 512 bytes for forty ([§4.2](#42-the-eight-banks)). |
| ~~A colony of four cannot staff the food chain~~ | ~~Medium~~ | **They could. They were dying on the way to the canteen.** [§6.6](#66-needs)'s "their own needs outrank the board" dropped the job by writing `NO_TASK`, which is how the tables spell *idle*, so the assignment pass handed the work straight back and the colonist oscillated between machine and canteen until it died with Food in store. Going to eat is now a task the board does not touch (`T_NEED`), and the same colony — greenhouse, lab, canteen, four people — runs **eight sols with no deaths**, Food bottoming at 12 on sol 6 and climbing back to 27. `tests/test_needs.py` watches the bars, and its negative control on the old binary is bars pinned at zero for 1,100 frames. |
| ~~One food chain feeds four, not twelve~~ | ~~Medium~~ | **It feeds twelve, once three things stopped fighting it** ([§6.5](#65-economy), [§6.7](#67-jobs)): one biologist per greenhouse instead of one per pot, `mach_vitromeat` at 2 per run instead of matching the canteen exactly, and `Operate` priorities per room instead of a tie broken by a distance that never changes. Measured: the twelve-person colony that used to die on sol 5 now runs eight sols with nobody dead. It has **no margin** — the store still touches zero — so the remaining work is a second chain, and the HUD now says `LOW ON FOOD` while there is still time to build one. |
| ~~Water is the next thing to run out~~ | ~~Medium~~ | **Measured, and no rate needed touching.** This row asked for one thing — *measure a two-extractor colony before changing any number* — and the answer is flat: with one pump the same food colony goes **83 → 0 by sol 4** and then hovers between 0 and 6, with the oxygen generator running dry alongside it; with a second pump it goes **85 → 288 and keeps climbing**. Demand is 4 pots + `mach_vitromeat` 2 + `mach_oxygen` 1 = 7 a cycle against one large pump's 5, and the second pump turns a 2-a-cycle deficit into a 3-a-cycle surplus. The lever was already in the player's hands; the HUD's `LOW ON WATER` is how they learn to reach for it. What the second pump *costs* is the next row. |
| ~~A second pump buys water with oxygen, after dark~~ | ~~Medium~~ | **Resolved at milestone 32, and the ordering was already written down.** [§6.5](#65-economy)'s failure column said *machines stop, then oxygen stops* and `power_ok` was one flag, so the blackout that stopped the pumps stopped life support in the same revolution — 13 of 80 samples dark, oxygen production 20 → 0, the worst bar at 208. There are three levels now (`P_ALL` / `P_ESS` / `P_NONE`) and the battery lends to the machines only while eight cycles of life support stay behind it. Same colony after: **0 of 80 dark, oxygen never leaves 20, the worst bar 251**, at the honest price of pumps that stop at dusk — water climbs 63 → 147 over the window instead of 63 → 153. The HUD says `LOW POWER` while the load is shed, and a shed sol is not an all-green sol. |
| ~~The map is scenery: the lake and the ore vein mean nothing~~ | ~~Medium~~ | **Resolved at milestone 31.** `extractor (on water)` and `mine (on ore)` had been in [§6.5](#65-economy)'s chain table from the first draft and nothing read them: a pump built in the middle of the desert pumped. Now the footprint must sit within two tiles of the material — measured, not chosen: the mine is impossible at one tile, because rock always rings a mountain — and the panel names what is missing. `tests/test_map.py` holds it, negative control included: with the rule stubbed out, the two "says no" checks fail and everything else still passes. |
| ~~A machine cannot be chosen, only its room~~ | ~~Medium~~ | **Resolved at milestone 45, as in Planetbase.** A dome is built empty and fitted slot by slot from what its room allows (`FIT`, `src/fit.asm`), each machine paid for separately and half refunded when taken out ([§6.5](#a-room-says-what-fits-the-player-says-what-goes-in)). The operator rule had to change with it — it counted slots, and a lone machine in slot 3 would have needed four people. A built dome still cannot change its *room*. |
| ~~The colony can spend its starting metal and never make more~~ | ~~High~~ | **Resolved and measured at milestone 27.** Two changes: the start state carries **60 Ore, 75 Metal, 45 Bioplastic**, and only pressurised structures cost Bioplastic ([§9.3](#93-build-flow)) — the old catalogue priced everything in both, so the colony's 30 Bioplastic ran out four buildings in and the only thing that makes more is behind two domes that cost it. A panel, an extractor and a small Factory now cost 57 Metal of the 75, and `tools/balance.py` measures the chain running: **60 Ore → 30 Metal by sol 4, 18 → 48**, which buys the 30-Metal mine that keeps the Factory fed ([§10.1](#101-start-state)). The opening is no longer the whole game's budget. |
| **A new dome joins at most four domes** (milestone 85) | Low | The player asked for *every* dome near it; the ghost's undo log holds an L dome's frame and four corridors of 13 marks (1,016 of 1,160 bytes), and a fifth would not fit. Five domes within 12 tiles of a new one, all routable and not crossing, is rare, and the `ΔΙΑΔΡΟΜΟΣ` button joins the rest. Lifting it costs 156 bytes of bank 2 per corridor. |
| **A cursor step near buildings costs 7–15 ms more** (milestone 85) — **a quarter less since milestone 107** | Medium | The check of [§9.3](#every-building-needs-a-neighbour-at-milestone-85) runs on every step. A solar beside the colony stepped in 40–46 ms instead of 31 when the camera does not scroll. Milestone 86 took some back: a dome with no corridor no longer looks for a path, and a structure walks only the structure table ([§9.3](#airlocks-are-the-doors-at-milestone-86)). Milestone 107 measured the whole step in the game, not only the check ([§9.3](#a-cursor-step-near-the-colony-at-milestone-107)). A dome S beside the colony was 43.8 ms of work, of which ~17 was the panel redrawing all eighty cells for two digits of the corridors' cost; it is now **31.7**, with rows 3–4 cached. A Solar was 23.0 and is now **19.7**: the ghost's columns and the L's walk got cheaper. What is left: the ghost, ~8–11 ms a step for the undo and the new frame — its two 1-byte sides are most of its lines, ~21 µs each; the panel's text, ~3.5 ms whenever its signature changes; the L's walk, ~100 µs a tile; and the corridors' route for a dome, 0–6 ms. |
| ~~**Nobody at the ship is drawn** (milestone 87)~~ | ~~Medium~~ | **Resolved at milestone 89.** Everyone outside is drawn: standing at the ship or a structure in their slot's place beside it, walking on the line between two nodes' front points, one step per movement update ([§6.3](#seen-outside-at-milestone-89), [§8.4](#colonists-outside-at-milestone-89)). The first screen shows the four beside the ship, and a solar panel's carriers are seen going and coming. In the tube, nothing is drawn, as before. |
| **A step outside costs 2.3 ms of the frame's 20** (milestone 89; 5 until 105, 4 until 106) | Medium | An outdoor walker on screen redraws its old cell and draws its new one about three times a second ([§8.5](#85-the-dirty-list)): measured 2.3 ms a step in open ground and 3.0 beside a building since milestone 106, charged about 3.2 and 3.8. Twenty walkers in view are about 140 ms a second of rendering, a seventh of the machine (a quarter until milestone 105). Milestone 105 took the cheaper erase this row asked for ([§8.5](#a-cheaper-erase-at-milestone-105)), about 1 ms a step. Milestone 106 gave the cell its own way — the clip set directly, the 3×3 read straight from the world, the figures found with `cpir` and drawn without `ob_fig`, one charge, and `fg_want` unrolled ([§8.5](#the-cells-own-way-at-milestone-106)) — another 1.5 ms. What is left is `fg_want` (~420 µs, paid by every walker outside on every step, in view or not), the tile and the figure themselves (~500), and the list's bookkeeping. Beside a building the erase still goes through the object pass and `fg_draw`. |
| **The ring can overflow with more than ~60 walkers in view** (milestone 89) | Low | Each agent is at most once in the 32-entry dirty ring (the mark of [§8.5](#85-the-dirty-list)), and the list drains ~4 steps a frame on screen against ≤ 12 pushed per movement frame. Past ~64 walkers on screen per revolution the ring fills, and an overflow is a full redraw — which rebuilds the list and clears every mark, so it is correct, only slow. |
| **Who does not fit is not drawn** (milestone 89) | Low | 64 figures outside (`FG_CAP`): the 65th is not drawn until a full redraw finds room. A ninth at a structure (`NO_SLOT`) is not drawn, as in a dome. |
| **Walkers cross buildings** (milestone 89) | Low | A walker goes in a straight line between front points, over whatever stands between — a dome, a corridor, a panel — and is drawn on top of it, since the list is drawn last. Movement has never had geometry ([§6.3](#63-movement)); this only makes it visible. |
| ~~**A figure whose second byte crosses a screen page costs more than it is charged** (milestone 89)~~ | ~~Low~~ | **It never happens, as milestone 105 found** ([§8.5](#a-cheaper-erase-at-milestone-105)): a figure outside is at an even `x` and `cam_p` is a multiple of 4, so its first byte is never `&FF`, and `ob_fig`'s check for it is never true. Since milestone 106 the erase and the paint of a cell do not go through `ob_fig` at all (`fg_cell`). |
| ~~A meteor's site keeps two kinds of people inside~~ (milestone 90) | ~~Medium~~ | **Resolved at milestone 104, and one of the two kinds never existed.** A meteor never knocks a dome back: since milestone 38 it stops one of the dome's machines, and this row was wrong about that. The other kind was real. Someone in the tube from a dome when the airlock became a site arrived there with `F_INDOORS`. `lk_air_out` now puts them outside at the impact, with a full suit, and the arrival is unchanged ([§6.2](#who-was-in-the-tube-at-milestone-104)). |
| **No airlock in reach repeats the search** (milestone 90) | Low | A colonist at a minute with no airlock to walk to asks `su_lock` again every 128 frames, 451 µs a time. Bounded by the eight colonists a needs slot visits: 3.6 ms on that slot if all eight are outside, low and cut off at once, with their phase bits aligned. In play it is the start (four, 1.8 ms) before the first airlock. A count of active airlocks, kept where they are built and destroyed, would make it one read. |
| ~~Colonist ships bring robots~~ | ~~Medium~~ | **Resolved at milestone 91** — this row was left open then. A newborn's role was its agent slot's id & 7 (`sh_born`), three in eight bots; since 91 the player sets the shares and ships bring none ([§6.11](#who-comes-at-milestone-91)). And bots *did* breathe, eat and sleep, whatever this row said, until milestone 92 ([§6.6](#66-needs)). |
| **Bots work only when there is something to build** (milestone 92) — **drillers since 94, carriers since 95** | Low | Since milestone 94 the mine needs someone and driller bots are made for it ([§6.7](#drilling-at-milestone-94)); since 95 carrier bots haul its Ore ([§6.7](#hauling-at-milestone-95)), and constructor bots still have only Build. Until then: constructor and carrier bots take Build and Supply; Haul and Drill have no publisher, and the mine needs nobody. Between buildings the bots stand in the factory, on its ring. Drillers, and a mine that needs them, are a later milestone. |
| **Code in bank 6 runs only from the wheel** (milestone 92) | Low | `b6code` is reachable only while bank 6 is in the window; a call from the renderer or the UI, or a callee that leaves another bank in, runs whatever is there. Since milestone 93 it holds the bots, the ships and the sol's reckoning, the specialties' count, and slot 12 — reached from `econ_events` and the wheel's table — 1,219 of 1,280 ([§4.2](#code-in-bank-6-at-milestone-92)). |
| **Code in bank 1 runs only with bank 1 in the window** (milestone 94) | Low | `b1code` holds the placement ([§4.2](#code-in-bank-1-at-milestone-94)): a call to it with another bank in, or a callee that returns with another, runs whatever is there. Every caller is the UI, which runs in the default configuration, and every callee was read for its exit. 25 of its 160 are left. |
| **People dig in stretches, and the count is read once a cycle** (milestone 94) | Low | A colonist at a mine goes back when the suit says so ([§6.6](#suits-at-milestone-90)), and the mine makes Ore by how many are there at the moment of the flow cycle, every 64 revolutions — a sample, not an integral. Over many cycles it is the same; on one it can miss or catch a short visit. Driller bots stay. |
| **The ground link is an L; the walkers walk straight** (milestone 94) | Low | As with the structures' paths since milestone 85: the drawn path goes along x then y, the colonists cut the corner, over whatever is there ([§6.3](#63-movement)). Rock, water and buildings on the way are not floored, so a long link shows gaps. |
| ~~Trade is delivered instantly~~ (milestone 93) | ~~Low~~ | **Resolved at milestone 98.** Colonists and carrier bots carry the goods both ways, as in Planetbase: what you give leaves at `FIRE`, what you take enters the stocks a load at a time, and the merchant leaves when nothing is left on either side ([§6.11](#carried-at-milestone-98)). |
| **A merchant whose goods nobody carries waits for ever** (milestone 98) | Low | Since milestone 98 a merchant leaves only when its goods are carried; its `EC_SHETA` is `#FFFF`, 4,096 sols. While it waits no other ship comes, colonists' or visitors'. A deal needs a free job and a standing pad, and anyone can take the jobs, so the case left is a colony with no one alive to carry — which has already lost. A pad knocked down meanwhile only holds the carriers where they are until it is rebuilt ([§6.11](#carried-at-milestone-98)). |
| ~~A demolished structure's path stays, and blocks the ground~~ (milestone 101) | ~~Medium~~ | **Built at milestone 102** ([§9.3](#paths-that-go-at-milestone-102)): each structure keeps where its link goes and the L its path took (`LK_OWN`), demolition clears the path bit on its own path and on every path that ended at it, and what hung from it hangs from its parent with a ground link. The tiles stay foundation, and build again. |
| **A carrier's load is lost when its store is demolished** (milestone 101) | Low | A Haul or a Supply whose store goes is put back as a dropped job is, and its carrier lets it go: a Haul's 10 Ore in hand, already off the mine's pile, go nowhere. So do they when the mine itself goes. A Supply's load was paid at placement, so nothing is lost there. The player sees the store go, not the load. |
| **The demolition's code lives in the routing matrix's holes** (milestone 101) | Low | 1,086 bytes in bank 1's columns 96–127 (901 until milestone 102), copied into `GH_BUF` to run with the ghost hidden; the first 32 run in place as two dirty-list handlers ([§4.2](#code-in-the-routing-matrixs-holes-at-milestone-101)). A routine that wrote all 128 columns again would erase it, and code added to it must not page bank 1 out under row 0's handlers. `tests/test_demolish.py` reads the holes back, and `tests/test_routing.py` checks the rebuild leaves them alone. Since milestone 102 it comes in at `OV_LOAD`, under the icons, and may take the whole ghost log; 25 bytes are left ([§4.2](#and-milestone-102-moved-where-it-comes-in)). Since milestone 103 the save and the disc's driver are a second overlay in the rows after it, 630 bytes, copied to `GH_BUF + 512` on every `S` and `L` ([§11](#where-the-code-is-since-milestone-103)); `tests/test_save.py` saves with `rst 0` written over them first, and `tests/test_disc.py` reads both back after a boot from the disc. |
| **A dome still being built loses its way when its airlock is demolished** (milestone 102) | Low | A dome's ground link goes to the nearest airlock or the ship, and it is the dome's only edge until it is finished: its corridors become edges then ([§6.9](#69-construction)). Demolish that airlock and the site has no edge, and nobody reaches it to build it. Structures hang from the demolished one's parent since milestone 102 ([§9.3](#paths-that-go-at-milestone-102)); a dome keeps no byte, so it is not among them. Demolishing the site gives everything back. The way out: relink a site left with no edge, which the first version did, at 3.7 ms a demolition for the pass over the 64 domes. |
| **What hung from a building with no parent stays without a link** (milestone 102) | Low | When the demolished structure hung from nothing — the test colony's airlock, whose links `src/colony.asm` makes by hand, or any structure of a save from before milestone 102 — or its parent has eight edges, what hung from it is left as at milestone 101. The nearest airlock would be the fallback, and it needs the whole tree walked to avoid the orphans' own children ([§9.3](#paths-that-go-at-milestone-102)): about 40 bytes. |
| **Two colonists walking over each other are drawn in another order for a few frames** (found at milestone 102) | Low | A moment after a demolition sends people walking, two or three of them leave by the same edge and overlap. Their step redraws the outdoor figures in the list's order (`fg_draw`), a full redraw in the object pass's, and 9 to 26 bytes in one or two tiles differ until they part; at milestone 102 it was seen at the test colony's airlock door, and at 101 the same moment gave the same bytes. Milestone 103 found the cause, and not a cure: it is cosmetic and goes by itself. `tests/test_unlink.py` looks again, up to five times two seconds apart, before it fails a screen; a leg that was not drawn fails all five. |
| **25 bytes left for the demolition, 18 for the save, and none in the text block** (milestone 101; 3 until 102; the save's since 103) | Low | The overlay may grow to the end of the ghost log, `&9C00`, since milestone 102 brought its image in at `OV_LOAD` instead of under the test colony ([§4.2](#and-milestone-102-moved-where-it-comes-in)); so may the save's, which starts after its 512-byte header ([§4.2](#memory-again-at-milestone-103)). Past that, a third overlay or code that runs in the holes themselves; the two images take 1,718 of `OV_LOAD`'s 2,048. Bank 7's text block is full (2,138 of 2,138), and the bank has 5 bytes: the next words need bytes from the font or the symbols. |
| **Corridors straddle tiles** (milestone 96) | Low | A centred axis corridor is a byte or four lines off the half-tile grid of [§3.3](#33-the-grid-is-not-a-choice), so where a dome's axis falls on a tile boundary it touches two columns or two rows of tiles. `cr_stampx` stamps the extra tile when it is free, so a crater or a figure outside redraws it with the objects, and nothing can be built on it or route through it; a tile that is already a path stays a path, and a figure walking on it would paint the terrain over the corridor's strip. Colonies saved before milestone 96 have no such stamps. Anything new that redraws by tile and trusts the grid has to take the extra column or row, as `crr_half` does ([§8.4](#centred-and-joined-to-the-ring-at-milestone-96)). |
| **A corridor shows over the ring for a moment** (milestone 96) | Low | The corridors are under the shells, and a new corridor's diagonal rows are redrawn without the terrain (`DK_CROW`), so between a row and the shell over it the corridor shows where the ring already was. 9 bytes in `tests/test_link.py`'s worst frame, against 18 at milestone 95 (limit 24). |
| ~~A joint is computed for a lone corridor~~ (milestone 96) | ~~Low~~ | **Resolved at milestone 97.** Measured on every route up to 12 tiles: the one geometry the fixed joints miss is the short bend, one horizontal tile after the diagonal — one pixel, always at the same place in the frame, now drawn from a flag per dome ([§8.4](#the-short-bends-at-milestone-97)). |
| **Renderer code in `b6code`** (milestone 96) | Low | `src/joint.asm` runs only with bank 6 in the window, and the only thing it calls that pages, `ob_put_in`, puts it back. A caller that reaches `jt_one` with another bank in would jump into data. The three callers are `ob_corr`, `ob_fittings` and `dt_prep`. |
| **Renderer code in bank 5** (milestone 97) | Low | `src/bend.asm` runs with bank 5 in the window and is entered only through `jt_b5`, which returns with bank 6, and `jt_b5c`, which returns through the routine in DE; nothing in it pages. A call that reached it otherwise would run machine sprites ([§4.2](#code-in-bank-5-at-milestone-97)). |
| **A switch written as code** (milestone 97) | Low | `jtd_end`'s first byte is `ret` or `ld hl,jtb_dome`, written by `jt_clear` and `jtm_bend`. Left on in a colony with no short bend it costs about 43 µs a dome with joints; left off with one, the pixel is missing. Only the corridors' index writes it, and `tests/test_oibuild.py` checks it after every build of that index ([§8.4](#the-short-bends-at-milestone-97)). |
| **A mine's pile sees the last balance's power** (milestone 95) | Low | `hl_pile` runs in the flow balance's scan, before this cycle's verdict, and reads the previous one, as slot 11's machines and gardens do ([§6.7](#hauling-at-milestone-95)): a mine goes on one cycle into a blackout and starts one cycle after the power is back. The cycle's own verdict needed a second search of the 32 structures, up to ~400 µs. |
| **One carrier per mine at a time** (milestone 95) | Low | One Haul per pile (bit 6), so a mine is emptied 10 at a time by one agent. Three drillers make 4 a cycle; a trip that takes longer than two and a half cycles, to a far store or ship, lets the pile reach 30 and the mine stop, as the player chose, however many idle workers there are. |
| **A load with nowhere to go is delivered at the mine** (milestone 95) | Low | With no Storage dome in use and no ship that the mine's node can reach, the 10 Ore go into the stocks where they were loaded, as a Supply with no source counts its load as in hand. It takes a mine whose node reaches neither a store nor the ship, which a new game always has; in Planetbase the Ore would wait. |
| **Haul outranks Drill** (milestone 95) | Low | Priority 5 to Drill's 4, my choice and not the player's ([§6.7](#hauling-at-milestone-95)): with Drill above it, few workers would all dig and the full pile would stop the mine for good. A colony with one worker now carries before it digs. |
| **A merchant holds the only ship for half a sol** (milestone 93) | Low | One ship at a time ([§6.11](#611-ships-and-arrivals)): while a merchant is here no visitor comes, and `C` says `A SHIP IS ALREADY DUE` for up to two minutes at ×1. Trading sends it away at once. |
| **The suit's unit is two visits, so its clock is the wheel's** | Low | 128 frames a unit at any speed of the wheel, because both decrements and visits are per wheel tick: at ×4 a trip still lasts 70 units of game time. If a slot is ever skipped or doubled (the wheel's order, [§7.2](#72-the-wheel)), the suits follow it, and `tests/test_suit.py`'s rate check (one unit per 128 frames to within two over fifty) is what would see it. |
| **A full job board drops a site's jobs** (milestone 88) | Low | `jb_post_build` and `sp_post` write into the first free entry and post nothing when there is none — a site placed then gets no Supply, or a supplied site no Build, and waits for ever. That was true of the Build job since it existed; with two Supply jobs a site, sixteen sites placed at once fill the 32 entries before anyone is assigned. Nothing re-posts: a scan of the sites for one with loads owed and no job would cost the job board's slot every visit. If it is ever seen, the cure is in `jp_one`, which already visits four domes a visit — not structures. Since milestone 99 the same holds for a machine fitted with the board full: no Supply, or no Build once its materials are in, and it waits stopped ([§6.9](#machines-carried-at-milestone-99)). |
| **The first building of an empty world has no edge** (milestone 85) — **closed at milestone 87** | Low | Whatever is placed without a path gets a ground link to the nearest ship or airlock, and the ship is always there ([§6.2](#inside-and-outside--milestone-87)). What is left: an anchor with all eight edges taken is passed over, and with every door full a site would be unreachable — eight sites waiting on one airlock first. Until 87: nothing is near it, so nothing joins it, and its Build job is unreachable — the bug of milestone 26 in a new place. The start colony of [§10.1](#101-start-state) means it cannot happen yet; milestone 87 starts with no buildings and the colonists beside their ship, and must give the first building a way to be reached — and since milestone 86 an airlock or a dome can also stand alone while nothing of its kind exists ([§9.3](#airlocks-are-the-doors-at-milestone-86)). The start colony's landing pad also keeps its old edge to dome 2 with no path drawn: a door into a dome that the rule of milestone 86 would not build. |
| **Corridors eat the opening's metal** (milestones 85–86) | Medium | A dome costs 12 Metal and 6 for each corridor piece, and since milestone 86 it cannot do without a corridor. The 75 Metal of [§10.1](#101-start-state) was measured to buy a panel, a pump and a small Factory at 57; with two to four corridor pieces the Factory alone is 32–44, and `tests/test_game.py` had to be given Metal for the Control room it used to afford. The balance table of §10.1 was not re-run. Milestone 87 replaces the start state and should set the stocks against the new prices. |
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
| load / `SP_PRIO` | 10 units / 4 | one trip of a Supply job, rounded up per material; its priority, under Build's 5 (milestone 88) |
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
| `WH_RT_B` | 15 | routing node expansions per frame ([§7.2](#72-the-wheel)); 12 until milestone 63 |
| `NO_EDGE` / `NO_SLOT` | 255 | "not in transit" / "holds no ring slot" |
| `RT_UNREACH` | 255 | no route. There is no distance ceiling since milestone 62: the longest path is 127 hops |
| `R_PLATEAU` / `R_BLEND` / `R_RIM` | 5 / 10 / 57 | generator shaping radii |
| `ANCHORS` | 6 | feature anchors per world |
| `SOL_FRAMES` | 12,000 | 4 minutes |
| `FRAME_US` | 19,968 | the budget everything is measured against |
| `AL_RANGE` / `AL_MAX` | 12 / 4 | how near a building must be, and how many corridors a new dome gets ([§9.3](#every-building-needs-a-neighbour-at-milestone-85)) |
| `CORR_M` / `CORR_B` | 6 / 3 | Metal / Bioplastic per corridor piece, the catalogue's price, also for automatic corridors |
| `W_OCC_PATH` | `&20` | occupancy 2: a path on the ground |

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
