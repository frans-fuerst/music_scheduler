#pragma once

#include <string>
#include <vector>

struct config_device_t {
    std::vector<std::string> hostnames =
        {
            "127.0.0.1",
        };
};

struct config_account_t {
    std::string user_id = "";
    std::string user_name = "";
};

struct config_t {
    config_device_t device;
    config_account_t account;
    config_t() : device(), account() {}
    void save();
    void load();
    bool is_complete() const {
        return device.hostnames.size() > 0 &&
                account.user_id != "" &&
                account.user_name != "";
    }

  private:
    std::string m_device_config_filename = "~/.pmp/client_config";
};
