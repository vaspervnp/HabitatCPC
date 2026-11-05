; map.asm — η είσοδος του χάρτη (βήμα 186, src/map_ov.asm). ΣΤΗ ΔΕΣΜΕΥΣΗ
; b1code, μετά το bar_want: η τράπεζα 0 έχει 7 bytes και η 2 δεκατρία. Τρέχει
; με την 1 στο παράθυρο, όπως όλο το UI· κάθε κλήση από εδώ γυρίζει με αυτήν
; (ov_cp16, το mpo_show με το ov_b1 του, το hp_back).
;
; ΠΩΣ ΦΤΑΝΕΙ ΕΔΩ: το TAB είναι μια δεύτερη θέση του κουμπιού BT_GOAL στη μπάρα
; των ομάδων (bk_more, src/goals.asm), όπως το G, και το ms_key ρωτά ποιο από
; τα δύο πατήθηκε.
mp_open:
        call    ui_hide                 ; το GH_BUF αδειάζει: εκεί τρέχει ο χάρτης
        ld      hl,OV5_HOLE
        ld      de,GH_BUF
        ld      a,OV5_ROWS
        ld      c,PAGE_B5
        call    ov_cp16                 ; src/demolish.asm
        call    mpo_show
        call    hp_back                 ; src/help.asm: η οθόνη από την αρχή
        jp      ui_show
        assert  mpo_show == GH_BUF
