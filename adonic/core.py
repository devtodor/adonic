# -*- coding: utf-8 -*-
"""
author: Todor Bukov
"""

import socket
import select

class Base():
    def __init__(self):
        pass



class SocketPair(Base):
    """
    Represents client/server pair of sockets on the two sides of the fully
    proxied connection.
    """
    def __init__(self, client_socket=None, server_socket=None):
        super().__init__()
        self._client_socket = client_socket
        self._server_socket = server_socket


    def fileno_list(self):
        """
        Return a list of file descriptiors in the socket pair.
        May return less than two file descriptiors in case one or both sockets
        are None.
        """

        result = []
        try:
            result.append(self._client_socket.fileno())
        except AttributeError:
            pass

        try:
            result.append(self._server_socket.fileno())
        except AttributeError:
            pass

        return result


    @property
    def client_socket(self):
        return self._client_socket

    @client_socket.setter
    def client_socket(self, new_socket):
        self._client_socket = new_socket

    @property
    def server_socket(self):
        return self._server_socket

    @server_socket.setter
    def server_socket(self, new_socket):
        self._server_socket = new_socket



class Probe(Base):
    """
    Represent a specific method for probing for the health of a server.
    """
    def __init__(self):
        super().__init__()

    def probe(self):
        """
        Returns True if the probe is successfull or False if it fails.
        """
        pass



class Pool(Base):
    """
    Represents a list of backend servers.
    """
    def __init__(self):
        super().__init__()

    def add(self, address, port):
        pass

    def remove(self, address, port):
        pass

    def list_all(self):
        pass

    def clear(self):
        pass

    def extend(self, pool):
        pass



class Monitor(Base):
    """
    Uses probes (instances of Probe) to continuously monitor the server health.
    """

    def __init__(self, probe, pool):
        super().__init__()
        self._probe = probe
        self._pool = pool

    def servers_up(self):
        pass

    def servers_down(self):
        pass

    def reset(self):
        pass



class Protocol(Base):
    """
    Describes how to process the data between the client and the server.
    """
    def __init__(self, socketpair):
        super().__init__()
        self._socketpair = socketpair

    def client_data_received(self, data):
        pass

    def server_data_received(self, data):
        pass


class PassthroughProtocol(Protocol):
    def __init__(self, socketpair, bufsize=4096):
        super().__init__(socketpair)
        self.set_bufsize(bufsize)

    def set_bufsize(self, bufsize):
        self._bufsize = bufsize

    # There is plenty of room for optimizations in the below code
    def client_data_received(self, data):
        data = self._socketpair.client_socket.read(self._bufsize)
        self._socketpair.server_socket.send(data)

    def server_data_received(self, data):
        data = self._socketpair.server_socket.read(self._bufsize)
        self._socketpair.client_socket.send(data)



class Service(Base):
    """
    Represent TCP or UDP service offered to clients
    """
    def __init__(self, protocol, address, port,
                 pool=None, monitor=None):
        super().__init__()
        self._protocol = protocol
        self._address = address
        self._port = port
        self.set_pool(pool)
        self.set_monitor(monitor)

    def set_pool(self, pool):
        self._pool = pool

    def set_monitor(self, monitor):
        self._monitor = monitor

    def start(self):
        pass

    def shutdown(self):
        pass

    def enable(self):
        pass

    def disable(self):
        pass



class Reactor(Base):
    """
    Process the events from the sockets in a specific Service
    """
    def __init__(self, probe, pool):
        super().__init__()
        self.epoll = select.epoll()



class TCPTransport(Base):
    def __init__(self, address, port,
                 conn_backlog=10):

        super().__init__()

        self.epoll = select.epoll()
        self._address = address
        self._port = port
        self._conn_backlog = conn_backlog

        try:
            # Attempt to use SO_REUSEPORT since under Linux it guarantees
            # fair load balancing between multiple threads/processes
            # listening on the same port
            self.serversocket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEPORT, 1)
        except AttributeError:
            # If SO_REUSEPORT is not available, then use SO_REUSEADDR instead
            self.serversocket.setsockopt(socket.SOL_SOCKET,
                                         socket.SO_REUSEADDR, 1)



    def start_processing(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((self._address, self._port))
        self.serversocket.listen(self._conn_backlog)
        self.serversocket.setblocking(False)

        self.epoll.register(self.serversocket.fileno(), select.EPOLLIN)

        self._connections = {}

        try:
           while True:
              events =self.epoll.poll(1)
              for fileno, event in events:
                # Check if the event comes from the bound socket i.e.
                # a new client connection (South) request has arrived
                if fileno == self.serversocket.fileno():
                    client_conn, address = self.serversocket.accept()
                    client_conn.setblocking(False)
                    # register interest in read from the client
                    self.epoll.register(client_conn.fileno(),
                                        select.EPOLLIN)
                    self._connections[client_conn.fileno()] = client_conn
                    # TODO: connect to a server socket (North), register interest in
                    # read from the server
                elif event & select.EPOLLIN:
                    # New data arrived from the socket
                    # TODO:
                    pass
                elif event & select.EPOLLOUT:
                    # The socket is ready for sending more data
                    # TODO:
                    pass
                elif event & select.EPOLLHUP:
                    # The socket has been closed
                    self.epoll.unregister(fileno)
                    self._connections[fileno].close()
                    # TODO: close the server connection (North) first
                    del self._connections[fileno]

            # TODO: process client connections and connect them to the server

        finally:
           self.epoll.unregister(self.serversocket.fileno())
           self.epoll.close()
           self.serversocket.close()
