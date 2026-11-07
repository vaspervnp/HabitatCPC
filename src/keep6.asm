; keep6.asm — ο κώδικας της τράπεζας 6 που είναι μέσα στο μπλοκ που σώζεται,
; στην άκρη όσο φορτώνεται ένα σώσιμο (βήματα 187-188, DESIGN §4.2, §11).
;
; Το b6x, #6606-#667F (src/need6.asm), και οι B6T_N ουρές των σελίδων πεδίων
; από το B6T_0 (src/full6.asm, οκτώ από το βήμα 197) είναι μέσα στο μπλοκ που
; σώζεται από το #6600.
; Ενα σώσιμο έχει εκεί τον κώδικα του παιχνιδιού που το έγραψε — ένα του
; βήματος 186, μηδενικά — και ένα φόρτωμα θα τον έγραφε πάνω στον δικό μας. Το
; sv_bodyx (src/demolish.asm) καλεί το svx_swap πριν από το sv_body και μετά:
; την πρώτη φορά ο κώδικας πάει στην ουρά της κεφαλίδας, τη δεύτερη γυρίζει, και
; εκεί μένει ό,τι είχε το σώσιμο, που δεν το διαβάζει κανείς. Το sv_after
; διαβάζει από την κεφαλίδα μόνο τα bytes 7-12. Στην τράπεζα 0, γιατί η 6 πρέπει
; να μπει στο παράθυρο, και ο κώδικας του σωσίματος (src/save.asm) έχει 1 byte
; ως την κεφαλίδα. Γυρίζει με την 1 μέσα, όπως το sv_body· χαλάει AF, BC, DE, HL.

SVX_AT      equ SV_HDR + 16             ; assert στο src/save.asm
SVX_BNC     equ SVX_AT + G_dome_tbl - G_b6x + B6T_HDR * B6T_LEN   ; το ενδιάμεσο (βήμα 197)

svx_swap:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_b6x
        ld      de,SVX_AT
        ld      bc,G_dome_tbl - G_b6x
        call    svs_blk
        ld      hl,B6T_0
        ld      a,B6T_N
svs_tl:
        push    af
        cp      B6T_N - B6T_HDR + 1
        jr      c,svs_nh
        call    svs_68                  ; οι B6T_HDR πρώτες: στην κεφαλίδα
        jr      svs_nx
        ; ΟΙ ΥΠΟΛΟΙΠΕΣ ΣΤΟ NEXTHOP (βήμα 197): η κεφαλίδα δεν τις χωρά, και οι
        ; γραμμές του τις μηδενίζει το sv_after αμέσως μετά. Η 6 και η 5 είναι
        ; και οι δύο στο #4000, γι' αυτό τρεις ανταλλαγές με ένα ενδιάμεσο:
        ; ουρά <-> ενδιάμεσο, γραμμή <-> ενδιάμεσο, ουρά <-> ενδιάμεσο. Η ουρά k
        ; πάει στη γραμμή 2(k - B6T_HDR), στις στήλες 0-67. Αν το φόρτωμα σπάσει
        ; πριν από την 6, η δεύτερη κλήση ξαναδίνει στη γραμμή ό,τι είχε.
svs_nh:
        push    hl                      ; -> η ουρά
        ld      de,SVX_BNC
        call    svs_68                  ; ουρά <-> ενδιάμεσο, στην 6
        pop     hl
        push    hl
        ld      a,h
        add     a,(#40 - (B6T_0 >> 8) - B6T_HDR) & 255
        ld      h,a
        ld      l,0                     ; -> η γραμμή του NEXTHOP
        ld      de,SVX_BNC
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        call    svs_68                  ; γραμμή <-> ενδιάμεσο, στην 5
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        pop     hl
        ld      de,SVX_BNC
        call    svs_68                  ; HL -> η αρχή της επόμενης σελίδας
svs_nx:
        ld      l,B6T_0 & 255           ; ...και η ουρά της
        pop     af
        dec     a
        jr      nz,svs_tl
        ; Η ΜΟΥΣΙΚΗ (βήμα 195): την πρώτη φορά το EC_MUS είναι ίδιο με το mu_off
        ; (το mu_key γράφει και τα δύο), τη δεύτερη είναι του σωσίματος που μόλις
        ; ήρθε. Στο node_occ από το βήμα 197 (ως τότε μετά την τελευταία ουρά).
        ld      a,(EC_MUS)
        ld      (mu_off),a
        jp      dt_end                  ; η 1 (src/dirty.asm)
        assert  (B6T_N - B6T_HDR - 1) * 2 < NODE_CAP && B6T_LEN <= NODE_CAP && (B6T_0 & 255) == N_AGENT
; svs_68 — μία ουρά: B6T_LEN bytes του (HL) με του (DE), και τα δύο μετά.
svs_68:
        ld      bc,B6T_LEN
; svs_blk — BC bytes του (HL) με του (DE), και τα δύο μετά.
svs_blk:
        ld      a,(de)
        ldi
        dec     hl
        ld      (hl),a
        inc     hl
        jp      pe,svs_blk
        ret
