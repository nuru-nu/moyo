#ifndef SMANMI_SETTINGS_H
#define SMANMI_SETTINGS_H

#include <opencv2/opencv.hpp>
#include <opencv2/viz/types.hpp>

struct person_t {

    int id;
    std::map<std::string, float> depth;
    std::map<std::string, cv::Point3d> points_3d;
} ;

// https://documentation.help/NiTE-2.0/namespacenite.html
const std::map<std::string, auto> limbs = { 
          {"joint_head", nite::JOINT_HEAD}, 
          {"joint_neck", nite::JOINT_NECK}, 
          {"joint_left_shoulder", nite::JOINT_LEFT_SHOULDER}, 
          {"joint_right_shoulder", nite::JOINT_RIGHT_SHOULDER}, 
          {"joint_left_elbow", nite::JOINT_LEFT_ELBOW}, 
          {"joint_right_elbow", nite::JOINT_RIGHT_ELBOW}, 
          {"joint_left_hand", nite::JOINT_LEFT_HAND}, 
          {"joint_right_hand", nite::JOINT_RIGHT_HAND}, 
          {"joint_torso", nite::JOINT_TORSO}, 
          {"joint_left_hip", nite::JOINT_LEFT_HIP}, 
          {"joint_right_hip", nite::JOINT_RIGHT_HIP}, 
          {"joint_left_knee", nite::JOINT_LEFT_KNEE}, 
          {"joint_right_knee", nite::JOINT_RIGHT_KNEE}, 
          {"joint_left_foot", nite::JOINT_LEFT_FOOT}, 
          {"joint_right_foot", nite::JOINT_RIGHT_FOOT}
};

using Values = std::map<std::string, float>;

const cv::Scalar USER_COLORS[] = { {255, 0, 0, 255}, // Blue
						 	   		{0, 255, 0, 255}, // Green
						 	   		{0, 0, 255, 255}, // Red
                               		{255, 255, 0, 255}, // Yellow
                               		{0, 255, 255, 255}, // Cyan / Aqua
                               		{255, 0, 255, 255}, // Magenta / Fuchsia
                               		{192, 192, 192, 255}, // Silver
                               		{128, 128, 128, 255}, // Gray
                               		{128, 0, 0, 255}, // Maroon
                               		{128, 128, 0, 255}, // Olive
                               		{0, 128, 0, 255}, // Green
                               		{128, 0, 128, 255}, // Purple
                               		{0, 128, 128, 255}, // Teal
                               		{0, 0, 128, 255} }; // Navy 

#endif
