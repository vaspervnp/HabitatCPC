; hud.asm — οι δύο λωρίδες Mode 1, πάνω και κάτω από το κάδρο (DESIGN §9.2).
;
; ΤΟ HUD ΕΙΝΑΙ ΣΕ MODE 1 ΑΠΟ ΤΟ ΒΗΜΑ 83. Δύο λωρίδες, με δική τους παλέτα, που
; τις στήνει η διακοπή (src/isr.asm, §8.1):
;
;   γραμμές   0- 15   πάνω λωρίδα   σειρές οθόνης 0-1    (T0, T1)
;   γραμμές  16-175   κάδρο, Mode 0 σειρές οθόνης 2-21
;   γραμμές 176-199   κάτω λωρίδα   σειρές οθόνης 22-24  (B0, B1, B2)
;
; Οι πέντε ΛΟΓΙΚΕΣ σειρές των σαράντα στηλών μένουν ό,τι ήταν, και ο κώδικας
; που τις γράφει δεν ξέρει πού κάθονται: οι 0 και 1 μοιράζονται την T0 (στήλες
; 0-39 και 40-79), η 2 είναι η T1 και οι 3 και 4 μοιράζονται την B2. Η B0 και
; η B1 είναι για τα κουμπιά (βήμα 84) και ως τότε μένουν μαύρες.
;
; Το HUD ζει στην ΙΔΙΑ σελίδα με το κάδρο (§8.1): ο CRTC κλειδώνει τη διεύθυνση
; έναρξης μία φορά ανά frame. Η πάνω λωρίδα είναι οι 160 bytes ΠΡΙΝ από το
; cam_p (το R12/R13 δείχνει 80 λέξεις πίσω), η κάτω τα 240 μετά το cam_p+1600.
; Οταν σκρολάρει η κάμερα, το δαχτυλίδι γυρίζει και οι λωρίδες ΜΕΤΑΚΙΝΟΥΝΤΑΙ
; μαζί του (hud_move): ίδια bytes, άλλη θέση.
;
; Η γραμματοσειρά είναι η 4x8 του Mode 0 ξαναγραμμένη σε Mode 1 από το
; tools/pack.py (font_m1): ένα byte ανά γραμμή, μελάνι στο pen 3. Ογδόντα
; στήλες στη γραμμή. Κάθε σειρά οθόνης αρχίζει σε γραμμή πολλαπλάσια του 8,
; οπότε τα 8 pixel ενός γλύφου πέφτουν ΜΕΣΑ στην ίδια σειρά: η θέση p δεν
; αλλάζει, το δαχτυλίδι δεν σπάει γλύφο, και το προχώρημα γραμμής είναι «+#800».
;
; ΟΛΕΣ οι 40 στήλες μιας λογικής σειράς γράφονται πάντα, και γι' αυτό δεν
; υπάρχει καθάρισμα: το κενό είναι ένα κελί σαν όλα τα άλλα. Ενας δρόμος για
; κάθε κελί (hud_char): χαρακτήρας, κενό και κελί μπάρας είναι όλα ένας κωδικός.

HUD_ROWS    equ 5
HUD_CACHED  equ 3                   ; σειρές 0..2 — βλ. hud_char
; Τα pens της λωρίδας (§8.1): 0 μαύρο, 1 κόκκινο, 2 πράσινο, 3 λευκό.
PEN_FULL    equ 2                   ; πράσινο — η μπάρα γεμάτη
PEN_LOW     equ 1                   ; κόκκινο — κάτω από το ένα τέταρτο
PEN_EMPTY   equ 4                   ; ΟΧΙ pen: το περίγραμμα της άδειας μπάρας
BAR_CELLS   equ 6
HUD_TOPB    equ 160                 ; bytes της πάνω λωρίδας πριν από το cam_p
HUD_BOT     equ 1600                ; η κάτω λωρίδα, μετά το cam_p
HUD_BOTB    equ 240

        assert  (G_hud_shadow & 255) == 0       ; σειρά*40 + στήλη στο L
        assert  BAR_CELLS == 6                  ; hud_bar: 6v = 2v + 4v
        assert  (G_font_m1 & 7) == 0            ; hc_line: inc e

