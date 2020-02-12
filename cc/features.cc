#include "features.h"

const float kFps = 50;
const float kTimeConstant = 10 * kFps;
const float kScaling = 1000;

void Features::process(const cv::Mat& depth) {
  if (should_reset_) {
    background_ = depth.clone();
    should_reset_ = false;
  }
  background_ = background_ + (depth - background_) / kTimeConstant;
  const cv::Mat diff = cv::abs(background_ - depth);
  presence_ = cv::mean(diff)[0] / kScaling;
}
