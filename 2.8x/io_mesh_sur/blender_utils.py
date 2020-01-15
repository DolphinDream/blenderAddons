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

import bpy
import array
from itertools import chain

from pprint import pprint

def create_and_link_mesh(name, faces, face_normals, points, global_matrix):
    """
    Create a blender mesh and object called name from a list of
    *points* and *faces* and link it in the current scene.
    """

    print("new mesh will be created")

    print("name = ", name)
    print("faces = ", faces)
    print("face_normals = ", face_normals)
    print("points = ", points)
    print("global_matrix = ", global_matrix)

    # return

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)

    if face_normals:
        # Note: we store 'temp' normals in loops, since validate() may alter final mesh,
        #       we can only set custom loop_normals *after* calling it.
        mesh.create_normals_split()
        loop_normals = tuple(chain(*chain(*zip(face_normals, face_normals, face_normals))))
        mesh.loops.foreach_set("normal", loop_normals)

    mesh.transform(global_matrix)

    # update mesh to allow proper display
    mesh.validate(clean_customdata=False)  # *Very* important to not remove loop_normals here!

    if face_normals:
        clnors = array.array('f', [0.0] * (len(mesh.loops) * 3))
        mesh.loops.foreach_get("normal", clnors)

        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

        mesh.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
        mesh.use_auto_smooth = True
        mesh.show_edge_sharp = True
        mesh.free_normals_split()

    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def faces_from_mesh(ob, global_matrix, use_mesh_modifiers=False):
    """
    From an object, return a generator over a list of faces.

    Each faces is a list of his vertexes. Each vertex is a tuple of
    his coordinate.

    use_mesh_modifiers
        Apply the preview modifier to the returned liste

    triangulate
        Split the quad into two triangles
    """

    # get the editmode data
    ob.update_from_editmode()

    # get the modifiers
    if use_mesh_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_owner = ob.evaluated_get(depsgraph)
    else:
        mesh_owner = ob

    try:
        mesh = mesh_owner.to_mesh()
    except RuntimeError:
        return

    mat = global_matrix @ ob.matrix_world
    mesh.transform(mat)
    if mat.is_negative:
        mesh.flip_normals()
    mesh.calc_loop_triangles()

    vertices = mesh.vertices
    triangles = mesh.loop_triangles

    print("mesh = ")
    pprint(mesh)

    print("triangles=")
    pprint(triangles)
    # print("triangles = ", triangles)
    # triangles = mesh.triangles
    tris = [list(tri.vertices) for tri in triangles]
    print("tris=")
    pprint(tris)

    return vertices, triangles

    # mesh_owner.to_mesh_clear()