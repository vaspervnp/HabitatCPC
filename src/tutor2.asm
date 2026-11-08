; ---------------------------------------------------------------------------
; tutor2.asm — το δεύτερο μέρος του κώδικα του tutorial (src/tutor.asm): ο
; έλεγχος ενός βήματος και ο πίνακάς τους, και από το βήμα 202 η ανάγνωση της
; γραμμής του κειμένου (tuo_line). ΓΡΑΜΜΕΝΟ ΓΙΑ ΤΟ GH_BUF + TU_ALEN,
; μετά το πρώτο μέρος, και ΣΤΙΣ ΤΡΥΠΕΣ ΤΟΥ ΜΠΛΟΚΑ ΤΩΝ ΔΟΜΩΝ από το βήμα 201:
; στις στήλες 48-63 των γραμμών 32-47 (TB_HOLE, src/const.asm), μετά τις
; γραμμές του κειμένου. Ο εγκαταστάτης το βάζει εκεί από την αρχή της εικόνας,
; και το tuo_go το φέρνει στη θέση του πριν από οτιδήποτε άλλο. Ως το βήμα 200
; ήταν μέσα στο OV_R1, μαζί με το πρώτο, και τα 160 bytes του τα παίρνει η
; κορδέλα του εργοταξίου (βήμα 202).
;
; Κανένα jr δεν περνά από το ένα μέρος στο άλλο: το tuo_go το καλεί με call,
; και πριν από αυτό το πρώτο μέρος τελειώνει με jp tu_page.
; ---------------------------------------------------------------------------

TU_N        equ 14                      ; τα βήματα
TU_YOURS    equ TU_N + 1                ; «THE COLONY IS YOURS», και η γραμμή του ως το LOOK
TU_STRUCT   equ #80                     ; tuo_tab: δομές αυτού του είδους, όσες λέει το δεύτερο byte
TU_SHIP     equ #FF                     ; tuo_tab: πλοίο αποίκων στον δρόμο
TU_ROOM     equ #FF                     ; δεύτερο byte: φτάνει το δωμάτιο
TU_ANY      equ #FE                     ; δεύτερο byte: ό,τι κι αν μπει σε υποδοχή (φυτά)
TU_METAL    equ 1                       ; οι μηχανές, με τη σειρά του MACH του tools/pack.py
TU_MEALS    equ 6
TU_MEAT     equ 9

; tuo_line — A = η γραμμή του κειμένου: στο x_t_look της τράπεζας 7, που μένει
; μέσα. Ως το βήμα 201 ήταν μέσα στο tuo_go, στο πρώτο μέρος: 60 bytes του
; OV_R1 για την κορδέλα του εργοταξίου (βήμα 202).
tuo_line:
        ld      (tuo_i),a
        ; ΑΠΟ ΤΟ ΜΠΛΟΚ ΤΩΝ ΔΟΜΩΝ (βήμα 199, TX_HOLE): η γραμμή A στις στήλες
        ; 48-63 των γραμμών 2A και 2A + 1 του, 64 bytes η μία από την άλλη.
        ; Ως το 198 32 bytes συνεχόμενα στο OV_R1 (από το βήμα 155).
        ld      h,a
        ld      l,0
        srl     h
        rr      l                       ; HL = A * 128
        ld      de,TX_HOLE
        add     hl,de
        call    ov_b1                   ; src/demolish.asm
        ld      de,tuo_buf
        ld      bc,OV_UNIT
        ldir
        ld      c,DB_STRIDE - OV_UNIT   ; το B είναι 0 μετά το ldir
        add     hl,bc
        ld      c,OV_UNIT
        ldir
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        ld      hl,tuo_buf
        ld      de,t_look
        ld      bc,32
        ldir
        ld      a,(tuo_i)
        cp      TU_YOURS
        ld      a,' '
        jr      nz,tuo_33
        ld      a,'P'                   ; το τέλος του «C=SHIP»
tuo_33:
        ld      (de),a
        ret

; tuo_done — A = βήμα 1-14. CY αν έγινε. Η 6 στο παράθυρο.
tuo_done:
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,tuo_tab - 2
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      e,(hl)
        cp      TU_SHIP
        jr      z,tuo_ship
        bit     7,a
        jr      nz,tuo_st
        ; --- θόλος με δωμάτιο A — εργοτάξιο ή χτισμένος — και μηχανή E ---
        ld      c,a
        ld      ix,G_dome_tbl
        ld      b,MAX_DOME