; ---------------------------------------------------------------------------
; hud_go — A = σειρά (0-4), στήλη 0. hud_goc — και C = στήλη (0-39).
;
; Οι δύο δείκτες βγαίνουν ΜΙΑ φορά εδώ και μετά προχωρούν μαζί, ένα κελί τη
; φορά (hud_next): ο δείκτης οθόνης και ο δείκτης της κρυφής μνήμης.
; ---------------------------------------------------------------------------
hud_go:
        ld      c,0
hud_goc:
        push    af
        ld      b,a
        ld      hl,0                    ; σειρές 3-4: χωρίς κρυφή μνήμη
        cp      HUD_CACHED
        jr      nc,hg_sp
        ld      a,c
        inc     b
        jr      hg_t
hg_row: add     a,40
hg_t:   djnz    hg_row                  ; A = σειρά*40 + στήλη
        ld      l,a
        ld      h,G_hud_shadow >> 8
hg_sp:  ld      (hud_sp),hl
        pop     af
        ; p = cam_p + hg_off[σειρά] + στήλη, mod 2048, στη γραμμή 0
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,hg_off
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      b,d
        add     hl,bc
        ld      de,(cam_p)
        add     hl,de
        ld      a,h
        and     7
        or      SCR_BASE / 256
        ld      h,a
        ld      (hud_de),hl
        ret

; Η αρχή κάθε λογικής σειράς μέσα στο δαχτυλίδι, από το cam_p.
hg_off: dw      -HUD_TOPB, -HUD_TOPB + 40, -HUD_TOPB + 80
        dw      HUD_BOT + 160, HUD_BOT + 200

; ---------------------------------------------------------------------------
; hud_inval — οι λωρίδες από την αρχή: όλες μαύρες, και η κρυφή μνήμη το ξέρει.
;
; Καλείται όταν η κάμερα ΠΗΔΑ (view_draw: σπίτι, φόρτωμα) — τότε στη θέση των
; λωρίδων κάθεται έδαφος — και πριν από τον δίσκο (src/save.asm). Ενα βήμα
; κάμερας ΔΕΝ το καλεί πια: οι λωρίδες μετακινούνται (hud_move).
;
; Το σβήσιμο είναι ανά στήλη, οι οκτώ γραμμές ξετυλιγμένες: τα bits 3-5 του H
; είναι η γραμμή, και τα επισκέπτεται με κώδικα Gray (ένα set/res ανά βήμα),
; οπότε το H γυρίζει εκεί που ξεκίνησε. Οι 400 στήλες, ~16 ms.
;
; Το hud_gen είναι ένα byte της υπογραφής του ui_panel (§9.2): μία κλήση εδώ
; ακυρώνει ΚΑΙ τις δύο κρυφές μνήμες του HUD.
; ---------------------------------------------------------------------------
hud_inval:
        ld      hl,G_hud_shadow
        ld      de,G_hud_shadow + 1
        ld      bc,HUD_CACHED * 40 - 1
        ld      (hl),#80                ; κενό κελί: αυτό ακριβώς αφήνει το σβήσιμο
        ldir
        ld      hl,hud_gen
        inc     (hl)
        ld      hl,-HUD_TOPB
        ld      b,HUD_TOPB
        call    hi_clr
        ld      hl,HUD_BOT
        ld      b,HUD_BOTB
; hi_clr — HL = θέση από το cam_p, B = στήλες (1-255).
hi_clr:
        ld      de,(cam_p)
        add     hl,de
        ld      a,h
        and     7
        or      SCR_BASE / 256
        ld      h,a
hic_col:
        xor     a
        ld      (hl),a
        set     3,h
        ld      (hl),a
        set     4,h
        ld      (hl),a
        res     3,h
        ld      (hl),a
        set     5,h
        ld      (hl),a
        set     3,h
        ld      (hl),a
        res     4,h
        ld      (hl),a
        res     3,h
        ld      (hl),a
        res     5,h
        inc     hl
        res     3,h                     ; το δαχτυλίδι: #C7FF -> #C000
        djnz    hic_col
        ret

