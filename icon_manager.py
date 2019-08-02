# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

bl_info = {
    "name": "Icon Manager",
    "author": "Marius Giurgi (DolphinDream)",
    "version": (0, 0, 1),
    "blender": (2, 79, 0),
    "location": "View3D > Toolshelf > Edit Linked Library",
    "description": "Allows organizing, navigating and rendering icons.",
    "wiki_url": "some link goes here",
    "category": "Object",
}


import bpy
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty, StringProperty, PointerProperty

import os
import glob
import json
from collections import OrderedDict
from pprint import pprint

from sverchok.ui.sv_icons import custom_icon


DEBUG = False

_icon_list = {}

directionItems = [
    ("EAST_NORTH", "East-North", "", custom_icon("SV_DIRECTION_EN"), 0),
    ("EAST_SOUTH", "East-South", "", custom_icon("SV_DIRECTION_ES"), 1),
    ("WEST_NORTH", "West-North", "", custom_icon("SV_DIRECTION_WN"), 2),
    ("WEST_SOUTH", "West-South", "", custom_icon("SV_DIRECTION_WS"), 3),
    ("NORTH_EAST", "North-East", "", custom_icon("SV_DIRECTION_NE"), 4),
    ("NORTH_WEST", "North-West", "", custom_icon("SV_DIRECTION_NW"), 5),
    ("SOUTH_EAST", "South-East", "", custom_icon("SV_DIRECTION_SE"), 6),
    ("SOUTH_WEST", "South-West", "", custom_icon("SV_DIRECTION_SW"), 7)]

orient_cell = {
    0: lambda x, y, z: [+x, +y, z],  # east north (+x, +y)
    1: lambda x, y, z: [+x, -y, z],  # east south (+x, -y)
    2: lambda x, y, z: [-x, +y, z],  # west north (-x, +y)
    3: lambda x, y, z: [-x, -y, z],  # west south (-x, -y)
    4: lambda x, y, z: [+y, +x, z],  # north east (+y, +x)
    5: lambda x, y, z: [-y, +x, z],  # north west (-y, +x)
    6: lambda x, y, z: [+y, -x, z],  # south east (+y, -x)
    7: lambda x, y, z: [-y, -x, z]}  # south west (-y, -x)


def make_tile(center, width, height):
    ''' Make a tile mesh at given center with given weight and height '''
    cx, cy, cz = center

    verts = []
    verts.append([cx - width / 2, cy - height / 2, cz])
    verts.append([cx - width / 2, cy + height / 2, cz])
    verts.append([cx + width / 2, cy + height / 2, cz])
    verts.append([cx + width / 2, cy - height / 2, cz])

    edges = [[0, 1], [1, 2], [2, 3], [3, 0]]
    polys = [[0, 1, 2, 3]]

    return verts, edges, polys


def read_icon_data():
    ''' Read the icon data from file and cache it '''
    if _icon_list:
        return

    file_path = os.path.expanduser("~/iconList.json")

    #dir_path = os.path.dirname(os.path.realpath(__file__))
    #file_path = os.path.join(dir_path, "./iconList.json")

    print(os.getcwd())

    with open(file_path, encoding='utf-8') as data_file:
        data = json.load(data_file, object_pairs_hook=OrderedDict)

    numCategories = len(data.keys())
    numIconsInCategories = [len(x) for x in data.values()]

    if DEBUG:
        print("There are %d categories of icons: %s" % (numCategories, list(data.keys())))
        print("There are these number of icons in categories: ", numIconsInCategories)

    # cache the data into some useful hierarchies
    _icon_list["main"] = OrderedDict()
    _icon_list["main"]["data"] = data
    _icon_list["main"]["categoryNames"] = [category for category in data.keys()]
    _icon_list["main"]["iconNames"] = [name for iconPair in data.values() for name in iconPair.keys()]
    _icon_list["main"]["iconIDs"] = [ID for iconPair in data.values() for ID in iconPair.values()]
    _icon_list["main"]["indices"] = []  # updated later
    _icon_list["main"]["categories"] = OrderedDict()
    for category in data.keys():
        _icon_list["main"]["categories"][category] = OrderedDict()
        _icon_list["main"]["categories"][category]["names"] = [name for name in data[category].keys()]
        _icon_list["main"]["categories"][category]["IDs"] = [ID for ID in data[category].values()]
        _icon_list["main"]["categories"][category]["indices"] = []  # updated later


