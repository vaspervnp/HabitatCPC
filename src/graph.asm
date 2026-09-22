; graph.asm — ο γράφος κόμβων και οι δύο πίνακες δρομολόγησης (§6.2, §6.4)
;
; Μία BFS ανά πηγή, 128 πηγές, δύο σειρές των 128 bytes η καθεμία:
;
;       DIST[from][to]      άλματα, 254 = μακριά, 255 = απρόσιτος   (τράπεζα 1)
;       NEXTHOP[from][to]   ο επόμενος κόμβος, 255 = απρόσιτος      (τράπεζα 5)
;
; Και οι δύο σειρές βγαίνουν από την ΙΔΙΑ διάσχιση: όταν η BFS φτάνει πρώτη
; φορά σε γείτονα της πηγής, ο πρώτος κόμβος της διαδρομής είναι ο ίδιος ο
; γείτονας· κάθε άλλος κόμβος τον κληρονομεί από εκείνον που τον ανακάλυψε.
; Χωρίς δεύτερο πέρασμα, χωρίς αποθήκευση διαδρομών.
;
; ΓΙΑΤΙ ΕΙΝΑΙ ΔΙΑΚΟΠΤΟΜΕΝΗ. Μια ολόκληρη πηγή κοστίζει περισσότερο από ένα
; frame. Ο κανόνας 1 του §7.1 λέει ότι κανένα πέρασμα δεν κάνει απεριόριστη
; δουλειά σε ένα frame, οπότε η BFS κόβεται σε **κόμβους**: το rt_slice
; επεκτείνει ως B κόμβους και γυρίζει. Η κατάσταση είναι τέσσερα bytes.
;
; ΓΙΑΤΙ Ο ΠΑΓΚΟΣ ΕΙΝΑΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 2. Η έξοδος γράφεται στις τράπεζες 1 και
; 5, δηλαδή το παράθυρο &4000 αλλάζει μέσα στη ρουτίνα — δύο φορές ανά πηγή.
; Οτιδήποτε διαβάζει η BFS πρέπει να είναι εκτός παραθύρου, και η τράπεζα 2
; είναι πάντα ορατή.

ROWPG       equ G_rt_row / 256
NODEPG      equ G_rt_nodes / 256

RT_DIST     equ G_rt_row                ; [0..127]
RT_NEXT     equ G_rt_row + 128          ; [128..255]
NODE_DEG    equ G_rt_nodes              ; [0..127]
RT_QUEUE    equ G_rt_nodes + 128        ; [128..255]

RT_UNREACH  equ 255
RT_FAR      equ 254
RT_NODES    equ 128                     ; η πλευρά των πινάκων

; ---------------------------------------------------------------------------
; rt_begin — ξεκινά πλήρη ανοικοδόμηση από την πηγή 0.
;
; Τρέχουν ΚΑΙ ΟΙ 128 πηγές, ακόμη κι αν η αποικία έχει δέκα κόμβους. Ένας
; κόμβος που δεν υπάρχει είναι απλώς απομονωμένος, οπότε η σειρά του βγαίνει
; σωστή από μόνη της. Το κέρδος είναι ότι δεν χρειάζεται πέρασμα αρχικοποίησης
; 32 KB, και ότι οι πίνακες δεν έχουν ποτέ μπαγιάτικες σειρές.
; ---------------------------------------------------------------------------
rt_begin:
        xor     a
        ld      (rt_src),a
        ld      (rt_phase),a
        ret

; ---------------------------------------------------------------------------
; rt_slice — ως B επεκτάσεις κόμβων. Επιστρέφει Cy=1 όταν τελείωσαν και οι 128.
;
; Ενας «κόμβος» εδώ είναι μία αφαίρεση από την ουρά μαζί με τους ως 8 γείτονές
; του. Το άνοιγμα (καθάρισμα σειράς) και το κλείσιμο (δύο αντιγραφές των 128
; bytes) μετράνε το καθένα σαν ένας κόμβος — είναι μεγαλύτερα, αλλά σταθερά.
; ---------------------------------------------------------------------------
rt_slice:
        ld      a,(rt_phase)
        or      a
        jr      z,rts_open
        ; --- φάση 1: επέκταση κόμβων ---
rts_expand:
        call    rt_node
        jr      nc,rts_more             ; η ουρά είχε ακόμη κόμβο
        ; η ουρά άδειασε: κλείσιμο και επόμενη πηγή
        call    rt_flush
        ld      a,(rt_src)
        inc     a
        ld      (rt_src),a
        ld      hl,rt_n
        cp      (hl)
        jr      nc,rts_done
        xor     a
        ld      (rt_phase),a
        dec     b
        jr      nz,rt_slice
        or      a                       ; Cy=0 — μένει δουλειά
        ret
rts_more:
        djnz    rts_expand
        or      a
        ret
rts_done:
        scf
        ret
rts_open:
        call    rt_open
        ld      a,1
        ld      (rt_phase),a
        dec     b
        jr      nz,rts_expand
        or      a
        ret