; ---------------------------------------------------------------------------
; hud_move — οι λωρίδες ακολουθούν το δαχτυλίδι. In: DE = το cam_p ΠΡΙΝ από το
; βήμα κάμερας· το (cam_p) είναι ήδη το νέο.
;
; ΜΕΤΑΚΙΝΗΣΗ, ΟΧΙ ΞΑΝΑΓΡΑΨΙΜΟ (βήμα 83). Ως το βήμα 82 ένα βήμα κάμερας
; άκυρωνε το HUD: οι σειρές 3-4 ξαναγράφονταν αμέσως (18,4 ms ανά βήμα) και οι
; 0-2 έμεναν σκουπίδια ως το επόμενο ρολόι HUD — και ΓΙΑ ΠΑΝΤΑ σε παύση, που
; δεν έχει ρολόι. Τα 3.200 bytes των λωρίδων μετακινούνται τώρα κατά Δ (±4
; ανατολή/δύση, ±160 νότος/βορράς), όπως ακριβώς μετακινήθηκε το δαχτυλίδι,
; και η κρυφή μνήμη του HUD μένει αληθινή.
;
; Η ΣΕΙΡΑ ΜΕΤΡΑΕΙ. Με Δ > 0 η κάτω λωρίδα πέφτει πάνω στην παλιά πάνω (νότος:
; [p+1760, p+2000) πατά το [p+1888, p+2048)), άρα η πάνω φεύγει πρώτη· με Δ < 0
; το ανάποδο (βορράς). Μέσα σε κάθε λωρίδα, από το τέλος όταν ο προορισμός
; είναι μπροστά (ldd), από την αρχή όταν είναι πίσω (ldi).
;
; Κάθε λωρίδα κόβεται σε κομμάτια που δεν πατούν το τύλιγμα του δαχτυλιδιού —
; ούτε η πηγή ούτε ο προορισμός — και κάθε κομμάτι αντιγράφεται στις οκτώ
; γραμμές: οι θέσεις είναι ίδιες, μόνο το H ανεβαίνει κατά 8.
; ---------------------------------------------------------------------------
hud_move:
        ld      hl,(cam_p)
        or      a
        sbc     hl,de
        ld      a,h
        and     7
        ld      h,a
        ld      (hm_dl),hl              ; Δ mod 2048
        ld      a,h
        or      l
        ret     z                       ; η κάμερα δεν κουνήθηκε
        ex      de,hl                   ; HL = το παλιό cam_p, D = Δ >> 8
        bit     2,d                     ; Δ >= 1024: αρνητικό
        jr      nz,hm_neg
        push    hl
        dec     hl                      ; η πάνω: το τελευταίο της byte, p-1
        ld      bc,HUD_TOPB
        call    hm_back
        pop     hl
        ld      de,HUD_BOT + HUD_BOTB - 1
        add     hl,de
        ld      bc,HUD_BOTB
        jr      hm_back
hm_neg:
        push    hl
        ld      de,HUD_BOT
        add     hl,de
        ld      bc,HUD_BOTB
        call    hm_fwd
        pop     hl
        ld      de,-HUD_TOPB
        add     hl,de
        ld      bc,HUD_TOPB
        ; fall through

; hm_fwd — BC bytes από τη θέση HL (χωρίς mod) στη HL+Δ, από την αρχή.
hm_fwd:
        ld      (hm_n),bc
        ld      de,hmf_end
        ld      (hmc_end + 1),de
hmf_lp:
        call    hm_sd                   ; HL = d, (hm_s), (hm_d)
        ld      de,(hm_n)
        call    hm_room                 ; ως το τέλος του δαχτυλιδιού: προορισμός
        ld      hl,(hm_s)
        call    hm_room                 ; ...και πηγή
        call    hm_chunk
        ret     z
        add     hl,bc                   ; s += k
        jr      hmf_lp

; hm_back — BC bytes που ΤΕΛΕΙΩΝΟΥΝ στη θέση HL, στη HL+Δ, από το τέλος.
hm_back:
        ld      (hm_n),bc
        ld      de,hmb_end
        ld      (hmc_end + 1),de
hmb_lp:
        call    hm_sd
        ld      de,(hm_n)
        inc     hl                      ; d+1 bytes ως την αρχή του δαχτυλιδιού
        call    hm_min
        ld      hl,(hm_s)
        inc     hl
        call    hm_min
        call    hm_chunk
        ret     z
        sbc     hl,bc                   ; s -= k (το CY είναι 0 από το hm_chunk)
        jr      hmb_lp

; hm_sd — HL = s (χωρίς mod) -> (hm_s) = s mod 2048, HL = (hm_d) = s+Δ mod 2048.
hm_sd:
        ld      a,h
        and     7
        ld      h,a
        ld      (hm_s),hl
        ld      de,(hm_dl)
        add     hl,de
        ld      a,h
        and     7
        ld      h,a
        ld      (hm_d),hl
        ret

