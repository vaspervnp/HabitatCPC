; ---------------------------------------------------------------------------
; dzx0.asm — ο αποσυμπιεστής ZX0 του φορτωτή (βήμα 193, DESIGN §13.5).
;
; Ο dzx0_standard του Einar Saukas και του Urusergi, 68 bytes, ως έχει (από το
; ~/rasm/decrunch/dzx0_standard.asm, που είναι macro: εδώ ρουτίνα). Τα αρχεία
; του δίσκου τα συμπιέζει ο rasm (LZX0, tools/zx0.py). Κρατά τον ίδιο χώρο με
; τη ροή του και δεν έχει πίνακες: γράφει μόνο στον προορισμό, και διαβάζει
; τη ροή και ό,τι έχει ήδη γράψει.
;
;   In:  HL = η ροή, DE = ο προορισμός
;   Out: DE = μετά το τελευταίο byte που έγραψε. Χαλάει AF, BC, HL.
;
; ZX0 decoder by Einar Saukas & Urusergi, "Standard" version (68 bytes only).
; (c) Copyright 2021 by Einar Saukas. All rights reserved.
;
; Redistribution and use in source and binary forms, with or without
; modification, are permitted provided that the following conditions are met:
;     * Redistributions of source code must retain the above copyright
;       notice, this list of conditions and the following disclaimer.
;     * Redistributions in binary form must reproduce the above copyright
;       notice, this list of conditions and the following disclaimer in the
;       documentation and/or other materials provided with the distribution.
;     * The name of its author may not be used to endorse or promote products
;       derived from this software without specific prior written permission.
;
; THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS' AND
; ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
; WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
; DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
; DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
; (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
; ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
; (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
; SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
; ---------------------------------------------------------------------------

dzx0:
        ld      bc,#FFFF                ; preserve default offset 1
        push    bc
        inc     bc
        ld      a,#80
dzx0s_literals:
        call    dzx0s_elias             ; obtain length
        ldir                            ; copy literals
        add     a,a                     ; copy from last offset or new offset?
        jr      c,dzx0s_new_offset
        call    dzx0s_elias             ; obtain length
dzx0s_copy:
        ex      (sp),hl                 ; preserve source, restore offset
        push    hl                      ; preserve offset
        add     hl,de                   ; calculate destination - offset
        ldir                            ; copy from offset
        pop     hl                      ; restore offset
        ex      (sp),hl                 ; preserve offset, restore source
        add     a,a                     ; copy from literals or new offset?
        jr      nc,dzx0s_literals
dzx0s_new_offset:
        pop     bc                      ; discard last offset
        ld      c,#FE                   ; prepare negative offset
        call    dzx0s_elias_loop        ; obtain offset MSB
        inc     c
        ret     z                       ; check end marker
        ld      b,c
        ld      c,(hl)                  ; obtain offset LSB
        inc     hl
        rr      b                       ; last offset bit becomes first length bit
        rr      c
        push    bc                      ; preserve new offset
        ld      bc,1                    ; obtain length
        call    nc,dzx0s_elias_backtrack
        inc     bc
        jr      dzx0s_copy
dzx0s_elias:
        inc     c                       ; interlaced Elias gamma coding
dzx0s_elias_loop:
        add     a,a
        jr      nz,dzx0s_elias_skip
        ld      a,(hl)                  ; load another group of 8 bits
        inc     hl
        rla
dzx0s_elias_skip:
        ret     c
dzx0s_elias_backtrack:
        add     a,a
        rl      c
        rl      b
        jr      dzx0s_elias_loop
dzx0_end:
        assert  dzx0_end - dzx0 == 68
