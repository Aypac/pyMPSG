# Python Micro Pattern Stream Generator (pyMPSG) library

Generate streamfiles (.str) for patterning on e.g. FEI dualbeam focussed ion beam (FIB) milling machines,
such as Helios G4Cx or Helios 650.  This allows for generating arbitrary¹ 2.5D shapes, such as domes, cones,
markers, etc, as well as combinations thereof. Allowing for a wide range of complex patterns.

This should also be usable for electron- or ion-beam induced deposition (EBID/IBID). Extension to patterning text
and bitmaps should be fairly easy (please open an issue if you are interested in details).

I developed this at the [quantum technologies department at TNO](https://www.tno.nl/nl/digitaal/semicon-quantum/quantumtechnologie/)
and now publish it with their consent. If you are interested to have this technique applied to you chip², please reach
out to diamond-devices@tno.nl

_¹ within the limits of the machine_  
_² e.g. for [solid-immersion lenses around single color centers](https://ecosystem.qu-pilot.eu/technical-marketplace/product/?action=view&id_form=2&id_form_data=96)_

## Installation
`pip install pyMPSG`

## Minimal usage example

``` python
from pyMPSG import pointscanner, depthmapper, StreamGenerator, Setup, Streamfile


# Prepare "Setup" - ie. the settings for the machine and substrate
machine = Setup(mu=7.5e-6, I_B=9.4, ds=0.1, zoom=3500)

# Specify the object to pattern and the rastering method
dm = depthmapper.Circle(r=5, depth=1, setup=machine)
ps = pointscanner.Spiral(radius=dm.r_o, inside_out=True, setup=machine)

# Generate the streamfile
sg = StreamGenerator(pointscanner=ps, depthmapper=dm, setup=machine, layer_thickness=0.05)
sf = Streamfile(sg)
sf.write_file('instructions')
```

More usage examples and explanation can be found in the [examples folder](https://github.com/Aypac/pyMPSG/tree/master/examples).

## Reference and Citing

Based on the python2 script provided in:  
[_Mohammad Jamali, Ilja Gerhardt, Mohammad Rezai, Karsten Frenner, Helmut Fedder, Jörg Wrachtrup; Microscopic diamond solid-immersion-lenses fabricated around single defect centers by focused ion beam milling. Rev. Sci. Instrum. 1 December 2014; 85 (12): 123703._](https://doi.org/10.1063/1.4902818)

If you use this code in your work, please cite it with its DOI: [XXX]().

BibTeX:
```BibTeX
@misc{https://doi.org/,
  doi = {},
  url = {https://github.com/Aypac/pyMPSG},
  author = {René Vollmer},
  keywords = {FOS: Physical sciences, Publication, Dataset, EBID, IBID},
  language = {en},
  title = {pyMPSG},
  publisher = {},
  year = {2025}
}
```

## Disclaimer
All mentioned names (such as NanoBuilder, FEI, Helios, ...) are brands and/or registered trademarks of their respective
owners (e.g. ThermoFisher). There is no affiliation with any of these brands or companies.
For further disclaimers, please read the license file.


## Copyright 2025 René Vollmer

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at [apache.org](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.