#ifndef SMANMI_HARDWARE_H
#define SMANMI_HARDWARE_H

#include <memory>

#include <pcl/point_types.h>
#include <pcl/point_cloud.h>

#include <opencv2/opencv.hpp>

#include "NiTE.h"

class Hardware {
  public:
    // Also initializes Kinect and exits program in case of error.
    Hardware();

    // Waits for another frame. Returns `false` in case of error.
    int next();

    // // Returns IR data. Invalidated when `next()` is called.
    // cv::Mat ir();
    // // Returns rgb data. Invalidated when `next()` is called.
    // cv::Mat rgb();
    // Returns depth data. Invalidated when `next()` is called.
    cv::Mat depth();
    // Returns a point cloud.
    pcl::PointCloud<pcl::PointXYZ>::Ptr pcl();
    // Writes a pcl to file
    void write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud);
    // Starts a recording of each frame when  next() is called
    void record_pcl(const std::string path, const int nr_frames);
    // Shuts down the device, irreversibly.
    void close();

  private:   
    bool recording = false;
    int nr_rec_frames_;
    openni::VideoFrameRef depthFrame_;
    std::string rec_path_;
    std::vector<std::string> rec_names_;
    std::vector<pcl::PointCloud<pcl::PointXYZ>::Ptr> pointclouds_;

    nite::UserTrackerFrameRef userTrackerFrame_;
    nite::Status niteRc_;
    nite::UserTracker userTracker_;

    void recorder();

};

#endif