def get_icon_data():
    read_icon_data()
    return _icon_list["main"]["data"]


def get_category_names():
    read_icon_data()
    return _icon_list["main"]["categoryNames"]


def get_icon_names():
    read_icon_data()
    return _icon_list["main"]["iconNames"]


def get_icon_ids():
    read_icon_data()
    return _icon_list["main"]["iconIDs"]


def get_icon_indices():
    read_icon_data()
    return _icon_list["main"]["indices"]


def get_category_icon_names(category):
    read_icon_data()
    return _icon_list["main"]["categories"][category]["names"]


def get_category_icon_ids(category):
    read_icon_data()
    return _icon_list["main"]["categories"][category]["IDs"]


def get_category_icon_indices(category):
    read_icon_data()
    return _icon_list["main"]["categories"][category]["indices"]


def get_category_icon_index_lists():
    read_icon_data()
    return [get_category_icon_indices(category) for category in get_category_names()]


def update_icon_indices(wrap, separate):
    read_icon_data()
    iconData = get_icon_data()

    _icon_list["main"]["indices"] = []

    x = 0
    y = 1
    for category, iconPairs in iconData.items():
        _icon_list["main"]["categories"][category]["indices"] = []

        iconIndices = []
        for iconName, iconID in iconPairs.items():
            if x == wrap:  # reached the wrap limit ? => start a new line
                x = 1
                y = y + 1
            else:  # no wrap yet
                x = x + 1

            iconIndices.append([x - 1, y - 1])

        _icon_list["main"]["indices"].extend(iconIndices)
        _icon_list["main"]["categories"][category]["indices"] = [index for index in iconIndices]

        if separate:  # separate categories? => start next category on new line
            x = 0
            y = y + 1


def get_icon_grid_data(wrap, direction, grid_scale, center, separate_categories, current_icon):
    ''' Compute and return the icon grid data'''
    update_icon_indices(wrap, separate_categories)

    iconIndices = get_icon_indices()
    categoryIconIndices = get_category_icon_index_lists()

    maxX = max(x for x, y in iconIndices) + 1
    maxY = max(y for x, y in iconIndices) + 1

    iconCenters = [(x * grid_scale, y * grid_scale, 0) for x, y in iconIndices]

    gridIndices = [[x, y] for x in range(maxX) for y in range(maxY)]
    gridCenters = [(x * grid_scale, y * grid_scale, 0) for x, y in gridIndices]

    categoryIconCenters = [[[x * grid_scale, y * grid_scale, 0]
                            for x, y in iconIndices] for iconIndices in categoryIconIndices]

    # center the cells around scene origin
    if center:
        cx = 0.5 * (maxX - 1) * grid_scale
        cy = 0.5 * (maxY - 1) * grid_scale
        iconCenters = [[x - cx, y - cy, z] for x, y, z in iconCenters]
        gridCenters = [[x - cx, y - cy, z] for x, y, z in gridCenters]
        categoryIconCenters = [[[x - cx, y - cy, z] for x, y, z in iconCenters] for iconCenters in categoryIconCenters]

    # orient the cells based on given direction
    directionIndex = next(x[-1] for x in directionItems if x[0] == direction)

    orienter = orient_cell[directionIndex]
    iconCenters = [orienter(x, y, z) for x, y, z in iconCenters]
    gridCenters = [orienter(x, y, z) for x, y, z in gridCenters]
    categoryIconCenters = [[orienter(x, y, z) for x, y, z in iconCenters] for iconCenters in categoryIconCenters]

    # construct the icon meshes
    iconVertList, iconEdgeList, iconPolyList = [[], [], []]
    for iconCenter in iconCenters:
        verts, edges, polys = make_tile(iconCenter, 1, 1)
        iconVertList.append(verts)
        iconEdgeList.append(edges)
        iconPolyList.append(polys)
    iconVerts, iconEdges, iconPolys = mesh_join(iconVertList, iconVertList, iconPolyList)

    # construct the grid meshes
    gridVertList, gridEdgeList, gridPolyList = [[], [], []]
    for gridCenter in gridCenters:
        verts, edges, polys = make_tile(gridCenter, grid_scale, grid_scale)
        gridVertList.append(verts)
        gridEdgeList.append(edges)
        gridPolyList.append(polys)
    gridVerts, gridEdges, gridPolys = mesh_join(gridVertList, gridVertList, gridPolyList)

    categoryCenters = []
    categorySizes = []
    for iconCenterss in categoryIconCenters:
        minX = min([iconCenter[0] for iconCenter in iconCenterss]) - grid_scale / 2
        maxX = max([iconCenter[0] for iconCenter in iconCenterss]) + grid_scale / 2
        minY = min([iconCenter[1] for iconCenter in iconCenterss]) - grid_scale / 2
        maxY = max([iconCenter[1] for iconCenter in iconCenterss]) + grid_scale / 2
        categoryCenters.append([(minX + maxX) / 2, (minY + maxY) / 2, 0])
        categorySizes.append([(maxX - minX), (maxY - minY)])

    # construct the category meshes
    categoryVertList, categoryEdgeList, categoryPolyList = [[], [], []]
    for c, (w, h) in zip(categoryCenters, categorySizes):
        verts, edges, polys = make_tile(c, w, h)
        categoryVertList.append(verts)
        categoryEdgeList.append(edges)
        categoryPolyList.append(polys)
    categoryVerts, categoryEdges, categoryPolys = mesh_join(categoryVertList, categoryEdgeList, categoryPolyList)

    # get camera location for the current icon
    categoryNames = get_category_names()
    iconNames = get_icon_names()
    iconIndex = iconNames.index(current_icon)
    iconLocation = iconCenters[iconIndex]
    cameraLocation = [iconLocation[0], iconLocation[1], 4]

    data = OrderedDict()
    data["Category Names"] = categoryNames
    data["Category Centers"] = categoryCenters
    data["Category Verts"] = categoryVerts
    data["Category Polys"] = categoryPolys
    data["Grid Centers"] = gridCenters
    data["Grid Verts"] = gridVerts
    data["Grid Polys"] = gridPolys
    data["Icon Names"] = iconNames
    data["Icon Centers"] = iconCenters
    data["Icon Verts"] = iconVerts
    data["Icon Polys"] = iconPolys
    data["Camera Location"] = cameraLocation

    _icon_list["main"]["Current Icon Location"] = iconLocation

    if DEBUG:
        data["Category Indices"] = categoryIndices
        data["Icon Indices"] = iconIndices
        data["Grid Indices"] = gridIndices

    return data


