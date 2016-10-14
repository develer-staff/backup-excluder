#!/usr/shared/python3
# -*- coding: utf-8 -*-

import unittest
import re
from model import SystemTreeNode, BadElementException


class TestSystemTreeNode(unittest.TestCase):

    def setUp(self):
        # Leaf nodes have size != 0
        # Internal nodes have size == 0 ... their size will
        # be updated when children are inserted
        self.root = SystemTreeNode("10", 0, children={
            "6": SystemTreeNode("6", 0, children={
                "1": SystemTreeNode("1", 1),
                "5": SystemTreeNode("5", 0, children={
                    "2": SystemTreeNode("2", 2),
                    "3": SystemTreeNode("3", 3)
                })
            }),
            "4": SystemTreeNode("4", 4)})

    def _test_addChild_params(self, parent, child):
        self.assertEqual(child.parent, parent)
        self.assertTrue(child.name in parent.children)
        self.assertEqual(parent.children[child.name], child)

    def test_addChild_to_root(self):
        aNode = SystemTreeNode("aNode", 2)
        self.root.addChild(aNode)
        self._test_addChild_params(self.root, aNode)
        self.assertEqual(self.root.size, 12)

    def test_addChild_near_leaf(self):
        aNode = SystemTreeNode("aNode", 10)
        n5 = self.root.getChild("6").getChild("5")
        n5.addChild(aNode)
        self._test_addChild_params(n5, aNode)
        self.assertEqual(n5.size, 15)
        self.assertEqual(n5.parent.size, 16)
        self.assertEqual(self.root.size, 20)

    def test_addChild_add_tree(self):
        tree = SystemTreeNode("60", 0, children={
            "10": SystemTreeNode("10", 10),
            "20": SystemTreeNode("20", 20),
            "30": SystemTreeNode("30", 30)
            })
        n5 = self.root.getChild("6").getChild("5")
        n5.addChild(tree)
        self._test_addChild_params(n5, tree)
        self.assertEqual(n5.size, 65)
        self.assertEqual(n5.parent.size, 66)
        self.assertEqual(self.root.size, 70)

    def test_addChild_fake(self):
        fakeNode = {'name': 'bNode', 'size': 1}
        with self.assertRaises(BadElementException):
            self.root.addChild(fakeNode)

    def test_update_mock_regex(self):
        # ignore cutFunction
        fullsize, nodesCount = self.root.update("", lambda x: False)
        self.assertEqual(fullsize, 10)
        self.assertEqual(nodesCount, 7)
        nosize, nodesCount = self.root.update("", lambda x: True)
        self.assertEqual(nosize, 0)
        self.assertEqual(nodesCount, 0)

    def _test_perform_update_with_regex(self, node, parentPath,
                                        regex, expectedSize, expectedNodes):
        result, nodes = node.update(parentPath, re.compile(regex).match)
        self.assertEqual(result, expectedSize)
        self.assertEqual(nodes, expectedNodes)

    def test_update_valid_regex(self):
        # supply cutFunction matching a leaf node
        expectedResult = 10 - 2
        self._test_perform_update_with_regex(self.root, "", "10/6/5/2",
                                             expectedResult, 6)
        # supply cutFunction matching a inner node
        expectedResult = 10 - (1 + 2 + 3)
        self._test_perform_update_with_regex(self.root, "", "10/6",
                                             expectedResult, 2)

    def test_update_parent_path(self):
        # supply an invalid parentPath
        self._test_perform_update_with_regex(self.root, "invalid/parent/path",
                                             "10/6", 10, 7)
        # supply a valid parentPath
        startingNode = self.root.getChild("6").getChild("5")
        self._test_perform_update_with_regex(startingNode, "10/6", "10/6/5/3",
                                             2 ,2)


if __name__ == '__main__':
    unittest.main()
