; object.asm — το πέρασμα αντικειμένων (DESIGN §8.4, SPRITES.md §10).
;
; Η σειρά είναι του SPRITES.md §10 με τη διόρθωση του §8.4: οι διάδρομοι
; μπαίνουν ΑΝΑΜΕΣΑ στα κελύφη και στις πόρτες, γιατί η πόρτα ανοίγει ΠΑΝΩ στον
; δακτύλιο και πρέπει να μείνει από πάνω.
;
;       1  δακτύλιοι + θόλοι          μάσκα, από το ένα αποθηκευμένο nw
;       2  διάδρομοι                  μάσκα
;       3  πόρτες, εικονίδιο, μηχανές ή φυτά, φιγούρες
;       4  εξωτερικές δομές, ταξινομημένες κατά cy
;
; ΤΟ CLIP ΕΙΝΑΙ Ο ΜΗΧΑΝΙΣΜΟΣ ΤΟΥ ΣΚΡΟΛΑΡΙΣΜΑΤΟΣ. Κάθε blit κόβεται σε ένα
; ορθογώνιο. Με ολόκληρο το κάδρο είναι η πρώτη σχεδίαση· με μία στήλη είναι η
; στήλη που μόλις μπήκε στο κάδρο, και ένας μεγάλος θόλος κοστίζει το ένα
; όγδοο του εαυτού του αντί για ολόκληρο. Ενας μηχανισμός, δύο δουλειές.
;
; ΣΕΛΙΔΟΠΟΙΗΣΗ. Οι πίνακες (dome_tbl, struct_tbl, corr_tbl, agent_fields) είναι
; στην ΤΡΑΠΕΖΑ 6 μαζί με τα τεταρτημόρια και τις φιγούρες· τα εικονίδια, οι
; μηχανές, οι διάδρομοι και οι πόρτες στην 2 (πάντα ορατή)· τα ΦΥΤΑ και οι
; ΕΞΩΤΕΡΙΚΕΣ ΔΟΜΕΣ στην 7. Οπου χρειάζεται και πίνακας και τράπεζα 7, η εγγραφή
; ΑΝΤΙΓΡΑΦΕΤΑΙ πρώτη σε RAM της τράπεζας 0 — το ίδιο μάθημα με τον πάγκο της
; BFS, τρίτη φορά.

AG_FLAGS    equ G_agent_fields          ; +0 flags, +128 role
AG_NODE     equ G_agent_fields + 256    ; +0 node,  +128 slot
OB_ALIVE    equ 1                       ; F_ALIVE του entity.asm

; ---------------------------------------------------------------------------
; ob_blit — ΕΝΑ sprite, κομμένο στο παράθυρο clip, με προαιρετικό καθρέφτισμα.
;
; Παράμετροι στο μπλοκ ob_* παρακάτω. Το ob_fl κουβαλά τον προσανατολισμό στα
; bits 0-1 (ίδια κωδικοποίηση με το blit_quad) και το «αδιαφανές» στο bit 2.
;
; Το καθρεφτισμένο sprite γυρίζει ΟΛΟΚΛΗΡΗ τη γραμμή στο flipbuf και μετά
; κόβεται μέσα στο buffer: το clip από αριστερά αντιστοιχεί σε ζεύγη από το
; ΤΕΛΟΣ της πηγής, και κανένας δείκτης δεν το εκφράζει αυτό πιο απλά.
; ---------------------------------------------------------------------------
ob_blit:
        ; --- κάθετο clip ---
        ld      hl,(ob_y)
        ld      (cl_pos),hl
        ld      a,(ob_h)
        ld      (cl_len),a
        ld      hl,(clip_y0)            ; y0 χαμηλό, y1 ψηλό — ένα ld
        ld      (cl_lo),hl
        call    ob_clip
        or      a
        ret     z
        ld      a,(cl_skip)
        ld      (ob_st),a
        ld      a,(cl_n)
        ld      (ob_nl),a
        ld      a,(cl_start)
        ld      (ob_y0),a
        ; --- οριζόντιο clip ---
        ld      hl,(ob_x)
        ld      (cl_pos),hl
        ld      a,(ob_w)
        ld      (cl_len),a
        ld      hl,(clip_x0)
        ld      (cl_lo),hl
        call    ob_clip
        or      a
        ret     z
        ld      a,(cl_skip)
        ld      (ob_sl),a
        ld      a,(cl_n)
        ld      (ob_nb),a
        ld      a,(cl_start)
        ld      (ob_x0),a

        ; --- βήμα πηγής ανά γραμμή: W αδιαφανές, 2W με μάσκα ---
        ld      a,(ob_w)
        ld      c,a
        ld      a,(ob_fl)
        and     4
        jr      nz,ob_stride
        sla     c
ob_stride:
        ld      a,c
        ld      (ob_str),a

        ; --- πρώτη γραμμή πηγής: από πάνω, ή από κάτω αν καθρεφτίζεται ---
        ld      a,(ob_fl)
        and     2
        ld      a,(ob_st)
        jr      z,ob_fromtop
        ld      b,a
        ld      a,(ob_h)
        dec     a
        sub     b
