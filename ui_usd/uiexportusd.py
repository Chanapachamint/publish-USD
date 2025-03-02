import sys
import os
import json
import mayaUsd.ufe
import mayaUsd.lib
import mayaUsd_createStageWithNewLayer
import ufe
import math
import logging
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from pxr import Usd, UsdGeom, Gf, Sdf
from util_usd import ufeUtils

try:
    from PySide6.QtCore import *
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtUiTools import QUiLoader
    from shiboken6 import wrapInstance
except Exception:
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtUiTools import QUiLoader
    from shiboken2 import wrapInstance


usdSeparator = '/'

pathDir = os.path.dirname(sys.modules[__name__].__file__)
fileUi = '%s/uiwidget.ui' % pathDir
config_file_path = '%s/ui_config.json' % pathDir
output_path = 'D:/Work_Year4/THESIS/example_scenes'


def load_configjson():
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    root_path = config['root_path']

    return root_path

# def maya_plugin():
#    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
#        cmds.loadPlugin("mayaUsdPlugin")


class MainWidget(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)

        self.mainwidget = setup_ui_maya(fileUi, self)
        self.setCentralWidget(self.mainwidget)
        self.root_path = load_configjson()
        self.setWindowTitle('Export /Import USD')
        self.resize(450, 500)
        self.current_stage = None
        self.current_layer = None

        #self.mainwidget.path_export.setText(pathDir)
        self.mainwidget.add_button.clicked.connect(self.add_object)
        self.mainwidget.remove_button.clicked.connect(self.remove_object)
        self.mainwidget.export_button.clicked.connect(self.export_selected_usd)
        #self.mainwidget.set_xform_checkBox.stateChanged.connect(self.set_xform)
        self.mainwidget.import_pushButton.clicked.connect(self.import_usd_to_own_stage)
        self.mainwidget.browse_pushButton.clicked.connect(self.open_selcect_folder)
        self.mainwidget.browseX_pushButton.clicked.connect(self.open_folder)

    def add_object(self):  # <<user select obj and click add to show in table widget
        selcect_object = cmds.ls(sl=True)
        for obj in selcect_object:
            row_position = self.mainwidget.export_tableWidget.rowCount()
            self.mainwidget.export_tableWidget.insertRow(row_position)
            self.mainwidget.export_tableWidget.setItem(
                row_position, 1, QTableWidgetItem(obj))

    def remove_object(self):
        select_rows = set(index.row() for index in self.mainwidget.export_tableWidget.selectedIndexes())
        for row in sorted(select_rows):
            self.mainwidget.export_tableWidget.removeRow(row)

    def output_text(self, source_row):
        column_position = self.mainwidget.export_tableWidget.columnCount()
        self.mainwidget.export_tableWidget.insertRow(column_position)
        for col in range(self.mainwidget.export_tableWidget.columnCount()):
            source_item = self.mainwidget.export_tableWidget.item(
                source_row, col)
        if source_item:
            source_text = source_item.text()
            self.mainwidget.export_tableWidget.setItem(
                column_position, col, QTableWidgetItem(source_text))

    #def set_xform(self):  # << ต้องปรับแก้จุดหมุน
    #    if self.mainwidget.set_xform_checkBox.isChecked():
    #        obj_selcect = cmds.ls(selection=True)
        # is_checked = self.mainwidget.set_xform_checkBox.isChecked()
        # print("Check:", is_checked)
    #        for obj in obj_selcect:
    #            cmds.xform(obj, ws=True, t=(0, 0, 0)) 

    def export_selected_usd(self):
        stage = Usd.Stage.CreateNew('D:/Work_Year4/THESIS/02.usd')
        xformPrim = UsdGeom.Xform.Define(stage, '/hello')
        spherePrim = UsdGeom.Sphere.Define(stage, '/hello/world')
        stage.GetRootLayer().Save()

        print(stage)
        return xformPrim, spherePrim

        '''obj_selcect = cmds.ls(selection=True)
        cmds.loadPlugin('mayaUsdPlugin', quiet=True)
        obj_selcect_export = []
        
        for obj in obj_selcect:
            if cmds.nodeType(obj) == "transform":
                all_children = cmds.listRelatives(obj, allDescendents=True)
                all_children = cmds.listRelatives(obj, allDescendents=True, type="mesh") or []
                obj_selcect_export.extend(all_children)

        cmds.select(obj_selcect_export, replace=True)
        cmds.mayaUSDExport(selection=True, file=output_path)
        #add_payload()'''

    def add_payload(self, prim: Usd.Prim, payload_asset_path: str, payload_target_path: Sdf.Path) -> None:
        payloads: Usd.Payloads = prim.GetPayloads()
        payloads.AddPayload(
            assetPath=payload_asset_path,
            # OPTIONAL: Payload a specific target prim. Otherwise, uses the payloadd layer's defaultPrim.
            primPath=payload_target_path
            )

    def create_new_usd_stage(self):
        # cmds.mayaUSDImport(file = 'D:/Work_Year4/THESIS/Maya/living_room_assets/scenes/USD/dice.usd')
        # stage =  Usd.Stage.CreateNew()
        # stage1 = cmds.mayaUsdCreateStageWithNewLayer()
        # xformPrim = UsdGeom.Xform.Define(stage, '/hello')
        # stage.GetRootLayer().Save()

        stage = cmds.mayaUsdCreateStageWithNewLayer('')
        xform_path = "/World/MyXform"
        xform = UsdGeom.Xform.Define(stage, xform_path)
        return xform

    def open_selcect_folder(self):
        folder_path = QFileDialog.getExistingDirectory()

        if folder_path:
            self.mainwidget.path_import.setText(folder_path)
            self.show_usd_file()

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory()
        self.mainwidget.path_export.setText(folder_path)

    def show_usd_file(self):
        self.mainwidget.import_listWidget.clear()

        folder_path = self.mainwidget.path_import.text()

        if not folder_path or not os.path.exists(folder_path):
            QWidget.QMessageBox.warning(
                self, "Error", "Invalid folder path selected!")
            return

        # Find all .usd files in the folder
        usd_files = [f for f in os.listdir(folder_path) if f.endswith(".usd")]

        # Populate the ListWidget
        if usd_files:
            self.mainwidget.import_listWidget.addItems(usd_files)
            return

    def onItemSelected(self):
        '''Handles user selecting a USD file and importing it into the stage.'''
        folder_path = self.mainwidget.path_import.text()
        usd_file_name = self.mainwidget.import_listWidget.currentItem().text()
        usd_file_path = os.path.normpath(
            os.path.join(folder_path, usd_file_name))

        print(f"Selected USD File: {usd_file_path}")

        if not hasattr(self, "stage"):
            print("No stage found. Creating a new stage...")
            self.createSimpleStage()

        self.importUsdIntoStage(usd_file_path)

    def importUsdIntoStage(self, usd_file_path):
        '''Imports a selected USD file into the existing stage.'''
        if not os.path.exists(usd_file_path):
            print(f"Error: File not found - {usd_file_path}")
            return

        try:
            print(f"Importing USD file into stage: {usd_file_path}")
            cmds.mayaUSDImport(usd_file_path)

        except Exception as e:
            print(f"Error importing USD file: {e}")

    def import_usd_to_own_stage(self):
        """Import a USD file into its own stage in Maya when button is clicked"""
        # Get folder path and file name from UI elements
        folder_path = self.mainwidget.path_import.text()

        # Make sure a file is selected in the list widget
        if not self.mainwidget.import_listWidget.currentItem():
            print("Error: No file selected")
            return

        usd_file_name = self.mainwidget.import_listWidget.currentItem().text()
        usd_file_path = os.path.normpath(
            os.path.join(folder_path, usd_file_name))

        print(f"Selected USD File: {usd_file_path}")

        if not os.path.exists(usd_file_path):
            print(f"Error: File not found - {usd_file_path}")
            return

        print(f"Importing USD file into its own stage: {usd_file_path}")

        try:
            # Create a proxy shape node for the USD stage
            proxy_shape = cmds.createNode('mayaUsdProxyShape')
            transform_node = cmds.listRelatives(proxy_shape, parent=True)[0]

            # Set the file path for the proxy shape to load the USD file
            cmds.setAttr(f"{proxy_shape}.filePath",
                         usd_file_path, type="string")

            # Optional: Give the node a meaningful name based on the file
            file_name = os.path.basename(usd_file_path).split('.')[0]
            cmds.rename(transform_node, f"{file_name}_stage")

            print(f"Created stage with proxy shape: {proxy_shape}")

        except Exception as e:
            print(f"Error creating USD stage: {e}")
            import traceback
            traceback.print_exc()


