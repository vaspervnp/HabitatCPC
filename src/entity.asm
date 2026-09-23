; entity.asm — οι πράκτορες και η κίνησή τους (§6.1, §6.3)
;
; Δομή-από-πίνακες: ένα πεδίο ανά πίνακα των 128, δύο πεδία ανά σελίδα. Μια
; ανάγνωση πεδίου είναι `ld h,σελίδα / ld l,id / ld a,(hl)` — και γι' αυτό το
; agent_fields ΠΡΕΠΕΙ να είναι σε σελίδα.
;
; Η κίνηση έχει δύο καταστάσεις και τίποτε άλλο: στέκεται σε κόμβο, ή διασχίζει
; ακμή. Ο επόμενος κόμβος βγαίνει από μία ανάγνωση του NEXTHOP — χωρίς
; αναζήτηση, χωρίς λίστα ανοιχτών, χωρίς αποθηκευμένη διαδρομή.
;
; ΤΟ ΠΑΡΑΘΥΡΟ. Οι πράκτορες ζουν στην τράπεζα 6 και το NEXTHOP στην 5 — δεν
; φαίνονται ταυτόχρονα. Η αναζήτηση σελιδοποιεί την 5, διαβάζει ΕΝΑ byte, και
; γυρίζει την 6. Δύο out ανά πράκτορα που ξεκινά ταξίδι, δηλαδή ~10 us — και
; μόνο γι' αυτούς, όχι για όλους.
;
; ΑΠΟΚΛΙΣΗ ΑΠΟ ΤΟ §6.1, ΣΚΟΠΙΜΗ: το πεδίο `edge` κρατά τη θέση του γείτονα
; μέσα στη λίστα γειτνίασης του κόμβου (0..7), όχι καθολικό id διαδρόμου. Ετσι
; ο κόμβος-στόχος βγαίνει με μία ανάγνωση αντί για ψάξιμο στον πίνακα
; διαδρόμων.

; Τα AG_* και το OCCPG είναι στο const.asm — τα διαβάζει και ο renderer.

F_ALIVE     equ 1
F_INDOORS   equ 2
F_ASLEEP    equ 4
F_SICK      equ 8
F_IDLE      equ 16

NO_EDGE     equ 255
NO_SLOT     equ 255
N_AGENT     equ 128

; ---------------------------------------------------------------------------
; ent_move_slice — C = πρώτος πράκτορας, B = πλήθος. Αύξουσα σειρά (§7.1).
; ---------------------------------------------------------------------------
ent_move_slice:
        inc     b                       ; φέτα μηδέν: το djnz θα έκανε 256 γύρους
        dec     b
        ret     z
ems_lp:
        ld      a,c
        ld      (em_id),a
        push    bc
        call    ent_move_one
        pop     bc
        ld      a,c
        inc     a
        and     N_AGENT - 1
        ld      c,a
        djnz    ems_lp
        ret

; ---------------------------------------------------------------------------
; ent_move_one — ένα βήμα για τον (em_id).
; ---------------------------------------------------------------------------
ent_move_one:
        ld      a,(em_id)
        ld      h,AG_PG
        ld      l,a
        ld      a,(hl)
        and     F_ALIVE
        ret     z

        ld      a,(em_id)
        ld      h,AG_PG + 2
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; edge
        inc     a
        jp      nz,em_trans             ; != 255 -> ταξιδεύει

