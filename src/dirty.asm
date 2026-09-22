; dirty.asm — η λίστα αλλαγών (DESIGN §8.5).
;
; Μετά την πρώτη σχεδίαση, ΤΙΠΟΤΑ δεν ξαναζωγραφίζεται αν δεν άλλαξε. Ενα
; δαχτυλίδι 32 θέσεων κρατά τι άλλαξε, και ο renderer ξέρει την ελάχιστη
; επανασχεδίαση για κάθε είδος.
;
; Ο ΠΡΟΫΠΟΛΟΓΙΣΜΟΣ ΕΙΝΑΙ ΤΟ ΝΟΗΜΑ. Χωρίς αυτόν, μια αμμοθύελλα που βρωμίζει
; σαράντα tiles ή ένα βήμα κάμερας που ξαναγράφει το HUD θα έριχνε frames. Με
; αυτόν, η δουλειά απλώνεται και το υπόλοιπο μεταφέρεται — η εικόνα μένει ένα
; δύο frames πίσω αντί για το ρολόι.
;
; Δεν υπάρχει ρολόι στον CPC, οπότε ο προϋπολογισμός είναι σε ΜΕΤΡΗΜΕΝΟ κόστος
; ανά είδος (dirty_cost). Οι αριθμοί βγήκαν από το test_dirty, όχι από εκτίμηση.
;
; ΠΑΝΤΑ βγαίνει τουλάχιστον ΕΝΑ στοιχείο ανά κλήση: αλλιώς ένα στοιχείο πιο
; ακριβό από τον προϋπολογισμό θα κολλούσε τη λίστα για πάντα.

DIRTY_N     equ 32
DIRTY_REC   equ 3
DIRTY_BUD   equ 20000               ; us ανά frame (§8.5)

DK_SLOT     equ 0                   ; a = θόλος, b = θέση δακτυλίου
DK_MACH     equ 1                   ; a = θόλος, b = υποδοχή
DK_ICON     equ 2                   ; a = θόλος
DK_CONN     equ 3                   ; a = θόλος, b = κατεύθυνση
DK_TILE     equ 4                   ; a = tx, b = ty (προσημασμένα)
DK_KINDS    equ 5

; ---------------------------------------------------------------------------
; dirty_reset — άδεια λίστα.
; ---------------------------------------------------------------------------
dirty_reset:
        xor     a
        ld      (dirty_head),a
        ld      (dirty_num),a
        ld      (dirty_over),a
        ret

; ---------------------------------------------------------------------------
; dirty_push — A = είδος, B = a, C = b.
;
; Αν το δαχτυλίδι γεμίσει, ΔΕΝ πετάμε το παλιότερο: σηκώνουμε σημαία. Μια
; χαμένη αλλαγή αφήνει ψέμα στην οθόνη για πάντα· μια πλήρης επανασχεδίαση
; κοστίζει, αλλά λέει αλήθεια.
; ---------------------------------------------------------------------------
dirty_push:
        ld      (dp_kind),a             ; ΟΧΙ στο D: το dirty_slot_addr το πατάει
        ld      a,(dirty_num)
        cp      DIRTY_N
        jr      c,dp_room
        ld      a,1
        ld      (dirty_over),a
        ret
dp_room:
        ld      e,a
        inc     a
        ld      (dirty_num),a
        ld      a,(dirty_head)
        add     a,e
        cp      DIRTY_N
        jr      c,dp_nowrap
        sub     DIRTY_N
dp_nowrap:
        call    dirty_slot_addr
        ld      a,(dp_kind)
        ld      (hl),a
        inc     hl
        ld      (hl),b
        inc     hl
        ld      (hl),c
        ret

; dirty_slot_addr — A = θέση στο δαχτυλίδι -> HL = η εγγραφή.
dirty_slot_addr:
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; *3
        ld      de,dirty_ring
        add     hl,de
        ret

; ---------------------------------------------------------------------------
; dirty_tick — δουλεύει ως τον προϋπολογισμό. Out: A = πόσα έμειναν.
; ---------------------------------------------------------------------------
dirty_tick:
        ld      hl,0
        ld      (dt_spent),hl
