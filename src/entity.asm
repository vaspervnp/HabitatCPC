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
; 32 = F_WORKING (src/jobs.asm), 64 = F_SUITPH (src/suit.asm, βήμα 90)

NO_EDGE     equ 255
NO_SLOT     equ 255
        ; Το N_AGENT (188· 128 ως το βήμα 172) είναι στο src/const.asm.
        ; κανένα id στην κρυφή μνήμη φιγούρων (βήμα 172): το 192-255 των οκτώ
        ; σελίδων των δεύτερων πεδίων είναι δική της (src/object.asm, of_at)
        assert  N_AGENT <= DF_L

; --- ΦΤΑΝΕΙ. B = edge + 1, H = AG_PG + 3, L = id. ---
; Πριν από το ent_move_slice, για να το φτάνει το jr του em_trans.
em_arrive:
        ; ο κόμβος στην άλλη άκρη: node_adj[node*8 + edge]
        ld      c,l                     ; C = id
        ld      h,AG_PG + 1
        ld      a,(hl)                  ; node
        add     a,(G_node_adj >> 3) & 255
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        add     hl,hl
        dec     b                       ; edge < 8: χωρίς κρατούμενο
        ld      a,l
        add     a,b
        ld      l,a
        ld      a,(hl)                  ; ο κόμβος-στόχος
        ld      b,a                     ; B = στόχος, C = id

        ; Μπαίνει ΠΑΝΤΑ, με θέση ή χωρίς. Το δαχτυλίδι έχει οκτώ θέσεις
        ; επειδή τόσες ζωγραφίζει το sprite — δεν είναι πόρτα. Οσο ήταν,
        ; ένας γεμάτος θόλος με χαλασμένη μηχανή δεν επισκευαζόταν ποτέ.
        push    bc
        call    ent_claim               ; A = θέση, ή 255 αν δεν χωρά
        pop     bc
        ld      l,c
        ld      h,AG_PG + 1
        ld      (hl),b                  ; node = στόχος
        set     3,h                     ; AG_PG + 1 + AG_HI
        ld      (hl),a                  ; slot
        inc     h
        ld      (hl),NO_EDGE
        inc     h
        res     3,h                     ; AG_PG + 3
        ld      (hl),0                  ; progress = 0
        ; Οποιος ταξίδευε μέσα φτάνει μέσα: η αναχώρηση ρώτησε ήδη το en_in
        ; του στόχου. Μόνο όποιος ερχόταν απ' έξω ρωτά — μπαίνει σε airlock;
        ; (βήμα 87· H = AG_PG + 3, L = id)
        ; Και η φιγούρα: όποιος ερχόταν από έξω σταματά, και όποιος φτάνει
        ; σε δομή στέκεται δίπλα της (βήμα 89). Μέσα, σε θόλο, τον δείχνει ο
        ; δακτύλιος.
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS
        jr      z,ea_out
        bit     6,b                     ; κόμβος < 64 (assert): θόλος
        jr      z,ems_nx
        jr      ems_mark
ea_out:
        ld      a,b
        call    en_in                   ; κρατά BC
        ld      l,c
        jr      nc,ems_mark             ; έξω, και μένει
        ld      h,AG_PG
        set     1,(hl)                  ; μπήκε
        jr      ems_mark

; --- ΤΑΞΙΔΕΥΕΙ. A = edge + 1, L = id. ---
em_trans:
        ld      b,a                     ; B = edge + 1
        ld      h,AG_ROLE >> 8
        ld      a,(hl)                  ; role
        and     7
        add     a,role_speed & 255      ; ο πίνακας σε μία σελίδα (assert):
        ld      e,a                     ; 3 us λιγότερα από το adc/sub
        ld      d,role_speed >> 8
        ld      a,(de)                  ; ταχύτητα
        ld      h,AG_PG + 3
        add     a,(hl)                  ; + progress
        jr      c,em_arrive
        ld      (hl),a                  ; ακόμη στον δρόμο
        ; Στον σωλήνα δεν φαίνεται· στο έδαφος η φιγούρα του προχωρά (βήμα 89).
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS
        jr      nz,ems_nx
ems_mark:
        call    fg_mark
        jr      ems_nx

