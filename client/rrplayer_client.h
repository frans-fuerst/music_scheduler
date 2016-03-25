#pragma once

#include <pal/log.h>
#include "./errors.h"

#include <zmq.hpp>

class rrp_client {

  public:
    class handler {
        handler(const handler &) = delete;
        handler & operator=(const handler &) = delete;
      public:
        handler() = default;
        virtual void on_notification() = 0;
        virtual ~handler() {}
    };

    rrp_client(handler           &handler,
               pal::log::logger  &logger)
        : logger(logger)
        , m_handler(handler)
        , m_context() {

    }

    void send_str(zmq::socket_t &socket, const std::string &msg) {
        zmq::message_t l_message(msg.size());
        memcpy((void *) l_message.data (), msg.data(), msg.size());
        socket.send(l_message);
    }

    std::string recv_str(zmq::socket_t &socket) {
        zmq::message_t l_msg_request;
        if (!socket.recv(&l_msg_request)) {
            throw rrp::timeout();
        }

        return std::string(static_cast<char*>(l_msg_request.data()),
                           l_msg_request.size());
    }

    void connect(const std::string &hostname) {
        std::string l_addr(pal::str::str("tcp://") << hostname << ":9876");
        logger.log_i() << "connect to: '" << l_addr << "'";

        auto l_socket = new zmq::socket_t(m_context, ZMQ_REQ);
        int l_to(1000);
        l_socket->setsockopt(ZMQ_RCVTIMEO, &l_to, sizeof(l_to));

        l_socket->connect(l_addr.c_str());

        send_str(*l_socket, "{\"type\": \"hello\"}");
        logger.log_i() << l_addr;
        auto l_reply(recv_str(*l_socket));
        logger.log_i() << l_reply;

        m_req_socket = l_socket;
        l_to = -1;
        m_req_socket->setsockopt(ZMQ_RCVTIMEO, &l_to, sizeof(l_to));

        m_connected = true;

        //        self._req_poller = zmq.Poller()
        //        self._req_poller.register(self._req_socket, zmq.POLLIN)
        //        self._running = True
        //        self._sub_thread = threading.Thread(target=self._subscriber_thread_fn)
        //        self._sub_thread.start()
    }

    bool is_connected() {
        return m_connected;
    }

    std::string request(const std::string &msg) {
        if (!m_connected) {
            throw rrp::invalid_state("not connected");
        }
        send_str(*m_req_socket, msg);
        return recv_str(*m_req_socket);

//        self._req_socket.send_json(msg)
//        while True:
//            if self._req_poller.poll(1000) == []:
//                print('server timeout!')
//                continue
//            break
//        reply = self._req_socket.recv_json()
//        self._notification_handler._on_message("reply: %s" % reply)
//        return reply
    }

    void shutdown() {
//        print('shutdown client..')
//        self._running = False
//        self._sub_thread.join()
//        self._req_socket.close()
//        self._context.term()
//        print('ready!')
    }

    void _subscriber_thread_fn() {
//        print("connect to broadcasts")
//        _sub_socket = self._context.socket(zmq.SUB)
//        _sub_socket.connect('tcp://127.0.0.1:9875')
//        _sub_socket.setsockopt(zmq.SUBSCRIBE, b"")

//        _sub_poller = zmq.Poller()
//        _sub_poller.register(_sub_socket, zmq.POLLIN)

//        while True:
//            if not self._running:
//                break
//            if _sub_poller.poll(200) == []:
//                continue
//            _msg = _sub_socket.recv_json()
//            print('published "%s"' % _msg)
//            if self._notification_handler:
//                self._notification_handler._on_notification(_msg)

//        _sub_socket.close()
//        print("disconnect from broadcasts")
    }

  private:
    rrp_client(const rrp_client &) = delete;
    rrp_client & operator =(const rrp_client &) = delete;

    pal::log::logger &logger;
    handler          &m_handler;
    zmq::context_t    m_context;
    bool              m_connected = false;
    zmq::socket_t    *m_req_socket = nullptr;
};
