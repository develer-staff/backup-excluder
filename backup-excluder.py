#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QPlainTextEdit
from model import SystemTreeNode

class ExampleItem(QTreeWidgetItem):
	def __init__(self, parent, data):
		super().__init__(parent)
		self.setText(0, data.name)
		self.setText(1, str(data.size))
		

class Example(QMainWindow):

	def __init__(self):
		super().__init__()
		self.customInit()
		
	def customInit(self):
		self.tree = QTreeWidget()
		self.tree.setColumnCount(2)
		self.root = SystemTreeNode.createStubTree()
		self.initStubTree()
		
		v1 = QVBoxLayout()
		v1.addWidget(self.tree)
		
		self.edit = QPlainTextEdit()
		self.confirm = QPushButton("apply filters")
		self.confirm.clicked.connect(self.dosomething)
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
		self.dosomething(None)

	def initStubTree(self):
		n1 = ExampleItem(self.tree, self.root)
		n2 = ExampleItem(n1, self.root.children[0])
		n3 = ExampleItem(n2, self.root.children[0].children[0])
		n4 = ExampleItem(n1, self.root.children[1])
		n5 = ExampleItem(n2, self.root.children[0].children[1])
		n6 = ExampleItem(n5, self.root.children[0].children[1].children[0])

	def dosomething(self, sender):
		filters = self.edit.document().toPlainText().split("\n")
		if filters == ['']:
			filters = []
		self.statusBar().showMessage("Total sum: " + str(self.root.update("", filters)))


if __name__ == '__main__':

	app = QApplication(sys.argv)
	w = Example()
	retVal = app.exec_()
	del w
	del app
	sys.exit(retVal)
	
		
	
