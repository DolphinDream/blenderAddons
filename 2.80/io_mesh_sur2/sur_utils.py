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

# <pep8 compliant>

"""
Import and export SUR files

Used as a blender script, it load all the sur files in the scene:

blender --python sur_utils.py -- file1.sur file2.sur file3.sur ...
"""

import os
import struct
import contextlib
import itertools
from mathutils.geometry import normal


import struct
import mmap
import contextlib


def read_sur(filepath):
    ## the SUR file format is :
    # numVertices
    # x y z
    # x y z
    # ...
    # numTriangles
    # id1 id2 id3
    # id1 id2 id3
    # ...

    with open(filepath, 'rb') as file:
        # check http://bugs.python.org/issue8046 to have mmap context
        # manager fixed in python
        data = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        #yield data
        #data.close()

        verts, faces, norms = [], [], []

        # read the number of vertices
        nv = int(data.readline().rstrip())
        # read the vertex coordinates for all vertices
        for i in range(nv):
            line = data.readline().rstrip()
            v = list(map(float, line.split()))
            verts.append(v)

        # read the number of faces
        nf = int(data.readline().rstrip())
        # read the face's vertex indices for all faces
        for i in range(nf):
            line = data.readline().rstrip()
            t = list(map(int, line.split()))
            faces.append(t)

        print("SUR file has %d verts and %d faces" %(nv, nf))

        return verts, faces, norms



def write_sur(filepath, verts, faces):
    # the SUR file format is :
    # numVertices
    # x y z
    # x y z
    # ...
    # numTriangles
    # id1 id2 id3
    # id1 id2 id3
    # ...

    # print("faces=", list(faces))
    # print("num faces=", len(list(faces)))
    # print("filepath=", filepath)

    with open(filepath, 'w') as data:
        # write the number of vertices
        data.write("%d\n" % len(verts))
        # write the vertex coordinates
        for vert in verts:
            data.write("%f %f %f\n" % (vert[0], vert[1], vert[2]))

        # write the number of faces
        data.write("%d\n" % len(faces))
        # write the face vertex indices
        for face in faces:
            data.write("%d %d %d\n" % (face[0], face[1], face[2]))


if __name__ == '__main__':
    import sys
    import bpy
    from io_mesh_sur import blender_utils

    filepaths = sys.argv[sys.argv.index('--') + 1:]

    for filepath in filepaths:
        objName = bpy.path.display_name(filepath)
        verts, faces, norms = read_sur(filepath)

        blender_utils.create_and_link_mesh(objName, faces, verts)
