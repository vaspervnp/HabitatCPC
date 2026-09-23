"""Ανάγνωση τομέων από εικόνα .dsk — για τις δοκιμές του οδηγού δισκέτας.

Ο δίσκος δεν είναι γραμμικός: η κεφαλίδα κάθε track λέει ποιοι τομείς υπάρχουν
και με ποια σειρά, και η σειρά είναι ΠΛΕΓΜΕΝΗ (C1, C6, C2, C7, ...) ώστε ο
ελεγκτής να προλαβαίνει. Το id ενός τομέα δεν είναι η θέση του.
"""
import os

SIG_STD = b"MV - CPCEMU"
SIG_EXT = b"EXTENDED"


class Dsk:
    def __init__(self, path):
        self.buf = bytearray(open(path, "rb").read())
        self.ntracks = self.buf[0x30]
        self.nsides = self.buf[0x31]
        self.tracksize = int.from_bytes(self.buf[0x32:0x34], "little")
        if not self.buf.startswith(SIG_STD):
            raise ValueError("μόνο τυπικό .dsk· το EXTENDED δεν χρειάστηκε ακόμη")

    def _track(self, track, side=0):
        return 0x100 + (track * self.nsides + side) * self.tracksize

    def sector(self, track, sid, side=0):
        """Τα 512 bytes του τομέα με id sid — ή None αν δεν υπάρχει."""
        t = self._track(track, side)
        n = self.buf[t + 0x15]
        off = t + 0x100
        for i in range(n):
            e = t + 0x18 + i * 8
            size = 128 << self.buf[e + 3]
            if self.buf[e + 2] == sid:
                return bytes(self.buf[off:off + size])
            off += size
        return None

    def ids(self, track, side=0):
        t = self._track(track, side)
        return [self.buf[t + 0x18 + i * 8 + 2] for i in range(self.buf[t + 0x15])]
