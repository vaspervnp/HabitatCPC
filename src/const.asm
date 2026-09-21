; const.asm — σταθερές μηχανής και χάρτη μνήμης
; Βλ. DESIGN.md §2.1, §4.1, §8.1

; --- οθόνη ---
SCR_BASE    equ #C000       ; σελίδα 3 — περιοχή παιχνιδιού
SCR_W       equ 80          ; bytes ανά γραμμή
SCR_H       equ 200         ; γραμμές συνολικά
PLAY_LINES  equ 160         ; §8.1 — οι πρώτες 160 είναι το κάδρο
HUD_LINES   equ 40

; --- gate array ---
GA_PORT     equ #7F00
RMR_MODE0   equ #8C         ; 100 0 11 00 : mode 0, κάτω ROM off, πάνω ROM off
GA_PEN      equ #00         ; 00pppppp επιλογή pen
GA_BORDER   equ #10
GA_INK      equ #40         ; 01cccccc τιμή χρώματος

; --- διαμορφώσεις RAM για το παράθυρο &4000-&7FFF (§4.1) ---
PAGE_B1     equ #C0         ; βασική τράπεζα 1
PAGE_B4     equ #C4         ; επίπεδο κόσμου
PAGE_B5     equ #C5         ; NEXTHOP
PAGE_B6     equ #C6         ; τεταρτημόρια, φιγούρες, πίνακες οντοτήτων
PAGE_B7     equ #C7         ; εξωτερικές δομές, φυτά, κείμενο, ήχος

; --- προσανατολισμοί τεταρτημορίου (§5 του SPRITES.md) ---
Q_NW        equ 0
Q_NE        equ 1           ; ζεύγη ανάποδα + flip_mode0 σε κάθε byte
Q_SW        equ 2           ; γραμμές ανάποδα
Q_SE        equ 3           ; και τα δύο