; --- ΣΤΑΘΕΡΟΣ: χρειάζεται να ξεκινήσει; ---
        ld      a,(em_id)
        ld      h,AG_PG + 2
        ld      l,a
        ld      a,(hl)                  ; dest
        ld      e,a
        ld      h,AG_PG + 1
        ld      a,(em_id)
        ld      l,a
        ld      a,(hl)                  ; node
        ld      (em_node),a
        cp      e
        ret     z                       ; είναι ήδη εκεί

        ; --- NEXTHOP[node][dest] : μία ανάγνωση, μία σελιδοποίηση ---
        ld      h,a
        ld      l,0
        srl     h
        rr      l                       ; HL = node*128
        ld      a,l
        add     a,e                     ; + dest  (δεν κρατάει: l = 0 ή 128)
        ld      l,a
        set     6,h                     ; + &4000
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      a,(hl)
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        cp      255
        jr      nz,em_have

        ; ΑΠΡΟΣΙΤΟΣ: ΠΑΡΑΙΤΕΙΤΑΙ ΚΑΙ ΑΦΗΝΕΙ ΚΑΙ ΤΗ ΔΟΥΛΕΙΑ. Μόνο ο προορισμός
        ; δεν έφτανε: ο πίνακας εργασιών κρατά την ανάθεση όσο το task του
        ; πράκτορα δείχνει σε αυτήν, οπότε μια εργασία που δόθηκε μέσα στα ~5
        ; δευτερόλεπτα της ανοικοδόμησης δρομολόγησης (§6.4) κολλούσε ΓΙΑ
        ; ΠΑΝΤΑ πάνω σε κάποιον που είχε ήδη παραιτηθεί. Μετρημένο: ένας θόλος
        ; του παίκτη τελείωνε άλλοτε σε 300 frames και άλλοτε σε 10.800 — όσο
        ; χρειαζόταν για να πεινάσει ο μηχανικός, που είναι το μόνο άλλο
        ; πράγμα που καθαρίζει το task.
        ld      a,(em_node)
        ld      e,a
        ld      a,(em_id)
        ld      h,AG_PG + 2
        ld      l,a
        ld      (hl),e                  ; dest = node
        ld      h,AG_PG + 3             ; +128 = task
        set     7,l
        ld      (hl),NO_TASK
        ret

em_have:
        ld      (em_nh),a
        ; --- ποια θέση της λίστας γειτνίασης είναι ο nh; ---
        ld      a,(em_node)
        ld      h,NODEPG
        ld      l,a
        ld      b,(hl)                  ; deg[node]
        inc     b
        dec     b
        ret     z                       ; κόμβος χωρίς ακμές — δεν συμβαίνει
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_node_adj
        add     hl,de
        ld      a,(em_nh)
        ld      c,0
em_scan:
        cp      (hl)
        jr      z,em_found
        inc     hl
        inc     c
        djnz    em_scan
        ret                             ; μπαγιάτικο NEXTHOP — μένει ακίνητος

em_found:
        ; Αν δούλευε, ο θόλος χάνει έναν χειριστή καθώς βγαίνει. Είναι ο
        ; καθρέφτης της άφιξης στο jobs.asm, και χωρίς αυτό οι χειριστές
        ; μόνο ανεβαίνουν: ο θόλος θυμάται κόσμο που έφυγε πριν από ώρα.
        ld      a,(em_id)
        ld      h,AG_PG
        ld      l,a
        ld      a,(hl)
        and     F_WORKING
        jr      z,emf_rel
        ld      a,(hl)
        and     255 - F_WORKING
        ld      (hl),a
        ld      a,(em_node)
        cp      MAX_DOME
        jr      nc,emf_rel
        call    jb_dome_ptr
        ld      de,D_OPS
        add     hl,de
        dec     (hl)
emf_rel:
        ; ελευθερώνει τη θέση του και μπαίνει στην ακμή C
        call    ent_release
        ld      a,(em_id)
        ld      h,AG_PG + 2
        ld      l,a
        set     7,l
        ld      (hl),c                  ; edge = k
        ld      h,AG_PG + 3
        ld      l,a
        ld      (hl),0                  ; progress = 0
        ret

; --- ΤΑΞΙΔΕΥΕΙ ---
em_trans:
        ld      a,(em_id)
        ld      h,AG_PG
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; role
        and     7
        ld      hl,role_speed
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      e,(hl)                  ; ταχύτητα

        ld      a,(em_id)
        ld      h,AG_PG + 3
        ld      l,a
        ld      a,(hl)
        add     a,e
        jr      c,em_arrive
        ld      (hl),a                  ; ακόμη στον σωλήνα
        ret

em_arrive:
        ; ο κόμβος στην άλλη άκρη: node_adj[node*8 + edge]
        ld      a,(em_id)
        ld      h,AG_PG + 1
        ld      l,a
        ld      a,(hl)                  ; node
        ld      (em_node),a
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_node_adj
        add     hl,de
        ld      a,(em_id)
        ld      d,h
        ld      e,l
        ld      h,AG_PG + 2
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; edge
        add     a,e
        ld      e,a
        ld      a,0
        adc     a,d
        ld      d,a
        ld      a,(de)                  ; ο κόμβος-στόχος
        ld      (em_dst),a

        ; Μπαίνει ΠΑΝΤΑ, με θέση ή χωρίς. Το δαχτυλίδι έχει οκτώ θέσεις
        ; επειδή τόσες ζωγραφίζει το sprite — δεν είναι πόρτα. Οσο ήταν,
        ; ένας γεμάτος θόλος με χαλασμένη μηχανή δεν επισκευαζόταν ποτέ.
        call    ent_claim               ; A = θέση, ή 255 αν δεν χωρά
