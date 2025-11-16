# -*- coding: utf-8 -*-
import threading
import time
from collections import deque
import statistics
import math

import serial
import serial.tools.list_ports

import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ===== Parámetros de serie =====
PUERTO_DESEADO = "COM4"     # <- Ajusta si hace falta
BAUDRATE = 9600
TIMEOUT_S = 1.0

# ===== Parámetros de visualización =====
N_MUESTRAS = 120
REFRESH_MS = 100
VENTANA_MEDIA = 10

# ===== Radar =====
RADAR_R_MAX = 50.0          # cm, eje radial 0..50
TRAIL_GRADOS = 20           # ángulo detrás del haz donde se conserva rastro
TRAIL_MAX_PUNTOS = 50       # puntos guardados para el rastro

# ---------- Utilidades ----------
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
        time.sleep(2.0)  # estabilizar
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except serial.SerialException as e:
        raise RuntimeError(f"No se pudo abrir {device}: {e}")


# ---------- Aplicación ----------
class EstacionGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Estación de Tierra — Sistema Satelital")
        self.root.minsize(1180, 640)
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
        self.medias = deque(maxlen=N_MUESTRAS)
        self.contador = 0

        self.limite_alarma = 30.0
        self.contador_altas = 0
        self.calculo_en_tierra = True  # por defecto: Python

        # Radar (último punto y rastro)
        self.angulo_radar = 0.0
        self.distancia_radar = 0.0
        # guardamos tuples (timestamp, angle_deg, dist_cm)
        self.trail = deque(maxlen=TRAIL_MAX_PUNTOS)

        # ---------- Layout ----------
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self.root, padding=(12, 10))
        header.grid(row=0, column=0, columnspan=2, sticky="nsew")
        ttk.Label(header, text="Estación de Tierra", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        body = ttk.Frame(self.root, padding=10)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        panel_plots = ttk.Frame(body)
        panel_plots.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_plots.grid_rowconfigure(0, weight=1)
        panel_plots.grid_columnconfigure(0, weight=3)   # gráficas tiempo
        panel_plots.grid_columnconfigure(1, weight=2)   # radar

        sidebar = ttk.Frame(body, width=240)
        sidebar.grid(row=0, column=1, sticky="ns")

        # --- Botones de control ---
        self.btn_iniciar = ttk.Button(sidebar, text="Iniciar conexión", command=self.on_iniciar)
        self.btn_parar   = ttk.Button(sidebar, text="Parar / Reanudar (3:)", command=self.on_parar, state="disabled")
        self.btn_periodo = ttk.Button(sidebar, text="Cambiar periodo (1:s)", command=self.on_periodo, state="disabled")
        self.btn_orient  = ttk.Button(sidebar, text="Orientar servo (2:°)", command=self.on_orient, state="disabled")
        self.btn_auto    = ttk.Button(sidebar, text="Barrido automático (7:)", command=self.on_auto, state="disabled")
        self.btn_limite  = ttk.Button(sidebar, text="Límite alarma medias (5:valor)", command=self.on_limite)

        self.btn_iniciar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.btn_parar.grid(row=1, column=0, sticky="ew", pady=6)
        self.btn_periodo.grid(row=2, column=0, sticky="ew", pady=6)
        self.btn_orient.grid(row=3, column=0, sticky="ew", pady=6)
        self.btn_auto.grid(row=4, column=0, sticky="ew", pady=6)
        self.btn_limite.grid(row=5, column=0, sticky="ew", pady=10)

        ttk.Separator(sidebar, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=10)

        ttk.Label(sidebar, text="Modo de cálculo de medias:").grid(row=7, column=0, sticky="w", padx=5)
        self.modo_var = tk.StringVar(value="tierra")
        ttk.Radiobutton(
            sidebar, text="En Tierra (Python)", variable=self.modo_var,
            value="tierra", command=self.on_modo_calculo
        ).grid(row=8, column=0, sticky="w", padx=10)
        ttk.Radiobutton(
            sidebar, text="En Satélite (Arduino)", variable=self.modo_var,
            value="satelite", command=self.on_modo_calculo
        ).grid(row=9, column=0, sticky="w", padx=10)

        ttk.Separator(sidebar, orient="horizontal").grid(row=10, column=0, sticky="ew", pady=12)

        self.lbl_estado = ttk.Label(
            sidebar, text="Puerto: —\nMuestras: 0\nÚltima T/H: —/—", justify="left"
        )
        self.lbl_estado.grid(row=11, column=0, sticky="ew")

        # ---------- Gráficas T/H/Media ----------
        self.fig = Figure(figsize=(7, 6), dpi=100, constrained_layout=True)
        self.axT = self.fig.add_subplot(3, 1, 1)
        self.axH = self.fig.add_subplot(3, 1, 2)
        self.axM = self.fig.add_subplot(3, 1, 3)

        self.axT.set_title("Temperatura (°C)")
        self.axT.set_ylabel("°C")
        self.axH.set_title("Humedad (%)")
        self.axH.set_ylabel("%")
        self.axM.set_title(f"Media móvil temperatura ({VENTANA_MEDIA} últimas)")
        self.axM.set_ylabel("°C")

        for ax in (self.axT, self.axH, self.axM):
            ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)

        self.lineT, = self.axT.plot([], [], lw=1.8, label="Temperatura")
        self.lineH, = self.axH.plot([], [], lw=1.8, label="Humedad")
        self.lineM, = self.axM.plot([], [], lw=1.8, label="Media 10", color="orange")
        self.lineLimit = self.axM.axhline(
            self.limite_alarma, color="red", linestyle="--", label="Límite alarma"
        )

        for ax in (self.axT, self.axH, self.axM):
            ax.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(self.fig, master=panel_plots)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # ---------- Radar semicircular 0..180° con rastro ----------
        self.figRadar = Figure(figsize=(5, 4), dpi=100)
        self.axRadar = self.figRadar.add_subplot(111, polar=True)
        self.configurar_radar_axes()

        self.radar_canvas = FigureCanvasTkAgg(self.figRadar, master=panel_plots)
        self.radar_canvas.draw()
        self.radar_canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew")

        # refresco periódico
        self.root.after(REFRESH_MS, self.actualizar_vista)

    # ----- Config ejes del radar -----
    def configurar_radar_axes(self):
        ax = self.axRadar
        ax.clear()
        ax.set_theta_zero_location('E')    # 0° a la derecha
        ax.set_theta_direction(-1)         # sentido horario (0..180 arriba)
        ax.set_thetalim(0, math.pi)        # 0..180°
        ax.set_rmax(RADAR_R_MAX)
        ax.set_rticks([10, 20, 30, 40, 50])
        ax.set_title("Radar de Ultrasonido (0–180°)\nDistancia 0–50 cm", pad=14)
        ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)

    # ---------- Callbacks ----------
    def on_iniciar(self):
        if self.hilo_rx and self.hilo_rx.is_alive():
            return
        try:
            device = elegir_puerto(PUERTO_DESEADO)
            self.ser = abrir_serial(device)
            self.conectado = True
            self.lbl_estado.config(
                text=f"Puerto: {device}\nMuestras: 0\nÚltima T/H: —/—"
            )
        except Exception as e:
            messagebox.showerror("Conexión", str(e))
            return

        self.tiempos.clear()
        self.temperaturas.clear()
        self.humedades.clear()
        self.medias.clear()
        self.trail.clear()
        self.contador = 0

        self.rx_activa.set()
        self.hilo_rx = threading.Thread(target=self.recepcion, daemon=True)
        self.hilo_rx.start()

        self.btn_iniciar.config(state="disabled")
        self.btn_parar.config(state="normal")
        self.btn_periodo.config(state="normal")
        self.btn_orient.config(state="normal")
        self.btn_auto.config(state="normal")

    def on_parar(self):
        if not self.conectado:
            return
        try:
            self.ser.write(b"3:\n")  # toggle on/off datos T/H
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar '3:': {e}")

    def on_periodo(self):
        if not self.conectado:
            return
        valor = simple_input(self.root, "Nuevo periodo (s) para T/H:")
        if not valor:
            return
        try:
            s = int(valor)
            self.ser.write(f"1:{s}\n".encode("utf-8"))
        except Exception:
            messagebox.showerror("Error", "Valor inválido")

    def on_orient(self):
        if not self.conectado:
            return
        valor = simple_input(self.root, "Nueva orientación servo (0–180 grados):")
        if not valor:
            return
        try:
            ang = int(valor)
            ang = max(0, min(180, ang))
            self.ser.write(f"2:{ang}\n".encode("utf-8"))
        except Exception:
            messagebox.showerror("Error", "Valor inválido")

    def on_auto(self):
        if not self.conectado:
            return
        try:
            self.ser.write(b"7:\n")  # reactivar barrido automático en el satélite
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar '7:': {e}")

    def on_limite(self):
        val = simple_input(self.root, "Nuevo límite de alarma (°C):")
        if val:
            try:
                self.limite_alarma = float(val)
                if self.conectado:
                    self.ser.write(f"5:{self.limite_alarma}\n".encode("utf-8"))
                self.lineLimit.remove()
                self.lineLimit = self.axM.axhline(
                    self.limite_alarma, color="red", linestyle="--", label="Límite alarma"
                )
                self.axM.legend(loc="upper right")
                self.canvas.draw_idle()
            except ValueError:
                messagebox.showerror("Error", "Valor no válido")

    def on_modo_calculo(self):
        modo = self.modo_var.get()
        self.calculo_en_tierra = (modo == "tierra")
        try:
            if self.conectado and not self.calculo_en_tierra:
                self.ser.write(b"4:\n")  # activar cálculo de medias en satélite
            messagebox.showinfo(
                "Modo",
                f"Cálculo {'en Tierra (Python)' if self.calculo_en_tierra else 'en Satélite (Arduino)'}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar '4:': {e}")

    # ---------- Recepción ----------
    def recepcion(self):
        while self.rx_activa.is_set():
            try:
                if self.ser.in_waiting > 0:
                    linea = self.ser.readline().decode(
                        'utf-8', errors='replace'
                    ).strip()
                    if not linea:
                        continue
                    partes = linea.split(':')
                    codigo = partes[0]

                    # 1:t:h  -> temperatura/humedad
                    if codigo == "1" and len(partes) >= 3:
                        try:
                            t = float(partes[1])
                            h = float(partes[2])
                        except ValueError:
                            continue
                        self.contador += 1
                        self.tiempos.append(self.contador)
                        self.temperaturas.append(t)
                        self.humedades.append(h)

                        # media en tierra
                        if self.calculo_en_tierra and len(self.temperaturas) >= VENTANA_MEDIA:
                            media = statistics.mean(
                                list(self.temperaturas)[-VENTANA_MEDIA:]
                            )
                            self.medias.append(media)
                            self.comprobar_alarma(media)

                        self.lbl_estado.config(
                            text=(
                                f"Puerto: {self.ser.port}\n"
                                f"Muestras: {self.contador}\n"
                                f"Última T/H: {t:.1f} / {h:.1f}"
                            )
                        )

                    # 4:media  -> media calculada en satélite
                    elif codigo == "4" and len(partes) >= 2:
                        try:
                            media = float(partes[1])
                        except ValueError:
                            continue
                        self.medias.append(media)
                        self.comprobar_alarma(media)

                    # 5: -> alarma tres medias en satélite
                    elif codigo == "5":
                        self.root.bell()
                        messagebox.showwarning(
                            "⚠ Alarma",
                            "Tres medias consecutivas superan el límite (enviada por Satélite)"
                        )

                    # 2:dist:angulo  -> radar
                    elif codigo == "2" and len(partes) >= 3:
                        try:
                            dist = float(partes[1])
                            ang = float(partes[2])
                        except ValueError:
                            continue
                        dist = max(0.0, min(RADAR_R_MAX, dist))
                        ang = max(0.0, min(180.0, ang))
                        self.angulo_radar = ang
                        self.distancia_radar = dist
                        self.trail.append((time.monotonic(), ang, dist))

                    # 3: -> error sensor T/H
                    elif codigo == "3":
                        print("[ALERTA] Error de sensor T/H (3:)")

                    # 6: -> fallo sensor distancia
                    elif codigo == "6":
                        self.root.bell()
                        messagebox.showwarning(
                            "⚠ Alarma", "Fallo en el sensor de distancia (HC-SR04)"
                        )

                time.sleep(0.01)
            except Exception as e:
                print("[ERROR RX]", e)
                time.sleep(0.1)

    # ---------- Alarma (medias) ----------
    def comprobar_alarma(self, media):
        if media > self.limite_alarma:
            self.contador_altas += 1
        else:
            self.contador_altas = 0
        if self.contador_altas >= 3:
            self.root.bell()
            messagebox.showwarning(
                "⚠ Alarma",
                f"Tres medias consecutivas superan {self.limite_alarma:.1f} °C"
            )
            self.contador_altas = 0

    # ---------- Dibujo Radar con rastro en líneas ----------
 # ---------- Dibuix Radar amb rastre ----------
    def dibujar_radar(self):
        # reconfig eixos (manté semicercle 0..180)
        self.configurar_radar_axes()

        # Si hi ha rastre, dibuixem línies entre els punts antics
        if len(self.trail) >= 2:
            # trail = [(timestamp, ang_deg, dist_cm), ...]
            # Convertim a llistes polars
            angles = []
            distancias = []
            for _, ang, dist in self.trail:
                angles.append(math.radians(ang))
                distancias.append(dist)

            # Dibuixar una línia que connecta tots els punts del rastre
            self.axRadar.plot(
                angles,
                distancias,
                lw=2,
                color='green',
                alpha=0.7
            )

        # feix actual: línia radial + punt
        theta = math.radians(self.angulo_radar)
        r = self.distancia_radar

        # línia des del centre fins al punt actual
        self.axRadar.plot([theta, theta], [0, r], lw=2, color='green', alpha=0.95)

        # punt actual
        self.axRadar.plot([theta], [r], marker='o', markersize=6, color='green', alpha=0.95)

    # ---------- Refresco general ----------
    def actualizar_vista(self):
        # Gráficas T/H/Media
        self.lineT.set_data(self.tiempos, self.temperaturas)
        self.lineH.set_data(self.tiempos, self.humedades)
        self.lineM.set_data(range(len(self.medias)), self.medias)

        for ax in (self.axT, self.axH, self.axM):
            ax.relim()
            ax.autoscale_view()

        self.canvas.draw_idle()

        # Radar
        self.dibujar_radar()
        self.radar_canvas.draw_idle()

        self.root.after(REFRESH_MS, self.actualizar_vista)

    # ---------- Cierre ----------
    def on_close(self):
        self.rx_activa.clear()
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.root.destroy()


# ---------- Entrada simple ----------
def simple_input(root, prompt: str) -> str:
    top = tk.Toplevel(root)
    top.title("Entrada")
    ttk.Label(top, text=prompt).pack(padx=10, pady=8)
    var = tk.StringVar()
    entry = ttk.Entry(top, textvariable=var)
    entry.pack(padx=10, pady=5)
    entry.focus()
    val = []

    def aceptar():
        val.append(var.get())
        top.destroy()

    ttk.Button(top, text="Aceptar", command=aceptar).pack(pady=8)
    top.grab_set()
    root.wait_window(top)
    return val[0] if val else ""


# ---------- main ----------
def main():
    root = tk.Tk()
    EstacionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
