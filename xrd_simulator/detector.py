import numpy as np 
import matplotlib.pyplot as plt
from numpy.lib.utils import source
from xrd_simulator import utils
from scipy.interpolate import griddata

class Detector(object):

    """Represents a rectangular X-ray scattering flat area detection device.

    The detector can collect scattering as abstract objects and map them to frame numbers.
    Using a render function these abstract representation can be rendered into pixelated frames.
    The detector is described by a 3 x 3 geometry matrix whic columns contain vectors that attach
    to three of the four corners of the detector.

    Args:
        pixel_size (:obj:`float`): Pixel side length (square pixels) in units of microns.
        d0,d1,d2 (:obj:`numpy array`): Detector corner 3d coordinates ```shape=(3,)```. The origin of the detector
            is at d0.

    Attributes:
        pixel_size (:obj:`float`): Pixel side length (square pixels) in units of microns.
        d0,d1,d2 (:obj:`numpy array`): Detector corner 3d coordinates ```shape=(3,)```. The origin of the detector
            is at d0.
        frames (:obj:`list` of :obj:`list` of :obj:`scatterer.Scatterer`): Analytical diffraction patterns which
        zdhat,ydhat (:obj:`numpy array`): Detector basis vectors.
        normal (:obj:`numpy array`): Detector normal.
        zmax,ymax (:obj:`numpy array`): Detector width and height.
    """

    def __init__(self, pixel_size, d0, d1, d2 ):
        self.d0, self.d1, self.d2 = d0, d1, d2
        self.pixel_size = pixel_size
        self.zmax   = np.linalg.norm(self.d2-self.d0)
        self.ymax   = np.linalg.norm(self.d1-self.d0)
        self.zdhat  = (self.d2-self.d0 ) / self.zmax
        self.ydhat  = (self.d1-self.d0 ) / self.ymax
        self.normal = np.cross(self.zdhat, self.ydhat)
        self.frames = []

    def render(self, frame_number, lorentz=True, polarization=True, structure_factor=True):
        """Take a list of scatterers render to a pixelated pattern.

        Args:
            frame_number (:obj:`int`): Index of the frame in the :obj:`frames` list to be rendered.

        Returns:
            A pixelated frame as a (:obj:`numpy array`) with shape infered form the detector geometry and
            pixel size.

        NOTE: This function is meant to allow for overriding when specalised intensity models are to be tested.

        """
        frame = np.zeros( (int(self.zmax/self.pixel_size), int(self.ymax/self.pixel_size)) )
        for scatterer in self.frames[frame_number]:
            z0, z1, y0, y1, intensity = self.project( scatterer, full=True ) #TODO: move keyword full to controllable place
            if intensity is not None:
                #zd, yd = self.get_intersection( scatterer.scattered_wave_vector, scatterer.centroid )
                #if self.contains(zd,yd):
                #intensity = scatterer.volume
                if lorentz:
                    intensity = intensity * scatterer.lorentz_factor 
                if polarization:
                    intensity = intensity * scatterer.polarization_factor
                if structure_factor and scatterer.real_structure_factor is not None:
                    intensity = intensity * ( scatterer.real_structure_factor**2 + scatterer.imaginary_structure_factor**2 )
                #frame[int(zd/self.pixel_size), int(yd/self.pixel_size)] += intensity
                print(z0, z1, y0, y1)
                frame[z0:z1, y0:y1] += intensity
        return frame

    def project( self, scatterer, full=False ):
        #TODO: Consider moving bulk of this to utils.py
        #TODO: Fix weird prjections...
        if not full:
            zd, yd      = self.get_intersection( scatterer.scattered_wave_vector, scatterer.centroid )
            z0,z1,y0,y1 = int(zd/self.pixel_size), int(zd/self.pixel_size)+1, int(yd/self.pixel_size), int(yd/self.pixel_size)+1
            if self.contains(zd, yd):
                volume_intensity_weight = scatterer.volume
            else:
                volume_intensity_weight = None
        else:
            detector_intersection, clip_length = self.project_convex_hull(scatterer)

            zd = detector_intersection[:,0]
            yd = detector_intersection[:,1]
            points = np.array( [ zd, yd ] ).T/self.pixel_size
            values = clip_length

            minpix_zd = int(np.min(zd)/self.pixel_size)
            maxpix_zd = int(np.max(zd)/self.pixel_size)
            minpix_yd = int(np.min(yd)/self.pixel_size)
            maxpix_yd = int(np.max(yd)/self.pixel_size)
            
            if minpix_yd<0: minpix_yd=0
            elif minpix_yd>=int(self.ymax/self.pixel_size): minpix_yd = int(self.ymax/self.pixel_size)-1

            if maxpix_yd<0: maxpix_yd=0
            elif maxpix_yd>=int(self.ymax/self.pixel_size): maxpix_yd = int(self.ymax/self.pixel_size)-1

            if minpix_zd<0: minpix_zd=0
            elif minpix_zd>=int(self.zmax/self.pixel_size): minpix_zd = int(self.zmax/self.pixel_size)-1

            if maxpix_zd<0: maxpix_zd=0
            elif maxpix_zd>=int(self.zmax/self.pixel_size): maxpix_zd = int(self.zmax/self.pixel_size)-1

            steps = 3
            zz = np.linspace(minpix_zd, maxpix_zd, steps*(maxpix_zd-minpix_zd+1) )
            yy = np.linspace(minpix_yd, maxpix_yd, steps*(maxpix_yd-minpix_yd+1) )
            Z,Y = np.meshgrid(zz, yy, indexing='ij')
            xi = np.array( [Z.flatten(), Y.flatten()] ).T

            high_res_volume_intensity_weight = griddata(points, values, xi, method='linear', fill_value=0, rescale=False).reshape(Z.shape)

            volume_intensity_weight = np.zeros((high_res_volume_intensity_weight.shape[0]//steps, high_res_volume_intensity_weight.shape[1]//steps))
            for i in range(steps):
                volume_intensity_weight += high_res_volume_intensity_weight[i::steps, i::steps]
            volume_intensity_weight = volume_intensity_weight/ (steps**2)

            z0,z1,y0,y1 = minpix_zd, maxpix_zd+1, minpix_yd, maxpix_yd+1
            # import matplotlib.pyplot as plt
            # plt.imshow(volume_intensity_weight)
            # plt.title( "z0=" +str(z0)+"   z1="+str(z1)+"   y0="+str(y0)+"   y1="+str(y1) )
            # plt.show()

        return z0, z1, y0, y1, volume_intensity_weight

    def project_convex_hull( self, scatterer ):
        """Compute parametric projection of scattering region unto detector.

            NOTE: Mike Cyrus and Jay Beck. “Generalized two- and three-dimensional clipping”. (1978)
            (based on orthogonal equations: (p - e - t*r) . n = 0 )
        """
        #TODO: Consider moving bulk of this to utils.py
        vertices      = scatterer.convex_hull.points[ scatterer.convex_hull.vertices ]
        ray_direction = scatterer.scattered_wave_vector / np.linalg.norm( scatterer.scattered_wave_vector )
        plane_normals = scatterer.convex_hull.equations[:,0:3]
        plane_ofsets  = scatterer.convex_hull.equations[:,3].reshape(scatterer.convex_hull.equations.shape[0], 1)

        detector_intersection = np.zeros((vertices.shape[0],2))
        clip_length           = np.zeros((vertices.shape[0],))

        # for each vertex
        for i,e in enumerate( vertices ):  

            plane_points = -np.multiply( plane_ofsets, plane_normals ) 
            
            pe = plane_points-e
            n  = plane_normals 

            # find ine-plane intersect 
            t1 = np.sum( np.multiply(pe,n), axis=1 )
            t2 = np.dot( n, ray_direction ) 
            ti = t1/t2
            
            # Sort intersections as potential entry and exit points
            te = np.max( ti[t2<0] )
            tl = np.min( ti[t2>0] )

            zd, yd = self.get_intersection( ray_direction, source_point=e )
            clip_length[i] =  np.max([0, tl-te]) # safeguard against bad precision to avoid negative lengths
            assert tl-te>=-1e-7, str(tl-te)+"  "+str(t2)+"  "+str(ti)+"  "+str(te)+"  "+str(tl)
            detector_intersection[i,:] = [ zd, yd ]

        return detector_intersection, clip_length

    def get_intersection(self, ray_direction, source_point):
        """Get detector intersection in detector coordinates of singel a ray originating from source_point.

        Args:
            ray_direction (:obj:`numpy array`): Vector in direction of the X-ray propagation 
            source_point (:obj:`numpy array`): Origin of the ray.

        Returns:
            (:obj:`tuple`) zd, yd in detector plane coordinates.

        """
        #TODO: Consider moving this to utils.py and generalise for line and plane
        s = (self.d0 - source_point).dot(self.normal) / ray_direction.dot(self.normal)
        intersection =  source_point + ray_direction*s
        zd = np.dot( intersection - self.d0 , self.zdhat)
        yd = np.dot( intersection - self.d0 , self.ydhat)
        return zd, yd

    def contains(self, zd, yd):
        """Determine if the detector coordinate zd,yd lies within the detector bounds.

        Args:
            zd (:obj:`float`): Detector z coordinate
            yd (:obj:`float`): Detector y coordinate

        Returns:
            (:obj:`boolean`) True if the zd,yd is within the detector bounds.

        """
        return zd>=0 and zd<=self.zmax and yd>=0 and yd<=self.ymax

    def get_wrapping_cone(self, k, source_point):
        """Compute the cone around a wavevector such that the cone wrapps the detector corners.

        Args:
            k (:obj:`numpy array`): Wavevector forming the central axis of cone ´´´shape=(3,)´´´.
            source_point (:obj:`numpy array`): Origin of the wavevector ´´´shape=(3,)´´´.

        Returns:
            (:obj:`float`) Cone opening angle divided by two (radians), corresponding to a maximum bragg angle after
                which scattering will systematically miss the detector.

        """
        fourth_corner_of_detector = self.d2 + (self.d1 - self.d0[:])
        geom_mat = np.zeros((3,4))
        for i,det_corner in enumerate([self.d0,self.d1,self.d2,fourth_corner_of_detector]):
            geom_mat[:,i] = det_corner - source_point
        normalised_local_coord_geom_mat = geom_mat/np.linalg.norm(geom_mat, axis=0)
        cone_opening = np.arccos( np.dot(normalised_local_coord_geom_mat.T, k / np.linalg.norm(k) ) ) # These are two time Bragg angles        
        return np.max( cone_opening ) / 2.