; hm_room — DE = min(DE, 2048 - HL). hm_min — DE = min(DE, HL). Χαλάνε HL.
hm_room:
        ld      a,l
        cpl
        ld      l,a
        ld      a,h
        cpl
        add     a,8
        ld      h,a
        inc     hl                      ; 2048 - HL
hm_min:
        or      a
        sbc     hl,de
        ret     nc
        add     hl,de
        ex      de,hl
        ret

; hm_chunk — DE = k bytes από το (hm_s) στο (hm_d), στις οκτώ γραμμές.
; Out: Z αν τελείωσε η λωρίδα· αλλιώς HL = (hm_s), BC = k, CY = 0.
hm_chunk:
        push    de
        ld      b,d
        ld      c,e
        ld      hl,(hm_s)
        ld      de,(hm_d)
        call    hmc
        pop     bc
        ld      hl,(hm_n)
        or      a
        sbc     hl,bc                   ; n >= k: κανένα δανεικό, CY = 0
        ret     z
        ld      (hm_n),hl
        ld      hl,(hm_s)               ; τα ld δεν αγγίζουν τα flags: NZ, CY = 0
        ret

; hmc — BC = k bytes, HL = πηγή, DE = προορισμός (θέσεις στο δαχτυλίδι), στις
; οκτώ γραμμές. Το ldi/ldd είναι ξετυλιγμένο ανά 16 (5 us το byte αντί για τα
; 6 του ldir), και η πρώτη βόλτα μπαίνει στη μέση του: τα k mod 16 πρώτα.
hmc:
        ld      (hmc_k + 1),bc
        push    de
        ld      a,c
        dec     a
        and     15
        inc     a
        add     a,a                     ; 2r: r = 1-16 εντολές στην πρώτη βόλτα
        ld      e,a
        ld      d,0
        push    hl
hmc_end:
        ld      hl,0                    ; hmf_end ή hmb_end (το γράφει ο καλών)
        sbc     hl,de                   ; CY = 0 από το and
        ld      (hmc_call + 1),hl
        pop     hl
        pop     de
        ld      a,h
        or      SCR_BASE / 256
        ld      h,a
        ld      a,d
        or      SCR_BASE / 256
        ld      d,a                     ; η γραμμή 0
        ld      a,8
hmc_lp:
        push    hl
        push    de
hmc_k:  ld      bc,0
hmc_call:
        call    0                       ; τα ldi δεν αγγίζουν το A
        pop     de
        pop     hl
        ld      c,a
        ld      a,h
        add     a,8
        ld      h,a
        ld      a,d
        add     a,8
        ld      d,a
        ld      a,c
        dec     a
        jr      nz,hmc_lp
        ret

hmf_lp16:
        repeat  16
        ldi
        rend
hmf_end:
        jp      pe,hmf_lp16
        ret
hmb_lp16:
        repeat  16
        ldd
        rend
hmb_end:
        jp      pe,hmb_lp16
        ret

hm_dl:      dw 0                        ; Δ mod 2048
hm_s:       dw 0
hm_d:       dw 0
hm_n:       dw 0

; ---------------------------------------------------------------------------
; hud_text7 — HL = κείμενο στην ΤΡΑΠΕΖΑ 7 (§4.2, src/uitext.asm).
;
; ΟΛΑ τα κείμενα του παιχνιδιού ζουν εκεί από το βήμα 23, γιατί η τράπεζα 0
; τελείωσε. Σελιδοποιεί την 7, τυπώνει, και ξαναβάζει την 1 — που είναι αυτό
; που βλέπει ο υπόλοιπος κώδικας του βρόχου. Η μόνη συμβολοσειρά που ΔΕΝ περνά
; από εδώ είναι το όνομα του καταλόγου (bd_name), που ζει στην τράπεζα 2.
;
; hud_page — BC = θύρα + τράπεζα: σελιδοποιεί, και ο γλύφος γυρίζει ΕΚΕΙ
; (hud_pg) και όχι πάντα στην 1: το hud_text διαβάζει το ΕΠΟΜΕΝΟ γράμμα του
; κειμένου του από την τράπεζα 7 αμέσως μετά.
; ---------------------------------------------------------------------------
hud_text7:
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page
        call    hud_text
        ld      bc,GA_PORT + PAGE_B1
