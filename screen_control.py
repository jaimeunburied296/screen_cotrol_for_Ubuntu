#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import subprocess
import time

# Directory where screenshots are saved
BASE_DIR = os.path.expanduser('~/openclaw_screens')
os.makedirs(BASE_DIR, exist_ok=True)


def _human_delay(min_delay: float = 0.2, max_delay: float = 0.4) -> None:
    """Sleep for a small random duration to make actions feel natural."""
    time.sleep(random.uniform(min_delay, max_delay))


def _load_pyautogui():
    """Load pyautogui and return module, or print JSON error and return None."""
    try:
        import pyautogui  # type: ignore

        pyautogui.PAUSE = 0.1
        pyautogui.FAILSAFE = True
        return pyautogui
    except Exception as exc:
        reason = str(exc)
        hint = (
            'pyautogui is not installed or wrong interpreter is used.'
            if 'No module named' in reason
            else 'pyautogui could not access DISPLAY/X11. Run in a graphical desktop session.'
        )
        print(
            json.dumps(
                {
                    'ok': False,
                    'type': 'import_error',
                    'package': 'pyautogui',
                    'reason': reason,
                    'hint': hint,
                },
                ensure_ascii=False,
            )
        )
        return None


def _run_xdotool(args, error_type: str, hint: str) -> bool:
    """Run xdotool command and normalize failure output."""
    cmd = ['xdotool'] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(
            json.dumps(
                {
                    'ok': False,
                    'type': error_type,
                    'backend': 'xdotool',
                    'reason': (result.stderr or result.stdout or 'xdotool failed').strip(),
                    'hint': hint,
                },
                ensure_ascii=False,
            )
        )
        return False
    return True


# --------------------- Core actions ---------------------

def do_screenshot(args=None) -> None:
    ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    path = os.path.join(BASE_DIR, f'screen_{ts}.png')
    result = subprocess.run(['gnome-screenshot', '-f', path], capture_output=True, text=True)

    if result.returncode != 0:
        print(
            json.dumps(
                {
                    'ok': False,
                    'type': 'screenshot_error',
                    'reason': (result.stderr or result.stdout or 'gnome-screenshot failed').strip(),
                    'hint': 'Run in a graphical desktop session and ensure screenshot permission is granted.',
                },
                ensure_ascii=False,
            )
        )
        return

    print(json.dumps({'ok': True, 'type': 'screenshot', 'path': path}, ensure_ascii=False))


