import sys
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.2/lib/python3.2')
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.2/lib/python3.2/site-packages')
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.2/lib/python3.2/site-packages/pycollada-0.3-py3.2.egg')
sys.path.append('/Library/Frameworks/Python.framework/Versions/3.2/lib/python3.2/site-packages/python_dateutil-2.0-py3.2.egg')

import bpy
from hashlib import sha1
from mathutils import Matrix
from collada import Collada
from collada.triangleset import TriangleSet


def load(op, ctx, filepath=None, **kwargs):
    c = Collada(filepath)

    imp = ColladaImport(ctx, c)

    for obj in c.scene.objects('geometry'):
        imp.import_geometry(obj)

    return {'FINISHED'}


class ColladaImport(object):
    def __init__(self, ctx, collada):
        self._ctx = ctx
        self._collada = collada
        self._imported_geometries = []

    def import_geometry(self, geom):
        b_materials = {}
        for sym, matnode in geom.materialnodebysymbol.items():
            mat = matnode.target
            b_matname = self.import_name(mat)
            if b_matname not in bpy.data.materials:
                self.import_material(mat, b_matname)
            b_materials[sym] = bpy.data.materials[b_matname]

        for i, p in enumerate(geom.original.primitives):
            if not isinstance(p, TriangleSet):
                continue
            b_meshname = self.import_name(geom.original, i)
            b_obj = self.import_geometry_triangleset(p, b_meshname)
            if not b_obj:
                continue

            tf = Matrix(geom.matrix)
            tf.transpose()

            b_obj.matrix_world = tf
            self._ctx.scene.objects.link(b_obj)

    def import_geometry_triangleset(self, triset, b_name):
        b_mesh = None
        if b_name in bpy.data.meshes:
            b_mesh = bpy.data.meshes[b_name]
        else:
            if not (triset.vertex is not None and \
                    triset.vertex_index is not None):
                return
            b_mesh = bpy.data.meshes.new(b_name)
            b_mesh.from_pydata(triset.vertex, [], triset.vertex_index)
            b_mesh.update()

        b_obj = bpy.data.objects.new(b_name, b_mesh)
        b_obj.data = b_mesh
        return b_obj

    def import_material(self, mat, b_name):
        b_mat = bpy.data.materials.new(b_name)
        b_mat.diffuse_shader = 'LAMBERT'
        getattr(self, 'import_rendering_' + \
                mat.effect.shadingtype)(mat, b_mat)

    def import_rendering_blinn(self, mat, b_mat):
        effect = mat.effect
        self.import_rendering_diffuse(effect.diffuse, b_mat)

    def import_rendering_constant(self, mat, b_mat):
        effect = mat.effect

    def import_rendering_lambert(self, mat, b_mat):
        effect = mat.effect
        self.import_rendering_diffuse(effect.diffuse, b_mat)

    def import_rendering_phong(self, mat, b_mat):
        effect = mat.effect
        self.import_rendering_diffuse(effect.diffuse, b_mat)

    def import_rendering_diffuse(self, diffuse, b_mat):
        if isinstance(diffuse, tuple):
            b_mat.diffuse_color = diffuse[:3]

    def import_name(self, obj, index=0):
        base = ('%s-%d' % (obj.id, index))
        return base[:10] + sha1(base.encode('utf-8')
                ).hexdigest()[:10]