hud_page:
        ld      (hud_pg),bc
        out     (c),c
        ret

; hud_text — HL = κείμενο, τερματισμένο με 0, σε μνήμη που φαίνεται ήδη.
; Γυρίζει με το HL στο 0.
hud_text:
        ld      a,(hl)
        or      a
        ret     z
        inc     hl
        push    hl
        call    hud_char
        pop     hl
        jr      hud_text

; ---------------------------------------------------------------------------
; hud_num — HL = τιμή, B = ψηφία (1-3). hud_numa — A = τιμή, ένα byte.
;
; Δεξιά στοίχιση, τα μπροστινά μηδενικά κενά, το τελευταίο ψηφίο πάντα ψηφίο.
; Τιμή με περισσότερα ψηφία δείχνει τα B τελευταία, όπως όταν ήταν διαιρέσεις:
; η πρώτη αφαίρεση, του 10^B, πετά ό,τι περισσεύει.
; ---------------------------------------------------------------------------
hud_numa:
        ld      l,a
        ld      h,0
hud_num:
        ex      de,hl                   ; DE = τιμή
        push    de
        ld      e,b
        ld      d,0
        ld      hl,hn_pow
        add     hl,de
        add     hl,de                   ; HL -> 10^B
        pop     de
        call    hn_div                  ; ό,τι ξεπερνά τα B ψηφία πέφτει
        ld      c,' '                   ; τα μπροστινά μηδενικά: κενά
        dec     b
        jr      z,hn_last
hn_lp:
        call    hn_div
        cp      '0'
        jr      z,hn_zero
        ld      c,'0'                   ; από εδώ και πέρα τα μηδενικά μετράνε
        jr      hn_put
hn_zero:
        ld      a,c
hn_put:
        call    hn_out
        djnz    hn_lp
hn_last:
        call    hn_div                  ; το τελευταίο: και το 0 ως «0»
hn_out:
        push    hl
        push    de
        push    bc
        call    hud_char
        pop     bc
        pop     de
        pop     hl
        ret

; hn_div — HL -> δύναμη του 10, DE = τιμή. Out: A = το ψηφίο σε ASCII, DE = ό,τι
; μένει, HL -> η επόμενη, μικρότερη δύναμη. Το B και το C μένουν.
hn_div:
        push    hl
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ex      de,hl                   ; HL = τιμή, DE = δύναμη
        ld      a,'0' - 1
        or      a
hnd_lp: inc     a
        sbc     hl,de
        jr      nc,hnd_lp
        add     hl,de
        ex      de,hl
        pop     hl
        dec     hl
        dec     hl
        ret

; ---------------------------------------------------------------------------
; hd_flow — HL = ετικέτα (τράπεζα 7), BC = τιμή, DE = μέγιστο: η ετικέτα, η
; μπάρα των BAR_CELLS κελιών, και ένα κενό.
;
; Οι ροές είναι μπάρες και τα αποθέματα αριθμοί, και αυτό δεν είναι διακόσμηση:
; στη ροή σημασία έχει το ΠΕΡΙΘΩΡΙΟ, στο απόθεμα η ΠΟΣΟΤΗΤΑ (§9.2).
;
; Το «μέγιστο» του οξυγόνου είναι η ΚΑΤΑΝΑΛΩΣΗ και μπορεί να είναι μηδέν.
; Μηδενική κατανάλωση σημαίνει γεμάτη μπάρα, όχι διαίρεση με μηδέν.
; ---------------------------------------------------------------------------
hd_flow:
        push    de
        push    bc
        call    hud_text7
        pop     hl
        pop     de
        ld      a,d
        or      e
        jr      nz,hud_bar
        inc     de
        ld      h,d
        ld      l,e                     ; 1 από 1: γεμάτη
hud_bar:
        ; Κελί i γεμάτο όταν τιμή*6 >= i*μέγιστο. Το v μικραίνει κατά ένα
        ; μέγιστο ανά κελί· στο πρώτο άδειο ξαναπαίρνει ό,τι έχασε, και αφού
        ; τότε είναι κάτω από ένα μέγιστο, μένουν άδεια και όσα ακολουθούν.
        add     hl,hl                   ; 2v
        ld      b,h
        ld      c,l
        add     hl,hl                   ; 4v
        push    hl
        or      a
        sbc     hl,de                   ; κάτω από το ένα τέταρτο: κόκκινη
        ld      a,PEN_FULL
        jr      nc,hb_pen
        ld      a,PEN_LOW
