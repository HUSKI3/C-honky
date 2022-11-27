// [GL.CK] 
// A graphics library for ChonkPC.
// 2022 Copyright liuk707 & HUSKI3

// Keep track of queued bytes (max 256)
int queued = 0;

namespace GL {
// Executes command fifo
func draw() void {
    [0xFFFF8100, byte] = 0x1;
}

// Waits for a VBLANK to happen.
func vsync() void {
    #embed[assembly] "
    ldr r23, FFFF8120
    ldr r25, .__glvsync__
    ldr r26, 1
    ldr r27, 0
.__glvsync__
    ldb r24, r23
    jprne r25, r24, r26
    stb r27, r23
    "
}

// Draws, waits for VBLANK, draws again.
func draw_double() void {
    GL::draw();
    GL::vsync();
    GL::draw();
}

// Clears the command fifo.
func clear_cmd_fifo() void {
    [0xFFFF811C, byte] = 0x1;
    queued = 0;
}

// Fills the screen with the given RGB color.
func clear(int r, int g, int b) void {
    GL::clear_cmd_fifo();
    [0xFFFF8001, byte] = 0x01; // Clear screen
    [0xFFFF8002, byte] = r;
    [0xFFFF8003, byte] = g;
    [0xFFFF8004, byte] = b;
}
 
// Queues a triangle in the command FIFO
func tri(
    int x1, int y1, 
    int x2, int y2, 
    int x3, int y3, 
    int r1, int g1, int b1, 
    int r2, int g2, int b2, 
    int r3, int g3, int b3
) void {
    GL::clear_cmd_fifo();
    [0xFFFF8001, byte] = 0x10; // Draw tri
    [0xFFFF8002, byte] = x1 >> 8;
    [0xFFFF8003, byte] = x1 & 0xff;
    [0xFFFF8004, byte] = y1 >> 8;
    [0xFFFF8005, byte] = y1 & 0xff;
    [0xFFFF8006, byte] = x2 >> 8;
    [0xFFFF8007, byte] = x2 & 0xff;
    [0xFFFF8008, byte] = y2 >> 8;
    [0xFFFF8009, byte] = y2 & 0xff;
    [0xFFFF800a, byte] = x3 >> 8;
    [0xFFFF800b, byte] = x3 & 0xff;
    [0xFFFF800c, byte] = y3 >> 8;
    [0xFFFF800d, byte] = y3 & 0xff;
    [0xFFFF800e, byte] = r1;
    [0xFFFF800f, byte] = g1;
    [0xFFFF8010, byte] = b1;
    [0xFFFF8011, byte] = r2;
    [0xFFFF8012, byte] = g2;
    [0xFFFF8013, byte] = b2;
    [0xFFFF8014, byte] = r3;
    [0xFFFF8015, byte] = g3;
    [0xFFFF8016, byte] = b3;
}

// Queues a textured triangle in the command FIFO
func textri(
    int x1, int y1, 
    int x2, int y2, 
    int x3, int y3,
    int tx1, int ty1,
    int tx2, int ty2,
    int tx3, int ty3 
) void {
    GL::clear_cmd_fifo();
    [0xFFFF8001, byte] = 0x11; // Draw tri
    [0xFFFF8002, byte] = x1 >> 8;
    [0xFFFF8003, byte] = x1 & 0xff;
    [0xFFFF8004, byte] = y1 >> 8;
    [0xFFFF8005, byte] = y1 & 0xff;
    [0xFFFF8006, byte] = x2 >> 8;
    [0xFFFF8007, byte] = x2 & 0xff;
    [0xFFFF8008, byte] = y2 >> 8;
    [0xFFFF8009, byte] = y2 & 0xff;
    [0xFFFF800a, byte] = x3 >> 8;
    [0xFFFF800b, byte] = x3 & 0xff;
    [0xFFFF800c, byte] = y3 >> 8;
    [0xFFFF800d, byte] = y3 & 0xff;
    [0xFFFF800e, byte] = tx1 >> 8;
    [0xFFFF800f, byte] = tx1 & 0xff;
    [0xFFFF8010, byte] = ty1 >> 8;
    [0xFFFF8011, byte] = ty1 & 0xff;
    [0xFFFF8012, byte] = tx2 >> 8;
    [0xFFFF8013, byte] = tx2 & 0xff;
    [0xFFFF8014, byte] = ty2 >> 8;
    [0xFFFF8015, byte] = ty2 & 0xff;
    [0xFFFF8016, byte] = tx3 >> 8;
    [0xFFFF8017, byte] = tx3 & 0xff;
    [0xFFFF8018, byte] = ty3 >> 8;
    [0xFFFF8019, byte] = ty3 & 0xff;
}

// Queues a quad in the command FIFO.
// A quad is split into two triangles, one with vertices v1, v2, v3 and one
// with vertices v2, v3, v4.
func quad(
    int x1, int y1, 
    int x2, int y2, 
    int x3, int y3, 
    int x4, int y4, 
    int r1, int g1, int b1, 
    int r2, int g2, int b2, 
    int r3, int g3, int b3,
    int r4, int g4, int b4
) void {
    GL::clear_cmd_fifo();
    [0xFFFF8001, byte] = 0x10; // Draw tri
    [0xFFFF8002, byte] = x1 >> 8;
    [0xFFFF8003, byte] = x1 & 0xff;
    [0xFFFF8004, byte] = y1 >> 8;
    [0xFFFF8005, byte] = y1 & 0xff;
    [0xFFFF8006, byte] = x2 >> 8;
    [0xFFFF8007, byte] = x2 & 0xff;
    [0xFFFF8008, byte] = y2 >> 8;
    [0xFFFF8009, byte] = y2 & 0xff;
    [0xFFFF800a, byte] = x3 >> 8;
    [0xFFFF800b, byte] = x3 & 0xff;
    [0xFFFF800c, byte] = y3 >> 8;
    [0xFFFF800d, byte] = y3 & 0xff;
    [0xFFFF800e, byte] = r1;
    [0xFFFF800f, byte] = g1;
    [0xFFFF8010, byte] = b1;
    [0xFFFF8011, byte] = r2;
    [0xFFFF8012, byte] = g2;
    [0xFFFF8013, byte] = b2;
    [0xFFFF8014, byte] = r3;
    [0xFFFF8015, byte] = g3;
    [0xFFFF8016, byte] = b3;
    [0xFFFF8017, byte] = 0x10; // Draw tri
    [0xFFFF8018, byte] = x2 >> 8;
    [0xFFFF8019, byte] = x2 & 0xff;
    [0xFFFF801a, byte] = y2 >> 8;
    [0xFFFF801b, byte] = y2 & 0xff;
    [0xFFFF801c, byte] = x3 >> 8;
    [0xFFFF801d, byte] = x3 & 0xff;
    [0xFFFF801e, byte] = y3 >> 8;
    [0xFFFF801f, byte] = y3 & 0xff;
    [0xFFFF8020, byte] = x4 >> 8;
    [0xFFFF8021, byte] = x4 & 0xff;
    [0xFFFF8022, byte] = y4 >> 8;
    [0xFFFF8023, byte] = y4 & 0xff;
    [0xFFFF8024, byte] = r2;
    [0xFFFF8025, byte] = g2;
    [0xFFFF8026, byte] = b2;
    [0xFFFF8027, byte] = r3;
    [0xFFFF8028, byte] = g3;
    [0xFFFF8029, byte] = b3;
    [0xFFFF802a, byte] = r4;
    [0xFFFF802b, byte] = g4;
    [0xFFFF802c, byte] = b4;
}

// Queues a textured quad in the command FIFO. Texture coordinates work like the vertices: refer to the
// above function for more info.
func texquad(
    int x1, int y1, 
    int x2, int y2, 
    int x3, int y3,
    int x4, int y4,
    int tx1, int ty1,
    int tx2, int ty2,
    int tx3, int ty3, 
    int tx4, int ty4 
) void {
    GL::clear_cmd_fifo();
    [0xFFFF8001, byte] = 0x11; // Draw tri
    [0xFFFF8002, byte] = x1 >> 8;
    [0xFFFF8003, byte] = x1 & 0xff;
    [0xFFFF8004, byte] = y1 >> 8;
    [0xFFFF8005, byte] = y1 & 0xff;
    [0xFFFF8006, byte] = x2 >> 8;
    [0xFFFF8007, byte] = x2 & 0xff;
    [0xFFFF8008, byte] = y2 >> 8;
    [0xFFFF8009, byte] = y2 & 0xff;
    [0xFFFF800a, byte] = x3 >> 8;
    [0xFFFF800b, byte] = x3 & 0xff;
    [0xFFFF800c, byte] = y3 >> 8;
    [0xFFFF800d, byte] = y3 & 0xff;
    [0xFFFF800e, byte] = tx1 >> 8;
    [0xFFFF800f, byte] = tx1 & 0xff;
    [0xFFFF8010, byte] = ty1 >> 8;
    [0xFFFF8011, byte] = ty1 & 0xff;
    [0xFFFF8012, byte] = tx2 >> 8;
    [0xFFFF8013, byte] = tx2 & 0xff;
    [0xFFFF8014, byte] = ty2 >> 8;
    [0xFFFF8015, byte] = ty2 & 0xff;
    [0xFFFF8016, byte] = tx3 >> 8;
    [0xFFFF8017, byte] = tx3 & 0xff;
    [0xFFFF8018, byte] = ty3 >> 8;
    [0xFFFF8019, byte] = ty3 & 0xff;
    [0xFFFF801a, byte] = 0x11; // Draw tri
    [0xFFFF801b, byte] = x2 >> 8;
    [0xFFFF801c, byte] = x2 & 0xff;
    [0xFFFF801d, byte] = y2 >> 8;
    [0xFFFF801e, byte] = y2 & 0xff;
    [0xFFFF801f, byte] = x3 >> 8;
    [0xFFFF8020, byte] = x3 & 0xff;
    [0xFFFF8021, byte] = y3 >> 8;
    [0xFFFF8022, byte] = y3 & 0xff;
    [0xFFFF8023, byte] = x4 >> 8;
    [0xFFFF8024, byte] = x4 & 0xff;
    [0xFFFF8025, byte] = y4 >> 8;
    [0xFFFF8026, byte] = y4 & 0xff;
    [0xFFFF8027, byte] = tx2 >> 8;
    [0xFFFF8028, byte] = tx2 & 0xff;
    [0xFFFF8029, byte] = ty2 >> 8;
    [0xFFFF802a, byte] = ty2 & 0xff;
    [0xFFFF802b, byte] = tx3 >> 8;
    [0xFFFF802c, byte] = tx3 & 0xff;
    [0xFFFF802d, byte] = ty3 >> 8;
    [0xFFFF802e, byte] = ty3 & 0xff;
    [0xFFFF802f, byte] = tx4 >> 8;
    [0xFFFF8030, byte] = tx4 & 0xff;
    [0xFFFF8031, byte] = ty4 >> 8;
    [0xFFFF8032, byte] = ty4 & 0xff;
}

// Uploads a texture to VRAM.
func texture(
    int saddr,
    int dest_x,
    int dest_y,
    int width,
    int height    
) void {
    [0xFFFF8104, word] = saddr;
    [0xFFFF8108, word] = dest_x;
    [0xFFFF810C, word] = dest_y;
    [0xFFFF8110, word] = width;
    [0xFFFF8114, word] = height;
    [0xFFFF8118, byte] = 0x1;
}
} // End namespace GL