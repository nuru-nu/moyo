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

  niteRc_ = userTracker_.create();
  if (niteRc_ != nite::STATUS_OK)
  {
      printf("niteRc %d \n", niteRc_);
      printf("Couldn't create user tracker\n");
  }
}

int Hardware::next() {

  if(recording)
    recorder();

  return userTracker_.readFrame(&userTrackerFrame_);
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

cv::Mat Hardware::depth() {
  depthFrame_ = userTrackerFrame_.getDepthFrame();

  openni::DepthPixel *depthPixels = new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];
  memcpy(depthPixels, depthFrame_.getData(), depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  return depthImage;
}

// cv::Mat Hardware::rgb() {
//   const libfreenect2::Frame* const rgb = frames_[libfreenect2::Frame::Color];
//   return cv::Mat(rgb->height, rgb->width, CV_8UC4, rgb->data).clone();
// }

// cv::Mat Hardware::ir() {
//   const libfreenect2::Frame* const ir = frames_[libfreenect2::Frame::Ir];
//   return cv::Mat(ir->height, ir->width, CV_32FC1, ir->data).clone();
// }

pcl::PointCloud<pcl::PointXYZ>::Ptr Hardware::pcl(){  

  openni::DepthPixel *depthPixels = new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];
  memcpy(depthPixels, depthFrame_.getData(), depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud(new pcl::PointCloud<pcl::PointXYZ>);

  float x,y;

  pointcloud->width = depthFrame_.getWidth(); //Dimensions must be initialized to use 2-D indexing 
  pointcloud->height = depthFrame_.getHeight();

  for (int i = 0; i< pointcloud->width; i++){
    for(int j = 0; j < pointcloud->height; j++){
      pcl::PointXYZ vertex;
      int depth_value = (int) depthImage.at<unsigned short>(j,i);

      // find the world coordinates
      userTracker_.convertDepthCoordinatesToJoint(j, i, depth_value, &x, &y);

      vertex.x   = (float) x;
      vertex.y   = (float) y;
      vertex.z   = (float) depth_value;

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
