; bar.asm — τα κουμπιά της κάτω λωρίδας (DESIGN §9.3, βήμα 84). Τράπεζα 0.
;
; ΟΙ ΕΝΤΟΛΕΣ ΕΙΝΑΙ ΚΟΥΜΠΙΑ, ΣΕ ΟΜΑΔΕΣ, ΟΠΩΣ ΣΤΟ PLANETBASE. Δεκαέξι θέσεις των
; 20 pixel στις γραμμές 177-191 (η 176 μένει μαύρη: εκεί σπάει η διακοπή, §8.1).
; Στο LOOK η μπάρα δείχνει τις έξι ομάδες· μια ομάδα ανοίγει τα δικά της στην
; ίδια μπάρα, με την ίδια στην αρχή (λευκή). Το ? στη θέση 15 είναι παντού.
;
;   ΘΟΛΟΙ D       S M L μέγεθος · O C Q G F B E N T U τα δέκα δωμάτια
;   ΔΙΑΔΡΟΜΟΣ R   (μόνος του: η ομάδα είναι ο διάδρομος)
;   ΕΝΕΡΓΕΙΑ P    S ηλιακός · T τουρμπίνα · C συλλέκτης
;   ΠΟΡΟΙ E       X αντλία · M ορυχείο
;   ΜΕΤΑΦΟΡΑ T    A αεροθάλαμος · P πίστα · C πλοίο · M έμπορος (βήμα 93)
;   ΔΙΑΧΕΙΡΙΣΗ M  I πληροφορίες · F εξοπλισμός · S σώσιμο · L φόρτωμα · H κέντρο
;
; ΤΟ ΓΡΑΜΜΑ ΣΤΗΝ ΚΑΤΩ ΑΡΙΣΤΕΡΗ ΓΩΝΙΑ ΕΙΝΑΙ ΤΟ ΠΛΗΚΤΡΟ, και ισχύει όσο το κουμπί
; φαίνεται. Η ομάδα ανοίγει στο MENU με το αντικείμενό της έτοιμο (όπως ως
; τώρα ο κατάλογος)· ένα αντικείμενο πάει κατευθείαν στο PLACE· το μέγεθος
; αλλάζει χωρίς να αλλάξει κατάσταση· το δωμάτιο που δεν χωρά είναι κόκκινο.
; Το ίδιο γράμμα της ανοιχτής ομάδας την κλείνει.
;
; ΤΟ ΑΡΙΣΤΕΡΑ/ΔΕΞΙΑ ΤΟΥ MENU ΜΕΝΕΙ Ο ΕΠΙΠΕΔΟΣ ΚΑΤΑΛΟΓΟΣ (src/build.asm): περνά
; από τα έντεκα με τη σειρά, και η μπάρα ακολουθεί την ομάδα του τρέχοντος.
; Το SPACE SPACE ξανανοίγει ό,τι ήταν ανοιχτό τελευταίο, όπως ως το βήμα 83.
;
; Η ΜΠΑΡΑ ΞΑΝΑΓΡΑΦΕΤΑΙ ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΖΕΙ (bar_sync, από το ui_panel): οκτώ
; bytes υπογραφής, και από τις δεκαέξι θέσεις μόνο όσες άλλαξαν. Τη ζωγραφίζει
; το sl_draw της τράπεζας 2 (src/help.asm), που ζωγραφίζει και την οθόνη
; βοήθειας με τα ίδια κουμπιά.

