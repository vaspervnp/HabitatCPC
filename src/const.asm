; const.asm — σταθερές μηχανής και χάρτη μνήμης
; Βλ. DESIGN.md §2.1, §4.1, §8.1

; --- οθόνη ---
SCR_BASE    equ #C000       ; σελίδα 3 — περιοχή παιχνιδιού
SCR_W       equ 80          ; bytes ανά γραμμή
SCR_H       equ 200         ; γραμμές συνολικά
PLAY_LINES  equ 160         ; §8.1 — οι πρώτες 160 είναι το κάδρο
HUD_LINES   equ 40

; --- gate array ---
GA_PORT     equ #7F00
RMR_MODE0   equ #8C         ; 100 0 11 00 : mode 0, κάτω ROM off, πάνω ROM off
GA_PEN      equ #00         ; 00pppppp επιλογή pen
GA_BORDER   equ #10
GA_INK      equ #40         ; 01cccccc τιμή χρώματος

; --- διαμορφώσεις RAM για το παράθυρο &4000-&7FFF (§4.1) ---
PAGE_B1     equ #C0         ; βασική τράπεζα 1
PAGE_B4     equ #C4         ; επίπεδο κόσμου
PAGE_B5     equ #C5         ; NEXTHOP
PAGE_B6     equ #C6         ; τεταρτημόρια, φιγούρες, πίνακες οντοτήτων
PAGE_B7     equ #C7         ; εξωτερικές δομές, φυτά, κείμενο, ήχος

; --- προσανατολισμοί τεταρτημορίου (§5 του SPRITES.md) ---
Q_NW        equ 0
Q_NE        equ 1           ; ζεύγη ανάποδα + flip_mode0 σε κάθε byte
Q_SW        equ 2           ; γραμμές ανάποδα
Q_SE        equ 3           ; και τα δύο

; --- οι εγγραφές των πινάκων της τράπεζας 6 (§6.1) ---
; Εδώ και όχι στο econ.asm: ο renderer τις διαβάζει χωρίς να θέλει τίποτε άλλο
; από την οικονομία, και ο assembler δεν συγχωρεί δύο ορισμούς.
MAX_DOME    equ 64
MAX_STRUCT  equ 64
MAX_CORR    equ 96
DOME_REC    equ 24
D_CX        equ 0
D_CY        equ 1
D_SIZE      equ 2
D_ROOM      equ 3
D_STATE     equ 4
D_INTEG     equ 5
D_POWER     equ 6
D_OPS       equ 7
D_MACH      equ 8
D_HEALTH    equ 16
STRUCT_REC  equ 8
ST_CX       equ 0
ST_CY       equ 1
ST_KIND     equ 2
ST_SIZE     equ 3
ST_STATE    equ 4
ST_INTEG    equ 5
CORR_REC    equ 5
C_A         equ 0
C_B         equ 1
C_DIR       equ 2
C_LEN       equ 3
C_CSTATE    equ 4
DS_EMPTY    equ 0
DS_BUILDING equ 1
DS_ACTIVE   equ 2
NO_MACH     equ 255
R_GREENHS   equ 5
R_LOUNGE    equ 11
K_SOLAR     equ 0
K_TURBINE   equ 1
K_COLLECT   equ 2
K_EXTRACT   equ 3
K_MINE      equ 4
K_AIRLOCK   equ 5
K_PAD       equ 6
K_SHIP      equ 7
