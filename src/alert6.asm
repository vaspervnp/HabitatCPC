; alert6.asm — η γραμμή ειδοποιήσεων λέει ΠΟΙΑ μηχανή (βήμα 119, DESIGN §9.2).
;
; Ως το βήμα 118 η γραμμή έλεγε την κατάσταση αλλά όχι το πράγμα: «NO
; ENGINEER» χωρίς να λέει τι περιμένει, και μια χαλασμένη μηχανή δεν την έλεγε
; καθόλου — μόνο το κόκκινο σημάδι πάνω στον θόλο (βήμα 100), αν ήταν στο
; κάδρο. Οι αποφάσεις του παίκτη:
;
;   NO ENGINEER  και τι περιμένει: μια μηχανή που ήρθαν τα υλικά της και θέλει
;                να στηθεί («NO ENGINEER OXYGEN»), ή ένα κτίριο-εργοτάξιο
;                («NO ENGINEER SOLAR», «NO ENGINEER DOME M»). Η πρώτη Build του
;                πίνακα που έχει κάτι να ονομάσει.
;   BROKEN       και ποια μηχανή, αμέσως μετά το NO ENGINEER στη σειρά: όσο μια
;                μηχανή — όχι φυτό: το μαραμένο φυτό δεν είναι «χαλασμένο» —
;                έχει υγεία 0. Μία, η πιο πρόσφατη που χάλασε.
;
; ΤΑ ΟΝΟΜΑΤΑ ΥΠΗΡΧΑΝ ΗΔΗ: των μηχανών στην τράπεζα 7 (t_f_names, οκτώ bytes, του
; FIT και του εμπορίου), των κτιρίων στην τράπεζα 2 (t_dome_s, t_solar, δέκα
; bytes, του καταλόγου και του INFO). Η γραμμή έχει 19 στήλες, και το «NO
; ENGINEER » αφήνει επτά: όσο το μακρύτερο όνομα μηχανής· από τα κτίρια το
; COLLECTOR και το EXTRACTOR κόβονται σε COLLECT και EXTRACT.
;
; Η ΧΑΛΑΣΜΕΝΗ ΜΗΧΑΝΗ ΧΩΡΙΣ ΣΑΡΩΜΑ ΣΕ ΚΑΘΕ ΤΙΚ. Ενα σάρωμα του πίνακα εργασιών
; κάθε 16 frames θα κόστιζε ~0,4 ms και στη συνηθισμένη γραμμή, «ALL SYSTEMS
; OK». Το al_brk κρατά ΜΙΑ (θόλος, υποδοχή), και το γράφουν δύο σημεία:
;   ec_break_d  εκεί χαλάει μια μηχανή (φθορά και μετεωρίτης): η πιο πρόσφατη
;               λέγεται αμέσως, όποια κι αν κρατιόταν.
;   jp_one      η δημοσίευση των εργασιών (src/jobs.asm), που επισκέπτεται τους
;               θόλους κυκλικά και βρίσκει τη χαλασμένη για τη Repair: αν δεν
;               κρατιέται καμία, κρατά αυτή. Ετσι λέγεται η δεύτερη όταν
;               επισκευαστεί η πρώτη — η Repair της μπορεί να μην είναι ακόμη
;               στον πίνακα εκείνη τη στιγμή, γιατί ένα σάρωμα του πίνακα δεν
;               θα την έβρισκε — και μετά από φόρτωση, και με γεμάτο πίνακα.
; Το HUD ρωτά σε κάθε τικ μόνο αν η κρατημένη είναι ακόμη χαλασμένη μηχανή
; (al_is)· όταν πάψει — επισκευή, αφαίρεση, κατεδάφιση, ένα φυτό που μαράθηκε
; — καμία, ως την επόμενη επίσκεψη του jp_one σε θόλο με χαλασμένη.
;
; ΣΤΟ b6code: διαβάζει θόλους και δομές με την 6 μέσα (το hud_alert τη βάζει,
; hd_b6). Ο πίνακας εργασιών είναι στην τράπεζα 2.

; ---------------------------------------------------------------------------
; al_wait — τι περιμένει μηχανικό. A = 7 και HL = όνομα μηχανής (τράπεζα 7),
; A = 2 και HL = όνομα κτιρίου (τράπεζα 2, γεμισμένο με κενά), ή A = 0.
; ---------------------------------------------------------------------------
al_wait:
        ld      hl,G_job_tbl
        ld      de,JOB_REC
        ld      b,MAX_JOB
alw_lp:
        ld      a,(hl)                  ; J_KIND
        or      a                       ; J_BUILD
        jr      z,alw_job
alw_nx:
        add     hl,de
        djnz    alw_lp
        xor     a
        ret