ob_fromtop:
        ld      c,a
        ld      a,(ob_str)
        call    ob_mul                  ; HL = γραμμή * βήμα
        ld      de,(ob_src)
        add     hl,de
        ld      (ob_ln),hl

        ; --- μετατόπιση μέσα στη γραμμή, για το clip από αριστερά ---
        ld      a,(ob_sl)
        ld      c,a
        ld      a,(ob_fl)
        and     4
        jr      nz,ob_skip1
        sla     c
ob_skip1:
        ld      b,0
        ld      (ob_sk),bc

        ld      a,(ob_x0)
        ld      c,a
        ld      a,(ob_y0)
        call    scr_addr

ob_line:
        push    de
        ld      hl,(ob_ln)
        ld      a,(ob_fl)
        and     1
        jr      z,ob_direct
        ld      a,(ob_w)
        ld      (bq_w),a
        call    flip_line               ; -> flipbuf, το HL μένει
        ld      hl,flipbuf
ob_direct:
        ld      bc,(ob_sk)
        add     hl,bc
        ld      a,(ob_nb)
        ld      b,a
        ld      a,(ob_fl)
        and     4
        jr      nz,ob_opaque
        call    blt_mask_line
        jr      ob_next
ob_opaque:
        call    blt_op_line
ob_next:
        pop     de
        call    scr_nextline
        ld      hl,(ob_ln)
        ld      a,(ob_str)
        ld      c,a
        ld      b,0
        ld      a,(ob_fl)
        and     2
        jr      z,ob_down
        or      a
        sbc     hl,bc
        jr      ob_store
ob_down:
        add     hl,bc
ob_store:
        ld      (ob_ln),hl
        ld      a,(ob_nl)
        dec     a
        ld      (ob_nl),a
        jr      nz,ob_line
        ret

; ---------------------------------------------------------------------------
; ob_clip — ένας άξονας. Δίνει πόσο κόβεται από την αρχή, πόσο μένει, και πού
; αρχίζει στην οθόνη.
; In :  (cl_pos) 16-bit προσημασμένο, (cl_len), (cl_lo), (cl_hi)
; Out:  A = 0 -> εκτός· αλλιώς (cl_skip), (cl_n), (cl_start)
; ---------------------------------------------------------------------------
ob_clip:
        ld      hl,(cl_pos)
        ld      a,(cl_lo)
        ld      e,a
        ld      d,0
        ex      de,hl                   ; HL = lo, DE = pos
        or      a
        sbc     hl,de                   ; lo - pos
        jp      m,oc_after
        ld      a,h
        or      a
        jr      nz,oc_cull              ; κόβεται πάνω από 255 -> έξω
        ld      a,l
        ld      (cl_skip),a
        ld      b,a
        ld      a,(cl_len)
        sub     b
        jr      c,oc_cull
        jr      z,oc_cull
        ld      c,a
        ld      a,(cl_lo)
        ld      (cl_start),a
        jr      oc_tail
oc_after:
        xor     a
        ld      (cl_skip),a
        ld      a,d
        or      a
        jr      nz,oc_cull              ; δεξιά/κάτω από την οθόνη
        ld      a,e
        ld      (cl_start),a
        ld      a,(cl_len)
        ld      c,a
oc_tail:
        ld      a,(cl_start)
        ld      b,a
        ld      a,(cl_hi)
        sub     b
        jr      c,oc_cull
        jr      z,oc_cull
        cp      c
        jr      c,oc_have
        ld      a,c
oc_have:
        ld      (cl_n),a
        ld      a,1
        ret
oc_cull:
        xor     a
        ret

; ---------------------------------------------------------------------------
; ob_mul — HL = A * C, χωρίς πίνακα. Καλείται μία φορά ανά sprite.
; ---------------------------------------------------------------------------
ob_mul:
        ld      hl,0
        ld      d,0
        ld      e,c
        ld      b,8
obm_lp:
        add     hl,hl
        rlca
        jr      nc,obm_no
        add     hl,de
obm_no:
        djnz    obm_lp
        ret

; ---------------------------------------------------------------------------
; ob_sext — A (προσημασμένο byte) -> HL.
; ---------------------------------------------------------------------------
ob_sext:
        ld      l,a
        rla
        sbc     a,a
        ld      h,a
        ret

; ob_sx / ob_sy — κέντρο αντικειμένου σε μισά tiles -> οθόνη (§3.4).
;       x = 2*hx - 4*cam_tx        y = 8*hy - 16*cam_ty
ob_sx:
        call    ob_sext
        add     hl,hl
        push    hl
        ld      a,(cam_tx)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret
ob_sy:
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        push    hl
        ld      a,(cam_ty)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret

; ---------------------------------------------------------------------------
; ob_getdome — A = id θόλου· αντιγράφει τα 24 bytes στη RAM της τράπεζας 0 και
; υπολογίζει το πλαίσιο. Η αντιγραφή δεν είναι σπατάλη: χωρίς αυτήν δεν
; μπορούμε να σελιδοποιήσουμε την 7 για τα φυτά.
; Απαιτεί: τράπεζα 6.
; ---------------------------------------------------------------------------
ob_getdome:
        ld      (d_id),a
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l                     ; 8*id
        add     hl,hl                   ; 16*id
        add     hl,de                   ; 24*id
        ld      de,G_dome_tbl
        add     hl,de
        ld      de,d_rec
        ld      bc,DOME_REC
        ldir
        ; fall through

