#include "hardware.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <stdio.h>

#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <pcl/console/print.h>
#include <pcl/console/parse.h>
#include <pcl/console/time.h>

#include "util.h"
#include "jute.h"

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

  std::string default_trafo_path = "../../blender/data/kinect_trafo.json";
  load_extrinsic_matrix(default_trafo_path);
}

void Hardware::load_extrinsic_matrix(std::string path){
  std::ifstream in(path);
  std::string str = "";
  std::string tmp;

  printf("Loading trafo %s \n", path.c_str());

  if(in.fail()) {
    printf("\n### FATAL : Cannot open trafo file !!\n\n");
    exit(1);
  }
  while (getline(in, tmp)) str += tmp;

  jute::jValue v = jute::parser::parse(str);
  printf("scan_name=%s\n", v["scan_name"].as_string().c_str());
  if (v["world_matrix"].size() != 4 || v["world_matrix"][0].size() != 4) {
    printf("\n### FATAL : Expected world_matrix of dimension 4x4 !!\n\n");
    exit(1);
  }
  for(int rdx=0; rdx<v["world_matrix"].size(); rdx++) {
    for(int cdx=0; cdx<v["world_matrix"][0].size(); cdx++) {
      trafo_.at<double>(rdx, cdx) = v["world_matrix"][rdx][cdx].as_double();
    }
  }
}

