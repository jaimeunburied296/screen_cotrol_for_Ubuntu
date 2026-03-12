---
name: screen-control
description: "Control the local Ubuntu desktop mouse, keyboard and screenshots using pyautogui and xdotool."
metadata:
  openclaw:
    emoji: "🖱️"
    os:
      - linux
    requires:
      bins:
        - xdotool
        - gnome-screenshot
---

# What this skill does

This skill lets the agent control the local Ubuntu VM desktop:

- Move the mouse to a given coordinate
- Click / right-click / double-click
- Drag from one point to another
- Scroll at a given location
- Type text
- Trigger common hotkeys (copy / paste / select all / undo / redo / address bar / refresh)
- Press single keys like Enter / Esc / Tab reliably
- Focus target windows by title before actions
- Probe current active window + mouse position (focus-probe)
- Retry click around a base point to handle small offset errors (click-retry)
- Take full-screen screenshots and save them to disk

All commands are executed via this Python script and virtualenv:

- Script: `/home/moderlick/tools/screen_tool.py`
- Python: `/home/moderlick/tools/screen-env/.venv/bin/python`

Always call it like:

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py <subcommand> [options...]

Session note:

- Prefer **Xorg (x11)** session for reliable mouse/keyboard control.
- Under Wayland, pyautogui input simulation may fail due to compositor security restrictions.

## Move the mouse

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py move --position 255,255

## Click

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py click --position 400,300
    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py click --position 400,300 --right
    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py click --position 400,300 --double

## Drag

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py drag --start 100,100 --end 600,400 --duration 0.8

## Scroll

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py scroll --position 800,400 --amount -500

## Type text

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py type --text "Hello from OpenClaw"

## Hotkeys

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py hotkey --combo copy
    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py hotkey --combo address_bar

## Press single key

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py press --key enter
    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py press --key esc

## Focus window

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py focus --name "Firefox|火狐"

## Focus probe (check active window + mouse)

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py focus-probe

## Click retry (small-offset compensation)

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py click-retry --position 1148,768 --radius 30 --step 8 --retries 5

Recommended web workflow:

1. focus Firefox
2. focus-probe
3. click-retry on target input area
4. type text
5. press enter

## Screenshots

    /home/moderlick/tools/screen-env/.venv/bin/python /home/moderlick/tools/screen_tool.py screenshot