; ---------------------------------------------------------------------------
; ent_move_slice — C = πρώτος πράκτορας, B = πλήθος. Αύξουσα σειρά (§7.1).
;
; ΤΟ ΒΗΜΑ ΤΟΥ ΠΡΑΚΤΟΡΑ ΕΙΝΑΙ ΜΕΣΑ ΣΤΟΝ ΒΡΟΧΟ (βήμα 89). Ως τότε ήταν ρουτίνα,
; το ent_move_one, με έναν μόνο καλούντα: ένα call ανά πράκτορα, 5 us, και τα
; ret του γίνονται jr στο ems_nx με το ίδιο κόστος. 60 us ανά φέτα των
; δώδεκα — περισσότερα από όσα κόστισε η φιγούρα έξω στην κίνηση (fg_mark).
;
; Το id έρχεται στο L και μένει σε καταχωρητή (L, ή D και C όπου το HL
; χρειάζεται αλλού): τα πεδία είναι σε σελίδες, οπότε ένα πεδίο είναι ένα
; `ld h` μακριά (ως το βήμα 171 και ένα `set`/`res 7,l`). Ως το βήμα 59 κάθε πεδίο ξαναδιάβαζε
; το em_id· τώρα γράφεται μόνο όταν κάποιος φεύγει από κόμβο, όπου το θέλει το
; ent_release.
; ---------------------------------------------------------------------------
ent_move_slice:
        inc     b                       ; φέτα μηδέν: το djnz θα έκανε 256 γύρους
        dec     b
        ret     z
        ; Ο ΜΕΤΡΗΤΗΣ ΚΑΙ ΤΟ ID ΣΤΟ ΣΚΙΩΔΕΣ BC (βήμα 87). Το push/pop γύρω από
        ; κάθε πράκτορα ήταν 7 us· δύο exx είναι 2. Το βήμα του πράκτορα και
        ; ό,τι καλεί δεν αγγίζουν σκιώδεις, και το ISR ούτε (src/isr.asm).
        ; ΚΑΙ ΟΙ ΣΗΜΑΙΕΣ ΣΤΟ ΣΚΙΩΔΕΣ HL (βήμα 173): H' = AG_PG, L' = id. Ο
        ; νεκρός, ή η άδεια θέση, δεν βγαίνει ποτέ από τα σκιώδη — 41 T, 64 ως
        ; το 172 — και ο ζωντανός κερδίζει το ld h,AG_PG, 7 T. Με 160 θέσεις
        ; αποίκων μια αποικία των 80 έχει 80 άδειες σε κάθε περιστροφή.
        push    bc
        exx
        pop     bc
        ld      l,c                     ; L' = ο πρώτος (ως το βήμα 172 το C', με res 7,c)
        ld      h,AG_PG
ems_lp:
        bit     0,(hl)                  ; F_ALIVE
        jr      z,ems_dead
        ld      a,l
        inc     l
        exx
        ld      l,a
        ld      h,AG_EDGE >> 8
        ld      a,(hl)                  ; edge
        inc     a
        jr      nz,em_trans             ; != 255 -> ταξιδεύει

; --- ΣΤΑΘΕΡΟΣ: χρειάζεται να ξεκινήσει; ---
        res     3,h                     ; AG_PG + 2
        ld      e,(hl)                  ; dest
        dec     h                       ; AG_PG + 1
        ld      a,(hl)                  ; node
        cp      e
        jr      z,ems_nx                ; είναι ήδη εκεί
        ld      (em_node),a
        ld      d,l                     ; D = id

        ; --- NEXTHOP[node][dest] : μία ανάγνωση, μία σελιδοποίηση. Η γραμμή
        ; είναι #4000 + node*128: (node + 128) / 2 στο H, και το bit που
        ; περισσεύει πάνω από το dest στο L (dest < 128). ---
        add     a,#80
        rra
        ld      h,a
        ld      a,0
        rra
        or      e
        ld      l,a
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      a,(hl)
        ld      c,PAGE_B6 & 255         ; το B είναι ακόμη GA_PORT / 256
        out     (c),c
        ld      l,d
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
        ld      h,AG_PG + 1
        ld      a,(hl)                  ; node
        inc     h
        ld      (hl),a                  ; dest = node
        ld      h,AG_TASK >> 8
        ld      (hl),NO_TASK
ems_nx:
        exx
        djnz    ems_lp
        exx
        ret
