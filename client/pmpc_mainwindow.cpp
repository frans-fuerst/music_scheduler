#include "./pmpc_mainwindow.h"
#include "./pmpc_client.h"
#include "./errors.h"

#include <pal/pal.h>
#include <pal/str.h>
#include <pal/log.h>
#include <pal/error.h>

#include <QString>
#include <QPushButton>
#include <QListWidget>
#include <QTextEdit>
#include <QtUiTools>

#include <boost/algorithm/string/join.hpp>

#include <iostream>
#include <fstream>
#include <stdlib.h>

#if defined(ANDROID)
#include <android/log.h>
#endif

pmpc_mainwindow::pmpc_mainwindow(
        QWidget *a_parent)
    : QMainWindow(a_parent)
    , pal::log::logger(
          std::bind(
              &pmpc_mainwindow::log_output, this,
              std::placeholders::_1,
              std::placeholders::_2))
    , m_client(*this, *this)
    , m_config() {

    QWidget *l_ui_widget = loadUiFile();
    setCentralWidget(l_ui_widget);

    m_lst_messages = l_ui_widget->findChild<QListWidget*>("lst_messages");
    m_lbl_current_track = l_ui_widget->findChild<QLabel*>("lbl_current_track");
    m_lbl_current_track_location = l_ui_widget->findChild<QLabel*>("lbl_current_track_location");
    m_lbl_host = l_ui_widget->findChild<QLabel*>("lbl_host");
    m_sb_position = l_ui_widget->findChild<QScrollBar*>("sb_position");
    m_txt_ban_substring = l_ui_widget->findChild<QLineEdit*>("txt_ban_substring");
    m_frm_ban = l_ui_widget->findChild<QFrame*>("frm_ban");
    m_frm_search_result = l_ui_widget->findChild<QFrame*>("frm_search_result");
    m_frm_credentials = l_ui_widget->findChild<QFrame*>("frm_credentials");
    m_txt_username = l_ui_widget->findChild<QLineEdit*>("txt_username");
    m_txt_hostnames = l_ui_widget->findChild<QLineEdit*>("txt_hostnames");
    m_lst_result = l_ui_widget->findChild<QListWidget*>("lst_result");
    m_txt_search_or_add = l_ui_widget->findChild<QLineEdit*>("txt_search_or_add");

    m_frm_ban->setVisible(false);
    m_frm_search_result->setVisible(false);
    m_frm_credentials->setVisible(false);


    m_txt_ban_substring->setInputMethodHints(Qt::ImhNoPredictiveText);
    m_txt_search_or_add->setInputMethodHints(Qt::ImhNoPredictiveText);

    resize(700, 700);
    setWindowTitle("party music player");

    log_i() << "version: "  << m_client.version;
    log_i() << "pwd:     '" << QApplication::applicationDirPath() << "'";
    log_i() << "home:    '" << pal::fs::expanduser("~") << "'";

    QMetaObject::connectSlotsByName(this);

    /// call show before reading geometry
    show();

    // QSize l_pbsize(m_txt_search->height(), m_txt_search->height());
    // l_pb_add->setFixedSize(l_pbsize);
}

pmpc_mainwindow::~pmpc_mainwindow() {
}

std::string pmpc_mainwindow::generate_uid() {
    std::string l_return;
    l_return.reserve(16);
    l_return.resize(16);
    const char *l_characters = "0123456789abcdef";
    for(int i = 0; i < 16; ++i){
        l_return[i] = l_characters[rand() % 16];
    }
    return l_return;
}

void pmpc_mainwindow::log_output(
        const std::string       &a_message,
              pal::log::level_t  a_level) {
    std::string l_message(
                (pal::str::str()
                 << ((a_level == pal::log::level_t::CRITICAL) ? "(CC) " :
                     (a_level == pal::log::level_t::ERROR)    ? "(EE) " :
                     (a_level == pal::log::level_t::WARNING)  ? "(WW) " :
                     (a_level == pal::log::level_t::INFO)     ? "(II) " :
                     (a_level == pal::log::level_t::DEBUG)    ? "(DD) " :
                     (a_level == pal::log::level_t::TRACE)    ? "(TT) " : "(--)")
                 // << "0x" << std::hex << std::this_thread::get_id() << ":  "
                 << a_message));
#if defined(ANDROID)
    __android_log_print(ANDROID_LOG_INFO, "pmpc", l_message.c_str());
#else
    std::cout << l_message << std::endl;
#endif

    QMetaObject::invokeMethod(
                this, "add_log_line", Qt::QueuedConnection,
                Q_ARG(QString, QString::fromStdString(l_message.c_str())));
}

