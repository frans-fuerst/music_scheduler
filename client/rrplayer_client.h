#pragma once

#include <pal/log.h>
#include <pal/pal.h>
#include "./errors.h"

#include <zmq.hpp>
#include <memory>
#include <thread>
#include <vector>

class rrp_client {

  public:
    class handler {
        handler(const handler &) = delete;
        handler & operator=(const handler &) = delete;
      public:
        handler() = default;
        virtual void server_message(const std::string &) = 0;
        virtual ~handler() {}
    };

    rrp_client(handler           &handler,
               pal::log::logger  &logger)
        : logger(logger)
        , m_handler(handler)
        , m_context()
        , m_subscriber_thread() {

    }

    ~rrp_client() {
        shutdown();
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

    static std::shared_ptr<zmq::socket_t> create_socket(
            zmq::context_t &context,
            int             type) {
        std::shared_ptr<zmq::socket_t> l_result(new zmq::socket_t(context, type));
        int l_value(0);
        l_result->setsockopt(ZMQ_LINGER, &l_value, sizeof(l_value));
        return l_result;
    }

    static void set_recv_timeout(
            std::shared_ptr<zmq::socket_t> socket,
            int                            timeout) {
        socket->setsockopt(ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
    }

    void connect(const std::string &hostname) {
        std::string l_addr(pal::str::str("tcp://") << hostname << ":9876");
        auto l_socket(create_socket(m_context, ZMQ_REQ));
        set_recv_timeout(l_socket, 1000);
        l_socket->connect(l_addr.c_str());

        send_str(*l_socket, pal::str::str("{\"type\": \"hello\", \"name\":\"")
                 << pal::os::user_name() << "\"}");
        auto l_reply(recv_str(*l_socket));
        logger.log_i() << l_reply;
        m_handler.server_message(l_reply);

        // todo: handle port
        // const auto l_reply_values(pal::json::to_map(l_reply));

        m_req_socket = l_socket;
        set_recv_timeout(m_req_socket, -1);

        m_connected = true;

        m_subscriber_thread = std::thread(
                    &rrp_client::subscriber_thread_fn, this,
                    hostname, 9875);

        //        self._req_poller = zmq.Poller()
        //        self._req_poller.register(self._req_socket, zmq.POLLIN)
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
        logger.log_i() << "shutdown client..";
        if (m_running) {
            m_running = false;
            m_subscriber_thread.join();
        }
//        self._req_socket.close()
//        self._context.term()
        logger.log_i() << "ready!";
    }

    void subscriber_thread_fn(const std::string &hostname, int port) {
//        print("connect to broadcasts")
        m_running = true;
        auto l_sub_socket(create_socket(m_context, ZMQ_SUB));
        std::string l_addr(pal::str::str("tcp://") << hostname << ":" << port);
        l_sub_socket->connect(l_addr.data());
        l_sub_socket->setsockopt(ZMQ_SUBSCRIBE, "", 0);
        set_recv_timeout(l_sub_socket, 100);

//        _sub_poller = zmq.Poller()
//        _sub_poller.register(_sub_socket, zmq.POLLIN)

        while (m_running) {
            try {
                auto l_message_str(recv_str(*l_sub_socket));
                m_handler.server_message(l_message_str);
            } catch (rrp::timeout &) {}
        }
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

    pal::log::logger               &logger;
    handler                        &m_handler;
    zmq::context_t                  m_context;
    bool                            m_connected = false;
    bool                            m_running = false;
    std::shared_ptr<zmq::socket_t>  m_req_socket = nullptr;
    std::thread                     m_subscriber_thread;
};