void Hardware::recorder(){

  pointclouds_.push_back(pcl());
  rec_names_.push_back(datetime_str());

  if (int(rec_names_.size()) == nr_rec_frames_){
    for(int i = 0; i < int(rec_names_.size()); i++){
      // std::cout << "pcl_" + rec_names_[i] << std::endl;
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

  const nite::Array<nite::UserData>& users = userTrackerFrame_.getUsers();

  return userTracker_.readFrame(&userTrackerFrame_);
}

cv::Mat Hardware::get_user_pixels(){
  const nite::UserMap& userLabels = userTrackerFrame_.getUserMap();

  cv::Mat user_pixels(depthFrame_.getHeight(),
                      depthFrame_.getWidth(),
                      CV_8UC3, cv::Scalar(0,0,0));

  const nite::UserId* pLabels = userLabels.getPixels();
  for (int y = 0; y < depthFrame_.getHeight(); ++y) {
    for (int x = 0; x < depthFrame_.getWidth(); ++x, ++pLabels){
      if (*pLabels != 0){
        int nr_colors = (sizeof(USER_COLORS)/sizeof(*USER_COLORS));
        cv::Scalar color = USER_COLORS[(*pLabels - 1)%nr_colors];
        cv::Vec3b vec_color{
          static_cast<unsigned char>(color(0)),
          static_cast<unsigned char>(color(1)),
          static_cast<unsigned char>(color(2))
        };
        user_pixels.at<cv::Vec3b>(y, x) = vec_color;
      }
    }
  }
  // delete pLabels;
  return user_pixels;
}

std::vector<person_t> Hardware::get_tracking_data() {
  const nite::Array<nite::UserData>& users = userTrackerFrame_.getUsers();

  cv::Mat depthImage = this->depth();
  std::vector<person_t> people;
  for (int i = 0; i < users.getSize(); ++i)
  {
    person_t person;

    const nite::UserData& user = users[i];
    update_user_state(user, userTrackerFrame_.getTimestamp());
    if (user.isNew())
    {
      userTracker_.startSkeletonTracking(user.getId());
    }
    person.id = user.getId();

    float x, y, z, xd, yd;
    convertJointCoordinatesToDepth(user.getCenterOfMass().x,
                                   user.getCenterOfMass().y,
                                   user.getCenterOfMass().z,
                                   &xd, &yd);

    convertDepthCoordinatesToWorld(int(yd), int(xd), user.getCenterOfMass().z , x, y, z);

    cv::Matx41d loc(x, y, z, 1);
    cv::Mat local_point = trafo_*loc;

    x = local_point.at<double>(0,0);
    y = local_point.at<double>(0,1);
    z = local_point.at<double>(0,2);

    person.depth.insert(std::pair<std::string, float>("cm_depth",
                                                  user.getCenterOfMass().z));

    person.points3d.insert(std::pair<std::string, cv::Point3d>("cm",
                                                  cv::Point3d((float) x,
                                                              (float) y,
                                                              (float) z)));
    if(false){ // Skeletal tracking not implemented
      std::cout << "Point3d - " <<
                      (float) x << ", " <<
                      (float) y << ", " <<
                      (float) z << ". cm_depth = " << user.getCenterOfMass().z << std::endl;

      if (user.getSkeleton().getState() == nite::SKELETON_TRACKED)
      {
        const nite::SkeletonJoint& head = user.getSkeleton().getJoint(nite::JOINT_HEAD);
        if (head.getPositionConfidence() > .5)
          printf("%d. (%5.2f, %5.2f, %5.2f) - Head found with condfidence %5.2f\n", user.getId(), head.getPosition().x, head.getPosition().y, head.getPosition().z, head.getPositionConfidence());
      } else {
        printf("%d. (%5.2f, %5.2f, %5.2f)\n", user.getId(), user.getCenterOfMass().x, user.getCenterOfMass().y, user.getCenterOfMass().z);
      }
    }

    people.push_back(person);
  }
  
  delete depthImage.data;
  return people;
}

cv::Mat Hardware::depth() {
  depthFrame_ = userTrackerFrame_.getDepthFrame();

  openni::DepthPixel *depthPixels =
            new openni::DepthPixel[depthFrame_.getHeight()*depthFrame_.getWidth()];

  memcpy(depthPixels, depthFrame_.getData(),
                      depthFrame_.getHeight()*depthFrame_.getWidth()*sizeof(uint16_t));

  cv::Mat depthImage(depthFrame_.getHeight(), depthFrame_.getWidth(), CV_16U, depthPixels);

  return depthImage;
}

pcl::PointCloud<pcl::PointXYZ>::Ptr Hardware::pcl(){

  cv::Mat depthImage = Hardware::depth();

  pcl::PointCloud<pcl::PointXYZ>::Ptr pointcloud(new pcl::PointCloud<pcl::PointXYZ>);

  pointcloud->width = depthImage.size().width; //Dimensions must be initialized to use 2-D indexing
  pointcloud->height = depthImage.size().height;

  for (int xd = 0; xd < pointcloud->width; xd++){
    for(int yd = 0; yd < pointcloud->height; yd++){
      pcl::PointXYZ vertex;

      // find the world coordinates
      float x, y, z;
      int depth_value = (int) depthImage.at<unsigned short>(yd, xd);  ///                     PROPABLY SWITCHED I AND J. FIX later...
      convertDepthCoordinatesToWorld(yd, xd, depth_value, x, y, z);

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
  std::cout << "Storing pcl to " << path + "/pcl_" + datetime_str() + ".ply" << std::endl;
  writer.write(path + "/pcl_" + datetime_str() + ".ply", *pointcloud, false, false);
}

void Hardware::close() {
  depthFrame_.release();
  userTracker_.destroy();
  nite::NiTE::shutdown();
}

void Hardware::convertDepthCoordinatesToWorld(int r, int c, float depth,
                                              float &x, float &y, float &z) const {

  const float cx = 256.684;
  const float cy = 207.085;
  const float fx = 366.193;
  const float fy = 366.193;

  const float bad_point = std::numeric_limits<float>::quiet_NaN();
  // const float cx(depth.cx), cy(depth.cy);
  // const float fx(1/depth.fx), fy(1/depth.fy);
  // float* undistorted_data = (float *)undistorted->data;

  const float depth_val = depth / 1000.0f; //scaling factor, so that value of 1 is one meter.

  // std::cout << "depth_val: " << depth_val << std::endl;

  x = -(c + 0.5 - cx) * fx * depth_val / 100000.0f;
  y = (r + 0.5 - cy) * fy * depth_val / 100000.0f;
  z = depth_val;
}

void Hardware::convertJointCoordinatesToDepth(float x, float y, float z,
                                              float* pOutX, float* pOutY) const {

  userTracker_.convertJointCoordinatesToDepth(x, y, z, pOutX, pOutY);
}

void Hardware::convertJointCoordinatesToWorld(float x, float y, float z,
                                              float &tx, float &ty, float &tz) const {

  convertDepthCoordinatesToWorld(x, y, z, tx, ty, tz);

  cv::Matx41d loc(tx, ty, tz, 1);
  cv::Mat local_point = trafo_*loc;

  tx = local_point.at<double>(0,0);
  ty = local_point.at<double>(0,1);
  tz = local_point.at<double>(0,2);

  if(isnan(tx) || isnan(ty) || isnan(tz)){
    tx = 0;
    ty = 0;
    tz = 0;
  }
}

void Hardware::convertDepthCoordinatesToJoint(int x, int y, int z,
                                              float* pOutX, float* pOutY) const {

  userTracker_.convertDepthCoordinatesToJoint(x, y, z, pOutX, pOutY);
}