em_landed:
        ld      e,a                     ; E = θέση
        ld      a,(em_id)
        ld      h,AG_PG + 1
        ld      l,a
        ld      a,(em_dst)
        ld      (hl),a                  ; node = στόχος
        set     7,l
        ld      (hl),e                  ; slot
        ld      a,(em_id)
        ld      h,AG_PG + 2
        ld      l,a
        set     7,l
        ld      (hl),NO_EDGE
        ld      h,AG_PG + 3
        res     7,l
        ld      (hl),0                  ; progress = 0
        ret

; ---------------------------------------------------------------------------
; ent_claim — A/(em_dst) = κόμβος. Επιστρέφει A = θέση, ή 255 αν γέμισε.
;
; Η σειρά γεμίσματος είναι το corr_fill των assets (0,4,2,6,1,5,3,7) ώστε οι
; άνθρωποι να μη μοιάζουν στοιβαγμένοι στο δαχτυλίδι.
; ---------------------------------------------------------------------------
ent_claim:
        ld      a,(em_dst)
        ld      h,OCCPG
        ld      l,a
        ld      c,(hl)                  ; μάσκα κατοχής
        push    hl
        ld      hl,G_corr_fill
        ld      b,8
ec_lp:
        ld      a,(hl)                  ; η θέση που δοκιμάζουμε
        push    hl
        ld      hl,bit_tab
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)                  ; 1 << θέση
        pop     hl
        ld      e,a
        and     c
        jr      z,ec_free
        inc     hl
        djnz    ec_lp
        pop     hl
        ld      a,NO_SLOT
        ret
ec_free:
        ld      a,(hl)                  ; ο αριθμός της θέσης
        ld      d,a
        ld      a,c
        or      e
        pop     hl
        ld      (hl),a                  ; η μάσκα με τη νέα θέση πιασμένη
        ld      a,d
        ld      (ec_slot),a
        ld      a,(em_dst)
        cp      MAX_DOME
        jr      nc,ec_done
        ld      b,a
        ld      a,(ec_slot)
        ld      c,a
        ld      a,DK_SLOT
        call    wh_push
ec_done:
        ld      a,(ec_slot)
        ret

ec_slot:    db 0

; ---------------------------------------------------------------------------
; ent_release — ελευθερώνει τη θέση του (em_id) στον (em_node).
; ---------------------------------------------------------------------------
ent_release:
        push    bc
        ld      a,(em_id)
        ld      h,AG_PG + 1
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; slot
        cp      NO_SLOT
        jr      z,er_out
        ld      (er_slot),a
        ld      (hl),NO_SLOT
        ld      hl,bit_tab
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        cpl                             ; ~(1<<slot)
        ld      c,a
        ld      a,(em_node)
        ld      h,OCCPG
        ld      l,a
        ld      a,(hl)
        and     c
        ld      (hl),a
        ; Η θέση άδειασε: η οθόνη πρέπει να σβήσει τη φιγούρα. Οι δομές δεν
        ; έχουν δακτύλιο, οπότε μόνο οι θόλοι.
        ld      a,(em_node)
        cp      MAX_DOME
        jr      nc,er_out
        ld      b,a
        ld      a,(er_slot)
        ld      c,a
        ld      a,DK_SLOT
        call    wh_push
er_out:
        pop     bc
        ret

er_slot:    db 0

bit_tab:    db 1,2,4,8,16,32,64,128
; Διπλάσιες από την πρώτη εκτίμηση: με τις παλιές, μια ακμή ήθελε έξι
; περιστροφές και μια διαδρομή πέντε αλμάτων κρατούσε όσο και η ανάγκη που
; σε έστειλε — κανείς δεν πρόφταινε ποτέ να πιάσει δουλειά.
role_speed: db 96,96,88,104,112,128,144,120

em_id:      db 0
em_node:    db 0
em_dst:     db 0
em_nh:      db 0
