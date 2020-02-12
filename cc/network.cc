#include "network.h"

#include <arpa/inet.h>
#include <iostream>
#include <sstream>

SignalSender::SignalSender(const int port, const char* const ip) : port_(port) {
  sock_ = socket(AF_INET,SOCK_DGRAM,0);
  if(sock_ < 0){
    std::cerr << "### Cannot open socket : errno=" << errno << std::endl;
    exit(-1);
  }
  bzero(&servaddr_, sizeof(servaddr_));
  servaddr_.sin_family = AF_INET;
  servaddr_.sin_addr.s_addr = inet_addr(ip);
  servaddr_.sin_port = htons(port);
}

int SignalSender::send(const std::map<std::string, float>& values) {
  std::stringstream buf;
  buf << '{';
  bool first = true;
  for(const auto& pair : values) {
    if (!first) buf << ',';
    first = false;
    buf << '"' << pair.first << '"' << ':' << pair.second;
  }
  buf << '}';
  const std::string msg = buf.str();
  return sendto(
      sock_, msg.c_str(), msg.length(), 0, (sockaddr*)&servaddr_,
      sizeof(servaddr_));
}
