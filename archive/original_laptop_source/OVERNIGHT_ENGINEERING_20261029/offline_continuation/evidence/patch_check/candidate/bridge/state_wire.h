#pragma once
#include <cstdint>
#include <string>
#include <utility>
namespace forcat {
// Nonblocking state stdout. Never interleave partial lines: one in-flight line
// plus one replaceable latest pending line, bounded at2*16384bytes. Sink returns
//0 on EAGAIN and<0 on terminal failure. All calls are on the inference thread.
class StateWire {
 std::string active_,pending_;size_t offset_=0;bool failed_=false;uint64_t dropped_=0;
 public:
 template<class Sink>bool flush(Sink sink){
   if(failed_)return false;
   if(active_.empty()){active_=std::move(pending_);pending_.clear();offset_=0;}
   if(active_.empty())return true;
   const auto n=sink(active_.data()+offset_,active_.size()-offset_);
   if(n<0 || static_cast<size_t>(n)>active_.size()-offset_){failed_=true;return false;}
   offset_+=static_cast<size_t>(n);
   if(offset_==active_.size()){active_.clear();offset_=0;}
   return true;
 }
 template<class Sink>bool offer(std::string line,Sink sink){
   if(line.size()>16383 || line.find('\n')!=std::string::npos)return false;
   if(!pending_.empty())++dropped_;
   pending_=std::move(line);pending_+='\n';return flush(sink);
 }
 size_t buffered()const{return active_.size()+pending_.size();}
 uint64_t dropped()const{return dropped_;}
 bool failed()const{return failed_;}
};
}
