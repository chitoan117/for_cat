#pragma once
#include "Arduino.h"
#include <cstring>
#include <cstdlib>
class Preferences {
 public:
  bool begin(const char* name,bool read_only) {
    host_board::other_work(); prefix_=std::string(name)+"/"; read_only_=read_only;
    if (!host_board::nvs_available || (read_only && host_board::nvs_read_failure)) return false;
    if (!read_only) return true;
    for (const auto& entry:host_board::nvs) if (entry.first.find(prefix_)==0) return true;
    return false;
  }
  bool isKey(const char* key) const { return host_board::nvs.count(prefix_+key)!=0; }
  std::size_t getBytesLength(const char* key) const {
    const auto i=host_board::nvs.find(prefix_+key); return i==host_board::nvs.end()?0:i->second.size();
  }
  std::size_t getBytes(const char* key,void* output,std::size_t count) const {
    const auto i=host_board::nvs.find(prefix_+key);
    if (i==host_board::nvs.end() || count<i->second.size()) return 0;
    std::memcpy(output,i->second.data(),i->second.size()); return i->second.size();
  }
  std::size_t putBytes(const char* key,const void* input,std::size_t count) {
    host_board::other_work();
    if (read_only_ || !host_board::nvs_available || host_board::nvs_write_failure) return 0;
    if (count>256 || prefix_.size()+std::strlen(key)>96 ||
        (host_board::nvs.count(prefix_+key)==0 && host_board::nvs.size()>=16)) return 0;
    if (host_board::nvs_crash_stage==1) std::_Exit(91);
    const auto* bytes=static_cast<const std::uint8_t*>(input);
    const auto previous=host_board::nvs;
    const auto stored=host_board::nvs_short_write?count/2:count;
    host_board::nvs[prefix_+key]=std::vector<std::uint8_t>(bytes,bytes+stored);
    if (host_board::nvs_commit && !host_board::nvs_commit()) { host_board::nvs=previous; return 0; }
    ++host_board::nvs_writes;
    if (host_board::nvs_crash_stage==2 || host_board::nvs_crash_stage==3) std::_Exit(92);
    return stored;
  }
  void end() {}
 private:
  std::string prefix_;
  bool read_only_=true;
};
