; keep6.asm — ο κώδικας της τράπεζας 6 που είναι μέσα στο μπλοκ που σώζεται,
; στην άκρη όσο φορτώνεται ένα σώσιμο (βήματα 187-188, DESIGN §4.2, §11).
;
; Το b6x, #6606-#667F (src/need6.asm), και οι B6T_N ουρές των σελίδων πεδίων
; από το B6T_0 (src/full6.asm) είναι μέσα στο μπλοκ που σώζεται από το #6600.
; Ενα σώσιμο έχει εκεί τον κώδικα του παιχνιδιού που το έγραψε — ένα του
; βήματος 186, μηδενικά — και ένα φόρτωμα θα τον έγραφε πάνω στον δικό μας. Το
; sv_bodyx (src/demolish.asm) καλεί το svx_swap πριν από το sv_body και μετά:
; την πρώτη φορά ο κώδικας πάει στην ουρά της κεφαλίδας, τη δεύτερη γυρίζει, και
; εκεί μένει ό,τι είχε το σώσιμο, που δεν το διαβάζει κανείς. Το sv_after
; διαβάζει από την κεφαλίδα μόνο τα bytes 7-12. Στην τράπεζα 0, γιατί η 6 πρέπει
; να μπει στο παράθυρο, και ο κώδικας του σωσίματος (src/save.asm) έχει 1 byte
; ως την κεφαλίδα. Γυρίζει με την 1 μέσα, όπως το sv_body· χαλάει AF, BC, DE, HL.

SVX_AT      equ SV_HDR + 16             ; assert στο src/save.asm

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
        ld      bc,B6T_LEN
        call    svs_blk                 ; HL -> η αρχή της επόμενης σελίδας
        ld      l,B6T_0 & 255           ; ...και η ουρά της
        pop     af
        dec     a
        jr      nz,svs_tl
        jp      dt_end                  ; η 1 (src/dirty.asm)
; svs_blk — BC bytes του (HL) με του (DE), και τα δύο μετά.
svs_blk:
        ld      a,(de)
        ldi
        dec     hl
        ld      (hl),a
        inc     hl
        jp      pe,svs_blk
        ret
