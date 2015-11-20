# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

'''
bl_info = {
    "name": "Torus Knots",
    "author": "Marius Giurgi, testscreenings",
    "version": (0, 2),
    "blender": (2, 76, 0),
    "location": "View3D > Add > Curve",
    "description": "Adds many types of (torus) knots",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Curve/Torus_Knot",
    "category": "Add Curve"}
'''

##------------------------------------------------------------
#### import modules
import bpy
from bpy.props import *
from math import sin, cos, pi
from math import *
from mathutils import *
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from random import random

DEBUG = False

# greatest common denominator
def gcd(a, b):
    if b == 0: 
        return a
    else:
        return gcd(b, a % b)


########################################################################
####################### Knot Definitions ###############################
########################################################################
def Torus_Knot(self, linkIndex=0):
    p = self.torus_p # revolution count (around the torus center)
    q = self.torus_q # spin count (around the torus tube)

    N = self.torus_res # curve resolution (number of control points)

    # use plus options only when they are enabled
    if self.options_plus:
        u = self.torus_u # p multiplier
        v = self.torus_v # q multiplier
        h = self.torus_h # height (scale along Z)
        s = self.torus_s # torus scale (radii scale factor)
    else: # don't use plus setings
        u = 1
        v = 1
        h = 1
        s = 1

    R = self.torus_R * s # major radius (scaled)
    r = self.torus_r * s # minor radius (scaled)
    
    # number of decoupled links when (p,q) are NOT co-primes
    links = gcd(p,q) # = 1 when (p,q) are co-primes
    
    # parametrized angle increment (cached outside of the loop for performance)
    # NOTE: the total angle is divided by number of decoupled links to ensure 
    #       the curve does not overlap when (p,q) are not co-primes
    da = 2*pi/links/(N-1) 

    # link phase : each decoupled link is phased equally around the torus center
    # NOTE: linkIndex value is in [0, links-1]
    linkPhase = 2*pi/q * linkIndex # = 0 when there is just ONE link
        
    # user defined phasing
    if self.options_plus:
        rPhase = self.torus_rP # user defined revolution phase
        sPhase = self.torus_sP # user defined spin phase
    else:
        rPhase = 0
        sPhase = 0

    rPhase += linkPhase # total revolution phase of the current link

    if DEBUG:
        print("")
        print("Link: %i of %i" % (linkIndex, links))
        print("gcd = %i" % links)
        print("p = %i" % p)
        print("q = %i" % q)
        print("link phase = %.2f deg" % (linkPhase * 180/pi))
        print("link phase = %.2f rad" % linkPhase)

    # flip directions ?
    if self.flip_p: p*=-1
    if self.flip_q: q*=-1

    # create the 3D point array for the current link
    newPoints = []
    for n in range(N-1):
        # t = 2*pi / links * n/(N-1) with: da = 2*pi/links/(N-1) => t = n * da
        t = n * da
        theta = p*t*u + rPhase # revolution angle
        phi   = q*t*v + sPhase # spin angle

        x = (R + r*cos(phi)) * cos(theta)
        y = (R + r*cos(phi)) * sin(theta)
        z = r*sin(phi) * h

        # append 3D point 
        # NOTE : the array is adjusted later as needed to 4D for POLY and NURBS
        newPoints.append([x,y,z]) 

    return newPoints


##------------------------------------------------------------
# calculates the matrix for the new object
# depending on user pref
def align_matrix(context):
    loc = Matrix.Translation(context.scene.cursor_location)
    obj_align = context.user_preferences.edit.object_align
    if (context.space_data.type == 'VIEW_3D' and obj_align == 'VIEW'):
        rot = context.space_data.region_3d.view_matrix.to_3x3().inverted().to_4x4()
    else:
        rot = Matrix()
    align_matrix = loc * rot
    return align_matrix

# sets BEZIER handles to auto
def setBezierHandles(obj, mode = 'AUTOMATIC'):
    scene = bpy.context.scene
    if obj.type != 'CURVE':
        return
    scene.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=True)
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.handle_type_set(type=mode)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=True)

# get array of vert coordinates according to spline type
def vertsToPoints(Verts, splineType):
    # main vars
    vertArray = []

    # array for BEZIER spline output (V3)
    if splineType == 'BEZIER':
        for v in Verts:
            vertArray += v

    # array for non-BEZIER output (V4)
    else:
        for v in Verts:
            vertArray += v
            if splineType == 'NURBS':
                vertArray.append(1) # for NURBS w=1
            else: # for POLY w=0
                vertArray.append(0)

    return vertArray

# create new CurveObject from vertarray and splineType
# def createCurve(vertArray, self, align_matrix):
    # something