void pmpc_mainwindow::add_log_line(const QString &a_msg) {
    if (!m_lst_messages) {
        return;
    }
    m_lst_messages->addItem(QString(a_msg));
    m_lst_messages->scrollToBottom();
}

void pmpc_mainwindow::server_message(
        const std::string &a_msg) {
    QMetaObject::invokeMethod(
                this, "on_server_message", Qt::QueuedConnection,
                Q_ARG(QString, QString::fromStdString(a_msg)));
}

void pmpc_mainwindow::on_server_message(const QString &a_msg) {
    auto l_values(pal::json::to_map(a_msg.toStdString()));

    //log_d() << "message:";
    for (auto &p : l_values) {
        if (p.first == "type") {
        } else if (p.first == "current_track") {
            auto l_current_track_components(pal::str::split(p.second, ':'));
            if (l_current_track_components.size() >= 3) {
                log_i() << "now playing: " << l_current_track_components[1]
                        << "/" << l_current_track_components[2];
                m_lbl_current_track->setText(
                            QString::fromStdString(
                                pal::fs::basename(l_current_track_components[2])));
                m_lbl_current_track_location->setText(
                            QString::fromStdString(l_current_track_components[1]));
                m_current_track = l_current_track_components[1]
                                + "/"
                                + l_current_track_components[2];
            }
        } else if (p.first == "track_length") {
            m_sb_position->setMaximum(static_cast<int>(
                QString::fromStdString(p.second).toFloat()));
        } else if (p.first == "current_pos") {
            m_sb_position->setValue(static_cast<int>(
                QString::fromStdString(p.second).toFloat()));
        } else {
            log_d() << "   " << p.first << ": " << p.second;
        }
    }
}

bool pmpc_mainwindow::event(QEvent *event) {
    if (event->type() == QEvent::WindowActivate) {
        if (!m_initialized) {
            on_initialized();
        }
    }
    return QMainWindow::event(event);
}

void pmpc_mainwindow::on_initialized() {
    m_initialized = true;
    try {
        m_config.load();
    } catch (pal::could_not_open &ex) {
        log_w() << "could not load configuration. that better be the first run..";
        m_config.device.hostnames = {
            "127.0.0.1",
            "mucke", "10.0.0.113",
            "brick", "10.0.0.103",
        };

        m_config.account.user_id = generate_uid();
        m_config.save();
    } catch (pal::broken_format &ex) {
        log_e() << "exception when trying to read config file: " << ex.what();
        throw;
    }

    log_i() << "user ID:   '" << m_config.account.user_id << "'";
    log_i() << "user name: '" << m_config.account.user_name << "'";
    log_i() << "hosts:     "
            << boost::algorithm::join(m_config.device.hostnames, " ");

    if (m_config.is_complete()) {
        QTimer::singleShot(1000, this, SLOT(one_connection_attempt()));
    } else {
        on_pb_config_clicked();
    }
}

void pmpc_mainwindow::one_connection_attempt() {
    if (m_client.is_connected()) {
        return;
    }
    for (auto l_hostname : m_config.device.hostnames) {
        try {
            log_i() << "try connection to: '" << l_hostname << "'";
            m_client.connect(m_config.account.user_id, m_config.account.user_name, l_hostname);
            log_i() << "success!";
            m_lbl_host->setText(QString::fromStdString(l_hostname));
            return;
        } catch (pmp::error &e) {
            log_w() << "failure: '" << e.what() << "'";
        }
    }

    log_i() << "no known host reachable";
}

void pmpc_mainwindow::on_txt_search_or_add_textChanged(
        const QString &text) {

    try {
        search_on_server(text.toStdString());
    } catch (pmp::timeout &) {}
}

