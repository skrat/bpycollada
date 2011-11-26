import bpy
import numpy as np
from mathutils import Matrix, Vector

from collada import Collada
from collada.scene import Node, Scene
from collada.scene import GeometryNode
from collada.scene import MatrixTransform


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

    # def obj_MESH(self, b_obj):
    #     geom = ?
    #     return GeometryNode(geom, [])

    def matrix(self, b_matrix):
        f = tuple(map(tuple, b_matrix.transposed()))
        return MatrixTransform(np.array(
            [e for r in f for e in r], dtype=np.float32))

