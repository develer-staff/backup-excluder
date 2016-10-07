#!/usr/shared/python3
# -*- coding: utf-8 -*-

import unittest
import re
from model import SystemTreeNode


class TestSystemTreeNode(unittest.TestCase):

    def setUp(self):
        self.root = SystemTreeNode("1", 1, children={
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
        fakeNode = {'name': 'bNode', 'size': 1}
        self.assertRaises(Exception, self.root.addChild, fakeNode)
        del aNode

    def test_navigateToNode_existing_node(self):
        n1 = self.root
        n2 = self.root.getChild("2")
        n3 = self.root.getChild("2").getChild("3")
        n5 = self.root.getChild("2").getChild("5")
        self.assertEqual(n1.navigateToNode("/2/3"), n3)
        self.assertEqual(n1.navigateToNode("2/3"), n3)
        self.assertEqual(n2.navigateToNode("/5"), n5)
        self.assertEqual(n2.navigateToNode("5"), n5)

    def test_navigateToNode_nonexisting_node(self):
        self.assertRaises(KeyError, self.root.navigateToNode,
                          "bad/node/from/start")
        self.assertRaises(KeyError, self.root.navigateToNode,
                          "2/3/bad/node")

    def test_navigateToNode_bad_path(self):
        self.assertRaises(KeyError, self.root.navigateToNode, "/1/2/3")
        self.assertRaises(KeyError, self.root.navigateToNode, "/2/3/")
        n5 = self.root.getChild("2").getChild("5")
        self.assertRaises(KeyError, n5.navigateToNode, "/2/3")

    def test_update_mock_regex(self):
        # ignore cutFunction
        fullsize = self.root.update("", lambda x: False)
        self.assertEqual(fullsize, 21)
        nosize = self.root.update("", lambda x: True)
        self.assertEqual(nosize, 0)

    def _perform_update_with_regex(self, node, parentPath,
                                   regex, expectedResult):
        result = node.update(parentPath, re.compile(regex).match)
        self.assertEqual(result, expectedResult)

    def test_update_valid_regex(self):
        # supply cutFunction matching a leaf node
        expectedResult = 21 - 6
        self._perform_update_with_regex(self.root, "", "1/2/5/6",
                                        expectedResult)
        # supply cutFunction matching a inner node
        expectedResult = 21 - (2 + 3 + 5 + 6)
        self._perform_update_with_regex(self.root, "", "1/2", expectedResult)

    def test_update_parent_path(self):
        # supply an invalid parentPath
        self._perform_update_with_regex(self.root, "invalid/parent/path",
                                        "1/2", 21)
        # supply a valid parentPath
        startingNode = self.root.getChild("2").getChild("5")
        self._perform_update_with_regex(startingNode, "1/2", "1/2/5/6", 5)


if __name__ == '__main__':
    unittest.main()
