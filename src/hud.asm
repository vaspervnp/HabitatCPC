; hud.asm — οι πέντε τελευταίες σειρές χαρακτήρων (DESIGN §9.2).
;
; Το HUD ζει στην ΙΔΙΑ σελίδα με το κάδρο (§8.1): η τομή δύο σελίδων δεν
; γίνεται, ο CRTC κλειδώνει τη διεύθυνση έναρξης μία φορά ανά frame. Συνέπεια:
; όταν σκρολάρει η κάμερα, το δαχτυλίδι γυρίζει και η ΜΝΗΜΗ του HUD αλλάζει
; θέση ενώ η θέση του στην ΟΘΟΝΗ δεν αλλάζει. Αρα ξαναγράφεται ολόκληρο μετά
; από κάθε βήμα.
;
; Η γραμματοσειρά είναι 4x8 — 40 στήλες, γιατί οι 20 του 8x8 δεν φτάνουν για
; τίποτα (ASSET-4). Κάθε σειρά χαρακτήρων αρχίζει σε γραμμή πολλαπλάσια του 8,
; οπότε και τα 8 pixel ενός γλύφου πέφτουν ΜΕΣΑ στην ίδια σειρά χαρακτήρων:
; η θέση p δεν αλλάζει, το δαχτυλίδι δεν μπορεί να σπάσει γλύφο, και το
; προχώρημα γραμμής είναι ένα «d += 8».
;
; ΟΛΕΣ οι 40 στήλες γράφονται πάντα, και γι' αυτό δεν υπάρχει καθάρισμα: το
; κενό είναι ο χαρακτήρας 32 και κοστίζει όσο κάθε άλλος.

HUD_TOP     equ PLAY_LINES          ; 160 — η πρώτη γραμμή του HUD
HUD_ROWS    equ 5
PEN_FULL    equ 9                   ; έντονο πράσινο — η μπάρα γεμάτη
PEN_EMPTY   equ 1                   ; μπλε — η μπάρα άδεια
PEN_LOW     equ 8                   ; έντονο κόκκινο — κάτω από το ένα τρίτο
BAR_CELLS   equ 6

; ---------------------------------------------------------------------------
; hud_at — DE = διεύθυνση οθόνης για (hud_col, hud_row).
; ---------------------------------------------------------------------------
hud_at:
        ld      a,(hud_col)
        add     a,a
        ld      c,a
        ld      a,(hud_row)
        add     a,a
        add     a,a
        add     a,a
        add     a,HUD_TOP
        jp      scr_addr

; ---------------------------------------------------------------------------
; hud_go — A = σειρά· στήλη 0, και ο δείκτης οθόνης υπολογίζεται ΜΙΑ φορά.
;
; Το scr_addr κόστιζε 230 T ανά γλύφο και ο γλύφος γράφει 16 bytes: πάνω από
; το ένα τρίτο του χρόνου πήγαινε στο να ξαναβρεθεί μια διεύθυνση που απέχει
; δύο bytes από την προηγούμενη.
; ---------------------------------------------------------------------------
hud_go:
        ld      (hud_row),a
        xor     a
        ld      (hud_col),a
        call    hud_at
        ld      (hud_de),de
        ret

; hud_adv — ο δείκτης προχωράει B στήλες. Το `and #C7` είναι το δαχτυλίδι· η
; αρχή μιας σειράς HUD έχει πάντα (y&7)==0, οπότε τα bits 3-5 του D είναι
; μηδέν και η μάσκα δεν τα πειράζει.
hud_adv:
        ld      hl,hud_col
        ld      a,(hl)
        add     a,b
        ld      (hl),a
        ld      hl,(hud_de)
        ld      a,b
        add     a,a
        ld      c,a
        ld      b,0
        add     hl,bc
        ld      a,h
        and     #C7
        ld      h,a
        ld      (hud_de),hl
        ret

