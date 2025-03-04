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
        self.context_menu = QMenu(self)
        

        #self.mainwidget.path_export.setText(pathDir)
        self.mainwidget.add_button.clicked.connect(self.add_object)
        self.mainwidget.remove_button.clicked.connect(self.remove_object)
        self.mainwidget.export_button.clicked.connect(self.export_selected_objects)
        # Connect the tableWidget selection signal to sync function
        self.mainwidget.export_tableWidget.itemSelectionChanged.connect(self.sync_selection_with_maya)
        self.mainwidget.export_all_checkBox.stateChanged.connect(self.export_all_checkbox_changed)
        self.mainwidget.import_pushButton.clicked.connect(self.import_usd_to_own_stage)
        self.mainwidget.browse_pushButton.clicked.connect(self.open_selcect_folder)
        self.mainwidget.browseX_pushButton.clicked.connect(self.open_folder)
        self.mainwidget.export_tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mainwidget.export_tableWidget.customContextMenuRequested.connect(self.show_table_context_menu)

        clear_item = self.context_menu.addAction("Clear")
        clear_item.triggered.connect(self.clear_all_objects)

    def add_object(self):  # <<user select obj and click add to show in table widget
        selcect_object = cmds.ls(sl=True)
        
        # First, build a list of existing objects in the tableWidget
        existing_objects = []
        for row in range(self.mainwidget.export_tableWidget.rowCount()):
            item = self.mainwidget.export_tableWidget.item(row, 1)
            if item:
                existing_objects.append(item.text())
        
        # Add only objects that don't already exist in the table
        for obj in selcect_object:
            if obj not in existing_objects:
                row_position = self.mainwidget.export_tableWidget.rowCount()
                self.mainwidget.export_tableWidget.insertRow(row_position)
                self.mainwidget.export_tableWidget.setItem(
                    row_position, 1, QTableWidgetItem(obj))
    
    def sync_selection_with_maya(self):
        """
        Synchronizes the selection between tableWidget and Maya's outliner.
        When an item is selected in the tableWidget, it also selects that object in Maya.
        """
        # Get selected items from the tableWidget
        selected_rows = set(index.row() for index in self.mainwidget.export_tableWidget.selectedIndexes())
        
        if selected_rows:
            # Create a list to store the object names to be selected in Maya
            objects_to_select = []
            
            # Get object names from the selected rows in the tableWidget
            for row in selected_rows:
                item = self.mainwidget.export_tableWidget.item(row, 1)
                if item and item.text():
                    object_name = item.text()
                    # Check if the object exists in the Maya scene
                    if cmds.objExists(object_name):
                        objects_to_select.append(object_name)
            
            # Clear current selection in Maya
            cmds.select(clear=True)
            
            # Select objects in Maya if any valid objects found
            if objects_to_select:
                cmds.select(objects_to_select, add=True)

    def export_all_checkbox_changed(self):
        """
        When the export_all_checkBox is checked, select all objects in the Maya scene.
        When unchecked, clear the selection in Maya.
        """
        # Check if the checkbox is checked
        if self.mainwidget.export_all_checkBox.isChecked():
            # Get all objects in the scene (excluding default Maya objects)
            all_objects = cmds.ls(dag=True, long=True)
            
            # Filter out default cameras and other Maya default objects
            # This is a basic filter - you might need to adjust based on your needs
            filtered_objects = [obj for obj in all_objects if not obj.startswith('|camera') 
                                and not obj.startswith('|light') 
                                and not 'initialShadingGroup' in obj 
                                and not 'defaultLightSet' in obj
                                and not 'defaultObjectSet' in obj]
            
            # Select all filtered objects
            if filtered_objects:
                cmds.select(filtered_objects, replace=True)
        else:
            # If checkbox is unchecked, clear selection
            cmds.select(clear=True)

    def show_table_context_menu(self, position):
        # Show the context menu only for the tableWidget
        global_pos = self.mainwidget.export_tableWidget.mapToGlobal(position)
        self.context_menu.exec_(global_pos)

    def clear_all_objects(self):
        # Clear all rows from the table widget
        self.mainwidget.export_tableWidget.setRowCount(0)

    def remove_object(self):
        if self.mainwidget.export_tableWidget.selectionModel().hasSelection():
            select_rows = set(index.row() for index in self.mainwidget.export_tableWidget.selectedIndexes())
            if select_rows:
                # Remove selected rows
                for row in sorted(select_rows, reverse=True):
                    self.mainwidget.export_tableWidget.removeRow(row)
            else:
                # If selection exists but no specific rows selected, it means "select all" was used
                self.mainwidget.export_tableWidget.setRowCount(0)

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

    def export_selected_objects(self):
        """
        Exports objects from the export_tableWidget as USD files using the path from path_export.
        Tries multiple methods to export USD files depending on Maya version.
        """
        # Check if the USD plugin is loaded, if not, try to load it
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
            try:
                cmds.loadPlugin("mayaUsdPlugin")
                print("Maya USD Plugin loaded successfully")
            except Exception as e:
                cmds.warning(f"Failed to load Maya USD Plugin: {str(e)}")
                # Try the Autodesk USD plugin as an alternative
                try:
                    cmds.loadPlugin("pxrUsd")
                    print("Pixar USD Plugin loaded successfully")
                except Exception as e:
                    cmds.warning(f"Failed to load Pixar USD Plugin: {str(e)}")
                    try:
                        cmds.loadPlugin("bifrostGraph")
                        print("Bifrost plugin loaded successfully (may contain USD export)")
                    except:
                        cmds.warning("Unable to load any USD-compatible plugins. Please install one first.")
                        return False
        
        # Check if there are any items in the tableWidget
        if self.mainwidget.export_tableWidget.rowCount() == 0:
            cmds.warning("No objects in the export list. Please add objects first.")
            return False
        
        # Get export path from the path_export field
        export_path = self.mainwidget.path_export.text()
        
        if not export_path:
            cmds.warning("Export path is empty. Please specify a valid export path.")
            return False
        
        # Ensure the path has a USD extension
        if not export_path.lower().endswith(('.usd', '.usda', '.usdc')):
            export_path += '.usd'
            
        export_dir = os.path.dirname(export_path)
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except Exception as e:
                cmds.warning(f"Failed to create directory: {str(e)}")
                return False
        
        # Get all objects from the tableWidget
        objects_to_export = []
        for row in range(self.mainwidget.export_tableWidget.rowCount()):
            item = self.mainwidget.export_tableWidget.item(row, 1)
            if item and item.text():
                objects_to_export.append(item.text())
        
        if not objects_to_export:
            cmds.warning("No valid objects in the export list.")
            return False
        
        # Select all objects to export
        cmds.select(objects_to_export)
        
        # Try multiple methods to export USD files
        success = False
        
        try:
            # Method 1: Direct usdExport command (Maya 2020+)
            if hasattr(cmds, 'usdExport'):
                print("Using cmds.usdExport method")
                cmds.usdExport(
                    file=export_path,
                    selection=True,
                    defaultMeshScheme='catmullClark',
                    exportColorSets=True,
                    exportUVs=True,
                    exportVisibility=True,
                    exportDisplayColor=True,
                    mergeTransformAndShape=True
                )
                success = True
            # Method 2: Using file export with USD type (Maya 2019+)
            elif "USD Export" in cmds.pluginInfo(query=True, listPlugins=True):
                print("Using file export with USD type")
                cmds.file(
                    export_path,
                    force=True,
                    options="",
                    type="USD Export",
                    exportSelected=True
                )
                success = True
            # Method 3: Using mayaUSDExport mel command
            else:
                import maya.mel as mel
                try:
                    print("Attempting to use MEL mayaUSDExport command")
                    mel_cmd = f'mayaUSDExport -mergeTransformAndShape -file "{export_path}" -selection'
                    mel.eval(mel_cmd)
                    success = True
                except Exception as mel_error:
                    print(f"MEL export error: {mel_error}")
                    # Try other methods before giving up
                    try:
                        print("Attempting to use USD Export Plugin directly")
                        cmds.file(
                            export_path,
                            force=True,
                            options="",
                            type="pxrUsdExport",
                            exportSelected=True
                        )
                        success = True
                    except Exception as pxr_error:
                        print(f"pxrUsdExport error: {pxr_error}")
                        # One last attempt with a different command name
                        try:
                            cmds.USDExport(
                                file=export_path,
                                selection=True
                            )
                            success = True
                        except Exception as final_error:
                            print(f"Final USD export attempt error: {final_error}")
                            cmds.warning("All USD export methods failed.")
                            return False
        except Exception as e:
            cmds.warning(f"Error during export: {str(e)}")
            return False
        
        if success:
            cmds.confirmDialog(
                title="Export Successful", 
                message=f"USD file exported successfully to:\n{export_path}",
                button=["OK"]
            )
            return True
        else:
            cmds.warning("Failed to export USD file. No compatible USD export method found.")
            return False
    
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

    '''def add_payload(self, prim: Usd.Prim, payload_asset_path: str, payload_target_path: Sdf.Path) -> None:
        payloads: Usd.Payloads = prim.GetPayloads()
        payloads.AddPayload(
            assetPath=payload_asset_path,
            # OPTIONAL: Payload a specific target prim. Otherwise, uses the payloadd layer's defaultPrim.
            primPath=payload_target_path
            )'''

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
