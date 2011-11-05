import os
import bpy
from hashlib import sha1
from mathutils import Matrix, Vector
from bpy_extras.image_utils import load_image

from collada import Collada
from collada.triangleset import TriangleSet
from collada.material import Map


__all__ = ['load']

VENDOR_SPECIFIC = []
COLLADA_NS = 'http://www.collada.org/2005/11/COLLADASchema'


def load(op, ctx, filepath=None, **kwargs):
    c = Collada(filepath)
    impclass = get_import(c)
    imp = impclass(ctx, c, os.path.dirname(filepath))

    for obj in c.scene.objects('geometry'):
        imp.import_geometry(obj)

    return {'FINISHED'}


def get_import(collada):
    for i in VENDOR_SPECIFIC:
        if i.match(collada):
            return i
    return ColladaImport


class ColladaImport(object):
    """ Standard COLLADA importer. """
    def __init__(self, ctx, collada, basedir):
        self._ctx = ctx
        self._collada = collada
        self._basedir = basedir
        self._images = {}

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
            b_mat = b_materials.get(p.material, None)
            b_meshname = self.import_name(bgeom.original, i)
            if isinstance(p, TriangleSet):
                b_obj = self.import_geometry_triangleset(
                        p, b_meshname, b_mat)
            else:
                continue
            if not b_obj:
                continue

            self._ctx.scene.objects.link(b_obj)
            self._ctx.scene.objects.active = b_obj
            b_obj.matrix_world = _transposed(bgeom.matrix)
            bpy.ops.object.material_slot_add()
            b_obj.material_slots[0].material = b_mat

    def import_geometry_triangleset(self, triset, b_name, b_mat):
        b_mesh = None
        if b_name in bpy.data.meshes:
            b_mesh = bpy.data.meshes[b_name]
        else:
            if triset.vertex_index is None or \
                    not len(triset.vertex_index):
                return

            b_mesh = bpy.data.meshes.new(b_name)
            b_mesh.vertices.add(len(triset.vertex))
            b_mesh.faces.add(len(triset.vertex_index))
            for vidx, vertex in enumerate(triset.vertex):
                b_mesh.vertices[vidx].co = vertex

            # eekadoodle
            eekadoodle_faces = []
            for v1, v2, v3 in triset.vertex_index:
                eekadoodle_faces.extend([v3, v1, v2, 0] if v3 == 0 else [v1, v2, v3, 0])
            b_mesh.faces.foreach_set('vertices_raw', eekadoodle_faces)

            has_normal = (triset.normal_index is not None)
            has_uv = (len(triset.texcoord_indexset) > 0)

            if has_normal or has_uv:
                if has_uv:
                    b_mesh.uv_textures.new()
                for i, f in enumerate(b_mesh.faces):
                    if has_normal:
                        f.use_smooth = not _is_flat_face(
                                triset.normal[triset.normal_index[i]])
                    if has_uv:
                        t1, t2, t3 = triset.texcoord_indexset[0][i]
                        tface = b_mesh.uv_textures[0].data[i]
                        # eekadoodle
                        if triset.vertex_index[i][2] == 0:
                            t1, t2, t3 = t3, t1, t2
                        tface.uv1 = triset.texcoordset[0][t1]
                        tface.uv2 = triset.texcoordset[0][t2]
                        tface.uv3 = triset.texcoordset[0][t3]
                        if b_mat.name in self._images:
                            image = self._images[b_mat.name]
                            if image.has_data and image.depth == 32:
                                tface.alpha_blend = 'ALPHA'
                            tface.image = self._images[b_mat.name]

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
        if isinstance(diffuse, Map):
            image_path = diffuse.sampler.surface.image.path
            image = load_image(image_path, self._basedir)
            if image is not None:
                texture = bpy.data.textures.new(name='Kd', type='IMAGE')
                texture.image = image
                mtex = b_mat.texture_slots.add()
                mtex.texture_coords = 'UV'
                mtex.texture = texture
                mtex.use_map_color_diffuse = True
                self._images[b_mat.name] = image
            else:
                b_mat.diffuse_color = 1., 0., 0.
        elif isinstance(diffuse, tuple):
            b_mat.diffuse_color = diffuse[:3]

    def import_name(self, obj, index=0):
        base = ('%s-%d' % (obj.id, index))
        return base[:10] + sha1(base.encode('utf-8')
                ).hexdigest()[:10]


class SketchUpImport(ColladaImport):
    """ SketchUp specific COLLADA import.

    Features:

    - imports PNG textures with alpha channel
    """
    def import_rendering_diffuse(self, diffuse, b_mat):
        ColladaImport.import_rendering_diffuse(self, diffuse, b_mat)
        if isinstance(diffuse, Map):
            if b_mat.name in self._images:
                image = self._images[b_mat.name]
                if image.has_data and image.depth == 32:
                    diffslot = None
                    for ts in b_mat.texture_slots:
                        if ts.use_map_diffuse:
                            diffslot = ts
                            break
                    diffslot.use_map_alpha = True
                    tex = diffslot.texture
                    tex.use_mipmap = True
                    tex.use_interpolation = True
                    tex.use_alpha = True
                    b_mat.use_transparency = True
                    b_mat.alpha = 0.0

    @classmethod
    def match(cls, collada):
        xml = collada.xmlnode
        ns = {'dae': COLLADA_NS}
        def test1():
            src = [ xml.find('//dae:instance_visual_scene',
                        namespaces=ns).get('url') ]
            at = xml.find('//dae:authoring_tool', namespaces=ns)
            if at is not None:
                src.append(at.text)
            return all(['SketchUp' in s for s in src if s])
        def test2():
            et = xml.find('//dae:extra/dae:technique',
                    namespaces=ns)
            return et is not None and et.get('profile') == 'GOOGLEEARTH'
        return test1() or test2()

VENDOR_SPECIFIC.append(SketchUpImport)


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

