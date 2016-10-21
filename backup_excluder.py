#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import re
import os
import threading

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
        QPushButton, QWidget, QPlainTextEdit, QSplitter, QTextEdit, QAction,
        QToolBar, QFileDialog, QLabel, QMenu, QAbstractItemView)
    from PyQt5.QtGui import QBrush, QColor, QIcon
    from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication, QSettings, QTranslator
except ImportError:
    print("Need PyQt5")
    print("pip install backup_excluder[qt]")
    raise

from model import SystemTreeNode
from scripts.dirsize import humanize_bytes


infoLabelText = ""
matchRootLabelText = ""
filtersErrorText = ""
filtersValidLabelText = ""
waitStatus1 = ""
waitStatus2 = ""
waitStatus3 = ""
toggleMatchRootStatusYes = ""
toggleMatchRootStatusNo = ""


def matchNothing(ignored):
    return False


class SystemTreeWidgetNode(QTreeWidgetItem):

    percentTemplate = "{:.1%}"
    brushes = {
        SystemTreeNode.DIRECTLY_EXCLUDED: QBrush(QColor("orange")),
        SystemTreeNode.PARTIALLY_INCLUDED: QBrush(QColor("yellow")),
        SystemTreeNode.FULLY_INCLUDED: QBrush(QColor("white"))
    }

    def __init__(self, parent, data):
        super().__init__(parent)
        self.setText(0, data.name)
        self._uncutSize = data.subtreeTotalSize
        self._cutSize = data.subtreeTotalSize
        self.setText(1, humanize_bytes(self._cutSize))
        self.setText(2, SystemTreeWidgetNode.percentTemplate.format(1))
        self.setText(3, humanize_bytes(self._uncutSize))
        data.visibilityChangedHandler = self._update_visibility

    def __lt__(self, other):
        col = self.treeWidget().sortColumn()
        if col == 1:
            return self._cutSize < other._cutSize
        elif col == 2:
            selfPercentage = float(self.text(2).strip("%"))
            otherPercentage = float(other.text(2).strip("%"))
            return selfPercentage < otherPercentage
        elif col == 3:
            return self._uncutSize < other._uncutSize
        else:
            return super().__lt__(other)

    def _colorBackground(self, brush):
        self.setBackground(0, brush)
        self.setBackground(1, brush)
        self.setBackground(2, brush)
        self.setBackground(3, brush)

    def _update_visibility(self, exclusionState, actualSize):
        self._cutSize = actualSize
        ratio = float(actualSize)/max([self._uncutSize, 1.0])
        self._colorBackground(self.brushes[exclusionState])
        self.setText(1, humanize_bytes(actualSize))
        self.setText(2, SystemTreeWidgetNode.percentTemplate.format(ratio))
        if exclusionState == SystemTreeNode.DIRECTLY_EXCLUDED:
            # Update all the descendant children because the model won't
            # send any event/call any callback for these nodes.
            for i in range(0, self.childCount()):
                self.child(i)._update_visibility(exclusionState, 0)
        QCoreApplication.processEvents()

    def getFullPath(self):
        node = self.parent()
        result = self.text(0)
        while isinstance(node, QTreeWidgetItem):
            result = os.path.join(node.text(0), result)
            node = node.parent()
        return result

    @staticmethod
    def fromSystemTree(parent, data):
        root = SystemTreeWidgetNode(parent, data)
        for node in data.children:
            SystemTreeWidgetNode.fromSystemTree(root, data.getChild(node))
        QCoreApplication.processEvents()
        return root


class WorkerThread(threading.Thread):

    def __init__(self, mainThread, initialPath):
        super().__init__()
        self.mainThread = mainThread
        self.initialPath = initialPath

    def run(self):
        callback = self.mainThread._createSystemTreeAsyncEnd
        workerObject = WorkerObject(self.mainThread)
        workerObject.moveToThread(QApplication.instance().thread())
        workerObject.workFinished.connect(callback)
        workerObject.doWork(self.initialPath)


