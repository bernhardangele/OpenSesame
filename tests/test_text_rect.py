#!/usr/bin/env python
# -*- coding:utf-8 -*-

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

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""
import unittest
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from openexp._canvas._richtext.richtext import text_rect


class CheckTextRect(unittest.TestCase):

    """
    desc:
        Tests the standalone text_rect() function in the richtext module,
        which computes the bounding box of rendered text without requiring
        a Canvas or experiment instance.
    """

    def test_returns_four_tuple(self):
        """text_rect() must return a (x, y, width, height) 4-tuple."""
        result = text_rect('Hello world')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)

    def test_positive_dimensions(self):
        """Width and height must be positive for non-empty text."""
        x, y, w, h = text_rect('Hello world')
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_centered_origin(self):
        """With default center=True and x=0, y=0 the top-left x should be
        negative (text extends left of the anchor point)."""
        x, y, w, h = text_rect('Hello world', center=True, x=0, y=0)
        self.assertLess(x, 0)

    def test_non_centered_origin(self):
        """With center=False and x=0, y=0 the top-left x must equal 0."""
        x, y, w, h = text_rect('Hello world', center=False, x=0, y=0)
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

    def test_explicit_position(self):
        """The bounding box must be shifted by the given x, y offset."""
        x0, y0, w0, h0 = text_rect('Hello world', center=False, x=0, y=0)
        x1, y1, w1, h1 = text_rect('Hello world', center=False,
                                    x=100, y=50)
        self.assertEqual(x1, x0 + 100)
        self.assertEqual(y1, y0 + 50)
        self.assertEqual(w0, w1)
        self.assertEqual(h0, h1)

    def test_size_matches_text_content(self):
        """Longer text should produce a wider bounding box (same font/size)."""
        _, _, w_short, _ = text_rect('Hi', center=False)
        _, _, w_long, _ = text_rect('Hello, world!', center=False)
        self.assertGreater(w_long, w_short)

    def test_font_size_affects_height(self):
        """A larger font size should produce a taller bounding box."""
        _, _, _, h_small = text_rect('Test', font_size=12)
        _, _, _, h_large = text_rect('Test', font_size=36)
        self.assertGreater(h_large, h_small)

    def test_centered_rect_width_equals_non_centered(self):
        """Width and height must be the same regardless of the center flag."""
        _, _, w_c, h_c = text_rect('Same text', center=True, x=0, y=0)
        _, _, w_nc, h_nc = text_rect('Same text', center=False, x=0, y=0)
        self.assertEqual(w_c, w_nc)
        self.assertEqual(h_c, h_nc)

    def test_html_bold(self):
        """Bold HTML markup should produce a wider result than plain text."""
        _, _, w_plain, _ = text_rect('Bold', html=True)
        _, _, w_bold, _ = text_rect('<b>Bold</b>', html=True)
        self.assertGreater(w_bold, w_plain)

    def test_empty_text(self):
        """Empty text should return a non-negative bounding box without
        raising an exception."""
        result = text_rect('')
        self.assertEqual(len(result), 4)
        x, y, w, h = result
        self.assertGreaterEqual(w, 0)
        self.assertGreaterEqual(h, 0)


if __name__ == '__main__':
    unittest.main()
