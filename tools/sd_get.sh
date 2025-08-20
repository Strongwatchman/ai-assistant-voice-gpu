#!/usr/bin/env bash
set -euo pipefail
cache="${CACHE_DIR:-$HOME/Downloads/sd_models_cache}"
mkdir -p "$cache"

usage() {
  echo "Usage: sd_get.sh <subdir> <url> [<rename_to>]"
  echo "  <subdir> in {checkpoints, loras, vae, upscale_models}"
  exit 1
}

[[ $# -lt 2 ]] && usage
sub="$1"; url="$2"; name="${3:-}"

dest_root="$HOME/AI_Assistant/ComfyUI/models/$sub"
mkdir -p "$dest_root"

# guess filename if not provided
if [[ -z "$name" ]]; then
  # try to extract tail name; fall back to timestamp
  name="$(basename "${url%%\?*}")"
  [[ -z "$name" || "$name" == "/" ]] && name="$(date +%s).bin"
fi

tmp="$cache/.partial_${name}"
out_cache="$cache/$name"
out="$dest_root/$name"

echo "→ downloading:"
echo "  subdir : $sub"
echo "  url    : $url"
echo "  file   : $name"

# prefer aria2c if present (faster & resume), else curl
if command -v aria2c >/dev/null 2>&1; then
  aria2c -x 8 -s 8 -k 1M -d "$cache" -o "$name" "$url"
else
  curl -L --retry 5 --retry-delay 2 --fail --output "$tmp" "$url"
  mv "$tmp" "$out_cache"
fi

# move into ComfyUI models
mv -f "$out_cache" "$out"
echo "✅ saved: $out"