void pmpc_mainwindow::search_on_server(
        const std::string &a_text) {

    // log_i() << (a_text != "" ? a_text : "empty search text!");

    auto l_reply(m_client.request({{"type", "search"},
                                    {"query", a_text}}));

    auto l_result_it(l_reply.find("result"));

    m_lst_result->clear();
    m_search_result_identifier.clear();
    if (l_result_it == l_reply.end()) {
        log_e() << "result element is missing";
        return;
    }
    auto l_result_items(pal::str::split(l_result_it->second, '|'));
    if (l_result_items.size() == 0) {
        m_lst_result->addItem("no result");
    }

    for (auto &l_item : l_result_items) {
        auto l_components(pal::str::split(l_item, ':'));
        m_lst_result->addItem(QString::fromStdString(l_components[1]));
        m_search_result_identifier.push_back(l_components[0]);
    }

    m_lst_result->setEnabled(!l_result_items.empty());
    m_frm_search_result->setVisible(a_text.length() > 0);
    update();
}

void pmpc_mainwindow::on_txt_search_or_add_returnPressed() {
    log_i() << "enter";
}

void pmpc_mainwindow::on_pb_play_clicked() {
    log_i() << "play";
    try {
        m_client.request({{"type", "play"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_pause_clicked() {
    log_i() << "pause";
    try {
        m_client.request({{"type", "pause"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_stop_clicked() {
    log_i() << "stop";
    try {
        m_client.request({{"type", "stop"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_skip_clicked() {
    log_i() << "skip";
    try {
        m_client.request({{"type", "skip"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_upvote_clicked() {
    log_i() << "upvote";
    try {
        m_client.request({{"type", "add_tag"},
                          {"tag_name", "upvote"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_ban_clicked() {
    log_i() << "ban";
    m_frm_ban->setVisible(true);
    m_txt_ban_substring->setText(QString::fromStdString(m_current_track));
}

void pmpc_mainwindow::on_txt_ban_substring_selectionChanged() {
    auto l_current_selection(m_txt_ban_substring->selectedText());
    if (l_current_selection == "") {
        return;
    }
    m_selected_ban_substring = l_current_selection;
}

void pmpc_mainwindow::on_pb_ban_crop_clicked() {
    m_txt_ban_substring->setText(m_selected_ban_substring);
}

void pmpc_mainwindow::on_pb_ban_path_clicked() {
    std::vector<std::string> l_components(pal::str::split(m_current_track, '/'));
    if (l_components.size() < 1) {
        return;
    }
    l_components.pop_back();
    m_txt_ban_substring->setText(QString::fromStdString(
                                     boost::algorithm::join(l_components, "/")));
}

void pmpc_mainwindow::on_pb_ban_folder_clicked() {
    std::vector<std::string> l_components(pal::str::split(m_current_track, '/'));
    if (l_components.size() < 2) {
        return;
    }
    m_txt_ban_substring->setText(QString::fromStdString(*(l_components.rbegin() + 1)));
}

void pmpc_mainwindow::on_pb_ban_file_clicked() {
    std::vector<std::string> l_components(pal::str::split(m_current_track, '/'));
    m_txt_ban_substring->setText(QString::fromStdString(*l_components.rbegin()));
}

void pmpc_mainwindow::on_pb_ban_ok_clicked() {
    log_i() << "ban/ok";
    m_frm_ban->setVisible(false);

    try {
        m_client.request({{"type", "add_tag"},
                          {"tag_name", "ban"},
                          {"subject", m_txt_ban_substring->text().toStdString()}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_ban_cancel_clicked() {
    log_i() << "ban/cancel";
    m_frm_ban->setVisible(false);
}

void pmpc_mainwindow::on_pb_add_clicked() {
    log_i() << "add";
}

void pmpc_mainwindow::on_pb_volup_clicked() {
    log_i() << "volume up";
    try {
        m_client.request({{"type", "volup"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_voldown_clicked() {
    log_i() << "volume down";
    try {
        m_client.request({{"type", "voldown"}});
    } catch (pmp::error &ex) {
        log_e() << "got error '" << ex.what() << "'";
    }
}

void pmpc_mainwindow::on_pb_config_clicked() {
    log_i() << "config";
    m_txt_hostnames->setText(QString::fromStdString(
                                 boost::algorithm::join(m_config.device.hostnames, ",")));
    m_txt_username->setText(QString::fromStdString(
                                 m_config.account.user_name));

    m_frm_credentials->setVisible(true);
}

void pmpc_mainwindow::on_pb_connect_clicked() {
    log_i() << "connect";

    m_config.account.user_name = m_txt_username->text().toStdString();
    pal::str::trim(m_config.account.user_name);
    m_config.device.hostnames = pal::str::split(m_txt_hostnames->text().toStdString(), ',');

    if (m_config.is_complete()) {
        m_config.save();
        m_frm_credentials->setVisible(false);
        QTimer::singleShot(1000, this, SLOT(one_connection_attempt()));
    } else {
        log_e() << "configuration is still incomplete - please correct";
    }
}

void pmpc_mainwindow::on_lst_result_itemClicked(
        QListWidgetItem *a_item) {
    int l_index(m_lst_result->selectionModel()->currentIndex().row());
    std::string l_item(a_item->text().toStdString());
    std::string l_search_identifier(m_search_result_identifier[l_index]);
    log_i() << "item clicked: '" << l_item << "' "
            << l_search_identifier;
    m_txt_search_or_add->setText("");
    m_client.request({{"type", "schedule"},
                      {"item", l_search_identifier}});
}

QWidget * pmpc_mainwindow::loadUiFile() {
    QFile l_file;
    l_file.setFileName("pmpc.ui");
    if(!l_file.exists()) {
        l_file.setFileName(":/pmpc.ui");
    }
    l_file.open(QFile::ReadOnly);
    QUiLoader l_loader;
    return l_loader.load(&l_file, this);
}

void pmpc_mainwindow::closeEvent(QCloseEvent *event) {
    // todo: send goodbye
}

inline std::ostringstream & operator <<(
        std::ostringstream &stream,
        const QString &qstring) {
    stream << qstring.toStdString();
    return stream;
}

//inline sstr & operator <<(
//              sstr &stream,
//        const QString &qstring) {
//    stream << qstring.toStdString();
//    return stream;
//}

void config_t::save() {
    std::string l_filename(pal::fs::expanduser(m_device_config_filename));
    {
        pal::fs::mk_base_dir(l_filename);
        std::ofstream l_config_file(l_filename);
        if (!l_config_file.is_open()) {
            throw pmp::io_error("cannot open local config file for writing!");
        }
        l_config_file << "{" << std::endl;
        l_config_file << "    " << "\"hosts\": \""
                      <<  boost::algorithm::join(device.hostnames, ",")
                      << "\"" << std::endl;
        l_config_file << "}" << std::endl;
    }
    {
        std::string l_account_config_file(
                    pal::fs::join({
                        pal::fs::dirname(l_filename), "account", "account_config"}));
        pal::fs::mk_base_dir(l_account_config_file);
        std::ofstream l_config_file(l_account_config_file);
        if (!l_config_file.is_open()) {
            throw pmp::io_error("cannot open account config file for writing!");
        }
        l_config_file << "{" << std::endl;
        l_config_file << "    " << "\"user_id\": \""
                      << account.user_id << "\"" << "," << std::endl;
        l_config_file << "    " << "\"user_name\": \""
                      << account.user_name << "\"" << std::endl;
        l_config_file << "}" << std::endl;

    }
}

void config_t::load() {
    std::vector<std::string> l_new_hostnames;
    std::string l_new_user_id;
    std::string l_new_user_name;

    std::string l_filename(pal::fs::expanduser(m_device_config_filename));
    pal::json::walk_file(l_filename, [&](
                const std::string &k,
                const std::string &v) {
        if (k == "hosts") {
            l_new_hostnames = pal::str::split(v, ',');
        } else {
            std::cout << "unknown: '" << k << "': '" << v << "'" << std::endl;
        }
    });

    std::string l_account_config_filename(
                pal::fs::join(
                    {pal::fs::dirname(l_filename), "account", "account_config"}));
    pal::json::walk_file(l_account_config_filename, [&](
                const std::string &k,
                const std::string &v) {
        if (k == "user_id") {
            l_new_user_id = v;
        } else if (k == "user_name") {
            l_new_user_name = v;
        } else {
            std::cout << "unknown: '" << k << "': '" << v << "'" << std::endl;
        }
    });

    device.hostnames = l_new_hostnames;
    account.user_id = l_new_user_id;
    account.user_name = l_new_user_name;
}