tuo_dlp:
        ld      a,(ix+D_STATE)
        or      a
        jr      z,tuo_dnx
        ld      a,(ix+D_ROOM)
        cp      c
        jr      nz,tuo_dnx
        ld      a,e
        cp      TU_ROOM
        scf
        ret     z
        push    bc
        push    ix
        pop     hl
        ld      bc,D_MACH
        add     hl,bc
        ld      b,8                     ; οι άδειες είναι NO_MACH (bd_commit)
tuo_mlp:
        ld      a,(hl)
        cp      e
        jr      z,tuo_got
        inc     a                       ; NO_MACH
        jr      z,tuo_mnx
        ld      a,e
        cp      TU_ANY
        jr      z,tuo_got
tuo_mnx:
        inc     hl
        djnz    tuo_mlp
        pop     bc
tuo_dnx:
        push    de
        ld      de,DOME_REC
        add     ix,de
        pop     de
        djnz    tuo_dlp
        or      a
        ret
tuo_got:
        pop     bc
        scf
        ret
        ; --- E δομές του είδους A & #7F, εργοτάξια ή χτισμένες ---
tuo_st:
        and     #7F
        ld      c,a
        ld      hl,G_struct_tbl + ST_KIND
        ld      a,(ST_TOP)              ; ως την ψηλότερη θέση σε χρήση (βήμα 157)
        ld      b,a
tuo_slp:
        ld      a,(hl)
        cp      c
        jr      nz,tuo_snx
        inc     l
        inc     l
        ld      a,(hl)                  ; ST_STATE
        dec     l
        dec     l
        or      a
        jr      z,tuo_snx
        dec     e
        scf
        ret     z
tuo_snx:
        ld      a,l
        add     a,STRUCT_REC
        ld      l,a
        jr      c,tuo_pg                ; δύο σελίδες (βήμα 154): 2 us ανά εγγραφή
tuo_sc:
        djnz    tuo_slp
        or      a
        ret
tuo_pg:
        inc     h                       ; μία φορά, στο τέλος της πρώτης σελίδας
        jr      tuo_sc
        ; --- πλοίο αποίκων στον δρόμο: το έφερε το C ---
tuo_ship:
        ld      hl,(EC_SHSTATE)         ; L = κατάσταση, H = είδος
        ld      a,l
        or      a
        ret     z
        ld      a,h
        or      a                       ; SK_COLONIST
        ret     nz
        scf
        ret

; Ενα ζευγάρι ανά βήμα: δωμάτιο και μηχανή, TU_STRUCT | είδος και πόσες, ή
; TU_SHIP.
tuo_tab:
        db      TU_STRUCT | K_SOLAR, 1          ;  1 ηλιακός
        db      R_OXYGEN, M_OXYGEN              ;  2 θόλος οξυγόνου, με τη μηχανή του
        db      TU_STRUCT | K_AIRLOCK, 1        ;  3 airlock
        db      TU_STRUCT | K_EXTRACT, 1        ;  4 αντλία
        db      R_CANTEEN, TU_MEALS             ;  5 κυλικείο με MEALS
        db      TU_STRUCT | K_SOLAR, 2          ;  6 δεύτερος ηλιακός
        db      TU_STRUCT | K_COLLECT, 1        ;  7 συλλέκτης
        db      TU_STRUCT | K_MINE, 1           ;  8 ορυχείο
        db      R_FACTORY, TU_METAL             ;  9 εργοστάσιο με METAL
        db      R_GREENHS, TU_ANY               ; 10 θερμοκήπιο με φυτά
        db      R_LAB, TU_MEAT                  ; 11 εργαστήριο με MEAT
        db      R_CONTROL, TU_ROOM              ; 12 έλεγχος
        db      TU_STRUCT | K_PAD, 1            ; 13 πίστα
        db      TU_SHIP, 0                      ; 14 πλοίο
        assert  $ - tuo_tab == 2 * TU_N
tuo_buf     equ $                       ; 32 bytes, μετά τον κώδικα: δεν γράφονται
