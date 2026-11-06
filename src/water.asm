; water.asm — το ισοζύγιο του ρεύματος και του νερού όπως στο Planetbase, στις
; ουρές των σελίδων πεδίων της τράπεζας 6 (βήμα 189, DESIGN §6.5, §9.2).
;
; Μετά το ec_setfull (src/full6.asm), στο τέλος της δεύτερης ουράς και στην
; τρίτη και την τέταρτη. Τρέχουν με την 6 μέσα: από τον κύκλο ροής
; (src/flow.asm) και από το wheel_reset. Οσα γράφουν είναι στην τράπεζα 0
; (hu_pwr, hu_h2o, ew_last, ec_wcap, src/stock.asm· erp_go, src/econ.asm·
; vie_w, src/visit0.asm), στις συνταγές (G_recipes, στην κεντρική μνήμη) και
; στο b6code (nds_wld).

; ew_reset — από το wheel_reset, A = 0: η αποθήκη χωρά (ec_setfull) και το
; νερό φτάνει για όλα ως τον πρώτο κύκλο ροής, όπως το ec_full από το βήμα
; 122. Το ταβάνι EC_CAP, και καμία πτώση: το ew_last είναι το νερό τώρα. Στην
; αρχή κάθε παιχνιδιού, στην αποικία δοκιμών και σε κάθε φόρτωμα.
ew_reset:
        call    ec_setfull
        ld      hl,EC_CAP
        ld      (ec_wcap),hl
        ld      hl,(EC_STOCK + 2 * S_WATER)
        ld      (ew_last),hl
        ld      a,255                   ; «πολύ νερό»
        ld      c,0                     ; δεν έπεσε
        jp      ewc_rules

        B6T_PIECE 2

; ew_cycle — μία φορά ανά κύκλο ροής, μετά τις αντλίες (ή στη θέση τους, αν
; σταμάτησαν). Τα δύο πρόσημα, και ποιος παίρνει νερό όταν λείπει, η σειρά
; του παίκτη: κάτω από 1,5 x ζωντανούς (R1) σταματούν οι κήποι και το
; VITROMEAT, κάτω από τους ζωντανούς (R2) και το ποτό στο κυλικείο, των
; αποίκων και των επισκεπτών· οι μηχανές OXYGEN πίνουν ως την τελευταία μονάδα. Οι ζωντανοί είναι του προηγούμενου
; κύκλου (το ef_o2 τους μετρά μετά). Χαλάει AF, BC, DE, HL.
ew_cycle:
        ld      hl,(EC_PPROD)
        ld      de,(EC_PUSE)
        or      a
        sbc     hl,de                   ; CY: ζητούν περισσότερα απ' όσα βγαίνουν
        sbc     a,a                     ; το πρόσημο μέσα, όχι κλήση: 7 us
        and     '-' - '+'
        add     a,'+'
        ld      (hu_pwr + 3),a
        ld      hl,(EC_STOCK + 2 * S_WATER)
        ld      de,(ew_last)
        ld      (ew_last),hl
        or      a
        sbc     hl,de                   ; CY: έπεσε από τον προηγούμενο κύκλο
        sbc     a,a
        ld      c,a                     ; #FF αν έπεσε
        ld      hl,(EC_STOCK + 2 * S_WATER)
        inc     h
        dec     h
        ld      a,l
        jr      z,ewc_rules
        ld      a,255                   ; 256 ή πάνω: πάνω από κάθε όριο
; ewc_rules — A = το νερό ως 255, C = #FF αν έπεσε.
ewc_rules:
        ld      b,a
        ld      a,(EC_ALIVE)
        ld      d,a                     ; R2, ως 160
        srl     a
        add     a,d
        ld      e,a                     ; R1, ως 240
        ld      a,b
        ld      hl,256 * VW_Q + 1       ; το VITROMEAT θέλει VW_Q, ο κήπος 1
        cp      e                       ; CY: κάτω από R1
        jp      ewc_r1                  ; η επόμενη ουρά, με το CY

        B6T_PIECE 3

ewc_r1:
        jr      nc,ewc_q
        ld      hl,#FFFF                ; 255: κανένα νερό δεν φτάνει
        ld      c,h                     ; και το πρόσημο: λείπει
ewc_q:
        ld      a,h
        ld      (G_recipes + 10 * MT_VITRO + 1),a
        ld      a,l
        ld      (erp_go + 1),a
        ld      a,b
        cp      d                       ; CY: κάτω από R2
        sbc     a,a
        ld      b,a
        and     #C9 ^ #3E
        xor     #3E                     ; ret, ή το ld a,S_WATER που ήταν
        ld      (nds_wld),a
        ld      a,b                     ; ΚΑΙ ΤΟ ΓΕΥΜΑ ΤΩΝ ΕΠΙΣΚΕΠΤΩΝ (src/visit0.asm),
        and     #18 ^ #28               ; που πίνει κι αυτό: «jr vi_sad»,
        xor     #28                     ; ή το «jr z» που ήταν
        ld      (vie_w),a
        ld      a,c                     ; #FF: «-»
        and     '-' - '+'
        add     a,'+'
        ld      (hu_h2o + 3),a
        ret
        assert  S_WATER == 0
