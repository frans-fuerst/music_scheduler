#include "./rrplayer_mainwindow.h"
#include "./rrplayer_client.h"
#include "./errors.h"

#include <pal/pal.h>
#include <pal/str.h>
#include <pal/log.h>

#include <QString>
#include <QPushButton>
#include <QListWidget>
#include <QTextEdit>
#include <QtUiTools>

#include <iostream>

#if defined(ANDROID)
#include <android/log.h>
#endif

rrplayer_mainwindow::rrplayer_mainwindow(
        QWidget *a_parent)
    : QMainWindow(a_parent)
    , pal::log::logger(
          std::bind(
              &rrplayer_mainwindow::log_output, this,
              std::placeholders::_1,
              std::placeholders::_2))
    , m_client(*this, *this) {

    QWidget *l_ui_widget = loadUiFile();
    setCentralWidget(l_ui_widget);

    m_lst_messages = l_ui_widget->findChild<QListWidget*>("lst_messages");
    m_lbl_current_track = l_ui_widget->findChild<QLabel*>("lbl_current_track");
    m_lbl_host = l_ui_widget->findChild<QLabel*>("lbl_host");
    m_sb_position = l_ui_widget->findChild<QScrollBar*>("sb_position");
    m_txt_ban_substring = l_ui_widget->findChild<QLineEdit*>("txt_ban_substring");
    m_frm_ban = l_ui_widget->findChild<QFrame*>("frm_ban");
    m_frm_search_result = l_ui_widget->findChild<QFrame*>("frm_search_result");
    m_frm_credentials = l_ui_widget->findChild<QFrame*>("frm_credentials");

    m_frm_ban->setVisible(false);
    m_frm_search_result->setVisible(false);
    m_frm_credentials->setVisible(false);

    // m_lst_search_result = l_ui_widget->findChild<QListWidget*>("lst_search_result");
    // m_txt_search = l_ui_widget->findChild<QLineEdit*>("txt_search");

    // m_txt_ban_substring->setInputMethodHints(Qt::ImhNoPredictiveText);

    // QPushButton *l_pb_add = l_ui_widget->findChild<QPushButton*>("pb_add");

    //m_lst_search_result->setVisible(false);
    resize(700, 700);
    setWindowTitle("rrplayer");

    //    m_model.setLocalFolder( QDir::homePath() + QDir::separator() + "zm-local" );

    log_i() << "version: "  << 0.1;
    log_i() << "pwd:     '" << QApplication::applicationDirPath() << "'";

    QMetaObject::connectSlotsByName(this);

    /// call show before reading geometry
    show();

    // QSize l_pbsize(m_txt_search->height(), m_txt_search->height());
    // l_pb_add->setFixedSize(l_pbsize);

    m_lbl_current_track->setText("currently");
}

rrplayer_mainwindow::~rrplayer_mainwindow() {
}

void rrplayer_mainwindow::log_output(
        const std::string       &a_message,
              pal::log::level_t  a_level) {
    std::string l_message((pal::str::str()
                           << "0x" << std::hex << std::this_thread::get_id()
                           << ":  " << a_message));
#if defined(ANDROID)
    __android_log_print(ANDROID_LOG_INFO, "rrplayer", l_message.c_str());
#else
    std::cout << l_message << std::endl;
#endif

    QMetaObject::invokeMethod(
                this, "add_log_line", Qt::QueuedConnection,
                Q_ARG(QString, QString::fromStdString(l_message.c_str())));
}

void rrplayer_mainwindow::add_log_line(const QString &a_msg) {
    if (!m_lst_messages) {
        return;
    }
    m_lst_messages->addItem(QString(a_msg));
    m_lst_messages->scrollToBottom();
}

void rrplayer_mainwindow::server_message(
        const std::string &a_msg) {
    QMetaObject::invokeMethod(
                this, "on_server_message", Qt::QueuedConnection,
                Q_ARG(QString, QString::fromStdString(a_msg)));
}

void rrplayer_mainwindow::on_server_message(const QString &a_msg) {
    auto l_values(pal::json::to_map(a_msg.toStdString()));

    //log_d() << "message:";
    for (auto &p : l_values) {
        if (p.first == "type") {
        } else if (p.first == "current_track") {
            log_i() << "current track: " << p.second;
            auto l_filename(pal::fs::basename(p.second));
            m_lbl_current_track->setText(QString::fromStdString(l_filename));
            m_current_track = QString::fromStdString(p.second);
        } else if (p.first == "track_length") {
            m_sb_position->setMaximum(static_cast<int>(QString::fromStdString(p.second).toFloat()));
        } else if (p.first == "current_pos") {
            m_sb_position->setValue(static_cast<int>(QString::fromStdString(p.second).toFloat()));
        } else {
            log_d() << "   " << p.first << ": " << p.second;
        }
    }
}

