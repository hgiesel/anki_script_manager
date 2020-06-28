import os
import json

from typing import Union
from dataclasses import asdict, replace

import jsonschema
from jsonschema import validate, RefResolver, Draft7Validator
from pathlib import Path

from aqt import mw
from aqt.qt import QDialog, QWidget, QFont, Qt
from aqt.utils import showInfo # actually needed!

from .utils import (
    script_type_to_gui_text, script_position_to_gui_text,
    pos_to_script_type, pos_to_script_position,
)
from .js_highlighter import JSHighlighter

from ..script_config_ui import Ui_ScriptConfig

from ...config import serialize_script, deserialize_script
from ...config_types import ConcreteScript, MetaScript, ScriptStorage, ScriptBool

from ...lib.interface import make_script_bool
from ...lib.registrar import get_interface

def fix_storage(store: ScriptStorage, script: ConcreteScript, to_store: ScriptBool) -> ScriptStorage:
    """save to store from script according to to_store"""

    def filter_store(tost):
        return [
            storekey[0]
            for storekey
            in asdict(tost).items() if storekey[1]
        ]

    filtered_store = filter_store(to_store)
    the_dict = dict([
        (key, getattr(script, key))
        for key
        in filtered_store
    ])

    return replace(store, **the_dict)

class ScriptConfig(QDialog):
    def __init__(self, parent, model_name, callback):
        super().__init__(parent=parent)

        self.callback = callback
        self.modelName = model_name

        self.ui = Ui_ScriptConfig()
        self.ui.setupUi(self)

        self.accepted.connect(self.onAccept)
        self.rejected.connect(self.onReject)

        self.ui.resetButton.clicked.connect(self.reset)
        self.ui.resetButton.hide()

        self.ui.saveButton.clicked.connect(self.tryAccept)
        self.ui.saveButton.setDefault(True)

        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.validateButton.clicked.connect(self.validateConditions)

        self.ui.metaLabel.setText('')
        self.ui.enableScriptCheckBox.stateChanged.connect(self.enableChangeGui)
        self.initEditor(self.ui.codeTextEdit)

    def initEditor(self, editor):
        font = editor.document().defaultFont()
        font.setFamily('Courier New')
        font.setStyleHint(QFont.Monospace)
        font.setWeight(QFont.Medium)
        font.setFixedPitch(True)
        font.setPointSize(14)

        editor.setFont(font)

        self.highlighter = JSHighlighter(editor.document())

    def setupUi(self, script):
        if isinstance(script, ConcreteScript):
            self.setupUiConcrete(script)
        else:
            self.setupUiMeta(script)

    def setupUiConcrete(self, concrete_script):
        self.ui.nameLineEdit.setText(concrete_script.name)

        self.ui.enableScriptCheckBox.setChecked(concrete_script.enabled)
        self.ui.typeComboBox.setCurrentText(script_type_to_gui_text(concrete_script.type))

        self.ui.versionLineEdit.setText(concrete_script.version)
        self.ui.descriptionTextEdit.setPlainText(concrete_script.description)

        self.ui.positionComboBox.setCurrentText(script_position_to_gui_text(concrete_script.position))
        self.ui.conditionsTextEdit.setPlainText(json.dumps(concrete_script.conditions))

        self.ui.codeTextEdit.setPlainText(concrete_script.code)

        self.enableChangeGui()

    def setupUiMeta(self, meta_script):
        self.meta = meta_script
        self.iface = get_interface(meta_script.tag)

        self.setupUiConcrete(self.iface.getter(self.meta.id, self.meta.storage))
        self.ui.metaLabel.setText(self.iface.label(self.meta.id, self.meta.storage))

        if self.iface.reset:
            self.ui.resetButton.show()

    def reset(self):
        # only available for meta scripts

        try:
            self.validateConditionsRaw()
        except:
            showInfo('Invalid Conditions. Please fix the conditions before resetting.')
        else:
            self.setupUi(self.exportData())
            self.setupUiConcrete(self.iface.reset(self.meta.id, self.meta.storage))

            self.ui.nameLineEdit.repaint()

            self.ui.enableScriptCheckBox.repaint()
            self.ui.typeComboBox.repaint()

            self.ui.versionLineEdit.repaint()
            self.ui.descriptionTextEdit.repaint()

            self.ui.positionComboBox.repaint()
            self.ui.conditionsTextEdit.repaint()

            self.ui.codeTextEdit.repaint()

    def tryAccept(self):
        try:
            self.validateConditionsRaw()
        except:
            showInfo('Invalid Conditions. Please correct the conditions or just set it to `[]`.')
        else:
            self.accept()

    def onAccept(self):
        self.callback(self.exportData())

    def onReject(self):
        pass

    def enableChangeGui(self):
        try:
            self.enableChange(self.ui.enableScriptCheckBox.isChecked(), self.iface.readonly)
        except AttributeError:
            self.enableChange(self.ui.enableScriptCheckBox.isChecked())

    def enableChange(self, state=True, readonly=make_script_bool()):
        self.ui.nameLineEdit.setReadOnly(not state or readonly.name)
        self.ui.typeComboBox.setEnabled(state and not readonly.type)

        self.ui.versionLineEdit.setReadOnly(not state or readonly.version)
        self.ui.descriptionTextEdit.setReadOnly(not state or readonly.description)

        self.ui.positionComboBox.setEnabled(state and not readonly.position)
        self.ui.conditionsTextEdit.setReadOnly(not state or readonly.conditions)

        self.ui.codeTextEdit.setReadOnly(not state or readonly.code)

    def getConditions(self): # can throw
        return json.loads(self.ui.conditionsTextEdit.toPlainText())

    def validateConditionsRaw(self):
        dirpath  = Path(f'{os.path.dirname(os.path.realpath(__file__))}', '../../json_schemas/script_cond.json')
        schema_path = dirpath.absolute().as_uri()

        with dirpath.open('r') as jsonfile:

            schema = json.load(jsonfile)
            resolver = RefResolver(
                schema_path,
                schema,
            )

            validator = Draft7Validator(schema, resolver=resolver, format_checker=None)
            instance = self.getConditions()

            validator.validate(instance)

    def validateConditions(self):
        try:
            self.validateConditionsRaw()
        except json.decoder.JSONDecodeError as e:
            showInfo(str(e))
        except jsonschema.exceptions.ValidationError as e:
            showInfo(str(e))
        else:
            showInfo('Valid Conditions.')

    def exportData(self) -> Union[ConcreteScript, MetaScript]:
        result = deserialize_script({
            'name': self.ui.nameLineEdit.text(),

            'enabled': self.ui.enableScriptCheckBox.isChecked(),
            'type': pos_to_script_type(self.ui.typeComboBox.currentIndex()),

            'version': self.ui.versionLineEdit.text(),
            'description': self.ui.descriptionTextEdit.toPlainText(),

            'position': pos_to_script_position(self.ui.positionComboBox.currentIndex()),
            'conditions': self.getConditions(),

            'code': self.ui.codeTextEdit.toPlainText(),
        })

        try:
            user_result = self.iface.setter(self.meta.id, result)

            if isinstance(user_result, ConcreteScript):
                return replace(
                    self.meta,
                    storage = fix_storage(self.meta.storage, user_result, self.iface.store),
                )

            elif user_result:
                return replace(
                    self.meta,
                    storage = fix_storage(self.meta.storage, result, self.iface.store),
                )

            else:
                return self.meta

        except AttributeError:
            return result