hb_pen:
        pop     hl
        add     hl,bc                   ; 6v
        ld      b,BAR_CELLS
hb_cell:
        push    af
        or      a
        sbc     hl,de
        jr      nc,hb_full
        add     hl,de
        ld      a,PEN_EMPTY
hb_full:
        push    hl
        push    de
        push    bc
        call    hud_cell
        pop     bc
        pop     de
        pop     hl
        pop     af
        djnz    hb_cell
        ; fall through: το κενό μετά τη μπάρα

; ---------------------------------------------------------------------------
; hud_space — ένα κενό κελί. hud_cell — ένα κελί μπάρας, A = 0-4.
; hud_char — A = κωδικός: χαρακτήρας 32-127, ή #80-#84 κελί μπάρας.
;
; ΟΛΑ ΕΙΝΑΙ ΓΛΥΦΟΙ (βήμα 83). Τα κελιά της μπάρας κάθονται στη γραμματοσειρά
; αμέσως μετά τον 127 (tools/pack.py, HUD_CELLS): κενό, κόκκινο, πράσινο,
; λευκό, άδειο. Ως το βήμα 82 ήταν συμπαγή κελιά με δικό τους δρόμο· τώρα
; έχουν το ύψος των γραμμάτων, και η άδεια μπάρα είναι περίγραμμα.
;
; Ενας κωδικός ανά κελί, γιατί η ΚΡΥΦΗ ΜΝΗΜΗ (G_hud_shadow, 120 bytes) κρατά
; αυτόν: «αυτό το κελί έχει ήδη αυτό το περιεχόμενο;». Ηταν το κέρδος του
; βήματος 19, και οι σειρές 0-2 αλλάζουν τρία-τέσσερα κελιά τη φορά.
;
; ΟΙ ΣΕΙΡΕΣ 3-4 ΔΕΝ ΜΠΑΙΝΟΥΝ ΣΤΗΝ ΚΡΥΦΗ ΜΝΗΜΗ: ο πίνακας επιλογής φυλάγεται
; ήδη πίσω από υπογραφή (§9.3). Εκεί το hud_sp έχει H = 0.
;
; Χαλάει AF, BC, DE, HL.
; ---------------------------------------------------------------------------
hud_space:
        xor     a
hud_cell:
        or      #80
hud_char:
        ld      hl,(hud_sp)
        inc     h
        dec     h
        jr      z,hc_draw               ; σειρά 3-4: πάντα
        cp      (hl)
        jr      z,hud_next              ; ήδη εκεί: μόνο προχώρημα
        ld      (hl),a
hc_draw:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 8 x κωδικός
        ld      de,G_font_m1 - 32 * 8
        add     hl,de
        ex      de,hl                   ; DE = ο γλύφος
        ld      hl,(hud_de)
        ; Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ ΖΕΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 7 (§4.2). Η οθόνη είναι στο #C000,
        ; έξω από το παράθυρο, οπότε η αντιγραφή βλέπει και τα δύο.
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        ld      bc,#0800
        ; ΤΟ ΤΕΛΟΣ ΤΟΥ ΒΡΟΧΟΥ ΕΙΝΑΙ ΤΟ CARRY. Η σειρά αρχίζει με (y&7)==0, άρα
        ; H = #C0-#C7· οκτώ φορές +#800 το φτάνουν στο #100-#107, και το carry
        ; ανάβει ακριβώς στην όγδοη γραμμή. Η οθόνη ΠΡΕΠΕΙ να είναι στο #C000.
hc_line:
        ld      a,(de)
        inc     e                       ; ο γλύφος δεν διασχίζει σελίδα
        ld      (hl),a
        add     hl,bc
        jr      nc,hc_line
        ld      bc,(hud_pg)             ; πίσω στην τράπεζα του καλούντος
        out     (c),c
        ; fall through

; hud_next — ένα κελί δεξιά, και οι δύο δείκτες. Το `res 3,h` είναι το
; δαχτυλίδι: η αρχή μιας σειράς HUD έχει τα bits 3-5 του H μηδέν, και το
; μόνο που ξεχειλίζει είναι το #C7FF -> #C800.
hud_next:
        ld      hl,(hud_sp)
        inc     hl
        ld      (hud_sp),hl
        ld      hl,(hud_de)
        inc     hl
        res     3,h
        ld      (hud_de),hl
        ret

