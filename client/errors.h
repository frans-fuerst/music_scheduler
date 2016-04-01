#pragma once

#include <stdexcept>

namespace rrp {

struct error : public std::runtime_error {
    error(const std::string &message) : std::runtime_error(message) {}
};

struct invalid_state : public error {
    invalid_state(const std::string &message) : error(message) {}
};

struct cannot_connect : public error {
    cannot_connect(const std::string &message) : error(message) {}
};

struct timeout : public error {
    timeout(const std::string &message = "") : error(message) {}
};

struct io_error : public error {
    io_error(const std::string &message = "") : error(message) {}
};

}
