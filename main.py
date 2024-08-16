import math
import qrcode
import socket
import tqdm


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
                        data = conn.recv(1024)

                        f_name, num_bytes, num_updates = data.decode().split(':')

                        if '.' in f_name and num_bytes.isdigit():
                            with open(f'./test-receive/{f_name}', 'wb') as f:
                                print(f'Receiving {f_name}')
                                conn.sendall(b'AckFle')

                                # for loop is causing problems. was => while recived_bytes < num_bytes
                                # Error Message : UnicodeDecodeError: 'utf-8' codec can't decode byte 0xae in position 0: invalid start byte
                                # from pictures i transfered we can infer that the program misses the last data chunk. 
                                # and moves on with the rest of the file in the buffer which causes an error because the program tries to read it as a utf8 char
                                for i in tqdm.tqdm(range(math.ceil(int(num_bytes) / 1024))):
                                    data = conn.recv(1024)
                                    f.write(data)
                                    if math.floor(i % (math.ceil(int(num_bytes) / 1024) / int(num_updates))) == 0:
                                        conn.sendall(
                                            (f'GOT {i * 1024} ').encode())
                                print('Done!')
                            conn.sendall(b'Fin')
                        else:
                            conn.sendall(b'Inv : not digit')
                    else:
                        conn.sendall(b'Inv : data is not S or Q')


if __name__ == '__main__':
    app()
