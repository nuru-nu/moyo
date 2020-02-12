#ifndef SMANMI_VIEWER_H
#define SMANMI_VIEWER_H

#include <chrono>

#include <opencv2/opencv.hpp>

#include "features.h"

class Viewer {
  public:
    Viewer();
    void update(const cv::Mat& img, const Features& features);
    bool should_quit() const { return should_quit_; }
    bool should_reset() const { return should_reset_; }

  private:
    void draw_process_key();
    void update_graphs(const cv::Mat& img, const Features& features);

    float hz_;
    std::chrono::high_resolution_clock::time_point t0_, last_t_;
    bool should_quit_ = false;
    bool should_reset_ = false;
    float last_presence_x_ = 0;
    cv::Mat graphs_;
};

#endif
