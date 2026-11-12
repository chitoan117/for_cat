#include "telemetry.h"
#include <fstream>
#include <iostream>
int main(int argc,char** argv){
 try{
  if(argc!=2)return 2;
  std::ifstream in(argv[1]);std::string line;unsigned frames=0;
  while(std::getline(in,line))if(!line.empty() && line[0]=='{'){
   auto t=forcat::parseTelemetry(line);++frames;
   if(forcat::boolean(forcat::field(t.normalized.get(),"safety"),"actuator_execution"))return 3;
  }
  if(frames!=2)return 4;
  std::cout<<"Existing bridge accepts "<<frames<<" quad diagnostic frames; synthetic software compatibility only\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
