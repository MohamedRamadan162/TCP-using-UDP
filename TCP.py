import socket
import threading
import time

class UDPServer:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.connections = {}  # Store connection state
        print(f"Server started at {host}:{port}")

    def listen(self):
        while True:
            data, addr = self.sock.recvfrom(4096)
            print(f"Received data from {addr}: {data.decode().strip()}")
            self.handle_packet(data, addr)

    def handle_packet(self, data, addr):
        headers, content = data.decode().split('\r\n\r\n', 1)
        request_line = headers.split('\r\n')[0]
        headers_dict = {line.split(":")[0].strip(): line.split(":")[1].strip() for line in headers.split('\r\n')[1:]}
        method, path, protocol = request_line.split()
        connection = headers_dict.get("Connection", "close")

        if connection.lower() == "keep-alive":
            if addr not in self.connections:
                self.connections[addr] = {"last_seen": time.time()}
            else:
                self.connections[addr]["last_seen"] = time.time()
            response_connection = "keep-alive"
        else:
            response_connection = "close"

        response = "HTTP/1.1 405 Method Not Allowed\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nMethod not supported."
        if method == 'GET':
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: {response_connection}\r\n\r\nHello, this is a GET response."
        elif method == 'POST':
            print(f"Received POST request with body: {content}")
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: {response_connection}\r\n\r\nReceived POST data: {content}"
        
        self.sock.sendto(response.encode(), addr)

        if response_connection == "close":
            if addr in self.connections:
                del self.connections[addr]

class UDPClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (host, port)

    def send_request(self, method="GET", content="", keep_alive=True):
        connection_header = "keep-alive" if keep_alive else "close"
        body = f"\r\n\r\n{content}" if content else "\r\n\r\n"
        request = f"{method} / HTTP/1.1\r\nHost: localhost\r\nConnection: {connection_header}\r\nContent-Length: {len(content)}{body}"
        self.sock.sendto(request.encode(), self.server_address)
        data, _ = self.sock.recvfrom(1024)
        print(f"Received {method} response:")
        print(data.decode())

# Example usage
server = UDPServer('localhost', 10000)
server_thread = threading.Thread(target=server.listen)
server_thread.start()

# Run client actions after server thread has started
client = UDPClient('localhost', 10000)
client.send_request("GET")
client.send_request("POST", "This is the data sent via POST", True)
client.send_request("DELETE")
