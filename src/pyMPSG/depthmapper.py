# -*- coding: utf-8 -*-
"""
Collection of classes that define 2.5D shapes (a 2D map of depths).
All classes inherit from DepthMapper and provide the main function query_depth(xp, yp) that returns a number
of required dwell steps for the queried pixel location (based on the provided Setup).

@author: René Vollmer
"""

import numpy as np
from typing import List, Optional, Iterable

from .setup import Setup


class DepthMapper:
    setup: Setup

    def _query_depth(self, x: float, y: float) -> float:
        return 0

    def query_depth(self, xp: int, yp: int) -> int:
        x, y = self.setup.convert_pixels_to_position(xp, yp)
        depth = self._query_depth(x=x, y=y)
        return self.setup.convert_depth_to_dwelltime_steps(depth)


class SummingCombiner(DepthMapper):
    def __init__(self, elements: List[DepthMapper]):
        assert len(elements) > 0

        # Warn if not all the setups are the same
        self.setup = elements[0].setup
        for e in elements:
            if e.setup != self.setup:
                print("Warning: not all Setups used in the SummingCombiner are the same!")
                break
        self.elements = elements

    def _query_depth(self, x: float, y: float) -> int:
        return sum([ele._query_depth(x=x, y=y) for ele in self.elements])


def _ramp(r: float, dr: float, z: float) -> float:
    return z * (1 - r / dr)


def _sphere(r: float, rs: float) -> float:
    return rs - np.sqrt(rs ** 2 - r ** 2)


def _get_radial(x: float, y: float, center: [float, float]) -> float:
    return ((x - center[0]) ** 2 + (y - center[1]) ** 2) ** 0.5


def _get_square_radial(x: float, y: float, center: [float, float]) -> float:
    return max(abs(x - center[0]), abs(y - center[1]))


class Ring(DepthMapper):
    def __init__(self, r_i: float, r_o: float, depth: float, setup: Setup,
                 center: Optional[tuple] = None, square: bool = False):
        assert r_i <= r_o, "Inner radius must be smaller or equal to outer radius!"
        self.r_i = r_i
        self.r_o = r_o
        self.depth = depth
        self.setup = setup
        self.center = center if center else (0, 0)
        self._transl_f = _get_square_radial if square else _get_radial

    def _query_depth(self, x: float, y: float) -> float:
        r: float = self._transl_f(x, y, self.center)
        if self.r_o > r > self.r_i:
            return self.depth
        return 0


class Circle(Ring):
    def __init__(self, r: float, depth: float, setup: Setup,
                 center: Optional[Iterable[float]] = None, square: bool = False):
        super().__init__(r_i=0, r_o=r, depth=depth, setup=setup,
                         center=center, square=square)


class Square(DepthMapper):

    def __init__(self, width: float, depth: float, setup: Setup,
                 center: Optional[Iterable[float]] = None,
                 height: Optional[float] = None):
        self.width = width
        self.height = height if height is not None else width
        self.depth = depth
        self.setup = setup
        self.center = center if center else (0, 0)

    def _query_depth(self, x: float, y: float) -> float:
        x, y = (x - self.center[0]), (y - self.center[1])

        # print(f"x={x};y={y};r={r} is a", end='')
        if abs(x) < self.width / 2 and abs(y) < self.height / 2:
            # Outside the structure
            # print("n outside point")
            return self.depth
        return 0


#########################################################################################################

class CircularRamp(DepthMapper):

    def __init__(self, r_i: float, c_r: float, depth: float, setup: Setup,
                 center: Optional[tuple] = None, invert: bool = False, square: bool = False):
        self.r_i = r_i
        self.r_o = r_i + c_r
        self.c_r = c_r
        self.depth = depth
        self.invert = invert
        self.setup = setup
        self.center = center if center else (0, 0)
        self._transl_f = _get_square_radial if square else _get_radial

    def _query_depth(self, x: float, y: float) -> float:
        r: float = self._transl_f(x, y, self.center)
        if self.r_i < r < self.r_o:
            if self.invert:
                return self.depth - _ramp(r=r - self.r_i, dr=self.c_r, z=self.depth)
            else:
                return _ramp(r=r - self.r_i, dr=self.c_r, z=self.depth)
        return 0


