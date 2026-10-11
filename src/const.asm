; const.asm — σταθερές μηχανής και χάρτη μνήμης
; Βλ. DESIGN.md §2.1, §4.1, §8.1

; --- οθόνη ---
SCR_BASE    equ #C000       ; σελίδα 3 — περιοχή παιχνιδιού
SCR_W       equ 80          ; bytes ανά γραμμή
SCR_H       equ 200         ; γραμμές συνολικά
PLAY_LINES  equ 160         ; §8.1 — οι πρώτες 160 είναι το κάδρο
HUD_LINES   equ 40

; --- PPI 8255: πληκτρολόγιο ΚΑΙ ήχος περνούν από εδώ (§9.1, §9.5) ---
; Η θύρα Α του PPI είναι ο δίαυλος δεδομένων του PSG, και το πληκτρολόγιο
; κρέμεται από τη θύρα Α του PSG. Γι' αυτό οι σταθερές είναι εδώ και όχι στο
; input.asm: τις χρειάζονται και τα δύο, και η σειρά τους είναι κοινή.
PPI_A       equ #F400
PPI_B       equ #F500
PPI_C       equ #F600
PPI_CTRL    equ #F700

; --- gate array ---
GA_PORT     equ #7F00
RMR_MODE0   equ #8C         ; 100 0 11 00 : mode 0, κάτω ROM off, πάνω ROM off
GA_PEN      equ #00         ; 00pppppp επιλογή pen
GA_BORDER   equ #10
GA_INK      equ #40         ; 01cccccc τιμή χρώματος

; --- διαμορφώσεις RAM για το παράθυρο &4000-&7FFF (§4.1) ---
PAGE_B1     equ #C0         ; βασική τράπεζα 1
PAGE_B4     equ #C4         ; επίπεδο κόσμου
PAGE_B5     equ #C5         ; NEXTHOP, και πάνω του το ευρετήριο αντικειμένων
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
ST_JOINED   equ 6           ; airlock: έχει ήδη τον διάδρομό του (βήμα 87)
ST_OPS      equ 6           ; ορυχείο: όσοι σκάβουν εκεί (βήμα 94, src/drill.asm), η Drill (bit 7), η Haul (bit 6, βήμα 95)
ST_OWED     equ 7           ; εργοτάξιο: φορτία που χρωστιούνται, μέταλλο<<4 | βιοπλ. (βήμα 88)· έτοιμο ορυχείο: ο σωρός (βήμα 95, src/haul.asm)
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
MACH_HP     equ 200             ; υγεία: δουλεύει (bit 7· όπως στο newgame)
MACH_OWED   equ 7               ; καινούργια: χρωστά μέταλλο (bit 0), βιοπλαστικό (bit 1), περιμένει χτίστη (βήμα 99, src/install.asm)
MACH_READY  equ 4               ; τα υλικά ήρθαν: τη στήνει μια Build
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
; Πόσα tiles φτάνει η αντλία/το ορυχείο (§6.5). Ηταν στο build.asm, που στο
; main.asm έρχεται ΜΕΤΑ το terrain.asm: το rasm ΠΕΤΑΕΙ το μείον μπροστά σε equ
; που ορίζεται πιο κάτω (`-X`, `-X * k`, `-X + 1`· οι ετικέτες δεν παθαίνουν
; τίποτα). Το `ld bc,-RES_NEAR * 129` έβγαινε +258 (βήμα 67).
RES_NEAR    equ 2
K_AIRLOCK   equ 5
K_PAD       equ 6
K_SHIP      equ 7
; Το airlock ως άκρο διαδρόμου (src/route.asm, βήμα 86): «μέγεθος» -1, ώστε
; η ακτίνα μέγεθος + 2 να βγαίνει 1 tile, όσο το αποτύπωμά του 2x2.
AIRLOCK     equ 255

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
EC_FREELK   equ G_econ_state + 63       ; airlock μόνα τους, χωρίς διάδρομο (βήμα 86)
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

; ΟΙ ΤΡΕΙΣ ΣΤΑΘΜΕΣ ΡΕΥΜΑΤΟΣ (§6.5). Το EC_POK δεν είναι σημαία αλλά στάθμη: το
; §6.5 γράφει «machines stop, THEN oxygen stops» και ως το βήμα 32 δεν υπήρχε
; «then» — το ίδιο μπλακάουτ σταματούσε τις αντλίες και τη γεννήτρια οξυγόνου.
; Εδώ και όχι στο econ.asm, επειδή τις διαβάζουν και το hud.asm, το main.asm και
; το ship.asm, και δεν συμπεριλαμβάνουν όλα τα harness το econ.asm.
P_NONE      equ 0                       ; μπλακάουτ: τίποτα δεν γυρίζει
P_ALL       equ 1                       ; όλα
P_ESS       equ 2                       ; μόνο η υποστήριξη ζωής (MF_FLOW)