; ---------------------------------------------------------------------------
; hud_char — A = χαρακτήρας ASCII. Προχωράει τη στήλη.
;
; Ο βρόχος είναι ξετυλιγμένος και δεν καλεί ούτε scr_nextline ούτε έλεγχο
; δαχτυλιδιού: ένας γλύφος είναι 8 γραμμές μέσα σε ΜΙΑ σειρά χαρακτήρων, άρα
; μόνο το ψηλό byte κινείται και μόνο κατά 8.
; ---------------------------------------------------------------------------
hud_char:
        sub     FONT_FIRST
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *FONT_SIZE
        ld      de,G_font_gfx
        add     hl,de
        ld      de,(hud_de)
        repeat  8
        ld      a,(hl)
        inc     hl
        ld      (de),a
        inc     de
        ld      a,(hl)
        inc     hl
        ld      (de),a
        dec     de
        ld      a,d
        add     a,8
        ld      d,a
        rend
        ld      b,1
        jp      hud_adv

; ---------------------------------------------------------------------------
; hud_blank — B στήλες κενές.
;
; Ο χαρακτήρας 32 της γραμματοσειράς είναι δεκαέξι μηδενικά, οπότε το γέμισμα
; είναι ΤΑΥΤΟΣΗΜΟ με το να ζωγραφιστούν κενά — και δέκα φορές φθηνότερο. Οι
; σειρές 3 και 4 είναι ογδόντα κενά: το 40% των κελιών του HUD.
; ---------------------------------------------------------------------------
hud_blank:
        ld      a,b
        add     a,a
        ld      (hbl_n),a
        push    bc
        ld      de,(hud_de)
        ld      b,8
hbl_line:
        push    bc
        push    de
        ld      hl,hud_zero
        ld      a,(hbl_n)
        ld      b,a
        call    blt_op_line
        pop     de
        ld      a,d
        add     a,8
        ld      d,a
        pop     bc
        djnz    hbl_line
        pop     bc
        jp      hud_adv

; ---------------------------------------------------------------------------
; hud_text — HL = κείμενο, τερματισμένο με 0.
; ---------------------------------------------------------------------------
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
; hud_num — HL = τιμή, B = ψηφία. Δεξιά στοίχιση, τα μπροστινά μηδενικά κενά.
; ---------------------------------------------------------------------------
hud_num:
        ld      a,b
        ld      (hn_n),a
        ld      ix,hn_buf
        ld      c,b
hn_lp:
        call    hud_div10
        add     a,'0'
        ld      (ix+0),a
        inc     ix
        dec     c
        jr      nz,hn_lp
        ; σβήσε τα μπροστινά μηδενικά — όχι όμως το τελευταίο ψηφίο, ώστε το
        ; μηδέν να είναι «0» και όχι κενό
        ld      a,(hn_n)
        dec     a
        jr      z,hn_show
        ld      c,a
hn_zap:
        dec     ix
        ld      a,(ix+0)
        cp      '0'
        jr      nz,hn_show
        ld      (ix+0),' '
        dec     c
        jr      nz,hn_zap
hn_show:
        ld      ix,hn_buf
        ld      a,(hn_n)
        ld      c,a
        ld      e,a
        ld      d,0
        add     ix,de
hn_out:
        dec     ix
        ld      a,(ix+0)
        push    bc
        call    hud_char
        pop     bc
        dec     c
        jr      nz,hn_out
        ret

; hud_div10 — HL /= 10, A = υπόλοιπο.
hud_div10:
        xor     a
        ld      b,16
hd_lp:
        add     hl,hl
        rla
        cp      10
        jr      c,hd_no
        sub     10
        inc     l
hd_no:
        djnz    hd_lp
        ret

; ---------------------------------------------------------------------------
; hud_bar — HL = τιμή, DE = μέγιστο, BAR_CELLS κελιά.
;
; Οι ροές είναι μπάρες και τα αποθέματα αριθμοί, και αυτό δεν είναι διακόσμηση:
; στη ροή σημασία έχει το ΠΕΡΙΘΩΡΙΟ, στο απόθεμα η ΠΟΣΟΤΗΤΑ (§9.2).
; ---------------------------------------------------------------------------
hud_bar:
        ld      (hb_max),de
        ld      (hb_val),hl
        ld      hl,0
        ld      b,BAR_CELLS
