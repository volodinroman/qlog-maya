import json
import os

import maya.OpenMayaUI as omui
import maya.api.OpenMayaUI as omui_api
from pyside_wrapper import QtWidgets, wrapInstance


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