class IconManagerPanelProperties(bpy.types.PropertyGroup):
    ''' Manages Icons '''

    def navigate_icon(self, context, direction):
        if DEBUG:
            print("Advancing to %s icon" % direction)

        if self.selected_category == "All":
            iconNames = get_icon_names()
        else:
            iconNames = get_category_icon_names(self.selected_category)

        delta = +1 if direction == "NEXT" else -1
        iconIndex = iconNames.index(self.selected_icon)
        newIconIndex = (iconIndex + delta) % len(iconNames)
        newIconName = iconNames[newIconIndex]
        self.selected_icon = newIconName

        self.update_metronom = not self.update_metronom

    def selectedCategoryItems(self, context):
        categories = ["All"]
        categories.extend(get_category_names())
        categoryItems = [(k, k.title(), "", "", i) for i, k in enumerate(categories)]
        return categoryItems

    def selectedIconItems(self, context):
        if self.selected_category == "All":
            iconNames = get_icon_names()
            iconIDs = get_icon_ids()
        else:
            iconNames = get_category_icon_names(self.selected_category)
            iconIDs = get_category_icon_ids(self.selected_category)

        iconItems = [(k, k.title(), "", custom_icon(iconIDs[iconNames.index(k)]), i) for i, k in enumerate(iconNames)]
        return iconItems

    def update_direction(self, context):
        print(self.direction)
        self.process(context)

    def update_selected_category(self, context):
        if DEBUG:
            print("Selected category:", self.selected_category)

        if self.selected_category == "All":
            iconNames = get_icon_names()
        else:
            iconNames = get_category_icon_names(self.selected_category)

        self.selected_icon = iconNames[0]

        self.process(context)

    def update_selected_icon(self, context):
        if DEBUG:
            print("Selected icon:", self.selected_icon)
            print("Selected category:", self.selected_category)

        if self.selected_category == "All":
            iconNames = get_icon_names()
            iconIDs = get_icon_ids()
        else:
            iconNames = get_category_icon_names(self.selected_category)
            iconIDs = get_category_icon_ids(self.selected_category)

        index = iconNames.index(self.selected_icon)
        objectName = iconIDs[index]
        objects = context.scene.objects

        if self.auto_select_empty:
            if objectName in objects.keys():
                # bpy.context.scene.objects.active = objects[objectName]
                bpy.ops.object.select_all(action='DESELECT')
                objects[objectName].select = True

        self.process(context)

    def update_empties(self, context):
        if DEBUG:
            print("update empties locations")
        self.process(context)

    def update_now(self, context):
        print("checking to update")
        self.update_metronom = not self.update_metronom

    def process(self, context):

        data = get_icon_grid_data(self.wrap,
                                  self.direction,
                                  self.grid_scale,
                                  self.center_grid,
                                  self.separate_categories,
                                  self.selected_icon)

        # locate empties to icon locations
        objectNames = bpy.context.scene.objects.keys()
        iconIDs = get_icon_ids()
        for iconIndex, iconID in enumerate(iconIDs):
            if iconID in objectNames:
                bpy.context.scene.objects[iconID].location = data["Icon Centers"][iconIndex]

        # update the 3D cursor location
        if self.relocate_3d_cursor:
            if DEBUG:
                print("relocating 3d cursor")
            c = _icon_list["main"]["Current Icon Location"]
            bpy.context.scene.cursor_location = c

        if "Camera SV" in objectNames:
            bpy.context.scene.objects["Camera SV"].location = data["Camera Location"]

    direction = EnumProperty(
        name="Direction",
        default="EAST_NORTH", items=directionItems,
        update=update_direction)

    selected_category = EnumProperty(
        name="Selected Category", items=selectedCategoryItems,
        update=update_selected_category)

    selected_icon = EnumProperty(
        name="Selected Icon", items=selectedIconItems,
        update=update_selected_icon)

    wrap = IntProperty(
        name="Wrap", description="Max number of cells before wrapping",
        default=9, min=1, update=process)

    grid_scale = FloatProperty(
        name="Grid Scale", description="Spread the icon grid apart",
        default=2.0, min=1.0, update=process)

    center_grid = BoolProperty(
        name="Center Grid", description="Center icon grid around origin",
        default=True, update=process)

    separate_categories = BoolProperty(
        name="Separate Categories", description="Separate the icons into categories",
        default=True, update=process)

    show_empty_names = BoolProperty(
        name="Show Empty Names", description="Show/Hide icon empty ID names",
        default=False, update=process)

    auto_select_empty = BoolProperty(
        name="Auto Select Empty", description="Auto select icon empty on icon selection",
        default=True, update=process)

    relocate_3d_cursor = BoolProperty(
        name="Relocate 3D Cursor", description="Relocate 3D cursor with Icon navigation",
        default=True, update=process)

    update_metronom = BoolProperty(
        name="Update Metronom", description="Update cycle",
        default=False, update=update_now)

