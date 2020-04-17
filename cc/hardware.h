#ifndef SMANMI_HARDWARE_H
#define SMANMI_HARDWARE_H

#include <memory>

#ifdef USE_PCL
#include <pcl/point_types.h>
#include <pcl/point_cloud.h>
#endif

#include <opencv2/opencv.hpp>

#ifdef USE_NITE
#include "NiTE.h"
#endif

class Hardware {
  public:
    // Also initializes Kinect and exits program in case of error.
    Hardware(bool simulate = false);

    // Waits for another frame. Returns 0 if successful, != 0 if timeout.
    int next();

    // // Returns IR data. Invalidated when `next()` is called.
    // cv::Mat ir();
    // // Returns rgb data. Invalidated when `next()` is called.
    // cv::Mat rgb();
    // Returns depth data. Invalidated when `next()` is called.
    cv::Mat depth();

    // Shuts down the device, irreversibly.
    void close();

#ifdef USE_PCL
    // Returns a point cloud.
    pcl::PointCloud<pcl::PointXYZ>::Ptr pcl();
    // Writes a pcl to file
    void write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud);
    // Starts a recording of each frame when  next() is called
    void record_pcl(const std::string path, const int nr_frames);
#endif

  private:
    const bool simulate_;
    cv::Mat simulated_depth_, simulated_ir_, simulated_rgb_;
    bool recording = false;
    int nr_rec_frames_;
    std::string rec_path_;
    std::vector<std::string> rec_names_;

#ifdef USE_NITE
    openni::VideoFrameRef depthFrame_;
    nite::UserTrackerFrameRef userTrackerFrame_;
    nite::Status niteRc_;
    nite::UserTracker userTracker_;
#endif

#ifdef USE_PCL
    std::vector<pcl::PointCloud<pcl::PointXYZ>::Ptr> pointclouds_;
    void recorder();
#endif

};

#endif
