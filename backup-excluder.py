#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import re
import os

from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QPushButton, QWidget, QPlainTextEdit, QSplitter, QTextEdit, QAction, QToolBar, QFileDialog, QLabel
from PyQt5.QtGui import QBrush, QColor, QIcon

from model import SystemTreeNode, removePrefix
from scripts.dirsize import humanize_bytes


class ExampleItem(QTreeWidgetItem):

    percentFormat = "{:.1%}"
    brushes = {
        SystemTreeNode.DIRECTLY_EXCLUDED: QBrush(QColor("orange")),
        SystemTreeNode.PARTIALLY_INCLUDED: QBrush(QColor("yellow")),
        SystemTreeNode.FULLY_INCLUDED: QBrush(QColor("white"))
    }

    def __init__(self, parent, data):
        super().__init__(parent)
        self.setText(0, data.name)
        self.uncutSize = data.size
        self.setText(1, humanize_bytes(self.uncutSize))
        self.setText(2, ExampleItem.percentFormat.format(1))
        self.setText(3, humanize_bytes(self.uncutSize))

        data.visibilityChanged.connect(self._update_visibility)

    def _colorBackground(self, brush):
        self.setBackground(0, brush)
        self.setBackground(1, brush)
        self.setBackground(2, brush)
        self.setBackground(3, brush)

    def _update_visibility(self, exclusionState, actualSize):
        ratio = float(actualSize)/max([self.uncutSize, 1.0])
        if exclusionState == SystemTreeNode.DIRECTLY_EXCLUDED:
            # we update all the children because the model won't inspect them
            for i in range(0, self.childCount()):
                self.child(i)._update_visibility(exclusionState, 0)
        self._colorBackground(self.brushes[exclusionState])
        self.setText(1, humanize_bytes(actualSize))
        self.setText(2, ExampleItem.percentFormat.format(ratio))

    @staticmethod
    def fromSystemTree(parent, data):
        root = ExampleItem(parent, data)
        for node in sorted(data.children):
            ExampleItem.fromSystemTree(root, data.getChild(node))
        return root


