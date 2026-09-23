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
        push    af
        xor     a
        ld      (hud_col),a
        call    hud_at
        ld      (hud_de),de
        ; Ο δείκτης της κρυφής μνήμης βγαίνει ΜΙΑ φορά ανά σειρά και προχωρά
        ; μετά μαζί με τον δείκτη οθόνης. Οσο τον ξανάβγαζα ανά κελί, ο
        ; πολλαπλασιασμός σειρά*40 κόστιζε περισσότερο από όσο γλίτωνε.
        pop     af
        cp      HUD_CACHED
        jr      nc,hg_nocache
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *8
        ld      c,l
        ld      b,h
        add     hl,hl
        add     hl,hl                   ; *32
        add     hl,bc                   ; *40
        ld      bc,G_hud_shadow
        add     hl,bc
        ld      (hud_sp),hl
        ret
hg_nocache:
        ld      hl,0                    ; σειρές 3-4: χωρίς κρυφή μνήμη
        ld      (hud_sp),hl
        ret

; hud_adv — ο δείκτης προχωράει B στήλες. Το `and #C7` είναι το δαχτυλίδι· η
; αρχή μιας σειράς HUD έχει πάντα (y&7)==0, οπότε τα bits 3-5 του D είναι
; μηδέν και η μάσκα δεν τα πειράζει.
hud_adv:
        ld      hl,hud_col
        ld      a,(hl)
        add     a,b
        ld      (hl),a
        ld      c,b                     ; το B σβήνεται παρακάτω
        ld      b,0
        ld      hl,(hud_sp)
        add     hl,bc
        ld      (hud_sp),hl
        ld      hl,(hud_de)
        ld      a,c
        add     a,a                     ; δύο bytes ανά στήλη
        ld      c,a
        add     hl,bc
        ld      a,h
        and     #C7
        ld      h,a
        ld      (hud_de),hl
        ret

; ---------------------------------------------------------------------------
; hud_seen — «αυτό το κελί έχει ήδη αυτό το περιεχόμενο;»
;
; ΤΟ ΚΕΡΔΟΣ ΤΟΥ ΒΗΜΑΤΟΣ 19. Μια πλήρης επανασχεδίαση HUD κόστιζε 50.918 us,
; δηλαδή 2,55 frames, και γίνεται κάθε δεκαέξι: η προσομοίωση έπαιρνε 16 από
; τα 19 frames (§9.1). Οι σειρές 0-2 όμως αλλάζουν τρία-τέσσερα κελιά τη φορά
; — ένα ψηφίο αποθέματος, ένα κελί μπάρας. Τα υπόλοιπα 116 ξαναγράφονταν
; πανομοιότυπα.
;
; Ενας κωδικός ανά κελί, 120 bytes στην τράπεζα 2: για γλύφο ο χαρακτήρας του
; (32-127), για συμπαγές κελί το #80 + pen. Δεν συγκρούονται.
;
; ΟΙ ΣΕΙΡΕΣ 3-4 ΔΕΝ ΜΠΑΙΝΟΥΝ ΣΤΗΝ ΚΡΥΦΗ ΜΝΗΜΗ: ο πίνακας επιλογής φυλάγεται
; ήδη πίσω από υπογραφή (§9.3). Εκεί ο δείκτης hud_sp είναι μηδέν.
;
; Μετρημένο μετά: 22.963 us ζεστό (1,15 frames) και 43.930 us κρύο, δηλαδή
; μετά από βήμα κάμερας, που ακυρώνει και τα 120 κελιά. Το x1 ανέβηκε από
; 0,84 σε 0,92 του ονομαστικού.
;
; In:  A = κωδικός.
; Out: carry = «είναι ήδη εκεί, μην το γράψεις». A, BC, DE ανέπαφα.
; ---------------------------------------------------------------------------
HUD_CACHED  equ 3                   ; σειρές 0..2

hud_seen:
        push    hl
        ld      hl,(hud_sp)
        ld      c,a
        ld      a,h
        or      a                       ; 0 = σειρά εκτός κρυφής μνήμης
        ld      a,c
        jr      z,hs_write
        cp      (hl)
        jr      z,hs_same
        ld      (hl),a
hs_write:
        pop     hl
        or      a                       ; carry = 0: γράψ' το
        ret
hs_same:
        pop     hl
        scf
        ret

; ---------------------------------------------------------------------------
; hud_inval — η κρυφή μνήμη δεν ισχύει πια.
;
; Καλείται από το view_cam: όταν γυρίζει το δαχτυλίδι, η ΜΝΗΜΗ του HUD αλλάζει
; θέση ενώ η θέση του στην οθόνη δεν αλλάζει, οπότε τα παλιά bytes δεν είναι
; πια εκεί που τα άφησε η κρυφή μνήμη.
;
; ΚΑΙ ΟΙ ΣΕΙΡΕΣ 3-4: το hud_gen είναι ένα byte της υπογραφής του ui_panel
; (§9.2), οπότε μία κλήση εδώ ακυρώνει ΚΑΙ τις δύο κρυφές μνήμες του HUD.
; Χωρίς αυτό ο πίνακας έμενε με ό,τι βρήκε στη νέα θέση του δαχτυλιδιού —
; έδαφος — και δεν ξαναγραφόταν ποτέ, γιατί η υπογραφή του δεν είχε αλλάξει.
; ---------------------------------------------------------------------------
hud_inval:
        ld      hl,G_hud_shadow
        ld      de,G_hud_shadow + 1
        ld      bc,HUD_CACHED * 40 - 1
        ld      (hl),0                  ; κανένα κελί δεν έχει κωδικό 0
        ldir
        ld      hl,hud_gen
        inc     (hl)
        ret

