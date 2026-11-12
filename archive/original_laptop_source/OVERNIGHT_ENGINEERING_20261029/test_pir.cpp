#include "m4/pir_telemetry.h"
#include <iostream>
#include <stdexcept>
#include <cstdint>
unsigned count=0;
void check(bool v) { ++count; if(!v)throw std::runtime_error("PIR assertion failed"); }
int main() {
  for(uint32_t boot : {0u,UINT32_MAX-30000u}) {
    m4::PirTelemetry p; p.begin(true,boot);
    check(!p.valid() && p.warming(boot));
    p.sample(true,boot+59999);check(!p.valid());
    p.sample(true,boot+60000);check(p.valid() && p.motion() && !p.warming(boot+60000));
    p.sample(false,boot+60001);check(!p.valid());
    p.sample(true,boot+60050);check(!p.valid());
    p.sample(false,boot+60080);p.sample(false,boot+60179);check(!p.valid());
    p.sample(false,boot+60180);check(p.valid() && !p.motion());
    // A restart at a high level starts warm-up again; it is not a feed edge.
    p.begin(true,boot+62000);check(!p.valid() && p.warming(boot+62000));
  }
  std::cout<<"PIR_TELEMETRY_PASS assertions="<<count<<" fake_clock_only=true\n";
}
