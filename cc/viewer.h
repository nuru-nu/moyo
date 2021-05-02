#ifndef SMANMI_VIEWER_H
#define SMANMI_VIEWER_H

#include <chrono>

#include <opencv2/opencv.hpp>

#include "settings.h"
#include "features.h"

#include <chrono>
#include <thread>
#include <functional>


// Shows Kinect data and lets change parameters via keyboard.
// In the default GUI mode, the data is shown in a OpenCV window. If GUI mode
// is disabled, then data is stored upon request in a file `kinect_frame.jpg`.
// In both modes input is taken directly from the keyboard.
class Viewer {
  public:
    Viewer(bool gui = true);
    void update(const cv::Mat& img, 
                const Features& features, 
                const cv::Mat user_pixels,
                std::map<int, cv::Point2i>& depth_seg_cos);
    bool should_quit() const { return should_quit_; }
    bool should_store() const { return should_store_; }
    bool should_record() const { return should_record_; }
    bool should_reset() const { return should_reset_; }

  private:
    void draw_process_key();
    void update_graphs(const cv::Mat& img, 
                       const Features& features,
                       const std::vector<person_t>& people);

    const bool gui_;
    float hz_;
    std::chrono::high_resolution_clock::time_point t0_, last_t_, last_img_store_t_;
    bool should_quit_ = false;
    bool should_store_ = false;
    bool should_record_ = false;
    bool should_reset_ = false;
    bool should_ref_img_ = false;
    bool should_dump_ = false;
    float last_presence_x_ = 0;
    int frame_idx = 0;

    std::vector<float> last_depths_ = {0, 0, 0, 0, 0, 0, 
                                       0, 0 ,0 ,0, 0, 0};

    cv::Mat graphs_;

};

#endif
