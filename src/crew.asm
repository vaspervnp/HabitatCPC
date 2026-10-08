; crew.asm — ποιοι έρχονται με το πλοίο αποίκων (βήμα 91, DESIGN §6.11).
;
; Ο ΠΑΙΚΤΗΣ ΟΡΙΖΕΙ ΠΟΣΟΣΤΟ ΑΝΑ ΕΙΔΙΚΟΤΗΤΑ, ανά 10% και με άθροισμα πάντα 100:
; το EC_LAND, πέντε bytes σε δέκατα (εργάτης, μηχανικός, βιολόγος, γιατρός,
; φρουρός), με άθροισμα 10. Το αλλάζει η γραμμή του πλοίου (cw_open), και
; σώζεται με την οικονομία.
;
; ΚΑΘΕ ΝΕΟΦΕΡΜΕΝΟΣ ΠΑΙΡΝΕΙ ΤΗΝ ΕΙΔΙΚΟΤΗΤΑ ΠΟΥ ΛΕΙΠΕΙ ΠΕΡΙΣΣΟΤΕΡΟ από την
; αποικία. Αν ζουν N άνθρωποι και c_r από την r, μετά από αυτόν θα έπρεπε να
; είναι t_r (N + 1) / 10, και λείπουν d_r = t_r (N + 1) - 10 c_r δέκατα. Το
; μεγαλύτερο κερδίζει, το πρώτο σε ισοπαλία, και έτσι αναπληρώνονται μόνοι
; τους και οι θάνατοι. Το άθροισμα των d_r είναι 10: κάποιο είναι πάντα
; θετικό, και ειδικότητα με 0% (d <= 0) δεν έρχεται ποτέ.
;
; ΤΑ ΠΛΟΙΑ ΔΕΝ ΦΕΡΝΟΥΝ ΡΟΜΠΟΤ (η απόφαση του παίκτη). Ως το βήμα 90 ο ρόλος
; ήταν η ταυτότητα & 7, και οι τρεις στους οκτώ ήταν ρομπότ.

CW_N        equ 5                       ; ειδικότητες· οι ρόλοι 5-7 είναι ρομπότ
CW_BIAS     equ 2048                    ; d + 2048 > 0 πάντα: 10 c <= 1270
CW_REC      equ G_crew                  ; 8 x [d + CW_BIAS (2), t, -], ρόλοι 0-7
CW_BP       equ G_crew + 32             ; το κάτω byte της εγγραφής του καλύτερου
        assert  (G_crew & 255) + 33 <= 256  ; μία σελίδα (tools/pack.py)

; ---------------------------------------------------------------------------
; cw_count — ship_crew, μία φορά ανά πλοίο, πριν από τις γεννήσεις, με την
; τράπεζα 6 μέσα (οι πράκτορες). A = ο πρώτος νεκρός (128: κανείς) — από εκεί
; ψάχνει θέσεις το ship_crew. Χαλάει όλους.
;
;   1. οι εγγραφές: c = 0 στη θέση του d, και t από το EC_LAND
;   2. οι ζωντανοί ανά ρόλο. Τα ρομπότ (5-7) μετριούνται κι αυτά, στις τρεις
;      εγγραφές που δεν διαβάζει κανείς (ούτε μηδενίζονται: ένα byte που
;      γυρίζει δεν πειράζει): ένα cp λιγότερο σε κάθε ζωντανό.
;      ΣΤΑΜΑΤΑ ΜΟΛΙΣ ΜΕΤΡΗΣΕΙ EC_ALIVE: ο μετρητής δεν είναι ποτέ κάτω από τους
;      ζωντανούς (οι γεννήσεις τον ανεβάζουν αμέσως, οι θάνατοι τον κατεβάζουν
;      στην επόμενη μέτρηση της θέσης 12), άρα μετά από αυτόν όλοι είναι νεκροί.
;      Χωρίς αυτό μια αποικία τεσσάρων έψαχνε και τους 124 νεκρούς: 4.937 us
;      η προσγείωση αντί για 3.198 (tests/test_crew.py, το αρνητικό του κόστους).
;   3. d + CW_BIAS = CW_BIAS - 10 c + t N για τον καθένα: το cw_pick προσθέτει
;      t πριν από κάθε σύγκριση, άρα ο πρώτος βλέπει t (N + 1).
; ---------------------------------------------------------------------------
cw_count:
        ld      hl,CW_REC
        ld      de,EC_LAND
        ld      b,CW_N                  ; 5-7: ό,τι είναι, δεν διαβάζεται
