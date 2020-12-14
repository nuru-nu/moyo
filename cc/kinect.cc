#include <iostream>
#include <signal.h>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <math.h>

#include <opencv2/opencv.hpp>

#include "features.h"
#include "network.h"
#include "util.h"
#include "viewer.h"
#include "hardware.h"

const int kSignalinPort = 6100;
const int kCmdPort = 6111;
bool running = true;


void sigint_handler(int s) {
  std::cerr << "Caught CTRL-C : Shutting down..." << std::endl;
  running = false;
}

int main(const int argc, const char** const argv) {

#ifdef USE_PCL
  std::cout << "Compiled with USE_PCL" << std::endl;
#endif

#ifdef USE_NITE
  std::cout << "Compiled with USE_NITE" << std::endl;
#endif

  bool gui = true;
  const std::vector<std::string> args(argv + 1, argv + argc);
  for (const auto& arg : args) {
    if (arg == "--no-gui") {
      gui = false;
    } else if (arg == "--help") {
      std::cout << R"(kinect sensor; available options:
  --no-gui: don't show GUI; useful if X not available
)" << std::endl;
      return 0;
    } else {
      std::cerr << "Unknown option : " << arg << std::endl;
      return -1;
    }
  }


  Hardware hardware;

  Features features;
  Viewer viewer(gui);
  SignalSender sender(kSignalinPort, kCmdPort);

  signal(SIGINT, sigint_handler);
  while (running && !viewer.should_quit()) {
    if (hardware.next() != 0) {
      std::cerr << "### Timeout!" << std::endl;
      return -1;
    } 

    std::vector<person_t> people = hardware.get_tracking_data();
    const int bytesS = sender.send_tracking_data(
                                  people, 
                                  {{"presence", features.presence()},}); 
    if (bytesS < 0) {
      std::cerr << "### errno=" << errno << std::endl;
    }

    cv::Mat depth = hardware.depth(); 
    cv::Mat user_pixels = hardware.get_user_pixels();

    features.process(depth);
    const int bytes_sent = sender.send({
        {"presence", features.presence()},
    });
    if (bytes_sent < 0) {
      std::cerr << "### errno=" << errno << std::endl;
    }
    viewer.update(depth, features, people, user_pixels);
    if (viewer.should_reset()) {
      features.reset();
    }

    if (viewer.should_store()) {
      pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud = hardware.pcl();
      hardware.write_pcl("../../data/pcls", pointcloud);
    }

    if (viewer.should_record()) {
      hardware.record_pcl("../../data/pcls", 60);
    }
    delete depth.data;
    // delete user_pixels.data;
    // depth.release();
  }

  hardware.close();
  return 0;
}
