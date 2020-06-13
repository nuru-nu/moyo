#include "viewer.h"

#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <termios.h>
#include <unistd.h>

#include "util.h"

namespace {

const float kHzSlow = 1;
const float kHzFast = 30;
const int kGraphDy = 2;
const cv::Scalar kOriginCol4(255, 255, 255, 255);
const cv::Scalar kPresenceCol4(255, 255, 255, 255);
const cv::Scalar kTextCol(0, 255, 0);

void apply_overlay(const cv::Mat& overlay, cv::Mat* const image) {
  std::vector<cv::Mat> brga;
  cv::split(overlay, brga);
  cv::Mat overlay_brg;
  cv::cvtColor(overlay, overlay_brg, cv::COLOR_RGBA2RGB);
  // cv::add(*image, overlay_brg, *image);
  overlay_brg.copyTo(*image, brga[3]);
}

struct termios orig_termios;

void reset_terminal_mode() {
    tcsetattr(0, TCSANOW, &orig_termios);
}

// Sets character mode in stdin (instead of default line mode).
void set_conio_terminal_mode() {
    struct termios new_termios;

    /* take two copies - one for now, one for later */
    tcgetattr(0, &orig_termios);
    memcpy(&new_termios, &orig_termios, sizeof(new_termios));

    /* register cleanup handler, and set the new terminal mode */
    atexit(reset_terminal_mode);
    cfmakeraw(&new_termios);
    new_termios.c_oflag |= OPOST;
    tcsetattr(0, TCSANOW, &new_termios);
}

// Returns 0 if no keyboard stroke is available.
int kbhit() {
    struct timeval tv = { 0L, 0L };
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(0, &fds);
    return select(1, &fds, NULL, NULL, &tv);
}

// Returns character, or <0 if error occured.
int getch() {
  int r;
  unsigned char c;
  if ((r = read(0, &c, sizeof(c))) < 0) {
    return r;
  } else {
    return c;
  }
}

}  // namespace

Viewer::Viewer(const bool gui) : hz_(kHzFast), gui_(gui) {
  last_t_ = t0_ = std::chrono::high_resolution_clock::now();
  if (gui) {
    cv::namedWindow("viewer", cv::WINDOW_AUTOSIZE);
  } else {
    set_conio_terminal_mode();
    std::cerr << R"(
Commands:
  - <ENTER> : outputs information & stores a single "kinect_frame.jpg"
  - <SPACE> : reset features
  - q : quit
  - s : stores a single pointcloud
  - r : starts pointcloud recording
)" << std::endl;
  }
}

void Viewer::draw_process_key() {
  const int key = gui_ ? cv::waitKey(1) : (kbhit() ? getch() : -1);
  if (key == (int) 'q') {
    should_quit_ = true;
  }
  if (key == (int) '\t') {
    hz_ = hz_ == kHzSlow ? kHzFast : kHzSlow;
  }
  should_store_ = key == (int) 's';
  should_record_ = key == (int) 'r';
  should_reset_ = key == (int) ' ';
  should_dump_ = key == 13;
}

