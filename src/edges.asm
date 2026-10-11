; edges.asm — οι ακμές του γράφου, και «είναι έτοιμο;» (βήμα 87)
;
; Ως το βήμα 86 το cr_link_bc ήταν στο route.asm. Από το 87 το θέλει και το
; door.asm, που τελειώνει ένα κτίσμα μέσα στο πέρασμα των εργασιών — και αυτό
; τρέχει και στο tests/simtest.asm, που δρομολογητή δεν έχει. Ενα μικρό
; αρχείο που μπαίνει σε όλες τις εκδόσεις, στην τράπεζα 2 του παιχνιδιού.

; cr_link_bc — η ακμή B <-> C, και οι δύο κατευθύνσεις (και το colony.asm).
cr_link_bc:
        call    cr_edge                 ; κρατά τα BC
        ld      a,b
        ld      b,c
        ld      c,a
        call    cr_edge
        ; Οχι rt_begin: αυτό μόνο μηδενίζει τον μετρητή πηγών. Το rt_dirty
        ; είναι που κάνει τον τροχό να ΤΡΕΞΕΙ την ανοικοδόμηση.
        jp      rt_mark

; cr_edge — προσθέτει τον C στους γείτονες του B, αν χωράει. Κρατά τα BC.
cr_edge:
        ld      h,NODEPG
        ld      l,b
        ld      a,(hl)
        cp      MAX_DEGREE
        ret     nc
        inc     (hl)
        ld      l,b
        ld      h,G_node_adj >> 11      ; G_node_adj + 8 * B, όπως το lk_adj
        add     hl,hl                   ; (src/door.asm): το #300 με δύο inc h
        add     hl,hl
        inc     h
        add     hl,hl
        inc     h
        add     a,l                     ; ο βαθμός < 8: χωρά στα τρία bits
        ld      l,a
        ld      (hl),c
        ret

        assert  MAX_DEGREE <= 8
        assert  (G_node_adj & #7FF) == #300     ; τα δύο inc h του cr_edge

; ---------------------------------------------------------------------------
; gr_live — A = κόμβος, τράπεζα 6 μέσα -> Z αν το κτίσμα του είναι
; DS_ACTIVE, HL -> D_STATE / ST_STATE. Κρατά BC, DE. Για το cr_commit, το
; door.asm και το en_in (βήμα 87), σε όλες τις εκδόσεις — γι' αυτό χωρίς το
; mt_rec, που το tests/uitest.asm δεν έχει. Στην τράπεζα 2: η 0 είναι γεμάτη
; ως τη σκαλωσιά των tests (#3C00).
; ---------------------------------------------------------------------------
gr_live:
        push    de
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 8 * κόμβος
        cp      MAX_DOME
        jr      nc,grl_s
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; 24 * θόλος
        ld      de,G_dome_tbl + D_STATE
        jr      grl_t
grl_s:
        ld      de,G_struct_tbl - MAX_DOME * STRUCT_REC + ST_STATE
grl_t:
        add     hl,de
        pop     de
        ld      a,(hl)
        cp      DS_ACTIVE
        ret

        assert  DOME_REC == 24 && STRUCT_REC == 8 && D_STATE == ST_STATE
