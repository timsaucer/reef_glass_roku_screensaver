# Roku Streaming Store listing

Text and assets for the Developer Dashboard (developer.roku.com). Lengths checked against
Roku's limits.

## Listing text

**Name** (22/30): Reef Glass Screensaver

**On-device description** (281/300):

> A fully animated reef tank, not a slideshow. Clownfish, tangs, damselfish and a pufferfish that puffs up swim their own paths among photoreal coral, a moray breathes in its cave, and the view glides along a tank two screens wide. Daylight by default, or dusk, night, or your clock.

**Online description** (1448/1500):

```
Reef Glass is a fully animated aquarium, not a slideshow or a slow pan across a still photo. Every fish swims live, choosing its own path, so the tank never plays the same way twice.

Clownfish, blue and yellow tangs, royal grammas, a school of blue damselfish and a porcupine pufferfish swim among photoreal coral. Built from 3D models, they turn with real depth, bend through their turns, climb and dive, pass in front of and behind the reef, and keep a little apart. The clownfish pair stays together near their anemone. The pufferfish now and then puffs up into a spiny ball. A bright orange dragon moray breathes in its cave and pulls back into the dark when a big fish swims close. Feather duster worms snap shut as fish pass, and a starfish creeps over the sand.

The tank is about two screens wide, and the view glides slowly across it and back. Light shafts fall from the surface, and the reef is mirrored faintly in the water surface and the back glass.

Lighting is daytime by default; pick a blue dusk, dim moonlit night, or have it follow your Roku's clock under Settings > Theme > Screensavers > Reef Glass > Change screensaver settings. No ads, no accounts, no network access.

About the art: every image was made for Reef Glass with open models run locally (Z-Image-Turbo, FLUX.2 klein 4B, TripoSR). All of it is public domain (CC0 1.0); the code is open source (Apache 2.0). Source: github.com/timsaucer/reef_glass_roku_screensaver
```

## Assets

| Field | File |
|---|---|
| Poster, 540x405 | `store/poster-540x405.jpg` |
| Screenshots, 1920x1080 | `store/screenshots/1-day.jpg`, `2-day-anemone.jpg`, `3-day-cave.jpg`, `4-dusk.jpg`, `5-night.jpg`, `6-settings.jpg` |
| Privacy policy URL | https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/PRIVACY.md |
| Terms of use URL | https://github.com/timsaucer/reef_glass_roku_screensaver/blob/main/TERMS.md |
| Support | https://github.com/timsaucer/reef_glass_roku_screensaver/issues |

Suggested settings: monetization **Free**; category **Screensavers** (or Lifestyle, if the
dashboard offers no screensaver category); rating: all ages; no deep linking.

## Signed package

Signed with the developer key already on the dev Roku (shared with Dusk; DevID and password in
the gitignored `.env`, keep a copy in a password manager). Every update must use the same key.

```sh
tools/package.sh   # installs the --release build, writes build/reefglass-<version>.pkg
```

Bump `build_version` (or `minor_version`) in `roku/reefglass/manifest` before each upload.

## Dashboard checklist (account owner)

1. Developer Dashboard › **Beta apps** › **Create app**. A beta publishes at once on a private
   link and runs Static Analysis, so the signed package is tested outside developer mode.
   Repeat under **Public apps** once it is clean. Profile type: Theme (no screensaver type is
   offered; the manifest makes it a screensaver).
2. Fill in the listing text; upload the poster and screenshots.
3. Upload `build/reefglass-<version>.pkg`.
4. Run Static Analysis and App Behavior Analysis; fix anything flagged.
5. Countries, privacy policy and support URLs, submit. Public apps are scheduled for the second
   business day at the earliest (not Fridays or weekends).
6. After installing the beta: Settings › Theme › Screensavers › Reef Glass, and its
   "Change screensaver settings" entry.
