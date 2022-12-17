; enter
ldr r0, .entry
jpr r0

.entry
    ; l1 reserved for current action
    ldr r3, .pchr
    ldr r4, .lvar
    ldr r9, .done

    ; Most code goes here
    {code}
    
    jpr r9

.cmemw
    ldw r20, r11
    jpr r0

.cmemh
    ldh r20, r11
    jpr r0

.cmemb
    ldb r20, r11
    jpr r0

.lmemw
    stw r20, r11
    jpr r0

.lmemh
    sth r20, r11
    jpr r0

.lmemb
    stb r20, r11
    jpr r0

.pchr
    ldr r5, FFFF0000
    stb r20, r5
    jpr r0

.lvar
    mov r21, r0

    ; store at addr
    ldr r0, $2
    jpr r1

    jpr r21

; Func declarations go here
{func_code}

.done
    jpr r9