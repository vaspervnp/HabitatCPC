# Habitat

A colony-survival game for the **Amstrad CPC 6128** — 128 KB, Mode 0, disc.

You drop a construction pod on an unnamed world and place what the colony needs.
You never give an order. Colonists walk out, take jobs from whatever you built, and
either keep the oxygen running or do not.

Systems are modelled on *Planetbase* (Madruga Works, 2015), cut down until they fit
in a Z80 and 128 KB.

> **Status: it runs.** `RUN"HABITAT` on a 6128 generates a world, builds the starting
> colony and hands it over; the player builds, the colonists work, `S` / `L` save
> and load the game, and it makes noises at you. Left: music, a slot picker, tuning.
> Build it with `tools/build.sh` — that also runs every test — and read
> [`DESIGN.md`](DESIGN.md) first.

---

## The shape of it

| | |
|---|---|
| World | 128 × 128 tiles, procedurally generated, origin `(0,0)` at the centre |
| Seed | 16-bit, four hex digits — the same seed always builds the same world |
| Colony | up to 80 colonists and 16 bots, all autonomous |
| View | 20 × 10 tiles of the world at a time, hardware-scrolled |
| Memory | all eight 16 KB banks used: world, routing tables, sprites, two screen pages |

Two decisions shape everything else:

- **The world is a pure function of its seed.** Terrain is generated once, into a
  dedicated 16 KB bank, by a program that is loaded, run and then overwritten by the
  game itself. Saves keep the whole 16 KB rather than the seed: regenerating costs
  13.5 seconds and reading it back costs one.
- **Nothing runs all at once.** Agents, production, routing, rendering and even world
  generation are sliced across a 16-frame wheel with a fixed per-frame budget. The
  simulation is allowed to think more slowly as the colony grows; the frame rate is
  not allowed to drop.

---

## Repository

```
DESIGN.md           the design document — start here
README.md           this file
sync-assets.sh      pulls the graphics from the CPCArt repo
assets/             Mode 0 graphics, generated — do not edit by hand
  SPRITES.md        every sprite, its pointer, and how a dome is composed
  sprites.asm       RASM source to include
  sprites.bin       the same bytes as raw binary
  sprites_map.txt   offset and size of every sprite
  aseprite/         the source spritemaps and their exports
  preview/          sheet.png and assembled dome composites
```

Nothing in `assets/` is edited here. It is generated in the [`CPCArt`](../CPCArt)
repo and copied in:

```bash
./sync-assets.sh --regen
```

---

## Building (once there is something to build)

| Tool | Path | Role |
|---|---|---|
| `rasm` | `~/rasm/rasm.exe` | assembler |
| `iDSK` | `~/idsk/iDSK` | builds the `.dsk` image |
| `cpcemu` | `~/cpcemu/cpc.py` | headless CPC 6128 emulator, renders to PNG |

The emulator is headless and scriptable, which is what makes the test plan in
[`DESIGN.md` §13](DESIGN.md#13-build-and-test) real — including generating a seed
twice from cold boot and asserting the two 16 KB worlds are byte-identical, and
sweeping thousands of seeds to prove every one of them is playable.

---

## Before writing code

Three things in [`DESIGN.md`](DESIGN.md) will save the most time:

1. **[§2.2 The frame budget](DESIGN.md#22-the-frame-budget)** — drawing one large dome
   costs almost six frames. Every other decision in the design follows from that.
2. **[§4 The memory map](DESIGN.md#4-memory-map--all-128-kb)** — all eight banks are
   spoken for, with under 1.5 KB of slack.
3. **[§15 Open risks](DESIGN.md#15-open-risks)** — the CRTC offset scroll with a
   two-page raster split is the least certain claim in the document. Prove it at
   milestone 5, before anything is built on top of it.

There are also eight outstanding art requests in
[§12 Asset gaps](DESIGN.md#12-asset-gaps). The first four are blocking — most
importantly, **there are no terrain tiles yet**, and the sprite build must be pinned to
`--quads nw` or it will not fit in memory.