class WorkerObject(QObject):

    workFinished = pyqtSignal()

    def __init__(self, parent):
        super().__init__(None)
        self.mainThread = parent

    def doWork(self, initialPath):
        a, b, c = SystemTreeNode.createSystemTree(initialPath)
        self.mainThread.basePath = a
        self.mainThread.root = b
        self.mainThread.totalNodes = c
        self.workFinished.emit()


class BackupExcluderWindow(QMainWindow):

    startWork = pyqtSignal(str)

    def __init__(self, initialPath):
        super().__init__()
        self._customInit(os.path.abspath(initialPath))

    def _customInit(self, initialPath):
        super().__init__()

        QCoreApplication.setOrganizationName("Develer")
        QCoreApplication.setOrganizationDomain("develer.com")
        QCoreApplication.setApplicationName("Backup excluder")
        self.settings = QSettings()

        self.basePath = self.settings.value("config/basePath", initialPath)
        self.root = None
        self.totalNodes = 0
        self.matchRoot = self.settings.value("config/matchRoot",
                                             False, type=bool)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels([
            self.tr("File System"),
            self.tr("Backup Size"),
            "%",
            self.tr("Full Size")])
        self.tree.header().resizeSection(0, 250)
        self.tree.setEnabled(False)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(self.tr("No paths matched"))

        self.rootFolderDisplay = QLabel()

        self.infoLabel = QLabel(infoLabelText)
        self.infoLabel.setWordWrap(True)
        self.filtersValidLabel = QLabel(filtersValidLabelText)
        self.filtersValidLabel.setWordWrap(True)
        self.filtersValidLabel.setVisible(True)
        self.matchRootLabel = QLabel(matchRootLabelText)
        self.matchRootLabel.setWordWrap(True)
        self.matchRootLabel.setVisible(self.matchRoot)

        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText(self.tr("No filters"))
        self.edit.setPlainText(self.settings.value("editor/filters"))

        self.confirm = QPushButton(self.tr("Apply filters"))
        self.confirm.clicked.connect(self.applyFilters)

        v1 = QVBoxLayout()
        v1.addWidget(self.rootFolderDisplay)
        v1.addWidget(self.tree)
        v1.addWidget(self.output)
        leftPane = QWidget()
        leftPane.setLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(self.infoLabel)
        v2.addWidget(self.filtersValidLabel)
        v2.addWidget(self.matchRootLabel)
        v2.addWidget(self.edit)
        v2.addWidget(self.confirm)
        v2.addStretch(1)
        rightPane = QWidget()
        rightPane.setLayout(v2)

        splitter = QSplitter()
        splitter.addWidget(leftPane)
        splitter.addWidget(rightPane)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        self._initToolBar()

        self.statusBar()
        self.setCentralWidget(splitter)
        self.setGeometry(10, 100, 800, 600)
        self.treeview.trigger()

        # initial visualization: no tree to avoid (possible) long wait,
        # display of initial path (with hint of refresh), disable filters
        moreInfo = self.tr("(refresh to show tree)")
        self._update_basePath(self.basePath + os.sep, moreInfo)
        self.confirm.setEnabled(False)

        self.show()

    def _initToolBar(self):

        openIcon = QIcon.fromTheme("folder-open")
        openAction = QAction(
            openIcon, self.tr("Select root folder"), self)
        openAction.triggered.connect(self._selectRootFolder)

        saveIcon = QIcon.fromTheme("document-save")
        saveAction = QAction(
            saveIcon, self.tr("Save excluded paths"), self)
        saveAction.triggered.connect(self._saveToFile)

        refreshIcon = QIcon.fromTheme("view-refresh")
        refreshAction = QAction(
            refreshIcon, self.tr("Refresh from file system"), self)
        refreshAction.triggered.connect(self._refreshFileSystem)

        treeviewIcon = QIcon.fromTheme("format-indent-more")
        treeviewAction = QAction(
            treeviewIcon, self.tr("File system tree view"),
            self, checkable=True)
        treeviewAction.triggered.connect(self._showTreeView)

        listviewIcon = QIcon.fromTheme("format-justify-fill")
        listviewAction = QAction(
            listviewIcon, self.tr("Excluded paths list view"),
            self, checkable=True)
        listviewAction.triggered.connect(self._showListView)

        matchFromRootIcon = QIcon.fromTheme("tools-check-spelling")
        matchFromRootAction = QAction(
            matchFromRootIcon, self.tr("Include/exclude root path from match"),
            self, checkable=True)
        matchFromRootAction.setChecked(self.matchRoot)
        matchFromRootAction.triggered.connect(self._toggle_match_root)

        excludeFolderIcon = QIcon.fromTheme("user-trash")
        excludeFolderAction = QAction(
            excludeFolderIcon, self.tr("Exclude item"), self)
        excludeFolderAction.triggered.connect(self._exclude_item)

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
        self.save = saveAction
        self.open = openAction
        self.refresh = refreshAction
        self.exclude = excludeFolderAction

    def _exclude_item(self, boh):
        if self.matchRoot:
            basePath = self.basePath
        else:
            basePath = ""
        items = self.tree.selectedItems()
        for item in items:
            treePath = item.getFullPath()
            # we want to remove the root from the path, because it is
            # not used for matching. +1 becasue of the separator.
            if treePath.startswith(self.root.name):
                treePath = treePath[len(self.root.name)+1:]
            path = os.path.join(basePath, treePath)
            self.edit.appendPlainText(path)
        self.applyFilters(None)

    def contextMenuEvent(self, event):
        if event.reason() == event.Mouse:
            pos = event.globalPos()
            item = self.tree.selectedItems()
            if not item:
                return
        else:
            return
        contextMenu = QMenu(self.tree)
        contextMenu.addAction(self.exclude)
        contextMenu.popup(pos)
        event.accept()

    def _update_basePath(self, path, moreInfo=""):
        labelText = self.tr("Root path") + ": <strong>" + path + "</strong>"
        if moreInfo:
            labelText += " <span style='color:red'>" + moreInfo + "</span>"
        self.rootFolderDisplay.setText(labelText)

    def _notifyStatus(self, message):
        self.statusBar().showMessage(message)

    def _notifyBackupStatus(self, finalSize, usedNodes):
        self._notifyStatus("{}: {} ({}/{} {})".format(
            self.tr("Size"), humanize_bytes(finalSize), usedNodes,
            self.totalNodes, self.tr("Items to backup")))

    def _clear_widgets(self):
        self.tree.clear()
        self.output.clear()
        self.filtersValidLabel.setVisible(True)

    def _setOutputEnabled(self, enabled):
        self.tree.setEnabled(enabled)
        self.output.setEnabled(enabled)
        self.confirm.setEnabled(enabled)
        self.refresh.setEnabled(enabled)
        self.open.setEnabled(enabled)
        self.save.setEnabled(enabled)

    def _createSystemTree(self, initialPath):
        self._createSystemTreeAsyncStart(initialPath)

    def _createSystemTreeAsyncStart(self, initialPath):
        self._notifyStatus(waitStatus1)
        self._setOutputEnabled(False)
        self._clear_widgets()
        worker = WorkerThread(self, initialPath)
        worker.start()

    def _createSystemTreeAsyncEnd(self):
        self._notifyStatus(waitStatus2)
        self.tree.setSortingEnabled(False)
        SystemTreeWidgetNode.fromSystemTree(self.tree, self.root)
        self.tree.setSortingEnabled(True)
        self.tree.expandToDepth(0)
        self._notifyStatus(waitStatus3)
        self._listen_for_excluded_paths(self.root)
        self._update_basePath(self.basePath + os.sep)
        self._notifyBackupStatus(self.root.subtreeTotalSize, self.totalNodes)
        self._setOutputEnabled(True)

    def _selectRootFolder(self):
        newRootFolder = QFileDialog.getExistingDirectory(
            self, self.tr("Select root directory"),
            None, QFileDialog.ShowDirsOnly)
        if newRootFolder:
            self.settings.setValue("config/basePath", newRootFolder)
            self._createSystemTree(newRootFolder)
            return True
        return False

    def _saveToFile(self):
        fileName, fileExtension = QFileDialog.getSaveFileName(
            self, self.tr("Save excluded paths list"), "",
            "Paths excluded list (*.pel);;All Files (*)")
        if not fileName:
            return False
        with open(fileName, "w+") as f:
            f.write(self.output.document().toPlainText())

    def _refreshFileSystem(self):
        self._createSystemTree(self.basePath)

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
        self.settings.setValue("config/matchRoot", self.matchRoot)
        self.matchRootLabel.setVisible(self.matchRoot)
        if self.matchRoot:
            matching = toggleMatchRootStatusYes
        else:
            matching = toggleMatchRootStatusNo
        self._notifyStatus(matching.format(matching))

    def _manageExcludedPath(self, newPath):
        self.output.append(newPath)

    def _listen_for_excluded_paths(self, root):
        root.excludedPathFoundHandler = self._manageExcludedPath
        for child in root.children.values():
            self._listen_for_excluded_paths(child)

    def applyFilters(self, sender):
        self._notifyStatus(self.tr("Please wait...applying filters. It may take a while."))
        self.output.document().clear()
        text = self.edit.document().toPlainText()
        self.settings.setValue("editor/filters", text)
        filters = list(filter(str.strip, text.split("\n")))
        if len(filters) > 0:
            if self.matchRoot:
                base = ""
            else:
                base = self.basePath + os.sep
            filterExpr = base + '(' + '|'.join(filters) + ')'
            try:
                cutFunction = re.compile(filterExpr).match
            except Exception:
                self._notifyStatus(filtersErrorText)
                return
        else:
            cutFunction = matchNothing
        hiddenPath = os.path.dirname(self.basePath)
        self.confirm.setEnabled(False)
        finalSize, nodesCount = self.root.update(hiddenPath, cutFunction)
        self.filtersValidLabel.setVisible(False)
        self.confirm.setEnabled(True)
        self._notifyBackupStatus(finalSize, nodesCount)


