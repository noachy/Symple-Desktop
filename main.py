import math
import qrcode
import socket

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

def open_connection():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # TODO : wrap socket with TLS
        s.bind(('', 0))
        port = s.getsockname()[1]
        local_address = socket.gethostbyname(socket.gethostname())
        print_qr_address(f'{local_address}:{port}')
        print(f'Listening at {local_address}:{port}...')
        while True:
            s.listen(1)
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    data = conn.recv(1)

                    if not data or data.decode() == 'Q':
                        break
                    if data.decode() == 'S':
                        conn.sendall(b'AckCom')
                        data = conn.recv(1024)

                        print(f'Received {data.decode()}')

                        f_name, num_bytes = data.decode().split(':')
                        if '.' in f_name and num_bytes.isdigit():
                            with open(f'./test-receive/{f_name}', 'wb') as f:
                                conn.sendall(b'AckFile')
                                received_bytes = 0
                                while received_bytes < int(num_bytes):
                                    data = conn.recv(1024)    
                                    f.write(data)
                                    received_bytes += len(data)
                                    print([f'{received_bytes}/{int(num_bytes)}'])
                            conn.sendall(b'Fin')
                        else:
                            conn.sendall(b'Inv : not digit')
                    else:
                        conn.sendall(b'Inv : data is not S or Q')

open_connection()

        
    

