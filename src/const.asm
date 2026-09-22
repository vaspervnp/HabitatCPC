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
; ΟΙ ΚΟΜΒΟΙ ΕΙΝΑΙ 96, ΟΧΙ 128, και αυτό είναι απόφαση χάρτη μνήμης (§4.2). Οι
; δύο πίνακες δρομολόγησης είναι κόμβοι x 128 bytes ο καθένας, δηλαδή 12 KB
; αντί για 16 — και τα 4 KB που ελευθερώνονται στην τράπεζα 1 πήραν τα
; εικονίδια δωματίων m και l, που με τη σειρά τους ελευθέρωσαν 3.936 bytes
; ΚΩΔΙΚΑ στην τράπεζα 2. Ο κόμβος ενός θόλου είναι το id του, μιας δομής
; MAX_DOME + id: 64 + 32 = 96.
MAX_DOME    equ 64
MAX_STRUCT  equ 32
MAX_NODE    equ MAX_DOME + MAX_STRUCT
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
; --- οι δώδεκα τύποι δωματίου, με τη σειρά των εικονιδίων του pack.py ---
R_EMPTY     equ 0
R_CONTROL   equ 1
R_QUARTERS  equ 2
R_CANTEEN   equ 3
R_OXYGEN    equ 4
R_GREENHS   equ 5
R_STORAGE   equ 6
R_AIRLOCK   equ 7
R_FACTORY   equ 8
R_LAB       equ 9
R_MEDBAY    equ 10
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

; --- οι κλάσεις του world byte (§3.5) ---
W_GROUND    equ 0
W_DUST      equ 1
W_ROCK      equ 2
W_MOUNTAIN  equ 3
W_WATER     equ 4
W_DEEPWATER equ 5
W_CRATER    equ 6
W_FOUNDATION equ 7
W_OCC_MASK  equ #30
W_OCC_STRUCT equ #10

; --- ο πίνακας εργασιών (§6.7). Εδώ επειδή τον γράφει και το build mode.
MAX_JOB     equ 32
JOB_REC     equ 5
J_KIND      equ 0
J_NODE      equ 1
J_AGENT     equ 2
J_PRIO      equ 3
J_AGE       equ 4
NO_JOB      equ 255
J_BUILD     equ 0
J_OPERATE   equ 1
J_HAUL      equ 2
J_DRILL     equ 3
J_REPAIR    equ 4
J_HEAL      equ 5
J_DEFEND    equ 6

; --- ο γράφος κόμβων (§6.2). Εδώ επειδή τον γράφει και το build mode.
MAX_DEGREE  equ 8

; --- τα πεδία των πρακτόρων (§6.1), σε παράλληλες στήλες των 128.
; Εδώ και όχι στο entity.asm: τα διαβάζει και ο renderer, και ο assembler δεν
; συγχωρεί δύο ορισμούς — αυτό ήταν το πρώτο που έσπασε όταν τα δύο μισά του
; παιχνιδιού μπήκαν για πρώτη φορά στο ίδιο binary.
AG_PG       equ G_agent_fields / 256
AG_FLAGS    equ G_agent_fields               ; +0 flags   +128 role
AG_NODE     equ G_agent_fields + 256         ; +0 node    +128 slot
AG_DEST     equ G_agent_fields + 512         ; +0 dest    +128 edge
AG_PROG     equ G_agent_fields + 768         ; +0 progress +128 task
AG_O2       equ G_agent_fields + 1024        ; +0 o2      +128 water
AG_FOOD     equ G_agent_fields + 1280        ; +0 food    +128 sleep
AG_HEALTH   equ G_agent_fields + 1536        ; +0 health  +128 morale
AG_SKILL    equ G_agent_fields + 1792        ; +0 skill   +128 spare
OCCPG       equ G_node_occ / 256

; --- η ελεύθερη τράπεζα 2, μοιρασμένη (§4.3).
; Πρώτα οι δύο μεγάλοι buffers και μετά κώδικας. Η τράπεζα 2 φαίνεται πάντα,
; οπότε και τα δύο δουλεύουν χωρίς σελιδοποίηση· αυτό που κερδίζεται είναι
; χώρος στην τράπεζα 0, που είναι η μόνη σπάνια.
GH_BUF      equ PAGE2_TOP
GH_LOG      equ 1600
DOME_FIG    equ GH_BUF + GH_LOG     ; 64 θόλοι x 8 θέσεις
PAGE2_CODE  equ DOME_FIG + 512      ; από εδώ και πάνω, κώδικας
