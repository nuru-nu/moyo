#ifndef SMANMI_NETWORK_H
#define SMANMI_NETWORK_H

#include <map>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>

using Values = std::map<std::string, float>;

class SignalSender {
  public:
    // Fails if socket cannot be created;
    SignalSender(int signal_port, int cmd_port, const char* ip = "127.0.0.1");
    // Returns numbers of bytes sent.
    int send(const Values& values);
  private:
    const int signal_port_, cmd_port_;
    int signal_sock_, cmd_sock_;
    sockaddr_in signal_addr_, cmd_addr_;
    Values overrides_;
};

#endif
