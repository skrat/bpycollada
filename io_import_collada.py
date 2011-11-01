import bpy
from collada import Collada


def load(op, ctx, filepath=None, **kwargs):
    c = Collada(filepath)

    imp = ColladaImport(ctx, c)

    for obj in c.scene.objects('geometry'):
        imp.import_object(obj)

    return {'FINISHED'}


class ColladaImport(object):
    def __init__(self, ctx, collada):
        self._ctx = ctx
        self._collada = collada

        self._imported_materials = []

    def import_object(self, obj):
        b_materials = {}
        for sym, matnode in obj.materialnodebysymbol.items():
            mat = matnode.target
            b_matname = ('%s - %s' % (mat.id, mat.name))[:20]
            if mat not in self._imported_materials:
                self.import_material(mat, b_matname)
            b_materials[sym] = bpy.data.materials[b_matname]
        for p in obj.primitives():
            print(type(p))

    def import_material(self, mat, b_matname):
        b_mat = bpy.data.materials.new(b_matname)
        b_mat.diffuse_shader = 'LAMBERT'
        getattr(self, 'import_rendering_' + mat.effect.shadingtype)(mat, b_mat)

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

