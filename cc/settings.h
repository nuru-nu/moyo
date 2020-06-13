#ifndef SMANMI_SETTINGS_H
#define SMANMI_SETTINGS_H

#include <opencv2/opencv.hpp>
#include <opencv2/viz/types.hpp>

struct person_t {

    int id;
    std::map<std::string, float> depth;
    std::map<std::string, cv::Point3d> points3d;

} ;

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