# -*- coding: utf-8 -*-
"""
Classes that provide the basic machine settings.

@author: René Vollmer
TODO: Better storing of machine settings?!
"""

import numpy as np
from dataclasses import dataclass, FrozenInstanceError
from math import floor
from tabulate import tabulate
from typing import Union, Tuple


@dataclass  # (frozen=True)
class Setup:
    mu: float  # milling rate in [um**3 / (us * nA)]
    I_B: float  # beamcurrent in [nA]
    ds: float  # in [um]

    # TODO: can this be different for other types?
    max_dwelltime: int = 2 ** 18  # in units of base_time_res

    base_time_res: int = 100  # in [ns]; typically 100ns
    zoom: int = int(3.5e3)
    translation_factor: int = 207200  # also seen 127750
    dac_bits: int = 16  # Bits of the x/y-DAC in the FIB
    time_res: int = 100  # in [ns]

    # Do not set these!
    # repetitions: int = 1
    # x_res: int = 0 # pixels
    # y_res: int = 0 # pixels
    # max_width: float # in [um]
    # max_height: float # in [um]
    # pixel_size: float # in [um]
    __after_init_done__: bool = False

    def __post_init__(self):
        # ensure these variables are integer:
        self.zoom = int(self.zoom)
        self.base_time_res = int(self.base_time_res)
        self.time_res = int(self.time_res)
        self.dac_bits = int(self.dac_bits)
        self.translation_factor = int(self.translation_factor)

        # Helping variables

        # Factor 1e-3 from us -> ns
        # Note: I do no know where the magic divisor 2 comes from, but it's needed!
        mu = (1e-3 * self.mu) / 2  # um**3 / (ns * nA)
        self.zeta = mu * self.I_B / self.ds ** 2  # um/ns
        self.depth_to_time = 1 / (self.zeta * 2)

        # Calculate the resolution-size relationship (scaling)
        assert self.dac_bits > 0, "Number of DAC bits must be larger than zero!"
        self.x_res = int(2 ** self.dac_bits)
        self.y_res = int(2 ** self.dac_bits)
        if self.dac_bits != 16:
            print("Warning: The code has only been tested with 16bit DAC.")

        self.max_width = self.translation_factor / self.zoom  # in [um]
        self.pixel_size = self.max_width / self.x_res
        self.max_height = self.pixel_size * self.y_res

        # Calculate the dwelltime step length and number of repetions
        assert self.time_res > 0, "Time resolution must be larger than zero!"
        if self.time_res % 100 == 0:
            self.base_time_res = int(100)
            self.repetitions = int(self.time_res / 100)
        else:
            if self.base_time_res % 50 == 0:
                self.time_res = int(50)
                self.repetitions = int(self.time_res / 50)
            elif self.base_time_res % 25 == 0:
                self.time_res = int(25)
                self.repetitions = int(self.time_res / 25)
            else:
                self.repetitions = 1
                self.base_time_res = self.time_res
            print("Warning: this script has only been tested with 100ns resolution for the dwell time" +
                  f" (you chose {self.time_res:d}ns!")
        assert self.base_time_res * self.repetitions == self.time_res, "Programming error!"

        self.__after_init_done__ = isinstance(self, Setup) and not issubclass(type(self), Setup)

    def __setattr__(self, field, value):
        # Emulate the "Frozen" behaviour for dataclasses, after finishing initializing.
        if self.__after_init_done__:
            raise FrozenInstanceError(f"cannot assign to field '{field}'")
        else:
            self.__dict__[field] = value

    def summary(self) -> str:
        s = "Setup summary:\n"
        items = [
            ['Beam current', self.I_B, "nA"],
            ['Material milling rate μ', self.mu, "μm³/(nA·ns)"],
            ['Used step size (should be similar to beam size)', f"{self.ds * 1e3:.1f}", "nm"],
            ['Base time step', f"{self.base_time_res:d}", "ns"],
            ['Eff. time step (repetions)', f"{self.time_res:d} ({self.repetitions:d})", "ns (-)"],
            ['Eff. depth resolution', f"{self.convert_dwelltime_steps_to_depth(1) * 1e3:.3f}", "nm"],
            ['Max. depth per instruction', f"{self.convert_dwelltime_steps_to_depth(self.max_dwelltime):.3f}", "μm"],
            ['-', '-', '-'],
            ['Magnification/Zoom', f"{self.zoom:d}", ""],
            ['DAC bits', self.dac_bits, "bit"],
            ['Pixel-size translation factor', f"{self.translation_factor:d}", "μm/\"zoom\""],
            ['Writefield resolution', f"{self.x_res:d}x{self.y_res:d}", "px"],
            ['Writefield size', f"{self.max_width:.1f}x{self.max_height:.1f}", "μm"],
            ['Pixel size', f"{self.pixel_size * 1e3:.3f}", "nm"],
        ]

        s += tabulate(items, headers=['Parameter', 'Value', 'Unit'], tablefmt="rst")
        return s

    def convert_dwelltime_to_depth(self, dt: float) -> float:
        """
        :param dt: depth in dwelltime [ns] to be converted to micrometres
        :returns: depth in micrometres
        """
        return dt / self.depth_to_time

    def convert_depth_to_dwelltime(self, dz: float) -> float:
        """
        :param dz: depth in micrometres to be converted to dwelltime
        :returns: depth expressed as dwelltime [ns]
        """
        return dz * self.depth_to_time

    def convert_dwelltime_steps_to_depth(self, dt: Union[int, np.ndarray]) -> float:
        """
        :param dt: depth in dwelltime steps to be converted to micrometres
        :returns: depth in micrometres
        """
        return self.convert_dwelltime_to_depth(dt=dt * self.time_res)

    def convert_depth_to_dwelltime_steps(self, dz: Union[float, np.ndarray]) -> Union[int, np.ndarray]:
        """
        :param dz: depth in micrometres to be converted to dwelltime steps
        :returns: depth expressed as dwelltime steps
        """
        return np.round(self.convert_depth_to_dwelltime(dz=dz) / self.time_res)

    def convert_pixels_to_length(self, dp: int) -> float:
        """
        :param dp: length in pixels to be converted to micrometres
        :returns: length in micrometres
        """
        return dp * self.pixel_size

    def convert_length_to_pixels(self, dx: float) -> int:
        """
        :param dx: length in micrometres to be converted to pixels
        :returns: length in pixels
        """
        return np.round(dx / self.pixel_size)

    def convert_position_to_pixels(self, x: float, y: float) -> Tuple[int, int]:
        """
        Assumes that (0., 0.) is in the middle of the write-field
        :param x: x-Position in micrometres to be converted to pixels
        :param y: y-Position in micrometres to be converted to pixels
        :returns: position in pixels
        """
        assert abs(x) < self.max_width / 2, "point is outside the writefield!"
        assert abs(y) < self.max_height / 2, "point is outside the writefield!"

        xp = int(self.convert_length_to_pixels(x) + floor(self.x_res / 2))
        yp = int(self.convert_length_to_pixels(y) + floor(self.y_res / 2))

        assert 0 <= xp < self.x_res, f"{xp:d} > {self.x_res} : programming error!"
        assert 0 <= yp < self.y_res, f"{yp:d} > {self.y_res} : programming error!"

        return xp, yp

    def convert_pixels_to_position(self, xp: int, yp: int) -> Tuple[float, float]:
        """
        Assumes that (0., 0.) is in the middle of the write-field
        :param xp: x-Position in pixels to be converted to micrometres
        :param yp: y-Position in pixels to be converted to micrometres
        :returns: positon in micrometres
        """

        assert 0 <= xp < self.x_res, "point is outside the writefield!"
        assert 0 <= yp < self.y_res, "point is outside the writefield!"

        x = self.convert_pixels_to_length(xp - floor(self.x_res / 2))
        y = self.convert_pixels_to_length(yp - floor(self.y_res / 2))

        assert abs(x) <= self.max_width / 2, f"programming error! {xp}->{x}"
        assert abs(y) <= self.max_height / 2, f"programming error! {yp}->{y}"

        return x, y


@dataclass
class LayeredSetup(Setup):
    """
    Allows you to specify the maximum layer height dz. This is not a very clean solution to achieve the layering.
    """
    dz: float = -1

    def __post_init__(self):
        super().__post_init__()
        if self.dz > 0:
            steps = self.convert_depth_to_dwelltime_steps(dz=self.dz)
            if steps <= self.max_dwelltime:
                self.max_dwelltime = steps
        self.dz = self.convert_dwelltime_to_depth(self.max_dwelltime)
        self.__after_init_done__ = True
