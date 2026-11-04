; info.asm — «τι έχει από κάτω»: το I στο LOOK (DESIGN §9.1, βήμα 79).
;
; Οι σειρές 3-4 του HUD λένε τι είναι χτισμένο στο tile του κέρσορα και τι
; έδαφος έχει. Είναι μια κατάσταση του ui (UI_INFO) που τρέχει τον κώδικα του
; LOOK: μένει ώσπου να κουνηθεί ο κέρσορας ή να πατηθεί το ESC, και ένα I
; ακόμη την ξαναδιαβάζει. Μόνο στο πλήρες παιχνίδι: το κτίριο το βρίσκει το
; mt_scan του src/meteor.asm, η ίδια ερώτηση που κάνει μια κρούση.
;
; Στην τράπεζα 2, όπως ό,τι τρέχει μόνο όταν το ζητήσει ο παίκτης.
;
;   σειρά 3   DOME S   OXYGEN     ACTIVE HP 100%     (θόλος: μέγεθος, δωμάτιο)
;             SOLAR               SITE   HP  40%     (δομή)
;             CORRIDOR                               (κατοχή, χωρίς κτίριο)
;             NOTHING BUILT
;   σειρά 4   MOUNTAIN   ORE VEIN                    (το έδαφος του tile)

; ---------------------------------------------------------------------------
; mt_cursor — το κτίριο κάτω από τον κέρσορα, όπως το βρίσκει μια κρούση
; (mt_scan). CY: A = ο κόμβος, HL -> η εγγραφή, E = το μήκος της (DOME_REC ή
; STRUCT_REC). Πάντα B = x - MT_REACH, C = y του tile. Με την τράπεζα 6 μέσα.
; Για το in_panel και την κατεδάφιση (βήμα 101, src/demolish.asm).
; ---------------------------------------------------------------------------
mt_cursor:
        call    ob_b6
        call    ui_curt                 ; L = x, H = y
        ld      a,l
        sub     MT_REACH                ; το mt_scan θέλει x - MT_REACH (βήμα 87)
        ld      b,a
        ld      c,h
        ld      hl,G_dome_tbl
        ld      de,MAX_DOME * 256 + DOME_REC
        call    mt_scan
        ld      a,MAX_DOME
        jr      c,mtc_hit
        ld      de,MAX_STRUCT * 256 + STRUCT_REC
        call    mt_scan                 ; το HL είναι ήδη στο G_struct_tbl
        ld      a,MAX_NODE
        ret     nc
mtc_hit:
        sub     d                       ; ο κόμβος, όπως στο mt_hit
        scf
        ret
        assert  DOME_REC & 16 && !(STRUCT_REC & 16)

; ---------------------------------------------------------------------------
; in_panel — από το ui_panel, με το HUD στη σειρά 3, στήλη 0. Τελειώνει στο
; uip_spd, την ταχύτητα στις στήλες 35-39 της σειράς 3. Εδώ ό,τι διαβάζεται·
; το τύπωμα στην 7 από το βήμα 180 (in_p7, src/panel7.asm).
; ---------------------------------------------------------------------------
in_panel:
        ; --- ό,τι χρειάζεται από τις τράπεζες 6 και 4, πριν τυπωθεί τίποτα:
        ; ο γλύφος σελιδοποιεί την 7 ---
        call    mt_cursor
        ld      a,0                     ; τίποτα· οι σημαίες μένουν
        jr      nc,inp_rec
        inc     a                       ; θόλος
        bit     4,e                     ; DOME_REC 24, STRUCT_REC 8
        jr      nz,inp_rec
        inc     a                       ; δομή
inp_rec:
        ld      (in_t),a
        ld      a,b
        add     a,MT_REACH
        ld      b,a
        push    bc                      ; το tile, για το έδαφος
        inc     hl
        inc     hl                      ; D_SIZE / ST_KIND
        ld      de,in_k
        ld      bc,6                    ; μέγεθος/είδος, δωμάτιο/μέγεθος, κατάσταση,
        ldir                            ; ακεραιότητα, και των κιβωτίων ST_OPS, ST_OWED
        assert  D_ROOM == D_SIZE + 1 && D_STATE == D_SIZE + 2 && D_INTEG == D_SIZE + 3
        assert  ST_SIZE == ST_KIND + 1 && ST_STATE == ST_KIND + 2 && ST_INTEG == ST_KIND + 3
        assert  D_SIZE == ST_KIND
        pop     bc
        ld      a,#FF                   ; όλο το byte: το tl_occ (src/tiles.asm)
        call    tl_occ                  ; με την 4 μέσα, και μετά πάλι η 1
        ld      (in_w),a
        ; ΤΟ ΤΥΠΩΜΑ ΣΤΗΝ ΤΡΑΠΕΖΑ 7 από το βήμα 180 (in_p7, src/panel7.asm): ο
        ; γλύφος γυρίζει εκεί (hud_pg), και τα κείμενα φαίνονται χωρίς hud_text7.
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page
        jp      in_p7

in_t:       db 0                ; 0 τίποτα, 1 θόλος, 2 δομή
in_k:       db 0                ; μέγεθος θόλου / είδος δομής
in_r:       db 0                ; δωμάτιο θόλου / μέγεθος δομής
in_st:      db 0                ; κατάσταση
in_hp:      db 0                ; ακεραιότητα
in_ops:     db 0                ; τα κιβώτια (βήμα 181): η λήξη στα κάτω έξι bits,
in_ow:      db 0                ; και ο σωρός
in_w:       db 0                ; το byte του κόσμου
        assert  in_r == in_k + 1 && in_st == in_k + 2 && in_hp == in_k + 3
        assert  in_ops == in_k + ST_OPS - ST_KIND && in_ow == in_k + ST_OWED - ST_KIND
        assert  rm_names == rm_list + 10
