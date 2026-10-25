"""Κώδικας του παιχνιδιού, όπου κι αν ζει: για τις δοκιμές που τον διαβάζουν ή
τον πειράζουν (βήμα 110).

Το peek/poke του εξομοιωτή βλέπει ό,τι είναι στο παράθυρο &4000-&7FFF τη
στιγμή εκείνη, συνήθως η τράπεζα 1. Ο κώδικας του τροχού στο b6code
(src/bots.asm και ό,τι ακολουθεί στο src/main.asm) ζει στην τράπεζα 6, στις
ίδιες διευθύνσεις. Από το βήμα 110 εκεί είναι και οι ανάγκες και οι
μετεωρίτες, που πολλές δοκιμές πειράζουν για τα αρνητικά τους· ένα poke στη
διεύθυνσή τους θα έγραφε στο DIST της τράπεζας 1, και το αρνητικό θα «περνούσε»
επειδή δεν πείραξε τίποτα.
"""
import ctypes, os

import cpc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == name:
            return int(p[2].lstrip("#"), 16)
    raise KeyError(name)


B6_START = _layout("G_b6code")
B6_END = _layout("G_worldinfo")         # εκεί τελειώνει το b6code (βήμα 172· ως τότε το G_agent_fields, #6C00)


def in_b6(addr):
    return B6_START <= addr < B6_END


def _b6(m):
    return cpc._lib.cpcemu_ram_ptr(m._h, 6)


def read(m, addr, n):
    """n bytes κώδικα από το addr, από την τράπεζα 6 αν είναι στο b6code."""
    if in_b6(addr):
        return ctypes.string_at(ctypes.addressof(_b6(m).contents) + addr - 0x4000, n)
    return bytes(m.read_ram(addr, n))


def poke(m, addr, v):
    if in_b6(addr):
        _b6(m)[addr - 0x4000] = v
    else:
        m.poke(addr, v)


def find(m, addr, pat, span=400):
    """Η διεύθυνση του pat μετά το addr, ή None."""
    i = read(m, addr, span).find(bytes(pat))
    return None if i < 0 else addr + i


CTRL_AT, CTRL_N = 0x3F80, 64


def phase(m):
    """Η ΦΑΣΗ ΤΗΣ ΜΕΤΡΗΣΗΣ (βήμα 155): πόσα µs παραπάνω, 0 ή 1, μετρά ο βρόχος
    των δοκιμών — set_pc στο probe, run_us(1) ώσπου το PC να φτάσει στο jr $ —
    από αυτό το σημείο της ιστορίας του m.

    Ο εξομοιωτής δεν στρογγυλεύει κάθε εντολή σε µs: ένα call (17 T) και ένα
    ret (10 T) κοστίζουν ένα µs παραπάνω ή όχι, ανάλογα με τη φάση που άφησε ό,τι
    έτρεξε πριν. Ενα Rig που τρέχει 400 frames του παιχνιδιού πριν μετρήσει την
    παίρνει από την εκκίνηση: όταν το βήμα 155 άλλαξε τον εγκαταστάτη των
    τρυπών, κάθε μέτρηση του test_oibuild βγήκε 1 µs πάνω, ίδια σε όλες τις 300
    περιπτώσεις, και 200 nop με call και ret 220 αντί για 219. Ο μάρτυρας εδώ
    έχει το σχήμα των probe — di, ld sp, ld bc, out, call σε CTRL_N nop και ret,
    jr $ — και κοστίζει ακριβώς 19 + CTRL_N µs· ό,τι παραπάνω είναι η φάση, και
    η δοκιμή την αφαιρεί. Τα bytes του γυρίζουν όπως ήταν, και ο Z80 μένει στο
    jr $: μόνο αμέσως πριν από ένα probe."""
    at, sub = CTRL_AT, CTRL_AT + 16
    code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
            0xCD, sub & 255, sub >> 8, 0x18, 0xFE]
    old = bytes(m.read_ram(at, 16 + CTRL_N + 1))
    m.write_ram(at, bytes(code).ljust(16, b"\0") + bytes(CTRL_N) + b"\xC9")
    m.set_pc(at)
    end, t = at + 12, 0
    while not (end <= m.pc <= end + 2) and t < 1000:
        m.run_us(1)
        t += 1
    m.write_ram(at, old)
    ph = t - (19 + CTRL_N)
    assert ph in (0, 1), f"ο μάρτυρας της φάσης μέτρησε {t} µs, όχι {19 + CTRL_N} ή {20 + CTRL_N}"
    return ph


