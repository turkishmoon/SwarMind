import tkinter as tk
from PIL import Image, ImageTk

root = tk.Tk()

# JPEG desteklenmediği için PIL üzerinden dönüştür
icon_image = Image.open("/home/arda/Masaüstü/SP-494/SwarMind.jpeg")
icon_photo = ImageTk.PhotoImage(icon_image)
root.iconphoto(False, icon_photo)

root.mainloop()
