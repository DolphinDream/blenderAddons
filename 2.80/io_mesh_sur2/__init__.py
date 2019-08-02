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

# <pep8-80 compliant>

bl_info = {
    "name": "SUR format",
    "author": "Marius Giurgi (DolphinDream)",
    "version": (1, 1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export > Sur",
    "description": "Import-Export SUR files",
    "warning": "",
    "wiki_url": "",
    "support": 'OFFICIAL',
    "category": "Import-Export",
}


# @todo write the wiki page

"""
Import-Export SUR files (binary or ascii)

- Import automatically remove the doubles.
- Export can export with/without modifiers applied

Issues:

Import:
    - Does not handle endien
"""

if "bpy" in locals():
    import importlib
    if "sur_utils" in locals():
        importlib.reload(sur_utils)
    if "blender_utils" in locals():
        importlib.reload(blender_utils)

import os

import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        axis_conversion,
        )
from bpy.types import (
        Operator,
        OperatorFileListElement,
        )


@orientation_helper(axis_forward='Y', axis_up='Z')
class ImportSUR(Operator, ImportHelper):
    """Load SUR triangle mesh data"""
    bl_idname = "import_mesh.sur"
    bl_label = "Import SUR"
    bl_options = {'UNDO'}

    filename_ext = ".sur"

    filter_glob: StringProperty(
            default="*.sur",
            options={'HIDDEN'},
            )
    files: CollectionProperty(
            name="File Path",
            type=OperatorFileListElement,
            )
    directory: StringProperty(
            subtype='DIR_PATH',
            )

    global_scale: FloatProperty(
            name="Scale",
            soft_min=0.001, soft_max=1000.0,
            min=1e-6, max=1e6,
            default=1.0,
            )

    use_scene_unit: BoolProperty(
            name="Scene Unit",
            description="Apply current scene's unit (as defined by unit scale) to imported data",
            default=False,
            )

    use_facet_normal: BoolProperty(
            name="Facet Normals",
            description="Use (import) facet normals (note that this will still give flat shading)",
            default=False,
            )

    def execute(self, context):
        from . import sur_utils
        from . import blender_utils
        from mathutils import Matrix

        paths = [os.path.join(self.directory, name.name)
                 for name in self.files]

        scene = context.scene

        # Take into account scene's unit scale, so that 1 inch in Blender gives 1 inch elsewhere! See T42000.
        global_scale = self.global_scale
        if scene.unit_settings.system != 'NONE' and self.use_scene_unit:
            global_scale /= scene.unit_settings.scale_length

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4() @ Matrix.Scale(global_scale, 4)

        if not paths:
            paths.append(self.filepath)

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action='DESELECT')

        for path in paths:
            objName = bpy.path.display_name(os.path.basename(path))
            tris, tri_nors, pts = sur_utils.read_sur(path)
            tri_nors = tri_nors if self.use_facet_normal else None
            blender_utils.create_and_link_mesh(objName, tris, tri_nors, pts, global_matrix)

        return {'FINISHED'}


@orientation_helper(axis_forward='Y', axis_up='Z')
class ExportSUR(Operator, ExportHelper):
    """Save SUR triangle mesh data from the active object"""
    bl_idname = "export_mesh.sur"
    bl_label = "Export SUR"

    filename_ext = ".sur"
    filter_glob: StringProperty(default="*.sur", options={'HIDDEN'})

    use_selection: BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )
    global_scale: FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=1.0,
            )

    use_scene_unit: BoolProperty(
            name="Scene Unit",
            description="Apply current scene's unit (as defined by unit scale) to exported data",
            default=False,
            )
    ascii: BoolProperty(
            name="Ascii",
            description="Save the file in ASCII file format",
            default=False,
            )
    use_mesh_modifiers: BoolProperty(
            name="Apply Modifiers",
            description="Apply the modifiers before saving",
            default=True,
            )
    batch_mode: EnumProperty(
            name="Batch Mode",
            items=(('OFF', "Off", "All data in one file"),
                   ('OBJECT', "Object", "Each object as a file"),
                   ))

    @property
    def check_extension(self):
        return self.batch_mode == 'OFF'

    def execute(self, context):
        from . import sur_utils
        from . import blender_utils
        import itertools
        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "ascii",
                                            "axis_up",
                                            "use_selection",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "use_scene_unit",
                                            "use_mesh_modifiers",
                                            "batch_mode"
                                            ))

        scene = context.scene
        if self.use_selection:
            data_seq = context.selected_objects
        else:
            data_seq = scene.objects

        # Take into account scene's unit scale, so that 1 inch in Blender gives 1 inch elsewhere! See T42000.
        global_scale = self.global_scale
        if scene.unit_settings.system != 'NONE' and self.use_scene_unit:
            global_scale *= scene.unit_settings.scale_length

        global_matrix = axis_conversion(to_forward=self.axis_forward,
                                        to_up=self.axis_up,
                                        ).to_4x4() @ Matrix.Scale(global_scale, 4)

        if self.batch_mode == 'OFF':
            faces = itertools.chain.from_iterable(
                    blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
                    for ob in data_seq)

            sur_utils.write_sur(faces=faces, **keywords)
        elif self.batch_mode == 'OBJECT':
            prefix = os.path.splitext(self.filepath)[0]
            keywords_temp = keywords.copy()
            for ob in data_seq:
                faces = blender_utils.faces_from_mesh(ob, global_matrix, self.use_mesh_modifiers)
                keywords_temp["filepath"] = prefix + bpy.path.clean_name(ob.name) + ".sur"
                sur_utils.write_sur(faces=faces, **keywords_temp)

        return {'FINISHED'}


def menu_import(self, context):
    self.layout.operator(ImportSUR.bl_idname, text="Sur (.sur)")


def menu_export(self, context):
    self.layout.operator(ExportSUR.bl_idname, text="Sur (.sur)")


classes = (
    ImportSUR,
    ExportSUR
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)


if __name__ == "__main__":
    register()
