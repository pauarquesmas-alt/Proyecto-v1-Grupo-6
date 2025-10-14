import time
import re
import threading
from collections import deque

import serial
import serial.tools.list_ports

from tkinter import *
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

PUERTO_DESEADO = "COM4"
BAUDRATE = 9600
TIMEOUT_S = 1.0
COMM_TIMEOUT_S = 5.0  # 5 segons sense dades -> alarma comunicació


# --- SERIAL ---
def elegir_puerto(deseado: str | None = None) -> str:
    disponibles = [p.device for p in serial.tools.list_ports.comports()]
    print("Puertos disponibles:", disponibles)
    if deseado and deseado in disponibles:
        return deseado
    if not disponibles:
        raise RuntimeError("No hay puertos serie disponibles.")
    print(f"Aviso: {deseado} no encontrado. Usando {disponibles[0]}")
    return disponibles[0]


def abrir_serial(device: str) -> serial.Serial:
    try:
        ser = serial.Serial(device, BAUDRATE, timeout=TIMEOUT_S)
        time.sleep(2.0)  # reset Arduino
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except serial.SerialException as e:
        raise RuntimeError(f"No se pudo abrir {device}: {e}")


# --- APP ---
class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("Control Satèl·lit - V1")
        self.geometry("820x600")

        # estat
        self.ser = None
        self.device = None
        self.rx_thread = None
        self.rx_running = False
        self.paused = False
        self.lock = threading.Lock()

        # dades gràfic
        self.patron = re.compile(r"T:(-?\d+(?:\.\d+)?).*H:(-?\d+(?:\.\d+)?)")
        self.N = 100
        self.tiempos = deque(maxlen=self.N)
        self.temperaturas = deque(maxlen=self.N)
        self.humedades = deque(maxlen=self.N)
        self.contador = 0

        # alarmes
        self.alarm_sensor = False
        self.alarm_comm = False
        self.last_rx_time = time.monotonic()

        # ui
        self._build_ui()

        # obrir port
        try:
            self.device = elegir_puerto(PUERTO_DESEADO)
            self.ser = abrir_serial(self.device)
            self.lbl_estado.config(text=f"Conectado a {self.device}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.destroy()
            return

        # refrescos
        self._tick_plot()
        self._tick_alarms()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(side=TOP, fill=X)

        self.btn_iniciar = ttk.Button(frame, text="Iniciar", command=self.on_iniciar)
        self.btn_parar = ttk.Button(frame, text="Parar", command=self.on_parar, state=DISABLED)
        self.btn_reanudar = ttk.Button(frame, text="Reanudar", command=self.on_reanudar, state=DISABLED)
        self.lbl_estado = ttk.Label(frame, text="Estado: Sin conexión")

        self.btn_iniciar.pack(side=LEFT, padx=5)
        self.btn_parar.pack(side=LEFT, padx=5)
        self.btn_reanudar.pack(side=LEFT, padx=5)
        self.lbl_estado.pack(side=LEFT, padx=20)

        alarms = ttk.Frame(self, padding=(10, 0, 10, 5))
        alarms.pack(side=TOP, fill=X)

        self.badge_sensor = Label(alarms, text="Sensor: OK", bg="#2ecc71", fg="white", padx=10, pady=4)
        self.badge_comm   = Label(alarms, text="Comunicación: OK", bg="#2ecc71", fg="white", padx=10, pady=4)
        self.badge_sensor.pack(side=LEFT, padx=5)
        self.badge_comm.pack(side=LEFT, padx=5)

        fig = Figure(figsize=(7.4, 4.4), dpi=100)
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Temperatura / Humedad en tiempo real")
        self.ax.set_xlabel("Muestras")
        self.ax.set_ylabel("Valor")
        (self.line_t,) = self.ax.plot([], [], label="Temperatura (°C)")
        (self.line_h,) = self.ax.plot([], [], label="Humedad (%)")
        self.ax.set_ylim(0, 100)  # simple i suficient per a V1
        self.ax.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

    # --- botons ---
    def on_iniciar(self):
        if self.rx_running:
            return
        self.paused = False
        self.rx_running = True
        self.rx_thread = threading.Thread(target=self._recepcion, daemon=True)
        self.rx_thread.start()
        self.lbl_estado.config(text="Recibiendo datos...")
        self.btn_iniciar.config(state=DISABLED)
        self.btn_parar.config(state=NORMAL)
        self.btn_reanudar.config(state=NORMAL)
        self._set_alarm_comm(False)

    def on_parar(self):
        try:
            self.ser.write(b"Parar\n")
        except Exception as e:
            print(f"[Error envío] {e}")
        self.paused = True
        self.rx_running = False
        self.lbl_estado.config(text="Orden enviada: Parar")
        self.btn_iniciar.config(state=NORMAL)
        self.btn_parar.config(state=DISABLED)
        self.btn_reanudar.config(state=NORMAL)
        self._set_alarm_comm(False)  # no alarma mentre està pausat

    def on_reanudar(self):
        try:
            self.ser.write(b"Reanudar\n")
        except Exception as e:
            print(f"[Error envío] {e}")
        self.paused = False
        self.last_rx_time = time.monotonic()
        self._set_alarm_comm(False)
        if not self.rx_running:
            self.rx_running = True
            self.rx_thread = threading.Thread(target=self._recepcion, daemon=True)
            self.rx_thread.start()
        self.lbl_estado.config(text="Orden enviada: Reanudar")
        self.btn_iniciar.config(state=DISABLED)
        self.btn_parar.config(state=NORMAL)
        self.btn_reanudar.config(state=NORMAL)

    # --- recepció ---
    def _recepcion(self):
        proximo_ping = time.monotonic() + 1.0
        while self.rx_running:
            try:
                if self.ser.in_waiting:
                    linea = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if linea:
                        self.last_rx_time = time.monotonic()
                        print(linea)

                        if "Fallo" in linea:
                            self._set_alarm_sensor(True)
                            continue

                        m = self.patron.search(linea)
                        if m:
                            t = float(m.group(1))
                            h = float(m.group(2))
                            with self.lock:
                                self.tiempos.append(self.contador)
                                self.temperaturas.append(t)
                                self.humedades.append(h)
                                self.contador += 1
                            self._set_alarm_sensor(False)

                # ping opcional
                ahora = time.monotonic()
                if ahora >= proximo_ping:
                    try:
                        self.ser.write(b"P")
                    except Exception:
                        pass
                    proximo_ping = ahora + 1.0

                time.sleep(0.01)

            except Exception as e:
                print(f"[Recepción] {e}")
                time.sleep(0.2)

    # --- alarmes ---
    def _tick_alarms(self):
        elapsed = time.monotonic() - self.last_rx_time
        comm_fail = (elapsed > COMM_TIMEOUT_S) and (not self.paused) and self.rx_running
        self._set_alarm_comm(comm_fail)
        self.after(200, self._tick_alarms)

    def _set_alarm_sensor(self, active: bool):
        if self.alarm_sensor == active:
            return
        self.alarm_sensor = active
        if active:
            self.badge_sensor.config(text="Sensor: FALLO", bg="#e74c3c")
            self._beep()
        else:
            self.badge_sensor.config(text="Sensor: OK", bg="#2ecc71")

    def _set_alarm_comm(self, active: bool):
        if self.alarm_comm == active:
            return
        self.alarm_comm = active
        if active:
            self.badge_comm.config(text="Comunicación: FALLO", bg="#e74c3c")
            self._beep()
        else:
            self.badge_comm.config(text="Comunicación: OK", bg="#2ecc71")

    def _beep(self):
        try:
            import winsound
            winsound.Beep(880, 200)
        except Exception:
            try:
                self.bell()
            except Exception:
                pass

    # --- gràfic ---
    def _tick_plot(self):
        self._update_plot()
        self.after(100, self._tick_plot)

    def _update_plot(self):
        with self.lock:
            xs = list(self.tiempos)
            ys_t = list(self.temperaturas)
            ys_h = list(self.humedades)
        self.line_t.set_data(xs, ys_t)
        self.line_h.set_data(xs, ys_h)
        if xs:
            self.ax.set_xlim(max(0, xs[0]), max(50, xs[-1]))
        self.canvas.draw_idle()

    def _on_close(self):
        try:
            self.rx_running = False
            if self.rx_thread and self.rx_thread.is_alive():
                self.rx_thread.join(timeout=1.0)
            if self.ser:
                self.ser.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
