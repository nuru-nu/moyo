#include <iostream>
#include <signal.h>

#include <opencv2/opencv.hpp>

#include "features.h"
#include "hardware.h"
#include "network.h"
#include "util.h"
#include "viewer.h"

const int kSignalinPort = 6101;
bool running = true;

void sigint_handler(int s) {
  std::cerr << "Caught CTRL-C : Shutting down..." << std::endl;
  running = false;
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
  }

  hardware.close();
  return 0;
}
