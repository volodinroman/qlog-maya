# qlog-maya

`qlog-maya` is a small Maya viewport HUD for Script Editor output.

It shows Maya command output in a transparent overlay near the active viewport, so warnings, errors, results, and info messages can be seen without keeping Script Editor open.

## Features

- Displays Maya command output in a viewport overlay.
- Supports info, warning, error, and result colors.
- Optional word wrap for long lines.
- Optional message type filters.
- Click a visible line to copy the full original message.
- Optional copy feedback highlight.
- Optional fading for older visible messages.
- Basic startup history loading when Maya exposes Script Editor history.

## Requirements

- Autodesk Maya with Python.
- PySide2 or PySide6.

The package includes `qlog_maya/pyside_wrapper.py`, which tries PySide6 first and falls back to PySide2.

## Installation

Clone or download this repository somewhere on disk.

Example:

```text
E:\Dev\GitHub\qlog-maya
```

The Python package folder must stay inside the project root:

```text
qlog-maya/
  qlog_maya/
    __init__.py
    qlog.py
    utils.py
    pyside_wrapper.py
    config.json
    assets/
```

## Run

Create a Python shelf button in Maya and use this command. First time you run it - it will show the qlog UI, second time click - it will close it (qlog UI doesn't have a close button)

Change `PROJECT_ROOT` to your local repository path.

```python
import os
import sys

PROJECT_ROOT = r"E:\Dev\GitHub\qlog-maya"

project_root = os.path.normcase(os.path.normpath(PROJECT_ROOT))
sys_paths = [os.path.normcase(os.path.normpath(path)) for path in sys.path]

if project_root not in sys_paths:
    sys.path.insert(0, PROJECT_ROOT)

import qlog_maya

qlog_maya_ui = qlog_maya.run()
```

Running the command again closes the existing overlay.

## Development

Use this shelf command while editing the source code. It removes loaded `qlog_maya` modules before importing the package again.

```python
import os
import sys
import importlib

PROJECT_ROOT = r"E:\Dev\GitHub\qlog-maya"
PACKAGE_NAME = "qlog_maya"

project_root = os.path.normcase(os.path.normpath(PROJECT_ROOT))
sys_paths = [os.path.normcase(os.path.normpath(path)) for path in sys.path]

if project_root not in sys_paths:
    sys.path.insert(0, PROJECT_ROOT)

for module_name in list(sys.modules.keys()):
    if module_name == PACKAGE_NAME or module_name.startswith(PACKAGE_NAME + "."):
        del sys.modules[module_name]

package = importlib.import_module(PACKAGE_NAME)

qlog_maya_ui = package.run()
```

## Configuration

Settings are stored in `qlog_maya/config.json`.

Common options:

| Option | Description |
| --- | --- |
| `width` / `height` | Overlay size in pixels. |
| `margin_left` / `margin_top` | Offset from the active viewport top-left corner. |
| `visible_lines` | Maximum visible text lines. |
| `history_limit` | Maximum stored source messages. |
| `text_opacity` | Overall text opacity. |
| `background_color` | Overlay background color as `[r, g, b, a]`. |
| `word_wrap` | Wrap long messages instead of truncating them. |
| `click_to_copy` | Copy the clicked message to clipboard. |
| `copy_feedback` | Highlight copied message briefly. |
| `copy_feedback_duration_ms` | Copy highlight duration in milliseconds. |
| `copy_feedback_color` | Copy highlight color as `[r, g, b, a]`. |
| `message_fading` | Fade older visible lines. |
| `faded_text_opacity` | Minimum opacity used by fading. |
| `message_filters` | Show or hide `info`, `warning`, `error`, and `result` messages. |
| `message_colors` | Text colors for each message type. |
| `font_file` | Optional font file from `qlog_maya/assets`. |
| `font_size` | Text font size. |

Example filter configuration:

```json
"message_filters": {
    "info": false,
    "warning": true,
    "error": true,
    "result": false
}
```

## Usage Notes

- Drag the overlay with the left mouse button.
- Scroll over the overlay to browse older visible lines.
- Short-click a line to copy the full message.
- If `word_wrap` is enabled, clicking any wrapped part copies the original full message.
- Startup history is only available when Maya exposes Script Editor history. Future output is captured through Maya command output callbacks.

## License

See `LICENSE`.
