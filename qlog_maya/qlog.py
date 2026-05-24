import maya.OpenMaya as om
import maya.cmds as cmds
from qlog_maya.pyside_wrapper import QtWidgets, QtCore, QtGui
import qlog_maya.utils as utils

CONFIG = utils.load_config()
MESSAGE_TYPE_NAMES = {
    om.MCommandMessage.kWarning: "warning",
    om.MCommandMessage.kError: "error",
    om.MCommandMessage.kResult: "result",
}


class TransparentHistoryTextUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(TransparentHistoryTextUI, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

        self.messages = []
        self.max_lines = CONFIG["history_limit"]
        self.scroll_offset = 0
        self.copied_text = None
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

    def append_colored_text(self, text, color, message_type="info"):
        for line in text.splitlines():
            line = line.strip()
            if line:
                self.messages.append((line, QtGui.QColor(color), message_type))

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

        for text, color, message_type in self.messages:
            if not self.is_message_type_visible(message_type):
                continue

            if CONFIG.get("word_wrap", False):
                # Keep the original text with each wrapped line so click-to-copy
                # copies the full message, not only the clicked visual line.
                for wrapped_line in self.wrap_text(text, metrics, max_width):
                    lines.append((wrapped_line, color, message_type, text))
            else:
                line = metrics.elidedText(text, QtCore.Qt.ElideRight, max_width)
                lines.append((line, color, message_type, text))

        return lines

    def is_message_type_visible(self, message_type):
        filters = CONFIG.get("message_filters", {})
        return filters.get(message_type, True)

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
        # Maya output often contains paths and traceback chunks without spaces.
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

    def get_painted_text_lines(self, metrics):
        line_height = metrics.lineSpacing()
        max_visible_lines = min(CONFIG["visible_lines"], max(1, self.height() // line_height))
        text_lines = self.get_visible_text_lines(metrics)
        end_index = len(text_lines) - self.scroll_offset
        start_index = max(0, end_index - max_visible_lines)
        return text_lines[start_index:end_index]

    def copy_line_at(self, pos):
        metrics = QtGui.QFontMetrics(self.font)
        line_index = (pos.y() - 2) // metrics.lineSpacing()
        visible_lines = self.get_painted_text_lines(metrics)

        if line_index < 0 or line_index >= len(visible_lines):
            return False

        source_text = visible_lines[int(line_index)][3]
        QtWidgets.QApplication.clipboard().setText(source_text)
        self.show_copy_feedback(source_text)
        return True

    def show_copy_feedback(self, text):
        if not CONFIG.get("copy_feedback", True):
            return

        self.copied_text = text
        self.update()
        QtCore.QTimer.singleShot(CONFIG.get("copy_feedback_duration_ms", 450), self.clear_copy_feedback)

    def clear_copy_feedback(self):
        if self.copied_text is None:
            return

        self.copied_text = None
        self.update()

    def get_faded_color(self, color, index, line_count):
        faded_opacity = max(0.0, min(1.0, CONFIG.get("faded_text_opacity", 0.35)))
        if not CONFIG.get("message_fading", False) or line_count <= 1:
            opacity = 1.0
        else:
            opacity = faded_opacity + ((1.0 - faded_opacity) * (float(index) / (line_count - 1)))

        faded_color = QtGui.QColor(color)
        faded_color.setAlphaF(opacity)
        return faded_color

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setOpacity(max(0.0, min(1.0, CONFIG["text_opacity"])))
        painter.setFont(self.font)

        metrics = QtGui.QFontMetrics(self.font)
        line_height = metrics.lineSpacing()
        visible_messages = self.get_painted_text_lines(metrics)

        x = 4
        y = metrics.ascent() + 2

        for index, (text, color, _message_type, source_text) in enumerate(visible_messages):
            if source_text == self.copied_text:
                feedback_rect = QtCore.QRect(
                    0,
                    y - metrics.ascent() - 1,
                    self.width(),
                    line_height,
                )
                painter.fillRect(feedback_rect, QtGui.QColor(*CONFIG["copy_feedback_color"]))

            painter.setPen(self.get_faded_color(color, index, len(visible_messages)))
            painter.drawText(x, y, text)
            y += line_height

        painter.end()


class MayaHistoryOverlayUI(QtWidgets.QWidget):
    message_received = QtCore.Signal(str, int)

    def __init__(self):
        QtWidgets.QWidget.__init__(self, utils.get_maya_main_window())
        self.setObjectName(CONFIG["object_name"])

        self.callback_id = None
        self._drag_offset = None
        self._press_pos = None

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

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        self.text_widget = TransparentHistoryTextUI(self)
        main_layout.addWidget(self.text_widget)

    def populate_existing_history(self):
        history_lines = utils.get_script_editor_history_lines(CONFIG["history_limit"])
        for line in history_lines:
            message_type = self.get_message_type_from_text(line)
            self.text_widget.append_colored_text(line, self.get_message_color(message_type), message_type)

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
            self._press_pos = event.globalPos()
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
            # A small mouse move means "copy"; a real move means "drag window".
            if self.is_click(event) and CONFIG.get("click_to_copy", False):
                self.copy_line_at(event.pos())
            self._drag_offset = None
            self._press_pos = None
            event.accept()
            return
        QtWidgets.QWidget.mouseReleaseEvent(self, event)

    def leaveEvent(self, event):
        if not QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
            self._drag_offset = None
        QtWidgets.QWidget.leaveEvent(self, event)
        
    def register_callback(self):
        try:
            # Maya may emit command output outside normal Qt input handling.
            # The signal keeps widget updates on the Qt side.
            self.callback_id = om.MCommandMessage.addCommandOutputCallback(self._maya_output_callback, None)
        except Exception as e:
            cmds.warning("Failed to register HUD logger: {}".format(e))
            
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

        message_type_name = MESSAGE_TYPE_NAMES.get(message_type, "info")
        self.text_widget.append_colored_text(
            cleaned_msg,
            self.get_message_color(message_type_name),
            message_type_name,
        )

    def get_message_type_from_text(self, text):
        lower_text = text.lower()
        if "warning:" in lower_text:
            return "warning"
        if "error:" in lower_text or "traceback" in lower_text:
            return "error"
        if text.startswith("// Result:") or text.startswith("# Result:"):
            return "result"
        return "info"

    def get_message_color(self, message_type):
        return CONFIG.get("message_colors", {}).get(message_type, CONFIG["text_color"])

    def is_click(self, event):
        if self._press_pos is None:
            return False
        return (event.globalPos() - self._press_pos).manhattanLength() <= 3

    def copy_line_at(self, pos):
        text_pos = self.text_widget.mapFrom(self, pos)
        self.text_widget.copy_line_at(text_pos)

    def closeEvent(self, event):
        self.remove_callback()
        QtWidgets.QWidget.closeEvent(self, event)


def run():
    existing_overlay = utils.find_existing_widget(CONFIG["object_name"])
    if existing_overlay is not None:
        existing_overlay.close()
        existing_overlay.deleteLater()
        return None

    overlay = MayaHistoryOverlayUI()
    overlay.show()
    QtWidgets.QApplication.processEvents()
    overlay.position_at_viewport_top_left()
    overlay.raise_()
    return overlay
