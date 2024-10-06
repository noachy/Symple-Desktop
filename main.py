import flet as ft
import qrcode
import base64
import socket
import threading
import psutil
import netifaces
import ssl
import datetime

from enum import Enum
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ping3 import ping
from io import BytesIO


# TODO: Add file receive screen -> Switch to screen after connection established -> Return after connection lost
# TODO: Add titles and instructions
# TODO: Add styling
# TODO: Add option for choosing default download location -> Implement Flet file picker!
# TODO: Test code and implement error handling where needed

# TODO: ...more neat features :)

class CommState(Enum):
    EMPTY = 1
    WAITING = 2
    CONNECTED = 3


class CommHandler:
    buffer_size = 1024

    def __init__(self, page, column):
        self.page: ft.Page = page
        self.column: ft.Column = column
        self.ip_address: str = None
        self.port: int = None
        self._comm_state = CommState.EMPTY

    def update_content(self) -> None:
        match self.comm_state:
            case CommState.EMPTY:
                self.column.controls = [
                    ft.Container(
                        content=ft.ProgressRing())]
                self.page.update()
            case CommState.WAITING:
                self.column.controls = [
                    ft.Container(
                        border_radius=20,
                        content=ft.Image(
                            src_base64=self.gen_addinf_qr_b64str())),
                    ft.Text(
                        value='Scan the code using the app',
                        size=24)]
                self.page.update()
            case CommState.CONNECTED:
                self.column.controls = [
                    ft.Text(
                        value='Placeholder for file receiving screen',
                        size=24)]
                self.page.update()

    @property
    def comm_state(self):
        return self._comm_state

    @comm_state.setter
    def comm_state(self, comm_state: CommState) -> None:
        self._comm_state = comm_state
        self.update_content()

    def gen_addinf_qr_b64str(self) -> str:
        data = f'{self.ip_address}:{self.port}'.encode()
        qr_img = qrcode.make(base64.b64encode(data).decode('utf-8'), border=2)
        buffered = BytesIO()
        qr_img.save(buffered)
        qr_str_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return qr_str_b64

    def create_cert_files(self) -> None:
        key = rsa.generate_private_key(

            public_exponent=65537,

            key_size=2048,
        )
        subject = issuer = x509.Name([

            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),

            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),

            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),

            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Company"),

            x509.NameAttribute(NameOID.COMMON_NAME, "mysite.com"),

        ])

        cert = x509.CertificateBuilder().subject_name(

            subject

        ).issuer_name(

            issuer

        ).public_key(

            key.public_key()

        ).serial_number(

            x509.random_serial_number()

        ).not_valid_before(

            datetime.datetime.now(datetime.timezone.utc)

        ).not_valid_after(

            datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(days=10)

        ).add_extension(

            x509.SubjectAlternativeName([x509.DNSName("localhost")]),

            critical=False,


        ).sign(key, hashes.SHA256())

        with open("./pem_files/certchain.pem", "wb") as f:

            f.write(cert.public_bytes(serialization.Encoding.PEM))

            f.write(key.private_bytes(

                encoding=serialization.Encoding.PEM,

                format=serialization.PrivateFormat.TraditionalOpenSSL,

                encryption_algorithm=serialization.NoEncryption(),

            ))

    def connect(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.bind(('', 0))
        self.port = sock.getsockname()[1]

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
                try:
                    ping(dest_addr='8.8.8.8', src_addr=item)
                    self.ip_address = item
                except:
                    pass
            finally:
                if self.ip_address == '':
                    print('No interface able to connect to local network.')
                    return

        self.create_cert_files()

        self.comm_state = CommState.WAITING

        while True:
            sock.listen(1)
            context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(
                certfile='./pem_files/certchain.pem')
            with context.wrap_socket(sock, server_side=True) as ssock:
                conn, _ = ssock.accept()
                self.comm_state = CommState.CONNECTED
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


class SettingsView(ft.View):
    def __init__(self):
        super().__init__()

        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.padding = 200
        self.appbar = ft.AppBar()
        self.controls = [
            ft.ExpansionPanelList(

                controls=[
                    ft.ExpansionPanel(
                        bgcolor='#2c333e',
                        can_tap_header=True,
                        header=ft.Text('Expansion Panel 1')) for x in range(5)
                ])
        ]


def main(page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def open_settings(e):
        page.views.append(SettingsView())
        page.update()

    def pop_view(view):
        page.views.pop()
        page.update()

    page.on_view_pop = pop_view

    page.appbar = ft.AppBar(
        leading=ft.IconButton(tooltip='Settings', icon=ft.icons.SETTINGS, on_click=open_settings))

    main_column = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[ft.Container(ft.ProgressRing(), border_radius=20)])

    comm_handler = CommHandler(page, main_column)
    t_comm = threading.Thread(target=comm_handler.connect)
    t_comm.start()

    page.add(main_column)


ft.app(main)
