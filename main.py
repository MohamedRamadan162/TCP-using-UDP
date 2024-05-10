import socket
import threading
import time

# Server configuration details
SERVER_IP = '127.0.0.1'  # IP address of the server
SERVER_PORT = 3000      # Port number for the server
BUFFER_SIZE = 1024       # Size of the buffer for receiving data

client_address = (SERVER_IP, SERVER_PORT)

# Create a UDP socket for the server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_IP, SERVER_PORT))

# Initialize sequence numbers for client and server
client_seq = 0
server_seq = 0

def send_handshake(sock, address):
    """ Initiate a three-way handshake from the client side. """
    global client_seq
    sock.sendto(f"SYN:{client_seq}".encode(), address)
    response, _ = sock.recvfrom(BUFFER_SIZE)
    if "SYN-ACK" in response.decode():
        client_seq += 1
        sock.sendto(f"ACK:{client_seq}".encode(), address)
        print("Handshake completed")
        return True
    return False

def listen_for_handshake(sock):
    """ Listen and respond to handshake initiation on the server side. """
    global server_seq
    data, addr = sock.recvfrom(BUFFER_SIZE)
    if "SYN" in data.decode():
        server_seq += 1
        sock.sendto(f"SYN-ACK:{server_seq}".encode(), addr)
        ack, _ = sock.recvfrom(BUFFER_SIZE)
        if "ACK" in ack.decode():
            print("Handshake completed with client")
            return addr
    return None

def reliable_send(data, addr):
    global client_seq
    """ Send data reliably by ensuring acknowledgment for each packet. """
    tries = 5             # Maximum number of tries to resend data
    timeout = 2           # Timeout in seconds before resending data
    server_socket.settimeout(timeout)  # Set the socket timeout
    ack_received = False  # Flag to track acknowledgment receipt

    while not ack_received and tries > 0:
        print(f"Sending data: {data}")
        packet = f"{client_seq}:{data}".encode()  # Encode data with sequence number
        server_socket.sendto(packet, addr)        # Send the packet
        try:
            ack, _ = server_socket.recvfrom(BUFFER_SIZE)  # Receive acknowledgment
            ack_seq = int(ack.decode().split(':')[1])     # Parse the acknowledgment sequence
            if ack_seq == client_seq:             # Check if the received ACK is for the sent packet
                ack_received = True
                client_seq += 1                  # Increment sequence number on acknowledgment
        except socket.timeout:
            tries -= 1                           # Decrement retry count on timeout
            print("Timeout, retrying...")
    if not ack_received:
        print("Failed to receive ACK after several tries.")
    return ack_received

def handle_client(addr):
    global server_seq
    """ Thread to handle incoming data and send ACKs. """
    while True:
        data, _ = server_socket.recvfrom(BUFFER_SIZE)  # Listen for incoming data
        parts = data.decode().split(':', 1)  # Split the data into parts
        print("parts", parts)
        command = parts[0]  # The command could be a sequence number or a control message like "SYN"

        if command.isdigit():  # Check if the command is a digit (sequence number)
            received_seq = int(command)  # Convert to integer if it's a sequence number
            message = parts[1]  # The actual message
            if received_seq == server_seq:  # Check sequence number for ordering
                print(f"Received: {message} from {addr}")
                ack = f"ACK:{server_seq}".encode()  # Send ACK with the correct sequence
                server_socket.sendto(ack, addr)
                server_seq += 1  # Increment server sequence number
                # Process further if there's a specific handling mechanism for data packets
        else:
            # Handle control messages like "SYN", "ACK", etc.
            if command == "SYN":
                # Process SYN message, send SYN-ACK, etc.
                server_seq += 1  # Or handle according to your protocol design
                response = f"SYN-ACK:{server_seq}".encode()
                server_socket.sendto(response, addr)
            elif command == "ACK":
                print("Handshake completed with client")
                # Further processing can be done here if necessary


def process_http_get(request, addr):
    """ Process a simple HTTP GET request and send a response. """
    headers, _ = request.split('\r\n\r\n', 1)
    path = headers.split(' ')[1]                   # Extract the requested path
    response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nYou requested {path}"
    reliable_send(response, addr)                  # Send response reliably

def main():
    """ Main function to run server and client functionalities. """
    thread = threading.Thread(target=handle_client, args=(client_address,))
    thread.start()
    time.sleep(1)  # Give the server thread time to start

    # Example HTTP GET request
    if send_handshake(server_socket, client_address):
        http_request = "GET /hello HTTP/1.1\r\nHost: localhost\r\n\r\n"
        reliable_send(http_request, client_address)  # Send an HTTP request to test
    
    thread.join()  # Ensure that the server thread completes before exiting

if __name__ == '__main__':
    main()
