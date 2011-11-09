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

# Script copyright (C) Tim Knip, floorplanner.com
# Contributors: Tim Knip (tim@floorplanner.com)

bl_info = {
    'name'       : 'COLLADA format',
    'author'     : 'Tim Knip, Dusan Maliarik',
    'blender'    : (2, 5, 7),
    'api'        : 35622,
    'location'   : 'File > Import',
    'description': 'Import COLLADA',
    'warning'    : '',
    'wiki_url'   : 'https://github.com/skrat/blender-pycollada/wiki',
    'tracker_url': 'https://github.com/skrat/blender-pycollada/issues',
    'support'    : 'OFFICIAL',
    'category'   : 'Import'}


if 'bpy' in locals() and 'import_collada' in locals():
    import imp
    imp.reload(import_collada)

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper


class IMPORT_OT_collada(bpy.types.Operator, ImportHelper):
    """ COLLADA import operator. """

    bl_idname= 'import_scene.collada'
    bl_label = 'Import COLLADA'
    bl_options = {'UNDO'}

    filter_glob = StringProperty(
            default='*.dae',
            options={'HIDDEN'},
            )
    files = CollectionProperty(
            name='File Path',
            type=bpy.types.OperatorFileListElement,
            )
    directory = StringProperty(
            subtype='DIR_PATH',
            )

    transparent_shadows = BoolProperty(
            default=False,
            name="Transparent shadows",
            description="Import all materials receiving transparent shadows",
            )

    raytrace_transparency = BoolProperty(
            default=False,
            name="Raytrace transparency",
            description="Raytrace transparent materials",
            )

    def execute(self, context):
        from . import import_collada
        kwargs = self.as_keywords(ignore=('filter_glob', 'files', 'directory'))
        return import_collada.load(self, context, **kwargs)

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_collada.bl_idname,
            text="COLLADA (py) (.dae)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == '__main__':
    register()