; ob_frame — πλαίσιο του θόλου από το d_rec: (d_fx, d_fy) και ο πίνακας d_geo.
ob_frame:
        ld      a,(d_rec+D_SIZE)
        ld      l,a
        ld      h,0
        add     hl,hl
        ld      d,h
        ld      e,l                     ; 2*size
        add     hl,hl
        add     hl,hl                   ; 8*size
        add     hl,de                   ; 10*size — η εγγραφή είναι ΔΕΚΑ bytes
        ld      de,dome_geo
        add     hl,de
        ld      (d_geo),hl
        ld      a,(d_rec+D_CX)
        call    ob_sx
        ld      de,(d_geo)
        ld      a,(de)                  ; QW
        ld      (d_qw),a
        ld      c,a
        ld      b,0
        or      a
        sbc     hl,bc
        ld      (d_fx),hl
        ld      a,(d_rec+D_CY)
        call    ob_sy
        ld      de,(d_geo)
        inc     de
        ld      a,(de)                  ; QH
        ld      (d_qh),a
        ld      c,a
        ld      b,0
        or      a
        sbc     hl,bc
        ld      (d_fy),hl
        ret

; ---------------------------------------------------------------------------
; ob_shell — βήματα 1-2: δακτύλιος και θόλος, τέσσερα τεταρτημόρια το καθένα.
; In: A = id θόλου. Απαιτεί τράπεζα 6.
; ---------------------------------------------------------------------------
ob_shell:
        call    ob_getdome
        ld      a,(d_rec+D_STATE)
        or      a
        ret     z
        ld      hl,(d_geo)
        inc     hl
        inc     hl                      ; -> dome_nw
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        push    de                      ; ο θόλος περιμένει
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        call    ob_quads                ; πρώτα ο δακτύλιος
        pop     de
        ; fall through — μετά ο θόλος, στο ίδιο πλαίσιο

; ob_quads — DE = αρχή του nw· τέσσερα τεταρτημόρια στο πλαίσιο (d_fx,d_fy).
ob_quads:
        ld      (ob_src),de
        xor     a
oq_loop:
        ld      (oq_cur),a
        ld      (ob_fl),a               ; bits 0-1 = προσανατολισμός, bit2 = 0
        ld      hl,(d_fx)
        and     1
        jr      z,oq_nox
        ld      a,(d_qw)
        ld      c,a
        ld      b,0
        add     hl,bc
oq_nox:
        ld      (ob_x),hl
        ld      hl,(d_fy)
        ld      a,(oq_cur)
        and     2
        jr      z,oq_noy
        ld      a,(d_qh)
        ld      c,a
        ld      b,0
        add     hl,bc
oq_noy:
        ld      (ob_y),hl
        ld      a,(d_qw)
        ld      (ob_w),a
        ld      a,(d_qh)
        ld      (ob_h),a
        push    hl
        call    ob_blit
        pop     hl
        ld      a,(oq_cur)
        inc     a
        cp      4
        jr      nz,oq_loop
        ret

; ---------------------------------------------------------------------------
; ob_fittings — βήματα 3-6 ενός θόλου: πόρτες, εικονίδιο, μηχανές ή φυτά,
; φιγούρες. In: A = id θόλου. Απαιτεί τράπεζα 6 στην είσοδο, την αφήνει ως έχει.
; ---------------------------------------------------------------------------
ob_fittings:
        call    ob_getdome
        ld      a,(d_rec+D_STATE)
        or      a
        ret     z
        call    ob_conns
        call    ob_icon
        call    ob_machines
        jp      ob_figures

; --- πόρτες: μόνο εκεί που υπάρχει διάδρομος -------------------------------
ob_conns:
        ld      a,(d_id)
        ld      e,a
        ld      d,0
        ld      hl,dome_conn
        add     hl,de
        ld      a,(hl)
        ld      (oc_mask),a
        or      a
        ret     z
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,a                     ; size*16
        ld      (oc_base),a
        xor     a
ocn_lp:
        ld      (oc_dir),a
        ld      b,a
        ld      a,(oc_mask)
        inc     b
        jr      ocn_shend
ocn_sh:
        rrca
ocn_shend:
        djnz    ocn_sh
        and     1
        jr      z,ocn_skip
        ld      a,(oc_dir)
        add     a,a
        ld      c,a
        ld      a,(oc_base)
        add     a,c
        ld      l,a
        ld      h,0
        ld      de,G_conn_points
        add     hl,de
        ld      c,(hl)                  ; px
        inc     hl
        ld      b,(hl)                  ; py
        push    bc
        ld      hl,(d_fx)
        ld      b,0
        add     hl,bc
        ld      (ob_x),hl
        pop     bc
        ld      c,b
        ld      b,0
        ld      hl,(d_fy)
        add     hl,bc
        ld      (ob_y),hl
        ld      a,(oc_dir)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        add     a,a                     ; dir*32
        ld      l,a
        ld      h,0
        ld      de,G_connectors
        add     hl,de
        ld      (ob_src),hl
        ld      a,CONN_W
        ld      (ob_w),a
        ld      a,CONN_H
        ld      (ob_h),a
        xor     a
        ld      (ob_fl),a
        call    ob_blit
ocn_skip:
        ld      a,(oc_dir)
        inc     a
        cp      8
        jp      nz,ocn_lp
        ret