cwc_z:
        xor     a
        ld      (hl),a
        inc     l
        ld      (hl),a
        inc     l
        ld      a,(de)
        ld      (hl),a
        inc     l
        inc     l
        inc     de
        djnz    cwc_z
        ld      a,(EC_ALIVE)
        ld      b,a                     ; B = όσοι ζωντανοί μένουν να βρεθούν
        ld      c,128                   ; C = ο πρώτος νεκρός: κανείς ακόμη
        ld      de,G_agent_fields       ; οι σημαίες, E = ταυτότητα
        ld      h,CW_REC >> 8
cwc_lp:
        ld      a,(de)
        rra                             ; F_ALIVE
        jr      c,cwc_a
        bit     7,c
        jr      z,cwc_n
        ld      c,e
        jr      cwc_n
cwc_a:
        set     7,e
        ld      a,(de)                  ; ρόλος 0-7
        res     7,e
        add     a,a
        add     a,a
        add     a,CW_REC & 255
        ld      l,a
        inc     (hl)
        dec     b
        jr      z,cwc_e
cwc_n:
        inc     e
        jp      p,cwc_lp                ; E < 128
        jr      cwc_d
cwc_e:
        bit     7,c
        jr      z,cwc_d
        ld      c,e
        inc     c                       ; ο αμέσως επόμενος (128 αν ήταν ο 127)
cwc_d:
        ld      a,c
        push    af                      ; ο πρώτος νεκρός, για το ship_crew
        ; N = c_0 + ... + c_4
        ld      l,CW_REC & 255
        ld      b,CW_N
        xor     a
cwn_lp:
        add     a,(hl)
        inc     l
        inc     l
        inc     l
        inc     l
        djnz    cwn_lp
        ld      c,a                     ; BC = N
        ld      l,CW_REC & 255
cwi_lp:
        ld      e,(hl)                  ; c
        push    hl
        inc     l
        inc     l
        ld      a,(hl)                  ; t
        ld      d,0
        ld      h,d
        ld      l,e
        add     hl,hl
        add     hl,hl
        add     hl,de
        add     hl,hl                   ; 10 c (CY = 0)
        ex      de,hl
        ld      hl,CW_BIAS
        sbc     hl,de
        or      a
        jr      z,cwi_s
cwi_t:
        add     hl,bc                   ; + t N
        dec     a
        jr      nz,cwi_t
cwi_s:
        ex      de,hl
        pop     hl
        ld      (hl),e
        inc     l
        ld      (hl),d
        inc     l
        inc     l
        inc     l
        ld      a,l
        cp      (CW_REC + 4 * CW_N) & 255
        jr      nz,cwi_lp
        pop     af
        ret

; ---------------------------------------------------------------------------
; cw_pick — μία γέννηση (sh_born): A = η ειδικότητα. Κρατά το HL. d += t σε
; όλους (ένας ακόμη στην αποικία), ο μεγαλύτερος κερδίζει — ο πρώτος σε
; ισοπαλία — και χάνει 10 (ένας ακόμη της ειδικότητάς του). Ως την πρώτη γραφή
; του βήματος ξαναϋπολόγιζε κάθε d από την αρχή, 858 us η επιλογή.
; ---------------------------------------------------------------------------
cw_pick:
        push    hl
        ld      bc,0                    ; BC = το καλύτερο: κάθε d + CW_BIAS > 0
        ld      hl,CW_REC
cwk_lp:
        ld      e,(hl)
        inc     l
        ld      d,(hl)
        inc     l
        ld      a,(hl)                  ; t
        add     a,e
        ld      e,a
        jr      nc,cwk_1
        inc     d
cwk_1:
        dec     l
        ld      (hl),d
        dec     l
        ld      (hl),e                  ; d += t
        ld      a,c
        sub     e
        ld      a,b
        sbc     a,d                     ; CY: d > το καλύτερο (ίσο: ο πρώτος μένει)
        jr      nc,cwk_x
        ld      b,d
        ld      c,e
        ld      a,l
        ld      (CW_BP),a
cwk_x:
        ld      a,l
        add     a,4
        ld      l,a
        cp      (CW_REC + 4 * CW_N) & 255
        jr      nz,cwk_lp
        ld      a,(CW_BP)
        ld      l,a
        ld      a,(hl)
        sub     10
        ld      (hl),a
        jr      nc,cwk_r
        inc     l
        dec     (hl)
cwk_r:
        ld      a,(CW_BP)
        sub     CW_REC & 255
        rrca
        rrca                            ; r
        pop     hl
        ret

        ifdef HAS_SIM
