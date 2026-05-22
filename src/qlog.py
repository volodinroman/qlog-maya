import importlib

import maya.OpenMaya as om
import maya.cmds as cmds
from pyside_wrapper import QtWidgets, QtCore, QtGui
import utils

utils = importlib.reload(utils)
CONFIG = utils.load_config()

class TransparentHistoryText(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TransparentHistoryText, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

        self.messages = []
        self.max_lines = CONFIG["history_limit"]
        self.scroll_offset = 0
        self.font = self.create_font()

    def create_font(self):
        font_size = CONFIG["font_size"]
        font_file = CONFIG.get("font_file")

        if font_file:
            font_path = utils.get_asset_path(font_file)
            font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
            font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                return QtGui.QFont(font_families[0], font_size)

        font = QtGui.QFont(CONFIG["font_family"], font_size)
        if not QtGui.QFontInfo(font).exactMatch():
            font = QtGui.QFont(CONFIG["font_fallback_family"], font_size)
        return font

    def append_colored_text(self, text, color):
        for line in text.splitlines():
            line = line.strip()
            if line:
                self.messages.append((line, QtGui.QColor(color)))

        if len(self.messages) > self.max_lines:
            self.messages = self.messages[-self.max_lines:]
        self.scroll_offset = 0
        self.update()

    def scroll_lines(self, delta):
        metrics = QtGui.QFontMetrics(self.font)
        visible_count = min(
            CONFIG["visible_lines"],
            max(1, self.height() // metrics.lineSpacing()),
        )
        max_offset = max(0, len(self.messages) - visible_count)
        self.scroll_offset = max(0, min(max_offset, self.scroll_offset + delta))
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setOpacity(max(0.0, min(1.0, CONFIG["text_opacity"])))
        painter.setFont(self.font)

        metrics = QtGui.QFontMetrics(self.font)
        line_height = metrics.lineSpacing()
        max_visible_lines = min(CONFIG["visible_lines"], max(1, self.height() // line_height))
        end_index = len(self.messages) - self.scroll_offset
        start_index = max(0, end_index - max_visible_lines)
        visible_messages = self.messages[start_index:end_index]

        x = 4
        y = metrics.ascent() + 2
        shadow_color = QtGui.QColor(0, 0, 0, 0)

        for text, color in visible_messages:
            elided = metrics.elidedText(text, QtCore.Qt.ElideRight, max(1, self.width() - 8))
            painter.setPen(shadow_color)
            painter.drawText(x + 1, y + 1, elided)
            painter.setPen(color)
            painter.drawText(x, y, elided)
            y += line_height

        painter.end()


class MayaHistoryOverlay(QtWidgets.QWidget):
    message_received = QtCore.Signal(str, int)

    def __init__(self):
        QtWidgets.QWidget.__init__(self, utils.get_maya_main_window())
        self.setObjectName(CONFIG["object_name"])

        self.margin_left = CONFIG["margin_left"]
        self.margin_top = CONFIG["margin_top"]
        self.callback_id = None
        self._drag_offset = None

        self.build_ui()
        self.connect_signals()
        self.register_callback()

    def build_ui(self):
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(False)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.NoDropShadowWindowHint
        )
        self.resize(CONFIG["width"], CONFIG["height"])
        self.setCursor(QtCore.Qt.SizeAllCursor)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)
        
        self.text_widget = TransparentHistoryText(self)
        self.main_layout.addWidget(self.text_widget)

    def connect_signals(self):
        self.message_received.connect(self.append_message)

    def position_at_viewport_top_left(self):
        viewport_x, viewport_y = utils.get_active_viewport_screen_position()
        self.move(int(viewport_x) + self.margin_left, int(viewport_y) + self.margin_top)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*CONFIG["background_color"])))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), CONFIG["border_radius"], CONFIG["border_radius"])
        painter.end()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            self.text_widget.scroll_lines(1 if delta > 0 else -1)
            event.accept()
            return
        QtWidgets.QWidget.wheelEvent(self, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        QtWidgets.QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        QtWidgets.QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
            return
        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def leaveEvent(self, event):
        if not QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
            self._drag_offset = None
        QtWidgets.QWidget.leaveEvent(self, event)
        
    def register_callback(self):
        try:
            self.callback_id = om.MCommandMessage.addCommandOutputCallback(self._maya_output_callback, None)
        except Exception as e:
            cmds.warning("Не удалось зарегистрировать HUD логгер: {}".format(e))
            
    def remove_callback(self):
        if self.callback_id is not None:
            try:
                om.MMessage.removeCallback(self.callback_id)
            except Exception:
                pass
            self.callback_id = None
            
    def _maya_output_callback(self, *args):
        if len(args) >= 2:
            self.message_received.emit(args[0], args[1])
        
    def append_message(self, message, message_type):
        cleaned_msg = message.strip()
        if not cleaned_msg:
            return
            
        color = QtGui.QColor(CONFIG["text_color"])
        if message_type == om.MCommandMessage.kWarning:
            color = "#ffcc00"
        elif message_type == om.MCommandMessage.kError:
            color = "#843333"
        elif message_type == om.MCommandMessage.kResult:
            color = "#479047"
            
        self.text_widget.append_colored_text(cleaned_msg, color)

    def closeEvent(self, event):
        self.remove_callback()
        QtWidgets.QWidget.closeEvent(self, event)


def run():
    existing_overlay = utils.find_existing_widget(CONFIG["object_name"])
    if existing_overlay is not None:
        existing_overlay.close()
        existing_overlay.deleteLater()
        return None

    overlay = MayaHistoryOverlay()
    overlay.show()
    QtWidgets.QApplication.processEvents()
    overlay.position_at_viewport_top_left()
    overlay.raise_()
    return overlay
