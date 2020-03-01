#ifndef SMANMI_HARDWARE_H
#define SMANMI_HARDWARE_H

#include <memory>

#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/registration.h>
#include <libfreenect2/packet_pipeline.h>
#include <libfreenect2/logger.h>

// #include <pcl/io/pcd_io.h>
// #include <pcl/io/ply_io.h>
// #include <pcl/console/print.h>
// #include <pcl/console/parse.h>
// #include <pcl/console/time.h>
// #include <pcl/point_types.h>

#include <OpenNI.h>

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
    // pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pcl();  
    void pcl();  



    // Shuts down the device, irreversibly.
    void close();

  private:
    const bool rgb_;
    int frame_ = 0;
    libfreenect2::FrameMap frames_;
    std::unique_ptr<libfreenect2::Freenect2> freenect2_;
    std::unique_ptr<libfreenect2::SyncMultiFrameListener> listener_;
    std::unique_ptr<libfreenect2::Freenect2Device> dev_;
};

#endif
