#include "hardware.h"

#include <iostream>
#include <string>
#include <stdio.h>

#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <pcl/console/print.h>
#include <pcl/console/parse.h>
#include <pcl/console/time.h>

namespace {

const bool kEnableDepth = true;

}  // namespace

Hardware::Hardware(const bool rgb) : rgb_(rgb) {
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
    listener_->release(frames_);
  }
  return listener_->waitForNewFrame(frames_, 10 * 1000);
}

cv::Mat Hardware::depth() {
  const libfreenect2::Frame* const depth = frames_[libfreenect2::Frame::Depth];
  return cv::Mat(depth->height, depth->width, CV_32FC1, depth->data).clone();
}

cv::Mat Hardware::rgb() {
  const libfreenect2::Frame* const rgb = frames_[libfreenect2::Frame::Color];
  return cv::Mat(rgb->height, rgb->width, CV_8UC4, rgb->data).clone();
}

cv::Mat Hardware::ir() {
  const libfreenect2::Frame* const ir = frames_[libfreenect2::Frame::Ir];
  return cv::Mat(ir->height, ir->width, CV_32FC1, ir->data).clone();
}

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

void Hardware::write_pcl(std::string path, pcl::PointCloud<pcl::PointXYZRGBA>::Ptr pointcloud){

    pcl::PLYWriter writer;
    writer.write(path, *pointcloud, false, false);
}


void Hardware::close() {
  dev_->stop();
  dev_->close();
}

