# -*- coding: utf-8 -*-
"""
Class Streamfile to conveniently turn the point lists and dwell times of a StreamGenerator into one or multiple*
streamfiles.

* there is a maximum length of streamfiles, which may necessitate splitting.
       This is also automatically handled by this class.

@author: René Vollmer
"""

import time
from math import ceil
from tabulate import tabulate

from .helper import ensure_file_ending, remove_file_ending
from .streamgenerator import StreamGenerator


# from mpl_toolkits.mplot3d import Axes3D
# import matplotlib.pyplot as plt


def map_string(vals: list) -> str:
    return f"{vals[2]:d} {vals[0]:d} {vals[1]:d}"


class Streamfile:
    stream_generator: StreamGenerator
    max_entries: int = int(8e6)
    use_multiprocessing = True

    def __init__(self, stream_generator: StreamGenerator, max_entries: int = 0):
        self.stream_generator = stream_generator
        if max_entries > 0:
            self.max_entries = max_entries
        # Mamimum number of entries per file
        assert self.max_entries > 0, "Number of maximum entries per file must be larger than zero!"
        if self.max_entries > int(8e6):
            print("Warning: this script has only been tested with a maximum of 8 million points." +
                  f"You set it to {self.max_entries:d}, which might result in large files and crash the software!")

    def _ensure_run(self):
        self.stream_generator.ensure_run()

    def summary(self) -> str:
        s = "Streamfile summary:\n"

        if self.stream_generator.has_run():
            p = self.get_number_of_required_parts()
            if p > 1:
                s = "Streamfiles summary:\n"

            items = self.stream_generator.get_summary_table()
            N_tot: int = self.stream_generator.get_number_of_instructions()
            items.append(
                ["Approx. total filesize", f"{N_tot * 16.8 * 1e-6:.2f}/{N_tot * 16.8 / 2 ** 20:.2f}", "MB/MiB"])
            items.append(["Number of .str files", p, '"file"'])

            s += tabulate(items, headers=['Parameter', 'Value', 'Unit'], tablefmt="rst")
        else:
            s += " > Has not been generated/executed yet!"

        return s

    def get_number_of_required_parts(self):
        self._ensure_run()
        return ceil(self.stream_generator.get_number_of_instructions() / self.max_entries)

    def get_text(self, part: int = 0) -> str:
        """
        :param part: If exceeding the maximum number of points for a single file,
                        use this to get the consecutive file-contents
        """
        self._ensure_run()
        t = time.time()
        max_part = self.get_number_of_required_parts()
        assert 0 <= part <= max_part, f"Indicate a valid part! Maximum is {max_part:d}, minimum is 0."

        N_tot: int = self.stream_generator.get_number_of_instructions()
        N_p: int = part * self.max_entries
        N: int = min(self.max_entries, N_tot - N_p)
        assert N > 0, "There are no points in this part!"

        print("    Generate text for streamfile.", f"[T={time.time() - t:.3f}s]")
        # Create file header
        s: str = f"s{self.stream_generator.setup.dac_bits:d}"
        if self.stream_generator.setup.time_res != 100:
            s += f",{self.stream_generator.setup.time_res:d}ns"
        s += f"\n{self.stream_generator.setup.repetitions:d}\n{N:d}\n"

        # Write all points of this part
        # Map & join seems to be the fastest option
        p = None
        mymap = None
        if self.use_multiprocessing:
            # from multiprocessing import Pool
            try:
                from multiprocessing.pool import ThreadPool as Pool
                p = Pool(8)
                mymap = p.map
            except ModuleNotFoundError:
                print("    Note: Consider installing multiprocessing to speed up.")
        if not mymap:
            mymap = map
        s += "\n".join(mymap(map_string, self.stream_generator.list_of_instructions[N_p:N_p + N]))
        if p and self.use_multiprocessing:
            p.close()
            p.join()
        print("    Done.", f"[T={time.time() - t:.3f}s]")

        return s + ' 0\n'

    def write_file(self, filename: str, part: int = -1) -> None:
        self._ensure_run()

        filename = remove_file_ending(filename, 'str')

        # iterate over parts
        max_part = self.get_number_of_required_parts()
        assert part == -1 or (0 <= part < max_part), \
            f"Indicate a valid part! Maximum is {max_part:d}, minimum is 0. Use -1 to generate all parts."
        for i in range(max_part):
            print(f"Info: Writing part {int(i + 1)}/{max_part}.")
            if part == -1 or part == i:
                s = self.get_text(part=i)

                fn = filename + f"_part{i:d}" if max_part > 1 else filename
                fn = ensure_file_ending(fn, 'str')

                with open(fn, 'w') as f:
                    f.write(s)
                    f.flush()