ems_dead:
        inc     l
        djnz    ems_lp
        exx
        ret

em_have:
        ; --- ποια θέση της λίστας γειτνίασης είναι ο nh; ---
        ld      e,a                     ; E = nh
        ld      (em_nh),a
        ld      a,l
        ld      (em_id),a
        ld      a,(em_node)
        ld      l,a
        ld      h,NODEPG
        ld      c,(hl)                  ; deg[node]
        inc     c
        dec     c
        jr      z,ems_nx                ; κόμβος χωρίς ακμές — δεν συμβαίνει
        ld      b,0
        ; G_node_adj + node*8 = (G_node_adj/8 + node) * 8, χωρίς κρατούμενο
        ; στο κάτω byte (assert)
        add     a,(G_node_adj >> 3) & 255
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      a,e
        cpir
        jr      nz,ems_nx               ; μπαγιάτικο NEXTHOP — μένει ακίνητος
        dec     l
        ld      a,l
        and     7                       ; k: η λίστα ξεκινά σε πολλαπλάσιο του 8
        ld      c,a

        ; Αν δούλευε, ο θόλος χάνει έναν χειριστή καθώς βγαίνει. Είναι ο
        ; καθρέφτης της άφιξης στο jobs.asm, και χωρίς αυτό οι χειριστές
        ; μόνο ανεβαίνουν: ο θόλος θυμάται κόσμο που έφυγε πριν από ώρα.
        ld      l,d                     ; το id, από την αρχή του σταθερού
        ld      h,AG_PG
        bit     5,(hl)                  ; F_WORKING (assert στο jobs.asm)
        jr      z,emf_rel
        res     5,(hl)
        ld      a,(em_node)
        call    op_ptr                  ; θόλος, ή ορυχείο (βήμα 94)· κρατά το BC
        dec     (hl)
emf_rel:
        ; ελευθερώνει τη θέση του και μπαίνει στην ακμή C
        call    ent_release             ; κρατά το BC
        ld      a,(em_id)
        ld      l,a
        ld      h,AG_PG + 3
        ld      (hl),0                  ; progress = 0
        ld      h,AG_EDGE >> 8
        ld      (hl),c                  ; edge = k
        ; --- ΜΕΣΑ Ή ΕΞΩ (βήμα 87). Οποιος ξεκινά έξω μένει έξω. Οποιος
        ; ξεκινά μέσα μένει μέσα μόνο σε διάδρομο προς έτοιμο μέρος με αέρα,
        ; και όχι από δομή σε δομή: δύο airlock τα ενώνει μόνο το έδαφος. Το
        ; «ξεκινά μέσα» είναι η σημαία, όχι ξανά το en_in του κόμβου. ---
        ; Και η φιγούρα (βήμα 89): φαίνεται όποιος φεύγει έξω ή από δομή.
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS
        jp      z,ems_mark
        ld      a,(em_node)
        ld      b,a                     ; B = από πού, για μετά το en_in
        ld      hl,em_nh
        and     (hl)
        and     MAX_DOME                ; και οι δύο 64 ή πάνω: δομή με δομή
        jr      nz,emd_put              ; το and άφησε CY = 0: έξω
        ld      a,(hl)
        call    en_in                   ; src/door.asm· κρατά BC
        jr      nc,emd_put
        bit     6,b                     ; μέσα, και μένει: από θόλο δεν
        jp      z,ems_nx                ; φαινόταν, από airlock ναι
        ld      a,(em_id)
        ld      l,a
        jp      ems_mark
emd_put:
        ld      a,(em_id)
        ld      l,a
        ld      h,AG_PG
        res     1,(hl)                  ; F_INDOORS: βγαίνει
        ld      h,AG_PG + 7
        ld      (hl),SUIT_TRIP          ; με γεμάτη στολή, πάντα (βήμα 90)
        jp      ems_mark

; fg_mark — L = πράκτορας: η φιγούρα του έξω ίσως άλλαξε (src/figure.asm).
; Ενα byte ανά πράκτορα, στη σελίδα MKPG (ως το βήμα 171 στο πάνω μισό του
; node_occ, όπου το bit 7 του L δεν μετρούσε), λέει «είναι ήδη στη λίστα
; αλλαγών»: μία εγγραφή DK_AGENT το πολύ, όσο γρήγορα κι αν κινείται. Το σβήνει
; το dh_agent. Χαλάει A, B, D, HL.
fg_mark:
        ld      h,MKPG
        ld      a,(hl)
        or      a
        ret     nz
        inc     (hl)
        ld      b,l
        ld      a,DK_AGENT
        jp      wh_push