alw_job:
        push    hl
        push    bc
        inc     hl
        ld      a,(hl)                  ; J_NODE
        call    alw_node
        pop     bc
        or      a
        jr      nz,alw_got
        pop     hl
        ld      de,JOB_REC
        jr      alw_nx
alw_got:
        pop     de                      ; ο δείκτης της εργασίας, δεν χρειάζεται
        ret

; alw_node — A = ο κόμβος μιας Build -> A = 7 / 2 και HL, ή A = 0.
alw_node:
        cp      MAX_DOME
        jr      nc,alw_st
        call    ob_domeadr              ; HL -> D_CX
        push    hl
        pop     ix
        ld      a,(ix+D_STATE)
        cp      DS_BUILDING
        jr      nz,alw_mach
        ld      a,(ix+D_SIZE)           ; εργοτάξιο θόλου: DOME S, M, L
        ld      hl,t_dome_s
        jr      alw_x10
alw_mach:
        ; θόλος σε λειτουργία: η πρώτη μηχανή που ήρθαν τα υλικά της (4 + 32k:
        ; το bit 7 σβηστό, όχι 0, τα bits 0-1 σβηστά — src/install.asm)
        ld      b,MACH_SLOTS
alwm_lp:
        ld      a,(ix+D_MACH)
        cp      FT_CLS
        jr      nc,alwm_nx              ; φυτό, ή άδεια
        ld      e,a
        ld      a,(ix+D_HEALTH)
        or      a
        jr      z,alwm_nx               ; χαλασμένη
        jp      m,alwm_nx               ; δουλεύει
        and     MACH_OWED & 3
        jr      z,al_mname              ; στήνεται: αυτή
alwm_nx:
        inc     ix
        djnz    alwm_lp
        xor     a
        ret
alw_st:
        add     a,a
        add     a,a                     ; 4 x κόμβος = 4 x δομή σε 8 bits
        add     a,STB_C + ST_KIND / 2
        ld      l,a
        ld      h,STB_H
        add     hl,hl                   ; -> ST_KIND (src/const.asm, βήμα 154)
        ld      a,(hl)                  ; το είδος, με τη σειρά του t_solar
        ld      hl,t_solar
alw_x10:
        add     a,a
        ld      e,a
        add     a,a
        add     a,a
        add     a,e                     ; x10
        call    ob_addu
        ld      a,2
        ret

; al_mname — E = μηχανή -> HL = το όνομά της (τράπεζα 7), A = 7.
al_mname:
        ld      a,e
        add     a,a
        add     a,a
        add     a,a                     ; x8 (ως 11 x 8)
        ld      hl,t_f_names
        call    ob_addu
        ld      a,7
        ret

; ---------------------------------------------------------------------------
; al_broken — μια χαλασμένη μηχανή: A = 7 και HL = το όνομά της, ή A = 0.
; ---------------------------------------------------------------------------
; Το hud_alert την καλεί μόνο όταν ο θόλος του al_brk δεν είναι 255.
al_broken:
        ld      bc,(al_brk)             ; C = υποδοχή, B = θόλος
        call    al_is
        jr      z,al_mname              ; ακόμη χαλασμένη
        ld      a,255
        ld      (al_brk + 1),a          ; έπαψε: καμία, ως να την πει το jp_one
        xor     a
        ret

; al_is — B = θόλος, C = υποδοχή: Z και E = η μηχανή αν είναι χαλασμένη
; μηχανή σε θόλο σε λειτουργία· αλλιώς NZ. Κρατά BC. Ο θόλος είναι πάντα
; θόλος: το eb_d του ec_break_d ή το jb_d του jp_one.
al_is:
        ld      a,b
        call    ob_domeadr              ; HL -> D_CX· κρατά το BC
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      DS_ACTIVE
        ret     nz
        ld      a,c
        add     a,D_MACH
        ld      e,a
        ld      d,0
        add     hl,de                   ; HL -> η υποδοχή
        ld      a,(hl)
        cp      FT_CLS
        jr      nc,ali_no               ; φυτό, ή άδεια
        ld      e,a
        ld      a,D_HEALTH - D_MACH
        call    ob_addu
        ld      a,(hl)
        or      a                       ; Z: χαλασμένη
        ret
ali_no:
        or      1                       ; NZ
        ret

        assert  J_BUILD == 0 && J_KIND == 0 && J_NODE == 1
        assert  MACH_SLOTS == 8 && D_HEALTH - D_MACH == MACH_SLOTS
        assert  MACH_OWED & 3 == 3 && (MACH_READY & 3) == 0
        assert  MAX_DOME == 64 && (ST_KIND & 1) == 0
        assert  t_dome_m == t_dome_s + 10 && t_dome_l == t_dome_m + 10