class MayaUsdLayer(MainWidget):
    hosts = ['maya']
    families = ["mayaUsdLayer"]

    def __init__(self, *args, **kwargs):
        super(MayaUsdLayer, self).__init__(*args, **kwargs)

    def process(self, instance):
        cmds.loadPlugin("mayaUsdPlugin", quiet=True)

        data = instance.data["stageLayerIdentifier"]
        self.log.debug(f"Using proxy layer: {data}")

        proxy, layer_identifier = data.split(">", 1)

        stage = mayaUsd.ufe.getStage('|world' + proxy)
        layers = stage.GetLayerStack(includeSessionLayers=False)
        layer = next(
            layer for layer in layers if layer.identifier == layer_identifier
        )

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{0}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        self.log.debug("Exporting USD layer to: {}".format(file_path))
        layer.Export(file_path, args={
            "format": instance.data.get("defaultUSDFormat", "usdc")
        })

        representation = {
            'name': "usd",
            'ext': "usd",
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data.setdefault("representations", []).append(representation)
        self.log.debug(
            "Extracted instance {} to {}".format(instance.name, file_path)
        )


def setup_ui_maya(design_widget, parent):
    fileUi = QDir(os.path.dirname(design_widget))
    qt_loader = QUiLoader()
    qt_loader.setWorkingDirectory(fileUi)

    f = QFile(design_widget)
    f.open(QFile.ReadOnly)

    widget = qt_loader.load(f, parent)
    f.close()

    return widget


def run():
    global ui
    try:
        ui.close()
    except:
        pass

    ptr = wrapInstance(int(omui.MQtUtil.mainWindow()), QWidget)
    ui = MainWidget(parent=ptr)
    ui.show()


run()
