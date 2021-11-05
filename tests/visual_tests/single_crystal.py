import numpy as np
from xrd_simulator.polycrystal import Polycrystal
from xrd_simulator.mesh import TetraMesh
from xrd_simulator.phase import Phase
from xrd_simulator.detector import Detector
from xrd_simulator.beam import Beam
from xrd_simulator.motion import RigidBodyMotion
from xfab import tools
from scipy.signal import convolve

np.random.seed(2)

pixel_size = 75.
detector_size = pixel_size*1024
detector_distance = 142938.28756189224
d0 = np.array([detector_distance,   -detector_size/2.,  -detector_size/2.])
d1 = np.array([detector_distance,    detector_size/2.,  -detector_size/2.])
d2 = np.array([detector_distance,   -detector_size/2.,   detector_size/2.])

detector = Detector( pixel_size, d0, d1, d2 )

r = (detector_size/10.)
mesh = TetraMesh.generate_mesh_from_levelset(
    level_set = lambda x: x[0]*x[0] + x[1]*x[1] + x[2]*x[2] - r**2,
    bounding_radius = 1.1*r, 
    cell_size = 0.27*r )
print('nelm:', mesh.number_of_elements)

unit_cell = [4.926, 4.926, 5.4189, 90., 90., 120.]
sgname = 'P3221' # Quartz
phases = [Phase(unit_cell, sgname)]
B0 = tools.epsilon_to_b( np.zeros((6,)), unit_cell )
eB = np.array( [ B0 for _ in range(mesh.number_of_elements)] )

grain_avg_rot = np.max( [np.radians(1.0), np.random.rand() * 2 * np.pi] )
euler_angles  = grain_avg_rot  + np.random.normal(loc=0.0, scale=np.radians(0.05), size=(mesh.number_of_elements, 3) ) 
eU = np.array( [tools.euler_to_u(ea[0], ea[1], ea[2]) for ea in euler_angles] )
ephase = np.zeros((mesh.number_of_elements,)).astype(int)
polycrystal = Polycrystal(mesh, ephase, eU, eB, phases)

w = detector_size/2. # full field beam
beam_vertices = np.array([
    [-detector_distance, -w, -w ],
    [-detector_distance,  w, -w ],
    [-detector_distance,  w,  w ],
    [-detector_distance, -w,  w ],
    [ detector_distance, -w, -w  ],
    [ detector_distance,  w, -w  ],
    [ detector_distance,  w,  w  ],
    [ detector_distance, -w,  w  ]])
wavelength = 0.285227
xray_propagation_direction = np.array([1,0,0]) * 2 * np.pi / wavelength
polarization_vector = np.array([0,1,0])
beam = Beam(beam_vertices, xray_propagation_direction, wavelength, polarization_vector)
d
rotation_angle = 0.5*np.pi/180.
rotation_axis = np.array([0,0,1])
translation = np.array([0,0,0])
motion  = RigidBodyMotion(rotation_axis, rotation_angle, translation)

polycrystal.diffract( beam, detector, motion )
pixim = detector.render(frame_number=0)

import matplotlib.pyplot as plt
from scipy.signal import convolve
pixim[ pixim<=0 ] = 1
pixim = np.log(pixim)
plt.imshow(pixim , cmap='gray')
plt.title("Hits: "+str(len(detector.frames[0]) ))
plt.show()
