from enum import Enum
from pickle import FALSE
from colour import Color
import argparse
import time
from rpi_ws281x import PixelStrip
import sys, pygame, pygame.midi

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

class Preset:
    def __init__(self, name, idx, param):
        self.name = name
        self.idx = idx
        self.param = param
    #wipe = 1
    #theaterChase = 2
    #wheel = 3
    #rainbow = 4
    #rainbowCycle = 5
    #theaterChaseRainbow = 6

PRESETS = [Preset("Solid Gradient", 0, 0)]

# Global bookkeeping  
curPreset = PRESETS[0]
curColor = Color("red") # Start with red
curBrightness = 0.8 # Medium-high brightness

def get24BitColor(color):
    return (int(color.red * 255) << 16) | (int(color.green * 255) << 8) | int(color.blue * 255)

# Returns a list of nb color HSL tuples between begin_hsl and end_hsl
def colorScale(begin_hsl, end_hsl, nb):
    if nb < 0:
        raise ValueError("Unsupported negative number of colors (nb=%r)." % nb)

    step = tuple([float(end_hsl[i] - begin_hsl[i]) / nb for i in range(0, 3)]) \
           if nb > 0 else (0, 0, 0)

    def mul(step, value):
        return tuple([v * value for v in step])
    def add_v(step, step2):
        return tuple([(v + step2[i]) % 1.0001 for i, v in enumerate(step)])
    return [add_v(begin_hsl, mul(step, r)) for r in range(0, nb + 1)]

def rangeTo(start, end, steps):
    for hsl in colorScale(start.hsl, end.hsl, steps - 1):
        yield Color(hsl=hsl)

# Define functions which animate LEDs in various ways.
#def colorWipe(strip, color, wait_ms=50):
#    """Wipe color across display a pixel at a time."""
#    for i in range(strip.numPixels()):
#        strip.setPixelColor(i, color)
#        if (wait_ms != 0): 
#                strip.show()
#       		time.sleep(wait_ms / 1000.0)
#    strip.show()
#
#def theaterChase(strip, color, wait_ms=50, iterations=10):
#    """Movie theater light style chaser animation."""
#    for j in range(iterations):
#        for q in range(3):
#            for i in range(0, strip.numPixels(), 3):
#                strip.setPixelColor(i + q, color)
#            strip.show()
#            time.sleep(wait_ms / 1000.0)
#            for i in range(0, strip.numPixels(), 3):
#                strip.setPixelColor(i + q, 0)
#
#def wheel(pos):
#    """Generate rainbow colors across 0-255 positions."""
#    if pos < 85:
#        return Color(pos * 3, 255 - pos * 3, 0)
#    elif pos < 170:
#        pos -= 85
#        return Color(255 - pos * 3, 0, pos * 3)
#    else:
#        pos -= 170
#        return Color(0, pos * 3, 255 - pos * 3)

#def rainbow(strip, wait_ms=20, iterations=1):
#    """Draw rainbow that fades across all pixels at once."""
#    for j in range(256 * iterations):
#        for i in range(strip.numPixels()):
#            strip.setPixelColor(i, wheel((i + j) & 255))
#        strip.show()
#        time.sleep(wait_ms / 1000.0)

#def rainbowCycle(strip, wait_ms=20, iterations=5):
#    """Draw rainbow that uniformly distributes itself across all pixels."""
#    for j in range(256 * iterations):
#        for i in range(strip.numPixels()):
#            strip.setPixelColor(i, wheel(
#                (int(i * 256 / strip.numPixels()) + j) & 255))
#        strip.show()
#        time.sleep(wait_ms / 1000.0)

#def theaterChaseRainbow(strip, wait_ms=50):
#    """Rainbow movie theater light style chaser animation."""
#    for j in range(256):
#        for q in range(3):
#            for i in range(0, strip.numPixels(), 3):
#                strip.setPixelColor(i + q, wheel((i + j) % 255))
#            strip.show()
#            time.sleep(wait_ms / 1000.0)
#            for i in range(0, strip.numPixels(), 3):
#                strip.setPixelColor(i + q, 0)

# Applies a solid gradient across the strip
# gradientAmount: Amount of hue to interpolate for the end color of the strip (0.0-1.0)
def solidGradient(strip):
    endHue = curColor.hue + curPreset.param
    print("--")
    print(curColor.hue)
    print(endHue)
    endColor = Color(hue = endHue, saturation = 1, luminance = curColor.luminance)
    gradientColors = list(rangeTo(curColor, endColor, LED_COUNT))
    for i in range(strip.numPixels()):
        pixelColor = get24BitColor(gradientColors[i])
        strip.setPixelColor(i, pixelColor)
    strip.show()

def handleMidiMessage(strip, message):
    messageCC = message[0][1]
    messageVal = message[0][2]
    global curPreset
    # Update current preset
    for i in range(len(PRESETS)):
        if messageCC == PRESETS[i].idx:
            if curPreset.name != PRESETS[i].name:
                curPreset = PRESETS[i]
            curPreset.param = messageVal / 128.0
    # Update base color and brightness
    if messageCC == MIDI_CC_COLOR:
        curColor.hue = messageVal / 128.0
    elif messageCC == MIDI_CC_BRIGHTNESS:
        curColor.luminance = messageVal / 256.0

    # Update LED strip based on current preset
    if curPreset.name == "Solid Gradient":
        solidGradient(strip)

# Main program logic follows:
if __name__ == '__main__':
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    for i in range(strip.numPixels()):
        strip.setPixelColor(i, get24BitColor(curColor))
    strip.show()

    # set up pygame
    pygame.init()
    pygame.midi.init()

    # open the first non-internal MIDI internal device
    inp = pygame.midi.Input(3)

    try:
        while True:
            if inp.poll():
                # Only process the most recent MIDI message to avoid redundant operations
                handleMidiMessage(strip, inp.read(1000)[-1])
            time.sleep(50.0/1000)

    except KeyboardInterrupt:
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, 0)
        strip.show()