BT_N        equ 35                      ; κουμπιά (tools/buttons.py)· 34 ως το βήμα 100
BT_SMALL    equ 1                       ; 1-3 τα μεγέθη
BT_ROOM0    equ 4                       ; 4-13 τα δωμάτια, με τη σειρά του rm_list
BT_CORR     equ 14
BT_SHIP     equ 25
BT_TRADE    equ 26                      ; βήμα 93: αμέσως μετά το πλοίο
BT_MANAGE   equ 27
BT_FIT      equ 29
BT_DEMO     equ 33                      ; βήμα 101
BT_HELP     equ 34
BT_NONE     equ 255
BAR_N       equ 16                      ; θέσεις
BAR_HELP    equ 15                      ; το ?
BAR_OFF     equ 1600                    ; η σειρά οθόνης 22 από το cam_p (= HUD_BOT)
BAR_W      equ 5                       ; bytes ανά θέση: 18 pixel κουμπί, 2 κενό
BK_MAX      equ 15                      ; πλήκτρα ανά μπάρα: οι ΘΟΛΟΙ είναι 14 + ?
BS_GREEN    equ 0
BS_WHITE    equ 1
BS_RED      equ 2
BSG_N       equ 10                      ; bytes υπογραφής
BAR_PER     equ 2                       ; κουμπιά ανά frame (bar_more)
; Οι ομάδες
G_DOMES     equ 0
G_CORR      equ 1
G_TRANS     equ 4
G_MANAGE    equ 5
; Το τέταρτο byte του bt_tab: είδος << 5 | παράμετρος (src/act.asm, bt_key)
KB_GROUP    equ 0
KB_SIZE     equ 1
KB_ROOM     equ 2
KB_ITEM     equ 3
KB_ACT      equ 4
AB_INFO     equ 0
AB_FIT      equ 1
AB_SAVE     equ 2
AB_LOAD     equ 3
AB_HOME     equ 4
AB_SHIP     equ 5
AB_TRADE    equ 6                       ; βήμα 93· το AB_HELP ήταν 6
AB_HELP     equ 7
AB_DEMO     equ 8                       ; βήμα 101: το src/act.asm πριν από τον πίνακα

; ---------------------------------------------------------------------------
; bt_tab — ανά κουμπί: το γράμμα, η γραμμή και η μάσκα του πλήκτρου στη μήτρα
; (src/input.asm), και τι κάνει. Η σειρά είναι η σειρά του tools/buttons.py.
; ---------------------------------------------------------------------------
bt_tab:
        db 'D',7,#20, KB_GROUP << 5 | G_DOMES   ;  0 ΘΟΛΟΙ
        db 'S',7,#10, KB_SIZE << 5 | 0          ;  1 μικρός
        db 'M',4,#40, KB_SIZE << 5 | 1          ;  2 μεσαίος
        db 'L',4,#10, KB_SIZE << 5 | 2          ;  3 μεγάλος
        db 'O',4,#04, KB_ROOM << 5 | 0          ;  4 οξυγόνο
        db 'C',7,#40, KB_ROOM << 5 | 1          ;  5 καντίνα
        db 'Q',8,#08, KB_ROOM << 5 | 2          ;  6 καταλύματα
        db 'G',6,#10, KB_ROOM << 5 | 3          ;  7 θερμοκήπιο
        db 'F',6,#20, KB_ROOM << 5 | 4          ;  8 εργοστάσιο
        db 'B',6,#40, KB_ROOM << 5 | 5          ;  9 εργαστήριο
        db 'E',7,#04, KB_ROOM << 5 | 6          ; 10 ιατρείο
        db 'N',5,#40, KB_ROOM << 5 | 7          ; 11 αίθουσα ελέγχου
        db 'T',6,#08, KB_ROOM << 5 | 8          ; 12 αποθήκη
        db 'U',5,#04, KB_ROOM << 5 | 9          ; 13 σαλόνι
        db 'R',6,#04, KB_GROUP << 5 | G_CORR    ; 14 ΔΙΑΔΡΟΜΟΣ
        db 'P',3,#08, KB_GROUP << 5 | 2         ; 15 ΕΝΕΡΓΕΙΑ
        db 'S',7,#10, KB_ITEM << 5 | 4          ; 16 ηλιακός
        db 'T',6,#08, KB_ITEM << 5 | 5          ; 17 τουρμπίνα
        db 'C',7,#40, KB_ITEM << 5 | 6          ; 18 συλλέκτης
        db 'E',7,#04, KB_GROUP << 5 | 3         ; 19 ΠΟΡΟΙ
        db 'X',7,#80, KB_ITEM << 5 | 7          ; 20 αντλία
        db 'M',4,#40, KB_ITEM << 5 | 8          ; 21 ορυχείο
        db 'T',6,#08, KB_GROUP << 5 | G_TRANS   ; 22 ΜΕΤΑΦΟΡΑ
        db 'A',8,#20, KB_ITEM << 5 | 9          ; 23 αεροθάλαμος
        db 'P',3,#08, KB_ITEM << 5 | 10         ; 24 πίστα
        db 'C',7,#40, KB_ACT << 5 | AB_SHIP     ; 25 πλοίο
        db 'M',4,#40, KB_ACT << 5 | AB_TRADE    ; 26 έμπορος (βήμα 93)
        db 'M',4,#40, KB_GROUP << 5 | G_MANAGE  ; 27 ΔΙΑΧΕΙΡΙΣΗ
        db 'I',4,#08, KB_ACT << 5 | AB_INFO     ; 28
        db 'F',6,#20, KB_ACT << 5 | AB_FIT      ; 29
        db 'S',7,#10, KB_ACT << 5 | AB_SAVE     ; 30
        db 'L',4,#10, KB_ACT << 5 | AB_LOAD     ; 31
        db 'H',5,#10, KB_ACT << 5 | AB_HOME     ; 32
        db 'D',7,#20, KB_ACT << 5 | AB_DEMO     ; 33 κατεδάφιση (βήμα 101)
        db '?',3,#40, KB_ACT << 5 | AB_HELP     ; 34 (το πλήκτρο / ?)
