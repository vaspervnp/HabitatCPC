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
DHS_VAC_US  equ 18000               ; θέση δακτυλίου που αδειάζει και φαίνεται, πέρα
                                    ; από το DK_SLOT (dhs_vacate, μετρημένο)

; τα DK_* είναι στο const.asm — τα σπρώχνει και η προσομοίωση

; ---------------------------------------------------------------------------
; dirty_reset — άδεια λίστα.
; ---------------------------------------------------------------------------
dirty_reset:
        xor     a
        ld      (rv_pend),a
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
        or      a                       ; DK_SLOT είναι το μηδέν
        jr      nz,dp_nofig
        dec     a
        ld      (dirty_figs),a          ; «ο πίνακας φιγούρων είναι μπαγιάτικος»
        xor     a                       ; και πίσω το DK_SLOT
dp_nofig:
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
        ld      a,(dirty_num)
        or      a
        ret     z
        ; Ο ΠΙΝΑΚΑΣ ΦΙΓΟΥΡΩΝ ξαναχτίζεται εδώ, ΜΟΝΟ αν σπρώχτηκε θέση
        ; δακτυλίου από τότε. Το dh_slot διαβάζει από αυτόν, και όταν η
        ; προσομοίωση μετακινεί αποίκους είναι μπαγιάτικος — η φιγούρα θα
        ; ξαναζωγραφιζόταν εκεί που έφυγε και δεν θα εμφανιζόταν εκεί που πήγε.
        ;
        ; Η σάρωση περνά και τους 128 πράκτορες και κοστίζει ΜΕΤΡΗΜΕΝΑ 9.984 us
        ; — μισό frame. Πολύ ακριβή για να τρέχει σε κάθε πέρασμα της λίστας·
        ; μία φορά ανά ριπή σπρωξιμάτων είναι το σωστό.
        ld      a,(dirty_figs)
        or      a
        jr      z,dt_figs_ok
        xor     a
        ld      (dirty_figs),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        call    ob_fig_scan
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
dt_figs_ok:
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
        ; ΞΕΧΕΙΛΙΣΜΑ 16 BIT = σίγουρα πάνω από τον προϋπολογισμό. Χωρίς αυτό
        ; δύο σειρές διαγωνίου (40.000 + 40.000) έβγαιναν 14.464 και περνούσαν
        ; μαζί σε έναν γύρο· δύο σειρές εργοταξίου τύλιγαν στα 44.464 και
        ; σταματούσαν από τύχη (βήμα 37).
        jr      c,dt_done
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
        ; ΤΟ ΦΑΝΤΑΣΜΑ ΞΑΝΑΜΠΑΙΝΕΙ ΜΙΑ ΦΟΡΑ, στο τέλος. Αν κάποιος χειριστής το
        ; έβγαλε (dt_ghost), κάθε επόμενος ζωγράφισε ελεύθερα από κάτω του.
        ld      a,(dt_hid)
        or      a
        jr      z,dt_out
        xor     a
        ld      (dt_hid),a
        call    gh_swap
dt_out:
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
        ret     z
        call    dt_ghost
        or      1                       ; NZ: «ζωγράφισε»
dt_no:
        ret

