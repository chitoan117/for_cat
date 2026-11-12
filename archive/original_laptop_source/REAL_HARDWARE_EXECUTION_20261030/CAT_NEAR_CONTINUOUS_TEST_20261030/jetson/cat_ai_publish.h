#pragma once
// Linux/Jetson C++ AI hook. Does not open UART or camera. Call once per ORIGINAL
// inference result, with its original CLOCK_MONOTONIC capture timestamp and seq.
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cstddef>
namespace cat_test_ai {
enum class Label {Cat,None,Dog,Other};
class Publisher {
    int fd_=-1;sockaddr_un addr_{};bool valid_=false;
 public:
    explicit Publisher(const char* path){
        if(!path||path[0]!='/'||std::strlen(path)>=sizeof(addr_.sun_path))return;
        addr_.sun_family=AF_UNIX;std::strcpy(addr_.sun_path,path);
        fd_=::socket(AF_UNIX,SOCK_DGRAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0);valid_=fd_>=0;
    }
    Publisher(const Publisher&)=delete;Publisher& operator=(const Publisher&)=delete;
    ~Publisher(){if(fd_>=0)::close(fd_);}
    bool publish(uint32_t source_seq,uint64_t captured_monotonic_ns,Label label,float confidence){
        if(!valid_||!source_seq||!std::isfinite(confidence)||confidence<0||confidence>1)return false;
        const char* text=label==Label::Cat?"CAT":label==Label::None?"NONE":label==Label::Dog?"DOG":"OTHER";
        char data[256];const int n=std::snprintf(data,sizeof(data),"{\"schema\":\"fc-cat-1\",\"source_seq\":%lu,\"captured_monotonic_ns\":%llu,\"label\":\"%s\",\"confidence\":%.7g}",
            static_cast<unsigned long>(source_seq),static_cast<unsigned long long>(captured_monotonic_ns),text,double(confidence));
        if(n<=0||size_t(n)>=sizeof(data))return false;
        return ::sendto(fd_,data,size_t(n),MSG_DONTWAIT|MSG_NOSIGNAL,reinterpret_cast<const sockaddr*>(&addr_),sizeof(addr_))==n;
    }
};
}