class Dome(DepthMapper):

    def __init__(self, r: float, setup: Setup, center: Optional[Iterable[float]] = None,
                 stickout_radius: Optional[float] = None):
        self.r = r
        self.setup = setup
        self.stickout_r = stickout_radius if stickout_radius else r
        self.center = center if center else (0, 0)

    def _query_depth(self, x: float, y: float) -> float:
        r: float = _get_radial(x, y, self.center)
        if r <= self.stickout_r:
            return _sphere(r=r, rs=self.r)
        return 0


class FullRecessedDome(SummingCombiner):
    # Outer radius of structure
    r_o: float
    def __init__(self,
                 premill_depth: float,
                 dome_radius: float,
                 dome_sag: float,
                 recess_clearance_distance: float,
                 slope_length: float,
                 setup: Setup, center: Optional[Iterable[float]] = None):
        self.premill_depth = premill_depth
        self.dome_radius = dome_radius
        self.dome_sag = dome_sag
        self.recess_clearance_distance = recess_clearance_distance
        self.slope_length = slope_length

        # # Calculated parameters
        # The total depth of the recession, next to the dome
        self.total_depth = premill_depth + dome_sag

        # The radius of the circle formed by the actual physical dome that sticks out of the recessed area
        self.dome_stickout_radius = np.sqrt(dome_radius ** 2 - (dome_radius - dome_sag) ** 2)

        # Distance/Radius from the center of the dome to the start of the edge-slope.
        self.dome_slope_distance = self.dome_stickout_radius + self.recess_clearance_distance
        self.r_o = self.dome_slope_distance + self.dome_slope_distance

        self.setup = setup
        self.center = center if center else (0, 0)
        elms = [
            Dome(r=self.dome_radius, setup=setup, center=self.center, stickout_radius=self.dome_stickout_radius),
            Ring(r_i=self.dome_stickout_radius, r_o=self.dome_slope_distance, depth=self.total_depth, setup=setup,
                 center=self.center),
            CircularRamp(r_i=self.dome_slope_distance, c_r=self.slope_length, depth=self.total_depth,
                         setup=setup, center=self.center),
        ]
        if premill_depth:
            elms.append(Ring(r_o=self.dome_stickout_radius, r_i=0, depth=premill_depth, center=center, setup=setup))
        super().__init__(elements=elms)


class FullSIL(FullRecessedDome):
    """
    Obsolete, simplified version of FullRecessedDome with historic variable naming scheme.
    """
    def __init__(self, r_i: float, c_t: float, c_r: float, setup: Setup, center: Optional[Iterable[float]] = None):
        super().__init__(premill_depth=0,
                         dome_radius=r_i,
                         dome_sag=r_i,
                         recess_clearance_distance=c_t,
                         slope_length=c_r, setup=setup, center=center)
        self.r_i = r_i
        self.r_o = r_i + c_t + c_r
        self.r_t = r_i + c_t
        self.c_t = c_t
        self.c_r = c_r


class PostSlope(SummingCombiner):

    def __init__(self, r_i: float, c_t: float, c_r: float, c_r_post_slope: float, setup: Setup,
                 center: Optional[Iterable[float]] = None):
        self.r_o = r_i + c_t + c_r
        self.r_o_post_slope = r_i + c_t + c_r_post_slope
        self.r_t = r_i + c_t
        self.c_t = c_t
        self.c_r = c_r
        self.setup = setup
        self.center = center if center else (0, 0)
        super().__init__(elements=[
            CircularRamp(r_i=self.r_t, c_r=c_r, depth=-1 * r_i, setup=setup, center=self.center),
            CircularRamp(r_i=self.r_t, c_r=c_r_post_slope, depth=r_i, setup=setup, center=self.center),
        ])


