import sys
import os
import json
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QComboBox, QFormLayout, QMainWindow, QGraphicsOpacityEffect
)
from PyQt6.QtCore import QProcess, Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QTextCursor, QIcon

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_exe = os.path.join(os.path.dirname(__file__), "faster-whisper-xxl.exe")
        return {"exe_path": default_exe if os.path.exists(default_exe) else ""}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if not config.get("exe_path"):
                default_exe = os.path.join(os.path.dirname(__file__), "faster-whisper-xxl.exe")
                if os.path.exists(default_exe):
                    config["exe_path"] = default_exe
            return config
    except json.JSONDecodeError:
        default_exe = os.path.join(os.path.dirname(__file__), "faster-whisper-xxl.exe")
        return {"exe_path": default_exe if os.path.exists(default_exe) else ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

class FasterWhisperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Faster Whisper GUI")
        self.setWindowIcon(QIcon("zen_icon.ico"))
        self.resize(700, 500)
        self.config = load_config()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.main_tab = QWidget()
        self.config_tab = QWidget()
        self.tabs.addTab(self.main_tab, "Principal")
        self.tabs.addTab(self.config_tab, "Configuración")

        self.init_main_tab()
        self.init_config_tab()

        self.process = None
        # Efecto de fundido suave al mostrar la ventana
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(600)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

    def init_main_tab(self):
        layout = QFormLayout()

        self.file_entry = QLineEdit()
        browse_file_btn = QPushButton("Examinar")
        browse_file_btn.clicked.connect(self.browse_file)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_entry)
        file_layout.addWidget(browse_file_btn)
        layout.addRow("Archivo:", file_layout)

        self.lang_menu = QComboBox()
        self.lang_menu.addItems(["Japonés", "Inglés", "Español", "Francés", "Alemán", "Chino"])
        self.lang_menu.setCurrentText("Japonés")
        layout.addRow("Idioma:", self.lang_menu)

        self.model_menu = QComboBox()
        self.model_menu.addItems(["Pequeño", "Mediano", "Grande", "Turbo"])
        self.model_menu.setCurrentText("Mediano")
        layout.addRow("Modelo:", self.model_menu)

        self.output_dir = QLineEdit()
        output_btn = QPushButton("Examinar")
        output_btn.clicked.connect(self.browse_output_dir)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(output_btn)
        layout.addRow("Salida:", output_layout)

        self.format_menu = QComboBox()
        self.format_menu.addItems(["txt", "srt", "json", "vtt", "Todos"])
        layout.addRow("Formato:", self.format_menu)

        self.task_menu = QComboBox()
        self.task_menu.addItems(["Transcribir", "Traducir"])
        layout.addRow("Tarea:", self.task_menu)

        self.run_btn = QPushButton("Ejecutar")
        self.run_btn.clicked.connect(self.run_command)
        layout.addRow(self.run_btn)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addRow(QLabel("Resultado:"), self.result_text)

        self.copy_btn = QPushButton("Copiar")
        self.copy_btn.clicked.connect(self.copy_result)
        layout.addRow(self.copy_btn)

        self.main_tab.setLayout(layout)

    def init_config_tab(self):
        layout = QFormLayout()

        self.exe_entry = QLineEdit()
        self.exe_entry.setText(self.config.get("exe_path", ""))
        exe_btn = QPushButton("Buscar")
        exe_btn.clicked.connect(self.browse_exe)
        exe_layout = QHBoxLayout()
        exe_layout.addWidget(self.exe_entry)
        exe_layout.addWidget(exe_btn)
        layout.addRow("Ruta del ejecutable:", exe_layout)

        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.save_settings)
        layout.addRow(save_btn)

        self.config_tab.setLayout(layout)

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", filter="Audios (*.mp3 *.wav *.m4a *.flac *.webm *.opus *.ogg)")
        if file:
            self.file_entry.setText(file)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")
        if directory:
            self.output_dir.setText(directory)

    def browse_exe(self):
        exe, _ = QFileDialog.getOpenFileName(self, "Seleccionar ejecutable", filter="Ejecutables (*.exe)")
        if exe:
            self.exe_entry.setText(exe)

    def save_settings(self):
        self.config["exe_path"] = self.exe_entry.text()
        save_config(self.config)
        QMessageBox.information(self, "Configuración", "Ruta guardada correctamente.")

    def run_command(self):
        exe = self.exe_entry.text().strip()
        file = self.file_entry.text().strip()
        output_dir = self.output_dir.text().strip()
        if not output_dir:
            output_dir = os.path.dirname(file)

        if not exe or not os.path.exists(exe):
            QMessageBox.critical(self, "Error", "Configura la ruta del ejecutable.")
            return

        if not file:
            QMessageBox.critical(self, "Error", "Selecciona un archivo de audio.")
            return

        language_map = {
            "Japonés": "Japanese",
            "Inglés": "English",
            "Español": "Spanish",
            "Francés": "French",
            "Alemán": "German",
            "Chino": "Chinese"
        }
        format_map = {
            "Todos": "all",
            "txt": "txt",
            "srt": "srt",
            "json": "json",
            "vtt": "vtt"
        }
        task_map = {
            "Transcribir": "transcribe",
            "Traducir": "translate"
        }
        model_map = {
            "Pequeño": "small",
            "Mediano": "medium",
            "Grande": "large",
            "Turbo": "turbo"
        }

        args = [exe, file,
                "--language", language_map[self.lang_menu.currentText()],
                "--task", task_map[self.task_menu.currentText()],
                "--output_dir", output_dir,
                "--output_format", format_map[self.format_menu.currentText()],
                "--model", model_map[self.model_menu.currentText()]]

        self.process = QProcess(self)
        self.process.setProgram(args[0])
        self.process.setArguments(args[1:])
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.process_finished)

        self.result_text.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Procesando...")
        self.run_btn.setStyleSheet("QPushButton:disabled { color: white; background-color: #666; }")
        self.process.start()

    def read_output(self):
        text = self.process.readAllStandardOutput().data().decode("utf-8")
        self.result_text.moveCursor(QTextCursor.MoveOperation.End)
        self.result_text.insertPlainText(text)
        self.result_text.ensureCursorVisible()

    def process_finished(self):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Ejecutar")
        self.run_btn.setStyleSheet("")

    def copy_result(self):
        texto = self.result_text.toPlainText()
        lineas = texto.splitlines()
        solo_texto = []

        for linea in lineas:
            match = re.match(r"\[\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}\.\d{3}\]\s*(.*)", linea)
            if match:
                solo_texto.append(match.group(1))
            elif re.search(r"[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f]", linea):
                solo_texto.append(linea.strip())

        resultado = "\n".join(solo_texto)
        QApplication.clipboard().setText(resultado)

        # Cambiar el texto y color del botón temporalmente
        boton = self.sender()
        original_text = boton.text()
        boton.setText("¡Copiado!")
        boton.setStyleSheet("color: #00FF7F; font-weight: bold;")
        boton.setEnabled(False)

        def restaurar_boton():
            boton.setText(original_text)
            boton.setStyleSheet("")
            boton.setEnabled(True)

        QTimer.singleShot(2000, restaurar_boton)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FasterWhisperApp()
    window.show()
    sys.exit(app.exec())