// Generated-media tooling tests ONLY. Never represent real bowls/cat behavior.
#include <opencv2/opencv.hpp>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
int main(int argc,char** argv) {
    try {
        if (argc != 2 || mkdir(argv[1],0700) != 0) throw std::runtime_error("fixture directory must be new");
        const std::string out = argv[1]; cv::Mat original(480,640,CV_8UC3,cv::Scalar(30,30,30));
        cv::rectangle(original,cv::Rect(64,48,160,144),cv::Scalar(0,0,255),2);
        cv::rectangle(original,cv::Rect(416,48,160,144),cv::Scalar(255,0,0),2);
        cv::putText(original,"SYNTHETIC TOOLING FIXTURE",cv::Point(60,440),cv::FONT_HERSHEY_SIMPLEX,0.7,cv::Scalar(255,255,255),1);
        if (!cv::imwrite(out+"/original.png",original)) throw std::runtime_error("fixture image write failed");
        cv::Mat wrong; cv::resize(original,wrong,cv::Size(320,240)); cv::imwrite(out+"/wrong_dimensions.png",wrong);
        cv::VideoWriter writer(out+"/fixture.mp4",cv::VideoWriter::fourcc('m','p','4','v'),10,original.size());
        if (!writer.isOpened()) throw std::runtime_error("MP4 fixture encoder unavailable");
        std::ofstream boxes(out+"/manual.csv"); boxes << "frame_index,class_id,confidence,x1,y1,x2,y2\n";
        for (int i = 0; i < 50; ++i) {
            cv::Mat frame = original.clone();
            cv::Rect cat;
            if (i <= 9) cat = cv::Rect(100,250-i*16,80,60);
            else if (i <= 15) cat = cv::Rect(100,90,80,60);
            else if (i <= 19) cat = cv::Rect(100,120+(i-16)*35,80,60);
            else if (i >= 22 && i <= 24) cat = cv::Rect(100,225,80,60);
            else if (i >= 43) cat = cv::Rect(450,90,80,60);
            if (cat.area() > 0) {
                boxes << i << ",15,0.9," << cat.x << ',' << cat.y << ',' << cat.x+cat.width << ',' << cat.y+cat.height << '\n';
                cv::rectangle(frame,cat,cv::Scalar(80,200,80),1);
            }
            if (i == 45) boxes << i << ",15,0.9,100,90,180,150\n";
            writer.write(frame);
        }
        writer.release(); boxes.close(); if (!boxes) throw std::runtime_error("fixture CSV write failed");
        std::cout << "SYNTHETIC fixture: 50 MP4 frames, manual rectangles, no real cat\n"; return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
