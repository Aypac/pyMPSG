# -*- coding: utf-8 -*-
"""
Class that uses a PointScanner, a DepthMapper, and a Setup to generate a list of pixel coordinates and dwell times.
We suggest using the LayeredGenerator for most applications (it will pass over the entire surface of the PointScanner,
milling up to a maximum depth, and then repeat).

@author: René Vollmer
"""
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import time
from math import floor, ceil

from matplotlib.axes._axes import Axes

from .depthmapper import DepthMapper
from .pointscanner import PointScanner
from .setup import Setup


class StreamGenerator:
    list_of_instructions: list = None  # list of [x, y, dz, start_z]
    pointscanner: PointScanner
    depthmapper: DepthMapper
    setup: Setup
    layer_thickness: float
    layered_mode: bool

    # Key is (x, y) [pixels], value is current depth at that point.
    #   TODO: might make sense to introduce a dedicated class at some point to enforce this.
    _depth_map: dict = None

    # Sum of the current dwell time (ignoring repetitions) in dwelltime steps.
    _dwell_time_sum: int

    eff_layers: int = 0

    # Flag that can be set for more verbose output
    debug: bool = False

    def __init__(self, pointscanner: PointScanner, depthmapper: DepthMapper, setup: Setup,
                 layer_thickness: Optional[float] = None):
        self.layer_thickness = layer_thickness
        self.layered_mode = bool(self.layer_thickness)
        self.pointscanner = pointscanner
        self.depthmapper = depthmapper
        self.setup = setup

    def has_run(self) -> bool:
        return self.list_of_instructions is not None

    def ensure_run(self) -> None:
        """
        Ensures that the generator ran while avoiding running it multiple times (which takes a lot of resources).
        """
        if not self.has_run():
            self.generate_points()

    def generate_points(self):
        # Initialize all variables
        self.list_of_instructions = []
        self._depth_map = {}
        self._dwell_time_sum = 0

        self._generate_points()

    def _depth_at(self, x: int, y: int) -> int:
        return self._depth_map[(x, y)] if (x, y) in self._depth_map else 0

    def get_number_of_instructions(self) -> int:
        self.ensure_run()
        return len(self.list_of_instructions)

    def format_total_time(self) -> str:
        self.ensure_run()
        tT = self.get_total_time() * 1e-9
        return "%02d:%02d:%06.3f" % (floor(tT / 3600), floor(tT % 3600 / 60), tT % 60)

    def plot_result(self, all_layers: bool = False,
                    display: bool = True, view: tuple = None,
                    micrometres: bool = False, whole_field: bool = False) -> Axes:
        self.ensure_run()

        if all_layers:
            # Indicate the result of all exposure steps (not recommended)
            ps = np.array(self.list_of_instructions, dtype=float)
            xs, ys, zs = ps[:, 0], ps[:, 1], ps[:, 2] + ps[:, 3]
        else:
            # Just indicate the final depth
            ps = np.array([p for p in self._depth_map.keys()], dtype=int)
            xs, ys = ps[:, 0], ps[:, 1]
            zs = np.array(list(self._depth_map.values()), dtype=int)

        # Add a boundary around the plot to indicate the size of the WF
        if whole_field:
            # We don't need to plot a point at each pixel for it to appear as
            # a solid line, therefore only mark a point every ... pixels
            ds_pixel = self.setup.convert_length_to_pixels(dx=10 * self.setup.ds)
            x_range = np.arange(0, self.setup.x_res, ds_pixel)
            y_range = np.arange(0, self.setup.y_res, ds_pixel)

            xs = np.append(xs, x_range)
            ys = np.append(ys, np.zeros_like(x_range))
            zs = np.append(zs, np.zeros_like(x_range))

            xs = np.append(xs, x_range)
            ys = np.append(ys, np.zeros_like(x_range) + (self.setup.y_res - 1))
            zs = np.append(zs, np.zeros_like(x_range))

            xs = np.append(xs, np.zeros_like(y_range))
            ys = np.append(ys, y_range)
            zs = np.append(zs, np.zeros_like(y_range))

            xs = np.append(xs, np.zeros_like(y_range) + (self.setup.x_res - 1))
            ys = np.append(ys, y_range)
            zs = np.append(zs, np.zeros_like(y_range))

        # rescale to um
        if micrometres:
            xs = np.array(xs, dtype=float)
            ys = np.array(ys, dtype=float)
            zs = np.array(zs, dtype=float)

            for i, x in enumerate(xs):
                xs[i], ys[i] = self.setup.convert_pixels_to_position(xp=x, yp=ys[i])
            zs = self.setup.convert_dwelltime_steps_to_depth(dt=zs)

        # print(xs, ys, zs)
        fig = plt.figure(figsize=(11, 11))
        ax = fig.add_subplot(111, projection='3d')

        # Colormap
        cmsel = plt.get_cmap("rainbow")

        size = 1.5e3 * self.setup.ds ** 2 if micrometres else 50
        size = size / 5 if whole_field else size
        color = np.linspace(0, 1, len(xs)) if all_layers else zs / np.max(zs)
        ax.scatter(xs, ys, -zs, c=color, marker='.', alpha=0.2, s=size, cmap=cmsel)

        if micrometres:
            ax.set_xlabel('X [μm]')
            ax.set_ylabel('Y [μm]')
            ax.set_zlabel('Z [μm]')
        else:
            ax.set_xlabel('X [px]')
            ax.set_ylabel('Y [px]')
            ax.set_zlabel('Z [dwelltime steps]')

        # fig.colorbar(plt.cm.ScalarMappable(cmap=cmsel), ax=ax)

        # Make the aspect ratio equal
        def axisEqual3D(ax):
            extents = np.array([getattr(ax, 'get_{}lim'.format(dim))() for dim in 'xyz'])
            sz = extents[:, 1] - extents[:, 0]
            centers = np.mean(extents, axis=1)
            maxsize = max(abs(sz))
            r = maxsize / 2
            for ctr, dim in zip(centers, 'xyz'):
                getattr(ax, 'set_{}lim'.format(dim))(ctr - r, ctr + r)

        if micrometres:
            axisEqual3D(ax)

        if view:
            ax.view_init(*view)

        if display:
            plt.show()
        # plt.close()

        return ax

    def save_plots(self, out_folder: str, save_args: dict = None, **args) -> None:
        save_args = save_args if save_args else {}

        if 'dpi' not in save_args:
            save_args['dpi'] = 150

        ax = self.plot_result(**args)

        ax.set_proj_type('persp')  # persp/ortho
        plt.savefig(out_folder + 'view_00.png', **save_args)

        ax.view_init(70, 45)
        ax.set_proj_type('persp')
        plt.savefig(out_folder + 'view_03.png', **save_args)

        ax.view_init(90 - 52, 90)
        ax.set_proj_type('persp')
        plt.savefig(out_folder + 'view_02_as_SEM.png', **save_args)

        ax.view_init(0, 0)
        ax.set_proj_type('ortho')
        plt.savefig(out_folder + 'view_side.png', **save_args)

        ax.view_init(90, 0)
        ax.set_proj_type('ortho')
        plt.savefig(out_folder + 'view_top.png', **save_args)

        plt.close()

    def get_total_time(self) -> float:
        """
        Total dwelltime (~total run time) in ns
        """
        self.ensure_run()

        return self._dwell_time_sum * self.setup.time_res

    def get_deepest_point(self, micrometres: bool = False) -> float:
        self.ensure_run()

        m = np.max(list(self._depth_map.values()))
        if micrometres:
            return self.setup.convert_dwelltime_steps_to_depth(m)
        else:
            return m

    def get_shallowest_point(self, micrometres: bool = False) -> float:
        self.ensure_run()

        m = np.min(list(self._depth_map.values()))
        if micrometres:
            return self.setup.convert_dwelltime_steps_to_depth(m)
        else:
            return m

    def get_summary_table(self) -> list:
        if self.has_run():
            N_tot: int = self.get_number_of_instructions()
            items = [
                ["Total dwelltime (expected run time)", self.format_total_time(), "HH:MM:ss.sss"],
                ["Total dwelltime", f"{int(self._dwell_time_sum):.3e}", "dwelltime intervals"],
                ["Layered mode on?", 'yes' if self.layered_mode else 'no', ""],
                ["Number of eff. layers", self.eff_layers, ""],
                ["Number of instructions", N_tot, ""],
                ["Deepest point", f"{self.get_deepest_point(micrometres=True):.5f}", "μm"],
                ["Shallowest point", f"{self.get_shallowest_point(micrometres=True):.5f}", "μm"],
            ]
            return items
        else:
            return [["has run?", False, "bool"], ]

    def _generate_points(self) -> None:
        t = time.time()
        layer_steps: int = int(self.setup.convert_depth_to_dwelltime_steps(self.layer_thickness))
        scan_points = np.array([p for p in self.pointscanner], dtype=int)
        print(f"    Generated {len(scan_points):d} scan points.", f"[T={time.time() - t:.3f}s]")
        depth_steps = np.array([self.depthmapper.query_depth(x, y) for x, y in scan_points], dtype=int)
        depth_mask = np.where(depth_steps > 1e-4)
        depth_steps = depth_steps[depth_mask]
        scan_points = scan_points[depth_mask]
        print("    Created discretized depth-map.", f"[T={time.time() - t:.3f}s]")
        self._dwell_time_sum = int(np.sum(depth_steps, dtype=np.int64))  # type required here to prevent overflow.
        self._depth_map = {tuple(scan_points[i, :]): depth_steps[i] for i in range(len(scan_points))}
        print("    Created dict.", f"[T={time.time() - t:.3f}s]")

        self.eff_layers = ceil(np.max(depth_steps) / layer_steps)
        print(f"    Splitting into {self.eff_layers:d} layers...")
        _dwell_time_sum_check: np.int64 = np.int64(0)
        # Process all the layers (plus one extra, just to make sure, that the last one never contains points :)
        # TODO: parallel-process all layers?

        # print(f"      Processing layer 0000/{self.eff_layers: 4d}=000%", end='')
        for i in range(self.eff_layers + 1):
            print("\r" + f"      Processing layer {i: 4d}/{self.eff_layers: 4d}={round(100 * i / self.eff_layers):3d}%",
                  end='')
            layered_depths = depth_steps - i * layer_steps
            # ok, which points do we still need to mill?
            mask = np.where(layered_depths > 1e-4)
            # print(f" with {len(mask[0]): 6d} points", end='')
            if len(mask[0]) > 0:
                layered_depths[np.where(layered_depths > layer_steps)] = layer_steps
                # Do some asserts for debugging. Warning: these make the code noticeable slower!
                if self.debug:
                    assert np.max(layered_depths[mask]) <= layer_steps
                    assert np.min(layered_depths[mask]) > 0
                _dwell_time_sum_check += np.sum(layered_depths[mask])
                # Collect and reformat data
                v = np.array([
                    scan_points[mask, 0][0], scan_points[mask, 1][0],  # coords
                    layered_depths[mask],  # Depths to be milled on this layer
                    [max((i - 1) * layer_steps, 0), ] * len(mask[0])  # Previous layer depth
                ], dtype=int)
                # This numpy magic quickly turns the data into the desired format:
                #  [[x, y, Depths to be milled on this layer, Previous layer depth], ...]
                self.list_of_instructions.extend(np.rot90(np.reshape(v, [4, len(mask[0])]))[::-1])
            # print(f" [T={time.time() - t:05.3f}s]", end='')
        print("")

        # Do some sanity checks. These might take a few secs, so you can disable them to safe some time.
        if self.debug:
            print("    Checking results...")
            assert len(mask[0]) == 0, \
                "Internal programming error! There are points in layers beyond the calculated maximum."

            assert _dwell_time_sum_check == self._dwell_time_sum, \
                f"Internal programming error! The total write time does not match! " + \
                f"({_dwell_time_sum_check} vs {self._dwell_time_sum}"
            _dwell_time_sum_check2: np.int64 = np.sum([self.list_of_instructions[i][2]
                                                       for i in range(len(self.list_of_instructions))],
                                                      dtype=np.int64)
            assert _dwell_time_sum_check2 == self._dwell_time_sum, \
                f"Internal programming error! The total write time does not match! " + \
                f"({_dwell_time_sum_check2} vs {self._dwell_time_sum}"

        print("    Done generating stream.", f"Total time for this step: {time.time() - t:.3f}s")
