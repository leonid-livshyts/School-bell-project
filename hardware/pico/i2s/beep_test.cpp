// Standalone I2S tone test for the PCM5102A DAC. Diagnostic only.
//
// Absolute-minimum version: ONE constant 440Hz sine, forever. No SPI, no MP3,
// no DMA, no volume changes, and NOTHING printed inside the audio loop -- so
// nothing periodic can interrupt the feed. The TX FIFO is joined (8 deep) so a
// background USB interrupt can't starve the PIO. If this rings a clean, steady
// tone, the earlier "ripple" was my own test artifacts (periodic printf + the
// 3s volume cycling); if it still ripples, something periodic is genuinely
// interrupting the output and we chase that.
//
// Pins: BCLK=GP2, LRC=GP3, DIN=GP4, 44.1kHz, 16-bit stereo.
#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/gpio.h"
#include "hardware/clocks.h"
#include "i2s.pio.h"

#define PIN_I2S_BCLK 2
#define PIN_I2S_LRC  3
#define PIN_I2S_DIN  4

#define SAMPLE_RATE  44100
#define TONE_HZ      440
#define AMPLITUDE    12000
#define SINE_N       1024

static int16_t sine_tab[SINE_N];

static inline void i2s_output_program_init(PIO pio, uint sm, uint offset,
                                           uint pin_din, uint pin_bclk, float clk_div) {
    pio_sm_config c = i2s_output_program_get_default_config(offset);
    sm_config_set_out_pins(&c, pin_din, 1);
    sm_config_set_sideset_pins(&c, pin_bclk);
    sm_config_set_clkdiv(&c, clk_div);
    sm_config_set_out_shift(&c, false, true, 32);
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX); // 8-deep TX FIFO for margin

    pio_gpio_init(pio, pin_din);
    pio_gpio_init(pio, pin_bclk);
    pio_gpio_init(pio, PIN_I2S_LRC);

    pio_sm_init(pio, sm, offset, &c);
    uint32_t io_mask = (1u << pin_bclk) | (1u << PIN_I2S_LRC) | (1u << pin_din);
    pio_sm_set_pindirs_with_mask(pio, sm, io_mask, io_mask);
    pio_sm_set_enabled(pio, sm, true);
}

static inline uint32_t stereo_word(int16_t s) {
    return ((uint32_t)(uint16_t)s << 16) | (uint16_t)s;
}

int main() {
    // Force the Pico's on-board SMPS into PWM mode instead of the default
    // PFM/power-save mode. GPIO23 (SMPS "PS" control): low = PFM (under light
    // load it switches at a low, VARIABLE frequency -- tens of Hz -- which
    // ripples the 3.3V rail); high = fixed ~1MHz PWM (much cleaner rail). The DAC
    // is powered from this rail, so PFM ripple AM-modulates the audio == the
    // ~25Hz warble. This is the standard Pico fix for analog/audio noise.
    gpio_init(23);
    gpio_set_dir(23, GPIO_OUT);
    gpio_put(23, 1);

    stdio_init_all();
    for (int i = 0; i < 4; i++) {
        printf("=== beep_test v6 (SMPS PWM mode via GPIO23, %dHz sine) ===\n", TONE_HZ);
        sleep_ms(300);
    }
    for (int i = 0; i < SINE_N; i++)
        sine_tab[i] = (int16_t)(AMPLITUDE * sinf(2.0f * (float)M_PI * i / SINE_N));

    PIO pio = pio0;
    uint sm = pio_claim_unused_sm(pio, true);
    uint offset = pio_add_program(pio, &i2s_output_program);
    // TEST: force an INTEGER clock divider (no fractional part) so BCLK has zero
    // divider jitter. The PCM5102A's internal PLL (no-MCLK mode) can turn the
    // fractional-divider jitter (44.29) into an audible warble/ripple. Integer
    // truncation makes the pitch ~0.7% sharp (inaudible) but the clock clean.
    uint32_t whole_div = clock_get_hz(clk_sys) / (SAMPLE_RATE * 32 * 2); // 44
    float div = (float)whole_div;
    i2s_output_program_init(pio, sm, offset, PIN_I2S_DIN, PIN_I2S_BCLK, div);
    printf("clk_sys=%lu  integer div=%.1f  playing constant %dHz sine\n",
           (unsigned long)clock_get_hz(clk_sys), div, TONE_HZ);

    uint32_t phase = 0;
    uint32_t phase_inc = (uint32_t)(((uint64_t)TONE_HZ * SINE_N << 16) / SAMPLE_RATE);
    while (1) {
        int16_t s = sine_tab[(phase >> 16) & (SINE_N - 1)];
        phase += phase_inc;
        pio_sm_put_blocking(pio, sm, stereo_word(s)); // nothing else in this loop
    }
}