##------------------------------------------------------------
# Main Function
def create_torus_knot(self, context):
    # pick a name based on (p,q) parameters
    aName = "Torus Knot %i x %i" % (self.torus_p, self.torus_q)
    
    # create curve
    curve_data = bpy.data.curves.new(name=aName, type='CURVE')
    
    # setup materials to be used for the links
    if self.use_colors:
        addLinkColors(self, curve_data)

    # create torus knot link(s)
    if self.multiple_links:
        links = gcd(self.torus_p, self.torus_q);
    else:
        links = 1;

    for l in range(links):
        # get vertices for the current link
        verts = Torus_Knot(self, l)
    
        # output splineType 'POLY' 'NURBS' or 'BEZIER'
        splineType = self.outputType    
        
        # turn verts into proper array (based on spline type)
        vertArray = vertsToPoints(verts, splineType)

        # create spline from vertArray (based on spline type)
        spline = curve_data.splines.new(type=splineType)
        if splineType == 'BEZIER':
            spline.bezier_points.add(int(len(vertArray)*1.0/3-1))
            spline.bezier_points.foreach_set('co', vertArray)
        else:
            spline.points.add(int(len(vertArray)*1.0/4 - 1))
            spline.points.foreach_set('co', vertArray)
            spline.use_endpoint_u = True

        # set curve options
        spline.use_cyclic_u = True
        spline.order_u = 4

        # set a color per link
        if self.use_colors:
            spline.material_index = l

    curve_data.dimensions = '3D'

    # create surface ?
    if self.geo_surface:
        curve_data.bevel_depth = self.geo_bDepth
        curve_data.bevel_resolution = self.geo_bRes
        curve_data.fill_mode = 'FULL'
        curve_data.extrude = self.geo_extrude
        #curve_data.offset = self.geo_width # removed, somehow screws things up all of a sudden
        curve_data.resolution_u = self.geo_res

    # new_obj = object_data_add(context, curve_data, operator=self)
    new_obj = bpy.data.objects.new(aName, curve_data)

    # set object in the scene
    scene = bpy.context.scene
    scene.objects.link(new_obj) # place in active scene
    new_obj.select = True # set as selected
    scene.objects.active = new_obj  # set as active
    new_obj.matrix_world = self.align_matrix # apply matrix

    # set BEZIER handles
    if splineType == 'BEZIER':
        setBezierHandles(new_obj, self.handleType)

    return

# Create materials to be assigned to each TK link 
def addLinkColors(self, curveData):
    # some predefined colors for torus knot chained links
    colors = []
    colors += [ [0.0, 0.0, 1.0] ]
    colors += [ [0.0, 1.0, 0.0] ]
    colors += [ [1.0, 0.0, 0.0] ]
    colors += [ [1.0, 1.0, 0.0] ]
    colors += [ [0.0, 1.0, 1.0] ]
    colors += [ [1.0, 0.0, 1.0] ]

    me = curveData
    mat_offset = len(me.materials)
    mat_count = gcd(self.torus_p, self.torus_q)
    mats = []
    for i in range(mat_count):
        matName = "TorusKnot-Link-%i" % i
        matListNames = bpy.data.materials.keys()
        if matName not in matListNames:
            print("Creating new material : %s" % matName)
            mat = bpy.data.materials.new(matName)
            if self.options_plus and self.random_colors:
                mat.diffuse_color = random(), random(), random()
            else:
                cID = i % (len(colors))
                mat.diffuse_color = colors[cID]
                mat.diffuse_color.s = 0.75
        else:
            print("Material %s already exists" % matName)
            mat = bpy.data.materials[matName]
        
        if self.options_plus:
            mat.diffuse_color.s = self.saturation
        me.materials.append(mat)


