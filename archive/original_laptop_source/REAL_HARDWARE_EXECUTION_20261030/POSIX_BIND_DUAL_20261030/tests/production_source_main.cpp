// The COMPLETE patched source is included: Database, real bridge() loop, outbox,
// mux, validation, final publication and teardown. Only OS/clock/tty are replaced.
#define main preserved_production_main
#include "../bridge/esp32_bridge.cpp"
#undef main
int main(int argc,char** argv){try{
    if(argc==2 && std::string(argv[1])=="--default-plan"){
        char name[]="bridge";char* args[]{name};return preserved_production_main(1,args);
    }
    if(argc<4)return 2;
    bool enabled=false,dual=false;
    for(int i=4;i<argc;++i){if(std::string(argv[i])=="--fake-enabled")enabled=true;else if(std::string(argv[i])=="--dual")dual=true;else return 2;}
    mock_io::state().configure(enabled);
    Options o;o.db=argv[1];o.log=o.db+".events.log";o.feed_outbox=argv[2];o.feed_review=argv[3];
    o.feed_link=true;o.live_serial=true;o.firmware_policy=dual?FirmwarePolicy::DUAL_STATION_READ_ONLY:FirmwarePolicy::FEED_LINK_ONLY;o.reconnect_ms=100;
    return bridge(o);
}catch(const std::exception& e){std::cerr<<"ACTUAL_BRIDGE_SOURCE_ERROR "<<e.what()<<'\n';return 1;}}