; ---------------------------------------------------------------------------
; rt_open — καθαρίζει τη σειρά και βάζει την πηγή στην ουρά.
; ---------------------------------------------------------------------------
rt_open:
        push    bc                      ; το ldir τρώει το BC — και μαζί του τον
        ld      hl,G_rt_row             ; προϋπολογισμό της φέτας
        ld      (hl),RT_UNREACH
        ld      d,h
        ld      e,l
        inc     de
        ld      bc,255
        ldir                            ; 256 bytes σε 255

        ld      a,(rt_src)
        ld      h,ROWPG
        ld      l,a
        ld      (hl),0                  ; dist[src] = 0
        set     7,l
        ld      (hl),a                  ; next[src] = ο εαυτός
        ld      (RT_QUEUE),a
        xor     a
        ld      (rt_head),a
        inc     a
        ld      (rt_tail),a
        pop     bc
        ret

; ---------------------------------------------------------------------------
; rt_node — μία αφαίρεση από την ουρά. Cy=1 αν η ουρά ήταν άδεια.
; ---------------------------------------------------------------------------
rt_node:
        push    bc
        ld      a,(rt_head)
        ld      hl,rt_tail
        cp      (hl)
        jr      z,rtn_empty
        inc     a
        ld      (rt_head),a
        dec     a

        ld      h,NODEPG
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; A = u
        ld      (rt_u),a

        ld      l,a
        ld      b,(hl)                  ; B = deg[u]   (h=NODEPG)
        inc     b
        dec     b
        jr      z,rtn_out               ; μοναχικός κόμβος

        ; --- C = η απόσταση που θα πάρουν οι γείτονες ---
        ld      h,ROWPG
        ld      l,a
        ld      c,(hl)
        inc     c
        ld      a,c
        cp      RT_FAR
        jr      c,rtn_dok
        ld      c,RT_FAR                ; δεν συμβαίνει με 128 κόμβους· φθηνό
rtn_dok:
        ; --- IXL = ο πρώτος κόμβος της διαδρομής ---
        ; 255 = «είμαστε στην πηγή, βάλε τον ίδιο τον γείτονα»
        ld      a,(rt_u)
        ld      hl,rt_src
        cp      (hl)
        ld      a,RT_UNREACH
        jr      z,rtn_first
        ld      h,ROWPG
        ld      a,(rt_u)
        ld      l,a
        set     7,l
        ld      a,(hl)
rtn_first:
        ld      ixl,a

        ; --- DE = node_adj + u*8 ---
        ld      h,0
        ld      a,(rt_u)
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_node_adj
        add     hl,de
        ex      de,hl

        ld      h,ROWPG                 ; μένει σταθερό σε όλον τον βρόχο
        ; --- ο καυτός βρόχος: ως 8 γείτονες, 1.024 ανά πηγή ---
rtn_nb:
        ld      a,(de)                  ; v
        inc     de
        ld      l,a
        ld      a,(hl)                  ; dist[v]
        inc     a                       ; 255 -> 0
        jr      nz,rtn_skip             ; τον ξέρουμε ήδη
        ld      (hl),c                  ; dist[v] = d
        ld      a,ixl
        cp      RT_UNREACH
        jr      nz,rtn_have
        ld      a,l                     ; γείτονας της πηγής: ο ίδιος ο v
rtn_have:
        set     7,l
        ld      (hl),a                  ; next[v]
        res     7,l                     ; L = v ξανά
        ; ουρά
        push    de
        ld      a,(rt_tail)
        ld      e,a
        set     7,e
        ld      d,NODEPG
        ld      a,l
        ld      (de),a
        ld      a,(rt_tail)
        inc     a
        ld      (rt_tail),a
        pop     de
rtn_skip:
        djnz    rtn_nb
rtn_out:
        pop     bc
        or      a                       ; Cy=0
        ret
rtn_empty:
        pop     bc
        scf
        ret

; ---------------------------------------------------------------------------
; rt_flush — η έτοιμη σειρά στις δύο τράπεζες.
;
; Η γραμμή της πηγής s κάθεται στο &4000 + s*128 και στις δύο.
; ---------------------------------------------------------------------------
rt_flush:
        push    bc
        ld      a,(rt_src)
        ld      h,a
        ld      l,0
        srl     h
        rr      l                       ; HL = s*128
        set     6,h                     ; + &4000
        ld      (rt_dst),hl

        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      hl,RT_DIST
        ld      de,(rt_dst)
        ld      bc,128
        ldir

        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,RT_NEXT
        ld      de,(rt_dst)
        ld      bc,128
        ldir

        ld      bc,GA_PORT + PAGE_B1    ; πίσω στην προεπιλογή
        out     (c),c
        pop     bc
        ret

; ---------------------------------------------------------------------------
; rt_rebuild — όλη η ανοικοδόμηση χωρίς κόψιμο. Για μέτρηση και για δοκιμή.
; ---------------------------------------------------------------------------
rt_rebuild:
        call    rt_begin
rtr_lp:
        ld      b,255
        call    rt_slice
        jr      nc,rtr_lp
        ret

rt_n:       db RT_NODES             ; ανώτατο id + 1 — βλ. rt_begin
rt_src:     db 0
rt_u:       db 0
rt_head:    db 0
rt_tail:    db 0
rt_phase:   db 0
rt_dst:     dw 0
