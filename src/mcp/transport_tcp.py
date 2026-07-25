"""MCP TCP transport — socket-based JSON-RPC 2.0, disabled by default, localhost-only."""

import json
import socket
import threading


class TcpTransport:
    def __init__(self, host="127.0.0.1", port=9102):
        self.host = host
        self.port = port
        self._server = None
        self._running = False

    def start(self, handler):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(5)
        self._running = True
        threading.Thread(target=self._accept, args=(handler,), daemon=True).start()

    def _accept(self, handler):
        while self._running:
            try:
                client, addr = self._server.accept()
                threading.Thread(target=self._handle_client, args=(client, handler), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, client, handler):
        buf = b""
        while self._running:
            try:
                data = client.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError as e:
                        msg = {"error": {"code": -32700, "message": "Parse error: " + str(e)}}
                    response = handler(msg)
                    if response is not None:
                        client.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except OSError:
                break
        try:
            client.close()
        except OSError:
            pass

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass

    def __repr__(self):
        return "TcpTransport(%s:%d)" % (self.host, self.port)
