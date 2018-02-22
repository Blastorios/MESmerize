#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan  7 21:14:51 2018

@author: kushal

Chatzigeorgiou Group
Sars International Centre for Marine Molecular Biology

GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
"""

from pyqtgraphCore.Qt import QtCore, QtGui, USE_PYSIDE
from MesmerizeCore import ProjBrowser
from MesmerizeCore import ConfigWindow
from MesmerizeCore import configuration
import pyqtgraphCore
import numpy as np
import pickle
import sys
from MesmerizeCore import packager
from shutil import copyfile
import time
import pandas as pd
import os


'''
Main file to be called. The intent is that if no arguments are passed the standard desktop application loads.
I intend to create a headless mode for doing certain things on a cluster/supercomputer

The instance of MainWindow is useful for communicating between the Viewer & Project Browser
'''

# class main():
#     def __init__(self, args=None):
#         if args is None:
#             self.app = QtGui.QApplication([])
#
#             self.viewer = None
#             self.projName = None

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        # QtGui.QMainWindow.__init__(self)
        super().__init__()
        self.viewer = None
        self.projBrowserWin = None
        self.projName = None
        self.projDf = None
        self.setWindowTitle('Mesmerize')
        self.initMenuBar()
        self.resize(1000,845)
    def initMenuBar(self):
        # Menurbar
        self.menubar = self.menuBar()

        fileMenu = self.menubar.addMenu('&File')

        mBtnNewProj = fileMenu.addAction('New')
        mBtnNewProj.triggered.connect(self.newProjFileDialog)

        mBtnOpenProj = fileMenu.addAction('Open')
        mBtnOpenProj.triggered.connect(self.openProjFileDialog)


        dataframeMenu = self.menubar.addMenu('&DataFrame')

        saveRootDf = dataframeMenu.addAction('Save Root')

        saveChild = dataframeMenu.addAction('Save Current Child')

        saveChildAs = dataframeMenu.addAction('Save Current Child As...')

        saveAllChildren = dataframeMenu.addAction('Save All Children')

        saveAsNewProj = dataframeMenu.addAction('New Project from Current Child')

        deleteChild = dataframeMenu.addAction('Delete Current Child')



        editMenu = self.menubar.addMenu('&Edit')

        changeConfig = editMenu.addAction('Project Configuration')
        changeConfig.triggered.connect(self.openConfigWindow)


    def newProjFileDialog(self):
        # Opens a file dialog to selected a parent dir for a new project
        parentPath = QtGui.QFileDialog.getExistingDirectory(self, 'Choose location for new project')
        if parentPath == '':
            return

        projName, start = QtGui.QInputDialog.getText(self, '', 'Project Name:', QtGui.QLineEdit.Normal, '')

        if start and projName != '':
            self.projPath = parentPath + '/' + projName
            os.mkdir(self.projPath)

            self.newProj()
            # self.projDf = packager.empty_df()


#            self.projDf.to_csv(self.projDfFilePath, index=False)

    def newProj(self):
        self.checkProjOpen()  # If a project is already open, prevent loosing unsaved work
        # setup paths for the project files
        self.setupProjPaths()
        # Initialize a configuration for the project
        self.configwin = ConfigWindow
        configuration.newConfig()
        self.openConfigWindow()
        self.configwin.tabs.widget(0).ui.btnSave.clicked.connect(self.createNewDf)

    def checkProjOpen(self):
        # Function to check if any project is already open to prevnet losing unsaved work.
        if (self.viewer is not None):
            if QtGui.QMessageBox.warning(self, 'Close Viewer Window?', 'Would you like to discard any ' +\
                                                'unsaved work in your Viewer window?', QtGui.QMessageBox.Yes,
                                                QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
                self.viewerWindow.close()
                self.viewer = None
            else:
                return

        if (self.projBrowserWin is not None):
            if QtGui.QMessageBox.warning(self, 'Close Current Project?', 'You currently have a project open, would you' +\
                                          'like to discard any unsaved work and open another project?',
                                         QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
                self.projBrowserWin.close()
                self.projBrowserWin = None
            else:
                return

    def setupProjPaths(self, checkPaths=False):
        # Create important path attributes for the project
        self.projDfsDir = self.projPath + '/dataframes'
        configuration.configpath = self.projPath + '/config.cfg'
        self.projRootDfPath = self.projDfsDir + '/root.mzp'
        self.projName = self.projPath.split('/')[-1]

        # If opening a project check if this is a valid Mesmerize project by checking for paths
        if checkPaths:
            if os.path.isdir(self.projDfsDir) == False:
                QtGui.QMessageBox.warning(self, 'Project DataFrame Directory not found!', 'The selected directory is ' +\
                    'not a valid Mesmerize Project since it doesn\'t contain a DataFrame directory!',
                                          QtGui.QMessageBox.Ok)
                return False
            if (os.path.isfile(self.projRootDfPath) == False):
                QtGui.QMessageBox.warning(self, 'Project Root DataFrame not found!',
                                           'The selected directory does Not contain a Root DataFrame!', QtGui.QMessageBox.Ok)
                return False

            if os.path.isfile(configuration.configpath) == False:
                if QtGui.QMessageBox.warning(self, 'Project Config file not found!', 'The selected project does not ' +\
                                            'contain a config file. Would you like to create one now?\nYou cannot proceed'
                                            'without a config file.',
                                          QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
                    return False
        # create dirs if new project
        if checkPaths == False:
            os.mkdir(self.projDfsDir)
            os.mkdir(self.projPath + '/images')
            os.mkdir(self.projPath + '/curves')

        configuration.projPath = self.projPath

        self.setWindowTitle('Mesmerize - ' + self.projName)

    def createNewDf(self):
        # Create empty DataFrame
        self.configwin.tabs.widget(0).ui.btnSave.clicked.disconnect(self.createNewDf)

        include = configuration.cfg.options('INCLUDE')
        exclude = configuration.cfg.options('EXCLUDE')

        cols = include + exclude

        self.projDf = packager.empty_df(cols)
        assert isinstance(self.projDf, pd.DataFrame)
        self.projDf.to_pickle(self.projRootDfPath, protocol=4)

        # Start the Project Browser loaded with the dataframe columns in the listwidget
        self.initProjBrowser()


    def openConfigWindow(self):
        self.configwin = ConfigWindow.Window()
        self.configwin.tabs.widget(0).ui.btnSave.clicked.connect(self.update_all_from_config)
        self.configwin.resize(593, 617)
        self.configwin.show()

    def update_all_from_config(self):
        # To update the project configuration when the user changes the configuration in the middle of a project.
        self.configwin.tabs.widget(0).ui.btnSave.clicked.disconnect(self.update_all_from_config)

        if self.projDf is not None and self.projDf.empty:
            self.projDf = packager.empty_df(configuration.cfg.options('INCLUDE') + configuration.cfg.options('EXCLUDE'))

        if self.viewer is not None:
            self.viewer.update_from_config()

        if self.projBrowserWin is not None:

            for col in configuration.cfg.options('ROI_DEFS'):
                if col not in self.projDf.columns:
                    self.projDf[col] = 'untagged'

            for col in configuration.cfg.options('STIM_DEFS'):
                if col not in self.projDf.columns:
                    self.projDf[col] = [['untagged']] * len(self.projDf)

            copyfile(self.projRootDfPath, self.projRootDfPath + '_BACKUP' + str(time.time()))
            self.projDf.to_pickle(self.projRootDfPath, protocol=4)
            self.projBrowserWin.close()
            self.projBrowserWin = None
            self.initProjBrowser()
        # QtGui.QMessageBox.information(self, 'Config saved, restart.', 'You must restart Mesmerize and re-open your '
        #                                     'project for changes to take effect.')


    def openProjFileDialog(self):
        # File dialog to open an existing project
        self.checkProjOpen()
        self.projPath = QtGui.QFileDialog.getExistingDirectory(self, 'Select Project Folder')

        if self.projPath == '':
            return

        if self.setupProjPaths(checkPaths=True) is not False:
            self.openProj()
        
    def openProj(self):
        self.projDf = pd.read_pickle(self.projRootDfPath)
        assert isinstance(self.projDf, pd.DataFrame)
        configuration.openConfig()
        self.configwin = ConfigWindow
        self.projName = self.projPath.split('/')[-1][:-4]
        # Start the Project Browser loaded with the dataframe columns in the listwidget
        self.initProjBrowser()
        
    def initProjBrowser(self):

        self.projBrowserWin = ProjBrowser.Window(self.projDf)

        self.setCentralWidget(self.projBrowserWin)

        if self.viewer is None:
            self.initViewer()
        #self.projBrowser.ui.openViewerBtn.clicked.connect(self.viewerWindow.show())
        self.viewer.projPath = self.projPath

    def initViewer(self):
        # Interpret image data as row-major instead of col-major
        pyqtgraphCore.setConfigOptions(imageAxisOrder='row-major')
    
        ## Create window with ImageView widget
        self.viewerWindow = QtGui.QMainWindow()
        self.viewerWindow.resize(1458,931)
        self.viewer = pyqtgraphCore.ImageView()
        self.viewerWindow.setCentralWidget(self.viewer)
#        self.projBrowser.ui.openViewerBtn.clicked.connect(self.showViewer)
        self.viewerWindow.setWindowTitle('Mesmerize - Viewer')
        
        ## Set a custom color map
        colors = [
            (0, 0, 0),
            (45, 5, 61),
            (84, 42, 55),
            (150, 87, 60),
            (208, 171, 141),
            (255, 255, 255)
        ]
        cmap = pyqtgraphCore.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
        self.viewer.setColorMap(cmap)
        
        self.viewer.ui.btnAddToBatch.clicked.connect(self.viewerAddToBatch)
        self.viewer.ui.btnOpenBatch.clicked.connect(self.viewerOpenBatch)
        self.viewerWindow.show()

        self.viewer.ui.btnAddCurrEnvToProj.clicked.connect(self.addWorkEnvToProj)

        viewMenu = self.menubar.addMenu('&View')
        showViewer = viewMenu.addAction('Show Viewer')
        showViewer.triggered.connect(self.viewerWindow.show)

    def isProjLoaded(self):
        if self.projName is None:
            answer = QtGui.QMessageBox.question(self.viewer, 'Message', 
                'You don''t have any project open! Would you like to start a new project (Yes) or Open a project?',
                QtGui.QMessageBox.Yes, QtGui.QMessageBox.Open)
            if answer == QtGui.QMessageBox.Yes:
                self.newProjFileDialog()
            elif answer == QtGui.QMessageBox.Open:
                self.openProjFileDialog()
                
            return False
        
        else:
            return True
    
    def viewerAddToBatch(self):
        if self.isProjLoaded():
            self.viewer.addToBatch()
    
    def viewerOpenBatch(self):
        if self.isProjLoaded():
            self.viewer.openBatch()
    
    def addWorkEnvToProj(self):
        if self.isProjLoaded():
            if self.viewer.setSampleID() is False:
                return
            if any(self.projDf['SampleID'].str.match(self.viewer.workEnv.imgdata.SampleID)):
                QtGui.QMessageBox.warning(self, 'Sample ID already exists!', 'The following SampleID already exists'+\
                          ' in your DataFrame. Use a unique Sample ID for each sample.\n' +\
                          self.viewer.workEnv.imgdata.SampleID, QtGui.QMessageBox.Ok)
                return
            for ID in range(0, len(self.viewer.workEnv.ROIList)):
                self.viewer.updatePlot(ID, force=True)
            r, d = self.viewer.workEnv.to_pandas(self.projPath)
            if r is False:
                return
            copyfile(self.projRootDfPath, self.projRootDfPath + '_BACKUP' + str(time.time()))
            self.projDf = self.projDf.append(pd.DataFrame(d), ignore_index=True)
            self.projDf.to_pickle(self.projRootDfPath, protocol=4)
            self.projBrowserWin.tabs.widget(0).df = self.projDf
            self.projBrowserWin.tabs.widget(0).updateDf()

            
            
if __name__ == '__main__':
    app = QtGui.QApplication([])
    gui = MainWindow()
    gui.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()