; dt_ghost — πέφτει ο θόλος κάτω από το φάντασμα; Τότε το φάντασμα σηκώνεται
; ΠΡΙΝ ζωγραφίσει ο χειριστής, και το dirty_tick το ξαναρίχνει στο τέλος.
;
; Χωρίς αυτό η αναίρεση του φαντάσματος γράφει πίσω bytes που δεν είναι πια στην
; οθόνη (§15): ένα κόκκινο μπάλωμα μέσα σε τελειωμένο θόλο. Το ml_built το
; απέφευγε με ui_hide / ui_show γύρω από ΟΛΗ την επανασχεδίαση. Εδώ πληρώνεται
; μόνο όταν το περίγραμμα του αρχείου (gh_rect) τέμνει το πλαίσιο του θόλου —
; ο κέρσορας πάνω από την ερημιά δεν κοστίζει τίποτα — και πληρώνεται με δύο
; ανταλλαγές (gh_swap), όχι με ένα ui_show που ξαναϋπολογίζει το φάντασμα.
dt_ghost:
        ; ΜΙΑ ΦΟΡΑ ΑΝΑ ΤΙΚ. Η ανταλλαγή δεν αδειάζει το αρχείο, όπως το άδειαζε
        ; η αναίρεση: μια δεύτερη εγγραφή κάτω από το ίδιο φάντασμα θα το
        ; ξανάριχνε στην οθόνη πριν ζωγραφίσει, και στο τέλος θα έμενε
        ; σηκωμένο. Το test_save το βρήκε — μετά το φόρτωμα ξαναζωγραφίζονται
        ; πολλές θέσεις δακτυλίου κάτω από τον κέρσορα, και το πλαίσιό του
        ; χανόταν.
        ld      a,(dt_hid)
        or      a
        ret     nz
        ld      hl,(gh_ptr)
        ld      de,GH_BUF
        or      a
        sbc     hl,de
        ret     z                       ; άδειο αρχείο: τίποτα στην οθόνη
        ld      hl,(clip_x0)
        push    hl
        ld      hl,(clip_y0)
        push    hl
        ld      hl,(gh_bbx)
        ld      (clip_x0),hl
        ld      hl,(gh_bby)
        ld      (clip_y0),hl
        call    ob_vis
        pop     hl
        ld      (clip_y0),hl
        pop     hl
        ld      (clip_x0),hl
        or      a
        ret     z
        ld      (dt_hid),a
        jp      gh_swap

dt_end:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; --- μπαινοβγαίνει άποικος: ΜΙΑ θέση, 16 bytes ---
dh_slot:
        call    dt_prep
        jr      z,dt_end
        ld      a,(dt_b)
        call    ob_fig_one              ; και το ob_x, ob_y της θέσης
        ld      a,(of_fig)
        or      a
        call    z,dhs_vacate            ; ΕΦΥΓΕ: βλ. dhs_vacate
        jr      dt_end

; --- αλλάζει ή χαλάει μηχάνημα, ή μεγαλώνει φυτό: ΜΙΑ υποδοχή ---
; Η ΥΠΟΔΟΧΗ ΠΟΥ ΑΔΕΙΑΖΕΙ (ο εξοπλισμός, βήμα 45) δεν έχει sprite να γράψει
; από πάνω: ό,τι ήταν κάτω από τη μηχανή ξαναστρώνεται όπως για τη θέση
; δακτυλίου που αδειάζει (dhv_rect).
dh_mach:
        call    dt_prep
        jr      z,dt_end
        ld      a,(dt_b)
        ld      hl,d_rec + D_MACH
        call    ob_addu
        ld      a,(hl)
        inc     a
        jr      z,dhm_vac
        call    om_prep                 ; μηχανές ή φυτά, και η τράπεζα τους
        ld      a,(dt_b)
        call    ob_mach_one
        jr      dt_end
dhm_vac:
        ld      a,(dt_b)
        ld      de,G_machine_slots
        call    ob_slot_at
        ld      hl,MACH_H*256 + MACH_W
        call    dhv_rect
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

; --- ένα κτίριο τελείωσε (§6.9 βήμα 4) ---
; ΑΛΛΑΖΕΙ ΜΟΝΟ ΤΟ ΕΣΩΤΕΡΙΚΟ. Το εργοτάξιο ζωγραφίστηκε στην τοποθέτηση με
; δακτύλιο, θόλο, πόρτες και φιγούρες· του έλειπαν το εικονίδιο του δωματίου
; (είχε το κενό, ob_fittings) και οι μηχανές. Αυτά τα δύο είναι όλη η διαφορά,
; και είναι αδιαφανή: γράφουν πάνω από ό,τι ήταν εκεί χωρίς να χρειάζονται το
; από κάτω. Μια ΔΟΜΗ δεν αλλάζει καθόλου — το ob_struct τη ζωγραφίζει ίδια
; χτισμένη ή όχι — οπότε το μόνο που κάνει είναι ο ήχος.
;
; Ως το βήμα 34 αυτό ήταν το ml_built: ολόκληρο το κάδρο από την αρχή, 360 ως
; 920 ms ανάλογα με το τι φαινόταν, για να αλλάξουν ως 1.200 bytes.
dh_built:
        ld      a,SFX_DONE
        call    snd_play
        ld      a,(dt_a)
        cp      MAX_DOME
        ret     nc
        call    dt_prep
        jr      z,dt_end
        call    ob_icon
        call    ob_machines
        jp      dt_end                  ; jr: εκτός εμβέλειας από το βήμα 42