; --- εικονίδιο δωματίου, στο interior_ofs από το ΚΕΝΤΡΟ --------------------
ob_icon:
        ld      a,(d_rec+D_SIZE)
        add     a,a
        ld      l,a
        ld      h,0
        ld      de,G_interior_ofs
        add     hl,de
        ld      a,(hl)                  ; dx προσημασμένο
        inc     hl
        ld      c,(hl)                  ; dy προσημασμένο
        push    bc
        call    ob_sext
        ex      de,hl
        ld      hl,(d_fx)
        add     hl,de
        ld      a,(d_qw)
        ld      c,a
        ld      b,0
        add     hl,bc
        ld      (ob_x),hl
        pop     bc
        ld      a,c
        call    ob_sext
        ex      de,hl
        ld      hl,(d_fy)
        add     hl,de
        ld      a,(d_qh)
        ld      c,a
        ld      b,0
        add     hl,bc
        ld      (ob_y),hl
        ; πηγή: icon_{size}_ptr[room]
        ld      hl,(d_geo)
        ld      de,6
        add     hl,de                   ; -> icon_ptr, icon_w, icon_h
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      a,(hl)
        ld      (ob_w),a
        inc     hl
        ld      a,(hl)
        ld      (ob_h),a
        ld      a,(d_rec+D_ROOM)
        add     a,a
        ld      l,a
        ld      h,0
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (ob_src),hl
        ld      a,4                     ; αδιαφανές
        ld      (ob_fl),a
        jp      ob_blit

; --- μηχανές ή φυτά στις υποδοχές ------------------------------------------
; Το θερμοκήπιο γεμίζει τις ΙΔΙΕΣ υποδοχές με φυτά, και τα φυτά ζουν στην
; τράπεζα 7. Γι' αυτό η εγγραφή αντιγράφηκε: εδώ φεύγει η 6.
ob_machines:
        ld      a,(d_rec+D_SIZE)
        ld      l,a
        ld      h,0
        ld      de,G_machine_count
        add     hl,de
        ld      a,(hl)
        ld      (om_n),a
        ld      a,(d_rec+D_ROOM)
        cp      R_GREENHS
        ld      a,0
        jr      nz,om_notgreen
        inc     a
om_notgreen:
        ld      (om_green),a
        or      a
        jr      z,om_go
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
om_go:
        xor     a
om_lp:
        ld      (om_slot),a
        ld      e,a
        ld      d,0
        ld      hl,d_rec+D_MACH
        add     hl,de
        ld      a,(hl)
        cp      NO_MACH
        jr      z,om_skip
        ld      (om_type),a
        ; θέση μέσα στο πλαίσιο
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,(om_slot)
        add     a,a
        add     a,c
        ld      l,a
        ld      h,0
        ld      de,G_machine_slots
        add     hl,de
        ld      c,(hl)
        inc     hl
        ld      b,(hl)
        ld      a,c
        cp      255
        jr      z,om_skip
        push    bc
        ld      b,0
        ld      hl,(d_fx)
        add     hl,bc
        ld      (ob_x),hl
        pop     bc
        ld      c,b
        ld      b,0
        ld      hl,(d_fy)
        add     hl,bc
        ld      (ob_y),hl
        ; πηγή
        ld      a,(om_type)
        add     a,a
        ld      l,a
        ld      h,0
        ld      a,(om_green)
        or      a
        ld      de,G_mach_ptr
        jr      z,om_tab
        ld      de,G_plant_ptr
om_tab:
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (ob_src),hl
        ld      a,MACH_W
        ld      (ob_w),a
        ld      a,MACH_H
        ld      (ob_h),a
        ld      a,4
        ld      (ob_fl),a
        call    ob_blit
om_skip:
        ld      a,(om_slot)
        inc     a
        ld      hl,om_n
        cp      (hl)
        jp      nz,om_lp
        ld      a,(om_green)
        or      a
        ret     z
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ret

; --- φιγούρες στις θέσεις του δακτυλίου ------------------------------------
; Το dome_fig γέμισε με ΕΝΑ πέρασμα πάνω στους 128 πράκτορες (ob_fig_scan).
; Χωρίς αυτό κάθε θόλος θα σάρωνε και τους 128, δηλαδή 8.192 αναγνώσεις.
ob_figures:
        ld      a,(d_id)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; id*8 — ως 512, θέλει 16 bit
        ld      de,dome_fig
        add     hl,de
        ld      (of_ptr),hl
        ld      a,(d_rec+D_SIZE)
        ld      (of_size),a
        xor     a
