# -*- coding: utf-8 -*-
"""
/***************************************************************************
 weboptim
                                 A QGIS plugin
 Plugin that generates web optimized images
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-08-25
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Blackshark.ai
        email                : sridene@blackshark.ai
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import subprocess
from typing import Set
from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QThread,pyqtSignal,QObject, pyqtSlot
from PyQt5.QtGui import QIcon
from qgis.core import QgsProject,QgsTask
from PyQt5.QtWidgets import QApplication,QDialog,QMainWindow, QAction,QFileDialog,QLineEdit,QProgressBar,QMessageBox

from datetime import datetime
from datetime import timezone
from time import gmtime, strftime
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .weboptim_dialog import weboptimDialog
from .weboptim_dialog_base import Ui_weboptimDialogBase
import os.path
import time
import glob
from glob import glob
#from gdal import RegenerateOverviews
from osgeo import gdal
from functools import partial
import pytz
from pathlib import Path        
                  
class weboptim:

    """QGIS Plugin Implementation."""

    def __init__(self,iface,parent=None):
        #super(weboptim,self).__init__(parent)
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'weboptim_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        #self.setFixedSize(640, 480)
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WebOptimzedTIF')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        #self.show()


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('weboptim', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        self.dlg=weboptimDialog()
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/weboptim/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Web Optimized Images'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&WebOptimzedTIF'),
                action)
            self.iface.removeToolBarIcon(action)
    

    def run(self):
        #self.dlg.setWindowIcon(QIcon('C:\Users\sridene\Desktop\blackshark_logo.png'))

        """Run method that performs all the real work"""
        self.dlg.show()
        self.dlg.toolButton_2.clicked.connect(self.select_folder)
        self.dlg.toolButton.clicked.connect(self.select_folder_VRT)

        self.worker=WorkerThread()
        # Create QLineEdit instance and assign string
         #self.myLine = self.dlg.lineEdit()
        self.dire=self.dlg.lineEdit.text()
        self.vrt_input_name=self.dlg.lineEdit_3.text()
        self.dlg.textBrowser.append("Instructions:"+"\n"+"1. Choose the images directory")
        self.dlg.textBrowser.append("2. Set a directory and a name for the Virtual Dataset file"+"\n")
        
        self.worker.processStart.connect(self.statusText_processing_start)
        self.worker.progressReportStart.connect(self.statusText_updaterStart)
        self.worker.progressReportEnd.connect(self.statusText_updaterEnd)
        self.worker.progressVRT.connect(self.statusText_updaterVRT)
        self.worker.progressReportOVR.connect(self.statusText_updaterOVR)
        self.worker.progress_percent.connect(self.updateProgressBar)
        #self.wait_for_input1.emit(self.dire)
        #self.wait_for_input2.emit(self.vrt_input_name)
        self.dlg.pushButton.clicked.connect(self.evt_btnstart_clicked)
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started   
        # show the dialog
        self.worker.finished.connect(self.evt_worker_finished)
        # Run the dialog event loop
    def statusText_processing_start(self,text):
        self.dlg.textBrowser.append(text)
    def statusText_updaterStart(self,text):
        self.dlg.textBrowser.append(text)
    def statusText_updaterEnd(self,text):
        self.dlg.textBrowser.append(text)
    def statusText_updaterVRT(self,text):
        self.dlg.textBrowser.append(text)
    def statusText_updaterOVR(self,text):
        self.dlg.textBrowser.append(text)
    def updateProgressBar(self,val):
        self.dlg.progressBar.setValue(val)
    def evt_worker_finished(self):
        msg=QMessageBox()
        msg.setText("Process is completed!")
        msg.setWindowTitle("Message Box")
        msg.exec_()  
    def select_folder(self):
        foldername= QFileDialog.getExistingDirectory(self.dlg, "Select Folder")
        self.dlg.lineEdit.setText(foldername)
    
    def select_folder_VRT(self):
        filename= QFileDialog.getSaveFileName(self.dlg, 'Save File')
        #filename.setNameFilters(["*.vrt"])
        #filename.selectNameFilter("VRT Files (*.vrt)")
        self.dlg.lineEdit_3.setText(filename[0])
    
    #Connect the thread
    def evt_btnstart_clicked(self):
        self.worker.start()
        self.worker.line_thread=self.dlg.lineEdit.text()
        self.worker.line_thread2=self.dlg.lineEdit_3.text()
       
        #self.worker.started.connect(WorkerThread.run)
        
        #self.worker.finished.connect(self.evt_worker_finished)
        
class WorkerThread(QThread):
#We have to pass an information with this signal
#Create a signal in the thread in order to be picked up in the main application by a slot
    processStart=pyqtSignal(str)
    progressReportStart = pyqtSignal(str)
    progressReportEnd = pyqtSignal(str)
    progressVRT=pyqtSignal(str)
    progressReportOVR=pyqtSignal(str)
    progress_percent=pyqtSignal(int)
    finished = pyqtSignal()
    def __init__(self,parent=None):
        super(WorkerThread,self).__init__(parent)
        
        #QThread.__init__(parent=parent)
        #self.isRunning=True
        
    def run(self):
        #self.thread_started=weboptim(self.iface)
        #self.thread_started.start()
        dire=self.line_thread
        #dire=r'D:\blackshark'
        vrt_input_name=self.line_thread2
        #vrt_input_name="txt"
        self.processStart.emit("Start processing...")
        in_imgpath=os.path.join(dire, "*.TIF")
        compress_directory = os.path.join(dire, r'WebOptimized')
        if not os.path.exists(compress_directory):
            os.makedirs(compress_directory)
       
        self.count=len([f for f in os.listdir(dire) if f.endswith('.tif')])
        
        self.counter=0
        for filename in glob(in_imgpath):
            self.counter+=1
            
            QApplication.processEvents()
            time.sleep(3)
            path, base_filename = os.path.split(filename)
            #self.dlg.textBrowser.append(datetime.now(pytz.timezone('Europe/Berlin')).strftime("%H:%M:%S: %d-%m-%Y")+"Start compressing for: "+base_filename+"\n")
            self.progressReportStart.emit(datetime.now(pytz.timezone('Europe/Berlin')).strftime("%H:%M:%S %d-%m-%Y : ")+"Start compressing for: "+base_filename+"\n")
            time.sleep(3)
            compr = os.path.join(compress_directory, "WebOptimized_"+base_filename)
            #Compress Images
            translate_option1=gdal.TranslateOptions(gdal.ParseCommandLine("-of GTiff -co BIGTIFF=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 -co NUM_THREADS=ALL_CPUS -a_nodata 0 -b 1 -b 2 -b 3 -colorinterp red,green,blue")) 
            gdal.Translate(compr, filename, options=translate_option1)
            time.sleep(3)
            self.progressReportEnd.emit(datetime.now(pytz.timezone('Europe/Berlin')).strftime("%H:%M:%S %d-%m-%Y : ")+"Finish compressing for: "+base_filename+"\n")
            time.sleep(3)
            #Builds Overview Images
            Image = gdal.Open(compr,1)
            
            gdal.SetConfigOption("COMPRESS_OVERVIEW", "DEFLATE")
            Image.BuildOverviews("AVERAGE", [2,4,8,16,32,64])
            Image=None
            path2, base_filename2 = os.path.split(compr)
            self.progressReportOVR.emit(datetime.now(pytz.timezone('Europe/Berlin')).strftime("%H:%M:%S %d-%m-%Y : ")+"Internal overview created for: "+base_filename2+"\n")
            time.sleep(3)
            self.percent=int((self.counter/int(self.count))*100)
            self.progress_percent.emit(self.percent)
            
        #Create VRT File
        vrt_name=os.path.join(vrt_input_name +".vrt")  
        time.sleep(3) 
        vrt_dir=os.path.join(compress_directory,"*.tif")
        gdal.BuildVRT(vrt_name, glob(vrt_dir))
        time.sleep(3)
        self.progressVRT.emit(datetime.now(pytz.timezone('Europe/Berlin')).strftime("%H:%M:%S %d-%m-%Y : ")+'VRT file: "'+vrt_name+' created.')
        self.finished.emit()
