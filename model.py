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
    excludedPathFound = pyqtSignal(str)

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
        sup = self.parent
        while sup and isinstance(sup, SystemTreeNode):
            sup.size += child.size
            sup = sup.parent

    def getChild(self, childName):
        return self.children[childName]

    def _update(self, parentPath, cutPath):
        """Computes the size (in bytes and in number of tree nodes) of
        the subtree rooted in self. The subtree can be pruned by the
        supplied cutPath function. It also returns a flag showing
        wether the the cutPath function matched at least one element
         inside the whole subtree.
        """
        fullPath = os.path.join(parentPath, self.name)
        if cutPath(fullPath):
            self.excludedPathFound.emit(fullPath)
            self.visibilityChanged.emit(self.DIRECTLY_EXCLUDED, 0)
            return (True, 0, 0)
        elif self.children:
            # We are in a dir node: do not consider the size of the
            # node (which is the size of the uncut subtree). We must
            # compute it again based on its subtree AND cutPath
            prunedSubtree = False
            subtreeSize = 0
            nodesCount = 1  # for self
            for child in self.children.values():
                isPruned, childSize, childNodes = child._update(fullPath, cutPath)
                prunedSubtree |= isPruned
                subtreeSize += childSize
                nodesCount += childNodes
            if prunedSubtree:
                self.visibilityChanged.emit(self.PARTIALLY_INCLUDED, subtreeSize)
            else:
                self.visibilityChanged.emit(self.FULLY_INCLUDED, subtreeSize)
            return (prunedSubtree, subtreeSize, nodesCount)
        self.visibilityChanged.emit(self.FULLY_INCLUDED, self.size)
        return (False, self.size, 1)

    def update(self, parentPath, cutPath):
        modified, totalSize, totalNodes = self._update(parentPath, cutPath)
        return (totalSize, totalNodes)

    @staticmethod
    def _createSystemTreeRecursive(rootPath):
        """Recursivly create a SystemTreeNode tree depicting
        the file system footed in rootPath.
        """
        # rootFolder must be an absolute path
        head, tail = os.path.split(rootPath)
        currentRoot = SystemTreeNode(tail)
        nodesInSubtree = 0
        try:
            for root, dirs, files, rootfd in os.fwalk(rootPath):
                while dirs:
                    # Important: remove dir from dirs, so that fwalk will not
                    # inspect it in this recursion!
                    folder = dirs.pop()
                    dirPath = os.path.join(rootPath, folder)
                    dirChild, nodesCount = SystemTreeNode._createSystemTreeRecursive(dirPath)
                    currentRoot.addChild(dirChild)
                    nodesInSubtree += (nodesCount + 1)
                for file in files:
                    try:
                        child = SystemTreeNode(file, os.stat(file, dir_fd=rootfd, follow_symlinks=False).st_size)
                        currentRoot.addChild(child)
                        nodesInSubtree += 1
                    except EnvironmentError as err:
                        print("WARNING: {} in {}".format(err, root))
        except OSError as err:
            print("WARNING: {} in {}".format(err, rootPath))
        return (currentRoot, nodesInSubtree)

    @staticmethod
    def createSystemTree(rootFolder="."):
        """Returns a representation of the file system rooted in
        rootFolder as a SystemTreeNode tree and the prefix of the
        rootFolder in the file system.
        """
        rootPath = os.path.abspath(rootFolder)
        head, tail = os.path.split(rootPath)
        root, nodesCount = SystemTreeNode._createSystemTreeRecursive(rootPath)
        return (head, root, nodesCount + 1)

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
