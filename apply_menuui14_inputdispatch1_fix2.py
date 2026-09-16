#!/usr/bin/env python3
from pathlib import Path
import re

base = Path(__file__).with_name("apply_menuui14_inputdispatch1.py")
if not base.is_file():
    raise SystemExit("MENUUI14 FIX2: base patcher missing: " + str(base))

text = base.read_text(encoding="utf-8")
pattern = re.compile(
    r'# 5d\) If touch is rejected after clamp/hit test, state it explicitly\.\n'
    r'old = .*?'
    r'replace_once\("window", old, new, "touch outside-screen branch"\)\n',
    re.S,
)
if len(pattern.findall(text)) != 1:
    raise SystemExit(f"MENUUI14 FIX2: base touch-anchor block count={len(pattern.findall(text))}")

q = "'" * 3
lines = [
    '# 5d) If touch is rejected after clamp/hit test, state it explicitly.',
    '# FIX2: scope the generic shipped/break anchor to the outer touch switch block.',
    'old = ' + q + '                shipped = true;',
    '            }',
    '',
    '            break;',
    '        }',
    q,
    'new = ' + q + '                shipped = true;',
    '            } else {',
    '                LOG_WARN(SERVICE_WINDOW,',
    '                    "SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_SCREEN_DROP: host=({}, {}) action={} pointer={} reason=outside_screen_rect",',
    '                    input_event.mouse_.pos_x_, input_event.mouse_.pos_y_,',
    '                    static_cast<int>(input_event.mouse_.action_), input_event.mouse_.mouse_id);',
    '            }',
    '',
    '            break;',
    '        }',
    q,
    'window_text = src["window"]',
    'touch_begin = window_text.index("        case drivers::input_event_type::touch: {")',
    'outer_default = re.search(',
    '    r\'\\n        default:\\s*\\n\\s*LOG_ERROR\\(SERVICE_WINDOW, "Unknown driver event type \\{\\}"\',',
    '    window_text[touch_begin:],',
    ')',
    'if not outer_default:',
    '    raise SystemExit("MENUUI14 FIX2: outer driver-event default anchor not found")',
    'touch_end = touch_begin + outer_default.start()',
    'touch_block = window_text[touch_begin:touch_end]',
    'count = touch_block.count(old)',
    'if count != 1:',
    '    raise SystemExit(f"MENUUI14 FIX2: touch outside-screen branch count={count}")',
    'touch_block = touch_block.replace(old, new, 1)',
    'src["window"] = window_text[:touch_begin] + touch_block + window_text[touch_end:]',
    '',
]
replacement = "\n".join(lines)
patched = pattern.sub(lambda _: replacement, text, count=1)

# The base postcondition assumed every diagnostic marker is unique. Three markers
# intentionally occur in two mutually exclusive branches: INPUT_DRIVER (no winserv
# vs normal), INPUT_QUEUE (server unloaded vs normal), and INPUT_GET (touch vs
# non-touch). Correct only the validation counts; this does not change emulator behavior.
post_old = '''for name, markers in expected.items():
    for marker in markers:
        if src[name].count(marker) != 1:
            raise SystemExit(f"MENUUI14: marker postcondition failed {name}: {marker}")
'''
post_new = '''expected_counts = {
    ("thread", "MENUUI14 INPUT_DRIVER:"): 2,
    ("window", "MENUUI14 INPUT_QUEUE:"): 2,
    ("window", "MENUUI14 INPUT_GET:"): 2,
}
for name, markers in expected.items():
    for marker in markers:
        got = src[name].count(marker)
        want = expected_counts.get((name, marker), 1)
        if got != want:
            raise SystemExit(
                f"MENUUI14: marker postcondition failed {name}: {marker} count={got} expected={want}"
            )
'''
if patched.count(post_old) != 1:
    raise SystemExit(f"MENUUI14 FIX2: base postcondition block count={patched.count(post_old)}")
patched = patched.replace(post_old, post_new, 1)

print("MENUUI14 INPUTDISPATCH1 FIX2: scoped touch-case anchor + marker-count gates applied")
code = compile(patched, str(base) + "<FIX2>", "exec")
g = {"__name__": "__main__", "__file__": str(base), "__package__": None}
exec(code, g, g)
