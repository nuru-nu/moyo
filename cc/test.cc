#include <iostream>
#include <vector>

#include <opencv2/opencv.hpp>

void dump(const char* const name, const cv::Mat& mat) {
  std::cerr << name << " : "
    << mat.rows << 'x' << mat.cols << 'x' << mat.channels()
    << std::endl;
}

void mix(const cv::Mat& overlay, cv::Mat* img) {
  std::vector<cv::Mat> rgba;
  cv::split(overlay, rgba);
  cv::Mat rgb;
  cv::cvtColor(overlay, rgb, cv::COLOR_RGBA2RGB);
  // img->setTo(cv::Scalar(0, 0, 0), rgba[3]);
  rgb.copyTo(*img, rgba[3]);
}

void mix2(const cv::Mat& overlay, cv::Mat* img) {
  std::vector<cv::Mat> rgba;
  cv::split(overlay, rgba);
  cv::Mat rgb;
  cv::cvtColor(overlay, rgb, cv::COLOR_RGBA2RGB);

  cv::Mat alpha = cv::Mat(rgb.rows, rgb.cols, CV_8UC1, 255);
  cv::subtract(alpha, rgba[3], alpha);
  rgb.setTo(cv::Scalar(0, 0, 0), alpha);

  img->setTo(cv::Scalar(0, 0, 0), rgba[3]);
  cv::add(*img, rgb, *img);
}

void add(const cv::Mat& overlay, cv::Mat* img) {
  std::vector<cv::Mat> rgba;
  cv::split(overlay, rgba);
  cv::Mat rgb;
  cv::cvtColor(overlay, rgb, cv::COLOR_RGBA2RGB);
  cv::add(*img, rgb, *img);
}

int main() {
  cv::namedWindow("test", cv::WINDOW_AUTOSIZE);
  cv::Mat img = cv::Mat::zeros(600, 800, CV_8UC3);
  img.setTo(cv::Scalar(0, 255, 0));

  cv::Mat overlay = cv::Mat::zeros(600, 800, CV_8UC4);
  cv::putText(
      overlay, "test", cv::Point(10, 40),
      cv::FONT_HERSHEY_TRIPLEX, 1,
      cv::Scalar(0, 0, 255, 255));
  mix(overlay, &img);

  overlay = cv::Mat::zeros(600, 800, CV_8UC4);
  cv::putText(
      overlay, "test", cv::Point(10, 70),
      cv::FONT_HERSHEY_TRIPLEX, 1,
      cv::Scalar(0, 0, 255, 255));
  mix2(overlay, &img);

  overlay.setTo(0);
  cv::putText(
    overlay, "test", cv::Point(10, 100),
    cv::FONT_HERSHEY_TRIPLEX, 1,
    cv::Scalar(0, 0, 255, 255));
  add(overlay, &img);

  cv::imshow("viewer", img);
  dump("img", img);
  cv::waitKey(0);
  return 0;
}