def do_click(args) -> None:
    x, y = map(int, args.position.split(','))
    clicks = 2 if args.double else 1
    xbutton = '3' if args.right else '1'  # xdotool: 1=left, 3=right

    pyautogui = _load_pyautogui()
    error = None

    # Try pyautogui first
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.click(x=x, y=y, button='right' if args.right else 'left', clicks=clicks, interval=0.2)
            print(
                json.dumps(
                    {
                        'ok': True,
                        'type': 'click',
                        'backend': 'pyautogui',
                        'position': [x, y],
                        'button': 'right' if args.right else 'left',
                        'clicks': clicks,
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as exc:
            error = exc

    # Fallback to xdotool
    if not _run_xdotool(
        ['mousemove', x, y],
        'click_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return
    _human_delay()
    if not _run_xdotool(
        ['click', '--repeat', clicks, '--delay', 200, xbutton],
        'click_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'click',
                'backend': 'xdotool',
                'position': [x, y],
                'button': 'right' if args.right else 'left',
                'clicks': clicks,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def do_move(args) -> None:
    x, y = map(int, args.position.split(','))
    pyautogui = _load_pyautogui()
    error = None

    # Prefer pyautogui smooth move
    if pyautogui is not None:
        try:
            _human_delay()
            before = pyautogui.position()
            pyautogui.moveTo(x, y, duration=0.8)
            after = pyautogui.position()
            if before != after:
                print(
                    json.dumps(
                        {
                            'ok': True,
                            'type': 'move',
                            'backend': 'pyautogui',
                            'target': [x, y],
                            'before': list(before),
                            'after': list(after),
                        },
                        ensure_ascii=False,
                    )
                )
                return
        except Exception as exc:
            error = exc

    if not _run_xdotool(
        ['mousemove', x, y],
        'move_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'move',
                'backend': 'xdotool',
                'target': [x, y],
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def do_drag(args) -> None:
    x1, y1 = map(int, args.start.split(','))
    x2, y2 = map(int, args.end.split(','))
    duration = args.duration

    pyautogui = _load_pyautogui()
    error = None

    # Try pyautogui drag first
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.moveTo(x1, y1)
            _human_delay()
            pyautogui.dragTo(x2, y2, duration=duration, button='left')
            print(
                json.dumps(
                    {
                        'ok': True,
                        'type': 'drag',
                        'backend': 'pyautogui',
                        'start': [x1, y1],
                        'end': [x2, y2],
                        'duration': duration,
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as exc:
            error = exc

    # xdotool drag sequence: down -> move -> up
    if not _run_xdotool(
        ['mousemove', x1, y1],
        'drag_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return
    if not _run_xdotool(
        ['mousedown', '1'],
        'drag_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return
    _human_delay()
    if not _run_xdotool(
        ['mousemove', x2, y2],
        'drag_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        _run_xdotool(['mouseup', '1'], 'drag_error', 'Mouse release attempted after drag failure.')
        return
    time.sleep(max(duration, 0.0))
    _run_xdotool(['mouseup', '1'], 'drag_error', 'Run in a graphical desktop session and ensure input-control permission is granted.')

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'drag',
                'backend': 'xdotool',
                'start': [x1, y1],
                'end': [x2, y2],
                'duration': duration,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def do_scroll(args) -> None:
    x, y = map(int, args.position.split(','))
    amount = max(-5000, min(5000, args.amount))

    pyautogui = _load_pyautogui()
    error = None

    # Try pyautogui first
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.moveTo(x, y)
            pyautogui.scroll(amount)
            print(
                json.dumps(
                    {
                        'ok': True,
                        'type': 'scroll',
                        'backend': 'pyautogui',
                        'position': [x, y],
                        'amount': amount,
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as exc:
            error = exc

    # xdotool wheel buttons: 4=up 5=down
    button = '4' if amount > 0 else '5'
    repeat = abs(amount) // 100 or 1

    if not _run_xdotool(
        ['mousemove', x, y],
        'scroll_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return
    if not _run_xdotool(
        ['click', '--repeat', repeat, '--delay', 30, button],
        'scroll_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'scroll',
                'backend': 'xdotool',
                'position': [x, y],
                'amount': amount,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def type_text(args) -> None:
    text = args.text
    pyautogui = _load_pyautogui()
    error = None

    # Try pyautogui first
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.typewrite(text, interval=0.05)
            print(json.dumps({'ok': True, 'type': 'type', 'backend': 'pyautogui', 'text': text}, ensure_ascii=False))
            return
        except Exception as exc:
            error = exc

    if not _run_xdotool(
        ['type', '--delay', 50, text],
        'type_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'type',
                'backend': 'xdotool',
                'text': text,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def do_hotkey(args) -> None:
    mapping = {
        'copy': ('ctrl', 'c'),
        'paste': ('ctrl', 'v'),
        'cut': ('ctrl', 'x'),
        'select_all': ('ctrl', 'a'),
        'undo': ('ctrl', 'z'),
        'redo': ('ctrl', 'y'),
        'address_bar': ('ctrl', 'l'),
        'new_tab': ('ctrl', 't'),
        'close_tab': ('ctrl', 'w'),
        'refresh': ('ctrl', 'r'),
    }
    combo = mapping.get(args.combo)
    if combo is None:
        print(
            json.dumps(
                {
                    'ok': False,
                    'type': 'hotkey_error',
                    'reason': f'Unsupported combo {args.combo}',
                    'hint': 'Supported: copy, paste, cut, select_all, undo, redo, address_bar, new_tab, close_tab, refresh',
                },
                ensure_ascii=False,
            )
        )
        return

    pyautogui = _load_pyautogui()
    error = None

    # Try pyautogui first
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.hotkey(*combo)
            print(json.dumps({'ok': True, 'type': 'hotkey', 'backend': 'pyautogui', 'combo': args.combo}, ensure_ascii=False))
            return
        except Exception as exc:
            error = exc

    if not _run_xdotool(
        ['key', '+'.join(combo)],
        'hotkey_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'hotkey',
                'backend': 'xdotool',
                'combo': args.combo,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def do_press(args) -> None:
    key = args.key.lower()
    repeat = max(1, int(args.repeat))
    delay = max(0, int(args.delay))

    key_map = {
        'enter': 'Return',
        'return': 'Return',
        'esc': 'Escape',
        'escape': 'Escape',
        'tab': 'Tab',
        'space': 'space',
        'backspace': 'BackSpace',
        'delete': 'Delete',
        'up': 'Up',
        'down': 'Down',
        'left': 'Left',
        'right': 'Right',
        'home': 'Home',
        'end': 'End',
        'pageup': 'Page_Up',
        'pagedown': 'Page_Down',
    }
    x_key = key_map.get(key, args.key)

    pyautogui = _load_pyautogui()
    error = None

    if pyautogui is not None and key in key_map:
        try:
            _human_delay()
            for _ in range(repeat):
                pyautogui.press(key)
                if delay > 0:
                    time.sleep(delay / 1000)
            print(
                json.dumps(
                    {
                        'ok': True,
                        'type': 'press',
                        'backend': 'pyautogui',
                        'key': key,
                        'repeat': repeat,
                        'delay': delay,
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as exc:
            error = exc

    if not _run_xdotool(
        ['key', '--repeat', repeat, '--delay', delay, x_key],
        'press_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'press',
                'backend': 'xdotool',
                'key': args.key,
                'repeat': repeat,
                'delay': delay,
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def _focus_window(pattern: str, index: int = 0):
    search = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', pattern], capture_output=True, text=True)
    if search.returncode != 0 or not search.stdout.strip():
        return {
            'ok': False,
            'type': 'focus_error',
            'reason': (search.stderr or search.stdout or 'window not found').strip(),
            'pattern': pattern,
        }

    ids = [line.strip() for line in search.stdout.splitlines() if line.strip()]
    if index >= len(ids):
        return {
            'ok': False,
            'type': 'focus_error',
            'reason': f'index {index} out of range for {len(ids)} windows',
            'pattern': pattern,
            'matches': ids,
        }

    win_id = ids[index]
    activate = subprocess.run(['xdotool', 'windowactivate', '--sync', win_id], capture_output=True, text=True)
    if activate.returncode != 0:
        return {
            'ok': False,
            'type': 'focus_error',
            'reason': (activate.stderr or activate.stdout or 'windowactivate failed').strip(),
            'pattern': pattern,
            'window_id': win_id,
        }

    return {'ok': True, 'type': 'focus', 'pattern': pattern, 'window_id': win_id, 'match_count': len(ids)}


def do_focus(args) -> None:
    print(json.dumps(_focus_window(args.name, max(0, int(args.index))), ensure_ascii=False))


def _get_active_window_info():
    wid = subprocess.run(['xdotool', 'getactivewindow'], capture_output=True, text=True)
    active_window = wid.stdout.strip() if wid.returncode == 0 else ''

    name = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], capture_output=True, text=True)
    active_name = name.stdout.strip() if name.returncode == 0 else ''

    return active_window, active_name


def _window_name_matches(pattern: str, window_name: str) -> bool:
    if not pattern:
        return False
    try:
        return re.search(pattern, window_name) is not None
    except re.error:
        # Fall back to substring matching for invalid regex
        return pattern in window_name


def do_type_guard(args) -> None:
    expected = args.expect_window
    refocus = args.refocus
    settle_ms = max(0, int(args.settle_ms))

    before_window, before_name = _get_active_window_info()
    focused = False
    focus_result = None

    if expected and not _window_name_matches(expected, before_name):
        if refocus:
            focus_result = _focus_window(expected, 0)
            focused = bool(focus_result.get('ok'))
            if not focused:
                print(
                    json.dumps(
                        {
                            'ok': False,
                            'type': 'type_guard_error',
                            'reason': 'refocus failed',
                            'expect_window': expected,
                            'before_window': before_window,
                            'before_window_name': before_name,
                            'focus_result': focus_result,
                        },
                        ensure_ascii=False,
                    )
                )
                return
            if settle_ms > 0:
                time.sleep(settle_ms / 1000)
        else:
            print(
                json.dumps(
                    {
                        'ok': False,
                        'type': 'type_guard_error',
                        'reason': 'active window mismatch',
                        'expect_window': expected,
                        'before_window': before_window,
                        'before_window_name': before_name,
                    },
                    ensure_ascii=False,
                )
            )
            return

    text = args.text
    pyautogui = _load_pyautogui()
    error = None

    # Inline typing to keep output as one JSON object
    if pyautogui is not None:
        try:
            _human_delay()
            pyautogui.typewrite(text, interval=0.05)
            after_window, after_name = _get_active_window_info()
            print(
                json.dumps(
                    {
                        'ok': True,
                        'type': 'type_guard',
                        'backend': 'pyautogui',
                        'text': text,
                        'expect_window': expected,
                        'focused': focused,
                        'focus_result': focus_result,
                        'before_window': before_window,
                        'before_window_name': before_name,
                        'after_window': after_window,
                        'after_window_name': after_name,
                        'window_ok': (not expected) or _window_name_matches(expected, after_name),
                    },
                    ensure_ascii=False,
                )
            )
            return
        except Exception as exc:
            error = exc

    if not _run_xdotool(
        ['type', '--delay', 50, text],
        'type_error',
        'Run in a graphical desktop session and ensure input-control permission is granted.',
    ):
        return

    after_window, after_name = _get_active_window_info()
    print(
        json.dumps(
            {
                'ok': True,
                'type': 'type_guard',
                'backend': 'xdotool',
                'text': text,
                'expect_window': expected,
                'focused': focused,
                'focus_result': focus_result,
                'before_window': before_window,
                'before_window_name': before_name,
                'after_window': after_window,
                'after_window_name': after_name,
                'window_ok': (not expected) or _window_name_matches(expected, after_name),
                'pyautogui_error': str(error) if error else None,
            },
            ensure_ascii=False,
        )
    )


def _get_position_tuple():
    pyautogui = _load_pyautogui()
    if pyautogui is not None:
        try:
            x, y = pyautogui.position()
            return int(x), int(y), 'pyautogui'
        except Exception:
            pass

    probe = subprocess.run(['xdotool', 'getmouselocation', '--shell'], capture_output=True, text=True)
    if probe.returncode == 0:
        data = {}
        for line in probe.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                data[k.strip()] = v.strip()
        if 'X' in data and 'Y' in data:
            return int(data['X']), int(data['Y']), 'xdotool'

    return None


def do_click_retry(args) -> None:
    x, y = map(int, args.position.split(','))
    radius = max(0, int(args.radius))
    step = max(1, int(args.step))
    retries = max(1, int(args.retries))
    settle_ms = max(0, int(args.settle_ms))

    baseline_window, baseline_name = _get_active_window_info()

    offsets = [(0, 0)]
    for i in range(1, retries):
        ring = ((i + 1) // 2) * step
        if ring > radius:
            break
        offsets.extend([(ring, 0), (-ring, 0), (0, ring), (0, -ring)])

    tried = []
    matched = False
    stop_reason = 'exhausted'

    for dx, dy in offsets:
        tx, ty = x + dx, y + dy
        _human_delay(0.08, 0.18)

        do_move(argparse.Namespace(position=f'{tx},{ty}'))
        do_click(argparse.Namespace(position=f'{tx},{ty}', right=args.right, double=args.double))

        if settle_ms > 0:
            time.sleep(settle_ms / 1000)

        active_window, active_name = _get_active_window_info()
        is_match = False

        if args.expect_window:
            is_match = _window_name_matches(args.expect_window, active_name)
            if is_match:
                matched = True
                stop_reason = 'expect_window_matched'
        elif args.stop_on_same_window and baseline_window:
            is_match = active_window == baseline_window
            if is_match:
                matched = True
                stop_reason = 'same_window'

        tried.append(
            {
                'position': [tx, ty],
                'active_window': active_window,
                'active_window_name': active_name,
                'matched': is_match,
            }
        )
        if matched:
            break

    print(
        json.dumps(
            {
                'ok': True,
                'type': 'click_retry',
                'base': [x, y],
                'radius': radius,
                'step': step,
                'attempts': len(tried),
                'tried': tried,
                'baseline_window': baseline_window,
                'baseline_window_name': baseline_name,
                'expect_window': args.expect_window,
                'matched': matched,
                'stop_reason': stop_reason,
            },
            ensure_ascii=False,
        )
    )


def do_focus_probe(args) -> None:
    active_window, active_name = _get_active_window_info()
    pos = _get_position_tuple()
    if pos is None:
        print(
            json.dumps(
                {
                    'ok': False,
                    'type': 'focus_probe_error',
                    'reason': 'Could not read mouse position',
                    'active_window': active_window,
                    'active_window_name': active_name,
                },
                ensure_ascii=False,
            )
        )
        return

    x, y, source = pos
    print(
        json.dumps(
            {
                'ok': True,
                'type': 'focus_probe',
                'active_window': active_window,
                'active_window_name': active_name,
                'mouse_position': [x, y],
                'position_source': source,
            },
            ensure_ascii=False,
        )
    )


def do_position(args) -> None:
    """Helper command to get current pointer coordinates for UI calibration."""
    pos = _get_position_tuple()
    if pos is None:
        print(json.dumps({'ok': False, 'type': 'position_error', 'reason': 'Could not read mouse position'}, ensure_ascii=False))
        return
    x, y, source = pos
    print(json.dumps({'ok': True, 'type': 'position', 'position': [x, y], 'source': source}, ensure_ascii=False))


# --------------------- CLI entry ---------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Screen control helper for OpenClaw (screenshot, mouse, keyboard).'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_ss = subparsers.add_parser('screenshot', help='Take a full-screen screenshot and save to file')
    p_ss.set_defaults(func=do_screenshot)

    p_click = subparsers.add_parser('click', help='Mouse click')
    p_click.add_argument('--position', required=True, help='Format: x,y')
    p_click.add_argument('--right', action='store_true', help='Right click')
    p_click.add_argument('--double', action='store_true', help='Double click')
    p_click.set_defaults(func=do_click)

    p_move = subparsers.add_parser('move', help='Move mouse to target coordinate')
    p_move.add_argument('--position', required=True, help='Format: x,y')
    p_move.set_defaults(func=do_move)

    p_drag = subparsers.add_parser('drag', help='Drag between coordinates')
    p_drag.add_argument('--start', required=True, help='Start coordinate: x,y')
    p_drag.add_argument('--end', required=True, help='End coordinate: x,y')
    p_drag.add_argument('--duration', type=float, default=0.5, help='Drag duration in seconds')
    p_drag.set_defaults(func=do_drag)

    p_scroll = subparsers.add_parser('scroll', help='Scroll at coordinate')
    p_scroll.add_argument('--position', required=True, help='Focus coordinate: x,y')
    p_scroll.add_argument('--amount', type=int, required=True, help='Scroll amount; positive up, negative down')
    p_scroll.set_defaults(func=do_scroll)

    p_type = subparsers.add_parser('type', help='Type text')
    p_type.add_argument('--text', required=True, help='Text to type')
    p_type.set_defaults(func=type_text)

    p_type_guard = subparsers.add_parser('type-guard', help='Validate/refocus window before typing')
    p_type_guard.add_argument('--text', required=True, help='Text to type')
    p_type_guard.add_argument('--expect-window', default='', help='Expected active-window regex')
    p_type_guard.add_argument('--refocus', action='store_true', help='Try to focus expected window first')
    p_type_guard.add_argument('--settle-ms', type=int, default=120, help='Wait after refocus (milliseconds)')
    p_type_guard.set_defaults(func=do_type_guard)

    p_hotkey = subparsers.add_parser('hotkey', help='Run common shortcut combo')
    p_hotkey.add_argument(
        '--combo',
        required=True,
        choices=['copy', 'paste', 'cut', 'select_all', 'undo', 'redo', 'address_bar', 'new_tab', 'close_tab', 'refresh'],
        help='Shortcut action',
    )
    p_hotkey.set_defaults(func=do_hotkey)

    p_press = subparsers.add_parser('press', help='Press one key (enter/esc/tab/etc.)')
    p_press.add_argument('--key', required=True, help='Key name such as enter/esc/tab')
    p_press.add_argument('--repeat', type=int, default=1, help='Repeat count (default 1)')
    p_press.add_argument('--delay', type=int, default=0, help='Delay between repeats (ms)')
    p_press.set_defaults(func=do_press)

    p_focus = subparsers.add_parser('focus', help='Activate a window by name regex (xdotool)')
    p_focus.add_argument('--name', required=True, help='Window name regex (for example: Firefox|Chrome)')
    p_focus.add_argument('--index', type=int, default=0, help='Index when multiple windows are matched')
    p_focus.set_defaults(func=do_focus)

    p_probe = subparsers.add_parser('focus-probe', help='Report active window and mouse position')
    p_probe.set_defaults(func=do_focus_probe)

    p_click_retry = subparsers.add_parser('click-retry', help='Retry clicks around a target point')
    p_click_retry.add_argument('--position', required=True, help='Base coordinate: x,y')
    p_click_retry.add_argument('--radius', type=int, default=30, help='Retry radius in pixels')
    p_click_retry.add_argument('--step', type=int, default=8, help='Offset step in pixels')
    p_click_retry.add_argument('--retries', type=int, default=5, help='Maximum retry count')
    p_click_retry.add_argument('--right', action='store_true', help='Right click')
    p_click_retry.add_argument('--double', action='store_true', help='Double click')
    p_click_retry.add_argument('--expect-window', default='', help='Stop when expected active-window regex matches')
    p_click_retry.add_argument('--settle-ms', type=int, default=120, help='Wait after each click (milliseconds)')
    p_click_retry.add_argument('--no-stop-on-same-window', dest='stop_on_same_window', action='store_false', help='Do not stop on baseline active window')
    p_click_retry.set_defaults(func=do_click_retry, stop_on_same_window=True)

    p_pos = subparsers.add_parser('position', help='Get current mouse coordinate')
    p_pos.set_defaults(func=do_position)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
