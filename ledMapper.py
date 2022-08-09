# Local imports
from presets.solidGradient import solidGradient
from presets.trails import trails

# Standard library
from enum import Enum
from pickle import FALSE
import argparse
import logging
import sys
import time

# Third-party libraries
from colour import Color
from recordclass import recordclass
from rpi_ws281x import PixelStrip
import pygame, pygame.midi

# This program uses a Faderfox MIDI controller to select and control up to 14 LED strip preset patterns.

# LED strip configuration:
LED_COUNT = 150        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 200  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

# MIDI controller CCs
MIDI_CC_BRIGHTNESS = 15
MIDI_CC_COLOR = 11
MIDI_CC_MV_RATE = 7
MIDI_CC_COLOR_WIDTH = 3

# Other globals
TICK_RATE_MS = 30.0
RESOLUTION_MIDI = 128.0
RESOLUTION_24BIT = 256.0
DEFAULT_BRIGHTNESS = 0.8
DEFAULT_COLOR_WIDTH = 0.0

LEDState = recordclass("LEDState", ["movementRate", "color", "colorWidth", "brightness", "param", "timestamp"])
Preset = recordclass("Preset", ["name", "func"])

class LEDManager:
    def __init__(self, presets, strip):
        self.presets = presets
        self._input = None
        self._currentPreset = 0
        self._strip = strip
        self._state = LEDState(0.0, Color("red"), DEFAULT_COLOR_WIDTH, DEFAULT_BRIGHTNESS, 0.0, 0)

    def handleMidiMessage(self, message):
        messageCC, messageVal = message[0][1], message[0][2]
        # Update base color and brightness
        if messageCC == MIDI_CC_COLOR:
            self._state.color.hue = messageVal / RESOLUTION_MIDI
        elif messageCC == MIDI_CC_BRIGHTNESS:
            self._state.color.luminance = messageVal / RESOLUTION_24BIT
        elif messageCC == MIDI_CC_MV_RATE:
            self._state.movementRate = messageVal / RESOLUTION_MIDI
        elif messageCC == MIDI_CC_COLOR_WIDTH:
            self._state.colorWidth = messageVal / RESOLUTION_MIDI
        else:
            self.changePreset(messageCC)
            self._state.param = messageVal / RESOLUTION_MIDI

    def changePreset(self, idx):
        if idx < 0 or idx >= len(self.presets):
            logging.warning(f"Preset ID {idx} is out of range 0-{len(self.presets)-1}!")
        else:
            self._currentPreset = idx

    def tick(self):
        self.currentPreset.func(self._strip, self._state)
        self._state.timestamp = (self._state.timestamp + 1) % (LED_COUNT * 16)

    @property
    def currentPreset(self):
        return self.presets[self._currentPreset]

# Main program logic follows:
if __name__ == '__main__':
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    # set up pygame
    pygame.init()
    pygame.midi.init()
    # open the first non-internal MIDI internal device
    inp = pygame.midi.Input(3)

    presets = [Preset("Solid Gradient", solidGradient), Preset("Trails", trails)]
    LEDS = LEDManager(presets, strip)

    try:
        while True:
            if inp.poll():
                # Only process the most recent MIDI message to avoid redundant operations
                LEDS.handleMidiMessage(inp.read(1000)[-1])
            # Update LED strip based on current preset
            LEDS.tick()
            time.sleep(TICK_RATE_MS/1000)

    except KeyboardInterrupt:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, 0)
        strip.show()