dt_lp:
        ld      a,(dirty_num)
        or      a
        jr      z,dt_done
        ; --- χωράει άλλο ένα; ---
        ld      a,(dirty_head)
        call    dirty_slot_addr
        ld      a,(hl)
        cp      DK_KINDS
        jr      nc,dt_pop               ; άγνωστο είδος: πέτα το
        ld      (dt_kind),a
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,dirty_cost
        add     hl,de
        ld      e,(hl)
        inc     hl
        ld      d,(hl)                  ; DE = κόστος
        ld      hl,(dt_spent)
        ld      a,h
        or      l
        jr      z,dt_take               ; το πρώτο βγαίνει πάντα
        add     hl,de
        ld      (dt_new),hl
        ex      de,hl
        ld      hl,DIRTY_BUD
        or      a
        sbc     hl,de
        jr      c,dt_done               ; θα ξεπερνούσε — μένει για το επόμενο
        ld      hl,(dt_new)
        jr      dt_store
dt_take:
        add     hl,de
dt_store:
        ld      (dt_spent),hl
        ; --- τα ορίσματα, πριν χαθεί η εγγραφή ---
        ld      a,(dirty_head)
        call    dirty_slot_addr
        inc     hl
        ld      a,(hl)
        ld      (dt_a),a
        inc     hl
        ld      a,(hl)
        ld      (dt_b),a
        push    af
        call    dt_dispatch
        pop     af
dt_pop:
        ld      a,(dirty_head)
        inc     a
        cp      DIRTY_N
        jr      c,dt_ph
        xor     a
dt_ph:
        ld      (dirty_head),a
        ld      hl,dirty_num
        dec     (hl)
        jr      dt_lp
dt_done:
        ld      a,(dirty_num)
        ret

; dt_dispatch — το είδος στο dt_kind, τα ορίσματα σε dt_a / dt_b.
dt_dispatch:
        ld      a,(dt_kind)
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,dirty_jmp
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        jp      (hl)

; ---------------------------------------------------------------------------
; Οι χειριστές. Καθένας σελιδοποιεί ό,τι χρειάζεται και γυρίζει στην τράπεζα 1.
; ---------------------------------------------------------------------------
dt_prep:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(dt_a)
        call    ob_dome_live
        jr      z,dt_no
        call    ob_getdome
        call    ob_vis
        or      a
dt_no:
        ret

dt_end:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; --- μπαινοβγαίνει άποικος: ΜΙΑ θέση, 16 bytes ---
dh_slot:
        call    dt_prep
        jr      z,dt_end
        ld      a,(d_id)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,dome_fig
        add     hl,de
        ld      (of_ptr),hl
        ld      a,(d_rec+D_SIZE)
        ld      (of_size),a
        ld      a,(dt_b)
        call    ob_fig_one
        jr      dt_end

; --- αλλάζει ή χαλάει μηχάνημα, ή μεγαλώνει φυτό: ΜΙΑ υποδοχή ---
dh_mach:
        call    dt_prep
        jr      z,dt_end
        ld      a,(d_rec+D_ROOM)
        cp      R_GREENHS
        ld      a,0
        jr      nz,dh_m_nog
        inc     a
dh_m_nog:
        ld      (om_green),a
        or      a
        jr      z,dh_m_go
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
dh_m_go:
        ld      a,(dt_b)
        call    ob_mach_one
        jr      dt_end

; --- αλλάζει τύπος δωματίου: το εικονίδιο ---
dh_icon:
        call    dt_prep
        jr      z,dt_end
        call    ob_icon
        jr      dt_end

; --- προστίθεται διάδρομος: το conn της πλευράς ---
dh_conn:
        call    dt_prep
        jr      z,dt_end
        ld      a,(dt_b)
        and     7
        call    ob_conn_one
        jr      dt_end

; --- αλλάζει tile (ορυχείο, μετεωρίτης): το tile ΚΑΙ οι τέσσερις γείτονες ---
; Το autotile του καθενός εξαρτάται από τους δικούς του γείτονες, οπότε ένα
; tile που αλλάζει κλάση αλλάζει και τις τέσσερις παραλλαγές γύρω του. Το 3x3
; τα πιάνει όλα με ένα ορθογώνιο αντί για πέντε.
dh_tile:
        ld      a,(dt_a)
        ld      hl,cam_tx
        sub     (hl)
        dec     a                       ; στήλη κάδρου του γείτονα δυτικά
        ld      (dk_c0),a
        ld      a,(dt_b)
        ld      hl,cam_ty
        sub     (hl)
        dec     a
        ld      (dk_r0),a
        ld      hl,dk_c0
        ld      b,VIEW_TW
        call    dk_clamp
        ld      a,c
        ld      (td_c0),a
        ld      a,b
        ld      (td_nc),a
        or      a
        ret     z
        ld      hl,dk_r0
        ld      b,VIEW_TH
        call    dk_clamp
        ld      a,c
        ld      (td_r0),a
        ld      a,b
        ld      (td_nr),a
        or      a
        ret     z
        call    view_cliprect
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    tile_draw_rect
        call    dh_occupied             ; ΟΣΟ η τράπεζα 4 είναι ακόμη μέσα
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        or      a
        jr      z,dh_t_clean
        call    ob_draw_all