; --- ένα εργοτάξιο εμφανίζεται: ΜΙΑ σειρά tiles του (§6.9 βήμα 4) ---
; Η σειρά βγαίνει από την εγγραφή του θόλου, όχι από το πού ήταν η κάμερα όταν
; μπήκε: αν ο παίκτης σκρολάρει στο μεταξύ, το view_rect κόβει στο νέο κάδρο,
; και ό,τι μπήκε στο κάδρο από τη λωρίδα του σκρολαρίσματος έχει ήδη
; ζωγραφιστεί ολόκληρο. Το dt_prep σηκώνει και το φάντασμα, αν ο παίκτης το
; έφερε από πάνω πριν τελειώσει η εμφάνιση.
dh_site:
        ld      hl,rv_pend
        dec     (hl)
        call    dt_prep
        jp      z,dt_end
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,4                     ; πλευρά σε tiles: 4, 6, 8
        ld      (vr_w),a
        ld      e,a
        ld      a,(d_rec+D_CX)          ; κέντρο σε μισά tiles, ίδια ισοτιμία
        sub     e
        sra     a
        ld      (vr_tx),a
        ld      a,(d_rec+D_CY)
        sub     e
        sra     a
        ld      hl,dt_b
        add     a,(hl)
        ld      (vr_ty),a
        ld      a,1
        ld      (vr_h),a
        call    dt_end
        call    vr_tiles
        ret     z
        ; ΜΟΝΟ Ο ΘΟΛΟΣ, ΟΧΙ ΤΟ ob_draw_all. Το αποτύπωμα είναι δικό του — η
        ; κατοχή δεν αφήνει τίποτα άλλο να πατά μέσα — οπότε κέλυφος και
        ; εξαρτήματα κομμένα στη σειρά είναι ό,τι θα έβγαζε το πλήρες πέρασμα.
        ; Το ob_draw_all θα ρωτούσε πρώτα 64 θόλους, 96 διαδρόμους και όλες τις
        ; δομές: 18 ms σε κάθε σειρά ενός L, για να βρει αυτόν τον έναν. (Από
        ; το ευρετήριο του βήματος 39 θα ήταν ~2 ms, και θα ζωγράφιζε και ό,τι
        ; άλλο αγγίζει τη σειρά — που εδώ δεν υπάρχει.)
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        call    ob_index
        ld      a,(dt_a)
        call    ob_shell
        ld      a,(dt_a)
        call    ob_fittings
        call    ob_clip_full
        jp      dt_end

; --- ένας διάδρομος εμφανίζεται: ΜΙΑ σειρά της διαγωνίου του (§6.9) ---
; Τρία tiles από το (dt_a, dt_b) του κόσμου: όσα αγγίζουν τα δύο διαγώνια
; πλακίδια που μοιράζονται τη σειρά (cr_redraw). Το περίγραμμα μιας διαγωνίου
; n βημάτων είναι τετράγωνο n x n, και ως το βήμα 37 ξαναζωγραφιζόταν όλο σε
; έναν γύρο: 130 ms για 7 βήματα, 45 το έδαφος και 85 τα αντικείμενα.
;
; ΕΔΩ ΧΡΕΙΑΖΕΤΑΙ ΤΟ ob_draw_all, σε αντίθεση με το dh_site. Τα tiles που πατά
; ο διάδρομος είναι δικά του, αλλά τα άλλα δύο του τετραγώνου 2x2 κάθε
; πλακιδίου τα ΑΓΓΙΖΕΙ χωρίς να τα κατέχει — εκεί μπορεί να είναι δομή, άλλος
; θόλος ή ένας διάδρομος που διασταυρώνεται. Ως το βήμα 39 το ob_draw_all
; κόστιζε 30-45 ms ακόμη κι όταν δεν έβρισκε τίποτα· από το ευρετήριο, μια
; σειρά είναι 10-15 ms, και βγαίνει ακόμη μία ανά γύρο (dirty_cost).
dh_crow:
        ld      hl,rv_pend
        dec     (hl)
        ld      a,(dt_a)
        ld      (vr_tx),a
        ld      a,(dt_b)
        ld      (vr_ty),a
        ld      a,3
        ld      (vr_w),a
        ld      a,1
        ld      (vr_h),a
        call    vr_clip
        ret     z
        call    dt_ghost_rect
        ; ΧΩΡΙΣ ΕΔΑΦΟΣ (view_add): ο διάδρομος μόνο προσθέτει, και με το
        ; έδαφος πρώτα ό,τι ήδη φαινόταν στη λωρίδα — η στροφή, η γωνία του
        ; θόλου — έσβηνε για δύο-τρία καρέ ως να ξαναζωγραφιστεί.
        call    ob_draw_all
        jp      ob_clip_full

