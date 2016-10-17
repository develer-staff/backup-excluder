import os
import weakref


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class BadElementException(Exception):
    pass


class SystemTreeNode(object):

    """ The node and the tree roted in it have not matched any filter """
    FULLY_INCLUDED = 0
    """ The node has not matched any filter, but one of its descendant has """
    PARTIALLY_INCLUDED = 1
    """ The node has matched a filter """
    DIRECTLY_EXCLUDED = 2

    def __init__(self, name, size=0, parent=None, children=None):
        """ Create a new node (a tree if a list of children is supplied).

        A SystemTreeNode has a name and a size and an internal state.
        The size represents the size of the whole subtree rooted in the
        node (node comprised). The internal state remembers the status
        of the node w.r.t. to the filters used to prune the tree.
        """
        super().__init__()
        # self.name is redoundant since it is the key inside parent.children
        self.name = name
        self.size = size
        if parent is not None:
            self.parent = weakref.ref(parent)
        else:
            self.parent = None
        self.lastState = self.FULLY_INCLUDED
        self.excludedPathFoundHandler = None
        self.visibilityChangedHandler = None
        if not children:
            children = {}
        self.children = children
        for child in self.children.values():
            self.addChild(child)

    def addChild(self, child):
        """ Add a child to the specified node.

        Only SystemTreeNode can be used as children.
        The size of the added child is propagated up to the eldermost
        predecessor.
        """
        if not isinstance(child, SystemTreeNode):
            raise BadElementException()
        self.children[child.name] = child
        self.size += child.size
        child.parent = weakref.ref(self)
        sup = self.parent
        while sup and isinstance(sup(), SystemTreeNode):
            sup().size += child.size
            sup = sup().parent

    def getChild(self, childName):
        """ Get the child with the specifed name.

        Raise BadElementException if no child with the specified name
        is found.
        """
        try:
            child = self.children[childName]
        except KeyError as e:
            raise BadElementException()
        return child

    def _excludedPathFound(self, path):
        """ Trigger the callback that manages when a node matches
        the cut function of 'update'.
        """
        if self.excludedPathFoundHandler is not None:
            self.excludedPathFoundHandler(path)

    def _visibilityChanged(self, newStatus, newSize):
        """ Trigger the callback that manages when the subtree rooted
        in self changes its internal state.
        """
        if self.visibilityChangedHandler is not None:
            self.visibilityChangedHandler(newStatus, newSize)

    def _set_exclusion_state_recursive(self, exclusionState):
        """ Update the internal state of the subtree roted in self.

        No events/callback are raised.
        """
        self.lastState = exclusionState
        for child in self.children.values():
            child._set_exclusion_state_recursive(exclusionState)

    def _update(self, parentPath, cutPath):
        """ Update the tree roted in self with the given cutPath.

        Return 3 values:
        (1) a boolean flag telling whether the state of the subtree
        rooted in self has changed (some node have been pruned or de-pruned)
        (2) the size (in bytes) of the subtree
        (3) the size (number of leaves and internal nodes) of the subtree
        """
        fullPath = os.path.join(parentPath, self.name)
        if cutPath(fullPath):
            self._excludedPathFound(fullPath)
            if self.lastState != self.DIRECTLY_EXCLUDED:
                # This node must be cut -> all the subtree will be cut:
                # update the state of the whole subtree without calling
                # the callback for every node. The GUI must take care of
                # updating the whole subtree.
                # FIXME: we assume the regular expression do not
                # use exclusion sintax, e.g., [^a-z]
                self._set_exclusion_state_recursive(self.DIRECTLY_EXCLUDED)
                self._visibilityChanged(self.DIRECTLY_EXCLUDED, 0)
                return (True, 0, 0)
            return (False, 0, 0)
        elif self.children:
            subtreeChanged = False
            subtreeSize = 0
            subtreeNodes = 1  # for self
            for child in self.children.values():
                isPruned, childSize, childNodes = child._update(fullPath, cutPath)
                subtreeChanged |= isPruned
                subtreeSize += childSize
                subtreeNodes += childNodes
            if subtreeChanged or self.lastState == self.DIRECTLY_EXCLUDED:
                # Little hack: Compare the original size of the node
                # with the size of the pruned subtree to understand
                # whether the subtree changed because some nodes match
                # the cutPath function or because no nodes match the
                # filters anymore (e.g., a filter is removed)!
                if self.size == subtreeSize:
                    self.lastState = self.FULLY_INCLUDED
                    self._visibilityChanged(self.FULLY_INCLUDED, subtreeSize)
                else:
                    self.lastState = self.PARTIALLY_INCLUDED
                    self._visibilityChanged(self.PARTIALLY_INCLUDED, subtreeSize)
            return (subtreeChanged, subtreeSize, subtreeNodes)
        if self.lastState != self.FULLY_INCLUDED:
            self.lastState = self.FULLY_INCLUDED
            self._visibilityChanged(self.FULLY_INCLUDED, self.size)
            return (True, self.size, 1)
        return (False, self.size, 1)

    def update(self, parentPath, cutPath):
        """ Compute the size (in bytes and in number of tree nodes) of
        the subtree not pruned by cutPath which is rooted in self.
        """
        modified, totalSize, totalNodes = self._update(parentPath, cutPath)
        return (totalSize, totalNodes)

    @staticmethod
    def _createSystemTreeRecursive2(rootPath):
        """Recursivly create a SystemTreeNode tree depicting
        the file system footed in rootPath. Use os.fwalk.
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
                    path, count = SystemTreeNode._createSystemTreeRecursive2(dirPath)
                    currentRoot.addChild(path)
                    nodesInSubtree += (count + 1)
                for file in files:
                    try:
                        stat = os.stat(file, dir_fd=rootfd, follow_symlinks=False)
                        child = SystemTreeNode(file, stat.st_size)
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
        the file system footed in rootPath. Use os.scandir.
        """
        # rootFolder must be an absolute path
        head, tail = os.path.split(rootPath)
        currentRoot = SystemTreeNode(tail)
        nodesInSubtree = 0
        for entry in os.scandir(rootPath):
            if entry.is_dir(follow_symlinks=False):
                path, count = SystemTreeNode._createSystemTreeRecursive(entry.path)
                currentRoot.addChild(path)
                nodesInSubtree += (count + 1)
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
