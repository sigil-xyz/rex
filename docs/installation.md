# Installation

## Quick setup (recommended)

Clone the repo and run the setup script. It detects your hardware, installs the right STT backend,
downloads Piper and a voice model, and writes your config automatically.

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
bash scripts/setup.sh
```

The script handles everything below. Read on only if you prefer a manual setup or need to
troubleshoot.

---

## Manual setup

### 1. System dependencies

<details>
<summary><strong>Linux — Arch</strong></summary>

```bash
sudo pacman -S python uv portaudio libsndfile
```

</details>

<details>
<summary><strong>Linux — Debian / Ubuntu</strong></summary>

```bash
sudo apt install python3 python3-pip portaudio19-dev libsndfile1
pip install uv
```

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install portaudio uv
```

</details>

---

### 2. Install Rex

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
uv tool install .
```

#### Optional extras — better STT backends

| Extra | Hardware | Command |
|-------|----------|---------|
| `parakeet` | NVIDIA GPU, ≥6 GB VRAM | `uv tool install ".[parakeet]"` |
| `mlx` | Apple Silicon (M1/M2/M3/M4) | `uv tool install ".[mlx]"` |

With `backend = "auto"` in your config (the default), Rex detects at startup which backend to use
and falls back to `faster-whisper` if the extra is not installed.

---

### 3. Install Piper TTS

**macOS and Linux (no AUR):**

```bash
uv tool install piper-tts
```

**Linux — Arch (AUR):**

```bash
paru -S piper-tts   # or: yay -S piper-tts
```

---

### 4. Download a voice model

```bash
mkdir -p ~/.local/share/piper/voices
cd ~/.local/share/piper/voices
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

For other voices see the [Piper voice repository](https://huggingface.co/rhasspy/piper-voices).

---

### 5. Configure

```bash
mkdir -p ~/.config/rex
cp config/config.example.toml ~/.config/rex/config.toml
```

Open `~/.config/rex/config.toml` and set at minimum:

```toml
[tts]
model = "/home/yourname/.local/share/piper/voices/en_US-lessac-medium.onnx"

[llm]
api_key = "your-api-key"
```

Full config reference: [docs/configuration.md](configuration.md)

---

### 6. Start Rex

**Linux — systemd:**

```bash
just service-install
```

Verify:

```bash
systemctl --user status rex
journalctl --user -u rex -n 20
```

**macOS — foreground (or add to launchd manually):**

```bash
rex
```

---

### 7. Bind a hotkey

**Hyprland** — add to `~/.config/hypr/hyprland.conf`:

```ini
bind        = SUPER, Space, exec, rex-trigger start
bindrelease = SUPER, Space, exec, rex-trigger stop
```

Reload: `SUPER+SHIFT+R`

**macOS — skhd** — add to `~/.skhdrc`:

```
alt - space : rex-trigger start
```

skhd does not support key-up binds natively; use Karabiner-Elements for push-to-talk behaviour
(bind a key's `key_down` to `rex-trigger start` and `key_up` to `rex-trigger stop`).

---

## Troubleshooting

**No audio input detected**

```bash
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

Set `device` in `[audio]` to the device name or index.

**Piper not found**

Set `tts.piper_bin` to the full path of the binary, e.g. `~/.local/bin/piper-tts`.

**Wrong voice model path**

Set `tts.model` to the absolute path of your `.onnx` file.

**Daemon not starting (Linux)**

```bash
journalctl --user -u rex -n 50
```

**Daemon not starting (macOS)**

```bash
rex   # run in foreground to see errors
```