class IconManagerPanel(bpy.types.Panel):
    bl_idname = "icon_manager.panel"
    bl_label = "Icon Manager"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    # bl_category = 'Sverchok'

    # @classmethod
    # def poll(cls, context):
    #     # only show up in this tree
    #     if not context.space_data.tree_type == 'SverchCustomTreeType':
    #         return

    #     # only show up if developer_mode has been set to True
    #     with sv_preferences() as prefs:
    #         return prefs.developer_mode

    def draw(self, context):
        layout = self.layout

        iconManagerProps = context.space_data.node_tree.iconManagerProps

        # NAVIGATION SETTINGS
        box = layout.box()
        box.label("Navigation Settings")
        col = box.column()

        col.prop(iconManagerProps, "selected_category", text="")

        row = col.row(align=True)
        row.prop(iconManagerProps, "selected_icon", text="")

        prevIcon = row.operator('icon_manager.navigate', text="", icon="PLAY_REVERSE")
        prevIcon.direction = "PREV"

        nextIcon = row.operator('icon_manager.navigate', text="", icon="PLAY")
        nextIcon.direction = "NEXT"

        col = row.column()
        col.operator("render.render", text="", icon='RENDER_STILL')

        col = box.column()
        col.prop(iconManagerProps, "relocate_3d_cursor")
        col.prop(iconManagerProps, "auto_select_empty")

        # GRID SETTINGS
        box = layout.box()
        box.label("Grid Settings")
        col = box.column()

        col.prop(iconManagerProps, 'direction', expand=False)
        col.prop(iconManagerProps, 'center_grid')
        col.prop(iconManagerProps, 'separate_categories')

        col = box.column()
        col.prop(iconManagerProps, "wrap")
        col.prop(iconManagerProps, "grid_scale")

        # EMPTY SETTINGS
        box = layout.box()
        box.label("Empty Settings")
        row = box.row()
        ce = row.operator("icon_manager.create_empties")
        ce.showName = iconManagerProps.show_empty_names
        row = box.row()
        row.prop(iconManagerProps, "show_empty_names", text="Show Names")

        # CAMERA SETTINGS
        box = layout.box()
        box.label("Camera Settings")
        row = box.row()
        cc = row.operator("icon_manager.create_camera")

        # RENDERING SETTINGS
        box = layout.box()
        box.label("Render Settings")
        row = box.row()
        ri = row.operator("icon_manager.render_icons")
        row = box.row()
        row.operator("render.render", text="Render", icon='RENDER_STILL')


