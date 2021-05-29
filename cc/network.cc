#include "network.h"

#include <arpa/inet.h>
#include <fcntl.h>
#include <iostream>
#include <sstream>
#include <strings.h>
#include <math.h>

#include "jute.h"

SignalSender::SignalSender(
    const int signal_port, const int cmd_port, const char* const ip)
  : signal_port_(signal_port), cmd_port_(cmd_port)
{

  signal_sock_ = socket(AF_INET, SOCK_DGRAM, 0);
  if(signal_sock_ < 0){
    std::cerr << "### Cannot open socket : errno=" << errno << std::endl;
    exit(-1);
  }
  bzero(&signal_addr_, sizeof(signal_addr_));
  signal_addr_.sin_family = AF_INET;
  signal_addr_.sin_addr.s_addr = inet_addr(ip);
  signal_addr_.sin_port = htons(signal_port_);

  cmd_sock_ = socket(AF_INET, SOCK_DGRAM, 0);
  if(cmd_sock_ < 0){
    std::cerr << "### Cannot open socket : errno=" << errno << std::endl;
    exit(-1);
  }
  int flags = fcntl(cmd_sock_, F_GETFL);
  flags |= O_NONBLOCK;
  if (fcntl(cmd_sock_, F_SETFL, flags) == -1) {
    std::cerr << "### Cannot set nonblocking : errno=" << errno << std::endl;
    exit(-1);
  }
  bzero(&cmd_addr_, sizeof(cmd_addr_));
  cmd_addr_.sin_family = AF_INET;
  cmd_addr_.sin_addr.s_addr = inet_addr(ip);
  // cmd_addr_.sin_addr.s_addr = inet_addr(INADDR_ANY);
  cmd_addr_.sin_port = htons(cmd_port_);
  if (bind(cmd_sock_, (struct sockaddr*) &cmd_addr_, sizeof(cmd_addr_)) < 0) {
    std::cerr << "### Cannot bind socket : errno=" << errno << std::endl;
    exit(-1);
  }

  std::cout << "Will send UDP to " << ip << ':' << signal_port_ << std::endl;
  std::cout << "Will receive UDP from " << ip << ':' << cmd_port_ << std::endl;
}

int SignalSender::receive(std::map<std::string, std::string>& rec_msg) {
  char msgbuf[2048];
  struct sockaddr_in addr;
  int addrlen;
  const int recv_bytes = recvfrom(
      cmd_sock_, msgbuf, sizeof(msgbuf) - 1, 0,
      (struct sockaddr*) &addr, (socklen_t*) &addrlen);
  
  std::string delimiter = "=";
  if (recv_bytes > 0) {
    msgbuf[recv_bytes] = 0;
    jute::jValue json = jute::parser::parse(msgbuf);
    for (const auto& name : json.keys()) {
      if (name != "rec_action"){
        continue;
      }

      std::string msg;
      if (json[name].get_type() == jute::JSTRING) {
        msg = static_cast<std::string>(json[name].as_string());
      } else {
        msg = "None";
      }

      size_t pos = msg.find(delimiter);
      std::string key = msg.substr(0, pos);
      msg.erase(0, pos + delimiter.length());
      rec_msg[key] = msg;
    }
  }

  return recv_bytes;
}

int SignalSender::send(const Values& values) {
  std::stringstream buf;
  jute::jValue json(jute::JOBJECT);
  for(const auto& pair : values) {
    jute::jValue value(jute::JNUMBER);
    value.set_string(std::to_string(pair.second));
    json.add_property(pair.first, value);
  }
  const std::string msg = json.to_string();

  return sendto(
      signal_sock_, msg.c_str(), msg.length(), 0, (sockaddr*)&signal_addr_,
      sizeof(signal_addr_));
}

int SignalSender::send_tracking_data(
                                    const std::map<std::string, std::vector<person_t>>& people_sigs, 
                                    const std::map<std::string, float>& values){

  jute::jValue json(jute::JOBJECT);
  for(const auto& pair : values) {
    jute::jValue value(jute::JNUMBER);
    value.set_string(std::to_string(pair.second));
    json.add_property(pair.first, value);
  }

  for(const auto& people : people_sigs){
    jute::jValue people_jarray(jute::JARRAY);
    for(const auto& person : people.second) {
      jute::jValue person_jobject(jute::JOBJECT);

      jute::jValue id_value(jute::JNUMBER);
      id_value.set_string(std::to_string(person.id));
      person_jobject.add_property("id", id_value);

      for(const auto& pair : person.depth) {
        jute::jValue value(jute::JNUMBER);
        value.set_string(std::to_string(pair.second));
        person_jobject.add_property(pair.first, value);
      }

      for(const auto& joint : person.points_3d) {
        jute::jValue point3d(jute::JARRAY);

        jute::jValue nvalue(jute::JNUMBER);
        nvalue.set_string(std::to_string(joint.second.x));
        point3d.add_element(nvalue);
        nvalue.set_string(std::to_string(joint.second.y));
        point3d.add_element(nvalue);
        nvalue.set_string(std::to_string(joint.second.z));
        point3d.add_element(nvalue);

        person_jobject.add_property(joint.first, point3d);
      }

      people_jarray.add_element(person_jobject);
    }
    json.add_property(people.first, people_jarray);
  }
  const std::string msg = json.to_string();

  // std::cout << msg << std::endl;

  return sendto(
      signal_sock_, msg.c_str(), msg.length(), 0, (sockaddr*)&signal_addr_,
      sizeof(signal_addr_));
}
