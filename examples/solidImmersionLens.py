# -*- coding: utf-8 -*-
"""
This can be used to generate solid immersion lenses, as in
"""

from pyMPSG import pointscanner, depthmapper, StreamGenerator, Setup, Streamfile

### Machine and patterning settings
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

### Structure settings
# Depth to recess the central dome from the substrate surface in µm
premill_depth: float = 0.1

# Central dome radius in µm
dome_radius: float = 5

# Central dome sag (radius at lowest point) in µm
#  i.e. for a full half sphere set dome_sag = dome_radius
dome_sag: float = dome_radius

# Trench width around the central dome in µm
recess_clearance_distance: float = 1

# Width/Length of the slope going from the trench up to the surface of the substrate in µm
slope_length: float = 2

# Prepare "Setup" - i.e. the settings for the machine and substrate
machine = Setup(mu=mu, I_B=I_B, ds=ds, zoom=3500)

# Specify the object to pattern and the rastering method
dm = depthmapper.FullRecessedDome(premill_depth=premill_depth, dome_radius=dome_radius, dome_sag=dome_sag,
                                  recess_clearance_distance=recess_clearance_distance, slope_length=slope_length,
                                  setup=machine)
ps = pointscanner.Spiral(radius=dm.r_o, inside_out=True, setup=machine)

# Generate the streamfile
sg = StreamGenerator(pointscanner=ps, depthmapper=dm, setup=machine, layer_thickness=dz)
sf = Streamfile(sg)
sf.write_file('instructions_sil')
