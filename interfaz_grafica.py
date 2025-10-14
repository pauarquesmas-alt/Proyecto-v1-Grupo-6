import time
import re
from collections import deque

import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import threading
import tkinter as tk
from tkinter import messagebox


PUERTO_DESEADO = "COM4"
BAUDRATE = 9600
TIMEOUT_S = 1.0

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
        time.sleep(2.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except serial.SerialException as e:
        raise RuntimeError(f"No se pudo abrir {device}: {e}")


ser = None           
mySerial = None      
root = None         
threadRecepcion = None 

def main():
    global ser, mySerial, root, threadRecepcion

    device = elegir_puerto(PUERTO_DESEADO)
    ser = abrir_serial(device)
    mySerial = ser  
    print(f"Conectado a {device}. Esperando datos del Arduino...")

   
    plt.ion()
    fig, ax = plt.subplots()
    ax.set_title("Temperatura y Humedad en tiempo real")
    ax.set_xlabel("Muestras")
    ax.set_ylabel("Valores")

    N = 50
    temperaturas = deque(maxlen=N)
    humedades = deque(maxlen=N)
    tiempos = deque(maxlen=N)

    patron = re.compile(r"T:(-?\d+(?:\.\d+)?).*H:(-?\d+(?:\.\d+)?)")
    contador = 0

    proximo_ping = time.monotonic() + 1.0


    def recepcion():
        nonlocal contador, proximo_ping
        try:
            while True:
                if mySerial.in_waiting > 0:
                    try:
                        linea = mySerial.readline().decode('utf-8').rstrip()
                    except Exception as e:
                        print(f"[Decodificación] {e}")
                        linea = ""
                    if linea:
                        print(linea)  
                    
                        m = patron.search(linea)
                        if m:
                            t = float(m.group(1))
                            h = float(m.group(2))
                            temperaturas.append(t)
                            humedades.append(h)
                            tiempos.append(contador)
                            contador += 1

                            ax.clear()
                            ax.plot(tiempos, temperaturas, label="Temperatura (°C)")
                            ax.plot(tiempos, humedades, label="Humedad (%)")
                            ax.set_ylim(0, 100)
                            ax.set_xlabel("Muestras")
                            ax.set_ylabel("Valores")
                            ax.set_title("Temperatura y Humedad en tiempo real")
                            ax.legend(loc="upper right")
                            plt.pause(0.01)

                # Tu ping periódico
                ahora = time.monotonic()
                if ahora >= proximo_ping:
                    try:
                        mySerial.write(b"P")
                    except serial.SerialException as e:
                        print(f"[Escritura] {e}")
                        break
                    proximo_ping = ahora + 1.0

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nPrograma terminado por el usuario (hilo).")
        except serial.SerialException as e:
            print(f"Error de puerto serie (hilo): {e}")
        except Exception as e:
            print(f"Ocurrió un error inesperado (hilo): {e}")

    root = tk.Tk()
    root.title("Iniciar / Parar / Reanudar (Paso 11)")

    def on_iniciar():
    
        global threadRecepcion
        if threadRecepcion and threadRecepcion.is_alive():
            return
        threadRecepcion = threading.Thread(target=recepcion, daemon=True)
        threadRecepcion.start()

    def on_parar():
        try:
            mensaje = "Parar"
            mySerial.write(mensaje.encode('utf-8'))
            print("Enviado:", mensaje)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar 'Parar': {e}")

    def on_reanudar():
        try:
            mensaje = "Reanudar"
            mySerial.write(mensaje.encode('utf-8'))
            print("Enviado:", mensaje)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar 'Reanudar': {e}")

    frame = tk.Frame(root)
    frame.pack(padx=8, pady=8)

    tk.Button(frame, text="Iniciar",  width=12, command=on_iniciar).grid(row=0, column=0, padx=4)
    tk.Button(frame, text="Parar",    width=12, command=on_parar).grid(row=0, column=1, padx=4)
    tk.Button(frame, text="Reanudar", width=12, command=on_reanudar).grid(row=0, column=2, padx=4)

    lbl = tk.Label(root, text="Pulsa Iniciar para empezar a recibir.\nParar/Reanudar envían esa palabra al satélite.")
    lbl.pack(pady=6)

    root.mainloop()


if __name__ == "__main__":
    main()
