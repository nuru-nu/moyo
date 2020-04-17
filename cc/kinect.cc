#include "conf.h"

#include <iostream>
#include <math.h>
#include <signal.h>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <vector>

#include <opencv2/opencv.hpp>

#include "features.h"
#include "hardware.h"
#include "network.h"
#include "util.h"
#include "viewer.h"

#ifdef USE_NITE
#include "NiTE.h"
#include <NiteSampleUtilities.h>
#endif

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

  bool rgb = true, simulate = false, gui = true;
  const std::vector<std::string> args(argv + 1, argv + argc);
  for (const auto& arg : args) {
    if (arg == "--no-rgb") {
      rgb = false;
    } else if (arg == "--no-gui") {
      gui = false;
    } else if (arg == "--simulate") {
      simulate = true;
    } else if (arg == "--help") {
      std::cout << R"(kinect sensor; available options:
  --no-rgb: don't use RGB channel
  --no-gui: don't show GUI; useful if X not available
  --simulate: don't actually try to connect to Kinect
)" << std::endl;
      return 0;
    } else {
      std::cerr << "Unknown option : " << arg << std::endl;
      return -1;
    }
  }

  Hardware hardware(rgb, simulate);

  Features features;
  Viewer viewer(gui);
  SignalSender sender(kSignalinPort, kCmdPort);

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

#ifdef USE_PCL
    if (viewer.should_store()) {
      pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud = hardware.pcl();
      hardware.write_pcl("../../data/pcls", pointcloud);
    }
    if (viewer.should_record()) {
      hardware.record_pcl("../../data/pcls", 60);
    }
#endif
  }

  hardware.close();
  return 0;
}
