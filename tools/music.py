#!/usr/bin/env python3
"""Η μουσική (βήμα 195, DESIGN §9.5): το ΜΟΝΤΕΛΟ ΑΝΑΦΟΡΑΣ του src/music.asm.

Γεννητική, όπως τη διάλεξε ο χρήστης: αργές καμπάνες από την πεντατονική της
λα ελάσσονας πάνω από ένα χαμηλό βάθος, και η ηχώ τους. Τίποτα γραμμένο από
πριν: μια γεννήτρια αποφασίζει πότε χτυπά η επόμενη καμπάνα και πού πηγαίνει.

    κανάλι A  η καμπάνα: κάθε 32-95 frames, μία στις τέσσερις σιωπή· ένα ή δύο
              σκαλιά πάνω ή κάτω στις δέκα νότες A4-G6, ένταση 8 που πέφτει
              ένα σκαλί κάθε 4 frames
    κανάλι B  το βάθος: A2 F2 C3 G2, μία συγχορδία κάθε 512 frames (10 s), που
              φουσκώνει ως το 3 και σβήνει πριν από την επόμενη
    κανάλι C  η ηχώ: η ίδια νότα 12 frames μετά, από το 4

Οι εντάσεις είναι το 1/4 του πρώτου δείγματος (ο χρήστης, «η ένταση να είναι
το 1/4 αυτής»): τέσσερα σκαλιά του AY κάτω, 12 -> 8 η καμπάνα, 8 -> 4 η ηχώ,
7 -> 3 το βάθος. Τα εφέ παίζουν στο 6-12, πάνω από αυτήν.

Ενα tick είναι ένα frame, όπως το mu_tick του Z80, και η σειρά των πράξεων
είναι η ΙΔΙΑ, ώστε το tests/test_music.py να συγκρίνει τους καταχωρητές του
εξομοιωτή με αυτούς εδώ frame προς frame.

    python3 tools/music.py [δευτερόλεπτα] [αρχείο.wav]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# οι πίνακες, όπως στο src/music.asm (mu_scale, mu_chords, mu_drone, mu_step)
SCALE = [142, 120, 106, 95, 80, 71, 60, 53, 47, 40]    # A4 C5 D5 E5 G5 A5 C6 D6 E6 G6
CHORDS = [568, 716, 478, 638]                           # A2 F2 C3 G2
DRONE = [0, 0, 0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 0]   # ανά 32 frames της συγχορδίας
STEP = [-2, -1, 1, 2]
BELL, ECHO, ECHO_T = 8, 4, 12
SEED = 0xACE1
MIXER = 0x38                       # τόνος στα A, B, C· θόρυβος κλειστός (src/sound.asm)


class Music:
    def __init__(self):
        self.fr = 0
        self.rnd = SEED
        self.deg = 4
        self.bt = 20                       # ο πρώτος χτύπος
        self.dc = 0                        # η φάση του σβησίματος, 0-3
        self.et = 0                        # frames ως την ηχώ
        self.ep = 0                        # η νότα της
        self.vol = [0, 0, 0]               # A, B, C
        self.per = [0, 0, 0]

    def rand(self):
        # 16-bit Galois LFSR, #B400: το χαμηλό byte μετά την ολίσθηση
        x = self.rnd
        bit = x & 1
        x >>= 1
        if bit:
            x ^= 0xB400
        self.rnd = x
        return x & 255

    def tick(self):
        fr = self.fr
        if fr & 511 == 0:
            self.per[1] = CHORDS[(fr >> 9) & 3]
        self.vol[1] = DRONE[(fr >> 5) & 15]
        self.fr = (fr + 1) & 0xFFFF
        self.bt -= 1
        if self.bt == 0:
            x = self.rand()
            self.bt = 32 + (x & 63)
            if x & 0xC0:                   # 1/4: σιωπή
                d = self.deg + STEP[(self.rand() >> 3) & 3]
                d = 1 if d < 0 else 8 if d > 9 else d
                self.deg = d
                self.per[0] = SCALE[d]
                self.vol[0] = BELL
                self.dc = 0
                self.et = ECHO_T
                self.ep = SCALE[d]
        self.dc = (self.dc + 1) & 3
        if self.dc == 0 and self.vol[0]:
            self.vol[0] -= 1
        if self.et:
            self.et -= 1
            if self.et == 0:
                self.per[2] = self.ep
                self.vol[2] = ECHO
        if self.dc == 2 and self.vol[2]:
            self.vol[2] -= 1

    def regs(self):
        """Οι 16 καταχωρητές του AY, όπως τους θέλει το tools/ayrender.py."""
        r = [0] * 16
        for c in range(3):
            r[2 * c], r[2 * c + 1] = self.per[c] & 255, self.per[c] >> 8
            r[8 + c] = self.vol[c]
        r[7] = MIXER
        return r


def frames(n):
    m = Music()
    out = []
    for _ in range(n):
        m.tick()
        out.append(m.regs())
    return out


if __name__ == "__main__":
    import ayrender as AY
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(HERE), "build",
                                                               "music.wav")
    d = AY.write_wav(path, AY.render_ticks(frames(int(secs * 50))))
    print(path, round(d, 1), "s")