; ΤΑ ΔΥΟ ΝΕΑ ΠΕΔΙΑ ΣΤΟ ΤΕΛΟΣ, ΚΑΙ ΕΠΙΤΗΔΕΣ: το EC_POK κάθεται στο +46 και οι
; ζωντανοί στο +58, και αυτές τις μετατοπίσεις τις ξέρουν απ' έξω δέκα δοκιμές
; και τρία εργαλεία — δύο πεδία στη μέση θα τα μετακινούσαν όλα για να
; κερδίσουν τίποτα.
EC_EPOWER   equ G_econ_state + 82       ; ζήτηση ΥΠΟΣΤΗΡΙΞΗΣ ΖΩΗΣ (§6.5)
EC_ACCE     equ G_econ_state + 84       ; ο συσσωρευτής της, ανά σάρωμα
; Η βροχή μετεωριτών (§6.10), βήμα 38 — πάλι στο τέλος, για τον ίδιο λόγο.
EC_METEOR   equ G_econ_state + 86       ; κρούσεις που μένουν (0 = καμία βροχή)
EC_MCX      equ G_econ_state + 87       ; το κέντρο της, σε tiles, προσημασμένα
EC_MCY      equ G_econ_state + 88
EC_MRND     equ G_econ_state + 89       ; η δική της γεννήτρια (16 bit)
; Οι εργασίες Build στον πίνακα (βήμα 88): το NO ENGINEER του HUD ρωτά ένα byte
; αντί να σαρώνει τον πίνακα σε κάθε τικ του. Μπαίνει με το sp_build, βγαίνει
; όταν το κτίσμα τελειώσει (ja_build) — καμία Build δεν φεύγει αλλιώς.
EC_NBUILD   equ G_econ_state + 91
EC_LAND     equ G_econ_state + 92       ; 5 bytes: οι ειδικότητες των πλοίων σε δέκατα (βήμα 91, src/crew.asm)
; Ο ΕΜΠΟΡΟΣ (βήμα 93, src/ship.asm, src/lines.asm): ό,τι φέρνει, όσο είναι
; προσγειωμένος. Το κέρδος του σε %, και τέσσερα [απόθεμα, ποσότητα] — απόθεμα 0
; (το νερό, που δεν είναι εμπόρευμα) είναι κενή θέση.
EC_MARKUP   equ G_econ_state + 97
EC_CARGO    equ G_econ_state + 98       ; 8 bytes
; Τα έτοιμα ορυχεία (βήμα 94, src/drill.asm): τα μετρά ο κύκλος ροής, και τα
; διαβάζει το dr_need όταν ξυπνά ρομπότ — αλλιώς θα σάρωνε 32 δομές (+430 us).
EC_MINES    equ G_econ_state + 106

