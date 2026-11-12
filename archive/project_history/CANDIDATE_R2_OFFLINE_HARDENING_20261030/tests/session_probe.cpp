#include "diagnostic_session.h"
#include <iostream>
int main(){forcat::DiagnosticSession s;s.connection();s.accept(100,1000);s.accept(90,1100);std::cout<<"BACKWARD_UPTIME health="<<s.health(1100,3000)<<" source=SIMULATED\n";}
