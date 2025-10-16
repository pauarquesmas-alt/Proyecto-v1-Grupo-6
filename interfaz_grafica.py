# -- coding: utf-8 --
import threading
import time
import re
from collections import deque

import serial
import serial.tools.list_ports

import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ===== Parámetros de serie =====
PUERTO_DESEADO = "COM9"      # Ajusta según tu equipo
BAUDRATE = 9600
TIMEOUT_S = 1.0

# ===== Parámetros de visualización =====
N_MUESTRAS = 120
REFRESH_MS = 100
PATRON_TH = re.compile(r"T:(-?\d+(?:\.\d+)?).*H:(-?\d+(?:\.\d+)?)")

# ---------- Utilidades de puerto ----------
def elegir_puerto(deseado: str | None = None) -> str:
    disponibles = [p.device for p in serial.tools.list_ports.comports()]
    print("[INFO] Puertos disponibles:", disponibles)
    if deseado and deseado in disponibles:
        return deseado
    if not disponibles:
        raise RuntimeError("No hay puertos serie disponibles.")
    if deseado and deseado not in disponibles:
        print(f"[AVISO] {deseado} no encontrado. Usando {disponibles[0]}")
    return disponibles[0]

def abrir_serial(device: str) -> serial.Serial:
    try:
        ser = serial.Serial(device, BAUDRATE, timeout=TIMEOUT_S)
        time.sleep(2.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except serial.SerialException as e:
        raise RuntimeError(f"No se pudo abrir {device}: {e}")

# ---------- Aplicación ----------
class EstacionGUI:
    def _init_(self, root: tk.Tk):
        self.root = root
        self.root.title("Estación de Tierra — Sistema Satelital")
        self.root.minsize(860, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 20, "italic"))
        style.configure("TButton", padding=8)

        # Estado
        self.ser = None
        self.hilo_rx = None
        self.rx_activa = threading.Event()
        self.conectado = False

        self.tiempos = deque(maxlen=N_MUESTRAS)
        self.temperaturas = deque(maxlen=N_MUESTRAS)
        self.humedades = deque(maxlen=N_MUESTRAS)
        self.contador = 0

        # ---------- Layout principal ----------
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Cabecera (sin subtítulo)
        header = ttk.Frame(self.root, padding=(12, 10))
        header.grid(row=0, column=0, columnspan=2, sticky="nsew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Estación de Tierra", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        # Cuerpo: plots + barra lateral
        body = ttk.Frame(self.root, padding=10)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        panel_plots = ttk.Frame(body)
        panel_plots.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_plots.grid_rowconfigure(0, weight=1)
        panel_plots.grid_columnconfigure(0, weight=1)

        sidebar = ttk.Frame(body, width=160)
        sidebar.grid(row=0, column=1, sticky="ns")
        for r in range(5):
            sidebar.grid_rowconfigure(r, weight=0)
        sidebar.grid_rowconfigure(6, weight=1)

        # Botones
        self.btn_iniciar = ttk.Button(sidebar, text="Iniciar", command=self.on_iniciar)
        self.btn_parar   = ttk.Button(sidebar, text="Parar", command=self.on_parar, state="disabled")
        self.btn_rean    = ttk.Button(sidebar, text="Reanudar", command=self.on_reanudar, state="disabled")
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.btn_parar.grid(row=1, column=0, sticky="ew", pady=8)
        self.btn_rean.grid(row=2, column=0, sticky="ew", pady=8)

        ttk.Separator(sidebar, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=12)
        self.lbl_estado = ttk.Label(sidebar, text="Puerto: —\nMuestras: 0\nÚltima T/H: —/—", justify="left")
        self.lbl_estado.grid(row=4, column=0, sticky="ew")

        # Figura con dos subgráficas — sin solapes
        self.fig = Figure(figsize=(7, 5), dpi=100, constrained_layout=True)
        self.axT = self.fig.add_subplot(2, 1, 1)
        self.axH = self.fig.add_subplot(2, 1, 2)

        self.axT.set_title("Temperatura (°C) — tiempo real")
        self.axT.set_ylabel("°C")
        self.axT.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)
        # Importante: sin etiqueta X en el gráfico superior para no pisar el título inferior
        self.axT.set_xlabel("")

        self.axH.set_title("Humedad (%) — tiempo real")
        self.axH.set_xlabel("Muestras")   # solo aquí
        self.axH.set_ylabel("%")
        self.axH.set_ylim(0, 100)
        self.axH.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)

        # Por si tu backend no respeta constrained_layout
        self.fig.subplots_adjust(hspace=0.35, bottom=0.08, top=0.95)

        self.lineT, = self.axT.plot([], [], lw=1.8, label="T")
        self.lineH, = self.axH.plot([], [], lw=1.8, label="H")
        self.axT.legend(loc="upper right")
        self.axH.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(self.fig, master=panel_plots)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # (Eliminada la barra de estado inferior)

        # Refresco periódico
        self.root.after(REFRESH_MS, self.actualizar_graficas)

    # ---------- Callbacks ----------
    def on_iniciar(self):
        if self.hilo_rx and self.hilo_rx.is_alive():
            return
        try:
            device = elegir_puerto(PUERTO_DESEADO)
            self.ser = abrir_serial(device)
            self.conectado = True
            self.lbl_estado.config(text=f"Puerto: {device}\nMuestras: 0\nÚltima T/H: —/—")
        except Exception as e:
            messagebox.showerror("Conexión", str(e))
            return

        self.tiempos.clear(); self.temperaturas.clear(); self.humedades.clear()
        self.contador = 0

        self.rx_activa.set()
        self.hilo_rx = threading.Thread(target=self.recepcion, daemon=True)
        self.hilo_rx.start()

        self.btn_iniciar.config(state="disabled")
        self.btn_parar.config(state="normal")
        self.btn_rean.config(state="normal")

    def on_parar(self):
        if not self.conectado: return
        try:
            self.ser.write(b"Parar")
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar 'Parar': {e}")

    def on_reanudar(self):
        if not self.conectado: return
        try:
            self.ser.write(b"Reanudar")
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar 'Reanudar': {e}")

    # ---------- Hilo de recepción ----------
    def recepcion(self):
        proximo_ping = time.monotonic() + 1.0
        while self.rx_activa.is_set():
            try:
                if self.ser.in_waiting > 0:
                    linea = self.ser.readline().decode('utf-8', errors='replace').strip()
                    if linea:
                        m = PATRON_TH.search(linea)
                        if m:
                            t = float(m.group(1)); h = float(m.group(2))
                            self.contador += 1
                            self.tiempos.append(self.contador)
                            self.temperaturas.append(t)
                            self.humedades.append(h)
                            self.lbl_estado.config(
                                text=f"Puerto: {self.ser.port}\nMuestras: {self.contador}\nÚltima T/H: {t:.1f} / {h:.1f}"
                            )
                        else:
                            print("[RX]", linea)

                ahora = time.monotonic()
                if ahora >= proximo_ping:
                    try:
                        self.ser.write(b"P")
                    except serial.SerialException as e:
                        print("[ERROR TX]", e); break
                    proximo_ping = ahora + 1.0

                time.sleep(0.01)

            except serial.SerialException as e:
                print("[ERROR SERIE]", e)
                break
            except Exception as e:
                print("[ERROR]", e)
                time.sleep(0.1)

        print("[INFO] Recepción detenida.")

    # ---------- Refresco de gráficas ----------
    def actualizar_graficas(self):
        self.lineT.set_data(self.tiempos, self.temperaturas)
        self.lineH.set_data(self.tiempos, self.humedades)

        if self.tiempos:
            x0 = max(0, self.tiempos[0]-1); x1 = self.tiempos[-1]+1
            self.axT.set_xlim(x0, x1); self.axH.set_xlim(x0, x1)

            tmin = min(self.temperaturas); tmax = max(self.temperaturas)
            margen = max(0.5, (tmax - tmin) * 0.15)
            self.axT.set_ylim(tmin - margen, tmax + margen)

        self.canvas.draw_idle()
        self.root.after(REFRESH_MS, self.actualizar_graficas)

    # ---------- Cierre ----------
    def on_close(self):
        self.rx_activa.clear()
        try:
            if self.hilo_rx and self.hilo_rx.is_alive():
                self.hilo_rx.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.root.destroy()

# ---------- main ----------
def main():
    root = tk.Tk()
    EstacionGUI(root)
    root.mainloop()

if _name_ == "_main_":
    main()
