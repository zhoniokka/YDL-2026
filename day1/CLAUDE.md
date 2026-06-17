# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Practice/learning workspace (`ydl2026/day1`). Currently contains a single Python script and is in an early/empty state — there is no build system, dependency manifest, or test suite yet.

## Files

- `simple.py` — a 2-line script that reads a name from stdin and prints it.
- `creds.txt` — **contains live API credentials** (plaintext bearer keys) for the `llm.alem.ai` OpenAI-compatible API: a `gemma4` chat endpoint (`/v1/chat/completions`) and a `text-to-image` endpoint (`/v1/images/generations`), plus example request bodies. Treat as secret; do not commit. See the git warning below.

## Running

```sh
python simple.py
```

`simple.py` calls `input()`, so it expects interactive stdin.

## Notes

- This folder is **not** its own git repository — the enclosing git repo is rooted at the user's home directory (`C:/Users/Админ`). Be careful with `git` commands: `git add -A` from here would stage the entire home directory. Stage specific paths explicitly.