; dt_ghost_rect — το dt_ghost για ορθογώνιο: πέφτει το clip πάνω στο
; περίγραμμα του αρχείου του φαντάσματος; Τότε το φάντασμα σηκώνεται, μία φορά
; ανά τικ. Ενα άδειο αρχείο έχει περίγραμμα (255, 0) και δεν τέμνει τίποτα.
dt_ghost_rect:
        ld      a,(dt_hid)
        or      a
        ret     nz
        ld      hl,gh_bbx
        ld      de,clip_x0
        call    dtg_ovl
        ret     nc
        ld      hl,gh_bby
        ld      de,clip_y0
        call    dtg_ovl
        ret     nc
        ld      a,1
        ld      (dt_hid),a
        jp      gh_swap

; dtg_ovl — [(HL), (HL+1)) τέμνει το [(DE), (DE+1)); CY αν ναι.
dtg_ovl:
        ld      a,(de)
        inc     hl
        cp      (hl)                    ; αρχή του clip < τέλος του φαντάσματος
        ret     nc
        dec     hl
        inc     de
        ld      a,(hl)
        ex      de,hl
        cp      (hl)                    ; αρχή του φαντάσματος < τέλος του clip
        ret

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
        ld      bc,VIEW_TW * 256 + 3
        call    dk_clamp
        ld      a,c
        ld      (td_c0),a
        ld      a,b
        ld      (td_nc),a
        or      a
        ret     z
        ld      hl,dk_r0
        ld      bc,VIEW_TH * 256 + 3
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

; dk_clamp — (HL) = αρχή, C = μήκος, B = όριο κάδρου. Το μήκος ήταν πάντα 3
; ως το βήμα 34· το view_rect το θέλει όσο το κτίριο ή ο διάδρομος.
; Out: C = αρχή κομμένη, B = πλήθος (0 = εκτός κάδρου).
dk_clamp:
        ld      a,(hl)
        bit     7,a
        jr      z,dkc_pos
        ; αρνητική αρχή: κόψε από μπροστά
        neg
        ld      e,a
        ld      a,c
        sub     e
        jr      c,dkc_out
        jr      z,dkc_out
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
        dw      dh_slot, dh_mach, dh_icon, dh_conn, dh_tile, dh_built, dh_site
        dw      dh_crow

; Μετρημένο κόστος ανά είδος, σε us. Ο προϋπολογισμός δεν έχει ρολόι να
; κοιτάξει· έχει αυτόν τον πίνακα, και το test_dirty τον ελέγχει.
; ΜΕΤΡΗΜΕΝΑ, όχι εκτιμημένα. Το §8.5 έλεγε 64 / 530 / 800 / 450 / 1.600 και τα
; πέντε βγήκαν χαμηλά, από 2x ως 21x: το blit δεν είναι το κόστος — είναι η
; προετοιμασία (σελιδοποίηση, εγγραφή θόλου, πλαίσιο, έλεγχος ορατότητας) που
; πληρώνεται ολόκληρη για να γραφτούν δεκαέξι bytes.


