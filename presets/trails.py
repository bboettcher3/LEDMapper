from colour import Color
import random
LED_COUNT = 150        # Number of LED pixels.
MAX_TRAILS = 10
TRAIL_WIDTH = int(LED_COUNT * 0.66)

def _get24BitColor(color):
    return (int(color.red * 255) << 16) | (int(color.green * 255) << 8) | int(color.blue * 255)

# Returns a list of nb color HSL tuples between begin_hsl and end_hsl
def _colorScale(begin_hsl, end_hsl, nb):
    if nb < 0:
        raise ValueError("Unsupported negative number of colors (nb=%r)." % nb)

    step = tuple([float(end_hsl[i] - begin_hsl[i]) / nb for i in range(0, 3)]) \
           if nb > 0 else (0, 0, 0)

    def mul(step, value):
        return tuple([v * value for v in step])
    def add_v(step, step2):
        return tuple([(v + step2[i]) % 1.0001 for i, v in enumerate(step)])
    return [add_v(begin_hsl, mul(step, r)) for r in range(0, nb + 1)]

def _rangeTo(start, end, steps):
    for hsl in _colorScale(start.hsl, end.hsl, steps - 1):
        yield Color(hsl=hsl)

# Creates light trails at different rates
# numTrails: Number of trails
def trails(strip, state):
    numTrails = max(1, int(state.param * MAX_TRAILS))
    endHue = state.color.hue + state.colorWidth
    endColor = Color(hue = endHue, saturation = 1, luminance = state.color.luminance)
    trailColors = list(_rangeTo(state.color, endColor, numTrails))
    trailSpeeds = [(i + 1) * state.movementRate / numTrails for i in range(numTrails)]
    trailPositions = [int(state.timestamp * state.movementRate * 8 * trailSpeeds[i]) % LED_COUNT for i in range(numTrails)]
    #print(trailSpeeds)
    #print(state.movementRate)
    #print("----")
    for i in range(strip.numPixels()):
        hueContribs = []
        strengthContribs = []
        for j in range(numTrails):
            trailEndPos = trailPositions[j] - TRAIL_WIDTH
            strength = 0.0
            if i <= trailPositions[j] and i >= trailEndPos:
                strength = (i - trailEndPos) / float(TRAIL_WIDTH)
            elif i > trailPositions[j] and i >= (trailEndPos % LED_COUNT):
                strength = (i - LED_COUNT - trailEndPos) / float(TRAIL_WIDTH)
            if strength > 0.01:
                hueContribs.append(trailColors[j].hue)
                strengthContribs.append(strength)
        if len(hueContribs) > 0:
            weightedSum = sum([hueContribs[i]*strengthContribs[i] for i in range(len(hueContribs))])
            finalHue = weightedSum / sum(strengthContribs)
            finalLum = min(0.5, sum(strengthContribs) / 4.0)
            #print(f"{i}: {strengthContribs}")
            pixelColor = _get24BitColor(Color(hue=finalHue, saturation=1, luminance=finalLum))
        else:
            pixelColor = _get24BitColor(Color("black"))
        strip.setPixelColor(i, pixelColor)
    strip.show()