bool rrplayer_mainwindow::event(QEvent *event) {
    if (event->type() == QEvent::WindowActivate) {
        if (!m_client.is_connected()) {
            on_initialized();
        }
    }
//    if event.type() == QtCore.QEvent.WindowActivate:
//        # we abuse this event as some sort of WindowShow event
//        if not self._game_server_stub.is_connected():
//            self._on_initialized()
    return QMainWindow::event(event);
}

void rrplayer_mainwindow::on_initialized() {
    std::vector<std::string> l_hostnames = {
        "127.0.0.1",
        "mucke", "10.0.0.113",
        "brick", "10.0.0.103",
    };

    for (auto l_hostname : l_hostnames) {
        try {
            log_i() << "try connection to: '" << l_hostname << "'";
            m_client.connect(l_hostname);
            log_i() << "success!";
            m_lbl_host->setText(QString::fromStdString(l_hostname));
            return;
        } catch (rrp::error &e) {
            log_w() << "failure: '" << e.what() << "'";
        }
    }

    log_i() << "no known host reachable";
}

//void rrplayer_mainwindow::on_txt_search_textChanged(
//        const QString &text) {
//    auto l_text = text.toStdString();
//    // log_message(l_text != "" ? l_text : "empty search text!");
//    auto l_results = m_documents.search(l_text);
//    m_lst_search_result->clear();
//    if (l_results.empty()) {
//        m_lst_search_result->addItem("no results");
//    }
//    m_lst_search_result->setEnabled(!l_results.empty());
//    for (auto i : l_results) {
//        m_lst_search_result->addItem(QString().fromStdString(i));
//    }
//    m_lst_search_result->setVisible(text.length() > 0);
//    update();
//}

//void rrplayer_mainwindow::on_txt_search_returnPressed() {
//    log_message("enter");
//}

void rrplayer_mainwindow::on_pb_play_clicked() {
    log_i() << "play";
    try {
        m_client.request({{"type", "play"}});
    } catch (rrp::timeout &) {
        log_e() << "timeout";
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_pause_clicked() {
    log_i() << "pause";
    try {
        m_client.request({{"type", "pause"}});
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_stop_clicked() {
    log_i() << "stop";
    try {
        m_client.request({{"type", "stop"}});
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_skip_clicked() {
    log_i() << "skip";
    try {
        m_client.request({{"type", "skip"}});
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_upvote_clicked() {
    log_i() << "upvote";
    try {
        m_client.request({{"type", "upvote"}});
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_ban_clicked() {
    log_i() << "ban";
    m_frm_ban->setVisible(true);
    m_txt_ban_substring->setText(m_current_track);
}

void rrplayer_mainwindow::on_txt_ban_substring_selectionChanged() {
    auto l_current_selection(m_txt_ban_substring->selectedText());
    if (l_current_selection == "") {
        return;
    }
    m_selected_ban_substring = l_current_selection;
}

void rrplayer_mainwindow::on_pb_ban_crop_clicked() {
    log_i() << "ban/crop";
    m_txt_ban_substring->setText(m_selected_ban_substring);
}

void rrplayer_mainwindow::on_pb_ban_ok_clicked() {
    log_i() << "ban/ok";
    m_frm_ban->setVisible(false);

    try {
        m_client.request({{"type", "ban"},
                          {"substring", m_txt_ban_substring->text().toStdString()}});
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_ban_cancel_clicked() {
    log_i() << "ban/cancel";
    m_frm_ban->setVisible(false);
}

void rrplayer_mainwindow::on_pb_add_clicked() {
    log_i() << "add";
}

void rrplayer_mainwindow::on_pb_volup_clicked() {
    log_i() << "volume up";
    try {
        m_client.request("{\"type\": \"volup\"}");
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_voldown_clicked() {
    log_i() << "volume down";
    try {
        m_client.request("{\"type\": \"voldown\"}");
    } catch (rrp::error &) {}
}

void rrplayer_mainwindow::on_pb_connect_clicked() {
    log_i() << "connect";
}

//void rrplayer_mainwindow::on_lst_search_result_itemClicked(
//        QListWidgetItem *a_item) {
//    std::string l_doc_id(a_item->text().toStdString());
//    log_message(sstr("item clicked: '") << l_doc_id << "'");
//    m_txt_search->setText("");
//    m_documents.activate_document(l_doc_id);
//    m_txt_content->setText(
//                QString().fromStdString(m_documents.get_content()));
//    m_txt_content->setEnabled(true);
//    m_txt_content->setFocus();
//}

QWidget * rrplayer_mainwindow::loadUiFile() {
    QFile l_file;
    l_file.setFileName("rrplayer.ui");
    if(!l_file.exists()) {
        l_file.setFileName(":/rrplayer.ui");
    }
    l_file.open(QFile::ReadOnly);
    QUiLoader l_loader;
    return l_loader.load(&l_file, this);
}

void rrplayer_mainwindow::closeEvent(QCloseEvent *event) {
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