; ---------------------------------------------------------------------------
; ent_claim — A = κόμβος. Επιστρέφει A = θέση, ή 255 αν γέμισε.
;
; Η σειρά γεμίσματος είναι το corr_fill των assets (0,4,2,6,1,5,3,7) ώστε οι
; άνθρωποι να μη μοιάζουν στοιβαγμένοι στο δαχτυλίδι.
; ---------------------------------------------------------------------------
ent_claim:
        ld      l,a
        ld      h,OCCPG
        ld      c,(hl)                  ; μάσκα κατοχής
        push    hl
        ld      de,G_corr_fill
        ld      b,8
ec_lp:
        ld      a,(de)                  ; η θέση που δοκιμάζουμε
        ld      hl,bit_tab
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)                  ; 1 << θέση
        and     c
        jr      z,ec_free
        inc     e                       ; οκτώ bytes σε μία σελίδα (assert)
        djnz    ec_lp
        pop     hl
        ld      a,NO_SLOT
        ret
ec_free:
        ld      a,(hl)
        or      c
        pop     hl
        ld      (hl),a                  ; η μάσκα με τη νέα θέση πιασμένη
        ld      a,(de)                  ; ο αριθμός της θέσης
        ld      c,a
        ld      a,l                     ; ο κόμβος
        cp      MAX_DOME
        ld      a,c
        ret     nc                      ; δομή: δεν έχει δαχτυλίδι
        push    af                      ; το wh_push χαλάει ό,τι χαλάει ο χειριστής
        ld      b,l
        xor     a                       ; DK_SLOT
        call    wh_push
        pop     af
        ret

; ---------------------------------------------------------------------------
; ent_release — ελευθερώνει τη θέση του (em_id) στον (em_node). Κρατά το BC.
; ---------------------------------------------------------------------------
ent_release:
        push    bc
        ld      a,(em_id)
        ld      l,a
        ld      h,AG_SLOT >> 8
        ld      a,(hl)                  ; slot
        cp      NO_SLOT
        jr      z,er_out
        ld      (hl),NO_SLOT
        ld      c,a                     ; C = θέση, για το wh_push
        ld      hl,bit_tab
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(em_node)
        ld      e,a
        ld      d,OCCPG
        ld      a,(de)
        or      (hl)
        xor     (hl)                    ; μάσκα & ~(1 << θέση)
        ld      (de),a
        ; Η θέση άδειασε: η οθόνη πρέπει να σβήσει τη φιγούρα. Οι δομές δεν
        ; έχουν δακτύλιο, οπότε μόνο οι θόλοι.
        ld      a,e
        cp      MAX_DOME
        jr      nc,er_out
        ld      b,a
        xor     a                       ; DK_SLOT
        call    wh_push
er_out:
        pop     bc
        ret

; Διπλάσιες από την πρώτη εκτίμηση: με τις παλιές, μια ακμή ήθελε έξι
; περιστροφές και μια διαδρομή πέντε αλμάτων κρατούσε όσο και η ανάγκη που
; σε έστειλε — κανείς δεν πρόφταινε ποτέ να πιάσει δουλειά.
role_speed: db 96,96,88,104,112,128,144,120
bit_tab:    db 1,2,4,8,16,32,64,128

em_id:      db 0
em_node:    db 0
em_nh:      db 0                ; ο επόμενος κόμβος, για το μέσα-έξω (βήμα 87)

        assert  F_ALIVE == 1 && N_AGENT <= 256 && DK_SLOT == 0
        assert  (AG_PG & 15) == 0 && AG_HI == 8      ; set 3,h: το δεύτερο πεδίο
        assert  NO_EDGE == 255 && (PAGE_B5 >> 8) == (PAGE_B6 >> 8)
        assert  (G_node_adj & 7) == 0 && ((G_node_adj >> 3) & 255) + 128 <= 256
        assert  (G_corr_fill & 255) <= 256 - 8
        assert  (role_speed & 255) <= 248
        assert  MAX_DOME == 64
