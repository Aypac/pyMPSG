# -*- coding: utf-8 -*-

"""
Typical use-case showcasing the SummingCombiner to combine multiple basic shapes.
Additionally, showcasing how I log my settings etc to keep track of the settings used to generate a .str file.

@author: René Vollmer
"""
# *** NOTE: import any required libraries before the after the initialization or after the `get_table` command
#           of the VariableTracker!


import os
import codecs
from pyMPSG import pointscanner, depthmapper, helper, StreamGenerator, Setup, Streamfile

# You need the SetupVariableTracker installed for this example:
#     pip install git+https://github.com/Aypac/SetupVariableTracker
from SetupVariableTracker import SetupVariableTracker, Timekeeper

tk = Timekeeper()

output_folder: str = r"arrays/"

vtrack = SetupVariableTracker(locals())

##################################################
"""
All parameters defined below will end up in the summary list.
All parameters important for the outcome should be defined here, so that
documentation of the same exists next to the generated files. 
"""
##################################################

# sputter rate in um**3 / (us * nA)
# You'll need to calibrate this value for your acceleration voltage, ion species, and substrate.
mu: float = 7.5e-6  # Approx. value for 30keV, diamond, Ge+ ions

# Beamcurrent in nA
I_B: float = 9.4

# x-y step size in um
#   recommended to use ca. 1/5-1/3 of effective beam size
#   Smaller values unnecessarily increase script run time and file size significantly
ds: float = 0.1

# max depth per layer in um, -1 for all at once
#   recommended to use ca. 1/5 of effective beam size
#   Smaller values unnecessarily increase file size
dz: float = 0.075

center: tuple = (0, 0)

zoom: int = int(3500)
##################################################
# Number of holes in x and y
size_x: int = 5
size_y: int = 3

# Spacing of holes in x and y in µm
spacing_x: float = 5
spacing_y: float = 5

# Radius of the holes in µm
radius_hole: float = 0.5

# Depth of the holes in µm
depth_hole: float = 1
##################################################

# Create a summary of all newly defined variables
summary_content = vtrack.get_table(locals(), sort=True)
summary_content += '\n\n'
del vtrack

layered: bool = (dz > 0)

# Prepare "Setup" - i.e. the settings for the machine and substrate
mill_setup = Setup(mu=mu, I_B=I_B, ds=ds, zoom=3500)

# Adjust the maximal dwell time to the desired maximal layer height
if layered:
    dz_s = f"{int(dz * 1e3):d}nm"
else:
    dz_s = 'inf'
summary_content += '\n\n' + mill_setup.summary() + '\n\n'

# Name of the sub-folder in which the results will be stored
descriptor_str: str = f"r={radius_hole:.2f}um"
descriptor_str += f"_sx={spacing_x:.2f}um"
descriptor_str += f"_sy={spacing_y:.2f}um"
descriptor_str += f"_nx={size_x:.2f}um"
descriptor_str += f"_ny={size_y:.2f}um"
descriptor_str += f"_I={mill_setup.I_B:.2f}nA"
descriptor_str += f"_ds={ds:0.3f}"
descriptor_str += f"_dz=" + dz_s
descriptor_str += f"_zoom={zoom:d}x"
if center != (0, 0):
    descriptor_str += f"_xy=({center[0]:.1f},{center[1]:.1f})"

# Where to put the results?
output_folder += descriptor_str

# Create output-folder if required
if not os.path.exists(output_folder + '/images/'):
    os.makedirs(output_folder + '/images/')
else:
    print("------\n> Warning: overwriting previous files!\n------")

tk.touch(slot='Pattern gen')

# Specify the object to pattern and the rastering method
dms = []
for i in range(size_x):
    for j in range(size_y):
        p = (center[0] + (i - size_x / 2 + 0.5) * spacing_x, center[1] + (j - size_y / 2 + 0.5) * spacing_y)
        dms.append(depthmapper.Circle(r=radius_hole, depth=depth_hole, center=p, setup=mill_setup))
dm = depthmapper.SummingCombiner(dms)
ps = pointscanner.ConcentricSquares(width=size_x * spacing_x + radius_hole, height=size_y * spacing_y + radius_hole,
                                    center=center, inside_out=True, setup=mill_setup)

# Generate the streamfile
sg = StreamGenerator(pointscanner=ps, depthmapper=dm, setup=mill_setup, layer_thickness=dz)
sf = Streamfile(sg)
print(f"> Generating and writing str files [Intermediate total runtime: {tk.total_elapsed_time()}]")
sf.write_file(output_folder + '/instructions')

# Generate and save summary
summary_content += '\n\n' + sf.summary() + '\n\n'
print('> Summaries: \n' + '+-' * 38 + '+\n' + summary_content + '\n' + '+-' * 38 + '+\n')

with codecs.open(output_folder + '/summary.txt', 'w', 'utf-8') as f:
    f.write(summary_content)
    f.flush()

# Takes a long time, for production can be turned off
render: bool = True
if render:
    print(f"> Creating plot [Intermediate total runtime: {tk.total_elapsed_time()}]")
    # sf.plot_result(display=True, micrometres=True, all_layers=True)
    sg.plot_result(display=False, micrometres=True, all_layers=False, whole_field=False)
    print(f"> Generate some more plots and save to disk [Intermediate total runtime: {tk.total_elapsed_time()}]")
    sg.save_plots(out_folder=output_folder + '/images/', display=False, micrometres=True, all_layers=False)

# Can zip at the end for easier transfer to the machine
zip: bool = True
if zip:
    print('> Zipping results.', end='')
    helper.zip_folder(output_folder)
    print(f" [Took {tk.diff_elapsed_time()}]")

print(f"\n> All done. Have a nice day! [Total runtime: {tk.total_elapsed_time()}]")
print("Find the results in ", output_folder)