of_lp:
        ld      (of_slot),a
        ld      hl,(of_ptr)
        ld      a,(of_slot)
        ld      e,a
        ld      d,0
        add     hl,de
        ld      a,(hl)
        or      a
        jr      z,of_skip
        ld      (of_fig),a
        ld      a,(of_size)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,(of_slot)
        add     a,a
        add     a,c
        ld      l,a
        ld      h,0
        ld      de,G_corr_slots
        add     hl,de
        ld      c,(hl)
        inc     hl
        ld      b,(hl)
        push    bc
        ld      b,0
        ld      hl,(d_fx)
        add     hl,bc
        ld      (ob_x),hl
        pop     bc
        ld      c,b
        ld      b,0
        ld      hl,(d_fy)
        add     hl,bc
        ld      (ob_y),hl
        ; πηγή = corr_slot_gfx + size*SLOT_BANK + slot*SLOT_STRIDE + fig*SLOT_SIZE
        ld      a,(of_size)
        add     a,a
        ld      l,a
        ld      h,0
        ld      de,ob_sbank
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a                     ; size*SLOT_BANK — πίνακας, όχι γινόμενο:
        ld      (of_acc),hl             ; το 1152 δεν χωράει σε 8x8
        ld      a,(of_slot)
        ld      c,SLOT_STRIDE
        call    ob_mul
        ld      de,(of_acc)
        add     hl,de
        ld      (of_acc),hl
        ld      a,(of_fig)
        ld      c,SLOT_SIZE
        call    ob_mul
        ld      de,(of_acc)
        add     hl,de
        ld      de,G_corr_slot_gfx
        add     hl,de
        ld      (ob_src),hl
        ld      a,SLOT_W
        ld      (ob_w),a
        ld      a,SLOT_H
        ld      (ob_h),a
        ld      a,4
        ld      (ob_fl),a
        call    ob_blit
of_skip:
        ld      a,(of_slot)
        inc     a
        cp      CORR_SLOTS
        jp      nz,of_lp
        ret

; ---------------------------------------------------------------------------
; ob_corr — ένας διάδρομος. In: A = id διαδρόμου. Απαιτεί τράπεζα 6.
;
; Ο διάδρομος ζωγραφίζεται ΠΑΝΤΑ από την πλευρά του a: το `dir` είναι η
; κατεύθυνση a -> b, και τα οκτώ sprites είναι τέσσερα, το καθένα με δύο φορές.
; ---------------------------------------------------------------------------
ob_corr:
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl                   ; 4*id
        add     hl,de                   ; 5*id
        ld      de,G_corr_tbl
        add     hl,de
        ld      de,c_rec
        ld      bc,CORR_REC
        ldir
        ld      a,(c_rec+C_CSTATE)
        or      a
        ret     z
        ld      a,(c_rec+C_A)
        call    ob_getdome
        ; --- ο πίνακας της κατεύθυνσης ---
        ld      a,(c_rec+C_DIR)
        and     7
        ld      c,a
        ld      b,0
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,bc                   ; dir*9
        ld      de,corr_dir
        add     hl,de
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      (ob_src),de
        inc     hl
        ld      a,(hl)
        ld      (ob_w),a
        inc     hl
        ld      a,(hl)
        ld      (ob_h),a
        inc     hl
        ld      a,(hl)
        ld      (oc_dx),a
        inc     hl
        ld      a,(hl)
        ld      (oc_dy),a
        inc     hl
        ld      a,(hl)
        ld      (oc_ox),a
        inc     hl
        ld      a,(hl)
        ld      (oc_oy),a
        inc     hl
        ld      a,(hl)
        ld      (oc_diag),a
        or      a
        jr      nz,ob_corr_d
        ; --- αξονικός: από το σημείο σύνδεσης, προς τα έξω ---
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,(c_rec+C_DIR)
        add     a,a
        add     a,c
        ld      l,a
        ld      h,0
        ld      de,G_conn_points
        add     hl,de
        ld      c,(hl)
        ld      b,0
        ld      hl,(d_fx)
        add     hl,bc
        ld      a,(oc_ox)
        call    ob_addsx
        ld      (ob_x),hl
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,(c_rec+C_DIR)
        add     a,a
        add     a,c
        inc     a
        ld      l,a
        ld      h,0
        ld      de,G_conn_points
        add     hl,de
        ld      c,(hl)
        ld      b,0
        ld      hl,(d_fy)
        add     hl,bc
        ld      a,(oc_oy)
        call    ob_addsx
        ld      (ob_y),hl
        jr      ob_corr_run
ob_corr_d:
        ; --- διαγώνιος: πλέγμα DIAG_K από το ΚΕΝΤΡΟ του θόλου ---
        ld      a,(d_rec+D_SIZE)
        ld      l,a
        ld      h,0
        ld      de,diag_k
        add     hl,de
        ld      a,(hl)
        ld      (oc_k),a
        ld      hl,(d_fx)
        ld      a,(d_qw)
        sub     4
        call    ob_addsx
        ld      a,(oc_dx)
        call    ob_addk
        ld      (ob_x),hl
        ld      hl,(d_fy)
        ld      a,(d_qh)
        sub     8
        call    ob_addsx
        ld      a,(oc_dy)
        call    ob_addk
        ld      (ob_y),hl
ob_corr_run:
        ld      a,(c_rec+C_LEN)
        or      a
        ret     z
        ld      (oc_n),a
occ_lp:
        xor     a
        ld      (ob_fl),a
        call    ob_blit
        ld      hl,(ob_x)
        ld      a,(oc_dx)
        call    ob_addsx
        ld      (ob_x),hl
        ld      hl,(ob_y)
        ld      a,(oc_dy)
        call    ob_addsx
        ld      (ob_y),hl
        ld      a,(oc_n)
        dec     a
        ld      (oc_n),a
        jr      nz,occ_lp
        ret

; ob_addsx — HL += A προσημασμένο.
ob_addsx:
        push    hl
        call    ob_sext                 ; HL = sext(A)
        pop     de
        add     hl,de
        ret

