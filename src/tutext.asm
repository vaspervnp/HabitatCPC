; ---------------------------------------------------------------------------
; tutext.asm — οι γραμμές του tutorial (βήμα 149, src/tutor.asm): ΤΡΙΑΝΤΑΔΥΟ
; χαρακτήρες η καθεμία, με κενά ως το τέλος — σβήνουν ό,τι έγραφε η προηγούμενη
; στη γραμμή του LOOK. Κάθε μία πάει σε μία τρύπα του DIST (src/main.asm), και
; το tuo_go φέρνει μία κάθε φορά στο x_t_look της τράπεζας 7. Τα γράμματα πάνω
; στα κουμπιά είναι τα πλήκτρα τους (src/bar.asm): D θόλοι, S μικρός, M μεσαίος,
; O C G F B N δωμάτια, P ενέργεια, E πόροι, T μεταφορά.
; ---------------------------------------------------------------------------
tut_00:  db "P S: SOLAR PANEL, FIRE TO BUILD "     ; 1 ηλιακός: P η ομάδα ΕΝΕΡΓΕΙΑ, S ο ηλιακός
        assert  $ - tut_00 == 32
tut_01:  db "D S O: OXYGEN DOME, FIRE ON IT  "     ; 2 θόλος οξυγόνου, και FIRE πάνω του: ο εξοπλισμός με το OXYGEN
        assert  $ - tut_01 == 32
tut_02:  db "T A: AN AIRLOCK BY THE DOME     "     ; 3 airlock
        assert  $ - tut_02 == 32
tut_03:  db "E X: AN EXTRACTOR BY WATER      "     ; 4 αντλία
        assert  $ - tut_03 == 32
tut_04:  db "D S C: A CANTEEN, FIT MEALS     "     ; 5 κυλικείο με MEALS
        assert  $ - tut_04 == 32
tut_05:  db "P S: ANOTHER SOLAR PANEL        "     ; 6 δεύτερος ηλιακός (ο χρήστης, βήμα 149)
        assert  $ - tut_05 == 32
tut_06:  db "P C: A COLLECTOR FOR THE NIGHT  "     ; 7 συλλέκτης
        assert  $ - tut_06 == 32
tut_07:  db "E M: A MINE ON AN ORE VEIN      "     ; 8 ορυχείο
        assert  $ - tut_07 == 32
tut_08:  db "D S F: A FACTORY, FIT METAL     "     ; 9 εργοστάσιο με METAL
        assert  $ - tut_08 == 32
tut_09:  db "D M G: A GREENHOUSE, FIT PLANTS "     ; 10 μεσαίο θερμοκήπιο με φυτά
        assert  $ - tut_09 == 32
tut_10:  db "D S B: A LAB, FIT MEAT          "     ; 11 εργαστήριο με MEAT
        assert  $ - tut_10 == 32
tut_11:  db "D S N: A CONTROL ROOM           "     ; 12 έλεγχος
        assert  $ - tut_11 == 32
tut_12:  db "T P: A LANDING PAD              "     ; 13 πίστα
        assert  $ - tut_12 == 32
tut_13:  db "C, FIRE: CALL A COLONIST SHIP   "     ; 14 πλοίο
        assert  $ - tut_13 == 32
tut_14:  db "THE COLONY IS YOURS             "     ; 15 το μήνυμα, ως το επόμενο γεγονός
        assert  $ - tut_14 == 32
tut_15:  db "SPACE=MENU I=INFO FIRE=FIT C=SHI"     ; και η γραμμή που ήταν (το «P» το γράφει το tuo_go)
        assert  $ - tut_15 == 32
