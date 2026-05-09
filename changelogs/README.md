# Changelog Fragments

Every PR that changes user-visible behavior must include a fragment in this directory.

## Format

Filename: `<pr-number>.md`

Content: one or more plain sentences describing the change from a user's perspective. No headings, no bullet points.

## Examples

`42.md`:
```
Added push-to-talk via Hyprland `bindrelease` — hold SUPER+Space to record, release to process.
```

`67.md`:
```
Fixed audio device selection — Rex now respects the `audio.device` config key instead of always using the default device.
```

`89.md`:
```
Breaking: renamed config key `voice_model` to `tts_model`. Update your `config.toml` before upgrading.
```

## Compilation

Fragments are compiled into `CHANGELOG.md` during release via `just release <version>`.
Do not edit `CHANGELOG.md` directly — edit fragments instead.
