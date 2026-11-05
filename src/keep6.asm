; keep6.asm — ο κώδικας του b6x στην άκρη όσο φορτώνεται ένα σώσιμο (βήμα 187,
; DESIGN §4.2, §11).
;
; Το b6x, #6606-#667F της τράπεζας 6 (src/need6.asm), είναι μέσα στο μπλοκ που
; σώζεται από το #6600. Ενα σώσιμο έχει εκεί τον κώδικα του παιχνιδιού που το
; έγραψε — ένα του βήματος 186, μηδενικά — και ένα φόρτωμα θα τον έγραφε πάνω
; στον δικό μας. Το sv_bodyx (src/demolish.asm) τον βγάζει πριν από το sv_body
; και τον ξαναβάζει μετά, στην ουρά της κεφαλίδας: το sv_after διαβάζει από
; εκεί μόνο τα bytes 7-12. Στην τράπεζα 0, γιατί η 6 πρέπει να μπει στο
; παράθυρο, και ο κώδικας του σωσίματος (src/save.asm) έχει 1 byte ως την
; κεφαλίδα. Γυρίζουν με την 1 μέσα, όπως το sv_body· χαλάνε BC, DE, HL.

SVX_AT      equ SV_HDR + 16             ; assert στο src/save.asm

svx_out:
        ld      hl,G_b6x
        ld      de,SVX_AT
        jr      svx_go
svx_in:
        ld      hl,SVX_AT
        ld      de,G_b6x
svx_go:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      bc,G_dome_tbl - G_b6x
        ldir
        jp      dt_end                  ; η 1 (src/dirty.asm): A και F μένουν
