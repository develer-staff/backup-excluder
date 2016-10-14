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
        self._colorBackground(self.brushes[exclusionState])
        self.setText(1, humanize_bytes(actualSize))
        self.setText(2, ExampleItem.percentFormat.format(ratio))
        if exclusionState == SystemTreeNode.DIRECTLY_EXCLUDED:
            # we update all the children because the model won't inspect them
            for i in range(0, self.childCount()):
                self.child(i)._update_visibility(exclusionState, 0)

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
        self.basePath = ""
        self.root = None
        self.totalNodes = 0
        self.matchRoot = False

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["File System", "Size", "%", "Uncut Size"])
        self.tree.header().resizeSection(0, 250)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("No path matched")

        self.rootFolderDisplay = QLabel()

        self.infolabel = QLabel("""<strong>Filters list</strong><br/>
            Regex accepted<br/>""")
        self.infolabel.setWordWrap(True)
        self.matchRootLabel = QLabel("<span style='color:red'><em>Matching starts from the root path</em></span>")
        self.matchRootLabel.setWordWrap(True)
        self.matchRootLabel.setVisible(self.matchRoot)

        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("No filters")

        self.confirm = QPushButton("apply filters")
        self.confirm.clicked.connect(self.applyFilters)

        v1 = QVBoxLayout()
        v1.addWidget(self.rootFolderDisplay)
        v1.addWidget(self.tree)
        v1.addWidget(self.output)
        leftPane = QWidget()
        leftPane.setLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(self.infolabel)
        v2.addWidget(self.matchRootLabel)
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
        self._createSystemTree(initialPath)

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

        treeviewIcon = QIcon.fromTheme("format-indent-more")
        treeviewAction = QAction(treeviewIcon, "File system tree view", self, checkable=True)
        treeviewAction.triggered.connect(self._showTreeView)

        listviewIcon = QIcon.fromTheme("format-justify-fill")
        listviewAction = QAction(listviewIcon, "Excluded paths list view", self, checkable=True)
        listviewAction.triggered.connect(self._showListView)

        matchFromRootIcon = QIcon.fromTheme("tools-check-spelling")
        matchFromRootAction = QAction(matchFromRootIcon, "Match also root path", self, checkable=True)
        matchFromRootAction.triggered.connect(self._toggle_match_root)

        manageToolBar = QToolBar()
        manageToolBar.addAction(openAction)
        manageToolBar.addAction(saveAction)
        manageToolBar.addAction(refreshAction)
        manageToolBar.addAction(matchFromRootAction)
        viewToolBar = QToolBar()
        viewToolBar.addAction(treeviewAction)
        viewToolBar.addAction(listviewAction)

        self.addToolBar(manageToolBar)
        self.addToolBar(viewToolBar)
        self.insertToolBarBreak(manageToolBar)
        self.treeview = treeviewAction
        self.listview = listviewAction

    def _update_basePath(self, path):
        self.rootFolderDisplay.setText("root path: <strong>" + path + "</strong>")

    def _notifyStatus(self, message):
        self.statusBar().showMessage(message)

    def _notifyBackupStatus(self, finalSize, usedNodes):
        self._notifyStatus("Backup size: {} (using {}/{} nodes)".format(
            humanize_bytes(finalSize), usedNodes, self.totalNodes))

    def _clear_widgets(self):
        self.edit.clear()
        self.tree.clear()
        self.output.clear()

    def _createSystemTree(self, initialPath):
        self._notifyStatus("Please wait...reading file system. It may take a while.")
        self.tree.setEnabled(False)
        self.output.setEnabled(False)
        self._clear_widgets()
        self.basePath, self.root, self.totalNodes = SystemTreeNode.createSystemTree(initialPath)
        ExampleItem.fromSystemTree(self.tree, self.root)
        self._update_basePath(self.basePath)
        self._listen_for_excluded_paths(self.root)
        self._notifyBackupStatus(self.root.size, self.totalNodes)
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
            return True
        return False

    def _saveToFile(self):
        fileName, fileExtension = QFileDialog.getSaveFileName(
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

    def _toggle_match_root(self):
        self.matchRoot = not self.matchRoot
        self.matchRootLabel.setVisible(self.matchRoot)
        matching = "" if self.matchRoot else "NOT "
        self._notifyStatus("Switched to "+matching+"match root path. Views are NOT updated. Apply filters again.")

    def _manageExcludedPath(self, newPath):
        self.output.append(removePrefix(newPath, self.basePath))

    def _listen_for_excluded_paths(self, root):
        root.excludedPathFound.connect(self._manageExcludedPath)
        for child in root.children.values():
            self._listen_for_excluded_paths(child)

    def applyFilters(self, sender):
        self._notifyStatus("Please wait...applying filters.")
        filters = filter(str.strip, self.edit.document().toPlainText().split("\n"))
        filterExpr = '(' + '|'.join(filters) + ')'
        if filterExpr == "()":
            filterExpr = "^$"
        cutFunction = re.compile(filterExpr).match
        self.output.document().clear()
        base = self.basePath if self.matchRoot else ""
        finalSize, nodesCount = self.root.update(base, cutFunction)
        self._notifyBackupStatus(finalSize, nodesCount)


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
