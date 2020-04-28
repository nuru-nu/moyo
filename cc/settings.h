#ifndef SMANMI_SETTINGS_H
#define SMANMI_SETTINGS_H

#include <opencv2/opencv.hpp>

struct person_t {

    int id;
    std::map<std::string, cv::Point3d> points3d;
} ;

using Values = std::map<std::string, float>;


#endif