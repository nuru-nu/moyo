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

const cv::Vec3b USER_COLORS[] = {cv::Vec3b(255, 0, 0), // Blue
							 	 cv::Vec3b(0, 255, 0), // Green
							 	 cv::Vec3b(0, 0, 255), // Red
                                 cv::Vec3b(255, 255, 0), // Yellow
                                 cv::Vec3b(0, 255, 255), // Cyan / Aqua
                                 cv::Vec3b(255, 0, 255), // Magenta / Fuchsia
                                 cv::Vec3b(192, 192, 192), // Silver
                                 cv::Vec3b(128, 128, 128), // Gray
                                 cv::Vec3b(128, 0, 0), // Maroon
                                 cv::Vec3b(128, 128, 0), // Olive
                                 cv::Vec3b(0, 128, 0), // Green
                                 cv::Vec3b(128, 0, 128), // Purple
                                 cv::Vec3b(0, 128, 128), // Teal
                                 cv::Vec3b(0, 0, 128) }; // Navy 

const cv::Scalar USER_LINE_COLORS[] = { (255, 0, 0, 255), // Blue
							 	   		(0, 255, 0, 255), // Green
							 	   		(0, 0, 255, 255), // Red
                                   		(255, 255, 0, 255), // Yellow
                                   		(0, 255, 255, 255), // Cyan / Aqua
                                   		(255, 0, 255, 255), // Magenta / Fuchsia
                                   		(192, 192, 192, 255), // Silver
                                   		(128, 128, 128, 255), // Gray
                                   		(128, 0, 0, 255), // Maroon
                                   		(128, 128, 0, 255), // Olive
                                   		(0, 128, 0, 255), // Green
                                   		(128, 0, 128, 255), // Purple
                                   		(0, 128, 128, 255), // Teal
                                   		(0, 0, 128, 255) }; // Navy 

#endif