#pragma once

#include <pal/log.h>
#include "./rrplayer_client.h"

#include <QMainWindow>

class QListWidget;
class QLineEdit;
class QLabel;
class QEvent;
class QCloseEvent;
class QListWidgetItem;

class rrplayer_mainwindow
        : public QMainWindow
        , private pal::log::logger
        , private rrp_client::handler {

    Q_OBJECT

    QListWidget        *m_lst_messages = nullptr;
    QLabel             *m_lbl_current_track = nullptr;
//    QLineEdit          *m_txt_search = nullptr;
//    QListWidget        *m_lst_search_result = nullptr;
    rrp_client          m_client;

public:
    explicit rrplayer_mainwindow(QWidget *parent = 0);
    virtual ~rrplayer_mainwindow();
    rrplayer_mainwindow(const rrplayer_mainwindow&) = delete;
    rrplayer_mainwindow & operator=(const rrplayer_mainwindow&) = delete;

private:
    void log_output(
            const std::string       &message,
                  pal::log::level_t  level);
    QWidget * loadUiFile();
    bool event(QEvent *event) override;
    void closeEvent(QCloseEvent *event) override;
    void on_initialized();
    void server_message(const std::string &) override;

private slots:
    void add_log_line(const QString &);
    void on_server_message(const QString &);
    void on_pb_play_clicked();
    void on_pb_stop_clicked();
    void on_pb_skip_clicked();
    void on_pb_upvote_clicked();
    void on_pb_ban_clicked();
    void on_pb_add_clicked();
//    void on_txt_search_textChanged(const QString &text);
//    void on_txt_search_returnPressed();
//    void on_lst_search_result_itemClicked(QListWidgetItem *);
};
