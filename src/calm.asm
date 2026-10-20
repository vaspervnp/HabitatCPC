; calm.asm — η ηρεμία ανάμεσα στις καταστροφές (βήμα 121): οι δύο
; χρονοσφραγίδες και η ερώτηση «μπορεί να αρχίσει καταστροφή τώρα;».
;
; ΣΤΗ ΣΕΛΙΔΑ 2 ΑΠΟ ΤΟ ΒΗΜΑ 158, από το τέλος του b6code (src/meteor.asm): ο
; κώδικας δεν άλλαξε byte, και η σελίδα 2 φαίνεται πάντα, οπότε δουλεύει με
; την τράπεζα 6 μέσα όπως πριν. Το b6code κέρδισε 98 bytes.

; ev_may — μπορεί να αρχίσει καταστροφή τώρα (βήμα 121); CY = όχι: λιγότεροι
; από DIS_POP ζωντανοί, ή λιγότερο από FAULT_GAP περιστροφές από το τελευταίο
; γεγονός, ή λιγότερο από δύο sol από την τελευταία καταστροφή. Από τη θύελλα,
; την έκλαμψη (src/econ.asm) και το mt_tick, μόνο αφού έπεσε η ζαριά τους.
; Τα EC_LDIS και EC_LEV είναι στην τράπεζα 6, και όποιος καλεί την έχει μέσα:
; όλη η θέση 15 (src/econ.asm), και το mt_tick στο b6code. Ως το βήμα 157 στο
; b6code, στο τέλος του src/meteor.asm, για να μη βάλουν 96 bytes στην τράπεζα
; 0· από το 158 στη σελίδα 2, που φαίνεται πάντα, για να έχει χώρο το b6code.
; Χαλάει A, BC, DE, HL.
ev_may:
        ld      a,(EC_ALIVE)
        cp      DIS_POP
        ret     c
        ld      de,EC_LEV
        call    ev_since
        ld      bc,FAULT_GAP * 16
        or      a
        sbc     hl,bc
        ret     c
        ld      de,EC_LDIS
        call    ev_since
        ld      bc,(EC_SOLLEN)
        or      a
        sbc     hl,bc
        ret     c
        sbc     hl,bc                   ; δύο sol: το CY είναι ήδη 0
        ret

; ev_since — DE -> [sol, frame] ενός γεγονότος: HL = frames από τότε. #FFFF από
; τρία sol και πάνω (το sol είναι ένα byte: μετά από 256 sol ξαναμοιάζει
; πρόσφατο, για το πολύ δύο sol), και για το [0, 0] — «ποτέ»: ένα γεγονός στο
; sol 0 έχει frame 16 τουλάχιστον, γιατί η ζαριά βλέπει το ρολόι αφού
; προχωρήσει. Χαλάει A, BC, DE, HL.
ev_since:
        ex      de,hl
        ld      e,(hl)                  ; το sol τότε
        inc     hl
        ld      c,(hl)
        inc     hl
        ld      b,(hl)                  ; BC = το frame τότε
        ld      a,e
        or      c
        or      b
        jr      z,evs_far
        ld      a,(EC_SOL)
        sub     e
        cp      3
        jr      nc,evs_far
        ld      d,a                     ; 0-2 sol πριν
        ld      hl,(EC_FRAME)
        or      a
        sbc     hl,bc
        ld      bc,(EC_SOLLEN)
        inc     d
evs_lp:
        dec     d
        ret     z
        add     hl,bc
        jr      evs_lp
evs_far:
        ld      hl,#FFFF
        ret

; ev_mark — μια καταστροφή άρχισε τώρα: η χρονοσφραγίδα της, και του τελευταίου
; γεγονότος. ev_mark1 — μόνο του τελευταίου γεγονότος (η βλάβη). Χαλάει A, DE, HL.
ev_mark:
        ld      hl,EC_LDIS
        call    evm_put
ev_mark1:
        ld      hl,EC_LEV
evm_put:
        ld      a,(EC_SOL)
        ld      (hl),a
        inc     hl
        ld      de,(EC_FRAME)
        ld      (hl),e
        inc     hl
        ld      (hl),d
        ret
