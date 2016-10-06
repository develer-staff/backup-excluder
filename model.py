import re
import os


def removePrefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


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
            raise Exception
        self.children[child.name] = child
        child.parent = self

    def getChild(self, childName):
        return self.children[childName]

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
            current = current.getChild(child)
        return current

    @staticmethod
    def createStubTree():
        root = SystemTreeNode("1", 1, children={
            "2": SystemTreeNode("2", 2, children={
                "3": SystemTreeNode("3", 3),
                "5": SystemTreeNode("5", 5, children={
                    "6": SystemTreeNode("6", 6)}
                )}
            ),
            "4": SystemTreeNode("4", 4)})
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
