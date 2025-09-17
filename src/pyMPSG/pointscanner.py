# -*- coding: utf-8 -*-
"""
Collection of classes that define 2D point sequences.
All classes here inherit from PointScanner.

@author: René Vollmer
"""

import numpy as np
from typing import List, Optional

from . import helper
from .setup import Setup


class PointScanner:
    pos: int = 0
    _points: List[int]

    def __iter__(self):
        # reset
        self.pos = 0
        return self

    def __next__(self):
        if self.pos < len(self._points):
            p = self._points[self.pos]
            self.pos = (self.pos + 1)
            return p
        else:
            raise StopIteration()

    def _append_points(self, x, y, center: tuple, setup):
        for i in range(len(x)):
            self._points.append(
                setup.convert_position_to_pixels(x=x[i] + center[0],
                                                 y=y[i] + center[1])
            )

class Combiner(PointScanner):
    scannerlist: List[PointScanner]

    def __init__(self, scannerlist: List[PointScanner]):
        self.scannerlist = scannerlist

        self._points = []
        for scanner in scannerlist:
            self._points += scanner._points


class Spiral(PointScanner):
    def __init__(self, radius: float, setup: Setup,
                 center: Optional[tuple] = None, inside_out: bool = True,
                 alternating_handingness: bool = True):
        center = (0, 0) if center is None else center
        # Generate points
        self._points = []

        hands = [True, False] if alternating_handingness else [True]
        for i in hands:
            ds = np.sqrt(2) * setup.ds if alternating_handingness else setup.ds
            x, y, r = helper.spiral(radius=radius, step_size=ds,
                                    inside_out=inside_out, clockwise=bool(i))
            del r  # Not required

            self._append_points(x=x, y=y, center=center, setup=setup)


class ConcentricCircles(PointScanner):
    def __init__(self, radius: float, setup: Setup,
                 center: Optional[tuple] = None, inside_out: bool = True):
        center = (0, 0) if center is None else center
        # Generate points
        self._points = []

        rs = np.arange(0, radius, setup.ds)
        if inside_out:
            rs = np.flip(rs)

        for r in rs:
            x, y = helper.circle(radius=r, step_size=setup.ds)

            self._append_points(x=x, y=y, center=center, setup=setup)


class ConcentricSquares(PointScanner):
    def __init__(self, width: float, setup: Setup,
                 center: Optional[tuple] = None, inside_out: bool = True,
                 height: Optional[float] = None):
        center = (0, 0) if center is None else center
        # Generate points
        self._points = []

        height = height if height is not None else width

        mi = min(width, height)
        ma = max(width, height)

        rs = np.arange(0, mi / 2, setup.ds)
        if inside_out:
            rs = np.flip(rs)

        for i, r in enumerate(rs):
            R: float = float(2 * r)
            if (mi - R) >= 2 * setup.ds:
                # Create squares decreasing in size, circulating start
                # and alternating handingness
                x, y = helper.square(height=(height - R), width=(width - R),
                                     step_size=setup.ds,
                                     start=int(i % 4), clockwise=bool((i % 2) == 0))

            elif (mi - R) >= 0:
                # Add a centred line
                line = helper.arange_sym(ma - R, setup.ds)
                line_a = np.zeros_like(line)

                if mi == ma or len(line) <= 1:
                    x = [0, ]
                    y = [0, ]
                elif width == ma:
                    x = line
                    y = line_a
                else:
                    x = line_a
                    y = line
            else:
                x, y = [], []

            # Add points
            self._append_points(x=x, y=y, center=center, setup=setup)


class SquareGrid(PointScanner):
    def __init__(self, width: float, setup: Setup,
                 center: Optional[tuple] = None, height: Optional[float] = None):
        center = (0, 0) if center is None else center
        # Generate points
        self._points = []

        height = height if height is not None else width
        mx = int(width / (2 * setup.ds)) * setup.ds
        my = int(height / (2 * setup.ds)) * setup.ds
        x, y = np.mgrid[-mx:+mx:setup.ds, -my:+my:setup.ds].reshape(2, -1)
        self._append_points(x=x, y=y, center=center, setup=setup)
