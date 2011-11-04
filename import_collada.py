import bpy
from hashlib import sha1
from mathutils import Matrix, Vector

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

    def import_geometry(self, bgeom):
        b_materials = {}
        for sym, matnode in bgeom.materialnodebysymbol.items():
            mat = matnode.target
            b_matname = self.import_name(mat)
            if b_matname not in bpy.data.materials:
                self.import_material(mat, b_matname)
            b_materials[sym] = bpy.data.materials[b_matname]

        for i, p in enumerate(bgeom.original.primitives):
            b_obj = None
            b_meshname = self.import_name(bgeom.original, i)
            if isinstance(p, TriangleSet):
                b_obj = self.import_geometry_triangleset(p, b_meshname)
            else:
                continue
            if not b_obj:
                continue

            self._ctx.scene.objects.link(b_obj)
            self._ctx.scene.objects.active = b_obj
            b_obj.matrix_world = _transposed(bgeom.matrix)
            bpy.ops.object.material_slot_add()
            b_obj.material_slots[0].material = b_materials[p.material]

    def import_geometry_triangleset(self, triset, b_name):
        b_mesh = None
        if b_name in bpy.data.meshes:
            b_mesh = bpy.data.meshes[b_name]
        else:
            if triset.vertex_index is None or \
                    not len(triset.vertex_index):
                return

            b_mesh = bpy.data.meshes.new(b_name)
            b_mesh.from_pydata(triset.vertex, [], triset.vertex_index)
            if triset.normal_index is not None:
                for i, f in enumerate(b_mesh.faces):
                    f.use_smooth = not _is_flat_face(
                            triset.normal[triset.normal_index[i]])
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


def _is_flat_face(normal):
    a = Vector(normal[0])
    for n in normal[1:]:
        dp = a.dot(Vector(n))
        if dp < 0.99999 or dp > 1.00001:
            return False
    return True

def _transposed(matrix):
    m = Matrix(matrix)
    m.transpose()
    return m

