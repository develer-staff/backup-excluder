import re

class SystemTreeNode:

	name = None
	size = None
	children = None
	
	def __init__(self, name, size):
		self.name = name
		self.size = size
		self.children = []

	def matchFilter(self, fullPath, filters):
		for toExclude in filters:
			if re.match(toExclude, fullPath):
				return True
		return False
	
	def update(self, parentPath, filters):
		fullPath = parentPath + "/" + self.name
		# assuming that filters can be removed, we must check even for
		# already excluded elemnts.
		if self.matchFilter(fullPath, filters): 
			return 0
		elif self.children :
			childrenSum = 0
			for child in self.children:
				childrenSum += child.update(fullPath, filters)
			return self.size + childrenSum
		
		return self.size
		
	@staticmethod
	def createStubTree():
		n1 = SystemTreeNode("N1", 1)
		n2 = SystemTreeNode("N2", 2)
		n3 = SystemTreeNode("N3", 3)
		n4 = SystemTreeNode("N4", 4)
		n5 = SystemTreeNode("N5", 5)
		n6 = SystemTreeNode("N6", 6)
		n1.children += [n2, n4]
		n2.children += [n3, n5]
		n5.children += [n6]
		return n1

	
