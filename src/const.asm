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

; --- η κατάσταση της οικονομίας (§6.5). Εδώ επειδή τη διαβάζει και το HUD,
; σε κάθε frame, χωρίς να θέλει τίποτε άλλο από το econ.asm.
EC_STOCK    equ G_econ_state            ; 14 x 16-bit
EC_PSTORE   equ G_econ_state + 28
EC_PCAP     equ G_econ_state + 30
EC_PPROD    equ G_econ_state + 32
EC_PUSE     equ G_econ_state + 34
EC_MPOWER   equ G_econ_state + 36
EC_O2PROD   equ G_econ_state + 38
EC_O2USE    equ G_econ_state + 40
EC_ACCP     equ G_econ_state + 42
EC_ACCO2    equ G_econ_state + 44
EC_POK      equ G_econ_state + 46
EC_O2OK     equ G_econ_state + 47
EC_PDOME    equ G_econ_state + 48
EC_DAY      equ G_econ_state + 49
EC_WIND     equ G_econ_state + 50
EC_SOL      equ G_econ_state + 51
EC_FRAME    equ G_econ_state + 52
EC_RND      equ G_econ_state + 54
EC_JDOME    equ G_econ_state + 56       ; περιστροφικοί δείκτες του πίνακα
EC_JAGENT   equ G_econ_state + 57       ; εργασιών (§6.7)
EC_ALIVE    equ G_econ_state + 58
EC_GAMEOVER equ G_econ_state + 59       ; §10.3 — η μόνη συνθήκη ήττας
EC_GLOOM    equ G_econ_state + 60       ; πένθος: ανεβαίνει με κάθε θάνατο
EC_STORM    equ G_econ_state + 61       ; περιστροφές αμμοθύελλας (§6.10)
EC_AMENITY  equ G_econ_state + 62       ; δέντρα και σαλόνια (§6.6)
EC_SOLLEN   equ G_econ_state + 64       ; frames ανά sol — ΔΕΔΟΜΕΝΟ (§6.11)
EC_DAYLEN   equ G_econ_state + 66
EC_PRODM    equ G_econ_state + 68       ; ποια αποθέματα φτιάχτηκαν ΕΔΩ
EC_SHETA    equ G_econ_state + 70
EC_SHSTATE  equ G_econ_state + 72
EC_SHKIND   equ G_econ_state + 73
EC_POPCAP   equ G_econ_state + 74
EC_MILE     equ G_econ_state + 75       ; τα πέντε ορόσημα του §10.2
EC_DEATHS   equ G_econ_state + 76
EC_NODEATH  equ G_econ_state + 77
EC_GREENS   equ G_econ_state + 78
EC_NOTRADE  equ G_econ_state + 79
EC_TRADED   equ G_econ_state + 80
EC_PADNODE  equ G_econ_state + 81

EC_CAP      equ 600                     ; ταβάνι αποθέματος

; --- τα δεκατέσσερα αποθέματα, με τη σειρά του econ.py ---
S_WATER     equ 0
S_FOOD      equ 1
S_ORE       equ 2
S_METAL     equ 3
S_BIOPL     equ 4
S_PROC      equ 5
S_SPARE     equ 6
S_MEDI      equ 7
S_GUN       equ 8
S_BOT       equ 9
S_STARCH    equ 10
S_VEG       equ 11
S_MEDPLANT  equ 12
S_MEAT      equ 13
