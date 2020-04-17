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

namespace {

const bool kEnableDepth = true;

}  // namespace

// std::string datetime_str(){
//   char buffer[26];
//   int millisec;
//   struct tm* tm_info;
//   struct timeval tv;

//   gettimeofday(&tv, NULL);

//   millisec = lrint(tv.tv_usec/1000.0); // Round to nearest millisec
//   if (millisec>=1000) { // Allow for rounding up to nearest second
//     millisec -=1000;
//     tv.tv_sec++;
//   }

//   tm_info = localtime(&tv.tv_sec);

//   strftime(buffer, 26, "%Y:%m:%d_%H:%M:%S", tm_info);
//   std::string dt_string = buffer;

//   return dt_string + ":" + std::to_string(millisec);
// }

Hardware::Hardware(const bool rgb, const bool simulate)
  : rgb_(rgb), simulate_(simulate) {
  freenect2_ = std::unique_ptr<libfreenect2::Freenect2>(
      new libfreenect2::Freenect2);

  int listener_types = 0;
  listener_types |= libfreenect2::Frame::Ir;
  listener_types |= libfreenect2::Frame::Depth;
  if (rgb) {
    listener_types |= libfreenect2::Frame::Color;
  }
  listener_ = std::unique_ptr<libfreenect2::SyncMultiFrameListener>(
      new libfreenect2::SyncMultiFrameListener(listener_types));

  if (simulate_) {
    std::cerr << "SIMULATING kinect data" << std::endl;
    simulated_depth_ = cv::Mat(480, 640, CV_32FC1);
    simulated_ir_ = cv::Mat(480, 640, CV_32FC1);
    simulated_rgb_ = cv::Mat(480, 640, CV_8UC4);
    return;
  }

  libfreenect2::PacketPipeline *pipeline = 0;
  const std::string serial = freenect2_->getDefaultDeviceSerialNumber();

  // If OpenGL is installed.
  pipeline = new libfreenect2::OpenGLPacketPipeline();

  if(freenect2_->enumerateDevices() == 0) {
    std::cerr << "### No device connected!" << std::endl;
    exit(-1);
  }

  dev_ = std::unique_ptr<libfreenect2::Freenect2Device>(
      pipeline
      ? freenect2_->openDevice(serial, pipeline)
      : freenect2_->openDevice(serial));
  std::cout << "device serial: " << dev_->getSerialNumber() << std::endl;
  std::cout << "device firmware: " << dev_->getFirmwareVersion() << std::endl;

  dev_->setColorFrameListener(listener_.get());
  dev_->setIrAndDepthFrameListener(listener_.get());
  if (!dev_->startStreams(kEnableDepth, kEnableDepth)) {
    std::cerr << "### Cannot start streams!" << std::endl;
    exit(-1);
  }

  registration =
    new libfreenect2::Registration(
        dev_->getIrCameraParams(), dev_->getColorCameraParams());
  libfreenect2::Frame undistorted(512, 424, 4), registered(512, 424, 4);
}

bool Hardware::next() {
  if (++frame_) {

#ifdef USE_PCL
    if(recording){
      pointclouds_.push_back(pcl());
      rec_names_.push_back(datetime_str());
    }

    if (int(rec_names_.size()) == nr_rec_frames_){
      for(int i = 0; i < int(rec_names_.size()); i++){
        std::cout << "pcl_" + rec_names_[i] << std::endl;
        pcl::PLYWriter writer;
        writer.write(rec_path + "/pcl_" + rec_names_[i] + ".ply", *pointclouds_[i], false, false);
      }
      pointclouds_.clear();
      rec_names_.clear();
      recording = false;
    }
#endif

    if (!simulate_) {
      listener_->release(frames_);
    }
  }
  if (simulate_) {
    usleep(1e6 / 60);
    return true;
  }
  return listener_->waitForNewFrame(frames_, 10 * 1000);
}

cv::Mat Hardware::depth() {
  if (simulate_) return simulated_depth_;
  const libfreenect2::Frame* const depth = frames_[libfreenect2::Frame::Depth];
  return cv::Mat(depth->height, depth->width, CV_32FC1, depth->data).clone();
}

cv::Mat Hardware::ir() {
  if (simulate_) return simulated_ir_;
  const libfreenect2::Frame* const ir = frames_[libfreenect2::Frame::Ir];
  return cv::Mat(ir->height, ir->width, CV_32FC1, ir->data).clone();
}

cv::Mat Hardware::rgb() {
  if (simulate_) return simulated_rgb_;
  const libfreenect2::Frame* const rgb = frames_[libfreenect2::Frame::Color];
  return cv::Mat(rgb->height, rgb->width, CV_8UC4, rgb->data).clone();
}

void Hardware::close() {
  if (simulate_) return;
  dev_->stop();
  dev_->close();
}

#ifdef USE_PCL
pcl::PointCloud<pcl::PointXYZRGBA>::Ptr Hardware::pcl(){

  const libfreenect2::Frame* const rgb = frames_[libfreenect2::Frame::Color];
  const libfreenect2::Frame* const depth = frames_[libfreenect2::Frame::Depth];

  // Regester color frame to depth frame
  libfreenect2::Frame undistorted(depth->width, depth->height, 4);
  libfreenect2::Frame registered(depth->width, depth->height, 4);
  libfreenect2::Frame depth2rgb(rgb->width, rgb->height + 2, 4);
  registration->apply(rgb, depth, &undistorted, &registered, true, &depth2rgb);

  pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud(new pcl::PointCloud<pcl::PointXYZRGBA>);

  float x,y,z,rgb_values;

  pointcloud->width = depth->width; //Dimensions must be initialized to use 2-D indexing 
  pointcloud->height = depth->height;

  for (int i = 0; i< depth->height; i++){
    for(int j = 0; j < depth->width; j++){
      registration->getPointXYZRGB(&undistorted, &registered, i, j, x, y, z, rgb_values);

      pcl::PointXYZRGBA vertex;
      vertex.x   = (float) x;
      vertex.y   = (float) y;
      vertex.z   = (float) z;
      const uint8_t *p = reinterpret_cast<uint8_t*> (&rgb_values);
      vertex.b = p[0];
      vertex.g = p[1];
      vertex.r = p[2];
      vertex.a = p[3];

      pointcloud->points.push_back( vertex );
    }
  }

  return pointcloud;
}

void Hardware::record_pcl(const std::string path, const int nr_frames){
  recording = true;
  nr_rec_frames_ = nr_frames;
  rec_path = path;
}

void Hardware::write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud){
  pcl::PLYWriter writer;
  writer.write(path + "/pcl_" + datetime_str() + ".ply", *pointcloud, false, false);
}

#endif
