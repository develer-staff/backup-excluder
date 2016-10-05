import re
import os


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


class SystemTreeNode:

    # self.name is redoundant since it is the key inside parent.children
    name = None
    size = None
    parent = None
    children = None

    def __init__(self, name, size=0, parent=None, children=None):
        self.name = name
        self.size = size
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = {}
        for child in self.children.values():
            child.parent = self

    def __getitem__(self, key):
        return self.children[key]

    def __setitem__(self, key, value):
        self.children[key] = value
        if isinstance(value, SystemTreeNode):
            value.parent = self

    def matchFilter(self, fullPath, filters):
        for toExclude in filters:
            if re.match(toExclude, fullPath):
                return True
        return False

    def update(self, parentPath, filters):
        fullPath = os.path.join(parentPath, self.name)
        if self.matchFilter(fullPath, filters):
            return 0
        elif self.children:
            childrenSum = 0
            for child in self.children.values():
                childrenSum += child.update(fullPath, filters)
            return self.size + childrenSum
        return self.size

    def navigateToNode(self, path):
        head = path
        folders = []
        current = self
        while head:
            if head == os.sep:
                break
            head, tail = os.path.split(head)
            folders.insert(0, tail)
        for child in folders:
            current = current[child]
        return current

    @staticmethod
    def createStubTree():
        '''n1 = SystemTreeNode("N1", 1)
        n2 = SystemTreeNode("N2", 2)
        n3 = SystemTreeNode("N3", 3)
        n4 = SystemTreeNode("N4", 4)
        n5 = SystemTreeNode("N5", 5)
        n6 = SystemTreeNode("N6", 6)
        n1.children += [n2, n4]
        n2.children += [n3, n5]
        n5.children += [n6]'''
        root = SystemTreeNode("1", 1)
        root["2"] = SystemTreeNode("2", 2)
        root["2"]["3"] = SystemTreeNode("3", 3)
        root["2"]["5"] = SystemTreeNode("5", 5)
        root["2"]["5"]["6"] = SystemTreeNode("6", 6)
        root["4"] = SystemTreeNode("4", 4)
        return root

    @staticmethod
    def createSystemTree(rootFolder="."):
        import os
        rootPath = os.path.abspath(rootFolder)
        head, tail = os.path.split(rootPath)
        rootNode = SystemTreeNode(tail)
        for root, dirs, files, rootfd in os.fwalk(rootPath):
            partialPath = removePrefix(root, rootPath)
            current = rootNode.navigateToNode(partialPath)
            for folder in dirs:
                current[folder] = SystemTreeNode(folder)
            for file in files:
                try:
                    current[file] = SystemTreeNode(file, os.stat(file, dir_fd=rootfd).st_size)
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