; ob_addk — HL += A προσημασμένο, oc_k φορές.
ob_addk:
        ld      b,a
        ld      a,(oc_k)
        or      a
        ret     z
        ld      c,a
oak_lp:
        ld      a,b
        call    ob_addsx
        dec     c
        jr      nz,oak_lp
        ret

; ---------------------------------------------------------------------------
; ob_struct — μία εξωτερική δομή. In: A = id. Απαιτεί τράπεζα 6 στην είσοδο·
; γυρίζει με την 6 μέσα.
; ---------------------------------------------------------------------------
ob_struct:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 8*id
        ld      de,G_struct_tbl
        add     hl,de
        ld      de,s_rec
        ld      bc,STRUCT_REC
        ldir
        ld      a,(s_rec+ST_STATE)
        or      a
        ret     z
        ld      a,(s_rec+ST_KIND)
        add     a,a
        add     a,a
        add     a,a                     ; kind*8
        ld      c,a
        ld      a,(s_rec+ST_SIZE)
        add     a,a
        add     a,c
        ld      l,a
        ld      h,0
        ld      de,G_struct_dims
        add     hl,de
        ld      a,(hl)
        or      a
        ret     z                       ; 0,0 = αυτό το μέγεθος δεν υπάρχει
        ld      (ob_w),a
        inc     hl
        ld      a,(hl)
        ld      (ob_h),a
        ; θέση: κέντρο μείον το μισό πλαίσιο
        ld      a,(s_rec+ST_CX)
        call    ob_sx
        ld      a,(ob_w)
        srl     a
        neg
        call    ob_addsx
        ld      (ob_x),hl
        ld      a,(s_rec+ST_CY)
        call    ob_sy
        ld      a,(ob_h)
        srl     a
        neg
        call    ob_addsx
        ld      (ob_y),hl
        ; πηγή από το struct_ptr, και η πλατφόρμα είναι η μόνη ΑΔΙΑΦΑΝΗ
        ld      a,(s_rec+ST_KIND)
        add     a,a
        add     a,a
        ld      c,a
        ld      a,(s_rec+ST_SIZE)
        add     a,c
        add     a,a
        ld      l,a
        ld      h,0
        ld      de,G_struct_ptr
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      a,h
        or      l
        ret     z
        ld      (ob_src),hl
        ld      a,(s_rec+ST_KIND)
        cp      K_PAD
        ld      a,0
        jr      nz,os_masked
        ld      a,4
os_masked:
        ld      (ob_fl),a
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        call    ob_blit
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; ob_conn_scan — dome_conn[64]: ποιες κατευθύνσεις κάθε θόλου έχουν διάδρομο.
; Ενα πέρασμα στους 96 διαδρόμους αντί για 64 x 96.
; ---------------------------------------------------------------------------
ob_conn_scan:
        ld      hl,dome_conn
        ld      de,dome_conn+1
        ld      bc,63
        ld      (hl),0
        ldir
        ld      hl,G_corr_tbl
        ld      b,MAX_CORR
ocs_lp:
        push    bc
        push    hl
        ld      de,C_CSTATE
        add     hl,de
        ld      a,(hl)
        or      a
        jr      z,ocs_next
        pop     hl
        push    hl
        ld      c,(hl)                  ; a
        inc     hl
        ld      e,(hl)                  ; b
        inc     hl
        ld      a,(hl)                  ; dir
        and     7
        push    de
        call    ocs_set                 ; a, dir
        pop     de
        ld      c,e
        add     a,4                     ; η αντίθετη φορά για τον b
        and     7
        call    ocs_set
ocs_next:
        pop     hl
        ld      de,CORR_REC
        add     hl,de
        pop     bc
        djnz    ocs_lp
        ret

; ocs_set — C = θόλος, A = κατεύθυνση· ανάβει το bit. Γυρίζει A = dir.
ocs_set:
        push    af
        push    hl
        ld      b,a
        ld      a,1
        inc     b
        jr      ocss_e
ocss_lp:
        add     a,a
ocss_e:
        djnz    ocss_lp
        ld      l,c
        ld      h,0
        ld      de,dome_conn
        add     hl,de
        or      (hl)
        ld      (hl),a
        pop     hl
        pop     af
        ret

; ---------------------------------------------------------------------------
; ob_fig_scan — dome_fig[64][8]: ποια φιγούρα σε ποια θέση ποιου θόλου.
; Ενα πέρασμα στους 128 πράκτορες. 0 = κενή, και η κενή ΔΕΝ σχεδιάζεται στην
; πλήρη σχεδίαση — ο δακτύλιος μόλις ζωγραφίστηκε.
; ---------------------------------------------------------------------------
ob_fig_scan:
        ld      hl,dome_fig
        ld      de,dome_fig+1
        ld      bc,64*8-1
        ld      (hl),0
        ldir
        ld      b,128
        ld      c,0
