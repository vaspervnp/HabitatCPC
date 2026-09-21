#!/usr/bin/env python3
"""Γράφει το build/world_test.bin — ο συνθετικός κόσμος των δοκιμών.

ΔΕΝ είναι η γεννήτρια του DESIGN.md §5· αυτή έρχεται στο βήμα 4. Εδώ θέλουμε
απλώς ένα επίπεδο κόσμου που χτυπά κάθε περίπτωση του περάσματος εδάφους.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from world import test_world, SIZE, cls_of, CLASS_NAMES
from sprites import ROOT
import collections

p = test_world()
out = os.path.join(ROOT, "build", "world_test.bin")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "wb") as f:
    f.write(p.buf)
n = collections.Counter(cls_of(b) for b in p.buf)
print(f"{out}: {SIZE} bytes")
print("  " + "  ".join(f"{CLASS_NAMES[c]}={n[c]}" for c in sorted(n)))
