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

  ref_img_ = imread("../../data/ref_image.png", cv::IMREAD_GRAYSCALE);
  if (ref_img_.empty()) {
      std::cout << "Error : Ref image cannot be loaded!" << std::endl;
  }
  ref_img_.convertTo(ref_img_, CV_16U, 255);

  kernel_shrink_ = cv::Mat::ones(20, 20, CV_8U); 
  kernel_grow_ = cv::Mat::zeros(70, 70, CV_8U);

  for (int y = 0; y < kernel_grow_.rows; ++y) {
    kernel_grow_.at<std::uint8_t>(y, (int)(kernel_grow_.cols / 2)) = 1;
  }
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

cv::Mat Hardware::get_depth_segments(cv::Mat &depth_img){
  double min, max;

  cv::Mat diff_img;
  cv::absdiff(depth_img, ref_img_, diff_img);

  cv::erode(diff_img, diff_img, kernel_shrink_);
  cv::dilate(diff_img, diff_img, kernel_grow_);

  cv::Mat bin_img;
  cv::threshold(diff_img, bin_img, 1000, 65536, cv::THRESH_BINARY);

  bin_img.convertTo(bin_img, CV_8S);

  cv::Mat labelled_img;
  cv::connectedComponents(bin_img, labelled_img);

  cv::Mat user_pixels(depth_img.rows,
                      depth_img.cols,
                      CV_8UC3, cv::Scalar(0,0,0));

  int nr_colors = (sizeof(USER_COLORS)/sizeof(*USER_COLORS));

  std::map<int, std::vector<cv::Point2d>> depth_cos;
  for (int y = 0; y < labelled_img.rows; ++y) {
    for (int x = 0; x < labelled_img.cols; ++x){
      int label = labelled_img.at<int>(y, x);
      if(label == 0)
        continue;

      depth_cos[label].push_back(cv::Point(y, x));

      cv::Scalar color = USER_COLORS[(label - 1)%nr_colors];
      cv::Vec3b vec_color{
          static_cast<unsigned char>(color(0)),
          static_cast<unsigned char>(color(1)),
          static_cast<unsigned char>(color(2))
        };

      user_pixels.at<cv::Vec3b>(y, x) = vec_color;
    }
  }

  std::map<int, cv::Point2i> depth_seg_cos;
  for(const auto& p : depth_cos){
    cv::Point2i mean  = std::accumulate(p.second.begin(), p.second.end(), cv::Point2d(0,0));
    mean.x = (int)(mean.x / p.second.size());
    mean.y = (int)(mean.y / p.second.size());

    depth_seg_cos[p.first] = cv::Point2i(mean.y, mean.x);
  }
  depth_seg_cos_ = depth_seg_cos;

  return user_pixels;
}


std::vector<person_t> Hardware::deduce_3D_cos(cv::Mat &depth_image){
  std::vector<person_t> people;
  int idx = 0;

  for(const auto& p : depth_seg_cos_){
    person_t person;
    float x, y, z;

    convertDepthCoordinatesToWorld(int(p.second.y), int(p.second.x), depth_image.at<ushort>(int(p.second.y), int(p.second.x)), x, y, z);

    cv::Matx41d loc(x, y, z, 1);
    cv::Mat local_point = trafo_*loc;

    x = local_point.at<double>(0,0);
    y = local_point.at<double>(0,1);
    z = local_point.at<double>(0,2);

    person.id = idx;

    person.depth.insert(std::pair<std::string, float>("cm_depth", depth_image.at<ushort>(int(p.second.y), int(p.second.x))));
    
    person.points_3d.insert(std::pair<std::string, cv::Point3d>("cm",
                                                  cv::Point3d((float) x,
                                                              (float) y,
                                                              (float) z)));
    idx++;
    people.push_back(person);
  }
  return people;
}


std::vector<person_t> Hardware::get_tracking_data() {
  const nite::Array<nite::UserData>& users = userTrackerFrame_.getUsers();

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

    float x, y, z;
    convertJointCoordinatesToWorld(user.getCenterOfMass().x,
                                   user.getCenterOfMass().y,
                                   user.getCenterOfMass().z,
                                   x, y, z);

    person.depth.insert(std::pair<std::string, float>("cm_depth",
                                                  user.getCenterOfMass().z));

    person.points_3d.insert(std::pair<std::string, cv::Point3d>("cm",
                                                  cv::Point3d((float) x,
                                                              (float) y,
                                                              (float) z)));

    if (user.getSkeleton().getState() == nite::SKELETON_TRACKED)
    {
      for(const auto limb : limbs){
        const nite::SkeletonJoint& joint = user.getSkeleton().getJoint(limb.second);
        if (joint.getPositionConfidence() > .5){
          convertJointCoordinatesToWorld(joint.getPosition().x,
                                      joint.getPosition().y,
                                      joint.getPosition().z,
                                      x, y, z);
          person.points_3d.insert(std::pair<std::string, cv::Point3d>(limb.first,
                                                        cv::Point3d((float) x,
                                                                    (float) y,
                                                                    (float) z)));                                      
        }
      }
    }

    people.push_back(person);
  }
  
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

void Hardware::convertJointCoordinatesToWorld(float jx, float jy, float jz,
                                              float &x, float &y, float &z) const {

    float xd, yd;
    convertJointCoordinatesToDepth(jx, jy, jz, &xd, &yd);
    convertDepthCoordinatesToWorld(int(yd), int(xd), jz , x, y, z);

    cv::Matx41d loc(x, y, z, 1);
    cv::Mat local_point = trafo_*loc;

    x = local_point.at<double>(0,0);
    y = local_point.at<double>(0,1);
    z = local_point.at<double>(0,2);
}

void Hardware::convertDepthCoordinatesToJoint(int x, int y, int z,
                                              float* pOutX, float* pOutY) const {

  userTracker_.convertDepthCoordinatesToJoint(x, y, z, pOutX, pOutY);
}
