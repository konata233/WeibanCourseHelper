import tkinter
from io import BytesIO

from PIL import ImageTk, Image


def display_img(image_bytes: bytes):
    im = Image.open(BytesIO(image_bytes))
    wnd = tkinter.Tk()
    width = im.width
    height = im.height
    wnd.geometry(f"{width}x{height}")
    img = ImageTk.PhotoImage(im)
    label = tkinter.Label(wnd, image=img)
    label.place(x=0, y=0)
    label.config(width=width, height=height)
    label.pack()
    wnd.mainloop()