; ---------------------------------------------------------------------------
; Η ΓΡΑΜΜΗ ΤΟΥ ΠΛΟΙΟΥ: μία υπο-κατάσταση του μενού ενεργειών (UI_ACT, το
; ac_mode του src/act.asm), όπως η διαχείριση. Το κουμπί του πλοίου και το C
; την ανοίγουν.
;
;   σειρά 3   SHIP UP/DN=10% FIRE=CALL ESC=BACK  PAUSE
;   σειρά 4    >WRK 20 ENG 20 BIO 20 MED 20 GRD 20
;
; ΑΡΙΣΤΕΡΑ/ΔΕΞΙΑ διαλέγουν ειδικότητα. ΠΑΝΩ: +10% σε αυτήν, -10% από τη
; μεγαλύτερη από τις άλλες. ΚΑΤΩ: -10% σε αυτήν, +10% στη μικρότερη από τις
; άλλες. Σε ισοπαλία η πρώτη. Ετσι το άθροισμα μένει 100 και το κόστος μιας
; αλλαγής πέφτει εκεί που υπάρχει περισσότερο. FIRE καλεί το πλοίο, ESC κλείνει.
; ---------------------------------------------------------------------------
CW_MODE     equ 2                       ; ac_mode: 0 ομάδες, 1 διαχείριση

; cw_ud — από το cw_tick (src/act.asm): A = 1 πάνω, 2 κάτω (3: κάτω).
cw_ud:
        ld      b,a                     ; 1 πάνω, 2 κάτω (3: κάτω)
        ld      a,(cw_sel)
        ld      e,a
        ld      d,0
        ld      hl,EC_LAND
        add     hl,de                   ; HL -> t_s
        ld      c,d                     ; C = 0: η μεγαλύτερη
        ld      a,(hl)
        djnz    cwu_dn
        cp      10
        ret     nc
        inc     (hl)
        call    cw_ext
        dec     (hl)
        jp      cw_draw                 ; src/act.asm
cwu_dn:
        or      a
        ret     z
        dec     (hl)
        dec     c                       ; #FF: η μικρότερη
        call    cw_ext
        inc     (hl)
        jp      cw_draw

; cw_ext — E = s, C = 0 ή #FF: HL -> το t της μεγαλύτερης (ή, με το xor, της
; μικρότερης) από τις άλλες τέσσερις. Από το τέλος προς την αρχή, και το ίσο
; κερδίζει: σε ισοπαλία μένει η πρώτη.
cw_ext:
        ld      hl,EC_LAND + CW_N - 1
        ld      b,CW_N
        ld      d,0
        inc     e                       ; E = s + 1, όπως το B
cwe_lp:
        ld      a,b
        cp      e
        jr      z,cwe_n                 ; όχι η ίδια
        ld      a,(hl)
        xor     c
        cp      d
        jr      c,cwe_n
        ld      d,a
        ld      (cw_ptr),hl
cwe_n:
        dec     hl
        djnz    cwe_lp
        ld      hl,(cw_ptr)
        ret

; cw_panel — από το ac_panel, στη σειρά 3, στήλη 0. Οι οδηγίες στη σειρά 3
; και η λίστα στη 4, που έχει 40 στήλες: πέντε φορές «>WRK 20» είναι 35, και
; στη σειρά 3 θα κολλούσαν στην ταχύτητα (35-39) — οι δύο σειρές είναι μία
; γραμμή οθόνης. Τελειώνει όπως εκείνο.
cw_panel:
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; τα κείμενα στην 7
        ld      hl,t_cw_keys
        call    hud_text
        ld      b,35
        call    hud_to
        ld      a,4
        call    hud_go
        call    hud_space               ; ένα κενό μετά το PAUSE
        ld      hl,t_cw_names
        xor     a
cwp_lp:
        ld      (cw_i),a
        push    hl
        ld      hl,cw_sel
        cp      (hl)
        ld      a,'>'
        jr      z,cwp_m
        ld      a,' '
cwp_m:
        call    hud_char
        pop     hl
        call    hud_text                ; «WRK»
        inc     hl
        push    hl
        ld      a,(cw_i)
        add     a,EC_LAND & 255
        ld      l,a
        ld      h,EC_LAND >> 8
        ld      a,(hl)
        add     a,a
        ld      b,a
        add     a,a
        add     a,a
        add     a,b                     ; % = 10 t
        ld      b,3
        call    hud_numa                ; «  0», « 20», «100»
        pop     hl
        ld      a,(cw_i)
        inc     a
        cp      CW_N
        jr      c,cwp_lp
        jp      acp_end                 ; src/act.asm

cw_sel:     db 0
cw_i:       db 0
cw_ptr:     dw 0

        assert  (EC_LAND & 255) + CW_N <= 256
        assert  A_UP == 0 && A_DOWN == 1        ; το djnz του cw_ud
        endif
