; visit0.asm — οι επισκέπτες, ό,τι δεν θέλει την τράπεζα 6 (βήμα 136)
;
; Το src/visit.asm ζει στο b6code, που δεν είχε χώρο για όλα: εδώ, στην
; τράπεζα 0, το φαγητό, η πληρωμή, η εύνοια και το «πού είναι το κοντινότερο
; τέτοιο δωμάτιο». Τα καλεί μόνο το vi_at, μέσα στον τροχό, με την 6 στο
; παράθυρο — τα EC_COINS και EC_GOOD είναι εκεί (EC_X), και το nd_droom είναι
; στο b6code.

; via_go — E = είδος δωματίου, D = ο κόμβος του, L = ο επισκέπτης. Z: είναι
; σε τέτοιο. Αλλιώς πάει στο κοντινότερο (nd_nearest, από το DIST): NZ και NC,
; ή CY αν δεν φτάνει σε κανένα. Κρατά DE, L.
via_go:
        ld      a,d
        cp      MAX_DOME
        jr      nc,vig_f                ; δομή: η πίστα ή ένα airlock
        push    de
        push    hl
        call    nd_droom                ; src/needs.asm
        pop     hl
        pop     de
        cp      e
        ret     z
vig_f:
        push    de
        push    hl
        ld      a,e
        call    nd_nearest              ; src/b6out.asm: A = θόλος, ή 255
        pop     hl
        pop     de
        add     a,1
        ret     c                       ; κανένας
        dec     a
        ld      h,AG_PG + 2
        ld      (hl),a                  ; ο προορισμός
        or      h                       ; NZ, NC
        ret

; ---------------------------------------------------------------------------
; vi_eat — στο κυλικείο: ένα τρόφιμο και ένα νερό, η εύνοια +GOOD_UP ως το
; GOOD_MAX, και COIN_MEAL. NC. CY: λείπει το ένα, και η εύνοια -GOOD_DOWN
; (vi_sad). Ως το βήμα 135 το ίδιο, για όλους μαζί στην προσγείωση.
; ---------------------------------------------------------------------------
vi_eat:
        ld      hl,(EC_STOCK + 2*S_FOOD)
        ld      a,h
        or      l
        jr      z,vi_sad
        ld      de,(EC_STOCK + 2*S_WATER)
        ld      a,d
        or      e
        jr      z,vi_sad
        dec     hl
        ld      (EC_STOCK + 2*S_FOOD),hl
        dec     de
        ld      (EC_STOCK + 2*S_WATER),de
        ld      a,(EC_GOOD)
        add     a,GOOD_UP
        cp      GOOD_MAX + 1
        jr      c,vie_g
        ld      a,GOOD_MAX
vie_g:  ld      (EC_GOOD),a
        ld      a,COIN_MEAL
; vi_pay — A νομίσματα, ως το COIN_MAX. NC.
vi_pay:
        ld      hl,(EC_COINS)
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      (EC_COINS),hl
        ld      de,-(COIN_MAX + 1)
        add     hl,de                   ; CY: πάνω από το COIN_MAX
        ret     nc
        ld      hl,COIN_MAX
        ld      (EC_COINS),hl
        or      a
        ret
; vi_sad — η εύνοια -GOOD_DOWN, ως το 0. CY.
vi_sad:
        ld      a,(EC_GOOD)
        sub     GOOD_DOWN
        jr      nc,vis_st
        xor     a
vis_st: ld      (EC_GOOD),a
        scf
        ret

