; ---------------------------------------------------------------------------
; tpage.asm — οι σελίδες του tutorial (βήμα 175, DESIGN §9.6). ΣΤΗΝ ΤΡΑΠΕΖΑ 7,
; μετά τα κείμενα και το src/st7.asm, στο ίδιο αρχείο του δίσκου (TEXT.BIN):
; τρέχει με την 7 στο παράθυρο και δεν σελιδοποιεί ποτέ. Ό,τι καλεί στην 0
; και στη 2 δεν σελιδοποιεί κι αυτό: snd_off, is_m1, hw_clear, in_scan και ο
; οδηγός του δίσκου (src/fdc.asm, στο SV_ORG του GH_BUF από το sv_ovl).
;
; Ο ΠΑΙΚΤΗΣ: «Το tutorial δεν έχει οδηγίες. Βάλε να έχει οδηγίες.
; Χρησιμοποίησε και αρχείο στην δισκέττα αν χρειάζεσαι για τα κείμενά του.»
; Διάλεξε μια σελίδα σε κάθε βήμα, σε όλη την οθόνη όπως η βοήθεια του «?»:
; τι χτίζεις, γιατί, ποια πλήκτρα, τι να κοιτάς. Οποιοδήποτε πλήκτρο γυρίζει
; στο παιχνίδι, η γραμμή κάτω από τα κουμπιά μένει, και το «?» την ξαναδείχνει.
;
; ΤΑ ΚΕΙΜΕΝΑ ΕΙΝΑΙ ΣΤΟΝ ΔΙΣΚΟ, στο TUTOR.TXT (tools/tupages.py από το
; src/tupages.txt): ~6 KB, πολύ περισσότερα από όσα χωρούν στη μνήμη. Κάθε
; σελίδα διαβάζεται όταν δείχνεται: ο κατάλογος του δίσκου (track 0) δίνει
; τα blocks του αρχείου, και το tp_idx (build/tupages.asm) πού ξεκινά η
; σελίδα μέσα του. Ενας τομέας τη φορά, στα 512 bytes της κεφαλίδας του
; σωσίματος (SV_HDR, το GH_BUF με τον κέρσορα σβηστό).
;
; Η ΜΟΡΦΗ: «@» αρχή σελίδας, «*» λευκά / πράσινα, CR νέα γραμμή, LF τίποτα,
; #1A τέλος αρχείου. Ο τίτλος είναι η πρώτη γραμμή, λευκός με τους
; αστερίσκους του, και μετά μια κενή.
;
; ΧΩΡΙΣ ΔΙΣΚΟ — βγήκε από τον οδηγό, ή δεν είναι αυτός του παιχνιδιού — η
; σελίδα λέει πού είναι, και το πλήκτρο γυρίζει πίσω όπως πάντα.
; ---------------------------------------------------------------------------

