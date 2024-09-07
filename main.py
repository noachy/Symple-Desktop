import flet as ft
import qrcode
import base64

from io import BytesIO


def main(page: ft.Page):
    qr_img = qrcode.make('This is a Code!', border=2)
    buffered = BytesIO()
    qr_img.save(buffered, format='JPEG')
    qr_str_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(ft.Container(ft.Image(src_base64=qr_str_b64)))


ft.app(main)
