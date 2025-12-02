# -- coding: utf-8 --
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
import matplotlib.pyplot as plt


import datetime

# ===== Parámetros de serie =====
PUERTO_DESEADO = "COM4"     # <- Ajusta si hace falta
BAUDRATE = 9600
TIMEOUT_S = 1.0
GRUPO_ESPERADO = "G6:"


# ===== Registro de eventos =====
RUTA_LOG = "eventos.log"


def registrar_evento(tipo: str, descripcion: str):
    """
    Registra un evento en el archivo eventos.log
    tipo = COMANDO | ALARMA | OBSERVACION | ERROR
    """
    try:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"{fecha} | {tipo.upper():12} | {descripcion}\n"

        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(linea)

        print("[REGISTRO] ", linea.strip())

    except Exception as e:
        print("[ERROR] No se pudo escribir en eventos.log:", e)


# ===== Parámetros de visualización =====
N_MUESTRAS = 120
REFRESH_MS = 100
VENTANA_MEDIA = 10

# ===== Radar =====
RADAR_R_MAX = 50.0          # cm, eje radial 0..50
TRAIL_GRADOS = 20           # (no se usa ahora, pero lo dejamos)
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


# ===== Checksum =====
def calcular_checksum(msg: str) -> int:
    s = sum(ord(c) for c in msg)
    return s & 0xFF


def validar_linea(linea: str) -> str | None:
    if "*" not in linea:
        return None
    cuerpo, cs_str = linea.rsplit("*", 1)
    try:
        cs_recv = int(cs_str)
    except ValueError:
        return None
    cs_calc = calcular_checksum(cuerpo)
    if cs_recv == cs_calc:
        return cuerpo
    else:
        # Registrar mensaje corrupto
        registrar_evento("ERROR", f"Mensaje corrupto recibido: {linea}")
        return None


