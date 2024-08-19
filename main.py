import math
import qrcode
import socket

from tqdm import tqdm

BUFFER_SIZE = 1024


def print_qr_address(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr.print_ascii()


def app():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TODO : wrap socket with TLS
        s.bind(('', 0))
        port = s.getsockname()[1]
        local_address = socket.gethostbyname(socket.gethostname())
        print('Scan the following QR code on the mobile app in order to establish a connection: ')
        print_qr_address(f'{local_address}:{port}')
        print(f'Listening at {local_address}:{port}...')
        while True:
            s.listen(1)
            conn, addr = s.accept()
            print("\033[2J\033[H", end="", flush=True)
            print(f'Connected to {addr[0]}, waiting for files...')
            with conn:
                while True:
                    data = conn.recv(1)

                    if not data or data.decode() == 'Q':
                        print('Connection terminated.')
                        break
                    if data.decode() == 'S':
                        conn.sendall(b'AckCom')
                        data = conn.recv(BUFFER_SIZE)

                        f_name, num_bytes, num_updates = data.decode().split(':')

                        num_bytes = int(num_bytes)

                        if '.' in f_name and num_bytes.isdigit():
                            with open(f'./test-receive/{f_name}', 'wb') as f:
                                print(f'Receiving {f_name}')
                                conn.sendall(b'AckFle')
                                received_bytes = 0
                                bytes_from_last_got = 0

                                with tqdm(total=num_bytes) as prog_bar:
                                    while received_bytes < num_bytes:
                                        data = conn.recv(BUFFER_SIZE)
                                        f.write(data)
                                        received_bytes += len(data)
                                        bytes_from_last_got += len(data)

                                        if bytes_from_last_got > 333333:
                                            conn.sendall(
                                                (f'GOT {received_bytes / num_bytes} ').encode())
                                            bytes_from_last_got = 0

                                        prog_bar.update(BUFFER_SIZE)
                                print('Done!')
                            conn.sendall(b'Fin')
                        else:
                            conn.sendall(b'Inv : not digit')
                    else:
                        conn.sendall(b'Inv : data is not S or Q')


if __name__ == '__main__':
    app()
