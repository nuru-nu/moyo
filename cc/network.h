#ifndef SMANMI_NETWORK_H
#define SMANMI_NETWORK_H

#include <map>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>

class SignalSender {
  public:
    // Fails if socket cannot be created;
    SignalSender(int port, const char* ip = "127.0.0.1");
    // Returns numbers of bytes sent.
    int send(const std::map<std::string, float>& values);
  private:
    const int port_;
    int sock_;
    sockaddr_in servaddr_;
};

#endif
