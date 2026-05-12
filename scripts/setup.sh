#!/usr/bin/env bash
# Rex setup script
# Detects hardware, installs the right STT backend, downloads Piper + voice model,
# writes config.toml, and (on Linux) installs the systemd user service.
#
# Usage: bash scripts/setup.sh
# Must be run from the Rex repository root.

set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────

VOICE_DIR="$HOME/.local/share/piper/voices"
CONFIG_DIR="$HOME/.config/rex"
CONFIG_FILE="$CONFIG_DIR/config.toml"
VOICE_NAME="en_US-lessac-medium"
VOICE_URL_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"

# set by detect_hardware()
STT_BACKEND="faster-whisper"
REX_EXTRA=""

# set by install_piper()
PIPER_BIN="piper-tts"

# set by download_voice_model()
VOICE_MODEL_PATH="$VOICE_DIR/$VOICE_NAME.onnx"

# ── Output helpers ─────────────────────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

step()    { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }
ok()      { echo -e "  ${GREEN}✓${NC}  $*"; }
warn()    { echo -e "  ${YELLOW}!${NC}  $*"; }
die()     { echo -e "\n  ${RED}✗  $*${NC}" >&2; exit 1; }
dimline() { echo -e "  ${DIM}$*${NC}"; }

# ── Utilities ─────────────────────────────────────────────────────────────────

download() {
    local url="$1" dest="$2"
    if command -v curl &>/dev/null; then
        curl -fL --progress-bar -o "$dest" "$url"
    elif command -v wget &>/dev/null; then
        wget -q --show-progress -O "$dest" "$url"
    else
        die "Neither curl nor wget found. Install one and re-run."
    fi
}

in_path() { command -v "$1" &>/dev/null; }

# ── Guards ────────────────────────────────────────────────────────────────────

check_repo_root() {
    [[ -f pyproject.toml && -f scripts/setup.sh ]] \
        || die "Run this script from the Rex repository root:\n  bash scripts/setup.sh"
}

check_python() {
    in_path python3 || die "Python 3 is required. Install Python 3.11+ and re-run."
    local ver
    ver=$(python3 -c "import sys; print(sys.version_info >= (3, 11))")
    [[ "$ver" == "True" ]] || die "Python 3.11+ required. Found: $(python3 --version)"
}

# ── Detection ─────────────────────────────────────────────────────────────────

OS="$(uname -s)"
ARCH="$(uname -m)"

is_macos()         { [[ "$OS" == "Darwin" ]]; }
is_linux()         { [[ "$OS" == "Linux" ]]; }
is_apple_silicon() { is_macos && [[ "$ARCH" == "arm64" ]]; }

detect_hardware() {
    step "Detecting hardware"

    if is_apple_silicon; then
        STT_BACKEND="mlx"
        REX_EXTRA="mlx"
        ok "Apple Silicon ($ARCH) — will use mlx-whisper"
        return
    fi

    if is_macos; then
        ok "Intel Mac — will use faster-whisper"
        return
    fi

    # Linux: check NVIDIA GPU VRAM
    if in_path nvidia-smi; then
        local vram_mb
        vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null \
            | head -1 | tr -d ' ' || echo 0)
        vram_mb=${vram_mb:-0}

        if [[ "$vram_mb" -ge 6144 ]]; then
            STT_BACKEND="parakeet"
            REX_EXTRA="parakeet"
            ok "NVIDIA GPU with ${vram_mb} MB VRAM — will use Parakeet"
        else
            ok "NVIDIA GPU with ${vram_mb} MB VRAM (below 6 GB threshold) — will use faster-whisper"
        fi
    else
        ok "No NVIDIA GPU detected — will use faster-whisper"
    fi
}

# ── System dependencies ───────────────────────────────────────────────────────

