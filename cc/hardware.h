#ifndef SMANMI_HARDWARE_H
#define SMANMI_HARDWARE_H

#include <memory>

#include <pcl/point_types.h>
#include <pcl/point_cloud.h>

#include <opencv2/opencv.hpp>

#include "NiTE.h"

#include "settings.h"

#define MAX_USERS 10

#define USER_MESSAGE(msg) \
    {printf("[%08llu] User #%d:\t%s\n",ts, user.getId(),msg);}

class Hardware {
  public:
    // Also initializes Kinect and exits program in case of error.
    Hardware();

    int load_extrinsic_matrix(std::string path);

    // Waits for another frame. Returns `false` in case of error.
    int next();

    // Returns a list of people_t structs defined in settings.h.
    std::vector<person_t> get_tracking_data();
    // Returns depth data. Invalidated when `next()` is called.
    cv::Mat depth();
    // Returns a point cloud.
    pcl::PointCloud<pcl::PointXYZ>::Ptr pcl();
    // Writes a pcl to file
    void write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud);
    // Starts a recording of each frame when  next() is called
    void record_pcl(const std::string path, const int nr_frames);
    // Convert XYZ world coordinate from depth map val of kinect v2
    void convertDepthCoordinatesToWorld(int r, int c, float depth, float &x, float &y, float &z) const;
    // Convert joint to depth map value
    void convertJointCoordinatesToDepth(float x, float y, float z, float* pOutX, float* pOutY) const;
    // Convert depth map value to joint coordinate
    void convertDepthCoordinatesToJoint(int x, int y, int z, float* pOutX, float* pOutY) const;
    // Convert joint ot world
    void convertJointCoordinatesToWorld(float x, float y, float z, float &tx, float &ty, float &tz) const;
    // Returns a depth map size matrix with tracked user ID elements
    cv::Mat get_user_pixels();
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
    nite::UserTracker userTracker_;

    bool g_visibleUsers[MAX_USERS] = {false};
    nite::SkeletonState g_skeletonStates[MAX_USERS] = {nite::SKELETON_NONE};
    
    void recorder();
    void update_user_state(const nite::UserData& user, unsigned long long ts);

    cv::Mat trafo_ = cv::Mat::eye(4, 4, CV_64F);

};

#endif
