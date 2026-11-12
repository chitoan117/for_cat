#pragma once
#include <stdint.h>
// Pure decision logic; durable latch must be saved before acting on ATTEMPT.
namespace fallback_policy {
enum class Action { NONE, ATTEMPT, REARM };
struct Inputs {
  uint32_t now, distance_stamp;
  bool offline, permitted, distance_valid, pir, empty_scale;
  float cm;
};
struct Gate {
  bool used=false, pir_seen=false, clear_seen=false;
  uint8_t hits=0;
  uint32_t attempt_at=0,pir_at=0,clear_at=0,last_distance=0;
  void consumed(uint32_t now){used=true;attempt_at=now;hits=0;clear_seen=false;}
  Action step(const Inputs& s) {
    if(!s.pir) pir_seen=false;
    else if(!pir_seen){pir_seen=true;pir_at=s.now;}
    const bool fresh=s.distance_valid&&s.distance_stamp!=0&&uint32_t(s.now-s.distance_stamp)<=1200;
    if(used){
      if(fresh&&s.cm>30&&!s.pir){
        if(!clear_seen){clear_seen=true;clear_at=s.now;}
        if(s.permitted&&uint32_t(s.now-clear_at)>=5000&&uint32_t(s.now-attempt_at)>=300000)
          return Action::REARM;
      } else clear_seen=false;
      return Action::NONE;
    }
    if(!s.offline||!s.permitted||!s.empty_scale||!fresh||s.cm<2||s.cm>20||!pir_seen){hits=0;return Action::NONE;}
    if(s.distance_stamp!=last_distance){last_distance=s.distance_stamp;if(hits<3)++hits;}
    if(hits>=3&&uint32_t(s.now-pir_at)>=200) return Action::ATTEMPT;
    return Action::NONE;
  }
};
}
