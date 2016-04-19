#include "./pmpc_mainwindow.h"
#include <QApplication>

int main(int a_argsc, char *a_argsv[]) {
    QApplication l_application(a_argsc, a_argsv);
    pmpc_mainwindow l_gui;
//    l_gui.show();
    return l_application.exec();
}