dh_t_clean:
        jp      ob_clip_full

; dh_occupied — πατάει κάτι το ορθογώνιο; A = 0 αν είναι όλο ελεύθερο έδαφος.
;
; Χωρίς αυτό, ΚΑΘΕ αλλαγή εδάφους πλήρωνε ολόκληρο το πέρασμα αντικειμένων —
; 99.840 us για ένα tile που έσκαψε ένα ρομπότ στην ερημιά. Τα bits κατοχής
; του §3.5 υπάρχουν ακριβώς για να μη χρειάζεται να ρωτηθεί η λίστα θόλων.
dh_occupied:
        ld      a,(td_nr)
        ld      (dh_rows),a
        ld      a,(cam_ty)
        ld      hl,td_r0
        add     a,(hl)
        ld      (dh_ty),a
dho_row:
        ld      a,(cam_tx)
        ld      hl,td_c0
        add     a,(hl)
        ld      b,a
        ld      a,(dh_ty)
        ld      c,a
        call    tile_addr
        ld      a,(td_nc)
        ld      b,a
dho_col:
        ld      a,(hl)
        and     #30                     ; bits κατοχής
        jr      nz,dho_yes
        inc     hl
        djnz    dho_col
        ld      a,(dh_ty)
        inc     a
        ld      (dh_ty),a
        ld      a,(dh_rows)
        dec     a
        ld      (dh_rows),a
        jr      nz,dho_row
        xor     a
        ret
dho_yes:
        ld      a,1
        ret

; dk_clamp — (HL) = αρχή 3 πλακιδίων, B = όριο κάδρου.
; Out: C = αρχή κομμένη, B = πλήθος (0 = εκτός κάδρου).
dk_clamp:
        ld      a,(hl)
        ld      c,3
        bit     7,a
        jr      z,dkc_pos
        ; αρνητική αρχή: κόψε από μπροστά
        neg
        cp      3
        jr      nc,dkc_out
        ld      e,a
        ld      a,3
        sub     e
        ld      c,a
        xor     a
dkc_pos:
        ld      d,a                     ; αρχή
        add     a,c
        cp      b
        jr      c,dkc_ok
        ld      a,b
        sub     d
        jr      c,dkc_out
        jr      z,dkc_out
        ld      c,a
dkc_ok:
        ld      b,c
        ld      c,d
        ret
dkc_out:
        ld      b,0
        ld      c,0
        ret

dirty_jmp:
        dw      dh_slot, dh_mach, dh_icon, dh_conn, dh_tile

; Μετρημένο κόστος ανά είδος, σε us. Ο προϋπολογισμός δεν έχει ρολόι να
; κοιτάξει· έχει αυτόν τον πίνακα, και το test_dirty τον ελέγχει.
; ΜΕΤΡΗΜΕΝΑ, όχι εκτιμημένα. Το §8.5 έλεγε 64 / 530 / 800 / 450 / 1.600 και τα
; πέντε βγήκαν χαμηλά, από 2x ως 21x: το blit δεν είναι το κόστος — είναι η
; προετοιμασία (σελιδοποίηση, εγγραφή θόλου, πλαίσιο, έλεγχος ορατότητας) που
; πληρώνεται ολόκληρη για να γραφτούν δεκαέξι bytes.
dirty_cost:
        dw      1500                    ; θέση δακτυλίου — 16 bytes αδιαφανή
        dw      5000                    ; μηχάνημα ή φυτό — 132 bytes
        dw      2000                    ; εικονίδιο δωματίου — ως 200 bytes
        dw      3000                    ; πόρτα — 16 ζεύγη με μάσκα
        dw      11000                   ; tile + γείτονες σε ελεύθερο έδαφος

dirty_ring: defs DIRTY_N * DIRTY_REC
dirty_head: db 0
dirty_num:  db 0
dirty_over: db 0
dt_spent:   dw 0
dt_new:     dw 0
dp_kind:    db 0
dt_kind:    db 0
dt_a:       db 0
dt_b:       db 0
dk_c0:      db 0
dk_r0:      db 0
dh_ty:      db 0
dh_rows:    db 0
