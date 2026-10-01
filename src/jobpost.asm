; ---------------------------------------------------------------------------
; jb_post_build — A = κόμβος. Μία εργασία Build στην πρώτη ελεύθερη θέση· αν
; δεν υπάρχει, καμία.
;
; ΣΕ ΔΙΚΟ ΤΟΥ ΑΡΧΕΙΟ, από το βήμα 38. Το θέλουν δύο: το build.asm για κάθε
; νέο κτίριο, και ο μετεωρίτης που γυρίζει μια χτυπημένη δομή σε εργοτάξιο
; (src/meteor.asm). Το harness της προσομοίωσης (tests/simtest.asm) έχει τον
; μετεωρίτη αλλά όχι το build.asm, της διεπαφής (tests/uitest.asm) το
; ανάποδο — στο jobs.asm ή στο build.asm, ένα από τα δύο δεν θα έβρισκε τη
; ρουτίνα. Το περιλαμβάνουν και τα τρία.
; ---------------------------------------------------------------------------
jb_post_build:
        ld      c,a
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
jpb_lp:
        ld      a,(hl)
        cp      NO_JOB
        jr      z,jpb_got
        ld      de,JOB_REC
        add     hl,de
        djnz    jpb_lp
        ret
jpb_got:
        ld      (hl),J_BUILD
        inc     hl
        ld      (hl),c
        inc     hl
        ld      (hl),255                ; αδιάθετη
        inc     hl
        ld      (hl),5                  ; προτεραιότητα, από το job_prio
        inc     hl
        ld      (hl),0
        ret
