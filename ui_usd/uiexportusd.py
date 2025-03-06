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
#output_path = 'D:/Work_Year4/THESIS/example_scenes'


def load_configjson():
    with open(config_file_path, 'r') as f:
        config = json.load(f)
    root_path = config['root_path']

    return root_path


class MainWidget(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)

        self.mainwidget = setup_ui_maya(fileUi, self)
        self.setCentralWidget(self.mainwidget)
        self.root_path = load_configjson()
        self.setWindowTitle('Export /Import USD')
        self.resize(450, 500)
        self.context_menu = QMenu(self)
        self.mainwidget.export_tableWidget.setColumnWidth(0, 150)
        self.mainwidget.export_tableWidget.setColumnWidth(1, 100)
        self.mainwidget.export_tableWidget.setColumnWidth(2, 150)


        self.mainwidget.add_button.clicked.connect(self.add_object)
        self.mainwidget.remove_button.clicked.connect(self.remove_object)
        self.mainwidget.export_button.clicked.connect(self.export_selected_to_usd)
        self.mainwidget.export_tableWidget.itemSelectionChanged.connect(self.sync_selection_with_maya)
        self.mainwidget.export_all_checkBox.stateChanged.connect(self.export_all_checkbox_changed)
        self.mainwidget.import_pushButton.clicked.connect(self.import_usd_to_own_stage)
        self.mainwidget.browse_pushButton.clicked.connect(self.open_selcect_folder)
        self.mainwidget.browseX_pushButton.clicked.connect(self.open_folder)
        self.mainwidget.export_tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mainwidget.export_tableWidget.customContextMenuRequested.connect(self.show_table_context_menu)

        clear_item = self.context_menu.addAction("Clear")
        clear_item.triggered.connect(self.clear_all_objects)

    def add_object(self):
        selcect_object = cmds.ls(sl=True)
        existing_objects = []
        for row in range(self.mainwidget.export_tableWidget.rowCount()):
            item = self.mainwidget.export_tableWidget.item(row, 0)
            if item:
                existing_objects.append(item.text())

        # Add only objects that don't already exist in the table
        for obj in selcect_object:
            if obj not in existing_objects:
                row_position = self.mainwidget.export_tableWidget.rowCount()
                self.mainwidget.export_tableWidget.insertRow(row_position)
                self.mainwidget.export_tableWidget.setItem(
                    row_position, 0, QTableWidgetItem(obj))

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
                item = self.mainwidget.export_tableWidget.item(row, 0)
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
        if self.mainwidget.export_all_checkBox.isChecked():
            all_objects = cmds.ls(dag=True, long=True)

            filtered_objects = [obj for obj in all_objects if not obj.startswith('|camera')
                                and not obj.startswith('|light')
                                and not 'initialShadingGroup' in obj
                                and not 'defaultLightSet' in obj
                                and not 'defaultObjectSet' in obj]

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
            select_rows = set(
                index.row() for index in self.mainwidget.export_tableWidget.selectedIndexes())
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

    def export_usd(self,
                   selected_items,  # List of selected items from tableWidget
                   output_path,     # Destination path from path_export
                   export_type='reference',  # Default export strategy
                   up_axis='y',    # Default up axis
                   scale=1.0       # Optional scaling factor
                   ):
        """
        Export USD file from selected items in a table widget

        Args:
            selected_items (list): List of selected items from table widget
                Expected format: [{'path': str, 'name': str, ...}, ...]
            output_path (str): Destination path for USD file
            export_type (str): Export strategy 
                - 'reference': Create references to input files
                - 'payload': Create payloads instead of references
                - 'flatten': Merge all inputs into single file
            up_axis (str): Stage up axis ('y' or 'z')
            scale (float): Optional scaling factor for geometry

        Returns:
            tuple: (bool, str) - Export success status and message
        """
        try:
            # Validate inputs
            if not selected_items:
                return False, "No items selected for export"

            if not output_path:
                return False, "Invalid output path"

            # Determine file format (usda for text, usd for binary)
            file_format = 'usda' if output_path.endswith('.usda') else 'usd'

            # Extract input source paths
            input_sources = [
                item['path'] for item in selected_items
                if 'path' in item and os.path.exists(item['path'])
            ]

            if not input_sources:
                return False, "No valid source paths found"

            # Create new USD stage
            root_layer = Sdf.Layer.CreateNew(
                output_path, args={'format': file_format})
            stage = Usd.Stage.Open(root_layer)

            # Set stage properties
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y if up_axis.lower() == 'y' else UsdGeom.Tokens.z)
            UsdGeom.SetStageMetersPerUnit(stage, scale)

            # Root transform prim
            root_xform = UsdGeom.Xform.Define(stage, '/root')
            root_prim = root_xform.GetPrim()

            # Process input sources based on export type
            if export_type == 'reference':
                # Create references to input sources
                references = root_prim.GetReferences()
                for source in input_sources:
                    references.AddReference(source)

            elif export_type == 'payload':
                # Create payloads instead of direct references
                payloads = root_prim.GetPayloads()
                for source in input_sources:
                    payloads.AddPayload(source)

            elif export_type == 'flatten':
                # Flatten all inputs into a single file
                for source in input_sources:
                    stage.GetRootLayer().subLayerPaths.append(source)

            else:
                return False, f"Unsupported export type: {export_type}"

            # Save the stage
            stage.GetRootLayer().Save()

            return True, f"Successfully exported to {output_path}"

        except Exception as e:
            return False, f"Export failed: {str(e)}"
        

    def export_selected_from_table(self, export_tableWidget, path_export):
        """
        Collect ALL items from table widget and export

        Args:
            export_tableWidget (QTableWidget): Table with exportable items
            path_export (str): Destination export path

        Returns:
            tuple: (bool, str) - Export status and message
        """
        #export_tableWidget = self.mainwidget.export_tableWidget
        #path_export = self.mainwidget.path_export.text()
        selected_items = []

        for row in range(export_tableWidget.rowCount()):
            # Get items for the current row
            path_item = export_tableWidget.item(row, 0)  # Adjust column index as needed
            name_item = export_tableWidget.item(row, 1)  # Adjust column index as needed
            
            # Validate items exist and have valid paths
            if (path_item is not None and 
                name_item is not None and 
                os.path.exists(path_item.text())):
                
                item_data = {
                    'path': path_item.text(),
                    'name': name_item.text()
                }
                selected_items.append(item_data)
        #print(selected_items)
        # Check if any items were found
        if not selected_items:
            return False, "No valid items found in the table"

        # Perform export
        return self.export_usd(
            selected_items,
            output_path=path_export,
            export_type='reference'  
        )
    
    def on_export_clicked(self):
        export_path = self.mainwidget.path_export.text()
        self.main_export_process(export_tableWidget=self.mainwidget.export_tableWidget, path_export=export_path)


    def main_export_process(self, export_tableWidget, path_export):
        self.export_selected_from_table(export_tableWidget, path_export)

    def export_selected_to_usd(self):
        # Get export path from the UI
        export_path = self.mainwidget.path_export.text()
        
        # Get the selected object name from the table widget
        selected_row = 0  # First row in the table
        maya_object_name = self.mainwidget.export_tableWidget.item(selected_row, 0).text()
        
        # Select the object in Maya to ensure it's the active selection
        cmds.select(maya_object_name)
        
        # Get the full path of the selected object
        maya_object_name = self.mainwidget.export_tableWidget.item(selected_row, 0).text()

        if not export_path.endswith('.usda'):
            export_path += '.usda'
        # Create and export to USD
        try:
            # Export the selected object to USD
            # Use the appropriate export command for your Maya version/setup:
            cmds.mayaUSDExport(file=export_path, selection=True)
            
            # Create a proxy to view the exported USD
            cmds.createNode('mayaUsdProxyShape', name='stageShape')
            shape_node = cmds.ls(sl=True, l=True)[0]
            cmds.setAttr('{}.filePath'.format(shape_node), export_path, type='string')
            
            # Connect time
            cmds.select(clear=True)
            cmds.connectAttr('time1.outTime', '{}.time'.format(shape_node))
            
            print(f"Successfully exported {maya_object_name} to {export_path}")
            print(f"Created USD proxy: {shape_node}")
            
            return True
        except Exception as e:
            print(f"Error exporting to USD: {str(e)}")
            return False 

    #def export_selected_usd(self):
        #stage = Usd.Stage.CreateNew('D:/Work_Year4/THESIS/02.usd')
        #xformPrim = UsdGeom.Xform.Define(stage, '/hello')
        #spherePrim = UsdGeom.Sphere.Define(stage, '/hello/world')
        #stage.GetRootLayer().Save()

        #print(stage)
        #return xformPrim, spherePrim
        #export_path = self.mainwidget.path_export.text()
        #stage = Usd.Stage.CreateNew(export_path)
        #object_name = self.mainwidget.export_tableWidget.item(0, 0).text()
        #xformPrim = UsdGeom.Xform.Define(stage, f'/{object_name}')

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