hud_gen:    db 0

; ---------------------------------------------------------------------------
; hud_char — A = χαρακτήρας ASCII. Προχωράει τη στήλη.
;
; Ο βρόχος είναι ξετυλιγμένος και δεν καλεί ούτε scr_nextline ούτε έλεγχο
; δαχτυλιδιού: ένας γλύφος είναι 8 γραμμές μέσα σε ΜΙΑ σειρά χαρακτήρων, άρα
; μόνο το ψηλό byte κινείται και μόνο κατά 8.
; ---------------------------------------------------------------------------
hud_char:
        call    hud_seen
        jr      nc,hc_draw
        ld      b,1
        jp      hud_adv                 ; ίδιο κελί: μόνο προχώρημα
hc_draw:
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
; Περνά από το hud_cell και άρα από την κρυφή μνήμη. Ηταν χύμα γέμισμα οκτώ
; γραμμών, δέκα φορές φθηνότερο ανά κελί — αλλά ένα κενό που ΔΕΝ περνά από την
; κρυφή μνήμη την αφήνει να λέει ψέματα: το επόμενο κελί με τον ίδιο κωδικό
; θα παραλειπόταν και το κενό θα έμενε στην οθόνη.
; ---------------------------------------------------------------------------
hud_blank:
        ld      a,b
        or      a
        ret     z
hbl_col:
        push    bc
        xor     a                       ; pen 0: δεκαέξι μηδενικά, ταυτόσημα
        call    hud_cell                ; με το κενό της γραμματοσειράς
        pop     bc
        djnz    hbl_col
        ret

; ---------------------------------------------------------------------------
; hud_text7 — HL = κείμενο στην ΤΡΑΠΕΖΑ 7 (§4.2, src/uitext.asm).
;
; ΟΛΑ τα κείμενα του παιχνιδιού ζουν εκεί από το βήμα 23, γιατί η τράπεζα 0
; τελείωσε. Σελιδοποιεί την 7, τυπώνει, και ξαναβάζει την 1 — που είναι αυτό
; που βλέπει ο υπόλοιπος κώδικας του βρόχου. Η μόνη συμβολοσειρά που ΔΕΝ περνά
; από εδώ είναι το όνομα του καταλόγου (bd_name), που ζει στην τράπεζα 2.
; ---------------------------------------------------------------------------
hud_text7:
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        call    hud_text
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; hud_text — HL = κείμενο, τερματισμένο με 0, σε μνήμη που φαίνεται ήδη.
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
        ld      (hce_pen),a
        or      #80                     ; κωδικός συμπαγούς: #80 + pen
        call    hud_seen
        ld      a,(hce_pen)             ; ΟΧΙ pop af: θα έσβηνε το carry
        jr      nc,hce_draw
        ld      b,1
        jp      hud_adv
hce_draw:
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
        call    hud_text7
        ld      hl,(EC_O2PROD)
        ld      de,(EC_O2USE)
        call    hud_bar_safe
        call    hud_space
        ld      hl,txt_pwr
        call    hud_text7
        ld      hl,(EC_PSTORE)
        ld      de,(EC_PCAP)
        call    hud_bar_safe
        call    hud_space
        ld      hl,txt_h2o
        call    hud_text7
        ld      hl,(EC_STOCK + S_WATER*2)
        ld      de,EC_CAP
        call    hud_bar
        call    hud_space
        ld      hl,txt_fod
        call    hud_text7
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
        call    hud_text7
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
        call    hud_text7
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
        call    hud_text7
        call    hud_space
        call    hud_alert

        ; ΟΙ ΣΕΙΡΕΣ 3-4 ΔΕΝ ΑΓΓΙΖΟΝΤΑΙ ΕΔΩ. Τις κατέχει ο πίνακας επιλογής
        ; (§9.3), που ξέρει μόνος του πότε άλλαξε κάτι. Ως το βήμα 19 το
        ; hud_draw τις έσβηνε και τις ογδόντα σε κάθε κλήση και το ui_panel τις
        ; ξανάγραφε αμέσως μετά — 160 κελιά ανά τικ HUD, περισσότερα από τα 120
        ; που δείχνουν κάτι.
        ret

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
        jp      hud_text7

; --- κείμενα ---------------------------------------------------------------

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
hce_pen:    db 0
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
hud_sp:     dw 0     ; δείκτης μέσα στο G_hud_shadow, 0 = σειρά 3-4
