#!/usr/bin/env python3
"""ZX0 για τον δίσκο (βήμα 193, DESIGN §13.5).

Τα αρχεία που φορτώνει ο φορτωτής είναι στον δίσκο συμπιεσμένα με ZX0 (v2, του
Einar Saukas): ο rasm τα συμπιέζει (LZX0 ... LZCLOSE, ο salvador του Emmanuel
Marty), και ο φορτωτής τα ξεδιπλώνει με τον dzx0_standard (src/dzx0.asm).
Εδώ:

  pack(data)     τα bytes, συμπιεσμένα από τον rasm
  unpack(z)      (τα bytes, το περιθώριο) — ο αποσυμπιεστής της αναφοράς

ΤΟ ΠΕΡΙΘΩΡΙΟ. Ο φορτωτής ξεδιπλώνει κάθε αρχείο ΠΑΝΩ στη θέση του: η ροή
φορτώνεται στο τέλος του προορισμού και η αποσυμπίεση γράφει από την αρχή του.
Αυτό δουλεύει όσο το γράψιμο δεν προλαβαίνει το διάβασμα — αλλιώς σβήνει bytes
της ροής πριν τα διαβάσει. Η ροή μπαίνει λοιπόν ώστε να τελειώνει περιθώριο
bytes ΜΕΤΑ από το τέλος του προορισμού: το μικρότερο που κρατά κάθε byte που
γράφεται πριν από το πρώτο που δεν έχει διαβαστεί ακόμη. Το unpack το μετρά
πάνω στην ίδια την αποκωδικοποίηση, byte προς byte.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RASM = os.path.expanduser("~/rasm/rasm.exe")
WORK = os.path.join(ROOT, "build", "zx0")


def pack(data, name="pack"):
    """Τα bytes συμπιεσμένα από τον rasm (ο ίδιος συμπιεστής με το build)."""
    os.makedirs(WORK, exist_ok=True)
    raw = os.path.join(WORK, name + ".raw")
    out = os.path.join(WORK, name + ".zx0")
    asm = os.path.join(WORK, name + ".asm")
    open(raw, "wb").write(bytes(data))
    open(asm, "w").write(f'        org 0\n        lzx0\n        incbin "{raw}"\n'
                         f'        lzclose\n')
    r = subprocess.run([RASM, asm, "-ob", out], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"rasm (lzx0) απέτυχε για το {name}:\n{r.stdout}{r.stderr}")
    z = open(out, "rb").read()
    got, _ = unpack(z)
    if got != bytes(data):
        sys.exit(f"η ροή ZX0 του {name} δεν ξαναδίνει τα bytes της")
    return z


class _Bits:
    """Τα bits της ροής, όπως τα διαβάζει ο dzx0_standard: από το bit 7, ένα
    byte τη φορά, και το «backtrack» — το bit 0 του byte της απόστασης είναι το
    πρώτο bit του μήκους που ακολουθεί."""

    def __init__(self, z):
        self.z, self.i = z, 0
        self.mask, self.val = 0, 0
        self.back, self.last = False, 0

    def byte(self):
        b = self.z[self.i]
        self.i += 1
        self.last = b
        return b

    def bit(self):
        if self.back:
            self.back = False
            return self.last & 1
        self.mask >>= 1
        if not self.mask:
            self.mask, self.val = 128, self.byte()
        return 1 if self.val & self.mask else 0

    def elias(self, inverted=False):
        v = 1
        while not self.bit():
            v = v << 1 | (self.bit() ^ inverted)
        return v


def unpack(z):
    """(τα bytes, το περιθώριο). Το περιθώριο: η ροή πρέπει να τελειώνει τόσα
    bytes μετά το τέλος του προορισμού για να ξεδιπλωθεί πάνω του."""
    b = _Bits(z)
    out = bytearray()
    worst = -(1 << 30)              # max(γραμμένα - διαβασμένα), τη στιγμή κάθε γραψίματος

    def put(v):
        nonlocal worst
        # Το byte w γράφεται στο D+w· το πρώτο αδιάβαστο είναι στο S+i, με
        # S + len(z) = D + len(out τελικό) + περιθώριο. Πρέπει D+w < S+i.
        worst = max(worst, len(out) - b.i)
        out.append(v)

    last = 1
    state = "lit"
    while True:
        if state == "lit":
            for _ in range(b.elias()):
                put(b.byte())
            state = "new" if b.bit() else "rep"
        elif state == "rep":
            n = b.elias()
            for _ in range(n):
                put(out[-last])
            state = "new" if b.bit() else "lit"
        else:
            msb = b.elias(True)
            if msb == 256:
                break
            last = msb * 128 - (b.byte() >> 1)
            b.back = True
            n = b.elias() + 1
            for _ in range(n):
                put(out[-last])
            state = "new" if b.bit() else "lit"
    if b.i != len(z):
        raise ValueError(f"η ροή ZX0 τελείωσε στο byte {b.i} από {len(z)}")
    margin = max(0, worst - (len(out) - len(z)) + 1)
    return bytes(out), margin


if __name__ == "__main__":
    for path in sys.argv[1:]:
        d = open(path, "rb").read()
        z = pack(d, os.path.basename(path))
        _, m = unpack(z)
        print(f"{path}: {len(d)} -> {len(z)} bytes, περιθώριο {m}")