TP_COL      equ 2                       ; οι στήλες 2-77 (tools/tupages.py: TP_W 76)
TP_TROW     equ 1                       ; ο τίτλος· το σώμα από τη σειρά 3
TP_FROW     equ 24                      ; το υποσέλιδο, όπως της βοήθειας
TP_BUF      equ SV_HDR                  ; ένας τομέας
TP_WHITE    equ #FF                     ; pen 3 όπου ο γλύφος έχει pixel
TP_GREEN    equ #0F                     ; pen 2, όπως το hp_green
TP_KQ       equ 3                       ; το «?», το πλήκτρο /: γραμμή 3 του πίνακα,
TP_KQM      equ #40                     ; bit 6 (0 = πατημένο)
TP_KL       equ 4                       ; το L της σελίδας του τέλους (βήμα 177)
TP_KLM      equ #10
TP_STUB     equ #8000                   ; η επανεκκίνηση: έξω από το παράθυρο, κάτω
                                        ; από τον φορτωτή (#9000) και τον buffer του
        include "../build/tupages.asm"  ; TP_N, tp_idx
        assert  TP_N == PG_END + 1      ; src/const.asm, src/tupages.txt

; tp_show — A = σελίδα: 0 η εισαγωγή (και μετά η 1), #FF η σελίδα του βήματος
; (tp_cur). Γυρίζει με NZ αν το πλήκτρο που την έκλεισε ήταν το «?», με τις
; διακοπές κλειστές και την οθόνη όλη Mode 1: το ξαναζωγραφίζει ο καλών
; (hp_back, src/help.asm).
tp_show:
        cp      TP_CHOOSE
        call    z,ms_go                 ; τα ορόσημα και το τέλος (βήμα 177)
        inc     a
        jr      nz,tps_pg
        ld      a,(tp_cur)
        inc     a
tps_pg:
        dec     a
        ld      (tp_pg),a
        call    snd_off
        di
        call    fdc_on
        call    tp_find                 ; Z: βρέθηκε, τα blocks στο tp_blk
        ld      (tp_ok),a
tps_one:
        call    is_m1
        call    hw_clear
        ld      hl,-HUD_TOPB + TP_TROW * 80 + TP_COL
        call    tp_line
        ld      a,(tp_ok)
        or      a
        jr      z,tps_disc
        ld      hl,tp_nodisc
        call    tp_str
        jr      tps_foot
tps_disc:
        ld      a,(tp_pg)
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,tp_idx
        add     hl,de
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      (tp_off),de
        ld      a,#FF
        ld      (tp_k),a                ; κανένας τομέας ακόμη
tps_ch:
        call    tp_get                  ; C: ο δίσκος δεν τον έδωσε
        jr      c,tps_foot
        cp      '@'                     ; η επόμενη σελίδα
        jr      z,tps_foot
        cp      #1A                     ; το τέλος του αρχείου
        jr      z,tps_foot
        call    tp_put
        jr      tps_ch
tps_foot:
        ld      hl,-HUD_TOPB + TP_FROW * 80 + TP_COL
        call    tp_line
        ld      a,(tp_pg)
        cp      PG_END
        ld      hl,tp_foot
        jr      nz,tps_ft
        ld      hl,tp_endf              ; το τέλος: L, ή μια νέα αποικία
tps_ft:
        call    tp_str
        call    tp_key                  ; NZ: το «?», ή το L στο τέλος
        ld      hl,tp_pg
        ld      a,(hl)
        jr      nz,tps_spec
        cp      PG_END
        jp      z,tp_new                ; κάθε άλλο πλήκτρο: από το μενού, χωρίς γυρισμό
        inc     (hl)                    ; μετά την εισαγωγή το βήμα 1
        or      a
        jr      z,tps_one
        call    tp_mnext                ; τα ορόσημα που μένουν (βήμα 177)
        jr      nz,tps_one
        jr      tps_out                 ; Z: όχι το «?»
tps_spec:
        cp      PG_END                  ; το L: Z, χωρίς βοήθεια· το φόρτωμα το
        jr      nz,tps_out              ; ανοίγει το ms_key (src/goals.asm)
        xor     a
tps_out:
        push    af
        call    fdc_off
        ld      hl,tp_pg
        ld      (hl),#FF                ; καμία σελίδα: το βλέπουν οι δοκιμές και ο tools/play.py
        xor     a
        ld      (tp_mnew),a             ; ένα «?» στη μέση τα αφήνει
        pop     af
        ret

; ms_go — ποια σελίδα για το ms_key (src/goals.asm), και τα νούμερά της στο
; ms_val (βήμα 177, DESIGN §10.2). Η σειρά: όταν η αποικία χάθηκε, η σελίδα του
; τέλους — και για το G. Αλλιώς τα ορόσημα του αιτήματος (ms_req, τα bits 1-5:
; τα έβαλε εκεί ο κύκλος του sol, που τα σημείωσε και στο EC_MSEEN), το πρώτο
; τώρα και τα άλλα στο tp_mnew. Αλλιώς η σελίδα του G. Τα νούμερα, words, με τη
; σειρά των πεδίων ^A-^L του src/tupages.txt:
;   A ζωντανοί        B sols όλα πράσινα    C από τα 3 της Βιομηχανίας
;   D από τα 10 αγαθά E sols χωρίς εμπόριο  F ζωντανά ρομπότ
;   G sols χωρίς θάνατο H το sol            I το κύρος
;   J τα νομίσματα    K οι περισσότεροι     L τα ορόσημα
; και τα bits των οροσήμων για τα ^0-^4. Ο,τι είναι στην τράπεζα 6 το φέρνει το
; rd6 της 2 (src/link.asm): από εδώ η 6 δεν μπαίνει στο παράθυρο. A = η σελίδα.
ms_go:
        ld      hl,ms_req
        ld      c,(hl)
        ld      (hl),#FF                ; το αίτημα πάρθηκε
        push    bc
        ld      de,ms_val
        ld      a,(EC_ALIVE)            ; A
        call    msg_b
        ld      a,(EC_GREENS)           ; B
        call    msg_b
        ld      hl,(EC_PRODM)
        ld      a,l
        and     IND_MASK                ; C (src/ship.asm)
        call    msg_n
        ld      a,h
        and     DEP_MASK >> 8
        ld      c,0
        call    msg_pc                  ; D: τα δύο πάνω, και...
        ld      a,l
        call    msg_n0                  ; ...τα οκτώ κάτω
        ld      a,(EC_NOTRADE)          ; E
        call    msg_b
        ld      hl,G_agent_fields + AG_BOT0
        ld      bc,AG_NBOT * 256 + 0
        assert  F_ALIVE == 1            ; όπως το ship_tick
msg_bot:
        call    rd6
        and     F_ALIVE
        add     a,c
        ld      c,a
        inc     l
        djnz    msg_bot
        call    msg_c                   ; F
        ld      a,(EC_NODEATH)          ; G
        call    msg_b
        ld      a,(EC_SOL)              ; H
        call    msg_b
        ld      hl,EC_PREST             ; I
        call    msg_6
        ld      hl,EC_COINS             ; J, 16 bits
        call    rd6
        ld      (de),a
        inc     de
        inc     hl
        call    rd6
        ld      (de),a
        inc     de
        ld      hl,EC_PEAK              ; K
        call    msg_6
        ld      a,(EC_MILE)             ; L
        ld      b,a
        call    msg_n
        ld      a,b
        ld      (de),a                  ; ms_mile
        ; --- ποια σελίδα ---
        pop     bc                      ; C = το αίτημα
        ld      a,(EC_GAMEOVER)
        or      a                       ; και Cy = 0, για το rra
        ld      a,PG_END
        ret     nz
        ld      a,c
        rra                             ; το bit 0: 1, κανένα αίτημα (το G)
        jr      c,msg_g
        and     #1F                     ; τα καινούργια ορόσημα,
        ld      hl,EC_MILE
        and     (hl)                    ; όσα έχει η αποικία: ένα φόρτωμα στη μέση
        jr      z,msg_g
        ld      c,a
        dec     a
        and     c
        ld      (tp_mnew),a             ; όλα εκτός από το πρώτο
        ld      a,PG_MS0 - 1
msg_lo:
        inc     a
        srl     c
        jr      nc,msg_lo
        ret
msg_g:
        ld      a,PG_GOALS
        ret
; msg_n — A: τα bits του, ως ένα word στο (DE). msg_n0 — το ίδιο, με C ήδη
; μετρημένα. msg_c — το C. msg_6 — το (HL) της 6. msg_b — το A.
msg_n:
        ld      c,0
msg_n0:
        call    msg_pc
msg_c:
        ld      a,c
        jr      msg_b
msg_6:
        call    rd6
msg_b:
        ld      (de),a
        inc     de
        xor     a
        ld      (de),a
        inc     de
        ret
; msg_pc — C += τα bits του A.
msg_pc:
        or      a
        ret     z
        srl     a
        jr      nc,msg_pc
        inc     c
        jr      msg_pc

; tp_mnext — το επόμενο ορόσημο του tp_mnew (ms_go), η σελίδα του στο
; tp_pg. NZ αν υπάρχει. Δύο ορόσημα στο ίδιο sol: δύο σελίδες, η μία μετά την
; άλλη, με τη σειρά των bits.
tp_mnext:
        ld      hl,tp_mnew
        ld      a,(hl)
        or      a
        ret     z
        ld      c,a
        dec     a
        and     c
        ld      (hl),a                  ; χωρίς το πρώτο
        ld      a,PG_MS0 - 1
tpm_lo:
        inc     a
        srl     c
        jr      nc,tpm_lo
        ld      (tp_pg),a
        or      a                       ; NZ: το srl άφησε ίσως Z
        ret

; tp_new — κάθε πλήκτρο εκτός από το L στη σελίδα του τέλους: ΜΙΑ ΝΕΑ ΑΠΟΙΚΙΑ,
; από το μενού. Το μενού και ο φορτωτής θέλουν το firmware, που το παιχνίδι το
; έχει σβήσει (ο χώρος του AMSDOS είναι η τράπεζα 2). Το ξαναστήνει η ίδια η
; ROM: το MC START PROGRAM, όπως μετά από ένα RUN, τρέχει το tpn_stub, που
; ξυπνά το AMSDOS (KL ROM WALK), φορτώνει το LOADER.BIN, και πηδά εκεί. Η
; διεύθυνσή του στη ROM δεν είναι ίδια σε κάθε μηχάνημα: τη διάβασε ο
; φορτωτής από το jumpblock όσο ζούσε το firmware (src/boot.asm), στο tp_rom
; (src/uitext.asm), με τα bits 15 και 14 να λένε ποια ROM ανάβει. Χωρίς αυτήν
; (0): ένα reset, στο BASIC.
tp_new:
        ld      hl,tpn_stub
        ld      de,TP_STUB
        ld      bc,tpn_stub_end - tpn_stub
        ldir
        ld      hl,(tp_rom)
        ld      a,h
        rlca
        rlca
        and     3                       ; τα bits 15, 14: πάνω και κάτω ROM σβηστές...
        add     a,a
        add     a,a                     ; ...στα bits 3, 2 του RMR
        or      #81                     ; RMR, Mode 1
        ld      (TP_STUB + tps_rmr - tpn_stub),a
        ld      a,h
        and     #3F
        ld      h,a
        ld      (TP_STUB + tps_jp - tpn_stub),hl
        jp      TP_STUB

; tpn_stub — αντιγράφεται στο TP_STUB και τρέχει εκεί: η ROM ανάβει, και ό,τι
; είναι στο #0000-#3FFF γίνεται ROM. Οι διευθύνσεις του, σχετικές με αυτό.
tpn_stub:
        di
        im      1
        ld      bc,GA_PORT + #C0        ; η βασική μνήμη, όπως μετά από reset
        out     (c),c
tps_rmr     equ $ + 1
        ld      bc,GA_PORT + #89        ; η κάτω ROM αναμμένη (το γράφει το tp_new)
        out     (c),c
        ld      hl,TP_STUB + tpb_boot - tpn_stub
        ld      c,0
tps_jp      equ $ + 1
        jp      0                       ; το MC START PROGRAM της ROM (το tp_new)
tpb_boot:
        ld      de,#0040                ; όπως το BASIC: η μνήμη για τις ROM φόντου
        ld      hl,#ABFF
        call    #BCCB                   ; KL ROM WALK: το AMSDOS
        ld      hl,TP_STUB + tpb_name - tpn_stub
        ld      b,tpb_end - tpb_name
        ld      de,#9800                ; ο buffer του, όπως στον φορτωτή (LF_BUF)
        call    #BC77                   ; CAS IN OPEN
        jr      nc,tpb_fail
        ld      hl,#9000
        call    #BC83                   ; CAS IN DIRECT
        call    #BC7A                   ; CAS IN CLOSE
        jp      #9000                   ; ο φορτωτής, από την αρχή του
tpb_fail:
        rst     0                       ; κανένας δίσκος: reset
tpb_name:   db "LOADER.BIN"
tpb_end:
tpn_stub_end:
        assert  TP_STUB + tpn_stub_end - tpn_stub <= #9000

; tp_line — HL = θέση (από το cam_p, όπως το hp_go): εκεί η αρχή της γραμμής,
; πράσινα.
tp_line:
        ld      (tp_ls),hl
        ld      (tp_at),hl
        ld      a,TP_GREEN
        ld      (tp_mask),a
        ret

; tp_str — HL = κείμενο εδώ, ως το 0, με τους κανόνες του αρχείου.
tp_str:
        ld      a,(hl)
        or      a
        ret     z
        inc     hl
        push    hl
        call    tp_put
        pop     hl
        jr      tp_str

; tp_put — A = ένας χαρακτήρας του κειμένου: γλύφος, «*», CR ή τίποτα. Από
; το βήμα 177 και «^»: ο επόμενος είναι πεδίο (tp_field).
tp_put:
        ld      hl,tp_fl
        dec     (hl)
        jr      z,tp_field              ; ο χαρακτήρας μετά το «^»
        ld      (hl),0
        cp      '^'
        jr      z,tpp_fld
        cp      13
        jr      z,tpp_cr
        cp      '*'
        jr      z,tpp_ink
        sub     32
        ret     c                       ; το LF, και ό,τι δεν είναι γράμμα
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_font_m1
        add     hl,de
        ex      de,hl                   ; DE = ο γλύφος, στην 7 που είναι μέσα
        ld      hl,(tp_at)
        push    hl
        inc     hl
        ld      (tp_at),hl
        pop     hl
        ld      bc,(cam_p)
        add     hl,bc
        ld      a,h
        and     7                       ; το δαχτυλίδι των 2 KB, όπως το hg_p
        or      SCR_BASE / 256
        ld      h,a
        ld      a,(tp_mask)
        ld      c,a
        ld      b,8
tpp_ln:
        ld      a,(de)
        inc     e                       ; ο γλύφος δεν διασχίζει σελίδα (hp_green)
        and     c
        ld      (hl),a
        ld      a,h
        add     a,8
        ld      h,a
        djnz    tpp_ln
        ret
tpp_ink:
        ld      a,(tp_mask)
        xor     TP_WHITE ^ TP_GREEN
        ld      (tp_mask),a
        ret
tpp_cr:
        ld      hl,(tp_ls)
        ld      de,80
        add     hl,de
        jr      tp_line
tpp_fld:
        ld      (hl),1
        ret

; tp_field — A = ο χαρακτήρας μετά το «^» (βήμα 177, src/tupages.txt). «0»-«4»:
; DONE αν πιάστηκε το ορόσημο, μια παύλα αν όχι. «A»-«L»: το word του
; ms_val, σε δεκαδικά χωρίς μηδενικά μπροστά. Τα γράφει το ms_go.
tp_field:
        sub     'A'
        jr      nc,tpf_num
        add     a,'A' - '0'
        ld      b,a
        inc     b
        ld      a,(ms_mile)
tpf_bit:
        rrca                            ; το bit n στο Cy στην (n+1)-οστή
        djnz    tpf_bit
        ld      hl,tp_done
        jp      c,tp_str
        ld      hl,tp_none
        jp      tp_str
tpf_num:
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,ms_val
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        xor     a
        ld      (tp_nz),a
        ld      de,-10000
        call    tpn_d
        ld      de,-1000
        call    tpn_d
        ld      de,-100
        call    tpn_d
        ld      de,-10
        call    tpn_d
        ld      a,l                     ; οι μονάδες, πάντα
        jr      tpn_ch
; tpn_d — ένα ψηφίο: πόσα DE (αρνητικό) χωρούν στο HL. Μηδέν μπροστά: τίποτα.
tpn_d:
        ld      a,-1
tpn_lp:
        inc     a
        add     hl,de
        jr      c,tpn_lp
        sbc     hl,de                   ; Cy = 0: μία αφαίρεση παραπάνω, πίσω
        ld      c,a
        ld      a,(tp_nz)
        or      c
        ret     z
        ld      a,c
tpn_ch:
        add     a,'0'
        ld      (tp_nz),a               ; όχι μηδέν: από εδώ κάθε ψηφίο
        push    hl
        call    tp_put
        pop     hl
        ret

; tp_get — A = το επόμενο byte του αρχείου, NC. C αν ο τομέας του δεν διαβάστηκε.
tp_get:
        ld      hl,(tp_off)
        ld      a,h
        srl     a                       ; ο τομέας μέσα στο αρχείο: off >> 9
        ld      hl,tp_k
        cp      (hl)
        call    nz,tp_read
        ret     c
        ld      hl,(tp_off)
        ld      a,h
        and     1
        ld      h,a
        ld      de,TP_BUF
        add     hl,de
        ld      a,(hl)
        ld      hl,(tp_off)
        inc     hl
        ld      (tp_off),hl
        or      a                       ; NC
        ret

; tp_read — A = τομέας μέσα στο αρχείο: στο TP_BUF. C αν δεν διαβάστηκε.
; Το block από τον κατάλογο, ο λογικός τομέας του δίσκου 2 x block + μισό, και
; από αυτόν το track (/ 9) και το id (#C1 + υπόλοιπο), όπως ο αναγνώστης του
; φορτωτή (src/boot.asm).
tp_read:
        ld      (tp_k),a
        ld      c,a
        srl     a                       ; το block μέσα στο αρχείο
        cp      16
        ccf
        ret     c                       ; πέρα από την πρώτη έκταση
        ld      e,a
        ld      d,0
        ld      hl,tp_blk
        add     hl,de
        ld      l,(hl)
        ld      h,d
        add     hl,hl
        ld      a,c
        and     1
        or      l
        ld      l,a                     ; HL = ο τομέας του δίσκου
        ld      de,-9
        ld      b,-1
tpr_div:
        inc     b
        add     hl,de                   ; C όσο ήταν τουλάχιστον 9
        jr      c,tpr_div
        ld      a,l                     ; L = υπόλοιπο - 9
        add     a,#C1 + 9
        ld      (fd_sect),a
        ld      a,b
        call    fdc_seek
        ld      hl,TP_BUF
        call    fdc_rsect               ; Z (και NC) αν πέτυχε
        ret     z
        scf
        ret

; tp_find — ο κατάλογος, οι τομείς #C1-#C4 του track 0: η εγγραφή του
; TUTOR.TXT (χρήστης 0, έκταση 0), και τα blocks της στο tp_blk. Z αν βρέθηκε.
tp_find:
        xor     a
        call    fdc_seek
        ld      a,#C1
tpf_sec:
        ld      (fd_sect),a
        ld      hl,TP_BUF
        call    fdc_rsect
        ret     nz                      ; ο δίσκος δεν απάντησε
        ld      hl,TP_BUF
        ld      b,512 / 32
tpf_ent:
        push    bc
        push    hl
        ld      de,tp_name
        ld      b,13                    ; χρήστης, όνομα και τύπος, έκταση
tpf_cmp:
        ld      a,(de)
        cp      (hl)
        jr      nz,tpf_no
        inc     de
        inc     hl
        djnz    tpf_cmp
        ld      de,16 - 13
        add     hl,de                   ; τα blocks, από το byte 16
        ld      de,tp_blk
        ld      bc,16
        ldir
        pop     hl
        pop     bc
        xor     a                       ; Z
        ret
tpf_no:
        pop     hl
        ld      de,32
        add     hl,de
        pop     bc
        djnz    tpf_ent
        ld      a,(fd_sect)
        inc     a
        cp      #C5
        jr      nz,tpf_sec
        or      a                       ; NZ: δεν είναι σε αυτόν τον δίσκο
        ret

; tp_key — περιμένει να αφεθεί ό,τι κρατιέται (το «?» που την άνοιξε, το
; FIRE που έχτισε), ένα πλήκτρο ή το χειριστήριο, και να αφεθεί κι αυτό:
; αλλιώς το ίδιο πάτημα θα έκανε κάτι στο παιχνίδι (όπως το hp_up). NZ αν
; ήταν το «?» — ή το L, στη σελίδα του τέλους (βήμα 177).
tp_key:
        call    tpk_up
tpk_dn:
        call    tp_any
        jr      z,tpk_dn
        ld      a,(tp_pg)               ; στη σελίδα του τέλους το L (βήμα 177)
        cp      PG_END
        ld      a,(key_now + TP_KQ)
        ld      c,TP_KQM
        jr      nz,tpk_q
        ld      a,(key_now + TP_KL)
        ld      c,TP_KLM
tpk_q:
        cpl
        and     c
        push    af
        call    tpk_up
        pop     af
        ret
tpk_up:
        call    tp_any
        jr      nz,tpk_up
        ret

; tp_any — μια σάρωση, και NZ αν κάτι είναι πατημένο (όπως το hp_any).
tp_any:
        call    in_scan
        ld      hl,key_now
        ld      b,KEY_LINES
        ld      a,#FF
tpa_lp:
        and     (hl)
        inc     hl
        djnz    tpa_lp
        inc     a
        ret

tp_foot:    db "*ANY KEY*  GO ON             *?*  WHAT EVERY BUTTON DOES",0
tp_endf:    db "*L*  LOAD A SAVED COLONY     *ANY OTHER KEY*  A NEW COLONY",0
tp_done:    db "*DONE*",0
tp_none:    db "-   ",0
tp_nodisc:  db "*THIS PAGE IS ON THE GAME'S DISC*",13,13
            db "PUT THE DISC BACK IN THE DRIVE, AND PRESS *?* TO SEE IT.",0
tp_name:    db 0,"TUTOR   TXT",0
tp_cur:     db 1                        ; η σελίδα του βήματος: την γράφει το tuo_go
tp_pg:      db #FF                      ; η σελίδα που δείχνεται, #FF καμία
tp_ok:      db 0
tp_k:       db 0
tp_mask:    db 0
tp_off:     dw 0
tp_at:      dw 0
tp_ls:      dw 0
tp_blk:     ds 16
; ΤΑ ΝΟΥΜΕΡΑ ΤΩΝ ΣΕΛΙΔΩΝ (βήμα 177): τα γράφει όλα μαζί το ms_go.
ms_val:     ds 2 * 12                   ; ^A-^L
ms_mile:    db 0                        ; ^0-^4: τα bits του EC_MILE
tp_mnew:    db 0                        ; τα ορόσημα που μένουν να δειχτούν
tp_fl:      db 0                        ; 1: ο επόμενος χαρακτήρας είναι πεδίο
tp_nz:      db 0                        ; όχι μηδέν: γράφτηκε ψηφίο
