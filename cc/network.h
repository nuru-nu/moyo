#ifndef SMANMI_NETWORK_H
#define SMANMI_NETWORK_H

#include <map>
#include <vector>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>

#include "settings.h"

class SignalSender {
  public:
    // Fails if socket cannot be created;
    SignalSender(int signal_port, int cmd_port, const char* ip = "127.0.0.1");
    // Returns numbers of bytes sent.
    int send(const Values& values);
    // Returns numbers of bytes sent.
    int send_tracking_data(const std::map<std::string, std::vector<person_t>>& people, 
                           const std::map<std::string, float>& values);

  private:
    const int signal_port_, cmd_port_;
    int signal_sock_, cmd_sock_;
    sockaddr_in signal_addr_, cmd_addr_;
    Values overrides_;
    std::vector<person_t> poverrides_;
};

#endif
