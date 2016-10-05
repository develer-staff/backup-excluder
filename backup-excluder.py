#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QPlainTextEdit
from model import SystemTreeNode
from scripts.dirsize import humanize_bytes


class ExampleItem(QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent)
        self.setText(0, data.name)
        self.setText(1, humanize_bytes(data.size))

    @staticmethod
    def fromSystemTree(parent, data):
        root = ExampleItem(parent, data)
        for node in sorted(data.children):
            ExampleItem.fromSystemTree(root, data[node])
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
        filters = [x.strip() for x in self.edit.document().toPlainText().split("\n") if x.strip()]
        finalSize = self.root.update(self.basePath, filters)
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
