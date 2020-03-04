#ifndef SMANMI_HARDWARE_H
#define SMANMI_HARDWARE_H

#include <memory>

#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/registration.h>
#include <libfreenect2/packet_pipeline.h>
#include <libfreenect2/logger.h>

#include <pcl/point_types.h>
#include <pcl/point_cloud.h>

#include <opencv2/opencv.hpp>

class Hardware {
  public:
    // Also initializes Kinect and exits program in case of error.
    Hardware(bool rgb = false);

    // Waits for another frame. Returns `false` in case of error.
    bool next();

    // Returns depth data. Invalidated when `next()` is called.
    cv::Mat depth();
    // Returns IR data. Invalidated when `next()` is called.
    cv::Mat ir();
    // Returns rgb data. Invalidated when `next()` is called.
    cv::Mat rgb();
    // Returns a RGB point cloud. Invalidated when `next()` is called.
    pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pcl();
    // Writes a pcl to file
    void write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud);
    // Starts a recording of each frame when  next() is called
    void record_pcl(const std::string path, const int nr_frames);
    // Shuts down the device, irreversibly.
    void close();

  private:
    const bool rgb_;
    int frame_ = 0;
    libfreenect2::FrameMap frames_;
    std::unique_ptr<libfreenect2::Freenect2> freenect2_;
    std::unique_ptr<libfreenect2::SyncMultiFrameListener> listener_;
    std::unique_ptr<libfreenect2::Freenect2Device> dev_;
    libfreenect2::Registration* registration;
    
    bool recording = false;
    int nr_rec_frames_;
    std::string rec_path;
    std::vector<std::string> rec_names_;
    std::vector<pcl::PointCloud<pcl::PointXYZRGBA>::Ptr> pointclouds_;
};

#endif