; --- πλοία (§6.11): το src/ship.asm ζει στην τράπεζα 6 από το βήμα 93, και
; αυτά τα διαβάζουν και το HUD, η μπάρα και η γραμμή του εμπόρου ---
SHIP_NONE   equ 0
SHIP_INCOM  equ 1
SHIP_LANDED equ 2
SK_COLONIST equ 0
SK_MERCHANT equ 1
SK_VISITOR  equ 2
SK_DEALT    equ 3                       ; ο έμπορος μετά τη συμφωνία (βήμα 98, src/carry.asm)
MER_SLOTS   equ 4                       ; αγαθά στο φορτίο, ως
MER_ROLL    equ #5A5                    ; τα 11 κάτω bits του r2 (src/econ.asm)
MARKUP_MIN  equ 35                      ; + 0..30 %
TRADE_N     equ 13                      ; τα αποθέματα 1-13: όλα εκτός από το νερό
TRADE_MAX   equ 99                      ; ως τόσα από ένα αγαθό σε μία προσφορά

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
; ΤΟ ΠΕΜΠΤΟ BYTE ΕΙΝΑΙ Ο ΚΟΜΒΟΣ ΤΗΣ ΕΡΓΑΣΙΑΣ, και το J_NODE είναι πού πηγαίνει
; ο πράκτορας της (βήμα 88). Για όλες τις εργασίες τα δύο είναι ίδια, εκτός
; από το πρώτο σκέλος μιας Supply: τότε το J_NODE είναι η πηγή (το σκάφος, μια
; αποθήκη) και το J_SITE το εργοτάξιο. Ως το 87 ήταν «ηλικία» και δεν το
; διάβαζε κανείς.
J_SITE      equ 4
NO_JOB      equ 255
J_BUILD     equ 0
J_OPERATE   equ 1
J_HAUL      equ 2
J_DRILL     equ 3
J_REPAIR    equ 4
J_HEAL      equ 5
J_DEFEND    equ 6
J_SUPPLY    equ 7               ; μέταλλο· J_SUPPLY + 1 βιοπλαστικό (βήμα 88, src/supply.asm)
J_TRADE     equ 9               ; τα αγαθά του εμπόρου (βήμα 98, src/carry.asm)
; Μια J_TRADE κρατά το φορτίο της στο J_SITE, όχι στον πράκτορα (βήμα 98): ό,τι
; κουβαλά συνεχίζει με τον επόμενο, αν ο πρώτος πεινάσει ή πεθάνει. 0 άδεια,
; TRADE_GIVE ένα φορτίο για τον έμπορο, ποσότητα << 4 | απόθεμα ένα δικό του.
TRADE_JOBS  equ 2               ; εργασίες ανά συμφωνία: δύο μεταφορείς
TRADE_LOAD  equ 10              ; μονάδες ανά φορτίο, όπως της τροφοδοσίας
TRADE_GIVE  equ #0F
; οι ρόλοι (§6.1) που χτίζουν: μηχανικός και ρομπότ κατασκευής
RL_ENGINEER equ 1
RL_CBOT     equ 5
RL_CARRY    equ 6
RL_DRILL    equ 7           ; βήμα 94: τα ρομπότ γεώτρησης (src/drill.asm)
; ΟΙ ΘΕΣΕΙΣ ΤΩΝ ΡΟΜΠΟΤ (βήμα 92): οι πράκτορες 0-79 είναι άποικοι και οι 80-95
; ρομπότ, τα 80 + 16 του §6.1. Ο τροχός κινεί και τους 96· το πέρασμα των
; αναγκών σταματά στο 80 (src/needs.asm), γιατί τα ρομπότ δεν τρώνε, δεν
; πίνουν, δεν κοιμούνται και δεν αναπνέουν. Το ταβάνι πληθυσμού, οι ζωντανοί
; του EC_ALIVE και η ζήτηση οξυγόνου μετρούν μόνο τους 80.
AG_BOT0     equ 80
AG_NBOT     equ 16
; Το ευρετήριο δωματίων (src/needs.asm): ως τόσοι θόλοι ανά είδος. Εδώ από το
; βήμα 88, γιατί το διαβάζει και το src/supply.asm, που δεν έχει το needs.asm
; σε κάθε harness.
ROOM_MAX    equ 8

; --- ο γράφος κόμβων (§6.2). Εδώ επειδή τον γράφει και το build mode.
MAX_DEGREE  equ 8

; --- τα πεδία των πρακτόρων (§6.1), σε παράλληλες στήλες των 128.
; Εδώ και όχι στο entity.asm: τα διαβάζει και ο renderer, και ο assembler δεν
; συγχωρεί δύο ορισμούς — αυτό ήταν το πρώτο που έσπασε όταν τα δύο μισά του
; παιχνιδιού μπήκαν για πρώτη φορά στο ίδιο binary.
AG_PG       equ G_agent_fields >> 8
AG_FLAGS    equ G_agent_fields               ; +0 flags   +128 role
AG_NODE     equ G_agent_fields + 256         ; +0 node    +128 slot
AG_DEST     equ G_agent_fields + 512         ; +0 dest    +128 edge
AG_PROG     equ G_agent_fields + 768         ; +0 progress +128 task
AG_O2       equ G_agent_fields + 1024        ; +0 o2      +128 water
AG_FOOD     equ G_agent_fields + 1280        ; +0 food    +128 sleep
AG_HEALTH   equ G_agent_fields + 1536        ; +0 health  +128 morale
AG_SUIT     equ G_agent_fields + 1792        ; +0 suit    +128 spare (βήμα 90: ως τότε skill, που δεν το διάβασε ποτέ κανείς)
; «Πάω για ανάγκη» στο πεδίο της εργασίας: όχι δείκτης εργασίας (src/needs.asm).
T_NEED      equ 254
OCCPG       equ G_node_occ >> 8