class IconManagerRenderIcons(bpy.types.Operator):
    ''' Render Icons '''
    bl_idname = "icon_manager.render_icons"
    bl_label = "Render Icons"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        iconManager = context.space_data.node_tree.iconManagerProps

        iconNames = get_icon_names()
        iconIDs = get_icon_ids()
        for iconName, iconID in zip(iconNames, iconIDs):
            iconManager.selected_icon = iconName
            if DEBUG:
                print("Rendering icon: ", iconName)
            # set the path/file
            bpy.context.scene.render.filepath = "/tmp/sverchokIcons/" + iconID.lower() + ".png"
            # Render still image, automatically write to output path
            bpy.ops.render.render(write_still=True)

        return {'FINISHED'}


class IconManagerCreateCamera(bpy.types.Operator):
    ''' Create Icon Rendering Camera '''
    bl_idname = "icon_manager.create_camera"
    bl_label = "Create Camera"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if "Camera SV" not in context.scene.objects.keys():
            camera = bpy.data.cameras.new("Camera SV")
            camera.type = "ORTHO"
            camera.ortho_scale = 1
            camera_object = bpy.data.objects.new("Camera SV", camera)
            bpy.context.scene.objects.link(camera_object)
            bpy.context.scene.camera = camera_object

        return {'FINISHED'}


class IconManagerCreateEmpties(bpy.types.Operator):
    ''' Create Icon Empties '''
    bl_idname = "icon_manager.create_empties"
    bl_label = "Create Empties"
    bl_options = {'REGISTER', 'UNDO'}

    showName = BoolProperty(name='showName', default=False)

    def execute(self, context):
        iconManager = context.space_data.node_tree.iconManagerProps

        iconIDs = get_icon_ids()

        objects = context.scene.objects
        objectNames = objects.keys()

        for iconID in iconIDs:
            # print("icon ID:", iconID)
            if iconID not in objectNames:
                o = bpy.data.objects.new(iconID, None)
                bpy.context.scene.objects.link(o)
                o.empty_draw_size = 0.5
                o.empty_draw_type = 'PLAIN_AXES'
                o.show_name = self.showName
            else:
                o = objects[iconID]
                o.empty_draw_size = 0.5
                o.show_name = self.showName

        iconManager.update_empties(context)

        return {'FINISHED'}


class IconManagerNavigateIcon(bpy.types.Operator):
    ''' Navigate Icons '''
    bl_idname = "icon_manager.navigate"
    bl_label = "Navigate icons"
    bl_options = {'REGISTER', 'UNDO'}

    direction = StringProperty(name='direction')

    def execute(self, context):
        iconManager = context.space_data.node_tree.iconManagerProps
        iconManager.navigate_icon(context, self.direction)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(IconManagerCreateCamera)
    bpy.utils.register_class(IconManagerRenderIcons)
    bpy.utils.register_class(IconManagerCreateEmpties)
    bpy.utils.register_class(IconManagerNavigateIcon)
    bpy.utils.register_class(IconManagerPanel)
    bpy.utils.register_class(IconManagerPanelProperties)
    bpy.types.NodeTree.iconManagerProps = PointerProperty(
        name="iconManagerProps", type=IconManagerPanelProperties)


def unregister():
    del bpy.types.NodeTree.iconManagerProps
    bpy.utils.unregister_class(IconManagerPanel)
    bpy.utils.unregister_class(IconManagerPanelProperties)
    bpy.utils.unregister_class(IconManagerCreateCamera)
    bpy.utils.unregister_class(IconManagerNavigateIcon)
    bpy.utils.unregister_class(IconManagerCreateEmpties)
    bpy.utils.unregister_class(IconManagerRenderIcons)


