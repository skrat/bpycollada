import sys
sys.path.append('/usr/local/lib/python3.2/dist-packages/pycollada-0.3-py3.2.egg')
sys.path.append('/usr/local/lib/python3.2/dist-packages')

import bpy
import numpy as np
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

            indices, data, count, has_normal, has_uv = _vertex_data(triset)
            vertex, normal, uv, face, tri = [], [], [], [], []

            for i in range(0, len(indices)):
                index = indices[i] * count
                tri.append(len(vertex))
                vertex.append(data[index:index + 3])
                if has_normal:
                    index += 3
                    normal.append(data[index:index + 3])
                if has_uv:
                    index += 3
                    uv.append(data[index:index + 2])
                if len(tri) == 3:
                    face.append(tri)
                    tri = []

            b_mesh = bpy.data.meshes.new(b_name)
            b_mesh.from_pydata(vertex, [], face)
            b_mesh.update()

            if has_normal or has_uv:
                if has_uv:
                    b_mesh.uv_textures.new()
                for i in range(len(b_mesh.faces)):
                    a, b, c = b_mesh.faces[i].vertices
                    if has_normal:
                        b_mesh.faces[i].use_smooth = True
                        for v in b_mesh.faces[i].vertices:
                            b_mesh.vertices[v].normal = normal[v]
                    if has_uv:
                        tface = b_mesh.uv_textures[0].data[i]
                        tface.uv1 = uv[a]
                        tface.uv2 = uv[b]
                        tface.uv3 = uv[c]

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


def _vertex_data(triset):
    count = 3
    has_normal = False
    has_uv = False

    indices2stack = [triset.vertex_index.reshape(-1, 1)]
    alldata = [triset.vertex]

    if triset.normal is not None:
        count += 3
        indices2stack.append(triset.normal_index.reshape(-1, 1))
        alldata.append(triset.normal)
        has_normal = True
    if len(triset.texcoord_indexset):
        count += 2
        indices2stack.append(triset.texcoord_indexset[0].reshape(-1, 1))
        alldata.append(triset.texcoordset[0])
        has_uv = True

    # have to flatten and reshape like this so that it's contiguous
    stacked_indices = np.hstack(indices2stack).flatten().reshape(
            (-1, len(indices2stack)))

    # index_map - maps each unique value back to a location in the original
    #     array it came from
    #     eg. stacked_indices[index_map] == unique_stacked_indices
    # inverse_map - maps original array locations to their location in
    #     the unique array
    #     e.g. unique_stacked_indices[inverse_map] == stacked_indices
    unique_stacked_indices, index_map, inverse_map = np.unique(
            stacked_indices.view([('', stacked_indices.dtype)] * \
                    stacked_indices.shape[1]), return_index=True,
                    return_inverse=True)
    unique_stacked_indices = unique_stacked_indices.view(
            stacked_indices.dtype).reshape(-1, stacked_indices.shape[1])

    # unique returns as int64, so cast back
    index_map = np.cast['uint32'](index_map)
    inverse_map = np.cast['uint32'](inverse_map)

    # sort the index map to get a list of the index of the first time each
    # value was encountered
    sorted_map = np.cast['uint32'](np.argsort(index_map))

    #since we're sorting the unique values, we have to map the inverse_map
    # to the new index locations
    backwards_map = np.zeros_like(sorted_map)
    backwards_map[sorted_map] = np.arange(len(sorted_map), dtype=np.uint32)

    # now this is the new unique values and their indices
    unique_stacked_indices = unique_stacked_indices[sorted_map]
    inverse_map = backwards_map[inverse_map]

    # combine the unique stacked indices into unique stacked data
    data2stack = []
    for idx, data in enumerate(alldata):
        data2stack.append(data[unique_stacked_indices[:,idx]])
    unique_stacked_data = np.hstack(data2stack).flatten()
    unique_stacked_data.shape = (-1)

    return (inverse_map, unique_stacked_data, count, has_normal, has_uv)

