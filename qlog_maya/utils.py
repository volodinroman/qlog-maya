import json
import os

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.api.OpenMayaUI as omui_api
from qlog_maya.pyside_wrapper import QtWidgets, wrapInstance


def load_config(file_path=None):
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "config.json")

    with open(file_path, "r") as config_file:
        return json.load(config_file)


def wrap_qwidget(ptr):
    if not ptr:
        return None
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def get_maya_main_window():
    return wrap_qwidget(omui.MQtUtil.mainWindow())


def get_active_viewport_screen_position():
    view = omui_api.M3dView.active3dView()
    viewport_x, viewport_y = view.getScreenPosition()
    return int(viewport_x), int(viewport_y)


def get_asset_path(file_name):
    if not file_name:
        return None
    return os.path.join(os.path.dirname(__file__), "assets", file_name)


def get_script_editor_history_lines(limit):
    text = ""
    try:
        reporters = cmds.lsUI(type="cmdScrollFieldReporter") or []
    except Exception:
        reporters = []

    texts = []
    for reporter in reporters:
        try:
            reporter_text = cmds.cmdScrollFieldReporter(reporter, query=True, text=True)
        except Exception:
            continue
        if reporter_text:
            texts.append(reporter_text)

    if texts:
        text = max(texts, key=len)

    if not text:
        try:
            history_file = cmds.scriptEditorInfo(query=True, historyFilename=True)
        except Exception:
            history_file = None

        if history_file and os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8", errors="replace") as file_stream:
                    text = file_stream.read()
            except Exception:
                text = ""

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return lines[-limit:]


def is_live_widget(widget, object_name):
    if widget is None:
        return False

    try:
        return widget.objectName() == object_name and widget.isVisible()
    except RuntimeError:
        return False


def find_existing_widget(object_name):
    try:
        widget = wrap_qwidget(omui.MQtUtil.findControl(object_name))
        if is_live_widget(widget, object_name):
            return widget
    except Exception:
        pass

    app = QtWidgets.QApplication.instance()
    if app is None:
        return None

    for widget in app.topLevelWidgets():
        if is_live_widget(widget, object_name):
            return widget

    return None
