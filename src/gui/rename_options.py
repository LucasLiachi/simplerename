from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                           QLabel, QSpinBox, QGroupBox, QCheckBox, QComboBox)
from PyQt6.QtCore import pyqtSignal

class RenameOptions(QWidget):
    optionsChanged = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Text modifications group
        text_group = QGroupBox("Text Modifications")
        text_layout = QVBoxLayout()
        
        # Prefix/Suffix
        prefix_layout = QHBoxLayout()
        self.prefix_input = QLineEdit()
        prefix_layout.addWidget(QLabel("Prefix:"))
        prefix_layout.addWidget(self.prefix_input)
        
        suffix_layout = QHBoxLayout()
        self.suffix_input = QLineEdit()
        suffix_layout.addWidget(QLabel("Suffix:"))
        suffix_layout.addWidget(self.suffix_input)
        
        # Find and Replace
        replace_layout = QHBoxLayout()
        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        replace_layout.addWidget(QLabel("Find:"))
        replace_layout.addWidget(self.find_input)
        replace_layout.addWidget(QLabel("Replace:"))
        replace_layout.addWidget(self.replace_input)

        text_layout.addLayout(prefix_layout)
        text_layout.addLayout(suffix_layout)
        text_layout.addLayout(replace_layout)
        text_group.setLayout(text_layout)

        # Case options group
        case_group = QGroupBox("Case Options")
        case_layout = QVBoxLayout()
        self.case_combo = QComboBox()
        self.case_combo.addItems(["Keep Original", "UPPERCASE", "lowercase", "Title Case"])
        case_layout.addWidget(self.case_combo)
        case_group.setLayout(case_layout)

        # Numbering options group
        number_group = QGroupBox("Numbering")
        number_layout = QHBoxLayout()
        
        self.use_numbers = QCheckBox("Add Numbers")
        self.start_number = QSpinBox()
        self.start_number.setMinimum(0)
        self.start_number.setMaximum(9999)
        
        self.padding_spin = QSpinBox()
        self.padding_spin.setMinimum(1)
        self.padding_spin.setMaximum(10)
        self.padding_spin.setValue(1)
        
        number_layout.addWidget(self.use_numbers)
        number_layout.addWidget(QLabel("Start at:"))
        number_layout.addWidget(self.start_number)
        number_layout.addWidget(QLabel("Padding:"))
        number_layout.addWidget(self.padding_spin)
        number_group.setLayout(number_layout)

        # Add all groups to main layout
        layout.addWidget(text_group)
        layout.addWidget(case_group)
        layout.addWidget(number_group)
        layout.addStretch()
        
        self.setLayout(layout)

    def connect_signals(self):
        widgets = [
            self.prefix_input, self.suffix_input,
            self.find_input, self.replace_input,
            self.case_combo, self.use_numbers,
            self.start_number, self.padding_spin
        ]
        
        for widget in widgets:
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.emit_options)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.emit_options)
            elif isinstance(widget, (QCheckBox, QSpinBox)):
                widget.valueChanged.connect(self.emit_options)

    def emit_options(self):
        options = {
            'prefix': self.prefix_input.text(),
            'suffix': self.suffix_input.text(),
            'find': self.find_input.text(),
            'replace': self.replace_input.text(),
            'case': self.case_combo.currentText(),
            'use_numbers': self.use_numbers.isChecked(),
            'start_number': self.start_number.value(),
            'padding': self.padding_spin.value()
        }
        self.optionsChanged.emit(options)

    def get_options(self):
        return {
            'prefix': self.prefix_input.text(),
            'suffix': self.suffix_input.text(),
            'find': self.find_input.text(),
            'replace': self.replace_input.text(),
            'case': self.case_combo.currentText(),
            'use_numbers': self.use_numbers.isChecked(),
            'start_number': self.start_number.value(),
            'padding': self.padding_spin.value()
        }
