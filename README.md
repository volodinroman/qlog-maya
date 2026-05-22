# qlog-maya


## Run 

```python
import sys

PROJECT_ROOT = r"E:\Dev\GitHub\qlog-maya"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import qlog_maya

qlog_maya_ui = qlog_maya.run()
```


## Development

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