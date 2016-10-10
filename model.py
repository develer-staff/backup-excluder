import os

from PyQt5.QtCore import pyqtSignal, QObject


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class BadElementException(Exception):
    pass


class InexistentChildException(Exception):
    pass


class SystemTreeNode(QObject):

    FULLY_INCLUDED = 0
    PARTIALLY_INCLUDED = 1
    DIRECTLY_EXCLUDED = 2

    visibilityChanged = pyqtSignal(int, int)

    def __init__(self, name, size=0, parent=None, children=None):
        super().__init__()
        # self.name is redoundant since it is the key inside parent.children
        self.name = name
        self.size = size
        self.parent = parent
        if not children:
            children = {}
        self.children = children
        for child in self.children.values():
            self.addChild(child)

    def addChild(self, child):
        if not isinstance(child, SystemTreeNode):
            raise BadElementException()
        self.children[child.name] = child
        self.size += child.size
        child.parent = self

    def getChild(self, childName):
        return self.children[childName]

    def _update(self, parentPath, cutPath):
        """Computes the size of the subtree rooted in self. The subtree
        can be pruned by the supplied cutPath function. It also
        returns a flag showing wether the the cutPath function matched
        at least one element inside the whole subtree.
        """
        fullPath = os.path.join(parentPath, self.name)
        if cutPath(fullPath):
            self.visibilityChanged.emit(self.DIRECTLY_EXCLUDED, 0)
            return (True, 0)
        elif self.children:
            # We are in a dir node: do not consider the size of the
            # node (which is the size of the uncut subtree). We must
            # compute it again based on its subtree AND cutPath
            subtreeSize = 0
            prunedSubtree = False
            for child in self.children.values():
                isPruned, childSize = child._update(fullPath, cutPath)
                subtreeSize += child.update(fullPath, cutPath)
                prunedSubtree |= isPruned
            if prunedSubtree:
                self.visibilityChanged.emit(self.PARTIALLY_INCLUDED, subtreeSize)
            else:
                self.visibilityChanged.emit(self.FULLY_INCLUDED, subtreeSize)
            return (prunedSubtree, subtreeSize)
        self.visibilityChanged.emit(self.FULLY_INCLUDED, self.size)
        return (False, self.size)

    def update(self, parentPath, cutPath):
        return self._update(parentPath, cutPath)[1]

    @staticmethod
    def _createSystemTreeRecursive(rootPath):
        """Recursivly create a SystemTreeNode tree depicting
        the file system footed in rootPath.
        """
        # rootFolder must be an absolute path
        head, tail = os.path.split(rootPath)
        currentRoot = SystemTreeNode(tail)
        for root, dirs, files, rootfd in os.fwalk(rootPath):
            while dirs:
                # Important: remove dir from dirs, so that fwalk will not
                # inspect it in this recursion!
                folder = dirs.pop()
                dirPath = os.path.join(rootPath, folder)
                dirChild = SystemTreeNode._createSystemTreeRecursive(dirPath)
                currentRoot.addChild(dirChild)
            for file in files:
                try:
                    child = SystemTreeNode(file, os.stat(file, dir_fd=rootfd).st_size)
                    currentRoot.addChild(child)
                except EnvironmentError as err:
                    print("WARNING: {} in {}".format(err, root))
        return currentRoot

    @staticmethod
    def createSystemTree(rootFolder="."):
        """Returns a representation of the file system rooted in
        rootFolder as a SystemTreeNode tree and the prefix of the
        rootFolder in the file system.
        """
        rootPath = os.path.abspath(rootFolder)
        head, tail = os.path.split(rootPath)
        return (head, SystemTreeNode._createSystemTreeRecursive(rootPath))

    def printSubtree(self):
        current = self
        result = ""
        while current.parent:
            result += ">"
            current = current.parent
        result += "(" + str(self.name) + ")"
        print(result)
        for node in self.children.values():
            node.printSubtree()
