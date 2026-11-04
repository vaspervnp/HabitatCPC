"""Ανάγνωση τομέων από εικόνα .dsk — για τις δοκιμές του οδηγού δισκέτας.

Ο δίσκος δεν είναι γραμμικός: η κεφαλίδα κάθε track λέει ποιοι τομείς υπάρχουν
και με ποια σειρά, και η σειρά είναι ΠΛΕΓΜΕΝΗ (C1, C6, C2, C7, ...) ώστε ο
ελεγκτής να προλαβαίνει. Το id ενός τομέα δεν είναι η θέση του.

ΤΟ EXTENDED (βήμα 183). Το iDSK γράφει τυπικό .dsk, με ένα μέγεθος για όλα τα
tracks στο #32 της κεφαλίδας. Ο Retro Virtual Machine 2.1.20, μόλις το
παιχνίδι γράψει τομέα σε τέτοιον δίσκο, κρατά μόνο αυτό το track: το αρχείο
που ξαναέγραψε ήταν EXTENDED με τον πίνακα των μεγεθών (#34 και μετά) μηδέν
παντού εκτός από το track 24, το πρώτο του slot 0 — 5.120 bytes, χωρίς
κατάλογο και χωρίς παιχνίδι — και το σώσιμο κόλλησε, πιθανότατα στο track
25, που για εκείνον δεν υπήρχε πια. Το tools/mkdsk.py γράφει από τότε
EXTENDED (to_extended), με το μέγεθος κάθε track στον πίνακα. Οι τομείς μένουν
στη θέση τους.
"""
import os

SIG_STD = b"MV - CPCEMU"
SIG_EXT = b"EXTENDED"
EXT_HDR = b"EXTENDED CPC DSK File\r\nDisk-Info\r\n"
EXT_BY = b"HabitatCPC".ljust(14)


def track_at(buf, i):
    """Πού αρχίζει το Track-Info του i-οστού track (track x όψεις + όψη) — ή
    None για track χωρίς τομείς (μέγεθος 0 στον πίνακα του EXTENDED)."""
    if buf.startswith(SIG_EXT):
        if not buf[0x34 + i]:
            return None
        return 0x100 + 256 * sum(buf[0x34:0x34 + i])
    return 0x100 + i * int.from_bytes(buf[0x32:0x34], "little")


def to_extended(buf):
    """Το τυπικό .dsk του iDSK ως EXTENDED, με τα ίδια bytes σε κάθε track.
    Στο EXTENDED τα bytes 6-7 κάθε τομέα λένε το πραγματικό μήκος του."""
    if not buf.startswith(SIG_STD):
        raise ValueError("δεν είναι τυπικό .dsk")
    nt, ns = buf[0x30], buf[0x31]
    size = int.from_bytes(buf[0x32:0x34], "little")
    assert size % 256 == 0 and nt * ns <= 204
    out = bytearray(256) + bytearray(buf[0x100:0x100 + nt * ns * size])
    out[:len(EXT_HDR)] = EXT_HDR
    out[0x22:0x30] = EXT_BY
    out[0x30], out[0x31] = nt, ns
    for i in range(nt * ns):
        out[0x34 + i] = size // 256
        t = 0x100 + i * size
        assert out[t:t + 10] == b"Track-Info"
        for k in range(out[t + 0x15]):
            e = t + 0x18 + k * 8
            out[e + 6:e + 8] = (128 << out[e + 3]).to_bytes(2, "little")
    return bytes(out)


class Dsk:
    def __init__(self, path):
        self.buf = bytearray(open(path, "rb").read())
        self.ntracks = self.buf[0x30]
        self.nsides = self.buf[0x31]
        self.ext = self.buf.startswith(SIG_EXT)
        if not self.ext and not self.buf.startswith(SIG_STD):
            raise ValueError("ούτε τυπικό ούτε EXTENDED .dsk")

    def _track(self, track, side=0):
        return track_at(self.buf, track * self.nsides + side)

    def sector(self, track, sid, side=0):
        """Τα 512 bytes του τομέα με id sid — ή None αν δεν υπάρχει."""
        t = self._track(track, side)
        if t is None:
            return None
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
        if t is None:
            return []
        return [self.buf[t + 0x18 + i * 8 + 2] for i in range(self.buf[t + 0x15])]
