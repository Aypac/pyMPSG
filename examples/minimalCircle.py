# -*- coding: utf-8 -*-

from pyMPSG import pointscanner, depthmapper, StreamGenerator, Setup, Streamfile

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

# Prepare "Setup" - ie. the settings for the machine and substrate
machine = Setup(mu=mu, I_B=I_B, ds=ds, zoom=3500)

# Specify the object to pattern and the rastering method
dm = depthmapper.Circle(r=5, depth=1, setup=machine)
ps = pointscanner.Spiral(radius=dm.r_o, inside_out=True, setup=machine)


# Generate the streamfile
sg = StreamGenerator(pointscanner=ps, depthmapper=dm, setup=machine, layer_thickness=dz)
sf = Streamfile(sg)
sf.write_file('instructions_circle')