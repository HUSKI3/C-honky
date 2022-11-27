// [STD.CK] 
// A standard library for ChonkPC based on code provided by liuk707
// 2022 Copyright liuk707 & HUSKI3

namespace std {
// New line function
// Outputs a new line char
// returns: [void]
func _new_line() void {
    // Call a new line character here
    #embed[assembly] "
    ldr r5, FFFF0000
    ldr r25, 0x0a
    stb r25, r5
    "
}

// Print function
// Outputs [msg] to console
// Takes:
// [msg] CHAR_ARRAY - takes up to 100 characters
// returns [void]
func print(list msg[100]) void {
    !for index in msg {
        putchar(msg[index]);
    }
    !for index in msg {
        msg[index] = 0;
    }
}

// Println function
// Outputs [msg] to console with a new line char
// Takes:
// [msg] CHAR_ARRAY - takes up to 100 characters
// returns [void]
func println(list msg[100]) void {
    !for index in msg {
        putchar(msg[index]);
    }
    #embed[assembly] "
    ldr r5, FFFF0000
    ldr r25, 0x0a
    stb r25, r5
    "
    !for index in msg {
        msg[index] = 0;
    }
}

// Panic function
// Outputs [msg] and hangs
func panic(list msg[100]) void {
    !for index in msg {
        putchar(msg[index]);
    }
    #embed[assembly] "
    ldr r5, FFFF0000
    ldr r25, 0x0a
    stb r25, r5
    "
    int ___ = 0;
    while(___ == 0) {

    }
}

func print_int(int x_arg) void {
    #embed[assembly] "
    ldr r11, {x_arg}
    ldr r0, $2
    jpr r2
    ; iadd r20, #48
    ldr r5, FFFF0000
    stb r20, r5
    "
    std::_new_line();
}
} // End namespace std