class Example(QMainWindow):

    def __init__(self, initialPath):
        super().__init__()
        self.customInit(initialPath)

    def customInit(self, initialPath):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["File System", "Size", "%", "Uncut Size"])
        self.tree.header().resizeSection(0, 250)
        self.basePath, self.root = SystemTreeNode.createSystemTree(initialPath)
        ExampleItem.fromSystemTree(self.tree, self.root)
        self._listen_for_excluded_paths(self.root)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("No path matched")

        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("No filters")
        self.confirm = QPushButton("apply filters")
        self.confirm.clicked.connect(self.applyFilters)
        self.infolabel = QLabel("Filters list. Regex accepted: matching starts from the root path.")
        self.infolabel.setWordWrap(True)

        v1 = QVBoxLayout()
        v1.addWidget(self.tree)
        v1.addWidget(self.output)
        leftPane = QWidget()
        leftPane.setLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(self.infolabel)
        v2.addWidget(self.edit)
        v2.addWidget(self.confirm)
        v2.addStretch(1)
        rightPane = QWidget()
        rightPane.setLayout(v2)

        splitter = QSplitter()
        splitter.addWidget(leftPane)
        splitter.addWidget(rightPane)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.initToolBar()

        self.statusBar()
        self.setCentralWidget(splitter)
        self.setGeometry(10, 100, 800, 600)
        self.treeview.trigger()
        self.show()
        # Update tree view with default filters
        self.applyFilters(None)

    def initToolBar(self):

        openIcon = QIcon.fromTheme("folder-open")
        openAction = QAction(openIcon, "Select root folder", self)
        openAction.triggered.connect(self._selectRootFolder)

        saveIcon = QIcon.fromTheme("document-save")
        saveAction = QAction(saveIcon, "Save excluded paths", self)
        saveAction.triggered.connect(self._saveToFile)

        refreshIcon = QIcon.fromTheme("view-refresh")
        refreshAction = QAction(refreshIcon, "Refresh from file system", self)
        refreshAction.triggered.connect(self._refreshFileSystem)

        treeviewIcon = QIcon.fromTheme("format-justify-left")
        treeviewAction = QAction(treeviewIcon, "File system tree view", self, checkable=True)
        treeviewAction.triggered.connect(self._showTreeView)

        listviewIcon = QIcon.fromTheme("document-print-preview")
        listviewAction = QAction(listviewIcon, "Excluded paths list view", self, checkable=True)
        listviewAction.triggered.connect(self._showListView)

        manageToolBar = QToolBar()
        manageToolBar.addAction(openAction)
        manageToolBar.addAction(saveAction)
        manageToolBar.addAction(refreshAction)
        viewToolBar = QToolBar()
        viewToolBar.addAction(treeviewAction)
        viewToolBar.addAction(listviewAction)

        self.addToolBar(manageToolBar)
        self.addToolBar(viewToolBar)
        self.insertToolBarBreak(manageToolBar)
        self.treeview = treeviewAction
        self.listview = listviewAction

    def _notifyStatus(self, message):
        self.statusBar().showMessage(message)

    def _createSystemTree(self, initialPath):
        self._notifyStatus("Please wait...reading file system. It may take a while.")
        self.tree.setEnabled(False)
        self.output.setEnabled(False)
        self.tree.clear()
        self.basePath, self.root = SystemTreeNode.createSystemTree(initialPath)
        ExampleItem.fromSystemTree(self.tree, self.root)
        self._listen_for_excluded_paths(self.root)
        self._notifyStatus("Backup sum: " + humanize_bytes(self.root.size))
        self.tree.setEnabled(True)
        self.output.setEnabled(True)

    def _selectRootFolder(self):
        fileDialog = QFileDialog(self)
        fileDialog.setFileMode(QFileDialog.DirectoryOnly)
        newRootFolder = "/home"
        if fileDialog.exec():
            newRootFolder = fileDialog.selectedFiles()
            if len(newRootFolder) != 1:
                self._notifyStatus("Only one folder can be selected as root.")
                return False
            self._createSystemTree(newRootFolder[0])
            print(self.basePath)
            return True
        return False

    def _saveToFile(self):
        fileName = QFileDialog.getSaveFileName(
            self, "Save excluded paths list", "",
            "Paths excluded list (*.pel);;All Files (*)")
        if not fileName:
            return False
        with open(fileName[0], "w+") as f:
            f.write(self.output.document().toPlainText())

    def _refreshFileSystem(self):
        initialPath = os.path.join(self.basePath, self.root.name)
        self._createSystemTree(initialPath)

    def _showTreeView(self):
        self.tree.setVisible(True)
        self.output.setVisible(False)
        self.treeview.setChecked(True)
        self.listview.setChecked(False)

    def _showListView(self):
        self.tree.setVisible(False)
        self.output.setVisible(True)
        self.treeview.setChecked(False)
        self.listview.setChecked(True)

    def _manageExcludedPath(self, newPath):
        self.output.append(removePrefix(newPath, self.basePath))

    def _listen_for_excluded_paths(self, root):
        root.excludedPathFound.connect(self._manageExcludedPath)
        for child in root.children.values():
            self._listen_for_excluded_paths(child)

    def initStubTree(self):
        n1 = ExampleItem(self.tree, self.root)
        n2 = ExampleItem(n1, self.root.children[0])
        n3 = ExampleItem(n2, self.root.children[0].children[0])
        n4 = ExampleItem(n1, self.root.children[1])
        n5 = ExampleItem(n2, self.root.children[0].children[1])
        n6 = ExampleItem(n5, self.root.children[0].children[1].children[0])

    def applyFilters(self, sender):
        self._notifyStatus("Please wait...applying filters.")
        filters = filter(str.strip, self.edit.document().toPlainText().split("\n"))
        filterExpr = '(' + '|'.join(filters) + ')'
        if filterExpr == "()":
            filterExpr = "^$"
        cutFunction = re.compile(filterExpr).match
        self.output.document().clear()
        finalSize = self.root.update(self.basePath, cutFunction)
        self._notifyStatus("Backup sum: " + humanize_bytes(finalSize))


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
