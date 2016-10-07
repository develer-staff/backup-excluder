#!/usr/shared/python3
# -*- coding: utf-8 -*-

import unittest
import re
from model import SystemTreeNode


class TestSystemTreeNode(unittest.TestCase):

    def setUp(self):
        self.root =  SystemTreeNode("1", 1, children={
            "2": SystemTreeNode("2", 2, children={
                "3": SystemTreeNode("3", 3),
                "5": SystemTreeNode("5", 5, children={
                    "6": SystemTreeNode("6", 6)
                })
            }),
            "4": SystemTreeNode("4", 4)})

    def tearDown(self):
        del self.root

    def test_addChild(self):
        aNode = SystemTreeNode("aNode", 2)
        self.root.addChild(aNode)
        self.assertEqual(aNode.parent, self.root)
        self.assertTrue(aNode.name in self.root.children)
        self.assertEqual(self.root.children[aNode.name], aNode)
        self.assertRaises(Exception, self.root.addChild, {'name': 'bNode', 'size': 1})
        del aNode

    def test_navigateToNode(self):
        n1 = self.root
        n2 = self.root.getChild("2")
        n3 = self.root.getChild("2").getChild("3")
        n5 = self.root.getChild("2").getChild("5")
        self.assertEqual(n1.navigateToNode("/2/3"), n3)
        self.assertEqual(n1.navigateToNode("2/3"), n3)
        self.assertEqual(n2.navigateToNode("/5"), n5)
        self.assertEqual(n2.navigateToNode("5"), n5)
        self.assertRaises(KeyError, n1.navigateToNode, "/1/2/3")
        self.assertRaises(KeyError, n1.navigateToNode, "/2/3/")
        self.assertRaises(KeyError, n3.navigateToNode, "/2/3")

    def test_update(self):
        #ignore cutFunction
        fullsize = self.root.update("", lambda x: False)
        self.assertEqual(fullsize, 21)
        nosize = self.root.update("", lambda x: True)
        self.assertEqual(nosize, 0)
        #supply cutFunction matching a node with no subtree
        exclude6 = self.root.update("", re.compile("1/2/5/6").match)
        self.assertEqual(exclude6, 21 - 6)
        #supply cutFunction matching a node with a non-empty subtree
        exclude2 = self.root.update("", re.compile("1/2").match)
        self.assertEqual(exclude2, 21 - 6 - 5 - 3 -2)
        #supply an invalid parentPath
        invalidParentPath = self.root.update("invalid/parent/path", re.compile("1/2").match)
        self.assertEqual(invalidParentPath, 21)
        #supply a valid parentPath
        startingNode = self.root.getChild("2").getChild("5")
        validParentPath = startingNode.update("1/2", re.compile("1/2/5/6").match)
        self.assertEqual(validParentPath, 5)



if __name__ == '__main__':
    unittest.main()