ofs_lp:
        push    bc
        ld      l,c
        ld      h,AG_FLAGS/256
        ld      a,(hl)
        and     OB_ALIVE
        jr      z,ofs_next
        ld      h,AG_NODE/256
        set     7,l
        ld      a,(hl)                  ; slot
        cp      255
        jr      z,ofs_next
        ld      (ofs_slot),a
        res     7,l
        ld      a,(hl)                  ; node
        cp      MAX_DOME
        jr      nc,ofs_next             ; δομή, όχι θόλος
        ld      (ofs_node),a
        ld      h,AG_FLAGS/256
        set     7,l
        ld      a,(hl)                  ; role
        and     7
        ld      l,a
        ld      h,0
        ld      de,role_fig
        add     hl,de
        ld      a,(hl)
        ld      c,a
        ld      a,(ofs_node)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; node*8
        ld      a,(ofs_slot)
        and     7
        ld      e,a
        ld      d,0
        add     hl,de
        ld      de,dome_fig
        add     hl,de
        ld      (hl),c
ofs_next:
        pop     bc
        inc     c
        djnz    ofs_lp
        ret

; ---------------------------------------------------------------------------
; ob_draw_all — όλη η σκηνή, μέσα στο τρέχον clip.
; ---------------------------------------------------------------------------
ob_draw_all:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        call    ob_conn_scan
        call    ob_fig_scan
        ld      b,MAX_DOME
        ld      c,0
oda_sh:
        push    bc
        ld      a,c
        call    ob_shell
        pop     bc
        inc     c
        djnz    oda_sh
        ld      b,MAX_CORR
        ld      c,0
oda_co:
        push    bc
        ld      a,c
        call    ob_corr
        pop     bc
        inc     c
        djnz    oda_co
        ld      b,MAX_DOME
        ld      c,0
oda_fi:
        push    bc
        ld      a,c
        call    ob_fittings
        pop     bc
        inc     c
        djnz    oda_fi
        call    ob_struct_all
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; ob_struct_all — οι δομές ταξινομημένες κατά cy, ώστε οι νότιες να σκεπάζουν
; τις βόρειες (§8.4). Ταξινόμηση με παρεμβολή: 64 στοιχεία, μία φορά ανά
; πλήρη σχεδίαση, και ο πίνακας είναι ήδη σχεδόν ταξινομημένος.
; ---------------------------------------------------------------------------
ob_struct_all:
        ld      hl,G_struct_tbl + ST_STATE
        ld      de,st_ord
        ld      b,MAX_STRUCT
        ld      c,0
        ld      a,0
        ld      (st_n),a
osa_gather:
        ld      a,(hl)
        or      a
        jr      z,osa_gskip
        ld      a,c
        ld      (de),a
        inc     de
        ld      a,(st_n)
        inc     a
        ld      (st_n),a
osa_gskip:
        push    de
        ld      de,STRUCT_REC
        add     hl,de
        pop     de
        inc     c
        djnz    osa_gather
        ld      a,(st_n)
        or      a
        ret     z
        cp      2
        jr      c,osa_draw
        ; --- ταξινόμηση με παρεμβολή πάνω στο cy ---
        ld      a,(st_n)
        dec     a
        ld      b,a
        ld      c,1
osa_out:
        push    bc
        ld      a,c
        call    osa_key                 ; A = cy+128 του st_ord[c], E = id
        ld      d,a
        ld      a,c
        ld      (osa_j),a
osa_in:
        ld      a,(osa_j)
        or      a
        jr      z,osa_place
        dec     a
        push    de
        call    osa_key
        pop     de
        cp      d
        jr      c,osa_place
        jr      z,osa_place
        ; μετακίνησε ένα δεξιά
        ld      hl,st_ord
        ld      a,(osa_j)
        ld      c,a
        ld      b,0
        add     hl,bc
        dec     hl
        ld      a,(hl)
        inc     hl
        ld      (hl),a
        ld      a,(osa_j)
        dec     a
        ld      (osa_j),a
        jr      osa_in
osa_place:
        ld      hl,st_ord
        ld      a,(osa_j)
        ld      c,a
        ld      b,0
        add     hl,bc
        ld      (hl),e
        pop     bc
        inc     c
        djnz    osa_out
osa_draw:
        ld      a,(st_n)
        ld      b,a
        ld      hl,st_ord
osa_dl:
        push    bc
        push    hl
        ld      a,(hl)
        call    ob_struct
        pop     hl
        inc     hl
        pop     bc
        djnz    osa_dl
        ret

; osa_key — A = δείκτης μέσα στο st_ord -> A = cy+128, E = το id.
osa_key:
        ld      l,a
        ld      h,0
        ld      de,st_ord
        add     hl,de
        ld      a,(hl)
        ld      e,a
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      bc,G_struct_tbl + ST_CY
        add     hl,bc
        ld      a,(hl)
        add     a,128
        ret

; ---------------------------------------------------------------------------
; ob_clip_full / ob_clip_set — το παράθυρο σχεδίασης.
; ---------------------------------------------------------------------------
ob_clip_full:
        xor     a
        ld      (clip_x0),a
        ld      (clip_y0),a
        ld      a,SCR_W
        ld      (clip_x1),a
        ld      a,PLAY_LINES
        ld      (clip_y1),a
        ret

