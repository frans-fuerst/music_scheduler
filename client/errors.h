#pragma once

#include <stdexcept>

namespace pmp {

struct error : public std::runtime_error {
    explicit error(const std::string &message) : std::runtime_error(message) {}
};

struct invalid_state : public error {
    explicit invalid_state(const std::string &message) : error(message) {}
};

struct cannot_connect : public error {
    explicit cannot_connect(const std::string &message) : error(message) {}
};

struct timeout : public error {
    explicit timeout(const std::string &message = "") : error(message) {}
};

struct io_error : public error {
    explicit io_error(const std::string &message = "") : error(message) {}
};

}