hb_m:
        ld      de,(hb_val)
        add     hl,de
        djnz    hb_m
        ld      (hb_v),hl               ; τιμή * κελιά
        ld      hl,0
        ld      (hb_acc),hl
        ; χαμηλό; κάτω από το ένα τρίτο η μπάρα γίνεται κόκκινη
        ld      hl,(hb_val)
        add     hl,hl
        add     hl,hl                   ; 4*τιμή
        ld      de,(hb_max)
        or      a
        sbc     hl,de
        ld      a,PEN_FULL
        jr      nc,hb_pen
        ld      a,PEN_LOW
hb_pen:
        ld      (hb_full),a
        ld      b,BAR_CELLS
hb_cell:
        push    bc
        ld      hl,(hb_acc)
        ld      de,(hb_max)
        add     hl,de
        ld      (hb_acc),hl
        ex      de,hl
        ld      hl,(hb_v)
        or      a
        sbc     hl,de                   ; v - acc
        ld      a,(hb_full)
        jr      nc,hb_draw
        ld      a,PEN_EMPTY
hb_draw:
        call    hud_cell
        pop     bc
        djnz    hb_cell
        ret

; ---------------------------------------------------------------------------
; hud_cell — ένα συμπαγές κελί 4x8 στο pen A.
;
; Το byte ενός συμπαγούς pen στο Mode 0 δεν είναι το pen: τα bits του pixel
; είναι σκορπισμένα (7,3,5,1 για το αριστερό, 6,2,4,0 για το δεξί), οπότε
; χρειάζεται πίνακας 16 θέσεων.
; ---------------------------------------------------------------------------
hud_cell:
        ld      l,a
        ld      h,0
        ld      de,hud_solid
        add     hl,de
        ld      a,(hl)
        ld      de,(hud_de)
        repeat  8
        ld      (de),a
        inc     de
        ld      (de),a
        dec     de
        ld      b,a
        ld      a,d
        add     a,8
        ld      d,a
        ld      a,b
        rend
        ld      b,1
        jp      hud_adv

; ---------------------------------------------------------------------------
; hud_draw — και οι πέντε σειρές. Ολο το HUD, κάθε φορά.
; ---------------------------------------------------------------------------
hud_draw:
        ; --- σειρά 0: οι τέσσερις ροές, ως μπάρες ---
        xor     a
        call    hud_go
        ld      hl,txt_o2
        call    hud_text
        ld      hl,(EC_O2PROD)
        ld      de,(EC_O2USE)
        call    hud_bar_safe
        call    hud_space
        ld      hl,txt_pwr
        call    hud_text
        ld      hl,(EC_PSTORE)
        ld      de,(EC_PCAP)
        call    hud_bar_safe
        call    hud_space
        ld      hl,txt_h2o
        call    hud_text
        ld      hl,(EC_STOCK + S_WATER*2)
        ld      de,EC_CAP
        call    hud_bar
        call    hud_space
        ld      hl,txt_fod
        call    hud_text
        ld      hl,(EC_STOCK + S_FOOD*2)
        ld      de,EC_CAP
        call    hud_bar
        call    hud_space

        ; --- σειρά 1: τα αποθέματα, ως αριθμοί ---
        ld      a,1
        call    hud_go
        ld      hl,stock_row
        ld      (hd_ptr),hl
        ld      b,6
hd_stock:
        push    bc
        ld      hl,(hd_ptr)
        ld      a,(hl)
        inc     hl
        ld      a,(hl)                  ; δείκτης αποθέματος
        add     a,a
        ld      l,a
        ld      h,0
        ld      de,EC_STOCK
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (hd_val),hl
        ld      hl,(hd_ptr)
        ld      a,(hl)
        call    hud_char                ; πρώτο γράμμα
        ld      hl,(hd_ptr)
        inc     hl
        inc     hl
        ld      a,(hl)                  ; δεύτερο γράμμα
        call    hud_char
        ld      hl,(hd_val)
        ld      b,3
        call    hud_num
        call    hud_space
        ld      hl,(hd_ptr)
        ld      de,4
        add     hl,de
        ld      (hd_ptr),hl
        pop     bc
        djnz    hd_stock
        ld      b,4
        call    hud_blank

        ; --- σειρά 2: πληθυσμός, χρόνος, και η φωνή του παιχνιδιού ---
        ld      a,2
        call    hud_go
        ld      hl,txt_pop
        call    hud_text
        ld      a,(EC_ALIVE)
        ld      l,a
        ld      h,0
        ld      b,2
        call    hud_num
        ld      a,'/'
        call    hud_char
        ld      a,(EC_POPCAP)
        ld      l,a
        ld      h,0
        ld      b,2
        call    hud_num
        ld      hl,txt_sol
        call    hud_text
        ld      a,(EC_SOL)
        ld      l,a
        ld      h,0
        ld      b,3
        call    hud_num
        call    hud_space
        ld      a,(EC_DAY)
        or      a
        ld      hl,txt_night
        jr      z,hd_night
        ld      hl,txt_day