def enviar_con_checksum(ser, msg: str):
    cs = sum(ord(c) for c in msg) & 0xFF
    linea = f"{msg}*{cs}\n"
    ser.write(linea.encode("utf-8"))


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

        # ---------- Órbita ----------
        self.orbit_times = deque(maxlen=2000)
        self.orbit_x = deque(maxlen=2000)
        self.orbit_y = deque(maxlen=2000)
        self.orbit_z = deque(maxlen=2000)

        self.orbit_win = None
        self.orbit_fig = None
        self.orbit_ax = None
        self.orbit_canvas = None
        self.orbit_plot = None
        self.orbit_last = None


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
        ttk.Label(header, text="Estación de Tierra", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        body = ttk.Frame(self.root, padding=10)
        body.grid(row=1, column=0, columnspan=2, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        panel_plots = ttk.Frame(body)
        panel_plots.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_plots.grid_rowconfigure(0, weight=1)
        panel_plots.grid_columnconfigure(0, weight=3)   # gráficas tiempo
        panel_plots.grid_columnconfigure(1, weight=2)   # radar

        sidebar = ttk.Frame(body, width=260)
        sidebar.grid(row=0, column=1, sticky="ns")

        # --- Botones de control ---
        self.btn_iniciar = ttk.Button(sidebar, text="Iniciar conexión", command=self.on_iniciar)
        self.btn_parar = ttk.Button(
            sidebar, text="Parar / Reanudar T/H ", command=self.on_parar, state="disabled"
        )
        self.btn_periodo = ttk.Button(
            sidebar, text="Periodo T/H ", command=self.on_periodo, state="disabled"
        )
        self.btn_orient = ttk.Button(
            sidebar, text="Orientar servo ", command=self.on_orient, state="disabled"
        )
        self.btn_auto = ttk.Button(
            sidebar, text="Barrido automático", command=self.on_auto, state="disabled"
        )
        # NUEVOS BOTONES RADAR
        self.btn_radar_toggle = ttk.Button(
            sidebar, text="Parar / Reanudar RADAR ", command=self.on_radar_toggle, state="disabled"
        )
        self.btn_radar_periodo = ttk.Button(
            sidebar, text="Periodo RADAR ", command=self.on_periodo_radar, state="disabled"
        )

        self.btn_limite = ttk.Button(
            sidebar, text="Límite alarma medias ", command=self.on_limite
        )
        self.btn_eventos = ttk.Button(
            sidebar, text="Ver registro de eventos", command=self.abrir_eventos
        )
        self.btn_obs = ttk.Button(
            sidebar, text="Añadir observación", command=self.on_obs
        )
        self.btn_orbita = ttk.Button(
            sidebar, text="Ver órbita", command=self.abrir_orbita, state="disabled"
        )


        # Colocación en la barra lateral
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.btn_parar.grid(row=1, column=0, sticky="ew", pady=4)

        self.btn_periodo.grid(row=2, column=0, sticky="ew", pady=4)
        self.btn_orient.grid(row=3, column=0, sticky="ew", pady=4)
        self.btn_auto.grid(row=4, column=0, sticky="ew", pady=4)

        self.btn_radar_toggle.grid(row=5, column=0, sticky="ew", pady=4)
        self.btn_radar_periodo.grid(row=6, column=0, sticky="ew", pady=4)

        self.btn_orbita.grid(row=7, column=0, sticky="ew", pady=4)

        self.btn_limite.grid(row=8, column=0, sticky="ew", pady=8)
        ttk.Separator(sidebar, orient="horizontal").grid(row=9, column=0, sticky="ew", pady=8)

        ttk.Label(sidebar, text="Modo de cálculo de medias:").grid(
            row=10, column=0, sticky="w", padx=5
        )
        self.modo_var = tk.StringVar(value="tierra")
        ttk.Radiobutton(
            sidebar, text="En Tierra (Python)", variable=self.modo_var,
            value="tierra", command=self.on_modo_calculo
        ).grid(row=11, column=0, sticky="w", padx=10)
        ttk.Radiobutton(
            sidebar, text="En Satélite (Arduino)", variable=self.modo_var,
            value="satelite", command=self.on_modo_calculo
        ).grid(row=12, column=0, sticky="w", padx=10)

        ttk.Separator(sidebar, orient="horizontal").grid(row=13, column=0, sticky="ew", pady=8)

        self.lbl_estado = ttk.Label(
            sidebar,
            text="Puerto: —\nMuestras: 0\nÚltima T/H: —/—",
            justify="left"
        )
        self.lbl_estado.grid(row=14, column=0, sticky="ew", pady=(0, 6))

        self.btn_eventos.grid(row=15, column=0, sticky="ew", pady=4)
        self.btn_obs.grid(row=16, column=0, sticky="ew", pady=4)

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

    # ----- Configuración ejes del radar -----
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

        # Activar botones
        self.btn_iniciar.config(state="disabled")
        self.btn_parar.config(state="normal")
        self.btn_periodo.config(state="normal")
        self.btn_orient.config(state="normal")
        self.btn_auto.config(state="normal")
        self.btn_radar_toggle.config(state="normal")
        self.btn_radar_periodo.config(state="normal")
        self.btn_orbita.config(state="normal")


    def on_parar(self):
        if not self.conectado:
            return
        try:
            enviar_con_checksum(self.ser, "3:")  # Parar/Reanudar datos T y H
            registrar_evento("COMANDO", "Parar/Reanudar envío de datos T/H")
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
            enviar_con_checksum(self.ser, f"1:{s}")
            registrar_evento("COMANDO", f"Cambiar periodo T/H a {s} segundos")
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
            enviar_con_checksum(self.ser, f"2:{ang}")
            registrar_evento("COMANDO", f"Orientar servo a {ang} grados")
        except Exception:
            messagebox.showerror("Error", "Valor inválido")

    def on_auto(self):
        if not self.conectado:
            return
        try:
            enviar_con_checksum(self.ser, "7:")
            registrar_evento("COMANDO", "Activar barrido automático del radar")
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar '7:': {e}")

    def on_radar_toggle(self):
        """Parar/Reanudar envío de datos de distancia (RADAR) — usa comando 8:"""
        if not self.conectado:
            return
        try:
            enviar_con_checksum(self.ser, "8:")
            registrar_evento("COMANDO", "Parar/Reanudar envío de datos de distancia (RADAR)")
        except Exception as e:
            messagebox.showerror("Envío", f"No se pudo enviar '8:': {e}")

    def on_periodo_radar(self):
        """
        Cambiar periodo de medida de distancia (RADAR).
        IMPORTANTE: en el Arduino satélite debe existir el comando 6:valor
        que ajuste periodoDist.
        """
        if not self.conectado:
            return
        valor = simple_input(self.root, "Nuevo periodo para el RADAR (ms):")
        if not valor:
            return
        try:
            ms = int(valor)
            enviar_con_checksum(self.ser, f"6:{ms}")
            registrar_evento("COMANDO", f"Cambiar periodo RADAR a {ms} ms")
        except Exception:
            messagebox.showerror("Error", "Valor inválido")

    def on_limite(self):
        val = simple_input(self.root, "Nuevo límite de alarma (°C):")
        if val:
            try:
                self.limite_alarma = float(val)
                if self.conectado:
                    enviar_con_checksum(self.ser, f"5:{self.limite_alarma}")
                    registrar_evento(
                        "COMANDO",
                        f"Nuevo límite de alarma: {self.limite_alarma} °C"
                    )
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
                enviar_con_checksum(self.ser, "4:")  # activar cálculo de medias en satélite
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
                    linea_raw = self.ser.readline().decode("utf-8", errors="replace").strip()
                    if not linea_raw:
                        continue

                    # validar checksum
                    linea = validar_linea(linea_raw)
                    if linea is None:
                        continue  # ignorar mensaje corrupto

                    # ---- FILTRO POR GRUPO ----
                    if not linea.startswith(GRUPO_ESPERADO):
                        continue  # no es mi grupo, lo ignoro

                    # quitar prefijo G6:
                    linea = linea[len(GRUPO_ESPERADO):]

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

                    # 4:media  -> media calculada en satélit

                    # 5: -> alarma tres medias en satélite
                    elif codigo == "5":
                        self.root.bell()
                        registrar_evento("ALARMA", "Tres medias consecutivas superan el límite")
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
                        registrar_evento(
                            "ALARMA",
                            "Fallo en sensor de temperatura/humedad (DHT11)"
                        )
                        print("[ALERTA] Error de sensor T/H (3:)")

                    # 6: -> fallo sensor distancia
                    elif codigo == "6":
                        registrar_evento("ALARMA", "Fallo en sensor de distancia (HC-SR04)")
                        self.root.bell()
                        messagebox.showwarning(
                            "⚠ Alarma",
                            "Fallo en el sensor de distancia (HC-SR04)"
                        )

                                        # 4:media  -> media calculada en satélite
                    # 4:time:x:y:z -> órbita (nuevo)
                    elif codigo == "4":
                        # ÓRBITA: esperamos 4:time:x:y:z (5 partes mínimo)
                        if len(partes) >= 5:
                            try:
                                t_orb = float(partes[1])
                                x = float(partes[2])
                                y = float(partes[3])
                                z = float(partes[4])
                            except ValueError:
                                continue

                            self.orbit_times.append(t_orb)
                            self.orbit_x.append(x)
                            self.orbit_y.append(y)
                            self.orbit_z.append(z)

                        # MEDIA: formato antiguo 4:media
                        elif len(partes) >= 2:
                            try:
                                media = float(partes[1])
                            except ValueError:
                                continue
                            self.medias.append(media)
                            self.comprobar_alarma(media)


                time.sleep(0.01)
            except Exception as e:
                print("[ERROR RX]", e)
                time.sleep(0.1)

    def on_obs(self):
        texto = simple_input(self.root, "Escribe una observación:")
        if texto:
            registrar_evento("OBSERVACION", texto)
            messagebox.showinfo("OK", "Observación registrada.")



    def abrir_orbita(self):
        """Abre ventana con gráfica de órbita y empieza a actualizarla."""
        if self.orbit_win and tk.Toplevel.winfo_exists(self.orbit_win):
            # si ya existe, la traemos al frente
            self.orbit_win.lift()
            return

        win = tk.Toplevel(self.root)
        win.title("Órbita del satélite (vista polar norte)")
        win.geometry("620x620")
        self.orbit_win = win

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        self.orbit_fig = Figure(figsize=(6, 6), dpi=100)
        self.orbit_ax = self.orbit_fig.add_subplot(111)
        self.orbit_ax.set_aspect("equal", "box")
        self.orbit_ax.set_xlabel("X (m)")
        self.orbit_ax.set_ylabel("Y (m)")
        self.orbit_ax.set_title("Órbita ecuatorial (top view)")
        self.orbit_ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.6)

        # Tierra como círculo
        R_EARTH = 6371000
        earth_circle = plt.Circle((0, 0), R_EARTH, color="orange", fill=False, lw=2)
        self.orbit_ax.add_artist(earth_circle)

        # Línea órbita + punto actual
        self.orbit_plot, = self.orbit_ax.plot([], [], "b-", lw=1.5, label="Trayectoria")
        self.orbit_last = self.orbit_ax.scatter([], [], color="red", s=40, label="Último punto")
        self.orbit_ax.legend(loc="upper right")

        self.orbit_canvas = FigureCanvasTkAgg(self.orbit_fig, master=win)
        self.orbit_canvas.draw()
        self.orbit_canvas.get_tk_widget().pack(fill="both", expand=True)

        # cerrar ventana
        def _on_close():
            self.orbit_win = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)


    # ---------- Ventana registro de eventos ----------
    def abrir_eventos(self):
        """Ventana para mostrar el registro de eventos con filtro por tipo y por día."""

        win = tk.Toplevel(self.root)
        win.title("Registro de eventos")
        win.geometry("760x560")

        # ================== FILTRO POR TIPO ==================
        filtro_tipo = tk.StringVar(value="TODOS")
        opciones_tipo = ["TODOS", "COMANDO", "ALARMA", "OBSERVACION", "ERROR"]

        ttk.Label(win, text="Filtrar por tipo:").pack(pady=(10, 0))
        ttk.OptionMenu(win, filtro_tipo, "TODOS", *opciones_tipo).pack()

        # ================== FILTRO POR FECHA ==================
        ttk.Label(win, text="\nFiltrar por día (YYYY-MM-DD):").pack()

        filtro_fecha = tk.StringVar()
        entry_fecha = ttk.Entry(win, textvariable=filtro_fecha, width=20)
        entry_fecha.pack()

        # ================== CUADRO DE TEXTO ==================
        text = tk.Text(win, wrap="none", font=("Consolas", 10))
        text.pack(expand=True, fill="both", padx=10, pady=10)

        # ================== FUNCIÓN PARA CARGAR LOG ==================
        def cargar():
            text.delete("1.0", tk.END)

            tipo_sel = filtro_tipo.get().strip()
            fecha_sel = filtro_fecha.get().strip()

            try:
                with open(RUTA_LOG, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea_ok = True

                        # ---- FILTRO POR TIPO ----
                        if tipo_sel != "TODOS" and f"| {tipo_sel}" not in linea:
                            linea_ok = False

                        # ---- FILTRO POR FECHA ----
                        # Las líneas empiezan con "YYYY-MM-DD HH:MM:SS"
                        if fecha_sel and not linea.startswith(fecha_sel):
                            linea_ok = False

                        if linea_ok:
                            text.insert(tk.END, linea)

            except FileNotFoundError:
                text.insert(tk.END, "No hay registros todavía.")

        # Botón actualizar
        ttk.Button(win, text="Aplicar filtros", command=cargar).pack(pady=5)

        cargar()


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
    def dibujar_radar(self):
        # reconfigura ejes (mantiene semicirculo 0..180)
        self.configurar_radar_axes()

        # rastro
        if len(self.trail) >= 2:
            angles = []
            distancias = []
            for _, ang, dist in self.trail:
                angles.append(math.radians(ang))
                distancias.append(dist)

            self.axRadar.plot(
                angles,
                distancias,
                lw=2,
                color='green',
                alpha=0.7
            )

        # haz actual
        theta = math.radians(self.angulo_radar)
        r = self.distancia_radar

        self.axRadar.plot([theta, theta], [0, r], lw=2, color='green', alpha=0.95)
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

        #orbita
                # Órbita (si la ventana está abierta)
        if self.orbit_win is not None and self.orbit_ax is not None:
            xs = list(self.orbit_x)
            ys = list(self.orbit_y)
            if len(xs) >= 2:
                self.orbit_plot.set_data(xs, ys)
                self.orbit_last.set_offsets([[xs[-1], ys[-1]]])

                # auto-escalado razonable
                lim = max(max(map(abs, xs)), max(map(abs, ys)), 7e6) * 1.05
                self.orbit_ax.set_xlim(-lim, lim)
                self.orbit_ax.set_ylim(-lim, lim)

            self.orbit_canvas.draw_idle()


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