bt_end:
        assert  bt_end - bt_tab == 4 * BT_N

; Οι ομάδες: το πρώτο αντικείμενο του καταλόγου. (Το πρώτο κουμπί και πόσα
; τα δίνει το ac_l_grp πιο κάτω, που είναι οι ομάδες με τη σειρά και το ?.)
grp_bld:    db 0, 3, 4, 7, 9
; Ο κατάλογος (src/build.asm, ui_sel): η ομάδα και το κουμπί κάθε αντικειμένου.
bld_grp:    db 0, 0, 0, 1, 2, 2, 2, 3, 3, 4, 4
bld_btn:    db 1, 2, 3, 14, 16, 17, 18, 20, 21, 23, 24
bld_end:
; Οι λίστες του αριστερά/δεξιά στο μενού (src/act.asm): οι ομάδες και το ?,
; και η ΔΙΑΧΕΙΡΙΣΗ. Η πρώτη είναι και η μπάρα του LOOK, στις θέσεις 0-5.
ac_l_grp:   db 0, 14, 15, 19, 22, BT_MANAGE, BT_HELP
        ; bww_group: η ομάδα g είναι τα κουμπιά ac_l_grp[g] .. ac_l_grp[g + 1] - 1
        assert  BT_CORR == 14 && BT_MANAGE == 27 && BT_HELP == BT_MANAGE + 7
ac_l_man:   db 28, 29, 30, 31, 32, BT_DEMO, BT_HELP

; ---------------------------------------------------------------------------
; bk_scan — τα γράμματα της μπάρας που φαίνεται, μία φορά ανά frame.
; Out: CY = μόλις πατήθηκε, A = το κουμπί. NC: τίποτα καινούργιο.
;
; ΚΩΔΙΚΑΣ ΠΟΥ ΓΡΑΦΕΙ Ο bk_gen: ένα `ld a,(key_now + γραμμή) : and μάσκα :
; jr z,bk_hit : inc c` ανά πλήκτρο, 9 us το καθένα, και ένα jr στο τέλος της
; λίστας. Με πίνακα και βρόχο θα ήταν 16 us: στο LOOK, που είναι όλο το
; παιχνίδι, επτά γράμματα κοστίζουν 63 us αντί για 112.
;
; ΑΚΜΗ ΑΝΑ ΠΛΗΚΤΡΟ, ΟΧΙ ΑΝΑ ΘΕΣΗ: το E ανοίγει τους ΠΟΡΟΥΣ από τη θέση 3, και
; στην επόμενη μπάρα το ίδιο E είναι στη θέση 0. Αν το «κρατημένο» ήταν θέση,
; το ίδιο πάτημα θα έκλεινε την ομάδα που μόλις άνοιξε.
; ---------------------------------------------------------------------------
bk_scan:
        ld      c,0
