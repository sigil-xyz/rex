# Installation

## Prerequisites

Arch Linux with Hyprland (or any Wayland compositor with hotkey support).

```bash
sudo pacman -S python uv portaudio libsndfile
```

Install Piper TTS:

```bash
# AUR
paru -S piper-tts
or
yay -S piper-tts
# Download a voice model
mkdir -p ~/.local/share/piper
cd ~/.local/share/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

## Install Rex

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
uv sync
uv tool install .
```

## Configure

```bash
mkdir -p ~/.config/rex
cp config/config.example.toml ~/.config/rex/config.toml
```

Edit `~/.config/rex/config.toml` — at minimum set `tts.model` to your Piper voice path.

## systemd Service

```bash
just service-install
```

Verify it started:

```bash
systemctl --user status rex
journalctl --user -u rex -n 20
```

## Hyprland Hotkey

Add to `~/.config/hypr/hyprland.conf`:

```ini
bind = SUPER, Space, exec, rex-trigger start
bindrelease = SUPER, Space, exec, rex-trigger stop
```

Reload Hyprland config: `SUPER+SHIFT+R`

## Test

Hold `SUPER+Space`, say "hello", release. You should hear a voice response and see a notification.

## Troubleshooting

**No audio input detected**

List devices:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

Set the device name or index in `config.toml` under `[audio] device`.

**Piper not found**

Set `tts.piper_bin` in `config.toml` to the full path of the piper binary.

**Daemon not starting**

```bash
journalctl --user -u rex -n 50
```
