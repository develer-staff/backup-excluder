#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QPlainTextEdit
from PyQt5.QtGui import QBrush, QColor
from model import SystemTreeNode
from scripts.dirsize import humanize_bytes
import re


class ExampleItem(QTreeWidgetItem):

    orangeBrush = QBrush(QColor("orange"))
    yellowBrush = QBrush(QColor("yellow"))
    whiteBrush = QBrush(QColor("white"))

    def __init__(self, parent, data):
        super().__init__(parent)
        self.setText(0, data.name)
        self.setText(1, humanize_bytes(data.size))
        data.visibilityChanged.connect(self.update_visibility)

    def update_visibility(self, exclusionState):

        if exclusionState == SystemTreeNode.DIRECTLY_EXCLUDED:
            self.setBackground(0, self.orangeBrush)
            self.setBackground(1, self.orangeBrush)
            # we update all the child because the model won't inspect them
            for i in range(0, self.childCount()):
                self.child(i).update_visibility(exclusionState)
        elif exclusionState == SystemTreeNode.PARTIALLY_INCLUDED:
            self.setBackground(0, self.yellowBrush)
            self.setBackground(1, self.yellowBrush)
        elif exclusionState == SystemTreeNode.FULLY_INCLUDED:
            self.setBackground(0, self.whiteBrush)
            self.setBackground(1, self.whiteBrush)

    @staticmethod
    def fromSystemTree(parent, data):
        root = ExampleItem(parent, data)
        for node in sorted(data.children):
            ExampleItem.fromSystemTree(root, data.getChild(node))
        return root


class Example(QMainWindow):

    def __init__(self, basePath):
        super().__init__()
        self.customInit(basePath)

    def customInit(self, basePath):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["File System", "Size"])
        self.tree.header().resizeSection(0, 250)
        self.basePath, self.root = SystemTreeNode.createSystemTree(basePath)
        ExampleItem.fromSystemTree(self.tree, self.root)

        v1 = QVBoxLayout()
        v1.addWidget(self.tree)

        self.edit = QPlainTextEdit()
        self.confirm = QPushButton("apply filters")
        self.confirm.clicked.connect(self.applyFilters)
        v2 = QVBoxLayout()
        v2.addWidget(self.confirm)
        v2.addWidget(self.edit)
        v2.addStretch(1)

        h1 = QHBoxLayout()
        h1.addLayout(v1)
        h1.addLayout(v2)

        self.statusBar()
        tempWidget = QWidget()
        tempWidget.setLayout(h1)
        self.setCentralWidget(tempWidget)
        self.setGeometry(10, 100, 800, 600)
        self.show()
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
