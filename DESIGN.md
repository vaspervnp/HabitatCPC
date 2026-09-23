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
| One terrain tile | 64 opaque | **958 µs measured** | 0.048 |
| One viewport column (10 tiles) | 640 | **9,580 µs** | 0.48 |
| One viewport row (20 tiles) | 1,280 | **19,160 µs** | 0.96 |
| Full play area (200 tiles) | 12,800 | **191,600 µs** | **9.6** |
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
| `&0000–&3FFF` | 0 | engine code, ISR, blit kernels, UI | 16,384 | **2,108** |
| window | 1 | **distance matrix** `DIST[96][128]` 12,288 · room icons `m` and `l` 3,936 | 16,384 | 160 |
| window | 4 | **world plane** 128×128×1 byte | 16,384 | 0 |
| window | 5 | **next-hop matrix** `NEXTHOP[96][128]` | 16,384 | 4,096 |
| window | 6 | `flip_mode0` 256 · dome+ring `nw` quadrants 7,424 · slot figures 3,456 · entity tables 4,832 ([§6.1](#61-entities)) | 16,096 | 288 |
| window | 7 | external structures 11,264 · plants 1,584 · `plant_ptr` 24 · text 1,024 · audio 2,048 | 15,944 | 440 |
| `&8000–&BFFF` | 2 | graphics, flat · node graph + BFS workspace 1,536 · recipes 110 · economy 58 · job board 160 | 14,848 | **1,536** |
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
  `route.asm`, the ghost's 1,600-byte undo log and the 512-byte figure table live
  above it.

The result was 2,108 free in bank 0 and 708 in bank 2 — about 2.8 KB for save/load,
audio, meteors and intruders, with bank 7's reserved 1,024-byte `text` block
untouched behind it. `tests/test_game.py` builds the whole thing, so the number
cannot drift back without a test failing to assemble.

**Save and load spent 842 of it** (`fdc.asm`, `save.asm`, and the two keys in the
UI), and the ceiling turned out to be lower than `&4000`: the loader leaves its
endgame at `&3E00` and copies it there *after* the game is in memory
([§13.1](#131-three-ways-a-loader-does-not-run)), so bank-0 code must stop below
that. **649 bytes left**, checked by `tools/mkdsk.py` on every build — the failure
mode otherwise is a machine that loads perfectly and hangs, with nothing in the
build to point at.

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
| 4×8 font, 96 glyphs | 1,536 |
| Asset tables, `room_machines` included | 313 |
| Generated pointer tables (`tile_ptr`, `icon_{s,m,l}_ptr`, `mach_ptr`, `struct_ptr`) | 176 |
| Cursor and UI chrome (reserve) | 256 |
| Node graph (`node_deg`, `node_adj`) and BFS workspace | 1,536 |
| Machine recipes (12 × 10) + the "needs an operator" lookup | 132 |
| Economy state — stocks, flows, clock, weather, ships, milestones | 82 |
| Job board 160 · room index 108 | 268 |
| **Total** | **15,163** of 16,384 — **1,024 free, contiguous** |

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

13.5 s is tolerable for a new game. **It is not tolerable on load** — see
[§5.10](#510-player-modification).

The generator was going to run in slices behind a `GENERATING` progress bar. It
does not. It runs in one blocking call from the loader, before the game's own code
exists, with the **border colour** as the only feedback — BASIC's text is still on
the screen at that point, because the loader never touches the screen page and the
firmware's palette is still in force. A progress bar would need the game's tile
pass, its palette and its font, all of which arrive after the world does. The slice
structure is still in the generator and costs nothing; nothing calls it that way
yet.

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

   **As built it is a full redraw: 41 frames, 0.8 s, once per building.** The
   eight-chunk reveal is not written. The dirty list is *not* cheaper here — a
   single tile under a dome costs 99,840 µs and a small dome has sixteen — so the
   choice was between one stall and a worse one. It is the right place for the
   chunked reveal when someone writes it.

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

**Trade is a player action, not a wheel pass.** The mechanism lives here; the button
that calls it belongs in [§9](#9-interface). Trading sets a flag that breaks the
no-trade streak, which is the whole reason Independence in
[§10.2](#102-milestones) is hard to keep rather than hard to reach.

Merchants and colonist ships must be **called**; visitors arrive on their own roll.

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
| 11 | Production, machines and plants | 16 domes | 4,000 µs | **5,691 µs** ❌ 1.4× |
| 12 | Flow balance | 64 structures, plus counting the living | 2,000 µs | **7,887 µs** ❌ 3.9× |
| 13 | Job board — reap, arrive, post, assign | 4 domes, 32 agents | 3,000 µs | **4,692 µs** ❌ 1.6× |
| 14 | Room index, amenity, pad, population cap | 64 domes | *(was empty)* | **7,188 µs** |
| 15 | Events, ships, and the milestone check once a sol | three rolls | 500 µs | **499 µs** ✅ |
| — | wheel dispatch itself | every frame | — | **94 µs** |

**A whole revolution costs 73,400 µs spread over 16 frames — under a quarter of the
machine — and the worst single frame is 7,887 µs, 40 % of one.** That is the number the
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

The worst *frame* is a flow-balance slot during a routing rebuild: 7,887 + 2,700 + 94
≈ **10,700 µs, just over half the frame**. That leaves 9,300 µs for rendering — and a
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
| Terrain strip alone (one column) | 0.48 |
| Terrain strip alone (one row) | 0.96 |
| **Whole step, open ground** | **3.0 – 3.2** |
| **Whole step, through the middle of the base** | **4.2 – 8.8** |
| HUD re-render, on top of any of the above | **2.55** |

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
  reversing 16 pairs to write 4.

`tests/test_scroll.py` proves the result by **equivalence**: start five tiles
back, draw fully, scroll five times, and the screen memory must be identical to a
full draw at the destination — in all four directions.

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

| | µs per tile |
|---|---|
| `blit_tile` plus the column loop | 579 |
| class, variant, autotile, ore overlay | 350 |
| the camera: display offset and ring masking ([§8.2](#82-camera)) | 29 |
| **total** | **958** |

A scroll step costs one column of *terrain* — 0.48 frames — and that part is
comfortable. It is not the whole step ([§8.2](#82-camera)). A full redraw is 9.6
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

### 8.5 The dirty list

After the initial draw, **nothing is redrawn unless it changed.** A 32-entry ring of
`(kind, id)` records what changed; the renderer knows the minimal redraw for each kind,
straight out of `assets/SPRITES.md` §8:

| Change | Redraw | Estimated | **Measured** |
|---|---|---|---|
| Colonist enters or leaves a slot | one slot | 64 µs | **1,498 µs** |
| Machine changes state or breaks | one machine | 530 µs | **4,992 µs** |
| Plant grows a stage | one plant | 530 µs | **4,992 µs** |
| Room type changes | one icon | ≈ 800 µs | **1,997 µs** |
| Corridor added | one connector | ≈ 450 µs | **2,995 µs** |
| Terrain tile changes, open ground | 3×3 tiles | ≈ 1,600 µs | **9,984 µs** |
| Terrain tile changes, under a dome | 3×3 tiles + every object over them | — | **109,824 µs** |
| Dome built | everything, sliced over 8 frames | 1.4 – 5.7 frames | not built — [§6.9](#69-construction) |

**The figure cache is rebuilt from the agents, once per burst of pushes.**
`dome_fig` is what tells the slot redraw which figure belongs where, and when the
simulation moves colonists it is stale — the figure would be drawn back where it
left and never appear where it went. The rebuild walks all 128 agents and costs a
**measured 9,984 µs, half a frame**, so it runs only when a `DK_SLOT` has been
pushed since the last tick, not on every tick. The per-item budget below does not
include it; a frame that redraws a slot can therefore overrun by half a frame,
once.

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

If the 32-entry ring fills, nothing is discarded: an **overflow flag** is raised
and the caller owes a full redraw. A dropped change leaves a lie on the screen
for ever; a full redraw only costs.

`tests/test_dirty.py` checks the list by **equivalence** — the same mutation
applied once through the list and once by redrawing everything must leave
identical screen memory — plus a second check that the mutation changes the
picture at all, because two paths that both do nothing agree perfectly. That is
how it found the real defect: the **empty figure variant was never drawn**.
Skipping it is right in a full redraw, where the ring has just been painted
underneath; in the dirty list it meant a colonist who walked out stayed drawn in
a dome he had left.

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
to pan and build is a chore. **Built**, as the table says; every action has a key *and*
a joystick alternative, read in one pass over the PSG keyboard matrix.

| Input | Action |
|---|---|
| Cursors / joystick | move the build cursor; camera follows at the viewport edge |
| Fire / `COPY` | select, confirm, place |
| `ESC` | cancel, back |
| `SPACE` | open the build menu |
| `1`…`4` | speed: pause, normal, fast, very fast (wheel advances 0 / 1 / 2 / 4 slots per frame) — **bound, not yet acted on**: the keys reach `act_hit` and nothing reads them |
| `TAB` | cycle alerts — jump the camera to the next problem |
| `H` | centre on `(0,0)` |
| `S` / `L` | save to disc, load from disc ([§11](#11-save-and-load)) — only from `LOOK` |

`TAB` matters more than it looks. In a base that is 6 viewports wide, the thing that is
killing you is usually off-screen.

**Buttons are read on the edge, the cursor on the level, and that distinction was
not a style choice.** A `ui_tick` lasts one frame when nothing moves and **3 to 9**
when the camera scrolls ([§8.2](#82-camera)); a keypress shorter than the tick is
invisible to an edge test. The test held a direction for twelve ticks and got
eleven moves. Level-triggered movement also gives auto-repeat for free, at the
rate of the tick — which is the rate the screen can actually keep up with.

**A cursor step costs 16,224 µs — 0.81 frames — and half of that used to be the
HUD.** `ui_panel` rewrote rows 3–4 on every step for eighty cells that almost
always said the same thing; guarding it with a six-byte signature (state,
selection, validity, link anchor, run count, affordability) took the step from
29,952 µs to 16,224. With a corridor ghost on screen it is 39,936 µs. Asserted by
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
`NO POWER`, `NO OXYGEN`, `SANDSTORM`, `COLONY LOST`, `ALL SYSTEMS OK` — because
naming the machine needs the selection the build mode has not built yet.

Checked byte-for-byte against `tools/hudref.py` in two states, the second chosen
because the first exercised neither leading-zero suppression nor the alert line.
And checked at the **boundary**: the play area is filled with a marker, the world
is drawn without the HUD, and the marker must survive — opening the clip to line
200 puts 1,886 bytes of dome into the numbers.

Cost: **2.55 frames**, paid after every camera step ([§8.1](#81-screen-layout)).

### 9.3 Build flow

`SPACE` → item → a ghost follows the cursor, snapped to the correct parity
([§3.4](#34-anchors-are-centres)), with invalid footprint tiles tinted. Fire commits,
`ESC` backs out. A dome's room type is chosen immediately after placement, and can be
changed later at a cost.

**The menu is flat, not `category → item → size`.** Eleven things — three dome
sizes, corridor, four energy structures, mine, airlock, landing pad — fit on one
40-column row with their costs, and left/right cycles them. The tree cost three
presses where the list costs one, and its only advantage appears at about thirty
items, which is where it should come back.

**The ghost keeps an undo log, and that is why the cursor is cheap.** Every line
it writes is recorded with the bytes it covered, and hiding it writes them back —
so a cursor step costs a box, not a redraw. The log is 1,600 bytes and the drawing
refuses to write anything it cannot take back, so a very long corridor preview
truncates rather than corrupting.

**The order inside one step is binding: hide → move → scroll → show.** Undo-log
addresses are positions in the 2 KB ring ([§8.2](#82-camera)); once the ring has
rotated under them they name different pixels. Hiding after the scroll leaves a
trail that never goes away.

Three states, not four: `LOOK`, `MENU`, `PLACE` — and `LINK`, which the corridor
needs because a corridor has two ends rather than a footprint
([§9.4](#94-corridor-routing)).

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

---

## 10. Progression

### 10.1 Start state

At `(0,0)`, on guaranteed flat foundation: a landing pad, one small **Oxygen** dome with
one `mach_oxygen`, one small **Quarters**, one small **Storage**, and the corridors
joining them. Four colonists: two workers, one engineer, one biologist. Starting stock:
60 Water, 40 Food, 30 Metal, 10 Bioplastic, 4 Spares.

Enough to live about two sols without doing anything, which is exactly how long it
should take to realise you need power before you need anything else.

**Written** (`src/newgame.asm`), with two departures from the paragraph above.
The three domes sit 8 tiles apart centre to centre, because that is the closest
spacing that leaves a whole number of corridor tiles between two small domes
([§9.4](#94-corridor-routing)); and **the pad is joined by an outdoor edge, not a
corridor**, because a corridor record can only name domes.

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
saves, `L` loads, both only from `LOOK`.

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
tracks 24, 30 and 36 — the disc holds 42. `sv_save` and `sv_load` take a slot number;
**the keyboard reaches slot 1 only**, because a slot picker is a screen and there is
no screen for it yet. They belong to no AMSDOS file: this is the
game's own disc, `tools/mkdsk.py` checks at build time that no file reaches track 24,
and a save that overwrote one would be silent otherwise.

The header is checked **before** a single byte of the game is overwritten. An empty
slot is `&E5` from end to end — perfectly valid bytes, an invalid game — and without
the magic, *load* on an untouched slot would fill the world with rubbish and hang the
simulation. `tests/test_save.py` loads from an empty slot on purpose and asserts that
nothing moves.

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
| `LOADER.BIN` | `&9000` | 342 | the loader |
| `BANK6.BIN` | bank 6 | 16,384 | quadrants, figures, entity tables |
| `BANK7.BIN` | bank 7 | 16,384 | structures, plants, text, audio |
| `BANK1.BIN` | `&7000` | 4,096 | room icons above the distance matrix |
| `PAGE2.BIN` | bank 5, then `&8000` | 11,264 | bank 2's graphics and tables |
| `GAME2.BIN` | bank 5, then `&B440` | 2,300 | bank 2's code |
| `GEN.BIN` | `&8000` | 3,072 | the world generator: runs once, returns |
| `GAME.BIN` | `&0100` | 14,125 | the game |

**Measured: 31 s from `ENTER` to the colony** — 13.5 s of that is the generator
([§5.9](#59-cost--measured)), the rest is 68 KB off the floppy. The border changes
colour at each file, which is the only progress indicator there can be while the
firmware still owns the screen.

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
| Object pass | independent Python renderer from the prose, compared byte-for-byte at five camera positions (`test_object.py`) |
| Scrolling | equivalence: scroll *k* steps and compare with a full draw at the destination (`test_scroll.py`) |
| HUD | content against a reference, boundary against a marker, cost against a limit (`test_hud.py`) |
| Dirty list | equivalence: the same mutation through the list and through a full redraw (`test_dirty.py`) — the mutation moves an **agent**, not the renderer's figure cache, because the cache is now rebuilt from the agents |
| Input | every action, keyboard and joystick, one edge per press (`test_input.py`) |
| Build mode | cursor, ghost-leaves-no-trace, validation, placement, payment (`test_build.py`) |
| Corridor routing | independent Python router compared on every pair of domes, then the *picture* compared at both kinds of bend (`test_route.py`) |
| The whole game | `src/main.asm` booted: start state, the economy moving inside the loop, a building placed and **finished**, and the HUD following it with no input (`test_game.py`) |
| The disc | `RUN"HABITAT` from a cold BASIC prompt: the game arrives, the start state is there, the HUD is drawn, and the world is **generated** rather than loaded (`test_disc.py`) |
| Disc driver | the μPD765 without AMSDOS: reads the disc's own **catalogue** and compares it with the host's `.dsk` byte for byte, then writes three sectors, reads them back, and checks the neighbouring sector is untouched (`test_fdc.py`) |
| Save and load | freeze the wheel, photograph the state, `S`, run 12,000 frames until it has moved, `L`, and assert the economy, the world plane and the **picture** are back — plus a load from an empty slot that must be refused (`test_save.py`) |
| Playability of every seed | headless run of N seeds, assert water and ore within 30 tiles of centre |

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
loaded into bank 5 first and copied down by an **endgame** — twenty bytes copied to
`&3E00` and entered with both ROMs off, because the copy passes over the loader
itself and over BASIC's stack. It takes its two lengths in `BC` and `IX` rather
than reading them from memory that is about to disappear.

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
milestone 10's delivery and save/load halves. What is left of it is audio, the four
planets, and tuning.

---

## 15. Open risks

| Risk | Severity | Mitigation |
|---|---|---|
| ~~CRTC offset scrolling with a two-page raster split~~ | ~~High~~ | **Resolved at milestone 5, and split in two.** Offset scrolling works to the pixel ([§8.2](#82-camera)). The mid-frame page change does **not** — the CRTC latches the start address once per frame — so the HUD moved into the play page and bank 2 went flat ([§8.1](#81-screen-layout), [§4.3](#43-bank-2-flat-again)). |
| ~~HUD re-render on every scroll step, ≈ 0.4 frames, estimated not measured~~ | ~~Medium~~ | **Measured: 2.55 frames**, six times the estimate ([§8.1](#81-screen-layout)). Not rupture — the escape hatch is to *move* the HUD block inside the ring (≈ 0.85 frames) instead of re-rendering it. Held in reserve. |
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
| ~~Ships, trade and milestones are unbuilt~~ | ~~Medium~~ | **Built**, except Automation, which waits on bot-eligible jobs ([§10.2](#102-milestones)). |
| ~~A heavy sim frame plus a scroll column comes to 19.9 ms of 20~~ | High | **Worse than that, and now measured.** A scroll step is 3.0–8.8 frames of world plus 2.55 of HUD ([§8.2](#82-camera)), so it was never going to fit in one frame and does not need to: the dirty list is a budget and the strip fills over several frames. What this costs is **latency, not frame rate** — about a quarter of a second per tile through a dense base. The flow-balance slot still wants the fix described below. |
| **The flow-balance wheel slot re-scans 64 structures every revolution** | Medium | 7,887 µs for numbers that change slowly. The fix is the one production already took: accumulate during a pass that walks the structures anyway ([§7.2](#72-the-wheel)). |
| ~~Nothing the player does exists: no build mode, no input, no HUD, nothing drawn since milestone 5~~ | ~~High~~ | **Resolved.** The colony is drawn, the camera scrolls, the dirty list keeps it honest, the HUD reports — and the player now moves a cursor, opens a menu, places a dome and routes a corridor between two of them ([§9.1](#91-controls), [§9.3](#93-build-flow), [§9.4](#94-corridor-routing), [§6.9](#69-construction)). |
| ~~The two halves have never been assembled into one binary~~ | ~~Medium~~ | **Assembled, and it did not fit: 20,571 bytes wanted 16,128.** Resolved by moving the generator out, cutting `MAX_NODES` to 96 and putting code in bank 2 ([§4.2](#42-the-eight-banks)). It also turned up duplicate constants in three files and, worse, [§7.4](#74-one-convention-per-half-and-they-disagreed)'s paging disagreement. |
| **Memory is the binding constraint from here on** | High | 2,108 bytes free in bank 0 and 708 in bank 2, for save/load, audio, meteors and intruders. The reserves left, in order: bank 7's `text` block (1,024, already allocated for exactly this), size-optimising `route.asm`/`ui.asm`/`object.asm` (1,000–1,500 by estimate), and the cuts [§4.2](#42-the-eight-banks) already names. Every new feature now costs a decision. |
| ~~Nothing finishes what the player starts~~ | ~~High~~ | **Built.** A Build job is picked up, the agent routes to the site, works it 32 points a visit, and at 255 the building turns `DS_ACTIVE` and is drawn ([§6.9](#69-construction)). `tests/test_game.py` walks the whole chain: place a solar panel with 30 Metal, and about six seconds later the HUD says `ALL SYSTEMS OK` with no key pressed in between. |
| **A completed building stalls the game for 0.8 s** | Medium | The full redraw of [§6.9](#69-construction) step 4, in place of the eight-chunk reveal that is specified and unwritten. Rare — once per building — but it is a visible freeze, and it is the first thing to fix if building ever becomes frequent. |
| ~~The simulation still pushes nothing into the dirty list~~ | ~~High~~ | **Wired for ring slots**, which is what moves: `ent_claim` and `ent_release` push a `DK_SLOT`, and the figure cache is rebuilt once per burst rather than once per slot ([§8.5](#85-the-dirty-list)). Machines breaking, plants growing and room changes still push nothing. |
| **A near-diagonal pair of domes cannot be connected** | Low | The turn in [§9.4](#94-corridor-routing) spends `\|S − T\|` tiles, so when the two axes differ by less than the destination's radius there is no route and the panel says so. The band is 2–4 tiles wide and the player can step out of it by moving the dome. Closing it needs a corner sprite the art does not have. |
| **The rest of the dirty-list call sites** | Low | A machine breaking, a machine repaired and a plant growing push nothing — **and would change no pixels if they did**: there is no damaged-machine variant ([ASSET-8](#12-asset-gaps)) and a plant's sprite is chosen by class, not by stage. Ring slots were the only change the picture can show, and they are wired. A colonist who dies releases a slot, so that path is covered; one who arrives by ship gets no ring slot until they move. Wire the rest when the art gives them something to draw. |
| **A vacated ring slot leaves 2–7 wrong bytes** | Medium | Redrawing an *empty* ring slot over a freshly drawn dome does not reproduce the full pass, for five of the eight slots. It is **not** the empty-slot art: replacing the redraw with "draw the whole dome clipped to the slot's 2×8 rectangle" — which by construction must match — gives the same wrong pixels, so the fault is in how the object pass clips to a window about two bytes wide at a sprite's left edge. `tests/test_object.py` passes at four bytes, which is why scrolling never showed it. Bounded and idempotent: `tests/test_game.py` asserts the whole-screen divergence stays ≤ 8 bytes. |
| **The base is invisible on its own foundation** | Medium | The foundation tile, the dome rings and the corridors are all the same grey. Outside the base everything reads; inside it, the colony disappears into the slab. Found by looking at the first running build, not by any check. It is a palette question for [§8.6](#86-palette) — one pen, differently chosen. |
| **Scrolling is 4 to 8 tiles per second through a built-up base** | Medium | 3.0–3.2 frames per tile in open ground, up to 8.8 in the base, plus 2.55 for the HUD. Playable, not smooth. Three levers, all untaken: move the HUD block instead of redrawing it ([§8.1](#81-screen-layout)), index which objects overlap which strip instead of testing all 224 records, and blit tile pairs ([§8.3](#83-the-tile-pass)). |
| **A broken machine is invisible on screen** ([ASSET-8](#12-asset-gaps)) | Medium | One sprite per machine, no damaged variant. The economy knows, the alert line knows, the picture does not — wrong way round for a game about watching a colony. 132 bytes per machine would fix it. |
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
