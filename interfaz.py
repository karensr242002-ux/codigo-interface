import sys
import pyvisa
import numpy as np
import time
from datetime import datetime
import os
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Barrido LCR - Tiempo Real")
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        self.running = False
        self.f = []
        self.val1 = []
        self.val2 = []

        self.setup_ui()
        self.setup_lcr()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        self.tabla_valores = QTableWidget(0, 4)
        self.tabla_valores.setHorizontalHeaderLabels(["#", "Frecuencia (Hz)", "Valor Primario", "Valor Secundario"])
        header = self.tabla_valores.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.tabla_valores.setMinimumWidth(450)
        self.tabla_valores.verticalHeader().setDefaultSectionSize(22)
        self.tabla_valores.setWordWrap(False)
        
        # Configurar para que la tabla seleccione automáticamente la última fila
        self.tabla_valores.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_valores.setSelectionMode(QTableWidget.SingleSelection)

        self.boton = QPushButton("▶ Iniciar Barrido")
        self.boton.clicked.connect(self.iniciar_barrido)

        self.boton_stop = QPushButton("⏹ Detener")
        self.boton_stop.clicked.connect(self.detener)
        self.boton_stop.setEnabled(False)

        self.boton_guardar = QPushButton("💾 Guardar")
        self.boton_guardar.clicked.connect(self.guardar_datos)
        self.boton_guardar.setEnabled(False)

        left_panel.addWidget(self.tabla_valores)
        left_panel.addWidget(self.boton)
        left_panel.addWidget(self.boton_stop)
        left_panel.addWidget(self.boton_guardar)
        left_panel.addStretch(1)

        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)

        self.label_valores = QLabel("Frec: -- Hz | V1: -- | V2: --")
        self.label_valores.setStyleSheet("font-size: 14px; font-weight: bold; color: green; padding: 4px; background: #f0f0f0;")

        self.label_estado = QLabel("Listo - Presiona Iniciar")
        self.label_estado.setStyleSheet("font-weight: bold; color: blue; padding: 4px;")

        right_panel.addWidget(self.canvas, 1)
        bottom_panel = QHBoxLayout()
        bottom_panel.addWidget(self.label_valores)
        bottom_panel.addWidget(self.label_estado)
        right_panel.addLayout(bottom_panel)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

        contenedor = QWidget()
        contenedor.setLayout(main_layout)
        self.setCentralWidget(contenedor)

    def setup_lcr(self):
        self.rm = pyvisa.ResourceManager()
        try:
            print("Recursos VISA:", self.rm.list_resources())
            self.lcr = self.rm.open_resource('USB0::0x0471::0x2827::479A25127::INSTR')
            
            # ← TU CÓDIGO FUNCIONAL EXACTO
            self.lcr.timeout = 10000
            self.lcr.write_termination = '\n'
            self.lcr.read_termination = '\n'
            self.lcr.clear()

            print("Equipo:", self.lcr.query('*IDN?'))
            self.label_estado.setText("✓ LCR conectado")
        except Exception as e:
            print(f"❌ LCR: {e}")
            self.label_estado.setText("❌ Error conexión")
    
    def scroll_to_bottom(self):
        """Desplaza la tabla hasta la última fila"""
        row_count = self.tabla_valores.rowCount()
        if row_count > 0:
            # Desplazar a la última fila
            self.tabla_valores.scrollToBottom()
            # Seleccionar la última fila para mejor visualización
            self.tabla_valores.selectRow(row_count - 1)

    def iniciar_barrido(self):
        if self.running:
            return

        self.running = True
        self.boton.setEnabled(False)
        self.boton_stop.setEnabled(True)
        self.boton_guardar.setEnabled(False)
        self.label_estado.setText("🔄 Midiendo...")

        frecs = np.logspace(np.log10(20), np.log10(500000), 201)
        self.f = []
        self.val1 = []
        self.val2 = []
        self.tabla_valores.setRowCount(0)

        # Gráficas
        self.fig.clear()
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.line1, = self.ax1.plot([], [], 'b-', linewidth=2, label="Valor Primario")
        self.line2, = self.ax2.plot([], [], 'r-', linewidth=2, label="Valor Secundario")
        self.ax1.set_xscale('log')
        self.ax2.set_xscale('log')
        
        # Configurar el formateador del eje X para mostrar números enteros
        def format_func(value, pos):
            if value >= 1000:
                if value >= 1000000:
                    return f'{int(value/1000000)}M'
                elif value >= 1000:
                    return f'{int(value/1000)}k'
            return f'{int(value)}'
        
        # Aplicar el formateador a ambos ejes
        self.ax1.xaxis.set_major_formatter(ticker.FuncFormatter(format_func))
        self.ax2.xaxis.set_major_formatter(ticker.FuncFormatter(format_func))
        
        # Configurar ticks principales para que sean más legibles
        self.ax1.xaxis.set_major_locator(ticker.LogLocator(base=10, subs=[1,2,5,10]))
        self.ax2.xaxis.set_major_locator(ticker.LogLocator(base=10, subs=[1,2,5,10]))
        
        self.ax1.set_ylabel("Valor Primario")
        self.ax2.set_ylabel("Valor Secundario")
        self.ax2.set_xlabel("Frecuencia (Hz)")
        self.ax1.grid(alpha=0.3)
        self.ax2.grid(alpha=0.3)
        self.ax1.legend()
        self.ax2.legend()
        
        # Ajustar diseño para que no se corten las etiquetas
        self.fig.tight_layout()
        
        self.canvas.draw()

        # ← TU CÓDIGO FUNCIONAL EXACTO
        for i, freq in enumerate(frecs):
            if not self.running:
                break

            try:
                # PASO 1: Configurar frecuencia
                self.lcr.write(f'FREQ {freq:.2f}')
                
                # PASO 2: ESPERAR que termine
                self.lcr.write('*OPC')
                opc = self.lcr.query('*OPC?')
                
                # PASO 3: Limpiar buffer
                self.lcr.clear()
                
                # PASO 4: Leer datos
                data = self.lcr.query('FETC?').strip()
                valores = data.split(',')
                v1 = float(valores[0])
                v2 = float(valores[1])

                self.f.append(freq)
                self.val1.append(v1)
                self.val2.append(v2)

                # TABLA con TU FORMATO
                row = self.tabla_valores.rowCount()
                self.tabla_valores.insertRow(row)
                self.tabla_valores.setItem(row, 0, QTableWidgetItem(str(i + 1)))
                self.tabla_valores.setItem(row, 1, QTableWidgetItem(f"{freq:.2f}"))
                self.tabla_valores.setItem(row, 2, QTableWidgetItem(f"{v1:.6f}"))
                self.tabla_valores.setItem(row, 3, QTableWidgetItem(f"{v2:.6f}"))
                
                # AUTO-SCROLL: Desplazar automáticamente a la última fila
                self.scroll_to_bottom()

                # LABEL con TU FORMATO
                self.label_valores.setText(f"Frec: {freq:.2f} Hz | V1: {v1:.6f} | V2: {v2:.6f}")

                # Gráficas
                self.line1.set_data(self.f, self.val1)
                self.line2.set_data(self.f, self.val2)
                self.ax1.relim()
                self.ax1.autoscale_view()
                self.ax2.relim()
                self.ax2.autoscale_view()
                self.canvas.draw()
                QApplication.processEvents()

                print(f"Punto {i+1:03d} -> {freq:.2f} Hz | {v1:.6f} | {v2:.6f}")

                time.sleep(0.05)

            except Exception as e:
                print(f"Error punto {i+1}: {e}")
                self.label_estado.setText(f"⚠ Error punto {i+1}")
                continue

        self.running = False
        self.boton.setEnabled(True)
        self.boton_stop.setEnabled(False)
        self.boton_guardar.setEnabled(True)
        self.label_estado.setText("✅ Barrido completo ✓")

    def detener(self):
        self.running = False
        self.label_estado.setText("⏹ Detenido")

    def guardar_datos(self):
        if not self.f:
            self.label_estado.setText("❌ No hay datos")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar datos",
            f"lcr_{timestamp}.xlsx",
            "Excel (*.xlsx)"
        )

        if filename:
            df = pd.DataFrame({
                'Frecuencia (Hz)': self.f,
                'Valor Primario': self.val1,
                'Valor Secundario': self.val2
            })
            df.to_excel(filename, index=False, float_format='%.10f')
            self.label_estado.setText("💾 Guardado correctamente")
            print("Archivo:", filename)

    def closeEvent(self, event):
        if hasattr(self, 'lcr'):
            self.lcr.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = Ventana()
    ventana.show()
    sys.exit(app.exec_())