import os

from PyQt5.QtCore import pyqtSignal, QObject


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class BadElementException(Exception):
    pass


class SystemTreeNode(QObject):

    FULLY_INCLUDED = 0
    PARTIALLY_INCLUDED = 1
    DIRECTLY_EXCLUDED = 2

    visibilityChanged = pyqtSignal(int, "long long")
    excludedPathFound = pyqtSignal(str)

    def __init__(self, name, size=0, parent=None, children=None):
        super().__init__()
        # self.name is redoundant since it is the key inside parent.children
        self.name = name
        self.size = size
        self.parent = parent
        self.lastState = self.FULLY_INCLUDED
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

    def _set_exclusion_state_recursive(self, exclusionState):
        self.lastState = exclusionState
        for child in self.children.values():
            child._set_exclusion_state_recursive(exclusionState)

    def _update(self, parentPath, cutPath):
        """Computes the size (in bytes and in number of tree nodes) of
        the subtree rooted in self.
        The subtree can be pruned by the supplied cutPath function.
        It also returns a boolean flag telling whether the state of
        the subtree is changed (some node have been pruned or de-pruned).
        """
        fullPath = os.path.join(parentPath, self.name)
        if cutPath(fullPath):
            self.excludedPathFound.emit(fullPath)
            if self.lastState != self.DIRECTLY_EXCLUDED:
                # We update the state of each node of the subtree
                # WITHOUT emitting a signal for each node: only for the
                # root. The GUI must take care of correctly display
                # the pruned subtree.
                # FIXME: we assume the regular expression do not
                # use exclusion sintax, e.g., [^a-z]
                self._set_exclusion_state_recursive(self.DIRECTLY_EXCLUDED)
                self.visibilityChanged.emit(self.DIRECTLY_EXCLUDED, 0)
                return (True, 0, 0)
            return (False, 0, 0)
        elif self.children:
            # We are in a dir node: do not consider the size of the
            # node (which is the size of the uncut subtree). We must
            # compute it again based on its subtree AND cutPath.
            subtreeChanged = False
            subtreeSize = 0
            subtreeNodes = 1  # for self
            for child in self.children.values():
                isPruned, childSize, childNodes = child._update(fullPath, cutPath)
                subtreeChanged |= isPruned
                subtreeSize += childSize
                subtreeNodes += childNodes
            if subtreeChanged or self.lastState == self.DIRECTLY_EXCLUDED:
                # Little hack: if the subtree changed because a node
                # has matched the filter, then the visibility must update
                # accordingly. However, subtree can change also because
                # no more nodes match the filter (e.g., a filter is removed)
                # and in this case the view must reset the color. Comparing
                # the original size of the node with the size of the subtree
                # is the little hack to understand whether to reset the
                # view color!
                if self.size == subtreeSize:
                    self.visibilityChanged.emit(self.FULLY_INCLUDED, subtreeSize)
                else:
                    self.visibilityChanged.emit(self.PARTIALLY_INCLUDED, subtreeSize)
            return (subtreeChanged, subtreeSize, subtreeNodes)
        if self.lastState != self.FULLY_INCLUDED:
            self.lastState = self.FULLY_INCLUDED
            self.visibilityChanged.emit(self.FULLY_INCLUDED, self.size)
            return (True, self.size, 1)
        return (False, self.size, 1)

    def update(self, parentPath, cutPath):
        modified, totalSize, totalNodes = self._update(parentPath, cutPath)
        return (totalSize, totalNodes)

    @staticmethod
    def _createSystemTreeRecursive2(rootPath):
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
                    dirChild, nodesCount = SystemTreeNode._createSystemTreeRecursive2(dirPath)
                    currentRoot.addChild(dirChild)
                    nodesInSubtree += (nodesCount + 1)
                for file in files:
                    try:
                        child = SystemTreeNode(file, os.stat(file, dir_fd=rootfd,  follow_symlinks=False).st_size)
                        currentRoot.addChild(child)
                        nodesInSubtree += 1
                    except EnvironmentError as err:
                        print("WARNING: {} in {}".format(err, root))
        except PermissionError as err:
            print("WARNING 2: {} in {}".format(err, rootPath))
            currentRoot.name = "[DENIED]" + currentRoot.name
        return (currentRoot, nodesInSubtree)

    @staticmethod
    def _createSystemTreeRecursive(rootPath):
        """Recursivly create a SystemTreeNode tree depicting
        the file system footed in rootPath.
        """
        # rootFolder must be an absolute path
        head, tail = os.path.split(rootPath)
        currentRoot = SystemTreeNode(tail)
        nodesInSubtree = 0
        for entry in os.scandir(rootPath):
            if entry.is_dir(follow_symlinks=False):
                dirChild, nodesCount = SystemTreeNode._createSystemTreeRecursive(entry.path)
                currentRoot.addChild(dirChild)
                nodesInSubtree += (nodesCount + 1)
            elif entry.is_file(follow_symlinks=False):
                child = SystemTreeNode(entry.name, entry.stat().st_size)
                currentRoot.addChild(child)
                nodesInSubtree += 1
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