bk_code:
        jr      bk_none                 ; ως το πρώτο bk_gen: καμία μπάρα
        db      key_now >> 8
        and     0
        jr      z,bk_hit
        inc     c
        repeat  BK_MAX - 1
        ld      a,(key_now)
        and     0
        jr      z,bk_hit
        inc     c
        rend
bk_none:
        ld      c,BT_NONE
bk_hit:
        ld      a,c
        inc     a
        jr      z,bkh_up
        add     a,a
        add     a,a
        add     a,a                     ; 8 x (θέση + 1)
        ld      hl,bk_code + 1 - 8
        call    ob_addu
        ld      e,(hl)                  ; key_now + γραμμή
        inc     hl
        inc     hl
        inc     hl
        ld      d,(hl)                  ; μάσκα
        ld      hl,(bk_held)
        ld      (bk_held),de
        or      a
        sbc     hl,de
        ret     z                       ; κρατημένο από πριν: NC
        ld      a,c
        ld      hl,bk_ids
        call    ob_addu
        ld      a,(hl)
        scf
        ret
bkh_up:                                 ; NC ήδη: από το and του τελευταίου
        ld      h,c                     ; γράμματος, ή, χωρίς κανένα, από τον
        ld      l,c                     ; μόνο καλούντα (uit_state: jr c πριν)·
        ld      (bk_held),hl            ; C = BT_NONE (το inc a έδωσε 0)
        ret

        assert  bk_none - bk_code == 8 * BK_MAX
        assert  bk_hit + 2 - (bk_code + 7) <= 127   ; το jr της πρώτης

        assert  (key_now >> 8) == ((key_now + KEY_LINES - 1) >> 8)

; ---------------------------------------------------------------------------
; bar_sync — η μπάρα όπως πρέπει να είναι. Από το ui_panel, ΠΡΙΝ από το ui_hold:
; ένα μήνυμα κρατά τις σειρές 3-4, όχι τα κουμπιά.
; ---------------------------------------------------------------------------
bar_sync:
        ; ΣΥΓΚΡΙΣΗ ΚΑΘΩΣ ΔΙΑΒΑΖΕΙ: 10 us ανά byte, και στο πρώτο που διαφέρει
        ; γράφονται όλα. Τρέχει σε κάθε ui_panel, δηλαδή σε κάθε βήμα κέρσορα.
        ; Τα τρία του πλοίου ωμά (bar_shipok θα ήθελε κλήση): ένα δεύτερο
        ; Control ξαναζητά τη μπάρα χωρίς να αλλάξει τίποτα, και αυτό είναι όλο.
        ld      hl,bsg_was
        ld      a,(ui_state)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ui_sel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(bd_rsel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_sel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_mode)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_fit)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(hud_gen)             ; σβησμένες λωρίδες: όλα από την αρχή
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(G_room_n + R_CONTROL)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(EC_PADNODE)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(EC_SHSTATE)
        cp      (hl)
        ret     z
bsc_go:
        ; Η ΕΓΓΡΑΦΗ ΑΠΟ ΠΙΝΑΚΑ: τρέχει μόνο όταν κάτι άλλαξε, όχι σε κάθε βήμα
        ; κέρσορα όπως η σύγκριση από πάνω, που μένει ξετυλιγμένη.
        ld      hl,bsg_src
        ld      de,bsg_was
        ld      b,BSG_N
bsc_cp:
        ld      a,(hl)
        inc     hl
        push    hl
        ld      h,(hl)
        ld      l,a
        ld      a,(hl)
        ld      (de),a
        pop     hl
        inc     hl
        inc     de
        djnz    bsc_cp
        ld      a,(hud_gen)
        ld      hl,bs_gen
        cp      (hl)
        jr      z,bsc_want
        ld      (hl),a
        ld      hl,bs_id
        ld      b,BAR_N
bsc_inv:
        ld      (hl),BT_NONE - 1        ; καμία θέση δεν είναι αυτό
        inc     hl
        djnz    bsc_inv
bsc_want:
        call    bar_want
        ; --- άλλαξε κουμπί (όχι μόνο χρώμα); τότε και τα πλήκτρα ---
        ld      hl,bw_id
        ld      de,bs_id
        ld      b,BAR_N
