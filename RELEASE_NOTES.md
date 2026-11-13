# Reef Glass 1.1.3

A fix for Rokus with less graphics memory.

- **No more crashes on start:** on some lower-end Rokus, Reef Glass could close as soon as it
  started, because the tank's pictures did not all fit in graphics memory. It now loads the
  background and reef first. If something still does not fit, the tank leaves out a fish species
  or a piece of reef instead of crashing.
- **Less memory for the fish:** fish swimming to the left no longer keep a second, mirrored copy
  of their pictures, which halves the memory the fish use.

---

# Reef Glass 1.1.2

The first public release of Reef Glass, a screensaver for Roku: a calm saltwater reef tank seen
through the glass. It is fully animated, not a slideshow or a slow pan across a still photo, and
every fish swims live and chooses its own path.

No earlier version was released publicly, so these notes cover everything in the screensaver.

## The tank

- **A wide view:** the tank is about two screens wide, and the view glides slowly across it and
  back.
- **Fish:** a clownfish pair, blue and yellow tangs, royal grammas, a loose school of blue
  damselfish and a porcupine pufferfish that now and then puffs up into a spiny ball. Built from
  3D models, they bend through their turns, tilt as they climb and dive, pass in front of and
  behind the reef, and keep a little apart.
- **Critters:** a dragon moray breathes in its cave and pulls back into the dark when a big fish
  swims close. Feather duster worms snap shut as fish pass, and a starfish creeps over the sand.
- **Light and water:** light shafts fall from the surface, marine snow drifts past, and the reef
  is mirrored faintly in the water surface and the back glass.

## Lighting

The tank runs in daytime lighting unless you change it. The other choices are dusk, a dim
moonlit night, or following your Roku's clock.

To change it, go to **Settings > Theme > Screensavers > Reef Glass > Change screensaver
settings**.

## Turning it on

After installing, choose Reef Glass under **Settings > Theme > Screensavers**.

## Privacy

Reef Glass has no ads, accounts or purchases, and it makes no network requests. The only thing it
saves is your lighting choice, on your Roku. See the [privacy policy](https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/PRIVACY.md).

## Compatibility

Reef Glass has been tested on multiple Roku Express sticks and a Roku Ultra, and by 19 additional
beta testers. If it stutters or looks wrong on your Roku, please
[open an issue](https://github.com/timsaucer/reef_glass_roku_screensaver/issues) and include your
Roku model.

## Open source

The code is licensed under
[Apache 2.0](https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/LICENSE), and all
the art is public domain under
[CC0 1.0](https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/LICENSE-ART). Every
image was made for Reef Glass with open models run locally (Z-Image-Turbo, FLUX.2 klein 4B and
TripoSR). The prompts, seeds and processing steps are in
[CREDITS.md](https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/CREDITS.md).