def generateTranslations(app):
    global infoLabelText
    infoLabelText = "<strong>{}</strong><br/>{}".format(
        app.translate("BackupExcluderWindow", "Filters list"),
        app.translate("BackupExcluderWindow", "Regex accepted."))
    global matchRootLabelText
    matchRootLabelText = "<span style='color:red'><em>{}</em></span>".format(
        app.translate("BackupExcluderWindow", "Matching also root path"))
    global filtersErrorText
    filtersErrorText = app.translate("BackupExcluderWindow",
        "ERROR: bad format for regex.")
    global filtersValidLabelText
    filtersValidLabelText = "<span style='color:#666'><em>{}</em>".format(
        app.translate("BackupExcluderWindow", "Filters not applyed"))
    global waitStatus1
    waitStatus1 = app.translate("BackupExcluderWindow",
        "Please wait...scanning file system. It may take a while.")
    global waitStatus2
    waitStatus2 = app.translate("BackupExcluderWindow",
        "Please wait...populating tree view. It may take a while.")
    global waitStatus3
    waitStatus3 = app.translate("BackupExcluderWindow",
        "Please wait...connecting tree view. It may take a while.")
    global toggleMatchRootStatusYes
    toggleMatchRootStatusYes = app.translate("BackupExcluderWindow",
        "Switched to match root path. Views are NOT updated. Apply filters again.")
    global toggleMatchRootStatusNo
    toggleMatchRootStatusNo = app.translate("BackupExcluderWindow",
        "Switched to NOT match root path. Views are NOT updated. Apply filters again.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='backup excluder')
    parser.add_argument('start', nargs='?', default='.')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    translator = QTranslator()
    app.installTranslator(translator)
    generateTranslations(app)
    window = BackupExcluderWindow(args.start)
    retVal = app.exec_()
    del window
    del app
    sys.exit(retVal)


if __name__ == '__main__':
    main()
