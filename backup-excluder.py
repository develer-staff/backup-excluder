#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QPushButton, QWidget, QPlainTextEdit, QSplitter
from PyQt5.QtGui import QBrush, QColor
from model import SystemTreeNode
from scripts.dirsize import humanize_bytes
import re


class ExampleItem(QTreeWidgetItem):

    percentFormat = "{:.1%}"
    orangeBrush = QBrush(QColor("orange"))
    yellowBrush = QBrush(QColor("yellow"))
    whiteBrush = QBrush(QColor("white"))

    def __init__(self, parent, data):
        super().__init__(parent)
        self.setText(0, data.name)
        self.uncutSize = data.size
        if self.uncutSize > 0:
            # Update the size of parents. Folder's size is 0 by default,
            # this way it accounts for the files it contains.
            sup = self.parent()
            while sup and isinstance(sup, ExampleItem):
                sup.uncutSize += self.uncutSize
                sup = sup.parent()
        data.visibilityChanged.connect(self._update_visibility)

    def _colorBackground(self, brush):
        self.setBackground(0, brush)
        self.setBackground(1, brush)
        self.setBackground(2, brush)
        self.setBackground(3, brush)

    def _update_visibility(self, exclusionState, actualSize):
        theBrush = None
        ratio = float(actualSize)/max([self.uncutSize, 1.0])
        if exclusionState == SystemTreeNode.DIRECTLY_EXCLUDED:
            theBrush = self.orangeBrush
            # we update all the children because the model won't inspect them
            for i in range(0, self.childCount()):
                self.child(i)._update_visibility(exclusionState, 0)
        elif exclusionState == SystemTreeNode.PARTIALLY_INCLUDED:
            theBrush = self.yellowBrush
        elif exclusionState == SystemTreeNode.FULLY_INCLUDED:
            theBrush = self.whiteBrush
        self._colorBackground(theBrush)
        self.setText(1, humanize_bytes(actualSize))
        self.setText(2, ExampleItem.percentFormat.format(ratio))

    @staticmethod
    def fromSystemTree(parent, data):
        root = ExampleItem(parent, data)
        for node in sorted(data.children):
            ExampleItem.fromSystemTree(root, data.getChild(node))
        # Update here the display of the size because we need to complete
        # the subtree roted in root before showing its uncutSize
        root.setText(1, humanize_bytes(root.uncutSize))
        root.setText(2, ExampleItem.percentFormat.format(100))
        root.setText(3, humanize_bytes(root.uncutSize))
        return root


class Example(QMainWindow):

    def __init__(self, basePath):
        super().__init__()
        self.customInit(basePath)

    def customInit(self, basePath):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["File System", "Size", "%", "Uncut Size"])
        self.tree.header().resizeSection(0, 250)
        self.basePath, self.root = SystemTreeNode.createSystemTree(basePath)
        ExampleItem.fromSystemTree(self.tree, self.root)

        v1 = QVBoxLayout()
        v1.addWidget(self.tree)
        self.edit = QPlainTextEdit()
        self.confirm = QPushButton("apply filters")
        self.confirm.clicked.connect(self.applyFilters)
        leftPane = QWidget()
        leftPane.setLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(self.confirm)
        v2.addWidget(self.edit)
        v2.addStretch(1)
        rightPane = QWidget()
        rightPane.setLayout(v2)

        splitter = QSplitter()
        splitter.addWidget(leftPane)
        splitter.addWidget(rightPane)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.statusBar()
        self.setCentralWidget(splitter)
        self.setGeometry(10, 100, 800, 600)
        self.show()
        # Update tree view with default filters
        self.applyFilters(None)

    def initStubTree(self):
        n1 = ExampleItem(self.tree, self.root)
        n2 = ExampleItem(n1, self.root.children[0])
        n3 = ExampleItem(n2, self.root.children[0].children[0])
        n4 = ExampleItem(n1, self.root.children[1])
        n5 = ExampleItem(n2, self.root.children[0].children[1])
        n6 = ExampleItem(n5, self.root.children[0].children[1].children[0])

    def applyFilters(self, sender):
        filters = filter(str.strip, self.edit.document().toPlainText().split("\n"))
        filterExpr = '(' + '|'.join(filters) + ')'
        if filterExpr == "()":
            filterExpr = "^$"
        cutFunction = re.compile(filterExpr).match
        finalSize = self.root.update(self.basePath, cutFunction)
        self.statusBar().showMessage("Total sum: " + humanize_bytes(finalSize))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='backup excluder')
    parser.add_argument('start', nargs='?', default='.')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = Example(args.start)
    retVal = app.exec_()
    del window
    del app
    sys.exit(retVal)


if __name__ == '__main__':
    main()
