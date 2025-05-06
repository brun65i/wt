#!/usr/bin/env bash

function wt() {
  dest=$(uv run ~/code/wt/main.py "$@")
  if [ -d "$dest" ]; then
    cd "$dest" || exit 1
  fi
}
