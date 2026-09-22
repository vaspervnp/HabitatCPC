; graphtest.asm — η δρομολόγηση: ταυτότητα με την αναφορά, και το κόστος της.
;
; Ο γράφος έρχεται από τον host γραμμένος κατευθείαν στην τράπεζα 2 (πάντα
; ορατή, άρα write_ram). Εδώ τρέχει μόνο η BFS.
;
; Τρεις είσοδοι:
;   start      πλήρης ανοικοδόμηση χωρίς κόψιμο   -> done_flag
;   sliced     η ΙΔΙΑ δουλειά με μικρό B ανά κλήση -> done_flag, slice_count
;   dump_next  η τράπεζα 5 στο &C000 για να διαβαστεί -> dump_flag
;
; Το sliced υπάρχει επειδή η διακοπτόμενη μορφή είναι αυτή που θα τρέξει
; πραγματικά. Αν δίνει άλλο αποτέλεσμα από το start, η μηχανή κατάστασης έχει
; λάθος — και αυτό δεν φαίνεται με επιθεώρηση.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/layout.asm"

start:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    rt_rebuild
        ld      a,#5A
        ld      (done_flag),a
stop1:  jr      stop1

; --- η ίδια δουλειά, κομμένη σε φέτες των (slice_b) κόμβων ---
sliced:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      hl,0
        ld      (slice_count),hl
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    rt_begin
sl_lp:
        ld      a,(slice_b)
        ld      b,a
        call    rt_slice
        push    af
        ld      hl,(slice_count)
        inc     hl
        ld      (slice_count),hl
        pop     af
        jr      nc,sl_lp
        ld      a,#5A
        ld      (done_flag),a
stop2:  jr      stop2

; --- η τράπεζα 5 στη σελίδα οθόνης, ώστε να τη δει το read_ram ---
dump_next:
        di
        ld      sp,#0100
        xor     a
        ld      (dump_flag),a
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,#4000
        ld      de,#C000
        ld      bc,#4000
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#A5
        ld      (dump_flag),a
stop3:  jr      stop3

        include "../src/graph.asm"

done_flag:   db 0
dump_flag:   db 0
slice_b:     db 8
slice_count: dw 0