; hud_blank — B στήλες κενές· B = 0, καμία.
hud_blank:
        inc     b
        jr      hbl_t
hbl_lp: push    bc
        call    hud_space
        pop     bc
hbl_t:  djnz    hbl_lp
        ret

; ---------------------------------------------------------------------------
; hud_draw — οι σειρές 0-2. Ολες, κάθε φορά· η κρυφή μνήμη κρατά ό,τι δεν
; άλλαξε έξω από την οθόνη.
; ---------------------------------------------------------------------------
hud_draw:
        ; --- σειρά 0: οι τέσσερις ροές, ως μπάρες ---
        xor     a
        call    hud_go
        ld      hl,txt_o2
        ld      bc,(EC_O2PROD)
        ld      de,(EC_O2USE)
        call    hd_flow
        ld      hl,txt_pwr
        ld      bc,(EC_PSTORE)
        ld      de,(EC_PCAP)
        call    hd_flow
        ld      hl,txt_h2o
        ld      bc,(EC_STOCK + S_WATER*2)
        ld      de,EC_CAP
        call    hd_flow
        ld      hl,txt_fod
        ld      bc,(EC_STOCK + S_FOOD*2)
        ld      de,EC_CAP
        call    hd_flow

        ; --- σειρά 1: τα αποθέματα, ως αριθμοί ---
        ld      a,1
        call    hud_go
        ld      hl,stock_row
        ld      b,6
hd_stock:
        push    bc
        call    hud_text                ; δύο γράμματα· HL -> το 0
        inc     hl
        ld      a,(hl)                  ; ο δείκτης αποθέματος
        inc     hl
        push    hl
        call    ec_stock_ptr            ; DE -> απόθεμα
        ex      de,hl
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      b,3
        call    hud_num
        call    hud_space
        pop     hl
        pop     bc
        djnz    hd_stock
        ld      b,4
        call    hud_blank

        ; --- σειρά 2: πληθυσμός, χρόνος, και η φωνή του παιχνιδιού ---
        ld      a,2
        call    hud_go
        ld      hl,txt_pop
        call    hud_text7
        ld      a,(EC_ALIVE)
        ld      b,2
        call    hud_numa
        ld      a,'/'
        call    hud_char
        ld      a,(EC_POPCAP)
        ld      b,2
        call    hud_numa
        ld      hl,txt_sol
        call    hud_text7
        ld      a,(EC_SOL)
        ld      b,3
        call    hud_numa
        call    hud_space
        ld      a,(EC_DAY)
        or      a
        ld      hl,txt_night
        jr      z,hd_night
        ld      hl,txt_day
hd_night:
        call    hud_text7
        call    hud_space
        ; fall through

        ; ΟΙ ΣΕΙΡΕΣ 3-4 ΔΕΝ ΑΓΓΙΖΟΝΤΑΙ ΕΔΩ. Τις κατέχει ο πίνακας επιλογής
        ; (§9.3), που ξέρει μόνος του πότε άλλαξε κάτι. Ως το βήμα 19 το
        ; hud_draw τις έσβηνε και τις ογδόντα σε κάθε κλήση και το ui_panel τις
        ; ξανάγραφε αμέσως μετά — 160 κελιά ανά τικ HUD, περισσότερα από τα 120
        ; που δείχνουν κάτι.