class Pretrench(SummingCombiner):

    def __init__(self, r_t: float, c_r: float, depth: float, setup: Setup, r_i: float = 0, inner_depth: float = 0,
                 center: Optional[Iterable[float]] = None):
        self.r_i = r_i
        self.r_o = r_t + c_r
        self.r_t = r_t
        self.c_r = c_r
        self.depth = depth
        self.setup = setup
        self.center = center if center else (0, 0)
        eles = [
            Ring(r_i=r_i, r_o=self.r_t, depth=depth, setup=setup, center=self.center),
            CircularRamp(r_i=self.r_t, c_r=c_r, depth=depth, setup=setup, center=self.center),
        ]
        if r_i > 0 and inner_depth > 0:
            eles.append(Circle(r=r_i, depth=inner_depth, setup=setup, center=self.center))

        super().__init__(elements=eles)


class HoleWithChampfer(SummingCombiner):
    def __init__(self, r_i: float, depth: float, c_r: float, c_d: float, setup: Setup,
                 center: Optional[Iterable[float]] = None, square: bool = False):
        self.center = center if center else (0, 0)

        elms = [
            CircularRamp(r_i=r_i, c_r=c_r, depth=c_d, setup=setup, center=self.center, square=square),
        ]
        if square:
            elms.append(Square(width=2 * r_i, depth=depth, setup=setup, center=self.center))
        else:
            elms.append(Ring(r_i=0, r_o=r_i, depth=depth, setup=setup, center=self.center))
        super().__init__(elements=elms)


class Cone(SummingCombiner):
    def __init__(self, c_t: float, c_r: float, depth: float, setup: Setup, r_i: float = 0,
                 center: Optional[Iterable[float]] = None, square: bool = False):
        self.center = center if center else (0, 0)
        self.r_o = r_i + c_t + c_r

        eles = []

        if r_i > 0:
            eles.append(CircularRamp(r_i=0, c_r=r_i, depth=depth, setup=setup, center=self.center, invert=True,
                                     square=square))
        if c_t > 0:
            eles.append(Ring(r_i=r_i, r_o=r_i + c_t, depth=depth, setup=setup, center=self.center, square=square))
        if c_r > 0:
            eles.append(
                CircularRamp(r_i=r_i + c_t, c_r=c_r, depth=depth, setup=setup, center=self.center, square=square))
        super().__init__(elements=eles)


class Pyramid(Cone):
    def __init__(self, c_t: float, c_r: float, depth: float, setup: Setup, width: float = 0,
                 center: Optional[Iterable[float]] = None):
        super().__init__(c_t=c_t, c_r=c_r, depth=depth, setup=setup, r_i=width, center=center, square=True)


class Stairs(SummingCombiner):

    def __init__(self, setup: Setup, steps: int = 3, step_length: float = 1, target_angle: float = 90 - 52,
                 width: float = 5, center: Optional[Iterable[float]] = None):
        self.steps = steps
        self.step_length = step_length
        self.target_angle = target_angle
        self.tan_angle = np.tan(np.pi * target_angle / 180)
        self.width = width
        self.setup = setup
        self.center = center if center else (0, 0)
        eles = [
            Square(width=width, depth=i * step_length * self.tan_angle, height=step_length,
                   center=(self.center[0], self.center[1] - (i - steps / 2 - 0.5) * step_length), setup=setup)
            for i in range(1, steps + 1)
        ]

        super().__init__(elements=eles)


class Ramp(DepthMapper):
    def __init__(self, setup: Setup, height: float, depth: float, width: float = None, rotation: float = 0,
                 center: Optional[Iterable[float]] = None):
        self.width = width if width else height
        self.height = height
        self.setup = setup
        self.center = center if center else (0, 0)
        self.depth = depth
        self.rotation = rotation

    def _query_depth(self, x: float, y: float) -> float:
        x, y = x - self.center[0], y - self.center[1]
        a = self.rotation * np.pi / 180
        x, y = x * np.sin(a) + y * np.cos(a), x * np.cos(a) - y * np.sin(a)
        if self.width >= abs(x) and self.height / 2 >= abs(y):
            return -(x / self.width) * self.depth
        return 0
