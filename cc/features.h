#ifndef SMANMI_FEATURES_H
#define SMANMI_FEATURES_H

#include <opencv2/opencv.hpp>

class Features {
  public:
    Features() {}
    void process(const cv::Mat& depth);
    float presence() const { return presence_; }
    void reset() { should_reset_ = true; }
  private:
    cv::Mat background_;
    bool should_reset_ = true;
    float presence_;
};

#endif
