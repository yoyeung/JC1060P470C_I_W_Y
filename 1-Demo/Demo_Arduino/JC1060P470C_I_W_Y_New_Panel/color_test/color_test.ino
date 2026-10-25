// JC1060P470C (new panel, JD9165 1024x600 MIPI-DSI) - automatic colour / display test
//
// Runs a standard display test sequence in a loop with the backlight at 50%:
//   full-field primaries / secondaries / white / black / greys  (uniformity, dead & stuck pixels)
//   colour bars (75% and 100%)                                   (colour reproduction)
//   grey-scale steps and smooth R/G/B/W ramps                     (gamma, banding)
//   checkerboards, 1-px pattern, crosshatch, border, window       (crosstalk, flicker, geometry, edges)
// Each pattern name is printed on Serial (115200) so a test log can be captured.

#include <Arduino.h>
#include "esp_heap_caps.h"
#include "pins_config.h"
#include "src/lcd/jd9165_lcd.h"

#define BACKLIGHT_PERCENT 50   // test brightness
#define PATTERN_MS        3000 // time each pattern stays on screen

jd9165_lcd lcd = jd9165_lcd(LCD_RST);
static uint16_t *fb;

static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b)
{
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

static const uint16_t WHITE   = 0xFFFF;
static const uint16_t BLACK   = 0x0000;
static const uint16_t RED     = 0xF800;
static const uint16_t GREEN   = 0x07E0;
static const uint16_t BLUE    = 0x001F;
static const uint16_t CYAN    = 0x07FF;
static const uint16_t MAGENTA = 0xF81F;
static const uint16_t YELLOW  = 0xFFE0;

static inline void px(int x, int y, uint16_t c) { fb[y * LCD_H_RES + x] = c; }

static void fill(uint16_t c)
{
  for (int i = 0; i < LCD_H_RES * LCD_V_RES; i++) fb[i] = c;
}

static void rect(int x0, int y0, int w, int h, uint16_t c)
{
  for (int y = y0; y < y0 + h; y++)
    for (int x = x0; x < x0 + w; x++) px(x, y, c);
}

static void present()
{
  lcd.lcd_draw_bitmap(0, 0, LCD_H_RES, LCD_V_RES, fb);
}

// ---------- patterns ----------

static void p_white()   { fill(WHITE); }
static void p_black()   { fill(BLACK); }
static void p_red()     { fill(RED); }
static void p_green()   { fill(GREEN); }
static void p_blue()    { fill(BLUE); }
static void p_cyan()    { fill(CYAN); }
static void p_magenta() { fill(MAGENTA); }
static void p_yellow()  { fill(YELLOW); }
static void p_grey25()  { fill(rgb565(64, 64, 64)); }
static void p_grey50()  { fill(rgb565(128, 128, 128)); }
static void p_grey75()  { fill(rgb565(192, 192, 192)); }

// 8 vertical bars: W Y C G M R B K, at the given level (191 = 75%, 255 = 100%)
static void color_bars(uint8_t lv)
{
  const uint8_t m[8][3] = {{1,1,1},{1,1,0},{0,1,1},{0,1,0},{1,0,1},{1,0,0},{0,0,1},{0,0,0}};
  int w = LCD_H_RES / 8;
  for (int i = 0; i < 8; i++)
    rect(i * w, 0, (i == 7) ? LCD_H_RES - 7 * w : w, LCD_V_RES,
         rgb565(m[i][0] * lv, m[i][1] * lv, m[i][2] * lv));
}
static void p_bars75()  { color_bars(191); }
static void p_bars100() { color_bars(255); }

// 16-step grey scale, black on the left
static void p_grey_steps()
{
  for (int x = 0; x < LCD_H_RES; x++) {
    uint8_t v = (x * 16 / LCD_H_RES) * 255 / 15;
    uint16_t c = rgb565(v, v, v);
    for (int y = 0; y < LCD_V_RES; y++) px(x, y, c);
  }
}

// Four horizontal bands with smooth 0..255 ramps: R, G, B, W
static void p_ramps()
{
  int h = LCD_V_RES / 4;
  for (int x = 0; x < LCD_H_RES; x++) {
    uint8_t v = x * 255 / (LCD_H_RES - 1);
    uint16_t c[4] = {rgb565(v, 0, 0), rgb565(0, v, 0), rgb565(0, 0, v), rgb565(v, v, v)};
    for (int y = 0; y < LCD_V_RES; y++) px(x, y, c[min(y / h, 3)]);
  }
}

static void checker(int size)
{
  for (int y = 0; y < LCD_V_RES; y++)
    for (int x = 0; x < LCD_H_RES; x++)
      px(x, y, ((x / size + y / size) & 1) ? WHITE : BLACK);
}
static void p_checker_big() { checker(LCD_V_RES / 8); }
static void p_checker_1px() { checker(1); }

// White 1-px grid every 64 px, plus centre cross and full border
static void p_crosshatch()
{
  fill(BLACK);
  for (int x = 0; x < LCD_H_RES; x += 64) rect(x, 0, 1, LCD_V_RES, WHITE);
  for (int y = 0; y < LCD_V_RES; y += 60) rect(0, y, LCD_H_RES, 1, WHITE);
  rect(LCD_H_RES - 1, 0, 1, LCD_V_RES, WHITE);
  rect(0, LCD_V_RES - 1, LCD_H_RES, 1, WHITE);
  rect(LCD_H_RES / 2 - 1, 0, 2, LCD_V_RES, RED);
  rect(0, LCD_V_RES / 2 - 1, LCD_H_RES, 2, RED);
}

// 1-px border in R/G/B/W on each edge, to check no rows/columns are cut off
static void p_border()
{
  fill(BLACK);
  rect(0, 0, LCD_H_RES, 1, RED);
  rect(0, LCD_V_RES - 1, LCD_H_RES, 1, GREEN);
  rect(0, 0, 1, LCD_V_RES, BLUE);
  rect(LCD_H_RES - 1, 0, 1, LCD_V_RES, WHITE);
}

// Centre white window covering 1/9 of the area on black (crosstalk / blooming)
static void p_window()
{
  fill(BLACK);
  rect(LCD_H_RES / 3, LCD_V_RES / 3, LCD_H_RES / 3, LCD_V_RES / 3, WHITE);
}

struct test_pattern {
  const char *name;
  void (*draw)();
};

static const test_pattern patterns[] = {
  {"Full white",          p_white},
  {"Full black",          p_black},
  {"Full red",            p_red},
  {"Full green",          p_green},
  {"Full blue",           p_blue},
  {"Full cyan",           p_cyan},
  {"Full magenta",        p_magenta},
  {"Full yellow",         p_yellow},
  {"Grey 25%",            p_grey25},
  {"Grey 50%",            p_grey50},
  {"Grey 75%",            p_grey75},
  {"Colour bars 75%",     p_bars75},
  {"Colour bars 100%",    p_bars100},
  {"Grey scale 16 steps", p_grey_steps},
  {"RGBW ramps",          p_ramps},
  {"Checkerboard 8x8",    p_checker_big},
  {"Checkerboard 1px",    p_checker_1px},
  {"Crosshatch",          p_crosshatch},
  {"Border",              p_border},
  {"Centre window",       p_window},
};
static const int pattern_count = sizeof(patterns) / sizeof(patterns[0]);

void setup()
{
  Serial.begin(115200);
  Serial.println("JC1060P470C colour test");

  lcd.begin();
  lcd.example_bsp_set_lcd_backlight(BACKLIGHT_PERCENT);

  fb = (uint16_t *)heap_caps_malloc(LCD_H_RES * LCD_V_RES * sizeof(uint16_t), MALLOC_CAP_SPIRAM);
  assert(fb);

  Serial.printf("%dx%d, backlight %d%%, %d patterns, %d ms each\n",
                LCD_H_RES, LCD_V_RES, BACKLIGHT_PERCENT, pattern_count, PATTERN_MS);
}

void loop()
{
  static uint32_t cycle = 0;
  cycle++;
  for (int i = 0; i < pattern_count; i++) {
    Serial.printf("[cycle %lu] %2d/%d %s\n", cycle, i + 1, pattern_count, patterns[i].name);
    patterns[i].draw();
    present();
    delay(PATTERN_MS);
  }
}
