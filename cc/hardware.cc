#include "hardware.h"

#include <iostream>
#include <string>
#include <stdio.h>
#include <unistd.h>

#ifdef USE_PCL
#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <pcl/console/print.h>
#include <pcl/console/parse.h>
#include <pcl/console/time.h>
#endif

#include "util.h"


Hardware::Hardware(const bool simulate) : simulate_(simulate) {
  if (simulate_) {
    std::cerr << "SIMULATING kinect data" << std::endl;
    simulated_depth_ = cv::Mat(480, 640, CV_32FC1);
    simulated_ir_ = cv::Mat(480, 640, CV_32FC1);
    simulated_rgb_ = cv::Mat(480, 640, CV_8UC4);
    return;
  }

#ifndef USE_NITE
  std::cerr << "### Must be called with --simulate or compiled with USE_NITE"
    << std::endl;
  exit(-1);
#else

  nite::NiTE::initialize();

  niteRc_ = userTracker_.create();
  if (niteRc_ != nite::STATUS_OK)
  {
      printf("niteRc %d \n", niteRc_);
      printf("Couldn't create user tracker\n");
  }
#endif
}

int Hardware::next() {
#ifdef USE_PCL
  if(recording)
    recorder();
#endif

  if (simulate_) {
    usleep(1e6 / 60);
    return 0;
  }

#ifdef USE_NITE
  return userTracker_.readFrame(&userTrackerFrame_);
#endif
  std::cerr << "### Hardware::next()" << std::endl;
  exit(-1);
}

#ifdef USE_PCL
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
#endif

cv::Mat Hardware::depth() {
  if (simulate_) return simulated_depth_;
#ifdef USE_NITE
  depthFrame_ = userTrackerFrame_.getDepthFrame();

  openni::DepthPixel *depthPixels = new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];
  memcpy(depthPixels, depthFrame_.getData(), depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  return depthImage;
#endif
  std::cerr << "### Hardware::depth()" << std::endl;
  exit(-1);
}

// cv::Mat Hardware::rgb() {
// if (simulate_) return simulated_rgb_;
//   const libfreenect2::Frame* const rgb = frames_[libfreenect2::Frame::Color];
//   return cv::Mat(rgb->height, rgb->width, CV_8UC4, rgb->data).clone();
// }

// cv::Mat Hardware::ir() {
// if (simulate_) return simulated_ir_;
//   const libfreenect2::Frame* const ir = frames_[libfreenect2::Frame::Ir];
//   return cv::Mat(ir->height, ir->width, CV_32FC1, ir->data).clone();
// }

void Hardware::close() {
  if (simulate_) return;
#ifdef USE_NITE
  depthFrame_.release();
  nite::NiTE::shutdown();
#endif
}

#ifdef USE_PCL
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
#endif

