#pragma once
#ifdef FORCAT_BRIDGE_TEST
#include "mock_runtime.h"
#include <process.h>
struct SerialPoll {int fd;short events,revents;};
constexpr short SERIAL_IN=1,SERIAL_ERR=8,SERIAL_HUP=16,SERIAL_NVAL=32;
inline int pollSerial(SerialPoll* p,int count,int){
    auto& s=mock_io::state();s.advance();
    if(count && p){p->revents=!s.cable?SERIAL_HUP:!s.rx.empty()?SERIAL_IN:0;return p->revents?1:0;}return 0;
}
inline long readSerialBytes(int,void* target,size_t max){
    auto& q=mock_io::state().rx;auto p=static_cast<uint8_t*>(target);const size_t count=std::min(q.size(),max);
    for(size_t i=0;i<count;++i){p[i]=q.front();q.pop_front();}return static_cast<long>(count);
}
inline size_t writeSerialBytes(int,const uint8_t* p,size_t n){return mock_io::state().write(p,n);}
inline int bridgePid(){return _getpid();}
#else
#ifdef _WIN32
#error "Live Bridge is POSIX-only; Windows requires the explicit no-tty test platform"
#endif
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/timex.h>
#include <termios.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <glob.h>
using SerialPoll=pollfd;
constexpr short SERIAL_IN=POLLIN,SERIAL_ERR=POLLERR,SERIAL_HUP=POLLHUP,SERIAL_NVAL=POLLNVAL;
inline int pollSerial(SerialPoll* p,int n,int timeout){return poll(p,static_cast<nfds_t>(n),timeout);}
inline ssize_t readSerialBytes(int fd,void* p,size_t n){return read(fd,p,n);}
inline size_t writeSerialBytes(int fd,const uint8_t* p,size_t n){const auto done=write(fd,p,n);return done>0?static_cast<size_t>(done):0;}
inline int bridgePid(){return getpid();}
#endif
