#pragma once

#include <pal/log.h>
#include <pal/pal.h>
#include "./errors.h"

#include <zmq.hpp>
#include <memory>
#include <thread>
#include <vector>

class pmp_client {

  public:
    const std::string version = "0.1.5";
    typedef std::map<std::string, std::string> kv_map_t;

    class handler {
        handler(const handler &) = delete;
        handler & operator=(const handler &) = delete;
      public:
        handler() = default;
        virtual void server_message(const std::string &) = 0;
        virtual ~handler() {}
    };

    pmp_client(handler           &handler,
               pal::log::logger  &logger)
        : logger(logger)
        , m_handler(handler)
        , m_context()
        , m_subscriber_thread() {

    }

    ~pmp_client() {
        shutdown();
    }

    void send_kv(zmq::socket_t &socket, const kv_map_t &data) {
        auto l_result = pal::str::str("{");
        for (const auto &e : data) {
            l_result << "\"" << e.first << "\":\"" << e.second << "\"";
            if (&e == &(*data.rbegin())) {
                l_result << "}";
            } else {
                l_result << ",";
            }
        }
        _send_str(socket, l_result);
    }

    void _send_str(zmq::socket_t &socket, const std::string &msg) {
        zmq::message_t l_message(msg.size());
        memcpy((void *) l_message.data (), msg.data(), msg.size());
        try {
            socket.send(l_message);
        } catch(zmq::error_t &ex) {
            logger.log_e() << "fatal: could not send(): '" << ex.what() << "'";
        }
    }

    std::string recv_str(zmq::socket_t &socket) {
        zmq::message_t l_msg_request;
        try {
            if (!socket.recv(&l_msg_request)) {
                throw pmp::timeout();
            }
        } catch(zmq::error_t &ex) {
            logger.log_e() << "fatal: could not recv(): '" << ex.what() << "'";
        }

        return std::string(
                    static_cast<char*>(l_msg_request.data()),
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

    void connect(
            const std::string &user_id,
            const std::string &user_name,
            const std::string &hostname) {

        m_user_id = user_id;
        m_user_name = user_name;
        std::string l_addr(pal::str::str("tcp://") << hostname << ":9876");
        auto l_socket(create_socket(m_context, ZMQ_REQ));
        set_recv_timeout(l_socket, 1000);
        l_socket->connect(l_addr.c_str());

        _send_hello(*l_socket);

        m_req_socket = l_socket;
        // set_recv_timeout(m_req_socket, -1);

        m_connected = true;

        m_subscriber_thread = std::thread(
                    &pmp_client::subscriber_thread_fn, this,
                    hostname, 9875);

        //        self._req_poller = zmq.Poller()
        //        self._req_poller.register(self._req_socket, zmq.POLLIN)
    }

    bool is_connected() {
        return m_connected;
    }

    kv_map_t request(const kv_map_t &data, bool throw_on_timeout=false) {
        return _request(*m_req_socket, data, throw_on_timeout);
    }

    kv_map_t handle_response(const kv_map_t &data) {
        auto _type_it = data.find("type");
        if (_type_it == data.end()) {
            // throw response_malformed("not 'type'");
        }
        if (_type_it->second == "error") {
            auto _id_it = data.find("id");
            if (_id_it == data.end()) {
                /// throw unspecified
            } else if (_id_it->second == "not_identified") {
                _send_hello(*m_req_socket);

            } else {
                /// throw unspecified
            }

        }
        return data;
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
            } catch (pmp::timeout &) {}
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
    kv_map_t _request(
                  zmq::socket_t &socket,
            const kv_map_t      &data,
                  bool           throw_on_timeout) {

        if (!m_connected) {
            throw pmp::invalid_state("not connected");
        }
        send_kv(socket, data);
        //        while True:
        //            if self._req_poller.poll(1000) == []:
        //                print('server timeout!')
        //                continue
        //            break
        //        reply = self._req_socket.recv_json()
        try {
            return handle_response(pal::json::to_map(recv_str(*m_req_socket)));
        } catch (pmp::timeout &ex) {
            if (throw_on_timeout) {
                throw;
            } else {
                // here we have to handle timeouts in a gerneric way
                return kv_map_t();
            }
        }
    }

    void _send_hello(
                    zmq::socket_t &socket) {
        send_kv(socket, {{"type", "hello"},
                         {"user_id", m_user_id},
                         {"user_name", m_user_name}});
        auto l_response_str(recv_str(socket));
        auto l_reply(handle_response(pal::json::to_map(l_response_str)));
        logger.log_i() << l_response_str;
        m_handler.server_message(l_response_str);

        // todo: handle port
        // const auto l_reply_values(pal::json::to_map(l_reply));
    }

  private:
    pmp_client(const pmp_client &) = delete;
    pmp_client & operator =(const pmp_client &) = delete;

    pal::log::logger               &logger;
    handler                        &m_handler;
    zmq::context_t                  m_context;
    bool                            m_connected = false;
    bool                            m_running = false;
    std::shared_ptr<zmq::socket_t>  m_req_socket = nullptr;
    std::thread                     m_subscriber_thread;
    std::string                     m_user_id = "";
    std::string                     m_user_name = "";
};
