#pragma once
#include <stdexcept>
#include <string>
#ifdef FORCAT_BRIDGE_TEST
#include <io.h>
#include <fcntl.h>
#include <share.h>
#include <sys/stat.h>
#else
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>
#endif
class BridgeFileLock {
    int fd_=-1;
 public:
    explicit BridgeFileLock(const std::string& path){
#ifdef FORCAT_BRIDGE_TEST
        fd_=_sopen(path.c_str(),_O_CREAT|_O_RDWR|_O_BINARY,_SH_DENYRW,_S_IREAD|_S_IWRITE);
        if(fd_<0)throw std::runtime_error("another canonical bridge owns this database");
#else
        fd_=open(path.c_str(),O_CREAT|O_RDWR|O_CLOEXEC,0600);
        if(fd_<0 || flock(fd_,LOCK_EX|LOCK_NB)<0){if(fd_>=0)close(fd_);throw std::runtime_error("another canonical bridge owns this database");}
#endif
    }
    ~BridgeFileLock(){
#ifdef FORCAT_BRIDGE_TEST
        if(fd_>=0)_close(fd_);
#else
        if(fd_>=0)close(fd_);
#endif
    }
    BridgeFileLock(const BridgeFileLock&)=delete;
    BridgeFileLock& operator=(const BridgeFileLock&)=delete;
};
