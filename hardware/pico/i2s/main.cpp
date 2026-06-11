#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/spi.h"
#include "hardware/pio.h"
#include "i2s.pio.h"
#include "mp3dec.h" // Helix MP3 Decoder library
#include "hardware/clocks.h"


#define SPI_PORT    spi0
#define PIN_MISO    16
#define PIN_CS      17
#define PIN_SCK     18
#define PIN_MOSI    19

#define PIN_I2S_BCLK 2
#define PIN_I2S_LRC  3
#define PIN_I2S_DIN  4

// Initialize I2S PIO state machine
static inline void i2s_output_program_init(PIO pio, uint sm, uint offset, 
                                           uint pin_din, uint pin_bclk, float clk_div) {
    pio_sm_config c = i2s_output_program_get_default_config(offset);
    
    // Set data output pin
    sm_config_set_out_pins(&c, pin_din, 1);
    
    // Set side-set pins (BCLK and LRC)
    sm_config_set_sideset_pins(&c, pin_bclk);
    
    // Set the clock divider
    sm_config_set_clkdiv(&c, clk_div);
    
    // Set shift configuration for I2S
    sm_config_set_out_shift(&c, false, true, 32);
    
    // Initialize GPIO pins as PIO outputs
    pio_gpio_init(pio, pin_din);
    pio_gpio_init(pio, pin_bclk);
    pio_gpio_init(pio, PIN_I2S_LRC);
    
    // Set pins as outputs
    gpio_set_dir(pin_din, GPIO_OUT);
    gpio_set_dir(pin_bclk, GPIO_OUT);
    gpio_set_dir(PIN_I2S_LRC, GPIO_OUT);
    
    // Load configuration and start state machine
    pio_sm_init(pio, sm, offset, &c);
    pio_sm_set_enabled(pio, sm, true);
}

#define BUFFER_SIZE 16384 // 16KB compressed data ring buffer
uint8_t ring_buffer[BUFFER_SIZE];
volatile uint32_t write_ptr = 0;
volatile uint32_t read_ptr = 0;

// Core 1: Dedicated Audio Decoding & I2S Output Loop
void core1_entry() {
    HMP3Decoder hMP3Decoder = MP3InitDecoder();
    short sample_buffer[MAX_NCHAN * MAX_NSAMP]; // Out PCM buffer
    
    // Initialize PIO for I2S
    PIO pio = pio0;
    uint sm = pio_claim_unused_sm(pio, true);
    uint offset = pio_add_program(pio, &i2s_output_program);
    
    // Configure PIO clock rate for 44.1kHz 16-bit Stereo audio
    float div = (float)clock_get_hz(clk_sys) / (44100 * 32 * 2); 
    i2s_output_program_init(pio, sm, offset, PIN_I2S_DIN, PIN_I2S_BCLK, div);

    while (1) {
        uint32_t bytes_available = (write_ptr >= read_ptr) ? 
                                   (write_ptr - read_ptr) : 
                                   (BUFFER_SIZE - read_ptr + write_ptr);

        if (bytes_available > 2048) { // Wait for a solid frame chunk
            uint8_t *read_ptr_addr = &ring_buffer[read_ptr];
            int bytes_left = bytes_available;
            
            // Locate next valid MP3 frame header
            int sync_offset = MP3FindSyncWord(read_ptr_addr, bytes_left);
            if (sync_offset >= 0) {
                read_ptr = (read_ptr + sync_offset) % BUFFER_SIZE;
                bytes_left -= sync_offset;
                
                MP3FrameInfo frame_info;
                int err = MP3Decode(hMP3Decoder, &read_ptr_addr, &bytes_left, sample_buffer, 0);
                
                if (err == ERR_MP3_NONE) {
                    MP3GetLastFrameInfo(hMP3Decoder, &frame_info);
                    
                    // Shove the decoded samples into the PIO Tx FIFO
                    int samples = frame_info.outputSamps;
                    for (int i = 0; i < samples; i++) {
                        // Wait if FIFO is full, then push 16-bit sample
                        pio_sm_put_blocking(pio, sm, (uint32_t)sample_buffer[i]);
                    }
                }
            }
            // Advance the read pointer across processed bytes safely
            read_ptr = (BUFFER_SIZE - bytes_left + read_ptr) % BUFFER_SIZE;
        }
    }
}

// Core 0: High-Speed SPI Slave Data Ingest Loop
int main() {
    stdio_init_all();

    // Setup SPI Slave to accept data from the ESP32
    spi_init(SPI_PORT, 10000000); // 10 MHz clock rate
    spi_set_slave(SPI_PORT, true);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI);

    // Launch Core 1 DSP Engine
    multicore_launch_core1(core1_entry);

    uint8_t spi_rx_packet[512];

    while (1) {
        // Read data packet chunks from ESP32 master
        spi_read_blocking(SPI_PORT, 0, spi_rx_packet, sizeof(spi_rx_packet));
        size_t read_bytes = sizeof(spi_rx_packet);
        
        // Copy directly into the ring buffer
        for (size_t i = 0; i < read_bytes; i++) {
            uint32_t next_write = (write_ptr + 1) % BUFFER_SIZE;
            if (next_write != read_ptr) { // Avoid over-writing unread data
                ring_buffer[write_ptr] = spi_rx_packet[i];
                write_ptr = next_write;
            }
        }
    }
}
