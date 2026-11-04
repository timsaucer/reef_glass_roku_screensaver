# Roku Streaming Store listing

Text and assets for the Developer Dashboard (developer.roku.com). Lengths checked against
Roku's limits.

## Listing text

**Name** (22/30): Reef Glass Screensaver

**On-device description** (247/300):

> A calm saltwater reef tank on your TV. Clownfish, tangs, damselfish, a pufferfish that puffs up and a moray eel in its cave swim among photoreal coral, with light rippling over the sand. Lighting follows your clock, or stays at day, dusk or night.

**Online description** (1246/1500):

```
Reef Glass turns your TV into a quiet saltwater reef tank, seen full screen through the glass.

Clownfish, blue and yellow tangs, royal grammas, a school of blue damselfish and a porcupine pufferfish swim among the coral, turning with real depth, passing in front of and behind the reef, and keeping a little apart. The pufferfish now and then puffs up into a spiny ball. A snowflake moray breathes in its cave and pulls back into the dark when a big fish swims close. Feather duster worms snap shut as fish pass, a starfish creeps over the sand, and light ripples across the sand from the surface.

Lighting follows your Roku's clock (daylight, a blue dusk, dim moonlight at night), or pick daytime, dusk or night under Settings > Theme > Screensavers > Reef Glass > Change screensaver settings. No ads, no accounts, no network access.

About the art: every image was made for Reef Glass. The tank and the animals were generated locally with the open Z-Image-Turbo model (Apache 2.0); the fish were then rebuilt in 3D (TripoSR, MIT) so they turn convincingly. All of the art is dedicated to the public domain under CC0 1.0, and the code is open source under Apache 2.0. Prompts, seeds and source: github.com/timsaucer/reef_glass_roku_screensaver
```

## Assets

| Field | File |
|---|---|
| Poster, 540x405 | `store/poster-540x405.jpg` |
| Screenshots, 1920x1080 | `store/screenshots/1-day.jpg`, `2-day-school.jpg`, `3-dusk.jpg`, `4-night.jpg`, `5-settings.jpg` |
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
