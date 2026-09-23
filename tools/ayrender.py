#!/usr/bin/env python3
"""Ο AY-3-8912 σε ήχο που ακούγεται — από τους ΚΑΤΑΧΩΡΗΤΕΣ, όχι από τον κώδικα.

Ο κανόνας «όταν φτιάχνεις κάτι που σχεδιάζει, κοίταξέ το» δεν έχει νόημα για
τον ήχο: δεν κοιτιέται. Το αντίστοιχο είναι να ΑΚΟΥΓΕΤΑΙ, και γι' αυτό υπάρχει
αυτό εδώ. Η δοκιμή tests/test_sound.py κρατά την κατάσταση των 16 καταχωρητών
του AY σε κάθε tick (50 Hz) όπως την πήρε ο εξομοιωτής, και αυτό το αρχείο τη
μετατρέπει σε κύμα: τετραγωνικά κύματα και θόρυβος, ακριβώς όπως τα φτιάχνει το
τσιπ.

Το μοντέλο είναι του τσιπ, από την προδιαγραφή του:

  * ο μετρητής τόνου τρέχει στο ρολόι / 8 = 125.000 Hz (ο CPC δίνει 1 MHz) και
    αλλάζει στάθμη κάθε `period` βήματα — δηλαδή ΜΙΣΗ περίοδος κύματος. Ετσι
    βγαίνει ο τύπος του φύλλου δεδομένων, f = ρολόι / (16 * period): με 284 ο
    τόνος είναι 220 Hz. (Η πρώτη εκδοχή μετρούσε στο /16 και όλα ακούγονταν μία
    οκτάβα χαμηλά — φάνηκε μετρώντας τις διελεύσεις από το μηδέν στο αρχείο.)
  * ο θόρυβος είναι LFSR 17 bit, με ανάδραση bit0 xor bit3, ανά 2*`noise` βήματα
  * ο μίκτης είναι ΑΝΤΕΣΤΡΑΜΜΕΝΟΣ: 1 = κλειστό
  * η ένταση είναι λογαριθμική, 16 στάθμες

Δεν είναι ο ήχος του εξομοιωτή (που τρέχει με volume 0): είναι ΑΝΑΦΟΡΑ, όπως
το tools/refrender.py για την εικόνα.
"""
import struct, wave

CLOCK = 1000000                      # το ρολόι του AY στον CPC
STEP = CLOCK // 8                    # 125.000 βήματα το δευτερόλεπτο
TICK = STEP // 50                    # βήματα ανά frame
RATE = STEP // 2                     # ρυθμός δειγματοληψίας του αρχείου

# οι 16 στάθμες έντασης, λογαριθμικές (φύλλο δεδομένων AY-3-8910)
VOL = [0.0, 0.0137, 0.0205, 0.0291, 0.0423, 0.0618, 0.0847, 0.1369,
       0.1691, 0.2647, 0.3527, 0.4499, 0.5704, 0.6873, 0.8482, 1.0]


class AY:
    def __init__(self):
        self.tone_c = [0, 0, 0]
        self.tone_b = [1, 1, 1]
        self.noise_c = 0
        self.lfsr = 1
        self.noise_b = 1

    def render(self, reg, steps):
        """`steps` δείγματα με τους καταχωρητές `reg` σταθερούς."""
        per = [max(1, reg[0] | ((reg[1] & 15) << 8)),
               max(1, reg[2] | ((reg[3] & 15) << 8)),
               max(1, reg[4] | ((reg[5] & 15) << 8))]
        nper = max(1, reg[6] & 31)
        mix = reg[7]
        amp = [VOL[reg[8] & 15], VOL[reg[9] & 15], VOL[reg[10] & 15]]
        out = []
        for _ in range(steps):
            for c in range(3):
                self.tone_c[c] += 1
                if self.tone_c[c] >= per[c]:
                    self.tone_c[c] = 0
                    self.tone_b[c] ^= 1
            self.noise_c += 1
            if self.noise_c >= nper * 2:
                self.noise_c = 0
                bit = (self.lfsr ^ (self.lfsr >> 3)) & 1
                self.lfsr = (self.lfsr >> 1) | (bit << 16)
                self.noise_b = self.lfsr & 1
            s = 0.0
            for c in range(3):
                t = self.tone_b[c] | ((mix >> c) & 1)
                n = self.noise_b | ((mix >> (c + 3)) & 1)
                # Το τσιπ βγάζει 0 ή amp· εδώ το κύμα ΚΕΝΤΡΑΡΕΤΑΙ σε ±amp/2,
                # αλλιώς το αρχείο είναι ένα σκέτο DC σκαλοπάτι και ό,τι το
                # παίξει το κόβει.
                s += amp[c] * (0.5 if t & n else -0.5)
            out.append(s / 3.0)
        return out


def render_ticks(frames, gap=0):
    """`frames` = λίστα από καταστάσεις 16 καταχωρητών, μία ανά tick 50 Hz."""
    ay = AY()
    samples = []
    for reg in frames:
        samples += ay.render(reg, TICK)
    if gap:
        samples += [0.0] * int(gap * STEP)
    return samples


def write_wav(path, samples, rate=RATE):
    # υποδιπλασιασμός με μέσο όρο ζεύγους: 125 kHz -> 62,5 kHz, και λίγο
    # φιλτράρισμα στο δρόμο
    samples = [(a + b) / 2 for a, b in zip(samples[0::2], samples[1::2])]
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 26000))
                    for s in samples)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data)
    return len(samples) / rate
