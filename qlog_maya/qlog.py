import maya.OpenMaya as om
import maya.cmds as cmds
from qlog_maya.pyside_wrapper import QtWidgets, QtCore, QtGui
import qlog_maya.utils as utils

CONFIG = utils.load_config()
MESSAGE_TYPE_COLORS = {
    om.MCommandMessage.kWarning: "#ffcc00",
    om.MCommandMessage.kError: "#843333",
    om.MCommandMessage.kResult: "#479047",
}


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
        max_offset = max(0, len(self.get_visible_text_lines(metrics)) - visible_count)
        self.scroll_offset = max(0, min(max_offset, self.scroll_offset + delta))
        self.update()

    def text_width(self, metrics, text):
        if hasattr(metrics, "horizontalAdvance"):
            return metrics.horizontalAdvance(text)
        return metrics.width(text)

    def get_visible_text_lines(self, metrics):
        max_width = max(1, self.width() - 8)
        lines = []

        for text, color in self.messages:
            if CONFIG.get("word_wrap", False):
                for wrapped_line in self.wrap_text(text, metrics, max_width):
                    lines.append((wrapped_line, color))
            else:
                line = metrics.elidedText(text, QtCore.Qt.ElideRight, max_width)
                lines.append((line, color))

        return lines

    def wrap_text(self, text, metrics, max_width):
        wrapped_lines = []
        current_line = ""

        for word in text.split(" "):
            candidate = word if not current_line else current_line + " " + word
            if self.text_width(metrics, candidate) <= max_width:
                current_line = candidate
                continue

            if current_line:
                wrapped_lines.append(current_line)
            current_line = ""

            if self.text_width(metrics, word) <= max_width:
                current_line = word
            else:
                wrapped_lines.extend(self.wrap_long_word(word, metrics, max_width))

        if current_line:
            wrapped_lines.append(current_line)

        return wrapped_lines or [text]

    def wrap_long_word(self, word, metrics, max_width):
        lines = []
        current_line = ""

        for char in word:
            candidate = current_line + char
            if current_line and self.text_width(metrics, candidate) > max_width:
                lines.append(current_line)
                current_line = char
            else:
                current_line = candidate

        if current_line:
            lines.append(current_line)

        return lines

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setOpacity(max(0.0, min(1.0, CONFIG["text_opacity"])))
        painter.setFont(self.font)

        metrics = QtGui.QFontMetrics(self.font)
        line_height = metrics.lineSpacing()
        max_visible_lines = min(CONFIG["visible_lines"], max(1, self.height() // line_height))
        text_lines = self.get_visible_text_lines(metrics)
        end_index = len(text_lines) - self.scroll_offset
        start_index = max(0, end_index - max_visible_lines)
        visible_messages = text_lines[start_index:end_index]

        x = 4
        y = metrics.ascent() + 2

        for text, color in visible_messages:
            painter.setPen(color)
            painter.drawText(x, y, text)
            y += line_height

        painter.end()


class MayaHistoryOverlay(QtWidgets.QWidget):
    message_received = QtCore.Signal(str, int)

    def __init__(self):
        QtWidgets.QWidget.__init__(self, utils.get_maya_main_window())
        self.setObjectName(CONFIG["object_name"])

        self.callback_id = None
        self._drag_offset = None

        self.build_ui()
        self.message_received.connect(self.append_message)
        self.populate_existing_history()
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

    def populate_existing_history(self):
        history_lines = utils.get_script_editor_history_lines(CONFIG["history_limit"])
        for line in history_lines:
            self.text_widget.append_colored_text(line, self.get_message_color_from_text(line))

    def position_at_viewport_top_left(self):
        viewport_x, viewport_y = utils.get_active_viewport_screen_position()
        self.move(
            int(viewport_x) + CONFIG["margin_left"],
            int(viewport_y) + CONFIG["margin_top"],
        )

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
            message, message_type = args[:2]
            self.message_received.emit(message, message_type)
        
    def append_message(self, message, message_type):
        cleaned_msg = message.strip()
        if not cleaned_msg:
            return

        color = MESSAGE_TYPE_COLORS.get(message_type, CONFIG["text_color"])
        self.text_widget.append_colored_text(cleaned_msg, color)

    def get_message_color_from_text(self, text):
        lower_text = text.lower()
        if "warning:" in lower_text:
            return "#ffcc00"
        if "error:" in lower_text or "traceback" in lower_text:
            return "#843333"
        if text.startswith("// Result:") or text.startswith("# Result:"):
            return "#479047"
        return CONFIG["text_color"]

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