# --- ΤΟ ΟΡΙΟ ΣΑΡΩΣΗΣ (βήμα 157, src/top.asm) --------------------------------
# Κάθε πέρασμα του πίνακα των δομών σταματά στο ST_TOP. Το γράφουν μόνο το
# st_recount (wheel_reset: αρχή, φόρτωμα) και το st_raise (al_commit), οπότε
# μια δοκιμή που γράφει τον πίνακα μόνη της γράφει και το όριο — αλλιώς τα
# περάσματα δεν βλέπουν ό,τι έβαλε πάνω από αυτό. Οι πέντε μορφές είναι στο
# node_deg, μετά τον τελευταίο κόμβο (src/const.asm).
MAX_DOME, MAX_STRUCT = 64, 48
TOP_AT = _layout("G_rt_nodes") + MAX_DOME + MAX_STRUCT     # ST_TEND


def top_of(st):
    """ST_TOP για τα bytes ενός πίνακα δομών, όπως το st_count: η ψηλότερη θέση
    που δεν είναι άδεια + 1, ζυγό, τουλάχιστον 2."""
    used = [s for s in range(len(st) // 8) if st[8 * s + 4]]
    return (max(used) + 2) & ~1 if used else 2


def top_bytes(t):
    """Ό,τι γράφει το st_set για ST_TOP = t: ST_TEND, ST_THALF, ST_TOP,
    ST_TZERO, ST_THI. Το test_sttop κρατά αυτό το αντίγραφο ίδιο με το st_set."""
    assert t % 2 == 0 and 2 <= t <= MAX_STRUCT, t
    return bytes([MAX_DOME + t, t // 2, t, 0, max(t - 16, 1)])


def set_top(m, sym, t):
    """Το όριο t, όπως το γράφει το st_set: οι μορφές και το rt_n."""
    m.write_ram(TOP_AT, top_bytes(t))
    m.poke(sym["RT_N"], MAX_DOME + t)


def top(m):
    """Το ST_TOP του m, και οι πέντε μορφές του."""
    b = bytes(m.read_ram(TOP_AT, 5))
    return b[2], b


# ΤΟ ΟΡΙΟ ΤΩΝ ΔΙΑΔΡΟΜΩΝ (βήμα 159, CT_TOP, src/const.asm): ένα byte στη θέση
# 117 του node_deg, αμέσως μετά τις πέντε μορφές του ST_TOP. Το γράφουν το
# ct_recount (wheel_reset: αρχή, φόρτωμα) και το cr_commit· μια δοκιμή που
# γράφει τον πίνακα των διαδρόμων μόνη της γράφει και αυτό, αλλιώς το
# ευρετήριο, το lk_done και η κατεδάφιση δεν βλέπουν ό,τι έβαλε πάνω από αυτό.
MAX_CORR, CORR_REC, CT_EMPTY = 128, 4, 254
CT_AT = TOP_AT + 5


def ctop_of(ct):
    """CT_TOP για τα bytes ενός πίνακα διαδρόμων, όπως το ct_recount: η
    ψηλότερη εγγραφή που δεν είναι CT_EMPTY + 1 (και η συνέχεια μιας στροφής),
    τουλάχιστον 1. Κοιτάζει ως MAX_CORR εγγραφές: την άδεια μετά από αυτές όχι."""
    n = min(len(ct) // CORR_REC, MAX_CORR)
    used = [k for k in range(n) if ct[CORR_REC * k] != CT_EMPTY]
    return max(used) + 1 if used else 1


def set_ctop(m, n):
    """Το όριο των διαδρόμων n (1-128) στο m."""
    assert 1 <= n <= MAX_CORR, n
    m.poke(CT_AT, n)


def ctop(m):
    """Το CT_TOP του m."""
    return m.peek(CT_AT)
