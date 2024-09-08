import flet as ft
import qrcode
import base64
import socket
import threading
import asyncio

from io import BytesIO


class CommHandler:
    buffer_size = 1024

    def __init__(self, page, container):
        self.page: ft.Page = page
        self.container: ft.Container = container
        self.ip_address: str = None
        self.port: int = None
        self.is_connected = False

    def gen_addinf_qr_b64str(self) -> str:
        if not self.is_connected:
            return
        data = f'{self.ip_address}:{self.port}'
        qr_img = qrcode.make(data, border=2)
        buffered = BytesIO()
        qr_img.save(buffered, format='JPEG')
        qr_str_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return qr_str_b64

    def update_container(self) -> None:
        self.container.content = ft.Image(
            src_base64=self.gen_addinf_qr_b64str())
        self.page.update()

    def connect(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        self.port = s.getsockname()[1]
        self.ip_address = socket.gethostbyname_ex(socket.gethostname())[2][1]
        self.is_connected = True

        self.update_container()

        while True:
            s.listen(1)
            conn, _ = s.accept()
            with conn:
                while True:
                    data = conn.recv(1)

                    if not data or data.decode() == 'Q':
                        break

                    if data.decode == 'S':
                        conn.sendall(b'AckCom')
                        data = conn.recv(self.buffer_size)

                        f_name, num_bytes = data.decode().split(':')

                        if '.' in f_name and num_bytes.isdigit():
                            num_bytes = int(num_bytes)

                            with open(f'./test-receive/{f_name}', 'wb') as f:
                                print(f'Receiving {f_name}')
                                conn.sendall(b'AckFle')
                                received_bytes = 0
                                bytes_from_last_got = 0

                                while received_bytes < num_bytes:
                                    data = conn.recv(self.buffer_size)
                                    f.write(data)
                                    received_bytes += len(data)
                                    bytes_from_last_got += len(data)

                                    if bytes_from_last_got > 333333:
                                        conn.sendall(
                                            (f'GOT {received_bytes / num_bytes} ').encode())
                                        bytes_from_last_got = 0

                            conn.sendall(b'Fin')
                        else:
                            conn.sendall(b'Inv : not digit')
                    else:
                        conn.sendall(b'Inv : data is not S or Q')


def main(page):
    container = ft.Container(ft.ProgressRing())

    comm_handler = CommHandler(page, container)
    t_comm = threading.Thread(target=comm_handler.connect)
    t_comm.start()

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(container)


ft.app(main)