install_system_deps() {
    step "System dependencies"

    if is_macos; then
        in_path brew || die "Homebrew not found. Install it from https://brew.sh then re-run."
        if brew list portaudio &>/dev/null 2>&1; then
            ok "portaudio already installed"
        else
            brew install portaudio
            ok "portaudio"
        fi

    elif is_linux && in_path pacman; then
        local missing=()
        pacman -Qi portaudio  &>/dev/null 2>&1 || missing+=(portaudio)
        pacman -Qi libsndfile &>/dev/null 2>&1 || missing+=(libsndfile)
        if [[ ${#missing[@]} -gt 0 ]]; then
            sudo pacman -S --needed --noconfirm "${missing[@]}"
            ok "${missing[*]}"
        else
            ok "portaudio + libsndfile already installed"
        fi

    else
        warn "Unknown distro. Ensure portaudio and libsndfile are installed before continuing."
    fi
}

# ── uv ────────────────────────────────────────────────────────────────────────

ensure_uv() {
    step "uv package manager"

    if in_path uv; then
        ok "uv already installed ($(uv --version))"
        return
    fi

    if is_macos && in_path brew; then
        brew install uv
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi

    in_path uv || die "uv installation failed. Add ~/.local/bin to your PATH and re-run."
    ok "uv installed ($(uv --version))"
}

# ── Piper TTS binary ──────────────────────────────────────────────────────────

install_piper() {
    step "Piper TTS"

    if in_path piper-tts; then
        PIPER_BIN="piper-tts"
        ok "piper-tts already in PATH ($(command -v piper-tts))"
        return
    fi

    # Arch Linux: try AUR first (paru or yay)
    if is_linux && in_path pacman; then
        if in_path paru; then
            paru -S --needed --noconfirm piper-tts 2>/dev/null && {
                ok "piper-tts installed via AUR (paru)"
                PIPER_BIN="piper-tts"
                return
            } || true
        elif in_path yay; then
            yay -S --needed --noconfirm piper-tts 2>/dev/null && {
                ok "piper-tts installed via AUR (yay)"
                PIPER_BIN="piper-tts"
                return
            } || true
        fi
    fi

    # Fallback: PyPI wheel (works on macOS arm64/x86_64 and Linux x86_64)
    dimline "Installing piper-tts via uv..."
    uv tool install piper-tts
    export PATH="$HOME/.local/bin:$PATH"

    in_path piper-tts \
        || die "piper-tts not found after install. Add ~/.local/bin to your PATH and re-run."

    PIPER_BIN="piper-tts"
    ok "piper-tts installed ($(command -v piper-tts))"
}

# ── Piper voice model ─────────────────────────────────────────────────────────

download_voice_model() {
    step "Piper voice model ($VOICE_NAME)"
    mkdir -p "$VOICE_DIR"

    local onnx="$VOICE_DIR/$VOICE_NAME.onnx"
    local json="$VOICE_DIR/$VOICE_NAME.onnx.json"

    if [[ -f "$onnx" && -f "$json" ]]; then
        ok "Already present at $onnx"
        VOICE_MODEL_PATH="$onnx"
        return
    fi

    dimline "Downloading model weights (~63 MB)..."
    download "$VOICE_URL_BASE/$VOICE_NAME.onnx"      "$onnx"
    download "$VOICE_URL_BASE/$VOICE_NAME.onnx.json" "$json"

    VOICE_MODEL_PATH="$onnx"
    ok "Saved to $onnx"
}

# ── Rex installation ──────────────────────────────────────────────────────────

install_rex() {
    step "Installing Rex"

    local install_spec="."
    [[ -n "$REX_EXTRA" ]] && install_spec=".[$REX_EXTRA]"

    dimline "uv tool install --force \"$install_spec\""
    uv tool install --force "$install_spec"

    export PATH="$HOME/.local/bin:$PATH"
    in_path rex || die "rex not found after install. Add ~/.local/bin to your PATH."

    ok "rex installed ($(command -v rex))"
    [[ -n "$REX_EXTRA" ]] && ok "  extra: [$REX_EXTRA]"
}

# ── Config ────────────────────────────────────────────────────────────────────

write_config() {
    step "Configuration"

    if [[ -f "$CONFIG_FILE" ]]; then
        warn "Config already exists at $CONFIG_FILE — skipping"
        warn "Delete it and re-run to regenerate"
        return
    fi

    # Prompt for API key
    echo ""
    echo -e "  Rex needs an OpenAI-compatible LLM API key."
    echo -e "  ${DIM}(Leave blank to configure later in $CONFIG_FILE)${NC}"
    echo ""
    read -r -p "  API key: " api_key || api_key=""

    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_FILE" <<EOF
# Rex configuration
# Full reference: https://github.com/sigil-xyz/rex/blob/main/docs/configuration.md

[daemon]
log_level = "info"

[audio]
# Input device — leave empty for system default
# List devices: python3 -c "import sounddevice; print(sounddevice.query_devices())"
device      = ""
sample_rate = 16000

[stt]
# "auto" detects the best backend at startup (parakeet / mlx / faster-whisper)
backend = "$STT_BACKEND"
# model = ""  # leave empty to use the backend default

[tts]
piper_bin = "$PIPER_BIN"
model     = "$VOICE_MODEL_PATH"

[llm]
api_key = "$api_key"

[notification]
enabled = true
timeout = 5000
EOF

    ok "Config written to $CONFIG_FILE"
}

# ── systemd service (Linux only) ──────────────────────────────────────────────

install_service() {
    step "systemd user service"

    if systemctl --user is-active rex &>/dev/null 2>&1; then
        warn "rex.service already running — restarting"
        systemctl --user restart rex
        ok "rex.service restarted"
        return
    fi

    mkdir -p "$HOME/.config/systemd/user"
    cp systemd/rex.service "$HOME/.config/systemd/user/rex.service"
    systemctl --user daemon-reload
    systemctl --user enable --now rex

    ok "rex.service enabled and started"
}

# ── Summary ───────────────────────────────────────────────────────────────────

print_summary() {
    echo ""
    echo -e "${BOLD}${GREEN}Setup complete.${NC}"
    echo ""
    echo -e "  ${BOLD}STT backend${NC}  $STT_BACKEND"
    echo -e "  ${BOLD}Voice model${NC}  $VOICE_MODEL_PATH"
    echo -e "  ${BOLD}Config${NC}       $CONFIG_FILE"
    echo ""

    if is_linux; then
        echo -e "${BOLD}Hyprland hotkey${NC} — add to ~/.config/hypr/hyprland.conf:"
        echo ""
        echo "    bind        = SUPER, Space, exec, rex-trigger start"
        echo "    bindrelease = SUPER, Space, exec, rex-trigger stop"
        echo ""
        echo -e "  Reload config: ${CYAN}SUPER+SHIFT+R${NC}"
        echo ""
        echo -e "${BOLD}Test:${NC} hold SUPER+Space, say something, release."

    elif is_macos; then
        echo -e "${BOLD}Start Rex manually:${NC}"
        echo "    rex"
        echo ""
        echo -e "${BOLD}Hotkey:${NC} bind 'rex-trigger start' (key down) and"
        echo "        'rex-trigger stop' (key up) via skhd or Karabiner-Elements."
    fi

    echo ""
    if [[ -z "${api_key:-}" ]]; then
        echo -e "  ${YELLOW}!${NC}  Set your LLM API key in ${CYAN}$CONFIG_FILE${NC} before using Rex."
    fi
    echo ""
}

# ── Entry point ───────────────────────────────────────────────────────────────

main() {
    echo -e "\n${BOLD}Rex Setup${NC}"
    echo -e "${DIM}$(uname -s) / $(uname -m)${NC}\n"

    check_repo_root
    check_python
    detect_hardware
    install_system_deps
    ensure_uv
    install_piper
    download_voice_model
    install_rex
    write_config
    is_linux && install_service
    print_summary
}

main "$@"
