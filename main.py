import flet as ft
import qrcode
import base64
import socket
import threading
import psutil
import netifaces

from ping3 import ping
from io import BytesIO


# TODO: Add file receive screen -> Switch to screen after connection established -> Return after connection lost
# TODO: Add titles and instructions
# TODO: Add styling
# TODO: Add option for choosing default download location -> Implement Flet file picker!
# TODO: Test code and implement error handling where needed
# TODO: Make QR round instead of pointy

# TODO: ...more neat features :)

class CommHandler:
    buffer_size = 1024

    def __init__(self, page, container):
        self.page: ft.Page = page
        self.container: ft.Container = container
        self.ip_address: str = None
        self.port: int = None
        self.is_ready = False

    def gen_addinf_qr_b64str(self) -> str:
        if not self.is_ready:
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

        available_interfaces = [
            x for x in psutil.net_if_stats() if psutil.net_if_stats()[x].isup]
        available_addresses = [psutil.net_if_addrs(
        )[x][y].address for x in available_interfaces for y in range(len(psutil.net_if_addrs()[x])) if psutil.net_if_addrs()[x][y].family == socket.AF_INET]

        default_gateway = netifaces.gateways()['default'][netifaces.AF_INET][0]

        for item in available_addresses:
            try:
                ping(dest_addr=default_gateway, src_addr=item)
                self.ip_address = item
            except Exception as error:
                pass
            finally:
                if self.ip_address == '':
                    print('No interface able to connect to local network.')
                    return

        self.is_ready = True

        self.update_container()

        while True:
            s.listen(1)
            conn, _ = s.accept()
            print('Accepted connection')
            with conn:
                while True:
                    data = conn.recv(1)
                    print(f'Received {data.decode()}')

                    if not data or data.decode() == 'Q':
                        break

                    if data.decode() == 'S':
                        conn.sendall(b'AckCom')
                        print('Sent AckCom')
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
                            print('Sent Fin')
                        else:
                            conn.sendall(b'Inv : NaN')
                            print('Sent Inv: NaN')
                    else:
                        conn.sendall(b'Inv : Data not S or Q')


def main(page):
    container = ft.Container(ft.ProgressRing())

    comm_handler = CommHandler(page, container)
    t_comm = threading.Thread(target=comm_handler.connect)
    t_comm.start()

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.add(container)


ft.app(main)
