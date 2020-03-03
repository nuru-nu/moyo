#include <iostream>
#include <signal.h>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>

#include <opencv2/opencv.hpp>

#include "features.h"
#include "hardware.h"
#include "network.h"
#include "util.h"
#include "viewer.h"

#include "NiTE.h"

#include <NiteSampleUtilities.h>

const int kSignalinPort = 6101;
bool running = true;

void sigint_handler(int s) {
  std::cerr << "Caught CTRL-C : Shutting down..." << std::endl;
  running = false;
}

std::string datetime_str(){
  char buffer[26];
  int millisec;
  struct tm* tm_info;
  struct timeval tv;

  gettimeofday(&tv, NULL);

  millisec = lrint(tv.tv_usec/1000.0); // Round to nearest millisec
  if (millisec>=1000) { // Allow for rounding up to nearest second
    millisec -=1000;
    tv.tv_sec++;
  }

  tm_info = localtime(&tv.tv_sec);

  strftime(buffer, 26, "%Y:%m:%d_%H:%M:%S", tm_info);
  std::string dt_string = buffer;
  std::cout << dt_string << std::endl;
  return dt_string + ":" + std::to_string(millisec);
}

int main() {
  const int signalin_port = 6101;

  Hardware hardware(/*rgb=*/true);

  Features features;
  Viewer viewer;
  SignalSender sender(kSignalinPort);

  signal(SIGINT, sigint_handler);
  while (running && !viewer.should_quit()) {
    if (!hardware.next()) {
      std::cerr << "### Timeout!" << std::endl;
      return -1;
    }

    const cv::Mat depth = hardware.depth();
    const cv::Mat rgb = hardware.rgb();

    features.process(depth);
    const int bytes_sent = sender.send({
        {"presence", features.presence()},
    });
    if (bytes_sent < 0) {
      std::cerr << "### errno=" << errno << std::endl;
    }
    viewer.update(depth, features);
    if (viewer.should_reset()) {
      features.reset();
    }

    if (viewer.should_store()) {
      pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud = hardware.pcl();
      hardware.write_pcl("../../data/pcls/pcl_" + datetime_str() + ".ply", pointcloud);
      viewer.clear_store();
    }
  }

  hardware.close();
  return 0;
}
