

import tkinter as tk
from tkinter import ttk

root = tk.Tk()
ttk.Scale(root, from_=0, to=42, orient=tk.VERTICAL).pack()
ttk.Scale(root, from_=0, to=200, orient=tk.HORIZONTAL).pack()
onoff = tk.IntVar()
onoff.set(0)
ttk.Checkbutton(root, text='on/off x:', variable=onoff).pack()
tv = tk.StringVar()
tv.set(1.2)
ttk.Entry(root, textvariable=tv).pack()

tk.mainloop()