; hud_alert — 20 χαρακτήρες. Η γραμμή πρέπει να λέει ΤΙ, όχι «προσοχή» (§9.2).
hud_alert:
        ld      hl,txt_lost
        ld      a,(EC_GAMEOVER)
        or      a
        jr      nz,hd_say
        ; ΤΡΕΙΣ ΣΤΑΘΜΕΣ, ΔΥΟ ΜΗΝΥΜΑΤΑ (§6.5). Το μπλακάουτ είναι «NO POWER»·
        ; το P_ESS είναι «LOW POWER», και πρέπει να λέγεται: οι μηχανές
        ; σταμάτησαν και ο παίκτης δεν θα το δει αλλού — η μόνη ορατή διαφορά
        ; είναι ότι τα αποθέματα πάψανε να ανεβαίνουν.
        ;
        ; ΤΟ «LOW POWER» ΚΑΘΕΤΑΙ ΚΑΤΩ ΑΠΟ ΤΟ «NO OXYGEN», και η σειρά είναι ο
        ; χρόνος που έχει ο παίκτης: με πεσμένο φορτίο η υποστήριξη ζωής
        ; δουλεύει, οπότε αν ΚΑΙ ΠΑΛΙ λείπει οξυγόνο, λείπουν γεννήτριες — και
        ; αυτό σκοτώνει σε δευτερόλεπτα, ενώ οι σταματημένες μηχανές σε sols.
        ld      a,(EC_POK)
        ld      hl,txt_nopwr
        or      a
        jr      z,hd_say
        ld      hl,txt_noo2
        ld      a,(EC_O2OK)
        or      a
        jr      z,hd_say
        ld      hl,txt_shed
        ld      a,(EC_POK)
        cp      P_ESS
        jr      z,hd_say
        ; ΤΟ ΦΑΓΗΤΟ ΚΑΙ ΤΟ ΝΕΡΟ ΤΟ ΛΕΝΕ ΠΡΙΝ ΤΕΛΕΙΩΣΟΥΝ. Η πείνα σκοτώνει πιο
        ; αργά από την ασφυξία, και ακριβώς γι' αυτό ο παίκτης δεν την
        ; προσέχει: μετρημένο στο tools/balance.py, μια αποικία δώδεκα ατόμων
        ; αδειάζει την αποθήκη στο sol 4 και πεθαίνει στο 6, χωρίς η οθόνη να
        ; πει τίποτε άλλο από «ALL SYSTEMS OK». Κατώφλι: λιγότερο από ένα
        ; γεύμα ανά ζωντανό.
        ; Η ΒΡΟΧΗ ΠΡΙΝ ΑΠΟ ΤΗΝ ΠΕΙΝΑ: κρατά τρία δευτερόλεπτα, και μόνο τότε
        ; μπορεί ο παίκτης να δει πού πέφτει.
        ld      hl,txt_meteor
        ld      a,(EC_METEOR)
        or      a
        jr      nz,hd_say
        ld      a,S_FOOD
        call    hd_short
        ld      hl,txt_nofood
        jr      c,hd_say
        ld      a,S_WATER
        call    hd_short
        ld      hl,txt_nowater
        jr      c,hd_say
        ld      hl,txt_storm
        ld      a,(EC_STORM)
        or      a
        jr      nz,hd_say
        ld      hl,txt_ok
hd_say:
        jp      hud_text7

; hd_short — A = απόθεμα. CY αν έχει λιγότερο από έναν ζωντανό, δηλαδή
;            λιγότερο από μία μερίδα για τον καθένα. Χαλάει AF, BC, DE, HL.
;
; Το ec_stock_ptr ζει στο src/stock.asm, που το συμπεριλαμβάνουν από το βήμα
; 52 και οι σκαλωσιές των δοκιμών χωρίς οικονομία (tests/objtest.asm).
hd_short:
        call    ec_stock_ptr
        ex      de,hl
        ld      c,(hl)
        inc     hl
        ld      a,(hl)
        or      a
        ret     nz                      ; πάνω από 255: άφθονο, χωρίς CY
        ld      a,c
        ld      hl,EC_ALIVE
        cp      (hl)
        ret

; --- πίνακες ---------------------------------------------------------------

; δύο γράμματα και ο δείκτης αποθέματος, ανά στήλη της σειράς 1
stock_row:
        db      "FE", 0, S_METAL
        db      "BI", 0, S_BIOPL
        db      "PR", 0, S_PROC
        db      "SP", 0, S_SPARE
        db      "ME", 0, S_MEDI
        db      "BO", 0, S_BOT

; Το byte ενός συμπαγούς pen στο Mode 0, ανά pen. Το HUD δεν το χρειάζεται πια
; (βήμα 83)· το διαβάζει το ghost.asm.
hud_solid:
        db      #00, #C0, #0C, #CC, #30, #F0, #3C, #FC
        db      #03, #C3, #0F, #CF, #33, #F3, #3F, #FF

hn_pow: dw      1, 10, 100, 1000

; --- μεταβλητές ------------------------------------------------------------
hud_gen:    db 0
hud_pg:     dw GA_PORT + PAGE_B1        ; πού γυρίζει ο γλύφος
hud_de:     dw 0                        ; το επόμενο κελί στην οθόνη
hud_sp:     dw 0     ; και στο G_hud_shadow· H = 0 στις σειρές 3-4