; --- πίνακες ---------------------------------------------------------------
; Ανά μέγεθος θόλου: QW, QH, dome_nw, ring_nw, icon_ptr, icon_w, icon_h
dome_geo:
        db      DOME_S_W, DOME_S_H
        dw      G_dome_s_nw, G_ring_s_nw, G_icon_s_ptr
        db      ICON_S_W, ICON_S_H
        db      DOME_M_W, DOME_M_H
        dw      G_dome_m_nw, G_ring_m_nw, G_icon_m_ptr
        db      ICON_M_W, ICON_M_H
        db      DOME_L_W, DOME_L_H
        dw      G_dome_l_nw, G_ring_l_nw, G_icon_l_ptr
        db      ICON_L_W, ICON_L_H

; Ανά κατεύθυνση: sprite, w, h, βήμα x, βήμα y, μετατόπιση αρχής x, y, διαγώνιος;
corr_dir:
        dw G_corr_v  : db CORR_V_W, CORR_V_H,  0,-16,  0,-16, 0   ; n
        dw G_corr_dl : db CORR_D_W, CORR_D_H,  4,-16,  0,  0, 1   ; ne
        dw G_corr_h  : db CORR_H_W, CORR_H_H,  4,  0,  2,  0, 0   ; e
        dw G_corr_dr : db CORR_D_W, CORR_D_H,  4, 16,  0,  0, 1   ; se
        dw G_corr_v  : db CORR_V_W, CORR_V_H,  0, 16,  0,  8, 0   ; s
        dw G_corr_dl : db CORR_D_W, CORR_D_H, -4, 16,  0,  0, 1   ; sw
        dw G_corr_h  : db CORR_H_W, CORR_H_H, -4,  0, -4,  0, 0   ; w
        dw G_corr_dr : db CORR_D_W, CORR_D_H, -4,-16,  0,  0, 1   ; nw

; Από ποιο βήμα του πλέγματος ξεκινά ο διαγώνιος, ανά μέγεθος θόλου.
diag_k:
        db      2, 3, 3

; size*SLOT_BANK. Τρεις λέξεις αντί για πολλαπλασιασμό που δεν χωρά σε 8x8 —
; και η πρώτη γραφή του (x9 και μετά x2) έδινε 18 αντί για 1.152: μόνο οι
; φιγούρες των ΜΕΣΑΙΩΝ και ΜΕΓΑΛΩΝ θόλων έβγαιναν λάθος, δηλαδή ακριβώς όσες
; ένα βλέμμα στην οθόνη δεν θα ξεχώριζε.
ob_sbank:
        dw      0, SLOT_BANK, SLOT_BANK*2

; Ρόλος της προσομοίωσης -> φιγούρα της τέχνης (SPRITES.md §7).
; Δεν είναι ταυτοτικό: η τέχνη έχει τέσσερα ρομπότ και η προσομοίωση τρία, με
; τον ΜΗΧΑΝΙΚΟ ΑΝΘΡΩΠΟ. Ο μηχανικός παίρνει τη φιγούρα 7 (κυανό) γιατί σε 6x6
; pixel το χρώμα είναι η ταυτότητα.
role_fig:
        db      1, 7, 2, 3, 4, 8, 5, 6

; --- μεταβλητές ------------------------------------------------------------
clip_x0:    db 0
clip_x1:    db SCR_W
clip_y0:    db 0
clip_y1:    db PLAY_LINES

ob_src:     dw 0
ob_x:       dw 0
ob_y:       dw 0
ob_w:       db 0
ob_h:       db 0
ob_fl:      db 0
ob_st:      db 0                ; πόσες γραμμές κόπηκαν από πάνω
ob_nl:      db 0                ; πόσες μένουν
ob_sl:      db 0                ; πόσα bytes κόπηκαν από αριστερά
ob_nb:      db 0
ob_x0:      db 0
ob_y0:      db 0
ob_str:     db 0                ; bytes ανά γραμμή πηγής
ob_sk:      dw 0
ob_ln:      dw 0

cl_pos:     dw 0
cl_len:     db 0
cl_lo:      db 0
cl_hi:      db 0
cl_skip:    db 0
cl_n:       db 0
cl_start:   db 0

d_id:       db 0
d_rec:      defs DOME_REC
d_geo:      dw 0
d_fx:       dw 0
d_fy:       dw 0
d_qw:       db 0
d_qh:       db 0

s_rec:      defs STRUCT_REC
c_rec:      defs CORR_REC

oq_cur:     db 0
oc_mask:    db 0
oc_base:    db 0
oc_dir:     db 0
oc_dx:      db 0
oc_dy:      db 0
oc_ox:      db 0
oc_oy:      db 0
oc_diag:    db 0
oc_k:       db 0
oc_n:       db 0

om_n:       db 0
om_slot:    db 0
om_type:    db 0
om_green:   db 0

of_ptr:     dw 0
of_size:    db 0
of_slot:    db 0
of_fig:     db 0
of_acc:     dw 0

ofs_node:   db 0
ofs_slot:   db 0

st_n:       db 0
osa_j:      db 0
st_ord:     defs MAX_STRUCT

; Δύο ευρετήρια που χτίζονται με ΕΝΑ πέρασμα και γλιτώνουν δύο βρόχους:
;   dome_conn[64]     ποιες πόρτες έχει κάθε θόλος   (αλλιώς 64 x 96)
;   dome_fig[64][8]   ποια φιγούρα σε κάθε θέση      (αλλιώς 64 x 128)
dome_conn:  defs MAX_DOME
dome_fig:   defs MAX_DOME*CORR_SLOTS
