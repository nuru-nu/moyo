#include "hardware.h"

#include <iostream>
#include <string>
#include <stdio.h>

#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <pcl/console/print.h>
#include <pcl/console/parse.h>
#include <pcl/console/time.h>

#include "util.h"

namespace {

const bool kEnableDepth = true;

}  // namespace


Hardware::Hardware(void) {

  nite::NiTE::initialize();

  nite::Status niteRc = userTracker_.create();
  if (niteRc != nite::STATUS_OK)
  {
      printf("niteRc %d \n", niteRc);
      printf("Couldn't create user tracker\n");
  }
}

void Hardware::recorder(){

  pointclouds_.push_back(pcl());
  rec_names_.push_back(datetime_str());

  if (int(rec_names_.size()) == nr_rec_frames_){
    for(int i = 0; i < int(rec_names_.size()); i++){
      std::cout << "pcl_" + rec_names_[i] << std::endl;
      pcl::PLYWriter writer;
      writer.write(rec_path_ + "/pcl_" + rec_names_[i] + ".ply", *pointclouds_[i], false, false);
    }
    pointclouds_.clear();
    rec_names_.clear();
    recording = false;
  }
}

void Hardware::update_user_state(const nite::UserData& user, unsigned long long ts) {
  if (user.isNew())
    USER_MESSAGE("New")
  else if (user.isVisible() && !g_visibleUsers[user.getId()])
    USER_MESSAGE("Visible")
  else if (!user.isVisible() && g_visibleUsers[user.getId()])
    USER_MESSAGE("Out of Scene")
  else if (user.isLost())
    USER_MESSAGE("Lost")

  g_visibleUsers[user.getId()] = user.isVisible();


  if(g_skeletonStates[user.getId()] != user.getSkeleton().getState())
  {
    switch(g_skeletonStates[user.getId()] = user.getSkeleton().getState())
    {
    case nite::SKELETON_NONE:
      USER_MESSAGE("Stopped tracking.")
      break;
    case nite::SKELETON_CALIBRATING:
      USER_MESSAGE("Calibrating...")
      break;
    case nite::SKELETON_TRACKED:
      USER_MESSAGE("Tracking!")
      break;
    case nite::SKELETON_CALIBRATION_ERROR_NOT_IN_POSE:
    case nite::SKELETON_CALIBRATION_ERROR_HANDS:
    case nite::SKELETON_CALIBRATION_ERROR_LEGS:
    case nite::SKELETON_CALIBRATION_ERROR_HEAD:
    case nite::SKELETON_CALIBRATION_ERROR_TORSO:
      USER_MESSAGE("Calibration Failed... :-|")
      break;
    }
  }
}

int Hardware::next() {

  if(recording)
    recorder();

  return userTracker_.readFrame(&userTrackerFrame_);
}

void Hardware::get_users() {
  const nite::Array<nite::UserData>& users = userTrackerFrame_.getUsers();

  for (int i = 0; i < users.getSize(); ++i)
  {
    const nite::UserData& user = users[i];
    update_user_state(user, userTrackerFrame_.getTimestamp());
    if (user.isNew())
    {
      userTracker_.startSkeletonTracking(user.getId());
    }
    else if (user.getSkeleton().getState() == nite::SKELETON_TRACKED)
    {
      const nite::SkeletonJoint& head = user.getSkeleton().getJoint(nite::JOINT_HEAD);
      if (head.getPositionConfidence() > .5)
        printf("%d. (%5.2f, %5.2f, %5.2f) - Head found with condfidence %5.2f\n", user.getId(), head.getPosition().x, head.getPosition().y, head.getPosition().z, head.getPositionConfidence());
    } else {
      printf("%d. (%5.2f, %5.2f, %5.2f)\n", user.getId(), user.getCenterOfMass().x, user.getCenterOfMass().y, user.getCenterOfMass().z);
    }
  }
} 

cv::Mat Hardware::depth() {
  depthFrame_ = userTrackerFrame_.getDepthFrame();

  openni::DepthPixel *depthPixels = new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];
  memcpy(depthPixels, depthFrame_.getData(), depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  return depthImage;
}

pcl::PointCloud<pcl::PointXYZ>::Ptr Hardware::pcl(){  

  openni::DepthPixel *depthPixels = new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];
  memcpy(depthPixels, depthFrame_.getData(), depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud(new pcl::PointCloud<pcl::PointXYZ>);

  float x,y,z;

  pointcloud->width = depthFrame_.getWidth(); //Dimensions must be initialized to use 2-D indexing 
  pointcloud->height = depthFrame_.getHeight();

  for (int i = 0; i< pointcloud->width; i++){
    for(int j = 0; j < pointcloud->height; j++){
      pcl::PointXYZ vertex;
      int depth_value = (int) depthImage.at<unsigned short>(j,i);

      // find the world coordinates
       // userTracker_.convertDepthCoordinatesToJoint(j, i, depth_value, &x, &y);
      convertDepthCoordinatesToWorld(j, i, depth_value, x, y, z);

      vertex.x   = (float) x;
      vertex.y   = (float) y;
      vertex.z   = (float) z;

      // the point is pushed back in the cloud
      pointcloud->points.push_back( vertex );
    }  
  }
  
  return pointcloud;
}

void Hardware::record_pcl(const std::string path, const int nr_frames){
  printf("Recording PCL\n");
  recording = true;
  nr_rec_frames_ = nr_frames;
  rec_path_ = path;
}

void Hardware::write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud){
  pcl::PLYWriter writer;
  writer.write(path + "/pcl_" + datetime_str() + ".ply", *pointcloud, false, false);
}

void Hardware::close() {
  depthFrame_.release();
  nite::NiTE::shutdown();
}

void Hardware::convertDepthCoordinatesToWorld(int r, int c, float depth, float &x, float &y, float &z) const {

  const float cx = 256.684;
  const float cy = 207.085;
  const float fx = 366.193;
  const float fy = 366.193;

  const float bad_point = std::numeric_limits<float>::quiet_NaN();
  // const float cx(depth.cx), cy(depth.cy);
  // const float fx(1/depth.fx), fy(1/depth.fy);
  // float* undistorted_data = (float *)undistorted->data;

  const float depth_val = depth/1000.0f; //scaling factor, so that value of 1 is one meter.
  if (isnan(depth_val) || depth_val <= 0.001)
  {
    //depth value is not valid
    x = y = z = bad_point;
  }
  else
  {
    x = (c + 0.5 - cx) * fx * depth_val/100000.0f;
    y = (r + 0.5 - cy) * fy * depth_val/100000.0f;
    z = depth_val;
  }
}

void Hardware::convertJointCoordinatesToDepth(float x, float y, float z, float* pOutX, float* pOutY) const {

  userTracker_.convertJointCoordinatesToDepth(x, y, z, pOutX, pOutY);
}

// void Hardware::convertJointCoordinatesToWorld(float x, float y, float z, float* pOutX, float* pOutY) const {

//   userTracker_.convertDepthCoordinatesToJoint(x, y, z, pOutX, pOutY);
//   convertDepthCoordinatesToWorld(j, i, depth_value, x, y, z);

// }

void Hardware::convertDepthCoordinatesToJoint(int x, int y, int z, float* pOutX, float* pOutY) const {

  userTracker_.convertDepthCoordinatesToJoint(x, y, z, pOutX, pOutY);
}