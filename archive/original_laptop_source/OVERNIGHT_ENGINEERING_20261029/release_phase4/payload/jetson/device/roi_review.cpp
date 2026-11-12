// Human ROI selection from an image (or explicitly selected future camera).
// No inference, serial, servo or pump calls. Never used by offline test runner.
#include <opencv2/opencv.hpp>
#include <fcntl.h>
#include <unistd.h>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>
int main(int argc,char** argv){
 if(argc!=3&&argc!=4){std::cerr<<"roi_review --image REAL_FRAME_IMAGE NEW_CONFIG_JSON\n(or CAMERA_DEVICE NEW_CONFIG_JSON on Jetson desktop)\n";return 2;}
 try{
   const bool image_mode=argc==4&&std::string(argv[1])=="--image";
   if(argc==4&&!image_mode)throw std::runtime_error("expected --image FILE NEW_CONFIG");
   const std::string device=image_mode?"":argv[1],path=image_mode?argv[3]:argv[2];cv::Mat frame;
   if(image_mode){frame=cv::imread(argv[2]);if(frame.empty())throw std::runtime_error("image unreadable");}
   else{
     if(device.size()<=10 || device.find("/dev/video")!=0 || device.find_first_not_of("0123456789",10)!=std::string::npos)throw std::runtime_error("expected /dev/videoN");
     cv::VideoCapture camera(device,cv::CAP_V4L2);
     if(!camera.isOpened() || !camera.read(frame) || frame.empty())throw std::runtime_error("camera unavailable; stop other camera owner first");camera.release();
   }
   const auto r=cv::selectROI("Select feeding ROI; ENTER accepts rectangle",frame,false,false);
   if(r.width<=0 || r.height<=0)throw std::runtime_error("ROI cancelled");
   cv::Mat overlay=frame.clone();cv::rectangle(overlay,r,cv::Scalar(0,0,255),2);
   cv::imshow("Review ROI: press y to save, any other key cancels",overlay);
   if((cv::waitKey(0)&255)!='y')throw std::runtime_error("ROI not reviewed");
   std::ostringstream json;json<<std::setprecision(17)<<"{\"mode\":\"ROI_ENABLED\",\"enabled\":true,\"calibrated\":true,\"review_id\":\"HUMAN_ROI_"<<std::time(nullptr)
     <<"\",\"camera_device\":\""<<device<<"\",\"width\":"<<frame.cols<<",\"height\":"<<frame.rows
     <<",\"x1\":"<<static_cast<double>(r.x)/frame.cols<<",\"y1\":"<<static_cast<double>(r.y)/frame.rows
     <<",\"x2\":"<<static_cast<double>(r.x+r.width)/frame.cols<<",\"y2\":"<<static_cast<double>(r.y+r.height)/frame.rows<<"}\n";
   const int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
   if(fd<0)throw std::runtime_error("new output file required; existing calibration is never overwritten");
   const auto body=json.str();const auto n=write(fd,body.data(),body.size());close(fd);
   if(n!=static_cast<ssize_t>(body.size()))throw std::runtime_error("ROI write failed");
   std::cout<<body;cv::destroyAllWindows();return 0;
 }catch(const std::exception& e){std::cerr<<"ROI_REVIEW_ERROR "<<e.what()<<'\n';return 1;}
}