bsk_lp:
        ld      a,(de)
        cp      (hl)
        inc     hl                      ; δεν αγγίζουν τις σημαίες
        inc     de
        jr      nz,bsk_gen
        djnz    bsk_lp
bsk_gen:
        call    nz,bk_gen               ; NZ: κάποιο διέφερε
        jp      bar_more                ; src/button.asm, τράπεζα 2

; ---------------------------------------------------------------------------
; bar_want — τι πρέπει να δείχνει η μπάρα: στην τράπεζα 1 από το βήμα 152
; (src/bar1.asm, στη δέσμευση b1code). Γράφει τα bw_id / bw_st από κάτω.
; ---------------------------------------------------------------------------

; Τα bytes της υπογραφής, με τη σειρά της σύγκρισης του bar_sync.
bsg_src:    dw ui_state, ui_sel, bd_rsel, ac_sel, ac_mode, ac_fit, hud_gen
            dw G_room_n + R_CONTROL, EC_PADNODE, EC_SHSTATE
bsg_end:
        assert  bsg_end - bsg_src == 2 * BSG_N

; --- μεταβλητές ------------------------------------------------------------
bk_held:    dw BT_NONE * 257
bk_ids:     defs BK_MAX
bsg_was:    defs BSG_N, 255
bs_gen:     db 255
bw_fitp:    db 255                      ; το μέγεθος του bw_fitm
bw_fitm:    dw 0
; Τα τέσσερα μαζί και με αυτή τη σειρά: το bsd_lp τα βρίσκει ανά BAR_N.
bw_id:      defs BAR_N
bw_st:      defs BAR_N
bs_id:      defs BAR_N, BT_NONE - 1
bs_st:      defs BAR_N
        assert  bw_st == bw_id + BAR_N && bs_id == bw_st + BAR_N && bs_st == bs_id + BAR_N
        assert  BAR_W == 5                     ; bsd_draw: 4c + c

; --- τα δεδομένα του sl_draw (src/button.asm), εδώ γιατί η τράπεζα 2 γέμισε ---
; Ανά κατάσταση: η μάσκα του περιγράμματος, του συμβόλου, και ο πίνακας χρώματος.
sl_pens:    db #0F, #0F
            dw sl_ctg                   ; BS_GREEN
            db #FF, #FF
            dw sl_ctw                   ; BS_WHITE
            db #0F, #F0
            dw sl_ctr                   ; BS_RED: πράσινο κουμπί, κόκκινο σύμβολο

sl_at:      dw 0
sl_piq:     dw 0
sl_src:     dw 0
sl_pic:     dw 0
sl_po:      db 0
sl_pi:      db 0
sl_ctl:     dw 0
sl_buf:     defs 15 * BAR_W
        align   16                      ; sld_ct: or με το κάτω byte
; n x #11 AND μάσκα, για n = 0-15: πράσινο (pen 2), λευκό (3), κόκκινο (1)
sl_ctg:     db #00,#01,#02,#03,#04,#05,#06,#07,#08,#09,#0A,#0B,#0C,#0D,#0E,#0F
sl_ctw:     db #00,#11,#22,#33,#44,#55,#66,#77,#88,#99,#AA,#BB,#CC,#DD,#EE,#FF
sl_ctr:     db #00,#10,#20,#30,#40,#50,#60,#70,#80,#90,#A0,#B0,#C0,#D0,#E0,#F0
        assert  sl_ctw == sl_ctg + 16 && sl_ctr == sl_ctw + 16
; ΜΕΤΑ ΤΟΝ ΠΙΝΑΚΑ, όχι πριν (βήμα 155): τα 3 bytes τους γύρισαν το align 16 στο
; μηδέν, αφού το rt_flush (src/graph.asm) πήρε 4 και το έσπρωξε 13 bytes. Και
; το bs_pend από το βήμα 157, για το byte του ob_struct_sort (src/object.asm).
sl_gly:     dw 0
sl_id:      db 0
bs_pend:    db 0                        ; μένουν κουμπιά για το επόμενο frame
        assert  sl_pi == sl_po + 1 && sl_ctl == sl_pi + 1

