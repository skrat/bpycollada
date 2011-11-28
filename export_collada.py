import bpy
import numpy as np
from mathutils import Matrix, Vector

from collada import Collada
from collada.geometry import Geometry
from collada.scene import Node, Scene
from collada.scene import GeometryNode
from collada.scene import MatrixTransform
from collada.source import FloatSource, InputList


def save(op, context,
        filepath=None,
        directory=None,
        export_as=None,
        **kwargs):

    ex = ColladaExport(directory, export_as)

    for o in context.scene.objects:
        ex.object(o)

    ex.save(filepath)

    return {'FINISHED'}


class ColladaExport(object):
    def __init__(self, directory, export_as='dae_only'):
        self._dir = directory
        self._export_as = export_as
        self._geometries = {}
        self._collada = Collada()

        self._scene = Scene('main', [])
        self._collada.scenes.append(self._scene)
        self._collada.scene = self._scene

    def save(self, fp):
        self._collada.write(fp)

    def object(self, b_obj, parent=None, children=True):
        b_matrix = b_obj.matrix_world
        if parent:
            if children:
                b_matrix = b_obj.matrix_local
            else:
                b_matrix = Matrix()

        node = self.node(b_obj.name, b_matrix)
        if any(b_obj.children) and children:
            self.object(b_obj, parent=node, children=False)
            for child in b_obj.children:
                self.object(child, parent=node)

        if parent:
            parent.children.append(node)
        else:
            self._scene.nodes.append(node)

        inode_meth = getattr(self, 'obj_' + b_obj.type, None)
        if inode_meth:
            node.children.append(inode_meth(b_obj))

    def node(self, b_name, b_matrix=None):
        tf = []
        if b_matrix:
            tf.append(self.matrix(b_matrix))
        node = Node(b_name, transforms=tf)
        node.save()
        return node

    def obj_MESH(self, b_obj):
        geom = self._geometries.get(b_obj.data.name, None)
        if not geom:
            geom = self.mesh(b_obj.data)
            self._geometries[b_obj.data.name] = geom
        return GeometryNode(geom, [])

    def mesh(self, b_mesh):
        vert_srcid = b_mesh.name + '-vertary'
        vert_f = [c for v in b_mesh.vertices for c in v.co]
        vert_src = FloatSource(vert_srcid, np.array(vert_f), ('X', 'Y', 'Z'))

        norm_srcid = b_mesh.name + '-normary'
        norm_f = [c for v in b_mesh.vertices for c in v.normal]
        norm_src = FloatSource(norm_srcid, np.array(norm_f), ('X', 'Y', 'Z'))

        name = b_mesh.name + '-geom'
        geom = Geometry(self._collada, name, name, [vert_src, norm_src])
        ilist = InputList()
        ilist.addInput(0, 'VERTEX', _url(vert_srcid))
        ilist.addInput(1, 'NORMAL', _url(norm_srcid))
        indices = np.array([i for v in [
            (v, v) for f in b_mesh.faces for v in f.vertices]
            for i in v])
        if _is_trimesh(b_mesh):
            p = geom.createTriangleSet(indices, ilist, 'none')
        else:
            vcount = [len(f.vertices) for f in b_mesh.faces]
            p = geom.createPolylist(indices, vcount, ilist, 'none')

        geom.primitives.append(p)
        self._collada.geometries.append(geom)
        return geom

    def matrix(self, b_matrix):
        f = tuple(map(tuple, b_matrix.transposed()))
        return MatrixTransform(np.array(
            [e for r in f for e in r], dtype=np.float32))


def _is_trimesh(b_mesh):
    return all([len(f.vertices) == 3 for f in b_mesh.faces])

def _url(uid):
    return '#' + uid