void Viewer::update_graphs(const cv::Mat& img, 
                           const Features& features,
                           const std::vector<person_t>& people) {
  if (graphs_.empty()) {
    graphs_ = cv::Mat::zeros(img.rows, img.cols, CV_8UC4);
  }
  cv::Mat graphs_copy = graphs_.clone();
  graphs_copy(
      cv::Rect(0, kGraphDy, graphs_.cols, graphs_.rows - kGraphDy))
    .copyTo(
        graphs_(
          cv::Rect(0, 0, graphs_.cols, graphs_.rows - kGraphDy)));
  cv::rectangle(
    graphs_,
    cv::Point(0, graphs_.rows - kGraphDy - 1),
    cv::Point(graphs_.cols - 1, graphs_.rows - 1),
    cv::Scalar(0, 0, 0, 0),
    /*thickness=fill=*/-1);

  for(int i = 0; i != people.size(); i++){
    for(const auto& pair : people[i].depth) {

      const int depth = graphs_.cols / 2 + static_cast<int>(
                                  (pair.second / 10000) * graphs_.cols / 2);

      // std::cout << " id: " << i << " - " << depth << " - " << last_depths_[i] << std::endl;
      int nr_colors = (sizeof(USER_COLORS)/sizeof(*USER_COLORS));
      cv::Scalar color = USER_COLORS[(people[i].id - 1)%nr_colors];
      cv::line(
          graphs_,
          cv::Point(depth, graphs_.rows - 1),
          cv::Point(last_depths_[i], graphs_.rows - 1 - kGraphDy),
          color,
          /*int thickness=*/2);

      last_depths_[i] = depth;
    }
  }

  const int presence_x = graphs_.cols / 2 + static_cast<int>(
      features.presence() * graphs_.cols / 2);
  cv::line(
      graphs_, cv::Point(graphs_.cols / 2, graphs_.rows - 1),
      cv::Point(graphs_.cols / 2, graphs_.rows - 1 - kGraphDy), 
      kOriginCol4,
      /*int thickness=*/1);
  cv::line(
      graphs_,
      cv::Point(presence_x, graphs_.rows - 1),
      cv::Point(last_presence_x_, graphs_.rows - 1 - kGraphDy),
      kPresenceCol4,
      /*int thickness=*/2);
  last_presence_x_ = presence_x;

  // std::cout << "pres: " << presence_x<< " - " << last_presence_x_ << std::endl;
}

void Viewer::update(const cv::Mat& img, 
                    const Features& features,
                    const std::vector<person_t>& people,
                    const cv::Mat user_pixels) {
  // Performs actual drawing. Read key every cycle for better ui.
  draw_process_key();
  update_graphs(img, features, people);

  if (!should_dump_ && !gui_) return;

  const auto t = std::chrono::high_resolution_clock::now();
  const long long microseconds =
    std::chrono::duration_cast<std::chrono::microseconds>(t - last_t_).count();
  last_t_ = t;
  const long long t0_microseconds =
    std::chrono::duration_cast<std::chrono::microseconds>(t - t0_).count();
  if (!should_dump_ && t0_microseconds < 1e6 / hz_) {
    return;
  }
  t0_ = t;

  const std::string features_string =
    string_format("presence=%.2f", features.presence());
  const double fps = 1e6 / static_cast<double>(microseconds);
  const std::string fps_string =
    string_format("fps=%.2f display_fps=%.2f", fps, hz_);

  if (gui_ || should_dump_) {
    double min, max;
    cv::Point minloc, maxloc;
    cv::minMaxLoc(img, &min, &max, &minloc, &maxloc);
    cv::Mat img_brg;
    cv::cvtColor((img - min) / (max - min), img_brg, cv::COLOR_GRAY2RGB);
    img_brg.convertTo(img_brg, CV_8UC3, /*alpha=*/255.0);

    cv::putText(
        img_brg, features_string,
        cv::Point(10, 40), cv::FONT_HERSHEY_SIMPLEX, 0.5, kTextCol);
    cv::putText(
        img_brg, fps_string,
        cv::Point(10, 70), cv::FONT_HERSHEY_SIMPLEX, 0.5, kTextCol);


    cv::addWeighted( img_brg, 0.5, user_pixels, 0.5, 0.0, img_brg);

    apply_overlay(graphs_, &img_brg);
    if (gui_) {
      cv::imshow("viewer", img_brg);
    }
    if (should_dump_) {
      cv::imwrite("kinect_frame.jpg", img_brg);
      std::cout << "Stored frame to \"kinect_frame.jpg\"" << std::endl;
    }
  }
  if (!gui_) {
    std::cout << features_string << ' ' << fps_string << std::endl;
  }
}
