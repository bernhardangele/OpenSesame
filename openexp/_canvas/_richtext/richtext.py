# coding=utf-8

"""
This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public Licensepass
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import sys
from openexp import resources
from libopensesame.py3compat import *
from libopensesame import misc
from libopensesame.oslogging import oslogger
import warnings
from openexp._canvas._element.element import Element
from qtpy.QtWidgets import (
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QApplication
)
from qtpy.QtGui import QPixmap, QPainter, QColor, QFont, QFontDatabase, QImage
from qtpy.QtCore import Qt, QCoreApplication
from PIL import Image

FONTS = [
    'sans',
    'serif',
    'mono',
    'arabic',
    'chinese-japanese-korean',
    'hindi',
    'hebrew'
]
font_database = None
font_substitutions = []
pyqt_initialized = False
# Default half-canvas width used when no max_width is given to text_rect().
# This mirrors the calculation in RichText._to_qgraphicstextitem, which uses
# canvas.width // 2 (typically 1024 // 2 = 512) as the base max_width.
DEFAULT_HALF_CANVAS_WIDTH = 512


def _ensure_pyqt_initialized():
    """Initializes Qt and registers bundled fonts if not already done.
    This is a module-level helper shared by RichText and the standalone
    text_rect() function, so that text rendering works without a Canvas or
    experiment instance.
    """
    global pyqt_initialized, app, font_database

    if pyqt_initialized:
        return
    for subpath in [
            ('Library', 'plugins'),
            ('Library', 'lib', 'qt4', 'plugins')]:
        qt_plugin_path = os.path.join(os.path.dirname(sys.executable),
                                      *subpath)
        if os.path.isdir(qt_plugin_path):
            QCoreApplication.addLibraryPath(
                safe_decode(qt_plugin_path, enc=sys.getfilesystemencoding())
            )
    if QCoreApplication.instance() is None:
        app = QApplication([])
    if font_database is None:
        try:
            font_database = QFontDatabase()
        except TypeError:
            font_database = QFontDatabase
        for font in FONTS:
            try:
                path = resources[f'{font}.ttf']
            except Exception:
                warnings.warn(f'Font {font} not found')
                continue
            font_id = font_database.addApplicationFont(str(path))
            if font_id < 0:
                warnings.warn(f'Failed to load font {font}')
                continue
            font_families = font_database.applicationFontFamilies(font_id)
            if font_families:
                font_substitutions.append((font_families[0], font))
    pyqt_initialized = True


def text_rect(text, center=True, x=0, y=0, max_width=None,
              font_family='sans', font_size=18, font_bold=False,
              font_italic=False, html=True):
    """Computes the bounding box of rendered text without requiring a Canvas
    or experiment instance. This is a standalone equivalent of
    Canvas.text_rect(), intended for use in tests and scripts.

    Parameters
    ----------
    text : str
        A string of text. HTML tags are interpreted when html=True.
    center : bool, optional
        If True (default), x and y indicate the center of the text. If
        False, they indicate the top-left corner.
    x : int, optional
        The X coordinate of the text anchor point. Defaults to 0 (screen
        center in OpenSesame coordinates).
    y : int, optional
        The Y coordinate of the text anchor point. Defaults to 0 (screen
        center in OpenSesame coordinates).
    max_width : int, NoneType, optional
        Maximum pixel width before wrapping. Defaults to 1024 (centered)
        or 512 (non-centered), which matches a typical 1024-pixel-wide
        display.
    font_family : str, optional
        Font family name (e.g. 'sans', 'serif', 'mono'). Defaults to
        'sans'.
    font_size : int, optional
        Font size in pixels. Defaults to 18.
    font_bold : bool, optional
        Whether the font should be bold. Defaults to False.
    font_italic : bool, optional
        Whether the font should be italic. Defaults to False.
    html : bool, optional
        Whether HTML tags are interpreted. Defaults to True.

    Returns
    -------
    tuple
        A (x, y, width, height) tuple. x and y are the top-left corner of
        the bounding box. The leftmost pixel of the text is at x, and the
        rightmost pixel is at x + width.

    Examples
    --------
    >>> x, y, w, h = text_rect('Hello world')
    >>> print('Leftmost pixel: %d, rightmost pixel: %d' % (x, x + w))
    >>> x, y, w, h = text_rect('Hello world', x=100, y=50, center=False)
    """
    _ensure_pyqt_initialized()
    t = QGraphicsTextItem()
    t.setDefaultTextColor(QColor('black'))
    decoded = safe_decode(text)
    if html:
        html_text = decoded.replace('\n', '<br />')
        t.setHtml(
            '<div align="center">%s</div>' % html_text
            if center else html_text
        )
    else:
        t.setPlainText(decoded)
    if max_width is None:
        # Mirror the logic in RichText._to_qgraphicstextitem: use half of a
        # standard 1024-wide canvas, adjusted for the anchor position.
        mw = DEFAULT_HALF_CANVAS_WIDTH - x
        if center:
            mw *= 2
    else:
        mw = max_width * 2 if center else max_width
    t.setTextWidth(mw)
    f = QFont(
        font_family,
        weight=QFont.Bold if font_bold else QFont.Normal,
        italic=font_italic
    )
    for family, substitute in font_substitutions:
        f.insertSubstitution(substitute, family)
    f.setPixelSize(font_size)
    t.setFont(f)
    q_rect = t.boundingRect()
    height = int(q_rect.height())
    width = int(q_rect.width())
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    t.paint(painter, QStyleOptionGraphicsItem(), None)
    painter.end()
    qimage = pixmap.toImage()
    try:
        pil_image = Image.fromqimage(qimage)
    except (ImportError, TypeError):
        import numpy as np
        qimage = qimage.convertToFormat(QImage.Format_ARGB32)
        pw = qimage.width()
        ph = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        arr = np.array(ptr).reshape(ph, pw, 4)
        arr = arr[..., [2, 1, 0, 3]]
        pil_image = Image.fromarray(arr)
    bbox = pil_image.getbbox()
    x1, y1, x2, y2 = (0, 0, 1, 1) if bbox is None else bbox
    y2 = max(y1 + font_size, y2)
    w = x2 - x1
    h = y2 - y1
    if center:
        return x - w // 2, y - h // 2, w, h
    return x, y, w, h


class RichText(Element):

    def __init__(
            self,
            canvas,
            text,
            center=True,
            x=None,
            y=None,
            max_width=None,
            **properties
    ):

        global pyqt_initialized

        if not pyqt_initialized:
            self._init_pyqt(canvas.experiment)
            pyqt_initialized = True
        x, y = canvas.none_to_center(x, y)
        properties = properties.copy()
        properties.update({
            'text': safe_decode(text),
            'center': center,
            'x': x,
            'y': y,
            'max_width': max_width
        })
        self._cached_size = None
        Element.__init__(self, canvas, **properties)

    def _init_pyqt(self, exp):

        global app, font_database

        # Add the Qt plugin folders to the library path, if they exists. Where
        # these folders are depends on the version of Qt4, but these are two
        # possible locations.
        qt_plugin_path = os.path.join(
            os.path.dirname(sys.executable), 'Library', 'plugins')
        if os.path.isdir(qt_plugin_path):
            QCoreApplication.addLibraryPath(
                safe_decode(qt_plugin_path, enc=sys.getfilesystemencoding())
            )
        qt_plugin_path = os.path.join(
            os.path.dirname(sys.executable), 'Library', 'lib', 'qt4', 'plugins')
        if os.path.isdir(qt_plugin_path):
            QCoreApplication.addLibraryPath(
                safe_decode(qt_plugin_path, enc=sys.getfilesystemencoding())
            )
        # If no instance of QApplication exists, a segmentation fault seems to
        # always occur. So we create one.
        if QCoreApplication.instance() is None:
            app = QApplication([])
        # Register the fonts bundled with OpenSesame
        if font_database is None:
            try:
                font_database = QFontDatabase()
            except TypeError:
                # PyQt6 the class is used directly, without creating an
                # instance
                font_database = QFontDatabase
            for font in FONTS:
                self._register_font(exp, font)

    def _register_font(self, exp, font, fd=None):

        global pyqt_initialized
        if not pyqt_initialized:
            self._init_pyqt(exp)
            pyqt_initialized = True
        oslogger.debug(u'Registering font {}'.format(font))
        try:
            path = resources[f'{font}.ttf']
        except Exception:
            warnings.warn(u'Font %s not found' % font)
        else:
            if fd is None:
                fd = font_database
            font_id = fd.addApplicationFont(str(path))
            if font_id < 0:
                warnings.warn(u'Failed to load font %s' % font)
                return
            font_families = fd.applicationFontFamilies(font_id)
            if not font_families:
                warnings.warn(u'Font %s contains no families' % font)
                return
            font_substitutions.append((font_families[0], font))

    def _register_custom_font(self, font):

        if font + u'.ttf' not in self.experiment.pool:
            return
        if font in (font for font_family, font in font_substitutions):
            return
        self._register_font(self.experiment, font)

    @property
    def size(self):

        if self._cached_size:
            return self._cached_size
        bbox = self._qimage_to_pil(self._to_qimage()).getbbox()
        x1, y1, x2, y2 = (0, 0, 1, 1) if bbox is None else bbox
        y2 = max(y1 + self.font_size, y2)
        self._cached_size = x2 - x1, y2 - y1
        return self._cached_size

    @property
    def rect(self):

        w, h = self.size
        if self.center:
            return self.x - w // 2, self.y - h // 2, w, h
        return self.x, self.y, w, h

    def _to_qgraphicstextitem(self):

        t = QGraphicsTextItem()
        t.setDefaultTextColor(QColor(self.color.hexcolor))
        if self.html:
            text = self.text.replace(u'\n', u'<br />')
            t.setHtml(
                u'<div align="center">%s</div>' % text
                if self.center else text
            )
        else:
            t.setPlainText(self.text)
        mw = self.max_width
        if mw is None:
            mw = self._canvas.width // 2 - self.x
        if self.center:
            mw *= 2
        t.setTextWidth(mw)
        # Register custom fonts that are placed in the file pool
        self._register_custom_font(self.font_family)
        f = QFont(
            self.font_family,
            weight=QFont.Bold if self.font_bold else QFont.Normal,
            italic=self.font_italic
        )
        for family, substitute in font_substitutions:
            f.insertSubstitution(substitute, family)
        f.setPixelSize(self.font_size)
        t.setFont(f)
        return t

    def _to_qimage(self):

        t = self._to_qgraphicstextitem()
        rect = t.boundingRect()
        height = int(rect.height())
        width = int(rect.width())
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(Qt.red)
        if self.center and self.html:
            painter.drawPoint(width // 2, 0)
            painter.drawPoint(width // 2, height - 1)
        else:
            painter.drawPoint(0, 0)
            painter.drawPoint(0, height - 1)
        t.paint(painter, QStyleOptionGraphicsItem(), None)
        painter.end()
        return pixmap.toImage()
        
    def _qimage_to_pil(self, qimage):
        """This functions takes a QImage and returns a PIL Image. If available,
        this uses PIL's built-in conversion tool, but since this has broken
        for PyQt5 for Pillow >= 10, we resort to a custom conversion procedure
        if necessary.
        """
        try:
            return Image.fromqimage(self._to_qimage())
        except (ImportError, TypeError):
            pass
        import numpy as np
        oslogger.info('no Qt bindings, using custom QImage to PIL conversion')
        qimage = qimage.convertToFormat(QImage.Format_ARGB32)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        # Assuming 32-bit color depth
        arr = np.array(ptr).reshape(height, width, 4)
        if arr.shape[2] == 4:
            arr = arr[..., [2, 1, 0, 3]]  # Convert ARGB to RGBA
        else:
            arr = arr[..., [2, 1, 0]]  # Convert RGB to BGR
        return Image.fromarray(arr)

    def _to_pil(self):

        im = self._qimage_to_pil(self._to_qimage())
        bbox = im.getbbox()
        x1, y1, x2, y2 = (0, 0, 1, 1) if bbox is None else bbox
        y1 = min(y2 - self.font_size, y1)
        return im.crop((x1, y1 + 1, x2, y2 - 1))

    @staticmethod
    def _setter(key, self, val):

        if key == u'text':
            val = safe_decode(val)
        super(RichText, self)._setter(key, self, val)

    def _on_attribute_change(self, **kwargs):

        self._cached_size = None
        super(RichText, self)._on_attribute_change(key, self, val)
