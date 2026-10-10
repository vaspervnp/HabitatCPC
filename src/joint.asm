; ---------------------------------------------------------------------------
; joint.asm — οι αρμοί διαδρόμου-δακτυλίου (βήμα 96).
;
; Ο παίκτης: «οι διάδρομοι να μπαίνουν 1 pixel πιο μέσα». Ο διάδρομος
; ζωγραφίζεται κάτω από τα κελύφη και σταματά στο εξωτερικό χείλος του
; δακτυλίου, όπου το λευκό περίγραμμα τον χώριζε από το γκρι του δακτυλίου.
; Ο αρμός βάφει γκρι τα pixels αυτού του περιγράμματος που ακουμπούν το γκρι
; του διαδρόμου, ΠΑΝΩ από το κέλυφος: το βήμα 3 του θόλου, εκεί που ως το 95
; ήταν οι πόρτες, και με την ίδια λογιστική — το dome_conn λέει ποιες
; κατευθύνσεις κάθε θόλου έχουν διάδρομο. Τα σχέδια (jnt_v, jnt_h, jnt_d) τα
; φτιάχνει το tools/pack.py στην τράπεζα 5.
;
; ΣΤΟ b6code (src/main.asm): τρέχει μόνο με την 6 στο παράθυρο — στη μέτρηση
; του ευρετηρίου (ob_corr), στο ob_index, στο ob_fittings και στον χειριστή
; της λίστας (dt_prep) — και ό,τι καλεί γυρίζει με την 6 μέσα: το ob_put_in
; σελιδοποιεί την 5 για το σχέδιο και ξαναβάζει την 6 πριν επιστρέψει. Οι
; δοκιμαστικές εκδόσεις (tests/objtest.asm, uitest.asm) το έχουν επίπεδο.
; ---------------------------------------------------------------------------

; jt_mark — στη μέτρηση του ευρετηρίου των διαδρόμων (ob_corr με ob_meas):
; τα bits του a και του b στο dome_conn. Ο a στην κατεύθυνση του πρώτου
; τρεξίματος, ο b στην αντίθετη του ΤΕΛΕΥΤΑΙΟΥ — της συνέχειας, αν υπάρχει
; (oc_cont, oc_cr) — και μόνο αν είναι θόλος: το airlock δεν έχει δακτύλιο.
; Ο κανόνας είναι του ob_conn_scan του βήματος 95, χωρίς δικό του πέρασμα
; στους 96 διαδρόμους: η μέτρηση τους διαβάζει ήδη έναν έναν.
jt_mark:
        ld      a,(c_rec+C_A)
        ld      c,a
        ld      a,(c_rec+C_DIR)
        call    jtm_set
        ld      a,(c_rec+C_B)
        cp      MAX_DOME
        ret     nc
        ld      c,a
        ld      a,(oc_cont)
        or      a
        ld      a,(c_rec+C_DIR)
        jr      z,jtm_b
        call    jtm_bend                ; κοντή στροφή; (βήμα 97, src/object.asm)
        ld      a,(c_rec+C_B)
        ld      c,a
        ld      a,(oc_cr+C_DIR)
jtm_b:
        add     a,4                     ; η αντίθετη φορά για τον b
; jtm_set — C = θόλος, A = κατεύθυνση (μόνο τα bits 0-2): ανάβει το bit.
;
; ΜΕ ΤΟ bit_tab, ΟΧΙ ΜΕ ΒΡΟΧΟ (βήμα 97): το rlca/djnz ήταν 3,5 ms στο
; χειρότερο ευρετήριο διαδρόμων, δύο κλήσεις ανά διάδρομο, και πλήρωσε τις
; κοντές στροφές (src/bend.asm). Δεκαέξι bits γιατί ο πίνακας πέφτει όπου
; πέφτει στις δοκιμαστικές εκδόσεις.
jtm_set:
        and     7
        ld      hl,bit_tab              ; src/entity.asm
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)                  ; 1 << κατεύθυνση
        ld      hl,dome_conn
        ld      b,0
        add     hl,bc
        or      (hl)
        ld      (hl),a
        ret

; jt_dome — οι αρμοί του θόλου d_id, από το dome_conn. Απαιτεί το πλαίσιο
; (ob_getdome, ob_vis).
jt_dome:
        ld      a,(d_id)
        ld      c,a
        ld      b,0
        ld      hl,dome_conn
        add     hl,bc
        ld      a,(hl)
        or      a                       ; και CY = 0 για το πρώτο rra
        ret     z
        ld      c,b                     ; κατεύθυνση 0
jtd_lp:
        rra
        jr      nc,jtd_next
        push    af
        push    bc
        ld      a,c
        call    jt_one
        pop     bc
        pop     af
jtd_next:
        inc     c
        or      a                       ; CY = 0: το rra σπρώχνει μηδενικά
        jr      nz,jtd_lp
        jp      jtd_end                 ; και οι κοντές στροφές (src/object.asm)

; jt_one — ο αρμός του θόλου (d_rec, το πλαίσιο d_fx, d_fy) στην κατεύθυνση A:
; ένα σχέδιο της τράπεζας 5 στη θέση του jt_tab (tools/pack.py), με κάθετο
; καθρέφτισμα για τα νότια. Το οριζόντιο θα ήθελε το flip_mode0 της 6, που δεν
; φαίνεται όσο η 5 είναι μέσα: τα ανατολικά έχουν δικά τους σχέδια.
;
; ΧΩΡΙΣ ΤΟ and 7 του 96, και με sbc αντί για ld a,0 · rla · add a,a (βήμα
; 97): 3 µs ανά αρμό, 120 στις πέντε κάμερες του tests/test_object.py, που
; πληρώνουν το jp στο jtd_end. Το A είναι πάντα 0-7: το c του jt_dome, το
; dt_b ενός DK_CONN (crr_conns, jtb_cc).
jt_one:
        ld      c,a
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,c                     ; 8 x μέγεθος + κατεύθυνση
        ld      c,a
        add     a,a
        add     a,c                     ; x 3
        ld      c,a
        ld      b,0
        ld      hl,jt_tab
        add     hl,bc
        ld      a,(hl)                  ; x, σε bytes
        inc     hl
        ld      e,(hl)                  ; γραμμή
        inc     hl
        ld      d,(hl)                  ; σχέδιο | 128
        ld      hl,(d_fx)
        call    ob_addu
        ld      (ob_x),hl
        ld      a,e
        ld      hl,(d_fy)
        call    ob_addu
        ld      (ob_y),hl
        ld      a,d
        add     a,a                     ; CY = το κάθετο καθρέφτισμα
        push    af
        add     a,a                     ; σχέδιο x 4 (το bit 7 έφυγε)
        ld      c,a
        ld      hl,jt_spr
        add     hl,bc
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      (ob_src),de
        ld      e,(hl)                  ; πλάτος
        inc     hl
        ld      d,(hl)                  ; ύψος
        ex      de,hl
        pop     af
        sbc     a,a                     ; #FF με το καθρέφτισμα
        and     2                       ; bit 1 του ob_fl: κάθετα
        ld      c,PAGE_B5
        jp      ob_put_in

        include "../build/joint_tab.asm"
