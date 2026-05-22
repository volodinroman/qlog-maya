from typing import TYPE_CHECKING

def _import_qt():
    try:
        from PySide6 import QtCore, QtGui, QtSvg, QtWidgets
        from shiboken6 import wrapInstance

        return QtCore, QtGui, QtSvg, QtWidgets, wrapInstance
    except ImportError:
        from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
        from shiboken2 import wrapInstance

        return QtCore, QtGui, QtSvg, QtWidgets, wrapInstance


if TYPE_CHECKING:
    from PySide2 import QtCore, QtGui, QtSvg, QtWidgets
    from shiboken2 import wrapInstance
else:
    QtCore, QtGui, QtSvg, QtWidgets, wrapInstance = _import_qt()