; ---------------------------------------------------------------------------
; dhs_vacate — μια θέση του δακτυλίου άδειασε (dh_slot· ob_x, ob_y = η θέση).
;
; Οταν ΕΡΧΕΤΑΙ άποικος, το αδιαφανές 2x8 του ob_fig_one είναι ό,τι θα έβγαζε
; το πλήρες πέρασμα. Οταν ΦΕΥΓΕΙ, όχι: η «κενή» παραλλαγή είναι ο δακτύλιος
; πάνω σε ΜΑΥΡΟ, και όπου ο δακτύλιος είναι διαφανής το πλήρες πέρασμα δείχνει
; το ΕΔΑΦΟΣ — η αδιαφανής παραλλαγή εκεί βάφει pen 0. Ως το βήμα 42 αυτό άφηνε
; 1-8 bytes λάθος σε 12 από τις 20 θέσεις της αποικίας δοκιμής, και το §15 το
; χρέωνε στο κόψιμο του περάσματος αντικειμένων: ο θόλος ξανασχεδιασμένος
; κομμένος στο 2x8 έβγαζε τα ίδια pixel — γιατί ούτε κι εκείνος ξανάστρωνε
; έδαφος.
;
; Εδώ γίνεται ό,τι κάνει το πλήρες πέρασμα, ΜΟΝΟ στο 2x8: το έδαφος από κάτω
; (το tile, ή τα δύο ως τέσσερα που πιάνει η θέση, μέσα από το ob_blit που
; κόβει), και από πάνω όλα τα αντικείμενα κομμένα στο ίδιο. Μια πρώτη μορφή
; ξανάστρωνε ΟΛΟΚΛΗΡΑ τα tiles (view_rect) και έπρεπε μετά να ξαναζωγραφίσει
; ό,τι πατούσε πάνω τους — εικονίδιο, μηχανές: ως 32,6 ms για 16 bytes.
;
; dhv_rect — το ίδιο για ΟΠΟΙΟΔΗΠΟΤΕ ορθογώνιο στο ob_x, ob_y: L = bytes,
; H = γραμμές. Και για τη μηχανή που βγήκε (dh_mach, βήμα 45): 6x22 αντί 2x8.
; ---------------------------------------------------------------------------
dhs_vacate:
        ld      hl,SLOT_H*256 + SLOT_W
dhv_rect:
        ld      (dhv_w),hl              ; dhv_w, dhv_h διπλανά
        ; --- το clip: το ορθογώνιο, κομμένο στο κάδρο ---
        ld      a,l
        ld      hl,(ob_x)
        ld      de,SCR_W * 256          ; lo = 0, hi = SCR_W
        call    ob_clip
        ret     z
        ld      b,a                     ; cl_n
        ld      a,(cl_start)
        ld      (clip_x0),a
        add     a,b
        ld      (clip_x1),a
        ld      hl,(ob_y)
        ld      a,(dhv_h)
        ld      de,PLAY_LINES * 256
        call    ob_clip
        ; ΤΟ clip_x ΕΧΕΙ ΗΔΗ ΣΤΕΝΕΨΕΙ. Με `ret z` εδώ, μια θέση που φαίνεται
        ; οριζόντια αλλά πέφτει κάτω ή πάνω από το κάδρο άφηνε το clip μια
        ; στήλη δύο bytes, και ΚΑΘΕ επόμενος χειριστής της λίστας ζωγράφιζε
        ; μέσα σε αυτήν — δηλαδή τίποτα. Από το βήμα 42 ως το 45 δεν φάνηκε,
        ; γιατί κανένας θόλος δεν τελείωνε στο κάδρο μετά από τέτοιο άδειασμα·
        ; το test_link του βήματος 45, που περιμένει τον εξοπλισμό, βρήκε έναν
        ; L χωρίς εικονίδιο και χωρίς καμία από τις οκτώ μηχανές του.
        jp      z,ob_clip_full
        ld      b,a
        ld      a,(cl_start)
        ld      (clip_y0),a
        add     a,b
        ld      (clip_y1),a
        ; --- ΤΟ ΚΟΣΤΟΣ ΤΟ ΞΕΡΕΙ ΜΟΝΟ ΑΥΤΟΣ. Ο πίνακας λέει 1.500 για το
        ; DK_SLOT, όσο κοστίζει ένας άποικος που ΕΡΧΕΤΑΙ. Ενα άδειασμα που
        ; φαίνεται κοστίζει ως 18 ms ακόμη: ο θόλος, κομμένος στο 2x8, περνά
        ; ακόμη από ~25 blit. Το λέει στον dirty_tick, για να μην ακολουθήσει
        ; τίποτε άλλο στο ίδιο καρέ. Το 16 bit ξεχειλίζει ως «πάνω» (dt_lp).
        ld      hl,(dt_spent)
        ld      de,DHS_VAC_US
        add     hl,de
        jr      nc,dhv_spent
        ld      hl,#FFFF
