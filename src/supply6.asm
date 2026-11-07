; supply6.asm — κώδικας της τροφοδοσίας στις ουρές 4-5 των σελίδων πεδίων της
; τράπεζας 6 (βήμα 197, DESIGN §4.2): το sp_owed, το mc_live, το mc_order και
; το sp_find, από τη σελίδα 2 (src/supply.asm), όπου έμεναν 2 bytes. Τρέχουν
; μόνο με την 6 μέσα: τα καλούν το sp_arrive (από το jb_arrive του τροχού), το
; sp_sweep, το mca_got και το fit_set μετά το fit_slot. Στο tests/simtest.asm,
; στο uitest και στο objtest το B6T_PIECE δεν κάνει τίποτα.

        B6T_PIECE 4

; sp_owed — A = κόμβος, (sp_mat) = 0 μέταλλο, 1 βιοπλαστικό. HL -> το byte
; αυτού του υλικού, DE -> του άλλου (σε δομή το ίδιο), B = ένα φορτίο, C = η
; μάσκα του. Απαιτεί την τράπεζα 6. Θόλος: x24 από το G_dome_tbl· δομή: x8
; από το G_struct_tbl, που αρχίζει αμέσως μετά τους θόλους.
sp_owed:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x8
        ld      de,G_struct_tbl - MAX_DOME * STRUCT_REC + ST_OWED
        cp      MAX_DOME
        jr      nc,spo_add
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; x24
        ld      de,G_dome_tbl + D_OPS
spo_add:
        add     hl,de                   ; D_OPS, ή ST_OWED
        cp      MAX_DOME
        ld      d,h
        ld      e,l
        ld      a,(sp_mat)
        jr      nc,spo_st
        dec     de                      ; D_POWER
        or      a
        jr      nz,spo_one              ; βιοπλαστικό: HL -> D_OPS, DE -> D_POWER
        ex      de,hl                   ; μέταλλο: HL -> D_POWER, DE -> D_OPS
spo_one:
        ld      bc,#01FF
        ret
spo_st:
        or      a
        ld      bc,#10F0                ; μέταλλο: τα πάνω τέσσερα bits
        ret     z
        ld      bc,#010F
        ret

; ---------------------------------------------------------------------------
; mc_live — A = ο κόμβος μιας Supply. NZ αν είναι θόλος σε λειτουργία: τότε
; τα χρωστάνε μόνο οι μηχανές του. Κρατά A, BC. Τράπεζα 6. Από το sp_arrive.
; Στην τράπεζα 2 από το βήμα 100 (ο χώρος της 0 πήγε στα σήματα), εδώ από
; το 197.
; ---------------------------------------------------------------------------
mc_live:
        cp      MAX_DOME
        jr      nc,mcl_st
        call    jb_dome_ptr             ; κρατά το A (src/jobs.asm)
        ld      de,D_STATE
        add     hl,de
        bit     1,(hl)                  ; DS_ACTIVE
        ret
mcl_st:
        cp      a                       ; δομή: Z
        ret


        B6T_PIECE 5

; ---------------------------------------------------------------------------
; mc_order — A = θόλος, από το fit_set (src/fit.asm): μία Supply ανά υλικό
; για τη μηχανή που μόλις μπήκε, αν δεν υπάρχει ήδη μία για αυτόν τον θόλο —
; του εργοταξίου του ή άλλης μηχανής του (βήμα 99, src/install.asm). Κρατά
; το A και το HL.
; ---------------------------------------------------------------------------
mc_order:
        push    hl
        ld      c,J_SUPPLY
        call    mco_one
        inc     c                       ; J_SUPPLY + 1: βιοπλαστικό
        call    mco_one
        pop     hl
        ret
mco_one:
        call    sp_find
        ret     z
        jp      sp_post                 ; κρατά τα A, C

; sp_find — A = κόμβος, C = είδος: Z αν υπάρχει εργασία αυτού του είδους με
; J_SITE αυτόν τον κόμβο. Κρατά τα A, C· χαλάει B, DE, L, IX. Μια ελεύθερη
; θέση είναι NO_JOB, που δεν είναι κανένα είδος.
sp_find:
        ld      ix,G_job_tbl
        ld      de,JOB_REC
        ld      b,MAX_JOB
spf_lp:
        cp      (ix+J_SITE)
        jr      nz,spf_n
        ld      l,a
        ld      a,c
        cp      (ix+J_KIND)
        ld      a,l
        ret     z
spf_n:
        add     ix,de                   ; το add ix δεν αγγίζει το Z: NZ στο τέλος
        djnz    spf_lp
        ret

