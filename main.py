import os.path
import logging
import re
import uuid

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.locks
import tornado.gen

from tornado.options import define, options, parse_command_line

define("port", default=8080, help="run on the given port", type=int)
define("debug", default=True, help="run in debug mode")

lock = tornado.locks.Lock()


class MainHandler(tornado.web.RequestHandler):
    def check_xsrf_cookie(self):
        return True

    def get(self, doc_uuid=""):
        logging.info("index with (uuid: %s)" % doc_uuid)
        print(self.request.query_arguments)
        if "server" in self.request.query_arguments:
            print("rcv from "+self.request.query_arguments["server"][0].decode())
            WsHandler.send_messages(self.request.query_arguments["server"][0].decode())

        else:
            self.render("index.html", uuid=doc_uuid)

    def post(self):
        logging.info("post")
        data = tornado.escape.json_decode(self.request.body)
        if "server" in data:
            print("rcv from "+data["server"])
            WsHandler.send_messages(data["server"])


class WsHandler(tornado.websocket.WebSocketHandler):
    clients = {}
    allClients = []
    files = {}
    page_size = 100

    def __init__(self, application, request, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
        self.rows = []
        self.uuid = None

    @classmethod
    @tornado.gen.coroutine
    def add_clients(cls, doc_uuid, client):
        logging.info("add a client with (uuid: %s)" % doc_uuid)

        # locking clients
        with (yield lock.acquire()):
            if doc_uuid in cls.clients:
                clients_with_uuid = WsHandler.clients[doc_uuid]
                clients_with_uuid.append(client)
            else:
                WsHandler.clients[doc_uuid] = [client]

            cls.allClients.append(client)

    @classmethod
    @tornado.gen.coroutine
    def remove_clients(cls, doc_uuid, client):
        logging.info("remove a client with (uuid: %s)" % doc_uuid)

        # locking clients
        with (yield lock.acquire()):
            if doc_uuid in cls.clients:
                clients_with_uuid = WsHandler.clients[doc_uuid]
                clients_with_uuid.remove(client)

                if len(clients_with_uuid) == 0:
                    del cls.clients[doc_uuid]

            if doc_uuid not in cls.clients and doc_uuid in cls.files:
                del cls.files[doc_uuid]
            cls.allClients.remove(client)


    def check_origin(self, origin):
        return options.debug or bool(re.match(r'^.*\catlog\.kr', origin))

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self, doc_uuid=None):
        logging.info("open a websocket (uuid: %s)" % doc_uuid)

        if doc_uuid is None:
            # Generate a random UUID
            self.uuid = str(uuid.uuid4())

            logging.info("new client with (uuid: %s)" % self.uuid)
        else:
            self.uuid = doc_uuid
            WsHandler.send_message(self.uuid, self)

            logging.info("new client sharing (uuid: %s)" % self.uuid)

        WsHandler.add_clients(self.uuid, self)

    def on_close(self):
        logging.info("close a websocket")

        WsHandler.remove_clients(self.uuid, self)

    def on_message(self, message):
        logging.info("got message (uuid: %s)" % self.uuid)
        logging.info("page_no: " + message)

        WsHandler.send_messages(self.uuid)

    @classmethod
    def send_messages(cls, message):
        clients_with_uuid = cls.clients #[doc_uuid]

        logging.info("sending message to %d clients", len(clients_with_uuid))
        print(clients_with_uuid)
        out_message = cls.make_message(message)

        for client in cls.allClients:
            try:
                client.write_message(out_message)
            except:
                logging.error("Error sending message", exc_info=True)

    @classmethod
    def send_message(cls, doc_uuid, client):
        clients_with_uuid = cls.clients[doc_uuid]
        logging.info("sending message to %d clients", len(clients_with_uuid))

        message = cls.make_message(doc_uuid)
        client.write_message(message)

    @classmethod
    def make_message(cls, message):

        return {
            "message": message
        }


def main():
    parse_command_line()
    settings = dict(
            cookie_secret="SX4gEWPE6bVasdasdr0vbwGtMl",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            debug=options.debug
    )

    handlers = [
            (r"/", MainHandler),
            (r"/update", MainHandler),
            (r"/share/([^/]+)", MainHandler),
            (r"/ws", WsHandler),
            (r"/ws/([^/]+)", WsHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": settings["static_path"]})
    ]

    app = tornado.web.Application(handlers, **settings)
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