dhv_spent:
        ld      (dt_spent),hl
        ; --- το έδαφος: κάθε tile που αγγίζει το clip, κομμένο σε αυτό ---
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      a,(clip_y0)
        and     #F0                     ; η γραμμή του πρώτου tile
dhv_row:
        ld      (dhv_y),a
        ld      a,(clip_x0)
        and     #FC
dhv_col:
        ld      (dhv_x),a
        rrca
        rrca                            ; στήλη tile (το x < 80)
        ld      hl,cam_tx
        add     a,(hl)
        ld      b,a
        ld      a,(dhv_y)
        rrca
        rrca
        rrca
        rrca                            ; σειρά tile (το y < 160)
        ld      hl,cam_ty
        add     a,(hl)
        ld      c,a
        call    tile_addr
        ld      (t_wptr),hl
        call    tile_src
        ld      (ob_src),hl
        ld      a,(dhv_x)
        ld      l,a
        ld      h,0
        ld      (ob_x),hl
        ld      a,(dhv_y)
        ld      l,a
        ld      (ob_y),hl
        ld      hl,TILE_H*256 + TILE_W
        ld      a,4                     ; αδιαφανές
        call    ob_put
        ld      a,(dhv_x)
        add     a,TILE_W
        ld      hl,clip_x1
        cp      (hl)
        jr      c,dhv_col
        ld      a,(dhv_y)
        add     a,TILE_H
        ld      hl,clip_y1
        cp      (hl)
        jr      c,dhv_row
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ; --- και από πάνω ό,τι πατά εκεί ---
        call    ob_draw_all
        jp      ob_clip_full

dhv_x:      db 0
dhv_y:      db 0
dhv_w:      db 0
dhv_h:      db 0


dirty_cost:
        dw      1500                    ; θέση δακτυλίου — 16 bytes αδιαφανή
        dw      5000                    ; μηχάνημα ή φυτό — 132 bytes
        dw      2000                    ; εικονίδιο δωματίου — ως 200 bytes
        dw      3000                    ; πόρτα — 16 ζεύγη με μάσκα
        dw      11000                   ; tile + γείτονες σε ελεύθερο έδαφος
        dw      18000                   ; κτίριο που τελείωσε — θόλος M: εικονίδιο
                                        ; + μηχανές (ο L ~42.000, βγαίνει μόνος του)
        dw      55000                   ; μία σειρά εργοταξίου — θόλος M, βγαίνει μόνη
        dw      12000                   ; μία σειρά διαγωνίου — το ob_draw_all από το
                                        ; ευρετήριο (βήμα 39· ήταν 60.000). Μία ανά
                                        ; γύρο ακόμη: δύο θα ήταν 24.000

dirty_ring: defs DIRTY_N * DIRTY_REC
dirty_head: db 0
dirty_num:  db 0
dirty_over: db 0
dirty_figs: db 0
dt_spent:   dw 0
dt_new:     dw 0
dp_kind:    db 0
dt_kind:    db 0
dt_a:       db 0
dt_b:       db 0
dt_hid:     db 0                    ; το dt_ghost έβγαλε το φάντασμα σε αυτό το τικ
rv_pend:    db 0                    ; σειρές εργοταξίου που περιμένουν (DK_SITE)
dk_c0:      db 0
dk_r0:      db 0
dh_ty:      db 0
dh_rows:    db 0