class torus_knot_plus(bpy.types.Operator, AddObjectHelper):
    """"""
    bl_idname = "curve.torus_knot_plus"
    bl_label = "Torus Knot ++"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    bl_description = "Adds many types of knots"

    def mode_update_callback(self, context):
        # keep the reciprocal radii sets (R,r)/(iR,eR) in sync
        if self.mode == 'EXT_INT':
            self.torus_eR = self.torus_R + self.torus_r
            self.torus_iR = self.torus_R - self.torus_r

    # align_matrix for the invoke
    align_matrix = None

    #### GENERAL options
    options_plus = BoolProperty(
                name="plus options",
                default=False,
                description="Show more options (the plus part)")

    #### COLOR options
    use_colors = BoolProperty(
                name="Use Colors",
                default=False,
                description="Show torus links in colors")

    random_colors = BoolProperty(
                name="Randomize Colors",
                default=False,
                description="Randomize link colors")

    saturation = FloatProperty(
                name="Saturation",
                default=0.75,
                min=0.0, max=1.0,
                description="Color saturation")

    #### SURFACE Options
    geo_surface = BoolProperty(
                name="Surface",
                default=True,
                description="Create surface.")

    geo_bDepth = FloatProperty(
                name="Bevel Depth",
                default=0.02,
                min=0, soft_min=0,
                description="Bevel Depth")

    geo_bRes = IntProperty(
                name="Bevel Resolution",
                default=2,
                min=0, soft_min=0,
                max=5, soft_max=5,
                description="Bevel Resolution")

    geo_extrude = FloatProperty(
                name="Extrude",
                default=0.0,
                min=0, soft_min=0,
                description="Amount of curve extrusion.")

    geo_res = IntProperty(
                name="Segment Resolution",
                default=12,
                min=1, soft_min=1,
                description="Curve Subdivisions per segment.")

    #### TORUS KNOT Options
    torus_p = IntProperty(
                name="p",
                default=2,
                min=1, soft_min=1,
                description="Number of REVOLUTIONs around the torus hole before closing the knot.")
    
    torus_q = IntProperty(
                name="q",
                default=3,
                min=1, soft_min=1,
                description="Number of SPINs through the torus hole before closing the knot.")
 
    flip_p = BoolProperty(
                name="Flip p",
                default=False,
                description="Flip REVOLUTION direction")

    flip_q = BoolProperty(
                name="Flip q",
                default=False,
                description="Flip SPIN direction")

    multiple_links = BoolProperty(
                name="Multiple Links",
                default=True,
                description="Generate ALL links or just ONE when q and q are not co-primes.")

    torus_u = IntProperty(
                name="p multiplier",
                default=1,
                min=1, soft_min=1,
                description="p multiplier")

    torus_v = IntProperty(
                name="q multiplier",
                default=1,
                min=1, soft_min=1,
                description="q multiplier")

    torus_rP = FloatProperty(
                name="Revolution Phase",
                default=0.0,
                min=0.0, soft_min=0.0,
                description="Phase revolutions by this radian amount.")

    torus_sP = FloatProperty(
                name="Spin Phase",
                default=0.0,
                min=0.0, soft_min=0.0,
                description="Phase spins by this radian amount.")

    #### TORUS DIMENSIONS options
    mode = bpy.props.EnumProperty(
                name="Torus Dimensions",
                items=(("MAJOR_MINOR", "Major/Minor",
                        "Use the major/minor radii for torus dimensions"),
                       ("EXT_INT", "Exterior/Interior",
                        "Use the exterior/interior radii for torus dimensions")),
                update=mode_update_callback)

    torus_R = FloatProperty(
                name="Major Radius",
                min=0.00, max=100.0, 
                # soft_min=1, soft_max=1,
                default=1.0,
                subtype='DISTANCE',
                unit='LENGTH',
                description="Radius from the torus origin to the center of the cross section")

    torus_r = FloatProperty(
                name="Minor Radius",
                min=0.00, max=100.0, 
                # soft_min=1, soft_max=1,
                default=.25,
                subtype='DISTANCE',
                unit='LENGTH',
                description="Radius of the torus' cross section")

    torus_iR = FloatProperty(
                name="Interior Radius",
                min=0.00, max=100.0, 
                # soft_min=1, soft_max=1,
                default=.75,
                subtype='DISTANCE',
                unit='LENGTH',
                description="Total interior radius of the torus")

    torus_eR = FloatProperty(
                name="Exterior Radius",
                min=0.00, max=100.0, 
                # soft_min=1, soft_max=1,
                default=1.25,
                subtype='DISTANCE',
                unit='LENGTH',
                description="Total exterior radius of the torus")

    torus_s = FloatProperty(
                name="Scale",
                min=0.01, max=100.0, 
                # soft_min=1, soft_max=1,
                default=1.00,
                description="Scale factor to multiply the radii.")

    torus_h = FloatProperty(
                name="Height",
                default=1.0,
                min=0.0, max=100.0,
                description="Scale along Z")

    #### CURVE options
    torus_res = IntProperty(
                name="Resolution",
                default=100,
                min=3, soft_min=3,
                description='Number of control vertices')

    SplineTypes = [
                ('POLY', 'Poly', 'POLY'),
                ('NURBS', 'Nurbs', 'NURBS'),
                ('BEZIER', 'Bezier', 'BEZIER')]

    outputType = EnumProperty(
                name="Output splines",
                description="Type of splines to output",
                default='BEZIER',
                items=SplineTypes)

    bezierHandles = [
                ('VECTOR', 'Vector', 'VECTOR'),
                ('AUTOMATIC', 'Auto', 'AUTOMATIC')]

    handleType = EnumProperty(
                name="Handle type",
                description="Bezier handle type",
                default='AUTOMATIC',
                items=bezierHandles)

    adaptive_resolution = BoolProperty(
                name="Adaptive Resolution",
                default=False,
                description="Auto adjust curve resolution based on knot length")

    ##### DRAW #####
    def draw(self, context):
        layout = self.layout

        # extra parameters toggle
        layout.prop(self, 'options_plus', text="Extra Options")

        # TORUS KNOT Parameters
        col = layout.column()
        col.label(text="Torus Knot Parameters:")
        box = layout.box()
        row = box.row()
        row.column().prop(self, 'torus_p')
        row.column().prop(self, 'flip_p')
        row = box.row()
        row.column().prop(self, 'torus_q')
        row.column().prop(self, 'flip_q')
        box.prop(self, 'multiple_links')
        
        if self.options_plus:
            box = box.box()
            box.prop(self, 'torus_u')
            box.prop(self, 'torus_v')
            box.prop(self, 'torus_rP')
            box.prop(self, 'torus_sP')

        # TORUS DIMENSIONS options
        col = layout.column(align=True)
        col.label(text="Torus Dimensions:")
        box = layout.box()
        col = box.column(align=True)
        col.row().prop(self, "mode", expand=True)

        if self.mode == 'MAJOR_MINOR':
            col = box.column(align=True)
            col.prop(self, "torus_R", text="Major Radius")

            col = box.column(align=True)
            col.prop(self, "torus_r", text="Minor Radius")
        else: # EXTERIOR-INTERIOR
            col = box.column(align=True)
            col.prop(self, "torus_eR", text="Exterior Radius")

            col = box.column(align=True)
            col.prop(self, "torus_iR", text="Interior Radius")

        if self.options_plus:
            box = box.box()
            box.prop(self, 'torus_s')
            box.prop(self, 'torus_h')

        # CURVE options
        col = layout.column(align=True)
        col.label(text="Curve Options:")
        box = layout.box()

        col = box.column()
        col.label(text="Output Curve Type:")
        col.row().prop(self, 'outputType', expand=True)

        depends=box.column()
        depends.prop(self, 'torus_res', text="Curve Resolution")
        # deactivate the "curve resolution" if "adaptive resolution" is enabled
        depends.enabled = not (self.options_plus and self.adaptive_resolution)

        box.prop(self, 'geo_res')

        if self.options_plus:
            box = box.box()
            box.prop(self, 'adaptive_resolution')
    
        # SURFACE options
        col = layout.column()
        col.label(text="Geometry Options:")
        box = layout.box()
        box.prop(self, 'geo_surface')
        if self.geo_surface:
            box.prop(self, 'geo_bDepth')
            box.prop(self, 'geo_bRes')
            box.prop(self, 'geo_extrude')
           
        # COLOR options
        col = layout.column()
        col.label(text="Color Options:")
        box = layout.box()
        box.prop(self, 'use_colors')
        if self.use_colors and self.options_plus:
            box = box.box()
            box.prop(self, 'random_colors')
            box.prop(self, 'saturation')

        # TRANSFORM options
        col = layout.column()
        col.label(text="Transform Options:")
        box = col.box()
        box.prop(self, 'location')
        box.prop(self, 'rotation')

    ##### POLL #####
    @classmethod
    def poll(cls, context):
        return context.scene != None

    ##### EXECUTE #####
    def execute(self, context):
        if self.mode == 'EXT_INT':
            # adjust reciprocal radii (R,r) <-> (eR,iR)
            self.torus_R = (self.torus_eR + self.torus_iR)*0.5
            self.torus_r = (self.torus_eR - self.torus_iR)*0.5

        if self.options_plus and self.adaptive_resolution:
            # adjust curve resolution automatically based on (p,q,R,r) values
            p = self.torus_p
            q = self.torus_q
            R = self.torus_R
            r = self.torus_r
            links = gcd(p,q)
            # get an approximate TK length 
            maxTKLen = 2*pi*sqrt(p*p*(R+r)*(R+r) + q*q*r*r) # upper bound approximation
            minTKLen = 2*pi*sqrt(p*p*(R-r)*(R-r) + q*q*r*r) # lower bound approximation
            avgTKLen = (minTKLen + maxTKLen)/2 # average approximation
            if DEBUG: print("Approximate average TK length = %.2f" % avgTKLen)
            self.torus_res = avgTKLen/links * 8 # x N factor = control points per unit length 

        # turn off undo
        undo = bpy.context.user_preferences.edit.use_global_undo
        bpy.context.user_preferences.edit.use_global_undo = False

        # create the curve
        create_torus_knot(self, context)

        # restore pre operator undo state
        bpy.context.user_preferences.edit.use_global_undo = undo

        return {'FINISHED'}

    ##### INVOKE #####
    def invoke(self, context, event):
        # store creation_matrix
        self.align_matrix = align_matrix(context)
        self.execute(context)

        return {'FINISHED'}