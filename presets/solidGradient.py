from colour import Color
LED_COUNT = 150        # Number of LED pixels.

def _get24BitColor(color):
    return (int(color.red * 255) << 16) | (int(color.green * 255) << 8) | int(color.blue * 255)

# Returns a list of nb color HSL tuples between begin_hsl and end_hsl
def _colorScale(begin_hsl, end_hsl, nb):
    if nb < 0:
        raise ValueError("Unsupported negative number of colors (nb=%r)." % nb)

    step = tuple([float(end_hsl[i] - begin_hsl[i]) // nb for i in range(0, 3)]) \
           if nb > 0 else (0, 0, 0)

    def mul(step, value):
        return tuple([v * value for v in step])
    def add_v(step, step2):
        return tuple([(v + step2[i]) % 1.0001 for i, v in enumerate(step)])
    return [add_v(begin_hsl, mul(step, r)) for r in range(0, nb + 1)]

def _rangeTo(start, end, steps):
    for hsl in _colorScale(start.hsl, end.hsl, steps - 1):
        yield Color(hsl=hsl)

# Applies a solid gradient across the strip
# gradientAmount: Amount of hue to interpolate for the end color of the strip (0.0-1.0)
def solidGradient(strip, state):
    curColor = state.color
    curMovementRate = state.movementRate
    endHue = curColor.hue + state.param
    endColor = Color(hue = endHue, saturation = 1, luminance = curColor.luminance)
    gradientColors = list(_rangeTo(curColor, endColor, LED_COUNT // 2))
    smoothColors = gradientColors + list(reversed(gradientColors))
    startIdx = int(state.timestamp * curMovementRate * 4) % LED_COUNT
    rotColors = [smoothColors[(i+startIdx) % len(smoothColors)] for i in range(len(smoothColors))]
    for i in range(strip.numPixels()):
        pixelColor = _get24BitColor(rotColors[i])
        strip.setPixelColor(i, pixelColor)
    strip.show()
