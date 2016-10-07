import re
import os


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class BadElementException(Exception):
    pass


class InexistentChildException(Exception):
    pass


class SystemTreeNode:

    def __init__(self, name, size=0, parent=None, children=None):
        # self.name is redoundant since it is the key inside parent.children
        self.name = name
        self.size = size
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = {}
        for child in self.children.values():
            child.parent = self

    def addChild(self, child):
        if not isinstance(child, SystemTreeNode):
            raise BadElementException()
        self.children[child.name] = child
        child.parent = self

    def getChild(self, childName):
        return self.children[childName]

    def update(self, parentPath, cutPath):
        """Computes the size of the subtree rooted in self. The subtree can
        be pruned by the supplied cutPath function.
        """
        fullPath = os.path.join(parentPath, self.name)
        if cutPath(fullPath):
            return 0
        elif self.children:
            childrenSum = 0
            for child in self.children.values():
                childrenSum += child.update(fullPath, cutPath)
            return self.size + childrenSum
        return self.size

    def navigateToNode(self, path):
        """Returns the node reachable following path from the subtree rooted in self.

        The supplied path must not contain the name of node self.
        It raises a KeyError exception if the path contains non-valid
        children names.
        """
        head = path
        folders = []
        current = self
        while head:
            if head == os.sep:
                break
            head, tail = os.path.split(head)
            folders.insert(0, tail)
        try:
            for child in folders:
                current = current.getChild(child)
        except KeyError as e:
            raise InexistentChildException()

        return current

    @staticmethod
    def createSystemTree(rootFolder="."):
        """Create a representation of the file system rooted in rootFolder."""
        import os
        rootPath = os.path.abspath(rootFolder)
        head, tail = os.path.split(rootPath)
        rootNode = SystemTreeNode(tail)
        for root, dirs, files, rootfd in os.fwalk(rootPath):
            partialPath = removePrefix(root, rootPath)
            current = rootNode.navigateToNode(partialPath)
            for folder in dirs:
                current.addChild(SystemTreeNode(folder))
            for file in files:
                try:
                    current.addChild(SystemTreeNode(file, os.stat(file, dir_fd=rootfd).st_size))
                except EnvironmentError as err:
                    print("WARNING: {} in {}".format(err, root))
        return (head, rootNode)

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