hd_night:
        call    hud_text
        call    hud_space
        call    hud_alert

        ; --- σειρές 3-4: ο πίνακας επιλογής, ακόμη κενός ---
        ld      a,3
        call    hud_go
        ld      b,40
        call    hud_blank
        ld      a,4
        call    hud_go
        ld      b,40
        jp      hud_blank

; hud_bar_safe — μπάρα όπου το «μέγιστο» είναι η ΚΑΤΑΝΑΛΩΣΗ και μπορεί να
; είναι μηδέν. Μηδενική κατανάλωση σημαίνει γεμάτη μπάρα, όχι διαίρεση με μηδέν.
hud_bar_safe:
        ld      a,d
        or      e
        jp      nz,hud_bar
        ld      de,1
        ld      hl,1
        jp      hud_bar

hud_space:
        ld      b,1
        jp      hud_blank

hud_spaces:
        jp      hud_blank

; hud_alert — 20 χαρακτήρες. Η γραμμή πρέπει να λέει ΤΙ, όχι «προσοχή» (§9.2).
hud_alert:
        ld      hl,txt_lost
        ld      a,(EC_GAMEOVER)
        or      a
        jr      nz,hd_say
        ld      hl,txt_nopwr
        ld      a,(EC_POK)
        or      a
        jr      z,hd_say
        ld      hl,txt_noo2
        ld      a,(EC_O2OK)
        or      a
        jr      z,hd_say
        ld      hl,txt_storm
        ld      a,(EC_STORM)
        or      a
        jr      nz,hd_say
        ld      hl,txt_ok
hd_say:
        jp      hud_text

; --- κείμενα ---------------------------------------------------------------
txt_o2:     db "O2 ",0
txt_pwr:    db "PWR",0
txt_h2o:    db "H2O",0
txt_fod:    db "FOD",0
txt_pop:    db "POP ",0
txt_sol:    db "SOL",0
txt_day:    db "DAY",0
txt_night:  db "NGT",0
txt_ok:     db "ALL SYSTEMS OK      ",0
txt_nopwr:  db "NO POWER            ",0
txt_noo2:   db "NO OXYGEN           ",0
txt_storm:  db "SANDSTORM           ",0
txt_lost:   db "COLONY LOST         ",0

; δύο γράμματα και ο δείκτης αποθέματος, ανά στήλη της σειράς 1
stock_row:
        db      "F", S_METAL,  "E", 0
        db      "B", S_BIOPL,  "I", 0
        db      "P", S_PROC,   "R", 0
        db      "S", S_SPARE,  "P", 0
        db      "M", S_MEDI,   "E", 0
        db      "B", S_BOT,    "O", 0

; Το byte ενός συμπαγούς pen στο Mode 0, ανά pen.
hud_solid:
        db      #00, #C0, #0C, #CC, #30, #F0, #3C, #FC
        db      #03, #C3, #0F, #CF, #33, #F3, #3F, #FF

; --- μεταβλητές ------------------------------------------------------------
hud_col:    db 0
hud_row:    db 0
hn_n:       db 0
hn_buf:     defs 6
hb_val:     dw 0
hb_max:     dw 0
hb_v:       dw 0
hb_acc:     dw 0
hb_full:    db 0
hd_ptr:     dw 0
hd_val:     dw 0
hud_de:     dw 0
hbl_n:      db 0
hud_zero:   defs 80
