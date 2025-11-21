import sys
import matplotlib.pyplot as plt
import matplotlib
import re
import serial

matplotlib.use('TkAgg')

regex = re.compile(r"Position: \(X: ([\d\.-]+) m, Y: ([\d\.-]+) m, Z: ([\d\.-]+) m\)")

R_EARTH = 6371000

x_vals = []
y_vals = []

plt.ion()
fig, ax = plt.subplots()

orbit_plot, = ax.plot([], [], 'bo-', markersize=2)
last_point_plot = ax.scatter([], [], color='red', s=50)

earth_circle = plt.Circle((0,0), R_EARTH, fill=False, color='orange')
ax.add_artist(earth_circle)

ax.set_xlim(-7e6, 7e6)
ax.set_ylim(-7e6, 7e6)
ax.set_aspect("equal")

window_closed = False

def on_close(event):
    global window_closed
    window_closed = True
    print("Window closed")

fig.canvas.mpl_connect('close_event', on_close)

ser = serial.Serial('COM12', 9600, timeout=1)

def update_plot():
    if window_closed:
        return

    if ser.in_waiting > 0:
        line = ser.readline().decode().strip()
        match = regex.search(line)

        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            z = float(match.group(3))

            print("X:", x, "Y:", y, "Z:", z)

            x_vals.append(x)
            y_vals.append(y)

            orbit_plot.set_data(x_vals, y_vals)
            last_point_plot.set_offsets([[x, y]])

            plt.draw()
            fig.canvas.flush_events()

    fig.canvas.start_event_loop(0.01)

# Loop sin bloquear Tkinter
while not window_closed:
    update_plot()

plt.ioff()
plt.show()
