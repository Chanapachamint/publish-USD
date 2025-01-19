import sys
import os
import json
import mayaUsd
import logging
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from pxr import Usd, UsdGeom, Sdf

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


pathDir = os.path.dirname(sys.modules[__name__].__file__)
fileUi = '%s/uiwidget.ui' % pathDir
config_file_path = '%s/ui_config.json' % pathDir
output_path = 'D:/Work_Year4/THESIS/example_scenes'

def load_configjson():
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    root_path = config['root_path']

    return root_path

#def maya_plugin():
#    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
#        cmds.loadPlugin("mayaUsdPlugin")


class MainWidget(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)

        self.mainwidget = setup_ui_maya(fileUi, self)
        self.setCentralWidget(self.mainwidget)
        self.root_path = load_configjson()
        self.setWindowTitle('Export /Import USD')
        self.resize(450,500)
        self.current_stage = None
        self.current_layer = None

        #self.mainwidget.path_export.setText(pathDir)
        self.mainwidget.add_button.clicked.connect(self.add_object)
        self.mainwidget.remove_button.clicked.connect(self.remove_object)
        self.mainwidget.export_button.clicked.connect(self.export_selected_usd)
        self.mainwidget.set_xform_checkBox.stateChanged.connect(self.set_xform)
        self.mainwidget.import_pushButton.clicked.connect(self.createStageWithNewLayer)
        self.mainwidget.browse_pushButton.clicked.connect(self.open_selcect_folder)
        self.mainwidget.browseX_pushButton.clicked.connect(self.open_folder)

    def add_object(self): #<<user select obj and click add to show in table widget
       selcect_object = cmds.ls( sl=True )
       for obj in selcect_object:
        row_position = self.mainwidget.export_tableWidget.rowCount()
        self.mainwidget.export_tableWidget.insertRow(row_position)
        self.mainwidget.export_tableWidget.setItem(row_position, 1, QTableWidgetItem(obj))
    
    def remove_object(self):
        select_rows = set(index.row() for index in self.mainwidget.export_tableWidget.selectedIndexes())
        for row in sorted(select_rows):
            self.mainwidget.export_tableWidget.removeRow(row)
    
    def output_text(self, source_row):
        column_position = self.mainwidget.export_tableWidget.columnCount()
        self.mainwidget.export_tableWidget.insertRow(column_position)
        for col in range(self.mainwidget.export_tableWidget.columnCount()):
            source_item = self.mainwidget.export_tableWidget.item(source_row, col)
        if source_item:
            source_text = source_item.text()
            self.mainwidget.export_tableWidget.setItem(column_position, col, QTableWidgetItem(source_text))
    
    def set_xform(self): #<< ต้องปรับแก้จุดหมุน
        if self.mainwidget.set_xform_checkBox.isChecked():
            obj_selcect = cmds.ls(selection=True)
        #is_checked = self.mainwidget.set_xform_checkBox.isChecked()
        #print("Check:", is_checked)
            for obj in obj_selcect:
                cmds.xform(obj, ws=True, t=(0, 0, 0))

    '''def compute_bbox(prim: Usd.Prim) -> Gf.Range3d:
        imageable = UsdGeom.Imageable(prim)
        time = Usd.TimeCode.Default() # The time at which we compute the bounding box
        bound = imageable.ComputeWorldBound(time, UsdGeom.Tokens.default_)
        bound_range = bound.ComputeAlignedBox()
        return bound_range

    def add_payload(prim: Usd.Prim, payload_asset_path: str, payload_target_path: Sdf.Path) -> None:
        payloads: Usd.Payloads = prim.GetPayloads()
        payloads.AddPayload(
            assetPath=payload_asset_path,
            primPath=payload_target_path # OPTIONAL: Payload a specific target prim. Otherwise, uses the payloadd layer's defaultPrim.
        )

    def geom_stage(fileName, root_asset, render_value, proxy_value):

        stripExtension = os.path.splitext(fileName)[0]
        geom_name = stripExtension + '_geo'

        # Export the geo file
        cmds.file(geom_name, options=";exportDisplayColor=1;exportColorSets=0;mergeTransformAndShape=1;exportComponentTags=0;defaultUSDFormat=usdc;jobContext=[Arnold];materialsScopeName=mtl", 
                typ="USD Export", pr=True, ch=True, chn=True, exportSelected=True, f=True)
        
        # Replace xforms with scopes for purpose groups
        stage = Usd.Stage.Open(geom_name + '.usd')
        prim_geo = stage.GetPrimAtPath(root_asset + "/geo")
        prim_geo.SetTypeName("Scope")
        
        # Extents Hint BBox (not working with unloaded payloads currently in Maya)
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])    
        root_geom_model_API = UsdGeom.ModelAPI.Apply(prim_geo)
        extentsHint = root_geom_model_API.ComputeExtentsHint(bbox_cache)
        root_geom_model_API.SetExtentsHint(extentsHint)
        
        prim_render = stage.GetPrimAtPath(root_asset + "/geo/" + render_value)
        prim_render.SetTypeName("Scope")
        prim_proxy = stage.GetPrimAtPath(root_asset + "/geo/" + proxy_value)
        prim_proxy.SetTypeName("Scope")

        stage.Save()'''

    def export_selected_usd(self, output_path):
        obj_selcect = cmds.ls(selection=True)
        cmds.loadPlugin('mayaUsdPlugin', quiet=True)
        obj_selcect_export = []
        
        for obj in obj_selcect:
            if cmds.nodeType(obj) == "transform":
                all_children = cmds.listRelatives(obj, allDescendents=True)
                all_children = cmds.listRelatives(obj, allDescendents=True, type="mesh") or []
                obj_selcect_export.extend(all_children)

        cmds.select(obj_selcect_export, replace=True)
        cmds.mayaUSDExport(selection=True, file=output_path)
        #add_payload()

    def add_payload(self, prim: Usd.Prim, payload_asset_path: str, payload_target_path: Sdf.Path) -> None:
        payloads: Usd.Payloads = prim.GetPayloads()
        payloads.AddPayload(
            assetPath=payload_asset_path,
            primPath=payload_target_path # OPTIONAL: Payload a specific target prim. Otherwise, uses the payloadd layer's defaultPrim.
        )

    def create_new_usd_stage(self):
        cmds.mayaUSDImport(file = 'D:/Work_Year4/THESIS/Maya/living_room_assets/scenes/USD/dice.usd') 
        #stage =  Usd.Stage.CreateNew(path_scene_usd)
        #stage1 = cmds.mayaUsdCreateStageWithNewLayer()
        #xformPrim = UsdGeom.Xform.Define(stage, '/hello')
        #stage.GetRootLayer().Save()

        stage = cmds.mayaUsdCreateStageWithNewLayer('')
        xform_path = "/World/MyXform"
        xform = UsdGeom.Xform.Define(stage, xform_path)
        return xform
    
    def createStageWithNewLayer(self):
        # Simply create a proxy shape. Since it does not have a USD file associated
        # (in the .filePath attribute), the proxy shape base will create an empty
        # stage in memory. This will create the session and root layer as well.

        if hasattr(mayaUsd, 'ufe') and hasattr(mayaUsd.ufe, 'createStageWithNewLayer'):
            # Empty parent means parent to Maya world node.
            #shapeNode = mayaUsd.ufe.createStageWithNewLayer('')
            shapeNode = cmds.mayaUsdCreateStageWithNewLayer('')
            cmds.mayaUSDImport(file = 'D:/Work_Year4/THESIS/False.usd') 

            #cmds.select(shapeNode, replace=True)
            return shapeNode
        else:
            shapeNode = cmds.createNode('mayaUsdProxyShape', skipSelect=True, name='stageShape1')
            cmds.connectAttr('time1.outTime', shapeNode+'.time')
            cmds.select(shapeNode, replace=True)
            fullPath = cmds.ls(shapeNode, long=True)
            return fullPath[0]
        
    print('create_stage')

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
            QWidget.QMessageBox.warning(self, "Error", "Invalid folder path selected!")
            return

        # Find all .usd files in the folder
        usd_files = [f for f in os.listdir(folder_path) if f.endswith(".usd")]

        # Populate the ListWidget
        if usd_files:
            self.mainwidget.import_listWidget.addItems(usd_files)
        else:
            QWidget.QMessageBox.information(self, "No Files Found", "No .usd files found in the selected folder.")

    #def import_usd(self):

    #def create_xform(self):

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