; --- η ελεύθερη τράπεζα 2, μοιρασμένη (§4.3).
; Πρώτα οι δύο μεγάλοι buffers και μετά κώδικας. Η τράπεζα 2 φαίνεται πάντα,
; οπότε και τα δύο δουλεύουν χωρίς σελιδοποίηση· αυτό που κερδίζεται είναι
; χώρος στην τράπεζα 0, που είναι η μόνη σπάνια.
GH_BUF      equ PAGE2_TOP
; ΤΟ ΑΡΧΕΙΟ ΕΙΝΑΙ ΟΣΟ ΤΟ ΧΕΙΡΟΤΕΡΟ ΦΑΝΤΑΣΜΑ, ΥΠΟΛΟΓΙΣΜΕΝΟ — όχι ένα στρογγυλό
; 1.600 (βήμα 41). Το χειρότερο είναι ένας θόλος L κόκκινος σε όλα του τα
; tiles: το πλαίσιο, τέσσερα ορθογώνια (src/ghost.asm, gh_box), και ένα σημάδι
; 2x4 σε καθένα από τα 64 tiles. Μετρημένο στο παιχνίδι: 1.160 bytes
; (tests/test_reveal.py). Η προεπισκόπηση διαδρόμου φτάνει τα 308 (βήμα 40,
; εξαντλητικά), η μεγαλύτερη δομή τα 392. Ενα μεγαλύτερο αποτύπωμα αλλάζει
; το GH_SIDE, και το αρχείο ακολουθεί.
GH_HDR      equ 4                   ; κεφαλίδα ορθογωνίου: διεύθυνση, πλάτος, ύψος
GH_EDGE     equ 2                   ; πάχος της οριζόντιας πλευράς του πλαισίου
GH_SIDE     equ 8                   ; το μεγαλύτερο αποτύπωμα σε tiles: θόλος L
GH_LOG      equ 2 * (GH_HDR + GH_SIDE * 4 * GH_EDGE) + 2 * (GH_HDR + GH_SIDE * 16 - 2 * GH_EDGE) + GH_SIDE * GH_SIDE * (GH_HDR + 2 * 4)
PAGE2_CODE  equ GH_BUF + GH_LOG     ; από εδώ και πάνω, κώδικας
; Η κρυφή μνήμη φιγούρων ήταν εδώ και πήρε 512 bytes τράπεζας 2· από το βήμα 30
; ζει στην τράπεζα 6 (G_dome_fig), όπου το πέρασμα αντικειμένων την έχει ήδη
; σελιδοποιημένη. Τα 512 έγιναν κώδικας που έφυγε από την τράπεζα 0.
DOME_FIG    equ G_dome_fig

; --- τα είδη της λίστας βρώμικων (§8.5). Εδώ επειδή τα σπρώχνει η
; προσομοίωση, που δεν συνδέει renderer στο tests/simtest.asm.
DK_SLOT     equ 0                   ; a = θόλος, b = θέση δακτυλίου
DK_MACH     equ 1                   ; a = θόλος, b = υποδοχή
DK_ICON     equ 2                   ; a = θόλος
DK_CONN     equ 3                   ; a = θόλος, b = κατεύθυνση: ο αρμός (ως το 95 η πόρτα)
DK_TILE     equ 4                   ; a = tx, b = ty (προσημασμένα)
DK_BUILT    equ 5                   ; a = κόμβος που μόλις τελείωσε (§6.9)
DK_SITE     equ 6                   ; a = θόλος, b = σειρά tiles του εργοταξίου
DK_CROW     equ 7                   ; a = tx, b = ty: τρία tiles μιας διαγωνίου
DK_AGENT    equ 8                   ; a = πράκτορας: η φιγούρα του έξω (βήμα 89)
DK_RSIZE    equ 9                   ; a = πλάτος, b = ύψος του DK_RECT που ακολουθεί
DK_RECT     equ 10                  ; a = tx, b = ty: ορθογώνιο tiles, έδαφος και ό,τι
                                    ; το πατά (βήμα 101, η κατεδάφιση)
DK_KINDS    equ 11

; --- ευρετήριο αντικειμένων (src/object.asm, βήμα 39) ---
; Στην τράπεζα 5, πάνω από το NEXTHOP[MAX_NODE][128], που τελειώνει στο
; #6FFF: από το βήμα 30 (96 κόμβοι αντί για 128) τα 4 KB από εκεί ως το τέλος
; δεν τα χρησιμοποιούσε κανείς. Ανά εγγραφή x0, x1, y0, y1 σε tiles του
; κόσμου +128, και το id· θόλοι, διάδρομοι, δομές, με τη σειρά σχεδίασης.
OI_REC      equ 5
OB_IX_FIG   equ 1           ; ob_idx: οι φιγούρες (ob_fig_scan· ως το 95 και οι πόρτες)
OB_IX_DOME  equ 2           ;         τα κελύφη των θόλων
OB_IX_CORR  equ 4           ;         οι διάδρομοι
OB_IX_STRUCT equ 8          ;         οι δομές
OB_IX_ALL   equ 15
OI_DOME     equ #4000 + MAX_NODE * 128
OI_CORR     equ OI_DOME + MAX_DOME * OI_REC
OI_STRUCT   equ OI_CORR + MAX_CORR * OI_REC
OI_END      equ OI_STRUCT + MAX_STRUCT * OI_REC
        assert  OI_END <= #8000
